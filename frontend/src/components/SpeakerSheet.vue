<template>
  <BottomSheet v-if="store.ui.speakerSheet" title="Play on" label="Choose where to play" :layer="1" @close="close">
    <template #head-action>
      <button class="btn btn-ghost" :disabled="scanning" @click="scan">
        <Icon name="refresh" :size="18" /> {{ scanning ? 'Looking…' : 'Scan again' }}
      </button>
    </template>
    <p class="muted sp-note">{{ scanning ? 'Looking for speakers on your Wi-Fi…' : 'Speakers found on your Wi-Fi' }}</p>

    <div role="radiogroup" aria-label="Speakers">
      <button v-for="name in options" :key="name" class="choice" role="radio" :aria-checked="isChosen(name) ? 'true' : 'false'" :disabled="saving" @click="choose(name)">
        <span class="badge"><Icon name="speaker" :size="20" /></span>
        <span class="grow">
          <span class="title">{{ name }}</span>
          <span class="sub">{{ noteFor(name) }}</span>
        </span>
        <span class="radio-dot"></span>
      </button>
      <button class="choice" role="radio" :aria-checked="store.playTarget === 'phone' ? 'true' : 'false'" @click="choosePhone">
        <span class="badge"><Icon name="phone" :size="20" /></span>
        <span class="grow">
          <span class="title">This phone</span>
          <span class="sub">Listen here, no speaker needed</span>
        </span>
        <span class="radio-dot"></span>
      </button>
    </div>
    <p v-if="!scanning && speakers.length === 0" class="muted sp-note">No speakers found. Check they're switched on and on the same Wi-Fi, then scan again.</p>
    <p class="muted sp-note">Stickers always play on the chosen speaker. “This phone” only affects this phone.</p>

    <button class="btn btn-primary btn-lg btn-block" @click="close">Done</button>
  </BottomSheet>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '../api'
import { store, saveConfig, setPlayTarget, toast } from '../store'
import BottomSheet from './BottomSheet.vue'
import Icon from './Icon.vue'

const speakers = ref([])
const scanning = ref(false)
const saving = ref(false)

// Always list the saved speaker, even if the scan didn't find it this time
const options = computed(() => {
  const list = [...speakers.value]
  if (store.config.speaker && !list.includes(store.config.speaker)) list.unshift(store.config.speaker)
  return list
})

function isChosen(name) {
  return store.playTarget !== 'phone' && store.config.speaker === name
}

function noteFor(name) {
  const found = speakers.value.includes(name)
  if (store.config.speaker === name && store.playback.playing) return 'Playing now'
  if (!found && !scanning.value) return 'Not found right now'
  return store.config.speaker === name ? 'Saved speaker' : 'Ready'
}

async function scan() {
  scanning.value = true
  try {
    speakers.value = (await api.get('/speakers')).speakers || []
  } catch (e) {
    toast(`Couldn't look for speakers: ${e.message}`, 'error')
  } finally {
    scanning.value = false
  }
}

async function choose(name) {
  setPlayTarget('speaker')
  if (store.config.speaker === name) return
  saving.value = true
  try {
    await saveConfig({ speaker: name })
    toast(`Stories will play on ${name}`, 'ok')
  } catch (e) {
    toast(`Couldn't save: ${e.message}`, 'error')
  } finally {
    saving.value = false
  }
}

function choosePhone() {
  setPlayTarget('phone')
}

function close() { store.ui.speakerSheet = false }

watch(() => store.ui.speakerSheet, (open) => { if (open) scan() }, { immediate: true })
</script>

<style scoped>
.sp-note { font-size: 14px; margin: 0 4px 12px; }
.choice { margin-bottom: 8px; }
.choice + .choice { margin-top: 0; }
</style>

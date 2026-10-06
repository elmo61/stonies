<template>
  <section v-if="visible" class="now" aria-label="Now playing">
    <button class="np-open" @click="openSheet" :disabled="!song">
      <Cover v-if="song" :song="song" :size="64" />
      <div class="np-text">
        <span class="label">{{ label }}</span>
        <span class="title ellipsis">{{ title }}</span>
        <span v-if="subtitle" class="sub ellipsis">{{ subtitle }}</span>
      </div>
    </button>

    <div v-if="store.playback.playing && chapterCount">
      <div class="bar"><span :style="{ width: progressPct + '%' }"></span></div>
      <div class="times">
        <span>Chapter {{ chapterIndex + 1 }} of {{ chapterCount }}</span>
        <span v-if="store.playback.current_time">{{ formatTime(store.playback.current_time) }} in</span>
      </div>
    </div>

    <div class="np-controls">
      <button class="np-stop" :disabled="stopping || !store.playback.playing" aria-label="Stop playing" @click="stop">
        <Icon name="stop" :size="22" />
      </button>
      <button class="now-chip np-speaker" @click="store.ui.speakerSheet = true">
        <Icon name="speaker" :size="18" />
        <span class="ellipsis">{{ store.config.speaker || 'Choose speaker' }}</span>
        <Icon name="chevronDown" :size="16" class="np-chev" />
      </button>
      <RouterLink v-if="sleepAt" to="/settings" class="now-chip" :aria-label="`Bedtime: stops at ${sleepAt}`">
        <Icon name="moon" :size="18" />{{ sleepAt }}
      </RouterLink>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { store, songById, isStory, formatTime, stopPlayback, displayName } from '../store'
import Cover from './Cover.vue'
import Icon from './Icon.vue'

const stopping = ref(false)
const casting = computed(() => store.castingId ? songById(store.castingId) : null)
const song = computed(() => casting.value || songById(store.playback.song_id))
const visible = computed(() => store.playback.playing || !!casting.value)

const chapterCount = computed(() => isStory(song.value) ? song.value.chapters.length : 0)
const chapterIndex = computed(() => store.playback.chapter_index ?? 0)
const progressPct = computed(() => chapterCount.value ? Math.round(((chapterIndex.value + 1) / chapterCount.value) * 100) : 0)

const label = computed(() => {
  if (casting.value) return `Starting on ${store.config.speaker || 'speaker'}…`
  return `Playing on ${store.config.speaker || 'speaker'}`
})
const title = computed(() => (song.value ? displayName(song.value).title : store.playback.song_name) || 'Something')
const subtitle = computed(() => {
  if (casting.value || !isStory(song.value)) return ''
  const ch = song.value.chapters[chapterIndex.value]
  return ch ? `Ch ${chapterIndex.value + 1} · ${ch.name}` : ''
})

const sleepAt = computed(() => {
  const iso = store.nfc.sleep_stops_at
  if (!iso) return ''
  const d = new Date(iso)
  return isNaN(d) ? '' : d.toTimeString().slice(0, 5)
})

function openSheet() {
  if (song.value) store.ui.songId = song.value.id
}

async function stop() {
  stopping.value = true
  await stopPlayback()
  stopping.value = false
}
</script>

<style scoped>
.np-open { display: flex; gap: 14px; align-items: center; text-align: left; min-width: 0; }
.np-open:disabled { opacity: 1; }
.np-text { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.np-controls { display: flex; align-items: center; gap: 10px; }
.np-stop { width: 56px; height: 56px; flex-shrink: 0; border-radius: 50%; background: var(--amber); color: var(--navy); display: grid; place-items: center; }
.np-speaker { flex: 1; min-width: 0; }
.np-chev { margin-left: auto; flex-shrink: 0; }
</style>

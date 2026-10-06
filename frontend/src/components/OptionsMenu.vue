<template>
  <Teleport to="body">
    <template v-if="song">
      <div class="backdrop over" @click="close"></div>
      <div class="action-sheet" style="z-index: 71" role="dialog" aria-modal="true" :aria-label="`Options for ${song.name}`" @keydown.esc="close">
        <div class="group">
          <div class="om-head">
            <span class="display ellipsis">{{ song.name }}</span>
            <span v-if="place" class="muted">Saved place: Ch {{ place.chapter + 1 }}, {{ formatTime(place.time) }} in</span>
          </div>
          <button ref="first" class="action" @click="run(onPhone)">
            <Icon name="phone" class="icon" /> Play on this phone
          </button>
          <button v-if="!store.nfc.hw_error" class="action" @click="run(writeSticker)">
            <Icon name="sticker" class="icon" /> Write to a sticker
          </button>
          <button class="action" @click="run(renameSong)">
            <Icon name="pencil" class="icon" /> Rename
          </button>
          <button class="action" @click="run(chooseCover)">
            <Icon name="image" class="icon" /> {{ song.image_url ? 'Change cover' : 'Add cover' }}
          </button>
          <button v-if="hasChapters" class="action" @click="run(editChapters)">
            <Icon name="pencil" class="icon" /> Rename {{ song.type === 'album' ? 'tracks' : 'chapters' }}
          </button>
          <button v-if="place" class="action" @click="run(clearSavedPlace)">
            <Icon name="restart" class="icon" />
            <span>Start from the beginning next time<span class="hint">Forgets the saved place</span></span>
          </button>
          <button class="action danger" @click="remove">
            <Icon name="trash" class="icon" />
            <span>Delete…<span class="hint">Asks first. Its sticker will stop working.</span></span>
          </button>
        </div>
        <button class="btn btn-lg btn-block om-cancel" @click="close">Cancel</button>
      </div>
    </template>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { store, songById, isStory, savedPlace, formatTime, writeSticker, renameSong, clearSavedPlace, deleteSong, playOnPhone } from '../store'
import Icon from './Icon.vue'
import { chooseCover } from '../covers'
import { lockScroll, unlockScroll } from '../scrollLock'

const song = computed(() => songById(store.ui.optionsId))
const place = computed(() => song.value ? savedPlace(song.value) : null)
const hasChapters = computed(() => isStory(song.value) && song.value.chapters?.length > 0)
function editChapters(s) { store.ui.chaptersId = s.id }
const first = ref(null)

watch(song, async (s) => { if (s) { await nextTick(); first.value?.focus() } })

// Keep the page behind still while this is open
watch(() => !!song.value, (open, was) => { if (open && !was) lockScroll(); else if (!open && was) unlockScroll() })

function close() { store.ui.optionsId = null }

// Grab the song, then close the menu (which clears it) so dialogs and the
// sticker screen appear on top
function run(action) {
  const s = song.value
  close()
  action(s)
}

function onPhone(s) {
  const p = savedPlace(s)
  playOnPhone(s, p?.chapter ?? 0, p?.time ?? 0)
  store.ui.songId = null
}

async function remove() {
  const s = song.value
  close()
  if (await deleteSong(s)) store.ui.songId = null
}
</script>

<style scoped>
.om-head { padding: 16px 20px 12px; display: flex; flex-direction: column; gap: 2px; border-bottom: 1px solid var(--line); }
.om-head .display { font-size: 17px; }
.om-head .muted { font-size: 13px; }
.om-cancel { background: var(--card); color: var(--blue-ink); border-radius: 20px; }
</style>

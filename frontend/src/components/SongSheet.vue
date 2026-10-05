<template>
  <BottomSheet v-if="song" :label="song.name" @close="close">
    <template #top>
      <div class="ss-head">
        <Cover :song="song" :size="88" />
        <div class="ss-titles">
          <h2 class="display">{{ song.name }}</h2>
          <span class="muted">{{ kindLabel(song) }}<template v-if="story"> · {{ song.chapters.length }} {{ song.type === 'album' ? 'tracks' : 'chapters' }}</template></span>
        </div>
        <button class="icon-btn" :aria-label="`More options for ${song.name}`" @click="openOptions">
          <Icon name="more" />
        </button>
      </div>

      <div class="ss-actions">
        <button class="btn btn-primary btn-lg btn-block" :disabled="busy" @click="playMain">
          <Icon :name="busy ? 'refresh' : 'play'" :size="20" />
          {{ mainLabel }}
        </button>
        <button v-if="place" class="btn btn-ghost btn-block" :disabled="busy" @click="playFrom(0)">Start from chapter 1</button>
        <div class="ss-target">
          <span>Plays on <strong>{{ targetName }}</strong></span>
          <button class="btn btn-ghost" @click="store.ui.speakerSheet = true">Change</button>
        </div>
      </div>
      <h3 v-if="story" class="section-label ss-label">{{ song.type === 'album' ? 'Tracks' : 'Chapters' }} · tap one to play it</h3>
    </template>

    <ol v-if="story" class="chapters">
      <li v-for="(ch, i) in song.chapters" :key="ch.filename">
        <button class="chapter" :class="{ current: i === currentIndex }" :disabled="busy" @click="playFrom(i)" :aria-label="`Play chapter ${i + 1}, ${ch.name}`">
          <span class="num">{{ i + 1 }}</span>
          <span class="ch-text">
            <span class="ch-name ellipsis" :class="{ done: i < listenedUpTo }">{{ ch.name }}</span>
            <span v-if="i === currentIndex" class="ch-state">{{ currentLabel }}</span>
          </span>
          <Icon v-if="i === currentIndex && playingThis" name="bars" :size="20" class="ch-icon now" />
          <Icon v-else-if="i < listenedUpTo" name="check" :size="18" :stroke="2.4" class="ch-icon" />
        </button>
      </li>
    </ol>
  </BottomSheet>
</template>

<script setup>
import { computed, nextTick } from 'vue'
import { store, songById, isStory, kindLabel, savedPlace, formatTime, play } from '../store'
import BottomSheet from './BottomSheet.vue'
import Cover from './Cover.vue'
import Icon from './Icon.vue'

const song = computed(() => songById(store.ui.songId))
const story = computed(() => isStory(song.value))
const place = computed(() => song.value ? savedPlace(song.value) : null)
const busy = computed(() => store.castingId !== null)
const playingThis = computed(() => store.playback.playing && store.playback.song_id === song.value?.id)

// The highlighted chapter: what's playing now, otherwise the saved place
const currentIndex = computed(() => {
  if (playingThis.value && store.playback.chapter_index != null) return store.playback.chapter_index
  return place.value ? place.value.chapter : -1
})
const listenedUpTo = computed(() => Math.max(currentIndex.value, 0))
const currentLabel = computed(() => {
  if (playingThis.value) return 'Playing now'
  return place.value ? `Saved place · ${formatTime(place.value.time)} in` : ''
})

const mainLabel = computed(() => {
  if (!place.value) return story.value ? 'Play from the start' : 'Play'
  return `Resume · Ch ${place.value.chapter + 1}, ${formatTime(place.value.time)} in`
})
const targetName = computed(() => store.playTarget === 'phone' ? 'this phone' : (store.config.speaker || 'no speaker yet'))

function close() { store.ui.songId = null }
function openOptions() { store.ui.optionsId = song.value.id }

// Close the sheet and bring the now-playing card into view, so you can see
// it start (the card shows "Starting on…" while the speaker connects)
async function startPlaying(chapterIndex = null) {
  const s = song.value
  close()
  play(s, chapterIndex)
  // Scroll once the sheet is gone (its scroll lock released) and the card is in.
  // Smooth where the browser animates it; jump there if it hasn't moved.
  await nextTick()
  window.scrollTo({ top: 0, behavior: 'smooth' })
  setTimeout(() => { if (window.scrollY > 0) window.scrollTo(0, 0) }, 700)
}
function playMain() { startPlaying() }
function playFrom(i) { startPlaying(i) }
</script>

<style scoped>
.ss-head { display: flex; gap: 14px; align-items: flex-start; padding: 14px 10px 0 20px; }
.ss-titles { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6px; padding-top: 4px; }
.ss-titles h2 { font-size: 21px; line-height: 1.2; }
.ss-actions { display: flex; flex-direction: column; gap: 6px; padding: 16px 20px 0; }
.ss-target { display: flex; align-items: center; justify-content: space-between; font-size: 14px; color: var(--muted); }
.ss-target strong { color: var(--ink); }
.ss-target .btn { padding: 0 10px; min-height: 44px; }
.ss-label { padding: 10px 20px 4px; }
.chapters { list-style: none; margin: 0; padding: 0 0 8px; display: flex; flex-direction: column; gap: 2px; }
.chapter { width: 100%; min-height: 54px; padding: 6px 12px; border-radius: 14px; display: flex; align-items: center; gap: 14px; text-align: left; }
.chapter.current { background: var(--amber-soft); }
.num { width: 28px; flex-shrink: 0; text-align: center; font-weight: 700; font-size: 15px; color: var(--muted); }
.chapter.current .num { color: var(--amber-ink); }
.ch-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.ch-name { font-size: 16px; font-weight: 500; }
.ch-name.done { color: var(--muted); }
.chapter.current .ch-name { font-weight: 700; color: var(--ink); }
.ch-state { font-size: 13px; font-weight: 700; color: var(--amber-ink); }
.ch-icon { color: #8A93A6; flex-shrink: 0; }
.ch-icon.now { color: #C47A12; }
</style>

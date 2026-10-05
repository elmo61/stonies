<template>
  <section v-if="store.local" class="phone-player" aria-label="Playing on this phone">
    <ol v-if="expanded && story" class="pp-chapters">
      <li v-for="(ch, i) in song.chapters" :key="ch.filename">
        <button class="pp-ch" :class="{ on: i === chapter }" @click="startAudio(i, 0)">
          <span class="pp-num">{{ i + 1 }}</span><span class="ellipsis">{{ ch.name }}</span>
        </button>
      </li>
    </ol>

    <div class="pp-main">
      <button class="pp-info" :disabled="!story" :aria-expanded="story ? String(expanded) : undefined" @click="expanded = !expanded">
        <span class="pp-kicker">On this phone</span>
        <span class="pp-title ellipsis">{{ song.name }}</span>
        <span v-if="story" class="pp-sub ellipsis">Ch {{ chapter + 1 }} · {{ song.chapters[chapter]?.name }}</span>
      </button>
      <button v-if="story" class="icon-btn pp-btn" aria-label="Previous chapter" :disabled="chapter === 0" @click="startAudio(chapter - 1, 0)">
        <Icon name="back" :size="20" :stroke="2.4" />
      </button>
      <button class="icon-btn pp-btn pp-toggle" :aria-label="paused ? 'Play' : 'Pause'" @click="togglePause">
        <Icon :name="paused ? 'play' : 'pause'" :size="22" />
      </button>
      <button v-if="story" class="icon-btn pp-btn" aria-label="Next chapter" :disabled="chapter >= song.chapters.length - 1" @click="startAudio(chapter + 1, 0)">
        <Icon name="chevronRight" :size="20" :stroke="2.4" />
      </button>
      <button class="icon-btn pp-btn" aria-label="Stop playing on this phone" @click="stop">
        <Icon name="close" :size="20" :stroke="2.4" />
      </button>
    </div>

    <div class="pp-scrub">
      <span>{{ formatTime(current) }}</span>
      <input type="range" min="0" :max="duration || 100" step="1" :value="current" aria-label="Position" @input="seek($event.target.value)" />
      <span>{{ duration ? formatTime(duration) : '' }}</span>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'
import { audioUrl } from '../api'
import { store, isStory, formatTime } from '../store'
import Icon from './Icon.vue'

const song = computed(() => store.local?.song)
const story = computed(() => isStory(song.value))
const chapter = ref(0)
const current = ref(0)
const duration = ref(null)
const paused = ref(false)
const expanded = ref(false)
let audio = null

function teardown() {
  if (!audio) return
  audio.pause()
  audio.onloadedmetadata = audio.ontimeupdate = audio.onended = audio.onerror = null
  audio.src = ''
  audio = null
}

function startAudio(index, startTime = 0) {
  teardown()
  const s = song.value
  if (!s) return
  chapter.value = index
  current.value = 0
  duration.value = null
  paused.value = false
  expanded.value = false
  audio = new Audio(audioUrl(s, index))
  audio.onloadedmetadata = () => {
    duration.value = isFinite(audio.duration) ? audio.duration : null
    if (startTime > 0) audio.currentTime = startTime
  }
  audio.ontimeupdate = () => { current.value = audio.currentTime }
  audio.onended = () => {
    if (story.value && chapter.value < s.chapters.length - 1) startAudio(chapter.value + 1, 0)
    else stop()
  }
  audio.onerror = () => stop()
  audio.play().catch(() => { paused.value = true })
}

function togglePause() {
  if (!audio) return
  if (audio.paused) { audio.play(); paused.value = false }
  else { audio.pause(); paused.value = true }
}

function seek(v) { if (audio) audio.currentTime = parseFloat(v) }

function stop() {
  teardown()
  store.local = null
}

// A new play request (different song, or the same one again) restarts playback
watch(() => store.local, (req) => {
  if (req) startAudio(req.chapter ?? 0, req.time ?? 0)
  else teardown()
}, { immediate: true })

onUnmounted(teardown)
</script>

<style scoped>
.pp-main { display: flex; align-items: center; gap: 2px; }
.pp-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; text-align: left; min-height: 48px; }
.pp-info:disabled { opacity: 1; }
.pp-kicker { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--amber-light); }
.pp-title { font-weight: 700; }
.pp-sub { font-size: 13px; color: var(--navy-ink); }
.pp-btn { width: 44px; height: 44px; }
.pp-toggle { background: var(--amber); color: var(--navy); }
.pp-scrub { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--navy-ink); }
.pp-scrub span { min-width: 36px; text-align: center; }
.pp-chapters { list-style: none; margin: 0 0 8px; padding: 0; max-height: 40vh; overflow-y: auto; border-bottom: 1px solid var(--navy-2); }
.pp-ch { width: 100%; min-height: 44px; display: flex; align-items: center; gap: 10px; padding: 0 8px; border-radius: 10px; text-align: left; }
.pp-ch.on { background: var(--navy-2); color: var(--amber-light); font-weight: 700; }
.pp-num { width: 24px; text-align: center; color: var(--navy-ink); }
</style>

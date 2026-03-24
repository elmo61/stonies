<template>
  <div class="local-player-bar">

    <!-- Chapter panel -->
    <div v-if="expanded && song.type === 'audiobook'" class="local-player-chapters">
      <div
        v-for="(ch, i) in song.chapters"
        :key="i"
        class="local-player-chapter-row"
        :class="{ 'is-active': i === chapterIndex }"
        @click="jumpToChapter(i)"
      >
        <span class="local-player-ch-num">{{ i + 1 }}</span>
        <span class="local-player-ch-name">{{ ch.name }}</span>
        <span v-if="i === chapterIndex" class="local-player-ch-now">▶</span>
      </div>
    </div>

    <!-- Scrubber -->
    <div class="local-player-scrubber-row">
      <span class="local-player-time">{{ formatTime(currentTime) }}</span>
      <input
        type="range"
        class="local-player-scrubber"
        :min="0"
        :max="duration || 100"
        :value="currentTime"
        :step="1"
        @input="seek($event.target.value)"
      />
      <span class="local-player-time">{{ duration ? formatTime(duration) : '' }}</span>
    </div>

    <!-- Controls -->
    <div class="local-player-main-row">
      <div class="local-player-info">
        <div class="local-player-song-name">{{ song.name }}</div>
        <div v-if="song.type === 'audiobook'" class="local-player-chapter-label">
          Ch {{ chapterIndex + 1 }}
          <span v-if="song.chapters?.[chapterIndex]"> — {{ song.chapters[chapterIndex].name }}</span>
        </div>
      </div>
      <div class="local-player-controls">
        <button
          v-if="song.type === 'audiobook' && chapterIndex > 0"
          class="local-player-btn"
          @click="jumpToChapter(chapterIndex - 1)"
          title="Previous chapter"
        >⏮</button>
        <button
          v-if="song.type === 'audiobook' && chapterIndex < song.chapters.length - 1"
          class="local-player-btn"
          @click="jumpToChapter(chapterIndex + 1)"
          title="Next chapter"
        >⏭</button>
        <button class="local-player-btn is-stop" @click="stop" title="Stop">■</button>
        <button
          v-if="song.type === 'audiobook'"
          class="local-player-btn is-expand"
          @click="expanded = !expanded"
          :title="expanded ? 'Hide chapters' : 'Show chapters'"
        >{{ expanded ? '▼' : '▲' }}</button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  playRequest: { type: Object, required: true },
  // shape: { song, chapter, time }
})

const emit = defineEmits(['stopped'])

const BASE = `http://${window.location.hostname}:5000`

const song     = computed(() => props.playRequest.song)
const chapterIndex = ref(0)
const currentTime  = ref(0)
const duration     = ref(null)
const expanded     = ref(false)
let audio = null

// ── Audio helpers ──────────────────────────────────────────

function trackUrl(s, chIdx) {
  if (s.type === 'audiobook') {
    const ch = s.chapters[chIdx]
    return `${BASE}/music/${encodeURIComponent(s.folder)}/${encodeURIComponent(ch.filename)}`
  }
  return `${BASE}/music/${encodeURIComponent(s.filename)}`
}

function teardown() {
  if (!audio) return
  audio.pause()
  audio.src = ''
  audio.onloadedmetadata = null
  audio.ontimeupdate = null
  audio.onended = null
  audio.onerror = null
  audio = null
}

function startAudio(chIdx, startTime = 0) {
  teardown()
  const s = song.value
  chapterIndex.value = chIdx
  currentTime.value = 0
  duration.value = null

  audio = new Audio(trackUrl(s, chIdx))

  audio.onloadedmetadata = () => {
    if (!audio) return
    duration.value = isFinite(audio.duration) ? audio.duration : null
    if (startTime > 0) audio.currentTime = startTime
  }
  audio.ontimeupdate = () => {
    if (audio) currentTime.value = audio.currentTime
  }
  audio.onended = () => {
    const s = song.value
    if (s.type === 'audiobook' && chapterIndex.value < s.chapters.length - 1) {
      jumpToChapter(chapterIndex.value + 1)
    } else {
      stop()
    }
  }
  audio.onerror = () => stop()
  audio.play().catch(() => stop())
}

// ── Controls ───────────────────────────────────────────────

function jumpToChapter(i) {
  expanded.value = false
  startAudio(i, 0)
}

function seek(value) {
  if (audio) audio.currentTime = parseFloat(value)
}

function stop() {
  teardown()
  emit('stopped')
}

// ── Formatting ─────────────────────────────────────────────

function formatTime(seconds) {
  if (!seconds || seconds < 1) return '0:00'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  return `${m}:${s.toString().padStart(2, '0')}`
}

// ── Lifecycle ──────────────────────────────────────────────

// If the parent sends a new playRequest (e.g. tapping a different chapter row), restart.
watch(() => props.playRequest, (req) => {
  startAudio(req.chapter ?? 0, req.time ?? 0)
  expanded.value = false
})

onMounted(() => {
  const req = props.playRequest
  startAudio(req.chapter ?? 0, req.time ?? 0)
})

onUnmounted(teardown)
</script>

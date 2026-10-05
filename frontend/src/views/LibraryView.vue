<template>
  <div class="page" :class="{ 'has-player': store.local }">
    <NowPlaying />

    <div v-if="store.nfc.offline" class="quiet-note">
      <Icon name="moon" :size="18" />
      <span>Quiet mode is on: stickers are recognised but nothing plays.</span>
    </div>
    <div v-if="lastSeen" class="quiet-note">
      <Icon name="sticker" :size="18" />
      <span>Last sticker: <strong>{{ lastSeen.name }}</strong></span>
    </div>

    <div class="tabs" role="tablist" aria-label="Show">
      <button v-for="t in tabs" :key="t.id" role="tab" class="tab" :aria-selected="filter === t.id ? 'true' : 'false'" @click="filter = t.id">
        {{ t.label }}<span class="count">{{ t.count }}</span>
      </button>
    </div>

    <label class="search">
      <Icon name="search" :size="20" />
      <span class="sr-only">Search the library</span>
      <input v-model="query" type="search" placeholder="Search stories and songs" autocomplete="off" />
      <button v-if="query" class="icon-btn" aria-label="Clear search" @click.prevent="query = ''"><Icon name="close" :size="18" /></button>
    </label>

    <p v-if="!store.songsLoaded" class="empty">Loading the library…</p>
    <div v-else-if="store.songs.length === 0" class="empty">
      <p>Nothing here yet.</p>
      <RouterLink to="/add" class="btn btn-primary">Add your first story or song</RouterLink>
    </div>
    <p v-else-if="shown.length === 0" class="empty">Nothing matches “{{ query }}”.</p>

    <div v-else class="song-list">
      <div v-for="song in shown" :key="song.id" class="song-row" :class="{ 'is-playing': isPlaying(song) }">
        <button class="open" @click="store.ui.songId = song.id">
          <Cover :song="song" :size="52" />
          <span class="text">
            <span class="name ellipsis">{{ song.name }}</span>
            <span class="meta ellipsis">{{ isPlaying(song) ? 'Playing now' : songMeta(song) }}</span>
            <span v-if="progressPct(song) !== null" class="bar"><span :style="{ width: progressPct(song) + '%' }"></span></span>
          </span>
        </button>
        <button class="play" :aria-label="`Play ${song.name}`" :disabled="store.castingId !== null" @click="play(song)">
          <Icon :name="store.castingId === song.id ? 'refresh' : 'play'" :size="20" />
        </button>
      </div>
    </div>

    <RouterLink to="/add" class="fab" :class="{ raised: store.local }" aria-label="Add a story or song">
      <Icon name="plus" :size="26" :stroke="2.4" />
    </RouterLink>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { store, play, songMeta, savedPlace, isStory } from '../store'
import NowPlaying from '../components/NowPlaying.vue'
import Cover from '../components/Cover.vue'
import Icon from '../components/Icon.vue'

const filter = ref('all')
const query = ref('')

const stories = computed(() => store.songs.filter((s) => s.type === 'audiobook'))
const music = computed(() => store.songs.filter((s) => s.type !== 'audiobook'))
const tabs = computed(() => [
  { id: 'all', label: 'All', count: store.songs.length },
  { id: 'stories', label: 'Stories', count: stories.value.length },
  { id: 'music', label: 'Songs', count: music.value.length },
])

const shown = computed(() => {
  const base = filter.value === 'stories' ? stories.value : filter.value === 'music' ? music.value : store.songs
  const q = query.value.trim().toLowerCase()
  if (!q) return base
  return base.filter((s) =>
    s.name.toLowerCase().includes(q) ||
    (s.chapters || []).some((c) => (c.name || '').toLowerCase().includes(q)))
})

function isPlaying(song) {
  return store.playback.playing && store.playback.song_id === song.id
}

function progressPct(song) {
  const place = savedPlace(song)
  if (!place || !isStory(song)) return null
  return Math.max(4, Math.round(((place.chapter + 1) / song.chapters.length) * 100))
}

// Quiet mode: show which sticker was last tapped (nothing plays)
const lastSeen = computed(() => store.nfc.offline ? store.nfc.last_seen_song : null)
</script>

<style scoped>
.quiet-note {
  margin-top: 10px; padding: 12px 14px; border-radius: 14px; background: var(--blue-soft); color: var(--blue-ink);
  display: flex; align-items: center; gap: 10px; font-size: 14px; font-weight: 500;
}
.empty .btn { margin-top: 12px; }
</style>

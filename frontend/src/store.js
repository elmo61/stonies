// App-wide state and actions. Views read `store`; anything that talks to the
// box goes through an action here so polling and messages stay consistent.
import { reactive, computed } from 'vue'
import { api, connection } from './api'

// Earlier builds remembered "This phone" per phone, silently making every play
// button play on the phone. That mode is gone; forget any saved choice.
try { localStorage.removeItem('stonies.playTarget') } catch (_) {}

export const store = reactive({
  songs: [],
  songsLoaded: false,
  config: {},
  nfc: {},                    // /api/nfc/status
  playback: { playing: false },
  hostname: '',
  local: null,                // on-phone playback: { song, chapter, time }
  installPrompt: null,        // browser's install prompt, when it offers one (https only)
  castingId: null,            // song currently being sent to the speaker
  ui: {
    songId: null,             // story/song sheet
    optionsId: null,          // ⋮ menu
    chaptersId: null,         // chapter-name editor
    speakerSheet: false,
    writing: null,            // { songId } while a sticker is being written
    dialog: null,             // confirm / prompt dialog
    toast: null,              // { text, kind }
    offlineDismissed: false,
  },
})

// ---------------------------------------------------------------- helpers

export const isStory = (s) => s && (s.type === 'audiobook' || s.type === 'album')

export function songById(id) {
  return store.songs.find((s) => s.id === id) || null
}

export function formatTime(seconds) {
  if (!seconds || seconds < 1) return '0:00'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

export function kindLabel(song) {
  if (song.type === 'audiobook') return 'Story'
  if (song.type === 'album') return 'Album'
  return 'Song'
}

export function savedPlace(song) {
  if (!isStory(song) || !song.progress) return null
  return { chapter: song.progress.chapter_index || 0, time: song.progress.current_time || 0 }
}

export function songMeta(song) {
  if (!isStory(song)) return 'Song'
  const n = song.chapters?.length || 0
  const parts = [kindLabel(song), `${n} ${song.type === 'album' ? 'tracks' : 'chapters'}`]
  const place = savedPlace(song)
  if (place) parts.push(`Ch ${place.chapter + 1}, ${formatTime(place.time)} in`)
  return parts.join(' · ')
}

const SKIP = new Set(['the', 'and', 'of', 'a', 'an', 'to', 'in', 'for'])
export function initials(name) {
  const words = (name || '').replace(/[^\p{L}\p{N}\s]/gu, ' ').split(/\s+/).filter(Boolean)
  const keep = words.filter((w) => !SKIP.has(w.toLowerCase()))
  return (keep.length ? keep : words).slice(0, 2).map((w) => w[0].toUpperCase()).join('') || '♪'
}

// Deep, white-text-safe colours for covers without artwork
const COVER_COLORS = ['#7A2E3A', '#2F6B5E', '#345E8A', '#6A3FA0', '#8A5A12', '#A0452E', '#3B4FA0', '#5E6B2F']
export function coverColor(id) {
  let h = 0
  for (const c of String(id)) h = (h * 31 + c.charCodeAt(0)) >>> 0
  return COVER_COLORS[h % COVER_COLORS.length]
}

// "Ladybird Audio Adventures - Natural Wonders of the World" → series + title.
// Also "Ladybird   Outer Space": a run of spaces where a file name's dash was removed.
// Only split when several songs share the series, so a one-off title with a
// dash in it stays whole.
function splitTitle(name) {
  const m = /\s[-–—]\s|:\s|\s{2,}/.exec(name || '')
  if (!m || m.index < 3) return null
  const series = name.slice(0, m.index).trim()
  const title = name.slice(m.index + m[0].length).trim()
  return series && title ? { series, title } : null
}

const seriesNames = computed(() => {
  const counts = new Map()
  for (const s of store.songs) {
    const split = splitTitle(s.name)
    if (split) counts.set(split.series, (counts.get(split.series) || 0) + 1)
  }
  return new Set([...counts].filter(([, n]) => n >= 2).map(([series]) => series))
})

export function displayName(song) {
  const split = splitTitle(song?.name)
  if (split && seriesNames.value.has(split.series)) return split
  return { series: '', title: song?.name || '' }
}

// Covers are saved with the box's full http address (e.g. http://192.168.1.102:5000/images/x.jpg).
// Load them from wherever the app was opened instead: an https page can't load
// http images, and the box's address may have changed since the upload.
export function coverUrl(song) {
  const url = song?.image_url || ''
  const i = url.indexOf('/images/')
  return i >= 0 ? url.slice(i) : url
}

export function boxName() {
  const host = (store.hostname || window.location.hostname || '').replace(/\.local$/i, '')
  const m = host.match(/^stonies[-_](.+)$/i)
  if (m) return `${m[1].charAt(0).toUpperCase()}${m[1].slice(1)}'s Stonies`
  if (!host || /^[\d.]+$/.test(host) || host === 'localhost') return 'Stonies'
  return host
}

// Overall health shown in the top bar
export const health = computed(() => {
  if (!connection.online) return { level: 'offline', label: "Can't reach" }
  const n = store.nfc
  if (n.hw_error) return { level: 'warn', label: 'Needs a look' }
  if (n.nfc_heartbeat_age != null && n.nfc_heartbeat_age > 15) return { level: 'warn', label: 'Needs a look' }
  if (store.config && store.songsLoaded && !store.config.speaker) {
    return { level: 'warn', label: 'No speaker' }
  }
  if (n.offline) return { level: 'quiet', label: 'Quiet mode' }
  return { level: 'ok', label: 'All good' }
})

// ---------------------------------------------------------------- messages

let toastTimer = null
export function toast(text, kind = 'info') {
  store.ui.toast = { text, kind }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { store.ui.toast = null }, kind === 'error' ? 6000 : 3500)
}

// Promise-based dialogs: confirmDialog({...}) -> true/false, promptDialog -> string|null
export function confirmDialog({ title, message = '', confirmLabel = 'OK', danger = false }) {
  return new Promise((resolve) => {
    store.ui.dialog = { kind: 'confirm', title, message, confirmLabel, danger, resolve }
  })
}
export function promptDialog({ title, value = '', confirmLabel = 'Save', label = '' }) {
  return new Promise((resolve) => {
    store.ui.dialog = { kind: 'prompt', title, value, confirmLabel, label, resolve }
  })
}

// ---------------------------------------------------------------- loading

export async function loadSongs() {
  try {
    const data = await api.get('/songs')
    store.songs = data.songs || []
    store.songsLoaded = true
  } catch (e) {
    if (connection.online) toast(`Couldn't load the library: ${e.message}`, 'error')
  }
}

export async function loadConfig() {
  try { store.config = await api.get('/config') } catch (_) {}
}

export async function loadBox() {
  try { store.hostname = (await api.get('/box')).hostname || '' } catch (_) {}
}

export async function refreshNfc() {
  try { store.nfc = await api.get('/nfc/status') } catch (_) {}
}

export async function refreshPlayback() {
  try { store.playback = await api.get('/playback/status') } catch (_) {}
}

// Polling: quick while a sticker is being written, slower otherwise, and a
// steady retry while the box can't be reached.
let nfcTimer = null
let playTimer = null
function scheduleNfc() {
  clearTimeout(nfcTimer)
  const ms = store.ui.writing ? 1000 : (connection.online ? 10000 : 5000)
  nfcTimer = setTimeout(async () => {
    const wasOnline = connection.online
    await refreshNfc()
    if (!wasOnline && connection.online) {
      store.ui.offlineDismissed = false
      await Promise.all([loadSongs(), loadConfig(), refreshPlayback()])
    }
    scheduleNfc()
  }, ms)
}
function schedulePlayback() {
  clearTimeout(playTimer)
  playTimer = setTimeout(async () => {
    if (connection.online) await refreshPlayback()
    schedulePlayback()
  }, store.playback.playing ? 10000 : 30000)
}

export function pollNow() {
  refreshNfc().then(scheduleNfc)
}

export async function startApp() {
  await Promise.all([loadBox(), loadConfig(), loadSongs(), refreshNfc(), refreshPlayback()])
  scheduleNfc()
  schedulePlayback()
}

// ---------------------------------------------------------------- playback

export function playOnPhone(song, chapter, time = 0) {
  store.local = { song, chapter: chapter ?? 0, time, at: Date.now() }
}

// Play a song or a chapter on the box's speaker
// (to listen on the phone instead: ⋮ menu → Play on this phone → playOnPhone)
export async function play(song, chapterIndex = null) {
  if (store.nfc.offline) {
    toast('Quiet mode is on, so nothing plays. Turn it off in Settings.', 'error')
    return
  }
  if (!store.config.speaker) {
    toast('Choose a speaker first.', 'error')
    store.ui.speakerSheet = true
    return
  }
  if (store.castingId) return
  store.castingId = song.id
  try {
    const body = { id: song.id }
    if (chapterIndex != null) body.chapter_index = chapterIndex
    await api.post('/play', body)
    toast(`Playing on ${store.config.speaker}`, 'ok')
    await Promise.all([refreshPlayback(), refreshNfc()])
    schedulePlayback()
  } catch (e) {
    toast(`Couldn't play: ${e.message}`, 'error')
  } finally {
    store.castingId = null
  }
}

export async function stopPlayback() {
  try {
    await api.post('/playback/stop')
    store.playback = { playing: false }
    await loadSongs()   // pick up the saved place
  } catch (e) {
    toast(`Couldn't stop: ${e.message}`, 'error')
  }
}

// ---------------------------------------------------------------- songs

export async function renameSong(song) {
  const name = await promptDialog({ title: 'Rename', value: song.name, label: 'Name' })
  if (!name || !name.trim() || name.trim() === song.name) return
  try {
    await api.patch(`/songs/${song.id}`, { name: name.trim() })
    song.name = name.trim()
    toast('Renamed', 'ok')
  } catch (e) {
    toast(`Couldn't rename: ${e.message}`, 'error')
  }
}

export async function clearSavedPlace(song) {
  try {
    await api.del(`/songs/${song.id}/progress`)
    delete song.progress
    toast('It will start from the beginning next time', 'ok')
  } catch (e) {
    toast(`Couldn't reset: ${e.message}`, 'error')
  }
}

export async function deleteSong(song) {
  const ok = await confirmDialog({
    title: `Delete “${song.name}”?`,
    message: 'This removes it and its audio from this box. Its sticker will stop working.',
    confirmLabel: 'Delete',
    danger: true,
  })
  if (!ok) return false
  try {
    await api.del(`/songs/${song.id}`)
    store.songs = store.songs.filter((s) => s.id !== song.id)
    toast('Deleted', 'ok')
    return true
  } catch (e) {
    toast(`Couldn't delete: ${e.message}`, 'error')
    return false
  }
}

// ---------------------------------------------------------------- stickers

export async function writeSticker(song) {
  try {
    await api.post(`/songs/${song.id}/retag`)
    openWriter(song.id)
  } catch (e) {
    toast(`Couldn't start writing: ${e.message}`, 'error')
  }
}

export function openWriter(songId) {
  store.ui.writing = { songId, startedAt: Date.now() }
  pollNow()
}

export async function cancelWriting() {
  try { await api.post('/nfc/cancel') } catch (_) {}
  store.ui.writing = null
  pollNow()
}

// ---------------------------------------------------------------- settings

export async function saveConfig(partial) {
  const data = await api.post('/config', partial)
  await loadConfig()
  return data
}

// Self-update: the box installs, restarts, and we reload once it's back
export async function applyUpdate() {
  await api.post('/update/apply')
  toast('Update installed. Restarting…', 'ok')
  await new Promise((r) => setTimeout(r, 5000))
  for (let i = 0; i < 40; i++) {
    try {
      const r = await fetch('/api/nfc/status', { cache: 'no-store' })
      if (r.ok) break
    } catch (_) {}
    await new Promise((r) => setTimeout(r, 3000))
  }
  location.reload()
}

export async function toggleQuiet() {
  try {
    const data = await api.post('/offline/toggle')
    store.nfc = { ...store.nfc, offline: data.offline }
    toast(data.offline ? 'Quiet mode on: stickers won’t play' : 'Quiet mode off', 'ok')
  } catch (e) {
    toast(`Couldn't change quiet mode: ${e.message}`, 'error')
  }
}

<template>
  <div id="app">

    <!-- Header -->
    <section class="hero is-dark mb-5">
      <div class="hero-body">
        <div class="container">
          <div class="level">
            <div class="level-left">
              <div>
                <p class="title">Stonies</p>
                <p class="subtitle">NFC-triggered Chromecast music player</p>
              </div>
            </div>
            <div class="level-right">
              <span
                class="tag is-medium"
                :class="nfcBadgeClass"
                :title="nfcStatus.hw_error || ''"
              >
                <span v-if="nfcStatus.mode === 'writing'" class="spin mr-1">⟳</span>
                {{ nfcBadgeLabel }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <div class="container" style="max-width: 860px;">

      <!-- Now playing (sticky) -->
      <div v-if="playbackStatus.playing" class="now-playing-bar">
        <span style="color: white;">
          <span>▶</span>
          <strong class="ml-2" style="color: white;">{{ playbackStatus.song_name || 'Unknown' }}</strong>
          <span v-if="playbackStatus.chapter_index != null" class="ml-2" style="color: rgba(255,255,255,0.75); font-size:0.88rem;">
            Ch {{ playbackStatus.chapter_index + 1 }}<span v-if="playbackStatus.current_time"> · {{ formatTime(playbackStatus.current_time) }}</span>
          </span>
          <span v-else-if="playbackStatus.current_time" class="ml-2" style="color: rgba(255,255,255,0.75); font-size:0.88rem;">· {{ formatTime(playbackStatus.current_time) }}</span>
          <span v-if="nfcStatus.sleep_stops_at" class="tag is-info is-light is-small ml-2" :title="'Stops at ' + nfcStatus.sleep_stops_at">
            🌙 {{ formatSleepCountdown(nfcStatus.sleep_stops_at) }}
          </span>
        </span>
        <button class="button is-danger is-small" :class="{'is-loading': stopping}" @click="stopPlayback">■ Stop</button>
      </div>

      <!-- Offline mode toggle -->
      <div class="mb-4">
        <button
          class="button is-fullwidth is-medium"
          :class="nfcStatus.offline ? 'is-warning' : 'is-light'"
          @click="toggleOffline"
          :disabled="nfcStatus.mode === 'writing'"
        >
          {{ nfcStatus.offline ? '📴 Offline Mode — tap to go Online' : '🟢 Online — tap to go Offline' }}
        </button>
      </div>

      <!-- Offline last-seen banner -->
      <div v-if="nfcStatus.offline && nfcStatus.last_seen_song" class="notification is-warning is-light mb-4">
        <strong>Tag detected (not casting):</strong>
        <span v-if="nfcStatus.last_seen_song.image_url">
          <img :src="nfcStatus.last_seen_song.image_url" style="width:24px;height:24px;object-fit:cover;border-radius:3px;vertical-align:middle;margin: 0 6px;" />
        </span>
        {{ nfcStatus.last_seen_song.name }}
        <small class="has-text-grey ml-2">({{ nfcStatus.last_seen_song.id }})</small>
      </div>

      <!-- NFC status banner (visible when writing) -->
      <div v-if="nfcStatus.mode === 'writing' || nfcBannerDismissed === false && nfcStatus.sub_state === 'success'" class="notification mb-4" :class="nfcBannerClass">
        <button class="delete" @click="dismissNfcBanner"></button>
        <span v-if="nfcStatus.sub_state === 'waiting_for_tag'">
          <span class="spin">⟳</span> Touch the sticker now to write the tag...
        </span>
        <span v-else-if="nfcStatus.sub_state === 'writing_tag'">
          <span class="spin">⟳</span> Writing to tag...
        </span>
        <span v-else-if="nfcStatus.sub_state === 'success'">
          Tag written! Song added and ready to play.
          <span v-if="successCountdown > 0"> Returning to listening in {{ successCountdown }}s...</span>
        </span>
        <span v-else-if="nfcStatus.sub_state === 'error'">
          Write failed: {{ nfcStatus.error }}
          <button class="button is-small is-white ml-3" @click="cancelWrite">Cancel</button>
        </span>
        <span v-else-if="nfcStatus.mode === 'writing'">
          <span class="spin">⟳</span> Preparing write...
        </span>
      </div>

      <!-- Settings summary bar -->
      <div class="box settings-bar mb-4 px-4 py-3">
        <div class="level is-mobile">
          <div class="level-left" style="gap: 1rem; flex-wrap: wrap;">
            <span>
              🔊
              <strong v-if="savedSpeaker">{{ savedSpeaker }}</strong>
              <span v-else class="has-text-grey-light">No speaker set</span>
            </span>
            <span class="has-text-grey-light" aria-hidden="true">·</span>
            <span v-if="sleepTimer.enabled" class="has-text-grey">
              🌙 After {{ sleepTimer.after_time }}, {{ sleepTimer.duration_minutes }} min
            </span>
            <span v-else class="has-text-grey-light">🌙 Sleep timer off</span>
          </div>
          <div class="level-right" style="gap: 0.5rem;">
            <span v-if="updateAvailable" class="tag is-warning" :title="`${updateCommits} commit${updateCommits !== 1 ? 's' : ''} behind origin/main`">
              ⬆️ Update available
            </span>
            <button class="button is-light is-small" @click="openSettings" title="Settings">
              ⚙️ Settings
            </button>
          </div>
        </div>
      </div>

      <!-- Song library box -->
      <div class="box">
        <div class="level mb-4">
          <div class="level-left">
            <h2 class="title is-5 mb-0">Song Library</h2>
          </div>
          <div class="level-right">
            <div class="buttons">
              <button
                class="button is-light is-small"
                :class="{'is-loading': scanning}"
                @click="scanImports"
                title="Move files from music_import/ into the library"
              >
                📥 Scan Imports
              </button>
              <button class="button is-primary is-small" @click="showUpload = !showUpload; if (!showUpload) setUploadType('track')">
                {{ showUpload ? 'Cancel' : '+ Add Song' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Upload form -->
        <div v-if="showUpload" class="upload-form mb-4">

          <!-- Type toggle -->
          <div class="field">
            <label class="label">Type</label>
            <div class="buttons has-addons">
              <button class="button is-small" :class="uploadType === 'track' ? 'is-info is-selected' : 'is-light'" @click="setUploadType('track')">🎵 Track</button>
              <button class="button is-small" :class="uploadType === 'audiobook' ? 'is-info is-selected' : 'is-light'" @click="setUploadType('audiobook')">📚 Audiobook</button>
            </div>
          </div>

          <!-- Name -->
          <div class="field">
            <label class="label">{{ uploadType === 'audiobook' ? 'Audiobook Name' : 'Song Name' }}</label>
            <div class="control">
              <input class="input" type="text" v-model="uploadName" :placeholder="uploadType === 'audiobook' ? 'e.g. Harry Potter and the Philosopher\'s Stone' : 'e.g. Mr. Blue Sky'" />
            </div>
          </div>

          <!-- TRACK: single file -->
          <div v-if="uploadType === 'track'" class="field">
            <label class="label">Audio File</label>
            <div class="control">
              <input class="input" type="file" accept=".mp3,.m4a" @change="onFileChange" />
            </div>
          </div>

          <!-- AUDIOBOOK: folder or files -->
          <div v-if="uploadType === 'audiobook'" class="field">
            <label class="label">Chapter Files</label>
            <div class="mb-2">
              <button class="button is-small is-light mr-2" type="button" @click="$refs.folderPicker.click()">📁 Select Folder</button>
              <button class="button is-small is-light" type="button" @click="$refs.filesPicker.click()">📄 Select Files</button>
              <input ref="folderPicker" type="file" webkitdirectory multiple accept=".mp3,.m4a" style="display:none" @change="onAudiobookFilesChange" />
              <input ref="filesPicker" type="file" multiple accept=".mp3,.m4a" style="display:none" @change="onAudiobookFilesChange" />
            </div>
            <div v-if="uploadChapters.length > 0">
              <p class="help mb-2">{{ uploadChapters.length }} chapter{{ uploadChapters.length !== 1 ? 's' : '' }} selected — edit names if needed:</p>
              <div v-for="(ch, i) in uploadChapters" :key="i" class="field has-addons mb-1">
                <div class="control">
                  <span class="button is-small is-static">{{ i + 1 }}.</span>
                </div>
                <div class="control is-expanded">
                  <input class="input is-small" type="text" v-model="ch.name" :placeholder="`Chapter ${i + 1}`" />
                </div>
              </div>
            </div>
            <p v-else class="help has-text-grey">Select a folder or multiple audio files.</p>
          </div>

          <!-- Cover image -->
          <div class="field">
            <label class="label">Cover Image <span class="has-text-grey-light">(optional)</span></label>
            <div class="control">
              <input class="input" type="file" accept="image/*" @change="onImageChange" />
            </div>
            <p v-if="uploadImageFile" class="help has-text-grey">{{ uploadImageFile.name }}</p>
          </div>

          <div class="field">
            <div class="control">
              <button
                class="button is-primary"
                :class="{'is-loading': uploading}"
                :disabled="uploading || !uploadName || (uploadType === 'track' ? !uploadFile : uploadChapters.length === 0)"
                @click="uploadSong"
              >
                {{ nfcStatus.hw_error ? 'Upload' : 'Upload &amp; Write Tag' }}
              </button>
            </div>
          </div>
          <p v-if="uploadError" class="help is-danger">{{ uploadError }}</p>
        </div>

        <!-- Search -->
        <div v-if="songs.length > 0" class="field mb-3">
          <div class="control has-icons-left has-icons-right">
            <input class="input" type="text" v-model="searchQuery" placeholder="Search songs and audiobooks..." />
            <span class="icon is-left" style="pointer-events:none;">🔍</span>
            <span v-if="searchQuery" class="icon is-right" style="cursor:pointer; pointer-events:all;" @click="searchQuery = ''">✕</span>
          </div>
        </div>

        <!-- Import scan result -->
        <div v-if="scanResult" class="notification is-success is-light mb-3">
          <button class="delete" @click="scanResult = null"></button>
          <strong>Import complete:</strong>
          <span v-for="(item, i) in scanResult.imported" :key="i">
            {{ i > 0 ? ', ' : ' ' }}
            <span v-if="item.type === 'audiobook'">📚 {{ item.name }} ({{ item.chapters }} chapters)</span>
            <span v-else>🎵 {{ item.name }}</span>
          </span>
          <span v-if="scanResult.imported.length === 0">Nothing new found in music_import/.</span>
          <span v-if="scanResult.errors.length > 0" class="has-text-danger ml-2">
            {{ scanResult.errors.length }} error(s): {{ scanResult.errors.join('; ') }}
          </span>
        </div>

        <!-- Loading -->
        <div v-if="loadingSongs" class="has-text-centered py-5">
          <span class="spin" style="font-size: 2rem;">⟳</span>
          <p class="mt-2 has-text-grey">Loading songs...</p>
        </div>

        <!-- Empty -->
        <div v-else-if="songs.length === 0 && !showUpload && !loadingSongs" class="has-text-centered py-5 has-text-grey">
          <p>No songs yet. Click <strong>+ Add Song</strong> to get started.</p>
        </div>

        <!-- Empty search result -->
        <div v-if="songs.length > 0 && filteredSongs.length === 0" class="has-text-centered py-4 has-text-grey">
          No results for "{{ searchQuery }}"
        </div>

        <!-- Song table -->
        <table v-else-if="filteredSongs.length > 0" class="table is-fullwidth" style="border-collapse:collapse;">
          <tbody>
            <tr v-for="song in filteredSongs" :key="song.id" class="song-row" :class="{'is-audiobook': song.type === 'audiobook'}">

              <!-- Thumbnail -->
              <td style="width: 56px; padding-left: 0.75rem;">
                <img v-if="song.image_url" :src="song.image_url" class="song-thumb" :alt="song.name" />
                <div v-else-if="song.type === 'audiobook'" class="song-icon is-audiobook">📚</div>
                <div v-else class="song-icon is-track">🎵</div>
              </td>

              <!-- Name + metadata -->
              <td>
                <!-- View mode -->
                <template v-if="editingId !== song.id">
                  <div style="display:flex; align-items:baseline; gap:6px; flex-wrap:wrap;">
                    <span class="song-name">{{ song.name }}</span>
                    <span v-if="song.type === 'audiobook'" class="tag is-warning is-light" style="font-size:0.68rem; height:1.4em;">Audiobook</span>
                  </div>
                  <div class="song-meta">
                    {{ song.id }} · {{ formatDate(song.uploaded_at) }}
                    <template v-if="song.type === 'audiobook'">
                      · {{ song.chapters.length }} ch
                      <span v-if="song.progress" class="has-text-info ml-1">· Ch {{ (song.progress.chapter_index||0)+1 }} · {{ formatTime(song.progress.current_time) }} <a @click.prevent="clearProgress(song)" href="#" style="color:#aaa;" title="Clear saved position">✕</a></span>
                      <a class="ml-1" @click.prevent="toggleChapters(song.id)" href="#" style="color:#aaa;">[{{ expandedId === song.id ? 'hide' : 'show' }}]</a>
                    </template>
                    <template v-else>· {{ song.filename }}</template>
                  </div>
                  <ul v-if="song.type === 'audiobook' && expandedId === song.id" class="chapter-list mt-2">
                    <li v-for="(ch, i) in song.chapters" :key="ch.filename">
                      <button class="button is-primary is-small py-0" style="height:1.4rem; min-width:1.8rem; font-size:0.7rem;"
                        :class="{'is-loading': playingId === song.id}"
                        :disabled="!savedSpeaker || playingId !== null || nfcStatus.offline"
                        @click="playChapter(song, i)" :title="`Play from chapter ${i+1}`">▶</button>
                      <span :class="playbackStatus.song_id === song.id && playbackStatus.chapter_index === i ? 'has-text-success has-text-weight-semibold' : ''">
                        {{ i+1 }}. {{ ch.name }}
                        <span v-if="playbackStatus.song_id === song.id && playbackStatus.chapter_index === i" style="font-size:0.7rem; color:#888;"> ▶ {{ formatTime(playbackStatus.current_time) }}</span>
                      </span>
                    </li>
                  </ul>
                </template>

                <!-- Edit / rename mode -->
                <template v-else>
                  <div class="field has-addons mb-0">
                    <div class="control is-expanded">
                      <input class="input is-small" type="text" v-model="editingName"
                        @keyup.enter="saveRename(song)" @keyup.escape="cancelRename()"
                        style="font-weight:600;" autofocus />
                    </div>
                    <div class="control">
                      <button class="button is-success is-small" @click="saveRename(song)" :disabled="!editingName.trim()">✓</button>
                    </div>
                    <div class="control">
                      <button class="button is-light is-small" @click="cancelRename()">✕</button>
                    </div>
                  </div>
                  <p v-if="renameError" class="help is-danger mb-0">{{ renameError }}</p>
                </template>
              </td>

              <!-- Actions -->
              <td class="song-actions">
                <div class="buttons is-right">
                  <button class="button is-primary is-small"
                    :class="{'is-loading': playingId === song.id}"
                    :disabled="!savedSpeaker || playingId !== null || nfcStatus.offline"
                    @click="playSong(song)"
                    :title="nfcStatus.offline ? 'Go online to play' : !savedSpeaker ? 'Save a speaker first' : song.type === 'audiobook' && song.progress ? `Resume Ch ${(song.progress.chapter_index||0)+1} on ${savedSpeaker}` : 'Play on ' + savedSpeaker">
                    ▶
                  </button>
                  <button class="button is-light is-small"
                    :disabled="editingId === song.id"
                    @click="startRename(song)" title="Rename">
                    ✏️
                  </button>
                  <button v-if="!nfcStatus.hw_error" class="button is-info is-small is-outlined"
                    :class="{'is-loading': retaggingId === song.id}"
                    :disabled="nfcStatus.mode === 'writing'"
                    @click="retagSong(song)" title="Write NFC tag">
                    🏷
                  </button>
                  <button class="button is-danger is-small is-outlined"
                    :disabled="deletingId === song.id"
                    @click="deleteSong(song)" title="Delete">
                    ✕
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <p v-if="songError" class="help is-danger mt-2">{{ songError }}</p>
        <p v-if="playStatus" class="help is-success mt-2">{{ playStatus }}</p>
      </div>


      <p class="has-text-centered has-text-grey-light mt-3 mb-6">
        <small>Stonies — running on {{ piHost }}</small>
      </p>

    </div>

  <!-- Settings modal -->
  <div class="modal" :class="{'is-active': showSettings}">
    <div class="modal-background" @click="showSettings = false"></div>
    <div class="modal-card" style="max-width: 480px; width: 90%;">
      <header class="modal-card-head">
        <p class="modal-card-title">⚙️ Settings</p>
        <button class="delete" aria-label="close" @click="showSettings = false"></button>
      </header>
      <section class="modal-card-body">

        <h3 class="title is-6 mb-3">🔊 Speaker</h3>
        <div class="field has-addons mb-2">
          <div class="control is-expanded">
            <div class="select is-fullwidth" :class="{'is-loading': loadingSpeakers}">
              <select v-model="selectedSpeaker" :disabled="loadingSpeakers || speakers.length === 0">
                <option value="" disabled>
                  {{ loadingSpeakers ? 'Scanning network...' : speakers.length === 0 ? 'No speakers found' : 'Select a speaker' }}
                </option>
                <option v-for="s in speakers" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>
          </div>
          <div class="control">
            <button class="button is-light" @click="loadSpeakers" :disabled="loadingSpeakers" title="Scan for speakers">
              <span :class="loadingSpeakers ? 'spin' : ''">⟳</span>
            </button>
          </div>
        </div>
        <div class="field">
          <button class="button is-info is-fullwidth" @click="saveSpeaker" :disabled="!selectedSpeaker || savingSpeaker">
            {{ savingSpeaker ? 'Saving...' : 'Save Speaker' }}
          </button>
        </div>
        <p v-if="savedSpeaker" class="help is-success mb-2">Active: {{ savedSpeaker }}</p>
        <p v-if="speakerError" class="help is-danger mb-2">{{ speakerError }}</p>

        <hr />

        <h3 class="title is-6 mb-3">🌙 Bedtime Sleep Timer</h3>
        <div class="field">
          <label class="checkbox">
            <input type="checkbox" v-model="sleepTimer.enabled" class="mr-2" />
            Stop playback automatically at night
          </label>
        </div>
        <div v-if="sleepTimer.enabled" class="columns is-mobile is-vcentered">
          <div class="column">
            <label class="label is-small mb-1">Active after</label>
            <input class="input" type="time" v-model="sleepTimer.after_time" />
          </div>
          <div class="column is-narrow">
            <label class="label is-small mb-1">Stop after</label>
            <div class="field has-addons mb-0">
              <div class="control">
                <input class="input" type="number" v-model.number="sleepTimer.duration_minutes" min="1" max="240" style="width: 75px;" />
              </div>
              <div class="control">
                <span class="button is-static">min</span>
              </div>
            </div>
          </div>
        </div>
        <div class="field">
          <button class="button is-info is-fullwidth" :class="{'is-loading': savingSleep}" @click="saveSleepTimer">
            Save Sleep Timer
          </button>
        </div>
        <p v-if="sleepSaveStatus" class="help is-success mb-0">{{ sleepSaveStatus }}</p>

      </section>
      <footer class="modal-card-foot" style="justify-content: flex-end;">
        <button class="button" @click="showSettings = false">Close</button>
      </footer>
    </div>
  </div>

  <!-- Fixed activity log bar -->
  <div class="activity-bar">
    <div style="color: #4a4060; font-size: 0.7rem; margin-bottom: 0.2rem;">
      NFC reader:
      <span v-if="nfcStatus.hw_error" style="color: #e05;">offline</span>
      <span v-else-if="nfcStatus.nfc_heartbeat_age === null" style="color: #888;">starting...</span>
      <span v-else-if="nfcStatus.nfc_heartbeat_age > 10" style="color: #e05;">⚠ stuck ({{ nfcStatus.nfc_heartbeat_age }}s ago)</span>
      <span v-else style="color: #4a9;">● active ({{ nfcStatus.nfc_heartbeat_age }}s ago)</span>
    </div>
    <div v-if="activityLog.length === 0" style="color: #555; font-style: italic;">No activity yet...</div>
    <div
      v-for="entry in [...activityLog].slice(-5).reverse()"
      :key="entry.seq"
      class="activity-bar-entry"
    >
      <span style="color: #6272a4;">[{{ entry.time }}]</span> {{ entry.msg }}
    </div>
  </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const API = `http://${window.location.hostname}:5000/api`
const piHost = window.location.host

// --- Speakers ---
const speakers = ref([])
const selectedSpeaker = ref('')
const savedSpeaker = ref('')
const loadingSpeakers = ref(false)
const savingSpeaker = ref(false)
const speakerError = ref('')

async function loadSpeakers() {
  loadingSpeakers.value = true
  speakerError.value = ''
  try {
    const res = await fetch(`${API}/speakers`)
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    speakers.value = data.speakers
    if (!selectedSpeaker.value && data.speakers.length === 1) {
      selectedSpeaker.value = data.speakers[0]
    }
  } catch (e) {
    speakerError.value = `Failed to load speakers: ${e.message}`
  } finally {
    loadingSpeakers.value = false
  }
}

const showSettings = ref(false)

function openSettings() {
  showSettings.value = true
  if (speakers.value.length === 0) loadSpeakers()
}

const sleepTimer = ref({ enabled: false, after_time: '19:00', duration_minutes: 60 })
const savingSleep = ref(false)
const sleepSaveStatus = ref('')

async function loadConfig() {
  try {
    const res = await fetch(`${API}/config`)
    const data = await res.json()
    if (data.speaker) {
      savedSpeaker.value = data.speaker
      selectedSpeaker.value = data.speaker
    }
    if (data.sleep_timer) {
      sleepTimer.value = { ...sleepTimer.value, ...data.sleep_timer }
    }
  } catch (_) {}
}

async function saveSleepTimer() {
  savingSleep.value = true
  sleepSaveStatus.value = ''
  try {
    const res = await fetch(`${API}/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sleep_timer: { ...sleepTimer.value } }),
    })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    sleepSaveStatus.value = 'Saved'
    setTimeout(() => sleepSaveStatus.value = '', 2000)
  } catch (e) {
    sleepSaveStatus.value = `Error: ${e.message}`
  } finally {
    savingSleep.value = false
  }
}

function formatSleepCountdown(isoStr) {
  if (!isoStr) return ''
  const diff = Math.max(0, Math.round((new Date(isoStr) - Date.now()) / 1000))
  const h = Math.floor(diff / 3600)
  const m = Math.floor((diff % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

async function saveSpeaker() {
  savingSpeaker.value = true
  speakerError.value = ''
  try {
    const res = await fetch(`${API}/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ speaker: selectedSpeaker.value }),
    })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    savedSpeaker.value = selectedSpeaker.value
  } catch (e) {
    speakerError.value = `Failed to save: ${e.message}`
  } finally {
    savingSpeaker.value = false
  }
}

// --- NFC status ---
const nfcStatus = ref({ mode: 'listening', sub_state: null, error: null, hw_error: null })
const nfcBannerDismissed = ref(false)
const successCountdown = ref(0)
let nfcPollTimer = null
let countdownTimer = null

const nfcBadgeLabel = computed(() => {
  if (nfcStatus.value.hw_error) return 'NFC Unavailable'
  if (nfcStatus.value.mode === 'writing') return 'Writing Tag...'
  return 'Listening'
})

const nfcBadgeClass = computed(() => {
  if (nfcStatus.value.hw_error) return 'is-warning'
  if (nfcStatus.value.mode === 'writing') return 'is-info'
  return 'is-success'
})

const nfcBannerClass = computed(() => {
  const s = nfcStatus.value.sub_state
  if (s === 'success') return 'is-success is-light'
  if (s === 'error') return 'is-danger is-light'
  return 'is-info is-light'
})

function dismissNfcBanner() {
  nfcBannerDismissed.value = true
}

async function pollNfcStatus() {
  try {
    const res = await fetch(`${API}/nfc/status`)
    const data = await res.json()
    const prev = nfcStatus.value
    nfcStatus.value = data
    ingestLog(data.log)
    // Transition into success — start countdown and reload songs
    if (data.sub_state === 'success' && prev.sub_state !== 'success') {
      await loadSongs()
      startCountdown(5)
    }
    const done = data.sub_state === 'error' || data.mode === 'listening'
    if (done) {
      stopNfcPoll()
    }
  } catch (_) {}
}

function startCountdown(seconds) {
  if (countdownTimer) clearInterval(countdownTimer)
  successCountdown.value = seconds
  countdownTimer = setInterval(() => {
    successCountdown.value -= 1
    if (successCountdown.value <= 0) {
      clearInterval(countdownTimer)
      countdownTimer = null
    }
  }, 1000)
}

function startNfcPoll() {
  stopNfcPoll()
  nfcPollTimer = setInterval(pollNfcStatus, 500)
}

function stopNfcPoll() {
  if (nfcPollTimer) {
    clearInterval(nfcPollTimer)
    nfcPollTimer = null
  }
}

async function cancelWrite() {
  try {
    await fetch(`${API}/nfc/cancel`, { method: 'POST' })
    await pollNfcStatus()
    await loadSongs()
  } catch (_) {}
}

// --- Playback status poll ---
const playbackStatus = ref({ playing: false })
let playbackPollTimer = null

function formatTime(seconds) {
  if (!seconds || seconds < 1) return ''
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}:${s.toString().padStart(2, '0')}`
}

const stopping = ref(false)

async function stopPlayback() {
  stopping.value = true
  try {
    const res = await fetch(`${API}/playback/stop`, { method: 'POST' })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    playbackStatus.value = { playing: false }
  } catch (e) {
    songError.value = `Stop error: ${e.message}`
  } finally {
    stopping.value = false
  }
}

async function pollPlayback() {
  if (playbackPollTimer) { clearTimeout(playbackPollTimer); playbackPollTimer = null }
  try {
    const res = await fetch(`${API}/playback/status`)
    const data = await res.json()
    playbackStatus.value = data
    // Patch progress into the local songs array so display updates without reload
    if (data.song_id && data.song_type === 'audiobook' && data.progress) {
      const song = songs.value.find(s => s.id === data.song_id)
      if (song) song.progress = data.progress
    }
  } catch (_) {}
  // Poll faster when something is playing, slower when idle
  const interval = playbackStatus.value.playing ? 10000 : 30000
  playbackPollTimer = setTimeout(pollPlayback, interval)
}

function startPlaybackPoll() {
  if (playbackPollTimer) { clearTimeout(playbackPollTimer); playbackPollTimer = null }
  playbackPollTimer = setTimeout(pollPlayback, 5000)
}

// --- Import scan ---
const scanning = ref(false)
const scanResult = ref(null)

const updateAvailable = ref(false)
const updateCommits = ref(0)

async function checkForUpdates() {
  try {
    const res = await fetch(`${API}/update/status`)
    const data = await res.json()
    if (!data.error) {
      updateAvailable.value = data.updates_available
      updateCommits.value = data.commits_behind
    }
  } catch (_) {}
}

async function scanImports() {
  scanning.value = true
  scanResult.value = null
  songError.value = ''
  try {
    const res = await fetch(`${API}/import/scan`, { method: 'POST' })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    scanResult.value = data
    if (data.imported.length > 0) {
      songs.value = data.songs
    }
  } catch (e) {
    songError.value = `Scan error: ${e.message}`
  } finally {
    scanning.value = false
  }
}

// --- Activity log ---
const activityLog = ref([])
let lastLogSeq = 0

function ingestLog(entries) {
  if (!entries) return
  const fresh = entries.filter(e => e.seq > lastLogSeq)
  if (fresh.length) {
    activityLog.value = [...activityLog.value, ...fresh]
    lastLogSeq = fresh[fresh.length - 1].seq
  }
}

// --- Audiobook chapter expansion ---
const expandedId = ref(null)
function toggleChapters(id) {
  expandedId.value = expandedId.value === id ? null : id
}

// --- Search / filter ---
const searchQuery = ref('')
const filteredSongs = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return songs.value
  return songs.value.filter(s =>
    s.name.toLowerCase().includes(q) ||
    (s.chapters && s.chapters.some(ch => ch.name.toLowerCase().includes(q)))
  )
})

// --- Inline rename ---
const editingId = ref(null)
const editingName = ref('')
const renameError = ref('')

function startRename(song) {
  editingId.value = song.id
  editingName.value = song.name
  renameError.value = ''
}

async function saveRename(song) {
  if (!editingName.value.trim()) return
  renameError.value = ''
  try {
    const res = await fetch(`${API}/songs/${song.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: editingName.value.trim() }),
    })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    song.name = data.name
    editingId.value = null
  } catch (e) {
    renameError.value = e.message
  }
}

function cancelRename() {
  editingId.value = null
  editingName.value = ''
  renameError.value = ''
}

// --- Songs ---
const songs = ref([])
const loadingSongs = ref(false)
const songError = ref('')
const playStatus = ref('')
const playingId = ref(null)
const deletingId = ref(null)
const retaggingId = ref(null)

const showUpload = ref(false)
const uploadType = ref('track')
const uploadName = ref('')
const uploadFile = ref(null)
const uploadImageFile = ref(null)
const uploading = ref(false)
const uploadError = ref('')
const uploadChapters = ref([]) // [{file, name}]

function setUploadType(t) {
  uploadType.value = t
  uploadName.value = ''
  uploadFile.value = null
  uploadImageFile.value = null
  uploadChapters.value = []
  uploadError.value = ''
}

function onImageChange(event) {
  uploadImageFile.value = event.target.files[0] || null
}

function deriveChapterName(filename) {
  let name = filename.replace(/\.[^.]+$/, '')
  name = name.replace(/^CH\d+[\s\-_]*/i, '')
  name = name.replace(/[-_]/g, ' ').replace(/\s+/g, ' ').trim()
  name = name.replace(/\w\S*/g, w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
  name = name.replace(/(\w)'S\b/g, "$1's")
  return name || filename
}

function deriveBookName(name) {
  name = name.replace(/^\d+[\s\-_]*/, '')
  name = name.replace(/[-_]/g, ' ').replace(/\s+/g, ' ').trim()
  name = name.replace(/\w\S*/g, w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
  name = name.replace(/(\w)'S\b/g, "$1's")
  return name
}

function onAudiobookFilesChange(event) {
  const files = Array.from(event.target.files).filter(f =>
    /\.(mp3|m4a)$/i.test(f.name)
  )
  if (!files.length) return
  files.sort((a, b) => a.name.localeCompare(b.name))

  // Auto-populate book name from folder (webkitRelativePath = "FolderName/file.mp3")
  if (!uploadName.value && files[0].webkitRelativePath) {
    const folder = files[0].webkitRelativePath.split('/')[0]
    uploadName.value = deriveBookName(folder)
  }

  uploadChapters.value = files.map(f => ({ file: f, name: deriveChapterName(f.name) }))
  // Reset the input so the same folder can be re-selected if needed
  event.target.value = ''
}

async function loadSongs() {
  loadingSongs.value = true
  songError.value = ''
  try {
    const res = await fetch(`${API}/songs`)
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    songs.value = data.songs
  } catch (e) {
    songError.value = `Failed to load songs: ${e.message}`
  } finally {
    loadingSongs.value = false
  }
}

function onFileChange(event) {
  uploadFile.value = event.target.files[0] || null
}

// Low-frequency background poll to keep offline last-seen and mode badge fresh
let bgPollTimer = null
function startBgPoll() {
  bgPollTimer = setInterval(async () => {
    if (!nfcPollTimer) await pollNfcStatus()
  }, 2000)
}

async function uploadSong() {
  uploadError.value = ''
  if (!uploadName.value) return
  if (uploadType.value === 'track' && !uploadFile.value) return
  if (uploadType.value === 'audiobook' && uploadChapters.value.length === 0) return

  uploading.value = true
  if (bgPollTimer) { clearInterval(bgPollTimer); bgPollTimer = null }
  nfcBannerDismissed.value = false
  try {
    const form = new FormData()
    form.append('type', uploadType.value)
    form.append('name', uploadName.value)
    if (uploadImageFile.value) form.append('image', uploadImageFile.value)

    if (uploadType.value === 'audiobook') {
      form.append('chapter_names', JSON.stringify(uploadChapters.value.map(ch => ch.name)))
      for (const ch of uploadChapters.value) {
        form.append('files[]', ch.file)
      }
    } else {
      form.append('file', uploadFile.value)
    }

    const res = await fetch(`${API}/songs`, { method: 'POST', body: form })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Upload failed')

    // Reset form
    uploadName.value = ''
    uploadFile.value = null
    uploadImageFile.value = null
    uploadChapters.value = []
    showUpload.value = false

    if (nfcStatus.value.hw_error) {
      // NFC unavailable — song is saved, just reload the list
      await loadSongs()
    } else {
      // NFC available — poll for write status
      await pollNfcStatus()
      startNfcPoll()
    }
  } catch (e) {
    uploadError.value = e.message
  } finally {
    uploading.value = false
    startBgPoll()
  }
}

async function playSong(song) {
  if (!savedSpeaker.value) return
  playingId.value = song.id
  playStatus.value = ''
  songError.value = ''
  try {
    const res = await fetch(`${API}/play`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: song.id }),
    })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    playStatus.value = data.message
    setTimeout(pollPlayback, 3000)
  } catch (e) {
    songError.value = `Play error: ${e.message}`
  } finally {
    playingId.value = null
  }
}

async function playChapter(song, chapterIndex) {
  if (!savedSpeaker.value) return
  playingId.value = song.id
  playStatus.value = ''
  songError.value = ''
  try {
    const res = await fetch(`${API}/play`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: song.id, chapter_index: chapterIndex }),
    })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    playStatus.value = data.message
    setTimeout(pollPlayback, 3000)
  } catch (e) {
    songError.value = `Play error: ${e.message}`
  } finally {
    playingId.value = null
  }
}

async function retagSong(song) {
  retaggingId.value = song.id
  nfcBannerDismissed.value = false
  try {
    const res = await fetch(`${API}/songs/${song.id}/retag`, { method: 'POST' })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    await pollNfcStatus()
    startNfcPoll()
  } catch (e) {
    songError.value = `Retag error: ${e.message}`
  } finally {
    retaggingId.value = null
  }
}

async function toggleOffline() {
  try {
    await fetch(`${API}/offline/toggle`, { method: 'POST' })
    await pollNfcStatus()
  } catch (_) {}
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

async function deleteSong(song) {
  const msg = song.type === 'audiobook'
    ? `Delete audiobook "${song.name}"?\n\nThis will permanently delete the entire folder and all ${song.chapters.length} chapter files from the Pi.`
    : `Delete "${song.name}"?`
  if (!confirm(msg)) return
  deletingId.value = song.id
  songError.value = ''
  try {
    const res = await fetch(`${API}/songs/${song.id}`, { method: 'DELETE' })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    songs.value = songs.value.filter(s => s.id !== song.id)
  } catch (e) {
    songError.value = `Delete error: ${e.message}`
  } finally {
    deletingId.value = null
  }
}

async function clearProgress(song) {
  if (!confirm(`Clear saved position for "${song.name}"?`)) return
  try {
    const res = await fetch(`${API}/songs/${song.id}/progress`, { method: 'DELETE' })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    const s = songs.value.find(s => s.id === song.id)
    if (s) delete s.progress
  } catch (e) {
    songError.value = `Clear progress error: ${e.message}`
  }
}

onMounted(async () => {
  await Promise.all([loadConfig(), loadSpeakers(), loadSongs()])
  await pollNfcStatus()
  startBgPoll()
  startPlaybackPoll()
  checkForUpdates()
})

onUnmounted(() => {
  stopNfcPoll()
  if (bgPollTimer) clearInterval(bgPollTimer)
  if (playbackPollTimer) { clearTimeout(playbackPollTimer); playbackPollTimer = null }
})
</script>

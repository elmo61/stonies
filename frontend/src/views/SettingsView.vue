<template>
  <div class="page" :class="{ 'has-player': store.local }">
    <h1 class="page-title">Settings</h1>

    <h2 class="section-label">Playback</h2>
    <div class="list">
      <button class="list-row" @click="store.ui.speakerSheet = true">
        <span class="grow"><span class="title">Speaker</span></span>
        <span class="value">{{ store.config.speaker || 'Not chosen' }}</span>
        <Icon name="chevronRight" :size="16" :stroke="2.4" class="chev" />
      </button>
      <button class="list-row" @click="sheet = 'cast'">
        <span class="grow"><span class="title">Cast player</span></span>
        <span class="value">{{ castLabel }}</span>
        <Icon name="chevronRight" :size="16" :stroke="2.4" class="chev" />
      </button>
      <button class="list-row" @click="openBedtime">
        <span class="grow"><span class="title">Bedtime</span></span>
        <span class="value">{{ bedtimeLabel }}</span>
        <Icon name="chevronRight" :size="16" :stroke="2.4" class="chev" />
      </button>
    </div>

    <h2 class="section-label">Stickers</h2>
    <div class="list">
      <button class="list-row" role="switch" :aria-checked="store.nfc.offline ? 'true' : 'false'" @click="toggleQuiet">
        <span class="grow">
          <span class="title">Quiet mode</span>
          <span class="sub">{{ store.nfc.offline ? 'On: stickers are recognised but nothing plays' : 'Test stickers without playing anything' }}</span>
        </span>
        <span class="switch"></span>
      </button>
    </div>

    <h2 class="section-label">This box</h2>
    <div class="list">
      <RouterLink to="/status" class="list-row">
        <span class="grow"><span class="title">{{ boxName() }}</span></span>
        <span class="value st-health" :class="health.level">{{ health.label }}</span>
        <Icon name="chevronRight" :size="16" :stroke="2.4" class="chev" />
      </RouterLink>
      <button class="list-row" @click="openUpdates">
        <span class="grow"><span class="title">Updates</span></span>
        <span class="value">{{ updateLabel }}</span>
        <Icon name="chevronRight" :size="16" :stroke="2.4" class="chev" />
      </button>
    </div>

    <h2 class="section-label">Library</h2>
    <div class="list">
      <button class="list-row" @click="openSync">
        <span class="grow"><span class="title">Copy from another box</span><span class="sub">Pulls songs this box doesn't have yet</span></span>
        <Icon name="chevronRight" :size="16" :stroke="2.4" class="chev" />
      </button>
      <button class="list-row" :disabled="importing" @click="runImport">
        <span class="grow"><span class="title">{{ importing ? 'Importing…' : 'Import from the box’s import folder' }}</span><span class="sub">Adds files copied into music_import/</span></span>
        <Icon name="chevronRight" :size="16" :stroke="2.4" class="chev" />
      </button>
    </div>

    <button v-if="store.installPrompt" class="card install" @click="install">
      <Icon name="download" :size="24" :stroke="2.2" class="install-icon" />
      <span class="grow">
        <strong>Install Stonies</strong>
        <span>Opens full-screen like an app, even when the box is offline</span>
      </span>
    </button>
    <button v-else-if="!installed" class="card install" @click="sheet = 'install'">
      <Icon name="download" :size="24" :stroke="2.2" class="install-icon" />
      <span class="grow">
        <strong>Add Stonies to your home screen</strong>
        <span>An icon on your phone that opens this box</span>
      </span>
    </button>

    <p v-if="disk" class="muted set-foot">{{ disk.free_gb }} GB free of {{ disk.total_gb }} GB<template v-if="update"> · {{ update.current_version }}</template></p>

    <!-- Cast player -->
    <BottomSheet v-if="sheet === 'cast'" title="Cast player" @close="sheet = null">
      <div role="radiogroup" aria-label="Cast player">
        <button class="choice" role="radio" :aria-checked="store.config.cast_receiver !== 'default' ? 'true' : 'false'" @click="setCast('stonies')">
          <span class="grow"><span class="title">Stonies player</span><span class="sub">Cover art and chapter names on screens, live audiobook position. Recommended.</span></span>
          <span class="radio-dot"></span>
        </button>
        <button class="choice" role="radio" :aria-checked="store.config.cast_receiver === 'default' ? 'true' : 'false'" @click="setCast('default')">
          <span class="grow"><span class="title">Google standard player</span><span class="sub">Use if a speaker won't open the Stonies player.</span></span>
          <span class="radio-dot"></span>
        </button>
      </div>
      <p class="muted sheet-note">Applies from the next thing you play.</p>
    </BottomSheet>

    <!-- Bedtime -->
    <BottomSheet v-if="sheet === 'bedtime'" title="Bedtime" @close="sheet = null">
      <button class="choice" role="switch" :aria-checked="bed.enabled ? 'true' : 'false'" @click="bed.enabled = !bed.enabled">
        <span class="grow"><span class="title">Stop playing automatically at night</span><span class="sub">Anything started after the time below stops on its own</span></span>
        <span class="switch"></span>
      </button>
      <div v-if="bed.enabled" class="bed-grid">
        <label class="field"><span>Starts after</span><input v-model="bed.after_time" class="input" type="time" /></label>
        <label class="field"><span>Stop after (minutes)</span><input v-model.number="bed.duration_minutes" class="input" type="number" min="1" max="240" inputmode="numeric" /></label>
      </div>
      <button class="btn btn-primary btn-lg btn-block sheet-gap" :disabled="saving" @click="saveBedtime">{{ saving ? 'Saving…' : 'Save' }}</button>
    </BottomSheet>

    <!-- Updates -->
    <BottomSheet v-if="sheet === 'updates'" title="Updates" @close="sheet = null">
      <div role="radiogroup" aria-label="Release channel">
        <button class="choice" role="radio" :aria-checked="channel === 'stable' ? 'true' : 'false'" @click="setChannel('stable')">
          <span class="grow"><span class="title">Stable</span><span class="sub">Tested releases. Recommended.</span></span>
          <span class="radio-dot"></span>
        </button>
        <button class="choice" role="radio" :aria-checked="channel === 'beta' ? 'true' : 'false'" @click="setChannel('beta')">
          <span class="grow"><span class="title">Beta</span><span class="sub">Newest features first, may be rough</span></span>
          <span class="radio-dot"></span>
        </button>
      </div>
      <p class="muted sheet-note">{{ update ? `Running ${update.current_version}` : 'Checking for updates…' }}</p>
      <template v-if="update && update.updates_available">
        <p v-if="update.can_self_update === false" class="sheet-note">{{ update.manual_reason || 'This update needs bash update.sh on the box.' }}</p>
        <button v-else class="btn btn-primary btn-lg btn-block" :disabled="updating" @click="runUpdate">{{ updating ? 'Updating… back in about 30 seconds' : 'Update now' }}</button>
      </template>
      <p v-else-if="update" class="sheet-note ok-note">Up to date.</p>
    </BottomSheet>

    <!-- Copy from another box -->
    <BottomSheet v-if="sheet === 'sync'" title="Copy from another box" @close="closeSync">
      <template v-if="sync.step === 'input'">
        <label class="field">
          <span>Other box's name or address</span>
          <input v-model="sync.peer" class="input" type="text" placeholder="stonies-rose.local" autocapitalize="off" autocorrect="off" @keyup.enter="syncPreview" />
        </label>
        <p class="muted sheet-note">For example <strong>stonies-rose.local</strong> or <strong>192.168.1.20</strong>. Nothing is copied until you confirm.</p>
        <button class="btn btn-primary btn-lg btn-block" :disabled="!sync.peer.trim() || sync.busy" @click="syncPreview">{{ sync.busy ? 'Looking…' : 'See what’s missing' }}</button>
      </template>
      <template v-else-if="sync.step === 'preview'">
        <p v-if="!sync.missing.length" class="sheet-note ok-note">This box already has everything from {{ sync.peer }}.</p>
        <template v-else>
          <p class="sheet-note">{{ sync.missing.length }} to copy from <strong>{{ sync.peer }}</strong>:</p>
          <ul class="sync-list">
            <li v-for="m in sync.missing" :key="m.id">{{ m.name }} <span class="muted">· {{ m.type === 'audiobook' ? `story, ${m.chapter_count} ch` : 'song' }}</span></li>
          </ul>
          <button class="btn btn-primary btn-lg btn-block" @click="syncPull">Copy {{ sync.missing.length }}</button>
        </template>
        <button class="btn btn-ghost btn-block" @click="sync.step = 'input'">Back</button>
      </template>
      <template v-else>
        <p class="sheet-note">{{ sync.status.status === 'running' ? `Copying ${sync.status.done} of ${sync.status.total}…` : 'Finished.' }}</p>
        <div class="bar sync-bar"><span :style="{ width: syncPct + '%' }"></span></div>
        <p v-if="sync.status.current && sync.status.status === 'running'" class="muted sheet-note">{{ sync.status.current }}</p>
        <p v-if="sync.status.errors?.length" class="sheet-note warn-note">{{ sync.status.errors.length }} couldn't be copied: {{ sync.status.errors.join('; ') }}</p>
        <button v-if="sync.status.status !== 'running'" class="btn btn-primary btn-lg btn-block" @click="closeSync">Done</button>
      </template>
    </BottomSheet>

    <!-- Add to home screen -->
    <BottomSheet v-if="sheet === 'install'" title="Add to home screen" @close="sheet = null">
      <template v-if="isIOS">
        <p class="sheet-note">Then Stonies opens full-screen from an icon, like any other app.</p>
        <ol class="install-steps">
          <li>Tap the <strong>Share</strong> button at the bottom of Safari.</li>
          <li>Choose <strong>Add to Home Screen</strong>.</li>
          <li>Tap <strong>Add</strong>.</li>
        </ol>
      </template>
      <template v-else>
        <p class="sheet-note">Then a Stonies icon on your home screen opens this box.</p>
        <ol class="install-steps">
          <li>Open Chrome's <strong>⋮ menu</strong>.</li>
          <li>Choose <strong>Add to home screen</strong>.</li>
          <li>Choose <strong>Create shortcut</strong>, then <strong>Add</strong>.</li>
        </ol>
        <p class="muted sheet-note">If Chrome offers <strong>Install</strong> and then says the app can't be installed, that's expected: a full install needs the box to use a secure (https) address, which is on the to-do list. The shortcut works fine meanwhile.</p>
      </template>
      <p class="muted sheet-note">Each box has its own address, so add one icon per box.</p>
    </BottomSheet>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import { api } from '../api'
import { store, boxName, health, toggleQuiet, saveConfig, loadSongs, toast, applyUpdate } from '../store'
import BottomSheet from '../components/BottomSheet.vue'
import Icon from '../components/Icon.vue'

const sheet = ref(null)
const saving = ref(false)
const importing = ref(false)
const updating = ref(false)
const disk = ref(null)
const update = ref(null)
const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent)
// Already running as an installed app (or a full-screen home-screen icon)?
const installed = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true

async function install() {
  const prompt = store.installPrompt
  if (!prompt) return
  prompt.prompt()
  const { outcome } = await prompt.userChoice
  store.installPrompt = null
  if (outcome === 'accepted') toast('Stonies is installed', 'ok')
}

const castLabel = computed(() => ({ default: 'Google standard', own: 'Custom' }[store.config.cast_receiver] || 'Stonies player'))
const bedtimeLabel = computed(() => {
  const st = store.config.sleep_timer
  return st?.enabled ? `Stops ${st.duration_minutes} min after ${st.after_time}` : 'Off'
})
const channel = computed(() => update.value?.channel || store.config.update_channel || 'stable')
const updateLabel = computed(() => {
  if (!update.value) return '…'
  const ch = channel.value === 'beta' ? 'Beta' : 'Stable'
  return update.value.updates_available ? `${ch} · update ready` : `${ch} · up to date`
})

async function setCast(mode) {
  try {
    await saveConfig({ cast_receiver: mode })
    toast(mode === 'default' ? 'Using Google’s standard player' : 'Using the Stonies player', 'ok')
  } catch (e) { toast(`Couldn't save: ${e.message}`, 'error') }
}

// Bedtime
const bed = reactive({ enabled: false, after_time: '19:00', duration_minutes: 60 })
function openBedtime() {
  Object.assign(bed, { enabled: false, after_time: '19:00', duration_minutes: 60 }, store.config.sleep_timer || {})
  sheet.value = 'bedtime'
}
async function saveBedtime() {
  saving.value = true
  try {
    await saveConfig({ sleep_timer: { ...bed } })
    toast('Bedtime saved', 'ok')
    sheet.value = null
  } catch (e) { toast(`Couldn't save: ${e.message}`, 'error') }
  finally { saving.value = false }
}

// Updates
async function loadUpdate() {
  try { update.value = await api.get('/update/status') } catch (_) {}
}
function openUpdates() { sheet.value = 'updates'; loadUpdate() }
async function setChannel(ch) {
  try {
    await saveConfig({ update_channel: ch })
    update.value = null
    await loadUpdate()
  } catch (e) { toast(`Couldn't change channel: ${e.message}`, 'error') }
}
async function runUpdate() {
  updating.value = true
  try { await applyUpdate() } catch (e) { toast(`Update failed: ${e.message}`, 'error'); updating.value = false }
}

// Import folder
async function runImport() {
  importing.value = true
  try {
    const r = await api.post('/import/scan')
    await loadSongs()
    const n = r.imported?.length || 0
    toast(n ? `Imported ${n} item${n === 1 ? '' : 's'}` : 'Nothing new in the import folder', n ? 'ok' : 'info')
    if (r.errors?.length) toast(`${r.errors.length} couldn't be imported: ${r.errors.join('; ')}`, 'error')
  } catch (e) { toast(`Import failed: ${e.message}`, 'error') }
  finally { importing.value = false }
}

// Copy from another box
const sync = reactive({ step: 'input', peer: '', busy: false, missing: [], status: {} })
let syncTimer = null
const syncPct = computed(() => sync.status.total ? Math.round((sync.status.done / sync.status.total) * 100) : 0)
function openSync() {
  Object.assign(sync, { step: 'input', peer: store.config.sync_peer || '', busy: false, missing: [], status: {} })
  sheet.value = 'sync'
}
async function syncPreview() {
  sync.busy = true
  try {
    const r = await api.post('/sync/preview', { peer: sync.peer.trim() })
    sync.peer = r.peer
    sync.missing = r.missing || []
    sync.step = 'preview'
  } catch (e) { toast(e.message, 'error') }
  finally { sync.busy = false }
}
async function syncPull() {
  try {
    await api.post('/sync/pull', { peer: sync.peer })
    sync.step = 'pulling'
    pollSync()
  } catch (e) { toast(e.message, 'error') }
}
async function pollSync() {
  try { sync.status = await api.get('/sync/status') } catch (_) {}
  if (sync.status.status === 'running') syncTimer = setTimeout(pollSync, 2000)
  else loadSongs()
}
function closeSync() {
  clearTimeout(syncTimer)
  sheet.value = null
}

onMounted(async () => {
  try { disk.value = await api.get('/disk') } catch (_) {}
  loadUpdate()
})
</script>

<style scoped>
.list-row:disabled { opacity: 0.6; }
.st-health.ok { color: var(--ok-ink); font-weight: 700; }
.st-health.warn, .st-health.offline { color: #8A4F00; font-weight: 700; }
.install { margin-top: 18px; width: 100%; min-height: 64px; padding: 10px 16px; display: flex; align-items: center; gap: 14px; background: var(--navy); color: #fff; text-align: left; }
.install-icon { color: var(--amber); flex-shrink: 0; }
.install .grow { display: flex; flex-direction: column; gap: 2px; }
.install .grow span { font-size: 13px; color: var(--navy-ink); }
.set-foot { font-size: 13px; text-align: center; margin: 18px 0 0; }
.sheet-note { font-size: 14px; margin: 12px 4px; }
.ok-note { color: var(--ok-ink); font-weight: 700; }
.warn-note { color: #8A4F00; }
.sheet-gap { margin-top: 14px; }
.bed-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }
.sync-list { margin: 0 0 12px; padding-left: 20px; max-height: 40vh; overflow-y: auto; font-size: 15px; }
.sync-list li { padding: 4px 0; }
.sync-bar { height: 8px; margin: 4px 4px 0; }
.install-steps { margin: 0 0 8px; padding-left: 22px; display: flex; flex-direction: column; gap: 8px; font-size: 15px; }
</style>

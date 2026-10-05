<template>
  <div class="page">
    <div class="st-head">
      <RouterLink to="/" class="icon-btn" aria-label="Back to the library"><Icon name="back" /></RouterLink>
      <h1 class="display st-title">Is it working?</h1>
    </div>
    <p class="page-sub">{{ boxName() }}<template v-if="store.hostname && store.hostname !== boxName()"> · {{ store.hostname }}</template></p>

    <div class="list st-list">
      <div v-for="c in checks" :key="c.title" class="list-row">
        <span class="badge-icon" :class="c.level"><Icon :name="c.level === 'ok' ? 'check' : c.level === 'warn' ? 'alert' : 'refresh'" :size="18" :stroke="2.6" /></span>
        <span class="grow">
          <span class="title st-strong">{{ c.title }}</span>
          <span class="sub">{{ c.detail }}</span>
        </span>
        <span class="word" :class="c.level">{{ c.word }}</span>
      </div>
    </div>

    <div v-if="update && update.updates_available" class="card st-update">
      <span class="grow">
        <strong>An update is ready</strong>
        <span class="muted">{{ update.can_self_update === false ? (update.manual_reason || 'This one needs bash update.sh on the box.') : 'Takes about 30 seconds. Anything playing on a speaker keeps playing.' }}</span>
      </span>
      <button v-if="update.can_self_update !== false" class="btn btn-primary" :disabled="updating" @click="applyUpdate">{{ updating ? 'Updating…' : 'Update' }}</button>
    </div>

    <p class="muted st-foot">
      <template v-if="lastSticker">Last sticker: {{ lastSticker }}<br></template>
      <template v-if="update">{{ update.channel === 'beta' ? 'Beta' : 'Stable' }} · {{ update.current_version }}</template>
    </p>

    <button class="btn btn-dark btn-lg btn-block" :disabled="checking" @click="checkAll">
      <Icon name="refresh" :size="18" /> {{ checking ? 'Checking…' : 'Check again' }}
    </button>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { api } from '../api'
import { store, boxName, refreshNfc, loadConfig, toast, applyUpdate as doUpdate } from '../store'
import Icon from '../components/Icon.vue'

const wifi = ref(null)
const disk = ref(null)
const update = ref(null)
const found = ref(null)        // speakers found by the latest scan (null = still looking)
const lastSticker = ref('')
const checking = ref(false)
const updating = ref(false)

const ok = (title, detail) => ({ title, detail, level: 'ok', word: 'OK' })
const warn = (title, detail, word = 'CHECK') => ({ title, detail, level: 'warn', word })
const pending = (title, detail) => ({ title, detail, level: 'info', word: '…' })

const checks = computed(() => {
  const list = []
  const w = wifi.value
  if (!w) list.push(pending('Wi-Fi', 'Checking…'))
  else if (!w.available) list.push(ok('Network', 'Connected (no Wi-Fi details: wired, or not a Pi)'))
  else if (!w.connected) list.push(warn('Wi-Fi', 'Not connected to Wi-Fi', 'OFF'))
  else if (w.strength === 'weak') list.push(warn('Wi-Fi', `Weak signal (${w.quality_pct}%). Stories may stutter: move the box nearer a Wi-Fi point.`, 'WEAK'))
  else list.push(ok('Wi-Fi', `${w.strength === 'strong' ? 'Strong' : 'OK'} signal (${w.quality_pct}%)`))

  const n = store.nfc
  if (n.hw_error) list.push(warn('Sticker reader', `Not detected. ${n.hw_error}`, 'OFF'))
  else if (n.nfc_heartbeat_age == null) list.push(pending('Sticker reader', 'Checking…'))
  else if (n.nfc_heartbeat_age > 15) list.push(warn('Sticker reader', `Not responding (last check ${Math.round(n.nfc_heartbeat_age)}s ago)`, 'STUCK'))
  else list.push(ok('Sticker reader', `Ready · checked ${Math.round(n.nfc_heartbeat_age)}s ago`))
  if (n.offline) list.push(warn('Quiet mode', 'On: stickers are recognised but nothing plays', 'ON'))

  const sp = store.config.speaker
  if (!sp) list.push(warn('Speaker', 'No speaker chosen yet', 'NONE'))
  else if (found.value === null) list.push(pending('Speaker', `Looking for ${sp}…`))
  else if (found.value.includes(sp)) list.push(ok('Speaker', `${sp} found`))
  else list.push(warn('Speaker', `${sp} not found. Is it on, and on the same Wi-Fi?`, 'MISSING'))

  const mode = store.config.cast_receiver
  list.push(ok('Cast player', mode === 'default' ? 'Google standard player' : mode === 'own' ? 'Custom receiver' : 'Stonies player'))

  const d = disk.value
  if (d) {
    const detail = `${d.free_gb} GB free of ${d.total_gb} GB`
    list.push(d.free_gb < 1 ? warn('Storage', `Nearly full: ${detail}`, 'LOW') : ok('Storage', detail))
  }
  return list
})

async function checkAll() {
  checking.value = true
  found.value = null
  await Promise.all([
    refreshNfc(),
    loadConfig(),
    api.get('/wifi').then((d) => { wifi.value = d }).catch(() => { wifi.value = { available: false } }),
    api.get('/disk').then((d) => { disk.value = d }).catch(() => {}),
    api.get('/update/status').then((d) => { update.value = d }).catch(() => {}),
    api.get('/log').then((d) => {
      const line = (d.lines || []).find((l) => l.includes('(NFC)'))
      if (line) {
        const [stamp, msg] = line.split(' | ')
        lastSticker.value = `${msg.replace(/ started playing \(NFC\)$/, '').replace(/^"|"$/g, '')} at ${stamp.slice(11, 16)}`
      }
    }).catch(() => {}),
    api.get('/speakers').then((d) => { found.value = d.speakers || [] }).catch(() => { found.value = [] }),
  ])
  checking.value = false
}

async function applyUpdate() {
  updating.value = true
  try {
    await doUpdate()
  } catch (e) {
    toast(`Update failed: ${e.message}`, 'error')
    updating.value = false
  }
}

onMounted(checkAll)
</script>

<style scoped>
.st-head { display: flex; align-items: center; gap: 4px; padding-top: 4px; margin-left: -8px; }
.st-title { font-size: 24px; }
.st-list { margin-top: 14px; }
.st-strong { font-weight: 700 !important; }
.st-update { margin-top: 12px; padding: 14px 16px; display: flex; align-items: center; gap: 12px; background: var(--blue-soft); }
.st-update .grow { flex: 1; display: flex; flex-direction: column; gap: 2px; font-size: 14px; }
.st-foot { font-size: 13px; margin: 14px 4px; }
</style>

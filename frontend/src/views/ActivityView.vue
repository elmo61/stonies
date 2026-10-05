<template>
  <div class="page" :class="{ 'has-player': store.local }">
    <h1 class="page-title">Activity</h1>
    <p class="page-sub">What {{ boxName() }} has been up to</p>

    <div class="tabs" role="tablist" aria-label="Show">
      <button v-for="t in tabs" :key="t.id" role="tab" class="tab" :aria-selected="filter === t.id ? 'true' : 'false'" @click="filter = t.id">{{ t.label }}</button>
    </div>

    <p v-if="loading" class="empty">Loading…</p>
    <p v-else-if="!shown.length" class="empty">{{ filter === 'problems' ? 'No problems logged. Good news!' : 'Nothing logged yet.' }}</p>

    <template v-for="ev in shown" :key="ev.key">
      <h2 v-if="ev.showDay" class="section-label">{{ ev.dayLabel }}</h2>
      <div class="ev card">
        <span class="ev-icon" :class="`k-${ev.kind}`"><Icon :name="ev.icon" :size="20" /></span>
        <span class="ev-text">
          <span class="ev-title">{{ ev.title }}</span>
          <span v-if="ev.detail" class="ev-detail">{{ ev.detail }}</span>
        </span>
        <span class="ev-time">{{ ev.time }}</span>
      </div>
    </template>

    <button class="btn btn-ghost btn-block tech-toggle" :aria-expanded="String(showTech)" @click="showTech = !showTech">
      {{ showTech ? 'Hide technical log' : 'Show technical log' }}
    </button>
    <div v-if="showTech" class="card tech">
      <p v-if="!techLines.length" class="muted">No recent entries.</p>
      <div v-for="l in techLines" :key="l.seq" class="tech-line"><span>{{ l.time }}</span>{{ l.msg }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { api } from '../api'
import { store, boxName, refreshNfc } from '../store'
import Icon from '../components/Icon.vue'

const filter = ref('all')
const loading = ref(true)
const showTech = ref(false)
const events = ref([])
const tabs = [
  { id: 'all', label: 'Everything' },
  { id: 'stickers', label: 'Stickers' },
  { id: 'problems', label: 'Problems' },
]

// Turn one activity.log line ("2026-10-02 18:42:01 | message") into a timeline entry
function parse(line, i) {
  const [stamp, ...rest] = line.split(' | ')
  const msg = rest.join(' | ').trim()
  const date = stamp.slice(0, 10)
  const time = stamp.slice(11, 16)
  const quoted = (msg.match(/^"(.+)"/) || [])[1]
  let kind = 'info', icon = 'activity', title = msg, detail = ''
  if (/\(NFC\)$/.test(msg)) {
    kind = 'sticker'; icon = 'sticker'; title = `Sticker: ${quoted || 'a song'}`; detail = 'Started playing'
  } else if (/\(web\)$/.test(msg)) {
    kind = 'app'; icon = 'phone'; title = quoted || 'Played'; detail = 'Played from the app'
  } else if (/sleep timer/i.test(msg)) {
    kind = 'bedtime'; icon = 'moon'; title = 'Bedtime: stopped playing'
  } else if (/ finished$/.test(msg)) {
    kind = 'done'; icon = 'check'; title = quoted || 'Finished'; detail = 'Finished'
  } else if (/ stopped$/.test(msg) || /^Playback stopped/.test(msg)) {
    kind = 'done'; icon = 'stop'; title = quoted || 'Stopped'; detail = 'Stopped'
  } else if (/^Update applied/.test(msg)) {
    kind = 'update'; icon = 'download'; title = 'Updated'; detail = (msg.match(/\((.+)\)/) || [])[1] || ''
  } else if (/unrecoverable|stale|fail|error/i.test(msg)) {
    kind = 'problem'; icon = 'alert'; title = 'Problem'; detail = msg
  } else if (/recovered/i.test(msg)) {
    kind = 'problem'; icon = 'check'; title = 'Fixed itself'; detail = msg
  } else if (/^NFC reader started/.test(msg)) {
    kind = 'info'; icon = 'restart'; title = 'Box started'
  } else if (/^Sync from/.test(msg)) {
    kind = 'info'; icon = 'sync'; title = 'Copied songs'; detail = msg.replace(/^Sync from /, 'From ')
  }
  return { key: i, date, time, kind, icon, title, detail }
}

function dayLabel(date) {
  const d = new Date(`${date}T00:00:00`)
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const diff = Math.round((today - d) / 86400000)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  return d.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' })
}

const shown = computed(() => {
  const list = events.value.filter((e) =>
    filter.value === 'all' ||
    (filter.value === 'stickers' ? e.kind === 'sticker' : e.kind === 'problem'))
  let last = null
  return list.slice(0, 150).map((e) => {
    const showDay = e.date !== last
    last = e.date
    return { ...e, showDay, dayLabel: dayLabel(e.date) }
  })
})

const techLines = computed(() => [...(store.nfc.log || [])].reverse())

onMounted(async () => {
  refreshNfc()
  try {
    const d = await api.get('/log')
    events.value = (d.lines || []).map(parse)
  } catch (_) {}
  loading.value = false
})
</script>

<style scoped>
.ev { display: flex; gap: 12px; align-items: flex-start; padding: 10px 12px; margin-bottom: 6px; border-radius: 16px; }
.ev-icon { width: 38px; height: 38px; flex-shrink: 0; border-radius: 12px; display: grid; place-items: center; background: #EEF0F5; color: #3A4459; }
.ev-icon.k-sticker { background: var(--blue-soft); color: var(--blue-ink); }
.ev-icon.k-bedtime { background: #ECE6F7; color: #5B3A92; }
.ev-icon.k-app { background: #E6F2EF; color: #1F5C50; }
.ev-icon.k-problem { background: var(--amber-soft); color: #8A4F00; }
.ev-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.ev-title { font-weight: 700; font-size: 15px; line-height: 1.3; }
.ev-detail { font-size: 13px; color: var(--muted); line-height: 1.35; overflow-wrap: anywhere; }
.ev-time { font-size: 13px; font-weight: 700; color: var(--muted); padding-top: 2px; }
.tech-toggle { margin-top: 10px; }
.tech { padding: 12px; font-family: ui-monospace, Consolas, monospace; font-size: 12px; max-height: 50vh; overflow-y: auto; }
.tech-line { padding: 3px 0; border-bottom: 1px solid var(--line-soft); overflow-wrap: anywhere; }
.tech-line span { color: var(--muted); margin-right: 8px; }
</style>

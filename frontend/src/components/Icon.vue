<template>
  <svg
    :width="size" :height="size" viewBox="0 0 24 24"
    :fill="filled ? 'currentColor' : 'none'" stroke="currentColor"
    :stroke-width="stroke" stroke-linecap="round" stroke-linejoin="round"
    aria-hidden="true" focusable="false"
    v-html="paths[name] || ''"
  />
</template>

<script setup>
// Small inline line-icon set. The markup is static and ours, so v-html is safe.
const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 22 },
  stroke: { type: [Number, String], default: 2 },
})

const FILLED = new Set(['play', 'pause', 'stop', 'more'])
const filled = FILLED.has(props.name)

const paths = {
  play: '<polygon points="8 4 20 12 8 20 8 4" stroke="none"/>',
  pause: '<rect x="6" y="4" width="4.5" height="16" rx="1.2" stroke="none"/><rect x="13.5" y="4" width="4.5" height="16" rx="1.2" stroke="none"/>',
  stop: '<rect x="5" y="5" width="14" height="14" rx="2.5" stroke="none"/>',
  more: '<circle cx="12" cy="5" r="2" stroke="none"/><circle cx="12" cy="12" r="2" stroke="none"/><circle cx="12" cy="19" r="2" stroke="none"/>',
  chevronDown: '<polyline points="6 9 12 15 18 9"/>',
  chevronRight: '<polyline points="9 6 15 12 9 18"/>',
  back: '<polyline points="15 6 9 12 15 18"/>',
  close: '<line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/>',
  plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  search: '<circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  speaker: '<rect x="6" y="2" width="12" height="20" rx="3"/><circle cx="12" cy="14" r="3.5"/><circle cx="12" cy="6.5" r="0.8"/>',
  screen: '<rect x="2" y="4" width="20" height="13" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/>',
  phone: '<rect x="7" y="2" width="10" height="20" rx="2"/><line x1="11" y1="18" x2="13" y2="18"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
  check: '<polyline points="20 6 9 17 4 12"/>',
  alert: '<path d="M12 3l10 18H2z"/><line x1="12" y1="10" x2="12" y2="14"/><line x1="12" y1="17.5" x2="12" y2="17.5"/>',
  sticker: '<circle cx="5" cy="12" r="1.6" fill="currentColor"/><path d="M9 8.5a5 5 0 0 1 0 7"/><path d="M12.5 6a9 9 0 0 1 0 12"/><path d="M16 3.5a13 13 0 0 1 0 17"/>',
  pencil: '<path d="M4 20h4L19 9l-4-4L4 16z"/><line x1="13" y1="7" x2="17" y2="11"/>',
  restart: '<polyline points="3 4 3 10 9 10"/><path d="M3.6 15a8.5 8.5 0 1 0 1.9-8.6L3 10"/>',
  refresh: '<polyline points="21 4 21 10 15 10"/><path d="M20.4 15a8.5 8.5 0 1 1-1.9-8.6L21 10"/>',
  trash: '<polyline points="4 7 20 7"/><path d="M6 7l1 13h10l1-13"/><path d="M9 7V4h6v3"/>',
  library: '<rect x="3" y="4" width="5" height="16" rx="1"/><rect x="10" y="4" width="5" height="16" rx="1"/><path d="M17.3 5.4l3.2.9-3.7 13.5-3.2-.9z"/>',
  activity: '<polyline points="3 12 7 12 10 4 14 20 17 12 21 12"/>',
  settings: '<line x1="4" y1="7" x2="20" y2="7"/><line x1="4" y1="17" x2="20" y2="17"/><circle cx="9" cy="7" r="2.5" fill="var(--icon-knob, #fff)"/><circle cx="15" cy="17" r="2.5" fill="var(--icon-knob, #fff)"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19V5"/>',
  disc: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5"/>',
  music: '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
  folder: '<path d="M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  camera: '<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 17l-5-5-9 8"/>',
  download: '<path d="M12 3v12"/><polyline points="7 10 12 15 17 10"/><path d="M5 21h14"/>',
  wifi: '<path d="M1.5 9a15 15 0 0 1 21 0"/><path d="M5 12.5a10 10 0 0 1 14 0"/><path d="M8.5 16a5 5 0 0 1 7 0"/><line x1="12" y1="19.5" x2="12" y2="19.5"/>',
  wifiOff: '<path d="M1.5 9a15 15 0 0 1 6.3-3.6"/><path d="M12 5a15 15 0 0 1 10.5 4"/><path d="M5 12.5a10 10 0 0 1 3.5-2.1"/><path d="M15.5 10.6a10 10 0 0 1 3.5 1.9"/><path d="M8.5 16a5 5 0 0 1 7 0"/><line x1="12" y1="19.5" x2="12" y2="19.5"/><line x1="3" y1="3" x2="21" y2="21"/>',
  sync: '<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
  storage: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  bars: '<path d="M4 10v4"/><path d="M9 6v12"/><path d="M14 8v8"/><path d="M19 11v2"/>',
}
</script>

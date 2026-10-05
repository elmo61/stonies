<template>
  <Teleport to="body">
    <div class="backdrop" :style="layer ? { zIndex: 60 + layer * 4 } : null" @click="$emit('close')"></div>
    <div
      ref="panel" class="sheet" :class="{ dragging }"
      :style="{ ...(layer ? { zIndex: 61 + layer * 4 } : {}), '--drag': drag + 'px' }"
      role="dialog" aria-modal="true" :aria-label="label" tabindex="-1" @keydown.esc="$emit('close')"
    >
      <!-- Swipe this area down to close (the scrolling list below is left alone) -->
      <div
        class="sheet-grab"
        @pointerdown="onDown" @pointermove="onMove" @pointerup="onUp" @pointercancel="onUp"
        @click.capture="swallowClickAfterDrag"
      >
        <div class="sheet-handle" aria-hidden="true"><span></span></div>
        <div v-if="title" class="sheet-head">
          <h2>{{ title }}</h2>
          <slot name="head-action">
            <button class="icon-btn" aria-label="Close" @click="$emit('close')"><Icon name="close" /></button>
          </slot>
        </div>
        <slot name="top" />
      </div>
      <div class="sheet-body"><slot /></div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { lockScroll, unlockScroll } from '../scrollLock'
import Icon from './Icon.vue'

defineProps({
  title: { type: String, default: '' },
  label: { type: String, default: '' },
  layer: { type: Number, default: 0 },   // raise sheets that open on top of other sheets
})
const emit = defineEmits(['close'])

const panel = ref(null)
onMounted(() => { lockScroll(); panel.value?.focus() })
onUnmounted(unlockScroll)

// ── Swipe down to close ──
const CLOSE_AFTER = 90     // px dragged down before letting go closes the sheet
const START_AFTER = 8      // px of movement before a press becomes a drag (taps still work)
const drag = ref(0)
const dragging = ref(false)
let startY = null
let moved = false

function onDown(e) {
  if (e.pointerType === 'mouse' && e.button !== 0) return
  startY = e.clientY
  moved = false
}
function onMove(e) {
  if (startY === null) return
  const dy = e.clientY - startY
  if (!moved) {
    if (Math.abs(dy) < START_AFTER) return
    moved = true
    dragging.value = true
    e.currentTarget.setPointerCapture?.(e.pointerId)
  }
  drag.value = Math.max(0, dy)
}
function onUp() {
  if (startY === null) return
  startY = null
  dragging.value = false
  if (drag.value > CLOSE_AFTER) emit('close')
  drag.value = 0
}
// A drag that started on a button shouldn't also press it
function swallowClickAfterDrag(e) {
  if (moved) {
    e.preventDefault()
    e.stopPropagation()
    moved = false
  }
}
</script>

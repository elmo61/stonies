<template>
  <Teleport to="body">
    <div class="backdrop" :style="layer ? { zIndex: 60 + layer * 4 } : null" @click="$emit('close')"></div>
    <div ref="panel" class="sheet" :style="layer ? { zIndex: 61 + layer * 4 } : null" role="dialog" aria-modal="true" :aria-label="label" tabindex="-1" @keydown.esc="$emit('close')">
      <div class="sheet-handle" aria-hidden="true"><span></span></div>
      <div v-if="title" class="sheet-head">
        <h2>{{ title }}</h2>
        <slot name="head-action">
          <button class="icon-btn" aria-label="Close" @click="$emit('close')"><Icon name="close" /></button>
        </slot>
      </div>
      <slot name="top" />
      <div class="sheet-body"><slot /></div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Icon from './Icon.vue'

defineProps({
  title: { type: String, default: '' },
  label: { type: String, default: '' },
  layer: { type: Number, default: 0 },   // raise sheets that open on top of other sheets
})
defineEmits(['close'])

const panel = ref(null)
onMounted(() => panel.value?.focus())
</script>

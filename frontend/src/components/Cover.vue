<template>
  <div class="cover" :style="{ width: size + 'px', height: size + 'px', background: song.image_url ? '#D3D7E2' : coverColor(song.id), fontSize: Math.round(size * 0.32) + 'px', borderRadius: Math.round(size * 0.22) + 'px' }" aria-hidden="true">
    <img v-if="song.image_url" :src="song.image_url" alt="" loading="lazy" />
    <span v-else>{{ initials(song.name) }}</span>
  </div>
</template>

<script setup>
import { coverColor, initials } from '../store'

defineProps({
  song: { type: Object, required: true },
  size: { type: Number, default: 52 },
})
</script>

<template>
  <BottomSheet v-if="song" :title="`Rename ${song.type === 'album' ? 'tracks' : 'chapters'}`" :label="`Rename chapters of ${song.name}`" :layer="1" @close="close">
    <p class="muted ce-note">Leave a box empty to keep its current name.</p>
    <ol class="ce-list">
      <li v-for="(ch, i) in song.chapters" :key="ch.filename">
        <span class="ce-num">{{ i + 1 }}</span>
        <input v-model="names[i]" class="input" type="text" :placeholder="ch.name" :aria-label="`Name of chapter ${i + 1}`" />
      </li>
    </ol>
    <div class="ce-actions">
      <button class="btn btn-primary btn-lg btn-block" :disabled="saving || !changed" @click="save">{{ saving ? 'Saving…' : 'Save names' }}</button>
      <button class="btn btn-ghost btn-block" @click="close">Cancel</button>
    </div>
  </BottomSheet>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '../api'
import { store, songById, toast } from '../store'
import BottomSheet from './BottomSheet.vue'

const song = computed(() => songById(store.ui.chaptersId))
const names = ref([])
const saving = ref(false)

watch(song, (s) => { names.value = s ? s.chapters.map((c) => c.name) : [] }, { immediate: true })

const changed = computed(() => song.value && names.value.some((n, i) => n.trim() && n.trim() !== song.value.chapters[i].name))

async function save() {
  saving.value = true
  try {
    const r = await api.patch(`/songs/${song.value.id}`, { chapter_names: names.value.map((n) => n.trim()) })
    song.value.chapters = r.chapters
    toast('Names saved', 'ok')
    close()
  } catch (e) {
    toast(`Couldn't save: ${e.message}`, 'error')
  } finally {
    saving.value = false
  }
}

function close() { store.ui.chaptersId = null }
</script>

<style scoped>
.ce-note { font-size: 14px; margin: 0 4px 12px; }
.ce-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.ce-list li { display: flex; align-items: center; gap: 8px; }
.ce-num { width: 28px; flex-shrink: 0; text-align: right; font-weight: 700; color: var(--muted); }
.ce-actions { margin-top: 16px; display: flex; flex-direction: column; gap: 6px; }
</style>

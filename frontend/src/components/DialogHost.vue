<template>
  <Teleport to="body">
    <template v-if="d">
      <div class="backdrop over" @click="answer(false)"></div>
      <form class="dialog" role="alertdialog" aria-modal="true" :aria-label="d.title" @submit.prevent="answer(true)" @keydown.esc="answer(false)">
        <h2>{{ d.title }}</h2>
        <p v-if="d.message" class="muted dh-msg">{{ d.message }}</p>
        <label v-if="d.kind === 'prompt'" class="field">
          <span>{{ d.label || 'Name' }}</span>
          <input ref="input" v-model="value" class="input" type="text" required />
        </label>
        <div class="dialog-actions">
          <button ref="cancelBtn" type="button" class="btn btn-grey" @click="answer(false)">Cancel</button>
          <button type="submit" class="btn" :class="d.danger ? 'btn-danger' : 'btn-primary'">{{ d.confirmLabel }}</button>
        </div>
      </form>
    </template>
    <div v-if="store.ui.toast" class="toast" :class="store.ui.toast.kind" role="status">{{ store.ui.toast.text }}</div>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { store } from '../store'
import { lockScroll, unlockScroll } from '../scrollLock'

const d = computed(() => store.ui.dialog)
const value = ref('')
const input = ref(null)
const cancelBtn = ref(null)

watch(d, async (dlg) => {
  if (!dlg) return
  value.value = dlg.value || ''
  await nextTick()
  // Destructive confirms focus Cancel, so Enter never deletes by accident
  if (dlg.kind === 'prompt') { input.value?.focus(); input.value?.select() }
  else cancelBtn.value?.focus()
})

// Keep the page behind still while this is open
watch(() => !!d.value, (open, was) => { if (open && !was) lockScroll(); else if (!open && was) unlockScroll() })

function answer(ok) {
  const dlg = d.value
  if (!dlg) return
  store.ui.dialog = null
  if (dlg.kind === 'prompt') dlg.resolve(ok ? value.value : null)
  else dlg.resolve(ok)
}
</script>

<style scoped>
.dh-msg { margin: 0; font-size: 15px; }
</style>

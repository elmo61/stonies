<template>
  <Teleport to="body">
    <div v-if="!connection.online && !store.ui.offlineDismissed" class="off" role="alertdialog" aria-modal="true" aria-labelledby="off-title">
      <section class="card off-card">
        <div class="off-top">
          <div class="off-icon" aria-hidden="true"><Icon name="wifiOff" :size="30" /></div>
          <div>
            <h2 id="off-title" class="display">{{ name }} isn't answering</h2>
            <span class="muted">{{ lastSeenText }}</span>
          </div>
        </div>
        <ol class="off-steps">
          <li><span>1</span>Check the green light on the box is on, so you know it's powered.</li>
          <li><span>2</span>Is it close enough to a Wi-Fi point? A weak signal can knock it off.</li>
          <li><span>3</span>Still nothing? Unplug it for 10 seconds, plug it back in and give it 2 minutes.</li>
        </ol>
        <button class="btn btn-primary btn-lg btn-block" :disabled="trying" @click="retry">
          {{ trying ? 'Trying…' : 'Try again now' }}
        </button>
        <p class="muted off-auto">This screen goes away by itself when the box is back.</p>
        <button class="btn btn-ghost btn-block" @click="store.ui.offlineDismissed = true">Keep browsing the library</button>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { connection } from '../api'
import { store, boxName, refreshNfc } from '../store'
import Icon from './Icon.vue'

const trying = ref(false)
const now = ref(Date.now())
let timer = null
onMounted(() => { timer = setInterval(() => { now.value = Date.now() }, 15000) })
onUnmounted(() => clearInterval(timer))

const name = computed(() => boxName())
const lastSeenText = computed(() => {
  if (!connection.lastSeen) return 'Not reached yet'
  const mins = Math.round((now.value - connection.lastSeen.getTime()) / 60000)
  if (mins < 1) return 'Last seen moments ago'
  return `Last seen ${mins} minute${mins === 1 ? '' : 's'} ago`
})

async function retry() {
  trying.value = true
  await refreshNfc()
  trying.value = false
}
</script>

<style scoped>
.off { position: fixed; inset: 0; z-index: 72; background: rgba(244, 245, 249, 0.97); display: flex; align-items: flex-start; justify-content: center; padding: 72px 16px 16px; overflow-y: auto; }
.off-card { width: 100%; max-width: 528px; padding: 22px 20px 16px; display: flex; flex-direction: column; gap: 16px; }
.off-top { display: flex; align-items: center; gap: 14px; }
.off-top h2 { font-size: 21px; line-height: 1.2; }
.off-icon { width: 60px; height: 60px; flex-shrink: 0; border-radius: 18px; background: var(--amber-soft); color: #8A4F00; display: grid; place-items: center; }
.off-steps { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 12px; font-size: 15px; }
.off-steps li { display: flex; gap: 12px; align-items: flex-start; }
.off-steps span { width: 26px; height: 26px; flex-shrink: 0; border-radius: 50%; background: var(--blue-soft); color: var(--blue-ink); display: grid; place-items: center; font-weight: 700; font-size: 14px; }
.off-auto { margin: -6px 0 0; font-size: 13px; text-align: center; }
</style>

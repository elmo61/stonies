<template>
  <Teleport to="body">
    <div v-if="store.ui.writing" class="ws" role="dialog" aria-modal="true" aria-label="Write a sticker">
      <header class="ws-head">
        <span class="ws-kicker">Write a sticker</span>
        <button class="icon-btn ws-close" aria-label="Close" @click="step === 'waiting' || step === 'writing' ? cancel() : close()">
          <Icon name="close" :size="20" :stroke="2.4" />
        </button>
      </header>
      <div v-if="song" class="ws-song">
        <Cover :song="song" :size="44" />
        <span>{{ song.name }}</span>
      </div>

      <div class="ws-middle">
        <div class="ring r3" :class="step" aria-hidden="true">
          <div class="ring r2" :class="step">
            <div class="core" :class="step">
              <Icon :name="step === 'done' ? 'check' : step === 'error' || step === 'timeout' ? 'alert' : 'sticker'" :size="64" :stroke="step === 'done' ? 2.6 : 1.8" />
            </div>
          </div>
        </div>
        <div role="status" class="ws-copy">
          <h2 class="display">{{ copy.title }}</h2>
          <p>{{ copy.detail }}</p>
          <span v-if="step === 'waiting'" class="ws-count">Waiting · {{ secondsLeft }} seconds left</span>
        </div>
      </div>

      <div class="ws-buttons">
        <template v-if="step === 'done'">
          <button class="btn btn-amber btn-lg btn-block" @click="close">Done</button>
          <button class="btn btn-lg btn-block ws-dark" @click="again">Write another copy</button>
        </template>
        <template v-else-if="step === 'error' || step === 'timeout'">
          <button class="btn btn-amber btn-lg btn-block" @click="again">Try again</button>
          <button class="btn btn-lg btn-block ws-dark" @click="close">Close</button>
        </template>
        <button v-else class="btn btn-lg btn-block ws-dark" @click="cancel">Cancel</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'
import { store, songById, cancelWriting, writeSticker, loadSongs, pollNow } from '../store'
import Cover from './Cover.vue'
import Icon from './Icon.vue'
import { lockScroll, unlockScroll } from '../scrollLock'

const WRITE_TIMEOUT = 20   // seconds — matches the box's own write timeout

const song = computed(() => store.ui.writing ? songById(store.ui.writing.songId) : null)
const latched = ref(null)          // 'done' | 'error' once the box reports it
const errorText = ref('')
const now = ref(Date.now())
let ticker = null

watch(() => store.ui.writing, (w) => {
  latched.value = null
  errorText.value = ''
  clearInterval(ticker)
  if (w) ticker = setInterval(() => { now.value = Date.now() }, 1000)
}, { immediate: true })
onUnmounted(() => clearInterval(ticker))

// Keep the page behind still while this is open
watch(() => !!store.ui.writing, (open, was) => { if (open && !was) lockScroll(); else if (!open && was) unlockScroll() })


// The box briefly reports success/error, then goes back to listening — latch it
watch(() => [store.nfc.mode, store.nfc.sub_state], ([mode, sub]) => {
  if (!store.ui.writing || latched.value) return
  if (sub === 'success') { latched.value = 'done'; loadSongs() }
  else if (sub === 'error') { latched.value = 'error'; errorText.value = store.nfc.error || '' }
})

const elapsed = computed(() => store.ui.writing ? (now.value - store.ui.writing.startedAt) / 1000 : 0)
const secondsLeft = computed(() => Math.max(0, Math.ceil(WRITE_TIMEOUT - elapsed.value)))

const step = computed(() => {
  if (latched.value) return latched.value
  const n = store.nfc
  if (n.mode === 'writing') return n.sub_state === 'writing_tag' ? 'writing' : 'waiting'
  // Back to listening without success: it timed out (allow a moment for the first poll)
  return elapsed.value > 3 ? 'timeout' : 'waiting'
})

const copy = computed(() => ({
  waiting: { title: 'Hold a blank sticker on the box', detail: 'Lay it flat on top of the box and keep it still.' },
  writing: { title: 'Writing… keep it still', detail: 'This takes about two seconds.' },
  done: { title: 'Sticker ready!', detail: 'Tap it on the box any time to play this. You can write more copies for other rooms.' },
  error: { title: "That didn't work", detail: (errorText.value ? `The box said: ${errorText.value}. ` : '') + 'Try again, holding the sticker still a little longer.' },
  timeout: { title: 'No sticker found', detail: "It's still saved in the library. You can write a sticker any time from its ⋮ menu." },
}[step.value]))

function close() {
  store.ui.writing = null
  pollNow()
}
function cancel() { cancelWriting() }
function again() {
  const s = song.value
  if (s) writeSticker(s)
}
</script>

<style scoped>
.ws {
  position: fixed; inset: 0; z-index: 75; background: var(--navy); color: #fff;
  display: flex; flex-direction: column; padding: env(safe-area-inset-top) 0 env(safe-area-inset-bottom);
}
.ws > * { width: 100%; max-width: 560px; margin-left: auto; margin-right: auto; }
.ws-head { display: flex; align-items: center; justify-content: space-between; padding: 14px 12px 0 20px; }
.ws-kicker { font-size: 13px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--navy-ink); }
.ws-close { background: var(--navy-2); }
.ws-song { display: flex; align-items: center; gap: 12px; padding: 8px 20px 0; font-weight: 700; }
.ws-middle { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 30px; padding: 0 28px; }
.ring, .core { border-radius: 50%; display: grid; place-items: center; }
.r3 { width: 250px; height: 250px; border: 2px solid #3A4A70; }
.r2 { width: 196px; height: 196px; border: 2px solid var(--stone); }
.core { width: 142px; height: 142px; background: var(--stone); }
.r3.writing { border-color: var(--amber); } .r2.writing { border-color: var(--amber-light); } .core.writing { background: var(--amber); color: var(--navy); }
.r3.done { border-color: var(--ok); } .r2.done { border-color: #57C384; } .core.done { background: var(--ok); }
.r3.error, .r3.timeout { border-color: #8A4F00; } .r2.error, .r2.timeout { border-color: #E08A12; } .core.error, .core.timeout { background: #E08A12; color: var(--navy); }
.r3.waiting { animation: pulse 1.6s ease-in-out infinite; }
@keyframes pulse { 50% { transform: scale(1.04); } }
@media (prefers-reduced-motion: reduce) { .r3.waiting { animation: none; } }
.ws-copy { display: flex; flex-direction: column; align-items: center; gap: 10px; text-align: center; }
.ws-copy h2 { font-size: 28px; line-height: 1.2; }
.ws-copy p { margin: 0; font-size: 16px; line-height: 1.45; color: var(--navy-ink); max-width: 320px; }
.ws-count { margin-top: 6px; min-height: 36px; padding: 0 16px; border-radius: 18px; background: var(--navy-2); display: flex; align-items: center; font-size: 14px; font-weight: 700; color: var(--amber-light); }
.ws-buttons { padding: 0 20px 28px; display: flex; flex-direction: column; gap: 10px; }
.ws-dark { background: var(--navy-2); color: #fff; }
</style>

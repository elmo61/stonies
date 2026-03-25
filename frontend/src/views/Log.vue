<template>
  <section class="hero is-dark">
    <div class="hero-body">
      <p class="title">Activity Log</p>
      <p class="subtitle">
        <router-link to="/" class="has-text-grey-light">← Back to player</router-link>
      </p>
    </div>
  </section>
  <section class="section">
    <div class="container">
      <!-- Debug log (collapsible) -->
      <div class="box">
        <div class="debug-toggle" @click="debugOpen = !debugOpen">
          <span>Debug log</span>
          <span class="debug-chevron" :class="{ open: debugOpen }">▶</span>
        </div>
        <div v-if="debugOpen" class="mt-3">
          <p class="has-text-grey is-size-7" v-if="!debugLines.length">No debug entries.</p>
          <table class="table is-fullwidth is-striped is-size-7" v-else>
            <tbody>
              <tr v-for="entry in debugLines" :key="entry.seq">
                <td class="debug-time">{{ entry.time }}</td>
                <td style="white-space: pre-wrap; font-family: monospace;">{{ entry.msg }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="box">
        <p class="has-text-grey" v-if="!lines.length">No log entries yet.</p>
        <table class="table is-fullwidth is-striped is-size-7" v-else>
          <tbody>
            <tr v-for="(line, i) in lines" :key="i">
              <td style="white-space: pre-wrap; font-family: monospace;">{{ line }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const lines = ref([])
const debugLines = ref([])
const debugOpen = ref(false)

onMounted(async () => {
  try {
    const [logRes, nfcRes] = await Promise.all([
      fetch('/api/log'),
      fetch('/api/nfc/status'),
    ])
    const logData = await logRes.json()
    const nfcData = await nfcRes.json()
    lines.value = logData.lines || []
    debugLines.value = (nfcData.log || []).slice().reverse() // newest first
  } catch (e) {
    console.error('Failed to load log', e)
  }
})
</script>

<style scoped>
.debug-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
  color: #555;
  user-select: none;
}

.debug-toggle:hover {
  color: #333;
}

.debug-chevron {
  font-size: 0.7rem;
  transition: transform 0.2s;
}

.debug-chevron.open {
  transform: rotate(90deg);
}

.debug-time {
  white-space: nowrap;
  color: #888;
  font-family: monospace;
  padding-right: 0.75rem;
}
</style>

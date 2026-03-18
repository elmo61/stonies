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

onMounted(async () => {
  try {
    const res = await fetch('/api/log')
    const data = await res.json()
    lines.value = data.lines || []
  } catch (e) {
    console.error('Failed to load log', e)
  }
})
</script>

<template>
  <div class="app">
    <header class="topbar">
      <RouterLink to="/status" class="box-pill">
        <svg width="30" height="30" viewBox="0 0 28 28" fill="none" aria-hidden="true">
          <ellipse cx="14" cy="20" rx="11" ry="7" :fill="connection.online ? '#5B8DEE' : '#AEB4C2'" />
          <path d="M11 12.5 Q14 8.5 17 12.5" stroke="#3D63C9" stroke-width="1.8" stroke-linecap="round" />
          <path d="M8.5 9.5 Q14 3.5 19.5 9.5" stroke="#9DB5F2" stroke-width="1.5" stroke-linecap="round" />
        </svg>
        <span class="ellipsis">{{ boxName() }}</span>
      </RouterLink>
      <RouterLink to="/status" class="status-chip" :class="`lvl-${health.level}`" :aria-label="`Box status: ${health.label}`">
        <span class="dot"></span>{{ health.label }}
      </RouterLink>
    </header>

    <div v-if="!connection.online && store.ui.offlineDismissed" class="offline-banner" role="status">
      <Icon name="wifiOff" :size="18" />
      <span>Can't reach the box. Trying again…</span>
      <button class="btn btn-ghost" @click="store.ui.offlineDismissed = false">Help</button>
    </div>

    <RouterView />
  </div>

  <PhonePlayer />

  <nav class="tabbar" aria-label="Main">
    <RouterLink to="/"><Icon name="library" :size="24" />Library</RouterLink>
    <RouterLink to="/activity"><Icon name="activity" :size="24" />Activity</RouterLink>
    <RouterLink to="/settings"><Icon name="settings" :size="24" />Settings</RouterLink>
  </nav>

  <SongSheet />
  <OptionsMenu />
  <SpeakerSheet />
  <ChapterEditor />
  <WriteSticker />
  <OfflineScreen />
  <DialogHost />
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { connection } from './api'
import { store, health, boxName, startApp } from './store'
import Icon from './components/Icon.vue'
import PhonePlayer from './components/PhonePlayer.vue'
import SongSheet from './components/SongSheet.vue'
import OptionsMenu from './components/OptionsMenu.vue'
import SpeakerSheet from './components/SpeakerSheet.vue'
import ChapterEditor from './components/ChapterEditor.vue'
import WriteSticker from './components/WriteSticker.vue'
import OfflineScreen from './components/OfflineScreen.vue'
import DialogHost from './components/DialogHost.vue'

const route = useRoute()

// Sheets belong to the screen they were opened from
watch(() => route.path, () => {
  store.ui.songId = null
  store.ui.optionsId = null
  store.ui.speakerSheet = false
  store.ui.chaptersId = null
})

watch(() => boxName(), (name) => { document.title = name }, { immediate: true })

onMounted(startApp)
</script>

<style scoped>
.offline-banner {
  margin: 0 16px 8px; padding: 6px 6px 6px 14px; border-radius: 14px; background: var(--amber-soft); color: #7A4500;
  display: flex; align-items: center; gap: 10px; font-size: 14px; font-weight: 700;
}
.offline-banner span { flex: 1; }
.offline-banner .btn { min-height: 44px; padding: 0 12px; color: #7A4500; }
</style>

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

// Fonts are bundled (Latin only) so nothing loads from the internet
import '@fontsource/fredoka/latin-500.css'
import '@fontsource/fredoka/latin-600.css'
import '@fontsource/dm-sans/latin-400.css'
import '@fontsource/dm-sans/latin-500.css'
import '@fontsource/dm-sans/latin-700.css'
import './style.css'

import { store } from './store'

createApp(App).use(router).mount('#app')

// Installable app + opens offline. Browsers only allow this on https.
if (window.isSecureContext && 'serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {})
}
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault()          // show our own Install button instead of the mini-bar
  store.installPrompt = e
})
window.addEventListener('appinstalled', () => { store.installPrompt = null })

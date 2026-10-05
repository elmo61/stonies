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

createApp(App).use(router).mount('#app')

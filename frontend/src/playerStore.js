import { ref } from 'vue'

// Shared across all views — persists through route changes.
// Set this ref to { song, chapter, time } to start local playback.
export const localPlayRequest = ref(null)

// Thin wrapper around the box's REST API. Every call goes through here so
// the app can tell when the box stops answering (see `connection`).
import { reactive } from 'vue'

export const connection = reactive({
  online: true,      // false once requests keep failing
  lastSeen: null,    // Date of the last successful response
  failures: 0,
})

// One failed request can be a blip; two in a row means the box is away
const FAILURES_BEFORE_OFFLINE = 2

function markOk() {
  connection.failures = 0
  connection.online = true
  connection.lastSeen = new Date()
}

function markFailed() {
  connection.failures += 1
  if (connection.failures >= FAILURES_BEFORE_OFFLINE) connection.online = false
}

async function request(method, path, body) {
  const opts = { method, headers: {} }
  if (body instanceof FormData) {
    opts.body = body
  } else if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  let res
  try {
    res = await fetch(`/api${path}`, opts)
  } catch (e) {
    markFailed()
    throw new Error("Can't reach the box")
  }
  markOk()
  let data = {}
  try { data = await res.json() } catch (_) {}
  if (!res.ok || data.error) throw new Error(data.error || `Something went wrong (${res.status})`)
  return data
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, body ?? {}),
  patch: (path, body) => request('PATCH', path, body),
  del: (path) => request('DELETE', path),
}

// Uploads use XHR so we can report progress on big audiobooks.
export function upload(path, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `/api${path}`)
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total)
    }
    xhr.onload = () => {
      markOk()
      let data = {}
      try { data = JSON.parse(xhr.responseText) } catch (_) {}
      if (xhr.status >= 400 || data.error) reject(new Error(data.error || `Upload failed (${xhr.status})`))
      else resolve({ status: xhr.status, data })
    }
    xhr.onerror = () => { markFailed(); reject(new Error("Can't reach the box")) }
    xhr.send(formData)
  })
}

// Audio URL for on-phone playback of a track or one chapter of a story
export function audioUrl(song, chapterIndex = 0) {
  if (song.type === 'audiobook' || song.type === 'album') {
    const ch = song.chapters[chapterIndex]
    return `/music/${encodeURIComponent(song.folder)}/${encodeURIComponent(ch.filename)}`
  }
  return `/music/${encodeURIComponent(song.filename)}`
}

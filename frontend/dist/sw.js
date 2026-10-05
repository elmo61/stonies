// Stonies service worker: lets the installed app open even when the box
// can't be reached, showing the saved library and the "box isn't answering"
// screen. Browsers only run this on https, so plain-http boxes ignore it.
//
// - Pages: network first, fall back to the saved app shell
// - /assets/*: cache first (file names change on every build)
// - Library data (/api/songs, /api/config, /api/box): network first, fall back to the last copy
// - Everything else (other /api calls, /music audio): straight to the box, never cached
const VERSION = 'stonies-v1'
const SHELL = `${VERSION}-shell`
const DATA = `${VERSION}-data`
const SAVED_API = ['/api/songs', '/api/config', '/api/box']

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL).then((c) => c.addAll(['/', '/manifest.json', '/icon-192.png'])))
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) {
      if (!key.startsWith(VERSION)) await caches.delete(key)
    }
    await self.clients.claim()
  })())
})

async function networkFirst(request, cacheName, fallbackUrl) {
  const cache = await caches.open(cacheName)
  try {
    const response = await fetch(request)
    if (response.ok) cache.put(fallbackUrl || request, response.clone())
    return response
  } catch (err) {
    const saved = await cache.match(fallbackUrl || request)
    if (saved) return saved
    throw err
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(SHELL)
  const saved = await cache.match(request)
  if (saved) return saved
  const response = await fetch(request)
  if (response.ok) cache.put(request, response.clone())
  return response
}

self.addEventListener('fetch', (event) => {
  const req = event.request
  if (req.method !== 'GET') return
  const url = new URL(req.url)
  if (url.origin !== self.location.origin) return

  if (req.mode === 'navigate') {
    // Every page is the same single-page app
    event.respondWith(networkFirst(req, SHELL, '/'))
  } else if (url.pathname.startsWith('/assets/')) {
    event.respondWith(cacheFirst(req))
  } else if (SAVED_API.includes(url.pathname)) {
    event.respondWith(networkFirst(req, DATA))
  }
  // anything else: default browser behaviour (straight to the box)
})

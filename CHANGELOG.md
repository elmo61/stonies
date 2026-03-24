# Changelog

All notable changes to Stonies are documented here, newest first.

---

## 2026-03-24 — On-device player bar

### Added
- Fixed bottom player bar for on-device (browser) playback — always visible, even when scrolled
- Scrubber with live seek and elapsed / total time display
- Previous and next chapter buttons for audiobooks
- Expandable chapter panel in the player bar — tap any chapter to jump to it
- Player bar persists across page navigation (Home ↔ Logs) using a shared Vue store (`playerStore.js`)
- NFC tap debounce — rapid re-taps of the same sticker are ignored

### Changed
- Player bar extracted into a self-contained `LocalPlayerBar.vue` component that owns its own `Audio` element — `Home.vue` now just passes a play request and listens for a `stopped` event
- Disk free/total space shown in the footer

---

## 2026-03-20 — On-device playback

### Added
- Play any track or audiobook directly in the browser without needing a Chromecast speaker
- Resume audiobooks from saved position when playing on-device
- Per-chapter play buttons in the audiobook chapter list for on-device playback

---

## 2026-03-19 — Device sync & UI refresh

### Added
- **Device sync** — pull songs from another Stonies device on the same network; enter a `.local` hostname, preview what's missing, and pull in one click
- Sync progress bar with per-song status during transfer

### Changed
- Nav bar redesigned with a custom SVG Stonies logo
- NFC daemon heartbeat moved into the nav bar (replaces the old inline activity bar)
- Hero banner removed to reduce clutter

---

## 2026-03-18 — Vite frontend & activity log

### Added
- Dedicated **Logs page** (`/log`) showing a live feed of every NFC tap, cast event, chapter advance, and position save
- Vue Router with two routes: Home (`/`) and Logs (`/log`)

### Changed
- Frontend migrated from a single `index.html` (Vue CDN) to a proper **Vite + Vue 3 SPA** with a build step
  - Source lives in `frontend/src/`; built output in `frontend/dist/` (committed to git)
  - Pi needs no Node.js installed — `git pull` is enough to update
- Cast monitor rewritten as an event-driven listener (previously polled Chromecast every 60 s); saves audiobook position every 30 s during playback
- Mobile layout fixes throughout

### Fixed
- Cast monitor reconnect loop under certain network conditions
- NFC daemon no longer dies on transient I2C errors
- Chromecast thread leak on repeated play calls
- `stop_discovery` called before cast connection was established

---

## 2026-03-13 — Quality of life

### Added
- **Update badge** in the settings bar when commits are available on `origin/main`
- Ability to **clear a saved audiobook position** to restart from the beginning

### Fixed
- Mobile layout overflow caused by song action buttons wrapping incorrectly

---

## 2026-03-11 — Robustness & local images

### Added
- Cover images are now hosted locally on the Pi and served over HTTP (no external URLs needed)
- NFC write timeout — write mode cancels automatically if no sticker is tapped within 60 s
- Guards against casting while in offline mode

### Fixed
- Chromecast startup bong no longer plays when Stonies connects to cast

---

## 2026-03-10 — System dependencies

### Added
- `i2c-tools` added as a required system dependency in `setup.sh`

---

## 2026-03-04 — Audiobooks, sleep timer & polish

### Added
- **Audiobook support** — upload a folder of chapter files; they are queued as a playlist in filename order
- **Resume** — audiobook position (chapter + timestamp) is saved every 30 s and resumed on the next tap
- **Per-chapter play** — tap any chapter in the expanded list to cast from that point
- **Scan Imports** — drop files into `music_import/` on the Pi and import them without using the upload form
- **Bedtime sleep timer** — stops playback automatically after a configurable duration if started after a set time
- **Stop playback** button in the now-playing bar
- **Inline rename** — rename any song or audiobook directly in the library row
- **Search / filter** — filter the library by song name or chapter title
- **Rich Chromecast metadata** — title, chapter number, album name, and cover art sent to the speaker
- **NFC activity log** (inline, later moved to its own page)
- **Sticky now-playing bar** showing current track, chapter, and playback position
- Speaker and sleep timer settings moved into a modal

### Fixed
- Playback status endpoint crashing due to a zeroconf race condition

---

## 2026-03-03 — Initial release

### Added
- NFC daemon reading NTAG stickers via PN532 over I2C
- Flask REST API serving audio files and handling cast operations
- Vue 3 (CDN) single-page UI — discover speakers, list tracks, play, stop
- Single track upload (`.mp3` / `.m4a`)
- NFC write on upload flow
- Re-tag existing songs
- Offline mode
- Bedtime sleep timer (early version)
- `setup.sh` one-shot install script for a fresh Raspberry Pi
- `INSTALL.md` manual setup guide

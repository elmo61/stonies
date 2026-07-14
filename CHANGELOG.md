# Changelog

All notable changes to Stonies are documented here, newest first.

---

## 2026-07-14 — Long-run reliability

Fixes for the "works for a week, then needs a reboot" class of failures: leaked Chromecast connections slowly exhausting the process, and a wedged NFC reader staying dead until power cycle.

### Fixed
- **Chromecast connection leak** — when the speaker connection dropped (speaker reboot, Wi-Fi blip), the monitor abandoned the connection without closing it; pychromecast then retried it forever in a background thread. These orphaned threads accumulated over days until the whole web app stopped responding. Dropped connections are now properly disconnected on the monitor thread.
- **Discovery (zeroconf) leak** — every cast operation created a fresh discovery browser (~5 threads + multicast sockets) that leaked whenever connecting to the speaker failed. All speaker lookups now go through a single `find_cast()` helper that always stops discovery, even on failure, and bounds connection retries.
- **Corrupt `songs.json` no longer destroys the library** — a corrupt file (e.g. after a power cut mid-write) used to be treated as an empty library and regenerated with brand-new song IDs, silently orphaning every written NFC tag. It is now reported as an error and left untouched.
- **Sync could hang forever** — peer downloads had no timeout; a peer disappearing mid-transfer left the sync job stuck on "running" until the next restart.

### Added
- **Self-healing NFC daemon** — on repeated reader errors the daemon now re-configures the PN532, then rebuilds the I2C bus from scratch, and as a last resort exits so systemd restarts the service clean. Previously a wedged reader/bus was retried with the same dead handle forever and stayed down until reboot.
- **NFC heartbeat watchdog** — restarts the service if the NFC loop hangs inside an I2C call (a failure mode the retry loop can't see).
- **Atomic JSON writes** (`storage.py`) — `songs.json` and `config.json` are written via temp-file-and-rename so they can never be left half-written by a power cut.
- **Activity log cap** — `activity.log` is trimmed to its most recent lines once it passes 1 MB, instead of growing forever.
- **Release channels** — Settings → Release Channel chooses **Stable** (follows `main`) or **Beta** (follows `beta`). Update checks, the update button, and `update.sh` all follow the chosen channel; switching channels — including downgrading beta → stable — is just another one-click update. The settings modal also shows the exact version the device is running.
- **One-click updates from the UI** — the update badge is now an **⬆️ Update now** button. It pulls the latest code, installs new Python packages into the venv, then exits so systemd restarts the service on the new code — no SSH or sudo needed. If an update would change the systemd service file (which does need sudo), the UI detects this and tells you to run `update.sh` instead.
- **`update.sh`** — one-command updater for existing installs: pulls the latest code, installs new Python packages, refreshes the systemd service file if it changed, and restarts. Previously new dependencies and service changes only reached fresh installs via `setup.sh`.
- **`requirements.txt`** — single source of truth for Python dependencies, used by both `setup.sh` and `update.sh`.
- README: *Reliability* and *Updating* sections, plus an I2C clock-stretching troubleshooting note for flaky readers.

### Changed
- Server now runs under **waitress** (bounded thread pool) instead of the Flask dev server; falls back to the dev server if waitress isn't installed.
- systemd unit waits for `network-online.target` so the service can't start before the Pi has an IP.
- `pychromecast` pinned to the tested major range in `setup.sh`; `waitress` added to dependencies.
- Audiobook position saves throttled from every 30 s to every 60 s to halve SD-card writes during playback.
- Repeated NFC errors log once to the activity feed instead of once per second.
- Removed dead code: the never-started fallback position tracker thread and an unused event in `NFCState`.

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

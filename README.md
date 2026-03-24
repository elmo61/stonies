# Stonies

A Raspberry Pi app for kids — tap an NFC sticker to play a song or audiobook on a Google/Chromecast speaker. Each sticker is permanently linked to one item in your library. A web UI running on the Pi handles everything else: adding songs, writing stickers, controlling playback, and listening on the device itself.

---

## How it works

Two things run in the same Python process:

- **NFC daemon** (background thread) — owns the PN532 reader and loops forever. When a sticker is tapped it reads the ID, looks it up in `songs.json`, and tells the Chromecast to fetch and play the audio served by this same Flask process.
- **Flask web server** (main thread) — serves the Vue 3 SPA and a REST API for managing everything.

When you add a new track or audiobook via the UI:
1. Audio files are uploaded and saved to `music/`
2. A 6-character hex ID is generated and written to `songs.json`
3. The daemon switches into **write mode** — tap a blank sticker and the ID is written to it
4. From then on, tapping that sticker casts the content to your speaker

---

## Features

### Playback
- **Tracks** — single `.mp3` / `.m4a` files cast to any Google/Chromecast speaker
- **Audiobooks** — multi-chapter folders queued as a playlist; resumes from where you left off across taps
- **On-device playback** — play audio directly in the browser with no speaker needed; persists while navigating between pages
- **Fixed bottom player bar** — always-visible controls with a scrubber, prev/next chapter buttons, and an expandable chapter list to jump to any chapter
- **Chromecast now-playing** — shows current track, chapter, and saved position while casting

### NFC
- **Write on upload** — upload a song and immediately write its ID to a sticker in one flow
- **Re-tag** — write an existing song's ID to a new sticker at any time
- **Offline mode** — stickers are identified but nothing is cast; useful for testing without a speaker
- **NFC status indicator** — live heartbeat in the nav bar showing daemon health
- **Debounce** — rapid re-taps of the same sticker are ignored

### Library management
- **Scan Imports** — drop files into `music_import/` on the Pi and import them in one click
- **Inline rename** — rename any track or audiobook directly in the library
- **Search** — filter by name or chapter title
- **Cover art** — upload an image per song; displayed in the library and sent to the Chromecast
- **Clear progress** — reset a saved audiobook position to start from the beginning
- **Device sync** — pull songs from another Stonies device on the same network

### Settings & automation
- **Speaker selection** — scan and save any Google/Chromecast speaker on the network
- **Bedtime sleep timer** — automatically stops playback after a set duration if started after a configured time (e.g. stop after 60 min if started after 7 pm)
- **Update badge** — notified in the UI when commits are available on `origin/main`

### Activity log
- Dedicated `/log` page showing a live feed of every tag read, cast event, and position save

---

## Hardware

| Component | Details |
|---|---|
| Raspberry Pi | Any model with I2C (tested on Pi 3 / 4 / Zero 2 W) |
| PN532 NFC module | Connected via I2C — tested with Hailege PN532 |
| NTAG stickers | NTAG213 / 215 / 216 — not encrypted fobs |
| Google/Chromecast speaker | Any speaker on the same local network |

### PN532 wiring (I2C)

| PN532 pin | Pi GPIO header |
|---|---|
| VCC | Pin 1 (3.3 V) |
| GND | Pin 6 |
| SDA | Pin 3 (GPIO 2) |
| SCL | Pin 5 (GPIO 3) |

> **Note:** If your PN532 module has DIP switches, set both to OFF for I2C mode. Modules often ship set to UART or SPI.

---

## Quick start (fresh Raspberry Pi)

```bash
sudo apt update && sudo apt install git -y
git clone https://github.com/elmo61/stonies.git
bash stonies/projects/stonies/setup.sh
```

The script installs all system dependencies, enables I2C, creates a Python venv, and registers a systemd service so Stonies starts automatically on every boot.

Open `http://<pi-ip>:5000` in a browser on any device on the same network.

See [INSTALL.md](INSTALL.md) for manual steps and troubleshooting.

---

## Usage

### First-time setup
1. Open the UI and tap **⚙️ Settings**
2. Pick your speaker from the dropdown and click **Save Speaker**
3. Optionally configure the bedtime sleep timer

### Adding a track
1. **+ Add Song** → **🎵 Track** → enter a name, pick a file, optionally add a cover image
2. Click **Upload & Write Tag** — the banner changes to *"Touch the sticker now..."*
3. Tap a blank NTAG sticker — it's written and the song appears in the library

### Adding an audiobook
1. **+ Add Song** → **📚 Audiobook** → click **Select Folder** (or **Select Files**)
2. Chapter names are auto-derived from filenames — edit them if needed
3. Click **Upload & Write Tag** and tap a blank sticker

### Playing without a speaker
Click **▶** on any song row to play it directly in the browser. The player bar appears at the bottom of the screen and stays visible even while navigating to the Logs page.

### Syncing from another device
Click **⇄ Sync Device**, enter the hostname of another Stonies Pi on your network (e.g. `stonies-bedroom.local`), preview the missing songs, and pull them across.

---

## File structure

```
main.py               Entry point — wires state, starts daemon thread, runs Flask
nfc_daemon.py         NFCState class + NFC read/write helpers + background loop
api.py                Flask REST API (factory pattern via create_app())
cast_monitor.py       Event-driven Chromecast status listener + position saver
activity_log.py       Persistent activity log helpers
setup.sh              One-shot install script for a fresh Pi
INSTALL.md            Manual install guide
frontend/
  src/
    App.vue           Root component — nav, persistent player bar, disk footer
    views/
      Home.vue        Song library, upload, settings, sync
      Log.vue         Live activity log page
    components/
      LocalPlayerBar.vue  Self-contained on-device audio player component
    playerStore.js    Shared playback state ref (survives page navigation)
    router.js         Vue Router config
    style.css         Global styles
  dist/               Pre-built frontend (committed — Pi needs no Node.js)
music/                Audio files (gitignored — add your own)
music_import/         Drop files here; use Scan Imports to add them (gitignored)
songs.json            Song database (gitignored — generated at runtime)
config.json           Speaker + sleep timer config (gitignored)
```

---

## API reference

| Method | Path | Description |
|---|---|---|
| GET | `/` | Serves the UI |
| GET | `/music/<path>` | Serves audio files to Chromecast |
| GET | `/api/speakers` | Discover Chromecast speakers on the network |
| GET | `/api/config` | Get saved config (speaker, sleep timer) |
| POST | `/api/config` | Save config |
| GET | `/api/songs` | List all songs |
| POST | `/api/songs` | Upload a track or audiobook (multipart) |
| PATCH | `/api/songs/<id>` | Rename a song |
| DELETE | `/api/songs/<id>` | Delete a song and its files |
| DELETE | `/api/songs/<id>/progress` | Clear saved audiobook position |
| POST | `/api/songs/<id>/retag` | Write NFC tag for an existing song |
| POST | `/api/play` | Cast a song by ID (optional `chapter_index`) |
| GET | `/api/playback/status` | Current Chromecast playback state |
| POST | `/api/playback/stop` | Stop Chromecast playback |
| GET | `/api/nfc/status` | NFC daemon state + activity log |
| POST | `/api/nfc/cancel` | Cancel a pending write |
| POST | `/api/offline/toggle` | Toggle offline mode |
| POST | `/api/import/scan` | Import files from `music_import/` |
| POST | `/api/sync/preview` | Preview songs available from a peer device |
| POST | `/api/sync/pull` | Pull missing songs from a peer device |
| GET | `/api/sync/status` | Sync job progress |
| GET | `/api/disk` | Disk usage of the music folder |
| GET | `/api/update/status` | Check for available git updates |

---

## Notes

- The app starts cleanly even if the PN532 is not connected — the NFC daemon exits gracefully and Flask serves the UI normally. Useful for testing on a dev machine.
- Audio is served directly from the Pi to the Chromecast over HTTP — no internet required for playback.
- The frontend is a pre-built Vite + Vue 3 SPA. The `dist/` folder is committed so the Pi needs no Node.js installed. Run `npm run build` inside `frontend/` before committing any frontend source changes.
- `songs.json` and `config.json` are excluded from version control as they contain personal library data and are generated at runtime.

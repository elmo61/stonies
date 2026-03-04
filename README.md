# Stonies

A Raspberry Pi app that lets kids tap NFC stickers to cast music and audiobooks to Google/Chromecast speakers. Each sticker is linked to a track or audiobook — tap it, and it starts playing. A web UI handles everything else: adding songs, managing speakers, writing stickers, and controlling playback.

---

## How it works

Two things run in the same Python process:

- **NFC daemon** (background thread) — owns the PN532 reader, loops forever listening for stickers. When a sticker is tapped it reads the ID, looks it up in `songs.json`, and tells the Chromecast to fetch and play the audio served by this same app.
- **Flask web server** (main thread) — serves the Vue UI and a REST API for managing songs, speakers, and NFC write operations.

When you add a new track or audiobook via the UI:
1. The audio file(s) are uploaded and saved to `music/`
2. A 6-character hex ID is generated and saved to `songs.json`
3. The daemon switches into **write mode** — tap a blank sticker and the ID gets written to it
4. From then on, tapping that sticker casts the song or queues all audiobook chapters in order

---

## Features

- **Tracks** — single `.mp3` / `.m4a` files cast to any Google/Chromecast speaker
- **Audiobooks** — multi-chapter folders queued as a playlist; resumes from where you left off
- **NFC write** — upload a track and immediately write its ID to a sticker in one flow
- **Re-tag** — write an existing song's ID to a new sticker at any time
- **Now-playing bar** — sticky banner showing current track, chapter, and playback position; updates every 10 s while playing
- **Stop playback** — stop the Chromecast from the UI
- **Bedtime sleep timer** — automatically stops playback after a configurable duration if started after a set time (e.g. stop after 60 min if started after 7 pm)
- **Offline mode** — tap stickers to identify them without casting anything
- **Scan Imports** — drop files into `music_import/` on the Pi and import them in one click
- **Inline rename** — rename any track or audiobook directly in the library
- **Search** — filter the library by name or chapter title
- **NFC activity log** — live terminal-style log of every tag read and cast event
- **Rich Chromecast metadata** — title, album name, chapter number, and cover art sent to the speaker

---

## Hardware

| Component | Details |
|---|---|
| Raspberry Pi | Any model with I2C (tested on Pi 3/4/Zero 2) |
| PN532 NFC module | Connected via I2C — tested with Hailege PN532 |
| NTAG stickers | NTAG213/215/216 — not encrypted fobs |
| Google/Chromecast speaker | Any speaker on the same local network |

### PN532 wiring (I2C)

| PN532 pin | Pi GPIO header |
|---|---|
| VCC | Pin 1 (3.3V) |
| GND | Pin 6 |
| SDA | Pin 3 (GPIO 2) |
| SCL | Pin 5 (GPIO 3) |

> **Important:** If your PN532 module has DIP switches, set both to OFF for I2C mode. Some modules default to UART or SPI.

---

## Quick start (fresh Raspberry Pi)

```bash
git clone https://github.com/elmo61/stonies.git && bash stonies/projects/stonies/setup.sh
```

That's it. The script installs all dependencies, enables I2C, sets up a Python venv, and registers a systemd service so Stonies starts automatically on every boot.

Open `http://<pi-ip>:5000` in a browser on any device on the same network.

See [INSTALL.md](INSTALL.md) for manual steps and details.

---

## Usage

### First-time setup
1. Open the UI and click **⚙️ Settings**
2. Select your Google/Chromecast speaker from the dropdown and click **Save Speaker**
3. Optionally configure the bedtime sleep timer

### Adding a track
1. Click **+ Add Song** → select **🎵 Track**
2. Enter a name, pick an audio file (`.mp3` or `.m4a`), optionally add a cover image URL
3. Click **Upload & Write Tag** — the file uploads and the banner changes to *"Touch the sticker now..."*
4. Tap a blank NFC sticker against the PN532 — it gets written and the song appears in the library

### Adding an audiobook
1. Click **+ Add Song** → select **📚 Audiobook**
2. Click **Select Folder** (or **Select Files**) — chapter names are auto-derived from filenames
3. Edit chapter names if needed, then click **Upload & Write Tag**
4. Tap a blank sticker — from now on tapping it queues all chapters on the speaker

### Re-tagging
Click **🏷 Tag** next to any song to write its ID to a new sticker.

### Offline mode
Click the **Online** button to switch to offline mode — stickers are identified but nothing is cast. Useful for testing without a speaker nearby.

---

## File structure

```
main.py           Entry point — starts daemon thread and Flask
nfc_daemon.py     NFCState class + NFC read/write helpers + background loop
api.py            Flask REST API (factory pattern)
index.html        Vue 3 + Bulma single-page frontend (no build step)
setup.sh          One-shot install script for a fresh Pi
INSTALL.md        Manual install guide
music/            Audio files (gitignored — add your own)
music_import/     Drop files here and use Scan Imports to add them (gitignored)
songs.json        Song database (gitignored — generated at runtime)
config.json       Saved speaker + sleep timer config (gitignored)
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
| GET | `/api/songs` | List all songs (auto-detects new audiobook folders) |
| POST | `/api/songs` | Upload a track or audiobook (multipart) |
| PATCH | `/api/songs/<id>` | Rename a song |
| DELETE | `/api/songs/<id>` | Delete a song/audiobook and its files |
| POST | `/api/songs/<id>/retag` | Write NFC tag for an existing song |
| POST | `/api/play` | Cast a song by ID (optional `chapter_index`) |
| GET | `/api/playback/status` | Current Chromecast playback state |
| POST | `/api/playback/stop` | Stop Chromecast playback |
| GET | `/api/nfc/status` | NFC daemon state + activity log |
| POST | `/api/nfc/cancel` | Cancel a pending write |
| POST | `/api/offline/toggle` | Toggle offline mode |
| POST | `/api/import/scan` | Import files from `music_import/` |

---

## Notes

- The app starts cleanly even if the PN532 is not connected — the NFC daemon exits gracefully and Flask runs normally. Useful for testing the UI on a dev machine.
- Audio files are served directly from the Pi to the Chromecast over HTTP — no internet required.
- `songs.json` and `config.json` are excluded from version control as they contain personal data and are generated at runtime.

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

The web app is built for phones first: every button is at least 44px, rarely used actions live behind a ⋮ menu, and it works without the internet (fonts and styles are bundled).

### Playing
- **Library** — stories and songs as big rows with cover art (or coloured initials), filters for All / Stories / Songs, and search across names and chapter titles
- **One tap to play** — each row has a single play button; tap the row to open the story
- **Tap a chapter to play it** — the story sheet lists chapters by name; the playing chapter and saved place are highlighted, earlier ones ticked
- **Resume** — stories pick up where they left off, whether started from a sticker or the app
- **Now playing card** — what's playing, which chapter, a stop button, and one-tap chips for the speaker and bedtime
- **Speaker picker** — every speaker on your Wi-Fi; stickers and the app both play on the chosen one
- **Play on this phone** — from a song's ⋮ menu: listen in the browser with no speaker; has a scrubber and chapter skip

### Radio and podcasts
- **Radio stations** — Add → Radio station: search by name (from the free [radio-browser.info](https://www.radio-browser.info) directory) or paste a stream link. The box checks it plays (following `.pls`/`.m3u` playlists) and its sticker plays the station live
- **Podcasts** — Add → Podcast: search by name (Apple's podcast directory) or paste the feed link. Each podcast chooses what a tap plays:
  - **The newest episode** — for weekly shows; resumes it if it was stopped part-way
  - **Episodes in order** — starts at the first episode, carries on where it was stopped, and moves to the next one after each finishes
- Episodes play straight from the podcast's own site, so nothing is downloaded and the SD card doesn't fill up. Both need the internet when tapped
- Each podcast's episode list is cached on the box (`podcast_cache/`) and refreshed every few hours, so a tap doesn't wait for a feed that can be several MB; if the feed can't be reached, the saved list is used
- Covers come from the directory or the podcast's artwork; change them from the ⋮ menu like any other

### Stickers
- **Write on upload** — add a story or song and write its sticker in one flow, with a full-screen "hold a sticker on the box" guide
- **Write another copy** — any song's ⋮ menu → Write to a sticker; cancelling never deletes anything
- **Quiet mode** (Settings) — stickers are recognised but nothing plays; handy for testing
- **Debounce** — rapid re-taps of the same sticker are ignored

### Library management (⋮ menu and Settings)
- **Rename** songs, and **rename chapters** from an editable list
- **Add / change cover** — take a photo or choose an image; it's shrunk on the phone before upload. For many at once, `tools/upload_covers.py` matches a folder of pictures to song names (`--dry-run` first)
- **Start from the beginning next time** — forgets a story's saved place
- **Delete** — asks first
- **Add** — Story / Album / Song, pick a folder or files, check chapter names, and take a photo of the book cover as its artwork; shows upload progress
- **Copy from another box** — pull songs another Stonies box has and this one doesn't
- **Import folder** — files copied into `music_import/` on the Pi, imported in one tap

### Looking after the box
- **"Is it working?"** — Wi-Fi signal strength, sticker reader, whether the speaker is found, cast player, storage and updates, all in one place (tap the status chip at the top)
- **"Box isn't answering" screen** — appears when the box stops responding, with the steps to try, and clears itself when it's back
- **Activity** — a plain-English timeline of stickers, plays, bedtime stops, updates and problems, with the technical log one tap away
- **Updates** — stable/beta channel and one-tap updates in Settings
- **Bedtime** — anything started after a set time stops after a set number of minutes
- **Add to home screen** — a home-screen icon for each box (full-screen on iPhone; a shortcut on Android until the boxes have https; Settings shows how)

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

### Flaky reader? (I2C clock stretching)

The PN532 uses I2C clock stretching, which the Pi's I2C controller implements incorrectly — combined with long or marginal wiring this causes intermittent bus errors. The app now recovers from these automatically (see *Reliability* below), but if the reader is frequently dropping out you can also slow the bus down, which makes the hardware itself far more tolerant. Add to `/boot/config.txt` (or `/boot/firmware/config.txt` on newer OS images) and reboot:

```
dtparam=i2c_arm_baudrate=10000
```

---

## Quick start (fresh Raspberry Pi)

```bash
sudo apt update && sudo apt install git -y
git clone https://github.com/elmo61/stonies.git
bash stonies/setup.sh
```

The script installs all system dependencies, enables I2C, creates a Python venv, and registers a systemd service so Stonies starts automatically on every boot.

Open `http://<pi-ip>:5000` in a browser on any device on the same network.

See [INSTALL.md](INSTALL.md) for manual steps and troubleshooting.

---

## Updating an existing install

When an update is available the settings bar shows an **⬆️ Update now** button — click it and Stonies pulls the latest code, installs any new Python packages, and restarts itself (about 30 seconds; anything already playing on the speaker keeps playing). No SSH needed.

The button works without admin rights because it only touches files the app owns, then simply exits and lets systemd restart it on the new code. The one thing it *can't* do is rewrite the systemd service file — that needs sudo. When an update includes a service change, the UI detects it and shows **"Update available — run update.sh"** instead. In that case, SSH to the Pi and run:

```bash
cd stonies
bash update.sh
```

`update.sh` does everything the button does plus the service file refresh. It only touches what actually differs, so it's safe to run repeatedly. Either way, your library (`music/`, `songs.json`, `config.json`) is never affected.

### Release channels

Settings → **🧪 Release Channel** picks which releases the device follows:

| Channel | Git branch | Who it's for |
|---|---|---|
| **Stable** (default) | `main` | Everyday devices — tested releases only |
| **Beta** | `beta` | Try new features first; may be rough |

Switching channel is itself just an update: pick the channel, and if that channel's version differs from what's running, the **⬆️ Update now** button appears — including when moving *back* from beta to stable (a safe downgrade; your library is untouched). `update.sh` follows the same channel setting.

**Release workflow (for maintainers):** merge feature branches into `beta`; beta devices pick them up. When beta has proven itself, merge `beta` into `main` and stable devices see the update. Optionally tag main releases (`git tag v1.x && git push --tags`) as human-readable markers — devices don't use tags.

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
main.py               Entry point — wires state, starts daemon + watchdog threads, runs the server
nfc_daemon.py         NFCState class + NFC read/write helpers + self-healing background loop
api.py                Flask REST API (factory pattern via create_app())
cast_monitor.py       Event-driven Chromecast status listener + position saver
streams.py            Radio + podcasts: search, stream checks, feed reading and caching, episode choice
activity_log.py       Persistent activity log helpers (size-capped)
storage.py            Atomic JSON write helper for songs.json / config.json
setup.sh              One-shot install script for a fresh Pi
update.sh             In-place updater for existing installs (code + deps + service)
requirements.txt      Python dependencies (single source for setup.sh / update.sh)
INSTALL.md            Manual install guide
frontend/
  src/
    App.vue           App shell — top bar (box name + status), tab bar, sheets
    store.js          Shared state, polling and actions (play, rename, stickers…)
    api.js            API wrapper; notices when the box stops answering
    style.css         Mobile-first styles (no CSS framework)
    router.js         Routes: /, /activity, /settings, /status, /add
    views/            Library, Activity, Settings, Status ("Is it working?"), Add
    components/       Now playing, story sheet, ⋮ menu, speaker picker, chapter editor,
                      sticker writer, phone player, offline screen, dialogs, icons
  public/             manifest.json + home-screen icons
  dist/               Pre-built frontend (committed — Pi needs no Node.js)
music/                Audio files (gitignored — add your own)
music_import/         Drop files here; use Scan Imports to add them (gitignored)
songs.json            Song database (gitignored — generated at runtime)
podcast_cache/        Cached podcast episode lists (gitignored)
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
| POST | `/api/songs` | Upload a track or audiobook (multipart); or add a `radio` / `podcast` (`type`, `name`, `url`, optional `image_remote`, `episode_mode`) |
| GET | `/api/find/radio?q=` | Search radio stations by name |
| GET | `/api/find/podcasts?q=` | Search podcasts by name |
| POST | `/api/streams/check` | Check a station or feed address works before adding (`kind`, `url`) |
| POST | `/api/songs/<id>/image` | Add or replace a song's cover (multipart `image`) |
| PATCH | `/api/songs/<id>` | Rename a song (`name`) and/or its chapters (`chapter_names`, one per chapter; blank keeps the old name); for podcasts, `episode_mode`: `newest` or `next` |
| DELETE | `/api/songs/<id>` | Delete a song and its files |
| DELETE | `/api/songs/<id>/progress` | Clear saved audiobook position |
| POST | `/api/songs/<id>/retag` | Write NFC tag for an existing song |
| POST | `/api/play` | Cast a song by ID (optional `chapter_index`) |
| GET | `/api/playback/status` | Current Chromecast playback state |
| POST | `/api/playback/stop` | Stop Chromecast playback |
| GET | `/api/nfc/status` | NFC daemon state + activity log |
| POST | `/api/nfc/cancel` | Stop writing a sticker (the song always stays in the library) |
| POST | `/api/offline/toggle` | Toggle quiet mode (stickers recognised, nothing plays) |
| POST | `/api/import/scan` | Import files from `music_import/` |
| POST | `/api/sync/preview` | Preview songs available from a peer device |
| POST | `/api/sync/pull` | Pull missing songs from a peer device |
| GET | `/api/sync/status` | Sync job progress |
| GET | `/api/disk` | Disk usage of the music folder |
| GET | `/api/wifi` | Wi-Fi signal (`signal_dbm`, `quality_pct`, `strength`: strong/ok/weak), read-only |
| GET | `/api/box` | The box's hostname |
| GET | `/api/update/status` | Update check for the configured channel: availability, version, self-apply eligibility |
| POST | `/api/update/apply` | Self-update to the channel's branch: sync, install deps, restart (409 if it needs `update.sh`) |

---

## Cast player

**Settings → 📺 Cast Player** chooses what the speaker plays through:

| Option | Behaviour |
|---|---|
| **Stonies player** (default) | The Stonies Cast receiver (`A0D905F0`). Pushes the playback position to Stonies every 30 s, and on speakers with a screen shows the cover art, chapter name and book title. |
| **Google standard player** | Google's Default Media Receiver. Use it if a speaker won't open the Stonies player. Audiobook positions are saved less often. |

The change applies from the next thing you play. Stonies falls back to Google's standard player automatically if a speaker won't open the Stonies player, and logs *"Stonies receiver unavailable — using Google's standard player"*, so music always plays.

If you see that message, check the app in the [Google Cast SDK Developer Console](https://cast.google.com/publish):
- It must be **Published**. Unpublished apps only run on speakers registered there as test devices.
- **"Supports casting to audio only devices"** must be ticked. Otherwise Google won't open it on Nest Mini, Nest Audio, Google Home speakers or speaker groups.

The receiver page is `docs/receiver.html`, served by GitHub Pages from the **`main`** branch at `https://elmo61.github.io/stonies/receiver.html`, so receiver changes only go live once they're merged to `main`.

### Using your own receiver app

To use a different registered receiver, set its ID in `config.json` on the Pi. Settings then shows it as a custom receiver; picking either option there replaces it.

```json
{
  "speaker": "My Speaker",
  "cast_app_id": "YOUR_APP_ID"
}
```

`"cast_app_id": null` is the same as choosing **Google standard player**, and leaving the key out is the same as **Stonies player**.

---

## Reliability

Stonies is designed to run unattended for months. The moving parts:

- **Self-healing NFC daemon** — on repeated reader errors the daemon re-configures the PN532, then rebuilds the whole I2C bus, and as a last resort exits so systemd restarts the service in a clean state. A glitching reader recovers in seconds instead of staying dead until a reboot.
- **Heartbeat watchdog** — a separate thread restarts the service if the NFC loop ever hangs inside an I2C call (`nfc_heartbeat_age` in `/api/nfc/status` exposes the same signal to the UI).
- **Bounded Chromecast lifecycles** — every speaker discovery/connection goes through one helper that always stops discovery and never leaves a connection retrying in the background, so long uptimes don't accumulate leaked threads and sockets.
- **Atomic saves** — `songs.json` and `config.json` are written via temp-file-and-rename, so a power cut can't corrupt the library (which would orphan every written NFC tag). A corrupt `songs.json` is reported, never silently regenerated.
- **Bounded server** — runs under waitress with a fixed thread pool (falls back to the Flask dev server if waitress isn't installed).
- **Capped activity log** — `activity.log` is trimmed automatically so it can't grow without bound.

If things ever look stuck, `sudo systemctl restart stonies` beats a reboot — and if NFC only recovers after a full power cycle, suspect the reader's wiring/power rather than software.

---

## Notes

- The app starts cleanly even if the PN532 is not connected — the NFC daemon exits gracefully and Flask serves the UI normally. Useful for testing on a dev machine.
- Audio is served directly from the Pi to the Chromecast over HTTP — no internet required for playback.
- The frontend is a pre-built Vite + Vue 3 SPA. The `dist/` folder is committed so the Pi needs no Node.js installed. Run `npm run build` inside `frontend/` before committing any frontend source changes.
- `songs.json` and `config.json` are excluded from version control as they contain personal library data and are generated at runtime.

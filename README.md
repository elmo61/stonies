# Stonies

A Raspberry Pi app that lets you tap NFC stickers to cast music to Google/Chromecast speakers. Each sticker is linked to a song — tap it, and that song starts playing. A web UI handles adding songs, managing speakers, and writing new stickers.

---

## How it works

Two things run in the same Python process:

- **NFC daemon** (background thread) — owns the PN532 reader, loops forever listening for stickers. When a sticker is tapped it reads the ID, looks it up in `songs.json`, and tells the Chromecast to fetch and play the audio file served by this same app.
- **Flask web server** (main thread) — serves the Vue UI and a REST API for managing songs, speakers, and NFC write operations.

When you add a new song via the UI:
1. The audio file is uploaded and saved to `music/`
2. A 6-character hex ID is generated and saved to `songs.json`
3. The daemon switches into **write mode** — tap a blank sticker and the ID gets written to it
4. From then on, tapping that sticker casts the song

**Offline mode** lets you tap stickers without casting — the matched song name shows in the UI instead. Useful for testing or when you just want to see what a sticker is linked to.

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

## Setup

See [INSTALL.md](INSTALL.md) for the full step-by-step install guide.

Quick version:

```bash
# Enable I2C on the Pi
sudo raspi-config  # Interface Options → I2C → Enable
sudo reboot

# Install system dependencies
sudo apt update && sudo apt install python3-dev python3-venv i2c-tools

# Verify NFC board is detected
i2cdetect -y 1  # should show '24' or '48' in the grid

# Set up the app
git clone https://github.com/your-username/stonies.git
cd stonies
python3 -m venv env
source env/bin/activate
pip install flask flask-cors pychromecast RPi.GPIO adafruit-blinka adafruit-circuitpython-pn532

# Run
python main.py
```

Open `http://<pi-ip>:5000` in a browser on any device on the same network.

---

## Usage

### First-time setup
1. Open the UI and click **Refresh** under Speaker to scan the network
2. Select your Google/Chromecast speaker from the dropdown and click **Save**

### Adding a song
1. Click **+ Add Song**
2. Enter a name, pick an audio file (`.mp3` or `.m4a`), optionally add a cover image URL
3. Click **Upload & Write Tag** — the file uploads and the banner changes to *"Touch the sticker now..."*
4. Tap a blank NFC sticker against the PN532 — it gets written and the song appears in the library
5. From now on, tapping that sticker plays the song on your configured speaker

### Re-tagging a song
If you want to write a song's ID to a new sticker (e.g. the old one broke), click the **🏷 Tag** button next to that song in the library and tap a sticker.

### Offline mode
Click the **Online** button at the top to switch to offline mode. In this mode, tapping stickers shows the matched song in the UI but does not cast anything. Click again to go back online.

---

## File structure

```
main.py          Entry point — starts daemon thread and Flask
nfc_daemon.py    NFCState class + NFC read/write helpers + background loop
api.py           Flask REST API (factory pattern)
index.html       Vue 3 + Bulma single-page frontend (no build step)
INSTALL.md       Full install guide
music/           Audio files (gitignored — add your own)
songs.json       Song database (gitignored — generated at runtime)
config.json      Saved speaker config (gitignored — generated at runtime)
```

---

## API reference

| Method | Path | Description |
|---|---|---|
| GET | `/` | Serves the UI |
| GET | `/music/<filename>` | Serves audio to Chromecast |
| GET | `/api/speakers` | Discover Chromecast speakers on the network |
| GET | `/api/config` | Get saved speaker config |
| POST | `/api/config` | Save `{ speaker }` |
| GET | `/api/songs` | List all songs |
| POST | `/api/songs` | Upload a new song (multipart: `name`, `file`, `image_url`) |
| DELETE | `/api/songs/<id>` | Delete a song and its audio file |
| POST | `/api/songs/<id>/retag` | Write tag for an existing song |
| GET | `/api/nfc/status` | NFC daemon state |
| POST | `/api/nfc/cancel` | Cancel a pending write |
| POST | `/api/offline/toggle` | Toggle offline mode |
| POST | `/api/play` | Manually cast a song by ID |

---

## Notes

- The app starts cleanly even if the PN532 is not connected — the NFC daemon exits gracefully and Flask runs normally. Useful for testing the UI on a dev machine.
- Audio files are served directly from the Pi to the Chromecast over HTTP — no internet required.
- `songs.json` and `config.json` are excluded from version control as they contain personal data and are generated at runtime.

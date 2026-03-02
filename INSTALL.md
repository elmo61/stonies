# Stonies — Install Guide

Tested on Raspberry Pi OS Lite (armv7l, Python 3.13).

## 1. System dependencies

These must be installed before pip packages, as some require compiling C extensions.

```bash
sudo apt update
sudo apt install python3-dev python3-venv
```

## 2. Create a virtual environment

```bash
cd projects/stonies
python3 -m venv env
source env/bin/activate
```

## 3. Install Python packages

```bash
pip install flask flask-cors pychromecast RPi.GPIO adafruit-blinka adafruit-circuitpython-pn532
```

| Package | Purpose |
|---|---|
| `flask` | Web server |
| `flask-cors` | CORS headers for the API |
| `pychromecast` | Discover and cast to Google speakers |
| `RPi.GPIO` | GPIO access (required by adafruit-blinka) |
| `adafruit-blinka` | CircuitPython hardware abstraction layer |
| `adafruit-circuitpython-pn532` | PN532 NFC reader driver over I2C |

## 4. Hardware wiring (PN532 via I2C)

| PN532 pin | Pi pin |
|---|---|
| VCC | 3.3V (Pin 1) |
| GND | GND (Pin 6) |
| SDA | GPIO 2 / SDA (Pin 3) |
| SCL | GPIO 3 / SCL (Pin 5) |

Make sure I2C is enabled on the Pi:

```bash
sudo raspi-config
# Interface Options → I2C → Enable
```

## 5. Run

```bash
source env/bin/activate
python main.py
```

Access the UI at `http://<pi-ip>:5000`.

## Notes

- The app will start even if the PN532 is not connected — the NFC daemon exits gracefully and Flask runs normally.
- Audio files are stored in `music/` and served directly to Chromecast devices.
- `songs.json` and `config.json` are created automatically on first run.

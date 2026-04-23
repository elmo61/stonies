# Stonies — Install Guide

Tested on Raspberry Pi OS Lite (armv7l, Python 3.11+).

---

## Option A — Automatic (recommended)
Ensure you have git installed 
```bash
sudo apt update
sudo apt install git -y
```

Then run this single command on a fresh Pi to install the stonies

```bash
git clone https://github.com/elmo61/stonies.git && bash stonies/setup.sh
```

The script will:
1. Install system packages (`python3-dev`, `python3-venv`, `i2c-tools`)
2. Enable I2C
3. Create a Python virtual environment at `projects/stonies/env/`
4. Install all pip packages
5. Register and start a systemd service so Stonies auto-starts on every boot

---

## Option B — Manual

### 1. Enable I2C

```bash
sudo raspi-config
# Interface Options → I2C → Enable
sudo reboot
```

### 2. System dependencies

```bash
sudo apt update
sudo apt install python3-dev python3-venv i2c-tools
```

### 3. Clone the repo

```bash
git clone https://github.com/elmo61/stonies.git
cd stonies/projects/stonies
```

### 4. Create a virtual environment

```bash
python3 -m venv env
source env/bin/activate
```

### 5. Install Python packages

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

### 6. Run

```bash
source env/bin/activate
python main.py
```

Open `http://<pi-ip>:5000` in a browser on any device on the same network.

---

## Hardware wiring (PN532 via I2C)

| PN532 pin | Pi GPIO header |
|---|---|
| VCC | Pin 1 (3.3V) |
| GND | Pin 6 |
| SDA | Pin 3 (GPIO 2) |
| SCL | Pin 5 (GPIO 3) |

> If your PN532 module has DIP switches, set both to **OFF** for I2C mode.

You can verify the board is detected with:

```bash
sudo apt install i2c-tools
i2cdetect -y 1  # should show '24' or '48' in the grid
```

---

## Auto-start on boot (systemd)

The `setup.sh` script does this automatically. For a manual install, copy the included service file:

```bash
sudo cp stonies.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable stonies
sudo systemctl start stonies
```

**Useful commands:**

```bash
sudo systemctl status stonies    # check it's running
sudo systemctl restart stonies   # apply changes after editing code
sudo systemctl stop stonies      # stop it
journalctl -u stonies -f         # live logs
journalctl -u stonies -n 50      # last 50 log lines
```

---

## Notes

- The app starts cleanly even without the PN532 connected — the NFC daemon exits gracefully and Flask runs normally. Useful for testing the UI without hardware.
- `songs.json` and `config.json` are created automatically on first run.
- Audio files live in `music/` and are served directly to Chromecast devices over HTTP — no internet needed.

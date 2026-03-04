#!/usr/bin/env bash
# Stonies — one-shot setup for a fresh Raspberry Pi
# Usage: bash setup.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"
SERVICE_USER="${USER:-pi}"

echo ""
echo "╔══════════════════════════════════╗"
echo "║      Stonies Setup               ║"
echo "╚══════════════════════════════════╝"
echo "  App dir : $APP_DIR"
echo "  User    : $SERVICE_USER"
echo ""

# ── 1. System packages ──────────────────────────────────────────────────────
echo ">>> [1/5] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y python3-dev python3-venv

# ── 2. Enable I2C ───────────────────────────────────────────────────────────
echo ">>> [2/5] Enabling I2C..."
sudo raspi-config nonint do_i2c 0

# ── 3. Python virtual environment ───────────────────────────────────────────
echo ">>> [3/5] Creating Python venv..."
python3 -m venv "$APP_DIR/env"

# ── 4. Python packages ──────────────────────────────────────────────────────
echo ">>> [4/5] Installing Python packages (this may take a minute)..."
"$APP_DIR/env/bin/pip" install --upgrade pip -q
"$APP_DIR/env/bin/pip" install \
    flask \
    flask-cors \
    pychromecast \
    RPi.GPIO \
    adafruit-blinka \
    adafruit-circuitpython-pn532

# ── 5. Systemd service ──────────────────────────────────────────────────────
echo ">>> [5/5] Installing systemd service..."
sudo tee /etc/systemd/system/stonies.service > /dev/null <<EOF
[Unit]
Description=Stonies NFC Music Player
After=network.target

[Service]
User=$SERVICE_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/env/bin/python main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable stonies
sudo systemctl restart stonies

# ── Done ────────────────────────────────────────────────────────────────────
PI_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  All done! Stonies is running.               ║"
echo "║                                              ║"
echo "║  Open: http://$PI_IP:5000"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Handy commands:"
echo "  sudo systemctl status stonies   # check it's running"
echo "  journalctl -u stonies -f        # live logs"
echo "  sudo systemctl restart stonies  # restart after code changes"
echo ""

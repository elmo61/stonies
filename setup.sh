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
echo ">>> [1/4] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y python3-dev python3-venv i2c-tools

# ── 2. Enable I2C ───────────────────────────────────────────────────────────
echo ">>> [2/4] Enabling I2C..."
sudo raspi-config nonint do_i2c 0

# ── 3. Python virtual environment ───────────────────────────────────────────
echo ">>> [3/4] Creating Python venv..."
python3 -m venv "$APP_DIR/env"
"$APP_DIR/env/bin/pip" install --upgrade pip -q

# ── 4. Packages + systemd service (shared with update.sh) ───────────────────
echo ">>> [4/4] Installing packages and service (this may take a minute)..."
bash "$APP_DIR/update.sh" --skip-pull

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

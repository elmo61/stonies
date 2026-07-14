#!/usr/bin/env bash
# Stonies — update an existing install in place.
#
# Usage:
#   bash update.sh              pull latest code, update deps + service, restart
#   bash update.sh --skip-pull  everything except the git pull (used by setup.sh)
#
# Safe to run repeatedly — every step is idempotent and only changes what
# actually differs.
set -e

# All work happens inside functions: bash parses the whole file before main()
# runs, so a git pull that rewrites this script mid-update can't corrupt the
# currently running copy.

render_unit() {
    # Render the checked-in stonies.service template for this install's
    # user and location, so one template works for any clone path.
    sed -e "s|^User=.*|User=$SERVICE_USER|" \
        -e "s|^WorkingDirectory=.*|WorkingDirectory=$APP_DIR|" \
        -e "s|^ExecStart=.*|ExecStart=$APP_DIR/env/bin/python main.py|" \
        "$APP_DIR/stonies.service"
}

main() {
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    APP_DIR="$SCRIPT_DIR"
    SERVICE_USER="${USER:-pi}"
    UNIT_PATH="/etc/systemd/system/stonies.service"

    cd "$APP_DIR"

    if [[ ! -d "$APP_DIR/env" ]]; then
        echo "No Python venv found at $APP_DIR/env — run 'bash setup.sh' first."
        exit 1
    fi

    if [[ "${1:-}" != "--skip-pull" ]]; then
        echo ">>> [1/4] Pulling latest code..."
        git pull --ff-only
    else
        echo ">>> [1/4] Skipping git pull"
    fi

    echo ">>> [2/4] Updating Python packages..."
    "$APP_DIR/env/bin/pip" install -q --upgrade -r "$APP_DIR/requirements.txt"

    echo ">>> [3/4] Checking systemd service..."
    RENDERED="$(render_unit)"
    if [[ ! -f "$UNIT_PATH" ]] || ! diff -q <(echo "$RENDERED") "$UNIT_PATH" > /dev/null 2>&1; then
        echo "$RENDERED" | sudo tee "$UNIT_PATH" > /dev/null
        sudo systemctl daemon-reload
        sudo systemctl enable stonies > /dev/null 2>&1
        echo "    service file updated"
    else
        echo "    service file unchanged"
    fi

    echo ">>> [4/4] Restarting Stonies..."
    sudo systemctl restart stonies

    echo ""
    echo "Update complete — now running: $(git log -1 --pretty='%h %s')"
    echo "Check it:  sudo systemctl status stonies"
}

main "$@"

# Feature: WiFi Hotspot Fallback

## Overview
When taking the Pi away from home, it should automatically fall back to hotspot mode if the home WiFi isn't found. The web UI should reflect the current mode and offer a way to return to home network.

## Desired Behaviour
1. Pi boots and tries to connect to home WiFi
2. After ~2 minutes with no connection, it activates a WiFi hotspot
3. Phone connects to the hotspot and opens the web UI
4. UI shows a banner indicating hotspot mode
5. UI offers a "Reboot" button to retry home network connection (reboot re-triggers the fallback logic)

## Implementation Plan

### 1. Hotspot profile (NetworkManager)
Pre-configure the hotspot so it can be activated on demand:
```bash
sudo nmcli device wifi hotspot ifname wlan0 ssid "stonies" password "yourpassword"
sudo nmcli connection modify stonies connection.autoconnect no
```
`autoconnect no` so it doesn't fight with home WiFi on normal boots.

### 2. Fallback script (`/usr/local/bin/wifi-fallback.sh`)
```bash
#!/bin/bash
# Wait up to 2 minutes for home network connection
for i in $(seq 1 24); do
    sleep 5
    ACTIVE=$(nmcli -t -f NAME connection show --active)
    if echo "$ACTIVE" | grep -qv "stonies" && nmcli -t -f STATE general | grep -q "connected"; then
        exit 0  # connected to home network, nothing to do
    fi
done
# No home network found — activate hotspot
nmcli connection up stonies
```

### 3. Systemd service (`/etc/systemd/system/wifi-fallback.service`)
```ini
[Unit]
Description=WiFi hotspot fallback
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/wifi-fallback.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Enable with:
```bash
sudo systemctl enable wifi-fallback.service
```

### 4. Flask API additions (`api.py`)
New endpoints:

**`GET /api/network/mode`**
Returns current mode. Check by inspecting active NetworkManager connections.
```python
import subprocess

def get_network_mode():
    result = subprocess.run(
        ['nmcli', '-t', '-f', 'NAME', 'connection', 'show', '--active'],
        capture_output=True, text=True
    )
    active = result.stdout.strip().split('\n')
    if 'stonies' in active:
        return 'hotspot'
    return 'home'

@app.route('/api/network/mode')
def network_mode():
    return jsonify({'mode': get_network_mode()})
```

**`POST /api/network/reboot`**
Triggers a reboot so the fallback script retries home network on next boot.
```python
@app.route('/api/network/reboot', methods=['POST'])
def network_reboot():
    subprocess.Popen(['sudo', 'reboot'])
    return jsonify({'status': 'rebooting'})
```
Needs `sudo` permissions for the Flask user — add to `/etc/sudoers`:
```
pi ALL=(ALL) NOPASSWD: /sbin/reboot
```

### 5. Frontend banner (Vue / `index.html`)
On app mount, call `/api/network/mode`. If `hotspot`, show a dismissable top banner:

```
⚠ Hotspot mode — not connected to home network
[Reboot to reconnect]
```

Bulma notification component is a natural fit here.

## Open Questions
- What SSID/password to use for the hotspot? Could be hardcoded or configurable via UI.
- Should the UI also show the hotspot IP/SSID to make it easier to share with others?
- Could extend later: UI lets you enter home WiFi credentials and switch without rebooting.

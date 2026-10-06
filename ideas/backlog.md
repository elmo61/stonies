# Ideas Backlog

## Chosen next (picked 2026-10-06)

- **Status light on the box**: an RGB LED by the sticker spot that blinks when a sticker is read, when playing starts, and when something fails. Full plan and wiring: `led-status-light.md`
- **Control stickers**: special stickers for Stop, Pause, Next chapter and Bedtime (sleep timer), so kids don't need a phone
- **Updates that can't half-apply**: on 2026-10-06 rose pulled new code, then `pip install --upgrade` failed building `lgpio` and it never restarted. The page looked new, but the old program was still running. Plan:
  - stop upgrading every package on each update; install only what's missing, and pin versions
  - install and check first, then switch, and go back to the old version if the new one doesn't start
  - show the *running* version on "Is it working?", and warn if it differs from the code on disk
- ~~**Podcast and radio stickers**~~: built 2026-10-06 (newest or in-order episodes, radio search). Possible next steps: play on this phone, an episode list to pick from, auto-play the next episode when one finishes
- **Speakers with screens**: make the custom receiver great on Nest Hubs, with big cover art, chapter name and progress
- **Travel mode (Bluetooth or wired)**: the box plays the audio itself to a paired Bluetooth speaker (the Zero 2 W has Bluetooth 4.2), or to a USB audio dongle. Works with no Chromecast or Wi-Fi; pairs well with the Wi-Fi hotspot fallback. Note: Bluetooth and Wi-Fi share one radio on the Zero 2 W
- **Remote restart / remote help**: restart or fix a box without being at the Pi (on 2026-10-06 rose needed `sudo systemctl restart stonies` typed on the box). Starts with the "Restart box button" below
- **"What's new" in the app**: after an update, show the CHANGELOG entries since the last version
- **Tests on GitHub**: move the backend tests into the repo, run them with GitHub Actions on every push, and fail if `dist/` wasn't rebuilt after front-end changes

## Decided against (for now)

Shared master library across boxes, printing sticker labels from the app, recording your own stories, blank-sticker "what should this play?" setup, story progress following you between boxes, quiet hours, weekly listening summary, library tidy-up checker, auto-filling covers and chapter names when adding.

## Next: box-side work for the new UI

The redesigned UI (2026-10) shipped front-end first. These pieces need new code on the box, so they were deliberately left for later:

- **Pause / resume** — stop exists but no pause/resume on the Chromecast; the now-playing card has room for a pause button
- **Move what's playing to another speaker** — the speaker picker only changes where the *next* thing plays
- **Restart box button** — on the "Is it working?" screen
- **Wi-Fi hiccup history** — log Wi-Fi drops/reconnects so "Is it working?" can show "dropped twice today, reconnected by itself"
- **Network watchdog** — reconnect Wi-Fi (or restart cleanly) when the box falls off the network, instead of needing an unplug
- **Multi-box view** — one place to see every Stonies box; needs boxes to know about each other (each box only knows itself today)
- **HTTPS on the boxes** — the last step to a real installable app that opens offline. **The app side is done** (service worker, Install button, https-safe cover URLs, all on beta since 2026-10-06), so only the box setup remains. Plan: nginx on 443 in front of Stonies, keeping port 5000 http for the speakers, plus a setup script per box. Routes considered:
  - **DuckDNS + Let's Encrypt (recommended)** — free name per box, auto-renewing certificate via DNS challenge, nothing to install on phones; a timer on the box keeps the name pointed at its current address. Needs a DuckDNS account + token, and a check that the router doesn't block names pointing at home addresses.
  - **Own trusted certificate (mkcert)** — fully local, but the certificate must be installed on every phone, boxes need fixed addresses, manual renewal, and the master key needs guarding.
  - **Own domain (e.g. Cloudflare)** — like DuckDNS but sturdier, if a domain is ever bought.
  - Tailscale also works, but needs the app on every phone.
- **Albums as a real type** — the upload screen offers Album, but the box still saves albums as `audiobook`, so they show under Stories

## Not yet built

- **Volume control** — no API endpoint or UI slider
- **Speaker caching** — fresh mDNS scan every call is slow; cache last-known speaker and try it first
- **Queue / playlist** — line up multiple songs to play in order
- **WiFi hotspot fallback** — see `wifi-hotspot-fallback.md` for full spec
- **Guest QR code** — show a QR on screen to scan and instantly join hotspot / open app
- **Multi-room** — cast to multiple Chromecasts at the same time

## For kids specifically

- **Sticker gallery view** — big cards with artwork instead of a table, one tap to play, less reading required
- **"Read to me" mode** — auto-advance audiobook chapters without any interaction
- **Favourites / pin to top** — star the most-used songs so they're always first
- **Play count badge** — show how many times something has been played

## Day-to-day quality of life

- **Last played section** — shows the last 3-5 things played at the top for quick resuming
- **Resume banner on load** — if something was playing when the app last closed, show a "resume X?" prompt on open

## Admin / maintenance

- **Bulk delete** — select multiple songs and delete at once
- **Replace cover image** — swap artwork on an existing song without re-uploading audio
- **Auto-sleep after inactivity** — if nothing played for X hours, stop Chromecast and cancel sleep timer

## Bigger / longer term

- **Spotify / YouTube Music import** — paste a URL, Pi downloads via yt-dlp and adds it automatically
- **Bedtime mode** — one tap sets volume low, enables sleep timer, dims the UI
- **Pin / lock screen** — simple PIN so kids can use the app but can't delete songs or change settings

## Already done (for reference)
Upload, delete, rename, album art, audiobook + chapter progress, NFC write/retag,
offline mode (now "Quiet mode"), now playing bar, stop, sleep timer, activity log, sync between devices,
update checker, search, import scan, disk usage, settings, play on this phone,
mobile-first UI redesign (big tap targets, ⋮ menus, tap a chapter to play), "Is it working?"
status screen (Wi-Fi strength, reader, speaker found, storage warning), speaker picker,
plain-English activity timeline, "box isn't answering" screen, add to home screen

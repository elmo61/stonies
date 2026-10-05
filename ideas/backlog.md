# Ideas Backlog

## Next: box-side work for the new UI

The redesigned UI (2026-10) shipped front-end first. These pieces need new code on the box, so they were deliberately left for later:

- **Pause / resume** — stop exists but no pause/resume on the Chromecast; the now-playing card has room for a pause button
- **Move what's playing to another speaker** — the speaker picker only changes where the *next* thing plays
- **Restart box button** — on the "Is it working?" screen
- **Wi-Fi hiccup history** — log Wi-Fi drops/reconnects so "Is it working?" can show "dropped twice today, reconnected by itself"
- **Network watchdog** — reconnect Wi-Fi (or restart cleanly) when the box falls off the network, instead of needing an unplug
- **Multi-box view** — one place to see every Stonies box; needs boxes to know about each other (each box only knows itself today)
- **HTTPS on the boxes** — needed for a real installable app that opens offline (browsers only allow offline caching on https). Best bet: a free DuckDNS name per box + Let's Encrypt DNS-challenge certificate, renewed on the Pi. Alternatives: Tailscale, or mkcert/self-signed (warnings on every phone)
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

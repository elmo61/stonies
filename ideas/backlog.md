# Ideas Backlog

## Not yet built

- **Pause / resume** — stop exists but no pause/resume controls on Chromecast
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
- **Speaker health indicator** — small dot next to speaker name showing if it's reachable right now
- **"Play on this device" button** — use browser audio API to play directly on phone instead of casting

## Admin / maintenance

- **Bulk delete** — select multiple songs and delete at once
- **Replace cover image** — swap artwork on an existing song without re-uploading audio
- **Storage warning** — banner when disk is under X GB free (disk usage API already exists)
- **Auto-sleep after inactivity** — if nothing played for X hours, stop Chromecast and cancel sleep timer

## Bigger / longer term

- **Spotify / YouTube Music import** — paste a URL, Pi downloads via yt-dlp and adds it automatically
- **Bedtime mode** — one tap sets volume low, enables sleep timer, dims the UI
- **Pin / lock screen** — simple PIN so kids can use the app but can't delete songs or change settings

## Already done (for reference)
Upload, delete, rename, album art, audiobook + chapter progress, NFC write/retag,
offline mode, now playing bar, stop, sleep timer, activity log, sync between devices,
update checker, search, import scan, disk usage, settings

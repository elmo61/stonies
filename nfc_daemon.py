import ctypes
import ctypes.util
import json
import os
import socket
import time
import threading
from datetime import datetime

from storage import save_json


def _set_thread_name(name):
    """Set the OS-level thread name (visible in top -H). Max 15 chars on Linux."""
    try:
        libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
        libc.prctl(15, name[:15].encode(), 0, 0, 0)
    except Exception:
        pass


def get_ip():
    """Resolve the Pi's current LAN IP. Called fresh at cast time to avoid stale IPs."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def _resolve_cast_ip(fallback_ip, log_fn=None):
    """Resolve the current LAN IP, falling back to fallback_ip with a warning if unavailable."""
    ip = get_ip()
    if ip == "127.0.0.1":
        msg = f"WARNING: could not resolve LAN IP, falling back to {fallback_ip}"
        print(f"[Cast] {msg}")
        if log_fn:
            log_fn(msg)
        return fallback_ip
    return ip


def find_cast(speaker_name, timeout=10):
    """Discover and connect to the named speaker, returning a connected Chromecast.

    Discovery is always stopped, even on failure — a leaked browser costs
    ~5 zeroconf threads plus multicast sockets per call, which accumulates
    until the whole process runs out of resources. Connection retries are
    bounded (tries=2) so a failed socket can never retry forever.
    Raises RuntimeError if the speaker is not found.
    """
    import pychromecast

    chromecasts, browser = pychromecast.get_listed_chromecasts(
        friendly_names=[speaker_name], tries=2
    )
    try:
        if not chromecasts:
            raise RuntimeError(f"Speaker '{speaker_name}' not found")
        cast = chromecasts[0]
        try:
            cast.wait(timeout=timeout)
        except Exception:
            try:
                cast.disconnect()
            except Exception:
                pass
            raise
        return cast
    finally:
        pychromecast.discovery.stop_discovery(browser)


class NFCState:
    """Thread-safe shared state between the NFC daemon and Flask threads."""

    def __init__(self):
        self._lock = threading.Lock()
        self._mode = "listening"       # "listening" | "writing"
        self._sub_state = None         # None | "waiting_for_tag" | "writing_tag" | "success" | "error"
        self._pending_song_id = None
        self._error_msg = None         # hardware init error, or write error message
        self._hw_error = None          # set if PN532 failed to init
        self._offline = False          # offline mode: read tags but don't cast
        self._last_seen_song = None    # last matched song in offline mode
        self._log = []                 # activity log entries [{seq, time, msg}]
        self._log_seq = 0
        self._sleep_timer = None       # threading.Timer for bedtime stop
        self._sleep_stops_at = None    # ISO string when sleep will fire
        self._write_started_at = None  # time.time() when write mode was entered
        self._stonies_playing = False  # True only when Stonies itself initiated playback
        self._current_song_id = None   # song id currently being cast
        self._current_chapter_index = None
        self._nfc_heartbeat = None     # time.time() of last daemon loop iteration

    # --- Public API for Flask ---

    def add_log(self, msg):
        with self._lock:
            self._log_seq += 1
            self._log.append({
                "seq": self._log_seq,
                "time": datetime.now().strftime("%H:%M:%S"),
                "msg": msg,
            })
            if len(self._log) > 200:
                self._log = self._log[-200:]

    def schedule_sleep(self, seconds, stop_fn):
        """Start a sleep timer, cancelling any existing one."""
        self.cancel_sleep()
        from datetime import timedelta
        stops_at = datetime.now() + timedelta(seconds=seconds)
        t = threading.Timer(seconds, stop_fn)
        t.daemon = True
        t.start()
        with self._lock:
            self._sleep_timer = t
            self._sleep_stops_at = stops_at.isoformat(timespec="seconds")

    def cancel_sleep(self):
        """Cancel any active sleep timer."""
        with self._lock:
            t = self._sleep_timer
            self._sleep_timer = None
            self._sleep_stops_at = None
        if t:
            t.cancel()

    def get_status(self):
        with self._lock:
            heartbeat_age = round(time.time() - self._nfc_heartbeat, 1) if self._nfc_heartbeat else None
            return {
                "mode": self._mode,
                "sub_state": self._sub_state,
                "error": self._error_msg,
                "hw_error": self._hw_error,
                "offline": self._offline,
                "last_seen_song": self._last_seen_song,
                "sleep_stops_at": self._sleep_stops_at,
                "stonies_playing": self._stonies_playing,
                "current_song_id": self._current_song_id,
                "current_chapter_index": self._current_chapter_index,
                "nfc_heartbeat_age": heartbeat_age,
                "log": list(self._log),
            }

    def set_playing(self, val):
        with self._lock:
            self._stonies_playing = val
            if not val:
                self._current_song_id = None
                self._current_chapter_index = None

    def set_now_playing(self, song_id, chapter_index=None):
        with self._lock:
            self._stonies_playing = True
            self._current_song_id = song_id
            self._current_chapter_index = chapter_index

    def toggle_offline(self):
        with self._lock:
            self._offline = not self._offline
            if not self._offline:
                self._last_seen_song = None
            return self._offline

    def request_write(self, song_id):
        with self._lock:
            self._mode = "writing"
            self._pending_song_id = song_id
            self._sub_state = "waiting_for_tag"
            self._error_msg = None
            self._write_started_at = time.time()

    def cancel_write(self):
        with self._lock:
            self._mode = "listening"
            self._sub_state = None
            self._pending_song_id = None
            self._error_msg = None

    def set_hw_error(self, msg):
        with self._lock:
            self._hw_error = msg

    # --- Internal daemon use ---

    def _get_offline(self):
        with self._lock:
            return self._offline

    def _set_last_seen(self, song):
        with self._lock:
            self._last_seen_song = {
                "id": song.get("id"),
                "name": song.get("name"),
                "image_url": song.get("image_url", ""),
            }

    def _get_mode(self):
        with self._lock:
            return self._mode

    def _get_write_id(self):
        with self._lock:
            return self._pending_song_id

    def _set_sub_state(self, sub_state, error_msg=None):
        with self._lock:
            self._sub_state = sub_state
            if error_msg is not None:
                self._error_msg = error_msg

    def _revert_to_listening(self):
        with self._lock:
            self._mode = "listening"
            self._sub_state = None
            self._pending_song_id = None


# ---------------------------------------------------------------------------
# NFC helpers
# ---------------------------------------------------------------------------

def read_blocks(pn532):
    """Read blocks 4-39 from tag and return stripped ASCII string."""
    full_message = ""
    for block_num in range(4, 40):
        try:
            data = pn532.ntag2xx_read_block(block_num)
            if data is None:
                break
            chunk = "".join([chr(b) if 32 <= b <= 126 else "" for b in data])
            if not chunk.strip() and block_num > 10:
                break
            full_message += chunk
        except Exception:
            break
    return full_message.strip()


def write_blocks(pn532, text):
    """Pad text to 4-byte boundary, write from block 4, then clear trailing blocks."""
    while len(text) % 4 != 0:
        text += " "
    current_block = 4
    for i in range(0, len(text), 4):
        chunk = text[i:i + 4]
        data = bytearray(chunk, "utf-8")
        pn532.ntag2xx_write_block(current_block, data)
        current_block += 1
        time.sleep(0.1)
    # Overwrite trailing blocks with nulls so old longer content doesn't bleed through
    empty = bytearray(4)
    while current_block <= 15:
        pn532.ntag2xx_write_block(current_block, empty)
        current_block += 1
        time.sleep(0.1)


# ---------------------------------------------------------------------------
# Song / cast helpers
# ---------------------------------------------------------------------------

def lookup_song(id_str, songs_path, songs_lock):
    """Return matching song dict from songs.json or None."""
    with songs_lock:
        try:
            with open(songs_path, "r") as f:
                songs = json.load(f)
        except Exception:
            return None
    for song in songs:
        if song.get("id") == id_str:
            return song
    return None


def update_play_stats(song_id, songs_path, songs_lock):
    """Increment play_count and update first_played / last_played for a song."""
    now = datetime.now().isoformat(timespec="seconds")
    with songs_lock:
        try:
            with open(songs_path, "r") as f:
                songs = json.load(f)
            for s in songs:
                if s.get("id") == song_id:
                    s["play_count"] = s.get("play_count", 0) + 1
                    s["last_played"] = now
                    if not s.get("first_played"):
                        s["first_played"] = now
                    break
            save_json(songs_path, songs)
        except Exception:
            pass


def cast_audiobook(song, config_path, config_lock, pi_ip, start_index=0, start_time=0, log_fn=None):
    """Queue all chapters of an audiobook on the configured speaker. Raises on any failure."""
    from urllib.parse import quote

    pi_ip = _resolve_cast_ip(pi_ip, log_fn)

    with config_lock:
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception:
            config = {}

    speaker_name = config.get("speaker", "").strip()
    if not speaker_name:
        raise RuntimeError("No speaker configured")
    cast_app_id = config.get("cast_app_id", "A0D905F0") or None

    folder = song.get("folder", "")
    chapters = song.get("chapters", [])
    if not chapters:
        raise RuntimeError("Audiobook has no chapters")

    queue_items = []
    for i, ch in enumerate(chapters):
        url = f"http://{pi_ip}:5000/music/{quote(folder)}/{quote(ch['filename'])}"
        if i == 0:
            msg = f"Casting audiobook from {url}"
            print(f"[Cast] {msg}")
            if log_fn:
                log_fn(msg)
        filename = ch["filename"]
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        mime = "audio/mp4" if ext == "m4a" else "audio/mpeg"
        book_name = song.get("name", "")
        image_url = song.get("image_url", "")
        metadata = {
            "metadataType": 3,          # MusicTrackMediaMetadata
            "title": ch.get("name", f"Chapter {i + 1}"),
            "albumName": book_name,
            "trackNumber": i + 1,
        }
        if image_url:
            metadata["images"] = [{"url": image_url}]
        queue_items.append({
            "autoplay": True,
            "preloadTime": 3,
            "media": {
                "contentId": url,
                "contentType": mime,
                "streamType": "BUFFERED",
                "metadata": metadata,
            },
        })

    cast = find_cast(speaker_name)
    try:
        mc = cast.media_controller
        mc.update_status()
        time.sleep(0.5)
        if mc.status and mc.status.player_state not in (None, "IDLE", "UNKNOWN"):
            mc.stop()
            time.sleep(1)
        if cast_app_id and getattr(cast.status, "app_id", None) != cast_app_id:
            cast.start_app(cast_app_id)
            time.sleep(2)
            mc = cast.media_controller
        mc.send_message(
            {
                "type": "QUEUE_LOAD",
                "repeatMode": "REPEAT_OFF",
                "startIndex": start_index,
                "currentTime": start_time,
                "items": queue_items,
            },
            inc_session_id=True,
        )
        mc.block_until_active(timeout=10)
    finally:
        cast.disconnect()


def cast_song(song, config_path, config_lock, pi_ip, log_fn=None):
    """Cast a song to the configured speaker. Raises on any failure."""
    from urllib.parse import quote

    pi_ip = _resolve_cast_ip(pi_ip, log_fn)

    with config_lock:
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception:
            config = {}

    speaker_name = config.get("speaker", "").strip()
    if not speaker_name:
        raise RuntimeError("No speaker configured")
    cast_app_id = config.get("cast_app_id", "A0D905F0") or None

    filename = song.get("filename", "")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime = "audio/mp4" if ext == "m4a" else "audio/mpeg"
    url = f"http://{pi_ip}:5000/music/{quote(filename)}"
    msg = f"Casting track from {url}"
    print(f"[Cast] {msg}")
    if log_fn:
        log_fn(msg)

    cast = find_cast(speaker_name)
    try:
        mc = cast.media_controller
        mc.update_status()
        time.sleep(0.5)
        if mc.status and mc.status.player_state not in (None, "IDLE", "UNKNOWN"):
            mc.stop()
            time.sleep(1)
        kwargs = {"title": song.get("name", ""), "thumb": song.get("image_url") or None}
        if cast_app_id:
            kwargs["app_id"] = cast_app_id
        mc.play_media(url, mime, **kwargs)
        mc.block_until_active(timeout=10)
    finally:
        cast.disconnect()


# ---------------------------------------------------------------------------
# Sleep timer helpers
# ---------------------------------------------------------------------------

def sleep_timer_seconds(config):
    """Return duration in seconds if sleep timer should apply right now, else None."""
    st = config.get("sleep_timer", {})
    if not st.get("enabled"):
        return None
    after_time = st.get("after_time", "19:00")
    duration_minutes = int(st.get("duration_minutes", 60))
    try:
        now = datetime.now()
        h, m = map(int, after_time.split(":"))
        if now.hour > h or (now.hour == h and now.minute >= m):
            return duration_minutes * 60
    except Exception:
        pass
    return None


def make_stop_fn(config_path, config_lock, pi_ip, state, log_path=None):
    """Return a callback that stops Chromecast playback (used by sleep timer)."""
    def _stop():
        import time as _time
        from activity_log import write_log
        try:
            with config_lock:
                with open(config_path, "r") as f:
                    cfg = json.load(f)
            speaker_name = cfg.get("speaker", "").strip()
            if not speaker_name:
                return
            cast = find_cast(speaker_name, timeout=5)
            try:
                mc = cast.media_controller
                mc.update_status()
                _time.sleep(1)
                mc.stop()
                state.add_log("Sleep timer fired — playback stopped")
                if log_path:
                    write_log(log_path, "Sleep timer fired — playback stopped")
            finally:
                cast.disconnect()
        except Exception as e:
            state.add_log(f"Sleep timer stop failed: {e}")
        finally:
            with state._lock:
                state._sleep_timer = None
                state._sleep_stops_at = None
    return _stop


def check_and_schedule_sleep(state, config_path, config_lock, pi_ip, log_path=None):
    """Read config and schedule a sleep timer if conditions are met."""
    try:
        with config_lock:
            with open(config_path, "r") as f:
                cfg = json.load(f)
    except Exception:
        return
    secs = sleep_timer_seconds(cfg)
    if secs:
        state.schedule_sleep(secs, make_stop_fn(config_path, config_lock, pi_ip, state, log_path))
        state.add_log(f"Sleep timer set — stops in {secs // 60} min")


# ---------------------------------------------------------------------------
# Daemon loop
# ---------------------------------------------------------------------------

def _init_pn532():
    """Create the I2C bus and PN532, and configure it. Returns (i2c, pn532)."""
    import board
    import busio
    from adafruit_pn532.i2c import PN532_I2C

    i2c = busio.I2C(board.SCL, board.SDA)
    pn532 = PN532_I2C(i2c, debug=False)
    pn532.SAM_configuration()
    return i2c, pn532


def _daemon_iteration(state, pn532, songs_path, songs_lock, config_path,
                      config_lock, pi_ip, log_path, monitor):
    """One pass of the NFC loop. Raises on reader/I2C errors."""
    mode = state._get_mode()

    if mode == "listening":
        uid = pn532.read_passive_target(timeout=0.5)
        if uid is None:
            return
        uid_str = uid.hex().upper()
        state.add_log(f"Tag detected: {uid_str}")
        id_str = None
        song = None
        try:
            raw = read_blocks(pn532)
            print(f"[NFC] Tag read: '{raw}'")
            PREFIX = "stonies:"
            if raw and not raw.startswith(PREFIX):
                state.add_log(f"Unrecognized tag (not a Stonies tag): \"{raw[:20]}\"")
                id_str = None
            else:
                id_str = raw[len(PREFIX):] if raw else None
            if id_str:
                song = lookup_song(id_str, songs_path, songs_lock)
                if song:
                    if state._get_offline():
                        print(f"[NFC] Offline — tag matched: '{song['name']}'")
                        state._set_last_seen(song)
                        state.add_log(f"Offline — matched \"{song['name']}\" (not casting)")
                    else:
                        print(f"[NFC] Casting '{song['name']}'...")
                        state.add_log(f"Casting \"{song['name']}\"...")
                        state.set_playing(True)
                        def _do_cast(s=song):
                            try:
                                if s.get("type") in ("audiobook", "album"):
                                    prog = s.get("progress", {})
                                    start_index = prog.get("chapter_index", 0)
                                    cast_audiobook(
                                        s, config_path, config_lock, pi_ip,
                                        start_index=start_index,
                                        start_time=prog.get("current_time", 0),
                                        log_fn=state.add_log,
                                    )
                                    state.set_now_playing(s["id"], chapter_index=start_index)
                                else:
                                    cast_song(s, config_path, config_lock, pi_ip,
                                              log_fn=state.add_log)
                                    state.set_now_playing(s["id"])
                                if monitor:
                                    monitor.on_play()
                                update_play_stats(s["id"], songs_path, songs_lock)
                                print(f"[NFC] Now playing '{s['name']}'")
                                state.add_log(f"Now playing \"{s['name']}\"")
                                if log_path:
                                    from activity_log import write_log
                                    write_log(log_path, f'"{s["name"]}" started playing (NFC)')
                                check_and_schedule_sleep(state, config_path, config_lock, pi_ip, log_path)
                            except Exception as e:
                                print(f"[NFC] Cast error: {e}")
                                state.add_log(f"Cast failed: {e}")
                                state.set_playing(False)
                        t = threading.Thread(target=_do_cast, daemon=True)
                        t.start()
                else:
                    print(f"[NFC] No song found for id '{id_str}'")
                    state.add_log(f"No song found for ID \"{id_str}\"")
            else:
                state.add_log(f"Tag {uid_str}: no data")
        except Exception as e:
            print(f"[NFC] Read error: {e}")
            state.add_log(f"Read error: {e}")
        # Longer pause after a recognised song so holding the tag doesn't re-trigger
        debounce = 5 if (id_str and song) else 3
        time.sleep(debounce)

    elif mode == "writing":
        song_id = state._get_write_id()
        if song_id is None:
            time.sleep(0.1)
            return

        # Auto-cancel after 20 seconds if no tag presented (song stays saved)
        with state._lock:
            started = state._write_started_at
        if started and (time.time() - started) > 20:
            state.add_log("Write timed out — no tag presented. Song is saved.")
            print("[NFC] Write mode timed out, reverting to listening")
            state._revert_to_listening()
            return

        state._set_sub_state("waiting_for_tag")
        uid = pn532.read_passive_target(timeout=0.5)

        if uid is not None:
            state._set_sub_state("writing_tag")
            state.add_log(f"Writing tag for song \"{song_id}\"...")
            try:
                write_blocks(pn532, f"stonies:{song_id}")
                print(f"[NFC] Wrote song id '{song_id}' to tag")
                state.add_log(f"Tag written successfully for \"{song_id}\"")
                state._set_sub_state("success")
                time.sleep(5)
            except Exception as e:
                print(f"[NFC] Write error: {e}")
                state.add_log(f"Write failed: {e}")
                state._set_sub_state("error", error_msg=str(e))
                time.sleep(5)
            finally:
                state._revert_to_listening()
    else:
        time.sleep(0.1)


def run_daemon(state, songs_path, songs_lock, config_path, config_lock, pi_ip, log_path=None, monitor=None):
    """Background NFC loop. Owns the PN532 exclusively.

    Self-healing: on repeated errors it re-configures the PN532, then rebuilds
    the whole I2C bus, and as a last resort exits the process so systemd
    (Restart=always) brings everything back in a known-good state. Previously
    a wedged reader stayed dead until the Pi was rebooted.
    """
    _set_thread_name("nfc-daemon")
    from activity_log import write_log

    try:
        i2c, pn532 = _init_pn532()
        print("[NFC] PN532 online. Listening for tags...")
        state.add_log("NFC reader online")
        if log_path:
            write_log(log_path, "NFC reader started")
    except Exception as e:
        msg = f"PN532 not available: {e}"
        print(f"[NFC] {msg}")
        state.set_hw_error(msg)
        return  # Flask still runs; daemon exits cleanly

    consecutive_errors = 0

    while True:
        try:
            with state._lock:
                state._nfc_heartbeat = time.time()
            _daemon_iteration(state, pn532, songs_path, songs_lock,
                              config_path, config_lock, pi_ip, log_path, monitor)
            if consecutive_errors:
                print("[NFC] Reader recovered")
                state.add_log("NFC reader recovered")
                if log_path:
                    write_log(log_path, "NFC reader recovered")
            consecutive_errors = 0
        except Exception as e:
            consecutive_errors += 1
            print(f"[NFC] Daemon loop error #{consecutive_errors} (will retry): {e}")
            if consecutive_errors == 1:
                # Log only the first of a run of errors — one per second
                # would drown the activity log
                state.add_log(f"NFC error (retrying): {e}")
            time.sleep(1)

            # Escalating recovery: re-configure the chip, then rebuild the
            # bus from scratch, then give up and let systemd restart us.
            if consecutive_errors in (5, 10):
                try:
                    pn532.SAM_configuration()
                    print("[NFC] PN532 re-configured")
                except Exception as re_err:
                    print(f"[NFC] PN532 re-configuration failed: {re_err}")
            elif consecutive_errors in (15, 20, 25):
                try:
                    try:
                        i2c.deinit()
                    except Exception:
                        pass
                    i2c, pn532 = _init_pn532()
                    print("[NFC] I2C bus and PN532 rebuilt")
                    state.add_log("NFC reader re-initialised")
                except Exception as re_err:
                    print(f"[NFC] PN532 rebuild failed: {re_err}")
            elif consecutive_errors >= 30:
                msg = "NFC reader unrecoverable — exiting so systemd can restart the service"
                print(f"[NFC] {msg}")
                state.add_log(msg)
                if log_path:
                    write_log(log_path, msg)
                os._exit(1)


def run_watchdog(state, log_path=None, stale_after=120, check_every=30):
    """Exit the process (systemd restarts it) if the NFC daemon stops beating.

    Covers the failure mode the retry loop can't: an I2C call that hangs
    forever inside the kernel driver, freezing the daemon thread. Does
    nothing in web-only mode (PN532 never initialised).
    """
    _set_thread_name("nfc-watchdog")
    from activity_log import write_log

    while True:
        time.sleep(check_every)
        with state._lock:
            heartbeat = state._nfc_heartbeat
            hw_error = state._hw_error
        if hw_error or heartbeat is None:
            continue
        age = time.time() - heartbeat
        if age > stale_after:
            msg = f"NFC daemon heartbeat stale ({int(age)}s) — exiting so systemd can restart the service"
            print(f"[Watchdog] {msg}")
            if log_path:
                write_log(log_path, msg)
            os._exit(1)

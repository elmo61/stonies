import json
import time
import threading
from datetime import datetime


class NFCState:
    """Thread-safe shared state between the NFC daemon and Flask threads."""

    def __init__(self):
        self._lock = threading.Lock()
        self._event = threading.Event()
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
        self._event.set()

    def cancel_write(self):
        with self._lock:
            self._mode = "listening"
            self._sub_state = None
            self._pending_song_id = None
            self._error_msg = None
        self._event.set()

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


def cast_audiobook(song, config_path, config_lock, pi_ip, start_index=0, start_time=0):
    """Queue all chapters of an audiobook on the configured speaker. Raises on any failure."""
    import pychromecast
    from urllib.parse import quote

    with config_lock:
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception:
            config = {}

    speaker_name = config.get("speaker", "").strip()
    if not speaker_name:
        raise RuntimeError("No speaker configured")

    folder = song.get("folder", "")
    chapters = song.get("chapters", [])
    if not chapters:
        raise RuntimeError("Audiobook has no chapters")

    queue_items = []
    for i, ch in enumerate(chapters):
        url = f"http://{pi_ip}:5000/music/{quote(folder)}/{quote(ch['filename'])}"
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

    chromecasts, browser = pychromecast.get_listed_chromecasts(
        friendly_names=[speaker_name]
    )
    if not chromecasts:
        pychromecast.discovery.stop_discovery(browser)
        raise RuntimeError(f"Speaker '{speaker_name}' not found")

    cast = chromecasts[0]
    try:
        cast.wait()
        pychromecast.discovery.stop_discovery(browser)
        cast.media_controller.send_message(
            {
                "type": "QUEUE_LOAD",
                "repeatMode": "REPEAT_OFF",
                "startIndex": start_index,
                "currentTime": start_time,
                "items": queue_items,
            },
            inc_session_id=True,
        )
        cast.media_controller.block_until_active()
    finally:
        cast.disconnect()


def cast_song(song, config_path, config_lock, pi_ip):
    """Cast a song to the configured speaker. Raises on any failure."""
    import pychromecast

    with config_lock:
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception:
            config = {}

    speaker_name = config.get("speaker", "").strip()
    if not speaker_name:
        raise RuntimeError("No speaker configured")

    filename = song.get("filename", "")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime = "audio/mp4" if ext == "m4a" else "audio/mpeg"
    url = f"http://{pi_ip}:5000/music/{filename}"

    chromecasts, browser = pychromecast.get_listed_chromecasts(
        friendly_names=[speaker_name]
    )
    if not chromecasts:
        pychromecast.discovery.stop_discovery(browser)
        raise RuntimeError(f"Speaker '{speaker_name}' not found")

    cast = chromecasts[0]
    try:
        cast.wait()
        pychromecast.discovery.stop_discovery(browser)
        cast.media_controller.play_media(
            url, mime,
            title=song.get("name", ""),
            thumb=song.get("image_url") or None,
        )
        cast.media_controller.block_until_active()
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


def make_stop_fn(config_path, config_lock, pi_ip, state):
    """Return a callback that stops Chromecast playback (used by sleep timer)."""
    def _stop():
        import pychromecast
        import time as _time
        try:
            with config_lock:
                with open(config_path, "r") as f:
                    cfg = json.load(f)
            speaker_name = cfg.get("speaker", "").strip()
            if not speaker_name:
                return
            chromecasts, browser = pychromecast.get_listed_chromecasts(
                friendly_names=[speaker_name]
            )
            if not chromecasts:
                pychromecast.discovery.stop_discovery(browser)
                return
            cast = chromecasts[0]
            try:
                cast.wait(timeout=5)
                pychromecast.discovery.stop_discovery(browser)
                mc = cast.media_controller
                mc.update_status()
                _time.sleep(1)
                mc.stop()
                state.add_log("Sleep timer fired — playback stopped")
            finally:
                cast.disconnect()
        except Exception as e:
            state.add_log(f"Sleep timer stop failed: {e}")
        finally:
            with state._lock:
                state._sleep_timer = None
                state._sleep_stops_at = None
    return _stop


def check_and_schedule_sleep(state, config_path, config_lock, pi_ip):
    """Read config and schedule a sleep timer if conditions are met."""
    try:
        with config_lock:
            with open(config_path, "r") as f:
                cfg = json.load(f)
    except Exception:
        return
    secs = sleep_timer_seconds(cfg)
    if secs:
        state.schedule_sleep(secs, make_stop_fn(config_path, config_lock, pi_ip, state))
        state.add_log(f"Sleep timer set — stops in {secs // 60} min")


# ---------------------------------------------------------------------------
# Position tracker (runs every 2 minutes, saves progress to songs.json)
# ---------------------------------------------------------------------------

def run_position_tracker(state, songs_path, songs_lock, config_path, config_lock):
    """Background thread: polls Chromecast every 2 minutes and saves audiobook progress."""
    import pychromecast
    from urllib.parse import unquote, urlparse
    import time as _time

    while True:
        _time.sleep(120)

        with state._lock:
            playing = state._stonies_playing
            song_id = state._current_song_id

        if not playing or not song_id:
            continue

        state.add_log("Position tracker: checking...")
        try:
            with config_lock:
                with open(config_path, "r") as f:
                    config = json.load(f)
            speaker_name = config.get("speaker", "").strip()
            if not speaker_name:
                state.add_log("Position tracker: no speaker configured")
                continue

            chromecasts, browser = pychromecast.get_listed_chromecasts(
                friendly_names=[speaker_name]
            )
            if not chromecasts:
                pychromecast.discovery.stop_discovery(browser)
                state.add_log("Position tracker: speaker not found")
                continue

            cast = chromecasts[0]
            player_state = None
            content_id = ""
            current_time = 0
            try:
                cast.wait(timeout=10)
                pychromecast.discovery.stop_discovery(browser)
                mc = cast.media_controller
                mc.update_status()
                _time.sleep(1)
                # Capture all values before disconnect clears the status object
                if mc.status:
                    player_state = mc.status.player_state
                    content_id = mc.status.content_id or ""
                    current_time = round(mc.status.current_time or 0, 1)
            finally:
                cast.disconnect()

            if player_state not in ("PLAYING", "PAUSED", "BUFFERING"):
                state.add_log(f"Position tracker: not playing ({player_state})")
                state.set_playing(False)
                continue

            # Identify chapter from content URL for audiobooks
            chapter_idx = None
            try:
                parts = urlparse(content_id).path.split("/music/", 1)
                if len(parts) == 2:
                    path_parts = unquote(parts[1]).split("/", 1)
                    if len(path_parts) == 2:
                        folder, ch_file = path_parts
                        with songs_lock:
                            with open(songs_path, "r") as f:
                                songs = json.load(f)
                        for s in songs:
                            if s.get("id") == song_id and s.get("type") == "audiobook":
                                for i, ch in enumerate(s.get("chapters", [])):
                                    if ch.get("filename") == ch_file:
                                        chapter_idx = i
                                        break
                                break
            except Exception:
                pass

            # Save progress for audiobooks only
            with songs_lock:
                try:
                    with open(songs_path, "r") as f:
                        songs = json.load(f)
                except Exception:
                    continue
                for s in songs:
                    if s.get("id") == song_id and s.get("type") == "audiobook":
                        progress = {
                            "current_time": current_time,
                            "updated_at": datetime.now().isoformat(timespec="seconds"),
                        }
                        if chapter_idx is not None:
                            progress["chapter_index"] = chapter_idx
                            with state._lock:
                                state._current_chapter_index = chapter_idx
                        s["progress"] = progress
                        with open(songs_path, "w") as f:
                            json.dump(songs, f, indent=2)
                        state.add_log(f"Progress saved: ch{(chapter_idx or 0) + 1} @ {int(current_time)}s")
                        break

        except Exception as e:
            state.add_log(f"Position tracker error: {e}")


# ---------------------------------------------------------------------------
# Daemon loop
# ---------------------------------------------------------------------------

def run_daemon(state, songs_path, songs_lock, config_path, config_lock, pi_ip):
    """Background NFC loop. Owns the PN532 exclusively."""
    try:
        import board
        import busio
        from adafruit_pn532.i2c import PN532_I2C

        i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
        pn532 = PN532_I2C(i2c, debug=False)
        pn532.SAM_configuration()
        print("[NFC] PN532 online. Listening for tags...")
        state.add_log("NFC reader online")
    except Exception as e:
        msg = f"PN532 not available: {e}"
        print(f"[NFC] {msg}")
        state.set_hw_error(msg)
        return  # Flask still runs; daemon exits cleanly

    while True:
      try:
        with state._lock:
            state._nfc_heartbeat = time.time()
        mode = state._get_mode()

        if mode == "listening":
            uid = pn532.read_passive_target(timeout=0.5)
            if uid is not None:
                uid_str = uid.hex().upper()
                state.add_log(f"Tag detected: {uid_str}")
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
                                        if s.get("type") == "audiobook":
                                            prog = s.get("progress", {})
                                            start_index = prog.get("chapter_index", 0)
                                            cast_audiobook(
                                                s, config_path, config_lock, pi_ip,
                                                start_index=start_index,
                                                start_time=prog.get("current_time", 0),
                                            )
                                            state.set_now_playing(s["id"], chapter_index=start_index)
                                        else:
                                            cast_song(s, config_path, config_lock, pi_ip)
                                            state.set_now_playing(s["id"])
                                        print(f"[NFC] Now playing '{s['name']}'")
                                        state.add_log(f"Now playing \"{s['name']}\"")
                                        check_and_schedule_sleep(state, config_path, config_lock, pi_ip)
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
                time.sleep(3)  # debounce

        elif mode == "writing":
            song_id = state._get_write_id()
            if song_id is None:
                time.sleep(0.1)
                continue

            # Auto-cancel after 20 seconds if no tag presented (song stays saved)
            with state._lock:
                started = state._write_started_at
            if started and (time.time() - started) > 20:
                state.add_log("Write timed out — no tag presented. Song is saved.")
                print("[NFC] Write mode timed out, reverting to listening")
                state._revert_to_listening()
                continue

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

      except Exception as e:
        print(f"[NFC] Daemon loop error (will retry): {e}")
        state.add_log(f"NFC error (retrying): {e}")
        time.sleep(1)

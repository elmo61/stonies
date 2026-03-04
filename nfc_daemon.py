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

    def get_status(self):
        with self._lock:
            return {
                "mode": self._mode,
                "sub_state": self._sub_state,
                "error": self._error_msg,
                "hw_error": self._hw_error,
                "offline": self._offline,
                "last_seen_song": self._last_seen_song,
                "log": list(self._log),
            }

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
        queue_items.append({
            "autoplay": True,
            "preloadTime": 3,
            "media": {
                "contentId": url,
                "contentType": mime,
                "streamType": "BUFFERED",
                "metadata": {
                    "metadataType": 0,
                    "title": ch.get("name", f"Chapter {i + 1}"),
                },
            },
        })

    chromecasts, browser = pychromecast.get_listed_chromecasts(
        friendly_names=[speaker_name]
    )
    if not chromecasts:
        raise RuntimeError(f"Speaker '{speaker_name}' not found")

    cast = chromecasts[0]
    cast.wait()
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
        raise RuntimeError(f"Speaker '{speaker_name}' not found")

    cast = chromecasts[0]
    cast.wait()
    cast.media_controller.play_media(url, mime)
    cast.media_controller.block_until_active()


# ---------------------------------------------------------------------------
# Daemon loop
# ---------------------------------------------------------------------------

def run_daemon(state, songs_path, songs_lock, config_path, config_lock, pi_ip):
    """Background NFC loop. Owns the PN532 exclusively."""
    try:
        import board
        import busio
        from adafruit_pn532.i2c import PN532_I2C

        i2c = busio.I2C(board.SCL, board.SDA)
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
        mode = state._get_mode()

        if mode == "listening":
            uid = pn532.read_passive_target(timeout=0.5)
            if uid is not None:
                uid_str = uid.hex().upper()
                state.add_log(f"Tag detected: {uid_str}")
                try:
                    id_str = read_blocks(pn532)
                    print(f"[NFC] Tag read: '{id_str}'")
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
                                try:
                                    if song.get("type") == "audiobook":
                                        prog = song.get("progress", {})
                                        cast_audiobook(
                                            song, config_path, config_lock, pi_ip,
                                            start_index=prog.get("chapter_index", 0),
                                            start_time=prog.get("current_time", 0),
                                        )
                                    else:
                                        cast_song(song, config_path, config_lock, pi_ip)
                                    print(f"[NFC] Now playing '{song['name']}'")
                                    state.add_log(f"Now playing \"{song['name']}\"")
                                except Exception as e:
                                    print(f"[NFC] Cast error: {e}")
                                    state.add_log(f"Cast failed: {e}")
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

            state._set_sub_state("waiting_for_tag")
            uid = pn532.read_passive_target(timeout=0.5)

            if uid is not None:
                state._set_sub_state("writing_tag")
                state.add_log(f"Writing tag for song \"{song_id}\"...")
                try:
                    write_blocks(pn532, song_id)
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

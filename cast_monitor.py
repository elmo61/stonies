"""
Persistent Chromecast media status listener.

Runs as a background daemon thread. Maintains a long-lived connection to the
configured speaker so we receive push notifications for PLAYING / PAUSED /
FINISHED events instead of polling.

Responsibilities:
  - Log "finished" and "stopped" events to activity.log
  - Save audiobook position every 30 s during playback (push-driven)
  - Detect end-of-audiobook (last chapter FINISHED) and clear saved progress
  - Update NFCState when playback ends unexpectedly
"""
import json
import time
import threading
from datetime import datetime
from urllib.parse import unquote, urlparse


class _MediaListener:
    """Thin adapter — forwards pychromecast callbacks into CastMonitor."""

    def __init__(self, on_status):
        self._on_status = on_status

    def new_media_status(self, status):
        try:
            self._on_status(status)
        except Exception as e:
            print(f"[Monitor] Callback error: {e}")


class CastMonitor:

    def __init__(self, state, songs_path, songs_lock,
                 config_path, config_lock, log_path):
        self._state = state
        self._songs_path = songs_path
        self._songs_lock = songs_lock
        self._config_path = config_path
        self._config_lock = config_lock
        self._log_path = log_path
        self._cast = None
        self._connected_speaker = None
        self._last_player_state = None
        self._last_position_save = 0

    def start(self):
        t = threading.Thread(target=self._run, daemon=True, name="cast-monitor")
        t.start()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _run(self):
        try:
            import ctypes, ctypes.util
            libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
            libc.prctl(15, b"cast-monitor", 0, 0, 0)
        except Exception:
            pass
        backoff = 15
        while True:
            try:
                speaker = self._get_speaker()
                if not speaker:
                    time.sleep(30)
                    continue

                # Reconnect if speaker changed
                if self._connected_speaker != speaker:
                    self._disconnect()

                if self._cast is None:
                    self._connect(speaker)
                    if self._cast is None:
                        time.sleep(backoff)
                        backoff = min(backoff * 2, 120)
                        continue
                    backoff = 15  # reset on success

                # Connection established — pychromecast manages the socket
                # and delivers callbacks on its own background thread.
                # Sleep and let it do its thing; we only reconnect on exception
                # or if the speaker config changes.
                time.sleep(60)

            except Exception as e:
                print(f"[Monitor] Unexpected error: {e}")
                self._disconnect()
                time.sleep(backoff)
                backoff = min(backoff * 2, 120)

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _get_speaker(self):
        try:
            with self._config_lock:
                with open(self._config_path, "r") as f:
                    config = json.load(f)
            return config.get("speaker", "").strip()
        except Exception:
            return ""

    def _connect(self, speaker_name):
        import pychromecast
        print(f"[Monitor] Connecting to '{speaker_name}'...")
        try:
            chromecasts, browser = pychromecast.get_listed_chromecasts(
                friendly_names=[speaker_name]
            )
            if not chromecasts:
                pychromecast.discovery.stop_discovery(browser)
                print(f"[Monitor] Speaker '{speaker_name}' not found")
                return
            cast = chromecasts[0]
            cast.wait(timeout=10)
            pychromecast.discovery.stop_discovery(browser)
            cast.media_controller.register_status_listener(
                _MediaListener(self._on_media_status)
            )
            self._cast = cast
            self._connected_speaker = speaker_name
            print(f"[Monitor] Connected to '{speaker_name}'")
        except Exception as e:
            print(f"[Monitor] Connect failed: {e}")

    def _disconnect(self):
        cast = self._cast
        self._cast = None
        self._connected_speaker = None
        self._last_player_state = None
        if cast:
            try:
                cast.disconnect()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Media status callback (runs on pychromecast socket thread)
    # ------------------------------------------------------------------

    def _on_media_status(self, status):
        from activity_log import write_log

        player_state = status.player_state
        idle_reason = getattr(status, "idle_reason", None) if player_state == "IDLE" else None
        current_time = round(status.current_time or 0, 1)
        content_id = status.content_id or ""

        with self._state._lock:
            stonies_playing = self._state._stonies_playing
            song_id = self._state._current_song_id
            chapter_index = self._state._current_chapter_index

        if not stonies_playing or not song_id:
            self._last_player_state = player_state
            return

        song = self._lookup_song(song_id)
        song_name = song.get("name", "Unknown") if song else "Unknown"
        prev_state = self._last_player_state
        self._last_player_state = player_state

        if player_state == "IDLE":
            if idle_reason == "FINISHED":
                # Only treat as the end of everything when the last chapter finishes.
                # Mid-queue FINISHED events (between chapters) are ignored.
                if self._is_last_chapter(song, content_id):
                    write_log(self._log_path, f'"{song_name}" finished')
                    self._state.add_log(f'"{song_name}" finished')
                    self._state.set_playing(False)
                    if song and song.get("type") == "audiobook":
                        # Clear saved progress so next play starts from the beginning
                        self._clear_progress(song_id)

            elif idle_reason in ("CANCELLED", "INTERRUPTED"):
                if prev_state in ("PLAYING", "PAUSED", "BUFFERING"):
                    write_log(self._log_path, f'"{song_name}" stopped')
                    self._state.set_playing(False)

        # Throttled position save for audiobooks while playing/paused
        if (player_state in ("PLAYING", "PAUSED")
                and song and song.get("type") == "audiobook"):
            now = time.time()
            if now - self._last_position_save >= 30:
                self._last_position_save = now
                self._save_progress(song_id, song, chapter_index, current_time, content_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _lookup_song(self, song_id):
        with self._songs_lock:
            try:
                with open(self._songs_path, "r") as f:
                    songs = json.load(f)
                return next((s for s in songs if s.get("id") == song_id), None)
            except Exception:
                return None

    def _is_last_chapter(self, song, content_id):
        """True if content_id refers to the last chapter, or if this is a track."""
        if not song or song.get("type") != "audiobook":
            return True  # tracks always count as final
        if not content_id:
            return True
        try:
            path = urlparse(content_id).path
            parts = path.split("/music/", 1)
            if len(parts) == 2:
                ch_file = unquote(parts[1]).split("/", 1)[-1]
                chapters = song.get("chapters", [])
                return bool(chapters) and chapters[-1].get("filename") == ch_file
        except Exception:
            pass
        return False

    def _clear_progress(self, song_id):
        with self._songs_lock:
            try:
                with open(self._songs_path, "r") as f:
                    songs = json.load(f)
                for s in songs:
                    if s.get("id") == song_id:
                        s.pop("progress", None)
                        break
                with open(self._songs_path, "w") as f:
                    json.dump(songs, f, indent=2)
            except Exception:
                pass

    def _save_progress(self, song_id, song, chapter_index, current_time, content_id):
        """Save audiobook position, identifying chapter from content URL if possible."""
        if content_id:
            try:
                path = urlparse(content_id).path
                parts = path.split("/music/", 1)
                if len(parts) == 2:
                    ch_file = unquote(parts[1]).split("/", 1)[-1]
                    for i, ch in enumerate(song.get("chapters", [])):
                        if ch.get("filename") == ch_file:
                            chapter_index = i
                            with self._state._lock:
                                self._state._current_chapter_index = chapter_index
                            break
            except Exception:
                pass

        with self._songs_lock:
            try:
                with open(self._songs_path, "r") as f:
                    songs = json.load(f)
                for s in songs:
                    if s.get("id") == song_id and s.get("type") == "audiobook":
                        progress = {
                            "current_time": current_time,
                            "updated_at": datetime.now().isoformat(timespec="seconds"),
                        }
                        if chapter_index is not None:
                            progress["chapter_index"] = chapter_index
                        s["progress"] = progress
                        break
                with open(self._songs_path, "w") as f:
                    json.dump(songs, f, indent=2)
            except Exception:
                pass

import json
import os
import re
import secrets
import shutil
import threading
import urllib.request
import urllib.error
from urllib.parse import quote as url_quote
from datetime import datetime

import pychromecast
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

from nfc_daemon import cast_audiobook, cast_song, lookup_song, check_and_schedule_sleep, update_play_stats
from activity_log import write_log


AUDIO_EXTS = (".mp3", ".m4a")


def derive_track_name(filename):
    """Derive a display name from an audio filename."""
    name = filename.rsplit(".", 1)[0]
    name = re.sub(r'^CH\d+[\s\-_]+', '', name, flags=re.IGNORECASE)
    name = name.replace("-", " ").replace("_", " ")
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.title()
    name = re.sub(r"(\w)'S\b", r"\1's", name)
    return name or filename.rsplit(".", 1)[0]


def derive_book_name(folder_name):
    """Derive a display name from a folder name."""
    name = re.sub(r'^\d+[\s\-_]+', '', folder_name)
    name = name.replace("-", " ").replace("_", " ")
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.title()
    name = re.sub(r"(\w)'S\b", r"\1's", name)
    return name or folder_name


def scan_audiobooks(music_folder, existing_songs):
    """Scan music_folder for subdirectories not already in existing_songs.
    Returns a list of new audiobook entries to append."""
    existing_folders = {s.get("folder") for s in existing_songs if s.get("type") == "audiobook"}
    new_entries = []

    try:
        entries = os.listdir(music_folder)
    except Exception:
        return []

    for entry in sorted(entries):
        entry_path = os.path.join(music_folder, entry)
        if not os.path.isdir(entry_path):
            continue
        if entry in existing_folders:
            continue

        try:
            files = sorted([f for f in os.listdir(entry_path) if f.lower().endswith(AUDIO_EXTS)])
        except Exception:
            continue

        if not files:
            continue

        chapters = [{"filename": f, "name": derive_track_name(f)} for f in files]
        new_entries.append({
            "id": secrets.token_hex(3),
            "type": "audiobook",
            "name": derive_book_name(entry),
            "folder": entry,
            "chapters": chapters,
            "image_url": "",
            "uploaded_at": datetime.now().isoformat(timespec="seconds"),
        })

    return new_entries


def run_sync(peer_hostname, pi_ip, songs_path, songs_lock, music_folder,
             images_folder, sync_job, sync_job_lock, log_path=None):
    """Background thread: pulls missing songs from a peer Stonies device."""
    from activity_log import write_log as _write_log

    def update(**kwargs):
        with sync_job_lock:
            sync_job.update(kwargs)

    pulled, errors = [], []

    try:
        update(status="running", current="Fetching catalogue from peer...")

        # Try hostname as-is, then with .local
        candidates = [peer_hostname]
        if not peer_hostname.endswith(".local"):
            candidates.append(peer_hostname + ".local")
        peer_songs = None
        resolved_host = peer_hostname
        last_err = None
        for h in candidates:
            try:
                req = urllib.request.urlopen(f"http://{h}:5000/api/songs", timeout=15)
                peer_songs = json.loads(req.read().decode()).get("songs", [])
                resolved_host = h
                break
            except Exception as e:
                last_err = e
        if peer_songs is None:
            raise last_err
        peer_url = f"http://{resolved_host}:5000"

        with songs_lock:
            try:
                with open(songs_path) as f:
                    local_songs = json.load(f)
            except Exception:
                local_songs = []

        local_ids = {s["id"] for s in local_songs}
        missing = [s for s in peer_songs if s["id"] not in local_ids]

        if not missing:
            update(status="complete", total=0, done=0, current="",
                   pulled=[], skipped=[], errors=[])
            return

        update(total=len(missing), done=0)

        for song in missing:
            song_name = song.get("name", "Unknown")
            song_id = song["id"]
            update(current=song_name)

            try:
                song_copy = {
                    "id": song_id,
                    "type": song.get("type", "track"),
                    "name": song_name,
                    "image_url": "",
                    "uploaded_at": song.get("uploaded_at", ""),
                }

                # Download cover image
                peer_img = song.get("image_url", "")
                if peer_img and "/images/" in peer_img:
                    img_filename = peer_img.rsplit("/images/", 1)[-1]
                    local_img = os.path.join(images_folder, img_filename)
                    urllib.request.urlretrieve(
                        f"{peer_url}/images/{url_quote(img_filename)}", local_img
                    )
                    song_copy["image_url"] = f"http://{pi_ip}:5000/images/{img_filename}"

                if song.get("type") == "audiobook":
                    folder = song.get("folder", song_id)
                    chapters = song.get("chapters", [])
                    folder_path = os.path.join(music_folder, folder)
                    os.makedirs(folder_path, exist_ok=True)
                    for ch in chapters:
                        ch_file = ch["filename"]
                        urllib.request.urlretrieve(
                            f"{peer_url}/music/{url_quote(folder)}/{url_quote(ch_file)}",
                            os.path.join(folder_path, ch_file),
                        )
                    song_copy["folder"] = folder
                    song_copy["chapters"] = [
                        {"filename": ch["filename"], "name": ch["name"]}
                        for ch in chapters
                    ]
                else:
                    filename = song.get("filename", "")
                    urllib.request.urlretrieve(
                        f"{peer_url}/music/{url_quote(filename)}",
                        os.path.join(music_folder, filename),
                    )
                    song_copy["filename"] = filename

                # Append to local songs.json
                with songs_lock:
                    with open(songs_path) as f:
                        songs = json.load(f)
                    # Double-check it still doesn't exist (race safety)
                    if not any(s["id"] == song_id for s in songs):
                        songs.append(song_copy)
                        with open(songs_path, "w") as f:
                            json.dump(songs, f, indent=2)

                pulled.append(song_name)

            except Exception as e:
                errors.append(f"{song_name}: {e}")

            with sync_job_lock:
                sync_job["done"] += 1
                sync_job["pulled"] = list(pulled)
                sync_job["errors"] = list(errors)

        if log_path and pulled:
            _write_log(log_path, f"Sync from {peer_hostname}: pulled {len(pulled)} song(s)")

        update(status="complete", current="", pulled=pulled, skipped=[], errors=errors)

    except Exception as e:
        update(status="error", current="", errors=[str(e)])


def create_app(state, songs_lock, config_lock, music_folder, import_folder, images_folder, songs_path, config_path, pi_ip, log_path=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "frontend", "dist")
    app = Flask(__name__, static_folder=dist_dir, static_url_path="")
    CORS(app)

    # ------------------------------------------------------------------
    # Frontend — serve Vue SPA (history mode: all unknown routes → index.html)
    # ------------------------------------------------------------------

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def index(path):
        # API routes are handled before this catch-all
        if path.startswith("api/") or path.startswith("music/") or path.startswith("images/"):
            from flask import abort
            abort(404)
        file_path = os.path.join(dist_dir, path)
        if path and os.path.isfile(file_path):
            return send_file(file_path)
        return send_file(os.path.join(dist_dir, "index.html"))

    # ------------------------------------------------------------------
    # Audio serving
    # ------------------------------------------------------------------

    @app.route("/music/<path:filename>")
    def serve_music(filename):
        file_path = os.path.realpath(os.path.join(music_folder, filename))
        music_root = os.path.realpath(music_folder)
        if not file_path.startswith(music_root + os.sep) and file_path != music_root:
            return jsonify({"error": "Forbidden"}), 403
        if not os.path.isfile(file_path):
            return jsonify({"error": "Track not found"}), 404
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        mime = "audio/mp4" if ext == "m4a" else "audio/mpeg"
        return send_file(file_path, mimetype=mime, conditional=True)

    # ------------------------------------------------------------------
    # Image serving
    # ------------------------------------------------------------------

    @app.route("/images/<path:filename>")
    def serve_image(filename):
        file_path = os.path.realpath(os.path.join(images_folder, filename))
        images_root = os.path.realpath(images_folder)
        if not file_path.startswith(images_root + os.sep) and file_path != images_root:
            return jsonify({"error": "Forbidden"}), 403
        if not os.path.isfile(file_path):
            return jsonify({"error": "Image not found"}), 404
        return send_file(file_path, conditional=True)

    # ------------------------------------------------------------------
    # Speakers
    # ------------------------------------------------------------------

    @app.route("/api/speakers")
    def get_speakers():
        try:
            services, browser = pychromecast.discovery.discover_chromecasts()
            pychromecast.discovery.stop_discovery(browser)
            names = [s.friendly_name for s in services]
            return jsonify({"speakers": names})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    @app.route("/api/config", methods=["GET"])
    def get_config():
        with config_lock:
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        return jsonify(data)

    @app.route("/api/config", methods=["POST"])
    def save_config():
        body = request.get_json(silent=True) or {}
        speaker = body.get("speaker", "").strip()
        sleep_timer = body.get("sleep_timer")
        if not speaker and sleep_timer is None:
            return jsonify({"error": "Nothing to save"}), 400
        with config_lock:
            try:
                with open(config_path, "r") as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
            if speaker:
                existing["speaker"] = speaker
            if sleep_timer is not None:
                existing["sleep_timer"] = sleep_timer
            with open(config_path, "w") as f:
                json.dump(existing, f, indent=2)
        return jsonify({"ok": True, "speaker": existing.get("speaker", ""),
                        "sleep_timer": existing.get("sleep_timer")})

    # ------------------------------------------------------------------
    # Songs
    # ------------------------------------------------------------------

    @app.route("/api/songs", methods=["GET"])
    def get_songs():
        with songs_lock:
            try:
                with open(songs_path, "r") as f:
                    songs = json.load(f)
            except Exception:
                songs = []
            new_audiobooks = scan_audiobooks(music_folder, songs)
            if new_audiobooks:
                songs.extend(new_audiobooks)
                with open(songs_path, "w") as f:
                    json.dump(songs, f, indent=2)
        return jsonify({"songs": songs})

    @app.route("/api/songs", methods=["POST"])
    def add_song():
        name = request.form.get("name", "").strip()
        song_type = request.form.get("type", "track")

        if not name:
            return jsonify({"error": "name is required"}), 400

        song_id = secrets.token_hex(3)

        # Handle cover image upload
        image_url = ""
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            img_ext = image_file.filename.rsplit(".", 1)[-1].lower() if "." in image_file.filename else ""
            if img_ext in ("jpg", "jpeg", "png", "gif", "webp"):
                img_filename = f"{song_id}.{img_ext}"
                image_file.save(os.path.join(images_folder, img_filename))
                image_url = f"http://{pi_ip}:5000/images/{img_filename}"

        if song_type == "audiobook":
            files = request.files.getlist("files[]")
            valid = [(secure_filename(f.filename), f) for f in files if f.filename]
            valid = sorted(valid, key=lambda x: x[0])
            valid = [(n, f) for n, f in valid if n.rsplit(".", 1)[-1].lower() in ("mp3", "m4a")]
            if not valid:
                return jsonify({"error": "At least one .mp3 or .m4a file is required"}), 400

            try:
                chapter_names = json.loads(request.form.get("chapter_names", "[]"))
            except Exception:
                chapter_names = []

            folder_name = song_id
            folder_path = os.path.join(music_folder, folder_name)
            os.makedirs(folder_path, exist_ok=True)

            chapters = []
            for i, (safe_name, file_obj) in enumerate(valid):
                file_obj.save(os.path.join(folder_path, safe_name))
                ch_name = chapter_names[i] if i < len(chapter_names) else safe_name.rsplit(".", 1)[0]
                chapters.append({"filename": safe_name, "name": ch_name})

            song = {
                "id": song_id,
                "type": "audiobook",
                "name": name,
                "folder": folder_name,
                "chapters": chapters,
                "image_url": image_url,
                "uploaded_at": datetime.now().isoformat(timespec="seconds"),
            }

        else:
            file = request.files.get("file")
            if not file or file.filename == "":
                return jsonify({"error": "file is required"}), 400
            ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
            if ext not in ("mp3", "m4a"):
                return jsonify({"error": "Only .mp3 and .m4a files are supported"}), 400
            safe_name = secure_filename(file.filename)
            filename = f"{song_id}_{safe_name}"
            file.save(os.path.join(music_folder, filename))
            song = {
                "id": song_id,
                "type": "track",
                "name": name,
                "filename": filename,
                "image_url": image_url,
                "uploaded_at": datetime.now().isoformat(timespec="seconds"),
            }

        with songs_lock:
            try:
                with open(songs_path, "r") as f:
                    songs = json.load(f)
            except Exception:
                songs = []
            songs.append(song)
            with open(songs_path, "w") as f:
                json.dump(songs, f, indent=2)

        # Only request NFC write if the hardware is available
        if not state._hw_error:
            state.request_write(song_id)
            return jsonify({"id": song_id, "status": "pending"}), 202
        else:
            return jsonify({"id": song_id, "status": "saved"}), 200

    @app.route("/api/songs/<song_id>", methods=["PATCH"])
    def rename_song(song_id):
        body = request.get_json(silent=True) or {}
        name = body.get("name", "").strip()
        if not name:
            return jsonify({"error": "name is required"}), 400
        with songs_lock:
            try:
                with open(songs_path, "r") as f:
                    songs = json.load(f)
            except Exception:
                songs = []
            for s in songs:
                if s.get("id") == song_id:
                    s["name"] = name
                    break
            else:
                return jsonify({"error": "Song not found"}), 404
            with open(songs_path, "w") as f:
                json.dump(songs, f, indent=2)
        return jsonify({"ok": True, "name": name})

    @app.route("/api/songs/<song_id>/progress", methods=["DELETE"])
    def clear_progress(song_id):
        with songs_lock:
            try:
                with open(songs_path, "r") as f:
                    songs = json.load(f)
            except Exception:
                songs = []
            for s in songs:
                if s.get("id") == song_id:
                    s.pop("progress", None)
                    break
            else:
                return jsonify({"error": "Song not found"}), 404
            with open(songs_path, "w") as f:
                json.dump(songs, f, indent=2)
        return jsonify({"ok": True})

    @app.route("/api/songs/<song_id>", methods=["DELETE"])
    def delete_song(song_id):
        removed = None
        with songs_lock:
            try:
                with open(songs_path, "r") as f:
                    songs = json.load(f)
            except Exception:
                songs = []
            updated = [s for s in songs if s.get("id") != song_id]
            for s in songs:
                if s.get("id") == song_id:
                    removed = s
                    break
            with open(songs_path, "w") as f:
                json.dump(updated, f, indent=2)

        if removed:
            if removed.get("type") == "audiobook":
                folder_path = os.path.join(music_folder, removed.get("folder", ""))
                if os.path.isdir(folder_path):
                    shutil.rmtree(folder_path)
            else:
                file_path = os.path.join(music_folder, removed.get("filename", ""))
                if os.path.isfile(file_path):
                    os.remove(file_path)
            # Remove associated image file if it was locally hosted
            img_url = removed.get("image_url", "")
            if img_url and "/images/" in img_url:
                img_filename = img_url.rsplit("/images/", 1)[-1]
                img_path = os.path.join(images_folder, img_filename)
                if os.path.isfile(img_path):
                    os.remove(img_path)
            return jsonify({"ok": True})
        return jsonify({"error": "Song not found"}), 404

    # ------------------------------------------------------------------
    # Update / deploy
    # ------------------------------------------------------------------

    @app.route("/api/update/status", methods=["GET"])
    def update_status():
        import subprocess
        try:
            subprocess.run(["git", "fetch"], cwd=base_dir, capture_output=True, timeout=10)
            result = subprocess.run(
                ["git", "rev-list", "HEAD..origin/main", "--count"],
                cwd=base_dir, capture_output=True, text=True, timeout=5
            )
            behind = int(result.stdout.strip() or "0")
            return jsonify({"updates_available": behind > 0, "commits_behind": behind})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ------------------------------------------------------------------
    # Import scan
    # ------------------------------------------------------------------

    @app.route("/api/import/scan", methods=["POST"])
    def import_scan():
        imported = []
        errors = []

        try:
            entries = sorted(os.listdir(import_folder))
        except Exception as e:
            return jsonify({"error": f"Cannot read import folder: {e}"}), 500

        with songs_lock:
            try:
                with open(songs_path, "r") as f:
                    songs = json.load(f)
            except Exception:
                songs = []

            for entry in entries:
                entry_path = os.path.join(import_folder, entry)

                # Direct audio file → track
                if os.path.isfile(entry_path) and entry.lower().endswith(AUDIO_EXTS):
                    try:
                        song_id = secrets.token_hex(3)
                        safe_name = secure_filename(entry)
                        dest_filename = f"{song_id}_{safe_name}"
                        shutil.move(entry_path, os.path.join(music_folder, dest_filename))
                        song = {
                            "id": song_id,
                            "type": "track",
                            "name": derive_track_name(entry),
                            "filename": dest_filename,
                            "image_url": "",
                            "uploaded_at": datetime.now().isoformat(timespec="seconds"),
                        }
                        songs.append(song)
                        imported.append({"type": "track", "name": song["name"]})
                    except Exception as e:
                        errors.append(f"{entry}: {e}")

                # Subdirectory → audiobook
                elif os.path.isdir(entry_path):
                    try:
                        files = sorted([
                            f for f in os.listdir(entry_path)
                            if f.lower().endswith(AUDIO_EXTS)
                        ])
                        if not files:
                            continue
                        song_id = secrets.token_hex(3)
                        dest_folder = song_id
                        shutil.move(entry_path, os.path.join(music_folder, dest_folder))
                        chapters = [{"filename": f, "name": derive_track_name(f)} for f in files]
                        song = {
                            "id": song_id,
                            "type": "audiobook",
                            "name": derive_book_name(entry),
                            "folder": dest_folder,
                            "chapters": chapters,
                            "image_url": "",
                            "uploaded_at": datetime.now().isoformat(timespec="seconds"),
                        }
                        songs.append(song)
                        imported.append({"type": "audiobook", "name": song["name"], "chapters": len(chapters)})
                    except Exception as e:
                        errors.append(f"{entry}: {e}")

            if imported:
                with open(songs_path, "w") as f:
                    json.dump(songs, f, indent=2)

        return jsonify({"imported": imported, "errors": errors, "songs": songs})

    # ------------------------------------------------------------------
    # NFC status / cancel
    # ------------------------------------------------------------------

    @app.route("/api/nfc/status")
    def nfc_status():
        return jsonify(state.get_status())

    @app.route("/api/nfc/cancel", methods=["POST"])
    def nfc_cancel():
        # Get pending song id before cancelling so we can clean it up
        status = state.get_status()
        pending_id = None
        if status["mode"] == "writing":
            with state._lock:
                pending_id = state._pending_song_id

        state.cancel_write()

        # Remove orphaned song record + file if write hadn't succeeded
        if pending_id and status.get("sub_state") not in ("success",):
            removed = None
            with songs_lock:
                try:
                    with open(songs_path, "r") as f:
                        songs = json.load(f)
                except Exception:
                    songs = []
                updated = [s for s in songs if s.get("id") != pending_id]
                for s in songs:
                    if s.get("id") == pending_id:
                        removed = s
                        break
                with open(songs_path, "w") as f:
                    json.dump(updated, f, indent=2)
            if removed:
                if removed.get("type") == "audiobook":
                    folder_path = os.path.join(music_folder, removed.get("folder", ""))
                    if os.path.isdir(folder_path):
                        shutil.rmtree(folder_path)
                else:
                    file_path = os.path.join(music_folder, removed.get("filename", ""))
                    if os.path.isfile(file_path):
                        os.remove(file_path)

        return jsonify({"ok": True})

    # ------------------------------------------------------------------
    # Retag existing song
    # ------------------------------------------------------------------

    @app.route("/api/songs/<song_id>/retag", methods=["POST"])
    def retag_song(song_id):
        if state._hw_error:
            return jsonify({"error": "NFC reader not available"}), 400
        song = lookup_song(song_id, songs_path, songs_lock)
        if not song:
            return jsonify({"error": "Song not found"}), 404
        state.add_log(f"Tag write requested for \"{song['name']}\"")
        state.request_write(song_id)
        return jsonify({"ok": True, "status": "pending"})

    # ------------------------------------------------------------------
    # Device sync
    # ------------------------------------------------------------------

    _sync_job = {"status": "idle", "total": 0, "done": 0, "current": "",
                 "pulled": [], "skipped": [], "errors": []}
    _sync_job_lock = threading.Lock()

    def _normalise_peer(raw):
        """Strip http(s)://, port, and trailing slashes from a peer hostname."""
        h = raw.strip()
        for prefix in ("https://", "http://"):
            if h.startswith(prefix):
                h = h[len(prefix):]
        h = h.split("/")[0]   # drop any path
        h = h.rsplit(":", 1)[0]  # drop port if present
        return h.strip()

    def _fetch_peer_songs(hostname):
        """Try hostname as-is, then with .local appended. Returns (songs, resolved_hostname)."""
        candidates = [hostname]
        if not hostname.endswith(".local"):
            candidates.append(hostname + ".local")
        last_err = None
        for h in candidates:
            try:
                url = f"http://{h}:5000/api/songs"
                req = urllib.request.urlopen(url, timeout=10)
                songs = json.loads(req.read().decode()).get("songs", [])
                return songs, h
            except Exception as e:
                last_err = e
        raise last_err

    @app.route("/api/sync/preview", methods=["POST"])
    def sync_preview():
        body = request.get_json(silent=True) or {}
        raw_peer = body.get("peer", "").strip()
        if not raw_peer:
            return jsonify({"error": "peer is required"}), 400

        peer = _normalise_peer(raw_peer)
        try:
            peer_songs, resolved = _fetch_peer_songs(peer)
            peer = resolved  # use whichever hostname actually worked
        except Exception as e:
            return jsonify({"error": f"Cannot reach {peer}: {e}"}), 400

        with songs_lock:
            try:
                with open(songs_path) as f:
                    local_songs = json.load(f)
            except Exception:
                local_songs = []

        local_ids = {s["id"] for s in local_songs}
        missing = [
            {
                "id": s["id"],
                "name": s.get("name"),
                "type": s.get("type", "track"),
                "chapter_count": len(s.get("chapters", [])) if s.get("type") == "audiobook" else None,
            }
            for s in peer_songs if s["id"] not in local_ids
        ]

        # Save peer hostname to config for next time
        with config_lock:
            try:
                with open(config_path) as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}
            cfg["sync_peer"] = peer
            with open(config_path, "w") as f:
                json.dump(cfg, f, indent=2)

        return jsonify({"missing": missing, "peer": peer})

    @app.route("/api/sync/pull", methods=["POST"])
    def sync_pull():
        body = request.get_json(silent=True) or {}
        raw_peer = body.get("peer", "").strip()
        if not raw_peer:
            return jsonify({"error": "peer is required"}), 400
        peer = _normalise_peer(raw_peer)

        with _sync_job_lock:
            if _sync_job.get("status") == "running":
                return jsonify({"error": "Sync already in progress"}), 409
            _sync_job.update({"status": "running", "total": 0, "done": 0,
                               "current": "Starting...", "pulled": [], "skipped": [], "errors": []})

        t = threading.Thread(
            target=run_sync,
            args=(peer, pi_ip, songs_path, songs_lock, music_folder,
                  images_folder, _sync_job, _sync_job_lock, log_path),
            daemon=True,
        )
        t.start()
        return jsonify({"ok": True})

    @app.route("/api/sync/status")
    def sync_status():
        with _sync_job_lock:
            return jsonify(dict(_sync_job))

    # ------------------------------------------------------------------
    # Activity log
    # ------------------------------------------------------------------

    log_path = os.path.join(base_dir, "activity.log")

    @app.route("/api/log")
    def get_log():
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            lines = [l.rstrip("\n") for l in lines if l.strip()]
            return jsonify({"lines": lines[-1000:][::-1]})  # newest first
        except FileNotFoundError:
            return jsonify({"lines": []})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ------------------------------------------------------------------
    # Offline mode toggle
    # ------------------------------------------------------------------

    @app.route("/api/offline/toggle", methods=["POST"])
    def toggle_offline():
        is_offline = state.toggle_offline()
        return jsonify({"offline": is_offline})

    # ------------------------------------------------------------------
    # Manual play (web-triggered)
    # ------------------------------------------------------------------

    @app.route("/api/play", methods=["POST"])
    def play():
        body = request.get_json(silent=True) or {}
        song_id = body.get("id", "").strip()
        chapter_index = body.get("chapter_index")  # None = use saved progress
        if not song_id:
            return jsonify({"error": "id is required"}), 400

        song = lookup_song(song_id, songs_path, songs_lock)
        if not song:
            return jsonify({"error": "Song not found"}), 404

        try:
            state.add_log(f"Web play: \"{song['name']}\"...")
            if song.get("type") == "audiobook":
                prog = song.get("progress", {})
                if chapter_index is not None:
                    start_index, start_time = chapter_index, 0
                else:
                    start_index = prog.get("chapter_index", 0)
                    start_time = prog.get("current_time", 0)
                cast_audiobook(song, config_path, config_lock, pi_ip,
                               start_index=start_index, start_time=start_time)
                state.set_now_playing(song_id, chapter_index=start_index)
            else:
                cast_song(song, config_path, config_lock, pi_ip)
                state.set_now_playing(song_id)
            update_play_stats(song_id, songs_path, songs_lock)
            state.add_log(f"Now playing \"{song['name']}\"")
            if log_path:
                write_log(log_path, f'"{song["name"]}" started playing (web)')
            check_and_schedule_sleep(state, config_path, config_lock, pi_ip, log_path)
            return jsonify({"ok": True, "message": f"Now playing '{song['name']}'"})
        except Exception as e:
            state.set_playing(False)
            state.add_log(f"Play failed: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/playback/status")
    def playback_status():
        # Reads from state + songs.json only — no Chromecast connection.
        # Position is kept fresh by the background run_position_tracker thread.
        with state._lock:
            playing = state._stonies_playing
            song_id = state._current_song_id
            chapter_index = state._current_chapter_index

        if not playing or not song_id:
            return jsonify({"playing": False})

        with songs_lock:
            try:
                with open(songs_path, "r") as f:
                    songs = json.load(f)
            except Exception:
                songs = []

        matched = next((s for s in songs if s.get("id") == song_id), None)
        if not matched:
            return jsonify({"playing": False})

        result = {
            "playing": True,
            "song_id": song_id,
            "song_name": matched.get("name"),
            "song_type": matched.get("type", "track"),
            "chapter_index": chapter_index,
        }

        if matched.get("type") == "audiobook":
            prog = matched.get("progress", {})
            result["current_time"] = prog.get("current_time", 0)
            result["progress"] = prog

        return jsonify(result)

    @app.route("/api/playback/stop", methods=["POST"])
    def playback_stop():
        import pychromecast

        with config_lock:
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
            except Exception:
                config = {}

        speaker_name = config.get("speaker", "").strip()
        if not speaker_name:
            return jsonify({"error": "No speaker configured"}), 400

        try:
            import time as _time
            chromecasts, browser = pychromecast.get_listed_chromecasts(
                friendly_names=[speaker_name]
            )
            if not chromecasts:
                pychromecast.discovery.stop_discovery(browser)
                return jsonify({"error": f"Speaker '{speaker_name}' not found"}), 404
            cast = chromecasts[0]
            try:
                cast.wait(timeout=5)
                pychromecast.discovery.stop_discovery(browser)
                mc = cast.media_controller
                mc.update_status()
                _time.sleep(1)
                mc.stop()
            finally:
                cast.disconnect()
            state.set_playing(False)
            state.cancel_sleep()
            state.add_log(f"Playback stopped on \"{speaker_name}\"")
            if log_path:
                write_log(log_path, f'Playback stopped manually on "{speaker_name}"')
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app

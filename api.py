import json
import os
import secrets
from datetime import datetime

import pychromecast
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

from nfc_daemon import cast_song, lookup_song


def create_app(state, songs_lock, config_lock, music_folder, songs_path, config_path, pi_ip):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__, static_folder=base_dir, static_url_path="")
    CORS(app)

    # ------------------------------------------------------------------
    # Frontend
    # ------------------------------------------------------------------

    @app.route("/")
    def index():
        return send_file(os.path.join(base_dir, "index.html"))

    # ------------------------------------------------------------------
    # Audio serving
    # ------------------------------------------------------------------

    @app.route("/music/<filename>")
    def serve_music(filename):
        safe = os.path.basename(filename)
        file_path = os.path.join(music_folder, safe)
        if not os.path.isfile(file_path):
            return jsonify({"error": "Track not found"}), 404
        ext = safe.rsplit(".", 1)[-1].lower() if "." in safe else ""
        mime = "audio/mp4" if ext == "m4a" else "audio/mpeg"
        return send_file(file_path, mimetype=mime, conditional=True)

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
        if not speaker:
            return jsonify({"error": "speaker is required"}), 400
        with config_lock:
            try:
                with open(config_path, "r") as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
            existing["speaker"] = speaker
            with open(config_path, "w") as f:
                json.dump(existing, f, indent=2)
        return jsonify({"ok": True, "speaker": speaker})

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
        return jsonify({"songs": songs})

    @app.route("/api/songs", methods=["POST"])
    def add_song():
        name = request.form.get("name", "").strip()
        image_url = request.form.get("image_url", "").strip()
        file = request.files.get("file")

        if not name:
            return jsonify({"error": "name is required"}), 400
        if not file or file.filename == "":
            return jsonify({"error": "file is required"}), 400

        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ("mp3", "m4a"):
            return jsonify({"error": "Only .mp3 and .m4a files are supported"}), 400

        song_id = secrets.token_hex(3)
        safe_name = secure_filename(file.filename)
        filename = f"{song_id}_{safe_name}"
        save_path = os.path.join(music_folder, filename)
        file.save(save_path)

        song = {
            "id": song_id,
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

        state.request_write(song_id)
        return jsonify({"id": song_id, "status": "pending"}), 202

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
            file_path = os.path.join(music_folder, removed.get("filename", ""))
            if os.path.isfile(file_path):
                os.remove(file_path)
            return jsonify({"ok": True})
        return jsonify({"error": "Song not found"}), 404

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
                file_path = os.path.join(music_folder, removed.get("filename", ""))
                if os.path.isfile(file_path):
                    os.remove(file_path)

        return jsonify({"ok": True})

    # ------------------------------------------------------------------
    # Retag existing song
    # ------------------------------------------------------------------

    @app.route("/api/songs/<song_id>/retag", methods=["POST"])
    def retag_song(song_id):
        song = lookup_song(song_id, songs_path, songs_lock)
        if not song:
            return jsonify({"error": "Song not found"}), 404
        state.request_write(song_id)
        return jsonify({"ok": True, "status": "pending"})

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
        if not song_id:
            return jsonify({"error": "id is required"}), 400

        song = lookup_song(song_id, songs_path, songs_lock)
        if not song:
            return jsonify({"error": "Song not found"}), 404

        try:
            cast_song(song, config_path, config_lock, pi_ip)
            return jsonify({"ok": True, "message": f"Now playing '{song['name']}'"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app

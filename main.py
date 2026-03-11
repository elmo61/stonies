import os
import socket
import threading

from nfc_daemon import NFCState, run_daemon
from api import create_app


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    music_folder = os.path.join(base_dir, "music")
    import_folder = os.path.join(base_dir, "music_import")
    images_folder = os.path.join(base_dir, "images")
    songs_path = os.path.join(base_dir, "songs.json")
    config_path = os.path.join(base_dir, "config.json")

    os.makedirs(music_folder, exist_ok=True)
    os.makedirs(import_folder, exist_ok=True)
    os.makedirs(images_folder, exist_ok=True)

    pi_ip = get_ip()
    print(f"[Main] Pi IP: {pi_ip}")

    state = NFCState()
    songs_lock = threading.Lock()
    config_lock = threading.Lock()

    daemon_thread = threading.Thread(
        target=run_daemon,
        args=(state, songs_path, songs_lock, config_path, config_lock, pi_ip),
        daemon=True,
    )
    daemon_thread.start()

    app = create_app(state, songs_lock, config_lock, music_folder, import_folder, images_folder, songs_path, config_path, pi_ip)
    print(f"[Main] Starting Flask on http://{pi_ip}:5000")
    app.run(host="0.0.0.0", port=5000, threaded=True)

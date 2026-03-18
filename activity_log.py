"""
Simple append-only activity log.
Writes one human-readable line per event to activity.log.
Thread-safe via a module-level lock.
"""
import threading
from datetime import datetime

_lock = threading.Lock()


def write_log(log_path, message):
    """Append a timestamped line to the activity log file."""
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {message}\n"
    with _lock:
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            print(f"[Log] Failed to write activity log: {e}")

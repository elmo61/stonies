"""
Simple append-only activity log.
Writes one human-readable line per event to activity.log.
Thread-safe via a module-level lock.

The log is capped: once it grows past _MAX_BYTES it is trimmed back to the
most recent _KEEP_LINES lines (checked periodically, not on every write).
Unbounded growth made /api/log — which reads the whole file — slower every
week the Pi stayed up.
"""
import os
import threading
from datetime import datetime

_lock = threading.Lock()
_write_count = 0

_MAX_BYTES = 1_000_000
_KEEP_LINES = 2000
_CHECK_EVERY = 100  # writes between size checks


def write_log(log_path, message):
    """Append a timestamped line to the activity log file."""
    global _write_count
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {message}\n"
    with _lock:
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line)
            _write_count += 1
            if _write_count % _CHECK_EVERY == 1:  # also fires on first write after boot
                _trim_if_needed(log_path)
        except Exception as e:
            print(f"[Log] Failed to write activity log: {e}")


def _trim_if_needed(log_path):
    """Trim the log to the last _KEEP_LINES lines once it exceeds _MAX_BYTES."""
    try:
        if os.path.getsize(log_path) <= _MAX_BYTES:
            return
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        tmp_path = log_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.writelines(lines[-_KEEP_LINES:])
        os.replace(tmp_path, log_path)
        print(f"[Log] Trimmed activity log to last {_KEEP_LINES} lines")
    except Exception as e:
        print(f"[Log] Failed to trim activity log: {e}")

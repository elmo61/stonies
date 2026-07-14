"""
Atomic JSON persistence for songs.json / config.json.

A plain open(path, "w") truncates the file before writing, so a power cut
mid-write leaves it corrupt. On this app that is catastrophic: a corrupt
songs.json used to be treated as an empty library and regenerated with new
song IDs, orphaning every written NFC tag. Writing to a temp file in the
same directory, fsyncing, then os.replace() means the file on disk is always
either the old or the new version — never half-written.
"""
import json
import os
import tempfile


def save_json(path, data):
    """Atomically write data as pretty-printed JSON to path."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise

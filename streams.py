"""Radio stations and podcasts: things that play from a web address instead of
a file on the box.

Radio  — the speaker plays the station's live stream directly.
Podcast — on each tap the box reads the podcast's feed, picks an episode
          (the newest, or the next one not yet finished) and the speaker
          plays it straight from the podcast's own site. Nothing is downloaded.

Only the standard library is used, so nothing new to install on the Pi.
"""
import http.client
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from io import BytesIO
from urllib.parse import quote, urljoin

from storage import save_json

USER_AGENT = "Stonies/1.0 (kids audio box)"
FEED_MAX_BYTES = 30 * 1024 * 1024        # big back-catalogues run to several MB
IMAGE_MAX_BYTES = 5 * 1024 * 1024
EPISODE_MODES = ("newest", "next")
RADIO_DIRECTORY = "https://all.api.radio-browser.info"

# Each podcast's episode list is kept here, so a tap doesn't wait for a
# feed that can be several MB. Refreshed in the background (refresh_loop) and
# whenever it's older than FEED_FRESH_FOR when a sticker is tapped.
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "podcast_cache")
FEED_FRESH_FOR = 30 * 60
REFRESH_EVERY = 3 * 60 * 60

ITUNES_NS = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
AUDIO_TYPES = {
    "mp3": "audio/mpeg", "m4a": "audio/mp4", "aac": "audio/aac",
    "ogg": "audio/ogg", "opus": "audio/ogg", "m3u8": "application/x-mpegurl",
}


class StreamError(Exception):
    """Something a parent can act on, worded for the app."""


def _unreachable(e):
    reason = str(getattr(e, "reason", e)).lower()
    return "it took too long to answer" if "timed out" in reason else "couldn't reach it"


def _open(url, timeout=15, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        raise StreamError(f"the site answered {e.code}") from e
    except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
        raise StreamError(_unreachable(e)) from e


def _read(url, max_bytes, timeout=15):
    with _open(url, timeout=timeout) as r:
        data = r.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise StreamError("it's too big")
    return data


def _web_url(url):
    url = (url or "").strip()
    if not re.match(r"^https?://", url, re.I):
        raise StreamError("that doesn't look like a web address (it should start with http)")
    return url


# ---------------------------------------------------------------------------
# Search (so nobody has to hunt for feed or stream addresses)
# ---------------------------------------------------------------------------

def search_podcasts(term, limit=12):
    """Apple's podcast directory, which lists almost every podcast."""
    url = ("https://itunes.apple.com/search?media=podcast&entity=podcast&country=GB"
           f"&limit={limit}&term={quote(term)}")
    data = json.loads(_read(url, 2 * 1024 * 1024))
    results = []
    for r in data.get("results", []):
        if not r.get("feedUrl"):
            continue
        results.append({
            "name": r.get("collectionName") or r.get("trackName") or "",
            "author": r.get("artistName") or "",
            "url": r["feedUrl"],
            "image": r.get("artworkUrl600") or r.get("artworkUrl100") or "",
            "thumb": r.get("artworkUrl100") or "",
            "episodes": r.get("trackCount"),
        })
    return results


def search_radio(term, limit=15):
    """radio-browser.info, a free community directory of internet radio."""
    url = (f"{RADIO_DIRECTORY}/json/stations/search?name={quote(term)}&limit={limit}"
           "&hidebroken=true&order=votes&reverse=true")
    data = json.loads(_read(url, 2 * 1024 * 1024))
    results, seen = [], set()
    for s in data:
        stream = s.get("url_resolved") or s.get("url")
        if not stream or stream in seen:
            continue
        seen.add(stream)
        detail = " · ".join(x for x in (
            s.get("countrycode") or "",
            f"{s['bitrate']} kbps" if s.get("bitrate") else "",
        ) if x)
        results.append({
            "name": (s.get("name") or "").strip(),
            "author": detail,
            "url": stream,
            "image": s.get("favicon") or "",
        })
    return results


# ---------------------------------------------------------------------------
# Radio
# ---------------------------------------------------------------------------

def _playlist_entry(text, base):
    """First stream address in a .pls or .m3u playlist."""
    pls = re.search(r"^\s*\[playlist\]", text, re.I | re.M)
    for line in text.splitlines():
        line = line.strip()
        if pls:
            m = re.match(r"^File\d+=(.+)$", line, re.I)
            if m:
                return urljoin(base, m.group(1).strip())
        elif line and not line.startswith("#"):
            return urljoin(base, line)
    return None


def check_radio(url, _depth=0):
    """Make sure a station address plays. Returns {"url", "content_type"}.

    Follows playlist files (.pls/.m3u) to the real stream. Only the response
    headers are read: a live stream never ends."""
    url = _web_url(url)
    with _open(url, timeout=10, headers={"Icy-MetaData": "0"}) as r:
        ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        final = r.geturl()
        is_playlist = (ctype in ("audio/x-scpls", "audio/x-mpegurl", "audio/mpegurl")
                       or re.search(r"\.(pls|m3u)(\?|$)", final, re.I))
        if is_playlist and ctype != "application/vnd.apple.mpegurl":
            if _depth > 2:
                raise StreamError("the playlist goes round in circles")
            entry = _playlist_entry(r.read(64 * 1024).decode("utf-8", "replace"), final)
            if not entry:
                raise StreamError("the playlist is empty")
            return check_radio(entry, _depth + 1)
    if ctype in ("application/vnd.apple.mpegurl", "application/x-mpegurl") or final.lower().split("?")[0].endswith(".m3u8"):
        return {"url": final, "content_type": "application/x-mpegurl"}
    if ctype.startswith("audio/") or ctype in ("application/ogg", "video/mp2t"):
        return {"url": final, "content_type": ctype}
    if ctype.startswith("text/html"):
        raise StreamError("that's a web page, not a radio stream")
    raise StreamError(f"that isn't an audio stream ({ctype or 'unknown type'})")


# ---------------------------------------------------------------------------
# Podcasts
# ---------------------------------------------------------------------------

def _text(el, tag):
    found = el.find(tag)
    return (found.text or "").strip() if found is not None and found.text else ""


def _duration(raw):
    """itunes:duration as seconds: "1234", "20:34" or "1:02:03"."""
    try:
        parts = [float(p) for p in (raw or "").split(":")]
    except ValueError:
        return None
    if not parts:
        return None
    secs = 0
    for p in parts:
        secs = secs * 60 + p
    return int(secs) or None


def _mime_for(url, given):
    given = (given or "").split(";")[0].strip().lower()
    if given.startswith("audio/"):
        return given
    ext = url.lower().split("?")[0].rsplit(".", 1)[-1]
    return AUDIO_TYPES.get(ext, "audio/mpeg")


def parse_feed(data):
    """Podcast RSS -> {"title", "image", "episodes"} with episodes oldest first.

    Uses iterparse and drops each episode once read, so a feed with a
    thousand episodes doesn't need much memory on a Pi Zero."""
    title = image = ""
    episodes = []
    order = 0
    try:
        for event, el in ET.iterparse(BytesIO(data), events=("end",)):
            tag = el.tag
            if tag == "item":
                enc = el.find("enclosure")
                url = enc.get("url", "").strip() if enc is not None else ""
                if url:
                    published = None
                    pub = _text(el, "pubDate")
                    if pub:
                        try:
                            published = parsedate_to_datetime(pub).timestamp()
                        except (TypeError, ValueError, IndexError):
                            published = None
                    episodes.append({
                        "guid": _text(el, "guid") or url,
                        "title": _text(el, "title") or "Episode",
                        "url": url,
                        "mime": _mime_for(url, enc.get("type")),
                        "published": published,
                        "duration": _duration(_text(el, f"{ITUNES_NS}duration")),
                        "_order": order,
                    })
                    order += 1
                el.clear()
            elif tag == "channel":
                title = _text(el, "title") or title
            elif tag == f"{ITUNES_NS}image" and not image:
                image = el.get("href", "") or image
            elif tag == "image" and not image:
                image = _text(el, "url") or image
    except ET.ParseError as e:
        raise StreamError("that isn't a podcast feed") from e
    if not episodes:
        raise StreamError("that feed has no episodes to play")
    # Oldest first. Feeds are usually newest first, so items without a date
    # fall back to the reverse of their order in the feed.
    episodes.sort(key=lambda e: (e["published"] if e["published"] is not None else float("-inf"), -e["_order"]))
    for e in episodes:
        del e["_order"]
    return {"title": title, "image": image, "episodes": episodes}


def fetch_feed(url):
    return parse_feed(_read(_web_url(url), FEED_MAX_BYTES, timeout=20))


def _cache_path(song_id):
    return os.path.join(CACHE_DIR, f"{song_id}.json")


def _load_cache(song):
    try:
        with open(_cache_path(song["id"]), "r", encoding="utf-8") as f:
            cache = json.load(f)
        return cache if cache.get("feed_url") == song.get("feed_url") and cache.get("episodes") else None
    except (OSError, ValueError):
        return None


def _save_cache(song_id, cache):
    os.makedirs(CACHE_DIR, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=CACHE_DIR, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    os.replace(tmp, _cache_path(song_id))


def remember_feed(song_id, feed_url, feed):
    """Start the cache with a feed just read (when a podcast is added)."""
    _save_cache(song_id, {"feed_url": feed_url, "fetched_at": time.time(), "etag": None,
                          "modified": None, "title": feed["title"], "image": feed["image"],
                          "episodes": feed["episodes"]})


def remove_cache(song_id):
    try:
        os.remove(_cache_path(song_id))
    except OSError:
        pass


def get_episodes(song, max_age=FEED_FRESH_FOR, log_fn=None):
    """The podcast's episodes, oldest first: from the cache when it's fresh,
    otherwise from the feed (asking the site for changes only). If the feed
    can't be reached, an older cached list is used rather than failing."""
    cache = _load_cache(song)
    if cache and time.time() - cache.get("fetched_at", 0) < max_age:
        return cache["episodes"]

    url = _web_url(song.get("feed_url", ""))
    headers = {"User-Agent": USER_AGENT}
    if cache and cache.get("etag"):
        headers["If-None-Match"] = cache["etag"]
    if cache and cache.get("modified"):
        headers["If-Modified-Since"] = cache["modified"]
    try:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
                data = r.read(FEED_MAX_BYTES + 1)
                etag, modified = r.headers.get("ETag"), r.headers.get("Last-Modified")
        except urllib.error.HTTPError as e:
            if e.code == 304 and cache:
                cache["fetched_at"] = time.time()
                _save_cache(song["id"], cache)
                return cache["episodes"]
            raise StreamError(f"the site answered {e.code}") from e
        except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
            raise StreamError(_unreachable(e)) from e
        if len(data) > FEED_MAX_BYTES:
            raise StreamError("it's too big")
        feed = parse_feed(data)
    except StreamError as e:
        if cache:
            if log_fn:
                log_fn(f"Couldn't check \"{song.get('name')}\" for new episodes ({e}), using the saved list")
            return cache["episodes"]
        raise
    _save_cache(song["id"], {
        "feed_url": song.get("feed_url"), "fetched_at": time.time(),
        "etag": etag, "modified": modified,
        "title": feed["title"], "image": feed["image"], "episodes": feed["episodes"],
    })
    return feed["episodes"]


def refresh_loop(songs_path, songs_lock, every=REFRESH_EVERY):
    """Background thread: keep every podcast's episode list fresh, so taps
    rarely wait for a download. Also updates each podcast's "latest" summary."""
    time.sleep(120)              # let the box finish starting first
    while True:
        try:
            with songs_lock:
                with open(songs_path, "r") as f:
                    podcasts = [s for s in json.load(f) if s.get("type") == "podcast"]
            for song in podcasts:
                try:
                    summary = episode_summary(get_episodes(song, max_age=every / 2))
                except StreamError as e:
                    print(f"[Podcasts] {song.get('name')}: {e}")
                    continue
                with songs_lock:
                    with open(songs_path, "r") as f:
                        songs = json.load(f)
                    for s in songs:
                        if s.get("id") == song["id"] and s.get("latest") != summary:
                            s["latest"] = summary
                            save_json(songs_path, songs)
                            break
        except Exception as e:
            print(f"[Podcasts] refresh failed: {e}")
        time.sleep(every)


def choose_episode(song, episodes):
    """Which episode a tap plays, and where in it to start. Returns (episode, seconds).

    newest: the latest episode (resuming it if it was stopped part-way).
    next:   carry on with the episode in progress; otherwise the one after the
            last finished episode, starting from the very first. When every
            episode has been heard, play the newest again.
    """
    progress = song.get("progress") or {}
    by_guid = {e["guid"]: i for i, e in enumerate(episodes)}

    if song.get("episode_mode") == "next":
        if progress.get("episode_guid") in by_guid:
            return episodes[by_guid[progress["episode_guid"]]], progress.get("current_time", 0)
        last = by_guid.get(song.get("last_finished_guid"))
        if last is None:
            return episodes[0], 0
        if last + 1 < len(episodes):
            return episodes[last + 1], 0
        return episodes[-1], 0

    newest = episodes[-1]
    if progress.get("episode_guid") == newest["guid"]:
        return newest, progress.get("current_time", 0)
    return newest, 0


def episode_summary(episodes):
    """Small facts the app shows without fetching the feed itself."""
    newest = episodes[-1]
    return {"count": len(episodes), "newest_title": newest["title"], "newest_published": newest["published"]}


# ---------------------------------------------------------------------------
# Covers
# ---------------------------------------------------------------------------

def download_image(url, folder, song_id):
    """Save a remote picture as images/<song_id>.<ext>. Returns the file name."""
    url = _web_url(url)
    with _open(url, timeout=20) as r:
        ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        data = r.read(IMAGE_MAX_BYTES + 1)
    if len(data) > IMAGE_MAX_BYTES:
        raise StreamError("the picture is too big")
    ext = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png",
           "image/gif": "gif", "image/webp": "webp"}.get(ctype)
    if not ext:
        guess = url.lower().split("?")[0].rsplit(".", 1)[-1]
        ext = {"jpeg": "jpg"}.get(guess, guess)
        if ext not in ("jpg", "png", "gif", "webp"):
            raise StreamError("that isn't a picture")
    name = f"{song_id}.{ext}"
    with open(os.path.join(folder, name), "wb") as f:
        f.write(data)
    return name

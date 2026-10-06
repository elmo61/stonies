#!/usr/bin/env python3
"""Bulk-add cover pictures to a Stonies box, matching image files to songs by name.

Run from any computer on the same Wi-Fi as the box (needs Pillow: pip install pillow):

    python tools/upload_covers.py --box http://192.168.1.102:5000 \\
        --images ~/covers/ladybird --images ~/covers/calm --dry-run

  --images   a folder of pictures; repeat it, earlier folders win when two have a match
  --dry-run  show what would be matched and uploaded, change nothing
  --replace  also replace covers that are already set (default: only songs without one)
  --size     longest side in pixels after shrinking (default 600)

File names are matched to song names ignoring case, punctuation, apostrophes and
a leading "The", and against either the whole title or the part after a series
separator ("Ladybird Audio Adventures - Amazing Vehicles" matches
Amazing_Vehicles.jpg). Near misses are listed so you can check them.
"""
import argparse
import difflib
import io
import json
import os
import re
import sys
import urllib.request
import uuid

from PIL import Image

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")
SEPARATOR = re.compile(r"\s[-–—]\s|:\s|\s{2,}")


def norm(text):
    text = text.lower().replace("'", "").replace("’", "")
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return re.sub(r"^the ", "", text)


def song_keys(name):
    """The whole title, plus the part after a series separator."""
    keys = [norm(name)]
    m = SEPARATOR.search(name)
    if m and m.start() >= 3:
        keys.append(norm(name[m.end():]))
    return [k for k in keys if k]


def find_images(folders):
    """{normalised name: path}, earlier folders winning ties."""
    found = {}
    for folder in folders:
        for f in sorted(os.listdir(folder)):
            stem, ext = os.path.splitext(f)
            if ext.lower() in IMAGE_EXTS and not stem.endswith("_log"):
                found.setdefault(norm(stem), os.path.join(folder, f))
    return found


def shrink(path, size):
    with Image.open(path) as im:
        im = im.convert("RGBA") if im.mode in ("P", "LA", "RGBA") else im.convert("RGB")
        if im.mode == "RGBA":                       # flatten transparency onto white
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        im.thumbnail((size, size), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, "JPEG", quality=85, optimize=True)
        return out.getvalue()


def get_json(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode())


def upload_image(box, song_id, data):
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"cover.jpg\"\r\n"
            f"Content-Type: image/jpeg\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{box}/api/songs/{song_id}/image", data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--box", required=True, help="e.g. http://192.168.1.102:5000")
    ap.add_argument("--images", action="append", required=True, help="folder of pictures (repeatable)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--size", type=int, default=600)
    args = ap.parse_args()
    box = args.box.rstrip("/")

    songs = get_json(f"{box}/api/songs")["songs"]
    images = find_images([os.path.expanduser(f) for f in args.images])
    print(f"{len(songs)} songs on {box}, {len(images)} pictures found\n")

    plan, close, missing, skipped = [], [], [], []
    for s in songs:
        if s.get("image_url") and not args.replace:
            skipped.append(s["name"])
            continue
        keys = song_keys(s["name"])
        path = next((images[k] for k in keys if k in images), None)
        if not path:
            near = difflib.get_close_matches(keys[-1], images.keys(), n=1, cutoff=0.85)
            if near:
                path = images[near[0]]
                close.append((s["name"], path))
        if path:
            plan.append((s, path))
        else:
            missing.append(s["name"])

    for s, path in plan:
        print(f"  {s['name'][:52]:52}  <-  {os.path.basename(path)}")
    if close:
        print("\nClose (not exact) matches, please check:")
        for name, path in close:
            print(f"  {name}  <-  {path}")
    if missing:
        print("\nNo picture found for:")
        for name in missing:
            print(f"  {name}")
    if skipped:
        print(f"\nAlready have a cover (left alone; use --replace to change): {len(skipped)}")
    print(f"\n{len(plan)} cover(s) to upload")
    if args.dry_run or not plan:
        return

    done = 0
    for s, path in plan:
        try:
            data = shrink(path, args.size)
            upload_image(box, s["id"], data)
            done += 1
            print(f"  ok  {s['name']}  ({len(data) // 1024} KB)")
        except Exception as e:
            print(f"  FAILED  {s['name']}: {e}", file=sys.stderr)
    print(f"\nUploaded {done} of {len(plan)}")


if __name__ == "__main__":
    main()

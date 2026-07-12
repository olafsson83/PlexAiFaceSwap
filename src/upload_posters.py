"""Stage 3: upload swapped posters and paired background artwork to Plex.

Matches files back to Plex items using the ratingKey embedded in the filename
by download_posters.py, so this only works on files that came from stage 1.
Each upload is followed by locking the poster field -- without that, Plex can
silently revert to agent-sourced artwork on the next metadata refresh.
"""
import sys

import requests
from tqdm import tqdm

from config import SWAPPED_DIR, ARTWORK_SWAPPED_DIR
from plex_client import (
    get_sections, upload_poster, upload_artwork, lock_poster, lock_artwork,
    rating_key_from_filename,
)
import preflight

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
PLEX_TYPE_CODES = {"movie": 1, "show": 2}


def main():
    preflight.require_ready(need_plex=True)

    if not SWAPPED_DIR.exists():
        sys.exit(f"Swapped posters folder not found: {SWAPPED_DIR}. Run the swap stage first.")

    sections = {s["title"]: s for s in get_sections()}
    image_sets = (
        ("poster", SWAPPED_DIR, upload_poster, lock_poster),
        ("artwork", ARTWORK_SWAPPED_DIR, upload_artwork, lock_artwork),
    )

    uploaded, locked, failed = 0, 0, 0
    files = [
        (kind, root, upload, lock, path)
        for kind, root, upload, lock in image_sets if root.exists()
        for path in root.rglob("*") if path.suffix.lower() in IMAGE_EXTS
    ]
    for kind, root, upload, lock, f in tqdm(files, desc="Uploading", unit="image"):
        rating_key = rating_key_from_filename(f)
        if not rating_key:
            tqdm.write(f"  skipped (no ratingKey in filename): {f.name}")
            failed += 1
            continue

        try:
            upload(rating_key, f)
            uploaded += 1
        except requests.HTTPError as e:
            tqdm.write(f"  upload failed: {f.name} ({e})")
            failed += 1
            continue

        library_name = f.relative_to(root).parts[0]
        section = sections.get(library_name)
        item_type = PLEX_TYPE_CODES.get(section.get("type")) if section else None
        if not section or not item_type:
            tqdm.write(f"  uploaded but NOT locked (unknown library/type): {f.name}")
            continue

        try:
            lock(rating_key, section["key"], item_type)
            locked += 1
        except requests.HTTPError as e:
            tqdm.write(f"  uploaded but lock failed: {f.name} ({e})")

    print(f"Done. Uploaded {uploaded} poster/artwork images ({locked} locked), failed {failed}.")


if __name__ == "__main__":
    main()

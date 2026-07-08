"""Stage 3 (optional): upload swapped posters back into Plex as each item's poster.

Matches files back to Plex items using the ratingKey embedded in the filename
by download_posters.py, so this only works on files that came from stage 1.
"""
import sys

import requests
from tqdm import tqdm

from config import SWAPPED_DIR
from plex_client import upload_poster, rating_key_from_filename
import preflight

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def main():
    preflight.require_ready(need_plex=True)

    if not SWAPPED_DIR.exists():
        sys.exit(f"Swapped posters folder not found: {SWAPPED_DIR}. Run the swap stage first.")

    files = [p for p in SWAPPED_DIR.rglob("*") if p.suffix.lower() in IMAGE_EXTS]

    uploaded, failed = 0, 0
    for f in tqdm(files, desc="Uploading", unit="poster"):
        rating_key = rating_key_from_filename(f)
        if not rating_key:
            tqdm.write(f"  skipped (no ratingKey in filename): {f.name}")
            failed += 1
            continue

        try:
            upload_poster(rating_key, f)
            uploaded += 1
        except requests.HTTPError as e:
            tqdm.write(f"  failed: {f.name} ({e})")
            failed += 1

    print(f"Done. Uploaded {uploaded}, failed {failed}.")


if __name__ == "__main__":
    main()

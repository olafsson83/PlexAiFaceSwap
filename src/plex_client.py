"""Small wrapper around the bits of the Plex HTTP API this pipeline needs."""
from pathlib import Path

import requests

from config import PLEX_URL, PLEX_TOKEN

_JSON_HEADERS = {"X-Plex-Token": PLEX_TOKEN, "Accept": "application/json"}


def get_sections():
    """Returns the server's library sections, e.g. [{"key": "1", "title": "Movies", ...}, ...]."""
    r = requests.get(f"{PLEX_URL}/library/sections", headers=_JSON_HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()["MediaContainer"].get("Directory", [])


def get_section_items(section_key):
    """Returns the top-level items (movies, or shows) in a library section."""
    r = requests.get(f"{PLEX_URL}/library/sections/{section_key}/all", headers=_JSON_HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()["MediaContainer"].get("Metadata", [])


def download_thumb(thumb_path: str, dest: Path):
    """Downloads a poster image referenced by an item's `thumb` path to dest."""
    r = requests.get(f"{PLEX_URL}{thumb_path}", headers={"X-Plex-Token": PLEX_TOKEN}, timeout=30)
    r.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)


def upload_poster(rating_key: str, image_path: Path):
    """Uploads a local image as the new poster for an item, selecting it immediately."""
    url = f"{PLEX_URL}/library/metadata/{rating_key}/posters"
    r = requests.post(url, headers={"X-Plex-Token": PLEX_TOKEN}, data=image_path.read_bytes(), timeout=60)
    r.raise_for_status()


def safe_filename(title: str, rating_key: str) -> str:
    """Builds a filesystem-safe filename that embeds the ratingKey for later lookup."""
    cleaned = "".join(c for c in title if c not in '<>:"/\\|?*').strip()
    return f"{cleaned} [{rating_key}].jpg"


def rating_key_from_filename(path: Path):
    """Reverses safe_filename() to recover the ratingKey embedded in a poster filename."""
    stem = path.stem
    if stem.endswith("]") and "[" in stem:
        return stem.rsplit("[", 1)[1][:-1]
    return None

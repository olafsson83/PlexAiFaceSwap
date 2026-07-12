import sys
import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"

try:
    load_dotenv(ENV_PATH)
except UnicodeDecodeError:
    sys.exit(
        f"{ENV_PATH} isn't valid UTF-8 text (often caused by hand-editing it in a "
        "text editor that saves as ANSI/Windows-1252 instead of UTF-8 - e.g. Notepad's "
        "default 'Save As' encoding). Re-run `python setup.py` to regenerate it cleanly, "
        "or re-save the file with UTF-8 encoding."
    )

PLEX_URL = os.environ.get("PLEX_URL", "http://127.0.0.1:32400").rstrip("/")
PLEX_TOKEN = os.environ.get("PLEX_TOKEN", "")

LIBRARY_NAMES = [
    name.strip()
    for name in os.environ.get("LIBRARY_NAMES", "Movies,TV Shows").split(",")
    if name.strip()
]

def _configured_faces():
    raw = os.environ.get("SOURCE_FACES") or os.environ.get("SOURCE_FACE", "my_face.jpg")
    paths = []
    for value in raw.split("|"):
        value = value.strip()
        if not value:
            continue
        path = Path(value)
        paths.append(path if path.is_absolute() else REPO_ROOT / path)
    return paths


SOURCE_FACES = _configured_faces()
# Kept for compatibility with older callers/configuration.
SOURCE_FACE = SOURCE_FACES[0] if SOURCE_FACES else REPO_ROOT / "my_face.jpg"
POSTERS_DIR = REPO_ROOT / os.environ.get("POSTERS_DIR", "posters_original")
SWAPPED_DIR = REPO_ROOT / os.environ.get("SWAPPED_DIR", "posters_swapped")
ARTWORK_DIR = REPO_ROOT / os.environ.get("ARTWORK_DIR", "artwork_original")
ARTWORK_SWAPPED_DIR = REPO_ROOT / os.environ.get("ARTWORK_SWAPPED_DIR", "artwork_swapped")

CTX_ID = int(os.environ.get("CTX_ID", "0"))

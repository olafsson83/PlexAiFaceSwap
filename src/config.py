import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

PLEX_URL = os.environ.get("PLEX_URL", "http://127.0.0.1:32400").rstrip("/")
PLEX_TOKEN = os.environ.get("PLEX_TOKEN", "")

LIBRARY_NAMES = [
    name.strip()
    for name in os.environ.get("LIBRARY_NAMES", "Movies,TV Shows").split(",")
    if name.strip()
]

SOURCE_FACE = REPO_ROOT / os.environ.get("SOURCE_FACE", "my_face.jpg")
POSTERS_DIR = REPO_ROOT / os.environ.get("POSTERS_DIR", "posters_original")
SWAPPED_DIR = REPO_ROOT / os.environ.get("SWAPPED_DIR", "posters_swapped")

CTX_ID = int(os.environ.get("CTX_ID", "0"))

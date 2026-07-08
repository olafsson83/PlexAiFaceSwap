"""Shared readiness checks so a missing setup step fails with a clear fix,
not a stack trace halfway through a batch job.
"""
from pathlib import Path

import requests

from config import PLEX_URL, PLEX_TOKEN, SOURCE_FACE, REPO_ROOT

MODEL_PATH = Path.home() / ".insightface" / "models" / "inswapper_128.onnx"


def _plex_reachable():
    if not PLEX_TOKEN:
        return False
    try:
        r = requests.get(f"{PLEX_URL}/identity", headers={"X-Plex-Token": PLEX_TOKEN}, timeout=5)
        return r.ok
    except requests.RequestException:
        return False


def diagnose():
    """Full readiness checklist, used by setup.py to show a status report."""
    return [
        ((REPO_ROOT / ".env").exists(), ".env file exists"),
        (bool(PLEX_TOKEN), "PLEX_TOKEN is set"),
        (_plex_reachable(), f"Plex reachable at {PLEX_URL}"),
        (SOURCE_FACE.exists(), f"Source face image found ({SOURCE_FACE.name})"),
        (MODEL_PATH.exists(), "Face-swap model downloaded"),
    ]


def print_report(checks=None):
    checks = checks if checks is not None else diagnose()
    for ok, label in checks:
        print(f"  [{'OK' if ok else 'MISSING'}] {label}")
    return all(ok for ok, _ in checks)


def require_ready(need_plex=False, need_face=False, need_model=False):
    """Exits with a friendly message (not a traceback) if a stage's needs aren't met."""
    problems = []

    if not (REPO_ROOT / ".env").exists():
        problems.append("No .env file found.")
    elif need_plex and not PLEX_TOKEN:
        problems.append("PLEX_TOKEN is not set in .env.")
    elif need_plex and not _plex_reachable():
        problems.append(f"Could not reach Plex at {PLEX_URL} — is the server running and the token correct?")

    if need_face and not SOURCE_FACE.exists():
        problems.append(f"Source face image not found: {SOURCE_FACE}")

    if need_model and not MODEL_PATH.exists():
        problems.append(f"Face-swap model not found: {MODEL_PATH}")

    if problems:
        print("Setup is incomplete:")
        for p in problems:
            print(f"  - {p}")
        raise SystemExit("\nRun `python setup.py` to fix this.")

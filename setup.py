"""One-time interactive setup wizard.

Walks you through connecting to Plex, picking libraries, checking your face
photo, installing the right onnxruntime for your hardware, and downloading
the face-swap model. Writes everything to .env. Safe to re-run any time.
"""
import subprocess
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent
ENV_PATH = REPO_ROOT / ".env"

# Same URL used by ComfyUI-ReActor's own installer to fetch this model.
MODEL_URL = "https://huggingface.co/datasets/Gourieff/ReActor/resolve/main/models/inswapper_128.onnx"
MODEL_DIR = Path.home() / ".insightface" / "models"
MODEL_PATH = MODEL_DIR / "inswapper_128.onnx"


def ask(prompt, default=None):
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default or ""


def ask_yes_no(prompt, default=False):
    suffix = "[Y/n]" if default else "[y/N]"
    value = input(f"{prompt} {suffix}: ").strip().lower()
    if not value:
        return default
    return value.startswith("y")


def step(n, title):
    print(f"\n--- Step {n}: {title} ---")


def fetch_sections(plex_url, plex_token):
    try:
        r = requests.get(
            f"{plex_url}/library/sections",
            headers={"X-Plex-Token": plex_token, "Accept": "application/json"},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["MediaContainer"].get("Directory", [])
    except requests.RequestException:
        return None


def connect_to_plex():
    print("In Plex: play anything -> the (...) menu -> Get Info -> View XML.")
    print("Read the server address from your browser's address bar, and the value")
    print("after 'X-Plex-Token=' from that same URL.\n")

    while True:
        plex_url = ask("Plex server URL", "http://127.0.0.1:32400").rstrip("/")
        plex_token = ask("Plex token")

        print("Testing connection...")
        sections = fetch_sections(plex_url, plex_token)
        if sections is not None:
            print(f"Connected. Found {len(sections)} libraries.")
            return plex_url, plex_token, sections

        print("Could not reach Plex with that URL/token.")
        if not ask_yes_no("Try again?", default=True):
            sys.exit("Setup cancelled.")


def choose_libraries(sections):
    for i, s in enumerate(sections, 1):
        print(f"  {i}) {s['title']} ({s.get('type', 'unknown')})")

    choice = ask("Which libraries do you want posters for? (comma-separated numbers, or 'all')", "all")
    if choice.lower() == "all":
        chosen = [s["title"] for s in sections]
    else:
        indices = [int(x.strip()) - 1 for x in choice.split(",") if x.strip().isdigit()]
        chosen = [sections[i]["title"] for i in indices if 0 <= i < len(sections)]

    if not chosen:
        print("Nothing selected, defaulting to all libraries.")
        chosen = [s["title"] for s in sections]

    print(f"Using: {', '.join(chosen)}")
    return chosen


def choose_face_photo():
    print("Needs to be front-facing, well-lit, at least 512x512, nothing covering your face.")
    default_path = REPO_ROOT / "my_face.jpg"

    while True:
        face_path = Path(ask("Path to your face photo", str(default_path)))
        if face_path.exists():
            return face_path
        print(f"Can't find that file: {face_path}")
        print("Place your photo there (or type a different path) then press Enter to check again.")
        input("Press Enter to continue...")


def write_env(plex_url, plex_token, libraries, face_path, ctx_id):
    lines = [
        f"PLEX_URL={plex_url}",
        f"PLEX_TOKEN={plex_token}",
        f"LIBRARY_NAMES={','.join(libraries)}",
        f"SOURCE_FACE={face_path}",
        "POSTERS_DIR=posters_original",
        "SWAPPED_DIR=posters_swapped",
        f"CTX_ID={ctx_id}",
        "",
    ]
    ENV_PATH.write_text("\n".join(lines), encoding="utf-8")


def pip_install(*args):
    subprocess.run([sys.executable, "-m", "pip", "install", *args], check=True)


def ensure_onnxruntime(has_gpu):
    """Installs exactly one onnxruntime variant, idempotently.

    insightface declares plain (CPU) onnxruntime as a dependency, so a base
    `pip install -r requirements.txt` always pulls it in. onnxruntime and
    onnxruntime-gpu ship overlapping files under the same "onnxruntime"
    package directory, so having both installed (even briefly, across
    separate uninstall/install calls) can leave the package broken -- e.g.
    "module 'onnxruntime' has no attribute 'InferenceSession'". That's
    especially likely on a second run of setup.py, since pip considers an
    already-installed package "satisfied" and silently skips reinstalling
    it, even if a step in between deleted files it needs. Uninstalling both
    variants and doing a --force-reinstall of the one we want avoids that
    regardless of what state a previous run left behind.
    """
    subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", "onnxruntime", "onnxruntime-gpu"],
        check=False,
    )
    package = "onnxruntime-gpu" if has_gpu else "onnxruntime"
    # --no-deps: onnxruntime(-gpu)'s own dependency resolution can pull numpy
    # past the <2 pin insightface/scikit-image need here. Re-pin numpy
    # explicitly afterward -- NOT by re-running the full requirements.txt,
    # which would reinstall plain onnxruntime on top (it doesn't recognize
    # onnxruntime-gpu as satisfying insightface's "onnxruntime" dependency)
    # and undo the swap we just made.
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-cache-dir", "--no-deps", package],
        check=True,
    )
    subprocess.run([sys.executable, "-m", "pip", "install", "numpy<2"], check=True)


def download_model():
    if MODEL_PATH.exists():
        print(f"  Already downloaded: {MODEL_PATH}")
        return

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = MODEL_PATH.with_suffix(".onnx.part")

    with requests.get(MODEL_URL, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done = 0
        with open(tmp_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    print(f"\r  {pct}% ({done // (1024 * 1024)}MB / {total // (1024 * 1024)}MB)", end="", flush=True)
        print()

    tmp_path.rename(MODEL_PATH)


def main():
    print("PlexAiFaceSwap setup wizard")
    print("You can re-run this any time to change settings.")

    step(1, "Connect to Plex")
    plex_url, plex_token, sections = connect_to_plex()

    step(2, "Choose libraries")
    libraries = choose_libraries(sections)

    step(3, "Your source face photo")
    face_path = choose_face_photo()

    step(4, "Hardware")
    has_gpu = ask_yes_no("Do you have an NVIDIA GPU you want to use (much faster)?", default=False)
    ctx_id = 0 if has_gpu else -1

    step(5, "Saving configuration")
    write_env(plex_url, plex_token, libraries, face_path, ctx_id)
    print(f"Wrote {ENV_PATH}")

    step(6, "Installing the right packages for your hardware")
    ensure_onnxruntime(has_gpu)

    step(7, "Downloading the face-swap model (about 250MB, one-time)")
    download_model()

    step(8, "Checking everything is ready")
    sys.path.insert(0, str(REPO_ROOT / "src"))
    import preflight  # imported now so it picks up the .env we just wrote

    ok = preflight.print_report()
    if ok:
        print("\nAll set! Run `python run.py` to start (or double-click run.bat on Windows).")
    else:
        print("\nSome checks above are still failing - fix those and re-run `python setup.py`.")


if __name__ == "__main__":
    main()

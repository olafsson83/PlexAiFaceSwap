"""Main entry point. Run with no arguments for an interactive menu, or pass
flags for non-interactive/scheduled use (cron, Task Scheduler, etc.).
"""
import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SRC = REPO_ROOT / "src"


def run_stage(script):
    print(f"\n=== {script} ===")
    result = subprocess.run([sys.executable, str(SRC / script)])
    if result.returncode != 0:
        print(f"\n{script} failed (exit code {result.returncode}).")
        return False
    return True


def full_pipeline(upload=False):
    if not run_stage("download_posters.py"):
        return
    if not run_stage("swap_faces.py"):
        return
    if upload and not run_stage("upload_posters.py"):
        return
    print("\nPipeline complete.")


def menu():
    actions = {
        "1": ("Download posters from Plex", lambda: run_stage("download_posters.py")),
        "2": ("Swap faces (batch)", lambda: run_stage("swap_faces.py")),
        "3": ("Upload swapped posters back to Plex", lambda: run_stage("upload_posters.py")),
        "4": ("Run full pipeline (download + swap)", lambda: full_pipeline(upload=False)),
        "5": ("Run full pipeline + upload to Plex", lambda: full_pipeline(upload=True)),
    }
    while True:
        print("\nPlexAiFaceSwap")
        for key, (label, _) in actions.items():
            print(f"  {key}) {label}")
        print("  0) Exit")

        choice = input("Choose an option: ").strip()
        if choice == "0":
            return
        action = actions.get(choice)
        if not action:
            print("Not a valid option, try again.")
            continue
        action[1]()


def main():
    parser = argparse.ArgumentParser(description="Plex poster face-swap pipeline")
    parser.add_argument("--all", action="store_true", help="Run download + swap non-interactively")
    parser.add_argument("--upload", action="store_true", help="Also (or only) upload swapped posters back to Plex")
    parser.add_argument("--download-only", action="store_true", help="Run only the download stage")
    parser.add_argument("--swap-only", action="store_true", help="Run only the swap stage")
    args = parser.parse_args()

    if args.download_only:
        run_stage("download_posters.py")
    elif args.swap_only:
        run_stage("swap_faces.py")
    elif args.all:
        full_pipeline(upload=args.upload)
    elif args.upload:
        run_stage("upload_posters.py")
    else:
        menu()


if __name__ == "__main__":
    main()

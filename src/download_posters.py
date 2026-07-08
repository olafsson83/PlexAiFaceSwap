"""Stage 1: download current posters for every configured library from Plex.

Incremental: a manifest.json per library records each item's thumb path, so
re-runs only fetch items that are new or whose poster actually changed.
"""
import json

from tqdm import tqdm

from config import LIBRARY_NAMES, POSTERS_DIR
from plex_client import get_sections, get_section_items, download_thumb, safe_filename
import preflight


def load_manifest(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_manifest(path, manifest):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2))


def main():
    preflight.require_ready(need_plex=True)

    sections = {s["title"]: s for s in get_sections()}
    missing = [name for name in LIBRARY_NAMES if name not in sections]
    if missing:
        print(f"Warning: these libraries were not found on the server: {', '.join(missing)}")

    total_new, total_updated, total_skipped = 0, 0, 0

    for name in LIBRARY_NAMES:
        section = sections.get(name)
        if not section:
            continue

        out_dir = POSTERS_DIR / name
        manifest_path = out_dir / "manifest.json"
        manifest = load_manifest(manifest_path)

        items = get_section_items(section["key"])

        for item in tqdm(items, desc=name, unit="poster"):
            thumb = item.get("thumb")
            if not thumb:
                continue

            rating_key = str(item["ratingKey"])
            filename = safe_filename(item["title"], rating_key)
            dest = out_dir / filename

            previous = manifest.get(rating_key)
            if previous == thumb and dest.exists():
                total_skipped += 1
                continue

            download_thumb(thumb, dest)
            manifest[rating_key] = thumb
            if previous is None:
                total_new += 1
                tqdm.write(f"  new: {filename}")
            else:
                total_updated += 1
                tqdm.write(f"  updated: {filename}")

        save_manifest(manifest_path, manifest)

    print(f"Done. {total_new} new, {total_updated} updated, {total_skipped} unchanged (skipped).")


if __name__ == "__main__":
    main()

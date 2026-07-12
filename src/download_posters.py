"""Stage 1: download current posters and background artwork from Plex.

Incremental: a manifest.json per library records each item's poster and art paths, so
re-runs only fetch items that are new or whose selected images actually changed.
"""
import json

from tqdm import tqdm

from config import LIBRARY_NAMES, POSTERS_DIR, ARTWORK_DIR
from plex_client import get_sections, get_section_items, download_image, safe_filename
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

    counts = {"new": 0, "updated": 0, "skipped": 0, "missing": 0}

    for name in LIBRARY_NAMES:
        section = sections.get(name)
        if not section:
            continue

        out_dir = POSTERS_DIR / name
        art_dir = ARTWORK_DIR / name
        manifest_path = out_dir / "manifest.json"
        manifest = load_manifest(manifest_path)

        items = get_section_items(section["key"])

        for item in tqdm(items, desc=name, unit="item"):
            rating_key = str(item["ratingKey"])
            filename = safe_filename(item["title"], rating_key)
            previous = manifest.get(rating_key, {})
            # Migrate manifests created by the poster-only version.
            if isinstance(previous, str):
                previous = {"thumb": previous}

            current = {"thumb": item.get("thumb"), "art": item.get("art")}
            for kind, dest_dir in (("thumb", out_dir), ("art", art_dir)):
                plex_path = current[kind]
                if not plex_path:
                    counts["missing"] += 1
                    continue
                dest = dest_dir / filename
                if previous.get(kind) == plex_path and dest.exists():
                    counts["skipped"] += 1
                    continue
                download_image(plex_path, dest)
                status = "new" if not previous.get(kind) else "updated"
                counts[status] += 1
                tqdm.write(f"  {status} {kind}: {filename}")

            manifest[rating_key] = current

        save_manifest(manifest_path, manifest)

    print(
        f"Done. {counts['new']} new, {counts['updated']} updated, "
        f"{counts['skipped']} unchanged, {counts['missing']} unavailable images."
    )


if __name__ == "__main__":
    main()

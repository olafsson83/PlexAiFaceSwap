"""Stage 2: swap evenly assigned source faces into posters and artwork.

Uses insightface directly (the same buffalo_l detector + inswapper_128.onnx
model that both Roop and ReActor wrap) so the whole step is one headless
script with no GUI or node graph involved.
"""
import json
import sys

import cv2
import insightface
import onnxruntime
from insightface.app import FaceAnalysis
from tqdm import tqdm

from config import (
    POSTERS_DIR, SWAPPED_DIR, ARTWORK_DIR, ARTWORK_SWAPPED_DIR,
    SOURCE_FACES, CTX_ID,
)
import preflight

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MANIFEST_NAME = "manifest.json"  # written by download_posters.py; not an image, skip it


def build_models():
    print("Loading face detection + swap models (first run also fetches the ~350MB detector pack)...")
    # The GPU build's CUDA/cuDNN runtime DLLs live inside their own pip
    # packages (nvidia-cublas-cu12 etc.), not on the normal Windows DLL
    # search path -- without this, onnxruntime silently falls back to CPU
    # even though CUDAExecutionProvider is "available". Safe to call
    # unconditionally: it's a no-op on the CPU-only onnxruntime package.
    onnxruntime.preload_dlls()
    face_app = FaceAnalysis(name="buffalo_l")
    face_app.prepare(ctx_id=CTX_ID, det_size=(640, 640))
    # get_model() only joins a name with the model root if it does NOT end in
    # ".onnx" -- pass a name ending in .onnx and it's used as a literal path
    # instead (relative to the current working directory), which silently
    # fails unless you happen to run from inside ~/.insightface/models/.
    # Passing the fully resolved path sidesteps that entirely.
    swapper = insightface.model_zoo.get_model(str(preflight.MODEL_PATH), download=False, download_zip=False)
    return face_app, swapper


def get_source_face(face_app, source_path):
    img = cv2.imread(str(source_path))
    if img is None:
        sys.exit(f"Could not read source face image: {source_path}")
    faces = face_app.get(img)
    if not faces:
        sys.exit(f"No face detected in source image: {source_path}")
    return faces[0]


def rating_key(path):
    stem = path.stem
    return stem.rsplit("[", 1)[1][:-1] if stem.endswith("]") and "[" in stem else None


def build_assignments(files, face_count):
    """Assign each Plex item to one face, with group sizes differing by at most one."""
    keys = sorted({key for path in files if (key := rating_key(path))}, key=lambda x: (len(x), x))
    return {key: index % face_count for index, key in enumerate(keys)}


def swap_one(face_app, swapper, source_face, src, dest):
    img = cv2.imread(str(src))
    if img is None:
        return "unreadable"

    faces = face_app.get(img)
    if not faces:
        return "no_face"

    result = img.copy()
    for face in faces:
        result = swapper.get(result, face, source_face, paste_back=True)

    dest.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dest), result)
    return "swapped"


def main():
    preflight.require_ready(need_face=True, need_model=True)

    if not POSTERS_DIR.exists():
        sys.exit(f"Posters folder not found: {POSTERS_DIR}. Run the download stage first.")

    face_app, swapper = build_models()
    source_faces = [get_source_face(face_app, path) for path in SOURCE_FACES]

    image_sets = (
        ("poster", POSTERS_DIR, SWAPPED_DIR),
        ("artwork", ARTWORK_DIR, ARTWORK_SWAPPED_DIR),
    )
    all_files = [
        p for _, source_dir, _ in image_sets if source_dir.exists()
        for p in source_dir.rglob("*") if p.suffix.lower() in IMAGE_EXTS
    ]
    assignments = build_assignments(all_files, len(source_faces))
    assignment_path = SWAPPED_DIR / "face_assignments.json"
    old_assignments = {}
    face_signatures = [f"{path.resolve()}|{path.stat().st_mtime_ns}|{path.stat().st_size}" for path in SOURCE_FACES]
    if assignment_path.exists():
        try:
            old_data = json.loads(assignment_path.read_text(encoding="utf-8"))
            if old_data.get("face_signatures") == face_signatures:
                old_assignments = old_data.get("assignments", {})
        except (json.JSONDecodeError, OSError):
            pass

    counts = {"swapped": 0, "skipped": 0, "no_face": 0, "unreadable": 0}
    for kind, source_dir, output_dir in image_sets:
        if not source_dir.exists():
            continue
        files = [p for p in source_dir.rglob("*") if p.suffix.lower() in IMAGE_EXTS]
        for src in tqdm(files, desc=f"Swapping {kind}", unit="image"):
            rel = src.relative_to(source_dir)
            dest = output_dir / rel
            key = rating_key(src)
            if key is None:
                tqdm.write(f"  skipped (no ratingKey): {rel}")
                continue
            face_index = assignments[key]

            if (
                dest.exists()
                and old_assignments.get(key) == face_index
                and dest.stat().st_mtime_ns >= src.stat().st_mtime_ns
            ):
                counts["skipped"] += 1
                continue

            result = swap_one(face_app, swapper, source_faces[face_index], src, dest)
            counts[result] = counts.get(result, 0) + 1
            if result != "swapped":
                tqdm.write(f"  {result}: {kind}/{rel}")

    assignment_path.parent.mkdir(parents=True, exist_ok=True)
    assignment_path.write_text(json.dumps({
        "faces": [str(path) for path in SOURCE_FACES],
        "face_signatures": face_signatures,
        "assignments": assignments,
    }, indent=2), encoding="utf-8")

    print(
        f"Done with {len(source_faces)} selected face(s). Swapped {counts['swapped']}, "
        f"skipped {counts['skipped']} (already done), "
        f"{counts['no_face']} had no detectable face, {counts['unreadable']} unreadable."
    )


if __name__ == "__main__":
    main()

"""Stage 2: batch face-swap every downloaded poster onto SOURCE_FACE.

Uses insightface directly (the same buffalo_l detector + inswapper_128.onnx
model that both Roop and ReActor wrap) so the whole step is one headless
script with no GUI or node graph involved.
"""
import sys

import cv2
import insightface
from insightface.app import FaceAnalysis
from tqdm import tqdm

from config import POSTERS_DIR, SWAPPED_DIR, SOURCE_FACE, CTX_ID
import preflight
import gpu_runtime

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MANIFEST_NAME = "manifest.json"  # written by download_posters.py; not an image, skip it

GPU_REQUESTED = CTX_ID >= 0


def build_models():
    print("Loading face detection + swap models (first run also fetches the ~350MB detector pack)...")
    # The GPU build's CUDA/cuDNN runtime DLLs live inside their own pip
    # packages (nvidia-cublas-cu12 etc.), not on the normal Windows DLL
    # search path -- without this, onnxruntime silently falls back to CPU
    # even though CUDAExecutionProvider is "available". Safe to call
    # unconditionally: it's a no-op on the CPU-only onnxruntime package.
    gpu_runtime.configure_cuda_runtime(GPU_REQUESTED)
    providers = gpu_runtime.requested_providers(GPU_REQUESTED)
    face_app = FaceAnalysis(name="buffalo_l", providers=providers)
    face_app.prepare(ctx_id=CTX_ID, det_size=(640, 640))
    for task_name, model in face_app.models.items():
        session = getattr(model, "session", None)
        if session is not None:
            gpu_runtime.enforce_session_provider(session, GPU_REQUESTED, f"InsightFace {task_name} model")
    # get_model() only joins a name with the model root if it does NOT end in
    # ".onnx" -- pass a name ending in .onnx and it's used as a literal path
    # instead (relative to the current working directory), which silently
    # fails unless you happen to run from inside ~/.insightface/models/.
    # Passing the fully resolved path sidesteps that entirely.
    swapper = insightface.model_zoo.get_model(
        str(preflight.MODEL_PATH), download=False, download_zip=False, providers=providers
    )
    gpu_runtime.enforce_session_provider(swapper.session, GPU_REQUESTED, "INSwapper model")
    return face_app, swapper


def get_source_face(face_app):
    img = cv2.imread(str(SOURCE_FACE))
    if img is None:
        sys.exit(f"Could not read source face image: {SOURCE_FACE}")
    faces = face_app.get(img)
    if not faces:
        sys.exit(f"No face detected in source image: {SOURCE_FACE}")
    return faces[0]


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
    source_face = get_source_face(face_app)

    poster_files = [
        p for p in POSTERS_DIR.rglob("*")
        if p.suffix.lower() in IMAGE_EXTS and p.name != MANIFEST_NAME
    ]

    counts = {"swapped": 0, "skipped": 0, "no_face": 0, "unreadable": 0}
    for src in tqdm(poster_files, desc="Swapping", unit="poster"):
        rel = src.relative_to(POSTERS_DIR)
        dest = SWAPPED_DIR / rel

        if dest.exists():
            counts["skipped"] += 1
            continue

        result = swap_one(face_app, swapper, source_face, src, dest)
        counts[result] = counts.get(result, 0) + 1
        if result != "swapped":
            tqdm.write(f"  {result}: {rel}")

    print(
        f"Done. Swapped {counts['swapped']}, skipped {counts['skipped']} (already done), "
        f"{counts['no_face']} had no detectable face, {counts['unreadable']} unreadable."
    )


if __name__ == "__main__":
    main()

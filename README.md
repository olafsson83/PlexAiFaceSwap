# PlexAiFaceSwap

Swap faces in movie/TV posters. Three stages, run in order:

1. **Download** — pulls current posters for your chosen Plex libraries down to local
   files. Incremental: re-runs only fetch items that are new or whose poster changed.
2. **Swap** — batch-swaps your face onto every downloaded poster, using
   [insightface](https://github.com/deepinsight/insightface) directly (the same
   detector + model that both Roop and ReActor wrap). No GUI, no ComfyUI node graph.
3. **Upload** *(optional)* — pushes the swapped images back into Plex as the selected
   poster for each item, then locks the poster field so a later "Refresh Metadata" can't
   silently revert it back to the original artwork.

> Personal, non-commercial use only. Keep this on your own server for your own laughs —
> don't redistribute posters with a swapped face, and don't run this on anyone's likeness
> without their consent.

## Requirements

**Python 3.11** specifically. `insightface`'s dependencies (`onnx`, `onnxruntime`) only
ship prebuilt wheels for a handful of Python versions — on anything newer (3.13, 3.14...)
`pip install` will try to compile `onnx` from source and fail with a `Failed to build
wheel for onnx` error unless you have a full C++ build toolchain installed. Using 3.11
avoids that entirely.

## Quick start

**Windows:** double-click `setup.bat`, then `run.bat`.

`setup.bat` creates a `.venv` folder using **Python 3.11** specifically (via the `py`
launcher), so it works correctly even if your system's default `python` is a different,
incompatible version. If Python 3.11 isn't installed, it'll tell you to grab it from
[python.org](https://www.python.org/downloads/release/python-3119/) or run
`winget install --id Python.Python.3.11`, then re-run `setup.bat`.

**Any OS (terminal):**

```bash
py -3.11 -m venv .venv          # Windows; use `python3.11 -m venv .venv` on macOS/Linux
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
python setup.py
python run.py
```

`setup.py` is an interactive wizard that:

- walks you through getting your `PLEX_URL` and `PLEX_TOKEN` (no manual XML-hunting —
  it tests the connection for you and tells you right away if something's wrong),
- fetches your actual library list from Plex and lets you pick from a numbered menu
  instead of typing exact names,
- checks your source face photo exists,
- asks if you have an NVIDIA GPU and installs `onnxruntime-gpu` with its CUDA/cuDNN
  runtime libraries (as pip packages -- no separate CUDA Toolkit install or NVIDIA
  developer account needed), otherwise the plain CPU `onnxruntime`,
- **downloads the face-swap model automatically** (previously a manual step — finding
  and placing `inswapper_128.onnx` by hand is the single most confusing part of setting
  this kind of tool up),
- writes all of that to `.env`,
- and finishes with a checklist confirming everything is ready.

It's safe to re-run any time you want to change libraries, swap your source photo, etc.

`run.py` (or `run.bat`) then gives you a menu:

```
1) Download posters from Plex
2) Swap faces (batch)
3) Upload swapped posters back to Plex
4) Run full pipeline (download + swap)
5) Run full pipeline + upload to Plex
0) Exit
```

For scheduled/unattended runs (cron, Task Scheduler), skip the menu with flags:

```bash
python run.py --all              # download + swap
python run.py --all --upload     # download + swap + upload
python run.py --download-only
python run.py --swap-only
python run.py --upload           # upload stage only
```

Every stage also runs its own readiness check first and tells you exactly what's missing
("PLEX_TOKEN is not set", "face-swap model not found", etc.) with a pointer back to
`python setup.py`, instead of failing with a raw stack trace.

## Your source face photo

Front-facing, evenly lit, at least 512×512, nothing covering your face (no sunglasses,
shadows, hands). A phone selfie in good daylight works fine. `setup.py` will ask where
it is and re-prompt if it can't find the file.

## Where things land

- `posters_original/<library>/` — downloaded originals
- `posters_swapped/<library>/` — swapped copies

Filenames encode each item's Plex `ratingKey` (e.g. `The Matrix [12345].jpg`) — the
upload stage uses that to know which Plex item each file belongs to, so don't rename
files between stages.

## Notes & troubleshooting

- **First run is slow** — downloading a large library and running inference over
  hundreds/thousands of posters can take hours. Later runs are much faster: the download
  stage only re-fetches changed posters, and the swap stage skips anything already
  present in `posters_swapped/`.
- **Poster changed in Plex after you already swapped it?** Delete the corresponding file
  from `posters_swapped/<library>/` so the swap stage reprocesses it — it won't overwrite
  existing output on its own.
- **Animal / cartoon posters**: the detector is trained almost entirely on human faces.
  It skips images where it can't find a face rather than erroring, but expect some misses
  on non-human or heavily stylized art — worth trying, not guaranteed.
- **"no face detected" on a poster that clearly has one**: usually low resolution, an
  extreme angle, or heavy stylization. It gets skipped and left out of
  `posters_swapped/` — the swap stage's final summary tells you how many were skipped
  for that reason so you know how many to expect.
- **Re-running `setup.py`** is always safe — it overwrites `.env` with whatever you enter
  and skips re-downloading the model if it's already there.
- **Said yes to GPU but the swap stage logs `Applied providers: ['CPUExecutionProvider']`
  instead of `CUDAExecutionProvider`?** Re-run `setup.py` — an earlier version of this
  wizard installed `onnxruntime-gpu` without its actual CUDA/cuDNN runtime libraries,
  which made it silently fall back to CPU (still worked, just much slower). The current
  version installs those libraries and loads them correctly; re-running picks up the fix.
- **Want the original poster back for something?** The upload stage locks each poster it
  sets (`thumb.locked=1`) so Plex won't silently revert it. To undo that for an item: in
  Plex, open its poster picker and choose a different poster (including one of the
  original agent-sourced ones still listed there) — selecting any poster through the UI
  re-locks it to your new choice, which is exactly what you want.

## Manual setup (skipping the wizard)

If you'd rather configure things by hand: copy `.env.example` to `.env` and fill it in,
then download `inswapper_128.onnx` yourself (see
[insightface's in_swapper example](https://github.com/deepinsight/insightface/blob/master/examples/in_swapper/README.md)
or [ReActor's README](https://github.com/Gourieff/ComfyUI-ReActor) for the current link)
to `~/.insightface/models/inswapper_128.onnx`, and install `onnxruntime` or
`onnxruntime-gpu` yourself.

## Alternatives considered

This repo calls `insightface` directly rather than going through ComfyUI, for a
fully-scriptable, GUI-free batch process. If you'd rather have a visual node-graph
workflow instead:

- **[ComfyUI-ReActor](https://github.com/Gourieff/ComfyUI-ReActor)** — actively
  maintained, the community's default ComfyUI face-swap node today; pair it with
  ComfyUI's folder-batch image loader for the same folder-in/folder-out behavior.
- **[ComfyUI-Roop](https://github.com/glitchinthemetrix16/ComfyUI-Roop)** — has a
  dedicated `RoopBatchFaceSwap` node (source image + folder in, folder out), but wraps
  the no-longer-actively-maintained `roop` project and needs it cloned separately.
- **[roop-unleashed](https://github.com/C0untFloyd/roop-unleashed)** — standalone GUI app
  with folder batch mode built in, no ComfyUI required.

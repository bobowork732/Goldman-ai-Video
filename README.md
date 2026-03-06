# Goldman AI Video

Open-source-first starter kit to build your own AI video generator (similar product shape to Wan/PixVerse/Kling/Pika):

- Text-to-video and image-to-video entry points
- Safety moderation gate before generation
- Output watermarking for attribution
- Optional audio track muxing (music, voice-over, SFX)
- GPU runtime profile support (`auto` / `cuda` / `cpu`) with low-VRAM mode
- Resolution presets (`1080p`, `4k`) + 24fps duration presets (5s/10s/15s/20s/25s)
- Python codebase that can be wired to open source models

## Model strategy (open-source)

This starter exposes a model catalog in `goldman_video.config.OPEN_SOURCE_MODELS`:

- `THUDM/CogVideoX-5b` for text-to-video
- `stabilityai/stable-video-diffusion-img2vid-xt` for image-to-video

The repository currently ships with a lightweight mock generator so you can build product plumbing first:

- `text2video` mock mode uses a **noise-to-clean** temporal smoothing flow with default **200 samples** (`num_inference_steps=200`)
- `image2video` mock mode uses your source image and creates a deterministic pan/zoom animation (no random noise grain)

Then replace `_mock_generate` in `src/goldman_video/pipeline.py` with real Diffusers inference.

## Install

```bash
pip install -e .
```

Optional generation stack:

```bash
pip install -e .[gen]
```

## CLI usage

```bash
goldman-video models
goldman-video text2video "a friendly 3D mascot introducing Goldman AI" --output outputs/intro.mp4 --fps 24 --duration 5 --resolution 1080p --gpu cuda
goldman-video text2video "mascot cinematic reveal" --output outputs/intro_audio.mp4 --audio assets/voiceover.mp3 --audio-start 0.5 --audio-volume 0.9
goldman-video text2video "mascot detail pass" --output outputs/intro_vae.mp4 --vae stabilityai/sd-vae-ft-mse --vae-tiling --vae-slicing
goldman-video image2video "camera orbit around the mascot" --image assets/mascot.png --output outputs/orbit.mp4 --audio assets/music.wav --audio-loop --animation-style pan_zoom --animation-intensity 1.0
goldman-video multishot shots/demo_shots.json --output outputs/story.mp4 --audio assets/score.mp3 --audio-loop
goldman-video-tk
```





## Output presets (v1.0)

This repo now supports a practical output profile surface for local prototyping:

- Frame rate: default `24fps`
- Duration presets: `5`, `10`, `15`, `20`, `25` seconds (via `--duration`)
- Resolution presets: `1080p` and `4k` (via `--resolution`)
- GPU runtime: `--gpu auto|cuda|cpu` ("Cuba" requests map to `cuda`)
- Low-VRAM mode: `--low-vram` (uses memory-conscious mock write path and runtime hinting)
- Precision hint: `--precision fp32|fp16|bf16`

When `--duration` is set, frame count is derived as `duration * fps` so output length stays consistent.

## Desktop Tk app

A minimal Tkinter GUI wrapper is available in `app/tk_app.py` and can be launched with:

```bash
python -m app.tk_app
# or
goldman-video-tk
```

The app includes mode selection (`text2video`, `image2video`, `multishot`), file pickers (image/audio/spec/output), a **Load Spec Preview** action (shot count + key fields), concise shot-validation errors in the status/log area, and background-thread generation so the UI stays responsive.

## Multi-shot support

Use the `multishot` command with a JSON/YAML spec to render multiple shots and stitch them into one final video.

Example shot spec (`shots/demo_shots.json`):

```json
{
  "prompt": "brand story edit",
  "shots": [
    {
      "prompt": "wide drone flyover city at dawn",
      "num_frames": 24,
      "fps": 8,
      "transition": "cut"
    },
    {
      "prompt": "close-up hero character",
      "image_path": "assets/hero.png",
      "num_frames": 24,
      "fps": 8,
      "transition": "crossfade",
      "transition_frames": 4,
      "camera": "slow push in",
      "style": "cinematic"
    }
  ]
}
```

Notes:
- If `shots` is present, pipeline runs in multi-shot mode; single-shot fields remain backward compatible.
- Supported transitions today: `cut`, `crossfade`.
- Crossfade reduces final duration by `transition_frames` at each crossfade boundary.
- Each shot is resampled to the timeline FPS (`GenerationRequest.fps`) so per-shot duration remains correct even when shots use different FPS values.

## Audio support

When `--audio` is provided, the pipeline muxes audio into the generated MP4 after watermarking.

- Requires `ffmpeg` available in your system `PATH`
- Supports common formats accepted by ffmpeg (`.mp3`, `.wav`, `.m4a`, etc.)
- Audio is trimmed to video duration (`num_frames / fps`)
- `fps` and `num_frames` must be greater than 0
- `audio-start` and `audio-volume` must be greater than or equal to 0
- Use `--audio-loop` to loop shorter audio across full video duration

## Safety

`src/goldman_video/safety.py` contains a blocklist moderation gate. Expand this with:

- LLM classifier policy checks
- image/video moderation model checks
- account-level abuse throttling and audit logging

## Watermark

`src/goldman_video/watermark.py` overlays text on each frame and writes the final video.

## Delivery roadmap (phased)

### Phase A — Backend scaffolding, runtime policy mapping, contract tests

**Scope**
- Complete backend abstraction and selection flow (mock vs diffusers) and keep mock as default for CI/local without heavy dependencies.
- Stabilize runtime policy resolution (`device`, `precision`, low-VRAM strategy) and preflight model validation.
- Expand contract-style tests for backend routing and shared post-processing behavior without requiring real model downloads.

**Exit criteria**
- CI passes with no real model dependency required.
- Backend toggle behavior is deterministic and tested (`mock` default, diffusers only when enabled).
- Runtime policy and model/vae compatibility validations are covered by unit tests.

**Primary modules/files**
- `src/goldman_video/pipeline.py`
- `src/goldman_video/models.py`
- `src/goldman_video/config.py`
- `tests/test_pipeline.py`, `tests/test_cli.py`

### Phase B — Optional local real-model smoke script (manual, non-CI)

**Scope**
- Provide a developer-only smoke script to run one short text2video and image2video pass against local diffusers setup.
- Keep script out of CI and document required env/resources (GPU, VRAM, model cache, ffmpeg).

**Exit criteria**
- Manual run instructions are documented and reproducible on a configured machine.
- Smoke script verifies end-to-end generation, watermarking, and optional mux integration for at least one happy path.

**Primary modules/files**
- `scripts/` (new smoke runner, if added)
- `README.md` (manual smoke instructions)
- `src/goldman_video/cli.py`, `src/goldman_video/pipeline.py`

### Phase C — Quality controls (reproducibility, safety parity, timeline correctness)

**Scope**
- Tighten seed reproducibility expectations between mock and diffusers-enabled paths where practical.
- Ensure safety policy behavior remains consistent regardless of backend.
- Add explicit correctness checks for FPS/duration/frame-count and multishot resampling/crossfade timelines.

**Exit criteria**
- Determinism and timeline correctness tests are green for defined scenarios.
- Safety-gate behavior is validated across text2video/image2video/multishot flows.
- Regression tests protect prompt handling and frame count semantics.

**Primary modules/files**
- `src/goldman_video/safety.py`
- `src/goldman_video/pipeline.py`
- `tests/test_safety.py`, `tests/test_pipeline.py`, `tests/test_cli.py`

### Phase D — Performance and memory profiles

**Scope**
- Define low-VRAM presets and tuning knobs (offload, slicing/chunking strategy, precision guidance).
- Capture benchmark baselines (time/frame, peak memory, output dimensions/fps) for representative settings.
- Publish a benchmark table and recommended presets.

**Exit criteria**
- At least one documented benchmark matrix exists for CPU/CUDA and low-VRAM profiles.
- Low-VRAM preset recommendations are documented and tied to measurable outcomes.
- No regressions in functional tests while profiling hooks are enabled.

**Primary modules/files**
- `src/goldman_video/pipeline.py`
- `src/goldman_video/config.py`
- `README.md` (benchmark table + recommended presets)
- optional profiling helpers under `scripts/`

### Phase E — Production hardening

**Scope**
- Add robust retry/fallback routing for model/provider failures.
- Introduce model cache strategy (local + warm/cold path behavior) and telemetry hooks.
- Improve operability: structured logs/metrics around generation lifecycle and failure classes.

**Exit criteria**
- Failure handling policy is implemented and tested for key error classes.
- Model cache behavior and invalidation strategy are documented.
- Telemetry emits actionable metrics/events for latency, errors, and backend usage.

**Primary modules/files**
- `src/goldman_video/pipeline.py`
- `src/goldman_video/models.py`
- `src/goldman_video/media.py`
- `README.md` and production docs (if added)

from __future__ import annotations

from pathlib import Path
import os
import random
import logging
import imageio.v3 as iio
import numpy as np
from PIL import Image

from .config import GenerationRequest, ShotRequest
from .safety import moderate_prompt
from .watermark import apply_text_watermark
from .media import mux_audio_track
from .models import resolve_model_selection, validated_model_catalog


logger = logging.getLogger(__name__)


class VideoGenerator:
    """
    Minimal open-source-first orchestrator.

    If diffusers backends are installed, swap `_mock_generate` with real model calls.
    """

    def generate(self, req: GenerationRequest) -> Path:
        req.output_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path = req.output_path.with_name(req.output_path.stem + "_raw.mp4")

        if req.shots:
            shot_paths: list[Path] = []
            for idx, shot in enumerate(req.shots):
                safety = moderate_prompt(shot.prompt)
                if not safety.allowed:
                    raise ValueError(safety.reason)
                shot_path = req.output_path.with_name(f"{req.output_path.stem}_shot_{idx:03d}.mp4")
                self._generate_shot(req, shot, shot_path)
                shot_paths.append(shot_path)

            total_frames = self._concatenate_shots(req, req.shots, shot_paths, raw_path)
            watermark_fps = req.fps
        else:
            safety = moderate_prompt(req.prompt)
            if not safety.allowed:
                raise ValueError(safety.reason)
            if self._use_diffusers_backend(req):
                self._diffusers_generate(req, raw_path)
            else:
                self._mock_generate(req, raw_path)
            total_frames = req.num_frames
            watermark_fps = req.fps

        output = apply_text_watermark(raw_path, req.output_path, req.watermark_text, watermark_fps)

        if req.audio_path is not None:
            output = mux_audio_track(
                video_path=output,
                audio_path=req.audio_path,
                num_frames=total_frames,
                fps=watermark_fps,
                audio_start_sec=req.audio_start_sec,
                audio_volume=req.audio_volume,
                audio_loop=req.audio_loop,
            )
        return output

    def _generate_shot(self, req: GenerationRequest, shot_req: ShotRequest, output_path: Path) -> None:
        shot_gen = GenerationRequest(
            prompt=shot_req.prompt,
            width=req.width,
            height=req.height,
            num_frames=shot_req.num_frames,
            fps=shot_req.fps,
            seed=req.seed,
            image_path=shot_req.image_path,
            output_path=output_path,
            watermark_text=req.watermark_text,
            negative_prompt=req.negative_prompt,
            num_inference_steps=req.num_inference_steps,
            guidance_scale=req.guidance_scale,
            device=req.device,
            low_vram=req.low_vram,
            precision=req.precision,
            use_diffusers=req.use_diffusers,
            vae_model_id=req.vae_model_id,
            vae_tiling=req.vae_tiling,
            vae_slicing=req.vae_slicing,
        )
        if self._use_diffusers_backend(shot_gen):
            self._diffusers_generate(shot_gen, output_path)
        else:
            self._mock_generate(shot_gen, output_path)

    def _concatenate_shots(
        self,
        req: GenerationRequest,
        shots: list[ShotRequest],
        shot_paths: list[Path],
        output_path: Path,
    ) -> int:
        all_frames: list[np.ndarray] = []

        for idx, (shot_req, shot_path) in enumerate(zip(shots, shot_paths)):
            source_frames = list(iio.imread(shot_path, index=None))
            frames = self._resample_to_timeline_fps(source_frames, source_fps=shot_req.fps, target_fps=req.fps)
            if idx == 0:
                all_frames.extend(frames)
                continue

            if shot_req.transition == "crossfade" and shot_req.transition_frames > 0:
                # transition_frames are interpreted in the timeline fps domain.
                n = min(shot_req.transition_frames, len(all_frames), len(frames))
                if n > 0:
                    head = frames[n:]
                    for i in range(n):
                        alpha = (i + 1) / (n + 1)
                        blended = (
                            (1.0 - alpha) * all_frames[-n + i].astype(np.float32)
                            + alpha * frames[i].astype(np.float32)
                        ).astype(np.uint8)
                        all_frames[-n + i] = blended
                    all_frames.extend(head)
                else:
                    all_frames.extend(frames)
            else:
                all_frames.extend(frames)

        iio.imwrite(output_path, all_frames, fps=req.fps)
        return len(all_frames)

    @staticmethod
    def _resample_to_timeline_fps(
        frames: list[np.ndarray],
        source_fps: int,
        target_fps: int,
    ) -> list[np.ndarray]:
        if not frames:
            return []
        if source_fps <= 0 or target_fps <= 0:
            return frames

        target_count = max(1, int(round(len(frames) * target_fps / source_fps)))
        indices = np.linspace(0, len(frames) - 1, num=target_count).round().astype(int)
        return [frames[i] for i in indices]

    def _mock_generate(self, req: GenerationRequest, output: Path) -> None:
        seed = req.seed if req.seed is not None else random.randint(0, 2**31 - 1)
        rng = np.random.default_rng(seed)

        def frame_iter() -> list[np.ndarray]:
            if req.image_path is None:
                # "noise to clean" mock: start from noise then apply temporal smoothing.
                smooth_factor = min(max(req.num_inference_steps / 200.0, 0.1), 2.0)
                alpha = min(0.25 * smooth_factor, 0.6)
                prev: np.ndarray | None = None
                for _ in range(req.num_frames):
                    raw = rng.integers(0, 255, size=(req.height, req.width, 3), dtype=np.uint8).astype(np.float32)
                    if prev is None:
                        clean = raw
                    else:
                        clean = ((1.0 - alpha) * prev) + (alpha * raw)
                    prev = clean
                    yield np.clip(clean, 0, 255).astype(np.uint8)
                return

            if not req.image_path.exists() or not req.image_path.is_file():
                raise ValueError(f"image_path does not exist or is not a file: {req.image_path}")

            try:
                with Image.open(req.image_path) as img:
                    base = img.convert("RGB")
            except Exception as exc:
                raise ValueError(f"image_path is not readable as an image: {req.image_path}") from exc

            resized = np.asarray(base.resize((req.width, req.height), Image.Resampling.LANCZOS))
            span = max(req.num_frames - 1, 1)
            style = req.animation_style
            intensity = float(req.animation_intensity)

            for i in range(req.num_frames):
                t = i / span
                frame = resized

                if style in {"pan", "pan_zoom"}:
                    max_shift = max(1, int((req.width // 24) * intensity))
                    base_shift = int(t * max_shift)
                    wobble = int(round(np.sin(t * np.pi * 2) * max(1, int(max_shift * 0.25))))
                    frame = np.roll(frame, shift=base_shift + wobble, axis=1)

                if style in {"zoom", "pan_zoom"}:
                    max_zoom = min(0.12 * intensity, 0.25)
                    zoom = 1.0 + (max_zoom * t)
                    crop_w = max(1, int(req.width / zoom))
                    crop_h = max(1, int(req.height / zoom))
                    cx = req.width // 2
                    cy = req.height // 2
                    x0 = max(0, min(req.width - crop_w, cx - crop_w // 2))
                    y0 = max(0, min(req.height - crop_h, cy - crop_h // 2))
                    cropped = frame[y0:y0 + crop_h, x0:x0 + crop_w]
                    frame = np.asarray(Image.fromarray(cropped).resize((req.width, req.height), Image.Resampling.LANCZOS))

                yield frame.astype(np.uint8)

        # Stream-write frames to reduce memory footprint for 1080p/4k and longer durations.
        try:
            with iio.imopen(output, "w") as writer:
                writer.init_video_stream("libx264", fps=req.fps)
                for frame in frame_iter():
                    writer.write_frame(frame)
        except Exception:
            iio.imwrite(output, list(frame_iter()), fps=req.fps)


    @staticmethod
    def _use_diffusers_backend(req: GenerationRequest) -> bool:
        return req.use_diffusers or os.getenv("GOLDMAN_VIDEO_USE_DIFFUSERS", "0") == "1"

    @staticmethod
    def _resolve_runtime_policy(req: GenerationRequest, torch_module: object) -> dict[str, object]:
        device = req.device
        if device == "auto":
            device = "cuda" if torch_module.cuda.is_available() else "cpu"

        dtype_map = {
            "fp32": torch_module.float32,
            "fp16": torch_module.float16,
            "bf16": torch_module.bfloat16,
        }
        torch_dtype = dtype_map.get(req.precision, torch_module.float16)

        memory_strategy = ["standard"]
        if req.low_vram:
            memory_strategy = ["model_cpu_offload", "attention_slicing", "vae_slicing"]

        return {
            "device": device,
            "torch_dtype": torch_dtype,
            "memory_strategy": memory_strategy,
        }

    def _diffusers_generate(self, req: GenerationRequest, output: Path) -> None:
        selection = resolve_model_selection(req)

        try:
            import torch  # type: ignore
            from diffusers import AutoencoderKL, DiffusionPipeline, StableVideoDiffusionPipeline  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Diffusers backend requires optional generation dependencies. "
                "Install with `pip install -e .[gen]`."
            ) from exc

        policy = self._resolve_runtime_policy(req, torch)
        device = policy["device"]
        torch_dtype = policy["torch_dtype"]
        logger.debug("Resolved runtime policy: %s", policy)

        if req.image_path is None:
            model_id = selection.model_id
            pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=torch_dtype)
            infer_kwargs = {
                "prompt": req.prompt,
                "negative_prompt": req.negative_prompt,
                "num_inference_steps": req.num_inference_steps,
                "guidance_scale": req.guidance_scale,
            }
            if "num_frames" in pipe.__call__.__code__.co_varnames:
                infer_kwargs["num_frames"] = req.num_frames
        else:
            if not req.image_path.exists() or not req.image_path.is_file():
                raise ValueError(f"image_path does not exist or is not a file: {req.image_path}")

            model_id = selection.model_id
            pipe = StableVideoDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch_dtype)
            with Image.open(req.image_path) as img:
                infer_kwargs = {
                    "image": img.convert("RGB"),
                    "num_inference_steps": req.num_inference_steps,
                }
            if "num_frames" in pipe.__call__.__code__.co_varnames:
                infer_kwargs["num_frames"] = req.num_frames

        vae_settings = {
            "vae_model_id": req.vae_model_id,
            "vae_tiling": req.vae_tiling,
            "vae_slicing": req.vae_slicing,
        }

        if req.vae_model_id:
            pipe.vae = AutoencoderKL.from_pretrained(req.vae_model_id, torch_dtype=torch_dtype)
            logger.debug("Applied custom VAE model", extra={"vae_model_id": req.vae_model_id})

        if req.vae_tiling and hasattr(pipe, "enable_vae_tiling"):
            pipe.enable_vae_tiling()
            logger.debug("Enabled VAE tiling")

        if req.vae_slicing and hasattr(pipe, "enable_vae_slicing"):
            pipe.enable_vae_slicing()
            logger.debug("Enabled VAE slicing")

        logger.debug("Resolved VAE settings for diffusers generation: %s", vae_settings)

        memory_strategy = policy["memory_strategy"]
        if "model_cpu_offload" in memory_strategy and hasattr(pipe, "enable_model_cpu_offload"):
            pipe.enable_model_cpu_offload()
        if "attention_slicing" in memory_strategy and hasattr(pipe, "enable_attention_slicing"):
            pipe.enable_attention_slicing()
        if req.low_vram and "vae_slicing" in memory_strategy and hasattr(pipe, "enable_vae_slicing") and not req.vae_slicing:
            pipe.enable_vae_slicing()

        pipe = pipe.to(device)
        result = pipe(**infer_kwargs)

        frames = getattr(result, "frames", None)
        if not frames:
            raise RuntimeError("Diffusers pipeline did not return frames in result.frames")

        if isinstance(frames, list) and frames and isinstance(frames[0], list):
            frames = frames[0]

        output_frames = []
        for frame in frames:
            if isinstance(frame, Image.Image):
                output_frames.append(np.asarray(frame.convert("RGB"), dtype=np.uint8))
            else:
                output_frames.append(np.asarray(frame, dtype=np.uint8))

        if not output_frames:
            raise RuntimeError("Diffusers pipeline returned an empty frame sequence")

        iio.imwrite(output, output_frames, fps=req.fps)


    @staticmethod
    def model_catalog() -> dict:
        return validated_model_catalog()

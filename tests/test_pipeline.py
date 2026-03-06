from pathlib import Path

import pytest


def test_image_to_video_uses_source_image(tmp_path: Path):
    PIL = pytest.importorskip("PIL")
    pytest.importorskip("imageio.v3")
    np = pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator

    image_path = tmp_path / "source.png"
    output_path = tmp_path / "out.mp4"

    img = np.zeros((32, 32, 3), dtype=np.uint8)
    img[:, :, 1] = 180
    PIL.Image.fromarray(img).save(image_path)

    req = GenerationRequest(
        prompt="animate this image",
        image_path=image_path,
        output_path=output_path,
        num_frames=6,
        width=32,
        height=32,
        fps=7,
    )

    out = VideoGenerator().generate(req)
    assert out.exists()


def test_image_to_video_missing_file_raises(tmp_path: Path):
    pytest.importorskip("PIL")
    pytest.importorskip("imageio.v3")
    pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator

    req = GenerationRequest(
        prompt="animate this image",
        image_path=tmp_path / "missing.png",
        output_path=tmp_path / "out.mp4",
        num_frames=3,
    )

    with pytest.raises(ValueError, match="image_path does not exist"):
        VideoGenerator().generate(req)



def test_generate_passes_request_fps_to_watermark(tmp_path: Path, monkeypatch):
    pytest.importorskip("PIL")
    pytest.importorskip("imageio.v3")
    pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator

    captured = {}

    def fake_mock_generate(self, req, output):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"raw")

    def fake_apply_text_watermark(input_video, output_video, text, fps):
        captured["fps"] = fps
        output_video.parent.mkdir(parents=True, exist_ok=True)
        output_video.write_bytes(b"final")
        return output_video

    monkeypatch.setattr(VideoGenerator, "_mock_generate", fake_mock_generate)
    import goldman_video.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod, "apply_text_watermark", fake_apply_text_watermark)

    req = GenerationRequest(
        prompt="fps should flow to watermark",
        output_path=tmp_path / "out.mp4",
        num_frames=2,
        fps=13,
    )

    out = VideoGenerator().generate(req)
    assert out.exists()
    assert captured["fps"] == 13



def test_generate_without_audio_does_not_call_mux(tmp_path: Path, monkeypatch):
    pytest.importorskip("PIL")
    pytest.importorskip("imageio.v3")
    pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator

    called = {"mux": False}

    def fake_mock_generate(self, req, output):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"raw")

    def fake_apply_text_watermark(input_video, output_video, text, fps):
        output_video.parent.mkdir(parents=True, exist_ok=True)
        output_video.write_bytes(b"final")
        return output_video

    def fake_mux_audio_track(**kwargs):
        called["mux"] = True
        return kwargs["video_path"]

    monkeypatch.setattr(VideoGenerator, "_mock_generate", fake_mock_generate)
    import goldman_video.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod, "apply_text_watermark", fake_apply_text_watermark)
    monkeypatch.setattr(pipeline_mod, "mux_audio_track", fake_mux_audio_track)

    req = GenerationRequest(
        prompt="no audio requested",
        output_path=tmp_path / "out.mp4",
        num_frames=2,
        fps=8,
        audio_path=None,
    )

    out = VideoGenerator().generate(req)
    assert out.exists()
    assert called["mux"] is False



def test_generate_with_audio_calls_mux(tmp_path: Path, monkeypatch):
    pytest.importorskip("PIL")
    pytest.importorskip("imageio.v3")
    pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator

    audio = tmp_path / "track.mp3"
    audio.write_bytes(b"audio")
    captured = {}

    def fake_mock_generate(self, req, output):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"raw")

    def fake_apply_text_watermark(input_video, output_video, text, fps):
        output_video.parent.mkdir(parents=True, exist_ok=True)
        output_video.write_bytes(b"final")
        return output_video

    def fake_mux_audio_track(**kwargs):
        captured.update(kwargs)
        return kwargs["video_path"]

    monkeypatch.setattr(VideoGenerator, "_mock_generate", fake_mock_generate)
    import goldman_video.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod, "apply_text_watermark", fake_apply_text_watermark)
    monkeypatch.setattr(pipeline_mod, "mux_audio_track", fake_mux_audio_track)

    req = GenerationRequest(
        prompt="with audio",
        output_path=tmp_path / "out.mp4",
        num_frames=16,
        fps=8,
        audio_path=audio,
        audio_start_sec=0.5,
        audio_volume=0.8,
        audio_loop=True,
    )

    out = VideoGenerator().generate(req)
    assert out.exists()
    assert captured["audio_path"] == audio
    assert captured["num_frames"] == 16
    assert captured["fps"] == 8
    assert captured["audio_start_sec"] == 0.5
    assert captured["audio_volume"] == 0.8
    assert captured["audio_loop"] is True


def test_multishot_generation_preserves_order(tmp_path: Path, monkeypatch):
    pytest.importorskip("PIL")
    pytest.importorskip("imageio.v3")
    pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest, ShotRequest
    from goldman_video.pipeline import VideoGenerator

    calls = {"prompts": [], "shot_paths": []}

    def fake_generate_shot(self, req, shot_req, output_path):
        calls["prompts"].append(shot_req.prompt)
        calls["shot_paths"].append(output_path.name)
        output_path.write_bytes(shot_req.prompt.encode())

    def fake_concat(self, req, shots, shot_paths, output_path):
        output_path.write_bytes(b"joined")
        return sum(s.num_frames for s in shots)

    def fake_watermark(input_video, output_video, text, fps):
        output_video.write_bytes(b"final")
        return output_video

    monkeypatch.setattr(VideoGenerator, "_generate_shot", fake_generate_shot)
    monkeypatch.setattr(VideoGenerator, "_concatenate_shots", fake_concat)
    import goldman_video.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod, "apply_text_watermark", fake_watermark)

    req = GenerationRequest(
        prompt="master prompt",
        output_path=tmp_path / "multi.mp4",
        shots=[
            ShotRequest(prompt="shot one", num_frames=4),
            ShotRequest(prompt="shot two", num_frames=5),
            ShotRequest(prompt="shot three", num_frames=6),
        ],
    )

    out = VideoGenerator().generate(req)
    assert out.exists()
    assert calls["prompts"] == ["shot one", "shot two", "shot three"]
    assert calls["shot_paths"] == [
        "multi_shot_000.mp4",
        "multi_shot_001.mp4",
        "multi_shot_002.mp4",
    ]


def test_generate_shot_selects_image_or_text_mode(tmp_path: Path, monkeypatch):
    PIL = pytest.importorskip("PIL")
    np = pytest.importorskip("numpy")
    pytest.importorskip("imageio.v3")

    from goldman_video.config import GenerationRequest, ShotRequest
    from goldman_video.pipeline import VideoGenerator

    image = tmp_path / "seed.png"
    PIL.Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(image)

    seen = []

    def fake_mock_generate(self, req, output):
        seen.append(req.image_path)
        output.write_bytes(b"ok")

    monkeypatch.setattr(VideoGenerator, "_mock_generate", fake_mock_generate)

    gen = VideoGenerator()
    base = GenerationRequest(prompt="base", width=32, height=32)
    gen._generate_shot(base, ShotRequest(prompt="text shot", image_path=None), tmp_path / "a.mp4")
    gen._generate_shot(base, ShotRequest(prompt="image shot", image_path=image), tmp_path / "b.mp4")

    assert seen[0] is None
    assert seen[1] == image


def test_concatenate_shots_crossfade_duration(tmp_path: Path):
    pytest.importorskip("imageio.v3")
    np = pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest, ShotRequest
    from goldman_video.pipeline import VideoGenerator
    import imageio.v3 as iio

    shot1 = tmp_path / "s1.mp4"
    shot2 = tmp_path / "s2.mp4"
    out = tmp_path / "joined.mp4"

    f1 = [np.zeros((16, 16, 3), dtype=np.uint8) for _ in range(6)]
    f2 = [np.full((16, 16, 3), 200, dtype=np.uint8) for _ in range(6)]
    iio.imwrite(shot1, f1, fps=8)
    iio.imwrite(shot2, f2, fps=8)

    req = GenerationRequest(prompt="multi", fps=8)
    shots = [
        ShotRequest(prompt="a", num_frames=6),
        ShotRequest(prompt="b", num_frames=6, transition="crossfade", transition_frames=2),
    ]

    total = VideoGenerator()._concatenate_shots(req, shots, [shot1, shot2], out)
    frames = iio.imread(out, index=None)
    assert total == 10
    assert len(frames) == 10


def test_concatenate_shots_preserves_duration_with_mixed_fps(tmp_path: Path):
    pytest.importorskip("imageio.v3")
    np = pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest, ShotRequest
    from goldman_video.pipeline import VideoGenerator
    import imageio.v3 as iio

    shot1 = tmp_path / "mixed_s1.mp4"
    shot2 = tmp_path / "mixed_s2.mp4"
    out = tmp_path / "mixed_joined.mp4"

    # 6 frames @ 6 fps => 1.0s
    f1 = [np.zeros((16, 16, 3), dtype=np.uint8) for _ in range(6)]
    # 12 frames @ 12 fps => 1.0s
    f2 = [np.full((16, 16, 3), 180, dtype=np.uint8) for _ in range(12)]
    iio.imwrite(shot1, f1, fps=6)
    iio.imwrite(shot2, f2, fps=12)

    req = GenerationRequest(prompt="multi", fps=8)
    shots = [
        ShotRequest(prompt="a", num_frames=6, fps=6),
        ShotRequest(prompt="b", num_frames=12, fps=12),
    ]

    total = VideoGenerator()._concatenate_shots(req, shots, [shot1, shot2], out)
    frames = iio.imread(out, index=None)

    # 1.0s + 1.0s on an 8fps timeline -> 16 frames expected.
    assert total == 16
    assert len(frames) == 16


def test_concatenate_shots_crossfade_uses_timeline_frames_with_mixed_fps(tmp_path: Path):
    pytest.importorskip("imageio.v3")
    np = pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest, ShotRequest
    from goldman_video.pipeline import VideoGenerator
    import imageio.v3 as iio

    shot1 = tmp_path / "xf_s1.mp4"
    shot2 = tmp_path / "xf_s2.mp4"
    out = tmp_path / "xf_joined.mp4"

    # 8 frames @ 8 fps => 1.0s -> 8 timeline frames
    f1 = [np.zeros((16, 16, 3), dtype=np.uint8) for _ in range(8)]
    # 12 frames @ 12 fps => 1.0s -> resampled to 8 timeline frames
    f2 = [np.full((16, 16, 3), 220, dtype=np.uint8) for _ in range(12)]
    iio.imwrite(shot1, f1, fps=8)
    iio.imwrite(shot2, f2, fps=12)

    req = GenerationRequest(prompt="multi", fps=8)
    shots = [
        ShotRequest(prompt="a", num_frames=8, fps=8),
        ShotRequest(prompt="b", num_frames=12, fps=12, transition="crossfade", transition_frames=3),
    ]

    total = VideoGenerator()._concatenate_shots(req, shots, [shot1, shot2], out)
    frames = iio.imread(out, index=None)

    # 8 + 8 - 3 overlap (timeline frames) = 13
    assert total == 13
    assert len(frames) == 13


def test_shot_request_invalid_transition_rejected():
    pydantic = pytest.importorskip("pydantic")
    ValidationError = pydantic.ValidationError
    from goldman_video.config import ShotRequest

    with pytest.raises(ValidationError):
        ShotRequest(prompt="bad", transition="fade")


def test_shot_request_negative_transition_frames_rejected():
    pydantic = pytest.importorskip("pydantic")
    ValidationError = pydantic.ValidationError
    from goldman_video.config import ShotRequest

    with pytest.raises(ValidationError):
        ShotRequest(prompt="bad", transition="crossfade", transition_frames=-1)


def test_shot_request_cut_normalizes_transition_frames_to_zero():
    pytest.importorskip("pydantic")
    from goldman_video.config import ShotRequest

    shot = ShotRequest(prompt="cut shot", transition="cut", transition_frames=5)
    assert shot.transition_frames == 0


def test_generation_request_numeric_constraints():
    pydantic = pytest.importorskip("pydantic")
    ValidationError = pydantic.ValidationError
    from goldman_video.config import GenerationRequest

    with pytest.raises(ValidationError):
        GenerationRequest(prompt="x", fps=0)

    with pytest.raises(ValidationError):
        GenerationRequest(prompt="x", num_frames=0)

    with pytest.raises(ValidationError):
        GenerationRequest(prompt="x", audio_start_sec=-0.1)

    with pytest.raises(ValidationError):
        GenerationRequest(prompt="x", audio_volume=-1.0)


def test_generation_request_duration_sets_num_frames_and_24fps_default():
    pytest.importorskip("pydantic")
    from goldman_video.config import GenerationRequest

    req = GenerationRequest(prompt="x", duration_seconds=5)
    assert req.fps == 24
    assert req.num_frames == 120


def test_generation_request_resolution_presets_map_to_dimensions():
    pytest.importorskip("pydantic")
    from goldman_video.config import GenerationRequest

    req_1080 = GenerationRequest(prompt="x", resolution_preset="1080p")
    req_4k = GenerationRequest(prompt="x", resolution_preset="4k")

    assert (req_1080.width, req_1080.height) == (1920, 1080)
    assert (req_4k.width, req_4k.height) == (3840, 2160)


def test_image_animation_is_deterministic_with_fixed_seed(tmp_path: Path, monkeypatch):
    PIL = pytest.importorskip("PIL")
    np = pytest.importorskip("numpy")
    pytest.importorskip("imageio.v3")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator
    import goldman_video.pipeline as pipeline_mod

    image = tmp_path / "seed.png"
    grad = np.tile(np.arange(32, dtype=np.uint8), (32, 1))
    rgb = np.stack([grad, grad, grad], axis=2)
    PIL.Image.fromarray(rgb).save(image)

    class FakeWriter:
        def __init__(self, bucket):
            self.bucket = bucket

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def init_video_stream(self, *_args, **_kwargs):
            return None

        def write_frame(self, frame):
            self.bucket.append(frame.copy())

    captures: list[list[np.ndarray]] = [[], []]

    def mk_imopen(idx):
        def _imopen(_output, _mode):
            return FakeWriter(captures[idx])
        return _imopen

    req = GenerationRequest(
        prompt="animate",
        image_path=image,
        width=32,
        height=32,
        num_frames=6,
        fps=24,
        seed=123,
        animation_style="pan_zoom",
        animation_intensity=1.0,
        output_path=tmp_path / "x.mp4",
    )

    monkeypatch.setattr(pipeline_mod.iio, "imopen", mk_imopen(0))
    VideoGenerator()._mock_generate(req, tmp_path / "a.mp4")

    monkeypatch.setattr(pipeline_mod.iio, "imopen", mk_imopen(1))
    VideoGenerator()._mock_generate(req, tmp_path / "b.mp4")

    assert len(captures[0]) == len(captures[1]) == 6
    for f1, f2 in zip(captures[0], captures[1]):
        assert np.array_equal(f1, f2)


def test_image_animation_pan_mode_has_no_random_noise(tmp_path: Path, monkeypatch):
    PIL = pytest.importorskip("PIL")
    np = pytest.importorskip("numpy")
    pytest.importorskip("imageio.v3")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator
    import goldman_video.pipeline as pipeline_mod

    image = tmp_path / "flat.png"
    flat = np.full((24, 24, 3), 120, dtype=np.uint8)
    PIL.Image.fromarray(flat).save(image)

    frames: list[np.ndarray] = []

    class FakeWriter:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def init_video_stream(self, *_args, **_kwargs):
            return None

        def write_frame(self, frame):
            frames.append(frame.copy())

    monkeypatch.setattr(pipeline_mod.iio, "imopen", lambda *_args, **_kwargs: FakeWriter())

    req = GenerationRequest(
        prompt="animate",
        image_path=image,
        width=24,
        height=24,
        num_frames=5,
        fps=24,
        animation_style="pan",
        animation_intensity=1.0,
        output_path=tmp_path / "flat.mp4",
    )

    VideoGenerator()._mock_generate(req, tmp_path / "flat_out.mp4")

    assert len(frames) == 5
    for f in frames[1:]:
        assert np.array_equal(f, frames[0])


def test_generation_request_defaults_to_200_samples():
    pytest.importorskip("pydantic")
    from goldman_video.config import GenerationRequest

    req = GenerationRequest(prompt="x")
    assert req.num_inference_steps == 200


def test_text_mock_noise_to_clean_temporal_smoothing(tmp_path: Path, monkeypatch):
    np = pytest.importorskip("numpy")
    pytest.importorskip("imageio.v3")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator
    import goldman_video.pipeline as pipeline_mod

    frames: list[np.ndarray] = []

    class FakeWriter:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def init_video_stream(self, *_args, **_kwargs):
            return None

        def write_frame(self, frame):
            frames.append(frame.copy())

    monkeypatch.setattr(pipeline_mod.iio, "imopen", lambda *_args, **_kwargs: FakeWriter())

    req = GenerationRequest(
        prompt="noise to clean",
        num_frames=8,
        width=32,
        height=32,
        seed=7,
        num_inference_steps=200,
        output_path=tmp_path / "out.mp4",
    )

    VideoGenerator()._mock_generate(req, tmp_path / "mock.mp4")

    assert len(frames) == 8
    # ensure frames are not identical pure static output and are temporally correlated
    diffs = [
        np.abs(frames[i].astype(np.int16) - frames[i - 1].astype(np.int16)).mean()
        for i in range(1, len(frames))
    ]
    assert max(diffs) > 0
    assert np.mean(diffs) < 80  # cleaner than frame-independent random noise


def test_generate_uses_diffusers_backend_when_enabled(tmp_path: Path, monkeypatch):
    pytest.importorskip("PIL")
    pytest.importorskip("imageio.v3")
    pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator

    monkeypatch.setenv("GOLDMAN_VIDEO_USE_DIFFUSERS", "1")
    calls = {"mock": 0, "diffusers": 0}

    def fake_mock_generate(self, req, output):
        calls["mock"] += 1
        output.write_bytes(b"raw-mock")

    def fake_diffusers_generate(self, req, output):
        calls["diffusers"] += 1
        output.write_bytes(b"raw-diffusers")

    def fake_apply_text_watermark(input_video, output_video, text, fps):
        output_video.write_bytes(b"final")
        return output_video

    monkeypatch.setattr(VideoGenerator, "_mock_generate", fake_mock_generate)
    monkeypatch.setattr(VideoGenerator, "_diffusers_generate", fake_diffusers_generate)
    import goldman_video.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod, "apply_text_watermark", fake_apply_text_watermark)

    req = GenerationRequest(prompt="use diffusers", output_path=tmp_path / "out.mp4", num_frames=3)
    out = VideoGenerator().generate(req)

    assert out.exists()
    assert calls["diffusers"] == 1
    assert calls["mock"] == 0


def test_diffusers_generate_missing_deps_has_actionable_error(tmp_path: Path, monkeypatch):
    pytest.importorskip("PIL")
    pytest.importorskip("imageio.v3")
    pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator
    import builtins

    orig_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in {"torch", "diffusers"}:
            raise ModuleNotFoundError(name)
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    req = GenerationRequest(prompt="x", output_path=tmp_path / "out.mp4", num_frames=2)
    with pytest.raises(RuntimeError, match=r"pip install -e \.\[gen\]"):
        VideoGenerator()._diffusers_generate(req, tmp_path / "raw.mp4")


def test_diffusers_generate_applies_vae_model_and_toggles(tmp_path: Path, monkeypatch, caplog):
    pytest.importorskip("PIL")
    pytest.importorskip("imageio.v3")
    np = pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator
    import goldman_video.pipeline as pipeline_mod
    import builtins
    import logging
    import types

    class FakeAutoencoderKL:
        calls = []

        @classmethod
        def from_pretrained(cls, model_id, torch_dtype=None):
            cls.calls.append((model_id, torch_dtype))
            return object()

    class FakePipe:
        tiling_calls = 0
        slicing_calls = 0

        def __init__(self):
            self.vae = None

        @classmethod
        def from_pretrained(cls, model_id, torch_dtype=None):
            return cls()

        def enable_vae_tiling(self):
            type(self).tiling_calls += 1

        def enable_vae_slicing(self):
            type(self).slicing_calls += 1

        def to(self, _device):
            return self

        def __call__(self, prompt, negative_prompt, num_inference_steps, guidance_scale, num_frames=None):
            frame = np.zeros((8, 8, 3), dtype=np.uint8)
            return types.SimpleNamespace(frames=[frame for _ in range(num_frames or 2)])

    fake_torch = types.SimpleNamespace(
        float32="float32",
        float16="float16",
        bfloat16="bfloat16",
        cuda=types.SimpleNamespace(is_available=lambda: False),
    )
    fake_diffusers = types.SimpleNamespace(
        AutoencoderKL=FakeAutoencoderKL,
        DiffusionPipeline=FakePipe,
        StableVideoDiffusionPipeline=FakePipe,
    )

    orig_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "torch":
            return fake_torch
        if name == "diffusers":
            return fake_diffusers
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(pipeline_mod.iio, "imwrite", lambda *_args, **_kwargs: None)

    req = GenerationRequest(
        prompt="vae test",
        output_path=tmp_path / "out.mp4",
        num_frames=3,
        vae_model_id="stabilityai/sd-vae-ft-mse",
        vae_tiling=True,
        vae_slicing=True,
    )

    caplog.set_level(logging.DEBUG)
    VideoGenerator()._diffusers_generate(req, tmp_path / "raw.mp4")

    assert FakeAutoencoderKL.calls
    assert FakeAutoencoderKL.calls[0][0] == "stabilityai/sd-vae-ft-mse"
    assert FakePipe.tiling_calls == 1
    assert FakePipe.slicing_calls == 1
    assert "Enabled VAE tiling" in caplog.text
    assert "Enabled VAE slicing" in caplog.text
    assert "Resolved VAE settings for diffusers generation" in caplog.text


def test_resolve_runtime_policy_auto_cuda(monkeypatch):
    pytest.importorskip("pydantic")
    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator
    import types

    fake_torch = types.SimpleNamespace(
        float32="float32",
        float16="float16",
        bfloat16="bfloat16",
        cuda=types.SimpleNamespace(is_available=lambda: True),
    )

    req = GenerationRequest(prompt="p", device="auto", precision="bf16", low_vram=True)
    policy = VideoGenerator._resolve_runtime_policy(req, fake_torch)

    assert policy["device"] == "cuda"
    assert policy["torch_dtype"] == "bfloat16"
    assert policy["memory_strategy"] == ["model_cpu_offload", "attention_slicing", "vae_slicing"]


def test_resolve_runtime_policy_auto_cpu(monkeypatch):
    pytest.importorskip("pydantic")
    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator
    import types

    fake_torch = types.SimpleNamespace(
        float32="float32",
        float16="float16",
        bfloat16="bfloat16",
        cuda=types.SimpleNamespace(is_available=lambda: False),
    )

    req = GenerationRequest(prompt="p", device="auto", precision="fp32", low_vram=False)
    policy = VideoGenerator._resolve_runtime_policy(req, fake_torch)

    assert policy["device"] == "cpu"
    assert policy["torch_dtype"] == "float32"
    assert policy["memory_strategy"] == ["standard"]


def test_diffusers_generate_applies_low_vram_memory_strategy(tmp_path: Path, monkeypatch):
    pytest.importorskip("PIL")
    pytest.importorskip("imageio.v3")
    np = pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator
    import goldman_video.pipeline as pipeline_mod
    import builtins
    import types

    class FakeAutoencoderKL:
        @classmethod
        def from_pretrained(cls, model_id, torch_dtype=None):
            return object()

    class FakePipe:
        offload_calls = 0
        attention_calls = 0

        def __init__(self):
            self.vae = None

        @classmethod
        def from_pretrained(cls, model_id, torch_dtype=None):
            return cls()

        def enable_model_cpu_offload(self):
            type(self).offload_calls += 1

        def enable_attention_slicing(self):
            type(self).attention_calls += 1

        def to(self, _device):
            return self

        def __call__(self, prompt, negative_prompt, num_inference_steps, guidance_scale, num_frames=None):
            frame = np.zeros((8, 8, 3), dtype=np.uint8)
            return types.SimpleNamespace(frames=[frame for _ in range(num_frames or 2)])

    fake_torch = types.SimpleNamespace(
        float32="float32",
        float16="float16",
        bfloat16="bfloat16",
        cuda=types.SimpleNamespace(is_available=lambda: False),
    )
    fake_diffusers = types.SimpleNamespace(
        AutoencoderKL=FakeAutoencoderKL,
        DiffusionPipeline=FakePipe,
        StableVideoDiffusionPipeline=FakePipe,
    )

    orig_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "torch":
            return fake_torch
        if name == "diffusers":
            return fake_diffusers
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(pipeline_mod.iio, "imwrite", lambda *_args, **_kwargs: None)

    req = GenerationRequest(
        prompt="low vram",
        output_path=tmp_path / "out.mp4",
        num_frames=3,
        low_vram=True,
    )

    VideoGenerator()._diffusers_generate(req, tmp_path / "raw.mp4")

    assert FakePipe.offload_calls == 1
    assert FakePipe.attention_calls == 1


def test_diffusers_generate_rejects_text2video_with_vae(tmp_path: Path):
    pytest.importorskip("PIL")
    pytest.importorskip("imageio.v3")
    pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator

    req = GenerationRequest(
        prompt="bad combo",
        output_path=tmp_path / "out.mp4",
        num_frames=2,
        vae_model_id="stabilityai/sd-vae-ft-mse",
    )

    with pytest.raises(ValueError, match="only supported for image2video"):
        VideoGenerator()._diffusers_generate(req, tmp_path / "raw.mp4")


def test_diffusers_generate_rejects_missing_mode_model_config(tmp_path: Path, monkeypatch):
    pytest.importorskip("PIL")
    pytest.importorskip("imageio.v3")
    pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator
    import goldman_video.models as models_mod

    patched = dict(models_mod.OPEN_SOURCE_MODELS)
    patched.pop("text_to_video", None)
    monkeypatch.setattr(models_mod, "OPEN_SOURCE_MODELS", patched)

    req = GenerationRequest(prompt="missing model", output_path=tmp_path / "out.mp4", num_frames=2)

    with pytest.raises(ValueError, match="No model configured for mode 'text2video'"):
        VideoGenerator()._diffusers_generate(req, tmp_path / "raw.mp4")


def test_generate_uses_mock_backend_by_default(tmp_path: Path, monkeypatch):
    pytest.importorskip("PIL")
    pytest.importorskip("imageio.v3")
    pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator

    calls = {"mock": 0, "diffusers": 0}

    def fake_mock_generate(self, req, output):
        calls["mock"] += 1
        output.write_bytes(b"raw-mock")

    def fake_diffusers_generate(self, req, output):
        calls["diffusers"] += 1
        output.write_bytes(b"raw-diffusers")

    def fake_apply_text_watermark(input_video, output_video, text, fps):
        output_video.write_bytes(b"final")
        return output_video

    monkeypatch.delenv("GOLDMAN_VIDEO_USE_DIFFUSERS", raising=False)
    monkeypatch.setattr(VideoGenerator, "_mock_generate", fake_mock_generate)
    monkeypatch.setattr(VideoGenerator, "_diffusers_generate", fake_diffusers_generate)
    import goldman_video.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod, "apply_text_watermark", fake_apply_text_watermark)

    req = GenerationRequest(prompt="use mock", output_path=tmp_path / "out.mp4", num_frames=3)
    out = VideoGenerator().generate(req)

    assert out.exists()
    assert calls["mock"] == 1
    assert calls["diffusers"] == 0


def test_generate_diffusers_still_runs_shared_post_processing(tmp_path: Path, monkeypatch):
    pytest.importorskip("PIL")
    pytest.importorskip("imageio.v3")
    pytest.importorskip("numpy")

    from goldman_video.config import GenerationRequest
    from goldman_video.pipeline import VideoGenerator

    audio = tmp_path / "track.mp3"
    audio.write_bytes(b"audio")
    captured = {}

    def fake_diffusers_generate(self, req, output):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"raw")

    def fake_apply_text_watermark(input_video, output_video, text, fps):
        captured["watermark"] = {"input_video": input_video, "output_video": output_video, "text": text, "fps": fps}
        output_video.write_bytes(b"final")
        return output_video

    def fake_mux_audio_track(**kwargs):
        captured["mux"] = kwargs
        return kwargs["video_path"]

    monkeypatch.setattr(VideoGenerator, "_diffusers_generate", fake_diffusers_generate)
    import goldman_video.pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod, "apply_text_watermark", fake_apply_text_watermark)
    monkeypatch.setattr(pipeline_mod, "mux_audio_track", fake_mux_audio_track)

    req = GenerationRequest(
        prompt="with audio",
        output_path=tmp_path / "out.mp4",
        num_frames=16,
        fps=8,
        audio_path=audio,
        audio_start_sec=0.5,
        audio_volume=0.8,
        audio_loop=True,
        use_diffusers=True,
    )

    out = VideoGenerator().generate(req)
    assert out.exists()
    assert captured["watermark"]["fps"] == 8
    assert captured["watermark"]["text"] == "Generated by Goldman AI"
    assert captured["mux"]["audio_path"] == audio
    assert captured["mux"]["num_frames"] == 16
    assert captured["mux"]["fps"] == 8
    assert captured["mux"]["audio_start_sec"] == 0.5
    assert captured["mux"]["audio_volume"] == 0.8
    assert captured["mux"]["audio_loop"] is True

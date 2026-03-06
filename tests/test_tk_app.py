from pathlib import Path
import json

import pytest

pytest.importorskip("tkinter")
pytest.importorskip("pydantic")

from app.tk_app import (
    build_generation_request,
    parse_and_validate_shots,
    run_generation_job,
    summarize_shots,
)


def test_build_generation_request_text2video_defaults(tmp_path: Path):
    req = build_generation_request(
        mode="text2video",
        prompt="hello",
        output_path=tmp_path / "out.mp4",
        image_path=None,
        audio_path=None,
        spec_path=None,
        width=320,
        height=240,
        fps=8,
        frames=10,
        audio_start_sec=0.0,
        audio_volume=1.0,
        audio_loop=False,
        watermark_text="wm",
    )

    assert req.prompt == "hello"
    assert req.image_path is None
    assert req.num_frames == 10


def test_build_generation_request_image2video_requires_image(tmp_path: Path):
    with pytest.raises(ValueError, match="requires an input image"):
        build_generation_request(
            mode="image2video",
            prompt="hello",
            output_path=tmp_path / "out.mp4",
            image_path=None,
            audio_path=None,
            spec_path=None,
            width=320,
            height=240,
            fps=8,
            frames=10,
            audio_start_sec=0.0,
            audio_volume=1.0,
            audio_loop=False,
            watermark_text="wm",
        )


def test_build_generation_request_multishot_loads_spec(tmp_path: Path):
    spec = tmp_path / "shots.json"
    spec.write_text(json.dumps({"shots": [{"prompt": "one", "num_frames": 4, "fps": 8}]}))

    req = build_generation_request(
        mode="multishot",
        prompt="",
        output_path=tmp_path / "out.mp4",
        image_path=None,
        audio_path=None,
        spec_path=spec,
        width=320,
        height=240,
        fps=8,
        frames=10,
        audio_start_sec=0.0,
        audio_volume=1.0,
        audio_loop=False,
        watermark_text="wm",
    )

    assert req.shots is not None
    assert len(req.shots) == 1
    assert req.shots[0].prompt == "one"


def test_parse_and_validate_shots_returns_field_specific_errors(tmp_path: Path):
    spec = tmp_path / "bad.json"
    spec.write_text(json.dumps({"shots": [{"prompt": "bad", "transition": "fade"}]}))

    with pytest.raises(ValueError, match=r"Shot spec error at .*transition"):
        parse_and_validate_shots(spec)


def test_summarize_shots_contains_count_and_keys(tmp_path: Path):
    spec = tmp_path / "ok.json"
    spec.write_text(json.dumps({"shots": [{"prompt": "intro", "num_frames": 6, "fps": 8}]}))

    _, shots = parse_and_validate_shots(spec)
    lines = summarize_shots(shots)
    assert lines[0] == "Shots: 1"
    assert "frames=6" in lines[1]
    assert "fps=8" in lines[1]


def test_run_generation_job_emits_statuses_and_returns_output(tmp_path: Path):
    from goldman_video.config import GenerationRequest

    events: list[tuple[str, str]] = []

    class DummyGenerator:
        def generate(self, req):
            out = tmp_path / "done.mp4"
            out.write_bytes(b"ok")
            return out

    def build_req() -> GenerationRequest:
        return GenerationRequest(prompt="x", output_path=tmp_path / "out.mp4")

    out = run_generation_job(build_request=build_req, generator=DummyGenerator(), emit=lambda k, m: events.append((k, m)))

    assert out.exists()
    assert events == [
        ("status", "Generating"),
        ("status", "Watermarking/Audio mux"),
    ]


def test_run_generation_job_propagates_errors_after_generating_status(tmp_path: Path):
    from goldman_video.config import GenerationRequest

    events: list[tuple[str, str]] = []

    class FailingGenerator:
        def generate(self, req):
            raise RuntimeError("boom")

    def build_req() -> GenerationRequest:
        return GenerationRequest(prompt="x", output_path=tmp_path / "out.mp4")

    with pytest.raises(RuntimeError, match="boom"):
        run_generation_job(build_request=build_req, generator=FailingGenerator(), emit=lambda k, m: events.append((k, m)))

    assert events == [("status", "Generating")]



def test_build_generation_request_multishot_requires_spec_path(tmp_path: Path):
    with pytest.raises(ValueError, match="requires a JSON/YAML shot spec file"):
        build_generation_request(
            mode="multishot",
            prompt="story",
            output_path=tmp_path / "out.mp4",
            image_path=None,
            audio_path=None,
            spec_path=None,
            width=320,
            height=240,
            fps=8,
            frames=10,
            audio_start_sec=0.0,
            audio_volume=1.0,
            audio_loop=False,
            watermark_text="wm",
        )


def test_run_generation_job_uses_default_videogenerator_and_passes_request(tmp_path: Path, monkeypatch):
    from goldman_video.config import GenerationRequest
    import app.tk_app as tk_app

    captured = {}

    class DummyGenerator:
        def generate(self, req):
            captured["req"] = req
            out = tmp_path / "auto.mp4"
            out.write_bytes(b"ok")
            return out

    monkeypatch.setattr(tk_app, "VideoGenerator", DummyGenerator)

    def build_req() -> GenerationRequest:
        return GenerationRequest(
            prompt="mapped prompt",
            output_path=tmp_path / "out.mp4",
            num_frames=12,
            fps=6,
        )

    out = run_generation_job(build_request=build_req)

    assert out.exists()
    assert captured["req"].prompt == "mapped prompt"
    assert captured["req"].num_frames == 12
    assert captured["req"].fps == 6

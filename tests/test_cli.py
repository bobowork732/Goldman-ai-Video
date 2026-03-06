from pathlib import Path
import json

import pytest

pytest.importorskip("typer")
pytest.importorskip("PIL")
pytest.importorskip("imageio.v3")
pytest.importorskip("numpy")

from typer.testing import CliRunner
from goldman_video.cli import app


runner = CliRunner()


def test_multishot_invalid_transition_returns_friendly_error(tmp_path: Path):
    spec = tmp_path / "shots.json"
    spec.write_text(json.dumps({
        "shots": [
            {"prompt": "one", "transition": "fade"}
        ]
    }))

    result = runner.invoke(app, ["multishot", str(spec)])

    assert result.exit_code != 0
    assert "Invalid shot spec" in result.stdout
    assert "transition" in result.stdout


def test_text2video_forwards_vae_options(monkeypatch, tmp_path: Path):
    captured = {}

    def fake_generate(self, req):
        captured["req"] = req
        return req.output_path

    monkeypatch.setattr("goldman_video.cli.VideoGenerator.generate", fake_generate)

    out = tmp_path / "vae.mp4"
    result = runner.invoke(
        app,
        [
            "text2video",
            "a prompt",
            "--output",
            str(out),
            "--vae",
            "stabilityai/sd-vae-ft-mse",
            "--vae-tiling",
            "--vae-slicing",
        ],
    )

    assert result.exit_code == 0
    req = captured["req"]
    assert req.vae_model_id == "stabilityai/sd-vae-ft-mse"
    assert req.vae_tiling is True
    assert req.vae_slicing is True


def test_models_command_supports_json_output():
    result = runner.invoke(app, ["models", "--json"])

    assert result.exit_code == 0
    assert '"catalog"' in result.stdout
    assert '"validated"' in result.stdout


def test_text2video_vae_invalid_combo_returns_friendly_error(monkeypatch):
    monkeypatch.setenv("GOLDMAN_VIDEO_USE_DIFFUSERS", "1")

    result = runner.invoke(
        app,
        [
            "text2video",
            "a prompt",
            "--vae",
            "stabilityai/sd-vae-ft-mse",
        ],
    )

    assert result.exit_code != 0
    assert "only supported for image2video" in result.stdout


def test_text2video_use_diffusers_flag_reaches_request(monkeypatch, tmp_path: Path):
    captured = {}

    def fake_generate(self, req):
        captured["req"] = req
        return req.output_path

    monkeypatch.setattr("goldman_video.cli.VideoGenerator.generate", fake_generate)

    out = tmp_path / "d.mp4"
    result = runner.invoke(app, ["text2video", "a prompt", "--output", str(out), "--use-diffusers"])

    assert result.exit_code == 0
    assert captured["req"].use_diffusers is True

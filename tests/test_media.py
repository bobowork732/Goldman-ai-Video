from pathlib import Path

import pytest

from goldman_video.media import mux_audio_track


def test_mux_audio_builds_expected_ffmpeg_command(tmp_path: Path, monkeypatch):
    video = tmp_path / "video.mp4"
    audio = tmp_path / "audio.mp3"
    video.write_bytes(b"video")
    audio.write_bytes(b"audio")

    captured = {}

    class Result:
        stdout = ""
        stderr = ""

    def fake_run(cmd, check, capture_output, text):
        captured["cmd"] = cmd
        out = tmp_path / "video_with_audio.mp4"
        out.write_bytes(b"muxed")
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)

    out = mux_audio_track(
        video_path=video,
        audio_path=audio,
        num_frames=52,
        fps=13,
        audio_start_sec=1.25,
        audio_volume=0.4,
        audio_loop=True,
    )

    assert out == video
    cmd = captured["cmd"]
    assert cmd[:4] == ["ffmpeg", "-y", "-i", str(video)]
    assert "-stream_loop" in cmd
    assert "-ss" in cmd and "1.25" in cmd
    assert "-af" in cmd and "volume=0.4" in cmd
    assert "-t" in cmd and "4.000" in cmd


def test_mux_audio_missing_file_raises(tmp_path: Path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")

    with pytest.raises(ValueError, match="audio_path does not exist"):
        mux_audio_track(video_path=video, audio_path=tmp_path / "missing.mp3", num_frames=10, fps=5)


def test_mux_audio_invalid_fps_raises(tmp_path: Path):
    video = tmp_path / "video.mp4"
    audio = tmp_path / "audio.mp3"
    video.write_bytes(b"video")
    audio.write_bytes(b"audio")

    with pytest.raises(ValueError, match="fps must be > 0"):
        mux_audio_track(video_path=video, audio_path=audio, num_frames=10, fps=0)


def test_mux_audio_invalid_num_frames_raises(tmp_path: Path):
    video = tmp_path / "video.mp4"
    audio = tmp_path / "audio.mp3"
    video.write_bytes(b"video")
    audio.write_bytes(b"audio")

    with pytest.raises(ValueError, match="num_frames must be > 0"):
        mux_audio_track(video_path=video, audio_path=audio, num_frames=0, fps=8)

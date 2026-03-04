from __future__ import annotations

from pathlib import Path
import subprocess


def mux_audio_track(
    video_path: Path,
    audio_path: Path,
    num_frames: int,
    fps: int,
    audio_start_sec: float = 0.0,
    audio_volume: float = 1.0,
    audio_loop: bool = False,
) -> Path:
    if not audio_path.exists() or not audio_path.is_file():
        raise ValueError(f"audio_path does not exist or is not a file: {audio_path}")

    if num_frames <= 0:
        raise ValueError(f"num_frames must be > 0 for audio muxing, got {num_frames}")
    if fps <= 0:
        raise ValueError(f"fps must be > 0 for audio muxing, got {fps}")

    duration_sec = num_frames / fps
    tmp_out = video_path.with_name(video_path.stem + "_with_audio" + video_path.suffix)

    cmd = ["ffmpeg", "-y", "-i", str(video_path)]
    if audio_loop:
        cmd.extend(["-stream_loop", "-1"])
    if audio_start_sec > 0:
        cmd.extend(["-ss", str(audio_start_sec)])
    cmd.extend([
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-af",
        f"volume={audio_volume}",
        "-t",
        f"{duration_sec:.3f}",
        "-shortest",
        str(tmp_out),
    ])

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required for audio muxing but was not found in PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffmpeg failed to mux audio: {exc.stderr.strip()}") from exc

    tmp_out.replace(video_path)
    return video_path

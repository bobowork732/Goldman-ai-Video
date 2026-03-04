from __future__ import annotations

import json
from pathlib import Path
from queue import Empty, Queue
import threading
from typing import Any, Callable

import tkinter as tk
from tkinter import filedialog, ttk

from pydantic import ValidationError

from goldman_video.config import GenerationRequest, ShotRequest
from goldman_video.pipeline import VideoGenerator


def load_shot_spec(spec_path: Path) -> dict[str, Any]:
    """Ported from CLI semantics: JSON + optional YAML mapping root."""
    suffix = spec_path.suffix.lower()
    if suffix == ".json":
        data = json.loads(spec_path.read_text())
        if not isinstance(data, dict):
            raise ValueError("JSON spec root must be an object")
        return data

    if suffix in {".yml", ".yaml"}:
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError as exc:
            raise ValueError("YAML spec requires PyYAML installed") from exc
        loaded = yaml.safe_load(spec_path.read_text())
        if not isinstance(loaded, dict):
            raise ValueError("YAML spec root must be a mapping/object")
        return loaded

    raise ValueError("Spec file must be .json, .yml, or .yaml")


def _format_shot_validation_error(exc: ValidationError) -> str:
    details = exc.errors()
    if not details:
        return "Invalid shot spec"
    first = details[0]
    loc = ".".join(str(x) for x in first.get("loc", []))
    msg = first.get("msg", "validation error")
    return f"Shot spec error at {loc}: {msg}"


def parse_and_validate_shots(spec_path: Path) -> tuple[str, list[ShotRequest]]:
    if not spec_path.exists():
        raise ValueError(f"Spec file not found: {spec_path}")

    data = load_shot_spec(spec_path)
    raw_shots = data.get("shots")
    if not raw_shots:
        raise ValueError("Spec must include a non-empty 'shots' list")

    try:
        shots = [ShotRequest.model_validate(shot) for shot in raw_shots]
    except ValidationError as exc:
        raise ValueError(_format_shot_validation_error(exc)) from exc

    return str(data.get("prompt", "")).strip(), shots


def summarize_shots(shots: list[ShotRequest]) -> list[str]:
    lines = [f"Shots: {len(shots)}"]
    for idx, shot in enumerate(shots, start=1):
        mode = "image" if shot.image_path else "text"
        lines.append(
            f"{idx:02d}. {mode} | prompt='{shot.prompt[:40]}' | frames={shot.num_frames} | fps={shot.fps} | transition={shot.transition}({shot.transition_frames})"
        )
    return lines


def build_generation_request(
    *,
    mode: str,
    prompt: str,
    output_path: Path,
    image_path: Path | None,
    audio_path: Path | None,
    spec_path: Path | None,
    width: int,
    height: int,
    fps: int,
    frames: int,
    audio_start_sec: float,
    audio_volume: float,
    audio_loop: bool,
    watermark_text: str,
) -> GenerationRequest:
    prompt = prompt.strip()
    if mode == "multishot":
        if spec_path is None:
            raise ValueError("Multishot mode requires a JSON/YAML shot spec file")
        spec_prompt, shots = parse_and_validate_shots(spec_path)

        return GenerationRequest(
            prompt=spec_prompt or prompt or "multi-shot generation",
            output_path=output_path,
            width=width,
            height=height,
            fps=fps,
            shots=shots,
            audio_path=audio_path,
            audio_start_sec=audio_start_sec,
            audio_volume=audio_volume,
            audio_loop=audio_loop,
            watermark_text=watermark_text,
        )

    if mode == "image2video" and image_path is None:
        raise ValueError("image2video mode requires an input image")

    return GenerationRequest(
        prompt=prompt,
        output_path=output_path,
        image_path=image_path if mode == "image2video" else None,
        width=width,
        height=height,
        fps=fps,
        num_frames=frames,
        audio_path=audio_path,
        audio_start_sec=audio_start_sec,
        audio_volume=audio_volume,
        audio_loop=audio_loop,
        watermark_text=watermark_text,
    )


def run_generation_job(
    *,
    build_request: Callable[[], GenerationRequest],
    generator: VideoGenerator | None = None,
    emit: Callable[[str, str], None] | None = None,
) -> Path:
    emit = emit or (lambda _kind, _message: None)
    emit("status", "Generating")
    req = build_request()
    out = (generator or VideoGenerator()).generate(req)
    emit("status", "Watermarking/Audio mux")
    return out


class TkVideoApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Goldman AI Video - Tk App")
        self.queue: Queue[tuple[str, str]] = Queue()
        self.worker_running = False

        self.mode_var = tk.StringVar(value="text2video")
        self.prompt_var = tk.StringVar(value="a friendly 3D mascot introducing Goldman AI")
        self.image_var = tk.StringVar()
        self.audio_var = tk.StringVar()
        self.spec_var = tk.StringVar()
        self.output_var = tk.StringVar(value="outputs/gui_output.mp4")
        self.width_var = tk.IntVar(value=576)
        self.height_var = tk.IntVar(value=320)
        self.fps_var = tk.IntVar(value=24)
        self.frames_var = tk.IntVar(value=49)
        self.audio_start_var = tk.DoubleVar(value=0.0)
        self.audio_volume_var = tk.DoubleVar(value=1.0)
        self.audio_loop_var = tk.BooleanVar(value=False)
        self.watermark_var = tk.StringVar(value="Generated by Goldman AI")
        self.status_var = tk.StringVar(value="Idle")

        self._build_ui()
        self._refresh_field_state()

    def _build_ui(self) -> None:
        frm = ttk.Frame(self.root, padding=10)
        frm.grid(sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        row = 0
        ttk.Label(frm, text="Mode").grid(row=row, column=0, sticky="w")
        mode = ttk.Combobox(
            frm,
            textvariable=self.mode_var,
            values=["text2video", "image2video", "multishot"],
            state="readonly",
        )
        mode.grid(row=row, column=1, sticky="ew")
        mode.bind("<<ComboboxSelected>>", lambda _: self._refresh_field_state())

        row += 1
        ttk.Label(frm, text="Prompt").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.prompt_var).grid(row=row, column=1, columnspan=2, sticky="ew")

        row += 1
        ttk.Label(frm, text="Image").grid(row=row, column=0, sticky="w")
        self.image_entry = ttk.Entry(frm, textvariable=self.image_var)
        self.image_entry.grid(row=row, column=1, sticky="ew")
        self.image_btn = ttk.Button(frm, text="Browse", command=self._pick_image)
        self.image_btn.grid(row=row, column=2, sticky="ew")

        row += 1
        ttk.Label(frm, text="Multishot spec").grid(row=row, column=0, sticky="w")
        self.spec_entry = ttk.Entry(frm, textvariable=self.spec_var)
        self.spec_entry.grid(row=row, column=1, sticky="ew")
        self.spec_btn = ttk.Button(frm, text="Browse", command=self._pick_spec)
        self.spec_btn.grid(row=row, column=2, sticky="ew")

        row += 1
        self.preview_btn = ttk.Button(frm, text="Load Spec Preview", command=self._preview_spec)
        self.preview_btn.grid(row=row, column=1, columnspan=2, sticky="ew")

        row += 1
        ttk.Label(frm, text="Audio").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.audio_var).grid(row=row, column=1, sticky="ew")
        ttk.Button(frm, text="Browse", command=self._pick_audio).grid(row=row, column=2, sticky="ew")

        row += 1
        ttk.Label(frm, text="Output").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.output_var).grid(row=row, column=1, sticky="ew")
        ttk.Button(frm, text="Browse", command=self._pick_output).grid(row=row, column=2, sticky="ew")

        row += 1
        ttk.Label(frm, text="Width").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.width_var, width=8).grid(row=row, column=1, sticky="w")
        ttk.Label(frm, text="Height").grid(row=row, column=2, sticky="w")
        ttk.Entry(frm, textvariable=self.height_var, width=8).grid(row=row, column=2, sticky="e")

        row += 1
        ttk.Label(frm, text="FPS").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.fps_var, width=8).grid(row=row, column=1, sticky="w")
        ttk.Label(frm, text="Frames").grid(row=row, column=2, sticky="w")
        ttk.Entry(frm, textvariable=self.frames_var, width=8).grid(row=row, column=2, sticky="e")

        row += 1
        ttk.Label(frm, text="Audio start").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.audio_start_var, width=8).grid(row=row, column=1, sticky="w")
        ttk.Label(frm, text="Audio volume").grid(row=row, column=2, sticky="w")
        ttk.Entry(frm, textvariable=self.audio_volume_var, width=8).grid(row=row, column=2, sticky="e")

        row += 1
        ttk.Checkbutton(frm, text="Audio loop", variable=self.audio_loop_var).grid(row=row, column=0, sticky="w")

        row += 1
        ttk.Label(frm, text="Watermark").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.watermark_var).grid(row=row, column=1, columnspan=2, sticky="ew")

        row += 1
        self.generate_btn = ttk.Button(frm, text="Generate", command=self._start_generate)
        self.generate_btn.grid(row=row, column=0, sticky="ew")
        ttk.Label(frm, textvariable=self.status_var).grid(row=row, column=1, columnspan=2, sticky="w")

        row += 1
        self.log_box = tk.Text(frm, height=10, width=80)
        self.log_box.grid(row=row, column=0, columnspan=3, sticky="nsew")

        frm.columnconfigure(1, weight=1)
        frm.columnconfigure(2, weight=1)

    def _refresh_field_state(self) -> None:
        mode = self.mode_var.get()
        image_enabled = mode == "image2video"
        spec_enabled = mode == "multishot"
        self.image_entry.configure(state="normal" if image_enabled else "disabled")
        self.image_btn.configure(state="normal" if image_enabled else "disabled")
        self.spec_entry.configure(state="normal" if spec_enabled else "disabled")
        self.spec_btn.configure(state="normal" if spec_enabled else "disabled")
        self.preview_btn.configure(state="normal" if spec_enabled else "disabled")

    def _append_log(self, text: str) -> None:
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    def _set_error(self, message: str) -> None:
        self.status_var.set("Error")
        self._append_log(f"Error: {message}")

    def _pick_image(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        if path:
            self.image_var.set(path)

    def _pick_audio(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.m4a *.aac *.ogg"), ("All", "*.*")])
        if path:
            self.audio_var.set(path)

    def _pick_spec(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Spec", "*.json *.yml *.yaml")])
        if path:
            self.spec_var.set(path)

    def _pick_output(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
        if path:
            self.output_var.set(path)

    def _preview_spec(self) -> None:
        if self.mode_var.get() != "multishot":
            return

        spec_text = self.spec_var.get().strip()
        if not spec_text:
            self._set_error("Select a multishot spec file first")
            return

        try:
            _, shots = parse_and_validate_shots(Path(spec_text))
            self.status_var.set("Idle")
            self._append_log("Spec preview:")
            for line in summarize_shots(shots):
                self._append_log(f"  {line}")
        except Exception as exc:
            self._set_error(str(exc))

    def _start_generate(self) -> None:
        if self.worker_running:
            return

        # Prevent launch on invalid multishot spec before spawning worker.
        if self.mode_var.get() == "multishot":
            spec_text = self.spec_var.get().strip()
            if not spec_text:
                self._set_error("Multishot mode requires a JSON/YAML shot spec file")
                return
            try:
                parse_and_validate_shots(Path(spec_text))
            except Exception as exc:
                self._set_error(str(exc))
                return

        self.worker_running = True
        self.generate_btn.configure(state="disabled")
        self.status_var.set("Generating")
        self._append_log("Starting generation...")

        thread = threading.Thread(target=self._worker, daemon=True)
        thread.start()
        self.root.after(100, self._poll_queue)

    def _build_request_from_ui(self) -> GenerationRequest:
        return build_generation_request(
            mode=self.mode_var.get(),
            prompt=self.prompt_var.get(),
            output_path=Path(self.output_var.get()),
            image_path=Path(self.image_var.get()) if self.image_var.get() else None,
            audio_path=Path(self.audio_var.get()) if self.audio_var.get() else None,
            spec_path=Path(self.spec_var.get()) if self.spec_var.get() else None,
            width=self.width_var.get(),
            height=self.height_var.get(),
            fps=self.fps_var.get(),
            frames=self.frames_var.get(),
            audio_start_sec=self.audio_start_var.get(),
            audio_volume=self.audio_volume_var.get(),
            audio_loop=self.audio_loop_var.get(),
            watermark_text=self.watermark_var.get(),
        )

    def _worker(self) -> None:
        try:
            out = run_generation_job(
                build_request=self._build_request_from_ui,
                emit=lambda kind, message: self.queue.put((kind, message)),
            )
            self.queue.put(("success", f"Done: {out}"))
        except Exception as exc:
            self.queue.put(("error", str(exc)))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, message = self.queue.get_nowait()
                if kind == "status":
                    self.status_var.set(message)
                    self._append_log(message)
                elif kind == "success":
                    self.status_var.set("Done")
                    self._append_log(message)
                    self.generate_btn.configure(state="normal")
                    self.worker_running = False
                elif kind == "error":
                    self.status_var.set("Error")
                    self._append_log(f"Error: {message}")
                    self.generate_btn.configure(state="normal")
                    self.worker_running = False
        except Empty:
            pass

        if self.worker_running:
            self.root.after(100, self._poll_queue)


def main() -> None:
    root = tk.Tk()
    TkVideoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

"""FFmpeg rendering and progress tracking."""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from config import IMAGE_EXTENSIONS, VIDEO_FORMATS
from settings import load_settings
from utils import ffmpeg_concat_path, require_tool


ProgressCallback = Callable[[int, str], None]
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RenderSettings:
    output_format: str
    resolution: str
    fps: int
    seconds_per_image: float | None


def ffprobe_duration(media_path: Path) -> float:
    app_settings = load_settings()
    ffprobe_override = ""
    ffmpeg_override = str(app_settings.get("ffmpeg_path", "") or "")
    if ffmpeg_override:
        candidate = Path(ffmpeg_override).expanduser().with_name("ffprobe")
        if candidate.is_file():
            ffprobe_override = str(candidate)
    command = [
        require_tool("ffprobe", ffprobe_override),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(media_path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(f"Dauer konnte nicht gelesen werden: {media_path.name}") from error


def write_concat_file(images: list[Path], seconds_per_image: float, target: Path) -> None:
    lines: list[str] = []
    for image in images:
        lines.append(f"file '{ffmpeg_concat_path(image)}'")
        lines.append(f"duration {seconds_per_image:.6f}")
    lines.append(f"file '{ffmpeg_concat_path(images[-1])}'")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_video(
    images: list[Path],
    audio: Path,
    output: Path,
    settings: RenderSettings,
    progress: ProgressCallback | None = None,
) -> None:
    logger.info("Render startet: format=%s resolution=%s fps=%s output=%s", settings.output_format, settings.resolution, settings.fps, output)
    app_settings = load_settings()
    if settings.output_format not in VIDEO_FORMATS:
        raise RuntimeError("Unbekanntes Ausgabeformat.")

    image_files = [path for path in images if path.suffix.lower() in IMAGE_EXTENSIONS]
    if not image_files:
        raise RuntimeError("Bitte mindestens ein Bild hochladen.")

    audio_duration = ffprobe_duration(audio)
    seconds_per_image = settings.seconds_per_image
    if seconds_per_image is None:
        seconds_per_image = audio_duration / len(image_files)
    if seconds_per_image <= 0:
        raise RuntimeError("Die Bilddauer muss groesser als 0 sein.")

    expected_duration = min(audio_duration, seconds_per_image * len(image_files))
    concat_file = output.parent / "images.txt"
    write_concat_file(image_files, seconds_per_image, concat_file)

    video_filter = (
        f"scale={settings.resolution}:force_original_aspect_ratio=decrease,"
        f"pad={settings.resolution}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={settings.fps},format=yuv420p"
    )
    command = [
        require_tool("ffmpeg", str(app_settings.get("ffmpeg_path", "") or "")),
        "-y",
        "-nostats",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-i",
        str(audio),
        "-vf",
        video_filter,
        *VIDEO_FORMATS[settings.output_format]["args"],
        "-shortest",
        "-progress",
        "pipe:1",
        str(output),
    ]

    if progress:
        progress(2, "Rendering gestartet")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stderr = ""
    assert process.stdout is not None
    for line in process.stdout:
        key, _, value = line.strip().partition("=")
        if key == "out_time_ms" and expected_duration > 0:
            if not value.isdigit():
                continue
            percent = min(99, max(2, int((int(value) / 1_000_000) / expected_duration * 100)))
            if progress:
                progress(percent, f"Rendering... {percent} %")
        elif key == "progress" and value == "end" and progress:
            progress(100, "Fertig")

    if process.stderr is not None:
        stderr = process.stderr.read()
    return_code = process.wait()
    if return_code != 0:
        logger.error("ffmpeg fehlgeschlagen: %s", stderr.strip())
        message = stderr.strip().splitlines()[-1] if stderr.strip() else f"ffmpeg ist mit Code {return_code} fehlgeschlagen."
        raise RuntimeError(message)
    logger.info("Render fertig: %s", output)

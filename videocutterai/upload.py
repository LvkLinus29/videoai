"""Multipart upload handling."""

from __future__ import annotations

import cgi
import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from config import (
    DEFAULT_FORMAT,
    DEFAULT_FPS,
    DEFAULT_RESOLUTION,
    IMAGE_EXTENSIONS,
    MAX_FPS,
    MAX_UPLOAD_BYTES,
    MIN_FPS,
    RESOLUTIONS,
    VIDEO_FORMATS,
    WORK_DIR,
)
from renderer import RenderSettings
from settings import load_settings
from utils import safe_name


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UploadResult:
    job_id: str
    job_dir: Path
    images: list[Path]
    audio: Path
    output: Path
    settings: RenderSettings


def parse_upload(handler) -> UploadResult:
    content_length = int(handler.headers.get("Content-Length", "0") or 0)
    if content_length > MAX_UPLOAD_BYTES:
        raise RuntimeError("Upload ist zu groß.")

    form = cgi.FieldStorage(
        fp=handler.rfile,
        headers=handler.headers,
        environ={
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": handler.headers.get("Content-Type", ""),
            "CONTENT_LENGTH": handler.headers.get("Content-Length", "0"),
        },
    )

    app_settings = load_settings()

    output_format = (form.getfirst("format") or app_settings["default_format"] or DEFAULT_FORMAT).lower()
    if output_format not in VIDEO_FORMATS:
        raise RuntimeError("Dieses Ausgabeformat wird nicht unterstützt.")

    resolution = form.getfirst("resolution") or app_settings["default_resolution"] or DEFAULT_RESOLUTION
    if resolution not in RESOLUTIONS:
        raise RuntimeError("Diese Auflösung wird nicht unterstützt.")

    try:
        fps = int(form.getfirst("fps") or str(app_settings["default_fps"] or DEFAULT_FPS))
    except ValueError as error:
        raise RuntimeError("FPS muss eine Zahl sein.") from error
    if fps < MIN_FPS or fps > MAX_FPS:
        raise RuntimeError(f"FPS muss zwischen {MIN_FPS} und {MAX_FPS} liegen.")

    duration_value = form.getfirst("seconds_per_image") or ""
    try:
        seconds_per_image = float(duration_value) if duration_value.strip() else None
    except ValueError as error:
        raise RuntimeError("Sekunden pro Foto muss eine Zahl sein.") from error

    job_id = uuid.uuid4().hex
    job_dir = WORK_DIR / job_id
    input_dir = job_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    images: list[Path] = []
    image_fields = form["images"] if "images" in form else []
    if not isinstance(image_fields, list):
        image_fields = [image_fields]
    for index, field in enumerate(image_fields, start=1):
        if not getattr(field, "filename", ""):
            continue
        target = input_dir / safe_name(field.filename, f"image-{index}.jpg")
        if target.suffix.lower() not in IMAGE_EXTENSIONS:
            raise RuntimeError(f"Nicht unterstütztes Bildformat: {target.name}")
        with target.open("wb") as file:
            shutil.copyfileobj(field.file, file)
        images.append(target)
    if not images:
        raise RuntimeError("Bitte mindestens ein Bild hinzufügen.")

    audio_field = form["audio"] if "audio" in form else None
    if isinstance(audio_field, list):
        audio_field = audio_field[0] if audio_field else None
    if audio_field is None or not getattr(audio_field, "filename", ""):
        raise RuntimeError("Bitte eine Audiodatei hinzufuegen.")

    audio_path = input_dir / safe_name(audio_field.filename, "audio")
    with audio_path.open("wb") as file:
        shutil.copyfileobj(audio_field.file, file)

    extension = VIDEO_FORMATS.get(output_format, VIDEO_FORMATS["mp4"])["extension"]
    output = job_dir / f"video{extension}"
    settings = RenderSettings(output_format, resolution, fps, seconds_per_image)
    logger.info("Upload verarbeitet: job=%s images=%s audio=%s format=%s", job_id, len(images), audio_path.name, output_format)
    return UploadResult(job_id, job_dir, images, audio_path, output, settings)

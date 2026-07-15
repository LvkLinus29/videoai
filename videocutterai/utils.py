"""Small shared helpers for the local app."""

from __future__ import annotations

import mimetypes
import shutil
from pathlib import Path


def require_tool(name: str, override_path: str | None = None) -> str:
    if override_path:
        configured = Path(override_path).expanduser()
        if configured.is_file():
            return str(configured)
    path = shutil.which(name)
    if not path:
        raise RuntimeError(
            f"'{name}' wurde nicht gefunden. Installiere ffmpeg unter Linux mit: sudo apt install ffmpeg"
        )
    return path


def safe_name(filename: str, fallback: str) -> str:
    cleaned = Path(filename or fallback).name.replace("\x00", "")
    return cleaned or fallback


def content_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def ffmpeg_concat_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "'\\''")

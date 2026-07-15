"""Persistent user settings for VideoCutterAI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from config import APP_NAME, DEFAULT_FORMAT, DEFAULT_FPS, DEFAULT_RESOLUTION, RESOLUTIONS, VIDEO_FORMATS


CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME
SETTINGS_FILE = CONFIG_DIR / "settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "theme": "dark",
    "language": "de",
    "default_format": DEFAULT_FORMAT,
    "default_resolution": DEFAULT_RESOLUTION,
    "default_fps": DEFAULT_FPS,
    "default_output_dir": "",
    "ffmpeg_path": "",
}

THEMES = {"dark", "light"}
LANGUAGES = {"de", "en"}


def load_settings() -> dict[str, Any]:
    settings = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.is_file():
        try:
            raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}
        if isinstance(raw, dict):
            settings.update(raw)
    return validate_settings(settings)


def save_settings(data: dict[str, Any]) -> dict[str, Any]:
    settings = load_settings()
    settings.update(data)
    settings = validate_settings(settings)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return settings


def validate_settings(data: dict[str, Any]) -> dict[str, Any]:
    settings = dict(DEFAULT_SETTINGS)

    theme = str(data.get("theme", settings["theme"]))
    settings["theme"] = theme if theme in THEMES else DEFAULT_SETTINGS["theme"]

    language = str(data.get("language", settings["language"]))
    settings["language"] = language if language in LANGUAGES else DEFAULT_SETTINGS["language"]

    output_format = str(data.get("default_format", settings["default_format"])).lower()
    settings["default_format"] = output_format if output_format in VIDEO_FORMATS else DEFAULT_SETTINGS["default_format"]

    resolution = str(data.get("default_resolution", settings["default_resolution"]))
    settings["default_resolution"] = resolution if resolution in RESOLUTIONS else DEFAULT_SETTINGS["default_resolution"]

    try:
        fps = int(data.get("default_fps", settings["default_fps"]))
    except (TypeError, ValueError):
        fps = DEFAULT_SETTINGS["default_fps"]
    settings["default_fps"] = min(60, max(1, fps))

    output_dir = str(data.get("default_output_dir", "") or "").strip()
    settings["default_output_dir"] = output_dir

    ffmpeg_path = str(data.get("ffmpeg_path", "") or "").strip()
    settings["ffmpeg_path"] = ffmpeg_path
    return settings

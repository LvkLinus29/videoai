"""Shared application configuration."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
TEMPLATE_DIR = ROOT / "templates"
WORK_DIR = ROOT / "output" / "jobs"
LOG_DIR = ROOT / "output" / "logs"
LOG_FILE = LOG_DIR / "videocutterai.log"

APP_NAME = "VideoCutterAI"
APP_VERSION = "0.2.0"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7865
DEFAULT_FORMAT = "mp4"
DEFAULT_RESOLUTION = "1920:1080"
DEFAULT_FPS = 30
MAX_FPS = 60
MIN_FPS = 1

RESOLUTIONS = {"1920:1080", "1280:720", "1080:1080", "1080:1920"}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024

VIDEO_FORMATS = {
    "mp4": {
        "extension": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k"],
    },
    "mov": {
        "extension": ".mov",
        "args": ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k"],
    },
    "mkv": {
        "extension": ".mkv",
        "args": ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k"],
    },
    "webm": {
        "extension": ".webm",
        "args": ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0", "-c:a", "libopus", "-b:a", "160k"],
    },
}

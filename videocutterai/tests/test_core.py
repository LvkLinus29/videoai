from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import renderer
import settings
import upload
from config import DEFAULT_FORMAT, DEFAULT_FPS, DEFAULT_RESOLUTION
from utils import content_type, safe_name


class FakeField:
    def __init__(self, filename: str, payload: bytes) -> None:
        import io

        self.filename = filename
        self.file = io.BytesIO(payload)


class FakeForm:
    def __init__(self, fields: dict[str, object]) -> None:
        self.fields = fields

    def getfirst(self, key: str):
        value = self.fields.get(key)
        if isinstance(value, list):
            return value[0]
        return value

    def __contains__(self, key: str) -> bool:
        return key in self.fields

    def __getitem__(self, key: str):
        return self.fields[key]


class CoreTests(unittest.TestCase):
    def test_safe_name_strips_path_parts(self) -> None:
        self.assertEqual(safe_name("../../demo.mp3", "fallback.mp3"), "demo.mp3")

    def test_content_type_falls_back(self) -> None:
        self.assertEqual(content_type(Path("file.unknownext")), "application/octet-stream")

    def test_parse_upload_accepts_expected_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with (
                patch.object(upload, "WORK_DIR", tmp_path / "jobs"),
                patch.object(upload, "DEFAULT_FORMAT", DEFAULT_FORMAT),
                patch.object(upload, "DEFAULT_RESOLUTION", DEFAULT_RESOLUTION),
                patch.object(upload, "DEFAULT_FPS", DEFAULT_FPS),
                patch.object(
                    upload.cgi,
                    "FieldStorage",
                    return_value=FakeForm(
                        {
                            "images": [FakeField("photo.png", b"fake-image")],
                            "audio": FakeField("song.mp3", b"fake-audio"),
                        }
                    ),
                ),
            ):
                handler = type("Handler", (), {"headers": {"Content-Length": "123", "Content-Type": "multipart/form-data"}, "rfile": None})()
                result = upload.parse_upload(handler)

        self.assertEqual(result.settings.output_format, DEFAULT_FORMAT)
        self.assertEqual(result.settings.resolution, DEFAULT_RESOLUTION)
        self.assertEqual(result.settings.fps, DEFAULT_FPS)
        self.assertEqual(len(result.images), 1)
        self.assertTrue(result.audio.name.endswith(".mp3"))
        self.assertTrue(result.output.name.startswith("video"))

    def test_render_video_reports_progress_and_writes_output(self) -> None:
        progress_events: list[tuple[int, str]] = []

        class FakeStdout:
            def __iter__(self):
                return iter([
                    "out_time_ms=5000000\n",
                    "progress=end\n",
                ])

        class FakeStderr:
            def read(self) -> str:
                return ""

        class FakeProcess:
            def __init__(self) -> None:
                self.stdout = FakeStdout()
                self.stderr = FakeStderr()

            def wait(self) -> int:
                return 0

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            image = tmp_path / "a.png"
            image.write_text("fake", encoding="utf-8")
            audio = tmp_path / "a.mp3"
            audio.write_text("fake", encoding="utf-8")
            output = tmp_path / "video.mp4"

            with (
                patch.object(renderer, "ffprobe_duration", return_value=10.0),
                patch.object(renderer.subprocess, "Popen", return_value=FakeProcess()),
                patch.object(renderer, "require_tool", side_effect=lambda name, override_path=None: override_path or name),
            ):
                renderer.render_video(
                    [image],
                    audio,
                    output,
                    renderer.RenderSettings("mp4", "1280:720", 24, None),
                    progress=lambda percent, message: progress_events.append((percent, message)),
                )

            self.assertTrue(progress_events)
            self.assertEqual(progress_events[-1][0], 100)

    def test_settings_are_validated_and_saved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp) / "config"
            settings_file = config_dir / "settings.json"
            with (
                patch.object(settings, "CONFIG_DIR", config_dir),
                patch.object(settings, "SETTINGS_FILE", settings_file),
            ):
                saved = settings.save_settings(
                    {
                        "theme": "light",
                        "language": "de",
                        "default_format": "webm",
                        "default_resolution": "1280:720",
                        "default_fps": 120,
                        "ffmpeg_path": "/usr/bin/ffmpeg",
                    }
                )
                loaded = settings.load_settings()

        self.assertEqual(saved["theme"], "light")
        self.assertEqual(loaded["default_format"], "webm")
        self.assertEqual(loaded["default_resolution"], "1280:720")
        self.assertEqual(loaded["default_fps"], 60)
        self.assertEqual(loaded["ffmpeg_path"], "/usr/bin/ffmpeg")


if __name__ == "__main__":
    unittest.main()

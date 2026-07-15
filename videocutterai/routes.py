"""HTTP routes for the local VideoCutterAI app."""

from __future__ import annotations

import html
import json
import logging
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

from config import APP_VERSION, STATIC_DIR, TEMPLATE_DIR, WORK_DIR
from renderer import render_video
from settings import load_settings, save_settings
from upload import parse_upload
from utils import content_type


logger = logging.getLogger(__name__)


@dataclass
class JobState:
    status: str = "queued"
    progress: int = 0
    message: str = "Wartet"
    filename: str | None = None
    path: str | None = None
    error: str | None = None
    started_at: float | None = None
    finished_at: float | None = None


JOBS: dict[str, JobState] = {}
JOBS_LOCK = threading.Lock()


def set_job(job_id: str, **changes: object) -> None:
    with JOBS_LOCK:
        state = JOBS.setdefault(job_id, JobState())
        for key, value in changes.items():
            setattr(state, key, value)


def get_job(job_id: str) -> JobState | None:
    with JOBS_LOCK:
        return JOBS.get(job_id)


def run_render(upload_result) -> None:
    def progress(percent: int, message: str) -> None:
        set_job(upload_result.job_id, status="running", progress=percent, message=message)

    try:
        logger.info("Renderjob startet: %s", upload_result.job_id)
        set_job(upload_result.job_id, status="running", progress=1, message="Upload verarbeitet", started_at=time.time())
        render_video(
            upload_result.images,
            upload_result.audio,
            upload_result.output,
            upload_result.settings,
            progress,
        )
        set_job(
            upload_result.job_id,
            status="done",
            progress=100,
            message="Fertig",
            filename=upload_result.output.name,
            path=str(upload_result.output),
            finished_at=time.time(),
        )
        logger.info("Renderjob fertig: %s", upload_result.job_id)
    except Exception as error:  # noqa: BLE001 - local app should show useful render errors.
        logger.exception("Renderjob fehlgeschlagen: %s", upload_result.job_id)
        set_job(upload_result.job_id, status="error", message=str(error), error=str(error), finished_at=time.time())


class VideoCutterHandler(BaseHTTPRequestHandler):
    server_version = "VideoCutterAI/0.2"

    def do_GET(self) -> None:
        self.route_request(head_only=False)

    def do_HEAD(self) -> None:
        self.route_request(head_only=True)

    def route_request(self, head_only: bool) -> None:
        if self.path in {"/", "/index.html"}:
            self.send_file(TEMPLATE_DIR / "index.html", base_dir=TEMPLATE_DIR, head_only=head_only)
            return
        if self.path.startswith("/static/"):
            relative = unquote(self.path.removeprefix("/static/"))
            self.send_file(STATIC_DIR / relative, base_dir=STATIC_DIR, head_only=head_only)
            return
        if self.path.startswith("/api/status/"):
            if head_only:
                self.send_error(405)
                return
            self.send_status(unquote(self.path.removeprefix("/api/status/")))
            return
        if self.path == "/api/settings":
            if head_only:
                self.send_error(405)
                return
            self.send_settings()
            return
        if self.path.startswith("/download/"):
            self.send_download(unquote(self.path.removeprefix("/download/")), head_only=head_only)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/api/settings":
            self.save_settings()
            return
        if self.path != "/api/render":
            self.send_error(404)
            return
        try:
            upload_result = parse_upload(self)
            set_job(upload_result.job_id, status="queued", progress=0, message="Renderjob angelegt")
            thread = threading.Thread(target=run_render, args=(upload_result,), daemon=True)
            thread.start()
            self.send_json({"ok": True, "job_id": upload_result.job_id})
        except Exception as error:  # noqa: BLE001 - show useful local-app errors.
            logger.exception("Upload konnte nicht verarbeitet werden")
            self.send_json({"ok": False, "error": str(error)}, status=400)

    def send_status(self, job_id: str) -> None:
        state = get_job(Path(job_id).name)
        if state is None:
            self.send_json({"ok": False, "error": "Job nicht gefunden."}, status=404)
            return
        elapsed_seconds = None
        if state.started_at is not None:
            finished_at = state.finished_at if state.finished_at is not None else time.time()
            elapsed_seconds = round(max(0, finished_at - state.started_at), 1)
        self.send_json(
            {
                "ok": True,
                "status": state.status,
                "progress": state.progress,
                "message": state.message,
                "error": state.error,
                "download": f"/download/{Path(job_id).name}" if state.status == "done" else None,
                "filename": state.filename,
                "path": state.path,
                "elapsed_seconds": elapsed_seconds,
            }
        )

    def send_settings(self) -> None:
        self.send_json({"ok": True, "settings": load_settings(), "version": APP_VERSION})

    def save_settings(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length > 64 * 1024:
                raise RuntimeError("Einstellungen sind zu groß.")
            payload = self.rfile.read(length).decode("utf-8") if length else "{}"
            data = json.loads(payload)
            if not isinstance(data, dict):
                raise RuntimeError("Ungültige Einstellungen.")
            self.send_json({"ok": True, "settings": save_settings(data)})
        except Exception as error:  # noqa: BLE001 - local app should show useful settings errors.
            logger.exception("Einstellungen konnten nicht gespeichert werden")
            self.send_json({"ok": False, "error": str(error)}, status=400)

    def send_file(self, path: Path, base_dir: Path, head_only: bool = False) -> None:
        resolved = path.resolve()
        base = base_dir.resolve()
        if not resolved.is_file() or (resolved != base and base not in resolved.parents):
            self.send_error(404)
            return
        content = resolved.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type(resolved))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if not head_only:
            self.wfile.write(content)

    def send_download(self, job_id: str, head_only: bool = False) -> None:
        job_dir = WORK_DIR / Path(job_id).name
        matches = [path for path in job_dir.glob("video.*") if path.is_file()]
        if not matches:
            self.send_error(404)
            return
        path = matches[0]
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type(path))
        self.send_header("Content-Disposition", f'attachment; filename="{html.escape(path.name)}"')
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        if not head_only:
            self.wfile.write(content)

    def send_json(self, data: dict, status: int = 200) -> None:
        content = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: object) -> None:
        logger.info("%s - %s", self.address_string(), format % args)

#!/usr/bin/env python3
"""Start the local VideoCutterAI web app."""

from __future__ import annotations

import argparse
import logging
import threading
import warnings
import webbrowser
from http.server import ThreadingHTTPServer

warnings.simplefilter("ignore", DeprecationWarning)

from config import APP_NAME, APP_VERSION, DEFAULT_HOST, DEFAULT_PORT, WORK_DIR
from logging_setup import setup_logging
from routes import VideoCutterHandler


logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog=APP_NAME, description="VideoCutterAI lokale Linux-App")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")
    args = parser.parse_args()

    setup_logging(debug=args.debug)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), VideoCutterHandler)
    url = f"http://{args.host}:{args.port}"
    logger.info("%s %s gestartet: %s", APP_NAME, APP_VERSION, url)
    print(f"{APP_NAME} laeuft: {url}")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("%s wird beendet", APP_NAME)
        print(f"\n{APP_NAME} beendet.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

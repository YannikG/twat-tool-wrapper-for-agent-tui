"""Localhost HTTP listener for twat-hook events (Qt-free).

Stdlib `http.server` in a background thread, 127.0.0.1-only, auto-allocated
ephemeral port, per-session token validated on each POST. Events are handed to
the `on_event` callback on the listener thread (the UI side marshals to the Qt
main thread). See ADR-0002.
"""

from __future__ import annotations

import contextlib
import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

Event = dict[str, object]
EventHandler = Callable[[Event], None]
StatusProvider = Callable[[str], dict[str, object] | None]


class HookListener:
    """A localhost-only HTTP listener receiving twat-hook events."""

    def __init__(
        self,
        *,
        token: str,
        on_event: EventHandler,
        on_status: StatusProvider | None = None,
    ) -> None:
        self._token = token
        self._on_event = on_event
        self._on_status = on_status
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._port = 0

    @property
    def port(self) -> int:
        return self._port

    def start(self) -> None:
        if self._server is not None:
            return
        token = self._token
        on_event = self._on_event
        on_status = self._on_status

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args: object) -> None:
                pass  # silence stderr

            def _check_token(self) -> bool:
                if self.headers.get("X-Twat-Token") != token:
                    self.send_response(401)
                    self.end_headers()
                    return False
                return True

            def do_GET(self) -> None:
                # /status?sessionId=<id> -> session state JSON (read-only).
                if not self._check_token():
                    return
                if on_status is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                from urllib.parse import parse_qs, urlparse

                parsed = urlparse(self.path)
                if parsed.path != "/status":
                    self.send_response(404)
                    self.end_headers()
                    return
                sid = parse_qs(parsed.query).get("sessionId", [None])[0]
                if not sid:
                    self.send_response(400)
                    self.end_headers()
                    return
                info = on_status(str(sid))
                if info is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                body = json.dumps(info).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:
                if not self._check_token():
                    return
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw = self.rfile.read(length) if length else b""
                try:
                    event = json.loads(raw.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    self.send_response(400)
                    self.end_headers()
                    return
                if not isinstance(event, dict):
                    self.send_response(400)
                    self.end_headers()
                    return
                with contextlib.suppress(Exception):
                    on_event(event)  # never let a handler error kill the response
                self.send_response(200)
                self.end_headers()

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._port = self._server.server_address[1]
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="twat-hook-listener", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._port = 0

"""Hook integration: owns the listener, routes events to the service (Qt-free).

One listener per app (auto-allocated port, single token). Each pi child gets
the port + token + its session id via env. Events are routed to the service by
session id. The UI marshals updates to the Qt main thread (slice wiring below).
"""

from __future__ import annotations

import logging
import secrets

from twat.app.service import AppService
from twat.hook.listener import HookListener
from twat.hook.router import route_event

_log = logging.getLogger("twat.hook")


class HookIntegration:
    """Owns the localhost listener and routes events to the service."""

    def __init__(self, service: AppService, *, on_event: object | None = None) -> None:
        self._service = service
        self._on_event = on_event  # optional UI callback (marshalled by caller)
        self._token = secrets.token_hex(16)
        self._listener = HookListener(token=self._token, on_event=self._handle)

    @property
    def port(self) -> int:
        return self._listener.port

    @property
    def token(self) -> str:
        return self._token

    def start(self) -> None:
        self._listener.start()
        _log.info("hook listener started on port %s", self.port)

    def stop(self) -> None:
        _log.info("hook listener stopping")
        self._listener.stop()

    def env_for(self, session_id: str) -> dict[str, str]:
        """Env vars to inject into a pi child so its hook can call back."""
        return {
            "TWAT_HOOK_PORT": str(self.port),
            "TWAT_HOOK_TOKEN": self._token,
            "TWAT_SESSION_ID": session_id,
        }

    def _handle(self, event: dict[str, object]) -> None:
        _log.info("hook event received: %s", {k: event.get(k) for k in ("type", "sessionId")})
        try:
            route_event(self._service, event)
        except Exception:
            _log.exception("hook event routing failed")
        if self._on_event is not None:
            # mypy: on_event is loosely typed to avoid importing Qt here
            self._on_event(event)  # type: ignore[operator]

"""Process adapter port: how the app launches/stops pi sessions.

Qt-free. A protocol (structural type) — no concrete base class needed. The real
implementation wraps the terminal PTY; tests inject a fake. No second real
implementation exists yet, so this stays a Protocol only because tests need a
fake (architecture guardrail: an interface is allowed when a test fake needs it).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProcessAdapter(Protocol):
    """Launch and control the pi process for a session."""

    def start(self, session_id: str, cwd: str, resume_file: str | None) -> None:
        """Start pi in `cwd`; if resume_file is set, resume that pi Session file."""
        ...

    def stop(self, session_id: str) -> None:
        """Graceful stop (SIGTERM / shutdown)."""
        ...

    def terminate(self, session_id: str) -> None:
        """Hard kill (SIGKILL / TerminateProcess)."""
        ...

    def is_alive(self, session_id: str) -> bool:
        """Whether the session's pi process is still running."""
        ...

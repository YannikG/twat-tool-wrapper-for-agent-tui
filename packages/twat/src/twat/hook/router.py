"""Route hook events to AppService seams (Qt-free).

Maps the JSON events posted by twat-hook.ts to service methods. Unknown event
types and unknown session ids are ignored.
"""

from __future__ import annotations

from typing import Protocol

from twat.core.session import SessionState


class _ServiceLike(Protocol):
    def get_session(self, session_id: str) -> object: ...
    def _set_session_bound_file(self, session_id: str, path: str) -> None: ...
    def _set_session_name(self, session_id: str, name: str) -> None: ...
    def _set_session_agent_activity(self, session_id: str, activity: str) -> None: ...
    def mark_session_exited(self, session_id: str) -> None: ...


def route_event(service: _ServiceLike, event: dict[str, object]) -> None:
    event_type = event.get("type")
    session_id = event.get("sessionId")
    if not isinstance(session_id, str):
        return
    try:
        service.get_session(session_id)
    except KeyError:
        return

    if event_type == "session_start":
        session_file = event.get("sessionFile")
        name = event.get("name")
        if isinstance(session_file, str):
            service._set_session_bound_file(session_id, session_file)
        if isinstance(name, str) and name:
            service._set_session_name(session_id, name)
    elif event_type == "agent_activity":
        activity = event.get("activity")
        if isinstance(activity, str) and activity in ("idle", "working"):
            service._set_session_agent_activity(session_id, activity)
    elif event_type == "name":
        name = event.get("name")
        if isinstance(name, str) and name:
            service._set_session_name(session_id, name)
    elif event_type == "session_shutdown":
        # pi ended. Mark exited idempotently WITHOUT killing the PTY (the reader's
        # `finished` signal is authoritative for terminal teardown). Avoids racing
        # the reader and SIGKILLing a still-draining process.
        service.mark_session_exited(session_id)


# re-export for type-checking convenience
__all__ = ["SessionState", "route_event"]

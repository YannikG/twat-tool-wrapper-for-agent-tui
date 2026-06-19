"""Qt-free tests for routing hook events to the AppService seams."""

from pathlib import Path

from twat.app.service import AppService
from twat.core.session import SessionState
from twat.core.store import StateStore
from twat.hook.router import route_event


def _service(tmp_path: Path) -> AppService:
    return AppService(StateStore(tmp_path / "state.json"))


def test_session_start_sets_binding_and_name(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    proj = svc.add_project("/p/proj")
    s = svc.new_session(proj.id)

    route_event(
        svc,
        {
            "type": "session_start",
            "sessionId": s.id,
            "sessionFile": "/x/abc.jsonl",
            "name": "My Sess",
        },
    )

    got = svc.get_session(s.id)
    assert got.bound_file == "/x/abc.jsonl"
    assert got.name == "My Sess"


def test_agent_activity_working_then_idle(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    proj = svc.add_project("/p/proj")
    s = svc.new_session(proj.id)

    route_event(svc, {"type": "agent_activity", "sessionId": s.id, "activity": "working"})
    assert svc.get_session(s.id).agent_activity == "working"

    route_event(svc, {"type": "agent_activity", "sessionId": s.id, "activity": "idle"})
    assert svc.get_session(s.id).agent_activity == "idle"


def test_name_event_updates_name(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    proj = svc.add_project("/p/proj")
    s = svc.new_session(proj.id)

    route_event(svc, {"type": "name", "sessionId": s.id, "name": "Renamed"})

    assert svc.get_session(s.id).name == "Renamed"


def test_session_shutdown_marks_exited(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    proj = svc.add_project("/p/proj")
    s = svc.new_session(proj.id)
    svc.start_session(s.id)  # requires an adapter; use a fake

    class _Fake:
        def start(self, *a: object) -> None:
            pass

        def stop(self, *a: object) -> None:
            pass

        def terminate(self, *a: object) -> None:
            pass

        def is_alive(self, *a: object) -> bool:
            return False

    svc.process_adapter = _Fake()  # type: ignore[assignment]
    svc.start_session(s.id)
    assert svc.get_session(s.id).state is SessionState.RUNNING

    route_event(svc, {"type": "session_shutdown", "sessionId": s.id})

    assert svc.get_session(s.id).state is SessionState.EXITED


def test_unknown_event_type_is_ignored(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    # must not raise
    route_event(svc, {"type": "whatever", "sessionId": "nope"})


def test_unknown_session_id_is_ignored(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    route_event(svc, {"type": "name", "sessionId": "nope", "name": "x"})

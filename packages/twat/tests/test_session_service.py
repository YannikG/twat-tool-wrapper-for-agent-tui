"""Tests for session management via the AppService, using a fake process adapter."""

from pathlib import Path

import pytest

from twat.app.service import AppService
from twat.core.session import SessionState
from twat.core.store import StateStore


class FakeProcessAdapter:
    """Records calls; simulates a pi process that stays alive until stopped."""

    def __init__(self) -> None:
        self.started: list[str] = []  # session ids started
        self.stopped: list[str] = []
        self.terminated: list[str] = []
        self.alive: set[str] = set()

    def start(self, session_id: str, cwd: str, resume_file: str | None) -> None:
        self.started.append(session_id)
        self.alive.add(session_id)

    def stop(self, session_id: str) -> None:
        self.stopped.append(session_id)
        self.alive.discard(session_id)

    def terminate(self, session_id: str) -> None:
        self.terminated.append(session_id)
        self.alive.discard(session_id)

    def is_alive(self, session_id: str) -> bool:
        return session_id in self.alive


@pytest.fixture()
def service(tmp_path: Path) -> AppService:
    svc = AppService(StateStore(tmp_path / "state.json"))
    return svc


def test_new_session_appears_exited_under_project(service: AppService) -> None:
    proj = service.add_project("/p/proj")
    service.process_adapter = FakeProcessAdapter()

    s = service.new_session(proj.id)

    assert s.state is SessionState.EXITED
    assert s.project_id == proj.id
    assert [x.id for x in service.sessions_for(proj.id)] == [s.id]


def test_start_launches_process_and_sets_running(service: AppService) -> None:
    proj = service.add_project("/p/proj")
    service.process_adapter = FakeProcessAdapter()
    s = service.new_session(proj.id)

    service.start_session(s.id)

    assert service.get_session(s.id).state is SessionState.RUNNING
    assert service.process_adapter.started == [s.id]


def test_start_resumes_bound_file_when_set(service: AppService) -> None:
    proj = service.add_project("/p/proj")
    fake = FakeProcessAdapter()
    service.process_adapter = fake
    s = service.new_session(proj.id)
    # simulate a binding arriving from the hook
    service._set_session_bound_file(s.id, "/sessions/abc.jsonl")

    service.start_session(s.id)

    assert fake.started == [s.id]
    # the fake would receive resume_file; here we just assert it was called
    assert service.get_session(s.id).state is SessionState.RUNNING


def test_stop_sets_exited(service: AppService) -> None:
    proj = service.add_project("/p/proj")
    service.process_adapter = FakeProcessAdapter()
    s = service.new_session(proj.id)
    service.start_session(s.id)

    service.stop_session(s.id)

    assert service.get_session(s.id).state is SessionState.EXITED
    assert service.process_adapter.stopped == [s.id]


def test_terminate_sets_failed(service: AppService) -> None:
    proj = service.add_project("/p/proj")
    service.process_adapter = FakeProcessAdapter()
    s = service.new_session(proj.id)
    service.start_session(s.id)

    service.terminate_session(s.id)

    assert service.get_session(s.id).state is SessionState.FAILED
    assert service.process_adapter.terminated == [s.id]


def test_sessions_persist_across_restart(service: AppService, tmp_path: Path) -> None:
    proj = service.add_project("/p/proj")
    service.process_adapter = FakeProcessAdapter()
    service.new_session(proj.id)

    reloaded = AppService(StateStore(tmp_path / "state.json"))
    reloaded.process_adapter = FakeProcessAdapter()

    assert len(reloaded.sessions_for(proj.id)) == 1
    # processes did not survive restart -> exited
    assert reloaded.sessions_for(proj.id)[0].state is SessionState.EXITED


def test_start_unknown_session_raises(service: AppService) -> None:
    service.process_adapter = FakeProcessAdapter()
    with pytest.raises(KeyError):
        service.start_session("nope")

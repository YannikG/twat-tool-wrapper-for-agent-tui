"""Tests for the application service (orchestrates store + core, Qt-free)."""

from pathlib import Path

import pytest

from twat.app.service import AppService, SessionActiveError
from twat.core.project import ProjectExistsError
from twat.core.session import SessionState
from twat.core.settings import Theme
from twat.core.store import StateStore


class FakeProcessAdapter:
    """Records calls; simulates a pi process that stays alive until stopped."""

    def __init__(self) -> None:
        self.started: list[str] = []
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
    return AppService(StateStore(tmp_path / "state.json"))


def test_add_project_persists_and_appears(tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))

    proj = svc.add_project(tmp_path / "proj", name="Proj")

    assert proj.name == "Proj"
    assert [p.name for p in svc.projects] == ["Proj"]

    # a fresh service loading the same store sees the project
    reloaded = AppService(StateStore(tmp_path / "state.json"))
    assert [p.name for p in reloaded.projects] == ["Proj"]


def test_add_project_defaults_name_to_basename(tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))

    svc.add_project(tmp_path / "alpha")

    assert svc.projects[0].name == "alpha"


def test_add_project_rejects_duplicate_path(tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))
    folder = tmp_path / "dup"
    svc.add_project(folder)

    with pytest.raises(ProjectExistsError):
        svc.add_project(folder)


def test_add_project_rejects_duplicate_resolved_path(tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))
    folder = tmp_path / "dup"
    svc.add_project(folder)

    # same folder via a relative-ish alias still resolves to the same path
    with pytest.raises(ProjectExistsError):
        svc.add_project(str(folder) + "/.")


def test_set_theme_persists(tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))

    svc.set_theme(Theme.LIGHT)

    assert svc.settings.theme is Theme.LIGHT
    assert AppService(StateStore(tmp_path / "state.json")).settings.theme is Theme.LIGHT


def test_set_pi_path_persists(tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))

    svc.set_pi_path("/some/pi")

    assert svc.settings.pi_path == "/some/pi"
    assert AppService(StateStore(tmp_path / "state.json")).settings.pi_path == "/some/pi"


def test_initial_pi_path_prefilled_from_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("twat.app.service.discover_pi", lambda: "/discovered/pi")

    svc = AppService(StateStore(tmp_path / "state.json"))

    assert svc.settings.pi_path == "/discovered/pi"


def test_initial_pi_path_not_overwritten_if_already_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # first launch discovers and saves
    monkeypatch.setattr("twat.app.service.discover_pi", lambda: "/discovered/pi")
    AppService(StateStore(tmp_path / "state.json")).set_theme(Theme.DARK)  # forces a save
    # second launch: discovery returns something else, but saved value must win
    monkeypatch.setattr("twat.app.service.discover_pi", lambda: "/other/pi")

    svc = AppService(StateStore(tmp_path / "state.json"))

    assert svc.settings.pi_path == "/discovered/pi"


# -- delete session / delete project -----------------------------------------


def test_delete_session_removes_record(service: AppService) -> None:
    proj = service.add_project("/p/proj")
    service.process_adapter = FakeProcessAdapter()
    s = service.new_session(proj.id)
    service.archive_session(s.id)

    service.delete_session(s.id)

    with pytest.raises(KeyError):
        service.get_session(s.id)
    assert s.id not in [x.id for x in service.sessions_for(proj.id)]


def test_delete_session_refuses_running(service: AppService) -> None:
    proj = service.add_project("/p/proj")
    service.process_adapter = FakeProcessAdapter()
    s = service.new_session(proj.id)
    service.start_session(s.id)

    with pytest.raises(SessionActiveError):
        service.delete_session(s.id)

    # not removed
    assert service.get_session(s.id).state is SessionState.RUNNING


def test_delete_session_persists(service: AppService, tmp_path: Path) -> None:
    proj = service.add_project("/p/proj")
    service.process_adapter = FakeProcessAdapter()
    s = service.new_session(proj.id)
    service.archive_session(s.id)
    service.delete_session(s.id)

    reloaded = AppService(StateStore(tmp_path / "state.json"))
    with pytest.raises(KeyError):
        reloaded.get_session(s.id)


def test_delete_session_does_not_touch_bound_file_metadata_of_others(
    service: AppService,
) -> None:
    proj = service.add_project("/p/proj")
    service.process_adapter = FakeProcessAdapter()
    keep = service.new_session(proj.id)
    service._set_session_bound_file(keep.id, "/sessions/keep.jsonl")
    gone = service.new_session(proj.id)
    service.archive_session(gone.id)

    service.delete_session(gone.id)

    assert service.get_session(keep.id).bound_file == "/sessions/keep.jsonl"


def test_delete_project_removes_project_and_sessions(service: AppService) -> None:
    proj = service.add_project("/p/proj")
    service.process_adapter = FakeProcessAdapter()
    service.new_session(proj.id)
    service.new_session(proj.id)

    service.delete_project(proj.id)

    assert proj.id not in [p.id for p in service.projects]
    assert service.sessions_for(proj.id) == []


def test_delete_project_stops_running_sessions_first(service: AppService) -> None:
    proj = service.add_project("/p/proj")
    fake = FakeProcessAdapter()
    service.process_adapter = fake
    s = service.new_session(proj.id)
    service.start_session(s.id)

    service.delete_project(proj.id)

    assert fake.stopped == [s.id]
    assert proj.id not in [p.id for p in service.projects]


def test_delete_project_persists(service: AppService, tmp_path: Path) -> None:
    proj = service.add_project("/p/proj")
    service.process_adapter = FakeProcessAdapter()
    service.new_session(proj.id)
    service.delete_project(proj.id)

    reloaded = AppService(StateStore(tmp_path / "state.json"))
    assert proj.id not in [p.id for p in reloaded.projects]


def test_delete_project_unknown_raises(service: AppService) -> None:
    with pytest.raises(KeyError):
        service.delete_project("nope")


def test_delete_project_leaves_other_projects(service: AppService) -> None:
    keep = service.add_project("/p/keep")
    gone = service.add_project("/p/gone")
    service.delete_project(gone.id)

    assert [p.id for p in service.projects] == [keep.id]

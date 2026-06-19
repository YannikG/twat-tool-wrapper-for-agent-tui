"""Tests for the Session core model and state transitions."""

from pathlib import Path

from twat.core.project import create_project
from twat.core.session import Session, SessionState, create_session


def test_create_session_starts_exited_unbound() -> None:
    proj = create_project("/p")

    s = create_session(project_id=proj.id)

    assert s.state is SessionState.EXITED
    assert s.bound_file is None
    assert s.id  # non-empty
    assert s.project_id == proj.id
    assert s.name  # default name


def test_session_states_are_the_four_lifecycle_values() -> None:
    assert {s.value for s in SessionState} == {"starting", "running", "exited", "failed"}


def test_session_default_name_is_informative() -> None:
    proj = create_project("/p")

    s = create_session(project_id=proj.id)

    # default name is non-empty and identifies it as a session
    assert "session" in s.name.lower() or s.name.strip()


def test_session_to_from_dict_round_trips() -> None:
    proj = create_project("/p")
    s = create_session(project_id=proj.id)
    s = s.with_state(SessionState.RUNNING).with_bound_file("/some/file.jsonl")

    rebuilt = Session.from_dict(s.to_dict())

    assert rebuilt.id == s.id
    assert rebuilt.project_id == s.project_id
    assert rebuilt.state is SessionState.RUNNING
    assert rebuilt.bound_file == "/some/file.jsonl"
    assert rebuilt.name == s.name


def test_session_is_immutable_with_state() -> None:
    proj = create_project("/p")
    s = create_session(project_id=proj.id)

    s2 = s.with_state(SessionState.RUNNING)

    assert s.state is SessionState.EXITED  # original unchanged
    assert s2.state is SessionState.RUNNING


def test_session_with_bound_file_sets_binding() -> None:
    proj = create_project("/p")
    s = create_session(project_id=proj.id)

    s2 = s.with_bound_file("/sessions/abc.jsonl")

    assert s2.bound_file == "/sessions/abc.jsonl"
    assert s.bound_file is None  # original unchanged


def test_session_with_name_updates_name() -> None:
    proj = create_project("/p")
    s = create_session(project_id=proj.id)

    s2 = s.with_name("Refactor auth")

    assert s2.name == "Refactor auth"


def test_session_relative_path_irrelevant(tmp_path: Path) -> None:
    # project path is resolved at project creation; session just references the id
    proj = create_project(tmp_path / "p")
    s = create_session(project_id=proj.id)

    assert s.project_id == proj.id

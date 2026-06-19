"""Tests for the application service (orchestrates store + core, Qt-free)."""

from pathlib import Path

import pytest

from twat.app.service import AppService
from twat.core.project import ProjectExistsError
from twat.core.settings import Theme
from twat.core.store import StateStore


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

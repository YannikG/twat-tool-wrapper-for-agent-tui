"""Tests for Settings and the JSON state store."""

from pathlib import Path

from twat.core.project import Project, create_project
from twat.core.settings import Settings, Theme
from twat.core.store import State, StateStore


def test_default_settings_are_dark_with_empty_pi_path() -> None:
    s = Settings()

    assert s.theme is Theme.DARK
    assert s.pi_path == ""


def test_store_round_trips_projects_and_settings(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    state = State(
        projects=[create_project("/home/me/a", "Alpha")],
        settings=Settings(theme=Theme.LIGHT, pi_path="/usr/local/bin/pi"),
    )

    store.save(state)
    loaded = store.load()

    assert loaded.settings.theme is Theme.LIGHT
    assert loaded.settings.pi_path == "/usr/local/bin/pi"
    assert len(loaded.projects) == 1
    assert loaded.projects[0].name == "Alpha"
    assert loaded.projects[0].path == str(Path("/home/me/a").resolve())


def test_store_missing_file_returns_empty_state(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "absent.json")

    loaded = store.load()

    assert loaded.projects == []
    assert loaded.settings == Settings()


def test_store_corrupt_file_recovers_to_empty_state(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{ not valid json", encoding="utf-8")

    loaded = StateStore(path).load()

    assert loaded.projects == []


def test_store_atomic_write_leaves_no_temp_behind(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    StateStore(path).save(State())

    assert path.exists()
    # only the final file should exist, no .tmp leftover
    assert list(tmp_path.glob("*.tmp")) == []


def test_state_serializes_project_with_custom_name(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.save(State(projects=[Project(id="x", path="/p", name="Custom & Co")]))

    loaded = store.load()

    assert loaded.projects[0].name == "Custom & Co"

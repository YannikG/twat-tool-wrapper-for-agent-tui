"""pytest-qt tests for the main window shell."""

from pathlib import Path

from twat.app.service import AppService
from twat.core.store import StateStore
from twat.ui.main_window import MainWindow


def test_empty_state_shows_hint(qtbot, tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))
    win = MainWindow(svc)
    qtbot.addWidget(win)

    assert win.project_names() == []
    # the placeholder invites the user to add a project
    assert "project" in win.panel_subtitle().lower()


def test_add_project_appears_in_sidebar_and_panel(qtbot, tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))
    win = MainWindow(svc)
    qtbot.addWidget(win)

    proj = svc.add_project(tmp_path / "proj", name="MyProj")
    win.refresh_projects()

    assert win.project_names() == ["MyProj"]

    win.select_project(proj.id)

    assert win.panel_title() == "MyProj"
    assert str(Path(tmp_path / "proj").resolve()) in win.panel_subtitle()


def test_selecting_unselected_makes_context_visible(qtbot, tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))
    win = MainWindow(svc)
    qtbot.addWidget(win)

    a = svc.add_project(tmp_path / "alpha", name="Alpha")
    b = svc.add_project(tmp_path / "beta", name="Beta")
    win.refresh_projects()

    win.select_project(b.id)

    assert win.panel_title() == "Beta"
    # alpha is present but not the selected one
    assert "Alpha" in win.project_names()
    assert win.panel_title() != "Alpha"
    assert a.id != b.id
    # the OS window title carries the selected project context (wrong-window safeguard)
    assert "Beta" in win.windowTitle()
    assert "Alpha" not in win.windowTitle()


def test_no_selection_window_title_is_app_title(qtbot, tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))
    win = MainWindow(svc)
    qtbot.addWidget(win)

    assert win.panel_title() == "TWAT"
    assert win.windowTitle() == "TWAT — Tool Wrapper for Agent TUIs"

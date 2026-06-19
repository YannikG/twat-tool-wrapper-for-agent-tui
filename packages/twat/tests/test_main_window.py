"""pytest-qt tests for the main window shell (styled tree, no tabs)."""

from pathlib import Path

from twat.app.service import AppService
from twat.core.store import StateStore
from twat.ui.main_window import MainWindow


def _service(tmp_path: Path) -> AppService:
    return AppService(StateStore(tmp_path / "state.json"))


def test_empty_state_shows_hint(qtbot, tmp_path: Path) -> None:
    win = MainWindow(_service(tmp_path))
    qtbot.addWidget(win)

    assert win.project_names() == []
    assert win.windowTitle().startswith("TWAT")


def test_add_project_appears_in_sidebar(qtbot, tmp_path: Path) -> None:
    svc = _service(tmp_path)
    win = MainWindow(svc)
    qtbot.addWidget(win)

    svc.add_project(tmp_path / "proj", name="MyProj")
    win._refresh_tree()

    assert win.project_names() == ["MyProj"]


def test_new_session_appears_as_child_of_project(qtbot, tmp_path: Path) -> None:
    svc = _service(tmp_path)
    win = MainWindow(svc)
    qtbot.addWidget(win)
    proj = svc.add_project(tmp_path / "proj", name="Proj")
    win._refresh_tree()
    win.select_project(proj.id)

    svc.new_session(proj.id, name="Auth")
    win._refresh_tree()

    labels = win.session_labels_for(proj.id)
    assert any("Auth" in lbl for lbl in labels)


def test_window_title_reflects_selected_session_and_project(qtbot, tmp_path: Path) -> None:
    svc = _service(tmp_path)
    win = MainWindow(svc)
    qtbot.addWidget(win)
    proj = svc.add_project(tmp_path / "proj", name="Proj")
    win._refresh_tree()
    win.select_project(proj.id)
    sess = svc.new_session(proj.id, name="Auth refactor")
    win._refresh_tree()
    win.select_session(sess.id)

    title = win.windowTitle()
    assert "Auth refactor" in title
    assert "Proj" in title


def test_project_title_when_no_session_selected(qtbot, tmp_path: Path) -> None:
    svc = _service(tmp_path)
    win = MainWindow(svc)
    qtbot.addWidget(win)
    proj = svc.add_project(tmp_path / "proj", name="Solo")
    win._refresh_tree()
    win.select_project(proj.id)

    assert "Solo" in win.windowTitle()

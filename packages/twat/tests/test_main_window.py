"""pytest-qt tests for the main window shell (styled tree, no tabs)."""

from pathlib import Path

from twat.app.service import AppService
from twat.core.store import StateStore
from twat.ui.main_window import MainWindow
from twat.ui.open_in import open_in_targets


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


# -- archive / restore -------------------------------------------------------


def test_archived_session_moves_to_archive_node(qtbot, tmp_path: Path) -> None:
    svc = _service(tmp_path)
    win = MainWindow(svc)
    qtbot.addWidget(win)
    proj = svc.add_project(tmp_path / "proj", name="Proj")
    sess = svc.new_session(proj.id, name="Done")
    win._refresh_tree()

    svc.archive_session(sess.id)
    win._refresh_tree()

    # gone from the project's active list...
    assert not any("Done" in lbl for lbl in win.session_labels_for(proj.id))
    # ...but present under the Archive node
    assert any("Done" in lbl for lbl in win.archive_labels())


def test_restore_moves_session_back_to_project(qtbot, tmp_path: Path) -> None:
    svc = _service(tmp_path)
    win = MainWindow(svc)
    qtbot.addWidget(win)
    proj = svc.add_project(tmp_path / "proj", name="Proj")
    sess = svc.new_session(proj.id, name="Revive")
    svc.archive_session(sess.id)
    win._refresh_tree()

    svc.restore_session(sess.id)
    win._refresh_tree()

    assert any("Revive" in lbl for lbl in win.session_labels_for(proj.id))
    assert not any("Revive" in lbl for lbl in win.archive_labels())


def test_delete_archived_session_removes_it(qtbot, tmp_path: Path, monkeypatch) -> None:
    # confirm dialog auto-accepted so the test does not block
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    svc = _service(tmp_path)
    win = MainWindow(svc)
    qtbot.addWidget(win)
    proj = svc.add_project(tmp_path / "proj", name="Proj")
    sess = svc.new_session(proj.id, name="Goner")
    svc.archive_session(sess.id)
    win._refresh_tree()
    win.select_session(sess.id)

    win._on_delete_session()

    assert not any("Goner" in lbl for lbl in win.archive_labels())
    assert not any("Goner" in lbl for lbl in win.session_labels_for(proj.id))


def test_delete_session_cancel_keeps_it(qtbot, tmp_path: Path, monkeypatch) -> None:
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    svc = _service(tmp_path)
    win = MainWindow(svc)
    qtbot.addWidget(win)
    proj = svc.add_project(tmp_path / "proj", name="Proj")
    sess = svc.new_session(proj.id, name="Keep")
    svc.archive_session(sess.id)
    win._refresh_tree()
    win.select_session(sess.id)

    win._on_delete_session()

    assert any("Keep" in lbl for lbl in win.archive_labels())


def test_delete_project_removes_project_and_sessions(qtbot, tmp_path: Path, monkeypatch) -> None:
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    svc = _service(tmp_path)
    win = MainWindow(svc)
    qtbot.addWidget(win)
    proj = svc.add_project(tmp_path / "proj", name="ByeProj")
    svc.new_session(proj.id, name="S1")
    win._refresh_tree()
    win.select_project(proj.id)

    win._on_delete_project()

    assert "ByeProj" not in win.project_names()
    assert win.session_labels_for(proj.id) == []


def test_delete_project_cancel_keeps_it(qtbot, tmp_path: Path, monkeypatch) -> None:
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    svc = _service(tmp_path)
    win = MainWindow(svc)
    qtbot.addWidget(win)
    proj = svc.add_project(tmp_path / "proj", name="StayProj")
    win._refresh_tree()
    win.select_project(proj.id)

    win._on_delete_project()

    assert "StayProj" in win.project_names()


def test_archive_node_hidden_when_empty(qtbot, tmp_path: Path) -> None:
    svc = _service(tmp_path)
    win = MainWindow(svc)
    qtbot.addWidget(win)
    svc.add_project(tmp_path / "proj", name="Proj")
    win._refresh_tree()

    assert win.archive_labels() == []
    assert "Archive" not in win.project_names()


def test_session_context_menu_actions_are_state_aware(qtbot, tmp_path: Path) -> None:
    # A stopped archived session exposes Restore + Delete (no Archive).
    svc = _service(tmp_path)
    win = MainWindow(svc)
    qtbot.addWidget(win)
    proj = svc.add_project(tmp_path / "proj", name="Proj")
    sess = svc.new_session(proj.id, name="Arch")
    svc.archive_session(sess.id)
    win._refresh_tree()
    win.select_session(sess.id)

    actions = win.session_context_actions()
    assert "Restore" in actions
    assert "Delete" in actions
    assert "Archive" not in actions  # already archived
    assert "Start" not in actions  # archived -> Restore first, no Start


def test_project_context_menu_has_add_and_delete(qtbot, tmp_path: Path) -> None:
    svc = _service(tmp_path)
    win = MainWindow(svc)
    qtbot.addWidget(win)
    proj = svc.add_project(tmp_path / "proj", name="Proj")
    win._refresh_tree()
    win.select_project(proj.id)

    actions = win.project_context_actions()
    assert actions == ["Add Session", "Rename Project…", "Delete Project"]


def test_menubar_has_settings_entry(qtbot, tmp_path: Path) -> None:
    win = MainWindow(_service(tmp_path))
    qtbot.addWidget(win)

    labels: list[str] = []
    for action in win.menuBar().actions():
        labels.append(action.text())
        menu = action.menu()
        if menu is not None:
            for child in menu.actions():
                labels.append(child.text())
    # Settings moved out of the sidebar into a menu-bar entry.
    assert any("Settings" in lbl for lbl in labels)


def test_open_in_menu_lists_available_editors_and_finder(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    # No macOS app bundles, no CLI shims -> editors absent; Finder/Terminal
    # always present. (open_in detection lives in twat.ui.open_in.)
    import twat.ui.open_in as oi

    monkeypatch.setattr(oi, "_mac_app_available", lambda app: False)
    monkeypatch.setattr(oi.shutil, "which", lambda exe: None)
    monkeypatch.setattr(oi.sys, "platform", "darwin")
    win = MainWindow(_service(tmp_path))
    qtbot.addWidget(win)
    proj = win._service.add_project(tmp_path / "proj", name="Proj")
    win._refresh_tree()
    win.select_project(proj.id)

    labels = [t[0] for t in open_in_targets()]

    assert "VS Code" not in labels
    assert "WebStorm" not in labels
    assert "PyCharm" not in labels
    assert "Rider" not in labels
    # Finder/Terminal are always present on macOS.
    assert "Finder" in labels
    assert "Terminal" in labels

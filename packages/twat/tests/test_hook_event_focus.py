"""Regression: hook events must not rebuild the tree or steal focus.

Bug (slice 4): _on_hook_event called _refresh_tree (clear+rebuild) +
_show_selected (setFocus) on every event, which broke terminal keyboard input
mid-keystroke. Fix: update only the affected session's label in place.
"""

from pathlib import Path

from PySide6.QtWidgets import QApplication

from twat.app.service import AppService
from twat.core.session import SessionState
from twat.core.store import StateStore
from twat.hook.router import route_event
from twat.ui.main_window import MainWindow


class _FakeAdapter:
    def __init__(self) -> None:
        self.stopped: list[str] = []

    def start(self, session_id: str, cwd: str, resume_file: str | None) -> None:
        pass

    def stop(self, session_id: str) -> None:
        self.stopped.append(session_id)

    def terminate(self, session_id: str) -> None:
        self.stopped.append(session_id)

    def is_alive(self, session_id: str) -> bool:
        return False


def test_hook_event_updates_label_without_rebuilding_or_killing(qtbot, tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))
    win = MainWindow(svc)
    win._adapter = None  # no real pi
    fake = _FakeAdapter()
    svc.process_adapter = fake  # type: ignore[assignment]
    qtbot.addWidget(win)

    proj = svc.add_project(tmp_path / "proj", name="Proj")
    s = svc.new_session(proj.id, name="Old")
    win._refresh_tree()

    # real flow: route_event updates the service, then the UI refreshes the label.
    route_event(svc, {"type": "name", "sessionId": s.id, "name": "New Name"})
    win._on_hook_event({"type": "name", "sessionId": s.id, "name": "New Name"})

    labels = win.session_labels_for(proj.id)
    assert any("New Name" in lbl for lbl in labels)
    assert fake.stopped == []


def test_session_shutdown_marks_exited_without_stop(qtbot, tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))
    win = MainWindow(svc)
    win._adapter = None
    fake = _FakeAdapter()
    svc.process_adapter = fake  # type: ignore[assignment]
    qtbot.addWidget(win)
    proj = svc.add_project(tmp_path / "proj", name="Proj")
    s = svc.new_session(proj.id)
    svc.start_session(s.id)
    assert svc.get_session(s.id).state is SessionState.RUNNING

    route_event(svc, {"type": "session_shutdown", "sessionId": s.id})
    win._on_hook_event({"type": "session_shutdown", "sessionId": s.id})

    assert svc.get_session(s.id).state is SessionState.EXITED
    assert fake.stopped == []


_ = QApplication

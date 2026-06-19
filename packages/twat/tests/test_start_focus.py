"""Regression: Start must hand focus to the terminal, not the tree.

Bug: _session_action called _refresh_tree + _show_selected after Start, which
reclaimed focus for the tree and broke terminal keyboard input. Fix: after
Start, update the label in place and skip _show_selected (the terminal already
has focus via _focus_terminal's deferred grab).
"""

from pathlib import Path

from PySide6.QtWidgets import QApplication

from twat.app.service import AppService
from twat.core.store import StateStore
from twat.ui.main_window import MainWindow
from twat.ui.termqt_terminal import TermQtTerminal


class _FakeAdapter:
    def __init__(self) -> None:
        self.alive: set[str] = set()

    def start(self, session_id: str, cwd: str, resume_file: str | None) -> None:
        self.alive.add(session_id)

    def stop(self, session_id: str) -> None:
        self.alive.discard(session_id)

    def terminate(self, session_id: str) -> None:
        self.alive.discard(session_id)

    def is_alive(self, session_id: str) -> bool:
        return session_id in self.alive


def test_start_hands_focus_to_terminal(qtbot, tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))
    win = MainWindow(svc)
    win._adapter = None
    fake = _FakeAdapter()
    svc.process_adapter = fake  # type: ignore[assignment]
    qtbot.addWidget(win)
    win.show()

    proj = svc.add_project(tmp_path / "proj", name="Proj")
    win._refresh_tree()
    win.select_project(proj.id)
    sess = svc.new_session(proj.id)
    win._refresh_tree()
    win.select_session(sess.id)

    # simulate Start's terminal creation + focus handoff
    term = TermQtTerminal(parent=win._session_area)
    win._terminal_by_session[sess.id] = term
    win._terminal_host.addWidget(term)
    win._terminal_host.setCurrentWidget(term)
    win._focus_terminal(term)

    qtbot.wait(50)  # let the deferred singleShot focus grab run

    assert QApplication.focusWidget() is term


_ = QApplication

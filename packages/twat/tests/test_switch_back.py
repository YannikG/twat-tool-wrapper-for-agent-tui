"""Regression: switching back to a running session shows its terminal.

Bug: _clear_terminal_host nuked live terminals from the host, so reselecting a
running session left the placeholder visible. Fix: live terminals stay in the
host; only a reusable placeholder is swapped in/out.
"""

from pathlib import Path

from PySide6.QtWidgets import QApplication

from twat.app.service import AppService
from twat.core.store import StateStore
from twat.ui.main_window import MainWindow


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


def test_reselect_running_session_shows_its_terminal(qtbot, tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))
    svc.process_adapter = _FakeAdapter()
    win = MainWindow(svc)
    win._adapter = None  # avoid real pi launch; drive via service + fake
    qtbot.addWidget(win)

    proj = svc.add_project(tmp_path / "proj", name="Proj")
    win._refresh_tree()
    win.select_project(proj.id)

    a = svc.new_session(proj.id, name="A")
    b = svc.new_session(proj.id, name="B")
    win._refresh_tree()

    # fake "start": register a terminal widget for each (without real pi)
    from twat.ui.termqt_terminal import TermQtTerminal

    for s in (a, b):
        term = TermQtTerminal(parent=win._session_area)
        win._terminal_by_session[s.id] = term
        win._terminal_host.addWidget(term)

    # select A, then B, then A again — A's terminal must still be reachable
    win.select_session(a.id)
    assert win._terminal_host.currentWidget() is win._terminal_by_session[a.id]
    win.select_session(b.id)
    assert win._terminal_host.currentWidget() is win._terminal_by_session[b.id]
    win.select_session(a.id)
    assert win._terminal_host.currentWidget() is win._terminal_by_session[a.id]


_ = QApplication  # keep ref for pytest-qt offscreen

"""Tests for terminal key encoding and the widget (pytest-qt)."""

from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from twat.ui.terminal_widget import TerminalWidget, key_to_bytes


def _key(
    key_code: int, text: str = "", mods: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier
) -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, key_code, mods, text)


def test_key_to_bytes_printable() -> None:
    assert key_to_bytes(_key(Qt.Key.Key_A, "a")) == b"a"


def test_key_to_bytes_enter_is_cr() -> None:
    assert key_to_bytes(_key(Qt.Key.Key_Return, "\r")) == b"\r"


def test_key_to_bytes_backspace_is_del() -> None:
    assert key_to_bytes(_key(Qt.Key.Key_Backspace)) == b"\x7f"


def test_key_to_bytes_arrows() -> None:
    assert key_to_bytes(_key(Qt.Key.Key_Up)) == b"\x1b[A"
    assert key_to_bytes(_key(Qt.Key.Key_Down)) == b"\x1b[B"
    assert key_to_bytes(_key(Qt.Key.Key_Right)) == b"\x1b[C"
    assert key_to_bytes(_key(Qt.Key.Key_Left)) == b"\x1b[D"


def test_key_to_bytes_ctrl_c() -> None:
    assert key_to_bytes(_key(Qt.Key.Key_C, "c", Qt.KeyboardModifier.ControlModifier)) == b"\x03"


def test_key_to_bytes_alt_prefixes_escape() -> None:
    assert key_to_bytes(_key(Qt.Key.Key_A, "a", Qt.KeyboardModifier.AltModifier)) == b"\x1ba"


def test_widget_feeds_bytes_without_raising(qtbot) -> None:
    w = TerminalWidget()
    qtbot.addWidget(w)
    w.resize(400, 300)

    w._on_data(b"hello world\n")
    w.update()

    assert w._emu.display_line(0).startswith("hello world") or "hello" in "".join(
        w._emu.display_line(i) for i in range(w._emu.rows)
    )


def test_widget_paint_does_not_raise(qtbot) -> None:
    w = TerminalWidget()
    qtbot.addWidget(w)
    w.resize(200, 150)
    w._on_data(b"\x1b[31mRED\x1b[0m plain")

    # force a paint
    w.grab()


def test_widget_start_stop_runs_shell(qtbot, tmp_path: Path) -> None:
    import sys

    if sys.platform == "win32":
        return
    w = TerminalWidget()
    qtbot.addWidget(w)
    w.resize(400, 300)
    w.start(["/bin/sh", "-c", "echo ok; sleep 0.2"], cwd=tmp_path)
    try:
        qtbot.wait_until(w.is_running, timeout=3000)
    finally:
        w.stop()
    assert not w.is_running()


# keep QApplication referenced for pytest-qt offscreen
_ = QApplication

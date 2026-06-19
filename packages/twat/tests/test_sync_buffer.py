"""Regression: DEC 2026 (Synchronized Output) must buffer frames atomically.

pi wraps every redraw frame in ESC[?2026h ... ESC[?2026l. termqt doesn't
implement 2026, so without buffering it renders partial frames and the cursor
drifts, causing status lines (e.g. "Working") to stack downward. TermQtTerminal
buffers bytes between ?2026h and ?2026l and flushes them as one chunk.
"""

from PySide6.QtWidgets import QApplication

from twat.ui.termqt_terminal import TermQtTerminal


def _cells(t, row, n=20):
    return "".join((c.char if c is not None else " ") for c in t._buffer[row][:n])


def test_sync_frame_content_is_flushed(qtbot) -> None:
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.resize(400, 200)

    t._on_data(b"\x1b[?2026hHELLO\x1b[?2026l")
    QApplication.processEvents()

    assert _cells(t, 0).startswith("HELLO")


def test_sync_control_bytes_are_stripped(qtbot) -> None:
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.resize(400, 200)

    t._on_data(b"\x1b[?2026hX\x1b[?2026l")
    QApplication.processEvents()

    # no raw escape bytes leak into the rendered buffer
    row = _cells(t, 0)
    assert "\x1b" not in row
    assert "?" not in row


def test_non_sync_bytes_pass_through(qtbot) -> None:
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.resize(400, 200)

    t._on_data(b"PLAIN")
    QApplication.processEvents()

    assert _cells(t, 0).startswith("PLAIN")


def test_open_frame_holds_until_close(qtbot) -> None:
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.resize(400, 200)

    t._on_data(b"\x1b[?2026hHELD")
    QApplication.processEvents()
    # frame open: content must NOT render yet
    assert _cells(t, 0).strip() == ""

    t._on_data(b"MORE\x1b[?2026l")
    QApplication.processEvents()
    # frame closed: full content renders atomically
    assert _cells(t, 0).startswith("HELDMORE")


def test_frame_split_across_chunks(qtbot) -> None:
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.resize(400, 200)

    t._on_data(b"\x1b[?2026hAB")
    QApplication.processEvents()
    t._on_data(b"CD\x1b[?2026l")
    QApplication.processEvents()

    assert _cells(t, 0).startswith("ABCD")


def test_open_marker_split_mid_bytes(qtbot) -> None:
    # the real-app failure: a PTY read ends mid-marker. The ?2026h open marker
    # is split across two chunks; carry-over must reassemble it so the frame
    # still opens and buffers (otherwise the spinner stacks).
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.resize(400, 200)

    full = b"\x1b[?2026h"
    t._on_data(full[:4])  # "\x1b[?2"
    QApplication.processEvents()
    t._on_data(full[4:] + b"HELD")  # "026h" + content
    QApplication.processEvents()
    # frame is open: content must NOT render yet
    assert _cells(t, 0).strip() == ""

    t._on_data(b"\x1b[?2026l")
    QApplication.processEvents()
    assert _cells(t, 0).startswith("HELD")


def test_close_marker_split_mid_bytes(qtbot) -> None:
    # the ?2026l close marker is split across two chunks; carry-over must
    # reassemble it so the frame flushes atomically.
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.resize(400, 200)

    t._on_data(b"\x1b[?2026hWORK")
    QApplication.processEvents()
    assert _cells(t, 0).strip() == ""  # still buffering

    close = b"\x1b[?2026l"
    t._on_data(close[:3])  # "\x1b[?"
    QApplication.processEvents()
    t._on_data(close[3:])  # "2026l"
    QApplication.processEvents()

    assert _cells(t, 0).startswith("WORK")


def test_decckm_marker_split_mid_bytes(qtbot) -> None:
    # DECCKM (application cursor) marker split across chunks must still toggle
    # _app_cursor, so arrows use the right sequence inside a TUI.
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.resize(400, 200)
    assert t._app_cursor is False

    on = b"\x1b[?1h"
    t._on_data(on[:2])  # "\x1b["
    QApplication.processEvents()
    t._on_data(on[2:])  # "?1h"
    QApplication.processEvents()

    assert t._app_cursor is True

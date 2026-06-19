"""Regression: multibyte UTF-8 glyphs must occupy exactly one cell.

termqt's own byte->buffer decode has an operator-precedence bug
(`char & 0xc0 == 0xc0` binds as `char & (0xc0 == 0xc0)`), so every multibyte
glyph (pi's braille spinner, box-drawing) is written as several latin-1 cells.
That widens pi's full-width spinner line past the grid, so its cursor-relative
redraw drifts one row per frame and the "Working" status stacks downward.
TermQtTerminal overrides _stdout_string to decode UTF-8 by whole characters.
"""

from PySide6.QtWidgets import QApplication

from twat.ui.termqt_terminal import TermQtTerminal

_GLYPH = b" \xe2\xa0\x99 X"  # space, braille U+2819, space, X
_BRAILLE = "\u2819"


def _cells(t, row, n=5):
    return [(c.char if c is not None else None) for c in t._buffer[row][:n]]


def test_braille_glyph_is_one_cell(qtbot) -> None:
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.create_buffer(80, 24)

    t._on_data(_GLYPH)
    QApplication.processEvents()

    # one logical cell for the glyph (plus a zero-width TAIL placeholder)
    assert _cells(t, 0) == [" ", _BRAILLE, " ", "X", None]


def test_glyph_split_across_chunks_survives(qtbot) -> None:
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.create_buffer(80, 24)

    t._on_data(_GLYPH[:2])  # ends mid-glyph
    QApplication.processEvents()
    t._on_data(_GLYPH[2:])
    QApplication.processEvents()

    assert _cells(t, 0) == [" ", _BRAILLE, " ", "X", None]
    assert bytes(t._utf8_carry) == b""


_SPINNER_GLYPHS = (
    b"\xe2\xa0\x8b",
    b"\xe2\xa0\x99",
    b"\xe2\xa0\xb9",
    b"\xe2\xa0\xb8",
    b"\xe2\xa0\xbc",
)


def test_spinner_does_not_stack_with_glyphs(qtbot) -> None:
    # pi redraws its spinner every frame with cursor-up-5, clear, rewrite,
    # cursor-down-5, wrapped in DEC 2026. Before the UTF-8 fix the braille glyph
    # was mis-decoded into extra latin-1 cells, so the home row drifted and
    # "Working" stacked on many rows. After the fix it stays on a single row.
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.resize(700, 400)
    t.create_buffer(80, 24)
    # prime the screen so the spinner sits near the bottom (the real case)
    t._on_data(b"\r\r\n".join(b"line%02d" % i for i in range(30)))
    QApplication.processEvents()

    for n in range(40):
        glyph = _SPINNER_GLYPHS[n % len(_SPINNER_GLYPHS)]
        frame = (
            b"\x1b[?2026h\x1b[5A\r\x1b[2K "
            + glyph
            + b" Working..."
            + b" " * 67
            + b"\x1b[0m\x1b[?2026l\x1b[5B\x1b[1G\x1b[?25l"
        )
        t._on_data(frame)
        QApplication.processEvents()

    def line(row, n=40):
        return "".join((c.char if c is not None else " ") for c in t._buffer[row][:n])

    working = [r for r in range(len(t._buffer)) if "Working" in line(r)]
    assert len(working) == 1


def test_unsupported_escape_does_not_crash(qtbot) -> None:
    # pi emits sequences termqt doesn't implement (Kitty keyboard `[>...u`,
    # OSC 8 hyperlinks `]8;;`); termqt raises ValueError on them. We must skip,
    # not crash, and keep rendering the rest of the stream.
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.create_buffer(80, 24)

    t._on_data(b"\x1b[>7u\x1b]8;;\x07AFTER")
    QApplication.processEvents()

    assert "".join((c.char if c is not None else " ") for c in t._buffer[0][:5]) == "AFTER"


def test_char_width_matches_wcwidth_not_font(qtbot) -> None:
    # pi lays out with wcwidth; braille and box-drawing are 1 cell, CJK is 2.
    # The font's glyph advance must not decide cell width (that caused drift).
    t = TermQtTerminal()
    qtbot.addWidget(t)
    assert t.get_char_width("A") == 1
    assert t.get_char_width("\u2819") == 1  # braille spinner
    assert t.get_char_width("\u2500") == 1  # box drawing
    assert t.get_char_width("\u4e2d") == 2  # CJK (wide)


def test_tab_and_backtab_go_to_pty(qtbot) -> None:
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent

    t = TermQtTerminal()
    qtbot.addWidget(t)
    sent: list[bytes] = []
    t.stdin_callback = sent.append

    tab = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier)
    backtab = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backtab, Qt.KeyboardModifier.ShiftModifier)
    assert t.event(tab) is True
    assert t.event(backtab) is True
    assert sent == [b"\t", b"\x1b[Z"]

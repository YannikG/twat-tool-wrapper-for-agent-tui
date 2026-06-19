"""Regression: truecolor SGR (38;2;r;g;b) must reach termqt cells.

termqt's SGR parser omits the truecolor branch; pi emits ~50 truecolor seqs/sec.
TermQtTerminal patches the escape processor's `m` dispatch entry with a
truecolor-aware parser.
"""

from PySide6.QtWidgets import QApplication

from twat.ui.termqt_terminal import TermQtTerminal


def test_truecolor_foreground_reaches_cell(qtbot) -> None:
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.resize(400, 200)

    t.stdout(b"\x1b[38;2;138;190;183mX\x1b[0m")
    QApplication.processEvents()

    cell = t._buffer[0][0]
    color = cell.color
    assert (color.red(), color.green(), color.blue()) == (138, 190, 183)


def test_truecolor_background_reaches_cell(qtbot) -> None:
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.resize(400, 200)

    t.stdout(b"\x1b[48;2;10;20;30mY\x1b[0m")
    QApplication.processEvents()

    cell = t._buffer[0][0]
    bg = cell.bg_color
    assert (bg.red(), bg.green(), bg.blue()) == (10, 20, 30)


def test_256color_still_works(qtbot) -> None:
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.resize(400, 200)

    t.stdout(b"\x1b[38;5;196mZ\x1b[0m")  # 256-color red
    QApplication.processEvents()

    cell = t._buffer[0][0]
    # 196 is bright red in the xterm palette
    assert cell.color.red() > 200


def test_reset_restores_default(qtbot) -> None:
    t = TermQtTerminal()
    qtbot.addWidget(t)
    t.resize(400, 200)

    t.stdout(b"\x1b[38;2;138;190;183mX\x1b[0mW")
    QApplication.processEvents()

    reset_cell = t._buffer[0][1]
    # after SGR 0, color is the default (not the truecolor value)
    assert (reset_cell.color.red(), reset_cell.color.green(), reset_cell.color.blue()) != (
        138,
        190,
        183,
    )

"""Qt-free tests for the terminal emulator wrapper."""

from twat.terminal.emulator import TerminalEmulator


def test_feed_renders_text_on_first_line() -> None:
    emu = TerminalEmulator(rows=24, cols=80)

    emu.feed(b"Hi there")

    assert emu.display_line(0).startswith("Hi there")


def test_cursor_is_zero_indexed_after_write() -> None:
    emu = TerminalEmulator(rows=24, cols=80)

    emu.feed(b"Hi")

    # after writing 2 chars, cursor sits at column 2, row 0
    assert emu.cursor() == (2, 0)


def test_resize_changes_dimensions() -> None:
    emu = TerminalEmulator(rows=24, cols=80)

    emu.resize(rows=10, cols=40)

    assert emu.rows == 10
    assert emu.cols == 40


def test_feed_records_color_attribute() -> None:
    emu = TerminalEmulator(rows=24, cols=80)

    # SGR red (31), write X, SGR reset (0)
    emu.feed(b"\x1b[31mX\x1b[0m")

    cell = emu.cell(0, 0)
    assert cell is not None
    assert cell.fg == "red"


def test_invalid_utf8_does_not_raise() -> None:
    emu = TerminalEmulator(rows=24, cols=80)

    emu.feed(b"\xff\xfeABC")  # invalid utf-8 lead bytes

    line = emu.display_line(0)
    assert "ABC" in line
    assert line.startswith("�")  # replacement char, not a crash


def test_cell_out_of_range_returns_none() -> None:
    emu = TerminalEmulator(rows=3, cols=3)

    assert emu.cell(5, 5) is None

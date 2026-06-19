"""Terminal emulator: a thin Qt-free wrapper over `pyte`.

Feeds PTY bytes into a `pyte` screen and exposes the buffer + cursor for the
render widget. pyte stores colors as strings ('default', named, or hex); the
widget maps them via `color_for`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Cell:
    """A rendered screen cell."""

    data: str
    fg: str
    bg: str
    bold: bool
    italics: bool
    underscore: bool
    reverse: bool
    strikethrough: bool
    blink: bool


class TerminalEmulator:
    """Wraps a pyte Screen + Stream."""

    def __init__(self, rows: int, cols: int) -> None:
        import pyte

        self._screen = pyte.Screen(cols, rows)
        self._stream = pyte.Stream(self._screen)

    @property
    def rows(self) -> int:
        return self._screen.lines

    @property
    def cols(self) -> int:
        return self._screen.columns

    def feed(self, data: bytes) -> None:
        self._stream.feed(data.decode("utf-8", errors="replace"))

    def resize(self, rows: int, cols: int) -> None:
        self._screen.resize(lines=rows, columns=cols)

    def display_line(self, row: int) -> str:
        if 0 <= row < self._screen.lines:
            return self._screen.display[row]
        return ""

    def cursor(self) -> tuple[int, int]:
        return (self._screen.cursor.x, self._screen.cursor.y)

    def cell(self, row: int, col: int) -> Cell | None:
        if not (0 <= row < self._screen.lines and 0 <= col < self._screen.columns):
            return None
        ch = self._screen.buffer[row][col]
        return Cell(
            data=ch.data,
            fg=ch.fg,
            bg=ch.bg,
            bold=ch.bold,
            italics=ch.italics,
            underscore=ch.underscore,
            reverse=ch.reverse,
            strikethrough=ch.strikethrough,
            blink=ch.blink,
        )

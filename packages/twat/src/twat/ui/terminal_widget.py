"""Embedded terminal widget: renders a pyte screen and pipes keys to a PTY.

Architecture: a reader thread only reads bytes from the PTY and emits them via a
Qt signal; the main thread feeds the emulator and paints. The emulator is
touched on the main thread only, so no locks are needed.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Mapping

from PySide6.QtCore import QObject, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QKeyEvent, QPainter
from PySide6.QtWidgets import QWidget

from twat.terminal.emulator import TerminalEmulator
from twat.terminal.pty_session import PtySession

# 16-color ANSI palette (dark-first). pyte names: black/red/green/brown/blue/
# magenta/cyan/white + bright* variants.
_ANSI: dict[str, str] = {
    "black": "#1b1b25",
    "red": "#ff5555",
    "green": "#50fa7b",
    "brown": "#f1fa8c",
    "blue": "#bd93f9",
    "magenta": "#ff79c6",
    "cyan": "#8be9fd",
    "white": "#f8f8f2",
    "brightblack": "#6272a4",
    "brightred": "#ff6e6e",
    "brightgreen": "#69ff94",
    "brightbrown": "#ffffa5",
    "brightblue": "#d6acff",
    "brightmagenta": "#ff92df",
    "brightcyan": "#a4ffff",
    "brightwhite": "#ffffff",
}


def _color(name: str, default: QColor) -> QColor:
    if name == "default":
        return default
    hexc = _ANSI.get(name)
    if hexc is None and len(name) == 6:
        hexc = name  # pyte truecolor is a 6-hex-digit string
    if hexc is None:
        return default
    return QColor("#" + hexc if not hexc.startswith("#") else hexc)


def key_to_bytes(event: QKeyEvent) -> bytes | None:
    """Encode a Qt key event into terminal input bytes, or None if ignored."""
    key = event.key()
    mods = event.modifiers()
    ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
    alt = bool(mods & Qt.KeyboardModifier.AltModifier)

    # Ctrl + letter -> control character
    if ctrl and Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
        b = bytes([key - Qt.Key.Key_A + 1])
        return b"\x1b" + b if alt else b

    specials: dict[int, bytes] = {
        Qt.Key.Key_Return: b"\r",
        Qt.Key.Key_Enter: b"\r",
        Qt.Key.Key_Backspace: b"\x7f",
        Qt.Key.Key_Tab: b"\t",
        Qt.Key.Key_Escape: b"\x1b",
        Qt.Key.Key_Up: b"\x1b[A",
        Qt.Key.Key_Down: b"\x1b[B",
        Qt.Key.Key_Right: b"\x1b[C",
        Qt.Key.Key_Left: b"\x1b[D",
        Qt.Key.Key_Home: b"\x1b[H",
        Qt.Key.Key_End: b"\x1b[F",
        Qt.Key.Key_PageUp: b"\x1b[5~",
        Qt.Key.Key_PageDown: b"\x1b[6~",
        Qt.Key.Key_Delete: b"\x1b[3~",
        Qt.Key.Key_Insert: b"\x1b[2~",
    }
    if key in specials:
        return b"\x1b" + specials[key] if alt else specials[key]

    text = event.text()
    if text and not ctrl:
        data = text.encode("utf-8")
        return b"\x1b" + data if alt else data
    return None


class _Reader(QObject):
    """Reads PTY bytes on a thread, emits them on the main thread."""

    data_read = Signal(bytes)
    finished = Signal()

    def __init__(self, session: PtySession) -> None:
        super().__init__()
        self._session = session
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            chunk = self._session.read(timeout=0.1)
            if chunk:
                self.data_read.emit(chunk)
            elif not self._session.is_alive():
                self.finished.emit()
                return


class TerminalWidget(QWidget):
    """An embedded terminal: pyte screen rendered, keys piped to a PTY."""

    finished = Signal()  # emitted when the child process exits

    def __init__(
        self,
        *,
        bg: str = "#15151d",
        fg: str = "#d7d9e3",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self._bg = QColor(bg)
        self._fg = QColor(fg)

        self._font = QFont("Menlo", 12)
        self._font.setStyleHint(QFont.StyleHint.Monospace)
        self._fm = QFontMetrics(self._font)
        self._char_w = self._fm.horizontalAdvance("M") or 8
        self._char_h = self._fm.height() or 16

        rows, cols = self._size_in_cells()
        self._emu = TerminalEmulator(rows=max(1, rows), cols=max(1, cols))
        self._session: PtySession | None = None
        self._reader: _Reader | None = None

    # -- lifecycle -----------------------------------------------------------

    def start(
        self,
        argv: list[str],
        *,
        cwd: str | os.PathLike[str],
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.stop()
        rows, cols = self._emu.rows, self._emu.cols
        self._session = PtySession.spawn(argv, cwd=cwd, env=env, rows=rows, cols=cols)
        self._reader = _Reader(self._session)
        self._reader.data_read.connect(self._on_data)
        self._reader.finished.connect(self._on_finished)
        self._reader.start()
        self.setFocus()

    def stop(self) -> None:
        if self._reader is not None:
            self._reader.stop()
            self._reader = None
        if self._session is not None:
            self._session.close(force=True)
            self._session = None

    def is_running(self) -> bool:
        return self._session is not None and self._session.is_alive()

    # -- Qt events -----------------------------------------------------------

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), self._bg)
        p.setFont(self._font)

        emu = self._emu
        cw, ch = self._char_w, self._char_h
        for row in range(emu.rows):
            y = row * ch
            for col in range(emu.cols):
                cell = emu.cell(row, col)
                if cell is None:
                    continue
                x = col * cw
                bg = _color(cell.bg, self._bg)
                fg = _color(cell.fg, self._fg)
                if cell.reverse:
                    bg, fg = fg, bg
                if bg != self._bg:
                    p.fillRect(QRect(x, y, cw, ch), bg)
                if cell.data and cell.data != " ":
                    if cell.bold:
                        f = QFont(self._font)
                        f.setBold(True)
                        p.setFont(f)
                    p.setPen(fg)
                    p.drawText(
                        QRect(x, y, cw, ch),
                        Qt.AlignmentFlag.AlignCenter,
                        cell.data,
                    )
                    if cell.bold:
                        p.setFont(self._font)
        # block cursor
        if self.is_running():
            cx, cy = emu.cursor()
            if 0 <= cy < emu.rows and 0 <= cx < emu.cols:
                p.fillRect(QRect(cx * cw, cy * ch, cw, ch), self._fg)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._session is None:
            return
        data = key_to_bytes(event)
        if data is not None:
            self._session.write(data)

    def resizeEvent(self, event: object) -> None:
        rows, cols = self._size_in_cells()
        rows, cols = max(1, rows), max(1, cols)
        if rows != self._emu.rows or cols != self._emu.cols:
            self._emu.resize(rows, cols)
            if self._session is not None:
                self._session.resize(rows=rows, cols=cols)
        super().resizeEvent(event)  # type: ignore[arg-type]

    # -- slots ---------------------------------------------------------------

    def _on_data(self, data: bytes) -> None:
        self._emu.feed(data)
        self.update()

    def _on_finished(self) -> None:
        self.finished.emit()
        self.update()

    # -- helpers -------------------------------------------------------------

    def _size_in_cells(self) -> tuple[int, int]:
        cols = self.width() // self._char_w
        rows = self.height() // self._char_h
        return rows, cols

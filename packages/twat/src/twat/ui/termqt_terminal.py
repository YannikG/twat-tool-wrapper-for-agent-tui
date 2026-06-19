"""Embedded terminal widget backed by termqt (ADR-0003, revised).

Wraps `termqt.Terminal` (a VT100/XTerm emulator + Qt renderer) and feeds it
from our `PtySession`. We keep our own PTY layer (cwd + env injection for the
pi lifecycle hook) rather than termqt's IO backends, which lack cwd/env
control.

Four termqt gaps are patched here:
  * Char width — termqt's widget sizes cells by the font's glyph advance, so a
    glyph the font draws wider than a cell (e.g. braille) counts as 2 columns.
    pi lays out with wcwidth (braille/box-drawing = 1), and that mismatch made
    lines wrap one extra row, drifting pi's cursor-relative redraw. We override
    get_char_width to use Unicode width.
  * DECCKM — termqt's key handler hardcodes normal-mode arrows; we override
    keyPressEvent to send application-cursor (`ESC O ...`) when a TUI enables
    DECCKM (`ESC [ ? 1 h`).
  * Truecolor — termqt's SGR parser omits 38;2;r;g;b / 48;2;r;g;b, which pi
    emits heavily. We replace the escape processor's `m` dispatch entry with a
    truecolor-aware parser.
  * UTF-8 decode — termqt's byte->buffer decode has an operator-precedence bug
    (`char & 0xc0 == 0xc0` binds as `char & (0xc0 == 0xc0)`), corrupting every
    multibyte glyph into several latin-1 cells. That widened pi's spinner line
    so its cursor-relative redraw drifted and status lines stacked. We override
    _stdout_string to decode UTF-8 by whole characters (chunk-safe).
"""

from __future__ import annotations

import logging
import re
import threading
import unicodedata
from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent
from termqt import Terminal
from termqt.colors import colors8, colors16, colors256

from twat.terminal.pty_session import PtySession

_log = logging.getLogger("twat.terminal")

_DECCKM_ON = b"\x1b[?1h"
_DECCKM_OFF = b"\x1b[?1l"
# DEC 2026 (Synchronized Output): BSU/ESU mark an atomic redraw frame.
_SYNC_ON = b"\x1b[?2026h"
_SYNC_OFF = b"\x1b[?2026l"

# Escape sequences termqt's escape processor can't handle (it raises). pi emits
# all of these; none affect text rendering, so strip them before feeding termqt:
#   * OSC strings (\x1b]...BEL/ST): titles (OSC 0/2), hyperlinks (OSC 8),
#     color queries — termqt never responds to queries and renders text fine
#     without them.
#   * Kitty keyboard protocol CSI: \x1b[<...u / \x1b[>...u / \x1b[?...u
#     (capability negotiation; no response = pi falls back to plain keys).
#   * Device Attributes queries: \x1b[c / \x1b[>c (DA1/DA2; termqt ignores).
_UNSUPPORTED_SEQ_RE = re.compile(
    rb"\x1b\].*?(?:\x07|\x1b\\)"  # OSC: ESC ] ... BEL | ST
    rb"|\x1b\[[<>?][0-9]*u"  # Kitty keyboard
    rb"|\x1b\[[0-9>]*c",  # DA1/DA2 query
    re.DOTALL,
)


def _strip_unsupported(data: bytes) -> bytes:
    """Remove escape sequences termqt can't parse, before they reach it."""
    return _UNSUPPORTED_SEQ_RE.sub(b"", data)


_APP_ARROWS = {
    Qt.Key.Key_Up: b"\x1bOA",
    Qt.Key.Key_Down: b"\x1bOB",
    Qt.Key.Key_Right: b"\x1bOC",
    Qt.Key.Key_Left: b"\x1bOD",
    Qt.Key.Key_Home: b"\x1bOH",
    Qt.Key.Key_End: b"\x1bOF",
}
_NORMAL_ARROWS = {
    Qt.Key.Key_Up: b"\x1b[A",
    Qt.Key.Key_Down: b"\x1b[B",
    Qt.Key.Key_Right: b"\x1b[C",
    Qt.Key.Key_Left: b"\x1b[D",
    Qt.Key.Key_Home: b"\x1b[H",
    Qt.Key.Key_End: b"\x1b[F",
}

_DEFAULT_FG = QColor(229, 229, 229)
_DEFAULT_BG = QColor(0, 0, 0)

# Control markers we detect by byte-matching before handing data to termqt.
# A PTY read may end mid-marker, so we hold back a trailing fragment that could
# be the start of one of these and prepend it to the next chunk.
_MARKERS = (_SYNC_ON, _SYNC_OFF, _DECCKM_ON, _DECCKM_OFF)
_MAX_MARKER = max(len(m) for m in _MARKERS)


def _safe_split(buf: bytes) -> int:
    """Return how many leading bytes of `buf` are safe to process now.

    Holds back a trailing fragment that is a *proper prefix* of any control
    marker, so a marker split across two PTY reads is never missed. Only the
    last `_MAX_MARKER - 1` bytes can possibly be such a fragment.
    """
    start = max(0, len(buf) - (_MAX_MARKER - 1))
    for cut in range(start, len(buf)):
        tail = buf[cut:]
        if any(len(tail) < len(m) and m.startswith(tail) for m in _MARKERS):
            return cut
    return len(buf)


def _split_incomplete_utf8(data: bytes) -> tuple[bytes, bytes]:
    """Split off a trailing incomplete UTF-8 sequence.

    A PTY read may end mid-character; returns (complete, tail) so the tail can
    be prepended to the next chunk. Without this, a multibyte glyph split across
    reads decodes as replacement characters.
    """
    for back in range(1, min(4, len(data)) + 1):
        b = data[-back]
        if b < 0x80:
            break  # ASCII byte: nothing pending
        if b >= 0xC0:  # lead byte: needs `need` bytes total
            need = 4 if b >= 0xF0 else 3 if b >= 0xE0 else 2
            if back < need:
                return data[:-back], data[-back:]
            break
        # else: continuation byte (0x80..0xBF), keep scanning backward
    return data, b""


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


class TermQtTerminal(Terminal):
    """termqt Terminal with DECCKM-aware arrows and truecolor SGR, fed from a PTY."""

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(800, 600)
        if parent is not None:
            self.setParent(parent)
        self.set_font()
        self.maximum_line_history = 2000
        self._app_cursor = False
        self._session: PtySession | None = None
        self._reader: _Reader | None = None
        self._on_finished: Callable[[], None] | None = None
        # DEC 2026 (Synchronized Output): buffer bytes between BSU (?2026h)
        # and ESU (?2026l), flush atomically. pi wraps every redraw frame in
        # this; without buffering, termqt renders partial frames and the cursor
        # drifts, causing status lines (e.g. "Working") to stack downward.
        self._sync_buf: bytearray | None = None
        # Carry-over for a trailing incomplete escape sequence. The PTY reader
        # delivers arbitrary-sized chunks; a ?2026h/?2026l (or DECCKM) marker can
        # straddle a chunk boundary. We hold the unterminated tail and prepend it
        # to the next chunk so marker detection stays chunk-safe.
        self._carry = bytearray()
        # Carry-over for a trailing incomplete UTF-8 sequence across PTY reads
        # (see _stdout_string, which replaces termqt's buggy UTF-8 decode).
        self._utf8_carry = bytearray()
        self._install_truecolor_patch()

    # -- lifecycle -----------------------------------------------------------

    def attach(self, session: PtySession, *, on_finished: Callable[[], None] | None = None) -> None:
        """Bind to an externally-owned PTY (the process adapter's)."""
        self.detach()
        self._session = session
        self._on_finished = on_finished
        self.stdin_callback = session.write
        # Force termqt to compute its cell size from the current widget geometry
        # (it normally does this in resizeEvent, which may not have fired yet if
        # the widget was just added to the host). Then sync the PTY to it.
        self.resize(self.size().width(), self.size().height())
        self._resize_pty()
        self._reader = _Reader(session)
        self._reader.data_read.connect(self._on_data)
        self._reader.finished.connect(self._on_finished_slot)
        self._reader.start()
        self.setFocus()

    def detach(self) -> None:
        if self._reader is not None:
            self._reader.stop()
            self._reader = None
        self._session = None
        self._on_finished = None
        self._carry.clear()
        self._utf8_carry.clear()
        self._sync_buf = None
        self.stdin_callback = lambda _b: None  # type: ignore[assignment]
        # stop termqt's cursor-blink timer so focusOutEvent doesn't touch a
        # timer Qt is already tearing down on widget destruction.
        import contextlib

        with contextlib.suppress(Exception):
            self._cursor_blinking_timer.stop()  # type: ignore[attr-defined]

    def is_running(self) -> bool:
        return self._session is not None and self._session.is_alive()

    # -- SGR override: add truecolor (38;2 / 48;2) to termqt's parser --------

    def _install_truecolor_patch(self) -> None:
        """Patch the escape processor's SGR handler to support truecolor.

        termqt's EscapeProcessor._csi_m handles 16/256-color but omits
        38;2;r;g;b / 48;2;r;g;b, which pi emits heavily. The dispatch dict
        captures the bound method at init, so we replace the dict entry.
        """
        ep = self.escape_processor
        ep._csi_func["m"] = self._truecolor_csi_m

    def _truecolor_csi_m(self) -> None:
        ep = self.escape_processor
        args = ep._args if ep._args else [0]
        color: QColor | None = None
        bg_color: QColor | None = None
        bold = underline = reverse = -1

        i = 0
        while i < len(args):
            arg = int(args[i])
            if arg == 0:
                bold = underline = reverse = 0
                color = _DEFAULT_FG
                bg_color = _DEFAULT_BG
            elif arg == 1:
                bold = 1
            elif arg == 4:
                underline = 1
            elif arg == 7:
                reverse = 1
            elif arg == 22:
                bold = 0
            elif arg == 24:
                underline = 0
            elif arg == 27:
                reverse = 0
            elif arg == 39:
                color = _DEFAULT_FG
            elif arg == 49:
                bg_color = _DEFAULT_BG
            elif arg in (38, 48) and i + 1 < len(args):
                mode = int(args[i + 1])
                if mode == 2 and i + 4 < len(args):
                    qc = QColor(int(args[i + 2]), int(args[i + 3]), int(args[i + 4]))
                    if arg == 38:
                        color = qc
                    else:
                        bg_color = qc
                    i += 4
                elif mode == 5 and i + 2 < len(args):
                    idx = int(args[i + 2])
                    if 0 <= idx <= 255:
                        if arg == 38:
                            color = colors256[idx]
                        else:
                            bg_color = colors256[idx]
                    i += 2
            elif 30 <= arg <= 37:
                color = colors8[arg]
            elif 40 <= arg <= 47:
                bg_color = colors8[arg - 10]
            elif 90 <= arg <= 97:
                color = colors16[arg - 60]
            elif 100 <= arg <= 107:
                bg_color = colors16[arg - 70]
            i += 1

        if color is None:
            color = _DEFAULT_FG
        if bg_color is None:
            bg_color = _DEFAULT_BG
        if bold == -1:
            bold = 0
        if underline == -1:
            underline = 0
        if reverse == -1:
            reverse = 0
        ep.set_style_cb(color, bg_color, bold, underline, reverse)

    def get_char_width(self, t: str) -> int:
        """Cell width by Unicode rules, not the font's glyph advance.

        termqt's widget measures `ceil(fontAdvance / cellWidth)`, so a glyph the
        font draws wider than the cell (e.g. braille `⠙`, in many fonts) counts
        as 2 cells. pi lays out using wcwidth (braille/box-drawing = 1), so that
        mismatch makes every spinner/stream line wrap one extra row and pi's
        cursor-relative redraw drifts, stacking status lines. We match pi.
        """
        if not t:
            return 1
        if ord(t[0]) < 0x80:
            return 1
        if unicodedata.combining(t):
            return 0
        return 2 if unicodedata.east_asian_width(t) in ("W", "F") else 1

    # -- key handling: override termqt to honor DECCKM -----------------------

    def event(self, e: QEvent) -> bool:
        # Qt consumes Tab/Backtab for focus traversal before keyPressEvent, so a
        # TUI never sees it. Intercept here and send it to the PTY instead.
        if e.type() == QEvent.Type.KeyPress and isinstance(e, QKeyEvent):
            if e.key() == Qt.Key.Key_Tab:
                self.input(b"\t")
                return True
            if e.key() == Qt.Key.Key_Backtab:
                self.input(b"\x1b[Z")
                return True
        return bool(super().event(e))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        arrows = _APP_ARROWS if self._app_cursor else _NORMAL_ARROWS
        if key in arrows:
            self.input(arrows[key])
            return
        super().keyPressEvent(event)

    # -- data + DECCKM sniff + DEC 2026 sync buffering ----------------------

    def _on_data(self, data: bytes) -> None:
        # Prepend any carried-over incomplete escape sequence from the previous
        # chunk, then hold back a new incomplete tail so control markers
        # (?2026h/?2026l, DECCKM) are never split across chunk boundaries.
        buf = bytes(self._carry) + data
        self._carry.clear()
        split = _safe_split(buf)
        if split < len(buf):
            self._carry.extend(buf[split:])
            buf = buf[:split]
        if not buf:
            return
        # Strip escape sequences termqt can't parse (OSC titles/hyperlinks,
        # Kitty keyboard, DA queries) before they reach its escape processor.
        buf = _strip_unsupported(buf)
        if not buf:
            return
        if _DECCKM_ON in buf:
            self._app_cursor = True
        elif _DECCKM_OFF in buf:
            self._app_cursor = False
        self._feed_with_sync(buf)

    def _feed_with_sync(self, data: bytes) -> None:
        """Honor DEC 2026: buffer bytes while a synchronized update is open.

        Bytes are accumulated in self._sync_buf once ?2026h is seen and flushed
        to termqt's stdout as one atomic chunk when ?2026l closes the frame.
        Bytes outside any frame pass through immediately. The ?2026 control
        bytes themselves are stripped (termqt does not implement the mode).
        """
        out = bytearray()
        pos = 0
        n = len(data)
        while pos < n:
            idx_h = data.find(_SYNC_ON, pos)
            idx_l = data.find(_SYNC_OFF, pos)
            next_h = idx_h if idx_h >= 0 else n
            next_l = idx_l if idx_l >= 0 else n
            if next_h == n and next_l == n:
                chunk = data[pos:]
                if self._sync_buf is not None:
                    self._sync_buf.extend(chunk)
                else:
                    out.extend(chunk)
                break
            if next_h < next_l:
                # ?2026h opens a frame
                out.extend(data[pos:next_h])
                if self._sync_buf is None:
                    self._sync_buf = bytearray()
                pos = next_h + len(_SYNC_ON)
            else:
                # ?2026l closes the frame; append buffered content then flush
                if self._sync_buf is not None:
                    self._sync_buf.extend(data[pos:next_l])
                    out.extend(self._sync_buf)
                    self._sync_buf = None
                else:
                    out.extend(data[pos:next_l])
                pos = next_l + len(_SYNC_OFF)
        if out:
            self.stdout(bytes(out))

    def _stdout_string(self, string: bytes) -> bool:
        """Decode bytes to the buffer (replaces termqt's broken UTF-8 path).

        termqt's own `_stdout_string` has an operator-precedence bug in its
        UTF-8 decode: `char & 0xc0 == 0xc0` binds as `char & (0xc0 == 0xc0)`
        i.e. `char & 1`, so every multibyte glyph (the braille spinner,
        box-drawing) is written as several latin-1 cells. That widens lines past
        the grid, so pi's cursor-relative spinner redraw (cursor-up N, rewrite,
        cursor-down N) drifts one row per frame and status lines stack.

        We decode UTF-8 by whole characters and carry an incomplete trailing
        sequence to the next chunk, then feed termqt's escape processor exactly
        as it expects (one code point at a time, control chars handled inline).
        """
        data = bytes(self._utf8_carry) + string
        self._utf8_carry.clear()
        keep, tail = _split_incomplete_utf8(data)
        self._utf8_carry.extend(tail)
        text = keep.decode("utf-8", errors="replace")

        ep = self.escape_processor
        need_draw = False
        pending = ""
        for ch in text:
            c = ord(ch)
            try:
                ret = ep.input(c)
            except (ValueError, IndexError) as exc:
                # termqt raises ValueError on sequences it doesn't implement
                # (Kitty keyboard `[>...u`, OSC 8 hyperlinks `]8;;`) and IndexError when an
                # erase/cursor op runs against a row index outside the deque
                # (e.g. `ESC[J` while the cursor is past the buffer during a
                # scroll/resize race). Most unsupported sequences are stripped
                # upstream (_strip_unsupported); anything residual here (a
                # sequence split across PTY reads) is expected — reset and keep
                # rendering. DEBUG, not WARNING: these are not actionable.
                ep.reset()
                _log.debug("escape processor dropped a byte (0x%02x): %s", c, exc)
                continue
            if ret == 0:
                if pending:
                    self.write_at_cursor(pending)
                    pending = ""
                continue
            if ret == 1:
                need_draw = True
                continue
            # ret == -1: not part of a control sequence
            if c == 0x08:  # BS
                if pending:
                    self.write_at_cursor(pending)
                    pending = ""
                self.backspace()
            elif c == 0x0D:  # CR
                if pending:
                    self.write_at_cursor(pending)
                    pending = ""
                self.carriage_feed()
            elif c == 0x0A:  # LF
                if pending:
                    self.write_at_cursor(pending)
                    pending = ""
                self.write_at_cursor("\n")
            elif c == 0x09:  # TAB
                pending += "        "
            elif c == 0x07:  # BEL
                pass
            else:
                pending += ch
            need_draw = True
        if pending:
            self.write_at_cursor(pending)
        return need_draw

    def _on_finished_slot(self) -> None:
        if self._on_finished is not None:
            self._on_finished()

    # -- resize: keep termqt + PTY in sync -----------------------------------

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        self._resize_pty()

    def _resize_pty(self) -> None:
        if self._session is None:
            return
        import contextlib

        # termqt: row_len = columns, col_len = rows. Before the widget is laid
        # out these are None/0; never push a non-positive size to the PTY (it
        # would make pi think the terminal is 0 rows and break cursor math).
        rows = self.col_len or 0
        cols = self.row_len or 0
        if rows <= 0 or cols <= 0:
            return
        with contextlib.suppress(Exception):
            self._session.resize(rows=rows, cols=cols)

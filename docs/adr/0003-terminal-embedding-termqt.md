# 0003 — Terminal embedding uses termqt + our own PTY

TWAT embeds terminals with `termqt` (a pure-Python VT100/XTerm emulator plus a
Qt renderer), fed by our own `PtySession` (`ptyprocess` on POSIX, `pywinpty` on
Windows in a later slice). We keep our own PTY layer rather than termqt's IO
backends because we need cwd and environment injection for the pi lifecycle
hook, which termqt's backends do not expose.

We rejected `qtermwidget` / C++ terminal bindings: they pull in KDE Frameworks
and are painful to package across macOS Apple Silicon, Windows x64/ARM64, and
Linux, where TWAT must ship as a self-contained bundle. We also rejected
hand-painting a `pyte` screen buffer cell-by-cell: it works, but reimplements a
renderer termqt already provides. `termqt` is pure Python, installs cleanly
everywhere (PySide6 via `qtpy`), and PyInstaller-bundles without C++ toolchain
pain.

The cost is that termqt has gaps and bugs that a full TUI like `pi` exercises.
We patch these in a `TermQtTerminal(Terminal)` subclass rather than forking
termqt, so upgrades stay cheap:

- **Char width** — termqt's widget sizes cells by the font's glyph advance, so
  a glyph the font draws wider than a cell (e.g. braille `⠙`) counts as 2
  columns. pi lays out with wcwidth (braille/box-drawing = 1 column), and that
  mismatch made every spinner/stream line wrap one extra row, so pi's relative
  cursor redraw clamped short and status/streaming lines stacked. We override
  `get_char_width` to use Unicode width (`unicodedata`) instead of the font.
- **Tab key** — Qt consumes Tab/Backtab for focus traversal before the widget's
  key handler, so a TUI never sees it; we intercept in `event()` and send `\t` /
  `ESC [ Z` to the PTY.
- **DECCKM (application cursor keys)** — termqt hardcodes normal-mode arrows; we
  override `keyPressEvent` to send `ESC O ...` when a TUI enables DECCKM
  (`ESC [ ? 1 h`) and revert on `ESC [ ? 1 l`.
- **Truecolor** — termqt's SGR parser omits `38;2;r;g;b` / `48;2;r;g;b`, which
  pi emits heavily; we replace the escape processor's `m` dispatch entry with a
  truecolor-aware parser.
- **DEC 2026 (Synchronized Output)** — termqt does not implement it, so it
  renders partial redraw frames; we buffer bytes between `?2026h` and `?2026l`
  and flush them atomically.
- **UTF-8 decode** — termqt's byte→buffer decode has an operator-precedence bug
  (`char & 0xc0 == 0xc0` binds as `char & (0xc0 == 0xc0)`), corrupting every
  multibyte glyph (pi's braille spinner, box-drawing) into several latin-1
  cells. That widened pi's full-width spinner line past the grid, so its
  cursor-relative redraw (`ESC[5A` … `ESC[5B`) drifted one row per frame and the
  "Working" status stacked downward. We override `_stdout_string` to decode
  UTF-8 by whole characters, carrying an incomplete trailing sequence to the
  next chunk so glyphs split across PTY reads survive too.

The PTY is spawned on the main thread before the reader thread starts (avoids
the multi-threaded `forkpty` deadlock warning); the reader thread only reads
bytes and emits them via a Qt signal, so the emulator is touched on the main
thread only. PTY size is kept in sync with termqt's actual grid (rows × cols),
not a fixed guess, so the program's line padding matches the rendered width.

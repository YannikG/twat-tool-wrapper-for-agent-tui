# 0003 — Terminal embedding uses ptyprocess + pyte + custom Qt render

TWAT embeds terminals with a `ptyprocess` PTY, a `pyte` terminal emulator, and
a custom Qt widget that paints the `pyte` screen buffer and encodes key events
back to bytes.

We rejected `qtermwidget` / C++ terminal bindings: they pull in KDE Frameworks
and are painful to package across macOS Apple Silicon, Windows x64/ARM64, and
Linux, where TWAT must ship as a self-contained bundle. `ptyprocess` + `pyte`
are pure Python, install cleanly everywhere, and PyInstaller-bundle without C++
toolchain pain.

The cost is the render widget: a full TUI like `pi` uses alt-screen, cursor
control, and colors, so a plain `QPlainTextEdit` would break it. We paint the
`pyte` buffer cell-by-cell (fg/bg/attributes/cursor). A spike confirmed a real
login shell echoes commands and alt-screen escape sequences are parsed
correctly.

The PTY is spawned on the main thread before the reader thread starts (avoids
the multi-threaded `forkpty` deadlock warning); the reader thread only reads
bytes and emits them via a Qt signal, and the emulator is touched on the main
thread only, so no locks are needed. Windows ConPTY (`pywinpty`) replaces
`ptyprocess` on Windows in a later slice.

# 0001 — In-window terminal embedding is a hard requirement

The `pi` terminal for every TWAT session must run embedded in the TWAT window's
right panel. There is no external-terminal fallback mode in v1.

We rejected spawning an OS terminal (Terminal.app / xterm / cmd) per session
because it re-creates the exact wrong-window hazard TWAT exists to prevent: the
typing surface would be a separate floating window, and the sidebar would
degrade into a launcher rather than a guardrail. Keeping the sidebar selection
and the terminal as one focused surface is the product's core safeguard.

This is the riskiest dependency in the project: a full TUI app like `pi` uses
alt-screen, cursor control, and color, so a naive `QPlainTextEdit` + raw PTY
bytes will break its rendering. A real terminal emulator (native widget or a
PTY + parser + renderer) is therefore required, not stdlib alone. That choice is
deferred to a later slice; slice 1 ships a placeholder.

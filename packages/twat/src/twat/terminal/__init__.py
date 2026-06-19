"""Terminal process + emulator adapters (Qt-free).

The process adapter (`pty_session`) wraps `ptyprocess`; the emulator wraps
`pyte`. Both must stay free of PySide6 imports (see architecture guardrails).
"""

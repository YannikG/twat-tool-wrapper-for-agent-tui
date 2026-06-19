"""Application entry point. Run with `python -m twat` or the `twat` script."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from twat.app.service import AppService
from twat.core.store import StateStore
from twat.ui.main_window import MainWindow
from twat.ui.theme import apply_theme


def config_dir() -> Path:
    """Platform config directory for TWAT state."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "twat"
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "twat"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "twat"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _configure_logging(log_file: Path) -> None:
    """Heavy logging: DEBUG to a file, INFO to stderr.

    Set TWAT_LOG_LEVEL=DEBUG to push stderr to debug too. Logs carry enough
    context (session ids, hook events, terminal lifecycle) that a failure
    report includes what happened before the error.
    """
    level = logging.getLevelName(os.environ.get("TWAT_LOG_LEVEL", "INFO").upper())
    root = logging.getLogger("twat")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(level)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    root.info("logging initialized; file=%s stderr-level=%s", log_file, logging.getLevelName(level))


def run() -> None:
    cfg = config_dir()
    _configure_logging(cfg / "twat.log")
    log = logging.getLogger("twat.main")
    log.info("TWAT starting; config dir=%s", cfg)

    app = QApplication(sys.argv)
    app.setApplicationName("TWAT")
    app.setStyle("Fusion")

    service = AppService(StateStore(cfg / "state.json"))
    apply_theme(app, service.settings.theme.value)

    window = MainWindow(service)
    window.show()
    log.info("TWAT window shown")
    sys.exit(app.exec())


if __name__ == "__main__":
    run()

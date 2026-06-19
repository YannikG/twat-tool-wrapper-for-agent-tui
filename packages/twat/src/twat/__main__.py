"""Application entry point. Run with `python -m twat` or the `twat` script."""

from __future__ import annotations

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


def run() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("TWAT")
    app.setStyle("Fusion")

    service = AppService(StateStore(config_dir() / "state.json"))
    apply_theme(app, service.settings.theme.value)

    window = MainWindow(service)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()

"""Application icon loading."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon


def app_icon() -> QIcon | None:
    """Return the TWAT window icon, or None if the asset is missing."""
    candidates = [Path(__file__).resolve().parent / "assets" / "icon.png"]
    meipass = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and meipass:
        candidates.insert(0, Path(meipass) / "twat" / "ui" / "assets" / "icon.png")
    for path in candidates:
        if path.is_file():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    return None

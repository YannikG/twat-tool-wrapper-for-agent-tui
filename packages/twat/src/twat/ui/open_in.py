"""Build the "Open in ..." menu: open a project folder in an editor/IDE/Finder.

Editors are detected by macOS app bundle (so VS Code, PyCharm, WebStorm, Rider
appear even without their CLI launchers) and by PATH CLI shim elsewhere.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

_log = logging.getLogger("twat.ui.open_in")

# macOS app bundle names. `open -a <name>` launches them whether or not a CLI
# shim is installed.
_MAC_APPS: list[tuple[str, str]] = [
    ("VS Code", "Visual Studio Code"),
    ("WebStorm", "WebStorm"),
    ("PyCharm", "PyCharm"),
    ("Rider", "Rider"),
]
# CLI shim names used off-macOS (and as a fallback on macOS).
_CLI_SHIMS: list[tuple[str, str]] = [
    ("VS Code", "code"),
    ("WebStorm", "webstorm"),
    ("PyCharm", "pycharm"),
    ("Rider", "rider"),
]


def _mac_app_available(app_name: str) -> bool:
    """True if the macOS app bundle is installed (in /Applications or ~/Applications)."""
    if sys.platform != "darwin":
        return False
    candidates = [
        Path("/Applications") / f"{app_name}.app",
        Path.home() / "Applications" / f"{app_name}.app",
    ]
    return any(c.exists() for c in candidates)


def _spawn(cmd: list[str], label: str) -> None:
    try:
        subprocess.Popen(cmd)
        _log.info("open-in %s -> %s", label, " ".join(cmd))
    except OSError as e:
        _log.warning("open-in %s failed: %s", label, e)


def open_in_targets() -> list[tuple[str, Callable[[str], None]]]:
    """Return (label, open_fn(cwd)) pairs for available targets.

    Successful launches are logged; launch failures are logged at WARNING.
    """
    targets: list[tuple[str, Callable[[str], None]]] = []

    def add_mac(label: str, app_name: str) -> None:
        def open_fn(cwd: str) -> None:
            _spawn(["open", "-a", app_name, cwd], label)

        targets.append((label, open_fn))

    def add_cli(label: str, shim: str) -> None:
        exe = shutil.which(shim)
        if exe is None:
            return

        def open_fn(cwd: str, s: str = shim) -> None:
            _spawn([s, cwd], label)

        targets.append((label, open_fn))

    if sys.platform == "darwin":
        for label, app in _MAC_APPS:
            if _mac_app_available(app):
                add_mac(label, app)
            else:
                add_cli(label, app.replace(" ", "").lower())
    else:
        for label, shim in _CLI_SHIMS:
            add_cli(label, shim)

    # Platform file manager + terminal (always available).
    if sys.platform == "darwin":
        targets.append(("Finder", lambda cwd: _spawn(["open", cwd], "Finder")))
        targets.append(
            ("Terminal", lambda cwd: _spawn(["open", "-a", "Terminal", cwd], "Terminal"))
        )
    elif os.name == "nt":
        targets.append(("Explorer", lambda cwd: _spawn(["explorer", cwd], "Explorer")))
        targets.append(
            (
                "Terminal",
                lambda cwd: _spawn(
                    ["cmd", "/c", "start", "cmd", "/k", "cd", "/d", cwd], "Terminal"
                ),
            )
        )
    else:
        targets.append(("Files", lambda cwd: _spawn(["xdg-open", cwd], "Files")))
        term = (
            os.environ.get("TERMINAL")
            or shutil.which("x-terminal-emulator")
            or shutil.which("gnome-terminal")
        )
        if term:
            targets.append(("Terminal", lambda cwd, t=term: _spawn([t, cwd], "Terminal")))

    return targets

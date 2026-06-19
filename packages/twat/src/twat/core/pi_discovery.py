"""Autodiscovery of the `pi` executable.

Searches PATH (via `shutil.which`) first, then common install locations.
Platform-aware. Used to prefill the `pi` path setting; the user can override
via the native file picker.
"""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path


def _is_executable(path: Path) -> bool:
    if sys.platform == "win32":
        return path.exists()
    return path.exists() and os.access(path, os.X_OK)


def _candidate_names() -> list[str]:
    if sys.platform == "win32":
        return ["pi.exe", "pi.cmd", "pi.bat", "pi"]
    return ["pi"]


def _default_search_dirs() -> list[Path]:
    home = Path.home()
    if sys.platform == "darwin":
        return [
            Path("/opt/homebrew/bin"),
            Path("/usr/local/bin"),
            home / ".local" / "bin",
        ]
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        local = os.environ.get("LOCALAPPDATA", "")
        dirs = [home / ".local" / "bin"]
        if appdata:
            dirs.append(Path(appdata) / "npm")
        if local:
            dirs.append(Path(local) / "pnpm")
        return dirs
    return [Path("/usr/local/bin"), Path("/usr/bin"), home / ".local" / "bin"]


def discover_pi(search_dirs: Sequence[Path] | None = None) -> str | None:
    """Find the `pi` executable.

    Tries PATH first, then the given (or default) search dirs. Returns the
    absolute path string, or None if not found.
    """
    found = shutil.which("pi")
    if found and _is_executable(Path(found)):
        return found

    dirs = list(search_dirs) if search_dirs is not None else _default_search_dirs()
    for d in dirs:
        if not d.exists():
            continue
        for name in _candidate_names():
            cand = d / name
            if _is_executable(cand):
                return str(cand)
    return None

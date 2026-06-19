"""Single-instance lock (Qt-free).

One TWAT per machine via a PID file in the config dir. Stale locks (dead PID)
are taken over on startup.
"""

from __future__ import annotations

import atexit
import contextlib
import os
from pathlib import Path


class InstanceLockError(RuntimeError):
    """Another live TWAT instance holds the lock."""


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _read_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


class InstanceLock:
    """Held for the app lifetime; released on quit or process exit."""

    def __init__(self, path: Path, pid: int) -> None:
        self._path = path
        self._pid = pid
        self._released = False
        atexit.register(self.release)

    @property
    def path(self) -> Path:
        return self._path

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        if _read_pid(self._path) == self._pid:
            with contextlib.suppress(OSError):
                self._path.unlink()


def acquire(config_dir: Path) -> InstanceLock:
    """Take the instance lock, or raise if another live TWAT holds it."""
    path = config_dir / "twat.lock"
    pid = os.getpid()
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            os.write(fd, f"{pid}\n".encode())
            os.close(fd)
            return InstanceLock(path, pid)
        except FileExistsError:
            other = _read_pid(path)
            if other == pid:
                return InstanceLock(path, pid)
            if other is None or not _pid_alive(other):
                with contextlib.suppress(OSError):
                    path.unlink()
                continue
            raise InstanceLockError(f"TWAT already running (pid {other})") from None

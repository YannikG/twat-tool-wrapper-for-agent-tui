"""PTY process adapter: a Qt-free wrapper over `ptyprocess` / `pywinpty`.

POSIX: `ptyprocess`. Windows: ConPTY via `pywinpty` (optional dependency on
win32). Spawns a command in a pseudo-terminal with cwd, env, and initial size.
"""

from __future__ import annotations

import contextlib
import os
import select
import signal
import sys
from collections.abc import Mapping
from typing import cast


class PtySession:
    """A running PTY child process."""

    def __init__(self, process: object, rows: int, cols: int) -> None:
        self._p = process
        self._rows = rows
        self._cols = cols

    @classmethod
    def spawn(
        cls,
        argv: list[str],
        *,
        cwd: str | os.PathLike[str],
        env: Mapping[str, str] | None = None,
        rows: int = 24,
        cols: int = 80,
    ) -> PtySession:
        env_dict = dict(env) if env is not None else None
        if sys.platform == "win32":
            from pywinpty import PtyProcess

            proc = PtyProcess.spawn(
                argv,
                cwd=str(cwd),
                env=env_dict,
                dimensions=(rows, cols),
            )
            return cls(proc, rows, cols)
        from ptyprocess import PtyProcess

        proc = PtyProcess.spawn(
            argv,
            cwd=str(cwd),
            env=env_dict,
            dimensions=(rows, cols),
        )
        return cls(proc, rows, cols)

    @property
    def pid(self) -> int:
        return int(self._p.pid)  # type: ignore[attr-defined]

    def is_alive(self) -> bool:
        with contextlib.suppress(Exception):
            return bool(self._p.isalive())  # type: ignore[attr-defined]
        return False

    def read(self, *, timeout: float = 0.0) -> bytes:
        """Read available bytes; blocks up to `timeout` seconds. Returns b'' if none."""
        if sys.platform == "win32":
            return self._read_win(timeout)
        fd = int(self._p.fd)  # type: ignore[attr-defined]
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            return b""
        with contextlib.suppress(EOFError):
            chunk = self._p.read()  # type: ignore[attr-defined]
            return chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
        return b""

    def _read_win(self, timeout: float) -> bytes:
        fd = self._p.fileno()  # type: ignore[attr-defined]
        if fd is not None and timeout >= 0:
            ready, _, _ = select.select([fd], [], [], timeout)
            if not ready:
                return b""
        try:
            chunk = self._p.read(4096)  # type: ignore[attr-defined]
        except EOFError:
            return b""
        if isinstance(chunk, str):
            return chunk.encode("utf-8")
        return cast(bytes, chunk)

    def write(self, data: bytes) -> None:
        if sys.platform == "win32":
            self._p.write(data.decode("utf-8", errors="surrogateescape"))  # type: ignore[attr-defined]
        else:
            self._p.write(data)  # type: ignore[attr-defined]

    def resize(self, *, rows: int, cols: int) -> None:
        self._rows, self._cols = rows, cols
        self._p.setwinsize(rows, cols)  # type: ignore[attr-defined]

    def close(self, *, force: bool = False) -> None:
        if sys.platform == "win32":
            with contextlib.suppress(Exception):
                self._p.terminate(force=force)  # type: ignore[attr-defined]
            with contextlib.suppress(Exception):
                self._p.close(force=force)  # type: ignore[attr-defined]
            return
        if force:
            with contextlib.suppress(Exception):
                self._p.terminate(force=True)  # type: ignore[attr-defined]
        else:
            with contextlib.suppress(OSError):
                self._p.terminate(force=False)  # type: ignore[attr-defined]
            if self.is_alive():
                with contextlib.suppress(OSError):
                    os.kill(self.pid, signal.SIGKILL)
        with contextlib.suppress(Exception):
            self._p.close()  # type: ignore[attr-defined]

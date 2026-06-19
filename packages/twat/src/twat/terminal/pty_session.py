"""PTY process adapter: a Qt-free wrapper over `ptyprocess`.

POSIX only for now (ptyprocess). Windows ConPTY (`pywinpty`) is a later slice.
Spawns a command in a pseudo-terminal with a cwd, env, and initial size; reads
non-blocking, writes input, resizes, and terminates.
"""

from __future__ import annotations

import contextlib
import os
import select
import signal
import sys
from collections.abc import Mapping


class PtySession:
    """A running PTY child process."""

    def __init__(self, process: object, rows: int, cols: int) -> None:
        self._p = process  # ptyprocess.PtyProcess
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
        if sys.platform == "win32":
            raise NotImplementedError("Windows PTY arrives in a later slice")
        from ptyprocess import PtyProcess  # type: ignore[import-untyped]

        proc = PtyProcess.spawn(
            argv,
            cwd=str(cwd),
            env=dict(env) if env is not None else None,
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
        fd = int(self._p.fd)  # type: ignore[attr-defined]
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            return b""
        with contextlib.suppress(EOFError):
            return self._p.read()  # type: ignore[attr-defined,no-any-return]
        return b""

    def write(self, data: bytes) -> None:
        self._p.write(data)  # type: ignore[attr-defined]

    def resize(self, *, rows: int, cols: int) -> None:
        self._rows, self._cols = rows, cols
        self._p.setwinsize(rows, cols)  # type: ignore[attr-defined]

    def close(self, *, force: bool = False) -> None:
        if force:
            with contextlib.suppress(Exception):
                self._p.terminate(force=True)  # type: ignore[attr-defined]
        else:
            # graceful: SIGHUP/SIGCONT/SIGINT via terminate, then force if alive
            with contextlib.suppress(OSError):
                self._p.terminate(force=False)  # type: ignore[attr-defined]
            if self.is_alive():
                with contextlib.suppress(OSError):
                    os.kill(self.pid, signal.SIGKILL)
        with contextlib.suppress(Exception):
            self._p.close()  # type: ignore[attr-defined]

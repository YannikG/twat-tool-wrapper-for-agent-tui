"""Real ProcessAdapter: one PTY per session, running the Launcher (shell + pi).

Qt-free. The Launcher (see CONTEXT.md) runs the user's login shell which runs
`pi`; on pi exit it drops to an interactive shell. The UI owns the terminal
widget that reads from these PTYs; this adapter only owns process lifecycle.
"""

from __future__ import annotations

import os
import shlex
import sys

from twat.app.process_adapter import ProcessAdapter  # noqa: F401  (re-exported)
from twat.terminal.pty_session import PtySession


def _launcher_command(pi_path: str, resume_file: str | None) -> list[str]:
    """Build the shell command that launches pi in the project folder.

    POSIX: login shell sources rc (so pi is on PATH), runs pi, drops to an
    interactive shell on pi exit. Windows: cmd stub (refined later).
    """
    if sys.platform == "win32":
        if resume_file:
            return ["cmd.exe", "/c", f'"{pi_path}" --resume "{resume_file}"']
        return ["cmd.exe", "/c", f'"{pi_path}"']
    shell = os.environ.get("SHELL") or "/bin/bash"
    if resume_file:
        pi_arg = f"{shlex.quote(pi_path)} --resume {shlex.quote(resume_file)}"
    else:
        pi_arg = shlex.quote(pi_path)
    # run pi; on exit, exec into an interactive shell so output stays visible
    script = f"{pi_arg}; exec {shlex.quote(shell)}"
    return [shell, "-lc", script]


class PiProcessAdapter:
    """ProcessAdapter backed by PTY sessions, one per session id."""

    def __init__(self, pi_path: str) -> None:
        self._pi_path = pi_path
        self._sessions: dict[str, PtySession] = {}

    def pty(self, session_id: str) -> PtySession | None:
        return self._sessions.get(session_id)

    def start(self, session_id: str, cwd: str, resume_file: str | None) -> None:
        self.stop(session_id)
        argv = _launcher_command(self._pi_path, resume_file)
        env = dict(os.environ)
        self._sessions[session_id] = PtySession.spawn(argv, cwd=cwd, env=env)

    def stop(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.close(force=False)
            del self._sessions[session_id]

    def terminate(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.close(force=True)
            del self._sessions[session_id]

    def is_alive(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        return session is not None and session.is_alive()

    def stop_all(self) -> None:
        for sid in list(self._sessions):
            self.stop(sid)

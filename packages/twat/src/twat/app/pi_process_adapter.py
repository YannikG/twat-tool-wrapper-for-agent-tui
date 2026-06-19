"""Real ProcessAdapter: one PTY per session, running the Launcher (shell + pi).

Qt-free. The Launcher (see CONTEXT.md) runs the user's login shell which runs
`pi`; on pi exit it drops to an interactive shell. The UI owns the terminal
widget that reads from these PTYs; this adapter only owns process lifecycle.
"""

from __future__ import annotations

import os
import shlex
import sys
from collections.abc import Mapping

from twat.app.process_adapter import ProcessAdapter  # noqa: F401  (re-exported)
from twat.hook.generator import needs_update, write_hook
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
    pi_arg = (
        shlex.quote(pi_path)
        if not resume_file
        else (f"{shlex.quote(pi_path)} --resume {shlex.quote(resume_file)}")
    )
    # Run pi directly; the PTY closes when pi exits, so TWAT detects exit cleanly.
    # (Earlier design dropped to an interactive shell after pi exit, but that left
    # an orphan shell alive while the session was "exited" — confusing. Removed.)
    return [shell, "-lc", pi_arg]


class PiProcessAdapter:
    """ProcessAdapter backed by PTY sessions, one per session id."""

    def __init__(self, pi_path: str, *, version: str) -> None:
        self._pi_path = pi_path
        self._version = version
        # per-session TWAT_HOOK_* env, set before each start and consumed at start
        self._hook_env_by_session: dict[str, dict[str, str]] = {}
        self._sessions: dict[str, PtySession] = {}

    def set_hook_env_for(self, session_id: str, env: Mapping[str, str]) -> None:
        """Set the TWAT_HOOK_* env for a specific session's upcoming start."""
        self._hook_env_by_session[session_id] = dict(env)

    def pty(self, session_id: str) -> PtySession | None:
        return self._sessions.get(session_id)

    def start(self, session_id: str, cwd: str, resume_file: str | None) -> None:
        self.stop(session_id)
        # generate / refresh the twat-hook extension in the project (idempotent)
        if needs_update(cwd, self._version):
            write_hook(cwd, self._version)
        argv = _launcher_command(self._pi_path, resume_file)
        env = dict(os.environ)
        env.update(self._hook_env_by_session.get(session_id, {}))
        self._sessions[session_id] = PtySession.spawn(argv, cwd=cwd, env=env)
        # consume the one-shot env
        self._hook_env_by_session.pop(session_id, None)

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

"""Application service: the UI's entry point into core + storage.

Qt-free. The UI calls these methods and re-renders; no signals here yet (no
second consumer needs live updates in slice 1).
"""

from __future__ import annotations

from pathlib import Path

from twat.app.process_adapter import ProcessAdapter
from twat.core.pi_discovery import discover_pi
from twat.core.project import Project, ProjectExistsError, create_project
from twat.core.session import Session, SessionState, create_session
from twat.core.settings import Settings, Theme
from twat.core.store import StateStore

__all__ = ["AppService", "ProjectExistsError"]


class _NoopProcessAdapter:
    """Default adapter: no process control until the UI injects a real one."""

    def start(self, session_id: str, cwd: str, resume_file: str | None) -> None:
        pass

    def stop(self, session_id: str) -> None:
        pass

    def terminate(self, session_id: str) -> None:
        pass

    def is_alive(self, session_id: str) -> bool:
        return False


class AppService:
    """Owns in-memory state and persists changes through the store."""

    def __init__(self, store: StateStore) -> None:
        self._store = store
        self._state = store.load()
        # On reload, any session that was `starting`/`running` did not survive
        # restart; normalize to exited.
        self._state.sessions = [
            s.with_state(SessionState.EXITED)
            if s.state in (SessionState.STARTING, SessionState.RUNNING)
            else s
            for s in self._state.sessions
        ]
        self.process_adapter: ProcessAdapter = _NoopProcessAdapter()
        self._prefill_pi_path()

    @property
    def projects(self) -> list[Project]:
        return list(self._state.projects)

    @property
    def settings(self) -> Settings:
        return self._state.settings

    def add_project(self, path: str | Path, name: str | None = None) -> Project:
        """Register a project folder; reject duplicate (resolved) paths."""
        resolved = str(Path(path).expanduser().resolve())
        if any(p.path == resolved for p in self._state.projects):
            raise ProjectExistsError(resolved)
        project = create_project(resolved, name)
        self._state.projects.append(project)
        self._save()
        return project

    def set_theme(self, theme: Theme) -> None:
        self._state.settings.theme = theme
        self._save()

    def set_pi_path(self, path: str) -> None:
        self._state.settings.pi_path = path
        self._save()

    # -- sessions -----------------------------------------------------------

    def sessions_for(self, project_id: str) -> list[Session]:
        return [s for s in self._state.sessions if s.project_id == project_id]

    def get_session(self, session_id: str) -> Session:
        for s in self._state.sessions:
            if s.id == session_id:
                return s
        raise KeyError(session_id)

    def new_session(self, project_id: str, name: str | None = None) -> Session:
        session = create_session(project_id, name)
        self._state.sessions.append(session)
        self._save()
        return session

    def start_session(self, session_id: str) -> None:
        session = self.get_session(session_id)
        project = next((p for p in self._state.projects if p.id == session.project_id), None)
        if project is None:
            raise KeyError(session.project_id)
        self._replace(session.with_state(SessionState.STARTING))
        self.process_adapter.start(session_id, project.path, session.bound_file)
        self._replace(session.with_state(SessionState.RUNNING))

    def stop_session(self, session_id: str) -> None:
        self.process_adapter.stop(session_id)
        self._replace(self.get_session(session_id).with_state(SessionState.EXITED))

    def terminate_session(self, session_id: str) -> None:
        self.process_adapter.terminate(session_id)
        self._replace(self.get_session(session_id).with_state(SessionState.FAILED))

    def _set_session_bound_file(self, session_id: str, path: str) -> None:
        """Internal seam for the hook to report a binding (slice 4)."""
        self._replace(self.get_session(session_id).with_bound_file(path))

    def _set_session_name(self, session_id: str, name: str) -> None:
        """Internal seam for the hook to report a name (slice 4)."""
        self._replace(self.get_session(session_id).with_name(name))

    def _set_session_agent_activity(self, session_id: str, activity: str) -> None:
        """Internal seam for the hook to report agent activity (slice 4)."""
        self._replace(self.get_session(session_id).with_agent_activity(activity))

    def mark_session_exited(self, session_id: str) -> None:
        """Mark a session exited (idempotent) without touching the PTY.

        Used by the hook's session_shutdown event; the reader's finished signal
        owns actual terminal teardown.
        """
        sess = self.get_session(session_id)
        if sess.state is SessionState.EXITED:
            return
        self._replace(sess.with_state(SessionState.EXITED))

    def _replace(self, session: Session) -> None:
        for i, s in enumerate(self._state.sessions):
            if s.id == session.id:
                self._state.sessions[i] = session
                self._save()
                return
        raise KeyError(session.id)

    def _prefill_pi_path(self) -> None:
        if self._state.settings.pi_path:
            return
        found = discover_pi()
        if found:
            self._state.settings.pi_path = found
            self._save()

    def _save(self) -> None:
        self._store.save(self._state)

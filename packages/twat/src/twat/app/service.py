"""Application service: the UI's entry point into core + storage.

Qt-free. The UI calls these methods and re-renders; no signals here yet (no
second consumer needs live updates in slice 1).
"""

from __future__ import annotations

import logging
from pathlib import Path

from twat.app.process_adapter import ProcessAdapter
from twat.core.pi_discovery import discover_pi
from twat.core.project import Project, ProjectExistsError, create_project
from twat.core.session import Session, SessionState, create_session
from twat.core.settings import Settings, Theme
from twat.core.store import StateStore

__all__ = ["AppService", "ProjectExistsError", "SessionActiveError"]

_log = logging.getLogger("twat.service")


class SessionActiveError(RuntimeError):
    """Raised when a destructive op targets a still-running session."""


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

    # -- projects -----------------------------------------------------------

    def rename_project(self, project_id: str, name: str) -> None:
        """Set a project's display name. The folder path is never touched."""
        name = name.strip()
        if not name:
            raise ValueError("project name must not be empty")
        for i, p in enumerate(self._state.projects):
            if p.id == project_id:
                self._state.projects[i] = Project(id=p.id, path=p.path, name=name)
                self._save()
                _log.info("renamed project %s -> %r", project_id, name)
                return
        raise KeyError(project_id)

    # -- sessions -----------------------------------------------------------

    def sessions_for(self, project_id: str) -> list[Session]:
        return [s for s in self._state.sessions if s.project_id == project_id]

    def sessions_for_all(self) -> list[Session]:
        return list(self._state.sessions)

    def get_session(self, session_id: str) -> Session:
        for s in self._state.sessions:
            if s.id == session_id:
                return s
        raise KeyError(session_id)

    def new_session(self, project_id: str, name: str | None = None) -> Session:
        session = create_session(project_id, name)
        self._state.sessions.append(session)
        self._save()
        _log.info("new session id=%s project=%s name=%r", session.id, project_id, session.name)
        return session

    def start_session(self, session_id: str) -> None:
        session = self.get_session(session_id)
        project = next((p for p in self._state.projects if p.id == session.project_id), None)
        if project is None:
            _log.error("start: project not found for session %s", session_id)
            raise KeyError(session.project_id)
        _log.info("start session %s in %s resume=%s", session_id, project.path, session.bound_file)
        self._replace(session.with_state(SessionState.STARTING))
        self.process_adapter.start(session_id, project.path, session.bound_file)
        self._replace(session.with_state(SessionState.RUNNING))

    def stop_session(self, session_id: str) -> None:
        _log.info("stop session %s", session_id)
        self.process_adapter.stop(session_id)
        self._replace(self.get_session(session_id).with_state(SessionState.EXITED))

    def terminate_session(self, session_id: str) -> None:
        _log.warning("terminate session %s", session_id)
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

    # -- archive / restore --------------------------------------------------

    def archive_session(self, session_id: str) -> None:
        """Hide a session from the active sidebar under the archive.

        If it is running/starting, Stop it gracefully first (wait for the
        process to end), then set the archived flag. The pi Session conversation
        file is untouched. Never launches pi.
        """
        sess = self.get_session(session_id)
        _log.info("archive session %s state=%s", session_id, sess.state)
        if sess.state in (SessionState.RUNNING, SessionState.STARTING):
            self.stop_session(session_id)
        self._replace(self.get_session(session_id).with_archived(True))

    def restore_session(self, session_id: str) -> None:
        """Un-archive a stopped session so it reappears in the active sidebar.

        Does NOT launch pi; the user Starts to resume the conversation.
        """
        _log.info("restore session %s", session_id)
        self._replace(self.get_session(session_id).with_archived(False))

    # -- delete -------------------------------------------------------------

    def delete_session(self, session_id: str) -> None:
        """Permanently remove a stopped session record from TWAT's state.

        The pi Session conversation file (owned by pi) is NEVER touched; only
        TWAT metadata is removed. Refuses a running/starting session — Stop or
        Terminate first. Destructive: a deleted session cannot be Restored.
        """
        sess = self.get_session(session_id)
        if sess.state in (SessionState.RUNNING, SessionState.STARTING):
            raise SessionActiveError(
                f"session {session_id} is {sess.state.value}; stop it before deleting"
            )
        _log.info("delete session %s (metadata only; conversation file kept)", session_id)
        self._state.sessions = [s for s in self._state.sessions if s.id != session_id]
        self._save()

    def delete_project(self, project_id: str) -> None:
        """Permanently remove a project and all its sessions from TWAT's state.

        Running sessions are gracefully Stopped first. The on-disk folder and
        pi Session conversation files are NEVER touched; only TWAT metadata is
        removed. The folder can be re-added later.
        """
        if project_id not in {p.id for p in self._state.projects}:
            raise KeyError(project_id)
        sessions = self.sessions_for(project_id)
        for s in sessions:
            if s.state in (SessionState.RUNNING, SessionState.STARTING):
                _log.info("delete_project: stopping running session %s first", s.id)
                self.stop_session(s.id)
        _log.info(
            "delete project %s + %d session(s) (metadata only; files kept)",
            project_id,
            len(sessions),
        )
        self._state.sessions = [s for s in self._state.sessions if s.project_id != project_id]
        self._state.projects = [p for p in self._state.projects if p.id != project_id]
        self._save()

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

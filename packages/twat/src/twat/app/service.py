"""Application service: the UI's entry point into core + storage.

Qt-free. The UI calls these methods and re-renders; no signals here yet (no
second consumer needs live updates in slice 1).
"""

from __future__ import annotations

from pathlib import Path

from twat.core.pi_discovery import discover_pi
from twat.core.project import Project, ProjectExistsError, create_project
from twat.core.settings import Settings, Theme
from twat.core.store import StateStore

__all__ = ["AppService", "ProjectExistsError"]


class AppService:
    """Owns in-memory state and persists changes through the store."""

    def __init__(self, store: StateStore) -> None:
        self._store = store
        self._state = store.load()
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

    def _prefill_pi_path(self) -> None:
        if self._state.settings.pi_path:
            return
        found = discover_pi()
        if found:
            self._state.settings.pi_path = found
            self._save()

    def _save(self) -> None:
        self._store.save(self._state)

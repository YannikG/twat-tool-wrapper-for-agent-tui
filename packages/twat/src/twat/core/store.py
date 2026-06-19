"""JSON state file persistence.

A single JSON file in the platform config directory, written atomically
(temp file + rename). Stdlib `json` only. See
`docs/specs/platform/persistence.md`.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from twat.core.project import Project
from twat.core.settings import Settings


@dataclass
class State:
    """All persisted TWAT state."""

    projects: list[Project] = field(default_factory=list)
    settings: Settings = field(default_factory=Settings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "projects": [p.to_dict() for p in self.projects],
            "settings": self.settings.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> State:
        projects = [Project.from_dict(p) for p in data.get("projects", [])]
        settings_data = data.get("settings")
        if isinstance(settings_data, dict):
            settings = Settings.from_dict(settings_data)
        else:
            settings = Settings()
        return cls(projects=projects, settings=settings)


class StateStore:
    """Loads and atomically saves the state file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> State:
        """Load state; a missing or corrupt file yields empty state."""
        if not self._path.exists():
            return State()
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return State()
        if not isinstance(data, dict):
            return State()
        return State.from_dict(data)

    def save(self, state: State) -> None:
        """Atomically write state (temp file in same dir, then rename)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state.to_dict(), indent=2)
        # ponytail: os.replace is atomic on the same filesystem; temp in same dir.
        fd, tmp = tempfile.mkstemp(dir=self._path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp, self._path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

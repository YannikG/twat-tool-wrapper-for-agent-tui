"""Project core model.

A Project is a filesystem folder the user runs `pi` sessions in. Name defaults
to the folder basename; the user can override the display name at creation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ProjectExistsError(Exception):
    """Raised when adding a Project whose folder path is already registered."""


@dataclass(frozen=True)
class Project:
    """A registered project folder."""

    id: str
    path: str  # absolute, resolved folder path
    name: str  # display name (defaults to folder basename)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "path": self.path, "name": self.name}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Project:
        return cls(id=str(data["id"]), path=str(data["path"]), name=str(data["name"]))


def suggest_name(path: str | Path) -> str:
    """Default project name: the folder basename."""
    return Path(path).name


def create_project(path: str | Path, name: str | None = None) -> Project:
    """Create a Project from a folder path, defaulting the name to basename."""
    resolved = str(Path(path).expanduser().resolve())
    return Project(id=uuid.uuid4().hex, path=resolved, name=name or suggest_name(resolved))

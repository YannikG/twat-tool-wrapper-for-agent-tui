"""Session core model.

A Session is a TWAT-owned runtime handle wrapping a `pi` process, bound to a
Project. See CONTEXT.md (Session, Binding, Session state). Immutable value
object; state changes return new instances.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class SessionState(StrEnum):
    """Life of the TWAT session's pi process handle."""

    STARTING = "starting"
    RUNNING = "running"
    EXITED = "exited"
    FAILED = "failed"


@dataclass(frozen=True)
class Session:
    """A TWAT session: a pi process handle + metadata, bound to a project."""

    id: str
    project_id: str
    name: str
    state: SessionState
    bound_file: str | None = None  # pi Session file; None until the hook reports it

    def with_state(self, state: SessionState) -> Session:
        return Session(
            id=self.id,
            project_id=self.project_id,
            name=self.name,
            state=state,
            bound_file=self.bound_file,
        )

    def with_bound_file(self, path: str) -> Session:
        return Session(
            id=self.id,
            project_id=self.project_id,
            name=self.name,
            state=self.state,
            bound_file=path,
        )

    def with_name(self, name: str) -> Session:
        return Session(
            id=self.id,
            project_id=self.project_id,
            name=name,
            state=self.state,
            bound_file=self.bound_file,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "state": self.state.value,
            "bound_file": self.bound_file,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        return cls(
            id=str(data["id"]),
            project_id=str(data["project_id"]),
            name=str(data["name"]),
            state=SessionState(str(data["state"])),
            bound_file=data.get("bound_file"),
        )


def create_session(project_id: str, name: str | None = None) -> Session:
    """Create a Session in `exited` state, unbound. Does not launch pi."""
    return Session(
        id=uuid.uuid4().hex,
        project_id=project_id,
        name=name or "New session",
        state=SessionState.EXITED,
        bound_file=None,
    )

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
    agent_activity: str = "idle"  # "idle" | "working"; ephemeral, from hook events
    archived: bool = False  # orthogonal to state; hides from active sidebar

    def with_state(self, state: SessionState) -> Session:
        return Session(
            id=self.id,
            project_id=self.project_id,
            name=self.name,
            state=state,
            bound_file=self.bound_file,
            agent_activity=self.agent_activity,
        )

    def with_bound_file(self, path: str) -> Session:
        return Session(
            id=self.id,
            project_id=self.project_id,
            name=self.name,
            state=self.state,
            bound_file=path,
            agent_activity=self.agent_activity,
        )

    def with_name(self, name: str) -> Session:
        return Session(
            id=self.id,
            project_id=self.project_id,
            name=name,
            state=self.state,
            bound_file=self.bound_file,
            agent_activity=self.agent_activity,
        )

    def with_agent_activity(self, activity: str) -> Session:
        return Session(
            id=self.id,
            project_id=self.project_id,
            name=self.name,
            state=self.state,
            bound_file=self.bound_file,
            agent_activity=activity,
            archived=self.archived,
        )

    def with_archived(self, archived: bool) -> Session:
        return Session(
            id=self.id,
            project_id=self.project_id,
            name=self.name,
            state=self.state,
            bound_file=self.bound_file,
            agent_activity=self.agent_activity,
            archived=archived,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "state": self.state.value,
            "bound_file": self.bound_file,
            "agent_activity": self.agent_activity,
            "archived": self.archived,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        return cls(
            id=str(data["id"]),
            project_id=str(data["project_id"]),
            name=str(data["name"]),
            state=SessionState(str(data["state"])),
            bound_file=data.get("bound_file"),
            agent_activity=str(data.get("agent_activity", "idle")),
            archived=bool(data.get("archived", False)),
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

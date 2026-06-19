"""User settings (v1: theme + pi executable path)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Theme(StrEnum):
    """UI color theme."""

    DARK = "dark"
    LIGHT = "light"


@dataclass
class Settings:
    """The only two v1 settings."""

    theme: Theme = Theme.DARK
    pi_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"theme": self.theme.value, "pi_path": self.pi_path}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Settings:
        theme = Theme(str(data.get("theme", Theme.DARK.value)))
        return cls(theme=theme, pi_path=str(data.get("pi_path", "")))

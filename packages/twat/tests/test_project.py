"""Tests for the Project core model."""

from pathlib import Path

from twat.core.project import create_project, suggest_name


def test_suggest_name_is_folder_basename() -> None:
    assert suggest_name("/home/me/cool-project") == "cool-project"


def test_create_project_defaults_name_to_basename() -> None:
    proj = create_project("/home/me/cool-project")

    assert proj.name == "cool-project"
    assert proj.path == str(Path("/home/me/cool-project").resolve())
    assert proj.id  # non-empty


def test_create_project_accepts_custom_name() -> None:
    proj = create_project("/home/me/cool-project", name="My Cool Project")

    assert proj.name == "My Cool Project"


def test_create_project_has_unique_ids() -> None:
    a = create_project("/home/me/a")
    b = create_project("/home/me/b")

    assert a.id != b.id

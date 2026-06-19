"""Tests for the twat-hook.ts generator."""

from pathlib import Path

from twat.hook.generator import (
    HOOK_FILENAME,
    hook_path,
    needs_update,
    render_hook,
    write_hook,
)


def test_render_hook_has_version_header() -> None:
    src = render_hook(version="0.1.0")

    assert "// @twat-version 0.1.0" in src
    assert ".pi/extensions/twat-hook.ts" in src or "twat-hook" in src


def test_render_hook_reads_env_at_runtime() -> None:
    src = render_hook(version="0.1.0")

    # port/token/session come from env, not baked in
    assert "TWAT_HOOK_PORT" in src
    assert "TWAT_HOOK_TOKEN" in src
    assert "TWAT_SESSION_ID" in src


def test_render_hook_emits_lifecycle_events() -> None:
    src = render_hook(version="0.1.0")

    assert "session_start" in src
    assert "agent_start" in src
    assert "agent_end" in src
    assert "turn_end" in src
    assert "session_shutdown" in src


def test_render_hook_posts_to_localhost() -> None:
    src = render_hook(version="0.1.0")

    assert "127.0.0.1" in src
    assert "fetch" in src


def test_render_hook_ignores_errors() -> None:
    src = render_hook(version="0.1.0")

    # failures must be swallowed so direct pi use is never broken
    assert "catch" in src


def test_hook_path_is_in_project_extensions(tmp_path: Path) -> None:
    p = hook_path(str(tmp_path))

    assert p == tmp_path / ".pi" / "extensions" / HOOK_FILENAME


def test_needs_update_when_missing(tmp_path: Path) -> None:
    assert needs_update(str(tmp_path), "0.1.0") is True


def test_needs_update_false_when_version_matches(tmp_path: Path) -> None:
    write_hook(str(tmp_path), "0.1.0")

    assert needs_update(str(tmp_path), "0.1.0") is False


def test_needs_update_true_when_version_differs(tmp_path: Path) -> None:
    write_hook(str(tmp_path), "0.0.9")

    assert needs_update(str(tmp_path), "0.1.0") is True


def test_write_hook_is_idempotent(tmp_path: Path) -> None:
    write_hook(str(tmp_path), "0.1.0")
    first = hook_path(str(tmp_path)).read_text()

    write_hook(str(tmp_path), "0.1.0")
    second = hook_path(str(tmp_path)).read_text()

    assert first == second


def test_write_hook_creates_directories(tmp_path: Path) -> None:
    write_hook(str(tmp_path), "0.1.0")

    assert hook_path(str(tmp_path)).exists()

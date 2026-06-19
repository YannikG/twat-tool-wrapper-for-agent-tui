"""Tests for `pi` executable autodiscovery."""

import sys
from pathlib import Path

import pytest

from twat.core.pi_discovery import discover_pi


def _make_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)


@pytest.fixture(autouse=True)
def _no_pi_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Don't let a real `pi` on PATH interfere with these tests."""
    monkeypatch.setattr("twat.core.pi_discovery.shutil.which", lambda _cmd: None)


def test_discover_pi_finds_executable_in_search_dir(tmp_path: Path) -> None:
    _make_executable(tmp_path / "pi")

    assert discover_pi(search_dirs=[tmp_path]) == str(tmp_path / "pi")


def test_discover_pi_returns_none_when_not_found(tmp_path: Path) -> None:
    assert discover_pi(search_dirs=[tmp_path]) is None


def test_discover_pi_ignores_non_executable(tmp_path: Path) -> None:
    (tmp_path / "pi").write_text("not executable", encoding="utf-8")  # no +x

    if sys.platform == "win32":
        pytest.skip("exec bit not meaningful on Windows")
    assert discover_pi(search_dirs=[tmp_path]) is None


def test_discover_pi_prefers_path_over_search_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_executable(tmp_path / "pi")
    monkeypatch.setattr(
        "twat.core.pi_discovery.shutil.which",
        lambda _cmd: "/from/path/pi",
    )
    monkeypatch.setattr(
        "twat.core.pi_discovery._is_executable",
        lambda _p: True,
    )

    assert discover_pi(search_dirs=[tmp_path]) == "/from/path/pi"


def test_discover_pi_handles_missing_search_dir(tmp_path: Path) -> None:
    # a non-existent dir must not raise
    assert discover_pi(search_dirs=[tmp_path / "nope"]) is None

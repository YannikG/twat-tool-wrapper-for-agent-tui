"""Tests for the single-instance PID lock."""

import os
from pathlib import Path

import pytest

from twat.core.instance_lock import InstanceLockError, acquire


def test_acquire_creates_lock_file(tmp_path: Path) -> None:
    lock = acquire(tmp_path)
    try:
        assert lock.path.exists()
        assert lock.path.read_text(encoding="utf-8").strip() == str(os.getpid())
    finally:
        lock.release()


def test_second_acquire_fails_when_other_pid_alive(tmp_path: Path, monkeypatch) -> None:
    other = 424242
    (tmp_path / "twat.lock").write_text(f"{other}\n", encoding="utf-8")
    monkeypatch.setattr("twat.core.instance_lock._pid_alive", lambda pid: pid == other)
    with pytest.raises(InstanceLockError, match="already running"):
        acquire(tmp_path)


def test_stale_lock_is_replaced(tmp_path: Path) -> None:
    stale = tmp_path / "twat.lock"
    stale.write_text("999999\n", encoding="utf-8")
    lock = acquire(tmp_path)
    try:
        assert lock.path.read_text(encoding="utf-8").strip() == str(os.getpid())
    finally:
        lock.release()


def test_release_allows_reacquire(tmp_path: Path) -> None:
    first = acquire(tmp_path)
    first.release()
    second = acquire(tmp_path)
    second.release()

"""Qt-free tests for the PTY process adapter (uses a real /bin/sh)."""

import sys
import time

import pytest

from twat.terminal.pty_session import PtySession


def _wait_for(session: PtySession, needle: bytes, timeout: float = 3.0) -> bytes:
    """Drain output until needle appears or timeout."""
    buf = b""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        chunk = session.read(timeout=0.2)
        if chunk:
            buf += chunk
            if needle in buf:
                break
    return buf


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX PTY only for now")
def test_spawn_runs_command_and_outputs(tmp_path) -> None:
    session = PtySession.spawn(["/bin/sh", "-c", "echo hello-twats; exit 0"], cwd=tmp_path)

    try:
        out = _wait_for(session, b"hello-twats")
        assert b"hello-twats" in out
    finally:
        session.close(force=True)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX PTY only for now")
def test_write_is_echoed_back_by_cat(tmp_path) -> None:
    session = PtySession.spawn(["/bin/cat"], cwd=tmp_path)
    try:
        # wait for shell readiness not needed; cat echoes stdin
        session.write(b"ping\n")
        out = _wait_for(session, b"ping")
        assert b"ping" in out
    finally:
        session.close(force=True)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX PTY only for now")
def test_terminate_stops_process(tmp_path) -> None:
    session = PtySession.spawn(["/bin/sleep", "3600"], cwd=tmp_path)
    try:
        assert session.is_alive()
    finally:
        session.close(force=True)

    assert not session.is_alive()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX PTY only for now")
def test_resize_does_not_raise(tmp_path) -> None:
    session = PtySession.spawn(["/bin/sh", "-c", "sleep 1"], cwd=tmp_path, rows=24, cols=80)
    try:
        session.resize(rows=30, cols=100)
    finally:
        session.close(force=True)

"""Tests for the pi launcher command builder (Qt-free)."""

from __future__ import annotations

import shlex
import sys

from twat.app.pi_process_adapter import _launcher_command


def _pi_arg(argv: list[str]) -> str:
    """Pull the `pi ...` argument string out of the launcher argv (POSIX)."""
    # argv == [shell, "-lc", "<pi arg>"]
    assert argv[0:2] == ["_shell_check"]
    return argv[2]


def _posix_argv(pi_arg: str) -> list[str]:
    return ["_shell_check", "-lc", pi_arg]


def test_unbound_session_launches_plain_pi(monkeypatch) -> None:
    monkeypatch.setenv("SHELL", "/bin/bash")
    argv = _launcher_command("/opt/homebrew/bin/pi", None)
    assert argv[0:2] == ["/bin/bash", "-lc"]
    assert argv[2] == shlex.quote("/opt/homebrew/bin/pi")


def test_bound_session_uses_session_flag_not_resume(monkeypatch) -> None:
    monkeypatch.setenv("SHELL", "/bin/bash")
    argv = _launcher_command("/opt/homebrew/bin/pi", "/path/to/sess.jsonl")
    pi_arg = argv[2]

    # `pi --resume` ignores a file arg and shows a picker; we must use
    # `pi --session <path>` to resume an exact file directly.
    assert "--resume" not in pi_arg
    assert "--session" in pi_arg
    assert "/path/to/sess.jsonl" in pi_arg


def test_bound_session_paths_are_shell_quoted(monkeypatch) -> None:
    monkeypatch.setenv("SHELL", "/bin/bash")
    argv = _launcher_command("/opt/homebrew/bin/pi", "/path with space/s.jsonl")
    pi_arg = argv[2]

    # the space must be quoted so the shell doesn't split it
    assert "/path with space/s.jsonl" not in pi_arg.split()  # not bare
    assert "'/path with space/s.jsonl'" in pi_arg


def test_windows_bound_uses_session_flag(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    argv = _launcher_command("C:\\pi.exe", "C:\\sess.jsonl")
    assert argv == ["C:\\pi.exe", "--session", "C:\\sess.jsonl"]


def test_windows_unbound_launches_plain_pi(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    argv = _launcher_command("C:\\pi.exe", None)
    assert argv == ["C:\\pi.exe"]

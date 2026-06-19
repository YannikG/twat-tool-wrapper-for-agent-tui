"""Tests for the hook HTTP listener and event dispatcher."""

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from twat.hook.listener import HookListener


def _post(port: int, token: str, body: dict[str, object]) -> int:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/hook",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Twat-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def test_listener_starts_on_ephemeral_port() -> None:
    listener = HookListener(token="t", on_event=lambda _e: None)
    listener.start()
    try:
        assert listener.port > 0
    finally:
        listener.stop()


def test_listener_accepts_valid_token_event() -> None:
    received: list[dict[str, object]] = []
    listener = HookListener(token="secret", on_event=lambda e: received.append(e))
    listener.start()
    try:
        status = _post(listener.port, "secret", {"type": "session_start", "sessionId": "s1"})
        assert status == 200
        # give the handler a moment
        import time

        time.sleep(0.1)
        assert any(e.get("type") == "session_start" for e in received)
    finally:
        listener.stop()


def test_listener_rejects_wrong_token() -> None:
    listener = HookListener(token="secret", on_event=lambda _e: None)
    listener.start()
    try:
        status = _post(listener.port, "wrong", {"type": "session_start"})
        assert status == 401
    finally:
        listener.stop()


def test_listener_rejects_missing_token() -> None:
    listener = HookListener(token="secret", on_event=lambda _e: None)
    listener.start()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{listener.port}/hook",
            data=json.dumps({"type": "session_start"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req, timeout=2)
        assert exc.value.code == 401
    finally:
        listener.stop()


def test_listener_bad_json_returns_400() -> None:
    listener = HookListener(token="secret", on_event=lambda _e: None)
    listener.start()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{listener.port}/hook",
            data=b"{not json",
            headers={"Content-Type": "application/json", "X-Twat-Token": "secret"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req, timeout=2)
        assert exc.value.code == 400
    finally:
        listener.stop()


def test_listener_stop_is_idempotent() -> None:
    listener = HookListener(token="t", on_event=lambda _e: None)
    listener.start()
    listener.stop()
    listener.stop()  # no error


_ = Path  # silence unused import linter across envs
_ = threading

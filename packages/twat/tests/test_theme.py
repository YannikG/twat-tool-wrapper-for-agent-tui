"""Tests for theme token -> QSS rendering."""

from twat.ui.theme import render_qss


def test_render_qss_dark_is_nonempty_and_resolved() -> None:
    qss = render_qss("dark")

    assert qss.strip()
    assert "$" not in qss  # every token placeholder resolved


def test_render_qss_light_is_nonempty_and_resolved() -> None:
    qss = render_qss("light")

    assert qss.strip()
    assert "$" not in qss


def test_dark_and_light_differ() -> None:
    assert render_qss("dark") != render_qss("light")

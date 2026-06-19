"""Smoke test: the package imports and exposes its version."""

from twat import __version__


def test_package_exposes_version() -> None:
    assert __version__ == "0.2.2"

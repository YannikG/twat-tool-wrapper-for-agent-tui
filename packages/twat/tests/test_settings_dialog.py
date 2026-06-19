"""Regression: SettingsDialog accept must persist a real Theme, not a str.

StrEnum members are str subclasses, so Qt's currentData() returns a plain str.
The dialog coerces back to Theme so Settings.to_dict() (.value) doesn't crash.
"""

from pathlib import Path

from twat.app.service import AppService
from twat.core.settings import Theme
from twat.core.store import StateStore
from twat.ui.settings_dialog import SettingsDialog


def test_settings_dialog_accept_persists_theme(qtbot, tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))
    dialog = SettingsDialog(svc)
    qtbot.addWidget(dialog)

    # select Light (index 1) and accept
    dialog._theme.setCurrentIndex(1)
    dialog._on_accept()

    assert svc.settings.theme is Theme.LIGHT
    # the crash was here: to_dict() called .value on a plain str
    svc._store.save(svc._state)  # exercise the failing path
    assert StateStore(tmp_path / "state.json").load().settings.theme is Theme.LIGHT


def test_settings_dialog_accept_dark(qtbot, tmp_path: Path) -> None:
    svc = AppService(StateStore(tmp_path / "state.json"))
    svc.set_theme(Theme.LIGHT)
    dialog = SettingsDialog(svc)
    qtbot.addWidget(dialog)

    dialog._theme.setCurrentIndex(0)  # Dark
    dialog._on_accept()

    assert svc.settings.theme is Theme.DARK

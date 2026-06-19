"""Settings dialog: theme + `pi` executable path (the only two v1 settings)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from twat.app.service import AppService
from twat.core.settings import Theme


class SettingsDialog(QDialog):
    def __init__(self, service: AppService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self.setWindowTitle("Settings")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._theme = QComboBox()
        self._theme.addItem("Dark", Theme.DARK)
        self._theme.addItem("Light", Theme.LIGHT)
        self._theme.setCurrentIndex(0 if service.settings.theme is Theme.DARK else 1)
        form.addRow("Theme", self._theme)

        path_row = QHBoxLayout()
        self._pi_path = QLineEdit(service.settings.pi_path)
        self._pi_path.setReadOnly(True)  # native picker only; no free-text path
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._on_browse)
        path_row.addWidget(self._pi_path, 1)
        path_row.addWidget(browse)
        path_widget = QWidget()
        path_widget.setLayout(path_row)
        form.addRow("pi executable", path_widget)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_browse(self) -> None:
        start = self._pi_path.text() or ""
        path, _ = QFileDialog.getOpenFileName(self, "Select pi executable", start)
        if path:
            self._pi_path.setText(path)

    def _on_accept(self) -> None:
        # Qt returns StrEnum members as plain str via currentData(); coerce back.
        theme = Theme(self._theme.currentData())
        self._service.set_theme(theme)
        self._service.set_pi_path(self._pi_path.text())
        self.accept()

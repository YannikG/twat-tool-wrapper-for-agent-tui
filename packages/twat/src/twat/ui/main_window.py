"""Main window: sidebar (projects) + terminal panel.

Slice 2: the right panel runs a real embedded terminal (login shell in the
selected project folder). No `pi` yet (next slice). Terminal state is not
preserved across project switches — sessions arrive in a later slice.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from twat.app.service import AppService, ProjectExistsError
from twat.core.project import Project, suggest_name
from twat.ui.settings_dialog import SettingsDialog
from twat.ui.terminal_widget import TerminalWidget
from twat.ui.theme import apply_theme

_PROJECT_ID_ROLE = Qt.ItemDataRole.UserRole + 1
_APP_TITLE = "TWAT — Tool Wrapper for Agent TUIs"


def _shell_argv() -> list[str]:
    """Login shell for the PTY: $SHELL, fallback /bin/bash (POSIX)."""
    if sys.platform == "win32":
        # Git Bash if present, else cmd — refined in a later slice.
        git_bash = r"C:\Program Files\Git\bin\bash.exe"
        return [git_bash] if os.path.exists(git_bash) else ["cmd.exe"]
    shell = os.environ.get("SHELL") or "/bin/bash"
    return [shell]


class MainWindow(QMainWindow):
    def __init__(self, service: AppService) -> None:
        super().__init__()
        self._service = service
        self._selected: Project | None = None
        self._terminal: TerminalWidget | None = None
        self.setWindowTitle(_APP_TITLE)
        self.resize(1040, 660)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_sidebar())
        splitter.addWidget(self._build_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 760])
        self.setCentralWidget(splitter)

        self._status = self.statusBar()
        self._status.showMessage(self._pi_status_text())

        self.refresh_projects()

    # -- sidebar -------------------------------------------------------------

    def _build_sidebar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("SidebarFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QLabel("Projects")
        header.setObjectName("SidebarHeader")
        layout.addWidget(header)

        self._project_list = QListWidget()
        self._project_list.currentItemChanged.connect(self._on_project_changed)
        layout.addWidget(self._project_list, 1)

        add_btn = QPushButton("+ Add Project")
        add_btn.clicked.connect(self._on_add_project)
        layout.addWidget(add_btn)

        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self._on_settings)
        layout.addWidget(settings_btn)

        return frame

    # -- panel (stacked: placeholder <-> terminal) ---------------------------

    def _build_panel(self) -> QWidget:
        self._stack = QStackedWidget()

        self._placeholder = QFrame()
        self._placeholder.setObjectName("PlaceholderPanel")
        layout = QVBoxLayout(self._placeholder)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._panel_title = QLabel()
        self._panel_title.setObjectName("PlaceholderTitle")
        self._panel_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._panel_subtitle = QLabel()
        self._panel_subtitle.setObjectName("PlaceholderSubtitle")
        self._panel_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._open_btn = QPushButton("Open Terminal")
        self._open_btn.clicked.connect(self._on_open_terminal)
        self._show_empty_panel()

        layout.addStretch(1)
        layout.addWidget(self._panel_title)
        layout.addWidget(self._panel_subtitle)
        layout.addWidget(self._open_btn)
        layout.addStretch(1)

        self._stack.addWidget(self._placeholder)
        return self._stack

    # -- public test/refresh API --------------------------------------------

    def refresh_projects(self) -> None:
        """Rebuild the sidebar list from the service."""
        self._project_list.clear()
        for proj in self._service.projects:
            item = QListWidgetItem(proj.name)
            item.setData(_PROJECT_ID_ROLE, proj.id)
            self._project_list.addItem(item)

    def project_names(self) -> list[str]:
        return [self._project_list.item(i).text() for i in range(self._project_list.count())]

    def select_project(self, project_id: str) -> None:
        for i in range(self._project_list.count()):
            item = self._project_list.item(i)
            if item.data(_PROJECT_ID_ROLE) == project_id:
                self._project_list.setCurrentRow(i)
                return

    def panel_title(self) -> str:
        return str(self._panel_title.text())

    def panel_subtitle(self) -> str:
        return str(self._panel_subtitle.text())

    # -- handlers ------------------------------------------------------------

    def _on_project_changed(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        # switching project stops the current terminal (state not preserved yet)
        self._close_terminal()
        if current is None:
            self._selected = None
            self._show_empty_panel()
            self.setWindowTitle(_APP_TITLE)
            return
        project_id = current.data(_PROJECT_ID_ROLE)
        proj = next((p for p in self._service.projects if p.id == project_id), None)
        if proj is None:
            return
        self._selected = proj
        self._panel_title.setText(proj.name)
        self._panel_subtitle.setText(proj.path)
        self._open_btn.setText("Open Terminal")
        self._open_btn.setEnabled(True)
        self._stack.setCurrentWidget(self._placeholder)
        # OS window title carries project context — a wrong-window safeguard.
        self.setWindowTitle(f"{proj.name} — {_APP_TITLE}")

    def _show_empty_panel(self) -> None:
        self._panel_title.setText("TWAT")
        self._panel_subtitle.setText("Add a project to get started.")
        self._open_btn.setEnabled(False)
        self._stack.setCurrentWidget(self._placeholder)

    def _on_open_terminal(self) -> None:
        if self._selected is None:
            return
        self._close_terminal()
        term = TerminalWidget(parent=self._stack)
        term.finished.connect(self._on_terminal_finished)
        self._stack.addWidget(term)
        self._stack.setCurrentWidget(term)
        term.start(_shell_argv(), cwd=self._selected.path)
        self._terminal = term

    def _on_terminal_finished(self) -> None:
        if self._selected is not None:
            self._panel_title.setText(self._selected.name)
            self._panel_subtitle.setText("Terminal closed.")
            self._open_btn.setText("Reopen Terminal")
            self._open_btn.setEnabled(True)
            self._stack.setCurrentWidget(self._placeholder)
        self._terminal = None

    def _close_terminal(self) -> None:
        if self._terminal is not None:
            term = self._terminal
            self._terminal = None
            term.finished.disconnect(self._on_terminal_finished)
            term.stop()
            self._stack.removeWidget(term)
            term.deleteLater()

    def _on_add_project(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Add Project Folder")
        if not folder:
            return
        default_name = suggest_name(folder)
        name, ok = QInputDialog.getText(self, "Project Name", "Project name:", text=default_name)
        if not ok:
            return
        try:
            self._service.add_project(folder, name=name.strip() or default_name)
        except ProjectExistsError:
            QMessageBox.warning(self, "Project exists", "That folder is already added.")
            return
        self.refresh_projects()
        if self._service.projects:
            self.select_project(self._service.projects[-1].id)

    def _on_settings(self) -> None:
        dialog = SettingsDialog(self._service, parent=self)
        if dialog.exec():
            apply_theme(self._app(), self._service.settings.theme.value)
            self._status.showMessage(self._pi_status_text())

    def closeEvent(self, event: object) -> None:
        # no hidden long-running processes: stop the terminal on window close
        self._close_terminal()
        super().closeEvent(event)  # type: ignore[arg-type]

    # -- helpers -------------------------------------------------------------

    def _app(self) -> object:
        from PySide6.QtWidgets import QApplication

        return QApplication.instance()

    def _pi_status_text(self) -> str:
        path = self._service.settings.pi_path
        return f"pi: {path}" if path else "pi: not found (set path in Settings)"

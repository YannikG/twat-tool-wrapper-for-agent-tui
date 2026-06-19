"""Main window: styled project/session tree (left) + single terminal (right).

Slice 3a (rev2): no tabs. A custom-styled QTreeWidget shows Projects -> Sessions
on the left; selecting a session node shows that session's terminal on the
right (one at a time, others kept alive in the background). Start/Stop/
Terminate + New Session live in a toolbar above the terminal.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from twat.app.pi_process_adapter import PiProcessAdapter
from twat.app.service import AppService, ProjectExistsError
from twat.core.project import Project, suggest_name
from twat.core.session import Session, SessionState
from twat.hook.integration import HookIntegration
from twat.ui.settings_dialog import SettingsDialog
from twat.ui.termqt_terminal import TermQtTerminal
from twat.ui.theme import apply_theme

_PROJECT_ROLE = Qt.ItemDataRole.UserRole + 1
_SESSION_ROLE = Qt.ItemDataRole.UserRole + 2
_APP_TITLE = "TWAT — Tool Wrapper for Agent TUIs"

_STATE_CHIP = {
    SessionState.STARTING: "…",
    SessionState.RUNNING: "▶",
    SessionState.EXITED: "■",
    SessionState.FAILED: "✕",
}


class _EventBridge(QObject):
    """Marshals hook events (listener thread) to the Qt main thread."""

    event_received = Signal(dict)


class MainWindow(QMainWindow):
    def __init__(self, service: AppService) -> None:
        super().__init__()
        self._service = service
        self._terminal_by_session: dict[str, TermQtTerminal] = {}
        self._adapter: PiProcessAdapter | None = None
        self._hook: HookIntegration | None = None
        self._bridge = _EventBridge()
        self._bridge.event_received.connect(self._on_hook_event)
        self.setWindowTitle(_APP_TITLE)
        self.resize(1040, 660)

        self._install_process_adapter()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_sidebar())
        splitter.addWidget(self._build_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 740])
        self.setCentralWidget(splitter)

        self._status = self.statusBar()
        self._status.showMessage(self._pi_status_text())

        self._refresh_tree()

    def _install_process_adapter(self) -> None:
        from twat import __version__

        pi_path = self._service.settings.pi_path
        # stop any previous hook listener
        if self._hook is not None:
            self._hook.stop()
            self._hook = None
        if pi_path:
            self._adapter = PiProcessAdapter(pi_path, version=__version__)
            self._service.process_adapter = self._adapter
            self._hook = HookIntegration(self._service, on_event=self._bridge.event_received.emit)
            self._hook.start()
        else:
            self._adapter = None
            self._service.process_adapter = _NoopAdapter()

    def _build_sidebar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("SidebarFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QLabel("Projects")
        header.setObjectName("SidebarHeader")
        layout.addWidget(header)

        self._tree = QTreeWidget()
        self._tree.setObjectName("SessionTree")
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(16)
        self._tree.setUniformRowHeights(True)
        self._tree.setExpandsOnDoubleClick(False)
        self._tree.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self._tree, 1)

        add_btn = QPushButton("+ Add Project")
        add_btn.clicked.connect(self._on_add_project)
        layout.addWidget(add_btn)

        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self._on_settings)
        layout.addWidget(settings_btn)

        return frame

    def _build_panel(self) -> QWidget:
        self._stack = QStackedWidget()

        self._placeholder = QFrame()
        self._placeholder.setObjectName("PlaceholderPanel")
        ph_layout = QVBoxLayout(self._placeholder)
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._panel_title = QLabel("TWAT")
        self._panel_title.setObjectName("PlaceholderTitle")
        self._panel_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._panel_subtitle = QLabel("Add a project, then create and start a session.")
        self._panel_subtitle.setObjectName("PlaceholderSubtitle")
        self._panel_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_layout.addStretch(1)
        ph_layout.addWidget(self._panel_title)
        ph_layout.addWidget(self._panel_subtitle)
        ph_layout.addStretch(1)

        self._session_area = QWidget()
        sa_layout = QVBoxLayout(self._session_area)
        sa_layout.setContentsMargins(8, 8, 8, 8)
        sa_layout.setSpacing(6)

        self._toolbar = QFrame()
        self._toolbar.setObjectName("ToolbarFrame")
        tb_layout = QHBoxLayout(self._toolbar)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.setSpacing(6)
        self._new_session_btn = QPushButton("+ New Session")
        self._new_session_btn.clicked.connect(self._on_new_session)
        self._start_btn = QPushButton("▶ Start")
        self._stop_btn = QPushButton("⏹ Stop")
        self._term_btn = QPushButton("✕ Terminate")
        self._start_btn.clicked.connect(lambda: self._session_action("start"))
        self._stop_btn.clicked.connect(lambda: self._session_action("stop"))
        self._term_btn.clicked.connect(lambda: self._session_action("terminate"))
        self._ctx_label = QLabel("")
        self._ctx_label.setObjectName("ToolbarContext")
        tb_layout.addWidget(self._new_session_btn)
        tb_layout.addStretch(1)
        tb_layout.addWidget(self._ctx_label)
        tb_layout.addStretch(1)
        tb_layout.addWidget(self._start_btn)
        tb_layout.addWidget(self._stop_btn)
        tb_layout.addWidget(self._term_btn)
        sa_layout.addWidget(self._toolbar)

        self._terminal_host = QStackedWidget()
        sa_layout.addWidget(self._terminal_host, 1)

        # single reusable placeholder for the terminal host; live terminals are
        # added at Start and removed only at teardown, never cleared wholesale.
        self._dyn_placeholder = QFrame()
        self._dyn_placeholder.setObjectName("PlaceholderPanel")
        dph = QVBoxLayout(self._dyn_placeholder)
        dph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dyn_ph_title = QLabel("TWAT")
        self._dyn_ph_title.setObjectName("PlaceholderTitle")
        self._dyn_ph_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dyn_ph_sub = QLabel("")
        self._dyn_ph_sub.setObjectName("PlaceholderSubtitle")
        self._dyn_ph_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dph.addStretch(1)
        dph.addWidget(self._dyn_ph_title)
        dph.addWidget(self._dyn_ph_sub)
        dph.addStretch(1)
        self._terminal_host.addWidget(self._dyn_placeholder)

        self._stack.addWidget(self._placeholder)
        self._stack.addWidget(self._session_area)
        return self._stack

    def _refresh_tree(self) -> None:
        selected_sid = self._selected_session_id()
        self._tree.clear()
        for proj in self._service.projects:
            proj_item = QTreeWidgetItem([proj.name])
            proj_item.setData(0, _PROJECT_ROLE, proj.id)
            proj_item.setExpanded(True)
            for sess in self._service.sessions_for(proj.id):
                sess_item = QTreeWidgetItem([self._session_label(sess)])
                sess_item.setData(0, _SESSION_ROLE, sess.id)
                proj_item.addChild(sess_item)
            self._tree.addTopLevelItem(proj_item)
        if selected_sid is not None:
            self._select_session(selected_sid)
        self._update_controls()

    def _on_selection_changed(self) -> None:
        self._show_selected()
        self._update_controls()

    def _selected_session_id(self) -> str | None:
        item = self._tree.currentItem()
        if item is None:
            return None
        sid = item.data(0, _SESSION_ROLE)
        return str(sid) if sid is not None else None

    def _selected_session(self) -> Session | None:
        sid = self._selected_session_id()
        if sid is None:
            return None
        try:
            return self._service.get_session(sid)
        except KeyError:
            return None

    def _selected_project(self) -> Project | None:
        item = self._tree.currentItem()
        if item is None:
            return None
        pid = item.data(0, _PROJECT_ROLE)
        if pid is not None:
            return next((p for p in self._service.projects if p.id == pid), None)
        sid = item.data(0, _SESSION_ROLE)
        if sid is not None:
            try:
                sess = self._service.get_session(str(sid))
            except KeyError:
                return None
            return next((p for p in self._service.projects if p.id == sess.project_id), None)
        return None

    def _show_selected(self) -> None:
        sess = self._selected_session()
        proj = self._selected_project()
        if sess is None:
            if proj is None:
                self._stack.setCurrentWidget(self._placeholder)
                self._panel_title.setText("TWAT")
                self._panel_subtitle.setText("Add a project, then create and start a session.")
                self._ctx_label.setText("")
                self.setWindowTitle(_APP_TITLE)
            else:
                self._stack.setCurrentWidget(self._session_area)
                self._ctx_label.setText(proj.name)
                self._show_placeholder_for_project(proj)
                self.setWindowTitle(f"{proj.name} — {_APP_TITLE}")
            return

        self._stack.setCurrentWidget(self._session_area)
        self._ctx_label.setText(f"{sess.name} · {proj.name}" if proj else sess.name)
        if sess.id in self._terminal_by_session:
            term = self._terminal_by_session[sess.id]
            self._terminal_host.setCurrentWidget(term)
            self._focus_terminal(term)
        else:
            self._show_session_placeholder(sess, proj)
        self.setWindowTitle(
            f"{sess.name} · {proj.name} — {_APP_TITLE}" if proj else f"{sess.name} — {_APP_TITLE}"
        )

    def _focus_terminal(self, term: TermQtTerminal) -> None:
        """Hand focus to a terminal, deferred to next event loop iteration.

        Selecting a tree node fires while the tree still holds focus; requesting
        focus synchronously can be overridden by Qt restoring focus to the tree.
        A queued invocation moves the focus grab after the selection cycle.
        """
        from PySide6.QtCore import QTimer

        term.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        QTimer.singleShot(0, lambda: term.setFocus(Qt.FocusReason.OtherFocusReason))

    def _show_placeholder_for_project(self, proj: Project) -> None:
        self._dyn_ph_title.setText(proj.name)
        self._dyn_ph_sub.setText("Select or create a session.")
        self._terminal_host.setCurrentWidget(self._dyn_placeholder)

    def _show_session_placeholder(self, sess: Session, proj: Project | None) -> None:
        base = f"{proj.name} · {proj.path}" if proj else ""
        hint = {
            SessionState.RUNNING: f"{base}  (reconnecting…)",
            SessionState.EXITED: f"{base}  — press Start to launch pi",
            SessionState.FAILED: f"{base}  — terminated",
            SessionState.STARTING: f"{base}  — starting…",
        }.get(sess.state, base)
        self._dyn_ph_title.setText(sess.name)
        self._dyn_ph_sub.setText(hint)
        self._terminal_host.setCurrentWidget(self._dyn_placeholder)

    def _update_controls(self) -> None:
        proj = self._selected_project()
        sess = self._selected_session()
        self._new_session_btn.setEnabled(proj is not None)
        if sess is None or self._adapter is None:
            for b in (self._start_btn, self._stop_btn, self._term_btn):
                b.setEnabled(False)
            return
        running = sess.state in (SessionState.RUNNING, SessionState.STARTING)
        self._start_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)
        self._term_btn.setEnabled(running)

    def _session_action(self, action: str) -> None:
        sess = self._selected_session()
        if sess is None:
            return
        try:
            if action == "start":
                self._start_session(sess)
            elif action == "stop":
                self._service.stop_session(sess.id)
                self._teardown_terminal(sess.id)
            elif action == "terminate":
                self._service.terminate_session(sess.id)
                self._teardown_terminal(sess.id)
        except Exception as e:  # surface process/launch errors to the user
            QMessageBox.warning(self, "Session error", str(e))
        # Update the affected session in place. Never rebuild the tree here: a
        # rebuild steals focus from the terminal mid-keystroke. After Start the
        # terminal already has focus, so skip _show_selected for that action.
        self._update_session_label(sess.id)
        self._update_controls()
        if action != "start":
            self._show_selected()

    def _start_session(self, sess: Session) -> None:
        if self._adapter is None:
            return
        term = self._terminal_by_session.get(sess.id)
        if term is None:
            term = TermQtTerminal(parent=self._session_area)
            self._terminal_by_session[sess.id] = term
            self._terminal_host.addWidget(term)
        if self._hook is not None:
            self._adapter.set_hook_env_for(sess.id, self._hook.env_for(sess.id))
        self._service.start_session(sess.id)
        pty = self._adapter.pty(sess.id)
        if pty is not None:
            term.attach(pty, on_finished=lambda sid=sess.id: self._on_terminal_finished(sid))  # type: ignore[misc]
        self._terminal_host.setCurrentWidget(term)
        self._focus_terminal(term)

    def _on_terminal_finished(self, session_id: str) -> None:
        try:
            self._service.stop_session(session_id)
        except KeyError:
            return
        self._teardown_terminal(session_id)
        self._refresh_tree()
        self._show_selected()

    def _teardown_terminal(self, session_id: str) -> None:
        term = self._terminal_by_session.pop(session_id, None)
        if term is not None:
            term.detach()
            self._terminal_host.removeWidget(term)
            term.deleteLater()

    def _on_new_session(self) -> None:
        proj = self._selected_project()
        if proj is None:
            return
        sess = self._service.new_session(proj.id)
        self._refresh_tree()
        self._select_session(sess.id)

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
        self._refresh_tree()

    def _on_settings(self) -> None:
        dialog = SettingsDialog(self._service, parent=self)
        if dialog.exec():
            apply_theme(self._app(), self._service.settings.theme.value)
            self._status.showMessage(self._pi_status_text())
            self._install_process_adapter()
            self._show_selected()

    def _on_hook_event(self, event: dict[str, object]) -> None:
        """Main-thread handler for hook events.

        Updates only the affected session's tree label in place — never rebuilds
        the tree or steals focus (rebuilding mid-keystroke broke terminal input).
        """
        sid = event.get("sessionId")
        if isinstance(sid, str):
            self._update_session_label(sid)

    def _update_session_label(self, session_id: str) -> None:
        """Refresh a single session's tree label + controls without rebuilding."""
        try:
            sess = self._service.get_session(session_id)
        except KeyError:
            return
        # find the tree item and update its text in place
        for i in range(self._tree.topLevelItemCount()):
            parent = self._tree.topLevelItem(i)
            if parent is None:
                continue
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child is not None and child.data(0, _SESSION_ROLE) == session_id:
                    child.setText(0, self._session_label(sess))
                    break
        # update toolbar context + control enabled state for the active session
        if session_id == self._selected_session_id():
            self._update_controls()

    def _session_label(self, sess: Session) -> str:
        chip = _STATE_CHIP.get(sess.state, "?")
        activity = " ⋯" if sess.agent_activity == "working" else ""
        return f"{chip}  {sess.name}{activity}"

    def closeEvent(self, event: object) -> None:
        if self._adapter is not None:
            self._adapter.stop_all()
        if self._hook is not None:
            self._hook.stop()
        for term in list(self._terminal_by_session.values()):
            term.detach()
        super().closeEvent(event)  # type: ignore[arg-type]

    # -- test helpers --------------------------------------------------------

    def project_names(self) -> list[str]:
        names: list[str] = []
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item is not None:
                names.append(item.text(0))
        return names

    def session_labels_for(self, project_id: str) -> list[str]:
        names: list[str] = []
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item is None or item.data(0, _PROJECT_ROLE) != project_id:
                continue
            for j in range(item.childCount()):
                child = item.child(j)
                if child is not None:
                    names.append(child.text(0))
        return names

    def select_project(self, project_id: str) -> None:
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item is not None and item.data(0, _PROJECT_ROLE) == project_id:
                self._tree.setCurrentItem(item)
                return

    def select_session(self, session_id: str) -> None:
        self._select_session(session_id)

    def panel_title(self) -> str:
        return str(self._panel_title.text())

    def panel_subtitle(self) -> str:
        return str(self._panel_subtitle.text())

    def _select_session(self, session_id: str) -> None:
        for i in range(self._tree.topLevelItemCount()):
            parent = self._tree.topLevelItem(i)
            if parent is None:
                continue
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child is not None and child.data(0, _SESSION_ROLE) == session_id:
                    self._tree.setCurrentItem(child)
                    return

    def _app(self) -> object:
        from PySide6.QtWidgets import QApplication

        return QApplication.instance()

    def _pi_status_text(self) -> str:
        path = self._service.settings.pi_path
        return f"pi: {path}" if path else "pi: not found (set path in Settings)"


class _NoopAdapter:
    def start(self, session_id: str, cwd: str, resume_file: str | None) -> None:
        pass

    def stop(self, session_id: str) -> None:
        pass

    def terminate(self, session_id: str) -> None:
        pass

    def is_alive(self, session_id: str) -> bool:
        return False

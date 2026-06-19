"""Action handlers extracted from MainWindow: session/project lifecycle + open-in.

Kept as a mixin so MainWindow stays under the 500 logic-line limit. All methods
operate on MainWindow state via self (typed loosely to avoid a circular import).
"""

from __future__ import annotations

import logging
import os

from PySide6.QtWidgets import QFileDialog, QInputDialog, QMenu, QMessageBox

from twat.app.service import ProjectExistsError, SessionActiveError
from twat.core.project import suggest_name
from twat.core.session import SessionState
from twat.ui.open_in import open_in_targets

_log = logging.getLogger("twat.ui")


class WindowActions:
    """Mixin: session/project action handlers for MainWindow.

    These assume the host defines the attributes/methods MainWindow sets up
    (self._service, self._adapter, self._hook, self._terminal_by_session,
    self._terminal_host, self._session_area, self._open_in_btn,
    _selected_session, _selected_project, _teardown_terminal, _refresh_tree,
    _show_selected, _select_session, _update_session_label, _update_controls,
    _focus_terminal, _on_terminal_finished, _install_process_adapter,
    _app, _status, _pi_status_text).
    """

    # -- session process lifecycle ------------------------------------------

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
            _log.exception("session action %r failed for %s", action, sess.id)
            QMessageBox.warning(self, "Session error", f"{type(e).__name__}: {e}")
        # Update in place. Never rebuild the tree here: a rebuild steals focus
        # from the terminal mid-keystroke. After Start the terminal has focus,
        # so skip _show_selected for that action.
        self._update_session_label(sess.id)
        self._update_controls()
        if action != "start":
            self._show_selected()

    def _start_session(self, sess) -> None:  # type: ignore[no-untyped-def]
        if self._adapter is None:
            return
        self._hook_connected.discard(sess.id)
        term = self._terminal_by_session.get(sess.id)
        if term is None:
            from twat.ui.termqt_terminal import TermQtTerminal

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
        _log.info("terminal finished session=%s", session_id)
        try:
            self._service.stop_session(session_id)
        except KeyError:
            _log.warning("terminal finished for unknown session %s", session_id)
            return
        self._teardown_terminal(session_id)
        self._refresh_tree()
        self._show_selected()

    def _teardown_terminal(self, session_id: str) -> None:
        self._hook_connected.discard(session_id)
        term = self._terminal_by_session.pop(session_id, None)
        if term is not None:
            term.detach()
            self._terminal_host.removeWidget(term)
            term.deleteLater()

    # -- open in editor / shell --------------------------------------------

    def _on_open_in(self) -> None:
        """Show a menu of editors/shells to open the selected session's cwd in."""
        proj = self._selected_project()
        if proj is None:
            return
        cwd = proj.path
        menu = QMenu(self)
        for label, open_fn in open_in_targets():
            menu.addAction(label, lambda _=False, fn=open_fn: fn(cwd))
        menu.exec(self._open_in_btn.mapToGlobal(self._open_in_btn.rect().bottomLeft()))

    # -- session / project record actions ----------------------------------

    def _on_new_session(self) -> None:
        proj = self._selected_project()
        if proj is None:
            _log.warning("new_session clicked but no project selected")
            return
        sess = self._service.new_session(proj.id)
        _log.info("new session created id=%s; refreshing tree", sess.id)
        self._refresh_tree()
        self._select_session(sess.id)

    def _on_archive(self) -> None:
        sess = self._selected_session()
        if sess is None:
            return
        try:
            self._service.archive_session(sess.id)
        except Exception as e:  # surface process/launch errors to the user
            QMessageBox.warning(self, "Session error", str(e))
            return
        self._teardown_terminal(sess.id)
        self._refresh_tree()
        self._show_selected()

    def _on_restore(self) -> None:
        sess = self._selected_session()
        if sess is None:
            return
        self._service.restore_session(sess.id)
        self._refresh_tree()
        self._select_session(sess.id)

    def _on_delete_session(self) -> None:
        sess = self._selected_session()
        if sess is None:
            return
        confirm = QMessageBox.question(
            self,
            "Delete session",
            f"Delete session '{sess.name}'?\n\n"
            "This removes it from TWAT. The pi conversation file on disk is kept.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self._service.delete_session(sess.id)
        except SessionActiveError as e:
            _log.warning("delete session refused (active): %s", e)
            QMessageBox.warning(self, "Cannot delete", str(e))
            return
        _log.info("deleted session %s via UI", sess.id)
        self._teardown_terminal(sess.id)
        self._refresh_tree()
        self._show_selected()

    def _on_delete_project(self) -> None:
        proj = self._selected_project()
        if proj is None:
            return
        n = len(self._service.sessions_for(proj.id))
        confirm = QMessageBox.question(
            self,
            "Delete project",
            f"Delete project '{proj.name}' and all its sessions ({n})?\n\n"
            "Running sessions are stopped first.\n"
            "The folder and pi conversations are NOT deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        for sid in [s.id for s in self._service.sessions_for(proj.id)]:
            self._teardown_terminal(sid)
        try:
            self._service.delete_project(proj.id)
        except Exception as e:  # surface errors to the user
            QMessageBox.warning(self, "Project error", str(e))
            return
        self._refresh_tree()
        self._show_selected()

    def _on_rename_project(self) -> None:
        proj = self._selected_project()
        if proj is None:
            return
        name, ok = QInputDialog.getText(self, "Rename Project", "Project name:", text=proj.name)
        if not ok:
            return
        try:
            self._service.rename_project(proj.id, name)
        except (KeyError, ValueError) as e:
            QMessageBox.warning(self, "Rename failed", str(e))
            return
        self._refresh_tree()
        self._show_selected()

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
        from twat.ui.settings_dialog import SettingsDialog
        from twat.ui.theme import apply_theme

        dialog = SettingsDialog(self._service, parent=self)
        if dialog.exec():
            apply_theme(self._app(), self._service.settings.theme.value)
            self._status.showMessage(self._pi_status_text())
            self._install_process_adapter()
            self._show_selected()

    def _on_repair_session(self) -> None:
        """Force-regenerate twat-hook.ts, stop if running, then Start again."""
        sess = self._selected_session()
        proj = self._selected_project()
        if sess is None or proj is None or sess.archived:
            return
        from twat import __version__
        from twat.hook.generator import write_hook

        write_hook(proj.path, __version__)
        _log.info("repair session %s: rewrote twat-hook in %s", sess.id, proj.path)
        if self._is_running(sess):
            self._service.stop_session(sess.id)
            self._teardown_terminal(sess.id)
            self._refresh_tree()
        self._session_action("start")

    # state-awareness helper used by the context menu builder (host overrides
    # SessionState only for typing convenience)
    def _is_running(self, sess) -> bool:  # type: ignore[no-untyped-def]
        return sess.state in (SessionState.RUNNING, SessionState.STARTING)

    def _hook_suffix(self, sess) -> str:  # type: ignore[no-untyped-def]
        if sess.state in (SessionState.RUNNING, SessionState.STARTING):
            return " ●" if sess.id in self._hook_connected else " ○"
        return ""

    def _quit_close(self, event: object) -> bool:
        """Confirm quit and tear down sessions. Return False if the user cancels."""
        running = [
            s
            for s in self._service.sessions_for_all()
            if s.state in (SessionState.RUNNING, SessionState.STARTING) and not s.archived
        ]
        if running and os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            n = len(running)
            word = "session" if n == 1 else "sessions"
            btn = QMessageBox.question(
                self,
                "Quit TWAT",
                f"{n} {word} still running. Stop them and quit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if btn != QMessageBox.StandardButton.Yes:
                event.ignore()  # type: ignore[attr-defined]
                return False
        if self._adapter is not None:
            self._adapter.stop_all()
        if self._hook is not None:
            self._hook.stop()
        for term in list(self._terminal_by_session.values()):
            term.detach()
        return True

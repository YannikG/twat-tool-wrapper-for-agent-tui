"""Theme tokens (JSON) rendered into app-wide QSS.

Tokens live in `themes/<name>.json`; the QSS template uses `$token` placeholders
resolved via `string.Template`. The Fusion style is the base (set in the entry
point). See `docs/specs/platform/theme.md`.
"""

from __future__ import annotations

import json
from pathlib import Path
from string import Template

_THEMES_DIR = Path(__file__).parent / "themes"

_QSS_TEMPLATE = Template("""
* { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; font-size: 13px; }

QMainWindow, QDialog { background-color: $bg; color: $text; }
QWidget { color: $text; }

QPushButton {
    background-color: $surface;
    color: $text;
    border: 1px solid $border;
    padding: 6px 12px;
    border-radius: 5px;
}
QPushButton:hover { background-color: $hover; border-color: $accent; }
QPushButton:pressed { background-color: $accent; color: $accent_text; }
QPushButton:disabled { color: $text_dim; border-color: $border; }

QToolButton {
    background-color: transparent;
    color: $text_dim;
    border: none;
    padding: 6px 8px;
    border-radius: 4px;
}
QToolButton:hover { background-color: $hover; color: $text; }

QListWidget {
    background-color: $sidebar;
    color: $text;
    border: none;
    outline: 0;
}
QListWidget::item { padding: 9px 12px; border-left: 3px solid transparent; }
QListWidget::item:hover { background-color: $hover; }
QListWidget::item:selected {
    background-color: $selected;
    color: $selected_text;
    border-left: 3px solid $accent;
}

QLabel { background-color: transparent; }
QLabel#SectionLabel { color: $text_dim; font-size: 11px; font-weight: 600; }
QLabel#PlaceholderTitle { color: $text_dim; font-size: 22px; font-weight: 700; }
QLabel#PlaceholderSubtitle { color: $text_dim; font-size: 13px; }
QLabel#SidebarHeader { color: $text; font-size: 15px; font-weight: 700; padding: 6px 4px; }

QLineEdit, QComboBox {
    background-color: $surface;
    color: $text;
    border: 1px solid $border;
    padding: 5px 8px;
    border-radius: 5px;
}
QLineEdit:focus, QComboBox:focus { border-color: $accent; }
QComboBox QAbstractItemView {
    background-color: $surface;
    color: $text;
    selection-background-color: $selected;
    selection-color: $selected_text;
    border: 1px solid $border;
}

QSplitter::handle { background-color: $border; }
QSplitter::handle:horizontal { width: 1px; }

QScrollBar:vertical { background: $sidebar; width: 10px; margin: 0; border: none; }
QScrollBar::handle:vertical { background: $border; border-radius: 4px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: $accent; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }

QMenuBar { background-color: $bg; color: $text; border-bottom: 1px solid $border; }
QMenuBar::item { background-color: transparent; padding: 4px 10px; border-radius: 4px; }
QMenuBar::item:selected { background-color: $hover; }
QMenuBar::item:pressed { background-color: $selected; color: $selected_text; }

QMenu { background-color: $surface; color: $text; border: 1px solid $border; padding: 4px; }
QMenu::item { padding: 6px 22px; border-radius: 4px; }
QMenu::item:disabled { color: $text_dim; }
QMenu::item:selected { background-color: $selected; color: $selected_text; }
QMenu::separator { height: 1px; background-color: $border; margin: 4px 8px; }

QTabWidget::pane { border: none; top: -1px; }
QTabBar { background-color: transparent; }
QTabBar::tab {
    background-color: $sidebar;
    color: $text_dim;
    border: 1px solid $border;
    border-bottom: none;
    padding: 6px 14px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    margin-right: 2px;
}
QTabBar::tab:selected { background-color: $surface; color: $text; }
QTabBar::tab:hover:!selected { background-color: $hover; color: $text; }

QToolTip { background-color: $surface; color: $text; border: 1px solid $border; padding: 4px 6px; }

QInputDialog QLabel, QMessageBox QLabel { color: $text; }

QStatusBar { background-color: $sidebar; color: $text_dim; }
QStatusBar::item { border: none; }

QFrame#PlaceholderPanel { background-color: $placeholder; }
QFrame#SidebarFrame { background-color: $sidebar; }
QFrame#ToolbarFrame { background-color: $panel; border-bottom: 1px solid $border; }
QLabel#ToolbarContext { color: $text_dim; font-size: 12px; }

QTreeWidget#SessionTree {
    background-color: $sidebar;
    color: $text;
    border: none;
    outline: 0;
    padding: 4px 0px;
}
QTreeWidget::item { padding: 6px 4px; border-left: 3px solid transparent; }
QTreeWidget::item:hover { background-color: $hover; }
QTreeWidget::item:selected {
    background-color: $selected;
    color: $selected_text;
    border-left: 3px solid $accent;
}
/* branch expand/collapse arrows: use native indicators (no override) */
""")


def load_tokens(theme: str) -> dict[str, str]:
    """Load the token dict for a theme name (`dark` or `light`)."""
    path = _THEMES_DIR / f"{theme}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: str(v) for k, v in data.items()}


def render_qss(theme: str) -> str:
    """Render the app-wide QSS for a theme, with all tokens resolved."""
    return _QSS_TEMPLATE.safe_substitute(load_tokens(theme))


def apply_theme(app: object, theme: str) -> None:
    """Apply a theme's QSS to a QApplication instance."""
    app.setStyleSheet(render_qss(theme))  # type: ignore[attr-defined]

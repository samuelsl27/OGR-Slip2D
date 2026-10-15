# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Qt stylesheet themes (QSS) — light and dark, QGIS-inspired.

The ``THEMES`` dict is the single source of truth; switching is a
matter of calling ``QApplication.setStyleSheet(THEMES[name])``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

_LIGHT = """
/* -----------------------------------------------------------------
   OGR Suite — LIGHT theme (QGIS-inspired)
   ----------------------------------------------------------------- */
QMainWindow, QDialog {
    background-color: #f3f3f3;
    color: #202020;
}
QMenuBar {
    background-color: #e9e9e9;
    color: #202020;
    spacing: 3px;
    padding: 2px 6px;
    border-bottom: 1px solid #c0c0c0;
}
QMenuBar::item {
    padding: 4px 10px;
    background: transparent;
    border-radius: 3px;
}
QMenuBar::item:selected {
    background-color: #d7e8ff;
}
QMenu {
    background-color: #ffffff;
    color: #202020;
    border: 1px solid #a0a0a0;
    padding: 4px;
}
QMenu::item {
    padding: 5px 22px 5px 22px;
    border-radius: 3px;
}
QMenu::item:selected {
    background-color: #d7e8ff;
}
/* v0.1.288 (D289): with a stylesheet, Qt draws a disabled item in the
   colour given to QMenu unless a :disabled rule says otherwise. */
QMenu::item:disabled {
    color: #a0a0a0;
}
QMenu::separator {
    height: 1px;
    background: #d0d0d0;
    margin: 4px 6px;
}
QToolBar {
    background-color: #e9e9e9;
    border-bottom: 1px solid #c0c0c0;
    spacing: 2px;
    padding: 2px;
}
QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 4px;
    margin: 1px;
}
QToolButton:hover {
    background-color: #d7e8ff;
    border-color: #8fb9e0;
}
QToolButton:pressed, QToolButton:checked {
    background-color: #b9d7f7;
    border-color: #6aa3d5;
}
QStatusBar {
    background-color: #e9e9e9;
    color: #202020;
    border-top: 1px solid #c0c0c0;
}
QStatusBar QLabel {
    padding: 0 6px;
}
QDockWidget {
    color: #202020;
    titlebar-close-icon: url(none);
}
QDockWidget::title {
    background: #dbdbdb;
    padding: 4px;
    border-bottom: 1px solid #bcbcbc;
}
QTreeView, QListView, QTableView {
    background-color: #ffffff;
    alternate-background-color: #f6f9fc;
    selection-background-color: #b9d7f7;
    selection-color: #000000;
    gridline-color: #dedede;
}
QHeaderView::section {
    background-color: #ececec;
    padding: 4px 6px;
    border: 1px solid #d0d0d0;
    font-weight: 500;
}
QPushButton {
    background-color: #f7f7f7;
    border: 1px solid #b0b0b0;
    padding: 5px 14px;
    border-radius: 3px;
}
QPushButton:hover { background-color: #e8f1fb; }
QPushButton:pressed { background-color: #c9dff7; }
QPushButton:default { border: 2px solid #4a90d9; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {
    background-color: #ffffff;
    border: 1px solid #b0b0b0;
    padding: 3px 5px;
    border-radius: 2px;
    selection-background-color: #b9d7f7;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #4a90d9;
}
QGroupBox {
    border: 1px solid #c0c0c0;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 8px;
    font-weight: 500;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #40607a;
}
QGroupBox::title:disabled {
    color: #a0a0a0;
}
QTabWidget::pane {
    border: 1px solid #c0c0c0;
    background: #ffffff;
}
QTabBar::tab {
    background: #e4e4e4;
    padding: 5px 14px;
    border: 1px solid #c0c0c0;
    border-bottom: none;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
}
QTabBar::tab:selected {
    background: #ffffff;
    font-weight: 500;
}
QScrollBar:vertical {
    background: #e9e9e9; width: 12px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #b6b6b6; border-radius: 6px; min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #8fb9e0; }
QScrollBar:horizontal {
    background: #e9e9e9; height: 12px; margin: 0;
}
QScrollBar::handle:horizontal {
    background: #b6b6b6; border-radius: 6px; min-width: 20px;
}
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QToolTip {
    background-color: #fffddc;
    color: #202020;
    border: 1px solid #a08030;
    padding: 4px;
}
"""

_DARK = """
/* -----------------------------------------------------------------
   OGR Suite — DARK theme
   ----------------------------------------------------------------- */
QMainWindow, QDialog {
    background-color: #2b2b2b;
    color: #e0e0e0;
}
QMenuBar {
    background-color: #3a3a3a;
    color: #e0e0e0;
    border-bottom: 1px solid #1e1e1e;
}
QMenuBar::item { padding: 4px 10px; background: transparent; border-radius: 3px; }
QMenuBar::item:selected { background-color: #505a70; }
QMenu {
    background-color: #353535; color: #e0e0e0;
    border: 1px solid #1e1e1e; padding: 4px;
}
QMenu::item { padding: 5px 22px; border-radius: 3px; }
QMenu::item:selected { background-color: #4a5a75; }
/* v0.1.288 (D289): every text colour set here needs its :disabled one. */
QMenu::item:disabled { color: #7a7a7a; }
QMenu::separator { height: 1px; background: #4a4a4a; margin: 4px 6px; }

QToolBar {
    background-color: #3a3a3a;
    border-bottom: 1px solid #1e1e1e;
    spacing: 2px; padding: 2px;
}
QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 4px; margin: 1px;
    color: #e0e0e0;
}
QToolButton:hover {
    background-color: #4a5a75;
    border-color: #6a85b0;
}
QToolButton:pressed, QToolButton:checked {
    background-color: #5b7398;
    border-color: #7895b9;
}
QStatusBar {
    background-color: #3a3a3a;
    color: #e0e0e0;
    border-top: 1px solid #1e1e1e;
}
QStatusBar QLabel { padding: 0 6px; }
QDockWidget::title {
    background: #3a3a3a; padding: 4px;
    border-bottom: 1px solid #1e1e1e;
    color: #e0e0e0;
}
QTreeView, QListView, QTableView {
    background-color: #2b2b2b;
    alternate-background-color: #323232;
    selection-background-color: #5b7398;
    selection-color: #ffffff;
    color: #e0e0e0;
    gridline-color: #404040;
}
QHeaderView::section {
    background-color: #404040;
    color: #e0e0e0;
    padding: 4px 6px;
    border: 1px solid #1e1e1e;
}
QPushButton {
    background-color: #3f3f3f;
    border: 1px solid #555;
    padding: 5px 14px;
    border-radius: 3px;
    color: #e0e0e0;
}
QPushButton:hover { background-color: #4a5a75; }
QPushButton:pressed { background-color: #5b7398; }
QPushButton:default { border: 2px solid #6a85b0; }
QPushButton:disabled, QToolButton:disabled { color: #7a7a7a; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #555;
    padding: 3px 5px; border-radius: 2px;
    selection-background-color: #5b7398;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #6a85b0;
}
QGroupBox {
    border: 1px solid #555;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 8px;
    color: #e0e0e0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #9ab6d6;
}
QTabWidget::pane { border: 1px solid #555; background: #2b2b2b; }
QTabBar::tab {
    background: #3a3a3a; color: #e0e0e0;
    padding: 5px 14px;
    border: 1px solid #555; border-bottom: none;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
}
QTabBar::tab:selected { background: #2b2b2b; font-weight: 500; }
QTabBar::tab:disabled { color: #7a7a7a; }
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
QComboBox:disabled, QPlainTextEdit:disabled, QTextEdit:disabled,
QTreeView:disabled, QListView:disabled, QTableView:disabled,
QHeaderView::section:disabled, QGroupBox:disabled,
QGroupBox::title:disabled { color: #7a7a7a; }
QScrollBar:vertical { background: #2b2b2b; width: 12px; }
QScrollBar::handle:vertical { background: #555; border-radius: 6px; }
QScrollBar::handle:vertical:hover { background: #6a85b0; }
QScrollBar:horizontal { background: #2b2b2b; height: 12px; }
QScrollBar::handle:horizontal { background: #555; border-radius: 6px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QToolTip {
    background-color: #1e1e1e; color: #e0e0e0;
    border: 1px solid #6a85b0; padding: 4px;
}
"""

THEMES: dict[str, str] = {
    "light": _LIGHT,
    "dark": _DARK,
}


#: v0.1.316 (D301) — the colours the widgets used to write as literals, by
#: what they are for. The light values ARE those literals, so the light
#: theme looks exactly as it did; the dark ones are lighter, to read on a
#: dark background. A role whose widget paints its own background (the
#: status-bar toggles, the stale-results band) needs no entry: it reads
#: the same in both.
ROLE_COLORS: dict[str, dict[str, str]] = {
    "light": {
        "muted": "#555555",         # notes in italics, hints
        "muted_strong": "#444444",
        "muted_soft": "#666666",
        "disabled": "#909090",      # a label whose control is off
        "error": "#b00020",         # why OK did not close
        "warning": "#a05a00",       # what the search will do with a value
        "caution": "#8a5a00",
        "accent": "#c0392b",        # the factor of safety in Interpret
        "ink": "#202020",           # plain text a widget writes itself
        "note_bg": "#f4f4f8",       # a boxed note
        "info_bg": "#eeeeff",
        "status_text": "#4a4a4a",   # the coordinates of the status bar
        "toggle_off": "#707070",
        "separator": "#c0c0c0",
        "canvas_bg": "#fafafa",
        "canvas_bg_gray": "#e8e8e8",
        "grid_minor": "#dcdcdc",
        "grid_major": "#b4b4b4",
        "ruler_text": "#646464",
    },
    "dark": {
        "muted": "#a8a8a8",
        "muted_strong": "#b8b8b8",
        "muted_soft": "#9a9a9a",
        "disabled": "#7a7a7a",
        "error": "#ff6b6b",
        "warning": "#f0b060",
        "caution": "#e0a050",
        "accent": "#ff7f6e",
        "ink": "#e0e0e0",
        "note_bg": "#353540",
        "info_bg": "#34384a",
        "status_text": "#d0d0d0",
        "toggle_off": "#9a9a9a",
        "separator": "#5a5a5a",
        "canvas_bg": "#1f1f1f",
        "canvas_bg_gray": "#2a2a2a",
        "grid_minor": "#373737",
        "grid_major": "#505050",
        "ruler_text": "#aaaaaa",
    },
}

#: The application's palette before any theme touched it, which IS the
#: light theme's: the light theme is the platform's palette plus the sheet.
_ORIGINAL_PALETTE = None


def current_theme(app=None) -> str:
    """The theme whose sheet the application has, or "light".

    Read from the style sheet itself and not from a variable set by
    :func:`apply_theme`: a test that puts the sheet back would leave such a
    variable saying "dark" over a light application.
    """
    from PySide6.QtWidgets import QApplication
    app = app or QApplication.instance()
    sheet = app.styleSheet() if app is not None else ""
    for name, qss in THEMES.items():
        if sheet == qss:
            return name
    return "light"


def theme_color(role: str, theme: str | None = None) -> str:
    """The colour of ``role`` in ``theme`` (the active one by default)."""
    theme = theme or current_theme()
    return ROLE_COLORS.get(theme, ROLE_COLORS["light"])[role]


def _dark_palette():
    """The dark theme's palette, from the colours its sheet already uses."""
    from PySide6.QtGui import QColor, QPalette
    p = QPalette()
    roles = {
        QPalette.Window: "#2b2b2b", QPalette.WindowText: "#e0e0e0",
        QPalette.Base: "#1e1e1e", QPalette.AlternateBase: "#323232",
        QPalette.Text: "#e0e0e0", QPalette.Button: "#3f3f3f",
        QPalette.ButtonText: "#e0e0e0", QPalette.BrightText: "#ffffff",
        QPalette.Highlight: "#5b7398", QPalette.HighlightedText: "#ffffff",
        QPalette.ToolTipBase: "#1e1e1e", QPalette.ToolTipText: "#e0e0e0",
        QPalette.PlaceholderText: "#8a8a8a", QPalette.Link: "#8ab4f8",
        QPalette.Light: "#505050", QPalette.Midlight: "#454545",
        QPalette.Mid: "#3a3a3a", QPalette.Dark: "#202020",
        QPalette.Shadow: "#101010",
    }
    for role, hexa in roles.items():
        p.setColor(role, QColor(hexa))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, QColor("#7a7a7a"))
    return p


def apply_theme(app, name: str = "light") -> None:
    """Apply a named theme to the running QApplication.

    v0.1.315 (D293) — and the floor of the buttons of a button box
    (``ogr_gui.button_floor``), which replaces the ``min-width: 70px`` these
    sheets used to give every button: in a style sheet that minimum
    replaced the one the text asks for, and cut Spanish buttons.

    v0.1.316 (D301) — and a palette. The sheet alone colours the widgets
    it names; the dark one names no ``QLabel``, ``QCheckBox`` or plain
    panel, and those kept the light palette: dark text on a dark window.
    The dark theme now sets a dark palette, and the light one puts back
    the palette the application had before any theme, so it does not
    change. Icons and colours read the palette and :func:`theme_color`
    when they are built, so a window built after this follows the theme;
    the main window refreshes what it keeps.
    """
    global _ORIGINAL_PALETTE
    from PySide6.QtGui import QPalette
    from ogr_gui import button_floor
    button_floor.install(app)
    if _ORIGINAL_PALETTE is None:
        _ORIGINAL_PALETTE = QPalette(app.palette())
    name = name if name in THEMES else "light"
    app.setPalette(_dark_palette() if name == "dark"
                   else QPalette(_ORIGINAL_PALETTE))
    app.setStyleSheet(THEMES[name])
    # qtawesome colours an icon with no colour of its own from the palette
    # when it builds it, and both it and our ``icon`` cache what they built
    from ogr_gui.resources import icons
    icons.reset_cache()

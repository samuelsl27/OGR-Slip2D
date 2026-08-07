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
    min-width: 70px;
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
    min-width: 70px;
}
QPushButton:hover { background-color: #4a5a75; }
QPushButton:pressed { background-color: #5b7398; }
QPushButton:default { border: 2px solid #6a85b0; }
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


def apply_theme(app, name: str = "light") -> None:
    """Apply a named stylesheet to the running QApplication."""
    app.setStyleSheet(THEMES.get(name, _LIGHT))

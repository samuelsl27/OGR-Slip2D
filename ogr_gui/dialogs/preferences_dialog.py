# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Preferences dialog.

Small application-wide settings: active language, active theme and a
few display toggles. Kept deliberately narrow — per-project settings
live in :class:`ProjectSettingsDialog`.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QVBoxLayout,
)

from ogr_gui.i18n import available_languages, current_language, tr
from ogr_gui.themes import THEMES
from ogr_gui.i18n import tr  # noqa: E402


class PreferencesDialog(QDialog):
    language_changed = Signal(str)
    theme_changed = Signal(str)

    def __init__(self, parent=None, active_theme: str = "light") -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Preferences..."))
        self.setMinimumWidth(380)
        root = QVBoxLayout(self)

        # --- General group --------------------------------------------
        gen = QGroupBox(tr("File"))
        form = QFormLayout(gen)
        self.cbo_language = QComboBox()
        for code in available_languages():
            label = {"en": "English", "es": "Español"}.get(code, code)
            self.cbo_language.addItem(label, code)
        idx = self.cbo_language.findData(current_language())
        self.cbo_language.setCurrentIndex(idx if idx >= 0 else 0)
        form.addRow(tr("Language") + ":", self.cbo_language)

        self.cbo_theme = QComboBox()
        for key in THEMES:
            self.cbo_theme.addItem(tr(key.capitalize()), key)
        idx = self.cbo_theme.findData(active_theme)
        self.cbo_theme.setCurrentIndex(idx if idx >= 0 else 0)
        form.addRow(tr("Theme") + ":", self.cbo_theme)

        root.addWidget(gen)

        # --- Display group -------------------------------------------
        disp = QGroupBox(tr("Display Options..."))
        form2 = QFormLayout(disp)
        self.chk_show_tabs = QCheckBox(tr("Show Tabs for Multiple Windows"))
        self.chk_show_tabs.setChecked(True)
        self.chk_mark_modified = QCheckBox(tr("Mark file as modified after importing"))
        self.chk_mark_modified.setChecked(True)
        self.chk_save_compressed = QCheckBox(tr("Default to compressed format when saving"))
        self.chk_save_compressed.setChecked(False)
        form2.addRow(self.chk_show_tabs)
        form2.addRow(self.chk_mark_modified)
        form2.addRow(self.chk_save_compressed)
        root.addWidget(disp)

        # --- Buttons --------------------------------------------------
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ------------------------------------------------------------------
    def _accept(self) -> None:
        lang = self.cbo_language.currentData()
        theme = self.cbo_theme.currentData()
        self.language_changed.emit(lang)
        self.theme_changed.emit(theme)
        self.accept()

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.291 (D290b) — *Preferences* announces a change of language only when
the language changed.

The defect: ``PreferencesDialog._accept`` emitted ``language_changed`` on
every Save, and since D290 (0.1.289) the window answers it by saving the
language and showing «Language changed. Restart OGR Slip2D to see the menus
and toolbars in it.». Changing only the theme showed that notice, which was
false (the second GUI test, H2).

What these tests protect, on the real dialog:

* Save with the theme changed and the language as it is: no language
  signal, the theme signal;
* Save with another language: the language signal, with it;
* the same with Spanish as the session's language (the dialog shows it,
  and Save without touching it says nothing).

The language is restored in ``finally`` (rule 5).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from ogr_gui.i18n import current_language, set_language  # noqa: E402


def _saved(lang_in_session, choose_language=None, choose_theme="dark"):
    """Open Preferences with ``lang_in_session`` active, pick, press Save;
    returns (languages emitted, themes emitted)."""
    from ogr_gui.dialogs.preferences_dialog import PreferencesDialog
    QApplication.instance() or QApplication([])
    prev = current_language()
    langs, themes = [], []
    try:
        set_language(lang_in_session)
        dlg = PreferencesDialog(active_theme="light")
        dlg.language_changed.connect(langs.append)
        dlg.theme_changed.connect(themes.append)
        if choose_language is not None:
            dlg.cbo_language.setCurrentIndex(
                dlg.cbo_language.findData(choose_language))
        dlg.cbo_theme.setCurrentIndex(dlg.cbo_theme.findData(choose_theme))
        dlg._accept()
    finally:
        set_language(prev)
    return langs, themes


class TestTheNotice:
    def test_a_theme_change_does_not_announce_a_language(self):
        langs, themes = _saved("en")
        assert langs == []
        assert themes == ["dark"]

    def test_another_language_is_announced(self):
        langs, _themes = _saved("en", choose_language="es")
        assert langs == ["es"]

    def test_saving_spanish_as_it_is_says_nothing(self):
        langs, themes = _saved("es", choose_theme="light")
        assert langs == []
        assert themes == ["light"]

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.289 (D290) — the language (and the theme) chosen in *Preferences* is
saved and applied at the next start.

The defect: *Preferences → Language: Español → Save* set the language for
the session and said «Restart the application to fully apply translations»;
nothing stored the choice, the restart came back in English, and the menus,
toolbar and status bar — built once with ``tr()`` — never showed Spanish
(the GUI test of 0.1.284). The owner's decision: save and restart, no live
retranslation.

What these tests protect:

* a saved language and theme are read back; a value this version does not
  know is ignored;
* ``apply_saved_preferences`` sets them, and a window built AFTER it has its
  menu bar in Spanish (the reason it runs before the window is built);
* choosing a language in the window saves it and says so in that language;
  choosing a theme saves it too;
* the preferences live where ``OGR_SETTINGS_DIR`` says — the runner points
  it at a folder of its own, so no test touches the user's registry.

Each test uses a fresh folder and restores the variable, the language and
the stylesheet in ``finally`` (rule 5).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from ogr_gui import user_prefs  # noqa: E402
from ogr_gui.i18n import current_language, set_language, tr  # noqa: E402
from ogr_gui.themes import THEMES  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


class _Fresh:
    """A preferences folder of the test's own; everything put back."""

    def __enter__(self):
        self.env = os.environ.get("OGR_SETTINGS_DIR")
        self.lang = current_language()
        self.sheet = _app().styleSheet()
        self.dir = tempfile.mkdtemp(prefix="ogr_test_prefs_")
        os.environ["OGR_SETTINGS_DIR"] = self.dir
        # v0.1.292 (D302) — apply_saved_preferences installs Qt's own
        # catalogue for Spanish; whatever it installs is removed here
        self.translators = []
        return self

    def __exit__(self, *exc):
        for t in self.translators:
            if t is not None:
                _app().removeTranslator(t)
        set_language(self.lang)
        _app().setStyleSheet(self.sheet)
        if self.env is None:
            os.environ.pop("OGR_SETTINGS_DIR", None)
        else:
            os.environ["OGR_SETTINGS_DIR"] = self.env
        return False


class TestTheStore:
    def test_nothing_saved_reads_none(self):
        with _Fresh():
            assert user_prefs.saved_language() is None
            assert user_prefs.saved_theme() is None

    def test_a_saved_choice_is_read_back(self):
        with _Fresh() as f:
            user_prefs.save_language("es")
            user_prefs.save_theme("dark")
            assert user_prefs.saved_language() == "es"
            assert user_prefs.saved_theme() == "dark"
            assert os.path.exists(os.path.join(f.dir, "ogr-slip2d.ini"))

    def test_an_unknown_value_is_ignored(self):
        with _Fresh() as f:
            s = QSettings(os.path.join(f.dir, "ogr-slip2d.ini"),
                          QSettings.Format.IniFormat)
            s.setValue("language", "tlh")
            s.setValue("theme", "neon")
            s.sync()
            assert user_prefs.saved_language() is None
            assert user_prefs.saved_theme() is None


class TestTheStart:
    def test_the_saved_language_and_theme_are_applied(self):
        from ogr_gui.__main__ import apply_saved_preferences
        with _Fresh() as f:
            user_prefs.save_language("es")
            user_prefs.save_theme("dark")
            f.translators.append(apply_saved_preferences(_app()))
            assert current_language() == "es"
            assert _app().styleSheet() == THEMES["dark"]

    def test_a_window_built_after_it_has_spanish_menus(self):
        from ogr_gui.__main__ import apply_saved_preferences
        from ogr_gui.main_window import MainWindow
        with _Fresh() as f:
            user_prefs.save_language("es")
            f.translators.append(apply_saved_preferences(_app()))
            w = MainWindow()
            try:
                assert w._actions["project_settings"].text() == \
                    "Ajustes de proyecto..."
                titles = [a.text() for a in w.menuBar().actions()]
                assert "Agua subterránea" in titles, titles
            finally:
                w.close()

    def test_nothing_saved_starts_in_english(self):
        from ogr_gui.__main__ import apply_saved_preferences
        with _Fresh():
            set_language("en")
            apply_saved_preferences(_app())
            assert current_language() == "en"
            assert _app().styleSheet() == THEMES["light"]


class TestTheWindow:
    def test_choosing_a_language_saves_it_and_says_so_in_it(self):
        from ogr_gui.main_window import MainWindow
        shown = []
        raw = QMessageBox.__dict__.get("information")
        with _Fresh():
            w = MainWindow()
            QMessageBox.information = staticmethod(
                lambda _p, title, text, *a, **k: shown.append((title, text)))
            try:
                w._apply_language("es")
                assert user_prefs.saved_language() == "es"
                title, text = shown[0]
                assert title == "Idioma"
                assert text == tr("Language changed. Restart OGR Slip2D to "
                                  "see the menus and toolbars in it.")
                assert text.startswith("Idioma cambiado")
            finally:
                if raw is None:
                    del QMessageBox.information
                else:
                    QMessageBox.information = raw
                w.close()

    def test_choosing_a_theme_saves_it(self):
        from ogr_gui.main_window import MainWindow
        with _Fresh():
            w = MainWindow()
            try:
                w._apply_theme("dark")
                assert user_prefs.saved_theme() == "dark"
                assert w.active_theme == "dark"
            finally:
                w.close()

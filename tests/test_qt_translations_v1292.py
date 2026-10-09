# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.292 (D302) — Qt's own texts (the standard buttons «Yes», «No»,
«Save», «Cancel»…) follow the saved language.

The defect: with the interface in Spanish, the question of *Load Demo
Slope* had «Yes» and «No», and *Preferences* «Save» and «Cancel» (the
second GUI test, H8). Those buttons are written by Qt and translated with
Qt's own catalogue; PySide6 ships ``qtbase_es.qm`` and nothing loaded it.

What these tests protect:

* ``install_qt_translator(app, "es")`` loads the catalogue: a message box's
  Yes is «&Sí», a button box's Save is «Guardar»;
* English loads nothing (the texts are Qt's own);
* ``apply_saved_preferences`` installs it with Spanish saved;
* once removed, the buttons are English again.

Every translator installed here is removed in ``finally`` (rule 5).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox  # noqa: E402

from ogr_gui.i18n import current_language, set_language  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def _yes():
    box = QMessageBox(QMessageBox.Question, "t", "x",
                      QMessageBox.Yes | QMessageBox.No)
    return box.button(QMessageBox.Yes).text()


class TestTheCatalogue:
    def test_spanish_translates_the_standard_buttons(self):
        from ogr_gui.__main__ import install_qt_translator
        app = _app()
        t = install_qt_translator(app, "es")
        try:
            assert t is not None
            assert _yes() == "&Sí"
            bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
            assert bb.button(QDialogButtonBox.Save).text() == "Guardar"
            assert bb.button(QDialogButtonBox.Cancel).text() == "Cancelar"
        finally:
            if t is not None:
                app.removeTranslator(t)
        assert _yes() == "&Yes"

    def test_english_loads_nothing(self):
        from ogr_gui.__main__ import install_qt_translator
        assert install_qt_translator(_app(), "en") is None
        assert _yes() == "&Yes"

    def test_the_saved_spanish_installs_it(self):
        from ogr_gui import user_prefs
        from ogr_gui.__main__ import apply_saved_preferences
        app = _app()
        env = os.environ.get("OGR_SETTINGS_DIR")
        prev, sheet = current_language(), app.styleSheet()
        os.environ["OGR_SETTINGS_DIR"] = tempfile.mkdtemp(prefix="ogr_test_qt_")
        t = None
        try:
            user_prefs.save_language("es")
            t = apply_saved_preferences(app)
            assert _yes() == "&Sí"
        finally:
            if t is not None:
                app.removeTranslator(t)
            set_language(prev)
            app.setStyleSheet(sheet)
            if env is None:
                os.environ.pop("OGR_SETTINGS_DIR", None)
            else:
                os.environ["OGR_SETTINGS_DIR"] = env
        assert _yes() == "&Yes"

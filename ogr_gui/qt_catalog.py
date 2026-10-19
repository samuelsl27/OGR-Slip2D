# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Qt's own catalogue: the texts Qt writes itself, the standard buttons «Yes»,
«No», «Save», «Cancel»… (v0.1.292, D302).

v0.1.329 (D327). The catalogue was installed once, at start, for the saved
language, and choosing another language in Preferences changed every text
of the program but not Qt's: switching to English, the notice «Language
changed…» came with «Aceptar», and the «Save first?» after it with
«Guardar / Descartar / Cancelar». ``switch_qt_translator`` puts the
catalogue of the new language in place of the one it installed before, and
the window calls it before saying anything.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

#: The translator ``switch_qt_translator`` installed last, if any. Module
#: state on purpose: there is one application and one catalogue in it.
#: Tests that switch put it back with ``reset_qt_translator`` (rule 5).
_CURRENT = None


def install_qt_translator(app, lang: str):
    """Qt's catalogue for ``lang``, installed in ``app``.

    PySide6 ships ``qtbase_<lang>.qm`` in Qt's translations folder and
    nothing loaded it, so a Spanish question had «Yes» and «No». Returns
    the translator installed (the caller may remove it), or None for
    English or when the catalogue is missing."""
    if not lang or lang == "en":
        return None
    from PySide6.QtCore import QLibraryInfo, QTranslator
    translator = QTranslator(app)
    folder = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if not translator.load("qtbase_" + lang, folder):
        return None
    app.installTranslator(translator)
    return translator


def switch_qt_translator(app, lang: str):
    """Qt's catalogue for ``lang`` in place of the one this function
    installed before; English, or a missing catalogue, leaves none.
    Returns the translator now installed, or None."""
    global _CURRENT
    if _CURRENT is not None:
        app.removeTranslator(_CURRENT)
        _CURRENT = None
    _CURRENT = install_qt_translator(app, lang)
    return _CURRENT


def reset_qt_translator(app) -> None:
    """Remove the catalogue ``switch_qt_translator`` installed, if any."""
    switch_qt_translator(app, "en")

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.325 (D318) — one form for each term and one voice in the Spanish of
the interface.

The defect: the third test of the interface listed pairs that said one
thing two ways: «B-bar» and «B-barra» in the same dialog, «FEA» and
«elementos finitos», «superficie de deslizamiento» and «de rotura» in the
same sentence, «sólo» and «solo», tú («Pulsa») and usted («Pulse»), and the
English name of a method or a model inside a Spanish sentence («el método
Block Search», «un material Generalized Anisotropic»). Counted in the
dictionary, one form was always the most used, and by decision of the owner
that is the one kept:

* B-barra (4 against 3), elementos finitos (16 against 1), superficie de
  rotura (12 against 9; the dictionary's header already called it the
  standard), por defecto (19 against 1), solo and este without accent (52
  against 10, RAE 2010), tú (about 90 against 52), contorno exterior (17
  against 12);
* «Definir soporte» in the menu and the title, and the undo step of placing
  a support is «Colocar soporte», no longer the menu's own text;
* «Norma de diseño: Ninguna» (the generic «None» read «Ninguno») and the
  Preferences group «Interfaz» (it was titled «File»);
* the parameter keys of the random variables and data tips by their symbol
  (φb, φr, c∞, k_h).

Controls: «Superficie freática» stays — it is the free surface the finite
element solution computes, not the water table — and so does «malla» for
the finite-element mesh.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

_WINDOWS: list = []


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _spanish():
    from ogr_gui.i18n import _DICTS
    return _DICTS["es"]


#: The forms that left, and the one that replaces each.
RETIRED = {
    r"\bB-bar\b": "B-barra",
    r"\bFEA\b": "elementos finitos",
    r"\bsuperficies? de deslizamiento\b": "superficie de rotura",
    r"\b[Ss]ólo\b|\bSÓLO\b": "solo",
    r"\béste\b": "este",
    r"\b[Cc]ontornos? extern[oa]s?\b": "contorno exterior",
    r"\bGeneralized Anisotropic\b": "anisótropo generalizado",
    r"\bBlock Search\b": "búsqueda por bloques",
    r"\bpredeterminad[oa]s?\b": "por defecto",
}

#: Usted imperatives the dictionary used; tú is the program's voice.
USTED = (r"\b(Use|Elija|Seleccione|Introduzca|Vuelva|Pulse|Asigne|Pruebe|"
         r"Dibuje|Arranque|Ejecute|Compruebe|Revise|Defina|Aumente|Calcule|"
         r"Marque|Edite|Repita|Recalcule|Escoja|Cámbielos|Cámbielas|"
         r"revíselo|revísela|compruébela|introdúzcalo|Defínalas|"
         r"Prolónguelo)\b")


class TestOneFormForEachTerm:
    def test_no_retired_form_is_left(self):
        es = _spanish()
        for pattern in RETIRED:
            left = sorted(k for k, v in es.items() if re.search(pattern, v))
            assert not left, (pattern, left)

    def test_one_voice_tu(self):
        es = _spanish()
        left = sorted(k for k, v in es.items()
                      if re.search(USTED, v, re.IGNORECASE))
        assert not left, left

    def test_the_kept_forms_are_there(self):
        es = _spanish()
        assert es["External Boundary"] == "Contorno exterior"
        assert es["Define Support Properties"] == "Definir soporte"
        assert es["Set support"] == "Colocar soporte"
        assert es["Set support"] != es["Define Support..."].rstrip(".")
        assert es["No standard"] == "Ninguna"
        assert es["Interface"] == "Interfaz"

    def test_control_the_other_concepts_keep_their_names(self):
        es = _spanish()
        assert es["Phreatic Surface"] == "Superficie freática"
        assert es["Finite element mesh"] == "Malla de elementos finitos"


class TestTheParametersBySymbol:
    def test_random_variable_and_data_tip_keys(self):
        from ogr_gui.i18n import current_language, set_language
        from ogr_gui.labels import param_label
        before = current_language()
        try:
            set_language("es")
            assert param_label("phi_b") == "φb"
            assert param_label("phi_r") == "φr"
            assert param_label("c_inf") == "c∞"
            assert param_label("kh") == "k_h"
            # control: the English the tips have always shown
            set_language("en")
            assert param_label("phi_b") == "phi b"
        finally:
            set_language(before)


@_requires_qt
class TestTheTwoKeysOfTheirOwn:
    def test_preferences_and_the_design_standard(self):
        from PySide6.QtWidgets import QGroupBox
        from ogr_core.project.project import Project
        from ogr_gui.dialogs.preferences_dialog import PreferencesDialog
        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog)
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        QApplication.instance() or QApplication([])
        try:
            for language, group, none in (("es", "Interfaz", "Ninguna"),
                                          ("en", "Interface",
                                           "No standard")):
                set_language(language)
                pref = PreferencesDialog()
                _WINDOWS.append(pref)
                titles = [g.title() for g in pref.findChildren(QGroupBox)]
                assert group in titles, titles
                p = Project(name="D318")
                d = ProjectSettingsDialog(p.settings, None, project=p)
                _WINDOWS.append(d)
                page = next(pg for pg in d.pages
                            if type(pg).__name__ == "_DesignStandardPage")
                assert page.cbo_std.itemText(
                    page.cbo_std.findData("none")) == none
        finally:
            set_language(before)

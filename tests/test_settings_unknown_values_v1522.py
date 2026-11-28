# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D462 (v0.1.522) — the settings dialog keeps a stored value it does not know.

The invariant
-------------
Opening Project Settings and pressing OK does not change a setting nobody
touched. Up to 0.1.521 each of eleven combos chose its option with
``max(0, findData(value))``: a value the combo did not list (a ``.ogr`` of a
later version) showed as the FIRST option and ``apply()`` wrote that option
back, silently. Measured on 0.1.485 and again on 0.1.521: an
``optimized_future`` face-angle policy became ``bisector``, and an unknown
interslice-forces value became ``effective`` although the setting's default
is ``total``.

Now (``ogr_gui.combo_values.select_stored_value``) the value gets an entry of
its own, «Unknown value: <value>», selected, so ``apply()`` writes it back
intact. Checked here, for each of the eleven:

* with an unknown value, the combo shows it as unknown and ``apply()``
  returns it unchanged (fails with the ``max(0, …)`` of 0.1.521);
* with every value the combo lists, nothing is added and ``apply()`` writes
  that value (the options a project of this version sees are the same);
* the face-angle combo of a default project offers exactly its five values,
  which ``d357()`` of the bank reads.

What the analysis does with an unknown value (Sarma left out with its note,
an unknown drawdown procedure refused) is the engine's and is not tested
here.

Cost: some sixty pages, never shown and never ``exec()``-ed; about 1 s.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_UNKNOWN = "from_a_later_version"

#: (page class name, settings section, attribute, combo attribute)
_COMBOS = (
    ("_MethodsPage", "methods", "interslice_function", "cbo_f"),
    ("_MethodsPage", "methods", "interslice_forces", "cbo_zf"),
    ("_MethodsPage", "sarma", "slice_angles", "cbo_sarma_angles"),
    ("_MethodsPage", "sarma", "interslice_strength", "cbo_sarma_strength"),
    ("_MethodsPage", "sarma", "shear_sense", "cbo_sarma_sense"),
    ("_GroundwaterPage", "groundwater", "method", "cbo_method"),
    ("_GroundwaterPage", "groundwater", "rapid_drawdown_method",
     "cbo_drawdown"),
    ("_StatisticsPage", "statistics", "analysis_type", "cbo_type"),
    ("_StatisticsPage", "statistics", "sampling_method", "cbo_sampling"),
    ("_RandomNumbersPage", "random_numbers", "method", "cbo_method"),
    ("_DesignStandardPage", "design_standard", "standard", "cbo_std"),
)


def _page(page_name, settings):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ogr_gui.dialogs import project_settings_dialog as D
    return getattr(D, page_name)(settings)


def _settings(section=None, attr=None, value=None):
    from ogr_core.project.settings import ProjectSettings
    s = ProjectSettings()
    if section is not None:
        setattr(getattr(s, section), attr, value)
    return s


def _data(combo):
    return [combo.itemData(i) for i in range(combo.count())]


def _known(page_name, combo_name):
    """The data of the combo on a page of a default project. The page is
    held while it is read: a temporary one is deleted under the combo."""
    page = _page(page_name, _settings())
    return _data(getattr(page, combo_name))


class TestUnknownComboValues:

    def test_an_unknown_value_is_shown_and_kept(self):
        from ogr_gui.i18n import tr
        wrong = []
        for page_name, section, attr, combo_name in _COMBOS:
            known = _known(page_name, combo_name)
            s = _settings(section, attr, _UNKNOWN)
            page = _page(page_name, s)
            combo = getattr(page, combo_name)
            if (combo.currentData() != _UNKNOWN
                    or combo.currentText() != tr("Unknown value: %s") % _UNKNOWN
                    or _data(combo) != known + [_UNKNOWN]):
                wrong.append("%s shows %r (%r)" % (
                    combo_name, combo.currentText(), combo.currentData()))
            page.apply()
            got = getattr(getattr(s, section), attr)
            if got != _UNKNOWN:
                wrong.append("%s.%s written back as %r" % (section, attr, got))
        assert not wrong, wrong

    def test_the_unknown_entry_says_so(self):
        from PySide6.QtCore import Qt
        from ogr_gui.i18n import tr
        page = _page("_MethodsPage", _settings(
            "sarma", "slice_angles", _UNKNOWN))
        combo = page.cbo_sarma_angles
        i = combo.currentIndex()
        assert combo.itemData(i, Qt.ToolTipRole) == tr(
            "This version of the program does not know this value. It is "
            "kept as it is unless you choose another option.")
        assert combo.itemData(i, Qt.FontRole).italic()

    def test_a_known_value_changes_nothing(self):
        wrong = []
        for page_name, section, attr, combo_name in _COMBOS:
            known = _known(page_name, combo_name)
            assert known and None not in known, (combo_name, known)
            for value in known:
                s = _settings(section, attr, value)
                page = _page(page_name, s)
                combo = getattr(page, combo_name)
                if combo.currentData() != value or _data(combo) != known:
                    wrong.append("%s with %r: %r of %r" % (
                        combo_name, value, combo.currentData(), _data(combo)))
                page.apply()
                if getattr(getattr(s, section), attr) != value:
                    wrong.append("%s.%s %r not kept" % (section, attr, value))
        assert not wrong, wrong

    def test_the_face_angles_of_a_default_project(self):
        assert _known("_MethodsPage", "cbo_sarma_angles") == ["bisector", "mean_normal", "vertical",
                                "optimized_global", "optimized_all"]

    def test_the_probe_of_the_ficha(self):
        """The five values of the probe of D462, together on one page."""
        s = _settings()
        s.methods.enabled_methods = list(s.methods.enabled_methods) + ["sarma"]
        s.sarma.slice_angles = "optimized_future"
        s.sarma.interslice_strength = "by_vertex_only"
        s.sarma.shear_sense = "mixed"
        s.methods.interslice_function = "user_defined"
        s.methods.interslice_forces = "partial"
        _page("_MethodsPage", s).apply()
        assert (s.sarma.slice_angles, s.sarma.interslice_strength,
                s.sarma.shear_sense, s.methods.interslice_function,
                s.methods.interslice_forces) == (
            "optimized_future", "by_vertex_only", "mixed", "user_defined",
            "partial")

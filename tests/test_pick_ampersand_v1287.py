# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.287 (D288) — an ampersand in a label that Qt reads as a mnemonic is
drawn, not swallowed.

The defect: the list of *Pick…* said «Soil (values from Rawls, Brakensiek
 Saxton (1982)):» — the label of a ``QInputDialog`` has a buddy, so Qt reads
«&» as the mark of a keyboard shortcut and does not draw it (the GUI test of
0.1.284). The source is right everywhere else (``LIBRARY_SOURCES``, the API,
the MCP; D273). A group box title is read the same way, and «Surface Type &
Algorithm» of *Surface Options* lost its ampersand too.

What these tests protect: the text AS DRAWN — the label's text with Qt's
mnemonic rule applied («&&» → «&», «&x» → «x») — keeps the ampersand, for
Brooks-Corey and van Genuchten in the *Pick…* list and for the group box
title; and *Pick…* hands Qt that escaped text (it still calls
``QInputDialog.getItem``, which ``test_pick_library_v1279`` replaces). The
dialogs are built and read, never executed.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QGroupBox, QLabel  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def _drawn(text: str) -> str:
    """What Qt draws for a text read with mnemonics."""
    return re.sub(r"&(.)", r"\1", text)


def _hydraulic_dialog():
    from ogr_core.hydraulic import HydraulicProperties, PermeabilityModel
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_gui.dialogs.hydraulic_properties_dialog import (
        HydraulicPropertiesDialog)
    _app()
    p = Project("d288")
    m = Material(name="Soil", unit_weight=20.0,
                 strength=MohrCoulomb(cohesion=5.0, friction_angle=30.0))
    m.hydraulic = HydraulicProperties(ks=1e-6,
                                      model=PermeabilityModel.BROOKS_COREY)
    p.materials = [m]
    return HydraulicPropertiesDialog(p)


def _label_with_buddy(dialog) -> QLabel:
    labels = [lb for lb in dialog.findChildren(QLabel) if lb.buddy() is not None]
    assert len(labels) == 1, [lb.text() for lb in labels]
    return labels[0]


class TestThePickList:
    def _drawn_label(self, model):
        """The Pick list's label as Qt draws it, built as
        ``QInputDialog.getItem`` builds it (``_pick`` calls that)."""
        from PySide6.QtWidgets import QInputDialog
        dlg = _hydraulic_dialog()
        try:
            pick = QInputDialog()
            pick.setComboBoxItems(["x"])
            pick.setLabelText(dlg._pick_prompt(model))
            # the label takes its buddy when the dialog is laid out, as
            # getItem does by showing it
            pick.show()
            _app().processEvents()
            try:
                return _drawn(_label_with_buddy(pick).text())
            finally:
                pick.reject()
        finally:
            dlg.reject()

    def test_brooks_corey_keeps_its_ampersand(self):
        from ogr_core.hydraulic import PermeabilityModel
        text = self._drawn_label(PermeabilityModel.BROOKS_COREY)
        assert "Rawls, Brakensiek & Saxton (1982)" in text, text

    def test_van_genuchten_keeps_its_ampersand(self):
        from ogr_core.hydraulic import PermeabilityModel
        text = self._drawn_label(PermeabilityModel.VAN_GENUCHTEN)
        assert "Carsel & Parrish (1988)" in text, text

    def test_pick_hands_the_prompt_to_qt(self):
        """``_pick`` shows the escaped prompt, not the raw label."""
        from PySide6.QtWidgets import QInputDialog
        from ogr_core.hydraulic import PermeabilityModel
        dlg = _hydraulic_dialog()
        seen = []

        def fake(_parent, _title, label, items, *_a, **_k):
            seen.append(label)
            return items[0], False

        raw = QInputDialog.__dict__.get("getItem")
        QInputDialog.getItem = staticmethod(fake)
        try:
            dlg.cbo_model.setCurrentIndex(
                dlg.cbo_model.findData(PermeabilityModel.BROOKS_COREY))
            dlg._pick()
        finally:
            if raw is None:
                del QInputDialog.getItem
            else:
                QInputDialog.getItem = raw
            dlg.reject()
        assert seen == [dlg._pick_prompt(PermeabilityModel.BROOKS_COREY)]


class TestTheGroupBoxTitle:
    def test_surface_options_keeps_its_ampersand(self):
        from ogr_core.project import Project
        from ogr_gui.dialogs.grid_dialogs import SurfaceOptionsDialog
        _app()
        dlg = SurfaceOptionsDialog(Project("d288"))
        try:
            titles = [_drawn(g.title()) for g in dlg.findChildren(QGroupBox)]
            assert "Surface Type & Algorithm" in titles, titles
        finally:
            dlg.reject()

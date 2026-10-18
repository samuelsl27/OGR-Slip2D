# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.322 (D300, the supports) — the support types read in the interface
language: their names, descriptions, parameter rows and help, tabs, and the
application and orientation of their force.

The defect: the support family came from ogr_core in English and reached the
screen without ``tr()``:

* ``DISPLAY_NAME`` and ``DESCRIPTION`` of each type (Define Support, the
  type of a support, a pattern, the tooltip on the canvas, the data tip);
* each parameter row of Define Support, labelled with its key in title case
  («Out Of Plane Spacing:»), and its help, the core's description;
* the tabs of the parameter editor (``PARAMETER_TABS``);
* the application and the orientation of the force, written as the enum's
  value — «Tangent To Slip» in three dialogs and «Tangent to slip surface»
  in a fourth, two English names for one thing.

Now the row keeps the label it has always had in English and goes through
``tr()``; each key is written once in Spanish and gives both its row label
and the key the data tips and random variables show. The name the user gave
a set (``_display_name``) is data and is shown as it is. The application
and orientation have one table, in ``ogr_gui.labels``.

The supports' exceptions of test_labels_spanish_v1321's screen test are
gone with this version; that test's ghost check is what makes sure.

Controls: in English the rows, the data tips and the random variables read
what they always read.
"""
from __future__ import annotations

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


def _types():
    from ogr_core.support import support_registry
    return list(support_registry().values())


def _row_label(key):
    return key.replace("_", " ").title() + ":"


class TestEverySupportTextHasSpanish:
    def test_names_and_descriptions(self):
        es = _spanish()
        missing = [t for cls in _types()
                   for t in (cls.DISPLAY_NAME, cls.DESCRIPTION)
                   if t not in es]
        assert not missing, missing

    def test_every_parameter_its_row_its_key_and_its_help(self):
        es = _spanish()
        missing = sorted({t for cls in _types()
                          for key, (_d, _u, desc) in cls.PARAMETERS.items()
                          for t in (_row_label(key), key.replace("_", " "),
                                    desc)
                          if t not in es})
        assert not missing, missing

    def test_the_row_label_and_the_key_say_the_same(self):
        """Written once per key, so the row and the data tip cannot drift
        apart."""
        es = _spanish()
        for cls in _types():
            for key in cls.PARAMETERS:
                row = es[_row_label(key)]
                assert row == es[key.replace("_", " ")].capitalize() + ":" \
                    or row[:-1].lower() == es[key.replace("_", " ")], key

    def test_every_tab(self):
        es = _spanish()
        same = {"Geometry", "Pullout", "Tensile"}   # already in the dict
        tabs = {t for cls in _types()
                for t in (getattr(cls, "PARAMETER_TABS", None) or {})}
        assert tabs and all(t in es for t in tabs), \
            sorted(t for t in tabs if t not in es)
        assert same <= tabs


def _define_support(language):
    from ogr_core.project.project import Project
    from ogr_gui.dialogs.define_support_dialog import DefineSupportDialog
    from ogr_gui.i18n import set_language
    QApplication.instance() or QApplication([])
    set_language(language)
    d = DefineSupportDialog(Project(name="D300"))
    _WINDOWS.append(d)
    return d


def _panel_texts(panel):
    from PySide6.QtWidgets import QLabel, QTabWidget, QWidget
    out = []
    for w in panel.findChildren(QWidget):
        if isinstance(w, QLabel) and w.text():
            out.append(w.text())
        if w.toolTip():
            out.append(w.toolTip())
        if isinstance(w, QTabWidget):
            out += [w.tabText(i) for i in range(w.count())]
    return out


@_requires_qt
class TestDefineSupportSpeaksSpanish:
    def test_every_type_its_rows_help_and_tabs(self):
        from ogr_gui.i18n import current_language, set_language, tr
        before = current_language()
        try:
            d = _define_support("es")
            checked = 0
            for cls in _types():
                d.param_panel.set_type(cls)
                shown = _panel_texts(d.param_panel)
                for key, (_d, _u, desc) in cls.PARAMETERS.items():
                    assert tr(_row_label(key)) in shown, (cls.TYPE_ID, key)
                    assert _row_label(key) not in shown, (cls.TYPE_ID, key)
                    assert tr(desc) in shown, (cls.TYPE_ID, key)
                    checked += 1
                for tab in (getattr(cls, "PARAMETER_TABS", None) or {}):
                    assert tr(tab) in shown, (cls.TYPE_ID, tab)
            assert checked > 50, checked
            types = [d.cbo_type.itemText(i) for i in range(d.cbo_type.count())]
            assert "Anclado en el extremo" in types, types
            app = [d.cbo_app.itemText(i) for i in range(d.cbo_app.count())]
            assert app == ["Activa", "Pasiva"], app
            ori = [d.cbo_ori.itemText(i) for i in range(d.cbo_ori.count())]
            assert "Tangente a la superficie de rotura" in ori, ori
        finally:
            set_language(before)

    def test_control_in_english_the_rows_are_what_they_were(self):
        from ogr_core.support import EndAnchored
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        try:
            d = _define_support("en")
            d.param_panel.set_type(EndAnchored)
            shown = _panel_texts(d.param_panel)
            assert "Out Of Plane Spacing:" in shown, shown
            assert "Anchor Capacity:" in shown, shown
            ori = [d.cbo_ori.itemText(i) for i in range(d.cbo_ori.count())]
            assert "Tangent to slip surface" in ori, ori
        finally:
            set_language(before)


@_requires_qt
class TestTheOtherSupportDialogsShareOneName:
    def test_properties_pattern_and_modify_pattern(self):
        """Three dialogs wrote the orientation as ``value.title()`` («Tangent
        To Slip»); they now say what Define Support says."""
        from ogr_core.geometry import Vertex
        from ogr_core.project.project import Project
        from ogr_core.support import EndAnchored, SupportInstance
        from ogr_gui.dialogs.support_properties_dialog import (
            SupportInstancePropertiesDialog)
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        try:
            for language, want in (
                    ("es", "Tangente a la superficie de rotura"),
                    ("en", "Tangent to slip surface")):
                QApplication.instance() or QApplication([])
                set_language(language)
                p = Project(name="D300")
                st = EndAnchored(anchor_capacity=120.0,
                                 out_of_plane_spacing=1.0)
                p.support_types = [st]
                s = SupportInstance(type_id=st.TYPE_ID, type_ref=st.id,
                                    head=Vertex(30.0, 20.0),
                                    tail=Vertex(36.0, 17.0))
                p.supports.append(s)
                d = SupportInstancePropertiesDialog(s, p, None)
                _WINDOWS.append(d)
                ori = [d.cbo_ori.itemText(i)
                       for i in range(d.cbo_ori.count())]
                assert want in ori, ori
                assert "Tangent To Slip" not in ori, ori
        finally:
            set_language(before)


class TestTheSupportTipAndVariable:
    def test_the_data_tip(self):
        from ogr_core.geometry import Vertex
        from ogr_core.project.project import Project
        from ogr_core.support import GroutedTieback, SupportInstance
        from ogr_gui.data_tips import DataTipMode, support_tip
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        p = Project(name="D300")
        st = GroutedTieback()
        p.support_types = [st]
        s = SupportInstance(type_id=st.TYPE_ID, type_ref=st.id,
                            head=Vertex(30.0, 20.0), tail=Vertex(36.0, 17.0))
        p.supports.append(s)
        try:
            set_language("es")
            tip = support_tip(s, DataTipMode.MAXIMUM, project=p)
            assert tip.splitlines()[0] == "Anclaje inyectado", tip
            assert "capacidad a tracción" in tip, tip
            assert "aplicación: " in tip, tip
            # control: the English the tip has always shown
            set_language("en")
            tip = support_tip(s, DataTipMode.MAXIMUM, project=p)
            assert tip.splitlines()[0] == "Grouted Tieback", tip
            assert "tensile capacity" in tip, tip
        finally:
            set_language(before)

    def test_the_random_variable(self):
        from ogr_core.statistics import Distribution, DistributionType
        from ogr_core.statistics.random_variables import (RandomVariable,
                                                          VariableKind)
        from ogr_gui.i18n import current_language, set_language
        from ogr_gui.labels import random_variable_label
        before = current_language()
        rv = RandomVariable(kind=VariableKind.SUPPORT, target_id="t",
                            param="anchor_capacity",
                            label="End Anchored — anchor_capacity",
                            distribution=Distribution(
                                DistributionType.NORMAL, mean=1.0))
        try:
            set_language("es")
            assert random_variable_label(rv) == \
                "Anclado en el extremo — capacidad del anclaje"
            assert rv.label == "End Anchored — anchor_capacity"
            set_language("en")
            assert random_variable_label(rv) == \
                "End Anchored — anchor capacity"
        finally:
            set_language(before)

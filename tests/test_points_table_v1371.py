# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.371 (D352) — the points table of a function strength model shows three
rows and every heading whole, in its four kinds.

The finding (the fifth interface test, 0.1.355, H1; 1920 × 1080 at 125 %,
1536 × 864 logical pixels for Qt): with "Función tangencial/normal" the
table of points was one row tall and its first heading read «nsión normal
(kF» instead of «Tensión normal (kPa)». Read: ``_build_points_table`` asked
for no height and left the columns at Qt's default width, in the four kinds
of table it builds (``points``, ``rows3``, ``cphi``, ``rules``). D321
(0.1.326) fixed the texts this dialog cut, and did not look at its tables:
the dialog census opens Mohr-Coulomb materials, which have none.

Measured on that screen before writing (Windows platform, the dialog laid
out without being shown): 1.2 rows for the points, 1.0 for the three-column
tables, 0.5 for the rules of Generalized Anisotropic. And three rows did not
fit by asking for height alone: General, Strength and Water stacked in one
column made the dialog 818 px tall with the rules, on 816 px of screen. By
the owner's decision the column scrolls (``VerticalScrollArea``, as the
hydraulic dialog and Project Settings), and the window does not grow.

What these tests protect, with the dialogs SHOWN (a widget that was never
shown has no real size: the canvas of 98 × 28 px), in Spanish with Qt's own
catalogue, at the theme's font and one point bigger:

* Define Materials, in the four kinds, at the size it opens at and at its
  minimum: three rows and every heading whole (each column at least its
  text by the header's font plus the style's margins: when the columns do
  not fit, the table scrolls sideways instead of cutting a heading), and the
  column never scrolls sideways;
* it still opens at what its content asks for: no vertical bar on a
  Mohr-Coulomb material, the size it had before the scroll area (its
  minimum with the column holding everything), and choosing a model with a
  table does not grow the window;
* the strength function of a Snowden material, the other dialog of the same
  panel and one without a scroll area, at its minimum: three rows and its
  headings whole. Without the table's minimum height it keeps a third of a
  row (measured), so this is the test that shows the minimum moves
  something (rule 7).
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

#: A model of each kind of table.
_KINDS = {"points": "shear_normal_function",
          "rows3": "anisotropic_strength_function",
          "cphi": "c_phi_function",
          "rules": "generalized_anisotropic"}


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _materials():
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    return [Material(name=n, strength=MohrCoulomb(cohesion=5.0,
                                                  friction_angle=30.0))
            for n in ("Arcilla", "Roca")]


@contextmanager
def _bigger_font(extra):
    app = _app()
    base = app.font()
    if extra:
        font = type(base)(base)
        font.setPointSizeF(base.pointSizeF() + extra)
        app.setFont(font)
    try:
        yield
    finally:
        app.setFont(base)


@contextmanager
def _spanish(extra):
    import test_dialogs_fit_v1315 as fit
    with _bigger_font(extra), fit._spanish_with("light") as app, \
            fit._no_modals():
        yield app


def _settle(app):
    for _ in range(3):
        app.processEvents()


def _table(tbl):
    """``(rows_seen, [(heading, width, needs)])`` of a shown table."""
    from PySide6.QtWidgets import QStyle
    hh = tbl.horizontalHeader()
    rows = (tbl.viewport().height()
            / tbl.verticalHeader().defaultSectionSize())
    margin = hh.style().pixelMetric(QStyle.PM_HeaderMargin, None, hh)
    cols = []
    for c in range(tbl.columnCount()):
        text = tbl.horizontalHeaderItem(c).text()
        cols.append((text, hh.sectionSize(c),
                     hh.fontMetrics().horizontalAdvance(text) + 2 * margin))
    return rows, cols


def _bad(where, rows, cols):
    out = []
    if rows < 3:
        out.append((where, "rows", round(rows, 2)))
    for text, width, needs in cols:
        if width < needs:
            out.append((where, text, width, needs))
    return out


def _define_materials(extra=0.0):
    """What Define Materials shows: the problems found, its opening size,
    whether the column scrolled at opening, and the sizes after each kind
    was chosen."""
    from PySide6.QtWidgets import QScrollArea

    from ogr_gui.dialogs.material_properties_dialog import (
        MaterialPropertiesDialog)
    bad, sizes = [], []
    with _spanish(extra) as app:
        dlg = MaterialPropertiesDialog(_materials(), None)
        try:
            dlg.show()
            _settle(app)
            opened = (dlg.width(), dlg.height())
            # read without the column too, so that the tree before this
            # version fails on what it showed and not on an attribute
            area = getattr(dlg, "scroll", None)
            area = area if isinstance(area, QScrollArea) else None
            bar_at_opening = (area is not None
                              and area.verticalScrollBar().isVisible())
            editor = getattr(dlg, "_editor", None)
            content = (editor.minimumSizeHint().height()
                       if editor is not None else 0)
            for at in ("open", "minimum"):
                if at == "minimum":
                    dlg.resize(dlg.minimumSizeHint())
                    _settle(app)
                for kind, model in _KINDS.items():
                    i = dlg.cbo_strength.findData(model)
                    assert i >= 0, model
                    dlg.cbo_strength.setCurrentIndex(i)
                    _settle(app)
                    assert dlg.param_panel._table_kind == kind, kind
                    rows, cols = _table(dlg.param_panel._table)
                    bad += _bad((at, kind), rows, cols)
                    if (area is not None
                            and area.horizontalScrollBar().isVisible()):
                        bad.append((at, kind, "the column scrolls sideways"))
                    if at == "open":
                        sizes.append((kind, dlg.width(), dlg.height()))
                        headings = [t for t, _w, _n in cols]
                        if kind == "points":
                            # the premise of the ticket, with its units
                            assert headings[0].startswith(
                                "Tensión normal ("), headings
        finally:
            dlg.close()
    return bad, opened, bar_at_opening, content, sizes


class TestDefineMaterials:

    def test_three_rows_and_whole_headings(self):
        bad, *_ = _define_materials()
        assert not bad, bad

    def test_one_point_bigger(self):
        bad, *_ = _define_materials(extra=1.0)
        assert not bad, bad

    def test_it_opens_at_its_content_and_does_not_grow(self):
        _bad_, opened, bar, content, sizes = _define_materials()
        assert not bar, "the column scrolls on a Mohr-Coulomb material"
        assert opened[0] >= 720 and opened[1] >= 500, opened
        # the column holds everything it shows at opening
        assert opened[1] >= content, (opened, content)
        grown = [s for s in sizes if (s[1], s[2]) != opened]
        assert not grown, (opened, grown)


class TestTheStrengthFunction:
    """The bedding and rock mass functions of a Snowden material: the same
    panel, in a dialog without a scroll area."""

    def _check(self, extra):
        from ogr_gui.dialogs.material_properties_dialog import (
            StrengthFunctionDialog)
        bad = []
        with _spanish(extra) as app:
            for kind in ("shear_normal_function", "c_phi_function"):
                dlg = StrengthFunctionDialog({"model_id": kind}, title="f")
                try:
                    dlg.show()
                    _settle(app)
                    dlg.resize(dlg.minimumSizeHint())
                    _settle(app)
                    bad += _bad(kind, *_table(dlg.panel._table))
                finally:
                    dlg.close()
        assert not bad, bad

    def test_at_its_minimum(self):
        self._check(0.0)

    def test_at_its_minimum_one_point_bigger(self):
        self._check(1.0)

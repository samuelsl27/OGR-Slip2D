# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Query Slice Data: the panel shows the reference's numbers, not dashes.

WHAT INVARIANT THIS PROTECTS.

The panel listed four of the most interesting quantities on a slice —
base normal force, shear force, shear strength, effective normal stress —
and printed "—" for every one of them. They are not attributes of a
Slice: the METHOD computes them and stores them on the LEMResult, in
per-slice arrays. A panel handed only the slice could never reach them,
so the dashes were structural rather than a missing calculation.

The numbers themselves are checked against the reference's own Slice Data
table (Slide2d_Ej_2_General.htm), which is what makes this a validation
and not a snapshot of what the code prints today. Row 1 of the global
minimum for ordinary/fellenius:

    width 1.04705 m | weight 9.40306 kN | c 26 kPa | phi 30 deg
    shear stress 27.8907 | shear strength 31.082
    base normal stress 8.80223 | pore pressure 0 | effective 8.80223

That table also settles a definition this panel got wrong on its first
attempt. ``base_shear_force`` in a LEMResult is ``W·sin(alpha)``, the
force DRIVING the slice, and labelling it "mobilised shear" is wrong:
31.082 / 1.11442 = 27.8907 shows the reference's "Shear Stress" is
tau_f / F, the strength divided by the factor of safety. The two differ
by exactly the factor of safety, which is the entire point of the number.

Reference: Slide Interpret > Slip Surfaces > Query > Query Slice Data —
"Click on any slice, and the data for the slice will be displayed in the
dialog. Force arrows will also be displayed on the slice".

Author: Samuel Sáez López (UPCT)
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


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_WINDOWS = []

# Row 1 of the reference's Slice Data table, ordinary/fellenius global
# minimum of Ej_2. FS there is 1.11442.
REFERENCE_ROW_1 = {
    "Width b (m)": 1.04705,
    "Weight W (kN)": 9.40306,
    "Base cohesion c (kPa)": 26.0,
    "Base friction angle φ (°)": 30.0,
    "Shear strength τ_f (kPa)": 31.082,
    "Mobilised shear τ_m = τ_f/F (kPa)": 27.8907,
    "Base normal stress σₙ (kPa)": 8.80223,
    "Effective normal σ′ₙ (kPa)": 8.80223,
    "Pore pressure u (kPa)": 0.0,
}


def _ej2_reference_result():
    """The reference SMALL critical circle, sliced and solved."""
    from test_slide_validation_ej2_v184 import _ej2_project, SMALL, NUM_SLICES
    from ogr_slip2d.methods import get_method
    from ogr_slip2d.search import GridSearch
    from ogr_slip2d.surface import SlipCircle
    p = _ej2_project()
    cx, cy, r = SMALL
    gs = GridSearch(method=get_method("ordinary_fellenius")(),
                    num_slices=NUM_SLICES, min_area=0.0)
    return p, gs.evaluate_circle(
        p, SlipCircle(centre_x=cx, centre_y=cy, radius=r))


def _field(label, s, res):
    from ogr_gui.interpret_window import _SliceDataDock
    for lab, getter in _SliceDataDock.FIELDS:
        if lab == label:
            return getter(s, res)
    raise AssertionError(f"no such field: {label}")


def _interpret():
    from test_slide_validation_ej1 import _ej1_project
    import ogr_slip2d as M
    from ogr_gui.i18n import set_language
    from ogr_gui.interpret_window import InterpretWindow
    from ogr_slip2d.search import GridSearch
    QApplication.instance() or QApplication([])
    set_language("en")
    p = _ej1_project()
    r = GridSearch(method=M.BishopSimplified(), grid_x=(70, 100),
                   grid_y=(58, 84), grid_nx=4, grid_ny=4,
                   radius_increment=8, min_radius=12, num_slices=14,
                   min_area=0.5).run(p)
    w = InterpretWindow(p, {"bishop_simplified": r}, None)
    w.canvas.resize(800, 600)
    w.canvas.show()
    _WINDOWS.append(w)
    return p, r, w


def _click(view, scene_x, scene_y):
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import Qt, QPointF, QEvent
    pos = QPointF(view.mapFromScene(QPointF(scene_x, scene_y)))
    view.mousePressEvent(QMouseEvent(
        QEvent.MouseButtonPress, pos, view.mapToGlobal(pos),
        Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))


def _click_slice(w, s):
    _click(w.canvas, 0.5 * (s.base_x_left + s.base_x_right),
           0.5 * (s.base_y_left + s.base_y_right))


# ======================================================================
class TestThePanelMatchesTheReference:
    """Numbers, against the reference's own Slice Data table."""

    def test_every_reference_column_agrees(self):
        _p, res = _ej2_reference_result()
        assert res is not None and res.is_valid
        s = res.slices[0]
        for label, ref in REFERENCE_ROW_1.items():
            got = _field(label, s, res)
            assert got != "—", f"{label} is still a dash"
            got = float(got)
            if ref == 0.0:
                assert abs(got) < 1e-6, (label, got)
            else:
                assert abs(got - ref) / abs(ref) < 0.005, (label, got, ref)

    def test_mobilised_shear_is_the_strength_over_the_factor(self):
        """The definition the first attempt got wrong.

        W·sin(alpha) is a different quantity and is reported separately.
        If these two were ever equal the factor of safety would be 1.
        """
        _p, res = _ej2_reference_result()
        s = res.slices[0]
        tau_f = float(_field("Shear strength τ_f (kPa)", s, res))
        tau_m = float(_field("Mobilised shear τ_m = τ_f/F (kPa)", s, res))
        # Both come back rounded to the two decimals the panel displays,
        # so the identity can only be checked to that precision — the
        # tolerance is display resolution, not physics.
        assert abs(tau_m - tau_f / res.fos) < 0.02, (tau_m, tau_f, res.fos)
        # W·sin(alpha) is a different quantity. On this slice it is not
        # even close: mistaking one for the other is what the first
        # version of this panel did.
        driving = float(_field("Driving shear W·sinα (kN)", s, res))
        assert abs(driving - tau_m * s.base_length) > 0.1, driving

    def test_strength_follows_mohr_coulomb_at_the_base(self):
        """tau_f = c + sigma'_n tan(phi), with the base's own parameters."""
        import math
        _p, res = _ej2_reference_result()
        for s in res.slices[:5]:
            c = float(_field("Base cohesion c (kPa)", s, res))
            phi = float(_field("Base friction angle φ (°)", s, res))
            sig = float(_field("Effective normal σ′ₙ (kPa)", s, res))
            tau = float(_field("Shear strength τ_f (kPa)", s, res))
            expected = c + max(0.0, sig) * math.tan(math.radians(phi))
            assert abs(tau - expected) < 0.05, (s.index, tau, expected)


# ======================================================================
@_requires_qt
class TestClickingASliceFillsThePanel:
    def test_no_field_the_method_can_compute_is_left_as_a_dash(self):
        """The whole complaint: the panel was there and always empty.

        v0.1.91 — the interslice rows are excluded, and the exclusion is
        the point rather than a concession. This panel is driven with
        Bishop, which does not FORM interslice forces at all: it assumes
        the interslice shear is zero. A dash there is the honest answer,
        and the row beside it says so in words. Printing a number would be
        printing the solver's assumption as if it were a result — the
        mistake v0.1.82 removed from the line of thrust.

        A method that does solve them fills these in; that is asserted in
        tests/test_slice_panel_buttons_v191.py, on Spencer.
        """
        _p, r, w = _interpret()
        w._query_slice()
        s = w._query_slice_target.slices[5]
        _click_slice(w, s)
        t = w.slice_dock.table
        interslice = {"E left (kN)", "E right (kN)",
                      "X left (kN)", "X right (kN)"}
        blanks = [t.item(i, 0).text() for i in range(t.rowCount())
                  if t.item(i, 1).text() == "—"]
        unexpected = [b for b in blanks if b not in interslice]
        assert unexpected == [], unexpected
        # And the exclusion must not become a hole: with a method that
        # does not resolve them, all four have to be dashes, not some.
        assert sorted(b for b in blanks if b in interslice) == sorted(
            interslice), blanks

    def test_clicking_another_slice_updates_it(self):
        _p, r, w = _interpret()
        w._query_slice()
        slices = w._query_slice_target.slices
        _click_slice(w, slices[3])
        first = w.slice_dock.table.item(1, 1).text()
        _click_slice(w, slices[8])
        second = w.slice_dock.table.item(1, 1).text()
        assert first != second, (first, second)

    def test_the_selected_slice_is_drawn_with_force_arrows(self):
        _p, r, w = _interpret()
        w._query_slice()
        _click_slice(w, w._query_slice_target.slices[5])
        items = [it for it in w.canvas.scene().items()
                 if getattr(it, "_is_slice_highlight", False)]
        # One body + three arrows, each a shaft and two barbs.
        assert len(items) >= 4, len(items)

    def test_only_one_slice_is_highlighted_at_a_time(self):
        _p, r, w = _interpret()
        w._query_slice()
        slices = w._query_slice_target.slices
        _click_slice(w, slices[3])
        n_one = len([it for it in w.canvas.scene().items()
                     if getattr(it, "_is_slice_highlight", False)])
        _click_slice(w, slices[8])
        n_two = len([it for it in w.canvas.scene().items()
                     if getattr(it, "_is_slice_highlight", False)])
        assert n_one == n_two, (n_one, n_two)

    def test_a_click_outside_says_so_and_changes_nothing(self):
        _p, r, w = _interpret()
        w._query_slice()
        _click_slice(w, w._query_slice_target.slices[5])
        before = w.slice_dock.table.item(1, 1).text()
        _click(w.canvas, 500.0, 500.0)
        assert w.slice_dock.table.item(1, 1).text() == before


# ======================================================================
@_requires_qt
class TestShowSlicesCoversEveryQuery:
    """"Show Slices ... applies to ALL QUERIES IN THE CURRENT VIEW"."""

    def test_two_queries_get_two_sets_of_slice_lines(self):
        _p, r, w = _interpret()
        picks = sorted({(e.surface.to_dict()["centre_x"],
                         e.surface.to_dict()["centre_y"]) for e in r.valid()})
        assert len(picks) >= 2
        for cx, cy in picks[:2]:
            w._add_query()
            _click(w.canvas, cx, cy)
        assert len(w._queries()) == 2
        w._act_show_slices.setChecked(True)
        drawn = [it for it in w.canvas.scene().items()
                 if getattr(it, "_is_slice_line", False)]
        expected = sum(len(q.slices) for q in w._queries())
        assert len(drawn) == expected, (len(drawn), expected)

    def test_with_no_query_it_still_shows_the_global_minimum(self):
        """The documented shortcut must survive the change."""
        _p, r, w = _interpret()
        w._act_show_slices.setChecked(True)
        assert len(w._queries()) == 1
        drawn = [it for it in w.canvas.scene().items()
                 if getattr(it, "_is_slice_line", False)]
        assert len(drawn) == len(w._queries()[0].slices)


# ======================================================================
class TestThePanelSpeaksSpanish:
    def test_every_field_label_has_a_spanish_entry(self):
        """Rule 2. The labels are translated through a VARIABLE, so the
        coverage test cannot see them and they need their own case."""
        from ogr_gui.i18n import _DICTS
        from ogr_gui.interpret_window import _SliceDataDock
        es = _DICTS["es"]
        missing = [lab for lab, _ in _SliceDataDock.FIELDS if lab not in es]
        assert missing == [], missing

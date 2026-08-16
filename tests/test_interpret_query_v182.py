# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.82 — Interpret: Filter Surfaces, Export Raw Data, Line of Thrust.

**The invariant these protect is project rule 7**: a control that does not
change the result is worse than no control, because the user believes the
analysis honours it. Two entries in this window were exactly that:

* *Filter Surfaces* opened a dialog, computed ``self._fos_filter`` and
  reported "filter active" on the status bar — and **nothing ever read the
  attribute**. Every surface went on being drawn.
* *Text during Query* was a checkable menu entry connected to nothing at
  all, and *Query Invalid Surfaces* opened a summary rather than governing
  what Add Query shows.

*Show Line of Thrust* was a third case of the same family, one step
subtler: it was always enabled, including for Bishop, Janbu and Ordinary,
which assume the interslice forces away. A thrust line drawn there is
computed from an assumption, not from a result, and the reference lists
those methods as unavailable for that reason.

*Export Raw Data* pointed at the slice-data CSV, which is a different
export. The reference's raw data is one row per SURFACE — centre, radius,
the two slope intersections, and the factor of safety **or a negative
error code in its place**; the rows carrying error codes are precisely the
ones that explain a blank patch in the contoured grid.
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


def _interpret(methods=("bishop_simplified",)):
    from test_slide_validation_ej1 import _ej1_project

    import ogr_slip2d as M
    from ogr_gui.i18n import set_language
    from ogr_gui.interpret_window import InterpretWindow
    from ogr_slip2d.search import GridSearch
    QApplication.instance() or QApplication([])
    set_language("en")
    cls = {"bishop_simplified": M.BishopSimplified,
           "spencer": M.Spencer}
    p = _ej1_project()
    results = {}
    for mid in methods:
        results[mid] = GridSearch(
            method=cls[mid](), grid_x=(70, 100), grid_y=(58, 84),
            grid_nx=4, grid_ny=4, radius_increment=8, min_radius=12,
            num_slices=14, min_area=0.5).run(p)
    w = InterpretWindow(p, results, None)
    _WINDOWS.append(w)
    return p, results[methods[0]], w


def _drawn(w):
    from ogr_gui.canvas.canvas_view import SlipSurfaceItem
    return [it for it in w.canvas._result_items
            if isinstance(it, SlipSurfaceItem)]


# ======================================================================
@_requires_qt
class TestFilterSurfacesActuallyFilters:
    def test_a_range_removes_surfaces(self):
        _p, r, w = _interpret()
        w._set_surface_mode("all")
        before = len(_drawn(w))
        assert before > 3
        cut = r.critical.fos + 0.2
        w._fos_filter = (0.0, cut, None)
        w._refresh_canvas_with_highlights()
        after = _drawn(w)
        assert len(after) < before, (len(after), before)
        assert all(it.fos <= cut or it.is_critical for it in after)

    def test_lowest_n_keeps_exactly_n(self):
        _p, _r, w = _interpret()
        w._set_surface_mode("all")
        w._fos_filter = (None, None, 5)
        w._refresh_canvas_with_highlights()
        assert len(_drawn(w)) == 5

    def test_the_global_minimum_survives_any_filter(self):
        """A filter is a way of looking at the result, not a way of
        hiding its answer: losing the global minimum is how a reader ends
        up quoting the wrong number."""
        _p, r, w = _interpret()
        w._set_surface_mode("all")
        w._fos_filter = (r.critical.fos + 1.0, 99.0, None)
        w._refresh_canvas_with_highlights()
        assert any(it.is_critical for it in _drawn(w))

    def test_clearing_the_filter_restores_everything(self):
        _p, _r, w = _interpret()
        w._set_surface_mode("all")
        full = len(_drawn(w))
        w._fos_filter = (None, None, 3)
        w._refresh_canvas_with_highlights()
        assert len(_drawn(w)) == 3
        w._fos_filter = None
        w._refresh_canvas_with_highlights()
        assert len(_drawn(w)) == full

    def test_the_filter_reaches_minimum_surfaces_too(self):
        _p, _r, w = _interpret()
        w._set_surface_mode("minimum")
        full = len(_drawn(w))
        w._fos_filter = (None, None, 2)
        w._refresh_canvas_with_highlights()
        assert len(_drawn(w)) < full


# ======================================================================
@_requires_qt
class TestSurfacesWithErrorCode:
    """The reference's third filtering mode, and it is a view of its own:
    ONLY the invalid surfaces of one error code, in purple, with the valid
    ones hidden. The question is "what failed here", not "how does this
    compare"."""

    def test_it_shows_only_that_error_code(self):
        _p, r, w = _interpret()
        reasons = w._invalid_reasons()
        if not reasons:
            return                      # nothing failed on this grid
        why, count = reasons[0]
        w._set_surface_mode("all")
        w._error_filter = why
        w._refresh_canvas_with_highlights()
        drawn = _drawn(w)
        assert drawn, why
        assert len(drawn) <= count
        ids = {it.surface_dict.get("id") for it in drawn}
        for ev in r.evaluations:
            if ev.surface.to_dict().get("id") in ids:
                assert w.invalid_reason(ev) == why

    def test_no_valid_surface_is_drawn(self):
        _p, _r, w = _interpret()
        reasons = w._invalid_reasons()
        if not reasons:
            return
        w._error_filter = reasons[0][0]
        w._refresh_canvas_with_highlights()
        assert all(not it.is_critical for it in _drawn(w))

    def test_clearing_it_restores_the_normal_view(self):
        _p, _r, w = _interpret()
        w._set_surface_mode("all")
        normal = len(_drawn(w))
        reasons = w._invalid_reasons()
        if not reasons:
            return
        w._error_filter = reasons[0][0]
        w._refresh_canvas_with_highlights()
        w._error_filter = None
        w._refresh_canvas_with_highlights()
        assert len(_drawn(w)) == normal


# ======================================================================
@_requires_qt
class TestGraphSFAlongSlope:
    """v0.1.82 — this plotted the CRITICAL surface only, and gave every
    slice the global factor of safety ("very coarse: treat every slice
    with the global FoS"). What that draws is a horizontal line: one
    number, repeated. The option exists to show WHERE on the slope the low
    factors of safety daylight, so it has to use every valid surface and
    its two slope intercepts."""

    def test_it_uses_every_valid_surface_not_just_the_critical(self):
        _p, r, w = _interpret()
        xs, ys = w.sf_along_slope_series(bins=None)
        assert len(xs) == 2 * len(list(r.valid())), (len(xs),
                                                     len(list(r.valid())))

    def test_it_is_not_a_horizontal_line(self):
        """The defect, pinned: the old plot had a single distinct y."""
        _p, _r, w = _interpret()
        _xs, ys = w.sf_along_slope_series(bins=None)
        assert len(set(round(y, 6) for y in ys)) > 1

    def test_one_intercept_gives_half_the_points(self):
        _p, _r, w = _interpret()
        both = len(w.sf_along_slope_series(True, True, None)[0])
        left = len(w.sf_along_slope_series(True, False, None)[0])
        right = len(w.sf_along_slope_series(False, True, None)[0])
        assert left + right == both
        assert left > 0 and right > 0

    def test_binning_takes_the_minimum_in_each_bin(self):
        _p, _r, w = _interpret()
        xs_all, ys_all = w.sf_along_slope_series(bins=None)
        xs_b, ys_b = w.sf_along_slope_series(bins=8)
        assert 0 < len(xs_b) <= 8
        assert len(xs_b) < len(xs_all)
        # Every binned value must be a value that actually occurs, and the
        # overall minimum has to survive the binning — it is the whole
        # point of the reading.
        assert min(ys_b) == min(ys_all)
        for y in ys_b:
            assert y in ys_all

    def test_bins_are_ordered_along_the_slope(self):
        _p, _r, w = _interpret()
        xs, _ys = w.sf_along_slope_series(bins=12)
        assert xs == sorted(xs)


# ======================================================================
@_requires_qt
class TestExportRawData:
    def test_one_row_per_surface_analysed(self):
        _p, r, w = _interpret()
        rows = w._raw_data_rows()
        assert len(rows) == len(r.evaluations)
        assert all(len(row) == 6 for row in rows)

    def test_invalid_surfaces_carry_a_negative_code(self):
        """Dropping them would throw away the rows that explain a blank
        patch in the contoured grid."""
        _p, r, w = _interpret()
        rows = w._raw_data_rows()
        codes = [row[5] for row in rows]
        for ev, code in zip(r.evaluations, codes):
            if ev.is_valid and getattr(ev, "admissible", True):
                assert float(code) > 0
            else:
                assert float(code) < 0, code

    def test_the_geometry_is_the_surface_geometry(self):
        _p, r, w = _interpret()
        row = w._raw_data_rows()[0]
        sd = r.evaluations[0].surface.to_dict()
        assert abs(float(row[0]) - sd["centre_x"]) < 1e-9
        assert abs(float(row[2]) - sd["radius"]) < 1e-9


# ======================================================================
@_requires_qt
class TestLineOfThrustAvailability:
    """The reference computes a thrust line only for methods that resolve
    the interslice forces. Offering it for Bishop invites the user to read
    a curve produced by an assumption."""

    def test_disabled_for_bishop(self):
        _p, _r, w = _interpret(("bishop_simplified",))
        assert w._act_thrust.isEnabled() is False
        assert w._act_thrust.toolTip()

    def test_enabled_for_spencer(self):
        _p, _r, w = _interpret(("spencer",))
        assert w._act_thrust.isEnabled() is True

    def test_switching_method_updates_availability(self):
        _p, _r, w = _interpret(("spencer", "bishop_simplified"))
        assert w._act_thrust.isEnabled() is True
        w._act_thrust.setChecked(True)
        idx = w.cb_method.findData("bishop_simplified")
        assert idx >= 0
        w._on_method_changed(idx)
        assert w._act_thrust.isEnabled() is False
        # And it must not be left switched on over a method that cannot
        # produce it.
        assert w._act_thrust.isChecked() is False


# ======================================================================
@_requires_qt
class TestQueryToggles:
    def test_text_during_query_governs_the_label(self):
        """It was a checkbox wired to nothing."""
        _p, r, w = _interpret()
        sd = r.critical.surface.to_dict()
        w._add_query()
        w._act_query_text.setChecked(True)
        w._hover_for_query(sd["centre_x"], sd["centre_y"])
        assert w._query_label_item is not None
        w._act_query_text.setChecked(False)
        w._hover_for_query(sd["centre_x"], sd["centre_y"])
        assert w._query_label_item is None

    def test_a_query_survives_the_display_mode_and_the_filter(self):
        """A Query is something the user deliberately singled out.
        Switching to Global Minimum used to erase it from the canvas."""
        _p, r, w = _interpret()
        picked = max(r.valid(), key=lambda e: e.fos)      # not the critical
        w._commit_query(picked)
        qid = picked.surface.to_dict().get("id")
        for mode in ("global_min", "minimum", "all"):
            w._set_surface_mode(mode)
            ids = {it.surface_dict.get("id") for it in _drawn(w)}
            assert qid in ids, mode
        w._fos_filter = (0.0, r.critical.fos + 0.01, None)
        w._refresh_canvas_with_highlights()
        assert qid in {it.surface_dict.get("id") for it in _drawn(w)}

    def test_show_slices_falls_back_to_the_global_minimum(self):
        """The documented shortcut: Show Slices with no query created
        makes one on the Global Minimum rather than drawing nothing."""
        _p, _r, w = _interpret()
        assert w._queries() == []
        w._act_show_slices.setChecked(True)
        lines = [it for it in w.canvas.scene().items()
                 if getattr(it, "_is_slice_line", False)]
        assert lines

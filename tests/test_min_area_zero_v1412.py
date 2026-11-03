# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.412 (D369) — a Minimum Area of 0 declared by the model switches the
area filter off; an empty field (null) is the search's own default.

The finding (seen while planning D346, measured with 0.1.372): the analysis
door handed every search ``min_area or fallback``, so a declared 0 reached
the Grid Search as 1, the Block Search as 2 and Auto Refine as 0.5, exactly
like an empty field, while 1e-9 went through and −1 switched the filter off.
A setting the user could type, in the dialog, the API, a .ogr or a script,
and that did not do what it said: rule 7. The decision (the owner,
2026-11-02, option A): 0 is "no area filter", null stays "the search's
default", the API refuses a negative, and the dialog's unchecked row shows
the default that applies with the chosen search instead of a fixed 0.5.

What these tests protect:

* rule 7, measured on a result: the circle of D346 that grazes the demo's
  face (a mass of about 0.13 m²) gets a factor with 0 — the one it gets
  with 1e-9, a value the door always honoured — and none with null;
* 0 reaches the Grid Search, the Block Search and Auto Refine as 0, and
  null as each search's fallback (1, 2, 0.5), through the single door;
* the note of a filtered hand-drawn circle says "default" for null only,
  and with 0 has no area fragment at all;
* the API refuses −1 with the range in the message, and accepts 0;
* the dialog's unchecked row shows 1 with the Grid Search and 2 with the
  Block Search, follows a change of search, says what it is in Spanish,
  and saves 0 as 0 and unchecked as null.
"""
from __future__ import annotations

import math
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


@contextmanager
def _spanish():
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language("es")
    try:
        yield
    finally:
        set_language(before)


def _grazing_circle():
    """The circle of ``test_user_surface_note_v1367``: radius 5, dipping
    0.1 m into the demo's slope face at its middle point."""
    from ogr_slip2d.surface import SlipCircle
    r, sag = 5.0, 0.1
    n = 1.0 / math.sqrt(2.0)
    d = r - sag
    return SlipCircle(centre_x=30.0 + d * n, centre_y=20.0 + d * n, radius=r)


def _run(min_area):
    """One Bishop run of the demo with the grazing circle; the result and
    the notes about hand-drawn circles. The grid is cut to 3 × 3 × 3 (the
    demo's own costs ~6 s a run): a hand-drawn circle is evaluated whatever
    the grid, and the grid only has to give the run a critical surface."""
    from ogr_core.messages import METHOD_NOTE
    from ogr_core.project.demo import build_demo_project
    from ogr_slip2d.analysis_runner import run_analysis
    p = build_demo_project()
    s = p.settings.search
    s.grid_nx = s.grid_ny = s.radius_increment = 3
    s.min_area = min_area
    p.user_surfaces = [_grazing_circle()]
    out = run_analysis(p, ["bishop_simplified"])
    notes = [w.args["note"] for w in out.warnings
             if getattr(w, "code", "") == METHOD_NOTE
             and w.args["note"]["code"].startswith("search.user_")]
    return out.results["bishop_simplified"], notes


_RUNS = {}


def _cached(min_area):
    """Each run once for the file: a grid search of the demo per value."""
    if min_area not in _RUNS:
        _RUNS[min_area] = _run(min_area)
    return _RUNS[min_area]


# ======================================================================
class TestADeclaredZeroFiltersNothing:

    def test_the_grazing_circle_gets_a_factor_with_zero(self):
        result, _notes = _cached(0.0)
        users = result.user_evaluations
        assert len(users) == 1 and users[0].is_valid, users
        reference = _cached(1e-9)[0].user_evaluations
        # The same circle through a value the door always let through
        assert users[0].fos == reference[0].fos, (users[0].fos,
                                                  reference[0].fos)
        assert abs(users[0].fos - 11.8431) < 5e-5, users[0].fos

    def test_and_none_with_the_default(self):
        result, notes = _cached(None)
        assert result.user_evaluations == []
        assert [n["code"] for n in notes] == [
            "search.user_no_result_filtered"], notes

    def test_the_critical_surface_does_not_move(self):
        """What the area filter removes is never the critical circle of
        the grid: 0 and null give the same factor (on the demo's own grid
        too, 1.0914331494631124 both, measured for the changelog)."""
        crit_null = _cached(None)[0].critical.fos
        crit_zero = _cached(0.0)[0].critical.fos
        assert crit_null == crit_zero, (crit_null, crit_zero)


class TestTheDoor:

    @staticmethod
    def _handed(method, surface_type, min_area):
        from ogr_core.project.demo import build_demo_project
        from ogr_slip2d.analysis_runner import build_evaluator, build_search
        p = build_demo_project()
        s = p.settings.search
        s.search_method, s.surface_type = method, surface_type
        s.min_area = min_area
        return (build_search(p, "bishop_simplified").min_area,
                build_evaluator(p, "bishop_simplified").min_area)

    def test_zero_reaches_every_search_as_zero(self):
        for method, stype in (("grid", "circular"),
                              ("block", "non_circular"),
                              ("auto_refine", "circular")):
            assert self._handed(method, stype, 0.0) == (0.0, 0.0), method

    def test_null_reaches_each_search_as_its_default(self):
        for method, stype, default in (("grid", "circular", 1.0),
                                       ("block", "non_circular", 2.0),
                                       ("auto_refine", "circular", 0.5)):
            assert self._handed(method, stype, None) == (default, default), \
                method

    def test_the_public_rule_is_the_door(self):
        from ogr_core.project.settings import SearchSettings
        from ogr_slip2d.analysis_runner import (
            effective_min_area, min_area_fallback,
        )
        s = SearchSettings()
        s.search_method = "block"
        assert s.min_area is None
        assert effective_min_area(s) == min_area_fallback("block") == 2.0
        assert effective_min_area(s, "grid") == 1.0
        s.min_area = 0.0
        assert effective_min_area(s) == 0.0
        assert effective_min_area(s, "grid") == 0.0


class TestTheNote:

    @staticmethod
    def _fragments(search_min_area, declared):
        """The filter fragments the note of a refused hand-drawn circle
        would carry, for a search filtering at ``search_min_area`` over a
        model that declares ``declared``."""
        from ogr_core.project.demo import build_demo_project
        from ogr_slip2d.analysis_runner import build_search
        p = build_demo_project()
        g = build_search(p, "bishop_simplified")
        p.settings.search.min_area = declared
        g.min_area = search_min_area
        return [f["code"] for f in g._user_surface_filters(p)]

    def test_null_is_said_to_be_the_default(self):
        assert self._fragments(1.0, None) == [
            "search.filter.min_area_default"]

    def test_a_declared_value_is_said_plainly(self):
        assert self._fragments(1.0, 1.0) == ["search.filter.min_area"]

    def test_zero_and_a_negative_are_no_filter(self):
        assert self._fragments(0.0, 0.0) == []
        assert self._fragments(-1.0, -1.0) == []

    def test_a_real_run_with_zero_has_no_area_fragment(self):
        """With 0 the circle has its factor, so the run says nothing of a
        filter; with null the note is the default one (D346)."""
        _result, zero = _cached(0.0)
        assert zero == [], zero
        _result, null = _cached(None)
        frags = [f["code"] for f in null[0]["args"]["filters"]]
        assert frags == ["search.filter.min_area_default"], frags


class TestTheApi:

    def test_a_negative_is_refused_with_the_range(self):
        from ogr_api.errors import InvalidArgument
        from ogr_api.settings_schema import apply_changes
        from ogr_core.project.demo import build_demo_project
        p = build_demo_project()
        try:
            apply_changes(p, {"search.min_area": -1.0})
        except InvalidArgument as e:
            assert "search.min_area must be at least 0" in str(e), str(e)
        else:
            raise AssertionError("a negative Minimum Area was accepted")
        assert p.settings.search.min_area is None

    def test_zero_is_accepted(self):
        from ogr_api.settings_schema import apply_changes
        from ogr_core.project.demo import build_demo_project
        p = build_demo_project()
        apply_changes(p, {"search.min_area": 0.0})
        assert p.settings.search.min_area == 0.0


class TestTheDialog:

    @staticmethod
    def _dialog(min_area=None):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from ogr_core.project.demo import build_demo_project
        from ogr_gui.dialogs import SurfaceOptionsDialog
        p = build_demo_project()
        p.settings.search.min_area = min_area
        return p, SurfaceOptionsDialog(p)

    @staticmethod
    def _choose(dlg, method):
        from ogr_core.project.settings import SearchMethod
        i = dlg.cb_method.findData(SearchMethod(method))
        assert i >= 0, method
        dlg.cb_method.setCurrentIndex(i)

    def test_unchecked_shows_what_the_chosen_search_applies(self):
        _p, dlg = self._dialog()
        try:
            assert not dlg.cb_filter_min_area.isChecked()
            assert dlg.sb_min_area.value() == 1.0      # the Grid Search
            dlg.rb_non_circular.setChecked(True)
            self._choose(dlg, "block")
            assert dlg.sb_min_area.value() == 2.0
            self._choose(dlg, "path")
            assert dlg.sb_min_area.value() == 1.0
        finally:
            dlg.deleteLater()

    def test_a_checked_value_is_not_overwritten_by_a_change_of_search(self):
        _p, dlg = self._dialog(0.0)
        try:
            assert dlg.cb_filter_min_area.isChecked()
            dlg.rb_non_circular.setChecked(True)
            self._choose(dlg, "block")
            assert dlg.sb_min_area.value() == 0.0
            # unchecking shows the default again
            dlg.cb_filter_min_area.setChecked(False)
            assert dlg.sb_min_area.value() == 2.0
        finally:
            dlg.deleteLater()

    def test_zero_is_saved_as_zero_and_unchecked_as_null(self):
        p, dlg = self._dialog()
        try:
            dlg.cb_filter_min_area.setChecked(True)
            dlg.sb_min_area.setValue(0.0)
            dlg.apply()
            assert p.settings.search.min_area == 0.0
            dlg.cb_filter_min_area.setChecked(False)
            dlg.apply()
            assert p.settings.search.min_area is None
        finally:
            dlg.deleteLater()

    def test_the_row_says_what_unchecked_means_in_spanish(self):
        with _spanish():
            _p, dlg = self._dialog()
            try:
                tip = dlg.cb_filter_min_area.toolTip()
                assert tip == dlg.sb_min_area.toolTip()
                assert tip == (
                    "Sin marcar, se aplica el valor por defecto del método "
                    "de búsqueda elegido. Con 0 no se descarta ninguna "
                    "superficie."), tip
            finally:
                dlg.deleteLater()

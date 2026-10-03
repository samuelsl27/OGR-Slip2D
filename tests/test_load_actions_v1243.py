# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D226b — each load carries its action, permanent or variable, and a design
standard factors it as a whole by whether it drives the sliding of the
surface.

**The invariant.** With a design standard on, a load is multiplied by γG or
γG,fav if it is permanent and by γQ or γQ,fav if it is variable, the first of
each pair when the whole load drives the sliding — the component of all it
puts on the mass along the direction of sliding is positive — and the second
when it resists it. Until v0.1.242 every load of the analysis copy took γQ:
with EN 1997-1 DA1-C1 a variable load on the part of the slope that resists
the sliding took 1.5 where Table A.3 gives γQ,fav = 0 (on the φ = 0 slope
below, 20 kPa on the face gave 0.847712 where the load left out gives
0.822909, +3.0 % on the unsafe side), and a permanent load could not be
declared.

What each class pins, and against what
--------------------------------------
1. EN 1997-1, Annex A, Table A.3, as identities in the nine methods: a
   favourable variable load (γQ,fav = 0) gives exactly the model without it;
   an unfavourable one (γQ = 1.5) the model with its magnitude × 1.5; a
   permanent one × 1.35 and × 1.0. The comparison model carries the same
   soil factor and loads that nothing factors.
2. Horizontal loads: pushing out of the slope (with the sliding) they drive,
   pushing into it they resist.
3. A load is one action: one that straddles the lowest point of the circle
   takes one factor, by what it does on balance, and its two halves drawn
   as two loads give another number.
4. The sense of sliding does not change, and nothing moves without a
   standard: the per-load parts add up to the slice weight the slicer
   built, bit for bit.
5. Rule 7: the action moves the number; γQ,fav moves it; the dialog shows
   the action only with a standard and keeps it when hidden.
6. The files: a load without an action is variable; a settings block without
   γQ,fav takes the preset's 0 for a named standard and its own γQ for a
   custom one, so a custom file's numbers do not move.
7. The rule (γQ ≥ 1 ≥ γQ,fav ≥ 0) and 0 accepted by the API and the dialog.
8. What reads the result: the API summary, the report rows and the results
   panel say how each load was classed on the critical surface.
9. Off (``design_factors.LOADS_BY_ACTION``), the v0.1.242 numbers; and the
   user's loads are never touched.

The slope is the φ = 0 one of ``test_tension_crack_truncation_v1109``
(c = 40 kPa, γ = 19, dry), its circle (55; 58) R 34 sliding right to left,
Bishop to 1e-12 on 160 slices unless the nine methods are named. Comparisons
are relative, never ``==`` on doubles of different computations.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

_CX = 55.0
_SLICES = 160
_REL = 5e-9


def _face_y(x):
    """The slope face, from the toe (30; 20) to the crest (60; 40)."""
    return 20.0 + (x - 30.0) * 20.0 / 30.0


def _with_action(load, action):
    """The action set only when it is not the default, so a variable load
    is built the same way by a tree that has no actions at all (the
    discrimination against v0.1.242 then fails by behaviour)."""
    if action != "variable":
        from ogr_core.loads import LoadAction
        load.action = LoadAction(action)
    return load


def _dist(x1, x2, q, action="variable", name=""):
    """A vertical distributed load on the ground between x1 and x2."""
    from ogr_core.geometry import Vertex
    from ogr_core.loads import DistributedLoad, LoadOrientation

    def y(x):
        return 40.0 if x >= 60.0 else _face_y(x)
    return _with_action(DistributedLoad(
        start=Vertex(x1, y(x1)), end=Vertex(x2, y(x2)), magnitude_1=q,
        orientation=LoadOrientation.VERTICAL, name=name), action)


def _crest(q=20.0, action="variable"):
    return _dist(62.0, 78.0, q, action, "crest")


def _face(q=20.0, action="variable"):
    return _dist(42.0, 52.0, q, action, "face")


def _line(magnitude, angle_deg, action="variable"):
    """A line load on the crest at x = 70 pushing at ``angle_deg`` from +x."""
    from ogr_core.geometry import Vertex
    from ogr_core.loads import LineLoad, LoadOrientation
    return _with_action(LineLoad(
        point=Vertex(70.0, 40.0), magnitude=magnitude,
        orientation=LoadOrientation.ANGLE_FROM_HORIZONTAL,
        angle_deg=angle_deg, name="line"), action)


def _slope(*loads, lines=()):
    import test_tension_crack_truncation_v1109 as U
    p = U._phi0_slope(crack_y=None)
    p.distributed_loads = list(loads)
    p.line_loads = list(lines)
    return p


def _da1c1(p):
    ds = p.settings.design_standard
    ds.enabled = True
    ds.apply_preset("eurocode7_da1c1")
    return p


def _plain_loads(p):
    """DA1-C1's soil factor with loads nothing factors: the model the
    identities compare against, its magnitudes already multiplied by hand."""
    ds = p.settings.design_standard
    ds.enabled = True
    ds.apply_preset("eurocode7_da1c1")
    ds.standard = "custom"
    ds.factor_variable = 1.0
    ds.factor_variable_favourable = 1.0
    ds.factor_permanent_favourable = 1.0
    return p


def _sliced(p, n=_SLICES):
    from ogr_core.project.design_factors import prepare_analysis_project
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    work, _rep = prepare_analysis_project(p)
    c = SlipCircle(centre_x=_CX, centre_y=58.0, radius=34.0)
    sl = slice_surface(work, c, num_slices=n)
    assert sl is not None
    return work, c, sl


def _fos(p, method="bishop_simplified"):
    from ogr_slip2d.methods import get_method
    work, c, sl = _sliced(p)
    r = get_method(method)(tolerance=1e-12).compute_fos(work, c, sl)
    assert r.fos is not None, (method, getattr(r, "reason", None))
    return float(r.fos)


def _result(p):
    from ogr_slip2d.methods import get_method
    work, c, sl = _sliced(p)
    return get_method("bishop_simplified")(tolerance=1e-12).compute_fos(
        work, c, sl)


def _nine():
    from ogr_slip2d.methods import method_registry
    names = sorted(method_registry())
    assert len(names) == 9, names
    return names


def _close(a, b, rel=_REL):
    return math.isclose(a, b, rel_tol=rel)


def _classes(p):
    """``{load name: (action, drives, factor)}`` on the circle."""
    _w, _c, sl = _sliced(p)
    return {name: (action, drives, xi)
            for _id, (action, drives, xi, name)
            in (sl.load_factors or {}).items()}


# ======================================================================
class TestTableA3AsIdentities:

    def test_a_favourable_variable_load_is_left_out(self):
        for m in _nine():
            a = _fos(_da1c1(_slope(_face())), m)
            b = _fos(_da1c1(_slope()), m)
            assert _close(a, b), (m, a, b)
        assert _classes(_da1c1(_slope(_face())))["face"] == (
            "variable", False, 0.0)

    def test_an_unfavourable_variable_load_takes_one_and_a_half(self):
        for m in _nine():
            a = _fos(_da1c1(_slope(_crest(20.0))), m)
            b = _fos(_plain_loads(_slope(_crest(30.0))), m)
            assert _close(a, b), (m, a, b)
        assert _classes(_da1c1(_slope(_crest())))["crest"] == (
            "variable", True, 1.5)

    def test_a_permanent_load_takes_gamma_g_or_its_favourable_factor(self):
        a = _fos(_da1c1(_slope(_crest(20.0, "permanent"))))
        b = _fos(_plain_loads(_slope(_crest(27.0))))
        assert _close(a, b), (a, b)
        a = _fos(_da1c1(_slope(_face(20.0, "permanent"))))
        b = _fos(_plain_loads(_slope(_face(20.0))))
        assert _close(a, b), (a, b)

    def test_the_two_together(self):
        a = _fos(_da1c1(_slope(_crest(), _face())))
        b = _fos(_plain_loads(_slope(_crest(30.0))))
        assert _close(a, b), (a, b)


class TestHorizontalLoads:

    def test_out_of_the_slope_drives_into_it_resists(self):
        """The mass slides to −x: a load pushing to −x drives it."""
        out = _da1c1(_slope(lines=[_line(30.0, 180.0)]))
        into = _da1c1(_slope(lines=[_line(30.0, 0.0)]))
        assert _close(_fos(out),
                      _fos(_plain_loads(_slope(lines=[_line(45.0, 180.0)]))))
        assert _close(_fos(into), _fos(_da1c1(_slope())))
        assert _classes(out)["line"][1] is True
        assert _classes(into)["line"][1] is False


class TestALoadIsOneAction:

    def test_a_load_across_the_lowest_point_takes_one_factor(self):
        from ogr_slip2d.design_actions import sliding_sense
        whole = _dist(48.0, 60.0, 20.0, name="across")
        _w, _c, sl = _sliced(_da1c1(_slope(whole)))
        _w, _c, plain = _sliced(_slope(whole))
        # Every part of it was multiplied by the same factor, the one its
        # whole balance asks for. Computed here from the plain slices.
        sense = sliding_sense(plain.slices)
        drive = sense * sum(
            math.sin(s.base_angle) * fv - math.cos(s.base_angle) * fh
            for s in plain.slices for _id, _a, fv, fh, _y in s.load_parts)
        (xi,) = {v[2] for v in sl.load_factors.values()}
        assert xi == (1.5 if drive > 0.0 else 0.0), (drive, xi)
        left = sum(1 for s in plain.slices if s.load_parts
                   and s.x_centre < _CX)
        right = sum(1 for s in plain.slices if s.load_parts
                    and s.x_centre > _CX)
        assert left > 5 and right > 5, "premise: it straddles the point"

    def test_its_two_halves_as_two_loads_are_another_number(self):
        whole = _fos(_da1c1(_slope(_dist(48.0, 60.0, 20.0))))
        halves = _fos(_da1c1(_slope(_dist(48.0, 55.0, 20.0),
                                    _dist(55.0, 60.0, 20.0))))
        assert abs(halves / whole - 1.0) > 1e-3, (whole, halves)


class TestNothingElseMoves:

    def test_the_parts_add_up_to_the_slice_weight(self):
        """Without a standard the slicer builds the weight it always built:
        soil, plus the pressure total times the width, plus the line loads;
        the parts are a record of that, not a second sum."""
        from ogr_slip2d.slicer import _surface_pressure_at, _surface_pressures_at
        p = _slope(_crest(), _face(), lines=[_line(30.0, 225.0)])
        _w, _c, sl = _sliced(p)
        for s in sl.slices:
            want = sum(fv for _id, _a, fv, _fh, _y in s.load_parts)
            assert _close(s.weight - s.soil_weight, want, 1e-12), s.x_centre
            parts = _surface_pressures_at(p, s.x_centre)
            total = 0.0
            for _load, q in parts:
                total += q
            assert total == _surface_pressure_at(p, s.x_centre)
            assert s.weight_factor == 1.0
        assert sl.load_factors is None and sl.design_sense is None

    def test_the_sense_of_sliding_does_not_change(self):
        from ogr_slip2d.design_actions import sliding_sense
        p = _da1c1(_slope(_crest(), _face(), lines=[_line(30.0, 0.0)]))
        _w, _c, sl = _sliced(p)
        assert sliding_sense(sl.slices) == sl.design_sense


# ======================================================================
class TestEverySettingMovesTheNumber:
    """Rule 7."""

    def test_the_action(self):
        a = _fos(_da1c1(_slope(_face(20.0, "variable"))))
        b = _fos(_da1c1(_slope(_face(20.0, "permanent"))))
        assert b > a + 0.01, (a, b)

    def test_the_favourable_variable_factor(self):
        def run(fav):
            p = _da1c1(_slope(_face()))
            p.settings.design_standard.standard = "custom"
            p.settings.design_standard.factor_variable_favourable = fav
            return _fos(p)
        assert run(1.0) > run(0.0) + 0.01

    def test_the_dialog_shows_the_action_only_with_a_standard(self):
        from PySide6.QtWidgets import QApplication
        from ogr_core.loads import LoadAction
        from ogr_gui.dialogs.load_dialogs import (DistributedLoadDialog,
                                                  LineLoadDialog)
        QApplication.instance() or QApplication([])
        load = _face(20.0, "permanent")
        off = DistributedLoadDialog(existing=load)
        on = DistributedLoadDialog(existing=load, design_standard=True)
        assert off.cb_action.isHidden() and off.lbl_action.isHidden()
        assert not on.cb_action.isHidden()
        # Hidden, it keeps what the load had.
        assert off.action() == LoadAction.PERMANENT
        assert LineLoadDialog(design_standard=True).action() == (
            LoadAction.VARIABLE)


# ======================================================================
class TestTheFiles:

    def test_a_load_without_an_action_is_variable(self):
        from ogr_core.loads import DistributedLoad, LineLoad, LoadAction
        d = _face().to_dict()
        d.pop("action")
        assert DistributedLoad.from_dict(d).action == LoadAction.VARIABLE
        line = _line(1.0, 0.0, "permanent").to_dict()
        assert LineLoad.from_dict(line).action == LoadAction.PERMANENT
        line.pop("action")
        assert LineLoad.from_dict(line).action == LoadAction.VARIABLE

    def test_settings_without_the_favourable_variable_factor(self):
        from ogr_core.project.settings import DesignStandardSettings as D
        old = {"enabled": True, "standard": "eurocode7_da1c1",
               "factor_permanent": 1.35, "factor_variable": 1.5,
               "single_source_weight": True}
        assert D.from_dict(old).factor_variable_favourable == 0.0
        custom = dict(old, standard="custom", factor_variable=1.4)
        assert D.from_dict(custom).factor_variable_favourable == 1.4
        none = dict(old, standard="none", factor_variable=1.0)
        assert D.from_dict(none).factor_variable_favourable == 1.0

    def test_a_custom_file_of_v0_1_242_keeps_its_number(self):
        """Every load of it took its γQ, favourable or not; it still does:
        the face load of such a file weighs 1.5 times, as before."""
        from ogr_core.project.settings import DesignStandardSettings as D
        p = _slope(_face())
        p.settings.design_standard = D.from_dict(
            {"enabled": True, "standard": "custom", "factor_variable": 1.5,
             "factor_permanent": 1.0, "single_source_weight": True})
        q = _slope(_face(30.0))
        q.settings.design_standard.enabled = True
        q.settings.design_standard.standard = "custom"
        assert _close(_fos(p), _fos(q)), (_fos(p), _fos(q))

    def test_the_eurocode_presets(self):
        from ogr_core.project.settings import DesignStandardSettings as D
        for name, want in (("eurocode7_da1c1", (1.5, 0.0)),
                           ("eurocode7_da1c2", (1.3, 0.0)),
                           ("eurocode7_da2", (1.5, 0.0)),
                           ("eurocode7_da3", (1.3, 0.0)),
                           ("none", (1.0, 1.0))):
            s = D()
            s.apply_preset(name)
            assert (s.factor_variable, s.factor_variable_favourable) == want


# ======================================================================
class TestTheRule:

    def test_its_codes(self):
        from ogr_core.project.rules import design_action_factors_refusal
        from ogr_core.project.settings import DesignStandardSettings as D

        def code(**kw):
            s = D()
            for k, v in kw.items():
                setattr(s, k, v)
            why = design_action_factors_refusal(s)
            return None if why is None else why.code
        assert code(factor_variable=1.5, factor_variable_favourable=0.0) \
            is None
        assert code(factor_variable=0.9) == (
            "design_action_factor_variable_unfavourable_below_one")
        assert code(factor_variable_favourable=1.1) == (
            "design_action_factor_variable_favourable_above_one")
        assert code(factor_variable_favourable=-0.1) == (
            "design_action_factor_variable_favourable_negative")
        assert code(factor_variable_favourable=float("inf")) == (
            "design_action_factor_not_a_number")

    def test_zero_goes_through_the_api_and_the_dialog(self):
        from PySide6.QtWidgets import QApplication
        from ogr_api import Conflict, Workspace, call
        from ogr_core.project import ProjectSettings
        from ogr_gui.dialogs.project_settings_dialog import (
            _DesignStandardPage)
        ws = Workspace()
        try:
            pid = call(ws, "project_new", name="d226b")["project_id"]

            def put(changes):
                return call(ws, "settings_set", project_id=pid,
                            changes=changes)
            out = put({"design_standard.standard": "custom",
                       "design_standard.factor_variable_favourable": 0.0})
            assert out["changed"][
                "design_standard.factor_variable_favourable"]["new"] == 0.0
            with pytest.raises(Conflict):
                put({"design_standard.standard": "custom",
                     "design_standard.factor_variable": 0.8})
        finally:
            ws.shutdown()
        QApplication.instance() or QApplication([])
        s = ProjectSettings()
        s.design_standard.enabled = True
        s.design_standard.standard = "custom"
        page = _DesignStandardPage(s)
        fav = page.factors["factor_variable_favourable"]
        assert fav.minimum() == 0.0 and fav.maximum() == 1.0
        assert page.factors["factor_variable"].minimum() == 1.0
        fav.setValue(0.0)
        page.apply()
        assert s.design_standard.factor_variable_favourable == 0.0


# ======================================================================
class TestWhatReadsTheResult:

    def test_the_api_summary(self):
        from ogr_api.results import lem_summary
        rows = lem_summary(_result(_da1c1(_slope(_crest(), _face()))))[
            "load_factors"]
        by_name = {r["name"]: r for r in rows}
        assert by_name["crest"]["drives"] is True
        assert by_name["crest"]["factor"] == 1.5
        assert by_name["face"]["drives"] is False
        assert by_name["face"]["factor"] == 0.0
        assert "load_factors" not in lem_summary(_result(_slope(_crest())))

    def test_the_api_load_set_says_when_nothing_reads_the_action(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = call(ws, "project_new", name="d226b")["project_id"]
            call(ws, "model_define", project_id=pid, spec={
                "external": [[0, 0], [100, 0], [100, 40], [60, 40],
                             [30, 20], [0, 20]],
                "materials": [{"name": "Clay", "unit_weight": 19.0,
                               "strength": {"model": "undrained",
                                            "params": {"cohesion": 40.0}}}]})
            out = call(ws, "load_set", project_id=pid, kind="distributed",
                       start=[62, 40], end=[78, 40], magnitude=20,
                       orientation="vertical", action="permanent")
            assert out["load"]["action"] == "permanent"
            assert any("design standard" in n for n in out["notes"])
        finally:
            ws.shutdown()

    def test_the_report_and_the_results_panel(self):
        from ogr_core.report.report_generator import _load_factor_rows
        from ogr_gui.widgets.results_dock import load_factor_lines
        res = _result(_da1c1(_slope(_crest(), _face())))
        rows = dict(_load_factor_rows(res))
        assert "drives" in rows["crest"] and "1.5" in rows["crest"]
        assert "resists" in rows["face"] and "× 0" in rows["face"]
        text = load_factor_lines(res)
        assert "resists the sliding" in text and "crest" in text
        assert load_factor_lines(_result(_slope(_crest()))) == ""


# ======================================================================
class TestOffAndUntouched:

    def test_off_every_load_takes_the_variable_factor_again(self):
        import ogr_core.project.design_factors as DF
        saved = DF.LOADS_BY_ACTION
        try:
            DF.LOADS_BY_ACTION = False
            off = _fos(_da1c1(_slope(_face())))
        finally:
            DF.LOADS_BY_ACTION = saved
        # v0.1.242: the face load × 1.5 in the copy, measured 0.847712.
        assert _close(off, _fos(_plain_loads(_slope(_face(30.0))))), off
        assert abs(off - 0.847712) < 1e-6, off

    def test_the_users_loads_are_never_touched(self):
        import json
        p = _da1c1(_slope(_crest(), _face(), lines=[_line(30.0, 0.0)]))
        before = json.dumps(p.to_dict(), sort_keys=True, default=str)
        _w, _c, sl = _sliced(p)
        assert sl.load_factors
        assert json.dumps(p.to_dict(), sort_keys=True, default=str) == before
        work, _c, _sl = _sliced(p)
        assert [ld.magnitude_1 for ld in work.distributed_loads] == [20.0,
                                                                      20.0]

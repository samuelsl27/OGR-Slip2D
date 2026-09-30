# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""The back analysis undoes the method it back-analyses, whatever the model
carries (v0.1.220, D210).

INVARIANT PROTECTED
-------------------
At the factor of safety a method gives a surface, the force the Back
Analysis of Support Force requires to reach that same factor is ZERO. That
is not a convention: the back analysis holds F fixed and solves the
method's own balance for one more force, so at the method's own F the
balance already closes with none. It is the identity that makes the number
mean anything, and it is asserted here unclipped, to 1e-9 of the weight,
with the solver pinned at 1e-12:

* on a dry slope with Bishop, WITHOUT the arm discount
  ``test_back_analysis_envelope_v1215`` had to subtract;
* under a reservoir (the ponded water's weight and its thrust);
* with water in a tension crack, and with an inclined line load (the
  horizontal forces the slicer keeps in ``water_force_h``);
* under an earthquake, kh and kv, on the reservoir;
* with an Active and a Passive nail, which enter the sums as the method
  applies them (decision of the owner, 2026-09-28): the force found is the
  one to ADD to the reinforcement already there;
* where Janbu slides the other way from Bishop's sense (D112's shape: a
  steep passive base with water standing on it).

WHAT WAS WRONG
--------------
``back_analysis._sums_at_fixed_fos`` rebuilt the two sums by hand from the
soil weight: no ponded water nor its thrust, ``sin a`` where Bishop's solver
takes ``Slice.weight_arm_ratio``, Bishop's sense of sliding for Janbu too,
and no supports at all. Measured at the method's own factor on the 335
archived surfaces of the verification bank: above 1e-9 of the weight on 208,
up to 1.44 times the weight under a reservoir and 0.61 with supports. The
fix is not a better copy: the solvers expose their sums at a fixed F
(``bishop.circle_driving_sum``, ``janbu.horizontal_driving_sum``,
``bishop.x0_resisting_pass``) and the back analysis calls them.

WHY NOTHING HERE IS A SNAPSHOT
------------------------------
The anchor is the identity itself, force = 0 at the method's own factor,
which no printed number of today can stand in for. The fixtures are the
suite's own, imported so they cannot drift: the dam face of
``test_interslice_ponded_v1214``, the nail of ``test_support_normal_v1137``,
the slope of ``test_slide_sign_by_method_v1189``.

WHAT THIS FILE DISCRIMINATES, MEASURED
--------------------------------------
Against the v0.1.219 tree: see ``_auditoria/P4_0220`` in the verification
bank for the count, recorded when the version was closed.
"""
from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

TOL_W = 1e-9
_ROOT = Path(__file__).resolve().parent.parent
_CACHE: dict = {}


# ----------------------------------------------------------------------
def _weight(slices) -> float:
    from ogr_slip2d.external_forces import slice_forces
    return sum(slice_forces(s).w_total for s in slices)


def _sums(slices, surface, f_eval, kh, kv, elevation, method_id,
          stress_fos, project):
    """``_sums_at_fixed_fos`` with the model. On a tree without the
    ``project`` argument (v0.1.219) it is called without it, which is the
    old reading: the cases then fail on the number, not on a name."""
    from ogr_slip2d.back_analysis import _sums_at_fixed_fos
    try:
        return _sums_at_fixed_fos(slices, surface, f_eval, kh, kv, elevation,
                                  method_id, stress_fos=stress_fos,
                                  project=project)
    except TypeError:
        return _sums_at_fixed_fos(slices, surface, f_eval, kh, kv, elevation,
                                  method_id, stress_fos=stress_fos)


def _solve(project, surface, slices, method_id):
    from ogr_slip2d.methods import method_registry
    m = method_registry()[method_id]()
    m.tolerance = 1e-12
    m.max_iterations = 400
    res = m.compute_fos(project, surface, slices)
    assert res.fos is not None and res.converged, (method_id,
                                                   res.error_message)
    return res


def _force_at_own_factor(project, surface, slices, method_id):
    """(passive force UNCLIPPED at the method's own factor, weight)."""
    res = _solve(project, surface, slices, method_id)
    s_list = list(slices.slices if hasattr(slices, "slices") else slices)
    kh = project.seismic.kh if project.seismic.enabled else 0.0
    kv = project.seismic.kv if project.seismic.enabled else 0.0
    f_eval = res.fos
    if method_id == "janbu_corrected":
        f_eval = res.fos / res.details["janbu_f0"]
    elevation = min(s.base_y_left for s in s_list) - 1.0
    sums = _sums(s_list, surface, f_eval, kh, kv, elevation, method_id,
                 f_eval, project)
    assert sums is not None, method_id
    resisting, driving, arm = sums
    return (f_eval * driving - resisting) / arm, _weight(s_list)


def _check(project, surface, slices, methods):
    bad = []
    for mid in methods:
        t, w = _force_at_own_factor(project, surface, slices, mid)
        if not abs(t) < TOL_W * w:
            bad.append((mid, t, w))
    assert not bad, bad


# ---------------------------------------------------------------- fixtures
def _dry_slope():
    from test_slide_sign_by_method_v1189 import _circle, _slope
    from ogr_slip2d.slicer import slice_surface
    p, c = _slope(), _circle()
    return p, c, slice_surface(p, c, num_slices=25)


def _reservoir(kh=0.0, kv=0.0):
    from test_interslice_ponded_v1214 import CIRCLE, N_SLICES, _project
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    p = _project(True, kh, kv)
    c = SlipCircle(**CIRCLE)
    return p, c, slice_surface(p, c, num_slices=N_SLICES)


def _crack():
    """The water-filled crack of ``test_ponded_water_v161``, written here:
    that module builds a window at import."""
    from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                   TensionCrackProperties, Vertex,
                                   WaterLevelMode)
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    p = Project("tc")
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(60, 0), Vertex(60, 10),
        Vertex(35, 10), Vertex(15, 30), Vertex(0, 30)], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(0, 24), Vertex(14, 24)], closed=False),
        btype=BoundaryType.TENSION_CRACK))
    p.materials = [Material(
        name="S", strength=MohrCoulomb(cohesion=20, friction_angle=25))]
    p.tension_crack_properties = TensionCrackProperties(
        mode=WaterLevelMode.FILLED)
    c = SlipCircle(centre_x=25.0, centre_y=40.0, radius=25.0)
    sl = slice_surface(p, c, num_slices=30)
    assert abs(sum(s.water_force_h for s in sl.slices)) > 0.0
    return p, c, sl


def _inclined_load():
    """The dry slope with a line load on the crest, 30 degrees below the
    horizontal: its vertical part joins the weight and its horizontal
    part the horizontal forces."""
    from ogr_core.geometry import Vertex
    from ogr_core.loads import LineLoad, LoadOrientation
    from ogr_slip2d.slicer import slice_surface
    from test_slide_sign_by_method_v1189 import _circle, _slope
    p, c = _slope(), _circle()
    p.line_loads.append(LineLoad(
        point=Vertex(85.0, 40.0), magnitude=150.0,
        orientation=LoadOrientation.ANGLE_FROM_HORIZONTAL, angle_deg=-30.0))
    sl = slice_surface(p, c, num_slices=25)
    assert any(abs(s.water_force_h) > 0.0 for s in sl.slices)
    return p, c, sl


def _nail(active):
    from ogr_slip2d.slicer import slice_surface
    from test_support_normal_v1137 import NSLICES, _circle, _nail, _project
    p = _project(_nail(-15.0, active))
    c = _circle()
    return p, c, slice_surface(p, c, num_slices=NSLICES)


def _janbu_the_other_way():
    """Three slices where Janbu's sense of sliding, sign(sum W_total tan a),
    is the opposite of Bishop's, sign(sum W sin a): a steep passive base
    with water standing on it, the shape of D112 (the numbers of
    ``test_slide_sign_by_method_v1189.TestTheWitnessWhereTheyDisagree``)."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_slip2d.slicer import Slice
    from ogr_slip2d.surface import SlipSurface
    mat = Material(name="m", unit_weight=20.0, sat_unit_weight=20.0,
                   strength=MohrCoulomb(cohesion=5.0, friction_angle=30.0))
    rows = ((-70.0, 1.0, 100.0, 400.0), (20.0, 5.0, 500.0, 0.0),
            (20.0, 5.0, 500.0, 0.0))
    slices, x, y = [], 0.0, 0.0
    pts = [(x, y)]
    for i, (a_deg, b, w, ww) in enumerate(rows):
        a = math.radians(a_deg)
        x1, y1 = x + b, y + b * math.tan(a)
        slices.append(Slice(
            index=i, x_centre=x + 0.5 * b, width=b,
            base_x_left=x, base_x_right=x1, base_y_left=y, base_y_right=y1,
            base_angle=a, base_length=b / math.cos(a),
            top_y_left=max(y, y1) + 5.0, top_y_right=max(y, y1) + 5.0,
            weight=w, water_weight=ww, material=mat))
        x, y = x1, y1
        pts.append((x, y))
    surf = SlipSurface(polyline=Polyline(
        vertices=[Vertex(px, py) for px, py in pts], closed=False))
    return Project("d112"), surf, slices


# ======================================================================
class TestTheFixturesCarryWhatTheyClaim:
    """Guards on the guards: a case whose fixture lost its water, its load
    or its disagreement would pass here asserting nothing."""

    def test_the_reservoir_stands_on_the_slices(self):
        from ogr_slip2d.external_forces import slice_forces
        _p, _c, sl = _reservoir()
        wet = [slice_forces(s) for s in sl.slices]
        assert sum(f.w_total - f.w_soil for f in wet) > 0.0
        assert any(f.h_water != 0.0 for f in wet)

    def test_janbu_and_bishop_disagree_on_the_sense(self):
        from ogr_slip2d.methods.bishop import slide_sense as bishop_sense
        from ogr_slip2d.methods.janbu import slide_sense as janbu_sense
        _p, _s, sl = _janbu_the_other_way()
        assert bishop_sense(sl, 0.0) == 1.0
        assert janbu_sense(sl, 0.0, 0.0) == -1.0

    def test_the_nail_crosses_the_surface(self):
        from ogr_slip2d.support_integration import resolve_support_terms
        for active in (True, False):
            p, c, sl = _nail(active)
            sup = resolve_support_terms(p, c, sl, 1.0)
            assert sup.present, active
            col = sup.t_active if active else sup.t_passive
            assert any(col), active


# ======================================================================
class TestZeroForceAtTheMethodsOwnFactor:
    """The identity, unclipped, at 1e-9 of the weight."""

    X0 = ("bishop_simplified", "janbu_simplified", "janbu_corrected")

    def test_bishop_without_discount_on_a_dry_slope(self):
        """Bishop's weight arm is ``weight_arm_ratio``, not ``sin a``: the
        discount ``test_back_analysis_envelope_v1215`` subtracted is gone."""
        _check(*_dry_slope(), self.X0)

    def test_under_a_reservoir(self):
        _check(*_reservoir(), self.X0)

    def test_with_water_in_a_tension_crack(self):
        _check(*_crack(), self.X0)

    def test_with_an_inclined_line_load(self):
        _check(*_inclined_load(), self.X0)

    def test_under_an_earthquake_on_a_reservoir(self):
        _check(*_reservoir(kh=0.1, kv=0.05), self.X0)

    def test_with_an_active_nail(self):
        _check(*_nail(True), self.X0)

    def test_with_a_passive_nail(self):
        _check(*_nail(False), self.X0)

    def test_where_janbu_slides_the_other_way(self):
        p, s, sl = _janbu_the_other_way()
        _check(p, s, sl, ("janbu_simplified", "janbu_corrected"))


# ======================================================================
class TestTheSwitchMovesTheNumber:
    """Rule 7: ``back_analysis.LOADS_FROM_METHOD`` off rebuilds the hand
    sums, and the identity breaks by far more than any tolerance."""

    def test_off_under_a_reservoir(self):
        from ogr_slip2d import back_analysis as ba
        p, c, sl = _reservoir()
        old = ba.LOADS_FROM_METHOD
        ba.LOADS_FROM_METHOD = False
        try:
            t, w = _force_at_own_factor(p, c, sl, "bishop_simplified")
        finally:
            ba.LOADS_FROM_METHOD = old
        assert abs(t) > 1e-3 * w, (t, w)

    def test_off_with_a_nail(self):
        from ogr_slip2d import back_analysis as ba
        p, c, sl = _nail(False)
        old = ba.LOADS_FROM_METHOD
        ba.LOADS_FROM_METHOD = False
        try:
            t, w = _force_at_own_factor(p, c, sl, "janbu_simplified")
        finally:
            ba.LOADS_FROM_METHOD = old
        assert abs(t) > 1e-3 * w, (t, w)


# ======================================================================
class TestTheCallersPassTheModel:

    def test_required_force_counts_the_reinforcement_already_there(self):
        """Through the public function, at the method's own factor: zero
        with the model, and the whole nail short without it."""
        from ogr_slip2d.back_analysis import required_force
        p, c, sl = _nail(False)
        res = _solve(p, c, sl, "bishop_simplified")
        try:
            with_model = required_force(sl.slices, c, res.fos,
                                        "bishop_simplified", 0.0,
                                        project=p)
        except TypeError:
            with_model = required_force(sl.slices, c, res.fos,
                                        "bishop_simplified", 0.0)
        w = _weight(sl.slices)
        assert with_model is not None
        assert with_model.passive_force < TOL_W * w, with_model.passive_force
        bare = required_force(sl.slices, c, res.fos, "bishop_simplified", 0.0)
        assert bare.passive_force > 1.0, bare.passive_force

    def test_run_back_analysis_hands_over_its_project(self):
        """The driver, with a search that returns the one nailed surface:
        at that surface's own factor the governing force is zero."""
        from types import SimpleNamespace

        from ogr_slip2d.back_analysis import run_back_analysis
        p, c, sl = _nail(False)
        res = _solve(p, c, sl, "bishop_simplified")

        class _One:
            def run(self, project):
                return SimpleNamespace(evaluations=[res])

        out = run_back_analysis(p, _One(), target_fos=res.fos,
                                elevation=0.0,
                                method_id="bishop_simplified")
        assert out.critical is not None, out.notes
        assert out.critical.passive_force < TOL_W * _weight(sl.slices), (
            out.critical.passive_force)

    def test_the_interpretation_window_passes_the_factored_model(self):
        """The window calls ``required_force`` itself, on the critical
        surface of a run that used the FACTORED copy of the project. Read
        by AST: the call is inside a slot that opens two modal inputs."""
        tree = ast.parse((_ROOT / "ogr_gui" / "interpret_window.py")
                         .read_text(encoding="utf-8"))
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef)
                  and n.name == "_back_analysis_report")
        calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
                 and getattr(n.func, "id", "") == "required_force"]
        assert len(calls) == 1, len(calls)
        assert any(k.arg == "project" for k in calls[0].keywords)
        names = {getattr(n.func, "id", "") for n in ast.walk(fn)
                 if isinstance(n, ast.Call)}
        # v0.1.228 (D218b) — changed on purpose: the analysis copy is made
        # by ``prepare_analysis_project``, which applies the design factors
        # and resolves the Generalized Anisotropic links on the same copy.
        assert "prepare_analysis_project" in names

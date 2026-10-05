# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.260, defect D259 — Surface Altering, the second technique of Optimize
Surfaces, against closed forms; and the random walk untouched.

Invariants protected, each with the external anchor that makes it more
than a snapshot:

1. **The Coulomb wedge.** With the toe end held (its Slope Limit window
   collapsed on the toe) and only step A running, the surface stays a plane
   through the toe, its factor is the closed form of the wedge at its own
   daylight point (Coulomb 1776; Duncan & Wright 2005 §6; Ordinary is exact
   on a plane, see ``test_janbu_wedge_v1142``), and it lands on the
   minimiser of that closed form, found independently by a 1-D bounded
   minimisation of the formula itself.
2. **The infinite slope.** On a cohesionless slope no surface may come
   below ``tan phi / tan beta`` (Duncan & Wright 2005; verification problems
   79 and 81, case 2), and the alteration approaches it from above.
3. **The maps of the document are what they say.** Eq. 1 moves the end
   exactly and keeps a straight line straight, x ordered and the concavity
   of the surface; Eq. 2 with the dynamic bounds gives a convex surface for
   any displacement asked for; the pair slide keeps x ordered; the ground
   path follows a vertical face (fig. 2 of the document).
4. **The ends stay on the ground and in their own window**, also on a model
   with a vertical face and two Slope Limit windows.
5. **x strictly increasing and the concave ceiling** on every surface
   returned.
6. **Deterministic**: two runs give the same surface bit for bit, and the
   seed is not read.
7. **The budget**: never more evaluations than ``max_iterations``, the
   random walk's arithmetic (``accepted + rejected == iterations``), never
   worse than the start, an admissible answer.
8. **Weak layers.** On the planar joint of ``test_weak_layer_v1121`` (the
   soil made strong, the ends held at the joint's daylight points) the
   alteration reaches the closed form of the joint,
   ``F = (cL + W cos a tan phi) / (W sin a)``, exactly; and step D alone
   moves points onto the joint and lowers the factor.
9. **Monte Carlo is untouched**, bit for bit: an explicit
   ``technique="monte_carlo"`` and the default give the same walk, and the
   project default is Monte Carlo, also for a file written before the key
   existed.
10. **Rule 7 for the new setting**: choosing Surface Altering moves the
    critical surface of a search, and never above the search's own.
11. **Rule 7 for what Surface Altering honours**: the tolerance, the
    Surface Filters through *Use checks*, and *Snap Shallow Surfaces*.
12. **The start contract** is the random walk's: the same ``error`` note
    when the start cannot be evaluated.
13. **The focus** is respected.
14. **The notes**: the two random-walk settings Surface Altering does not
    read are said only when changed, and an unknown technique is refused.

COST. Ordinary or Bishop with 25 to 50 slices and budgets of a few hundred
evaluations; the runs are cached per module. About half a minute.
"""
from __future__ import annotations

import math

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
_CACHE: dict = {}


def _poly(pts):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in pts], closed=False))


def _model(ext, materials, slices, windows=None):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.project import Project
    p = Project("SAO")
    e = Polyline(vertices=[Vertex(x, y) for x, y in ext], closed=True)
    e.ensure_ccw()
    p.add_boundary(Boundary(polyline=e, btype=BoundaryType.EXTERNAL))
    p.materials = materials
    p.resolve_regions()
    p.settings.methods.num_slices = slices
    s = p.settings.search
    s.search_method = "path"
    s.surface_type = "non_circular"
    if windows:
        (a, b), (c, d) = windows
        s.slope_limit_left, s.slope_limit_right = a, b
        s.slope_limit_left_2, s.slope_limit_right_2 = c, d
    p.settings.advanced.parallel_search = False
    return p


def _mc(c, phi, gamma):
    from ogr_core.materials import Material, MohrCoulomb
    return Material(name="Soil", unit_weight=gamma,
                    strength=MohrCoulomb(cohesion=c, friction_angle=phi))


# The wedge of test_janbu_wedge_v1142: H 12, toe at 30, crest at 38.
_H, _TOE, _CREST = 12.0, 30.0, 38.0
_COH, _PHI, _GAMMA = 5.0, 30.0, 18.0


def _wedge_model():
    return _model([(0, -10), (60, -10), (60, _H), (_CREST, _H), (_TOE, 0),
                   (0, 0)], [_mc(_COH, _PHI, _GAMMA)], 50,
                  windows=((_TOE, _TOE), (_CREST, 60.0)))


def _wedge_closed(xd):
    """The wedge through the toe daylighting at ``xd`` on the crest:
    W from the triangle (toe, crest corner, daylight), no slicer."""
    th = math.atan2(_H, xd - _TOE)
    length = math.hypot(xd - _TOE, _H)
    w = _GAMMA * 0.5 * _H * (xd - _CREST)
    return ((_COH * length + w * math.cos(th) * math.tan(math.radians(_PHI)))
            / (w * math.sin(th)))


# A cohesionless 2:1 slope, toe at x = 10, crest at y = 20.
_TAN_BETA = 0.5


def _sand_model():
    return _model([(0, -10), (80, -10), (80, 20), (50, 20), (10, 0), (0, 0)],
                  [_mc(0.0, 30.0, 19.0)], 25)


_SAND_START = [(14.0, 2.0), (22.0, 2.5), (32.0, 6.5), (40.0, 11.0),
               (46.0, 18.0)]

# The planar joint of test_weak_layer_v1121, the soil made strong.
_JOINT = ((2.0, 2.0), (30.0, 10.0))


def _joint_model():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    p = _model([(0, 0), (40, 0), (40, 10), (10, 10)], [_mc(200.0, 30.0, 20.0)],
               40, windows=((2.0, 2.0), (30.0, 30.0)))
    jm = Material(name="Joint", unit_weight=20.0,
                  strength=MohrCoulomb(cohesion=5.0, friction_angle=20.0))
    p.materials.append(jm)
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(*_JOINT[0]), Vertex(*_JOINT[1])]),
        btype=BoundaryType.WEAK_LAYER, material_id=jm.id))
    return p


def _joint_closed():
    (x0, y0), (x1, y1) = _JOINT
    length = math.hypot(x1 - x0, y1 - y0)
    a = math.atan2(y1 - y0, x1 - x0)
    w = 20.0 * 80.0
    return ((5.0 * length + w * math.cos(a) * math.tan(math.radians(20.0)))
            / (w * math.sin(a)))


_CAP = [(2.0, 2.0), (9.0, 6.0), (16.0, 8.5), (23.0, 9.6), (30.0, 10.0)]


def _sao(project, method, start, steps=None, **kw):
    """One Surface Altering run; ``steps`` restricts the module's STEPS
    and is restored afterwards (rule 5)."""
    import ogr_slip2d.surface_altering as SA
    from ogr_slip2d.analysis_runner import build_search
    from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
    kw.setdefault("snap_shallow_to_slope", False)
    old = SA.STEPS
    try:
        if steps is not None:
            SA.STEPS = steps
        search = build_search(project, method)
        return optimize_surface(project, search, _poly(start),
                                OptimizeSettings(technique="surface_altering",
                                                 **kw))
    finally:
        SA.STEPS = old


def _cached(name, fn):
    if name not in _CACHE:
        _CACHE[name] = fn()
    return _CACHE[name]


def _wedge_run():
    xd0 = _TOE + _H / math.tan(math.radians(50.0))
    return _cached("wedge", lambda: _sao(
        _wedge_model(), "ordinary_fellenius", [(_TOE, 0.0), (xd0, _H)],
        steps=("A",), max_iterations=200))


def _sand_run():
    return _cached("sand", lambda: _sao(
        _sand_model(), "spencer", _SAND_START, max_iterations=300))


def _wall_model():
    """A vertical face at x = 20 (toe flat at 10, crest at 30) and two
    windows: the toe side up to the foot of the wall, the crest side."""
    return _model([(0, 0), (60, 0), (60, 30), (20, 30), (20, 10), (0, 10)],
                  [_mc(10.0, 30.0, 20.0)], 30,
                  windows=((0.0, 20.0), (24.0, 60.0)))


_WALL_START = [(15.0, 10.0), (24.0, 6.0), (34.0, 9.0), (42.0, 18.0),
               (48.0, 30.0)]


def _wall_run():
    return _cached("wall", lambda: _sao(
        _wall_model(), "bishop_simplified", _WALL_START, max_iterations=250))


# ======================================================================
class TestTheCoulombWedge:
    """Invariant 1."""

    def test_the_surface_stays_a_plane_through_the_toe(self):
        sup, res, rep = _wedge_run()
        v = [(p.x, p.y) for p in sup.polyline.vertices]
        assert v[0] == (_TOE, 0.0)
        slope = _H / (v[-1][0] - _TOE)
        assert max(abs(y - slope * (x - _TOE)) for x, y in v) < 1e-9

    def test_its_factor_is_the_closed_form_at_its_own_daylight(self):
        sup, res, rep = _wedge_run()
        xd = sup.polyline.vertices[-1].x
        assert math.isclose(res.fos, _wedge_closed(xd), rel_tol=1e-12)

    def test_it_lands_on_the_minimum_of_the_closed_form(self):
        from scipy.optimize import minimize_scalar
        best = minimize_scalar(_wedge_closed, bounds=(_CREST + 1e-6, 60.0),
                               method="bounded", options={"xatol": 1e-12})
        sup, res, rep = _wedge_run()
        assert abs(res.fos - best.fun) / best.fun < 1e-9, (res.fos, best.fun)
        assert abs(sup.polyline.vertices[-1].x - best.x) < 1e-4
        assert rep.technique == "surface_altering"


class TestTheInfiniteSlopeBound:
    """Invariant 2."""

    def test_never_below_tan_phi_over_tan_beta_and_below_the_start(self):
        from ogr_slip2d.analysis_runner import build_search
        bound = math.tan(math.radians(30.0)) / _TAN_BETA
        p = _sand_model()
        start = build_search(p, "spencer").evaluate_surface(
            p, _poly(_SAND_START))
        sup, res, rep = _sand_run()
        assert res.fos >= bound * (1.0 - 2e-3), (res.fos, bound)
        assert res.fos < start.fos


class TestThePureMaps:
    """Invariant 3, without a slope-stability solve."""

    _PTS = [(0.0, 5.0), (2.0, 2.0), (5.0, 0.8), (9.0, 1.2), (12.0, 3.5),
            (14.0, 7.0)]

    def test_eq1_moves_the_end_exactly_and_keeps_the_shape(self):
        from ogr_slip2d.optimize import max_concave_angle_deg
        from ogr_slip2d.surface_altering import stretch_from_end
        for a, d in ((0, (-3.0, 1.5)), (0, (6.5, -2.0)), (-1, (5.0, 2.0)),
                     (-1, (-6.5, -1.0))):
            out = stretch_from_end(self._PTS, a, d)
            i = 0 if a == 0 else len(self._PTS) - 1
            j = len(self._PTS) - 1 - i
            assert out[i] == (self._PTS[i][0] + d[0], self._PTS[i][1] + d[1])
            assert out[j] == self._PTS[j]
            assert all(q[0] > p[0] for p, q in zip(out, out[1:]))
            assert max_concave_angle_deg(out) <= 1e-9

    def test_eq1_keeps_a_straight_line_straight(self):
        from ogr_slip2d.surface_altering import stretch_from_end
        line = [(x, 2.0 + 0.5 * x) for x in (0.0, 1.0, 3.0, 6.0, 10.0)]
        out = stretch_from_end(line, -1, (3.0, 4.0))
        (x0, y0), (x1, y1) = out[0], out[-1]
        for x, y in out:
            assert abs(y - (y0 + (y1 - y0) * (x - x0) / (x1 - x0))) < 1e-12

    def test_eq2_with_the_dynamic_bounds_gives_a_convex_surface(self):
        """At the corners and the centre of the box of displacements."""
        import itertools
        from ogr_slip2d.optimize import max_concave_angle_deg
        from ogr_slip2d.surface_altering import curvature_map
        pts = self._PTS
        ls = [0.0] + [1.5] * (len(pts) - 2) + [0.0]
        us = [0.0] + [1.0] * (len(pts) - 2) + [0.0]
        m = len(pts) - 2
        for reverse in (False, True):
            for corner in itertools.product((-1.0, 0.0, 1.0), repeat=m):
                v = [c * (us[i + 1] if c > 0 else ls[i + 1])
                     for i, c in enumerate(corner)]
                out = curvature_map(pts, v, ls, us, reverse=reverse)
                assert max_concave_angle_deg(out) <= 1e-9, (corner, reverse)
                assert [p[0] for p in out] == [p[0] for p in pts]

    def test_the_pair_slide_keeps_x_ordered(self):
        from ogr_slip2d.surface_altering import slide_pair, _END_REACH
        pts = self._PTS
        j, k = 1, 4
        (xj, yj), (xk, yk) = pts[j], pts[k]
        ux = (xk - xj) / math.hypot(xk - xj, yk - yj)
        lo_j = -_END_REACH * (xj - pts[0][0]) / ux
        hi_j = _END_REACH * (xk - xj) / (2 * ux)
        lo_k = -_END_REACH * (xk - xj) / (2 * ux)
        hi_k = _END_REACH * (pts[-1][0] - xk) / ux
        for tj in (lo_j, 0.0, hi_j):
            for tk in (lo_k, 0.0, hi_k):
                out = slide_pair(pts, j, k, tj, tk)
                assert all(q[0] > p[0] for p, q in zip(out, out[1:]))
                assert out[0] == pts[0] and out[-1] == pts[-1]

    def test_the_ground_path_follows_a_vertical_face(self):
        """The three cases of fig. 2: on the face, at its top moving onto
        the crest, at its foot moving onto the flat."""
        from ogr_slip2d.surface_altering import GroundPath
        g = GroundPath([(0.0, 10.0), (20.0, 10.0), (20.0, 30.0),
                        (60.0, 30.0)])
        d, s = g.locate(20.0, 18.0)
        assert d == 0.0 and g.point_at(s + 5.0) == (20.0, 23.0)
        assert g.point_at(s - 5.0) == (20.0, 13.0)
        _d, top = g.locate(20.0, 30.0)
        assert g.point_at(top + 4.0) == (24.0, 30.0)
        _d, foot = g.locate(20.0, 10.0)
        assert g.point_at(foot - 4.0) == (16.0, 10.0)
        lo, hi = g.window(0.0, 20.0)
        assert g.point_at(hi) == (20.0, 30.0)       # the whole face is in


class TestTheEndsStayOnTheGround:
    """Invariant 4."""

    def test_both_ends_on_the_ground_and_each_in_its_window(self):
        from ogr_slip2d.surface_altering import GroundPath
        sup, res, rep = _wall_run()
        assert res is not None and res.is_valid
        g = GroundPath([(0.0, 10.0), (20.0, 10.0), (20.0, 30.0),
                        (60.0, 30.0)])
        v = sup.polyline.vertices
        width = v[-1].x - v[0].x
        for p in (v[0], v[-1]):
            assert g.locate(p.x, p.y)[0] < 1e-9 * width
        assert 0.0 - 1e-9 <= v[0].x <= 20.0 + 1e-9
        assert 24.0 - 1e-9 <= v[-1].x <= 60.0 + 1e-9
        assert res.fos < 2.0  # the start; premise that it moved
        assert rep.iterations > 0


class TestTheShapeIsKept:
    """Invariant 5, across the runs above."""

    def test_x_increasing_and_within_the_concave_ceiling(self):
        from ogr_slip2d.optimize import max_concave_angle_deg
        for sup, res, rep in (_wedge_run(), _sand_run(), _wall_run()):
            v = [(p.x, p.y) for p in sup.polyline.vertices]
            assert all(b[0] > a[0] for a, b in zip(v, v[1:]))
            assert max_concave_angle_deg(v) <= 5.0 + 1e-9


class TestDeterministic:
    """Invariant 6."""

    def test_two_runs_and_two_seeds_give_the_same_surface(self):
        a = _sao(_wedge_model(), "ordinary_fellenius",
                 [(_TOE, 0.0), (45.0, _H)], max_iterations=80, seed=1)
        b = _sao(_wedge_model(), "ordinary_fellenius",
                 [(_TOE, 0.0), (45.0, _H)], max_iterations=80, seed=2)
        pa = [(p.x, p.y) for p in a[0].polyline.vertices]
        pb = [(p.x, p.y) for p in b[0].polyline.vertices]
        assert pa == pb and repr(a[1].fos) == repr(b[1].fos)


class TestTheBudget:
    """Invariant 7."""

    def test_never_more_than_the_budget_and_the_arithmetic_holds(self):
        """Against ``initial_fos``, the start as the optimisation sees it:
        densified to twelve vertices, which slices a little differently
        from the five the search handed over."""
        for budget in (1, 13, 60):
            sup, res, rep = _sao(_wall_model(), "bishop_simplified",
                                 _WALL_START, max_iterations=budget)
            assert rep.iterations <= budget
            if rep.notes.get("stopped_by") == "budget":
                assert rep.iterations == budget
            assert rep.accepted + rep.rejected == rep.iterations
            assert res.fos <= rep.initial_fos
            assert res.is_valid and getattr(res, "admissible", True)


class TestWeakLayers:
    """Invariant 8."""

    def test_it_reaches_the_closed_form_of_the_joint(self):
        sup, res, rep = _cached("joint", lambda: _sao(
            _joint_model(), "ordinary_fellenius", _CAP, max_iterations=400,
            densify_to=5, use_surface_checks=False))
        assert abs(res.fos - _joint_closed()) / _joint_closed() < 1e-9

    def test_step_d_alone_moves_points_onto_the_joint(self):
        from ogr_slip2d.analysis_runner import build_search
        p = _joint_model()
        start = build_search(p, "ordinary_fellenius").evaluate_surface(
            p, _poly(_CAP))
        sup, res, rep = _sao(_joint_model(), "ordinary_fellenius", _CAP,
                             steps=("D",), max_iterations=60, densify_to=5,
                             use_surface_checks=False)
        assert rep.notes.get("weak_layer_snaps", 0) > 0
        assert res.fos < start.fos
        on = [(p.x, p.y) for p in sup.polyline.vertices[1:-1]
              if abs(p.y - (2.0 + (p.x - 2.0) * 8.0 / 28.0)) < 1e-12]
        assert on


class TestMonteCarloIsUntouched:
    """Invariant 9."""

    def _walk(self, **kw):
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
        p = _wall_model()
        return optimize_surface(p, build_search(p, "bishop_simplified"),
                                _poly(_WALL_START),
                                OptimizeSettings(seed=7, max_iterations=60,
                                                 **kw))

    def test_explicit_monte_carlo_is_the_default_bit_for_bit(self):
        a = self._walk()
        b = self._walk(technique="monte_carlo")
        assert ([(p.x, p.y) for p in a[0].polyline.vertices]
                == [(p.x, p.y) for p in b[0].polyline.vertices])
        assert repr(a[1].fos) == repr(b[1].fos)
        assert (a[2].iterations, a[2].accepted, a[2].passes) == (
            b[2].iterations, b[2].accepted, b[2].passes)
        assert a[2].technique == "monte_carlo"

    def test_the_project_default_is_monte_carlo_also_for_old_files(self):
        from ogr_core.project.settings import ProjectSettings, SearchSettings
        assert SearchSettings().optimize_technique == "monte_carlo"
        assert SearchSettings.from_dict({}).optimize_technique == "monte_carlo"
        assert ProjectSettings().optimize_settings().technique == "monte_carlo"


class TestTheSettingMovesTheNumber:
    """Invariant 10, through the search door."""

    def _critical(self, technique):
        from ogr_slip2d.analysis_runner import build_search
        p = _wall_model()
        s = p.settings.search
        s.path_num_surfaces = 40
        s.optimize_enabled = True
        s.optimize_max_iterations = 120
        s.optimize_technique = technique
        r = build_search(p, "bishop_simplified").run(p)
        return r

    def test_surface_altering_moves_the_critical_and_never_above(self):
        mc = _cached("door_mc", lambda: self._critical("monte_carlo"))
        sao = _cached("door_sao", lambda: self._critical("surface_altering"))
        assert mc.critical is not None and sao.critical is not None
        assert abs(mc.critical.fos - sao.critical.fos) > 1e-6
        searched = min(e.fos for e in sao.evaluations
                       if e.is_valid and getattr(e, "admissible", True)
                       and e is not getattr(sao, "optimized", None))
        assert sao.critical.fos <= searched


class TestTheHonouredSettings:
    """Invariant 11."""

    def test_a_loose_tolerance_stops_on_the_tolerance(self):
        """Four control points keep a pass cheap enough for the tight run
        to go past the five passes the criterion needs."""
        def run(tol):
            return _sao(_wall_model(), "bishop_simplified", _WALL_START,
                        max_iterations=1200, densify_to=4, tolerance=tol)
        tight, loose = run(1e-9), run(1.0)
        assert tight[2].passes > 5                  # the premise
        assert loose[2].notes.get("stopped_by") == "tolerance"
        assert loose[2].passes == 5
        assert loose[2].iterations < tight[2].iterations

    def test_the_surface_checks_bite(self):
        """A Minimum Depth that the cohesionless slope wants to break: on,
        the alteration respects it; off, it does not."""
        def run(checks):
            p = _sand_model()
            p.settings.search.min_depth = 3.0
            return _sao(p, "spencer", _SAND_START, max_iterations=120,
                        use_surface_checks=checks)
        on, off = run(True), run(False)
        assert abs(on[1].fos - off[1].fos) > 1e-6
        assert off[1].fos < on[1].fos

    def test_snap_shallow_surfaces_runs_on_the_answer(self):
        """The cohesionless answer runs a few decimetres under the ground
        near its ends, inside a 0.5 m snap distance."""
        sup, res, rep = _sao(_sand_model(), "spencer", _SAND_START,
                             max_iterations=300, snap_shallow_to_slope=True,
                             snap_distance=0.5)
        assert rep.notes.get("snapped_vertices", 0) > 0, rep.notes


class TestTheStartContract:
    """Invariant 12."""

    def test_an_unevaluable_start_gives_the_same_error_note(self):
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
        p = _wall_model()
        bad = [(15.0, 12.0)] + _WALL_START[1:]      # an end in the air
        notes = []
        for technique in ("monte_carlo", "surface_altering"):
            _s, res, rep = optimize_surface(
                p, build_search(p, "bishop_simplified"), _poly(bad),
                OptimizeSettings(technique=technique, max_iterations=20))
            notes.append(rep.notes.get("error"))
        assert notes[0] and notes[0] == notes[1]


class TestTheFocusIsRespected:
    """Invariant 13."""

    def test_the_answer_stays_inside_a_focus_window_and_still_moves(self):
        from ogr_slip2d.focus import FocusKind, FocusObject, accepts_surface
        from ogr_slip2d.methods.base import method_registry
        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
        from ogr_slip2d.search import PathSearch
        p = _wall_model()
        window = FocusObject(kind=FocusKind.WINDOW,
                             points=[(22.0, 2.0), (36.0, 2.0), (36.0, 9.5),
                                     (22.0, 9.5)])
        search = PathSearch(method=method_registry()["bishop_simplified"](),
                            num_slices=30, focus_objects=[window])
        start = _poly(_WALL_START)
        assert accepts_surface([window], _WALL_START)  # the premise
        sup, res, rep = optimize_surface(
            p, search, start, OptimizeSettings(technique="surface_altering",
                                               max_iterations=150,
                                               snap_shallow_to_slope=False))
        assert accepts_surface([window], [(q.x, q.y)
                                          for q in sup.polyline.vertices])
        assert rep.accepted > 0


class TestTheNotes:
    """Invariant 14."""

    def test_the_walk_settings_are_named_only_when_changed(self):
        from ogr_core.project.settings import SearchSettings
        from ogr_slip2d.analysis_runner import _optimize_notes
        s = SearchSettings(search_method="path", surface_type="non_circular",
                           optimize_enabled=True)
        key = "Surface Altering does not read"
        s.optimize_technique = "surface_altering"
        assert not any(key in n for n in _optimize_notes(s))
        s.optimize_explore_all_vertices = True
        assert any(key in n for n in _optimize_notes(s))
        s.optimize_technique = "monte_carlo"
        assert not any(key in n for n in _optimize_notes(s))

    def test_an_unknown_technique_is_refused(self):
        from ogr_slip2d.analysis_runner import check_analysis_settings
        from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
        from ogr_slip2d.analysis_runner import build_search
        p = _wall_model()
        p.settings.search.optimize_technique = "bobyqa"
        assert any("bobyqa" in m for m in check_analysis_settings(p))
        _s, res, rep = optimize_surface(
            p, build_search(p, "bishop_simplified"), _poly(_WALL_START),
            OptimizeSettings(technique="bobyqa"))
        assert res is None and "bobyqa" in rep.notes.get("error", "")

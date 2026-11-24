# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.471 (D357, spec 009 tasks 30–32) — the angles of the faces between
Sarma's wedges that make the factor least (``sarma.optimize_angles``), and
the two values of ``settings.sarma.slice_angles`` that ask for them:
``optimized_global`` (every surface with the bisector, the critical one
optimised afterwards, in its place) and ``optimized_all`` (every surface
optimised).

THE REFERENCE (rule 1)
    Problem 1 of the reference's Sarma verification manual (Baker 1980, on
    Fredlund and Krahn 1977): its figures 1.2 and 1.3 draw the optimised
    surfaces with three and «seven» wedges, F = 1.382 and 1.324. Digitised
    by the bank's ``_auditoria/P9_D357/digitalizar_p1_v1471.py`` with the
    reading DECLARED there:

    * the images of the PDF at their native resolution (456 × 417 and
      619 × 558 px), calibrated in x and y apart (x = −7, the toe x = 0, the
      crest corner x = 27, x = 40; y = 1.25, 13.5 and 0), residuals under
      0.07 m;
    * each drawn line fitted by least squares on its dark pixels, the
      vertices their intersections, the entry and the exit put on the
      ground;
    * the weak layer where the figures' colours put it: y = 0 to 0.75
      (green 60,179,113), the upper soil above (gold 242,206,0, the slope's
      own); the bank's model had it at 0.75–1.25 (D459), and on these
      surfaces gives 2.40.

    Figure 1.3 draws EIGHT wedges for «seven slices» (one at the toe, five
    equal on the flat stretch, two on the scarp); the faces on a straight
    stretch of one material move no factor, so it is the same mechanism.

THE TOLERANCES (the owner's decisions of 2026-11-17)
    * Figure 1.3: 1 % of 1.324. The ±1 px reading moves F by 0.0045; what
      is left (0.7 %) is the strength of the faces: 1.324 lies between the
      mean of the materials by length (1.3147) and the upper soil alone
      (1.3388), and the toe face crosses the two nearly half and half.
    * Its faces: the reference's drawn faces are optimal in this model to
      0.1 % (measured +0.072 %, under the published 1.324 ± 0.04 %), and
      the face at the kink within 2° of the drawn one (measured 1.64°; the
      minimum is flat: 0.046 % at the drawn angle).
    * Figure 1.2: the base of the toe wedge crosses the contact y = 0.75,
      and the wedge takes the material of its midpoint. The reading puts
      it 0.015 m under the contact (the weak layer, 1.3367); half a pixel
      higher puts it in the upper soil, and gives 1.382 to 0.2 %.

    Problem 4 of the same manual (Hoek 1987), dry, with its one interface:
    the optimiser on that face against a brute sweep, and at or under the
    published 1.198 of the interface Hoek gives.

THE RULES (each measured before it was written; the module docstring)
    * The pattern search never ends above any policy.
    * The push: a move takes the neighbours it crosses with it. Judged on
      figure 1.3 by an independent push (retry the neighbour the
      constructor names) that no pushed move of the last step improves.
    * The continuity: a jump of the factor across a move is refused.
      Judged exactly on a synthetic factor with a step in it.
    * The guard of D457 (v0.1.471 to v0.1.486): a factor whose wedges had a
      larger root was refused. v0.1.487 (D457): ``solve`` no longer steps
      over one, and the guard went (the owner's decision); what is left
      here is that the factor kept on a circle of close roots (Ru 0.7) is
      the largest root of its wedges by the independent Kc of
      ``test_sarma_solver_v1461`` (``_kc_direct``).
    * The fold (the review): where the largest root meets the next and
      both vanish, the search stopped wherever its last step left it, and
      the factor depended on the step (−1.3 % with a step eight times
      finer). The edge is now halved (to 0.001° in v0.1.471, to
      ``FOLD_STEP`` = 1e-7° since v0.1.487, D457, where F goes as the
      square root of the distance to a true fold): the saturated problem 4
      gives the same edge with two wedges and with ten, and with a last
      step eight times finer, and the run says it is a fold.
    * Under an objective other than F (Ky), a critical surface the faces
      would rank after keeps its own (the owner's decision); the
      sensitivity computes the frozen faces, as the samples do.

COST
    About 18 s together on this machine (2026-11-17), shared through two
    caches: figure 1.3 optimised (about 1 s, bounded at 400 wedges built)
    for the reference, once more with «all surfaces», the circle of close roots
    with its judge, problem 4 saturated with ten wedges (a published case,
    about 3 s) and problem 5 with γw = 9.81. No other test above about 2 s.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import test_sarma_wedges_v1463 as W63  # noqa: E402

# ----------------------------------------------------------------- problem 1
#: The polylines of figures 1.2 and 1.3, as ``(name, x, y)``: the entry, the
#: vertices of the base (one at the foot of each face drawn) and the exit.
_FIG12 = (("entry", -1.7029, 1.25), ("P1", -0.545, 0.2214),
          ("P2", 23.5502, 0.2214), ("exit", 35.512, 13.5))
_FIG12_FACES = {"P1": 50.33, "P2": 117.58}
_FIG13 = (("entry", -2.7803, 1.25), ("P1", -0.4, 0.1089),
          ("B2", 4.1133, 0.132), ("B3", 8.7648, 0.1559),
          ("B4", 13.4207, 0.1798), ("B5", 18.0673, 0.2036),
          ("P2", 22.7384, 0.2276), ("B7", 28.4282, 6.8082),
          ("exit", 34.2142, 13.5))
_FIG13_FACES = {"P1": 75.28, "B2": 90.0, "B3": 90.0, "B4": 94.21,
                "B5": 123.25, "P2": 116.83, "B7": 140.82}
_PUBLISHED = {"fig12": 1.382, "fig13": 1.324}
#: Figure 1.2's model metres per pixel in y: half a pixel up.
_HALF_PX = 0.5 * 0.11546


def _problem1():
    from ogr_core.geometry import Boundary, BoundaryType
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    p = Project("v1471 problem 1")
    W63._external(p, ((-7, 0), (40, 0), (40, 13.5), (27, 13.5), (0, 1.25),
                      (-7, 1.25)))
    upper = Material(name="Upper soil", unit_weight=18.84,
                     strength=MohrCoulomb(cohesion=28.45,
                                          friction_angle=20.0))
    weak = Material(name="Weak layer", unit_weight=18.84,
                    strength=MohrCoulomb(cohesion=0.0, friction_angle=10.0))
    p.add_boundary(Boundary(polyline=W63._pl(((-7, 0.75), (40, 0.75))),
                            btype=BoundaryType.MATERIAL))
    p.materials = [upper, weak]
    p.assign_material_at(20.0, 5.0, upper.id)
    p.assign_material_at(20.0, 0.3, weak.id)
    sa = p.settings.sarma
    sa.tolerance = 1e-6
    sa.boundaries_at_materials = False
    return p


def _surface(points, dy=0.0, faces=None):
    """The polyline, its flat base (every vertex but the ends and the one on
    the scarp) raised ``dy``, with ``faces`` {name: θ} at its vertices."""
    from ogr_slip2d.surface import SlipSurface, attach_vertex_data
    pts = [(n, x, y + (dy if n not in ("entry", "exit", "B7") else 0.0))
           for n, x, y in points]
    s = SlipSurface(polyline=W63._pl([(x, y) for _n, x, y in pts]))
    if faces:
        by = {n: (x, y) for n, x, y in pts}
        attach_vertex_data(s, {by[n]: {"angle": a, "c": None, "phi": None}
                               for n, a in faces.items()})
    return s


def _door(project, surface, mode="bisector", n=None, **sarma):
    from ogr_slip2d.analysis_runner import evaluate_surfaces
    sa = project.settings.sarma
    sa.slice_angles = mode
    if n is not None:
        sa.num_slices = n
    for k, v in sarma.items():
        setattr(sa, k, v)
    out = evaluate_surfaces(project, surface, ["sarma"],
                            allow_unconfigured=True)
    return out.results["sarma"]


_CACHE: dict = {}


def _p1(fig, mode="bisector", faces=False, dy=0.0, **sarma):
    key = (fig, mode, faces, dy, tuple(sorted(sarma.items())))
    if key not in _CACHE:
        pts = _FIG12 if fig == "fig12" else _FIG13
        given = (_FIG12_FACES if fig == "fig12" else _FIG13_FACES) \
            if faces else None
        _CACHE[key] = _door(_problem1(), _surface(pts, dy, given), mode,
                            len(pts) - 1, **sarma)
    return _CACHE[key]


def _theta_at(res, x):
    f = next(f for f in res.slices.faces if abs(f.x_base - x) < 1e-6)
    return math.degrees(f.theta)


# ======================================================================
class TestProblem1:

    def test_figure_13_with_its_drawn_faces(self):
        r = _p1("fig13", faces=True)
        assert len(r.slices) == 8
        assert abs(r.fos / _PUBLISHED["fig13"] - 1.0) < 0.01, r.fos
        # the 0.7 % left is the strength of the faces: 1.324 between the
        # mean of the materials and the upper soil alone
        upper = _p1("fig13", faces=True, interslice_strength="given",
                    interslice_cohesion=28.45, interslice_phi=20.0)
        assert r.fos < _PUBLISHED["fig13"] < upper.fos, (r.fos, upper.fos)

    def test_figure_13_optimised(self):
        drawn = _p1("fig13", faces=True)
        r = _p1("fig13", mode="optimized_global")
        d = r.details
        assert r.slices.angle_policy == "optimized_global"
        assert d["sarma_angle_mode"] == "optimized_global"
        assert abs(r.fos / _PUBLISHED["fig13"] - 1.0) < 0.01, r.fos
        # at or under the drawn faces, and they optimal to 0.1 %
        assert r.fos <= drawn.fos + 1e-6, (r.fos, drawn.fos)
        assert drawn.fos <= r.fos * 1.001, (r.fos, drawn.fos)
        # the face at the kink: within 2° of the drawn one
        x = dict((n, x) for n, x, _y in _FIG13)["P2"]
        assert abs(_theta_at(r, x) - _FIG13_FACES["P2"]) < 2.0, \
            _theta_at(r, x)
        # the faces the user did not give are the optimiser's
        assert all(f.angle_source == "optimized"
                   for f in r.slices.faces[1:-1])
        assert d["sarma_angle_trials"] <= 400, d["sarma_angle_trials"]

    def test_figure_12_two_branches_at_the_contact(self):
        reading = _p1("fig12", faces=True)
        toe = reading.slices[0]
        mid = 0.5 * (toe.base_y_left + toe.base_y_right)
        assert 0.73 < mid < 0.75 and toe.material.name == "Weak layer"
        assert reading.fos < 0.98 * _PUBLISHED["fig12"], reading.fos
        up = _p1("fig12", faces=True, dy=_HALF_PX)
        assert up.slices[0].material.name == "Upper soil"
        assert abs(up.fos / _PUBLISHED["fig12"] - 1.0) < 0.002, up.fos

    def test_figure_12_optimised(self):
        r = _p1("fig12", mode="optimized_global")
        assert r.fos <= _p1("fig12", faces=True).fos + 1e-6
        assert r.details["sarma_start_fos"] == _p1("fig12").fos


# ======================================================================
def _policies(project_fn, surface_fn, n):
    out = {}
    for pol in ("vertical", "bisector", "mean_normal"):
        r = _door(project_fn(), surface_fn(), pol, n)
        out[pol] = r.fos if r is not None and r.is_valid else None
    return out


def _circle(ru, n):
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.project import Project
    from ogr_slip2d.surface import SlipCircle
    p = Project("v1471 circle")
    W63._external(p, ((0, 0), (80, 0), (80, 20), (40, 20), (20, 10),
                      (0, 10)))
    soil = Material(name="soil", unit_weight=18.0, sat_unit_weight=20.0,
                    use_sat_unit_weight=True,
                    strength=MohrCoulomb(cohesion=1.0, friction_angle=30.0))
    soil.pore_pressure = PorePressureType.RU_COEFFICIENT
    soil.ru = ru
    p.materials = [soil]
    p.settings.sarma.num_slices = n
    p.settings.sarma.tolerance = 1e-6
    return p, SlipCircle(centre_x=30, centre_y=35, radius=26)


class TestNeverAboveAPolicy:

    def _check(self, project_fn, surface_fn, n):
        pols = _policies(project_fn, surface_fn, n)
        best = min(v for v in pols.values() if v is not None)
        r = _door(project_fn(), surface_fn(), "optimized_global", n)
        assert r.fos <= best + 1e-9, (r.fos, pols)
        assert r.details["sarma_start_fos"] == best
        assert r.details["sarma_start_policy"] == min(
            (k for k in pols if pols[k] is not None), key=lambda k: pols[k])
        return r, pols

    def test_figure_13(self):
        # the cached runs of TestProblem1, the same door
        pols = {pol: _p1("fig13", mode=pol).fos
                for pol in ("vertical", "bisector", "mean_normal")}
        r = _p1("fig13", mode="optimized_global")
        assert r.fos <= min(pols.values()) + 1e-9, (r.fos, pols)
        assert r.details["sarma_start_fos"] == min(pols.values())

    def test_a_circle(self):
        r, pols = self._check(lambda: _circle(0.3, 6)[0],
                              lambda: _circle(0.3, 6)[1], 6)
        assert r.fos < min(v for v in pols.values() if v) - 1e-4

    def test_twice_the_same_bits(self):
        a = _door(_problem1(), _surface(_FIG12), "optimized_global", 3)
        b = _door(_problem1(), _surface(_FIG12), "optimized_global", 3)
        assert a.fos == b.fos
        assert [f.theta for f in a.slices.faces] == \
            [f.theta for f in b.slices.faces]


# ======================================================================
class TestOneFaceAgainstABruteSweep:
    """Problem 4 dry (Hoek 1987), its one interface at the kink: the
    optimiser against every degree and then every hundredth of one around
    the best."""

    def test_problem_4_dry(self):
        from ogr_slip2d.sarma.wedges import build_wedges, solve_wedges
        from ogr_slip2d.slicer import slice_surface
        p, s, angles = W63._problem4(False)
        kink = next(iter(angles))
        v = slice_surface(p, s, num_slices=30)

        def F(th):
            w = build_wedges(p, s, v, 2, vertex_angles={kink: th})
            if w is None:
                return math.inf
            sol = solve_wedges(w, 0.0, 0.0, tolerance=1e-10)
            return sol.fos if sol.fos is not None else math.inf
        best = min((F(float(k)), float(k)) for k in range(1, 180))
        best = min((F(best[1] + 0.01 * k), best[1] + 0.01 * k)
                   for k in range(-100, 101))
        p, s, _a = W63._problem4(False)
        r = _door(p, s, "optimized_global", 2, tolerance=1e-10)
        assert abs(r.fos - best[0]) < 1e-4 * best[0], (r.fos, best)
        assert abs(_theta_at(r, kink[0]) - best[1]) < 0.5
        # at or under the factor of Hoek's own interface (published 1.198)
        assert r.fos <= W63._PUBLISHED4[False]
        # it started from the best policy, here the mean normal (1.2010;
        # the bisector gives 1.2722)
        pols = {}
        for pol in ("vertical", "bisector", "mean_normal"):
            p, s, _a = W63._problem4(False)
            q = _door(p, s, pol, 2, tolerance=1e-10)
            pols[pol] = q.fos if q is not None and q.is_valid else math.inf
        assert r.details["sarma_start_policy"] == "mean_normal", pols
        assert r.details["sarma_start_fos"] == min(pols.values())


class TestTheInterfaceOfHoekIsReached:
    """Problem 4 saturated (Hoek 1987), ten wedges asked (eight built):
    the face at the kink has to swing past the faces of the scarp to reach
    the interface Hoek gives (F 0.4347, published 0.434) and beyond. Without
    the push a move alone crosses them and the search stops at 0.585.
    With it, the search goes down to a fold, the edge past which the
    largest root and the next vanish (0.19955 since v0.1.487, 0.2037 when
    the solver's sweep lost the pair before it met; every face in tension
    there; near Spencer's 0.209 on this surface by coincidence, the review
    of 0.1.471). About 3 s: a published case."""

    def test_at_or_under_the_published_interface(self):
        p, s, angles = W63._problem4(True)
        from ogr_slip2d.surface import attach_vertex_data
        attach_vertex_data(s, {k: {"angle": a, "c": None, "phi": None}
                               for k, a in angles.items()})
        hoek = _door(p, s, "bisector", 10, tolerance=1e-6)
        assert abs(hoek.fos - W63._PUBLISHED4[True]) < 1e-3, hoek.fos
        r = _hoek_fold(10)
        assert r.fos <= hoek.fos, (r.fos, hoek.fos)

    def test_the_fold_is_its_edge_whatever_the_step(self):
        """The same edge with two wedges and with ten, and with a last step
        eight times finer: no longer where the last step left it."""
        from ogr_slip2d.analysis_runner import sarma_notes
        from ogr_slip2d.sarma import optimize_angles as OA
        ten, two = _hoek_fold(10), _hoek_fold(2)
        kept = OA.STEPS
        OA.STEPS = kept + (0.15625, 0.078125, 0.0390625)
        try:
            finer = _hoek_fold(2, cache=False)
        finally:
            OA.STEPS = kept
        for r in (ten, two, finer):
            assert r.details["sarma_fold_faces"] >= 1
        assert abs(ten.fos / two.fos - 1.0) < 1e-4, (ten.fos, two.fos)
        assert abs(finer.fos / two.fos - 1.0) < 1e-4, (finer.fos, two.fos)
        codes = [getattr(n, "code", None) for n in sarma_notes(two)]
        assert "method.sarma_angles_fold" in codes, codes


def _hoek_fold(n, cache=True):
    key = ("hoek", n)
    if not cache or key not in _CACHE:
        p, s, _a = W63._problem4(True)
        r = _door(p, s, "optimized_global", n, tolerance=1e-6)
        if not cache:
            return r
        _CACHE[key] = r
    return _CACHE[key]


# ======================================================================
class TestTheConstructorByAbscissa:
    """``build_wedges(boundaries=..., face_angles=...)``: the faces the
    optimiser sets are like a vertex's, never dropped nor made vertical, on
    the slope of ``test_sarma_wedges_v1463`` (its refusals by vertex)."""

    def _build(self, p, s, n=1, **kw):
        from ogr_slip2d.sarma.wedges import build_wedges
        from ogr_slip2d.slicer import slice_surface
        v = slice_surface(p, s, num_slices=30)
        reasons = []
        return build_wedges(p, s, v, n, reasons=reasons, **kw), reasons

    def test_a_face_that_does_not_leave_is_refused(self):
        from ogr_slip2d import messages as msg
        p, s = W63._slope(load=False)
        w, why = self._build(p, s, face_angles={60.0: 10.0})
        assert w is None and why[0][0] == msg.SARMA_FACE_NO_EXIT, why
        assert why[0][1]["face"] == 5

    def test_two_that_cross_are_refused(self):
        from ogr_slip2d import messages as msg
        p, s = W63._slope(load=False)
        w, why = self._build(p, s, face_angles={24.0: 30.0, 40.0: 150.0})
        assert w is None and why[0] == (msg.SARMA_FACES_CROSS,
                                        {"face": 3, "next": 4}), why

    def test_the_same_faces_the_same_wedges(self):
        """The wedges of a policy, built again from their own boundaries
        and angles by abscissa: the same factor, the faces ``optimized``."""
        p, s = W63._slope(load=False)
        w, _ = self._build(p, s, 8)
        again, why = self._build(p, s, 8, boundaries=w.boundaries,
                                 face_angles={f.x_base: math.degrees(f.theta)
                                              for f in w.faces[1:-1]})
        assert again is not None, why
        assert abs(W63._f(again) - W63._f(w)) < 1e-12
        assert ([f.angle_source for f in again.faces[1:-1]]
                == ["optimized"] * (len(w.faces) - 2))

    def test_boundaries_without_the_ends_are_an_error(self):
        p, s = W63._slope(load=False)
        w, _ = self._build(p, s, 4)
        for bad in (w.boundaries[1:], w.boundaries[:-1],
                    tuple(reversed(w.boundaries))):
            try:
                self._build(p, s, 4, boundaries=bad)
            except ValueError:
                continue
            raise AssertionError(bad)


# ======================================================================
class _Fake:
    """Wedges and results a synthetic factor answers for: a slope, and
    one interior face at (30, 2) whose angle sets F."""

    def __init__(self, factor):
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_slip2d.sarma.wedges import WedgeFace
        self.p = Project("v1471 fake")
        W63._external(self.p, ((0, 0), (80, 0), (80, 20), (40, 20),
                               (20, 10), (0, 10)))
        self.p.materials = [Material(name="soil", unit_weight=18.0,
                                     strength=MohrCoulomb(cohesion=1.0,
                                                          friction_angle=30.0))]
        self.factor = factor
        self.WedgeFace = WedgeFace
        self.calls = 0

    def build(self, policy=None, boundaries=None, face_angles=None):
        from types import SimpleNamespace
        th = 90.0 if face_angles is None else next(iter(face_angles.values()))
        face = self.WedgeFace(index=1, x_base=30.0, y_base=2.0, x_top=30.0,
                              y_top=17.5, theta=math.radians(th), length=1.0,
                              angle_source=(policy or "optimized"))
        ends = [self.WedgeFace(index=0, x_base=5.0, y_base=10.0, x_top=5.0,
                               y_top=10.0, theta=math.pi / 2, length=0.0,
                               angle_source="end"),
                self.WedgeFace(index=2, x_base=75.0, y_base=20.0, x_top=75.0,
                               y_top=20.0, theta=math.pi / 2, length=0.0,
                               angle_source="end")]
        return SimpleNamespace(faces=[ends[0], face, ends[1]],
                               boundaries=(5.0, 30.0, 75.0), theta=th)

    def evaluate(self, w):
        from types import SimpleNamespace
        self.calls += 1
        return SimpleNamespace(fos=self.factor(w.theta), theta=w.theta)

    def run(self):
        from ogr_slip2d.sarma.optimize_angles import optimize
        return optimize(self.p, build=self.build, evaluate=self.evaluate,
                        gain=1e-9)


class TestTheRulesExactly:

    def test_a_smooth_drop_is_followed_and_a_step_is_not(self):
        """F = 1 + (θ − 55)²/1000 above 55°, a step down to 0.5 below: the
        search comes down the smooth side (drops far above 1 % each) and
        stops at the step."""
        fake = _Fake(lambda th: 1.0 + (th - 55.0) ** 2 / 1000.0
                     if th >= 55.0 else 0.5)
        out = fake.run()
        assert out.jumps >= 1
        assert 55.0 <= out.result.theta < 55.0 + 0.3125 + 1e-9, \
            out.result.theta
        assert out.result.fos < 1.0 + 1e-4

    def test_without_the_step_it_goes_on(self):
        fake = _Fake(lambda th: 1.0 + (th - 40.0) ** 2 / 1000.0)
        out = fake.run()
        assert out.jumps == 0
        assert abs(out.result.theta - 40.0) < 0.3125

    def test_no_policy_no_optimum(self):
        fake = _Fake(lambda th: 1.0)
        fake.evaluate = lambda w: None
        assert fake.run() is None


# ======================================================================
def _judge_of(result):
    """The independent Kc of ``result``'s wedges (``_kc_direct``), with
    the senses of the face shear the solver used."""
    from test_sarma_near_pair_v1470 import _Judge, _solver_input
    from ogr_slip2d.sarma import solver as SV
    si = _solver_input(result)
    sol = SV.solve(si.bases, si.faces, slide_sign=si.slide_sign,
                   head_thrust=si.head_thrust, tolerance=1e-10)
    return _Judge(si.bases, si.faces, sol.slide_sign, sol.senses)


class TestTheRulesOnRealWedges:

    def test_the_push_figure_13_is_a_minimum_of_pushed_moves(self):
        """An independent push: move one face by the last step, and while
        the constructor refuses the crossing it names, make the neighbour
        parallel; no such move lowers the factor by more than the
        tolerance."""
        from ogr_slip2d import messages as msg
        from ogr_slip2d.sarma.wedges import build_wedges
        r = _p1("fig13", mode="optimized_global")
        p = _problem1()
        s = _surface(_FIG13)
        from ogr_slip2d.analysis_runner import build_search
        from ogr_core.project import prepare_analysis_project
        pp, _rep = prepare_analysis_project(p)
        p.settings.sarma.num_slices = 8
        search = build_search(pp, "sarma")
        base = search.evaluate_surface(pp, s)
        vertical = base.slices.vertical
        faces = r.slices.faces
        xs = r.slices.boundaries
        theta = {f.x_base: math.degrees(f.theta) for f in faces[1:-1]}
        keys = sorted(theta)
        best = r.fos
        tol = p.settings.sarma.tolerance
        for i, x in enumerate(keys):
            for d in (-0.3125, 0.3125):
                th = dict(theta)
                th[x] += d
                for _tries in range(len(keys)):
                    why = []
                    w = build_wedges(pp, base.surface, vertical, 8,
                                     boundaries=xs, face_angles=th,
                                     boundaries_at_materials=False,
                                     reasons=why)
                    if w is not None:
                        break
                    code, args = next((c for c in why if isinstance(c, tuple)),
                                      (None, {}))
                    if code != msg.SARMA_FACES_CROSS:
                        break
                    # faces a < b (0-based, the end faces included): the
                    # one farther from the moved face takes the other's
                    a, b = args["face"] - 1, args["next"] - 1
                    moved, keep = (a, b) if b <= i + 1 else (b, a)
                    if not 0 < moved < len(keys) + 1:
                        break
                    th[keys[moved - 1]] = (th[keys[keep - 1]]
                                           if 0 < keep < len(keys) + 1
                                           else th[x])
                if w is None:
                    continue
                F = search.method.compute_fos(pp, base.surface, w).fos
                assert F is None or F >= best - 2 * tol, (x, d, F, best)

    def test_the_factor_kept_on_a_circle_of_close_roots(self):
        """Ru 0.7 (D452's circle, roots and poles interleaved), 8 wedges: the
        factor kept is the largest root of its wedges by an independent Kc
        (``_kc_direct``). Until v0.1.486 the guard of D457 refused factors
        here; v0.1.487 has no guard, and the solver gives the largest root.

        The search ends on a fold here (the largest root and the next meet:
        0.51808, two faces on the edge), so the two roots lie within the
        solver's tolerance of the factor and Kc − kh need not change sign
        across ±1e-5 of it (measured: it does not; it does within 1e-6)."""
        p, s = _circle(0.7, 8)
        r = _door(p, s, "optimized_global", 8)
        assert "sarma_sweep_misses" not in r.details
        assert r.details["sarma_fold_faces"] >= 1
        judge = _judge_of(r)
        # a root to the solver's tolerance (1e-6 on F about 0.5)
        assert judge.changes_near(r.fos, 1e-5) >= 1, r.fos
        assert _roots_above(judge, r.fos, 50.0) == [], r.fos


def _roots_above(judge, F, top, n=1500):
    """The roots of Kc = kh above ``F`` (up to ``top``) by the independent
    Kc: each change of sign of a fine logarithmic scan is bisected, and it
    is a root when Kc − kh goes to zero there, a pole of Kc when it grows.
    v0.1.471: the rule of 0.1.470's judge («a pole has |Kc − kh| > 1»)
    reads a pole of Kc that nearly cancels (D and N both near zero, D452)
    as a root: measured on this circle at F = 0.5269, where D vanishes and
    H, the polynomial without poles, does not change sign."""
    import numpy as np
    xs = np.geomspace(F * (1.0 + 1e-5), top, n)
    vs = [judge.h(x) for x in xs]
    roots = []
    for a, b, va, vb in zip(xs, xs[1:], vs, vs[1:]):
        if va is None or vb is None or (va > 0.0) == (vb > 0.0):
            continue
        lo, hi, vlo = a, b, va
        for _ in range(80):
            m = 0.5 * (lo + hi)
            vm = judge.h(m)
            if vm is None:
                break
            if (vm > 0.0) == (vlo > 0.0):
                lo, vlo = m, vm
            else:
                hi = m
        ends = [judge.h(lo), judge.h(hi)]
        if (all(v is not None for v in ends)
                and min(abs(v) for v in ends) < 1e-6):
            roots.append(float(lo))
    return roots


# ======================================================================
class TestRule7AndTheDoors:

    def test_global_moves_the_factor(self):
        assert _p1("fig12", mode="optimized_global").fos < \
            _p1("fig12").fos - 1e-3

    _RUNS: dict = {}

    def _two_surfaces(self, mode, second="given"):
        """Figure 1.3's surface free, and after it either the same with every
        face given at its vertices (``given``: nothing to optimise; 1.3173
        with the bisector, the drawn faces 1.3147, optimised 1.3137) or
        figure 1.2's, free (``fig12``). One run per case, shared."""
        key = (mode, second)
        if key not in self._RUNS:
            self._RUNS[key] = self._run_two(mode, second)
        return self._RUNS[key]

    def _run_two(self, mode, second):
        from ogr_core.geometry.user_polyline import UserPolylineSurface
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.search import SearchResult
        from ogr_core.project import prepare_analysis_project
        p = _problem1()
        p.settings.sarma.num_slices = 8
        p.settings.sarma.slice_angles = mode
        p.settings.search.surface_type = "non_circular"
        pts = [(x, y) for _n, x, y in _FIG13]
        free = UserPolylineSurface.from_points(pts)
        if second == "given":
            other = UserPolylineSurface.from_points(pts, vertex_data=[
                {"x": x, "y": y, "angle": _FIG13_FACES[n]}
                for n, x, y in _FIG13[1:-1]])
        else:
            other = UserPolylineSurface.from_points(
                [(x, y) for _n, x, y in _FIG12])
        p.user_polylines = [free, other]
        pp, _rep = prepare_analysis_project(p)
        search = build_search(pp, "sarma")
        search._run = lambda project: SearchResult(method_id="sarma")
        return search.run(pp)

    def test_all_against_global(self):
        g = self._two_surfaces("optimized_global")
        a = self._two_surfaces("optimized_all")
        # global: the given surface is the critical one (1.3147 < 1.3173),
        # and nothing in it moves: it is not marked as optimised either
        assert "sarma_angle_mode" not in g.critical.details
        assert g.critical is g.user_evaluations[1], [
            r.fos for r in g.user_evaluations]
        # all: the free one, optimised, goes under it
        assert a.critical is a.user_evaluations[0]
        assert a.critical.fos < g.critical.fos - 1e-4
        assert a.user_evaluations[0].details["sarma_angle_mode"] == \
            "optimized_all"

    def test_the_critical_is_replaced_in_its_place(self):
        """Figures 1.3 and 1.2, both free: the critical one (1.3) is
        replaced by its optimised result in its place, the other keeps the
        bisector's."""
        b = self._two_surfaces("bisector", "fig12")
        g = self._two_surfaces("optimized_global", "fig12")
        assert len(g.user_evaluations) == len(b.user_evaluations) == 2
        assert g.valid_count == b.valid_count
        assert g.attempts == b.attempts
        assert b.critical is b.user_evaluations[0]
        crit = g.user_evaluations[0]
        assert g.critical is crit and crit is not b.critical
        assert crit.details["sarma_angle_mode"] == "optimized_global"
        assert crit.slices.angle_policy == "optimized_global"
        assert crit.fos < b.critical.fos
        assert g.user_evaluations[1].fos == b.user_evaluations[1].fos
        assert "sarma_angle_mode" not in g.user_evaluations[1].details

    def test_under_ky_a_worse_critical_is_not_replaced(self):
        """Ky on (the objective of the run): figure 1.3 free is the critical
        surface by Ky (0.09979); its optimised faces lower F and raise Ky
        (0.10064), so it keeps its own, and the note says why (the owner's
        decision)."""
        from ogr_slip2d.analysis_runner import sarma_notes
        from ogr_core.geometry.user_polyline import UserPolylineSurface
        from ogr_slip2d.analysis_runner import build_search
        from ogr_slip2d.search import SearchResult
        from ogr_core.project import prepare_analysis_project
        p = _problem1()
        p.settings.sarma.num_slices = 8
        p.settings.sarma.slice_angles = "optimized_global"
        p.settings.search.surface_type = "non_circular"
        p.settings.seismic.compute_ky = True
        pts = [(x, y) for _n, x, y in _FIG13]
        p.user_polylines = [
            UserPolylineSurface.from_points(pts),
            UserPolylineSurface.from_points(pts, vertex_data=[
                {"x": x, "y": y, "angle": _FIG13_FACES[n]}
                for n, x, y in _FIG13[1:-1]])]
        pp, _rep = prepare_analysis_project(p)
        search = build_search(pp, "sarma")
        search._run = lambda project: SearchResult(
            method_id="sarma", objective=search.objective)
        out = search.run(pp)
        assert out.objective != "fos"
        crit = out.critical
        assert crit is out.user_evaluations[0]
        assert "sarma_angle_mode" not in crit.details
        kept = crit.details["sarma_angle_kept"]
        assert kept["optimised"] > kept["kept"], kept
        codes = [getattr(n, "code", None) for n in sarma_notes(crit)]
        assert "method.sarma_angles_kept" in codes, codes

    def test_the_sensitivity_keeps_the_faces(self):
        """The sensitivity's point at the mean is the deterministic
        optimised factor, as a Global Minimum sample is (the review)."""
        from ogr_core.statistics import (Distribution, DistributionType,
                                         available_variables)
        from ogr_slip2d.sensitivity import run_sensitivity
        p = _problem1()
        p.settings.sarma.slice_angles = "optimized_global"
        p.settings.sarma.num_slices = 3
        det = _door(p, _surface(_FIG12), "optimized_global", 3)
        rv = next(v for v in available_variables(p)
                  if v.key.endswith(":friction_angle")
                  and "Weak" in v.label)
        rv.distribution = Distribution(dist_type=DistributionType.UNIFORM,
                                       mean=10.0, rel_min=1.0, rel_max=1.0)
        out = run_sensitivity(p, {"sarma": det}, [rv], intervals=2)
        sweep = next(iter(out.by_method["sarma"].values()))
        at_mean = dict(zip(sweep.values, sweep.fos))[10.0]
        assert abs(at_mean - det.fos) < 1e-9, (at_mean, det.fos)
        assert at_mean < _p1("fig12").fos - 1e-3

    def test_a_probabilistic_sample_keeps_the_faces(self):
        """Global Minimum: every sample computes the deterministic
        mechanism, faces and all (the owner's decision): with the weak
        layer's φ held, each sample is the optimised factor, not the
        bisector's, and the check of D88 lets the method through."""
        from ogr_core.statistics import (Distribution, DistributionType,
                                         SamplingMethod, available_variables)
        from ogr_slip2d.probabilistic import run_global_minimum
        p = _problem1()
        p.settings.sarma.slice_angles = "optimized_global"
        p.settings.sarma.num_slices = 3
        det = _door(p, _surface(_FIG12), "optimized_global", 3)
        rv = next(v for v in available_variables(p)
                  if v.key.endswith(":friction_angle")
                  and "Weak" in v.label)
        rv.distribution = Distribution(dist_type=DistributionType.UNIFORM,
                                       mean=10.0, rel_min=1e-9, rel_max=1e-9)
        out = run_global_minimum(p, {"sarma": det}, [rv], num_samples=3,
                                 sampling=SamplingMethod.LATIN_HYPERCUBE,
                                 seed=7)
        m = out.by_method["sarma"]
        assert m.statistics.n == 3, out.note_lines
        assert all(abs(v - det.fos) < 1e-6 for v in m.statistics.values), \
            (m.statistics.values, det.fos, _p1("fig12").fos)


# ======================================================================
class TestItIsSaid:

    def test_settings_api_and_report(self):
        from ogr_api.settings_schema import choices_for
        assert {"optimized_global", "optimized_all"} <= set(
            choices_for("sarma.slice_angles"))
        from ogr_slip2d.analysis_runner import sarma_setting_problem
        p = _problem1()
        for mode in ("optimized_global", "optimized_all"):
            p.settings.sarma.slice_angles = mode
            assert sarma_setting_problem(p) is None
        p.settings.sarma.slice_angles = "optimised"
        assert sarma_setting_problem(p)[0] == "slice_angles"
        from ogr_core.report.report_generator import _sarma_result_rows
        rows = dict(_sarma_result_rows(_p1("fig12", mode="optimized_global")))
        assert rows["Faces Optimised From"] == "Bisector"
        from ogr_api.results import lem_summary
        d = lem_summary(_p1("fig12", mode="optimized_global"))["details"]
        assert d["sarma_angle_mode"] == "optimized_global"
        assert d["sarma_start_policy"] == "bisector"
        assert d["sarma_angle_trials"] > 0

    def test_the_notes_of_the_review(self):
        from ogr_slip2d.analysis_runner import sarma_notes
        from types import SimpleNamespace
        notes = sarma_notes(SimpleNamespace(details={
            "sarma_angle_kept": {"objective": "ky", "kept": 0.1,
                                 "optimised": 0.11},
            "sarma_fold_faces": 1, "sarma_angle_mode": "optimized_global",
            "sarma_face_effective": [0.0, -5.0, 3.0, 0.0]},
            fos=1.0, slices=()))
        by = {getattr(n, "code", None): n for n in notes}
        assert by["method.sarma_angles_kept"].args["objective"] == "ky"
        assert by["method.sarma_angles_fold"].args["count"] == 1

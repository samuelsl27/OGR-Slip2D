# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""The prescribed-inclination family inclines each interslice force at the
average of the inclinations of the two slices that share its boundary
(v0.1.223, D222).

INVARIANT PROTECTED
-------------------
Corps of Engineers #2 and Lowe-Karafiath define their inclination per slice;
the force it prescribes acts on a BOUNDARY. Until v0.1.222 the recursion gave
each boundary the angle of the slice on its left in index order -- always
left to right in x, whichever way the mass slides -- which evaluates the
assumption half a slice away from where it is stated ("at each vertical
interslice boundary", USACE 2003, EM 1110-2-1902 Sec. C-4a; Duncan, Wright &
Brandon 2014, Table 6.1 and Fig. 6.14c). The consequences, measured:

* the same problem reflected about a vertical line gave another factor
  (Corps #2 -0.88 %, Lowe-Karafiath -0.10 % with 50 slices);
* the factor converged at first order in the slice width, and missed the
  published values of a given circle.

What is asserted, none of it a snapshot:

* reflection symmetry, to the tolerance of the root: a slope and its mirror
  image give the same factor; with the old rule they do not (rule 7);
* second-order convergence on a ground whose slope varies smoothly
  (y = 10 (1 - cos(pi x / 40)), C1): the observed order over 50, 100 and
  200 slices is 2, and 1 with the old rule; and the old rule's factors,
  extrapolated at first order (Richardson), land where the new ones do --
  the two rules are consistent, the new one is more accurate;
* the external check, verification problem 27 (Malkawi, Hassan & Sarma
  2001), whose given circle the reference program and XSTABL both solve:
  Lowe-Karafiath equals Corps #1 and Corps #2 is 0.003 above it, in both
  programs. The differences cancel what the model shares with the
  published one (Corps #1 does not depend on the rule); the tolerance is
  the rounding of two three-decimal numbers, 0.001. The old rule misses
  Lowe-Karafiath by 0.002;
* Corps #1, whose inclination is one constant, does not move by a bit, and
  the published ratios are the tangents of the inclinations the recursion
  used.

WHAT THIS FILE DISCRIMINATES, MEASURED
--------------------------------------
Against the v0.1.222 tree: see ``_auditoria/P4_0223`` in the verification
bank for the count, recorded when the version was closed.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

FAMILY_VARYING = ("corps_engineers_2", "lowe_karafiath")


def _rule(on):
    """Context: ``modified_swedish.THETA_AT_BOUNDARY`` as asked, put back
    afterwards (the runner has no teardown)."""
    import contextlib

    @contextlib.contextmanager
    def cm():
        from ogr_slip2d.methods import modified_swedish as ms
        old = getattr(ms, "THETA_AT_BOUNDARY", None)
        ms.THETA_AT_BOUNDARY = on
        try:
            yield
        finally:
            if old is None:
                vars(ms).pop("THETA_AT_BOUNDARY", None)
            else:
                ms.THETA_AT_BOUNDARY = old
    return cm()


def _fos(mid, project, surface, n, on=True):
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, surface, num_slices=n)
    with _rule(on):
        res = method_registry()[mid]().compute_fos(project, surface, sl)
    assert res.fos is not None, (mid, res.error_message)
    return res


# ----------------------------------------------------------------------
def _nail_slope(mirror=False):
    """The bare slope and circle of ``test_support_normal_v1137``, or their
    reflection about x = 0: provably the same problem."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipCircle
    from test_support_normal_v1137 import _circle, _project
    p, c = _project(None), _circle()
    if not mirror:
        return p, c
    for b in p.boundaries:
        vs = [Vertex(-v.x, v.y) for v in reversed(b.polyline.vertices)]
        b.polyline = Polyline(vertices=vs, closed=b.polyline.closed)
        if b.polyline.closed:
            b.polyline.ensure_ccw()
    return p, SlipCircle(centre_x=-c.centre_x, centre_y=c.centre_y,
                         radius=c.radius)


class TestAMirrorImageIsTheSameProblem:

    def test_the_two_factors_agree(self):
        for mid in FAMILY_VARYING:
            f = _fos(mid, *_nail_slope(), 50).fos
            fm = _fos(mid, *_nail_slope(True), 50).fos
            assert abs(fm - f) <= 1e-8 * f, (mid, f, fm)

    def test_the_old_rule_told_them_apart(self):
        """Rule 7, at the size the defect was measured: -0.88 % and
        -0.10 %."""
        for mid, gap in (("corps_engineers_2", 5e-3),
                         ("lowe_karafiath", 5e-4)):
            f = _fos(mid, *_nail_slope(), 50, on=False).fos
            fm = _fos(mid, *_nail_slope(True), 50, on=False).fos
            assert abs(fm - f) > gap * f, (mid, f, fm)


# ----------------------------------------------------------------------
def _smooth_ground():
    """A slope whose ground has a continuous inclination: y = 10 (1 - cos(pi
    x / 40)) between x = 0 and 40 (a polyline of 800 sides), flat on both
    sides, c = 5 kPa, phi = 30 deg; the circle (22, 34) R 30 lies across
    it."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_slip2d.surface import SlipCircle
    top = [(-60.0, 0.0)] + [
        (40.0 * i / 800, 10.0 * (1.0 - math.cos(math.pi * i / 800)))
        for i in range(801)] + [(100.0, 20.0)]
    pts = [(-60.0, -30.0)] + top + [(100.0, -30.0)]
    ext = Polyline(vertices=[Vertex(x, y) for x, y in pts], closed=True)
    ext.ensure_ccw()
    p = Project("smooth-ground")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="s", unit_weight=18.0,
                            strength=MohrCoulomb(cohesion=5.0,
                                                 friction_angle=30.0))]
    return p, SlipCircle(centre_x=22.0, centre_y=34.0, radius=30.0)


_ORDER_CACHE: dict = {}


def _ladder(mid, on):
    """F at three slice counts, each twice the last. The old rule's ladder
    starts higher: its first-order term is small against the second-order
    one on this ground, so its observed order only settles past 100 slices
    (measured 0.29, 0.73, 0.88, 0.94, 0.97 from 25 to 1 600 with
    Lowe-Karafiath; the new rule reads 1.98 to 2.00 all along)."""
    key = (mid, on)
    if key not in _ORDER_CACHE:
        p, c = _smooth_ground()
        ns = (50, 100, 200) if on else (100, 200, 400)
        _ORDER_CACHE[key] = [_fos(mid, p, c, n, on).fos for n in ns]
    return _ORDER_CACHE[key]


def _order(f):
    return math.log2(abs((f[0] - f[1]) / (f[1] - f[2])))


class TestTheBoundaryAverageIsSecondOrder:

    def test_observed_order_two(self):
        for mid in FAMILY_VARYING:
            p = _order(_ladder(mid, True))
            assert 1.9 <= p <= 2.1, (mid, p, _ladder(mid, True))

    def test_the_old_rule_was_first_order(self):
        for mid in FAMILY_VARYING:
            p = _order(_ladder(mid, False))
            assert 0.8 <= p <= 1.2, (mid, p, _ladder(mid, False))

    def test_both_rules_converge_to_the_same_factor(self):
        """Richardson: a first-order ladder extrapolates as 2 F(2n) - F(n)
        (the old rule, 200 and 400 slices), a second-order one as
        (4 F(2n) - F(n)) / 3 (the new, 100 and 200). Measured 3e-6 apart,
        against 1e-3 between the raw factors of the two rules at 100
        slices."""
        for mid in FAMILY_VARYING:
            old, new = _ladder(mid, False), _ladder(mid, True)
            f_old = 2.0 * old[2] - old[1]
            f_new = (4.0 * new[2] - new[1]) / 3.0
            assert abs(f_old - f_new) <= 5e-5 * f_new, (mid, f_old, f_new)


# ----------------------------------------------------------------------
def _problem_27():
    """Verification problem 27 (Malkawi, Hassan & Sarma 2001, from the
    XSTABL reference manual): two soils on an undulating rock floor under a
    measured water table with Hu = cos^2, the given circle (59.52, 219.21)
    R 157.68 and 30 slices; imperial units. The model of the verification
    bank, written here because a test does not read the bank."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_slip2d.surface import SlipCircle
    ground = [(0, 68), (22, 67), (38, 63), (63, 73), (101, 88), (138, 103),
              (200, 110)]
    floor = [(200, 76), (161, 58), (133, 56), (113, 64), (94, 65), (78, 56),
             (51, 26), (29, 24), (0, 15)]
    contact = [(101, 88), (200, 99)]
    water = [(0, 68.0), (22, 67.0), (38, 63.0), (63, 73.0), (66, 73.51),
             (73, 74.51), (80, 76.95), (87, 78.46), (94, 79.69),
             (101, 80.87), (108, 82.16), (115, 83.23), (122, 84.17),
             (129, 85.10), (136, 85.85), (143, 86.60), (150, 87.37),
             (157, 87.99), (164, 88.57), (171, 89.23), (178, 90.01),
             (185, 90.62), (192, 91.22), (200, 91.85)]
    p = Project("problem-27")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in
                             ground + [(200, 99)] + floor], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    soil1 = Material(name="Soil 1", unit_weight=116.4, sat_unit_weight=124.2,
                     use_sat_unit_weight=True,
                     strength=MohrCoulomb(cohesion=500.0, friction_angle=14.0),
                     pore_pressure=PorePressureType.WATER_TABLE)
    soil1.auto_hu = True
    soil2 = Material(name="Soil 2", unit_weight=116.4, sat_unit_weight=116.4,
                     use_sat_unit_weight=True,
                     strength=MohrCoulomb(cohesion=0.0, friction_angle=0.0),
                     pore_pressure=PorePressureType.WATER_TABLE)
    soil2.auto_hu = True
    p.materials = [soil1, soil2]
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in contact], closed=False),
        btype=BoundaryType.MATERIAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in water], closed=False),
        btype=BoundaryType.WATER_TABLE))
    for reg in p.resolve_regions():
        cx, cy = reg.centroid()
        mat = soil1
        if cx > 101.0 and cy > 88.0 + 11.0 * (cx - 101.0) / 99.0:
            mat = soil2
        p.assign_material_at(cx, cy, mat.id)
    p.settings.units.system_id = "imperial_psf"
    p.settings.groundwater.pore_fluid_unit_weight = 62.4
    p.settings.groundwater.auto_hu = True
    # Tight, so what is compared is the rule and not where the root stopped
    # (measured: the differences are the same at 1e-4 and at 1e-8).
    p.settings.methods.tolerance = 1e-8
    return p, SlipCircle(centre_x=59.52, centre_y=219.21, radius=157.68)


def _on_problem_27(mid, on=True):
    from ogr_slip2d.analysis_runner import build_method
    from ogr_slip2d.search import GridSearch
    p, c = _problem_27()
    with _rule(on):
        r = GridSearch(method=build_method(p, mid, 30), num_slices=30,
                       min_area=0.0).evaluate_circle(p, c)
    assert r is not None and r.fos is not None, mid
    return r.fos


class TestTheGivenCircleOfProblem27:
    """Published, the reference program / XSTABL: Corps #1 1.411 / 1.413,
    Corps #2 1.414 / 1.416, Lowe-Karafiath 1.411 / 1.413 (Table 27.2)."""

    def test_the_published_differences(self):
        c1 = _on_problem_27("corps_engineers_1")
        assert abs(c1 / 1.411 - 1.0) < 0.02, c1          # guard: the model
        for mid, published in (("corps_engineers_2", 0.003),
                               ("lowe_karafiath", 0.000)):
            got = _on_problem_27(mid) - c1
            assert abs(got - published) <= 0.001, (mid, got, published)

    def test_the_old_rule_missed_lowe_karafiath(self):
        c1 = _on_problem_27("corps_engineers_1", on=False)
        got = _on_problem_27("lowe_karafiath", on=False) - c1
        assert abs(got - 0.000) > 0.001, got


# ----------------------------------------------------------------------
class TestWhatDoesNotMove:

    def test_corps_one_bit_for_bit(self):
        for n in (25, 50):
            on = _fos("corps_engineers_1", *_nail_slope(), n, True)
            off = _fos("corps_engineers_1", *_nail_slope(), n, False)
            assert on.fos == off.fos, n
            assert on.base_normal_force == off.base_normal_force, n

    def test_the_published_ratios_are_the_boundary_inclinations(self):
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.methods.modified_swedish import boundary_theta
        for mid in FAMILY_VARYING:
            res = _fos(mid, *_nail_slope(), 50)
            th = method_registry()[mid]()._theta_angles(res.slices)
            want = [math.tan(t) for t in boundary_theta(th)]
            assert res.details["boundary_ratios"] == want, mid
            # Each interior boundary sits between its two slices.
            for k in range(1, len(th)):
                assert min(th[k - 1], th[k]) <= math.atan(want[k]) + 1e-15
                assert math.atan(want[k]) <= max(th[k - 1], th[k]) + 1e-15

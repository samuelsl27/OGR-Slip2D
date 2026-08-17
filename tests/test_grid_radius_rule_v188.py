# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The Grid Search radius rule, against the reference's own generated radii.

WHAT INVARIANT THIS PROTECTS. Every other numerical test in the suite fixes
a factor of safety on a circle whose geometry is given. This one fixes the
POPULATION: which circles a Grid Search generates at all. A search cannot
find a critical surface it never generated, and for eighty-odd versions this
program did not generate the reference's — its critical radius was simply not
among the eleven sampled at its own critical centre. The factors of safety
were right; the sampling was not, and no method test could see it.

WHERE THE NUMBERS COME FROM. Not from this program's output — from the
reference's. The models in
``referencias/Ejemplos/00_2026_08_17_Test_Regla_radios`` were run for this,
and their ``.s01`` result files list every circle generated at every centre
as ``(r, yleft, x1, y1, x2, y2, yright, fs..., b1)``. So the radii below were
READ, not fitted. That distinction is the whole reason this could be settled:
four fitted numbers can always be made to agree with four parameters, which
is what rule 1 forbids.

The experiment came in pairs — Radius Increment 1 (two circles per centre,
i.e. the bare bracket) and 10 (eleven), on the SAME grid — for two
geometries, one failing left-to-right and one right-to-left. The pair is what
proves the bracket does not depend on the Radius Increment, which no single
run could show.

THE RULE, with ``S`` the ground profile between the Slope Limits and
``P_L``/``P_R`` the two limit points::

    d_min = distance from the centre to the nearest point of S
    d_max = min(|C - P_L|, |C - P_R|)
    delta = 0.05 * (d_max - d_min)
    radii = rinc + 1 equally spaced values over [d_min + delta, d_max - delta]

``d_max >= d_min`` always, because P_L and P_R are points of S. See
``GridSearch._radius_bracket`` for the derivation and
``docs/audits/grid_radius_rule_v188.md`` for the full tables.

Geometry is built in code, not loaded from ``referencias/``: the suite has to
run from a clean checkout, and that directory is not part of it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

# ----------------------------------------------------------------------
# Reference brackets, read from the .s01 of the reference runs.
#
# Ej_1 — Slide2d_Ej_1_General.s01, grid (40,30)-(120,120), 20x20, rinc 10.
# Each entry: centre -> (r_first, r_last) of the eleven circles emitted.
EJ1_BRACKETS = {
    # Perpendicular foot on the 45 deg slope face. This is also the centre
    # of the reference's Ordinary/Janbu-simplified global minimum.
    (84.0, 66.0): (36.3156666795018, 53.6015638426406),
    # The centre of the reference's Bishop global minimum. Its 5th radius,
    # 47.2124436, is the one the old rule could not reach.
    (88.0, 70.5): (42.0787585213113, 54.9129713154809),
    # Directly above the right Slope Limit (120, 25): d_min == d_max, so the
    # reference emits eleven IDENTICAL circles rather than none. The
    # population has to stay 4851 whatever the geometry does.
    (120.0, 30.0): (5.0, 5.0),
    # High above the crest: d_max is the LEFT limit here, not the right one.
    (40.0, 120.0): (70.5311288741493, 80.0914486088362),
}

# The one centre where the reference disagrees with the rule, and by how
# much: (52, 48) lies exactly ON the slope face (52 + 48 = 100), so d_min is
# 0 and the reference's own nearest-point search loses a little precision.
# 1.5e-8 relative. Kept as a test rather than hidden, so that if the
# implementation ever drifts by more than that it is not mistaken for this.
EJ1_ON_THE_FACE = ((52.0, 48.0), (2.60192240629104, 49.4365249608866))

# Ej_2 — Slide2d_Ej_2_General.s01, grid (-40,35)-(70,135), 21x19, rinc 10.
EJ2_BRACKETS = {
    # The centre of the reference's Bishop global minimum. Its 4th radius,
    # 60.2564659, is the other one the old rule could not reach.
    (-3.33333333333334, 87.6315789473684): (54.7373610642169,
                                            73.1343773134626),
    # Nearest point of the profile is the VERTEX (40, 55), not the foot of
    # any perpendicular. A rule measuring distances to vertices only, or one
    # measuring them to segments without clamping, both get this wrong.
    (12.3809523809524, 87.6315789473684): (44.8596742644165,
                                           82.8192351658443),
    (-3.33333333333334, 61.3157894736842): (32.5600073167778,
                                            54.9559284924622),
    # Centre of the reference's Ordinary/Janbu-simplified global minimum;
    # its 2nd radius is 30.4081979.
    (12.3809523809524, 61.3157894736842): (26.2857835957567,
                                           67.5099266382109),
}

# The two reference global-minimum radii, from the "Global Minimum FS" block
# of each .s01. These are the numbers that were missing from the population.
EJ1_CRITICAL = ((88.0, 70.5), 47.2124436389792)
EJ2_CRITICAL = ((-3.33333333333334, 87.6315789473684), 60.2564659389906)


# ----------------------------------------------------------------------
def _ej1_external():
    """Ej_1's external boundary. Ground profile: (0,50) (50,50) (75,25)
    (120,25) — a 45 deg face between crest and toe, with a footing."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.project import Project
    ext = Polyline(vertices=[
        Vertex(120, 0), Vertex(120, 25), Vertex(75, 25), Vertex(50, 50),
        Vertex(0, 50), Vertex(0, 30), Vertex(0, 20), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("ej1-geometry")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    return p


def _ej2_external():
    """Ej_2's external boundary. Its bottom edge carries a vertex at (0,0),
    which is why the profile must come from the upper envelope."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.project import Project
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(100, 0), Vertex(100, 70), Vertex(70, 70),
        Vertex(55, 55), Vertex(40, 55), Vertex(15, 30), Vertex(-50, 30),
        Vertex(-50, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("ej2-geometry")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    return p


def _searcher(project=None, **kw):
    """A GridSearch configured only enough to ask it for brackets."""
    from ogr_slip2d import BishopSimplified
    from ogr_slip2d.search import GridSearch
    kw.setdefault("min_radius", 0.0)
    return GridSearch(method=BishopSimplified(), **kw)


def _bracket(project, xc, yc, **kw):
    gs = _searcher(**kw)
    return gs._radius_bracket(xc, yc, gs._slope_surface(project))


def _radii(project, xc, yc, rinc, **kw):
    lo, hi = _bracket(project, xc, yc, **kw)
    return [lo + (hi - lo) * k / rinc for k in range(rinc + 1)]


# ----------------------------------------------------------------------
class TestBracketMatchesTheReference:
    """The bracket, centre by centre, against radii the reference printed."""

    # Absolute agreement observed across all 881 centres of the two
    # reference grids is 7.5e-13; 1e-9 leaves three orders of margin
    # without letting a real change through.
    TOL = 1e-9

    def test_ej1_brackets(self):
        p = _ej1_external()
        for (xc, yc), (lo_ref, hi_ref) in EJ1_BRACKETS.items():
            lo, hi = _bracket(p, xc, yc)
            assert abs(lo - lo_ref) < self.TOL, \
                f"Ej_1 ({xc},{yc}) r_min {lo!r} vs reference {lo_ref!r}"
            assert abs(hi - hi_ref) < self.TOL, \
                f"Ej_1 ({xc},{yc}) r_max {hi!r} vs reference {hi_ref!r}"

    def test_ej2_brackets(self):
        p = _ej2_external()
        for (xc, yc), (lo_ref, hi_ref) in EJ2_BRACKETS.items():
            lo, hi = _bracket(p, xc, yc)
            assert abs(lo - lo_ref) < self.TOL, \
                f"Ej_2 ({xc},{yc}) r_min {lo!r} vs reference {lo_ref!r}"
            assert abs(hi - hi_ref) < self.TOL, \
                f"Ej_2 ({xc},{yc}) r_max {hi!r} vs reference {hi_ref!r}"

    def test_degenerate_centre_yields_a_zero_width_bracket(self):
        """Above a Slope Limit, d_min == d_max. The reference emits eleven
        identical circles there; returning nothing would move the
        denominator, which is what v0.1.83 fixed."""
        p = _ej1_external()
        lo, hi = _bracket(p, 120.0, 30.0)
        assert abs(lo - 5.0) < self.TOL, lo
        assert abs(hi - 5.0) < self.TOL, hi

    def test_centre_lying_on_the_slope_face(self):
        """d_min = 0 exactly. Held to 1e-7 relative, not 1e-9: this is the
        single centre of 881 where the reference's own numerics differ from
        the rule, by 1.5e-8 relative."""
        (xc, yc), (lo_ref, hi_ref) = EJ1_ON_THE_FACE
        lo, hi = _bracket(_ej1_external(), xc, yc)
        assert abs(lo - lo_ref) / lo_ref < 1e-7, (lo, lo_ref)
        assert abs(hi - hi_ref) / hi_ref < 1e-7, (hi, hi_ref)

    def test_nearest_point_can_be_a_vertex(self):
        """Ej_2 (12.381, 87.632): the closest point of the profile is the
        vertex (40, 55). Distances to segment interiors alone would put
        d_min elsewhere and the whole bracket with it."""
        import math
        p = _ej2_external()
        xc, yc = 12.3809523809524, 87.6315789473684
        gs = _searcher()
        d_min = gs._distance_to_surface(xc, yc, gs._slope_surface(p))
        assert abs(d_min - math.hypot(xc - 40.0, yc - 55.0)) < 1e-12, d_min


class TestTheCriticalRadiiAreGenerated:
    """The point of the whole change: the reference's own global-minimum
    radius has to be IN the sampled set. Neither was, before v0.1.88."""

    def test_ej1_critical_radius_is_sampled(self):
        (xc, yc), r_ref = EJ1_CRITICAL
        radii = _radii(_ej1_external(), xc, yc, 10)
        best = min(radii, key=lambda r: abs(r - r_ref))
        assert abs(best - r_ref) / r_ref < 1e-9, \
            f"reference R={r_ref} not generated; closest is {best}"

    def test_ej2_critical_radius_is_sampled(self):
        (xc, yc), r_ref = EJ2_CRITICAL
        radii = _radii(_ej2_external(), xc, yc, 10)
        best = min(radii, key=lambda r: abs(r - r_ref))
        assert abs(best - r_ref) / r_ref < 1e-9, \
            f"reference R={r_ref} not generated; closest is {best}"

    def test_every_reference_radius_of_the_critical_centres(self):
        """Not just the critical one — all eleven, in order, at both
        critical centres. A rule that hit one radius by luck would fail
        this."""
        cases = [
            (_ej1_external(), (88.0, 70.5), [
                42.0787585213113, 43.3621798, 44.6456011, 45.9290224,
                47.2124436389792, 48.4958649, 49.7792862, 51.0627075,
                52.3461288, 53.6295500, 54.9129713154809]),
            (_ej2_external(), (-3.33333333333334, 87.6315789473684), [
                54.7373610642169, 56.5770627, 58.4167643,
                60.2564659389906, 62.0961676, 63.9358692, 65.7755708,
                67.6152724, 69.4549741, 71.2946757, 73.1343773134626]),
        ]
        for p, (xc, yc), refs in cases:
            radii = _radii(p, xc, yc, 10)
            assert len(radii) == len(refs)
            for k, (got, ref) in enumerate(zip(radii, refs)):
                assert abs(got - ref) < 1e-6, (xc, yc, k, got, ref)


class TestTheBracketDoesNotDependOnTheRadiusIncrement:
    """What the A1/A2 and B1/B2 pairs were run to establish: with Radius
    Increment 1 the reference emits exactly two circles, and they are the
    same two numbers as the ends of the eleven it emits with 10. So the 5 %
    inset is a constant of the rule, not a function of how many circles
    were asked for — which is the one thing a single run cannot tell you."""

    def test_bracket_is_identical_for_rinc_1_and_10(self):
        for p, centres in ((_ej1_external(), EJ1_BRACKETS),
                           (_ej2_external(), EJ2_BRACKETS)):
            for xc, yc in centres:
                a = _bracket(p, xc, yc, radius_increment=1)
                b = _bracket(p, xc, yc, radius_increment=10)
                assert a == b, (xc, yc, a, b)

    def test_rinc_1_reproduces_the_reference_two_circles(self):
        """A1's centre (84, 66) with Radius Increment 1: the reference emits
        36.3156667 and 53.6015638, which are the ends of its eleven."""
        radii = _radii(_ej1_external(), 84.0, 66.0, 1)
        assert len(radii) == 2
        assert abs(radii[0] - 36.3156666795018) < 1e-9, radii
        assert abs(radii[1] - 53.6015638426406) < 1e-9, radii

    def test_radii_are_equally_spaced(self):
        radii = _radii(_ej2_external(), -3.33333333333334,
                       87.6315789473684, 10)
        steps = [b - a for a, b in zip(radii[:-1], radii[1:])]
        assert max(steps) - min(steps) < 1e-9, steps


class TestPopulationIsExact:
    """(X intervals + 1)(Y intervals + 1)(Radius Increment + 1), documented
    by the reference. v0.1.83 made the counter honest; this keeps the
    generator honest, which is the other half. The grid below is placed on
    purpose over the right Slope Limit, so three of its nine centres are the
    degenerate d_min == d_max case that an earlier draft dropped silently —
    Ej_1's whole x = 120 column, 4851 circles down to 4620."""

    @staticmethod
    def _one_material_ej1():
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        p = _ej1_external()
        m = Material(name="S", unit_weight=20,
                     strength=MohrCoulomb(cohesion=15, friction_angle=25))
        p.materials = [m]
        return p

    def test_total_equals_the_documented_identity(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        nx, ny, rinc = 2, 2, 4
        r = GridSearch(method=BishopSimplified(), grid_x=(112.0, 120.0),
                       grid_y=(30.0, 48.0), grid_nx=nx, grid_ny=ny,
                       radius_increment=rinc, min_radius=0.0,
                       num_slices=12, min_area=0.5).run(
                           self._one_material_ej1())
        assert r.total_count == (nx + 1) * (ny + 1) * (rinc + 1), \
            (r.total_count, r.valid_count, r.invalid_count)

    def test_degenerate_centres_are_in_that_grid(self):
        """Guards the test above: if the grid ever stopped straddling the
        limit, it would pass without exercising the case it exists for."""
        p = _ej1_external()
        degenerate = [(x, y) for x in (112.0, 116.0, 120.0)
                      for y in (30.0, 39.0, 48.0)
                      if abs(_bracket(p, x, y)[1]
                             - _bracket(p, x, y)[0]) < 1e-12]
        assert len(degenerate) == 3, degenerate


class TestSlopeLimitsAreHonoured:
    """The clip has to interpolate the limit abscissae, because the bracket
    is measured TO the limit points. Filtering vertices by x — what this did
    before v0.1.88 — drops the segment a limit cuts through, so a limit
    between two vertices produced no point and both ends of the bracket were
    measured to the wrong place.

    These are analytic identities on Ej_1's profile, not captured output:
    the face runs (50,50) to (75,25), dropping 1 in 1, so ground at x = 60 is
    exactly y = 40, and the bench beyond the toe is flat at y = 25."""

    def test_clip_creates_the_limit_points(self):
        gs = _searcher(slope_limits=(60.0, 100.0))
        pts = gs._slope_surface(_ej1_external())
        assert abs(pts[0].x - 60.0) < 1e-9 and abs(pts[0].y - 40.0) < 1e-9, \
            (pts[0].x, pts[0].y)
        assert abs(pts[-1].x - 100.0) < 1e-9 and abs(pts[-1].y - 25.0) < 1e-9, \
            (pts[-1].x, pts[-1].y)

    def test_narrowing_the_limits_moves_the_bracket(self):
        """Rule 7: a control that changes nothing is worse than no control.
        Narrowing the limits brings the nearer limit point closer, so r_max
        must come down."""
        p = _ej1_external()
        wide = _bracket(p, 88.0, 70.5)
        narrow = _bracket(p, 88.0, 70.5, slope_limits=(60.0, 100.0))
        assert narrow[1] < wide[1], (wide, narrow)

    def test_no_limits_means_the_whole_profile(self):
        gs = _searcher()
        pts = gs._slope_surface(_ej1_external())
        assert abs(pts[0].x - 0.0) < 1e-9, pts[0].x
        assert abs(pts[-1].x - 120.0) < 1e-9, pts[-1].x


class TestMinRadiusStillDoesSomething:
    """``min_radius`` has no counterpart in the reference, which is why its
    default is now 0 — the out-of-the-box sampling has to be the
    reference's. But it is still an option, and rule 7 says an option that
    moves no number should not exist. It acts as a floor on d_min."""

    def test_raising_min_radius_raises_r_min(self):
        p = _ej1_external()
        lo0, hi0 = _bracket(p, 120.0, 45.0, min_radius=0.0)
        lo1, hi1 = _bracket(p, 120.0, 45.0, min_radius=25.0)
        assert lo1 > lo0, (lo0, lo1)
        assert abs(lo1 - 25.0) < 1e-9, lo1

    def test_default_is_zero_so_the_reference_is_reproduced(self):
        """The default matters: with the old 2.0, Ej_1's centre (52, 48)
        — the one lying on the face, d_min = 0 — sampled from 4.5 instead of
        the reference's 2.6."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        assert GridSearch(method=BishopSimplified()).min_radius == 0.0

    def test_min_radius_never_inverts_the_bracket(self):
        """A floor above d_max would otherwise produce r_max < r_min."""
        p = _ej1_external()
        lo, hi = _bracket(p, 120.0, 30.0, min_radius=500.0)
        assert lo <= hi, (lo, hi)

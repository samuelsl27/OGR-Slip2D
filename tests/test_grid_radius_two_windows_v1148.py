# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The Grid Search radius bracket with TWO Slope Limit windows, against the
reference's own generated radii on a tiered wall.

WHAT INVARIANT THIS PROTECTS. ``tests/test_grid_radius_rule_v188.py`` pins
the bracket a Grid Search samples at each centre with ONE window. This file
pins the bracket with TWO — the exit-window / entry-window declaration of
defect D50 — which the reference generates by a different rule altogether.
Until v0.1.148 this engine generated from the hull of the two windows, and on
the reference bank's eight tiered walls (verification problems 87-94) that
stopped every centre left of the toe at the model's corner: the published
critical circle of problem 87, radius 18.547 from (-5.713, 20.432), sat 3 m
above anything the grid could produce there. Defect D77.

WHERE THE NUMBERS COME FROM. Five models of that wall were run in the
reference program on 2026-09-06 (``referencias/Ejemplos/
00_2026_09_06_Test_Muro_D77``, models A-E). Their ``.s01`` files list every
circle generated at every centre, so every bracket below was READ, not
fitted. Model A (Radius Increment 1, 440 centres) gives the bare bracket; B
repeats A's ends with Increment 10; C is the bank's own grid (342 centres,
Increment 60); E is the same wall with ONE window, and it is what proves the
one-window rule needs no change: 440 centres at 9e-14 with vertical faces.

THE RULE (``GridSearch._radius_bracket_two_windows``): the range of radii
whose circle enters the soil inside window 1 and leaves it inside window 2,
each window's surface being the profile segments overlapping it (a limit
mid-segment takes the segment whole) without the gap between them; a 0.1 %
relative margin at an end fixed by a profile corner, none at an end fixed by
a limit point; ``rinc + 1`` equally spaced radii in between.

The four readings discarded on the way — hull, "last radius with two
crossings", 5 % inset, bench-touching segments — are in
``docs/audits/grid_radius_two_windows_v1148.md`` with the centre that
killed each. Geometry is built in code: ``referencias/`` is not part of the
repository.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

# ----------------------------------------------------------------------
# The wall of verification problem 87 (Leshchinsky and Han 2004, baseline):
# foundation surface y = 6, three 3 m tiers with vertical faces at x = 6,
# 7.2 and 8.4, crest y = 15, model from x = 0 to 24. Problem 94 has five
# 1.8 m tiers set back 0.6 m; problem 91 extends the model to x = -2.
# ----------------------------------------------------------------------
X_TOE, Y_FOUND, Y_CREST, X_RIGHT = 6.0, 6.0, 15.0, 24.0
EXIT_WINDOW = (0.0, 6.5)      # the figures' inner marker, on the lower bench
ENTRY_WINDOW = (8.4, 24.0)    # from the crest vertex to the model's end


def _wall_profile(n_tiers=3, setback=1.2, x_left=0.0):
    h = (Y_CREST - Y_FOUND) / n_tiers
    faces = [X_TOE + i * setback for i in range(n_tiers)]
    pts = [(x_left, 0.0), (X_RIGHT, 0.0), (X_RIGHT, Y_CREST)]
    for i in reversed(range(n_tiers)):
        pts.append((faces[i], Y_FOUND + (i + 1) * h))
        pts.append((faces[i], Y_FOUND + i * h))
    pts.append((x_left, Y_FOUND))
    return pts


def _wall_project(n_tiers=3, setback=1.2, x_left=0.0, with_material=False):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.project import Project
    ext = Polyline(vertices=[Vertex(x, y) for x, y in
                             _wall_profile(n_tiers, setback, x_left)],
                   closed=True)
    ext.ensure_ccw()
    p = Project("tiered-wall")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    if with_material:
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        p.materials = [Material(name="fill", unit_weight=18,
                                strength=MohrCoulomb(cohesion=0,
                                                     friction_angle=34))]
    return p


def _searcher(**kw):
    from ogr_slip2d import BishopSimplified
    from ogr_slip2d.search import GridSearch
    kw.setdefault("min_radius", 0.0)
    return GridSearch(method=BishopSimplified(), **kw)


def _bracket(project, xc, yc, **kw):
    gs = _searcher(**kw)
    return gs._radius_bracket(xc, yc, gs._slope_surface(project))


TWO = (EXIT_WINDOW, ENTRY_WINDOW)
ONE = (0.0, 24.0)

# ----------------------------------------------------------------------
# Read from Problema_87_A.s01 (Radius Increment 1: the two radii ARE the
# bracket). Grid corner at the published centre of problem 87.
A_BRACKETS = {
    # The published centre. The engine emitted [15.142, 15.502] here until
    # v0.1.148; the published radius 18.547 is inside this one.
    (-5.713, 20.432): (17.2635848774869, 18.568424394412),
    (-5.713, 24.0): (19.8123560407027, 21.4539609735911),
    (-1.713, 20.432): (14.5104330575691, 16.3474069744101),
    (-1.713, 24.0): (17.4657022927671, 19.5633272157976),
    # r_min is 1.001 x |C - (7.2, 9)| although a smaller circle already
    # daylights on the bench in front of the wall: the constraint is the
    # concave corner at the end of the exit bench, and the margin is 0.1 %.
    (-3.23680952380952, 23.8122105263158): (18.1379590689851,
                                             20.0446678600171),
}

# Read from Problema_87_C.s01 (the bank's grid, Radius Increment 60).
C_BRACKETS = {
    # r_min fixed by the corner (7.2, 9) even though the arc then crosses
    # the second bench at y = 12 on its way to the crest: the gap between
    # the windows is not part of either surface.
    (-24.0, 22.2941176470588): (33.9481230897296, 34.1052552967233),
    # r_max is EXACTLY |C - (24, 15)|: an end fixed by a limit point
    # carries no margin.
    (0.555555555555554, 40.5294117647059): (32.2541468861376,
                                            34.6611142400319),
    # r_min is EXACTLY |C - (8.4, 15)|: the crest crossing reaching the
    # entry window's edge, again without margin.
    (-8.88888888888889, 15.0): (17.2888888888889, 17.3802749402879),
    (-12.6666666666667, 46.0): (42.0382394614448, 44.0970464317056),
    (-7.0, 31.4117647058824): (26.5581579849487, 28.5154183671567),
    # The two margins cross here, and the reference repeats r_min.
    (-20.2222222222222, 18.6470588235294): (29.0987104288951,
                                            29.0987104288951),
}

# Read from Problema_87_E.s01: the same wall with ONE window.
E_BRACKETS = {
    (-5.713, 20.432): (15.1422487674981, 15.5016624184891),
    (-1.713, 24.0): (13.7650022963078, 17.8541515681188),
}

# The published critical circles (figures 87.2, 91.2 and 94.2 of the
# reference manual), each with its own wall.
PUBLISHED = [
    # problem, tiers, setback, x_left, exit window, centre, radius
    (87, 3, 1.2, 0.0, (0.0, 6.5), (-5.713, 20.432), 18.547),
    (91, 3, 1.2, -2.0, (-2.0, 6.5), (4.658, 15.000), 10.934),
    (94, 5, 0.6, 0.0, (0.0, 6.4), (-5.537, 20.452), 18.450),
]


# ----------------------------------------------------------------------
class TestTwoWindowsMatchTheReference:
    """Centre by centre, against radii the reference printed."""

    # Agreement observed over 440 + 301 centres is 5e-10 at worst (the
    # collapsed brackets), 9e-14 elsewhere.
    TOL = 1e-8

    def test_model_a_the_bare_bracket(self):
        p = _wall_project()
        for (xc, yc), (lo_ref, hi_ref) in A_BRACKETS.items():
            lo, hi = _bracket(p, xc, yc, slope_limits=TWO)
            assert abs(lo - lo_ref) < self.TOL, (xc, yc, lo, lo_ref)
            assert abs(hi - hi_ref) < self.TOL, (xc, yc, hi, hi_ref)

    def test_model_c_the_bank_grid(self):
        p = _wall_project()
        for (xc, yc), (lo_ref, hi_ref) in C_BRACKETS.items():
            lo, hi = _bracket(p, xc, yc, slope_limits=TWO)
            assert abs(lo - lo_ref) < self.TOL, (xc, yc, lo, lo_ref)
            assert abs(hi - hi_ref) < self.TOL, (xc, yc, hi, hi_ref)

    def test_the_published_radius_of_87_is_now_generated(self):
        """The point of the change. Until v0.1.148 the bracket at this
        centre was [15.142, 15.502]; the published radius is 18.547."""
        lo, hi = _bracket(_wall_project(), -5.713, 20.432, slope_limits=TWO)
        assert lo <= 18.547 <= hi, (lo, hi)
        assert hi > 18.0, hi

    def test_the_bracket_does_not_depend_on_the_radius_increment(self):
        """Model B (Increment 10) repeats model A's ends to 9e-14."""
        p = _wall_project()
        for xc, yc in A_BRACKETS:
            a = _bracket(p, xc, yc, slope_limits=TWO, radius_increment=1)
            b = _bracket(p, xc, yc, slope_limits=TWO, radius_increment=10)
            assert a == b, (xc, yc, a, b)


class TestOneWindowIsUntouched:
    """Model E: the same wall, vertical faces and all, with ONE window.
    The reference reproduces the v0.1.88 rule at 9e-14 over 440 centres,
    which is what the docstring of that rule said was still unmeasured."""

    def test_model_e_matches_the_v188_rule(self):
        p = _wall_project()
        for (xc, yc), (lo_ref, hi_ref) in E_BRACKETS.items():
            lo, hi = _bracket(p, xc, yc, slope_limits=ONE)
            assert abs(lo - lo_ref) < 1e-9, (xc, yc, lo, lo_ref)
            assert abs(hi - hi_ref) < 1e-9, (xc, yc, hi, hi_ref)

    def test_one_window_is_the_old_arithmetic_exactly(self):
        """Not merely close: the one-window branch is the same code path,
        so the bracket is d_min + 5 % .. d_max - 5 % to the last bit."""
        p = _wall_project()
        gs = _searcher(slope_limits=ONE)
        pts = gs._slope_surface(p)
        xc, yc = -5.713, 20.432
        d_min = gs._distance_to_surface(xc, yc, pts)
        d_max = min(math.hypot(xc - pts[0].x, yc - pts[0].y),
                    math.hypot(xc - pts[-1].x, yc - pts[-1].y))
        delta = gs.RADIUS_INSET * (d_max - d_min)
        assert gs._radius_bracket(xc, yc, pts) == (d_min + delta,
                                                   d_max - delta)

    def test_declaring_the_second_window_moves_the_bracket(self):
        """Rule 7. With one window the toe circle is unreachable from
        the published centre; declaring the second window reaches it."""
        p = _wall_project()
        one = _bracket(p, -5.713, 20.432, slope_limits=ONE)
        two = _bracket(p, -5.713, 20.432, slope_limits=TWO)
        assert two[1] - one[1] > 3.0, (one, two)


class TestThePublishedCirclesFitTheirCentres:
    """The eight walls' published circles all lie inside the bracket the
    reference generates at their own centre (problem 90's radius IS the
    last one). Three of the eight are pinned here, one per geometry."""

    def test_87_91_and_94(self):
        for n, tiers, setback, x_left, exit_w, (xc, yc), r_pub in PUBLISHED:
            p = _wall_project(tiers, setback, x_left)
            lo, hi = _bracket(p, xc, yc, slope_limits=(exit_w, ENTRY_WINDOW))
            assert lo - 1e-9 <= r_pub <= hi + 1e-9, (n, lo, hi, r_pub)


class TestCentresWithNoValidRadius:
    """Far left and low, no circle can leave through the exit window and
    enter through the crest. The reference still emits rinc + 1 circles
    there — 61 at each of 40 such centres of the bank grid — and not one
    of them resolves (0 valid of 2440). The engine has to keep the
    population identity the same way: a degenerate bracket whose circle
    the slicer rejects, never a missing centre."""

    def test_the_bracket_is_degenerate(self):
        lo, hi = _bracket(_wall_project(), -24.0, 15.0, slope_limits=TWO)
        assert lo == hi, (lo, hi)
        assert lo > 0.0

    def test_population_is_exact_and_nothing_is_valid(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        nx, ny, rinc = 2, 2, 2
        r = GridSearch(method=BishopSimplified(), grid_x=(-24.0, -22.1),
                       grid_y=(15.0, 16.8), grid_nx=nx, grid_ny=ny,
                       radius_increment=rinc, min_radius=0.0,
                       num_slices=12, min_area=2.0, slope_limits=TWO).run(
                           _wall_project(with_material=True))
        assert r.total_count == (nx + 1) * (ny + 1) * (rinc + 1), \
            (r.total_count, r.valid_count, r.invalid_count)
        assert r.valid_count == 0, r.valid_count


class TestTheWindowSurfaces:
    """The two clauses of ``_window_segments`` that the data decided."""

    def test_a_limit_mid_segment_takes_the_segment_whole(self):
        """The exit limit at x = 6.5 sits on the bench (6, 9)-(7.2, 9):
        the bench belongs to the exit surface out to (7.2, 9). That corner
        is what fixes r_min at every centre of model A."""
        from ogr_slip2d.search import GridSearch
        gs = _searcher(slope_limits=TWO)
        pts = gs._slope_surface(_wall_project())
        segs = GridSearch._window_segments(pts, 0.0, 6.5, 1e-9)
        ends = {(round(s[2], 6), round(s[3], 6)) for s in segs}
        assert (7.2, 9.0) in ends, ends

    def test_the_gap_and_the_windows_edge_face_are_left_out(self):
        """Neither the face at x = 7.2 nor the bench at y = 12 belongs to
        any window, and the face at x = 8.4 — standing ON the entry
        window's edge — does not either. Model C's (-24, 22.29) and
        (-8.889, 15) are the centres that decide both."""
        from ogr_slip2d.search import GridSearch
        gs = _searcher(slope_limits=TWO)
        pts = gs._slope_surface(_wall_project())
        exit_segs = GridSearch._window_segments(pts, 0.0, 6.5, 1e-9)
        entry_segs = GridSearch._window_segments(pts, 8.4, 24.0, 1e-9)
        xs = {(s[0], s[2]) for s in exit_segs + entry_segs}
        assert (7.2, 7.2) not in xs, xs          # the face at x = 7.2
        assert (7.2, 8.4) not in xs, xs          # the bench at y = 12
        assert (8.4, 8.4) not in xs, xs          # the face at x = 8.4
        assert (8.4, 24.0) in xs, xs             # the crest itself

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
ACADS 1(a) — the first PUBLISHED reference in the suite, and the first
validation of a **search** rather than of a method.

Source
------
Giam, S.K. & Donald, I.B. (1989). *Example problems for testing soil
slope stability programs.* Civil Engineering Research Report No. 8/1989,
Monash University. Problem **1(a)**: a homogeneous slope, total stress,
no pore pressures. Thirty-three programs solved it independently.

    Referee factor of safety                    1.00
    Mean of 33 programs                         0.991      <- used here
    Mean Bishop of 18 programs                  0.993

The mean of the 33 is the expected value, for two reasons. It is the
number with statistical backing rather than one arbiter's opinion on a
problem with no known exact answer; and it enshrines **no single
program**, which a validation case that copies a competitor's output
would. The tolerance is 2 % because the source is not more precise than
that: the referee value and the mean differ by 0.9 % from each other.

Why this file exists
--------------------
Every other numerical case in the suite fixes a **method**, by evaluating
a circle whose geometry is already known. None of them fixes the
**search**, which is the part that has to find that circle.

Slope Search in particular had no external reference at all. Until
v0.1.77 it could not even be run from the interface (it raised on every
call); v0.1.77 fixed the wiring and said so plainly: "that it returns a
number does not say the number is right." This is that check. It turns
out to be right — 0.9868 against a published 0.991 — but "turns out to
be" is precisely what a test is for.

Geometry and properties are taken from the problem statement **in text**.
No coordinate here is read off a figure, which is also why the layered
ACADS variants 1(c) and 1(d) are not in this file: their material
boundaries exist only as a drawing.

Cost note: the grid below is the one the problem specifies (20x20
intervals, 11 circles per point = 4851 surfaces) and is shared by every
test in the file, because re-running it per test would be the single
most expensive thing in the suite for no added coverage.
"""
from __future__ import annotations


# ======================================================================
# The model
# ======================================================================
def _acads_1a():
    """ACADS problem 1(a).

    External boundary and soil properties verbatim from the statement:
    base at elevation 20, crest at 35, slope face from (30,25) to
    (50,35) — 10 m high at 1:2, beta = 26.57 deg.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(20, 20), Vertex(70, 20), Vertex(70, 35),
        Vertex(50, 35), Vertex(30, 25), Vertex(20, 25),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("ACADS 1(a)")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="Soil", unit_weight=20.0,
        strength=MohrCoulomb(cohesion=3.0, friction_angle=19.6))]
    return p


# The published consensus and its tolerance, in one place.
_MEAN_33 = 0.991
_TOL = 0.02

# The search grid of the problem statement.
_GRID = dict(grid_x=(22.8, 43.7), grid_y=(42.3, 62.6),
             grid_nx=21, grid_ny=21,        # 20 x 20 intervals
             radius_increment=11,           # 11 circles per grid point
             min_radius=3.0, num_slices=25, min_area=0.5)

_CACHE: dict = {}


def _grid_result():
    """The reference grid search, run once for the whole file."""
    if "grid" not in _CACHE:
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch
        _CACHE["grid"] = GridSearch(method=BishopSimplified(),
                                    **_GRID).run(_acads_1a())
    return _CACHE["grid"]


def _slope_result(seed: int = 42, n: int = 1500):
    key = ("slope", seed, n)
    if key not in _CACHE:
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import SlopeSearch
        _CACHE[key] = SlopeSearch(method=BishopSimplified(), num_surfaces=n,
                                  num_slices=25, seed=seed).run(_acads_1a())
    return _CACHE[key]


# ======================================================================
class TestTheModelIsWhatTheProblemDescribes:
    def test_single_homogeneous_region(self):
        assert len(_acads_1a().resolve_regions()) == 1

    def test_slope_face_is_ten_metres_at_one_in_two(self):
        """A geometry typo would make every number below meaningless
        while still looking like a slope."""
        import math
        p = _acads_1a()
        ys = [v.y for v in p.external_boundary().polyline.vertices]
        assert min(ys) == 20 and max(ys) == 35
        beta = math.degrees(math.atan2(35 - 25, 50 - 30))
        assert abs(beta - 26.565) < 0.01, beta


class TestGridSearchFindsThePublishedMinimum:
    def test_bishop_matches_the_mean_of_33_programs(self):
        r = _grid_result()
        assert r.critical is not None
        err = abs(r.critical.fos - _MEAN_33) / _MEAN_33
        assert err < _TOL, f"FoS={r.critical.fos:.4f} err={err * 100:.2f}%"

    def test_the_critical_circle_daylights_on_the_slope(self):
        """A factor of safety on a circle that misses the slope would be
        arithmetic, not a slope stability result."""
        c = _grid_result().critical.surface
        assert 20.0 <= c.centre_x <= 50.0, c.centre_x
        assert 42.0 <= c.centre_y <= 63.0, c.centre_y
        assert c.radius > 10.0, c.radius


class TestEveryMethodOnTheCriticalCircle:
    """All seven methods on the circle the grid search found.

    Published per-method values (the reference program's own minima):
    Bishop 0.987, Spencer 0.986, GLE 0.986, Janbu corrected 0.990.

    Read this for what it is. Each published number is that method's own
    global minimum, while these are evaluated on **Bishop's** minimum, so
    a rigorous method can only come out at or above its own optimum. The
    bias is upward and small, and the tolerance is set to swallow it. It
    is a cross-check on method agreement, not the validation — the
    validation is the search tests above and below, against 0.991.
    """

    _REF = [
        ("bishop_simplified", 0.987, 1.0),
        ("spencer", 0.986, 1.0),
        ("gle_morgenstern_price", 0.986, 1.0),
        ("janbu_corrected", 0.990, 1.0),
    ]

    @staticmethod
    def _method(mid):
        import ogr_slip2d as M
        return {
            "ordinary_fellenius": M.OrdinaryFellenius,
            "bishop_simplified": M.BishopSimplified,
            "janbu_simplified": M.JanbuSimplified,
            "janbu_corrected": M.JanbuCorrected,
            "spencer": M.Spencer,
            "gle_morgenstern_price": M.GLEMorgensternPrice,
            "lowe_karafiath": M.LoweKarafiath,
        }[mid]()

    def _evaluate(self, mid):
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        c = _grid_result().critical.surface
        ev = GridSearch(method=self._method(mid), num_slices=25, min_area=0.0)
        return ev.evaluate_circle(
            _acads_1a(),
            SlipCircle(centre_x=c.centre_x, centre_y=c.centre_y,
                       radius=c.radius))

    def test_rigorous_methods_agree_with_the_published_values(self):
        for mid, ref, tol in self._REF:
            res = self._evaluate(mid)
            assert res is not None, mid
            err = abs(res.fos - ref) / ref * 100
            assert err < tol, f"{mid}: FS={res.fos:.4f} err={err:.2f}%"

    def test_all_seven_methods_converge_on_this_circle(self):
        """Including Lowe-Karafiath, which v0.1.78 finally made reachable
        from Project Settings. The problem publishes no value for it, so
        this asserts convergence and a physical result, not a number."""
        for mid in ("ordinary_fellenius", "bishop_simplified",
                    "janbu_simplified", "janbu_corrected", "spencer",
                    "gle_morgenstern_price", "lowe_karafiath"):
            res = self._evaluate(mid)
            assert res is not None and res.converged, mid
            assert 0.90 < res.fos < 1.05, f"{mid}: {res.fos:.4f}"

    def test_the_simplified_methods_sit_below_the_rigorous_ones(self):
        """Fellenius and Janbu simplified neglect forces the rigorous
        methods carry, and on a circular surface that is known to make
        them conservative. If one ever came out above Bishop, something
        is wrong with the method and not with the reference."""
        bishop = self._evaluate("bishop_simplified").fos
        for mid in ("ordinary_fellenius", "janbu_simplified"):
            assert self._evaluate(mid).fos < bishop, mid


# ======================================================================
class TestSlopeSearchAgainstThePublishedValue:
    """The point of the version.

    Slope Search has existed since v0.1.17, was fixed in v0.1.24 (the
    inverted sign on the Initial Angle at Toe upper limit), and could not
    be launched from the interface at all until v0.1.77. Through all of
    that, nothing compared its answer to anything outside this codebase.
    """

    def test_it_matches_the_mean_of_33_programs(self):
        r = _slope_result()
        assert r.critical is not None
        err = abs(r.critical.fos - _MEAN_33) / _MEAN_33
        assert err < _TOL, f"FoS={r.critical.fos:.4f} err={err * 100:.2f}%"

    def test_it_is_at_least_as_critical_as_the_grid(self):
        """The defining property of a directed search: it may beat the
        grid, it must not lose to it. Here it does beat it — 0.9868
        against 0.9895 — because the grid can only place centres on its
        own lattice."""
        slope = _slope_result().critical.fos
        grid = _grid_result().critical.fos
        assert slope <= grid * 1.005, (slope, grid)

    def test_the_answer_does_not_depend_on_the_seed(self):
        """A random search that only reaches the published value with a
        lucky seed has not been validated, it has been sampled. Three
        seeds, each independently within tolerance."""
        for seed in (7, 42, 123):
            fos = _slope_result(seed=seed).critical.fos
            err = abs(fos - _MEAN_33) / _MEAN_33
            assert err < _TOL, f"seed {seed}: FoS={fos:.4f} err={err*100:.2f}%"

    def test_the_same_seed_gives_the_same_answer(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import SlopeSearch
        p = _acads_1a()
        kw = dict(method=BishopSimplified(), num_surfaces=400,
                  num_slices=20, seed=5)
        a = SlopeSearch(**kw).run(p)
        b = SlopeSearch(**kw).run(p)
        assert abs(a.critical.fos - b.critical.fos) < 1e-12


class TestWhatNumberOfSurfacesActuallyMeans:
    """Reported, not changed (rule 6).

    ``SlopeSearch(num_surfaces=1500)`` returns ``valid_count`` around
    1900. That is not a miscount: the generation loop runs exactly
    ``num_surfaces`` times, and the local refinement stage that follows
    adds up to 8 x 120 further evaluations, all of them counted as valid.

    So "Number of Surfaces" means **surfaces generated** here, while in
    ``PathSearch`` it means surfaces *accepted* — that search keeps
    generating until the requested count of valid ones is reached, and
    ``test_slide_validation_ej1.py`` pins that meaning explicitly.
    ``attempts`` compounds it: PathSearch reports it, SlopeSearch leaves
    it at zero.

    Two searches, two meanings for the same setting, and nothing in the
    interface distinguishes them. These tests fix the CURRENT behaviour
    so that whichever way it is later reconciled is a deliberate change
    with a visible diff — they are not an endorsement of it.
    """

    def test_valid_count_exceeds_the_requested_number(self):
        r = _slope_result(seed=42, n=1500)
        assert r.valid_count > 1500, r.valid_count

    def test_the_refinement_stage_is_what_adds_them(self):
        """Scaling the request does not scale the surplus proportionally:
        the refinement contribution is capped at 8 circles x 120 steps,
        independent of ``num_surfaces``."""
        small = _slope_result(seed=42, n=400)
        big = _slope_result(seed=42, n=1500)
        assert small.valid_count - 400 <= 8 * 120
        assert big.valid_count - 1500 <= 8 * 120

    def test_attempts_is_not_reported(self):
        """PathSearch fills this in and SlopeSearch does not, so a caller
        reading it gets 0 rather than a count."""
        assert _slope_result().attempts == 0

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.129 — a focus object must narrow EVERY search, not one.

**The invariant**: a focus object is drawn on the model and saved in the
.ogr, so it is a property of the PROJECT. Every search must therefore
honour it, and the surface the search returns must satisfy it. Rule 7,
and here the setting is not a number of vertices — it is the restriction
that says WHICH CASE is being analysed.

What it protects, and it was real (defect D33). ``build_search`` handed
``focus_objects`` to the Grid Search branch alone. Two of the other six
searches declared the argument, stored it under a comment claiming it was
"applied BEFORE evaluation", and never read the attribute again; the
other four did not declare it, and ``**legacy_kwargs`` would have
swallowed it in silence had anyone passed one. So a focus on a model that
did not use a Grid Search did nothing whatsoever.

What that cost in the reference bank: ten non-circular models whose two
published cases differ ONLY by their focus object were the same
calculation twice. Problem 78, cases 1a (the surface passes through the
toe) and 1b (it is tangent to the bottom of the foundation), both
returned 0.9275 in the search and 0.9137 optimised, to the sixth decimal
— and the comparativa published one of them OK and the other REVISAR out
of that single number.

Why the surface predicate had to be DEFINED and not merely translated.
The reference documents focus objects for the Grid Search and the Slope
Search, both circular, and defines all four kinds as rules for generating
the circle RADII at a slip centre. It never applies one to a non-circular
search, so it never says what tangency to a polyline is. Point, line and
window translate with nothing decided; TANGENT is our reading, and
``TestTangencyIsNotCrossing`` below is the whole of it: a circle is
tangent to a line when it touches without crossing, so a surface is taken
as tangent when it reaches the line to within the tolerance and does not
pass through to the other side.

Note this is NOT ``min_elevation`` restated. That filter says how deep a
surface MAY go; the tangent focus says it must actually GET there. A
shallow surface passes the filter and fails the focus, and that
difference is the two cases of problem 78.
"""
from __future__ import annotations


# ----------------------------------------------------------------------
def _layered_slope(name: str = "d33"):
    """The four-layer slope of ``test_search_inequality_v1118``.

    Reused rather than reinvented: it is already known to give every one
    of the seven searches something to find, which is what a test that
    walks all seven needs. Two of its four layers have no cohesion, so
    there ARE deep mechanisms for a low tangent focus to select.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    p = Project(name)
    ext = Polyline(vertices=[
        Vertex(0, -20), Vertex(130, -20), Vertex(130, 10),
        Vertex(85, 40), Vertex(60, 40), Vertex(25, 10), Vertex(0, 10),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    for y in (10.0, 5.0, -5.0):
        p.add_boundary(Boundary(polyline=Polyline(vertices=[
            Vertex(0, y), Vertex(130, y)], closed=False),
            btype=BoundaryType.MATERIAL))

    sup = Material(name="Upper", unit_weight=20.38,
                   strength=MohrCoulomb(cohesion=49.0, friction_angle=29.0))
    l2 = Material(name="L2", unit_weight=17.64,
                  strength=MohrCoulomb(cohesion=0.0, friction_angle=30.0))
    l3 = Material(name="L3", unit_weight=20.38,
                  strength=MohrCoulomb(cohesion=7.84, friction_angle=20.0))
    inf = Material(name="Bottom", unit_weight=17.64,
                   strength=MohrCoulomb(cohesion=0.0, friction_angle=30.0))
    p.materials = [sup, l2, l3, inf]
    p.resolve_regions()
    p.assign_material_at(70.0, 25.0, sup.id)
    p.assign_material_at(65.0, 7.5, l2.id)
    p.assign_material_at(65.0, 0.0, l3.id)
    p.assign_material_at(65.0, -10.0, inf.id)

    p.settings.methods.num_slices = 15
    p.settings.statistics.seed = 20260829
    return p


def _method():
    from ogr_slip2d import BishopSimplified
    return BishopSimplified()


def _deep_tangent(tolerance: float = 2.0):
    """Tangent to the third material boundary, y = -5.

    A horizontal line well below the toe (y = 10), so it selects the deep
    mechanisms and rejects the shallow face slides — which is exactly what
    case (b) of verification problem 78 asks for, and why every tangent
    focus in the reference bank is a horizontal line at the base of a
    stratum.
    """
    from ogr_slip2d.focus import FocusKind, FocusObject
    return FocusObject(kind=FocusKind.TANGENT,
                       points=[(0.0, -5.0), (130.0, -5.0)],
                       tolerance=tolerance)


def _surface_points(result):
    """The critical surface's ``(x, y)``, or None when it is a circle."""
    surf = result.critical.surface
    poly = getattr(surf, "polyline", None)
    if poly is not None:
        return [(v.x, v.y) for v in poly.vertices]
    return None


def _satisfies(focus, result) -> bool:
    """Whether the critical surface satisfies the focus.

    Asks the predicate that matches what the search generated, which is
    the same choice ``BaseSearch._focus_rejects`` makes.
    """
    from ogr_slip2d.focus import accepts, accepts_surface

    pts = _surface_points(result)
    if pts is not None:
        return accepts_surface([focus], pts)
    c = result.critical.surface
    return accepts([focus], c.centre_x, c.centre_y, c.radius)


# ======================================================================
class TestTheSurfacePredicate:
    """The geometry, against cases computable by hand.

    A horizontal focus line at y = 0 and three surfaces: one that dips to
    y = 0.4 (touches, within a tolerance of 1), one that dips to y = -2
    (crosses) and one that stays at y = 3 (never arrives).
    """

    TOUCHES = [(0, 5), (3, 0.5), (6, 0.4), (10, 5)]
    CROSSES = [(0, 5), (3, -2.0), (6, -1.5), (10, 5)]
    STAYS_UP = [(0, 5), (3, 3.0), (6, 3.2), (10, 5)]

    def _fo(self, kind, points, tol=1.0):
        from ogr_slip2d.focus import FocusKind, FocusObject
        return FocusObject(kind=FocusKind(kind), points=points,
                           tolerance=tol)

    def test_a_point_is_captured_within_the_tolerance(self):
        near = self._fo("point", [(5.0, 0.0)])
        assert near.accepts_surface(self.TOUCHES)
        assert not near.accepts_surface(self.STAYS_UP)

    def test_the_point_tolerance_widens_the_capture(self):
        """Rule 7 for the tolerance itself: it has to decide something."""
        tight = self._fo("point", [(5.0, 0.0)], tol=0.1)
        loose = self._fo("point", [(5.0, 0.0)], tol=4.0)
        assert not tight.accepts_surface(self.STAYS_UP)
        assert loose.accepts_surface(self.STAYS_UP)

    def test_a_line_has_to_be_crossed(self):
        """Crossing, not passing near: the surface must cut the segment."""
        cut = self._fo("line", [(5.0, -3.0), (5.0, 3.0)])
        assert cut.accepts_surface(self.TOUCHES)
        missed = self._fo("line", [(5.0, -3.0), (5.0, -1.0)])
        assert not missed.accepts_surface(self.TOUCHES)

    def test_a_window_has_to_be_entered(self):
        win = self._fo("window", [(2.0, -1.0), (7.0, -1.0),
                                  (7.0, 1.0), (2.0, 1.0)])
        assert win.accepts_surface(self.TOUCHES)
        assert not win.accepts_surface(self.STAYS_UP)

    def test_a_window_crossed_without_a_vertex_inside_still_counts(self):
        """The two halves of the window test are both needed.

        This surface has no vertex inside the window and goes straight
        through it, so a vertices-only test would miss it.
        """
        win = self._fo("window", [(4.0, -6.0), (6.0, -6.0),
                                  (6.0, -2.0), (4.0, -2.0)])
        through = [(0.0, 5.0), (5.0, -8.0), (10.0, 5.0)]
        assert not any(-6.0 <= y <= -2.0 and 4.0 <= x <= 6.0
                       for (x, y) in through)          # no vertex inside
        # it enters through the left edge at (4, -5.4) and leaves through
        # the bottom, so only the edge-crossing half of the test sees it
        assert win.accepts_surface(through)

    def test_a_malformed_or_disabled_object_filters_nothing(self):
        """Same contract as ``accepts_circle``: it must not reject all.

        A focus with too few points is a half-drawn object, and silently
        rejecting every surface would report "no mechanism found" for what
        is really an unfinished drawing.
        """
        half_drawn = self._fo("tangent", [(0.0, 0.0)])
        assert not half_drawn.valid
        assert half_drawn.accepts_surface(self.STAYS_UP)
        off = self._fo("tangent", [(0.0, 0.0), (10.0, 0.0)])
        off.enabled = False
        assert off.accepts_surface(self.STAYS_UP)

    def test_objects_combine_with_and(self):
        """Adding one must NARROW, which is what focusing means."""
        from ogr_slip2d.focus import accepts_surface

        tan = self._fo("tangent", [(0.0, 0.0), (10.0, 0.0)])
        far = self._fo("point", [(50.0, 50.0)])
        assert accepts_surface([tan], self.TOUCHES)
        assert not accepts_surface([tan, far], self.TOUCHES)
        assert accepts_surface([], self.STAYS_UP)


class TestTangencyIsNotCrossing:
    """The one definition this version had to make, isolated.

    For a circle, tangent means touching the line without crossing it.
    Carried over: a surface is tangent when it reaches the infinite line
    to within the tolerance AND does not pass to the other side. Both
    halves are load-bearing — drop the first and every shallow surface
    qualifies, drop the second and a tangent focus becomes a line focus.
    """

    def _tan(self, tol=1.0):
        from ogr_slip2d.focus import FocusKind, FocusObject
        return FocusObject(kind=FocusKind.TANGENT,
                           points=[(0.0, 0.0), (10.0, 0.0)],
                           tolerance=tol)

    def test_touching_is_accepted(self):
        assert self._tan().accepts_surface(
            [(0, 5), (3, 0.5), (6, 0.4), (10, 5)])

    def test_crossing_is_rejected(self):
        assert not self._tan().accepts_surface(
            [(0, 5), (3, -2.0), (6, -1.5), (10, 5)])

    def test_not_arriving_is_rejected(self):
        assert not self._tan().accepts_surface(
            [(0, 5), (3, 3.0), (6, 3.2), (10, 5)])

    def test_it_is_the_infinite_line_not_the_drawn_segment(self):
        """As in ``accepts_circle``, and for the same reason: a surface
        tangent to the plane of a weak layer beyond the drawn extent is
        still tangent to that plane."""
        from ogr_slip2d.focus import FocusKind, FocusObject
        stub = FocusObject(kind=FocusKind.TANGENT,
                           points=[(0.0, 0.0), (1.0, 0.0)], tolerance=1.0)
        far_away = [(50, 5), (53, 0.5), (56, 0.4), (60, 5)]
        assert stub.accepts_surface(far_away)

    def test_it_is_not_minimum_elevation_restated(self):
        """The distinction that makes problem 78 have two cases.

        ``min_elevation`` bounds how deep a surface MAY go; the tangent
        focus demands it GET there. A shallow surface satisfies the first
        and fails the second, and that is the whole difference between
        case (a) and case (b).
        """
        shallow = [(0, 5), (3, 3.0), (6, 3.2), (10, 5)]
        assert min(y for _, y in shallow) > 0.0      # clears any floor
        assert not self._tan().accepts_surface(shallow)


# ======================================================================
class TestEverySearchHonoursTheFocus:
    """Rule 7, one per branch of ``build_search``.

    Two assertions per search, and the second is the one that matters:
    that the number MOVED says the argument arrived, that the returned
    surface SATISFIES the focus says it arrived as a focus and not as
    some other perturbation.
    """

    def _pair(self, cls, focus=None, **kw):
        """The same search with and without the focus, same seed.

        ``focus`` defaults to the deep tangent, but two searches get one
        of their own and the reason is measured, not stylistic — see
        ``TestGuidedSearchesCanBeCutOffByTheirFocus``.
        """
        p = _layered_slope()
        focus = focus if focus is not None else _deep_tangent()
        base = dict(method=_method(), num_slices=15, **kw)
        free = cls(**base).run(p)
        held = cls(focus_objects=[focus], **base).run(p)
        return focus, free, held

    def _assert_honoured(self, focus, free, held, label):
        assert free.critical is not None, "%s found nothing unfocused" % label
        assert held.critical is not None, "%s found nothing focused" % label
        assert abs(held.min_fos - free.min_fos) > 1e-9, label
        assert _satisfies(focus, held), label

    def test_grid_search(self):
        from ogr_slip2d.search import GridSearch
        self._assert_honoured(*self._pair(
            GridSearch, grid_nx=8, grid_ny=8, radius_increment=8), "grid")

    def test_slope_search(self):
        from ogr_slip2d.search import SlopeSearch
        self._assert_honoured(*self._pair(
            SlopeSearch, num_surfaces=250, seed=5), "slope")

    def test_auto_refine_search(self):
        from ogr_slip2d.search import AutoRefineSearch
        self._assert_honoured(*self._pair(
            AutoRefineSearch, divisions=8, circles_per_division=6,
            iterations=3), "auto_refine")

    def test_auto_refine_non_circular_search(self):
        """The non-circular variant asks about the CIRCLE it generated,
        before converting it to chords — see ``_focus_rejects``."""
        from ogr_slip2d.search import AutoRefineNonCircularSearch
        self._assert_honoured(*self._pair(
            AutoRefineNonCircularSearch, num_vertices=8, divisions=8,
            circles_per_division=6, iterations=3), "auto_refine_nc")

    def test_block_search(self):
        from ogr_slip2d.search import BlockSearch
        self._assert_honoured(*self._pair(
            BlockSearch, num_groups=3, num_surfaces=400, seed=5), "block")

    def test_path_search(self):
        from ogr_slip2d.search import PathSearch
        self._assert_honoured(*self._pair(
            PathSearch, num_surfaces=250, seed=5), "path")

    def test_simulated_annealing_search(self):
        """A WINDOW focus, not the deep tangent the others get, and the
        reason is measured: see
        ``TestGuidedSearchesCanBeCutOffByTheirFocus``. The annealing walks
        from candidate to candidate, so a focus its walk cannot reach cuts
        the walk instead of narrowing it."""
        from ogr_slip2d.focus import FocusKind, FocusObject
        from ogr_slip2d.search import SimulatedAnnealingSearch
        window = FocusObject(kind=FocusKind.WINDOW,
                             points=[(40.0, -2.0), (80.0, -2.0),
                                     (80.0, 6.0), (40.0, 6.0)])
        self._assert_honoured(*self._pair(
            SimulatedAnnealingSearch, focus=window, initial_vertices=6,
            generation_steps=25, seed=5), "simulated_annealing")

    def test_particle_swarm_search(self):
        """The same tangent, at a tolerance the swarm can reach.

        Its particles are circles built from a toe point, a tangent angle
        and a crest point, and that parametrisation simply cannot place a
        circle tangent to y = -5 to within 2 m on this model — at that
        tolerance the swarm returns nothing at all. Measured, and pinned
        in ``TestGuidedSearchesCanBeCutOffByTheirFocus``.
        """
        from ogr_slip2d.particle_swarm import ParticleSwarmSearch
        self._assert_honoured(*self._pair(
            ParticleSwarmSearch, focus=_deep_tangent(5.0),
            num_particles=12, num_iterations=8, seed=5), "particle_swarm")


class TestTheFocusDecidesWhichCase:
    """The closure criterion of D33, in miniature.

    Two focus objects on ONE model — a point high on the slope and a
    tangent to the deep boundary — must produce two DIFFERENT answers
    from a non-circular search. That is what verification problem 78 asks
    of cases (a) and (b), and until v0.1.129 it was the same calculation
    twice.
    """

    def test_two_focus_objects_give_two_different_analyses(self):
        from ogr_slip2d.focus import FocusKind, FocusObject
        from ogr_slip2d.search import PathSearch

        p = _layered_slope()
        shallow = FocusObject(kind=FocusKind.POINT, points=[(30.0, 12.0)],
                              tolerance=3.0)
        deep = _deep_tangent()
        kw = dict(method=_method(), num_slices=15, num_surfaces=250, seed=5)
        a = PathSearch(focus_objects=[shallow], **kw).run(p)
        b = PathSearch(focus_objects=[deep], **kw).run(p)
        assert a.critical is not None and b.critical is not None
        assert abs(a.min_fos - b.min_fos) > 1e-9
        # and each one where its own focus put it
        assert _satisfies(shallow, a)
        assert _satisfies(deep, b)
        y_a = min(y for _, y in _surface_points(a))
        y_b = min(y for _, y in _surface_points(b))
        assert y_b < y_a, (y_a, y_b)


class TestGuidedSearchesCanBeCutOffByTheirFocus:
    """A measured limitation, pinned rather than papered over.

    The five searches that draw independent candidates — Grid, Slope,
    Auto Refine, Block, Path — lose YIELD to a focus and nothing else:
    fewer surfaces survive, and the ones that do are the focused ones.
    The two GUIDED searches do not behave that way. Simulated Annealing
    walks from candidate to candidate, and the Particle Swarm steers
    particles towards the best one found; a focus filters the path as
    well as the destination, so a focus the walk cannot reach cuts the
    walk off instead of narrowing it.

    Measured on the model above, tangent to y = -5, Simulated Annealing
    with 6 vertices and 25 generation steps:

        tolerance   2    5   10   12   14   20
        valid       0    0    0   71   71   71
        minimum     -    -    -  1.3427 (the UNFOCUSED answer)

    There is no middle. Below 12 it returns nothing; at 12 and above the
    focus accepts everything the walk produces and stops deciding. The
    cause is the bootstrap: it builds a starting bowl from a DEPTH and
    SHRINKS that depth on each retry (``_bootstrap_parameters``), so a
    rejection walks it AWAY from a deep tangent rather than towards it.

    This is reported, not fixed. Making the bootstrap aim at the focus
    would be steering generation, which is a different design from the
    filter this version implements, and it would change the sampling
    distribution of a stochastic search — something to decide with
    measurements in hand, not on the way past.

    The Particle Swarm has the milder version of the same thing: its
    particles are circles built from a toe point, a tangent angle and a
    crest point, and that parametrisation cannot place a circle tangent
    to y = -5 within 2 m of this model. Widen the tolerance to 5 and it
    works and narrows properly.
    """

    def _sa(self, focus, **kw):
        from ogr_slip2d.search import SimulatedAnnealingSearch
        return SimulatedAnnealingSearch(
            method=_method(), num_slices=15, initial_vertices=6,
            generation_steps=25, seed=5, focus_objects=focus, **kw
        ).run(_layered_slope())

    def test_the_annealing_returns_nothing_for_a_focus_it_admits(self):
        """The discriminating measurement, and it is not a tolerance
        being too tight: the surface the UNFOCUSED search returns
        satisfies this very focus, and the focused search still finds
        nothing. So a satisfying surface demonstrably exists and the walk
        cannot reach it."""
        from ogr_slip2d.focus import accepts_surface

        free = self._sa([])
        assert free.critical is not None
        pts = [(v.x, v.y) for v in free.critical.surface.polyline.vertices]
        reachable = _deep_tangent(10.0)
        assert accepts_surface([reachable], pts),             "the premise of this test: the unfocused answer satisfies it"

        held = self._sa([reachable])
        assert held.critical is None, (
            "if this now finds something, the bootstrap has been taught "
            "to aim at the focus and this finding is closed — update the "
            "docstring rather than deleting the test")
        assert held.valid_count == 0

    def test_a_focus_the_walk_can_reach_narrows_it_properly(self):
        """The other half, so the finding above is not read as "focus and
        annealing do not mix". A window over the region the walk already
        explores both survives and decides."""
        from ogr_slip2d.focus import FocusKind, FocusObject

        window = FocusObject(kind=FocusKind.WINDOW,
                             points=[(40.0, -2.0), (80.0, -2.0),
                                     (80.0, 6.0), (40.0, 6.0)])
        free = self._sa([])
        held = self._sa([window])
        assert held.critical is not None
        assert held.valid_count > 0
        assert abs(held.min_fos - free.min_fos) > 1e-9
        assert _satisfies(window, held)

    def test_the_swarm_narrows_once_its_parametrisation_can_reach(self):
        from ogr_slip2d.particle_swarm import ParticleSwarmSearch

        kw = dict(method=_method(), num_slices=15, num_particles=12,
                  num_iterations=8, seed=5)
        p = _layered_slope()
        free = ParticleSwarmSearch(**kw).run(p)
        tight = ParticleSwarmSearch(
            focus_objects=[_deep_tangent(2.0)], **kw).run(p)
        wide = ParticleSwarmSearch(
            focus_objects=[_deep_tangent(5.0)], **kw).run(p)
        assert tight.critical is None          # cannot be reached at all
        assert wide.critical is not None
        assert abs(wide.min_fos - free.min_fos) > 1e-9
        assert _satisfies(_deep_tangent(5.0), wide)


class TestOptimiseSurfacesStaysInsideTheFocus:
    """The last door, and the one that would have undone all the rest.

    ``optimize_surface`` evaluates its candidate steps by calling
    ``evaluate_surface`` DIRECTLY on the search object, so it bypassed
    every filter the search applies before evaluating. That matters more
    here than anywhere else: the reference optimises every non-circular
    result it publishes, so the OPTIMISED surface is the one a bank row
    compares against the manual. A walk free to wander off the focus
    would hand back a surface belonging to a different case than the one
    the model declares — defect D33 coming back through the back door
    after being shut at the front.
    """

    def _run(self, focus):
        from ogr_slip2d.optimize import OptimizeSettings
        from ogr_slip2d.search import PathSearch
        return PathSearch(
            method=_method(), num_slices=15, num_surfaces=250, seed=5,
            focus_objects=focus,
            optimize=OptimizeSettings(enabled=True), optimize_seed=5,
        ).run(_layered_slope())

    def test_the_optimised_surface_still_satisfies_the_focus(self):
        window = self._window()
        held = self._run([window])
        assert held.critical is not None
        assert _satisfies(window, held),             "the optimisation walked the surface out of its focus"

    def test_the_optimisation_still_does_something(self):
        """Rule 7 for the guard itself: refusing the steps that leave the
        focus must not amount to refusing every step, or the fix above
        would have quietly turned the optimisation off."""
        window = self._window()
        held = self._run([window])
        free = self._run([])
        assert held.critical is not None and free.critical is not None
        assert abs(held.min_fos - free.min_fos) > 1e-9

    @staticmethod
    def _window():
        from ogr_slip2d.focus import FocusKind, FocusObject
        return FocusObject(kind=FocusKind.WINDOW,
                           points=[(40.0, -2.0), (80.0, -2.0),
                                   (80.0, 6.0), (40.0, 6.0)])


class TestBuildSearchHandsTheFocusToEverySearch:
    """The wiring, which is where the defect actually lived.

    ``focus_objects`` travels in ``common`` and through ``_base_kwargs``
    for the same reason the Surface Filters (v0.1.102), the Slope Limits
    (v0.1.118) and the seismic modes (v0.1.127) do: the seven branches
    below are exactly where one of them gets forgotten.
    """

    METHODS = ("grid", "slope", "auto_refine", "block", "path",
               "simulated_annealing", "particle_swarm")

    def _project_with_a_focus(self):
        from ogr_slip2d.focus import FocusKind, FocusObject
        p = _layered_slope()
        p.focus_objects.append(FocusObject(
            kind=FocusKind.TANGENT, points=[(0.0, -5.0), (130.0, -5.0)],
            tolerance=2.0))
        return p

    def test_every_branch_receives_it(self):
        from ogr_slip2d.analysis_runner import build_search

        p = self._project_with_a_focus()
        for m in self.METHODS:
            p.settings.search.search_method = m
            s = build_search(p, "bishop_simplified")
            assert s is not None, m
            assert len(s.focus_objects) == 1, m

    def test_a_disabled_object_is_not_handed_over(self):
        from ogr_slip2d.analysis_runner import build_search

        p = self._project_with_a_focus()
        p.focus_objects[0].enabled = False
        for m in self.METHODS:
            p.settings.search.search_method = m
            assert build_search(p, "bishop_simplified").focus_objects == [], m

    def test_a_malformed_object_is_not_handed_over(self):
        from ogr_slip2d.analysis_runner import build_search

        p = self._project_with_a_focus()
        p.focus_objects[0].points = [(0.0, -5.0)]      # a tangent needs two
        for m in self.METHODS:
            p.settings.search.search_method = m
            assert build_search(p, "bishop_simplified").focus_objects == [], m

    def test_no_focus_costs_nothing(self):
        """An empty list must be indistinguishable from the feature not
        existing, or every model without a focus pays for it."""
        from ogr_slip2d.analysis_runner import build_search

        p = _layered_slope()
        for m in self.METHODS:
            p.settings.search.search_method = m
            s = build_search(p, "bishop_simplified")
            assert s.focus_objects == [], m
            assert s._focus_rejects_circle(65.0, 40.0, 30.0) is False, m


class TestMinimumAreaReachesEverySearch:
    """Defect D51, and it is the same shape as D33 in a different filter.

    ``min_area`` was handed out by hand in six of the seven branches, and
    the seventh — ``path`` — did not pass it, so ``PathSearch`` pinned it
    at 1.0 whatever the project declared. What that cost on verification
    problem 86: Spencer 1.1728 (-26.4 %) on a 2.41 ft2 skin against
    1.5841 (-0.62 %) on the 201.95 ft2 mechanism the manual publishes.
    """

    METHODS = TestBuildSearchHandsTheFocusToEverySearch.METHODS

    def test_a_declared_value_reaches_every_branch(self):
        from ogr_slip2d.analysis_runner import build_search

        p = _layered_slope()
        p.settings.search.min_area = 50.0
        for m in self.METHODS:
            p.settings.search.search_method = m
            assert build_search(p, "bishop_simplified").min_area == 50.0, m

    def test_an_undeclared_value_keeps_each_branch_its_own_fallback(self):
        """Not a detail: 76 models of the reference bank leave the field
        empty and ride on whichever fallback their branch has. Collapsing
        the seven to one number would move published rows for a reason
        that has nothing to do with the defect being closed."""
        from ogr_slip2d.analysis_runner import build_search

        expected = {"grid": 1.0, "slope": 1.0, "auto_refine": 0.5,
                    "block": 2.0, "path": 1.0, "simulated_annealing": 1.0,
                    "particle_swarm": 1.0}
        p = _layered_slope()
        p.settings.search.min_area = None
        for m in self.METHODS:
            p.settings.search.search_method = m
            got = build_search(p, "bishop_simplified").min_area
            assert got == expected[m], (m, got, expected[m])

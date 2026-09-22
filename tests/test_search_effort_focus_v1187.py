# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""What a search EFFORT is, now that every search publishes it (D160).

THE INVARIANT THIS FILE PROTECTS is that the effort of a run is a number
the run states, not one a reader infers. Before v0.1.187 two things were
missing and the second hid the first:

  * ``attempts`` was filled by Path Search and Auto Refine and left at 0
    by the other five, so a caller reading it could not tell "it tried
    nothing" from "this search does not say";
  * a candidate removed by a FOCUS OBJECT left every loop without
    touching any counter at all, so the work it cost was invisible.

D160 asked whether Path Search should stop counting in VALID surfaces.
The answer, with the bank census in front, is no: the semantics are the
reference's, documented since v0.1.24, and three assertions of
``test_search_effort_v1103.py`` fix them. What the census DID show is
that the rows which die at the attempt ceiling are exactly the ones with
a focus object — and that in nineteen of them the real effort cannot be
recovered from what is archived, because ``generadas`` is
``valid + invalid`` and a focus rejection is neither.

WHY THESE ARE IDENTITIES AND NOT SNAPSHOTS. Every assertion here is a
relation between numbers the same run produces, so none of them can be
satisfied by recording whatever the code happens to print today:

    Grid      attempts == (nx+1)(ny+1)(rinc+1)     the documented population
    Block     attempts == num_surfaces             a fixed generation budget
    any       attempts - total_count == focus_rejected  where nothing else
                                                        skips silently
    no focus  focus_rejected == 0

THE ONE THAT IS NOT ARITHMETIC is ``TestAWalkIsNotPopulation``. The
obvious place to increment the counter is inside ``_focus_rejects``
itself, and it is wrong: ``optimize.py`` reaches that method through
``getattr(evaluator, "_focus_rejects", None)``, so the rejections of the
optimisation WALK would be added to the population of the SEARCH. The
test runs the same search twice, with the optimisation on and off, and
demands the counter not move.
"""
NX = NY = 4
RINC = 6
SEMILLA = 10116


# ----------------------------------------------------------------------
def _slope():
    """A simple slope, built in code — the suite runs from a clone."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, 12.0),
        Vertex(50, 12.0), Vertex(30, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("effort-and-focus")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="Soil", unit_weight=18,
                            strength=MohrCoulomb(cohesion=8,
                                                 friction_angle=20))]
    return p


def _tangent(y=-4.0, tolerance=0.5):
    """A horizontal tangent focus below the toe.

    Below the toe rather than through it because that is the shape every
    tangent focus of the reference bank has — the base of a stratum — and
    because it has to reject a worthwhile share of what is generated for
    the subtraction to be measuring anything.
    """
    from ogr_slip2d.focus import FocusKind, FocusObject
    return FocusObject(kind=FocusKind.TANGENT,
                       points=[(0.0, y), (60.0, y)], tolerance=tolerance)


def _grid(project, **kw):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.search import GridSearch
    xs = [v.x for v in project.boundaries[0].polyline.vertices]
    ys = [v.y for v in project.boundaries[0].polyline.vertices]
    kw.setdefault("method", method_registry()["bishop_simplified"]())
    return GridSearch(grid_x_min=min(xs) + 10, grid_x_max=max(xs) - 10,
                      grid_y_min=max(ys), grid_y_max=max(ys) + 25,
                      grid_nx=NX, grid_ny=NY, radius_increment=RINC,
                      num_slices=12, **kw)


def _path(project, **kw):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.search import PathSearch
    kw.setdefault("method", method_registry()["bishop_simplified"]())
    kw.setdefault("num_surfaces", 25)
    return PathSearch(num_vertices=6, num_slices=12, seed=SEMILLA, **kw)


def _block(project, **kw):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.search import BlockSearch
    kw.setdefault("method", method_registry()["bishop_simplified"]())
    kw.setdefault("num_surfaces", 40)
    return BlockSearch(num_slices=12, seed=SEMILLA, **kw)


POBLACION_GRID = (NX + 1) * (NY + 1) * (RINC + 1)


# ======================================================================
class TestTheGridPopulationIsAnIdentity:
    """``attempts`` is the documented population, focus or no focus."""

    def test_attempts_is_the_documented_population(self):
        p = _slope()
        r = _grid(p).run(p)
        assert r.attempts == POBLACION_GRID, (r.attempts, POBLACION_GRID)

    def test_without_a_focus_nothing_is_rejected_for_focus(self):
        p = _slope()
        r = _grid(p).run(p)
        assert r.focus_rejected == 0
        assert r.attempts == r.total_count, (r.attempts, r.total_count)

    def test_a_focus_removes_candidates_without_shrinking_the_population(self):
        """The two halves of what a focus does, one assertion each.

        The population is a property of the GRID and may not move when the
        user narrows what is considered — that is the whole of the
        exception ``_run_centres`` documents. What moves is how many of
        them were analysed, and the difference now has a name.
        """
        p = _slope()
        r = _grid(p, focus_objects=[_tangent()]).run(p)
        assert r.attempts == POBLACION_GRID, r.attempts
        assert r.focus_rejected > 0, "the focus rejected nothing: no measure"
        assert r.attempts - r.total_count == r.focus_rejected, (
            r.attempts, r.total_count, r.focus_rejected)


# ======================================================================
class TestPathSearchSubtractionNowHasAName:
    """What D160 asked for, in the search D160 is about."""

    def test_without_a_focus_every_attempt_is_accounted_for(self):
        p = _slope()
        r = _path(p).run(p)
        assert r.focus_rejected == 0
        assert r.attempts == r.total_count, (r.attempts, r.total_count)

    def test_with_a_focus_the_difference_is_the_counter(self):
        """The invariant that makes the published number checkable.

        Every other exit of ``PathSearch._run`` touches ``valid_count`` or
        ``invalid_count``; the focus rejection is the only one that does
        not. So the subtraction is exact, and a future skip added without
        a counter would break this rather than pass unnoticed.
        """
        p = _slope()
        r = _path(p, focus_objects=[_tangent()]).run(p)
        assert r.focus_rejected > 0, "the focus rejected nothing: no measure"
        assert r.attempts - r.total_count == r.focus_rejected, (
            r.attempts, r.total_count, r.focus_rejected)

    def test_the_budget_still_counts_valid_surfaces(self):
        """D160 was REPORTED and not reconciled, and this says so.

        Publishing the effort does not change what "Number of Surfaces"
        means. If someone later makes Path Search stop at a generation
        count, this test is the one that has to be rewritten on purpose.
        """
        p = _slope()
        r = _path(p, num_surfaces=25).run(p)
        assert r.valid_count == 25, r.valid_count
        assert r.attempts > r.valid_count, (r.attempts, r.valid_count)


# ======================================================================
class TestBlockSearchIsAFixedGenerationBudget:
    """The shape D160 weighed for Path Search, which already exists here."""

    def test_attempts_is_exactly_the_request(self):
        p = _slope()
        r = _block(p, num_surfaces=40).run(p)
        assert r.attempts == 40, r.attempts

    def test_and_a_focus_does_not_change_it(self):
        """The property that makes a generation budget a generation budget.

        Block Search costs the same however many candidates are rejected,
        which is exactly what Path Search does not do. Having both in the
        suite is what turns "two semantics" from a sentence into a
        measurement.
        """
        p = _slope()
        r = _block(p, num_surfaces=40, focus_objects=[_tangent()]).run(p)
        assert r.attempts == 40, r.attempts


# ======================================================================
class TestAWalkIsNotPopulation:
    """The counter may not be fed by anything that is not generation.

    This is the test that would have caught the obvious implementation.
    """

    def test_the_optimisation_walk_does_not_touch_the_search_counter(self):
        from ogr_slip2d.optimize import OptimizeSettings
        p = _slope()
        foco = [_tangent()]
        sin = _path(p, focus_objects=foco).run(p)
        con = _path(p, focus_objects=foco,
                    optimize=OptimizeSettings(enabled=True),
                    optimize_seed=SEMILLA).run(p)
        assert sin.focus_rejected > 0, "no focus rejections: no measure"
        assert con.focus_rejected == sin.focus_rejected, (
            con.focus_rejected, sin.focus_rejected)
        assert con.attempts == sin.attempts, (con.attempts, sin.attempts)

    def test_the_test_would_notice(self):
        """Guard on the guard.

        The assertion above is only worth something if the optimisation
        walk actually consults the focus. It does: the walk reaches
        ``_focus_rejects`` through ``getattr`` (v0.1.129, defect D33
        through the back door), and that is precisely the path that would
        have contaminated the counter.
        """
        from ogr_slip2d.optimize import OptimizeSettings
        p = _slope()
        vistas = []
        s = _path(p, focus_objects=[_tangent()],
                  optimize=OptimizeSettings(enabled=True),
                  optimize_seed=SEMILLA)
        original = s._focus_rejects

        def espia(candidate, _v=vistas, _o=original):
            out = _o(candidate)
            _v.append(bool(out))
            return out

        s._focus_rejects = espia
        try:
            s.run(p)
        finally:
            s._focus_rejects = original
        assert vistas, "the focus was never consulted at all"
        assert sum(vistas) > 0, "the focus never rejected anything"

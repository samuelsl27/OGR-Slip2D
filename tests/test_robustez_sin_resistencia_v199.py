# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A surface that cannot be analysed must not kill the search.

WHAT INVARIANT THIS PROTECTS. A material with c = 0 and phi = 0 is legitimate
data — a problem of the reference verification bank requires one, because that
is what its source published — and until v0.1.99 a slip surface whose mass fell
entirely inside such a material ended the whole analysis with a traceback. Not
one surface discarded with a warning: the run itself, out of GridSearch.run and
upwards, with nothing to show for it. On the reference grid of that problem 147
of the 4860 circles it generates did exactly that, 3.0 %, and neither a minimum
area nor a tighter grid avoided them: any grid that reaches the weak material
ends up generating one.

The mechanism was arithmetic, not physics. Bishop's numerator is exactly 0.0
when no slice offers resistance, so F becomes 0.0 — which is FINITE, and
therefore passes the isfinite guard — and the next pass evaluates tan(phi)/F as
0.0/0.0, which in Python raises ZeroDivisionError instead of returning nan. The
m_alpha guard two lines below never ran. Janbu repeated it with n_alpha.

THIS IS NOT A SNAPSHOT TEST. The factor of safety of a strengthless mass is
fixed by an identity, not by what this code happens to print: F is resisting
over driving, and the resisting term shared by every method here,
c'*b + (W - u*b)*tan(phi'), is identically zero when c and tan(phi) are —
Bishop (1955), and the same term in Janbu (1954, 1973), Lowe & Karafiath
(1960), Spencer (1967) and Fredlund & Krahn (1977). So F = 0 exactly. A mass
with no strength anywhere does not stand up. That zero is the only number this
file asserts.

WHY IT IS REPORTED AS A FAILED CALCULATION AND NOT AS A FACTOR OF SAFETY OF
ZERO. Because a factor of zero wins every search, and the answer to "what is
the critical surface of this slope" would become "the piece of it that has no
strength" — true, and useless. The reference documentation resolves it the same
way and is explicit about this exact condition ("normal / shear resistance =
zero along part of the slip surface"): it writes an error code in place of the
safety factor, and the surface joins the population its interface calls invalid
surfaces. Here that means error_message set, is_valid False and invalid_count
incremented — and NOT admissible = False, which this program reserves for a
CONVERGED factor that fails a post-analysis check (methods/base.py).

WHAT EACH CLASS PINS. They guard four different layers, and a failure should
say which one broke:

* TestEveryMethodAgrees — the shared pre-check, and that all nine methods
  answer the same. Measured on 0.1.98 they answered six different ways: three
  raised ZeroDivisionError, two blamed their lambda search (which had nothing
  to do with it), three returned 0.2 — not a factor of safety but the first
  sample of their force-balance F grid — and only Ordinary/Fellenius had the
  number right, with no reason attached to it.
* TestTheGuardIsConditional — rule 7 in its plainest form. The same circle on
  the same geometry, given strength, gives an ordinary factor. A guard that
  fired always would be worse than no guard.
* TestPartialWeakness — the edge of the predicate: a mass that crosses the weak
  layer AND a competent one is analysed normally.
* TestSearchSurvives — the invariant itself, over a whole grid: the run
  finishes, the documented population identity holds, and the surfaces that
  could not be analysed are counted with their reason.
* TestArithmeticNet — the net at the search boundary, exercised with a method
  that fails on purpose. That layer is what makes the invariant true for causes
  nobody has met yet.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

#: The slope both models are cut from: 20 m of face at 38.7 degrees, a gentler
#: bench above it, and 10 m of foundation under the toe. The foundation is not
#: decoration — without it the stretch from x = 0 to the toe encloses no soil
#: and the closing edge runs back along the bottom one (the v0.1.89 note in
#: tests/test_supports_all_methods_v164.py).
_EXTERNAL = [(0, -10), (80, -10), (80, 30), (50, 20), (25, 0), (0, 0)]

#: Splits off the upper-right wedge — the same topology as the reference
#: problem, where the strengthless layer OUTCROPS at the crest. That is what
#: lets a whole sliding mass sit inside it; a weak layer buried under a
#: competent one could never produce the failure this file is about.
_CONTACT = [(50, 20), (80, 20)]

#: A circle whose mass, on the single-material model, is the slope itself:
#: 25 slices, daylighting at x = 37.50 and x = 66.58.
_CIRCLE = (37.5, 45.0, 35.0)

#: A larger circle on the two-material model whose base runs through BOTH
#: materials. Checked in the test, not assumed.
_MIXED_CIRCLE = (30.0, 40.0, 40.0)

_SLICES = 25


# ----------------------------------------------------------------------
def _slope(cohesion: float, friction_deg: float):
    """The slope in ONE material, with the strength asked for."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[Vertex(x, y) for x, y in _EXTERNAL], closed=True)
    ext.ensure_ccw()
    p = Project("one-material")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="soil", unit_weight=19.0,
        strength=MohrCoulomb(cohesion=cohesion, friction_angle=friction_deg))]
    return p


def _two_layer_slope():
    """The same slope with a strengthless wedge outcropping at the crest."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[Vertex(x, y) for x, y in _EXTERNAL], closed=True)
    ext.ensure_ccw()
    p = Project("two-material")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    strong = Material(name="strong", unit_weight=19.0,
                      strength=MohrCoulomb(cohesion=15.0, friction_angle=25.0))
    weak = Material(name="weak", unit_weight=19.0,
                    strength=MohrCoulomb(cohesion=0.0, friction_angle=0.0))
    p.materials = [strong, weak]
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in _CONTACT], closed=False),
        btype=BoundaryType.MATERIAL))
    for region in p.resolve_regions():
        cx, cy = region.centroid()
        p.assign_material_at(cx, cy,
                             (weak if (cx > 50 and cy > 20) else strong).id)
    return p


def _search(method, **kw):
    """A search built by hand, the way every test and script here does."""
    from ogr_slip2d.search import GridSearch
    return GridSearch(method, num_slices=_SLICES, min_area=1.0, **kw)


def _evaluate(project, method_id, circle=_CIRCLE):
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.surface import SlipCircle

    xc, yc, r = circle
    return _search(method_registry()[method_id]()).evaluate_circle(
        project, SlipCircle(centre_x=xc, centre_y=yc, radius=r))


def _all_method_ids():
    from ogr_slip2d.methods import method_registry
    return sorted(method_registry())


def _note():
    from ogr_slip2d.methods.base import LEMMethod
    return LEMMethod.NO_SHEAR_STRENGTH_NOTE


# ----------------------------------------------------------------------
class TestEveryMethodAgrees:
    """Nine methods, one answer, on a mass with no strength anywhere."""

    def test_all_nine_return_zero_and_say_why(self):
        project = _slope(cohesion=0.0, friction_deg=0.0)
        ids = _all_method_ids()
        assert len(ids) == 9, ids          # a new method must join this test
        for method_id in ids:
            res = _evaluate(project, method_id)
            assert res is not None, method_id
            # The identity, not a snapshot: resisting is zero, so F is zero.
            assert res.fos == 0.0, (method_id, res.fos)
            # Reported as a failed calculation, the way the reference writes
            # an error code in place of the safety factor.
            assert not res.is_valid, method_id
            assert res.error_message == _note(), (method_id, res.error_message)
            # And NOT through the admissibility channel, which is meant for a
            # converged factor that fails a post-analysis check.
            assert getattr(res, "admissible", True) is True, method_id

    def test_nothing_raises_where_it_used_to(self):
        """The original defect, named: Bishop and Janbu divided by that zero.

        Reproduced with the shared pre-check disabled ON THE INSTANCE, so what
        has to hold is the arithmetic backstop inside the iteration. Patching
        the instance and not the class is deliberate: the classes and the
        registry are global state (rule 5).
        """
        from ogr_slip2d.methods import method_registry
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle

        project = _slope(cohesion=0.0, friction_deg=0.0)
        xc, yc, r = _CIRCLE
        for method_id in ("bishop_simplified", "janbu_simplified",
                          "janbu_corrected"):
            method = method_registry()[method_id]()
            method._no_shear_strength_result = lambda surface, slices: None
            surface = SlipCircle(centre_x=xc, centre_y=yc, radius=r)
            slices = slice_surface(project, surface, num_slices=_SLICES)
            assert slices is not None and len(slices) >= 3, method_id
            res = method.compute_fos(project, surface, slices)   # must return
            assert not res.is_valid, method_id
            assert res.error_message, method_id


class TestTheGuardIsConditional:
    """Rule 7: a guard that fired always would be worse than no guard."""

    def test_the_same_circle_with_strength_gets_an_ordinary_factor(self):
        weak = _slope(cohesion=0.0, friction_deg=0.0)
        competent = _slope(cohesion=12.0, friction_deg=20.0)
        for method_id in _all_method_ids():
            zero = _evaluate(weak, method_id)
            real = _evaluate(competent, method_id)
            assert zero.fos == 0.0, method_id
            assert real is not None, method_id
            assert real.is_valid, (method_id, real.error_message)
            assert real.fos > 0.0, (method_id, real.fos)
            assert real.error_message == "", (method_id, real.error_message)


class TestPartialWeakness:
    """The edge of the predicate: some strength is not no strength."""

    def test_a_mass_crossing_both_materials_is_analysed(self):
        project = _two_layer_slope()
        res = _evaluate(project, "bishop_simplified", circle=_MIXED_CIRCLE)
        assert res is not None
        names = {s.material.name for s in res.slices if s.material is not None}
        # Checked and not assumed: the circle has to reach both materials for
        # this test to be testing anything at all.
        assert names == {"strong", "weak"}, names
        assert res.is_valid, res.error_message
        assert res.fos > 0.0, res.fos
        assert res.error_message == ""


class TestSearchSurvives:
    """The invariant itself, over a whole grid."""

    #: 5 x 5 centres and 5 radii each. Deliberately under the 400-circle floor
    #: at which Grid Search splits across processes, so this measures the
    #: engine and not the process pool.
    _NX = _NY = _RINC = 4
    _GRID_X = (25.0, 60.0)
    _GRID_Y = (25.0, 55.0)

    def _run(self):
        from ogr_slip2d.methods import method_registry
        project = _two_layer_slope()
        search = _search(method_registry()["bishop_simplified"](),
                         grid_x=self._GRID_X, grid_y=self._GRID_Y,
                         grid_nx=self._NX, grid_ny=self._NY,
                         radius_increment=self._RINC)
        return search.run(project)

    def test_the_run_finishes_and_the_population_adds_up(self):
        result = self._run()
        population = (self._NX + 1) * (self._NY + 1) * (self._RINC + 1)
        # The documented identity: every circle the grid GENERATES is
        # accounted for, whether or not it could be analysed.
        assert result.total_count == population, (result.total_count,
                                                  population)
        assert result.valid_count + result.invalid_count == population

    def test_the_strengthless_circles_are_counted_with_their_reason(self):
        result = self._run()
        blamed = [e for e in result.evaluations if e.error_message == _note()]
        # The grid has to reach the weak wedge, or there is nothing to count.
        assert blamed, "the grid generated no strengthless circle"
        assert len(blamed) <= result.invalid_count
        for e in blamed:
            assert e.fos == 0.0
            assert not e.is_valid

    def test_the_search_still_returns_a_minimum(self):
        result = self._run()
        critical = result.critical
        assert critical is not None, "no critical surface"
        assert critical.is_valid
        assert math.isfinite(result.min_fos) and result.min_fos > 0.0
        # A strengthless surface must never be the answer.
        assert critical.error_message != _note()


class _ExplodingMethod:
    """A method that fails the way the NUMBERS can fail, on purpose.

    Not registered with the register_method decorator: the registry is
    module-level global state and a test that grew it would leak into every
    other file (rule 5). BaseSearch only ever asks a method for METHOD_ID and
    compute_fos, so an object with those two is all it takes.
    """

    METHOD_ID = "exploding_for_test"
    DISPLAY_NAME = "Exploding"

    def compute_fos(self, project, surface, slices):
        zero = len(slices) - len(slices)     # a real zero, not a literal
        return 1.0 / zero


class TestArithmeticNet:
    """The layer that covers the causes nobody has met yet."""

    def test_a_method_that_divides_by_zero_does_not_end_the_run(self):
        project = _two_layer_slope()
        search = _search(_ExplodingMethod(),
                         grid_x=TestSearchSurvives._GRID_X,
                         grid_y=TestSearchSurvives._GRID_Y,
                         grid_nx=2, grid_ny=2, radius_increment=2)
        result = search.run(project)         # must not raise
        assert result.valid_count == 0
        assert result.invalid_count == result.total_count > 0
        blamed = [e for e in result.evaluations
                  if e.error_message.startswith("Arithmetic failure:")]
        assert blamed, [e.error_message for e in result.evaluations]
        for e in blamed:
            assert not e.is_valid

    def test_a_programming_error_still_raises(self):
        """The net is narrow on purpose.

        A blanket except-Exception here is the shape that turned Slope
        Search's TypeError into a generic "Error" dialog with no results, in
        every release up to v0.1.77. A defect in the code has to stay loud.
        """
        import pytest

        class _BrokenMethod(_ExplodingMethod):
            METHOD_ID = "broken_for_test"

            def compute_fos(self, project, surface, slices):
                raise TypeError("a defect, not a number")

        project = _two_layer_slope()
        search = _search(_BrokenMethod(),
                         grid_x=TestSearchSurvives._GRID_X,
                         grid_y=TestSearchSurvives._GRID_Y,
                         grid_nx=2, grid_ny=2, radius_increment=2)
        with pytest.raises(TypeError):
            search.run(project)

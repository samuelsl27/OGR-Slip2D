# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Composite Surfaces has to CLIP the arc, not merely stop rejecting it.

WHAT INVARIANT THIS PROTECTS. A circular slip surface may not run below the
floor of the model, because below it there is no soil. With the option off the
reference program discards such a surface outright — its own Surface Options
dialog draws exactly that circle beside the words "Invalid Surface". With the
option ON it does the other thing: the surface "conforms to the shape of the
External Boundary", riding the floor over the stretch where the arc would have
escaped. Both branches are one rule seen from two sides, and until v0.1.111
this program implemented neither: the option skipped the rejection and analysed
the escaping arc WHOLE, slice bases and all, several feet under the model.

WHY THIS CASE. Verification problem 22 of the reference bank is Fredlund and
Krahn (1977) — the paper that introduced the general limit-equilibrium
formulation precisely so that composite surfaces could be solved — and it is
built for this: a 1 ft weak layer of c' = 0, phi' = 10 deg lying ON the floor
of the model, under a stronger soil. The paper gives the surface rather than
searching for it (xc = 120, yc = 90, R = 80), and that circle reaches y = 10
against a floor at y = 15. Which soil the surface runs through is therefore the
whole problem: composed, it rides the weak layer for 56 ft; unclipped, it
misses it almost entirely.

Measured on 0.1.110, before the fix, with the option ENABLED: the arc reached
y = 10.0000 — exactly ``centre_y - radius``, the untouched circle — 2 of its 30
slice bases sat in the weak layer, and Bishop came out at 1.9806 against the
1.377 the paper publishes. +43 %, on the unsafe side.

THIS IS NOT A SNAPSHOT TEST. Four independent things are asserted and none of
them is a number this code printed:

* the GEOMETRY is closed-form arithmetic — the arc meets a floor at elevation
  ``y_f`` at ``xc +- sqrt(R^2 - (yc - y_f)^2)``, and that is where the composite
  must change branch, to the last bit;
* the CONTAINMENT is a statement about the model, not about the answer: no part
  of the analysed surface may lie below the floor;
* the VALUE is anchored to Fredlund and Krahn (1977) table 22.3, the ORIGINAL
  source of the problem, and not to what any program reports for it;
* the OPTION MOVES THE NUMBER (rule 7), and it moves it in both directions:
  with the option off this very circle is refused, and a circle that never
  leaves the soil is answered identically whether the option is on or off.

ONE EXCLUSION, AND IT IS SOURCED. The Ordinary/Fellenius method is asserted
against the paper in the DRY case only. With pore pressure the two classical
formulations of how ``u`` enters Fellenius moment equilibrium separate, the
paper used one and modern programs use the other, and the gap is about 5 %.
That was measured independently on verification problem 21 — the same slope
without the weak layer — where the dry case agrees to 0.1 % and only the Ru
case parts company. Asserting the disagreement would freeze a difference of
formulation into a test; asserting the agreement would fail for a reason that
has nothing to do with composite surfaces. So the dry case carries all four
methods and the Ru case carries the three that share one formulation.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

import pytest


# ----------------------------------------------------------------------
# Problem 22, figure 22.1, vertex by vertex (feet). The floor of the model
# is y = 15 and the top of the weak layer is y = 16.
_Y_FLOOR = 15.0
_Y_WEAK_TOP = 16.0
_EXTERNAL = [(0, 15), (180, 15), (180, 16), (180, 20), (140, 20),
             (60, 60), (0, 60), (0, 16)]

#: The surface the paper gives, rather than one this program searched for.
_XC, _YC, _R = 120.0, 90.0, 80.0

#: Table 22.3 — Fredlund and Krahn (1977), composite circular.
_FK_DRY = {"ordinary_fellenius": 1.288, "bishop_simplified": 1.377,
           "spencer": 1.373, "gle_morgenstern_price": 1.370}
_FK_RU = {"bishop_simplified": 1.124, "spencer": 1.118,
          "gle_morgenstern_price": 1.118}

#: The manual warns that "the location of the weak layer is slightly
#: different in all the above references" and that results "routinely vary
#: in the second decimal place" because of it. 2 % is that second decimal
#: place with room to spare, and is the tolerance the project already uses
#: for a published critical surface.
_TOL = 0.02

_METHODS = ("ordinary_fellenius", "bishop_simplified", "spencer",
            "gle_morgenstern_price")


def _project(ru: float = 0.0, composite: bool = True):
    """The problem-22 model, built from the published geometry."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection

    p = Project("composite / weak layer — Fredlund & Krahn (1977)")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in _EXTERNAL], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(0, _Y_WEAK_TOP), Vertex(180, _Y_WEAK_TOP)], closed=False),
        btype=BoundaryType.MATERIAL))

    ppt = PorePressureType.RU_COEFFICIENT if ru else PorePressureType.NONE
    upper = Material(name="Upper soil", unit_weight=120.0,
                     sat_unit_weight=120.0,
                     strength=MohrCoulomb(cohesion=600.0, friction_angle=20.0),
                     pore_pressure=ppt, ru=ru)
    weak = Material(name="Weak layer", unit_weight=120.0,
                    sat_unit_weight=120.0,
                    strength=MohrCoulomb(cohesion=0.0, friction_angle=10.0),
                    pore_pressure=ppt, ru=ru)
    p.materials = [upper, weak]
    p.resolve_regions()
    p.assign_material_at(90.0, 30.0, upper.id)
    p.assign_material_at(90.0, 15.5, weak.id)

    p.settings.units.system_id = "imperial_psf"
    p.settings.groundwater.pore_fluid_unit_weight = 62.4
    p.settings.methods.num_slices = 30
    p.settings.methods.interslice_function = "half_sine"
    p.settings.search.composite_surfaces = composite
    # The crest is on the LEFT (y = 60) and the toe on the right (y = 20).
    p.settings.units.failure_direction = FailureDirection.LEFT_TO_RIGHT
    return p


def _evaluate(method_id: str, ru: float = 0.0, composite: bool = True,
              n: int = 30, circle=(_XC, _YC, _R)):
    """The published circle, through the one door a search uses."""
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.search import GridSearch
    from ogr_slip2d.surface import SlipCircle

    p = _project(ru=ru, composite=composite)
    c = SlipCircle(centre_x=circle[0], centre_y=circle[1], radius=circle[2])
    search = GridSearch(method=method_registry()[method_id](),
                        num_slices=n, min_area=0.0)
    return search.evaluate_circle(p, c)


def _transition_abscissae() -> tuple[float, float]:
    """Where a circle of radius R about (xc, yc) meets the elevation y_f.

    Closed form, so the test measures the code and not the other way round.
    """
    half = math.sqrt(_R * _R - (_YC - _Y_FLOOR) ** 2)
    return _XC - half, _XC + half


# ======================================================================
class TestTheGeometryIsClosedForm:
    """Where the surface bends is arithmetic, not a measurement."""

    def test_the_arc_alone_would_dive_below_the_model(self):
        # The bottom of the published circle against the floor of the
        # model. This is the premise of the whole problem, and it is the
        # number the defect used to report as the surface elevation.
        assert _YC - _R == pytest.approx(10.0)
        assert _YC - _R < _Y_FLOOR - 4.0

    def test_the_composite_changes_branch_where_arithmetic_says(self):
        res = _evaluate("bishop_simplified")
        assert res is not None
        kinks = res.surface.kinks()
        x_in, x_out = _transition_abscissae()
        assert len(kinks) == 2, kinks
        assert kinks[0] == pytest.approx(x_in, rel=1e-9)
        assert kinks[1] == pytest.approx(x_out, rel=1e-9)

    def test_the_surface_is_the_arc_outside_and_the_floor_between(self):
        res = _evaluate("bishop_simplified")
        s = res.surface
        x_in, x_out = _transition_abscissae()
        # Strictly inside the clipped stretch the surface IS the floor...
        for t in (0.25, 0.5, 0.75):
            x = x_in + (x_out - x_in) * t
            assert s.base_y_at(x) == pytest.approx(_Y_FLOOR, abs=1e-9)
            assert s.base_angle_at(x) == pytest.approx(0.0, abs=1e-12)
        # ...and outside it, the arc, to the last bit.
        for x in (x_in - 5.0, x_out + 5.0):
            arc = _YC - math.sqrt(_R * _R - (x - _XC) ** 2)
            assert s.base_y_at(x) == pytest.approx(arc, rel=1e-12)

    def test_no_part_of_the_analysed_surface_is_below_the_floor(self):
        res = _evaluate("bishop_simplified")
        lowest = min(min(sl.base_y_left, sl.base_y_right)
                     for sl in res.slices)
        assert lowest == pytest.approx(_Y_FLOOR, abs=1e-9)

    def test_minimum_elevation_is_asked_of_the_clipped_surface(self):
        # Not ``centre_y - radius``: that is the point the clipping
        # removed. Answering with it would let the Minimum Elevation filter
        # discard the very surface this option exists to build.
        from ogr_slip2d.surface import lowest_elevation
        res = _evaluate("bishop_simplified")
        assert lowest_elevation(res.surface) == pytest.approx(_Y_FLOOR,
                                                              abs=1e-9)


# ======================================================================
class TestTheSurfaceRestsOnTheWeakLayer:
    """The reference's rule for the linear stretches, and the layer cut."""

    def test_the_straight_stretch_takes_the_material_above_it(self):
        # "The material strength used for each slice along the linear
        # portions of the composite surface will be the strength of the
        # material immediately above each slice base." On this model that
        # material is the weak layer, and it is the only reason the
        # published factor of safety is 1.38 and not 2.
        res = _evaluate("bishop_simplified")
        on_floor = [sl for sl in res.slices
                    if abs(sl.base_y_left - _Y_FLOOR) < 1e-9
                    and abs(sl.base_y_right - _Y_FLOOR) < 1e-9]
        assert len(on_floor) >= 10, len(on_floor)
        assert all(sl.material.name == "Weak layer" for sl in on_floor)

    def test_the_weak_layer_is_still_a_mandatory_cut(self):
        # The slicer culls material boundaries by bounding box, using the
        # y-range of the surface. Answer that range the way a plain arc
        # would — the two endpoints only, (20, 60) here — and the layer at
        # y = 16 falls outside it, is culled, and stops being a mandatory
        # cut without a word.
        #
        # Where the arc meets that layer is closed form, so the assertion
        # is that those two abscissae ARE slice boundaries, not that some
        # cut happens to land nearby.
        res = _evaluate("bishop_simplified")
        half = math.sqrt(_R * _R - (_YC - _Y_WEAK_TOP) ** 2)
        edges = [sl.base_x_left for sl in res.slices]
        edges.append(res.slices[-1].base_x_right)
        span = res.slices[-1].base_x_right - res.slices[0].base_x_left
        for x in (_XC - half, _XC + half):
            assert any(abs(e - x) < 1e-9 * span for e in edges), (
                f"the layer crossing at x = {x:.6f} is not a slice boundary")

    def test_no_slice_base_crosses_the_layer_in_its_interior(self):
        # The consequence of the cut above, and the thing that actually
        # goes wrong without it: a base that passes THROUGH the layer top
        # has to be given one material for a surface that lies in two.
        # A base that merely ENDS on the layer is not one of those, which
        # is why both comparisons are strict.
        res = _evaluate("bishop_simplified")
        tol = 1e-9 * _R
        for sl in res.slices:
            lo = min(sl.base_y_left, sl.base_y_right)
            hi = max(sl.base_y_left, sl.base_y_right)
            assert not (lo < _Y_WEAK_TOP - tol and hi > _Y_WEAK_TOP + tol), (
                f"slice {sl.index} crosses the weak layer top")

    def test_the_span_the_slicer_culls_on_covers_the_floor(self):
        res = _evaluate("bishop_simplified")
        s = res.surface
        lo, hi = s.y_span(*s.x_range())
        assert lo == pytest.approx(_Y_FLOOR, abs=1e-9)
        assert lo < _Y_WEAK_TOP < hi


# ======================================================================
class TestTheOptionMovesTheNumber:
    """Rule 7, in both directions."""

    def test_without_the_option_this_circle_is_refused(self):
        # Which is the reference's own OFF branch: its dialog draws this
        # circle next to the label "Invalid Surface".
        assert _evaluate("bishop_simplified", composite=False) is None

    def test_with_the_option_it_is_analysed_and_it_is_a_composite(self):
        from ogr_slip2d.surface import CompositeSurface
        res = _evaluate("bishop_simplified", composite=True)
        assert res is not None
        assert isinstance(res.surface, CompositeSurface)

    def test_a_circle_that_stays_in_the_soil_is_untouched(self):
        # The other half of rule 7: an option that changes an answer it has
        # no business changing is as bad as one that changes nothing. A
        # shallow circle never reaches the floor, so the two runs must
        # agree to the last digit AND leave a plain circle behind.
        from ogr_slip2d.surface import SlipCircle
        shallow = (100.0, 55.0, 22.0)
        on = _evaluate("bishop_simplified", composite=True, circle=shallow)
        off = _evaluate("bishop_simplified", composite=False, circle=shallow)
        assert on is not None and off is not None
        assert isinstance(on.surface, SlipCircle)
        assert on.fos == off.fos


# ======================================================================
class TestAgainstFredlundAndKrahn1977:
    """Table 22.3 of the source the problem is taken from."""

    def test_the_dry_case_reproduces_all_four_methods(self):
        bad = []
        for mid, published in _FK_DRY.items():
            res = _evaluate(mid, ru=0.0)
            assert res is not None, mid
            err = abs(res.fos / published - 1.0)
            if err > _TOL:
                bad.append(f"{mid}: {res.fos:.4f} vs {published} "
                           f"({100 * err:+.2f} %)")
        assert not bad, bad

    def test_the_ru_case_reproduces_the_three_that_share_a_formulation(self):
        # Ordinary is left out on purpose; see the module docstring and
        # verification problem 21 for the measurement that settles why.
        bad = []
        for mid, published in _FK_RU.items():
            res = _evaluate(mid, ru=0.25)
            assert res is not None, mid
            err = abs(res.fos / published - 1.0)
            if err > _TOL:
                bad.append(f"{mid}: {res.fos:.4f} vs {published} "
                           f"({100 * err:+.2f} %)")
        assert not bad, bad

    def test_the_answer_does_not_hang_on_the_slice_count(self):
        # A factor of safety that moves with the slicing is a factor of
        # safety about the slicing. The published value was computed at
        # some slice count nobody wrote down, so agreement at 30 slices
        # means nothing unless 60 says the same.
        coarse = _evaluate("bishop_simplified", n=30).fos
        fine = _evaluate("bishop_simplified", n=60).fos
        assert abs(fine / coarse - 1.0) < 0.005, (coarse, fine)


# ======================================================================
class TestTheMomentAxisIsTheCentreOfTheCircle:
    """Fredlund and Krahn (1977) take moments about the circular part.

    A composite is not a circle — its base normals do not all point at the
    centre, and the ``Sigma N.f`` term of their general formulation is
    exactly the one that accounts for the difference — but it does have a
    centre of rotation, and that is the point the balance is written about.
    The alternative is the axis this program constructs for a surface with
    no centre at all, and on this very surface that costs Bishop 1.9 %.
    """

    def test_the_axis_is_the_centre(self):
        from ogr_slip2d.surface import moment_axis
        res = _evaluate("bishop_simplified")
        assert moment_axis(res.surface) == (_XC, _YC)

    def test_the_methods_use_it(self):
        for mid in ("bishop_simplified", "ordinary_fellenius"):
            res = _evaluate(mid)
            assert res.details.get("moment_axis") == (_XC, _YC), mid

    def test_a_user_axis_does_not_override_a_real_centre(self):
        # The same rule a circle already lives by: Add Axis exists for
        # surfaces that have no centre of rotation, and a composite has one.
        from ogr_slip2d.surface import moment_axis
        res = _evaluate("bishop_simplified")
        assert moment_axis(res.surface, override=(1.0, 2.0)) == (_XC, _YC)


# ======================================================================
class TestTheArcWinsWhereverItCan:
    """A floor crossed four times, which the reference does not draw.

    Its wording covers one dip — "between the two circle intersection
    points" — and a bedrock horizon is not obliged to be crossed twice. The
    rule implemented is ``max(arc, floor)`` at every abscissa, which agrees
    with the documented case and settles the rest by mechanics rather than
    by phrasing: the floor constrains the surface from BELOW and nowhere
    else, so where the arc runs above the floor the arc is the surface.

    The case that separates the two readings is a TRENCH in the bedrock.
    Read literally — follow the boundary from the first intersection to the
    last — the surface would climb down one wall of the trench, along its
    bottom and up the other side, adding depth and length that nothing
    requires. Under ``max`` it passes straight over, which is what a slip
    surface does: a hole in the bedrock is not something the failing mass
    has to go into.
    """

    #: Flat floor at y = 0 with a trench between x = 40 and x = 60 whose
    #: bottom, y = -12, is well below the deepest point of the arc (-5).
    _EXTERNAL = [(0, 0), (40, 0), (45, -12), (55, -12), (60, 0),
                 (100, 0), (100, 40), (0, 40)]
    _CIRCLE = (50.0, 40.0, 45.0)
    _ENDS = (6.0, 94.0)

    @classmethod
    def _trenched(cls):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_slip2d.surface import SlipCircle, compose_with_bedrock
        ext = Polyline(vertices=[Vertex(x, y) for x, y in cls._EXTERNAL],
                       closed=True)
        ext.ensure_ccw()
        b = Boundary(polyline=ext, btype=BoundaryType.EXTERNAL)
        c = SlipCircle(centre_x=cls._CIRCLE[0], centre_y=cls._CIRCLE[1],
                       radius=cls._CIRCLE[2])
        c.x_left, c.x_right = cls._ENDS
        return compose_with_bedrock(c, b), c

    def test_the_premise_the_arc_dips_below_the_flat_floor(self):
        # Closed form: the arc meets y = 0 at xc +- sqrt(R^2 - yc^2).
        _surface, circle = self._trenched()
        half = math.sqrt(45.0 ** 2 - 40.0 ** 2)
        assert circle.base_y_at(50.0 - half) == pytest.approx(0.0, abs=1e-9)
        assert circle.base_y_at(35.0) < 0.0        # inside the dip
        assert circle.base_y_at(50.0) == pytest.approx(-5.0)   # 40 - 45

    def test_it_rides_the_floor_on_both_sides_of_the_trench(self):
        surface, _circle = self._trenched()
        for x in (35.0, 65.0):
            assert surface.base_y_at(x) == pytest.approx(0.0, abs=1e-9)
            assert surface.follows_bedrock_at(x)

    def test_it_passes_over_the_trench_on_its_own_arc(self):
        surface, circle = self._trenched()
        for x in (45.0, 50.0, 55.0):
            assert surface.base_y_at(x) == pytest.approx(
                circle.base_y_at(x), rel=1e-12)
            assert not surface.follows_bedrock_at(x)
        # And it never reaches the bottom of the trench.
        assert surface.y_span(*surface.x_range())[0] > -12.0 + 6.0

    def test_the_arc_is_still_the_surface_outside_the_dip(self):
        surface, circle = self._trenched()
        for x in (10.0, 90.0):
            assert surface.base_y_at(x) == pytest.approx(
                circle.base_y_at(x), rel=1e-12)

    def test_every_change_of_slope_is_a_mandatory_cut(self):
        # Six: four arc-to-floor transitions, plus the two lips of the
        # trench, which ARE bends of the surface because the floor is the
        # surface on their outer side. The bottom corners of the trench are
        # not — the arc is the surface there — and counting them would
        # spend two slices on bends the surface does not have.
        surface, _circle = self._trenched()
        assert len(surface.kinks()) == 6, surface.kinks()
        assert 40.0 in surface.kinks() and 60.0 in surface.kinks()
        assert not any(44.0 < k < 56.0 for k in surface.kinks())

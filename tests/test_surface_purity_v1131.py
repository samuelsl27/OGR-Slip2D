# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Evaluating a surface may not change the surface, and endpoints may not be a
way past the rules that decide whether the surface exists.

WHAT INVARIANT THIS PROTECTS. ``BaseSearch.evaluate_circle`` used to write the
analysed extent — ``x_left``, ``x_right``, the reverse-curvature cracks and the
tension-crack wall — back onto the ``SlipCircle`` it was handed, "so the drawing
and the number agree". Nothing drew from that object: the canvas, the exporters
and the reports all read ``result.surface``. What the write did do was pin the
next call: a circle that arrives with its endpoints set names one mass and is
never re-resolved, so the SECOND evaluation of the same object answered for the
extent the FIRST one had found, whatever model it was now being asked about.

WHY THIS CASE. Verification problem 22 — Fredlund and Krahn (1977), the paper
that introduced the general limit-equilibrium formulation so that composite
surfaces could be solved — publishes its surface instead of searching for it
(xc = 120, yc = 90, R = 80), and that arc reaches y = 10 against a floor at
y = 15. Which soil the surface runs through IS the problem: composed, it rides
a 1 ft weak layer of c' = 0, phi' = 10 deg for 56 ft; unclipped, it misses it
almost entirely and weighs five feet of soil the model does not contain.

WHAT WAS MEASURED, on 0.1.130, before the fix:

* the same object three times, Composite Surfaces ON — 1.3809, then 1.9806,
  then 1.9806. The second call answers for the UNCLIPPED arc, which is defect
  D15 exactly as v0.1.111 closed it, arriving again through the endpoints;
* the same loop ``run_global_minimum`` runs — one rebuilt surface, N samples —
  with five IDENTICAL samples and nothing perturbed: 1.3809 once and 1.9806
  four times. So this was never a masking defect. Probabilistic Analysis and
  Sensitivity Analysis reported it to the user;
* Composite Surfaces OFF, the same circle pre-resolved by hand: None when its
  endpoints are unset, because ``leaves_soil_region`` refuses it, and 1.9806
  the moment they are set. The reference counts that rejection as its error
  -103, and named endpoints walked straight past it.

THIS IS NOT A SNAPSHOT TEST. What is asserted is either a statement about the
object (its fields are unchanged; two routes give the same number) or a value
anchored to Fredlund and Krahn (1977) table 22.3 — 1.377 for Bishop, 1.373 for
Spencer — never a number this program printed. 1.98 appears only as the value
that must NOT come back, and it is published as the defect in the v0.1.111
changelog rather than measured here.

WHY THE PINNING STAYS. Endpoints that arrive set are honoured on purpose: it is
how a caller asks about a mass other than the critical one, which is what
``tests/test_disjoint_masses_v1101.py`` does to evaluate the two masses of
problem 27 one at a time. The fix is not to ignore them — a class below fails
if they are ignored — but to stop the engine SETTING them behind the caller's
back, and to give a named mass the same clipping and the same containment rule
a resolved one gets.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
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

#: Table 22.3 — Fredlund and Krahn (1977), composite circular, dry case.
_FK_DRY = {"bishop_simplified": 1.377, "spencer": 1.373}

#: The same 2 % the composite file uses, and for the same reason the manual
#: gives: "the location of the weak layer is slightly different in all the
#: above references" and results "routinely vary in the second decimal place".
_TOL = 0.02

#: What the UNCLIPPED arc gives. Not measured here — it is what the v0.1.111
#: changelog publishes as defect D15/A22-1, +43 % on the unsafe side, and it
#: is the number that must not come back.
_UNCLIPPED = 1.98

_SLICES = 30

_CACHE: dict = {}


# ----------------------------------------------------------------------
def _project(composite: bool = True):
    """The problem-22 model, built from the published geometry.

    Built here rather than loaded, because the verification bank lives
    outside this repository. Cached per option: every class below asks for
    the same two projects, and building one costs more than evaluating on it.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection

    key = bool(composite)
    if key in _CACHE:
        return _CACHE[key]

    p = Project("composite / weak layer — Fredlund & Krahn (1977)")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in _EXTERNAL], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(0, _Y_WEAK_TOP), Vertex(180, _Y_WEAK_TOP)], closed=False),
        btype=BoundaryType.MATERIAL))

    upper = Material(name="Upper soil", unit_weight=120.0,
                     sat_unit_weight=120.0,
                     strength=MohrCoulomb(cohesion=600.0, friction_angle=20.0),
                     pore_pressure=PorePressureType.NONE)
    weak = Material(name="Weak layer", unit_weight=120.0,
                    sat_unit_weight=120.0,
                    strength=MohrCoulomb(cohesion=0.0, friction_angle=10.0),
                    pore_pressure=PorePressureType.NONE)
    p.materials = [upper, weak]
    p.resolve_regions()
    p.assign_material_at(90.0, 30.0, upper.id)
    p.assign_material_at(90.0, 15.5, weak.id)

    p.settings.units.system_id = "imperial_psf"
    p.settings.groundwater.pore_fluid_unit_weight = 62.4
    p.settings.methods.num_slices = _SLICES
    p.settings.methods.interslice_function = "half_sine"
    p.settings.search.composite_surfaces = composite
    # The crest is on the LEFT (y = 60) and the toe on the right (y = 20).
    p.settings.units.failure_direction = FailureDirection.LEFT_TO_RIGHT
    _CACHE[key] = p
    return p


def _search(method_id: str = "bishop_simplified"):
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.search import GridSearch

    return GridSearch(method=method_registry()[method_id](),
                      num_slices=_SLICES, min_area=0.0)


def _circle(x_left=None, x_right=None):
    """A FRESH circle, optionally pinned to one named extent."""
    from ogr_slip2d.surface import SlipCircle

    c = SlipCircle(centre_x=_XC, centre_y=_YC, radius=_R)
    if x_left is not None:
        c.x_left, c.x_right = x_left, x_right
    return c


def _published_chord():
    """Where the published arc meets the ground, from the model itself."""
    if "chord" not in _CACHE:
        from ogr_core.geometry import ground_surface
        ground = ground_surface(_project().external_boundary())
        chords = _circle().candidate_chords(ground)
        assert chords, "the published circle must cut the ground"
        _CACHE["chord"] = chords[0]
    return _CACHE["chord"]


# ======================================================================
class TestThePremiseTheArcEscapesTheModel:
    """Closed-form geometry, so the rest measures the code and not itself."""

    def test_the_arc_dives_below_the_floor_of_the_model(self):
        # The lowest point of the arc is centre_y - R, and the centre's
        # abscissa lies inside the chord, so the arc actually reaches it.
        x_l, x_r = _published_chord()
        assert x_l < _XC < x_r, (x_l, x_r)
        assert _YC - _R == pytest.approx(10.0)
        assert _YC - _R < _Y_FLOOR

    def test_the_containment_rule_refuses_it_when_it_is_not_clipped(self):
        from ogr_slip2d.surface import leaves_soil_region

        x_l, x_r = _published_chord()
        verts = list(_project(False).external_boundary().polyline.vertices)
        assert leaves_soil_region(_circle(), verts, x_l, x_r)


# ======================================================================
class TestTheObjectComesOutAsItWentIn:
    """Criterion 1 of the defect report: ``evaluate_circle`` is not a
    mutator. Stated on the object, so it holds whatever the number is."""

    def test_nothing_is_written_onto_the_circle(self):
        p, ev = _project(), _search()
        c = _circle()
        before = copy.deepcopy(vars(c))
        assert ev.evaluate_circle(p, c) is not None
        assert vars(c) == before, {
            k: (before.get(k), vars(c).get(k))
            for k in vars(c) if before.get(k) != vars(c).get(k)}

    def test_nothing_is_written_when_the_answer_is_a_refusal(self):
        """A rejected circle must not be marked by the attempt either."""
        p, ev = _project(False), _search()
        c = _circle()
        before = copy.deepcopy(vars(c))
        assert ev.evaluate_circle(p, c) is None
        assert vars(c) == before

    def test_the_analysed_extent_is_in_the_result(self):
        """Nothing is LOST by not writing it: the mass that was analysed
        travels in ``result.surface``, which is where every consumer in this
        program already reads it from."""
        p, ev = _project(), _search()
        res = ev.evaluate_circle(p, _circle())
        x_l, x_r = _published_chord()
        assert res.surface.x_left == pytest.approx(x_l, abs=1e-9)
        assert res.surface.x_right == pytest.approx(x_r, abs=1e-9)
        assert res.slices[0].base_x_left == pytest.approx(x_l, abs=1e-6)
        assert res.slices[-1].base_x_right == pytest.approx(x_r, abs=1e-6)

    def test_the_polyline_door_does_not_write_on_its_argument_either(self):
        """``evaluate_surface`` reaches the same engine, so the same rule
        has to hold for the geometry a circle is not."""
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.surface import SlipSurface

        x_l, x_r = _published_chord()
        pts = []
        for i in range(41):
            x = x_l + (x_r - x_l) * i / 40
            d = max(0.0, _R * _R - (x - _XC) ** 2)
            pts.append(Vertex(x, max(_Y_FLOOR, _YC - math.sqrt(d))))
        surf = SlipSurface(polyline=Polyline(vertices=pts, closed=False))
        before = [(v.x, v.y) for v in surf.polyline.vertices]
        _search().evaluate_surface(_project(), surf)
        assert [(v.x, v.y) for v in surf.polyline.vertices] == before


# ======================================================================
class TestTheSameObjectReusedAnswersLikeAFreshOne:
    """Criterion 2, the one that actually closes the defect: a first
    evaluation may not decide what a second one measures."""

    def test_three_calls_on_one_object_give_one_number(self):
        p = _project()
        for method_id in sorted(_FK_DRY):
            ev, c = _search(method_id), _circle()
            got = [ev.evaluate_circle(p, c).fos for _ in range(3)]
            assert got[1] == pytest.approx(got[0], rel=1e-12), (method_id, got)
            assert got[2] == pytest.approx(got[0], rel=1e-12), (method_id, got)

    def test_and_that_number_is_the_published_one(self):
        """Anchored to Fredlund and Krahn (1977) table 22.3. Reusing the
        object must not merely be self-consistent, it must be RIGHT: before
        the fix the second call gave 1.98, the unclipped arc."""
        p = _project()
        for method_id in sorted(_FK_DRY):
            ev, c = _search(method_id), _circle()
            for k in range(3):
                fos = ev.evaluate_circle(p, c).fos
                assert fos == pytest.approx(_FK_DRY[method_id], rel=_TOL),                     (method_id, k, fos)
                assert fos < _UNCLIPPED - 0.2, (method_id, k, fos)

    def test_the_same_object_on_ANOTHER_model_answers_for_that_model(self):
        """The literal criterion of the defect report: the same object
        across two projects.

        The two differ only in Composite Surfaces, which is the cleanest
        pair available — the same circle is CLIPPED in one and REFUSED in
        the other, so an inherited extent shows up as an answer where there
        must be none.
        """
        on, off = _project(True), _project(False)
        ev = _search()
        c = _circle()
        assert ev.evaluate_circle(on, c) is not None
        assert ev.evaluate_circle(off, c) is None
        assert ev.evaluate_circle(on, c).fos == pytest.approx(
            ev.evaluate_circle(on, _circle()).fos, rel=1e-12)

    def test_the_statistical_loop_gives_identical_samples(self):
        """The path that makes this a defect of the PROGRAM and not of the
        measuring scripts: ``run_global_minimum`` rebuilds ONE surface and
        evaluates it on every sample. Five identical clones, nothing
        perturbed, so five identical factors — before the fix the first
        differed from the other four by 43 %."""
        from ogr_core.statistics.probabilistic import (
            _evaluate_on, _rebuild_surface,
        )
        from ogr_core.statistics.random_variables import clone_project

        p, ev = _project(), _search()
        det = ev.evaluate_circle(p, _circle())
        surface = _rebuild_surface(det.surface.to_dict())
        got = [_evaluate_on(clone_project(p), ev, surface).fos
               for _ in range(5)]
        for fos in got[1:]:
            assert fos == pytest.approx(got[0], rel=1e-12), got
        assert got[0] == pytest.approx(_FK_DRY["bishop_simplified"],
                                       rel=_TOL), got


# ======================================================================
class TestEndpointsThatArriveSetStillNameAMass:
    """The feature the fix must not break. Ignoring the endpoints would
    pass every class above and lose the only way to ask about a mass that
    is not the critical one."""

    #: A named sub-extent of the published chord, well inside it.
    _NAMED = (60.0, 140.0)

    def test_the_named_extent_is_the_one_analysed(self):
        res = _search().evaluate_circle(_project(), _circle(*self._NAMED))
        assert res is not None
        assert res.surface.x_left == pytest.approx(self._NAMED[0], abs=1e-9)
        assert res.surface.x_right == pytest.approx(self._NAMED[1], abs=1e-9)
        # The slices are the surface as actually analysed, so they are the
        # assertion that cannot be satisfied by carrying a label around.
        assert res.slices[0].base_x_left == pytest.approx(
            self._NAMED[0], abs=1e-6)
        assert res.slices[-1].base_x_right == pytest.approx(
            self._NAMED[1], abs=1e-6)

    def test_it_is_not_silently_replaced_by_the_whole_mass(self):
        ev, p = _search(), _project()
        named = ev.evaluate_circle(p, _circle(*self._NAMED))
        whole = ev.evaluate_circle(p, _circle())
        assert abs(named.surface.x_left - whole.surface.x_left) > 1.0
        assert named.fos != pytest.approx(whole.fos, rel=1e-6)


# ======================================================================
class TestNamedEndpointsAreNotAWayPastTheRules:
    """The second defect, underneath the first: until v0.1.131 the branch
    that honours incoming endpoints skipped the composite clipping and the
    containment rule, so naming a mass meant skipping the two rules that
    decide whether the surface exists at all."""

    def test_a_named_mass_is_clipped_like_a_resolved_one(self):
        """Same circle and same extent, one resolved by the engine and one
        named by the caller: the surface analysed has to be the same kind of
        thing, and the number has to be the paper's."""
        from ogr_slip2d.surface import CompositeSurface

        ev, p = _search(), _project(True)
        x_l, x_r = _published_chord()
        named = ev.evaluate_circle(p, _circle(x_l, x_r))
        assert isinstance(named.surface, CompositeSurface)
        assert named.fos == pytest.approx(_FK_DRY["bishop_simplified"],
                                          rel=_TOL), named.fos
        assert named.fos == pytest.approx(
            ev.evaluate_circle(p, _circle()).fos, rel=1e-12)

    def test_a_named_mass_that_leaves_the_model_is_still_refused(self):
        """With the option off the containment rule owns this circle, and
        naming its extent may not buy it an answer: it reaches y = 10 under
        a floor at y = 15, and the weight of those five feet is soil that
        does not exist. The reference counts that rejection as error -103."""
        ev, p = _search(), _project(False)
        x_l, x_r = _published_chord()
        assert ev.evaluate_circle(p, _circle()) is None
        assert ev.evaluate_circle(p, _circle(x_l, x_r)) is None
        assert ev.evaluate_surface(p, _circle(x_l, x_r)) is None

    def test_the_rule_passes_what_stays_inside_the_model(self):
        """The other half of it (rule 7): a containment rule that rejected
        everything named would not be a rule but a veto.

        The window is closed-form. To the right of the centre the arc leaves
        the floor (y = 15) at ``xc + sqrt(R^2 - (yc - 15)^2)`` and daylights
        through the toe bench (y = 20) at ``xc + sqrt(R^2 - (yc - 20)^2)``;
        between the two it runs inside the soil, so an extent named there
        must be answered for even with the option off.
        """
        ev = _search()
        x_floor = _XC + math.sqrt(_R * _R - (_YC - _Y_FLOOR) ** 2)
        x_day = _XC + math.sqrt(_R * _R - (_YC - 20.0) ** 2)
        assert x_floor < x_day, (x_floor, x_day)
        inside = (x_floor + 0.5, x_day - 0.5)
        res = ev.evaluate_circle(_project(False), _circle(*inside))
        assert res is not None, inside
        # ``x_left``/``x_right`` and not ``x_range()``: on a circle the
        # latter is the extent of the whole circle before any ground
        # clipping, by its own docstring, so it says nothing about the mass.
        assert res.surface.x_left == pytest.approx(inside[0], abs=1e-9)
        assert res.surface.x_right == pytest.approx(inside[1], abs=1e-9)

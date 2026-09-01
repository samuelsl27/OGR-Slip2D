# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Outside the External Boundary there is no soil, and a default that cannot
be told apart from a measurement is invented data.

Until v0.1.143 ``ogr_slip2d.slicer._material_at`` answered a point outside
every region with the FIRST material of the project, silently. That is the
residue of anomaly D48, whose other half was fixed in v0.1.126 with a
geometric guard after an optimised surface walked to y = -4.83 under a
model floored at y = 0 and was REWARDED for it: outside the regions it was
handed the weakest of the two materials, so it returned 1.0902 where the
same surface clipped back inside returns 1.2676.

What the measurement found, and what these tests are shaped by, is that
the fallback was not the unreachable leftover it had been filed as. It
fired 11 972 times over the first four problems of the verification bank —
and not one of those was a surface leaving the model. Every one was the
material query itself overshooting: the base is asked about at
``base_y_mid + 0.01``, an absolute lift unchanged since v0.1.59, and where
a base runs within 0.01 of the ground — the end slices of every surface
that enters or exits near the tangent — the lift jumps over the ground
surface and asks about a point in the air. On problem 3, one Bishop
search, 431 of them, and in 301 the material handed back was the WRONG
one: Soil #1 where the base is cut in Soil #3.

So there are two questions, and the invariants below keep them apart:

  * *what fills a point the lift overshot?* — the base is in soil, the
    QUERY was wrong, and the answer is the material the base really cuts;
  * *what fills a point outside the model?* — there is no soil, and the
    surface is refused whole, which is the judgement
    ``water_surface_defined_at`` has made since v0.1.96 for a water
    surface that does not reach an abscissa.

Every anchor here is an identity, never a captured number: no soil weighs
nothing; a base cut in a layer is made of that layer; a surface with no
soil under it is not a free body. None of them can be satisfied by
consecrating what the code prints today.
"""
from __future__ import annotations

import pytest

GAMMA_LOW = 15.0
GAMMA_HIGH = 21.0

#: The flat top of the block. Flat on purpose: it lets a polyline surface
#: sit a known, tiny distance under the ground over its whole run, which
#: is the geometry that makes the overshoot reproducible.
GROUND_Y = 30.0
SPLIT_Y = 10.0


# ======================================================================
# Fixtures
# ======================================================================
def _block(name="dominio"):
    """A rectangular block, two layers, with the lower one listed FIRST.

    The order is the whole point. ``materials[0]`` is the layer that does
    not touch the ground, so a slice that silently fell back to it can be
    told apart from one that resolved its material honestly. With the
    layers the other way round the substitution would return the right
    answer by luck and these tests would measure nothing.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(100, 0),
        Vertex(100, GROUND_Y), Vertex(0, GROUND_Y),
    ], closed=True)
    ext.ensure_ccw()
    p = Project(name)
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [
        Material(name="Lower", unit_weight=GAMMA_HIGH,
                 strength=MohrCoulomb(cohesion=50, friction_angle=20)),
        Material(name="Upper", unit_weight=GAMMA_LOW,
                 strength=MohrCoulomb(cohesion=5, friction_angle=30)),
    ]
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(-5, SPLIT_Y), Vertex(105, SPLIT_Y)],
                          closed=False),
        btype=BoundaryType.MATERIAL))
    # The upper region has to be CLICKED, or both regions inherit the
    # first material and the two layers become one.
    p.assign_material_at(50.0, SPLIT_Y + 10.0, p.materials[1].id)
    return p


def _polyline_surface(points):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in points], closed=False))


def _grazing_surface():
    """A surface running 0.007 under a flat ground — inside the soil.

    Every slice base is closer to the ground than the 0.01 lift, so every
    material query overshoots. That is the shape of the end slices of any
    near-tangent trial surface; making it thin all the way just takes the
    luck out of the test.
    """
    return _polyline_surface([
        (10.0, GROUND_Y),
        (12.0, GROUND_Y - 0.007),
        (88.0, GROUND_Y - 0.007),
        (90.0, GROUND_Y),
    ])


def _escaping_surface():
    """A surface whose middle sinks well below the floor of the model."""
    return _polyline_surface([
        (10.0, GROUND_Y),
        (50.0, -5.0),
        (90.0, GROUND_Y),
    ])


# ======================================================================
class TestTheQueryDoesNotInventSoil:
    """``_material_at`` outside the model answers None, and says so."""

    def test_a_point_outside_the_model_has_no_material(self):
        from ogr_core.geometry import Vertex
        from ogr_slip2d.slicer import _material_at

        p = _block()
        for pt in ((-1000.0, -1000.0), (1000.0, 1000.0),
                   (50.0, GROUND_Y + 5.0), (50.0, -5.0)):
            assert _material_at(p, Vertex(*pt)) is None, (
                "%s is outside the External Boundary and came back with a "
                "material" % (pt,))

    def test_a_point_inside_still_resolves_its_own_layer(self):
        from ogr_core.geometry import Vertex
        from ogr_slip2d.slicer import _material_at

        p = _block()
        assert _material_at(p, Vertex(50.0, 20.0)).name == "Upper"
        assert _material_at(p, Vertex(50.0, 5.0)).name == "Lower"

    def test_an_unassigned_region_keeps_its_documented_default(self):
        """The OTHER question, which must not change.

        A region inside the model that no click ever claimed resolves to
        the first material by convention. Dropping the fallback outside
        the model has to leave that alone, or the fix would have traded a
        silent answer for a missing one.
        """
        from ogr_core.geometry import Vertex
        from ogr_slip2d.slicer import _material_at

        p = _block()
        p.region_assignments = []          # nobody ever painted anything
        assert _material_at(p, Vertex(50.0, 20.0)) is p.materials[0]
        assert _material_at(p, Vertex(50.0, 5.0)) is p.materials[0]


# ======================================================================
class TestTheLiftDoesNotOvershootTheGround:
    """The live half of the defect: a right base asked in the wrong place."""

    def test_the_geometry_really_does_overshoot(self):
        """Without this the next test could pass by never firing.

        The discriminator is that ``base + 0.01`` leaves the model while
        the base itself does not. If a later change to the lift makes that
        untrue, this has to fail loudly rather than let the next test go
        quietly green on a fixture that no longer reproduces anything.
        """
        from ogr_core.geometry import Vertex
        from ogr_slip2d.slicer import _material_at, slice_surface

        p = _block()
        sl = slice_surface(p, _grazing_surface(), num_slices=40)
        assert sl is not None
        overshoots = 0
        for s in sl.slices:
            base = 0.5 * (s.base_y_left + s.base_y_right)
            if _material_at(p, Vertex(s.x_centre, base + 0.01)) is None:
                assert _material_at(p, Vertex(s.x_centre, base)) is not None
                overshoots += 1
        assert overshoots > 0, (
            "no slice overshot the ground: this fixture no longer "
            "reproduces the defect it was written for")

    def test_a_grazing_base_gets_the_layer_it_is_really_cut_in(self):
        """The 301-out-of-431 case, as an identity.

        The base runs 0.007 under the ground, so it is cut in the UPPER
        layer everywhere. Before v0.1.143 the overshooting query answered
        with ``materials[0]`` — the lower layer — for every one of them.
        """
        from ogr_slip2d.slicer import slice_surface

        p = _block()
        sl = slice_surface(p, _grazing_surface(), num_slices=40)
        assert sl is not None
        wrong = [s.index for s in sl.slices
                 if s.material is None or s.material.name != "Upper"]
        assert not wrong, (
            "slices %s are cut in the upper layer but were given another "
            "material" % wrong[:8])

    def test_the_lift_still_wins_where_it_does_not_overshoot(self):
        """A base ON a contact keeps taking the material ABOVE it.

        The lift exists so that a base running along a material contact
        resolves to the mass it carries instead of landing on a region
        edge where point-in-polygon is ambiguous. Asking at the base is a
        fallback for the overshoot, not a replacement, and this pins that
        ordering.
        """
        from ogr_slip2d.slicer import slice_surface

        p = _block()
        flat = _polyline_surface([
            (10.0, GROUND_Y), (20.0, SPLIT_Y), (80.0, SPLIT_Y),
            (90.0, GROUND_Y)])
        sl = slice_surface(p, flat, num_slices=40)
        assert sl is not None
        on_contact = [s for s in sl.slices
                      if abs(0.5 * (s.base_y_left + s.base_y_right)
                             - SPLIT_Y) < 1e-9]
        assert on_contact, "the fixture no longer runs along the contact"
        assert all(s.material.name == "Upper" for s in on_contact)


# ======================================================================
class TestTheCallerActsOnTheAnswer:
    """A None is refused, not quietly turned back into a material."""

    def test_a_surface_that_leaves_the_soil_is_refused_whole(self):
        from ogr_slip2d.slicer import slice_surface

        p = _block()
        assert slice_surface(p, _escaping_surface(), num_slices=40) is None

    def test_the_refusal_says_which_of_the_causes_it_was(self):
        """Refusing is half the fix; being distinguishable is the other.

        ``slice_surface`` returns None for several unrelated reasons, and
        the search writes a note blaming the slice count for all of them.
        A surface that walked out of the model, told to use more slices,
        is an aviso pointing at the wrong culprit.
        """
        from ogr_slip2d.slicer import REFUSED_OUTSIDE_MODEL, slice_surface

        p = _block()
        why = []
        assert slice_surface(p, _escaping_surface(), num_slices=40,
                             reasons=why) is None
        assert REFUSED_OUTSIDE_MODEL in why

    def test_a_surface_inside_the_soil_is_not_refused(self):
        """The control that keeps the refusal from being vacuous."""
        from ogr_slip2d.slicer import REFUSED_OUTSIDE_MODEL, slice_surface

        p = _block()
        why = []
        sl = slice_surface(p, _grazing_surface(), num_slices=40, reasons=why)
        assert sl is not None and len(sl) >= 3
        assert REFUSED_OUTSIDE_MODEL not in why

    def test_no_slice_survives_with_an_invented_material(self):
        """The substitution must not come back three lines further down."""
        from ogr_core.geometry import Vertex
        from ogr_slip2d.slicer import _material_at, slice_surface

        p = _block()
        for surface in (_grazing_surface(),
                        _polyline_surface([(10.0, GROUND_Y), (50.0, 5.0),
                                           (90.0, GROUND_Y)])):
            sl = slice_surface(p, surface, num_slices=40)
            assert sl is not None
            for s in sl.slices:
                base = 0.5 * (s.base_y_left + s.base_y_right)
                real = (_material_at(p, Vertex(s.x_centre, base + 0.01))
                        or _material_at(p, Vertex(s.x_centre, base)))
                assert s.material is real


# ======================================================================
class TestTheWeightDoesNotInventSoil:
    """A column where there is no soil weighs nothing."""

    def test_a_column_entirely_outside_the_model_weighs_nothing(self):
        from ogr_slip2d.slicer import _column_weight

        p = _block()
        weight, _ = _column_weight(p, -500.0, -500.0, -400.0, 1.0)
        assert weight == 0.0, (
            "100 units of column a thousand units away from the model "
            "weighed %r" % weight)

    def test_a_column_inside_the_model_still_weighs_its_layers(self):
        """The control: the identity the fix must not disturb."""
        from ogr_slip2d.slicer import _column_weight

        p = _block()
        weight, _ = _column_weight(p, 50.0, 0.0, GROUND_Y, 1.0)
        expected = (GAMMA_HIGH * SPLIT_Y
                    + GAMMA_LOW * (GROUND_Y - SPLIT_Y)) * 1.0
        assert weight == pytest.approx(expected, rel=1e-12)

    def test_a_sliver_above_the_ground_takes_the_layer_below_it(self):
        """The mean-elevation artefact, weighed honestly.

        ``_column_weight`` is asked for the column up to the MEAN ground
        elevation over the slice (v0.1.96), so where the ground rises
        across a slice the top band reaches above the ground at ``x``. The
        band is real — the column is that tall on purpose — but its
        material used to be ``materials[0]``, a layer that need not be
        anywhere near the top of the column. It is the layer below it.
        """
        from ogr_slip2d.slicer import _column_weight

        p = _block()
        weight, _ = _column_weight(p, 50.0, 0.0, GROUND_Y + 2.0, 1.0)
        expected = (GAMMA_HIGH * SPLIT_Y
                    + GAMMA_LOW * (GROUND_Y + 2.0 - SPLIT_Y)) * 1.0
        assert weight == pytest.approx(expected, rel=1e-12)


# ======================================================================
class TestTheSearchNamesTheRightCulprit:
    """The two refusals are counted apart, because their remedies differ."""

    def test_the_outside_model_note_is_not_the_slice_count_one(self):
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch

        s = GridSearch(method=get_method("bishop_simplified")())
        s._outside_model = 7
        note = s._outside_model_note()
        assert "7" in note
        assert "outside" in note.lower()
        assert "not a slice-count problem" in note.lower()

    def test_the_note_is_silent_when_nothing_left_the_model(self):
        """Rule 7 the other way round: an aviso that always fires is noise.

        The whole verification bank is analysed without a single surface
        leaving the model, so a note printed unconditionally would be
        wrong on every run that matters.
        """
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch

        p = _block()
        search = GridSearch(method=get_method("bishop_simplified")(),
                            num_slices=20)
        result = search.run(p)
        assert not [n for n in result.notes if "outside" in n.lower()]

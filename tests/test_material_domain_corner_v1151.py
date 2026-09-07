# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A slip surface that daylights exactly ON a vertex of the External Boundary
is a legitimate surface, and refusing it puts a hole in a continuous field.

v0.1.143 taught the slicer to refuse a surface whose base has no soil under
it (D48r), and that judgement is right. What it could not know is that two
comparisons upstream of it are ABSOLUTE where the project convention asks
for a tolerance relative to the size of the model, and that together they
manufacture a base with no soil under it out of a surface that is sitting
in the soil.

Measured on the geometry of USACE (2003) example F-5, defect D64:

    R = 277.9      ->  1.322210      accepted
    R = 277.9964   ->  None          reasons: ['outside_model']
    R = 278.0      ->  1.320817      accepted

A hole 5.8 µm wide in the radius, with an accepted surface on either side
of it — 58 refusals out of 1001 radii swept at 1e-7 around the radius that
passes exactly through the vertex.

WHERE THE HOLE COMES FROM, because neither half is obvious
----------------------------------------------------------
At that radius the circle crosses the ground envelope and the Material
Boundary 3.6e-6 apart — both of them within microns of the vertex the two
share. ``slicer.py`` kept the second crossing as a mandatory cut because
its "a crossing that merely grazes an end" test was an absolute ``1e-9``,
and 3.6e-6 is not a graze by that yardstick even though it is 1.1e-8 of
the failure width. So the first slice was 3.6e-6 wide.

The base midpoint of that sliver then fell outside every region — not
because it left the soil, but because the regions being asked are not the
polygons the user drew. ``_build_regions_shapely`` snap-rounds every node
of the planar subdivision onto a grid of ``diag * 1e-8`` before
polygonising (``ogr_core/geometry/regions.py``), so on this geometry the
corner drawn at (0, 100) is stored at (0, 99.99999733577782) in BOTH
adjacent regions: half a grid cell away, exactly as snap-rounding does.

That measurement is what sizes the fix. The tolerance is not forgiving
float noise; it is clearing the resolution at which the polygons exist:

    1e-9 * diag   a tenth of a cell   does NOT rescue
    1e-8 * diag   one cell            rescues
    1e-6 * diag   a hundred cells     rescues, same factor to six figures

WHAT THESE TESTS DELIBERATELY DO NOT CLAIM
------------------------------------------
* Not that any particular factor is right. The rescued radius is required
  to lie BETWEEN the factors of the radii on either side of it, which is
  continuity of FoS(R), a property of the physics. The one absolute number
  asserted anywhere here is the published 1.332 of USACE (2003) F-5, and
  it is asserted at 1 % on a radius that evaluates today and must keep
  evaluating to the same place.
* Not that the factor is invariant under a change of units. It is not, and
  cannot be: cohesion is not scaled with length, so the same model at
  1/1000 scale is a different problem. What must be invariant is the
  VERDICT — sliced or refused — and that is what the three scales compare.
  With an absolute tolerance they would disagree, which is the point.
* Not that a base outside the model is ever rescued. The third probe goes
  DOWN, and down from below the floor is still below the floor. The
  escaping surfaces are here as controls, refused before and after.
"""

import math

import pytest

# --- USACE (2003) example F-5, the geometry of verification problem 67.
#: The vertex the whole defect is about: the sloping ground meets the flat
#: ground here, and the Material Boundary starts here too.
CORNER = (0.0, 100.0)

EXTERNAL = [(-100.0, 0.0), (400.0, 0.0), (400.0, 150.0), (301.0, 191.0),
            (257.0, 191.0), (174.0, 158.0), CORNER, (-100.0, 100.0)]
CONTACT = [CORNER, (400.0, 100.0)]

CENTRE = (101.0, 359.0)

#: The radius that puts the circle exactly through ``CORNER``: it is
#: ``hypot(101, 259)`` and nothing else, so it is derived here rather than
#: written down, and it moves if the geometry above ever moves.
R_EXACT = math.hypot(CENTRE[0] - CORNER[0], CENTRE[1] - CORNER[1])

#: The radius a user types: ``R_EXACT`` truncated to four decimals,
#: which is what the bank wrote down when it asked "which radius
#: passes through the toe?", and the one the defect was reported on.
R_KNIFE = 277.9964

#: Radii that evaluate today, on both sides of the hole. Nothing here may
#: move: they are the bracket the rescued radius has to land inside.
R_NEIGHBOURS = (277.9, 277.99, 277.996, 278.0, 278.01)

#: The radius the manual publishes for this example, and the factor it
#: publishes with it (USACE 2003, example F-5, Bishop simplified).
R_PUBLISHED = 278.0
FOS_PUBLISHED = 1.332

N_SLICES = 50


# ======================================================================
# Fixtures
# ======================================================================
def _model(mirror=False, scale=1.0, name="d64"):
    """The F-5 embankment, optionally reflected in x and rescaled.

    ``mirror`` exists because the surface daylights on the vertex from the
    LEFT here, and a fix that only worked on one end would pass every test
    written on this model alone. ``scale`` exists because a tolerance that
    is really relative must give the same verdict on the same model
    expressed in different units.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    def t(x, y):
        return ((-x if mirror else x) * scale, y * scale)

    ext = Polyline(vertices=[Vertex(*t(x, y)) for x, y in EXTERNAL],
                   closed=True)
    ext.ensure_ccw()
    p = Project(name)
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    # The embankment is listed FIRST for the same reason v1143 lists the
    # lower layer first: a slice that silently fell back to ``materials[0]``
    # must be tellable from one that resolved its material honestly.
    p.materials = [
        Material(name="embankment", unit_weight=135.0,
                 strength=MohrCoulomb(cohesion=1780.0, friction_angle=5.0)),
        Material(name="foundation", unit_weight=127.0,
                 strength=MohrCoulomb(cohesion=1600.0, friction_angle=2.0)),
    ]
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(*t(x, y)) for x, y in CONTACT],
                          closed=False),
        btype=BoundaryType.MATERIAL))
    # Both regions have to be clicked or they inherit one material and the
    # contact this defect is about stops existing.
    p.assign_material_at(*t(100.0, 120.0), p.materials[0].id)
    p.assign_material_at(*t(100.0, 50.0), p.materials[1].id)
    return p


def _circle(radius, mirror=False, scale=1.0):
    from ogr_slip2d.surface import SlipCircle
    cx = (-CENTRE[0] if mirror else CENTRE[0]) * scale
    return SlipCircle(cx, CENTRE[1] * scale, radius * scale)


def _slice(p, radius, mirror=False, scale=1.0):
    """``(slices, reasons)`` for one radius on one model."""
    from ogr_slip2d.slicer import slice_surface
    why = []
    out = slice_surface(p, _circle(radius, mirror, scale),
                        num_slices=N_SLICES, reasons=why)
    return out, why


def _fos(p, radius, method="bishop_simplified", mirror=False, scale=1.0):
    """The factor of safety on one circle, or None if it was refused."""
    from ogr_slip2d.analysis_runner import build_method
    from ogr_slip2d.search import GridSearch

    g = GridSearch(method=build_method(p, method, N_SLICES),
                   num_slices=N_SLICES, min_area=0.0)
    r = g.evaluate_circle(p, _circle(radius, mirror, scale))
    return None if r is None else float(r.fos)


def _probe_tol(p):
    """The same length the slicer derives, so a test can reach it."""
    x0, y0, x1, y1 = p.bounding_box()
    return 1e-6 * math.hypot(x1 - x0, y1 - y0)


def _flat_bottom_model(width=10000.0, height=10000.0):
    """A model big enough that the new probe is DEEPER than the 0.01 lift.

    On a 10 km square the tolerance is 0.0141, which exceeds the absolute
    0.01 the material query has lifted by since v0.1.59. That makes this
    the sharpest available control on the probe's reach: here it is the
    deepest of the three queries, so if it could rescue an escaping
    surface at all, it would rescue one here.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0.0, 0.0), Vertex(width, 0.0),
        Vertex(width, height), Vertex(0.0, height),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("d64-grande")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="soil", unit_weight=20.0,
        strength=MohrCoulomb(cohesion=50.0, friction_angle=25.0))]
    return p


def _ground_y(p, x):
    """The ground elevation of ``p`` at ``x``, asked of the model itself."""
    from ogr_core.geometry import envelope_y_at
    from ogr_slip2d.slicer import _ground_surface_from_external
    return envelope_y_at(_ground_surface_from_external(
        p.external_boundary()), x)


def _flat_polyline(p, depth):
    """A polyline that daylights on the ground and runs flat at ``depth``.

    ``depth`` is measured from the FLOOR of the model, signed, so a
    negative value is a surface that has left the model underneath —
    which is D48's shape, and the one thing no tolerance here may rescue.
    The ends are put ON the ground rather than at the top of the bounding
    box: a surface that starts in the air is refused for a different
    reason, and a control that fires for the wrong reason is not a control.
    """
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface

    x0, y0, x1, y1 = p.bounding_box()
    a, b = x0 + 0.2 * (x1 - x0), x0 + 0.8 * (x1 - x0)
    span = b - a
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(a, _ground_y(p, a)),
        Vertex(a + 0.05 * span, y0 + depth),
        Vertex(b - 0.05 * span, y0 + depth),
        Vertex(b, _ground_y(p, b)),
    ], closed=False))


# ======================================================================
class TestTheFixtureReproducesTheDefect:
    """Without this, everything below can go green on nothing."""

    def test_the_corner_is_a_vertex_of_both_boundaries(self):
        from ogr_core.geometry import BoundaryType

        p = _model()
        seen = set()
        for b in p.boundaries:
            for v in b.polyline.vertices:
                if (abs(v.x - CORNER[0]) < 1e-12
                        and abs(v.y - CORNER[1]) < 1e-12):
                    seen.add(b.btype)
        assert BoundaryType.EXTERNAL in seen
        assert BoundaryType.MATERIAL in seen

    def test_the_knife_edge_radius_really_passes_through_the_corner(self):
        """It is a knife edge, not a radius picked to be awkward."""
        assert abs(R_KNIFE - R_EXACT) < 1e-5

    def test_the_regions_do_not_store_the_corner_where_it_was_drawn(self):
        """The measurement that sizes the tolerance, kept as an assertion.

        If the region builder ever stops snap-rounding, this fails and the
        derivation behind ``1e-6`` needs rewriting rather than quietly
        surviving as a magic number.
        """
        p = _model()
        x0, y0, x1, y1 = p.bounding_box()
        grid = 1e-8 * math.hypot(x1 - x0, y1 - y0)
        offsets = [
            abs(v.y - CORNER[1])
            for r in p.resolve_regions() for v in r.polygon.vertices
            if abs(v.x - CORNER[0]) < 1e-12
            and abs(v.y - CORNER[1]) < 0.5
        ]
        assert offsets, "the corner is not in any region"
        # moved, but by less than one cell — which is what snapping does
        assert max(offsets) > 0.0
        assert max(offsets) < grid


# ======================================================================
class TestASurfaceDaylightingOnAVertexIsNotRefused:
    """The defect itself. These fail on v0.1.150."""

    def test_the_knife_edge_radius_is_sliced(self):
        from ogr_slip2d.slicer import REFUSED_OUTSIDE_MODEL

        sl, why = _slice(_model(), R_KNIFE)
        assert REFUSED_OUTSIDE_MODEL not in why
        assert sl is not None and len(sl) >= 3

    def test_it_daylights_on_the_vertex_from_the_other_side_too(self):
        """The same model reflected: the vertex is now on the right."""
        from ogr_slip2d.slicer import REFUSED_OUTSIDE_MODEL

        sl, why = _slice(_model(mirror=True), R_KNIFE, mirror=True)
        assert REFUSED_OUTSIDE_MODEL not in why
        assert sl is not None and len(sl) >= 3

    def test_the_mirror_gives_the_same_factor(self):
        """Reflection is an exact symmetry of the problem: an identity."""
        left = _fos(_model(), R_KNIFE)
        right = _fos(_model(mirror=True), R_KNIFE, mirror=True)
        assert left is not None and right is not None
        assert left == pytest.approx(right, rel=1e-9)

    def test_no_sliver_slice_survives(self):
        """The cut 3.6e-6 from the end separated nothing; it made a splinter.

        A slice 1e-8 of the failure width is not a slice, it is a rounding
        error with a material. This is the half of the fix that stops it
        from being built in the first place.
        """
        sl, _ = _slice(_model(), R_KNIFE)
        assert sl is not None
        widths = [s.width for s in sl]
        assert min(widths) > 1e-3 * (sum(widths) / len(widths))


# ======================================================================
class TestTheToleranceIsRelativeToTheModel:
    """The same model in millimetres and in kilometres decides the same."""

    def test_the_verdict_does_not_depend_on_the_units(self):
        from ogr_slip2d.slicer import REFUSED_OUTSIDE_MODEL

        for mirror in (False, True):
            for scale in (0.001, 1.0, 1000.0):
                p = _model(mirror=mirror, scale=scale)
                sl, why = _slice(p, R_KNIFE, mirror=mirror, scale=scale)
                assert REFUSED_OUTSIDE_MODEL not in why, (
                    "refused at scale %g (mirror=%s): the tolerance is "
                    "behaving as an absolute" % (scale, mirror))
                assert sl is not None


# ======================================================================
class TestTheFactorHasNoHoleInIt:
    """Rule 1: the anchor is continuity, not a captured number."""

    def test_the_rescued_radius_lies_between_its_neighbours(self):
        p = _model()
        around = [_fos(p, r) for r in R_NEIGHBOURS]
        assert all(v is not None for v in around)
        here = _fos(p, R_KNIFE)
        assert here is not None
        assert min(around) <= here <= max(around)

    def test_it_lies_between_its_two_IMMEDIATE_neighbours(self):
        """Tighter, and the one that would catch a plausible wrong answer.

        Bracketing by the whole family is satisfied by anything in a wide
        band. Between the two radii that straddle it, it is not.
        """
        p = _model()
        below, above = _fos(p, 277.996), _fos(p, 278.0)
        here = _fos(p, R_KNIFE)
        assert None not in (below, above, here)
        assert above <= here <= below, (
            "%.9f is not between %.9f and %.9f" % (here, above, below))

    def test_the_published_case_still_reproduces(self):
        """USACE (2003) example F-5, Bishop simplified: 1.332 published.

        The external anchor of the whole file. It is asserted on the
        PUBLISHED radius, which evaluates today, so this is the test that
        fails if the fix moved a number it had no business moving.
        """
        got = _fos(_model(), R_PUBLISHED)
        assert got is not None
        assert got == pytest.approx(FOS_PUBLISHED, rel=0.01)


# ======================================================================
class TestTheProbeOnlyGoesDown:
    """D48 and D48r must not reopen. They are anchors, not neighbours."""

    def test_a_surface_below_the_floor_of_the_model_is_still_refused(self):
        from ogr_slip2d.slicer import REFUSED_OUTSIDE_MODEL, slice_surface

        p = _model()
        x0, y0, x1, y1 = p.bounding_box()
        why = []
        assert slice_surface(p, _flat_polyline(p, -0.5 * (y1 - y0)),
                             num_slices=40, reasons=why) is None
        assert REFUSED_OUTSIDE_MODEL in why

    def test_the_refusal_holds_where_the_probe_is_deeper_than_the_lift(self):
        """On a 10 km model the probe (0.0141) exceeds the 0.01 lift.

        So here the new query is the deepest of the three, and if it could
        reach past its own tolerance this is where it would show.
        """
        from ogr_slip2d.slicer import REFUSED_OUTSIDE_MODEL, slice_surface

        p = _flat_bottom_model()
        tol = _probe_tol(p)
        assert tol > 0.01, "the fixture no longer makes the probe the deepest"
        for k in (0.9, 1.5, 100.0):
            why = []
            assert slice_surface(p, _flat_polyline(p, -k * tol),
                                 num_slices=40, reasons=why) is None, (
                "accepted a surface %g tolerances under the floor" % k)
            assert REFUSED_OUTSIDE_MODEL in why

    def test_a_surface_just_under_the_floor_is_still_accepted(self):
        """The control that keeps the three above from being vacuous.

        Half a tolerance under the floor the 0.01 lift has always found
        soil, and it still must: nothing here is allowed to make the
        slicer STRICTER than it was.
        """
        from ogr_slip2d.slicer import REFUSED_OUTSIDE_MODEL, slice_surface

        p = _flat_bottom_model()
        why = []
        sl = slice_surface(p, _flat_polyline(p, -0.5 * _probe_tol(p)),
                           num_slices=40, reasons=why)
        assert sl is not None
        assert REFUSED_OUTSIDE_MODEL not in why


# ======================================================================
class TestTheThirdProbeIsBoundedAndSaysSo:
    """The backstop, addressed directly.

    On the F-5 geometry the third probe does not fire once the splinter is
    gone — measured, 58 rescues with only the second half of the fix and 0
    with both. That is not because it is dead code: on verification problem
    14 of the bank it answers 42 slice bases in a single Bishop search. It
    is exercised HERE, on the function, because a backstop reached only by
    a geometry the OTHER half of the fix now prevents is a backstop no test
    on this fixture could ever reach — and one nothing tests is one nobody
    can trust.
    """

    def test_a_base_on_the_ground_resolves_to_the_soil_under_it(self):
        from ogr_slip2d.slicer import _base_material

        p = _model()
        why = []
        mat = _base_material(p, 200.0, 100.0, _probe_tol(p), reasons=why)
        assert mat is not None

    def test_a_base_in_the_air_still_has_no_soil(self):
        """The bound. Without it the tolerance is unlimited."""
        from ogr_slip2d.slicer import _base_material

        p = _model()
        tol = _probe_tol(p)
        # a metre above the crest is not a tangency by any yardstick
        assert _base_material(p, 200.0, 192.0, tol, reasons=[]) is None

    def test_the_probe_reaches_exactly_as_far_as_its_tolerance(self):
        """Half a tolerance above the ground: soil. Ten: none.

        Above the GROUND and not below the floor, because that is the only
        edge where the third probe can be the one that answers: under the
        floor the soil is overhead, and the 0.01 lift has always found it.
        """
        from ogr_slip2d.slicer import _base_material

        p = _flat_bottom_model()
        tol = _probe_tol(p)
        x0, y0, x1, y1 = p.bounding_box()
        x = 0.5 * (x0 + x1)
        assert _base_material(p, x, y1 + 0.5 * tol, tol,
                              reasons=[]) is not None
        assert _base_material(p, x, y1 + 10.0 * tol, tol, reasons=[]) is None

    def test_the_rescue_is_announced(self):
        from ogr_slip2d.slicer import TOUCHED_MODEL_EDGE, _base_material

        p = _flat_bottom_model()
        tol = _probe_tol(p)
        x0, y0, x1, y1 = p.bounding_box()
        x = 0.5 * (x0 + x1)

        why = []
        # deep inside the soil: the lift answers, nothing to announce
        assert _base_material(p, x, 0.5 * (y0 + y1), tol,
                              reasons=why) is not None
        assert TOUCHED_MODEL_EDGE not in why

        why = []
        # on the very edge: only the downward probe can answer
        assert _base_material(p, x, y1 + 0.5 * tol, tol,
                              reasons=why) is not None
        assert TOUCHED_MODEL_EDGE in why


# ======================================================================
class TestTheSearchTellsTheUser:
    """Rule 7's shape: the note exists, names the count, and stays quiet."""

    def test_the_note_names_how_many_and_what_happened(self):
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch

        s = GridSearch(method=get_method("bishop_simplified")())
        s._on_model_edge = 5
        note = s._on_model_edge_note()
        assert "5" in note
        assert "edge" in note.lower() or "boundary" in note.lower()

    def test_it_is_not_the_outside_model_note(self):
        """The two remedies are opposite; the notes must not be confusable."""
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.search import GridSearch

        s = GridSearch(method=get_method("bishop_simplified")())
        s._on_model_edge = 3
        s._outside_model = 3
        assert s._on_model_edge_note() != s._outside_model_note()

    def test_the_note_is_silent_when_it_did_not_happen(self):
        p = _model()
        from ogr_slip2d.analysis_runner import build_method
        from ogr_slip2d.search import GridSearch

        g = GridSearch(method=build_method(p, "bishop_simplified", N_SLICES),
                       num_slices=N_SLICES, min_area=0.0)
        g.evaluate_circle(p, _circle(R_PUBLISHED))
        assert getattr(g, "_on_model_edge", 0) == 0

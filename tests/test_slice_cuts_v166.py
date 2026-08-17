# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Where the slip surface changes layer is a mandatory slice boundary.

Until v0.1.66 the slice boundaries were a uniform division of the failure
width and nothing else. A slice whose base crossed a material boundary had
to pick ONE material for the whole base — the one under its midpoint — so
part of its base was given a cohesion and a friction angle belonging to the
other layer. v0.1.63 fixed the WEIGHT of such a slice by integrating its
column; this fixes its BASE, which is where the shear strength and the pore
pressure are evaluated.

**The validation cases do not protect this change, and that is the point
worth recording.** ej1 has three materials and two material boundaries, and
its critical circle crosses neither: measured, the slice widths come out
identical to the uniform ones (1.1464 m, all 25 of them) and the three
factors of safety do not move in the sixth digit. The same thing happened
in v0.1.63, for a different reason (there, all three materials shared
γ = 20). A reference case that exercises nothing is not evidence, so the
fixtures below are built to cross on purpose.

The anchors:

  * **Geometric identity.** If a cut is placed where the surface crosses,
    then evaluating the material at the base midpoint of every slice must
    give a partition: no slice may have a base that starts in one layer and
    ends in another. That is checkable directly, without knowing any factor
    of safety.
  * **The cut is where the surfaces meet.** The abscissa found must satisfy
    ``base_y(x) == boundary_y(x)`` to numerical precision — a root, not an
    approximation.
  * **Conservation.** The requested number of slices is still delivered,
    and the slices still tile the failure width exactly.
  * **Rule 7 for the change itself**: with a layer crossing, the resulting
    factor of safety must differ from the uniform-slicing one. If it did
    not, the change would be decoration.
"""
from __future__ import annotations

import math

SPLIT_Y = 6.0     # horizontal material boundary
WEAK_C = 2.0      # lower layer: weak
STRONG_C = 60.0   # upper layer: strong


# ======================================================================
def _crossing_project():
    """A slope whose critical arc genuinely cuts a material boundary.

    The boundary is horizontal at y = 6 and the arc runs below it over its
    lower stretch and above it near the crest, so the base changes layer
    once. Only once, and that is geometry rather than choice: the arc
    daylights at the toe, at y = 0, which is already under the boundary,
    so it cannot start above it. The many-cut case is covered by the
    ten-layer test further down.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    # v0.1.89 — 10 m of foundation. Without it the stretch from x = 0 to
    # the toe at x = 30 encloses no soil. Not listed among the five in
    # docs/PENDIENTES.md — the inventory there was made by hand.
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, 12),
        Vertex(50, 12), Vertex(30, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("cut")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(0, SPLIT_Y), Vertex(60, SPLIT_Y)],
                          closed=False),
        btype=BoundaryType.MATERIAL))
    upper = Material(name="Upper", unit_weight=19,
                     strength=MohrCoulomb(cohesion=STRONG_C,
                                          friction_angle=30))
    lower = Material(name="Lower", unit_weight=19,
                     strength=MohrCoulomb(cohesion=WEAK_C,
                                          friction_angle=15))
    p.materials = [upper, lower]
    # The click points must be INSIDE the model. x = 30 is the toe, where
    # the slope has zero height, so clicking there assigns nothing and
    # both regions silently keep the default material — which is how the
    # first version of this fixture came to have one layer while looking
    # like it had two.
    assert p.assign_material_at(55.0, SPLIT_Y - 3.0, lower.id)
    assert p.assign_material_at(55.0, SPLIT_Y + 3.0, upper.id)
    return p


def _arc():
    from ogr_slip2d.surface import SlipCircle
    # Dips to y ≈ 3.5 at its lowest, well under the boundary at y = 6.
    return SlipCircle(centre_x=40.0, centre_y=21.0, radius=17.5)


def _uniform_bounds(project, surface, x_l, x_r, num_slices):
    step = (x_r - x_l) / num_slices
    return [x_l + step * i for i in range(num_slices + 1)]


def _slices(p, n=25, uniform=False):
    import ogr_slip2d.slicer as S
    if not uniform:
        return S.slice_surface(p, _arc(), num_slices=n)
    real = S._slice_boundaries
    S._slice_boundaries = _uniform_bounds
    try:
        return S.slice_surface(p, _arc(), num_slices=n)
    finally:
        S._slice_boundaries = real


def _base_materials(p, s):
    """Material just above the base at 5 % and 95 % along the slice.

    Not at the very ends: the outermost slice daylights exactly on the
    external boundary, where a point-in-polygon query legitimately answers
    None. Sampling a little inside asks the question the test means — does
    the base of THIS slice sit in one layer — without depending on how the
    boundary itself is classified.
    """
    out = []
    for f in (0.05, 0.95):
        x = s.base_x_left + f * s.width
        y = s.base_y_left + f * (s.base_y_right - s.base_y_left)
        out.append(p.material_at(x, y + 1e-4))
    return out


# ======================================================================
class TestTheFixtureActuallyCrosses:
    """Guard the guard: if the arc stopped crossing, every test below
    would pass while measuring nothing — which is exactly how ej1 came to
    look like a validation of this change."""

    def test_the_base_really_changes_layer(self):
        sl = _slices(_crossing_project())
        assert sl is not None
        below = [s for s in sl.slices if s.base_y_mid < SPLIT_Y]
        above = [s for s in sl.slices if s.base_y_mid > SPLIT_Y]
        assert below and above, (len(below), len(above))


class TestTheCutLandsOnTheCrossing:
    def test_the_boundary_abscissas_are_roots(self):
        from ogr_slip2d.slicer import _surface_crossings
        p = _crossing_project()
        wall = [b for b in p.boundaries
                if b.polyline.vertices[0].y == SPLIT_Y][0]
        sl = _slices(p)
        x_l = sl.slices[0].base_x_left
        x_r = sl.slices[-1].base_x_right
        xs = _surface_crossings(_arc(), wall.polyline, x_l, x_r)
        assert len(xs) == 1, xs
        for x in xs:
            # A root of base_y(x) − boundary_y(x), not an approximation.
            assert abs(_arc().base_y_at(x) - SPLIT_Y) < 1e-9, x

    def test_every_crossing_is_a_slice_boundary(self):
        from ogr_slip2d.slicer import _surface_crossings
        p = _crossing_project()
        wall = [b for b in p.boundaries
                if b.polyline.vertices[0].y == SPLIT_Y][0]
        sl = _slices(p)
        edges = ([s.base_x_left for s in sl.slices]
                 + [sl.slices[-1].base_x_right])
        xs = _surface_crossings(_arc(), wall.polyline,
                                sl.slices[0].base_x_left,
                                sl.slices[-1].base_x_right)
        for x in xs:
            assert min(abs(e - x) for e in edges) < 1e-6, (x, edges)


class TestNoSliceStraddlesALayer:
    """The geometric identity, and the reason the change exists."""

    def test_each_base_lies_wholly_in_one_material(self):
        p = _crossing_project()
        sl = _slices(p)
        for s in sl.slices:
            a, b = _base_materials(p, s)
            assert a is not None and b is not None, (s.index, s.x_centre)
            assert a.id == b.id, (s.index, s.x_centre, a.name, b.name)

    def test_uniform_slicing_does_straddle(self):
        """The bug, still reachable through the old path — so the test
        above is measuring something rather than passing by luck."""
        p = _crossing_project()
        sl = _slices(p, uniform=True)
        straddling = 0
        for s in sl.slices:
            a, b = _base_materials(p, s)
            if a is not None and b is not None and a.id != b.id:
                straddling += 1
        assert straddling > 0


class TestTheSlicesStillTileTheMass:
    def test_the_requested_count_is_delivered(self):
        for n in (10, 25, 40):
            sl = _slices(_crossing_project(), n=n)
            assert len(sl.slices) == n, (n, len(sl.slices))

    def test_the_slices_are_contiguous_and_cover_the_width(self):
        sl = _slices(_crossing_project())
        for a, b in zip(sl.slices[:-1], sl.slices[1:]):
            assert abs(a.base_x_right - b.base_x_left) < 1e-12
        total = sum(s.width for s in sl.slices)
        span = sl.slices[-1].base_x_right - sl.slices[0].base_x_left
        assert abs(total - span) < 1e-9

    def test_without_any_crossing_the_division_is_still_uniform(self):
        """No mandatory cut ⇒ the old behaviour, bit for bit. This is what
        keeps every model that does not cross a layer unchanged."""
        from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                        Vertex)
        p = _crossing_project()
        # Replace the boundary with one far below the arc. Vertices are
        # frozen, so this builds a new one rather than moving the old.
        p.boundaries = [b for b in p.boundaries
                        if b.btype != BoundaryType.MATERIAL]
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(0, -50.0), Vertex(60, -50.0)],
                              closed=False),
            btype=BoundaryType.MATERIAL))
        sl = _slices(p)
        w = [s.width for s in sl.slices]
        assert max(w) - min(w) < 1e-12


class TestItMovesTheNumber:
    """Rule 7 applied to the change itself."""

    def test_the_factor_of_safety_differs_from_uniform_slicing(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        p = _crossing_project()
        cut = BishopSimplified().compute_fos(p, _arc(), _slices(p)).fos
        uni = BishopSimplified().compute_fos(
            p, _arc(), _slices(p, uniform=True)).fos
        assert math.isfinite(cut) and math.isfinite(uni)
        assert abs(cut - uni) / uni > 1e-3, (cut, uni)


class TestRefusalsAreExplicit:
    def test_more_cuts_than_slices_is_refused(self):
        """The reference reports this rather than dropping crossings, and
        the fix is to ask for more slices, not to hide the layers."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        p = _crossing_project()
        # Ten thin layers slicing through the arc.
        for k in range(10):
            y = 3.0 + 0.4 * k
            p.add_boundary(Boundary(
                polyline=Polyline(
                    vertices=[Vertex(0, y), Vertex(60, y)], closed=False),
                btype=BoundaryType.MATERIAL))
        assert _slices(p, n=4) is None
        # With enough slices to spend, it works again.
        assert _slices(p, n=40) is not None

    def test_near_coincident_cuts_merge_relative_to_the_model(self):
        """Two layers pinching out at nearly the same abscissa are one
        cut. The tolerance is a fraction of the failure width, so the
        behaviour is the same whether the model is in metres or in
        millimetres — the convention this project uses everywhere."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        p = _crossing_project()
        # A second boundary a hair above the first.
        p.add_boundary(Boundary(
            polyline=Polyline(
                vertices=[Vertex(0, SPLIT_Y + 1e-4),
                          Vertex(60, SPLIT_Y + 1e-4)], closed=False),
            btype=BoundaryType.MATERIAL))
        sl = _slices(p)
        assert sl is not None
        assert len(sl.slices) == 25

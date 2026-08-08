# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The weight of a slice is the integral of its column, not one γ times its
height.

Until v0.1.63 the slicer classified each slice WHOLE by its base midpoint:
one unit weight over the full height, and the material of the base for the
entire column. Two consequences, both silent:

  * a slice spanning two layers weighed as if it were made entirely of the
    material under its base — and the module docstring claimed the
    opposite, that weights were composed by intersecting each slice with
    every material boundary;
  * a slice straddling the water table got either γ or γsat for all of it,
    the choice hinging on which side of the surface its base midpoint
    happened to fall.

Every anchor below is an ANALYTIC IDENTITY, never a captured number. The
column weight is Σ γ_i·Δh_i·dx, linear in each γ and in each band height,
so all of these can be written out by hand:

  * a column with two layers of known thickness has a weight that equals
    the thickness-weighted sum, exactly;
  * splitting a HOMOGENEOUS column with a boundary that changes nothing
    must leave the weight bit-for-bit identical — the cut is real, the
    physics is not;
  * a column half below the water table weighs γ·h/2 + γsat·h/2 exactly;
  * and the total weight of the mass cannot depend on how many slices it
    was cut into, beyond the discretisation of the ground surface.

The last group guards the direction that matters most: a model with ONE
material and no water table must come out of this change unchanged, since
that is what the seven LEM validation cases are.
"""
from __future__ import annotations

GAMMA_TOP = 16.0
GAMMA_BOT = 22.0
GAMMA_SAT = 24.0


# ======================================================================
# Fixtures
# ======================================================================
def _base_project(name="col"):
    """A rectangular block with a sloping face, one material, no water."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(60, 0), Vertex(60, 10),
        Vertex(35, 10), Vertex(15, 30), Vertex(0, 30),
    ], closed=True)
    ext.ensure_ccw()
    p = Project(name)
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="Bulk",
        strength=MohrCoulomb(cohesion=20, friction_angle=25),
        unit_weight=GAMMA_BOT,
        sat_unit_weight=GAMMA_SAT,
        use_sat_unit_weight=True,
    )]
    return p


def _horizontal(p, btype, y: float):
    from ogr_core.geometry import Boundary, Polyline, Vertex
    b = Boundary(
        polyline=Polyline(vertices=[Vertex(-5, y), Vertex(65, y)],
                          closed=False),
        btype=btype,
    )
    p.add_boundary(b)
    return b


def _two_layers(p, split_y: float):
    """Add a horizontal material boundary and a lighter upper material.

    The upper layer is assigned by a click point, which is how the model
    resolves regions; without it both regions inherit the first material
    and the test would measure nothing.
    """
    from ogr_core.geometry import BoundaryType
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb

    _horizontal(p, BoundaryType.MATERIAL, split_y)
    top = Material(
        name="Top",
        strength=MohrCoulomb(cohesion=5, friction_angle=30),
        unit_weight=GAMMA_TOP,
        sat_unit_weight=GAMMA_SAT,
        use_sat_unit_weight=True,
    )
    p.materials.append(top)
    # Click well inside the upper region, in the tall part of the block.
    p.assign_material_at(5.0, split_y + 5.0, top.id)
    return top


def _column(p, x, y0, y1, dx=1.0):
    from ogr_slip2d.slicer import _column_weight
    return _column_weight(p, x, y0, y1, dx)


# ======================================================================
class TestASingleLayerColumnIsUnchanged:
    """The regression direction: one material, no water ⇒ γ·h·dx."""

    def test_weight_is_gamma_times_height(self):
        p = _base_project()
        w = _column(p, 5.0, 0.0, 30.0, dx=2.0)
        assert abs(w - GAMMA_BOT * 30.0 * 2.0) < 1e-9

    def test_a_boundary_that_changes_nothing_changes_nothing(self):
        """A material boundary with the SAME material on both sides cuts
        the column in two but must not move the weight by a single bit.

        This separates "the cut happened" from "the cut mattered": if the
        band loop were wrong — double counting a band, or losing one to a
        tolerance — this is where it shows, with no γ difference to hide
        behind.
        """
        from ogr_core.geometry import BoundaryType
        p = _base_project()
        before = _column(p, 5.0, 0.0, 30.0, dx=2.0)
        _horizontal(p, BoundaryType.MATERIAL, 12.0)
        after = _column(p, 5.0, 0.0, 30.0, dx=2.0)
        assert after == before


class TestLayersAreWeighedSeparately:
    """The bug: a column crossing a layer boundary used one γ throughout."""

    def test_weight_is_the_thickness_weighted_sum(self):
        p = _base_project()
        _two_layers(p, split_y=12.0)
        # 12 m of the heavy material below, 18 m of the light one above.
        w = _column(p, 5.0, 0.0, 30.0, dx=2.0)
        expected = (GAMMA_BOT * 12.0 + GAMMA_TOP * 18.0) * 2.0
        assert abs(w - expected) < 1e-9

    def test_a_column_entirely_inside_one_layer_uses_only_that_gamma(self):
        p = _base_project()
        _two_layers(p, split_y=12.0)
        w = _column(p, 5.0, 15.0, 25.0, dx=1.0)
        assert abs(w - GAMMA_TOP * 10.0) < 1e-9
        w = _column(p, 5.0, 2.0, 8.0, dx=1.0)
        assert abs(w - GAMMA_BOT * 6.0) < 1e-9

    def test_the_split_is_additive(self):
        """Cutting the same column anywhere and adding the parts gives the
        whole. True of any integral, and it holds across the layer cut."""
        p = _base_project()
        _two_layers(p, split_y=12.0)
        whole = _column(p, 5.0, 0.0, 30.0, dx=1.0)
        parts = (_column(p, 5.0, 0.0, 7.0, dx=1.0)
                 + _column(p, 5.0, 7.0, 20.0, dx=1.0)
                 + _column(p, 5.0, 20.0, 30.0, dx=1.0))
        assert abs(whole - parts) < 1e-9


class TestTheWaterTableSplitsTheColumn:
    """The other half of the bug: γ or γsat for the whole slice."""

    def test_half_submerged_column_uses_both_unit_weights(self):
        from ogr_core.geometry import BoundaryType
        p = _base_project()
        _horizontal(p, BoundaryType.WATER_TABLE, 15.0)
        w = _column(p, 5.0, 0.0, 30.0, dx=1.0)
        expected = GAMMA_SAT * 15.0 + GAMMA_BOT * 15.0
        assert abs(w - expected) < 1e-9

    def test_fully_submerged_still_uses_gamma_sat_throughout(self):
        """The case the v0.1.60 tests pin: a water table at or above the
        ground. It must be untouched by this change."""
        from ogr_core.geometry import BoundaryType
        p = _base_project()
        _horizontal(p, BoundaryType.WATER_TABLE, 40.0)
        w = _column(p, 5.0, 0.0, 30.0, dx=1.0)
        assert abs(w - GAMMA_SAT * 30.0) < 1e-9

    def test_a_dry_column_ignores_a_water_table_below_it(self):
        from ogr_core.geometry import BoundaryType
        p = _base_project()
        _horizontal(p, BoundaryType.WATER_TABLE, 3.0)
        w = _column(p, 5.0, 10.0, 30.0, dx=1.0)
        assert abs(w - GAMMA_BOT * 20.0) < 1e-9

    def test_a_piezometric_line_does_not_saturate_anything(self):
        """Only a water table decides the unit weight — the first of the
        three documented NF ↔ piezometric differences."""
        from ogr_core.geometry import BoundaryType
        p = _base_project()
        _horizontal(p, BoundaryType.PIEZOMETRIC, 15.0)
        w = _column(p, 5.0, 0.0, 30.0, dx=1.0)
        assert abs(w - GAMMA_BOT * 30.0) < 1e-9

    def test_layers_and_water_table_compose(self):
        """Four bands: two layers cut by a water table between them."""
        from ogr_core.geometry import BoundaryType
        p = _base_project()
        _two_layers(p, split_y=12.0)
        _horizontal(p, BoundaryType.WATER_TABLE, 20.0)
        w = _column(p, 5.0, 0.0, 30.0, dx=1.0)
        expected = (
            GAMMA_SAT * 12.0            # heavy layer, submerged
            + GAMMA_SAT * 8.0           # light layer, submerged (12 → 20)
            + GAMMA_TOP * 10.0          # light layer, dry (20 → 30)
        )
        assert abs(w - expected) < 1e-9


class TestFoldedBoundariesAreNotLost:
    """A material boundary may cross the same column twice."""

    def test_all_crossings_are_returned(self):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.slicer import _polyline_crossings_at_x
        # A V that dips down and comes back up crosses x = 10 twice.
        pl = Polyline(vertices=[
            Vertex(0, 20), Vertex(20, 5), Vertex(0, 2),
        ], closed=False)
        ys = sorted(_polyline_crossings_at_x(pl, 10.0))
        assert len(ys) == 2
        # Straight-line interpolation on each leg: 20→5 over 0→20 gives
        # 12.5 at x = 10; 5→2 over 20→0 gives 3.5 at x = 10.
        assert abs(ys[0] - 3.5) < 1e-9
        assert abs(ys[1] - 12.5) < 1e-9

    def test_a_vertical_segment_contributes_no_cut(self):
        """It lies along the column instead of cutting it; treating its
        endpoints as cuts would invent bands."""
        from ogr_core.geometry import Polyline, Vertex
        from ogr_slip2d.slicer import _polyline_crossings_at_x
        pl = Polyline(vertices=[Vertex(10, 0), Vertex(10, 20)],
                      closed=False)
        assert _polyline_crossings_at_x(pl, 10.0) == []


class TestTheSlicerUsesIt:
    """End to end, through ``slice_surface``."""

    def _circle(self):
        from ogr_slip2d.surface import SlipCircle
        return SlipCircle(centre_x=25.0, centre_y=40.0, radius=25.0)

    def _total(self, p, n=25):
        from ogr_slip2d.slicer import slice_surface
        sl = slice_surface(p, self._circle(), num_slices=n)
        assert sl is not None
        return sum(s.weight for s in sl.slices)

    def test_a_lighter_upper_layer_lowers_the_total_weight(self):
        p = _base_project()
        heavy = self._total(p)
        q = _base_project()
        _two_layers(q, split_y=12.0)
        light = self._total(q)
        # γ_top < γ_bot, and part of the mass sits above y = 12.
        assert light < heavy

    def test_total_weight_is_stable_under_refinement(self):
        """Doubling the slice count may not change the mass by more than
        the ground-surface discretisation. A per-slice weight bug shows up
        here as a count-dependent total."""
        p = _base_project()
        _two_layers(p, split_y=12.0)
        w25 = self._total(p, 25)
        w100 = self._total(p, 100)
        assert abs(w100 - w25) / w25 < 0.02

    def test_one_material_no_water_matches_the_closed_form(self):
        """The regression guard for the validation cases: with a single
        material the slicer must still reduce to Σ γ·h·dx."""
        from ogr_slip2d.slicer import slice_surface
        p = _base_project()
        sl = slice_surface(p, self._circle(), num_slices=25)
        assert sl is not None
        for s in sl.slices:
            assert abs(s.weight - GAMMA_BOT * s.height * s.width) < 1e-9

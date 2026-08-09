# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Excess pore pressure from undrained loading, and line loads that finally load.

Two things land together here because the first is a prerequisite of the
second: a load cannot generate excess pore pressure in a program that
does not know the load exists.

**Line loads reached nothing.** Until v0.1.75 the limit-equilibrium
engine contained no reference at all to line loads. They could be drawn,
saved, exported to DXF and factored by a design standard, and the
analysis never read them. Measured before the fix: a line load of
**5000 kN/m** moved the factor of safety by **exactly zero**, while the
equivalent distributed load moved it from 1.2189 to 0.8392. It failed on
the unsafe side, because the user believes the slope has been loaded.

**Excess pore pressure** is Skempton (1954): Δu = B̄·Δσv, added to the
initial pore pressure. The stress model is ONE-DIMENSIONAL and does not
spread — Δσv is what is added directly above, transmitted straight down,
undiminished with depth. That is not a simplification invented here; the
reference states it, and its tutorial computes exactly this.

The anchors below are analytic identities and reproductions of the
reference's own worked example, never captured output:

1. a uniform load q with B̄ = 1 must give Δu = q **exactly, at every
   depth** — which is the whole no-spreading claim in one assertion;
2. an embankment of γ = 21 over 10 m must give Δu = 210 kPa in the clay
   beneath, and **zero within itself** when its own B̄ = 0 — the case the
   reference's tutorial walks through in words;
3. B̄ = 0 must give exactly zero however much load arrives;
4. a line load of P must produce the same factor of safety as a
   distributed load whose integral is P over the same slice.
"""
from __future__ import annotations

import math


# ======================================================================
# Fixtures
# ======================================================================
def _slope():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(60, 0), Vertex(60, 10),
        Vertex(35, 10), Vertex(15, 30), Vertex(0, 30),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("excess")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(
        name="Soil", strength=MohrCoulomb(cohesion=10, friction_angle=25))]
    return p


def _circle():
    from ogr_slip2d import SlipCircle
    return SlipCircle(centre_x=35, centre_y=42, radius=35)


def _fos(project, num_slices=25):
    from ogr_slip2d import slice_surface
    from ogr_slip2d.methods import BishopSimplified

    circle = _circle()
    sl = slice_surface(project, circle, num_slices=num_slices)
    assert sl is not None
    return BishopSimplified().compute_fos(project, circle, sl).fos


def _block(b_bar=1.0):
    """A flat 100 x 30 block of one material — the 1-D column."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(100, 0), Vertex(100, 30), Vertex(0, 30),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("column")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    m = Material(name="clay",
                 strength=MohrCoulomb(cohesion=10, friction_angle=20))
    m.b_bar = b_bar
    p.materials = [m]
    p.settings.groundwater.set_advanced_option("excess_pore_pressure")
    return p, m


def _uniform_load(project, q, x0=10.0, x1=90.0, marked=True):
    from ogr_core.geometry import Vertex
    from ogr_core.loads import DistributedLoad
    from ogr_core.loads.loads import LoadOrientation

    project.distributed_loads.append(DistributedLoad(
        start=Vertex(x0, 30), end=Vertex(x1, 30), magnitude_1=q,
        orientation=LoadOrientation.VERTICAL,
        creates_excess_pore_pressure=marked))


# ======================================================================
# 1. The one-dimensional identity
# ======================================================================
class TestAUniformLoadTransmitsItselfUndiminished:
    """Δu = B̄·q, at every depth. The no-spreading claim, asserted."""

    def test_delta_u_equals_q_exactly_at_every_depth(self):
        from ogr_core.hydraulic.excess_pore_pressure import excess_at
        p, m = _block(b_bar=1.0)
        q = 37.0
        _uniform_load(p, q)
        for depth in (0.5, 1.0, 10.0, 25.0, 29.5):
            du = excess_at(p, m, 50.0, 30.0 - depth, 30.0)
            assert abs(du - q) < 1e-12, (depth, du)

    def test_b_bar_scales_it_linearly(self):
        from ogr_core.hydraulic.excess_pore_pressure import excess_at
        q = 37.0
        for b_bar in (0.25, 0.5, 0.75, 1.0, 1.4):
            p, m = _block(b_bar=b_bar)
            _uniform_load(p, q)
            du = excess_at(p, m, 50.0, 20.0, 30.0)
            assert abs(du - b_bar * q) < 1e-12, (b_bar, du)

    def test_a_free_draining_material_develops_none(self):
        """B̄ = 0 is free-draining BY DEFINITION, so no amount of load
        can produce excess. The reference says so in as many words."""
        from ogr_core.hydraulic.excess_pore_pressure import excess_at
        p, m = _block(b_bar=0.0)
        _uniform_load(p, 5000.0)
        assert excess_at(p, m, 50.0, 20.0, 30.0) == 0.0

    def test_an_unmarked_load_contributes_nothing(self):
        from ogr_core.hydraulic.excess_pore_pressure import excess_at
        p, m = _block(b_bar=1.0)
        _uniform_load(p, 37.0, marked=False)
        assert excess_at(p, m, 50.0, 20.0, 30.0) == 0.0

    def test_nothing_happens_outside_the_load(self):
        from ogr_core.hydraulic.excess_pore_pressure import excess_at
        p, m = _block(b_bar=1.0)
        _uniform_load(p, 37.0, x0=40.0, x1=60.0)
        assert excess_at(p, m, 5.0, 20.0, 30.0) == 0.0
        assert abs(excess_at(p, m, 50.0, 20.0, 30.0) - 37.0) < 1e-12

    def test_the_option_gates_everything(self):
        """Rule 7 for the switch itself: with the advanced option off,
        no excess exists however the materials and loads are set."""
        from ogr_core.hydraulic.excess_pore_pressure import excess_at
        p, m = _block(b_bar=1.0)
        _uniform_load(p, 37.0)
        p.settings.groundwater.set_advanced_option(None)
        assert excess_at(p, m, 50.0, 20.0, 30.0) == 0.0


# ======================================================================
# 2. The reference's own worked example
# ======================================================================
def _embankment_over_clay():
    """Embankment γ = 21 over 10 m, on a clay foundation with B̄ = 1.

    Reproduces in geometry what the reference's tutorial describes in
    words, including the detail that makes the two flags distinct: the
    embankment LOADS what is under it while developing no excess within
    itself, because its own B̄ is zero.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(100, 0), Vertex(100, 30), Vertex(0, 30),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("embankment")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(0, 20), Vertex(100, 20)],
                          closed=False),
        btype=BoundaryType.MATERIAL))

    emb = Material(name="embankment", unit_weight=21.0,
                   strength=MohrCoulomb(cohesion=5, friction_angle=32))
    emb.weight_creates_excess = True
    emb.b_bar = 0.0
    clay = Material(name="clay", unit_weight=18.0,
                    strength=MohrCoulomb(cohesion=20, friction_angle=0))
    clay.b_bar = 1.0
    p.materials = [emb, clay]
    assert p.assign_material_at(50, 25, emb.id)
    assert p.assign_material_at(50, 10, clay.id)
    p.settings.groundwater.set_advanced_option("excess_pore_pressure")
    return p, emb, clay


class TestTheEmbankmentCase:

    def test_the_clay_carries_the_full_embankment_weight(self):
        """γ·h = 21 × 10 = 210 kPa, and the same at every depth in the
        clay, because the stress does not spread."""
        from ogr_core.hydraulic.excess_pore_pressure import excess_at
        p, _emb, clay = _embankment_over_clay()
        for y in (19.0, 15.0, 5.0, 0.5):
            du = excess_at(p, clay, 50.0, y, 30.0)
            assert abs(du - 210.0) < 1e-9, (y, du)

    def test_the_embankment_develops_none_within_itself(self):
        """Its own B̄ = 0. The two flags answer different questions, and
        this is the case that separates them."""
        from ogr_core.hydraulic.excess_pore_pressure import excess_at
        p, emb, _clay = _embankment_over_clay()
        assert emb.weight_creates_excess is True
        assert excess_at(p, emb, 50.0, 25.0, 30.0) == 0.0

    def test_unticking_the_weight_flag_removes_the_load(self):
        """The reference's own additional exercise: turn the material
        weight off and only the external loads remain."""
        from ogr_core.hydraulic.excess_pore_pressure import excess_at
        p, emb, clay = _embankment_over_clay()
        emb.weight_creates_excess = False
        assert excess_at(p, clay, 50.0, 10.0, 30.0) == 0.0

    def test_load_and_weight_add_up(self):
        from ogr_core.hydraulic.excess_pore_pressure import excess_at
        p, _emb, clay = _embankment_over_clay()
        _uniform_load(p, 40.0, x0=0.0, x1=100.0)
        du = excess_at(p, clay, 50.0, 10.0, 30.0)
        assert abs(du - 250.0) < 1e-9, du


# ======================================================================
# 3. The vertical seismic coefficient
# ======================================================================
class TestOnlyTheVerticalSeismicCoefficientCounts:

    def _seismic(self, kh, kv, marked=True):
        from ogr_core.hydraulic.excess_pore_pressure import excess_at
        p, _emb, clay = _embankment_over_clay()
        p.seismic.enabled = True
        p.seismic.kh = kh
        p.seismic.kv = kv
        p.seismic.creates_excess_pore_pressure = marked
        return excess_at(p, clay, 50.0, 10.0, 30.0)

    def test_the_vertical_one_scales_the_soil_stress(self):
        assert abs(self._seismic(0.0, 0.2) - 210.0 * 1.2) < 1e-9

    def test_the_horizontal_one_never_contributes(self):
        """It changes no VERTICAL stress, so it can generate no excess —
        whatever the checkbox says."""
        assert abs(self._seismic(0.3, 0.0) - 210.0) < 1e-9

    def test_unmarked_seismic_contributes_nothing(self):
        assert abs(self._seismic(0.0, 0.2, marked=False) - 210.0) < 1e-9


# ======================================================================
# 4. Line loads finally reach the calculation
# ======================================================================
class TestALineLoadLoads:

    def _with_line(self, magnitude, x=8.0):
        from ogr_core.geometry import Vertex
        from ogr_core.loads import LineLoad
        from ogr_core.loads.loads import LoadOrientation
        p = _slope()
        p.line_loads.append(LineLoad(
            point=Vertex(x, 30), magnitude=magnitude,
            orientation=LoadOrientation.VERTICAL))
        return p

    def test_it_moves_the_factor_of_safety(self):
        """The regression that motivated half this version: before
        v0.1.75 this difference was EXACTLY zero for any magnitude."""
        bare = _fos(_slope())
        loaded = _fos(self._with_line(500.0))
        assert loaded < bare - 1e-3, (bare, loaded)

    def test_a_bigger_load_lowers_it_further(self):
        assert _fos(self._with_line(1000.0)) < _fos(self._with_line(200.0))

    def test_it_matches_the_equivalent_distributed_load(self):
        """The analytic identity that pins the magnitude, not just the
        sign: a line load of P and a distributed load whose integral is P
        over the same slice must weigh the same, because a line load IS a
        surcharge concentrated on its slice.
        """
        from ogr_core.geometry import Vertex
        from ogr_core.loads import DistributedLoad
        from ogr_core.loads.loads import LoadOrientation
        from ogr_slip2d import slice_surface

        p_line = self._with_line(500.0, x=8.0)
        sl = slice_surface(p_line, _circle(), num_slices=25)
        # The slice the load fell on, and its width.
        target = next(s for s in sl.slices
                      if s.base_x_left - 1e-9 <= 8.0 < s.base_x_right)
        width = target.width

        p_dist = _slope()
        p_dist.distributed_loads.append(DistributedLoad(
            start=Vertex(target.base_x_left, 30),
            end=Vertex(target.base_x_right, 30),
            magnitude_1=500.0 / width,
            orientation=LoadOrientation.VERTICAL))
        sl_d = slice_surface(p_dist, _circle(), num_slices=25)
        target_d = next(s for s in sl_d.slices
                        if abs(s.x_centre - target.x_centre) < 1e-9)
        assert abs(target.weight - target_d.weight) < 1e-6, (
            target.weight, target_d.weight)

    def test_a_horizontal_line_load_acts_horizontally(self):
        """It must not be silently dropped for want of a vertical part."""
        from ogr_core.geometry import Vertex
        from ogr_core.loads import LineLoad
        from ogr_core.loads.loads import LoadOrientation
        from ogr_slip2d import slice_surface

        p = _slope()
        p.line_loads.append(LineLoad(
            point=Vertex(8, 30), magnitude=300.0,
            orientation=LoadOrientation.HORIZONTAL))
        sl = slice_surface(p, _circle(), num_slices=25)
        total_h = sum(s.water_force_h for s in sl.slices)
        assert abs(total_h - 300.0) < 1e-9, total_h

    def test_a_load_outside_the_surface_changes_nothing(self):
        assert abs(_fos(self._with_line(500.0, x=55.0))
                   - _fos(_slope())) < 1e-9

    def test_it_is_counted_once_at_a_slice_boundary(self):
        """Half-open intervals: a load exactly on a boundary belongs to
        one slice, never to both and never to neither."""
        from ogr_slip2d import slice_surface
        p = self._with_line(500.0, x=8.0)
        sl = slice_surface(p, _circle(), num_slices=25)
        boundary_x = sl.slices[5].base_x_left
        p2 = self._with_line(500.0, x=boundary_x)
        sl2 = slice_surface(p2, _circle(), num_slices=25)
        bare = slice_surface(_slope(), _circle(), num_slices=25)
        added = (sum(s.weight for s in sl2.slices)
                 - sum(s.weight for s in bare.slices))
        assert abs(added - 500.0) < 1e-6, added


# ======================================================================
# 5. The excess reaches the factor of safety
# ======================================================================
class TestItReachesTheAnalysis:

    def test_the_excess_lowers_the_factor_of_safety(self):
        """Rule 7 end to end: more pore pressure, less effective stress,
        less strength.

        On the SLOPING fixture, not the flat block: a horizontal block
        has zero driving moment and every factor of safety comes back
        infinite, which would make the comparison vacuous. The first
        draft of this test did exactly that and asserted inf < inf.
        """
        from ogr_core.geometry import Vertex
        from ogr_core.loads import DistributedLoad
        from ogr_core.loads.loads import LoadOrientation

        def _build(enabled):
            p = _slope()
            p.materials[0].b_bar = 1.0
            p.distributed_loads.append(DistributedLoad(
                start=Vertex(0, 30), end=Vertex(15, 30), magnitude_1=60.0,
                orientation=LoadOrientation.VERTICAL,
                creates_excess_pore_pressure=True))
            p.settings.groundwater.set_advanced_option(
                "excess_pore_pressure" if enabled else None)
            return p

        with_excess = _fos(_build(True))
        without = _fos(_build(False))
        assert all(math.isfinite(f) for f in (with_excess, without)), (
            with_excess, without)
        assert 0.3 < with_excess < without < 3.0, (with_excess, without)
        assert with_excess < without - 1e-3, (with_excess, without)

    def test_the_slice_records_it_on_top_of_the_initial_pressure(self):
        """u_final = u_initial + Δu, which is the order Skempton's
        formulation and the reference both state."""
        from ogr_slip2d import slice_surface
        p, m = _block(b_bar=1.0)
        _uniform_load(p, 40.0, x0=0.0, x1=100.0)
        from ogr_slip2d import SlipCircle
        circle = SlipCircle(centre_x=50, centre_y=45, radius=30)
        sl = slice_surface(p, circle, num_slices=20)
        assert sl is not None
        for s in sl.slices:
            # No water table, so the initial pressure is zero and the
            # whole of u is the excess.
            assert abs(s.pore_pressure - 40.0) < 1e-9, s.pore_pressure


# ======================================================================
# 6. Serialization and the interface
# ======================================================================
class TestItSurvivesASave:

    def test_the_material_flag_round_trips(self):
        from ogr_core.materials import Material, MohrCoulomb
        m = Material(name="m",
                     strength=MohrCoulomb(cohesion=1, friction_angle=20))
        m.weight_creates_excess = True
        assert Material.from_dict(m.to_dict()).weight_creates_excess is True

    def test_the_default_is_off_for_older_files(self):
        from ogr_core.materials import Material, MohrCoulomb
        m = Material(name="m",
                     strength=MohrCoulomb(cohesion=1, friction_angle=20))
        data = m.to_dict()
        del data["weight_creates_excess"]
        assert Material.from_dict(data).weight_creates_excess is False

    def test_every_load_kind_round_trips_its_flag(self):
        from ogr_core.geometry import Vertex
        from ogr_core.loads import DistributedLoad, LineLoad, SeismicLoad
        loads = [
            DistributedLoad(start=Vertex(0, 0), end=Vertex(1, 0),
                            magnitude_1=5.0),
            LineLoad(point=Vertex(0, 0), magnitude=5.0),
            SeismicLoad(kh=0.1, kv=0.05, enabled=True),
        ]
        for load in loads:
            load.creates_excess_pore_pressure = True
            back = type(load).from_dict(load.to_dict())
            assert back.creates_excess_pore_pressure is True, type(load)


_WINDOWS: list = []


class TestTheInterface:

    def _dialog(self, **kw):
        from PySide6.QtWidgets import QApplication
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog,
        )
        QApplication.instance() or QApplication([])
        m = Material(name="M",
                     strength=MohrCoulomb(cohesion=10, friction_angle=25))
        d = MaterialPropertiesDialog([m], None, **kw)
        _WINDOWS.append(d)
        d.list.setCurrentRow(0)
        return d

    def test_the_group_appears_only_with_the_analysis(self):
        d = self._dialog()
        assert d.grp_excess.isVisibleTo(d) is False
        d2 = self._dialog(excess_pore_pressure=True)
        assert d2.grp_excess.isVisibleTo(d2) is True

    def test_it_writes_both_fields(self):
        d = self._dialog(excess_pore_pressure=True)
        d.dsp_b_bar_excess.setValue(0.85)
        d.chk_weight_excess.setChecked(True)
        d._store(0)
        m = d.materials[0]
        assert abs(m.b_bar - 0.85) < 1e-12
        assert m.weight_creates_excess is True

    def test_the_two_advanced_groups_are_never_both_shown(self):
        """They are mutually exclusive analyses, so at most one of the
        two groups can be on screen."""
        for kw in ({}, {"excess_pore_pressure": True},
                   {"rapid_drawdown": True}):
            d = self._dialog(**kw)
            both = (d.grp_excess.isVisibleTo(d)
                    and d.grp_drawdown.isVisibleTo(d))
            assert both is False, kw

    def test_the_load_dialog_checkbox_reads_the_real_field(self):
        """It used to read ``excess_pp``, an attribute no load class ever
        had, so an existing load always showed the box unticked."""
        from PySide6.QtWidgets import QApplication
        from ogr_core.geometry import Vertex
        from ogr_core.loads import LineLoad
        from ogr_gui.dialogs.load_dialogs import LineLoadDialog
        QApplication.instance() or QApplication([])
        load = LineLoad(point=Vertex(0, 0), magnitude=5.0)
        load.creates_excess_pore_pressure = True
        dlg = LineLoadDialog(existing=load)
        _WINDOWS.append(dlg)
        assert dlg.cb_excess.isChecked() is True
        assert dlg.excess_pp() is True


class TestTheNewStringsAreTranslated:
    KEYS = [
        "Excess Pore Pressure",
        "Material weight creates excess pore pressure",
    ]

    def test_every_new_key_has_a_spanish_entry(self):
        from ogr_gui.i18n import current_language, set_language, tr
        prev = current_language()
        try:
            set_language("es")
            missing = [k for k in self.KEYS if tr(k) == k]
            assert not missing, missing
        finally:
            set_language(prev)

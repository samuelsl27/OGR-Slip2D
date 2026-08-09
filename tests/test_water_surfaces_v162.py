# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Which water surface applies, and what the grid may not override.

Four invariants, each of which was violated by v0.1.61.

1. **A water table clips a pressure grid.** This is the third of the three
   documented differences between a water table and a piezometric line,
   and the only one that was never implemented: with a grid method
   selected, ``pore_pressure_at`` returned before the water-table branch
   was reachable, so an interpolated grid could report positive pressure
   arbitrarily high above the phreatic surface. The anchor is an exact
   identity, not a captured value: over a grid whose sample values are all
   equal, any interpolation returns that same constant, so u below the
   water table must equal it EXACTLY and u above it must be exactly zero.
   A piezometric line must NOT clip — it is a pressure measurement, not a
   free surface.

2. **The per-material water surface has to be selectable, and selecting it
   has to move the number** (rule 7). ``Material.water_surface_id`` was
   honoured by the solver since v0.1.7 but nothing in the interface ever
   wrote it, so the resolver always fell through to "the first surface of
   that type" and a second piezometric line was unreachable. The anchor is
   again analytic: with Hu = 1, u = γw·(y_surface − y), so pointing the
   same material at two piezometric lines a known distance apart must
   change u by exactly γw times that distance.

3. **hu, auto_hu, undrained_behaviour and b_bar must survive a save.**
   They were read with ``getattr`` off attributes no dataclass declared,
   so they existed only if injected at runtime and ``to_dict`` dropped
   them silently. Auto Hu carries its own closed-form anchor:
   Hu = cos²α, which is exactly 1 on a horizontal surface and exactly 0.5
   on one at 45°.

4. **Reopening an old project may not change its factor of safety.** B̄
   now defaults to "freely draining" per the reference, where before it
   defaulted implicitly to 1.0 for every material. The migration in
   ``Project.from_dict`` has to give legacy files back the old behaviour,
   exactly as v0.1.60 did for ``use_sat_unit_weight``.
"""
from __future__ import annotations

GAMMA_W = 9.81

_WINDOWS: list = []


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


# ======================================================================
# Fixtures
# ======================================================================
def _slope_project(name="ws"):
    """A sloping model with no water of any kind. Water is added per test.

    The ground slopes because a horizontal block has zero driving moment
    and every factor of safety comes back infinite, which would make any
    FoS comparison vacuous.
    """
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
        name="Soil",
        strength=MohrCoulomb(cohesion=20, friction_angle=25),
        unit_weight=19.0,
    )]
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W
    return p


def _add_level(p, btype, y: float):
    """A horizontal water surface of type ``btype`` spanning the model."""
    from ogr_core.geometry import Boundary, Polyline, Vertex
    b = Boundary(
        polyline=Polyline(vertices=[Vertex(-5, y), Vertex(65, y)],
                          closed=False),
        btype=btype,
    )
    p.add_boundary(b)
    return b


def _flat_grid(p, value: float):
    """A pore-pressure grid whose every sample equals ``value``.

    Any interpolation of a constant field is that constant, whichever
    scheme runs — which is what makes the comparison below exact instead
    of tolerance-bound.
    """
    from ogr_core.hydraulic import GridValueType, WaterPressureGrid
    from ogr_core.project.settings import GroundwaterMethod

    pts = [(x, y, value) for x in (0.0, 30.0, 60.0)
           for y in (0.0, 15.0, 30.0)]
    p.water_pressure_grid = WaterPressureGrid(
        points=pts, value_type=GridValueType.PORE_PRESSURE,
        interpolation="idw",
    )
    p.settings.groundwater.method = GroundwaterMethod.GRID_PORE_PRESSURE.value
    return p.water_pressure_grid


def _u(p, x: float, y: float, mat=None) -> float:
    from ogr_core.geometry import Vertex
    from ogr_core.hydraulic.pore_pressure import pore_pressure_at
    return pore_pressure_at(p, Vertex(x, y), mat or p.materials[0])


# ======================================================================
class TestGridIsClippedByTheWaterTable:
    """Invariant 1 — the third NF ↔ piezometric difference."""

    def test_grid_alone_reports_its_value_everywhere(self):
        """Baseline: without a water table the grid governs at any height.

        Without this the next test could pass for the wrong reason — a
        grid that returned zero everywhere would also look 'clipped'.

        The comparison is against the grid's OWN interpolated value, not
        against the literal 100.0: inverse-distance weighting of a
        constant field returns that constant only to within floating-point
        (99.999999999999972 here), and the invariant under test is "the
        grid passes through untouched", not "the interpolator is exact".
        The second assertion pins the value as a constant field anyway, so
        a broken interpolator would still be caught.
        """
        p = _slope_project()
        g = _flat_grid(p, 100.0)
        for y in (5.0, 25.0):
            assert _u(p, 30.0, y) == g.pore_pressure_at(30.0, y, GAMMA_W)
            assert abs(_u(p, 30.0, y) - 100.0) / 100.0 < 1e-12

    def test_water_table_forces_zero_above_and_leaves_below_intact(self):
        from ogr_core.geometry import BoundaryType
        p = _slope_project()
        g = _flat_grid(p, 100.0)
        _add_level(p, BoundaryType.WATER_TABLE, 15.0)

        # Above the water table: clipped to exactly zero. This one IS an
        # exact equality — the clip is a literal ``return 0.0``.
        assert _u(p, 30.0, 20.0) == 0.0
        # Below it: the grid governs, bit for bit.
        assert _u(p, 30.0, 10.0) == g.pore_pressure_at(30.0, 10.0, GAMMA_W)
        # On it: not above, so not clipped.
        assert _u(p, 30.0, 15.0) == g.pore_pressure_at(30.0, 15.0, GAMMA_W)

    def test_piezometric_line_does_not_clip_a_grid(self):
        """Deliberate asymmetry: a piezometric line is a measurement, not
        a free surface, so it says nothing about what lies above it."""
        from ogr_core.geometry import BoundaryType
        p = _slope_project()
        g = _flat_grid(p, 100.0)
        _add_level(p, BoundaryType.PIEZOMETRIC, 15.0)
        assert _u(p, 30.0, 20.0) == g.pore_pressure_at(30.0, 20.0, GAMMA_W)
        assert _u(p, 30.0, 20.0) > 0.0

    def test_per_material_ru_still_overrides_the_grid(self):
        """The grid is a project-level source; Ru is an explicit
        per-material choice and keeps precedence, water table or not."""
        from ogr_core.geometry import BoundaryType
        from ogr_core.materials import PorePressureType
        p = _slope_project()
        _flat_grid(p, 100.0)
        _add_level(p, BoundaryType.WATER_TABLE, 15.0)
        m = p.materials[0]
        m.pore_pressure = PorePressureType.RU_COEFFICIENT
        m.ru = 0.5
        from ogr_core.geometry import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        # 10 m of cover, γ = 19 ⇒ σv = 190, u = 0.5·190 = 95 exactly.
        u = pore_pressure_at(p, Vertex(30.0, 20.0), m, ground_surface_y=30.0)
        assert abs(u - 95.0) < 1e-9


# ======================================================================
class TestTheSelectorMovesTheNumber:
    """Invariant 2 — rule 7 for ``water_surface_id``."""

    def _two_piezos(self):
        from ogr_core.geometry import BoundaryType
        from ogr_core.materials import PorePressureType
        p = _slope_project()
        low = _add_level(p, BoundaryType.PIEZOMETRIC, 12.0)
        high = _add_level(p, BoundaryType.PIEZOMETRIC, 20.0)
        p.materials[0].pore_pressure = PorePressureType.PIEZO_LINE
        return p, low, high

    def test_u_follows_the_assigned_surface_exactly(self):
        p, low, high = self._two_piezos()
        m = p.materials[0]

        m.water_surface_id = low.id
        u_low = _u(p, 30.0, 5.0)
        m.water_surface_id = high.id
        u_high = _u(p, 30.0, 5.0)

        # Hu defaults to 1 ⇒ u = γw·(y_surface − y), so the difference is
        # exactly γw times the 8 m between the two lines.
        assert abs(u_low - GAMMA_W * 7.0) < 1e-9
        assert abs(u_high - GAMMA_W * 15.0) < 1e-9
        assert abs((u_high - u_low) - GAMMA_W * 8.0) < 1e-9

    def test_unassigned_falls_back_to_the_first_of_the_type(self):
        """The legacy behaviour, kept deliberately — and the reason the
        selector had to exist: with two lines it is arbitrary."""
        p, low, _high = self._two_piezos()
        p.materials[0].water_surface_id = None
        assert abs(_u(p, 30.0, 5.0) - GAMMA_W * 7.0) < 1e-9

    def test_the_choice_changes_the_factor_of_safety(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle

        p, low, high = self._two_piezos()
        m = p.materials[0]
        circle = SlipCircle(centre_x=25.0, centre_y=40.0, radius=25.0)

        def fos():
            sl = slice_surface(p, circle, num_slices=25)
            assert sl is not None
            return BishopSimplified().compute_fos(p, circle, sl).fos

        m.water_surface_id = low.id
        f_low = fos()
        m.water_surface_id = high.id
        f_high = fos()
        # More head ⇒ more pore pressure ⇒ less effective stress ⇒ lower
        # factor of safety. The direction is the invariant; the gap only
        # has to be big enough not to be numerical noise.
        assert f_high < f_low
        assert (f_low - f_high) / f_low > 0.01


# ======================================================================
class TestWaterParametersSurviveASave:
    """Invariant 3 — the three ``getattr`` fields are real fields now."""

    def test_round_trip_preserves_all_four(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb

        m = Material(name="M", strength=MohrCoulomb(cohesion=1,
                                                    friction_angle=20))
        m.hu = 0.62
        m.auto_hu = True
        m.undrained_behaviour = True
        m.b_bar = 0.85
        back = Material.from_dict(m.to_dict())
        assert back.hu == 0.62
        assert back.auto_hu is True
        assert back.undrained_behaviour is True
        assert back.b_bar == 0.85

    def test_defaults_are_the_reference_defaults(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        m = Material(name="M", strength=MohrCoulomb(cohesion=1,
                                                    friction_angle=20))
        assert m.hu is None            # → project default
        assert m.auto_hu is False
        assert m.undrained_behaviour is False
        assert m.b_bar == 0.0          # freely draining

    def test_hu_scales_u_linearly(self):
        from ogr_core.geometry import BoundaryType
        from ogr_core.materials import PorePressureType
        p = _slope_project()
        _add_level(p, BoundaryType.WATER_TABLE, 20.0)
        m = p.materials[0]
        m.pore_pressure = PorePressureType.WATER_TABLE

        m.hu = 1.0
        assert abs(_u(p, 30.0, 5.0) - GAMMA_W * 15.0) < 1e-9
        m.hu = 0.5
        assert abs(_u(p, 30.0, 5.0) - GAMMA_W * 15.0 * 0.5) < 1e-9
        m.hu = 0.0
        assert _u(p, 30.0, 5.0) == 0.0

    def test_auto_hu_is_cos_squared_alpha(self):
        """Closed form: Hu = cos²α. Exactly 1 flat, exactly 0.5 at 45°."""
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import PorePressureType

        # Horizontal surface → α = 0 → Hu = 1.
        p = _slope_project()
        _add_level(p, BoundaryType.WATER_TABLE, 20.0)
        m = p.materials[0]
        m.pore_pressure = PorePressureType.WATER_TABLE
        m.auto_hu = True
        assert abs(_u(p, 30.0, 5.0) - GAMMA_W * 15.0) < 1e-9

        # 45° surface → cos²45° = 1/2, exactly.
        q = _slope_project()
        q.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(0, 0), Vertex(40, 40)],
                              closed=False),
            btype=BoundaryType.WATER_TABLE,
        ))
        n = q.materials[0]
        n.pore_pressure = PorePressureType.WATER_TABLE
        n.auto_hu = True
        # At x = 20 the surface is at y = 20; the point sits 15 m below.
        assert abs(_u(q, 20.0, 5.0) - GAMMA_W * 15.0 * 0.5) < 1e-9

    def test_material_auto_hu_overrides_the_project_default(self):
        from ogr_core.geometry import BoundaryType
        from ogr_core.materials import PorePressureType
        p = _slope_project()
        _add_level(p, BoundaryType.WATER_TABLE, 20.0)
        p.settings.groundwater.default_hu = 0.25
        m = p.materials[0]
        m.pore_pressure = PorePressureType.WATER_TABLE
        # No per-material Hu → the project default applies.
        assert abs(_u(p, 30.0, 5.0) - GAMMA_W * 15.0 * 0.25) < 1e-9
        # Per-material Hu wins over the project default.
        m.hu = 0.75
        assert abs(_u(p, 30.0, 5.0) - GAMMA_W * 15.0 * 0.75) < 1e-9


# ======================================================================
class TestBBarMigration:
    """Invariant 4 — what an old project is allowed to do on being read.

    Two migrations meet here, and they answer to different rules.

    v0.1.62 restored ``b_bar`` and ``undrained_behaviour`` to files
    written before those keys existed, so the factor of safety would NOT
    change: the defaults had moved and a saved project must not drift.

    v0.1.69 does the opposite on purpose. Until then this model demanded
    the drawdown line ABOVE the water table, the reverse of the reference
    and of the other three procedures, and the factor of safety it
    produced was the one from BEFORE the drawdown. Swapping the two
    labels leaves the geometry untouched and makes the file mean what it
    always meant; the number it yields changes, because the old number
    was wrong. That is the one case where the drift is the repair.
    """

    def _drawdown_project(self, dd_above=True):
        """The old convention by default: drawdown line ABOVE the table.

        ``dd_above=False`` builds the same model the v0.1.69 way, which
        is what a file saved from this version on will look like.
        """
        from ogr_core.geometry import BoundaryType
        from ogr_core.materials import PorePressureType
        p = _slope_project("dd")
        wt, dd = (12.0, 22.0) if dd_above else (22.0, 12.0)
        _add_level(p, BoundaryType.WATER_TABLE, wt)
        _add_level(p, BoundaryType.DRAWDOWN, dd)
        p.settings.groundwater.set_advanced_option("rapid_drawdown")
        p.settings.groundwater.rapid_drawdown_method = "b_bar"
        p.materials[0].pore_pressure = PorePressureType.WATER_TABLE
        return p

    def _levels(self, project):
        from ogr_core.geometry import BoundaryType
        from ogr_core.hydraulic.water_surfaces import interp_y_on_polyline
        out = {}
        for b in project.boundaries:
            if b.btype in (BoundaryType.WATER_TABLE, BoundaryType.DRAWDOWN):
                out[b.btype] = interp_y_on_polyline(b.polyline, 30.0)
        return out

    # -- v0.1.69, the convention swap --------------------------------
    def test_an_inverted_file_has_its_two_levels_exchanged(self):
        from ogr_core.geometry import BoundaryType
        from ogr_core.project import Project

        back = Project.from_dict(self._drawdown_project().to_dict())
        lv = self._levels(back)
        assert lv[BoundaryType.WATER_TABLE] == 22.0, "initial level"
        assert lv[BoundaryType.DRAWDOWN] == 12.0, "final level"

    def test_the_swap_leaves_the_geometry_alone(self):
        """Only the two labels move; no vertex does."""
        from ogr_core.geometry import BoundaryType
        from ogr_core.project import Project

        p = self._drawdown_project()
        before = sorted(
            (v.x, v.y) for b in p.boundaries
            if b.btype in (BoundaryType.WATER_TABLE, BoundaryType.DRAWDOWN)
            for v in b.polyline.vertices)
        back = Project.from_dict(p.to_dict())
        after = sorted(
            (v.x, v.y) for b in back.boundaries
            if b.btype in (BoundaryType.WATER_TABLE, BoundaryType.DRAWDOWN)
            for v in b.polyline.vertices)
        assert before == after

    def test_a_file_already_in_the_new_convention_is_not_touched(self):
        from ogr_core.geometry import BoundaryType
        from ogr_core.project import Project

        back = Project.from_dict(
            self._drawdown_project(dd_above=False).to_dict())
        lv = self._levels(back)
        assert lv[BoundaryType.WATER_TABLE] == 22.0
        assert lv[BoundaryType.DRAWDOWN] == 12.0

    def test_a_multi_stage_file_is_refused_rather_than_repaired(self):
        """The swap is gated on B-bar. A multi-stage project with an
        inverted line was never valid, so it gets the explicit message
        instead of a silent fix that would hide the modelling error."""
        from ogr_core.geometry import BoundaryType
        from ogr_core.project import Project
        from ogr_slip2d.rapid_drawdown import check_drawdown_settings

        p = self._drawdown_project()
        p.settings.groundwater.rapid_drawdown_method = "duncan_wright"
        p.materials[0].undrained_behaviour = True
        back = Project.from_dict(p.to_dict())
        assert self._levels(back)[BoundaryType.DRAWDOWN] == 22.0
        msg = check_drawdown_settings(back)
        assert msg is not None and "ABOVE" in msg

    def test_a_material_keeps_pointing_at_the_level_it_meant(self):
        """A material assigned to the old low water table must follow it
        into its new role, not fall back to whatever comes first."""
        from ogr_core.geometry import BoundaryType
        from ogr_core.project import Project

        p = self._drawdown_project()
        low = next(b for b in p.boundaries
                   if b.btype == BoundaryType.WATER_TABLE)
        p.materials[0].water_surface_id = low.id
        back = Project.from_dict(p.to_dict())
        assert back.materials[0].water_surface_id != low.id
        target = next(b for b in back.boundaries
                      if b.id == back.materials[0].water_surface_id)
        assert target.btype == BoundaryType.WATER_TABLE

    # -- v0.1.62, the defaults ---------------------------------------
    def test_legacy_file_keeps_the_old_implicit_b_bar(self):
        from ogr_core.project import Project

        p = self._drawdown_project(dd_above=False)
        data = p.to_dict()
        # Simulate a file written before the keys existed.
        for m in data["materials"]:
            m.pop("b_bar", None)
            m.pop("undrained_behaviour", None)
        back = Project.from_dict(data)
        assert back.materials[0].undrained_behaviour is True
        assert back.materials[0].b_bar == 1.0

    def test_a_file_that_carries_the_keys_is_left_alone(self):
        from ogr_core.project import Project
        p = self._drawdown_project(dd_above=False)
        p.materials[0].undrained_behaviour = False
        p.materials[0].b_bar = 0.0
        back = Project.from_dict(p.to_dict())
        assert back.materials[0].undrained_behaviour is False
        assert back.materials[0].b_bar == 0.0
        # Freely draining ⇒ no excess, just the steady head from the
        # water table at 22: γw·(22 − 5).
        assert abs(_u(back, 30.0, 5.0, back.materials[0])
                   - GAMMA_W * 17.0) < 1e-9

    def test_the_pore_pressure_model_no_longer_knows_about_drawdown(self):
        """v0.1.69 — rule 7 read backwards. ``pore_pressure_at`` must now
        give the same steady head whatever the drawdown settings say,
        because the excess is applied on the slices instead."""
        p = self._drawdown_project(dd_above=False)
        m = p.materials[0]
        m.b_bar = 1.0
        steady = GAMMA_W * 17.0
        for undrained in (False, True):
            m.undrained_behaviour = undrained
            assert abs(_u(p, 30.0, 5.0) - steady) < 1e-9


# ======================================================================
class TestOrdinaryReportsItsOwnWeakness:
    """Not a fix — a diagnosis. Fellenius resolves the weight on the base
    with no interslice force, so a high u drives N' below zero and the
    clamp discards the deficit (Whitman and Bailey 1967)."""

    def test_negative_effective_normals_are_counted(self):
        from ogr_core.geometry import BoundaryType
        from ogr_core.materials import PorePressureType
        from ogr_slip2d.methods.ordinary import OrdinaryFellenius
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle

        p = _slope_project("ord")
        # A piezometric line far above the ground: a deliberately extreme
        # head, which is exactly the regime where the method breaks down.
        _add_level(p, BoundaryType.PIEZOMETRIC, 80.0)
        p.materials[0].pore_pressure = PorePressureType.PIEZO_LINE

        circle = SlipCircle(centre_x=25.0, centre_y=40.0, radius=25.0)
        sl = slice_surface(p, circle, num_slices=25)
        assert sl is not None
        res = OrdinaryFellenius().compute_fos(p, circle, sl)
        assert res.details["negative_effective_normal"] > 0
        assert res.details["num_slices"] == len(sl.slices)

    def test_no_water_means_no_warning(self):
        from ogr_slip2d.methods.ordinary import OrdinaryFellenius
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle

        p = _slope_project("dry")
        circle = SlipCircle(centre_x=25.0, centre_y=40.0, radius=25.0)
        sl = slice_surface(p, circle, num_slices=25)
        res = OrdinaryFellenius().compute_fos(p, circle, sl)
        assert res.details["negative_effective_normal"] == 0


# ======================================================================
class TestTheInterfaceWritesTheField:
    """The whole point of invariant 2: something has to set the id."""

    def _dialog(self, p):
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog,
        )
        from ogr_core.hydraulic import water_surfaces
        _app()
        choices = [(b.id, b.id[:6]) for b in water_surfaces(p)]
        d = MaterialPropertiesDialog(
            p.materials, None, water_surfaces=choices, rapid_drawdown=True)
        _WINDOWS.append(d)
        return d

    def test_combo_offers_every_water_surface_plus_the_fallback(self):
        from ogr_core.geometry import BoundaryType
        p = _slope_project()
        _add_level(p, BoundaryType.WATER_TABLE, 20.0)
        _add_level(p, BoundaryType.PIEZOMETRIC, 12.0)
        d = self._dialog(p)
        # Two surfaces + the "(first of this type)" entry.
        assert d.cbo_water_surface.count() == 3
        assert d.cbo_water_surface.itemData(0) is None

    def test_selecting_a_surface_writes_the_id(self):
        from ogr_core.geometry import BoundaryType
        p = _slope_project()
        wt = _add_level(p, BoundaryType.WATER_TABLE, 20.0)
        d = self._dialog(p)
        d.list.setCurrentRow(0)
        idx = d.cbo_water_surface.findData(wt.id)
        assert idx > 0
        d.cbo_water_surface.setCurrentIndex(idx)
        d._store(0)
        assert d.materials[0].water_surface_id == wt.id

    def test_hu_checkbox_unticked_means_project_default(self):
        from ogr_core.geometry import BoundaryType
        p = _slope_project()
        _add_level(p, BoundaryType.WATER_TABLE, 20.0)
        d = self._dialog(p)
        d.list.setCurrentRow(0)
        d.chk_hu.setChecked(False)
        d._store(0)
        assert d.materials[0].hu is None
        d.chk_hu.setChecked(True)
        d.dsp_hu.setValue(0.4)
        d._store(0)
        assert abs(d.materials[0].hu - 0.4) < 1e-12

    def test_widgets_are_disabled_for_models_that_ignore_them(self):
        """Disabled, not hidden — an option nobody can see is an option
        nobody discovers."""
        from ogr_core.geometry import BoundaryType
        from ogr_core.materials import PorePressureType
        p = _slope_project()
        _add_level(p, BoundaryType.WATER_TABLE, 20.0)
        d = self._dialog(p)
        d.list.setCurrentRow(0)

        d.cbo_pp.setCurrentIndex(
            d.cbo_pp.findData(PorePressureType.WATER_TABLE))
        assert d.cbo_water_surface.isEnabled() is True
        assert d.dsp_ru.isEnabled() is False

        d.cbo_pp.setCurrentIndex(
            d.cbo_pp.findData(PorePressureType.RU_COEFFICIENT))
        assert d.cbo_water_surface.isEnabled() is False
        assert d.dsp_ru.isEnabled() is True

        # Auto Hu takes Hu out of the user's hands.
        d.cbo_pp.setCurrentIndex(
            d.cbo_pp.findData(PorePressureType.WATER_TABLE))
        d.chk_hu.setChecked(True)
        assert d.dsp_hu.isEnabled() is True
        d.chk_auto_hu.setChecked(True)
        assert d.dsp_hu.isEnabled() is False

    def test_b_bar_is_disabled_without_a_rapid_drawdown_run(self):
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog,
        )
        _app()
        p = _slope_project()
        d = MaterialPropertiesDialog(p.materials, None, rapid_drawdown=False)
        _WINDOWS.append(d)
        d.list.setCurrentRow(0)
        assert d.chk_undrained.isEnabled() is False
        # v0.1.72 — the group is now hidden as well, since a project that
        # runs no drawdown has no use for a quarter of the dialog. The
        # guarantee under test is unchanged: B̄ stays out of reach.
        assert d.grp_drawdown.isVisibleTo(d) is False

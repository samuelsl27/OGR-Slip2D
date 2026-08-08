# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Saturated unit weight as an OPT-IN, and non-destructive material editing.

Two invariants are protected here.

1. The saturated unit weight is now a switch, and a switch that does not
   move the number is worse than no switch at all (rule 7). The numeric
   anchor is an ANALYTIC IDENTITY rather than a captured value: the slice
   weight is linear in γ, so for a slip surface whose slices are ALL below
   the water table,

       Σ W(option on) / Σ W(option off)  ==  γsat / γ

   exactly, whatever the geometry. The same identity anchors the Ru pore
   pressure, u = ru·γ·z.

2. The Define Materials dialog must not lose edits. Before v0.1.60 the
   selection handler only LOADED the newly selected material and never
   committed the one being left, so switching rows discarded the edit;
   and the dialog mutated the project's own Material objects, so Cancel
   did not cancel. Both are covered below.

A third group covers the serialization bug that surfaced while checking
whether a Material could be copied through to_dict/from_dict: the table of
the function-based strength models was silently replaced by the built-in
demo table on every save/load cycle.
"""
from __future__ import annotations

import math

from PySide6.QtWidgets import QApplication

# Keep dialogs alive: a garbage-collected QWidget takes its children with
# it and the assertions below would read a dead object.
_WINDOWS: list = []


def _app():
    return QApplication.instance() or QApplication([])


# ======================================================================
# Fixtures
# ======================================================================
def _submerged_project(gamma: float, gamma_sat: float, use_sat: bool):
    """A simple slope whose water table runs ALONG the ground surface.

    Every slice base midpoint then lies strictly below the water table —
    a slice has positive height — so all of them take the same branch of
    ``gamma_at`` and the γsat comparison becomes an exact ratio.

    The water table follows the ground rather than floating above it on
    purpose: a water table drawn ABOVE the external boundary means ponded
    water, whose weight and hydrostatic thrust are part of the analysis.
    A fixture that relied on that load being absent would be measuring a
    gap rather than the option under test.

    The ground has to slope: on a horizontal block the driving moment is
    zero and every factor of safety comes back infinite, which would make
    the FoS comparison vacuous.
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
    p = Project("sat")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[
            Vertex(0, 30), Vertex(15, 30), Vertex(35, 10), Vertex(60, 10),
        ], closed=False),
        btype=BoundaryType.WATER_TABLE,
    ))
    p.materials = [Material(
        name="Soil",
        strength=MohrCoulomb(cohesion=20, friction_angle=25),
        unit_weight=gamma,
        sat_unit_weight=gamma_sat,
        use_sat_unit_weight=use_sat,
    )]
    return p


def _circle():
    from ogr_slip2d.surface import SlipCircle
    # Cuts the ground twice, well inside the model.
    return SlipCircle(centre_x=25.0, centre_y=40.0, radius=25.0)


def _total_weight(p) -> float:
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(p, _circle(), num_slices=25)
    assert sl is not None
    return sum(s.weight for s in sl.slices)


def _two_materials():
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    return [
        Material(name="A", unit_weight=18.0, sat_unit_weight=21.0,
                 strength=MohrCoulomb(cohesion=5, friction_angle=30)),
        Material(name="B", unit_weight=19.0, sat_unit_weight=22.0,
                 strength=MohrCoulomb(cohesion=7, friction_angle=28)),
    ]


def _dialog(materials, has_water_table=True):
    from ogr_gui.dialogs.material_properties_dialog import (
        MaterialPropertiesDialog,
    )
    _app()
    d = MaterialPropertiesDialog(materials, None,
                                 has_water_table=has_water_table)
    _WINDOWS.append(d)
    return d


# ======================================================================
class TestTheOptionMovesTheNumber:
    """Rule 7: a setting that changes nothing is worse than no setting."""

    def test_weight_ratio_is_exactly_gamma_ratio(self):
        """All slices submerged ⇒ ΣW(on)/ΣW(off) == γsat/γ, exactly.

        An analytic identity, not a captured value: the slice weight is
        γ·h·dx, linear in γ, and every slice takes the same branch.
        """
        gamma, gamma_sat = 18.0, 27.0
        w_off = _total_weight(_submerged_project(gamma, gamma_sat, False))
        w_on = _total_weight(_submerged_project(gamma, gamma_sat, True))
        assert w_off > 0.0
        assert math.isclose(w_on / w_off, gamma_sat / gamma, rel_tol=1e-9)

    def test_factor_of_safety_changes(self):
        """The switch has to reach the answer, not just the slice table."""
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import GridSearch

        ev = GridSearch(method=BishopSimplified(), num_slices=25,
                        min_area=0.0)
        r_off = ev.evaluate_circle(
            _submerged_project(18.0, 27.0, False), _circle())
        r_on = ev.evaluate_circle(
            _submerged_project(18.0, 27.0, True), _circle())
        assert r_off is not None and r_on is not None
        assert abs(r_on.fos - r_off.fos) > 1e-6, (r_off.fos, r_on.fos)

    def test_equal_weights_make_the_switch_a_no_op(self):
        """γsat == γ ⇒ the option cannot change anything. Guards against
        the identity above passing for the wrong reason."""
        w_off = _total_weight(_submerged_project(20.0, 20.0, False))
        w_on = _total_weight(_submerged_project(20.0, 20.0, True))
        assert math.isclose(w_on, w_off, rel_tol=1e-12)


# ======================================================================
class TestGammaAt:
    def test_opt_out_ignores_saturated_weight(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        m = Material(name="s", strength=MohrCoulomb(cohesion=1,
                                                    friction_angle=20),
                     unit_weight=19.0, sat_unit_weight=21.5,
                     use_sat_unit_weight=False)
        assert m.gamma_at(below_water=True) == 19.0
        assert m.gamma_at(below_water=False) == 19.0

    def test_opt_in_uses_it_only_below_water(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        m = Material(name="s", strength=MohrCoulomb(cohesion=1,
                                                    friction_angle=20),
                     unit_weight=19.0, sat_unit_weight=21.5,
                     use_sat_unit_weight=True)
        assert m.gamma_at(below_water=True) == 21.5
        assert m.gamma_at(below_water=False) == 19.0

    def test_new_material_defaults_to_opt_out(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        m = Material(name="s", strength=MohrCoulomb(cohesion=1,
                                                    friction_angle=20))
        assert m.use_sat_unit_weight is False


# ======================================================================
class TestBackwardCompatibility:
    """Reopening a project saved before the option existed must not
    change its factor of safety."""

    def _legacy_dict(self):
        from ogr_core.materials.builtin_models import MohrCoulomb
        return {
            "name": "Legacy",
            "strength": MohrCoulomb(cohesion=10,
                                    friction_angle=25).to_dict(),
            "unit_weight": 20.0,
            "sat_unit_weight": 21.0,
            # no "use_sat_unit_weight" key — this is the old format
        }

    def test_legacy_file_keeps_using_saturated_weight(self):
        from ogr_core.materials import Material
        m = Material.from_dict(self._legacy_dict())
        assert m.use_sat_unit_weight is True
        assert m.gamma_at(below_water=True) == 21.0

    def test_file_without_any_saturated_weight_opts_out(self):
        from ogr_core.materials import Material
        data = self._legacy_dict()
        del data["sat_unit_weight"]
        m = Material.from_dict(data)
        assert m.use_sat_unit_weight is False

    def test_roundtrip_preserves_the_flag(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        for flag in (True, False):
            m = Material(name="r",
                         strength=MohrCoulomb(cohesion=1, friction_angle=20),
                         unit_weight=20.0, sat_unit_weight=22.0,
                         use_sat_unit_weight=flag)
            m2 = Material.from_dict(m.to_dict())
            assert m2.use_sat_unit_weight is flag
            assert m2.sat_unit_weight == 22.0


# ======================================================================
class TestRuUsesTheSameSwitch:
    """u = ru·γ·z — the Ru model must not reach γsat through a back door
    when the material has opted out of it."""

    def _material(self, use_sat: bool):
        from ogr_core.materials import Material, PorePressureType
        from ogr_core.materials.builtin_models import MohrCoulomb
        return Material(
            name="ru", strength=MohrCoulomb(cohesion=1, friction_angle=20),
            unit_weight=18.0, sat_unit_weight=22.0,
            use_sat_unit_weight=use_sat,
            pore_pressure=PorePressureType.RU_COEFFICIENT, ru=0.4,
        )

    def _u(self, use_sat: bool) -> float:
        from ogr_core.geometry import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        from ogr_core.project import Project
        return pore_pressure_at(Project("ru"), Vertex(10.0, 5.0),
                                self._material(use_sat),
                                ground_surface_y=15.0)

    def test_opt_out_uses_bulk_weight(self):
        assert math.isclose(self._u(False), 0.4 * 18.0 * 10.0, rel_tol=1e-12)

    def test_opt_in_uses_saturated_weight(self):
        assert math.isclose(self._u(True), 0.4 * 22.0 * 10.0, rel_tol=1e-12)


# ======================================================================
class TestDialogSaturatedCheckbox:
    def test_disabled_without_a_water_table(self):
        d = _dialog(_two_materials(), has_water_table=False)
        assert d.chk_gamma_sat.isEnabled() is False
        assert d.dsp_gamma_sat.isEnabled() is False

    def test_enabled_with_a_water_table(self):
        d = _dialog(_two_materials(), has_water_table=True)
        assert d.chk_gamma_sat.isEnabled() is True
        # Unchecked by default, so the value box stays out of reach.
        assert d.dsp_gamma_sat.isEnabled() is False
        d.chk_gamma_sat.setChecked(True)
        assert d.dsp_gamma_sat.isEnabled() is True

    def test_checkbox_reaches_the_material(self):
        d = _dialog(_two_materials())
        d.chk_gamma_sat.setChecked(True)
        d.dsp_gamma_sat.setValue(23.5)
        d._ok()
        assert d.result_materials()[0].use_sat_unit_weight is True
        assert d.result_materials()[0].sat_unit_weight == 23.5

    def test_warning_when_saturated_weight_is_lower(self):
        """γsat is the saturated BULK weight, not the buoyant one, so it
        must exceed the weight above the water table. isVisibleTo is used
        because every child of an unshown window reports isVisible False."""
        d = _dialog(_two_materials())
        d.chk_gamma_sat.setChecked(True)
        d.dsp_gamma.setValue(18.0)
        d.dsp_gamma_sat.setValue(21.0)
        assert d.lbl_gamma_sat_warn.isVisibleTo(d) is False
        d.dsp_gamma_sat.setValue(15.0)
        assert d.lbl_gamma_sat_warn.isVisibleTo(d) is True
        d.dsp_gamma_sat.setValue(25.0)
        assert d.lbl_gamma_sat_warn.isVisibleTo(d) is False

    def test_no_warning_while_the_option_is_off(self):
        d = _dialog(_two_materials())
        d.dsp_gamma.setValue(30.0)
        assert d.lbl_gamma_sat_warn.isVisibleTo(d) is False


# ======================================================================
class TestDialogNonDestructiveEditing:
    def test_switching_material_keeps_the_edit(self):
        d = _dialog(_two_materials())
        d.dsp_gamma.setValue(25.0)
        d.list.setCurrentRow(1)
        d.list.setCurrentRow(0)
        assert d.dsp_gamma.value() == 25.0

    def test_every_edit_survives_to_the_result(self):
        d = _dialog(_two_materials())
        d.dsp_gamma.setValue(25.0)
        d.list.setCurrentRow(1)
        d.dsp_gamma.setValue(33.0)
        d._ok()
        got = [m.unit_weight for m in d.result_materials()]
        assert got == [25.0, 33.0]

    def test_name_edit_survives_a_row_change(self):
        d = _dialog(_two_materials())
        d.ed_name.setText("Renamed")
        d.list.setCurrentRow(1)
        d._ok()
        assert d.result_materials()[0].name == "Renamed"

    def test_adding_a_material_does_not_drop_the_pending_edit(self):
        d = _dialog(_two_materials())
        d.dsp_gamma.setValue(27.0)
        d._add_material()
        d._ok()
        assert d.result_materials()[0].unit_weight == 27.0
        assert len(d.result_materials()) == 3

    def test_cancel_really_cancels(self):
        """The dialog used to edit the project's own Material objects, so
        Cancel discarded only added/removed rows, never field edits."""
        mats = _two_materials()
        d = _dialog(mats)
        d.dsp_gamma.setValue(99.0)
        d.ed_name.setText("Should not stick")
        d.list.setCurrentRow(1)
        d.reject()
        assert mats[0].unit_weight == 18.0
        assert mats[0].name == "A"

    def test_ok_does_not_alias_the_originals(self):
        """result_materials() must be independent objects, so a later
        dialog cannot mutate what the project already holds."""
        mats = _two_materials()
        d = _dialog(mats)
        d._ok()
        assert all(a is not b for a, b in zip(mats, d.result_materials()))
        # ...but the ids must survive: region assignments key off them.
        assert [m.id for m in d.result_materials()] == [m.id for m in mats]

    def test_apply_button_is_gone(self):
        from PySide6.QtWidgets import QDialogButtonBox
        d = _dialog(_two_materials())
        assert d.buttons.button(QDialogButtonBox.Apply) is None


# ======================================================================
class TestStrengthTableSurvivesSerialization:
    """Regression for a bug found while checking whether a Material can be
    copied through to_dict/from_dict: the base ``StrengthModel.from_dict``
    rebuilt the model from ``params`` alone and never dispatched to the
    subclass, so the user's τ–σ'n table was replaced by the demo table on
    every save/load."""

    def test_shear_normal_function_keeps_its_points(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import ShearNormalFunction
        pts = [(0.0, 7.0), (200.0, 99.0)]
        m = Material(name="f", strength=ShearNormalFunction(points=pts))
        m2 = Material.from_dict(m.to_dict())
        assert m2.strength.points == pts

    def test_discrete_function_keeps_its_points(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import DiscreteFunction
        pts = [(0.0, 3.0), (50.0, 40.0), (150.0, 70.0)]
        m = Material(name="d", strength=DiscreteFunction(points=pts))
        m2 = Material.from_dict(m.to_dict())
        assert m2.strength.points == pts

    def test_generalized_anisotropic_keeps_its_rules(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        m = Material(name="g", strength=GeneralizedAnisotropic())
        m2 = Material.from_dict(m.to_dict())
        assert m2.strength.rules == m.strength.rules

    def test_a_plain_model_is_unaffected(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        m = Material(name="mc",
                     strength=MohrCoulomb(cohesion=12.5, friction_angle=31.0))
        m2 = Material.from_dict(m.to_dict())
        assert m2.strength.params == m.strength.params

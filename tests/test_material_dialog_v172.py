# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Water parameters where they belong, and drawdown parameters only when asked.

The invariant protected here is about WHERE a setting lives, and it has
two halves that must not be confused with each other:

* What the PROJECT makes irrelevant is HIDDEN. The rapid-drawdown group
  used to occupy a quarter of the material editor in every project, most
  of which never run a drawdown; the grid switch decides nothing without
  a grid; and under a finite-element analysis the whole water group is
  replaced by the unsaturated parameters. Hiding is not losing: the
  analysis that needs the field is what brings it back.

* What the MATERIAL's own choice makes irrelevant is only DISABLED, so
  that changing the choice back shows the value that was there. This is
  the older convention of this dialog and it stays.

Getting those two backwards is what makes an interface either cluttered
or forgetful, so each is pinned separately below.

The numeric anchor is rule 7 applied to the new ``use_grid`` switch: a
control that does not move the number is worse than no control, because
the user believes the analysis respects it. With a grid of CONSTANT
value, turning the switch off must change ``u`` by exactly that constant
— an analytic identity, not a captured number, because any interpolation
of a constant field is that constant whatever the scheme.
"""
from __future__ import annotations

from PySide6.QtWidgets import QApplication

# Keep dialogs alive: a garbage-collected QWidget takes its children with
# it and the assertions below would read a dead object.
_WINDOWS: list = []


def _app():
    return QApplication.instance() or QApplication([])


def _material(**kw):
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    kw.setdefault("name", "M1")
    kw.setdefault("strength", MohrCoulomb(cohesion=15.0, friction_angle=25.0))
    return Material(**kw)


def _dialog(materials=None, **kw):
    from ogr_gui.dialogs.material_properties_dialog import (
        MaterialPropertiesDialog,
    )
    _app()
    d = MaterialPropertiesDialog(materials or [_material()], None, **kw)
    _WINDOWS.append(d)
    d.list.setCurrentRow(0)
    return d


# ======================================================================
# What the project makes irrelevant is hidden
# ======================================================================
class TestTheDrawdownGroupOnlyAppearsForADrawdown:

    def test_it_is_gone_without_a_rapid_drawdown_analysis(self):
        d = _dialog()
        assert d.grp_drawdown.isVisibleTo(d) is False

    def test_it_is_there_with_one(self):
        d = _dialog(rapid_drawdown=True)
        assert d.grp_drawdown.isVisibleTo(d) is True

    def test_b_bar_shows_for_the_effective_stress_procedure_only(self):
        """B̄ and the undrained envelope belong to different procedures.

        Showing both at once showed every user at least one field their
        analysis ignores, which is the interface half of rule 7.
        """
        d = _dialog(rapid_drawdown=True, drawdown_method="b_bar")
        assert d.dsp_b_bar.isVisibleTo(d) is True
        assert d.lbl_envelope.isVisibleTo(d) is False

    def test_the_envelope_shows_for_the_multi_stage_procedures_only(self):
        for method in ("duncan_wright", "corps_2", "lowe_karafiath"):
            d = _dialog(rapid_drawdown=True, drawdown_method=method)
            assert d.lbl_envelope.isVisibleTo(d) is True, method
            assert d.dsp_b_bar.isVisibleTo(d) is False, method


class TestTheWaterGroupFollowsTheGroundwaterMethod:

    def test_a_finite_element_analysis_replaces_it(self):
        """The pore pressures come from the seepage solution; what the
        material still contributes is phi_b and the air entry value."""
        d = _dialog(gw_method="fea_steady")
        assert d.grp_water.isVisibleTo(d) is False
        assert d.dsp_phi_b.isVisibleTo(d) is True

    def test_the_unsaturated_fields_are_gone_otherwise(self):
        d = _dialog(gw_method="water_table")
        assert d.grp_water.isVisibleTo(d) is True
        assert d.dsp_phi_b.isVisibleTo(d) is False

    def test_the_unsaturated_labels_go_with_their_fields(self):
        """v0.1.72 — they used to stay behind, two captions over nothing.

        The old code asked ``parentWidget()`` for the label and got the
        group box, so it hid the spinbox a second time instead.
        """
        d = _dialog(gw_method="water_table")
        for wgt in (d.dsp_phi_b, d.dsp_aev):
            label = d._general_form.labelForField(wgt)
            assert label is not None
            assert label.isVisibleTo(d) is False

    def test_the_grid_switch_only_appears_with_a_grid_method(self):
        assert _dialog(gw_method="water_table").chk_use_grid.isVisibleTo(
            _WINDOWS[-1]) is False
        for method in ("grid_total_head", "grid_pressure_head",
                       "grid_pore_pressure"):
            d = _dialog(gw_method=method)
            assert d.chk_use_grid.isVisibleTo(d) is True, method


# ======================================================================
# What the material's own choice makes irrelevant is disabled
# ======================================================================
class TestTheMaterialsOwnChoiceOnlyGreysThings:

    def test_the_envelope_button_is_disabled_for_a_draining_material(self):
        d = _dialog(rapid_drawdown=True, drawdown_method="duncan_wright")
        assert d.btn_envelope.isEnabled() is False
        d.chk_undrained.setChecked(True)
        assert d.btn_envelope.isEnabled() is True
        # Disabled, never hidden: the capability stays discoverable.
        assert d.btn_envelope.isVisibleTo(d) is True

    def test_ru_and_constant_u_answer_to_the_type(self):
        from ogr_core.materials import PorePressureType
        d = _dialog()
        d.cbo_pp.setCurrentIndex(
            d.cbo_pp.findData(PorePressureType.RU_COEFFICIENT))
        assert d.dsp_ru.isEnabled() is True
        assert d.dsp_u.isEnabled() is False
        d.cbo_pp.setCurrentIndex(
            d.cbo_pp.findData(PorePressureType.CONSTANT))
        assert d.dsp_ru.isEnabled() is False
        assert d.dsp_u.isEnabled() is True

    def test_three_strength_models_read_no_pore_pressure_at_all(self):
        """The reference disables water parameters outright for these.

        None of the three consults a pore pressure, so offering the
        inputs would suggest an influence that does not exist.
        """
        d = _dialog()
        assert d.cbo_pp.isEnabled() is True
        for mid in ("undrained", "no_strength", "infinite_strength"):
            index = d.cbo_strength.findData(mid)
            assert index >= 0, mid
            d.cbo_strength.setCurrentIndex(index)
            assert d.cbo_pp.isEnabled() is False, mid
        d.cbo_strength.setCurrentIndex(
            d.cbo_strength.findData("mohr_coulomb"))
        assert d.cbo_pp.isEnabled() is True

    def test_switching_the_grid_off_hands_the_material_its_own_model(self):
        d = _dialog(gw_method="grid_pore_pressure")
        assert d.cbo_pp.isEnabled() is False
        d.chk_use_grid.setChecked(False)
        assert d.cbo_pp.isEnabled() is True


# ======================================================================
# Rule 7: the new switch has to move the number
# ======================================================================
def _grid_project(u_value: float):
    """A one-material project under a grid of CONSTANT pore pressure.

    Any interpolation of a constant field is that constant, whichever
    scheme runs, so the comparison below is exact rather than
    tolerance-bound.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.hydraulic import GridValueType, WaterPressureGrid
    from ogr_core.project import Project
    from ogr_core.project.settings import GroundwaterMethod

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(60, 0), Vertex(60, 10),
        Vertex(35, 10), Vertex(15, 30), Vertex(0, 30),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("grid")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials.append(_material())
    p.water_pressure_grid = WaterPressureGrid(
        points=[(x, y, u_value) for x in (0.0, 30.0, 60.0)
                for y in (0.0, 15.0, 30.0)],
        value_type=GridValueType.PORE_PRESSURE,
        interpolation="idw",
    )
    p.settings.groundwater.method = GroundwaterMethod.GRID_PORE_PRESSURE.value
    return p


class TestTheGridSwitchMovesTheNumber:

    def test_on_the_grid_governs_and_off_it_does_not(self):
        from ogr_core.geometry import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at

        p = _grid_project(42.0)
        mat = p.materials[0]
        point = Vertex(30.0, 5.0)

        assert mat.use_grid is True
        assert abs(pore_pressure_at(p, point, mat) - 42.0) < 1e-9

        # Off, the material falls back to its own water parameters, which
        # are the default NONE — so the grid's contribution disappears in
        # full rather than partially.
        mat.use_grid = False
        assert abs(pore_pressure_at(p, point, mat)) < 1e-12

    def test_off_the_materials_own_model_is_what_applies(self):
        """Not a blanket zero: the switch hands control back, it does not
        take it away. A material with its own Ru keeps using it."""
        from ogr_core.geometry import Vertex
        from ogr_core.hydraulic.pore_pressure import pore_pressure_at
        from ogr_core.materials import PorePressureType

        p = _grid_project(42.0)
        mat = p.materials[0]
        mat.use_grid = False
        mat.pore_pressure = PorePressureType.RU_COEFFICIENT
        mat.ru = 0.5
        # u = ru·γ·z with z the depth below the ground surface.
        u = pore_pressure_at(p, Vertex(30.0, 5.0), mat, ground_surface_y=15.0)
        assert abs(u - 0.5 * mat.unit_weight * 10.0) < 1e-9

    def test_the_default_leaves_every_existing_project_untouched(self):
        """Files written before the switch existed always had the grid on,
        so True is the only default that cannot change a saved result."""
        from ogr_core.materials import Material
        m = Material.from_dict(_material().to_dict())
        assert m.use_grid is True
        data = _material().to_dict()
        del data["use_grid"]
        assert Material.from_dict(data).use_grid is True


class TestTheSwitchSurvivesASaveAndTheDialog:

    def test_it_round_trips_through_to_dict(self):
        from ogr_core.materials import Material
        m = _material()
        m.use_grid = False
        assert Material.from_dict(m.to_dict()).use_grid is False

    def test_the_dialog_writes_it_back(self):
        d = _dialog(gw_method="grid_pore_pressure")
        d.chk_use_grid.setChecked(False)
        d._store(0)
        assert d.materials[0].use_grid is False


class TestTheEnvelopeSurvivesTheMove:
    """It now lives in a dialog of its own; it must still reach the
    material and the file."""

    def _sub(self, envelope=None):
        from ogr_gui.dialogs.drawdown_strength_dialog import (
            DrawdownStrengthDialog,
        )
        _app()
        # Built directly rather than through the button, which calls
        # exec() and would block forever without a screen.
        sub = DrawdownStrengthDialog(envelope, None)
        _WINDOWS.append(sub)
        return sub

    def test_it_reaches_the_material_and_the_file(self):
        from ogr_core.materials import Material
        from ogr_core.materials.drawdown_envelopes import REnvelope

        d = _dialog(rapid_drawdown=True, drawdown_method="duncan_wright")
        sub = self._sub()
        sub.cbo_kind.setCurrentIndex(sub.cbo_kind.findData("r"))
        sub.dsp_a.setValue(60.0)
        sub.dsp_b.setValue(23.0)
        d._envelope = sub.envelope()
        d._store(0)

        env = d.materials[0].drawdown_envelope
        assert isinstance(env, REnvelope)
        again = Material.from_dict(d.materials[0].to_dict()).drawdown_envelope
        assert isinstance(again, REnvelope)
        assert abs(again.c_r - 60.0) < 1e-9
        assert abs(again.phi_r_deg - 23.0) < 1e-9

    def test_none_stays_none(self):
        sub = self._sub()
        assert sub.envelope() is None
        assert sub.dsp_a.isEnabled() is False

    def test_the_summary_names_the_form_it_describes(self):
        from ogr_core.materials.drawdown_envelopes import Kc1Envelope, REnvelope
        from ogr_gui.dialogs.drawdown_strength_dialog import envelope_summary
        from ogr_gui.i18n import current_language, set_language

        prev = current_language()
        try:
            set_language("en")
            assert "Cr" in envelope_summary(REnvelope(c_r=60.0,
                                                      phi_r_deg=23.0))
            assert "Kc" in envelope_summary(Kc1Envelope(d=64.0,
                                                        psi_deg=24.4))
            assert envelope_summary(None) == "(none)"
        finally:
            set_language(prev)


class TestTheNewStringsAreTranslated:
    """Rule 2 — a wrapped key with no Spanish entry is a visible English
    string in a Spanish interface."""

    KEYS = [
        "Water Parameters",
        "Use the water pressure grid",
        "Define Strength...",
        "Define Strength",
    ]

    def test_every_new_key_has_a_spanish_entry(self):
        """Checked through ``tr()`` rather than the dictionary, so this
        keeps working if the storage ever changes: a key with no entry
        falls back to itself, which is the symptom the user would see."""
        from ogr_gui.i18n import current_language, set_language, tr

        prev = current_language()
        try:
            set_language("es")
            untranslated = [k for k in self.KEYS if tr(k) == k]
            assert not untranslated, untranslated
        finally:
            set_language(prev)

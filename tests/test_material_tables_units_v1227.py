# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.227 — the material dialog's tables and boxes speak the project's
units, refuse what they cannot store, and move nothing nobody edited
(defect D217 of the verification bank, with its findings B, C, D, F, H, L
and M), and the interpretation window prints Newmark's displacement in the
project's small length (defect D225).

THE DEFECTS.

* D217: the tables of the shear-normal and discrete functions showed and
  stored kPa under a fixed "σ'ₙ (kPa)", "τ (kPa)" whatever the project's
  units; their headers were not translated; ``get_params`` dropped a row
  that was not numbers without a word (and, for the anisotropic function,
  D209's check ran at OK only).
* B: moving to another material, or adding one, stored the table without
  that check.
* C: the discrete function showed the shear-normal function's default.
* D: a table stored empty was shown, and stored, as the default.
* F: the constant pore pressure carried a fixed " kPa" and the air entry
  value no unit at all, both unconverted; their tooltips were not
  translated.
* H: the API accepted an empty table, which answered τ = 0 at every base.
* L: showing a table saved as points before 0.1.218 and moving on stored
  it as ranges, unreviewed.
* M: γ, u, the air entry value, ru, Hu, B̄ and φb sat in boxes with 2 to 4
  decimals (the class of D181), and in a unit system with a factor every OK
  rewrote them, x·f/f being x only to an ulp.
* D225: ``_reported_value`` asked ``units.unit_system()``, which does not
  exist; a bare ``except`` hid it and every project read centimetres.

THE INVARIANTS: the displayed value is the SI value in the project's unit;
a value nobody edited goes back bit for bit; an edited one is converted
with the same function the strength parameters use; a table the dialog
cannot store is refused where the user can fix it, with no modal box.

DISCRIMINATION, measured on the v0.1.226 tree: 18 of the 20 cases fail
there. 12 fail by behaviour (the conversions, the rows refused at OK, on
leaving and on adding, the empty table, the legacy table kept, the boxes'
units and rounding, the API, Newmark in inches); 6 by a symbol that did
not exist. The SI round trip and the centimetres pass.
"""
from __future__ import annotations

import math

PSF = 20.88543423315013      # kPa -> psf, the imperial_psf factor


def _units(system_id="imperial_psf"):
    from ogr_core.project.units import Units
    return Units(system_id=system_id)


def _dialog(*strengths, units=None):
    from PySide6.QtWidgets import QApplication
    from ogr_core.materials import Material
    from ogr_gui.dialogs.material_properties_dialog import (
        MaterialPropertiesDialog)
    QApplication.instance() or QApplication([])
    mats = [Material(name=f"m{i}", unit_weight=19.0 + i, strength=s)
            for i, s in enumerate(strengths)]
    dlg = MaterialPropertiesDialog(mats, units_obj=units)
    dlg.list.setCurrentRow(0)
    # v0.1.231 -- the lambda keeps the LIST, not the dialog: capturing
    # the dialog made a cycle the garbage collector broke at any later
    # moment, inside another test; a Qt object destroyed there is the
    # likely cause of the segfault of the 3.12 job of v0.1.230.
    calls = dlg.accepted_calls = []
    dlg.accept = lambda: calls.append(True)
    return dlg


def _cells(dlg):
    tbl = dlg.param_panel._table
    return [[tbl.item(r, c).text() for c in range(tbl.columnCount())]
            for r in range(tbl.rowCount())]


def _set_cell(dlg, r, c, text):
    from PySide6.QtWidgets import QTableWidgetItem
    dlg.param_panel._table.setItem(r, c, QTableWidgetItem(text))


def _snf(points=((0.0, 5.0), (100.0, 45.0), (300.0, 110.0))):
    from ogr_core.materials.builtin_models import ShearNormalFunction
    return ShearNormalFunction(points=list(points))


# ======================================================================
class TestTablesSpeakTheProjectsUnits:

    def test_the_cells_and_headers_are_in_psf(self):
        dlg = _dialog(_snf(), units=_units())
        headers = dlg.param_panel.table_headers()
        assert all("psf" in h for h in headers), headers
        cells = _cells(dlg)
        assert math.isclose(float(cells[1][0]), 100.0 * PSF, rel_tol=1e-15)
        assert math.isclose(float(cells[1][1]), 45.0 * PSF, rel_tol=1e-15)

    def test_the_headers_are_translated(self):
        from ogr_gui.i18n import current_language, set_language
        old = current_language()
        try:
            set_language("es")
            dlg = _dialog(_snf(), units=_units())
            assert dlg.param_panel.table_headers()[0].startswith(
                "Tensión normal")
        finally:
            set_language(old)

    def test_ok_without_touching_is_bit_for_bit(self):
        pts = [(0.0, 5.123456789), (97.3, 44.0000001), (301.7, 110.9)]
        dlg = _dialog(_snf(pts), units=_units())
        dlg._ok()
        assert dlg.accepted_calls == [True]
        assert dlg.result_materials()[0].strength.points == pts

    def test_an_edited_cell_is_converted_back(self):
        dlg = _dialog(_snf(), units=_units())
        _set_cell(dlg, 1, 1, "1000")
        dlg._ok()
        tau = dlg.result_materials()[0].strength.points[1][1]
        assert math.isclose(tau, 1000.0 / PSF, rel_tol=1e-15), tau

    def test_the_anisotropic_function_converts_c_and_not_the_angles(self):
        from ogr_core.materials.builtin_models import (
            AnisotropicStrengthFunction)
        dlg = _dialog(AnisotropicStrengthFunction(), units=_units())
        headers = dlg.param_panel.table_headers()
        assert "°" in headers[0] and "psf" in headers[1] and \
            "°" in headers[2], headers
        cells = _cells(dlg)
        assert float(cells[0][0]) == -30.0 and float(cells[0][2]) == 35.0
        assert math.isclose(float(cells[0][1]), 10.0 * PSF, rel_tol=1e-15)


class TestDefaultsAndEmptyTables:

    def test_the_discrete_function_shows_its_own_default(self):
        from ogr_core.materials.builtin_models import (DiscreteFunction,
                                                       MohrCoulomb)
        dlg = _dialog(MohrCoulomb())
        dlg.cbo_strength.setCurrentIndex(
            dlg.cbo_strength.findData("discrete_function"))
        want = [list(map(float, p)) for p in DiscreteFunction.DEFAULT_POINTS]
        got = [[float(t) for t in row] for row in _cells(dlg)]
        assert got == want, got

    def test_an_empty_stored_table_is_shown_empty_and_said(self):
        """Shown empty, with the reason on screen; OK judges what the session
        changed (v0.1.225), so the analysis is what refuses it."""
        from ogr_slip2d.analysis_runner import check_analysis_settings
        from ogr_core.project import Project
        dlg = _dialog(_snf([]))
        assert _cells(dlg) == []
        assert not dlg.lbl_strength_problem.isHidden()
        p = Project("empty")
        p.materials = [dlg.materials[0]]
        assert any("no points" in s for s in check_analysis_settings(p))

    def test_an_emptied_table_is_refused_at_ok(self):
        dlg = _dialog(_snf())
        for _ in range(3):
            dlg.param_panel._table.removeRow(0)
        dlg._ok()
        assert dlg.accepted_calls == []
        assert not dlg.lbl_strength_problem.isHidden()


class TestRowsThatAreNotNumbers:

    def test_ok_refuses_with_the_right_count(self):
        dlg = _dialog(_snf())
        _set_cell(dlg, 1, 0, "abc")
        dlg._ok()
        assert dlg.accepted_calls == []
        text = dlg.lbl_strength_problem.text()
        assert "2" in text and "3" not in text.split("2")[0], text

    def test_leaving_the_material_is_refused_and_keeps_the_rows(self):
        from ogr_core.materials.builtin_models import MohrCoulomb
        dlg = _dialog(_snf(), MohrCoulomb())
        _set_cell(dlg, 1, 1, "4 5")
        dlg.list.setCurrentRow(1)
        assert dlg.list.currentRow() == 0
        assert dlg._current_row == 0
        assert _cells(dlg)[1][1] == "4 5"
        assert not dlg.lbl_strength_problem.isHidden()

    def test_adding_a_material_is_refused(self):
        dlg = _dialog(_snf())
        _set_cell(dlg, 0, 0, "")
        dlg._add_material()
        assert len(dlg.materials) == 1

    def test_a_non_finite_value_is_not_a_number(self):
        dlg = _dialog(_snf())
        _set_cell(dlg, 2, 1, "nan")
        assert dlg.param_panel.unparsed_table_rows() == [3]


class TestALegacyTableIsNotConvertedByLooking:

    def test_moving_to_another_material_keeps_its_points(self):
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.materials.strength_model import StrengthModel
        legacy = StrengthModel.from_dict({
            "model_id": "anisotropic_strength_function", "params": {},
            "points": [[-90.0, 20.0, 30.0], [0.0, 5.0, 15.0],
                       [90.0, 20.0, 30.0]]})
        dlg = _dialog(legacy, MohrCoulomb())
        dlg.list.setCurrentRow(1)
        assert dlg.materials[0].strength.legacy_points is not None


class TestTheMaterialsBoxes:

    def test_u_and_the_air_entry_value_in_the_projects_unit(self):
        from ogr_core.materials import Material, MohrCoulomb
        from PySide6.QtWidgets import QApplication
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog)
        QApplication.instance() or QApplication([])
        m = Material(name="w", unit_weight=19.0, strength=MohrCoulomb(),
                     constant_u=12.5, air_entry_value=7.25)
        dlg = MaterialPropertiesDialog([m], units_obj=_units())
        dlg.list.setCurrentRow(0)
        assert "psf" in dlg.dsp_u.suffix() and "psf" in dlg.dsp_aev.suffix()
        assert math.isclose(dlg.dsp_u.value(), 12.5 * PSF, rel_tol=1e-15)
        assert math.isclose(dlg.dsp_aev.value(), 7.25 * PSF, rel_tol=1e-15)
        dlg.dsp_u.setValue(500.0)
        dlg.accept = lambda: None
        dlg._ok()
        out = dlg.result_materials()[0]
        assert math.isclose(out.constant_u, 500.0 / PSF, rel_tol=1e-15)
        assert out.air_entry_value == 7.25

    def test_nothing_rounds_or_drifts_on_an_untouched_ok(self):
        """γ at 4 decimals, u at 2, B̄ at 3...: every one of them used to
        be rounded on OK, and the converted ones to drift by an ulp."""
        from ogr_core.materials import Material, MohrCoulomb
        from PySide6.QtWidgets import QApplication
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog)
        QApplication.instance() or QApplication([])
        m = Material(name="w", unit_weight=19.123456789,
                     sat_unit_weight=20.987654321, strength=MohrCoulomb(),
                     ru=0.12345678, constant_u=12.3456789,
                     air_entry_value=7.654321, phi_b=12.3456789,
                     b_bar=0.87654321)
        m.hu = 0.98765432
        for units in (None, _units()):
            dlg = MaterialPropertiesDialog([m], units_obj=units)
            dlg.list.setCurrentRow(0)
            dlg.accept = lambda: None
            dlg._ok()
            out = dlg.result_materials()[0]
            for attr in ("unit_weight", "sat_unit_weight", "ru",
                         "constant_u", "air_entry_value", "phi_b", "b_bar"):
                assert getattr(out, attr) == getattr(m, attr), (units, attr)


class TestTheRuleAndTheAPI:

    def test_what_a_table_may_hold(self):
        from ogr_core.project.rules import function_points_refusal as why
        assert why([(0, 5), (100, 45)]) is None
        assert why([]).code == "function_points_empty"
        assert why([(0, "x")]).code == "function_points_not_points"
        assert why([(0, float("inf"))]).code == "function_points_not_points"
        assert why([(0, -1.0)]).code == "function_points_strength"
        assert why([(0, 5), (0, 7)]).code == "function_points_order"

    def test_the_api_refuses_an_empty_table(self):
        from ogr_api.catalog import strength_from_spec
        from ogr_api.errors import InvalidArgument
        for mid in ("shear_normal_function", "discrete_function"):
            try:
                strength_from_spec({"model": mid, "points": []})
            except InvalidArgument as exc:
                assert "no points" in str(exc)
            else:
                raise AssertionError(f"{mid}: an empty table was accepted")

    def test_every_header_has_its_spanish(self):
        """The headers are translated through a variable, which the
        coverage test cannot see."""
        from ogr_gui.dialogs.material_properties_dialog import (
            _StrengthParamPanel)
        from ogr_gui.i18n import _DICTS
        missing = [text for cols in _StrengthParamPanel._TABLE_COLUMNS.values()
                   for text, _q in cols if text not in _DICTS["es"]]
        assert not missing, missing


class TestNewmarkInTheProjectsUnit:
    """D225."""

    def _result(self):
        from ogr_slip2d.search import SearchResult

        class _Item:
            is_valid = True
            admissible = True
            fos = 1.2
            iterations = 3
            surface = None

            def __init__(self, det):
                self.details = det

        r = SearchResult(method_id="bishop_simplified", objective="ky")
        r.evaluations.append(_Item({"ky": 0.14,
                                    "newmark_displacement": 0.05042}))
        r.valid_count = 1
        return r

    def _text(self, project):
        from ogr_gui.interpret_window import _reported_value
        r = self._result()
        return _reported_value(r, r.critical, project)[0]

    def test_inches_in_an_imperial_project(self):
        from ogr_core.project import Project
        p = Project("imperial")
        p.settings.units = _units()
        assert self._text(p) == "%.3f in" % (0.05042 / 0.0254)

    def test_centimetres_in_si_and_without_a_project(self):
        from ogr_core.project import Project
        assert self._text(Project("si")) == "5.042 cm"
        assert self._text(None) == "5.042 cm"

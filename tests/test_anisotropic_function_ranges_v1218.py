# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.218 — the Anisotropic Strength Function is a table of RANGES, as the
reference documents it (defect D209 of the verification bank).

THE DEFECT. The reference documentation defines this strength type as
"discrete angular ranges of slice base inclination, each with its own
cohesion and friction angle", entered as rows of "Angle To, c and phi": the
first range starts at -90, the last must end at +90, and c and phi are
constant inside each range. OGR kept a table of POINTS (angle, c, phi) and
interpolated linearly between them, so one table meant two different
materials in the two programs.

THE DECISIONS (owner, 2026-09-28):

* ranges, as the reference: ``rows`` of (angle to, c, phi), each holding
  from the previous row's angle (exclusive; -90 for the first) up to its
  own (inclusive). The documentation does not say which range owns an
  angle exactly on a limit; the lower one does, the convention of
  ``GeneralizedAnisotropic._model_for_angle``;
* a NEW key, ``rows``: the model interpolated in v0.1.15–v0.1.125 and in
  v0.1.215–v0.1.217, and a .ogr does not record which version wrote it, so
  a file that still holds ``points`` opens and keeps them but the analysis
  refuses it. Reading them as ranges would change the number in silence;
* one rule for what a table may be (``rules.
  anisotropic_function_rows_refusal``), asked by the dialog, the API and
  the analysis;
* the angle is folded into (-90, 90]: a support reads the model at the
  angle of its axis, ``atan2`` of head to tail, and a plane at 165 degrees
  is the plane at -15 (a defect of the same class, entered in D209).

THE REFERENCES (rule 1): the example the documentation draws for the
strength type, -90..-30 → (10, 35), -30..0 → (1, 20), 0..90 → (5, 10),
written by hand; and an identity: a range no base reaches cannot move the
factor, while under interpolation it would.

DISCRIMINATION, measured on the v0.1.217 tree: the cases that read the
ranges, the rule, the legacy refusal and the fold fail there; the
controls pass.
"""
from __future__ import annotations

import math

#: The documented example, which is also the model's default table.
DOC_ROWS = [(-30.0, 10.0, 35.0), (0.0, 1.0, 20.0), (90.0, 5.0, 10.0)]
#: What the model interpolated from v0.1.15 to v0.1.217 by default.
OLD_DEFAULT_POINTS = [(-90.0, 20.0, 30.0), (0.0, 5.0, 15.0),
                      (90.0, 20.0, 30.0)]
#: A dry circle whose bases run from about -18 to +62 degrees: they reach
#: the second and third ranges of ``DOC_ROWS`` and never the first.
CIRCLE = (38.0, 22.0, 23.0)
N_SLICES = 30


def _model(rows=None, **kw):
    from ogr_core.materials.builtin_models import AnisotropicStrengthFunction
    if rows is None and "points" not in kw:
        return AnisotropicStrengthFunction()
    if rows is None:
        return AnisotropicStrengthFunction(**kw)
    try:
        return AnisotropicStrengthFunction(rows=rows)
    except ValueError as exc:
        # A tree before v0.1.218 has no ``rows``: the same numbers go in as
        # the points it read, so a case falls there by the NUMBER (the
        # interpolation) and not by the missing keyword.
        if "rows" not in str(exc):
            raise
        return AnisotropicStrengthFunction(points=rows)


def _ctx(angle_deg):
    from ogr_core.materials.strength_model import SliceContext
    return SliceContext(base_angle_rad=math.radians(angle_deg))


def _tau(model, angle_deg, sigma=50.0):
    return model.shear_strength_ctx(sigma, _ctx(angle_deg))


def _mc(c, phi, sigma=50.0):
    return c + sigma * math.tan(math.radians(phi))


def _project(strength):
    """The dry 1V:1.67H slope of the v0.1.15 strength-model tests."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.project import Project
    h, toe = 12.0, 30.0
    crest = toe + h / math.tan(math.radians(30.96))
    ext = Polyline(vertices=[
        Vertex(0, -10), Vertex(60, -10), Vertex(60, h),
        Vertex(crest, h), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("ranges")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    mat = Material(name="bedded", unit_weight=20.0, strength=strength)
    p.materials = [mat]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), mat.id)
    return p


def _fos(strength, method_id="bishop_simplified"):
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    p = _project(strength)
    circle = SlipCircle(*CIRCLE)
    sl = slice_surface(p, circle, num_slices=N_SLICES)
    return method_registry()[method_id]().compute_fos(p, circle, sl)


# ======================================================================
class TestTheDocumentedExample:
    """Written by hand from the documentation's figure."""

    def test_each_range_holds_its_own_c_and_phi(self):
        m = _model(DOC_ROWS)
        for angle, (c, phi) in ((-89.0, (10.0, 35.0)), (-60.0, (10.0, 35.0)),
                                (-29.5, (1.0, 20.0)), (-5.0, (1.0, 20.0)),
                                (0.5, (5.0, 10.0)), (45.0, (5.0, 10.0)),
                                (89.9, (5.0, 10.0))):
            assert math.isclose(_tau(m, angle), _mc(c, phi),
                                rel_tol=1e-12), angle

    def test_c_and_phi_are_constant_inside_a_range(self):
        m = _model(DOC_ROWS)
        assert _tau(m, 1.0) == _tau(m, 44.0) == _tau(m, 89.0)
        assert _tau(m, -29.0) == _tau(m, -15.0) == _tau(m, -0.5)

    def test_a_limit_belongs_to_the_lower_range(self):
        m = _model(DOC_ROWS)
        assert math.isclose(_tau(m, -30.0), _mc(10.0, 35.0), rel_tol=1e-12)
        assert math.isclose(_tau(m, 0.0), _mc(1.0, 20.0), rel_tol=1e-12)
        assert math.isclose(_tau(m, 90.0), _mc(5.0, 10.0), rel_tol=1e-12)

    def test_the_default_table_is_the_documented_example(self):
        from ogr_core.materials.builtin_models import (
            AnisotropicStrengthFunction)
        assert [tuple(r) for r in AnisotropicStrengthFunction().rows] \
            == DOC_ROWS


class TestTheAngleIsAPlane:
    """Folded into (-90, 90]: a plane has no sense."""

    def test_an_axis_pointing_left_is_the_same_plane(self):
        m = _model(DOC_ROWS)
        for axis, plane in ((165.0, -15.0), (-135.0, 45.0), (120.0, -60.0),
                            (-170.0, 10.0)):
            assert _tau(m, axis) == _tau(m, plane), (axis, plane)

    def test_the_vertical_is_the_last_range(self):
        m = _model(DOC_ROWS)
        assert _tau(m, -90.0) == _tau(m, 90.0) == _mc(5.0, 10.0)

    def test_a_support_reads_the_folded_angle(self):
        """``bond.soil_shear_strength_at`` passes the axis angle of a
        support; one pointing to -x used to read the last row whatever
        its inclination."""
        from ogr_core.support.bond import soil_shear_strength_at
        p = _project(_model(DOC_ROWS))
        down_right = soil_shear_strength_at(
            p, 40.0, -5.0, 60.0, axis_angle_rad=math.radians(-15.0))
        up_left = soil_shear_strength_at(
            p, 40.0, -5.0, 60.0, axis_angle_rad=math.radians(165.0))
        assert up_left == down_right, (up_left, down_right)
        assert math.isclose(down_right, _mc(1.0, 20.0, 60.0),
                            rel_tol=1e-12), down_right


class TestRangesAreNotPoints:
    """Rule 7, and the identity that tells ranges from interpolation."""

    def test_the_bases_reach_two_ranges_and_not_the_first(self):
        res = _fos(_model(DOC_ROWS))
        angles = [math.degrees(s.base_angle) for s in res.slices.slices]
        assert -30.0 < min(angles) < 0.0 < max(angles), (min(angles),
                                                         max(angles))

    def test_a_range_no_base_reaches_does_not_move_the_factor(self):
        """Changing the FIRST range, which no base on this circle reaches,
        leaves every method's factor as it was. Interpolated, the first
        point pulls every angle between -30 and 0 and the factor moves."""
        from ogr_slip2d.methods import method_registry
        other = [(-30.0, 60.0, 5.0)] + DOC_ROWS[1:]
        for mid in sorted(method_registry()):
            a = _fos(_model(DOC_ROWS), mid).fos
            b = _fos(_model(other), mid).fos
            assert a is not None and a == b, (mid, a, b)

    def test_a_range_the_bases_reach_moves_it(self):
        from ogr_slip2d.methods import method_registry
        other = DOC_ROWS[:1] + [(0.0, 8.0, 20.0)] + DOC_ROWS[2:]
        for mid in sorted(method_registry()):
            a = _fos(_model(DOC_ROWS), mid).fos
            b = _fos(_model(other), mid).fos
            assert abs(a - b) > 1e-3 * a, (mid, a, b)


class TestTheRule:

    def _why(self, rows):
        from ogr_core.project.rules import anisotropic_function_rows_refusal
        return anisotropic_function_rows_refusal(rows)

    def test_the_documented_table_is_valid(self):
        assert self._why(DOC_ROWS) is None
        assert self._why([(90.0, 5.0, 30.0)]) is None

    def test_what_it_refuses(self):
        cases = {
            "anisotropic_table_empty": [],
            "anisotropic_table_start": OLD_DEFAULT_POINTS,
            "anisotropic_table_end": [(-30.0, 10.0, 35.0), (60.0, 1.0, 20.0)],
            "anisotropic_table_order": [(10.0, 1.0, 20.0), (0.0, 5.0, 10.0),
                                        (90.0, 5.0, 10.0)],
            "anisotropic_table_strength": [(0.0, -1.0, 20.0),
                                           (90.0, 5.0, 10.0)],
            "anisotropic_table_not_rows": [(0.0, 1.0), (90.0, 5.0, 10.0)],
        }
        for code, rows in cases.items():
            why = self._why(rows)
            assert why is not None and why.code == code, (code, why)

    def test_a_friction_angle_of_ninety_is_refused(self):
        why = self._why([(90.0, 5.0, 90.0)])
        assert why is not None and why.code == "anisotropic_table_strength"

    def test_the_model_does_not_sort_the_rows(self):
        """An unordered table is refused, not silently rearranged."""
        rows = [(10.0, 1.0, 20.0), (0.0, 5.0, 10.0), (90.0, 5.0, 10.0)]
        assert [tuple(r) for r in _model(rows).rows] == rows


class TestATableSavedAsPoints:
    """A .ogr written before v0.1.218 holds ``points``."""

    def _legacy(self):
        from ogr_core.materials.strength_model import StrengthModel
        return StrengthModel.from_dict({
            "model_id": "anisotropic_strength_function", "params": {},
            "points": [list(p) for p in OLD_DEFAULT_POINTS]})

    def test_it_opens_and_keeps_its_points(self):
        m = self._legacy()
        assert m.legacy_points == OLD_DEFAULT_POINTS
        d = m.to_dict()
        assert d["points"] == [list(p) for p in OLD_DEFAULT_POINTS]
        assert "rows" not in d

    def test_it_is_never_computed_with(self):
        from ogr_core.materials.builtin_models import LegacyAnisotropicTable
        m = self._legacy()
        for call in (lambda: m.shear_strength_ctx(50.0, _ctx(10.0)),
                     lambda: m.shear_strength(50.0)):
            try:
                call()
            except LegacyAnisotropicTable:
                continue
            raise AssertionError("a legacy table was computed with")

    def test_the_analysis_refuses_it_by_name(self):
        from ogr_slip2d.analysis_runner import check_analysis_settings
        p = _project(self._legacy())
        problems = check_analysis_settings(p)
        assert any("'bedded'" in s and "0.1.218" in s for s in problems), (
            problems)

    def test_and_inside_a_generalized_anisotropic_rule(self):
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        from ogr_slip2d.analysis_runner import check_analysis_settings
        nested = GeneralizedAnisotropic(rules=[{
            "angle_min": -90.0, "angle_max": 90.0,
            "model": self._legacy().to_dict()}])
        problems = check_analysis_settings(_project(nested))
        assert any("0.1.218" in s for s in problems), problems

    def test_a_valid_table_of_ranges_is_not_refused(self):
        from ogr_slip2d.analysis_runner import check_analysis_settings
        assert not any("Anisotropic" in s for s in
                       check_analysis_settings(_project(_model(DOC_ROWS))))

    def test_rows_round_trip(self):
        from ogr_core.materials.strength_model import StrengthModel
        m = _model(DOC_ROWS)
        back = StrengthModel.from_dict(m.to_dict())
        assert back.legacy_points is None
        assert [tuple(r) for r in back.rows] == DOC_ROWS


class TestTheAPI:

    def test_rows_are_accepted(self):
        from ogr_api.catalog import strength_from_spec
        m = strength_from_spec({"model": "anisotropic_strength_function",
                                "rows": [list(r) for r in DOC_ROWS]})
        assert [tuple(r) for r in m.rows] == DOC_ROWS

    def test_a_table_that_is_not_ranges_is_refused(self):
        from ogr_api.catalog import strength_from_spec
        from ogr_api.errors import InvalidArgument
        for rows in (OLD_DEFAULT_POINTS, [(0.0, 1.0, 20.0)]):
            try:
                strength_from_spec({"model": "anisotropic_strength_function",
                                    "rows": [list(r) for r in rows]})
            except InvalidArgument:
                continue
            raise AssertionError(rows)

    def test_points_are_not_a_field_any_more(self):
        from ogr_api.catalog import strength_from_spec
        from ogr_api.errors import InvalidArgument
        try:
            strength_from_spec({"model": "anisotropic_strength_function",
                                "points": [list(p) for p in DOC_ROWS]})
        except InvalidArgument:
            return
        raise AssertionError("points were accepted")


class TestTheDialog:
    """The table editor edits ``rows``; OK refuses a table that is not
    ranges, with the reason on screen and no modal box."""

    def _dialog(self, strength):
        from PySide6.QtWidgets import QApplication
        from ogr_core.materials import Material
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog)
        QApplication.instance() or QApplication([])
        mat = Material(name="bedded", unit_weight=20.0, strength=strength)
        dlg = MaterialPropertiesDialog([mat])
        dlg.list.setCurrentRow(0)
        # Record acceptance instead of reading ``result()``: nothing is
        # executed modally here, and the enum types of ``result()`` vary
        # between PySide6 releases.
        dlg.accepted_calls = []
        dlg.accept = lambda: dlg.accepted_calls.append(True)
        return dlg

    def _table_rows(self, dlg):
        tbl = dlg.param_panel._table
        return [tuple(float(tbl.item(r, c).text()) for c in range(3))
                for r in range(tbl.rowCount())]

    def test_the_rows_are_shown_and_stored(self):
        dlg = self._dialog(_model(DOC_ROWS))
        assert self._table_rows(dlg) == DOC_ROWS
        dlg._ok()
        assert dlg.accepted_calls == [True]
        assert [tuple(r) for r in dlg.result_materials()[0].strength.rows] \
            == DOC_ROWS

    def test_a_legacy_table_is_shown_with_its_warning(self):
        from ogr_core.materials.strength_model import StrengthModel
        legacy = StrengthModel.from_dict({
            "model_id": "anisotropic_strength_function", "params": {},
            "points": [list(p) for p in OLD_DEFAULT_POINTS]})
        dlg = self._dialog(legacy)
        assert self._table_rows(dlg) == OLD_DEFAULT_POINTS
        assert not dlg.lbl_strength_problem.isHidden()
        assert "0.1.218" in dlg.lbl_strength_problem.text()

    def test_ok_refuses_a_table_that_is_not_ranges(self):
        """The old default points start at -90: as ranges the first one
        would be empty, and OK says so instead of accepting."""
        from ogr_core.materials.strength_model import StrengthModel
        legacy = StrengthModel.from_dict({
            "model_id": "anisotropic_strength_function", "params": {},
            "points": [list(p) for p in OLD_DEFAULT_POINTS]})
        dlg = self._dialog(legacy)
        dlg._ok()
        assert dlg.accepted_calls == []
        assert "-90" in dlg.lbl_strength_problem.text() \
            or "−90" in dlg.lbl_strength_problem.text()

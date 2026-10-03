# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D229 — the Discrete Function is the reference's: a strength given at
scattered (x, y) points of the material and interpolated at each slice
base; the step function of σ'ₙ that OGR called Discrete Function until
v0.1.245 is now "Step Function (σ′ₙ)", with the same τ.

**The invariant.** A Discrete Function of type ``undrained`` gives
τ = cu(x, y) and one of type ``drained`` τ = c(x, y) + σ'ₙ·tan φ(x, y), with
(x, y) the middle of the slice base and the field interpolated by its
method: inverse distance (Shepard 1968, every point weighted 1/d²), TIN
(Delaunay and the plane of the triangle), thin plate spline (Harder &
Desmarais 1972; Duchon 1976) or linear by elevation, with the reference's
secondary method (the local spline, then inverse distance) where the
chosen one cannot answer.

Against what (rule 1):

* identities: a constant field IS the Undrained or Mohr-Coulomb material
  of that constant, in the nine methods and with the four interpolations;
  a PLANAR field comes out exact from TIN (inside the hull) and from the
  spline, which reproduce linear functions by construction;
* hand calculations: inverse distance at a point of three data points;
  linear by elevation between two levels and outside them;
* a closed form for the reading point: on a φ = 0 circle Bishop's factor is
  Σ cu(xᵢ, yᵢ)·lᵢ / Σ Wᵢ·sin αᵢ, so with the driving sum taken from a
  uniform run the field's factor follows from the cu the slices should
  read at the middle of their bases;
* strength reduction: γcu divides the interpolated cu (Γ = F/1.4 on φ = 0
  with EC7 DA1-C2), and γc′, γφ′ divide c and tan φ (Γ = F/1.25);
* the migration: a file's ``discrete_function`` of (σ'ₙ, τ) points is the
  step function, τ for τ;
* the rule, the API and the dialog in psf.

The slope is the φ = 0 one of ``test_tension_crack_truncation_v1109``, its
circle (55; 58) R 34, 160 slices, methods to 1e-12. Comparisons are
relative, never ``==`` on doubles of different computations.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_REL = 1e-12
#: Four points around the sliding mass.
_XY = ((20.0, 10.0), (90.0, 10.0), (55.0, 40.0), (40.0, 25.0))


def _df(ftype, points, method="inverse_distance"):
    from ogr_core.materials.builtin_models import DiscreteFunction
    return DiscreteFunction(function_type=ftype, method=method,
                            points=points)


def _slope(strength):
    import test_tension_crack_truncation_v1109 as U
    p = U._phi0_slope(crack_y=None)
    p.materials[0].strength = strength
    return p


def _sliced(p):
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    c = SlipCircle(centre_x=55.0, centre_y=58.0, radius=34.0)
    return c, slice_surface(p, c, num_slices=160)


def _fos(p, method="bishop_simplified"):
    from ogr_core.project.design_factors import prepare_analysis_project
    from ogr_slip2d.methods import get_method
    work, _rep = prepare_analysis_project(p)
    c, sl = _sliced(work)
    r = get_method(method)(tolerance=1e-12).compute_fos(work, c, sl)
    assert r.fos is not None, (method, getattr(r, "reason", None))
    return float(r.fos)


def _nine():
    from ogr_slip2d.methods import method_registry
    names = sorted(method_registry())
    assert len(names) == 9, names
    return names


def _close(a, b, rel=_REL):
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-12)


# ======================================================================
class TestAConstantFieldIsTheMaterialOfThatConstant:

    def test_undrained_and_drained_in_the_nine_methods(self):
        from ogr_core.materials.builtin_models import MohrCoulomb, Undrained
        cu = [(x, y, 40.0) for x, y in _XY]
        cphi = [(x, y, 5.0, 30.0) for x, y in _XY]
        for m in _nine():
            u = _fos(_slope(Undrained(cohesion=40.0)), m)
            d = _fos(_slope(MohrCoulomb(cohesion=5.0, friction_angle=30.0)),
                     m)
            for method in ("inverse_distance", "tin", "thin_plate_spline",
                           "linear_by_elevation"):
                a = _fos(_slope(_df("undrained", cu, method)), m)
                b = _fos(_slope(_df("drained", cphi, method)), m)
                assert _close(a, u, 1e-12), (m, method, a, u)
                assert _close(b, d, 1e-12), (m, method, b, d)


class TestTheInterpolations:

    @staticmethod
    def _plane(x, y):
        return 20.0 + 0.5 * x - 0.8 * y

    def test_a_plane_is_exact_with_tin_inside_and_with_the_spline(self):
        pts = [(x, y, self._plane(x, y)) for x, y in
               ((0, 0), (100, 0), (100, 50), (0, 50), (50, 20))]
        tin = _df("undrained", pts, "tin")
        tps = _df("undrained", pts, "thin_plate_spline")
        for x, y in ((10, 5), (50, 25), (90, 40), (33.3, 12.7)):
            want = self._plane(x, y)
            assert _close(tin.c_phi_at(x, y)[0], want, 1e-12), (x, y)
            assert _close(tps.c_phi_at(x, y)[0], want, 1e-9), (x, y)

    def test_outside_the_tin_the_local_spline_answers(self):
        """With ten points or fewer the local spline is the spline over all
        of them; a curved field, so the answer is the spline's own."""
        pts = [(0, 0, 10.0), (10, 0, 30.0), (0, 10, 20.0), (10, 10, 70.0)]
        tin = _df("undrained", pts, "tin")
        tps = _df("undrained", pts, "thin_plate_spline")
        x, y = 15.0, 5.0       # outside the square
        assert _close(tin.c_phi_at(x, y)[0], tps.c_phi_at(x, y)[0], 1e-12)
        # and inside it is the plane of its triangle, not the spline
        inside = tin.c_phi_at(7.0, 2.0)[0]
        assert not _close(inside, tps.c_phi_at(7.0, 2.0)[0], 1e-6)

    def test_inverse_distance_by_hand(self):
        pts = [(0.0, 0.0, 10.0), (4.0, 0.0, 30.0), (0.0, 3.0, 50.0)]
        x, y = 1.0, 1.0
        w = [1.0 / ((px - x) ** 2 + (py - y) ** 2) for px, py, _ in pts]
        want = sum(wi * v for wi, (_a, _b, v) in zip(w, pts)) / sum(w)
        got = _df("undrained", pts).c_phi_at(x, y)[0]
        assert _close(got, want), (got, want)
        assert _df("undrained", pts).c_phi_at(4.0, 0.0)[0] == 30.0

    def test_linear_by_elevation_by_hand(self):
        pts = [(0.0, 0.0, 60.0), (99.0, 10.0, 40.0), (5.0, 30.0, 20.0)]
        f = _df("undrained", pts, "linear_by_elevation")
        assert _close(f.c_phi_at(70.0, 5.0)[0], 50.0)
        assert _close(f.c_phi_at(0.0, 20.0)[0], 30.0)
        assert f.c_phi_at(0.0, 99.0)[0] == 20.0
        assert f.c_phi_at(0.0, -9.0)[0] == 60.0

    def test_c_and_phi_are_interpolated_independently_and_clipped(self):
        pts = [(0.0, 0.0, 0.0, 10.0), (10.0, 0.0, 20.0, 40.0)]
        f = _df("drained", pts, "linear_by_elevation")
        c, phi = f.c_phi_at(5.0, 0.0)
        assert _close(c, 10.0) and _close(phi, 25.0)
        spline = _df("undrained", [(0, 0, 0.0), (10, 0, 0.0), (5, 5, 0.0),
                                   (5, 1, 50.0)], "thin_plate_spline")
        assert spline.c_phi_at(20.0, -20.0)[0] >= 0.0


class TestEachSliceReadsTheMiddleOfItsBase:

    def test_bishop_on_phi_0_is_the_closed_form(self):
        """F = Σ cu(xᵢ, yᵢ)·lᵢ / D, with D = Σ W·sin α taken from a uniform
        run (F₀ = cu₀·Σ l / D): the field's factor checks the cu each slice
        read, at (x_centre, middle of its base)."""
        from ogr_core.materials.builtin_models import Undrained
        pts = [(20.0, 0.0, 30.0), (95.0, 0.0, 70.0), (20.0, 45.0, 50.0),
               (95.0, 45.0, 90.0)]
        field = _df("undrained", pts)
        p0 = _slope(Undrained(cohesion=40.0))
        f0 = _fos(p0)
        _c, sl = _sliced(p0)
        lengths = [s.base_length for s in sl.slices]
        drive = 40.0 * sum(lengths) / f0
        want = sum(field.c_phi_at(s.x_centre,
                                  0.5 * (s.base_y_left + s.base_y_right))[0]
                   * s.base_length for s in sl.slices) / drive
        got = _fos(_slope(field))
        assert _close(got, want, 1e-9), (got, want)

    def test_a_field_across_moves_the_number(self):
        """Rule 7 for x: the same values swapped left for right."""
        a = _fos(_slope(_df("undrained", [(20.0, 20.0, 30.0),
                                          (90.0, 20.0, 70.0)])))
        b = _fos(_slope(_df("undrained", [(20.0, 20.0, 70.0),
                                          (90.0, 20.0, 30.0)])))
        assert abs(a / b - 1.0) > 0.05, (a, b)

    def test_a_support_reads_the_field_at_its_point(self):
        from ogr_core.support.bond import soil_shear_strength_at
        field = _df("undrained", [(20.0, 20.0, 30.0), (90.0, 20.0, 70.0)])
        p = _slope(field)
        for x in (25.0, 85.0):
            want = field.c_phi_at(x, 15.0)[0]
            got = soil_shear_strength_at(p, x, 15.0, 100.0)
            assert _close(got, want, 1e-12), (x, got, want)


class TestDesignFactors:

    def test_cu_takes_gamma_cu_and_c_phi_take_theirs(self):
        cu = _df("undrained", [(20.0, 20.0, 30.0), (90.0, 20.0, 70.0)])
        p = _slope(cu)
        q = _slope(cu)
        q.settings.design_standard.enabled = True
        q.settings.design_standard.apply_preset("eurocode7_da1c2")
        assert _close(_fos(q), _fos(p) / 1.4, 5e-9)
        cphi = _df("drained", [(20.0, 20.0, 5.0, 25.0),
                               (90.0, 20.0, 15.0, 35.0)])
        p = _slope(cphi)
        q = _slope(cphi)
        ds = q.settings.design_standard
        ds.enabled = True
        ds.standard = "custom"
        ds.factor_cohesion = ds.factor_friction = 1.25
        assert _close(_fos(q), _fos(p) / 1.25, 5e-9)


# ======================================================================
class TestTheStepFunctionAndTheFiles:

    def test_a_file_s_discrete_function_of_sigma_is_the_step_function(self):
        from ogr_core.materials.builtin_models import StepFunction
        from ogr_core.materials.strength_model import StrengthModel
        pts = [[0.0, 10.0], [100.0, 50.0], [200.0, 80.0]]
        old = StrengthModel.from_dict({"model_id": "discrete_function",
                                       "params": {}, "points": pts})
        assert isinstance(old, StepFunction)
        new = StepFunction(points=pts)
        for s in (-5.0, 0.0, 50.0, 99.9, 100.0, 150.0, 250.0):
            assert old.shear_strength(s) == new.shear_strength(s)
        assert old.to_dict()["model_id"] == "step_function"

    def test_rows_of_three_or_four_without_a_type_say_which(self):
        from ogr_core.materials.strength_model import StrengthModel
        u = StrengthModel.from_dict({"model_id": "discrete_function",
                                     "params": {},
                                     "points": [[0, 0, 30], [9, 0, 40]]})
        d = StrengthModel.from_dict({"model_id": "discrete_function",
                                     "params": {},
                                     "points": [[0, 0, 5, 30],
                                                [9, 0, 6, 31]]})
        assert (u.function_type, d.function_type) == ("undrained", "drained")

    def test_the_round_trip(self):
        from ogr_core.materials import Material
        f = _df("drained", [(0.0, 0.0, 5.0, 30.0), (9.0, 1.0, 6.0, 31.0)],
                "tin")
        m = Material.from_dict(Material(name="d", strength=f).to_dict())
        assert (m.strength.function_type, m.strength.method) == (
            "drained", "tin")
        assert m.strength.points == f.points


class TestTheRule:

    def test_its_codes(self):
        from ogr_core.project.rules import strength_model_refusal

        def code(**kw):
            from ogr_core.materials.builtin_models import DiscreteFunction
            f = DiscreteFunction(**kw)
            why = strength_model_refusal(f, "m")
            return None if why is None else why.code
        assert code() is None
        assert code(function_type="drained") is None
        assert code(function_type="other") == "discrete_function_type"
        assert code(method="kriging") == "discrete_function_method"
        assert code(points=[]) == "discrete_function_empty"
        assert code(points=[(0, 0)]) == "discrete_function_not_points"
        assert code(points=[(0, 0, -1)]) == "discrete_function_strength"
        assert code(function_type="drained",
                    points=[(0, 0, 5, 95)]) == "discrete_function_angle"
        assert code(points=[(0, 0, 5), (0, 0, 7)]) == (
            "discrete_function_repeated")
        assert code(points=[(0, 0, float("nan"))]) == (
            "discrete_function_not_points")

    def test_the_api_builds_it_and_refuses_a_bad_one(self):
        from ogr_api.catalog import strength_from_spec
        from ogr_api.errors import InvalidArgument
        m = strength_from_spec({"model": "discrete_function",
                                "function_type": "drained", "method": "tin",
                                "points": [[0, 0, 5, 30], [10, 0, 6, 31],
                                           [5, 5, 7, 32]]})
        assert (m.function_type, m.method) == ("drained", "tin")
        try:
            strength_from_spec({"model": "discrete_function",
                                "method": "chugh"})
        except InvalidArgument as exc:
            assert "interpolation method" in str(exc)
        else:
            raise AssertionError("an unknown method was accepted")


class TestTheDialog:

    def _dialog(self, strength):
        from test_material_tables_units_v1227 import _dialog, _units
        return _dialog(strength, units=_units())

    def test_in_psf_with_its_type_and_its_method(self):
        f = _df("undrained", [(3.048, 6.096, 47.88026), (6.096, 3.048,
                                                         95.76052)], "tin")
        dlg = self._dialog(f)
        panel = dlg.param_panel
        headers = panel.table_headers()
        assert "ft" in headers[0] and "ft" in headers[1], headers
        assert "psf" in headers[2], headers
        cells = [[float(t) for t in row] for row in panel._cell_texts()]
        assert _close(cells[0][0], 10.0, 1e-9) and _close(
            cells[0][2], 1000.0, 1e-5), cells
        assert panel._discrete["method"].currentData() == "tin"
        params = panel.get_params()
        assert params["points"] == f.points
        assert (params["function_type"], params["method"]) == (
            "undrained", "tin")

    def test_changing_the_type_keeps_the_points(self):
        f = _df("undrained", [(0.0, 0.0, 30.0), (9.0, 1.0, 40.0)])
        dlg = self._dialog(f)      # kept: the panel's widgets are its own
        panel = dlg.param_panel
        combo = panel._discrete["type"]
        combo.setCurrentIndex(combo.findData("drained"))
        params = panel.get_params()
        assert params["function_type"] == "drained"
        assert [tuple(r) for r in params["points"]] == [
            (0.0, 0.0, 30.0, 0.0), (9.0, 1.0, 40.0, 0.0)]
        assert len(panel.table_headers()) == 4

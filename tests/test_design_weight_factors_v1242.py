# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D226a — the permanent-action factor of a design standard multiplies the soil
weight of each slice.

**The invariant.** With a design standard on, the SOIL weight of every slice
is multiplied by γG where its base drives the sliding and by γG,fav where it
climbs against it — or by γG everywhere under the single source assumption,
the default — and every term that reads the weight follows. Until v0.1.241
``factor_permanent`` was read and never applied: on the reference's
Eurocode 7 tutorial (Smith 2006, example 5.12) the preset DA1-C1 gave the
characteristic 1.36 where the tutorial publishes 1.207. That anchor is
``test_tutorial21_eurocode_v1242``; this file holds the identities.

What each class pins, and against what
--------------------------------------
1. Frank et al. (2004), *Designers' Guide to EN 1997-1*, §11.5: with the
   whole weight factored, the over-design factor of a dry undrained slope is
   F/(γG·γcu·γR;e) — DA1-C1 F/1.35, DA2 F/1.485, DA1-C2 and DA3 F/1.4 — in
   the nine methods, on one circle.
2. Homogeneity: when the strength is proportional to the weight (c′ = 0 and
   dry, or the Vertical Stress Ratio) multiplying every weight by γG leaves
   the factor where it was, Γ = F; and the pseudo-static force, proportional
   to the weight, follows it: φ = 0 with kh gives Γ = F/1.35.
3. Slice by slice, as the reference's figure splits the mass: the slices on
   the driving side of the lowest point of the circle take γG and the
   others γG,fav, and on the φ = 0 circle Bishop converges to the closed form
   c·L·R / (γG·M_drive − γG,fav·M_resist), the moment integrals split at
   x = x_c (Bishop 1955; the convergence of
   ``test_tension_crack_truncation_v1109``).
4. The sense of sliding survives the factoring, in both failure directions
   (the bound of ``rules.design_action_factors_refusal``).
5. Rule 7: the single source option and γG,fav move the number, γG,fav does
   not while the option is on, and the dialog greys it out then.
6. The presets and the files: DA3 is DA1-C2 on a slope; an old DA3 file gets
   the corrected actions and a custom one keeps its numbers.
7. The rule, asked by the analysis, the API and the dialog's ranges.
8. What reads the result: the slice tables and the report carry the factor.
9. Off (``slicer.DESIGN_WEIGHT_FACTORS``), the v0.1.241 number; and the
   user's project is never touched.

Comparisons are relative, never ``==`` on doubles of different computations.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

_CX, _CY, _R = 55.0, 58.0, 34.0      # the circle of test_..._v1109
_SLICES = 160
#: The iterative methods stop at 1e-12 on F; measured here, an identity
#: between two converged factors holds to a few 1e-10 at worst.
_REL = 5e-9


def _slope(strength=None, mirror=False):
    """The dry φ = 0 slope of ``test_tension_crack_truncation_v1109``
    (c = 40 kPa, γ = 19), with another strength if given. ``mirror``
    reflects it about x = 50, so that it slides left to right."""
    import test_tension_crack_truncation_v1109 as U
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.project.units import FailureDirection
    p = U._phi0_slope(crack_y=None)
    if strength is not None:
        p.materials[0].strength = strength
    if mirror:
        ext = Polyline(vertices=[
            Vertex(100 - x, y) for x, y in ((0, 0), (100, 0), (100, 40),
                                           (60, 40), (30, 20), (0, 20))],
            closed=True)
        ext.ensure_ccw()
        p.boundaries = []
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.settings.units.failure_direction = FailureDirection.LEFT_TO_RIGHT
    return p


def _circle(mirror=False):
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=100.0 - _CX if mirror else _CX,
                      centre_y=_CY, radius=_R)


def _undrained():
    from ogr_core.materials.builtin_models import Undrained
    import test_tension_crack_truncation_v1109 as U
    return _slope(Undrained(cohesion=U._C))


def _standard(project, preset=None, single=True, **factors):
    ds = project.settings.design_standard
    ds.enabled = True
    if preset is not None:
        assert ds.apply_preset(preset), preset
    else:
        ds.standard = "custom"
    for name, value in factors.items():
        setattr(ds, name, value)
    ds.single_source_weight = single
    return project


def _sliced(project, mirror=False, n=_SLICES):
    """The circle sliced on the project an analysis computes on."""
    from ogr_core.project.design_factors import prepare_analysis_project
    from ogr_slip2d.slicer import slice_surface
    work, _rep = prepare_analysis_project(project)
    c = _circle(mirror)
    sl = slice_surface(work, c, num_slices=n)
    assert sl is not None
    return work, c, sl


def _fos(project, method="bishop_simplified", mirror=False, n=_SLICES):
    from ogr_slip2d.methods import get_method
    work, c, sl = _sliced(project, mirror, n)
    r = get_method(method)(tolerance=1e-12).compute_fos(work, c, sl)
    assert r.fos is not None, (method, getattr(r, "reason", None))
    return float(r.fos)


def _nine():
    from ogr_slip2d.methods import method_registry
    names = sorted(method_registry())
    assert len(names) == 9, names
    return names


def _close(a, b, rel=_REL):
    return math.isclose(a, b, rel_tol=rel)


# ======================================================================
class TestTheOverDesignFactorOfAnUndrainedSlope:
    """Frank et al. (2004), §11.5: Γ = F/(γG·γcu·γR;e)."""

    _CASES = (("eurocode7_da1c1", 1.35), ("eurocode7_da2", 1.35 * 1.1),
              ("eurocode7_da1c2", 1.4), ("eurocode7_da3", 1.4))

    def test_in_the_nine_methods(self):
        base = {m: _fos(_undrained(), m) for m in _nine()}
        for preset, divisor in self._CASES:
            p = _standard(_undrained(), preset)
            for m in _nine():
                got = _fos(p, m)
                assert _close(got, base[m] / divisor), (
                    preset, m, got, base[m] / divisor)


class TestWhatIsProportionalToTheWeight:

    def test_a_frictional_dry_slope_keeps_its_factor(self):
        """c′ = 0, dry: every force scales with the weight, so does the
        strength, and Γ = F (Frank et al. 2004, §11.5)."""
        from ogr_core.materials.builtin_models import MohrCoulomb
        mc = MohrCoulomb(cohesion=0.0, friction_angle=40.0)
        for m in _nine():
            a = _fos(_slope(mc), m)
            b = _fos(_standard(_slope(mc), "eurocode7_da1c1"), m)
            assert _close(a, b), (m, a, b)

    def test_the_vertical_stress_ratio_keeps_its_factor(self):
        """τ = K·σ′v reads the factored weight: the same weight feeds
        every term, so the factor does not move."""
        from ogr_core.materials.builtin_models import VerticalStressRatio
        vsr = VerticalStressRatio(K=0.6, min_strength=0.0)
        for m in _nine():
            a = _fos(_slope(vsr), m)
            b = _fos(_standard(_slope(vsr), "eurocode7_da1c1"), m)
            assert _close(a, b), (m, a, b)

    def test_the_seismic_force_follows_the_weight(self):
        """kh·W acts on the factored soil weight: φ = 0, Γ = F/1.35."""
        def seismic(p):
            p.seismic.enabled = True
            p.seismic.kh = 0.1
            return p
        for m in _nine():
            a = _fos(seismic(_undrained()), m)
            b = _fos(_standard(seismic(_undrained()), "eurocode7_da1c1"), m)
            assert _close(b, a / 1.35), (m, a, b, a / 1.35)


# ======================================================================
def _split_closed_form(x_l, x_r, g_drive, g_resist):
    """``F = c·L_arc·R / (γG·M_drive − γG,fav·M_resist)`` on the φ = 0 mass.

    The closed form of ``test_tension_crack_truncation_v1109``
    (``c·L_arc·R/M``, Bishop 1955) with the moment of the weight split at
    the lowest point of the circle, x = x_c: right of it the weight drives
    this right-to-left slide, left of it it resists. Simpson quadrature of
    ``γ·(y_ground − y_arc)·|x − x_c|`` on each side, from the geometry alone.
    """
    import test_tension_crack_truncation_v1109 as U

    def moment(a, b):
        n = 20001
        h = (b - a) / (n - 1)
        total = 0.0
        for i in range(n):
            x = a + i * h
            arc = _CY - math.sqrt(max(_R * _R - (x - _CX) ** 2, 0.0))
            f = U._GAMMA * (U._ground_y(x) - arc) * abs(x - _CX)
            total += (1 if i in (0, n - 1) else (4 if i % 2 else 2)) * f
        return total * h / 3.0

    l_arc = _R * (math.asin((x_r - _CX) / _R) - math.asin((x_l - _CX) / _R))
    return U._C * l_arc * _R / (g_drive * moment(_CX, x_r)
                                - g_resist * moment(x_l, _CX))


class TestSliceBySlice:

    def test_each_side_of_the_lowest_point_takes_its_factor(self):
        """Off the single source assumption, the slices right of the lowest
        point weigh exactly γG times what they weighed, and the others
        γG,fav times; on it, every slice γG times."""
        _w, _c, plain = _sliced(_slope())
        for single, fav in ((False, 0.9), (True, 0.9)):
            p = _standard(_slope(), single=single, factor_permanent=1.35,
                          factor_permanent_favourable=fav)
            _w, _c, sl = _sliced(p)
            assert len(sl.slices) == len(plain.slices)
            right = 0
            for a, b in zip(sl.slices, plain.slices):
                xi = 1.35 if (single or a.x_centre > _CX) else fav
                right += a.x_centre > _CX
                assert _close(a.weight, xi * b.weight, 1e-14), (
                    single, a.x_centre, a.weight, b.weight, xi)
                assert a.weight_factor == xi, (a.x_centre, a.weight_factor)
            assert 10 < right < len(sl.slices) - 10, "premise: both sides"

    def test_bishop_converges_to_the_split_closed_form(self):
        from ogr_slip2d.methods import get_method
        p = _standard(_slope(), single=False, factor_permanent=1.35,
                      factor_permanent_favourable=0.9)
        errors = {}
        for n in (40, 160, 640):
            work, c, sl = _sliced(p, n=n)
            got = float(get_method("bishop_simplified")(tolerance=1e-12)
                        .compute_fos(work, c, sl).fos)
            errors[n] = abs(got / _split_closed_form(
                c.x_left, c.x_right, 1.35, 0.9) - 1.0)
        # The slice base is a chord and the slice that holds the lowest
        # point takes one factor: both errors are O(1/n²).
        assert errors[640] < 1e-5, errors
        assert errors[640] < errors[160] < errors[40], errors

    def test_the_closed_form_is_not_the_single_source_one(self):
        """So the identity above discriminates: with the same factors on
        the whole mass the factor is another number."""
        split = _fos(_standard(_slope(), single=False, factor_permanent=1.35,
                               factor_permanent_favourable=0.9), n=640)
        whole = _fos(_standard(_slope(), single=True, factor_permanent=1.35),
                     n=640)
        assert abs(split / whole - 1.0) > 0.03, (split, whole)


class TestTheSenseSurvivesTheFactoring:

    def test_in_both_directions(self):
        from ogr_slip2d.design_actions import sliding_sense
        for mirror in (False, True):
            plain = _sliced(_slope(mirror=mirror), mirror)[2]
            p = _standard(_slope(mirror=mirror), single=False,
                          factor_permanent=10.0,
                          factor_permanent_favourable=0.1)
            sl = _sliced(p, mirror)[2]
            sense = sliding_sense(plain.slices)
            assert sl.design_sense == sense, (mirror, sl.design_sense)
            assert sliding_sense(sl.slices) == sense, mirror
            cx = 100.0 - _CX if mirror else _CX
            for s in sl.slices:
                drives = (s.x_centre < cx) if mirror else (s.x_centre > cx)
                assert s.weight_factor == (10.0 if drives else 0.1), (
                    mirror, s.x_centre, s.weight_factor)

    def test_the_mirror_gives_the_same_factor(self):
        p = _standard(_slope(), single=False, factor_permanent=1.35,
                      factor_permanent_favourable=0.9)
        q = _standard(_slope(mirror=True), single=False,
                      factor_permanent=1.35, factor_permanent_favourable=0.9)
        a, b = _fos(p), _fos(q, mirror=True)
        assert _close(a, b, 1e-9), (a, b)


# ======================================================================
class TestEverySettingMovesTheNumber:
    """Rule 7."""

    def test_the_single_source_option(self):
        """φ = 0: per slice the resisting side is lighter than under the
        single source assumption, so the factor is lower."""
        single = _fos(_standard(_slope(), "eurocode7_da1c1"))
        split = _fos(_standard(_slope(), "eurocode7_da1c1", single=False))
        plain = _fos(_slope())
        assert _close(single, plain / 1.35), (single, plain)
        assert split < single - 0.01, (split, single)

    def test_the_favourable_factor_only_with_the_option_off(self):
        def run(single, fav):
            return _fos(_standard(_slope(), single=single,
                                  factor_permanent=1.35,
                                  factor_permanent_favourable=fav))
        # Measured on v0.1.242: 0.78282 against 0.79139 (−1.1 %), the
        # resisting side's moment being an eighth of the driving one.
        assert run(False, 0.9) < run(False, 1.0) * 0.995
        assert _close(run(True, 0.9), run(True, 1.0), 1e-15)

    def test_the_dialog_greys_the_favourable_factor_with_the_option_on(self):
        from PySide6.QtWidgets import QApplication
        from ogr_core.project import ProjectSettings
        from ogr_gui.dialogs.project_settings_dialog import (
            _DesignStandardPage)
        QApplication.instance() or QApplication([])
        s = ProjectSettings()
        s.design_standard.enabled = True
        s.design_standard.standard = "custom"
        page = _DesignStandardPage(s)
        fav = page.factors["factor_permanent_favourable"]
        assert page.chk_single_source.isChecked()
        assert page.chk_single_source.isEnabled()
        assert not fav.isEnabled()
        page.chk_single_source.setChecked(False)
        assert fav.isEnabled()
        fav.setValue(0.9)
        page.apply()
        assert s.design_standard.single_source_weight is False
        assert s.design_standard.factor_permanent_favourable == 0.9

    def test_the_option_is_open_for_a_named_standard(self):
        """It says how the factors are laid on the slices, not which: the
        tutorial's 1.207 is DA1-C1 with it off."""
        from PySide6.QtWidgets import QApplication
        from ogr_core.project import ProjectSettings
        from ogr_gui.dialogs.project_settings_dialog import (
            _DesignStandardPage)
        QApplication.instance() or QApplication([])
        s = ProjectSettings()
        s.design_standard.enabled = True
        s.design_standard.apply_preset("eurocode7_da1c1")
        page = _DesignStandardPage(s)
        assert page.chk_single_source.isEnabled()
        assert not page.factors["factor_permanent"].isEnabled()
        page.chk_single_source.setChecked(False)
        page.apply()
        assert s.design_standard.single_source_weight is False
        assert s.design_standard.standard == "eurocode7_da1c1"


# ======================================================================
class TestThePresetsAndTheFiles:

    def test_da3_is_da1c2_on_a_slope(self):
        """DA3 factors geotechnical actions with A2, and on a slope every
        action is geotechnical (Frank et al. 2004, §11.5: γG = 1.00 in
        DA-1C2 and DA-3)."""
        from ogr_core.project.settings import DesignStandardSettings as D
        assert D.PRESETS["eurocode7_da3"] == D.PRESETS["eurocode7_da1c2"]
        a = _fos(_standard(_undrained(), "eurocode7_da3"))
        b = _fos(_standard(_undrained(), "eurocode7_da1c2"))
        assert _close(a, b, 1e-15), (a, b)

    def test_the_eurocode_actions(self):
        """EN 1997-1, Annex A, Table A.3: A1 1.35/1.0, A2 1.0/1.0."""
        from ogr_core.project.settings import DesignStandardSettings as D
        want = {"eurocode7_da1c1": (1.35, 1.0), "eurocode7_da1c2": (1.0, 1.0),
                "eurocode7_da2": (1.35, 1.0), "eurocode7_da3": (1.0, 1.0),
                "none": (1.0, 1.0)}
        for name, pair in want.items():
            s = D()
            s.apply_preset(name)
            assert (s.factor_permanent, s.factor_permanent_favourable) == pair
            assert s.single_source_weight is True

    def test_an_old_da3_file_gets_the_actions_of_a2(self):
        from ogr_core.project.settings import DesignStandardSettings as D
        old = {"enabled": True, "standard": "eurocode7_da3",
               "factor_permanent": 1.35, "factor_variable": 1.5,
               "factor_cohesion": 1.25, "factor_friction": 1.25,
               "factor_unit_weight": 1.0, "factor_resistance": 1.0,
               "factor_undrained": 1.4, "factor_shear_strength": 1.25}
        s = D.from_dict(old)
        assert (s.factor_permanent, s.factor_variable) == (1.0, 1.3)
        assert s.factor_permanent_favourable == 1.0
        assert s.single_source_weight is True

    def test_an_old_custom_file_keeps_its_numbers(self):
        from ogr_core.project.settings import DesignStandardSettings as D
        s = D.from_dict({"enabled": True, "standard": "custom",
                         "factor_permanent": 1.35, "factor_variable": 1.5})
        assert (s.factor_permanent, s.factor_variable) == (1.35, 1.5)

    def test_a_new_file_is_read_as_written(self):
        from ogr_core.project import ProjectSettings
        s = ProjectSettings()
        ds = s.design_standard
        ds.enabled = True
        ds.standard = "custom"
        ds.factor_permanent = 1.2
        ds.factor_permanent_favourable = 0.95
        ds.single_source_weight = False
        t = ProjectSettings.from_dict(s.to_dict()).design_standard
        assert (t.factor_permanent, t.factor_permanent_favourable,
                t.single_source_weight) == (1.2, 0.95, False)


# ======================================================================
class TestTheRule:

    def test_its_codes(self):
        from ogr_core.project.rules import design_action_factors_refusal
        from ogr_core.project.settings import DesignStandardSettings as D

        def code(**kw):
            s = D()
            for k, v in kw.items():
                setattr(s, k, v)
            why = design_action_factors_refusal(s)
            return None if why is None else why.code
        assert code() is None
        assert code(factor_permanent=1.0, factor_permanent_favourable=1.0) \
            is None
        assert code(factor_permanent=1.1, factor_permanent_favourable=0.9) \
            is None
        assert code(factor_permanent=0.95) == (
            "design_action_factor_unfavourable_below_one")
        assert code(factor_permanent_favourable=1.05) == (
            "design_action_factor_favourable_above_one")
        assert code(factor_permanent_favourable=0.0) == (
            "design_action_factor_favourable_not_positive")
        assert code(factor_permanent=float("nan")) == (
            "design_action_factor_not_a_number")
        assert code(factor_permanent_favourable="x") == (
            "design_action_factor_not_a_number")
        for name in D.PRESETS:
            s = D()
            s.apply_preset(name)
            assert design_action_factors_refusal(s) is None, name

    def test_the_analysis_asks_it_with_the_standard_on(self):
        from ogr_slip2d.analysis_runner import check_analysis_settings
        p = _standard(_slope(), single=False, factor_permanent=1.35,
                      factor_permanent_favourable=1.2)
        assert any("favourable permanent actions" in m
                   for m in check_analysis_settings(p))
        p.settings.design_standard.enabled = False
        assert not any("permanent actions" in m
                       for m in check_analysis_settings(p))

    def test_the_api_asks_it_when_the_standard_is_touched(self):
        from ogr_api import Conflict, Workspace, call
        ws = Workspace()
        try:
            pid = call(ws, "project_new", name="d226a")["project_id"]
            call(ws, "model_define", project_id=pid, spec={
                "external": [[0, 0], [100, 0], [100, 40], [60, 40],
                             [30, 20], [0, 20]],
                "materials": [{"name": "Clay", "unit_weight": 19.0,
                               "strength": {"model": "undrained",
                                            "params": {"cohesion": 40.0}}}]})

            def put(changes):
                return call(ws, "settings_set", project_id=pid,
                            changes=changes)
            with pytest.raises(Conflict):
                put({"design_standard.standard": "custom",
                     "design_standard.factor_permanent_favourable": 1.2})
            out = put({"design_standard.standard": "custom",
                       "design_standard.factor_permanent_favourable": 0.9,
                       "design_standard.single_source_weight": False})
            assert "design_standard.factor_permanent_favourable" in (
                out["changed"])
            # A stored value is the analysis's to refuse, not a reason to
            # refuse an edit that does not touch the standard.
            ws.get(pid).project.settings.design_standard \
                .factor_permanent_favourable = 1.2
            put({"methods.num_slices": 30})
        finally:
            ws.shutdown()

    def test_the_dialog_cannot_hold_a_pair_the_run_would_refuse(self):
        from PySide6.QtWidgets import QApplication
        from ogr_core.project import ProjectSettings
        from ogr_core.project.rules import PERMANENT_ACTION_FACTOR_BOUND
        from ogr_gui.dialogs.project_settings_dialog import (
            _DesignStandardPage)
        QApplication.instance() or QApplication([])
        page = _DesignStandardPage(ProjectSettings())
        assert page.factors["factor_permanent"].minimum() == (
            PERMANENT_ACTION_FACTOR_BOUND)
        assert page.factors["factor_permanent_favourable"].maximum() == (
            PERMANENT_ACTION_FACTOR_BOUND)
        assert page.factors["factor_permanent_favourable"].minimum() > 0.0


# ======================================================================
class TestWhatReadsTheResult:

    def test_the_slice_tables_carry_the_factor(self):
        from ogr_api.results import slice_table
        from ogr_slip2d.interpretation import slice_rows
        from ogr_slip2d.methods import get_method
        p = _standard(_slope(), single=False, factor_permanent=1.35)
        work, c, sl = _sliced(p)
        res = get_method("bishop_simplified")(tolerance=1e-12).compute_fos(
            work, c, sl)
        want = [s.weight_factor for s in sl.slices]
        assert {1.0, 1.35} == set(want)
        assert [r["weight_factor"] for r in slice_rows(res)] == want
        assert [r["weight_factor"] for r in slice_table(res)] == want
        assert [s.to_dict()["weight_factor"] for s in sl.slices] == want

    def test_the_slice_data_panel_has_the_row(self):
        from ogr_gui.interpret_window import _SliceDataDock
        assert "Weight factor" in [label for label, _ in
                                   _SliceDataDock.FIELDS]

    def test_the_report_says_what_was_factored(self):
        from ogr_core.project.design_factors import apply_design_factors
        p = _standard(_slope(), single=False, factor_permanent=1.35)
        _out, rep = apply_design_factors(p)
        assert any("drives the sliding" in n for n in rep.notes), rep.notes
        _out, rep = apply_design_factors(
            _standard(_slope(), "eurocode7_da1c1"))
        assert any("every slice" in n and "1.35" in n
                   for n in rep.notes), rep.notes

    def test_the_pdf_slice_table_has_the_column_only_when_factored(self):
        from ogr_core.report.report_generator import _slice_table
        from ogr_slip2d.methods import get_method
        for single, want in ((False, True), (None, False)):
            p = (_slope() if single is None else
                 _standard(_slope(), single=single, factor_permanent=1.35))
            work, c, sl = _sliced(p, n=20)
            res = get_method("bishop_simplified")(tolerance=1e-12) \
                .compute_fos(work, c, sl)
            header = _slice_table(res, work)._cellvalues[0]
            assert ("Weight\nfactor" in header) is want, header


# ======================================================================
class TestOffAndUntouched:

    def test_off_it_is_the_old_number(self):
        import ogr_slip2d.slicer as S
        plain = _fos(_slope())
        saved = S.DESIGN_WEIGHT_FACTORS
        try:
            S.DESIGN_WEIGHT_FACTORS = False
            off = _fos(_standard(_slope(), "eurocode7_da1c1"))
        finally:
            S.DESIGN_WEIGHT_FACTORS = saved
        on = _fos(_standard(_slope(), "eurocode7_da1c1"))
        assert _close(off, plain, 1e-15), (off, plain)
        assert _close(on, plain / 1.35), (on, plain)

    def test_the_users_project_is_never_touched(self):
        import json
        from ogr_slip2d.slicer import slice_surface
        p = _standard(_slope(), single=False, factor_permanent=1.35)
        before = json.dumps(p.to_dict(), sort_keys=True, default=str)
        work, _c, _sl = _sliced(p)
        assert work is not p
        assert work.action_factors is not None
        assert p.action_factors is None
        assert json.dumps(p.to_dict(), sort_keys=True, default=str) == before
        assert "action_factors" not in before
        mine = slice_surface(p, _circle(), num_slices=_SLICES)
        assert {s.weight_factor for s in mine.slices} == {1.0}
        assert mine.design_sense is None

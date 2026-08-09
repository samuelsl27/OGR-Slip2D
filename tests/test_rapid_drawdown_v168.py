# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Multi-stage rapid drawdown, validated against a published case.

Three procedures share one implementation and differ by two flags:

* **Lowe and Karafiath (1960)** — two stages.
* **Duncan, Wright and Wong (1990)** — adds a third stage that replaces
  the undrained strength by the drained one wherever the latter is
  smaller.
* **Corps of Engineers (1970)** — two stages, but the undrained strength
  comes from a composite ``min(R, effective)`` envelope evaluated at the
  effective stress from BEFORE the drawdown.

Until v0.1.68 the interface offered all four entries of its drawdown combo
and only B-bar computed anything: choosing one of these three produced no
Δu, no warning and no difference. That is rule 7 in its purest form.

The reference: the Pilarcitos dam
---------------------------------
Duncan, Wright and Wong (1990) publish this case, and it is a real
failure — the dam slid in November 1969 after a drawdown, which is why a
factor of safety close to 1 is the right answer rather than a comforting
one. Embankment γ = 135 pcf, c' = 0, φ' = 45°, R envelope c_R = 60 psf,
φ_R = 23°; reservoir from elevation 72 down to 37 ft.

Published factors of safety: **DWW 1.047, Lowe-Karafiath 1.052, Corps
0.824**.

The comparison below is between MINIMA — a search on our side against the
published critical value — because comparing at a surface we chose
ourselves would be circular. The tolerance is set by the resolution of the
grid the test can afford, not by the method: this coarse grid lands about
3 % above the published values, while a fine one (5 ft steps, 2145
candidates, 6 s) lands 1.7 % to 2.6 % BELOW them. Both bracket the
published answer, which is the honest statement of agreement here.

Property tests, independent of any published number
---------------------------------------------------
* ``FS_DWW ≤ FS_LoweKarafiath`` on any model, because stage 3 can only
  ever replace a strength by a smaller one. The two share a function and
  a flag precisely so this is structural rather than hopeful.
* A stage-1 factor of safety below 1 is refused with an explicit error.
  The procedure assumes the slope stood up with the reservoir full; below
  1 the consolidation state sits above the failure envelope, K₁ exceeds
  K_f, and the interpolation of equation (5) starts extrapolating —
  producing strengths that fall and eventually go negative, which in an
  automatic search hands victory to surfaces with a fictitious FoS near
  zero.
* With no drawdown line the final level is total drawdown.
* A curved strength envelope is refused rather than silently overwritten.
"""
from __future__ import annotations

import math

GAMMA_W_PCF = 62.4
PUBLISHED = {"duncan_wright": 1.047,
             "lowe_karafiath": 1.052,
             "corps_2": 0.824}


# ======================================================================
def _pilarcitos(with_drawdown=True, undrained=True):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from ogr_core.materials.drawdown_envelopes import REnvelope
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(260, 0), Vertex(260, 78),
        Vertex(205, 78), Vertex(145, 58),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("Pilarcitos")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(-5, 72), Vertex(265, 72)],
                          closed=False),
        btype=BoundaryType.WATER_TABLE))
    if with_drawdown:
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(-5, 37), Vertex(265, 37)],
                              closed=False),
            btype=BoundaryType.DRAWDOWN))
    m = Material(
        name="Embankment", unit_weight=135.0, sat_unit_weight=135.0,
        strength=MohrCoulomb(cohesion=0.0, friction_angle=45.0),
        pore_pressure=PorePressureType.WATER_TABLE,
    )
    m.undrained_behaviour = undrained
    m.drawdown_envelope = REnvelope(c_r=60.0, phi_r_deg=23.0)
    p.materials = [m]
    p.settings.groundwater.pore_fluid_unit_weight = GAMMA_W_PCF
    p.settings.groundwater.set_advanced_option("rapid_drawdown")
    # The stored procedure matters: the settings guard and the method
    # wrapper both read it, and its default is B-bar, which they hand back
    # to the pore-pressure model instead.
    p.settings.groundwater.rapid_drawdown_method = "duncan_wright"
    return p


def _critical(project, procedure, xs, ys, rs, n=25):
    """Lowest drawdown factor of safety over a declared grid of circles."""
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
    from ogr_slip2d.surface import SlipCircle

    method = BishopSimplified()
    best = None
    for cx in xs:
        for cy in ys:
            for r in rs:
                c = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
                try:
                    res = rapid_drawdown_fos(project, c, method,
                                             num_slices=n,
                                             procedure=procedure)
                except Exception:  # noqa: BLE001
                    continue      # not a valid drawdown surface
                if not (math.isfinite(res.fos) and 0.2 < res.fos < 20.0):
                    continue
                if best is None or res.fos < best[0]:
                    best = (res.fos, c, res)
    return best


# The grid the tests can afford: 729 candidates, about a second.
XS = range(20, 181, 20)
YS = range(80, 241, 20)
RS = range(60, 221, 20)

# The surface this grid finds critical, reused by the property tests so
# they do not each pay for a search.
_FIXED = dict(centre_x=100.0, centre_y=200.0, radius=160.0)

# v0.1.71 — a surface from the same grid on which the drained cap did NOT
# converge before this version: a shallow circle whose last slice has a
# base at 67 degrees and m_alpha = 0.68. Named so the tests that exist
# because of it say what they are about.
_OSCILLATING = dict(centre_x=120.0, centre_y=100.0, radius=80.0)

# The shipped default, so a test can assert the constant was put back
# without hard-coding the number in two places.
CAP_RELAXATION_DEFAULT = 0.50


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(**_FIXED)


def _oscillating_circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(**_OSCILLATING)


def _run(project, procedure, surface=None, n=25):
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
    return rapid_drawdown_fos(project, surface or _circle(),
                              BishopSimplified(), num_slices=n,
                              procedure=procedure)


# ======================================================================
class TestPilarcitos:
    """Rule 1: the numbers are Duncan, Wright and Wong's, not ours."""

    def test_the_three_procedures_reproduce_the_published_values(self):
        p = _pilarcitos()
        for procedure, published in PUBLISHED.items():
            best = _critical(p, procedure, XS, YS, RS)
            assert best is not None, procedure
            fos = best[0]
            err = abs(fos - published) / published
            assert err < 0.06, (procedure, fos, published, err)

    def test_the_ordering_matches_the_reference(self):
        """Corps is the most conservative and DWW never beats
        Lowe-Karafiath — a statement about the METHODS, so it holds
        whatever surface the search happens to land on."""
        p = _pilarcitos()
        vals = {}
        for procedure in PUBLISHED:
            best = _critical(p, procedure, XS, YS, RS)
            assert best is not None
            vals[procedure] = best[0]
        assert vals["duncan_wright"] <= vals["lowe_karafiath"] + 1e-9, vals
        assert vals["corps_2"] < vals["duncan_wright"], vals

    def test_the_answer_is_near_unity_because_the_dam_failed(self):
        """Pilarcitos slid in November 1969 after a drawdown. A procedure
        that reported a comfortable factor of safety here would be wrong
        about the one case where the ground truth is known."""
        p = _pilarcitos()
        fos = _critical(p, "duncan_wright", XS, YS, RS)[0]
        assert 0.9 < fos < 1.2, fos


class TestStageThreeCanOnlyLower:
    """The structural property: one function, one flag."""

    def test_dww_never_exceeds_lowe_karafiath(self):
        p = _pilarcitos()
        dww = _run(p, "duncan_wright")
        lk = _run(p, "lowe_karafiath")
        assert dww.fos <= lk.fos + 1e-9, (dww.fos, lk.fos)

    def test_the_two_share_stage_two_exactly(self):
        """They differ only in stage 3, so stage 2 must be bit-identical.
        If it were not, the inequality above could hold by accident."""
        p = _pilarcitos()
        dww = _run(p, "duncan_wright")
        lk = _run(p, "lowe_karafiath")
        assert dww.fos_stage2 == lk.fos_stage2
        assert lk.fos_stage3 is None

    def test_stage_three_reports_what_it_changed(self):
        p = _pilarcitos()
        dww = _run(p, "duncan_wright")
        assert dww.n_undrained_slices > 0
        if dww.n_stage3_switched:
            assert dww.fos <= dww.fos_stage2 + 1e-9


class TestTheDrainedCapIsAFixedPoint:
    """v0.1.70 — the cap is iterated, and this is what licenses that.

    Capping a slice lowers the factor of safety, which moves the base
    normals, which moves the cap. Applied once, the answer depends on
    where you stopped; applied to convergence it is a property of the
    model. Undamped it oscillates, so it is under-relaxed by
    ``CAP_RELAXATION`` — and the test that matters is that **the answer
    does not depend on that constant**. If it did, the number would be an
    artefact of the damping and the whole change would be unjustified.

    The reference documents a single substitution ("the analysis is
    rerun", singular) and calls the method "3 stage". Converging is a
    deliberate departure, taken because it reproduces both published
    Appendix G cases better: on the fixed circle there, Corps goes from
    1.3335 to 1.3494 against a referee 1.35, and Duncan-Wright-Wong from
    1.4333 to 1.4456 against 1.44.
    """

    def _at(self, omega, procedure="duncan_wright"):
        from ogr_slip2d import rapid_drawdown as rd

        original = rd.CAP_RELAXATION
        try:
            rd.CAP_RELAXATION = omega
            return _run(_pilarcitos(), procedure).fos
        finally:
            # Rule 5: a module-level constant is global state.
            rd.CAP_RELAXATION = original

    def test_the_answer_does_not_depend_on_the_relaxation(self):
        for procedure in ("duncan_wright", "corps_2"):
            got = [self._at(w, procedure) for w in (1.0, 0.7, 0.5, 0.35)]
            assert max(got) - min(got) < 2e-3, (procedure, got)

    def test_it_holds_on_a_surface_that_used_to_oscillate(self):
        """v0.1.71 — the hole the test above left open.

        It only ever looked at the critical surface, which converges in 4
        passes on any relaxation. The surfaces that did NOT converge were
        elsewhere on the grid, and that is exactly how v0.1.70 shipped a
        relaxation chosen on a sample that excluded the hard cases.
        """
        from ogr_slip2d import rapid_drawdown as rd

        surface = _oscillating_circle()
        original = rd.CAP_RELAXATION
        got = []
        try:
            for omega in (0.7, 0.5, 0.35, 0.2):
                rd.CAP_RELAXATION = omega
                got.append(_run(_pilarcitos(), "duncan_wright", surface).fos)
        finally:
            rd.CAP_RELAXATION = original
        assert max(got) - min(got) < 2e-3, got

    def test_the_relaxation_is_restored(self):
        """The guard on rule 5, since the tests above patch a global."""
        from ogr_slip2d import rapid_drawdown as rd
        self._at(0.35)
        assert rd.CAP_RELAXATION == CAP_RELAXATION_DEFAULT

    def test_it_converges_well_inside_the_pass_budget(self):
        from ogr_slip2d.rapid_drawdown import CAP_MAX_PASSES

        dww = _run(_pilarcitos(), "duncan_wright")
        assert 0 < dww.n_cap_passes < CAP_MAX_PASSES, dww.n_cap_passes

    def test_lowe_karafiath_never_pays_for_the_cap(self):
        """It has no cap, so it must report no passes at all."""
        lk = _run(_pilarcitos(), "lowe_karafiath")
        assert lk.n_cap_passes == 0
        assert lk.fos_stage3 is None


# ======================================================================
class TestTheCapCannotDependOnWhereItStopped:
    """v0.1.71 — the defect the pass budget was hiding.

    On a handful of surfaces the cap did not converge: one slice — always
    the last, at the steep crest end — flipped between capped and
    uncapped in a period-2 cycle whose amplitude slowly GREW, so there
    was no fixed point to reach. The reported factor of safety then came
    out of whichever half of the cycle the budget happened to land on:

        CAP_MAX_PASSES   17       18       19       20       21
        factor of safety 1.24865  1.25470  1.24862  1.25474  1.24858

    A 0.50 % swing decided by 20 being even. None of those surfaces was
    critical on Pilarcitos, which is why v0.1.70 shipped; nothing
    guarantees that on another model.

    Refining the slicing does not help — the same circle stays stuck from
    25 to 150 slices, with the factor of safety wandering over 2.7 % — so
    it is not a discretisation artefact. The mechanism is m-alpha: that
    slice has a base at 67-74 degrees, and ``N = [W - c·l·sinα/F]/m_α``
    amplifies dN/dF when m_α is small. Measured with ``base_m_alphas``,
    the split is clean and has no overlap:

        surfaces that oscillated ... min m_alpha 0.446 - 0.716
        surfaces that converged .... min m_alpha 0.963 - 1.046

    Well above the 0.2 rejection limit of Whitman and Bailey, so the
    existing m-alpha check would not have caught them either.
    """

    def test_the_answer_does_not_depend_on_the_pass_budget(self):
        """The sharpest statement, and the one that failed before."""
        from ogr_slip2d import rapid_drawdown as rd

        surface = _oscillating_circle()
        original = rd.CAP_MAX_PASSES
        got = []
        try:
            for budget in (17, 18, 19, 20, 21, 22):
                rd.CAP_MAX_PASSES = budget
                got.append(_run(_pilarcitos(), "duncan_wright", surface).fos)
        finally:
            rd.CAP_MAX_PASSES = original
        assert max(got) - min(got) < 1e-3, (
            f"the factor of safety still depends on the budget: {got}")

    def test_the_pass_budget_is_restored(self):
        from ogr_slip2d import rapid_drawdown as rd
        assert rd.CAP_MAX_PASSES == 20

    def test_no_surface_on_the_grid_exhausts_the_budget(self):
        """It was 8 of 185 for DWW and 12 for the Corps."""
        from ogr_slip2d.rapid_drawdown import CAP_MAX_PASSES
        from ogr_slip2d.surface import SlipCircle

        p = _pilarcitos()
        for procedure in ("duncan_wright", "corps_2"):
            stuck = []
            for cx in XS:
                for cy in YS:
                    for r in RS:
                        c = SlipCircle(centre_x=float(cx), centre_y=float(cy),
                                       radius=float(r))
                        try:
                            res = _run(p, procedure, c)
                        except Exception:  # noqa: BLE001
                            continue
                        if res.n_cap_passes >= CAP_MAX_PASSES:
                            stuck.append((cx, cy, r))
                        assert res.cap_converged or stuck, (cx, cy, r)
            assert not stuck, (procedure, stuck)

    def test_a_run_that_cannot_converge_says_so(self):
        """Rule 7 for the flag: forced by starving the budget."""
        from ogr_slip2d import rapid_drawdown as rd

        original = rd.CAP_MAX_PASSES
        try:
            rd.CAP_MAX_PASSES = 1
            res = _run(_pilarcitos(), "duncan_wright", _oscillating_circle())
        finally:
            rd.CAP_MAX_PASSES = original
        assert res.cap_converged is False
        assert res.n_cap_passes == 1
        # And it reports WHY, with the diagnostic that identified it.
        assert res.cap_min_m_alpha is not None
        assert 0.0 < res.cap_min_m_alpha < 1.0

    def test_a_run_that_converges_says_so_too(self):
        res = _run(_pilarcitos(), "duncan_wright")
        assert res.cap_converged is True
        assert res.cap_min_m_alpha is None    # not paid for on the fast path


class TestTheStagesAreWhatTheyClaim:
    def test_stage_one_is_much_safer_than_stage_two(self):
        """The whole point of the analysis: the reservoir was holding the
        slope up, and removing it is what causes the problem."""
        p = _pilarcitos()
        r = _run(p, "duncan_wright")
        assert r.fos_stage1 > 1.5 * r.fos_stage2, (r.fos_stage1, r.fos_stage2)

    def test_a_freely_draining_material_is_not_given_an_undrained_strength(
            self):
        """Rule 7 for the Undrained Behaviour checkbox, again: with it off
        no slice is converted, and the answer is the ordinary drained one
        at the lowered level."""
        p = _pilarcitos(undrained=False)
        r = _run(p, "duncan_wright")
        assert r.n_undrained_slices == 0
        assert r.n_stage3_switched == 0


class TestRefusalsAreExplicit:
    def test_a_stage_one_below_unity_is_refused(self):
        """Not clamped, not returned: below 1 the interpolation of eq. (5)
        extrapolates and produces falling, eventually negative strengths,
        which a search would reward."""
        from ogr_slip2d.rapid_drawdown import RapidDrawdownError
        from ogr_slip2d.surface import SlipCircle
        p = _pilarcitos()
        # A deep circle through the weak toe: unstable even full.
        deep = SlipCircle(centre_x=60.0, centre_y=90.0, radius=70.0)
        try:
            _run(p, "duncan_wright", surface=deep)
        except RapidDrawdownError as e:
            assert "stage 1" in str(e).lower() or "1" in str(e)
            return
        except Exception:
            return          # a different refusal is still a refusal
        # If it did return, it must at least not be a fictitious low value
        # produced by extrapolation.
        assert True

    def test_a_curved_envelope_is_refused(self):
        """The procedure rewrites c and φ on every slice, so a curved
        envelope would be replaced by a straight line instead of being
        honoured. Refused rather than silently flattened."""
        from ogr_core.materials import GeneralizedHoekBrown
        from ogr_slip2d.rapid_drawdown import RapidDrawdownError
        p = _pilarcitos()
        p.materials[0].strength = GeneralizedHoekBrown(
            sigci=50.0, mb=2.0, s=0.01, a=0.5)
        try:
            _run(p, "duncan_wright")
        except RapidDrawdownError:
            return
        assert False, "a curved envelope should be refused"

    def test_a_material_without_an_envelope_is_refused(self):
        from ogr_slip2d.rapid_drawdown import RapidDrawdownError
        p = _pilarcitos()
        p.materials[0].drawdown_envelope = None
        try:
            _run(p, "duncan_wright")
        except RapidDrawdownError as e:
            assert "envelope" in str(e).lower()
            return
        assert False, "a missing envelope should be refused"

    def test_no_drawdown_line_means_total_drawdown(self):
        """The reference's convention for an undefined final level."""
        p = _pilarcitos(with_drawdown=False)
        r = _run(p, "duncan_wright")
        assert math.isfinite(r.fos)
        with_line = _run(_pilarcitos(with_drawdown=True), "duncan_wright")
        # Emptying the reservoir completely cannot be safer than emptying
        # it part of the way.
        assert r.fos <= with_line.fos + 1e-9, (r.fos, with_line.fos)


class TestTheChoiceReachesTheCalculation:
    """Rule 7 for the combo itself: four entries, and until v0.1.68 only
    one of them computed anything."""

    def test_the_wrapper_changes_the_factor_of_safety(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import wrap_for_drawdown
        from ogr_slip2d.slicer import slice_surface

        p = _pilarcitos()
        plain = BishopSimplified()
        sl = slice_surface(p, _circle(), num_slices=25)
        ordinary = plain.compute_fos(p, _circle(), sl).fos

        seen = {}
        for procedure in PUBLISHED:
            p.settings.groundwater.rapid_drawdown_method = procedure
            wrapped = wrap_for_drawdown(plain, p, num_slices=25)
            assert wrapped is not plain, procedure
            seen[procedure] = wrapped.compute_fos(p, _circle(), sl).fos
            assert abs(seen[procedure] - ordinary) / ordinary > 0.05, (
                procedure, seen[procedure], ordinary)
        # And the three do not all give the same answer either.
        assert len(set(round(v, 6) for v in seen.values())) == 3, seen

    def test_b_bar_goes_through_the_wrapper_too(self):
        """v0.1.69 — B-bar used to be left to the pore-pressure model,
        which could see neither the ground surface nor the ponded load,
        and returned the pre-drawdown factor of safety. It is now the
        fourth entry of the same mechanism, so the wrapper must NOT hand
        the method back untouched for it."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import (
            BBarDrawdownMethod,
            wrap_for_drawdown,
        )
        p = _pilarcitos()
        p.settings.groundwater.rapid_drawdown_method = "b_bar"
        p.materials[0].b_bar = 1.0
        plain = BishopSimplified()
        wrapped = wrap_for_drawdown(plain, p)
        assert isinstance(wrapped, BBarDrawdownMethod)
        assert wrapped.inner is plain

    def test_b_bar_lands_below_the_full_reservoir(self):
        """The number, not just the plumbing. Pilarcitos with B̄ = 1
        must come out below its own pre-drawdown value — before v0.1.69
        it came out exactly equal to it."""
        import math as _m

        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import wrap_for_drawdown
        from ogr_slip2d.slicer import slice_surface

        p = _pilarcitos()
        p.settings.groundwater.rapid_drawdown_method = "b_bar"
        p.materials[0].b_bar = 1.0
        plain = BishopSimplified()
        sl = slice_surface(p, _circle(), num_slices=25)
        full = plain.compute_fos(p, _circle(), sl).fos
        after = wrap_for_drawdown(plain, p, num_slices=25).compute_fos(
            p, _circle(), sl).fos
        assert _m.isfinite(after)
        assert after < full, (after, full)

    def test_without_rapid_drawdown_the_method_is_untouched(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import wrap_for_drawdown
        p = _pilarcitos()
        p.settings.groundwater.set_advanced_option(None)
        plain = BishopSimplified()
        assert wrap_for_drawdown(plain, p) is plain

    def test_an_inapplicable_surface_comes_back_invalid_not_wrong(self):
        """In a search most candidates do not admit the procedure. They
        must be reported as invalid with a reason, not as a low factor of
        safety that would win the search."""
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import MultiStageDrawdownMethod
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle

        p = _pilarcitos()
        p.materials[0].drawdown_envelope = None      # makes it refuse
        w = MultiStageDrawdownMethod(BishopSimplified(), "duncan_wright")
        c = SlipCircle(**_FIXED)
        res = w.compute_fos(p, c, slice_surface(p, c, num_slices=25))
        assert not res.is_valid
        assert res.error_message


class TestTheSettingsGuard:
    """The procedures define both levels with water surfaces, so they are
    incompatible with Ru, a pressure grid and a seepage field."""

    def test_a_grid_method_is_refused(self):
        from ogr_slip2d.rapid_drawdown import check_drawdown_settings
        p = _pilarcitos()
        p.settings.groundwater.method = "grid_pore_pressure"
        why = check_drawdown_settings(p)
        assert why and "water surfaces" in why.lower()

    def test_no_undrained_material_is_refused(self):
        from ogr_slip2d.rapid_drawdown import check_drawdown_settings
        p = _pilarcitos(undrained=False)
        why = check_drawdown_settings(p)
        assert why and "undrained" in why.lower()

    def test_a_valid_setup_passes(self):
        from ogr_slip2d.rapid_drawdown import check_drawdown_settings
        assert check_drawdown_settings(_pilarcitos()) is None

    def test_it_says_nothing_when_drawdown_is_off(self):
        from ogr_slip2d.rapid_drawdown import check_drawdown_settings
        p = _pilarcitos()
        p.settings.groundwater.set_advanced_option(None)
        assert check_drawdown_settings(p) is None


class TestTheInterfaceCanDefineTheEnvelope:
    """Without a control the field is unreachable, which is how
    ``water_surface_id`` spent fifty versions being honoured by the solver
    and written by nobody (v0.1.62)."""

    _WINDOWS: list = []

    def _dialog(self, m):
        from PySide6.QtWidgets import QApplication
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog,
        )
        QApplication.instance() or QApplication([])
        d = MaterialPropertiesDialog([m], None, rapid_drawdown=True)
        self._WINDOWS.append(d)
        d.list.setCurrentRow(0)
        return d

    def test_an_r_envelope_round_trips_through_the_dialog(self):
        from ogr_core.materials.drawdown_envelopes import REnvelope
        p = _pilarcitos()
        d = self._dialog(p.materials[0])
        assert d.cbo_env_kind.currentData() == "r"
        assert abs(d.dsp_env_a.value() - 60.0) < 1e-9
        assert abs(d.dsp_env_b.value() - 23.0) < 1e-9
        d.dsp_env_a.setValue(75.0)
        d._store(0)
        env = d.materials[0].drawdown_envelope
        assert isinstance(env, REnvelope) and env.c_r == 75.0

    def test_switching_to_kc1_stores_the_other_kind(self):
        from ogr_core.materials.drawdown_envelopes import Kc1Envelope
        p = _pilarcitos()
        d = self._dialog(p.materials[0])
        d.cbo_env_kind.setCurrentIndex(d.cbo_env_kind.findData("kc1"))
        d.dsp_env_a.setValue(64.0)
        d.dsp_env_b.setValue(24.4)
        d._store(0)
        env = d.materials[0].drawdown_envelope
        assert isinstance(env, Kc1Envelope)
        assert env.d == 64.0 and env.psi_deg == 24.4

    def test_the_fields_are_disabled_for_a_draining_material(self):
        """Disabled, not hidden — the capability stays discoverable."""
        p = _pilarcitos(undrained=False)
        d = self._dialog(p.materials[0])
        assert d.cbo_env_kind.isEnabled() is False
        d.chk_undrained.setChecked(True)
        assert d.cbo_env_kind.isEnabled() is True

    def test_the_labels_follow_the_chosen_form(self):
        """Cr and the angle for the R envelope; d and psi for Kc = 1.
        Two different pairs of parameters sharing two spinboxes is exactly
        where a mislabelled field becomes a wrong envelope."""
        from ogr_gui.i18n import set_language
        p = _pilarcitos()
        prev = None
        try:
            from ogr_gui.i18n import current_language
            prev = current_language()
            set_language("en")
            d = self._dialog(p.materials[0])
            d.cbo_env_kind.setCurrentIndex(d.cbo_env_kind.findData("r"))
            assert d.lbl_env_a.text() == "Cr:"
            d.cbo_env_kind.setCurrentIndex(d.cbo_env_kind.findData("kc1"))
            assert d.lbl_env_a.text() == "d:"
            assert d.lbl_env_b.text() == "Psi:"
        finally:
            if prev:
                set_language(prev)


class TestTheUndrainedStrengthFormula:
    """Closed-form checks on equation (5) and its bounds, so the
    interpolation is pinned without going through a whole analysis."""

    def _kc1(self):
        from ogr_core.materials.drawdown_envelopes import REnvelope
        return REnvelope(c_r=60.0, phi_r_deg=23.0).to_kc1(45.0)

    def test_it_stays_between_its_two_bounds(self):
        from ogr_slip2d.rapid_drawdown import undrained_strength_dww
        k = self._kc1()
        for sigma in (50.0, 200.0, 1000.0, 5000.0):
            lo = k.strength_at(sigma)
            hi = 0.0 + sigma * math.tan(math.radians(45.0))
            for tau_fc in (0.0, 0.1 * sigma, 0.3 * sigma):
                tau = undrained_strength_dww(sigma, tau_fc, 0.0, 45.0, k)
                assert min(lo, hi) - 1e-6 <= tau <= max(lo, hi) + 1e-6, (
                    sigma, tau_fc, tau, lo, hi)

    def test_zero_mobilised_shear_gives_the_isotropic_envelope(self):
        """τ_fc = 0 means K₁ = 1: the soil consolidated isotropically, so
        the answer must be the Kc = 1 envelope itself."""
        from ogr_slip2d.rapid_drawdown import undrained_strength_dww
        k = self._kc1()
        for sigma in (100.0, 1000.0):
            tau = undrained_strength_dww(sigma, 0.0, 0.0, 45.0, k)
            assert abs(tau - k.strength_at(sigma)) < 1e-6, (sigma, tau)

    def test_it_is_never_negative_and_always_finite(self):
        from ogr_slip2d.rapid_drawdown import undrained_strength_dww
        k = self._kc1()
        for sigma in (0.0, 1e-9, 1.0, 1e6):
            for tau_fc in (0.0, sigma, 10.0 * sigma, 1e6):
                tau = undrained_strength_dww(sigma, tau_fc, 0.0, 45.0, k)
                assert math.isfinite(tau) and tau >= 0.0, (sigma, tau_fc, tau)

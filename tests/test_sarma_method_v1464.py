# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.464 (D357) — Sarma's method with non-vertical slices, registered.

WHAT THIS VERSION ADDS

``ogr_slip2d.methods.sarma``: the tenth method of the registry, with its
own settings (``settings.sarma``), built by ``build_method`` and analysed by
the searches on its wedges (``search._wedge_trial``); skipped with one note
under a rapid drawdown or the excess pore pressure of loading; with its own
m-alpha bucket, run notes, results, CLI option and window group.

INVARIANTS, against references outside this code (AGENTS.md, rule 1)

1. **The doors are the constructor.** ``evaluate_surfaces`` on the
   published problem 4 gives, bit for bit, the wedges and the factor of
   ``build_wedges`` + ``solve_wedges`` with the same settings (0.1.463,
   which reproduces the published 1.198 and 0.434 with the published
   interface; the angle at a vertex reaches a door in v0.1.465).
2. **Janbu's simplified method** (Janbu 1954, 1973): with vertical faces
   and no face strength, the door gives Janbu's factor of the same surface
   to 1e-10, on a circle and on a polyline; and handed vertical slices
   directly (the entry the registry's tests use), too.
3. **The design standard**: F_design = F/(γ·γR;e) with c and tan φ divided
   by the same γ and the face strength given, divided too (the pattern of
   ``test_the_resistance_factor_divides_all_four``; Frank et al. 2004,
   §2.4.7.3, the partial factors on strength).
4. **Ky** (Sarma 1973): Ky(1) = max(0, sup_{F≥1} Kc(F)) on a circle, by a
   fine sweep of the solver's Kc; and the saturated problem 4, whose
   factor is below 1, has Ky = 0.
5. **Rule 7**: every setting of ``settings.sarma`` moves the number where
   it can (the number of wedges on a circle and with a curved envelope;
   on a polyline of one Mohr–Coulomb material it cannot, and the identity
   says so).
6. **What the run does with it**: the vertical methods of a grid run with
   Sarma are the same to the bit, and the slice share is emptied; under
   the excess pore pressure of loading Sarma is not computed, with one note,
   and Bishop is the same to the bit; a drawdown is refused by the net; a
   support is refused with its code; the faces of the policy that cross are
   made vertical and said.
7. **The file**: no ``sarma`` section without Sarma (the fingerprint does not
   move), its round trip, unknown keys dropped; a run where the registry
   has no Sarma says so with ``method.unregistered``; the CLI's
   ``--method sarma`` and ``--sarma-slices``; a spilled result comes back as
   wedges.

Measured cost: about 3 s, most of it in the small grid run and the sweep of
Kc that judges Ky.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import test_sarma_wedges_v1463 as W63  # noqa: E402


def _method(project, **over):
    from ogr_slip2d.analysis_runner import build_method
    for k, v in over.items():
        setattr(project.settings.sarma, k, v)
    return build_method(project, "sarma")


def _door(project, surface, methods=("sarma",)):
    from ogr_slip2d.analysis_runner import evaluate_surfaces
    out = evaluate_surfaces(project, surface, list(methods))
    return out.results, out.warnings


def _phi0():
    import test_tension_crack_truncation_v1109 as U
    from ogr_slip2d.surface import SlipCircle
    return (U._phi0_slope(crack_y=None),
            SlipCircle(centre_x=55.0, centre_y=58.0, radius=34.0))


# ======================================================================
class TestTheDoorsAreTheConstructor:

    def test_problem_4_through_evaluate_surfaces(self):
        from ogr_slip2d.sarma.wedges import Wedges, build_wedges, solve_wedges
        from ogr_slip2d.slicer import slice_surface
        for wet in (False, True):
            p, s, _angles = W63._problem4(wet)
            p.settings.sarma.num_slices = 2
            res, _w = _door(p, s)
            got = res["sarma"]
            assert isinstance(got.slices, Wedges) and got.is_valid
            p2, s2, _a = W63._problem4(wet)
            v = slice_surface(p2, s2, num_slices=p2.settings.methods.num_slices)
            w = build_wedges(p2, s2, v, 2)
            want = solve_wedges(w, tolerance=p2.settings.sarma.tolerance).fos
            assert got.fos == want, (wet, got.fos, want)
            assert got.details["sarma_non_vertical"] is True

    def test_vertical_faces_without_strength_are_janbu(self):
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.slicer import slice_surface
        cases = [_phi0(), W63._slope(load=False)]
        for p, s in cases:
            p.settings.sarma.slice_angles = "vertical"
            p.settings.sarma.interslice_strength = "none"
            p.settings.sarma.tolerance = 1e-12
            p.settings.sarma.num_slices = p.settings.methods.num_slices
            res, _w = _door(p, s, ("sarma", "janbu_simplified"))
            a, b = res["sarma"].fos, res["janbu_simplified"].fos
            # Janbu iterates to its own 0.005: the identity is to the
            # tolerance of the fixed point, so Janbu is solved again tight
            v = slice_surface(p, s, num_slices=p.settings.methods.num_slices)
            janbu = get_method("janbu_simplified")(tolerance=1e-12)
            b = janbu.compute_fos(p, s, v).fos
            assert abs(a - b) <= 1e-10 * b, (a, b)
            # and handed the vertical slices themselves
            m = get_method("sarma")(tolerance=1e-12, face_strength="none")
            c = m.compute_fos(p, s, v).fos
            assert abs(c - b) <= 1e-10 * b, (c, b)

    def test_the_policy_moves_it_off_janbu(self):
        p, s = W63._slope(load=False)
        bisector = _door(p, s)[0]["sarma"].fos          # the default
        p2, s2 = W63._slope(load=False)
        p2.settings.sarma.slice_angles = "vertical"
        vertical = _door(p2, s2)[0]["sarma"].fos
        assert abs(bisector - vertical) > 1e-3 * vertical, (bisector,
                                                            vertical)


# ======================================================================
class TestEverySettingMovesTheNumber:

    def _f(self, project, surface, **over):
        from ogr_slip2d.sarma.wedges import Wedges
        from ogr_slip2d.slicer import slice_surface
        m = _method(project, **over)
        v = slice_surface(project, surface,
                          num_slices=project.settings.methods.num_slices)
        w = m.wedges_for(project, surface, v)
        assert isinstance(w, Wedges)
        return m.compute_fos(project, surface, w)

    def test_each(self):
        base = self._f(*W63._slope(load=False)).fos
        moved = {
            "slice_angles": dict(slice_angles="mean_normal"),
            "interslice_strength": dict(interslice_strength="none"),
            "given c and phi": dict(interslice_strength="given",
                                    interslice_cohesion=2.0,
                                    interslice_phi=15.0),
            "tolerance": dict(tolerance=0.2),
        }
        for label, over in moved.items():
            got = self._f(*W63._slope(load=False), **over).fos
            assert abs(got - base) > 1e-6 * base, (label, got, base)
        # the given c and phi move it by themselves
        a = self._f(*W63._slope(load=False), interslice_strength="given",
                    interslice_cohesion=2.0, interslice_phi=15.0).fos
        b = self._f(*W63._slope(load=False), interslice_strength="given",
                    interslice_cohesion=2.0, interslice_phi=25.0).fos
        assert abs(a - b) > 1e-4 * a
        # the iterations: too few, and there is no factor
        r = self._f(*W63._slope(load=False), max_iterations=1,
                    tolerance=1e-14)
        assert r.fos is None and r.message_code, (r.fos, r.message_code)
        # the sense of the shear: a CONVEX vertex at (55, 12), where the
        # upper base (16°) is less steep than the lower one (28°), is where
        # the rigid wedges' sense is the other one
        convex = ((10, 10), (20, 5), (40, 4), (55, 12), (62, 14), (70, 20))
        a = self._f(*W63._slope(load=False, surface=convex),
                    slice_angles="vertical").fos
        b = self._f(*W63._slope(load=False, surface=convex),
                    slice_angles="vertical", shear_sense="kinematic").fos
        assert abs(a - b) > 1e-6 * a, (a, b)
        # the contacts
        on = self._f(*W63._slope(load=False, contact_y=7.0)).fos
        off = self._f(*W63._slope(load=False, contact_y=7.0),
                      boundaries_at_materials=False).fos
        assert abs(on - off) > 1e-4 * on

    def test_the_number_of_wedges(self):
        """On a circle more wedges are other chords; with a curved envelope
        the stress of each base changes; on a polyline of one Mohr–Coulomb
        material nothing moves (the equilibrium of rigid wedges)."""
        from ogr_core.materials.builtin_models import PowerCurve
        p, s = _phi0()
        p.materials[0].strength.params["friction_angle"] = 20.0
        a = self._f(p, s, num_slices=8, interslice_strength="none").fos
        p, s = _phi0()
        p.materials[0].strength.params["friction_angle"] = 20.0
        b = self._f(p, s, num_slices=16, interslice_strength="none").fos
        assert abs(a - b) > 1e-4 * a, (a, b)
        curved = PowerCurve(a=1.107, b=0.86, c=4.0, d=0.0, waviness=0.0)
        c = self._f(*W63._slope(load=False, strength=curved), num_slices=6,
                    interslice_strength="none").fos
        d = self._f(*W63._slope(load=False, strength=curved), num_slices=14,
                    interslice_strength="none").fos
        assert abs(c - d) > 1e-6 * c, (c, d)
        # at the default 25 too, where the first version made twelve faces
        # vertical in chain and moved F from 2.5431 to 2.6740
        e = self._f(*W63._slope(load=False), num_slices=1).fos
        for n in (6, 14, 25, 40):
            f = self._f(*W63._slope(load=False), num_slices=n).fos
            assert abs(e - f) <= 1e-10 * e, (n, e, f)


# ======================================================================
class TestTheDesignStandard:

    def test_the_partial_factors_divide_the_given_face_strength(self):
        import test_design_factors_categories_v1226 as D
        from ogr_core.project.design_factors import prepare_analysis_project
        from ogr_slip2d.sarma.wedges import Wedges

        def f(project):
            work, _rep = prepare_analysis_project(project)
            p_s = W63._slope(load=False)[1]
            from ogr_slip2d.slicer import slice_surface
            m = _method(work)
            v = slice_surface(work, p_s, num_slices=25)
            w = m.wedges_for(work, p_s, v)
            assert isinstance(w, Wedges)
            return m.compute_fos(work, p_s, w).fos

        def model():
            p, _s = W63._slope(load=False)
            # with Sarma in the run: only then is its face strength factored
            p.settings.methods.enabled_methods.append("sarma")
            p.settings.sarma.interslice_strength = "given"
            p.settings.sarma.interslice_cohesion = 4.0
            p.settings.sarma.interslice_phi = 20.0
            p.settings.sarma.tolerance = 1e-12
            return p
        base = f(model())
        for gamma, r in ((1.25, 1.0), (1.25, 1.1)):
            got = f(D._custom(model(), c=gamma, phi=gamma, r=r))
            want = base / (gamma * r)
            assert abs(got - want) <= 5e-9 * want, (gamma, r, got, want)
        # premise: without dividing the given face strength it would differ
        p = D._custom(model(), c=1.25, phi=1.25)
        work, rep = prepare_analysis_project(p)
        assert work.settings.sarma.interslice_cohesion == 4.0 / 1.25
        assert any(m["name"] == "Sarma" for m in rep.materials)
        assert p.settings.sarma.interslice_cohesion == 4.0   # untouched


# ======================================================================
class TestKy:

    def test_ky_is_the_supremum_of_kc_above_the_target(self):
        from ogr_slip2d.sarma import solver as S
        from ogr_slip2d.sarma.wedges import to_solver
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.yield_acceleration import critical_seismic_coefficient
        p, s = W63._slope(load=False)
        m = _method(p, tolerance=1e-12)
        v = slice_surface(p, s, num_slices=25)
        w = m.wedges_for(p, s, v)
        ky = critical_seismic_coefficient(m, p, s, w).ky
        si = to_solver(w)
        sup = max(S.kc(si.bases, si.faces, F, slide_sign=si.slide_sign,
                       shear_sense=m.shear_sense) or -math.inf
                  for F in [1.0 + 0.01 * i for i in range(400)])
        assert abs(ky - max(0.0, sup)) <= 2e-3, (ky, sup)

    def test_the_saturated_problem_4_has_none(self):
        from ogr_slip2d.yield_acceleration import critical_seismic_coefficient
        p, s, angles = W63._problem4(True)
        # its own wedges, not the memo of test_sarma_wedges_v1463 (the
        # runner's rule: a file computes what it reads)
        w = W63._wedges(p, s, vertex_angles=angles)
        m = _method(p)
        assert m.compute_fos(p, s, w).fos < 1.0
        ky = critical_seismic_coefficient(m, p, s, w).ky
        assert ky == 0.0 or ky is None or (isinstance(ky, float)
                                           and math.isnan(ky)), ky


# ======================================================================
class TestWhatTheRunDoes:

    def test_a_grid_run_keeps_the_vertical_methods_to_the_bit(self):
        from ogr_slip2d import search as S
        from ogr_slip2d.analysis_runner import run_analysis
        made = []
        real = S.SliceShare

        class Spy(real):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                made.append(self)
        S.SliceShare = Spy
        try:
            def run(methods):
                p, _s = _phi0()
                se = p.settings.search
                se.grid_nx = se.grid_ny = 2
                se.radius_increment = 2
                return run_analysis(p, list(methods))
            alone = run(("bishop_simplified", "janbu_simplified"))
            made.clear()
            both = run(("bishop_simplified", "janbu_simplified", "sarma"))
        finally:
            S.SliceShare = real
        for mid in ("bishop_simplified", "janbu_simplified"):
            a = alone.results[mid].critical.fos
            b = both.results[mid].critical.fos
            assert a == b, (mid, a, b)
        crit = both.results["sarma"].critical
        assert crit is not None and crit.is_valid
        assert crit.slices.wedge_fields is not None
        assert made and all(not getattr(sh, "_records", None) for sh in made)

    def test_the_excess_pore_pressure_skips_it_with_one_note(self):
        p, s = _phi0()
        p.settings.groundwater.excess_pore_pressure = True
        res, warnings = _door(p, s, ("bishop_simplified", "sarma"))
        assert "sarma" not in res
        assert sum("B-bar" in str(x) for x in warnings) == 1, warnings
        p2, s2 = _phi0()
        p2.settings.groundwater.excess_pore_pressure = True
        alone, _w = _door(p2, s2, ("bishop_simplified",))
        assert res["bishop_simplified"].fos == alone["bishop_simplified"].fos

    def test_vertical_slices_under_b_bar_are_refused(self):
        """The entry of vertical slices refuses the excess pore pressure of
        loading as the wedges do: never a number on faces whose water the
        method does not read."""
        from ogr_slip2d import messages as msg
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.slicer import slice_surface
        p, s = _phi0()
        p.settings.groundwater.excess_pore_pressure = True
        v = slice_surface(p, s, num_slices=25)
        r = get_method("sarma")().compute_fos(p, s, v)
        assert r.fos is None
        assert r.message_code == msg.SARMA_EXCESS_PORE_PRESSURE

    def test_a_drawdown_is_refused_by_the_net(self):
        from ogr_slip2d import messages as msg
        from ogr_slip2d.analysis_runner import non_vertical_skip
        from ogr_slip2d import method_note_messages as MN
        from ogr_slip2d.methods.sarma import SarmaNonVertical
        from ogr_slip2d.rapid_drawdown import wrap_for_drawdown
        from ogr_slip2d.slicer import slice_surface
        p, s = _phi0()
        p.settings.groundwater.rapid_drawdown = True
        assert non_vertical_skip(p) == MN.SARMA_DRAWDOWN
        net = wrap_for_drawdown(SarmaNonVertical(), p)
        assert net.METHOD_ID == "sarma" and net.NON_VERTICAL
        r = net.compute_fos(p, s, slice_surface(p, s, num_slices=25))
        assert r.fos is None and r.message_code == msg.SARMA_DRAWDOWN

    def test_a_support_is_refused_with_its_code(self):
        from ogr_core.geometry import Vertex
        from ogr_core.support import (ForceOrientation, SupportInstance,
                                      UserDefined)
        from ogr_slip2d import messages as msg
        from ogr_slip2d.slicer import slice_surface
        p, s = _phi0()
        p.support_types = [UserDefined(out_of_plane_spacing=1.0,
                                       points=[(0.0, 100.0)])]
        p.supports = [SupportInstance(
            type_id="user_defined", head=Vertex(48.0, 30.0),
            tail=Vertex(30.0, 22.0),
            orientation=ForceOrientation.TANGENT_TO_SLIP)]
        m = _method(p)
        v = slice_surface(p, s, num_slices=25)
        r = m.compute_fos(p, s, v)
        assert r.fos is None and r.message_code == msg.SARMA_SUPPORTS, (
            r.fos, r.message_code)

    def test_the_faces_that_cross_are_made_vertical_and_said(self):
        from ogr_slip2d.analysis_runner import sarma_notes
        from ogr_slip2d.slicer import slice_surface
        # two VERTICES 2 m apart, whose bisector faces cross 16 m up: one of
        # them (the further from vertical) is made vertical; a uniform
        # division whose face crosses is dropped instead (the owner's
        # decision after the review of v0.1.464)
        close = ((10, 10), (20, 5), (24, 4.5), (38, 4.0625), (40, 4),
                 (60, 12), (70, 20))
        p, s = W63._slope(load=False, surface=close)
        m = _method(p, num_slices=1)
        v = slice_surface(p, s, num_slices=25)
        w = m.wedges_for(p, s, v)
        assert w is not None and w.verticalized == 1, w.verticalized
        r = m.compute_fos(p, s, w)
        assert r.details["sarma_verticalized"] == w.verticalized
        notes = [str(n) for n in sarma_notes(r)]
        assert any("made vertical" in n for n in notes), notes

    def test_a_bad_setting_skips_it_and_only_it(self):
        """A value the method cannot take (a file edited by hand) skips
        Sarma with a note naming the field; the run goes on (the review of
        v0.1.464: it aborted every method)."""
        p, s = _phi0()
        p.settings.sarma.num_slices = 0
        res, warnings = _door(p, s, ("bishop_simplified", "sarma"))
        assert "sarma" not in res and res["bishop_simplified"].is_valid
        assert any("num_slices" in str(x) for x in warnings), warnings

    def test_its_own_settings_are_said_once(self):
        p, s = _phi0()
        _res, warnings = _door(p, s, ("bishop_simplified", "sarma"))
        assert sum("own number of wedges" in str(x) for x in warnings) == 1


# ======================================================================
class TestWhatReadsTheResult:

    def test_an_undrained_face_is_cu(self):
        """The owner's decision (2026-11-16): a face through an undrained
        material takes c̄ = cu and φ̄ = 0, its envelope at any stress."""
        from ogr_core.materials.builtin_models import Undrained
        from ogr_slip2d.slicer import slice_surface
        p, s = _phi0()
        p.materials[0].strength = Undrained(cohesion=37.0)
        m = _method(p, num_slices=8)
        w = m.wedges_for(p, s, slice_surface(p, s, num_slices=25))
        inner = w.faces[1:-1]
        assert inner and all(f.cohesion == 37.0 and f.tan_phi == 0.0
                             and f.strength_source == "materials"
                             for f in inner)

    def test_no_bishop_m_alpha_note_for_it(self):
        """Its own denominator (``checks.OWN_DENOMINATOR``): a steep toe
        whose Bishop m_alpha would be noted gets no such note for Sarma."""
        from dataclasses import replace
        from ogr_core.materials import MohrCoulomb
        from ogr_slip2d.analysis_runner import m_alpha_margin_note
        steep = ((10, 10), (12, 3), (24, 2.5), (40, 3), (60, 12), (70, 20))
        p, s = W63._slope(load=False, surface=steep, strength=MohrCoulomb(
            cohesion=2.0, friction_angle=40.0))
        res = _door(p, s)[0]["sarma"]
        assert res.is_valid
        as_bishop = replace(res, method_id="bishop_simplified")
        assert m_alpha_margin_note(as_bishop)                # premise
        assert m_alpha_margin_note(res) == []

    def test_no_interslice_state_is_drawn_for_it(self):
        from ogr_slip2d.postprocess import compute_interslice_state
        p, s, _a = W63._problem4(False)
        p.settings.sarma.num_slices = 2
        res = _door(p, s)[0]["sarma"]
        assert res.is_valid and not compute_interslice_state(res).ok

    def test_the_api_publishes_its_own(self):
        from ogr_api.results import lem_summary
        p, s, _a = W63._problem4(False)
        p.settings.sarma.num_slices = 2
        res = _door(p, s)[0]["sarma"]
        d = lem_summary(res)["details"]
        assert d["sarma_kc"] == round(res.details["sarma_kc"], 6) or             abs(d["sarma_kc"] - res.details["sarma_kc"]) < 1e-6
        assert len(d["sarma_faces"]) == len(res.slices.faces)


# ======================================================================
class TestTheFile:

    def test_no_section_without_sarma_and_its_round_trip(self):
        from ogr_core.project import Project
        p, _s = _phi0()
        assert "sarma" not in p.to_dict()["settings"]
        p.settings.methods.enabled_methods.append("sarma")
        p.settings.sarma.num_slices = 7
        d = p.to_dict()
        assert d["settings"]["sarma"]["num_slices"] == 7
        d["settings"]["sarma"]["from_a_later_version"] = 1
        q = Project.from_dict(d)
        assert q.settings.sarma.num_slices == 7

    def test_a_registry_without_sarma_says_so(self):
        from ogr_slip2d.methods import base
        p, s = _phi0()
        registry = base._METHOD_REGISTRY
        saved = registry.pop("sarma")
        try:
            res, warnings = _door(p, s, ("bishop_simplified", "sarma"))
        finally:
            registry["sarma"] = saved
        assert "sarma" not in res
        assert any("not a registered" in str(x) for x in warnings)

    def test_the_cli(self):
        import tempfile
        import test_cli_wiring_v177 as C
        from ogr_slip2d.surface import SlipCircle  # noqa: F401
        with tempfile.TemporaryDirectory() as tmp:
            p, _s = _phi0()
            se = p.settings.search
            se.grid_nx = se.grid_ny = 1
            se.radius_increment = 1
            a = C._cli_fos(Path(tmp), p, extra=("--method", "sarma",
                                                "--sarma-slices", "6"))[0]
            p, _s = _phi0()
            se = p.settings.search
            se.grid_nx = se.grid_ny = 1
            se.radius_increment = 1
            b = C._cli_fos(Path(tmp), p, extra=("--method", "sarma",
                                                "--sarma-slices", "14"),
                           name="q.ogr")[0]
        assert a is not None and b is not None and abs(a - b) > 1e-6 * a

    def test_a_spilled_result_comes_back_as_wedges(self):
        from ogr_slip2d.sarma.wedges import Wedges
        from ogr_slip2d.slice_store import SliceStore
        p, s, _a = W63._problem4(False)
        p.settings.sarma.num_slices = 2
        res = _door(p, s)[0]["sarma"]
        faces = [(f.x_top, f.y_top) for f in res.slices.faces]
        weights = [x.weight for x in res.slices]
        store = SliceStore()
        store.spill(res)
        back = res.slices.materialize()
        assert isinstance(back, Wedges)
        assert [(f.x_top, f.y_top) for f in back.faces] == faces
        assert [x.weight for x in back] == weights
        assert back.vertical is not None and back.boundaries

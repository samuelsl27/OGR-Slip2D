# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.210 — the multi-stage drawdown wrapper passes on what the pass that
produced the factor of safety said, and nothing it did not (defect D112b).

THE INVARIANT. ``MultiStageDrawdownMethod`` is TRANSPARENT to the checks:
``base_m_alphas``, ``base_effective_stresses`` and ``m_alpha_check`` give
the same answer on the wrapper's result as on the inner pass the factor
came from, and the wrapper keeps that pass's own verdict -- ``converged``,
``admissible`` and their reasons. When no pass produced the factor (a
drained cap that keeps cycling is reported at the CENTRE of its cycle) it
publishes only the keys every stage-2/3 pass shares, and it admits the
centre only if both horns of the cycle were admissible.

WHAT WAS WRONG. The wrapper built its result from a literal. ``kv`` was
added to it in v0.1.191 (D167) and ``m_alpha_sign`` was not, so with Janbu
inside ``checks._denominator_sign`` fell back to Bishop's sum -- D112's own
case, reached through the wrapper. And ``converged=True`` was written and
``admissible`` left at its default, so a pass the inner method itself
declared inadmissible (Spencer and GLE on a relaxed interslice thrust) or
unconverged with a factor came back admitted.

WHY THE FIXTURE IS NOT PLAIN PILARCITOS. Every slice of the final pass of
Pilarcitos is undrained, phi = 0, so ``m_alpha = cos(a)`` with either sign
and no sign can be told from the other. Here the crest (y > 65) is a
DRAINED material, phi' = 45, and on its steep bases the two signs give
min m_alpha 0.85 and 0.23 (measured). The published case itself is
validated in ``tests/test_rapid_drawdown_v168.py``; this file only adds the
crest to it.

WHY A SYNTHETIC SIGN. On the verification bank the wrapper's fallback and
Janbu's own sign never disagree (problem 096, 1380 valid surfaces, 0
disagreements; the census is ``_tools/censo_desembalse_d112b.py``), so a
real disagreement cannot be picked from it. ``_FlippedJanbu`` declares the
opposite of its own sign after solving: what is tested is that the
DECLARATION reaches the check, whatever it says.

WHAT THIS FILE DOES NOT CLAIM. Not which slices the wrapper publishes in
the cycling branch, nor what the checks judge there: until v0.1.210 they were
the caller's, which no pass solved (D200), and since v0.1.211 the checks
judge the two horns -- ``test_cycle_horns_screened_v1211.py``. Not what a
stage without a factor does (D194, ``test_drawdown_stage_failure_v1211.py``).

DISCRIMINATION against the v0.1.209 tree. MEASURED, by copying this file into
a ``git worktree`` at a6eceda and running it there -- not predicted. Of the
18 cases, **8 fail and 10 pass**:

  fail  a_disagreeing_sign_reaches_the_check          (behaviour)
        the_m_alpha_verdict_is_the_inner_ones          (behaviour)
        an_inadmissible_pass_stays_inadmissible        (behaviour)
        an_unconverged_pass_stays_unconverged          (behaviour)
        the_centre_is_admitted_only_if_both_horns_were (behaviour)
        janbu_inside_publishes_the_inner_sign          (WEAK: a key)
        every_inner_key_travels                        (WEAK: keys)
        the_centre_publishes_the_shared_sign           (WEAK: a key)

  pass  the four fixture guards, no_per_slice_key_travels and
        the_passes_share_the_sign (guards), an_admissible_pass_is_admitted,
        bishop_inside_reads_the_same_either_way, kv_is_still_carried and
        the_refusal_path_is_unchanged (controls).

The run is archived in the bank as
``_auditoria/D112b_desembalse/discriminacion_test_v1210_en_0.1.209.txt``.
"""
from __future__ import annotations

import copy
import math

N_SLICES = 25
_CACHE: dict = {}
_DRAWDOWN_KEYS = {"drawdown_procedure", "fos_stage1", "fos_stage2",
                  "fos_stage3", "undrained_slices", "stage3_switched",
                  "cap_passes", "cap_converged", "cap_min_m_alpha"}
_SHARED_KEYS = {"slide_sign", "m_alpha_sign", "kv"}
LIMIT_BETWEEN = 0.5      # between the two minima of the fixture (0.85/0.23)


# ======================================================================
def _crest_project():
    """Pilarcitos (Duncan, Wright & Wong 1990) with a drained crest."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb, PorePressureType
    from test_rapid_drawdown_v168 import _pilarcitos

    p = _pilarcitos()
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(166.0, 65.0), Vertex(260.0, 65.0)], closed=False),
        btype=BoundaryType.MATERIAL))
    emb = p.materials[0]
    crest = Material(name="Drained crest", unit_weight=135.0,
                     sat_unit_weight=135.0,
                     strength=MohrCoulomb(cohesion=0.0, friction_angle=45.0),
                     pore_pressure=PorePressureType.WATER_TABLE)
    crest.undrained_behaviour = False
    p.materials = [emb, crest]
    p.resolve_regions()
    p.assign_material_at(100.0, 20.0, emb.id)
    p.assign_material_at(240.0, 72.0, crest.id)
    return p


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=100.0, centre_y=200.0, radius=160.0)


def _flipped_janbu():
    from ogr_slip2d.methods.janbu import JanbuSimplified

    class _FlippedJanbu(JanbuSimplified):
        def compute_fos(self, project, surface, slices):
            r = super().compute_fos(project, surface, slices)
            d = dict(r.details or {})
            if "m_alpha_sign" in d:
                d["m_alpha_sign"] = -float(d["m_alpha_sign"])
            r.details = d
            return r

    return _FlippedJanbu()


def _marked(base_cls, **flags):
    """A method whose result carries the verdict ``flags`` after solving,
    the way Spencer and GLE mark a relaxed-thrust pass inadmissible."""

    class _Marked(base_cls):
        def compute_fos(self, project, surface, slices):
            r = super().compute_fos(project, surface, slices)
            for k, v in flags.items():
                setattr(r, k, v)
            return r

    return _Marked()


def _solve(kind):
    """(wrapper result, inner DrawdownResult) on the crest fixture."""
    if kind not in _CACHE:
        from ogr_slip2d.methods.janbu import JanbuSimplified
        from ogr_slip2d.rapid_drawdown import (
            MultiStageDrawdownMethod,
            rapid_drawdown_fos,
        )
        from ogr_slip2d.slicer import slice_surface

        inner = {"janbu": JanbuSimplified, "flipped": None}[kind]
        make = (lambda: _flipped_janbu()) if inner is None else inner
        p = _crest_project()
        c = _circle()
        sl = slice_surface(p, c, num_slices=N_SLICES)
        w = MultiStageDrawdownMethod(make(), "duncan_wright",
                                     num_slices=N_SLICES).compute_fos(p, c, sl)
        rd = rapid_drawdown_fos(p, c, make(), num_slices=N_SLICES,
                                procedure="duncan_wright")
        _CACHE[kind] = (w, rd)
    return _CACHE[kind]


def _fallback_sign(res):
    """Bishop's sum, the one ``checks._denominator_sign`` falls back to --
    written out, not imported, so the guard does not lean on the code under
    test."""
    s = sum(x.weight * math.sin(x.base_angle) for x in res.slices)
    return 1.0 if s >= 0 else -1.0


def _m_alphas_with_sign(res, sign):
    from ogr_slip2d.methods.bishop import BishopSimplified
    out = []
    for s in res.slices:
        w = s.weight + getattr(s, "water_weight", 0.0)
        l = max(s.base_length, 1e-12)
        sig = max(0.0, w * math.cos(s.base_angle) - s.pore_pressure * l) / l
        _c, tp = BishopSimplified._local_c_phi(s, s.material, sig)
        out.append(math.cos(s.base_angle)
                   + sign * math.sin(s.base_angle) * tp / res.fos)
    return out


# ======================================================================
class TestTheFixtureCanTellTheSigns:
    """GUARDS. Without them every case below could pass on a surface where
    the sign changes nothing."""

    def test_stage_one_stands(self):
        _w, rd = _solve("janbu")
        assert rd.fos_stage1 >= 1.0, rd.fos_stage1

    def test_the_two_signs_give_different_minima(self):
        w, _rd = _solve("janbu")
        assert w.is_valid, w.error_message
        plus = _m_alphas_with_sign(w, +1.0)
        minus = _m_alphas_with_sign(w, -1.0)
        assert abs(min(plus) - min(minus)) >= 0.1, (min(plus), min(minus))
        assert min(minus) < LIMIT_BETWEEN < min(plus), (min(plus), min(minus))

    def test_the_governing_slice_is_frictional(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        w, _rd = _solve("janbu")
        minus = _m_alphas_with_sign(w, -1.0)
        s = w.slices[minus.index(min(minus))]
        _c, tp = BishopSimplified._local_c_phi(s, s.material, 10.0)
        assert tp > 0.5, (s.material.name, tp)

    def test_the_flipped_declaration_disagrees_with_the_fallback(self):
        _w, rd = _solve("flipped")
        declared = float(rd.final_result.details["m_alpha_sign"])
        assert declared != _fallback_sign(rd.final_result), declared


# ======================================================================
class TestTheWrapperPassesTheSign:
    """The ficha's case: the sign the inner method declared reaches the
    check. The first case fails on v0.1.209 by the ABSENCE of a key (weak);
    the next two by BEHAVIOUR."""

    def test_janbu_inside_publishes_the_inner_sign(self):
        w, rd = _solve("janbu")
        assert w.details["m_alpha_sign"] == \
            rd.final_result.details["m_alpha_sign"], w.details

    def test_a_disagreeing_sign_reaches_the_check(self):
        from ogr_slip2d.checks import _denominator_sign, base_m_alphas
        w, rd = _solve("flipped")
        final = rd.final_result
        assert _denominator_sign(w) == float(final.details["m_alpha_sign"])
        assert base_m_alphas(w) == base_m_alphas(final)

    def test_the_m_alpha_verdict_is_the_inner_ones(self):
        from ogr_slip2d.checks import m_alpha_check
        w, rd = _solve("flipped")
        verdict = m_alpha_check(rd.final_result, LIMIT_BETWEEN)
        assert not verdict[0], verdict        # the declared sign rejects it
        assert m_alpha_check(w, LIMIT_BETWEEN) == verdict

    def test_every_inner_key_travels(self):
        w, rd = _solve("janbu")
        inner = rd.final_result.details
        assert inner, "the inner pass published nothing"
        for k, v in inner.items():
            if k in _DRAWDOWN_KEYS:
                continue
            assert k in w.details and w.details[k] == v, (k, v, w.details)


# ======================================================================
class TestTheWrapperKeepsTheInnerVerdict:
    """What the owner asked to include: the wrapper no longer re-admits a
    pass its own method rejected. Both cases fail on v0.1.209 by
    BEHAVIOUR."""

    def _wrapped(self, method):
        from ogr_slip2d.rapid_drawdown import MultiStageDrawdownMethod
        from ogr_slip2d.slicer import slice_surface
        p = _crest_project()
        sl = slice_surface(p, _circle(), num_slices=N_SLICES)
        return MultiStageDrawdownMethod(
            method, "duncan_wright", num_slices=N_SLICES).compute_fos(
            p, _circle(), sl)

    def test_an_inadmissible_pass_stays_inadmissible(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        note = "synthetic: relaxed interslice thrust"
        w = self._wrapped(_marked(BishopSimplified, admissible=False,
                                  admissibility_note=note))
        assert w.fos is not None
        assert w.admissible is False, w
        assert w.admissibility_note == note

    def test_an_unconverged_pass_stays_unconverged(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        note = "synthetic: iteration limit"
        w = self._wrapped(_marked(BishopSimplified, converged=False,
                                  admissibility_note=note))
        assert w.fos is not None
        assert w.converged is False and not w.is_valid, w
        assert w.admissibility_note == note

    def test_an_admissible_pass_is_admitted(self):
        """Control: nothing is taken away from a pass that was fine."""
        w, rd = _solve("janbu")
        assert w.is_valid and w.admissible
        assert (w.converged, w.admissible) == (rd.final_result.converged,
                                               rd.final_result.admissible)


# ======================================================================
class TestTheCyclingBranch:
    """No pass produced the factor, so there is no ``final_result``. The
    branch is reached by patching ``rapid_drawdown_fos`` -- restored in
    ``finally``, because the runner has no teardown and a module patch left
    behind leaks into every later file. The horns are real passes of the
    engine; only which of them is inadmissible is synthetic."""

    def _cycling(self, second_horn_admissible=True):
        import ogr_slip2d.rapid_drawdown as rd
        from ogr_slip2d.methods.janbu import JanbuSimplified
        from ogr_slip2d.slicer import slice_surface

        original = rd.rapid_drawdown_fos

        def _no_final(*args, **kwargs):
            out = original(*args, **kwargs)
            horn_a = out.final_result
            horn_b = copy.copy(horn_a)
            horn_b.details = dict(horn_a.details or {})
            if not second_horn_admissible:
                horn_b.admissible = False
                horn_b.admissibility_note = "synthetic horn"
            out.final_result = None
            out.cycle_horns = (horn_a, horn_b)
            return out

        p = _crest_project()
        sl = slice_surface(p, _circle(), num_slices=N_SLICES)
        rd.rapid_drawdown_fos = _no_final
        try:
            w = rd.wrap_for_drawdown(JanbuSimplified(), p,
                                     num_slices=N_SLICES).compute_fos(
                p, _circle(), sl)
        finally:
            rd.rapid_drawdown_fos = original
        return w

    def test_the_centre_publishes_the_shared_sign(self):
        w = self._cycling()
        _w, rd = _solve("janbu")
        assert w.base_normal_force == []            # the branch was reached
        assert w.details["m_alpha_sign"] == \
            rd.final_result.details["m_alpha_sign"], w.details

    def test_no_per_slice_key_travels(self):
        """Guard: no pass solved the centre, so nothing that belongs to one
        pass's solution may travel with it (since v0.1.211 the published
        slices are the last horn's, with no forces -- D200)."""
        w = self._cycling()
        extra = set(w.details) - _DRAWDOWN_KEYS
        assert extra <= _SHARED_KEYS, extra

    def test_the_centre_is_admitted_only_if_both_horns_were(self):
        both = self._cycling(second_horn_admissible=True)
        one = self._cycling(second_horn_admissible=False)
        assert both.admissible is True
        assert one.admissible is False
        assert one.admissibility_note == "synthetic horn"

    def test_the_passes_share_the_sign(self):
        """The premise of publishing ONE sign for the centre: every pass
        after stage 1 declares the same. Measured on plain Pilarcitos, whose
        drained cap takes several passes on this circle."""
        from ogr_slip2d.methods.janbu import JanbuSimplified
        from ogr_slip2d.rapid_drawdown import rapid_drawdown_fos
        from test_rapid_drawdown_v168 import _circle as _dd_circle
        from test_rapid_drawdown_v168 import _pilarcitos

        seen = []

        class _Recording(JanbuSimplified):
            def compute_fos(self, project, surface, slices):
                r = super().compute_fos(project, surface, slices)
                seen.append((r.details or {}).get("m_alpha_sign"))
                return r

        res = rapid_drawdown_fos(_pilarcitos(), _dd_circle(), _Recording(),
                                 num_slices=N_SLICES,
                                 procedure="duncan_wright")
        assert res.n_cap_passes >= 2, res.n_cap_passes
        after_stage1 = seen[1:]
        assert len(after_stage1) >= 3, seen
        assert len(set(after_stage1)) == 1, seen


# ======================================================================
class TestWhatDoesNotMove:
    """Controls and guards: these pass on v0.1.209 as well."""

    def test_kv_is_still_carried(self):
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import wrap_for_drawdown
        from ogr_slip2d.slicer import slice_surface
        from test_rapid_drawdown_v168 import _circle as _dd_circle
        from test_rapid_drawdown_v168 import _pilarcitos

        p = _pilarcitos()
        p.seismic.enabled = True
        p.seismic.kv = 0.05
        sl = slice_surface(p, _dd_circle(), num_slices=N_SLICES)
        w = wrap_for_drawdown(BishopSimplified(), p,
                              num_slices=N_SLICES).compute_fos(
            p, _dd_circle(), sl)
        assert w.is_valid, w.error_message
        assert w.details["kv"] == 0.05, w.details
        assert _DRAWDOWN_KEYS <= set(w.details), w.details

    def test_bishop_inside_reads_the_same_either_way(self):
        """Null control: with Bishop inside the forwarded sign IS the
        fallback sum's, so the check reads the same numbers with the key
        as without it."""
        from ogr_slip2d.checks import base_m_alphas
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import MultiStageDrawdownMethod
        from ogr_slip2d.slicer import slice_surface

        p = _crest_project()
        sl = slice_surface(p, _circle(), num_slices=N_SLICES)
        w = MultiStageDrawdownMethod(BishopSimplified(), "duncan_wright",
                                     num_slices=N_SLICES).compute_fos(
            p, _circle(), sl)
        bare = copy.copy(w)
        bare.details = {k: v for k, v in (w.details or {}).items()
                        if k != "m_alpha_sign"}
        assert base_m_alphas(w) == base_m_alphas(bare)

    def test_the_refusal_path_is_unchanged(self):
        """A stage-1 factor below 1 is still refused, invalid, with its
        reason -- the path that never had a pass to copy from."""
        from ogr_slip2d.methods.base import REASON_DRAWDOWN_NOT_APPLICABLE
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.rapid_drawdown import MultiStageDrawdownMethod
        from ogr_slip2d.slicer import slice_surface

        p = _crest_project()
        for m in p.materials:
            m.strength = type(m.strength)(cohesion=0.0, friction_angle=12.0)
        sl = slice_surface(p, _circle(), num_slices=N_SLICES)
        w = MultiStageDrawdownMethod(BishopSimplified(), "duncan_wright",
                                     num_slices=N_SLICES).compute_fos(
            p, _circle(), sl)
        assert not w.is_valid
        assert w.reason == REASON_DRAWDOWN_NOT_APPLICABLE, w.reason

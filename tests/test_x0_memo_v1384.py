# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.384 (V6 of the compute audit) — the passes of one Bishop or Janbu solve
share what does not read F, and every float is the one a full pass gives.

Why it matters: the fixed point of Bishop (1955) and Janbu (1954) recomputed,
in every pass, each slice's forces, its support load, the linearisation of
its envelope and its trigonometry, though only the denominator m_alpha
(n_alpha) reads F. On K03 ``x0_resisting_pass`` was half the time of the two
methods. A memo that changed one float would move a factor of safety, and
every validated case with it.

The oracle is ``x0_resisting_pass`` of 0.1.383, copied literally below.
- **Each case** runs a sequence of factors as a solve does: the first pass
  fills the memo and the rest replay it. At every factor it compares, with
  ``float.hex``, the sum, the support loads and forces, the zero-strength
  slices and the collapse against the copy, and against the same pass
  without a memo.
- **Then the whole ``compute_fos``**, with the memo, against the same solve
  with the memo taken away.
- **The cases:** dry, with water (ru), a curved envelope (power curve, D84)
  read where an ``imposed`` reader says, an ACTIVE support (stored) and a
  PASSIVE one (recomputed every pass, its load is t_passive / F), with
  Bishop and with Janbu.

Every test is well under a second.
"""
import dataclasses
import math

from ogr_slip2d.methods import bishop, janbu
from ogr_slip2d.methods.bishop import BishopSimplified, X0Pass, slide_sense

FACTORS = (1.0, 1.31, 1.27, 1.2734, 1.27338)


def _x0_0_1_383(slices, kh, kv, slide_sign, sup, fos, imposed=None, *,
                janbu=False):
    """``bishop.x0_resisting_pass`` of 0.1.383, literally: the oracle."""
    from ogr_slip2d.external_forces import slice_forces
    s_list = slices.slices if hasattr(slices, "slices") else slices
    out = X0Pass(sigma_load=[0.0] * len(s_list) if sup.present else None,
                 support_force=[None] * len(s_list) if sup.present else None)
    if sup.present:
        # Only a reinforced surface pays for the import (every pass).
        from ogr_slip2d.support_integration import (support_force_on_slice,
                                                    support_vertical_load)
    total = 0.0
    for i_s, s in enumerate(s_list):
        W_eff = slice_forces(s, kh, kv).w_total
        b = s.width
        if sup.present:
            load = support_vertical_load(
                sup, i_s, s.base_angle, slide_sign, fos)
            W_eff += load
            out.sigma_load[i_s] = load
            out.support_force[i_s] = list(support_force_on_slice(
                sup, i_s, s.base_angle, slide_sign, fos))

        N_est = W_eff * math.cos(s.base_angle)
        raw = N_est - s.pore_pressure * s.base_length
        N_eff_est = max(0.0, raw)
        sigma_n_eff = N_eff_est / max(s.base_length, 1e-9)
        if imposed is not None:
            forced = imposed(i_s, s, W_eff, sigma_n_eff)
            if forced is not None:
                raw, sigma_n_eff = forced, max(0.0, forced)

        c, tan_phi = BishopSimplified._local_c_phi(s, s.material,
                                                   sigma_n_eff)
        if raw < 0.0 and BishopSimplified._zero_strength(s, raw, c, tan_phi):
            out.zero.append(i_s)

        if janbu:
            den = (math.cos(s.base_angle) ** 2) * (
                1.0 + slide_sign * math.tan(s.base_angle) * tan_phi / fos
            )
        else:
            den = math.cos(s.base_angle) + (
                slide_sign * math.sin(s.base_angle) * tan_phi / fos
            )
        if abs(den) < 1e-6:
            out.collapsed = (s.index, den)
            out.total = total
            return out

        total += (
            c * b + (W_eff - s.pore_pressure * b) * tan_phi
        ) / den
    out.total = total
    return out


def _bits(v):
    """Floats as ``float.hex`` (-0.0 and 0.0 differ, NaN equals itself),
    recursively; everything else as it is."""
    if isinstance(v, float):
        return v.hex()
    if isinstance(v, (list, tuple)):
        return type(v)(_bits(x) for x in v)
    if isinstance(v, dict):
        return {k: _bits(x) for k, x in v.items()}
    return v


def _pass_bits(p):
    return _bits((p.total, p.sigma_load, p.support_force, p.zero, p.collapsed))


def _case(kind):
    """(project, circle, slices) for one kind of slope."""
    from ogr_core.materials import PorePressureType
    from ogr_core.materials.builtin_models import PowerCurve
    from ogr_slip2d.slicer import slice_surface
    from test_support_normal_v1137 import _circle, _nail, _project
    support = {"active": _nail(30.0, True),
               "passive": _nail(30.0, False),
               # its tangential part drives the slide: t_passive < 0
               "passive_against": _nail(-60.0, False)}.get(kind)
    p = _project(support)
    m = p.materials[0]
    if kind in ("water", "power", "power0", "seismic"):
        m.pore_pressure = PorePressureType.RU_COEFFICIENT
        m.ru = 0.3
    if kind == "seismic":
        p.seismic.enabled = True
        p.seismic.kh, p.seismic.kv = 0.12, 0.05
    if kind == "power":
        m.strength = PowerCurve(a=3.4, b=0.6, c=0.0, d=0.15, waviness=0.0)
    if kind == "power0":      # through the origin: no strength at sigma <= 0
        m.strength = PowerCurve(a=1.4, b=0.8, c=0.0, d=0.0, waviness=0.0)
    circle = _circle()
    return p, circle, slice_surface(p, circle, num_slices=40)


def _terms(p, circle, sl):
    """(kh, kv, sense of sliding, support terms), as ``compute_fos`` forms
    them."""
    from ogr_slip2d.support_integration import resolve_support_terms
    kh = p.seismic.kh if p.seismic.enabled else 0.0
    kv = p.seismic.kv if p.seismic.enabled else 0.0
    slide = slide_sense(sl, kv)
    return kh, kv, slide, resolve_support_terms(p, circle, sl, slide)


def _imposed(i, _slice, _load, _sigma):
    """A fixed point per slice for every other slice, as the passes of
    ``self_consistent_envelope`` impose one; negative on a few, a base in
    tension."""
    return None if i % 2 else (12.5 * i - 60.0)


class TestEveryPassAsTheFullPass:

    def _sequence(self, kind, imposed=None):
        p, circle, sl = _case(kind)
        kh, kv, slide, sup = _terms(p, circle, sl)
        for is_janbu in (False, True):
            memo = {}
            for f in FACTORS:
                want = _pass_bits(_x0_0_1_383(sl, kh, kv, slide, sup, f,
                                              imposed, janbu=is_janbu))
                bare = bishop.x0_resisting_pass(sl, kh, kv, slide, sup, f,
                                                imposed, janbu=is_janbu)
                kept = bishop.x0_resisting_pass(sl, kh, kv, slide, sup, f,
                                                imposed, janbu=is_janbu,
                                                memo=memo)
                assert _pass_bits(bare) == want, (kind, is_janbu, f)
                assert _pass_bits(kept) == want, (kind, is_janbu, f)
        return sup, memo

    def test_dry(self):
        self._sequence("dry")

    def test_with_water(self):
        self._sequence("water")

    def test_with_water_and_an_earthquake(self):
        self._sequence("seismic")

    def test_a_curved_envelope_read_where_it_is_imposed(self):
        _sup, memo = self._sequence("power", imposed=_imposed)
        assert all(r is not None for r in memo["rows"])

    def test_slices_with_no_strength_are_flagged_in_every_pass(self):
        # A curve through the origin read at the negative stresses the
        # reader imposes on slices 0, 2 and 4: they enter with no strength
        # (D84), and the replayed passes must flag them as the full ones.
        _sup, memo = self._sequence("power0", imposed=_imposed)
        assert [i for i, r in enumerate(memo["rows"]) if r[3]] == [0, 2, 4]

    def test_an_active_support_is_kept(self):
        sup, memo = self._sequence("active")
        crossed = [i for i, v in enumerate(sup.t_active) if v]
        assert crossed and all(memo["rows"][i] is not None for i in crossed)

    def test_a_passive_support_is_recomputed_every_pass(self):
        sup, memo = self._sequence("passive")
        crossed = [i for i, v in enumerate(sup.t_passive) if v]
        assert crossed
        assert [i for i, r in enumerate(memo["rows"]) if r is None] == crossed

    def test_a_passive_term_against_the_slide_is_recomputed_too(self):
        # Any non-zero t_passive reads F (the truthiness test of
        # support_vertical_load), not only a positive one.
        sup, memo = self._sequence("passive_against")
        crossed = [i for i, v in enumerate(sup.t_passive) if v]
        assert crossed and all(sup.t_passive[i] < 0.0 for i in crossed)
        assert [i for i, r in enumerate(memo["rows"]) if r is None] == crossed


class TestWorkCounted:
    """What the memo saves, counted: the envelope is read once per slice
    and solve, not once per slice and pass; a passive slice, every pass."""

    @staticmethod
    def _reads(kind):
        p, circle, sl = _case(kind)
        kh, kv, slide, sup = _terms(p, circle, sl)
        reads = []
        desc = BishopSimplified.__dict__["_local_c_phi"]
        real = desc.__func__

        def spy(*a, **k):
            reads[-1] += 1
            return real(*a, **k)

        BishopSimplified._local_c_phi = staticmethod(spy)
        try:
            memo = {}
            for f in FACTORS:
                reads.append(0)
                bishop.x0_resisting_pass(sl, kh, kv, slide, sup, f,
                                         memo=memo)
        finally:
            BishopSimplified._local_c_phi = desc
        return len(sl.slices), sup, reads

    def test_once_per_slice_and_solve(self):
        n, _sup, reads = self._reads("dry")
        assert reads == [n] + [0] * (len(FACTORS) - 1)

    def test_a_passive_slice_every_pass(self):
        n, sup, reads = self._reads("passive")
        k = sum(1 for v in sup.t_passive if v)
        assert 0 < k < n
        assert reads == [n] + [k] * (len(FACTORS) - 1)


class TestTheSolveAsWithoutTheMemo:
    """The whole ``compute_fos`` of Bishop and of both Janbu, the
    self-consistent envelope's passes included, against the same solve with
    the memo taken away (the module function put back in ``finally``)."""

    FIELDS = ("fos", "converged", "iterations", "base_normal_force",
              "base_shear_force", "base_shear_strength")
    DETAILS = ("sigma_support_load", "support_force", "zero_strength_slices",
               "envelope_stress", "envelope_passes")

    @classmethod
    def _summary(cls, res):
        return _bits(([getattr(res, f, None) for f in cls.FIELDS],
                      [res.details.get(k) for k in cls.DETAILS]))

    def test_bishop_and_janbu_on_every_kind(self):
        from ogr_slip2d.methods import method_registry
        real = bishop.x0_resisting_pass

        def no_memo(*a, memo=None, **k):
            return real(*a, **k)

        for kind in ("dry", "water", "seismic", "power", "power0", "active",
                     "passive", "passive_against"):
            p, circle, sl = _case(kind)
            for mid in ("bishop_simplified", "janbu_simplified",
                        "janbu_corrected"):
                with_memo = method_registry()[mid]().compute_fos(p, circle, sl)
                bishop.x0_resisting_pass = janbu.x0_resisting_pass = no_memo
                try:
                    without = method_registry()[mid]().compute_fos(p, circle,
                                                                    sl)
                finally:
                    bishop.x0_resisting_pass = janbu.x0_resisting_pass = real
                assert with_memo.fos is not None, (kind, mid)
                assert self._summary(with_memo) == self._summary(without), \
                    (kind, mid)


class TestEverySliceAlone:
    """A sum of forty terms hides a one-ulp change in one of them: a term of
    about 15 against a running total of about 600, whose ulp is 64 times
    larger. Taking 1/F out of m_alpha passed every test above and still
    moved F in 3 of 105 solves (found by the review). With a one-slice list
    the total is the term itself."""

    LISTS = ("t_active", "t_passive", "n_press", "nf_h", "nf_v")

    def test_each_term_bit_for_bit(self):
        for kind in ("dry", "water", "seismic", "power", "power0", "active",
                     "passive", "passive_against"):
            imposed = _imposed if kind.startswith("power") else None
            p, circle, sl = _case(kind)
            kh, kv, slide, sup = _terms(p, circle, sl)
            for k, s in enumerate(sl.slices):
                one = sup
                if sup.present:
                    one = dataclasses.replace(sup, **{
                        f: [getattr(sup, f)[k]] for f in self.LISTS})
                imp = None if imposed is None else (
                    lambda i, *a, k=k: imposed(k, *a))
                for is_janbu in (False, True):
                    memo = {}
                    for f in FACTORS:
                        want = _pass_bits(_x0_0_1_383(
                            [s], kh, kv, slide, one, f, imp, janbu=is_janbu))
                        kept = bishop.x0_resisting_pass(
                            [s], kh, kv, slide, one, f, imp,
                            janbu=is_janbu, memo=memo)
                        bare = bishop.x0_resisting_pass(
                            [s], kh, kv, slide, one, f, imp, janbu=is_janbu)
                        assert _pass_bits(kept) == want, (kind, k, f)
                        assert _pass_bits(bare) == want, (kind, k, f)


class TestACollapseOnAReplayedPass:
    """m_alpha (n_alpha) vanishing on a REPLAYED pass, and on a first one:
    the same (slice, den) and partial sum as the full pass. Every collapse
    from the second pass on goes through the replayed branch."""

    def test_bishop_and_janbu(self):
        p, circle, sl = _case("dry")
        kh, kv, slide, sup = _terms(p, circle, sl)
        for is_janbu in (False, True):
            memo = {}
            bishop.x0_resisting_pass(sl, kh, kv, slide, sup, 1.0,
                                     janbu=is_janbu, memo=memo)
            # The root of den in F per slice; the largest is met first as F
            # falls. Just below it, den = -5e-7 (times cos^2 for Janbu).
            roots = [(-r[2] if is_janbu else -r[2] / r[1], r)
                     for r in memo["rows"]]
            _root, (_num, trig, mob, *_rest) = max(roots, key=lambda x: x[0])
            f = -mob / (1.0 + 5e-7) if is_janbu else -mob / (trig + 5e-7)
            want = _x0_0_1_383(sl, kh, kv, slide, sup, f, janbu=is_janbu)
            assert want.collapsed is not None and want.collapsed[1] < 0.0
            kept = bishop.x0_resisting_pass(sl, kh, kv, slide, sup, f,
                                            janbu=is_janbu, memo=memo)
            first = bishop.x0_resisting_pass(sl, kh, kv, slide, sup, f,
                                             janbu=is_janbu, memo={})
            assert _pass_bits(kept) == _pass_bits(want), is_janbu
            assert _pass_bits(first) == _pass_bits(want), is_janbu


class TestEachSolveUsesItsMemo:
    """compute_fos hands every pass of ONE solve the same memo, a fresh one
    per solve, and Janbu's passes replay it as Bishop's do. Without these
    the saving could vanish with every result still right."""

    def test_one_fresh_memo_per_solve(self):
        from ogr_slip2d.methods import method_registry
        real = bishop.x0_resisting_pass
        seen = []

        def spy(*a, memo=None, **k):
            seen.append(memo)
            return real(*a, memo=memo, **k)

        p, circle, sl = _case("dry")
        for mid in ("bishop_simplified", "janbu_simplified",
                    "janbu_corrected"):
            m = method_registry()[mid]()
            bishop.x0_resisting_pass = janbu.x0_resisting_pass = spy
            try:
                del seen[:]
                r1 = m.compute_fos(p, circle, sl)
                first = list(seen)
                del seen[:]
                m.compute_fos(p, circle, sl)
                second = list(seen)
            finally:
                bishop.x0_resisting_pass = janbu.x0_resisting_pass = real
            assert len(first) == r1.iterations > 1, mid
            assert isinstance(first[0], dict), mid
            assert all(x is first[0] for x in first), mid
            assert all(x is second[0] for x in second), mid
            assert second[0] is not first[0], mid

    def test_janbu_reads_the_envelope_once_per_slice(self):
        p, circle, sl = _case("dry")
        kh, kv, slide, sup = _terms(p, circle, sl)
        reads = []
        desc = BishopSimplified.__dict__["_local_c_phi"]
        real = desc.__func__

        def spy(*a, **k):
            reads[-1] += 1
            return real(*a, **k)

        BishopSimplified._local_c_phi = staticmethod(spy)
        try:
            memo = {}
            for f in FACTORS:
                reads.append(0)
                bishop.x0_resisting_pass(sl, kh, kv, slide, sup, f,
                                         janbu=True, memo=memo)
        finally:
            BishopSimplified._local_c_phi = desc
        assert reads == [len(sl.slices)] + [0] * (len(FACTORS) - 1)

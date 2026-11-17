# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.470 (D452) — the factor of Sarma's method next to a nearly cancelled
pair: said, not changed.

WHAT IT IS

The factor is the largest root of Kc(F) = kh (v0.1.461). A straight stretch
cut by a face cancels a factor of Kc exactly (``solver._pairs``); bent a
hair, the factor splits into a root of N and a zero of D, the denominator
of Kc, a hair apart, and the largest root can be that root: problem 4
saturated with its scarp bent 1 cm gives 0.9005, and the next root down,
0.4346, is the one the unbent scarp has (0.4347).

A rule that skipped such a root (within 1.2 % of a zero of D) was measured
and REFUTED in this version's review: the published branch of problem 4
saturated lies 1.4 % from a true zero of D, and kh 0.03, γw = 10 or a floor
of φ 5° bring it inside, the factor falling to 0.128, 0.140 or 0.138. By the
owner's decision the factor stays the largest root, and the run says the
pair: a factor already next to a pole of the recurrence (least |q| under
0.2) that lies within ``solver.NEAR_KC_POLE`` of a zero of D too gets a
note with the next root down (``method.sarma_near_pair``).

INVARIANTS, against references outside this code (AGENTS.md, rule 1)

1. **The factor is the largest root, as it was** (Hoek 1987): problem 4
   dry and saturated and problem 5 at 1e-6 of the bank's tool and ±1 % of
   the published; the review's variants of the saturated case (kh 0.03 and
   0.05, γw = 10, φ 5° on the floor) on the published branch, within 3 %
   of 0.4347; the bent scarp's factor the largest root, judged by
   ``_kc_direct`` (the equilibrium as one linear system, no recurrence).
2. **The pair, judged by the same independent computation**: on the scarp
   bent 1 cm and 2 m (with kh 0 and 0.05) and on the toe of the pairs bent
   0.06°, the factor has a pole of Kc within 1.2 %; the next root the note
   gives is a root of Kc = kh with none between it and the factor (the
   factor's window aside), and it continues the straight surface's, within
   1 % of it.
3. **No pair, no note, no cost**: the published cases, their variants and
   the straight toe (least |q| 0.185, its nearest zero of D far) get no
   note, and ``near_pair`` is not asked where the least |q| is 0.2 or more.
4. **Rule 7**: with ``NEAR_KC_POLE`` = 0 the note goes and the factor stays.
5. **Said**: in English and in Spanish, in the details and in the API.

The independent judge costs about a second per case: it is the check.
"""
from __future__ import annotations

import contextlib
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import test_sarma_pole_v1466 as T66  # noqa: E402
import test_sarma_wedges_v1463 as W63  # noqa: E402

_CACHE: dict = {}
#: The published saturated root of problem 4 (the bank's tool).
_P4 = W63._TOOL4[True]


def _p4_seismic(kh=0.0, gw=9.81, floor_phi=None):
    p = T66._p4(True)
    p.settings.groundwater.pore_fluid_unit_weight = gw
    if kh:
        p.seismic.enabled = True
        p.seismic.kh = kh
    if floor_phi is not None:
        floor = next(m for m in p.materials if m.name == "Sheared Floor")
        floor.strength.params["friction_angle"] = floor_phi
    return p


def _bent(dy, kh=0.0):
    key = ("bent", dy, kh)
    if key not in _CACHE:
        _CACHE[key] = T66._door(_p4_seismic(kh), T66._surface(T66._bent(dy)))
    return _CACHE[key]


def _published(kh=0.0, gw=9.81, floor_phi=None, n=2):
    """The published saturated problem 4, its interface given, n wedges."""
    from ogr_slip2d.surface import attach_vertex_data
    p, s, angles = W63._problem4(True)
    p.settings.sarma.tolerance = 1e-12
    p.settings.sarma.num_slices = n
    p.settings.groundwater.pore_fluid_unit_weight = gw
    if kh:
        p.seismic.enabled = True
        p.seismic.kh = kh
    if floor_phi is not None:
        floor = next(m for m in p.materials if m.name == "Sheared Floor")
        floor.strength.params["friction_angle"] = floor_phi
    attach_vertex_data(s, {k: {"angle": a, "c": None, "phi": None}
                           for k, a in angles.items()})
    return T66._door(p, s)


def _solver_input(result):
    from ogr_slip2d.sarma.wedges import to_solver
    d = result.details
    return to_solver(result.slices, d["kh"], d["kv"])


class _Judge:
    """Kc of the wedges by ``_kc_direct`` of ``test_sarma_solver_v1461``,
    which shares nothing with the recurrence."""

    def __init__(self, bases, faces, slide_sign, senses, kh=0.0, head=0.0):
        from test_sarma_solver_v1461 import _kc_direct, _mirrored
        if slide_sign == -1:
            bases, faces = _mirrored(bases, faces)
            senses = senses[::-1]
        self.kc = lambda F: _kc_direct(bases, faces, F, senses, head)
        self.kh = kh

    def h(self, F):
        v = self.kc(F)
        return None if v is None else v - self.kh

    def is_root(self, F):
        a, b = self.h(F * (1.0 - 1e-9)), self.h(F * (1.0 + 1e-9))
        return a is not None and b is not None and (a > 0.0) != (b > 0.0)

    def changes_near(self, F, eps):
        """Sign changes of Kc - kh within ``eps`` of F on a logarithmic
        sampling of both sides (1e-10 to eps): a lone root makes one, a root
        with a pole of Kc beside it two or more (a pair 1 cm of bend apart
        is a few 1e-6 wide: no linear sampling resolves it)."""
        import numpy as np
        offs = np.logspace(-10, math.log10(eps), 400)
        xs = sorted([F * (1.0 - o) for o in offs] + [F]
                    + [F * (1.0 + o) for o in offs])
        vs = [self.h(x) for x in xs]
        if any(v is None for v in vs):
            return math.inf
        return sum(1 for a, b in zip(vs, vs[1:]) if (a > 0.0) != (b > 0.0))

    def no_root_between(self, low, high, skip):
        """No root of Kc = kh in (low, high) outside ``skip`` = (lo, hi):
        a change of sign there is a pole, told by its size."""
        import numpy as np
        prev = None
        for x in np.geomspace(low * (1.0 + 1e-4), high, 1500):
            if skip[0] <= x <= skip[1]:
                prev = None
                continue
            v = self.h(x)
            assert v is not None, x
            if prev is not None and (v > 0.0) != (prev > 0.0):
                assert abs(v) + abs(prev) > 1.0, ("a root between", low, x)
            prev = v


@contextlib.contextmanager
def _window(value):
    from ogr_slip2d.sarma import solver as SV
    kept = SV.NEAR_KC_POLE
    SV.NEAR_KC_POLE = value
    try:
        yield
    finally:
        SV.NEAR_KC_POLE = kept


# ======================================================================
class TestTheFactorIsTheLargestRoot:

    def test_the_published_and_the_variants_of_the_review(self):
        for n in (2, 25):
            r, out = _published(n=n)
            assert abs(r.fos / _P4 - 1.0) <= 1e-6, (n, r.fos)
            assert "method.sarma_near_pair" not in T66._codes(out)
        # the review's: with the refuted rule 0.128, 0.117, 0.140, 0.138
        for kw in (dict(kh=0.03), dict(kh=0.05), dict(gw=10.0),
                   dict(floor_phi=5.0)):
            r, out = _published(**kw)
            assert abs(r.fos / _P4 - 1.0) <= 0.03, (kw, r.fos)
            assert "sarma_next_root" not in r.details, kw
            assert "method.sarma_near_pair" not in T66._codes(out), kw

    def test_the_bent_scarp_keeps_its_largest_root(self):
        """By a change of sign of the judge's Kc and none above it: next to
        its pole Kc is so steep that the root to 1e-12 leaves Kc = 9e-9,
        over the exact test of ``_assert_largest_root``."""
        from ogr_slip2d.sarma import solver as SV
        for dy in (0.01, 2.0):
            r, _out = _bent(dy)
            si = _solver_input(r)
            sol = SV.solve(si.bases, si.faces, slide_sign=si.slide_sign,
                           head_thrust=si.head_thrust, tolerance=1e-12)
            assert sol.fos == r.fos, (dy, sol.fos, r.fos)
            j = _Judge(si.bases, si.faces, sol.slide_sign, sol.senses)
            F, eps = sol.fos, SV.NEAR_KC_POLE
            assert j.is_root(F), F
            j.no_root_between(F * (1.0 + eps), 100.0, (0.0, 0.0))
        assert abs(_bent(2.0)[0].fos - 0.9232) <= 1e-4


class TestThePairByAnIndependentJudge:

    def _judge_pair(self, bases, faces, sol, next_root, kh=0.0,
                    straight=None):
        from ogr_slip2d.sarma import solver as SV
        eps = SV.NEAR_KC_POLE
        j = _Judge(bases, faces, sol.slide_sign, sol.senses, kh)
        F = sol.fos
        assert j.is_root(F) and j.is_root(next_root), (F, next_root)
        assert j.changes_near(F, eps) >= 2, F
        assert next_root < F
        j.no_root_between(next_root, F, (F * (1.0 - eps), F * (1.0 + eps)))
        if straight is not None:
            assert abs(next_root / straight - 1.0) <= 0.01, (next_root,
                                                             straight)

    def test_the_bent_scarp(self):
        from ogr_slip2d.sarma import solver as SV
        for dy, kh in ((0.01, 0.0), (2.0, 0.0), (2.0, 0.05)):
            r, out = _bent(dy, kh)
            d = r.details
            assert d["sarma_kc_pole_distance"] < SV.NEAR_KC_POLE, (dy, kh)
            assert "method.sarma_near_pair" in T66._codes(out), (dy, kh)
            si = _solver_input(r)
            sol = SV.solve(si.bases, si.faces, kh=kh,
                           slide_sign=si.slide_sign,
                           head_thrust=si.head_thrust, tolerance=1e-12)
            straight = _bent(0.0, kh)[0].fos if kh else _P4
            self._judge_pair(si.bases, si.faces, sol, d["sarma_next_root"],
                             kh, straight=straight if dy < 1.0 else None)
            if dy >= 1.0:
                # 2 m of bend moves the root that continues it a little
                assert abs(d["sarma_next_root"] / straight - 1.0) <= 0.02

    def test_the_toe_of_the_pairs(self):
        from ogr_slip2d.sarma import solver as SV
        from test_sarma_solver_v1461 import TestFalseZeros
        straight = SV.solve(*TestFalseZeros()._toe(), tolerance=1e-12)
        assert SV.near_pair(*TestFalseZeros()._toe(), straight.fos,
                            tolerance=1e-12) is None
        b, f = TestFalseZeros()._toe(dalpha=1e-3)
        sol = SV.solve(b, f, tolerance=1e-12)
        distance, nxt = SV.near_pair(b, f, sol.fos, tolerance=1e-12)
        assert distance < SV.NEAR_KC_POLE
        self._judge_pair(b, f, sol, nxt, straight=straight.fos)

    def test_the_next_root_just_under_the_start(self):
        """A root 3 % under where the search starts is found, not stepped
        over: the straight toe's 1.7408 from 1.8 (and its next, 0.0946,
        from just under it)."""
        from ogr_slip2d.sarma import solver as SV
        from test_sarma_solver_v1461 import TestFalseZeros
        b, f = TestFalseZeros()._toe()
        straight = SV.solve(b, f, tolerance=1e-12).fos
        fr = SV._frame(b, f, 1, 0.0)
        got = SV._lower_root(fr, 0.0, 1.8, 1e-12, 75)
        assert got is not None and abs(got[0] / straight - 1.0) <= 1e-9, got
        low = SV._lower_root(fr, 0.0, got[2], 1e-12, 75)
        assert low is not None and abs(low[0] - 0.0946) <= 1e-3, low

    def test_the_next_of_close_roots(self):
        """The circle of D452 (vertical faces, Ru 0.7, 25 wedges), whose
        roots stand 5 % apart (0.8045, 0.7635, 0.7256…): its note gives the
        one just under the factor, a root of the judge's Kc, with no other
        between them outside the factor's window. A search that started 10 %
        lower would cross two roots in one step and miss both."""
        from ogr_core.materials import Material, MohrCoulomb, PorePressureType
        from ogr_core.project import Project
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        from ogr_slip2d.sarma import solver as SV
        from ogr_slip2d.surface import SlipCircle
        p = Project("D452 circle")
        W63._external(p, ((0, 0), (80, 0), (80, 20), (40, 20), (20, 10),
                          (0, 10)))
        soil = Material(name="soil", unit_weight=18.0, sat_unit_weight=20.0,
                        use_sat_unit_weight=True,
                        strength=MohrCoulomb(cohesion=1.0,
                                             friction_angle=30.0))
        soil.pore_pressure = PorePressureType.RU_COEFFICIENT
        soil.ru = 0.7
        p.materials = [soil]
        p.settings.sarma.tolerance = 1e-12
        p.settings.sarma.slice_angles = "vertical"
        p.settings.sarma.num_slices = 25
        r = evaluate_surfaces(p, SlipCircle(centre_x=30, centre_y=35,
                                            radius=26), ["sarma"]
                              ).results["sarma"]
        nxt = r.details["sarma_next_root"]
        assert r.fos / nxt < 1.06, (r.fos, nxt)
        si = _solver_input(r)
        sol = SV.solve(si.bases, si.faces, slide_sign=si.slide_sign,
                       head_thrust=si.head_thrust, tolerance=1e-12)
        self._judge_pair(si.bases, si.faces, sol, nxt)


class TestNoPairNoNoteNoCost:

    def test_near_pair_is_asked_only_next_to_a_pole(self):
        from ogr_slip2d.sarma import solver as SV
        asked = []
        kept = SV.near_pair

        def spy(*a, **k):
            asked.append(a[2])
            return kept(*a, **k)
        SV.near_pair = spy
        try:
            r0, _o = _published()
            n0 = len(asked)
            r1, _o = T66._door(_p4_seismic(), T66._surface(T66._bent(2.0)))
        finally:
            SV.near_pair = kept
        assert r0.details["sarma_min_abs_q"] >= 0.2 and n0 == 0, asked
        assert r1.details["sarma_min_abs_q"] < 0.2 and asked == [r1.fos]

    def test_switched_off_the_note_goes_and_the_factor_stays(self):
        from ogr_slip2d.sarma import solver as SV
        with _window(0.0):
            r, out = T66._door(_p4_seismic(), T66._surface(T66._bent(2.0)))
        assert r.fos == _bent(2.0)[0].fos
        assert "sarma_next_root" not in r.details
        assert "method.sarma_near_pair" not in T66._codes(out)
        assert "method.sarma_near_pole" in T66._codes(out)
        assert SV.NEAR_KC_POLE == 0.012


class TestItIsSaid:

    def _note(self, out, code):
        for w in out.warnings:
            note = (getattr(w, "args", None) or {}).get("note")
            if isinstance(note, dict) and note.get("code") == code:
                return note
        raise AssertionError((code, out.warnings))

    def test_in_english_and_in_spanish(self):
        from ogr_core.messages import Coded
        from ogr_gui.core_messages import note_text
        from ogr_gui.i18n import current_language, set_language
        r, out = _bent(2.0)
        note = self._note(out, "method.sarma_near_pair")
        assert note["text"] == (
            "the factor of the reported surface, 0.9232, also lies 0.072 % "
            "from a pole of Kc: with the pole beside it, it may be the half "
            "of a root and a pole that almost cancel, as a straight stretch "
            "barely bent leaves them. The factor is kept, the largest root; "
            "the next root down is 0.4291."), note["text"]
        was = current_language()
        set_language("es")
        try:
            es = note_text(Coded(note["text"], note["code"], note["args"]))
        finally:
            set_language(was)
        assert es == (
            "el factor de la superficie del resultado, 0.9232, queda además "
            "a un 0.072 % de un polo de Kc: con el polo de al lado, puede ser "
            "la mitad de una raíz y un polo que casi se cancelan, como los "
            "deja un tramo recto apenas doblado. El factor se queda, la raíz "
            "mayor; la siguiente raíz hacia abajo es 0.4291."), es

    def test_the_details_and_the_api(self):
        from ogr_api.results import lem_summary
        r, _out = _bent(2.0)
        got = lem_summary(r)["details"]
        assert got["sarma_next_root"] == round(r.details["sarma_next_root"],
                                               6)
        assert got["sarma_kc_pole_distance"] == round(
            r.details["sarma_kc_pole_distance"], 6)
        r, _out = _published()
        assert "sarma_next_root" not in (lem_summary(r).get("details") or {})

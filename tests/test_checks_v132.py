# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.32 — Post-analysis admissibility checks (anomaly A3).

Implements and pins down the reference's two documented checks:

* **Tensile Stress Check** — negative effective normal stress on slice
  bases, tested AFTER convergence, over a percentage of slices measured
  from the toe (default 95 %; the crest slices are exempt because they
  are legitimately the tension-crack zone). Allowable tensile stress is
  zero except for Hoek-Brown, Generalised Hoek-Brown and Shear-Normal
  Function.
* **m-alpha Check** (Whitman & Bailey, 1967) — surfaces whose final
  iteration has m_alpha < 0.2 on any slice.

Both are OFF by default, matching the reference, where tensile normal
stresses are permitted unless the user opts in.

v0.1.82 — the invariant these tests protect changed, because the checks
were being evaluated in the wrong sign convention. ``m_alpha`` is not
symmetric in ``alpha``, so it only means anything when read with the same
``slide_sign`` the solver used, and both checks dropped that factor. The
consequence was a check that got both answers backwards: it flagged the
reference-validated critical circle (a false positive, and the reason the
default was believed to be "correct rather than merely conventional")
while missing the base tension on a genuinely degenerate wedge. The tests
below now pin the corrected diagnosis in both directions.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_core.geometry import Polyline, Vertex  # noqa: E402
from ogr_slip2d import BishopSimplified, Spencer  # noqa: E402
from ogr_slip2d.checks import (  # noqa: E402
    base_effective_stresses,
    base_m_alphas,
    check_surface,
    m_alpha_check,
    tensile_stress_check,
)
from ogr_slip2d.search import BlockSearch, GridSearch  # noqa: E402
from ogr_slip2d.surface import SlipCircle, SlipSurface  # noqa: E402

# The degenerate surface found by Block Search: a deep wedge closed by a
# near-vertical rising segment (+73.6 deg), 17 m below the toe.
_DEGENERATE = [(29.1, 50.0), (47.5, 31.9), (69.8, 8.1),
               (72.8, 18.4), (79.5, 25.0)]
_HEALTHY = [(32.6, 50.0), (50.2, 32.6), (59.3, 23.9),
            (74.3, 15.9), (83.5, 25.0)]
_REF_CIRCLE = dict(centre_x=88.0, centre_y=70.5, radius=47.212)


def _eval_poly(pts, **kw):
    p = _ej1_project()
    surf = SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in pts], closed=False))
    ev = GridSearch(method=Spencer(), num_slices=18, min_area=0.0, **kw)
    return ev.evaluate_surface(p, surf)


def _eval_ref_circle(**kw):
    p = _ej1_project()
    ev = GridSearch(method=BishopSimplified(), num_slices=25,
                    min_area=0.0, **kw)
    return ev.evaluate_circle(p, SlipCircle(**_REF_CIRCLE))


class TestMAlphaCheck:
    def test_flags_the_degenerate_surface(self):
        """v0.1.66 — the assertion used to be ``len(bad) >= 5``, a count
        captured from the slicing of the day. It is now ``bad`` is
        non-empty, because the count legitimately changed and the count
        was never the invariant.

        This wedge crosses ej1's material boundaries three times. Until
        v0.1.66 the slice edges were a uniform division, so the slices
        spanning those crossings took the friction angle of whichever
        layer their midpoint fell in and applied it to a base that lay
        partly in the other. Cutting at the crossings changed the factor
        of safety of this surface from 0.683 to 0.797 and the number of
        slices with m_alpha < 0.2 from eight to two — with the sequence of
        base materials unchanged and no sliver slices (widths 2.64 to
        2.93 m), which is what says the difference is the fix rather than
        a new artefact.

        What must hold is the diagnosis: this surface is flagged and the
        healthy one below is not.
        """
        r = _eval_poly(_DEGENERATE)
        ok, bad = m_alpha_check(r)
        assert not ok
        assert bad, bad
        assert min(base_m_alphas(r)) < 0.2

    def test_healthy_surface_passes(self):
        r = _eval_poly(_HEALTHY)
        ok, _bad = m_alpha_check(r)
        assert ok
        assert min(base_m_alphas(r)) >= 0.2

    def test_reference_circle_passes_the_check(self):
        """v0.1.82 — the decisive result, and it is the opposite of what
        this test used to assert.

        The reference-VALIDATED critical circle (FoS 0.883, matching the
        reference to 0.02 %) was being "flagged" with min m_alpha =
        −0.0100 on 5 slices. That was not a property of the circle: it
        slides towards decreasing x, so ``slide_sign = −1``, and reading
        ``cos α + sin α·tan φ/F`` without that factor evaluates the wrong
        branch. With the sign the solver itself uses, min m_alpha =
        +0.9282 and no slice is anywhere near the 0.2 limit.

        The number is the evidence, so it is asserted, not just the
        boolean: a future regression that half-restores the old sign
        would still pass a bare ``assert ok``.
        """
        r = _eval_ref_circle()
        assert abs(r.fos - 0.882889) / 0.882889 < 0.01
        ok, bad = m_alpha_check(r)
        assert ok, bad
        assert not bad
        assert min(base_m_alphas(r)) > 0.9, min(base_m_alphas(r))

    def test_sign_convention_matches_the_solver(self):
        """The identity that makes the check meaningful at all.

        ``base_m_alphas`` must reproduce, slice by slice, the m_alpha the
        method used inside its own iteration. Recomputing it here from
        Bishop's published expression is the only way to keep the two from
        drifting apart again.
        """
        import math as _m

        from ogr_slip2d.methods.bishop import BishopSimplified as _B
        r = _eval_ref_circle()
        sgn = 1.0 if sum(s.weight * _m.sin(s.base_angle)
                         for s in r.slices) >= 0 else -1.0
        assert sgn == -1.0            # this model slides towards -x
        for s, got in zip(r.slices, base_m_alphas(r)):
            a = s.base_angle
            l = max(s.base_length, 1e-12)
            sig = max(0.0, s.weight * _m.cos(a) - s.pore_pressure * l) / l
            _c, tan_phi = _B._local_c_phi(s, s.material, sig)
            want = _m.cos(a) + sgn * _m.sin(a) * tan_phi / r.fos
            assert abs(got - want) < 1e-12, (got, want)


class TestTensileStressCheck:
    def test_percentage_measured_from_the_toe(self):
        r = _eval_poly(_HEALTHY)
        n = len(list(r.slices))
        ok_all, _ = tensile_stress_check(r, 100.0)
        ok_none, bad_none = tensile_stress_check(r, 0.0)
        assert ok_none and not bad_none      # nothing tested
        assert isinstance(ok_all, bool)
        assert len(base_effective_stresses(r)) == n

    def test_tension_only_on_the_degenerate_surface(self):
        """v0.1.82 — with the sign convention corrected, the two checks
        agree on the same slice instead of contradicting each other.

        Slice 14 of the degenerate wedge is the near-vertical RISING
        segment (+73.8°) in the passive zone. Its m_alpha goes to −0.42,
        which flips the sign of the base normal force and reports a base
        effective stress of about −300 kPa. Both checks therefore point at
        the same physical pathology — exactly the case the reference
        describes for its error −112 ("deep seated slip surfaces with many
        high negative base angle slices in the passive zone").

        The healthy surface stays clean, which is what makes the
        distinction a diagnosis and not a blanket rejection.
        """
        ok_bad, bad = tensile_stress_check(_eval_poly(_DEGENERATE))
        assert not ok_bad
        assert bad == [14], bad
        ok_good, clean = tensile_stress_check(_eval_poly(_HEALTHY))
        assert ok_good, clean

    def test_detects_tension_when_present(self):
        """Synthetic check of the criterion itself: an artificially large
        pore pressure drives the base effective stress negative."""
        r = _eval_poly(_HEALTHY)
        for s in r.slices:
            s.pore_pressure = 1e4
        ok, bad = tensile_stress_check(r)
        assert not ok and bad


class TestPostFilterBehaviour:
    def test_disabled_by_default(self):
        s = GridSearch(method=Spencer())
        assert s.reject_tensile is False
        assert s.check_m_alpha is False

    def test_inadmissible_surfaces_are_marked_not_dropped(self):
        """The check runs as a POST-FILTER: the surface keeps its
        converged factor of safety and stays in the evaluation list (so
        search algorithms that steer on it, such as Simulated Annealing,
        keep working) but is excluded when the critical is selected."""
        r = _eval_poly(_DEGENERATE, check_m_alpha=True)
        assert r is not None
        assert r.is_valid                    # the FoS is still there
        assert r.admissible is False
        assert r.admissibility_note

    def test_critical_skips_inadmissible(self):
        p = _ej1_project()
        base = BlockSearch(method=Spencer(), num_surfaces=120,
                           num_slices=18, seed=0).run(p)
        checked = BlockSearch(method=Spencer(), num_surfaces=120,
                              num_slices=18, seed=0,
                              check_m_alpha=True).run(p)
        assert base.critical.fos < 0.8
        assert checked.critical.fos > base.critical.fos
        assert checked.inadmissible_count > 0
        # The evaluation list is NOT shortened by the check
        assert checked.valid_count == base.valid_count

    def test_falls_back_when_everything_is_inadmissible(self):
        """If every surface fails, the user still gets an answer plus the
        count, instead of an empty result."""
        from ogr_slip2d.search import SimulatedAnnealingSearch
        p = _ej1_project()
        r = SimulatedAnnealingSearch(method=BishopSimplified(),
                                     num_slices=18, generation_steps=15,
                                     check_m_alpha=True).run(p)
        if r.valid_count and r.inadmissible_count == r.valid_count:
            assert r.critical is not None

    def test_checks_forwarded_by_every_search(self):
        from ogr_slip2d.search import (
            PathSearch, SimulatedAnnealingSearch,
        )
        for cls in (GridSearch, BlockSearch, PathSearch,
                    SimulatedAnnealingSearch):
            s = cls(method=Spencer(), reject_tensile=True,
                    check_m_alpha=True, tensile_percent=90.0)
            assert s.reject_tensile and s.check_m_alpha
            assert abs(s.tensile_percent - 90.0) < 1e-9

    def test_check_surface_helper(self):
        r = _eval_poly(_DEGENERATE)
        ok, reason = check_surface(r, tensile=False, m_alpha=False)
        assert ok and reason is None
        ok, reason = check_surface(r, m_alpha=True)
        assert not ok and "m_alpha" in reason

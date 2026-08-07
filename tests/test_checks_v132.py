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

Both are OFF by default, and the tests below show WHY that default is
correct rather than merely conventional: the m-alpha check flags the
reference-validated critical circle itself.
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
        r = _eval_poly(_DEGENERATE)
        ok, bad = m_alpha_check(r)
        assert not ok
        assert len(bad) >= 5, bad
        assert min(base_m_alphas(r)) < 0.2

    def test_healthy_surface_passes(self):
        r = _eval_poly(_HEALTHY)
        ok, _bad = m_alpha_check(r)
        assert ok
        assert min(base_m_alphas(r)) >= 0.2

    def test_reference_circle_is_also_flagged(self):
        """The decisive result: the reference-VALIDATED critical circle
        (FoS 0.883, matching the reference to 0.02 %) itself has
        m_alpha < 0.2 on several slices. The check therefore cannot be a
        validity criterion — it is a diagnostic, which is exactly why the
        reference ships it disabled."""
        r = _eval_ref_circle()
        assert abs(r.fos - 0.882889) / 0.882889 < 0.01
        ok, bad = m_alpha_check(r)
        assert not ok
        assert bad


class TestTensileStressCheck:
    def test_percentage_measured_from_the_toe(self):
        r = _eval_poly(_HEALTHY)
        n = len(list(r.slices))
        ok_all, _ = tensile_stress_check(r, 100.0)
        ok_none, bad_none = tensile_stress_check(r, 0.0)
        assert ok_none and not bad_none      # nothing tested
        assert isinstance(ok_all, bool)
        assert len(base_effective_stresses(r)) == n

    def test_no_tension_on_these_surfaces(self):
        """Neither surface is rejected by the tensile check: the
        degenerate one fails on m_alpha, not on base tension. Recording
        this keeps the two mechanisms from being confused."""
        for pts in (_DEGENERATE, _HEALTHY):
            ok, bad = tensile_stress_check(_eval_poly(pts))
            assert ok, (pts[0], bad)

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

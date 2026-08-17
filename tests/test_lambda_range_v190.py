# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.90 — Spencer and GLE reach the λ their surfaces actually need.

WHAT INVARIANT THIS PROTECTS, in two halves that have to hold together:

1. **Widening the reach cannot move a surface that already converged.** The
   extended λ are sampled ONLY when the calibrated grid brackets nothing, so
   every surface that brackets today follows the identical code path with the
   identical samples. This is asserted, not argued: the same circles are
   solved with the range clipped to ±1.5 and with it open to 6, and the
   factors of safety must be bit-identical wherever the clipped run
   converged.
2. **A surface whose root lies beyond ±1.5 is solved instead of abandoned.**

Why this file exists. Both Spencer and GLE find λ by sampling a calibrated
grid, looking for a sign change in ``F_f(λ) − F_m(λ)``, and refining it. The
grid stopped at ±1.5. Measured on a Simulated Annealing candidate GLE could
not solve::

    λ = 1.500   F_f 0.7351   F_m 1.0551   F_f−F_m = −0.320
    λ = 2.994   F_f 1.1257   F_m 1.1262   F_f−F_m = −0.0005   <- the root

``F_f − F_m`` is monotone in λ here, so "no sign change" never meant "no
root": it meant the root was out of reach. Every one of the 61 candidates of
that run failed with "no λ-bracket"; not one of them was unsolvable.

The number 6 is not chosen, it is the reference's: its own models carry
``min_lambda: -0.1`` and ``max_lambda: 6``, with the enforcement checkboxes
off, so it does not restrict λ by default at all.

This had already bitten once. ``ogr_core/project/settings.py`` records that
the range was ±1.25 and became ±1.5 in v0.1.74 **because the
reference-validated Ej_1 circle converges at λ = 1.4919** — widened exactly
enough for the case that failed at the time. That is the same shape of
mistake as the radius rule of v0.1.88: a parameter calibrated against the
cases that happened to be tested rather than against the phenomenon.

Measured effect on the two reference grids, circles the reference solved and
this program did not:

    Ej_1 spencer   936 -> 172        Ej_1 gle    1314 -> 422
    Ej_2 spencer   932 -> 126        Ej_2 gle    1433 -> 446

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

# A Simulated Annealing candidate on the Ej_1 geometry whose root sits at
# λ ≈ 2.99. Captured from seed 1 of the run described above; it is here as
# GEOMETRY, not as a captured answer — what is asserted about it is that a
# root exists and is found, not what number it produces.
_BEYOND_15 = [(50.00, 50.00), (51.30, 45.51), (54.63, 36.76), (57.81, 31.43),
              (60.69, 28.70), (63.81, 27.32), (66.92, 26.88), (70.27, 26.64),
              (75.00, 25.00)]


def _ej1():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_slide_validation_ej1 import _ej1_project
    return _ej1_project()


def _surface(pts):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in pts], closed=False))


def _solve(method_cls, pts, **kw):
    from ogr_slip2d.search import GridSearch
    ev = GridSearch(method=method_cls(**kw), num_slices=18, min_area=0.0,
                    check_m_alpha=False)
    return ev.evaluate_surface(_ej1(), _surface(pts))


class TestTheCalibratedGridIsUnchanged:
    """Half 1: the first sampling pass must be what it always was."""

    def test_the_shape_is_still_the_calibrated_list(self):
        from ogr_slip2d import GLEMorgensternPrice
        assert list(GLEMorgensternPrice().lambda_grid()) == [
            -1.5, -1.0, -0.6, -0.4, -0.2, -0.1, 0.0,
            0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5]

    def test_widening_the_range_adds_nothing_to_the_first_pass(self):
        """The whole safety argument in one line: max_lambda 6 must not put
        a single extra sample in the grid that runs first."""
        from ogr_slip2d import GLEMorgensternPrice, Spencer
        for cls in (GLEMorgensternPrice, Spencer):
            assert (cls(max_lambda=1.5).lambda_grid()
                    == cls(max_lambda=6.0).lambda_grid()), cls.DISPLAY_NAME

    def test_a_narrowed_range_still_narrows_the_first_pass(self):
        from ogr_slip2d import GLEMorgensternPrice
        grid = GLEMorgensternPrice(min_lambda=-0.5, max_lambda=1.0).lambda_grid()
        assert min(grid) == -0.5 and max(grid) == 1.0, grid


class TestTheExtensionRespectsTheUser:
    """Rule 7 in reverse: a range the user narrowed has to keep meaning what
    it meant, or the control would have stopped doing anything."""

    def test_a_narrowed_range_gets_no_extension(self):
        from ogr_slip2d import GLEMorgensternPrice
        assert GLEMorgensternPrice(min_lambda=-0.5,
                                   max_lambda=1.0).lambda_grid_extension() == []

    def test_the_default_reaches_the_reference_maximum(self):
        from ogr_slip2d import GLEMorgensternPrice, Spencer
        for cls in (GLEMorgensternPrice, Spencer):
            ext = cls().lambda_grid_extension()
            assert ext, cls.DISPLAY_NAME
            assert abs(max(ext) - 6.0) < 1e-12, ext
            assert min(ext) > 1.5, ext

    def test_the_extension_is_positive_only(self):
        """λ is the interslice ratio X/E; the side difficult surfaces reach
        for is the steep one. The reference's own lower bound is −0.1, well
        inside the calibrated shape."""
        from ogr_slip2d import GLEMorgensternPrice
        assert all(v > 0 for v in GLEMorgensternPrice().lambda_grid_extension())

    def test_an_explicit_intermediate_range_is_honoured(self):
        from ogr_slip2d import Spencer
        ext = Spencer(max_lambda=3.0).lambda_grid_extension()
        assert ext and max(ext) <= 3.0 + 1e-12, ext


class TestTheRootBeyondFifteenIsFound:
    """Half 2, on the surface that motivated the change."""

    def test_gle_converges_where_it_used_to_give_up(self):
        from ogr_slip2d import GLEMorgensternPrice
        clipped = _solve(GLEMorgensternPrice, _BEYOND_15, max_lambda=1.5)
        opened = _solve(GLEMorgensternPrice, _BEYOND_15, max_lambda=6.0)
        assert not clipped.converged, "the case no longer reproduces"
        assert "λ-bracket" in (clipped.error_message or "")
        assert opened.converged, opened.error_message
        assert not opened.error_message, opened.error_message

    def test_the_root_it_finds_is_beyond_the_calibrated_grid(self):
        from ogr_slip2d import GLEMorgensternPrice
        opened = _solve(GLEMorgensternPrice, _BEYOND_15, max_lambda=6.0)
        lam = opened.details.get("lambda")
        assert lam is not None and lam > 1.5, lam

    def test_force_and_moment_agree_at_that_root(self):
        """The real check on the answer, and it needs no reference value:
        the whole point of λ is that F_f(λ) = F_m(λ), so at the root the two
        equilibria must agree to the solver's own tolerance.

        Read by watching the solver's own inner solve rather than calling it
        again from here. Reconstructing that call means guessing the sliding
        sign, the circle terms and the resolved support forces, and guessing
        them wrong returns NaN with no complaint — which is exactly what the
        first draft of this case did.
        """
        from ogr_slip2d import GLEMorgensternPrice
        from ogr_slip2d.slicer import slice_surface
        p, surf = _ej1(), _surface(_BEYOND_15)
        sl = slice_surface(p, surf, num_slices=18)
        m = GLEMorgensternPrice(max_lambda=6.0)
        seen = []
        inner = m._inner_solve

        def watch(slices, lam, *a, **k):
            ff, fm = inner(slices, lam, *a, **k)
            seen.append((lam, ff, fm))
            return ff, fm

        m._inner_solve = watch
        res = m.compute_fos(p, surf, sl)
        assert res.converged, res.error_message
        # compute_fos re-solves at the converged λ last of all.
        lam, ff, fm = seen[-1]
        assert abs(lam - res.details["lambda"]) < 1e-12, (lam, res.details)
        assert math.isfinite(ff) and math.isfinite(fm), (ff, fm)
        assert abs(ff - fm) < 1e-2, (lam, ff, fm)

    def test_annealing_with_gle_returns_surfaces_again(self):
        """0 valid surfaces on every seed was the symptom that started this."""
        from ogr_slip2d import GLEMorgensternPrice
        from ogr_slip2d.search import SimulatedAnnealingSearch
        for seed in (0, 1, 2):
            r = SimulatedAnnealingSearch(
                method=GLEMorgensternPrice(), num_slices=18,
                generation_steps=15, seed=seed).run(_ej1())
            assert r.valid_count > 0, f"seed {seed}: still 0 valid"
            assert r.critical is not None, seed


class TestNothingThatConvergedCanMove:
    """The assertion the safety of this change rests on, measured rather
    than argued. Over a sample of the Ej_1 reference grid: every circle the
    clipped range solved must give the IDENTICAL factor of safety with the
    range open, and none may be lost.

    The two known exceptions are not exceptions to that rule — they are
    circles the clipped run reported as converged through the no-bracket
    fallback (nearest |F_f − F_m| under 0.02, with no λ recorded at all).
    They are excluded here by asking for a real root, which is what makes
    the assertion exact instead of tolerant.
    """

    _CIRCLES = [(84.0, 66.0, 41.5014358), (88.0, 70.5, 47.2124436),
                (84.0, 70.5, 45.0), (92.0, 75.0, 52.0), (80.0, 61.5, 38.0),
                (96.0, 84.0, 60.0), (76.0, 57.0, 34.0), (100.0, 93.0, 70.0)]

    def test_identical_where_the_clipped_range_found_a_root(self):
        from ogr_slip2d import GLEMorgensternPrice, Spencer
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        p = _ej1()
        for cls in (GLEMorgensternPrice, Spencer):
            clipped = GridSearch(method=cls(max_lambda=1.5), num_slices=25,
                                 min_area=0.5, check_m_alpha=False)
            opened = GridSearch(method=cls(max_lambda=6.0), num_slices=25,
                                min_area=0.5, check_m_alpha=False)
            compared = 0
            for xc, yc, r in self._CIRCLES:
                c = SlipCircle(centre_x=xc, centre_y=yc, radius=r)
                a = clipped.evaluate_circle(p, c)
                b = opened.evaluate_circle(p, c)
                if a is None or not a.is_valid:
                    continue
                assert b is not None and b.is_valid, (cls.DISPLAY_NAME, xc, yc, r)
                if a.details.get("lambda") is None:
                    continue          # solved by the fallback, see docstring
                compared += 1
                assert a.fos == b.fos, (cls.DISPLAY_NAME, xc, yc, r,
                                        a.fos, b.fos)
            assert compared >= 4, (cls.DISPLAY_NAME, compared)

    def test_no_circle_is_lost(self):
        from ogr_slip2d import GLEMorgensternPrice, Spencer
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle
        p = _ej1()
        for cls in (GLEMorgensternPrice, Spencer):
            clipped = GridSearch(method=cls(max_lambda=1.5), num_slices=25,
                                 min_area=0.5, check_m_alpha=False)
            opened = GridSearch(method=cls(max_lambda=6.0), num_slices=25,
                                min_area=0.5, check_m_alpha=False)
            for xc, yc, r in self._CIRCLES:
                c = SlipCircle(centre_x=xc, centre_y=yc, radius=r)
                a = clipped.evaluate_circle(p, c)
                b = opened.evaluate_circle(p, c)
                if a is not None and a.is_valid:
                    assert b is not None and b.is_valid, (
                        cls.DISPLAY_NAME, xc, yc, r)


class TestStoredProjectsMigrate:
    """The pattern this project already uses: migrate only the value that
    WAS the default, because anything else the user typed on purpose."""

    def test_the_old_default_migrates(self):
        from ogr_core.project.settings import AdvancedSettings
        s = AdvancedSettings.from_dict({"max_lambda": 1.5})
        assert abs(s.max_lambda - 6.0) < 1e-12, s.max_lambda

    def test_the_pre_v174_default_migrates_all_the_way(self):
        """1.25 became 1.5 in v0.1.74 and 6.0 now; a project stored back
        then must not land on an intermediate nobody uses."""
        from ogr_core.project.settings import AdvancedSettings
        s = AdvancedSettings.from_dict({"max_lambda": 1.25})
        assert abs(s.max_lambda - 6.0) < 1e-12, s.max_lambda

    def test_a_deliberate_value_is_kept(self):
        from ogr_core.project.settings import AdvancedSettings
        s = AdvancedSettings.from_dict({"max_lambda": 2.25})
        assert abs(s.max_lambda - 2.25) < 1e-12, s.max_lambda

    def test_the_new_default_is_the_reference_range(self):
        from ogr_core.project.settings import AdvancedSettings
        assert abs(AdvancedSettings().max_lambda - 6.0) < 1e-12

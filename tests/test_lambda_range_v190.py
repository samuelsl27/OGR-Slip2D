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
        """v0.1.106 — asked for explicitly, because the DEFAULT lower bound
        is now the reference's own −0.1 and clips the negative tail. The
        shape itself is untouched; see ``AdvancedSettings.min_lambda``."""
        from ogr_slip2d import GLEMorgensternPrice
        assert list(GLEMorgensternPrice(min_lambda=-1.5).lambda_grid()) == [
            -1.5, -1.0, -0.6, -0.4, -0.2, -0.1, 0.0,
            0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5]

    def test_the_default_grid_starts_at_the_reference_lower_bound(self):
        """And a case for the clip itself, so it cannot be undone silently.

        λ is the inclination of the inter-slice force, X/E = tanθ. The
        reference's own models carry ``min_lambda: -0.1``; this program
        reached −1.5 as symmetry with a positive side that v0.1.74 widened
        for a real reason. With ``F_f − F_m`` now able to cross more than
        once, that unjustified tail was catching spurious roots — see
        ``TestSpuriousNegativeRoots`` below.
        """
        from ogr_slip2d import GLEMorgensternPrice, Spencer
        for cls in (GLEMorgensternPrice, Spencer):
            grid = cls().lambda_grid()
            assert abs(min(grid) + 0.1) < 1e-12, (cls.DISPLAY_NAME, grid)
            assert all(v >= -0.1 - 1e-12 for v in grid), grid

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


class TestTheReachOfTheLambdaSearch:
    """Half 2, and v0.1.106 turned its witness inside out.

    This class was written around a Simulated Annealing candidate whose root
    sat at λ ≈ 2.99, far outside the calibrated ±1.5, and it asserted that
    the clipped range could NOT solve it while the open one could. Both
    halves of that have stopped being true, and the reason is the finding:

        the same surface, same slices, same everything
            v0.1.105   root at λ = 2.994
            v0.1.106   root at λ = 0.782

    The force branch used to sum ``S·cos α`` where the horizontal equilibrium
    of the mass gives ``S·sec α``. That depressed ``F_f`` — by ``cos²α`` per
    slice, so most on the steep parts — and pushed the crossing ``F_f = F_m``
    out to λ values no slope needs. **Both widenings of the range were
    chasing that**: ±1.25 → ±1.5 in v0.1.74 for the Ej_1 circle "needing"
    λ = 1.4919 (it needs 0.862), and → 6 in v0.1.90 for 61 annealing
    candidates that "had no bracket". ``docs/PENDIENTES.md`` §9 predicted
    exactly this before it was measured, and
    ``docs/audits/spencer_gle_interslice_v179.md`` has the equation.

    Measured after the correction, over three Simulated Annealing runs on
    this same model: 341 solved surfaces between Spencer and GLE, **not one**
    with |λ| > 1.5, and **not one** failing with "no λ-bracket" — against 61
    of 61 failing before v0.1.90.

    So the reach is no longer exercised by any surface this project has. It
    is KEPT, because 6 is the reference's own upper bound and narrowing a
    range on the strength of "nothing needs it today" is how the ±1.25 of
    v0.1.74 came about in the first place. What this class asserts is what
    is still true and still checkable: the surface solves, the mechanism
    still respects the user's range, and the reach is there if a surface
    ever wants it.
    """

    def test_the_witness_surface_solves_inside_the_calibrated_shape(self):
        from ogr_slip2d import GLEMorgensternPrice
        opened = _solve(GLEMorgensternPrice, _BEYOND_15, max_lambda=6.0)
        assert opened.converged, opened.error_message
        lam = opened.details.get("lambda")
        assert lam is not None and abs(lam) <= 1.5, (
            f"λ = {lam}, outside the calibrated shape. If a surface needs "
            f"the extension again, say so here rather than leaving this "
            f"case asserting the opposite of what happens.")

    def test_clipping_the_range_below_the_root_still_loses_it(self):
        """The mechanism, exercised on purpose now that no surface does it
        by accident: a range that excludes the root must fail to bracket,
        or ``max_lambda`` would be a setting that does nothing (rule 7)."""
        from ogr_slip2d import GLEMorgensternPrice
        opened = _solve(GLEMorgensternPrice, _BEYOND_15, max_lambda=6.0)
        root = opened.details["lambda"]
        clipped = _solve(GLEMorgensternPrice, _BEYOND_15,
                         max_lambda=round(root, 3) - 0.3)
        assert not clipped.converged or (
            abs(clipped.details.get("lambda", 0.0) - root) > 1e-6), (
            f"clipping below λ = {root:.3f} changed nothing")

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


# ======================================================================
class TestSpuriousNegativeRoots:
    """Why the default lower bound came back to the reference's -0.1.

    ``F_f(lambda) - F_m(lambda)`` had exactly one crossing until v0.1.106,
    for a reason that was itself the defect: ``F_m`` did not depend on lambda
    at all. Once the inter-slice shear reaches the base normal it does, and
    the difference can cross more than once. Ching and Fredlund (1983) is the
    reference for that and for rejecting the extra crossings.

    The one that bit is Duncan and Wright verification #70 on a polyline —
    an already-submerged slope whose answer is 1.60, the referee value the
    file ``test_ponded_water_v161`` validates. Sampling from -1.5 upwards,
    the outer search met a crossing at lambda = -1.5 and took it, because it
    takes the FIRST sign change in ascending lambda:

        lambda = -1.5   F_f 1.0755  F_m 1.0452   -> crossing, F = 1.051
        lambda = +0.3   F_f 1.6      F_m 1.6      -> the answer

    A resultant at lambda = -1.5 is inclined 56 degrees downward-BACKWARD on
    a mass sliding forward. It is not a stress state; it is arithmetic.
    """

    def test_the_submerged_polyline_lands_on_its_referee_value(self):
        """The case itself, end to end. It is here and not only in
        ``test_noncircular_moments_v1105`` because what it guards is the
        LAMBDA RANGE, and someone widening that range back would break it
        without ever opening the other file."""
        import copy
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from ogr_core.geometry import Polyline, Vertex
        from ogr_core.geometry.ground import ground_surface
        from ogr_slip2d import Spencer
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle, SlipSurface
        from test_ponded_water_v161 import CIRCLE, buoyant

        c = SlipCircle(**CIRCLE)
        g = ground_surface(buoyant().external_boundary().polyline)
        x_l, x_r = c.intersect_with_ground(g)
        pts = [(x_l + (x_r - x_l) * i / 24,
                SlipCircle(**CIRCLE).base_y_at(x_l + (x_r - x_l) * i / 24))
               for i in range(25)]
        surface = SlipSurface(polyline=Polyline(
            vertices=[Vertex(x, y) for x, y in pts], closed=False))
        p = copy.deepcopy(buoyant())
        p.settings.search.axis_x = CIRCLE["centre_x"]
        p.settings.search.axis_y = CIRCLE["centre_y"]

        res = GridSearch(method=Spencer(), num_slices=50,
                         min_area=0.0).evaluate_surface(p, surface)
        assert res is not None and res.is_valid, res
        assert abs(res.fos - 1.60) / 1.60 < 0.01, res.fos
        assert res.details["lambda"] > 0.0, res.details["lambda"]

    def test_widening_the_range_backwards_is_what_loses_it(self):
        """The other half, so the cause is pinned and not just the symptom.

        With the old -1.5 lower bound handed in explicitly, the same surface
        returns the spurious crossing. If some later change makes this pass
        too, the clip has stopped being load-bearing and can be revisited —
        which is a better outcome than the clip quietly outliving its reason.
        """
        import copy
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from ogr_core.geometry import Polyline, Vertex
        from ogr_core.geometry.ground import ground_surface
        from ogr_slip2d import Spencer
        from ogr_slip2d.search import GridSearch
        from ogr_slip2d.surface import SlipCircle, SlipSurface
        from test_ponded_water_v161 import CIRCLE, buoyant

        c = SlipCircle(**CIRCLE)
        g = ground_surface(buoyant().external_boundary().polyline)
        x_l, x_r = c.intersect_with_ground(g)
        pts = [(x_l + (x_r - x_l) * i / 24,
                SlipCircle(**CIRCLE).base_y_at(x_l + (x_r - x_l) * i / 24))
               for i in range(25)]
        surface = SlipSurface(polyline=Polyline(
            vertices=[Vertex(x, y) for x, y in pts], closed=False))
        p = copy.deepcopy(buoyant())
        p.settings.search.axis_x = CIRCLE["centre_x"]
        p.settings.search.axis_y = CIRCLE["centre_y"]

        res = GridSearch(method=Spencer(min_lambda=-1.5), num_slices=50,
                         min_area=0.0).evaluate_surface(p, surface)
        assert res is not None
        assert abs(res.fos - 1.60) / 1.60 > 0.10, (
            f"the -1.5 lower bound no longer loses this surface "
            f"({res.fos:.4f}); the clip of v0.1.106 may be revisitable")

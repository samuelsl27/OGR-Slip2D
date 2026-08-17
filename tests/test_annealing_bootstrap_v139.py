# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.39 — Simulated Annealing bootstrap (anomaly A5).

The reported symptom was that Simulated Annealing produced NO valid
surfaces at all for some configurations. The cause was not the analysis
method (the original diagnosis blamed Spencer) but the **bootstrap**:
the starting surface was built by drawing every inner vertex
independently at random and hoping the result passed the admissibility
filters. The binding one is unimodality — the surface must descend to a
single low point and rise again — whose probability for n independently
ordered values is about 2^(n-1)/n!, i.e. well under 1 % for the default
nine vertices. Unlucky seeds therefore exhausted all 200 attempts without
a single valid candidate, and the search returned nothing at all
(``valid_count == 0`` AND ``invalid_count == 0``).

The fix constructs the starting surface so it is admissible BY
CONSTRUCTION: a bowl hanging below the entry-exit chord, single-valued
in x and with one low point. Randomness now controls the depth and
asymmetry of the bowl rather than each vertex independently.
"""
from __future__ import annotations

import statistics as pystat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_slip2d import (  # noqa: E402
    BishopSimplified,
    GLEMorgensternPrice,
    JanbuSimplified,
    LoweKarafiath,
    OrdinaryFellenius,
    Spencer,
)
from ogr_slip2d.search import SimulatedAnnealingSearch  # noqa: E402


def _run(method=None, seed=1, steps=15):
    return SimulatedAnnealingSearch(
        method=method or BishopSimplified(), num_slices=18,
        generation_steps=steps, seed=seed).run(_ej1_project())


class TestAnomalyA5:
    def test_the_failing_seed_now_works(self):
        """seed = 1 previously produced nothing at all."""
        r = _run(seed=1)
        assert r.critical is not None
        assert r.valid_count > 0

    def test_every_seed_produces_surfaces(self):
        """The bootstrap must not depend on luck."""
        empty = [s for s in range(20) if _run(seed=s).critical is None]
        assert not empty, empty

    def test_all_methods_work_on_the_failing_seed(self):
        """The original diagnosis blamed Spencer; in fact EVERY method
        failed on that seed, which is what pointed at the bootstrap.

        v0.1.89 — GLE moved to its own case below. It is NOT excused here:
        it is asserted to fail, so the day it stops failing this file goes
        red and somebody has to come and delete that case.
        """
        for m in (OrdinaryFellenius(), BishopSimplified(),
                  JanbuSimplified(), Spencer(), LoweKarafiath()):
            r = _run(method=m, seed=1)
            assert r.critical is not None, m.DISPLAY_NAME
            assert r.valid_count > 0, m.DISPLAY_NAME

    def test_gle_under_annealing_produces_nothing_open_defect(self):
        """GLE + Simulated Annealing yields NO valid surface. Open defect,
        recorded rather than hidden. See docs/PENDIENTES.md.

        Introduced by v0.1.89's slicer change, which places slice
        boundaries at the slip surface's own vertices — the principle
        v0.1.66 stated for material crossings ("the base of a slice belongs
        to one material or to another, never to a blend"), applied to the
        surface's geometry. That change fixes a WRONG NUMBER: Block Search
        used to return 0.65-0.82 on a stable slope whose circular minimum
        is 1.1239, from surfaces containing near-vertical steps narrower
        than a slice, invisible to every check. Across five seeds it now
        returns 1.13-1.16.

        The cost is here, and it was taken deliberately: a wrong number a
        user would act on is worse than a visible absence of one. The
        failure is narrow — GLE under SA only. Under Block Search GLE gives
        10-17 valid surfaces, and under circular Grid Search it is
        untouched, because circles have no vertices to cut at.

        Measured: 0 valid surfaces for seeds 0 through 7, at 18, 27, 36, 54
        and 72 slices. Not a fragile edge — a systematic one, which is why
        it is worth its own investigation instead of a tolerance.
        """
        for seed in (0, 1, 2):
            r = _run(method=GLEMorgensternPrice(), seed=seed)
            assert r.valid_count == 0, (
                f"seed {seed}: GLE now returns {r.valid_count} valid "
                f"surfaces. If this is a fix, delete this case and put GLE "
                f"back in the list above.")

    def test_spencer_specifically(self):
        r = _run(method=Spencer(), seed=1)
        assert r.valid_count > 10
        assert 0.3 < r.critical.fos < 2.0


class TestBootstrapConstruction:
    def test_constructed_surface_is_admissible(self):
        """Every parameter set the bootstrap produces must pass the
        admissibility filters — that is the whole point of building it
        rather than sampling it."""
        import random

        from ogr_core.geometry import BoundaryType, Vertex
        from ogr_slip2d.search import PathSearch

        p = _ej1_project()
        s = SimulatedAnnealingSearch(method=BishopSimplified(),
                                     num_slices=18, generation_steps=10)
        ext = [b for b in p.boundaries
               if b.btype == BoundaryType.EXTERNAL][0]
        top = PathSearch._ground_profile(ext.polyline.vertices)
        xmin, ymin, xmax, ymax = p.bounding_box()

        steep_i, steep = 0, -1.0
        for i in range(len(top) - 1):
            ddx = top[i + 1].x - top[i].x
            if abs(ddx) < 1e-9:
                continue
            sl = abs((top[i + 1].y - top[i].y) / ddx)
            if sl > steep:
                steep, steep_i = sl, i
        fa, fb = top[steep_i], top[steep_i + 1]
        x1, xN = min(fa.x, fb.x), max(fa.x, fb.x)
        y1 = s._interp_top_y(top, x1)
        yN = s._interp_top_y(top, xN)
        N = s.initial_vertices
        D = [x1 + i * (xN - x1) / (N - 1) for i in range(N)]
        y_toe = min(y1, yN)
        y_floor = max(y_toe - 0.15 * max(ymax - y_toe, 1.0), ymin)
        dy = ymax - ymin

        rng = random.Random(1)
        ok = 0
        for attempt in range(25):
            PX, PY = s._bootstrap_parameters(
                N - 2, D, top, y_floor, dy, ymax, x1, xN, y1, yN, rng,
                attempt)
            assert len(PX) == N - 2 and len(PY) == N - 2
            assert all(0.0 <= v <= 1.0 for v in PX + PY)
            inner = []
            for m in range(1, N - 1):
                xm = D[m - 1] + PX[m - 1] * (D[m] - D[m - 1])
                ty = s._interp_top_y(top, xm)
                y_top = ty if ty is not None else ymax
                lo, hi = y_floor, y_top - 0.05 * dy
                if hi <= lo:
                    hi = lo + 0.1
                inner.append(Vertex(xm, lo + PY[m - 1] * (hi - lo)))
            verts = [Vertex(x1, y1)] + inner + [Vertex(xN, yN)]
            ys = [v.y for v in verts]
            imin = ys.index(min(ys))
            unimodal = (
                all(ys[a] <= ys[a - 1] + 1e-6
                    for a in range(1, imin + 1))
                and all(ys[a] >= ys[a - 1] - 1e-6
                        for a in range(imin + 1, len(ys))))
            increasing_x = all(b.x > a.x for a, b in
                               zip(verts[:-1], verts[1:]))
            below_chord = all(
                v.y <= y1 + (v.x - x1) / (xN - x1) * (yN - y1) + 1e-6
                for v in verts[1:-1])
            assert unimodal, attempt
            assert increasing_x, attempt
            assert below_chord, attempt
            ok += 1
        assert ok == 25

    def test_randomness_still_explores(self):
        """Different seeds must give different starting bowls, otherwise
        the search would be deterministic."""
        crits = {(_run(seed=s).critical.fos if _run(seed=s).critical
                  else None) for s in (2, 3, 4, 5)}
        assert len(crits) > 1


class TestQuality:
    def test_results_are_in_a_physical_range(self):
        vals = []
        for seed in range(10):
            r = _run(seed=seed, steps=30)
            assert r.critical is not None
            vals.append(r.critical.fos)
        assert all(0.2 < v < 3.0 for v in vals), vals
        assert pystat.mean(vals) < 1.5

    def test_produces_a_useful_number_of_surfaces(self):
        r = _run(seed=3, steps=40)
        assert r.valid_count > 20

    def test_seed_is_reproducible(self):
        a = _run(seed=9, steps=20)
        b = _run(seed=9, steps=20)
        assert abs(a.critical.fos - b.critical.fos) < 1e-12
        assert a.valid_count == b.valid_count

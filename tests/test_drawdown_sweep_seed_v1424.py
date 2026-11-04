# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.424 (D373) — a level of the configured drawdown sweep answers the same
factor of safety whatever else the sweep visits.

WHAT INVARIANT THIS PROTECTS
----------------------------
``run_configured_drawdown_sweep`` built ONE search per method and handed it
to ``run_drawdown_sweep`` as the factory, so every level re-ran the same
object. The Slope Search and the Particle Swarm draw their generator in
``__init__`` and ``run`` does not reset it: each level started from the
random state the previous level left. Measured with the compute audit's
probe S2 (0.1.377) on Morgenstern's slope with a seeded Slope Search (300
surfaces, seed 12345, 18 slices): the total drawdown answered 1.20381 in a
sweep of 2 levels and 1.20561 in one of 4 — the same water, another factor
depending on how many levels came before. The owner's decision (option A):
a new search for every level, as Overall Slope builds one per sample.

THE LAW, NOT A SNAPSHOT
-----------------------
No factor is pinned. A level of the sweep must equal what the SAME search,
built fresh from the same project, answers at that level on its own
(``build_search(...).run(project_at_level(...))``). It follows that the
total drawdown — the same state of the water in both sweeps — gives the
same factor with 2 levels and with 4, which is what failed. The total
drawdown is compared, and not the level "0": with 4 levels the lowest one
is 100 - 3 * (100 / 3), about -1.4e-14, a different number.

The Grid is the control: it draws nothing, so it obeys the law in the old
tree and in the new one alike.

WHAT IT COSTS, AND WHY
----------------------
About 12 s. A sweep is a whole search per level, and what is under test
needs two sweeps (3 and 5 levels) plus the three levels on their own: 11
searches per search type. Most of it is the Slope Search, whose
refinement walk (up to 120 steps on each of its best 8 circles) has no
setting, so a population of 20 still evaluates about 590 circles. The
slices are 10, not Morgenstern's 18, because no factor here is compared
with Morgenstern's: only runs of the same model with each other. In the
tree before the fix the four Slope and swarm cases fail and the two grid
cases pass.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_MID = "bishop_simplified"
_TOTAL = None          # the total drawdown, as ``default_levels`` writes it
_CACHE: dict = {}


def _project(search_method):
    """Morgenstern's slope (``test_drawdown_sweep_v170``) with a seeded
    search, configured through the API as ``test_groundwater_ops_v1200``
    does: 10 slices, a small grid, a small Slope Search and a small swarm.

    Optimize Surfaces is turned off. It is on by default for the swarm, and
    here it was 95 % of the swarm's cost (a walk of 3267 evaluations per
    level, 10 s); it seeds its own walk from the project, so it reads
    nothing of the generator under test."""
    import test_drawdown_sweep_v170 as dd
    from ogr_api import Workspace, call
    ws = Workspace()
    pid = ws.add(dd._homogeneous()).id
    call(ws, "analysis_configure", project_id=pid,
         methods=[_MID], surface_type="circular",
         search_method=search_method, num_slices=10,
         grid={"x_min": 60, "x_max": 240, "y_min": 160, "y_max": 420,
               "nx": 2, "ny": 2},
         radius_increment=3, failure_direction="right_to_left")
    p = ws.get(pid).project
    s = p.settings
    s.search.num_surfaces = 20
    s.search.optimize_enabled = False
    s.search.pso_num_particles = 8
    s.search.pso_num_iterations = 5
    s.statistics.seed = 12345
    return p


def _sweeps(search_method):
    """The configured sweep with 2 and with 4 levels, once per search."""
    if search_method not in _CACHE:
        from ogr_slip2d.analysis_runner import run_configured_drawdown_sweep
        p = _project(search_method)
        two = run_configured_drawdown_sweep(p, [_MID], n_levels=2)[0]
        four = run_configured_drawdown_sweep(p, [_MID], n_levels=4)[0]
        _CACHE[search_method] = (p, two.by_method[_MID],
                                 four.by_method[_MID])
    return _CACHE[search_method]


def _alone(project, level):
    """The factor the same search, built fresh, answers at ``level``."""
    from ogr_core.hydraulic.drawdown_levels import project_at_level
    from ogr_core.project import prepare_analysis_project
    from ogr_slip2d.analysis_runner import build_search
    factored = prepare_analysis_project(project)[0]
    run = build_search(factored, _MID).run(project_at_level(factored, level))
    return run.critical.fos


def _total(sweep):
    return sweep.fos[sweep.levels.index(_TOTAL)]


# ======================================================================
class TestTheSameWaterTheSameFactor:

    def test_slope_search(self):
        _p, two, four = _sweeps("slope")
        assert _total(two) == _total(four), (_total(two), _total(four))

    def test_particle_swarm(self):
        _p, two, four = _sweeps("particle_swarm")
        assert _total(two) == _total(four), (_total(two), _total(four))

    def test_the_grid_control(self):
        _p, two, four = _sweeps("grid")
        assert _total(two) == _total(four)


class TestEveryLevelIsItsOwnSearch:
    """The law the equality above follows from: every level of the sweep
    is the search built fresh and run at that level alone."""

    def _check(self, search_method):
        p, two, _four = _sweeps(search_method)
        assert len(two.levels) == 3
        for level, fos in zip(two.levels, two.fos):
            assert fos is not None
            assert fos == _alone(p, level), (search_method, level, fos)

    def test_slope_search(self):
        self._check("slope")

    def test_particle_swarm(self):
        self._check("particle_swarm")

    def test_the_grid(self):
        self._check("grid")

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.132 — the annealing stops where the user says it stops.

**The invariant**: ``sa_num_fos_compared_before_stopping`` is the n_eps of
the stopping criterion, and the loop that stops must read it. It is rule 7
in its purest form: the field was declared with the reference value 5,
saved in the ``.ogr``, written by three places in the dialog and read by
nobody, while ``_vfsa`` broke on a hand-written ``no_improve_passes >= 3``
(D07c(a), reported in v0.1.103 and closed here).

**The external reference** is the paper of the formulation, Su, X. (2009),
*Global Optimization of General Failure Surfaces in Slope Analysis by
Hybrid Simulated Annealing*, University of Waterloo:

* section 2.1.7 — "if there has not been any visible improvement for the
  global optimum in the previous n_eps consecutive runs, the algorithm is
  to be stopped". That is exactly the shape of the loop, so the setting IS
  n_eps and there is no off-by-one to negotiate;
* section 3.1 — the parameter set used for the verification cases is
  "c = 8, T_in = 1.0, with stopping criterion N_eps = 5" and "a stopping
  criterion tolerance of 1e-04". So 5 — the value the field already
  declared — comes from the paper, and the 3 came from nowhere.

**What the measurement said**, because two things about it are worth not
re-walking:

* the sign the defect claimed was FALSE. "A longer search can only lower
  the factor or leave it" is not what happens: the annealing is stochastic
  and the local phase starts wherever the global one left it, so a
  different stopping point is a different basin. Going 3 -> 5 on five
  seeds, the caso 002 model improved on the three that moved (1.3325 ->
  1.3317, 1.3416 -> 1.3394, 1.3397 -> 1.3385) and the slope below got
  WORSE on the one that moved (1.0808 -> 1.0927, seed 7). Best-of-five did
  not change in either model. It is the same non-monotonicity
  ``docs/PENDIENTES.md`` section 0b records for ``generation_steps``;
* 3 against 5 is NOT a contrast a test can be built on — it moves one seed
  in five here, which is what section 0b had already measured. The reason
  is structural: the outer loop runs ``K = max(4, generation_steps / 50)``
  passes, so n_eps only bites while it is smaller than K. With the engine
  default of 200 steps K is 4 and the paper's own N_eps = 5 can never
  fire. The contrast below is 2 against 20, and it moves every seed tried.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_annealing_inequality_v1119 import _sa_slope  # noqa: E402

#: Steps and slices kept small on purpose: these tests measure where the
#: loop stops, not a factor of safety against a reference. Optimize
#: Surfaces stays OFF for the same reason — it is a post-process that
#: cannot move the stopping criterion and costs six times the run.
_STEPS = 300
_SLICES = 20
_SEEDS = (1234, 2024, 7)

#: (seed, n_eps) -> (progress reports, min_fos). Shared because two of the
#: tests below read the same runs and each one costs ~1.4 s.
_RUNS: dict = {}


def _run(seed: int, n_eps: int):
    key = (seed, n_eps)
    if key not in _RUNS:
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import SimulatedAnnealingSearch

        project, _toe, _crest = _sa_slope()
        reports = []
        s = SimulatedAnnealingSearch(
            method=BishopSimplified(), initial_vertices=9,
            generation_steps=_STEPS, num_slices=_SLICES, seed=seed,
            num_fos_compared_before_stopping=n_eps,
            progress_cb=lambda done, total: reports.append(done),
        )
        r = s.run(project)
        assert r.critical is not None, f"seed {seed} found nothing"
        # One report per outer pass that did NOT break, plus a last one
        # after the local phase. Both runs carry that same last one, so
        # comparing the counts compares the passes.
        _RUNS[key] = (len(reports), r.min_fos)
    return _RUNS[key]


# ======================================================================
class TestTheSettingReachesTheSearch:

    @staticmethod
    def _project(n_eps: int):
        project, _toe, _crest = _sa_slope()
        s = project.settings.search
        s.surface_type = "non_circular"
        s.search_method = "simulated_annealing"
        s.sa_num_fos_compared_before_stopping = n_eps
        return project

    def test_the_declared_value_reaches_the_search(self):
        from ogr_slip2d.analysis_runner import build_search
        p = self._project(7)
        assert build_search(
            p, "bishop_simplified").num_fos_compared_before_stopping == 7

    def test_the_default_is_the_one_the_paper_adopts(self):
        """Su (2009) section 3.1: N_eps = 5. Note this is NOT the
        migration guard the temperature coefficient had — there the
        default equalled the constant the code ran on, so wiring it up
        moved nothing. Here the code broke on 3 and the setting says 5,
        so stored annealing results CAN move, and the changelog of
        v0.1.132 measures by how much."""
        from ogr_core.project.settings import SearchSettings
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import SimulatedAnnealingSearch

        assert SearchSettings().sa_num_fos_compared_before_stopping == 5
        assert SimulatedAnnealingSearch(
            method=BishopSimplified()).num_fos_compared_before_stopping == 5

    def test_below_one_is_not_a_criterion_and_is_clamped(self):
        from ogr_slip2d import BishopSimplified
        from ogr_slip2d.search import SimulatedAnnealingSearch

        s = SimulatedAnnealingSearch(method=BishopSimplified(),
                                     num_fos_compared_before_stopping=0)
        assert s.num_fos_compared_before_stopping == 1


# ======================================================================
class TestTheSettingMovesTheSearch:
    """Rule 7. A control that does not change the result is worse than no
    control at all, because the user believes the analysis honours it."""

    #: Small enough to bite (K = 6 outer passes at 300 steps) against
    #: large enough never to fire.
    LOW, HIGH = 2, 20

    def test_it_stops_the_outer_loop_earlier(self):
        """The direct measurement, and a deterministic one: the two runs
        are bit-identical until the smaller n_eps breaks, so the smaller
        one can never report MORE passes, and it has to report fewer at
        least once or the setting does nothing."""
        low = [_run(sd, self.LOW)[0] for sd in _SEEDS]
        high = [_run(sd, self.HIGH)[0] for sd in _SEEDS]
        for sd, lo, hi in zip(_SEEDS, low, high):
            assert lo <= hi, (
                "seed %d ran MORE passes with n_eps=%d (%d) than with "
                "n_eps=%d (%d)" % (sd, self.LOW, lo, self.HIGH, hi))
        assert sum(low) < sum(high), (
            "the stopping criterion never fired: %s vs %s passes over "
            "seeds %s" % (low, high, list(_SEEDS)))

    def test_it_moves_the_number(self):
        """Not "for every seed": a run only diverges once a pass actually
        fails to improve, and on some seeds the loop exhausts its K passes
        either way. The honest statement is over the handful of runs an
        engineer would make."""
        moved = [sd for sd in _SEEDS
                 if _run(sd, self.LOW)[1] != _run(sd, self.HIGH)[1]]
        assert moved, (
            "n_eps=%d and n_eps=%d gave the same factor of safety on every "
            "seed %s: the setting is inert" % (self.LOW, self.HIGH,
                                               list(_SEEDS)))

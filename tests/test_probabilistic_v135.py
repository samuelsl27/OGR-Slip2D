# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.35 — Probabilistic engine, Global Minimum (Phase P2).

Validation strategy: every statistic is cross-checked against an
INDEPENDENT computation rather than a stored snapshot.

* the factors of safety produced by the engine are recomputed by hand,
  sample by sample, and must match exactly;
* the probability of failure must equal the counted fraction below 1;
* the reliability index must equal (mean - 1) / sigma;
* with zero-variance variables every sample must reproduce the
  deterministic factor of safety exactly;
* the mean must sit close to the deterministic value when the variables
  are centred on their means;
* the user's project must be byte-for-byte unchanged after the run.
"""
from __future__ import annotations

import math
import statistics as pystat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_core.statistics import (  # noqa: E402
    Distribution,
    DistributionType as DT,
    SamplingMethod as SM,
    apply_sample,
    available_variables,
    clone_project,
    run_global_minimum,
    sample_project_variables,
)
from ogr_slip2d.analysis_runner import build_method  # noqa: E402
from ogr_slip2d.search import GridSearch  # noqa: E402


def _deterministic(project, methods=("bishop_simplified",), grid=(4, 4, 6)):
    """Small deterministic search giving each method its own critical.

    v0.1.108 — through ``build_method``, and not ``BishopSimplified()``.
    Since this version the statistical engines build their method the way
    the PROJECT configures it, so a deterministic run made with the class
    defaults is a different calculation: the project tolerance is 0.005
    against the class's 0.001, which is worth about 3e-4 in the factor of
    safety — enough to break the 1e-6 identities below, and rightly so.

    v0.1.255 (D128) — ``grid`` is ``(nx, ny, radius increments)``. Seven
    tests share the 4 x 4 x 6 default, on which Bishop and Spencer pick the
    SAME circle; a test about two methods' surfaces needs a grid where they
    part, and asks for it instead of changing everyone's.
    """
    nx, ny, ri = grid
    out = {}
    for mid in methods:
        r = GridSearch(method=build_method(project, mid, 18),
                       grid_x=(70, 100),
                       grid_y=(60, 85), grid_nx=nx, grid_ny=ny,
                       radius_increment=ri, min_radius=15, num_slices=18,
                       min_area=0.5).run(project)
        out[mid] = r.critical
    return out


def _sampled_on(run):
    """``run()``, and the surface of every evaluation it made, by method.

    v0.1.255 (D128). Recorded at ``_evaluate_on``, the one call through
    which the engine evaluates a sample (and the probe of D88), keyed by
    ``_surface_key`` — type and geometry to the last digit, extent
    included — and tagged by the ``method_id`` of the result. Restored in
    ``finally``: a module function left patched would leak into every test
    that runs after this one (rule 5).
    """
    import ogr_core.statistics.probabilistic as P
    seen: dict = {}
    original = P._evaluate_on

    def spy(project, search, surface):
        r = original(project, search, surface)
        if r is not None and getattr(r, "surface", None) is not None:
            seen.setdefault(r.method_id, []).append(
                P._surface_key(r.surface.to_dict()))
        return r

    P._evaluate_on = spy
    try:
        res = run()
    finally:
        P._evaluate_on = original
    return res, seen


def _not_on_their_own_surfaces(res, det, seen) -> list:
    """What breaks "each method is sampled on its own deterministic
    surface", one line per problem; empty when nothing does."""
    from ogr_core.statistics.probabilistic import _surface_key
    problems = []
    for mid, crit in det.items():
        key = _surface_key(crit.surface.to_dict())
        mres = res.by_method.get(mid)
        if mres is None:
            problems.append("%s: not sampled (%s)" % (mid, res.notes.get(mid)))
            continue
        if mres.summary()["surface_key"] != key:
            problems.append("%s: the summary names another surface" % mid)
        keys = seen.get(mid) or []
        if not keys:
            problems.append("%s: no evaluation recorded" % mid)
        wrong = [k for k in keys if k != key]
        if wrong:
            problems.append("%s: %d of %d evaluations on another surface"
                            % (mid, len(wrong), len(keys)))
    return problems


def _cohesion_var(project, std_dev=3.0, span=9.0):
    mat = project.materials[0]
    v = [x for x in available_variables(project)
         if x.param == "cohesion" and x.target_id == mat.id][0]
    v.distribution = Distribution(
        DT.NORMAL, mean=mat.strength.params["cohesion"],
        std_dev=std_dev, rel_min=span, rel_max=span)
    return v


class TestGlobalMinimumEngine:
    def test_produces_statistics(self):
        p = _ej1_project()
        det = _deterministic(p)
        res = run_global_minimum(p, det, [_cohesion_var(p)],
                                 num_samples=60, sampling=SM.LATIN_HYPERCUBE,
                                 seed=3, num_slices=18)
        assert res.ok
        st = res.by_method["bishop_simplified"].statistics
        assert st.n == 60
        assert st.std_dev > 0

    def test_values_match_an_independent_recomputation(self):
        """The decisive check: replay the same samples by hand and
        compare factor by factor."""
        p = _ej1_project()
        det = _deterministic(p)
        v = _cohesion_var(p)
        n = 25
        res = run_global_minimum(p, det, [v], num_samples=n,
                                 sampling=SM.LATIN_HYPERCUBE, seed=7,
                                 num_slices=18)
        engine = res.by_method["bishop_simplified"].statistics.values

        samples = sample_project_variables([v], n, SM.LATIN_HYPERCUBE, 7)
        surface = det["bishop_simplified"].surface
        # v0.1.108 — ``build_method`` and not ``BishopSimplified()``: since
        # this version the engine builds its method the way the project
        # configures it, so a hand recomputation with the class defaults is
        # no longer the same calculation. It showed up here as 0.89318
        # against 0.89288, a tolerance apart — which is the point of the
        # change, not a casualty of it: the engine used to ignore the
        # convergence settings the user chose.
        # v0.1.202 — the project's own admissibility screens, and a sample
        # counts only when valid AND admissible: the reference's "numtotal
        # = total number of VALID analyses", where -112 / -120 are invalid.
        search = GridSearch(method=build_method(p, "bishop_simplified", 18),
                            num_slices=18, min_area=0.0,
                            **p.settings.admissibility_kwargs())
        manual = []
        for i in range(n):
            clone = clone_project(p)
            apply_sample(clone, [v], {v.key: samples[v.key][i]})
            r = search.evaluate_circle(clone, surface)
            if r is not None and r.is_valid and r.admissible:
                manual.append(r.fos)
        assert len(manual) == len(engine)
        for a, b in zip(manual, engine):
            assert abs(a - b) < 1e-9, (a, b)

    def test_probability_of_failure_is_the_counted_fraction(self):
        p = _ej1_project()
        det = _deterministic(p)
        res = run_global_minimum(p, det, [_cohesion_var(p)],
                                 num_samples=80, sampling=SM.LATIN_HYPERCUBE,
                                 seed=5, num_slices=18)
        mres = res.by_method["bishop_simplified"]
        vals = mres.statistics.values
        expected = sum(1 for v in vals if v < 1.0) / len(vals)
        assert abs(mres.probability_of_failure - expected) < 1e-12

    def test_reliability_index_formula(self):
        p = _ej1_project()
        det = _deterministic(p)
        res = run_global_minimum(p, det, [_cohesion_var(p)],
                                 num_samples=60, sampling=SM.LATIN_HYPERCUBE,
                                 seed=9, num_slices=18)
        mres = res.by_method["bishop_simplified"]
        vals = mres.statistics.values
        expected = (pystat.mean(vals) - 1.0) / pystat.stdev(vals)
        assert abs(mres.reliability_index - expected) < 1e-9

    def test_zero_variance_reproduces_the_deterministic_value(self):
        """With a degenerate distribution the run must collapse onto the
        deterministic answer — a strong end-to-end consistency check."""
        p = _ej1_project()
        det = _deterministic(p)
        v = _cohesion_var(p, std_dev=2.0, span=0.0)   # not random
        res = run_global_minimum(p, det, [v], num_samples=10,
                                 sampling=SM.MONTE_CARLO, seed=1,
                                 num_slices=18)
        # No active variable at all -> the engine reports it
        assert not res.ok
        assert "random variable" in res.notes.get("error", "").lower()

    def test_mean_near_deterministic_when_centred(self):
        p = _ej1_project()
        det = _deterministic(p)
        res = run_global_minimum(p, det, [_cohesion_var(p, 2.0, 6.0)],
                                 num_samples=200,
                                 sampling=SM.LATIN_HYPERCUBE, seed=4,
                                 num_slices=18)
        mres = res.by_method["bishop_simplified"]
        assert abs(mres.mean_fos - mres.deterministic_fos) < 0.05

    def _two_methods(self):
        """Ej_1 on the 6 x 6 x 8 grid, where Bishop and Spencer part:
        (90; 76.67; R 53.44) against (80; 60; R 35.12)."""
        p = _ej1_project()
        det = _deterministic(p, ("bishop_simplified", "spencer"),
                             grid=(6, 6, 8))
        return p, det

    def _run(self, p, det):
        return run_global_minimum(p, det, [_cohesion_var(p)],
                                  num_samples=30,
                                  sampling=SM.LATIN_HYPERCUBE, seed=2,
                                  num_slices=18)

    def test_each_method_keeps_its_own_surface(self):
        """Every method is sampled on ITS OWN deterministic surface.

        WHAT INVARIANT THIS PROTECTS (D59, D128). The reference stresses
        that every analysis method can have a different global minimum, so
        a Global Minimum run samples each method on the surface ITS search
        found. Until v0.1.255 this test asserted ``surface is not None`` and
        a copied deterministic factor: it passed with a composite degraded
        to a circle (D59), would have passed with both methods sampled on
        one circle, and ran on a 4 x 4 grid where Bishop and Spencer pick
        the same circle anyway — a green test watching nothing. Now: the
        two deterministic surfaces differ (premise), every evaluation of
        each method is on its own surface to the last digit
        (``_surface_key``, D87), the summary names it, and no sample changed
        mass (D89). ``test_a_shared_seed_is_denounced`` proves the check
        can fail.
        """
        from ogr_core.statistics.probabilistic import _surface_key
        p, det = self._two_methods()
        keys = {mid: _surface_key(c.surface.to_dict())
                for mid, c in det.items()}
        assert keys["bishop_simplified"] != keys["spencer"], keys
        res, seen = _sampled_on(lambda: self._run(p, det))
        assert set(res.by_method) == {"bishop_simplified", "spencer"}
        for mid, mres in res.by_method.items():
            assert mres.mass_switches == 0, (mid, mres.mass_switches)
            assert abs(mres.deterministic_fos - det[mid].fos) < 1e-12
        assert _not_on_their_own_surfaces(res, det, seen) == []

    def test_a_shared_seed_is_denounced(self):
        """The check above fails when both methods get Bishop's seed.

        Twice. With only ``_rebuild_surface`` sabotaged, the probe of D88
        refuses Spencer — its seed comes back as Bishop's circle — and the
        check says Spencer was not sampled. With the probe sabotaged too,
        Spencer IS sampled, on Bishop's circle, and the check says every
        one of its evaluations was on another surface. Both patches undone
        in ``finally`` (rule 5).
        """
        import ogr_core.statistics.probabilistic as P
        p, det = self._two_methods()
        bishop = det["bishop_simplified"].surface.to_dict()
        rebuild, probe = P._rebuild_surface, P._does_not_reevaluate_to_itself
        try:
            P._rebuild_surface = lambda sd: rebuild(bishop)
            res, seen = _sampled_on(lambda: self._run(p, det))
            said = _not_on_their_own_surfaces(res, det, seen)
            assert any(s.startswith("spencer: not sampled") for s in said), (
                said)
            P._does_not_reevaluate_to_itself = lambda *a, **k: None
            res, seen = _sampled_on(lambda: self._run(p, det))
            said = _not_on_their_own_surfaces(res, det, seen)
            assert any(s.startswith("spencer:") and "another surface" in s
                       for s in said), said
        finally:
            P._rebuild_surface, P._does_not_reevaluate_to_itself = (
                rebuild, probe)

    def test_project_is_not_modified(self):
        p = _ej1_project()
        before = p.to_dict()
        det = _deterministic(p)
        run_global_minimum(p, det, [_cohesion_var(p)], num_samples=40,
                           sampling=SM.LATIN_HYPERCUBE, seed=6,
                           num_slices=18)
        assert p.to_dict() == before

    def test_correlated_variables_run(self):
        p = _ej1_project()
        det = _deterministic(p)
        mat = p.materials[0]
        av = available_variables(p)
        c = [x for x in av if x.param == "cohesion"
             and x.target_id == mat.id][0]
        f = [x for x in av if x.param == "friction_angle"
             and x.target_id == mat.id][0]
        c.distribution = Distribution(DT.NORMAL, mean=15.0, std_dev=3.0,
                                      rel_min=9.0, rel_max=9.0)
        f.distribution = Distribution(DT.NORMAL, mean=25.0, std_dev=4.0,
                                      rel_min=12.0, rel_max=12.0)
        f.correlated_with = c.key
        f.correlation = -0.5
        res = run_global_minimum(p, det, [c, f], num_samples=60,
                                 sampling=SM.LATIN_HYPERCUBE, seed=8,
                                 num_slices=18)
        assert res.by_method["bishop_simplified"].statistics.n == 60
        assert len(res.variables) == 2

    def test_seismic_variable_lowers_the_mean(self):
        from ogr_core.statistics import VariableKind as VK
        p = _ej1_project()
        det = _deterministic(p)
        v = [x for x in available_variables(p)
             if x.kind == VK.SEISMIC and x.param == "kh"][0]
        v.distribution = Distribution(DT.UNIFORM, mean=0.1, rel_min=0.1,
                                      rel_max=0.1)
        res = run_global_minimum(p, det, [v], num_samples=40,
                                 sampling=SM.LATIN_HYPERCUBE, seed=1,
                                 num_slices=18)
        mres = res.by_method["bishop_simplified"]
        assert mres.mean_fos < mres.deterministic_fos


class TestErrorHandling:
    def test_no_random_variables(self):
        p = _ej1_project()
        res = run_global_minimum(p, _deterministic(p), [],
                                 num_samples=10)
        assert not res.ok
        assert "error" in res.notes

    def test_no_deterministic_result(self):
        p = _ej1_project()
        res = run_global_minimum(p, {}, [_cohesion_var(p)],
                                 num_samples=10)
        assert not res.ok
        assert "deterministic" in res.notes["error"].lower()

    def test_failed_samples_are_counted_not_hidden(self):
        """A distribution wide enough to make the surface unsolvable must
        be reported, because a large count means the ranges are
        unrealistic."""
        p = _ej1_project()
        det = _deterministic(p)
        mat = p.materials[0]
        v = [x for x in available_variables(p)
             if x.param == "unit_weight" and x.target_id == mat.id][0]
        v.distribution = Distribution(DT.UNIFORM, mean=20.0,
                                      rel_min=19.99, rel_max=200.0)
        res = run_global_minimum(p, det, [v], num_samples=30,
                                 sampling=SM.LATIN_HYPERCUBE, seed=1,
                                 num_slices=18)
        mres = res.by_method["bishop_simplified"]
        assert mres.statistics.n + mres.failed_samples == 30

    def test_progress_callback(self):
        p = _ej1_project()
        det = _deterministic(p)
        seen = []
        run_global_minimum(p, det, [_cohesion_var(p)], num_samples=60,
                           sampling=SM.LATIN_HYPERCUBE, seed=1,
                           num_slices=18,
                           progress_cb=lambda d, t: seen.append((d, t)))
        assert seen and seen[-1][0] == seen[-1][1]


class TestConvergenceData:
    def test_convergence_ends_at_full_sample(self):
        p = _ej1_project()
        det = _deterministic(p)
        res = run_global_minimum(p, det, [_cohesion_var(p)],
                                 num_samples=100,
                                 sampling=SM.LATIN_HYPERCUBE, seed=2,
                                 num_slices=18)
        st = res.by_method["bishop_simplified"].statistics
        conv = st.convergence(steps=10)
        assert conv[-1][0] == st.n
        assert abs(conv[-1][1] - st.mean) < 1e-9
        assert abs(conv[-1][2] - st.probability_of_failure()) < 1e-9

    def test_histogram_totals(self):
        p = _ej1_project()
        det = _deterministic(p)
        res = run_global_minimum(p, det, [_cohesion_var(p)],
                                 num_samples=80,
                                 sampling=SM.LATIN_HYPERCUBE, seed=3,
                                 num_slices=18)
        st = res.by_method["bishop_simplified"].statistics
        assert sum(c for _x, c in st.histogram(bins=12)) == st.n

    def test_summary_fields(self):
        p = _ej1_project()
        det = _deterministic(p)
        res = run_global_minimum(p, det, [_cohesion_var(p)],
                                 num_samples=40,
                                 sampling=SM.LATIN_HYPERCUBE, seed=4,
                                 num_slices=18)
        s = res.summary()[0]
        for key in ("method", "deterministic_fos", "samples", "mean_fos",
                    "std_dev", "pf", "reliability_index",
                    "failed_samples"):
            assert key in s
        assert math.isfinite(s["mean_fos"])

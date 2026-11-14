# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D416 (v0.1.453) — one rule answers «is this variable random?», and the run
says what it leaves out.

The invariants
--------------
**One rule.** Two rules answered the same question. The run's,
``Distribution.not_random_reason`` (which ``is_random`` reads, and through it
the sampling of both probabilistic analyses and the dialog's Plot button),
asked a standard deviation only of the normal and the lognormal. The agent's,
``variable_problems``, asked it of the beta and the gamma too, and refused
them without one. So a beta or a gamma with no deviation was random for the
run and unusable for the agent. By the owner's decision (option A) the
agent's rule rules: the four distributions of ``USES_STD_DEV`` need a
deviation, and the agent and the run ask the same predicates of the core
(``lacks_std_dev``, ``has_range`` and ``lacks_positive_mean``), so they
cannot part again.

The empty range has one threshold too, the run's (``EMPTY_RANGE`` = 1e-15),
by the owner's decision: the agent asked ``high - low > 0`` and accepted a
range of 5e-16 the run left out, and the sensitivity analysis kept its own
copy of the 1e-15.

The review of 0.1.453 found two more ways a variable the rule called random
did not vary, and by the owner's decision they entered this version:

* a lognormal, a gamma or an exponential (``POSITIVE_ONLY``) whose mean is
  not positive: the core clamps the mean to 1e-12, so a kh, a kv or a
  water-table offset (mean 0 by design) drew values of 1e-33 to 6e-12, and a
  mean of −5 drew −5 every time;
* a deviation that is not a finite number, which a project file can carry:
  a NaN one sampled NaN.

A variable with no distribution is NOT a refusal of the agent: that is how
an agent switches one off (D413). The identity below holds for the three
reasons a variable can be refused for.

**The run says what it leaves out** (the review of 0.1.453, the owner's
decision). Both analyses sample only what ``is_random`` calls random, and
left the rest out without a word. Measured with v0.1.452 on the demo slope:
a normal cohesion without a deviation next to a normal friction angle left
no note, and alone it stopped the run with ``stat.no_variables``, which says
no parameter was given "a statistical distribution", false for a normal that
has one. Now a warning names each variable left out by the core's reason, in
the core's order; with none left an error says why; and a correlation whose
partner is not sampled, which the sampler skips, is said too. A variable
with no distribution is left out without a warning when others are sampled:
it is how one is switched off (D413), and the Statistics window shows the
warnings as what the run could not do (the owner's decision, the second
review). Global Minimum and Overall Slope ask one function
(``_sampled_variables``).

A NaN that only a hand-edited file can carry: a range or a mean that is not
a number is an empty range now (0.1.452 sampled NaN), and a NaN correlation
is still applied as 0.1.452 applied it, bit for bit (the sampler's old test
kept to the letter; the second review found that the first draft reordered
it differently).

The reference (rule 1)
----------------------
Identities of the distributions: a beta or a gamma parameterised by its mean
and standard deviation has variance σ², so with σ = 0 it is the point mass
at its mean (degenerate); a distribution of positive values only has a
positive mean, so with a mean that is not positive it is not the
distribution asked for. The core drew them as it did only through its
guards (``Distribution._frozen``): the beta's deviation clamped to 1e-12,
the gamma's scale clamped to 1e-12 (which leaves it a deviation of 3.9e-6 at
a mean of 15; the review of 0.1.453 measured it), and the mean of the three
positive ones clamped to 1e-12 (the exponential's in ``cdf`` and ``ppf``).

Measured with v0.1.452 (``_V1452`` and ``_V1452_MEAN``, 200 Latin Hypercube
samples with seed 1). The test draws them again with the rule of 0.1.452
substituted in the same process, or (the beta and the gamma) with a
deviation of 1e-12, which goes through the same guards: the same numbers,
so each measurement is the code's and not a copy.

Consequences, said by the core's docstring, and proved here against the
rule of 0.1.452 substituted in the same process:

* leaving such a variable out changes, with the same seed, the samples of
  the variables after it (``sample_variables`` spends one stream of the
  generator per variable), and the variable behind is sampled as if the
  other were not there; with a deviation nothing moves, bit for bit;
* a variable correlated with it keeps its values and loses its order: it is
  no longer rank-reordered against what was a constant with noise in the
  last digits.

No QApplication (the dialog's module is imported for its list and its
reasons). Measured: about 2 s for the file in the runner, most of it the
first imports of the API workspace and of the dialog's module.
"""
from __future__ import annotations

import atexit
import contextlib
import math

#: measured with v0.1.452 (2889daa), not by this code: min and max of 200
#: LHS samples, seed 1, mean 15, range ±3, deviation 0
_V1452 = {"beta": (15.000000, 15.000000), "gamma": (14.999988, 15.000011)}

#: measured with v0.1.452 (2889daa), not by this code: 200 LHS samples, seed
#: 1, of a distribution of positive values only with a mean that is not
#: positive — (type, mean, std, range ±, min, max, distinct values)
_V1452_MEAN = [
    ("exponential", 0.0, 0.0, 0.1, 6.72e-16, 5.99e-12, 200),
    ("lognormal", 0.0, 0.05, 0.1, 3.36e-33, 7.21e-15, 200),
    ("lognormal", -5.0, 1.0, 2.0, -5.0, -5.0, 1),
    ("gamma", -5.0, 1.0, 2.0, -5.0, -5.0, 1),
    ("exponential", -5.0, 0.0, 2.0, -5.0, -5.0, 1),
]


def _dist(t, std=0.0, lo=3.0, hi=3.0, mean=15.0):
    from ogr_core.statistics.distributions import Distribution
    return Distribution(dist_type=t, mean=mean, std_dev=std, rel_min=lo,
                        rel_max=hi)


def _rv(d, name="k", **kw):
    """A variable on an imaginary material, keyed by ``name``."""
    from ogr_core.statistics import RandomVariable
    return RandomVariable(target_id=name, param="cohesion", distribution=d,
                          **kw)


def _std_message(problems) -> bool:
    return any("needs a positive std_dev" in p for p in problems)


def _range_message(problems) -> bool:
    return any("zero range is not random" in p for p in problems)


def _mean_message(problems) -> bool:
    return any("takes only positive values" in p for p in problems)


def _randomness_refused(problems) -> bool:
    return (_std_message(problems) or _range_message(problems)
            or _mean_message(problems))


def _old_reason(self) -> str:
    """``not_random_reason`` of v0.1.452, written out for the control."""
    from ogr_core.statistics.distributions import DistributionType as T
    if self.dist_type == T.NONE:
        return "none"
    if self.high - self.low <= 1e-15:
        return "no_range"
    if self.dist_type in (T.NORMAL, T.LOGNORMAL) and self.std_dev <= 0:
        return "no_std_dev"
    return ""


@contextlib.contextmanager
def _rule_of_0452():
    from ogr_core.statistics.distributions import Distribution
    saved = Distribution.__dict__["not_random_reason"]
    Distribution.not_random_reason = _old_reason
    try:
        yield
    finally:
        Distribution.not_random_reason = saved


def _draw(d, n=200):
    from ogr_core.statistics.distributions import (SamplingMethod,
                                                   sample_variables)
    return sample_variables({"k": d}, n, SamplingMethod.LATIN_HYPERCUBE,
                            seed=1)["k"]


def _flat(note) -> list:
    """``(code, args)`` of a note and of every message nested in it, in
    order (a joined warning holds several)."""
    from ogr_core.messages import is_nested, parts
    code, args, _text = parts(note)
    out = [(code, args)]

    def walk(v):
        if isinstance(v, dict) and is_nested(v):
            out.append((v["code"], v["args"]))
            for x in v["args"].values():
                walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)

    for v in args.values():
        walk(v)
    return out


def _codes(note) -> list:
    return [c for c, _a in _flat(note)]


# ======================================================================
class TestOneRule:

    @staticmethod
    def _cases():
        from ogr_core.statistics.distributions import DistributionType as T
        for t in T:
            for mean in (10.0, 0.0, -5.0):
                for std in (-1.0, 0.0, 1.0, math.nan, math.inf):
                    for lo, hi in ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)):
                        yield (t, mean, std, lo, hi,
                               _dist(t, std, lo, hi, mean=mean))

    def test_the_agent_refuses_what_the_run_would_not_sample(self):
        """Every distribution, mean 10, 0 and −5, deviation −1, 0, 1, NaN
        and ∞, empty and non-empty ranges: the agent refuses for randomness
        if and only if the run would not sample the variable (``none``
        aside: it is accepted). Behaviour only, in names both versions
        have."""
        from ogr_core.statistics.random_variables import variable_problems
        seen = set()
        for t, mean, std, lo, hi, d in self._cases():
            bad = variable_problems(_rv(d), [])
            why = d.not_random_reason()
            case = (t, mean, std, lo, hi, why, bad)
            assert _randomness_refused(bad) == (
                why in ("no_range", "no_std_dev", "no_positive_mean")), case
            assert d.is_random == (not why), case
            seen.add(why)
        assert seen == {"", "none", "no_range", "no_std_dev",
                        "no_positive_mean"}, seen

    def test_each_message_is_one_predicate_of_the_core(self):
        from ogr_core.statistics.distributions import DistributionType as T
        from ogr_core.statistics.random_variables import variable_problems
        for t, mean, std, lo, hi, d in self._cases():
            bad = variable_problems(_rv(d), [])
            case = (t, mean, std, lo, hi, bad)
            assert _std_message(bad) == d.lacks_std_dev, case
            assert _range_message(bad) == (
                t is not T.NONE and not d.has_range), case
            assert _mean_message(bad) == d.lacks_positive_mean, case
            assert d.not_random_reason() == (
                "none" if t is T.NONE else "no_range" if not d.has_range
                else "no_std_dev" if d.lacks_std_dev
                else "no_positive_mean" if d.lacks_positive_mean
                else ""), case

    def test_every_message_when_every_condition_fails(self):
        """The agent's ``details.problems`` keeps listing each reason in its
        order, though the core's reason names only the first."""
        from ogr_core.statistics.distributions import DistributionType as T
        from ogr_core.statistics.random_variables import variable_problems
        std_msg = ("A {} distribution needs a positive std_dev; with none "
                   "the variable is not random.")
        range_msg = ("rel_min + rel_max must be positive: a zero range is not "
                     "random.")
        for t in (T.NORMAL, T.BETA, T.GAMMA):
            d = _dist(t, 0.0, 0.0, 0.0)
            bad = variable_problems(_rv(d), [])
            assert d.not_random_reason() == "no_range", t
            assert bad == [std_msg.format(t.value), range_msg], bad
        d = _dist(T.LOGNORMAL, 0.0, 0.0, 0.0, mean=0.0)
        assert variable_problems(_rv(d), []) == [
            std_msg.format("lognormal"), range_msg,
            "A lognormal distribution takes only positive values; with a "
            "mean of 0 the variable is not random."]

    def test_the_two_lists(self):
        from ogr_core.statistics.distributions import (POSITIVE_ONLY,
                                                       USES_STD_DEV,
                                                       DistributionType as T)
        assert USES_STD_DEV == {T.NORMAL, T.LOGNORMAL, T.BETA, T.GAMMA}
        assert POSITIVE_ONLY == {T.LOGNORMAL, T.GAMMA, T.EXPONENTIAL}


# ======================================================================
class TestThePointMass:

    def test_the_measurement_is_the_cores_clamp(self):
        """The numbers of 0.1.452, drawn again through the guards the core
        applied to a deviation of 0: it still samples one of 1e-12."""
        from ogr_core.statistics.distributions import DistributionType as T
        for t in (T.BETA, T.GAMMA):
            d = _dist(t, std=1e-12)
            assert d.is_random, t
            xs = _draw(d)
            got = (round(min(xs), 6), round(max(xs), 6))
            assert got == _V1452[t.value], (t, got)
            assert max(abs(x - 15.0) for x in xs) < 2e-5, t

    def test_without_a_deviation_they_are_not_random(self):
        from ogr_core.statistics.distributions import DistributionType as T
        for t in (T.BETA, T.GAMMA):
            d = _dist(t)
            assert d.not_random_reason() == "no_std_dev", t
            assert not d.is_random, t
            assert _draw(d, 50) == [15.0] * 50, t
            # and the 0.1.452 rule called them random: the defect
            with _rule_of_0452():
                assert d.is_random, t

    def test_a_mean_that_is_not_positive(self):
        """The measurement of 0.1.452 under its rule, and no sampling now."""
        from ogr_core.statistics.distributions import DistributionType as T
        for name, mean, std, half, lo, hi, distinct in _V1452_MEAN:
            d = _dist(T(name), std, half, half, mean=mean)
            with _rule_of_0452():
                assert d.is_random, name
                xs = _draw(d)
            case = (name, mean, min(xs), max(xs))
            assert math.isclose(min(xs), lo, rel_tol=5e-3), case
            assert math.isclose(max(xs), hi, rel_tol=5e-3), case
            assert len(set(xs)) == distinct, case
            assert d.not_random_reason() == "no_positive_mean", name
            assert _draw(d, 20) == [mean] * 20, name

    def test_a_range_or_a_mean_that_is_not_a_number(self):
        """0.1.452 sampled NaN; it is an empty range now (the second
        review)."""
        from ogr_core.statistics.distributions import DistributionType as T
        for lo, mean in ((math.nan, 15.0), (3.0, math.nan)):
            d = _dist(T.NORMAL, std=1.0, lo=lo, mean=mean)
            with _rule_of_0452():
                assert d.is_random, (lo, mean)
                assert all(math.isnan(x) for x in _draw(d, 4)), (lo, mean)
            assert d.not_random_reason() == "no_range", (lo, mean)

    def test_a_deviation_that_is_not_a_finite_number(self):
        """Measured with v0.1.452, 20 samples: a NaN deviation sampled NaN
        in the four; an infinite one the mean every time (normal, gamma),
        NaN (lognormal) or only the two ends, 12 and 18 (beta)."""
        from ogr_core.statistics.distributions import DistributionType as T
        infinite = {T.NORMAL: {15.0}, T.GAMMA: {15.0}, T.BETA: {12.0, 18.0}}
        for t in (T.NORMAL, T.LOGNORMAL, T.BETA, T.GAMMA):
            for std in (math.nan, math.inf):
                d = _dist(t, std=std)
                with _rule_of_0452():
                    assert d.is_random, (t, std)
                    xs = _draw(d, 20)
                if math.isnan(std) or t is T.LOGNORMAL:
                    assert all(math.isnan(x) for x in xs), (t, std, xs)
                else:
                    assert set(xs) == infinite[t], (t, std, set(xs))
                assert d.not_random_reason() == "no_std_dev", (t, std)
                assert _draw(d, 20) == [15.0] * 20, (t, std)


# ======================================================================
class TestTheSamples:

    def test_the_samples_of_the_others(self):
        """With a deviation nothing moves, bit for bit against the rule of
        0.1.452; without one, the variable behind is sampled as if the
        non-random one were not there."""
        from ogr_core.statistics.distributions import (DistributionType as T,
                                                       SamplingMethod)
        from ogr_core.statistics.random_variables import (
            sample_project_variables)
        lhs = SamplingMethod.LATIN_HYPERCUBE
        normal = _rv(_dist(T.NORMAL, std=1.5), "n")

        def draw(*rvs):
            return sample_project_variables(list(rvs), 40, lhs, 7)

        n = normal.key
        with_std = _rv(_dist(T.BETA, std=1.0), "b")
        b = with_std.key
        now = draw(with_std, normal)
        with _rule_of_0452():
            then = draw(with_std, normal)
        assert [v.hex() for v in now[n]] == [v.hex() for v in then[n]]
        assert [v.hex() for v in now[b]] == [v.hex() for v in then[b]]

        without = _rv(_dist(T.BETA), "b")
        now = draw(without, normal)
        assert set(now) == {n}, set(now)
        alone = draw(normal)
        assert [v.hex() for v in now[n]] == [v.hex() for v in alone[n]]
        with _rule_of_0452():
            then = draw(without, normal)
        assert set(then) == {b, n}
        assert then[n] != now[n]            # the stream it spent, given back

    def test_a_partner_without_deviation_reorders_nothing(self):
        """A variable correlated with a beta without deviation keeps its
        values and loses the order the rank reordering gave it against the
        noise of a constant (the review of 0.1.453)."""
        from ogr_core.statistics.distributions import (DistributionType as T,
                                                       SamplingMethod)
        from ogr_core.statistics.random_variables import (
            sample_project_variables)
        beta = _rv(_dist(T.BETA), "b")
        normal = _rv(_dist(T.NORMAL, std=1.5), "n",
                     correlated_with=beta.key, correlation=0.8)
        lhs = SamplingMethod.LATIN_HYPERCUBE
        now = sample_project_variables([normal, beta], 20, lhs, 7)
        alone = sample_project_variables(
            [_rv(_dist(T.NORMAL, std=1.5), "n")], 20, lhs, 7)
        with _rule_of_0452():
            then = sample_project_variables([normal, beta], 20, lhs, 7)
        n = normal.key
        assert set(now) == {n}, set(now)
        assert [v.hex() for v in now[n]] == [v.hex() for v in alone[n]]
        assert sorted(now[n]) == sorted(then[n])
        assert now[n] != then[n]


# ======================================================================
def _demo_variables():
    """The demo slope's cohesion and friction angle, as variables."""
    from ogr_core.project.demo import build_demo_project
    from ogr_core.statistics import available_variables
    p = build_demo_project()
    av = available_variables(p)
    c = next(v for v in av if v.param == "cohesion")
    f = next(v for v in av if v.param == "friction_angle")
    return p, c, f


class TestTheRunSaysWhatItLeavesOut:

    def test_none_random_stops_both_analyses_with_the_reason(self):
        from ogr_core.statistics.distributions import DistributionType as T
        from ogr_slip2d import stat_messages as SM
        from ogr_slip2d.probabilistic import (run_global_minimum,
                                              run_overall_slope)
        p, c, _f = _demo_variables()
        c.distribution = _dist(T.BETA, mean=c.distribution.mean)
        gm = run_global_minimum(p, {}, [c], num_samples=10)
        os_ = run_overall_slope(p, lambda mid: None, [c], ["bishop_simplified"],
                                num_samples=10)
        for res in (gm, os_):
            flat = _flat(res.notes["error"])
            assert [code for code, _a in flat] == [
                SM.VARS_NOT_RANDOM_ONLY, SM.NOT_RANDOM_STD], flat
            assert flat[1][1] == {"keys": c.key}, flat
            assert not res.samples, res.samples
        assert str(gm.notes["error"]) == str(os_.notes["error"])

    def test_no_variable_at_all_is_still_no_variables(self):
        from ogr_slip2d import stat_messages as SM
        from ogr_slip2d.probabilistic import run_global_minimum
        p, _c, _f = _demo_variables()
        res = run_global_minimum(p, {}, [], num_samples=10)
        assert res.notes["error"].code == SM.NO_VARIABLES

    def test_the_ones_left_out_by_reason_in_the_cores_order(self):
        """Four left out, one per reason, given in another order; a normal
        friction angle is sampled. One warning, the reasons in the core's
        order, the same from both analyses; the variable switched off
        («none») is left out without being named (the owner's decision)."""
        from ogr_core.statistics import available_variables
        from ogr_core.statistics.distributions import DistributionType as T
        from ogr_slip2d import stat_messages as SM
        from ogr_slip2d.probabilistic import (run_global_minimum,
                                              run_overall_slope)
        p, c, f = _demo_variables()
        av = {v.key: v for v in available_variables(p)}
        kh = av["seismic::kh"]
        kv = av["seismic::kv"]
        w = next(v for v in av.values() if v.param == "unit_weight")
        f.distribution = _dist(T.NORMAL, 2.0, 5.0, 5.0,
                               mean=f.distribution.mean)
        kh.distribution = _dist(T.LOGNORMAL, 0.05, 0.1, 0.1, mean=0.0)
        c.distribution = _dist(T.GAMMA, mean=c.distribution.mean)
        w.distribution = _dist(T.NORMAL, 1.0, 0.0, 0.0,
                               mean=w.distribution.mean)
        kv.distribution = _dist(T.NONE, mean=0.0)
        variables = [kh, f, c, w, kv]
        gm = run_global_minimum(p, {}, variables, num_samples=10)
        os_ = run_overall_slope(p, lambda mid: None, variables, [],
                                num_samples=10)
        for res in (gm, os_):
            flat = _flat(res.notes["warning"])
            head = next(i for i, (code, _a) in enumerate(flat)
                        if code == SM.VARS_NOT_RANDOM)
            assert flat[head][1]["n"] == 3 and flat[head][1]["total"] == 5
            assert flat[head + 1:head + 4] == [
                (SM.NOT_RANDOM_RANGE, {"keys": w.key}),
                (SM.NOT_RANDOM_STD, {"keys": c.key}),
                (SM.NOT_RANDOM_MEAN, {"keys": kh.key})], flat
            assert SM.NOT_RANDOM_NONE not in _codes(res.notes["warning"])
            assert all(kv.key not in line for line in res.note_lines)
        assert gm.note_lines[0] == os_.note_lines[0]

    def test_switched_off_is_said_only_when_nothing_is_left(self):
        """A variable with no distribution, next to a random one, leaves no
        note; alone, the error names it, since then nothing is computed."""
        from ogr_core.statistics.distributions import DistributionType as T
        from ogr_slip2d import stat_messages as SM
        from ogr_slip2d.probabilistic import run_global_minimum
        p, c, f = _demo_variables()
        c.distribution = _dist(T.NONE, mean=c.distribution.mean)
        f.distribution = _dist(T.NORMAL, 2.0, 5.0, 5.0,
                               mean=f.distribution.mean)
        res = run_global_minimum(p, {}, [c, f], num_samples=10)
        assert "warning" not in res.notes, res.notes
        res = run_global_minimum(p, {}, [c], num_samples=10)
        assert _flat(res.notes["error"]) == [
            (SM.VARS_NOT_RANDOM_ONLY, res.notes["error"].args),
            (SM.NOT_RANDOM_NONE, {"keys": c.key})], res.notes

    def test_a_correlation_that_is_not_applied(self):
        """With its partner not random, or not defined, the correlation is
        said; with a random partner, not."""
        from ogr_core.statistics.distributions import DistributionType as T
        from ogr_slip2d import stat_messages as SM
        from ogr_slip2d.probabilistic import run_global_minimum
        p, c, f = _demo_variables()
        f.distribution = _dist(T.NORMAL, 2.0, 5.0, 5.0,
                               mean=f.distribution.mean)
        f.correlated_with, f.correlation = c.key, 0.5
        for partner, said in (
                (_dist(T.BETA, mean=c.distribution.mean), True),
                (_dist(T.BETA, 1.0, mean=c.distribution.mean), False)):
            c.distribution = partner
            res = run_global_minimum(p, {}, [c, f], num_samples=10)
            notes = [a for code, a in _flat(res.notes.get("warning", ""))
                     if code == SM.CORRELATION_NOT_APPLIED]
            assert notes == ([{"key": f.key, "other": c.key}] if said
                             else []), (partner, res.notes)
        # a partner that is not defined at all
        res = run_global_minimum(p, {}, [f], num_samples=10)
        notes = [a for code, a in _flat(res.notes.get("warning", ""))
                 if code == SM.CORRELATION_NOT_APPLIED]
        assert notes == [{"key": f.key, "other": c.key}], res.notes

    def test_the_rule_is_the_samplers(self):
        """``unapplied_correlations`` names exactly the pairs the sampler
        declares and does not reorder, measured by running the sampler: a
        pair is reordered when its samples differ from the same variable
        drawn without the correlation (the second review: the first test
        never ran the sampler). A correlation below 1e-12 is none at all, a
        variable that is not random declares nothing it is sampled for, and
        a NaN correlation is applied as 0.1.452 applied it."""
        from ogr_core.statistics.distributions import (DistributionType as T,
                                                       SamplingMethod)
        from ogr_core.statistics.random_variables import (
            sample_project_variables, unapplied_correlations)
        lhs = SamplingMethod.LATIN_HYPERCUBE
        random_b = _rv(_dist(T.BETA, std=1.0), "b")
        fixed_b = _rv(_dist(T.BETA), "b")
        cases = []
        for partner in (random_b, fixed_b):
            for corr in (0.5, 1e-13, 0.0, math.nan):
                cases.append((partner, corr))
        for partner, corr in cases:
            normal = _rv(_dist(T.NORMAL, std=1.5), "n",
                         correlated_with=partner.key, correlation=corr)
            plain = _rv(_dist(T.NORMAL, std=1.5), "n")
            now = sample_project_variables([partner, normal], 20, lhs, 7)
            base = sample_project_variables([partner, plain], 20, lhs, 7)
            reordered = now[normal.key] != base[normal.key]
            declared = corr == corr and abs(corr) >= 1e-12 or corr != corr
            unapplied = unapplied_correlations([partner, normal])
            case = (partner.distribution.std_dev, corr, reordered, unapplied)
            assert bool(unapplied) == (declared and not reordered), case
            assert reordered == (declared and partner is random_b), case
            with _rule_of_0452():
                then = sample_project_variables([partner, normal], 20, lhs,
                                                7)
            if partner is random_b:         # nothing moves for random pairs
                assert ([v.hex() for v in now[normal.key]]
                        == [v.hex() for v in then[normal.key]]), case
        # a variable that is not random and declares a correlation: it is
        # not sampled, so there is nothing of it to apply or to say
        # not even with a partner that is not sampled either
        for partner in (random_b, fixed_b):
            off = _rv(_dist(T.BETA), "o", correlated_with=partner.key,
                      correlation=0.5)
            assert unapplied_correlations([partner, off]) == [], partner

    def test_said_in_spanish(self):
        from ogr_core.statistics.distributions import DistributionType as T
        from ogr_gui.core_messages import note_text
        from ogr_gui.i18n import current_language, set_language
        from ogr_slip2d.probabilistic import run_global_minimum
        p, c, f = _demo_variables()
        f.distribution = _dist(T.NORMAL, 2.0, 5.0, 5.0,
                               mean=f.distribution.mean)
        f.correlated_with, f.correlation = c.key, 0.5
        c.distribution = _dist(T.BETA, mean=c.distribution.mean)
        res = run_global_minimum(p, {}, [c, f], num_samples=10)
        before = current_language()
        try:
            set_language("es")
            said = [note_text(line) for line in res.note_lines]
        finally:
            set_language(before)
        assert said[0].startswith(
            "1 de las 2 variables aleatorias no se pueden muestrear y se han "
            "dejado fuera: sin desviación típica ("), said
        assert said[0].endswith(")"), said
        assert said[1].startswith("La correlación de "), said
        assert "no se muestrea." in said[1], said


# ======================================================================
class TestTheRange:

    def test_the_threshold_is_the_runs(self):
        from ogr_core.statistics.distributions import (EMPTY_RANGE,
                                                       DistributionType as T)
        assert EMPTY_RANGE == 1e-15
        # the threshold itself is empty, as the run's «<= 1e-15» always had it
        for rel_min, random in ((5e-16, False), (1e-15, False),
                                (2e-15, True)):
            d = _dist(T.NORMAL, std=1.0, lo=rel_min, hi=0.0, mean=0.0)
            assert d.has_range == random, rel_min

    def test_one_threshold_for_the_run_the_agent_and_the_sensitivity(self):
        """Mean 0 (a kh, a kv): a range of 5e-16 is empty for all three, and
        one of 2e-15 for none. Behaviour only."""
        from ogr_core.project.demo import build_demo_project
        from ogr_core.statistics.distributions import DistributionType as T
        from ogr_core.statistics.random_variables import variable_problems
        from ogr_slip2d import stat_messages as SM
        from ogr_slip2d.sensitivity import run_sensitivity
        p = build_demo_project()
        for rel_min, random in ((5e-16, False), (1e-15, False),
                                (2e-15, True)):
            d = _dist(T.NORMAL, std=1.0, lo=rel_min, hi=0.0, mean=0.0)
            assert d.not_random_reason() == ("" if random else "no_range")
            assert _range_message(variable_problems(_rv(d), [])) == (
                not random), rel_min
            res = run_sensitivity(p, {}, [_rv(d)])
            stopped = getattr(res.notes.get("error"), "code", None)
            if random:
                assert stopped != SM.NO_RANGE, res.notes
            else:
                assert stopped == SM.NO_RANGE, res.notes


# ======================================================================
_WS: list = []


def _ws():
    if not _WS:
        from ogr_api import Workspace
        ws = Workspace()
        atexit.register(ws.shutdown)
        _WS.append(ws)
    return _WS[0]


def _slope(ws):
    from ogr_api import call
    pid = call(ws, "project_new", name="D416")["project_id"]
    call(ws, "model_define", project_id=pid, spec={
        "external": [[0, 0], [60, 0], [60, 20], [40, 20], [20, 10],
                     [0, 10]],
        "materials": [{"name": "Soil", "unit_weight": 19, "strength": {
            "model": "mohr_coulomb",
            "params": {"cohesion": 6.0, "friction_angle": 22.0}}}]})
    avail = call(ws, "random_variable_list", project_id=pid)["available"]
    key = next(v["key"] for v in avail if v["key"].endswith(":cohesion"))
    return pid, key


class TestTheAgent:

    def test_refused_and_listed_as_the_run_reads_them(self):
        from ogr_api import InvalidArgument, call
        from ogr_core.statistics import RandomVariable
        ws = _ws()
        pid, key = _slope(ws)
        for name, kw, said in (
                ("beta", {"std_dev": 0.0}, _std_message),
                ("gamma", {"std_dev": 0.0}, _std_message),
                # a kh: mean 0, the default dispersion
                ("lognormal", {"key": "seismic::kh"}, _mean_message),
                ("exponential", {"key": "seismic::kh"}, _mean_message)):
            args = {"key": key, **kw}
            try:
                call(ws, "random_variable_set", project_id=pid,
                     distribution=name, **args)
            except InvalidArgument as exc:
                assert said(exc.details["problems"]), exc.details
            else:
                raise AssertionError(f"a {name} {kw} stored")
        # one that arrives by a file, past the agent's rule
        call(ws, "random_variable_set", project_id=pid, key=key,
             distribution="beta", std_dev=0.5)
        project = ws.get(pid).project
        rv = RandomVariable.from_dict(project.random_variables[0].to_dict())
        rv.distribution.std_dev = 0.0
        project.random_variables = [rv]
        listed = call(ws, "random_variable_list", project_id=pid)
        assert [v["is_random"] for v in listed["defined"]] == [False], listed

    def test_the_std_dev_note_says_the_same_four(self):
        """A control: the agent's note was right already, written by hand
        as the complement of the four."""
        from ogr_api import call
        from ogr_core.statistics.distributions import DistributionType as T
        ws = _ws()
        pid, key = _slope(ws)
        four = {T.NORMAL, T.LOGNORMAL, T.BETA, T.GAMMA}
        for t in T:
            out = call(ws, "random_variable_set", project_id=pid, key=key,
                       distribution=t.value, std_dev=0.5, rel_min=1.0,
                       rel_max=1.0)
            said = any("std_dev is not read" in n for n in out["notes"])
            assert said == (t not in four), (t, out["notes"])

    def test_the_dialog_and_the_agent_ask_the_cores_list(self):
        """One list: the dialog's field and the agent's note read it, so a
        fifth distribution with a deviation is added once. The agent's by
        what it says with the core's list changed in memory (the first
        version read the source text, which an own tuple next to the import
        would have passed: the review of 0.1.453)."""
        from ogr_api import call
        import ogr_core.statistics.distributions as DI
        from ogr_core.statistics.distributions import USES_STD_DEV
        ws = _ws()
        pid, key = _slope(ws)
        saved = DI.USES_STD_DEV
        DI.USES_STD_DEV = saved - {DI.DistributionType.BETA}
        try:
            out = call(ws, "random_variable_set", project_id=pid, key=key,
                       distribution="beta", std_dev=0.5)
        finally:
            DI.USES_STD_DEV = saved
        assert any("std_dev is not read by a beta" in n
                   for n in out["notes"]), out["notes"]
        import importlib.util
        if importlib.util.find_spec("PySide6") is None:
            return                          # no PySide6: no dialog to ask
        from ogr_gui.dialogs import random_variables_dialog as dlg
        assert dlg._USES_STD is USES_STD_DEV

    def test_the_dialog_says_every_reason_of_the_core(self):
        """The Plot button's reason for each reason the core gives, in
        Spanish, never the code itself."""
        import importlib.util
        if importlib.util.find_spec("PySide6") is None:
            return                          # no PySide6: no dialog to ask
        # imported unguarded: a missing function is a failure, not a skip
        from ogr_gui.dialogs.random_variables_dialog import not_random_text
        from ogr_gui.i18n import current_language, set_language
        from ogr_slip2d.probabilistic import _NOT_RANDOM
        before = current_language()
        try:
            set_language("es")
            said = {why: not_random_text(why) for why in _NOT_RANDOM}
        finally:
            set_language(before)
        assert said["no_positive_mean"] == (
            "Esta distribución solo toma valores positivos, y la media no es "
            "positiva: elige otra distribución."), said
        assert said["no_std_dev"] == (
            "Esta distribución necesita una desviación típica mayor que "
            "cero."), said
        for why, text in said.items():
            assert text != why and text[0].isupper(), (why, text)

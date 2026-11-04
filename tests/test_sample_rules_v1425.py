# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.425 (D376) — a statistical run says how many of its samples break a
rule the run itself refuses.

WHAT INVARIANT THIS PROTECTS
----------------------------
``check_analysis_settings`` refuses what a run cannot compute as
configured: a negative kh, a strength model that cannot be computed with,
a drawdown line above the water table, and the rest. A statistical run
asks it once, of the model BEFORE sampling; every sample then writes its
own values on a clone, and nobody asked again. Measured with the compute
audit's probe S7 (0.1.377): the 028 model with a kh of mean zero and the
default dispersion (0.1 and +-0.3 absolute), 200 Monte Carlo samples, 99
with kh < 0, all evaluated, no note -- while a deterministic run with a
negative kh is refused.

The owner's decision (option C): say it, per rule, and change nothing. So
this file checks three things:

* the count is EXACT, against a count made independently of the code
  under test: the negative values of the kh column the run itself drew
  (Global Minimum, Overall Slope, and the points of the sweep), and, for a
  water-table variable on the Appendix G slope with the drawdown line
  8 ft below the water table, the offsets below -8 (both lines are flat,
  so that is exactly where the drawdown line ends up above the table);
* nothing moves: the same run with the check patched to nothing gives the
  same factors, bit for bit (A/B in the same process);
* what the model before sampling already breaks is not counted, and a run
  whose samples break nothing says nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_core.statistics import (  # noqa: E402
    Distribution,
    DistributionType as DT,
    SamplingMethod as SM,
    VariableKind as VK,
    available_variables,
)
from ogr_core.statistics.random_variables import (  # noqa: E402
    default_dispersion,
)
from ogr_slip2d import probabilistic as P  # noqa: E402
from ogr_slip2d.analysis_runner import build_method  # noqa: E402
from ogr_slip2d.probabilistic import (  # noqa: E402
    run_global_minimum,
    run_overall_slope,
)
from ogr_slip2d.search import GridSearch  # noqa: E402
from ogr_slip2d.sensitivity import run_sensitivity  # noqa: E402
from ogr_slip2d.surface import SlipCircle  # noqa: E402

_MID = "bishop_simplified"
_SLICES = 20
_CIRCLE = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)
_SAMPLES = "stat.samples_break_rules"
_POINTS = "stat.points_break_rules"


def _det(project, circle=_CIRCLE, slices=_SLICES):
    search = GridSearch(method=build_method(project, _MID, slices),
                        num_slices=slices, min_area=0.0)
    return {_MID: search.evaluate_circle(project, circle)}


def _kh(project):
    """kh as a random variable with the dialog's default dispersion: mean
    zero, so 0.1 and +-0.3 absolute (``default_dispersion``)."""
    v = [x for x in available_variables(project)
         if x.kind == VK.SEISMIC and x.param == "kh"][0]
    v.distribution = Distribution(DT.NORMAL, mean=0.0)
    return default_dispersion(v)


def _cohesion(project):
    mat = project.materials[0]
    v = [x for x in available_variables(project)
         if x.param == "cohesion" and x.target_id == mat.id][0]
    v.distribution = Distribution(
        DT.NORMAL, mean=mat.strength.params["cohesion"], std_dev=3.0,
        rel_min=9.0, rel_max=9.0)
    return v


def _line(result, code):
    """The run's line with ``code``, or None."""
    found = [x for x in result.note_lines
             if getattr(x, "code", None) == code]
    assert len(found) <= 1, found
    return found[0] if found else None


def _rules(line):
    """``{rule code: count}`` out of the warning's nested list."""
    return {r["args"]["rule"]["code"]: r["args"]["n"]
            for r in line.args["rules"]}


def _gm(project, variables, n=40, seed=11, det=None):
    return run_global_minimum(project, det or _det(project), variables,
                              num_samples=n, sampling=SM.MONTE_CARLO,
                              seed=seed, num_slices=_SLICES)


def _never(_mid):
    raise AssertionError("no search may run")


class _Spanish:
    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self._before = current_language()
        set_language("es")

    def __exit__(self, *_exc):
        from ogr_gui.i18n import set_language
        set_language(self._before)


_SHARED: dict = {}


def _kh_run():
    """One Global Minimum run with kh, shared by the cases that read it."""
    if "gm" not in _SHARED:
        p = _ej1_project()
        kh = _kh(p)
        _SHARED["gm"] = (p, kh, _gm(p, [kh]))
    return _SHARED["gm"]


# ======================================================================
class TestTheCountIsExact:

    def test_global_minimum(self):
        _p, kh, res = _kh_run()
        negative = sum(1 for v in res.samples[kh.key] if v < 0)
        assert 0 < negative < 40, negative       # the premise
        line = _line(res, _SAMPLES)
        assert line is not None, res.note_lines
        assert line.args["n"] == negative
        assert line.args["total"] == 40
        assert _rules(line) == {"rule.seismic_kh_negative": negative}
        # it is a warning: the run still answers
        assert res.ok and _SAMPLES in [getattr(x, "code", "") for x in
                                        res.note_lines]

    def test_overall_slope(self):
        """Counted before the search, so a factory that refuses to search
        loses every sample and the count is still there."""
        p = _ej1_project()
        kh = _kh(p)
        res = run_overall_slope(p, _never, [kh], [_MID], num_samples=12,
                                sampling=SM.MONTE_CARLO, seed=5)
        negative = sum(1 for v in res.samples[kh.key] if v < 0)
        assert negative > 0
        line = _line(res, _SAMPLES)
        assert line is not None and line.args["n"] == negative
        assert line.args["total"] == 12

    def test_the_points_of_the_sweep(self):
        """-0.3, -0.15, 0, 0.15 and 0.3: two of the five break the rule."""
        p = _ej1_project()
        kh = _kh(p)
        res = run_sensitivity(p, _det(p), [kh], intervals=4,
                              num_slices=_SLICES)
        line = _line(res, _POINTS)
        assert line is not None, res.note_lines
        assert (line.args["n"], line.args["total"]) == (2, 5)
        assert _rules(line) == {"rule.seismic_kh_negative": 2}

    def test_a_drawdown_line_above_the_water_table(self):
        """The route the card read and did not measure: a water-table
        offset takes the table below the drawdown line, which
        ``wrap_for_drawdown`` only checks when the method is built."""
        import test_drawdown_methods_v1108 as dd
        p = dd._appendix_g("corps_2", initial_y=103.0, final_y=95.0)
        wt = [x for x in available_variables(p)
              if x.kind == VK.WATER_TABLE][0]
        wt.distribution = Distribution(DT.NORMAL, mean=0.0, std_dev=10.0,
                                       rel_min=30.0, rel_max=30.0)
        det = _det(p, dd._circle(), 25)
        res = run_global_minimum(p, det, [wt], num_samples=20,
                                 sampling=SM.MONTE_CARLO, seed=3,
                                 num_slices=25)
        inverted = sum(1 for o in res.samples[wt.key] if 103.0 + o < 95.0)
        assert 0 < inverted < 20, inverted        # the premise
        line = _line(res, _SAMPLES)
        assert line is not None, res.note_lines
        assert line.args["n"] == inverted
        assert _rules(line) == {"setting.drawdown_line_above": inverted}


# ======================================================================
class TestNothingMoves:

    def test_the_factors_are_those_of_the_run_without_the_check(self):
        p, kh, new = _kh_run()
        saved = P._SampleRules.see
        P._SampleRules.see = lambda self, index, clone: None
        try:
            old = _gm(p, [kh])
        finally:
            P._SampleRules.see = saved
        assert _line(old, _SAMPLES) is None
        a = new.by_method[_MID].statistics.values
        b = old.by_method[_MID].statistics.values
        assert a and a == b
        assert new.by_method[_MID].sample_index == \
            old.by_method[_MID].sample_index

    def test_samples_that_break_nothing_say_nothing(self):
        p = _ej1_project()
        res = _gm(p, [_cohesion(p)], n=12)
        assert res.ok
        assert _line(res, _SAMPLES) is None

    def test_what_the_model_already_breaks_is_not_counted(self):
        """A caller that skipped the door hands over a model with a
        negative kh: that is the door's refusal, not the samples'."""
        p = _ej1_project()
        p.seismic.enabled = True
        p.seismic.kh = -0.05
        res = _gm(p, [_cohesion(p)], n=12)
        assert _line(res, _SAMPLES) is None


# ======================================================================
class TestItSaysItInSpanish:

    def test_the_warning(self):
        from ogr_gui.core_messages import note_text
        _p, _kh_v, res = _kh_run()
        with _Spanish():
            said = note_text(_line(res, _SAMPLES))
        assert "muestras incumplen una regla" in said, said
        assert "veces; la primera:" in said, said
        assert "kh" in said

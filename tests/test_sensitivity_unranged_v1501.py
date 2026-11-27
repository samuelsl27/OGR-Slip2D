# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.501 (D441) — the sensitivity analysis names the variables it leaves
out for want of a range, and sweeps a variable whose distribution is
'none' when it has one.

The invariants, on the demo slope (a 3×3 grid, Bishop, 4 intervals, through
``run_configured_statistics``), the bench's ``medir_d441.py``:

* **a variable without a range is named**: with the cohesion's range empty
  and the friction angle's ±5°, the run sweeps the friction angle and says,
  with ``stat.sens_no_range``, that it did not sweep the cohesion — in
  ``notes`` (the status bar) and in ``note_lines`` (the notes panel and the
  agent). Until this version the cohesion disappeared from the result and
  both were empty (measured with 0.1.485 and 0.1.500). Rule 7: the range
  moves the note — with a range for both, nothing is said;
* **'none' is swept** (the owner's decision A): the reference documents that
  a sensitivity analysis needs only the minimum and the maximum of each
  variable, and that the distribution does not apply to it; so the cohesion
  in 'none' with ±2 kPa is swept from 8 to 12 kPa, with no note, and the
  agent's guide no longer says that 'none' switches a variable off without
  qualification;
* **no factor moves**: the five factors of each swept variable are those of
  the sweep of the same variable with a range, bit for bit, whatever the
  other variable carries.

Cost: four sensitivity runs of 3×3 grids, about a tenth of a second each.
"""
from __future__ import annotations

_RUNS: dict = {}


def _run(cohesion, friction):
    """``(cohesion variable, friction variable, sensitivity result)`` with
    the cohesion ``"none"`` (±2, no distribution), ``"empty"`` (no range) or
    ``"ranged"`` (normal ±2), and the friction angle normal ±5."""
    key = (cohesion, friction)
    if key not in _RUNS:
        from ogr_core.project.demo import build_demo_project
        from ogr_core.statistics import available_variables
        from ogr_core.statistics.distributions import (Distribution,
                                                       DistributionType as T)
        from ogr_slip2d.analysis_runner import run_configured_statistics
        p = build_demo_project()
        s = p.settings.search
        s.grid_nx = s.grid_ny = 3
        p.settings.methods.enabled_methods = ["bishop_simplified"]
        av = {v.param: v for v in available_variables(p)
              if v.param in ("cohesion", "friction_angle")}
        c, f = av["cohesion"], av["friction_angle"]
        m = c.distribution.mean
        c.distribution = {
            "none": Distribution(T.NONE, m, 1.0, 2.0, 2.0),
            "empty": Distribution(T.NORMAL, m, 1.0, 0.0, 0.0),
            "ranged": Distribution(T.NORMAL, m, 1.0, 2.0, 2.0)}[cohesion]
        f.distribution = Distribution(T.NORMAL, f.distribution.mean, 2.0,
                                      5.0, 5.0)
        p.random_variables = [c, f] if friction else [c]
        st = p.settings.statistics
        st.sensitivity_analysis, st.probabilistic_analysis = True, False
        st.sensitivity_intervals = 4
        _RUNS[key] = (c, f, run_configured_statistics(p).sensitivity)
    return _RUNS[key]


def _codes(lines) -> list:
    from ogr_core.messages import parts
    return [parts(line)[0] for line in lines]


class TestAVariableWithoutARange:

    def test_it_is_named_with_its_code(self):
        from ogr_core.messages import parts
        c, f, sens = _run("empty", True)
        swept = set(sens.by_method["bishop_simplified"])
        assert swept == {f.key}
        lines = list(sens.note_lines)
        assert _codes(lines) == ["stat.sens_no_range"], lines
        _code, args, english = parts(lines[0])
        assert args["n"] == 1 and args["total"] == 2
        assert args["keys"] == c.key and c.key in str(english)
        assert "stat.sens_no_range" in _codes([sens.notes["warning"]])

    def test_with_a_range_for_both_nothing_is_said(self):
        """Rule 7: the range moves the note."""
        _c, _f, sens = _run("ranged", True)
        assert "stat.sens_no_range" not in _codes(sens.note_lines)
        assert len(sens.by_method["bishop_simplified"]) == 2


class TestNoneIsSwept:

    def test_it_is_swept_over_its_range_without_a_note(self):
        c, _f, sens = _run("none", True)
        sweep = sens.by_method["bishop_simplified"][c.key]
        assert [round(v, 9) for v in sweep.values] == [8.0, 9.0, 10.0, 11.0,
                                                        12.0]
        assert list(sens.note_lines) == []

    def test_the_agents_guide_says_so(self):
        from ogr_mcp.guide import GUIDE
        text = " ".join(GUIDE.split())
        assert "switches a variable off in the probabilistic runs" in text
        assert "stat.sens_no_range" in text


class TestNoFactorMoves:

    def test_the_friction_sweep_is_the_same_whatever_the_cohesion(self):
        ref = _run("ranged", True)
        sweeps = [r[2].by_method["bishop_simplified"][r[1].key].fos
                  for r in (ref, _run("empty", True), _run("none", True))]
        assert sweeps[0] == sweeps[1] == sweeps[2]

    def test_the_none_sweep_is_the_ranged_one(self):
        a = _run("none", True)
        b = _run("ranged", True)
        assert (a[2].by_method["bishop_simplified"][a[0].key].fos
                == b[2].by_method["bishop_simplified"][b[0].key].fos)

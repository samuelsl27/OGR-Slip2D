# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.423 (D372) — a HYDRAULIC random variable may not pass for one that
moves the factor of safety.

WHAT INVARIANT THIS PROTECTS
----------------------------
A hydraulic variable (``ks`` and the other parameters of
``material.hydraulic``) writes what only the seepage solver reads. The
limit-equilibrium methods take the pore pressure from the field the project
STORES, and no statistical run solves the seepage again for each sample.
So before this version every sample answered the same factor: measured with
the compute audit's probe S1 (0.1.377, Ej_1 with Gardner and the steady
finite-element field, Global Minimum with N = 20 on the reference circle),
``ks`` random gave ONE value in all 20 samples, 0.836185679621466, with no
failure and no note. A setting that does nothing (rule 7), which reads as
"the water does not matter".

What the owner decided (option A): say it and refuse.

* every active variable hydraulic: Global Minimum, Overall Slope and the
  sensitivity sweep stop before drawing, with ``stat.vars_hydraulic_only``
  under ``error`` and no ``by_method`` — no spread of zero published as a
  measurement;
* some of them hydraulic: a warning naming them (``stat.vars_hydraulic``),
  and the run goes on as before; the sweep does not sweep them and marks
  each with ``stat.var_hydraulic``, which the Statistics window names as
  hydraulic and NOT as "no longer in the model".

THIS IS NOT A SNAPSHOT TEST
---------------------------
No factor is pinned. The numbers are checked by two IDENTITIES, both
recomputed: a run with the cohesion and ``ks`` equals, value by value, the
run with the cohesion alone at the same seed (the hydraulic column reaches
nothing, and it is drawn AFTER the cohesion: ``sample_variables`` draws once
per key in insertion order, see ``test_random_variable_target_v1164``); and
the same mixed run with the new check patched to nothing equals the one
with it — the version moves no number.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_slide_validation_ej1 import _ej1_project  # noqa: E402

from ogr_core.statistics import (  # noqa: E402
    Distribution,
    DistributionType as DT,
    RandomVariable,
    SamplingMethod as SM,
    VariableKind as VK,
    available_variables,
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
#: The fixed circle of ``test_random_variable_target_v1164``: no search.
_CIRCLE = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)


def _project():
    """Ej_1 with hydraulic properties on every material, so ``ks`` is a
    variable the model offers (``available_variables``)."""
    from ogr_core.hydraulic import HydraulicProperties
    p = _ej1_project()
    for m in p.materials:
        m.hydraulic = HydraulicProperties(ks=1.0e-5)
    return p


def _det(project):
    search = GridSearch(method=build_method(project, _MID, _SLICES),
                        num_slices=_SLICES, min_area=0.0)
    return {_MID: search.evaluate_circle(project, _CIRCLE)}


def _cohesion(project):
    mat = project.materials[0]
    v = [x for x in available_variables(project)
         if x.param == "cohesion" and x.target_id == mat.id][0]
    v.distribution = Distribution(
        DT.NORMAL, mean=mat.strength.params["cohesion"], std_dev=3.0,
        rel_min=9.0, rel_max=9.0)
    return v


def _ks(project):
    mat = project.materials[0]
    found = [x for x in available_variables(project)
             if x.kind == VK.HYDRAULIC and x.param == "ks"
             and x.target_id == mat.id]
    # the premise: the model OFFERS it, which is why it has to be said
    assert found, "ks is not offered"
    v = found[0]
    v.distribution = Distribution(DT.NORMAL, mean=1.0e-5, std_dev=0.5e-5,
                                  rel_min=0.9e-5, rel_max=0.9e-5)
    return v


def _gm(project, variables, n=12, seed=3):
    return run_global_minimum(project, _det(project), variables,
                              num_samples=n, sampling=SM.LATIN_HYPERCUBE,
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


# ======================================================================
class TestAllHydraulicIsRefused:
    """Nothing that can move a factor is not a result of zero spread."""

    def test_global_minimum(self):
        p = _project()
        ks = _ks(p)
        res = _gm(p, [ks])
        assert not res.ok
        assert not res.by_method
        assert res.notes["error"].code == "stat.vars_hydraulic_only"
        assert ks.key in res.notes["error"]
        assert res.samples == {} or not res.samples

    def test_overall_slope_stops_before_searching(self):
        p = _project()
        ks = _ks(p)
        res = run_overall_slope(p, _never, [ks], [_MID], num_samples=4,
                                sampling=SM.MONTE_CARLO, seed=7)
        assert not res.ok
        assert res.notes["error"].code == "stat.vars_hydraulic_only"

    def test_the_sweep(self):
        p = _project()
        ks = _ks(p)
        res = run_sensitivity(p, _det(p), [ks], intervals=4,
                              num_slices=_SLICES)
        assert not res.ok
        assert not res.by_method
        assert res.notes["error"].code == "stat.vars_hydraulic_only"

    def test_it_says_it_in_spanish(self):
        from ogr_gui.core_messages import note_text
        p = _project()
        res = _gm(p, [_ks(p)])
        with _Spanish():
            said = note_text(res.notes["error"])
        assert "hidráulicas" in said and "filtración" in said, said
        assert "Every random variable" not in said, said


# ======================================================================
class TestSomeHydraulicAreNamed:
    """The other variables still carry a real sampling, so the run goes on;
    it may not go on quietly."""

    def test_global_minimum_warns_and_keeps_the_rest(self):
        p = _project()
        c, ks = _cohesion(p), _ks(p)
        res = _gm(p, [c, ks])
        assert res.ok
        assert "error" not in res.notes
        warning = res.notes["warning"]
        assert warning.code == "stat.vars_hydraulic"
        assert ks.key in warning and c.key not in warning
        # the line is in the notes panel too (D129)
        assert any(getattr(x, "code", None) == "stat.vars_hydraulic"
                   for x in res.note_lines)
        # the cohesion still moves the number
        values = res.by_method[_MID].statistics.values
        assert len(set(values)) > 1

    def test_the_values_are_those_of_the_run_without_it(self):
        """``ks`` reaches nothing: drawn AFTER the cohesion, it leaves the
        cohesion's column and every factor exactly as the run without it."""
        p = _project()
        c, ks = _cohesion(p), _ks(p)
        alone = _gm(p, [c]).by_method[_MID].statistics.values
        mixed = _gm(p, [c, ks]).by_method[_MID].statistics.values
        assert alone and alone == mixed

    def test_the_check_moves_no_number(self):
        """A/B in the same process: the same mixed run with the new check
        patched to nothing gives the same factors, bit for bit."""
        p = _project()
        c, ks = _cohesion(p), _ks(p)
        new = _gm(p, [c, ks]).by_method[_MID].statistics.values
        saved = P._hydraulic_variables_stop
        P._hydraulic_variables_stop = lambda _r, _v: False
        try:
            old = _gm(p, [c, ks]).by_method[_MID].statistics.values
        finally:
            P._hydraulic_variables_stop = saved
        assert new and new == old

    def test_overall_slope_warns(self):
        """The warning is written before the first search: a factory that
        refuses to search loses every sample, and the warning is still
        there."""
        p = _project()
        c, ks = _cohesion(p), _ks(p)
        res = run_overall_slope(p, _never, [c, ks], [_MID], num_samples=2,
                                sampling=SM.MONTE_CARLO, seed=7)
        assert res.notes["warning"].code == "stat.vars_hydraulic"
        assert ks.key in res.notes["warning"]

    def test_the_sweep_does_not_sweep_it(self):
        from ogr_slip2d.stat_messages import VAR_HYDRAULIC
        p = _project()
        c, ks = _cohesion(p), _ks(p)
        det = _det(p)
        alone = run_sensitivity(p, det, [c], intervals=4,
                                num_slices=_SLICES)
        mixed = run_sensitivity(p, det, [c, ks], intervals=4,
                                num_slices=_SLICES)
        assert mixed.ok
        assert mixed.notes["warning"].code == "stat.vars_hydraulic"
        sweeps = mixed.by_method[_MID]
        assert sweeps[ks.key].note.code == VAR_HYDRAULIC
        assert sweeps[ks.key].values == [] and sweeps[ks.key].fos == []
        # the cohesion's curve is untouched, and ks is not ranked
        assert sweeps[c.key].fos == alone.by_method[_MID][c.key].fos
        assert [r[0] for r in mixed.ranking(_MID)] == [c.key]


# ======================================================================
class TestTheWindowNamesItHydraulic:

    def test_the_status_of_the_sensitivity_plot(self):
        from PySide6.QtWidgets import QApplication
        from ogr_gui.statistics_window import StatisticsWindow
        QApplication.instance() or QApplication([])
        p = _project()
        c, ks = _cohesion(p), _ks(p)
        res = run_sensitivity(p, _det(p), [c, ks], intervals=4,
                              num_slices=_SLICES)
        with _Spanish():
            w = StatisticsWindow(p, sens_result=res)
            try:
                w._plot_sensitivity(_MID)
                text = w.status.text()
            finally:
                w.close()
                w.deleteLater()
        assert "hidráulica" in text, text
        assert "ya no está en el modelo" not in text, text

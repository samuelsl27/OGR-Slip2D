# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.164 (D91) — a random variable whose target no longer matches the model
must not pass for one that does.

WHAT INVARIANT THIS PROTECTS
----------------------------
``apply_sample`` returns how many parameters it wrote and ``set_value``
returns False when the target or the parameter is gone; the docstring of
``apply_sample`` says the count exists "so the caller can detect a
definition that no longer matches the model". All three callers threw the
value away, so a stale definition produced N IDENTICAL samples with
std_dev 0.0, PF 0.0, beta inf, ``ok`` true and an EMPTY ``notes``: rule 7
in its purest form, a declared input the analysis silently ignores.

WHY THE MEASUREMENT THE CARD PUBLISHES DOES NOT PROVE IT
--------------------------------------------------------
The card measures problem 12 sampling ``materials[0]``, the Embankment.
Measured on 0.1.163: the published Bishop circle (25.193, 15.283, r 7.715)
has its 30 slices in Soft Clay, so the Embankment is never crossed and its
cohesion does not move the factor even with the target INTACT — cohesion 0
and 50, friction 5 and 45 all answer 1.017489. A healthy variable
therefore produced the very output the card offers as proof. Only
``apply_sample -> 0`` distinguished the two. On ``materials[1]``, the
material the circle does cross, the contrast is real:

    intact  mean 0.996063021  std_dev 0.190636922  PF 0.450  beta -0.020652
    stale   mean 1.017489184  std_dev 0.0          PF 0.000  beta inf

PF of 45 % answered as 0 % with no note. That is the defect.

THIS IS NOT A SNAPSHOT TEST
---------------------------
No factor of safety is pinned here. What is checked is an IDENTITY: the
statistics of a run that carries a stale variable alongside a healthy one
must equal, value by value, the statistics of the same run without the
stale one at the same seed; and the values of a healthy run must equal
what applying the same samples by hand produces. Both are recomputed, not
recorded.

ONE ORDER DEPENDENCY, WRITTEN DOWN ON PURPOSE
---------------------------------------------
``sample_variables`` draws from its ``Random`` once per key in insertion
order, so the healthy variable keeps its column only while it comes
FIRST. Put the stale one first and the healthy column shifts. The test
that relies on the identity therefore builds ``[good, orphan]`` in that
order, and ``test_the_order_is_why`` fixes the reason so nobody
"simplifies" it away.

WHAT IS NOT A DEFECT HERE
-------------------------
A variable that writes and still leaves the factor flat is a fact about
the model, not about the sampler (the Embankment above). This file never
uses a flat curve as evidence of anything.
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
    apply_sample,
    available_variables,
    clone_project,
    run_global_minimum,
    run_overall_slope,
    run_sensitivity,
    set_value,
    unwritable_variables,
)
from ogr_slip2d.analysis_runner import build_method  # noqa: E402
from ogr_slip2d.search import GridSearch  # noqa: E402
from ogr_slip2d.surface import SlipCircle  # noqa: E402

_MID = "bishop_simplified"
_SLICES = 20

#: The same fixed circle ``test_random_variables_v134`` evaluates. A fixed
#: circle and no search at all: none of the invariants here depends on the
#: resolution of a grid, and the search is what makes the other statistics
#: files expensive.
_CIRCLE = SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.212)


def _search(project):
    """The search the sampler itself builds.

    Through ``build_method`` and not ``BishopSimplified()``: the engine
    takes the method as the PROJECT configures it, so a hand-built one
    would answer a different number and the identity below would be
    measuring method construction instead of ``apply_sample``.
    """
    return GridSearch(method=build_method(project, _MID, _SLICES),
                      num_slices=_SLICES, min_area=0.0)


def _det(project):
    return {_MID: _search(project).evaluate_circle(project, _CIRCLE)}


def _good(project, std_dev=3.0, span=9.0):
    """The cohesion of the first material, as a random variable."""
    mat = project.materials[0]
    v = [x for x in available_variables(project)
         if x.param == "cohesion" and x.target_id == mat.id][0]
    v.distribution = Distribution(
        DT.NORMAL, mean=mat.strength.params["cohesion"],
        std_dev=std_dev, rel_min=span, rel_max=span)
    return v


def _orphan(model, target_id="material-that-was-deleted"):
    """A variable pointing at a material that is not in the project.

    It carries the SAME distribution as the healthy one so the sampler
    draws the same amount of randomness for it: what is under test is the
    writing, never the drawing.
    """
    return RandomVariable(kind=VK.MATERIAL_STRENGTH, target_id=target_id,
                          param="cohesion", label="ghost cohesion",
                          distribution=model.distribution)


# ======================================================================
class TestTheCountNobodyRead:
    """The premise, measured rather than assumed."""

    def test_an_orphan_writes_nothing(self):
        p = _ej1_project()
        orphan = _orphan(_good(p))
        clone = clone_project(p)
        assert apply_sample(clone, [orphan], {orphan.key: 12.0}) == 0

    def test_the_helper_names_what_the_count_only_totals(self):
        p = _ej1_project()
        good = _good(p)
        orphan = _orphan(good)
        sample = {good.key: 12.0, orphan.key: 12.0}
        assert unwritable_variables(p, [good, orphan], sample) == [orphan.key]

    def _water_table_var(self):
        return RandomVariable(
            kind=VK.WATER_TABLE, target_id="", param="offset",
            label="water table offset",
            distribution=Distribution(DT.NORMAL, mean=0.0, std_dev=1.0,
                                      rel_min=3.0, rel_max=3.0))

    def _with_water_table(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex

        p = _ej1_project()
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(0, 22), Vertex(120, 12)], closed=False),
            btype=BoundaryType.WATER_TABLE))
        return p

    def _table_ys(self, project):
        from ogr_core.geometry import BoundaryType

        for b in project.boundaries:
            if b.btype == BoundaryType.WATER_TABLE:
                return [v.y for v in b.polyline.vertices]
        return []

    def test_the_water_table_write_is_not_idempotent(self):
        """WHY the probe needs a clone of its own rather than the one the
        sample was already applied to. The water-table variable is an
        OFFSET: asking the same project twice moves the table twice, so a
        probe run on an already-sampled clone would answer about a model
        that never existed. Measured: -2.5 twice is -5.0, not -2.5."""
        p = self._with_water_table()
        wt = self._water_table_var()
        clone = clone_project(p)
        assert self._table_ys(clone) == [22, 12]
        assert set_value(clone, wt, -2.5)
        assert self._table_ys(clone) == [19.5, 9.5]
        assert set_value(clone, wt, -2.5)
        assert self._table_ys(clone) == [17.0, 7.0]

    def test_get_value_would_have_called_a_deleted_table_healthy(self):
        """WHY the probe asks ``set_value`` and not ``get_value``. They are
        not mirrors: on a project with no water table at all ``get_value``
        answers 0.0 — the declared mean of an offset — while ``set_value``
        answers False. A probe built on ``get_value`` would pass exactly the
        class of definition this version exists to catch."""
        from ogr_core.statistics import get_value

        p = _ej1_project()
        assert not self._table_ys(p)
        wt = self._water_table_var()
        assert get_value(p, wt) == 0.0
        assert set_value(clone_project(p), wt, -2.5) is False
        assert unwritable_variables(p, [wt], {wt.key: -2.5}) == [wt.key]

    def test_a_water_table_that_is_there_is_not_an_orphan(self):
        p = self._with_water_table()
        wt = self._water_table_var()
        assert unwritable_variables(p, [wt], {wt.key: -2.5}) == []

    def test_the_probe_does_not_touch_the_project(self):
        """``unwritable_variables`` writes to find out, so it must write on
        a clone. The water-table variable is an OFFSET, which is why the
        probe may never be a project anyone else will read."""
        p = _ej1_project()
        good = _good(p)
        before = p.materials[0].strength.params["cohesion"]
        unwritable_variables(p, [good], {good.key: before + 25.0})
        assert p.materials[0].strength.params["cohesion"] == before


# ======================================================================
class TestAnOrphanStopsTheRun:
    """Nothing to sample is not a result of zero; it is not a result."""

    def test_global_minimum_refuses_and_says_which(self):
        p = _ej1_project()
        orphan = _orphan(_good(p))
        res = run_global_minimum(p, _det(p), [orphan], num_samples=4,
                                 sampling=SM.MONTE_CARLO, seed=7,
                                 num_slices=_SLICES)
        assert not res.ok
        assert orphan.key in res.notes["error"]
        assert "matches the model" in res.notes["error"]

    def test_overall_slope_refuses_too(self):
        """And it refuses BEFORE the first search: the guard is hoisted out
        of the per-method loop, so this costs nothing even though an
        Overall Slope sample is a whole search."""
        p = _ej1_project()
        orphan = _orphan(_good(p))

        def _never(_mid):
            raise AssertionError("the run must stop before searching")

        res = run_overall_slope(p, _never, [orphan], [_MID], num_samples=4,
                                sampling=SM.MONTE_CARLO, seed=7)
        assert not res.ok
        assert orphan.key in res.notes["error"]

    def test_no_variables_at_all_keeps_its_own_older_message(self):
        """An empty list is a different complaint from a list that matches
        nothing, and the guard must not swallow it."""
        p = _ej1_project()
        res = run_overall_slope(p, lambda _mid: _search(p), [], [_MID],
                                num_samples=4)
        assert not res.ok
        assert "random variable" in res.notes["error"].lower()


# ======================================================================
class TestAPartialOrphanWarnsAndKeepsTheRest:
    """The healthy variables still carry a real sampling, so the run goes
    on. What it may not do is go on quietly."""

    def _both(self, p, n=12, seed=3):
        good = _good(p)
        orphan = _orphan(good)
        det = _det(p)
        alone = run_global_minimum(p, det, [good], num_samples=n,
                                   sampling=SM.LATIN_HYPERCUBE, seed=seed,
                                   num_slices=_SLICES)
        # good FIRST -- see the module docstring.
        mixed = run_global_minimum(p, det, [good, orphan], num_samples=n,
                                   sampling=SM.LATIN_HYPERCUBE, seed=seed,
                                   num_slices=_SLICES)
        return good, orphan, alone, mixed

    def test_the_warning_names_only_the_orphan(self):
        p = _ej1_project()
        good, orphan, _alone, mixed = self._both(p)
        assert mixed.ok
        assert "error" not in mixed.notes
        warning = mixed.notes["warning"]
        assert orphan.key in warning
        assert good.key not in warning

    def test_the_statistics_are_those_of_the_run_without_it(self):
        """THE identity: a variable that writes nothing must change nothing
        about the sampling that does."""
        p = _ej1_project()
        _good_v, _orphan_v, alone, mixed = self._both(p)
        a = alone.by_method[_MID].statistics.values
        b = mixed.by_method[_MID].statistics.values
        assert a and b
        assert a == b

    def test_the_order_is_why(self):
        """Why the list above is built good-first, fixed so it is not
        'simplified'. The sampler draws once per key in insertion order, so
        a stale variable placed FIRST consumes the draw the healthy one
        would have had, and the identity above stops holding. This is a
        fact about the sampler, not a defect."""
        from ogr_core.statistics.random_variables import (
            sample_project_variables,
        )

        p = _ej1_project()
        good = _good(p)
        orphan = _orphan(good)
        alone = sample_project_variables([good], 8, SM.LATIN_HYPERCUBE, 5)
        after = sample_project_variables([good, orphan], 8,
                                         SM.LATIN_HYPERCUBE, 5)
        before = sample_project_variables([orphan, good], 8,
                                          SM.LATIN_HYPERCUBE, 5)
        assert after[good.key] == alone[good.key]
        assert before[good.key] != alone[good.key]


# ======================================================================
class TestSensitivityMarksTheOrphan:
    def _run(self, variables, p, intervals=4):
        return run_sensitivity(p, _det(p), variables, intervals=intervals,
                               num_slices=_SLICES)

    def test_it_is_named_and_left_unswept(self):
        p = _ej1_project()
        good = _good(p)
        orphan = _orphan(good)
        res = self._run([good, orphan], p)
        assert res.ok
        sweeps = res.by_method[_MID]
        assert sweeps[orphan.key].note
        assert sweeps[orphan.key].n == 0
        assert sweeps[good.key].n > 1 and not sweeps[good.key].note

    def test_it_is_not_the_least_influential_parameter(self):
        """A span of zero it never measured may not sit in the ranking as
        if it had been measured and found not to matter."""
        p = _ej1_project()
        good = _good(p)
        orphan = _orphan(good)
        res = self._run([good, orphan], p)
        ranked = [k for k, _lab, _span in res.ranking()]
        assert good.key in ranked
        assert orphan.key not in ranked

    def test_every_variable_stale_is_not_a_result(self):
        p = _ej1_project()
        orphan = _orphan(_good(p))
        res = self._run([orphan], p)
        assert not res.ok
        assert orphan.key in res.notes["error"]

    def test_a_healthy_sweep_still_has_its_note_empty(self):
        p = _ej1_project()
        good = _good(p)
        res = self._run([good], p)
        assert res.ok
        assert res.by_method[_MID][good.key].note == ""
        assert "warning" not in res.notes


# ======================================================================
class TestTheGuardIsSilentOnAHealthyModel:
    """The twin of rule 7: a guard that fires on a sound model would be a
    worse defect than the one it fixes. This is the in-repo analogue of the
    bank census (6 models with random variables, 22 variables, zero that
    fail to write)."""

    def test_no_note_of_any_kind(self):
        p = _ej1_project()
        res = run_global_minimum(p, _det(p), [_good(p)], num_samples=8,
                                 sampling=SM.LATIN_HYPERCUBE, seed=11,
                                 num_slices=_SLICES)
        assert res.ok
        assert "error" not in res.notes and "warning" not in res.notes

    def test_the_values_are_still_the_hand_computed_ones(self):
        """Recomputed, not recorded: every sampled factor must equal what
        applying the same sample by hand gives. This is also what proves
        the throwaway probe clone never leaks into the run."""
        p = _ej1_project()
        good = _good(p)
        det = _det(p)
        res = run_global_minimum(p, det, [good], num_samples=6,
                                 sampling=SM.LATIN_HYPERCUBE, seed=4,
                                 num_slices=_SLICES)
        column = res.samples[good.key]
        search = _search(p)
        by_hand = []
        for x in column:
            clone = clone_project(p)
            assert apply_sample(clone, [good], {good.key: x}) == 1
            r = search.evaluate_circle(clone, _CIRCLE)
            if r is not None and r.is_valid:
                by_hand.append(r.fos)
        assert by_hand == res.by_method[_MID].statistics.values

    def test_the_project_is_not_modified(self):
        p = _ej1_project()
        before = p.to_dict()
        run_global_minimum(p, _det(p), [_good(p)], num_samples=4,
                           sampling=SM.MONTE_CARLO, seed=2,
                           num_slices=_SLICES)
        assert p.to_dict() == before


# ======================================================================
from test_statistics_gui_v138 import (  # noqa: E402
    _app, _define_vars, _project, _requires_qt, _window,
)


@_requires_qt
class TestTheWarningReachesTheUser:
    """A note nobody shows is a note that does not exist — the phrase
    ``test_statistical_rebuild_v1154`` uses for this exact failure mode.
    ``_compute_statistics`` printed ``notes["error"]`` and ONLY when the run
    came back empty, so a partial run reported PF with nothing else said.
    This does NOT do D129's per-method work; it opens the channel for the
    one key this version writes."""

    def _run_with_one_stale(self, **kw):
        p = _project(n=6, **kw)
        variables = _define_vars(p)
        assert len(variables) > 1
        # The SECOND one goes stale, so the first still carries a real
        # sampling and the run survives as a partial.
        variables[1].target_id = "material-that-was-deleted"
        w = _window(p)
        w._compute_statistics()
        return w, variables[1]

    def test_the_partial_run_says_so(self):
        _app()
        w, stale = self._run_with_one_stale()
        assert w._prob_result is not None and w._prob_result.ok
        assert any(stale.key in n for n in w.last_statistics_notes)

    def test_the_panel_shows_it_beside_the_compute_notes(self):
        _app()
        w, stale = self._run_with_one_stale()
        w.last_compute_warnings = ["a note from the deterministic run"]
        w.act_analysis_notes()
        panel = w._analysis_notes_panel
        try:
            assert any(stale.key in n for n in panel.notes)
            assert "a note from the deterministic run" in panel.notes
        finally:
            # Rule 5: a non-modal window left open is leaked state.
            panel.close()

    def test_sensitivity_reports_it_too(self):
        _app()
        w, stale = self._run_with_one_stale(prob=False, sens=True)
        assert w._sens_result is not None and w._sens_result.ok
        assert any(stale.key in n for n in w.last_statistics_notes)
        ranked = [k for k, _lab, _span in w._sens_result.ranking()]
        assert stale.key not in ranked

    def test_an_open_panel_refreshes_instead_of_going_stale(self):
        """The panel is refreshed from two places. Either one rebuilding it
        from its own list alone would drop the other's notes, which is the
        same silence one window further along."""
        _app()
        p = _project(n=6)
        variables = _define_vars(p)
        w = _window(p)
        w.last_compute_warnings = ["a note from the deterministic run"]
        w.act_analysis_notes()
        panel = w._analysis_notes_panel
        try:
            assert not any("material-that-was" in n for n in panel.notes)
            variables[1].target_id = "material-that-was-deleted"
            w._compute_statistics()
            assert any(variables[1].key in n for n in panel.notes)
            assert "a note from the deterministic run" in panel.notes
        finally:
            panel.close()

    def test_a_healthy_run_leaves_the_list_empty(self):
        """The twin of rule 7 on this side: the channel must stay quiet
        when there is nothing to say."""
        _app()
        p = _project(n=6)
        _define_vars(p)
        w = _window(p)
        w._compute_statistics()
        assert w._prob_result is not None and w._prob_result.ok
        assert w.last_statistics_notes == []

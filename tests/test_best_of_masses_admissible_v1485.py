# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.485 — the choice among the disjoint masses of one surface uses the
order of ``SearchResult.critical``: an admissible mass beats a lower one
that is inadmissible (defect D374).

THE INVARIANTS.

1. ``BaseSearch._best_of_masses`` ranks its candidates (disjoint masses,
   weak-layer cases) with ``criticality_key``: valid first, then
   admissible, then score. A circle whose lowest mass is inadmissible and
   whose other mass is admissible reports the ADMISSIBLE one.
2. When every candidate is inadmissible, the lowest one is still reported,
   as ``critical`` falls back to all surfaces when none is admissible.
3. A surface with one mass is untouched: its answer is that mass.
4. ``critical``, ``top_n`` and the choice among masses share one key:
   ``top_n(1)[0] is critical`` on a mixed population, and the key orders
   valid, admissible and score in that order.

WHAT WAS WRONG. The loop compared by score alone, while ``critical`` and
``top_n`` (D361) put the admissible surfaces first. So the evaluation of a
circle could hide the mass the search would have preferred: the circle
entered the population as inadmissible at the lower factor, and its
admissible mechanism never competed.

THE WITNESS IS NATURAL. The reference grid of Ej_2
(``test_slide_validation_ej2_v184``, built in code there) contains the
circle (33.333333, 92.894737, 42.958327), which cuts the ground into two
masses. With Spencer (1967), the lower mass, at 3.0395, is declared
inadmissible by the method itself, and the other mass is admissible at
3.5401. Probe S3 of the compute audit of v0.1.377 found it, and the census
of the bank (``_tools/censo_masas_d374.py``, ``_auditoria/D374_masas/``)
saw it again. The guard of ``TestTheWitnessIsReal`` says so, or the cases
below prove nothing. The census of the bank found 34 such choices over 175
models, all in problem 059 with Spencer, and none moves a critical surface.
On Ej_2 it moves none either: the critical surface is another circle.

DISCRIMINATION against the v0.1.484 tree. MEASURED, by copying this file
into a ``git worktree`` at 69446c6 and running it there. Of the 7 cases,
**2 fail and 5 pass**:

  fail  the_circle_reports_its_admissible_mass   (3.0395, inadmissible)
        the_key_orders_valid_admissible_score    (no ``criticality_key``)

  pass  the guard, every_mass_inadmissible_keeps_the_lowest,
        an_invalid_mass_never_replaces_the_first and
        one_mass_is_untouched (what must not move), and
        critical_is_the_first_of_top_n (D361 already made them agree).

A mutant that makes ``critical`` rank by score alone fails
critical_is_the_first_of_top_n.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

WITNESS = dict(centre_x=33.333333, centre_y=92.894737, radius=42.958327)
#: A circle of Ej_2 that cuts a single mass.
ONE_MASS = dict(centre_x=20.0, centre_y=90.0, radius=55.0)

_CACHE: dict = {}


def _ej2():
    if "p" not in _CACHE:
        from test_slide_validation_ej2_v184 import NUM_SLICES, _ej2_project
        _CACHE["p"] = _ej2_project()
        _CACHE["n"] = NUM_SLICES
    return _CACHE["p"], _CACHE["n"]


def _search(mark=None):
    """A Spencer grid search on Ej_2 whose ``_analyse`` records every
    candidate it solves, optionally passed through ``mark`` first."""
    from ogr_slip2d.methods.spencer import Spencer
    from ogr_slip2d.search import GridSearch
    _p, n = _ej2()
    gs = GridSearch(method=Spencer(), num_slices=n, min_area=1.0)
    seen = []
    original = gs._analyse

    def recording(project, trial, slices):
        res = original(project, trial, slices)
        if res is not None and mark is not None:
            mark(res)
        seen.append(res)
        return res

    gs._analyse = recording
    return gs, seen


def _circle(**kw):
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(**kw)


def _evaluate(circle, mark=None):
    key = (tuple(sorted(circle.items())), mark)
    if key not in _CACHE:
        p, _n = _ej2()
        gs, seen = _search(mark)
        _CACHE[key] = (gs.evaluate_circle(p, _circle(**circle)), seen)
    return _CACHE[key]


def _inadmissible(res):
    res.admissible = False
    res.admissibility_note = "synthetic: every mass rejected"


def _invalid(res):
    res.fos = None
    res.converged = False
    res.error_message = "synthetic: every mass failed"
    res.reason = "not_converged"


# ======================================================================
class TestTheWitnessIsReal:
    """Guard: without it the cases below prove nothing."""

    def test_two_valid_masses_the_lower_one_inadmissible(self):
        _res, seen = _evaluate(WITNESS)
        valid = [r for r in seen if r is not None and r.is_valid]
        assert len(valid) == 2, [(r.fos, r.admissible) for r in valid]
        low, high = sorted(valid, key=lambda r: r.fos)
        assert not low.admissible and high.admissible, (
            low.admissible, high.admissible)
        assert low.admissibility_reason == ""      # the method's verdict
        assert math.isclose(low.fos, 3.0395, abs_tol=5e-4), low.fos
        assert math.isclose(high.fos, 3.5401, abs_tol=5e-4), high.fos


class TestTheAdmissibleMassWins:

    def test_the_circle_reports_its_admissible_mass(self):
        res, seen = _evaluate(WITNESS)
        high = max((r for r in seen if r is not None and r.is_valid),
                   key=lambda r: r.fos)
        assert res is high, (res.fos, res.admissible)
        assert res.admissible

    def test_every_mass_inadmissible_keeps_the_lowest(self):
        res, seen = _evaluate(WITNESS, mark=_inadmissible)
        valid = [r for r in seen if r is not None and r.is_valid]
        assert len(valid) == 2 and not any(r.admissible for r in valid)
        assert res is min(valid, key=lambda r: r.fos), res.fos

    def test_an_invalid_mass_never_replaces_the_first(self):
        """Every mass marked invalid: the first one solved stays, as
        before (control, passes on v0.1.484 too)."""
        res, seen = _evaluate(WITNESS, mark=_invalid)
        solved = [r for r in seen if r is not None]
        assert len(solved) >= 2 and not any(r.is_valid for r in solved)
        assert res is solved[0]

    def test_one_mass_is_untouched(self):
        res, seen = _evaluate(ONE_MASS)
        solved = [r for r in seen if r is not None]
        assert len(solved) == 1, len(solved)
        assert res is solved[0]


class TestOneKeyForTheThreeChoices:

    def test_the_key_orders_valid_admissible_score(self):
        from ogr_slip2d.methods.base import LEMResult
        from ogr_slip2d.search import criticality_key, surface_score

        def r(fos, admissible=True, valid=True):
            out = LEMResult(fos=fos if valid else None, converged=valid,
                            iterations=1, method_id="x",
                            surface=None, slices=None,
                            **({} if valid else {"error_message": "synthetic",
                                                 "reason": "not_converged"}))
            out.admissible = admissible
            return out

        population = [r(0.5, valid=False), r(0.9, admissible=False),
                      r(1.4), r(1.2), r(0.8, admissible=False)]
        order = sorted(population,
                       key=lambda x: criticality_key(x, surface_score))
        assert [(x.is_valid, x.admissible, x.fos) for x in order] == [
            (True, True, 1.2), (True, True, 1.4), (True, False, 0.8),
            (True, False, 0.9), (False, True, None)]

    def test_critical_is_the_first_of_top_n(self):
        from ogr_slip2d.methods.base import LEMResult
        from ogr_slip2d.search import SearchResult

        def r(fos, admissible=True):
            out = LEMResult(fos=fos, converged=True, iterations=1,
                            method_id="x",
                            surface=None, slices=None)
            out.admissible = admissible
            return out

        for pop in ([r(0.9, False), r(1.4), r(1.2)],
                    [r(0.9, False), r(0.7, False)]):
            sr = SearchResult(method_id="x", evaluations=pop)
            assert sr.top_n(1)[0] is sr.critical, (
                sr.top_n(1)[0].fos, sr.critical.fos)
        assert SearchResult(method_id="x", evaluations=[
            r(0.9, False), r(1.4), r(1.2)]).critical.fos == 1.2
        assert SearchResult(method_id="x", evaluations=[
            r(0.9, False), r(0.7, False)]).critical.fos == 0.7

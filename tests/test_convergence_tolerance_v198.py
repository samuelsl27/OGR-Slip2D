# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Where the iteration stops must not decide what it converges to.

WHAT INVARIANT THIS PROTECTS. Every iterative method here stops on an
ABSOLUTE criterion over the factor of safety, at a default of 0.005
(``ogr_core/project/settings.py``). On a factor of safety around 1.0 that is
half a percentage point, which is the same order as the whole band of results
the Slide2 verification bank flags for review — so until v0.1.97 nobody could
say whether those were engine defects or stopping noise. This file pins the
answer: a fixed point does not depend on when you stop iterating, so
tightening the tolerance by four orders of magnitude must move the factor of
safety by a bounded, small and *stated* amount.

This is NOT a snapshot test. It never asserts a factor of safety. It asserts
the DISTANCE between two runs of the same solve stopped at different points,
against a bound derived from the stopping mechanism — which is the analytic
form of anchoring that rule 1 allows.

It complements, and does not duplicate,
``test_project_settings_wiring_v174``'s
``test_a_tighter_tolerance_changes_the_answer``, which demands the opposite:
that tightening the tolerance MOVE the number, because a setting that changes
nothing is worse than no setting (rule 7). Together they say the knob acts,
and the point it converges to is stable.

WHY FOUR MARGINS AND NOT ONE. The same ``tolerance`` governs two criteria of
different nature, and they carry different error:

* **A STEP.** Bishop and Janbu stop on ``|F_new - F| < tol`` — literally what
  the reference documents ("the difference in safety factor between two
  successive iterations"). A contraction of ratio r stopped on a step of
  ``tol`` sits within ``tol*r/(1-r)`` of the root, and these iterations
  contract hard (4 to 7 passes), so the error is a small FRACTION of ``tol``.

* **A RESIDUAL.** Spencer and GLE stop their lambda search on
  ``|F_f - F_m| < tol`` and then return ``(F_f + F_m)/2``. A residual does
  not shrink geometrically the way a step does: the returned value sits
  within about half the residual of either branch, so the error scales like
  ``tol`` itself, not like a small fraction of it.

Measured on the case below (0.1.97), error as a fraction of ``tol``:

    bishop_simplified      0.024      janbu_corrected        0.034
    spencer                0.372      gle_morgenstern_price  0.226

The bounds below are the MECHANISM's, not the measurement's, and the measured
values sit under them with room: 0.024 and 0.034 against 0.1; 0.372 and 0.226
against 0.5.

DO NOT RAISE THESE CONSTANTS TO MAKE A FAILURE GO AWAY. This project has
already paid for that once: ``docs/audits/spencer_gle_interslice_v179.md``
records that Spencer and GLE were given double the margin of every other
method in ``test_slide_validation_ej1.py`` with no reason written down, and
that the asymmetry *was* the finding — it sat green for sixty versions over a
real defect. A tolerance loosened so that a test passes stops measuring the
code and starts measuring the patience of whoever set it. If a method exceeds
its bound here, the stopping criterion has changed meaning, and that is the
thing to report (rule 6), not the constant to edit.

WHAT THIS FILE DELIBERATELY DOES NOT ASSERT. At 1e-7 the four methods agree
with each other to seven significant figures on this circle. That is not a
property worth pinning — it is the symptom the audit above is open about, and
a test that fixed it in place would enshrine the very bug rule 1 exists to
forbid.

Case: Giam & Donald (1989), ACADS problem 1(c) — the versioned model in
``validacion/casos/003-acads-1c/``, evaluated on the critical circle the study
publishes, centre (34.121, 43.254) and R 18.781, whose reading is confirmed
independently: on this geometry the circle daylights within 1 mm of the
published outcrops.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from pathlib import Path

_MODEL = (Path(__file__).resolve().parent.parent
          / "validacion" / "casos" / "003-acads-1c" / "modelo.ogr")

#: The published critical circle of ACADS 1(c).
_CIRCLE = (34.121, 43.254, 18.781)

#: v0.1.100 — a circle of the SAME model's grid whose centre sits on the crest
#: vertex (50, 35), so it daylights at 90 deg. Its fixed point is 5.51; the map
#: sends the default initial guess F = 1.0 to 0.995, one step of 0.0048. It is
#: the surface that showed the first step must not be allowed to end the
#: iteration: accepted as converged it published 0.995 and won the grid search
#: at 29 % below the study's value.
_SLOW_CIRCLE = (50.0, 35.0, 9.181818181818182)

_LOOSE = 1e-3
_TIGHT = 1e-7

#: Bound on |dF| as a multiple of the loose tolerance, per method, with the
#: reason each one differs. See the module docstring before changing one.
_BOUND = {
    # Stop on a STEP of a hard-contracting fixed point -> a small fraction.
    "bishop_simplified": 0.1,
    "janbu_corrected": 0.1,
    # Stop on the RESIDUAL |F_f - F_m|, then average the two branches -> the
    # error scales with the residual, halved by the averaging.
    "spencer": 0.5,
    "gle_morgenstern_price": 0.5,
}

#: Convergence arguments held FIXED across the comparison.
#: ``max_iterations`` is stated here rather than inherited from the project
#: so that a failure means "the fixed point moved" and never "the iteration
#: ran out of room" — the two are indistinguishable in the result otherwise.
#: 200 is far above what any of these need (7 to 24 passes at 1e-7).
_FIXED = dict(max_iterations=200, initial_fos=1.0, iterate_steffensen=True,
              min_lambda=-1.5, max_lambda=6.0)


def _methods():
    from ogr_slip2d.methods import (BishopSimplified, GLEMorgensternPrice,
                                    JanbuCorrected, Spencer)
    return {
        "bishop_simplified": BishopSimplified,
        "janbu_corrected": JanbuCorrected,
        "spencer": Spencer,
        "gle_morgenstern_price": GLEMorgensternPrice,
    }


def _case():
    """The project, the circle and its slices, or None if the case is absent.

    Absent rather than failing: the validation cases live in their own folder
    and a checkout without them should not turn this file red for a reason
    that has nothing to do with convergence.
    """
    if not _MODEL.is_file():
        return None
    from ogr_core.project import Project
    from ogr_slip2d import SlipCircle, slice_surface

    project = Project.load(_MODEL)
    cx, cy, r = _CIRCLE
    circle = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
    slices = slice_surface(project, circle, num_slices=25)
    assert slices is not None and len(slices) == 25
    return project, circle, slices


def _slow_case():
    """The same model, on the circle whose map crawls past the initial guess."""
    if not _MODEL.is_file():
        return None
    from ogr_core.project import Project
    from ogr_slip2d import SlipCircle, slice_surface

    project = Project.load(_MODEL)
    cx, cy, r = _SLOW_CIRCLE
    circle = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
    slices = slice_surface(project, circle, num_slices=25)
    assert slices is not None and len(slices) == 25
    return project, circle, slices


def _solve(cls, tolerance, case):
    project, circle, slices = case
    return cls(tolerance=tolerance, **_FIXED).compute_fos(
        project, circle, slices)


# ======================================================================
class TestTheStoppingPointDoesNotDecideTheAnswer:

    def test_every_method_still_converges_at_the_tight_tolerance(self):
        """A comparison against a run that never converged measures nothing.

        The reference warns that much smaller tolerances "may lead to
        convergence problems", so this is checked and not assumed.
        """
        case = _case()
        if case is None:
            return
        for name, cls in _methods().items():
            result = _solve(cls, _TIGHT, case)
            assert result.converged, (name, result.error_message)
            assert result.iterations < _FIXED["max_iterations"], (
                name, result.iterations)

    def test_the_factor_of_safety_moves_less_than_its_stated_bound(self):
        """|F(1e-3) - F(1e-7)| against the bound the mechanism predicts."""
        case = _case()
        if case is None:
            return
        for name, cls in _methods().items():
            loose = _solve(cls, _LOOSE, case)
            tight = _solve(cls, _TIGHT, case)
            assert loose.converged and tight.converged, name
            moved = abs(loose.fos - tight.fos)
            limit = _BOUND[name] * _LOOSE
            assert moved < limit, (
                f"{name}: moved {moved:.3e} at tolerance {_LOOSE:g}, over "
                f"the {_BOUND[name]}*tol bound of {limit:.3e}. Read the "
                f"module docstring before touching the constant.")

    def test_the_step_methods_are_the_precise_ones(self):
        """The two families are not interchangeable, and the test says so.

        Bishop and Janbu stop on a step and must land well inside the loose
        bound that Spencer and GLE need. If this ever fails, the two families
        have stopped differing — which would mean the lambda search is no
        longer stopping on a residual, and the bounds above no longer
        describe the code.
        """
        case = _case()
        if case is None:
            return
        methods = _methods()
        for name in ("bishop_simplified", "janbu_corrected"):
            moved = abs(_solve(methods[name], _LOOSE, case).fos
                        - _solve(methods[name], _TIGHT, case).fos)
            assert moved < 0.1 * _LOOSE, (name, moved)


# ======================================================================
class TestTheFirstStepCannotEndTheIteration:
    """v0.1.100 — the initial guess is not an iterate of the map.

    The stopping rule is a STEP between two successive iterates, and the
    contraction argument in the module docstring is about ITERATES. Measuring
    the step from the value the program picked to start with says nothing
    about where the fixed point is: where the map is slow near that value the
    two are indistinguishable, and they are not the same thing.

    Measured on ``_SLOW_CIRCLE`` with the model's own tolerance of 0.005: the
    map sends F = 1.0 to 0.995207, a step of 0.0048, and accepting it reported
    a converged factor of safety of 0.995 whose real fixed point is 5.5147 —
    a factor of five and a half, on a surface that then won the ACADS 1(c)
    grid search and dragged it 29 % below the published value.
    """

    def test_a_slow_map_is_not_mistaken_for_a_fixed_point(self):
        case = _slow_case()
        if case is None:
            return
        loose = _solve(_methods()["bishop_simplified"], 0.005, case)
        tight = _solve(_methods()["bishop_simplified"], _TIGHT, case)
        assert tight.converged, tight.error_message
        assert loose.converged, loose.error_message
        # The whole point: the loose run must land on the same fixed point,
        # not on the neighbourhood of its own starting guess.
        assert abs(loose.fos - tight.fos) < 0.1, (loose.fos, tight.fos)
        assert abs(tight.fos - 1.0) > 1.0, (
            "the fixture stopped being the pathological one")

    def test_no_method_ever_converges_on_its_first_pass(self):
        """Stated as an invariant rather than as one circle's number.

        One pass means the only comparison made was against the initial guess,
        so ``converged`` would be asserting something the iteration never
        measured — whatever the surface, whatever the method.
        """
        for case in (_case(), _slow_case()):
            if case is None:
                continue
            for name, cls in _methods().items():
                for tol in (0.005, _LOOSE, _TIGHT):
                    r = _solve(cls, tol, case)
                    if r.converged:
                        assert r.iterations > 1, (name, tol, r.iterations)

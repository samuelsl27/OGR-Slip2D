# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Where the inner iteration stops must not decide which lambdas exist.

WHAT INVARIANT THIS PROTECTS. Spencer and GLE do not compute a factor of
safety directly: they look for the inter-slice inclination lambda at which
the force and the moment factors agree, by sampling a grid of lambdas and
bracketing the sign change of ``g(lambda) = F_f - F_m``. A lambda whose
inner fixed point fails to converge is dropped from that grid, silently, and
the search brackets whatever is left. So the rule this file exists to
enforce is that **a lambda must be dropped for a reason that belongs to the
slope, and never for a reason that belongs to the solver.**

That rule was broken from the first public commit until v0.1.159, and it is
defect D63 of the verification bank. ``solve_branch`` carried a hardcoded
ceiling of 80 passes. The moment branch is a linear contraction whose ratio
tends to 1 as lambda grows — measured on the 50 degree plane below with 50
slices: 0.73 at lambda = 0, 0.90 at the root 1.2269, 0.96 at 2.0 — so the
number of passes it needs grows with lambda AND with the tightness of the
tolerance. The set of lambdas that fitted inside 80 passes therefore SHRANK
as the tolerance was tightened, until the bracket itself was gone and the
"no lambda-bracket" path handed back the nearest raw grid node. The symptom
was the giveaway: tightening the convergence tolerance moved the answer AWAY
from the closed form of a plane wedge, from +6.7e-4 at 1e-3 to +2.8e-2 at
1e-10, while Corps #1 sat at 5e-10 at both.

WHY THE ANCHOR IS NOT IN THIS FILE. The external reference — the closed form
of a plane wedge, which binds every method that closes global force
equilibrium — lives in ``tests/test_janbu_wedge_v1142.py``, where
``TestSpencerAndGleSettleOnTheWedge`` asserts the closure criterion itself.
This file asserts the MECHANISM instead: that the criterion which now stops
the inner loop is stalling rather than counting, that it cannot retroactively
change anything that already converged, and that the two remaining reasons
for abandoning a branch are told apart rather than sharing one silence.
Splitting them is deliberate. A test of the mechanism that also owned the
reference value could be made to pass by moving the reference.

WHY THE SECOND HALF IS HERE TOO. The same defect had a second mouth: the
fallback that fires when no bracket is found called itself CONVERGED
whenever the residual was below a hardcoded 0.02 — twenty thousand times the
requested tolerance at 1e-6 — with an empty ``error_message`` and an empty
``reason``. A reserve value wearing the clothes of an answer is the same
family as D20 (the 0.22043 of verification problem 70) and D10, and the
lesson both times was that a fallback has to say it is one.

And the obvious repair for THAT is wrong, which this file also records
because the wrong version was written first and only measurement caught it.
Making the verdict follow the caller's tolerance converts a silent lie into
a silent VETO, because ``converged`` feeds ``is_valid`` and
``search.surface_score`` scores that at infinity — defect D37/C1 all over
again. Measured on the Ej_1 block search: the reported critical went from
0.654746 to 1.841807 and the m-alpha post-filter stopped flagging anything.
So the boundary keeps its value, gains a name and a reason
(``interslice.FALLBACK_RESIDUAL_LIMIT``), and the silence is broken where
breaking it vetoes nothing: in ``details`` and in a note.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

#: The plane wedge fixture, built here rather than imported: the modules in
#: ``tests/`` cannot import one another outside the runner, and this
#: geometry is four vertices and one material.
H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
NSLICES = 50

#: The plane whose root sits at lambda = 1.2269, where the moment branch
#: contracts at 0.8955 and needs 171 passes to reach 1e-10 — more than
#: twice the ceiling this version removed. That is the whole of D63 in one
#: number.
BETA = 50.0
ROOT_LAMBDA = 1.2269

#: A lambda well past the root, where the branch is not a solution and does
#: not converge at any budget.
WANDERING_LAMBDA = 2.5

OLD_CEILING = 80


def _daylight_x(beta_deg):
    return TOE + H / math.tan(math.radians(beta_deg))


def _bare():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project

    p = Project("wedge")
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=GAMMA,
                            strength=MohrCoulomb(cohesion=COH,
                                                 friction_angle=PHI))]
    return p


def _anchored(application=None):
    from ogr_core.geometry import Vertex
    from ogr_core.support import (EndAnchored, ForceApplication,
                                  ForceOrientation, SupportInstance)
    p = _bare()
    p.support_types = [EndAnchored(anchor_capacity=120.0,
                                   out_of_plane_spacing=1.0)]
    p.supports = [SupportInstance(
        type_id="end_anchored",
        head=Vertex(34.0, 6.0), tail=Vertex(48.0, 11.0),
        force_application=application or ForceApplication.ACTIVE,
        orientation=ForceOrientation.USER_DEFINED,
        user_angle_deg=15.0)]
    return p


def _plane(beta_deg=BETA):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(TOE, 0.0), Vertex(_daylight_x(beta_deg), H)]))


def _system(project=None, beta_deg=BETA):
    """The GLE system of the plane, ready to be asked for one branch."""
    from ogr_slip2d.interslice import GLESystem
    from ogr_slip2d.moment_balance import axis_for
    from ogr_slip2d.slicer import slice_surface

    project = project or _bare()
    surface = _plane(beta_deg)
    sl = slice_surface(project, surface, num_slices=NSLICES)
    assert sl is not None and sl.slices, "the plane produced no slices"
    n = len(sl.slices)
    return GLESystem(sl.slices, [1.0] * (n + 1), 0.0, 0.0, 1.0,
                     None, None, None, axis_for(project, surface),
                     tolerance=1e-14)


def _moment_branch(system, lam, tolerance, **kw):
    from ogr_slip2d.interslice import solve_branch
    return solve_branch(system.rows, system.lambda_boundary(lam),
                        system._moment_fos, tolerance, 1.0, **kw)


def _result(method_id, project, tolerance, beta_deg=BETA):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.slicer import slice_surface
    surface = _plane(beta_deg)
    sl = slice_surface(project, surface, num_slices=NSLICES)
    return method_registry()[method_id](
        tolerance=tolerance, max_iterations=400).compute_fos(
            project, surface, sl)


# ======================================================================
class TestPatienceCannotChangeWhatAlreadyConverged:
    """The neutrality of this version is a PROOF, not a sample, and this
    class is where that proof is written down as something executable.

    ``stall`` is incremented at most once per pass and starts at zero, so it
    cannot reach ``patience`` before pass ``patience + 1``. With a patience
    of 80 — the value of the ceiling it replaces — the first 80 passes of
    the loop are those of v0.1.158 instruction for instruction. Every branch
    that converged then converges now, to the same F, in the same number of
    passes, whatever the patience is set to.
    """

    def test_the_patience_is_at_least_the_ceiling_it_replaces(self):
        from ogr_slip2d.interslice import STALL_PATIENCE
        assert STALL_PATIENCE >= OLD_CEILING, STALL_PATIENCE

    def test_a_branch_that_converges_early_is_untouched_by_the_patience(self):
        """Same F, same pass count, at three patiences three orders apart."""
        system = _system()
        seen = []
        for patience in (OLD_CEILING, 200, 10000):
            state = _moment_branch(system, 0.2, 1e-3, patience=patience)
            assert state is not None and state.converged
            assert state.passes <= OLD_CEILING, state.passes
            seen.append((state.fos, state.passes))
        assert len(set(seen)) == 1, seen

    def test_it_is_untouched_at_the_tight_tolerance_too(self):
        """The branch below the ceiling at 1e-10 as well, so the claim is
        not an artefact of a loose tolerance converging in six passes."""
        system = _system()
        seen = []
        for patience in (OLD_CEILING, 10000):
            state = _moment_branch(system, 0.2, 1e-10, patience=patience)
            assert state is not None and state.converged
            assert state.passes <= OLD_CEILING, state.passes
            seen.append((state.fos, state.passes))
        assert len(set(seen)) == 1, seen


# ======================================================================
class TestTheCeilingNoLongerDecidesTheAnswer:
    """D63 in one branch. The root of the 50 degree plane sits at lambda
    1.2269; its moment branch needs more than twice the old ceiling to reach
    1e-10, so under v0.1.158 that lambda was thrown away and the bracket
    around the root went with it."""

    def test_the_branch_at_the_root_needs_more_than_the_old_ceiling(self):
        state = _moment_branch(_system(), ROOT_LAMBDA, 1e-10)
        assert state is not None and state.converged, state
        assert state.passes > OLD_CEILING, state.passes

    def test_the_old_ceiling_would_have_thrown_it_away(self):
        """The before half of the comparison, run rather than remembered:
        the same call capped where it used to be capped does not converge."""
        state = _moment_branch(_system(), ROOT_LAMBDA, 1e-10,
                               max_passes=OLD_CEILING)
        assert state is not None
        assert state.converged is False, state.passes
        assert state.passes == OLD_CEILING, state.passes

    def test_a_slower_lambda_still_beyond_the_ceiling_also_converges(self):
        """Rule 7 for the change itself: it must buy more than one lambda."""
        state = _moment_branch(_system(), 1.5, 1e-10)
        assert state is not None and state.converged, state
        assert state.passes > OLD_CEILING, state.passes


# ======================================================================
class TestStallingAndRunningOutOfBudgetAreDifferentThings:
    """Both abandon a branch, and until v0.1.159 both were the same silence.
    Only one of them is the solver's own limit deciding the answer, so only
    one of them can be reported — and it can only be reported if the two are
    told apart in the first place.

    ``BranchState.passes`` is what tells them apart, and it needs no new
    field: a branch cut by the backstop used every pass it had, a branch
    that stalled stopped short of it.
    """

    def test_a_wandering_branch_is_cut_well_before_the_backstop(self):
        from ogr_slip2d.interslice import MAX_PASSES
        state = _moment_branch(_system(), WANDERING_LAMBDA, 1e-10)
        assert state is not None
        assert state.converged is False
        assert state.passes < MAX_PASSES, state.passes

    def test_a_branch_cut_by_the_budget_used_every_pass_it_had(self):
        state = _moment_branch(_system(), ROOT_LAMBDA, 1e-10, max_passes=10)
        assert state is not None
        assert state.converged is False
        assert state.passes == 10, state.passes

    def test_only_the_budget_kind_is_counted(self):
        """``n_thrust_rejected`` and ``n_passes_exhausted`` say opposite
        things — one is about the stress state, the other about the solver —
        so a stalled branch must not raise the second."""
        system = _system()
        system.branches(WANDERING_LAMBDA)
        assert system.n_passes_exhausted == 0, system.n_passes_exhausted


# ======================================================================
class TestTheBackstopIsBoundedOnPurpose:
    """A large backstop is not free, and the reason is not iteration cost.

    ``E`` and ``X`` are not clamped the way ``F`` is, so a divergent branch
    grows them geometrically until ``math.fsum`` is handed -inf and +inf
    together and raises out of ``compute_fos``. Measured while choosing this
    number: with the stall test removed and the ceiling forced up, that
    ValueError appears on ``006-xstabl-1999-min-depth`` at 2000 passes and
    on ``003-acads-1c`` at 5000, at the SHIPPED tolerance, with none at 500
    or below. The old 80 was doing that job as well and said so nowhere.
    """

    def test_the_backstop_stays_in_the_band_that_was_measured_safe(self):
        from ogr_slip2d.interslice import MAX_PASSES
        assert MAX_PASSES <= 500, MAX_PASSES

    def test_it_is_still_above_what_the_slowest_real_branch_needs(self):
        from ogr_slip2d.interslice import MAX_PASSES
        state = _moment_branch(_system(), 1.5, 1e-10)
        assert state is not None and state.converged
        assert state.passes < MAX_PASSES, (state.passes, MAX_PASSES)

    def test_an_abandoned_branch_still_comes_back_finite(self):
        """Whichever of the two abandons it. A state carrying an infinity
        would move the failure downstream instead of ending it here."""
        for lam in (WANDERING_LAMBDA, ROOT_LAMBDA):
            state = _moment_branch(_system(), lam, 1e-14, max_passes=120)
            if state is None or state.converged:
                continue
            assert all(math.isfinite(v) for v in state.boundary_e), lam
            assert all(math.isfinite(v) for v in state.boundary_x), lam
            assert math.isfinite(state.fos), lam


# ======================================================================
class TestTheFallbackSaysWhatItIsWithoutVetoingIt:
    """The second mouth of D63, and the design that decides how it is shut.

    When no bracket is found the method returns the sampled lambda whose two
    factors are closest. Until v0.1.159 it said NOTHING about that whenever
    the residual was under a fixed 0.02 — ``converged=True``, empty
    ``error_message``, empty ``reason`` — which at a tolerance of 1e-6 is
    twenty thousand times what was asked for.

    The obvious repair is to make that boundary the caller's tolerance, and
    THIS FILE EXISTS PARTLY TO RECORD THAT IT IS WRONG. It was implemented
    and measured: ``converged`` feeds ``is_valid``, which
    ``search.surface_score`` scores at infinity, so tightening it converts a
    silent lie into a silent VETO — defect D37/C1, which v0.1.130 was written
    to fix. On the Ej_1 block search it moved the reported critical from
    0.654746 to 1.841807 and silently disabled the m-alpha post-filter.

    So the boundary stays and the SILENCE is what gets fixed, through
    ``details`` and a note, neither of which vetoes anything.
    """

    BETA = 45.0

    def _fallback(self, tolerance):
        from ogr_core.support import ForceApplication
        r = _result("spencer", _anchored(ForceApplication.PASSIVE),
                    tolerance, beta_deg=self.BETA)
        details = r.details or {}
        assert details.get("lambda_search_fell_back") is True, tolerance
        return r, details

    def test_the_boundary_is_not_the_tolerance_and_is_named(self):
        from ogr_slip2d.interslice import FALLBACK_RESIDUAL_LIMIT
        r, details = self._fallback(1e-3)
        assert details["lambda_residual"] >= details["lambda_tolerance"]
        assert details["lambda_residual"] < FALLBACK_RESIDUAL_LIMIT
        assert r.converged is True, "the boundary is not the tolerance"

    def test_and_yet_it_says_so(self):
        """Which is the whole repair: the answer stays usable and stops
        being silent about what it is."""
        from ogr_slip2d.analysis_runner import lambda_fallback_notes
        r, details = self._fallback(1e-3)
        notes = lambda_fallback_notes(r)
        assert notes, "a fallback above the tolerance has to be reportable"
        assert "%.3g" % details["lambda_residual"] in notes[0], notes[0]
        assert "%.3g" % details["lambda_tolerance"] in notes[0], notes[0]

    def test_the_residual_is_published_either_way(self):
        """A number the user cannot see is a number they cannot act on, and
        this path published none at all."""
        for tol in (1e-3, 5e-3):
            _r, details = self._fallback(tol)
            assert details["lambda_residual"] > 0.0
            assert details["lambda_tolerance"] == tol

    def test_a_residual_past_the_boundary_is_still_a_refusal(self):
        """The veto that DOES exist has not moved either: past the boundary
        the surface is not an answer and says so in ``error_message``."""
        from ogr_slip2d.interslice import FALLBACK_RESIDUAL_LIMIT
        r = _result("spencer", _bare(), 1e-6, beta_deg=55.0)
        details = r.details or {}
        if not details.get("lambda_search_fell_back"):
            return
        if details["lambda_residual"] < FALLBACK_RESIDUAL_LIMIT:
            return
        assert r.converged is False
        assert r.error_message, "a refusal with no reason is the defect"


# ======================================================================
class TestTheFallbackStillCompetesForTheMinimum:
    """The tripwire that would have caught the wrong repair, and the reason
    it is worth its cost.

    v0.1.130 made the difference explicit: ``error_message`` is a VETO, it
    feeds ``is_valid`` and ``surface_score`` scores it at infinity, while
    ``admissible`` is a PREFERENCE that keeps a surface out of the critical
    pick only while other surfaces exist. Defect D37/C1 is what happens when
    the two are confused — verification problems 60, 90 and 93 published a
    search minimum ABOVE the factor the same engine computes on the manual's
    own circle, because that circle was solved and then erased.

    Anything that widens what counts as "not converged" walks straight into
    that, and nothing in the suite was watching the two numbers below
    together. Measured while writing this file: making the fallback verdict
    follow the tolerance took the reported critical from 0.654746 to
    1.841807 and took the m-alpha filter's inadmissible count from 3 to 0.
    """

    def _search(self, check_m_alpha):
        import sys
        from pathlib import Path
        root = str(Path(__file__).resolve().parent)
        if root not in sys.path:
            sys.path.insert(0, root)
        from test_slide_validation_ej1 import _ej1_project
        from ogr_slip2d import Spencer
        from ogr_slip2d.search import BlockSearch
        return BlockSearch(method=Spencer(), num_surfaces=120, num_slices=18,
                           seed=0, check_m_alpha=check_m_alpha).run(
                               _ej1_project())

    def test_the_unfiltered_minimum_is_the_low_one(self):
        """Not a snapshot: the claim is that the surfaces the m-alpha check
        exists to flag are still IN the evaluation, which is only visible as
        a minimum well below the filtered one."""
        base = self._search(False)
        assert base.critical is not None
        assert base.critical.fos < 0.8, base.critical.fos

    def test_the_m_alpha_filter_still_has_something_to_flag(self):
        """Rule 7 for a check rather than for a setting: a filter whose
        targets are vetoed before it runs has stopped doing anything, and
        that is invisible in every number except this count."""
        checked = self._search(True)
        assert checked.inadmissible_count > 0, checked.inadmissible_count

    def test_and_the_filter_moves_the_answer(self):
        base = self._search(False)
        checked = self._search(True)
        assert checked.critical.fos > base.critical.fos
        assert checked.valid_count == base.valid_count, (
            "the check marks surfaces, it does not drop them")


# ======================================================================
class TestTheNoteIsReachableAndSaysOnlyWhatItMeans:
    """A note that cannot fire is worse than no note, so this pins that it
    can — on the 55 degree plane, unreinforced, where Spencer at 1e-10 loses
    exactly one lambda to the backstop and then finds no bracket.

    And it pins the two conditions, because either alone would be noise: a
    lambda lost with a bracket still found changes nothing, and a fallback
    with no lambda lost is the honest "this surface has no root".
    """

    def test_it_fires_where_it_was_measured_to_fire(self):
        from ogr_slip2d.analysis_runner import lambda_fallback_notes
        r = _result("spencer", _bare(), 1e-10, beta_deg=55.0)
        details = r.details or {}
        assert details.get("lambdas_lost_to_budget", 0) > 0, details
        assert details.get("lambda_search_fell_back") is True, details
        notes = lambda_fallback_notes(r)
        assert any("budget of passes" in n for n in notes), notes

    def test_it_stays_quiet_when_the_search_found_its_bracket(self):
        from ogr_slip2d.analysis_runner import lambda_fallback_notes

        class _Fake:
            details = {"lambda_search_fell_back": False,
                       "lambdas_lost_to_budget": 7}
        assert lambda_fallback_notes(_Fake()) == []

    def test_it_stays_quiet_when_nothing_was_lost_to_the_budget(self):
        from ogr_slip2d.analysis_runner import lambda_fallback_notes

        class _Fake:
            details = {"lambda_search_fell_back": True,
                       "lambdas_lost_to_budget": 0}
        assert lambda_fallback_notes(_Fake()) == []

    def test_it_avoids_the_three_substrings_the_bank_reserves(self):
        """The verification bank decides whether D40 is still closed by
        reading the text of the warnings, and three substrings are spoken
        for. The ban is wider than it looks: "unstable" contains "stable"
        and "ahead" contains "head", so the test is on the raw text and on
        its lowercase form."""
        from ogr_slip2d.analysis_runner import lambda_fallback_notes

        class _Fake:
            details = {"lambda_search_fell_back": True,
                       "lambdas_lost_to_budget": 2}
        for note in lambda_fallback_notes(_Fake()):
            for text in (note, note.lower()):
                assert "edge of the search grid" not in text
                assert "path_optimize" not in text
                assert not ("stable" in text and "head" in text)

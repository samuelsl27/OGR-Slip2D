# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The General Limit Equilibrium inter-slice force recursion.

Reference:
    Fredlund, D.G. & Krahn, J. (1977). "Comparison of slope stability
        methods of analysis." Can. Geotech. J. 14(3), 429-439.
    Fredlund, D.G., Krahn, J. & Pufahl, D.E. (1981). "The relationship
        between limit equilibrium slope stability methods." Proc. 10th
        Int. Conf. Soil Mech. Found. Engng., Stockholm, Vol. 3, 409-416.
    Spencer, E. (1967). "A method of analysis of the stability of
        embankments assuming parallel inter-slice forces." Geotechnique
        17(1), 11-26.
    Morgenstern, N.R. & Price, V.E. (1965). "The analysis of the stability
        of general slip surfaces." Geotechnique 15(1), 79-93.

Spencer and GLE/Morgenstern-Price share every line of this module and differ
in ONE thing: the shape function f(x) that modulates the inter-slice force
ratio along the surface (f = 1 everywhere is Spencer). Keeping the two in one
place is not tidiness — it is what makes the identity "GLE with a constant f
IS Spencer" true by construction instead of by inspection.

THE TWO EQUATIONS
-----------------
Each slice carries a horizontal inter-slice force E and a vertical one X on
each of its two vertical faces, tied by the defining assumption

    X_i = lam * f(x_i) * E_i        X_0 = X_n = 0  (both ends are free)

Vertical equilibrium of the slice gives the base normal,

    N   = [ W + (X_R - X_L) - (c'*l - u*l*tanphi')*sen(a) / F ] / m_a
    m_a = cos(a) + sen(a) * tanphi' / F

and horizontal equilibrium of the slice gives the recursion that carries E
from one boundary to the next,

    E_i = E_{i-1} - N*sen(a) + (S/F)*cos(a) - H_i
    S   = c'*l + (N - u*l)*tanphi'                  ( = F * S_mobilised )

with H_i the net EXTERNAL horizontal load on the slice, signed positive when
it drives the mass down-slope.

The factor of safety comes out twice, once from each equilibrium condition:

    F_f = SUM S*sec(a)  /  SUM [ (W + X_R - X_L)*tan(a) + H ]
    F_m = SUM S  /  SUM (driving moments)          (a circle; off one, see
                                                    :mod:`moment_balance`)

and the method's answer is the lambda where the two agree.

WHY F_f IS WRITTEN WITH sec(a), which is the whole of one old defect. Global
horizontal equilibrium is ``SUM N*sen(a) = SUM (S/F)*cos(a) - SUM H``.
Substituting ``N*sen(a) = (W + dX)*tan(a) - (S/F)*sen(a)^2/cos(a)`` and
collecting,

    SUM [ (W + dX)*tan(a) + H ] = (1/F) * SUM S * (cos(a) + sen(a)^2/cos(a))
                                = (1/F) * SUM S * sec(a)

At lambda = 0 that expression is Janbu simplified term for term, because
``n_a = cos(a) * m_a``. Until v0.1.106 this program wrote ``S*cos(a)`` here,
which is smaller by ``cos(a)^2`` per slice — a factor of two on a 45-64 degree
slope.

WHY EACH BRANCH GETS ITS OWN F, which is the whole of another one. F_f and F_m
are two INDEPENDENT fixed points: the m_a inside F_m has to be evaluated at
F_m itself, or the moment branch is not the moment factor of safety of
anything. Until v0.1.106 both branches shared one iterate, ``F = (F_f+F_m)/2``,
and ``F_m(lambda=0)`` came out 2-4 % short of Bishop for that reason alone —
not, as was recorded for two versions, because m_a lacks lambda. At lambda = 0
there IS no inter-slice shear, so an m_a without lambda is correct there. See
``docs/audits/spencer_gle_interslice_v179.md``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence

from .external_forces import slice_forces
from .methods.bishop import BishopSimplified


#: The window the fixed points are clamped to. It is the SAME band the
#: lambda search accepts a branch in (``spencer.py`` and ``gle.py`` keep a
#: sample only when both branches land inside it), and keeping the two the
#: same is not tidiness: while the iterate was clamped to [0.2, 10] and the
#: search accepted (0.05, 50), a surface whose factor of safety sat above 10
#: pinned itself to the ceiling and reported it as an answer.
F_MIN = 0.05
F_MAX = 50.0


#: How many consecutive passes a branch may fail to beat its own smallest
#: step ``|f_new - F|`` before it is called WANDERING rather than slow. This
#: is not a budget: a contraction drives that step down without a floor,
#: however slowly, while an iterate that has fallen into a limit cycle never
#: beats its record again.
#:
#: IT IS NOT A PERFECT SEPARATOR AND SAYING SO IS THE POINT. An accidental
#: small step early on sets a record the genuine contraction then has to
#: beat: on the 50 degree plane the moment branch at lambda = 2.0 drops far
#: on pass 5 by luck, so it is abandoned on pass 85 rather than converging on
#: pass 468. That is not a regression — the ceiling this replaces threw the
#: same branch away on pass 80 — but it is the honest limit of the criterion,
#: and it has the same root as the defect where a branch reports convergence
#: in two passes at a loose tolerance and diverges at a tight one.
#:
#: WHY COUNTING PASSES WAS THE WRONG INSTRUMENT, which is the whole of D63.
#: The 80 this replaces had a sound reason, written in
#: :meth:`GLESystem.branches`: on the Duncan and Wright buoyant polyline the
#: branches "were still wandering after 80 passes" and the pair they stopped
#: on crossed, so the outer search took it for a root and returned 1.051
#: where the answer is 1.60. The reason was right; the instrument conflates
#: two things. The moment branch converges LINEARLY with a ratio that tends
#: to 1 as lambda grows — measured on the 50 degree plane with 50 slices at
#: a tolerance of 1e-10: 53 passes at lambda = 0, 171 at the root 1.2269 and
#: 468 at 2.0 — so the set of lambdas that fit inside 80 passes SHRANK as
#: the tolerance was tightened. The bracket was lost, the reserve path of
#: ``spencer.py`` returned the nearest grid node, and Spencer answered that
#: wedge with 0.96866 against a closed form of 0.94198. Tightening the
#: tolerance moved the answer AWAY from the exact one, forty times over.
#:
#: WHY 80, AND IT IS A PROOF RATHER THAN A NOD TO THE OLD NUMBER. ``stall``
#: cannot exceed the pass index, so it cannot reach 80 before pass 81: the
#: first 80 passes of the loop below are those of v0.1.158 instruction for
#: instruction, and every branch that converged then converges now to the
#: same F in the same number of passes. Measured as well as proved: 1040
#: comparisons of ``fos``, ``converged``, ``error_message`` and lambda over
#: the seven cases in ``validacion/casos/`` at both shipped tolerances, zero
#: moved.
STALL_PATIENCE = 80

#: The residual ``|F_f - F_m|`` below which the "no lambda-bracket" fallback
#: of ``spencer.py`` and ``gle.py`` still counts its answer as usable. It is
#: NOT the caller's ``tolerance`` and it is deliberately looser, which is the
#: opposite of what it looks like it should be, so here is the measurement
#: that decided it.
#:
#: v0.1.159 tried exactly that — ``settled = residual < self.tolerance`` — on
#: the grounds that a fallback calling itself converged with a residual
#: twenty thousand times the requested tolerance is a reserve value wearing
#: the clothes of an answer. The reasoning was right and the consequence was
#: worse than the defect. ``converged`` feeds ``LEMResult.is_valid``, which
#: ``search.surface_score`` scores at infinity, so tightening this turns a
#: silent LIE into a silent VETO — and that is D37/C1, which v0.1.130 was
#: written to fix: verification problems 60, 90 and 93 published a search
#: minimum ABOVE the factor the same engine computes on the manual's own
#: circle, because that circle was solved and then erased. Measured on the
#: Ej_1 block search, 120 surfaces, seed 0: valid surfaces 48 -> 43 and the
#: reported critical 0.654746 -> 1.841807, a 181 % move on the unsafe side.
#: It also silently disabled the m-alpha post-filter, whose inadmissible
#: count went 3 -> 0 because the surfaces it flags were vetoed before it ran.
#:
#: WHERE 0.02 COMES FROM, which nothing in this repository said until
#: v0.1.175 (D120). It is not derived, it never was, and the honest form of
#: that sentence is the history rather than a shrug. The first Spencer this
#: project had wrote ``converged = abs(g) < 0.01`` inline, in ``spencer.py``
#: and ``gle.py`` alike, with no comment of any kind. v0.1.13 rewrote both
#: methods FROM SCRATCH against Fredlund and Krahn (1977) — four named bugs,
#: a bracket grid widened to [-1.5, +1.5], a validation table — and somewhere
#: inside that rewrite the threshold was DOUBLED to 0.02, in both files at
#: once. Its changelog documents the rewrite bug by bug and never mentions
#: the threshold: the only 0.01 anywhere in it belongs to a unit-conversion
#: table. So the number has a birth certificate and no derivation, and the
#: ``git log -S`` that looks for one stops at the first public commit,
#: which is later than the change it is looking for.
#:
#: Nor is there a published one to borrow. The reference formulation's
#: iteration parameters are the m-alpha check (Whitman and Bailey 1967),
#: the bounds on lambda, the initial trial factor, the largest change in F
#: allowed per iteration, a minimum F and Steffensen — and no acceptable
#: residual of any kind. Its published error codes have none for "no lambda
#: root" either: a convergence failure is about the factor-of-safety
#: iteration, and a surface that cannot be solved is simply refused. The
#: fallback below is a THIRD state that formulation does not have, which is
#: why nothing outside this file can say what this number should be.
#:
#: WHAT IT COSTS, counted on the verification bank in v0.1.175 because
#: until then nothing counted it at all: 41 of 229 Spencer/GLE rows publish
#: a minimum found down this path, in 11 problems, and every one of those 41
#: is UNDER this limit and therefore reported as converged — they compete,
#: and they win, in silence. Their residuals reach 0.02 itself, which is 200
#: times the tolerance those runs asked for.
#:
#: And the count is what confirms the v0.1.130 decision rather than merely
#: restating it. Excluding them from the preferred pool, recomputed over the
#: same evaluations, moves the reported minimum UP every single time it
#: moves at all — 24 of 32 rows measured, between 1.6 % and 15 % — while a
#: row whose critical surface did not come from this path does not move by
#: one digit, which is the control. Against the manual's own published
#: factors it is a WASH: 8 rows get closer and 9 get further. Problems 90
#: and 93 make the point on their own — same family, same mechanism,
#: OPPOSITE directions: excluding takes 90 from -10.1 % to +1.5 % of its
#: published factor and 93 from +4.3 % to +12.2 %. So there is no evidence
#: that these minima are artefacts to be filtered out; they are simply the
#: lower ones, and dropping them would publish a less conservative answer
#: for no measured gain. The census is ``_auditoria/RESERVA_LAMBDA_*.md``
#: in the verification bank.
#:
#: So the boundary stays where it was and gets a name and a reason instead.
#: What WAS wrong is that the residual was never reported: the result said
#: "converged" and nothing else, and the user had no way to tell a solved
#: root from the nearest sample. That is fixed where it belongs, in
#: ``details`` and in ``analysis_runner.lambda_fallback_notes``, neither of
#: which vetoes anything.
FALLBACK_RESIDUAL_LIMIT = 0.02

#: Backstop for a branch that keeps beating its own record, indefinitely, by
#: less and less, and so never stalls. It is NOT unreachable and it would be
#: wrong to write that it is: the unreinforced 55 degree plane of the wedge
#: fixture, Spencer at a tolerance of 1e-10, loses exactly one lambda to it.
#: Exhausting it means the same as stalling out — ``converged=False``, and
#: the lambda disappears — but the two are told apart by
#: ``BranchState.passes``, because only this one can move the answer with
#: nothing whatever wrong with the slope. See ``n_passes_exhausted``.
#:
#: It was kept LOW until v0.1.171 for a reason that has moved elsewhere, and
#: the history is worth keeping because the reason was sound and the
#: attribution was not. ``E`` and ``X`` were not clamped the way ``F`` is, so
#: in a divergent branch they grew geometrically with nothing whatever
#: watching them, and v0.1.159 recorded a ``ValueError: -inf + inf in fsum``
#: out of ``compute_fos`` when the ceiling went to 2000 on
#: ``006-xstabl-1999-min-depth`` and to 5000 on ``003-acads-1c``, with zero
#: failures anywhere at 500 or below. That measurement was taken with the
#: AUTO-SIZING branch solver it was evaluating, which is not what ships, and
#: v0.1.171 could not reproduce the exception on the published solver in
#: 2960 direct calls at those same ceilings — the runaway is real, the
#: particular exception it ends in is luck. What v0.1.159 also wrote here
#: and got backwards is that "the stall test is what actually prevents it":
#: its own sentence before that one measures the overflow WITH the stall
#: test in place, so the stall test was not the first lock. This ceiling
#: was, and it never said so.
#:
#: :data:`THRUST_SCALE_LIMIT` is the lock now, and it watches the thing that
#: runs away instead of the number of passes it takes to do it. This
#: constant goes back to being what its first paragraph says it is: a
#: backstop for a branch that keeps beating its own record by less and less.
#:
#: v0.1.173 (D117) — and since it is no longer a lock it can be RAISED by the
#: user, so this number now plays two roles: the backstop when nothing is
#: configured, and the FLOOR under what ``max_iterations`` can buy. See
#: :func:`branch_budget` for why those are deliberately the same number and
#: not two constants.
MAX_PASSES = 400


#: How many times the total driving force of the sliding mass the inter-slice
#: thrust may reach before the branch is abandoned as a runaway. Defect D118.
#:
#: NOT A GEOTECHNICAL FORMULA — a numerical guard, and the number is a
#: measurement. ``max|E|`` divided by :func:`_force_scale`, over a census of
#: 64 systems at 16 lambdas, both branches and three tolerances:
#:
#:   * every branch that is a SOLUTION peaks at 0.16 or under, and that
#:     includes the slow ones this package fought for in v0.1.159 — the 50
#:     degree plane at the root 1.2269 needs 254 passes at 1e-14 and peaks at
#:     0.035, and at lambda = 2.0 it needs 702 and peaks at 0.065;
#:   * a runaway crosses 1 and does not come back: the same plane at
#:     lambda = 2.5 with the stall test out of the way runs 0.021, 0.12,
#:     0.45, 4.1e21, 2.6e70, 6.3e216 over passes 10, 50, 100, 200, 400, 1000.
#:
#: So the two families are separated by two hundred decades and not by one,
#: and 10 sits 60 times (1.8 decades) above the worst branch that is an
#: answer. It is the TIGHTEST value that keeps that margin rather than the
#: loosest that is safe, because the looser it gets the more of the runaway
#: it lets through: 10, 100, 1000 and 1e6 all move zero factors of safety
#: over 113 circles and two methods, so nothing but the margin decides it.
#:
#: AND THE ZERO IS NOT VACUOUS, which is the measurement that matters. Over
#: those 113 circles the guard FIRES 8 times in 5206 branch solves, four of
#: them on branches that report ``converged=True`` carrying a thrust up to
#: 5.1e31 times the weight of the mass — states the lambda search consumed
#: as though they were measurements, because :func:`thrust_is_admissible`
#: asks the SIGN of the thrust and never its size.
THRUST_SCALE_LIMIT = 10.0


#: v0.1.176 (D125) — the relaxation RESCUE of :func:`solve_branch`, and the
#: lower of the two bounds on the relaxation it may use.
#:
#: WHAT IT IS FOR. The ordinary update ``F = 0.5*(F + f_new)`` is a damped
#: Picard iteration, and a damped Picard iteration has a flip: where the
#: slope f'(F) of the fixed-point map crosses -3 the iterate stops
#: converging and settles on a period-2 cycle instead, with the fixed point
#: it was after sitting UNTOUCHED between the two phases. Measured on the
#: published Spencer circle of verification problem 091 at 50 slices: the
#: force branch converges up to lambda 0.3669 and cycles between 0.9138 and
#: 1.1163 at lambda 0.4, from every start value tried and at every budget
#: from 400 to 80 000 passes (the phase it stops on is decided by the
#: PARITY of the budget). The root of F_f = F_m sits at lambda 0.3677,
#: exactly where the cycle opens, so the outer search only ever saw the
#: negative half of F_f - F_m and answered "no lambda-bracket" for sixteen
#: versions; the branch left through the stall test, which no counter
#: reported. Same mechanism on the published arc of problem 059 at
#: lambda 1.0 and on the slow moment branch of the 50 degree plane at
#: lambda 2.0, whose fixed point 0.83037 the stall test abandoned at pass 85.
#:
#: WHAT IT DOES. From the pass after :data:`STALL_PATIENCE`, a branch that
#: is still moving by more than the tolerance is continued with the
#: relaxation of Wegstein (1958), "Accelerating convergence of iterative
#: processes", Comm. ACM 1(6) 9-13: ``F = F + omega*(f_new - F)`` with
#: ``omega = 1/(1 - s)``, ``s`` the secant slope of the map through the
#: last two iterates. The ordinary update IS this rule with omega fixed at
#: 0.5, which is why its flip sits at s = -3; the secant value cancels the
#: local slope whatever it is, so ONE rule damps a cycle (s under -3, omega
#: under 0.25) and extrapolates a crawl (s near 1, omega above 1). Only F is
#: relaxed; the thrust X keeps its own update, and that is measured rather
#: than chosen: relaxing X with the same omega made the accepted F depend
#: on the start value by 1.5e-3 on the 091 branch and killed a branch
#: outright. Acceptance inside the rescue is two consecutive passes with the
#: residual of F AND the residual of X under the tolerance, not the
#: contraction test: a relaxed iteration is not damped, so its steps have no
#: reason to shrink monotonically, and a lucky small step is followed by a
#: large one while two in a row are not luck. The thrust residual is what
#: closes the door D116 measured — F sitting at the fixed point OF THE
#: CURRENT X while X is still far from its own.
#:
#: THE BOUNDS. A secant read off two iterates can say anything, so omega is
#: clamped. Measured on the problem-091 circle, on the published arc of
#: problem 059 and on the wedge ladder of ``tests/test_janbu_wedge_v1142``
#: at three tolerances: [0.1, 5], [0.05, 20] and [0.02, 100] give the same
#: roots to 1e-7 and the same total pass count within 0.1 %; a FIXED omega
#: of 0.25, the value that undoes the flip, cannot settle the moment branch
#: of the 50 degree plane at lambda 2.0 inside 400 passes at 1e-10 and
#: costs 7 % more passes, because a crawl needs extrapolation and not
#: damping. [0.1, 5] is the tightest of the three that passes everything:
#: 0.1 undoes a flip down to f' = -9 and 5 extrapolates a crawl up to
#: s = 0.8. Over the ladder the rescue costs -1.0 % passes: it converges
#: the slow branches faster than the damping did.
#:
#: WHAT IT DOES NOT TOUCH, said out loud because promising more than a
#: change delivers is what cost this project two versions in v0.1.82-84.
#: The first STALL_PATIENCE passes of every branch are those of v0.1.175
#: instruction for instruction, so a branch that converges inside them
#: cannot move. A branch whose last step is already under the tolerance is
#: left to the ordinary acceptance: taking it over changes the pass it is
#: admitted on, and with it the digit — problem 091 at 30 slices pins
#: 0.9641378773625315 bit for bit and stays. The thrust bound of D118 fires
#: before and regardless, the budget is the same MAX_PASSES, and a branch
#: the rescue cannot settle leaves through the same stall test as before,
#: now counted (``GLESystem.n_stalled``). What it cannot do is reach a
#: branch the thrust bound cuts first: the force branch of verification
#: problem 085 dies of thrust overflow from lambda 1.51 on, with or without
#: the rescue, and that problem stays where it was.
RESCUE_OMEGA_MIN = 0.1

#: The upper bound of the same relaxation; see :data:`RESCUE_OMEGA_MIN`.
RESCUE_OMEGA_MAX = 5.0

#: The switch, read at call time inside :func:`solve_branch` so that a test
#: can turn the rescue off in-process and measure what it changes against
#: what it leaves alone (the ``_lifted`` idiom of
#: ``tests/test_interslice_thrust_bound_v1171.py``). Off, the branch solver
#: is v0.1.175 bit for bit.
BRANCH_RESCUE = True

#: v0.1.179 (D145) — the two halves of the acceptance this version changes,
#: each with its own switch and for the same reason ``BRANCH_RESCUE`` has
#: one: an A/B that moves two things at once attributes neither. Read at
#: call time so a test can turn either off in-process.
#:
#: ``BRANCH_PAIR_TIGHTEN`` refuses an acceptance while the thrust is still
#: moving by more than the tolerance. It can only ever REFUSE, never admit,
#: so with it alone no branch converges sooner than it did. Measured on the
#: bench: the branch of verification problem 087 under GLE at lambda 3.0 is
#: admitted on pass 45 with a thrust residual of 885 times the tolerance and
#: its thrust still growing — a beat node of an iteration that diverges, and
#: pass 45 is far enough ahead of ``STALL_PATIENCE`` that the rescue, which
#: has had this gate since v0.1.176, never sees it.
#:
#: ``BRANCH_PAIR_SETTLE`` admits a branch whose two residuals have both been
#: under the tolerance for two consecutive passes, without asking the
#: contraction test for two shrinking steps. It can only ever ADMIT, never
#: refuse. It exists because a converging branch need not contract
#: monotonically: on the published circle of problem 091 at 30 slices the
#: force branch alternates — 6.10e-4, 6.22e-4, 3.18e-4, 3.26e-4, 1.65e-4,
#: 1.71e-4 — with the envelope halving every two passes and
#: ``step < prev_step < prev_step_2`` therefore never true. That branch sits
#: on its answer from pass 21 and is admitted on pass 107, when the pattern
#: finally breaks by rounding; at a neighbouring lambda it is never admitted
#: at all and the sample is lost to the stall test.
#:
#: Why BOTH and not one rule. The contraction path admits a cleanly
#: contracting branch one pass EARLIER than two-consecutive can, so keeping
#: it is what leaves those branches where they were: measured over the
#: bench, the pass a branch is admitted on does not move unless the thrust
#: gate refuses it. And the second path cannot be given the first one's
#: three-pass floor by accident — hence ``_pass > 1`` below, which is not a
#: number but the rule that a new way in may not cost LESS history than the
#: one it is added to. Without it, the wedge of 50 degrees at lambda 0 and
#: tolerance 5e-3 — one cell in the sixteen measured, and a cell
#: ``tests/test_branch_contraction_v1172`` sweeps — has its first two steps
#: already inside the tolerance (1.411e-3 and 1.029e-3) and would be
#: admitted on pass 2, which is the two-pass accidental acceptance D116
#: exists to refuse.
BRANCH_PAIR_TIGHTEN = True
BRANCH_PAIR_SETTLE = True


# ----------------------------------------------------------------------
def branch_budget(max_iterations: int) -> int:
    """The inner pass budget a user's ``max_iterations`` buys. Defect D117.

    v0.1.173. Until this version ``max_iterations`` reached the OUTER lambda
    secant of Spencer and GLE and nothing else, while the fixed point those
    two methods actually solve — one :func:`solve_branch` call per branch per
    lambda — ran on :data:`MAX_PASSES` with no way in from the settings. The
    name promised three loops and reached one, which is rule 7 in its
    quietest form: a control the user believes the analysis honours.

    WHY THERE IS A FLOOR AT ALL, because lowering the budget is NOT the
    mirror of raising it. Since v0.1.172 (D116) no branch can converge
    before its THIRD pass — seeing one step ratio costs two steps and seeing
    two costs three — and :data:`STALL_PATIENCE` is 80, so a budget under
    that would not trim a wasteful iteration, it would delete lambdas that
    are answers today. ``TestPatienceCannotChangeWhatAlreadyConverged`` in
    ``tests/test_interslice_budget_v1159.py`` is the executable form of that
    promise and it stays green.

    WHY THE FLOOR IS :data:`MAX_PASSES` ITSELF and not a second constant.
    Keeping them equal is what makes every stored model answer the number it
    answered before: the verification bank's 204 projects all carry
    ``max_iterations = 50``, and ``max(50, 400)`` is the 400 they already
    used, so zero moved digits here is an IDENTITY and not a measurement. A
    ``MAX_PASSES_MIN`` sitting beside ``MAX_PASSES`` would be two names for
    one number held equal by nothing but habit, and the day one of them
    moved the other would keep the reason that used to justify both.

    WHERE THIS STOPS, said out loud rather than implied, because promising
    more than a change delivers is what cost this project two versions in
    v0.1.82-84. Raising the budget only moves an answer where the ceiling
    was actually reached, and that takes a tolerance far tighter than the
    Project Settings dialog can express — its tolerance spin box floors at
    1e-6. Measured over 24 combinations of two wedge angles, both methods
    and six tolerances from 1e-5 to 1e-10, exactly ONE moved: the 55 degree
    plane under Spencer at 1e-10, where a lambda lost to the ceiling had
    pushed the answer to 2.6322 while the same solver settles on 2.59330 at
    1e-8 and at 1e-9. Reachable from a stored file and from the API; not
    from the dialog.
    """
    return max(int(max_iterations), MAX_PASSES)


# ----------------------------------------------------------------------
@dataclass(slots=True)
class SliceRow:
    """Everything about one slice that does NOT change with F or lambda.

    Resolving these once per surface rather than once per inner iteration is
    worth its own type: the lambda search calls the branch solver a dozen
    times and each call iterates, so the strength linearisation used to run
    some hundreds of times per surface for an answer that never moved.
    """

    alpha: float
    sin_a: float
    cos_a: float
    tan_a: float
    sec_a: float
    length: float          # base length l
    u: float               # pore pressure at the base midpoint
    c_l: float             # c' * l
    tan_phi: float
    w_eff: float           # total vertical downward load on the slice
    w_soil: float          # the same WITHOUT the support (moment arms)
    h_drive: float         # net external horizontal load, driving-positive
    arm_ratio: float       # slide_sign * weight_arm_ratio (circle only)
    t_active: float        # resisting tangential force, ACTIVE supports
    t_passive: float       # the same for PASSIVE supports


# ----------------------------------------------------------------------
def prepare_rows(s_list, kh: float, kv: float, slide_sign: float,
                 sup=None) -> tuple[list[SliceRow], list, list[int]]:
    """Resolve the loop-invariant part of every slice.

    ``alpha`` is flipped by ``slide_sign`` so the up-slope side is always
    positive and the driving terms always come out positive, which is the
    convention every method in this package shares.

    The rows come back in MARCHING order — from the down-slope free end
    towards the crest — which for a mass sliding towards −x is the reverse of
    the slicer's own left-to-right order. That is not cosmetic. The recursion
    starts from ``E = 0`` at a free end and accumulates; started from the
    WRONG end it produces the same factor of safety (the sum telescopes) but
    every ``E`` comes out negated, so a perfectly compressive stress state
    reads as a tensile one and :func:`thrust_is_admissible` rejects it. On the
    Prandtl surface of verification problem 26, which slides towards −x, all
    39 interior boundaries reported tension for exactly that reason.

    Returns ``(rows, forces, order)``. ``forces`` stays in SLICE order,
    because the moment side indexes it by slice; ``order[k]`` is the slice
    index of marching row ``k``.
    """
    rows: list[SliceRow] = []
    forces = []
    has_sup = sup is not None and sup.present
    for i, s in enumerate(s_list):
        fx = slice_forces(s, kh, kv)
        forces.append(fx)
        # v0.1.61 — total vertical load (soil + ponded water) is what the base
        # normal carries. v0.1.64 — a support's vertical component joins it
        # (``f_v`` is +y, ``w_eff`` is +down), so the friction it mobilises
        # falls out of the equilibrium instead of being added by hand.
        w_eff = fx.w_total
        # The external horizontal loads, all in the DRIVING sense.
        # ``h_seismic`` is a magnitude and already points down-slope;
        # ``h_water`` and the support's ``nf_h`` are signed in true +x, so
        # they take ``-slide_sign`` to land in the same frame.
        h_drive = fx.h_seismic - slide_sign * fx.h_water
        t_act = t_pas = 0.0
        if has_sup:
            # v0.1.115 — the support arrives SPLIT. Its NORMAL part is a
            # Cartesian load on the slice like ponded water: it presses the
            # base, raises N, and the friction it mobilises falls out of the
            # equilibrium as ``T_N·tan φ'`` without being added by hand. Its
            # TANGENTIAL part is not a load but a RESISTANCE on the base, and
            # it is carried separately because Active and Passive mobilise it
            # differently — see ``t_mob`` in :func:`solve_branch`. Until
            # v0.1.114 the whole resultant came in through ``f_h``/``f_v``,
            # which is the Active reading of it, and Spencer and GLE gave the
            # same number for both settings to the last digit.
            w_eff -= sup.nf_v[i]
            h_drive -= slide_sign * sup.nf_h[i]
            t_act = sup.t_active[i]
            t_pas = sup.t_passive[i]

        alpha = slide_sign * s.base_angle
        ca = math.cos(alpha)
        sa = math.sin(alpha)
        length = s.base_length
        u = s.pore_pressure
        # The strength linearisation point. Deliberately the SAME crude
        # estimate every method in this package has used since v0.1.14 —
        # ``W*cos(a) - u*l`` — and NOT the converged N of the recursion below:
        # changing it would move every non-linear material (Hoek-Brown,
        # SHANSEP, anisotropic) for a reason that has nothing to do with
        # inter-slice forces.
        sigma_est = max(0.0, w_eff * ca - u * length) / max(length, 1e-9)
        c_loc, tan_phi = BishopSimplified._local_c_phi(s, s.material, sigma_est)

        rows.append(SliceRow(
            alpha=alpha, sin_a=sa, cos_a=ca,
            tan_a=(sa / ca if abs(ca) > 1e-12 else math.copysign(1e12, sa)),
            sec_a=(1.0 / ca if abs(ca) > 1e-12 else 1e12),
            length=length, u=u, c_l=c_loc * length, tan_phi=tan_phi,
            w_eff=w_eff, w_soil=fx.w_total, h_drive=h_drive,
            arm_ratio=slide_sign * s.weight_arm_ratio,
            t_active=t_act, t_passive=t_pas,
        ))
    order = list(range(len(rows)))
    if slide_sign < 0.0:
        rows.reverse()
        order.reverse()
    return rows, forces, order


# ----------------------------------------------------------------------
@dataclass(slots=True)
class BranchState:
    """The per-slice quantities a converged branch leaves behind.

    ``abandoned`` is empty for every branch that ran to one of its three
    ordinary ends. It carries a reason when the branch was thrown away
    mid-iteration, and there is exactly one of those today — see
    :data:`THRUST_SCALE_LIMIT`. It is a field rather than a fourth
    ``return None`` because ``None`` cannot carry a reason, which is the
    whole of D56: a refusal that does not say why is a refusal nobody can
    act on. ``GLESystem.branches`` is what reads it.

    ``rescued`` (v0.1.176, D125) is True on a state that converged only
    through the relaxation rescue — see :data:`RESCUE_OMEGA_MIN`. It is a
    field and not a fifth exit because the answer it carries IS an answer;
    what it says is that the ordinary damped iteration would not have
    reached it, which is what ``GLESystem.n_rescued`` counts.
    """

    fos: float
    converged: bool
    passes: int
    normals: list[float]
    resisting: list[float]     # S = F * S_mobilised
    boundary_e: list[float]    # E at the n+1 boundaries
    boundary_x: list[float]    # X at the n+1 boundaries
    abandoned: str = ""        # why the iteration was cut, or ""
    rescued: bool = False      # converged only through the relaxation rescue


# ----------------------------------------------------------------------
def _force_scale(rows: Sequence[SliceRow]) -> float:
    """The total force this surface has to work with, as a magnitude.

    Every term that feeds the thrust recursion of :func:`solve_branch`,
    summed without its sign: the vertical load each slice carries, the
    cohesion its base can offer, the external horizontal loads and the
    reinforcement. It is a SCALE and not a bound — no equilibrium says ``E``
    has to stay under it — and it exists so that
    :data:`THRUST_SCALE_LIMIT` can be a pure number instead of a force,
    which is what ``AGENTS.md`` means by a tolerance relative to the size of
    the model rather than absolute.

    Deliberately NOT ``sum(W)`` alone, which is the obvious choice and is
    wrong for a case this package already has on record: the thin lens of
    the disjoint-mass problem carries 0.9 ft of soil and comes out at
    F = 34.3, so its weight is small and its cohesion is not. A limit
    written against ``sum(W)`` would be tight there for a reason that has
    nothing to do with the inter-slice thrust.

    Zero is a legitimate answer — a surface with no load and no strength
    anywhere — and it needs no floor: such a surface produces ``E = 0`` at
    every boundary, so ``0 <= 0`` holds and the guard never fires. Putting a
    floor here would be putting an absolute force back in.
    """
    return math.fsum(abs(r.w_eff) + r.c_l + abs(r.h_drive)
                     + abs(r.t_active) + abs(r.t_passive) for r in rows)


# ----------------------------------------------------------------------
def solve_branch(
    rows: Sequence[SliceRow],
    lam_boundary: Sequence[float],
    moment_fos,
    tolerance: float,
    initial_fos: float = 1.0,
    max_passes: int = MAX_PASSES,
    f_min: float = F_MIN,
    f_max: float = F_MAX,
    *,
    patience: int = STALL_PATIENCE,
) -> Optional[BranchState]:
    """One branch of the GLE system, iterated to its OWN fixed point.

    Args:
        rows: the output of :func:`prepare_rows`.
        lam_boundary: ``lam * f(x)`` at each of the n+1 slice boundaries. The
            two ends are ignored — a free end carries no inter-slice force.
        moment_fos: ``None`` for the FORCE branch. For the MOMENT branch, a
            callable ``(normals, resisting) -> float | None`` returning the
            moment factor of safety; the caller owns that geometry because it
            differs between a circle and a polyline.
        tolerance: convergence on F. Since v0.1.172 (D116) it is not enough
            on its own — the step has to be under it AND the iteration has
            to be CONTRACTING; see below.
        initial_fos: where the fixed point starts.
        patience: passes allowed without beating the smallest step so far
            before the branch is called wandering. See
            :data:`STALL_PATIENCE`; a value of at least 80 keeps every
            answer this function gave before v0.1.159 bit for bit.

    Returns:
        The converged :class:`BranchState`, or ``None`` if the branch is
        inadmissible (m_a collapsed, no driving term, a non-positive or
        non-finite factor of safety).

    The iteration stops on one of FOUR things and only one of them is an
    answer: the step falling under ``tolerance`` WHILE the iteration
    contracts (``converged=True``), the
    step failing to beat its own record for ``patience`` passes (wandering),
    ``max_passes`` (a backstop that IS reachable at tight tolerances), or
    the inter-slice thrust running away (v0.1.171, D118 — see
    :data:`THRUST_SCALE_LIMIT`). The last three all come back with
    ``converged=False``, which is what :meth:`GLESystem.branches` turns into
    "this lambda has no value" — see :data:`STALL_PATIENCE` for what
    conflating slow with wandering cost, and note that the fourth is the
    only one that says WHY in the state it returns, through
    ``BranchState.abandoned``.

    WHAT "CONVERGED" MEANS SINCE v0.1.172, and WHERE THE GUARANTEE STOPS,
    because promising more coverage than a guard gives is what cost this
    project two versions in v0.1.82-84. The acceptance test is the classical
    one for a contractive fixed point (Isaacson & Keller 1966, "Analysis of
    Numerical Methods", section 3.1): the step under ``tolerance`` AND the
    last two step ratios below 1. What it rules out is the step that falls
    under a loose tolerance BY LUCK in the oscillating transient of a damped
    iterate — defect D116, measured at 18 % of F on the 50 degree plane.
    What it does NOT rule out is an accepted value sitting far from the
    fixed point: a contraction of ratio r stopped on a step of ``tol``
    still sits within ``tol*r/(1-r)`` of the root, and r reaches 0.9614 on
    that same plane, so 25 times the requested tolerance is reachable.
    Adding that residual estimate to the test was measured and deliberately
    NOT adopted: it turns lambdas that give a bad number into lambdas that
    are LOST, and with ``MAX_PASSES`` where it is that is the D63 mechanism
    running backwards. See the changelog of v0.1.172.

    The X update rides the SAME pass as F rather than being iterated to
    convergence inside it. Measured back to back at a tolerance of 1e-10, the
    nested and the coupled forms agree on lambda and on F to six figures, and
    the coupled one gets there in 15 to 52 passes.

    v0.1.176 (D125) — THE RESCUE. After ``patience`` passes a branch that is
    still moving by more than ``tolerance`` is no longer left to the damped
    update that lost it: it is continued with the bounded relaxation of
    Wegstein (1958), whose secant-based omega undoes the period-2 cycle the
    damping falls into past f' = -3 and extrapolates the crawl it falls
    into near f' = 1. It creates no exit of its own — a branch the rescue
    cannot settle leaves through the same stall test — and it changes
    nothing for a branch that converges inside those ``patience`` passes or
    whose last step is already under the tolerance. The whole story, with
    the measurements, is at :data:`RESCUE_OMEGA_MIN`.
    """
    n = len(rows)
    if n == 0:
        return None
    F = max(f_min, float(initial_fos))
    X = [0.0] * (n + 1)
    normals = [0.0] * n
    resisting = [0.0] * n
    E = [0.0] * (n + 1)
    converged = False
    passes = 0
    # The smallest step seen, and how many passes have gone by without
    # beating it. See :data:`STALL_PATIENCE`.
    best_step = math.inf
    stall = 0
    # v0.1.172 (D116) — the two previous steps, for the contraction test at
    # the bottom of the loop. Two floats and not a list: this is the hottest
    # loop in the package.
    #
    # ``-inf`` and NOT ``+inf``, and the sentinel is load-bearing. With
    # ``+inf`` the chained comparison below is already true on the SECOND
    # pass, having seen a single ratio — which is exactly the two-pass
    # accidental convergence this version exists to refuse.
    prev_step = prev_step_2 = -math.inf
    # v0.1.171 (D118) — the thrust bound, resolved ONCE. It depends on the
    # rows and never on F, lambda or the pass, so evaluating it inside the
    # loop would be a per-pass sum over every slice for an answer that
    # cannot move.
    abandoned = ""
    force_scale = _force_scale(rows)
    thrust_limit = THRUST_SCALE_LIMIT * force_scale
    # v0.1.176 (D125) — the rescue's state: whether it is on, the last two
    # (F used, f_new obtained) pairs the secant slope reads, the relaxation
    # they gave, the thrust residual of the pass and whether the previous
    # pass was already inside the tolerance. Two more floats and three
    # names in the hottest loop of the package, updated once per pass; the
    # same price v0.1.172 paid for its two previous steps.
    rescuing = False
    rescued = False
    F_last = f_last = F_prev = f_prev = None
    omega = 0.5
    d_x = 0.0
    ok_before = False
    # v0.1.179 (D145) — the previous pass's thrust residual, kept
    # explicitly beside ``prev_step`` although ``d_x`` itself still holds it
    # at the top of the loop: a condition that reads ``d_x`` up there looks
    # like this pass's number and is the previous one, and a comment
    # defending a confusing read is worth less than a float.
    prev_d_x = -math.inf

    for _pass in range(max_passes):
        passes += 1
        # v0.1.176 (D125) — entry to the rescue: from the pass after
        # ``patience``, and only for a branch still moving by more than the
        # tolerance. Not before, because the first ``patience`` passes are
        # the ones every stored answer was computed with, instruction for
        # instruction (the proof STALL_PATIENCE rests on). And not for a
        # branch already under the tolerance: that one is converged in F
        # and waiting for the contraction test to admit it, and taking it
        # over would change the pass it is admitted on and with it the
        # digit — problem 091 at 30 slices pins its Spencer factor bit for
        # bit and this is what keeps it. See RESCUE_OMEGA_MIN.
        # v0.1.179 (D145) — and a branch whose F has settled while its
        # THRUST has not is taken over too. Without this it could not be
        # admitted (the gate below refuses it), could not be rescued (this
        # test used to ask only about F) and need not stall, so it ran to
        # MAX_PASSES and was counted as a branch that "was still making
        # progress when it was cut" — a fifth way out of this loop, wearing
        # the name of a fourth. The tightening creates that state, so the
        # tightening closes it: both halves answer to the same switch.
        if (BRANCH_RESCUE and not rescuing and _pass >= patience
                and (prev_step >= tolerance
                     or (BRANCH_PAIR_TIGHTEN and prev_d_x >= tolerance))):
            rescuing = True
            best_step = math.inf
            stall = 0
            ok_before = False
        if rescuing and F_prev is not None:
            # Wegstein (1958): omega = 1/(1 - s) with s the secant slope of
            # the fixed-point map through the last two iterates, which
            # cancels the map's local slope whatever it is. The ordinary
            # update below is this with omega fixed at 0.5. Bounded, because
            # two noisy iterates can give any s; and 0.5 when the iterates
            # are too close to read a slope at all.
            d_f = F_last - F_prev
            if abs(d_f) > 1e-14 * max(1.0, abs(F_last)):
                s = (f_last - f_prev) / d_f
                omega = (RESCUE_OMEGA_MAX if abs(1.0 - s) < 1e-12
                         else 1.0 / (1.0 - s))
                omega = max(RESCUE_OMEGA_MIN, min(omega, RESCUE_OMEGA_MAX))
            else:
                omega = 0.5
        e = 0.0
        # v0.1.171 (D118) — the largest |E| of THIS pass, tracked in the
        # march that is already visiting every one of them rather than in a
        # second loop over ``E`` afterwards. The two are the same number:
        # ``E[0]`` is never written and stays 0.0, and ``E[1..n]`` are the
        # successive values of ``e``. Fused because this is the hottest loop
        # in the package — Spencer and GLE cost 50 ms a circle against
        # Bishop's 12 — and a whole extra pass over n+1 floats per iteration
        # is the kind of cost that is invisible per call and hours long over
        # the verification bank.
        peak = 0.0
        for i, r in enumerate(rows):
            m_alpha = r.cos_a + r.sin_a * r.tan_phi / F
            if abs(m_alpha) < 1e-6:
                return None
            # v0.1.115 — the reinforcement on this base, at the value it is
            # MOBILISED at. An Active support is a force that is already
            # there, so it enters whole; a Passive one develops in proportion
            # to the mobilisation of everything else, so it enters at T/F
            # exactly as the soil strength does. That single line is the
            # whole of Method A versus Method B (Duncan & Wright 2005), and
            # it is why the two give different answers: substituting it into
            # the global horizontal balance below turns ``F = R/(D − T)``
            # into ``F = (R + T)/D``.
            t_mob = r.t_active + r.t_passive / F
            n_i = (r.w_eff + X[i + 1] - X[i]
                   - (r.c_l - r.u * r.length * r.tan_phi) * r.sin_a / F
                   - t_mob * r.sin_a
                   ) / m_alpha
            s_i = r.c_l + (n_i - r.u * r.length) * r.tan_phi
            normals[i] = n_i
            resisting[i] = s_i
            # Horizontal equilibrium of the slice. The external loads are
            # driving-positive, i.e. they point at -x in this frame, hence the
            # minus sign; the march closing on E_n = 0 is what global
            # horizontal equilibrium means. The reinforcement resists in the
            # same sense as the mobilised base shear, so it carries the same
            # sign here as ``s_i / F`` — and it MUST appear, or the thrust
            # this march reports is the thrust of a slope with no
            # reinforcement in it while the factor of safety below is not.
            e += (-n_i * r.sin_a + (s_i / F) * r.cos_a
                  + t_mob * r.cos_a - r.h_drive)
            E[i + 1] = e
            ae = abs(e)
            if not (ae <= peak):        # also True when ae is NaN
                peak = ae

        # v0.1.171 (D118) — THE THRUST, not the count. ``F`` is clamped to
        # [f_min, f_max] and ``f_new`` is checked for finiteness below, but
        # ``E`` had no bound at all, so a divergent branch grew it
        # geometrically with nothing watching: measured on the 50 degree
        # plane at lambda = 2.5 with the stall test out of the way, max|E|
        # runs 0.021, 0.12, 0.45, 4.1e21, 2.6e70 and 6.3e216 times
        # :func:`_force_scale` over passes 10, 50, 100, 200, 400 and 1000.
        #
        # WHY THE TEST SITS HERE, between the march and the X update, and it
        # is an argument from the order of the statements rather than a
        # measurement. ``resisting`` on pass k is built from the ``X`` of
        # pass k-1, so a branch cut at the first pass whose ``E`` crosses
        # the bound never reaches the pass that could hand a +-inf to the
        # ``math.fsum`` of the moment expression. It therefore does not
        # matter how far past the bound the runaway would have got.
        #
        # ``not (peak <= limit)`` and not ``peak > limit``: the second is
        # False for a NaN, and a NaN thrust is exactly the state this
        # refuses. ``peak`` is accumulated in the march above, and for the
        # same reason it is written as a negated ``<=`` there.
        if not (peak <= thrust_limit):
            abandoned = "thrust overflow"
            break

        # X_0 and X_n stay at zero: both ends of the surface are free.
        #
        # v0.1.176 (D125) — the thrust residual: how far the X the march
        # used sits from the X it produced, relative to the force scale like
        # the thrust bound. Nothing is accepted while this is above the
        # tolerance, because F can sit at the fixed point OF THE CURRENT X
        # while X is far from its own — the lucky step of D116 seen from the
        # other side. Fused into the update that already visits every
        # boundary, for the reason the thrust peak above is fused into the
        # march.
        #
        # v0.1.179 (D145) — measured on EVERY pass, where until now it was
        # measured only after the rescue had taken the branch over. The
        # sentence above was already written and already true; what it
        # described was half the solver. The extra work is a subtraction, an
        # abs and a comparison per interior boundary, against the ~170
        # operations a slice already costs in this same pass: about +9 % of
        # the branch solver, and 0 % of the seven methods that never enter
        # this file. It is NOT folded into the march even though the
        # arithmetic would allow it, because the thrust bound breaks out
        # BETWEEN the two on purpose and ``spencer.py`` publishes
        # ``force.boundary_x`` of abandoned states.
        d_x = 0.0
        for i in range(1, n):
            target = lam_boundary[i] * E[i]
            d = abs(target - X[i])
            if d > d_x:
                d_x = d
            X[i] = target
        if force_scale > 0.0:
            d_x /= force_scale
        # A surface with no load and no strength anywhere has a force scale
        # of zero and d_x is then left unnormalised. That is right, and the
        # reason has to be derived here rather than borrowed from
        # ``_force_scale``, whose docstring says such a surface produces
        # E = 0 everywhere and is wrong about it: with pore pressure and
        # friction but no weight, n_i and s_i are not zero. What makes the
        # gate safe is the bound above, not the scale — ``thrust_limit`` is
        # ``THRUST_SCALE_LIMIT * 0.0 = 0.0`` and it breaks out BEFORE this
        # loop, so every pass that reaches here has E identically zero, X
        # already zero and d_x exactly 0.0. The gate is trivially open,
        # never absurd.

        if moment_fos is None:
            num = 0.0
            den = 0.0
            for i, r in enumerate(rows):
                num += resisting[i] * r.sec_a
                den += (r.w_eff + X[i + 1] - X[i]) * r.tan_a + r.h_drive
                # v0.1.115 — the reinforcement, on whichever side of the bar
                # its Active/Passive flag puts it. Both carry ``sec(a)`` and
                # not ``cos(a)``, and that is not a choice: substituting
                # ``N·sen(a)`` out of global horizontal equilibrium (see the
                # module docstring) turns a base-tangential force T into
                # ``T·(cos a + sen^2 a / cos a) = T·sec(a)``, exactly as it
                # does for the base shear itself.
                #
                # For the ACTIVE case this is an IDENTITY with the treatment
                # it replaces: the old whole-resultant contribution
                # ``-f_v·tan(a) - slide_sign·f_h`` equals ``-T_S·sec(a)`` term
                # for term. The PASSIVE case is where the two part company,
                # because ``t_mob`` above divides it by F.
                if r.t_active:
                    den -= r.t_active * r.sec_a
                if r.t_passive:
                    num += r.t_passive * r.sec_a
            if abs(den) < 1e-9:
                return None
            f_new = num / den
        else:
            f_new = moment_fos(normals, resisting)
            if f_new is None:
                return None

        if not math.isfinite(f_new) or f_new <= 0.0:
            return None
        step = abs(f_new - F)
        # v0.1.172 (D116) — CONTRACTION, not a single small step. The
        # iterate is damped (``0.5*(F + f_new)`` below), so its transient
        # OSCILLATES: the steps alternate large and small, and one of the
        # small ones can fall under a loose tolerance by luck at a fixed
        # point that does not contract at all. Measured on the 50 degree
        # plane, moment branch, lambda = 2.0: the step drops to 1.8e-4 on
        # pass 5 and the branch was published as converged at F = 0.9673,
        # while its actual fixed point is 0.83037 and takes 585 passes to
        # reach at 1e-12 with the stall test out of the way. See
        # the module docstring of ``tests/test_branch_contraction_v1172.py``.
        #
        # ``step < prev_step < prev_step_2`` IS "the last two ratios
        # r_k = step_k / step_{k-1} are below 1", written without the
        # division: no zero denominator, no inf, and a NaN step makes it
        # False, which is the right verdict. That is the classical
        # acceptance test for a contractive fixed point (Isaacson & Keller
        # 1966, "Analysis of Numerical Methods", section 3.1).
        #
        # ``step == 0.0`` is the exact fixed point and it is NOT an
        # ornament: without it a branch that lands dead on its answer can
        # never beat its own zero step again, so it would iterate to the
        # stall test and lose its lambda. That is identity I5 of v0.1.141,
        # which converges with dF = 0.
        #
        # The consequence, said out loud because it is the price: NO branch
        # can converge before its THIRD pass. Seeing a ratio takes two
        # steps and seeing two takes three.
        #
        # And NO fourth counter in :class:`GLESystem`, which is a decision
        # and not an oversight: this test creates no new way out of the
        # loop, it only delays the first one, so a lambda lost to it leaves
        # through the stall test or the pass budget and is already counted
        # there. The three counters keep naming the three exits.
        contracting = step == 0.0 or step < prev_step < prev_step_2
        # Updated before the test, so that it also happens on the passes
        # that leave through one of the ``break``s below.
        prev_step_2, prev_step = prev_step, step
        prev_d_x = d_x
        # v0.1.179 (D145) — the state of this loop is the PAIR (F, X), and
        # until this version the acceptance asked about half of it. Both
        # residuals under the tolerance is what ``ok_now`` says; what the
        # three paths below differ in is how much history has to agree.
        ok_now = step < tolerance and d_x < tolerance
        if rescuing:
            # v0.1.176 (D125) — two consecutive passes with BOTH residuals
            # under the tolerance, instead of the contraction test. A
            # relaxed iteration is not damped, so its steps have no reason
            # to shrink monotonically; and the contraction test has an
            # honest limit of its own, measured on problem 091 at 30 slices,
            # where a branch sitting on its fixed point to ten figures from
            # pass 45 was admitted on pass 107, when two decreasing steps
            # that only floating-point noise decides finally came in a row.
            # The repetition stands in for the contraction: a lucky small
            # step is followed by a large one, two in a row are not luck,
            # and the thrust residual closes the door D116 measured.
            if ok_now and ok_before:
                F = f_new
                converged = True
                rescued = True
                break
        # v0.1.100 — not on the first pass; see
        # ``BishopSimplified._general_moment_fos``.
        # v0.1.179 (D145) — and not while the thrust is still moving. This
        # clause can only REFUSE: a branch that contracts cleanly with its
        # thrust already settled is admitted on exactly the pass it was
        # admitted on before.
        elif (_pass > 0 and step < tolerance and contracting
                and (d_x < tolerance or not BRANCH_PAIR_TIGHTEN)):
            F = f_new
            converged = True
            break
        # v0.1.179 (D145) — two consecutive passes with the whole state
        # inside the tolerance, for the converging branch whose steps
        # alternate instead of shrinking. ``_pass > 1`` gives this path the
        # same three-pass floor the contraction test pays for its two
        # ratios; see BRANCH_PAIR_SETTLE for the cell that proves it is
        # load-bearing. It comes AFTER the contraction clause and not
        # before, and that order is what keeps the pass counts: where both
        # could fire, contraction fires one pass sooner.
        elif BRANCH_PAIR_SETTLE and _pass > 1 and ok_now and ok_before:
            F = f_new
            converged = True
            break
        # v0.1.179 (D145) — maintained on every pass now, because the
        # path that reads it is no longer only the rescue's. A pass that
        # accepts leaves through one of the breaks above and never gets
        # here, which is what it meant inside the rescue too.
        ok_before = ok_now
        # v0.1.159 (D63) — STALLING, not budget. The step of a fixed point
        # that contracts beats its own record on every pass; the step of an
        # iterate that wanders never beats it again. Counting passes could
        # not tell the two apart, and the cost of that confusion ran in both
        # directions: it threw away slow-but-converging lambdas and it let a
        # divergent branch grind on. See :data:`STALL_PATIENCE`.
        if step < best_step:
            best_step = step
            stall = 0
        else:
            stall += 1
            if stall >= patience:
                break
        # Damped, and clamped to the window the METHOD declares it will
        # consider. Those two numbers used to disagree: the iterate was
        # clamped to [0.2, 10] while the lambda search accepts any branch in
        # (0.05, 50), so a surface whose factor of safety sits above 10 could
        # not be solved at all. It pinned itself to the ceiling and reported
        # it. On the thin lens of the disjoint-mass case (0.9 ft of soil, F =
        # 34.3 by Bishop) that was a silent 10.0 before v0.1.106 and a NaN
        # after the convergence check went in, which is how it was found.
        # v0.1.176 (D125) — the two pairs the secant reads on the next
        # pass: (F used, f_new obtained), this one and the one before.
        F_prev, f_prev = F_last, f_last
        F_last, f_last = F, f_new
        if rescuing:
            F = max(f_min, min(F + omega * (f_new - F), f_max))
        else:
            F = max(f_min, min(0.5 * (F + f_new), f_max))

    return BranchState(fos=F, converged=converged, passes=passes,
                       normals=list(normals), resisting=list(resisting),
                       boundary_e=list(E), boundary_x=list(X),
                       abandoned=abandoned, rescued=rescued)


# ----------------------------------------------------------------------
def branch_pair_ok(ff, fm) -> bool:
    """True when BOTH branches came back with a usable factor.

    v0.1.152 (D56) — the guard that used to stand at each of these twelve
    call sites was ``math.isfinite(ff) and math.isfinite(fm)``, because
    :meth:`GLESystem.branches` signalled a dead branch with ``NaN``. It
    signals it with ``None`` now, so that a value which is not a number
    cannot be added, compared or averaged by accident on its way out: the
    whole of D56 is that a NaN which survives arithmetic travels, and one
    that raises does not.

    The finiteness test is kept as well. It is redundant today —
    ``solve_branch`` already refuses a non-finite iterate — and it costs
    nothing to keep a second lock on the one door this defect came through.
    """
    return (ff is not None and fm is not None
            and math.isfinite(ff) and math.isfinite(fm))


def thrust_is_admissible(state: BranchState) -> bool:
    """Is the inter-slice thrust of this state a stress state soil can hold?

    ``E`` is the NORMAL force on a vertical face between two slices, positive
    in compression. Soil transmits no tension across such a face, so a
    solution whose faces are pulled apart is arithmetically consistent and
    physically meaningless. The test here is on the RESULTANT — the sum over
    the interior boundaries has to be compressive — rather than on every
    single face, because a legitimate solution can carry a small tensile
    thrust on one or two slices near a free end, where E is going to zero
    anyway.

    WHY THIS EXISTS AT ALL, and it is new in v0.1.106. ``F_f(lam) - F_m(lam)``
    is NOT monotone: this system has more than one root, and only one of them
    is a solution. On the Talbingo circle (verification problem 6) the outer
    search met a crossing at lam = -0.979 before the real one at lam = +0.419,
    and returned F = 1.6826 against the published 2.292. At that lam, 16 of
    the 24 interior boundaries were in tension, one of them at -63 000 kN/m;
    at lam = +0.419 every one of the 24 is in compression. On the non-circular
    problem 8 the spurious root had ALL 24 in tension.

    None of this could show up before, for a plain reason: until v0.1.106 the
    solver never formed ``E`` at all, and ``F_f - F_m`` really was monotone
    because ``F_m`` did not depend on lam.

    References:
        Spencer, E. (1967). "A method of analysis of the stability of
            embankments assuming parallel inter-slice forces." Geotechnique
            17(1), 11-26 — on the line of thrust and the admissibility of the
            inter-slice forces.
        Ching, R.K.H. & Fredlund, D.G. (1983). "Some difficulties associated
            with the limit equilibrium method of slices." Can. Geotech. J.
            20(4), 661-672 — on multiple and spurious roots of the GLE system
            and on rejecting them by the sign of the inter-slice forces.
    """
    interior = state.boundary_e[1:-1]
    if not interior:
        return True
    return math.fsum(interior) > 0.0


# ======================================================================
class GLESystem:
    """Everything ONE surface needs to answer F_f(lam) and F_m(lam).

    Built once per surface and reused for every lambda the outer search
    samples. That matters: the lambda search evaluates the pair a dozen times
    or more, and the slice geometry, the strength linearisation and the whole
    driving-moment sum are the same at every one of them.

    Spencer and GLE/Morgenstern-Price both go through this class. The ONLY
    difference between the two methods is ``shape`` — the value of f(x) at
    each slice boundary — which is why "GLE with a constant f is Spencer" is
    an identity here rather than a coincidence.
    """

    __slots__ = ("rows", "forces", "s_list", "shape", "order", "reversed_",
                 "tolerance", "initial_fos", "max_passes", "strict",
                 "n_thrust_rejected", "n_passes_exhausted",
                 "n_thrust_overflow", "n_stalled", "n_rescued",
                 "_moment_fos", "_driving")

    # v0.1.173 (D117) — ``max_passes`` goes LAST and keyword-defaulted on
    # purpose. Nine call sites build this class and every one of them passes
    # nine positionals and then names ``tolerance``/``initial_fos``, so
    # appending is the only place a new argument cannot silently land in
    # somebody else's slot.
    def __init__(self, s_list, shape: Sequence[float],
                 kh: float, kv: float, slide_sign: float,
                 circle_R, circle_yc, sup=None, axis=None,
                 tolerance: float = 1e-3, initial_fos: float = 1.0,
                 max_passes: int = MAX_PASSES) -> None:
        self.s_list = list(s_list)
        self.rows, self.forces, self.order = prepare_rows(
            self.s_list, kh, kv, slide_sign, sup)
        self.reversed_ = slide_sign < 0.0
        # ``shape`` arrives in slice-boundary order; the solver marches in
        # ``rows`` order, and boundary k of the reversed march is boundary
        # n − k of the slicer.
        self.shape = list(reversed(shape)) if self.reversed_ else list(shape)
        self.tolerance = tolerance
        self.initial_fos = initial_fos
        #: v0.1.173 (D117) — the pass budget every branch of THIS system is
        #: solved with. Held here rather than read from :data:`MAX_PASSES` at
        #: the call because it is now the user's ``max_iterations``, floored
        #: by :func:`branch_budget`; ``branches`` needs the number actually
        #: used to tell "ran out of budget" from "stalled", and the constant
        #: stopped being that number the moment it became configurable.
        self.max_passes = int(max_passes)
        # Whether an inadmissible inter-slice thrust disqualifies a lambda.
        # A PREFERENCE and not a veto: the caller turns it off and samples
        # again when nothing at all survived, so a surface that has no
        # admissible lambda still gets its number and a warning instead of a
        # NaN. See :meth:`branches`.
        self.strict = True
        #: How many lambdas the thrust criterion — and ONLY it — has thrown
        #: away. The caller re-samples with ``strict`` off when this is the
        #: reason nothing survived, and does NOT when the branches simply
        #: diverged: a surface that solves nowhere must not pay for a second
        #: sweep of the whole shape.
        self.n_thrust_rejected = 0
        #: v0.1.159 (D63) — how many lambdas were lost because a branch ran
        #: out of its pass budget while its step was still shrinking, as
        #: opposed to stalling out or being inadmissible. That budget was
        #: :data:`MAX_PASSES` until v0.1.173 (D117) made it configurable, and
        #: it is ``self.max_passes`` that this counts against: comparing to
        #: the constant once the two can differ would call a branch that
        #: stalled at 420 out of 500 "exhausted", which is precisely the
        #: conflation this counter exists to end. Kept apart from
        #: ``n_thrust_rejected`` because the two mean opposite things: that
        #: one is a statement about the stress state, this one is a
        #: statement about the SOLVER, and only this one can move the answer
        #: without anything being wrong with the slope. Until v0.1.159 the
        #: two were the same silence.
        self.n_passes_exhausted = 0
        #: v0.1.171 (D118) — how many lambdas were lost because a branch's
        #: inter-slice thrust ran away rather than because it stalled or ran
        #: out of passes. A THIRD counter and not a bigger one, for the
        #: reason the two above are already two: they are statements about
        #: different things, and this one says that the arithmetic left the
        #: range where it means anything, which is neither a statement about
        #: the stress state nor about the pass budget.
        self.n_thrust_overflow = 0
        #: v0.1.176 (D125) — how many lambdas were lost because a branch
        #: STALLED: stopped beating its own smallest step for STALL_PATIENCE
        #: passes, and the relaxation rescue could not settle it either.
        #: v0.1.159 left this exit uncounted on purpose, reading a stall as
        #: the slope's doing rather than the solver's; the published circle
        #: of verification problem 091 measured the opposite — the stall
        #: was the solver's own period-2 cycle, and it decided the answer
        #: with every counter reading zero. A fourth counter and not a wider
        #: one, for the reason the other three are three.
        self.n_stalled = 0
        #: v0.1.176 (D125) — how many lambdas came back as a usable pair
        #: only because one of their branches was rescued. The rule-7 count
        #: in the positive: a rescue that never fires is a setting that does
        #: nothing, and this is where that would show.
        self.n_rescued = 0
        self._driving = None

        if circle_R is None:
            from .moment_balance import moment_terms
            # Weights in SLICE order, which is what ``moment_terms`` walks
            # alongside ``s_list``. The SOIL weight: the support's normal part
            # is applied at its own point by ``moment_terms``, not smeared to
            # the slice's centre of gravity, and its tangential part goes
            # through ``tangential`` / ``tangential_passive``.
            weights = [0.0] * len(self.rows)
            for k, r in enumerate(self.rows):
                weights[self.order[k]] = r.w_soil
            t_act = t_pas = None
            if sup is not None and sup.present:
                t_act = list(sup.t_active)
                t_pas = list(sup.t_passive)

            def moment_fos(normals, resisting):
                terms = moment_terms(
                    axis, self.s_list, weights,
                    self.to_slice_order(resisting),
                    self.to_slice_order(normals),
                    kh=kh, kv=kv, sup=sup, tangential=t_act,
                    tangential_passive=t_pas, forces=self.forces,
                    couple=sup.couple if (sup is not None and sup.present)
                    else 0.0)
                return terms.factor_of_safety()
        else:
            # A circle divides its radius out of every term, so the whole
            # denominator is loop-invariant: it depends on the geometry and
            # the external loads, never on F, N or lambda. The inter-slice
            # forces take no part in it at all — they are internal, and each
            # pair cancels about the centre.
            from .moment_balance import slice_cg_y
            den = 0.0
            has_sup = sup is not None and sup.present
            by_slice = self.to_slice_order(self.rows)
            for i, (r, s) in enumerate(zip(by_slice, self.s_list)):
                fx = self.forces[i]
                den += r.w_soil * r.arm_ratio
                if kh > 0:
                    den += fx.h_seismic * (circle_yc - slice_cg_y(s)) / circle_R
                den += (-slide_sign
                        * fx.water_moment_about(circle_yc) / circle_R)
            # v0.1.115 — the reinforcement moment. Until v0.1.114 it was
            # reached the long way round, through the vertical component
            # riding the slice's own centre-of-gravity arm plus a separate
            # term for the horizontal one, and that arm is not the
            # support's: the two agree only where the support crosses the
            # slice's centre of gravity.
            #
            # v0.1.178 (D144) — and the sentence that stood here until this
            # version, "it needs no arm at all", was half right in a way
            # worth writing down, because the wrong half is not the one it
            # looks like. Its PREMISE is exact: a base normal force has no
            # moment about the centre, since the perpendicular bisector of
            # a chord passes through it and N acts at the midpoint. What is
            # false is the other half — that the TANGENTIAL part has an arm
            # of exactly R. It would, if the chord were the tangent of the
            # arc at the point where the support crosses; it is not, and on
            # the reference's verification problem 85 that cost 1.170 % of
            # the moment and 0.84 % of the factor of safety. So the fix is
            # not to add a normal term (the whole cross product already
            # contains it) but to take the moment where the force acts.
            m_passive = 0.0
            if has_sup:
                # v0.1.122 -- and the couple, when the resultant does not act
                # where the support crosses. Normalised like the water moment
                # in the loop above: -slide_sign*M/R.
                if sup.couple:
                    den += -slide_sign * sup.couple / circle_R
                den -= sup.moment_active
                m_passive = sup.moment_passive
            self._driving = den

            def moment_fos(normals, resisting, _den=den, _pas=m_passive):
                if abs(_den) < 1e-9:
                    return None
                return (math.fsum(resisting) + _pas) / _den

        self._moment_fos = moment_fos

    # ------------------------------------------------------------------
    def to_slice_order(self, marching: Sequence):
        """Re-index a per-slice array from marching order to slice order."""
        if not self.reversed_:
            return list(marching)
        out = [None] * len(marching)
        for k, v in enumerate(marching):
            out[self.order[k]] = v
        return out

    # ------------------------------------------------------------------
    def boundaries_in_slice_order(self, marching: Sequence[float]):
        """Re-index an n+1 boundary array from marching order to slice order."""
        return list(reversed(marching)) if self.reversed_ else list(marching)

    # ------------------------------------------------------------------
    def lambda_boundary(self, lam: float) -> list[float]:
        """``lam * f(x)`` at each of the n+1 boundaries, in MARCHING order."""
        return [lam * fb for fb in self.shape]

    # ------------------------------------------------------------------
    def states(self, lam: float):
        """``(force_branch, moment_branch)``, either of which may be None."""
        lam_b = self.lambda_boundary(lam)
        force = solve_branch(self.rows, lam_b, None,
                             self.tolerance, self.initial_fos,
                             max_passes=self.max_passes)
        moment = solve_branch(self.rows, lam_b, self._moment_fos,
                              self.tolerance, self.initial_fos,
                              max_passes=self.max_passes)
        return force, moment

    # ------------------------------------------------------------------
    def branches(self, lam: float) -> tuple:
        """``(F_f, F_m)`` at one lambda; ``None`` for a branch that failed.

        While ``strict`` is on, ``None`` is also what an INADMISSIBLE lambda
        gets —
        see :func:`thrust_is_admissible`. That matters to the outer search,
        which brackets the sign change of ``F_f - F_m``: this system has more
        than one root once the inter-slice forces are actually formed, and the
        extra ones are not solutions of anything.

        It is a PREFERENCE, not a veto, and the difference was measured. On
        the reinforced slope of verification problem 85 — 9000 kN/m of
        anchorage — the soil faces come out in net tension at EVERY lambda,
        so a veto returned nothing where v0.1.105 returned 1.568. Whether that
        tension is real or an artefact of concentrating the reinforcement is
        a question this version does not answer; turning a number into a
        refusal without answering it loses coverage for nothing. So the caller
        samples again with ``strict`` off when the strict pass found nothing,
        and says so in the result.
        """
        force, moment = self.states(lam)
        # v0.1.159 (D63) — say WHICH of the refusals this was. A branch that
        # used its whole budget was still making progress when it was cut;
        # one that stopped earlier had stalled. Both lose the lambda, but
        # only the first is the solver's own limit deciding the answer, and
        # that is the thing that has to be reportable.
        # v0.1.171 (D118) — and a third refusal, kept apart from the other
        # two. A branch cut for a runaway thrust has not used its budget and
        # has not stalled; counting it as either would make both numbers
        # mean "something went wrong" instead of what they say.
        # ``abandoned`` wins over the pass count because a branch can cross
        # the bound on its very last pass.
        # v0.1.176 (D125) — counted BEFORE the early return on a missing
        # partner, and the stall counted at last. Until this version a
        # branch that failed while the other one came back None was never
        # counted: on the published circle of verification problem 091,
        # 12 of 16 lambdas were lost with all three counters at zero, and
        # the "no lambda-bracket" the bank published rested on a stalled
        # branch that nothing reported.
        for state in (force, moment):
            if state is None or state.converged:
                continue
            if state.abandoned:
                self.n_thrust_overflow += 1
            elif state.passes >= self.max_passes:
                self.n_passes_exhausted += 1
            else:
                self.n_stalled += 1
        if force is None or moment is None:
            return None, None
        # An UNCONVERGED fixed point is not a value of F_f, and handing the
        # outer search its last iterate is worse than handing it nothing: on
        # the Duncan and Wright buoyant polyline the branches at lambda = -1.5
        # were still wandering after 80 passes, and the pair they happened to
        # stop on (1.0572, 1.0526) crossed. The outer search took that for a
        # root and returned 1.051 where the answer is 1.60. Before v0.1.106
        # this could not bite, because F_m did not depend on lambda and there
        # was only ever one crossing to find.
        if not (force.converged and moment.converged):
            return None, None
        if force.rescued or moment.rescued:
            self.n_rescued += 1
        if not thrust_is_admissible(force):
            self.n_thrust_rejected += 1
            if self.strict:
                return None, None
        return force.fos, moment.fos

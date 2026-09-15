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
#: So the boundary stays where it was and gets a name and a reason instead.
#: What WAS wrong is that the residual was never reported: the result said
#: "converged" and nothing else, and the user had no way to tell a solved
#: root from the nearest sample. That is fixed where it belongs, in
#: ``details`` and in ``analysis_runner.lambda_fallback_notes``, neither of
#: which vetoes anything.
FALLBACK_RESIDUAL_LIMIT = 0.02

STALL_PATIENCE = 80

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
    """

    fos: float
    converged: bool
    passes: int
    normals: list[float]
    resisting: list[float]     # S = F * S_mobilised
    boundary_e: list[float]    # E at the n+1 boundaries
    boundary_x: list[float]    # X at the n+1 boundaries
    abandoned: str = ""        # why the iteration was cut, or ""


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
        tolerance: convergence on F.
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
    answer: the step falling under ``tolerance`` (``converged=True``), the
    step failing to beat its own record for ``patience`` passes (wandering),
    ``max_passes`` (a backstop that IS reachable at tight tolerances), or
    the inter-slice thrust running away (v0.1.171, D118 — see
    :data:`THRUST_SCALE_LIMIT`). The last three all come back with
    ``converged=False``, which is what :meth:`GLESystem.branches` turns into
    "this lambda has no value" — see :data:`STALL_PATIENCE` for what
    conflating slow with wandering cost, and note that the fourth is the
    only one that says WHY in the state it returns, through
    ``BranchState.abandoned``.

    The X update rides the SAME pass as F rather than being iterated to
    convergence inside it. Measured back to back at a tolerance of 1e-10, the
    nested and the coupled forms agree on lambda and on F to six figures, and
    the coupled one gets there in 15 to 52 passes.
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
    # v0.1.171 (D118) — the thrust bound, resolved ONCE. It depends on the
    # rows and never on F, lambda or the pass, so evaluating it inside the
    # loop would be a per-pass sum over every slice for an answer that
    # cannot move.
    abandoned = ""
    thrust_limit = THRUST_SCALE_LIMIT * _force_scale(rows)

    for _pass in range(max_passes):
        passes += 1
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
        for i in range(1, n):
            X[i] = lam_boundary[i] * E[i]

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
        # v0.1.100 — not on the first pass; see
        # ``BishopSimplified._general_moment_fos``.
        if _pass > 0 and step < tolerance:
            F = f_new
            converged = True
            break
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
        F = max(f_min, min(0.5 * (F + f_new), f_max))

    return BranchState(fos=F, converged=converged, passes=passes,
                       normals=list(normals), resisting=list(resisting),
                       boundary_e=list(E), boundary_x=list(X),
                       abandoned=abandoned)


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
                 "tolerance", "initial_fos", "strict", "n_thrust_rejected",
                 "n_passes_exhausted", "n_thrust_overflow", "_moment_fos",
                 "_driving")

    def __init__(self, s_list, shape: Sequence[float],
                 kh: float, kv: float, slide_sign: float,
                 circle_R, circle_yc, sup=None, axis=None,
                 tolerance: float = 1e-3, initial_fos: float = 1.0) -> None:
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
        #: out of :data:`MAX_PASSES` while its step was still shrinking, as
        #: opposed to stalling out or being inadmissible. Kept apart from
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
            # v0.1.115 — the reinforcement moment, and it needs no arm at
            # all. A support resolved on the base splits into a NORMAL part,
            # whose line of action passes through the centre and whose moment
            # is therefore exactly zero, and a TANGENTIAL part, whose arm is
            # exactly R — which divides out of every term of this
            # denominator. So the whole contribution is −T_S, full stop.
            # Until v0.1.114 it was reached the long way round, through the
            # vertical component riding the slice's own centre-of-gravity arm
            # plus a separate term for the horizontal one, and that arm is
            # not the support's: the two agree only where the support crosses
            # the slice's centre of gravity.
            m_passive = 0.0
            if has_sup:
                # v0.1.122 -- and the couple, when the resultant does not act
                # where the support crosses. Normalised like the water moment
                # in the loop above: -slide_sign*M/R.
                if sup.couple:
                    den += -slide_sign * sup.couple / circle_R
                den -= math.fsum(sup.t_active)
                m_passive = math.fsum(sup.t_passive)
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
                             self.tolerance, self.initial_fos)
        moment = solve_branch(self.rows, lam_b, self._moment_fos,
                              self.tolerance, self.initial_fos)
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
            # v0.1.159 (D63) — say WHICH of the two refusals this was. A
            # branch that used its whole budget was still making progress
            # when it was cut; one that stopped earlier had stalled. Both
            # lose the lambda, but only the first is the solver's own limit
            # deciding the answer, and that is the thing that has to be
            # reportable.
            # v0.1.171 (D118) — and a third refusal, kept apart from the
            # other two. A branch cut for a runaway thrust has not used its
            # budget and has not stalled; counting it as either would make
            # both numbers mean "something went wrong" instead of what they
            # say. ``abandoned`` wins over the pass count because a branch
            # can cross the bound on its very last pass.
            for state in (force, moment):
                if state.converged:
                    continue
                if state.abandoned:
                    self.n_thrust_overflow += 1
                elif state.passes >= MAX_PASSES:
                    self.n_passes_exhausted += 1
            return None, None
        if not thrust_is_admissible(force):
            self.n_thrust_rejected += 1
            if self.strict:
                return None, None
        return force.fos, moment.fos

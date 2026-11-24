# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The angles of the faces between Sarma's wedges that make the factor of
safety least (v0.1.471, D357, spec 009).

``settings.sarma.slice_angles`` takes two values beside the three
policies (``angles.OPTIMIZED_MODES``): ``optimized_global``, every surface
computed with the bisector and the critical one optimised afterwards, and
``optimized_all``, every surface optimised. The documentation of the
reference program describes the two and a search by several resolutions;
it says nothing of how. What is here is the project's own, and every rule
in it was measured before it was written (the bank's
``_auditoria/P9_D357/medir_angulos_v1471.py``, with its log, and the
adversarial review of the version).

WHAT MOVES
    The angle θ of each interior face of the wedges an angle policy gave.
    The boundaries stay where the starting wedges have them
    (``build_wedges(boundaries=...)``), and so do the faces the user gave at
    a vertex. The faces the optimiser sets are given by abscissa
    (``build_wedges(face_angles=...)``), with the source ``optimized``:
    like a vertex's, never dropped nor made vertical. Wedges with no face to
    move have nothing to optimise, and are left as they are.

THE START
    The best of the three policies (vertical, bisector, mean normal) whose
    factor is valid, admissible and passes the guard of D457 (below): the
    least such. The optimised factor is never above it. A policy whose
    factor has a larger root cannot be the start (the review of 0.1.471:
    choosing the least favours exactly the factor the 1.05 sweep leaves too
    small, 0.5957 for 0.6096 on problem 5 with γw = 9.81 and ten wedges);
    when none passes, there is no start, and the caller keeps the method's
    ordinary factor and says so.

THE SEARCH (the owner's decisions of 2026-11-17, phase B of the plan)
    A pattern search, face by face from the toe to the head: θ − step and
    θ + step, a move kept when the factor drops by more than the method's
    tolerance (so a coarse tolerance makes it stop early: 1e-3 leaves the
    circle of the test where the bisector had it), until no face moves,
    then the step halved: ``STEPS`` = 10°, 5°, 2.5°, 1.25°, 0.625°,
    0.3125°. Deterministic: the same wedges give the same angles, bit for
    bit. The coarse scan measured beside it (every face at 5°, 15°, …, 175°
    first) found factors 2 % lower on problems 4 and 5 of the bank, at
    twice the trials and next to a pole (least |q| 0.039); it was not
    taken. A configuration already solved is not solved again.

THREE RULES THE MEASURE ASKED FOR
    * The push. A face moved alone crosses its neighbour long before it
      reaches an angle that matters: on the saturated problem 4 with ten
      wedges asked, the face at the kink could not reach the published
      interface (F 0.4347) past the faces of the scarp, and the search
      stopped at 0.585. A move that makes the face cross a free neighbour
      makes that neighbour parallel to it, and so on outward (two parallel
      faces never cross); a face given at a vertex in the way, or an end,
      makes the move impossible.
    * The continuity. F(θ) jumps where a pole of the recurrence or of Kc
      crosses the root, and a minimiser walks straight into those jumps:
      without this rule, problem 4 went to 0.16 with every face in tension
      and problem 5 to 0.36 beside a pole (least |q| 0.006). A move that
      lowers the factor by more than ``JUMP`` (1 %) is halved until each
      half changes it by less; a jump that is still there under
      ``JUMP_STEP`` (0.001°) is a change of branch, and the move is refused.
    * The fold. Where the largest root meets the next one and the two
      vanish, the factor falls continuously up to an edge past which the
      method has none (or past which it jumps): a minimiser stops wherever
      its last step left it, and its factor depended on the step (the
      review: the saturated problem 4 with two wedges 0.20804 at 0.3125°,
      0.20530 at 0.039°; with ten, −2.9 %). After the steps, a last move
      that finds no factor or a jump is halved toward that edge, keeping
      each half that lowers the factor, to ``FOLD_STEP``, and the result
      says it lies on a fold (``fold_faces``; the run's note, with the
      faces in tension there: on that problem all of them, where Hoek's
      interface has E′ > 0). The factor is kept (the owner's decision).
      v0.1.487 (D457): with the solver no longer losing the pair of roots
      before they meet, the edge is a true fold, where F(θ) goes as the
      square root of the distance to it: halved to 0.001° the saturated
      problem 4 gave 0.20001 with ten wedges and 0.20004 with two, and the
      edge kept falling with a finer halving (0.19969 at 1e-4°, 0.19956 at
      1e-5°). Halved to ``FOLD_STEP`` (1e-7°) both give 0.19955, to 2e-6
      (the owner's decision: refine the edge). Until v0.1.486 the edge was
      where the sweep of 1.05 lost the pair, 0.2037, a smooth condition
      that 0.001° resolved.

    What the rules give: problem 1 of the bank, digitised from the
    reference's figures, puts the face at its kink within 2° of the drawn
    one, with the drawn faces optimal here to 0.1 %; the dry problem 4
    reaches its brute-force minimum, 1.5° from Hoek's interface. The
    saturated problem 4 ends on a fold at 0.1996, near Spencer's 0.209
    on the same surface, which is a coincidence of that case and not a
    property: its faces are all in tension there.

THE GUARD OF D457 (v0.1.471 to v0.1.486)
    The sweep of ``solver.solve`` stepped by 1.05 and a pair of roots inside
    one step hid the largest, exactly where a minimiser goes; each factor
    kept was checked with a finer sweep and refused when a larger root
    showed. ``solve`` no longer steps over one (v0.1.487, D457), and the
    guard, which could then refuse nothing, went with it (the owner's
    decision, rule 7).

Author: Samuel Sáez López (UPCT)

References:
    Sarma, S. K. (1973). Stability analysis of embankments and slopes.
        Géotechnique 23(3), 423–433: a solution must be physically
        acceptable (no tension in the mass).
    Sarma, S. K. (1979). Stability analysis of embankments and slopes.
        J. Geotech. Eng. Div. ASCE 105(GT12), 1511–1524. NOT consulted.
    Hooke, R. and Jeeves, T. A. (1961). "Direct search" solution of
        numerical and statistical problems. J. ACM 8(2), 212–229: the
        pattern search with a step halved when no move improves.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

from ogr_core.progress import checkpoint

from . import angles as _angles
from . import wedges as _wedges

#: The steps of the search [degrees], coarse to fine.
STEPS = (10.0, 5.0, 2.5, 1.25, 0.625, 0.3125)
#: A move that lowers the factor by more than this, relative, is checked
#: for a jump.
JUMP = 0.01
#: A jump still there when the move is shorter than this [degrees] is a
#: change of branch.
JUMP_STEP = 1e-3
#: v0.1.487 (D457) -- the precision of the edge of a fold [degrees]: F goes
#: as the square root of the distance to it, so the edge needs a finer
#: halving than a jump does (see the module, «The fold»).
FOLD_STEP = 1e-7
#: The bound on the passes at one step: each kept move lowers the factor
#: by more than the tolerance, so it ends anyway; this bounds a
#: pathological surface's cost (the review measured 14 passes at 0.625° on
#: a slope with a contact and 25 wedges).
MAX_PASSES = 50

#: What a solved configuration was: the wedges could not be built, or they
#: have no valid admissible factor.
_NO_WEDGES = "no wedges"
_NO_FACTOR = "no factor"


@dataclass
class AngleOptimum:
    """What :func:`optimize` found."""

    #: The wedges with the optimised faces (``angle_policy`` not yet set:
    #: the caller names its mode).
    wedges: object
    #: Their solution, valid and admissible.
    result: object
    #: The policy the search started from, and its factor.
    start_policy: Optional[str]
    start_fos: Optional[float]
    #: The wedges built (each one a trial, the continuity's included).
    trials: int = 0
    #: Moves refused as a change of branch.
    jumps: int = 0
    #: The faces left on the edge of a fold (``FOLD_STEP`` from it).
    fold_faces: list = field(default_factory=list)

    def details(self, mode: str) -> dict:
        """What the result says of it (``LEMResult.details``)."""
        return {"sarma_angle_mode": mode,
                "sarma_start_policy": self.start_policy,
                "sarma_start_fos": self.start_fos,
                "sarma_angle_trials": self.trials,
                "sarma_angle_jumps": self.jumps,
                "sarma_fold_faces": len(self.fold_faces)}


def optimize(project, *, build: Callable, evaluate: Callable, gain: float,
             progress: Optional[Callable] = None) -> Optional[AngleOptimum]:
    """The faces that make the factor of one surface least (see the module).

    Args:
        project: the model the wedges are cut in (for the ground the faces
            reach, :func:`wedges.face_context`).
        build: ``build(policy=None, boundaries=None, face_angles=None)``,
            the surface's wedges (``SarmaNonVertical.wedges_for``), or None.
        evaluate: ``evaluate(wedges)``, their solution when it is valid and
            admissible, else None.
        gain: the least drop of the factor that counts as one (the method's
            tolerance on F).
        progress: ``progress(done, total)`` after each step, or None.

    Returns:
        An :class:`AngleOptimum`, or None when no policy gives a valid,
        admissible factor or there is no face to move: the caller keeps what
        it had.
    """
    trials = 0

    def built(**kw):
        nonlocal trials
        trials += 1
        checkpoint()                 # a watcher may cancel here
        return build(**kw)

    best = None
    for policy in _angles.POLICIES:
        w = built(policy=policy)
        r = evaluate(w) if w is not None else None
        if r is None:
            continue
        if best is None or r.fos < best[2].fos:
            best = (policy, w, r)
    if best is None:
        return None
    start_policy, w0, r0 = best
    faces = w0.faces
    n = len(faces) - 1
    xs = tuple(w0.boundaries)
    free = [k for k in range(1, n) if faces[k].angle_source != "vertex"]
    if not free:
        return None
    theta = [math.degrees(f.theta) for f in faces]
    context = _wedges.face_context(project)

    def position(k, th):
        _deg, top = _wedges.vertex_face(project, faces[k].x_base,
                                        faces[k].y_base, th, context)
        return None if top is None else _wedges.ground_position(context,
                                                                *top)
    lo = _wedges.ground_position(context, faces[0].x_top, faces[0].y_top)
    hi = _wedges.ground_position(context, faces[n].x_top, faces[n].y_top)
    pos = [lo] + [position(k, theta[k]) for k in range(1, n)] + [hi]

    def pushed(th, p, k):
        """``th`` with face ``k`` moved: the free faces it crosses (or that
        it leaves without a way to the ground) made parallel to it, outward,
        or None when a face given at a vertex or an end is in the way. ``p``,
        the positions of the tops along the ground, is updated with it: the
        faces do not cross while it increases strictly."""
        p[k] = position(k, th[k])
        if p[k] is None:
            return None
        j = k - 1                                 # toward the toe
        while j >= 1 and not (p[j] is not None and p[j] < p[j + 1]):
            if faces[j].angle_source == "vertex":
                return None
            th[j] = th[j + 1]
            p[j] = position(j, th[j])
            if p[j] is None or not p[j] < p[j + 1]:
                return None
            j -= 1
        j = k + 1                                 # toward the head
        while j <= n - 1 and not (p[j] is not None and p[j] > p[j - 1]):
            if faces[j].angle_source == "vertex":
                return None
            th[j] = th[j - 1]
            p[j] = position(j, th[j])
            if p[j] is None or not p[j] > p[j - 1]:
                return None
            j += 1
        if not (p[0] < p[1] and p[n - 1] < p[n]):
            return None
        return th

    seen: dict = {}

    def solve(th):
        """``(wedges, result)`` of the faces ``th``, or ``(None, why)``. A
        configuration solved before answers from memory with its factor
        alone (``(None, F)``): the search only re-solves to keep one."""
        key = tuple(round(th[k], 12) for k in free)
        if key in seen:
            return None, seen[key]
        w = built(boundaries=xs,
                  face_angles={faces[k].x_base: th[k] for k in free})
        if w is None:
            seen[key] = _NO_WEDGES
            return None, _NO_WEDGES
        r = evaluate(w)
        seen[key] = r.fos if r is not None else _NO_FACTOR
        return (w, r) if r is not None else (None, _NO_FACTOR)

    def factor_of(th):
        _w, r = solve(th)
        if isinstance(r, str):
            return None
        return r if isinstance(r, float) else r.fos

    # The start again, with its faces given by abscissa: the wedges every
    # later trial is compared with are built the way they are.
    w_best, r_best = solve(theta)
    if w_best is None:
        return None
    out = AngleOptimum(wedges=w_best, result=r_best, start_policy=start_policy,
                       start_fos=r0.fos)

    def moved(k, value):
        th, p = list(theta), list(pos)
        th[k] = value
        if pushed(th, p, k) is None:
            return None, None
        return th, p

    def continuous(k, a, b, Fa, Fb):
        if abs(Fb - Fa) <= JUMP * min(Fa, Fb):
            return True
        if abs(b - a) < JUMP_STEP:
            return False
        m = 0.5 * (a + b)
        th, _p = moved(k, m)
        if th is None:
            return False
        Fm = factor_of(th)
        if Fm is None:
            return False
        return continuous(k, a, m, Fa, Fm) and continuous(k, m, b, Fm, Fb)

    def attempt(k, value, count=True):
        """Try face ``k`` at ``value``: ``"kept"``, ``"edge"`` (no factor,
        or a jump: the side of a fold), or ``"no"``. ``count``: a refused
        jump goes to ``jumps`` (not while a fold is halved)."""
        nonlocal w_best, r_best
        if not 0.0 < value < 180.0:
            return "no"
        th, p = moved(k, value)
        if th is None:
            return "no"
        w, r = solve(th)
        if r == _NO_WEDGES:
            return "no"
        if r == _NO_FACTOR:
            return "edge"
        F = r if isinstance(r, float) else r.fos
        if not F < r_best.fos - gain:
            return "no"
        if w is None:                         # remembered: solve it again
            seen.pop(tuple(round(th[j], 12) for j in free), None)
            w, r = solve(th)
            if w is None:
                return "no"
        if not continuous(k, theta[k], value, r_best.fos, r.fos):
            if count:
                out.jumps += 1
            return "edge"
        theta[:], pos[:] = th, p
        w_best, r_best = w, r
        return "kept"

    for level, step in enumerate(STEPS):
        for _pass in range(MAX_PASSES):
            any_move = False
            for k in free:
                for value in (theta[k] - step, theta[k] + step):
                    if attempt(k, value) == "kept":
                        any_move = True
            if not any_move:
                break
        if progress is not None:
            progress(level + 1, len(STEPS))

    # The fold: a last move that met no factor or a jump, halved toward that
    # edge, each half that lowers the factor kept.
    last = STEPS[-1] if STEPS else None
    for _pass in range(MAX_PASSES if last else 0):
        any_move = False
        for k in free:
            for sign in (-1.0, 1.0):
                if attempt(k, theta[k] + sign * last, False) != "edge":
                    continue
                a, b, at_edge = theta[k], theta[k] + sign * last, True
                while abs(b - a) >= FOLD_STEP:
                    m = 0.5 * (a + b)
                    status = attempt(k, m, False)
                    if status == "kept":
                        a = m
                        any_move = True
                    else:
                        b, at_edge = m, status == "edge"
                if at_edge and k not in out.fold_faces:
                    out.fold_faces.append(k)
        if not any_move:
            break
    out.wedges, out.result, out.trials = w_best, r_best, trials
    return out


__all__ = ["AngleOptimum", "FOLD_STEP", "JUMP", "JUMP_STEP", "MAX_PASSES",
           "STEPS", "optimize"]

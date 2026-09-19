# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""v0.1.179 (D145) — a branch is accepted on the state it reached, and the
state of ``solve_branch`` is the PAIR (F, X), not F.

WHAT INVARIANT THIS PROTECTS. ``interslice.solve_branch`` iterates a factor
of safety F and a thrust distribution X together, and until this version its
acceptance asked only about F: a step under the tolerance plus two shrinking
steps (v0.1.172, D116). Two things follow from asking about half of a state,
and both were measured on the bank before anything was changed:

  * a branch can be admitted while X is nowhere near its own fixed point.
    On the archived critical circle of verification problem 087 under GLE
    the moment branch at lambda 3.0 is admitted on pass 45 with a thrust
    residual of 885 times the tolerance and the thrust still GROWING — a
    beat node of an iteration that diverges, which continued walks out of
    the loop on the thrust bound. Pass 45 is far ahead of STALL_PATIENCE, so
    the rescue of v0.1.176, which has had this gate since the day it was
    written, never sees it;
  * a branch that IS converging need not contract monotonically. On the
    published circle of problem 091 at 30 slices the force branch steps
    alternate — 6.10e-4, 6.22e-4, 3.18e-4, 3.26e-4, 1.65e-4, 1.71e-4 — with
    the envelope halving every two passes, so ``step < prev_step <
    prev_step_2`` is never true. That branch sits on its answer from pass
    21 and is admitted on pass 107, when rounding finally breaks the
    pattern; at a lambda a thousandth away it is never admitted at all and
    the sample is lost to the stall test.

    Pass 107 is the bank's own model through ``build_method``; the same
    branch on the reconstruction in this file, and through
    ``build_search``, stops on 105. The two doors set up the search
    slightly differently and neither number is the invariant — which is why
    what is asserted below is "more than 60 before, fewer than 60 now" and
    not either figure.

The diagnosis was already written inside the engine. ``RESCUE_OMEGA_MIN``
has said since v0.1.176 that "the thrust residual is what closes the door
D116 measured — F sitting at the fixed point OF THE CURRENT X while X is
still far from its own". What that sentence described was half the solver.

WHAT THE FICHA ASKED FOR, AND WHAT THE MEASUREMENT SAID INSTEAD. D145 gave
the 087 beat node on the circle 0.555556 / 16.823529 / 11.737803 and the 091
force branch at lambda 0.36703. Neither reproduces as written on 0.1.178,
and the reasons are worth keeping:

  * on THAT circle the branch is already refused, because there the beat
    node falls on pass 95, past the rescue's gate, and the rescue's own
    thrust test throws it out. The half of the defect that is still live is
    the half the rescue cannot reach, and the census found it on the
    ARCHIVED critical surface of the same problem, where the node is on
    pass 45. The published factor of that surface does not move; what moves
    is ``lambdas_lost_to_stall``, from 0 to 1;
  * 0.36703 is not a lambda the search samples. At 0.365133, which it does
    sample, the branch is admitted on pass 107 exactly as the ficha says.
    Off the sampled grid the same branch is never admitted at all, which is
    a worse symptom than the one reported, not a milder one.

HOW THE RULE 7 GATE WAS BUILT, because a test of a defect that cannot see
the defect is the trap this project has now walked into ten times (D101,
D103, D118, D127, D129). Each half of the change has its own module switch,
``BRANCH_PAIR_TIGHTEN`` and ``BRANCH_PAIR_SETTLE``, and every case that
claims a difference measures it against the same tree with the switch off,
in one process. ``TestEachSwitchMovesANumber`` fails if either of them turns
out to change nothing at all.

WHICH CASES MEASURE THE DEFECT AND WHICH ARE CONTROL, counted rather than
asserted, and NAMED rather than counted, because a file that only gives a
tally will be read as one where every case discriminates. Measured against
the tree of 0.1.178 with only this file added: 7 of the 18 FAIL and 11 PASS.

SIX fail on a measured difference, which is the real coverage:

* ``test_and_the_thrust_was_growing_when_it_was`` and
  ``test_now_it_is_refused_and_one_exit_names_it`` — the 087 beat node;
* ``test_it_is_now_accepted_where_it_already_sat`` — the 091, on pass 105
  there against 25 here;
* ``test_the_tightening_alone_changes_a_branch`` and
  ``test_the_settling_alone_changes_a_branch`` — with no switches to turn
  off, both sides of each A/B are the same run and the difference vanishes;
* ``test_and_every_branch_that_moved_carries_its_reason`` — nothing moves
  there, so the sweep finds no mover and says so.

ONE fails with ``AttributeError`` because it reads the new module
constants — ``test_both_are_on_by_default``. That is WEAK discrimination and
is labelled rather than counted as strength.

THREE of the eleven that pass are MEANT to, and would be broken if they
moved: ``test_it_used_to_be_accepted_on_a_node_of_a_growing_thrust`` and
``test_the_steps_alternate_instead_of_shrinking`` describe the OLD
behaviour, and ``test_a_branch_whose_thrust_had_settled_is_bit_for_bit`` is
an identity on either tree. The rest are the declared CONTROL classes.

WHAT THIS FILE DOES NOT CLAIM, said out loud because promising more coverage
than a change delivers is what cost this project two versions in v0.1.82-84:

* no assertion here fixes a factor of safety. Every numeric claim is either
  an A/B in one process, an identity, or a comparison of pass counts;
* ``converged`` still does not mean "the thrust state is admissible".
  ``thrust_is_admissible`` remains a separate, weaker preference applied by
  ``GLESystem.branches``, and this version does not merge the two;
* the residual gap of a slow contraction is untouched. A branch stopped on a
  step of ``tol`` with ratio r still sits ``tol*r/(1-r)`` from its fixed
  point, and that estimate was considered and NOT adopted in v0.1.172;
* the thrust residual is compared against the same ``tolerance`` as the step
  in F, which is what the rescue has done since v0.1.176. That equivalence
  is inherited, not derived here.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import math

# ----------------------------------------------------------------------
# The three-tiered geosynthetic wall of verification problems 87-94
# (Leshchinsky and Han 2004), written out from the bank's
# ``_tools/muro_bancadas.py`` so that the suite runs on a machine that does
# not have the bank. Problems 087 and 091 are the SAME wall: a structural
# diff of the two ``.ogr`` files gives three substantive differences and
# nothing else — the left edge of the model and the two strength parameters
# of the foundation — so the constructor takes one flag rather than being
# written twice.
# ----------------------------------------------------------------------
#: 087 "Baseline" keeps the model's left edge at the origin; 091
#: "Foundation Soil" extends it and replaces the foundation with a weak one.
X_PIE, Y_CIMIENTO, Y_CORONACION, X_DERECHA = 6.0, 6.0, 15.0, 24.0
X_IZQUIERDA = {False: 0.0, True: -2.0}
CIMIENTO = {False: (10.0, 34.0), True: (0.0, 18.0)}
RETRANQUEO, ANCHO_BLOQUE, SEPARACION, LONGITUD = 1.2, 0.2, 0.6, 6.3
N_BANCADAS = 3

#: The published Spencer circle of problem 091 and a lambda its own search
#: samples. Geometry and a sampling coordinate, not results.
CIRCLE_091 = (4.658, 15.0, 10.934)
LAMBDA_091 = 0.365133
SLICES_091 = 30

#: The critical circle problem 087 has archived under GLE, and the lambda of
#: the grid where its moment branch beats. Also geometry.
CIRCLE_087 = (-1.333333, 18.647059, 14.604747)
LAMBDA_087 = 3.0
SLICES_087 = 50

#: The plane of ``test_branch_contraction_v1172``, and the ONE cell of the
#: sixteen measured (four angles x two branches x two tolerances) whose two
#: first steps are both already inside the tolerance: 1.411e-3 and 1.029e-3.
#: Without the ``_pass > 1`` floor on the settle path, that cell is admitted
#: on pass 2 and the two-pass accidental acceptance of D116 comes back.
H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
NSLICES = 50
FLOOR_BETA, FLOOR_LAMBDA, FLOOR_TOL = 50.0, 0.0, 5e-3


# ----------------------------------------------------------------------
def _caras():
    return [X_PIE + i * RETRANQUEO for i in range(N_BANCADAS)]


def _cotas():
    h = (Y_CORONACION - Y_CIMIENTO) / N_BANCADAS
    return [(Y_CIMIENTO + i * h, Y_CIMIENTO + (i + 1) * h)
            for i in range(N_BANCADAS)]


def _wall(weak_foundation: bool):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  Geosynthetic, SupportInstance)

    x_izq = X_IZQUIERDA[weak_foundation]
    c_cim, phi_cim = CIMIENTO[weak_foundation]
    pts = [(x_izq, 0.0), (X_DERECHA, 0.0), (X_DERECHA, Y_CORONACION)]
    for x, (y_base, y_techo) in reversed(list(zip(_caras(), _cotas()))):
        pts.append((x, y_techo))
        pts.append((x, y_base))
    pts.append((x_izq, Y_CIMIENTO))
    p = Project("091" if weak_foundation else "087")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in pts], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(x_izq, Y_CIMIENTO),
                                    Vertex(X_DERECHA, Y_CIMIENTO)]),
        btype=BoundaryType.MATERIAL))
    for x_cara, (y_base, y_techo) in zip(_caras(), _cotas()):
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[
                Vertex(x_cara, y_base), Vertex(x_cara + ANCHO_BLOQUE, y_base),
                Vertex(x_cara + ANCHO_BLOQUE, y_techo),
                Vertex(x_cara, y_techo)]),
            btype=BoundaryType.MATERIAL))
    fill = Material(name="fill", unit_weight=18.0, sat_unit_weight=18.0,
                    strength=MohrCoulomb(cohesion=0.0, friction_angle=34.0))
    foundation = Material(name="foundation", unit_weight=18.0,
                          sat_unit_weight=18.0,
                          strength=MohrCoulomb(cohesion=c_cim,
                                               friction_angle=phi_cim))
    blocks = Material(name="blocks", unit_weight=18.0, sat_unit_weight=18.0,
                      strength=MohrCoulomb(cohesion=2.5, friction_angle=34.0))
    p.materials = [fill, foundation, blocks]
    bloque_x = [(x, x + ANCHO_BLOQUE) for x in _caras()]
    for reg in p.resolve_regions():
        cx, cy = reg.centroid()
        if cy < Y_CIMIENTO:
            mid = foundation.id
        elif any(lo <= cx <= hi for lo, hi in bloque_x):
            mid = blocks.id
        else:
            mid = fill.id
        p.assign_material_at(cx, cy, mid)
    p.settings.units.failure_direction = FailureDirection.RIGHT_TO_LEFT
    p.support_types = [Geosynthetic(
        tensile_capacity=10.0, strip_coverage=100.0, connection_strength=10.0,
        anchorage="slope_face", pullout_mode="coefficient",
        coefficient_of_interaction=0.8)]
    h = (Y_CORONACION - Y_CIMIENTO) / N_BANCADAS
    per_tier = int(round(h / SEPARACION))
    for x_cara, (y_base, _y) in zip(_caras(), _cotas()):
        x0 = x_cara + ANCHO_BLOQUE
        for k in range(per_tier):
            y = y_base + (k + 0.5) * SEPARACION
            p.supports.append(SupportInstance(
                type_id="geosynthetic", head=Vertex(x0, y),
                tail=Vertex(x0 + LONGITUD, y),
                force_application=ForceApplication.PASSIVE,
                orientation=ForceOrientation.PARALLEL_TO_SUPPORT))
    p.settings.methods.num_slices = 50
    p.settings.methods.tolerance = 1e-4
    return p


def _wall_system(weak_foundation, circle, method_id, n, tolerance=1e-4):
    """The ``GLESystem`` the METHOD builds, captured off the class.

    Captured and not rebuilt: the system is a local of ``compute_fos`` and a
    helper that builds one "the same way" measures a different system —
    the lesson ``_tools/curva_cuna_d119.py`` carries in its own header.
    """
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.search import GridSearch
    from ogr_slip2d.surface import SlipCircle

    cls = type(method_registry()[method_id]())
    cap = []
    orig = cls._inner_solve

    def spy(self, slices, lam, system):
        if system not in cap:
            cap.append(system)
        return orig(self, slices, lam, system)

    cls._inner_solve = spy
    try:
        GridSearch(method=method_registry()[method_id](
            tolerance=tolerance, max_iterations=50),
            num_slices=n, min_area=0.0).evaluate_circle(
                _wall(weak_foundation), SlipCircle(*circle))
    finally:
        cls._inner_solve = orig
    assert len(cap) == 1, len(cap)
    return cap[0]


# ----------------------------------------------------------------------
def _wedge(beta_deg=FLOOR_BETA):
    from ogr_core.geometry import (Boundary, BoundaryType, Polyline, Vertex)
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_slip2d.interslice import GLESystem
    from ogr_slip2d.moment_balance import axis_for
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipSurface

    p = Project("wedge")
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0)], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=GAMMA,
                            strength=MohrCoulomb(cohesion=COH,
                                                 friction_angle=PHI))]
    surface = SlipSurface(polyline=Polyline(vertices=[
        Vertex(TOE, 0.0),
        Vertex(TOE + H / math.tan(math.radians(beta_deg)), H)]))
    sl = slice_surface(p, surface, num_slices=NSLICES)
    assert sl is not None and sl.slices, "the plane produced no slices"
    n = len(sl.slices)
    return GLESystem(sl.slices, [1.0] * (n + 1), 0.0, 0.0, 1.0,
                     None, None, None, axis_for(p, surface),
                     tolerance=1e-14)


# ----------------------------------------------------------------------
def _branch(system, lam, tolerance, moment=False, initial=1.0, **kw):
    from ogr_slip2d.interslice import solve_branch
    kw.setdefault("max_passes", system.max_passes)
    return solve_branch(system.rows, system.lambda_boundary(lam),
                        system._moment_fos if moment else None,
                        tolerance, initial, **kw)


def _thrust_residual(system, lam, moment, tolerance, k):
    """``max|X_k - X_{k-1}|/force_scale`` — the pass-k thrust residual.

    Rebuilt from two capped calls rather than read off a field, so that this
    file measures the quantity the gate is ABOUT and not the engine's own
    opinion of it. ``max_passes`` is read by nothing but the loop's
    ``range``, which is what makes it a usable time machine — the same idiom
    as ``test_branch_contraction_v1172._iterate_at``.
    """
    from ogr_slip2d.interslice import _force_scale
    now = _branch(system, lam, tolerance, moment, max_passes=k)
    before = (_branch(system, lam, tolerance, moment, max_passes=k - 1)
              if k > 1 else None)
    if now is None:
        return None
    n = len(now.boundary_x) - 1
    base = [0.0] * (n + 1) if before is None else before.boundary_x
    worst = max((abs(now.boundary_x[i] - base[i]) for i in range(1, n)),
                default=0.0)
    scale = _force_scale(system.rows)
    return worst / scale if scale > 0.0 else worst


def _steps(system, lam, moment, tolerance, upto):
    """``|f_new - F|`` for passes 1..upto, rebuilt from the iterates.

    Outside the rescue the engine stores the damped mean ``0.5*(F + f_new)``,
    so the step is twice the move of the iterate; on the pass that ACCEPTS it
    stores ``f_new`` and the factor is one. Measured rather than assumed: with
    a single factor the accepting pass comes out at exactly double.
    """
    out, previous = [], 1.0
    for k in range(1, upto + 1):
        st = _branch(system, lam, tolerance, moment, max_passes=k)
        if st is None:
            out.append(None)
            continue
        factor = 1.0 if (st.converged and st.passes == k) else 2.0
        out.append(factor * abs(st.fos - previous))
        previous = st.fos
    return out


@contextlib.contextmanager
def _pair_off(tighten=True, settle=True):
    """The acceptance of 0.1.178, in this process.

    The runner has no ``monkeypatch`` and does not run ``teardown_method``,
    so the restoring is written out (rule 5). A tree without the switches has
    nothing to turn off, and there the CONTROL cases still mean what they say
    while the discriminating ones fail — which is the point of them.
    """
    import ogr_slip2d.interslice as interslice
    keep_t = getattr(interslice, "BRANCH_PAIR_TIGHTEN", None)
    keep_s = getattr(interslice, "BRANCH_PAIR_SETTLE", None)
    if keep_t is None or keep_s is None:
        yield
        return
    if tighten:
        interslice.BRANCH_PAIR_TIGHTEN = False
    if settle:
        interslice.BRANCH_PAIR_SETTLE = False
    try:
        yield
    finally:
        interslice.BRANCH_PAIR_TIGHTEN = keep_t
        interslice.BRANCH_PAIR_SETTLE = keep_s


# ======================================================================
# A. The half the rescue could never reach.
# ======================================================================
class TestAChatteringBranchIsRefused:
    """DISCRIMINATES. Against 0.1.178 the first two cases fail, because
    there the branch is accepted."""

    def test_it_used_to_be_accepted_on_a_node_of_a_growing_thrust(self):
        """The measurement this class rests on, asserted so that the case
        below cannot pass in a vacuum. Two facts about the old acceptance:
        it happened, and it happened while the thrust was moving by orders
        of magnitude more than the tolerance."""
        system = _wall_system(False, CIRCLE_087, "gle_morgenstern_price",
                              SLICES_087)
        with _pair_off():
            was = _branch(system, LAMBDA_087, system.tolerance, moment=True)
        assert was is not None and was.converged is True, was
        assert was.passes < 80, ("the node has to fall before the rescue's "
                                 "gate or this measures the rescue", was.passes)
        d_x = _thrust_residual(system, LAMBDA_087, True, system.tolerance,
                               was.passes)
        assert d_x > 100.0 * system.tolerance, d_x

    def test_and_the_thrust_was_growing_when_it_was(self):
        """A node is not a small residual: it is the moment a large one
        happens to stop moving F. The quantity asserted here is the one the
        gate reads, and it climbs monotonically straight THROUGH the pass
        the branch is admitted on — measured, 610 / 674 / 752 / 848 / 884 /
        924 times the tolerance on passes 35 to 46.

        The peak |E| is deliberately NOT what is asserted, because it is a
        different quantity and on this surface it is flat over that window
        to nine figures. A residual that grows while the magnitude it is a
        residual OF does not is exactly what a redistributing thrust looks
        like, and writing the wrong one of the two down would have made this
        case green for a reason it does not name.
        """
        system = _wall_system(False, CIRCLE_087, "gle_morgenstern_price",
                              SLICES_087)
        with _pair_off():
            was = _branch(system, LAMBDA_087, system.tolerance, moment=True)
        k = was.passes
        seen = [_thrust_residual(system, LAMBDA_087, True, system.tolerance, j)
                for j in (k - 8, k, k + 1)]
        assert all(d is not None for d in seen), seen
        assert seen[0] < seen[1] < seen[2], seen

    def test_now_it_is_refused_and_one_exit_names_it(self):
        """Rule 7 in the affirmative: a refusal that left no trace would be
        a fifth way out of the loop wearing no name. Exactly one of the three
        counters has to move, and which one is not asserted — that is the
        solver's business and it may change."""
        system = _wall_system(False, CIRCLE_087, "gle_morgenstern_price",
                              SLICES_087)
        now = _branch(system, LAMBDA_087, system.tolerance, moment=True)
        assert now is not None and now.converged is False, now
        before = (system.n_stalled, system.n_passes_exhausted,
                  system.n_thrust_overflow)
        system.branches(LAMBDA_087)
        after = (system.n_stalled, system.n_passes_exhausted,
                 system.n_thrust_overflow)
        moved = [a - b for a, b in zip(after, before)]
        assert sum(moved) >= 1, (before, after)


# ======================================================================
# B. The half that was waiting.
# ======================================================================
class TestASettledBranchStopsWaiting:
    """DISCRIMINATES. Against 0.1.178 the first case fails on the pass
    count; the other two are green on both sides and say why."""

    def test_the_steps_alternate_instead_of_shrinking(self):
        """The mechanism, asserted through behaviour and not by reading the
        source. Between the pass where the branch is already on its answer
        and the pass it used to be admitted on, there is no run of three
        strictly decreasing steps anywhere — which is exactly what
        ``step < prev_step < prev_step_2`` asks for and never gets.

        Green on both sides: it describes the branch, not the criterion.
        """
        system = _wall_system(True, CIRCLE_091, "spencer", SLICES_091)
        # Measured with the settle path OFF: with it on the branch is
        # admitted on pass 25 and every capped call past it returns the same
        # accepted state, so the tail of the sequence would read as a row of
        # exact zeros. That is an artefact of the time machine, not of the
        # branch, and it would have made this case green while measuring
        # nothing.
        with _pair_off():
            seq = _steps(system, LAMBDA_091, False, system.tolerance, 60)
        window = [s for s in seq[20:60] if s is not None]
        assert len(window) >= 30, len(window)
        runs = sum(1 for a, b, c in zip(window, window[1:], window[2:])
                   if c < b < a)
        assert runs == 0, (runs, window)
        # And it IS converging while it does that: the envelope falls by
        # more than two decades over the same window. A sequence that simply
        # wandered would satisfy the run test too.
        assert window[-1] < 0.01 * window[0], (window[0], window[-1])

    def test_it_is_now_accepted_where_it_already_sat(self):
        """The pass moves and the answer does not. Both halves are asserted,
        because a criterion that accepted sooner on a DIFFERENT number would
        be a different solver and not a repaired one; the two factors have to
        agree inside the tolerance the branch was asked for."""
        system = _wall_system(True, CIRCLE_091, "spencer", SLICES_091)
        with _pair_off():
            was = _branch(system, LAMBDA_091, system.tolerance)
        now = _branch(system, LAMBDA_091, system.tolerance)
        assert was is not None and now is not None
        assert was.converged and now.converged, (was, now)
        assert was.passes > 60, was.passes
        assert now.passes < 60, now.passes
        assert abs(now.fos - was.fos) < system.tolerance, (now.fos, was.fos)

    def test_and_what_it_settled_on_is_a_fixed_point(self):
        """Rule 1 without a reference value: the accepted iterate, fed back
        in as the start, has to come straight back. One more march is the
        yardstick, so nothing here is a snapshot of what the code prints."""
        system = _wall_system(True, CIRCLE_091, "spencer", SLICES_091)
        now = _branch(system, LAMBDA_091, system.tolerance)
        again = _branch(system, LAMBDA_091, system.tolerance,
                        initial=now.fos)
        assert again is not None and again.converged
        assert abs(again.fos - now.fos) < 10.0 * system.tolerance, (
            again.fos, now.fos)


# ======================================================================
# C. The floor the settle path may not undercut.
# ======================================================================
class TestTheThirdPassFloorSurvives:
    """Declared CONTROL: green on BOTH sides of this change, here to guard
    against an error THIS design can make — letting a branch in on two
    passes because the thrust happens to carry no information — and not
    against the defect it removes.

    The cell is named rather than swept, because sweeping found it once and
    a sweep that happens to miss it next time would read as a pass. At
    lambda 0 the interslice function is multiplied by zero, so X stays at
    zero for every pass and the thrust residual is EXACTLY zero: the pair
    test degenerates to the step test, and a path that asks only for two
    consecutive steps inside the tolerance is the +inf sentinel of D116
    coming back by another door.
    """

    def test_the_first_two_steps_of_that_cell_are_already_inside(self):
        """The danger is real, and this is the half of it that does not
        depend on the fix: one cell of the sixteen measured has both of its
        first steps under the tolerance."""
        system = _wedge(FLOOR_BETA)
        seq = _steps(system, FLOOR_LAMBDA, True, FLOOR_TOL, 2)
        assert all(s is not None and s < FLOOR_TOL for s in seq), seq

    def test_and_the_branch_still_takes_three(self):
        """And this is the half that does: it is admitted on the third pass
        all the same."""
        system = _wedge(FLOOR_BETA)
        st = _branch(system, FLOOR_LAMBDA, FLOOR_TOL, moment=True)
        assert st is not None and st.converged, st
        assert st.passes == 3, st.passes

    def test_the_thrust_residual_at_that_lambda_is_exactly_zero(self):
        """Not "small": zero, and by construction. It is what makes the case
        above a guard on the floor and not on the gate."""
        system = _wedge(FLOOR_BETA)
        for k in (1, 2, 3):
            d_x = _thrust_residual(system, FLOOR_LAMBDA, True, FLOOR_TOL, k)
            assert d_x == 0.0, (k, d_x)


# ======================================================================
# D. What did not move.
# ======================================================================
class TestOnlyADirtyThrustMovesABranch:
    """Declared CONTROL. The claim this version rests on is NOT that the
    bank improves — over the archived surfaces it mostly does not move at
    all — but that the pass a branch is admitted on moves only where the
    thrust had not settled. Measured as an A/B in one process, so it is an
    identity and not a stored number.

    The first draft of this class asserted that the wedge ladder was
    untouched outright, and the ladder refuted it: at 35 degrees, lambda
    -1.0, moment branch, tolerance 1e-6, the branch used to be admitted on
    pass 13 with a thrust residual of 1.088 times the tolerance and is now
    admitted on pass 15. That is the gate doing its job on a case nobody had
    looked at, so what the class asserts is the rule and not the hope.
    """

    LADDER = ((35.0, (-1.0, -0.4, 0.0, 0.2, 0.6, 1.0)),
              (40.0, (-1.0, -0.4, 0.0, 0.2, 0.6, 1.0)),
              (45.0, (-0.4, 0.0, 0.2, 0.6)),
              (50.0, (-0.4, 0.0, 0.2, 0.6)))

    def _sweep(self):
        """``(clean_and_identical, movers)`` over the ladder and the wall."""
        clean, movers = 0, []
        cases = [(_wedge(beta), lam, tol, moment, (beta, lam))
                 for beta, lambdas in self.LADDER for lam in lambdas
                 for moment in (False, True) for tol in (1e-3, 1e-6)]
        wall = _wall_system(True, CIRCLE_091, "spencer", SLICES_091)
        cases += [(wall, lam, wall.tolerance, moment, ("091", lam))
                  for lam in (-0.1, 0.0, 0.1, 0.2, LAMBDA_091, 0.4)
                  for moment in (False, True)]
        for system, lam, tol, moment, tag in cases:
            with _pair_off():
                was = _branch(system, lam, tol, moment)
            now = _branch(system, lam, tol, moment)
            if was is None or not was.converged:
                continue
            same = (now is not None and now.converged
                    and now.fos == was.fos and now.passes == was.passes)
            d_x = _thrust_residual(system, lam, moment, tol, was.passes)
            if same:
                if d_x is not None and d_x < tol:
                    clean += 1
            else:
                gap = (None if now is None or now.fos is None
                       else abs(now.fos - was.fos))
                movers.append((tag, moment, tol, was.passes,
                               None if now is None else now.passes, d_x, gap))
        return clean, movers

    def test_a_branch_whose_thrust_had_settled_is_bit_for_bit(self):
        """Same factor, same pass, same everything — and counted, so that a
        fixture that stopped producing converged branches cannot pass this
        by comparing nothing."""
        clean, _movers = self._sweep()
        assert clean >= 60, clean

    def test_and_every_branch_that_moved_carries_its_reason(self):
        """The other half, and the one that makes the first half mean
        something: nothing moves without a reason that can be read off the
        OLD state, and there are exactly two reasons because there are
        exactly two paths.

        A branch admitted LATER, or no longer admitted at all, is one the
        gate refused, and its old accepting pass has to show a thrust
        residual at or above the tolerance. A branch admitted SOONER is one
        the settle path took while the contraction test was still waiting
        for two shrinking steps, and there the factor has to be the same one
        inside the tolerance it was asked for — a path that admitted a
        DIFFERENT number sooner would be a different solver, not a repaired
        one. Anything else is a move this version did not intend.
        """
        _clean, movers = self._sweep()
        assert movers, "the fixture stopped exercising the change"
        earlier = later = 0
        for tag, moment, tol, was_k, now_k, d_x, gap in movers:
            if now_k is not None and now_k < was_k:
                earlier += 1
                assert gap is not None and gap < tol, (
                    tag, moment, tol, was_k, now_k, gap)
            else:
                later += 1
                assert d_x is not None and d_x >= tol, (
                    tag, moment, tol, was_k, now_k, d_x)
        assert earlier and later, (earlier, later)


# ======================================================================
# E. The switches, and the constants around them.
# ======================================================================
class TestEachSwitchMovesANumber:
    """Declared CONTROL for the constants and rule 7 for the switches: a
    setting that cannot change an answer is worse than no setting, so each
    one is asked to prove it changes one."""

    def test_both_are_on_by_default(self):
        import ogr_slip2d.interslice as interslice
        assert interslice.BRANCH_PAIR_TIGHTEN is True
        assert interslice.BRANCH_PAIR_SETTLE is True

    def test_the_tightening_alone_changes_a_branch(self):
        system = _wall_system(False, CIRCLE_087, "gle_morgenstern_price",
                              SLICES_087)
        with _pair_off(tighten=True, settle=False):
            was = _branch(system, LAMBDA_087, system.tolerance, moment=True)
        now = _branch(system, LAMBDA_087, system.tolerance, moment=True)
        assert was.converged != now.converged, (was, now)

    def test_the_settling_alone_changes_a_branch(self):
        system = _wall_system(True, CIRCLE_091, "spencer", SLICES_091)
        with _pair_off(tighten=False, settle=True):
            was = _branch(system, LAMBDA_091, system.tolerance)
        now = _branch(system, LAMBDA_091, system.tolerance)
        assert was.passes != now.passes, (was.passes, now.passes)

    def test_the_four_constants_did_not_move(self):
        """CONTROL. This version buys nothing by loosening a limit, and the
        four that bound the loop are the ones a change of criterion would be
        tempted to spend."""
        import ogr_slip2d.interslice as interslice
        assert interslice.STALL_PATIENCE == 80
        assert interslice.MAX_PASSES == 400
        assert interslice.FALLBACK_RESIDUAL_LIMIT == 0.02
        assert interslice.THRUST_SCALE_LIMIT == 10.0
        assert interslice.BRANCH_RESCUE is True

    def test_the_rescue_still_accepts_on_its_own_terms(self):
        """CONTROL. The rescue's acceptance is the rule this version
        generalises, and generalising it must not have changed it: entering
        the rescue still clears the two-pass memory, so a rescued branch
        cannot be admitted on the first relaxed pass it takes."""
        system = _wedge(50.0)
        st = _branch(system, 2.0, 1e-10, moment=True, max_passes=400)
        if st is not None and st.rescued:
            assert st.passes >= 82, st.passes


# ======================================================================
# F. Rule 6, made executable.
# ======================================================================
class TestWhatThisDoesNotFix:
    """Both of these are real, both are measured, and both are deliberately
    left alone — so they are asserted here, and the day one of them is
    repaired this class goes red and says which."""

    def test_an_accepted_value_can_still_sit_far_from_its_fixed_point(self):
        """The residual estimate that v0.1.172 considered and did not adopt,
        and that this version does not adopt either. A contraction of ratio r
        stopped on a step of ``tol`` sits within ``tol*r/(1-r)`` of the root,
        and the thrust gate does nothing about that: it asks whether X has
        settled, not how far F is from where it is going."""
        system = _wedge(50.0)
        tol = 5e-3
        st = _branch(system, 2.0, tol, moment=True)
        root = _branch(system, 2.0, 1e-12, moment=True, max_passes=4000,
                       patience=10 ** 9)
        assert st is not None and st.converged and root is not None
        assert abs(st.fos - root.fos) > 3.0 * tol, (st.fos, root.fos)

    def test_converged_still_does_not_mean_the_thrust_state_is_admissible(self):
        """``thrust_is_admissible`` is a separate and weaker preference, and
        this version does not merge the two. A branch can satisfy the pair
        test — X no longer MOVING — and still fail the admissibility test,
        which asks about the sign of the thrust it settled on."""
        from ogr_slip2d.interslice import thrust_is_admissible
        seen = {}
        # Two planes and not one, because on either of them alone the answer
        # is unanimous: every converged branch of the 50 degree wedge is
        # admissible and every converged branch of the 35 degree one is not.
        # That unanimity is itself the point — admissibility is a property of
        # the slope, and convergence says nothing about it.
        for beta in (50.0, 35.0):
            system = _wedge(beta)
            for lam in (-1.0, -0.4, 0.0, 0.2, 0.6, 1.0):
                for moment in (False, True):
                    st = _branch(system, lam, 1e-6, moment)
                    if st is None or not st.converged:
                        continue
                    seen[(beta, lam, moment)] = thrust_is_admissible(st)
        assert seen, "the sweep stopped producing converged branches"
        assert set(seen.values()) == {True, False}, sorted(seen.items())

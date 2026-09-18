# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""v0.1.176 (D125) — a branch the damped iteration cannot settle is rescued,
not lost.

WHAT INVARIANT THIS PROTECTS. ``interslice.solve_branch`` iterates each
equilibrium branch of Spencer and GLE as a DAMPED Picard map,
``F = 0.5*(F + f_new)``, and a damped Picard map has a flip: where the slope
of the fixed-point map crosses -3 the iterate stops converging and settles
on a period-2 cycle, with the fixed point it was after sitting untouched
between the two phases. Until this version such a branch left through the
stall test, no counter said so, and the lambda was lost. On the published
Spencer circle of verification problem 091 (Leshchinsky and Han 2004, the
weak-foundation wall) the flip sits at lambda 0.3670 and the root of
F_f = F_m at 0.3677, so the outer search only ever saw the negative half of
F_f - F_m and answered "no lambda-bracket" for sixteen versions, publishing
a fallback 2.0 % under the manual while the root sits 0.4 % under it. The
rule this file enforces is therefore: **a branch that is still moving after
STALL_PATIENCE passes is handed to a bounded relaxation (Wegstein 1958)
before it is given up on, and what the rescue settles on is a fixed point
of the same map — start-independent, and reproduced by one more march.**

WHY THE ANCHOR IS NOT IN THIS FILE. The 0.964 the manual publishes lives in
the verification bank's ``d125()``, outside this repository, and the closed
form of the plane wedge lives in ``tests/test_janbu_wedge_v1142.py``. A test
of the mechanism that also owned the reference value could be made to pass
by moving the reference. What is asserted here is identities: the rescued
value is a fixed point, it does not depend on where the iteration started,
the same circle at 30 and at 50 slices agrees to the discretisation, and a
slow branch lands on the fixed point that the stall test used to abandon
(the 0.83037 of ``test_branch_contraction_v1172``, computed here on the
spot with the stall test out of the way rather than remembered).

WHAT THE FICHA ASKED FOR, AND WHAT THE MEASUREMENT SAID INSTEAD. P-D125
named three hypotheses — a root outside the sampled range, a branch that
diverges because of the support force, two parallel branches — and on the
091 circle all three are refuted: the root sits inside the calibrated grid,
the same flip exists with every support removed in memory (the root moves
by 0.004 in lambda between no support and full support), and the branches
cross transversally. The defect is the branch SOLVER, which is why the fix
is in ``solve_branch`` and not in the lambda grid, the support terms or the
0.02 of ``FALLBACK_RESIDUAL_LIMIT``, none of which moves.

WHICH CASES MEASURE THE DEFECT AND WHICH ARE CONTROL, counted rather than
asserted. Against the tree of 0.1.175, with only this file added, the
COVERAGE classes fail and the CONTROL class passes; the numbers are in the
docstring of each class, and a test whose docstring does not say which of
the two it is will be read as the one it is not.

WHAT THIS FILE DOES NOT CLAIM, said out loud because promising more coverage
than a change delivers is what cost this project two versions in v0.1.82-84:

* it does not claim the rescue reaches a branch the thrust bound of D118
  cuts first. The force branch of verification problem 085 dies of thrust
  overflow from lambda 1.51 on, with or without the rescue, and that problem
  is closed in the bank as NOT REPRODUCIBLE with its curve, not here;
* it does not claim the ordinary acceptance is any better than it was: the
  contraction test of v0.1.172 can wait a hundred passes for two decreasing
  steps that only floating-point noise decides (measured on the 091 circle
  at 30 slices, admitted on pass 107 while sitting on its fixed point from
  pass 45). That is reported in the changelog and left where it is, because
  changing it moves every branch;
* it does not claim a digit of the verification bank; the bank's own A/B
  against ``Evaluaciones/0.1.175`` does that.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import math

#: The plane wedge of ``test_janbu_wedge_v1142``, built here rather than
#: imported: the modules in ``tests/`` cannot import one another outside
#: the runner.
H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
NSLICES = 50

#: The slow moment branch of the 50 degree plane at this lambda: its fixed
#: point is 0.83037 and it takes 585 damped passes at 1e-12 to reach it, so
#: the stall test abandoned it on pass 85. From ``test_branch_contraction_v1172``.
SLOW_BETA = 50.0
SLOW_LAMBDA = 2.0

#: The cell of ``test_max_iterations_scope_v1173`` where the pass budget
#: used to eat a lambda: the 55 degree plane, Spencer, at 1e-10. Its settled
#: answer is what the same solver returns at 1e-8 and 1e-9.
BUDGET_BETA = 55.0
BUDGET_TOL = 1e-10
SETTLED_TOLS = (1e-8, 1e-9)

#: The published Spencer circle of verification problem 091 and the lambda
#: at which its force branch cycles.
CIRCLE_091 = (4.658, 15.0, 10.934)
CYCLE_LAMBDA = 0.40


# ----------------------------------------------------------------------
# The three-tiered geosynthetic wall of verification problems 87-94 with the
# weak foundation of the 091 (Leshchinsky and Han 2004, "Foundation Soil"),
# written out from the bank's ``_tools/muro_bancadas.py`` so that the suite
# runs on a machine that does not have the bank.
# ----------------------------------------------------------------------
X_PIE, Y_CIMIENTO, Y_CORONACION, X_DERECHA, X_IZQUIERDA = 6.0, 6.0, 15.0, 24.0, -2.0
RETRANQUEO, ANCHO_BLOQUE, SEPARACION, LONGITUD = 1.2, 0.2, 0.6, 6.3
N_BANCADAS = 3


def _caras():
    return [X_PIE + i * RETRANQUEO for i in range(N_BANCADAS)]


def _cotas():
    h = (Y_CORONACION - Y_CIMIENTO) / N_BANCADAS
    return [(Y_CIMIENTO + i * h, Y_CIMIENTO + (i + 1) * h)
            for i in range(N_BANCADAS)]


def _wall():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  Geosynthetic, SupportInstance)

    pts = [(X_IZQUIERDA, 0.0), (X_DERECHA, 0.0), (X_DERECHA, Y_CORONACION)]
    for x, (y_base, y_techo) in reversed(list(zip(_caras(), _cotas()))):
        pts.append((x, y_techo))
        pts.append((x, y_base))
    pts.append((X_IZQUIERDA, Y_CIMIENTO))
    p = Project("091")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in pts], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(
        polyline=Polyline(vertices=[Vertex(X_IZQUIERDA, Y_CIMIENTO),
                                    Vertex(X_DERECHA, Y_CIMIENTO)]),
        btype=BoundaryType.MATERIAL))
    for x_cara, (y_base, y_techo) in zip(_caras(), _cotas()):
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[
                Vertex(x_cara, y_base), Vertex(x_cara + ANCHO_BLOQUE, y_base),
                Vertex(x_cara + ANCHO_BLOQUE, y_techo), Vertex(x_cara, y_techo)]),
            btype=BoundaryType.MATERIAL))
    fill = Material(name="fill", unit_weight=18.0, sat_unit_weight=18.0,
                    strength=MohrCoulomb(cohesion=0.0, friction_angle=34.0))
    foundation = Material(name="foundation", unit_weight=18.0,
                          sat_unit_weight=18.0,
                          strength=MohrCoulomb(cohesion=0.0, friction_angle=18.0))
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


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(*CIRCLE_091)


def _evaluate(project, method_id, n, tolerance=1e-4):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.search import GridSearch
    ev = GridSearch(method=method_registry()[method_id](
        tolerance=tolerance, max_iterations=50),
        num_slices=n, min_area=0.0)
    return ev.evaluate_circle(project, _circle())


def _system_091(n=NSLICES, tolerance=1e-4):
    """The GLESystem ``Spencer.compute_fos`` builds for the circle, captured
    off the class rather than rebuilt, so that it is the engine's own rows
    and support terms and not a copy that could drift."""
    from ogr_slip2d.methods.spencer import Spencer
    cap = []
    orig = Spencer._inner_solve

    def spy(self, slices, lam, system):
        if system not in cap:
            cap.append(system)
        return orig(self, slices, lam, system)

    Spencer._inner_solve = spy
    try:
        _evaluate(_wall(), "spencer", n, tolerance)
    finally:
        Spencer._inner_solve = orig
    assert len(cap) == 1, len(cap)
    return cap[0]


def _branch(system, lam, tolerance, moment=False, initial=1.0, **kw):
    from ogr_slip2d.interslice import solve_branch
    kw.setdefault("max_passes", system.max_passes)
    return solve_branch(system.rows, system.lambda_boundary(lam),
                        system._moment_fos if moment else None,
                        tolerance, initial, **kw)


@contextlib.contextmanager
def _unrescued():
    """The branch solver of 0.1.175, in-process: the switch is read at call
    time inside ``solve_branch``. The runner has no ``monkeypatch``, so the
    restoring is written out (rule 5)."""
    import ogr_slip2d.interslice as interslice
    keep = getattr(interslice, "BRANCH_RESCUE", None)
    if keep is None:
        # A tree without the switch has no rescue to turn off, so the
        # CONTROL cases mean the same thing on both sides of the change.
        yield
        return
    interslice.BRANCH_RESCUE = False
    try:
        yield
    finally:
        interslice.BRANCH_RESCUE = keep


# ----------------------------------------------------------------------
def _ground(project):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0)], closed=True)
    ext.ensure_ccw()
    project.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    project.materials = [Material(
        name="S", unit_weight=GAMMA,
        strength=MohrCoulomb(cohesion=COH, friction_angle=PHI))]
    return project


def _bare():
    from ogr_core.project import Project
    return _ground(Project("bare"))


def _anchored(application):
    from ogr_core.geometry import Vertex
    from ogr_core.project import Project
    from ogr_core.support import (EndAnchored, ForceApplication,
                                  ForceOrientation, SupportInstance)
    p = _ground(Project("anchored"))
    p.support_types = [EndAnchored(anchor_capacity=120.0,
                                   out_of_plane_spacing=1.0)]
    p.supports = [SupportInstance(
        type_id="end_anchored", head=Vertex(34.0, 6.0), tail=Vertex(48.0, 11.0),
        force_application=(ForceApplication.ACTIVE if application == "active"
                           else ForceApplication.PASSIVE),
        orientation=ForceOrientation.USER_DEFINED, user_angle_deg=15.0)]
    return p


def _plane(beta_deg):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(TOE, 0.0), Vertex(TOE + H / math.tan(math.radians(beta_deg)), H)]))


def _wedge_result(method_id, project, beta, tolerance):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.slicer import slice_surface
    surface = _plane(beta)
    sl = slice_surface(project, surface, num_slices=NSLICES)
    return method_registry()[method_id](
        tolerance=tolerance, max_iterations=400).compute_fos(project, surface, sl)


def _wedge_system(beta, tolerance):
    from ogr_slip2d.interslice import GLESystem
    from ogr_slip2d.moment_balance import axis_for
    from ogr_slip2d.slicer import slice_surface
    p = _bare()
    surface = _plane(beta)
    sl = slice_surface(p, surface, num_slices=NSLICES)
    n = len(sl.slices)
    return GLESystem(sl.slices, [1.0] * (n + 1), 0.0, 0.0, 1.0, None, None,
                     None, axis_for(p, surface), tolerance=tolerance)


# ======================================================================
# A. The cycle, and what the rescue makes of it.
# ======================================================================
class TestTheRescueSettlesTheCycle:
    """COVERAGE. Against 0.1.175 every case here fails: the force branch of
    the 091 circle at lambda 0.40 leaves through the stall test on pass 81
    with ``F`` on one phase of a period-2 cycle, and the outer search falls
    back with a residual of 0.0608."""

    def test_the_damped_iteration_cycles_and_the_rescue_does_not(self):
        """The defect and the fix on the same branch, in one process: with
        the switch off the branch is abandoned on pass 1 + STALL_PATIENCE
        with an empty ``abandoned`` (a stall, not an overflow and not the
        budget); with it on, the same branch converges and says it was
        rescued."""
        from ogr_slip2d.interslice import STALL_PATIENCE
        system = _system_091()
        with _unrescued():
            was = _branch(system, CYCLE_LAMBDA, 1e-4)
        assert was is not None and was.converged is False, was
        assert was.abandoned == "" and was.passes == STALL_PATIENCE + 1, (
            was.abandoned, was.passes)
        now = _branch(system, CYCLE_LAMBDA, 1e-4)
        assert now is not None and now.converged is True, now
        assert now.rescued is True
        assert now.passes < system.max_passes, now.passes

    def test_the_rescued_value_does_not_depend_on_where_it_started(self):
        """A period-2 cycle traps every start value on the same two phases
        (measured: nine starts from 0.9124 to 40.0). The rescued value is
        one number, which is what makes it a fixed point and not a phase."""
        system = _system_091()
        values = []
        for initial in (0.9, 1.0, 1.2):
            st = _branch(system, CYCLE_LAMBDA, 1e-4, initial=initial)
            assert st is not None and st.converged, (initial, st)
            values.append(st.fos)
        spread = max(values) - min(values)
        assert spread < 10.0 * 1e-4, values

    def test_and_one_more_march_reproduces_it(self):
        """Rule 1 without a reference value: a fixed point is a number the
        map gives back. Restarted AT the rescued value the damped iteration
        stays within the tolerance of it, which a phase of the cycle would
        not (the two phases sit 0.2 apart)."""
        system = _system_091()
        st = _branch(system, CYCLE_LAMBDA, 1e-4)
        assert st is not None and st.converged
        again = _branch(system, CYCLE_LAMBDA, 1e-4, initial=st.fos)
        assert again is not None and again.converged, again
        assert abs(again.fos - st.fos) < 10.0 * 1e-4, (again.fos, st.fos)

    def test_the_outer_search_now_brackets_the_root(self):
        """What the bank sees: a bracketed root instead of the nearest
        sample. The lambda is asserted as a band because the flip and the
        root are measured at 0.3670 and 0.3677; the factor is asserted
        against the SAME circle at 30 slices, which the damped iteration
        already solved (it is pinned bit for bit in
        ``test_support_failure_v1161``), as a discretisation identity."""
        r50 = _evaluate(_wall(), "spencer", 50)
        assert r50 is not None and r50.is_valid, (r50 and r50.error_message)
        d = r50.details or {}
        assert d.get("lambda_search_fell_back") is False, d
        assert 0.36 <= d["lambda"] <= 0.375, d["lambda"]
        r30 = _evaluate(_wall(), "spencer", 30)
        assert r30 is not None and r30.is_valid
        assert abs(r50.fos - r30.fos) / r30.fos < 0.01, (r50.fos, r30.fos)

    def test_and_says_how_many_lambdas_it_rescued(self):
        r50 = _evaluate(_wall(), "spencer", 50)
        d = r50.details or {}
        assert d.get("lambdas_rescued", 0) > 0, d


# ======================================================================
# B. The slow family: a crawl is extrapolated, not damped.
# ======================================================================
class TestTheSlowBranchReachesItsFixedPoint:
    """COVERAGE. The other face of the same relaxation. Against 0.1.175 the
    moment branch of the 50 degree plane at lambda 2.0 is abandoned by the
    stall test on pass 85 at 1e-4 (``test_branch_contraction_v1172`` pins
    that as the criterion's honest limit), and the 55 degree plane at 1e-10
    loses a lambda to the pass budget (``test_max_iterations_scope_v1173``
    pins that as the D117 cell)."""

    def _fixed_point(self, system):
        """The branch driven to its fixed point with the stall test out of
        the way and a generous budget: a yardstick computed on the spot."""
        st = _branch(system, SLOW_LAMBDA, 1e-12, moment=True,
                     max_passes=100000, patience=10 ** 9)
        assert st is not None and st.converged, st
        return st.fos

    def test_the_stalled_moment_branch_now_converges_to_it(self):
        system = _wedge_system(SLOW_BETA, 1e-4)
        root = self._fixed_point(system)
        with _unrescued():
            was = _branch(system, SLOW_LAMBDA, 1e-4, moment=True)
        assert was is not None and was.converged is False, was
        for tol in (1e-4, 1e-10):
            st = _branch(system, SLOW_LAMBDA, tol, moment=True)
            assert st is not None and st.converged and st.rescued, (tol, st)
            assert abs(st.fos - root) < 10.0 * tol, (tol, st.fos, root)

    def test_the_budget_no_longer_eats_the_55_degree_lambda(self):
        """The D117 cell, turned round: the lambda the shipped budget lost
        is now solved inside it, and the answer is the one the same solver
        settles on where the budget was never reached."""
        p = _bare()
        settled = [_wedge_result("spencer", p, BUDGET_BETA, tol).fos
                   for tol in SETTLED_TOLS]
        limit = 0.5 * (settled[0] + settled[1])
        spread = abs(settled[0] - settled[1])
        assert spread > 0.0, settled
        r = _wedge_result("spencer", p, BUDGET_BETA, BUDGET_TOL)
        d = r.details or {}
        assert d.get("lambdas_lost_to_budget", 0) == 0, d
        assert abs(r.fos - limit) < 10.0 * spread, (r.fos, limit, spread)


# ======================================================================
# C. What is counted, and what the result says.
# ======================================================================
class TestWhatIsCountedAndSaid:
    """COVERAGE. The rescue could not have been found through the result
    it hid behind: on the 091 circle 12 of 16 lambdas were lost and every
    counter read zero, because ``GLESystem.branches`` returned before
    counting whenever the OTHER branch was ``None``, and the stall exit was
    counted nowhere at all."""

    def test_a_loss_is_counted_even_when_the_partner_is_none(self):
        """At lambda 1.0 on the 091 circle the force branch is ``None`` and
        the moment branch dies of thrust overflow. That overflow was
        invisible until this version."""
        system = _system_091()
        force, moment = system.states(1.0)
        assert force is None, force
        assert moment is not None and moment.abandoned == "thrust overflow"
        before = system.n_thrust_overflow
        system.branches(1.0)
        assert system.n_thrust_overflow == before + 1

    def test_a_stall_is_counted(self):
        system = _system_091()
        before = (system.n_stalled, system.n_passes_exhausted,
                  system.n_thrust_overflow)
        with _unrescued():
            pair = system.branches(CYCLE_LAMBDA)
        assert pair == (None, None), pair
        assert system.n_stalled == before[0] + 1, (before, system.n_stalled)
        assert system.n_passes_exhausted == before[1]
        assert system.n_thrust_overflow == before[2]

    def test_and_so_is_a_rescue(self):
        """As a delta: the captured system already carries the counts of
        the ``compute_fos`` that built it."""
        system = _system_091()
        before = (system.n_rescued, system.n_stalled)
        pair = system.branches(CYCLE_LAMBDA)
        assert pair[0] is not None and pair[1] is not None, pair
        assert system.n_rescued == before[0] + 1, (before, system.n_rescued)
        assert system.n_stalled == before[1], (before, system.n_stalled)

    def test_both_exits_publish_the_two_keys(self):
        """The bracketed exit (the rescued 091 circle) and the fallback exit
        (the same circle with the rescue off, which brackets nothing) both
        carry the two counts, so a reader of ``details`` does not have to
        know which exit produced it."""
        bracketed = _evaluate(_wall(), "spencer", 50)
        with _unrescued():
            fallback = _evaluate(_wall(), "spencer", 50)
        for r in (bracketed, fallback):
            d = r.details or {}
            assert "lambdas_lost_to_stall" in d, d.keys()
            assert "lambdas_rescued" in d, d.keys()
        assert (fallback.details or {}).get("lambda_search_fell_back") is True
        assert (fallback.details or {})["lambdas_lost_to_stall"] > 0
        assert (bracketed.details or {})["lambdas_rescued"] > 0

    def test_the_fallback_of_a_reinforced_surface_keeps_the_d94_key(self):
        """Until this version the fallback exit skipped
        ``support_failure_details``, so the one exit where the reinforcement
        most needs explaining was the one that could not. The key is
        present only when a support could not be priced (D94: "no key" and
        "a failure with no text" must not be confused), so a failure is
        injected on the terms the solver receives, and the same injection
        through the bracketed exit is the control that the plumbing is the
        same on both."""
        import dataclasses
        import ogr_slip2d.support_integration as si
        keep = si.resolve_support_terms

        def failing(*args, **kwargs):
            return dataclasses.replace(keep(*args, **kwargs),
                                       failure="rescue test: priced nothing")

        si.resolve_support_terms = failing
        try:
            with _unrescued():
                fallback = _evaluate(_wall(), "spencer", 50)
            bracketed = _evaluate(_wall(), "spencer", 50)
        finally:
            si.resolve_support_terms = keep
        d = fallback.details or {}
        assert d.get("lambda_search_fell_back") is True, d
        assert d.get("support_failure") == "rescue test: priced nothing", sorted(d)
        assert (bracketed.details or {}).get("support_failure") ==             "rescue test: priced nothing"

    def test_the_damping_sits_inside_the_bounds(self):
        """The ordinary update is the relaxation with omega = 0.5, so 0.5
        has to be an allowed value — otherwise the rescue could not even
        reproduce the iteration it takes over from — and 0.25, the value
        that undoes the flip at f' = -3, has to be reachable."""
        from ogr_slip2d import interslice
        lo = interslice.RESCUE_OMEGA_MIN
        hi = interslice.RESCUE_OMEGA_MAX
        assert lo <= 0.25 < 0.5 <= hi, (lo, hi)
        assert interslice.BRANCH_RESCUE is True

    def test_the_stall_reaches_the_user_as_a_note(self):
        from ogr_slip2d.analysis_runner import lambda_fallback_notes
        with _unrescued():
            r = _evaluate(_wall(), "spencer", 50)
        notes = lambda_fallback_notes(r)
        assert any("stopped improving" in n for n in notes), notes
        # The three substrings the verification bank greps its notes for
        # must not appear, or a closure elsewhere turns green for nothing.
        for n in notes:
            assert "edge of the search grid" not in n
            assert "path_optimize" not in n
            assert not ("stable" in n and "head" in n), n


# ======================================================================
# D. The control: what the rescue must leave alone.
# ======================================================================
class TestTheControl:
    """Declared CONTROL: green on BOTH sides of this change, here to guard
    against an error THIS design can make — buying the cycle by disturbing
    the branches that were already converging — and not against the defect
    it removes."""

    def test_the_four_constants_did_not_move(self):
        from ogr_slip2d import interslice
        assert interslice.STALL_PATIENCE == 80
        assert interslice.MAX_PASSES == 400
        assert interslice.FALLBACK_RESIDUAL_LIMIT == 0.02
        assert interslice.THRUST_SCALE_LIMIT == 10.0

    def test_a_branch_that_converges_inside_the_patience_is_untouched(self):
        """Bit for bit, in one process: every branch of the wedge ladder at
        the loose tolerance converges long before pass 80, and the switch
        must not change one of them. The proof is the same as for
        STALL_PATIENCE — the first 80 passes are the old loop instruction
        for instruction — and the measurement is what makes it a test."""
        from ogr_slip2d.interslice import STALL_PATIENCE
        checked = 0
        for beta in (35.0, 40.0, 45.0):
            for moment in (False, True):
                system = _wedge_system(beta, 1e-3)
                for lam in (0.0, 0.2, 0.6):
                    with _unrescued():
                        was = _branch(system, lam, 1e-3, moment=moment)
                    now = _branch(system, lam, 1e-3, moment=moment)
                    assert was is not None and now is not None, (beta, lam)
                    if not was.converged or was.passes > STALL_PATIENCE:
                        continue
                    assert now.fos == was.fos and now.passes == was.passes, (
                        beta, lam, moment, was.fos, now.fos)
                    assert getattr(now, "rescued", False) is False
                    checked += 1
        assert checked >= 12, checked

    def test_a_root_found_without_the_rescue_is_the_same_root_with_it(self):
        """The outer search on the ladder at the shipped 1e-3: wherever the
        old solver bracketed a root, the new one publishes the identical
        factor. Rows that fell back are not compared — a fallback is the
        nearest sample and the rescue is allowed to move which sample is
        nearest — and the count of compared rows is asserted so this cannot
        pass by comparing nothing."""
        compared = 0
        for tag, p in (("bare", _bare()), ("active", _anchored("active")),
                       ("passive", _anchored("passive"))):
            for beta in (35.0, 40.0, 45.0, 50.0):
                for mid in ("spencer", "gle_morgenstern_price"):
                    with _unrescued():
                        was = _wedge_result(mid, p, beta, 1e-3)
                    now = _wedge_result(mid, p, beta, 1e-3)
                    if was.fos is None or (was.details or {}).get(
                            "lambda_search_fell_back"):
                        continue
                    assert now.fos == was.fos, (tag, beta, mid, was.fos, now.fos)
                    compared += 1
        assert compared >= 12, compared

    def test_a_branch_already_under_the_tolerance_is_left_to_the_old_rule(self):
        """The 091 circle at 30 slices: the damped iteration solves it, one
        of its branches only after pass 80, and that branch is already
        within the tolerance when the rescue could take it — so it must
        not. Bit for bit, because ``test_support_failure_v1161`` pins this
        very number against the bank."""
        with _unrescued():
            was = _evaluate(_wall(), "spencer", 30)
        now = _evaluate(_wall(), "spencer", 30)
        assert was is not None and was.is_valid
        assert now.fos == was.fos, (was.fos, now.fos)
        assert (now.details or {}).get("lambdas_rescued", 0) == 0

    def test_no_branch_converges_before_its_third_pass(self):
        """The v0.1.172 floor, unchanged: the rescue cannot start before
        pass 81, so it cannot lower it."""
        system = _wedge_system(40.0, 1e-3)
        for lam in (0.0, 0.2):
            for moment in (False, True):
                st = _branch(system, lam, 1e-3, moment=moment)
                assert st is not None and st.converged
                assert st.passes >= 3, (lam, moment, st.passes)

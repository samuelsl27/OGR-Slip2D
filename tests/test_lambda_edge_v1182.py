# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""v0.1.182 (D149) — the thrust criterion decides which λ the search PREFERS,
not which λ the search is allowed to SEE.

WHAT INVARIANT THIS PROTECTS. Spencer and GLE find their answer by bracketing
the inter-slice inclination λ where the force and the moment factors of safety
agree. ``GLESystem.branches`` hands back nothing at all for a λ whose
inter-slice thrust comes out in net tension, and that is a PREFERENCE its own
docstring has described as such since v0.1.130 — the search should prefer an
admissible root over an inadmissible one. But the preference was being applied
to the SCAFFOLDING: the criterion is evaluated at grid NODES, the answer is
not at a node, and deleting a node deletes the bracket that node was one side
of. The root that vanishes with it may itself be admissible. This file fixes
the sampling in place and leaves the criterion untouched.

WHAT THE FICHA ASKED FOR, AND WHAT THE MEASUREMENT SAID INSTEAD. Bank defect
D149 names one cell — a 45 degree plane, a passive 120 kN/m anchor, GLE, 50
slices, 1e-10 — and says it falls back to a reserve value at λ = 0.2 with a
residual of 6.144e-5. THAT CELL IS CURED, and has been since v0.1.181. Its
numbers reproduce to the digit with ``LAMBDA_GAP_REFINE`` switched off, which
is the λ search of v0.1.180: the ficha was written against an engine four
versions old, and D148's gap refinement cured this cell as a side effect
nobody noticed. Writing the obvious test on that cell would have produced a
case that is green on both trees and measures nothing.

WHAT SPLITS THE DEFECT IN TWO, and it is the finding worth keeping. Write
lam_E for where the interior thrust sum crosses zero and lam_g for where
``F_f - F_m`` does.

  * lam_E BELOW lam_g — the root is ADMISSIBLE and only the node carrying the
    other sign was deleted. ``refine_lambda_gap`` probes from the surviving
    edge into the lost node, lands between the two and brackets in one step.
    Cured by v0.1.181. This is the ficha's cell: 0.107787 against 0.189970.
  * lam_g BELOW lam_E — the root is on the inadmissible side. The refinement
    probes towards lam_E, which is PAST the root, and spends its budget
    without crossing anything. Nobody reaches it. This is what is left.

THE FIXTURE IS THEREFORE NOT THE FICHA'S, and it is found by moving one input.
Same plane, same anchor, same geometry: at 134 kN/m the engine publishes
+0.243 % of the closed form with ``converged`` true, an empty
``error_message`` and ``admissible`` true, while at 137 kN/m — two per cent
more — it publishes the closed form exactly, because there EVERY node is
inadmissible and the all-or-nothing sweep of v0.1.106 fires and finds the
root. A discontinuity that size across a 2 % change of input is the statement
of D149 with something to hold on to, and it is measured against an external
reference rather than a snapshot: on a plane the sliding mass is one rigid
wedge, ``F_f`` is exactly constant in λ and equal to the closed form (Coulomb
1776; Duncan & Wright 2005 §6, as ``test_janbu_wedge_v1142`` asserts premise
by premise), so ANY root of ``F_f - F_m`` is the wedge by identity and not by
luck.

HOW THE RULE 7 GATE WAS BUILT. The bank cannot supply it: over 340 rows at
0.1.181, 334 measured, not one takes this path — 310 reject no λ at all, 3
have none left, 1 brackets on its own and 20 have the shape but no sign change
anywhere, so the recovery rolls back on every one of them. A census that could
only say "zero" would be the trap this project has walked into ten times
(D101, D103, D118, D127, D129), so the gate is the capacity family above,
where the switch is worth 0.243 % against a closed form, and
``TestTheSwitchMovesANumber`` asserts it from both sides in the same case.

WHICH CASES MEASURE THE CHANGE AND WHICH ARE CONTROL, measured rather than
guessed and named rather than counted. Run against the tree of 0.1.181 with
only this file added, 7 of the 23 FAIL and 16 PASS.

Five fail on a measured difference in the published answer, and they are the
file's case for itself: ``test_with_the_recovery_it_is_the_wedge`` and
``test_both_capacities_now_report_their_own_closed_form`` (1.3649727 against a
closed form of 1.3616583, i.e. +0.243 %), ``test_it_says_the_thrust_is_not_
admissible`` (the old tree publishes the flag TRUE on that surface),
``test_and_it_stops_calling_itself_a_fallback`` and
``test_the_note_reaches_the_reader`` (five notes there, none of them this
one).

Two fail for the absence of a symbol, which is WEAK discrimination and is
labelled here rather than counted as strength: ``test_it_is_on_by_default``
raises ``AttributeError``, and ``test_and_turning_it_off_changes_the_
published_factor`` fails because without the switch the context manager is a
no-op and the case ends up comparing a number with itself.

Of the 16 that pass, three are MADE to pass and would be a worry if they did
not: ``test_without_it_the_same_surface_is_off_by_a_tenth_of_a_percent``,
``test_and_it_used_to_say_the_opposite_on_the_same_surface`` and
``test_and_they_did_not_before`` all describe the OLD behaviour through the
A/B, so they hold on both trees by construction. The rest are the two CONTROL
classes — the mechanism and the lam_E/lam_g taxonomy, which are statements
about the sampling this version does not touch — plus
``TestWhatItDoesNotTouch``, whose whole point is that it was green before and
has to stay green.

WHAT THIS FILE DOES NOT CLAIM. Not that the recovery helps any surface in the
verification bank — it helps none of them today, and that is published rather
than hidden. Not that an inadmissible root is a good answer: it is a solved
root reported WITH its flag, which is what a preference means, and whether the
tension is real is the question v0.1.106 declined to answer and this version
declines too. Not anything about λ outside the configured range: the default
grid starts at -0.1, and the spurious root of the Talbingo circle at -0.979
that ``thrust_is_admissible`` was written for lies outside it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import math

H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
NSLICES = 50
TIGHT = 1e-10
MAX_IT = 400
BETA = 45.0
METHOD = "gle_morgenstern_price"

#: The three capacities, and what each one is FOR.
#: 134 discriminates: five nodes survive, they share one sign, the root sits
#: at λ = 0.390 on the inadmissible side. 120 is the ficha's own cell, family
#: B1, which v0.1.181 already reaches — a control that goes red if this change
#: disturbs what D148 fixed. 137 is family A: no node survives at all, so the
#: v0.1.106 sweep fires and the recovery must not even run.
CAP_LOST, CAP_CURED, CAP_ALL_OUT = 134.0, 120.0, 137.0

_SYSTEMS: dict = {}


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


def _anchored(cap):
    """The plane with a PASSIVE end anchor of ``cap`` kN/m.

    Byte for byte the fixture of ``tests/test_anchored_wedge_root_v1177.py``
    except for the capacity, which is the only thing this file varies.
    """
    from ogr_core.geometry import Vertex
    from ogr_core.support import (EndAnchored, ForceApplication,
                                  ForceOrientation, SupportInstance)
    p = _bare()
    p.support_types = [EndAnchored(anchor_capacity=cap,
                                   out_of_plane_spacing=1.0)]
    p.supports = [SupportInstance(
        type_id="end_anchored",
        head=Vertex(34.0, 6.0), tail=Vertex(48.0, 11.0),
        force_application=ForceApplication.PASSIVE,
        orientation=ForceOrientation.USER_DEFINED, user_angle_deg=15.0)]
    return p


def _plane(beta_deg=BETA):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(TOE, 0.0), Vertex(_daylight_x(beta_deg), H)]))


def _slices(project, beta_deg=BETA):
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, _plane(beta_deg), num_slices=NSLICES)
    assert sl is not None and sl.slices, "the plane produced no slices"
    return sl


def _system(cap, method_id=METHOD):
    """The ``GLESystem`` the METHOD builds, cached.

    Not the ``_system()`` of ``test_interslice_budget_v1159.py``, which passes
    ``sup=None`` and so reaches the FORCE branch with the reinforcement and
    the MOMENT closure without it — measuring a system nobody solves. Mirrors
    ``gle.py``: the seismic pair, the sign of the driving force, the axis, the
    resolved support and the branch budget. Cached because building it slices
    the surface and several classes below want the same one.
    """
    from ogr_slip2d.interslice import GLESystem, branch_budget
    from ogr_slip2d.moment_balance import axis_for
    from ogr_slip2d.support_integration import resolve_support_terms

    clave = (cap, method_id)
    if clave in _SYSTEMS:
        return _SYSTEMS[clave]
    project = _anchored(cap)
    surface = _plane()
    sl = _slices(project)
    s_list = sl.slices
    raw = sum(s.weight * math.sin(s.base_angle) for s in s_list)
    sign = 1.0 if raw >= 0 else -1.0
    sup = resolve_support_terms(project, surface, sl, sign)
    if method_id == "spencer":
        shape = [1.0] * (len(s_list) + 1)
    else:
        from ogr_slip2d.methods.gle import GLEMorgensternPrice
        m = GLEMorgensternPrice(tolerance=TIGHT, max_iterations=MAX_IT)
        shape = [m.f_func(x, s_list[0].base_x_left, s_list[-1].base_x_right)
                 for x in m._boundary_x(sl)]
    system = GLESystem(s_list, shape, 0.0, 0.0, sign, None, None, sup,
                       axis_for(project, surface), tolerance=TIGHT,
                       initial_fos=1.0, max_passes=branch_budget(MAX_IT))
    _SYSTEMS[clave] = system
    return system


def _closed_form(cap):
    """The wedge, from geometry and the model's own support terms.

    The external reference of this file: Coulomb 1776; the modern statement,
    with the support resolved on the base, is Duncan & Wright 2005 §6. Same
    expression as ``_wedge`` in ``test_janbu_wedge_v1142.py``, where every
    premise it rests on is asserted rather than assumed. ``W`` comes from
    geometry alone and never from the slicer.
    """
    from ogr_slip2d.external_forces import slice_forces
    from ogr_slip2d.support_integration import resolve_support_terms

    project = _anchored(cap)
    sl = _slices(project)
    raw = sum(slice_forces(s, 0.0, 0.0).w_total * math.tan(s.base_angle)
              for s in sl.slices)
    sup = resolve_support_terms(project, _plane(), sl,
                                1.0 if raw >= 0 else -1.0)
    t_n, t_act, t_pas = ((math.fsum(sup.n_press), sup.total_active_t(),
                          sup.total_passive_t()) if sup.present
                         else (0.0, 0.0, 0.0))
    a = math.radians(BETA)
    W = GAMMA * 0.5 * H * (_daylight_x(BETA) - CREST)
    num = COH * (H / math.sin(a)) + (W * math.cos(a) + t_n) * math.tan(
        math.radians(PHI))
    return (num + t_pas) / (W * math.sin(a) - t_act)


def _result(cap, method_id=METHOD):
    from ogr_slip2d.methods.base import method_registry
    project = _anchored(cap)
    return method_registry()[method_id](
        tolerance=TIGHT, max_iterations=MAX_IT).compute_fos(
            project, _plane(), _slices(project))


def _grid(method_id=METHOD):
    from ogr_slip2d.methods.base import method_registry
    m = method_registry()[method_id](tolerance=TIGHT, max_iterations=MAX_IT)
    return list(m.lambda_grid())


@contextlib.contextmanager
def _no_edge_recovery():
    """The λ search of 0.1.181: the thrust-edge recovery of v0.1.182 off.

    Read at call time inside ``spencer.py`` and ``gle.py`` as
    ``interslice.LAMBDA_EDGE_RECOVERY``, which is why patching the module
    attribute is enough and is not a shortcut. The restoring is written out
    with ``try/finally`` because the runner does not call ``teardown_method``
    (rule 5), and ``getattr(..., None)`` because a tree without the switch has
    no guard to turn off — there the CONTROL cases still mean what they say
    while the discriminating ones fail on a measured difference, which is the
    point of keeping them apart.
    """
    import ogr_slip2d.interslice as interslice
    keep = getattr(interslice, "LAMBDA_EDGE_RECOVERY", None)
    if keep is None:
        yield
        return
    interslice.LAMBDA_EDGE_RECOVERY = False
    try:
        yield
    finally:
        interslice.LAMBDA_EDGE_RECOVERY = keep


def _nodos(cap, method_id=METHOD):
    """The grid, node by node: ``(λ, F_f, F_m, Σ E interior, admissible)``.

    Asked through ``states`` and never through ``branches``, so that looking
    at the grid does not move the engine's own counters or consult its filter
    — the lesson ``_tools/curva_cuna_d119.py`` carries in its header.
    """
    from ogr_slip2d.interslice import thrust_is_admissible
    system = _system(cap, method_id)
    fuera = []
    for lam in _grid(method_id):
        force, moment = system.states(lam)
        if force is None or moment is None:
            continue
        if not (force.converged and moment.converged):
            continue
        interior = force.boundary_e[1:-1]
        fuera.append({"lam": lam, "ff": force.fos, "fm": moment.fos,
                      "g": force.fos - moment.fos,
                      "e": math.fsum(interior) if interior else 0.0,
                      "adm": thrust_is_admissible(force)})
    return fuera


def _cruce(f, lo, hi, pasos=60):
    """Where ``f`` changes sign between ``lo`` and ``hi``, or None."""
    flo, fhi = f(lo), f(hi)
    if flo is None or fhi is None or flo * fhi > 0:
        return None
    for _ in range(pasos):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if fm is None:
            return None
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


def _lam_g(cap):
    system = _system(cap)
    nodos = _nodos(cap)
    par = next(((nodos[i], nodos[i + 1]) for i in range(len(nodos) - 1)
                if nodos[i]["g"] * nodos[i + 1]["g"] < 0), None)
    if par is None:
        return None

    def g(lam):
        force, moment = system.states(lam)
        if force is None or moment is None:
            return None
        return force.fos - moment.fos

    return _cruce(g, par[0]["lam"], par[1]["lam"])


def _lam_e(cap):
    system = _system(cap)
    nodos = _nodos(cap)
    par = next(((nodos[i], nodos[i + 1]) for i in range(len(nodos) - 1)
                if nodos[i]["adm"] != nodos[i + 1]["adm"]), None)
    if par is None:
        return None

    def e(lam):
        force, _moment = system.states(lam)
        if force is None:
            return None
        interior = force.boundary_e[1:-1]
        return math.fsum(interior) if interior else 0.0

    return _cruce(e, par[0]["lam"], par[1]["lam"])


# ======================================================================
class TestTheFilterDeletesOneSideOfTheSignChange:
    """The mechanism, measured on the grid the engine actually sweeps.

    CONTROL: every assertion here is true on both trees, and has to be. It
    describes the SAMPLING, which this version does not change — what changes
    is what the search does afterwards with what the sampling threw away.
    """

    def test_every_node_solves_so_nothing_here_is_a_failed_branch(self):
        """Both branches converge at all nine inclinations, which is what
        makes this a filtering story and not a convergence one."""
        assert len(_nodos(CAP_LOST)) == len(_grid()), _nodos(CAP_LOST)

    def test_the_survivors_all_carry_one_sign(self):
        sup = [v for v in _nodos(CAP_LOST) if v["adm"]]
        assert sup, "no node survived: this is family A, not the fixture"
        assert len({v["g"] > 0 for v in sup}) == 1, sup

    def test_and_the_full_set_does_change_sign(self):
        """So the bracket exists and only the filter hides it."""
        nodos = _nodos(CAP_LOST)
        cruces = [i for i in range(len(nodos) - 1)
                  if nodos[i]["g"] * nodos[i + 1]["g"] < 0]
        assert cruces, [v["g"] for v in nodos]
        i = cruces[0]
        assert not (nodos[i]["adm"] and nodos[i + 1]["adm"]), (
            "the crossing pair survived the filter, so nothing was hidden")


class TestTheAdmissibilityBoundaryIsNotTheRoot:
    """lam_E against lam_g, which is what splits D149 in two.

    CONTROL on both trees. It is the most reusable case in the file: without
    it, whoever comes next cannot tell the half v0.1.181 cured from the half
    it did not, and would rediscover the distinction the expensive way.
    """

    def test_at_the_lost_capacity_the_root_is_on_the_inadmissible_side(self):
        g, e = _lam_g(CAP_LOST), _lam_e(CAP_LOST)
        assert g is not None and e is not None, (g, e)
        assert g < e, (g, e)

    def test_at_the_cured_capacity_it_is_on_the_admissible_side(self):
        """Which is precisely why ``refine_lambda_gap`` reaches that one: its
        probes walk from the surviving edge towards the lost node and land
        between lam_E and lam_g."""
        g, e = _lam_g(CAP_CURED), _lam_e(CAP_CURED)
        assert g is not None and e is not None, (g, e)
        assert e < g, (g, e)

    def test_the_two_capacities_really_are_different_families(self):
        assert (_lam_g(CAP_LOST) < _lam_e(CAP_LOST)) != (
            _lam_g(CAP_CURED) < _lam_e(CAP_CURED))


class TestTheRecoveredRootIsTheClosedForm:
    """DISCRIMINATES against the tree of 0.1.181. This is the change.

    The reference is external and computed in this file: on a plane the mass
    is one rigid wedge, so a root of ``F_f - F_m`` IS the closed form. No
    assertion below fixes a factor of safety against a stored digit.
    """

    def test_with_the_recovery_it_is_the_wedge(self):
        r = _result(CAP_LOST)
        w = _closed_form(CAP_LOST)
        assert r.fos is not None and r.converged, r.error_message
        assert abs((r.fos - w) / w) < 1e-6, (r.fos, w)

    def test_without_it_the_same_surface_is_off_by_a_tenth_of_a_percent(self):
        with _no_edge_recovery():
            r = _result(CAP_LOST)
        w = _closed_form(CAP_LOST)
        assert r.fos is not None
        assert abs((r.fos - w) / w) > 1e-3, (r.fos, w)

    def test_and_it_stops_calling_itself_a_fallback(self):
        det = (_result(CAP_LOST).details or {})
        assert det.get("lambda_search_fell_back") is False, det
        assert int(det.get("lambda_edge_recovered") or 0) > 0, det


class TestTheDiscontinuityIsWhatThisFixes:
    """DISCRIMINATES. Why the change is not cosmetic.

    Two capacities 2 % apart used to sit on opposite sides of a cliff, because
    at 137 every node is inadmissible and the all-or-nothing sweep of v0.1.106
    fires while at 134 one node survives and it does not. Afterwards both are
    the wedge, and the engine's answer stops depending on whether the filter
    happened to leave a survivor behind.
    """

    def test_both_capacities_now_report_their_own_closed_form(self):
        for cap in (CAP_LOST, CAP_ALL_OUT):
            r, w = _result(cap), _closed_form(cap)
            assert r.fos is not None, cap
            assert abs((r.fos - w) / w) < 1e-6, (cap, r.fos, w)

    def test_and_they_did_not_before(self):
        with _no_edge_recovery():
            malo = _result(CAP_LOST)
            bueno = _result(CAP_ALL_OUT)
        e_malo = abs((malo.fos - _closed_form(CAP_LOST))
                     / _closed_form(CAP_LOST))
        e_bueno = abs((bueno.fos - _closed_form(CAP_ALL_OUT))
                      / _closed_form(CAP_ALL_OUT))
        assert e_malo > 100 * max(e_bueno, 1e-12), (e_malo, e_bueno)


class TestWhatItDoesNotTouch:
    """CONTROL, and the roll-back claim executed rather than asserted in prose.

    A surface that gains no bracket has to come out bit for bit what it was:
    same factor, same λ, same counters, same flag. That is the property which
    makes the bank A/B of this version an identity instead of a promise.
    """

    CLAVES = ("lambda", "lambda_search_fell_back", "lambda_gap_refined",
              "lambda_residual", "lambdas_lost_to_budget",
              "lambdas_lost_to_stall", "lambdas_lost_to_inadmissible",
              "lambdas_rescued", "thrust_admissible")

    def _par(self, cap, method_id=METHOD):
        con = _result(cap, method_id)
        with _no_edge_recovery():
            sin = _result(cap, method_id)
        return con, sin

    def test_the_cured_capacity_is_untouched(self):
        """v0.1.181 already reaches this root through the gap refinement, and
        putting the recovery AFTER it is what keeps that true."""
        con, sin = self._par(CAP_CURED)
        assert con.fos == sin.fos, (con.fos, sin.fos)
        assert int((con.details or {}).get("lambda_edge_recovered") or 0) == 0
        for k in self.CLAVES:
            assert (con.details or {}).get(k) == (sin.details or {}).get(k), k

    def test_the_all_inadmissible_capacity_is_untouched(self):
        """Family A: the v0.1.106 sweep fires first and the recovery is
        guarded out of it, because there nothing is hidden any more."""
        con, sin = self._par(CAP_ALL_OUT)
        assert con.fos == sin.fos, (con.fos, sin.fos)
        assert int((con.details or {}).get("lambda_edge_recovered") or 0) == 0

    def test_spencer_on_the_same_fixture_does_not_move(self):
        """The sharpest control here: same plane, same capacity, the method
        that must not move."""
        con, sin = self._par(CAP_LOST, "spencer")
        assert con.fos == sin.fos, (con.fos, sin.fos)


class TestTheFlagTellsTheTruthAboutTheRecoveredRoot:
    """DISCRIMINATES, and it is rule 7 in the uncomfortable direction.

    The recovered root is on the inadmissible side by construction, so the
    surface that used to publish ``admissible`` true now publishes false and
    says why. That is a search-steering change and it is declared, not buried:
    a preference that never costs anything is not a preference.
    """

    def test_it_says_the_thrust_is_not_admissible(self):
        r = _result(CAP_LOST)
        assert getattr(r, "admissible", True) is False, r.details
        assert r.admissibility_note, "an unflagged relaxation explains nothing"

    def test_and_it_used_to_say_the_opposite_on_the_same_surface(self):
        with _no_edge_recovery():
            r = _result(CAP_LOST)
        assert getattr(r, "admissible", True) is True

    def test_the_note_reaches_the_reader(self):
        """The door in ``lambda_fallback_notes`` is gated on having fallen
        back, and this surface did not. Third time that gate has had to be
        widened, which is why there is a case for it."""
        from ogr_slip2d.analysis_runner import lambda_fallback_notes
        notas = lambda_fallback_notes(_result(CAP_LOST))
        assert notas, "the one search with something new to say said nothing"
        assert any("net tension" in n for n in notas), notas


class TestTheSwitchMovesANumber:
    """Rule 7, asserted from both sides in one case."""

    def test_it_is_on_by_default(self):
        import ogr_slip2d.interslice as interslice
        assert interslice.LAMBDA_EDGE_RECOVERY is True

    def test_and_turning_it_off_changes_the_published_factor(self):
        con = _result(CAP_LOST).fos
        with _no_edge_recovery():
            sin = _result(CAP_LOST).fos
        assert con != sin, (con, sin)


class TestTheFixtureStillDiscriminates:
    """If the branch solver moves again, this file must go loud, not vacuous.

    The capacity that discriminates sits 2 % below the one where every node is
    inadmissible, so the window is narrow on purpose and worth pinning.
    """

    def test_the_anchor_is_actually_resolved(self):
        from ogr_slip2d.support_integration import resolve_support_terms
        p = _anchored(CAP_LOST)
        sup = resolve_support_terms(p, _plane(), _slices(p), 1.0)
        assert sup.present and sup.total_passive_t() > 1.0, sup

    def test_the_lost_capacity_is_still_family_B_and_not_A(self):
        nodos = _nodos(CAP_LOST)
        sup = [v for v in nodos if v["adm"]]
        assert sup, "became family A: the fixture stopped exercising D149"
        assert any(not v["adm"] for v in nodos), "nothing is being rejected"

    def test_the_all_out_capacity_really_has_no_survivor(self):
        assert not [v for v in _nodos(CAP_ALL_OUT) if v["adm"]]

    def test_the_two_closed_forms_are_different(self):
        assert abs(_closed_form(CAP_LOST) - _closed_form(CAP_CURED)) > 1e-3

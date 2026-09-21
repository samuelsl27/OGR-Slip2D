# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""v0.1.185 (D156) — THE FLAG COMES FROM THE STATE the method returns, in
BOTH of its exits and not only in one of them.

WHAT INVARIANT THIS PROTECTS. ``Spencer.compute_fos`` and
``GLEMorgensternPrice.compute_fos`` leave by one of two doors. The bracketed
one has derived ``admissible`` from the state it hands back since v0.1.106 and
says why twelve lines above the assignment: *"the flag comes from the state
that was RETURNED, not from which pass produced it. A bisection can land on a
lambda its bracketing samples did not share."* The RESERVE exit did the
opposite. It wrote ``admissible = not inadmissible``, and ``inadmissible`` is a
variable set on ENTERING the relaxed re-sweep of v0.1.106, so it names a PASS.
Two rules for one flag, and the second is the one the engine itself calls
wrong.

WHY THAT IS NOT A TIDINESS COMPLAINT. Between the assignment and the flag,
three more steps append rows to the very list the ``min |g|`` pick draws from
— the lazy extension of v0.1.90, ``refine_lambda_gap`` of v0.1.181 (which
returns its probes even when it finds no sign change, and says so in its own
docstring) and, on the bracketed path only, the edge recovery of v0.1.182 —
and every one of them runs with ``system.strict`` already false. Nothing stops
an ADMISSIBLE row from winning the pick after the flag has been nailed to
false. When that happens the surface is published inadmissible, is dropped
from ``SearchResult.critical``'s pool while any admissible surface exists, is
refused as a direction by ``SimulatedAnnealingSearch._steer``, and carries a
note that denies a compression the returned state has.

THE DENOMINATOR IS 0 of 3 and not 0 of 48, and correcting it is half the
finding. The ficha reports zero discrepancies over the 48 bank rows that leave
by the reserve exit. 45 of those never fire the v0.1.106 block at all — they
have surviving nodes, so ``inadmissible`` is false and the two rules agree
trivially — and the 3 that do fire (047, 060 and 090, all Spencer, all family
A of D149) have NO surviving node, so no admissible row exists for ``min |g|``
to land on. In those three the discrepancy is impossible by construction and
not by luck, which is a stronger statement than the one the ficha makes and a
much narrower one.

WHERE THE GATE CAME FROM INSTEAD, since the bank cannot supply it.
``lambda_grid`` IS SUBCLASSABLE — it and ``lambda_grid_extension`` are plain
methods of ``LEMMethod`` — so the scaffolding of the search can be placed by
hand over a model and a surface that are not synthetic at all: the 45 degree
plane with a passive 120 kN/m anchor of ``test_lambda_edge_v1182``, family B1
of D149, the one case measured with the admissibility boundary BELOW the root
(lam_E = 0.108, lam_g = 0.190). Put the grid at -0.05, 0.00, 0.05 — all
inadmissible, all one sign of ``g``, so the sweep fires and nothing brackets —
and the extension at 0.15, inside the window, and the engine of 0.1.184
publishes ``admissible`` FALSE over a state whose interior thrust sums to
+0.78 kN/m.

WHY THE GATE IS GLE'S AND NOT SPENCER'S, measured rather than assumed. Swept
over the same anchored family for Spencer — 3 slope angles, 2 force
applications, 4 orientations, 8 capacities, 192 cells — lam_E never crosses at
all. ``TestWhyTheWitnessIsNotSpencers`` shows the one-line reason on the same
wedge the witness uses: with the constant shape function of Spencer the
interior thrust sum runs from -2.29 to -1.39 across the whole grid without
reaching zero, while the half sine of GLE takes it from -4.52 to +13.13. The
shape function is what puts the faces into compression here, so the witness
belongs to the method that has one.

THE OTHER WRITER OF THE FLAG, and it is why this file calls ``compute_fos``
directly. ``search.py:583-584`` sets ``result.admissible = False`` on top of
whatever the method decided, for tension at the base or a collapsed m-alpha,
and never sets it back to true. Anything reached through
``build_search(...).evaluate_surface(...)`` therefore reports a COMPOSITE of
two criteria under one name — which is how the bank census came to publish a
single unexplained discrepancy on a row that leaves by the bracketed exit. The
invariant below is about the method, so it is asked of the method.

WHICH CASES MEASURE THE CHANGE AND WHICH ARE CONTROL, measured rather than
guessed and named rather than counted. Run against the tree of 0.1.184 with
only this file added, 11 of the 23 FAIL and 12 PASS.

Six fail on a measured difference in what the engine PUBLISHES, and they are
the file's case for itself: ``test_the_key_exists_on_the_reserve_exit``,
``test_and_so_does_the_margin`` and ``test_the_sign_of_the_margin_is_the_
verdict`` ("only 0 of 4 rows published a margin") on the two keys that exit
never wrote; ``test_the_flag_and_the_detail_agree_in_both_exits`` and
``test_and_on_the_witness_too``, which is the invariant that was inexpressible
on the very exit that got it wrong; and ``test_on_it_publishes_the_flag_of_the_
state``, where the old tree answers ``admissible`` FALSE on the witness.

Five fail for the ABSENCE OF A SYMBOL, which is
WEAK discrimination and is labelled here rather than counted as strength:
``test_the_switch_is_on_by_default`` raises ``AttributeError``;
``test_off_it_publishes_the_flag_of_the_pass`` and
``test_and_it_moves_the_flag_and_not_the_factor`` fail because without the
switch the context manager is a no-op and the case compares a value with
itself; and the two ``thrust_margin`` unit cases raise
``ImportError``.

Of the 12 that pass, four are MADE to pass and would be a worry if they did
not: the whole of ``TestTheSyntheticWitnessSeparatesTheTwoRules`` states what
the DEFECT is, reading the state through ``thrust_is_admissible`` instead of
through ``details``, so a difference there would mean the defect had stopped
existing rather than that the repair worked. The rest are the two CONTROL
classes — ``TestTheFixtureIsTheWitness``, which guards the scaffolding, and
``TestWhyTheWitnessIsNotSpencers``, which is a statement about the shape
function this version does not touch — plus the three cases of
``TestWhatItDoesNotTouch`` that were green before and have to stay green.

WHAT THIS FILE DOES NOT CLAIM. Not that any surface in the verification bank
moves: none does, and the census says so with its own denominator. Not that
``thrust_is_admissible`` is the right criterion, nor that the tension it
rejects is physically real — that is the question v0.1.106 declined to answer
and this version declines too. Not anything about the wording of the note on
the bracketed exit, which has conflated the same two facts since v0.1.106 and
is out of this ficha's scope. And not that the reserve exit is a good answer:
it is a ``min |g|`` pick with no root, reported WITH its residual, and all
this version changes is which of two true things the flag beside it describes.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib
import math

H, TOE, CREST = 12.0, 30.0, 38.0
COH, PHI, GAMMA = 5.0, 30.0, 18.0
NSLICES, TIGHT, MAX_IT, BETA = 50, 1e-10, 400, 45.0

#: Family B1 of D149: lam_E = 0.108 sits BELOW lam_g = 0.190, so there is a
#: window of lambda that is admissible and has not yet reached the root. That
#: window is the whole of the witness, and no other capacity of this family
#: has one — at 130, 134 and 137 the order is the other way round.
CAP_B1 = 120.0

#: The scaffolding, placed by hand. Every grid node is below lam_E, so the
#: strict pass returns nothing and the v0.1.106 sweep fires; all three share
#: one sign of ``g``, so nothing brackets; and the single extension node sits
#: inside (lam_E, lam_g), so it is admissible AND closer to the root than any
#: of them, which is what makes it win ``min |g|``.
REJILLA_TESTIGO = [-0.05, 0.0, 0.05]
EXTENSION_TESTIGO = [0.15]

_CACHE: dict = {}


# ----------------------------------------------------------------------
def _daylight_x(beta_deg=BETA):
    return TOE + H / math.tan(math.radians(beta_deg))


def _anchored(cap=CAP_B1):
    """The plane with a PASSIVE end anchor, as ``test_lambda_edge_v1182``.

    Same model, same surface, same slicing: this file varies the sampling
    grid and nothing else, so that a difference it measures cannot be a
    difference of fixture.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.support import (EndAnchored, ForceApplication,
                                  ForceOrientation, SupportInstance)

    p = Project("thrust-flag")
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=GAMMA,
                            strength=MohrCoulomb(cohesion=COH,
                                                 friction_angle=PHI))]
    p.support_types = [EndAnchored(anchor_capacity=cap,
                                   out_of_plane_spacing=1.0)]
    p.supports = [SupportInstance(
        type_id="end_anchored",
        head=Vertex(34.0, 6.0), tail=Vertex(48.0, 11.0),
        force_application=ForceApplication.PASSIVE,
        orientation=ForceOrientation.USER_DEFINED, user_angle_deg=15.0)]
    return p


def _plane():
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(vertices=[
        Vertex(TOE, 0.0), Vertex(_daylight_x(), H)]))


def _slices(project):
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, _plane(), num_slices=NSLICES)
    assert sl is not None and sl.slices, "the plane produced no slices"
    return sl


def _witness_class():
    """GLE with the sampling grid placed by hand, and NOTHING else changed.

    Subclassing is the honest way to reach this state: ``lambda_grid`` and
    ``lambda_grid_extension`` are the SCAFFOLDING of the search, not the
    physics, so replacing them asks the engine the same question about the
    same slope with the samples moved. Every other line of ``compute_fos``
    is the shipped one.
    """
    from ogr_slip2d.methods.gle import GLEMorgensternPrice

    class _Witness(GLEMorgensternPrice):
        def lambda_grid(self):
            return list(REJILLA_TESTIGO)

        def lambda_grid_extension(self):
            return list(EXTENSION_TESTIGO)

    return _Witness


def _solve(clase, project=None):
    """Run ``compute_fos`` and hand back ``(result, system)``.

    The system is captured by patching the class's own ``_inner_solve``
    rather than by building one that looks like it — the lesson
    ``_tools/curva_cuna_d119.py`` carries in its header, and the reason the
    bank tools do the same: an almost-identical system measures an
    almost-identical thing.
    """
    project = project if project is not None else _anchored()
    cap, orig = [], clase._inner_solve

    def espia(self, sl, lam, system, _o=orig):
        if not cap:
            cap.append(system)
        return _o(self, sl, lam, system)

    clase._inner_solve = espia
    try:
        res = clase(tolerance=TIGHT, max_iterations=MAX_IT).compute_fos(
            project, _plane(), _slices(project))
    finally:
        clase._inner_solve = orig
    return res, (cap[0] if cap else None)


def _witness():
    if "w" not in _CACHE:
        _CACHE["w"] = _solve(_witness_class())
    return _CACHE["w"]


def _state_rule(system, res):
    """``thrust_is_admissible`` asked at the λ the result publishes.

    This is the other rule, computed here and never read out of ``details``,
    so that the cases which describe the DEFECT hold on a tree that has no
    such key.
    """
    from ogr_slip2d.interslice import thrust_is_admissible
    lam = (res.details or {}).get("lambda")
    if system is None or lam is None:
        return None
    force, _moment = system.states(float(lam))
    return None if force is None else thrust_is_admissible(force)


@contextlib.contextmanager
def _flag_from_pass():
    """The reserve flag of 0.1.184: derived from which PASS produced it.

    Read at call time inside ``spencer.py`` and ``gle.py`` as
    ``interslice.THRUST_FLAG_FROM_STATE``, which is why patching the module
    attribute is enough. Restored with ``try/finally`` because the runner
    does not call ``teardown_method`` (rule 5), and ``getattr(..., None)``
    so that on a tree without the switch the CONTROL cases still mean what
    they say while the discriminating one fails on the missing symbol.
    """
    import ogr_slip2d.interslice as interslice
    keep = getattr(interslice, "THRUST_FLAG_FROM_STATE", None)
    if keep is None:
        yield False
        return
    interslice.THRUST_FLAG_FROM_STATE = False
    try:
        yield True
    finally:
        interslice.THRUST_FLAG_FROM_STATE = keep


# ----------------------------------------------------------------------
def _reinforced(layers=4, capacity=1000.0):
    """The reinforced circle of ``test_relaxed_thrust_v1130`` at the capacity
    that falls OFF the bracket.

    Borrowed rather than re-derived: at 200 kN/m that fixture leaves by the
    bracketed exit and at 1000 by the reserve one, which is exactly the pair
    this file needs to ask the same question of both doors, and it reaches
    the reserve exit under SPENCER, where the wedge above cannot.

    Its crest is at x = 50 and NOT at the 38 of the wedge above: same relief,
    a flatter face. Copying the wedge's crest by accident moved the fixture
    off the bracketed exit altogether and both doors came back as one, which
    is what ``test_the_flag_and_the_detail_agree_in_both_exits`` refuses to
    let pass in silence.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SupportInstance, UserDefined)

    CRESTA = 50.0
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CRESTA, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("thrust-flag-circle")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
                            strength=MohrCoulomb(cohesion=8.0,
                                                 friction_angle=20.0))]
    p.support_types = [UserDefined(out_of_plane_spacing=1.0,
                                   points=[(0.0, capacity)])]
    p.supports = [SupportInstance(
        type_id="user_defined",
        head=Vertex(38.0 + 0.6 * k, 2.0 + 3.0 * k),
        tail=Vertex(54.0, 2.0 + 3.0 * k),
        force_application=ForceApplication.PASSIVE,
        orientation=ForceOrientation.TANGENT_TO_SLIP) for k in range(layers)]
    return p


def _solve_circle(method_id, capacity):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    clave = ("c", method_id, capacity)
    if clave in _CACHE:
        return _CACHE[clave]
    project = _reinforced(capacity=capacity)
    surface = SlipCircle(centre_x=38.0, centre_y=26.0, radius=20.0)
    sl = slice_surface(project, surface, num_slices=25)
    clase = method_registry()[method_id]
    cap, orig = [], clase._inner_solve

    def espia(self, s, lam, system, _o=orig):
        if not cap:
            cap.append(system)
        return _o(self, s, lam, system)

    clase._inner_solve = espia
    try:
        res = clase().compute_fos(project, surface, sl)
    finally:
        clase._inner_solve = orig
    _CACHE[clave] = (res, cap[0] if cap else None)
    return _CACHE[clave]


_BOTH = ("spencer", "gle_morgenstern_price")
#: 200 brackets, 1000 falls back — the two doors of the same method.
_CAPS = (200.0, 1000.0)


# ======================================================================
class TestTheFixtureIsTheWitness:
    """Guard the scaffolding before anything is asserted on top of it.

    Each of the three facts below is load bearing: lose any one and the
    cases that follow would be exercising some other branch and passing
    vacuously, which is the failure mode this class makes loud.
    """

    def test_it_leaves_by_the_reserve_exit(self):
        res, _sys = _witness()
        assert res.details.get("lambda_search_fell_back") is True, (
            "the witness has to reach the RESERVE exit; with a bracket it "
            "would be measuring the door that was already right")

    def test_the_relaxed_sweep_fired(self):
        res, _sys = _witness()
        assert res.details.get("lambdas_lost_to_thrust_tension", 0) > 0, (
            "no λ was set aside by the thrust criterion, so the v0.1.106 "
            "sweep never ran and ``inadmissible`` was false all along")

    def test_the_lambda_it_returns_is_the_extension_node(self):
        res, _sys = _witness()
        assert abs(res.details["lambda"] - EXTENSION_TESTIGO[0]) < 1e-12, (
            "``min |g|`` no longer lands on the extension node, so the row "
            "that wins the pick is no longer one taken after the flag")


class TestWhyTheWitnessIsNotSpencers:
    """The shape function is what puts the faces into compression here.

    Control, green on both trees. It exists so that "no Spencer witness" is
    a measured statement with its reason attached rather than a gap.
    """

    def _sum_e(self, method_id, lam):
        from ogr_slip2d.interslice import GLESystem, branch_budget
        from ogr_slip2d.methods.gle import GLEMorgensternPrice
        from ogr_slip2d.moment_balance import axis_for
        from ogr_slip2d.support_integration import resolve_support_terms
        project, surface = _anchored(), _plane()
        sl = _slices(project)
        s_list = sl.slices
        raw = sum(s.weight * math.sin(s.base_angle) for s in s_list)
        sign = 1.0 if raw >= 0 else -1.0
        sup = resolve_support_terms(project, surface, sl, sign)
        if method_id == "spencer":
            shape = [1.0] * (len(s_list) + 1)
        else:
            m = GLEMorgensternPrice(tolerance=TIGHT, max_iterations=MAX_IT)
            shape = [m.f_func(x, s_list[0].base_x_left,
                              s_list[-1].base_x_right)
                     for x in m._boundary_x(sl)]
        system = GLESystem(s_list, shape, 0.0, 0.0, sign, None, None, sup,
                           axis_for(project, surface), tolerance=TIGHT,
                           initial_fos=1.0, max_passes=branch_budget(MAX_IT))
        force, _moment = system.states(lam)
        assert force is not None, "the branch did not solve at λ = %s" % lam
        return math.fsum(force.boundary_e[1:-1])

    def test_the_constant_shape_never_reaches_compression(self):
        for lam in (-0.1, 0.0, 0.8, 1.5):
            assert self._sum_e("spencer", lam) < 0.0, (
                "Spencer reaches net compression at λ = %s on this wedge, "
                "so the 192-cell sweep that found none would be wrong" % lam)

    def test_the_half_sine_crosses_inside_the_grid(self):
        bajo = self._sum_e("gle_morgenstern_price", 0.0)
        alto = self._sum_e("gle_morgenstern_price", 0.2)
        assert bajo < 0.0 < alto, (
            "the GLE thrust no longer changes sign between λ = 0 and 0.2, "
            "so the admissible window the witness lives in is gone")


class TestTheSyntheticWitnessSeparatesTheTwoRules:
    """What the DEFECT is. Green on both trees, and that is the point.

    Every assertion here reads the state through ``thrust_is_admissible``
    and never through ``details``, so it says the same thing on a tree that
    has no such key. A difference here would mean the defect had stopped
    existing, not that the repair worked.
    """

    def test_the_state_it_returns_is_admissible(self):
        res, system = _witness()
        assert _state_rule(system, res) is True, (
            "the λ handed back is in net tension, so the two rules agree "
            "and there is nothing for this file to separate")

    def test_and_the_pass_that_produced_it_was_the_relaxed_one(self):
        res, _sys = _witness()
        assert res.details.get("lambdas_lost_to_thrust_tension", 0) > 0

    def test_so_the_two_rules_give_opposite_answers(self):
        res, system = _witness()
        with _flag_from_pass():
            porla_pasada, _s = _solve(_witness_class())
        assert porla_pasada.admissible is False
        assert _state_rule(system, res) is True, (
            "by the pass: inadmissible. By the state: admissible. If these "
            "ever agree the witness has stopped being one")

    def test_and_the_old_note_denied_a_compression_that_is_there(self):
        with _flag_from_pass():
            porla_pasada, _s = _solve(_witness_class())
        assert "net compression" in (porla_pasada.admissibility_note or ""), (
            "the sentence under test is the one that claims no λ leaves the "
            "thrust in compression")


class TestTheReserveExitPublishesTheDetail:
    """The two keys that exit never wrote.

    Until this version ``thrust_admissible`` existed only on the bracketed
    exit, so ``res.admissible == res.details["thrust_admissible"]`` — the
    one invariant that ties the flag to the state — was inexpressible on
    the exit that got it wrong.
    """

    def test_the_key_exists_on_the_reserve_exit(self):
        res, _sys = _witness()
        assert "thrust_admissible" in (res.details or {}), (
            "the reserve exit still does not say what it thinks of the "
            "thrust, so nothing can check it")

    def test_and_so_does_the_margin(self):
        res, _sys = _witness()
        assert "thrust_margin" in (res.details or {})

    def test_the_margin_is_the_state_it_returns(self):
        """v0.1.186 (D159) — what this case stopped covering, said out loud.

        Until the per-λ cache, the ``states`` call below re-solved the two
        branches, so this comparison was also, without meaning to be, a test
        that ``states`` is deterministic. It is a cache hit now and the two
        sides are the SAME object, so that half has become trivial. The claim
        it still makes — that the published margin is the margin of the state
        the method returns, and not of some other λ — is untouched. The
        determinism is covered on purpose in
        ``tests/test_lambda_state_cache_v1186.py::test_two_calls_from_scratch_agree_bit_for_bit``.
        A case that goes quietly tautological is worse than one that goes red.
        """
        from ogr_slip2d.interslice import thrust_margin
        res, system = _witness()
        force, _moment = system.states(float(res.details["lambda"]))
        assert res.details["thrust_margin"] == thrust_margin(force), (
            "the margin published is not the margin of the state returned")

    def test_the_sign_of_the_margin_is_the_verdict(self):
        """An identity, not a snapshot: both are the sign of the same sum.

        The counter is not decoration. Skipping the rows with no margin and
        asserting nothing would make this case GREEN on a tree that writes
        neither key — a case that measures zero things and reports success,
        which is the shape of failure this project has walked into before.
        """
        comprobadas = 0
        for mid in _BOTH:
            for cap in _CAPS:
                res, _sys = _solve_circle(mid, cap)
                d = res.details or {}
                m = d.get("thrust_margin")
                if m is None:
                    continue
                comprobadas += 1
                assert (m > 0.0) is bool(d["thrust_admissible"]), (
                    "%s at %s: margin %r against verdict %r"
                    % (mid, cap, m, d["thrust_admissible"]))
        assert comprobadas == len(_BOTH) * len(_CAPS), (
            "only %d of %d rows published a margin, so this identity was "
            "checked on less than it claims"
            % (comprobadas, len(_BOTH) * len(_CAPS)))


class TestTheTwoExitsAgreeOnTheSameSurface:
    """The coincidence, FIXED instead of left to the path taken.

    Asked of ``compute_fos`` and not through a search, because
    ``search.py:583-584`` writes the same field for a different reason and
    would make this a statement about two criteria at once.
    """

    def test_the_flag_and_the_detail_agree_in_both_exits(self):
        vistos = set()
        for mid in _BOTH:
            for cap in _CAPS:
                res, _sys = _solve_circle(mid, cap)
                d = res.details or {}
                vistos.add(bool(d.get("lambda_search_fell_back")))
                assert res.admissible == d["thrust_admissible"], (
                    "%s at %s publishes admissible=%r with "
                    "thrust_admissible=%r"
                    % (mid, cap, res.admissible, d["thrust_admissible"]))
        assert vistos == {True, False}, (
            "the fixtures no longer cover both exits (%r), so the agreement "
            "is only checked on one door" % (vistos,))

    def test_and_on_the_witness_too(self):
        res, _sys = _witness()
        assert res.admissible == res.details["thrust_admissible"]


class TestTheSwitchMovesANumber:
    """The attribution table, executed rather than written down.

    Fails against 0.1.184 for the ABSENCE OF A SYMBOL, which is weak
    discrimination: without the switch the context manager is a no-op and
    the two halves compare a value with itself.
    """

    def test_the_switch_is_on_by_default(self):
        import ogr_slip2d.interslice as interslice
        assert interslice.THRUST_FLAG_FROM_STATE is True

    def test_off_it_publishes_the_flag_of_the_pass(self):
        with _flag_from_pass() as hay:
            res, _sys = _solve(_witness_class())
        assert hay, "no switch to turn off: this case measures nothing here"
        assert res.admissible is False
        assert res.details["thrust_admissible"] is True, (
            "off, the flag and the detail must DISAGREE — that is the "
            "defect the switch exists to turn on and off")

    def test_on_it_publishes_the_flag_of_the_state(self):
        res, _sys = _witness()
        assert res.admissible is True
        assert res.details["thrust_admissible"] is True

    def test_and_it_moves_the_flag_and_not_the_factor(self):
        con, _s1 = _witness()
        with _flag_from_pass():
            sin, _s2 = _solve(_witness_class())
        assert con.fos == sin.fos, (
            "the factor moved: %r against %r. This switch decides what the "
            "answer is CALLED, never what it is" % (con.fos, sin.fos))
        assert con.admissible != sin.admissible


class TestWhatItDoesNotTouch:
    """Green before and green after, and each one for a stated reason."""

    def test_the_criterion_itself_is_unchanged(self):
        from ogr_slip2d.interslice import BranchState, thrust_is_admissible
        def _estado(es):
            return BranchState(fos=1.0, converged=True, passes=1,
                               normals=[], resisting=[],
                               boundary_e=[0.0] + list(es) + [0.0],
                               boundary_x=[0.0] * (len(es) + 2))
        assert thrust_is_admissible(_estado([1.0, 2.0, 3.0])) is True
        assert thrust_is_admissible(_estado([-1.0, -2.0])) is False
        assert thrust_is_admissible(_estado([5.0, -1.0])) is True
        assert thrust_is_admissible(_estado([])) is True

    def test_the_margin_says_nothing_where_there_is_nothing_to_say(self):
        from ogr_slip2d.interslice import BranchState, thrust_margin
        assert thrust_margin(None) is None
        vacio = BranchState(fos=1.0, converged=True, passes=1, normals=[],
                            resisting=[], boundary_e=[0.0, 0.0],
                            boundary_x=[0.0, 0.0])
        assert thrust_margin(vacio) is None, (
            "with no interior face the question has no answer, and 0.0 "
            "would read as 'exactly on the boundary'")

    def test_the_grid_the_engine_ships_is_untouched_by_the_switch(self):
        from ogr_slip2d.methods.gle import GLEMorgensternPrice
        con, _s1 = _solve(GLEMorgensternPrice)
        with _flag_from_pass():
            sin, _s2 = _solve(GLEMorgensternPrice)
        assert con.fos == sin.fos
        assert con.admissible == sin.admissible
        assert con.admissibility_note == sin.admissibility_note, (
            "the same surface under the shipped grid must be described the "
            "same way on both sides: it brackets, so this ficha cannot "
            "reach it")

    def test_the_bracketed_exit_still_derives_its_own_flag(self):
        for mid in _BOTH:
            res, system = _solve_circle(mid, 200.0)
            assert res.details.get("lambda_search_fell_back") is False
            assert res.admissible == _state_rule(system, res), (
                "%s: the bracketed exit stopped agreeing with its own "
                "state, which is what it has done since v0.1.106" % mid)

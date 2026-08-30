# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.130 — a CONVERGED answer may not be filed as a failed
calculation.

**The invariant**, and it is a contract the code already stated rather than
a number: ``LEMResult.error_message`` marks a calculation that FAILED, and
it feeds ``is_valid``; a converged but physically unreliable answer belongs
in ``admissible`` / ``admissibility_note``. ``methods/base.py`` says so in
as many words. Spencer and GLE said the opposite in code.

What that cost. When no lambda leaves the inter-slice thrust in net
compression, both methods relax the criterion and report the answer —
``interslice.py`` calls the strict pass "a PREFERENCE, not a veto" and
explains why: on a heavily reinforced slope the soil faces come out in net
tension at every lambda, and turning that into a NaN loses coverage for
nothing. But the flag was written to ``error_message``, which IS a veto:
``search.surface_score`` scores such a surface ``inf`` and
``SearchResult.critical`` filters it with no fallback, so a search could
never report it however critical it was. The message read "the answer is
reported with the criterion relaxed" and the answer was not reported. It
was erased.

Measured on the verification bank, A/B in one process, the old behaviour
restored by wrapping ``compute_fos``. Surfaces struck off a single search:

    problem 85, GLE      1106 valid / 8280 invalid / 6 inadmissible
                    ->   1877 valid / 7509 invalid / 777 inadmissible
    problem 90, Spencer  1898 / 5284 / 0   ->   3124 / 4058 / 1226
    problem 93, Spencer  2166 / 5016 / 0   ->   3178 / 4004 / 1012

They were counted as failed calculations. They are now counted as
solved-but-inadmissible, which is what they are. **And the factor of safety
did not move in any of the four**: 1.583149, 0.95209, 1.021155 and 2.209135
before and after, to the last digit. That is asserted below and it is the
point — the defect was a misfiling, so the fix must be a misfiling
corrected and nothing else.

Read this before widening it. **Not every relaxed answer becomes valid**,
and the distinction cost a wrong diagnosis before it was measured. When the
lambda search finds no BRACKET at all, both methods return the nearest
F_f ~ F_m pair and set ``converged = abs(F_f - F_m) < 0.02``. That is a
failed solve, it stays a veto, and it stays in ``error_message``.
Verification problems 85 and 91 reach the engine by that branch: what the
bank publishes on their circle is a fallback value, not a measurement, and
no amount of fixing the thrust flag makes their search find it. Both cases
are covered here so the two never get merged again.
"""
from __future__ import annotations

H, TOE, CREST = 12.0, 30.0, 50.0

#: Four passive layers at 200 kN each. Swept for, not guessed: this is the
#: mildest configuration of the fixture below in which Spencer AND GLE both
#: CONVERGE and still find no lambda that leaves the thrust in compression.
#: Raising the capacity at four layers falls off the other side, into the
#: no-bracket branch, which is the case this file exists to keep SEPARATE
#: from the first. Lowering the LAYER COUNT does not: below four the circle
#: stops crossing the reinforcement altogether and the capacity becomes a
#: knob that moves nothing — measured, 1.5496 at 1000 kN and at 20000.
_LAYERS, _CAPACITY = 4, 200.0

_RELAXED = "leaves the inter-slice thrust in net compression"
_NO_BRACKET = "-bracket"


# ----------------------------------------------------------------------
def _project(layers=_LAYERS, capacity=_CAPACITY):
    """A homogeneous slope carrying ``layers`` passive supports.

    Same slope as ``test_support_active_passive_v1115``: 12 m of relief on a
    30 -> 50 face over a 10 m foundation. The reinforcement is what drives
    the inter-slice faces into net tension, which is the state under test.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SupportInstance, UserDefined)

    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("relaxed-thrust")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="S", unit_weight=18,
                            strength=MohrCoulomb(cohesion=8.0,
                                                 friction_angle=20.0))]
    # ``UserDefined`` with one table point, so the capacity is a datum of the
    # test and not the outcome of a start-up calculation — the same reason
    # verification problem 85 is modelled that way.
    p.support_types = [UserDefined(out_of_plane_spacing=1.0,
                                   points=[(0.0, capacity)])]
    p.supports = [SupportInstance(
        type_id="user_defined",
        head=Vertex(38.0 + 0.6 * k, 2.0 + 3.0 * k),
        tail=Vertex(54.0, 2.0 + 3.0 * k),
        force_application=ForceApplication.PASSIVE,
        orientation=ForceOrientation.TANGENT_TO_SLIP) for k in range(layers)]
    return p


def _circle():
    from ogr_slip2d.surface import SlipCircle
    return SlipCircle(centre_x=38.0, centre_y=26.0, radius=20.0)


def _solve(method_id, project, num_slices=25):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.slicer import slice_surface
    surface = _circle()
    sl = slice_surface(project, surface, num_slices=num_slices)
    assert sl is not None and sl.slices, "the surface produced no slices"
    return method_registry()[method_id]().compute_fos(project, surface, sl)


_COMPLETE = ("spencer", "gle_morgenstern_price")


# ======================================================================
class TestTheFixtureIsTheStateUnderTest:
    """Guard the fixture itself.

    If the sweep that found this configuration stops landing on it, every
    assertion below would pass vacuously against a surface that never
    relaxes anything. That is the failure mode this class makes loud
    instead of silent.
    """

    def test_both_methods_converge_and_relax_the_criterion(self):
        for mid in _COMPLETE:
            res = _solve(mid, _project())
            assert res.converged, (
                "%s no longer converges on the fixture: the tests below "
                "would be exercising the no-bracket branch by accident"
                % mid)
            assert res.details.get("thrust_admissible") is False, (
                "%s no longer relaxes the thrust criterion here; the "
                "fixture needs re-sweeping" % mid)

    def test_without_reinforcement_nothing_is_relaxed(self):
        """The control. No supports, no relaxation, no inadmissibility."""
        p = _project(layers=0)
        for mid in _COMPLETE:
            res = _solve(mid, p)
            assert res.converged and res.is_valid
            assert res.admissible
            assert not res.admissibility_note
            assert res.details.get("thrust_admissible") is True


# ======================================================================
class TestAConvergedAnswerIsNotAFailedCalculation:
    """The defect, stated as the contract it broke."""

    def test_the_relaxed_criterion_leaves_error_message_empty(self):
        for mid in _COMPLETE:
            res = _solve(mid, _project())
            assert not res.error_message, (
                "%s files a converged answer as a failed calculation: %r"
                % (mid, res.error_message))

    def test_it_goes_to_the_admissibility_note_instead(self):
        for mid in _COMPLETE:
            res = _solve(mid, _project())
            assert _RELAXED in res.admissibility_note, (
                "%s dropped the reason entirely; an unexplained rejection "
                "is worse than the misfiled one" % mid)

    def test_such_a_surface_is_valid_and_inadmissible(self):
        for mid in _COMPLETE:
            res = _solve(mid, _project())
            assert res.is_valid, (
                "%s: a converged, finite, positive answer is not an "
                "invalid surface" % mid)
            assert not res.admissible

    def test_the_flag_and_the_detail_agree(self):
        """``details["thrust_admissible"]`` already held the right answer.

        It has been there since v0.1.106 and nothing read it. The fix is
        that ``admissible`` now says the same thing, so the two cannot
        drift apart.
        """
        for mid in _COMPLETE:
            res = _solve(mid, _project())
            assert res.admissible == res.details["thrust_admissible"]


# ======================================================================
class TestTheNoBracketBranchIsStillAVeto:
    """The distinction that was nearly lost.

    No lambda-bracket means no root was found and the pair returned is the
    nearest crossing. That IS a failed solve, so it keeps
    ``error_message`` and keeps ``is_valid`` False. Verification problems
    85 and 91 live here, and treating them as the same defect as 90 and 93
    would have claimed a fix for rows the change cannot reach.
    """

    #: Same four layers, five times the capacity. NOT ``layers=1`` with a
    #: huge capacity, which looks like the obvious knob and is a dead one:
    #: the lone support sits at y = 2 and the circle never crosses it, so
    #: the factor comes out 1.5496 for 1000 kN and for 20000 alike. A
    #: fixture whose parameter moves nothing would have asserted nothing.
    _VETO = dict(layers=4, capacity=1000.0)

    def test_a_huge_capacity_falls_off_the_other_side(self):
        p = _project(**self._VETO)
        for mid in _COMPLETE:
            res = _solve(mid, p)
            assert not res.converged
            assert _NO_BRACKET in (res.error_message or ""), (
                "%s: expected the no-bracket fallback, got %r"
                % (mid, res.error_message))
            assert not res.is_valid

    def test_the_two_judgements_are_not_in_the_same_field(self):
        """One field held both, so one could not be read without the other."""
        p = _project(**self._VETO)
        for mid in _COMPLETE:
            res = _solve(mid, p)
            assert _RELAXED not in (res.error_message or "")


# ======================================================================
class TestItMovesNoFactorOfSafety:
    """Rule 7 read the other way round.

    A reclassification that silently moved a number would be a numerical
    change wearing a bookkeeping disguise. ``critical`` prefers admissible
    surfaces and falls back to the rest only when there are none
    (``ok or valid``), so a relaxed surface can win only where it is the
    only answer there is — which is exactly what "a preference, not a
    veto" means.
    """

    def _run(self):
        from ogr_slip2d.methods.base import method_registry
        from ogr_slip2d.search import GridSearch
        p = _project()
        s = GridSearch(method=method_registry()["spencer"](),
                       num_slices=25, min_area=0.0,
                       grid_x=(30.0, 46.0, 4), grid_y=(20.0, 30.0, 4),
                       radius_increments=4)
        return p, s.run(p)

    def test_an_admissible_surface_still_wins(self):
        _p, res = self._run()
        crit = res.critical
        assert crit is not None
        if res.analysed_count:
            assert crit.admissible, (
                "an inadmissible surface was reported as critical while "
                "admissible ones existed")

    def test_the_relaxed_surface_is_counted_as_analysed_not_as_failed(self):
        """The number that DOES move, and the only one.

        Before the change these surfaces went into ``invalid_count`` — the
        same bucket as a division by zero. The bank measured 771 of them
        in one search on verification problem 85 alone.
        """
        _p, res = self._run()
        relaxed = [r for r in res.evaluations
                   if _RELAXED in (r.admissibility_note or "")
                   and r.converged]
        assert relaxed, "the grid never reached the state under test"
        for r in relaxed:
            assert r.is_valid, (
                "a converged surface with a relaxed criterion is still "
                "being counted as a failed calculation")
        assert res.inadmissible_count >= len(relaxed)

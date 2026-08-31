# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.135 — what a Block Search's POPULATION is, and what the
number of groups can and cannot be asked to do. Defect D21b, point (1).

**The invariant, and it is an identity rather than an inequality**: the
population a Block Search generates is exactly ``num_surfaces``, whatever
``num_groups`` says. The loop is ``for ip in range(self.num_surfaces)``;
``num_groups`` changes how many FREE VERTICES each candidate has, not how
many candidates there are.

That identity is the instrument a claim about this search needs, and
nothing asserted it until now. The defect record for D21b carried the
premise "more groups is more surfaces", and the closure criterion built on
it read "AT EQUAL GENERATED SURFACES, the minimum does not get worse as
``num_groups`` rises". Both are answered here, and the second one cannot
be asserted:

* the population is ALREADY equal — measured on the four-layer dyke of
  verification problem 75 with its block object removed, 5000 generated at
  1, 2, 3 and 4 groups, ``total_count`` 5000 in all four — so the
  condition the criterion attaches is not one that can be added;
* and under it the minimum still moves BOTH WAYS: 1.633327, 0.619769,
  0.640339, 0.535380 for 1..4 groups. It falls overall and rises from two
  groups to three.

**Why no containment argument exists**, which is the part that makes the
monotonicity untestable rather than merely unproven. With k groups the
region is cut into k equal vertical strips and ONE point is drawn per
strip, so a candidate has exactly k block vertices and the strips are
RE-PARTITIONED when k changes — a k-1 surface is not a degenerate member
of the k family, it is not in it at all. This project asserts monotonicity
only where containment is demonstrable, and here it is demonstrably
absent. See ``test_the_group_families_are_disjoint``.

**What CAN be asserted, and nobody had**: the same claim along the axis
where containment is real. With one seed, the first N candidates of a run
of 2N are bit-identical to the N of a run of N — the loop depends on
``num_surfaces`` only in its bound and nothing else consumes the
generator — so more candidates can never give a worse answer. That is
``test_more_candidates_never_give_a_worse_answer``, and it is the honest
form of the claim D21b was reaching for.

The second half of the file protects the note added in the same version:
a factor of safety that leans on a near-zero ``m_alpha``. In a purely
cohesive material the friction term vanishes and ``m_alpha`` degenerates
to ``cos alpha`` EXACTLY, which turns the m-alpha check into a bare
ceiling on the base angle — 78.46 deg at the reference's limit of 0.2.
A search minimises the factor, and the factor is minimised by driving
``m_alpha`` towards that limit, so the surface a search reports is
systematically the one where its method is least valid. On the dyke above
at four groups the check rejected 82.6 % of the worst band and the winner
came out of what got through: m_alpha 0.2115 against the 0.20 limit, on a
base at 77.79 deg, and Bishop returned 0.5354 where the manual publishes
1.105 and Spencer returns 0.9645.

COST. Six Block Search runs of at most 640 candidates, shared through a
module cache, plus a few single-surface evaluations. Around six seconds.
"""
from __future__ import annotations
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_search_inequality_v1118 import _layered_slope  # noqa: E402

_SEED = 5
_CACHE: dict = {}


def _block(groups: int, num_surfaces: int):
    """One Block Search run, shared: the largest costs five seconds."""
    key = (groups, num_surfaces)
    if key not in _CACHE:
        from ogr_slip2d.methods.bishop import BishopSimplified
        from ogr_slip2d.search import BlockSearch

        p = _layered_slope()
        s = BlockSearch(method=BishopSimplified(), num_slices=15,
                        num_groups=groups, num_surfaces=num_surfaces,
                        seed=_SEED)
        _CACHE[key] = s.run(p)
    return _CACHE[key]


# ======================================================================
class TestThePopulationIsTheOneAskedFor:
    """The identity D21b's closure criterion needed and never had."""

    def test_every_group_count_generates_the_same_number(self):
        """``num_groups`` changes the shape of a candidate, not how many.

        This is the premise "more groups is more surfaces" made falsifiable
        for good. It was false: on the dyke of problem 75 the VALID counts
        go 3551, 4660, 3928, 3016 while the generated count never moves off
        5000. More groups redistributes the sampling; it does not enlarge
        it.
        """
        for groups in (1, 2, 3, 4):
            r = _block(groups, 160)
            assert r.total_count == 160, (groups, r.total_count)

    def test_the_yield_moves_even_though_the_population_does_not(self):
        """Rule 7's other half: the counts that SHOULD differ, do.

        Without this the test above would pass on a search that had
        stopped generating anything distinguishable at all.
        """
        yields = {g: _block(g, 160).valid_count for g in (1, 2, 3, 4)}
        assert len(set(yields.values())) > 1, yields


# ======================================================================
class TestTheGroupsAreNotNested:
    def test_the_group_families_are_disjoint(self):
        """Why monotonicity in ``num_groups`` has nothing to rest on.

        Checked over the POPULATION and not only over the critical
        surface: k groups puts exactly k block vertices between the two
        projected ends, so a candidate of a k-group run carries k+2
        vertices before near-coincident abscissae are merged. A k-1
        surface is therefore not a degenerate member of the k family.
        """
        for groups in (2, 3, 4):
            r = _block(groups, 160)
            counts = {len(e.surface.polyline.vertices)
                      for e in r.evaluations}
            assert counts, groups
            assert max(counts) == groups + 2, (groups, sorted(counts))
            assert min(counts) >= 3, (groups, sorted(counts))

    def test_the_group_count_moves_the_number(self):
        """Rule 7, and NOT "more groups finds a lower minimum".

        The direction is model-dependent and was measured in both: on the
        four-layer benchmark of ``test_search_inequality_v1118`` the
        minimum RISES with the count, and on the dyke of problem 75 it
        FALLS overall while rising from two groups to three. What is
        common to both, and all that can be claimed without a containment
        argument, is that the control does something.
        """
        mins = [round(_block(g, 160).min_fos, 9) for g in (2, 3, 4)]
        assert len(set(mins)) == len(mins), mins


# ======================================================================
class TestMoreCandidatesNeverGiveAWorseAnswer:
    """The monotonicity that CAN be asserted, along the axis where the
    containment is real."""

    def test_the_shorter_run_is_a_prefix_of_the_longer_one(self):
        """The claim the inequality below rests on, checked at full
        precision rather than assumed: the loop reads ``num_surfaces``
        only as its bound, so one seed makes the first N candidates of a
        2N run the same candidates, bit for bit."""
        short = _block(3, 160)
        long_ = _block(3, 640)

        def fingerprint(res):
            return [(repr(e.fos), e.converged, e.is_valid,
                     tuple((repr(v.x), repr(v.y))
                           for v in e.surface.polyline.vertices))
                    for e in res.evaluations]

        fs, fl = fingerprint(short), fingerprint(long_)
        assert len(fs) > 50, len(fs)
        assert len(set(fs)) > 1, "the fingerprint does not discriminate"
        assert fl[:len(fs)] == fs

    def test_more_candidates_never_give_a_worse_answer(self):
        """And therefore the minimum cannot rise with the budget.

        Two assertions, different on purpose: the first is the invariant,
        the second stops the test passing by inertia if the budget ever
        stopped being spent. Measured here: 1.372270 at 160 candidates
        against 1.328368 at 640.
        """
        short = _block(3, 160)
        long_ = _block(3, 640)
        assert long_.min_fos <= short.min_fos + 1e-12, (short.min_fos,
                                                        long_.min_fos)
        assert long_.min_fos < short.min_fos, (short.min_fos, long_.min_fos)


# ======================================================================
def _cohesive_slope(phi: float = 0.0):
    """A slope whose clay is purely cohesive, so ``m_alpha`` is ``cos a``.

    ``phi = 0`` is not a convenience here, it is the whole mechanism: the
    friction term of ``m_alpha`` disappears and the admissibility check
    stops being a statement about the method and becomes a bare ceiling on
    the base angle.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, -20), Vertex(120, -20), Vertex(120, 10),
        Vertex(70, 10), Vertex(40, 30), Vertex(0, 30),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("cohesive")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="Clay", unit_weight=18.0,
                            strength=MohrCoulomb(cohesion=30.0,
                                                 friction_angle=phi))]
    p.settings.methods.num_slices = 30
    return p


def _evaluate(project, points):
    """One polyline surface through the engine's ordinary door."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.search import BlockSearch
    from ogr_slip2d.surface import SlipSurface

    s = BlockSearch(method=BishopSimplified(), num_slices=30)
    poly = Polyline(vertices=[Vertex(x, y) for x, y in points], closed=False)
    return s.evaluate_surface(project, SlipSurface(polyline=poly))


#: A back scarp at 74.5 deg (dx 10, dy -36), so ``cos alpha`` is 0.267 —
#: past the 0.5 the note fires at and still clear of the 0.2 the m-alpha
#: check rejects at, which is the band the defect lives in: accepted, and
#: dividing the normal force by a quarter.
_STEEP = [(20, 30), (30, -6), (45, -8), (78, 10)]
#: The same slope with nothing steeper than 39 deg, ``cos alpha`` 0.78.
_GENTLE = [(10, 30), (45, 2), (85, 10)]


class TestItSaysWhenTheAnswerLeansOnANearZeroMAlpha:
    def test_m_alpha_is_the_cosine_when_the_soil_has_no_friction(self):
        """The analytic identity the note is built on, checked rather than
        asserted in a comment: with ``phi = 0``,
        ``m_alpha = cos a + s sin a tan phi / F`` is ``cos a`` exactly.

        This is what makes the m-alpha check degenerate into a ceiling on
        the base angle, and it is why the check leaves no margin at all
        between accepted and rejected in a cohesive soil.
        """
        from ogr_slip2d.checks import base_m_alphas

        res = _evaluate(_cohesive_slope(0.0), _STEEP)
        assert res is not None
        vals = base_m_alphas(res)
        assert vals
        for v, sl in zip(vals, res.slices):
            assert abs(v - math.cos(sl.base_angle)) < 1e-12, (
                v, math.cos(sl.base_angle))

    def test_a_steep_face_in_cohesive_soil_triggers_the_note(self):
        """The reported factor rests on a denominator near zero, and until
        v0.1.135 nothing said so."""
        from ogr_slip2d.analysis_runner import m_alpha_margin_note
        from ogr_slip2d.checks import base_m_alphas

        res = _evaluate(_cohesive_slope(0.0), _STEEP)
        assert res is not None
        worst = min(base_m_alphas(res))
        assert worst < 0.5, worst
        notes = m_alpha_margin_note(res)
        assert notes, worst
        assert "m_alpha" in notes[0]

    def test_a_gentle_surface_says_nothing(self):
        """A reporting note that fires on everything is noise, so the
        silent case is part of the invariant."""
        from ogr_slip2d.analysis_runner import m_alpha_margin_note
        from ogr_slip2d.checks import base_m_alphas

        res = _evaluate(_cohesive_slope(0.0), _GENTLE)
        assert res is not None
        assert min(base_m_alphas(res)) >= 0.5, base_m_alphas(res)
        assert m_alpha_margin_note(res) == []

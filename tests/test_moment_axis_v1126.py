# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.126 — what the moment axis of a NON-CIRCULAR surface costs, measured.

This file measures a convention. It does not ask for it to be changed —
that was tried, and the measurement said no.

The identity, and it is real
----------------------------

A polyline of N chords inscribed in an arc becomes the arc as N grows, so
its factor of safety has to converge to the arc's, for every method. It
does not. On the deep critical circle of verification problem 103 (centre
125.400, 56.700, R 56.40, 200 slices, two undrained layers)::

                Ordinary   Bishop   Spencer
    arc          1.3043    1.3043   1.3043
    24 chords    1.2470    1.2490   1.3051
    48 chords    1.2438    1.2497   1.3031
    192 chords   1.2427    1.2500   1.3032

Ordinary settles at -4.7 % and Bishop at -4.2 %, and neither improves
between 48 and 192 chords: a bias, not discretisation.

The cause is exact and is confirmed here: ``moment_axis`` builds the axis
of a polyline from its chord alone, ``midpoint(chord) + rot90(chord)``,
which for that surface lands 65 m from the centre — further than the
radius — and does not move when the polyline is refined, because it only
ever looks at the two endpoints. Force the axis onto the true centre and
all three methods return to 1.3043 exactly. Only the moment-ONLY methods
can drift at all: Spencer and GLE satisfy force equilibrium too, so their
answer cannot depend on which point moments are taken about.

Why the axis is not changed anyway
----------------------------------

Because the reference publishes the factor of safety of seven methods on
two hand-drawn non-circular surfaces, and the current construction
reproduces them. Both candidates were run against that table
(``test_noncircular_validation_v192.py`` holds the published values):

                        published   this axis    best-fit centre
    Ej_1 Ordinary        0.897423     0.89742      0.89407  (-0.37 %)
    Ej_1 Bishop          0.922931     0.92308      0.91866  (-0.46 %)
    Ej_2 Ordinary        1.36921      1.36921      1.38200  (+0.93 %)
    Ej_2 Bishop          1.42443      1.42318      1.46904  (+3.13 %)

Ordinary lands on the published value to SIX FIGURES on both surfaces
with the axis as it is, and Ordinary is the method with no inter-slice
forces to hide behind. Replacing the axis would trade that for a third of
a per cent on one surface and three per cent on the other, in order to
satisfy an identity that the source of those numbers does not satisfy
either. So the -4.7 % is a property of the CONVENTION, not a defect in
this program, and what this file does is keep it measured.

That matters beyond bookkeeping: it is the size of the anomaly recorded
for verification problem 41, where a Path Search reported a minimum below
every published reference. A moment-only factor of safety on a
non-circular surface carries this much slack, and now the number is
written down instead of being rediscovered.

What turns this file red
------------------------

Any change to the axis rule. The bands below are wide enough not to
quiver and narrow enough that moving the axis moves them, so whoever
moves it has to come back here and re-derive the trade above rather than
adjust a number.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest  # noqa: E402

from ogr_core.geometry import (  # noqa: E402
    Boundary,
    BoundaryType,
    Polyline,
    Vertex,
)
from ogr_core.materials import Material  # noqa: E402
from ogr_core.materials.builtin_models import (  # noqa: E402
    MohrCoulomb,
    Undrained,
)
from ogr_core.project import Project  # noqa: E402
from ogr_slip2d.methods import method_registry  # noqa: E402
from ogr_slip2d.search import GridSearch  # noqa: E402
from ogr_slip2d.surface import SlipCircle, SlipSurface, moment_axis  # noqa: E402


# ----------------------------------------------------------------------
# The model of verification problem 103 — Guo, S. and Griffiths, D.V.
# (2020), "Failure mechanisms in two-layer undrained slopes", Canadian
# Geotechnical Journal 57(10) 1617-1621, which publishes its geometry in
# full: H = 18 m, cot(beta) = 2, depth ratio D = 2, cu1 = 60 kPa, unit
# weight 20 kN/m3. Its deep critical circle is long and strongly curved,
# which is where a displaced axis costs most.
_H = 18.0
_CU1 = 60.0
_GAMMA = 20.0

#: Deep critical circle of the cu2/cu1 = 1.4 case, from a grid search.
_DEEP = (125.4, 56.7, 56.40)

#: Chord counts compared against the arc. 64 chords put the largest
#: chord-to-arc gap at R(1 - cos(theta/2)), about 14 mm on this 56 m
#: radius — two orders of magnitude below the effect being measured.
_CHORDS = (16, 64)

#: Slices. It has to EXCEED the vertex count: a polyline with more
#: vertices than slices is refused by the slicer, and refused silently
#: (the open note under D21b). 64 chords is 65 vertices.
_SLICES = 150

#: Methods that satisfy moment equilibrium and NOT force equilibrium.
#: These are the ones whose answer can depend on the axis at all.
_MOMENT_ONLY = ("ordinary_fellenius", "bishop_simplified")

#: And the two that satisfy both, which therefore cannot.
_BOTH_EQUILIBRIA = ("spencer", "gle_morgenstern_price")


def _two_layer_slope(cu2: float = 84.0, num_slices: int = _SLICES) -> Project:
    """Embankment of height H over a foundation of thickness (D-1)H."""
    left = 6.0 * _H
    x_toe = left + 2.0 * _H          # cot(beta) = 2
    right = x_toe + 5.0 * _H
    p = Project("moment-axis")
    ext = Polyline(vertices=[
        Vertex(0.0, 0.0), Vertex(right, 0.0), Vertex(right, _H),
        Vertex(x_toe, _H), Vertex(left, 2.0 * _H), Vertex(0.0, 2.0 * _H),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(0.0, _H), Vertex(right, _H)], closed=False),
        btype=BoundaryType.MATERIAL))
    emb = Material(name="embankment", unit_weight=_GAMMA,
                   strength=Undrained(cohesion=_CU1))
    fnd = Material(name="foundation", unit_weight=_GAMMA,
                   strength=Undrained(cohesion=cu2))
    p.materials = [emb, fnd]
    p.resolve_regions()
    p.assign_material_at(left + 1.0, 1.5 * _H, emb.id)
    p.assign_material_at(left + 1.0, 0.5 * _H, fnd.id)
    p.settings.methods.num_slices = num_slices
    return p


def _drained_slope(num_slices: int = _SLICES) -> Project:
    """A homogeneous c-phi slope, so nothing here rests on phi = 0."""
    p = Project("moment-axis-drained")
    ext = Polyline(vertices=[
        Vertex(0.0, 0.0), Vertex(120.0, 0.0), Vertex(120.0, 20.0),
        Vertex(80.0, 20.0), Vertex(50.0, 40.0), Vertex(0.0, 40.0),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="soil", unit_weight=19.0,
                            strength=MohrCoulomb(cohesion=15.0,
                                                 friction_angle=25.0))]
    p.resolve_regions()
    p.assign_material_at(60.0, 10.0, p.materials[0].id)
    p.settings.methods.num_slices = num_slices
    return p


def _search(method, num_slices: int) -> GridSearch:
    """A search object used only as an evaluator — the grid never runs."""
    return GridSearch(method=method, num_slices=num_slices,
                      grid_nx=3, grid_ny=3, radius_increment=3)


def _resolved_circle(project, method, circle_def, num_slices):
    """The circle with its ground crossings resolved, plus its result."""
    cx, cy, r = circle_def
    circle = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
    res = _search(method, num_slices).evaluate_circle(project, circle)
    return circle, res


def _inscribed(circle_def, x_left, x_right, n_chords):
    """``n_chords`` straight segments inscribed in the arc.

    Every vertex lies ON the circle, so the polyline converges to the arc
    uniformly: the largest gap between chord and arc is
    R(1 - cos(theta/2)) with theta the subtended angle, i.e. O(1/n^2).
    """
    cx, cy, r = circle_def
    pts = []
    for i in range(n_chords + 1):
        x = x_left + (x_right - x_left) * i / n_chords
        d = max(0.0, r * r - (x - cx) ** 2)
        pts.append(Vertex(x, cy - math.sqrt(d)))
    return SlipSurface(polyline=Polyline(vertices=pts, closed=False))


def _drift(project, method_id, circle_def, n_chords, num_slices=_SLICES):
    """Relative difference between the inscribed polyline and its arc."""
    method = method_registry()[method_id]()
    circle, arc = _resolved_circle(project, method, circle_def, num_slices)
    assert arc is not None and arc.is_valid, "the arc itself did not solve"
    surf = _inscribed(circle_def, circle.x_left, circle.x_right, n_chords)
    res = _search(method, num_slices).evaluate_surface(project, surf)
    assert res is not None and res.is_valid, (
        "the %d-chord inscription did not solve" % n_chords)
    return (res.fos - arc.fos) / arc.fos, arc.fos, res.fos


# ======================================================================
class TestTheIdentityHoldsWithTheTrueCentre:
    """The positive control, and the one that says the machinery is right.

    If a polyline that IS a circle reproduces the circle when the axis is
    the circle's own centre, then slicing, the base frame, the moment sums
    and every method are all consistent, and what remains is purely the
    choice of point. That is the claim, and it is what licenses reading
    the drift below as a property of the convention.
    """

    def test_every_method_reproduces_the_arc(self):
        project = _two_layer_slope()
        project.settings.search.axis_x = _DEEP[0]
        project.settings.search.axis_y = _DEEP[1]
        bad = []
        for mid in sorted(method_registry()):
            rel, arc, poly = _drift(project, mid, _DEEP, _CHORDS[-1])
            if abs(rel) >= 0.005:
                bad.append("%s: %.4f against the arc's %.4f (%+.2f %%)"
                           % (mid, poly, arc, 100.0 * rel))
        assert not bad, "\n".join(bad)

    def test_it_holds_on_a_drained_slope_too(self):
        """phi = 0 takes the normal force out of the STRENGTH but not out
        of its moment about a displaced axis, so the identity is checked
        with friction as well."""
        project = _drained_slope()
        circle_def = (60.0, 60.0, 45.0)
        project.settings.search.axis_x = circle_def[0]
        project.settings.search.axis_y = circle_def[1]
        for mid in ("ordinary_fellenius", "bishop_simplified", "spencer"):
            rel, arc, poly = _drift(project, mid, circle_def, _CHORDS[-1])
            assert abs(rel) < 0.005, (
                "%s: %.4f against the arc's %.4f (%+.2f %%)"
                % (mid, poly, arc, 100.0 * rel))


# ======================================================================
class TestWhatTheConventionCosts:
    """The measurement. Wide bands, but bands: moving the axis moves them.

    Not an equality, because the exact figure depends on the slice count
    and on which circle is chosen, and pinning it to four decimals would
    make this a snapshot of a run instead of a statement about a rule.
    """

    #: Measured at 64 chords, 150 slices: Ordinary -4.69 %, Bishop
    #: -4.18 %. The band leaves room either side without admitting zero.
    DRIFT_LO = 0.030
    DRIFT_HI = 0.065

    def test_the_moment_only_methods_drift(self):
        project = _two_layer_slope()
        for mid in _MOMENT_ONLY:
            rel, arc, poly = _drift(project, mid, _DEEP, _CHORDS[-1])
            assert rel < 0.0, (
                "%s reads ABOVE its own arc (%+.2f %%), which is not the "
                "direction this convention errs in" % (mid, 100.0 * rel))
            assert self.DRIFT_LO < abs(rel) < self.DRIFT_HI, (
                "%s drifts %+.2f %% from its own arc; the measured value "
                "is about -4.4 %% and this file exists to keep that "
                "number honest" % (mid, 100.0 * rel))

    def test_the_drift_does_not_shrink_when_the_polyline_is_refined(self):
        """The half that proves it is the axis and not discretisation.
        A chord polygon converges to its arc like 1/n^2; this does not
        converge at all."""
        project = _two_layer_slope()
        for mid in _MOMENT_ONLY:
            coarse, _a, _p = _drift(project, mid, _DEEP, _CHORDS[0])
            fine, _a, _p = _drift(project, mid, _DEEP, _CHORDS[-1])
            assert abs(fine) > 0.5 * abs(coarse), (
                "%s: %d -> %d chords took the drift from %+.2f %% to "
                "%+.2f %%, which is what discretisation would do — the "
                "bias may have been fixed, and if so this file is out of "
                "date" % (mid, _CHORDS[0], _CHORDS[-1],
                          100.0 * coarse, 100.0 * fine))

    def test_the_methods_that_satisfy_both_equilibria_do_not_drift(self):
        """Spencer and GLE solve force AND moment equilibrium, so their
        answer cannot depend on the point moments are taken about. This is
        the theoretical half of the diagnosis, asserted rather than
        assumed."""
        project = _two_layer_slope()
        for mid in _BOTH_EQUILIBRIA:
            rel, arc, poly = _drift(project, mid, _DEEP, _CHORDS[-1])
            assert abs(rel) < 0.005, (
                "%s drifts %+.2f %% from its own arc; it satisfies force "
                "equilibrium too and should not be able to"
                % (mid, 100.0 * rel))


# ======================================================================
class TestTheAxisItself:
    """Where the automatic axis lands, and where it does not."""

    def test_it_is_built_from_the_chord_alone(self):
        """midpoint(chord) + rot90(chord), stated as arithmetic so the
        rule is checkable without reading the implementation."""
        surf = SlipSurface(polyline=Polyline(vertices=[
            Vertex(0.0, 10.0), Vertex(5.0, 6.0), Vertex(10.0, 0.0)],
            closed=False))
        dx, dy = 10.0 - 0.0, 0.0 - 10.0
        ax, ay = moment_axis(surf, None)
        assert ax == pytest.approx(5.0 - dy)
        assert ay == pytest.approx(5.0 + dx)

    def test_refining_the_polyline_does_not_move_it(self):
        """Which is the mechanism: it reads two points, so there is
        nothing for a third to change."""
        project = _two_layer_slope()
        circle, _res = _resolved_circle(
            project, method_registry()["spencer"](), _DEEP, _SLICES)
        axes = [moment_axis(_inscribed(_DEEP, circle.x_left,
                                       circle.x_right, n), None)
                for n in (16, 64, 192)]
        span = max(math.hypot(a[0] - b[0], a[1] - b[1])
                   for a in axes for b in axes)
        assert span < 1e-6, "the axis moved %.4g m under refinement" % span

    def test_it_is_far_from_the_centre_of_the_arc_it_describes(self):
        """65 m on a radius of 56.40, and the number is kept because it is
        what makes the drift above unsurprising."""
        project = _two_layer_slope()
        circle, _res = _resolved_circle(
            project, method_registry()["spencer"](), _DEEP, _SLICES)
        ax, ay = moment_axis(
            _inscribed(_DEEP, circle.x_left, circle.x_right, 192), None)
        d = math.hypot(ax - _DEEP[0], ay - _DEEP[1])
        assert d > _DEEP[2], (
            "the axis is %.1f m from the centre of a circle of radius "
            "%.1f; if this has become small, the rule changed" % (d,
                                                                  _DEEP[2]))

    def test_the_user_axis_still_wins(self):
        """*Add Axis* is the user's own answer and overrides everything —
        and it is the only way to buy the identity above."""
        surf = SlipSurface(polyline=Polyline(vertices=[
            Vertex(0.0, 10.0), Vertex(5.0, 6.0), Vertex(10.0, 0.0)],
            closed=False))
        assert moment_axis(surf, (7.0, 11.0)) == (7.0, 11.0)

    def test_a_circle_answers_with_its_own_centre(self):
        circle = SlipCircle(centre_x=_DEEP[0], centre_y=_DEEP[1],
                            radius=_DEEP[2])
        assert moment_axis(circle, None) == (_DEEP[0], _DEEP[1])


# ======================================================================
class TestWhatMustNotMove:
    """A circle has a real centre of rotation and always had."""

    def test_phi_zero_still_collapses_ordinary_onto_bishop(self):
        """With phi = 0 the resisting moment about a circle's centre is
        sum(c*l*R) for both — the normal force drops out of the strength
        and has no moment about the centre — so they are the same sum.
        A property of the model, not a stored number."""
        project = _two_layer_slope()
        vals = {}
        for mid in ("ordinary_fellenius", "bishop_simplified", "spencer"):
            _c, res = _resolved_circle(
                project, method_registry()[mid](), _DEEP, _SLICES)
            vals[mid] = res.fos
        assert abs(vals["ordinary_fellenius"]
                   - vals["bishop_simplified"]) < 1e-9, vals
        # Spencer ITERATES to the same answer, so it agrees to its own
        # convergence tolerance and no further.
        assert abs(vals["spencer"] - vals["bishop_simplified"]) \
            / vals["bishop_simplified"] < 1e-4, vals

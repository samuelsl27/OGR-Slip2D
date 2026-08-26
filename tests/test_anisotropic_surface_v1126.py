# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.126 — the anisotropic surface: a polyline that says which way the
bedding runs, for anisotropy that changes direction with position.

What these tests protect
------------------------

**The identity that makes it checkable.** A STRAIGHT anisotropic surface
at alpha degrees has to give exactly what the material's own global
``bedding_angle = alpha`` already gave — digit for digit, through a whole
analysis. That is what says the new path computes the same quantity as
the old one and not merely a similar-looking number. Everything else the
feature does is the same machinery pointed at a curve.

**That nothing moves without one.** A material naming no anisotropic
surface, or naming one that has been deleted, falls back on its global
angle. Not a digit may change for any model in the suite, which is why
that is asserted rather than assumed.

**The closest point, not the one overhead.** This is the whole content of
the entity and the one place it differs from every other polyline in the
program: a water surface is read straight up, an anisotropic surface is
read at its nearest point. Under a steeply dipping fold the two are
different segments, and reading it the water way would give the wrong dip
exactly where the dip matters most.

**The vertex rule, awkwardness included.** When the nearest point of the
polyline is a vertex, the orientation taken is that of the segment drawn
FIRST — not the average of the two meeting there. The reference documents
this as a deliberate choice: the angle should be one the user drew rather
than one interpolated between two. Its visible consequence is that
reversing the drawing order of a kinked polyline can change the answer,
and the test below asserts that it does. An implementation that quietly
averaged would look tidier and would be a different model.

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
from ogr_core.geometry.anisotropic_surface import (  # noqa: E402
    anisotropy_angle_at,
    closest_segment_index,
    segment_angle_deg,
)
from ogr_core.materials import Material  # noqa: E402
from ogr_core.materials.builtin_models import AnisotropicLinear  # noqa: E402
from ogr_core.project import Project  # noqa: E402
from ogr_slip2d.methods import method_registry  # noqa: E402
from ogr_slip2d.search import GridSearch  # noqa: E402
from ogr_slip2d.surface import SlipCircle  # noqa: E402


def _line(*pts) -> Polyline:
    return Polyline(vertices=[Vertex(x, y) for x, y in pts], closed=False)


# ----------------------------------------------------------------------
def _slope(bedding_angle: float = 0.0, surface: Polyline | None = None,
           dangling: bool = False) -> Project:
    """A homogeneous anisotropic slope.

    ``bedding_angle`` is the material's own global angle; ``surface``, if
    given, is drawn as an anisotropic surface and assigned to it. Passing
    both is exactly how the identity below is set up: the two must agree
    when the surface is a straight line at the same angle.
    """
    p = Project("aniso")
    ext = Polyline(vertices=[
        Vertex(0.0, 0.0), Vertex(120.0, 0.0), Vertex(120.0, 20.0),
        Vertex(80.0, 20.0), Vertex(50.0, 40.0), Vertex(0.0, 40.0),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))

    mat = Material(
        name="bedded", unit_weight=20.0,
        strength=AnisotropicLinear(c1=5.0, phi1=12.0, c2=25.0, phi2=32.0,
                                   bedding_angle=bedding_angle,
                                   A=5.0, B=25.0))
    p.materials = [mat]
    p.resolve_regions()
    p.assign_material_at(60.0, 10.0, mat.id)

    if surface is not None:
        b = Boundary(polyline=surface,
                     btype=BoundaryType.ANISOTROPIC_SURFACE)
        p.add_boundary(b)
        mat.anisotropic_surface_id = b.id
    elif dangling:
        mat.anisotropic_surface_id = "a-boundary-that-was-deleted"

    p.settings.methods.num_slices = 40
    return p


def _fos(project, method_id: str = "bishop_simplified") -> float:
    g = GridSearch(method=method_registry()[method_id](), num_slices=40,
                   grid_nx=3, grid_ny=3, radius_increment=3)
    res = g.evaluate_circle(project, SlipCircle(centre_x=60.0, centre_y=62.0,
                                                radius=48.0))
    assert res is not None and res.is_valid, "the trial circle did not solve"
    return res.fos


# ======================================================================
class TestTheGeometryRule:
    """The polyline, asked directly. No analysis involved."""

    def test_a_horizontal_surface_reads_zero(self):
        assert anisotropy_angle_at(_line((0, 5), (100, 5)), 50.0, 0.0) \
            == pytest.approx(0.0, abs=1e-12)

    def test_the_angle_is_the_segment_orientation(self):
        pl = _line((0.0, 0.0), (10.0, 10.0))
        assert anisotropy_angle_at(pl, 5.0, 0.0) == pytest.approx(45.0)

    def test_the_direction_has_no_sense(self):
        """Drawing the same straight line the other way is the same
        bedding, so the angle may not flip: it is folded to (-90, 90]."""
        a = anisotropy_angle_at(_line((0.0, 0.0), (10.0, 10.0)), 5.0, 0.0)
        b = anisotropy_angle_at(_line((10.0, 10.0), (0.0, 0.0)), 5.0, 0.0)
        assert a == pytest.approx(b)

    def test_it_is_the_closest_point_and_not_the_one_overhead(self):
        """The discriminating case, and it has to be built on purpose.

        Two segments: a long shallow one, then a short steep one that
        doubles back above it. A point placed under the shallow segment
        but nearer the steep one must take the STEEP angle. Read
        vertically it would take the shallow one, which is what a water
        surface would do and what this entity exists not to do.
        """
        pl = _line((0.0, 0.0), (10.0, 0.0), (11.0, 10.0))
        # Just right of the kink and well below it: the perpendicular
        # distance to the steep segment beats the distance to the flat one.
        i = closest_segment_index(pl, 11.6, 5.0)
        assert i == 1, "took segment %r, not the steep one" % i
        assert segment_angle_deg(pl, 1) == pytest.approx(
            math.degrees(math.atan2(10.0, 1.0)))

    def test_at_a_vertex_the_first_drawn_segment_wins(self):
        """And reversing the polyline therefore changes the answer.

        The two segments meet at a right angle, so the two candidate
        answers are 0 and 90 degrees and no rounding can confuse them.
        The point sits exactly on the bisector, so the closest point of
        the polyline IS the shared vertex and both segments are equally
        near — which is the tie the rule exists to break.
        """
        forward = _line((0.0, 0.0), (10.0, 0.0), (10.0, 10.0))
        reverse = _line((10.0, 10.0), (10.0, 0.0), (0.0, 0.0))
        # (20, -10) is at distance sqrt(200) from the corner (10, 0) and
        # further from every interior point of either segment.
        a = anisotropy_angle_at(forward, 20.0, -10.0)
        b = anisotropy_angle_at(reverse, 20.0, -10.0)
        assert a == pytest.approx(0.0, abs=1e-9), a
        assert abs(b) == pytest.approx(90.0, abs=1e-9), b

    def test_a_polyline_with_one_vertex_cannot_answer(self):
        """None, and not zero: zero is a horizontal bedding somebody
        entered, None is the polyline having nothing to say. The caller
        falls back on the material's own angle."""
        assert anisotropy_angle_at(_line((0.0, 0.0)), 5.0, 5.0) is None


# ======================================================================
class TestTheIdentity:
    """A straight surface at alpha IS a global bedding angle of alpha."""

    def test_straight_surface_equals_the_global_angle(self):
        for alpha in (0.0, 20.0, -35.0, 60.0):
            dx = 100.0
            dy = dx * math.tan(math.radians(alpha))
            surf = _line((0.0, 15.0), (dx, 15.0 + dy))
            with_surface = _fos(_slope(bedding_angle=0.0, surface=surf))
            with_angle = _fos(_slope(bedding_angle=alpha))
            assert with_surface == pytest.approx(with_angle, rel=1e-12), (
                "alpha = %g: surface %.12f against global %.12f"
                % (alpha, with_surface, with_angle))

    def test_every_method_agrees_on_the_identity(self):
        alpha = 25.0
        surf = _line((0.0, 15.0),
                     (100.0, 15.0 + 100.0 * math.tan(math.radians(alpha))))
        bad = []
        for mid in sorted(method_registry()):
            a = _fos(_slope(bedding_angle=0.0, surface=surf), mid)
            b = _fos(_slope(bedding_angle=alpha), mid)
            if a != pytest.approx(b, rel=1e-9):
                bad.append("%s: %.10f vs %.10f" % (mid, a, b))
        assert not bad, "\n".join(bad)


# ======================================================================
class TestWhatMustNotMove:

    def test_no_surface_no_change(self):
        """The fallback, stated as an identity so it cannot rot."""
        plain = _fos(_slope(bedding_angle=17.0))
        again = _fos(_slope(bedding_angle=17.0, surface=None))
        assert plain == pytest.approx(again, rel=1e-15)

    def test_a_dangling_id_falls_back_instead_of_failing(self):
        """A material pointing at a deleted boundary behaves as one
        pointing at nothing. Anything else would turn a stale reference
        into a refusal to analyse — and the fallback is not a guess, it
        is the documented behaviour of a material with no surface."""
        assert _fos(_slope(bedding_angle=17.0, dangling=True)) \
            == pytest.approx(_fos(_slope(bedding_angle=17.0)), rel=1e-15)


# ======================================================================
class TestRuleSeven:
    """Every control has to move the number."""

    def test_a_folded_surface_moves_the_number(self):
        flat = _line((0.0, 15.0), (120.0, 15.0))
        folded = _line((0.0, 5.0), (40.0, 30.0), (80.0, 5.0), (120.0, 30.0))
        a = _fos(_slope(bedding_angle=0.0, surface=flat))
        b = _fos(_slope(bedding_angle=0.0, surface=folded))
        assert abs(a - b) > 1e-4, (
            "the fold changed nothing: %.6f against %.6f" % (a, b))

    def test_the_vertex_order_moves_the_number(self):
        """The awkward consequence of the documented vertex rule, at the
        level of a factor of safety and not just an angle. It is here so
        that anyone tempted to average the two segments finds out that it
        is a modelling decision and not a tidy-up.

        **The shape is chosen, not arbitrary**, and the first attempt did
        not work. The set of points whose nearest point on a polyline is a
        VERTEX is the exterior wedge of that corner — and for a corner
        pointing UP, that wedge lies above it. So the surface has to be an
        inverted V whose apex sits INSIDE the sliding mass, with the
        slice bases passing over it. A downward spike, which looks like
        the more obviously kinked shape, puts the wedge below the model
        where no slice base ever goes: measured, it moved 205 sample
        points by nothing at all except one, and the factor of safety by
        3e-15.

        The apex is at (60, 10) and the arms drop to y = -10, below the
        model. That is legal and deliberate — an anisotropic surface is
        not model geometry and is never intersected with any — and it is
        what makes the two arms differ by 37 degrees, which is what the
        wedge needs in order to be worth measuring.
        """
        kinked = _line((0.0, -10.0), (60.0, 10.0), (120.0, -10.0))
        rev = Polyline(vertices=list(reversed(kinked.vertices)), closed=False)
        a = _fos(_slope(bedding_angle=0.0, surface=kinked))
        b = _fos(_slope(bedding_angle=0.0, surface=rev))
        assert abs(a - b) > 1e-6, (
            "reversing a kinked surface changed nothing: %.8f" % a)


# ======================================================================
class TestSerialisation:

    def test_the_surface_and_the_link_survive_a_round_trip(self):
        surf = _line((0.0, 5.0), (40.0, 30.0), (80.0, 5.0))
        p = _slope(bedding_angle=0.0, surface=surf)
        back = Project.from_dict(p.to_dict())

        bs = [b for b in back.boundaries
              if b.btype == BoundaryType.ANISOTROPIC_SURFACE]
        assert len(bs) == 1
        # The ORDER of the vertices is part of the model — it decides the
        # angle at a kink — so a round trip that reordered them would be a
        # round trip that changed the answer.
        assert [(v.x, v.y) for v in bs[0].polyline.vertices] == \
            [(0.0, 5.0), (40.0, 30.0), (80.0, 5.0)]
        assert back.materials[0].anisotropic_surface_id == bs[0].id
        assert _fos(back) == pytest.approx(_fos(p), rel=1e-12)

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.89 — a contour that encloses no soil is detectable, and says where.

WHAT INVARIANT THIS PROTECTS: that "this boundary has ground in it" is a
question with a computable answer, instead of something noticed years later
by the shape of a failure.

Why this file exists. Nine test models in this project shared one contour::

    (0,0) (60,0) (60,H) (crest,H) (toe,0)

It draws a perfectly ordinary slope and it is broken: the closing edge runs
back along the bottom one, so between x = 0 and the toe at x = 30 the ground
surface and the base of the model are the same line at y = 0, enclosing
nothing. Nobody saw it for seventy versions because nothing downstream
complained — the analysis simply computed about ground that was not there.

v0.1.84 met it the hard way. Once surfaces leaving the soil region stopped
being analysed, the only circles left with enough driving moment to carry five
soil nails were exactly the ones that had been reaching below the base, and
``test_support_increases_fos`` returned no critical surface at all. The
diagnosis cost far more than the fix, and it is the sort of thing a DXF import
can hand you with nobody having drawn anything by hand.

The measurement is on the ENVELOPES, upper minus lower, so it does not care how
the contour was wound or where its vertices sit — which matters, because the
vertex-based reasoning is precisely what got the ground surface wrong for
eighty versions (see ogr_core/geometry/ground.py).

WHAT THIS DOES NOT DO: it does not stop a new test file from reintroducing the
contour. Making that automatic would mean funnelling every test model through
one factory, which is a larger change than this version. See
docs/PENDIENTES.md.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

# The contour, before and after, with the geometry the suite actually uses.
_H = 12.0
_TOE = 30.0
_CREST = _TOE + _H / math.tan(math.radians(30.96))     # 50.003
_BASE = -10.0


def _verts(pairs):
    from ogr_core.geometry import Vertex
    return [Vertex(x, y) for x, y in pairs]


def _degenerate():
    return _verts([(0, 0), (60, 0), (60, _H), (_CREST, _H), (_TOE, 0)])


def _fixed():
    return _verts([(0, _BASE), (60, _BASE), (60, _H),
                   (_CREST, _H), (_TOE, 0), (0, 0)])


class TestTheHistoricalContourIsCaught:
    def test_the_degenerate_contour_is_flagged(self):
        from ogr_core.geometry import zero_thickness_spans
        spans = zero_thickness_spans(_degenerate())
        assert spans, "the contour that broke v0.1.84 must be detected"

    def test_it_says_WHERE(self):
        """A verdict without a location is nearly useless on an imported
        boundary with two hundred vertices: the answer needed is which
        stretch to go and look at."""
        from ogr_core.geometry import zero_thickness_spans
        spans = zero_thickness_spans(_degenerate())
        assert len(spans) == 1, spans
        x0, x1 = spans[0]
        assert abs(x0 - 0.0) < 1e-9, x0
        assert abs(x1 - _TOE) < 1e-9, x1

    def test_the_fixed_contour_is_clean(self):
        from ogr_core.geometry import zero_thickness_spans
        assert zero_thickness_spans(_fixed()) == []

    def test_the_fix_really_added_soil_under_the_toe(self):
        """Guards the guard: if the 'fixed' contour were fixed by moving the
        toe rather than by adding a foundation, the test above would pass and
        the model would be a different problem."""
        from ogr_core.geometry import lower_y_at, upper_y_at
        v = _fixed()
        for x in (1.0, 15.0, 29.0):
            assert abs(upper_y_at(v, x) - 0.0) < 1e-9, x
            assert abs(lower_y_at(v, x) - _BASE) < 1e-9, x


class TestNoFalsePositives:
    def test_a_plain_rectangle_is_clean(self):
        from ogr_core.geometry import zero_thickness_spans
        assert zero_thickness_spans(
            _verts([(0, 0), (60, 0), (60, 10), (0, 10)])) == []

    def test_a_vertical_cut_face_is_clean(self):
        """A vertical step in the ground is not a degenerate contour: upper
        and lower envelopes meet at a single abscissa, which has zero width
        and must not be reported.

        The first version of this case was itself degenerate — ``(0,0)
        (40,0) (40,12) (20,12) (20,0)`` closes back along y = 0 and encloses
        nothing left of x = 20, which is the very contour under test. The
        detector was right and the test was wrong, which is worth leaving
        written down: this shape is easy to draw by accident."""
        from ogr_core.geometry import zero_thickness_spans
        # A bench: 12 m tall left of x = 20, 6 m right of it, vertical face.
        assert zero_thickness_spans(
            _verts([(0, 0), (40, 0), (40, 6), (20, 6), (20, 12), (0, 12)])) == []

    def test_a_thin_but_real_layer_is_not_flagged(self):
        """A 5 cm bench over a 60 m model is 0.08 % of the diagonal — real
        soil, and a detector that called it nothing would make the check
        unusable on surveyed ground."""
        from ogr_core.geometry import zero_thickness_spans
        v = _verts([(0, 0), (60, 0), (60, _H), (_CREST, _H),
                    (_TOE, 0.05), (0, 0.05)])
        assert zero_thickness_spans(v) == [], zero_thickness_spans(v)

    def test_the_two_reference_models_are_clean(self):
        """Real geometry, from the two validated benchmarks. A detector that
        flagged either of those would be worse than none."""
        from ogr_core.geometry import zero_thickness_spans
        ej1 = _verts([(120, 0), (120, 25), (75, 25), (50, 50),
                      (0, 50), (0, 30), (0, 20), (0, 0)])
        ej2 = _verts([(0, 0), (100, 0), (100, 70), (70, 70), (55, 55),
                      (40, 55), (15, 30), (-50, 30), (-50, 0)])
        assert zero_thickness_spans(ej1) == []
        assert zero_thickness_spans(ej2) == []


class TestItDoesNotDependOnHowTheContourWasDrawn:
    def test_winding_does_not_matter(self):
        from ogr_core.geometry import zero_thickness_spans
        forward = _degenerate()
        assert (zero_thickness_spans(forward)
                == zero_thickness_spans(list(reversed(forward))))

    def test_extra_collinear_vertices_do_not_matter(self):
        """A vertex added on the bottom edge changes nothing about the
        geometry, and must change nothing about the verdict. Adding one on a
        bottom edge is exactly what broke the ground surface in v0.1.84."""
        from ogr_core.geometry import zero_thickness_spans
        v = _verts([(0, 0), (25, 0), (60, 0), (60, _H),
                    (_CREST, _H), (_TOE, 0)])
        spans = zero_thickness_spans(v)
        assert len(spans) == 1, spans
        assert abs(spans[0][1] - _TOE) < 1e-9, spans

    def test_the_verdict_is_scale_invariant(self):
        """Rule of the house: tolerances relative to the model, never
        absolute. The same slope in millimetres must give the same answer —
        an absolute y tolerance would call a 12 mm model degenerate and a
        12 km one clean."""
        from ogr_core.geometry import zero_thickness_spans
        for scale in (0.001, 1.0, 1000.0):
            good = _verts([(x * scale, y * scale)
                           for x, y in [(0, _BASE), (60, _BASE), (60, _H),
                                        (_CREST, _H), (_TOE, 0), (0, 0)]])
            bad = _verts([(x * scale, y * scale)
                          for x, y in [(0, 0), (60, 0), (60, _H),
                                       (_CREST, _H), (_TOE, 0)]])
            assert zero_thickness_spans(good) == [], scale
            assert len(zero_thickness_spans(bad)) == 1, scale

    def test_it_accepts_the_three_shapes_the_call_sites_use(self):
        """Boundary, Polyline and a bare vertex list — the same three forms
        ground_surface() had to accept, for the same reason."""
        from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                       zero_thickness_spans)
        verts = _degenerate()
        poly = Polyline(vertices=verts, closed=True)
        bound = Boundary(polyline=poly, btype=BoundaryType.EXTERNAL)
        a = zero_thickness_spans(verts)
        assert a == zero_thickness_spans(poly)
        assert a == zero_thickness_spans(bound)


class TestLowerEnvelope:
    """``lower_y_at`` is new, and it is the half of the pair that had no
    call site before, so it gets its own cases."""

    def test_vertical_edges_go_opposite_ways(self):
        from ogr_core.geometry import lower_y_at, upper_y_at
        v = _verts([(0, 0), (10, 0), (10, 5), (0, 5)])
        assert abs(upper_y_at(v, 10.0) - 5.0) < 1e-9
        assert abs(lower_y_at(v, 10.0) - 0.0) < 1e-9

    def test_outside_the_model_is_none(self):
        from ogr_core.geometry import lower_y_at
        assert lower_y_at(_fixed(), 1000.0) is None

    def test_it_follows_a_sloping_base(self):
        from ogr_core.geometry import lower_y_at
        v = _verts([(0, 0), (60, -10), (60, 20), (0, 20)])
        assert abs(lower_y_at(v, 30.0) - (-5.0)) < 1e-9

    def test_degenerate_input_is_not_a_crash(self):
        from ogr_core.geometry import zero_thickness_spans
        assert zero_thickness_spans(_verts([(0, 0), (1, 1)])) == []
        assert zero_thickness_spans([]) == []
        # All vertices coincident: zero diagonal, no verdict to give.
        assert zero_thickness_spans(
            _verts([(5, 5), (5, 5), (5, 5)])) == []

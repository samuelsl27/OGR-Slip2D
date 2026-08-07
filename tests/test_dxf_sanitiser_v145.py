# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.45 — DXF geometry sanitiser (Phase D1).

This is the phase that decides whether an imported drawing is usable. The
decisive test is not "did the code run" but **do the regions close**, and
it is checked with the same invariant that validated the FE mesh: the
summed area of the reconstructed regions must equal the area of the
external boundary. That single check catches gaps, overlaps and leaks at
once.

Particular attention goes to **endpoint welding onto the interior of a
segment with node insertion**. Welding endpoint-to-endpoint only leaves
T-junctions that touch geometrically but share no node, and those are
exactly what once left material regions undetected in the editor.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.dxf import (  # noqa: E402
    DEFAULT_SIMPLIFY_PCT,
    DEFAULT_WELD_PCT,
    WELD_PCT_RANGE,
    DxfEntityKind as K,
    DxfPolyline,
    GeometrySanitiser,
    douglas_peucker,
)
from ogr_core.geometry import (  # noqa: E402
    Boundary,
    BoundaryType,
    Polyline,
    Vertex,
)
from ogr_core.geometry.regions import build_regions  # noqa: E402

_DIAG = math.hypot(100.0, 50.0)


def _square(x0=0.0, y0=0.0, x1=100.0, y1=50.0):
    return DxfPolyline(
        points=[(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)],
        closed=True)


def _sanitise(by_kind, weld=DEFAULT_WELD_PCT, simplify_pct=0.0,
              simplify=False, diagonal=_DIAG):
    s = GeometrySanitiser(diagonal, weld_pct=weld,
                          simplify_pct=simplify_pct, simplify=simplify)
    return s.run(by_kind), s.report


def _regions(out):
    """Rebuild regions from the sanitised geometry."""
    ext = out[K.EXTERNAL][0]
    ext_b = Boundary(btype=BoundaryType.EXTERNAL,
                     polyline=Polyline(
                         vertices=[Vertex(x, y) for x, y in ext.points],
                         closed=True))
    mats = [Boundary(btype=BoundaryType.MATERIAL,
                     polyline=Polyline(
                         vertices=[Vertex(x, y) for x, y in p.points],
                         closed=p.closed))
            for p in out.get(K.MATERIAL, [])]
    return build_regions(ext_b, mats)


def _area(points):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


# ======================================================================
class TestRegionClosure:
    """The invariant that matters: regions must tile the external
    boundary exactly."""

    def test_material_short_of_the_boundary_still_closes(self):
        """A material line stopping 0.4 units short at both ends — a gap
        invisible at normal zoom — must still produce closed regions
        after welding."""
        ext = _square()
        mat = DxfPolyline(points=[(0.4, 25.0), (99.6, 25.0)])
        out, rep = _sanitise({K.EXTERNAL: [ext], K.MATERIAL: [mat]},
                             weld=0.5)
        assert rep.welded_endpoints == 2
        assert rep.nodes_inserted == 2
        regs = _regions(out)
        assert len(regs) == 2, len(regs)
        total = sum(r.area for r in regs)
        assert abs(total - 5000.0) / 5000.0 < 1e-6, total

    def test_material_crossing_the_boundary_still_closes(self):
        """Overshooting is as common as falling short."""
        ext = _square()
        mat = DxfPolyline(points=[(-0.4, 25.0), (100.4, 25.0)])
        out, _rep = _sanitise({K.EXTERNAL: [ext], K.MATERIAL: [mat]},
                              weld=0.5)
        regs = _regions(out)
        assert len(regs) >= 2
        total = sum(r.area for r in regs)
        assert abs(total - 5000.0) / 5000.0 < 1e-4, total

    def test_two_crossing_materials_give_four_regions(self):
        """Two material lines crossing each other must share a node at the
        crossing, otherwise the four quadrants never form."""
        ext = _square()
        h = DxfPolyline(points=[(0.0, 25.0), (100.0, 25.0)])
        v = DxfPolyline(points=[(50.0, 0.0), (50.0, 50.0)])
        out, rep = _sanitise({K.EXTERNAL: [ext], K.MATERIAL: [h, v]},
                             weld=0.2)
        assert rep.crossings_split >= 1
        regs = _regions(out)
        assert len(regs) == 4, len(regs)
        total = sum(r.area for r in regs)
        assert abs(total - 5000.0) / 5000.0 < 1e-6

    def test_area_invariant_holds_with_simplification_on(self):
        """Simplification must not reopen anything it was run after."""
        ext = _square()
        pts = [(0.0, 25.0)]
        for i in range(1, 60):
            pts.append((100.0 * i / 60.0, 25.0 + 0.001 * (i % 3)))
        pts.append((100.0, 25.0))
        mat = DxfPolyline(points=pts)
        out, rep = _sanitise({K.EXTERNAL: [ext], K.MATERIAL: [mat]},
                             weld=0.2, simplify_pct=0.05, simplify=True)
        assert rep.vertices_after < rep.vertices_before
        regs = _regions(out)
        assert len(regs) == 2
        total = sum(r.area for r in regs)
        assert abs(total - 5000.0) / 5000.0 < 1e-4, total


# ======================================================================
class TestEndpointWelding:
    def test_interior_contact_inserts_a_node(self):
        """The heart of it: an endpoint landing on the INTERIOR of a
        segment must add a node there. Without it the junction touches but
        shares nothing."""
        ext = _square()
        before = ext.n
        mat = DxfPolyline(points=[(0.3, 25.0), (50.0, 25.0)])
        out, rep = _sanitise({K.EXTERNAL: [ext], K.MATERIAL: [mat]},
                             weld=0.5)
        assert rep.nodes_inserted >= 1
        assert out[K.EXTERNAL][0].n > before

    def test_contact_near_a_corner_snaps_to_it(self):
        """An endpoint landing near an EXISTING vertex must snap to that
        vertex, not gain a node of its own: a node inserted a fraction of
        a unit from a corner is a near-degenerate sliver segment, which is
        worse geometry than reusing the corner already there.

        The assertion is on the OUTCOME rather than on which stage did it:
        vertex merging may already collapse the point onto the corner
        before the welder sees it, and either route is correct.
        """
        ext = _square()
        before = ext.n
        mat = DxfPolyline(points=[(0.2, 0.2), (50.0, 25.0)])
        out, rep = _sanitise({K.EXTERNAL: [ext], K.MATERIAL: [mat]},
                             weld=0.5)
        assert rep.nodes_inserted == 0
        assert out[K.EXTERNAL][0].n == before
        # The endpoint now sits exactly on the corner
        assert out[K.MATERIAL][0].points[0] == (0, 0)

    def test_exact_contact_still_inserts_a_node(self):
        """Regression: an endpoint touching a segment interior EXACTLY
        (distance zero) must still get a node inserted.

        An early guard skipped ``d < 1e-15`` to avoid self-contact, and in
        doing so silently skipped the cleanest case of all — geometry
        drawn correctly in CAD that touches exactly — leaving a
        T-junction with no shared node and a region that never closed.
        Self-contact is excluded by identity, not by distance.
        """
        ext = _square()
        mat = DxfPolyline(points=[(0.0, 25.0), (100.0, 25.0)])
        out, rep = _sanitise({K.EXTERNAL: [ext], K.MATERIAL: [mat]},
                             weld=0.2)
        assert rep.nodes_inserted == 2, rep.summary()
        regs = _regions(out)
        assert len(regs) == 2
        # Relative tolerance: the region builder carries a few parts in a
        # billion of floating-point noise, which an absolute threshold on
        # an area of 5000 would flag as a failure.
        total = sum(r.area for r in regs)
        assert abs(total - 5000.0) / 5000.0 < 1e-6, total

    def test_beyond_tolerance_is_not_welded(self):
        """Welding must not drag geometry that was never meant to touch."""
        ext = _square()
        mat = DxfPolyline(points=[(20.0, 25.0), (80.0, 25.0)])
        _out, rep = _sanitise({K.EXTERNAL: [ext], K.MATERIAL: [mat]},
                              weld=0.05)
        assert rep.welded_endpoints == 0

    def test_welding_is_order_independent(self):
        """The editor bug this replaces was order-dependent, so the same
        geometry given in either order must give the same result."""
        for order in (False, True):
            ext = _square()
            a = DxfPolyline(points=[(0.3, 25.0), (99.7, 25.0)])
            b = DxfPolyline(points=[(50.0, 0.3), (50.0, 49.7)])
            mats = [b, a] if order else [a, b]
            out, _rep = _sanitise({K.EXTERNAL: [ext], K.MATERIAL: mats},
                                  weld=0.5)
            regs = _regions(out)
            assert len(regs) == 4, (order, len(regs))


# ======================================================================
class TestExternalBoundary:
    def test_open_boundary_is_closed(self):
        ext = DxfPolyline(points=[(0, 0), (100, 0), (100, 50), (0, 50)],
                          closed=False)
        out, rep = _sanitise({K.EXTERNAL: [ext]})
        assert rep.closed_boundaries == 1
        e = out[K.EXTERNAL][0]
        assert e.closed is True
        assert e.points[0] == e.points[-1]

    def test_large_gap_is_reported(self):
        """Closing a big gap changes the shape, so the user must be told."""
        ext = DxfPolyline(points=[(0, 0), (100, 0), (100, 50), (0, 50)],
                          closed=False)
        _out, rep = _sanitise({K.EXTERNAL: [ext]})
        assert any(p["kind"] == "external_gap" for p in rep.problems)

    def test_already_closed_is_left_alone(self):
        out, rep = _sanitise({K.EXTERNAL: [_square()]})
        assert rep.closed_boundaries == 0
        assert out[K.EXTERNAL][0].n == 5

    def test_missing_external_is_reported_not_fatal(self):
        mat = DxfPolyline(points=[(0, 25), (100, 25)])
        out, rep = _sanitise({K.MATERIAL: [mat]})
        assert any(p["kind"] == "external_missing" for p in rep.problems)
        assert out                       # import proceeds anyway

    def test_multiple_externals_keeps_the_largest(self):
        big = _square()
        small = _square(10, 10, 20, 20)
        out, rep = _sanitise({K.EXTERNAL: [small, big]})
        assert any(p["kind"] == "external_multiple" for p in rep.problems)
        assert len(out[K.EXTERNAL]) == 1
        assert _area(out[K.EXTERNAL][0].points) > 4000.0


# ======================================================================
class TestSimplification:
    def test_douglas_peucker_keeps_endpoints(self):
        pts = [(0, 0), (1, 0.01), (2, -0.01), (3, 0.0), (4, 0)]
        out = douglas_peucker(pts, 0.1)
        assert out[0] == pts[0] and out[-1] == pts[-1]
        assert len(out) < len(pts)

    def test_douglas_peucker_keeps_real_shape(self):
        pts = [(0, 0), (1, 0), (2, 5), (3, 0), (4, 0)]
        out = douglas_peucker(pts, 0.1)
        assert (2, 5) in out

    def test_zero_tolerance_keeps_everything(self):
        pts = [(0, 0), (1, 0.01), (2, 0)]
        assert douglas_peucker(pts, 0.0) == pts

    def test_shared_nodes_survive_simplification(self):
        """A vertex another polyline was welded to must never be removed:
        that would silently reopen the region."""
        ext = _square()
        pts = [(0.0, 25.0)] + [(x, 25.0) for x in range(1, 100)] + \
              [(100.0, 25.0)]
        mat = DxfPolyline(points=pts)
        out, _rep = _sanitise({K.EXTERNAL: [ext], K.MATERIAL: [mat]},
                              weld=0.2, simplify_pct=0.1, simplify=True)
        regs = _regions(out)
        assert len(regs) == 2
        # And the junction points are still present on the external
        e = out[K.EXTERNAL][0].points
        assert any(abs(p[1] - 25.0) < 1e-6 and abs(p[0]) < 1e-6
                   for p in e)

    def test_reports_vertex_counts_for_the_preview(self):
        pts = [(0.0, 25.0)] + [(x, 25.0 + 0.0005) for x in range(1, 80)] \
            + [(100.0, 25.0)]
        _out, rep = _sanitise({K.EXTERNAL: [_square()],
                               K.MATERIAL: [DxfPolyline(points=pts)]},
                              weld=0.2, simplify_pct=0.05, simplify=True)
        assert rep.vertices_before > rep.vertices_after
        assert rep.vertices_removed > 0


# ======================================================================
class TestRelativeTolerances:
    def test_tolerance_scales_with_the_model(self):
        """The same drawing in metres and in millimetres must be repaired
        identically: that is the whole point of a relative tolerance."""
        results = []
        for scale in (1.0, 0.001):
            ext = DxfPolyline(
                points=[(0, 0), (100 * scale, 0), (100 * scale, 50 * scale),
                        (0, 50 * scale), (0, 0)], closed=True)
            mat = DxfPolyline(points=[(0.4 * scale, 25 * scale),
                                      (99.6 * scale, 25 * scale)])
            diag = math.hypot(100 * scale, 50 * scale)
            out, rep = _sanitise({K.EXTERNAL: [ext], K.MATERIAL: [mat]},
                                 weld=0.5, diagonal=diag)
            results.append((rep.welded_endpoints, rep.nodes_inserted,
                            len(_regions(out))))
        assert results[0] == results[1], results

    def test_defaults_are_within_the_recommended_range(self):
        lo, hi = WELD_PCT_RANGE
        assert lo <= DEFAULT_WELD_PCT <= hi
        assert DEFAULT_SIMPLIFY_PCT > 0


# ======================================================================
class TestProblemReport:
    def test_dangling_end_is_reported_with_a_location(self):
        """The dialog needs coordinates so it can centre the view on the
        problem."""
        ext = _square()
        mat = DxfPolyline(points=[(30.0, 25.0), (70.0, 25.0)])
        _out, rep = _sanitise({K.EXTERNAL: [ext], K.MATERIAL: [mat]},
                              weld=0.05)
        dangling = [p for p in rep.problems if p["kind"] == "dangling_end"]
        assert dangling
        assert dangling[0]["x"] is not None
        assert dangling[0]["y"] is not None

    def test_clean_geometry_reports_no_problems(self):
        ext = _square()
        mat = DxfPolyline(points=[(0.0, 25.0), (100.0, 25.0)])
        _out, rep = _sanitise({K.EXTERNAL: [ext], K.MATERIAL: [mat]},
                              weld=0.2)
        assert rep.ok, rep.problems

    def test_empty_input_is_reported(self):
        _out, rep = _sanitise({})
        assert any(p["kind"] == "empty" for p in rep.problems)

    def test_summary_is_readable(self):
        ext = _square()
        _out, rep = _sanitise({K.EXTERNAL: [ext]})
        assert "vertices" in rep.summary()

    def test_input_is_not_mutated(self):
        """The sanitiser works on copies: re-running the import with
        different tolerances must start from the original drawing."""
        ext = _square()
        mat = DxfPolyline(points=[(0.4, 25.0), (99.6, 25.0)])
        before = list(mat.points)
        _sanitise({K.EXTERNAL: [ext], K.MATERIAL: [mat]}, weld=0.5)
        assert mat.points == before

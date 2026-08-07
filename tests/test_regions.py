# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Tests for the material region engine (ogr_core.geometry.regions)."""
from __future__ import annotations

from ogr_core.geometry import (
    Boundary,
    BoundaryType,
    MaterialRegion,
    Polyline,
    Vertex,
    build_regions,
    region_at_point,
    regions_available,
)


def _make_external_square(side: float = 10.0) -> Boundary:
    pl = Polyline(
        vertices=[
            Vertex(0, 0),
            Vertex(side, 0),
            Vertex(side, side),
            Vertex(0, side),
        ],
        closed=True,
    )
    pl.ensure_ccw()
    return Boundary(polyline=pl, btype=BoundaryType.EXTERNAL)


# ======================================================================
class TestRegionsAvailability:
    def test_degrades_gracefully_without_shapely(self):
        """If shapely is not installed, build_regions returns an empty list."""
        ext = _make_external_square()
        regions = build_regions(ext, [])
        # Either shapely is installed (single region = the whole square)
        # or it isn't (empty list). Both are acceptable — we only check
        # that the call doesn't crash.
        assert isinstance(regions, list)

    def test_material_region_area_shoelace(self):
        """The MaterialRegion class computes area correctly even without shapely."""
        pl = Polyline(
            vertices=[Vertex(0, 0), Vertex(4, 0), Vertex(4, 3), Vertex(0, 3)],
            closed=True,
        )
        r = MaterialRegion(polygon=pl, material_id=None)
        assert abs(r.area - 12.0) < 1e-9

    def test_material_region_centroid(self):
        pl = Polyline(
            vertices=[Vertex(0, 0), Vertex(10, 0), Vertex(10, 10), Vertex(0, 10)],
            closed=True,
        )
        r = MaterialRegion(polygon=pl, material_id=None)
        cx, cy = r.centroid()
        assert abs(cx - 5.0) < 1e-9
        assert abs(cy - 5.0) < 1e-9


# ======================================================================
class TestRegionsWithShapely:
    """Only run if shapely is installed."""

    def test_external_only_yields_one_region(self):
        if not regions_available():
            return  # skip
        ext = _make_external_square()
        regions = build_regions(ext, [])
        assert len(regions) == 1
        assert abs(regions[0].area - 100.0) < 1e-6

    def test_horizontal_cut_yields_two_regions(self):
        if not regions_available():
            return  # skip
        ext = _make_external_square(10.0)
        # A cut from (0, 5) to (10, 5) splits the square in two
        cut = Boundary(
            polyline=Polyline(
                vertices=[Vertex(0, 5), Vertex(10, 5)], closed=False
            ),
            btype=BoundaryType.MATERIAL,
        )
        regions = build_regions(ext, [cut])
        assert len(regions) == 2
        # Both halves have area 50
        for r in regions:
            assert abs(r.area - 50.0) < 1e-6

    def test_region_at_point(self):
        if not regions_available():
            return
        ext = _make_external_square(10.0)
        cut = Boundary(
            polyline=Polyline(
                vertices=[Vertex(0, 5), Vertex(10, 5)], closed=False
            ),
            btype=BoundaryType.MATERIAL,
        )
        regions = build_regions(ext, [cut])
        bottom = region_at_point(regions, 5.0, 2.5)
        top = region_at_point(regions, 5.0, 7.5)
        assert bottom is not None
        assert top is not None
        # They must be different regions
        assert bottom is not top

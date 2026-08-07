# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.17 — endpoint welding with node insertion.

Regression suite for the recurring "cannot assign different materials
per region" bug. Root cause history:
  1. A material boundary drawn with the mouse whose endpoint lands NEAR
     another boundary (but not exactly ON it) failed to cut → regions
     silently merged.
  2. The v0.1.15 extend-then-clip blindly extended such endpoints along
     their own direction, slicing through unrelated regions (phantom
     cuts → spurious extra regions).
  3. Relying on an endpoint merely "touching" a segment interior is
     fragile at the 1e-16 level: GEOS noding sometimes missed it.

Definitive fix (mirrors Slide's documented "Automatic Boundary
Intersection"): weld each near-miss endpoint onto the target —
snap-to-vertex with priority, otherwise snap-to-segment AND insert the
projection as a new vertex of the target so both lines share the node
with identical floats.
"""
from __future__ import annotations


def _screenshot_project(j):
    """Samuel's stepped-slope screenshot, with mouse jitter ``j``."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    p = Project("weld")
    ext = Polyline(vertices=[
        Vertex(15, 5), Vertex(85, 5), Vertex(85, 26), Vertex(53, 28),
        Vertex(45, 36), Vertex(36, 45), Vertex(15, 45)], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [
        Material(name=f"M{i}",
                 strength=MohrCoulomb(cohesion=10, friction_angle=20))
        for i in range(1, 6)
    ]
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(15 + j, 40.1), Vertex(45 - j, 36 + j)], closed=False),
        btype=BoundaryType.MATERIAL))
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(15 + j, 25), Vertex(28, 24), Vertex(85 - j, 22)],
        closed=False), btype=BoundaryType.MATERIAL))
    p.add_boundary(Boundary(polyline=Polyline(vertices=[
        Vertex(28 + j, 24 - j), Vertex(57, 5 + j)], closed=False),
        btype=BoundaryType.MATERIAL))
    return p


def _find(regs, pred):
    for r in regs:
        if pred(*r.centroid()):
            return r
    return None


class TestEndpointWelding:
    def test_four_regions_at_all_jitter_levels(self):
        """The screenshot geometry must yield 4 regions whether the
        endpoints are exact or drawn with realistic mouse error."""
        for j in (0.0, 0.02, 0.05, 0.08, 0.15, 0.3, 0.5):
            p = _screenshot_project(j)
            regs = p.resolve_regions()
            assert len(regs) == 4, (
                f"jitter={j}: {len(regs)} regions (expected 4)"
            )

    def test_four_distinct_materials(self):
        """Each of the 4 regions accepts its OWN material independently
        — the user-reported bug."""
        for j in (0.0, 0.08, 0.3):
            p = _screenshot_project(j)
            regs = p.resolve_regions()
            top = _find(regs, lambda x, y: y > 38)
            mid = _find(regs, lambda x, y: 26 < y < 35)
            bl = _find(regs, lambda x, y: y < 20 and x < 45)
            br = _find(regs, lambda x, y: y < 20 and x > 50)
            assert all([top, mid, bl, br]), f"jitter={j}: region ids"
            mats = p.materials
            for region, mat in [(top, mats[1]), (mid, mats[2]),
                                (bl, mats[3]), (br, mats[4])]:
                cx, cy = region.centroid()
                assert p.assign_material_at(cx, cy, mat.id)
            regs2 = p.resolve_regions()
            expected = {
                (lambda x, y: y > 38): mats[1].id,
                (lambda x, y: 26 < y < 35): mats[2].id,
                (lambda x, y: y < 20 and x < 45): mats[3].id,
                (lambda x, y: y < 20 and x > 50): mats[4].id,
            }
            for pred, mid_exp in expected.items():
                r = _find(regs2, pred)
                assert r is not None
                assert r.material_id == mid_exp, (
                    f"jitter={j}: wrong material on a region"
                )

    def test_no_phantom_regions_from_extension(self):
        """The pre-fix extension created a phantom 5th region by
        slicing the middle band. Total area must equal the External."""
        for j in (0.15, 0.3, 0.5):
            p = _screenshot_project(j)
            regs = p.resolve_regions()
            assert len(regs) == 4, f"jitter={j}: phantom region present"
            total = sum(r.area for r in regs)
            # External area
            try:
                from shapely.geometry import Polygon
                ext_area = Polygon([
                    (15, 5), (85, 5), (85, 26), (53, 28), (45, 36),
                    (36, 45), (15, 45)]).area
            except ImportError:
                return
            assert abs(total - ext_area) < 0.5 * j + 0.2, (
                f"jitter={j}: region areas do not tile the External"
            )

    def test_imprecise_t_junction(self):
        """T-junction with sloppy endpoints on both lines → 3 regions."""
        from ogr_core.geometry import (
            Boundary, BoundaryType, Polyline, Vertex,
        )
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        p = Project("t")
        ext = Polyline(vertices=[Vertex(0, 0), Vertex(60, 0),
                                 Vertex(60, 30), Vertex(0, 30)],
                       closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext,
                                btype=BoundaryType.EXTERNAL))
        p.materials = [Material(
            name="M1",
            strength=MohrCoulomb(cohesion=10, friction_angle=20))]
        p.add_boundary(Boundary(polyline=Polyline(vertices=[
            Vertex(-0.07, 15.1), Vertex(60.06, 14.95)], closed=False),
            btype=BoundaryType.MATERIAL))
        p.add_boundary(Boundary(polyline=Polyline(vertices=[
            Vertex(30.03, 15.06), Vertex(29.95, 29.96)], closed=False),
            btype=BoundaryType.MATERIAL))
        assert len(p.resolve_regions()) == 3

    def test_genuine_dangling_still_extends(self):
        """An endpoint far (>weld_tol) from everything is a genuine
        dangling and must keep the previous extend-to-cut behaviour."""
        from ogr_core.geometry import (
            Boundary, BoundaryType, Polyline, Vertex,
        )
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        p = Project("d")
        ext = Polyline(vertices=[Vertex(0, 0), Vertex(60, 0),
                                 Vertex(60, 30), Vertex(0, 30)],
                       closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext,
                                btype=BoundaryType.EXTERNAL))
        p.materials = [Material(
            name="M1",
            strength=MohrCoulomb(cohesion=10, friction_angle=20))]
        # Ends 10 units above the bottom — clearly intentional dangling;
        # the extension makes it reach the bottom and cut.
        p.add_boundary(Boundary(polyline=Polyline(vertices=[
            Vertex(30, 30), Vertex(30, 10)], closed=False),
            btype=BoundaryType.MATERIAL))
        assert len(p.resolve_regions()) == 2

    def test_paint_then_subdivide_with_jitter(self):
        """Painted material survives a mouse-imprecise subdivision."""
        from ogr_core.geometry import (
            Boundary, BoundaryType, Polyline, Vertex,
        )
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        p = Project("ps")
        ext = Polyline(vertices=[Vertex(0, 0), Vertex(60, 0),
                                 Vertex(60, 30), Vertex(0, 30)],
                       closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext,
                                btype=BoundaryType.EXTERNAL))
        p.materials = [
            Material(name=f"M{i}",
                     strength=MohrCoulomb(cohesion=10, friction_angle=20))
            for i in range(1, 4)
        ]
        p.add_boundary(Boundary(polyline=Polyline(vertices=[
            Vertex(0, 15), Vertex(60, 15)], closed=False),
            btype=BoundaryType.MATERIAL))
        p.assign_material_at(30, 7, p.materials[2].id)
        p.add_boundary(Boundary(polyline=Polyline(vertices=[
            Vertex(30, 0.04), Vertex(30, 14.93)], closed=False),
            btype=BoundaryType.MATERIAL))
        regs = p.resolve_regions()
        assert len(regs) == 3
        bl = _find(regs, lambda x, y: y < 15 and x < 30)
        br = _find(regs, lambda x, y: y < 15 and x > 30)
        assert bl.material_id == p.materials[2].id
        assert br.material_id == p.materials[2].id


class TestBetweenBoundariesWelding:
    """v0.1.17b — a material boundary drawn BETWEEN two other material
    boundaries (no External contact) must cut, regardless of drawing
    order and even when the canvas snap placed its endpoints EXACTLY on
    the target lines (distance ~1e-17 to a segment interior — the
    fragile GEOS-noding case). Fix: node insertion runs even at d≈0."""

    @staticmethod
    def _build(order, d0, d1):
        from ogr_core.geometry import (
            Boundary, BoundaryType, Polyline, Vertex,
        )
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        p = Project("bb")
        ext = Polyline(vertices=[
            Vertex(4, 2), Vertex(92, 2), Vertex(92, 30), Vertex(48, 32),
            Vertex(40, 62), Vertex(4, 63)], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext,
                                btype=BoundaryType.EXTERNAL))
        p.materials = [Material(
            name=f"M{i}",
            strength=MohrCoulomb(cohesion=10, friction_angle=20))
            for i in range(1, 6)]
        lines = {
            "3": [Vertex(4, 30), Vertex(33, 28.5), Vertex(92, 27.5)],
            "4": [Vertex(4, 17), Vertex(92, 17.5)],
            "D": [Vertex(*d0), Vertex(*d1)],
        }
        for k in order:
            p.add_boundary(Boundary(
                polyline=Polyline(vertices=lines[k], closed=False),
                btype=BoundaryType.MATERIAL))
        return p

    def test_snap_exact_diagonal_all_orders(self):
        """Diagonal from L3's interior vertex to a point EXACTLY on
        L4's segment interior (canvas snap-to-line arithmetic)."""
        from itertools import permutations
        # exact projection onto L4 ((4,17)→(92,17.5)) at x=43.099...
        x = 43.09902185492462
        t = (x - 4.0) / (92.0 - 4.0)
        d1 = (x, 17.0 + t * 0.5)
        d0 = (33.0, 28.5)  # exactly L3's interior vertex
        for order in permutations("34D"):
            p = self._build(order, d0, d1)
            n = len(p.resolve_regions())
            assert n == 4, (
                f"order {'-'.join(order)}: {n} regions (expected 4)"
            )

    def test_jittered_diagonal_all_orders(self):
        from itertools import permutations
        d0 = (33.06, 28.43)
        d1 = (43.0, 17.31)
        for order in permutations("34D"):
            p = self._build(order, d0, d1)
            assert len(p.resolve_regions()) == 4

    def test_distinct_materials_in_split_band(self):
        """The two halves of the band split by the diagonal accept
        DIFFERENT materials — the user-reported symptom."""
        p = self._build("34D", (33.0, 28.5), (43.0, 17.2))
        regs = p.resolve_regions()
        assert len(regs) == 4
        left = next(r for r in regs
                    if 17 < r.centroid()[1] < 28 and r.centroid()[0] < 35)
        right = next(r for r in regs
                     if 17 < r.centroid()[1] < 28 and r.centroid()[0] > 45)
        p.assign_material_at(*left.centroid(), p.materials[1].id)
        p.assign_material_at(*right.centroid(), p.materials[2].id)
        regs2 = p.resolve_regions()
        left2 = next(r for r in regs2
                     if 17 < r.centroid()[1] < 28 and r.centroid()[0] < 35)
        right2 = next(r for r in regs2
                      if 17 < r.centroid()[1] < 28 and r.centroid()[0] > 45)
        assert left2.material_id == p.materials[1].id
        assert right2.material_id == p.materials[2].id
        assert left2.material_id != right2.material_id

    def test_three_way_endpoint_cluster(self):
        """Divider drawn in two strokes meeting where the diagonal also
        ends — three endpoints clustered at one junction."""
        from itertools import permutations
        from ogr_core.geometry import (
            Boundary, BoundaryType, Polyline, Vertex,
        )
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_core.project import Project
        j = 0.07
        lines = {
            "A": [Vertex(4 + j, 30), Vertex(33 - j, 28.5 + j)],
            "B": [Vertex(33 + j, 28.5 - j), Vertex(92 - j, 27.5)],
            "C": [Vertex(4 + j, 17), Vertex(43 - j, 17.2 - j)],
            "E": [Vertex(43 + j, 17.2 + j), Vertex(92 - j, 17.5)],
            "D": [Vertex(33, 28.5 + j), Vertex(43, 17.2)],
        }
        orders = list(permutations("ABCDE"))[::12]  # sample of orders
        for order in orders:
            p = Project("3w")
            ext = Polyline(vertices=[
                Vertex(4, 2), Vertex(92, 2), Vertex(92, 30),
                Vertex(48, 32), Vertex(40, 62), Vertex(4, 63)],
                closed=True)
            ext.ensure_ccw()
            p.add_boundary(Boundary(polyline=ext,
                                    btype=BoundaryType.EXTERNAL))
            p.materials = [Material(
                name="M1",
                strength=MohrCoulomb(cohesion=10, friction_angle=20))]
            for k in order:
                p.add_boundary(Boundary(
                    polyline=Polyline(vertices=lines[k], closed=False),
                    btype=BoundaryType.MATERIAL))
            n = len(p.resolve_regions())
            assert n == 4, f"order {'-'.join(order)}: {n}"

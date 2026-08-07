# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Finite-element mesh data structures (Phase 1 of the groundwater plan).

Defines the minimal, solver-agnostic mesh representation used by the
OGR FEM2D seepage engine:

    * :class:`Node`    — a mesh vertex (x, y) with a stable integer id
    * :class:`Element` — a linear triangle (T3) referencing three node
      ids, carrying the material and source region it belongs to
    * :class:`Mesh`    — the node/element container plus the queries the
      solver and the GUI need (quality statistics, boundary edges,
      point location, serialisation)

Only T3 elements are produced for now. T3 is sufficient for
groundwater flow: the primary unknown is total head H, and a linear
interpolation of H over a triangle gives a constant flux per element,
which is the classical formulation for seepage (Bathe & Khoshgoftaar,
1979). T6 can be added later by mid-side node insertion without
changing this container.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterator, Optional


@dataclass(frozen=True)
class Node:
    """A mesh vertex."""

    id: int
    x: float
    y: float

    def distance_to(self, other: "Node") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


@dataclass
class Element:
    """A linear triangular element (T3), nodes in CCW order."""

    id: int
    nodes: tuple[int, int, int]
    material_id: Optional[str] = None
    region_index: Optional[int] = None

    # ------------------------------------------------------------------
    def coords(self, mesh: "Mesh") -> list[tuple[float, float]]:
        return [(mesh.nodes[i].x, mesh.nodes[i].y) for i in self.nodes]

    def area(self, mesh: "Mesh") -> float:
        (x1, y1), (x2, y2), (x3, y3) = self.coords(mesh)
        return 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))

    def centroid(self, mesh: "Mesh") -> tuple[float, float]:
        pts = self.coords(mesh)
        return (sum(p[0] for p in pts) / 3.0, sum(p[1] for p in pts) / 3.0)

    def angles_deg(self, mesh: "Mesh") -> list[float]:
        """The three interior angles, in degrees."""
        p = self.coords(mesh)
        out = []
        for i in range(3):
            a = p[i]
            b = p[(i + 1) % 3]
            c = p[(i + 2) % 3]
            v1 = (b[0] - a[0], b[1] - a[1])
            v2 = (c[0] - a[0], c[1] - a[1])
            n1 = math.hypot(*v1)
            n2 = math.hypot(*v2)
            if n1 < 1e-15 or n2 < 1e-15:
                out.append(0.0)
                continue
            cosang = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
            out.append(math.degrees(math.acos(max(-1.0, min(1.0, cosang)))))
        return out

    def min_angle_deg(self, mesh: "Mesh") -> float:
        return min(self.angles_deg(mesh))

    def shape_gradients(self, mesh: "Mesh"):
        """(dN/dx, dN/dy, area) for the three linear shape functions.

        For a T3 the gradients are constant over the element, which is
        what the seepage stiffness matrix assembly needs (Phase 2).
        """
        (x1, y1), (x2, y2), (x3, y3) = self.coords(mesh)
        det = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        if abs(det) < 1e-15:
            return None
        area = 0.5 * abs(det)
        dNdx = [(y2 - y3) / det, (y3 - y1) / det, (y1 - y2) / det]
        dNdy = [(x3 - x2) / det, (x1 - x3) / det, (x2 - x1) / det]
        return dNdx, dNdy, area

    def contains(self, mesh: "Mesh", x: float, y: float,
                 tol: float = 1e-9) -> bool:
        """Barycentric point-in-triangle test (inclusive of edges)."""
        bc = self.barycentric(mesh, x, y)
        if bc is None:
            return False
        return all(w >= -tol for w in bc)

    def barycentric(self, mesh: "Mesh", x: float, y: float):
        """Barycentric coordinates of (x, y), or None if degenerate."""
        (x1, y1), (x2, y2), (x3, y3) = self.coords(mesh)
        det = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        if abs(det) < 1e-15:
            return None
        l1 = ((x2 - x) * (y3 - y) - (x3 - x) * (y2 - y)) / det
        l2 = ((x3 - x) * (y1 - y) - (x1 - x) * (y3 - y)) / det
        return (l1, l2, 1.0 - l1 - l2)


@dataclass
class Mesh:
    """A 2D finite-element mesh of linear triangles."""

    nodes: list[Node] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)
    # Diagnostics filled in by the generator
    target_size: float = 0.0
    notes: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.elements)

    def __iter__(self) -> Iterator[Element]:
        return iter(self.elements)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def element_count(self) -> int:
        return len(self.elements)

    def total_area(self) -> float:
        return sum(e.area(self) for e in self.elements)

    # ------------------------------------------------------------------
    def quality_stats(self) -> dict:
        """Mesh quality summary. ``min_angle`` is the usual single-number
        indicator: a Delaunay mesh refined to a 25-30 deg floor is
        considered good for FE analysis."""
        if not self.elements:
            return {"elements": 0, "nodes": len(self.nodes)}
        angles = [e.min_angle_deg(self) for e in self.elements]
        areas = [e.area(self) for e in self.elements]
        angles_sorted = sorted(angles)
        n = len(angles_sorted)
        return {
            "elements": len(self.elements),
            "nodes": len(self.nodes),
            "min_angle": angles_sorted[0],
            "mean_min_angle": sum(angles) / n,
            "median_min_angle": angles_sorted[n // 2],
            "pct_below_20deg": 100.0 * sum(
                1 for a in angles if a < 20.0) / n,
            "pct_below_30deg": 100.0 * sum(
                1 for a in angles if a < 30.0) / n,
            "min_area": min(areas),
            "max_area": max(areas),
            "total_area": sum(areas),
        }

    # ------------------------------------------------------------------
    def edge_map(self) -> dict[tuple[int, int], list[int]]:
        """Map each undirected edge (sorted node ids) to the element ids
        sharing it."""
        out: dict[tuple[int, int], list[int]] = {}
        for e in self.elements:
            a, b, c = e.nodes
            for u, v in ((a, b), (b, c), (c, a)):
                key = (u, v) if u < v else (v, u)
                out.setdefault(key, []).append(e.id)
        return out

    def boundary_edges(self) -> list[tuple[int, int]]:
        """Edges belonging to exactly one element — the mesh boundary.
        These are where the seepage boundary conditions get applied
        (Phase 2/3)."""
        return [k for k, v in self.edge_map().items() if len(v) == 1]

    def boundary_node_ids(self) -> set[int]:
        ids: set[int] = set()
        for u, v in self.boundary_edges():
            ids.add(u)
            ids.add(v)
        return ids

    def is_conforming(self) -> bool:
        """True when no edge is shared by more than two elements (a
        basic conformity check: hanging nodes would show up as edges
        with 3+ owners or as boundary edges in the interior)."""
        return all(len(v) <= 2 for v in self.edge_map().values())

    # ------------------------------------------------------------------
    def locate(self, x: float, y: float) -> Optional[Element]:
        """Element containing (x, y), or None. Linear scan; adequate for
        the model sizes involved and used by the Phase-4 LEM coupling to
        interpolate pore pressure at slice base midpoints."""
        for e in self.elements:
            if e.contains(self, x, y):
                return e
        return None

    def interpolate(self, values: list[float], x: float,
                    y: float) -> Optional[float]:
        """Interpolate a nodal field at (x, y) with the T3 shape
        functions. ``values`` is indexed by node id."""
        e = self.locate(x, y)
        if e is None:
            return None
        bc = e.barycentric(self, x, y)
        if bc is None:
            return None
        return sum(w * values[nid] for w, nid in zip(bc, e.nodes))

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "nodes": [[n.id, n.x, n.y] for n in self.nodes],
            "elements": [
                [e.id, list(e.nodes), e.material_id, e.region_index]
                for e in self.elements
            ],
            "target_size": self.target_size,
            "notes": dict(self.notes),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Mesh":
        m = cls(target_size=float(d.get("target_size", 0.0)),
                notes=dict(d.get("notes", {})))
        m.nodes = [Node(int(i), float(x), float(y))
                   for i, x, y in d.get("nodes", [])]
        m.elements = [
            Element(int(eid), (int(nn[0]), int(nn[1]), int(nn[2])),
                    mat, rgn)
            for eid, nn, mat, rgn in d.get("elements", [])
        ]
        return m

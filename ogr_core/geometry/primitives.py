# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Geometric primitives for OGR Suite.

This module contains framework-agnostic geometric classes. No Qt, no
rendering code here — only math and topology. This is what makes the
core reusable from CLI, tests, and future 3D modules.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Vertex:
    """Immutable 2D point with optional unique id.

    Using a frozen dataclass gives us hashability (needed for spatial
    indices) and prevents accidental coordinate mutation downstream.
    """

    x: float
    y: float

    def distance_to(self, other: "Vertex") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    def __add__(self, other: "Vertex") -> "Vertex":
        return Vertex(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vertex") -> "Vertex":
        return Vertex(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vertex":
        return Vertex(self.x * scalar, self.y * scalar)


@dataclass
class Polyline:
    """Ordered sequence of vertices. May or may not be closed.

    Represents the geometric backbone of every boundary type (external,
    material, water table, piezometric line, tension crack).
    """

    vertices: list[Vertex] = field(default_factory=list)
    closed: bool = False
    id: str = field(default_factory=lambda: str(uuid4()))

    # ---------- basic queries ----------
    def __len__(self) -> int:
        return len(self.vertices)

    def __iter__(self):
        return iter(self.vertices)

    def is_empty(self) -> bool:
        return len(self.vertices) == 0

    # ---------- geometry ----------
    def length(self) -> float:
        if len(self.vertices) < 2:
            return 0.0
        total = 0.0
        for a, b in zip(self.vertices[:-1], self.vertices[1:]):
            total += a.distance_to(b)
        if self.closed and len(self.vertices) >= 3:
            total += self.vertices[-1].distance_to(self.vertices[0])
        return total

    def bounding_box(self) -> tuple[float, float, float, float]:
        """Return (xmin, ymin, xmax, ymax)."""
        if not self.vertices:
            return (0.0, 0.0, 0.0, 0.0)
        xs = [v.x for v in self.vertices]
        ys = [v.y for v in self.vertices]
        return (min(xs), min(ys), max(xs), max(ys))

    def signed_area(self) -> float:
        """Shoelace formula. Positive = CCW, negative = CW."""
        if len(self.vertices) < 3:
            return 0.0
        s = 0.0
        n = len(self.vertices)
        for i in range(n):
            j = (i + 1) % n
            s += self.vertices[i].x * self.vertices[j].y
            s -= self.vertices[j].x * self.vertices[i].y
        return s / 2.0

    def area(self) -> float:
        return abs(self.signed_area())

    def ensure_ccw(self) -> None:
        """Reverse in place if currently CW. Required for robust FEM meshing."""
        if self.signed_area() < 0:
            self.vertices.reverse()

    # ---------- mutation ----------
    def add_vertex(self, v: Vertex) -> None:
        self.vertices.append(v)

    def insert_vertex(self, index: int, v: Vertex) -> None:
        self.vertices.insert(index, v)

    def remove_vertex(self, index: int) -> None:
        if 0 <= index < len(self.vertices):
            del self.vertices[index]

    # ---------- serialization ----------
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "closed": self.closed,
            "vertices": [[v.x, v.y] for v in self.vertices],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Polyline":
        poly = cls(
            vertices=[Vertex(x, y) for x, y in data["vertices"]],
            closed=data.get("closed", False),
        )
        if "id" in data:
            poly.id = data["id"]
        return poly


def segments_of(polyline: Polyline) -> Iterable[tuple[Vertex, Vertex]]:
    """Yield consecutive vertex pairs (including closing segment if closed)."""
    verts = polyline.vertices
    n = len(verts)
    for i in range(n - 1):
        yield verts[i], verts[i + 1]
    if polyline.closed and n >= 3:
        yield verts[-1], verts[0]

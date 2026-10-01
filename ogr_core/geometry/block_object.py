# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Block Search objects: which kind each one is, and what the kind means.

v0.1.232 (D109). The reference defines four kinds of Block Search object,
and they differ in how many slip-surface vertices they give every trial
surface and in whether the surface follows them:

* **Window** — an arbitrary four-sided window; one vertex is generated at
  random inside it for every trial surface. OGR accepts any closed polygon
  of three or more vertices, which contains the quadrilateral.
* **Line** — one segment given by two points; one vertex at a random place
  along it. The surfaces do NOT follow the line: they only have a vertex
  somewhere on it.
* **Point** — one fixed vertex that every trial surface passes through; no
  random number is drawn for it.
* **Polyline** — one or more segments; TWO points are generated along it
  and the surface is constrained to follow the polyline BETWEEN them. How
  each point is generated is chosen separately for the left and the right
  one: anywhere along the polyline, anywhere on its end segment on that
  side, or fixed at its end vertex on that side. A one-segment Polyline is
  NOT a Line: the Line gives one vertex, the Polyline two and the stretch
  between them.

Until v0.1.232 OGR stored no kind. It was re-inferred from the vertex count
for every trial surface and every kind gave ONE point, so the Polyline did
not exist: a surface could touch a weak layer at one point and never run
along it, which made the flat of 80.4 m that verification problem 75
publishes on the top of its till unreachable by construction. The kind is
now stored on the object. A file written before carries none and is read
with :func:`infer_block_kind`, whose answers are the kinds those files
always behaved as — except an OPEN object of more than two vertices, which
used to give one point somewhere along its length and is now the Polyline
it is. That case is the defect itself, and no model of the verification
bank has one.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BlockObjectKind(Enum):
    """The four Block Search objects of the reference."""

    WINDOW = "window"
    LINE = "line"
    POINT = "point"
    POLYLINE = "polyline"


class PolylinePointMode(Enum):
    """How one of the two points of a Block Search Polyline is generated.

    Read separately for the left point and for the right one, as the
    reference offers them.
    """

    ANY = "any"
    """Anywhere along the whole polyline — the reference's default
    («Any Line Segment»)."""

    SEGMENT = "segment"
    """Anywhere on the polyline's end segment on that side («Left / Right
    Line Segment»). It assumes at least two segments; OGR refuses it on a
    one-segment polyline rather than let it mean «any»."""

    END_POINT = "end_point"
    """Fixed at the polyline's end vertex on that side, for every trial
    surface («Left / Right End Point»)."""


@dataclass
class BlockObjectSpec:
    """What a Block Search object is, as stored on its boundary.

    ``left_point`` and ``right_point`` are read only for a Polyline, and
    only a Polyline writes them.
    """

    kind: BlockObjectKind
    left_point: PolylinePointMode = PolylinePointMode.ANY
    right_point: PolylinePointMode = PolylinePointMode.ANY

    def to_dict(self) -> dict:
        out = {"kind": self.kind.value}
        if self.kind is BlockObjectKind.POLYLINE:
            out["left_point"] = self.left_point.value
            out["right_point"] = self.right_point.value
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "BlockObjectSpec":
        return cls(
            kind=BlockObjectKind(data["kind"]),
            left_point=PolylinePointMode(data.get("left_point", "any")),
            right_point=PolylinePointMode(data.get("right_point", "any")),
        )


def infer_block_kind(polyline) -> Optional[BlockObjectKind]:
    """The kind of an object that stores none: one saved before v0.1.232.

    The answers are the ones the search gave such an object then, so its
    surfaces do not change — one vertex is a Point, a closed polygon of
    three or more a Window, two vertices a Line (open or closed: a closed
    two-vertex ring was sampled along its segment) — with the single
    exception the module docstring gives: an open object of more than two
    vertices is a Polyline.
    """
    n = len(polyline.vertices)
    if n == 0:
        return None
    if n == 1:
        return BlockObjectKind.POINT
    if getattr(polyline, "closed", False) and n >= 3:
        return BlockObjectKind.WINDOW
    if n == 2:
        return BlockObjectKind.LINE
    return BlockObjectKind.POLYLINE


def block_spec_of(boundary) -> Optional[BlockObjectSpec]:
    """The spec a Block Search object is searched with.

    The stored one, or — for an object that stores none — the inferred
    kind with both Polyline points left at «any», which is the reference's
    default. None only for an object without vertices.
    """
    spec = getattr(boundary, "block_object", None)
    if spec is not None:
        return spec
    kind = infer_block_kind(boundary.polyline)
    return None if kind is None else BlockObjectSpec(kind=kind)


def left_to_right(vertices) -> list:
    """The vertices of an open object from its left end to its right end.

    The end with the smaller x is the left one; for a Polyline that
    advances in x — which :func:`ogr_core.project.rules.block_object_refusal`
    requires — that is the same as walking it from its leftmost vertex.
    """
    verts = list(vertices)
    if len(verts) >= 2 and verts[-1].x < verts[0].x:
        verts.reverse()
    return verts

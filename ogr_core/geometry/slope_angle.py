# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Change the overall angle of a slope face — and ONLY of the face.

v0.1.198. The function this replaces (``transforms.change_slope_angle``)
rotated the WHOLE External boundary about a typed pivot, and the sense of
the rotation depended on which way the slope faced: on the demo slope,
asking for 30° left the face at 60° and the base, the crest and everything
else tilted by 15°. Its "slope face" was a guess — the steepest edge.

What a user means by it, and what the interface asks for now:

* the face is the stretch of the External between two VERTICES the user
  picks — the toe and the crest — along the ground surface (never through
  the base);
* the overall angle is the angle of the chord toe → crest, and it changes
  by the amount asked (or to the angle asked), steeper or flatter, the same
  whichever way the slope faces;
* only the vertices of the face move, in one of three ways:

  - ``horizontal`` (the default): every vertex keeps its elevation. The
    crest goes to where the new chord reaches its elevation,
    ``x_c' = x_t + s·H / tan β'``;
  - ``vertical``: every vertex keeps its abscissa, and the crest goes to
    ``y_c' = y_t + |x_c − x_t|·tan β'``;
  - ``rotate``: the face turns rigidly about the toe;

* with ``keep_benches`` (the default for the two projections) each
  intermediate vertex moves in proportion to where it sits between toe and
  crest — by its height for the horizontal projection, by its abscissa for
  the vertical one — so two vertices at one elevation move together and a
  bench keeps its width. Without it each vertex is carried by its OWN ray
  from the toe, turned by the chord's rotation and projected back to its
  elevation (or abscissa), and the benches change width. This reading of
  the two options is ours: the documentation the interface follows names
  them and their purpose, not their formulas;
* a vertex of another boundary lying ON a stretch of the face moves with
  it, at the same fraction of that stretch, so a layer that reaches the
  face still reaches it;
* supports and loads do not move — they are placed on purpose, and the
  documentation this follows does not move them either; the answer names
  those that were on the face.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import dataclasses
import math
from typing import Optional, Sequence

from .primitives import Vertex

MODES = ("horizontal", "vertical", "rotate")


def _diag(vertices) -> float:
    xs = [v.x for v in vertices]
    ys = [v.y for v in vertices]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys)) or 1.0


def vertex_index(external, ref, rel_tol: float = 1e-5) -> int:
    """The index of an External vertex given as an index or as (x, y).

    A point must BE a vertex, within ``rel_tol`` of the model's diagonal
    (a coordinate read back from a rounded summary still names it).
    """
    verts = external.polyline.vertices
    if isinstance(ref, bool):
        raise ValueError("A vertex is an index or an [x, y] point.")
    if isinstance(ref, int):
        if not 0 <= ref < len(verts):
            raise ValueError(f"Vertex index {ref} is outside "
                             f"0..{len(verts) - 1}.")
        return ref
    try:
        x, y = float(ref[0]), float(ref[1])
    except (TypeError, ValueError, IndexError):
        raise ValueError("A vertex is an index or an [x, y] point.") \
            from None
    tol = rel_tol * _diag(verts)
    best = min(range(len(verts)),
               key=lambda i: math.hypot(verts[i].x - x, verts[i].y - y))
    if math.hypot(verts[best].x - x, verts[best].y - y) > tol:
        raise ValueError(f"({x:g}, {y:g}) is not a vertex of the External "
                         f"boundary.")
    return best


def slope_face(external, toe: int, crest: int) -> list[int]:
    """The ring indices from the toe to the crest along the ground surface.

    Of the two ways round the ring between them, the one whose vertices are
    all on the ground surface (``ground.ground_surface``); the other one
    goes through the base. Raises ``ValueError`` when the toe is not below
    the crest or neither way is ground.
    """
    from .ground import distance_to_profile, ground_surface

    verts = external.polyline.vertices
    n = len(verts)
    if toe == crest:
        raise ValueError("The toe and the crest are the same vertex.")
    if not verts[toe].y < verts[crest].y:
        raise ValueError("The toe must be lower than the crest.")
    profile = ground_surface(external)
    tol = 1e-6 * _diag(verts)

    def walk(step):
        path, i = [toe], toe
        while i != crest:
            i = (i + step) % n
            path.append(i)
        return path

    def on_ground(path):
        return all(distance_to_profile(profile, verts[i].x, verts[i].y)
                   <= tol for i in path)

    candidates = [p for p in (walk(1), walk(-1)) if on_ground(p)]
    if not candidates:
        raise ValueError("The toe and the crest are not joined by the "
                         "ground surface.")
    return min(candidates, key=len)


def overall_angle(external, toe: int, crest: int) -> float:
    """The angle of the chord toe → crest from the horizontal, degrees."""
    a = external.polyline.vertices[toe]
    b = external.polyline.vertices[crest]
    return math.degrees(math.atan2(b.y - a.y, abs(b.x - a.x)))


def _facing(verts, face) -> float:
    """+1 when the crest is to the right of the toe, −1 to the left. A
    vertical face takes it from the side its crest's plateau is on."""
    t, c = verts[face[0]], verts[face[-1]]
    dx = c.x - t.x
    if abs(dx) > 1e-12 * _diag(verts):
        return 1.0 if dx > 0 else -1.0
    n = len(verts)
    step = 1 if face[1] == (face[0] + 1) % n else -1
    beyond = verts[(face[-1] + step) % n]
    return 1.0 if beyond.x > c.x else -1.0


def _rotate(p, pivot, delta):
    c, s = math.cos(delta), math.sin(delta)
    dx, dy = p.x - pivot.x, p.y - pivot.y
    return Vertex(pivot.x + dx * c - dy * s, pivot.y + dx * s + dy * c)


def new_face(verts: Sequence[Vertex], face: list[int], new_angle_deg: float,
             mode: str = "horizontal",
             keep_benches: bool = True) -> list[Vertex]:
    """The face vertices (toe first, crest last) at ``new_angle_deg``.

    Pure geometry: the formulas of the module docstring.
    """
    if mode not in MODES:
        raise ValueError(f"mode is one of {MODES}.")
    if not 0.0 < new_angle_deg < 90.0:
        raise ValueError("The new overall angle must be between 0° and "
                         "90°.")
    toe, crest = verts[face[0]], verts[face[-1]]
    s = _facing(verts, face)
    H = crest.y - toe.y
    beta = math.radians(new_angle_deg)
    old = [verts[i] for i in face]
    theta_old = math.atan2(H, crest.x - toe.x)

    if mode == "rotate":
        theta_new = beta if s > 0 else math.pi - beta
        delta = theta_new - theta_old
        return [toe] + [_rotate(v, toe, delta) for v in old[1:]]

    if mode == "horizontal":
        xc_new = toe.x + s * H / math.tan(beta)
        if keep_benches:
            dxc = xc_new - crest.x
            return [toe] + [Vertex(v.x + dxc * (v.y - toe.y) / H, v.y)
                            for v in old[1:]]
        delta = math.atan2(H, xc_new - toe.x) - theta_old
        out = [toe]
        for v in old[1:]:
            r = _rotate(v, toe, delta)
            if abs(r.y - toe.y) < 1e-12 * _diag(verts):
                raise ValueError("A face vertex at the toe's elevation "
                                 "cannot be projected horizontally.")
            out.append(Vertex(toe.x + (r.x - toe.x) * (v.y - toe.y)
                              / (r.y - toe.y), v.y))
        return out

    # vertical
    run = crest.x - toe.x
    if abs(run) < 1e-12 * _diag(verts):
        raise ValueError("A vertical face cannot be projected vertically.")
    yc_new = toe.y + abs(run) * math.tan(beta)
    if keep_benches:
        dyc = yc_new - crest.y
        return [toe] + [Vertex(v.x, v.y + dyc * (v.x - toe.x) / run)
                        for v in old[1:]]
    delta = math.atan2(yc_new - toe.y, run) - theta_old
    out = [toe]
    for v in old[1:]:
        r = _rotate(v, toe, delta)
        if abs(r.x - toe.x) < 1e-12 * _diag(verts):
            raise ValueError("A face vertex above the toe cannot be "
                             "projected vertically.")
        out.append(Vertex(v.x, toe.y + (r.y - toe.y) * (v.x - toe.x)
                          / (r.x - toe.x)))
    return out


def _on_segment(p, a, b, tol):
    """The fraction t of ``p`` along a→b, or None when it is not on it."""
    dx, dy = b.x - a.x, b.y - a.y
    span = dx * dx + dy * dy
    if span <= 0.0:
        return 0.0 if math.hypot(p.x - a.x, p.y - a.y) <= tol else None
    t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / span
    if t < -1e-12 or t > 1 + 1e-12:
        return None
    t = min(1.0, max(0.0, t))
    if math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy)) > tol:
        return None
    return t


def change_slope_angle(project, toe, crest, *,
                       change_deg: Optional[float] = None,
                       target_deg: Optional[float] = None,
                       mode: str = "horizontal",
                       keep_benches: Optional[bool] = None) -> dict:
    """Change the overall angle of the slope face between ``toe`` and
    ``crest`` (External vertices: indices or (x, y)), IN ``project``.

    Give ``change_deg`` (positive steepens, negative flattens) or
    ``target_deg``. ``keep_benches`` is only read by the two projections
    (default True); passing it with ``mode='rotate'`` is an error, because
    that mode would not read it. Raises ``ValueError`` with the reason, and
    then nothing has changed. The caller owns the undo step.
    """
    from shapely.geometry import Polygon

    ext = project.external_boundary()
    if ext is None:
        raise ValueError("The model has no External boundary.")
    if mode not in MODES:
        raise ValueError(f"mode is one of {MODES}.")
    if keep_benches is not None and mode == "rotate":
        raise ValueError("keep_benches is only read by the horizontal and "
                         "vertical projections, not by 'rotate'.")
    if (change_deg is None) == (target_deg is None):
        raise ValueError("Give exactly one of change_deg or target_deg.")
    keep = True if keep_benches is None else bool(keep_benches)

    verts = list(ext.polyline.vertices)
    ti = vertex_index(ext, toe)
    ci = vertex_index(ext, crest)
    face = slope_face(ext, ti, ci)
    old_angle = overall_angle(ext, ti, ci)
    new_angle = (old_angle + float(change_deg) if change_deg is not None
                 else float(target_deg))
    moved = new_face(verts, face, new_angle, mode, keep)

    new_verts = list(verts)
    for i, v in zip(face, moved):
        new_verts[i] = v
    poly = Polygon([(v.x, v.y) for v in new_verts])
    if not poly.is_valid or poly.area <= 0.0:
        raise ValueError("At that angle the face runs into the rest of the "
                         "External boundary (past the next vertex of the "
                         "crest or the toe).")

    tol = 1e-6 * _diag(verts)
    segments = list(zip(face[:-1], face[1:]))
    new_of = dict(zip(face, moved))

    def carried(p):
        for a, b in segments:
            t = _on_segment(p, verts[a], verts[b], tol)
            if t is not None:
                na, nb = new_of[a], new_of[b]
                return Vertex(na.x + t * (nb.x - na.x),
                              na.y + t * (nb.y - na.y))
        return None

    notes = []
    attached = 0
    ext_idx = next(i for i, b in enumerate(project.boundaries) if b is ext)
    for idx, b in enumerate(project.boundaries):
        if idx == ext_idx:
            continue
        changed = False
        vs = list(b.polyline.vertices)
        for k, p in enumerate(vs):
            q = carried(p)
            if q is not None and (q.x != p.x or q.y != p.y):
                vs[k] = q
                changed = True
                attached += 1
        if changed:
            project.boundaries[idx] = dataclasses.replace(
                b, polyline=dataclasses.replace(b.polyline, vertices=vs))

    on_face = []
    for s in getattr(project, "supports", []) or []:
        if carried(s.head) is not None:
            on_face.append(s.name or s.id)
    if on_face:
        notes.append(f"{len(on_face)} support(s) had their head on the "
                     f"old face and were not moved: "
                     f"{', '.join(on_face[:10])}.")
    loads = []
    for ld in getattr(project, "distributed_loads", []) or []:
        if carried(ld.start) is not None or carried(ld.end) is not None:
            loads.append(ld.name or ld.id)
    for ld in getattr(project, "line_loads", []) or []:
        if carried(ld.point) is not None:
            loads.append(ld.name or ld.id)
    if loads:
        notes.append(f"{len(loads)} load(s) were on the old face and were "
                     f"not moved: {', '.join(loads[:10])}.")

    project.boundaries[ext_idx] = dataclasses.replace(
        ext, polyline=dataclasses.replace(ext.polyline,
                                          vertices=new_verts))
    project.invalidate_regions_cache()
    project._notify("boundary_modified")
    return {"old_angle_deg": old_angle, "new_angle_deg": new_angle,
            "toe": ti, "crest": ci, "face": face,
            "moved_vertices": len(face) - 1, "attached_moved": attached,
            "mode": mode, "keep_benches": keep if mode != "rotate" else None,
            "notes": notes}

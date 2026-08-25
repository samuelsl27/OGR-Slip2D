# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Weak layers: which of them a trial surface has to be clipped against.

A weak layer is a polyline carrying a strength of its own — a joint between
two gabion courses, a geomembrane interface, a bedding plane. It is NOT model
geometry: it is never intersected with the other boundaries and it never
defines a material region. Its one job is to be a plane of weakness the slip
surface travels ALONG instead of crossing, which is what a thin band of
material cannot do: a band has thickness, and a surface can cut it diagonally.

This module answers the model-level question — *which* layers apply to a given
trial surface, and *how many* surfaces that turns one surface into. The
geometry of the clipping itself lives in
:class:`ogr_slip2d.surface.WeakLayerSurface`.

Two policies, both deterministic
--------------------------------
``"highest"``
    Every layer the surface touches clips it, and where two overlap the higher
    wins. One evaluation per surface. The right choice when only the topmost
    joint is of concern, and the cheap one.

``"auto_cases"``
    Every combination of the touched layers being on or off is evaluated and
    the worst is kept — the all-off case included, because a surface shearing
    THROUGH the blocks instead of along a joint is a mechanism too. Rigorous,
    and 2**n evaluations of a single surface.

Why "touched" is decided one layer at a time
--------------------------------------------
A layer is touched when, **on its own**, it would clip the surface. Deciding
it with every layer active instead would be cheaper by a factor of n and
wrong: two parallel joints one metre apart both cross the same surface, but
with both active only the upper one ever wins, so the lower one would never
appear in the set — and under ``auto_cases`` the case that matters most, the
surface running along the LOWER joint with the upper one off, would never be
generated. The rigorous policy would then be quietly less rigorous than the
cheap one.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Iterator, Optional

from ogr_core.geometry import BoundaryType
from ogr_core.project.settings import WeakLayerHandling

from .surface import WeakLayerBand, WeakLayerSurface

__all__ = [
    "weak_layer_bands",
    "weak_layer_variants",
    "touching_bands",
    "weak_layer_model_warnings",
]


def weak_layer_bands(project) -> tuple:
    """The weak layers of ``project`` that take part in an analysis.

    A layer with fewer than two vertices is not a line and is skipped; a
    suppressed one is skipped by the user's own decision. Note that
    ``visible`` is NOT consulted: hiding a boundary is a drawing choice, and
    a model whose factor of safety changed when something was hidden would be
    the worst kind of surprise.
    """
    bands = []
    for b in project.boundaries:
        if b.btype is not BoundaryType.WEAK_LAYER:
            continue
        if getattr(b, "suppressed", False):
            continue
        vs = getattr(getattr(b, "polyline", None), "vertices", ())
        if len(vs) < 2:
            continue
        bands.append(WeakLayerBand(polyline=b.polyline,
                                   material_id=b.material_id,
                                   boundary_id=b.id))
    return tuple(bands)


def _may_reach(surface, band) -> bool:
    """Cheap bounding-box rejection before the exact test.

    Pure comparisons against the surface's own span, so a joint drawn at the
    other end of the model costs four floats instead of a root solve. The
    exact question is answered by :func:`touching_bands`.
    """
    x_l, x_r = surface.x_range()
    if x_l is None or x_r is None:
        return False
    bx0, bx1 = band.x_range()
    if bx1 < x_l or bx0 > x_r:
        return False
    span = surface.y_span(x_l, x_r)
    if span is None:
        return True
    ys = [v.y for v in band.polyline.vertices]
    # A layer entirely BELOW the deepest point of the surface can never lift
    # it. One entirely above can, in principle, so it is not rejected here —
    # a layer above the ground is a modelling error, and it is reported as
    # one rather than silently dropped.
    return max(ys) >= span[0]


def touching_bands(surface, bands) -> tuple:
    """The layers that clip ``surface`` when each is considered ALONE.

    One at a time, and the module docstring says why: with every layer active
    a lower joint hides behind a higher one and would never be offered to
    ``auto_cases`` as a case of its own.
    """
    out = []
    for band in bands:
        if not _may_reach(surface, band):
            continue
        if WeakLayerSurface(base=surface, bands=(band,)).clips_the_base():
            out.append(band)
    return tuple(out)


def weak_layer_variants(
    surface,
    bands,
    handling: str = WeakLayerHandling.HIGHEST.value,
    max_cases_log2: int = 6,
    note_cb=None,
) -> Iterator:
    """The surfaces to evaluate in place of ``surface``.

    Yields ``surface`` itself, unchanged and untouched, whenever no layer
    reaches it. That is not an optimisation but the invariant that keeps every
    model without weak layers answering bit for bit as it did before: the
    object handed to the slicer is the same object, not a wrapper around it.

    ``note_cb`` receives one line of explanation whenever a case set is cut
    short. A silently truncated set reads exactly like full coverage, which is
    the failure mode this project has paid for before.
    """
    if not bands:
        yield surface
        return
    touching = touching_bands(surface, bands)
    if not touching:
        yield surface
        return

    if handling == WeakLayerHandling.AUTO_CASES.value:
        n = len(touching)
        if n > max(0, int(max_cases_log2)):
            if note_cb is not None:
                note_cb(
                    f"A trial surface is cut by {n} weak layers, more than the "
                    f"{max_cases_log2} that automatic case generation is "
                    f"allowed to combine; that surface was analysed by "
                    f"snapping to the highest layer instead. Raise the limit "
                    f"or merge layers that lie close together."
                )
            yield WeakLayerSurface(base=surface, bands=touching)
            return
        # Ascending bitmask order: deterministic, and case 0 — every layer
        # off — is the unclipped surface, which the reference counts as one
        # of the combinations and which is a real mechanism: shearing
        # THROUGH the blocks rather than along a joint.
        for mask in range(1 << n):
            if mask == 0:
                yield surface
                continue
            subset = tuple(b for i, b in enumerate(touching) if mask >> i & 1)
            yield WeakLayerSurface(base=surface, bands=subset)
        return

    yield WeakLayerSurface(base=surface, bands=touching)


def weak_layer_model_warnings(project) -> list[str]:
    """Things about the weak layers of a model that are worth saying once.

    Asked at the start of an analysis rather than per surface: these are facts
    about the model, they cannot change while it is being analysed, and a
    per-surface warning would arrive thousands of times.
    """
    out: list[str] = []
    bands = weak_layer_bands(project)
    if not bands:
        return out

    ext = project.external_boundary()
    ground = None
    if ext is not None:
        from ogr_core.geometry.ground import ground_surface
        ground = ground_surface(ext)

    for band in bands:
        name = band.boundary_id[:8] if band.boundary_id else "?"
        mat = (project.material_by_id(band.material_id)
               if band.material_id else None)
        if mat is None:
            out.append(
                f"Weak layer {name} has no material assigned, so it carries "
                f"no strength of its own and would only change the geometry "
                f"of the surfaces it clips. Assign it a material or suppress "
                f"it."
            )
        if ground is None:
            continue
        from ogr_core.geometry.ground import envelope_y_at
        above = 0
        total = 0
        for v in band.polyline.vertices:
            gy = envelope_y_at(ground, v.x)
            if gy is None:
                continue
            total += 1
            if v.y > gy + 1e-9:
                above += 1
        if total and above == total:
            out.append(
                f"Weak layer {name} lies entirely above the ground surface, "
                f"so any surface it clips is pushed out of the soil and "
                f"discarded. Suppress it or move it into the model."
            )
    return out

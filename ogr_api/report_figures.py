# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The figures of the PDF report: one per method (v0.1.339, D336).

The report (``ogr_core.report.report_generator``) was tables and text, with
no drawing of the model at all. By decision of the owner it carries one
figure per method: the model, that method's critical surface, the annotation
layer and, when the search had a grid of slip centres, the contours of the
minimum factor of safety at each centre with the critical centre marked —
framed on the model alone or on the model and the whole area the grid
searched, the same frame for every figure so that they compare.

They are built here, above the core, because they need the engine's reading
of a search (``ogr_slip2d.interpretation.minimum_per_centre``) and the
picture ``render.render_png`` draws; the core embeds the bytes it is given.
The window and the ``report_generate`` operation both call
:func:`method_figures`.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Optional

#: The framings of the report's figures.
FRAMINGS = ("model", "search_area")
#: The margin around a frame, as a fraction of its larger side.
MARGIN = 0.05


def grid_data(search_result) -> Optional[dict]:
    """The minimum factor of safety at each slip centre of a search, as the
    interpretation window contours it (``minimum_per_centre`` over the valid
    surfaces), with the critical surface's centre: ``{"x", "y", "fos",
    "critical"}``. None when fewer than three centres have a factor — a
    non-circular search has none."""
    from ogr_slip2d.interpretation import minimum_per_centre, slip_centre
    xs, ys, fos = [], [], []
    for r in minimum_per_centre(search_result):
        centre = slip_centre(r.surface.to_dict())
        if centre is None or r.fos is None:
            continue
        xs.append(float(centre[0]))
        ys.append(float(centre[1]))
        fos.append(float(r.fos))
    if len(xs) < 3:
        return None
    crit = getattr(search_result, "critical", None)
    critical = (slip_centre(crit.surface.to_dict())
                if crit is not None else None)
    return {"x": xs, "y": ys, "fos": fos, "critical": critical}


def has_centres(results) -> bool:
    """Whether any search in ``results`` has a grid of slip centres."""
    return any(grid_data(sr) is not None
               for sr in (results or {}).values())


def _box(points) -> Optional[tuple]:
    pts = list(points)
    if not pts:
        return None
    return (min(p[0] for p in pts), max(p[0] for p in pts),
            min(p[1] for p in pts), max(p[1] for p in pts))


def _with_margin(box) -> tuple:
    xmin, xmax, ymin, ymax = box
    pad = MARGIN * max(xmax - xmin, ymax - ymin, 1e-9)
    return (xmin - pad, xmax + pad, ymin - pad, ymax + pad)


def figure_extent(project, results, framing: str = "model") -> tuple:
    """``(xmin, xmax, ymin, ymax)`` of the report's figures: the model's box,
    or the model's and every slip centre any search evaluated, valid or not
    (the area the grid searched); with a margin."""
    if framing not in FRAMINGS:
        raise ValueError("framing must be one of %s" % ", ".join(FRAMINGS))
    xmin, ymin, xmax, ymax = project.bounding_box()
    points = [(xmin, ymin), (xmax, ymax)]
    if framing == "search_area":
        from ogr_slip2d.interpretation import slip_centre
        for sr in (results or {}).values():
            # the user's surfaces too: the contours are drawn from them
            pool = (sr.all_evaluations() if hasattr(sr, "all_evaluations")
                    else getattr(sr, "evaluations", []))
            for ev in pool or []:
                centre = slip_centre(ev.surface.to_dict())
                if centre is not None:
                    points.append(centre)
    return _with_margin(_box(points))


def method_figures(project, results, *, framing: str = "model",
                   annotations: bool = True, factored: bool = False,
                   width: int = 1400, height: int = 900) -> list:
    """``[(method id, png bytes)]``: one figure per method with a critical
    surface, all with the same frame; the report writes their captions.

    ``factored`` -- the run applied partial factors, so the number on the
    contours is an over-design factor and its scale says so."""
    from .render import render_png
    extent = figure_extent(project, results, framing)
    label = ("minimum over-design factor" if factored
             else "minimum factor of safety")
    out = []
    for mid, sr in (results or {}).items():
        crit = getattr(sr, "critical", None)
        if crit is None or crit.fos is None:
            continue
        grid = grid_data(sr)
        if grid is not None:
            grid["label"] = label
        png = render_png(project, surfaces=[("critical surface", crit)],
                         width=width, height=height, labels=True,
                         annotations=annotations, extent=extent, grid=grid)
        out.append((mid, png))
    return out

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The figures of the PDF report: one per method (v0.1.339, D336).

The report (``ogr_core.report.report_generator``) was tables and text, with
no drawing of the model at all. By decision of the owner it carries one
figure per method: the model, that method's critical surface, the annotation
layer and, when the search had a grid of slip centres, the contours at each
centre of the number the run reports (the minimum factor of safety; since
v0.1.450, D423, the minimum Ky or the maximum Newmark displacement on a
seismic run) with the critical centre marked — framed on the model alone or
on the model and the whole area the grid searched, the same frame for every
figure so that they compare.

They are built here, above the core, because they need the engine's reading
of a search (``ogr_slip2d.interpretation.critical_per_centre``) and the
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


def grid_data(search_result, project=None) -> Optional[dict]:
    """The number the run reports at each slip centre of a search, with the
    critical surface's centre. On a run of factors, the minimum factor of
    safety, as the interpretation window contours it (``minimum_per_centre``
    over the valid surfaces): ``{"x", "y", "fos", "critical"}``. None when
    fewer than three centres have a factor, or (seismic run) when the search
    evaluated fewer than three — a non-circular search has none.

    v0.1.450 (D423) — on a Ky or a Newmark run, what that run minimises:
    the lowest Ky of each centre, or its largest Newmark displacement in the
    project's unit (``displacement_in_units``), from
    ``interpretation.critical_per_centre``. The figure drew the lowest
    factor of each centre and put the star on the centre of the lowest Ky,
    so the star stood on no minimum of what it drew ((40, 45) against
    (34, 29) on the demo slope with c = 20 kPa). Those values travel as
    ``values``, never under ``fos``, with ``quantity`` («ky» or «newmark»),
    and with ``unit`` and the reversed colour map for a displacement, whose
    critical end is the largest; a run of factors gets the dictionary it
    always got."""
    from ogr_slip2d.interpretation import (critical_per_centre,
                                           minimum_per_centre,
                                           reported_value, slip_centre)
    from ogr_slip2d.reported import KY, NEWMARK, displacement_in_units, \
        reported_caption
    # asked once: it reads ``critical``, which walks every surface
    caption = reported_caption(search_result)
    seismic = caption in (KY, NEWMARK)
    xs, ys, fos = [], [], []
    for r in critical_per_centre(search_result, caption):
        centre = slip_centre(r.surface.to_dict())
        if centre is None or r.fos is None:
            continue
        value = (reported_value(search_result, r, caption) if seismic
                 else float(r.fos))
        if value is None:
            continue
        if caption == NEWMARK:
            value = displacement_in_units(project, value)[0]
        xs.append(float(centre[0]))
        ys.append(float(centre[1]))
        fos.append(float(value))
    crit = getattr(search_result, "critical", None)
    critical = (slip_centre(crit.surface.to_dict())
                if crit is not None else None)
    if not seismic:
        if len(xs) < 3:
            return None
        return {"x": xs, "y": ys, "fos": fos, "critical": critical}
    # Every centre the search evaluated, valid, with the run's number or
    # without: whether the search has a grid at all (three centres, as for
    # a run of factors) does not depend on how many of them have a Ky, and
    # the dots say where it searched. The review of 0.1.450 found a Ky run
    # with two centres of Ky losing its whole grid, star included, and the
    # report's dialog greying out «Model and search area» with a false
    # reason (``has_centres``).
    centres = []
    for r in minimum_per_centre(search_result):
        centre = slip_centre(r.surface.to_dict())
        if centre is not None:
            centres.append((float(centre[0]), float(centre[1])))
    if len(centres) < 3:
        return None
    out = {"x": xs, "y": ys, "values": fos, "critical": critical,
           "quantity": caption,
           "centres": ([c[0] for c in centres], [c[1] for c in centres])}
    # v0.1.506 -- Viridis, dark at the critical end, as Interpret draws it
    # (``ContourSettings.for_reported``): the lowest Ky, and the largest
    # displacement (reversed). The factor keeps the drawing's default.
    if caption == KY:
        out["cmap"] = "viridis"
    if caption == NEWMARK:
        out["unit"] = displacement_in_units(project, 0.0)[1]
        out["cmap"] = "viridis_r"
    return out


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
                   width: int = 1400, height: int = 900,
                   translate=None) -> list:
    """``[(method id, png bytes)]``: one figure per method with a critical
    surface, all with the same frame; the report writes their captions.

    ``factored`` -- the run applied partial factors, so the number on the
    contours is an over-design factor and its scale says so.

    ``translate`` (v0.1.355, D335) -- the words drawn on the figure (the
    scale, the legend) in the reader's language, as ``generate_report``
    takes it; without it, English."""
    from .render import render_png
    T = translate or (lambda text: text)
    extent = figure_extent(project, results, framing)
    label = (T("minimum over-design factor") if factored
             else T("minimum factor of safety"))
    out = []
    for mid, sr in (results or {}).items():
        crit = getattr(sr, "critical", None)
        if crit is None or crit.fos is None:
            continue
        grid = grid_data(sr, project)
        if grid is not None:
            # v0.1.450 (D423) — the scale names what is drawn, the run's
            # own number (``grid_data``); ``factored`` only qualifies a
            # factor, which a Ky or a displacement is not
            if grid.get("quantity") == "ky":
                grid["label"] = T("minimum Ky")
            elif grid.get("quantity") == "newmark":
                grid["label"] = "%s [%s]" % (
                    T("maximum Newmark displacement"), grid["unit"])
            else:
                grid["label"] = label
            grid["critical_label"] = T("critical centre")
        png = render_png(project, surfaces=[(T("critical surface"), crit)],
                         width=width, height=height, labels=True,
                         annotations=annotations, extent=extent, grid=grid)
        out.append((mid, png))
    return out

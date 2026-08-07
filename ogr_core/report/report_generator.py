# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
OGR Slip2D — Analysis report generator.

Produces a multi-page PDF that mirrors the structure of a professional
slope-stability analysis report:

    1. Project Summary
    2. General Settings
    3. Analysis Options (methods, tolerance, surface options)
    4. Material Properties
    5. Global Minimums (one block per analysis method)
    6. Valid / Invalid Surfaces (per method)
    7. Slice Data (global-minimum query, per method)
    8. List of Coordinates (external + material boundaries)

The report is generated from a :class:`Project` and the dict of
``{method_id: SearchResult}`` produced by a Compute run.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    )
    _HAS_REPORTLAB = True
except ImportError:  # pragma: no cover
    _HAS_REPORTLAB = False


# Method id → human-readable name (matches the reference program)
_METHOD_NAMES = {
    "ordinary_fellenius": "Ordinary / Fellenius",
    "ordinary": "Ordinary / Fellenius",
    "fellenius": "Ordinary / Fellenius",
    "bishop_simplified": "Bishop Simplified",
    "bishop": "Bishop Simplified",
    "janbu_simplified": "Janbu Simplified",
    "janbu": "Janbu Simplified",
    "janbu_corrected": "Janbu Corrected",
    "spencer": "Spencer",
    "gle_morgenstern_price": "GLE / Morgenstern-Price",
    "morgenstern_price": "GLE / Morgenstern-Price",
    "lowe_karafiath": "Lowe-Karafiath",
}


def _method_name(mid: str) -> str:
    return _METHOD_NAMES.get(mid, mid.replace("_", " ").title())


def _fmt(x, nd=3):
    if x is None:
        return "—"
    if isinstance(x, float):
        if math.isnan(x):
            return "—"
        return f"{x:.{nd}f}"
    return str(x)


def generate_report(
    project,
    results: dict,
    output_path: str,
    *,
    author: Optional[str] = None,
    company: Optional[str] = None,
    title: Optional[str] = None,
) -> str:
    """Generate a PDF analysis report.

    Parameters
    ----------
    project : Project
        The analysed project.
    results : dict[str, SearchResult]
        Mapping of method id → search result (from a Compute run).
    output_path : str
        Destination .pdf path.
    author, company, title : str, optional
        Override the project-summary fields.

    Returns
    -------
    str
        The output path.
    """
    if not _HAS_REPORTLAB:  # pragma: no cover
        raise RuntimeError(
            "reportlab is required for PDF report generation "
            "(pip install reportlab)."
        )

    summary = project.settings.summary
    author = author or summary.author or ""
    company = company or summary.company or ""
    title = title or summary.title or "OGR Slip2D — Slope Stability Analysis"

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=title, author=author or "OGR Slip2D",
    )

    styles = getSampleStyleSheet()
    h_title = ParagraphStyle(
        "OGRTitle", parent=styles["Title"], fontSize=18,
        textColor=colors.HexColor("#1a3a5c"), spaceAfter=4,
    )
    h_sub = ParagraphStyle(
        "OGRSub", parent=styles["Normal"], fontSize=11,
        textColor=colors.HexColor("#456"), alignment=1, spaceAfter=14,
    )
    h_sec = ParagraphStyle(
        "OGRSection", parent=styles["Heading2"], fontSize=13,
        textColor=colors.HexColor("#1a3a5c"), spaceBefore=12, spaceAfter=6,
        borderWidth=0, leading=16,
    )
    h_method = ParagraphStyle(
        "OGRMethod", parent=styles["Heading3"], fontSize=11,
        textColor=colors.HexColor("#2a5a8c"), spaceBefore=8, spaceAfter=3,
    )
    body = ParagraphStyle(
        "OGRBody", parent=styles["Normal"], fontSize=9, leading=12,
    )

    story = []

    def section(txt):
        story.append(Paragraph(txt, h_sec))
        story.append(_hrule())

    def _hrule():
        t = Table([[""]], colWidths=[doc.width])
        t.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 0.8,
             colors.HexColor("#1a3a5c")),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        return t

    def kv_table(rows):
        t = Table([[Paragraph(f"<b>{k}</b>", body), Paragraph(str(v), body)]
                   for k, v in rows], colWidths=[55 * mm, doc.width - 55 * mm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        return t

    # ---- Title -----------------------------------------------------
    story.append(Paragraph(title, h_title))
    story.append(Paragraph(
        "OGR Slip2D — OpenGeoRock Suite", h_sub))

    # ---- 1. Project Summary ---------------------------------------
    section("Project Summary")
    story.append(kv_table([
        ("Project Title", title),
        ("File", getattr(project, "name", "—")),
        ("Author", author or "—"),
        ("Company", company or "—"),
        ("Date Created", summary.date_created
         or datetime.now().strftime("%d/%m/%Y, %H:%M:%S")),
        ("Report Generated",
         datetime.now().strftime("%d/%m/%Y, %H:%M:%S")),
    ]))
    if summary.comments:
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Comments:</b> {summary.comments}", body))

    # ---- 2. General Settings --------------------------------------
    units = project.settings.units
    section("General Settings")
    story.append(kv_table([
        ("Units of Measurement", _unit_label(
            getattr(units, "system", None),
            {"metric": "Metric Units", "imperial": "Imperial Units"})),
        ("Time Units", _unit_label(
            getattr(units, "time", None),
            {"d": "days", "s": "seconds", "h": "hours"})),
        ("Permeability Units", _unit_label(
            getattr(units, "permeability", None),
            {"m/s": "meters/second", "cm/s": "cm/second",
             "ft/s": "feet/second"})),
        ("Failure Direction", _unit_label(
            getattr(units, "failure_direction", None),
            {"R2L": "Right to Left", "L2R": "Left to Right"})),
    ]))

    # ---- 3. Analysis Options --------------------------------------
    m = project.settings.methods
    s = project.settings.search
    section("Analysis Options")
    story.append(Paragraph("<b>Analysis Methods Used</b>", body))
    method_ids = list(results.keys()) or list(m.enabled_methods)
    for mid in method_ids:
        story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;• {_method_name(mid)}",
                               body))
    story.append(Spacer(1, 4))
    story.append(kv_table([
        ("Number of Slices", m.num_slices),
        ("Tolerance", m.tolerance),
        ("Maximum Iterations", m.max_iterations),
    ]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Surface Options</b>", body))
    story.append(kv_table([
        ("Surface Type",
         "Circular" if s.surface_type in ("circular", "Circular")
         else str(s.surface_type).title()),
        ("Search Method",
         _search_method_name(s.search_method)),
        ("Radius Increment", s.radius_increment),
        ("Composite Surfaces",
         "Enabled" if getattr(s, "composite_surfaces", False)
         else "Disabled"),
    ]))

    # ---- 4. Material Properties -----------------------------------
    section("Material Properties")
    story.append(_materials_table(project, body))

    # ---- 5. Global Minimums ---------------------------------------
    section("Global Minimums")
    for mid in method_ids:
        res = results.get(mid)
        story.append(Paragraph(f"Method: {_method_name(mid)}", h_method))
        if res is None or res.critical is None:
            story.append(Paragraph("No valid critical surface found.",
                                   body))
            continue
        crit = res.critical
        surf = crit.surface
        rows = [("Factor of Safety (FS)", _fmt(crit.fos, 4))]
        if hasattr(surf, "centre_x") and surf.centre_x is not None:
            rows += [
                ("Centre", f"({_fmt(surf.centre_x)}, "
                           f"{_fmt(surf.centre_y)})"),
                ("Radius", _fmt(surf.radius)),
            ]
        x_l = getattr(surf, "x_left", None)
        x_r = getattr(surf, "x_right", None)
        if x_l is not None and x_r is not None:
            y_l = surf.base_y_at(x_l) if hasattr(surf, "base_y_at") else None
            y_r = surf.base_y_at(x_r) if hasattr(surf, "base_y_at") else None
            rows += [
                ("Left Slip Surface Endpoint",
                 f"({_fmt(x_l)}, {_fmt(y_l)})"),
                ("Right Slip Surface Endpoint",
                 f"({_fmt(x_r)}, {_fmt(y_r)})"),
            ]
        # Slice-area sum
        try:
            area = sum(sl.width * max(
                0.5 * ((sl.top_y_left - sl.base_y_left)
                       + (sl.top_y_right - sl.base_y_right)), 0.0)
                for sl in crit.slices.slices)
            rows.append(("Total Slice Area", f"{_fmt(area)} m²"))
        except Exception:  # noqa: BLE001
            pass
        story.append(kv_table(rows))
        story.append(Spacer(1, 4))

    # ---- 6. Valid / Invalid Surfaces ------------------------------
    section("Valid / Invalid Surfaces")
    vi_rows = [["Method", "Valid", "Invalid", "Total"]]
    for mid in method_ids:
        res = results.get(mid)
        if res is None:
            vi_rows.append([_method_name(mid), "—", "—", "—"])
        else:
            v = res.valid_count
            iv = res.invalid_count
            vi_rows.append([_method_name(mid), str(v), str(iv),
                            str(v + iv)])
    t = Table(vi_rows, colWidths=[70 * mm, 30 * mm, 30 * mm, 30 * mm])
    t.setStyle(_grid_style())
    story.append(t)

    # ---- 7. Slice Data --------------------------------------------
    story.append(PageBreak())
    section("Slice Data (Global Minimum Query)")
    for mid in method_ids:
        res = results.get(mid)
        if res is None or res.critical is None:
            continue
        story.append(Paragraph(
            f"Method: {_method_name(mid)} — FS = "
            f"{_fmt(res.critical.fos, 4)}", h_method))
        story.append(_slice_table(res.critical, project))
        story.append(Spacer(1, 8))

    # ---- 8. List of Coordinates -----------------------------------
    story.append(PageBreak())
    section("List of Coordinates")
    story.extend(_coordinates_flowables(project, h_method))

    # ---- Footer ----------------------------------------------------
    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#888"))
        canvas.drawString(
            18 * mm, 8 * mm,
            "OGR Slip2D — OpenGeoRock Suite  ·  GPL-3.0  ·  "
            "Samuel Sáez López, UPCT")
        canvas.drawRightString(
            doc_.pagesize[0] - 18 * mm, 8 * mm,
            f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output_path


def _unit_label(enum_val, mapping):
    """Map an enum (by .value) to a friendly label, with fallbacks."""
    if enum_val is None:
        return "—"
    val = getattr(enum_val, "value", enum_val)
    if val in mapping:
        return mapping[val]
    name = getattr(enum_val, "name", None)
    if name:
        return name.replace("_", " ").title()
    return str(val)


def _search_method_name(mid: str) -> str:
    names = {
        "grid": "Grid Search",
        "slope": "Slope Search",
        "auto_refine": "Auto Refine Search",
        "block": "Block Search",
        "path": "Path Search",
        "simulated_annealing": "Simulated Annealing",
    }
    return names.get(mid, str(mid).replace("_", " ").title())


def _grid_style():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#eef2f6")]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ])


def _materials_table(project, body):
    from reportlab.lib.units import mm
    mats = project.materials
    header = ["Property"] + [mm_name(mat) for mat in mats]
    rows = [header]

    def srow(label, fn):
        return [label] + [fn(mat) for mat in mats]

    def strength_type(mat):
        return getattr(mat.strength, "DISPLAY_NAME", None) \
            or type(mat.strength).__name__

    def _param(mat, key):
        params = getattr(mat.strength, "params", None)
        if isinstance(params, dict) and key in params:
            return params[key]
        return getattr(mat.strength, key, None)

    rows.append(srow("Strength Type", strength_type))
    rows.append(srow("Unit Weight [kN/m³]",
                     lambda m: _fmt(getattr(m, "unit_weight", None), 1)))
    rows.append(srow("Sat. Unit Weight [kN/m³]",
                     lambda m: _fmt(getattr(m, "sat_unit_weight", None), 1)))
    rows.append(srow("Cohesion [kPa]",
                     lambda m: _fmt(_param(m, "cohesion"), 1)))
    rows.append(srow("Friction Angle [deg]",
                     lambda m: _fmt(_param(m, "friction_angle"), 1)))
    ncol = len(mats) + 1
    w0 = 50 * mm
    wc = (project_width(project) - w0) / max(len(mats), 1)
    t = Table(rows, colWidths=[w0] + [wc] * len(mats))
    t.setStyle(_grid_style())
    return t


def project_width(project):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    return A4[0] - 36 * mm


def mm_name(mat):
    return getattr(mat, "name", "Material")


def _slice_table(crit, project):
    from reportlab.lib.units import mm
    header = ["#", "Width\n[m]", "Weight\n[kN]", "Base\nMat.",
              "c\n[kPa]", "φ\n[°]", "α\n[°]", "Base σ\n[kPa]",
              "Shear str.\n[kPa]", "u\n[kPa]"]
    rows = [header]
    slices = crit.slices.slices
    fos = crit.fos
    for i, sl in enumerate(slices):
        mat = sl.material
        c = phi = 0
        if mat is not None:
            params = getattr(mat.strength, "params", None)
            if isinstance(params, dict):
                c = params.get("cohesion", 0)
                phi = params.get("friction_angle", 0)
            else:
                c = getattr(mat.strength, "cohesion", 0)
                phi = getattr(mat.strength, "friction_angle", 0)
        # Base normal/shear come from the LEMResult arrays if present
        bn = (crit.base_normal[i]
              if crit.base_normal and i < len(crit.base_normal) else None)
        ss = (crit.base_shear_strength[i]
              if crit.base_shear_strength
              and i < len(crit.base_shear_strength) else None)
        rows.append([
            str(i + 1),
            _fmt(sl.width, 3),
            _fmt(sl.weight, 1),
            mm_name(mat) if mat else "—",
            _fmt(c, 0), _fmt(phi, 0),
            _fmt(math.degrees(sl.base_angle), 1),
            _fmt(bn, 2),
            _fmt(ss, 2),
            _fmt(sl.pore_pressure, 1),
        ])
    w = project_width(project)
    cw = [8, 13, 15, 18, 11, 9, 11, 16, 17, 12]
    scale = w / sum(cw)
    t = Table(rows, colWidths=[c * scale for c in cw], repeatRows=1)
    st = _grid_style()
    st.add("FONTSIZE", (0, 0), (-1, -1), 6.5)
    st.add("ALIGN", (0, 0), (-1, -1), "CENTER")
    t.setStyle(st)
    return t


def _coordinates_flowables(project, h_method):
    """Return a flat list of flowables: a heading + coordinate table
    per boundary. Wrapping each (heading, table) pair in KeepTogether
    keeps them on the same page."""
    from reportlab.lib.units import mm
    from reportlab.platypus import Table, Spacer, KeepTogether, Paragraph
    out = []

    def coord_table(verts):
        rows = [["X", "Y"]] + [[_fmt(v.x), _fmt(v.y)] for v in verts]
        t = Table(rows, colWidths=[25 * mm, 25 * mm])
        t.setStyle(_grid_style())
        return t

    for b in project.boundaries:
        label = b.btype.display_name
        out.append(KeepTogether([
            Paragraph(label, h_method),
            coord_table(b.polyline.vertices),
            Spacer(1, 6),
        ]))
    return out

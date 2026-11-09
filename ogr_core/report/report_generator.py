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
import os
from datetime import datetime, timezone
from typing import Optional
from xml.sax.saxutils import escape

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
        HRFlowable,
    )
    _HAS_REPORTLAB = True
except ImportError:  # pragma: no cover
    _HAS_REPORTLAB = False

#: The format the report writes its dates in.
STAMP_FORMAT = "%d/%m/%Y, %H:%M:%S"

#: reportlab's default Frame pads its content by 6 pt on each side, so the
#: width a flowable may take is the page's minus the margins minus these.
_FRAME_PADDING = 6

#: v0.1.417 (D351) -- the four faces the report is set in, DejaVu Sans,
#: registered once and EMBEDDED in the PDF. With the 14 standard fonts
#: nothing is embedded and the text is in WinAnsi: a viewer without
#: Helvetica's metrics drew «[kN/m ]» for «[kN/m³]», and σ, φ, α or ≤ are
#: not in WinAnsi at all. The files are the copy matplotlib ships (a
#: dependency already), so nothing is installed; licence: Bitstream Vera,
#: with DejaVu's changes in the public domain.
_DEJAVU = {"regular": "DejaVuSans", "bold": "DejaVuSans-Bold",
           "italic": "DejaVuSans-Oblique",
           "boldItalic": "DejaVuSans-BoldOblique"}
#: Only if matplotlib's copy cannot be read: the standard fonts, as before.
_STANDARD = {"regular": "Helvetica", "bold": "Helvetica-Bold",
             "italic": "Helvetica-Oblique",
             "boldItalic": "Helvetica-BoldOblique"}
_FONTS: dict = {}


def report_fonts() -> dict:
    """``{"regular", "bold", "italic", "boldItalic"}`` -> the font names
    the report uses: DejaVu Sans, embedded (registered with reportlab on
    the first call, as one family so that ``<b>`` and ``<i>`` find their
    faces), or the standard Helvetica if its files cannot be read."""
    if not _FONTS:
        _FONTS.update(_register_dejavu() or _STANDARD)
    return _FONTS


def _register_dejavu() -> Optional[dict]:
    try:
        import matplotlib
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFError, TTFont
    except ImportError:  # pragma: no cover - both are dependencies
        return None
    folder = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
    try:
        known = set(pdfmetrics.getRegisteredFontNames())
        for name in _DEJAVU.values():
            if name not in known:
                pdfmetrics.registerFont(
                    TTFont(name, os.path.join(folder, name + ".ttf")))
    except (OSError, TTFError):
        return None
    pdfmetrics.registerFontFamily(
        _DEJAVU["regular"], normal=_DEJAVU["regular"],
        bold=_DEJAVU["bold"], italic=_DEJAVU["italic"],
        boldItalic=_DEJAVU["boldItalic"])
    return dict(_DEJAVU)


def local_timestamp(text: str) -> str:
    """``summary.date_created`` as the report writes its own dates: in local
    time and as ``dd/mm/YYYY, HH:MM:SS`` (v0.1.417, D351).

    The project stamps it in ISO 8601, in UTC and without the zone
    (``Project.__init__``), so a stamp without a zone is read as UTC; one
    with a zone is read with it. Anything else -- a date typed through the
    API, a date with no time, which has no hour to move -- is shown as
    written. The file keeps what it had: only the report converts."""
    text = text or ""
    if "T" not in text and " " not in text.strip():
        return text
    try:
        when = datetime.fromisoformat(text.strip())
    except ValueError:
        return text
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone().strftime(STAMP_FORMAT)


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
    "corps_engineers_1": "Corps of Engineers #1",
    "corps_engineers_2": "Corps of Engineers #2",
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
    factor_report=None,
    figures=None,
    translate=None,
    method_name=None,
    standard_name=None,
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
    factor_report : FactorReport, optional
        The run's design-factor report (v0.1.242, D226a). With partial
        factors applied, the report says which, and the headline number is
        an over-design factor rather than a factor of safety. Asked of the
        run and not of ``project.settings``, which can change after it.
    figures : list of (method id, png bytes), optional
        v0.1.339 (D336) -- the figure of the critical surface of each
        method (``ogr_api.report_figures.method_figures``), embedded after
        the global minimums with the caption the report writes for it. The core draws nothing itself: the
        figures need the engine's reading of a search, which it cannot
        import.
    translate : callable, optional
        v0.1.355 (D335) -- the report in the reader's language: every fixed
        text of the report, and every message with a code (the design
        standard's summary and notes), is passed through it. The window
        passes its own (``ogr_gui.core_messages.note_text``); the core cannot
        import the interface's dictionary, so without it the report is in
        English, as the API and the MCP server write it.
    method_name : callable, optional
        A method's name from its identifier, in the reader's language (the
        window's ``ogr_gui.labels.method_name``). Without it, the report's
        own English names.

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

    T = translate or _same
    name_of = method_name or _method_name
    # v0.1.434 (D412) -- the design standard by its name in the reader's
    # language, when the caller knows it (the window); the API's report
    # keeps the stored id it always printed
    standard_of = standard_name or str
    summary = project.settings.summary
    author = author or summary.author or ""
    company = company or summary.company or ""
    # v0.1.433 (D411) -- a default title is the program's, not the user's:
    # in the reader's language (it printed «Untitled Project» in Spanish);
    # a title the user wrote is data. Asked of the title that is PRINTED,
    # whoever passes it: the window passes ``title=summary.title``, and a
    # project's summary is born with the project's name («Untitled», «Demo
    # slope»), so the summary's alone never reached the window's report
    # (review of 0.1.433).
    from ogr_core.project.demo import DEMO_PROJECT_NAME
    from ogr_core.project.project import DEFAULT_PROJECT_NAME
    from ogr_core.project.settings import DEFAULT_SUMMARY_TITLE
    title = title or summary.title
    if title in (DEFAULT_SUMMARY_TITLE, DEFAULT_PROJECT_NAME,
                 DEMO_PROJECT_NAME):
        title = T(title)
    title = title or T("OGR Slip2D — Slope Stability Analysis")

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=title, author=author or "OGR Slip2D",
    )

    styles = getSampleStyleSheet()
    font = report_fonts()
    # v0.1.417 (D351) -- the width a flowable may take, the same for the
    # rules, the tables and the figures: they used the page's width minus
    # the margins, 2 mm wider on each side than the frame lets them be
    width = project_width(project)
    h_title = ParagraphStyle(
        "OGRTitle", parent=styles["Title"], fontSize=18,
        fontName=font["bold"],
        textColor=colors.HexColor("#1a3a5c"), spaceAfter=4,
    )
    h_sub = ParagraphStyle(
        "OGRSub", parent=styles["Normal"], fontSize=11,
        fontName=font["regular"],
        textColor=colors.HexColor("#456"), alignment=1, spaceAfter=14,
    )
    # v0.1.417 (D351) -- a heading stays with what follows it: «Global
    # Minimums» was left alone at the foot of page 1
    h_sec = ParagraphStyle(
        "OGRSection", parent=styles["Heading2"], fontSize=13,
        fontName=font["bold"],
        textColor=colors.HexColor("#1a3a5c"), spaceBefore=12, spaceAfter=6,
        borderWidth=0, leading=16, keepWithNext=1,
    )
    h_method = ParagraphStyle(
        "OGRMethod", parent=styles["Heading3"], fontSize=11,
        fontName=font["boldItalic"],
        textColor=colors.HexColor("#2a5a8c"), spaceBefore=8, spaceAfter=3,
        keepWithNext=1,
    )
    body = ParagraphStyle(
        "OGRBody", parent=styles["Normal"], fontSize=9, leading=12,
        fontName=font["regular"],
    )

    story = []

    def section(txt):
        story.append(Paragraph(txt, h_sec))
        story.append(_hrule())

    def _hrule():
        # The frame's width, as the tables under it: the one-cell table it
        # was took the page's and crossed their edges
        rule = HRFlowable(width=width, thickness=0.8,
                          color=colors.HexColor("#1a3a5c"),
                          spaceBefore=0, spaceAfter=2)
        # the platypus way to say «with the next one»: the document groups
        # the heading, this rule and what follows in one KeepTogether
        rule.keepWithNext = 1
        return rule

    def kv_table(rows):
        t = Table([[Paragraph(f"<b>{k}</b>", body), Paragraph(str(v), body)]
                   for k, v in rows], colWidths=[55 * mm, width - 55 * mm])
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
    section(T("Project Summary"))
    # v0.1.417 (D351) -- «File» is the file the project was saved in; it
    # said the project's name, and the demo had never been saved
    path = getattr(project, "file_path", None)
    now = datetime.now().strftime(STAMP_FORMAT)
    story.append(kv_table([
        (T("Project Title"), title),
        (T("File"), escape(str(path)) if path else T("not saved")),
        (T("Author"), author or "—"),
        (T("Company"), company or "—"),
        # v0.1.417 (D351) -- in local time and in the format of the line
        # below: it was the stored ISO stamp, in UTC and to the microsecond
        (T("Date Created"), local_timestamp(summary.date_created) or now),
        (T("Report Generated"), now),
    ]))
    if summary.comments:
        # v0.1.417 -- one line per comment: ``comments`` is a list, and the
        # report printed its Python repr, brackets and quotes included
        lines = ([summary.comments] if isinstance(summary.comments, str)
                 else list(summary.comments))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>%s</b> %s" % (
            T("Comments:"),
            "<br/>".join(escape(str(c)) for c in lines)), body))

    # ---- 2. General Settings --------------------------------------
    units = project.settings.units
    section(T("General Settings"))
    story.append(kv_table([
        (T("Units of Measurement"), T(_unit_label(
            getattr(units, "system", None),
            {"metric": "Metric Units", "imperial": "Imperial Units"}))),
        (T("Time Units"), T(_unit_label(
            getattr(units, "time", None), TIME_UNIT_WORDS))),
        (T("Permeability Units"), T(_unit_label(
            getattr(units, "permeability", None), PERMEABILITY_UNIT_WORDS))),
        (T("Failure Direction"), T(_unit_label(
            getattr(units, "failure_direction", None),
            {"R2L": "Right to Left", "L2R": "Left to Right"}))),
    ]))

    # ---- 3. Analysis Options --------------------------------------
    m = project.settings.methods
    s = project.settings.search
    section(T("Analysis Options"))
    story.append(Paragraph("<b>%s</b>" % T("Analysis Methods Used"), body))
    method_ids = list(results.keys()) or list(m.enabled_methods)
    for mid in method_ids:
        story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;• {name_of(mid)}",
                               body))
    story.append(Spacer(1, 4))
    story.append(kv_table([
        (T("Number of Slices"), m.num_slices),
        (T("Tolerance"), m.tolerance),
        (T("Maximum Iterations"), m.max_iterations),
    ]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>%s</b>" % T("Surface Options"), body))
    story.append(kv_table([
        # v0.1.433 (D411) -- «Non-Circular» by its key: the title-case of
        # the identifier printed «Non_Circular», in English
        (T("Surface Type"),
         T("Circular") if s.surface_type in ("circular", "Circular")
         else T("Non-Circular") if s.surface_type in ("non_circular",
                                                      "Non-Circular")
         else T(str(s.surface_type).title())),
        (T("Search Method"),
         T(_search_method_name(s.search_method))),
        (T("Radius Increment"), s.radius_increment),
        (T("Composite Surfaces"),
         T("Enabled") if getattr(s, "composite_surfaces", False)
         else T("Disabled")),
    ]))

    # ---- 3b. Design Standard --------------------------------------
    # v0.1.242 (D226a) — what the run factored, from its own factor report.
    # Without one nothing is said here, as before; the slice table still
    # carries each slice's weight factor, which comes from the result.
    factored = bool(getattr(factor_report, "applied", False))
    if factored:
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>%s</b>" % T("Design Standard"), body))
        story.append(kv_table([
            (T("Standard"), standard_of(getattr(factor_report, "standard",
                                                "—"))),
            # v0.1.355 (D335) -- the summary and the notes carry their codes
            (T("Factored"), T(factor_report.summary())),
        ]))
        for note in getattr(factor_report, "notes", None) or []:
            story.append(Paragraph(
                f"&nbsp;&nbsp;&nbsp;• {escape(str(T(note)))}", body))
    # The caption follows the value printed: with partial factors on the
    # inputs the number is an over-design factor, which must exceed 1.
    fs_label = (T("Over-design Factor") if factored
                else T("Factor of Safety (FS)"))
    fs_short = T("ODF") if factored else T("FS")

    # ---- 4. Material Properties -----------------------------------
    section(T("Material Properties"))
    story.append(_materials_table(project, body, T))

    # ---- 5. Global Minimums ---------------------------------------
    section(T("Global Minimums"))
    for mid in method_ids:
        res = results.get(mid)
        story.append(Paragraph(T("Method: {0}").format(name_of(mid)),
                               h_method))
        if res is None or res.critical is None:
            story.append(Paragraph(T("No valid critical surface found."),
                                   body))
            continue
        crit = res.critical
        surf = crit.surface
        rows = [(fs_label, _fmt(crit.fos, 4))]
        if hasattr(surf, "centre_x") and surf.centre_x is not None:
            rows += [
                (T("Centre"), f"({_fmt(surf.centre_x)}, "
                              f"{_fmt(surf.centre_y)})"),
                (T("Radius"), _fmt(surf.radius)),
            ]
        x_l = getattr(surf, "x_left", None)
        x_r = getattr(surf, "x_right", None)
        if x_l is not None and x_r is not None:
            y_l = surf.base_y_at(x_l) if hasattr(surf, "base_y_at") else None
            y_r = surf.base_y_at(x_r) if hasattr(surf, "base_y_at") else None
            rows += [
                (T("Left Slip Surface Endpoint"),
                 f"({_fmt(x_l)}, {_fmt(y_l)})"),
                (T("Right Slip Surface Endpoint"),
                 f"({_fmt(x_r)}, {_fmt(y_r)})"),
            ]
        # Slice-area sum
        try:
            area = sum(sl.width * max(
                0.5 * ((sl.top_y_left - sl.base_y_left)
                       + (sl.top_y_right - sl.base_y_right)), 0.0)
                for sl in crit.slices.slices)
            rows.append((T("Total Slice Area"), f"{_fmt(area)} m²"))
        except Exception:  # noqa: BLE001
            pass
        # v0.1.243 (D226b) — how the design standard classed each load on
        # this surface: whether a load drives depends on the surface, so it
        # is said here and not in the run's section.
        for name, text in _load_factor_rows(crit, T):
            rows.append((T("Load '{0}'").format(name), text))
        story.append(kv_table(rows))
        story.append(Spacer(1, 4))

    # ---- 5b. Critical surface by method ---------------------------
    if figures:
        section(T("Critical Surface by Method"))
        story.extend(_figure_flowables(figures, results, fs_short,
                                       width, h_method, T, name_of))

    # ---- 6. Valid / Invalid Surfaces ------------------------------
    section(T("Valid / Invalid Surfaces"))
    # v0.1.187 (D160) — "Attempted" beside the population. Total is the
    # population the search ANALYSED; attempted is what it cost to get
    # it, and the two differ by the candidates a focus object removed,
    # which belong to neither of the first two columns.
    vi_rows = [[T("Method"), T("Valid"), T("Invalid"), T("Total"),
                T("Attempted")]]
    for mid in method_ids:
        res = results.get(mid)
        if res is None:
            vi_rows.append([name_of(mid), "—", "—", "—", "—"])
        else:
            v = res.valid_count
            iv = res.invalid_count
            at = getattr(res, "attempts", 0)
            vi_rows.append([name_of(mid), str(v), str(iv),
                            str(v + iv), str(at) if at else "—"])
    # v0.1.417 (D351) -- at the frame's width, as the rule above it: at
    # 164 mm the rule crossed its edges
    cw = [64, 24, 24, 24, 28]
    t = Table(vi_rows, colWidths=[c * width / sum(cw) for c in cw])
    t.setStyle(_grid_style())
    story.append(t)

    # ---- 7. Slice Data --------------------------------------------
    story.append(PageBreak())
    section(T("Slice Data (Global Minimum Query)"))
    for mid in method_ids:
        res = results.get(mid)
        if res is None or res.critical is None:
            continue
        story.append(Paragraph(
            T("Method: {0}").format(name_of(mid)) + " — %s = %s" % (
                fs_short, _fmt(res.critical.fos, 4)), h_method))
        story.append(_slice_table(res.critical, project, T))
        story.append(Spacer(1, 8))

    # ---- 8. List of Coordinates -----------------------------------
    story.append(PageBreak())
    section(T("List of Coordinates"))
    story.extend(_coordinates_flowables(project, h_method, T))

    # ---- Footer ----------------------------------------------------
    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont(font["regular"], 7)
        canvas.setFillColor(colors.HexColor("#888"))
        # v0.1.355 -- the program's licence, AGPL-3.0-or-later: the footer
        # said GPL-3.0, which is not the licence of this program
        canvas.drawString(
            18 * mm, 8 * mm,
            "OGR Slip2D — OpenGeoRock Suite  ·  AGPL-3.0-or-later  ·  "
            "Samuel Sáez López, UPCT")
        canvas.drawRightString(
            doc_.pagesize[0] - 18 * mm, 8 * mm,
            T("Page {0}").format(doc_.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output_path


def _same(text):
    """The report's text as written: the default of ``translate``."""
    return text


def _figure_flowables(figures, results, fs_short, width, caption_style,
                      T=_same, name_of=None):
    """One figure per method at the page's width, each under its caption:
    the method and the number it found, called what the run calls it."""
    import io

    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Image, KeepTogether
    out = []
    for mid, png in figures:
        res = results.get(mid)
        crit = getattr(res, "critical", None)
        caption = T("Method: {0}").format((name_of or _method_name)(mid))
        if crit is not None:
            caption += f" — {fs_short} = {_fmt(crit.fos, 4)}"
        w, h = ImageReader(io.BytesIO(png)).getSize()
        out.append(KeepTogether([
            Paragraph(caption, caption_style),
            Image(io.BytesIO(png), width=width, height=width * h / max(w, 1)),
        ]))
    return out


#: v0.1.434 (D412) -- the report's words for every time and permeability
#: unit the enums have (``ogr_core.project.units``): the others printed the
#: member's name title-cased, «Minutes», «M Day», «Mm Hour», in either
#: language. «ft/s» is no member, and went.
TIME_UNIT_WORDS = {"s": "seconds", "min": "minutes", "h": "hours",
                   "d": "days", "mo": "months", "yr": "years"}
PERMEABILITY_UNIT_WORDS = {"m/s": "meters/second", "m/day": "meters/day",
                           "m/year": "meters/year", "cm/s": "cm/second",
                           "mm/hour": "mm/hour"}


def _unit_label(enum_val, mapping):
    """Map an enum (by .value) to a friendly label, with fallbacks."""
    if enum_val is None:
        return "—"
    val = getattr(enum_val, "value", enum_val)
    if val in mapping:
        return mapping[val]
    # v0.1.434 (D412) -- a value with no label prints as it is stored («mo»,
    # «m/day»); the member's name title-cased read «M Day»
    return str(val)


def _search_method_name(mid: str) -> str:
    names = {
        "grid": "Grid Search",
        "slope": "Slope Search",
        "auto_refine": "Auto Refine Search",
        "block": "Block Search",
        "path": "Path Search",
        "simulated_annealing": "Simulated Annealing",
        # v0.1.433 (D411) -- it was missing: «Particle Swarm»
        "particle_swarm": "Particle Swarm Search",
    }
    return names.get(mid, str(mid).replace("_", " ").title())


def _grid_style():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, -1), report_fonts()["regular"]),
        ("FONTNAME", (0, 0), (-1, 0), report_fonts()["bold"]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#eef2f6")]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ])


def _materials_table(project, body, T=_same):
    from reportlab.lib.units import mm
    mats = project.materials
    header = [T("Property")] + [mm_name(mat) for mat in mats]
    rows = [header]

    def srow(label, fn):
        return [label] + [fn(mat) for mat in mats]

    def strength_type(mat):
        shown = getattr(mat.strength, "DISPLAY_NAME", None)
        return T(shown) if shown else type(mat.strength).__name__

    def _param(mat, key):
        params = getattr(mat.strength, "params", None)
        if isinstance(params, dict) and key in params:
            return params[key]
        return getattr(mat.strength, key, None)

    rows.append(srow(T("Strength Type"), strength_type))
    rows.append(srow(T("Unit Weight") + " [kN/m³]",
                     lambda m: _fmt(getattr(m, "unit_weight", None), 1)))
    # v0.1.60 — only report γsat for materials that actually use it, so the
    # report never states a weight the analysis did not apply.
    rows.append(srow(T("Sat. Unit Weight") + " [kN/m³]",
                     lambda m: _fmt(getattr(m, "sat_unit_weight", None), 1)
                     if getattr(m, "use_sat_unit_weight", False) else "—"))
    rows.append(srow(T("Cohesion") + " [kPa]",
                     lambda m: _fmt(_param(m, "cohesion"), 1)))
    # v0.1.370 (D344) -- "[°]" in both languages, as the slice table writes
    # φ: "[deg]" read as English in the Spanish report
    rows.append(srow(T("Friction Angle") + " [°]",
                     lambda m: _fmt(_param(m, "friction_angle"), 1)))
    ncol = len(mats) + 1
    w0 = 50 * mm
    wc = (project_width(project) - w0) / max(len(mats), 1)
    t = Table(rows, colWidths=[w0] + [wc] * len(mats))
    t.setStyle(_grid_style())
    return t


def project_width(project):
    """The width a flowable may take on the report's page: A4 minus the
    18 mm margins minus the frame's padding (v0.1.417, D351 -- without the
    padding the full-width tables stood 2 mm out of the frame each side)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    return A4[0] - 36 * mm - 2 * _FRAME_PADDING


def mm_name(mat):
    return getattr(mat, "name", "Material")


def _load_factor_rows(crit, T=_same) -> list:
    """``[(load name, "variable, drives the sliding: × 1.5")]`` for the loads
    a design standard factored on ``crit``'s surface; empty without one."""
    factors = getattr(getattr(crit, "slices", None), "load_factors", None)
    if not factors:
        return []
    return [(name,
             (T("{0}, drives the sliding: × {1:g}") if drives
              else T("{0}, resists the sliding: × {1:g}")).format(
                  T(f"{action}"), factor))
            for _load_id, (action, drives, factor, name) in factors.items()]


def _slice_table(crit, project, T=_same):
    from reportlab.lib.units import mm
    header = ["#", T("Width") + "\n[m]", T("Weight") + "\n[kN]",
              T("Base\nMat."), "c\n[kPa]", "φ\n[°]", "α\n[°]",
              T("Base σ") + "\n[kPa]", T("Shear str.") + "\n[kPa]",
              "u\n[kPa]"]
    slices = crit.slices.slices
    # v0.1.242 (D226a) — the permanent-action factor each weight carries,
    # beside it, when the run applied one: the weight column is the
    # FACTORED weight, and a reader checking it by hand needs the factor.
    weighted = any(getattr(sl, "weight_factor", 1.0) != 1.0
                   for sl in slices)
    if weighted:
        header.insert(3, T("Weight\nfactor"))
    rows = [header]
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
        bn = (crit.base_normal_force[i]
              if crit.base_normal_force
              and i < len(crit.base_normal_force) else None)
        ss = (crit.base_shear_strength[i]
              if crit.base_shear_strength
              and i < len(crit.base_shear_strength) else None)
        row = [
            str(i + 1),
            _fmt(sl.width, 3),
            _fmt(sl.weight, 1),
            mm_name(mat) if mat else "—",
            _fmt(c, 0), _fmt(phi, 0),
            _fmt(math.degrees(sl.base_angle), 1),
            _fmt(bn, 2),
            _fmt(ss, 2),
            _fmt(sl.pore_pressure, 1),
        ]
        if weighted:
            row.insert(3, _fmt(getattr(sl, "weight_factor", 1.0), 3))
        rows.append(row)
    w = project_width(project)
    cw = [8, 13, 15, 18, 11, 9, 11, 16, 17, 12]
    if weighted:
        cw.insert(3, 12)
    scale = w / sum(cw)
    t = Table(rows, colWidths=[c * scale for c in cw], repeatRows=1)
    st = _grid_style()
    st.add("FONTSIZE", (0, 0), (-1, -1), 6.5)
    st.add("ALIGN", (0, 0), (-1, -1), "CENTER")
    t.setStyle(st)
    return t


def _coordinates_flowables(project, h_method, T=_same):
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
        label = T(b.btype.display_name)
        out.append(KeepTogether([
            Paragraph(label, h_method),
            coord_table(b.polyline.vertices),
            Spacer(1, 6),
        ]))
    return out

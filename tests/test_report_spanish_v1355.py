# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.355 (D335, last part; D335 closed) — the PDF report in the language
of the interface, and its footer with the program's licence.

``ogr_core.report.generate_report`` wrote every text of the report in
English: the core cannot import the interface's dictionary. By decision of
the owner (2026-10-20) the report follows the interface's language: it takes
``translate`` and ``method_name``, and the window passes its own
(``core_messages.note_text``, which says a coded message by its code and a
fixed text through ``tr()``, and ``labels.method_name``). The figures take
``translate`` too (``report_figures.method_figures``: the scale and the
legend). The API and the MCP server pass nothing and write it in English,
as before. The footer said «GPL-3.0», which is not this program's licence:
it says AGPL-3.0-or-later now (only that text; by decision of the owner).

The invariants:

* **without ``translate`` the report writes what v0.1.354 wrote, text for
  text** (``_V1354``: every paragraph, table cell and footer text with
  words that v0.1.354 wrote on the model below, captured from its
  building; the timestamps masked), except the footer's licence;
* **with the window's ``translate``, in Spanish**: no fixed English text of
  the report is left, the methods are named in Spanish and the design
  standard's summary and notes are said by their codes;
* the figures' words go through ``translate``;
* the window passes it, and the API does not.
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent

#: ``(kind, text)``: what the v0.1.354 report wrote, in order and without
#: repeats -- "p" a paragraph, "t" a table cell, "f" the page footer.
_V1354 = [('p', 'Report'),
 ('p', 'OGR Slip2D — OpenGeoRock Suite'),
 ('p', 'Project Summary'),
 ('p', '<b>Project Title</b>'),
 ('p', '<b>File</b>'),
 ('p', '<b>Author</b>'),
 ('p', 'Samuel Sáez López'),
 ('p', '<b>Company</b>'),
 ('p', 'UPCT'),
 ('p', '<b>Date Created</b>'),
 ('p', '<b>Report Generated</b>'),
 ('p', '<date>'),
 ('p', 'General Settings'),
 ('p', '<b>Units of Measurement</b>'),
 ('p', 'Metric Units'),
 ('p', '<b>Time Units</b>'),
 ('p', 'days'),
 ('p', '<b>Permeability Units</b>'),
 ('p', 'meters/second'),
 ('p', '<b>Failure Direction</b>'),
 ('p', 'Right to Left'),
 ('p', 'Analysis Options'),
 ('p', '<b>Analysis Methods Used</b>'),
 ('p', '&nbsp;&nbsp;&nbsp;• Bishop Simplified'),
 ('p', '&nbsp;&nbsp;&nbsp;• Janbu Simplified'),
 ('p', '<b>Number of Slices</b>'),
 ('p', '<b>Tolerance</b>'),
 ('p', '<b>Maximum Iterations</b>'),
 ('p', '<b>Surface Options</b>'),
 ('p', '<b>Surface Type</b>'),
 ('p', 'Circular'),
 ('p', '<b>Search Method</b>'),
 ('p', 'Grid Search'),
 ('p', '<b>Radius Increment</b>'),
 ('p', '<b>Composite Surfaces</b>'),
 ('p', 'Disabled'),
 ('p', '<b>Design Standard</b>'),
 ('p', '<b>Standard</b>'),
 ('p', 'eurocode7_da1c1'),
 ('p', '<b>Factored</b>'),
 ('p', 'eurocode7_da1c1: 0 material(s) and 0 load(s) factored'),
 ('p',
  '&nbsp;&nbsp;&nbsp;• Soil weight: the permanent-action factor 1.35 '
  'multiplies the weight of every slice (single source assumption).'),
 ('p', 'Material Properties'),
 ('t', 'Property'),
 ('t', 'Soil'),
 ('t', 'Strength Type'),
 ('t', 'Mohr-Coulomb'),
 ('t', 'Unit Weight [kN/m³]'),
 ('t', 'Sat. Unit Weight [kN/m³]'),
 ('t', 'Cohesion [kPa]'),
 ('t', 'Friction Angle [deg]'),
 ('p', 'Global Minimums'),
 ('p', 'Method: Bishop Simplified'),
 ('p', '<b>Over-design Factor</b>'),
 ('p', '<b>Centre</b>'),
 ('p', '<b>Radius</b>'),
 ('p', '<b>Left Slip Surface Endpoint</b>'),
 ('p', '<b>Right Slip Surface Endpoint</b>'),
 ('p', '<b>Total Slice Area</b>'),
 ('p', 'Method: Janbu Simplified'),
 ('p', 'Critical Surface by Method'),
 ('p', 'Method: Bishop Simplified — ODF = 0.9508'),
 ('p', 'Method: Janbu Simplified — ODF = 0.9205'),
 ('p', 'Valid / Invalid Surfaces'),
 ('t', 'Method'),
 ('t', 'Valid'),
 ('t', 'Invalid'),
 ('t', 'Total'),
 ('t', 'Attempted'),
 ('t', 'Bishop Simplified'),
 ('t', 'Janbu Simplified'),
 ('p', 'Slice Data (Global Minimum Query)'),
 ('t', 'Width\n[m]'),
 ('t', 'Weight\n[kN]'),
 ('t', 'Weight\nfactor'),
 ('t', 'Base\nMat.'),
 ('t', 'c\n[kPa]'),
 ('t', 'Base σ\n[kPa]'),
 ('t', 'Shear str.\n[kPa]'),
 ('t', 'u\n[kPa]'),
 ('p', 'List of Coordinates'),
 ('p', 'External Boundary'),
 ('f',
  'OGR Slip2D — OpenGeoRock Suite  ·  GPL-3.0  ·  Samuel Sáez López, UPCT'),
 ('f', 'Page 1'),
 ('f', 'Property'),
 ('f', 'Strength Type'),
 ('f', 'Unit Weight [kN/m³]'),
 ('f', 'Sat. Unit Weight [kN/m³]'),
 ('f', 'Cohesion [kPa]'),
 ('f', 'Friction Angle [deg]'),
 ('f', 'Page 2'),
 ('f', 'Page 3'),
 ('f', 'Method'),
 ('f', 'Bishop Simplified'),
 ('f', 'Janbu Simplified'),
 ('f', 'Page 4'),
 ('f', 'Page 5'),
 ('f', 'Page 6')]


_DATE = re.compile(r"\d\d/\d\d/\d{4}, \d\d:\d\d:\d\d")
_STAMP = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?")


def _model():
    from ogr_api import Workspace, call
    ws = Workspace()
    try:
        pid = call(ws, "project_new", name="Report")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25],
                         [20, 25]],
            "materials": [{"name": "Soil", "unit_weight": 20.0,
                           "strength": {"model": "mohr_coulomb",
                                        "params": {"cohesion": 3.0,
                                                   "friction_angle": 19.6}}}],
            "settings": {
                "methods.enabled_methods": ["bishop_simplified",
                                            "janbu_simplified"],
                "search.grid_x_min": 22.8, "search.grid_x_max": 43.7,
                "search.grid_y_min": 42.3, "search.grid_y_max": 62.6,
                "search.grid_nx": 3, "search.grid_ny": 3,
                "search.radius_increment": 2}})
        p = ws.get(pid).project
    finally:
        ws.shutdown()
    ds = p.settings.design_standard
    ds.enabled = True
    ds.apply_preset("eurocode7_da1c1")
    return p


_RUN = {}


def _run():
    if "run" not in _RUN:
        from ogr_slip2d.analysis_runner import run_analysis
        p = _model()
        out = run_analysis(p)
        _RUN["run"] = (p, out.results, out.factor_report)
    return _RUN["run"]


def _capture(**kw):
    """Every text the report writes, in order: its paragraphs, its table
    cells and what the page footer draws."""
    import reportlab.platypus as platypus
    from reportlab.pdfgen.canvas import Canvas

    import ogr_core.report.report_generator as RG
    from ogr_api.report_figures import method_figures
    p, results, rep = _run()
    said = []
    real_par, real_tab = platypus.Paragraph, platypus.Table
    real_draw, real_right = Canvas.drawString, Canvas.drawRightString

    class Par(real_par):
        def __init__(self, text, *a, **k):
            said.append(("p", str(text)))
            super().__init__(text, *a, **k)

    class Tab(real_tab):
        def __init__(self, data, *a, **k):
            said.extend(("t", c) for row in data for c in row
                        if isinstance(c, str))
            super().__init__(data, *a, **k)

    def draw(self, x, y, text, *a, **k):
        said.append(("f", str(text)))
        return real_draw(self, x, y, text, *a, **k)

    def right(self, x, y, text, *a, **k):
        said.append(("f", str(text)))
        return real_right(self, x, y, text, *a, **k)

    figs = method_figures(p, results, factored=True, width=400, height=300,
                          translate=kw.get("translate"))
    platypus.Paragraph, platypus.Table = Par, Tab
    RG.Paragraph, RG.Table = Par, Tab
    Canvas.drawString, Canvas.drawRightString = draw, right
    try:
        with tempfile.TemporaryDirectory() as tmp:
            RG.generate_report(p, results, os.path.join(tmp, "r.pdf"),
                               factor_report=rep, figures=figs, **kw)
    finally:
        platypus.Paragraph, platypus.Table = real_par, real_tab
        RG.Paragraph, RG.Table = real_par, real_tab
        Canvas.drawString, Canvas.drawRightString = real_draw, real_right
    out = []
    for kind, text in said:
        # in the order ``_V1354`` was taken in: the report's dates masked,
        # the texts with words kept, then a timestamp inside one masked
        text = _DATE.sub("<date>", text)
        if not re.search(r"[A-Za-z]{2}", text):
            continue
        text = _STAMP.sub("<stamp>", text)
        if (kind, text) not in out:
            out.append((kind, text))
    return out


class _Spanish:
    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self._before = current_language()
        set_language("es")

    def __exit__(self, *_exc):
        from ogr_gui.i18n import set_language
        set_language(self._before)


_GPL = "OpenGeoRock Suite  ·  GPL-3.0  ·  "
_AGPL = "OpenGeoRock Suite  ·  AGPL-3.0-or-later  ·  "


# ======================================================================
class TestWithoutTranslateItIsTheOldReport:

    def test_text_for_text(self):
        expected = [(k, t.replace(_GPL, _AGPL)) for k, t in _V1354]
        said = _capture()
        assert said == expected, [x for x in said if x not in expected]

    def test_the_footer_says_the_programs_licence(self):
        footer = [t for k, t in _capture() if k == "f" and "Suite" in t]
        assert footer and all("AGPL-3.0-or-later" in t for t in footer)
        assert not any("GPL-3.0  " in t for t in footer)


#: The report's own fixed texts: none may be left in a Spanish report.
_FIXED = sorted({t for k, t in _V1354 if k in "pt"} & {
    "Project Summary", "General Settings", "Analysis Options",
    "Material Properties", "Global Minimums", "Critical Surface by Method",
    "Valid / Invalid Surfaces", "Slice Data (Global Minimum Query)",
    "List of Coordinates", "<b>Project Title</b>", "<b>Search Method</b>",
    "Metric Units", "days", "meters/second", "Right to Left", "Grid Search",
    "Disabled", "<b>Over-design Factor</b>", "Property", "Strength Type",
    "Method", "Valid", "Invalid", "Attempted",
    "Bishop Simplified", "Janbu Simplified", "External Boundary"})


class TestWithTheWindowsTranslateItIsSpanish:

    def _said(self):
        from ogr_gui.core_messages import note_text
        from ogr_gui.labels import method_name
        with _Spanish():
            return _capture(translate=note_text, method_name=method_name)

    def test_no_fixed_english_text_is_left(self):
        assert len(_FIXED) > 20, _FIXED
        texts = {t for _k, t in self._said()}
        left = [t for t in _FIXED if t in texts]
        assert not left, left

    def test_it_says_it_in_spanish(self):
        from ogr_gui.labels import method_name
        texts = [t for _k, t in self._said()]
        with _Spanish():
            bishop = method_name("bishop_simplified")
        for expected in ("Ajustes generales", "Lista de coordenadas",
                         "Método: " + bishop, "Página 1"):
            assert expected in texts, (expected, texts[:30])
        assert any(t.startswith("Método: %s — FSD = " % bishop)
                   for t in texts), texts
        assert ("eurocode7_da1c1: 0 material(es) y 0 carga(s) afectados por "
                "los coeficientes") in texts
        assert any("Peso del terreno: el coeficiente de las acciones "
                   "permanentes 1.35" in t for t in texts)


class TestTheFiguresWordsGoThroughTranslate:

    def test_the_scale_and_the_legend(self):
        import ogr_api.render as R
        from ogr_api.report_figures import method_figures
        from ogr_gui.core_messages import note_text
        p, results, _rep = _run()
        seen = []
        real = R.render_png

        def spy(project, **kw):
            seen.append(kw)
            return real(project, **kw)
        R.render_png = spy
        try:
            with _Spanish():
                method_figures(p, results, factored=True, width=300,
                               height=200, translate=note_text)
        finally:
            R.render_png = real
        assert seen
        for kw in seen:
            assert kw["surfaces"][0][0] == "superficie crítica", kw
            grid = kw["grid"]
            assert grid["label"] == "factor de sobredimensionamiento mínimo"
            assert grid["critical_label"] == "centro crítico"


class TestWhoPassesIt:

    def test_the_window_does_and_the_api_does_not(self):
        flat = " ".join((_ROOT / "ogr_gui" / "main_window.py").read_text(
            encoding="utf-8").split())
        assert ("factor_report=factor_report, figures=figures, "
                "translate=note_text, method_name=method_name)") in flat
        api = (_ROOT / "ogr_api" / "ops" / "files.py").read_text(
            encoding="utf-8")
        assert "translate" not in api

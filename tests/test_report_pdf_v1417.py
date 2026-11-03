# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.417 (D351) — the PDF report, read as a reader reads it.

The fifth GUI test (H11 of ``INFORME_prueba_GUI_0.1.355.md``) found four
faults in the PDF of the demo slope:

* the creation date was the stored stamp, «2026-10-22T15:16:13.558375»: ISO,
  UTC and to the microsecond, beside a generation date in local time and
  ``dd/mm/YYYY, HH:MM:SS``;
* «File: Demo slope» was the project's NAME, and the demo had never been
  saved;
* the fonts were the standard Helvetica, not embedded and in WinAnsi: a
  viewer drew «[kN/m ]» for «[kN/m³]»;
* «Global Minimums» stood alone at the foot of page 1, and the rule under
  «Valid / Invalid Surfaces» ran past both edges of its table.

The invariants, each read from the PDF itself (QtPdf, pdfium's text layer)
or from the flowables the document laid out:

* every text the report shows is set in an embedded TrueType subset
  (DejaVu Sans, from matplotlib), and «kN/m³» and «m²» come out of the PDF
  whole;
* the creation date is in local time and in the generation date's format,
  also for an old ``.ogr`` that stored it in ISO; a free text or a bare
  date is shown as written; the stamp a new project stores keeps its form;
* «File» is the path of a saved project, and «not saved» (in Spanish «sin
  guardar») otherwise;
* no heading is the last thing on its page: the comments of the summary are
  swept from 0 to 39 lines to walk every heading over a page's foot (in
  v0.1.416, from 28 lines on, «Method: Bishop Simplified» was left behind);
* the rules and the tables fit in the frame, and the rule of a section is as
  wide as the table under it;
* the comments are one line each, not a Python list.
"""
from __future__ import annotations

import base64
import io
import os
import re
import sys
import tempfile
import zlib
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import test_report_spanish_v1355 as RS  # noqa: E402  (its model builder)

_RUN = {}


def _run():
    """The model of the Spanish report's test, computed once for this
    file: two methods on a 3 x 3 grid, with a design standard."""
    if "run" not in _RUN:
        from ogr_slip2d.analysis_runner import run_analysis
        p = RS._model()
        out = run_analysis(p)
        _RUN["run"] = (p, out.results, out.factor_report)
    return _RUN["run"]


def _pdf(project=None, **kw) -> bytes:
    import ogr_core.report.report_generator as RG
    p, results, rep = _run()
    buf = io.BytesIO()
    RG.generate_report(project or p, results, buf, factor_report=rep, **kw)
    return buf.getvalue()


def _text(raw: bytes) -> list:
    """The text of each page, as pdfium reads it."""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    data = QBuffer()
    data.setData(QByteArray(raw))
    data.open(QIODevice.ReadOnly)
    doc = QPdfDocument()
    doc.load(data)
    assert doc.status() == QPdfDocument.Status.Ready, doc.status()
    pages = [doc.getAllText(i).text() for i in range(doc.pageCount())]
    doc.close()
    return pages


def _streams(raw: bytes):
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
        data = m.group(1).strip()
        try:
            if data.endswith(b"~>"):
                data = base64.a85decode(data[:-2])
            yield zlib.decompress(data)
        except (ValueError, zlib.error):
            continue


_SHOW = re.compile(rb"/(F\d+(?:\+\d+)?) [\d.]+ Tf"
                   rb"|\((?:\\.|[^\\)])*\)\s*Tj|\]\s*TJ")


def _fonts_shown(raw: bytes) -> dict:
    """``{font resource: base font}`` of every font active when a text is
    SHOWN. A page's preamble selects /F1 (Helvetica) and writes nothing."""
    names = {}
    for body in re.findall(rb"obj\s*<<(.*?)>>\s*endobj", raw, re.S):
        base = re.search(rb"/BaseFont /([\w+-]+)", body)
        name = re.search(rb"/Name /(\w+)", body)
        if base and name:
            names[name.group(1)] = base.group(1).decode()
    shown = {}
    for data in _streams(raw):
        cur = None
        for tok in _SHOW.finditer(data):
            if tok.group(1):
                cur = tok.group(1).split(b"+")[0]
            elif cur is not None:
                shown[cur.decode()] = names.get(cur, "?")
    return shown


# ======================================================================
class TestTheFontsAreEmbedded:

    def test_every_text_is_shown_in_an_embedded_subset(self):
        raw = _pdf()
        shown = _fonts_shown(raw)
        assert shown, "no text found in the content streams"
        assert all(re.fullmatch(r"[A-Z]{6}\+DejaVuSans[\w-]*", base)
                   for base in shown.values()), shown
        assert raw.count(b"/FontFile2") >= len(set(shown.values())), shown

    def test_the_superscripts_come_out_whole(self):
        text = "\n".join(_text(_pdf()))
        assert "[kN/m³]" in text, text[:600]
        assert "m²" in text, text[:600]
        assert "[kN/m ]" not in text


class TestTheCreationDate:

    def _created(self, stamp):
        import copy
        p, _results, _rep = _run()
        q = copy.copy(p)
        q.settings = copy.deepcopy(p.settings)
        q.settings.summary.date_created = stamp
        return "\n".join(_text(_pdf(q)))

    def test_an_iso_stamp_is_shown_in_local_time(self):
        stamp = "2026-10-22T15:16:13.558375"
        local = datetime(2026, 10, 22, 15, 16, 13, 558375,
                         tzinfo=timezone.utc).astimezone()
        text = self._created(stamp)
        assert local.strftime("%d/%m/%Y, %H:%M:%S") in text, text[:400]
        assert stamp not in text

    def test_a_stamp_with_its_zone_is_read_with_it(self):
        from ogr_core.report.report_generator import local_timestamp
        local = datetime(2026, 10, 22, 13, 16, 13,
                         tzinfo=timezone.utc).astimezone()
        assert (local_timestamp("2026-10-22T15:16:13+02:00")
                == local.strftime("%d/%m/%Y, %H:%M:%S"))

    def test_free_text_and_a_bare_date_are_shown_as_written(self):
        from ogr_core.report.report_generator import local_timestamp
        for text in ("2026-10-14", "octubre de 2026", ""):
            assert local_timestamp(text) == text

    def test_a_new_project_stores_the_same_form_as_before(self):
        from ogr_core.project.project import Project
        stamp = Project().settings.summary.date_created
        assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?",
                            stamp), stamp
        utc = datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc)
        assert abs((datetime.now(timezone.utc) - utc).total_seconds()) < 600

    def test_the_file_keeps_its_stamp(self):
        from ogr_core.project.project import Project
        p, _results, _rep = _run()
        data = p.to_dict()
        data["settings"]["summary"]["date_created"] = \
            "2026-08-09T22:26:52.298148"
        again = Project.from_dict(data).to_dict()
        assert (again["settings"]["summary"]["date_created"]
                == "2026-08-09T22:26:52.298148")


class TestTheFileRow:

    def test_a_project_never_saved_says_so(self):
        p, _results, _rep = _run()
        assert getattr(p, "file_path", None) is None
        text = "\n".join(_text(_pdf()))
        assert "File not saved" in text, text[:400]
        assert "File Report" not in text

    def test_in_spanish_it_says_sin_guardar(self):
        from ogr_gui.core_messages import note_text
        with RS._Spanish():
            text = "\n".join(_text(_pdf(translate=note_text)))
        assert "Archivo sin guardar" in text, text[:400]

    def test_a_saved_project_gives_its_path(self):
        import copy
        p, _results, _rep = _run()
        q = copy.copy(p)
        with tempfile.TemporaryDirectory() as tmp:
            q.file_path = Path(tmp) / "talud.ogr"
            text = "".join(_text(_pdf(q))).replace("\n", "")
        assert str(q.file_path) in text, text[:400]


def _laid_out(project=None):
    """``[(page, flowable)]`` in the order the document placed them."""
    from reportlab.platypus import SimpleDocTemplate
    seen = []
    real = SimpleDocTemplate.afterFlowable

    def after(self, flowable):
        seen.append((self.page, flowable))
        return real(self, flowable)

    SimpleDocTemplate.afterFlowable = after
    try:
        _pdf(project)
    finally:
        SimpleDocTemplate.afterFlowable = real
    return seen


def _is_heading(f) -> bool:
    from reportlab.platypus import Paragraph
    return (isinstance(f, Paragraph) and getattr(f.style, "name", "")
            in ("OGRSection", "OGRMethod"))


def _is_rule(f) -> bool:
    return type(f).__name__ == "HRFlowable" or (
        type(f).__name__ == "Table"
        and getattr(f, "_cellvalues", None) == [[""]])


class TestNoHeadingIsLeftAtAPagesFoot:

    def test_over_a_sweep_of_the_summary(self):
        import copy
        p, _results, _rep = _run()
        q = copy.copy(p)
        q.settings = copy.deepcopy(p.settings)
        alone = {}
        # every third line: 12 pt a line walks each heading over the foot
        # of its page in steps smaller than the space a heading needs
        for n in range(0, 40, 3):
            q.settings.summary.comments = [f"line {i}" for i in range(n)]
            seen = _laid_out(q)
            for i, (page, f) in enumerate(seen):
                if not _is_heading(f):
                    continue
                nxt = next((pg for pg, g in seen[i + 1:] if not _is_rule(g)),
                           None)
                if nxt is not None and nxt != page:
                    alone.setdefault(n, []).append(f.getPlainText())
        assert not alone, alone


class TestTheRulesAndTablesFitTheFrame:

    def test_every_one_within_the_frame(self):
        from ogr_core.report.report_generator import project_width
        p, _results, _rep = _run()
        width = project_width(p)
        frame = 210 / 25.4 * 72 - 2 * 18 / 25.4 * 72 - 12
        assert abs(width - frame) < 1e-6, (width, frame)
        wide = []
        for _page, f in _laid_out():
            kind = type(f).__name__
            if kind == "Table":
                w = sum(f._colWidths)
            elif kind == "HRFlowable":
                w = f.width
            else:
                continue
            if w > width + 1e-6:
                wide.append((kind, w))
        assert not wide, (width, wide)

    def test_the_rule_is_as_wide_as_the_valid_invalid_table(self):
        seen = _laid_out()
        i = next(i for i, (_pg, f) in enumerate(seen) if _is_heading(f)
                 and f.getPlainText() == "Valid / Invalid Surfaces")
        rule = seen[i + 1][1]
        table = next(f for _pg, f in seen[i + 2:]
                     if type(f).__name__ == "Table")
        assert type(rule).__name__ == "HRFlowable", rule
        assert abs(rule.width - sum(table._colWidths)) < 1e-6


class TestTheComments:

    def test_one_line_each(self):
        import copy
        p, _results, _rep = _run()
        q = copy.copy(p)
        q.settings = copy.deepcopy(p.settings)
        q.settings.summary.comments = ["first remark", "second remark"]
        text = "\n".join(_text(_pdf(q)))
        assert "first remark" in text and "second remark" in text, text[:500]
        assert "['first remark'" not in text

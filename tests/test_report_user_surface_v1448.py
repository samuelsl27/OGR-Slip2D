# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D404 (v0.1.448) — the report says whose each method's global minimum is.

The invariant
-------------
A run's critical surface competes over every surface it analysed, the
search's and the ones the user drew (D58: v0.1.157 the circles, v0.1.427 the
polylines), so a hand-drawn surface can be the global minimum. The «Global
Minimums» block of the PDF report wrote it exactly as it writes one of the
search's: on the demo slope with a Path Search of 5 and the polyline of
``test_user_polylines_v1427``, Bishop's critical surface is the user's
(1.1789; the search alone gives 1.3834) and Corps of Engineers #2's is the
search's (1.4150), and nothing said whose either surface was. Since D424
Bishop's block also names the axis of its moments, which Corps of Engineers
#2 does not keep, but that difference comes from the method, not from who
drew the surface.

Now a row «Surface | Defined by the user», right after the factor, says it,
in the words the windows use since D401 (``surface_note``). The reference is
an identity: the row is written if and only if the result says its critical
surface is the user's (``res.is_user_surface(res.critical)``). The report
asks it through the rule the windows, the API and the back analysis ask,
``is_user_surface_of``, which moved to the core for this (the core does not
import the engine), so a result without the user's list writes no row and
does not fail. «Valid / Invalid Surfaces» still counts the search (D58), and
a report of a run without surfaces of the user is the one it was
(``_V1354`` of ``test_report_spanish_v1355``).

Measured cost: about 3 s on the development laptop. The two runs take 1.2 s
of it, each computed once for the file (a Path Search of 5 with two methods,
and the coarse grid of ``test_user_surfaces_v1157``, 294 circles, with
Bishop). The first report takes 0.45 s, for its fonts, and each one after it
about 0.1 s.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

#: The row, in English and in the windows' Spanish.
_ROW = ["Surface", "Defined by the user"]
_FILA = ["Superficie", "Definida por el usuario"]

_RUNS: dict = {}


def _polyline_run():
    """The ficha's case: the demo slope, Path Search of 5, Bishop and Corps
    of Engineers #2, and the polyline of ``test_user_polylines_v1427``."""
    if "polyline" not in _RUNS:
        from test_user_polylines_v1427 import _WINNER

        from examples.quick_slope import build_demo_slope
        from ogr_slip2d.analysis_runner import run_analysis
        from ogr_slip2d.surface import UserPolylineSurface
        p = build_demo_slope()
        s = p.settings.search
        s.surface_type, s.search_method, s.path_num_surfaces = (
            "non_circular", "path", 5)
        p.settings.methods.enabled_methods = ["bishop_simplified",
                                              "corps_engineers_2"]
        p.user_polylines = [UserPolylineSurface.from_points(_WINNER)]
        _RUNS["polyline"] = (p, run_analysis(p).results)
    return _RUNS["polyline"]


def _circle_run():
    """The circle of ``test_user_surfaces_v1157`` on its coarse grid, with
    Bishop: the hand-placed circle beats the search."""
    if "circle" not in _RUNS:
        from test_user_surfaces_v1157 import _GRID, _WINNER

        from examples.quick_slope import build_demo_slope
        from ogr_slip2d import BishopSimplified, GridSearch
        from ogr_slip2d.surface import SlipCircle
        p = build_demo_slope()
        p.user_surfaces = [SlipCircle(**_WINNER)]
        sr = GridSearch(method=BishopSimplified(), **_GRID).run(p)
        _RUNS["circle"] = (p, {"bishop_simplified": sr})
    return _RUNS["circle"]


def _capture(project, results, **kw):
    """The paragraphs the report writes, bold taken off, in order."""
    import ogr_core.report.report_generator as RG
    said = []
    real = RG.Paragraph

    class Par(real):
        def __init__(self, text, *a, **k):
            said.append(str(text).replace("<b>", "").replace("</b>", ""))
            super().__init__(text, *a, **k)

    RG.Paragraph = Par
    try:
        with tempfile.TemporaryDirectory() as d:
            RG.generate_report(project, results, os.path.join(d, "r.pdf"),
                               **kw)
    finally:
        RG.Paragraph = real
    return said


def _block(said, heading, section=("Global Minimums", "Mínimos globales")):
    """One method's rows in «Global Minimums»: its heading and what follows,
    up to the next heading or section."""
    start = next(i for i, t in enumerate(said) if t in section)
    i = said.index(heading, start)
    out = [said[i]]
    for t in said[i + 1:]:
        if t.startswith(("Method: ", "Método: ")) or t in (
                "Global Minimum Coordinates",
                "Coordenadas de los mínimos globales",
                "Valid / Invalid Surfaces",
                "Superficies válidas / inválidas"):
            break
        out.append(t)
    return out


def _has_row(block, row=_ROW) -> bool:
    return any(block[k:k + 2] == row for k in range(len(block) - 1))


class _Spanish:
    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self._before = current_language()
        set_language("es")

    def __exit__(self, *_exc):
        from ogr_gui.i18n import set_language
        set_language(self._before)


# ======================================================================
class TestTheFichasCase:

    def test_the_premise_one_critical_of_each(self):
        _p, results = _polyline_run()
        bishop, corps = (results["bishop_simplified"],
                         results["corps_engineers_2"])
        assert bishop.is_user_surface(bishop.critical)
        assert "%.4f" % bishop.critical.fos == "1.1789"
        assert not corps.is_user_surface(corps.critical)
        assert "%.4f" % corps.critical.fos == "1.4150"

    def test_the_row_under_bishop_right_after_its_factor(self):
        p, results = _polyline_run()
        block = _block(_capture(p, results), "Method: Bishop Simplified")
        assert block[1:5] == ["Factor of Safety (FS)", "1.1789"] + _ROW, \
            block

    def test_no_row_under_the_searchs_surface(self):
        p, results = _polyline_run()
        block = _block(_capture(p, results), "Method: Corps of Engineers #2")
        assert block[1:3] == ["Factor of Safety (FS)", "1.4150"], block
        assert not _has_row(block), block

    def test_the_row_if_and_only_if_the_result_says_so(self):
        from ogr_core.report.report_generator import _method_name
        p, results = _polyline_run()
        said = _capture(p, results)
        for mid, r in results.items():
            block = _block(said, "Method: %s" % _method_name(mid))
            assert _has_row(block) == r.is_user_surface(r.critical), mid

    def test_in_spanish(self):
        from ogr_gui.core_messages import note_text
        from ogr_gui.labels import method_name
        p, results = _polyline_run()
        with _Spanish():
            said = _capture(p, results, translate=note_text,
                            method_name=method_name)
            bishop = method_name("bishop_simplified")
            corps = method_name("corps_engineers_2")
        mine = _block(said, "Método: " + bishop)
        assert mine[1:5] == ["Factor de seguridad (FS)", "1.1789"] + _FILA, \
            mine
        assert not _has_row(_block(said, "Método: " + corps), _FILA)
        assert not any("Defined by the user" in t for t in said)


class TestACircleOfTheUser:

    def test_the_premise(self):
        _p, results = _circle_run()
        sr = results["bishop_simplified"]
        assert sr.is_user_surface(sr.critical)

    def test_the_row_under_its_block(self):
        p, results = _circle_run()
        block = _block(_capture(p, results), "Method: Bishop Simplified")
        assert block[3:5] == _ROW and block[5] == "Centre", block


class TestOneRuleForTheReportAndTheWindows:
    """The report asks the rule the windows, the API and the back analysis
    ask (``is_user_surface_of``, in the core since this version, the engine
    re-exporting it). The review of 0.1.448 found the first draft asking the
    result's own method instead: a stand-in with the user's list read «Defined
    by the user» in the windows and not in the report. Now both read it the
    same, and a stand-in without the list writes no row and does not fail."""

    @staticmethod
    def _double(with_users_list: bool):
        """Bishop's result of the ficha's run as a stand-in: its critical
        surface and counts, its population, and the user's list or not."""
        _p, results = _polyline_run()
        real = results["bishop_simplified"]
        double = SimpleNamespace(
            critical=real.critical, valid_count=real.valid_count,
            invalid_count=real.invalid_count, attempts=real.attempts,
            evaluations=real.evaluations)
        if with_users_list:
            double.user_evaluations = real.user_evaluations
        return double

    def test_a_double_with_the_users_list_reads_as_the_windows_read_it(self):
        from ogr_gui.core_messages import surface_note
        p, _results = _polyline_run()
        double = self._double(True)
        block = _block(_capture(p, {"bishop_simplified": double}),
                       "Method: Bishop Simplified")
        assert block[3:5] == _ROW, block
        assert surface_note(double, double.critical)[0] == _ROW[1]

    def test_a_double_without_it_writes_no_row_and_does_not_fail(self):
        p, _results = _polyline_run()
        double = self._double(False)
        block = _block(_capture(p, {"bishop_simplified": double}),
                       "Method: Bishop Simplified")
        assert block[1:3] == ["Factor of Safety (FS)", "1.1789"], block
        assert not _has_row(block), block

    def test_the_engine_hands_out_the_cores_rule(self):
        import ogr_core.project.user_surfaces as core
        import ogr_slip2d.search as engine
        assert engine.is_user_surface_of is core.is_user_surface_of


class TestTheCountsStayTheSearchs:
    """«Valid / Invalid Surfaces» counts the search's population (D58): the
    user's surface that the block now names is not added to it."""

    @staticmethod
    def _counts(project, results) -> dict:
        import ogr_core.report.report_generator as RG
        rows, real = [], RG.Table

        class Tab(real):
            def __init__(self, data, *a, **k):
                if data and list(data[0][:3]) == ["Method", "Valid",
                                                  "Invalid"]:
                    rows.extend(list(r) for r in data[1:])
                super().__init__(data, *a, **k)

        RG.Table = Tab
        try:
            with tempfile.TemporaryDirectory() as d:
                RG.generate_report(project, results,
                                   os.path.join(d, "r.pdf"))
        finally:
            RG.Table = real
        return {r[0]: r[1:4] for r in rows}

    def test_valid_and_total_are_the_searchs(self):
        p, results = _polyline_run()
        counts = self._counts(p, results)
        for mid, name in (("bishop_simplified", "Bishop Simplified"),
                          ("corps_engineers_2", "Corps of Engineers #2")):
            r = results[mid]
            users = sum(1 for e in r.user_evaluations if e.is_valid)
            assert users == 1, (mid, users)     # the premise
            assert counts[name] == [str(r.valid_count), str(r.invalid_count),
                                    str(r.total_count)], (name, counts)


class TestTheWords:
    """The core's ``T()`` texts are not in the census of the interface's
    strings: their Spanish is checked here. Both words were already the
    windows' (D401's «Defined by the user», and «Surface»)."""

    def test_both_have_their_spanish(self):
        from ogr_gui.core_messages import note_text
        with _Spanish():
            assert [note_text(t) for t in _ROW] == _FILA

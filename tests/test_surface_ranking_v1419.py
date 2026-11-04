# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.419 (D361) — every list of surfaces is in the order the critical one
is chosen in: the admissible surfaces first, then the ones the checks
rejected, each group by its score.

The sixth GUI test (H9, H10 of ``INFORME_prueba_GUI_0.1.357.md``) saw the
results panel head «Critical FS: 0.946» over a first row of 0.7911,
highlighted as the critical one: a surface the m-alpha check had rejected.
``SearchResult.top_n`` sorted every converged surface by its factor, and
``critical`` skips the inadmissible ones; Interpret's *Surfaces* table and
the API's ``top`` and ``rank`` read ``top_n``. By the owner's decision
(2026-11-03) the rule is ``critical``'s, in the engine, and the rejected
surfaces stay in the tables after the admissible ones, marked with their
reason.

The invariants:

* **the law**, on pools built by hand: ``top_n`` is the admissible
  surfaces by score and then the rest by score, and ``top_n(1)[0] is
  critical`` — also when none is admissible, on a tie and under the Ky
  objective;
* **on a real pair** the engine evaluates and screens itself (the demo
  slope, Bishop, two non-circular surfaces: an admissible one at FS 1.4135
  and a lower one, FS 0.8621, that the m-alpha check rejects on two
  slices): the panel and Interpret list the admissible one first, in bold
  as the critical, and the other second, greyed, with its reason in
  Spanish; a click on the first row picks the critical; the centre and the
  radius of a surface that is not a circle read «—», in both tables and in
  the summary;
* **the API**: ``results_get(view="top")`` in that order with each
  surface's ``admissible``, and ``results_query(view="slices", rank=1)``
  reads the critical surface.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_PAIR = {}

#: the two non-circular surfaces of the demo slope (crest y = 25 for
#: x < 25, toe y = 15 for x > 35): a shallow one, and one whose exit
#: climbs at 74 degrees, which m-alpha screens out
_SHALLOW = [(14, 25), (24, 18), (34, 14.5), (38, 15)]
_STEEP = [(12, 25), (20, 14), (35, 10), (36.5, 15)]


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _pair():
    """``(project, admissible, rejected)``: two surfaces of the demo slope
    evaluated with Bishop by the engine, which screens them itself."""
    if "pair" not in _PAIR:
        from ogr_core.geometry import Polyline, Vertex
        from ogr_core.project.demo import build_demo_project
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        from ogr_slip2d.surface import SlipSurface
        p = build_demo_project()
        p.settings.methods.enabled_methods = ["bishop_simplified"]
        out = []
        for pts in (_SHALLOW, _STEEP):
            surf = SlipSurface(Polyline(
                vertices=[Vertex(x, y) for x, y in pts]))
            out.append(evaluate_surfaces(p, surf, ["bishop_simplified"])
                       .results["bishop_simplified"])
        _PAIR["pair"] = (p, out[0], out[1])
    return _PAIR["pair"]


def _search(*results, objective=None):
    from ogr_slip2d.search import SearchResult
    sr = SearchResult(method_id="bishop_simplified",
                      evaluations=list(results),
                      valid_count=sum(1 for r in results if r.is_valid))
    if objective is not None:
        sr.objective = objective
    return sr


def _result(fos, admissible=True, ky=None):
    from ogr_slip2d.methods.base import LEMResult
    r = LEMResult(fos=fos, converged=True, iterations=1,
                  method_id="bishop_simplified", surface=None, slices=None)
    r.admissible = admissible
    if ky is not None:
        r.details = {"ky": ky}
    return r


# ======================================================================
class TestTheLaw:

    def test_admissible_first_each_group_by_score(self):
        a = [_result(f) for f in (1.3, 1.1, 1.2)]
        b = [_result(f, admissible=False) for f in (0.7, 0.9)]
        sr = _search(b[0], a[0], b[1], a[1], a[2])
        top = sr.top_n(10)
        assert [r.fos for r in top] == [1.1, 1.2, 1.3, 0.7, 0.9]
        assert top[0] is sr.critical

    def test_none_admissible_the_critical_is_still_first(self):
        b = [_result(f, admissible=False) for f in (0.9, 0.7, 0.8)]
        sr = _search(*b)
        assert sr.top_n(1)[0] is sr.critical
        assert sr.critical.fos == 0.7

    def test_a_tie_is_broken_as_critical_breaks_it(self):
        a, b = _result(1.0), _result(1.0)
        sr = _search(_result(0.5, admissible=False), a, b)
        assert sr.top_n(1)[0] is sr.critical is a

    def test_under_the_ky_objective(self):
        from ogr_slip2d.search import OBJECTIVE_KY
        a = _result(1.2, ky=0.20)
        b = _result(1.1, ky=0.12, admissible=False)
        c = _result(1.3, ky=0.25)
        sr = _search(b, c, a, objective=OBJECTIVE_KY)
        assert sr.top_n(3) == [a, c, b]
        assert sr.top_n(1)[0] is sr.critical is a

    def test_invalid_surfaces_are_not_listed(self):
        bad = _result(0.4)
        bad.error_message = "vetoed"
        sr = _search(bad, _result(1.0))
        assert [r.fos for r in sr.top_n(10)] == [1.0]


class TestTheRealPair:

    def test_the_engine_screens_the_lower_one(self):
        _p, ok, rejected = _pair()
        assert ok.is_valid and ok.admissible
        assert rejected.is_valid and not rejected.admissible
        assert math.isclose(ok.fos, 1.4134927355114606, rel_tol=1e-9)
        assert math.isclose(rejected.fos, 0.8621129506601936, rel_tol=1e-9)
        sr = _search(rejected, ok)
        assert sr.critical is ok
        assert sr.top_n(2) == [ok, rejected]


def _spanish():
    import contextlib

    @contextlib.contextmanager
    def ctx():
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        set_language("es")
        try:
            yield
        finally:
            set_language(before)
    return ctx()


class TestTheResultsPanel:

    def test_the_critical_first_and_the_rejected_marked(self):
        from PySide6.QtGui import QFont
        from ogr_gui.core_messages import invalid_label, invalid_text
        from ogr_gui.widgets.results_dock import ResultsDock
        _app()
        _p, ok, rejected = _pair()
        sr = _search(rejected, ok)
        with _spanish():
            dock = ResultsDock()
            try:
                dock.show_result(sr)
                t = dock.table
                assert t.rowCount() == 2
                assert t.item(0, 1).text() == "%.4f" % ok.fos
                assert t.item(0, 1).font().weight() >= QFont.Bold
                assert t.item(1, 1).text() == "%.4f" % rejected.fos
                assert not t.item(1, 1).font().bold()
                assert t.item(0, 6).text() == ""
                note = t.item(1, 6)
                assert note.text() == invalid_label(rejected) != "", \
                    note.text()
                assert note.toolTip() == invalid_text(rejected)
                # in Spanish, by its code («m_alpha < 0.2 en … dovela(s)»,
                # the catalogue's text that test_core_messages_v1333 fixes)
                assert "dovela" in note.text(), note.text()
                for row in range(2):
                    assert [t.item(row, c).text() for c in (3, 4, 5)] == \
                        ["—", "—", "—"]
            finally:
                dock.deleteLater()


class TestInterpret:

    def test_the_table_the_pick_and_the_summary(self):
        from ogr_gui.interpret_window import InterpretWindow
        _app()
        p, ok, rejected = _pair()
        sr = _search(rejected, ok)
        w = InterpretWindow(p, {"bishop_simplified": sr}, None)
        try:
            t = w.results_dock.table
            assert t.item(0, 1).text() == "%.4f" % ok.fos
            assert t.item(1, 1).text() == "%.4f" % rejected.fos
            assert t.item(1, 6).text() != ""
            assert [t.item(0, c).text() for c in (3, 4, 5)] == \
                ["—", "—", "—"]
            w._on_surface_picked(0)
            assert w._selected_result is ok
            summary = w.summary_dock.label.text()
            assert "(—, —)" in summary and "0.00" not in summary, summary
        finally:
            w.close()
            w.deleteLater()


class TestTheAPI:

    def _stored(self):
        from ogr_api import Workspace, call
        p, ok, rejected = _pair()
        ws = Workspace()
        pid = call(ws, "project_new", name="D361")["project_id"]
        handle = ws.get(pid)
        res = ws.store_result(handle, "analysis", {"methods": {}},
                              model_hash="x",
                              payload={"results": {
                                  "bishop_simplified": _search(rejected, ok)},
                                  "factor_report": None})
        return ws, res.id, ok, rejected

    def test_top_and_rank_one(self):
        from ogr_api import call
        ws, rid, ok, rejected = self._stored()
        try:
            top = call(ws, "results_get", result_id=rid, view="top",
                       n=5)["top"]["bishop_simplified"]
            assert [round(x["fos"], 6) for x in top] == \
                [round(ok.fos, 6), round(rejected.fos, 6)]
            assert [x["admissible"] for x in top] == [True, False]
            first = call(ws, "results_query", result_id=rid, view="slices",
                         rank=1)["surface"]
            # the API rounds a factor to 6 decimals
            assert abs(first["fos"] - ok.fos) < 1e-6, (first["fos"], ok.fos)
        finally:
            ws.shutdown()

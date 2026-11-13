# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.443 (D401) — the results panel and Interpret show the critical surface
the user drew, say whose it is, and Interpret's back analysis says which
surface it priced.

The invariant: what a window says of a run is said of EVERY surface the run
analysed, the ones the user drew by hand included; the counts stay the
search's (D58), so a surface of the user is labelled wherever it appears.
Until this version the two windows looked at the search's population alone:
with a focus that rejects every surface of the search and a valid polyline of
the user (demo slope, Janbu, F = 1.1232, the critical surface of the run),
the panel said «No results yet.», the summary «No results to display.», the
result table «No valid surfaces.», and the CSV had no rows. Without the
focus the panel highlighted that surface without saying whose it was, and
the result table and the CSV left it out.

What is anchored here:

* the definition: the surface the windows show as critical IS
  ``SearchResult.critical``, and the surfaces they list are the valid ones of
  ``evaluations`` and ``user_evaluations``, the search's first and in their
  order; the label goes by identity (``is_user_surface_of``);
* the two tables say the same of one surface (one function,
  ``surface_note``), also of one a check rejected;
* the back analysis of Interpret prices the run's critical surface, and says
  so on a line of its own: with a circle of the user that is NOT critical it
  publishes 145.99 kN/m, where the run's back analysis publishes 166.33 on
  the user's circle (demo slope, Janbu, target 1.5, elevation 20). The force
  is ``required_force_of_result`` on that surface, to the last bit in this
  process: the label says which surface, it does not change it;
* without surfaces of the user the windows are the ones of 0.1.442.
  ``_V1442`` is MEASURED on that tree (b5a4d27) by running this file's
  ``_capture()`` there (``_auditoria/P10_herramientas/capture_d401.py`` of the
  bench); it is not what this code prints. Texts are compared exactly, and a
  cell that is a number with decimals to 1e-6 (the CSV writes coordinates at
  full precision, and the suite also runs on another machine). The one line
  that changes on purpose, the back analysis's, is spelled out in its test.

Five small in-process runs and five Interpret windows, built once and shared.
"""
from __future__ import annotations

import ast
import copy
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace as NS

_ROOT = Path(__file__).resolve().parent.parent
_J, _B = "janbu_simplified", "bishop_simplified"
#: The polyline of ``tests/test_back_analysis_user_surfaces_v1428.py``: added
#: to the demo slope's Path search of 5 it is the critical surface of the run.
_WINNER = [(19.0, 25.0), (25.0, 18.0), (31.0, 14.5), (37.0, 15.0)]
#: The one of ``tests/test_user_polylines_v1427.py`` that m-alpha rejects
#: under Bishop.
_STEEP = [(19.0, 25.0), (31.0, 8.0), (34.0, 16.0)]
_TARGET, _ELEVATION = 1.5, 20.0
_USERS = {"en": "Defined by the user", "es": "Definida por el usuario"}


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@contextmanager
def _language(code):
    from ogr_gui.i18n import current_language, set_language
    kept = current_language()
    set_language(code)
    try:
        yield
    finally:
        set_language(kept)


@contextmanager
def _swapped(owner, name, value):
    """``owner.name`` replaced and put back, an instance attribute removed
    again if it was not there."""
    own = vars(owner) if not isinstance(owner, type) else None
    had = own is None or name in own
    kept = getattr(owner, name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        if had:
            setattr(owner, name, kept)
        else:
            delattr(owner, name)


# ----------------------------------------------------------------------
# The runs
# ----------------------------------------------------------------------
def _path_project(method, polylines, focus=False):
    from examples.quick_slope import build_demo_slope
    from ogr_core.geometry.focus import FocusKind, FocusObject
    from ogr_slip2d.surface import UserPolylineSurface
    p = build_demo_slope()
    s = p.settings.search
    s.surface_type, s.search_method = "non_circular", "path"
    s.path_num_surfaces = 5
    s.optimize_enabled = False
    p.settings.methods.enabled_methods = [method]
    if focus:
        # a point no surface passes through: the search keeps nothing, as
        # in ``tests/test_newmark_user_surfaces_v1429.py``
        p.focus_objects = [FocusObject(kind=FocusKind.POINT,
                                       points=[(500.0, -500.0)],
                                       tolerance=0.01)]
    p.user_polylines = [UserPolylineSurface.from_points(q)
                        for q in polylines]
    return p


def _grid_project(with_circle):
    """The 64-circle grid of ``test_back_analysis_user_surfaces_v1428``, with
    its user circle, which needs more force than the grid's critical one and
    is not the critical surface."""
    from examples.quick_slope import build_demo_slope
    from ogr_slip2d.surface import SlipCircle
    p = build_demo_slope()
    s = p.settings.search
    s.surface_type, s.search_method = "circular", "grid"
    s.grid_x_min, s.grid_x_max = 30.0, 45.0
    s.grid_y_min, s.grid_y_max = 40.0, 55.0
    s.grid_nx = s.grid_ny = 3
    s.radius_increment = 3
    p.settings.methods.enabled_methods = [_J]
    ba = p.settings.back_analysis
    ba.method_id, ba.target_fos, ba.elevation = _J, _TARGET, _ELEVATION
    if with_circle:
        p.user_surfaces = [SlipCircle(centre_x=36.0, centre_y=34.0,
                                      radius=20.0)]
    return p


_CASES = {
    "focus": lambda: _path_project(_J, [_WINNER], focus=True),
    "path+user": lambda: _path_project(_J, [_WINNER]),
    "steep": lambda: _path_project(_B, [_WINNER, _STEEP]),
    "circle": lambda: _grid_project(True),
    "grid": lambda: _grid_project(False),
}
_RUNS: dict = {}
_WINDOWS: dict = {}
#: The dock whose table a helper last handed out, one of each kind: a table
#: dies with its dock, so the dock is kept until the next of its kind. A
#: slot here and not an attribute on the table, which would tie two Qt
#: objects in a cycle for the collector (v0.1.302).
_DOCKS: dict = {}


def _run(name):
    """``(project, search result)`` of a case, computed once."""
    if name not in _RUNS:
        from ogr_slip2d.analysis_runner import run_analysis
        p = _CASES[name]()
        mid = p.settings.methods.enabled_methods[0]
        _RUNS[name] = (p, run_analysis(p).results[mid])
    return _RUNS[name]


def _window(name):
    """The Interpret window of a case, built once (in English). Never shown
    and not closed: closing one and asking it again afterwards hung the run
    (tried in the review of 0.1.443)."""
    if name not in _WINDOWS:
        from ogr_gui.interpret_window import InterpretWindow
        _app()
        p, sr = _run(name)
        with _language("en"):
            _WINDOWS[name] = InterpretWindow(p, {sr.method_id: sr})
    return _WINDOWS[name]


# ----------------------------------------------------------------------
# What a window says, read without opening anything modal
# ----------------------------------------------------------------------
def _cells(table) -> list:
    return [[(table.item(r, c).text() if table.item(r, c) else None)
             for c in range(table.columnCount())]
            for r in range(table.rowCount())]


def _headers(table) -> list:
    return [table.horizontalHeaderItem(c).text()
            for c in range(table.columnCount())]


def _panel(name):
    """The results panel showing a case: ``(header, table)``."""
    from ogr_gui.widgets.results_dock import ResultsDock
    _app()
    dock = ResultsDock()
    dock.show_result(_run(name)[1])
    _DOCKS["panel"] = dock
    return dock.header_label.text(), dock.table


def _summary(name) -> str:
    import ogr_gui.interpret_window as iw
    _app()
    p, sr = _run(name)
    dock = iw._SummaryDock()
    dock.show_result(sr, p)
    return dock.label.text()


def _surfaces(name):
    """Interpret's Surfaces table showing a case."""
    import ogr_gui.interpret_window as iw
    _app()
    dock = iw._ResultsTableDock()
    dock.show_result(_run(name)[1])
    _DOCKS["surfaces"] = dock
    return dock.table


def _result_table(name, tips=False):
    """Interpret's Result Table (non modal): ``(headers, rows, said)``, the
    rows in the order of their «#» whatever order the table shows them in
    (it sorts that column as text). With ``tips``, the tooltip of each
    row's last cell instead of what was said."""
    from PySide6.QtWidgets import QTableWidget
    w = _window(name)
    said = []
    with _swapped(w, "_info", lambda text, *a: said.append(text)):
        dlg = w._add_result_table()
    if dlg is None:
        return [], [], said
    try:
        table = dlg.findChild(QTableWidget)
        rows = _cells(table)
        order = sorted(range(len(rows)), key=lambda i: int(rows[i][0]))
        last = table.columnCount() - 1
        return (_headers(table), [rows[i] for i in order],
                [table.item(i, last).toolTip() for i in order] if tips
                else said)
    finally:
        dlg.close()


def _refuse(*_a, **_k):
    raise AssertionError("a modal box was about to open")


def _csv(name) -> list:
    """The lines Interpret's Export Data (CSV) writes, each as its cells.
    Its error path is a modal box: replaced, so a failure in the export
    fails the test instead of waiting for a click nobody can give."""
    import ogr_gui.interpret_window as iw
    from PySide6.QtWidgets import QMessageBox
    w = _window(name)
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "data.csv")
        with _swapped(iw, "get_save_file_name", lambda *a, **k: (path, "")), \
                _swapped(QMessageBox, "critical", staticmethod(_refuse)):
            w._export_data_csv()
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as fh:
            return [line.split(",") for line in fh.read().splitlines()]


def _back_analysis(name, target=_TARGET, elevation=_ELEVATION) -> list:
    """What Interpret's back analysis says, with its two inputs answered."""
    from PySide6.QtWidgets import QInputDialog
    w = _window(name)
    answers = iter([(target, True), (elevation, True)])
    said = []
    with _swapped(QInputDialog, "getDouble",
                  staticmethod(lambda *a, **k: next(answers))), \
            _swapped(w, "_info", lambda text, *a: said.append(text)):
        w._back_analysis_report()
    return said


def _filter(name):
    """What the Filter Surfaces dialog shows as it opens, with its ``exec``
    replaced (nothing modal): ``(M, lowest, said)`` -- the M of its
    «Showing N of M surfaces.», the lower end of its prefilled range, and
    what the window said instead when it had nothing to filter."""
    from PySide6.QtWidgets import QDialog, QDoubleSpinBox, QLabel
    w = _window(name)
    seen, said = {}, []

    def opened(dlg):
        shown = [m for m in (re.fullmatch(r"Showing (\d+) of (\d+) surfaces\.",
                                          lab.text())
                             for lab in dlg.findChildren(QLabel)) if m]
        seen["m"] = int(shown[0].group(2)) if len(shown) == 1 else None
        seen["low"] = dlg.findChildren(QDoubleSpinBox)[0].value()
        return QDialog.DialogCode.Rejected

    with _language("en"), _swapped(QDialog, "exec", opened), \
            _swapped(w, "_info", lambda text, *a: said.append(text)):
        w._filter_surfaces()
    return seen.get("m"), seen.get("low"), said


def _valid_of(window) -> list:
    """What the CSV, the filter and the result table of ``window`` list. A
    tree without ``_valid_surfaces`` listed the search's valid surfaces."""
    own = getattr(window, "_valid_surfaces", None)
    if own is not None:
        return own()
    return [r for r in window.search_result.evaluations if r.is_valid]


def _note_of(search_result, res) -> tuple:
    """``surface_note``. A tree without it wrote the reason of a rejected
    surface, and nothing else, in each table."""
    from ogr_gui import core_messages as cm
    own = getattr(cm, "surface_note", None)
    if own is not None:
        return own(search_result, res)
    if getattr(res, "admissible", True):
        return "", ""
    return cm.invalid_label(res), cm.invalid_text(res)


def _is_number(text) -> bool:
    return bool(isinstance(text, str)
                and re.fullmatch(r"-?\d+\.\d+(e-?\d+)?", text))


def _same(got, want) -> bool:
    """Two captured values: texts exactly, lists item by item, and a cell
    that is a number with decimals to 1e-6."""
    if isinstance(want, list):
        return (isinstance(got, list) and len(got) == len(want)
                and all(_same(g, w) for g, w in zip(got, want)))
    if _is_number(want) and _is_number(got):
        return abs(float(got) - float(want)) <= 1e-6
    return got == want and type(got) is type(want)


def _capture():
    """What the windows say of the run WITHOUT surfaces of the user (the
    64-circle grid, Janbu), in English. Run on the tree of 0.1.442 for
    ``_V1442`` (see the header)."""
    with _language("en"):
        header, table = _panel("grid")
        heads, rows, said = _result_table("grid")
        csv = _csv("grid")
        return {
            "panel.header": header,
            "panel.table": [_headers(table), len(_cells(table)),
                            _cells(table)[:3]],
            "summary": _summary("grid"),
            "surfaces.table": [_headers(_surfaces("grid")),
                               len(_cells(_surfaces("grid"))),
                               _cells(_surfaces("grid"))[:3]],
            "result_table": [heads, len(rows), rows[:3], said],
            "filter": list(_filter("grid")),
            "csv": [len(csv), csv[:4]],
            "back_analysis": _back_analysis("grid"),
        }


#: MEASURED on 0.1.442 (b5a4d27) with ``_capture()``; see the header.
_V1442 = {'panel.header': 'Method: <b>Janbu Simplified</b>   Valid: 52   '
                 'Critical FoS: <b>1.146</b>',
 'panel.table': [['#', 'FoS', 'Method', 'Centre X', 'Centre Y',
                  'Radius', 'Note'],
                 50,
                 [['1', '1.1461', 'Janbu Simplified', '40.00',
                   '40.00', '24.93', ''],
                  ['2', '1.2727', 'Janbu Simplified', '40.00',
                   '45.00', '29.30', ''],
                  ['3', '1.2774', 'Janbu Simplified', '45.00',
                   '50.00', '35.19', '']]],
 'summary': 'Method: <b>Janbu Simplified</b><br>Valid surfaces: '
            '<b>52</b> / 64<br>Generation attempts: '
            '64<br><br><b>Critical surface</b><br>Factor of safety '
            "= <span style='color:#c0392b; "
            "font-size:14pt;'><b>1.146</b></span><br>Iterations: "
            '4<br>Centre: (40.00, 40.00)<br>Radius: 24.93 m',
 'surfaces.table': [['#', 'FoS', 'Method', 'Centre X', 'Centre Y',
                     'Radius', 'Note'],
                    52,
                    [['1', '1.1461', 'Janbu Simplified', '40.00',
                      '40.00', '24.93', ''],
                     ['2', '1.2727', 'Janbu Simplified', '40.00',
                      '45.00', '29.30', ''],
                     ['3', '1.2774', 'Janbu Simplified', '45.00',
                      '50.00', '35.19', '']]],
 'result_table': [['#', 'FoS', 'Type', 'Area (m²)', 'Slices'], 52,
                  [['0', '5.2543', 'circle', '1.5', '25'],
                   ['1', '1.9273', 'circle', '57.3', '25'],
                   ['2', '1.7935', 'circle', '179.7', '25']],
                  []],
 'filter': [52, 1.146, []],
 'csv': [53,
         [['rank', 'fos', 'method', 'centre_x', 'centre_y',
           'radius', 'x_left', 'x_right', 'iterations',
           'converged'],
          ['1', '1.146092', 'janbu_simplified', '40.0', '40.0',
           '24.926406825645888', '20.092067981892097',
           '34.255424280863785', '4', 'True'],
          ['2', '1.272664', 'janbu_simplified', '40.0', '45.0',
           '29.304804791094465', '18.581046154301717',
           '33.596656790316466', '4', 'True'],
          ['3', '1.277371', 'janbu_simplified', '45.0', '50.0',
           '35.18835316571922', '20.236716725858383',
           '33.123563397358296', '4', 'True']]],
 'back_analysis': ['Required support force for FS = 1.5\n'
                   '\n'
                   'active: 97.33\n'
                   'passive: 145.99\n'
                   '\n'
                   'The passive value is the larger and therefore '
                   'the conservative one for design.']}


# ======================================================================
class TestARunWhoseOnlySurfaceIsTheUsers:
    """The focus rejects every surface of the search; the polyline of the
    user is valid and is the critical surface of the run."""

    def test_the_case_is_the_one_of_the_ficha(self):
        _p, sr = _run("focus")
        assert sr.evaluations == [] and len(sr.user_evaluations) == 1
        assert sr.critical is sr.user_evaluations[0]
        assert abs(sr.critical.fos - 1.123199) < 2e-6
        assert sr.valid_count == 0

    def test_the_panel_gives_it_and_says_whose_it_is(self):
        _p, sr = _run("focus")
        for code, label, valid in (
                ("en", "(surface defined by the user)", "Valid: 0"),
                ("es", "(superficie definida por el usuario)", "Válidas: 0")):
            with _language(code):
                header, table = _panel("focus")
                assert f"<b>{sr.critical.fos:.3f}</b> {label}" in header
                # the count is still the search's (D58)
                assert valid in header, header
                rows = _cells(table)
                assert len(rows) == 1
                assert rows[0][1] == f"{sr.critical.fos:.4f}"
                assert rows[0][6] == _USERS[code]

    def test_the_summary_gives_it_and_says_whose_it_is(self):
        _p, sr = _run("focus")
        for code, heading in (
                ("en", "<b>Critical surface, defined by the user</b>"),
                ("es", "<b>Superficie crítica, definida por el usuario</b>")):
            with _language(code):
                text = _summary("focus")
                assert heading in text, text
                assert f"<b>{sr.critical.fos:.3f}</b>" in text
        with _language("en"):
            assert "Valid surfaces: <b>0</b>" in _summary("focus")

    def test_the_result_table_and_the_csv_have_it(self):
        _p, sr = _run("focus")
        with _language("en"):
            heads, rows, said = _result_table("focus")
            assert said == []
            assert heads[-1] == "Note" and len(heads) == 6
            assert len(rows) == 1
            assert rows[0][1] == f"{sr.critical.fos:.4f}"
            assert rows[0][5] == _USERS["en"]
            head, *lines = _csv("focus")
        assert head[-1] == "user_defined" and len(head) == 11
        assert len(lines) == 1 and len(lines[0]) == len(head)
        assert lines[0][1] == f"{sr.critical.fos:.6f}"
        assert lines[0][-1] == "1"

    def test_the_filter_has_something_to_filter(self):
        _p, sr = _run("focus")
        assert _valid_of(_window("focus")) == [sr.critical]
        m, low, said = _filter("focus")
        assert said == [] and m == 1
        assert abs(low - round(sr.critical.fos, 3)) < 1e-9

    def test_a_surface_of_the_user_without_a_factor_is_not_no_results(self):
        """The run analysed a surface and it has no factor: «no valid
        surfaces», with the search's count, and not «no results»."""
        from ogr_gui.widgets.results_dock import ResultsDock
        import ogr_gui.interpret_window as iw
        _app()
        _p, sr = _run("focus")
        bad = copy.copy(sr.user_evaluations[0])
        bad.converged = False
        assert not bad.is_valid
        result = NS(evaluations=[], user_evaluations=[bad], critical=None,
                    method_id=_J, objective="fos", valid_count=0,
                    invalid_count=27, top_n=lambda n: [])
        with _language("en"):
            dock = ResultsDock()
            dock.show_result(result)
            assert dock.header_label.text() == (
                "Method: Janbu Simplified. No valid surfaces found "
                "(27 invalid).")
            summary = iw._SummaryDock()
            summary.show_result(result)
            assert "No valid surfaces (27 invalid)" in summary.label.text()

    def test_a_run_with_nothing_at_all_still_says_so(self):
        from ogr_gui.widgets.results_dock import ResultsDock
        import ogr_gui.interpret_window as iw
        _app()
        nothing = NS(evaluations=[], user_evaluations=[])
        with _language("en"):
            for result in (None, nothing, NS(evaluations=[])):
                dock = ResultsDock()
                dock.show_result(result)
                assert dock.header_label.text() == "No results yet."
                summary = iw._SummaryDock()
                summary.show_result(result)
                assert summary.label.text() == "<i>No results to display.</i>"


# ======================================================================
class TestTheUsersRowsAreMarked:
    def test_both_tables_mark_the_users_row_and_only_it(self):
        from ogr_slip2d.search import is_user_surface_of
        for name, critical in (("path+user", True), ("circle", False)):
            # critical in the first run; in the second the user's circle is
            # further down the list, admissible and not the critical one
            _p, sr = _run(name)
            order = sr.top_n(100)
            whose = [is_user_surface_of(sr, r) for r in order]
            assert whose.count(True) == 1, name
            assert (whose.index(True) == 0) == critical, name
            assert whose.index(True) < 50
            for code in ("en", "es"):
                with _language(code):
                    want = [_USERS[code] if u else "" for u in whose]
                    _header, panel = _panel(name)
                    assert [row[6] for row in _cells(panel)] == want[:50]
                    assert [row[6] for row in
                            _cells(_surfaces(name))] == want

    def test_the_label_is_of_the_critical_surface_not_of_the_run(self):
        """A run with a surface of the user that is NOT the critical one:
        neither heading says «the user's»."""
        _p, sr = _run("circle")
        assert sr.user_evaluations and sr.critical is not sr.user_evaluations[0]
        for code in ("en", "es"):
            with _language(code):
                header, _table = _panel("circle")
                text = _summary("circle")
                for said in (header, text):
                    assert "user" not in said and "usuario" not in said, said
                assert f"<b>{sr.critical.fos:.3f}</b>" in header
        with _language("en"):
            assert "<b>Critical surface</b>" in _summary("circle")

    def test_the_critical_row_is_still_the_highlighted_one(self):
        with _language("en"):
            _header, panel = _panel("path+user")
            assert [panel.item(r, 1).font().bold()
                    for r in range(panel.rowCount())] == [True] + [False] * 5

    def test_a_rejected_surface_of_the_user_says_both_things(self):
        from ogr_gui.core_messages import invalid_label, invalid_text
        from ogr_gui.themes import theme_color
        from PySide6.QtGui import QColor
        from ogr_slip2d.search import is_user_surface_of
        _p, sr = _run("steep")
        order = sr.top_n(100)
        barred = [r for r in order if not r.admissible]
        assert len(barred) == 1 and is_user_surface_of(sr, barred[0])
        i = order.index(barred[0])
        for code in ("en", "es"):
            with _language(code):
                want = f"{_USERS[code]}: {invalid_label(barred[0])}"
                grey = QColor(theme_color("muted"))
                for table in (_panel("steep")[1], _surfaces("steep")):
                    note = table.item(i, 6)
                    assert note.text() == want, note.text()
                    assert note.toolTip() == invalid_text(barred[0])
                    # the whole row is greyed, and no other
                    assert all(table.item(i, c).foreground().color() == grey
                               for c in range(table.columnCount()))
                    assert not any(
                        table.item(r, c).foreground().color() == grey
                        for r in range(table.rowCount()) if r != i
                        for c in range(table.columnCount()))
                    # the critical one, also the user's
                    assert table.item(0, 6).text() == _USERS[code]
                    assert table.item(0, 6).toolTip() == ""
                # and the Result Table says the same of it, by the same
                # function: its row is the last of the list
                heads, rows, tips = _result_table("steep", tips=True)
                assert rows[-1][5] == want, rows[-1]
                assert tips[-1] == invalid_text(barred[0])
                assert [row[5] for row in rows[:-1]] == (
                    [""] * (len(rows) - 2) + [_USERS[code]])

    def test_a_rejected_surface_of_the_search_reads_as_it_did(self):
        """``surface_note`` on the same rejected evaluation, in a result
        that does not hold it as the user's."""
        from ogr_gui.core_messages import invalid_label, invalid_text
        surface_note = _note_of
        _p, sr = _run("steep")
        barred = sr.user_evaluations[1]
        fine = sr.evaluations[0]
        with _language("en"):
            assert surface_note(NS(user_evaluations=[]), barred) == (
                invalid_label(barred), invalid_text(barred))
            assert surface_note(NS(), fine) == ("", "")
            assert surface_note(sr, fine) == ("", "")
            # by identity: a twin of a surface of the user is not the user's
            twin = copy.copy(sr.user_evaluations[0])
            assert surface_note(sr, twin) == ("", "")
        w = _window("steep")
        is_users = getattr(w, "_is_users", lambda _evaluation: False)
        assert is_users(sr.user_evaluations[0]) and not is_users(twin)

    def test_the_lists_are_the_valid_surfaces_of_both(self):
        for name in ("path+user", "circle", "grid", "focus"):
            _p, sr = _run(name)
            assert _valid_of(_window(name)) == (
                [r for r in sr.evaluations if r.is_valid]
                + [r for r in sr.user_evaluations if r.is_valid]), name
        # and only the valid ones: no run above has an evaluation that is
        # not, so a stand-in result with one in each list
        w = _window("grid")
        a, b = _run("grid")[1].evaluations[:2]
        bad = NS(is_valid=False)
        with _swapped(w, "search_result",
                      NS(evaluations=[bad, a], user_evaluations=[b, bad])):
            assert _valid_of(w) == [a, b]
        with _swapped(w, "search_result", None):
            assert _valid_of(w) == []

    def test_the_csv_has_the_users_row_and_says_which(self):
        """Against the definition: the valid surfaces of both lists by
        factor, each with the cells of always and whose it is."""
        from ogr_slip2d.search import is_user_surface_of
        for name in ("path+user", "circle"):
            _p, sr = _run(name)
            head, *lines = _csv(name)
            assert head == ["rank", "fos", "method", "centre_x", "centre_y",
                            "radius", "x_left", "x_right", "iterations",
                            "converged", "user_defined"]
            want = sorted([r for r in sr.evaluations if r.is_valid]
                          + [r for r in sr.user_evaluations if r.is_valid],
                          key=lambda r: r.fos)
            assert len(lines) == len(want) == len(sr.valid())
            for i, (line, r) in enumerate(zip(lines, want)):
                sd = r.surface.to_dict()
                assert line == [
                    str(i + 1), f"{r.fos:.6f}", r.method_id,
                    f"{sd.get('centre_x', '')}", f"{sd.get('centre_y', '')}",
                    f"{sd.get('radius', '')}", f"{sd.get('x_left', '')}",
                    f"{sd.get('x_right', '')}", str(r.iterations),
                    str(r.converged),
                    "1" if is_user_surface_of(sr, r) else "0"], (name, i)
            assert [line[-1] for line in lines].count("1") == 1

    def test_the_column_is_there_for_a_surface_that_is_not_valid_too(self):
        """«Only when the run analysed a surface of the user», valid or not:
        with one that has no factor the CSV and the Result Table have the
        column, and no row to mark."""
        w = _window("grid")
        _p, sr = _run("grid")
        double = NS(evaluations=sr.evaluations,
                    user_evaluations=[NS(is_valid=False)])
        with _language("en"), _swapped(w, "search_result", double):
            head, *lines = _csv("grid")
            heads, rows, said = _result_table("grid")
        assert head[-1] == "user_defined"
        assert len(lines) == 52 and {line[-1] for line in lines} == {"0"}
        assert all(len(line) == len(head) for line in lines)
        assert said == [] and heads[-1] == "Note" and len(heads) == 6
        assert len(rows) == 52 and {row[5] for row in rows} == {""}

    def test_the_result_table_marks_it_in_a_last_column(self):
        """Every row with its cells of always, in the order of the list
        (the search's first), and the Note of the other tables."""
        from ogr_gui.labels import surface_kind_label
        from ogr_slip2d.interpretation import surface_area
        with _language("en"):
            for name in ("path+user", "circle"):
                _p, sr = _run(name)
                heads, rows, said = _result_table(name)
                assert said == [] and heads[-1] == "Note"
                listed = _valid_of(_window(name))
                assert len(rows) == len(listed) == len(sr.valid())
                for row, r in zip(rows, listed):
                    assert row[1:] == [
                        f"{r.fos:.4f}",
                        surface_kind_label(r.surface.to_dict()["type"]),
                        f"{surface_area(r):.1f}", str(len(r.slices)),
                        _USERS["en"] if r is sr.user_evaluations[0] else ""]
        with _language("es"):
            heads, rows, _said = _result_table("path+user")
            assert heads[-1] == "Nota"
            assert [row[5] for row in rows if row[5]] == [_USERS["es"]]

    def test_the_filter_counts_what_the_canvas_can_draw(self):
        """The dialog as it opens (its ``exec`` replaced): the M of «Showing
        N of M surfaces.» is the valid surfaces of both lists, and its range
        starts at the lowest factor of them. It said «6 of 5» and «53 of 52»
        with every surface drawn (measured in the review)."""
        for name in ("path+user", "circle"):
            _p, sr = _run(name)
            m, low, said = _filter(name)
            assert said == []
            assert m == len(sr.valid()) == len(sr.evaluations) + 1, (name, m)
            assert abs(low - round(min(r.fos for r in sr.valid()), 3)) < 1e-9

    def test_the_three_read_one_list(self):
        """In the source too: the filter, the result table and the CSV ask
        ``_valid_surfaces``, and none walks the search's population alone.
        (What they do with it is measured above.)"""
        tree = ast.parse((_ROOT / "ogr_gui" / "interpret_window.py")
                         .read_text(encoding="utf-8"))
        for name in ("_filter_surfaces", "_add_result_table",
                     "_export_data_csv"):
            func, = [n for n in ast.walk(tree)
                     if isinstance(n, ast.FunctionDef) and n.name == name]
            attrs = {n.attr for n in ast.walk(func)
                     if isinstance(n, ast.Attribute)}
            assert "_valid_surfaces" in attrs, name
            assert "evaluations" not in attrs, name


# ======================================================================
class TestTheBackAnalysisSaysWhichSurfaceItPriced:
    def _forces(self, name, mid):
        from ogr_slip2d.back_analysis import required_force_of_result
        p, sr = _run(name)
        return required_force_of_result(sr.critical, _TARGET, _ELEVATION,
                                        project=p, method_id=mid)

    def test_the_critical_surface_of_the_run_not_the_users(self):
        """The reason for the line: the run's back analysis publishes the
        force of the user's circle, and Interpret another, of another
        surface."""
        from ogr_slip2d.analysis_runner import run_configured_back_analysis
        from ogr_slip2d.search import is_user_surface_of
        p, sr = _run("circle")
        assert not is_user_surface_of(sr, sr.critical)
        run = run_configured_back_analysis(p)[0]
        assert run.critical.user_defined
        r = self._forces("circle", _J)
        assert run.required_force - r.passive_force > 10.0
        with _language("en"):
            said, = _back_analysis("circle")
        lines = said.split("\n")
        assert lines[0] == "Required support force for FS = 1.5"
        assert lines[1] == ("Back-analysed on the critical surface of the "
                            "run (Janbu Simplified).")
        assert lines[2] == ""
        assert lines[3] == "active: %.2f" % r.active_force
        assert lines[4] == "passive: %.2f" % r.passive_force
        assert "user" not in said
        from ogr_gui.labels import method_name
        with _language("es"):
            said, = _back_analysis("circle")
            assert said.split("\n")[1] == (
                "Retroanálisis sobre la superficie crítica del cálculo "
                "(%s)." % method_name(_J))

    def test_the_users_surface_when_it_is_the_critical_one(self):
        from ogr_gui.labels import method_name
        r = self._forces("path+user", _J)
        assert r.passive_force > 0.0
        for code, line in (
                ("en", "Back-analysed on the critical surface of the run "
                       "({0}), defined by the user."),
                ("es", "Retroanálisis sobre la superficie crítica del "
                       "cálculo ({0}), definida por el usuario.")):
            with _language(code):
                said, = _back_analysis("path+user")
                lines = said.split("\n")
                assert lines[1] == line.format(method_name(_J)), lines[1]
                assert "%.2f" % r.passive_force in lines[4]

    def test_without_a_force_there_is_no_such_line(self):
        """A surface already at the target is not priced (D418): the
        message is the reason, alone."""
        _p, sr = _run("path+user")
        with _language("en"):
            said, = _back_analysis("path+user",
                                   target=sr.critical.fos * 0.9)
        assert "Back-analysed" not in said
        assert "already reaches the target" in said

    def test_the_line_is_all_that_changes(self):
        """The message of 0.1.442 with the line put after its first one."""
        with _language("en"):
            said, = _back_analysis("grid")
        before, = _V1442["back_analysis"]
        first, rest = before.split("\n", 1)
        assert said == (first + "\nBack-analysed on the critical surface of "
                        "the run (Janbu Simplified).\n" + rest)


# ======================================================================
class TestWithoutUserSurfacesNothingChanges:
    def test_the_windows_are_the_ones_of_0_1_442(self):
        got = _capture()
        assert list(got) == list(_V1442)
        for key, want in _V1442.items():
            if key == "back_analysis":
                continue   # its one line: ``test_the_line_is_all_that_changes``
            assert _same(got[key], want), (key, got[key], want)

    def test_the_reference_says_something(self):
        """About the literal alone: a reference of empty answers would pin
        nothing."""
        assert _V1442["panel.table"][1] == 50
        assert _V1442["surfaces.table"][1] == 52
        assert _V1442["result_table"][1] == 52
        assert _V1442["csv"][0] == 53
        assert len(_V1442["result_table"][0]) == 5
        assert _V1442["filter"][0] == 52 and _V1442["filter"][2] == []
        assert len(_V1442["csv"][1][0]) == 10
        assert "passive: 145.99" in _V1442["back_analysis"][0]

    def test_nothing_says_user(self):
        def texts(obj):
            if isinstance(obj, (list, tuple)):
                return [t for item in obj for t in texts(item)]
            return [obj] if isinstance(obj, str) else []
        for code in ("en", "es"):
            with _language(code):
                header, table = _panel("grid")
                heads, rows, _said = _result_table("grid")
                said = texts([header, _cells(table), _summary("grid"),
                              _cells(_surfaces("grid")), heads, rows,
                              _csv("grid"), _back_analysis("grid")])
            assert said and not [t for t in said
                                 if "user" in t.lower() or "usuario" in t]

    def test_a_double_with_only_evaluations_still_shows(self):
        """The stand-in results of other tests have no ``user_evaluations``
        (``tests/test_names_and_headings_v1369.py``)."""
        from ogr_gui.widgets.results_dock import ResultsDock
        _app()
        _p, sr = _run("grid")
        rows = sr.top_n(3)
        double = NS(objective="fos", critical=rows[0], evaluations=rows,
                    method_id=_J, valid_count=3, invalid_count=0,
                    analysed_count=3, top_n=lambda n: rows[:n])
        with _language("en"):
            dock = ResultsDock()
            dock.show_result(double)
            assert "defined by the user" not in dock.header_label.text()
            assert [row[6] for row in _cells(dock.table)] == ["", "", ""]


# ======================================================================
class TestTheNewTextsAreTranslated:
    def test_each_sentence_has_its_spanish(self):
        from ogr_gui.i18n import tr
        with _language("es"):
            for english, spanish in (
                    ("Critical surface, defined by the user",
                     "Superficie crítica, definida por el usuario"),
                    ("Defined by the user", "Definida por el usuario"),
                    ("Defined by the user: {0}",
                     "Definida por el usuario: {0}"),
                    ("Back-analysed on the critical surface of the run "
                     "({0}).",
                     "Retroanálisis sobre la superficie crítica del "
                     "cálculo ({0})."),
                    ("Back-analysed on the critical surface of the run "
                     "({0}), defined by the user.",
                     "Retroanálisis sobre la superficie crítica del "
                     "cálculo ({0}), definida por el usuario.")):
                assert tr(english) == spanish

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.444 (D402) — the circles the user draws have what v0.1.427 gave the
polylines.

The invariant: one rule for the two kinds of hand-drawn surface. A surface
of the user that a post-analysis check rejects is said in the run's notes,
with its factor and the reason; a greyed menu entry says why on the status
bar; and the window does not store a surface under a Surface Type that the
operations layer refuses it under. The polylines had the three since
v0.1.427. The circles had none:

* the demo slope's circle of centre (32, 16) and radius 5 has a factor of
  3.0019 under Bishop that the m-alpha screen rejects, and the run did not
  say so;
* with a non-circular Surface Type the three circle entries were greyed with
  a tooltip, which no menu shows, and no status tip (D289b); and Auto Grid
  and Add Grid the same with a search that uses no grid (found while
  planning), and Add Water Table and Add Tension Crack in a model that
  already has one (found in the review): the same kind of defect;
* with the type changed while a circle mode was on (Surface Options, an
  agent), the three ways in stored the circle all the same: three circles
  and three undo steps, of surfaces ``user_surface_add`` refuses and a
  non-circular run skips.

What is anchored here:

* the note against the run itself: its factor is the evaluation's own
  ``fos``, its reason the one of that evaluation, one note per method with
  the method's own factor (three methods), and no number of the run moves
  (the critical surface and the counters are the ones of the run without
  the circle, in this process);
* the note is not said of the circle the run REPORTS: with no admissible
  surface ``critical`` falls back on the rejected ones, and «it cannot be
  the critical surface» would contradict the note that says it is the
  surface reported;
* the sentence is the polyline's, from «has a factor of safety» on;
* every greyed entry REACHABLE from the menu bar has a status tip, in four
  states of the search and with a water table and a tension crack in the
  model, and the seven of this version say their sentence;
* the three ways in refuse, leave the mode, say it with the two sentences
  that already existed, and open no input box; under a circular type they
  add the circle as always.

One ``MainWindow`` for the file. The engine runs are five small grids.
"""
from __future__ import annotations

import os
from contextlib import contextmanager

_B, _J, _S = "bishop_simplified", "janbu_simplified", "spencer"
#: The three reject the circle of the ficha, each with its own factor.
_METHODS = (_B, _J, _S)
#: The circle of the ficha: valid, and rejected by the m-alpha screen.
_BARRED = (32.0, 16.0, 5.0)
_CIRCLES_ONLY = ("Only available with Surface Options -> Surface Type = "
                 "Circular.")
_CIRCLES_ONLY_ES = ("Solo disponible con Opciones de superficie -> Tipo de "
                    "superficie = Circular.")
_NOT_ADDED = "The surface was not added."
_GREY = ("auto_grid", "add_grid", "surf_centre_radius", "surf_three_points",
         "surf_manage")


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
    """``owner.name`` replaced and put back; removed again if ``owner``
    did not have it of its own (an instance's method, or a class that
    inherits it: left behind, it would hide a later patch of the base)."""
    had = name in vars(owner)
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
_RUNS: dict = {}


def _project(circles=(_BARRED,)):
    from ogr_core.project.demo import build_demo_project
    from ogr_slip2d.surface import SlipCircle
    p = build_demo_project()
    s = p.settings.search
    s.grid_nx = s.grid_ny = s.radius_increment = 3
    p.user_surfaces = [SlipCircle(centre_x=x, centre_y=y, radius=r)
                       for x, y, r in circles]
    return p


#: A second circle the m-alpha screen rejects, with a higher factor.
_BARRED_TOO = (33.0, 16.0, 5.0)


def _run(name):
    """The outcome of a case, once, under the three methods: ``with`` the
    rejected circle, ``without`` any, and ``alone``: two rejected circles
    and a grid moved away from the slope, which finds no surface."""
    if name not in _RUNS:
        from ogr_slip2d.analysis_runner import run_analysis
        circles = {"with": (_BARRED,), "without": (),
                   "alone": (_BARRED, _BARRED_TOO)}[name]
        p = _project(circles)
        if name == "alone":
            s = p.settings.search
            s.grid_x_min, s.grid_x_max = 200.0, 210.0
            s.grid_y_min, s.grid_y_max = 200.0, 210.0
        _RUNS[name] = run_analysis(p, list(_METHODS))
    return _RUNS[name]


def _own(notes) -> list:
    """The notes of the new code among ``notes``."""
    from ogr_core.messages import parts
    return [n for n in notes if parts(n)[0] == "search.user_inadmissible"]


# ======================================================================
class TestARejectedCircleIsSaid:

    def test_the_circle_is_the_one_of_the_ficha(self):
        r = _run("with").results[_B]
        u, = r.user_evaluations
        assert u.is_valid and not u.admissible
        assert abs(u.fos - 3.0019) < 1e-4
        assert r.critical is not u and abs(r.critical.fos - 1.1355) < 1e-4

    def test_the_run_says_it_with_its_factor_and_its_reason(self):
        from ogr_core.messages import parts
        from ogr_slip2d.search_note_messages import NO_REASON_STOP, reason_of
        for mid in _METHODS:
            r = _run("with").results[mid]
            u, = r.user_evaluations
            assert u.is_valid and not u.admissible, mid
            note, = _own(r.notes)
            code, args, english = parts(note)
            # the factor of THIS method's evaluation, to the last bit
            assert args["factor"] == u.fos, mid
            assert (args["x"], args["y"], args["r"]) == _BARRED
            assert args["reason"] == reason_of(u, NO_REASON_STOP)
            assert english == (
                "The user-defined surface at centre (32, 16) with radius 5 "
                "has a factor of safety of %.4g, but the post-analysis "
                "checks reject it, so it cannot be the critical surface: %s"
                % (u.fos, u.admissibility_note)), english
        # each method its own factor: three different sentences
        said = {str(_own(_run("with").results[m].notes)[0])
                for m in _METHODS}
        assert len(said) == 3

    def test_it_is_not_said_of_the_circle_the_run_reports(self):
        """The grid finds no surface and both circles of the user are
        rejected: ``critical`` falls back on the lower of the two, which the
        run reports as the user's. The other one is said rejected; the
        reported one is not told that it cannot be what it is."""
        from ogr_core.messages import parts
        for mid in _METHODS:
            r = _run("alone").results[mid]
            assert r.evaluations == [], mid
            low, high = r.user_evaluations
            assert not low.admissible and not high.admissible
            assert low.fos < high.fos and r.critical is low
            note, = _own(r.notes)
            args = parts(note)[1]
            assert (args["x"], args["y"], args["r"]) == _BARRED_TOO, mid
            assert args["factor"] == high.fos
            reported = [n for n in r.notes
                        if parts(n)[0] == "search.user_reported"]
            assert len(reported) == 1
            assert (parts(reported[0])[1]["x"],
                    parts(reported[0])[1]["r"]) == (_BARRED[0], _BARRED[2])

    def test_it_reaches_the_warnings_of_the_run(self):
        out = _run("with")
        for mid in _METHODS:
            mine = [str(w) for w in out.warnings
                    if "(32, 16)" in str(w) and str(w).startswith(mid)]
            assert len(mine) == 1 and "cannot be the critical" in mine[0]

    def test_it_says_it_in_spanish(self):
        from ogr_gui.core_messages import note_text
        u, = _run("with").results[_B].user_evaluations
        note, = _own(_run("with").results[_B].notes)
        with _language("es"):
            said = note_text(note)
        assert said.startswith(
            "La superficie definida por el usuario con centro en (32, 16) y "
            "radio 5 tiene un factor de seguridad de %.4g, pero las "
            "comprobaciones posteriores al cálculo la rechazan, así que no "
            "puede ser la superficie crítica: " % u.fos), said
        assert "{" not in said

    def test_the_sentence_is_the_polylines(self):
        from ogr_slip2d import search_note_messages as SN
        cut = "has a factor of safety"
        # by their codes: a tree without the circle's has no such entry
        assert "search.user_inadmissible" in SN.SEARCH_NOTES
        circle = SN.SEARCH_NOTES["search.user_inadmissible"].english
        polyline = SN.SEARCH_NOTES[
            "search.user_polyline_inadmissible"].english
        assert circle.count(cut) == 1 == polyline.count(cut)
        assert circle.split(cut)[1] == polyline.split(cut)[1]
        assert "{fos" not in circle and "{factor:.4g}" in circle

    def test_no_number_of_the_run_moves(self):
        """The note is all that changes: the critical surface and the
        counters are the ones of the run without the circle."""
        for mid in _METHODS:
            mine, plain = (_run(n).results[mid] for n in ("with", "without"))
            assert mine.critical.fos == plain.critical.fos, mid
            assert (mine.total_count, mine.valid_count, mine.invalid_count,
                    mine.inadmissible_count) == (
                plain.total_count, plain.valid_count, plain.invalid_count,
                plain.inadmissible_count), mid
            assert [e.fos for e in mine.evaluations] == [
                e.fos for e in plain.evaluations]
            assert _own(plain.notes) == []

    def test_only_a_rejected_circle_is_said(self):
        """An admissible circle of the user leaves no such note, and one
        with no factor leaves the note it always left, alone."""
        from ogr_core.messages import parts
        from ogr_slip2d.analysis_runner import run_analysis
        out = run_analysis(_project(((36.0, 34.0, 20.0),)), [_B])
        r = out.results[_B]
        u, = r.user_evaluations
        assert u.is_valid and u.admissible
        assert _own(r.notes) == []
        # no factor: the stand-in evaluation the search hands back
        import ogr_slip2d.search as S
        real = S.GridSearch.evaluate_circle

        def without_factor(self, project, circle):
            res = real(self, project, circle)
            if res is not None and (circle.centre_x, circle.centre_y,
                                    circle.radius) == _BARRED:
                res.converged = False
            return res

        with _swapped(S.GridSearch, "evaluate_circle", without_factor):
            out = run_analysis(_project(), [_B])
        r = out.results[_B]
        u, = r.user_evaluations
        assert not u.is_valid
        codes = [parts(n)[0] for n in r.notes if "(32, 16)" in str(n)]
        assert codes == ["search.user_no_factor"], codes


# ======================================================================
_WINDOWS: list = []


def _window(surface_type="circular", method="grid"):
    """One window for the file (each one lives until the process ends), put
    back to a known state: no user surfaces, an empty undo stack, the Select
    mode and the given search."""
    if not _WINDOWS:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from ogr_gui.main_window import MainWindow
        with _language("en"):
            _WINDOWS.append(MainWindow())
    from ogr_gui.canvas import ToolMode
    w = _WINDOWS[0]
    w.project.user_polylines = []
    w.project.user_surfaces = []
    s = w.project.settings.search
    s.surface_type, s.search_method = surface_type, method
    w.canvas.set_tool_mode(ToolMode.SELECT)
    w.command_stack.clear()
    w.project.is_dirty = False
    w.refresh_action_availability()
    return w


def _grey_without_a_reason(w) -> list:
    """The entries reachable from the menu bar that are disabled and have no
    status tip."""
    from PySide6.QtWidgets import QMenu
    reach = {id(a) for m in w.menuBar().findChildren(QMenu)
             for a in m.actions()}
    return [k for k, a in w._actions.items()
            if id(a) in reach and not a.isEnabled() and not a.statusTip()]


class TestAGreyEntrySaysWhy:

    def test_no_reachable_entry_is_grey_without_a_reason(self):
        with _language("en"):
            for surface_type, method in (("non_circular", "path"),
                                         ("non_circular", "block"),
                                         ("circular", "slope"),
                                         ("circular", "grid")):
                w = _window(surface_type, method)
                assert _grey_without_a_reason(w) == [], (surface_type, method)

    def test_nor_in_a_model_with_a_water_table_and_a_tension_crack(self):
        """A new project greys neither entry: the model has to hold the one
        water table and the one tension crack it may hold."""
        from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                       Vertex)

        def line(*points):
            return Polyline(vertices=[Vertex(x, y) for x, y in points],
                            closed=False)

        w = _window("non_circular", "path")
        kept = list(w.project.boundaries)
        try:
            w.project.boundaries.append(Boundary(
                polyline=line((0.0, 5.0), (10.0, 5.0)),
                btype=BoundaryType.WATER_TABLE))
            w.project.boundaries.append(Boundary(
                polyline=line((3.0, 9.0), (3.0, 7.0)),
                btype=BoundaryType.TENSION_CRACK))
            for code, water, crack in (
                    ("en", "Only one Water Table is allowed.",
                     "Only one Tension Crack boundary is allowed. Delete the "
                     "existing one to add a new one."),
                    ("es", "Solo se permite un nivel freático.", None)):
                with _language(code):
                    w.refresh_action_availability()
                    assert _grey_without_a_reason(w) == []
                    wt, tc = w._actions["add_wt"], w._actions["add_crack"]
                    assert not wt.isEnabled() and not tc.isEnabled()
                    assert wt.statusTip() == water == wt.toolTip()
                    # the crack's reason on one line; its tooltip keeps two
                    assert "\n" in tc.toolTip() and "\n" not in tc.statusTip()
                    assert tc.statusTip() == " ".join(tc.toolTip().split())
                    if crack is not None:
                        assert tc.statusTip() == crack
        finally:
            w.project.boundaries[:] = kept
        with _language("en"):
            w = _window()
            for key, does in (("add_wt", "Add Water Table"),
                              ("add_crack", "Add Tension Crack")):
                a = w._actions[key]
                assert a.isEnabled() and a.statusTip() == "", key
                assert a.toolTip() == does

    def test_the_circles_entries_say_their_sentence(self):
        keys = ("surf_centre_radius", "surf_three_points", "surf_manage")
        for code, sentence in (("en", _CIRCLES_ONLY),
                               ("es", _CIRCLES_ONLY_ES)):
            with _language(code):
                w = _window("non_circular", "path")
                for key in keys:
                    a = w._actions[key]
                    assert not a.isEnabled(), key
                    assert a.statusTip() == sentence, (key, a.statusTip())
                    # the tooltip is the one of always
                    assert a.toolTip() == sentence
        with _language("en"):
            w = _window("circular", "grid")
            for key in keys:
                a = w._actions[key]
                # enabled: what it does in the tooltip, nothing on the bar
                assert a.isEnabled() and a.statusTip() == "", key
                assert a.toolTip() == ("Slip surfaces defined by hand, "
                                       "analysed in addition to the search")

    def test_the_grid_entries_say_theirs_on_one_line(self):
        for code, starts in (("en", "The current Search Method does not "
                                    "use a slip-circle centre grid."),
                             ("es", "El método de búsqueda actual no usa")):
            with _language(code):
                for surface_type, method in (("circular", "slope"),
                                             ("non_circular", "path")):
                    w = _window(surface_type, method)
                    for key in ("auto_grid", "add_grid"):
                        a = w._actions[key]
                        assert not a.isEnabled(), key
                        tip = a.statusTip()
                        assert tip.startswith(starts), (key, tip)
                        assert "\n" not in tip
                        # the tooltip's own sentence, which keeps its lines
                        assert "\n" in a.toolTip()
                        assert tip == " ".join(a.toolTip().split())
        with _language("en"):
            w = _window("circular", "grid")
            assert w._actions["auto_grid"].isEnabled()
            assert w._actions["auto_grid"].statusTip() == ""
            assert w._actions["auto_grid"].toolTip() == (
                "Auto-generate the slip-circle search grid")
            assert w._actions["add_grid"].toolTip() == (
                "Define a slip-circle search grid manually")

    def test_the_five_are_the_ones_that_had_none(self):
        """The control of the first test: these are the entries it is
        about, all five grey under a non-circular Path search."""
        with _language("en"):
            w = _window("non_circular", "path")
            assert all(not w._actions[k].isEnabled() for k in _GREY)


# ======================================================================
def _ways_in(w):
    """The three ways a circle reaches the window, each with the mode it is
    delivered in."""
    from ogr_gui.canvas import ToolMode
    return (
        ("clicked", ToolMode.ADD_SURFACE_CR,
         lambda: w._on_surface_cr_picked(30.0, 30.0, 40.0, 30.0)),
        ("typed", ToolMode.ADD_SURFACE_CR,
         lambda: w._type_surface_centre_radius((30.0, 30.0))),
        ("typed, no centre clicked", ToolMode.ADD_SURFACE_CR,
         lambda: w._type_surface_centre_radius()),
        ("three points", ToolMode.ADD_SURFACE_3PT,
         lambda: w._on_surface_3pt_picked(20.0, 25.0, 30.0, 14.0,
                                          40.0, 15.0)),
    )


@contextmanager
def _inputs(w, radius=(10.0, True)):
    """The input boxes replaced (nothing modal opens): ``asked`` gets the
    label of each one that would have opened."""
    from PySide6.QtWidgets import QInputDialog
    asked = []

    def get_double(_parent, _title, label, *a, **k):
        asked.append(label)
        return radius

    def get_text(_parent, _title, label, *a, **k):
        asked.append(label)
        return "", False

    with _swapped(QInputDialog, "getDouble", staticmethod(get_double)), \
            _swapped(QInputDialog, "getText", staticmethod(get_text)), \
            _swapped(w, "_read_points",
                     lambda *a, **k: asked.append("points") or None):
        yield asked


class TestTheWindowStoresNoCircleUnderANonCircularType:

    def test_the_three_ways_in_refuse(self):
        """The type changed while the mode was on (Surface Options, an
        agent)."""
        from ogr_gui.canvas import ToolMode
        with _language("en"):
            w = _window()
            s = w.project.settings.search
            for name, mode, deliver in _ways_in(w):
                s.surface_type = "circular"
                w.canvas.set_tool_mode(mode)
                assert w.canvas.tool_mode == mode
                s.surface_type = "non_circular"
                with _inputs(w) as asked:
                    deliver()
                assert w.project.user_surfaces == [], name
                assert w.command_stack.history() == ([], []), name
                assert w.project.is_dirty is False, name
                assert w.canvas.tool_mode == ToolMode.SELECT, name
                assert w.ogr_status.currentMessage() == (
                    _CIRCLES_ONLY + " " + _NOT_ADDED), name
                assert asked == [], (name, asked)

    def test_it_says_it_in_spanish(self):
        with _language("es"):
            w = _window()
            w.project.settings.search.surface_type = "non_circular"
            with _inputs(w):
                w._on_surface_cr_picked(30.0, 30.0, 40.0, 30.0)
            assert w.ogr_status.currentMessage() == (
                _CIRCLES_ONLY_ES + " No se ha añadido la superficie.")
            assert w.project.user_surfaces == []

    def test_under_a_circular_type_they_add_it_as_always(self):
        from ogr_gui.canvas import ToolMode
        with _language("en"):
            for i, (name, mode, deliver) in enumerate(_ways_in(_window())):
                w = _window()
                w.canvas.set_tool_mode(mode)
                with _inputs(w) as asked:
                    deliver()
                if name == "typed, no centre clicked":
                    # it asks for the centre, and the stand-in cancels
                    assert asked == ["points"]
                    assert w.project.user_surfaces == []
                    continue
                circle, = w.project.user_surfaces
                assert w.command_stack.history() == (
                    ["Add user surface"], []), name
                assert w.canvas.tool_mode == ToolMode.SELECT
                assert w.statusBar().currentMessage().startswith(
                    "Circle added: centre ("), name
                assert asked == (["Radius:"] if name == "typed" else [])
                if name != "three points":
                    assert (circle.centre_x, circle.centre_y,
                            circle.radius) == (30.0, 30.0, 10.0)
        _window()   # leave the window as it is found

    def test_the_check_itself(self):
        from ogr_gui.canvas import ToolMode
        with _language("en"):
            w = _window()
            # a tree without the check refused nothing
            refused = getattr(w, "_circles_refused", lambda: False)
            w.canvas.set_tool_mode(ToolMode.ADD_SURFACE_CR)
            assert refused() is False
            # not refused: it neither leaves the mode nor says anything
            assert w.canvas.tool_mode == ToolMode.ADD_SURFACE_CR
            w.project.settings.search.surface_type = "non_circular"
            assert refused() is True
            assert w.canvas.tool_mode == ToolMode.SELECT
        _window()

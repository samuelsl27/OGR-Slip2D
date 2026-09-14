# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D96 — the interface must say when a design standard was applied.

**The invariant**: with partial factors active the reported number is an
over-design factor, not a factor of safety, and every widget that prints it
has to say so. The engine has always known — ``run_analysis`` returns the
report in ``outcome.factor_report`` — and the command line has said it since
v0.1.127. The interface stored the report in ``_ComputeWorker`` and read it
nowhere, so the same run described itself correctly in a terminal and
incorrectly in a window.

That is regla 7 in its oldest form: partial factors were configurable
without applying for two versions (v0.1.52 → v0.1.57). They apply now; what
was missing was saying so.

**No assertion here fixes a factor of safety.** What is pinned is identity
(the same run, labelled, produces the same number) and what each widget
CALLS the number. A snapshot of today's arithmetic would protect nothing.

Two premises are pinned as tests rather than comments, because both were
measured against a ficha that assumed the opposite, and a comment nobody can
falsify is how a wrong measurement survives two versions:

* a note placed first in ``last_compute_warnings`` does NOT reach the status
  bar on a run that found a critical surface — the caption line replaces it;
* the caption follows the value the widget prints, which is why a Ky run is
  captioned differently in Interpret (which switches the value) and in the
  status bar (which always prints ``critical.fos``).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


# Qt destroys the child widgets when the owning window is collected, and a
# non-modal panel left open is leaked state (regla 5).
_WINDOWS: list = []


def _app():
    return QApplication.instance() or QApplication([])


# ======================================================================
def _slope(name="d96"):
    """A homogeneous slope small enough to search many times over.

    Three centres by three, three radii: these tests measure WHAT the run
    is called, never how good its minimum is, so a fine grid would buy
    nothing and cost seconds per test.
    """
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
        Vertex(35, 15), Vertex(25, 25), Vertex(0, 25),
    ], closed=True)
    ext.ensure_ccw()
    p = Project(name)
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.settings.units.failure_direction = FailureDirection.LEFT_TO_RIGHT
    p.add_material(Material(
        name="Silty clay", unit_weight=19.0,
        strength=MohrCoulomb(cohesion=10.0, friction_angle=25.0)))
    p.settings.methods.enabled_methods = ["bishop_simplified"]
    p.settings.methods.num_slices = 25
    p.settings.search.grid_nx = 3
    p.settings.search.grid_ny = 3
    p.settings.search.radius_increment = 2
    return p


def _with_standard(p, preset="eurocode7_da1c2"):
    """Switch the standard on, the way ``test_m6_v157`` does."""
    ds = p.settings.design_standard
    ds.enabled = True
    ds.apply_preset(preset)
    return p


def _all_unity(p):
    """Enabled, and every partial factor left at 1.0.

    ``apply_design_factors`` reports ``applied`` for this too, and files a
    note saying nothing changed.
    """
    ds = p.settings.design_standard
    ds.enabled = True
    ds.apply_preset("none")
    ds.standard = "custom"
    return p


def _window(project):
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow

    _app()
    set_language("en")
    w = MainWindow()
    _WINDOWS.append(w)
    w.project = project
    w.canvas.set_project(project)
    return w


def _compute(w):
    """Drive the real compute-finished path, without the modal dialog.

    ``act_compute`` ends in ``self.prog.exec()``, which blocks forever
    without a display; production wires the worker's ``finished_result`` to
    ``_on_compute_done`` and that is what is exercised here.
    """
    from ogr_gui.main_window import _ComputeWorker

    errors: list = []
    w.worker = _ComputeWorker(w.project, ["bishop_simplified"])
    w.worker.failed.connect(errors.append)
    w.worker.run()
    assert not errors, errors
    w._on_compute_done(w.worker.results)
    return w.worker


def _compute_all(w):
    """The same, for every method the project enables."""
    from ogr_gui.main_window import _ComputeWorker

    errors: list = []
    w.worker = _ComputeWorker(
        w.project, list(w.project.settings.methods.enabled_methods))
    w.worker.failed.connect(errors.append)
    w.worker.run()
    assert not errors, errors
    w._on_compute_done(w.worker.results)
    return w.worker


def _status(w):
    return w.ogr_status.currentMessage()


class _FakeResult:
    """The smallest thing ``reported_quantity`` can be asked about.

    A real Ky run costs a seismic search; what is under test is a caption
    function, and it reads two attributes.
    """

    def __init__(self, objective="fos", details=None):
        self.objective = objective
        self.critical = type("C", (), {"details": details or {}})()


class _FakeReport:
    def __init__(self, applied=True, summary="std: 1 material(s) factored",
                 notes=()):
        self.applied = applied
        self.notes = list(notes)
        self._summary = summary

    def summary(self):
        return self._summary


# ======================================================================
@_requires_qt
class TestThePremisesTheFichaAssumed:
    """Measured, and both came out the other way round.

    Neither of these is the fix; they are why the fix is where it is.
    """

    def test_the_first_note_does_not_survive_in_the_status_bar(self):
        """The ficha's step 1 says putting the sentence first in the notes
        makes it appear in the status bar. It does not: the caption line is
        shown afterwards and a status bar holds ONE temporary message, so on
        any run with a critical surface the note is replaced before anybody
        reads it. This is what forces the caption itself to change.
        """
        w = _window(_with_standard(_slope()))
        worker = _compute(w)
        assert worker.results["bishop_simplified"].critical is not None
        note = w.last_compute_warnings[0]
        assert "Design standard applied" in note, note
        # The note went into the list, and the bar shows the caption.
        assert note not in _status(w), _status(w)
        assert "Over-design factor" in _status(w), _status(w)

    def test_a_bare_status_bar_replaces_one_message_with_the_next(self):
        """The Qt behaviour the test above depends on, in isolation, so a
        failure says which of the two broke."""
        from PySide6.QtWidgets import QStatusBar

        _app()
        bar = QStatusBar()
        bar.showMessage("first", 15000)
        assert bar.currentMessage() == "first"
        bar.showMessage("second", 10000)
        assert bar.currentMessage() == "second"

    def test_the_report_is_applied_even_with_every_factor_at_one(self):
        """``applied`` tracks the standard being ENABLED, not anything
        having changed — which is why the note matters."""
        from ogr_core.project import apply_design_factors

        _out, rep = apply_design_factors(_all_unity(_slope()))
        assert rep.applied is True
        assert any("nothing changed" in n for n in rep.notes), rep.notes


# ======================================================================
@_requires_qt
class TestTheCaptionFollowsTheValue:
    """``reported_quantity`` switches the value, ``fos_label`` does not.

    Merging the two looks like an obvious simplification and would put
    "Critical seismic coefficient" over a factor of safety.
    """

    def test_a_factored_run_is_an_over_design_factor(self):
        from ogr_gui.i18n import set_language
        from ogr_gui.reported_quantity import fos_label, reported_quantity

        _app()
        set_language("en")
        kind, label = reported_quantity(_FakeResult(), _FakeReport())
        assert kind == "fos"          # same field, same units, same format
        assert label == "Over-design factor"
        assert fos_label(_FakeReport()) == "Over-design factor"

    def test_an_unfactored_run_is_untouched(self):
        from ogr_gui.i18n import set_language
        from ogr_gui.reported_quantity import fos_label, reported_quantity

        _app()
        set_language("en")
        assert reported_quantity(_FakeResult(), None)[1] == "Factor of safety"
        assert reported_quantity(_FakeResult(),
                                 _FakeReport(applied=False))[1] == \
            "Factor of safety"
        assert fos_label(None) == "Critical FoS"

    def test_a_seismic_run_keeps_its_own_caption_even_when_factored(self):
        """Partial factors on the soil do not turn a seismic coefficient
        into an over-design factor. The command line resolves this the
        other way round and prints a Ky under an "Over-design factor"
        heading; that is reported as a defect of the command line, and the
        divergence is deliberate. Do not "unify" them without reading it.
        """
        from ogr_gui.i18n import set_language
        from ogr_gui.reported_quantity import reported_quantity

        _app()
        set_language("en")
        ky = _FakeResult(objective="ky")
        assert reported_quantity(ky, _FakeReport())[1] == \
            "Critical seismic coefficient"
        newmark = _FakeResult(objective="ky",
                              details={"newmark_displacement": 0.01})
        assert reported_quantity(newmark, _FakeReport())[1] == \
            "Newmark displacement"

    def test_a_widget_that_prints_fos_keeps_the_fos_caption_on_a_ky_run(self):
        """``fos_label`` takes no result on purpose: the status bar and the
        results dock print ``critical.fos`` on every run, including a Ky
        one, where that number is a real factor of safety."""
        from ogr_gui.i18n import set_language
        from ogr_gui.reported_quantity import fos_label

        _app()
        set_language("en")
        assert fos_label(None) == "Critical FoS"
        assert fos_label(_FakeReport()) == "Over-design factor"


# ======================================================================
@_requires_qt
class TestWhatTheUserSeesAfterCompute:
    """Every widget that prints the headline number of the run."""

    def test_without_a_standard_nothing_changes(self):
        w = _window(_slope())
        _compute(w)
        assert w.last_factor_report is not None      # the empty report
        assert w.last_factor_report.applied is False
        assert not any("Design standard" in n
                       for n in w.last_compute_warnings)
        assert "Critical FoS" in _status(w), _status(w)
        assert "Over-design" not in _status(w), _status(w)
        assert "Critical FoS" in w.results_dock.header_label.text()

    def test_the_status_bar_says_over_design(self):
        w = _window(_with_standard(_slope()))
        _compute(w)
        assert "Over-design factor" in _status(w), _status(w)
        assert "Critical FoS" not in _status(w), _status(w)

    def test_the_results_dock_says_over_design(self):
        """The panel beside the canvas, which the ficha's inventory misses
        and which the user reads first."""
        w = _window(_with_standard(_slope()))
        _compute(w)
        text = w.results_dock.header_label.text()
        assert "Over-design factor" in text, text
        assert "Critical FoS" not in text, text

    def test_the_note_carries_the_report_summary_and_comes_first(self):
        w = _window(_with_standard(_slope()))
        worker = _compute(w)
        first = w.last_compute_warnings[0]
        assert "Design standard applied" in first, first
        assert worker.factor_report.summary() in first, first
        assert "must exceed 1" in first, first

    def test_the_note_reaches_the_panel_under_the_model_group(self):
        """The sentence contains a colon, and the panel groups notes by a
        ``"<method>: "`` prefix. The guard only takes a prefix without
        spaces, so this lands under Model — checked, not assumed.
        """
        w = _window(_with_standard(_slope()))
        _compute(w)
        w.act_analysis_notes()
        panel = w._analysis_notes_panel
        try:
            assert any("Design standard applied" in n for n in panel.notes)
            groups = [panel.tree.topLevelItem(i).text(0)
                      for i in range(panel.tree.topLevelItemCount())]
            assert any(g.startswith("Model") for g in groups), groups
            assert not any(g.startswith("Design") for g in groups), groups
        finally:
            panel.close()

    def test_the_all_unity_case_says_the_standard_changed_nothing(self):
        """Caption and note together. The caption matches the command line
        so the two front ends never disagree; the note is what stops that
        caption standing alone over an ordinary factor of safety.
        """
        w = _window(_all_unity(_slope()))
        _compute(w)
        assert "Over-design factor" in _status(w), _status(w)
        joined = " | ".join(w.last_compute_warnings)
        assert "Design standard applied" in joined, joined
        assert "nothing changed" in joined, joined

    def test_interpret_says_it_too(self):
        w = _window(_with_standard(_slope()))
        _compute(w)
        w.act_interpret()
        win = w.interpret_windows[-1]
        _WINDOWS.append(win)
        try:
            assert win.factor_report is w.last_factor_report
            assert "Over-design factor" in win.summary_dock.label.text()
            # The single-method read-out, which is where most runs land:
            # the selector combo only exists with more than one method.
            assert "Over-design factor" in win.lbl_algorithm.text()
            assert "FS =" not in win.lbl_algorithm.text()
        finally:
            win.close()

    def test_the_interpret_method_selector_says_it_too(self):
        """The combo appears only with more than one method computed, and
        it hard-coded "FoS" — so it had been contradicting the summary dock
        of its own window on every Ky run since v0.1.127."""
        p = _with_standard(_slope())
        p.settings.methods.enabled_methods = ["bishop_simplified",
                                              "ordinary_fellenius"]
        w = _window(p)
        _compute_all(w)
        w.act_interpret()
        win = w.interpret_windows[-1]
        _WINDOWS.append(win)
        try:
            first = win.cb_method.itemText(0)
            assert "Over-design factor" in first, first
            assert "FoS =" not in first, first
        finally:
            win.close()

    def test_interpret_without_a_standard_still_says_factor_of_safety(self):
        w = _window(_slope())
        _compute(w)
        w.act_interpret()
        win = w.interpret_windows[-1]
        _WINDOWS.append(win)
        try:
            assert "Factor of safety" in win.summary_dock.label.text()
            assert "Over-design" not in win.summary_dock.label.text()
        finally:
            win.close()


# ======================================================================
@_requires_qt
class TestTheNumberDoesNotMove:
    """Labelling is labelling. If any of this moved a digit it would be a
    different defect from the one being fixed."""

    def test_the_factored_run_is_the_one_the_engine_produces(self):
        """The window reports exactly what ``run_analysis`` returned — the
        caption is chosen from the report, never by re-running anything."""
        from ogr_slip2d.analysis_runner import run_analysis

        p = _with_standard(_slope())
        outcome = run_analysis(p, ["bishop_simplified"])
        engine = outcome.results["bishop_simplified"].critical.fos

        w = _window(_with_standard(_slope()))
        _compute(w)
        shown = w.last_search_result.critical.fos
        assert shown == engine, (shown, engine)

    def test_the_caption_does_not_touch_the_value(self):
        """Same project, same seed, with and without the standard: the two
        numbers differ because the partial factors differ, and each one is
        reproducible on its own."""
        from ogr_slip2d.analysis_runner import run_analysis

        plain = run_analysis(_slope(), ["bishop_simplified"])
        again = run_analysis(_slope(), ["bishop_simplified"])
        a = plain.results["bishop_simplified"].critical.fos
        b = again.results["bishop_simplified"].critical.fos
        assert a == b, (a, b)

        w = _window(_slope())
        _compute(w)
        assert w.last_search_result.critical.fos == a


# ======================================================================
@_requires_qt
class TestTheReportIsClearedWithItsResults:
    """A report that outlives its run captions the wrong number."""

    def test_a_fresh_window_has_none(self):
        w = _window(_slope())
        assert w.last_factor_report is None

    def test_a_new_project_clears_it(self):
        w = _window(_with_standard(_slope()))
        _compute(w)
        assert w.last_factor_report.applied is True
        w.project.is_dirty = False
        w.act_new()
        assert w.last_factor_report is None
        assert w.last_compute_warnings == []

    def test_loading_the_demo_clears_it(self):
        w = _window(_with_standard(_slope()))
        _compute(w)
        assert w.last_factor_report.applied is True
        w.project.is_dirty = False
        w.act_load_demo()
        assert w.last_factor_report is None

    def test_the_three_reset_sites_stay_in_step(self):
        """``last_factor_report`` belongs to the same run as the two note
        lists, so it is cleared wherever they are. A fourth reset site added
        later without it would leave the caption behind."""
        src = Path(__file__).resolve().parents[1] / "ogr_gui" / \
            "main_window.py"
        text = src.read_text(encoding="utf-8")
        assert text.count("self.last_factor_report = None") == \
            text.count("self.last_statistics_notes = []"), \
            "a reset site clears the notes but not the factor report"


# ======================================================================
@_requires_qt
class TestTheOpenPanelIsRefreshedByEveryRun:
    """The refresh used to sit inside ``if self.last_compute_warnings:``,
    so the one run guaranteed to leave the panel wrong — a clean one — was
    the only run that never refreshed it."""

    def test_a_clean_run_empties_an_open_panel(self):
        w = _window(_with_standard(_slope()))
        _compute(w)
        w.act_analysis_notes()
        panel = w._analysis_notes_panel
        try:
            assert any("Design standard applied" in n for n in panel.notes)
            # A second run with nothing to say. Driven through the real
            # completion path with a worker that produced no notes, rather
            # than hunting for a fixture that happens to be quiet: what is
            # under test is that the refresh is not gated on there BEING
            # notes, and a fixture that stops being quiet later would turn
            # this into a test of the fixture.
            class _Quiet:
                warnings: list = []
                factor_report = None

            w.worker = _Quiet()
            w._on_compute_done(w.last_search_results)
            assert w.last_compute_warnings == [], w.last_compute_warnings
            assert panel.notes == [], panel.notes
        finally:
            panel.close()


# ======================================================================
@_requires_qt
class TestTheTranslation:
    """Regla 2: every wrapped key needs its Spanish, and the terminology is
    the standard geotechnical one."""

    def test_the_caption_and_the_sentence_are_translated(self):
        from ogr_gui.i18n import current_language, set_language, tr

        _app()
        prev = current_language()
        try:
            set_language("es")
            assert tr("Over-design factor") == \
                "Factor de sobredimensionamiento"
            sentence = tr(
                "Design standard applied: %s — the reported value is an "
                "over-design factor, not a factor of safety, and must "
                "exceed 1")
            assert "sobredimensionamiento" in sentence
            assert "factor de seguridad" in sentence
            assert sentence.startswith("Norma de diseño aplicada")
        finally:
            set_language(prev)

    def test_the_status_bar_is_translated_end_to_end(self):
        """The caption reaches the bar through ``tr()``, not around it."""
        from ogr_gui.i18n import current_language, set_language

        prev = current_language()
        w = _window(_with_standard(_slope()))
        try:
            set_language("es")
            _compute(w)
            assert "sobredimensionamiento" in _status(w).lower(), _status(w)
        finally:
            set_language(prev)

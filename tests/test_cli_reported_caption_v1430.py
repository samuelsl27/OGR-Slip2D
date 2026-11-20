# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.430 (D405) — under a design standard, every door says what the
numbers it prints ARE.

The invariant: with a design standard applied, a run whose reported value
is a critical seismic coefficient or a Newmark displacement is called that,
and the over-design factor is called that where it is printed. One rule
decides it (``ogr_slip2d.reported``: ``run_caption`` and ``standard_note``)
and each door asks it for what it prints:

* the command line prints the Ky or the displacement alone, so its heading
  is the Ky's or the displacement's and its note says what that is;
* the window prints both: the factor of the critical surface in the status
  bar and the results panel (an over-design factor, by the design of
  v0.1.165), the Ky or the displacement in Interpret. Its first note says
  both things, and Interpret calls that factor ODF(0), not FS(0);
* an agent's analysis shown in the window carries the same note, and the
  agents' guide says the same.

Until this version the command line resolved the precedence the other way
round (``if seismic_objective and not factored``, reported in v0.1.165 and
not fixed then). With a standard and Newmark it printed a displacement in
centimetres under "Over-design factor" -- 187.2311 for a slope that moves
1.87 m, in the review of 0.1.429 -- under a note saying the value must
exceed 1, a reading on the unsafe side. The window's first note said the
over-design sentence alone on every run, the agent's bridge said nothing,
and the agents' guide said "the number is an OVER-DESIGN factor".

The first version of this fix gave the window the command line's sentence
("the reported value is the critical seismic coefficient ... not an
over-design factor"), right beside a status bar printing an over-design
factor. The review of 0.1.430 caught it; the test now reads the bar too.

The reference is external, on the plane of
``tests/test_newmark_user_surfaces_v1429.py`` (dry sand, φ = 30°, the user's
polyline (2, 2)–(30, 10), a focus that leaves it the only surface) with a
custom standard whose partial factor divides tan φ by 1.25, as Eurocode 7
does (``ogr_core.project.design_factors``):

* the factor of a cohesionless plane is ``tan φ / tan β``; the factored one,
  the over-design factor, ``tan φd / tan β`` with ``tan φd = tan φ / 1.25``;
* its yield acceleration is ``tan(φd − β)`` (Newmark 1965), measured
  1.5e-7 off in the run;
* its displacement under the rectangular pulse is
  ``u = V²/(2 g N)·(1 − N/A)`` at that Ky.

The number each door prints is checked against those -- the command
line's column, the window's status bar, Interpret's Ky and ODF(0) -- to
the half unit of its last printed digit plus 1e-5 relative, above the
residues of the engine against them, measured: 2.6e-6 on the factor (Janbu
on this plane), 1.5e-7 on the Ky, 2.3e-7 on the displacement at the
closed-form Ky. A heading cannot be right over a wrong number.

The command line also escapes what it prints from the model: rich reads
square brackets as its markup, and a seismic record called
"El Centro [/NS]" aborted ``compute`` with a MarkupError.

Cost: about 5 s the file alone, most of it importing the interface and
building one window, which the window's tests need: the note is checked
through the real compute-finished path, beside the status bar it has to
agree with. The runs are small, a few hundredths of a second each.
"""
from __future__ import annotations

import math
import os
import re

_FACTOR = 1.25


def _plane(mode, standard=True):
    """The plane of 0.1.429, reporting a Newmark displacement, a Ky or a
    factor (``mode``), with the custom standard or without one."""
    from test_newmark_user_surfaces_v1429 import _plane_project
    p = _plane_project()
    cfg = p.settings.seismic
    if mode == "ky":
        cfg.newmark, cfg.compute_ky = False, True
    elif mode == "fos":
        cfg.newmark, cfg.compute_ky = False, False
        p.seismic.enabled = False
    if standard:
        ds = p.settings.design_standard
        ds.enabled, ds.standard = True, "custom"
        ds.factor_cohesion = ds.factor_friction = _FACTOR
    return p


def _closed(mode, standard=True):
    """What the plane's reported value is in closed form, in the unit the
    command line prints it in (the displacement in centimetres)."""
    from test_newmark_user_surfaces_v1429 import (_A, _BETA, _PHI, _T0,
                                                  _closed_form)
    tan_phi = math.tan(math.radians(_PHI)) / (_FACTOR if standard else 1.0)
    if mode == "fos":
        return tan_phi / math.tan(math.radians(_BETA))
    ky = math.tan(math.atan(tan_phi) - math.radians(_BETA))
    if mode == "ky":
        return ky
    return 100.0 * _closed_form(_A, ky, _T0)


def _close_enough(printed, expected, decimals=4):
    """The half unit of the last decimal printed, and 1e-5 relative: above
    the engine's residues against these closed forms (2.6e-6 at most, on the
    factor), well below anything a wrong number would be off by."""
    return abs(printed - expected) <= 0.5 * 10.0 ** -decimals \
        + 1e-5 * abs(expected)


def _invoke(tmp_path, args):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from typer.testing import CliRunner

    import ogr_cli.__main__ as cli
    # wide, or rich wraps the caption and cuts the method names
    result = CliRunner().invoke(cli.app, args, env={"COLUMNS": "200"})
    assert result.exit_code == 0, (result.exit_code, result.output,
                                   result.exception)
    return result.output


def _compute(tmp_path, project):
    """``compute`` on the saved project, the real run included."""
    path = tmp_path / "plane.ogr"
    project.save(path)
    return _invoke(tmp_path, ["compute", str(path)])


def _heading_and_value(output):
    """The heading of the critical column and the number under it."""
    rows = [[c.strip() for c in line.split("│")[1:-1]]
            for line in output.splitlines() if "│" in line]
    # v0.1.476 — a missing row fails with the output, not a bare
    # StopIteration: on Linux's CI no row was found and nobody could see why
    head = next((r for r in rows if r and r[0] == "Method"), None)
    row = next((r for r in rows if r and r[0] == "janbu_simplified"), None)
    assert head is not None and row is not None, (
        "no 'Method' or 'janbu_simplified' row in the table:\n" + output)
    return head[1], float(row[1])


def _standard_line(output):
    lines = [ln for ln in output.splitlines()
             if ln.startswith("Design standard applied:")]
    assert len(lines) <= 1, lines
    return lines[0] if lines else None


# ======================================================================
class TestTheCommandLine:

    def test_a_newmark_run_with_a_standard_is_a_displacement(self, tmp_path):
        out = _compute(tmp_path, _plane("newmark"))
        heading, value = _heading_and_value(out)
        # 0.1.429 printed "Over-design factor" over these centimetres
        assert heading == "Newmark disp. (cm)", out
        assert _close_enough(value, _closed("newmark")), (value, out)
        line = _standard_line(out)
        assert "the Newmark displacement with the partial factors applied" \
            in line and "must exceed 1" not in line, out

    def test_a_ky_run_with_a_standard_is_a_seismic_coefficient(self, tmp_path):
        out = _compute(tmp_path, _plane("ky"))
        heading, value = _heading_and_value(out)
        assert heading == "Critical Ky", out
        assert _close_enough(value, _closed("ky")), (value, out)
        line = _standard_line(out)
        assert "the critical seismic coefficient with the partial factors" \
            in line and "must exceed 1" not in line, out

    def test_a_factor_with_a_standard_is_still_an_over_design_factor(
            self, tmp_path):
        """The control: what the command line has said since v0.1.127."""
        out = _compute(tmp_path, _plane("fos"))
        heading, value = _heading_and_value(out)
        assert heading == "Over-design factor", out
        assert _close_enough(value, _closed("fos")), (value, out)
        assert "is an over-design factor, not a factor of safety, and must " \
            "exceed 1." in _standard_line(out), out

    def test_without_a_standard_nothing_is_said(self, tmp_path):
        """The other control: no note, and the headings of 0.1.127."""
        out = _compute(tmp_path, _plane("fos", standard=False))
        assert _heading_and_value(out)[0] == "Critical FoS", out
        assert _close_enough(_heading_and_value(out)[1],
                             _closed("fos", standard=False)), out
        assert _standard_line(out) is None, out
        out = _compute(tmp_path, _plane("ky", standard=False))
        assert _heading_and_value(out)[0] == "Critical Ky", out
        assert _close_enough(_heading_and_value(out)[1],
                             _closed("ky", standard=False)), out
        assert _standard_line(out) is None, out


class TestTheCommandLineEscapesTheModel:
    """Square brackets in a name are rich's markup unless escaped."""

    def test_a_record_name_in_a_note(self, tmp_path):
        from ogr_core.loads.seismic_record import SeismicRecord
        p = _plane("newmark", standard=False)
        # one sample: the run says it cannot be integrated, by its name
        bad = SeismicRecord(name="El Centro [/NS]", dt=0.01,
                            accelerations=[0.1])
        p.seismic_records = [bad]
        p.settings.seismic.record_id = bad.id
        out = _compute(tmp_path, p)     # 0.1.429: exit 1, MarkupError
        assert "the seismic record 'El Centro [/NS]' cannot be integrated" \
            in out, out

    def test_a_material_name_in_the_summary(self, tmp_path):
        p = _plane("fos", standard=False)
        p.materials[0].name = "Clay [weathered]"
        path = tmp_path / "plane.ogr"
        p.save(path)
        out = _invoke(tmp_path, ["info", str(path)])
        # 0.1.429 printed "Clay " and lost the rest without a word
        assert "Clay [weathered]" in out, out


# ======================================================================
_WINDOWS: list = []


def _window():
    from PySide6.QtWidgets import QApplication

    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    if not _WINDOWS:
        _WINDOWS.append(MainWindow())
    return _WINDOWS[0]


def _in_window(project):
    """Compute ``project`` in the window through the real compute-finished
    path (``_on_compute_done``), without the modal dialog."""
    from ogr_gui.main_window import _ComputeWorker
    w = _window()
    w.project = project
    w.canvas.set_project(project)
    errors: list = []
    w.worker = _ComputeWorker(project, ["janbu_simplified"])
    w.worker.failed.connect(errors.append)
    w.worker.run()
    assert not errors, errors
    w._on_compute_done(w.worker.results)
    return w


class _English:
    def __enter__(self):
        from ogr_gui.i18n import current_language, set_language
        self.before = current_language()
        set_language("en")

    def __exit__(self, *exc):
        from ogr_gui.i18n import set_language
        set_language(self.before)


# v0.1.430 -- one compute per mode in the window, read by several tests.
# File-local (tests/test_shared_test_caches_v1378.py fails if another file
# reaches it).
_WINDOW_RUNS: dict = {}


def _window_run(mode):
    """``(first note, the note said in English, status bar, result, factor
    report)`` of one compute of the plane in the window."""
    if mode not in _WINDOW_RUNS:
        from ogr_gui.core_messages import note_line
        with _English():
            w = _in_window(_plane(mode))
            note = w.last_compute_warnings[0]
            _WINDOW_RUNS[mode] = (note, note_line(note),
                                  w.ogr_status.currentMessage(),
                                  w.last_search_result, w.last_factor_report)
    return _WINDOW_RUNS[mode]


class TestTheWindowSaysBothThings:
    """The status bar and the results panel print the critical surface's
    factor; the note says what that factor is, and what the Ky is. What
    each says is asserted first, so a tree without this fix fails by what
    it says and not by a name it lacks."""

    def test_a_ky_run(self):
        note, said, bar, _res, _rep = _window_run("ky")
        # 0.1.429: the over-design sentence alone
        assert "critical seismic coefficient is computed with the partial " \
            "factors applied" in said, said
        # the bar prints the factor of that surface: the note says what it
        # is, the first version of this fix said it was not one. (The
        # results panel says the same through the same ``fos_label``, but
        # not here: with the search's population empty it said "No results
        # yet." until v0.1.443, D401, which made it show the user's
        # surface; this test was written before and reads the bar.)
        assert bar.startswith("Over-design factor ("), bar
        assert "over-design factor, not a factor of safety, and must " \
            "exceed 1" in said, said
        value = float(re.search(r"\): ([0-9.]+)", bar).group(1))
        assert _close_enough(value, _closed("fos"), decimals=3), bar
        from ogr_slip2d import reported as R
        assert note.code == R.STANDARD_KY_FACTOR, note

    def test_a_newmark_run(self):
        note, said, bar, _res, _rep = _window_run("newmark")
        assert "Newmark displacement are computed with the partial" in said
        assert bar.startswith("Over-design factor ("), bar
        assert "must exceed 1" in said, said
        value = float(re.search(r"\): ([0-9.]+)", bar).group(1))
        assert _close_enough(value, _closed("fos"), decimals=3), bar
        from ogr_slip2d import reported as R
        assert note.code == R.STANDARD_NEWMARK_FACTOR, note

    def test_a_factor_run_is_the_sentence_of_always(self):
        """The control: what the window has said since v0.1.165."""
        _note, said, bar, _res, _rep = _window_run("fos")
        assert "the reported value is an over-design factor, not a factor " \
            "of safety, and must exceed 1." in said, said
        assert bar.startswith("Over-design factor ("), bar

    def test_the_note_follows_the_language_of_the_moment(self):
        """Kept with its code: computed in English, read in Spanish."""
        from ogr_gui.core_messages import note_line
        from ogr_gui.i18n import current_language, set_language
        note = _window_run("ky")[0]
        before = current_language()
        set_language("es")
        try:
            said = note_line(note)
        finally:
            set_language(before)
        assert said.startswith("Norma de diseño aplicada: "), said
        assert "debe ser mayor que 1" in said, said

    def test_interpret_calls_that_factor_an_over_design_factor(self):
        """Through Interpret's summary, which says the Ky and, beside it,
        the factor of the same surface. On the circular slope of
        ``test_design_factor_report_gui_v1165``: on the plane, whose search
        the focus empties, the summary said "No results to display." until
        v0.1.443 (D401), so this test reads the circular slope. The label
        is what is under test;
        the number beside it is the critical surface's own factor."""
        from test_design_factor_report_gui_v1165 import _slope, _with_standard

        from ogr_gui.interpret_window import _SummaryDock
        from ogr_slip2d.analysis_runner import run_analysis
        p = _with_standard(_slope())
        p.settings.seismic.compute_ky = True
        out = run_analysis(p, ["bishop_simplified"])
        crit = out.results["bishop_simplified"].critical
        assert out.factor_report.applied and crit is not None
        said = []
        with _English():
            for report in (out.factor_report, None):
                dock = _SummaryDock()     # one each: a dock keeps its report
                _WINDOWS.append(dock)
                try:
                    dock.show_result(out.results["bishop_simplified"], None,
                                     report)
                    said.append(dock.label.text())
                finally:
                    dock.close()
        # 0.1.429 called it FS(0), and the status bar "Over-design factor"
        assert "ODF(0) = %.3f" % crit.fos in said[0], said[0]
        assert "FS(0) = %.3f" % crit.fos in said[1] \
            and "ODF(0)" not in said[1], said[1]
        # and the numbers Interpret prints, on the plane, against their
        # closed forms (the summary itself could not show the plane when
        # this was written: D401, fixed in v0.1.443)
        from ogr_gui.interpret_window import _reported_value
        _n, _s, _b, res, report = _window_run("ky")
        with _English():
            text, tip = _reported_value(res, res.critical, None, report)
        assert _close_enough(float(text), _closed("ky")), text
        assert tip.startswith("ODF(0) = ") and _close_enough(
            float(tip.split("=")[1]), _closed("fos"), decimals=3), tip


class TestTheAgentsBridge:
    """An agent's analysis shown in the window, as a Compute shows it."""

    def test_it_carries_the_note_and_refreshes_the_panel(self):
        from ogr_gui.agent_bridge import WindowHost
        from ogr_gui.core_messages import note_line
        from ogr_slip2d.analysis_runner import run_analysis
        with _English():
            w = _in_window(_plane("fos", standard=False))
            w.act_analysis_notes()
            panel = w._analysis_notes_panel
            try:
                out = run_analysis(_plane("ky"))
                WindowHost(w).show_analysis(out.results, out.factor_report,
                                            out.warnings)
                notes = w.last_compute_warnings
                # 0.1.429: only the run's warnings, no word of the standard
                said = note_line(notes[0]) if notes else ""
                assert "critical seismic coefficient is computed with the " \
                    "partial factors applied" in said, notes
                assert len(notes) == \
                    1 + len(out.factor_report.notes) + len(out.warnings)
                # and the open panel shows them, not the previous run's
                assert panel.notes[:1] == notes[:1], panel.notes
            finally:
                panel.close()


class TestTheAgentsGuide:

    def test_it_says_what_a_ky_is_under_a_standard(self):
        from ogr_mcp.guide import GUIDE
        flat = " ".join(GUIDE.split())
        assert "the number is an OVER-DESIGN factor" not in flat
        assert "a Ky or a Newmark displacement stays what it is, computed " \
            "with the partial factors applied, and need not be above 1" \
            in flat, flat


# ======================================================================
class TestTheSentences:
    """Regla 2, and the census each family of codes keeps."""

    def _samples(self):
        from ogr_core.project.design_factors import FactorReport
        from ogr_slip2d import reported as R
        report = FactorReport(standard="custom", applied=True)
        out = {}
        for caption, code in ((R.OVERDESIGN, R.STANDARD_OVERDESIGN),
                              (R.KY, R.STANDARD_KY),
                              (R.NEWMARK, R.STANDARD_NEWMARK)):
            out[code] = R.standard_note(caption, report)
        for caption, code in ((R.KY, R.STANDARD_KY_FACTOR),
                              (R.NEWMARK, R.STANDARD_NEWMARK_FACTOR)):
            out[code] = R.standard_note(caption, report, shows_factor=True)
        return out

    def test_one_sentence_per_caption_and_door_and_none_without_a_standard(
            self):
        from ogr_core.project.design_factors import FactorReport
        from ogr_slip2d import reported as R
        samples = self._samples()
        assert sorted(samples) == sorted(R.REPORTED_NOTES)
        assert all(n.code == code for code, n in samples.items())
        report = FactorReport(standard="custom", applied=True)
        assert R.standard_note(R.OVERDESIGN, report, shows_factor=True) \
            .code == R.STANDARD_OVERDESIGN
        for caption in (R.FOS, R.OVERDESIGN, R.KY, R.NEWMARK):
            assert R.standard_note(caption, FactorReport()) is None
            assert R.standard_note(caption, None) is None

    def test_every_code_is_in_the_catalogue_with_its_spanish(self):
        import string

        from ogr_gui import core_messages
        from ogr_gui.i18n import _DICTS
        from ogr_slip2d.reported import REPORTED_NOTES
        es = _DICTS["es"]

        def fields(template):
            return sorted(f for _t, f, _s, _c
                          in string.Formatter().parse(template) if f)

        assert set(REPORTED_NOTES) <= set(core_messages._catalogue())
        for code, spec in REPORTED_NOTES.items():
            assert spec.english in es, code
            assert fields(es[spec.english]) == fields(spec.english), code

    def test_in_spanish(self):
        from ogr_gui import core_messages
        from ogr_gui.i18n import current_language, set_language
        from ogr_slip2d import reported as R
        before = current_language()
        set_language("es")
        try:
            said = {code: core_messages.note_text(n)
                    for code, n in self._samples().items()}
        finally:
            set_language(before)
        for code, text in said.items():
            # v0.1.434 (D412) -- the window names the standard («custom»
            # by its own key, the owner's decision): it printed the id
            assert text.startswith(
                "Norma de diseño aplicada: Norma personalizada: "), \
                (code, text)
            assert text.endswith("."), (code, text)    # D355
            assert re.search(r"[A-Za-z]+ applied|reported value|factor "
                             r"shown", text) is None, (code, text)
        # the command line's two say no factor; the window's three, one
        for code in (R.STANDARD_KY, R.STANDARD_NEWMARK):
            assert "mayor que 1" not in said[code], said[code]
        for code in (R.STANDARD_OVERDESIGN, R.STANDARD_KY_FACTOR,
                     R.STANDARD_NEWMARK_FACTOR):
            assert "mayor que 1" in said[code], said[code]
        assert "coeficiente sísmico crítico" in said[R.STANDARD_KY_FACTOR]
        assert "desplazamiento de Newmark" in said[R.STANDARD_NEWMARK_FACTOR]

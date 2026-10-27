# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.370 (D344) — fixed texts that were still English with the interface in
Spanish: ten formulas of *Define Materials*, two charts, the stage list of
*Interpret Groundwater*, "Añadido line", "[deg]" in the PDF, the proposed
name of the report and the filters of the file dialogs.

Why the censuses did not see them (rule 2 has a test, and two budgets):

* a class dictionary is not a ``tr()`` call: ``_FORMULA_TEXT`` was written
  to its label untranslated, and the key census only reads literal
  ``tr("…")`` calls;
* matplotlib's ``label=``/``set_ylabel`` and ``QFileDialog`` were outside the
  census's list of receivers;
* "Añadido line" was ``tr("Added %s") % kind.value``: the template was
  translated, the enum's value was data.

What these tests protect:

* every formula with words has its Spanish, with the same symbols, and the
  dialog shows it; the formulas that are only symbols carry no English word;
* *Interpret Groundwater*: the free surface's legend and the "[FS]" of a
  stage with factors, in Spanish;
* the statistics convergence chart: its legend and its right axis;
* an annotation added says its kind by its name ("Anotación añadida:
  Línea");
* the PDF: "Ángulo de rozamiento [°]" (and "[°]" in English too, as the
  slice table writes φ);
* the report's proposed name and filter, through the real dialog call;
* the census this file adds: every literal title or filter of a
  ``QFileDialog`` in ``ogr_gui`` with a word in it goes through ``tr()``, and
  every translated filter keeps its patterns.
"""
from __future__ import annotations

import ast
import re
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent
_MISSING = object()

#: The models whose formula has words; the others are only symbols.
_WITH_WORDS = ("anisotropic_linear", "shear_normal_function",
               "c_phi_function", "step_function", "discrete_function",
               "shansep", "anisotropic_strength_function",
               "generalized_anisotropic", "snowden_anisotropic_linear",
               "undrained_slope_distance")

#: The symbols a translation must keep, each the same number of times.
_SYMBOLS = "τσφΔ∞′ₙ·=+−^≥°√₁₃()"

#: Tokens of the symbol-only formulas that are notation, not words.
_NOTATION = {"tan", "log", "JRC", "JCS", "OCR", "top", "datum", "min"}


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@contextmanager
def _spanish():
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language("es")
    try:
        yield
    finally:
        set_language(before)


@contextmanager
def _swap(owner, name, value):
    raw = (owner.__dict__.get(name, _MISSING) if isinstance(owner, type)
           else getattr(owner, name))
    setattr(owner, name, value)
    try:
        yield
    finally:
        if raw is _MISSING:
            delattr(owner, name)
        else:
            setattr(owner, name, raw)


def _es():
    from ogr_gui.i18n import _DICTS
    return _DICTS["es"]


# ======================================================================
class TestTheFormulas:

    def test_every_formula_with_words_has_its_spanish(self):
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog as D)
        es = _es()
        for mid in _WITH_WORDS:
            english = D._FORMULA_TEXT[mid]
            spanish = es.get(english)
            assert spanish and spanish != english, (mid, english)
            for ch in _SYMBOLS:
                assert english.count(ch) == spanish.count(ch), (mid, ch)

    def test_the_others_are_only_symbols(self):
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog as D)
        for mid, formula in D._FORMULA_TEXT.items():
            if mid in _WITH_WORDS:
                continue
            words = {w for w in re.findall(r"[A-Za-z]{3,}", formula)
                     if w not in _NOTATION}
            assert not words, (mid, words)

    def test_the_dialog_shows_it_in_spanish(self):
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog)
        _app()
        mat = Material(name="S", strength=MohrCoulomb(cohesion=5.0,
                                                      friction_angle=30.0))
        with _spanish():
            dlg = MaterialPropertiesDialog([mat], None)
            try:
                i = dlg.cbo_strength.findData("shear_normal_function")
                assert i >= 0
                dlg.cbo_strength.setCurrentIndex(i)
                text = dlg.lbl_strength_formula.text()
            finally:
                dlg.close()
        assert text == "τ = f(σ′ₙ)  (tabla lineal a tramos)", text


# ======================================================================
class TestInterpretGroundwater:

    def test_the_stage_flag_and_the_free_surface_legend(self):
        import test_fos_chart_v1308 as fc
        p, w = fc._drawdown(calc_sf=True)
        iw = None
        try:
            with _spanish(), fc._no_modals():
                iw = fc._interpret(p, w)
                items = [iw.cbo_stage.itemText(i)
                         for i in range(iw.cbo_stage.count())]
                iw.chk_surface.setChecked(True)
                iw._redraw()
                legend = iw.canvas.figure.axes[0].get_legend()
                texts = ([t.get_text() for t in legend.get_texts()]
                         if legend is not None else [])
        finally:
            if iw is not None:
                iw.close()
            p.is_dirty = False
        assert any(t.endswith("[FS]") for t in items), items
        assert not any("[SF]" in t for t in items), items
        assert "Superficie freática (P=0)" in texts, texts


class TestTheConvergenceChart:

    def test_its_legend_and_right_axis(self):
        import test_statistics_gui_v138 as sg
        p = sg._project(n=12)
        sg._define_vars(p)
        with _spanish():
            w = sg._window(p)
            try:
                w._info = lambda *a: None
                w._compute_statistics()
                sw = w._stats_window
                mid = next(iter(w._prob_result.by_method))
                sw._plot_convergence(mid)
                ax, ax2 = sw.canvas.figure.axes[:2]
                legend = [t.get_text() for t in ax.get_legend().get_texts()]
                right = ax2.get_ylabel()
                sw.close()
            finally:
                p.is_dirty = False
                w.close()
        assert "probabilidad de rotura" in legend, legend
        assert right == "Probabilidad de rotura (%)", right


class TestAnAnnotationAdded:

    def test_it_is_said_by_its_kind_name(self):
        from PySide6.QtWidgets import QInputDialog

        from ogr_core.annotations import AnnotationKind
        from ogr_gui.main_window import MainWindow
        _app()
        with _spanish():
            w = MainWindow()
            try:
                w.act_load_demo()
                with _swap(QInputDialog, "getText", staticmethod(
                        lambda *a, **k: ("0,0 10,10", True))):
                    w._start_annotation(AnnotationKind.LINE)
                bar = w.statusBar().currentMessage()
            finally:
                w.project.is_dirty = False
                w.close()
        assert bar.startswith("Anotación añadida: Línea"), bar
        assert "line" not in bar, bar


# ======================================================================
class TestThePdf:

    def test_the_friction_angle_unit(self):
        import test_report_spanish_v1355 as rs
        from ogr_gui.core_messages import note_text
        from ogr_gui.labels import method_name
        english = {t for _k, t in rs._capture()}
        with _spanish():
            spanish = {t for _k, t in rs._capture(
                translate=note_text, method_name=method_name)}
        assert "Friction Angle [°]" in english
        assert "Ángulo de rozamiento [°]" in spanish, sorted(
            t for t in spanish if "rozamiento" in t)
        assert not any("[deg]" in t for t in english | spanish)


class TestTheReportFile:

    def test_its_proposed_name_and_filter(self):
        """With a computed demo (without results the action says so in a
        box), its figures dialog accepted, and any other modal turned into a
        failure instead of a wait without end."""
        import test_fos_chart_v1308 as fc
        from PySide6.QtWidgets import QFileDialog

        import ogr_gui.dialogs.report_dialog as rd
        from ogr_gui.main_window import MainWindow, _ComputeWorker
        _app()
        asked = []

        def save(parent, title, name, flt, *a, **k):
            asked.append((name, flt))
            return "", ""
        with _spanish():
            w = MainWindow()
            try:
                w.act_load_demo()
                w.worker = _ComputeWorker(w.project, ["bishop_simplified"])
                w.worker.run()
                w._on_compute_done(w.worker.results)
                with fc._no_modals(), \
                        _swap(rd.ReportDialog, "exec", lambda self: 1), \
                        _swap(QFileDialog, "getSaveFileName",
                              staticmethod(save)):
                    w.act_generate_report()
            finally:
                w.project.is_dirty = False
                w.close()
        assert asked, "the report did not ask for a file"
        name, flt = asked[0]
        assert name.endswith("_informe.pdf"), name
        assert flt == "Archivos PDF (*.pdf)", flt


# ======================================================================
#: Words a filter may keep: names of formats.
_FORMATS = {"CSV", "PNG", "JPEG", "JPG", "PDF", "DXF", "OGR", "TXT", "DAT",
            "BMP", "JSON"}


def _file_dialog_literals():
    """Every literal string argument of a ``QFileDialog.get*`` call in
    ogr_gui that is NOT inside ``tr()``: ``(file, line, text)``."""
    out = []
    for path in sorted((_ROOT / "ogr_gui").rglob("*.py")):
        if "i18n" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr.startswith("get")
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "QFileDialog"):
                continue
            for arg in list(node.args) + [k.value for k in node.keywords]:
                if (isinstance(arg, ast.Constant)
                        and isinstance(arg.value, str)):
                    out.append((path.name, node.lineno, arg.value))
    return out


class TestTheFileDialogs:

    def test_no_word_outside_tr(self):
        found = []
        for name, line, text in _file_dialog_literals():
            words = {w for w in re.findall(r"[A-Za-z]{2,}", text)
                     if w.upper() not in _FORMATS}
            if words:
                found.append((name, line, text))
        assert not found, found

    def test_every_translated_filter_keeps_its_patterns(self):
        es = _es()
        n = 0
        for key, value in es.items():
            if "(*." in key and ";;" in key or key.endswith("(*.pdf)"):
                n += 1
                pat = re.findall(r"\([^)]*\*[^)]*\)", key)
                assert re.findall(r"\([^)]*\*[^)]*\)", value) == pat, key
        assert n >= 10, n

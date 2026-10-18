# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.318 (D300) — no visible text of the interface skips ``tr()``, in all
of ``ogr_gui``.

D291 (0.1.290) and D291b (0.1.293) translated the main window and fixed it
with two AST tests that look at ``main_window.py`` only. Outside it, text
never went through ``tr()`` and showed in English with the interface in
Spanish: 116 texts in 26 files on 2026-10-09 (the census of the ticket), and
about 200 sites in 32 files at 0.1.316 once the three detections are joined.

This test joins them, over every module of ``ogr_gui`` but the dictionary:

* **visible**: a literal or an f-string with letters handed to a
  constructor or setter whose text the user reads (``QLabel``,
  ``setWindowTitle``, ``setToolTip``, ``addRow``, table headers…);
* **messages**: the same in ``showMessage``, the window's ``_info`` and the
  text of a ``QMessageBox`` (D291);
* **f-strings**: any f-string with letters, wherever it is (D291b), except
  where it is not interface text — a style sheet, an exception's message,
  the data of a combo item, a name the ``.ogr`` keeps, an undo step's name
  (the agent reads those in English) — each with its reason below.

What is left and is not to be translated (a proper name, a symbol, a unit)
goes in ``EXCEPTIONS`` with its reason; every one of them must still be in
the code. Everything else counts against ``BUDGET``, which only goes down:
P8h converts the interface family by family until it is zero.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent / "ogr_gui"

#: Calls whose FIRST argument is text the user reads.
_FIRST = {"setWindowTitle", "QLabel", "QPushButton", "QCheckBox",
          "QGroupBox", "QRadioButton", "QAction", "setText", "setToolTip",
          "setStatusTip", "setPlaceholderText", "setTitle", "setWhatsThis",
          "addRow", "showMessage", "QToolButton", "setSpecialValueText",
          # the titles of a tool bar, a dock and a menu
          "QToolBar", "QDockWidget", "QMenu", "addMenu", "addAction",
          "QProgressDialog", "setLabelText",
          # the text of a combo or list item (its data is the second)
          "addItem"}
#: QInputDialog.get*(parent, title, label, ...): the title and the label.
_INPUTS = ("getText", "getInt", "getDouble", "getItem", "getMultiLineText")
#: Calls whose SECOND argument is.
_SECOND = {"addTab", "setTabText", "insertTab", "insertItem"}
#: Calls whose first argument is a LIST of texts the user reads.
_HEADERS = {"setHorizontalHeaderLabels", "setVerticalHeaderLabels",
            "setHeaderLabels"}
_BOXES = ("information", "warning", "critical", "question")

#: Calls whose arguments are not interface text, whatever they hold.
_NOT_TEXT = {
    # CSS, not words
    "setStyleSheet",
    # names the .ogr, the agent or a file keep
    "setObjectName", "setProperty",
    # the data behind a combo or list item, as opposed to its text
    "setData", "findData", "findText",
    # the console, not the interface
    "print",
}

#: A lone axis name is a symbol, the same in every language.
_AXES = {"X", "Y", "Z", "x", "y", "z"}

#: What is left that is not to be translated, with the reason.
#: (file relative to ogr_gui, the text with {} for each field): reason
EXCEPTIONS: dict = {
    # the product's name and the PROJECT's name (data: a new project is
    # named "Untitled", the demo "Demo slope"), as test_window_english_left
    ("main_window.py", "OGR Slip2D v{} — OpenGeoRock Suite"):
        "the product's name and version",
    ("main_window.py", "OGR Slip2D v{} — Untitled"):
        "the product's name and the name of a new project",
    ("main_window.py", "OGR Slip2D v{} — {}"):
        "the product's name and the project's name",
    ("main_window.py", "OGR Slip2D v{} — Demo slope"):
        "the product's name and the name of the demo project",
    ("main_window.py", "{}_report.pdf"):
        "a file name",
    # notation that reads the same in Spanish: a translation would be the
    # English again, which test_i18n_coverage_v141 counts as untranslated
    ("interpret_window.py", "FS ={}"):
        "notation: the factor of safety is FS in Spanish too",
    ("interpret_window.py", "FS ={} r ={} c=({},{})"):
        "notation: factor, radius and centre of a circle",
    ("interpret_groundwater_window.py", "H: {} … {}"):
        "notation: the range of the total head",
    ("interpret_groundwater_window.py", "u: {} … {}"):
        "notation: the range of the pore pressure",
    ("interpret_groundwater_window.py", "t = {}"):
        "notation: the time of a stage",
    ("interpret_groundwater_window.py", "{}: t = {}{}{}"):
        "notation: the number and the time of a stage",
    # v0.1.319 — units and coordinates, the same in every language
    ("canvas/graphics_items.py", "{} kN/m²"):
        "a load's magnitude and its unit",
    ("canvas/graphics_items.py", "{} → {} kN/m²"):
        "a varying load's two magnitudes and their unit",
    ("canvas/graphics_items.py", "{} kN/m"):
        "a line load's magnitude and its unit",
    ("data_tips.py", "{}: {} kPa"):
        "a quantity named by the model, its value and its unit",
    ("widgets/legend.py", "X: 0.000   Y: 0.000"):
        "notation: the coordinates of the pointer",
    ("widgets/legend.py", "X: {}   Y: {}"):
        "notation: the coordinates of the pointer",
    ("widgets/status_bar.py", "X: {}   Y: {}"):
        "notation: the coordinates of the pointer",
    ("widgets/status_bar.py", "x, y"):
        "notation: the format of the coordinates to type",
    # v0.1.320 — the rest
    ("agent_bridge.py", "The window is in the middle of an edit ({}); an "
                        "edit now would land inside it."):
        "returned to the agent, which reads English like every API message",
    ("agent_bridge.py", "OGR Slip2D v{} — {}"):
        "the product's name and the project's name",
    ("dialogs/parameter_calculator_dialog.py", "mb:"):
        "the symbol of a Hoek-Brown parameter",
    ("dialogs/parameter_calculator_dialog.py", "s:"):
        "the symbol of a Hoek-Brown parameter",
    ("dialogs/parameter_calculator_dialog.py", "a:"):
        "the symbol of a Hoek-Brown parameter",
    ("main_window.py", "ΔX (m):"):
        "notation: a displacement and its unit",
    ("main_window.py", "ΔY (m):"):
        "notation: a displacement and its unit",
    ("dialogs/define_support_dialog.py", "Type {}"):
        "the default name of a new support type, which the model keeps "
        "(like a project's 'Untitled')",
    ("dialogs/tension_crack_dialog.py", "Piezo {}"):
        "an abbreviation that reads the same in Spanish, before an id",
    ("dialogs/grid_dialogs.py", "Circular"):
        "the same word in Spanish",
    ("dialogs/project_settings_dialog.py", "%s %s %.3f g, %.1f s"):
        "a seismic record: its name, its peak acceleration in g and its "
        "duration in s",
}

#: How many may be left. Lowering it is the point; raising it needs a
#: reason in a changelog. History: 193 at 0.1.317 by these rules; 94 at
#: 0.1.318, once the interpretation windows, the statistics window, the
#: charts and the last messages outside tr() went through it; 47 at
#: 0.1.319, the canvas, the data tips, the results panel and the status bar;
#: 0 at 0.1.320, the groundwater and search dialogs and the rest (the rules
#: also read combo items and skip %-style fields from this version on).
BUDGET = 0


def _letters(text):
    """Letters outside replacement fields ({0:.2f} and %d alike) and HTML
    tags."""
    text = re.sub(r"%[-+ #0]*\d*(?:\.\d+)?[sdifgeEx]", "", text)
    text = re.sub(r"<[^>]*>", "", re.sub(r"[{][^}]*[}]", "", text))
    return any(c.isalpha() for c in text)


def _text(node):
    """The text of a string node, with {} for each field, or None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "{}"
                       for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.left, ast.Constant) \
            and isinstance(node.left.value, str):
        return node.left.value
    return None


def _call_name(node):
    f = node.func
    return getattr(f, "attr", None) or getattr(f, "id", None)


def loose(src):
    """``[(lineno, text)]`` of the interface texts of ``src`` outside
    ``tr()``, by the three rules of this module."""
    return sorted((n.lineno, _text(n)) for n in loose_nodes(ast.parse(src)))


def loose_nodes(tree):
    """The string nodes of ``tree`` that :func:`loose` reports."""
    parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    found = {}

    def flag(node):
        text = _text(node)
        if text is not None and _letters(text) and text.strip() not in _AXES:
            found[id(node)] = node

    # 1 and 2 — the arguments read on screen
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        args = node.args
        if name in _FIRST and args:
            flag(args[0])
        elif name in _SECOND and len(args) >= 2:
            flag(args[1])
        elif name in _HEADERS and args and isinstance(args[0],
                                                      (ast.List, ast.Tuple)):
            for el in args[0].elts:
                flag(el)
        elif name == "_info":
            for a in args[:2]:
                flag(a)
        elif name in _INPUTS and isinstance(node.func, ast.Attribute) \
                and getattr(node.func.value, "id", None) == "QInputDialog":
            for a in args[1:3]:
                flag(a)
        elif name in _BOXES and isinstance(node.func, ast.Attribute) \
                and getattr(node.func.value, "id", None) == "QMessageBox" \
                and len(args) >= 3:
            flag(args[1])
            flag(args[2])

    # v0.1.324 (D315) — a subclass of one of those constructors passes its
    # text up with ``super().__init__("Results", parent)``: five dock titles
    # reached the screen in English that way, unseen by the rule above.
    for cls in ast.walk(tree):
        if not isinstance(cls, ast.ClassDef):
            continue
        bases = {getattr(b, "attr", None) or getattr(b, "id", None)
                 for b in cls.bases}
        if not bases & _FIRST:
            continue
        for node in ast.walk(cls):
            if isinstance(node, ast.Call) and node.args \
                    and isinstance(node.func, ast.Attribute) \
                    and node.func.attr == "__init__" \
                    and isinstance(node.func.value, ast.Call) \
                    and getattr(node.func.value.func, "id", None) == "super":
                flag(node.args[0])

    # 3 — every f-string with letters, unless it is not interface text
    def exempt(node):
        child = node
        p = parents.get(node)
        while p is not None:
            if isinstance(p, ast.FormattedValue) and p.format_spec is child:
                return True                       # a format spec (":.1f")
            if isinstance(p, ast.Raise):
                return True                       # an exception's message
            if isinstance(p, ast.Call):
                name = _call_name(p)
                if name in _NOT_TEXT:
                    return True
                if name and (name.endswith("Command")
                             or name in ("_model_step", "undo_step")) \
                        and p.args and p.args[0] is child:
                    return True                   # an undo step's name
                if name in ("addItem", "insertItem") and child in p.args[1:]:
                    return True                   # a combo item's data
                if any(kw is child and kw.arg == "name"
                       for kw in p.keywords):
                    return True                   # a name the .ogr keeps
            child, p = p, parents.get(p)
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr) and id(node) not in found \
                and not exempt(node):
            flag(node)
    return list(found.values())


def census():
    """``{file: [(lineno, text)]}`` over every module of ``ogr_gui`` but
    the dictionary, before the exceptions."""
    out = {}
    for path in sorted(_ROOT.rglob("*.py")):
        rel = path.relative_to(_ROOT).as_posix()
        if rel.startswith("i18n/"):
            continue
        hits = loose(path.read_text(encoding="utf-8"))
        if hits:
            out[rel] = hits
    return out


def _counted():
    out = []
    for rel, hits in census().items():
        for lineno, text in hits:
            if (rel, text) not in EXCEPTIONS:
                out.append((rel, lineno, text))
    return out


class TestNoInterfaceTextSkipsTr:
    def test_what_is_left_is_within_the_budget(self):
        left = _counted()
        assert len(left) <= BUDGET, (len(left), left[:40])

    def test_the_budget_is_exact(self):
        """Lowered as it is earned: a family converted lowers it in the
        same version, so the next one cannot slip back unseen."""
        assert len(_counted()) == BUDGET

    def test_no_exception_is_a_ghost(self):
        found = {(rel, text) for rel, hits in census().items()
                 for _ln, text in hits}
        ghosts = sorted(set(EXCEPTIONS) - found)
        assert not ghosts, ghosts
        assert all(r.strip() for r in EXCEPTIONS.values())


_WINDOWS: list = []


def _interpret_window(language):
    """The Interpret window of the reference slope, built in ``language``
    (the grid of test_interpret_i1_v149, small)."""
    from PySide6.QtWidgets import QApplication
    from test_slide_validation_ej1 import _ej1_project

    from ogr_gui.i18n import set_language
    from ogr_gui.interpret_window import InterpretWindow
    from ogr_slip2d import BishopSimplified
    from ogr_slip2d.search import GridSearch
    QApplication.instance() or QApplication([])
    set_language(language)
    p = _ej1_project()
    res = {"bishop_simplified": GridSearch(
        method=BishopSimplified(), grid_x=(70, 100), grid_y=(60, 85),
        grid_nx=3, grid_ny=3, radius_increment=10, min_radius=15,
        num_slices=16, min_area=0.5).run(p)}
    w = InterpretWindow(p, res, None)
    _WINDOWS.append(w)
    return p, w


class TestTheInterpretWindowSpeaksSpanish:
    def test_its_title_menus_and_tool_bars(self):
        from PySide6.QtWidgets import QToolBar
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        try:
            p, w = _interpret_window("es")
            assert w.windowTitle() == "OGR Slip2D — Interpretar — %s" % p.name
            menus = [a.text() for a in w.menuBar().actions()]
            for title in ("Agua subterránea", "Estadística"):
                assert title in menus, menus
            bars = [tb.windowTitle() for tb in w.findChildren(QToolBar)]
            assert "Método" in bars, bars
            w.close()
        finally:
            set_language(before)

    def test_in_english_nothing_changed(self):
        """Control: the English that tests and users read is the same."""
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        try:
            p, w = _interpret_window("en")
            assert w.windowTitle() == "OGR Slip2D — Interpret — %s" % p.name
            menus = [a.text() for a in w.menuBar().actions()]
            assert "Groundwater" in menus and "Statistics" in menus, menus
            w.close()
        finally:
            set_language(before)


class TestTheMainWindowSpeaksSpanish:
    """v0.1.319 — the results panel, built with the window."""

    def _headers(self, language):
        from PySide6.QtWidgets import QApplication
        from ogr_gui.i18n import set_language
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        set_language(language)
        w = MainWindow()
        try:
            table = w.results_dock.table
            return [table.horizontalHeaderItem(i).text()
                    for i in range(table.columnCount())]
        finally:
            w.project.is_dirty = False
            w.close()

    def test_the_results_panel_headers(self):
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        try:
            assert self._headers("es") == [
                "#", "FS", "Método", "Centro X", "Centro Y", "Radio"]
            # control: the English is what it was
            assert self._headers("en") == [
                "#", "FoS", "Method", "Centre X", "Centre Y", "Radius"]
        finally:
            set_language(before)


def _shown(dialog):
    """Every text a dialog shows or offers on hover: titles, labels, button
    texts, group titles, tooltips, combo items and table headers. The
    standard buttons of a button box are left out: Qt's own catalogue names
    them, not ours (test_qt_translations)."""
    from PySide6.QtWidgets import (QAbstractButton, QComboBox,
                                   QDialogButtonBox, QGroupBox, QLabel,
                                   QTableWidget, QWidget)
    out = [dialog.windowTitle()]
    for w in [dialog] + dialog.findChildren(QWidget):
        if w.toolTip():
            out.append(w.toolTip())
        if isinstance(w, QLabel):
            out.append(w.text())
        elif isinstance(w, QAbstractButton) and not isinstance(
                w.parent(), QDialogButtonBox):
            out.append(w.text())
        elif isinstance(w, QGroupBox):
            out.append(w.title())
        elif isinstance(w, QComboBox):
            out += [w.itemText(i) for i in range(w.count())]
        elif isinstance(w, QTableWidget):
            out += [w.horizontalHeaderItem(i).text()
                    for i in range(w.columnCount())
                    if w.horizontalHeaderItem(i) is not None]
    return [t for t in out if t]


class TestTheDialogsSpeakSpanish:
    """v0.1.320 — the dialogs of families (c) and (d), each opened with the
    interface in Spanish: none shows an English text that has its Spanish,
    and each shows in Spanish one of the texts this version wrapped."""

    def _dialogs(self, language):
        from PySide6.QtWidgets import QApplication
        from test_slide_validation_ej1 import _ej1_project
        from ogr_core.project.settings import GroundwaterSettings
        from ogr_gui.dialogs.grid_dialogs import (AddGridDialog,
                                                  SurfaceOptionsDialog)
        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog)
        from ogr_gui.dialogs.seismic_dialog import SeismicLoadDialog
        from ogr_gui.dialogs.tension_crack_dialog import (
            DefineTensionCrackDialog)
        from ogr_gui.dialogs.transient_stages_dialog import (
            TransientStagesDialog)
        from ogr_gui.i18n import set_language
        QApplication.instance() or QApplication([])
        set_language(language)
        p = _ej1_project()
        out = {
            "grid": AddGridDialog(p),
            "surface": SurfaceOptionsDialog(p),
            "crack": DefineTensionCrackDialog(p),
            "transient": TransientStagesDialog(GroundwaterSettings()),
            "seismic": SeismicLoadDialog(p.seismic),
            "settings": ProjectSettingsDialog(p.settings, None, project=p),
        }
        _WINDOWS.extend(out.values())
        return out

    #: One text each dialog wrapped in 0.1.320, as the start of what it shows.
    _WRAPPED = {
        "grid": ("<b>Define la rejilla de centros",
                 "<b>Define the slip-circle centre grid."),
        "surface": ("<b>Generación y optimización de superficies",
                    "<b>Failure surface generation & optimization."),
        "crack": ("<b>Propiedades hidráulicas de la grieta de tracción.",
                  "<b>Tension Crack hydraulic properties."),
        "transient": ("Calcular FS", "Calculate SF"),
        "seismic": ("Coeficiente sísmico horizontal.",
                    "Horizontal seismic coefficient."),
        "settings": ("Coeficiente Hu por defecto",
                     "Default Hu coefficient"),
    }

    def test_no_english_text_that_has_its_spanish(self):
        from ogr_gui.i18n import _DICTS, current_language, set_language
        es = _DICTS["es"]
        before = current_language()
        try:
            for name, dialog in self._dialogs("es").items():
                left = [t for t in _shown(dialog)
                        if t in es and es[t] != t]
                assert not left, (name, left)
        finally:
            set_language(before)

    def test_each_shows_what_it_wrapped_and_english_is_unchanged(self):
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        try:
            for language, which in (("es", 0), ("en", 1)):
                for name, dialog in self._dialogs(language).items():
                    want = self._WRAPPED[name][which]
                    assert any(t.startswith(want)
                               for t in _shown(dialog)), (language, name)
        finally:
            set_language(before)

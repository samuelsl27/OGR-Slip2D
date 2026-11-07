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

v0.1.432 (D399) — four places a text reached the screen from, unseen: the
canvas's ``status_message.emit``, either branch of a conditional
(``tr(a) if c else "b"``), an item's data in a role the user reads
(``setItemData(i, text, Qt.ToolTipRole)``), and, in a census of its own, a
field of a translated text filled with English (``.format(b.btype.
display_name)``, the ``value`` of an enum).

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
#: v0.1.432 (D399) -- the roles of an item's data that reach the screen
#: (``setItemData(i, text, Qt.ToolTipRole)``); any other role is data.
_TEXT_ROLES = {"DisplayRole", "ToolTipRole", "StatusTipRole",
               "WhatsThisRole"}
#: v0.1.433 (D411) -- item constructors whose first argument is the text of
#: the cell or the row (the tree item's is a list): « [BC]» reached a cell
#: of the transient stages this way.
_ITEMS = {"QTableWidgetItem", "QListWidgetItem", "QStandardItem"}
#: v0.1.433 (D411) -- matplotlib calls whose first argument is text on the
#: figure; ``text(x, y, s)`` has it third. The axes of the random variable's
#: plot and two charts' empty-state messages were English this way.
_MPL_FIRST = {"set_title", "set_xlabel", "set_ylabel", "set_zlabel",
              "suptitle", "annotate"}
#: ... and the plotting calls whose ``label=`` (a legend entry) or
#: ``title=`` is text.
_MPL_LABELLED = {"plot", "axvline", "axhline", "bar", "barh", "scatter",
                 "fill_between", "hist", "step", "errorbar", "axvspan",
                 "axhspan", "stairs", "semilogx", "semilogy", "loglog",
                 "stem", "legend"}
#: String methods that hand back the same text: the census reads through
#: them (``QTableWidgetItem((label + " [BC]").strip())``).
_SAME_TEXT = {"strip", "rstrip", "lstrip", "upper", "lower", "capitalize",
              "title"}
#: A colour's hex code is notation, not text.
_COLOUR = re.compile(r"#[0-9A-Fa-f]{3,8}")

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
    # the product's name and the PROJECT's name, as test_window_english_left.
    # v0.1.433 (D411): "— Untitled" and "— Demo slope" left, by the owner's
    # decision: a default project name is shown translated
    # (ogr_gui.labels.project_label), so the two titles are the third.
    ("main_window.py", "OGR Slip2D v{} — OpenGeoRock Suite"):
        "the product's name and version",
    ("main_window.py", "OGR Slip2D v{} — {}"):
        "the product's name and the project's name",
    # v0.1.433 (D411) -- notation on a figure, the same in Spanish
    ("interpret_window.py", "x (m)"):
        "notation: a coordinate and its unit, on a plot's axis",
    ("interpret_window.py", "y (m)"):
        "notation: a coordinate and its unit, on a plot's axis",
    ("statistics_window.py", "FS = 1"):
        "notation: the line of factor 1, FS in Spanish too",
    # v0.1.370 (D344): "{}_report.pdf" left, the name goes through tr()
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
    # v0.1.433 (D411): one field more, the flag of a stage with its own
    # conditions («[CC]»), which goes through tr() as «[FS]» does
    ("interpret_groundwater_window.py", "{}: t = {}{}{}{}"):
        "notation: the number and the time of a stage, and its flags",
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
        "the default name of a new support type, which the model keeps and "
        "the screen shows as it is; unlike a project's 'Untitled', which "
        "0.1.433 shows translated, it is not (yet) a name the program "
        "recognises as its own -- left for the owner (review of 0.1.433)",
    # v0.1.432 (D399): "Piezo {}" left, the lines are named as the material
    # dialog names them (ogr_gui.labels.water_surface_label)
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
#: v0.1.432 (D399): still 0, with two rules more -- the canvas's
#: ``status_message.emit`` and both branches of a conditional -- that found
#: three texts in English, put through tr() in the same version.
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
        # v0.1.432 (D399) -- a conditional puts one of its two branches on
        # screen: in ``tr(a) if c else "b"`` the census saw an IfExp, not a
        # text, and "b" reached the tool tip in English
        if isinstance(node, ast.IfExp):
            flag(node.body)
            flag(node.orelse)
            return
        # v0.1.433 (D411) -- an ``or`` puts one of its operands on screen:
        # ``"  |  ".join(parts) or "no conditions"``
        if isinstance(node, ast.BoolOp):
            for value in node.values:
                flag(value)
            return
        # v0.1.433 (D411) -- every literal of a concatenation reaches the
        # screen, not only the first: «Listo — File → Load Demo Slope…» was
        # ``tr("Ready") + " — File → …"``
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            flag(node.left)
            flag(node.right)
            return
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            # v0.1.433 (D411) -- a literal in a field of a translated text
            # is on screen too: ``tr("…: {0}").format(… or "nothing
            # selectable")``
            if node.func.attr == "format" and _is_tr(node.func.value):
                for value in list(node.args) + [k.value
                                                for k in node.keywords]:
                    flag(value)
                return
            if node.func.attr in _SAME_TEXT:
                flag(node.func.value)
                return
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod) \
                and _is_tr(node.left):
            right = node.right
            for value in (right.elts if isinstance(right, ast.Tuple)
                          else [right]):
                flag(value)
            return
        text = _text(node)
        if text is not None and _letters(text) and text.strip() not in _AXES \
                and not _COLOUR.fullmatch(text.strip()):
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
        elif name == "emit" and args and isinstance(node.func, ast.Attribute) \
                and getattr(node.func.value, "attr", None) == "status_message":
            # v0.1.432 (D399) -- the canvas speaks through this signal, which
            # the window shows on its status bar; two of its messages were
            # in English, unseen, because ``emit`` was not a call read here
            flag(args[0])
        elif name == "setItemData" and len(args) >= 3 \
                and getattr(args[2], "attr", None) in _TEXT_ROLES:
            # v0.1.432 (D399) -- an item's data in a role the user reads: two
            # tool tips of the tension crack's combo were in English
            flag(args[1])
        elif name in _INPUTS and isinstance(node.func, ast.Attribute) \
                and getattr(node.func.value, "id", None) == "QInputDialog":
            for a in args[1:3]:
                flag(a)
        elif name in _BOXES and isinstance(node.func, ast.Attribute) \
                and getattr(node.func.value, "id", None) == "QMessageBox" \
                and len(args) >= 3:
            flag(args[1])
            flag(args[2])
        # v0.1.433 (D411) -- the text of an item, and the text on a figure
        elif name in _ITEMS and args:
            flag(args[0])
        elif name == "QTreeWidgetItem" and args \
                and isinstance(args[0], (ast.List, ast.Tuple)):
            for el in args[0].elts:
                flag(el)
        elif name in _MPL_FIRST and args:
            flag(args[0])
        elif name == "text" and len(args) >= 3:
            flag(args[2])
        elif name == "legend" and args \
                and isinstance(args[0], (ast.List, ast.Tuple)):
            for el in args[0].elts:
                flag(el)
        if name in _MPL_LABELLED:
            for kw in node.keywords:
                if kw.arg in ("label", "title"):
                    flag(kw.value)

    # v0.1.433 (D411) -- a conditional half through tr(), anywhere: its
    # other branch goes where the translated one goes («ΔFoS» beside
    # ``tr("Δ over-design factor")``, carried by a variable)
    for node in ast.walk(tree):
        if isinstance(node, ast.IfExp):
            branches = (node.body, node.orelse)
        elif isinstance(node, ast.BoolOp):
            branches = tuple(node.values)
        else:
            continue
        if any(_is_tr(b) for b in branches):
            for b in branches:
                if not _is_tr(b):
                    flag(b)

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


#: v0.1.432 (D399) -- attributes that hold English whatever the language: a
#: type's ``display_name`` (a support type's ``DISPLAY_NAME``) and the
#: ``value`` of an enum, the identifier the ``.ogr`` keeps. Each has its
#: label in ``ogr_gui/labels.py``, or in the dialog that names it.
_ENGLISH_ATTRS = {"display_name", "DISPLAY_NAME", "value"}


def _is_tr(node):
    return isinstance(node, ast.Call) and _call_name(node) == "tr"


def english_fields(src):
    """``[(lineno, expression)]`` of the fields of a translated text that are
    filled with one of :data:`_ENGLISH_ATTRS`.

    v0.1.432 (D399): ``tr("Added {0} with {1} vertices").format(
    b.btype.display_name, n)`` passes every rule above — the text goes
    through tr() — and put «Añadido External Boundary con 6 vértices» on the
    status bar after every boundary drawn in Spanish. A boundary's stored
    name is English too while the user keeps the default, but it is data
    this census cannot tell from a material's name: test_spanish_texts_v1432
    reads those messages through the window."""
    out = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "format" and _is_tr(node.func.value):
            fields = list(node.args) + [k.value for k in node.keywords]
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod) \
                and _is_tr(node.left):
            right = node.right
            fields = (list(right.elts) if isinstance(right, ast.Tuple)
                      else list(right.values) if isinstance(right, ast.Dict)
                      else [right])
        else:
            continue
        for f in fields:
            if isinstance(f, ast.Attribute) and f.attr in _ENGLISH_ATTRS:
                out.append((f.lineno, ast.unparse(f)))
    return sorted(out)


def field_census():
    """``{file: [(lineno, expression)]}`` of :func:`english_fields` over
    every module of ``ogr_gui`` but the dictionary."""
    out = {}
    for path in sorted(_ROOT.rglob("*.py")):
        rel = path.relative_to(_ROOT).as_posix()
        if rel.startswith("i18n/"):
            continue
        hits = english_fields(path.read_text(encoding="utf-8"))
        if hits:
            out[rel] = hits
    return out


class TestNoFieldIsFilledWithEnglish:
    """v0.1.432 (D399): four of these on the screen at 0.1.431 -- the type
    of a boundary added and converted, the mode of the tension crack, the
    kind of a focus object -- and none left."""

    def test_none_is_left(self):
        found = field_census()
        assert not found, found


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
            # v0.1.419 (D361) -- and a last column, the reason a surface
            # the checks rejected cannot be the critical one
            assert self._headers("es") == [
                "#", "FS", "Método", "Centro X", "Centro Y", "Radio", "Nota"]
            # control: the English is what it was, with the same column
            assert self._headers("en") == [
                "#", "FoS", "Method", "Centre X", "Centre Y", "Radius",
                "Note"]
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

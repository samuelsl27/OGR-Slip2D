# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.432 (D399) — the last texts of the interface in English that this
version names, and the retired forms with a capital letter.

The invariant: with the interface in Spanish, the texts listed below reach
the screen in Spanish, by the rules ``ogr_gui.labels`` holds; and the
censuses see the four paths those texts came by. It does NOT say that no
English is left on screen: the review of this version found about twenty
older places, by other paths that no census reads yet (the startup message,
the selection filter, the cleanup report, the DXF import, the property
tables, plots, the engine's own messages…). The owner opened D411 for them,
in v0.1.433.

What was found. The census of ``test_gui_spanish_v1318`` (BUDGET = 0) saw
none of these:

* the canvas speaks through its ``status_message`` signal, which the window
  shows on its status bar; ``emit`` was not a call the census read, and two
  of its messages skipped ``tr()``: "Need at least 3 distinct points to
  close a boundary." (Enter on an External boundary of two vertices) and
  "Drawing cancelled." (Esc in the middle of a drawing);
* the tool tip of Add Grid was the second branch of a conditional,
  ``tr(a) if c else "b"``: the census looked for a text where there was an
  ``IfExp``;
* two tool tips of the tension crack's combo went in ``setItemData`` with
  ``Qt.ToolTipRole``, a call the census did not read;
* a field of a translated text filled with English. Found while writing
  this test, and in this version by the owner's decision: every boundary
  drawn in Spanish said «Añadido External Boundary con 6 vértices». A
  boundary is born with its type's ENGLISH name as its name, and Deleted,
  Copied, Moved, the title of Edit Coordinates, the list of Select Boundary,
  the canvas's tool tip and context menu printed that stored name; Added and
  Converted printed the type's ``display_name``; the tension crack's message
  its mode's identifier («Grieta de tracción: percent_filled»); Manage Focus
  Objects the kind's («1: point (…)»); the crack's combo of piezometric
  lines their stored names. One rule now (``ogr_gui.labels.boundary_label``,
  the one ``MainWindow._boundary_label`` held for Scale and Rotate, and
  ``water_surface_label``, the material dialog's) and two labels.

By the owner's decisions in this version, too:

* «contorno» carries the gender of the five feminine types («Contorno
  añadido: Línea de desembalse, con 2 vértices»; «Añadido Línea de
  desembalse» did not agree), and «[objeto desactivado]» that of the
  feminine kinds of focus object;
* any type's English name is a default name, not only the boundary's own:
  Convert Boundary from the canvas's context menu kept the old type's name
  until v0.1.455 (D410), and a water table converted from a material
  boundary said «Contorno eliminado: Material Boundary» (the review found
  it; a name left so by an older version is the case of
  ``test_copy_convert_boundary_rule_v1455``);
* the singular, for the boundary of one vertex (a Block Search point) and
  the Focus Point («con 1 vértice», «1 punto»).

And the retired form «superficie de deslizamiento» (D318) was searched for
in lower case only: three values that start with it in capitals were left.

What is checked here:

1. through the real window, built in Spanish: the two messages of the
   canvas (the vertices typed in the status bar's own field, Enter and Esc
   on the canvas); the messages of a boundary added, copied, moved, dragged,
   converted (from the menu and from the context menu) and deleted,
   default-named and named, and of one of a single vertex; the list of
   Select Boundary; the heading of a boundary's context menu, read in the
   menu; Manage Focus Objects; the tension crack's message and its combo;
   the tool tips of Add Grid, of the circles' actions, of a surface and of a
   boundary on the canvas; the title of Edit Coordinates. In English, what
   the tests and the users read (control);
2. the censuses check themselves on sources of their own: an English text
   in ``status_message.emit``, in either branch of a conditional or in a
   text role of ``setItemData`` is counted, and the same through ``tr()``
   is not; another signal and another role are data; a field filled with
   ``display_name`` or an enum's ``value`` is counted, and one filled by a
   label is not; ``_wrapped_keys`` reads both branches of
   ``tr(a if c else b)``; a retired form is caught with a capital letter,
   and the Spanish «fea» is not taken for FEA.

One main window for the file (each lives to the end of the process), kept
apart from the dialogs the tests keep alive, so that no filter (``-k``) can
hand a test a dialog for the window. Every test puts back the boundaries,
focus objects, tension crack and settings it changed, and the language.
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

#: The main window, built once for the file.
_WINDOW: list = []
#: The dialogs the tests build, kept alive to the end of the process: apart
#: from the window, or a test run alone could take a dialog for it.
_KEPT: list = []


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _window():
    """The main window, built in Spanish once for the file: the user's
    case, whose menus take their texts at the start (D290)."""
    if not _WINDOW:
        from ogr_gui.i18n import current_language, set_language
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        before = current_language()
        try:
            set_language("es")
            w = MainWindow()
        finally:
            set_language(before)
        _WINDOW.append(w)
    return _WINDOW[0]


@contextmanager
def _language(code):
    from ogr_gui.i18n import current_language, set_language
    before = current_language()
    set_language(code)
    try:
        yield
    finally:
        set_language(before)


@contextmanager
def _swapped(owner, name, value):
    """``owner.name`` replaced for the block and put back exactly (the leak
    detector watches the dialogs' static members)."""
    raw = owner.__dict__.get(name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        if raw is None:
            delattr(owner, name)
        else:
            setattr(owner, name, raw)


def _line(btype, name=None, y=5.0):
    from ogr_core.geometry import Boundary, Polyline, Vertex
    b = Boundary(btype=btype, polyline=Polyline(
        vertices=[Vertex(0.0, y), Vertex(60.0, y)], closed=False))
    if name is not None:
        b.name = name
    return b


class _ToWaterTable:
    """Convert Boundary's dialog, answered: to a water table."""

    def __init__(self, _btype, _parent=None):
        pass

    def exec(self):
        return 1

    def new_type(self):
        from ogr_core.geometry import BoundaryType
        return BoundaryType.WATER_TABLE


@contextmanager
def _added(w, *boundaries):
    """``boundaries`` in the window's model for the block, through the
    command stack, and every boundary the block adds taken away after."""
    from ogr_core.project.commands import (AddBoundaryCommand,
                                           RemoveBoundaryCommand)
    before = list(w.project.boundaries)
    for b in boundaries:
        w.command_stack.do(w.project, AddBoundaryCommand(boundary=b))
    try:
        yield
    finally:
        for b in [b for b in w.project.boundaries if b not in before]:
            w.command_stack.do(w.project, RemoveBoundaryCommand(boundary=b))
        w.project.is_dirty = False


def _type_point(w, x, y):
    """A vertex typed in the status bar's own field and Enter, as the user
    adds an exact one (``_CoordInput``)."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    field = w.ogr_status.coord_input
    field.clear()
    QTest.keyClicks(field, "%g, %g" % (x, y))
    QTest.keyClick(field, Qt.Key_Return, Qt.NoModifier)


def _draw(w, mode, points, key):
    """``points`` typed in ``mode``, then ``key`` on the canvas; the status
    bar's message after it, and the points the drawing kept."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from ogr_gui.canvas.tool_mode import ToolMode
    canvas = w.canvas
    canvas.set_tool_mode(mode)
    try:
        for x, y in points:
            _type_point(w, x, y)
        assert len(canvas._draw_points) == len(points), canvas._draw_points
        QTest.keyClick(canvas, key, Qt.NoModifier)
        return w.ogr_status.currentMessage(), list(canvas._draw_points)
    finally:
        canvas._cancel_drawing()
        canvas.set_tool_mode(ToolMode.SELECT)


@_requires_qt
class TestTheCanvasSpeaksSpanish:
    def _messages(self, language):
        from PySide6.QtCore import Qt
        from ogr_gui.canvas.tool_mode import ToolMode
        w = _window()
        two = [(10.0, 10.0), (20.0, 10.0)]
        with _language(language):
            too_few, left = _draw(w, ToolMode.DRAW_EXTERNAL, two,
                                  Qt.Key_Return)
            cancelled, gone = _draw(w, ToolMode.DRAW_EXTERNAL, two,
                                    Qt.Key_Escape)
        # the drawing stays after the first, so the user can go on; Esc
        # takes it away
        assert len(left) == 2 and gone == [], (left, gone)
        return too_few, cancelled

    def test_on_the_status_bar_in_spanish(self):
        too_few, cancelled = self._messages("es")
        assert too_few == ("Hacen falta al menos 3 puntos distintos para "
                           "cerrar un contorno."), too_few
        assert cancelled == "Dibujo cancelado.", cancelled

    def test_control_in_english_the_same_texts_as_before(self):
        too_few, cancelled = self._messages("en")
        assert too_few == ("Need at least 3 distinct points to close a "
                           "boundary."), too_few
        assert cancelled == "Drawing cancelled.", cancelled


@_requires_qt
class TestABoundaryByItsLabel:
    """The messages of a boundary's life, each through the window."""

    def _life(self, language, name=None):
        from PySide6.QtCore import Qt
        from ogr_core.geometry import BoundaryType
        from ogr_gui.canvas.tool_mode import ToolMode
        w = _window()
        bar = w.ogr_status
        out = {}
        with _language(language), _added(w):
            out["added"], _ = _draw(w, ToolMode.DRAW_MATERIAL,
                                    [(0.0, 5.0), (60.0, 5.0)], Qt.Key_Return)
            i = len(w.project.boundaries) - 1
            b = w.project.boundaries[i]
            assert b.btype == BoundaryType.MATERIAL, b
            if name is not None:
                b.name = name
            w._do_copy_boundary(i)
            out["copied"] = bar.currentMessage()
            w._do_move_boundary(i, 1.0, 2.0)
            out["moved"] = bar.currentMessage()
            w._on_boundary_dragged(i, 1.0, -2.0)
            out["dragged"] = bar.currentMessage()
            w._on_boundary_action_requested("delete", i + 1)
            out["deleted, menu"] = bar.currentMessage()
            w._do_delete_boundary(i)
            out["deleted"] = bar.currentMessage()
        return out

    def test_default_named_in_spanish(self):
        assert self._life("es") == {
            "added": "Contorno añadido: Contorno de material, con 2 "
                     "vértices",
            "copied": "Contorno copiado: Contorno de material",
            "moved": "Contorno movido: Contorno de material (1.00, 2.00)",
            "dragged": "Contorno movido: Contorno de material (+1.00, "
                       "-2.00)",
            "deleted, menu": "Contorno eliminado: Contorno de material",
            "deleted": "Contorno eliminado: Contorno de material",
        }

    def test_a_given_name_is_data(self):
        out = self._life("es", name="Arcilla")
        assert out["copied"] == "Contorno copiado: Arcilla", out
        assert out["deleted"] == "Contorno eliminado: Arcilla", out

    def test_control_in_english(self):
        assert self._life("en") == {
            "added": "Added Material Boundary with 2 vertices",
            "copied": "Copied Material Boundary",
            "moved": "Moved Material Boundary by (1.00, 2.00)",
            "dragged": "Moved Material Boundary by (+1.00, -2.00)",
            "deleted, menu": "Deleted Material Boundary",
            "deleted": "Deleted Material Boundary",
        }

    def test_converted_to_a_type_through_tr(self):
        import ogr_gui.main_window as mw
        from ogr_core.geometry import BoundaryType
        w = _window()
        seen = {}
        with _swapped(mw, "ConvertBoundaryDialog", _ToWaterTable):
            for language in ("es", "en"):
                with _language(language), \
                        _added(w, _line(BoundaryType.MATERIAL)):
                    w._do_convert_boundary(len(w.project.boundaries) - 1)
                    seen[language] = w.ogr_status.currentMessage()
        assert seen == {"es": "Convertido en Nivel freático",
                        "en": "Converted to Water Table"}, seen

    def test_converted_from_the_context_menu_keeps_no_english(self):
        """The context menu's Convert kept the old type's English name until
        v0.1.455 (D410, the path itself: it is the menu's now, so the name
        is the new type's); the rule counts any type's English name as a
        default, so the water table is shown as one, not as «Material
        Boundary» (the review of v0.1.432)."""
        import ogr_gui.dialogs as dialogs
        from ogr_core.geometry import BoundaryType
        w = _window()
        seen = {}
        with _swapped(dialogs, "ConvertBoundaryDialog", _ToWaterTable):
            for language in ("es", "en"):
                with _language(language), \
                        _added(w, _line(BoundaryType.MATERIAL)):
                    i = len(w.project.boundaries) - 1
                    w._on_boundary_action_requested("convert", i)
                    b = w.project.boundaries[i]
                    assert b.btype == BoundaryType.WATER_TABLE, b
                    # the new type's since v0.1.455 (D410: the menu's step)
                    assert b.name == "Water Table", b.name
                    w._do_delete_boundary(i)
                    seen[language] = w.ogr_status.currentMessage()
        assert seen == {"es": "Contorno eliminado: Nivel freático",
                        "en": "Deleted Water Table"}, seen

    def test_the_context_menu_heading(self):
        """Read in the menu itself, as the user reads it: the heading is the
        type, and the name after a dash only when the user gave one."""
        from PySide6.QtCore import QPoint
        from ogr_core.geometry import BoundaryType
        from test_labels_spanish_v1321 import _menu_texts
        w = _window()
        seen = {}
        mine = [_line(BoundaryType.MATERIAL),
                _line(BoundaryType.MATERIAL, name="Arcilla", y=8.0)]
        for language in ("es", "en"):
            with _language(language), _added(w, *mine):
                first = len(w.project.boundaries) - 2
                seen[language] = [
                    _menu_texts(lambda i=i: w.canvas._show_boundary_context_menu(
                        QPoint(0, 0), i))[0]
                    for i in (first, first + 1)]
        assert seen == {
            "es": ["Contorno de material", "Contorno de material — Arcilla"],
            "en": ["Material Boundary", "Material Boundary — Arcilla"],
        }, seen

    def test_a_boundary_of_one_vertex(self):
        """A Block Search point, the one boundary of a single vertex: the
        singular, when it is added and in the list of Select Boundary."""
        from PySide6.QtWidgets import QInputDialog
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        w = _window()
        search = w.project.settings.search
        kept = (search.surface_type, search.search_method)
        seen, items = {}, []

        def fake(_parent, _title, _label, entries, *_a, **_k):
            items.append(list(entries))
            return "", False

        def point(name=None):
            b = Boundary(btype=BoundaryType.BLOCK_SEARCH_OBJECT,
                         polyline=Polyline(vertices=[Vertex(20.0, 10.0)],
                                           closed=False))
            if name is not None:
                b.name = name
            return b

        # the rule admits a Block Search object only with that search
        search.surface_type, search.search_method = "non_circular", "block"
        try:
            for language in ("es", "en"):
                with _language(language), _added(w, point("P1")), \
                        _swapped(QInputDialog, "getItem", staticmethod(fake)):
                    w._on_boundary_drawn(point())
                    seen[language] = w.ogr_status.currentMessage()
                    w._ask_boundary_index()
        finally:
            search.surface_type, search.search_method = kept
            w.refresh_action_availability()
        assert seen == {
            "es": "Contorno añadido: Objeto de búsqueda por bloques, con 1 "
                  "vértice",
            "en": "Added Block Search Object with 1 vertex"}, seen
        es, en = items
        assert es[-2:] == [
            "[%d] Objeto de búsqueda por bloques «P1» (1 vértice)"
            % (len(es) - 2),
            "[%d] Objeto de búsqueda por bloques (1 vértice)"
            % (len(es) - 1)], es
        assert en[-2:] == [
            "[%d] Block Search Object 'P1' (1 vert)" % (len(en) - 2),
            "[%d] Block Search Object (1 vert)" % (len(en) - 1)], en

    def test_the_list_of_select_boundary(self):
        from PySide6.QtWidgets import QInputDialog
        from ogr_core.geometry import BoundaryType
        w = _window()
        seen = []

        def fake(_parent, _title, _label, items, *_a, **_k):
            seen.extend(items)
            return "", False

        mine = [_line(BoundaryType.MATERIAL),
                _line(BoundaryType.MATERIAL, name="Arcilla", y=8.0)]
        with _language("es"), _added(w, *mine), \
                _swapped(QInputDialog, "getItem", staticmethod(fake)):
            assert w._ask_boundary_index() is None
            first = len(w.project.boundaries) - 2
        assert seen[first:] == [
            "[%d] Contorno de material (2 vértices)" % first,
            "[%d] Contorno de material «Arcilla» (2 vértices)" % (first + 1),
        ], seen

    def test_the_canvas_and_the_dialog_name_it_so(self):
        from ogr_core.geometry import BoundaryType
        from ogr_gui.canvas.graphics_items import BoundaryItem
        from ogr_gui.dialogs.boundary_dialogs import EditCoordinatesDialog
        from ogr_gui.labels import boundary_heading
        QApplication.instance() or QApplication([])
        plain = _line(BoundaryType.MATERIAL)
        named = _line(BoundaryType.MATERIAL, name="Arcilla")
        with _language("es"):
            assert BoundaryItem(plain).toolTip() == \
                "<b>Contorno de material</b>"
            assert BoundaryItem(named).toolTip() == \
                "<b>Arcilla</b><br>Contorno de material"
            assert boundary_heading(plain) == "Contorno de material"
            assert boundary_heading(named) == "Contorno de material — Arcilla"
            d = EditCoordinatesDialog(plain)
            _KEPT.append(d)
            assert d.windowTitle() == \
                "Editar coordenadas — Contorno de material"
        with _language("en"):
            assert BoundaryItem(plain).toolTip() == \
                "<b>Material Boundary</b>"
            assert boundary_heading(named) == "Material Boundary — Arcilla"


@_requires_qt
class TestTheIdentifiersByTheirLabels:
    def test_manage_focus_objects(self):
        from PySide6.QtWidgets import QInputDialog
        from ogr_core.geometry.focus import FocusKind, FocusObject
        w = _window()
        seen = []

        def fake(_parent, _title, _label, items, *_a, **_k):
            seen.append(list(items))
            return "", False

        objs = w.project.focus_objects
        before = list(objs)
        window = FocusObject(kind=FocusKind.WINDOW, tolerance=0.5,
                             points=[(0.0, 0.0), (9.0, 0.0), (9.0, 9.0),
                                     (0.0, 9.0)])
        window.enabled = False
        objs[:] = [window, FocusObject(kind=FocusKind.POINT,
                                       points=[(10.0, 10.0)], tolerance=0.5)]
        try:
            with _swapped(QInputDialog, "getItem", staticmethod(fake)):
                for language in ("es", "en"):
                    with _language(language):
                        w._manage_focus()
        finally:
            objs[:] = before
        # «objeto» carries the gender of the feminine kinds, and the Focus
        # Point has one point (by the owner's decisions in this version)
        assert [items[:2] for items in seen] == [
            ["1: Ventana de foco (4 puntos, tolerancia 0.5)  "
             "[objeto desactivado]",
             "2: Punto de foco (1 punto, tolerancia 0.5)"],
            ["1: Focus Window (4 points, tolerance 0.5)  [disabled]",
             "2: Focus Point (1 point, tolerance 0.5)"]], seen

    def test_the_tension_crack_message(self):
        from ogr_core.geometry import BoundaryType
        from ogr_core.geometry.tension_crack import (TensionCrackProperties,
                                                     WaterLevelMode)
        from ogr_gui.dialogs.tension_crack_dialog import (
            DefineTensionCrackDialog)
        w = _window()
        kept = w.project.tension_crack_properties
        seen = {}
        try:
            with _swapped(DefineTensionCrackDialog, "exec", lambda _s: 1), \
                    _added(w, _line(BoundaryType.TENSION_CRACK, y=12.0)):
                for language in ("es", "en"):
                    # the dialog opens on the model's mode and gives it back
                    w.project.tension_crack_properties = \
                        TensionCrackProperties(
                            mode=WaterLevelMode.PERCENT_FILLED)
                    with _language(language):
                        w.act_define_tension_crack()
                        seen[language] = w.ogr_status.currentMessage()
        finally:
            w.project.tension_crack_properties = kept
            w.project.is_dirty = False
        assert seen == {"es": "Grieta de tracción: Porcentaje de llenado",
                        "en": "Tension Crack: Percent Filled"}, seen

    def test_the_tension_cracks_disabled_entries(self):
        from PySide6.QtCore import Qt
        from ogr_core.geometry.tension_crack import WaterLevelMode
        from ogr_core.project import Project
        from ogr_gui.dialogs.tension_crack_dialog import (
            DefineTensionCrackDialog)
        QApplication.instance() or QApplication([])
        with _language("es"):
            d = DefineTensionCrackDialog(Project())
        _KEPT.append(d)
        tips = {d.cb_mode.itemData(i): d.cb_mode.itemData(i, Qt.ToolTipRole)
                for i in range(d.cb_mode.count())}
        assert tips[WaterLevelMode.USE_WATER_TABLE] == (
            "Este modelo no tiene nivel freático. Añade uno primero."), tips
        assert tips[WaterLevelMode.USE_PIEZOMETRIC] == (
            "No hay líneas piezométricas. Añade una primero."), tips

    def test_the_piezometric_lines_named_as_the_material_dialog(self):
        """The crack's combo showed each line's stored name, «Piezometric
        Line» in every language; the material dialog numbers them («Línea
        piezométrica 2»). One rule now, so a line has one name."""
        from types import SimpleNamespace
        from ogr_core.geometry import BoundaryType
        from ogr_core.project import Project
        from ogr_gui.dialogs.tension_crack_dialog import (
            DefineTensionCrackDialog)
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        p = Project()
        p.boundaries += [_line(BoundaryType.PIEZOMETRIC, y=9.0),
                         _line(BoundaryType.PIEZOMETRIC, name="Pozo A",
                               y=11.0)]
        for language, want in (("es", ["Línea piezométrica 1",
                                       "Línea piezométrica 2"]),
                               ("en", ["Piezometric Line 1",
                                       "Piezometric Line 2"])):
            with _language(language):
                d = DefineTensionCrackDialog(p)
                material = [label for _id, label in
                            MainWindow._water_surface_choices(
                                SimpleNamespace(project=p))]
            _KEPT.append(d)
            crack = [d.cb_piezo.itemText(i) for i in range(d.cb_piezo.count())]
            assert crack == want == material, (language, crack, material)


@_requires_qt
class TestTheToolTipsSpeakSpanish:
    def _tips(self, language):
        from ogr_core.project.settings import SurfaceType
        w = _window()
        search = w.project.settings.search
        # the branches read here: a grid search, circular surfaces
        assert search.uses_grid(), search
        assert search.surface_type == SurfaceType.CIRCULAR.value, search
        try:
            with _language(language):
                w.refresh_action_availability()
                acts = w._actions
                return (acts["auto_grid"].toolTip(),
                        acts["add_grid"].toolTip(),
                        {acts[k].toolTip() for k in ("surf_centre_radius",
                                                     "surf_three_points",
                                                     "surf_manage")})
        finally:
            w.refresh_action_availability()

    def test_the_grid_and_the_circles_in_spanish(self):
        auto, add, circles = self._tips("es")
        assert auto == ("Generar automáticamente la rejilla de búsqueda de "
                        "círculos"), auto
        assert add == "Definir a mano la rejilla de búsqueda de círculos", add
        assert circles == {"Superficies de rotura definidas a mano, "
                           "analizadas además de la búsqueda"}, circles

    def test_control_in_english(self):
        auto, add, circles = self._tips("en")
        assert auto == "Auto-generate the slip-circle search grid", auto
        assert add == "Define a slip-circle search grid manually", add
        assert circles == {"Slip surfaces defined by hand, analysed in "
                           "addition to the search"}, circles

    def test_a_surface_on_the_canvas(self):
        from ogr_gui.canvas.graphics_items import SlipSurfaceItem
        QApplication.instance() or QApplication([])
        circle = {"type": "circle", "centre_x": 0.0, "centre_y": 10.0,
                  "radius": 5.0}
        with _language("es"):
            assert SlipSurfaceItem(circle, 1.234).toolTip() == \
                "Superficie de rotura — FS = 1.234"
            assert SlipSurfaceItem(circle, None).toolTip() == \
                "Superficie de rotura — sin factor de seguridad"
        with _language("en"):
            assert SlipSurfaceItem(circle, 1.234).toolTip() == \
                "Slip surface — FoS = 1.234"


class TestTheCensusesCheckThemselves:
    """On sources of their own: what each census must count, and a control
    of what it must not."""

    def test_the_status_bar_signal_is_text(self):
        import test_gui_spanish_v1318 as census
        assert census.loose(
            'self.status_message.emit("Drawing cancelled.")\n') == [
                (1, "Drawing cancelled.")]
        assert census.loose(
            'self.status_message.emit(tr("Drawing cancelled."))\n') == []
        # control: another signal carries an action's name, not text
        assert census.loose(
            'self.boundary_action_requested.emit("delete", 3)\n') == []

    def test_both_branches_of_a_conditional(self):
        import test_gui_spanish_v1318 as census
        assert census.loose(
            'a.setToolTip(tr("Auto") if k else "Define a grid by hand")\n'
        ) == [(1, "Define a grid by hand")]
        assert census.loose(
            'a.setToolTip("Define a grid" if k else tr("Auto"))\n') == [
                (1, "Define a grid")]
        # nested, and in a status-bar message
        assert census.loose(
            'self.status_message.emit("One" if k else ("Two" if j '
            'else tr("Three")))\n') == [(1, "One"), (1, "Two")]
        assert census.loose(
            'a.setToolTip(tr("Auto") if k else tr("By hand"))\n') == []

    def test_an_items_text_roles(self):
        import test_gui_spanish_v1318 as census
        assert census.loose(
            'c.setItemData(i, "Add one first.", Qt.ToolTipRole)\n') == [
                (1, "Add one first.")]
        assert census.loose(
            'c.setItemData(i, "Add one first.", '
            'Qt.ItemDataRole.StatusTipRole)\n') == [(1, "Add one first.")]
        assert census.loose(
            'c.setItemData(i, tr("Add one first."), Qt.ToolTipRole)\n') == []
        # control: the data behind an item is not text
        assert census.loose(
            'c.setItemData(i, "water_table", Qt.UserRole)\n') == []

    def test_a_field_filled_with_english(self):
        import test_gui_spanish_v1318 as census
        assert census.english_fields(
            'm(tr("Added {0} with {1} vertices").format('
            'b.btype.display_name, n))\n') == [(1, "b.btype.display_name")]
        assert census.english_fields(
            'm(tr("Tension Crack: %s") % props.mode.value)\n') == [
                (1, "props.mode.value")]
        assert census.english_fields(
            'm(tr("%d: %s") % (i, o.kind.value))\n') == [(1, "o.kind.value")]
        assert census.english_fields(
            'm(tr("Added {0}").format(boundary_label(b)))\n'
            'm(tr("Added {0}").format(b.name))\n') == []

    def test_the_keys_in_both_branches_of_tr(self):
        import test_i18n_coverage_v141 as coverage
        assert coverage._wrapped_keys(
            [("x.py", 'tr("Alpha" if c else "Beta")\n'
                      'tr("Gamma" if c else ("Delta" if d else "Eps"))\n')]
        ) == {"Alpha", "Beta", "Gamma", "Delta", "Eps"}

    def test_a_retired_form_with_a_capital(self):
        import test_voice_and_terms_v1325 as terms
        slip = r"\bsuperficies? de deslizamiento\b"
        assert slip in terms.RETIRED
        assert terms.holds_retired(slip, "Superficie de deslizamiento — FS")
        assert terms.holds_retired(slip, "superficies de deslizamiento")
        assert terms.holds_retired(r"\bcorridas?\b", "Corrida terminada")
        # FEA keeps its case: the Spanish «fea» is not the acronym
        fea = [p for p, kept in terms.RETIRED.items()
               if kept == "elementos finitos"]
        assert len(fea) == 1, fea
        assert terms.holds_retired(fea[0], "el análisis FEA")
        assert not terms.holds_retired(fea[0], "una malla fea")
        assert not terms.holds_retired(fea[0], "Fea")

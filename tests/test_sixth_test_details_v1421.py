# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.421 (D363) — details of the sixth GUI test (H4, H5, H7, H8, B2b of
``INFORME_prueba_GUI_0.1.357.md``, measured by ``repro_d363.py``), each on
its own.

The invariants:

1. **A refusal names the material.** ``material_set`` and ``model_define``
   refused a Hoek-Brown with a = 1.2 as «hoek_brown: Material '?', …»: the
   API asked the rule with no name. Now the material's own, or the one it is
   being renamed to in the same call. The English of the API is otherwise
   unchanged.
2. **Interpret opens on the main window's screen, within it.** It only did
   ``resize(1200, 800)``; on two screens at 100 % and 125 % it opened on the
   other one with its title bar above the top edge. Measured here on the
   offscreen screen, smaller than 1200 x 800: the window and its frame fit
   the available area.
3. **Interpret cuts no text** at 1536 x 823 and 1280 x 720, in Spanish and
   in English: every dock title and every table heading has the room it
   needs («Leye…», «létod», «entro» in the test).
4. **A window is named by its own title**, without the menu entry's «...»
   (Display Options, Define Materials, Preferences, Project Settings), and
   Qt no longer appends «- OGR Slip2D» to every title: the program sets no
   display name («OGR Slip2D v… — talud.ogr - OGR Slip2D»).
5. **The guide says** that a Compute of the window has no ``result_id``
   (the owner's decision, 2026-11-03: documented, not bridged).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent

_HB_BAD = {"model": "hoek_brown", "params": {"sigci": 30000, "mb": 0.067,
                                              "s": 2.5e-5, "a": 1.2}}
_SLOPE = [[0, 0], [40, 0], [40, 18], [25, 18], [15, 8], [0, 8]]


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


# ======================================================================
class TestARefusalNamesTheMaterial:

    def _refused(self, op, **kw):
        from ogr_api import InvalidArgument
        try:
            op(**kw)
        except InvalidArgument as exc:
            return str(exc)
        raise AssertionError("accepted")

    def test_material_set_and_model_define(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = call(ws, "project_new", name="d363")["project_id"]
            call(ws, "model_define", project_id=pid, spec={
                "external": _SLOPE,
                "materials": [{"name": "roca", "unit_weight": 25,
                               "strength": {"model": "hoek_brown", "params": {
                                   "sigci": 30000, "mb": 0.067, "s": 2.5e-5,
                                   "a": 0.619}}}]})
            said = {
                "update": self._refused(
                    lambda **k: call(ws, "material_set", **k),
                    project_id=pid, material="roca", strength=_HB_BAD),
                "renamed": self._refused(
                    lambda **k: call(ws, "material_set", **k),
                    project_id=pid, material="roca", name="granito",
                    strength=_HB_BAD),
                "new": self._refused(
                    lambda **k: call(ws, "material_set", **k),
                    project_id=pid, name="roca2", strength=_HB_BAD),
            }
            pid2 = call(ws, "project_new", name="d363b")["project_id"]
            said["model_define"] = self._refused(
                lambda **k: call(ws, "model_define", **k), project_id=pid2,
                spec={"external": _SLOPE,
                      "materials": [{"name": "roca", "unit_weight": 25,
                                     "strength": _HB_BAD}]})
        finally:
            ws.shutdown()
        expected = {"update": "roca", "renamed": "granito", "new": "roca2",
                    "model_define": "roca"}
        for case, name in expected.items():
            assert f"Material '{name}'" in said[case], (case, said[case])
            assert "'?'" not in said[case], said[case]
            assert "0 < a <= 1" in said[case], said[case]


class TestInterpretOpensWithinItsScreen:

    def test_its_frame_fits_the_available_area(self):
        """Opened by the window's own action, on the offscreen screen,
        which is smaller than 1200 x 800."""
        from ogr_gui.main_window import MainWindow
        app = _app()
        p, results = _interpret_run()
        w = MainWindow()
        try:
            w.resize(700, 500)
            w.show()
            app.processEvents()
            avail = w.screen().availableGeometry()
            assert avail.width() < 1200 or avail.height() < 800, avail
            w.last_search_results = results
            w.last_factor_report = None
            w.act_interpret()
            win = w.interpret_windows[-1]
            app.processEvents()
            assert win.screen() is w.screen()
            frame = win.frameGeometry()
            assert avail.contains(frame), (avail, frame)
            win.close()
        finally:
            w.project.is_dirty = False
            w.close()


class TestAWindowIsNamedByItsTitle:

    def test_the_four_dialogs(self):
        from ogr_core.project.demo import build_demo_project
        from ogr_gui.dialogs.display_options_dialog import \
            DisplayOptionsDialog
        from ogr_gui.dialogs.material_properties_dialog import \
            MaterialPropertiesDialog
        from ogr_gui.dialogs.preferences_dialog import PreferencesDialog
        from ogr_gui.dialogs.project_settings_dialog import \
            ProjectSettingsDialog
        from ogr_gui.canvas import DisplayOptions
        from ogr_gui.i18n import current_language, set_language
        _app()
        p = build_demo_project()
        before = current_language()
        titles = {}
        try:
            for lang in ("en", "es"):
                set_language(lang)
                for d in (DisplayOptionsDialog(DisplayOptions(), None),
                          MaterialPropertiesDialog(list(p.materials)),
                          PreferencesDialog(None),
                          ProjectSettingsDialog(p.settings, None,
                                                project=p)):
                    titles[(lang, type(d).__name__)] = d.windowTitle()
                    d.deleteLater()
        finally:
            set_language(before)
        assert not [t for t in titles.values() if t.endswith(("...", "…"))], \
            titles
        assert titles[("es", "PreferencesDialog")] == "Preferencias"
        assert titles[("es", "ProjectSettingsDialog")] == \
            "Ajustes de proyecto"

    def test_no_display_name_is_set(self):
        tree = ast.parse((_ROOT / "ogr_gui" / "__main__.py").read_text(
            encoding="utf-8"))
        calls = [n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute)]
        assert "setApplicationDisplayName" not in calls
        assert "setApplicationName" in calls


class TestTheGuideSaysIt:

    def test_a_compute_of_the_window_has_no_result_id(self):
        text = (_ROOT / "docs" / "mcp" / "clientes.md").read_text(
            encoding="utf-8")
        part = text[text.index("## Ver en el programa lo que hace el agente"):]
        assert "al revés no" in part
        assert "result_id" in part and "analysis_run" in part


_RUN = {}


def _interpret_run():
    """Hammah et al. (2005), example 1, with Bishop and Spencer on a small
    grid: what ``repro_d363.py`` opens Interpret with."""
    if "run" not in _RUN:
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.materials import GeneralizedHoekBrown, Material
        from ogr_core.project import Project
        from ogr_slip2d.analysis_runner import run_analysis
        ext = Polyline(vertices=[Vertex(x, y) for x, y in _SLOPE],
                       closed=True)
        ext.ensure_ccw()
        p = Project("Hammah et al. 2005, ej. 1")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        rock = Material(name="roca", unit_weight=25.0,
                        strength=GeneralizedHoekBrown(
                            sigci=30000.0, mb=0.067, s=2.5e-5, a=0.619))
        p.materials = [rock]
        for reg in p.resolve_regions():
            cx, cy = reg.centroid()
            p.assign_material_at(cx, cy, rock.id)
        p.settings.methods.num_slices = 50
        methods = ["bishop_simplified", "spencer"]
        p.settings.methods.enabled_methods = methods
        ss = p.settings.search
        ss.grid_nx = ss.grid_ny = 4
        ss.radius_increment = 3
        _RUN["run"] = (p, run_analysis(p, methods).results)
    return _RUN["run"]


def _cut(win):
    """Every dock title, table heading and legend title without room."""
    from PySide6.QtWidgets import QDockWidget, QStyle, QTableWidget
    cut = []
    st = win.style()
    button = 16 + 2 * st.pixelMetric(QStyle.PM_DockWidgetTitleBarButtonMargin)
    margin = 2 * st.pixelMetric(QStyle.PM_DockWidgetTitleMargin)
    for dock in win.findChildren(QDockWidget):
        if dock.isVisible():
            need = dock.fontMetrics().horizontalAdvance(dock.windowTitle())
            if need > dock.width() - 2 * button - margin:
                cut.append(("dock", dock.windowTitle()))
    for table in win.findChildren(QTableWidget):
        if not table.isVisible():
            continue
        head = table.horizontalHeader()
        pad = 2 * head.style().pixelMetric(QStyle.PM_HeaderMargin)
        for c in range(table.columnCount()):
            item = table.horizontalHeaderItem(c)
            text = item.text() if item is not None else ""
            if text and (head.fontMetrics().horizontalAdvance(text) + pad
                         > head.sectionSize(c)):
                cut.append(("heading", text))
    legend = win.legend
    if hasattr(legend, "title_rect"):
        need = legend.title_rect(legend.width()).width()
    else:                                   # one line, as it was painted
        from PySide6.QtGui import QFont, QFontMetrics
        font = QFont(legend.font())
        font.setPointSizeF(max(7.0, font.pointSizeF() - 1.0))
        need = QFontMetrics(font).horizontalAdvance(legend._title)
    if need > legend.width():
        cut.append(("legend", legend._title))
    return cut


class TestInterpretCutsNothing:

    def test_two_widths_two_languages(self):
        from ogr_gui.i18n import current_language, set_language
        from ogr_gui.interpret_window import InterpretWindow
        from ogr_gui.qt_catalog import switch_qt_translator
        app = _app()
        p, results = _interpret_run()
        before = current_language()
        found = {}
        try:
            for lang in ("es", "en"):
                set_language(lang)
                switch_qt_translator(app, lang)
                for size in ((1536, 823), (1280, 720)):
                    win = InterpretWindow(p, results, None)
                    try:
                        win.resize(*size)
                        win.show()
                        for _ in range(20):
                            app.processEvents()
                        found[(lang, size)] = _cut(win)
                    finally:
                        win.close()
        finally:
            set_language(before)
            switch_qt_translator(app, before)
        assert not any(found.values()), found

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.324 (D315, D316, D317) — what the third test of the interface still
saw in English, or with the wrong word, with the interface in Spanish.

The defects:

* **D315.** The method's IDENTIFIER (``bishop_simplified``) reached the
  screen in the results panel (its summary and its Method column), in the
  status bar after computing and in Interpret (summary, table, free-body
  diagram title): it went as an argument of ``tr(...).format(...)`` or
  straight into a cell, where neither AST census looks. Five docks were
  titled in English by ``super().__init__("Results", parent)``, a call the
  census of test_gui_spanish_v1318 did not read (it does now).
* **D316.** 32 of the 39 tool-mode hints had no Spanish. The window writes
  its own translated message over most of them, which is why the test saw
  only two («Click head, then tail of the support»); the census of D101
  checked one mode's hint only.
* **D317.** Six entries called a grid «malla», which 0.1.323 keeps for the
  finite-element mesh («Tipo de malla:», «Mostrar malla»…).

Controls: in English the panel says «Bishop Simplified» and «Results».
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

_WINDOWS: list = []


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


def _spanish():
    from ogr_gui.i18n import _DICTS
    return _DICTS["es"]


class TestEveryToolModeHintHasSpanish:
    def test_all_of_them(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        es = _spanish()
        missing = [m.name for m in ToolMode
                   if m.status_message and m.status_message not in es]
        assert not missing, missing

    def test_the_two_the_test_saw(self):
        from ogr_gui.canvas.tool_mode import ToolMode
        es = _spanish()
        assert es[ToolMode.MOVE_BOUNDARY.status_message].startswith(
            "Pulsa un contorno")
        assert es[ToolMode.ADD_SUPPORT.status_message] == \
            "Pulsa la cabeza y después la cola del soporte"


class TestNoGridIsAMesh:
    def test_a_grid_key_never_says_malla(self):
        es = _spanish()
        left = sorted(k for k, v in es.items()
                      if re.search(r"\bgrid", k, re.I)
                      and not re.search(r"\bmesh", k, re.I)
                      and re.search(r"\bmalla", v, re.I))
        assert not left, left

    def test_control_the_mesh_is_still_a_malla(self):
        es = _spanish()
        assert es["Finite element mesh"] == "Malla de elementos finitos"


def _computed_demo(language):
    from test_design_factor_report_gui_v1165 import _compute_all
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language(language)
    w = MainWindow()
    _WINDOWS.append(w)
    w.act_load_demo()
    _compute_all(w)
    w.project.is_dirty = False
    return w


@_requires_qt
class TestTheMethodIsNamed:
    def _panel(self, w):
        dock = w.results_dock
        table = dock.table
        cells = [table.item(r, 2).text() for r in range(table.rowCount())
                 if table.item(r, 2) is not None]
        return dock.windowTitle(), cells, w.ogr_status.currentMessage()

    def test_in_spanish_and_in_english(self):
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        try:
            w = _computed_demo("es")
            title, cells, status = self._panel(w)
            assert title == "Resultados", title
            assert cells and all(c == "Bishop simplificado"
                                 or "_" not in c for c in cells), cells
            assert "bishop_simplified" not in status, status
            assert "Bishop simplificado" in status, status
            w.close()
            # control: the English names it, as it never did
            w = _computed_demo("en")
            title, cells, status = self._panel(w)
            assert title == "Results", title
            assert "Bishop Simplified" in cells, cells
            assert "Bishop Simplified" in status, status
            w.close()
        finally:
            set_language(before)


@_requires_qt
class TestTheInterpretDocksAreNamed:
    def test_summary_and_surfaces(self):
        from test_gui_spanish_v1318 import _interpret_window
        from ogr_gui.i18n import current_language, set_language
        before = current_language()
        try:
            _p, iw = _interpret_window("es")
            _WINDOWS.append(iw)
            assert iw.summary_dock.windowTitle() == "Resumen"
            assert iw.results_dock.windowTitle() == "Superficies"
            table = iw.results_dock.table
            methods = {table.item(r, 2).text()
                       for r in range(table.rowCount())
                       if table.item(r, 2) is not None}
            assert methods and not any("_" in m for m in methods), methods
        finally:
            set_language(before)

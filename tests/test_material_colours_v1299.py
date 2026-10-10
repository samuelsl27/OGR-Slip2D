# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.299 (D297) — a new material gets a colour no material of the model
uses yet, and an agent's rename reaches the window's title.

The defect: every material was born ``#d4a373`` (the default of
``Material.color``), whether ``model_define``, ``material_set`` or the
window's *Define Materials* created it, so two materials of a model could
not be told apart on the canvas (the second GUI test, H15). And
``model_define {"name": ...}`` renamed the project without the window's
title following, while ``project_new(name=...)`` did. The owner's decision:
the ``name`` of ``model_define`` IS the project's name.

What these tests protect:

* the palette: its first colour is the old default (a one-material model
  looks as before), the next ones skip the colours in use, and twelve in
  use repeat in order;
* ``model_define`` with three materials gives three different colours,
  ``material_set`` a fourth, and a colour given explicitly is kept;
* the window's *Define Materials* → Add gives a colour the list does not
  use;
* after an agent's edit the window's title carries the project's name.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from ogr_core.materials.palette import MATERIAL_PALETTE, next_material_color  # noqa: E402

_SOIL = {"model": "mohr_coulomb", "params": {"cohesion": 5.0, "friction_angle": 30.0}}


class TestThePalette:
    def test_the_first_colour_is_the_old_default(self):
        assert next_material_color([]) == "#d4a373"

    def test_colours_in_use_are_skipped(self):
        assert next_material_color(["#D4A373"]) == MATERIAL_PALETTE[1]
        assert next_material_color(["#d4a373", MATERIAL_PALETTE[2]]) == \
            MATERIAL_PALETTE[1]

    def test_all_in_use_repeat_in_order(self):
        assert next_material_color(MATERIAL_PALETTE) == MATERIAL_PALETTE[0]

    def test_the_palette_has_no_repeats(self):
        assert len(set(MATERIAL_PALETTE)) == len(MATERIAL_PALETTE)


class TestTheApi:
    def test_model_define_and_material_set_give_distinct_colours(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = call(ws, "project_new", name="d297")["project_id"]
            call(ws, "model_define", project_id=pid, spec={
                "external": [[0, 0], [20, 0], [20, 10], [0, 10]],
                "materials": [{"name": n, "unit_weight": 20, "strength": _SOIL}
                              for n in ("A", "B", "C")]})
            call(ws, "material_set", project_id=pid, name="D",
                 strength=_SOIL)
            p = ws.get(pid).project
            colours = [m.color for m in p.materials]
            assert colours[0] == "#d4a373"
            assert len(set(colours)) == 4, colours
        finally:
            ws.shutdown()

    def test_an_explicit_colour_is_kept(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        try:
            pid = call(ws, "project_new", name="d297b")["project_id"]
            call(ws, "model_define", project_id=pid, spec={
                "external": [[0, 0], [20, 0], [20, 10], [0, 10]],
                "materials": [{"name": "A", "unit_weight": 20, "strength": _SOIL,
                               "color": "#123456"}]})
            assert ws.get(pid).project.materials[0].color == "#123456"
        finally:
            ws.shutdown()


class TestTheWindow:
    def test_add_material_takes_an_unused_colour(self):
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        p = Project("d297w")
        p.add_material(Material(name="First", unit_weight=20.0,
                                strength=MohrCoulomb(cohesion=5.0,
                                                     friction_angle=30.0)))
        w = MainWindow()
        w._attach_project(p)
        dlg = w._materials_dialog()
        try:
            dlg._add_material()
            dlg._add_material()
            colours = [m.color for m in dlg.materials]
            assert len(set(colours)) == 3, colours
        finally:
            dlg.reject()
            w.project.is_dirty = False
            w.close()

    def test_an_agent_rename_reaches_the_title(self):
        from ogr_gui.agent_bridge import WindowHost
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        w = MainWindow()
        try:
            w.project.name = "Renamed by an agent"
            WindowHost(w).after_edit()
            assert w.windowTitle().endswith("Renamed by an agent"), \
                w.windowTitle()
        finally:
            w.project.is_dirty = False
            w.close()

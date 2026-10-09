# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.286 (D287) — a material that regions or weak layers use is not
removed by the window's materials dialog, as the API already refused.

The defect: ``material_delete`` refused to delete a material used by region
assignments, weak layers or Generalized Anisotropic ranges, while the
window's *Define Materials* removed it without a word unless a range linked
it (D218b). The regions were left pointing at an id that no longer exists;
the limit equilibrium then found no factor and blamed surfaces leaving the
model (``_auditoria/P8_interfaz/repro_d287.py`` of the bank: Bishop 1.5866
→ none). The rule now lives in ``ogr_core/project/rules.py``
(``material_users``) and both doors ask it.

What these tests protect:

* ``material_users`` counts the region assignments, the weak layers and the
  linked ranges of a material;
* the API still refuses, with the same message;
* the window's dialog, built as *Define Materials* builds it, refuses to
  remove a material that a region uses, says why in its own label (nothing
  modal) and keeps it in the list; and the same for a weak layer;
* a material nobody uses is still removed.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from ogr_api import Conflict, Workspace, call  # noqa: E402
from ogr_core.project.rules import material_region_uses, material_users  # noqa: E402

_SOIL = {"model": "mohr_coulomb", "params": {"cohesion": 5.0, "friction_angle": 30.0}}


def _app():
    return QApplication.instance() or QApplication([])


def _model(weak_layer=False):
    """Two layers, «Upper» and «Lower», each assigned to its region, and a
    third material «Spare» that nobody uses."""
    ws = Workspace()
    pid = call(ws, "project_new", name="d287")["project_id"]
    spec = {
        "external": [[0, 0], [40, 0], [40, 10], [0, 10]],
        "material_boundaries": [[[0, 5], [40, 5]]],
        "materials": [{"name": n, "unit_weight": 20, "strength": _SOIL}
                      for n in ("Upper", "Lower", "Spare")]}
    call(ws, "model_define", project_id=pid, spec=spec)
    call(ws, "material_assign", project_id=pid, material="Upper", x=20, y=7.5)
    call(ws, "material_assign", project_id=pid, material="Lower", x=20, y=2.5)
    p = ws.get(pid).project
    if weak_layer:
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        spare = next(m for m in p.materials if m.name == "Spare")
        b = Boundary(polyline=Polyline(vertices=[Vertex(0, 3), Vertex(40, 3)],
                                       closed=False),
                     btype=BoundaryType.WEAK_LAYER)
        b.material_id = spare.id
        p.add_boundary(b)
    return ws, pid, p


def _by_name(p, name):
    return next(m for m in p.materials if m.name == name)


class TestTheRule:
    def test_it_counts_regions_layers_and_ranges(self):
        ws, _pid, p = _model(weak_layer=True)
        try:
            regions, layers, links = material_users(p, _by_name(p, "Upper").id)
            assert (len(regions), len(layers), len(links)) == (1, 0, 0)
            regions, layers, links = material_users(p, _by_name(p, "Spare").id)
            assert (len(regions), len(layers), len(links)) == (0, 1, 0)
            uses = material_region_uses(p)
            assert uses[_by_name(p, "Lower").id] == (1, 0)
        finally:
            ws.shutdown()

    def test_the_api_still_refuses(self):
        ws, pid, _p = _model()
        try:
            try:
                call(ws, "material_delete", project_id=pid, material="Upper")
                raise AssertionError("material_delete removed a used material")
            except Conflict as exc:
                assert "used by 1 region assignment(s)" in str(exc), exc
        finally:
            ws.shutdown()


class TestTheWindow:
    def _dialog(self, p):
        from ogr_gui.main_window import MainWindow
        _app()
        w = MainWindow()
        w._attach_project(p)
        dlg = w._materials_dialog()
        return w, dlg

    def _remove(self, dlg, name):
        row = [m.name for m in dlg.materials].index(name)
        dlg.list.setCurrentRow(row)
        dlg._remove_material()

    def test_a_material_a_region_uses_is_not_removed(self):
        ws, _pid, p = _model()
        w, dlg = self._dialog(p)
        try:
            self._remove(dlg, "Upper")
            assert [m.name for m in dlg.materials] == ["Upper", "Lower", "Spare"]
            text = dlg.lbl_strength_problem.text()
            assert "Upper" in text and "1" in text, text
            assert dlg.lbl_strength_problem.isVisibleTo(dlg)
        finally:
            dlg.reject()
            w.close()
            ws.shutdown()

    def test_a_material_a_weak_layer_uses_is_not_removed(self):
        ws, _pid, p = _model(weak_layer=True)
        w, dlg = self._dialog(p)
        try:
            self._remove(dlg, "Spare")
            assert "Spare" in [m.name for m in dlg.materials]
            assert "Spare" in dlg.lbl_strength_problem.text()
        finally:
            dlg.reject()
            w.close()
            ws.shutdown()

    def test_a_material_nobody_uses_is_removed(self):
        ws, _pid, p = _model()
        w, dlg = self._dialog(p)
        try:
            self._remove(dlg, "Spare")
            assert [m.name for m in dlg.materials] == ["Upper", "Lower"]
        finally:
            dlg.reject()
            w.close()
            ws.shutdown()

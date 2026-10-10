# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.298 (D298) — a region assigned to a material that no longer exists is
said, with its remedy, by every door; the window asks before computing.

The defect: up to 0.1.285 the window's *Define Materials* removed a
material in use and left its regions pointing at it (D287), and a file
saved then keeps them. ``resolve_regions`` copies the id unchecked,
``material_at`` gives None there, and the slicer refused every surface
through such a region as "outside the External Boundary", while
``project_validate`` said the model could run. Measured on the model of
``_auditoria/P8_interfaz/repro_d298.py``: can_run true and no warning;
Bishop with no factor and «1562 surfaces … left the model».

The owner's decision: warn, say what is wrong and what to change, and let
the user compute anyway. What these tests protect:

* ``rules.orphan_assignments`` finds the assignment, and
  ``in_orphan_region`` tells a point in that region from one outside the
  model and from one in a sound region;
* ``project_validate`` warns (it does not block);
* the analysis says it first, and the search names the real cause of the
  refused surfaces («a region whose material no longer exists») instead of
  «left the model»;
* a sound model warns nothing;
* the window asks «compute anyway?» and, answered No, computes nothing;
  without a screen it does not ask;
* opening a file with such a region says so on the status bar.

None of the 264 models of the verification bank has one (census of
2026-10-10), so no number of the bank moves. Patches are restored in
``finally`` (rule 5).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox  # noqa: E402

_SOIL = lambda c: {"model": "mohr_coulomb",  # noqa: E731
                   "params": {"cohesion": c, "friction_angle": 30.0}}


def _model(orphan=True):
    """The model of the reproduction: a strong lower layer and a weak
    upper one; with ``orphan``, the weak material removed from the list and
    its assignment left, as the dialog left it before 0.1.286."""
    from ogr_api import Workspace, call
    ws = Workspace()
    pid = call(ws, "project_new", name="d298")["project_id"]
    call(ws, "model_define", project_id=pid, spec={
        "external": [[0, 0], [40, 0], [40, 10], [20, 10], [10, 5], [0, 5]],
        "material_boundaries": [[[0, 3], [40, 3]]],
        "materials": [{"name": "Strong", "unit_weight": 20, "strength": _SOIL(50.0)},
                      {"name": "Weak", "unit_weight": 20, "strength": _SOIL(2.0)}]})
    call(ws, "material_assign", project_id=pid, material="Strong", x=20, y=1.5)
    call(ws, "material_assign", project_id=pid, material="Weak", x=30, y=6)
    p = ws.get(pid).project
    if orphan:
        weak = next(m for m in p.materials if m.name == "Weak")
        p.materials = [m for m in p.materials if m.id != weak.id]
    return ws, pid, p


class TestTheRule:
    def test_it_finds_the_orphan_and_tells_the_places_apart(self):
        from ogr_core.project.rules import in_orphan_region, orphan_assignments
        ws, _pid, p = _model()
        try:
            assert len(orphan_assignments(p)) == 1
            assert in_orphan_region(p, 30.0, 6.0) is True
            assert in_orphan_region(p, 20.0, 1.5) is False
            assert in_orphan_region(p, 100.0, 100.0) is False
        finally:
            ws.shutdown()

    def test_a_sound_model_has_none(self):
        from ogr_core.project.rules import orphan_assignments
        ws, _pid, p = _model(orphan=False)
        try:
            assert orphan_assignments(p) == []
        finally:
            ws.shutdown()


class TestTheDoors:
    def test_project_validate_warns_without_blocking(self):
        from ogr_api import call
        ws, pid, _p = _model()
        try:
            v = call(ws, "project_validate", project_id=pid)
            assert v["can_run"] is True
            assert any("no longer exists" in w for w in v["warnings"]), v
        finally:
            ws.shutdown()

    def test_the_analysis_names_the_real_cause(self):
        from ogr_slip2d.analysis_runner import run_analysis
        ws, _pid, p = _model()
        try:
            p.settings.methods.enabled_methods = ["bishop_simplified"]
            out = run_analysis(p)
            assert "no longer exists" in out.warnings[0], out.warnings[:2]
            notes = " ".join(out.warnings)
            assert "region whose material no longer exists" in notes, notes
            assert "left the model" not in notes, notes
        finally:
            ws.shutdown()

    def test_a_sound_model_warns_nothing(self):
        from ogr_slip2d.analysis_runner import run_analysis
        ws, _pid, p = _model(orphan=False)
        try:
            p.settings.methods.enabled_methods = ["bishop_simplified"]
            out = run_analysis(p)
            assert not any("no longer exists" in w for w in out.warnings)
        finally:
            ws.shutdown()


class TestTheWindow:
    def _window(self, project):
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        w = MainWindow()
        w._attach_project(project)
        return w

    def test_without_a_screen_it_does_not_ask(self):
        ws, _pid, p = _model()
        w = self._window(p)
        try:
            assert w._confirm_orphan_regions() is True
        finally:
            w.project.is_dirty = False
            w.close()
            ws.shutdown()

    def test_it_asks_and_no_computes_nothing(self):
        ws, _pid, p = _model()
        w = self._window(p)
        asked = []
        raw_q = QMessageBox.__dict__.get("question")
        raw_p = QApplication.__dict__.get("platformName")
        QMessageBox.question = staticmethod(
            lambda _p, title, text, *a, **k: asked.append(text) or QMessageBox.No)
        QApplication.platformName = staticmethod(lambda: "windows")
        try:
            assert w._confirm_orphan_regions() is False
            assert "no longer exists" in asked[0]
            assert "Compute anyway?" in asked[0]
            w.worker = None
            w.act_compute()
            assert w.worker is None, "act_compute started a run after No"
        finally:
            for name, raw, owner in (("question", raw_q, QMessageBox),
                                     ("platformName", raw_p, QApplication)):
                if raw is None:
                    delattr(owner, name)
                else:
                    setattr(owner, name, raw)
            w.project.is_dirty = False
            w.close()
            ws.shutdown()

    def test_opening_such_a_file_says_so(self):
        ws, _pid, p = _model()
        path = Path(tempfile.mkdtemp(prefix="ogr_test_d298_")) / "orphan.ogr"
        p.save(path)
        ws.shutdown()
        from ogr_core.project import Project
        w = self._window(Project("x"))
        raw = QFileDialog.__dict__.get("getOpenFileName")
        QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(path), ""))
        try:
            w.act_open()
            assert "no longer exists" in w.statusBar().currentMessage()
        finally:
            if raw is None:
                del QFileDialog.getOpenFileName
            else:
                QFileDialog.getOpenFileName = raw
            w.project.is_dirty = False
            w.close()

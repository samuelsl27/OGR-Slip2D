# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.297 (D304) — the results panel says when its result is of an earlier
model.

The defect: after computing the demo slope and moving its toe with *Move
Vertex*, the canvas dropped the surfaces but the results panel kept
«1.0914 | bishop_simplified …» and «FS crítico: 1.091», as if they were of
the geometry on screen (the second GUI test, H9). The API marks such a
result stale with a fingerprint of what an analysis reads
(``ogr_api.snapshot.model_hash``); the window had nothing. The owner's
decision: mark it, with the same fingerprint, and let a new compute clear
the mark.

What these tests protect, through the window's real compute path
(``_ComputeWorker.run`` + ``_on_compute_done``, as
``test_design_factor_report_gui_v1165`` drives it):

* a result just computed is not stale;
* an edit of the geometry makes it stale: the notice shows and the table
  greys out;
* undoing the edit gives the fingerprint back, and the mark goes;
* computing again clears it;
* an annotation, which no analysis reads, does not mark it;
* a project event starts the deferred check (the tests call the check
  directly instead of waiting for the timer).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402


def _slope():
    """The small homogeneous slope of test_design_factor_report_gui_v1165:
    three centres by three, three radii — fast to search."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection
    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
        Vertex(35, 15), Vertex(25, 25), Vertex(0, 25),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("d304")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.settings.units.failure_direction = FailureDirection.LEFT_TO_RIGHT
    p.add_material(Material(
        name="Silty clay", unit_weight=19.0,
        strength=MohrCoulomb(cohesion=10.0, friction_angle=25.0)))
    p.settings.methods.enabled_methods = ["bishop_simplified"]
    p.settings.methods.num_slices = 25
    p.settings.search.grid_nx = 3
    p.settings.search.grid_ny = 3
    p.settings.search.radius_increment = 2
    return p


def _computed_window():
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow, _ComputeWorker
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    w._attach_project(_slope())
    _compute(w)
    return w


def _compute(w):
    from ogr_gui.main_window import _ComputeWorker
    errors = []
    w.worker = _ComputeWorker(w.project, ["bishop_simplified"])
    w.worker.failed.connect(errors.append)
    w.worker.run()
    assert not errors, errors
    w._on_compute_done(w.worker.results)


def _move_toe(w):
    from ogr_core.project.commands import SnapshotCommand

    def move(project):
        from ogr_core.geometry import Vertex
        v = project.boundaries[0].polyline.vertices
        i = next(k for k, x in enumerate(v) if (x.x, x.y) == (35, 15))
        v[i] = Vertex(37.0, 15.0)
    w.command_stack.do(w.project, SnapshotCommand(
        "Edit Boundary", move, attrs=("boundaries",)))


def _done(w):
    w.project.is_dirty = False
    w.close()


class TestTheMark:
    def test_a_result_just_computed_is_not_stale(self):
        w = _computed_window()
        try:
            w._check_results_stale()
            assert w.results_dock.is_stale() is False
            assert not w.results_dock.stale_label.isVisibleTo(w.results_dock)
        finally:
            _done(w)

    def test_an_edit_marks_it_and_undo_clears_it(self):
        w = _computed_window()
        try:
            _move_toe(w)
            w._check_results_stale()
            assert w.results_dock.is_stale() is True
            assert w.results_dock.stale_label.isVisibleTo(w.results_dock)
            assert not w.results_dock.table.isEnabled()
            w.command_stack.undo(w.project)
            w._check_results_stale()
            assert w.results_dock.is_stale() is False
            assert w.results_dock.table.isEnabled()
        finally:
            _done(w)

    def test_computing_again_clears_it(self):
        w = _computed_window()
        try:
            _move_toe(w)
            w._check_results_stale()
            assert w.results_dock.is_stale() is True
            _compute(w)
            w._check_results_stale()
            assert w.results_dock.is_stale() is False
        finally:
            _done(w)

    def test_an_annotation_does_not_mark_it(self):
        from ogr_core.annotations import Annotation, AnnotationKind
        w = _computed_window()
        try:
            w.project.annotations.add(Annotation(
                kind=AnnotationKind.LINE, points=[(1.0, 1.0), (5.0, 2.0)]))
            w.project._notify("annotation_added")
            w._check_results_stale()
            assert w.results_dock.is_stale() is False
        finally:
            _done(w)

    def test_a_project_event_starts_the_deferred_check(self):
        w = _computed_window()
        try:
            w._stale_timer.stop()
            w.project._notify("boundary_modified")
            assert w._stale_timer.isActive()
        finally:
            w._stale_timer.stop()
            _done(w)

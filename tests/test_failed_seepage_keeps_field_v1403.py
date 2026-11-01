# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.403 (D388) — a groundwater solve that produced no field leaves the
project as it was.

WHAT INVARIANT THIS PROTECTS.

The interface test of 0.1.402 (hallazgo 1, its only FALLO) opened bank
problem 010, whose stored seepage field gives Bishop 1.4803266154071344 on
the published grid. *Compute Groundwater* answered with the solver's refusal
("no Dirichlet (head) boundary condition: the problem is singular"), and the
field was gone: ``solve_project_groundwater`` wrote the refused result, with
no heads, over ``project.seepage_result``, and the next Compute refused for
want of a field. A transient whose initial steady state cannot be solved
(D341) wrote its empty result over the project's stages the same way. The
API's door has refused to write a fieldless result back since v0.1.200
(``ogr_api.ops.groundwater._finish_groundwater``); the door everyone shares
now does it.

1. **A steady refusal keeps the field:** the result comes back with its
   reason, and the project's field, transient stages, initial state, solver
   and ponding cache are the objects they were.
2. **A transient whose initial state fails keeps them too.**
3. **A computed field is written as before** (the guard against refusing
   too much).
4. **In the window,** *Compute Groundwater* on such a model says the reason,
   keeps the field, and leaves a computed result current (not stale), with
   no undo step and nothing to save.

The models are a rectangle of one material on a coarse mesh: no clock.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_W, _H = 20.0, 8.0


def _project(heads: bool):
    """One material on a coarse mesh, with heads on its two sides or with
    no prescribed head at all (the steady problem is then singular)."""
    from ogr_core.geometry import Polyline, Vertex
    from ogr_core.geometry.regions import MaterialRegion
    from ogr_core.hydraulic.hydraulic_properties import HydraulicProperties
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_fem2d.mesh import generate_mesh
    from ogr_fem2d.solvers import BCType, SeepageBoundaryConditions
    poly = Polyline(vertices=[Vertex(0, 0), Vertex(_W, 0), Vertex(_W, _H),
                              Vertex(0, _H)], closed=True)
    mesh = generate_mesh([MaterialRegion(polygon=poly, material_id="m")],
                         target_size=2.0)
    p = Project()
    mat = Material(name="m", strength=MohrCoulomb(cohesion=10.0,
                                                  friction_angle=30.0))
    mat.id = "m"
    mat.hydraulic = HydraulicProperties(ks=1e-6)
    mat.pore_pressure = PorePressureType.FEM_SEEPAGE
    p.materials = [mat]
    p.fem_mesh = mesh
    bcs = SeepageBoundaryConditions()
    if heads:
        for nid in sorted(mesh.boundary_node_ids()):
            nd = mesh.nodes[nid]
            if abs(nd.x) < 1e-9:
                bcs.add_node(nid, BCType.TOTAL_HEAD, 6.0)
            elif abs(nd.x - _W) < 1e-9:
                bcs.add_node(nid, BCType.TOTAL_HEAD, 3.0)
    p.seepage_bcs = bcs
    return p


def _with_stored_field():
    """A project with a solved field, whose heads are then removed: what
    bank problem 010 is (a field stored, no conditions saved)."""
    from ogr_fem2d.solvers import SeepageBoundaryConditions
    from ogr_slip2d.transient_stability import solve_project_groundwater
    p = _project(heads=True)
    field = solve_project_groundwater(p)
    assert field.total_head and p.seepage_result is field
    p.seepage_bcs = SeepageBoundaryConditions()
    return p, field


_KEPT = ("seepage_result", "transient_results", "transient_initial_result",
         "_gw_solver", "_fea_ponding_cache")


def _state(p):
    return {a: getattr(p, a, None) for a in _KEPT}


def _same(before, p):
    return [a for a in _KEPT if getattr(p, a, None) is not before[a]]


class TestARefusalLeavesTheProject:
    """Invariants 1 to 3."""

    def test_a_steady_refusal_keeps_the_field(self):
        from ogr_slip2d.transient_stability import solve_project_groundwater
        p, field = _with_stored_field()
        p.transient_results = [field]           # a transient run before
        p._fea_ponding_cache = object()
        before = _state(p)
        out = solve_project_groundwater(p)
        assert out.notes.get("error") is not None and not out.total_head
        assert _same(before, p) == [], (
            "the refusal changed %s" % _same(before, p))
        assert p.seepage_result is field

    def test_a_transient_whose_initial_state_fails_keeps_them(self):
        from ogr_fem2d.solvers import SeepageBoundaryConditions
        from ogr_slip2d.transient_stability import solve_project_groundwater
        p, field = _with_stored_field()
        p.seepage_bcs = _project(heads=True).seepage_bcs   # stages solvable
        gw = p.settings.groundwater
        gw.set_advanced_option("transient")
        gw.transient_stages = [{"time": 0.0, "label": "t = 0"},
                               {"time": 3600.0, "label": "1 h"}]
        gw.transient_initial_bcs = SeepageBoundaryConditions().to_dict()
        stages = [field]
        p.transient_results = stages
        before = _state(p)
        results = solve_project_groundwater(p)
        assert len(results) == 1 and not results[0].total_head
        assert results[0].notes.get("error") is not None
        assert _same(before, p) == [], (
            "the failed transient changed %s" % _same(before, p))
        assert p.transient_results is stages and p.seepage_result is field

    def test_a_computed_field_is_still_written(self):
        from ogr_slip2d.transient_stability import solve_project_groundwater
        p = _project(heads=True)
        old = object()
        p.seepage_result = old
        out = solve_project_groundwater(p)
        assert out.total_head
        assert p.seepage_result is out and p.transient_results == []


class TestTheWindow:
    """Invariant 4."""

    def test_compute_groundwater_keeps_the_field(self):
        from PySide6.QtWidgets import QApplication
        from ogr_api.snapshot import model_hash
        from ogr_gui.i18n import current_language, set_language
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        lang = current_language()
        set_language("en")
        p, field = _with_stored_field()
        w = MainWindow()
        try:
            w.canvas.set_project(p)
            w.project = p
            w.command_stack.clear()
            history = w.command_stack.history()
            p.is_dirty = False
            w._results_model_hash = model_hash(p)   # a result of this model
            said = []
            bar = w.statusBar()
            real = bar.showMessage
            bar.showMessage = lambda text, *a: (said.append(text),
                                                real(text, *a))[1]
            w._compute_groundwater()
            assert said and "Dirichlet" in said[-1], said
            assert p.seepage_result is field, "the field was replaced"
            assert w._results_are_current(), "the result went stale"
            assert w.command_stack.history() == history, (
                "a refusal left an undo step: %r" % (w.command_stack.history(),))
            assert p.is_dirty is False
        finally:
            set_language(lang)
            p.is_dirty = False
            w.close()
            w.deleteLater()

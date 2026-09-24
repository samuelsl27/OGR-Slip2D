# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.194 (spec 008) — rules the interface enforced now live in the core,
and the interface asks them.

Invariants protected:

* ``ogr_core.project.rules.boundary_refusal`` gives the answers the
  interface used to give by greying menu items, and only those: one water
  table, one tension crack, one external boundary, a drawdown line only
  with rapid drawdown and only one, a Block Search object only with the
  Block Search; any number of piezometric lines and material boundaries.
* ``compute_blockers`` reports the two empty-model refusals of
  ``act_compute``, with codes, in the order the interface checks them.
* ``assign_water_surface`` sets the pore-pressure model with the surface
  (the v0.1.97 rule: an id without a model moved nothing).
* **Moved, not copied.** Replacing the rule in ``rules`` changes what the
  interface does — the one test that tells a delegation from a second
  copy that merely agrees today.
* ``SnapshotCommand`` restores onto the SAME object, is atomic, and knows
  whether it changed anything; ``CommandStack.record`` pushes without
  executing, and ``history`` reads descriptions as strings (calling the
  one that is a method by mistake, ``PaintRegionCommand.description``,
  reported and not changed).
* The test runner refuses an ``async def`` test instead of counting a body
  that never ran as a pass.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_TESTS = Path(__file__).resolve().parent
_WINDOWS: list = []


def _model():
    from ogr_api import Workspace, call
    ws = Workspace()
    pid = call(ws, "project_new", name="Rules")["project_id"]
    call(ws, "model_define", project_id=pid, spec={
        "external": [[0, 0], [40, 0], [40, 10], [20, 10], [10, 5], [0, 5]],
        "materials": [{"name": "Soil", "strength": {
            "model": "mohr_coulomb",
            "params": {"cohesion": 5, "friction_angle": 30}}}]})
    project = ws.get(pid).project
    ws.shutdown()
    return project


def _line(btype, y=3.0):
    from ogr_core.geometry import Boundary, Polyline, Vertex
    return Boundary(polyline=Polyline(vertices=[Vertex(0, y), Vertex(40, y)],
                                      closed=False), btype=btype)


class TestBoundaryRefusal:
    def test_single_instance_types(self):
        from ogr_core.geometry import BoundaryType as B
        from ogr_core.project.rules import boundary_refusal
        p = _model()
        assert boundary_refusal(p, B.EXTERNAL).code == "single_instance"
        for bt in (B.WATER_TABLE, B.TENSION_CRACK):
            assert boundary_refusal(p, bt) is None
            p.add_boundary(_line(bt))
            assert boundary_refusal(p, bt).code == "single_instance"
        for bt in (B.PIEZOMETRIC, B.MATERIAL, B.WEAK_LAYER):
            p.add_boundary(_line(bt))
            assert boundary_refusal(p, bt) is None

    def test_drawdown_needs_the_analysis_first_then_one(self):
        from ogr_core.geometry import BoundaryType as B
        from ogr_core.project.rules import boundary_refusal
        p = _model()
        assert boundary_refusal(p, B.DRAWDOWN).code == \
            "requires_rapid_drawdown"
        p.settings.groundwater.set_advanced_option("rapid_drawdown")
        assert boundary_refusal(p, B.DRAWDOWN) is None
        p.add_boundary(_line(B.DRAWDOWN))
        assert boundary_refusal(p, B.DRAWDOWN).code == "single_instance"

    def test_block_object_needs_the_block_search(self):
        from ogr_core.geometry import BoundaryType as B
        from ogr_core.project.rules import boundary_refusal
        p = _model()
        assert boundary_refusal(p, B.BLOCK_SEARCH_OBJECT).code == \
            "requires_block_search"
        p.settings.search.surface_type = "non_circular"
        p.settings.search.search_method = "block"
        assert boundary_refusal(p, B.BLOCK_SEARCH_OBJECT) is None


class TestComputeBlockers:
    def test_codes_and_order(self):
        from ogr_core.project import Project
        from ogr_core.project.rules import compute_blockers
        assert [r.code for r in compute_blockers(Project())] == [
            "no_boundaries", "no_materials"]
        assert compute_blockers(_model()) == []


class TestWaterSurface:
    def test_the_model_follows_the_surface(self):
        from ogr_core.geometry import BoundaryType as B
        from ogr_core.materials import PorePressureType as P
        from ogr_core.project.rules import assign_water_surface
        p = _model()
        wt, pz = _line(B.WATER_TABLE), _line(B.PIEZOMETRIC, 4.0)
        p.add_boundary(wt)
        p.add_boundary(pz)
        m = p.materials[0]
        assign_water_surface(p, wt.id, [m.id])
        assert (m.water_surface_id, m.pore_pressure) == (wt.id,
                                                         P.WATER_TABLE)
        assign_water_surface(p, pz.id, [m.id])
        assert m.pore_pressure == P.PIEZO_LINE
        assign_water_surface(p, pz.id, [], [m.id])
        assert (m.water_surface_id, m.pore_pressure) == (None, P.NONE)


def _qt():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:  # pragma: no cover
        return None
    return QApplication.instance() or QApplication([])


def _window(project):
    from ogr_gui.main_window import MainWindow
    w = MainWindow()
    w.PROMPT_ASSIGN_ON_DRAW = False
    w.project = project
    _WINDOWS.append(w)
    return w


class TestTheInterfaceAsksTheRules:
    def test_greying_follows_the_rule_not_a_copy_of_it(self):
        if _qt() is None:  # pragma: no cover
            return
        from ogr_core.geometry import BoundaryType as B
        import ogr_core.project.rules as rules
        p = _model()
        p.add_boundary(_line(B.WATER_TABLE))
        w = _window(p)
        w.refresh_action_availability()
        assert not w._actions["add_wt"].isEnabled()
        saved = rules.boundary_refusal
        try:
            rules.boundary_refusal = lambda *_a, **_k: None
            w.refresh_action_availability()
            assert w._actions["add_wt"].isEnabled()
            assert w._actions["add_crack"].isEnabled()
            assert w._actions["block_object"].isEnabled()
            assert w._actions["add_drawdown"].isEnabled()
        finally:
            rules.boundary_refusal = saved
        w.refresh_action_availability()
        assert not w._actions["add_wt"].isEnabled()

    def test_the_water_assignment_is_the_rules_one(self):
        if _qt() is None:  # pragma: no cover
            return
        import ogr_core.project.rules as rules
        p = _model()
        w = _window(p)
        calls = []
        saved = rules.assign_water_surface
        try:
            rules.assign_water_surface = lambda *a, **k: calls.append(a)
            w.apply_water_surface_assignment("wid", ["m"], [])
        finally:
            rules.assign_water_surface = saved
        assert calls and calls[0][1:] == ("wid", ["m"], [])


class TestSnapshotCommand:
    def test_restores_onto_the_same_object_and_is_atomic(self):
        from ogr_core.project.commands import CommandStack, SnapshotCommand
        p = _model()
        mats = p.materials
        stack = CommandStack()

        def rename(project):
            project.materials[0].name = "Renamed"
            project.materials.append(project.materials[0])

        cmd = SnapshotCommand("rename", rename)
        stack.do(p, cmd)
        assert cmd.changed and p.materials[0].name == "Renamed"
        stack.undo(p)
        assert p.materials[0].name == "Soil" and len(p.materials) == 1
        assert p.materials is not mats            # a fresh list ...
        stack.redo(p)
        assert len(p.materials) == 2              # ... on the same object

        def boom(project):
            project.name = "half"
            raise RuntimeError("stop")
        before = p.name
        with pytest.raises(RuntimeError):
            stack.do(p, SnapshotCommand("boom", boom))
        assert p.name == before
        assert stack.history()[0] == ["rename"]

    def test_record_and_history(self):
        from ogr_core.project.commands import (CommandStack,
                                               PaintRegionCommand,
                                               SnapshotCommand)
        p = _model()
        stack = CommandStack()
        cmd = SnapshotCommand("noop", lambda project: None)
        cmd.execute(p)
        assert cmd.changed is False
        stack.record(cmd)
        paint = PaintRegionCommand(x=20.0, y=4.0, material_id="m")
        stack.record(paint)
        undo, redo = stack.history()
        assert undo[0] == "noop" and undo[1].startswith("Paint material")
        assert redo == []


class TestTheRunnerRefusesCoroutines:
    def _runner(self):
        saved = sys.modules.get("pytest")
        try:
            spec = importlib.util.spec_from_file_location(
                "_ogr_runner_under_test_v1194", _TESTS / "_runner.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        finally:
            if saved is not None:
                sys.modules["pytest"] = saved
            else:
                sys.modules.pop("pytest", None)

    def test_an_async_test_fails_instead_of_passing_empty(self):
        runner = self._runner()
        ran = []

        class Case:
            async def test_async(self):
                ran.append(True)

            def test_plain(self):
                ran.append("plain")

        with pytest.raises(TypeError):
            runner._run_method(Case(), Case.test_async)
        assert ran == []
        runner._run_method(Case(), Case.test_plain)
        assert ran == ["plain"]

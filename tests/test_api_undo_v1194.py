# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.194 (spec 008) — every edit is one exact undo step, or no trace at all.

Invariants protected, for EVERY operation that edits a model:

* doing it, undoing it and redoing it gives back exactly the serialised
  model of before and after (``Project.to_dict``, compared as JSON);
* the ``Project`` OBJECT survives undo and redo — the interface, the canvas
  and an agent's handle all hold a reference to it, so a restore that
  swapped the object would leave them editing a ghost;
* an operation that fails leaves the model byte-identical and adds no
  undo step (``SnapshotCommand`` is atomic; ``CommandStack.do`` only
  records a command whose ``execute`` returned).

The table of examples below must name every editing operation in the
registry: an operation added later without an entry here fails
``test_every_editing_operation_has_an_example``. That is what makes this
file a property of the registry and not of the eight operations that
happened to exist when it was written.

Why it matters beyond convenience: until this version only the geometry
edits of the interface could be undone (loads, supports, materials and
settings could not), and an agent that makes a mistake needs a way back
that restores the model EXACTLY, not approximately.
"""
from __future__ import annotations

import json

import pytest

_SOIL = {"model": "mohr_coulomb",
         "params": {"cohesion": 3.0, "friction_angle": 19.6}}


def _setup():
    from ogr_api import Workspace, call

    ws = Workspace()
    pid = call(ws, "project_new", name="Undo")["project_id"]
    call(ws, "model_define", project_id=pid, spec={
        "external": [[20, 20], [70, 20], [70, 35], [50, 35], [30, 25],
                     [20, 25]],
        "material_boundaries": [[[20, 22.5], [70, 27.5]]],
        "materials": [
            {"name": "Soil", "unit_weight": 20.0, "strength": _SOIL,
             "at": [60, 32]},
            {"name": "Base", "unit_weight": 21.0, "strength": _SOIL,
             "at": [60, 21]}]})
    return ws, pid


def _external_id(project):
    return project.external_boundary().id


#: operation -> function(project) -> kwargs. Every editing operation of
#: the registry must appear here (see the meta-test).
EXAMPLES = {
    "boundary_add": lambda p: {"type": "water_table",
                               "points": [[20, 23], [70, 23]],
                               "assign_to": "all"},
    "boundary_edit": lambda p: {"boundary": _external_id(p),
                                "op": "move_vertex", "index": 0,
                                "point_xy": [20, 19]},
    "material_set": lambda p: {"name": "Clay", "strength": _SOIL,
                               "properties": {"unit_weight": 18.5}},
    "material_delete": lambda p: {"material": "Base",
                                  "reassign_to": "Soil"},
    "material_assign": lambda p: {"material": "Base", "x": 60, "y": 32},
    "model_define": lambda p: {"spec": {
        "external": [[0, 0], [40, 0], [40, 10], [20, 10], [10, 5],
                     [0, 5]],
        "materials": [{"name": "Sand", "strength": _SOIL}]}},
    "settings_set": lambda p: {"changes": {"methods.num_slices": 31,
                                           "search.search_method":
                                               "slope"}},
    "analysis_configure": lambda p: {"methods": ["spencer"],
                                     "num_slices": 44},
    "python_exec": lambda p: {"code": "project.name = 'renamed'\n"
                                      "project.materials[0].unit_weight"
                                      " = 17.0"},
}

#: Editing operations that are not an edit to undo.
_NOT_EDITS = {"project_history"}


def _state(ws, pid) -> str:
    return json.dumps(ws.get(pid).project.to_dict(), sort_keys=True,
                      default=str)


class TestEveryEditIsOneExactStep:
    def test_every_editing_operation_has_an_example(self):
        from ogr_api import OPERATIONS
        editing = {n for n, op in OPERATIONS.items() if op.mutates}
        missing = editing - set(EXAMPLES) - _NOT_EDITS
        assert not missing, f"no undo example for {sorted(missing)}"
        stale = set(EXAMPLES) - editing
        assert not stale, f"examples for non-editing ops: {sorted(stale)}"

    def test_do_undo_redo_restore_the_model_exactly(self):
        from ogr_api import call
        for name, make in EXAMPLES.items():
            ws, pid = _setup()
            try:
                handle = ws.get(pid)
                obj = handle.project
                steps = len(handle.stack.history()[0])
                before = _state(ws, pid)
                out = call(ws, name, project_id=pid, **make(obj))
                if name == "python_exec":
                    assert out["ok"], out
                after = _state(ws, pid)
                assert after != before, f"{name} changed nothing"
                assert len(handle.stack.history()[0]) == steps + 1, name
                call(ws, "project_history", project_id=pid, action="undo")
                assert _state(ws, pid) == before, f"{name}: undo differs"
                assert handle.project is obj, f"{name}: object replaced"
                call(ws, "project_history", project_id=pid, action="redo")
                assert _state(ws, pid) == after, f"{name}: redo differs"
                assert handle.project is obj
            finally:
                ws.shutdown()


class TestAFailedEditLeavesNoTrace:
    def test_refused_edits_change_nothing(self):
        from ogr_api import Conflict, InvalidArgument, NotFound, call
        ws, pid = _setup()
        try:
            call(ws, "boundary_add", project_id=pid, type="water_table",
                 points=[[20, 23], [70, 23]])
            handle = ws.get(pid)
            steps = len(handle.stack.history()[0])
            before = _state(ws, pid)
            attempts = [
                (Conflict, "boundary_add",
                 dict(type="water_table", points=[[20, 24], [70, 24]])),
                (Conflict, "boundary_add",
                 dict(type="external", points=[[0, 0], [1, 0], [1, 1]])),
                (Conflict, "material_delete", dict(material="Base")),
                (NotFound, "material_set",
                 dict(material="Nope", properties={"unit_weight": 5})),
                (InvalidArgument, "material_assign",
                 dict(material="Soil", x=500, y=500)),
                (InvalidArgument, "model_define",
                 dict(spec={"external": [[0, 0], [1, 1]]})),
                (InvalidArgument, "material_set",
                 dict(material="Soil", properties={"unit_wieght": 5})),
            ]
            for exc_type, name, kwargs in attempts:
                with pytest.raises(exc_type):
                    call(ws, name, project_id=pid, **kwargs)
                assert _state(ws, pid) == before, name
            assert len(handle.stack.history()[0]) == steps
        finally:
            ws.shutdown()

    def test_a_script_that_raises_is_rolled_back(self):
        from ogr_api import call
        ws, pid = _setup()
        try:
            before = _state(ws, pid)
            out = call(ws, "python_exec", project_id=pid,
                       code="project.name = 'half'\nraise ValueError('x')")
            assert out["ok"] is False and out["rolled_back"] is True
            assert "ValueError" in out["error"]
            assert _state(ws, pid) == before
        finally:
            ws.shutdown()

    def test_an_edit_that_changes_nothing_is_not_a_step(self):
        from ogr_api import call
        ws, pid = _setup()
        try:
            steps = len(ws.get(pid).stack.history()[0])
            call(ws, "python_exec", project_id=pid, code="x = 1 + 1")
            assert len(ws.get(pid).stack.history()[0]) == steps
        finally:
            ws.shutdown()


class TestAScriptIsOneStep:
    def test_operations_called_from_a_script_undo_together(self):
        from ogr_api import call
        ws, pid = _setup()
        try:
            before = _state(ws, pid)
            steps = len(ws.get(pid).stack.history()[0])
            out = call(ws, "python_exec", project_id=pid, code=(
                "api.material_set(name='Peat', strength="
                "{'model': 'undrained', 'params': {'cohesion': 12}})\n"
                "api.settings_set(changes={'methods.num_slices': 12})\n"
                "len(project.materials)"))
            assert out["ok"], out
            assert out["value"] == "3"
            assert len(ws.get(pid).stack.history()[0]) == steps + 1
            call(ws, "project_history", project_id=pid, action="undo")
            assert _state(ws, pid) == before
        finally:
            ws.shutdown()

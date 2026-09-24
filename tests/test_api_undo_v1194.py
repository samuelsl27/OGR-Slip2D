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
    # v0.1.196 (F2): loads, supports, search objects, annotations, files
    # and the two geometry operations. What an operation needs to exist
    # first (a load to delete, a pattern to ungroup) is made by PREPARE,
    # outside the step being measured.
    "load_set": lambda p: {"kind": "distributed", "start": [50, 35],
                           "end": [70, 35], "magnitude": 20.0,
                           "orientation": "vertical",
                           "creates_excess_pore_pressure": True},
    "load_delete": lambda p: {"loads": "all"},
    "seismic_set": lambda p: {"enabled": True, "kh": 0.15, "kv": -0.05},
    "seismic_record_set": lambda p: {"name": "Pulse", "dt": 0.01,
                                     "accelerations": [0.0, 0.1, -0.2,
                                                       0.05, 0.0]},
    "seismic_record_delete": lambda p: {"record": "Rec"},
    "support_type_set": lambda p: {"type_class": "soil_nail",
                                   "name": "Nail",
                                   "params": {"tensile_capacity": 150.0}},
    "support_type_delete": lambda p: {"support_type": "Bolt"},
    "support_set": lambda p: {"support_type": "Bolt", "head": [40, 30],
                              "tail": [48, 26]},
    "support_pattern_add": lambda p: {"support_type": "Bolt",
                                      "start": [30, 25], "end": [50, 35],
                                      "length": 6.0, "spacing": 3.0},
    "support_delete": lambda p: {"supports": "all"},
    "support_ungroup": lambda p: {},
    "tension_crack_set": lambda p: {"mode": "percent_filled",
                                    "percent_filled": 50.0},
    "focus_set": lambda p: {"kind": "point", "points_xy": [[40, 30]],
                            "tolerance": 0.5},
    "focus_delete": lambda p: {"focus": "all"},
    "user_surface_add": lambda p: {"surface": {"type": "circle",
                                               "centre_x": 45,
                                               "centre_y": 45,
                                               "radius": 20}},
    "user_surface_delete": lambda p: {"surface": "all"},
    "annotation_set": lambda p: {"kind": "text", "points_xy": [[30, 40]],
                                 "text": "Note"},
    "annotation_delete": lambda p: {"annotations": "all"},
    "annotation_to_boundary": lambda p: {
        "annotation": p.annotations.ordered()[0].id,
        "type": "water_table"},
    "external_reshape": lambda p: {"points_xy": [[50, 35], [60, 37],
                                                 [70, 35]]},
    "geometry_cleanup": lambda p: {"apply": True},
    # v0.1.198 — the face (30, 25) -> (50, 35) of the setup model, 26.6°.
    "slope_angle_change": lambda p: {"toe": [30, 25], "crest": [50, 35],
                                     "target_deg": 20.0},
    "dxf_import": lambda p: {},
    "properties_import": lambda p: {},
    # v0.1.200 (F3a): groundwater. The mesh and the conditions a step
    # needs are made by PREPARE; ``groundwater_run``'s step is the field
    # written back when its job ends.
    "hydraulic_set": lambda p: {"material": "Soil", "model": "gardner",
                                "properties": {"ks": 2e-6,
                                               "gardner_a": 0.5}},
    "mesh_generate": lambda p: {"target_elements": 120},
    "mesh_reset": lambda p: {},
    "seepage_bc_set": lambda p: {"bc_type": "total_head", "side": "left",
                                 "value": 24.0},
    "seepage_bc_clear": lambda p: {},
    "transient_set": lambda p: {"stages": [{"time": 10.0,
                                            "calculate_sf": True}]},
    "water_grid_set": lambda p: {"points": [[20, 20, 10.0],
                                            [70, 20, 5.0],
                                            [45, 35, 0.0]]},
    "water_grid_delete": lambda p: {},
    "groundwater_run": lambda p: {"wait_seconds": 120},
}


def _prep_load(ws, pid, tmp):
    from ogr_api import call
    call(ws, "load_set", project_id=pid, kind="line", point_xy=[60, 35],
         magnitude=10.0)


def _prep_record(ws, pid, tmp):
    from ogr_api import call
    call(ws, "seismic_record_set", project_id=pid, name="Rec", dt=0.02,
         accelerations=[0.0, 0.3, 0.0])


def _prep_type(ws, pid, tmp):
    from ogr_api import call
    call(ws, "support_type_set", project_id=pid, type_class="end_anchored",
         name="Bolt")


def _prep_support(ws, pid, tmp):
    from ogr_api import call
    _prep_type(ws, pid, tmp)
    call(ws, "support_set", project_id=pid, support_type="Bolt",
         head=[40, 30], tail=[48, 26])


def _prep_pattern(ws, pid, tmp):
    from ogr_api import call
    _prep_type(ws, pid, tmp)
    call(ws, "support_pattern_add", project_id=pid, support_type="Bolt",
         start=[30, 25], end=[50, 35], length=6.0, spacing=3.0)


def _prep_crack(ws, pid, tmp):
    from ogr_api import call
    call(ws, "boundary_add", project_id=pid, type="tension_crack",
         points=[[50, 32], [70, 32]])


def _prep_focus(ws, pid, tmp):
    from ogr_api import call
    call(ws, "focus_set", project_id=pid, kind="line",
         points_xy=[[35, 27], [45, 32]])


def _prep_surface(ws, pid, tmp):
    from ogr_api import call
    call(ws, "user_surface_add", project_id=pid,
         surface={"type": "circle", "centre_x": 45, "centre_y": 45,
                  "radius": 20})


def _prep_annotation(ws, pid, tmp):
    from ogr_api import call
    call(ws, "annotation_set", project_id=pid, kind="line",
         points_xy=[[20, 23], [70, 23]])


def _prep_duplicate(ws, pid, tmp):
    # A repeated vertex, put straight into the model: the cleanup must
    # have something to remove, or it is (rightly) not a step.
    import copy
    ext = ws.get(pid).project.external_boundary()
    ext.polyline.vertices.insert(1, copy.copy(ext.polyline.vertices[1]))


def _prep_dxf(ws, pid, tmp):
    from ogr_api import call
    path = str(tmp / "model.dxf")
    call(ws, "dxf_export", project_id=pid, path=path)
    return {"path": path}


def _prep_ogr(ws, pid, tmp):
    from ogr_api import call
    other = call(ws, "project_new", name="Source")["project_id"]
    call(ws, "material_set", project_id=other, name="Imported",
         strength=_SOIL, properties={"unit_weight": 16.0})
    path = str(tmp / "source.ogr")
    call(ws, "project_save", project_id=other, path=path)
    return {"path": path}


def _prep_mesh(ws, pid, tmp):
    from ogr_api import call
    call(ws, "mesh_generate", project_id=pid, target_elements=120)


def _prep_conditions(ws, pid, tmp):
    from ogr_api import call
    call(ws, "hydraulic_set", project_id=pid, material="Soil",
         properties={"ks": 1e-6})
    call(ws, "hydraulic_set", project_id=pid, material="Base",
         properties={"ks": 1e-6})
    _prep_mesh(ws, pid, tmp)
    for side, level in (("left", 24.0), ("right", 33.0)):
        call(ws, "seepage_bc_set", project_id=pid, bc_type="total_head",
             side=side, value=level)


def _prep_grid(ws, pid, tmp):
    from ogr_api import call
    call(ws, "water_grid_set", project_id=pid,
         points=[[20, 20, 10.0], [70, 20, 5.0], [45, 35, 0.0]])


#: operation -> function(ws, project_id, tmp_dir) run BEFORE the measured
#: step; it may return extra keyword arguments (a file path).
PREPARE = {
    "mesh_reset": _prep_mesh,
    "seepage_bc_set": _prep_mesh,
    "seepage_bc_clear": _prep_conditions,
    "water_grid_delete": _prep_grid,
    "groundwater_run": _prep_conditions,
    "load_delete": _prep_load,
    "seismic_record_delete": _prep_record,
    "support_type_delete": _prep_type,
    "support_set": _prep_type,
    "support_pattern_add": _prep_type,
    "support_delete": _prep_support,
    "support_ungroup": _prep_pattern,
    "tension_crack_set": _prep_crack,
    "focus_delete": _prep_focus,
    "user_surface_delete": _prep_surface,
    "annotation_delete": _prep_annotation,
    "annotation_to_boundary": _prep_annotation,
    "geometry_cleanup": _prep_duplicate,
    "dxf_import": _prep_dxf,
    "properties_import": _prep_ogr,
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
        import shutil
        import tempfile
        from pathlib import Path

        from ogr_api import call
        for name, make in EXAMPLES.items():
            ws, pid = _setup()
            tmp = Path(tempfile.mkdtemp(prefix="ogr_undo_"))
            try:
                handle = ws.get(pid)
                obj = handle.project
                extra = (PREPARE[name](ws, pid, tmp) or {}) \
                    if name in PREPARE else {}
                steps = len(handle.stack.history()[0])
                before = _state(ws, pid)
                out = call(ws, name, project_id=pid, **make(obj), **extra)
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
                shutil.rmtree(tmp, ignore_errors=True)

    def test_preparations_name_real_examples(self):
        stray = set(PREPARE) - set(EXAMPLES)
        assert not stray, f"PREPARE without an example: {sorted(stray)}"


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

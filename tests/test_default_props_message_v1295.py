# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.295 (D303) — the groundwater message names, as computed with the
default hydraulic properties, only the materials that elements of the mesh
use.

The defect: ``_compute_groundwater`` called ``missing`` every material
without hydraulic properties, used or not. With «Upper» and «Lower»
assigned and with properties, and «Spare» unassigned and without, the run
ended with «… (default properties used for: Spare)», and no element used
«Spare» (the second GUI test, H4). Nothing in the computation changed; the
message sent the user to look where there was nothing.

What these tests protect, through the window's own compute:

* a material without properties that no element uses is not named;
* a material without properties that elements use is.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

_SOIL = {"model": "mohr_coulomb", "params": {"cohesion": 5.0, "friction_angle": 30.0}}


def _run(lower_has_properties):
    """The model of the GUI test: Upper and Lower assigned, Spare not; the
    window computes it; returns its status message."""
    from ogr_api import Workspace, call
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    ws = Workspace()
    w = None
    try:
        pid = call(ws, "project_new", name="d303")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[0, 0], [40, 0], [40, 10], [0, 10]],
            "material_boundaries": [[[0, 5], [40, 5]]],
            "materials": [{"name": n, "unit_weight": 20, "strength": _SOIL}
                          for n in ("Upper", "Lower", "Spare")]})
        call(ws, "material_assign", project_id=pid, material="Upper", x=20, y=7.5)
        call(ws, "material_assign", project_id=pid, material="Lower", x=20, y=2.5)
        call(ws, "settings_set", project_id=pid,
             changes={"groundwater.method": "fea_steady"})
        call(ws, "hydraulic_set", project_id=pid, material="Upper",
             model="constant", properties={"ks": 1e-6})
        if lower_has_properties:
            call(ws, "hydraulic_set", project_id=pid, material="Lower",
                 model="constant", properties={"ks": 1e-5})
        call(ws, "mesh_generate", project_id=pid, target_elements=200)
        call(ws, "seepage_bc_set", project_id=pid, side="left",
             bc_type="total_head", value=9.0)
        call(ws, "seepage_bc_set", project_id=pid, side="right",
             bc_type="total_head", value=4.0)
        w = MainWindow()
        w._attach_project(ws.get(pid).project)
        w._compute_groundwater()
        return w.statusBar().currentMessage()
    finally:
        if w is not None:
            w.close()
        ws.shutdown()


class TestTheMessage:
    def test_an_unused_material_is_not_named(self):
        msg = _run(lower_has_properties=True)
        assert msg.startswith("Groundwater solved"), msg
        assert "Spare" not in msg, msg
        assert "default properties" not in msg, msg

    def test_a_used_material_without_properties_is_named(self):
        msg = _run(lower_has_properties=False)
        assert "default properties used for: Lower" in msg, msg
        assert "Spare" not in msg, msg

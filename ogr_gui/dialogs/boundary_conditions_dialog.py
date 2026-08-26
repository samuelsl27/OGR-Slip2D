# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Set Boundary Conditions dialog — Phase 5 of the groundwater plan.

Reproduces the reference dialog's behaviour:

* a **Value** field that is only enabled for Total Head, Nodal Flow Rate
  and Infiltration (the other types take no value);
* a **Seepage Face** checkbox only available for Nodal Flow Rate and
  Infiltration;
* a **Pick by** selector (segments / nodes), with **Infiltration
  restricted to segments** — it cannot be applied to individual nodes;
* assignment by boundary side rather than by mouse picking, which keeps
  this first iteration usable without a full interactive picking mode on
  the canvas (that belongs with the mesh-editing tools);
* v0.1.125 — and, above the four sides, **a reservoir**. Four whole sides
  cannot say where a body of water is: putting "total head = 24" on the
  ground surface puts it on the crest of the dam and down the far face as
  well, so a model with water on one side only was not expressible at
  all. A reservoir is one number and a side, and the wetted perimeter
  follows from the geometry (``ogr_fem2d.solvers.bc_targets``). A
  drawdown is the same target with a lower level.

The dialog edits a :class:`SeepageBoundaryConditions` in place and is
only reachable when a mesh exists — the reference disables the option
otherwise, and so does the main window.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from ogr_fem2d.solvers import (
    BCType,
    SIDE_LEFT,
    SIDE_RIGHT,
    SeepageBoundaryConditions,
    wetted_nodes,
)
from ogr_gui.i18n import tr  # noqa: E402

_BC_LABELS = [
    (BCType.TOTAL_HEAD, "Total Head"),
    (BCType.PRESSURE_HEAD, "Pressure Head"),
    (BCType.ZERO_PRESSURE, "Zero Pressure"),
    (BCType.NODAL_FLOW, "Nodal Flow Rate"),
    (BCType.INFILTRATION, "Infiltration"),
    (BCType.UNKNOWN, "Unknown (P=0 or Q=0)"),
]

_NEEDS_VALUE = {BCType.TOTAL_HEAD, BCType.PRESSURE_HEAD,
                BCType.NODAL_FLOW, BCType.INFILTRATION}
_ALLOWS_SEEPAGE_FACE = {BCType.NODAL_FLOW, BCType.INFILTRATION}


def boundary_sides(mesh) -> dict:
    """Classify boundary nodes into named sides so conditions can be
    assigned without interactive picking: left, right, bottom and the
    ground surface (everything else, which includes the slope face)."""
    out = {"Left edge": [], "Right edge": [], "Bottom edge": [],
           "Ground surface": []}
    bnd = sorted(mesh.boundary_node_ids())
    if not bnd:
        return out
    xs = [mesh.nodes[i].x for i in bnd]
    ys = [mesh.nodes[i].y for i in bnd]
    x_min, x_max, y_min = min(xs), max(xs), min(ys)
    tol = max(1e-6, 1e-4 * max(x_max - x_min, 1.0))
    for nid in bnd:
        nd = mesh.nodes[nid]
        if abs(nd.x - x_min) <= tol:
            out["Left edge"].append(nid)
        elif abs(nd.x - x_max) <= tol:
            out["Right edge"].append(nid)
        elif abs(nd.y - y_min) <= tol:
            out["Bottom edge"].append(nid)
        else:
            out["Ground surface"].append(nid)
    return out


class BoundaryConditionsDialog(QDialog):
    """Assign seepage boundary conditions to the mesh boundary."""

    def __init__(self, mesh, bcs: SeepageBoundaryConditions, parent=None):
        super().__init__(parent)
        self.mesh = mesh
        self.bcs = bcs
        self.sides = boundary_sides(mesh)
        self.setWindowTitle(tr("Set Boundary Conditions"))
        self.resize(560, 460)

        v = QVBoxLayout(self)

        gb = QGroupBox(tr("Boundary condition"))
        f = QFormLayout(gb)
        self.cbo_type = QComboBox()
        for t, label in _BC_LABELS:
            self.cbo_type.addItem(label, t)
        self.cbo_type.currentIndexChanged.connect(self._on_type_changed)
        f.addRow(tr("Type:"), self.cbo_type)

        self.sp_value = QDoubleSpinBox()
        self.sp_value.setDecimals(6)
        self.sp_value.setRange(-1e9, 1e9)
        f.addRow(tr("Value:"), self.sp_value)

        self.chk_seepage = QCheckBox(tr("Seepage face"))
        f.addRow("", self.chk_seepage)

        self.cbo_pick = QComboBox()
        self.cbo_pick.addItem("Line segments", "segments")
        self.cbo_pick.addItem("Nodes", "nodes")
        f.addRow(tr("Pick by:"), self.cbo_pick)
        v.addWidget(gb)

        v.addWidget(QLabel(tr("Apply to:")))
        self.list_sides = QListWidget()
        for name, ids in self.sides.items():
            it = QListWidgetItem(f"{name}  ({len(ids)} nodes)")
            it.setData(32, name)
            self.list_sides.addItem(it)
        # The reservoir targets. They are Total Head by construction — a
        # water level IS a prescribed total head — so choosing one sets
        # the type, rather than letting the two disagree.
        for label, side in ((tr("Reservoir on the left, at Value"),
                             SIDE_LEFT),
                            (tr("Reservoir on the right, at Value"),
                             SIDE_RIGHT)):
            it = QListWidgetItem(label)
            it.setData(32, "reservoir:" + side)
            self.list_sides.addItem(it)
        v.addWidget(self.list_sides, 1)

        row = QHBoxLayout()
        btn_apply = QPushButton(tr("Assign"))
        btn_apply.clicked.connect(self._assign)
        row.addWidget(btn_apply)
        btn_defaults = QPushButton(tr("Restore defaults"))
        btn_defaults.clicked.connect(self._defaults)
        row.addWidget(btn_defaults)
        row.addStretch(1)
        v.addLayout(row)

        self.lbl_summary = QLabel("")
        v.addWidget(self.lbl_summary)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

        self._on_type_changed(0)
        self._refresh_summary()

    # ------------------------------------------------------------------
    def _on_type_changed(self, _idx: int) -> None:
        t = self.cbo_type.currentData()
        self.sp_value.setEnabled(t in _NEEDS_VALUE)
        self.chk_seepage.setEnabled(t in _ALLOWS_SEEPAGE_FACE)
        if t not in _ALLOWS_SEEPAGE_FACE:
            self.chk_seepage.setChecked(False)
        # Infiltration can only be applied to segments, never to nodes
        if t == BCType.INFILTRATION:
            self.cbo_pick.setCurrentIndex(0)
            self.cbo_pick.setEnabled(False)
        else:
            self.cbo_pick.setEnabled(True)

    # ------------------------------------------------------------------
    def _assign(self) -> None:
        item = self.list_sides.currentItem()
        if item is None:
            self.lbl_summary.setText(
                tr("Select a boundary to assign to."))
            return
        name = item.data(32)
        if str(name).startswith("reservoir:"):
            self._assign_reservoir(str(name).split(":", 1)[1])
            return
        ids = self.sides.get(name, [])
        if not ids:
            return
        t = self.cbo_type.currentData()
        value = self.sp_value.value() if t in _NEEDS_VALUE else 0.0
        if t == BCType.INFILTRATION:
            # Distributed flux: assign to consecutive boundary segments
            ordered = sorted(ids, key=lambda i: (self.mesh.nodes[i].x,
                                                 self.mesh.nodes[i].y))
            edges = set()
            for u, w in self.mesh.boundary_edges():
                if u in ids and w in ids:
                    edges.add((u, w))
            if not edges:
                for a, b in zip(ordered[:-1], ordered[1:]):
                    edges.add((a, b))
            for a, b in edges:
                self.bcs.add_segment(a, b, value,
                                     self.chk_seepage.isChecked())
        else:
            for nid in ids:
                self.bcs.add_node(nid, t, value,
                                  self.chk_seepage.isChecked())
        self._refresh_summary()

    def _assign_reservoir(self, side: str) -> None:
        """Prescribe a body of water standing at *Value* on one side.

        Reports how many nodes it reached. A reservoir that touched two
        nodes because the level was set below the toe is the mistake this
        number exists to make visible; the dialog cannot know the right
        answer, but it can refuse to be quiet about a suspicious one.
        """
        level = self.sp_value.value()
        ids = wetted_nodes(self.mesh, level, side)
        if not ids:
            self.lbl_summary.setText(tr(
                "No boundary node is below that level on that side: "
                "nothing was assigned."))
            return
        for nid in ids:
            self.bcs.add_node(nid, BCType.TOTAL_HEAD, float(level))
        self.cbo_type.setCurrentIndex(0)     # Total Head, to match
        self._refresh_summary()
        self.lbl_summary.setText(
            tr("Reservoir at %.3f: %d node(s) submerged.  ")
            % (level, len(ids)) + self.lbl_summary.text())

    def _defaults(self) -> None:
        from ogr_fem2d.solvers import default_boundary_conditions
        fresh = default_boundary_conditions(self.mesh)
        self.bcs.nodes = list(fresh.nodes)
        self.bcs.segments = []
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        counts: dict[str, int] = {}
        for b in self.bcs.nodes:
            counts[b.bc_type.value] = counts.get(b.bc_type.value, 0) + 1
        parts = [f"{k}: {v}" for k, v in sorted(counts.items())]
        if self.bcs.segments:
            parts.append(f"infiltration segments: {len(self.bcs.segments)}")
        self.lbl_summary.setText("  |  ".join(parts) or "no conditions")

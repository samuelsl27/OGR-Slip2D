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
    apply_reservoir,
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


#: The core's sides under the names this dialog shows.
_SIDE_NAMES = {"left": "Left edge", "right": "Right edge",
               "bottom": "Bottom edge", "ground": "Ground surface"}


def boundary_sides(mesh) -> dict:
    """Boundary nodes by side, under the dialog's names.

    v0.1.200 — the classification moved to
    ``ogr_fem2d.solvers.bc_targets.boundary_sides``, which an agent uses
    too; this only renames its keys.
    """
    from ogr_fem2d.solvers.bc_targets import boundary_sides as _core
    return {_SIDE_NAMES[k]: v for k, v in _core(mesh).items()}


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
        # v0.1.200 — the core's rules (``bc_targets``), which an agent's
        # conditions are checked against too.
        from ogr_fem2d.solvers.bc_targets import (allows_seepage_face,
                                                  needs_value)
        self.sp_value.setEnabled(needs_value(t))
        self.chk_seepage.setEnabled(allows_seepage_face(t))
        if not allows_seepage_face(t):
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
        # v0.1.200 — ``bc_targets.assign_to_nodes``, the core's assignment
        # (an agent uses it too). It also REPLACES infiltration already on
        # an edge: assigning twice here used to double the flux.
        from ogr_fem2d.solvers.bc_targets import assign_to_nodes
        assign_to_nodes(self.bcs, self.mesh, ids, t, self.sp_value.value(),
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
        if not wetted_nodes(self.mesh, level, side):
            self.lbl_summary.setText(tr(
                "No boundary node is below that level on that side: "
                "nothing was assigned."))
            return
        # v0.1.200 — the core's ``apply_reservoir``, the one an agent's
        # reservoir goes through (same nodes, same condition).
        ids = apply_reservoir(self.bcs, self.mesh, level, side)
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

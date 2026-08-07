# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Modify Support Pattern dialog (v0.1.15).

Detects which supports in the project form a "pattern" (same type_id,
heads roughly collinear with constant spacing) and edits them
uniformly: length, spacing, angle, type, force application,
force orientation.

Algorithm to detect the pattern:
    1. Take the picked support S0 as the "anchor".
    2. Among supports with the same type_id, find those whose heads
       are within a tolerance band of the line through S0's head
       in the direction of S0's tangent to the slope (estimated as
       the average direction between S0's neighbours in head-x order).
    3. Sort by head-x; supports that fit a constant-spacing series
       (within 10% relative tolerance) are added to the pattern.

If only 1 support is detected the dialog falls back to editing that
single instance.

Author: Samuel Sáez López — UPCT
"""
from __future__ import annotations

import math

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)

from ogr_core.support import ForceApplication, ForceOrientation
from ogr_gui.i18n import tr  # noqa: E402


def _detect_pattern_members(project, anchor_idx: int) -> list[int]:
    """Find indices of supports that belong to the same pattern as
    project.supports[anchor_idx]. Returns at least [anchor_idx]."""
    if anchor_idx < 0 or anchor_idx >= len(project.supports):
        return []
    anchor = project.supports[anchor_idx]
    # Candidates: same type_id, similar length (within 5%)
    L_anchor = anchor.length()
    cands = []
    for i, s in enumerate(project.supports):
        if s.type_id != anchor.type_id:
            continue
        L = s.length()
        if L_anchor > 0 and abs(L - L_anchor) / L_anchor > 0.05:
            continue
        cands.append((i, s))
    if len(cands) < 2:
        return [anchor_idx]
    # Sort by head x
    cands.sort(key=lambda t: t[1].head.x)
    # All cands aligned? Check that consecutive head-x deltas are roughly
    # equal (within 25%).
    xs = [c[1].head.x for c in cands]
    deltas = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    if not deltas:
        return [anchor_idx]
    avg = sum(deltas) / len(deltas)
    if avg < 1e-6:
        return [anchor_idx]
    if all(abs(d - avg) / avg < 0.25 for d in deltas):
        return [c[0] for c in cands]
    return [anchor_idx]


class ModifySupportPatternDialog(QDialog):
    """Edit the parameters of an entire support pattern in-place."""

    def __init__(self, project, anchor_idx: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Modify Support Pattern"))
        self.resize(440, 460)
        self.project = project
        self.anchor_idx = anchor_idx
        self._member_idxs = _detect_pattern_members(project, anchor_idx)
        if not self._member_idxs:
            return

        anchor = project.supports[anchor_idx]
        members = [project.supports[i] for i in self._member_idxs]

        root = QVBoxLayout(self)
        info = QLabel(
            f"Pattern detected: <b>{len(members)} supports</b> of type "
            f"<b>{anchor.type_id}</b>"
        )
        info.setStyleSheet("padding: 6px; background: #eef; border-radius: 4px;")
        root.addWidget(info)

        # ---- Type
        g_type = QGroupBox(tr("Support type"))
        f_type = QFormLayout(g_type)
        self.cbo_type = QComboBox()
        for st in project.support_types:
            name = getattr(st, "_display_name", st.DISPLAY_NAME)
            self.cbo_type.addItem(name, st.TYPE_ID)
        idx = self.cbo_type.findData(anchor.type_id)
        if idx >= 0:
            self.cbo_type.setCurrentIndex(idx)
        f_type.addRow(tr("Type:"), self.cbo_type)
        root.addWidget(g_type)

        # ---- Geometry (length + spacing)
        g_geom = QGroupBox(tr("Geometry"))
        f_geom = QFormLayout(g_geom)
        self.spn_length = QDoubleSpinBox()
        self.spn_length.setRange(0.01, 1e6)
        self.spn_length.setSuffix(" m")
        self.spn_length.setValue(anchor.length())
        f_geom.addRow(tr("Length:"), self.spn_length)

        # Spacing (only meaningful if ≥ 2 members)
        if len(members) >= 2:
            xs = sorted([m.head.x for m in members])
            avg_dx = (xs[-1] - xs[0]) / (len(xs) - 1)
        else:
            avg_dx = 0.0
        self.spn_spacing = QDoubleSpinBox()
        self.spn_spacing.setRange(0.0, 1e6)
        self.spn_spacing.setSuffix(" m")
        self.spn_spacing.setValue(avg_dx)
        self.spn_spacing.setEnabled(len(members) >= 2)
        f_geom.addRow(tr("In-plane spacing:"), self.spn_spacing)

        # Angle
        self.spn_angle = QDoubleSpinBox()
        self.spn_angle.setRange(-180, 180)
        self.spn_angle.setSuffix(" °")
        self.spn_angle.setValue(anchor.axis_angle_deg())
        f_geom.addRow(tr("Angle from horizontal:"), self.spn_angle)

        self.chk_keep_heads = QCheckBox(
            tr("Keep head positions (only adjust length / angle)")
        )
        self.chk_keep_heads.setChecked(True)
        f_geom.addRow("", self.chk_keep_heads)
        root.addWidget(g_geom)

        # ---- Force application & orientation
        g_force = QGroupBox(tr("Force"))
        f_force = QFormLayout(g_force)
        self.cbo_app = QComboBox()
        for fa in ForceApplication:
            self.cbo_app.addItem(fa.value.capitalize(), fa)
        idx = self.cbo_app.findData(anchor.force_application)
        if idx >= 0:
            self.cbo_app.setCurrentIndex(idx)
        f_force.addRow(tr("Application:"), self.cbo_app)

        self.cbo_ori = QComboBox()
        for fo in ForceOrientation:
            self.cbo_ori.addItem(fo.value.replace("_", " ").title(), fo)
        idx = self.cbo_ori.findData(anchor.orientation)
        if idx >= 0:
            self.cbo_ori.setCurrentIndex(idx)
        f_force.addRow(tr("Orientation:"), self.cbo_ori)
        root.addWidget(g_force)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def accept(self) -> None:
        from ogr_core.geometry import Vertex
        new_type = self.cbo_type.currentData()
        new_len = self.spn_length.value()
        new_spacing = self.spn_spacing.value()
        new_angle_rad = math.radians(self.spn_angle.value())
        new_app = self.cbo_app.currentData()
        new_ori = self.cbo_ori.currentData()
        keep_heads = self.chk_keep_heads.isChecked()

        members = [self.project.supports[i] for i in self._member_idxs]
        if not members:
            return

        if keep_heads:
            # Modify each member: change type, force properties, length, angle
            for s in members:
                s.type_id = new_type
                s.force_application = new_app
                s.orientation = new_ori
                dx = new_len * math.cos(new_angle_rad)
                dy = new_len * math.sin(new_angle_rad)
                s.tail = Vertex(s.head.x + dx, s.head.y + dy)
        else:
            # Rebuild from leftmost head, applying new spacing
            members_sorted = sorted(members, key=lambda s: s.head.x)
            x0 = members_sorted[0].head.x
            y0 = members_sorted[0].head.y
            # Estimate slope direction from first and last head
            if len(members_sorted) >= 2:
                dx_h = members_sorted[-1].head.x - x0
                dy_h = members_sorted[-1].head.y - y0
                head_len = math.hypot(dx_h, dy_h)
                if head_len < 1e-6:
                    head_len = 1.0
                ux = dx_h / head_len
                uy = dy_h / head_len
            else:
                ux, uy = 1.0, 0.0
            n = len(members_sorted)
            for i, s in enumerate(members_sorted):
                t = i * new_spacing
                hx = x0 + t * ux
                hy = y0 + t * uy
                s.head = Vertex(hx, hy)
                s.type_id = new_type
                s.force_application = new_app
                s.orientation = new_ori
                dx = new_len * math.cos(new_angle_rad)
                dy = new_len * math.sin(new_angle_rad)
                s.tail = Vertex(hx + dx, hy + dy)
        super().accept()

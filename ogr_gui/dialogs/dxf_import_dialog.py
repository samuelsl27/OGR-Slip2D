# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
DXF import dialog — Phase D2.

Presents every layer found in the drawing with a dropdown so the user can
say what it represents, whether or not the name matched anything: a layer
called ``0`` must be mappable just like ``OGR_EXTERNAL``.

The design points that matter:

* **Tolerances are relative** to the model diagonal and expressed as a
  percentage, with the recommended range shown next to the field, because
  the same absolute tolerance behaves completely differently on a drawing
  in millimetres and one in metres.
* **Preview before committing.** The preview runs the real pipeline and
  reports the vertex count before and after simplification, the number of
  regions found, and — the decisive indicator — whether the region areas
  add up to the external boundary. If they do not, some region did not
  close and the user should adjust the welding tolerance before importing.
* **Import is never blocked.** Problems are listed, with coordinates, so
  they can be corrected in the editor afterwards; refusing to import would
  leave the user with nothing to correct.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import Qt
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
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ogr_core.dxf import (
    DEFAULT_SIMPLIFY_PCT,
    DEFAULT_WELD_PCT,
    WELD_PCT_RANGE,
    DxfEntityKind as K,
    ImportOptions,
    UNIT_FACTORS,
    preview,
    read_dxf,
)
from ogr_gui.i18n import tr

_KIND_LABELS = [
    (K.IGNORE, "(ignore)"),
    (K.EXTERNAL, "External Boundary"),
    (K.MATERIAL, "Material Boundary"),
    (K.WATER_TABLE, "Water Table"),
    (K.PIEZO, "Piezometric Line"),
    (K.DRAWDOWN, "Drawdown Line"),
    (K.TENSION_CRACK, "Tension Crack"),
    (K.SUPPORT, "Support"),
]


class DxfImportDialog(QDialog):
    """Map DXF layers to geometry and import."""

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = str(path)
        self.result_preview = None
        self.options = ImportOptions()
        self.setWindowTitle(tr("Import DXF"))
        self.resize(900, 640)

        root = QVBoxLayout(self)

        # ---- units and curve density --------------------------------
        gb_read = QGroupBox(tr("Reading"))
        f = QFormLayout(gb_read)
        self.cbo_unit = QComboBox()
        for name in ("m", "cm", "mm", "km", "ft", "in"):
            self.cbo_unit.addItem(name, name)
        f.addRow(tr("Drawing units:"), self.cbo_unit)
        self.lbl_suggest = QLabel("")
        f.addRow("", self.lbl_suggest)
        self.sp_segments = QSpinBox()
        self.sp_segments.setRange(4, 720)
        self.sp_segments.setValue(64)
        self.sp_segments.setToolTip(tr(
            "Segments per full circle used to discretise arcs, circles, "
            "splines and polyline bulges. An arc receives its "
            "proportional share."))
        f.addRow(tr("Curve discretisation:"), self.sp_segments)
        root.addWidget(gb_read)

        # ---- layer table --------------------------------------------
        root.addWidget(QLabel(tr("Layers found in the drawing:")))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            [tr("Layer"), tr("Entities"), tr("Vertices"),
             tr("Import as")])
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

        # ---- tolerances ---------------------------------------------
        gb_tol = QGroupBox(tr("Geometry repair"))
        ft = QFormLayout(gb_tol)
        lo, hi = WELD_PCT_RANGE
        self.sp_weld = QDoubleSpinBox()
        self.sp_weld.setDecimals(4)
        self.sp_weld.setRange(0.0, 5.0)
        self.sp_weld.setSingleStep(0.01)
        self.sp_weld.setValue(DEFAULT_WELD_PCT)
        self.sp_weld.setSuffix(" %")
        self.sp_weld.setToolTip(tr(
            "Endpoints closer than this are welded together and a node is "
            "inserted where one lands on the interior of a segment. "
            "Measured as a percentage of the model diagonal, so the same "
            "value works whatever the drawing units."))
        ft.addRow(tr("Welding tolerance:"), self.sp_weld)
        ft.addRow("", QLabel(tr("Recommended: %.3f – %.3f %% of the "
                                "model diagonal") % (lo, hi)))
        self.chk_simplify = QCheckBox(tr("Simplify polylines"))
        self.chk_simplify.setChecked(True)
        self.chk_simplify.toggled.connect(self._on_simplify_toggled)
        ft.addRow("", self.chk_simplify)
        self.sp_simplify = QDoubleSpinBox()
        self.sp_simplify.setDecimals(4)
        self.sp_simplify.setRange(0.0, 5.0)
        self.sp_simplify.setSingleStep(0.005)
        self.sp_simplify.setValue(DEFAULT_SIMPLIFY_PCT)
        self.sp_simplify.setSuffix(" %")
        self.sp_simplify.setToolTip(tr(
            "Douglas-Peucker tolerance, also as a percentage of the model "
            "diagonal. Vertices shared with another boundary are never "
            "removed."))
        ft.addRow(tr("Simplification tolerance:"), self.sp_simplify)
        self.chk_replace = QCheckBox(tr(
            "Replace existing boundaries of the imported types"))
        self.chk_replace.setChecked(True)
        ft.addRow("", self.chk_replace)
        root.addWidget(gb_tol)

        # ---- preview ------------------------------------------------
        row = QHBoxLayout()
        btn_prev = QPushButton(tr("Preview"))
        btn_prev.clicked.connect(self._preview)
        row.addWidget(btn_prev)
        self.lbl_preview = QLabel(tr("Press Preview to check the "
                                     "geometry before importing."))
        self.lbl_preview.setWordWrap(True)
        row.addWidget(self.lbl_preview, 1)
        root.addLayout(row)

        self.list_problems = QListWidget()
        self.list_problems.setMaximumHeight(110)
        root.addWidget(self.list_problems)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(tr("Import"))
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

        self._load_layers()
        self._on_simplify_toggled(True)

    # ==================================================================
    def _load_layers(self):
        """Read the drawing once to populate the table."""
        try:
            cat = read_dxf(self.path, unit="m",
                           segments_per_circle=self.sp_segments.value())
        except RuntimeError as exc:
            self.lbl_preview.setText(str(exc))
            return
        self.catalogue = cat
        suggested = cat.suggested_unit()
        i = self.cbo_unit.findData(suggested)
        if i >= 0:
            self.cbo_unit.setCurrentIndex(i)
        self.lbl_suggest.setText(tr(
            "The file suggests '%s'; it is only a hint and is often "
            "missing or wrong, so check it.") % suggested)

        self.table.setRowCount(0)
        for lay in cat.layers:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(lay.name))
            counts = ", ".join(f"{k}×{v}" for k, v in
                               sorted(lay.entity_counts.items()))
            self.table.setItem(r, 1, QTableWidgetItem(counts))
            self.table.setItem(r, 2,
                               QTableWidgetItem(str(lay.vertex_count)))
            cbo = QComboBox()
            for kind, label in _KIND_LABELS:
                cbo.addItem(tr(label), kind)
            j = cbo.findData(lay.proposed_kind)
            cbo.setCurrentIndex(max(0, j))
            self.table.setCellWidget(r, 3, cbo)
            # Highlight the rows the user must decide on
            if lay.proposed_kind == K.IGNORE:
                for c in range(3):
                    it = self.table.item(r, c)
                    if it is not None:
                        it.setForeground(Qt.darkGray)

    # ------------------------------------------------------------------
    def _on_simplify_toggled(self, on: bool):
        self.sp_simplify.setEnabled(bool(on))

    def _collect(self) -> ImportOptions:
        kinds = {}
        for r in range(self.table.rowCount()):
            name_item = self.table.item(r, 0)
            cbo = self.table.cellWidget(r, 3)
            if name_item is None or cbo is None:
                continue
            kinds[name_item.text()] = cbo.currentData()
        return ImportOptions(
            unit=self.cbo_unit.currentData(),
            segments_per_circle=self.sp_segments.value(),
            weld_pct=self.sp_weld.value(),
            simplify=self.chk_simplify.isChecked(),
            simplify_pct=self.sp_simplify.value(),
            replace_model=self.chk_replace.isChecked(),
            layer_kinds=kinds,
        )

    # ------------------------------------------------------------------
    def _preview(self):
        """Run the real pipeline and report what it produced."""
        opts = self._collect()
        pv = preview(self.path, opts)
        self.result_preview = pv
        self.list_problems.clear()
        if not pv.ok:
            self.lbl_preview.setText(pv.error or tr("Preview failed."))
            return

        rep = pv.report
        parts = [
            tr("Vertices: %d → %d") % (rep.vertices_before,
                                       rep.vertices_after),
            tr("welded: %d (%d nodes inserted)") % (rep.welded_endpoints,
                                                    rep.nodes_inserted),
            tr("crossings split: %d") % rep.crossings_split,
            tr("regions: %d") % pv.regions,
        ]
        if pv.external_area > 0:
            if pv.area_matches:
                parts.append(tr("region areas match the external "
                                "boundary — geometry closes"))
            else:
                parts.append(tr(
                    "REGION AREAS DO NOT MATCH (%.2f vs %.2f): some "
                    "region did not close. Try a larger welding "
                    "tolerance.") % (pv.region_area, pv.external_area))
        self.lbl_preview.setText("   |   ".join(parts))

        for p in rep.problems:
            where = ""
            if p.get("x") is not None:
                where = "  (%.2f, %.2f)" % (p["x"], p["y"])
            it = QListWidgetItem(f"[{p['kind']}] {p['message']}{where}")
            it.setData(Qt.UserRole, (p.get("x"), p.get("y")))
            self.list_problems.addItem(it)
        if not rep.problems:
            self.list_problems.addItem(
                QListWidgetItem(tr("No problems found.")))

    # ------------------------------------------------------------------
    def _accept(self):
        """Import always runs the pipeline once more, so what is applied
        matches the options as they stand at this moment even if the user
        changed them after previewing."""
        self.options = self._collect()
        self.result_preview = preview(self.path, self.options)
        self.accept()

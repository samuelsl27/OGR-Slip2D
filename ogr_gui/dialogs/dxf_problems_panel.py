# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
DXF import problem report — Phase D3.

An import that reports "3 problems found" and then closes has told the
user almost nothing: a gap of a few millimetres in a hundred-metre model
cannot be found by panning around. This panel makes each problem
*actionable*.

* Problems are grouped by kind and shown with a severity, because "the
  external boundary is missing" and "a material end does not reach
  anything" need very different responses.
* Selecting one **centres the canvas on it**; double-clicking zooms in
  closer still.
* Each kind carries a **suggested remedy** written for the situation,
  including which import setting to change and in which direction — the
  information the user would otherwise have to infer.
* The panel is non-modal and stays open while the model is edited, so
  problems can be worked through one by one and re-checked.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from ogr_gui.i18n import tr

# Severity and advice per problem kind. Keeping this here rather than in
# the sanitiser keeps engine and wording apart: the sanitiser records
# facts, the interface explains them.
_PROBLEM_INFO = {
    "external_missing": (
        "error",
        "No layer was mapped to the external boundary. Re-run the import "
        "and assign one in the layer table: without it the model cannot "
        "define regions at all."),
    "external_multiple": (
        "warning",
        "Several closed shapes were mapped to the external boundary. The "
        "largest was kept. If the wrong one was chosen, map the others to "
        "'Material Boundary' instead."),
    "external_gap": (
        "warning",
        "The external boundary arrived open and was closed with a "
        "straight segment. Check that the added segment follows the "
        "intended ground surface; if not, close the outline in the CAD "
        "drawing and import again."),
    "external": (
        "error",
        "The external boundary does not have enough vertices to enclose "
        "an area."),
    "dangling_end": (
        "warning",
        "A material boundary ends without touching anything, so its "
        "region will not close. Either extend it in the editor until it "
        "meets another boundary, or re-import with a larger welding "
        "tolerance."),
    "regions": (
        "error",
        "The regions could not be built from the imported geometry. This "
        "usually means boundaries cross without sharing a node; try a "
        "larger welding tolerance."),
    "empty": (
        "error",
        "No geometry was assigned to any layer."),
}

_SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}
_SEVERITY_LABEL = {"error": "Error", "warning": "Warning", "info": "Note"}


class DxfProblemsPanel(QDialog):
    """Non-modal list of unresolved import problems."""

    def __init__(self, preview, canvas=None, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.preview = preview
        self.setWindowTitle(tr("DXF Import — Problems"))
        self.setModal(False)
        self.resize(720, 420)

        v = QVBoxLayout(self)

        self.lbl_head = QLabel("")
        self.lbl_head.setWordWrap(True)
        v.addWidget(self.lbl_head)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("Problem"), tr("Location")])
        self.tree.setColumnWidth(0, 480)
        self.tree.currentItemChanged.connect(self._on_selected)
        self.tree.itemDoubleClicked.connect(self._on_double_clicked)
        v.addWidget(self.tree, 1)

        self.lbl_advice = QLabel("")
        self.lbl_advice.setWordWrap(True)
        self.lbl_advice.setMinimumHeight(56)
        v.addWidget(self.lbl_advice)

        row = QHBoxLayout()
        self.btn_zoom = QPushButton(tr("Go to problem"))
        self.btn_zoom.clicked.connect(self._go_to_current)
        row.addWidget(self.btn_zoom)
        btn_all = QPushButton(tr("Zoom all"))
        btn_all.clicked.connect(self._zoom_all)
        row.addWidget(btn_all)
        row.addStretch(1)
        v.addLayout(row)

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.close)
        v.addWidget(bb)

        self.populate(preview)

    # ==================================================================
    def populate(self, preview) -> None:
        """Fill the tree from an import preview."""
        self.preview = preview
        self.tree.clear()
        report = getattr(preview, "report", None)
        problems = list(getattr(report, "problems", []) or [])

        # The area mismatch is not recorded by the sanitiser (it only
        # emerges once regions are built), but it is the single most
        # important thing to tell the user, so it is injected here.
        if (preview is not None and getattr(preview, "external_area", 0)
                and not preview.area_matches):
            problems.insert(0, {
                "kind": "area_mismatch",
                "message": (
                    "The region areas (%.2f) do not add up to the "
                    "external boundary (%.2f): at least one region did "
                    "not close." % (preview.region_area,
                                    preview.external_area)),
                "x": None, "y": None})

        if not problems:
            self.lbl_head.setText(tr(
                "No problems: the imported geometry closes correctly."))
            self.lbl_advice.setText("")
            self.btn_zoom.setEnabled(False)
            return

        groups: dict = {}
        for p in problems:
            groups.setdefault(p["kind"], []).append(p)

        errors = sum(1 for p in problems
                     if self._severity(p["kind"]) == "error")
        self.lbl_head.setText(tr(
            "%d problem(s) found (%d error(s)). The geometry has been "
            "imported anyway: select a problem to locate it and correct "
            "it in the editor.") % (len(problems), errors))

        for kind in sorted(groups,
                           key=lambda k: (_SEVERITY_ORDER.get(
                               self._severity(k), 3), k)):
            items = groups[kind]
            sev = self._severity(kind)
            top = QTreeWidgetItem([
                tr("%s — %s (%d)") % (tr(_SEVERITY_LABEL[sev]),
                                      tr(self._title(kind)), len(items)),
                ""])
            top.setData(0, Qt.UserRole, ("kind", kind))
            if sev == "error":
                top.setForeground(0, Qt.red)
            self.tree.addTopLevelItem(top)
            for p in items:
                where = ""
                if p.get("x") is not None:
                    where = "%.3f, %.3f" % (p["x"], p["y"])
                child = QTreeWidgetItem([p["message"], where])
                child.setData(0, Qt.UserRole,
                              ("problem", p.get("x"), p.get("y"), kind))
                top.addChild(child)
            top.setExpanded(True)

        self.tree.setCurrentItem(self.tree.topLevelItem(0))

    # ------------------------------------------------------------------
    @staticmethod
    def _severity(kind: str) -> str:
        if kind == "area_mismatch":
            return "error"
        return _PROBLEM_INFO.get(kind, ("warning", ""))[0]

    @staticmethod
    def _title(kind: str) -> str:
        return kind.replace("_", " ").capitalize()

    @staticmethod
    def _advice(kind: str) -> str:
        if kind == "area_mismatch":
            return (
                "Increase the welding tolerance and import again. If the "
                "areas still disagree, look for a boundary that crosses "
                "another without sharing a node, or one that stops just "
                "short of the external boundary.")
        return _PROBLEM_INFO.get(kind, ("warning", ""))[1]

    # ------------------------------------------------------------------
    def _current_point(self):
        item = self.tree.currentItem()
        if item is None:
            return None
        data = item.data(0, Qt.UserRole)
        if not data or data[0] != "problem":
            return None
        x, y = data[1], data[2]
        if x is None or y is None:
            return None
        return float(x), float(y)

    def _on_selected(self, current, _previous=None) -> None:
        kind = None
        if current is not None:
            data = current.data(0, Qt.UserRole)
            if data:
                kind = data[1] if data[0] == "kind" else data[3]
        self.lbl_advice.setText(tr(self._advice(kind)) if kind else "")
        self.btn_zoom.setEnabled(self._current_point() is not None)
        # Selecting a located problem already centres the view, so
        # stepping through the list with the arrow keys walks the model.
        pt = self._current_point()
        if pt is not None:
            self._center(pt[0], pt[1])

    def _on_double_clicked(self, _item, _col) -> None:
        pt = self._current_point()
        if pt is not None:
            self._center(pt[0], pt[1], closer=True)

    def _go_to_current(self) -> None:
        pt = self._current_point()
        if pt is not None:
            self._center(pt[0], pt[1], closer=True)

    def _center(self, x: float, y: float, closer: bool = False) -> None:
        if self.canvas is None:
            return
        half = None
        if closer and getattr(self.canvas, "project", None) is not None:
            try:
                xmin, ymin, xmax, ymax = self.canvas.project.bounding_box()
                half = max(xmax - xmin, ymax - ymin, 1.0) * 0.01
            except Exception:  # noqa: BLE001
                half = None
        try:
            self.canvas.zoom_to_point(x, y, half)
        except Exception:  # noqa: BLE001
            pass

    def _zoom_all(self) -> None:
        if self.canvas is not None and hasattr(self.canvas, "zoom_all"):
            self.canvas.zoom_all()

    # ------------------------------------------------------------------
    def problem_count(self) -> int:
        n = 0
        for i in range(self.tree.topLevelItemCount()):
            n += self.tree.topLevelItem(i).childCount()
        return n

    def error_count(self) -> int:
        n = 0
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            data = top.data(0, Qt.UserRole)
            if data and data[0] == "kind" \
                    and self._severity(data[1]) == "error":
                n += top.childCount()
        return n

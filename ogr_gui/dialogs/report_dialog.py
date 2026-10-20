# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The options of the PDF report (v0.1.339, D336).

*Generate Report* asks these before the file name: whether the report
carries one figure per method, how the figures are framed and whether they
draw the annotation layer. The same three are the parameters of the
``report_generate`` operation, so a script and the window ask for the same
report.

An option that cannot change the report is greyed and says why (rule 7):
the search-area frame without a grid of slip centres, the annotations
without a visible one.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QRadioButton,
    QVBoxLayout,
)

from ogr_gui.i18n import tr


class ReportDialog(QDialog):
    """Choose the figures of the PDF report."""

    def __init__(self, project, results, parent=None):
        super().__init__(parent)
        from ogr_api.report_figures import has_centres
        from ogr_core.dxf.annotation_export import visible_annotations

        self.setWindowTitle(tr("Generate Report"))
        v = QVBoxLayout(self)

        self.chk_figures = QCheckBox(tr("Critical surface of each method"))
        self.chk_figures.setChecked(True)
        self.chk_figures.setToolTip(tr(
            "One figure per method: the model, that method's critical "
            "surface and, with a grid of slip centres, the contours of the "
            "minimum factor of safety at each centre."))
        v.addWidget(self.chk_figures)

        self.gb_framing = QGroupBox(tr("Framing"))
        fv = QVBoxLayout(self.gb_framing)
        self.rb_model = QRadioButton(tr("Model"))
        self.rb_search_area = QRadioButton(tr("Model and search area"))
        self.rb_search_area.setToolTip(tr(
            "The model and every slip centre the search evaluated, the same "
            "frame in every figure so that they compare."))
        self.rb_model.setChecked(True)
        self._framing = QButtonGroup(self)
        for rb in (self.rb_model, self.rb_search_area):
            self._framing.addButton(rb)
            fv.addWidget(rb)
        v.addWidget(self.gb_framing)

        self.chk_annotations = QCheckBox(tr("Annotations"))
        self.chk_annotations.setChecked(True)
        self.chk_annotations.setToolTip(tr(
            "The lines, texts, dimensions, axes and images drawn with the "
            "Tools menu."))
        v.addWidget(self.chk_annotations)

        # Availability reflects the run and the model, so nothing offered
        # leaves the report unchanged
        if not has_centres(results):
            self.rb_search_area.setEnabled(False)
            self.rb_search_area.setToolTip(tr(
                "No search of this run has a grid of slip centres."))
        self._has_annotations = bool(visible_annotations(project))
        if not self._has_annotations:
            self.chk_annotations.setEnabled(False)
            self.chk_annotations.setChecked(False)
            self.chk_annotations.setToolTip(tr(
                "The model has no visible annotation."))
        self.chk_figures.toggled.connect(self._figures_toggled)
        v.addStretch(1)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(tr("Generate"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _figures_toggled(self, on: bool) -> None:
        self.gb_framing.setEnabled(on)
        self.chk_annotations.setEnabled(on and self._has_annotations)

    @property
    def options(self) -> dict:
        """The keyword arguments of ``method_figures`` and of the
        ``report_generate`` operation."""
        return {
            "figures": self.chk_figures.isChecked(),
            "framing": ("search_area" if self.rb_search_area.isChecked()
                        else "model"),
            "annotations": (self.chk_annotations.isChecked()
                            and self.chk_annotations.isEnabled()),
        }

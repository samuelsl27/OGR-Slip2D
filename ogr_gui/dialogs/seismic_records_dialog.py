# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Seismic Records dialog (v0.1.127).

Defines and imports the acceleration-time histories a Newmark analysis
integrates. A record is a project-level object, like a material: it is
defined once and then chosen on the Seismic page of Project Settings.

The import reads plain text in the two layouts Jibson (1993) names —
pairs of time and acceleration, or one acceleration per line at a fixed
interval — and nothing else. A proprietary strong-motion format would be
a guess about a file this program has never seen.

Author: Samuel Sáez López (UPCT).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from ogr_core.loads.seismic_record import (
    AccelerationUnit,
    SeismicRecord,
    parse_record_text,
)
from ogr_gui.i18n import tr

_UNIT_CHOICES = (
    (AccelerationUnit.G, "g"),
    (AccelerationUnit.CM_S2, "cm/s²"),
    (AccelerationUnit.M_S2, "m/s²"),
)


class SeismicRecordsDialog(QDialog):
    """Manage the project's strong-motion records."""

    def __init__(self, project, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Seismic Records"))
        self.resize(560, 420)
        self.project = project
        # Edited on a copy of the list, so Cancel really cancels.
        self.records = [
            SeismicRecord.from_dict(r.to_dict())
            for r in getattr(project, "seismic_records", [])
        ]

        root = QVBoxLayout(self)
        root.addWidget(QLabel(tr(
            "Acceleration-time histories for Newmark displacement "
            "analysis.")))

        body = QHBoxLayout()
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._select)
        body.addWidget(self.list, 1)

        side = QVBoxLayout()
        self.btn_import = QPushButton(tr("Import from file..."))
        self.btn_import.clicked.connect(self._import)
        side.addWidget(self.btn_import)
        self.btn_delete = QPushButton(tr("Delete record"))
        self.btn_delete.clicked.connect(self._delete)
        side.addWidget(self.btn_delete)
        side.addStretch(1)
        body.addLayout(side)
        root.addLayout(body)

        form = QFormLayout()
        self.ed_name = QLineEdit()
        self.ed_name.textEdited.connect(self._rename)
        form.addRow(tr("Name:"), self.ed_name)

        self.sb_dt = QDoubleSpinBox()
        self.sb_dt.setDecimals(5)
        self.sb_dt.setRange(0.00001, 10.0)
        self.sb_dt.setSingleStep(0.005)
        self.sb_dt.setValue(0.02)
        self.sb_dt.valueChanged.connect(self._retime)
        form.addRow(tr("Time interval (s):"), self.sb_dt)

        self.cmb_unit = QComboBox()
        for _unit, label in _UNIT_CHOICES:
            self.cmb_unit.addItem(label)
        self.cmb_unit.setToolTip(tr(
            "Unit of the file being imported. Records are stored in g."))
        form.addRow(tr("File units:"), self.cmb_unit)

        self.lbl_summary = QLabel("")
        self.lbl_summary.setTextFormat(Qt.RichText)
        form.addRow(tr("Record:"), self.lbl_summary)
        root.addLayout(form)

        self.lbl_note = QLabel("")
        self.lbl_note.setWordWrap(True)
        root.addWidget(self.lbl_note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._reload()

    # ------------------------------------------------------------------
    def _current(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.records):
            return self.records[row]
        return None

    def _reload(self, row: int = 0) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for rec in self.records:
            self.list.addItem(rec.name)
        self.list.blockSignals(False)
        if self.records:
            self.list.setCurrentRow(max(0, min(row, len(self.records) - 1)))
        else:
            self._select(-1)

    def _select(self, row: int) -> None:
        rec = self.records[row] if 0 <= row < len(self.records) else None
        for widget in (self.ed_name, self.sb_dt, self.btn_delete):
            widget.setEnabled(rec is not None)
        if rec is None:
            self.ed_name.setText("")
            self.lbl_summary.setText(tr("No record defined."))
            return
        self.ed_name.setText(rec.name)
        self.sb_dt.blockSignals(True)
        self.sb_dt.setValue(rec.dt)
        self.sb_dt.blockSignals(False)
        # One format string and not three fragments glued together: a
        # sentence assembled from pieces cannot be reordered by a
        # translator, and the order of a Spanish sentence is not the
        # order of an English one.
        self.lbl_summary.setText(
            tr("%d samples, %.3f s, PGA %.4f g")
            % (len(rec.accelerations), rec.duration, rec.pga))

    def _rename(self, text: str) -> None:
        rec = self._current()
        if rec is None:
            return
        rec.name = text
        row = self.list.currentRow()
        item = self.list.item(row)
        if item is not None:
            item.setText(text)

    def _retime(self, value: float) -> None:
        """The interval is editable because a single-column file has none.

        Changing it does not resample anything: it restates what the
        samples already are, which is the only honest thing a program can
        do with a file that did not say.
        """
        rec = self._current()
        if rec is None:
            return
        rec.dt = float(value)
        self._select(self.list.currentRow())

    # ------------------------------------------------------------------
    def _import(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self, tr("Import Seismic Record"), "",
            tr("Text files (*.txt *.dat *.csv);;All files (*)"))
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            self.lbl_note.setText(tr("Could not read the file:") + f" {exc}")
            return
        unit = _UNIT_CHOICES[max(0, self.cmb_unit.currentIndex())][0]
        accel, dt, note = parse_record_text(text, unit,
                                            dt=self.sb_dt.value())
        if not accel:
            self.lbl_note.setText(tr("Nothing was imported:") + f" {note}")
            return
        import os
        rec = SeismicRecord(
            name=os.path.splitext(os.path.basename(path))[0],
            dt=dt, accelerations=accel, source_unit=unit,
            source_file=os.path.basename(path))
        self.records.append(rec)
        self.lbl_note.setText(note or "")
        self._reload(len(self.records) - 1)

    def _delete(self) -> None:
        row = self.list.currentRow()
        if 0 <= row < len(self.records):
            del self.records[row]
            self._reload(row)

    # ------------------------------------------------------------------
    def apply(self) -> None:
        """Write the edited list back into the project.

        A record that the Seismic page had selected and that is no longer
        here leaves the selection empty rather than pointing at nothing:
        the run then says it has no record instead of integrating one the
        user deleted.
        """
        self.project.seismic_records = list(self.records)
        settings = getattr(self.project.settings, "seismic", None)
        if settings is not None and settings.record_id:
            alive = {r.id for r in self.records}
            if settings.record_id not in alive:
                settings.record_id = ""

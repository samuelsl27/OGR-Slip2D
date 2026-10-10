# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Results dock — tabular view of the most critical slip surfaces.

A dockable QDockWidget listing the top-N failure surfaces by ascending
FoS. Double-clicking a row will (eventually) highlight that surface on
the canvas.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from ogr_gui.i18n import tr  # noqa: E402
from ogr_gui.reported_quantity import fos_label  # noqa: E402


def load_factor_lines(result) -> str:
    """How a design standard classed each load on ``result``'s surface, as
    lines to append to the header; empty without one (v0.1.243, D226b).

    Whether a load drives the sliding depends on the surface, so it is said
    for the critical one that is shown, not for the run."""
    factors = getattr(getattr(result, "slices", None), "load_factors", None)
    if not factors:
        return ""
    from html import escape
    lines = []
    for _load_id, (action, drives, factor, name) in factors.items():
        role = (tr("drives the sliding") if drives
                else tr("resists the sliding"))
        kind = (tr("permanent load") if action == "permanent"
                else tr("variable load"))
        lines.append(f"{escape(str(name))}: {kind}, {role}: × {factor:g}")
    return "<br>" + tr("Loads on this surface:") + "<br>" + "<br>".join(lines)


class ResultsDock(QDockWidget):
    """Dock widget that presents the Top-N critical surfaces of a search."""

    surface_selected = Signal(int)  # row index in the current SearchResult

    def __init__(self, parent=None) -> None:
        super().__init__("Results", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)

        self.header_label = QLabel(tr("No results yet."))
        self.header_label.setStyleSheet("font-weight: 500; padding: 2px;")
        layout.addWidget(self.header_label)

        # v0.1.297 (D304) — said when the model has changed since this
        # result was computed (the window compares the same fingerprint
        # the API marks a stale result with); hidden otherwise. Its own
        # colours, so it reads with either theme.
        self.stale_label = QLabel(tr(
            "Results of an earlier model: compute again."))
        self.stale_label.setWordWrap(True)
        self.stale_label.setStyleSheet(
            "color: #5a3b00; background: #fff1c2; padding: 3px; "
            "border-radius: 2px;")
        self.stale_label.setVisible(False)
        layout.addWidget(self.stale_label)
        self._stale = False

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["#", "FoS", "Method", "Centre X", "Centre Y", "Radius"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_selection)
        layout.addWidget(self.table)

        self.setWidget(container)

    # ------------------------------------------------------------------
    def set_stale(self, stale: bool) -> None:
        """Mark the result shown as computed on an earlier model, or not
        (v0.1.297, D304): the notice shows and the table greys out."""
        self._stale = bool(stale)
        self.stale_label.setVisible(self._stale)
        self.table.setEnabled(not self._stale)

    def is_stale(self) -> bool:
        return self._stale

    def show_result(self, search_result, factor_report=None) -> None:
        # a result just shown is of the model it was computed on
        self.set_stale(False)
        self.table.setRowCount(0)
        if search_result is None or not search_result.evaluations:
            self.header_label.setText(tr("No results yet."))
            return

        crit = search_result.critical
        if crit:
            # v0.1.84 — the same count the Interpret summary shows, and for
            # the same reason: a surface screened out by a post-analysis
            # check converged, so it is "valid", but it can never be the
            # critical factor of safety printed next to it.
            n_ok = getattr(search_result, "analysed_count",
                           search_result.valid_count)
            # v0.1.165 (D96) — this caption was hard-coded AND untranslated,
            # so the dock said "Critical FoS" in English while the status
            # bar three pixels below said "FS crítico", and both said it
            # over an over-design factor. One decider, and through tr().
            label = fos_label(factor_report)
            self.header_label.setText(
                f"Method: <b>{search_result.method_id}</b>   "
                f"Valid: {n_ok}   "
                f"{label}: <b>{crit.fos:.3f}</b>"
                + load_factor_lines(crit)
            )
        else:
            self.header_label.setText(
                f"Method: {search_result.method_id}. "
                f"No valid surfaces found ({search_result.invalid_count} invalid)."
            )

        for i, res in enumerate(search_result.top_n(50)):
            sd = res.surface.to_dict()
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(f"{res.fos:.4f}"))
            self.table.setItem(i, 2, QTableWidgetItem(res.method_id))
            self.table.setItem(i, 3, QTableWidgetItem(f"{sd.get('centre_x', float('nan')):.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{sd.get('centre_y', float('nan')):.2f}"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{sd.get('radius', float('nan')):.2f}"))

            if i == 0:
                # Highlight critical row
                for c in range(self.table.columnCount()):
                    item = self.table.item(i, c)
                    item.setBackground(Qt.yellow)
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)

    def _on_selection(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if rows:
            self.surface_selected.emit(rows[0].row())

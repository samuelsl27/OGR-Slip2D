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
from PySide6.QtGui import QColor
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
from ogr_gui.labels import circle_cells, method_name  # noqa: E402

#: The critical row: a fixed pair that reads in both themes (D319).
CRITICAL_ROW_BACKGROUND = "#fff1c2"
CRITICAL_ROW_INK = "#5a3b00"
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
    # v0.1.436 (D415) -- an unnamed load by the magnitude of the run that
    # factored it (the owner's decision, 2026-11-11), never by its id
    from ogr_gui.labels import load_name_label
    lines = []
    for _load_id, (action, drives, factor, name) in factors.items():
        role = (tr("drives the sliding") if drives
                else tr("resists the sliding"))
        kind = (tr("permanent load") if action == "permanent"
                else tr("variable load"))
        lines.append(f"{escape(load_name_label(name))}: {kind}, {role}: "
                     f"× {factor:g}")
    return "<br>" + tr("Loads on this surface:") + "<br>" + "<br>".join(lines)


class ResultsDock(QDockWidget):
    """Dock widget that presents the Top-N critical surfaces of a search."""

    surface_selected = Signal(int)  # row index in the current SearchResult

    def __init__(self, parent=None) -> None:
        super().__init__(tr("Results"), parent)
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

        # v0.1.419 (D361) -- a last column says why a surface the checks
        # rejected cannot be the critical one, listed after the admissible
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["#", tr("FoS"), tr("Method"), tr("Centre X"), tr("Centre Y"),
             tr("Radius"), tr("Note")]
        )
        # v0.1.421 (D363) -- each column as wide as its contents, heading
        # included, scrolling sideways when they do not fit, as Interpret's
        # Surfaces table: stretched, the headings were cut
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents)
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
        # v0.1.443 (D401) -- every surface the run analysed, the user's
        # included: with a search that leaves no population (a focus that
        # rejects every surface) and a valid surface drawn by hand, the run
        # has a critical surface and this said «No results yet.»
        from ogr_slip2d.search import all_evaluations_of, is_user_surface_of
        if search_result is None or not all_evaluations_of(search_result):
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
            # v0.1.443 (D401) -- «Valid» stays the search's count (D58: 0
            # with a focus that rejects every surface), so a critical
            # surface the user drew says whose it is: the number beside the
            # count is not one of the counted
            line = (tr('Method: <b>{0}</b>   Valid: {1}   {2}: <b>{3:.3f}</b>'
                       ' (surface defined by the user)')
                    if is_user_surface_of(search_result, crit) else
                    tr('Method: <b>{0}</b>   Valid: {1}   {2}: <b>{3:.3f}</b>'))
            self.header_label.setText(
                line.format(method_name(search_result.method_id), n_ok, label, crit.fos)
                + load_factor_lines(crit)
            )
        else:
            self.header_label.setText(
                tr('Method: {0}. No valid surfaces found ({1} invalid).').format(method_name(search_result.method_id), search_result.invalid_count)
            )

        # v0.1.369 (D345) — the column says what it prints: FoS, an
        # over-design factor with a standard, or each surface's Ky on a
        # seismic search (whose surfaces this table lists by Ky). The line
        # above keeps the critical's ``.fos``, captioned by ``fos_label``.
        from ogr_gui.reported_quantity import column_caption, column_value
        self.table.setHorizontalHeaderItem(1, QTableWidgetItem(
            column_caption(search_result, factor_report)))
        from ogr_gui.core_messages import surface_note
        from ogr_gui.themes import theme_color
        # v0.1.419 (D361) -- ``top_n`` lists the admissible surfaces first,
        # in the order ``critical`` chooses, so the highlighted row is the
        # critical one: it was the lowest factor, admissible or not
        for i, res in enumerate(search_result.top_n(50)):
            sd = res.surface.to_dict()
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(
                column_value(search_result, res, factor_report)))
            # v0.1.324 (D315) — the method's name, not its identifier
            self.table.setItem(i, 2, QTableWidgetItem(method_name(res.method_id)))
            for col, text in zip((3, 4, 5), circle_cells(sd)):
                self.table.setItem(i, col, QTableWidgetItem(text))
            # v0.1.443 (D401) -- and whose the surface is, when the user
            # drew it (``surface_note``)
            text, tip = surface_note(search_result, res)
            note = QTableWidgetItem(text)
            note.setToolTip(tip)
            self.table.setItem(i, 6, note)
            if not getattr(res, "admissible", True):
                for c in range(self.table.columnCount()):
                    self.table.item(i, c).setForeground(
                        QColor(theme_color("muted")))

            if res is crit:
                # Highlight critical row. v0.1.326 (D319) — a fixed ink on
                # a fixed background, legible in both themes: a yellow
                # background with the theme's text was white on yellow in
                # the dark one. The pair of the stale band above.
                for c in range(self.table.columnCount()):
                    item = self.table.item(i, c)
                    item.setBackground(QColor(CRITICAL_ROW_BACKGROUND))
                    item.setForeground(QColor(CRITICAL_ROW_INK))
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)

    def _on_selection(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if rows:
            self.surface_selected.emit(rows[0].row())

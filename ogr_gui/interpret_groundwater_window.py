# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Interpret Groundwater window — Phase 5 of the groundwater plan.

Displays the converged seepage field over the FE mesh:

    * filled contours of **total head H**, **pressure head P** or
      **pore pressure u** (suction shown as negative values)
    * **flow vectors** (element Darcy velocity)
    * the **free surface** (P = 0 iso-line)
    * a **discharge section** tool reporting the integrated normal flux

All the underlying quantities come straight from ``SeepageResult`` and
``UnsaturatedSeepageSolver``; this window only presents them.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from ogr_gui.i18n import tr  # noqa: E402

_FIELDS = [
    ("total_head", "Total Head H"),
    ("pressure_head", "Pressure Head P"),
    ("pore_pressure", "Pore Pressure u"),
]

#: v0.1.307 (D295) — the data of the selector's entry for the initial state
#: (the stages carry their own index, from 0).
_INITIAL = -1


class InterpretGroundwaterWindow(QMainWindow):
    """Read-only viewer for a seepage result."""

    def __init__(self, project, result, solver=None, parent=None):
        super().__init__(parent)
        self.project = project
        self.result = result
        self.solver = solver
        self.setWindowTitle(tr("Interpret Groundwater — OGR FEM2D"))
        self.resize(1000, 620)

        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)

        bar = QHBoxLayout()
        # v0.1.31 — stage navigation for transient runs
        self.stages = list(getattr(project, "transient_results", []) or [])
        # v0.1.307 (D295) — and the state they started from, first, as the
        # reference shows it. None for a steady field, and for a transient
        # computed before this version, which never stored it.
        self.initial = (getattr(project, "transient_initial_result", None)
                        if self.stages else None)
        if self.stages:
            bar.addWidget(QLabel(tr("Stage:")))
            self.cbo_stage = QComboBox()
            if self.initial is not None:
                self.cbo_stage.addItem(tr("0: t = 0 (initial state)"),
                                       _INITIAL)
            for i, r in enumerate(self.stages):
                t = r.notes.get("time", 0.0)
                lbl = r.notes.get("label") or ""
                sf = "  [SF]" if r.notes.get("calculate_sf") else ""
                self.cbo_stage.addItem(
                    f"{i + 1}: t = {t:g}{(' ' + lbl) if lbl else ''}{sf}", i)
            self.cbo_stage.setCurrentIndex(self.cbo_stage.count() - 1)
            # Each entry carries what it shows: with the initial state in
            # front, entry k is no longer stage k.
            self.cbo_stage.currentIndexChanged.connect(self._on_choice)
            bar.addWidget(self.cbo_stage)
            self.btn_fos = QPushButton(tr("FoS vs time…"))
            self.btn_fos.clicked.connect(self._plot_fos_history)
            bar.addWidget(self.btn_fos)
        else:
            self.cbo_stage = None
        bar.addWidget(QLabel(tr("Field:")))
        self.cbo_field = QComboBox()
        for key, label in _FIELDS:
            self.cbo_field.addItem(tr(label), key)
        self.cbo_field.currentIndexChanged.connect(self._redraw)
        bar.addWidget(self.cbo_field)

        self.chk_vectors = QCheckBox(tr("Flow vectors"))
        self.chk_vectors.setChecked(True)
        self.chk_vectors.toggled.connect(self._redraw)
        bar.addWidget(self.chk_vectors)

        self.chk_surface = QCheckBox(tr("Free surface (P=0)"))
        self.chk_surface.setChecked(True)
        self.chk_surface.toggled.connect(self._redraw)
        bar.addWidget(self.chk_surface)

        self.chk_mesh = QCheckBox(tr("Mesh"))
        self.chk_mesh.toggled.connect(self._redraw)
        bar.addWidget(self.chk_mesh)

        btn_q = QPushButton(tr("Discharge section…"))
        btn_q.clicked.connect(self._discharge_section)
        bar.addWidget(btn_q)
        bar.addStretch(1)
        v.addLayout(bar)

        self.canvas = None
        self._container = QVBoxLayout()
        v.addLayout(self._container, 1)

        self.status = QLabel("")
        v.addWidget(self.status)
        self._summary()
        self._redraw()

    # ------------------------------------------------------------------
    def _on_stage(self, index: int) -> None:
        """Switch the displayed stage of a transient run (``index`` is the
        stage's, 0-based)."""
        if not self.stages or not (0 <= index < len(self.stages)):
            return
        self._show(self.stages[index])

    def _on_choice(self, entry: int) -> None:
        """An entry of the stage selector: a stage, or the initial state
        (v0.1.307, D295)."""
        data = self.cbo_stage.itemData(entry) if self.cbo_stage else None
        if data == _INITIAL:
            if self.initial is not None:
                self._show(self.initial)
        elif data is not None:
            self._on_stage(int(data))

    def _show(self, result) -> None:
        self.result = result
        self._summary()
        self._redraw()

    def _plot_fos_history(self):
        """Plot the factor of safety against time for the stages flagged
        *Calculate SF* — the point of a transient stability analysis.

        v0.1.308 (D311) — NON-modal, and the same series and chart as
        *Interpret > Graph SF with Time* (``fos_history``,
        ``ogr_gui.xy_chart``). It opened its own dialog with ``exec()``,
        which blocked the application, and said "no factor" with a modal
        box; that goes to the status bar now. Returns the chart window, or
        None."""
        from ogr_slip2d.transient_stability import fos_history

        from .xy_chart import show_xy_chart
        series = fos_history(self.stages, self.initial)
        if not series:
            warn = next((r.notes.get("fos_warning") for r in self.stages
                         if r.notes.get("fos_warning")), None)
            self.statusBar().showMessage(
                tr(warn) if warn else tr(
                    "No stage has a computed factor of safety. Tick "
                    "'Calculate SF' on the stages you need and recompute."),
                15000)
            return None
        dlg = show_xy_chart(self, tr("Factor of safety vs time"), series,
                            tr("Time"), tr("Factor of safety"))
        if dlg is None:
            self.statusBar().showMessage(tr("matplotlib is not installed."),
                                         15000)
        return dlg

    def _summary(self) -> None:
        r = self.result
        if r is None or not r.total_head:
            self.status.setText(tr("No seepage result."))
            return
        bits = [tr('nodes: {0}').format(len(r.total_head)),
                f"H: {min(r.total_head):.2f} … {max(r.total_head):.2f}",
                f"u: {min(r.pore_pressure):.1f} … "
                f"{max(r.pore_pressure):.1f}",
                tr('iterations: {0}').format(r.iterations)]
        if r.seepage_nodes:
            bits.append(tr('seepage-face nodes: {0}').format(len(r.seepage_nodes)))
        if r.notes.get("time") is not None:
            bits.insert(0, f"t = {r.notes['time']:g}")
        if r.notes.get("initial_state"):
            bits.insert(1, tr("initial state"))
        fos = r.notes.get("fos") or {}
        if fos:
            bits.append("FoS " + ", ".join(
                f"{k}={v:.4f}" for k, v in sorted(fos.items())))
        if not r.converged:
            bits.append("NOT CONVERGED")
        warn = r.notes.get("warning")
        # v0.1.270 (D268): a stage that evolved from an unconverged steady
        # field says so, under its own warning
        init = r.notes.get("initial_state_warning")
        # v0.1.271 (D270): a mesh saved with flat elements says so
        mesh_warn = r.notes.get("mesh_warning")
        self.status.setText("   |   ".join(bits)
                            + (f"\n{warn}" if warn else "")
                            + (f"\n{init}" if init and init != warn else "")
                            + (f"\n{mesh_warn}" if mesh_warn else ""))

    # ------------------------------------------------------------------
    def _redraw(self) -> None:
        mesh = getattr(self.project, "fem_mesh", None)
        r = self.result
        if mesh is None or r is None or not r.total_head:
            return
        try:
            import matplotlib
            matplotlib.use("QtAgg", force=False)
            import matplotlib.tri as mtri
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
        except ImportError:
            self.status.setText(tr("matplotlib is not installed."))
            return

        if self.canvas is not None:
            self._container.removeWidget(self.canvas)
            self.canvas.setParent(None)

        fig = Figure(figsize=(9.4, 4.6), tight_layout=True)
        ax = fig.add_subplot(111)
        xs = [n.x for n in mesh.nodes]
        ys = [n.y for n in mesh.nodes]
        tris = [list(e.nodes) for e in mesh.elements]
        tri = mtri.Triangulation(xs, ys, tris)

        key = self.cbo_field.currentData()
        vals = getattr(r, key)
        cf = ax.tricontourf(tri, vals, levels=18, cmap="viridis",
                            alpha=0.92)
        ax.tricontour(tri, vals, levels=18, colors="white", linewidths=0.5)
        fig.colorbar(cf, ax=ax, label=self.cbo_field.currentText())

        if self.chk_mesh.isChecked():
            ax.triplot(tri, color="#888888", lw=0.25, alpha=0.6)

        if self.chk_vectors.isChecked() and r.velocity:
            step = max(1, len(mesh.elements) // 220)
            cx, cy, u, w = [], [], [], []
            for e in mesh.elements[::step]:
                px, py = e.centroid(mesh)
                vx, vy = r.velocity[e.id]
                cx.append(px)
                cy.append(py)
                u.append(vx)
                w.append(vy)
            mag = max((math.hypot(a, b) for a, b in zip(u, w)), default=0.0)
            if mag > 0:
                ax.quiver(cx, cy, u, w, color="crimson", width=0.0025,
                          scale=mag * 28.0)

        if self.chk_surface.isChecked() and self.solver is not None:
            try:
                fs = self.solver.free_surface_points(r)
            except Exception:  # noqa: BLE001
                fs = []
            if fs:
                ax.plot([p[0] for p in fs], [p[1] for p in fs],
                        color="#0b3d91", lw=2.2, ls="--",
                        label="free surface (P=0)")
                ax.legend(loc="upper right", fontsize=8)

        ax.set_aspect("equal")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        self.canvas = FigureCanvasQTAgg(fig)
        self._container.addWidget(self.canvas)

    # ------------------------------------------------------------------
    def _discharge_section(self) -> None:
        """Integrate the normal flux across a user-defined section."""
        if self.solver is None or self.result is None:
            return
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(
            self, tr("Discharge section"),
            tr("Section as x0,y0,x1,y1:"))
        if not ok or not text:
            return
        try:
            x0, y0, x1, y1 = (float(v) for v in text.replace(";", ",")
                              .split(","))
        except ValueError:
            QMessageBox.warning(self, tr("Discharge section"),
                                tr("Enter four numbers: x0,y0,x1,y1"))
            return
        q = self.solver.flux_through_segment(self.result, x0, y0, x1, y1,
                                             samples=500)
        QMessageBox.information(
            self, tr("Discharge section"),
            tr('Normal flux through the section:\n\nQ = {0:.6e}  (per unit width)\n\nSign convention: positive when the flow crosses towards the section normal, i.e. the tangent rotated +90 deg. Reversing the section reverses the sign.').format(q))

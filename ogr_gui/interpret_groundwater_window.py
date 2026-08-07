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
        if self.stages:
            bar.addWidget(QLabel(tr("Stage:")))
            self.cbo_stage = QComboBox()
            for i, r in enumerate(self.stages):
                t = r.notes.get("time", 0.0)
                lbl = r.notes.get("label") or ""
                sf = "  [SF]" if r.notes.get("calculate_sf") else ""
                self.cbo_stage.addItem(
                    f"{i + 1}: t = {t:g}{(' ' + lbl) if lbl else ''}{sf}", i)
            self.cbo_stage.setCurrentIndex(len(self.stages) - 1)
            self.cbo_stage.currentIndexChanged.connect(self._on_stage)
            bar.addWidget(self.cbo_stage)
            self.btn_fos = QPushButton(tr("FoS vs time…"))
            self.btn_fos.clicked.connect(self._plot_fos_history)
            bar.addWidget(self.btn_fos)
        else:
            self.cbo_stage = None
        bar.addWidget(QLabel(tr("Field:")))
        self.cbo_field = QComboBox()
        for key, label in _FIELDS:
            self.cbo_field.addItem(label, key)
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
        """Switch the displayed stage of a transient run."""
        if not self.stages or not (0 <= index < len(self.stages)):
            return
        self.result = self.stages[index]
        self._summary()
        self._redraw()

    def _plot_fos_history(self) -> None:
        """Plot the factor of safety against time for the stages flagged
        *Calculate SF* — the point of a transient stability analysis."""
        pts = []
        for r in self.stages:
            fos = r.notes.get("fos") or {}
            if fos:
                pts.append((r.notes.get("time", 0.0), fos))
        if not pts:
            warn = next((r.notes.get("fos_warning") for r in self.stages
                         if r.notes.get("fos_warning")), None)
            QMessageBox.information(
                self, "FoS vs time",
                warn or "No stage has a computed factor of safety. Tick "
                        "'Calculate SF' on the stages you need and "
                        "recompute.")
            return
        try:
            import matplotlib
            matplotlib.use("QtAgg", force=False)
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
            from PySide6.QtWidgets import QDialog
        except ImportError:
            QMessageBox.information(self, "FoS vs time",
                                    "matplotlib is not installed.")
            return
        methods = sorted({m for _t, f in pts for m in f})
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Factor of safety vs time"))
        dlg.resize(620, 420)
        lay = QVBoxLayout(dlg)
        fig = Figure(figsize=(5.8, 3.9), tight_layout=True)
        ax = fig.add_subplot(111)
        for mid in methods:
            xs = [t for t, f in pts if mid in f]
            ys = [f[mid] for _t, f in pts if mid in f]
            ax.plot(xs, ys, marker="o", label=mid)
        ax.set_xlabel("Time")
        ax.set_ylabel("Critical factor of safety")
        ax.grid(True, alpha=0.3)
        if len(methods) > 1:
            ax.legend(fontsize=8)
        lay.addWidget(FigureCanvasQTAgg(fig))
        dlg.exec()

    def _summary(self) -> None:
        r = self.result
        if r is None or not r.total_head:
            self.status.setText(tr("No seepage result."))
            return
        bits = [f"nodes: {len(r.total_head)}",
                f"H: {min(r.total_head):.2f} … {max(r.total_head):.2f}",
                f"u: {min(r.pore_pressure):.1f} … "
                f"{max(r.pore_pressure):.1f}",
                f"iterations: {r.iterations}"]
        if r.seepage_nodes:
            bits.append(f"seepage-face nodes: {len(r.seepage_nodes)}")
        if r.notes.get("time") is not None:
            bits.insert(0, f"t = {r.notes['time']:g}")
        fos = r.notes.get("fos") or {}
        if fos:
            bits.append("FoS " + ", ".join(
                f"{k}={v:.4f}" for k, v in sorted(fos.items())))
        if not r.converged:
            bits.append("NOT CONVERGED")
        warn = r.notes.get("warning")
        self.status.setText("   |   ".join(bits)
                            + (f"\n{warn}" if warn else ""))

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
            self, "Discharge section",
            "Section as x0,y0,x1,y1:")
        if not ok or not text:
            return
        try:
            x0, y0, x1, y1 = (float(v) for v in text.replace(";", ",")
                              .split(","))
        except ValueError:
            QMessageBox.warning(self, "Discharge section",
                                "Enter four numbers: x0,y0,x1,y1")
            return
        q = self.solver.flux_through_segment(self.result, x0, y0, x1, y1,
                                             samples=500)
        QMessageBox.information(
            self, "Discharge section",
            f"Normal flux through the section:\n\n"
            f"Q = {q:.6e}  (per unit width)\n\n"
            f"Sign convention: positive when the flow crosses towards "
            f"the section normal, i.e. the tangent rotated +90 deg. "
            f"Reversing the section reverses the sign.")

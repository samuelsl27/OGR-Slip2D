# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Define Hydraulic Properties dialog — Phase 5 of the groundwater plan.

Follows the reference layout reverse-engineered in
``docs/INTERFAZ_AGUA_SUBTERRANEA.md``:

* material list on the left, parameters on the right;
* material **names and colours are read-only here** — they belong to the
  strength-properties dialog, because both are views of the SAME material
  list, not two separate lists;
* ``Ks`` is disabled when the model is *User Defined* (there Ks is the
  first point of the curve);
* the parameter widgets shown depend on the selected model;
* **Plot** graphs the resulting k(psi) function;
* **Pick** loads representative literature parameters, and is offered
  only for the models that have a library (Brooks-Corey, Fredlund-Xing,
  Gardner, van Genuchten).

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
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ogr_core.hydraulic import (
    HydraulicProperties,
    PermeabilityModel,
    SimpleSoilType,
    library_for,
)
from ogr_gui.i18n import tr  # noqa: E402

_MODEL_LABELS = [
    (PermeabilityModel.CONSTANT, "Constant"),
    (PermeabilityModel.SIMPLE, "Simple"),
    (PermeabilityModel.BROOKS_COREY, "Brooks-Corey"),
    (PermeabilityModel.FREDLUND_XING, "Fredlund-Xing"),
    (PermeabilityModel.GARDNER, "Gardner"),
    (PermeabilityModel.VAN_GENUCHTEN, "van Genuchten"),
    (PermeabilityModel.USER_DEFINED, "User Defined"),
]

_SOIL_LABELS = [
    (SimpleSoilType.GENERAL, "General"),
    (SimpleSoilType.SAND, "Sand"),
    (SimpleSoilType.SILT, "Silt"),
    (SimpleSoilType.CLAY, "Clay"),
    (SimpleSoilType.LOAM, "Loam"),
]


def _spin(minimum, maximum, value, decimals=4, step=0.1):
    s = QDoubleSpinBox()
    s.setDecimals(decimals)
    s.setRange(minimum, maximum)
    s.setSingleStep(step)
    s.setValue(value)
    return s


class HydraulicPropertiesDialog(QDialog):
    """Edit the hydraulic properties of every material."""

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(tr("Define Hydraulic Properties"))
        self.resize(720, 520)
        self._current = -1
        # Working copies so Cancel really cancels
        self._props: list[HydraulicProperties] = []
        for m in project.materials:
            self._props.append(
                HydraulicProperties.from_dict(m.hydraulic.to_dict())
                if m.hydraulic is not None else HydraulicProperties())

        root = QHBoxLayout(self)

        # ---- material list (names read-only) -------------------------
        left = QVBoxLayout()
        left.addWidget(QLabel(tr("Materials")))
        self.list = QListWidget()
        for m in project.materials:
            self.list.addItem(m.name)
        self.list.currentRowChanged.connect(self._on_material_changed)
        left.addWidget(self.list, 1)
        left.addWidget(QLabel(
            "<i>Names and colours are defined in\nDefine Material "
            "Properties</i>"))
        root.addLayout(left, 1)

        # ---- parameters ---------------------------------------------
        right = QVBoxLayout()

        gb_k = QGroupBox(tr("Permeability"))
        fk = QFormLayout(gb_k)
        self.sp_ks = _spin(1e-14, 1.0, 1e-6, decimals=12, step=1e-7)
        fk.addRow(tr("Saturated permeability Ks:"), self.sp_ks)
        self.sp_k2k1 = _spin(0.0, 100.0, 1.0, decimals=4, step=0.05)
        fk.addRow(tr("K2 / K1:"), self.sp_k2k1)
        self.sp_angle = _spin(-90.0, 90.0, 0.0, decimals=2, step=5.0)
        fk.addRow(tr("K1 angle (deg from +X):"), self.sp_angle)
        right.addWidget(gb_k)

        gb_m = QGroupBox(tr("Unsaturated permeability model"))
        fm = QVBoxLayout(gb_m)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Model:")))
        self.cbo_model = QComboBox()
        for mdl, label in _MODEL_LABELS:
            self.cbo_model.addItem(label, mdl)
        self.cbo_model.currentIndexChanged.connect(self._on_model_changed)
        row.addWidget(self.cbo_model, 1)
        self.btn_pick = QPushButton(tr("Pick…"))
        self.btn_pick.clicked.connect(self._pick)
        row.addWidget(self.btn_pick)
        self.btn_plot = QPushButton(tr("Plot…"))
        self.btn_plot.clicked.connect(self._plot)
        row.addWidget(self.btn_plot)
        fm.addLayout(row)

        self.stack = QStackedWidget()
        self._pages: dict[PermeabilityModel, QWidget] = {}
        self._build_pages()
        fm.addWidget(self.stack)
        right.addWidget(gb_m, 1)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        right.addWidget(bb)
        root.addLayout(right, 2)

        if project.materials:
            self.list.setCurrentRow(0)

    # ==================================================================
    def _build_pages(self) -> None:
        # Constant / User Defined — no parameters here
        for mdl, text in (
            (PermeabilityModel.CONSTANT,
             "k = Ks everywhere (fully saturated)."),
            (PermeabilityModel.USER_DEFINED,
             "Ks is taken from the first point of the user curve."),
        ):
            w = QWidget()
            v = QVBoxLayout(w)
            v.addWidget(QLabel(text))
            v.addStretch(1)
            self._pages[mdl] = w
            self.stack.addWidget(w)

        # Simple
        w = QWidget()
        f = QFormLayout(w)
        self.cbo_soil = QComboBox()
        for st, label in _SOIL_LABELS:
            self.cbo_soil.addItem(label, st)
        f.addRow(tr("Soil type:"), self.cbo_soil)
        self._pages[PermeabilityModel.SIMPLE] = w
        self.stack.addWidget(w)

        # Brooks-Corey
        w = QWidget()
        f = QFormLayout(w)
        self.sp_bc_lambda = _spin(0.01, 20.0, 0.6, 4, 0.05)
        self.sp_bc_psib = _spin(0.0, 1e6, 30.0, 3, 5.0)
        f.addRow(tr("Pore size index (lambda):"), self.sp_bc_lambda)
        f.addRow(tr("Bubbling pressure:"), self.sp_bc_psib)
        self._pages[PermeabilityModel.BROOKS_COREY] = w
        self.stack.addWidget(w)

        # Fredlund-Xing
        w = QWidget()
        f = QFormLayout(w)
        self.sp_fx_a = _spin(1e-6, 1e7, 50.0, 4, 5.0)
        self.sp_fx_b = _spin(1e-6, 100.0, 2.0, 4, 0.1)
        self.sp_fx_c = _spin(1e-6, 100.0, 1.0, 4, 0.1)
        f.addRow(tr("A:"), self.sp_fx_a)
        f.addRow(tr("B:"), self.sp_fx_b)
        f.addRow(tr("C:"), self.sp_fx_c)
        self._pages[PermeabilityModel.FREDLUND_XING] = w
        self.stack.addWidget(w)

        # Gardner
        w = QWidget()
        f = QFormLayout(w)
        self.sp_g_a = _spin(0.0, 1e9, 0.01, 6, 0.01)
        self.sp_g_n = _spin(1e-6, 100.0, 2.0, 4, 0.1)
        f.addRow(tr("a:"), self.sp_g_a)
        f.addRow(tr("n:"), self.sp_g_n)
        self._pages[PermeabilityModel.GARDNER] = w
        self.stack.addWidget(w)

        # van Genuchten
        w = QWidget()
        f = QFormLayout(w)
        self.sp_vg_alpha = _spin(1e-9, 1e4, 0.036, 6, 0.005)
        self.sp_vg_n = _spin(1.0001, 20.0, 1.56, 4, 0.05)
        self.chk_custom_m = QCheckBox(tr("Custom m"))
        self.sp_vg_m = _spin(1e-4, 0.9999, 0.359, 4, 0.02)
        self.chk_custom_m.toggled.connect(self.sp_vg_m.setEnabled)
        self.sp_vg_m.setEnabled(False)
        f.addRow(tr("alpha:"), self.sp_vg_alpha)
        f.addRow(tr("n:"), self.sp_vg_n)
        f.addRow(self.chk_custom_m, self.sp_vg_m)
        self._pages[PermeabilityModel.VAN_GENUCHTEN] = w
        self.stack.addWidget(w)

    # ==================================================================
    def _on_model_changed(self, _idx: int) -> None:
        mdl = self.cbo_model.currentData()
        page = self._pages.get(mdl)
        if page is not None:
            self.stack.setCurrentWidget(page)
        # Ks is disabled for User Defined (it is the curve's first point)
        self.sp_ks.setEnabled(mdl != PermeabilityModel.USER_DEFINED)
        # Pick is only offered for models with a parameter library
        self.btn_pick.setEnabled(bool(library_for(mdl)))

    def _on_material_changed(self, row: int) -> None:
        if self._current >= 0:
            self._store(self._current)
        self._current = row
        if 0 <= row < len(self._props):
            self._load(self._props[row])

    # ------------------------------------------------------------------
    def _load(self, p: HydraulicProperties) -> None:
        self.sp_ks.setValue(p.ks)
        self.sp_k2k1.setValue(p.k2_k1)
        self.sp_angle.setValue(p.k1_angle_deg)
        i = self.cbo_model.findData(p.model)
        self.cbo_model.setCurrentIndex(max(0, i))
        j = self.cbo_soil.findData(p.simple_soil_type)
        self.cbo_soil.setCurrentIndex(max(0, j))
        self.sp_bc_lambda.setValue(p.bc_lambda)
        self.sp_bc_psib.setValue(p.bc_psi_b)
        self.sp_fx_a.setValue(p.fx_a)
        self.sp_fx_b.setValue(p.fx_b)
        self.sp_fx_c.setValue(p.fx_c)
        self.sp_g_a.setValue(p.gardner_a)
        self.sp_g_n.setValue(p.gardner_n)
        self.sp_vg_alpha.setValue(p.vg_alpha)
        self.sp_vg_n.setValue(p.vg_n)
        self.chk_custom_m.setChecked(p.vg_custom_m)
        self.sp_vg_m.setValue(p.vg_m)
        self._on_model_changed(0)

    def _store(self, row: int) -> None:
        if not (0 <= row < len(self._props)):
            return
        p = self._props[row]
        p.ks = self.sp_ks.value()
        p.k2_k1 = self.sp_k2k1.value()
        p.k1_angle_deg = self.sp_angle.value()
        p.model = self.cbo_model.currentData()
        p.simple_soil_type = self.cbo_soil.currentData()
        p.bc_lambda = self.sp_bc_lambda.value()
        p.bc_psi_b = self.sp_bc_psib.value()
        p.fx_a = self.sp_fx_a.value()
        p.fx_b = self.sp_fx_b.value()
        p.fx_c = self.sp_fx_c.value()
        p.gardner_a = self.sp_g_a.value()
        p.gardner_n = self.sp_g_n.value()
        p.vg_alpha = self.sp_vg_alpha.value()
        p.vg_n = self.sp_vg_n.value()
        p.vg_custom_m = self.chk_custom_m.isChecked()
        p.vg_m = self.sp_vg_m.value()

    # ==================================================================
    def _pick(self) -> None:
        """Load representative literature parameters for the model."""
        from PySide6.QtWidgets import QInputDialog
        mdl = self.cbo_model.currentData()
        lib = library_for(mdl)
        if not lib:
            return
        names = sorted(lib)
        name, ok = QInputDialog.getItem(
            self, "Pick representative parameters",
            "Soil (literature values):", names, 0, False)
        if not ok:
            return
        for key, value in lib[name].items():
            widget = {
                "bc_lambda": self.sp_bc_lambda,
                "bc_psi_b": self.sp_bc_psib,
                "fx_a": self.sp_fx_a, "fx_b": self.sp_fx_b,
                "fx_c": self.sp_fx_c,
                "gardner_a": self.sp_g_a, "gardner_n": self.sp_g_n,
                "vg_alpha": self.sp_vg_alpha, "vg_n": self.sp_vg_n,
            }.get(key)
            if widget is not None:
                widget.setValue(float(value))

    def _plot(self) -> None:
        """Graph the permeability function currently defined."""
        self._store(self._current)
        if not (0 <= self._current < len(self._props)):
            return
        p = self._props[self._current]
        try:
            import matplotlib
            matplotlib.use("QtAgg", force=False)
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
        except ImportError:
            QMessageBox.information(self, "Plot",
                                    "matplotlib is not installed.")
            return
        curve = p.curve(psi_max=1e4, n=90)
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Permeability function"))
        dlg.resize(560, 400)
        v = QVBoxLayout(dlg)
        fig = Figure(figsize=(5.4, 3.8), tight_layout=True)
        ax = fig.add_subplot(111)
        xs = [max(c[0], 1e-2) for c in curve[1:]]
        ys = [p.ks * c[1] for c in curve[1:]]
        ax.loglog(xs, ys, lw=1.8)
        ax.set_xlabel("Matric suction")
        ax.set_ylabel("Permeability k")
        ax.grid(True, which="both", alpha=0.3)
        ax.set_title(self.cbo_model.currentText())
        v.addWidget(FigureCanvasQTAgg(fig))
        dlg.exec()

    # ==================================================================
    def _accept(self) -> None:
        self._store(self._current)
        for m, p in zip(self.project.materials, self._props):
            m.hydraulic = p
        self.project.is_dirty = True
        self.accept()

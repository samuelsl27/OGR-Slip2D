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
* **Pick** loads representative parameters, and is offered only for the
  models that have a library (Brooks-Corey, Fredlund-Xing, Gardner, van
  Genuchten). Its list says where they come from (v0.1.279, D273): the
  published table for van Genuchten and Brooks-Corey, "illustrative, no
  published source" for Gardner and Fredlund-Xing.

v0.1.268 (D191) — the **water content function** of the transient
analysis is a group of its own, visible with every model: theta_s,
theta_r, the van Genuchten alpha, n and m, and the specific storage Ss.
Until this version alpha and n sat on the van Genuchten page only, and
theta_s, theta_r and Ss on none, although the transient reads all of them
with ANY permeability model: a material with a user curve had five
parameters moving its transient that the user could neither see nor
change. alpha, n and m are the same widgets as before (one set: they are
both the van Genuchten permeability and the retention curve of every
model, an OGR convention); theta_s, theta_r and Ss are greyed out when no
transient analysis reads them (``rules.transient_storage_is_read``).

v0.1.278 (D275) — the alpha of that curve is per model. The group's alpha
is ``wc_alpha``, read by every model except van Genuchten; the van
Genuchten page has its own alpha again, ``vg_alpha``, which with that model
is both the permeability and the curve (one alpha, as van Genuchten 1980
derives one from the other). Each of alpha, n and m is greyed out when it
moves nothing for the model shown and the analysis
(``rules.retention_field_is_read``).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ogr_core.hydraulic import (
    HydraulicProperties,
    PermeabilityModel,
    SimpleSoilType,
    library_for,
)
from ogr_core.hydraulic.permeability_models import (library_source,
                                                     parse_user_curve_text)
from ogr_core.project.rules import (retention_field_is_read,
                                    transient_storage_is_read)
from ogr_gui.dialogs.material_properties_dialog import (
    _exact_text,
    _PreciseSpinBox,
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


def _precise(minimum, maximum, value, step):
    """A spin box that keeps every double it is given (v0.1.275, D271): a
    permeability or a kr floor of 1e-13 survives opening the dialog and
    pressing OK, which a fixed-decimal box does not."""
    s = _PreciseSpinBox()
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
        # v0.1.276 (D282) — in a scroll area. With the water content group
        # of D191 and the curve table of D271 the column grew to 842 and 974
        # px, taller than a 1536 x 816 screen: the title bar went off the
        # top and the dialog could not be moved. The problems and OK /
        # Cancel stay outside it, always in view.
        panel = QWidget()
        right = QVBoxLayout(panel)

        gb_k = QGroupBox(tr("Permeability"))
        fk = QFormLayout(gb_k)
        # v0.1.275 (D271): it had twelve decimals, so opening the dialog and
        # pressing OK rounded a Ks below 1e-10 and turned 1e-13 into the
        # box's minimum, 1e-14; the verification bank has Ks of 1e-13.
        self.sp_ks = _precise(1e-300, 1.0, 1e-6, 1e-7)
        fk.addRow(tr("Saturated permeability Ks:"), self.sp_ks)
        self.sp_k2k1 = _spin(0.0, 100.0, 1.0, decimals=4, step=0.05)
        fk.addRow(tr("K2 / K1:"), self.sp_k2k1)
        self.sp_angle = _spin(-90.0, 90.0, 0.0, decimals=2, step=5.0)
        fk.addRow(tr("K1 angle (deg from +X):"), self.sp_angle)
        # v0.1.275 (D271): the floor of the relative permeability, which
        # moves the flow of every model with a dry zone, could be set by a
        # script or the API and not seen or changed here
        self.sp_kr_min = _precise(1e-300, 1.0, 1e-6, 1e-6)
        fk.addRow(tr("Minimum relative permeability kr_min:"),
                  self.sp_kr_min)
        kr_note = QLabel(tr(
            "kr is never taken below this floor, so the dry zone keeps some "
            "conductivity; points of a user curve below it change nothing."))
        kr_note.setWordWrap(True)
        fk.addRow(kr_note)
        self.sp_kr_min.valueChanged.connect(self._refresh_problems)
        right.addWidget(gb_k)

        gb_m = QGroupBox(tr("Unsaturated permeability model"))
        fm = QVBoxLayout(gb_m)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Model:")))
        self.cbo_model = QComboBox()
        for mdl, label in _MODEL_LABELS:
            self.cbo_model.addItem(tr(label), mdl)
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
        self._build_water_content_group()
        self._build_pages()
        fm.addWidget(self.stack)
        right.addWidget(gb_m, 1)
        right.addWidget(self.gb_wc)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(panel)
        column = QVBoxLayout()
        column.addWidget(self.scroll, 1)

        # v0.1.268 (D191) — what makes the current material unusable, in
        # words, inside the dialog (a message box would block a test). It
        # is where a User Defined material without a curve says so.
        self.lbl_problems = QLabel("")
        self.lbl_problems.setWordWrap(True)
        self.lbl_problems.setStyleSheet("color: #b00020;")
        column.addWidget(self.lbl_problems)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        column.addWidget(bb)
        root.addLayout(column, 2)

        if project.materials:
            self.list.setCurrentRow(0)

    # ==================================================================
    def _build_pages(self) -> None:
        # Constant — no parameters
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel(tr("k = Ks everywhere (fully saturated).")))
        v.addStretch(1)
        self._pages[PermeabilityModel.CONSTANT] = w
        self.stack.addWidget(w)

        # User Defined — v0.1.275 (D271): the curve itself. Until this
        # version the page was this one sentence, and the curve could only
        # be set by a script or the API: choosing User Defined here gave a
        # material with no curve, which is kr = 1 everywhere.
        w = QWidget()
        v = QVBoxLayout(w)
        note = QLabel(tr("Ks is taken from the first point of the user "
                         "curve."))
        note.setWordWrap(True)
        v.addWidget(note)
        self.tbl_curve = QTableWidget(0, 2)
        # D217: a table without units misleads; the suction of a user curve
        # is in kPa since v0.1.200 (D121)
        self.tbl_curve.setHorizontalHeaderLabels(
            [tr("Matric suction (kPa)"), tr("Permeability (m/s)")])
        # v0.1.276 — the first column as wide as its header (it showed
        # "latric suction (kP"), the second takes the rest
        self.tbl_curve.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_curve.horizontalHeader().setStretchLastSection(True)
        self.tbl_curve.itemChanged.connect(self._on_curve_edited)
        v.addWidget(self.tbl_curve, 1)
        row = QHBoxLayout()
        self.btn_curve_add = QPushButton(tr("+ Row"))
        self.btn_curve_add.clicked.connect(self._add_curve_row)
        self.btn_curve_del = QPushButton(tr("− Row"))
        self.btn_curve_del.clicked.connect(self._delete_curve_rows)
        self.btn_curve_csv = QPushButton(tr("Import CSV…"))
        self.btn_curve_csv.clicked.connect(self._import_curve)
        for b in (self.btn_curve_add, self.btn_curve_del, self.btn_curve_csv):
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self._pages[PermeabilityModel.USER_DEFINED] = w
        self.stack.addWidget(w)

        # Simple
        w = QWidget()
        f = QFormLayout(w)
        self.cbo_soil = QComboBox()
        for st, label in _SOIL_LABELS:
            self.cbo_soil.addItem(tr(label), st)
        f.addRow(tr("Soil type:"), self.cbo_soil)
        # v0.1.267 (D190): the curve behind Simple is OGR's own convention
        # (see permeability_models.kr_simple). The user is told so where
        # the model is chosen, not only in a docstring.
        self.lbl_simple_note = QLabel(tr(
            "Simple is an OGR convention: the reference does not publish "
            "its function. General: kr drops one decade over the first "
            "100 kPa of suction, then stays constant. Ks does not change "
            "the shape of the curve."))
        self.lbl_simple_note.setWordWrap(True)
        f.addRow(self.lbl_simple_note)
        self._pages[PermeabilityModel.SIMPLE] = w
        self.stack.addWidget(w)

        # Brooks-Corey
        w = QWidget()
        f = QFormLayout(w)
        self.sp_bc_lambda = _spin(0.01, 20.0, 0.6, 4, 0.05)
        # Six decimals (v0.1.279, D273): the library's psi_b is the table's
        # cm times 0.0981 (sand 0.712206 kPa), which three decimals rounded
        # on Pick and again on OK.
        self.sp_bc_psib = _spin(0.0, 1e6, 30.0, 6, 5.0)
        f.addRow(tr("Pore size index (lambda):"), self.sp_bc_lambda)
        f.addRow(tr("Bubbling pressure (kPa):"), self.sp_bc_psib)
        self._pages[PermeabilityModel.BROOKS_COREY] = w
        self.stack.addWidget(w)

        # Fredlund-Xing
        w = QWidget()
        f = QFormLayout(w)
        self.sp_fx_a = _spin(1e-6, 1e7, 50.0, 4, 5.0)
        self.sp_fx_b = _spin(1e-6, 100.0, 2.0, 4, 0.1)
        self.sp_fx_c = _spin(1e-6, 100.0, 1.0, 4, 0.1)
        f.addRow(tr("A (kPa):"), self.sp_fx_a)
        f.addRow(tr("B:"), self.sp_fx_b)
        f.addRow(tr("C:"), self.sp_fx_c)
        self._pages[PermeabilityModel.FREDLUND_XING] = w
        self.stack.addWidget(w)

        # Gardner
        w = QWidget()
        f = QFormLayout(w)
        self.sp_g_a = _spin(0.0, 1e9, 0.01, 6, 0.01)
        self.sp_g_n = _spin(1e-6, 100.0, 2.0, 4, 0.1)
        f.addRow(tr("a (1/m^n):"), self.sp_g_a)
        f.addRow(tr("n:"), self.sp_g_n)
        self._pages[PermeabilityModel.GARDNER] = w
        self.stack.addWidget(w)

        # van Genuchten — its own alpha (v0.1.278, D275), and the n and m of
        # the water content function below
        w = QWidget()
        f = QFormLayout(w)
        self.sp_vg_alpha = _spin(1e-9, 1e4, 3.6, 6, 0.1)
        f.addRow(tr("alpha (1/m):"), self.sp_vg_alpha)
        note = QLabel(tr(
            "The van Genuchten permeability uses this alpha and the n and m "
            "of the water content function below; with this model the water "
            "content function uses this alpha too."))
        note.setWordWrap(True)
        f.addRow(note)
        self._pages[PermeabilityModel.VAN_GENUCHTEN] = w
        self.stack.addWidget(w)

    def _build_water_content_group(self) -> None:
        """theta_s, theta_r, alpha, n, m and Ss, for every model."""
        self.gb_wc = QGroupBox(tr("Water content function (transient analysis)"))
        f = QFormLayout(self.gb_wc)
        note = QLabel(tr(
            "The transient analysis reads this van Genuchten curve with "
            "every permeability model (an OGR convention); below the water "
            "table it reads the specific storage."))
        note.setWordWrap(True)
        f.addRow(note)
        self.sp_wc_sat = _spin(0.0, 1.0, 0.4, 4, 0.01)
        self.sp_wc_res = _spin(0.0, 1.0, 0.05, 4, 0.01)
        f.addRow(tr("Saturated water content (θs):"), self.sp_wc_sat)
        f.addRow(tr("Residual water content (θr):"), self.sp_wc_res)
        # v0.1.278 (D275): the curve's own alpha; van Genuchten uses its
        # page's (greyed out here then, see _refresh_retention)
        self.sp_wc_alpha = _spin(1e-9, 1e4, 0.036, 6, 0.01)
        self.sp_vg_n = _spin(1.0001, 20.0, 1.56, 4, 0.05)
        self.chk_custom_m = QCheckBox(tr("Custom m"))
        self.sp_vg_m = _spin(1e-4, 0.9999, 0.359, 4, 0.02)
        self.chk_custom_m.toggled.connect(self._refresh_retention)
        self.sp_vg_m.setEnabled(False)
        f.addRow(tr("alpha (1/m):"), self.sp_wc_alpha)
        f.addRow(tr("n:"), self.sp_vg_n)
        f.addRow(self.chk_custom_m, self.sp_vg_m)
        # Ten decimals: with six, opening the dialog and pressing OK set an
        # Ss of 1e-7 1/m to zero, because QDoubleSpinBox rounds on setValue.
        self.sp_ss = _spin(0.0, 1.0, 1e-5, 10, 1e-5)
        f.addRow(tr("Specific storage Ss (1/m):"), self.sp_ss)
        # Read only by a transient analysis (rule 7): greyed out otherwise.
        read = transient_storage_is_read(self.project)
        for wdg in (self.sp_wc_sat, self.sp_wc_res, self.sp_ss):
            wdg.setEnabled(read)
            if not read:
                wdg.setToolTip(tr(
                    "Read only by a transient groundwater analysis."))
        for wdg in (self.sp_wc_sat, self.sp_wc_res, self.sp_ss,
                    self.sp_wc_alpha):
            wdg.valueChanged.connect(self._refresh_problems)

    def _refresh_retention(self, *_args) -> None:
        """Grey out the alpha, n and m of the water content function that
        move nothing for the model shown and this project's analysis
        (rule 7; v0.1.278, D275, ``rules.retention_field_is_read``)."""
        if not hasattr(self, "cbo_model"):
            return
        mdl = self.cbo_model.currentData()
        tips = {
            "wc_alpha": tr("With van Genuchten the water content function "
                           "uses the alpha of its page; with the other "
                           "models it is read only by a transient "
                           "groundwater analysis."),
            "vg_n": tr("Read only by a transient groundwater analysis."),
        }
        for field, wdg in (("wc_alpha", self.sp_wc_alpha),
                           ("vg_n", self.sp_vg_n),
                           ("vg_custom_m", self.chk_custom_m)):
            read = retention_field_is_read(self.project, mdl, field)
            wdg.setEnabled(read)
            wdg.setToolTip("" if read else tips.get(field, tips["vg_n"]))
        self.sp_vg_m.setEnabled(self.chk_custom_m.isEnabled()
                                and self.chk_custom_m.isChecked())

    # ==================================================================
    def _on_model_changed(self, _idx: int) -> None:
        mdl = self.cbo_model.currentData()
        page = self._pages.get(mdl)
        if page is not None:
            self.stack.setCurrentWidget(page)
        # Ks is disabled for User Defined (it is the curve's first point,
        # which the box shows: v0.1.275, D271)
        self.sp_ks.setEnabled(mdl != PermeabilityModel.USER_DEFINED)
        self._sync_ks()
        # Pick is only offered for models with a parameter library
        self.btn_pick.setEnabled(bool(library_for(mdl)))
        self._refresh_retention()
        self._refresh_problems()

    def _refresh_problems(self, *_args) -> None:
        """Show what makes the material being edited unusable (v0.1.268,
        D191): the widgets' values applied to a copy, asked to
        ``HydraulicProperties.problems``. Nothing is blocked; it is said.
        v0.1.275 (D271): also what it contains that changes nothing
        (``notices``) and the rows of the user curve that are not two
        numbers."""
        if not (0 <= self._current < len(self._props)) or \
                not hasattr(self, "lbl_problems"):
            return
        probe = HydraulicProperties.from_dict(
            self._props[self._current].to_dict())
        self._write(probe)
        lines = [tr(text) for text in probe.problems() + probe.notices()]
        _pts, bad = self._curve_points()
        if bad:
            lines.append(tr("Rows of the user curve that are not two "
                            "numbers: %s") % ", ".join(str(r) for r in bad))
        self.lbl_problems.setText("\n".join(lines))

    # ---- the user curve (v0.1.275, D271) ------------------------------
    def _curve_points(self):
        """(points, bad rows): the table's (suction, k) pairs in its order,
        and the 1-based rows that are not two numbers; blank rows skipped.
        A decimal comma is read as a point."""
        pts, bad = [], []
        for r in range(self.tbl_curve.rowCount()):
            texts = []
            for c in (0, 1):
                item = self.tbl_curve.item(r, c)
                texts.append(item.text().strip() if item is not None else "")
            if not any(texts):
                continue
            try:
                pts.append(tuple(float(t.replace(",", ".")) for t in texts))
            except ValueError:
                bad.append(r + 1)
        return pts, bad

    def _set_curve_rows(self, pts) -> None:
        """Fill the table with ``pts``, each value written so that it reads
        back exactly (``_exact_text``)."""
        self.tbl_curve.blockSignals(True)
        try:
            self.tbl_curve.setRowCount(0)
            for s, k in pts:
                r = self.tbl_curve.rowCount()
                self.tbl_curve.insertRow(r)
                self.tbl_curve.setItem(r, 0, QTableWidgetItem(_exact_text(s)))
                self.tbl_curve.setItem(r, 1, QTableWidgetItem(_exact_text(k)))
        finally:
            self.tbl_curve.blockSignals(False)
        self._on_curve_edited()

    def _add_curve_row(self) -> None:
        self.tbl_curve.insertRow(self.tbl_curve.rowCount())

    def _delete_curve_rows(self) -> None:
        rows = sorted({i.row() for i in self.tbl_curve.selectedIndexes()},
                      reverse=True)
        if not rows and self.tbl_curve.rowCount():
            rows = [self.tbl_curve.rowCount() - 1]
        for r in rows:
            self.tbl_curve.removeRow(r)
        self._on_curve_edited()

    def _import_curve(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Import CSV…"), "",
            tr("Text files (*.csv *.txt);;All files (*)"))
        if path:
            with open(path, encoding="utf-8", errors="replace") as fh:
                self.import_curve_text(fh.read())

    def import_curve_text(self, text: str) -> int:
        """Load the curve from CSV-like text (``parse_user_curve_text``);
        returns how many points were read. Nothing read leaves the table as
        it was and says so where the problems are shown."""
        pts = parse_user_curve_text(text)
        if pts:
            self._set_curve_rows(pts)
        else:
            self.lbl_problems.setText(tr(
                "No (suction, permeability) pairs were found in the file."))
        return len(pts)

    def _on_curve_edited(self, *_args) -> None:
        self._sync_ks()
        self._refresh_problems()

    def _sync_ks(self) -> None:
        """With User Defined, the Ks box shows the curve's first point."""
        if self.cbo_model.currentData() != PermeabilityModel.USER_DEFINED:
            return
        pts, _bad = self._curve_points()
        if pts:
            k_first = sorted(pts, key=lambda t: t[0])[0][1]
            if k_first > 0:
                self.sp_ks.setValue(k_first)

    def _on_material_changed(self, row: int) -> None:
        if self._current >= 0:
            self._store(self._current)
        self._current = row
        if 0 <= row < len(self._props):
            self._load(self._props[row])

    # ------------------------------------------------------------------
    def _load(self, p: HydraulicProperties) -> None:
        # The curve before Ks: filling the table re-syncs the Ks box while
        # the model combo still shows the previous material's model, and
        # Ks has to win (the model is set below and syncs it again).
        self._set_curve_rows(p.user_curve)
        self.sp_ks.setValue(p.ks)
        self.sp_kr_min.setValue(p.kr_min)
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
        self.sp_wc_sat.setValue(p.wc_sat)
        self.sp_wc_res.setValue(p.wc_res)
        self.sp_wc_alpha.setValue(p.wc_alpha)
        self.sp_ss.setValue(p.specific_storage)
        self._on_model_changed(0)

    def _store(self, row: int) -> None:
        if not (0 <= row < len(self._props)):
            return
        self._write(self._props[row])

    def _write(self, p: HydraulicProperties) -> None:
        """The widgets' values into ``p``."""
        p.ks = self.sp_ks.value()
        p.kr_min = self.sp_kr_min.value()
        # v0.1.275 (D271): the curve, sorted by suction. A table that holds
        # the same points as the curve it was loaded with keeps that list
        # as it was, so opening and pressing OK changes nothing.
        pts, _bad = self._curve_points()
        if sorted(pts) != sorted(tuple(q) for q in p.user_curve):
            p.user_curve = sorted(pts, key=lambda t: t[0])
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
        p.wc_sat = self.sp_wc_sat.value()
        p.wc_res = self.sp_wc_res.value()
        p.wc_alpha = self.sp_wc_alpha.value()
        p.specific_storage = self.sp_ss.value()

    # ==================================================================
    def _pick_label(self, mdl) -> str:
        """What the Pick list says its values are (v0.1.279, D273): the
        published table they come from, or that they have none. It said
        "literature values" for the four libraries, and two of them have no
        source."""
        source = library_source(mdl)
        if source:
            return tr("Soil (values from {0}):").format(source)
        return tr("Soil (illustrative values, no published source):")

    def _pick_prompt(self, mdl) -> str:
        """The label of the Pick list as handed to Qt.

        v0.1.287 (D288) — the label of a ``QInputDialog`` has a buddy, so Qt
        reads «&» as the mark of a keyboard shortcut and does not draw it:
        «Rawls, Brakensiek & Saxton (1982)» came out «Rawls, Brakensiek
        Saxton (1982)». Doubled, it is drawn. ``_pick_label`` keeps the
        source as written, for whoever reads it."""
        return self._pick_label(mdl).replace("&", "&&")

    def _pick(self) -> None:
        """Load representative parameters for the model."""
        from PySide6.QtWidgets import QInputDialog
        mdl = self.cbo_model.currentData()
        lib = library_for(mdl)
        if not lib:
            return
        names = sorted(lib)
        name, ok = QInputDialog.getItem(
            self, tr("Pick representative parameters"),
            self._pick_prompt(mdl), names, 0, False)
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

    def _plot(self):
        """Graph the permeability function currently defined.

        v0.1.275 (D271): NOT modal (it was ``exec()``: an informative chart
        that blocks the dialog cannot be compared with the table beside it,
        and blocks a run without a screen for ever); the points of a user
        curve are drawn over its interpolation; the scale is the Ks the
        material is computed with (``saturated_k``), which for a user curve
        is its first point — it was the ``ks`` box, disabled there."""
        self._store(self._current)
        if not (0 <= self._current < len(self._props)):
            return None
        p = self._props[self._current]
        try:
            import matplotlib
            matplotlib.use("QtAgg", force=False)
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
        except ImportError:
            QMessageBox.information(self, tr("Plot"),
                                    tr("matplotlib is not installed."))
            return None
        curve = p.curve(psi_max=1e4, n=90)
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("Permeability function"))
        dlg.resize(560, 400)
        v = QVBoxLayout(dlg)
        fig = Figure(figsize=(5.4, 3.8), tight_layout=True)
        ax = fig.add_subplot(111)
        k_sat = p.saturated_k()
        # v0.1.276 — from the first sample (suction 0, drawn at 1e-2 like
        # the first point of a user curve): the line started at 0.1 and
        # left the first point alone
        xs = [max(c[0], 1e-2) for c in curve]
        ys = [k_sat * c[1] for c in curve]
        ax.loglog(xs, ys, lw=1.8)
        if p.model == PermeabilityModel.USER_DEFINED and p.user_curve:
            pts = sorted(p.user_curve, key=lambda t: t[0])
            ax.loglog([max(s, 1e-2) for s, _k in pts], [k for _s, k in pts],
                      "o", label=tr("Points of the user curve"))
            ax.legend(fontsize=8)
        # v0.1.200 — in the unit the model is written in.
        ax.set_xlabel(tr("Suction head (m)") if p.suction_unit() == "m"
                      else tr("Matric suction (kPa)"))
        ax.set_ylabel(tr("Permeability k"))
        ax.grid(True, which="both", alpha=0.3)
        ax.set_title(self.cbo_model.currentText())
        v.addWidget(FigureCanvasQTAgg(fig))
        dlg.show()
        # kept so Qt does not collect the window as soon as this returns
        if not hasattr(self, "_plot_windows"):
            self._plot_windows = []
        self._plot_windows.append(dlg)
        return dlg

    # ==================================================================
    def _accept(self) -> None:
        self._store(self._current)
        for m, p in zip(self.project.materials, self._props):
            m.hydraulic = p
        self.project.is_dirty = True
        self.accept()

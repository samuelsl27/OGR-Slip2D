# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Project Settings dialog — hierarchical configuration tree.

Mirrors the menu specified in ``Analysis → Project Settings...`` with
General → Methods → Groundwater → Transient → Statistics → Advanced
→ Project Summary pages.

Each page is a self-contained QWidget so new pages can be added without
touching this file (plugin-style).

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
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ogr_core.project import ProjectSettings
from ogr_core.project.settings import (
    GroundwaterMethod,
    LEMMethod as LEM,
    SearchMethod,
    SurfaceType,
)
from ogr_core.project.units import (
    FailureDirection,
    PermeabilityUnit,
    TimeUnit,
    UnitSystem,
)
from ogr_gui.i18n import tr


# ----------------------------------------------------------------------
class _GeneralPage(QWidget):
    """General settings — units, max counts, failure direction.

    v0.1.13 — replaces the simple metric/imperial dropdown with the
    full Slide-style 6-system selector (Pattern A: stored as SI). The
    selected system controls how every value is displayed and entered
    in the GUI; internal storage remains in SI (m, kN, kPa, kN/m³).
    """

    def __init__(self, s: ProjectSettings) -> None:
        super().__init__()
        self.s = s

        # Lazy-import the detailed unit module
        from ogr_core.units import SYSTEMS, get_system

        layout = QVBoxLayout(self)

        # --- Units group ---------------------------------------------
        from PySide6.QtWidgets import QGroupBox, QLabel
        ug = QGroupBox(tr("Units"))
        ufrm = QFormLayout(ug)

        self.cbo_unit_system = QComboBox()
        # Keep the systems in the canonical order shown in Slide:
        ordered_ids = [
            "metric_mpa", "metric_kpa", "metric_tonnes",
            "imperial_tons", "imperial_ksf", "imperial_psf",
        ]
        for sid in ordered_ids:
            sys_obj = SYSTEMS[sid]
            self.cbo_unit_system.addItem(sys_obj.label, sid)
        # Select the project's current system
        idx = ordered_ids.index(s.units.system_id) if s.units.system_id in ordered_ids else 1
        self.cbo_unit_system.setCurrentIndex(idx)

        # Summary label (auto-updates)
        self._unit_summary = QLabel()
        self._unit_summary.setStyleSheet(
            "color: #555; font-style: italic; padding-left: 6px;"
        )
        self._refresh_unit_summary()
        self.cbo_unit_system.currentIndexChanged.connect(
            self._refresh_unit_summary
        )

        ufrm.addRow(tr("Units:"), self.cbo_unit_system)
        ufrm.addRow("", self._unit_summary)
        layout.addWidget(ug)

        # --- Other settings -----------------------------------------
        og = QGroupBox(tr("Other settings"))
        form = QFormLayout(og)
        self.cbo_time = QComboBox()
        for t in TimeUnit:
            self.cbo_time.addItem(t.value, t)
        self.cbo_time.setCurrentIndex(list(TimeUnit).index(s.units.time))

        self.cbo_perm = QComboBox()
        for p in PermeabilityUnit:
            self.cbo_perm.addItem(p.value, p)
        self.cbo_perm.setCurrentIndex(
            list(PermeabilityUnit).index(s.units.permeability)
        )

        self.cbo_dir = QComboBox()
        for d in FailureDirection:
            self.cbo_dir.addItem(d.value, d)
        self.cbo_dir.setCurrentIndex(
            list(FailureDirection).index(s.units.failure_direction)
        )

        self.spn_mats = QSpinBox()
        self.spn_mats.setRange(1, 500)
        self.spn_mats.setValue(s.max_materials)
        self.spn_sups = QSpinBox()
        self.spn_sups.setRange(0, 500)
        self.spn_sups.setValue(s.max_supports)

        form.addRow(tr("Time Units:"), self.cbo_time)
        form.addRow(tr("Permeability Units:"), self.cbo_perm)
        form.addRow(tr("Failure Direction:"), self.cbo_dir)
        form.addRow(tr("Max Materials:"), self.spn_mats)
        form.addRow(tr("Max Supports:"), self.spn_sups)
        layout.addWidget(og)
        layout.addStretch()

    def _refresh_unit_summary(self) -> None:
        from ogr_core.units import get_system
        sid = self.cbo_unit_system.currentData()
        sys_obj = get_system(sid)
        self._unit_summary.setText(sys_obj.summary)

    def apply(self) -> None:
        # Detailed unit system (v0.1.13)
        new_sid = self.cbo_unit_system.currentData() or "metric_kpa"
        self.s.units.system_id = new_sid
        # Keep legacy ``system`` aligned (used by older code paths)
        self.s.units.system = (
            UnitSystem.IMPERIAL if new_sid.startswith("imperial")
            else UnitSystem.METRIC
        )
        self.s.units.time = self.cbo_time.currentData()
        self.s.units.permeability = self.cbo_perm.currentData()
        self.s.units.failure_direction = self.cbo_dir.currentData()
        self.s.max_materials = self.spn_mats.value()
        self.s.max_supports = self.spn_sups.value()


# ----------------------------------------------------------------------
class _MethodsPage(QWidget):
    METHODS = [
        (LEM.BISHOP_SIMPLIFIED, "Bishop Simplified"),
        (LEM.JANBU_SIMPLIFIED, "Janbu Simplified"),
        (LEM.JANBU_CORRECTED, "Janbu Corrected"),
        (LEM.ORDINARY_FELLENIUS, "Ordinary / Fellenius"),
        (LEM.SPENCER, "Spencer"),
        (LEM.GLE_MORGENSTERN_PRICE, "GLE / Morgenstern-Price"),
        (LEM.CORPS_OF_ENGINEERS_1, "Corps of Engineers #1"),
        (LEM.CORPS_OF_ENGINEERS_2, "Corps of Engineers #2"),
        (LEM.LOWE_KARAFIATH, "Lowe-Karafiath"),
    ]

    def __init__(self, s: ProjectSettings) -> None:
        super().__init__()
        self.s = s
        root = QVBoxLayout(self)

        grp = QGroupBox(tr("Methods (enable/disable)"))
        vbox = QVBoxLayout(grp)
        self.checkboxes: dict[str, QCheckBox] = {}
        enabled = set(s.methods.enabled_methods)
        for m, label in self.METHODS:
            cb = QCheckBox(label)
            cb.setChecked(m.value in enabled)
            # v0.1.7: Spencer and GLE/Morgenstern-Price are implemented.
            # Mark unimplemented Corps of Engineers and Lowe-Karafiath only.
            implemented = m in (
                LEM.BISHOP_SIMPLIFIED,
                LEM.JANBU_SIMPLIFIED,
                LEM.JANBU_CORRECTED,
                LEM.ORDINARY_FELLENIUS,
                LEM.SPENCER,
                LEM.GLE_MORGENSTERN_PRICE,
            )
            if not implemented:
                cb.setEnabled(False)
                cb.setToolTip(tr("Not yet implemented in OGR Slip2D"))
            self.checkboxes[m.value] = cb
            vbox.addWidget(cb)
        root.addWidget(grp)

        conv = QGroupBox(tr("Convergence Options"))
        form = QFormLayout(conv)
        self.spn_slices = QSpinBox(); self.spn_slices.setRange(3, 500); self.spn_slices.setValue(s.methods.num_slices)
        self.dsp_tol = QDoubleSpinBox(); self.dsp_tol.setDecimals(6); self.dsp_tol.setRange(1e-6, 1.0); self.dsp_tol.setValue(s.methods.tolerance)
        self.spn_iter = QSpinBox(); self.spn_iter.setRange(1, 500); self.spn_iter.setValue(s.methods.max_iterations)
        form.addRow(tr("Number of slices:"), self.spn_slices)
        form.addRow(tr("Tolerance:"), self.dsp_tol)
        form.addRow(tr("Maximum iterations:"), self.spn_iter)
        root.addWidget(conv)

    def apply(self) -> None:
        self.s.methods.enabled_methods = [
            k for k, cb in self.checkboxes.items() if cb.isChecked()
        ]
        self.s.methods.num_slices = self.spn_slices.value()
        self.s.methods.tolerance = self.dsp_tol.value()
        self.s.methods.max_iterations = self.spn_iter.value()


# ----------------------------------------------------------------------
class _GroundwaterPage(QWidget):
    def __init__(self, s: ProjectSettings) -> None:
        super().__init__()
        self.s = s
        from PySide6.QtWidgets import QCheckBox, QGroupBox, QVBoxLayout

        root = QVBoxLayout(self)
        # Basic
        basic = QGroupBox(tr("Basic"))
        form = QFormLayout(basic)

        self.cbo_method = QComboBox()
        for m in GroundwaterMethod:
            self.cbo_method.addItem(m.value, m.value)
        i = self.cbo_method.findData(s.groundwater.method)
        self.cbo_method.setCurrentIndex(max(0, i))

        self.dsp_gamma = QDoubleSpinBox()
        self.dsp_gamma.setRange(0.1, 50.0); self.dsp_gamma.setDecimals(3)
        self.dsp_gamma.setValue(s.groundwater.pore_fluid_unit_weight)
        self.dsp_gamma.setSuffix(" kN/m³")

        self.dsp_hu = QDoubleSpinBox()
        self.dsp_hu.setRange(0.0, 1.0); self.dsp_hu.setDecimals(3)
        self.dsp_hu.setValue(s.groundwater.default_hu)
        self.dsp_hu.setToolTip(
            "Default Hu coefficient (0..1) — multiplies the vertical "
            "distance to a Water Surface to obtain the pressure head."
        )

        self.cb_auto_hu = QCheckBox(tr("Auto Hu (compute from water-surface slope)"))
        self.cb_auto_hu.setChecked(s.groundwater.auto_hu)
        self.cb_auto_hu.setToolTip(
            "Hu = cos²(α), where α is the inclination of the water "
            "surface above the slice. For a horizontal water table "
            "α=0 and Hu=1."
        )

        form.addRow(tr("Method:"), self.cbo_method)
        form.addRow(tr("Pore Fluid Unit Weight:"), self.dsp_gamma)
        form.addRow(tr("Default Hu:"), self.dsp_hu)
        form.addRow("", self.cb_auto_hu)
        root.addWidget(basic)

        # Advanced (Rapid Drawdown / Excess Pore Pressure)
        adv = QGroupBox(tr("Advanced"))
        af = QFormLayout(adv)

        self.cb_excess = QCheckBox(tr("Calculate Excess Pore Pressure (B-bar method)"))
        self.cb_excess.setChecked(s.groundwater.excess_pore_pressure)
        self.cb_excess.setToolTip(
            "Enable B-bar method on undrained materials. Required for\n"
            "Rapid Drawdown analysis using Effective Stress with B-bar."
        )

        self.cb_rapid = QCheckBox(tr("Rapid Drawdown analysis"))
        self.cb_rapid.setChecked(s.groundwater.rapid_drawdown)
        self.cb_rapid.setToolTip(
            "Enables the Drawdown Line boundary tool (Boundaries menu)\n"
            "and computes the safety factor against rapid drawdown."
        )

        self.cbo_drawdown = QComboBox()
        for label, val in [
            ("Effective Stress using B-bar", "b_bar"),
            ("Duncan, Wright, Wong (1990) — 3-stage", "duncan_wright"),
            ("Army Corps of Engineers (1970) — 2-stage", "corps_2"),
            ("Lowe and Karafiath (1960)", "lowe_karafiath"),
        ]:
            self.cbo_drawdown.addItem(label, val)
        i = self.cbo_drawdown.findData(s.groundwater.rapid_drawdown_method)
        self.cbo_drawdown.setCurrentIndex(max(0, i))

        af.addRow("", self.cb_excess)
        af.addRow("", self.cb_rapid)
        af.addRow(tr("Drawdown method:"), self.cbo_drawdown)
        root.addWidget(adv)

        self.cb_rapid.toggled.connect(self._refresh_advanced)
        self._refresh_advanced()

    def _refresh_advanced(self) -> None:
        self.cbo_drawdown.setEnabled(self.cb_rapid.isChecked())

    def apply(self) -> None:
        self.s.groundwater.method = self.cbo_method.currentData()
        self.s.groundwater.pore_fluid_unit_weight = self.dsp_gamma.value()
        self.s.groundwater.default_hu = self.dsp_hu.value()
        self.s.groundwater.auto_hu = self.cb_auto_hu.isChecked()
        self.s.groundwater.excess_pore_pressure = self.cb_excess.isChecked()
        self.s.groundwater.rapid_drawdown = self.cb_rapid.isChecked()
        self.s.groundwater.rapid_drawdown_method = self.cbo_drawdown.currentData()


# ----------------------------------------------------------------------
class _SearchPage(QWidget):
    def __init__(self, s: ProjectSettings) -> None:
        super().__init__()
        self.s = s
        form = QFormLayout(self)

        self.cbo_type = QComboBox()
        for t in SurfaceType:
            self.cbo_type.addItem(t.value, t.value)
        self.cbo_type.setCurrentIndex(
            max(0, self.cbo_type.findData(s.search.surface_type))
        )
        self.cbo_method = QComboBox()
        for m in SearchMethod:
            self.cbo_method.addItem(m.value, m.value)
        self.cbo_method.setCurrentIndex(
            max(0, self.cbo_method.findData(s.search.search_method))
        )
        self.dsp_r = QDoubleSpinBox(); self.dsp_r.setRange(0.01, 100.0); self.dsp_r.setValue(s.search.radius_increment); self.dsp_r.setSuffix(" m")
        self.spn_n = QSpinBox(); self.spn_n.setRange(10, 1_000_000); self.spn_n.setValue(s.search.num_surfaces)
        self.chk_composite = QCheckBox(tr("Composite Surfaces")); self.chk_composite.setChecked(s.search.composite_surfaces)

        form.addRow(tr("Surface Type:"), self.cbo_type)
        form.addRow(tr("Search Method:"), self.cbo_method)
        form.addRow(tr("Radius Increment:"), self.dsp_r)
        form.addRow(tr("Number of Surfaces:"), self.spn_n)
        form.addRow(self.chk_composite)

    def apply(self) -> None:
        self.s.search.surface_type = self.cbo_type.currentData()
        self.s.search.search_method = self.cbo_method.currentData()
        self.s.search.radius_increment = self.dsp_r.value()
        self.s.search.num_surfaces = self.spn_n.value()
        self.s.search.composite_surfaces = self.chk_composite.isChecked()


# ----------------------------------------------------------------------
class _SummaryPage(QWidget):
    def __init__(self, s: ProjectSettings) -> None:
        super().__init__()
        self.s = s
        form = QFormLayout(self)
        self.ed_title = QLineEdit(s.summary.title)
        self.ed_author = QLineEdit(s.summary.author)
        self.ed_company = QLineEdit(s.summary.company)
        self.ed_analysis = QLineEdit(s.summary.analysis)
        self.ed_comments = QPlainTextEdit("\n".join(s.summary.comments))
        form.addRow(tr("Project Title:"), self.ed_title)
        form.addRow(tr("Author:"), self.ed_author)
        form.addRow(tr("Company:"), self.ed_company)
        form.addRow(tr("Analysis:"), self.ed_analysis)
        form.addRow(tr("Comments:"), self.ed_comments)

    def apply(self) -> None:
        self.s.summary.title = self.ed_title.text()
        self.s.summary.author = self.ed_author.text()
        self.s.summary.company = self.ed_company.text()
        self.s.summary.analysis = self.ed_analysis.text()
        txt = self.ed_comments.toPlainText().splitlines()
        self.s.summary.comments = [l for l in txt if l.strip()]


# ----------------------------------------------------------------------
class ProjectSettingsDialog(QDialog):
    """Tree-navigated project settings editor."""

    def __init__(self, settings: ProjectSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Project Settings..."))
        self.resize(720, 480)
        self.settings = settings

        layout = QHBoxLayout(self)

        self.nav = QListWidget()
        self.nav.setMaximumWidth(180)
        layout.addWidget(self.nav)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.pages: list[QWidget] = []
        self._add_page("General", _GeneralPage(settings))
        self._add_page("Methods", _MethodsPage(settings))
        self._add_page("Groundwater", _GroundwaterPage(settings))
        self._add_page("Transient", _TransientPage(settings))
        self._add_page("Statistics", _StatisticsPage(settings))
        self._add_page("Random Numbers", _RandomNumbersPage(settings))
        self._add_page("Design Standard", _DesignStandardPage(settings))
        self._add_page("Advanced", _AdvancedPage(settings))
        # v0.1.9 — Surface Search removed from Project Settings; it now
        # lives in Surfaces → Surface Options (Slide convention).
        self._add_page("Project Summary", _SummaryPage(settings))

        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

        right_wrap = QVBoxLayout()
        layout.addLayout(right_wrap, 0)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok
            | QDialogButtonBox.Apply
            | QDialogButtonBox.Cancel
            | QDialogButtonBox.RestoreDefaults
        )
        buttons.accepted.connect(self._ok)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self._apply)
        buttons.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self._defaults)
        main = QVBoxLayout()
        layout.takeAt(1)
        layout.takeAt(1)
        # Rebuild layout properly
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.addWidget(self.stack)
        vbox.addWidget(buttons)
        layout.addWidget(container, 1)

    # ------------------------------------------------------------------
    def _add_page(self, label: str, widget: QWidget) -> None:
        self.nav.addItem(label)
        self.stack.addWidget(widget)
        self.pages.append(widget)

    def _apply(self) -> None:
        for p in self.pages:
            if hasattr(p, "apply"):
                p.apply()

    def _ok(self) -> None:
        self._apply()
        self.accept()

    def _defaults(self) -> None:
        # Replace self.settings with a fresh ProjectSettings in place
        fresh = ProjectSettings()
        for attr in vars(fresh):
            setattr(self.settings, attr, getattr(fresh, attr))
        # Rebuild pages (cheap)
        self.nav.clear()
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()
        self.pages.clear()
        self._add_page("General", _GeneralPage(self.settings))
        self._add_page("Methods", _MethodsPage(self.settings))
        self._add_page("Groundwater", _GroundwaterPage(self.settings))
        # v0.1.9 — Surface Search now in Surfaces → Surface Options
        self._add_page("Project Summary", _SummaryPage(self.settings))
        self.nav.setCurrentRow(0)


# ======================================================================
# v0.1.52 (phase M2) — the five pages the specification describes and the
# dialog lacked. The data already existed in the model and was reachable
# from other dialogs; what was missing was the central place to see and
# change it.
# ======================================================================
class _TransientPage(QWidget):
    """Staged transient groundwater analysis.

    Editing the stage TABLE stays in the Groundwater menu, where the
    boundary conditions it depends on also live; this page holds the
    solver options and reports how many stages are defined, so the user
    can see at a glance whether a transient run is configured at all.
    """

    def __init__(self, settings) -> None:
        super().__init__()
        self.s = settings.groundwater
        form = QFormLayout(self)

        self.chk_enabled = QCheckBox(tr("Transient groundwater analysis"))
        self.chk_enabled.setChecked(bool(self.s.transient))
        self.chk_enabled.setToolTip(tr(
            "Advanced groundwater options are mutually exclusive: "
            "enabling this switches off Excess Pore Pressure and Rapid "
            "Drawdown."))
        form.addRow("", self.chk_enabled)

        self.lbl_stages = QLabel("")
        self._refresh_stage_label()
        form.addRow(tr("Stages defined:"), self.lbl_stages)

        self.sp_tol = QDoubleSpinBox()
        self.sp_tol.setDecimals(9)
        self.sp_tol.setRange(1e-9, 1.0)
        self.sp_tol.setValue(self.s.transient_tolerance)
        form.addRow(tr("Tolerance:"), self.sp_tol)

        self.sp_iter = QSpinBox()
        self.sp_iter.setRange(1, 1000)
        self.sp_iter.setValue(self.s.transient_max_iterations)
        form.addRow(tr("Maximum iterations:"), self.sp_iter)

        self.sp_steps = QSpinBox()
        self.sp_steps.setRange(0, 100000)
        self.sp_steps.setValue(self.s.transient_time_steps)
        self.sp_steps.setSpecialValueText(tr("Auto"))
        self.sp_steps.setToolTip(tr(
            "Number of time steps per stage. Auto derives it from the "
            "element size and the storage, so the water front cannot "
            "cross more than about one element per step."))
        form.addRow(tr("Number of time steps:"), self.sp_steps)

        note = QLabel(tr(
            "Stage times and the per-stage 'Calculate SF' flags are "
            "edited in Groundwater → Transient Groundwater, next to the "
            "boundary conditions they depend on."))
        note.setWordWrap(True)
        form.addRow("", note)

    def _refresh_stage_label(self) -> None:
        n = len(self.s.transient_stages or [])
        sf = len([x for x in (self.s.transient_stages or [])
                  if x.get("calculate_sf")])
        self.lbl_stages.setText(
            tr("%d stage(s), %d with a factor of safety") % (n, sf))

    def apply(self) -> None:
        if self.chk_enabled.isChecked():
            self.s.set_advanced_option("transient")
        elif self.s.transient:
            self.s.set_advanced_option(None)
        self.s.transient_tolerance = self.sp_tol.value()
        self.s.transient_max_iterations = self.sp_iter.value()
        self.s.transient_time_steps = self.sp_steps.value()


class _StatisticsPage(QWidget):
    """Probabilistic and sensitivity analysis."""

    def __init__(self, settings) -> None:
        super().__init__()
        self.s = settings.statistics
        form = QFormLayout(self)

        self.chk_prob = QCheckBox(tr("Probabilistic analysis"))
        self.chk_prob.setChecked(bool(self.s.probabilistic_analysis))
        form.addRow("", self.chk_prob)
        self.chk_sens = QCheckBox(tr("Sensitivity analysis"))
        self.chk_sens.setChecked(bool(self.s.sensitivity_analysis))
        form.addRow("", self.chk_sens)

        self.cbo_type = QComboBox()
        for value, label in (("global_minimum", tr("Global Minimum")),
                             ("overall_slope", tr("Overall Slope"))):
            self.cbo_type.addItem(label, value)
        i = self.cbo_type.findData(self.s.analysis_type)
        self.cbo_type.setCurrentIndex(max(0, i))
        self.cbo_type.setToolTip(tr(
            "Global Minimum reuses the deterministic critical surface for "
            "every sample. Overall Slope repeats the WHOLE search per "
            "sample: more rational, substantially slower."))
        form.addRow(tr("Analysis type:"), self.cbo_type)

        self.cbo_sampling = QComboBox()
        for value, label in (("monte_carlo", tr("Monte Carlo")),
                             ("latin_hypercube", tr("Latin Hypercube"))):
            self.cbo_sampling.addItem(label, value)
        j = self.cbo_sampling.findData(self.s.sampling_method)
        self.cbo_sampling.setCurrentIndex(max(0, j))
        self.cbo_sampling.setToolTip(tr(
            "Latin Hypercube converges markedly faster: around 1000 of "
            "its samples match some 5000 Monte Carlo ones."))
        form.addRow(tr("Sampling method:"), self.cbo_sampling)

        self.sp_samples = QSpinBox()
        self.sp_samples.setRange(1, 1000000)
        self.sp_samples.setValue(self.s.num_samples)
        form.addRow(tr("Number of samples:"), self.sp_samples)

        self.sp_intervals = QSpinBox()
        self.sp_intervals.setRange(2, 500)
        self.sp_intervals.setValue(self.s.sensitivity_intervals)
        self.sp_intervals.setToolTip(tr(
            "Number of equal intervals each variable range is divided "
            "into for the sensitivity sweep."))
        form.addRow(tr("Sensitivity intervals:"), self.sp_intervals)

        note = QLabel(tr(
            "Random variables are defined in Statistics → Random "
            "Variables."))
        note.setWordWrap(True)
        form.addRow("", note)

    def apply(self) -> None:
        self.s.probabilistic_analysis = self.chk_prob.isChecked()
        self.s.sensitivity_analysis = self.chk_sens.isChecked()
        self.s.analysis_type = self.cbo_type.currentData()
        self.s.sampling_method = self.cbo_sampling.currentData()
        self.s.num_samples = self.sp_samples.value()
        self.s.sensitivity_intervals = self.sp_intervals.value()


class _RandomNumbersPage(QWidget):
    """Seed and generator for the probabilistic analysis."""

    def __init__(self, settings) -> None:
        super().__init__()
        self.s = settings.random_numbers
        form = QFormLayout(self)

        self.cbo_method = QComboBox()
        for value, label in (("pseudo_random", tr("Pseudo-random")),
                             ("random", tr("Random"))):
            self.cbo_method.addItem(label, value)
        i = self.cbo_method.findData(self.s.method)
        self.cbo_method.setCurrentIndex(max(0, i))
        self.cbo_method.currentIndexChanged.connect(self._on_method)
        form.addRow(tr("Generation:"), self.cbo_method)

        self.sp_seed = QSpinBox()
        self.sp_seed.setRange(0, 2147483647)
        self.sp_seed.setValue(int(self.s.seed))
        form.addRow(tr("Seed:"), self.sp_seed)

        note = QLabel(tr(
            "A pseudo-random stream is reproducible: the same seed gives "
            "the same answer, which is what makes a probabilistic result "
            "defensible in a report and comparable between runs. A random "
            "stream is seeded from the clock, so successive runs explore "
            "differently — useful to check that a conclusion is not an "
            "artefact of one seed."))
        note.setWordWrap(True)
        form.addRow("", note)
        self._on_method()

    def _on_method(self, *_a) -> None:
        # The seed is meaningless for a clock-seeded run, so it is
        # disabled rather than left to look effective.
        self.sp_seed.setEnabled(
            self.cbo_method.currentData() == "pseudo_random")

    def apply(self) -> None:
        self.s.method = self.cbo_method.currentData()
        self.s.seed = self.sp_seed.value()


class _DesignStandardPage(QWidget):
    """Partial factors on actions and material properties."""

    def __init__(self, settings) -> None:
        super().__init__()
        self.s = settings.design_standard
        form = QFormLayout(self)

        self.chk_enabled = QCheckBox(tr("Apply partial factors"))
        self.chk_enabled.setChecked(bool(self.s.enabled))
        self.chk_enabled.toggled.connect(self._on_enabled)
        form.addRow("", self.chk_enabled)

        self.cbo_std = QComboBox()
        for value, label in (
            ("none", tr("None")),
            ("eurocode7_da1c1", tr("Eurocode 7 — DA1 Combination 1")),
            ("eurocode7_da1c2", tr("Eurocode 7 — DA1 Combination 2")),
            ("eurocode7_da2", tr("Eurocode 7 — DA2")),
            ("eurocode7_da3", tr("Eurocode 7 — DA3")),
            ("custom", tr("Custom")),
        ):
            self.cbo_std.addItem(label, value)
        i = self.cbo_std.findData(self.s.standard)
        self.cbo_std.setCurrentIndex(max(0, i))
        self.cbo_std.currentIndexChanged.connect(self._on_standard)
        form.addRow(tr("Design standard:"), self.cbo_std)

        self.factors = {}
        for attr, label in (
            ("factor_permanent", tr("Permanent actions:")),
            ("factor_variable", tr("Variable actions:")),
            ("factor_cohesion", tr("Cohesion:")),
            ("factor_friction", tr("tan(friction angle):")),
            ("factor_unit_weight", tr("Unit weight:")),
            ("factor_resistance", tr("Resistance:")),
        ):
            sp = QDoubleSpinBox()
            sp.setDecimals(3)
            sp.setRange(0.1, 10.0)
            sp.setSingleStep(0.05)
            sp.setValue(float(getattr(self.s, attr, 1.0)))
            self.factors[attr] = sp
            form.addRow(label, sp)

        note = QLabel(tr(
            "Off by default: applying partial factors silently would "
            "change every factor of safety previously compared against, "
            "so it has to be an explicit choice. Selecting a standard "
            "loads its factors; choose Custom to enter your own."))
        note.setWordWrap(True)
        form.addRow("", note)
        self._on_enabled(self.chk_enabled.isChecked())

    def _on_enabled(self, on: bool) -> None:
        self.cbo_std.setEnabled(bool(on))
        custom = self.cbo_std.currentData() == "custom"
        for sp in self.factors.values():
            sp.setEnabled(bool(on) and custom)

    def _on_standard(self, *_a) -> None:
        name = self.cbo_std.currentData()
        probe = type(self.s)()
        if probe.apply_preset(name):
            for attr, sp in self.factors.items():
                sp.setValue(float(getattr(probe, attr, 1.0)))
        self._on_enabled(self.chk_enabled.isChecked())

    def apply(self) -> None:
        self.s.enabled = self.chk_enabled.isChecked()
        self.s.standard = self.cbo_std.currentData()
        for attr, sp in self.factors.items():
            setattr(self.s, attr, sp.value())


class _AdvancedPage(QWidget):
    """Convergence and admissibility options."""

    def __init__(self, settings) -> None:
        super().__init__()
        self.s = settings.advanced
        form = QFormLayout(self)

        self.chk_tensile = QCheckBox(tr("Tensile stress check"))
        self.chk_tensile.setChecked(bool(self.s.check_tensile_stresses))
        self.chk_tensile.setToolTip(tr(
            "Rejects a surface with tension on a slice base. Applied "
            "AFTER the factor of safety converges, over a percentage of "
            "slices measured from the toe."))
        form.addRow("", self.chk_tensile)

        self.chk_steffensen = QCheckBox(
            tr("Accelerate convergence (Steffensen)"))
        self.chk_steffensen.setChecked(bool(self.s.iterate_steffensen))
        form.addRow("", self.chk_steffensen)

        self.sp_initial = QDoubleSpinBox()
        self.sp_initial.setDecimals(3)
        self.sp_initial.setRange(0.001, 100.0)
        self.sp_initial.setValue(self.s.min_initial_fs)
        form.addRow(tr("Initial factor of safety:"), self.sp_initial)

        self.sp_lmin = QDoubleSpinBox()
        self.sp_lmin.setDecimals(3)
        self.sp_lmin.setRange(-10.0, 10.0)
        self.sp_lmin.setValue(self.s.min_lambda)
        form.addRow(tr("Minimum lambda:"), self.sp_lmin)

        self.sp_lmax = QDoubleSpinBox()
        self.sp_lmax.setDecimals(3)
        self.sp_lmax.setRange(-10.0, 10.0)
        self.sp_lmax.setValue(self.s.max_lambda)
        self.sp_lmax.setToolTip(tr(
            "Search range for the interslice force scaling factor used by "
            "Spencer and GLE / Morgenstern-Price."))
        form.addRow(tr("Maximum lambda:"), self.sp_lmax)

        note = QLabel(tr(
            "The m-alpha check is deliberately NOT offered here. It "
            "rejects surfaces whose base normal denominator falls below "
            "0.2, and measurement showed it also rejects the "
            "reference-validated critical circle, so it is a diagnostic "
            "rather than a validity criterion and stays with the search "
            "options."))
        note.setWordWrap(True)
        form.addRow("", note)

    def apply(self) -> None:
        self.s.check_tensile_stresses = self.chk_tensile.isChecked()
        self.s.iterate_steffensen = self.chk_steffensen.isChecked()
        self.s.min_initial_fs = self.sp_initial.value()
        self.s.min_lambda = self.sp_lmin.value()
        self.s.max_lambda = self.sp_lmax.value()

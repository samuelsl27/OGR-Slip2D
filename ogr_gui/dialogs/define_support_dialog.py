# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Define Support Properties dialog (Slide-style).

Lets the user maintain a list of named "Support Types" — concrete
parameter sets bound to one of the 7 built-in SupportType classes
(End Anchored, Grouted Tieback, Soil Nail, etc.). Each named slot is
stored in :attr:`Project.support_types`.

UI layout:

    ┌─────────────────────┬───────────────────────────────────────┐
    │ Support Types  [+]  │ Name:        [Type 1               ]  │
    │                     │ Type:        [Grouted Tieback     ▼]  │
    │  Type 1             │ Application: [Active              ▼]  │
    │  Type 2             │ Orientation: [Parallel to bolt    ▼]  │
    │  ...                │ Description: <type-specific text>     │
    │                     │ ─────────────────────────────────────  │
    │                     │  (parameter form with tabs if needed)  │
    │                     │                                       │
    │                     │  spacing:       [  2.0 m       ]      │
    │                     │  tensile_cap.:  [600.0 kN      ]      │
    │                     │  ...                                  │
    │                     │                                       │
    │ [Add] [Dup] [Del]   │      [OK]  [Cancel]                   │
    └─────────────────────┴───────────────────────────────────────┘

Author: Samuel Sáez López — UPCT
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ogr_core.support import (
    ForceApplication,
    ForceOrientation,
    SupportType,
    UserDefined,
    support_registry,
)
from ogr_gui.i18n import tr  # noqa: E402


# ----------------------------------------------------------------------
# Choice lists for the string-valued support parameters. Kept here rather
# than in ``PARAMETERS`` because a label is user-visible text and belongs
# on the GUI side of the line, where ``tr()`` can reach it; the stored
# value is the ASCII token the .ogr file carries.
#
# v0.1.116 — ``pullout_mode`` used to be the only one, hard-coded inline
# and NOT wrapped in ``tr()``, so its three labels were the only part of
# this dialog a Spanish user still read in English.
_CHOICES: dict[str, list[tuple[str, str]]] = {
    "pullout_mode": [
        ("Adhesion and friction angle", "mohr_coulomb"),
        ("Coefficient of interaction (Ci)", "coefficient"),
        ("Friction factor (F*)", "friction_factor"),
    ],
    "shear_strength_model": [
        ("Linear (Mohr-Coulomb)", "linear"),
        ("Hyperbolic", "hyperbolic"),
    ],
    "anchorage": [
        ("None", "none"),
        ("Slope face", "slope_face"),
        ("Embedded end", "embedded_end"),
        ("Both ends", "both_ends"),
    ],
    "friction_factor_mode": [
        ("Constant", "constant"),
        ("Function of depth", "function"),
    ],
}


# ----------------------------------------------------------------------
class _SupportParamPanel(QWidget):
    """Parameter editor for the currently-selected SupportType class.

    Builds itself dynamically from ``SupportType.PARAMETERS`` and
    optionally groups parameters into tabs declared in
    ``SupportType.PARAMETER_TABS``.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._editors: dict[str, QWidget] = {}
        self._type_cls: Optional[type[SupportType]] = None
        self._user_table: Optional[QTableWidget] = None

    def _clear(self) -> None:
        # Remove all widgets from layout
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._editors.clear()
        self._user_table = None

    def set_type(
        self,
        type_cls: type[SupportType],
        current_values: Optional[dict] = None,
    ) -> None:
        """Rebuild the editor for ``type_cls``. ``current_values`` is a
        dict of param_name → value to seed the editors."""
        self._clear()
        self._type_cls = type_cls
        current_values = current_values or {}

        params = type_cls.PARAMETERS or {}
        tabs_spec = type_cls.PARAMETER_TABS or {}

        if tabs_spec:
            # Build a tabbed editor
            tabs = QTabWidget()
            for tab_name, param_names in tabs_spec.items():
                page = QWidget()
                form = QFormLayout(page)
                for name in param_names:
                    if name not in params:
                        continue
                    default, unit, desc = params[name]
                    val = current_values.get(name, default)
                    editor = self._build_editor_for_param(
                        name, default, unit, desc, val,
                    )
                    label = QLabel(self._pretty_name(name))
                    label.setToolTip(desc)
                    form.addRow(label, editor)
                tabs.addTab(page, tab_name)
            self._layout.addWidget(tabs)
        else:
            # Flat form
            form_widget = QWidget()
            form = QFormLayout(form_widget)
            for name, (default, unit, desc) in params.items():
                val = current_values.get(name, default)
                editor = self._build_editor_for_param(
                    name, default, unit, desc, val,
                )
                label = QLabel(self._pretty_name(name))
                label.setToolTip(desc)
                form.addRow(label, editor)
            self._layout.addWidget(form_widget)

        # User-defined table?
        if type_cls.TYPE_ID == "user_defined":
            self._build_user_table(current_values)

    def _pretty_name(self, name: str) -> str:
        return name.replace("_", " ").title() + ":"

    def _build_editor_for_param(
        self, name: str, default, unit: str, desc: str, value,
    ) -> QWidget:
        # String fields (choice lists declared in _CHOICES below)
        if isinstance(default, str):
            editor = QComboBox()
            choices = _CHOICES.get(name)
            if choices:
                for label, data in choices:
                    editor.addItem(tr(label), data)
                idx = editor.findData(value)
                editor.setCurrentIndex(max(0, idx))
            else:
                editor.addItem(str(value), value)
            editor.setToolTip(desc)
            self._editors[name] = editor
            return editor
        # Numeric
        spin = QDoubleSpinBox()
        spin.setRange(-1e9, 1e9)
        spin.setDecimals(4)
        if unit and unit != "-":
            spin.setSuffix(f" {unit}")
        spin.setValue(float(value))
        spin.setToolTip(desc)
        self._editors[name] = spin
        return spin

    def _build_user_table(self, current_values: dict) -> None:
        """Table editor for the UserDefined support's (distance, force)
        capacity points."""
        gb = QGroupBox(tr("Capacity vs Distance from Head (points)"))
        v = QVBoxLayout(gb)
        tbl = QTableWidget(0, 2)
        tbl.setHorizontalHeaderLabels(["Distance (m)", "Force (kN)"])
        tbl.horizontalHeader().setStretchLastSection(True)
        pts = current_values.get("points") or [
            (0.0, 100.0), (5.0, 200.0), (10.0, 100.0),
        ]
        tbl.setRowCount(len(pts))
        for i, (x, f) in enumerate(pts):
            tbl.setItem(i, 0, QTableWidgetItem(f"{x:.3f}"))
            tbl.setItem(i, 1, QTableWidgetItem(f"{f:.3f}"))
        v.addWidget(tbl)
        btns = QHBoxLayout()
        b_add = QPushButton(tr("+ Add row"))
        b_del = QPushButton(tr("− Remove row"))

        def _add():
            r = tbl.rowCount()
            tbl.insertRow(r)
            tbl.setItem(r, 0, QTableWidgetItem("0.0"))
            tbl.setItem(r, 1, QTableWidgetItem("0.0"))

        def _del():
            cur = tbl.currentRow()
            if cur >= 0:
                tbl.removeRow(cur)
        b_add.clicked.connect(_add)
        b_del.clicked.connect(_del)
        btns.addWidget(b_add); btns.addWidget(b_del); btns.addStretch()
        v.addLayout(btns)
        self._layout.addWidget(gb)
        self._user_table = tbl

    def get_values(self) -> dict:
        """Return the current values as a dict ready for the
        constructor of the SupportType subclass."""
        out: dict = {}
        for name, editor in self._editors.items():
            if isinstance(editor, QDoubleSpinBox):
                out[name] = editor.value()
            elif isinstance(editor, QComboBox):
                out[name] = editor.currentData()
        # User-defined: read the table
        if self._user_table is not None:
            pts = []
            for r in range(self._user_table.rowCount()):
                try:
                    x = float(self._user_table.item(r, 0).text())
                    f = float(self._user_table.item(r, 1).text())
                    pts.append((x, f))
                except (ValueError, AttributeError):
                    continue
            out["points"] = pts
        return out


# ----------------------------------------------------------------------
class _SupportRow:
    """A single Support Type slot — wraps a SupportType instance with a
    user-chosen name and color."""
    def __init__(
        self, name: str, support: SupportType,
        force_application: ForceApplication = ForceApplication.ACTIVE,
        orientation: ForceOrientation = ForceOrientation.TANGENT_TO_SLIP,
        user_angle_deg: float = 0.0,
        color: str = "#4b0082",
    ) -> None:
        self.name = name
        self.support = support
        self.force_application = force_application
        self.orientation = orientation
        self.user_angle_deg = user_angle_deg
        self.color = color


# ----------------------------------------------------------------------
class DefineSupportDialog(QDialog):
    """Slide-style Define Support Properties dialog."""

    def __init__(
        self,
        project,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Define Support Properties"))
        self.resize(820, 540)
        self.project = project

        # Load existing support types (or seed one default if empty)
        self._rows: list[_SupportRow] = []
        for st in getattr(project, "support_types", []) or []:
            self._rows.append(_SupportRow(
                name=getattr(st, "_display_name", st.DISPLAY_NAME),
                support=st,
                force_application=getattr(
                    st, "_force_application", ForceApplication.ACTIVE,
                ),
                orientation=getattr(
                    st, "_orientation", st.DEFAULT_ORIENTATION,
                ),
                user_angle_deg=getattr(st, "_user_angle_deg", 0.0),
                color=getattr(st, "_color", "#4b0082"),
            ))
        if not self._rows:
            self._rows.append(self._make_default_row())

        self._build_ui()
        self.list_widget.setCurrentRow(0)

    # ---- UI build -----------------------------------------------
    def _build_ui(self) -> None:
        root = QHBoxLayout(self)

        # LEFT — list of support types
        left = QVBoxLayout()
        left.addWidget(QLabel(tr("Support Types")))
        self.list_widget = QListWidget()
        for r in self._rows:
            self.list_widget.addItem(self._row_label(r))
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        left.addWidget(self.list_widget, stretch=1)

        btn_row = QHBoxLayout()
        b_add = QPushButton(tr("+ Add"))
        b_dup = QPushButton(tr("Duplicate"))
        b_del = QPushButton(tr("− Remove"))
        b_add.clicked.connect(self._add_row)
        b_dup.clicked.connect(self._duplicate_row)
        b_del.clicked.connect(self._delete_row)
        btn_row.addWidget(b_add); btn_row.addWidget(b_dup); btn_row.addWidget(b_del)
        left.addLayout(btn_row)
        left_w = QWidget(); left_w.setLayout(left); left_w.setMaximumWidth(220)

        # RIGHT — editor for the selected row
        right = QVBoxLayout()
        # Name
        nrow = QFormLayout()
        self.ed_name = QLineEdit()
        self.ed_name.editingFinished.connect(self._on_name_edited)
        nrow.addRow(tr("Name:"), self.ed_name)
        # Support type combobox
        self.cbo_type = QComboBox()
        for tid, cls in support_registry().items():
            self.cbo_type.addItem(cls.DISPLAY_NAME, tid)
        self.cbo_type.currentIndexChanged.connect(self._on_type_changed)
        nrow.addRow(tr("Support Type:"), self.cbo_type)
        # Force application
        self.cbo_app = QComboBox()
        for fa in ForceApplication:
            self.cbo_app.addItem(fa.value.capitalize(), fa)
        self.cbo_app.currentIndexChanged.connect(self._on_app_changed)
        nrow.addRow(tr("Force Application:"), self.cbo_app)
        # Orientation
        self.cbo_ori = QComboBox()
        for fo in ForceOrientation:
            self.cbo_ori.addItem(self._pretty_orientation(fo), fo)
        self.cbo_ori.currentIndexChanged.connect(self._on_ori_changed)
        nrow.addRow(tr("Force Orientation:"), self.cbo_ori)
        # User angle (only enabled when orientation = USER_DEFINED)
        self.spn_user_angle = QDoubleSpinBox()
        self.spn_user_angle.setRange(-360.0, 360.0)
        self.spn_user_angle.setSuffix(" °")
        self.spn_user_angle.valueChanged.connect(self._on_user_angle_changed)
        nrow.addRow(tr("User Angle (from horizontal):"), self.spn_user_angle)
        right.addLayout(nrow)

        # Description label
        self.lbl_desc = QLabel()
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet(
            "color: #555; font-style: italic; padding: 8px;"
            "background: #f4f4f8; border-radius: 4px;"
        )
        right.addWidget(self.lbl_desc)

        # Parameter panel (built dynamically)
        self.param_panel = _SupportParamPanel()
        right.addWidget(self.param_panel, stretch=1)

        # Dialog buttons
        bb = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        right.addWidget(bb)
        right_w = QWidget(); right_w.setLayout(right)

        root.addWidget(left_w)
        root.addWidget(right_w, stretch=1)

    # ---- helpers ------------------------------------------------
    def _pretty_orientation(self, fo: ForceOrientation) -> str:
        return {
            ForceOrientation.TANGENT_TO_SLIP: "Tangent to slip surface",
            ForceOrientation.PARALLEL_TO_SUPPORT: "Parallel to support",
            ForceOrientation.BISECTOR: "Bisector (tangent + parallel)",
            ForceOrientation.HORIZONTAL: "Horizontal",
            ForceOrientation.PERPENDICULAR_TO_PILE: "Perpendicular to pile",
            ForceOrientation.USER_DEFINED: "User-defined angle",
        }.get(fo, fo.value)

    def _row_label(self, row: _SupportRow) -> str:
        return f"{row.name}  [{row.support.DISPLAY_NAME}]"

    def _make_default_row(self) -> _SupportRow:
        cls = list(support_registry().values())[0]  # End Anchored
        return _SupportRow(
            name="Type 1", support=cls(),
            force_application=cls.DEFAULT_APPLICATION,
            orientation=cls.DEFAULT_ORIENTATION,
        )

    # ---- slots --------------------------------------------------
    def _on_row_changed(self, row_idx: int) -> None:
        if row_idx < 0 or row_idx >= len(self._rows):
            return
        row = self._rows[row_idx]
        self.ed_name.blockSignals(True)
        self.ed_name.setText(row.name)
        self.ed_name.blockSignals(False)

        # Combo for type
        self.cbo_type.blockSignals(True)
        idx = self.cbo_type.findData(row.support.TYPE_ID)
        if idx >= 0:
            self.cbo_type.setCurrentIndex(idx)
        self.cbo_type.blockSignals(False)
        self.lbl_desc.setText(type(row.support).DESCRIPTION)

        # Application
        self.cbo_app.blockSignals(True)
        idx = self.cbo_app.findData(row.force_application)
        if idx >= 0:
            self.cbo_app.setCurrentIndex(idx)
        self.cbo_app.blockSignals(False)
        # Orientation
        self.cbo_ori.blockSignals(True)
        idx = self.cbo_ori.findData(row.orientation)
        if idx >= 0:
            self.cbo_ori.setCurrentIndex(idx)
        self.cbo_ori.blockSignals(False)
        self.spn_user_angle.blockSignals(True)
        self.spn_user_angle.setValue(row.user_angle_deg)
        self.spn_user_angle.setEnabled(
            row.orientation == ForceOrientation.USER_DEFINED
        )
        self.spn_user_angle.blockSignals(False)

        # Build the parameter editor
        self.param_panel.set_type(
            type(row.support),
            current_values=row.support.__dict__,
        )

    def _on_name_edited(self) -> None:
        row_idx = self.list_widget.currentRow()
        if row_idx < 0:
            return
        self._commit_row(row_idx)
        self._rows[row_idx].name = self.ed_name.text()
        item = self.list_widget.item(row_idx)
        item.setText(self._row_label(self._rows[row_idx]))

    def _on_type_changed(self, _idx: int) -> None:
        row_idx = self.list_widget.currentRow()
        if row_idx < 0:
            return
        # Save what's there and instantiate new type
        tid = self.cbo_type.currentData()
        cls = support_registry().get(tid)
        if cls is None:
            return
        row = self._rows[row_idx]
        row.support = cls()
        row.orientation = cls.DEFAULT_ORIENTATION
        row.force_application = cls.DEFAULT_APPLICATION
        self.lbl_desc.setText(cls.DESCRIPTION)
        item = self.list_widget.item(row_idx)
        item.setText(self._row_label(row))
        # Rebuild editor
        self.param_panel.set_type(cls, current_values=row.support.__dict__)
        # Sync the application / orientation combos
        self.cbo_app.blockSignals(True)
        idx = self.cbo_app.findData(row.force_application)
        if idx >= 0:
            self.cbo_app.setCurrentIndex(idx)
        self.cbo_app.blockSignals(False)
        self.cbo_ori.blockSignals(True)
        idx = self.cbo_ori.findData(row.orientation)
        if idx >= 0:
            self.cbo_ori.setCurrentIndex(idx)
        self.cbo_ori.blockSignals(False)

    def _on_app_changed(self, _idx: int) -> None:
        row_idx = self.list_widget.currentRow()
        if row_idx < 0:
            return
        self._rows[row_idx].force_application = self.cbo_app.currentData()

    def _on_ori_changed(self, _idx: int) -> None:
        row_idx = self.list_widget.currentRow()
        if row_idx < 0:
            return
        ori = self.cbo_ori.currentData()
        self._rows[row_idx].orientation = ori
        self.spn_user_angle.setEnabled(ori == ForceOrientation.USER_DEFINED)

    def _on_user_angle_changed(self, val: float) -> None:
        row_idx = self.list_widget.currentRow()
        if row_idx < 0:
            return
        self._rows[row_idx].user_angle_deg = val

    def _add_row(self) -> None:
        # Commit current row first
        cur = self.list_widget.currentRow()
        if cur >= 0:
            self._commit_row(cur)
        row = self._make_default_row()
        row.name = f"Type {len(self._rows) + 1}"
        self._rows.append(row)
        self.list_widget.addItem(self._row_label(row))
        self.list_widget.setCurrentRow(len(self._rows) - 1)

    def _duplicate_row(self) -> None:
        cur = self.list_widget.currentRow()
        if cur < 0:
            return
        self._commit_row(cur)
        src = self._rows[cur]
        cls = type(src.support)
        new_support = cls(**src.support.__dict__)
        new_row = _SupportRow(
            name=src.name + " (copy)",
            support=new_support,
            force_application=src.force_application,
            orientation=src.orientation,
            user_angle_deg=src.user_angle_deg,
            color=src.color,
        )
        self._rows.append(new_row)
        self.list_widget.addItem(self._row_label(new_row))
        self.list_widget.setCurrentRow(len(self._rows) - 1)

    def _delete_row(self) -> None:
        cur = self.list_widget.currentRow()
        if cur < 0 or len(self._rows) <= 1:
            return
        del self._rows[cur]
        self.list_widget.takeItem(cur)
        new_cur = min(cur, len(self._rows) - 1)
        self.list_widget.setCurrentRow(new_cur)

    # ---- commit & save ------------------------------------------
    def _commit_row(self, row_idx: int) -> None:
        """Apply current editor values into the corresponding _rows entry."""
        if row_idx < 0 or row_idx >= len(self._rows):
            return
        row = self._rows[row_idx]
        # Rebuild the support instance with current panel values
        if self.param_panel._type_cls is None:
            return
        cls = self.param_panel._type_cls
        values = self.param_panel.get_values()
        try:
            row.support = cls(**values)
        except TypeError:
            # Some types like UserDefined have ``points`` only
            row.support = cls(**{k: v for k, v in values.items()
                                  if k in cls.__init__.__code__.co_varnames})

    def accept(self) -> None:
        # Commit the active row
        cur = self.list_widget.currentRow()
        if cur >= 0:
            self._commit_row(cur)
        # Push to project.support_types
        out = []
        for row in self._rows:
            st = row.support
            # Stash extra metadata as private attrs (UI-only fields)
            st._display_name = row.name
            st._force_application = row.force_application
            st._orientation = row.orientation
            st._user_angle_deg = row.user_angle_deg
            st._color = row.color
            out.append(st)
        self.project.support_types = out
        self.project.is_dirty = True
        if hasattr(self.project, "_notify"):
            self.project._notify("support_types_changed")
        super().accept()

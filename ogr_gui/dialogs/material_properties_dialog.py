# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Material properties dialog — polymorphic constitutive-model editor.

Every strength model registered in :mod:`ogr_core.materials.registry`
is available from a combo box. When the user changes the model, the
parameter panel is rebuilt on-the-fly from ``PARAMETERS`` — so newly
added plugins appear automatically.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
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
    QVBoxLayout,
    QWidget,
)

from ogr_core.materials import (
    REGISTRY,
    Material,
    PorePressureType,
    StrengthModel,
)
from ogr_gui.i18n import tr

from .drawdown_strength_dialog import DrawdownStrengthDialog, envelope_summary


# ----------------------------------------------------------------------
#: The strength models that can read an anisotropic surface. v0.1.225
#: (D218) — the rule lives in ``ogr_core.project.rules`` so the API asks the
#: same one; Generalized Anisotropic left it that version, because its
#: ranges are absolute slice base inclinations.
from ogr_core.project.rules import (  # noqa: E402
    SURFACE_READING_MODEL_IDS as _ANISOTROPIC_MODEL_IDS,
)


def _exact_text(value: float) -> str:
    """The shortest text that reads back as exactly ``value``.

    ``repr`` of a float is that text by definition; the trailing ``.0`` of a
    whole number is dropped because it adds nothing a reader needs.
    """
    text = repr(float(value))
    return text[:-2] if text.endswith(".0") else text


class _PreciseSpinBox(QDoubleSpinBox):
    """A spin box that keeps the number it is given, to the last bit.

    v0.1.192 (D181) — the strength-parameter editors were plain spin boxes
    with four decimals, and ``QDoubleSpinBox.setValue`` ROUNDS to its
    decimals. The dialog rebuilds the strength from its editors whenever a
    material is stored, so opening it and pressing OK without touching
    anything rewrote every parameter at four decimals: the Hoek-Brown ``s``
    of a GSI-10 rock mass, 4.54e-5, came back 0.0 — and with it the tensile
    strength s*sigci/mb that v0.1.191 grants rock (5.65 kPa -> 0). Every
    GSI up to 13 was lost entirely, and GSI 20 lost 29 % of its ``s``.

    The fix is not "more decimals": any fixed count loses the small values
    of some parameter. The box stores at Qt's maximum precision, so
    ``setValue`` no longer rounds anything a double can hold, and shows the
    shortest text that reads back exactly (``_exact_text``) — so even a box
    that re-reads its own text on losing focus gets the same number back.
    Typed input accepts scientific notation (``4.54e-5``), which a
    fixed-decimal box cannot show at all.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # Qt caps decimals at DBL_MAX_10_EXP + DBL_DIG = 323, which is
        # enough for its internal round() to return every double as is.
        self.setDecimals(323)

    def _bare(self, text: str) -> str:
        """``text`` without prefix, suffix and surrounding spaces."""
        prefix, suffix = self.prefix(), self.suffix()
        if prefix and text.startswith(prefix):
            text = text[len(prefix):]
        if suffix and text.endswith(suffix):
            text = text[:-len(suffix)]
        return text.strip()

    def textFromValue(self, value: float) -> str:          # noqa: N802
        return _exact_text(value).replace(".", self.locale().decimalPoint())

    def valueFromText(self, text: str) -> float:           # noqa: N802
        bare = self._bare(text).replace(self.locale().decimalPoint(), ".")
        try:
            return float(bare)
        except ValueError:
            return self.value()

    def validate(self, text: str, pos: int):
        from PySide6.QtGui import QValidator

        bare = self._bare(text).replace(self.locale().decimalPoint(), ".")
        try:
            value = float(bare)
        except ValueError:
            # "", "-", "1e", "1e-" ... are on the way to a number.
            return QValidator.State.Intermediate, text, pos
        if not (self.minimum() <= value <= self.maximum()):
            return QValidator.State.Intermediate, text, pos
        return QValidator.State.Acceptable, text, pos


class _StrengthParamPanel(QWidget):
    """Dynamically-built parameter editor for the active strength model.

    v0.1.13 — unit-aware. Each parameter's canonical unit (declared in
    ``PARAMETERS``) is mapped to a :class:`Quantity` and the editor shows
    the value in the active project unit system. Conversion happens in
    ``set_model`` (SI → user) and ``get_params`` (user → SI).

    v0.1.227 (D217) — the tables too, and nothing moves that nobody
    edited:

    * a table's cells are in the quantity of their column (a stress in the
      project's stress unit, an angle in degrees), converted with the same
      function as the parameters, under a translated header that names the
      unit (``_TABLE_COLUMNS``). They were kPa under a fixed "(kPa)" header
      whatever the project's units;
    * what the panel was given is kept beside what it shows: a value, or a
      whole table, whose display was not changed goes back EXACTLY as it
      came in. Converting to the user's unit and back loses up to an ulp
      (x·f/f), so every OK in imperial units used to rewrite every value;
      and ``is_unchanged`` lets the dialog keep a strength it did not edit
      as it is -- a table saved before 0.1.218 is then not converted just
      by being looked at (D209's warning asked for a review, not this);
    * a row that is not numbers is reported for every table, not only the
      anisotropic function's, and an empty stored table is shown empty
      rather than replaced by the default.
    """

    # Map the literal SI unit string declared in builtin_models to the
    # corresponding Quantity. Used for display + conversion only.
    _UNIT_TO_QUANTITY = {
        "kPa":     "pressure",
        # v0.1.120 — a cohesion gradient is stress per length, which is
        # the quantity the imperial system already spells psf/ft. Without
        # this entry it would fall through to "dimensionless" and reach a
        # project in feet unconverted.
        "kPa/m":   "joint_stiffness",
        "kN/m³":   "unit_weight",
        "kN/m²":   "shear_strength",
        "kN":      "force",
        "kNm":     "moment",
        "deg":     "angle",
        "m":       "length",
        "mm":      "very_small_length",
        "1/m":     "one_over_length",
        "-":       "dimensionless",
        "":        "dimensionless",
    }

    #: v0.1.227 (D217) — each table's columns: the ``tr()`` key of the
    #: header (a ``%s`` takes the unit label of the column's quantity) and
    #: the quantity of its cells. The keys are translated through a
    #: variable, so a test guards that each has its Spanish entry.
    _TABLE_COLUMNS = {
        "points": (("Normal stress (%s)", "pressure"),
                   ("Shear strength (%s)", "pressure")),
        "rows3": (("Angle to (°)", "angle"),
                  ("Cohesion (%s)", "pressure"),
                  ("Friction angle (°)", "angle")),
        # v0.1.228 (D218b) — the Generalized Anisotropic ranges: the angle
        # each one ends at and the material it takes, a choice and not a
        # quantity (None).
        "rules": (("Angle to (°)", "angle"),
                  ("Material", None)),
        # v0.1.248 (D231a) — the joints of "Angle or Surface": the angle of
        # each joint, its A and B (read by the A and B mapping only) and the
        # material it takes.
        "joints": (("Joint angle (°)", "angle"),
                   ("Half-width A (°)", "angle"),
                   ("Transition end B (°)", "angle"),
                   ("Material", None)),
        # v0.1.249 (D231b) — the same, each joint along an anisotropic
        # surface of the model, a choice ("surface") and not a quantity.
        "joints_surface": (("Anisotropic surface", "surface"),
                           ("Half-width A (°)", "angle"),
                           ("Transition end B (°)", "angle"),
                           ("Material", None)),
        # v0.1.229 (D215) — the C/Phi function: (σ'ₙ, c, φ) rows.
        "cphi": (("Normal stress (%s)", "pressure"),
                 ("Cohesion (%s)", "pressure"),
                 ("Friction angle (°)", "angle")),
        # v0.1.246 (D229) — the Discrete Function: a field over (x, y), of
        # cu (undrained) or of c and φ (drained), in the project's units.
        "discrete_cu": (("X (%s)", "length"), ("Y (%s)", "length"),
                        ("Cohesion cu (%s)", "pressure")),
        "discrete_cphi": (("X (%s)", "length"), ("Y (%s)", "length"),
                          ("Cohesion (%s)", "pressure"),
                          ("Friction angle (°)", "angle")),
    }

    #: v0.1.228 (D218b) — the caption of each table.
    _TABLE_CAPTIONS = {"points": "Function points:",
                       "rows3": "Function points:",
                       "rules": "Angle ranges:",
                       "joints": "Joints:",
                       "joints_surface": "Joints:",
                       "cphi": "Function points:",
                       "discrete_cu": "Data points:",
                       "discrete_cphi": "Data points:"}

    #: v0.1.246 (D229) — the Discrete Function's two choices, as the
    #: reference's dialog offers them (the methods this program has).
    _DISCRETE_TYPES = (("undrained", "Undrained (phi = 0)"),
                       ("drained", "Drained (c, phi)"))
    _DISCRETE_METHODS = (("inverse_distance", "Inverse Distance"),
                         ("tin", "TIN Triangulation"),
                         ("thin_plate_spline", "Thin Plate Spline"),
                         ("linear_by_elevation", "Linear by Elevation"))

    #: v0.1.248 (D231a) — the choices of a Generalized Anisotropic function,
    #: as the reference's dialog offers them.
    _GA_INPUTS = (("angle_range", "Angle Range"),
                  ("angle_or_surface", "Angle or Surface"))
    _GA_DEFINITIONS = (("angle", "Angle"), ("surface", "Surface"))
    _GA_MAPPINGS = (("ab", "A and B"), ("cosine", "Cosine"),
                    ("linear", "Linear"))
    _GA_SELECTIONS = (("worst_case", "Worst case"), ("closest", "Closest"))
    #: The fields of each input: what the other input holds is carried
    #: through unchanged while one of them is on screen.
    _GA_RANGE_KEYS = ("rules", "use_parent_water")
    _GA_JOINT_KEYS = ("base", "joints", "definition", "mapping",
                      "joint_selection", "use_base_if_weaker")

    #: v0.1.229 (D215) — the two strength functions of a Snowden material:
    #: the button that opens each one and the title of its dialog.
    _FUNCTION_BUTTONS = (
        ("bedding", "Bedding Strength Function...",
         "Define Bedding Strength Function"),
        ("rock_mass", "Rock Mass Strength Function...",
         "Define Rock Mass Strength Function"),
    )

    def __init__(self, parent=None, units_obj=None) -> None:
        super().__init__(parent)
        self._form = QFormLayout(self)
        self._editors: dict[str, QDoubleSpinBox] = {}
        self._param_quantity: dict[str, str] = {}  # name → quantity_id
        self._model_cls: type[StrengthModel] | None = None
        self._units_obj = units_obj  # ogr_core.project.units.Units or None
        # v0.1.227 (D217) — what each editor was given (SI) and showed.
        self._given: dict[str, tuple[float, float]] = {}
        self._table = None
        self._table_kind = None
        self._table_given = None     # the rows as given (SI)
        self._table_shown = None     # the cell texts as first shown
        self._chk_cutoff = None
        self._cutoff_given = None
        # v0.1.228 (D218b) — (id, name, strength dict) of the materials a
        # Generalized Anisotropic range can take; see ``set_rule_materials``.
        self._rule_choices: list = []
        # v0.1.229 (D215) — a Snowden material's two strength functions, as
        # given and as they stand, and the label that sums each one up.
        self._functions = None
        self._functions_given = None
        self._function_labels: dict = {}
        # v0.1.246 (D229) — the Discrete Function's type and method combos,
        # and what they were given.
        self._discrete = None
        # v0.1.247 (D230) — a Generalized Anisotropic material's «water
        # parameters of the parent» switch, and what it was given.
        self._chk_parent_water = None
        self._parent_water_given = None
        # v0.1.248 (D231a) — the Generalized Anisotropic editor's controls.
        self._ga = None
        # v0.1.249 (D231b) — (id, label) of the model's anisotropic
        # surfaces, and, per material combo of a joints table, the joint it
        # was built from: what the table does not show (the angle of a joint
        # by surface, the surface of a joint by angle) is carried from it.
        self._surface_choices: list = []
        self._joint_given: dict = {}

    def set_anisotropic_surfaces(self, choices) -> None:
        """The anisotropic surfaces a joint can follow, as (id, label)
        (v0.1.249, D231b); the dialog passes them."""
        self._surface_choices = [(str(i), str(n)) for i, n in choices]

    def set_rule_materials(self, choices) -> None:
        """The materials a Generalized Anisotropic range can take, as (id,
        name, strength dict): every material of the project but the one
        being edited and the Generalized Anisotropic ones (v0.1.228, D218b).
        The dialog passes them because this panel knows nothing of the
        other materials."""
        self._rule_choices = [(str(i), str(n), s) for i, n, s in choices]

    def set_units(self, units_obj) -> None:
        """Update the active unit system (e.g. project settings changed).
        Repopulates the editors converting their current SI values to
        the new display system."""
        old_si_values = self.get_params() if self._editors else None
        self._units_obj = units_obj
        if self._model_cls is not None:
            self.set_model(self._model_cls, old_si_values)

    def _active_system(self):
        """Return the active UnitSystem (detailed) or None."""
        if self._units_obj is None:
            return None
        try:
            return self._units_obj.get_system()
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _si_to_user(si_value: float, quantity_id: str, sys_obj) -> float:
        """An SI value in the unit the editor shows. One function for
        ``set_model``, ``set_param_values`` and the tables, so they cannot
        convert differently."""
        from ogr_core.units import Quantity
        if sys_obj is not None and quantity_id != "dimensionless":
            try:
                return sys_obj.to_user(si_value, Quantity(quantity_id))
            except (ValueError, KeyError):
                pass
        return si_value

    @staticmethod
    def _user_to_si(user_value: float, quantity_id: str, sys_obj) -> float:
        """The inverse of :meth:`_si_to_user`."""
        from ogr_core.units import Quantity
        if sys_obj is not None and quantity_id != "dimensionless":
            try:
                return sys_obj.from_user(user_value, Quantity(quantity_id))
            except (ValueError, KeyError):
                pass
        return user_value

    def _unit_label(self, quantity_id: str, fallback: str = "") -> str:
        from ogr_core.units import Quantity
        sys_obj = self._active_system()
        if sys_obj is not None and quantity_id != "dimensionless":
            try:
                return sys_obj.label_for(Quantity(quantity_id))
            except (ValueError, KeyError):
                pass
        return fallback

    def set_param_values(self, values: dict) -> None:
        """Write SI ``values`` into the editors of the current model.

        v0.1.192 (D176) — the parameter calculator used to look its editors
        up in ``_widgets``, an attribute this panel never had, so
        ``getattr(..., {})`` handed it an empty dict and every value was
        skipped without a word: accepting the calculator changed nothing.
        A name with no editor now RAISES instead of being skipped, because
        skipping silently is exactly how that went unnoticed.
        """
        missing = sorted(k for k in values if k not in self._editors)
        if missing:
            raise KeyError(
                f"no editor for {missing} in "
                f"{getattr(self._model_cls, 'MODEL_ID', '?')}; "
                f"editors: {sorted(self._editors)}")
        sys_obj = self._active_system()
        for name, si_value in values.items():
            quantity_id = self._param_quantity.get(name, "dimensionless")
            self._editors[name].setValue(
                self._si_to_user(float(si_value), quantity_id, sys_obj))

    def set_model(
        self,
        model_cls: type[StrengthModel],
        current_params: dict | None = None,
    ) -> None:
        """Build editors. ``current_params`` are values in SI (canonical
        units stored on the material)."""
        self._model_cls = model_cls
        # Clear
        while self._form.count():
            item = self._form.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._editors.clear()
        self._param_quantity.clear()
        self._given.clear()

        current_params = current_params or {}
        sys_obj = self._active_system()

        for name, (default, unit, description) in model_cls.PARAMETERS.items():
            quantity_id = self._UNIT_TO_QUANTITY.get(unit, "dimensionless")
            self._param_quantity[name] = quantity_id

            # SI value (always)
            si_value = float(current_params.get(name, default))
            # Convert to display
            user_value = self._si_to_user(si_value, quantity_id, sys_obj)
            user_label = self._unit_label(quantity_id,
                                          unit if unit != "-" else "")

            # v0.1.192 (D181) — was a QDoubleSpinBox with 4 decimals, which
            # rounded every value it was given; see ``_PreciseSpinBox``.
            ed = _PreciseSpinBox()
            ed.setRange(-1e12, 1e12)
            ed.setSuffix(f" {user_label}" if user_label else "")
            ed.setValue(user_value)
            ed.setToolTip(description)
            label = QLabel(f"{name}:")
            label.setToolTip(description)
            self._form.addRow(label, ed)
            self._editors[name] = ed
            self._given[name] = (si_value, ed.value())

        if not model_cls.PARAMETERS:
            self._form.addRow(QLabel(tr("(no parameters)")))

        # v0.1.15 — function/table-based models (Shear/Normal Function,
        # Discrete Function, Anisotropic Strength Function) carry a table
        # instead of (or in addition to) numeric PARAMETERS.
        self._table = None
        self._table_kind = None
        self._table_given = None
        self._table_shown = None
        self._functions = None
        self._functions_given = None
        self._function_labels = {}
        self._discrete = None
        self._chk_parent_water = None
        self._parent_water_given = None
        self._ga = None
        self._joint_given = {}
        mid = getattr(model_cls, "MODEL_ID", "")
        if mid == "discrete_function":
            self._build_discrete(current_params, model_cls)
        elif mid in ("shear_normal_function", "step_function"):
            # v0.1.227 (D217) — each model's own default table: the discrete
            # function used to show the shear-normal one.
            self._build_points_table(current_params, kind="points",
                                     default=list(model_cls.DEFAULT_POINTS))
        elif mid == "anisotropic_strength_function":
            # v0.1.218 (D209) — each row is a RANGE, (angle to, c, φ), as
            # the reference documents the strength type; the default is
            # the model's own, not a second copy of it.
            self._build_points_table(current_params, kind="rows3",
                                     default=list(model_cls.DEFAULT_ROWS))
        elif mid == "c_phi_function":
            # v0.1.229 (D215) — (σ'ₙ, c, φ) rows, in the project's units.
            self._build_points_table(current_params, kind="cphi",
                                     default=list(model_cls.DEFAULT_ROWS))
        elif mid == "generalized_anisotropic":
            self._build_generalized(current_params, model_cls)

        if mid == "snowden_anisotropic_linear":
            self._build_function_buttons(current_params, model_cls)

        # v0.1.120 — the depth-dependent undrained models carry ONE piece
        # of state that is not a number: whether the cutoff applies at
        # all. A spinbox showing 0 or 1 would be a worse control than a
        # checkbox, and the value alone cannot encode "off" — zero is a
        # legitimate minimum when the rate is negative.
        self._chk_cutoff = None
        self._cutoff_given = None
        if getattr(model_cls, "_C_REF", None) is not None and \
                "cutoff" in model_cls.PARAMETERS:
            self._build_cutoff_switch(
                bool(current_params.get("cutoff_enabled", False)))
            self._cutoff_given = self._chk_cutoff.isChecked()

    def _build_discrete(self, current_params, model_cls) -> None:
        """The Discrete Function's editor (v0.1.246, D229): its function
        type, its interpolation method and its table of points, whose
        columns are those of the type. Changing the type keeps the points:
        a cu becomes a c with φ = 0, and back the c is kept."""
        ftype = current_params.get("function_type", "undrained")
        if ftype not in dict(self._DISCRETE_TYPES):
            ftype = "undrained"
        method = current_params.get("method", "inverse_distance")
        cbo_type = QComboBox()
        for value, label in self._DISCRETE_TYPES:
            cbo_type.addItem(tr(label), value)
        cbo_type.setCurrentIndex(max(0, cbo_type.findData(ftype)))
        cbo_method = QComboBox()
        for value, label in self._DISCRETE_METHODS:
            cbo_method.addItem(tr(label), value)
        cbo_method.setCurrentIndex(max(0, cbo_method.findData(method)))
        cbo_method.setToolTip(tr(
            "Where the method cannot answer (outside the triangles of a "
            "TIN, a spline that cannot be solved), a local thin plate "
            "spline over the ten nearest points does, and inverse "
            "distance where that fails too."))
        self._form.addRow(tr("Function type:"), cbo_type)
        self._form.addRow(tr("Interpolation method:"), cbo_method)
        kind = "discrete_cu" if ftype == "undrained" else "discrete_cphi"
        self._build_points_table(current_params, kind=kind,
                                 default=list(model_cls.DEFAULT_POINTS[ftype]))
        self._discrete = {"type": cbo_type, "method": cbo_method,
                          "given": (ftype, method)}
        cbo_type.currentIndexChanged.connect(
            lambda _i: self._on_discrete_type(model_cls))

    def _on_discrete_type(self, model_cls) -> None:
        """Rebuild the editor with the other type's columns, the points
        carried across."""
        params = self.get_params()
        new = self._discrete["type"].currentData()
        rows = []
        for r in params.get("points", []):
            if new == "drained":
                rows.append(tuple(r[:3]) + ((r[3],) if len(r) > 3
                                            else (0.0,)))
            else:
                rows.append(tuple(r[:3]))
        params["points"] = rows
        params["function_type"] = new
        self.set_model(model_cls, params)

    def _build_generalized(self, current_params, model_cls) -> None:
        """The Generalized Anisotropic editor: its input type and, below it,
        the editor of that input (v0.1.248, D231a). What the other input
        holds is carried through unchanged."""
        input_type = current_params.get("input_type", "angle_range")
        if input_type not in dict(self._GA_INPUTS):
            input_type = "angle_range"
        cbo_input = QComboBox()
        for value, label in self._GA_INPUTS:
            cbo_input.addItem(tr(label), value)
        cbo_input.setCurrentIndex(max(0, cbo_input.findData(input_type)))
        self._form.addRow(tr("Input type:"), cbo_input)
        joints = input_type == "angle_or_surface"
        keep = {k: copy.deepcopy(current_params[k])
                for k in (self._GA_RANGE_KEYS if joints
                          else self._GA_JOINT_KEYS)
                if k in current_params}
        self._ga = {"input": cbo_input, "keep": keep}
        if joints:
            self._build_joints_editor(current_params)
        else:
            # v0.1.228 (D218b) — the reference's "Angle Range" input: each
            # row is the angle a range ends at and the material it takes.
            # A new selection starts with one range, −90° to +90°, taking
            # the first material it can.
            default = ([{"angle_min": -90.0, "angle_max": 90.0,
                         "material_id": self._rule_choices[0][0],
                         "model": copy.deepcopy(self._rule_choices[0][2])}]
                       if self._rule_choices else [])
            self._build_points_table(current_params, kind="rules",
                                     default=default)
            self._build_parent_water(
                bool(current_params.get("use_parent_water", True)))
        self._ga["given"] = self._ga_state()
        cbo_input.currentIndexChanged.connect(
            lambda _i: self._on_ga_input(model_cls))

    def _build_joints_editor(self, current_params) -> None:
        """"Angle or Surface": the base, the definition, the mapping, the
        joint selection, the weaker base and the joints (v0.1.248, D231a).
        A new selection starts with the first material as the base and one
        joint at 0° that takes the first material too."""
        from PySide6.QtWidgets import QCheckBox

        base = current_params.get("base")
        if not isinstance(base, dict):
            base = ({"material_id": self._rule_choices[0][0],
                     "model": copy.deepcopy(self._rule_choices[0][2])}
                    if self._rule_choices else None)
        cbo_base = self._choice_combo("base", base)
        self._form.addRow(tr("Base material:"), cbo_base)

        def combo(options, value, label):
            c = QComboBox()
            for v, text in options:
                c.addItem(tr(text), v)
            c.setCurrentIndex(max(0, c.findData(value)))
            self._form.addRow(tr(label), c)
            return c
        cbo_def = combo(self._GA_DEFINITIONS,
                        current_params.get("definition", "angle"),
                        "Anisotropy definition:")
        # v0.1.249 (D231b) — by surface only when the model has one to
        # follow (a choice that cannot be completed would do nothing).
        item = cbo_def.model().item(cbo_def.findData("surface"))
        if item is not None and not self._surface_choices \
                and cbo_def.currentData() != "surface":
            item.setEnabled(False)
            cbo_def.setToolTip(tr("Draw an anisotropic surface first to "
                                  "define the joints by surface."))
        cbo_map = combo(self._GA_MAPPINGS,
                        current_params.get("mapping", "ab"),
                        "Mapping function:")
        cbo_map.setToolTip(tr(
            "How the strength goes from the joint's to the base's as the "
            "slice base turns away from the joint: A and B as in Anisotropic "
            "Linear, the S-shaped cosine curve (sin² of the offset) or a "
            "straight line from 0 to 90 degrees."))
        cbo_sel = combo(self._GA_SELECTIONS,
                        current_params.get("joint_selection", "worst_case"),
                        "Several joints:")
        cbo_sel.setToolTip(tr(
            "Worst case: the joint that gives the lowest strength. Closest: "
            "the joint most closely aligned with the slice base, the first "
            "of the list on a tie."))
        chk = QCheckBox(tr("Use the base material where it is weaker"))
        chk.setChecked(bool(current_params.get("use_base_if_weaker", True)))
        self._form.addRow("", chk)
        default = ([{"angle": 0.0, "A": 10.0, "B": 20.0,
                     "material_id": self._rule_choices[0][0],
                     "model": copy.deepcopy(self._rule_choices[0][2])}]
                   if self._rule_choices else [])
        if cbo_def.currentData() == "surface":
            for joint in default:
                joint.pop("angle", None)
                if self._surface_choices:
                    joint["surface_id"] = self._surface_choices[0][0]
            kind = "joints_surface"
        else:
            kind = "joints"
        self._build_points_table(current_params, kind=kind, default=default)
        self._ga.update({"base": cbo_base, "base_given": base,
                         "definition": cbo_def, "mapping": cbo_map,
                         "selection": cbo_sel, "weaker": chk})
        cbo_map.currentIndexChanged.connect(
            lambda _i: self._sync_ab_columns())
        cbo_def.currentIndexChanged.connect(
            lambda _i: self.set_model(self._model_cls, self.get_params()))
        self._sync_ab_columns()

    def _sync_ab_columns(self) -> None:
        """A and B are read by the A and B mapping only: with the other two
        their cells cannot be edited (rule 7)."""
        from PySide6.QtCore import Qt
        ga, tbl = self._ga, self._table
        if ga is None or "mapping" not in ga or tbl is None:
            return
        on = ga["mapping"].currentData() == "ab"
        for r in range(tbl.rowCount()):
            for c in (1, 2):
                item = tbl.item(r, c)
                if item is None:
                    continue
                flags = item.flags()
                item.setFlags(flags | Qt.ItemIsEditable | Qt.ItemIsEnabled
                              if on else
                              flags & ~Qt.ItemIsEditable & ~Qt.ItemIsEnabled)

    def _ga_state(self):
        """What the Generalized editor's own controls hold, comparable."""
        ga = self._ga
        if ga is None:
            return None
        out = [ga["input"].currentData()]
        for k in ("base", "definition", "mapping", "selection"):
            if k in ga:
                out.append(ga[k].currentData())
        if "weaker" in ga:
            out.append(ga["weaker"].isChecked())
        return tuple(out)

    def _on_ga_input(self, model_cls) -> None:
        """Rebuild the editor for the other input; the fields of both are
        kept."""
        params = self.get_params()
        params["input_type"] = self._ga["input"].currentData()
        self.set_model(model_cls, params)

    def _base_from_combo(self):
        """The base on screen: the material chosen, or the base's own
        model when it keeps it; None when there is nothing to take."""
        by_id = {cid: st for cid, _n, st in self._rule_choices}
        data = self._ga["base"].currentData() or ""
        if data.startswith("material:") and data[9:] in by_id:
            return {"material_id": data[9:],
                    "model": copy.deepcopy(by_id[data[9:]])}
        given = self._ga.get("base_given")
        if data.startswith("own:") and isinstance(given, dict):
            out = copy.deepcopy(given)
            out.pop("material_id", None)
            return out
        return None

    def _joints_from_table(self, sys_obj) -> list:
        """The joints on screen (v0.1.248, D231a): angle, A and B, and the
        material each takes or the model it keeps, as the ranges are read
        by :meth:`_rules_from_table`. v0.1.249 (D231b): by surface, the
        surface instead of the angle; what a row does not show is carried
        from the joint it was built from."""
        by_id = {cid: st for cid, _n, st in self._rule_choices}
        by_surface = self._table_kind == "joints_surface"
        joints = []
        for r, row in enumerate(self._cell_texts()):
            try:
                a, b = (self._user_to_si(float(t), "angle", sys_obj)
                        for t in row[1:3])
                angle = (None if by_surface else
                         self._user_to_si(float(row[0]), "angle", sys_obj))
            except ValueError:
                continue    # reported by ``unparsed_table_rows``
            hidden = self._joint_given.get(self._table.cellWidget(r, 3), {})
            choice = row[3]
            given = None
            if choice.startswith("own:"):
                given = self._table_given[int(choice[len("own:"):])]
            link = (choice[len("material:"):]
                    if choice.startswith("material:") else None)
            if link in by_id:
                joint = {"material_id": link,
                         "model": copy.deepcopy(by_id[link])}
            elif isinstance(given, dict):
                joint = copy.deepcopy(given)
                joint.pop("material_id", None)
            else:
                joint = {}
            if by_surface:
                joint["surface_id"] = row[0]
                if "angle" in hidden:
                    joint["angle"] = hidden["angle"]
            else:
                joint["angle"] = angle
                if hidden.get("surface_id"):
                    joint["surface_id"] = hidden["surface_id"]
            joint["A"], joint["B"] = a, b
            joints.append(joint)
        return joints

    def _surface_combo(self, joint):
        """The anisotropic surface of a joint: the model's surfaces, and the
        one the joint names when it is no longer in the model (OK then
        refuses it with its reason)."""
        combo = QComboBox()
        sid = joint.get("surface_id") if isinstance(joint, dict) else None
        ids = [i for i, _n in self._surface_choices]
        for i, label in self._surface_choices:
            combo.addItem(label, i)
        if sid and sid not in ids:
            combo.addItem(tr("(a surface no longer in the model)"), sid)
        if sid:
            combo.setCurrentIndex(max(0, combo.findData(sid)))
        return combo

    def _build_parent_water(self, checked: bool) -> None:
        """The «water parameters of the parent material» switch of a
        Generalized Anisotropic material (v0.1.247, D230). Greyed out while
        no range takes a material: a range with its own model has no water
        of its own, so the switch would change nothing."""
        from PySide6.QtWidgets import QCheckBox

        chk = QCheckBox(tr("Use the water parameters of the parent material"))
        chk.setChecked(checked)
        chk.setToolTip(tr(
            "Ticked, every slice base takes the water of this material. "
            "Unticked, a base whose range takes a material takes that "
            "material's water (water surface, Hu, Ru, grid, B-bar and "
            "unsaturated strength). The weight is always this material's, "
            "and the rapid drawdown always the range's material's."))
        self._form.addRow("", chk)
        self._chk_parent_water = chk
        self._parent_water_given = checked
        self._sync_parent_water()

    def _sync_parent_water(self) -> None:
        chk = self._chk_parent_water
        if chk is None or self._table is None:
            return
        links = any(str(row[1]).startswith("material:")
                    for row in self._cell_texts())
        chk.setEnabled(links)

    def _build_cutoff_switch(self, enabled: bool) -> None:
        """Checkbox governing the cutoff, and the spinbox it governs.

        Disabling the value rather than hiding it is deliberate: unticking
        the box must not lose what was typed.
        """
        from PySide6.QtWidgets import QCheckBox

        chk = QCheckBox(tr("Apply cutoff"))
        chk.setChecked(enabled)
        chk.setToolTip(tr(
            "The cutoff is a maximum strength; if the rate of change is "
            "negative it is a minimum instead."))
        editor = self._editors.get("cutoff")

        def _sync(*_a):
            if editor is not None:
                editor.setEnabled(chk.isChecked())

        chk.stateChanged.connect(_sync)
        _sync()
        self._form.addRow("", chk)
        self._chk_cutoff = chk

    @staticmethod
    def _table_key(kind) -> str:
        """The stored field a table kind edits: the anisotropic function's
        ranges live in ``rows`` since v0.1.218 (D209), the functions of
        σ'ₙ in ``points``."""
        return {"rows3": "rows", "cphi": "rows", "rules": "rules",
                "joints": "joints",
                "joints_surface": "joints"}.get(kind, "points")

    def table_headers(self) -> list[str]:
        """The headers of the table on screen, as shown."""
        tbl = self._table
        if tbl is None:
            return []
        return [tbl.horizontalHeaderItem(c).text()
                for c in range(tbl.columnCount())]

    def _build_points_table(self, current_params, kind, default):
        """Build an editable table for function-based models."""
        from PySide6.QtWidgets import (
            QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout, QWidget,
        )
        key = self._table_key(kind)
        columns = self._TABLE_COLUMNS[kind]
        # v0.1.227 (D217) — an empty table that was STORED is shown empty
        # (and OK refuses it); the default is only for a new selection.
        pts = (list(current_params[key])
               if current_params and key in current_params else default)
        ncol = len(columns)
        sys_obj = self._active_system()
        headers = []
        for text, quantity_id in columns:
            header = tr(text)
            if "%s" in header:
                header = header % self._unit_label(quantity_id, "kPa")
            headers.append(header)
        tbl = QTableWidget(len(pts), ncol)
        tbl.setHorizontalHeaderLabels(headers)
        tbl.horizontalHeader().setStretchLastSection(True)
        shown = []
        for r, row in enumerate(pts):
            # A rule is shown as (angle to, the material it takes), a joint
            # as (angle, A, B, the material it takes).
            if kind == "rules":
                cells = (row.get("angle_max") if isinstance(row, dict)
                         else None, None)
            elif kind == "joints":
                cells = ((row.get("angle"), row.get("A"), row.get("B"), None)
                         if isinstance(row, dict) else (None,) * 4)
            elif kind == "joints_surface":
                cells = ((None, row.get("A"), row.get("B"), None)
                         if isinstance(row, dict) else (None,) * 4)
            else:
                cells = row
            texts = []
            for c in range(ncol):
                if columns[c][1] is None:
                    combo = self._choice_combo(r, row)
                    tbl.setCellWidget(r, c, combo)
                    texts.append(self._choice_text(combo))
                    if kind in ("joints", "joints_surface"):
                        self._joint_given[combo] = copy.deepcopy(row)
                    continue
                if columns[c][1] == "surface":
                    combo = self._surface_combo(row)
                    tbl.setCellWidget(r, c, combo)
                    texts.append(self._choice_text(combo))
                    continue
                # v0.1.192 (D181) — was f"{:.3f}", which rounded every
                # point to three decimals on the next OK; the exact text
                # of the displayed value round-trips through float().
                try:
                    user = self._si_to_user(float(cells[c]), columns[c][1],
                                            sys_obj)
                    text = _exact_text(user)
                except (TypeError, ValueError):
                    text = ""    # reported by ``unparsed_table_rows``
                texts.append(text)
                tbl.setItem(r, c, QTableWidgetItem(text))
            shown.append(texts)
        self._form.addRow(QLabel(tr(self._TABLE_CAPTIONS[kind])), tbl)
        # Add/remove buttons
        btns = QWidget()
        hl = QHBoxLayout(btns)
        hl.setContentsMargins(0, 0, 0, 0)
        b_add = QPushButton(tr("+ Row"))
        b_del = QPushButton(tr("− Row"))

        def _add():
            r = tbl.rowCount()
            tbl.insertRow(r)
            for c in range(ncol):
                if columns[c][1] is None:
                    tbl.setCellWidget(r, c, self._choice_combo(None, None))
                elif columns[c][1] == "surface":
                    tbl.setCellWidget(r, c, self._surface_combo(
                        {"surface_id": self._surface_choices[0][0]}
                        if self._surface_choices else None))
                else:
                    tbl.setItem(r, c, QTableWidgetItem("0.0"))
            self._sync_parent_water()
            self._sync_ab_columns()

        def _del():
            cur = tbl.currentRow()
            if cur >= 0:
                tbl.removeRow(cur)
            self._sync_parent_water()
        b_add.clicked.connect(_add)
        b_del.clicked.connect(_del)
        hl.addWidget(b_add)
        hl.addWidget(b_del)
        hl.addStretch()
        self._form.addRow("", btns)
        self._table = tbl
        self._table_kind = kind
        self._table_ncol = ncol
        # The rules are kept as they came, dicts and all; the tables of
        # numbers as numbers.
        self._table_given = (copy.deepcopy(pts)
                             if kind in ("rules", "joints", "joints_surface")
                             else
                             [tuple(float(v) for v in row) for row in pts])
        self._table_shown = shown

    # ------------------------------------------------------------------
    # v0.1.228 (D218b) — the material column of the Generalized Anisotropic
    # ranges. Each row offers the materials the dialog passed; a rule that
    # links none of them (its own model, from a file, the API or a script,
    # or a link that no longer resolves) also offers to keep its own model,
    # which is what it shows until another choice is made.
    @staticmethod
    def _model_name(rule) -> str:
        try:
            return REGISTRY.get(rule["model"]["model_id"]).DISPLAY_NAME
        except Exception:  # noqa: BLE001 - any malformed rule: no name
            return "?"

    def _choice_combo(self, index, rule):
        combo = QComboBox()
        link = rule.get("material_id") if isinstance(rule, dict) else None
        ids = [cid for cid, _n, _s in self._rule_choices]
        # v0.1.248 (D231a) — the base of "Angle or Surface" offers to keep
        # its own model only when it has one.
        if index == "base" and not (isinstance(rule, dict)
                                    and rule.get("model")):
            index = None
        if index is not None and link not in ids:
            text = (tr("(own model: %s; its link is broken)") if link else
                    tr("(own model: %s)")) % self._model_name(rule)
            combo.addItem(text, f"own:{index}")
        for cid, cname, _s in self._rule_choices:
            combo.addItem(cname, f"material:{cid}")
        if link in ids:
            combo.setCurrentIndex(combo.findData(f"material:{link}"))
        combo.currentIndexChanged.connect(
            lambda _i: self._sync_parent_water())
        return combo

    @staticmethod
    def _choice_text(combo) -> str:
        data = combo.currentData() if combo is not None else None
        return "" if data is None else str(data)

    def _cell_texts(self) -> list[list[str]]:
        tbl = self._table
        columns = self._TABLE_COLUMNS[self._table_kind]
        out = []
        for r in range(tbl.rowCount()):
            row = []
            for c in range(self._table_ncol):
                if columns[c][1] in (None, "surface"):
                    row.append(self._choice_text(tbl.cellWidget(r, c)))
                    continue
                item = tbl.item(r, c)
                row.append(item.text() if item is not None else "")
            out.append(row)
        return out

    def table_unchanged(self) -> bool:
        """True when the table on screen is the one it was given."""
        if self._table is None:
            return True
        return self._cell_texts() == self._table_shown

    def unparsed_table_rows(self) -> list[int]:
        """The rows (1-based) of the table on screen that are not numbers.

        ``get_params`` cannot store them. For the anisotropic function a
        dropped row would silently merge two ranges into one (v0.1.218,
        D209); for the functions of σ'ₙ it would move the envelope (v0.1.227,
        D217), so the dialog asks before accepting, and before leaving the
        material for another one.
        """
        import math
        if self._table is None:
            return []
        columns = self._TABLE_COLUMNS[self._table_kind]
        bad = []
        for r, row in enumerate(self._cell_texts(), start=1):
            try:
                if not all(math.isfinite(float(t))
                           for c, t in enumerate(row)
                           if columns[c][1] not in (None, "surface")):
                    bad.append(r)
            except ValueError:
                bad.append(r)
        return bad

    def table_columns(self) -> int:
        return self._table_ncol if self._table is not None else 0

    def is_unchanged(self) -> bool:
        """True when no editor, no cell and no switch was changed since the
        panel was given its values (v0.1.227, D217)."""
        for k, ed in self._editors.items():
            if ed.value() != self._given[k][1]:
                return False
        if self._chk_cutoff is not None and \
                self._chk_cutoff.isChecked() != self._cutoff_given:
            return False
        if self._functions is not None and \
                self._functions != self._functions_given:
            return False
        if self._discrete is not None and (
                self._discrete["type"].currentData(),
                self._discrete["method"].currentData()) != \
                self._discrete["given"]:
            return False
        if self._chk_parent_water is not None and (
                self._chk_parent_water.isChecked()
                != self._parent_water_given):
            return False
        if self._ga is not None and self._ga_state() != self._ga["given"]:
            return False
        return self.table_unchanged()

    def get_params(self) -> dict:
        """Return the editor values converted to SI (the storage unit).

        v0.1.227 (D217) — a value whose display was not changed is returned
        exactly as it was given, not converted there and back.
        """
        sys_obj = self._active_system()
        out: dict = {}
        for k, ed in self._editors.items():
            si_given, shown = self._given.get(k, (None, None))
            if si_given is not None and ed.value() == shown:
                out[k] = si_given
                continue
            out[k] = self._user_to_si(ed.value(),
                                      self._param_quantity.get(
                                          k, "dimensionless"), sys_obj)
        # v0.1.15 — read the function table if present
        if self._table is not None:
            key = self._table_key(self._table_kind)
            if self.table_unchanged():
                out[key] = copy.deepcopy(self._table_given)
            elif self._table_kind == "rules":
                out[key] = self._rules_from_table(sys_obj)
            elif self._table_kind in ("joints", "joints_surface"):
                out[key] = self._joints_from_table(sys_obj)
            else:
                columns = self._TABLE_COLUMNS[self._table_kind]
                pts = []
                for row in self._cell_texts():
                    try:
                        pts.append(tuple(
                            self._user_to_si(float(t), columns[c][1],
                                             sys_obj)
                            for c, t in enumerate(row)))
                    except ValueError:
                        # Reported by ``unparsed_table_rows``, which the
                        # dialog asks before it stores anything.
                        continue
                out[key] = pts
        # v0.1.120 — the cutoff switch, for the models that have one.
        if self._chk_cutoff is not None:
            out["cutoff_enabled"] = self._chk_cutoff.isChecked()
        # v0.1.229 (D215) — a Snowden material's two strength functions.
        if self._functions is not None:
            out.update(copy.deepcopy(self._functions))
        # v0.1.246 (D229) — the Discrete Function's type and method.
        if self._discrete is not None:
            out["function_type"] = self._discrete["type"].currentData()
            out["method"] = self._discrete["method"].currentData()
        # v0.1.247 (D230) — the Generalized Anisotropic water switch.
        if self._chk_parent_water is not None:
            out["use_parent_water"] = self._chk_parent_water.isChecked()
        # v0.1.248 (D231a) — the input type, the other input's fields as
        # they came, and the controls of "Angle or Surface".
        ga = self._ga
        if ga is not None:
            for k, v in ga["keep"].items():
                out.setdefault(k, copy.deepcopy(v))
            out["input_type"] = ga["input"].currentData()
            if "base" in ga:
                out["base"] = self._base_from_combo()
                out["definition"] = ga["definition"].currentData()
                out["mapping"] = ga["mapping"].currentData()
                out["joint_selection"] = ga["selection"].currentData()
                out["use_base_if_weaker"] = ga["weaker"].isChecked()
        return out

    def _rules_from_table(self, sys_obj) -> list:
        """The ranges on screen as rules (v0.1.228, D218b).

        Each range starts where the one before it ends and the first at
        −90°, the structure of the reference's "Angle Range" input, so the
        table holds only where each one ends. A range that takes a material
        carries its id and a copy of its strength, which the analysis
        replaces with the material's strength when it runs
        (``prepare_analysis_project``); one that keeps its own model keeps
        the rule it was given, without a link.
        """
        by_id = {cid: s for cid, _n, s in self._rule_choices}
        rules, lo = [], -90.0
        for row in self._cell_texts():
            try:
                hi = self._user_to_si(float(row[0]), "angle", sys_obj)
            except ValueError:
                continue    # reported by ``unparsed_table_rows``
            choice = row[1]
            given = None
            if choice.startswith("own:"):
                given = self._table_given[int(choice[len("own:"):])]
            link = (choice[len("material:"):]
                    if choice.startswith("material:") else None)
            if link in by_id:
                rule = {"material_id": link,
                        "model": copy.deepcopy(by_id[link])}
            elif isinstance(given, dict):
                rule = copy.deepcopy(given)
                rule.pop("material_id", None)
            else:
                # Nothing to take (no other material in the project): a
                # range without a model, which OK refuses with its reason.
                rule = {}
            rule["angle_min"], rule["angle_max"] = lo, hi
            rules.append(rule)
            lo = hi
        return rules

    # ------------------------------------------------------------------
    # v0.1.229 (D215) — Snowden's bedding and rock mass strength functions.
    # Each is edited in a dialog of its own (the reference's "Bedding
    # Strength Function" and "Rock Mass Strength Function" buttons); the
    # panel keeps the two dicts and a label that sums each one up.
    def _build_function_buttons(self, current_params, model_cls) -> None:
        current_params = current_params or {}
        given = {}
        for which, text, _title in self._FUNCTION_BUTTONS:
            default = (model_cls.DEFAULT_BEDDING if which == "bedding"
                       else model_cls.DEFAULT_ROCK_MASS)
            given[which] = copy.deepcopy(current_params.get(which, default))
            btn = QPushButton(tr(text))
            btn.clicked.connect(
                lambda _checked=False, w=which: self._open_function(w))
            label = QLabel("")
            label.setStyleSheet("color: #555; font-style: italic;")
            self._form.addRow(btn, label)
            self._function_labels[which] = label
        self._functions = given
        self._functions_given = copy.deepcopy(given)
        for which in given:
            self._refresh_function_label(which)

    @staticmethod
    def function_summary(function) -> str:
        """What a strength function is, in a few words: its kind and the
        size of its table."""
        try:
            cls = REGISTRY.get(function["model_id"])
        except Exception:  # noqa: BLE001 - a function a file broke
            return tr("(not a valid function)")
        table = function.get("rows", function.get("points")) or []
        return tr("%s, %d row(s)") % (cls.DISPLAY_NAME, len(table))

    def _refresh_function_label(self, which: str) -> None:
        label = self._function_labels.get(which)
        if label is not None and self._functions is not None:
            label.setText(self.function_summary(self._functions[which]))

    def function(self, which: str) -> dict:
        """The ``"bedding"`` or ``"rock_mass"`` function as it stands."""
        return copy.deepcopy(self._functions[which])

    def set_function(self, which: str, function: dict) -> None:
        """Replace one of the two functions (what the function dialog's OK
        does; a test calls it without the dialog)."""
        self._functions[which] = copy.deepcopy(function)
        self._refresh_function_label(which)

    def _open_function(self, which: str) -> None:
        title = next(t for w, _b, t in self._FUNCTION_BUTTONS if w == which)
        dlg = StrengthFunctionDialog(self._functions[which],
                                     units_obj=self._units_obj,
                                     title=tr(title), parent=self)
        if dlg.exec():
            self.set_function(which, dlg.result_function())

    def current_model(self) -> type[StrengthModel] | None:
        return self._model_cls


# ----------------------------------------------------------------------
class StrengthFunctionDialog(QDialog):
    """The bedding or the rock mass strength function of a Snowden material
    (v0.1.229, D215).

    The reference documentation offers two kinds, a "Shear-Normal function"
    (τ at each σ'ₙ) and a "Cohesion-Friction function" (c and φ at each
    σ'ₙ), which are this program's shear-normal and C/Phi functions: the
    dialog is a choice of kind and that model's table, in the project's
    units, with the same checks as the material dialog. OK is
    :meth:`_accept_if_valid`, so a test drives the dialog without
    ``exec()``. A table left as it was comes back exactly as it came in.
    """

    KINDS = (("shear_normal_function", "Shear-Normal function"),
             ("c_phi_function", "Cohesion-Friction function"))

    def __init__(self, function, units_obj=None, title: str = "",
                 parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self._given = copy.deepcopy(function)
        self._result = None
        lay = QVBoxLayout(self)
        self.cbo_kind = QComboBox()
        for mid, text in self.KINDS:
            self.cbo_kind.addItem(tr(text), mid)
        lay.addWidget(self.cbo_kind)
        self.panel = _StrengthParamPanel(units_obj=units_obj)
        lay.addWidget(self.panel)
        self.lbl_problem = QLabel("")
        self.lbl_problem.setWordWrap(True)
        self.lbl_problem.setStyleSheet("color: #b00020;")
        self.lbl_problem.setVisible(False)
        lay.addWidget(self.lbl_problem)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

        mid = function.get("model_id") if isinstance(function, dict) else None
        known = mid in dict(self.KINDS)
        self._given_kind = mid if known else None
        self.cbo_kind.setCurrentIndex(
            self.cbo_kind.findData(mid if known else "c_phi_function"))
        table = {k: v for k, v in (function or {}).items()
                 if k in ("points", "rows")} if known else {}
        self.panel.set_model(REGISTRY.get(self.cbo_kind.currentData()), table)
        if not known:
            self._show(tr("This function is not a shear-normal or a C/Phi "
                          "function; a new one is shown."))
        self.cbo_kind.currentIndexChanged.connect(self._on_kind)

    def _show(self, text: str) -> None:
        self.lbl_problem.setText(text)
        self.lbl_problem.setVisible(bool(text))

    def _on_kind(self, _index) -> None:
        self.panel.set_model(REGISTRY.get(self.cbo_kind.currentData()))
        self._show("")

    def _accept_if_valid(self) -> bool:
        from ogr_core.materials.builtin_models import ShearNormalFunction
        from ogr_core.project.rules import (c_phi_rows_refusal,
                                            function_points_refusal)
        bad = self.panel.unparsed_table_rows()
        if bad:
            self._show(tr("Row %d of the table is not %d numbers.")
                       % (bad[0], self.panel.table_columns()))
            return False
        kind = self.cbo_kind.currentData()
        if kind == self._given_kind and self.panel.is_unchanged():
            self._result = copy.deepcopy(self._given)
            self.accept()
            return True
        model = REGISTRY.get(kind)(**self.panel.get_params())
        why = (function_points_refusal(model.points)
               if isinstance(model, ShearNormalFunction)
               else c_phi_rows_refusal(model.rows))
        if why is not None:
            self._show(tr(MaterialPropertiesDialog._TABLE_REFUSALS.get(
                why.code, why.message)))
            return False
        self._result = model.to_dict()
        self.accept()
        return True

    def result_function(self):
        """The function the dialog was accepted with, or None."""
        return copy.deepcopy(self._result)


# ----------------------------------------------------------------------
class MaterialPropertiesDialog(QDialog):
    """Editor for the full list of materials in a project."""

    def __init__(
        self,
        materials: list[Material],
        parent=None,
        units_obj=None,
        gw_method: str = "none",
        has_water_table: bool = False,
        water_surfaces: list[tuple[str, str]] | None = None,
        anisotropic_surfaces: list[tuple[str, str]] | None = None,
        rapid_drawdown: bool = False,
        drawdown_method: str = "b_bar",
        excess_pore_pressure: bool = False,
        material_uses: dict | None = None,
    ) -> None:
        super().__init__(parent)
        # v0.1.286 (D287) — {material id: (region assignments, weak
        # layers)}, from rules.material_region_uses, handed in like the
        # water surfaces: this dialog knows nothing of a Project.
        self._material_uses = dict(material_uses or {})
        # v0.1.62 — (boundary id, translated label) for every water table
        # and piezometric line in the project. Passed in rather than read
        # from a Project so this dialog keeps knowing nothing about one,
        # the same way ``has_water_table`` is a derived flag.
        self._water_surfaces = list(water_surfaces or [])
        # v0.1.126 — (boundary id, label) for every anisotropic surface in
        # the project, passed in for the same reason the water surfaces
        # are: this dialog knows nothing about a Project.
        self._aniso_surfaces = list(anisotropic_surfaces or [])
        self._rapid_drawdown = bool(rapid_drawdown)
        # v0.1.72 — which of the four procedures is configured. B̄ and the
        # undrained envelope belong to different ones, so the dialog needs
        # to know which before it can show only the relevant field.
        self._drawdown_method = str(drawdown_method or "b_bar")
        # v0.1.75 — the OTHER advanced groundwater option. Mutually
        # exclusive with the drawdown, so at most one of the two
        # groups is ever on screen.
        self._excess_pore_pressure = bool(excess_pore_pressure)
        # v0.1.29 — the unsaturated-strength fields are only meaningful
        # (and only shown) when the groundwater method is an FEA, since
        # only then can pore pressures be negative.
        self._gw_method = str(gw_method)
        # v0.1.60 — a saturated unit weight can only mean something if a
        # water table exists to separate the saturated zone from the rest.
        self._has_water_table = bool(has_water_table)
        self.setWindowTitle(tr("Define Materials..."))
        self.resize(720, 500)
        # v0.1.60 — work on deep copies, so the user can move freely
        # between materials and still have Cancel discard everything. A
        # shallow ``list(materials)`` shared the Material instances with
        # the project, which made Cancel a no-op for field edits.
        # ``deepcopy`` rather than ``from_dict(to_dict())`` because it also
        # preserves each material's ``id`` (region assignments key off it)
        # and any attribute set outside the dataclass, such as ``b_bar``.
        self.materials = [copy.deepcopy(m) for m in materials]
        # v0.1.225 (D218) — each material's strength as it came in, so OK
        # judges only the strengths this session changed: a material whose
        # model the dialog cannot edit (Generalized Anisotropic rules), and
        # that was merely looked at, must not block accepting other edits.
        # The analysis still refuses it.
        self._strength_on_entry = {
            m.id: self._strength_state(m) for m in self.materials}
        self._current_row = -1
        self._units_obj = units_obj  # ogr_core.project.units.Units

        layout = QHBoxLayout(self)

        # Left: material list
        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.setMaximumWidth(200)
        for m in self.materials:
            self._append_item(m)
        self.list.currentRowChanged.connect(self._on_select)
        btn_add = QPushButton("+ " + tr("Name"))
        btn_add.setText(tr("+ Add"))
        btn_add.clicked.connect(self._add_material)
        btn_del = QPushButton(tr("− Remove"))
        btn_del.clicked.connect(self._remove_material)
        left.addWidget(self.list, 1)
        hb = QHBoxLayout()
        hb.addWidget(btn_add)
        hb.addWidget(btn_del)
        left.addLayout(hb)
        layout.addLayout(left)

        # Right: editor form
        right = QVBoxLayout()

        # Identity group
        gen_grp = QGroupBox(tr("General"))
        gen_form = QFormLayout(gen_grp)
        self._general_form = gen_form
        self.ed_name = QLineEdit()
        self.btn_color = QPushButton()
        self.btn_color.setFixedWidth(60)
        self.btn_color.clicked.connect(self._pick_color)
        self._color_hex = "#d4a373"
        self._update_color_button()
        # γ and γ_sat: display in active system, store internally in kN/m³.
        gamma_label, gamma_factor = self._unit_weight_label_factor()
        self._gamma_label = gamma_label
        self._gamma_factor = gamma_factor
        # v0.1.227 (D217) — every number of the material in a box that does
        # not round (D181 fixed the strength parameters and left these at 2
        # to 4 decimals), and what each box was given kept beside what it
        # shows (``_put_si``/``_get_si``), so an OK in another unit system
        # does not move a value nobody edited.
        self._si_shown: dict = {}
        self._pressure_label, self._pressure_factor = \
            self._quantity_label_factor("pressure", "kPa")
        self.dsp_gamma = _PreciseSpinBox()
        self.dsp_gamma.setRange(0.0, 1e6)
        self.dsp_gamma.setSuffix(f" {gamma_label}")
        self.dsp_gamma_sat = _PreciseSpinBox()
        self.dsp_gamma_sat.setRange(0.0, 1e6)
        self.dsp_gamma_sat.setSuffix(f" {gamma_label}")
        # v0.1.60 — the saturated unit weight is opt-in, and the option is
        # only offered when a water table exists: without one there is no
        # boundary between the saturated and unsaturated zones, so the
        # value could not be applied anywhere.
        self.chk_gamma_sat = QCheckBox(tr("Saturated Unit Weight") + ":")
        self.chk_gamma_sat.setEnabled(self._has_water_table)
        self.chk_gamma_sat.setToolTip(
            tr("Different unit weights above and below the water table. "
               "Requires a water table in the model.")
            if not self._has_water_table else
            tr("Saturated bulk unit weight, used below the water table. "
               "It is not the submerged (buoyant) unit weight, so it "
               "should be greater than the unit weight above.")
        )
        self.chk_gamma_sat.toggled.connect(self._on_gamma_sat_toggled)
        # Non-modal warning: the saturated BULK unit weight must exceed the
        # unsaturated one. The value is still accepted — this only says so.
        self.lbl_gamma_sat_warn = QLabel(
            tr("The saturated unit weight should be greater than the "
               "unit weight above the water table."))
        self.lbl_gamma_sat_warn.setStyleSheet("color: #b00020;")
        self.lbl_gamma_sat_warn.setWordWrap(True)
        self.lbl_gamma_sat_warn.setVisible(False)
        self.dsp_gamma.valueChanged.connect(self._refresh_gamma_warning)
        self.dsp_gamma_sat.valueChanged.connect(self._refresh_gamma_warning)
        gen_form.addRow(tr("Name") + ":", self.ed_name)
        gen_form.addRow(tr("Color") + ":", self.btn_color)
        gen_form.addRow(tr("Unit Weight") + ":", self.dsp_gamma)
        gen_form.addRow(self.chk_gamma_sat, self.dsp_gamma_sat)
        gen_form.addRow("", self.lbl_gamma_sat_warn)

        # v0.1.29 — Unsaturated shear strength (extended Mohr-Coulomb).
        # The reference only exposes these when the groundwater method is
        # a finite-element analysis, because only then can the pore
        # pressures be negative. Both default to 0, so matric suction
        # contributes nothing unless the user opts in.
        self.dsp_phi_b = _PreciseSpinBox()
        self.dsp_phi_b.setRange(0.0, 89.0)
        self.dsp_phi_b.setSingleStep(1.0)
        self.dsp_phi_b.setSuffix(" °")
        self.dsp_phi_b.setToolTip(tr(
            "Unsaturated shear strength angle. 0 means matric suction "
            "does not contribute to strength (conservative default)."))
        # v0.1.227 (D217) — a suction is a pressure, in the project's unit.
        self.dsp_aev = _PreciseSpinBox()
        self.dsp_aev.setRange(0.0, 1e7)
        self.dsp_aev.setSingleStep(5.0)
        self.dsp_aev.setSuffix(f" {self._pressure_label}")
        self.dsp_aev.setToolTip(tr(
            "Air entry value: matric suction below which the saturated "
            "friction angle still governs (bilinear envelope)."))
        self._row_phi_b = gen_form.rowCount()
        gen_form.addRow(tr("Unsaturated Shear Strength Angle") + ":",
                        self.dsp_phi_b)
        gen_form.addRow(tr("Air Entry Value") + ":", self.dsp_aev)
        self._unsat_widgets = [self.dsp_phi_b, self.dsp_aev]
        self._apply_unsaturated_visibility()
        right.addWidget(gen_grp)

        # Strength group
        str_grp = QGroupBox(tr("Strength Type"))
        str_layout = QVBoxLayout(str_grp)
        # Top row: dropdown + formula label
        top_row = QHBoxLayout()
        self.cbo_strength = QComboBox()
        for mid, cls in REGISTRY.all().items():
            self.cbo_strength.addItem(cls.DISPLAY_NAME, mid)
        self.cbo_strength.currentIndexChanged.connect(self._on_strength_changed)
        top_row.addWidget(self.cbo_strength)
        # Formula label, shown next to the dropdown
        self.lbl_strength_formula = QLabel("")
        self.lbl_strength_formula.setStyleSheet(
            "color: #444; font-style: italic; padding-left: 12px;"
        )
        self.lbl_strength_formula.setMinimumWidth(220)
        top_row.addWidget(self.lbl_strength_formula, stretch=1)
        # v0.1.57 — the GSI calculator, shown only for the Generalised
        # Hoek-Brown criterion, whose mb, s and a are DERIVED quantities.
        self.btn_gsi = QPushButton(tr("GSI..."))
        self.btn_gsi.setToolTip(tr(
            "Calculate mb, s and a from GSI, the intact rock constant mi "
            "and the disturbance factor D."))
        self.btn_gsi.clicked.connect(self._open_parameter_calculator)
        self.btn_gsi.setVisible(False)
        top_row.addWidget(self.btn_gsi)
        str_layout.addLayout(top_row)
        self.param_panel = _StrengthParamPanel(units_obj=self._units_obj)
        str_layout.addWidget(self.param_panel)

        # v0.1.126 — which anisotropic surface orients this material's
        # bedding. Shown ONLY for the models that read it (two since
        # v0.1.225): offering it beside Mohr-Coulomb would be a control that
        # decides nothing, which this project counts as worse than not
        # having one.
        self._aniso_row = QWidget()
        _aniso_lay = QHBoxLayout(self._aniso_row)
        _aniso_lay.setContentsMargins(0, 0, 0, 0)
        self.lbl_aniso = QLabel(tr("Anisotropic Surface:"))
        self.cbo_aniso = QComboBox()
        self.cbo_aniso.addItem(tr("(none - use the angle above)"), None)
        for sid, label in self._aniso_surfaces:
            self.cbo_aniso.addItem(label, sid)
        self.cbo_aniso.setToolTip(tr(
            "Polyline that gives the bedding orientation point by point, "
            "for folded anisotropy. The angle is read at the CLOSEST point "
            "of the polyline, not the one directly above."))
        _aniso_lay.addWidget(self.lbl_aniso)
        _aniso_lay.addWidget(self.cbo_aniso, 1)
        str_layout.addWidget(self._aniso_row)
        self._aniso_row.setVisible(False)

        # v0.1.218 (D209) — what is wrong with the strength table on screen:
        # a table saved as interpolated points before 0.1.218, or ranges
        # that OK refuses. A label and not a message box, so nothing modal
        # stands between a test and the dialog.
        self.lbl_strength_problem = QLabel("")
        self.lbl_strength_problem.setWordWrap(True)
        self.lbl_strength_problem.setStyleSheet("color: #b00020;")
        self.lbl_strength_problem.setVisible(False)
        str_layout.addWidget(self.lbl_strength_problem)

        right.addWidget(str_grp)

        # Water parameters — named after what the reference calls this
        # section. "Pore pressure" is the quantity; these are the inputs
        # that determine it, and only some of them apply at a time.
        pp_grp = QGroupBox(tr("Water Parameters"))
        self.grp_water = pp_grp
        pp_form = QFormLayout(pp_grp)
        self._water_form = pp_form
        self.cbo_pp = QComboBox()
        for t in PorePressureType:
            self.cbo_pp.addItem(t.value, t)
        self.dsp_ru = _PreciseSpinBox(); self.dsp_ru.setRange(0.0, 1.0)
        # v0.1.227 (D217) — a pressure, in the project's unit; it was kPa
        # under a fixed " kPa" whatever the units.
        self.dsp_u = _PreciseSpinBox(); self.dsp_u.setRange(0.0, 1e6)
        self.dsp_u.setSuffix(f" {self._pressure_label}")

        # v0.1.62 — which water surface this material takes its pore
        # pressure from. The field existed and was honoured by the solver
        # since v0.1.7, but nothing in the interface ever wrote it, so
        # every project silently fell back to "the first one of that type"
        # and a second piezometric line was unreachable.
        self.cbo_water_surface = QComboBox()
        self.cbo_water_surface.addItem(tr("(first of this type)"), None)
        for wid, label in self._water_surfaces:
            self.cbo_water_surface.addItem(label, wid)
        self.cbo_water_surface.setToolTip(tr(
            "Water surface this material takes its pore pressure from. "
            "It must span every abscissa the material occupies."))

        # Hu: unchecked means "use the project default", which is why this
        # is a checkbox and not a spinbox with a magic value — the same
        # pattern the saturated unit weight above already uses.
        self.chk_hu = QCheckBox(tr("Hu coefficient") + ":")
        self.dsp_hu = _PreciseSpinBox()
        self.dsp_hu.setRange(0.0, 1.0)
        self.dsp_hu.setValue(1.0)
        self.chk_hu.setToolTip(tr(
            "u = γw · Hu · h, with h the vertical distance up to the "
            "water surface. Unchecked, the project default applies."))
        self.chk_auto_hu = QCheckBox(tr("Auto Hu (cos²α from the water-surface slope)"))
        self.chk_auto_hu.setToolTip(tr(
            "Assumes the equipotential through the slice base is straight, "
            "which is exact only for an infinite slope."))

        # v0.1.72 — the per-material way out of a water pressure grid.
        # Only shown when the project actually uses one, because that is
        # the only time it decides anything.
        self.chk_use_grid = QCheckBox(tr("Use the water pressure grid"))
        self.chk_use_grid.setChecked(True)
        self.chk_use_grid.setToolTip(tr(
            "With the grid off, this material takes its pore pressure "
            "from its own water parameters instead of the grid."))

        pp_form.addRow(tr("Type:"), self.cbo_pp)
        pp_form.addRow("", self.chk_use_grid)
        pp_form.addRow(tr("Water Surface:"), self.cbo_water_surface)
        pp_form.addRow(self.chk_hu, self.dsp_hu)
        pp_form.addRow("", self.chk_auto_hu)
        pp_form.addRow(tr("Ru coefficient:"), self.dsp_ru)
        pp_form.addRow(tr("Constant u:"), self.dsp_u)
        right.addWidget(pp_grp)

        # v0.1.62 — Rapid drawdown parameters. B̄ used to be read off the
        # material with getattr, defaulting to 1.0, which made EVERY
        # material undrained without anyone choosing it.
        # v0.1.72 — the whole group is gone unless a rapid drawdown is
        # configured. It used to be permanently on screen and merely
        # greyed out, which cost every other user a quarter of the dialog
        # for a parameter almost nobody sets. Hiding it is not losing it:
        # the analysis that needs it is what brings it back, which is the
        # same route the reference takes.
        rd_grp = QGroupBox(tr("Rapid Drawdown Parameters"))
        self.grp_drawdown = rd_grp
        rd_form = QFormLayout(rd_grp)
        self._drawdown_form = rd_form
        self.chk_undrained = QCheckBox(tr("Undrained Behaviour"))
        self.dsp_b_bar = _PreciseSpinBox()
        self.dsp_b_bar.setRange(0.0, 5.0)
        self.dsp_b_bar.setToolTip(tr(
            "Skempton's B̄: Δu = B̄ · Δσv. Only a material that behaves "
            "undrained retains excess pore pressure after drawdown."))
        # v0.1.68 — the undrained envelope the multi-stage procedures need.
        # v0.1.72 — it moved behind this button, where the reference keeps
        # it. The summary beside the button means the value is still
        # readable without opening anything.
        self.btn_envelope = QPushButton(tr("Define Strength..."))
        self.btn_envelope.clicked.connect(self._open_drawdown_strength)
        self.btn_envelope.setToolTip(tr(
            "Undrained envelope from isotropically consolidated undrained "
            "tests. Needed by the multi-stage drawdown procedures."))
        self.lbl_envelope = QLabel("")
        self.lbl_envelope.setStyleSheet("color: #555; font-style: italic;")
        # The envelope being edited for the material on screen. Staged the
        # same way ``_color_hex`` is: ``_load`` fills it, ``_store`` writes
        # it back, so Cancel still discards everything.
        self._envelope = None

        rd_form.addRow("", self.chk_undrained)
        rd_form.addRow(tr("B-bar:"), self.dsp_b_bar)
        rd_form.addRow(self.btn_envelope, self.lbl_envelope)
        right.addWidget(rd_grp)

        # v0.1.75 — Excess pore pressure from undrained LOADING, which is
        # a different analysis from the drawdown above and exclusive with
        # it, so it gets its own group with its own gate. Deliberately
        # held back in v0.1.72, when its engine did not exist: an
        # interface for a calculation nobody performs is the fault the
        # partial factors had for five versions.
        ex_grp = QGroupBox(tr("Excess Pore Pressure"))
        self.grp_excess = ex_grp
        ex_form = QFormLayout(ex_grp)
        self.dsp_b_bar_excess = _PreciseSpinBox()
        self.dsp_b_bar_excess.setRange(0.0, 5.0)
        self.dsp_b_bar_excess.setToolTip(tr(
            "Skempton's B̄: Δu = B̄ · Δσv. Use 0 for a free-draining "
            "material, which then develops no excess however much load "
            "arrives."))
        self.chk_weight_excess = QCheckBox(
            tr("Material weight creates excess pore pressure"))
        self.chk_weight_excess.setToolTip(tr(
            "This material's weight loads the materials BENEATH it. It "
            "is a separate question from whether this material develops "
            "excess itself, which is its own B-bar: an embankment over a "
            "clay foundation usually has this on and B-bar = 0."))
        ex_form.addRow(tr("B-bar:"), self.dsp_b_bar_excess)
        ex_form.addRow("", self.chk_weight_excess)
        right.addWidget(ex_grp)

        self.cbo_pp.currentIndexChanged.connect(self._refresh_water_parameters)
        self.chk_use_grid.toggled.connect(self._refresh_water_parameters)
        self.chk_hu.toggled.connect(self._refresh_water_parameters)
        self.chk_auto_hu.toggled.connect(self._refresh_water_parameters)
        self.chk_undrained.toggled.connect(self._refresh_water_parameters)
        self.cbo_strength.currentIndexChanged.connect(
            self._refresh_water_parameters)

        right.addStretch(1)
        layout.addLayout(right, 1)

        # Buttons — v0.1.60: no Apply. Edits are committed to the working
        # copy as soon as the user moves to another material, so Apply had
        # nothing left to do; OK confirms the whole list, Cancel drops it.
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._ok)
        self.buttons.rejected.connect(self.reject)
        right.addWidget(self.buttons)

        if self.materials:
            self.list.setCurrentRow(0)
        else:
            self._set_editor_enabled(False)

    # ------------------------------------------------------------------
    def _append_item(self, m: Material) -> None:
        item = QListWidgetItem(m.name)
        item.setData(Qt.UserRole, m.id)
        item.setForeground(QColor(m.color))
        self.list.addItem(item)

    def _set_editor_enabled(self, on: bool) -> None:
        for w in (self.ed_name, self.btn_color, self.dsp_gamma,
                  self.cbo_strength, self.cbo_pp, self.param_panel):
            w.setEnabled(on)
        # γsat has its own gate on top of this one: the checkbox needs a
        # water table, and the spinbox needs the checkbox.
        self.chk_gamma_sat.setEnabled(on and self._has_water_table)
        self.dsp_gamma_sat.setEnabled(
            on and self._has_water_table and self.chk_gamma_sat.isChecked())
        if not on:
            self.lbl_gamma_sat_warn.setVisible(False)
        self._editor_on = on
        self._refresh_water_parameters()

    # ------------------------------------------------------------------
    # Strength models for which the reference disables water parameters
    # outright: not one of them reads a pore pressure, so offering the
    # inputs would suggest an influence that does not exist (rule 7).
    # v0.1.120 — the three depth-dependent undrained models join the list
    # for the same reason as the first: φ = 0 and τ = c(z), so no pore
    # pressure enters the strength.
    _NO_WATER_STRENGTHS = ("undrained", "no_strength", "infinite_strength",
                           "undrained_depth_layer", "undrained_depth_datum",
                           "undrained_slope_distance")

    @staticmethod
    def _set_row_visible(form: QFormLayout, field: QWidget,
                         visible: bool) -> None:
        """Show or hide a form row, label included.

        ``QFormLayout.setRowVisible`` only arrived in Qt 6.4, and
        ``labelForField`` returns whatever was passed as the row's first
        element — a QLabel for a string, or the widget itself when the row
        was built from two widgets — so this works for both shapes.
        """
        label = form.labelForField(field)
        if label is not None:
            label.setVisible(visible)
        field.setVisible(visible)

    def _refresh_water_parameters(self, *_args) -> None:
        """Show only the water parameters that decide something.

        Two layers, and they are different on purpose. What the PROJECT
        makes irrelevant is HIDDEN — a grid switch in a project with no
        grid, or the whole group under a finite-element analysis, where
        the reference replaces it with the unsaturated parameters. What
        the MATERIAL's own choice makes irrelevant is merely DISABLED, so
        that changing the type back shows the value that was there.
        """
        on = getattr(self, "_editor_on", True)
        ppt = self.cbo_pp.currentData()
        uses_surface = ppt in (PorePressureType.WATER_TABLE,
                               PorePressureType.PIEZO_LINE)

        # A finite-element analysis supplies the pore pressures itself;
        # the material contributes phi_b and the air entry value instead,
        # which live in the General group and have their own gate.
        fea = self._gw_method in ("fea_steady", "fea_transient")
        self.grp_water.setVisible(not fea)

        # The grid switch decides nothing unless the project uses a grid.
        grid = self._gw_method in ("grid_total_head", "grid_pressure_head",
                                   "grid_pore_pressure")
        self._set_row_visible(self._water_form, self.chk_use_grid, grid)
        self.chk_use_grid.setEnabled(on)
        # With the grid governing, the material's own model is what
        # applies only after switching the grid off.
        own_model = on and (not grid or not self.chk_use_grid.isChecked())

        # Rule of the reference: these strength models read no pore
        # pressure at all, so the whole group is greyed out.
        mid = self.cbo_strength.currentData()
        if mid in self._NO_WATER_STRENGTHS:
            own_model = False
        self.cbo_pp.setEnabled(own_model)

        self.cbo_water_surface.setEnabled(own_model and uses_surface)
        self.chk_auto_hu.setEnabled(own_model and uses_surface)
        self.chk_hu.setEnabled(
            own_model and uses_surface and not self.chk_auto_hu.isChecked())
        self.dsp_hu.setEnabled(
            own_model and uses_surface
            and not self.chk_auto_hu.isChecked()
            and self.chk_hu.isChecked())
        self.dsp_ru.setEnabled(
            own_model and ppt == PorePressureType.RU_COEFFICIENT)
        self.dsp_u.setEnabled(own_model and ppt == PorePressureType.CONSTANT)

        self._refresh_drawdown_group()
        self._refresh_excess_group()

    def _refresh_excess_group(self) -> None:
        """Present only when the project runs the B-bar loading analysis.

        The same rule the drawdown group follows, and for the same
        reason: the analysis that needs these fields is what brings them
        back, and it is switched on somewhere else entirely.
        """
        on = getattr(self, "_editor_on", True)
        self.grp_excess.setVisible(self._excess_pore_pressure)
        for wgt in (self.dsp_b_bar_excess, self.chk_weight_excess):
            wgt.setEnabled(on and self._excess_pore_pressure)

    def _refresh_drawdown_group(self) -> None:
        """Show the drawdown parameters the chosen procedure asks for.

        B̄ and the undrained envelope are alternatives, not companions:
        the effective-stress procedure needs the first and the three
        multi-stage ones need the second. Showing both at once was
        showing every user at least one field their analysis ignores.
        """
        on = getattr(self, "_editor_on", True)
        self.grp_drawdown.setVisible(self._rapid_drawdown)
        if not self._rapid_drawdown:
            # Hidden AND disabled. Hiding alone would be enough for the
            # eye, but the guarantee being made is that B̄ cannot be set
            # without a drawdown run, and that is a statement about the
            # widgets, not about what happens to be on screen.
            for wgt in (self.chk_undrained, self.dsp_b_bar,
                        self.btn_envelope):
                wgt.setEnabled(False)
            return
        undrained = self.chk_undrained.isChecked()
        self.chk_undrained.setEnabled(on)
        multistage = self._drawdown_method != "b_bar"
        self._set_row_visible(self._drawdown_form, self.dsp_b_bar,
                              not multistage)
        self._set_row_visible(self._drawdown_form, self.lbl_envelope,
                              multistage)
        self.dsp_b_bar.setEnabled(on and undrained)
        self.btn_envelope.setEnabled(on and undrained)
        self.lbl_envelope.setText(envelope_summary(self._envelope))

    def _open_drawdown_strength(self) -> None:
        """Edit the undrained envelope of the material on screen."""
        dlg = DrawdownStrengthDialog(self._envelope, self)
        if dlg.exec():
            self._envelope = dlg.envelope()
            self._refresh_drawdown_group()

    def _current_material(self) -> Material | None:
        row = self.list.currentRow()
        if 0 <= row < len(self.materials):
            return self.materials[row]
        return None

    # ------------------------------------------------------------------
    def _on_select(self, row: int) -> None:
        """Commit the material being left, then load the new one.

        v0.1.60 — the commit half used to be missing, so any edit was
        silently discarded unless the user pressed Apply before changing
        the selection.
        """
        if self._current_row >= 0 and self._current_row != row:
            # v0.1.227 (D217) — a table row that is not numbers keeps the
            # material on screen: storing it would drop the row (D209 asked
            # this at OK only). ``currentRowChanged`` arrives AFTER the list
            # moved, so it is put back with its signals blocked, and nothing
            # is reloaded -- a reload would throw away the table being fixed.
            if self._refuse_unparsed_rows():
                self.list.blockSignals(True)
                self.list.setCurrentRow(self._current_row)
                self.list.blockSignals(False)
                return
            self._store(self._current_row)
        self._current_row = row if 0 <= row < len(self.materials) else -1
        if self._current_row < 0:
            self._set_editor_enabled(False)
            return
        self._set_editor_enabled(True)
        self._load(self._current_row)

    def _rule_choices_for(self, parent) -> list:
        """What a Generalized Anisotropic range of ``parent`` can take
        (v0.1.228, D218b): every other material that is not Generalized
        Anisotropic itself, with its strength as it stands in this session.
        The same materials ``rules.generalized_links_refusal`` accepts."""
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        return [(m.id, m.name, m.strength.to_dict()) for m in self.materials
                if m is not parent and not isinstance(
                    getattr(m, "strength", None), GeneralizedAnisotropic)]

    def _load(self, row: int) -> None:
        """Populate the editor widgets from ``self.materials[row]``."""
        m = self.materials[row]
        self.param_panel.set_rule_materials(self._rule_choices_for(m))
        # v0.1.249 (D231b) — the surfaces a joint can follow.
        self.param_panel.set_anisotropic_surfaces(self._aniso_surfaces)
        self.ed_name.setText(m.name)
        self._color_hex = m.color
        self._update_color_button()
        self._populate_gamma(m)
        self.dsp_phi_b.setValue(getattr(m, "phi_b", 0.0) or 0.0)
        self._put_si(self.dsp_aev,
                     getattr(m, "air_entry_value", 0.0) or 0.0,
                     self._pressure_factor)

        idx = self.cbo_strength.findData(m.strength.MODEL_ID)
        if idx >= 0:
            self.cbo_strength.setCurrentIndex(idx)
        # v0.1.120 — ``cutoff_enabled`` rides beside the numeric params,
        # because it is a boolean and PARAMETERS holds only floats.
        _params = dict(m.strength.params)
        if hasattr(m.strength, "cutoff_enabled"):
            _params["cutoff_enabled"] = m.strength.cutoff_enabled
        # v0.1.229 (D215) — Snowden's bedding and rock mass functions.
        for _which in ("bedding", "rock_mass"):
            if isinstance(getattr(m.strength, _which, None), dict):
                _params[_which] = copy.deepcopy(getattr(m.strength, _which))
        # v0.1.246 (D229) — the Discrete Function's type and method, which
        # decide the columns of its table.
        _discrete = {}
        if m.strength.MODEL_ID == "discrete_function":
            _discrete = {"function_type": m.strength.function_type,
                         "method": m.strength.method}
        _params.update(_discrete)
        # v0.1.247 (D230) — the Generalized Anisotropic water switch, and
        # v0.1.248 (D231a) every field of both its inputs.
        _ga = {}
        if m.strength.MODEL_ID == "generalized_anisotropic":
            _ga = {k: copy.deepcopy(v) for k, v in m.strength.to_dict().items()
                   if k not in ("model_id", "params", "rules")}
        _params.update(_ga)
        self.param_panel.set_model(type(m.strength), _params)
        # v0.1.15 — for function/table-based models, also pass the
        # ``points`` so the table editor pre-fills.
        #
        # v0.1.218 (D209) — the anisotropic function keeps its ranges in
        # ``rows``. A table it still holds as interpolated points (a file
        # saved before 0.1.218) is shown as it was written, for the user to
        # review as ranges: the analysis refuses it until then, and the
        # label says why. Accepting the dialog stores what is on screen.
        legacy = getattr(m.strength, "legacy_points", None)
        if self.param_panel._table is not None:
            params_with_pts = dict(m.strength.params)
            if hasattr(m.strength, "rows"):
                params_with_pts["rows"] = list(
                    legacy if legacy is not None else m.strength.rows)
                self.param_panel.set_model(type(m.strength), params_with_pts)
            elif hasattr(m.strength, "points"):
                params_with_pts["points"] = list(m.strength.points)
                params_with_pts.update(_discrete)
                self.param_panel.set_model(type(m.strength), params_with_pts)
            elif isinstance(getattr(m.strength, "rules", None), list):
                # v0.1.228 (D218b) — the Generalized Anisotropic ranges.
                params_with_pts["rules"] = copy.deepcopy(m.strength.rules)
                params_with_pts.update(_ga)
                self.param_panel.set_model(type(m.strength), params_with_pts)
        problem = ""
        if legacy is not None:
            problem = tr(
                "This table was saved as interpolated points by a version "
                "before 0.1.218. Each row is now a range (angle to, c, φ), "
                "as the reference documents this strength type: review it "
                "before accepting.")
        elif getattr(m.strength, "legacy_params", None) is not None:
            # v0.1.229 (D215) — ``SNOWDEN_LEGACY_NOTE``.
            problem = tr(
                "This material was saved by a version before 0.1.229, with "
                "c1, φ1, c2, φ2 and a single B and a cosine transition. The "
                "model is now the reference's: a linear transition between "
                "a bedding and a rock mass strength function, with A1, B1, "
                "A2 and B2. What is shown is the nearest such form, whose "
                "numbers are not the old ones: review it before accepting.")
        elif getattr(m.strength, "MODEL_ID", None) == \
                "generalized_anisotropic" and m.anisotropic_surface_id:
            # v0.1.225 (D218) — ``rules.material_surface_refusal``: the
            # analysis refuses the link until the material is stored here.
            problem = tr(
                "This material links an anisotropic surface. Since 0.1.225 "
                "its ranges are absolute slice base inclinations, measured "
                "from the horizontal, as the reference defines them; before, "
                "the surface's bedding was subtracted first. Accepting keeps "
                "the ranges and removes the link.")
        else:
            # v0.1.227 (D217) — a strength the analysis will refuse (an empty
            # table, rules with a gap) says so as soon as it is shown. OK
            # judges only what the session changed, so this is where the user
            # sees why a run will be refused.
            from ogr_core.project.rules import (
                generalized_links_refusal, strength_model_refusal)
            why = (strength_model_refusal(m.strength, m.name)
                   or generalized_links_refusal(m, self.materials))
            if why is not None:
                problem = (tr("In material %s:") % m.name + " "
                           + self._refusal_text(why))
        self._show_strength_problem(problem)

        # v0.1.126 — the anisotropic surface, restored before the pore
        # pressure so it sits with the strength it belongs to. An id that
        # no longer names a boundary falls back to "(none)", which is what
        # the engine does with it too.
        ai = self.cbo_aniso.findData(
            getattr(m, "anisotropic_surface_id", None))
        self.cbo_aniso.setCurrentIndex(max(0, ai))

        idx = self.cbo_pp.findData(m.pore_pressure)
        if idx >= 0:
            self.cbo_pp.setCurrentIndex(idx)
        self.dsp_ru.setValue(m.ru)
        self._put_si(self.dsp_u, m.constant_u, self._pressure_factor)

        # v0.1.62 — water parameters. Signals are blocked while loading so
        # that populating the widgets cannot write back into the material
        # that is only being displayed.
        _blocked = (self.cbo_water_surface, self.chk_hu, self.chk_auto_hu,
                    self.chk_undrained, self.chk_use_grid,
                    self.chk_weight_excess)
        for w in _blocked:
            w.blockSignals(True)
        idx = self.cbo_water_surface.findData(m.water_surface_id)
        self.cbo_water_surface.setCurrentIndex(max(0, idx))
        self.chk_auto_hu.setChecked(bool(m.auto_hu))
        self.chk_hu.setChecked(m.hu is not None)
        self.dsp_hu.setValue(1.0 if m.hu is None else float(m.hu))
        self.chk_use_grid.setChecked(bool(getattr(m, "use_grid", True)))
        self.chk_undrained.setChecked(bool(m.undrained_behaviour))
        self.dsp_b_bar.setValue(float(m.b_bar))
        # Same B̄ field, shown in whichever group is active.
        self.dsp_b_bar_excess.setValue(float(m.b_bar))
        self.chk_weight_excess.setChecked(
            bool(getattr(m, "weight_creates_excess", False)))
        # v0.1.72 — the envelope is staged rather than shown, because its
        # editor is a dialog of its own now.
        self._envelope = getattr(m, "drawdown_envelope", None)
        for w in _blocked:
            w.blockSignals(False)
        self._refresh_water_parameters()

    # Formula text shown next to each strength type — these mirror the
    # strength-parameter equations the reference displays.
    _FORMULA_TEXT = {
        "mohr_coulomb":         "τ = c′ + σ′ₙ · tan(φ′)",
        "undrained":            "τ = c",
        "no_strength":          "τ = 0",
        "infinite_strength":    "τ = ∞",
        "hoek_brown_classic":   "σ′₁ = σ′₃ + σ_ci · √(m·σ′₃/σ_ci + s)",
        "hoek_brown":           "σ′₁ = σ′₃ + σ_ci · ((m_b·σ′₃/σ_ci + s)^a)",
        "power_curve":          "τ = c + a·(σ′ₙ + d)^b + σ′ₙ · tan(W)",
        "hyperbolic":           "τ = c_∞·σ′ₙ·tan(φ_0) / (c_∞ + σ′ₙ·tan(φ_0))",
        "vertical_stress_ratio":"τ = K · σ′_v",
        # v0.1.15 — strength models added to complete the catalogue
        "barton_bandis":        "τ = σ′ₙ · tan(φ_r + JRC·log₁₀(JCS/σ′ₙ))",
        "drained_undrained":    "τ = min(c′+σ′ₙ·tanφ′,  c′+σ_t·tanφ′)",
        # v0.1.225 (D216) — the TANGENT of φ is interpolated.
        "anisotropic_linear":   "c and tan φ vary linearly with angle to "
                                "bedding",
        "shear_normal_function":"τ = f(σ′ₙ)  (piecewise-linear table)",
        # v0.1.229 (D215) — c and φ interpolated in σ′ₙ.
        "c_phi_function":       "τ = c(σ′ₙ) + σ′ₙ · tan φ(σ′ₙ)  "
                                "(c, φ interpolated)",
        # v0.1.246 (D229) — the step function of σ′ₙ was called Discrete
        # Function until this version; the Discrete Function is the
        # reference's field over the material.
        "step_function":        "τ = f(σ′ₙ)  (step function table)",
        "discrete_function":    "cu(x, y), or c(x, y) + σ′ₙ · tan φ(x, y), "
                                "interpolated",
        # v0.1.218 (D207) — A is added, as the published formula writes it;
        # su_min stays the floor it always was.
        "shansep":              "τ = A + σ′_v · S · OCR^m  (≥ su_min)",
        # v0.1.218 (D209) — constant within each range of base angle.
        "anisotropic_strength_function":
                                "(c, φ) per range of base angle, −90° to +90°",
        # v0.1.225 (D218) — absolute ranges, −90° to +90°; v0.1.228
        # (D218b) — each takes a material, as the reference's input does.
        "generalized_anisotropic":
                                "material per range of base angle, "
                                "−90° to +90°",
        # v0.1.229 (D215) — the reference's model.
        "snowden_anisotropic_linear":
                                "τ = (1 − t)·τ_bedding + t·τ_rock mass, t "
                                "linear in the angle to bedding",
        # v0.1.120 — undrained strength varying linearly with depth
        "undrained_depth_layer": "τ = c_top + Δc·(y_top − y)",
        "undrained_depth_datum": "τ = c_datum + Δc·(y_datum − y)",
        "undrained_slope_distance":
                                "τ = c_top + Δc·(distance to slope)",
    }

    def _unit_weight_label_factor(self) -> tuple[str, float]:
        """Return (display_label, kN/m³ → user factor) for the active
        unit system. Defaults to ('kN/m³', 1.0) if no units_obj."""
        if self._units_obj is None:
            return "kN/m³", 1.0
        try:
            from ogr_core.units import Quantity
            sys_obj = self._units_obj.get_system()
            return (
                sys_obj.label_for(Quantity.UNIT_WEIGHT),
                sys_obj.factors[Quantity.UNIT_WEIGHT.value],
            )
        except Exception:  # noqa: BLE001
            return "kN/m³", 1.0

    def _quantity_label_factor(self, quantity_id: str,
                               default_label: str) -> tuple[str, float]:
        """(display label, SI → user factor) of a quantity in the active
        unit system; ``(default_label, 1.0)`` without one (v0.1.227)."""
        if self._units_obj is None:
            return default_label, 1.0
        try:
            from ogr_core.units import Quantity
            q = Quantity(quantity_id)
            sys_obj = self._units_obj.get_system()
            return sys_obj.label_for(q), sys_obj.factors[q.value]
        except Exception:  # noqa: BLE001
            return default_label, 1.0

    def _put_si(self, widget, si_value: float, factor: float) -> None:
        """Show an SI value in the user's unit, and remember both.

        v0.1.227 (D217) — ``_get_si`` returns ``si_value`` EXACTLY while the
        box still shows what this put in it: x·f/f is not x to the last bit,
        so reading back through the factor moved every value of a material
        on every OK in a unit system with a factor other than 1.
        """
        widget.setValue(float(si_value) * factor)
        self._si_shown[widget] = (widget.value(), float(si_value))

    def _get_si(self, widget, factor: float) -> float:
        shown, si = self._si_shown.get(widget, (None, None))
        if shown is not None and widget.value() == shown:
            return si
        return widget.value() / (factor or 1.0)

    def _populate_gamma(self, mat) -> None:
        """Set the γ / γ_sat controls from the material (stored in SI).

        Signals are blocked while repopulating: the spinboxes drive the
        γ_sat warning and the checkbox drives the spinbox's enabled state,
        and neither should fire for values that are merely being loaded.
        """
        for wgt, si in ((self.dsp_gamma, mat.unit_weight),
                        (self.dsp_gamma_sat, mat.sat_unit_weight)):
            wgt.blockSignals(True)
            self._put_si(wgt, si, self._gamma_factor)
            wgt.blockSignals(False)
        self.chk_gamma_sat.blockSignals(True)
        self.chk_gamma_sat.setChecked(bool(mat.use_sat_unit_weight))
        self.chk_gamma_sat.blockSignals(False)
        self.dsp_gamma_sat.setEnabled(
            self._has_water_table and self.chk_gamma_sat.isChecked())
        self._refresh_gamma_warning()

    def _read_gamma(self) -> tuple[float, float, bool]:
        """Read γ, γ_sat (converted to SI) and the γ_sat opt-in flag."""
        f = self._gamma_factor or 1.0
        gamma_si = self._get_si(self.dsp_gamma, f)
        gamma_sat_si = self._get_si(self.dsp_gamma_sat, f)
        return gamma_si, gamma_sat_si, self.chk_gamma_sat.isChecked()

    def _on_gamma_sat_toggled(self, checked: bool) -> None:
        self.dsp_gamma_sat.setEnabled(self._has_water_table and checked)
        self._refresh_gamma_warning()

    def _refresh_gamma_warning(self) -> None:
        """Warn, without blocking, when γ_sat ≤ γ.

        γ_sat is the saturated BULK unit weight, not the submerged one, so
        it must exceed the weight above the water table. The value is left
        as typed — this only makes the inconsistency visible.
        """
        show = (self.chk_gamma_sat.isChecked()
                and self._has_water_table
                and self.dsp_gamma_sat.value() < self.dsp_gamma.value())
        self.lbl_gamma_sat_warn.setVisible(show)

    def _on_strength_changed(self, _) -> None:
        mid = self.cbo_strength.currentData()
        if not mid:
            return
        cls = REGISTRY.get(mid)
        if 0 <= self._current_row < len(self.materials):
            self.param_panel.set_rule_materials(self._rule_choices_for(
                self.materials[self._current_row]))
        self.param_panel.set_model(cls)
        self._show_strength_problem("")
        # Update formula label
        self.lbl_strength_formula.setText(self._FORMULA_TEXT.get(mid, ""))
        # v0.1.57 — the GSI calculator only makes sense for the
        # Generalised Hoek-Brown criterion, whose mb, s and a are derived
        # quantities rather than things to be typed from memory.
        btn = getattr(self, "btn_gsi", None)
        if btn is not None:
            btn.setVisible(mid == "hoek_brown")
        row = getattr(self, "_aniso_row", None)
        if row is not None:
            row.setVisible(mid in _ANISOTROPIC_MODEL_IDS)

    def _open_parameter_calculator(self) -> None:
        """Derive mb, s and a from GSI, mi and D."""
        from .parameter_calculator_dialog import ParameterCalculatorDialog

        dlg = ParameterCalculatorDialog(self)
        if not dlg.exec():
            return
        result = dlg.result_params
        if result is None:
            return
        self._apply_parameter_result(result)

    def _apply_parameter_result(self, result) -> None:
        """Write a calculator result's mb, s and a into the editors.

        v0.1.192 (D176) — apart from the modal ``exec()`` above so a test
        can drive it without a screen. The three are dimensionless, and the
        panel converts anyway, so a future parameter with a unit would not
        need a second path. The formulas are Hoek, Carranza-Torres & Corkum
        (2002), in ``calculate_hoek_brown``; nothing here recomputes them.
        """
        self.param_panel.set_param_values(
            {"mb": result.mb, "s": result.s, "a": result.a})

    def _pick_color(self) -> None:
        c = QColorDialog.getColor(QColor(self._color_hex), self, tr("Color"))
        if c.isValid():
            self._color_hex = c.name()
            self._update_color_button()

    def _update_color_button(self) -> None:
        self.btn_color.setStyleSheet(f"background:{self._color_hex}; border:1px solid #777;")
        self.btn_color.setText("")

    # ------------------------------------------------------------------
    def _store(self, row: int) -> None:
        """Write the editor widgets back into ``self.materials[row]``."""
        if not (0 <= row < len(self.materials)):
            return
        m = self.materials[row]
        m.name = self.ed_name.text().strip() or m.name
        m.color = self._color_hex
        # γ and γ_sat: convert from displayed user-units back to SI (kN/m³)
        m.unit_weight, m.sat_unit_weight, m.use_sat_unit_weight = \
            self._read_gamma()
        m.phi_b = self.dsp_phi_b.value()
        m.air_entry_value = self._get_si(self.dsp_aev, self._pressure_factor)

        mid = self.cbo_strength.currentData()
        cls = REGISTRY.get(mid)
        # v0.1.227 (D217) — a strength nobody edited is kept as it is, not
        # rebuilt from its editors: rebuilding converts a table saved as
        # points before 0.1.218 into ranges just because the material was
        # shown (D209 wanted a review, not that), and any state the editors
        # do not hold would be lost.
        unchanged = (getattr(m.strength, "MODEL_ID", None) == mid
                     and self.param_panel.is_unchanged())
        if not unchanged:
            # v0.1.225 (D218) carried the Generalized Anisotropic rules over
            # here, because rebuilding them from editors that did not hold
            # them left ``rules = []`` and a strength of zero at every base;
            # since v0.1.228 (D218b) the panel edits and returns them.
            m.strength = cls(**self.param_panel.get_params())
        # Only the models that read it keep it. Switching a material away
        # from an anisotropic model has to CLEAR the link, or a strength
        # nobody can see would still be pointing at a polyline.
        m.anisotropic_surface_id = (self.cbo_aniso.currentData()
                                    if mid in _ANISOTROPIC_MODEL_IDS
                                    else None)

        m.pore_pressure = self.cbo_pp.currentData()
        m.ru = self.dsp_ru.value()
        m.constant_u = self._get_si(self.dsp_u, self._pressure_factor)

        # v0.1.62 — water parameters
        m.water_surface_id = self.cbo_water_surface.currentData()
        m.auto_hu = self.chk_auto_hu.isChecked()
        m.hu = self.dsp_hu.value() if self.chk_hu.isChecked() else None
        m.use_grid = self.chk_use_grid.isChecked()
        m.undrained_behaviour = self.chk_undrained.isChecked()
        # B̄ is ONE property of the material, shown in the group the
        # active analysis owns; whichever is on screen is the one
        # that writes it.
        m.b_bar = (self.dsp_b_bar_excess.value()
                   if self._excess_pore_pressure
                   else self.dsp_b_bar.value())
        m.weight_creates_excess = self.chk_weight_excess.isChecked()
        m.drawdown_envelope = self._envelope

        # Refresh list item
        item = self.list.item(row)
        if item is not None:
            item.setText(m.name)
            item.setForeground(QColor(m.color))

    #: v0.1.218 (D209) — what the dialog says for each refusal of
    #: ``rules.anisotropic_function_rows_refusal``. The rule's own messages
    #: are English, like every message of the engine; the interface
    #: translates its own, keyed by the code that never changes wording.
    _TABLE_REFUSALS = {
        "anisotropic_table_empty":
            "The table has no rows: at least one range, ending at +90°, "
            "is needed.",
        "anisotropic_table_not_rows":
            "Every row must be three numbers: angle to, c and φ.",
        "anisotropic_table_strength":
            "The cohesion must be zero or more and the friction angle "
            "between 0° and 90°.",
        "anisotropic_table_start":
            "The first range starts at −90°, so its «angle to» must be "
            "greater than −90°.",
        "anisotropic_table_order":
            "The ranges must be in order: each «angle to» greater than the "
            "one before.",
        "anisotropic_table_end":
            "The last range must end at +90°.",
        # v0.1.225 (D218) — ``rules.generalized_anisotropic_rules_refusal``.
        # v0.1.228 (D218b) — the ranges are edited here, each taking a
        # material, so the messages say so.
        "generalized_rules_empty":
            "A Generalized Anisotropic material needs its ranges, from −90° "
            "to +90°, each taking the strength of a material.",
        "generalized_rules_not_rules":
            "Every rule must be a range of angles with a strength model.",
        "generalized_rules_angles":
            "Each range must go from a lower to a higher angle, between "
            "−90° and +90°.",
        "generalized_rules_start":
            "The first range must start at −90°.",
        "generalized_rules_order":
            "Each range must start where the previous one ends: no gaps and "
            "no overlaps.",
        "generalized_rules_end":
            "The last range must end at +90°.",
        "generalized_rules_model":
            "Every range needs a material, or a strength model that can be "
            "built.",
        # v0.1.228 (D218b) — ``rules.generalized_links_refusal``.
        "generalized_link_missing":
            "A range takes a material that is not in the project: choose "
            "another one.",
        "generalized_link_self":
            "A range cannot take the strength of its own material.",
        "generalized_link_generalized":
            "A range cannot take the strength of another Generalized "
            "Anisotropic material.",
        # v0.1.248–0.1.249 (D231) — ``rules.generalized_angle_or_surface_
        # refusal`` and ``rules.generalized_surfaces_refusal``.
        "generalized_aos_base":
            "The base needs a material, or a strength model that can be "
            "built.",
        "generalized_aos_joints":
            "At least one joint is needed.",
        "generalized_aos_joint_model":
            "Every joint needs a material, or a strength model that can be "
            "built.",
        "generalized_aos_ab":
            "A and B of every joint must satisfy 0 <= A <= B <= 90 degrees.",
        "generalized_aos_joint_surface":
            "Every joint must follow an anisotropic surface.",
        "generalized_surface_missing":
            "A joint follows an anisotropic surface that is not in the "
            "model: choose another one.",
        # v0.1.225 (D216) — ``rules.anisotropic_linear_refusal``.
        "anisotropic_linear_ab":
            "A and B must satisfy 0° ≤ A ≤ B.",
        # v0.1.227 (D217) — ``rules.function_points_refusal``.
        "function_points_empty":
            "The table has no points: at least one (normal stress, shear "
            "strength) point is needed.",
        "function_points_not_points":
            "Every point must be two numbers: normal stress and shear "
            "strength.",
        "function_points_strength":
            "The shear strength must be zero or more.",
        "function_points_order":
            "The normal stresses must increase from one row to the next.",
        # v0.1.229 (D215) — ``rules.c_phi_rows_refusal``.
        "c_phi_rows_empty":
            "The table has no rows: at least one (normal stress, cohesion, "
            "friction angle) row is needed.",
        "c_phi_rows_not_rows":
            "Every row must be three numbers: normal stress, cohesion and "
            "friction angle.",
        "c_phi_rows_strength":
            "The cohesion must be zero or more and the friction angle "
            "between 0° and 90°.",
        "c_phi_rows_order":
            "The normal stresses must increase from one row to the next.",
        # v0.1.229 (D215) — ``rules.snowden_refusal``. The two function
        # codes are followed by the text of their ``cause``.
        "snowden_ab":
            "A1, B1, A2 and B2 must satisfy 0° ≤ A ≤ B ≤ 90° on each side "
            "of the bedding.",
        "snowden_bedding":
            "The bedding strength function is not valid:",
        "snowden_rock_mass":
            "The rock mass strength function is not valid:",
        "snowden_function_type":
            "it must be a shear-normal or a C/Phi function that can be "
            "built.",
    }

    def _refusal_text(self, why) -> str:
        """A refusal in the user's language, by its code; with the text of
        its ``cause`` after it when it has one (v0.1.229)."""
        text = tr(self._TABLE_REFUSALS.get(why.code, why.message))
        cause = getattr(why, "cause", None)
        if cause is not None:
            text += " " + tr(self._TABLE_REFUSALS.get(cause.code,
                                                      cause.message))
        return text

    def _show_strength_problem(self, text: str) -> None:
        self.lbl_strength_problem.setText(text)
        self.lbl_strength_problem.setVisible(bool(text))

    def _refuse_unparsed_rows(self) -> bool:
        """Say so, and answer True, when the table on screen has a row that
        is not numbers (v0.1.227, D217: every table, and before switching
        material as well as at OK)."""
        bad = self.param_panel.unparsed_table_rows()
        if not bad:
            return False
        if self.param_panel._table_kind == "rules":
            # v0.1.228 (D218b) — its one number is where the range ends.
            self._show_strength_problem(
                tr("Row %d of the table: «angle to» is not a number.")
                % bad[0])
            return True
        if self.param_panel._table_kind == "joints":
            # v0.1.248 (D231a) — three numbers and a material.
            self._show_strength_problem(
                tr("Row %d of the table: the angle, A and B must be "
                   "numbers.") % bad[0])
            return True
        if self.param_panel._table_kind == "joints_surface":
            # v0.1.249 (D231b) — a surface, two numbers and a material.
            self._show_strength_problem(
                tr("Row %d of the table: A and B must be numbers.") % bad[0])
            return True
        self._show_strength_problem(
            tr("Row %d of the table is not %d numbers.")
            % (bad[0], self.param_panel.table_columns()))
        return True

    def _missing_joint_surface(self, m):
        """``rules.generalized_surfaces_refusal`` with the surfaces this
        dialog was given (it has no project): a joint by surface naming one
        that is not among them (v0.1.249, D231b)."""
        from types import SimpleNamespace

        from ogr_core.geometry import BoundaryType
        from ogr_core.project.rules import generalized_surfaces_refusal
        fake = SimpleNamespace(boundaries=[
            SimpleNamespace(id=sid, btype=BoundaryType.ANISOTROPIC_SURFACE)
            for sid, _n in self._aniso_surfaces])
        return generalized_surfaces_refusal(m, fake)

    @staticmethod
    def _strength_state(m) -> object:
        """What a material's strength holds, comparable by value."""
        strength = getattr(m, "strength", None)
        try:
            return strength.to_dict()
        except Exception:  # noqa: BLE001 - then it always counts as changed
            return None

    def _ok(self) -> None:
        # v0.1.218 (D209) — a table of ranges that is not one is refused
        # here, with the reason on screen, instead of being accepted and
        # refused later by the analysis. A row that is not three numbers
        # first: storing would drop it, and two ranges would become one.
        if self._refuse_unparsed_rows():
            return
        self._store(self._current_row)
        from ogr_core.project import resolve_generalized_links
        from ogr_core.project.rules import (
            generalized_links_refusal, strength_model_refusal)
        # v0.1.225 (D218) — only a strength this session changed (or a new
        # material) is judged here; see ``_strength_on_entry``.
        changed = set()
        for m in self.materials:
            entry = self._strength_on_entry.get(m.id)
            if entry is None or entry != self._strength_state(m):
                changed.add(m.id)
        # v0.1.228 (D218b) — the copy of a linked material's strength that
        # a Generalized Anisotropic range keeps follows the material, for
        # what is shown and saved; the analysis takes the material's own
        # strength anyway. A range whose material changed is judged too.
        resolve_generalized_links(self.materials)
        for row, m in enumerate(self.materials):
            # v0.1.248 (D231a): the base and the joints link too.
            links = {r.get("material_id")
                     for _k, r in (m.strength.children_items()
                                   if hasattr(m.strength, "children_items")
                                   else ())
                     if isinstance(r, dict)} - {None}
            if m.id not in changed and not (links & changed):
                continue
            why = strength_model_refusal(m.strength, m.name)
            # A table still held as points (or a Snowden material saved
            # before 0.1.229) was not shown or not touched: it stays as it
            # was and the analysis says why it refuses it.
            if why is not None and why.code in ("anisotropic_table_legacy",
                                                "snowden_legacy"):
                continue
            why = why or generalized_links_refusal(m, self.materials)
            # v0.1.249 (D231b) — a joint following a surface the model no
            # longer has.
            if why is None:
                why = self._missing_joint_surface(m)
            if why is None:
                continue
            if row != self._current_row:
                self.list.setCurrentRow(row)
            self._show_strength_problem(
                tr("In material %s:") % m.name + " "
                + self._refusal_text(why))
            return
        self.accept()

    # ------------------------------------------------------------------
    def _add_material(self) -> None:
        from ogr_core.materials import MohrCoulomb  # lazy
        # v0.1.227 (D217) — checked BEFORE anything is added: the new row
        # would move the selection away from a table that cannot be stored.
        if self._current_row >= 0 and self._refuse_unparsed_rows():
            return
        # Commit whatever is on screen first: adding a material moves the
        # selection, which would otherwise drop the pending edits.
        self._store(self._current_row)
        m = Material(
            name=f"Material {len(self.materials) + 1}",
            strength=MohrCoulomb(cohesion=10.0, friction_angle=25.0),
        )
        self.materials.append(m)
        self._append_item(m)
        self.list.setCurrentRow(len(self.materials) - 1)

    def _remove_material(self) -> None:
        row = self.list.currentRow()
        if 0 <= row < len(self.materials):
            # v0.1.228 (D218b) — a material whose strength a Generalized
            # Anisotropic range takes stays until that range takes another:
            # removing it would leave the range pointing at nothing.
            gone = self.materials[row]
            users = [g.name for g in self.materials if g is not gone and any(
                isinstance(r, dict) and r.get("material_id") == gone.id
                for _k, r in (g.strength.children_items()
                              if hasattr(g.strength, "children_items")
                              else ()))]
            if users:
                self._show_strength_problem(
                    tr("%s cannot be removed: the ranges of %s take its "
                       "strength. Change them first.")
                    % (gone.name, ", ".join(users)))
                return
            # v0.1.286 (D287) — and one that regions or weak layers use
            # stays too, as the API's material_delete refuses it
            # (rules.material_users): removed, they pointed at nothing.
            n_regions, n_layers = self._material_uses.get(gone.id, (0, 0))
            if n_regions or n_layers:
                from ogr_core.project.rules import MATERIAL_IN_USE
                self._show_strength_problem(tr(MATERIAL_IN_USE).format(
                    gone.name, n_regions, n_layers))
                return
            # The row about to disappear must not be committed afterwards.
            self._current_row = -1
            del self.materials[row]
            self.list.takeItem(row)
            self._on_select(self.list.currentRow())

    # ------------------------------------------------------------------
    def result_materials(self) -> list[Material]:
        return list(self.materials)

    # ------------------------------------------------------------------
    def _apply_unsaturated_visibility(self) -> None:
        """Show the unsaturated-strength fields only when the groundwater
        method is a finite-element analysis, as the reference does.

        v0.1.72 — the LABELS used to stay behind. The old code looked up
        ``wgt.parentWidget()``, which is the group box rather than the
        label, and then hid the spinbox again; the result was two captions
        floating over nothing. The form layout knows where its labels are,
        so it is the one asked.
        """
        method = getattr(self, "_gw_method", "none")
        show = method in ("fea_steady", "fea_transient")
        form = getattr(self, "_general_form", None)
        for wgt in getattr(self, "_unsat_widgets", []):
            wgt.setEnabled(show)
            if form is not None:
                self._set_row_visible(form, wgt, show)
            else:
                wgt.setVisible(show)
        return show

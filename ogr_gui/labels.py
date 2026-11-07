# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""What the interface calls each internal identifier, in the interface
language.

v0.1.321 (D300). An identifier the ``.ogr`` keeps (``water_table``,
``grid_total_head``, ``bishop_simplified``) is data, and it reached the
screen as data: ``addItem(m.value, m)`` showed ``grid_total_head`` in a
combo in every language, and the name of a method lived in three tables
(Interpret, Project Settings, the report) that did not agree — Interpret
had no entry for Corps of Engineers or Lowe-Karafiath and showed their
identifiers. This module is the one place that names them.

Each table holds the ENGLISH label; the functions return ``tr(label)`` when
called, so the language is read at that moment and a table evaluated at
import does not freeze it. The stored value never changes: the combo keeps
the enum or the identifier as its data.
"""
from __future__ import annotations

from ogr_core.annotations.annotation import AnnotationKind
from ogr_core.geometry import BoundaryType
from ogr_core.geometry.focus import FocusKind
from ogr_core.geometry.tension_crack import WaterLevelMode
from ogr_core.loads.loads import LoadDistribution, LoadOrientation
from ogr_core.materials.material import PorePressureType
from ogr_core.project.settings import (GroundwaterMethod, LEMMethod,
                                       SearchMethod)
from ogr_core.project.units import PermeabilityUnit, TimeUnit
from ogr_core.support import ForceApplication, ForceOrientation

from ogr_gui.i18n import tr

#: The limit-equilibrium methods, by their stored identifier.
METHOD_NAMES = {
    LEMMethod.BISHOP_SIMPLIFIED.value: "Bishop Simplified",
    LEMMethod.JANBU_SIMPLIFIED.value: "Janbu Simplified",
    LEMMethod.JANBU_CORRECTED.value: "Janbu Corrected",
    LEMMethod.ORDINARY_FELLENIUS.value: "Ordinary / Fellenius",
    LEMMethod.SPENCER.value: "Spencer",
    LEMMethod.GLE_MORGENSTERN_PRICE.value: "GLE / Morgenstern-Price",
    LEMMethod.CORPS_OF_ENGINEERS_1.value: "Corps of Engineers #1",
    LEMMethod.CORPS_OF_ENGINEERS_2.value: "Corps of Engineers #2",
    LEMMethod.LOWE_KARAFIATH.value: "Lowe-Karafiath",
}

PORE_PRESSURE = {
    PorePressureType.NONE: "None",
    PorePressureType.WATER_TABLE: "Water Table",
    PorePressureType.PIEZO_LINE: "Piezometric Line",
    PorePressureType.RU_COEFFICIENT: "Ru Coefficient",
    PorePressureType.CONSTANT: "Constant",
    PorePressureType.FEM_SEEPAGE: "Finite Element Seepage",
}

GROUNDWATER_METHOD = {
    GroundwaterMethod.NONE: "None",
    GroundwaterMethod.WATER_TABLE: "Water Table",
    GroundwaterMethod.PIEZO_LINE: "Piezometric Line",
    GroundwaterMethod.RU_COEFFICIENT: "Ru Coefficient",
    GroundwaterMethod.GRID_TOTAL_HEAD: "Water Pressure Grid: Total Head",
    GroundwaterMethod.GRID_PRESSURE_HEAD:
        "Water Pressure Grid: Pressure Head",
    GroundwaterMethod.GRID_PORE_PRESSURE:
        "Water Pressure Grid: Pore Pressure",
    GroundwaterMethod.FEA_STEADY: "Finite Element: Steady State",
    GroundwaterMethod.FEA_TRANSIENT: "Finite Element: Transient",
}

LOAD_ORIENTATION = {
    LoadOrientation.NORMAL_TO_BOUNDARY: "Normal to Boundary",
    LoadOrientation.VERTICAL: "Vertical (default downward)",
    LoadOrientation.HORIZONTAL: "Horizontal (against failure dir.)",
    LoadOrientation.ANGLE_FROM_HORIZONTAL: "Angle from Horizontal",
    LoadOrientation.ANGLE_TO_BOUNDARY: "Angle to Boundary",
}

LOAD_DISTRIBUTION = {
    LoadDistribution.CONSTANT: "Constant",
    LoadDistribution.TRIANGULAR: "Triangular",
    LoadDistribution.TRAPEZOIDAL: "Trapezoidal",
}

#: v0.1.322 — the support's force. Define Support said "Tangent to slip
#: surface" and the other three support dialogs ``value.title()``, "Tangent
#: To Slip": one table now, Define Support's.
FORCE_APPLICATION = {
    ForceApplication.ACTIVE: "Active",
    ForceApplication.PASSIVE: "Passive",
}

FORCE_ORIENTATION = {
    ForceOrientation.TANGENT_TO_SLIP: "Tangent to slip surface",
    ForceOrientation.PARALLEL_TO_SUPPORT: "Parallel to support",
    ForceOrientation.BISECTOR: "Bisector (tangent + parallel)",
    ForceOrientation.HORIZONTAL: "Horizontal",
    ForceOrientation.PERPENDICULAR_TO_PILE: "Perpendicular to pile",
    ForceOrientation.USER_DEFINED: "User-defined angle",
}

#: Symbols that read the same in Spanish stay as they are; the English
#: abbreviations get their entry.
TIME_UNIT = {
    TimeUnit.SECONDS: "s",
    TimeUnit.MINUTES: "min",
    TimeUnit.HOURS: "h",
    TimeUnit.DAYS: "d",
    TimeUnit.MONTHS: "mo",
    TimeUnit.YEARS: "yr",
}

PERMEABILITY_UNIT = {
    PermeabilityUnit.M_S: "m/s",
    PermeabilityUnit.M_DAY: "m/day",
    PermeabilityUnit.M_YEAR: "m/year",
    PermeabilityUnit.CM_S: "cm/s",
    PermeabilityUnit.MM_HOUR: "mm/hour",
}

#: v0.1.370 (D344) — the annotation kinds, as nouns: the status bar said
#: "Añadido line" with the enum's value in it. The menu's actions are verbs
#: ("Dimension Length" is «Acotar longitud»), so the two dimension kinds
#: have their own names here.
ANNOTATION_KIND = {
    AnnotationKind.LINE: "Line",
    AnnotationKind.ARROW: "Arrow",
    AnnotationKind.POLYLINE: "Polyline",
    AnnotationKind.POLYGON: "Polygon",
    AnnotationKind.RECTANGLE: "Rectangle",
    AnnotationKind.CIRCLE: "Circle",
    AnnotationKind.TEXT: "Text",
    AnnotationKind.DIMENSION_LENGTH: "Length dimension",
    AnnotationKind.DIMENSION_ANGLE: "Angle dimension",
    AnnotationKind.DIMENSION_X: "Dimension X",
    AnnotationKind.DIMENSION_Y: "Dimension Y",
    AnnotationKind.AXES: "Axes",
    AnnotationKind.IMAGE: "Image",
}


def _of(table, key) -> str:
    """``tr`` of the label of ``key``; an identifier with no label (a file
    from a newer version, a script) shows as it is rather than raising."""
    text = table.get(key)
    if text is None:
        return str(getattr(key, "value", key))
    return tr(text)


def method_name(method_id) -> str:
    """The name of a limit-equilibrium method, from its identifier (a
    ``LEMMethod`` or its value)."""
    return _of(METHOD_NAMES, getattr(method_id, "value", method_id))


def annotation_kind_label(kind) -> str:
    """The name of an annotation kind (an ``AnnotationKind``), v0.1.370."""
    return _of(ANNOTATION_KIND, kind)


def pore_pressure_label(kind) -> str:
    return _of(PORE_PRESSURE, kind)


def groundwater_method_label(method) -> str:
    return _of(GROUNDWATER_METHOD, method)


def load_orientation_label(orientation) -> str:
    return _of(LOAD_ORIENTATION, orientation)


def load_distribution_label(distribution) -> str:
    return _of(LOAD_DISTRIBUTION, distribution)


def force_application_label(application) -> str:
    return _of(FORCE_APPLICATION, application)


def force_orientation_label(orientation) -> str:
    return _of(FORCE_ORIENTATION, orientation)


#: v0.1.433 (D411) -- the support classes' English names that read
#: differently in Spanish here than elsewhere: «User Defined» is also a
#: permeability model («Definida por el usuario», feminine), and the support
#: type is masculine. Its own key keeps both right.
_SUPPORT_CLASS_KEYS = {"User Defined": "User-defined"}


def _support_class_label(name: str) -> str:
    return tr(_SUPPORT_CLASS_KEYS.get(name, name))


def default_support_name(name):
    """``(class name, " (n)")`` when ``name`` is the name a support set is
    born with -- the ENGLISH ``DISPLAY_NAME`` of any registered class, as
    the window and the agent write it, with « (n)» for a second one
    (``ogr_api/ops/supports.py``) -- else None. Read from the registry on
    each call, so a class registered later counts."""
    import re
    from ogr_core.support import support_registry
    m = re.fullmatch(r"(.+?)( \(\d+\))?", str(name or ""))
    if not m:
        return None
    names = {cls.DISPLAY_NAME for cls in support_registry().values()}
    if m.group(1) in names:
        return m.group(1), m.group(2) or ""
    return None


def support_type_label(stype) -> str:
    """The name a support type is shown with: the name the user gave the
    set (``_display_name``, data, never translated), else the class's
    ``DISPLAY_NAME`` through tr().

    v0.1.433 (D411) -- a set that keeps the name it was born with (the
    class's English name, « (2)» for the second) is shown by the class's
    name in the interface's language: a set an agent defined without a name
    read «End Anchored» everywhere in Spanish. The stored name is unchanged.

    The class shown is the set's CURRENT class, as ``boundary_label`` shows
    a boundary's current type: any class's name counts as the default, and
    changing a set's class keeps its name (the type combo of Define Support,
    ``support_type_set`` without a name). Found by the review of 0.1.433: a
    set born End Anchored and changed to Grouted Tieback read «Anclado en el
    extremo»."""
    given = getattr(stype, "_display_name", None)
    name = getattr(stype, "DISPLAY_NAME", None)
    if given:
        default = default_support_name(given)
        if default is None:
            return str(given)
        return _support_class_label(name or default[0]) + default[1]
    return (_support_class_label(name) if name
            else str(getattr(stype, "TYPE_ID", "")))


def support_name(support, stype=None) -> str:
    """A placed support's name as the user reads it: the name it was given,
    or, when it carries its set's default name (copied from the class's
    English name), that name in the interface's language; the set's label
    when it has none (v0.1.433, D411)."""
    name = getattr(support, "name", "") or ""
    if name:
        default = default_support_name(name)
        if default is None:
            return name
        # with the set, by its current class, as support_type_label
        current = (getattr(stype, "DISPLAY_NAME", None)
                   if stype is not None else None)
        return _support_class_label(current or default[0]) + default[1]
    return support_type_label(stype) if stype is not None else ""


def boundary_type_label(btype: BoundaryType) -> str:
    return tr(btype.display_name)


#: The English name of every boundary type: the name a boundary is born with.
_DEFAULT_BOUNDARY_NAMES = frozenset(t.display_name for t in BoundaryType)


def boundary_has_given_name(boundary) -> bool:
    """Whether the user named ``boundary``. A boundary is born with its
    type's ENGLISH name as its name (``Boundary.__post_init__``): that name
    is data the ``.ogr`` keeps, and on screen it is the type's name in the
    interface's language.

    Any type's English name counts as the default, not only its own: Convert
    Boundary from the canvas's context menu keeps the old type's name, and so
    did the v0.1.69 migration that swapped the water table and the drawdown
    line. Found by the review of v0.1.432: a water table converted from a
    material boundary said «Contorno eliminado: Material Boundary»."""
    name = getattr(boundary, "name", "")
    return bool(name) and name not in _DEFAULT_BOUNDARY_NAMES


def boundary_label(boundary) -> str:
    """A boundary's name as the user reads it: the name the user gave it,
    else its type's name in the interface's language.

    v0.1.432 (D399) -- the rule ``MainWindow._boundary_label`` held for
    Scale and Rotate, moved here so every place asks it: the status bar's
    messages, a dialog's title and the list of Select Boundary printed the
    stored name instead, in English with the interface in Spanish."""
    if boundary_has_given_name(boundary):
        return boundary_name(boundary)
    return boundary_type_label(boundary.btype)


def boundary_heading(boundary) -> str:
    """The type's name, then the name the user gave the boundary, if any
    (``Contorno de material — Arcilla``): where both are shown, the default
    name would only repeat the type, in English."""
    label = boundary_type_label(boundary.btype)
    if boundary_has_given_name(boundary):
        return "%s — %s" % (label, boundary_name(boundary))
    return label


def _program_names():
    """The names the PROGRAM gives a boundary, in English, as the core
    writes them; imported, not copied, so the two cannot drift."""
    from ogr_core.geometry.expand_shrink import REMOVED_ARC_NAME
    return {REMOVED_ARC_NAME}


def boundary_name(boundary) -> str:
    """A boundary's own name as the user reads it: the one the user gave,
    as it is, or, for a name the program gives (the ground Expand / Shrink
    keeps, «Original ground (from Expand/Shrink)»), its translation
    (v0.1.433, D411). The stored name is unchanged."""
    name = getattr(boundary, "name", "") or ""
    return tr(name) if name in _program_names() else name


#: v0.1.432 (D399) -- the kind of a focus object, as its menu entry names it;
#: Manage Focus Objects listed the stored identifier («1: point (…)»)
FOCUS_KIND = {
    FocusKind.WINDOW: "Focus Window",
    FocusKind.LINE: "Focus Line",
    FocusKind.POINT: "Focus Point",
    FocusKind.TANGENT: "Focus Tangent",
}


def focus_kind_label(kind) -> str:
    return _of(FOCUS_KIND, kind)


def water_surface_label(project, boundary) -> str:
    """The name of a water surface as the interface shows it: «Nivel
    freático» (numbered when the model has more than one) and «Línea
    piezométrica N», by its number among the lines of its type
    (``water_surface_index``, from project order). The translated
    counterpart of ``ogr_core.hydraulic.water_surface_label``, which is
    English for the CLI, logs and DXF.

    v0.1.432 (D399) -- moved from ``MainWindow._water_surface_choices`` so
    the tension crack's dialog names its lines as the material dialog does:
    it showed the stored name, «Piezometric Line» in every language."""
    from ogr_core.hydraulic import water_surface_index
    n = water_surface_index(project, boundary)
    if boundary.btype == BoundaryType.WATER_TABLE:
        total = len(project.boundaries_of(BoundaryType.WATER_TABLE))
        return (tr("Water Table") if total <= 1
                else "%s %d" % (tr("Water Table"), n))
    return "%s %d" % (tr("Piezometric Line"), n)


#: v0.1.432 (D399) -- the water level of a tension crack, in the order its
#: dialog offers them; the window's status bar printed the identifier
#: («Grieta de tracción: percent_filled»)
WATER_LEVEL_MODE = {
    WaterLevelMode.DRY: "Dry — no water",
    WaterLevelMode.FILLED: "Filled — 100% saturated",
    WaterLevelMode.PERCENT_FILLED: "Percent Filled",
    WaterLevelMode.FILLED_BELOW_ELEVATION:
        "Filled below Elevation (absolute Y)",
    WaterLevelMode.FILLED_TO_DEPTH: "Filled to Depth (relative to crack top)",
    WaterLevelMode.USE_WATER_TABLE: "Use Water Table",
    WaterLevelMode.USE_PIEZOMETRIC: "Use Piezometric Line",
}


def water_level_mode_label(mode) -> str:
    return _of(WATER_LEVEL_MODE, mode)


def time_unit_label(unit) -> str:
    return _of(TIME_UNIT, unit)


def permeability_unit_label(unit) -> str:
    return _of(PERMEABILITY_UNIT, unit)


def param_label(key: str) -> str:
    """The short label of a parameter key, as the data tips and the random
    variables show it: the key with spaces (``unit weight``, ``friction
    angle``), which is the English those two have always shown, through
    ``tr``. A key that is a symbol (``mb``, ``phi r``) has no entry and
    reads the same in every language."""
    return tr(str(key).replace("_", " "))


def random_variable_label(rv) -> str:
    """The label a random variable is SHOWN with.

    The ``.ogr`` keeps the label ``ogr_core.statistics.available_variables``
    wrote (``"Clay — friction_angle"``, ``"Clay — hydraulic ks"``,
    ``"seismic kh"``), and it is not touched: this builds the shown text from
    it, keeping the name part as stored and translating the parameter. A
    label that does not have the form the core writes (edited in a file or
    by a script) is shown as it is.
    """
    label = rv.label or rv.key
    kind = getattr(rv.kind, "value", rv.kind)
    param = str(rv.param)
    if kind == "water_table":
        return tr(label)
    if kind == "seismic":
        return (tr("seismic {0}").format(param_label(param))
                if label == "seismic " + param else label)
    head, sep, tail = label.rpartition(" — ")
    if kind == "support":
        # the head is the class's DISPLAY_NAME (or "support"): tr() names
        # it, and a name it does not know comes back as it is
        if sep and tail == param:
            # by the support class's own key: «User Defined» is masculine
            # here (v0.1.433, D411)
            return "%s — %s" % (_support_class_label(head),
                                param_label(param))
        return label
    if not sep:
        return label
    if not head:
        # a load without a name: the core writes " — magnitude"
        head = (tr("Line Load") if kind == "line_load"
                else tr("Distributed Load"))
    if kind == "hydraulic" and tail == "hydraulic " + param:
        return "%s — %s" % (head, tr("hydraulic {0}").format(
            param_label(param)))
    if tail == param:
        return "%s — %s" % (head, param_label(param))
    return label


def measurement_text(x0: float, y0: float, x1: float, y1: float) -> str:
    """What Measure says about two points (v0.1.331, D329a): the distance
    and its two components, in model units. Nothing of it is stored."""
    import math
    return tr("Distance: {0}   Δx: {1}   Δy: {2}").format(
        "%.3f" % math.dist((x0, y0), (x1, y1)), "%.3f" % (x1 - x0),
        "%.3f" % (y1 - y0))


def circle_cells(surface_dict) -> tuple:
    """``(centre x, centre y, radius)`` of a surface as a table writes them,
    to 2 decimals, or «—» for each when the surface is not a circle
    (v0.1.419, D361): the results panel wrote «nan» and Interpret «0.00»
    for a non-circular surface, a number that is not one."""
    from ogr_slip2d.interpretation import slip_circle
    circle = slip_circle(surface_dict)
    if circle is None:
        return ("—", "—", "—")
    return tuple(f"{v:.2f}" for v in circle)


# ---------------------------------------------------------------------------
# v0.1.433 (D411) -- identifiers and default names that reached the screen
# as they are stored.

#: The search methods, as Surface Options names them: the status bar and the
#: Information Viewer printed the identifier («Búsqueda: grid»).
SEARCH_METHOD = {
    SearchMethod.GRID_SEARCH: "Grid Search",
    SearchMethod.SLOPE_SEARCH: "Slope Search",
    SearchMethod.AUTO_REFINE: "Auto Refine Search",
    SearchMethod.BLOCK_SEARCH: "Block Search",
    SearchMethod.PATH_SEARCH: "Path Search",
    SearchMethod.SIMULATED_ANNEALING: "Simulated Annealing",
    SearchMethod.PARTICLE_SWARM: "Particle Swarm Search",
}


def search_method_label(method) -> str:
    """The name of a search method, from the enum or its stored value."""
    try:
        method = SearchMethod(getattr(method, "value", method))
    except ValueError:
        return str(getattr(method, "value", method))
    return _of(SEARCH_METHOD, method)


#: What the Selection Filter lets the pointer pick, by the fields of
#: ``SelectionFilterState``: the status bar printed the field names.
SELECTABLE = {
    "boundaries": "boundaries",
    "vertices": "vertices",
    "materials": "materials",
    "supports": "supports",
    "loads": "loads",
    "surfaces": "slip surfaces",
}


def project_label(project) -> str:
    """The project's name as the user reads it: its own, or, for the two
    names the PROGRAM gives (a new project, the demo), their translation.
    By the owner's decision (D411), as for a boundary's default name in
    D399: the ``.ogr`` and the agent keep «Untitled»; a name the user gave
    is data and is shown as it is. Accepts a project or a name."""
    from ogr_core.project.demo import DEMO_PROJECT_NAME
    from ogr_core.project.project import DEFAULT_PROJECT_NAME
    name = getattr(project, "name", project)
    name = "" if name is None else str(name)
    if name in (DEFAULT_PROJECT_NAME, DEMO_PROJECT_NAME):
        return tr(name)
    return name


def variable_label(project, key, stored) -> str:
    """A random variable's label as Define Random Variables shows it
    (:func:`random_variable_label`), found by its key in ``project``; the
    stored label when the variable is no longer there. The sensitivity plot,
    its ranking and the status bar printed the stored «Mat1 —
    friction_angle»."""
    for rv in getattr(project, "random_variables", None) or []:
        if getattr(rv, "key", None) == key:
            return random_variable_label(rv)
    return stored


#: The choice lists of the support parameters, by parameter: (label, stored
#: value). Moved from Define Support (``_CHOICES``) so the Support Properties
#: Table names the values as the dialog does; it printed «shear»,
#: «intersection».
SUPPORT_CHOICES: dict = {
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
    # v0.1.122 — the equivalent-fluid retaining wall.
    "profile_type": [
        ("Uniform", "uniform"),
        ("Triangular", "triangular"),
        ("Trapezoidal", "trapezoidal"),
        ("Custom", "custom"),
    ],
    "force_location": [
        ("At the slip surface", "intersection"),
        ("At the centroid of the pressure diagram", "centroid"),
    ],
    # v0.1.123 — the pile failure mode. The two entries are not two ways
    # of writing the same thing: Shear is how much load the pile can take,
    # Ito & Matsui is how much the ground can hand it.
    "failure_mode": [
        ("Shear", "shear"),
        ("Ito & Matsui", "ito_matsui"),
    ],
    # v0.1.124 - the helical anchor. Only the AREA of the shaft matters,
    # which is what the plate loses to it.
    "shaft_type": [
        ("Round", "round"),
        ("Square", "square"),
    ],
}


def support_choice_label(param, value) -> str:
    """The label of a stored choice of a support parameter; the value as it
    is when the parameter has no list."""
    for label, data in SUPPORT_CHOICES.get(param, ()):
        if data == value:
            return tr(label)
    return str(getattr(value, "value", value))


def _permeability_models():
    from ogr_core.hydraulic import PermeabilityModel
    return {
        PermeabilityModel.CONSTANT: "Constant",
        PermeabilityModel.SIMPLE: "Simple",
        PermeabilityModel.BROOKS_COREY: "Brooks-Corey",
        PermeabilityModel.FREDLUND_XING: "Fredlund-Xing",
        PermeabilityModel.GARDNER: "Gardner",
        PermeabilityModel.VAN_GENUCHTEN: "van Genuchten",
        PermeabilityModel.USER_DEFINED: "User Defined",
    }


#: The permeability models, as Define Hydraulic Properties names them
#: (moved from its ``_MODEL_LABELS``): the Hydraulic Properties Table printed
#: «constant», «van_genuchten».
PERMEABILITY_MODEL = _permeability_models()


def permeability_model_label(model) -> str:
    from ogr_core.hydraulic import PermeabilityModel
    try:
        model = PermeabilityModel(getattr(model, "value", model))
    except ValueError:
        return str(getattr(model, "value", model))
    return _of(PERMEABILITY_MODEL, model)


#: Units the core writes in words that have a symbol on screen: Define
#: Support showed « deg» where every other angle shows «°».
_UNIT_SYMBOLS = {"deg": "°"}


def unit_symbol(unit) -> str:
    return _UNIT_SYMBOLS.get(unit, unit)


#: v0.1.433 (D411) -- the Surface Type, by its stored value.
SURFACE_TYPE = {"circular": "Circular", "non_circular": "Non-Circular"}


def surface_type_label(value) -> str:
    return _of(SURFACE_TYPE, getattr(value, "value", value))


#: v0.1.433 (D411) -- a serialised surface's type (``to_dict()["type"]``),
#: which the statistics' and the DXF export's notes printed as it is.
SURFACE_KIND = {"circle": "circle", "polyline": "polyline",
                "composite": "composite surface",
                "weak_layer": "weak-layer surface"}


def surface_kind_label(value) -> str:
    return _of(SURFACE_KIND, value)


#: The same types as the noun of «a … surface» (``stat.case_text_*``): in
#: Spanish each reads «superficie …», so its template does not repeat it
#: (review of 0.1.433).
SURFACE_NOUN = {"circle": "circular surface", "polyline": "polyline surface",
                "composite": "composite surface",
                "weak_layer": "weak-layer surface"}


def surface_noun_label(value) -> str:
    return _of(SURFACE_NOUN, value)


#: v0.1.433 (D411) -- the rapid drawdown procedures, as Project Settings
#: names them (moved from its combo), by the stored value.
DRAWDOWN_PROCEDURE = {
    "b_bar": "Effective Stress using B-bar",
    "duncan_wright": "Duncan, Wright, Wong 3 Stage (1990)",
    "corps_2": "Army Corp. Eng. 2 Stage (1970)",
    "lowe_karafiath": "Lowe and Karafiath (1960)",
}


def drawdown_procedure_label(value) -> str:
    return _of(DRAWDOWN_PROCEDURE, getattr(value, "value", value))


#: v0.1.433 (D411) -- the techniques of Optimize Surfaces, as its dialog
#: names them (moved from its combo), by the stored value.
OPTIMIZE_TECHNIQUE = {"monte_carlo": "Monte Carlo",
                      "surface_altering": "Surface Altering"}


def optimize_technique_label(value) -> str:
    return _of(OPTIMIZE_TECHNIQUE, getattr(value, "value", value))

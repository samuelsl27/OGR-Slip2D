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
from ogr_core.loads.loads import LoadDistribution, LoadOrientation
from ogr_core.materials.material import PorePressureType
from ogr_core.project.settings import GroundwaterMethod, LEMMethod
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


def support_type_label(stype) -> str:
    """The name a support type is shown with: the name the user gave the
    set (``_display_name``, data, never translated), else the class's
    ``DISPLAY_NAME`` through tr()."""
    given = getattr(stype, "_display_name", None)
    if given:
        return str(given)
    name = getattr(stype, "DISPLAY_NAME", None)
    return tr(name) if name else str(getattr(stype, "TYPE_ID", ""))


def boundary_type_label(btype: BoundaryType) -> str:
    return tr(btype.display_name)


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
            return "%s — %s" % (tr(head), param_label(param))
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

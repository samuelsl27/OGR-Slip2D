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


def support_class_label(name) -> str:
    """A support class named by its English ``DISPLAY_NAME``, in the
    interface's language: «User Defined» in the masculine of a support type,
    not the feminine of the permeability model of that name (v0.1.436, D415:
    the note on an ambiguous set read «Definida por el usuario»)."""
    return _support_class_label(str(name or ""))


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
        # v0.1.436 (D415) -- every name the program gives a set, not only the
        # class's: «Type 3», «X (copy)» (support_set_name)
        return support_set_name(given, name)
    return (_support_class_label(name) if name
            else str(getattr(stype, "TYPE_ID", "")))


def support_name(support, stype=None) -> str:
    """A placed support's name as the user reads it: the name it was given,
    or, when it carries its set's default name (copied from the class's
    English name), that name in the interface's language; the set's label
    when it has none (v0.1.433, D411). v0.1.436 (D415): every name the
    program gives a set, as :func:`support_set_name` reads it."""
    name = getattr(support, "name", "") or ""
    if name:
        # with the set, by its current class, as support_type_label
        current = (getattr(stype, "DISPLAY_NAME", None)
                   if stype is not None else None)
        return support_set_name(name, current)
    return support_type_label(stype) if stype is not None else ""


# ----------------------------------------------------------------------
# v0.1.436 (D415) -- the names the program gives (``ogr_core.naming``)
# ----------------------------------------------------------------------
def _set_name_parts(name) -> tuple:
    """``(base, suffixes)`` of a set's name: the « (copy)» and « (n)» the
    program appended, in the order they were appended. «X (copy) (2)» is
    ``("X", [" (copy)", " (2)"])``."""
    import re
    from ogr_core.naming import COPY_SUFFIX
    text = str(name or "")
    suffixes: list = []
    while True:
        if text.endswith(COPY_SUFFIX) and len(text) > len(COPY_SUFFIX):
            suffixes.append(COPY_SUFFIX)
            text = text[:-len(COPY_SUFFIX)]
            continue
        m = re.fullmatch(r"(.+?)( \(\d+\))", text)
        if m:
            suffixes.append(m.group(2))
            text = m.group(1)
            continue
        return text, suffixes[::-1]


def _class_names() -> set:
    from ogr_core.support import support_registry
    return {cls.DISPLAY_NAME for cls in support_registry().values()}


def _program_base(base, current=None):
    """How a base the program wrote reads, or None when the user wrote it: a
    class's English name by the class the set has NOW (``current``), and
    «Type N» as «Tipo N»."""
    import re
    from ogr_core.naming import NEW_SET_NAME
    if base in _class_names():
        return _support_class_label(current or base)
    # exactly what NEW_SET_NAME writes (first_free_set_name starts at 1, and
    # never writes «Type 01»): a name the user typed stays the user's, and
    # the number is shown as written (review of 0.1.436)
    m = re.fullmatch(
        re.escape(NEW_SET_NAME).replace(r"\{0\}", r"([1-9][0-9]*)"), base,
        re.ASCII)
    if m:
        return tr("Type {0}").format(m.group(1))
    return None


def support_set_name(name, current=None) -> str:
    """A support set's name (or a support's, which is its set's) as the user
    reads it (v0.1.436, D415).

    The names the program gives -- a class's English name, «Type N» from
    Define Support, « (copy)» from Duplicate, « (n)» from the agent and the
    importer -- are shown in the interface's language: «Tipo 3», «Anclado en
    el extremo (copia) (2)». A class's name reads as the class ``current``
    the set has now, as ``boundary_label`` reads a boundary's type. A name
    the user gave is data and shows as it is, except for a « (copy)» the
    program appended to it («Norte (copia)»). The stored name never
    changes; the edit fields show it."""
    from ogr_core.naming import COPY_SUFFIX
    text = str(name or "")
    base, suffixes = _set_name_parts(text)
    head = _program_base(base, current)
    if head is None:
        if COPY_SUFFIX not in suffixes:
            return text
        head = base
    return head + "".join(" " + tr("(copy)") if s == COPY_SUFFIX else s
                          for s in suffixes)


def set_name_names_its_class(name) -> bool:
    """Whether a set's name says its class (a class's English name, with any
    suffix the program appended), so a list need not add the class."""
    return _set_name_parts(name)[0] in _class_names()


def is_program_set_name(name) -> bool:
    """Whether the PROGRAM wrote a set's name entirely: a class's name or
    «Type N», with the suffixes it appends. «Norte (copy)» is not: «Norte»
    is the user's."""
    return bool(name) and _program_base(_set_name_parts(name)[0]) is not None


def _set_label_of(project, name, ref) -> str:
    """One property set named in a note: by the set ``ref`` when ``project``
    still has it under that name, else by the name alone."""
    for st in getattr(project, "support_types", None) or []:
        if getattr(st, "id", None) == ref and ref is not None:
            stored = (getattr(st, "_display_name", "")
                      or getattr(st, "DISPLAY_NAME", ""))
            if stored == name:
                return support_type_label(st)
            break
    return support_set_name(name)


def set_names_label(project, value) -> str:
    """Property sets as the engine named them in a note
    (``ogr_core.messages.Joined``): each by :func:`support_type_label`, the
    ones the program named in the reader's language and by the class they
    have now; between «» when the engine quoted them. A plain string is one
    name: a name the user gave may hold «, »."""
    items = getattr(value, "items", None)
    if items is None:
        return support_set_name(value)
    refs = getattr(value, "refs", ()) or ()
    quote = getattr(value, "quote", "")
    shown = [_set_label_of(project, name, refs[k] if k < len(refs) else None)
             for k, name in enumerate(items)]
    if quote:
        # the quotes of the reader's language: «» in Spanish, the engine's
        # straight ones in English, as the rest of the English sentence
        # (review of 0.1.436)
        shown = [tr("'{0}'").format(s) if quote == "'" else quote + s + quote
                 for s in shown]
    return getattr(value, "sep", ", ").join(shown)


def record_label(name) -> str:
    """A strong-motion record's name as the user reads it: «Record», the
    name the program gives one read from text or values, in the
    interface's language; any other name, a file's or the user's, as it is
    (v0.1.436, D415)."""
    from ogr_core.naming import DEFAULT_RECORD_NAME
    text = str(name or "")
    return tr("Record") if text == DEFAULT_RECORD_NAME else text


def record_name_label(project, value) -> str:
    """A record named in a note (a ``Joined`` of one, or a plain name)."""
    items = getattr(value, "items", None)
    return record_label(items[0] if items else value)


def _load_heading(kind, magnitude, end=None) -> str:
    """An unnamed load by its kind and its magnitude: the context menu's
    words, «Carga distribuida — 35.0 kN/m²»; a distributed load that varies
    along it by its two ends, «Carga distribuida — 10.0–30.0 kN/m²» (the
    owner's decision in the review of 0.1.436: by the first alone, its
    variable of the second magnitude read the first)."""
    if kind == "line":
        return tr("Line Load — {0:.1f} kN/m").format(magnitude)
    if end is not None:
        return tr("Distributed Load — {0:.1f}–{1:.1f} kN/m²").format(
            magnitude, end)
    return tr("Distributed Load — {0:.1f} kN/m²").format(magnitude)


def load_label(load) -> str:
    """A load as the user reads it (v0.1.436, D415): the name the user gave
    it, as it is; else -- no name, or the one it was born with («Dist 20.0
    kN/m²», which kept the magnitude it had then) -- its kind and its
    magnitude NOW, in the interface's language. In both languages: the
    English window said «Dist 20.0 kN/m²» of a load of 35."""
    from ogr_core.naming import (load_end_magnitude, load_has_given_name,
                                 load_kind, load_magnitude)
    if load_has_given_name(load):
        return str(load.name)
    magnitude = load_magnitude(load)
    if magnitude is None:
        return (tr("Line Load") if load_kind(load) == "line"
                else tr("Distributed Load"))
    return _load_heading(load_kind(load), magnitude, load_end_magnitude(load))


def load_name_label(value) -> str:
    """A load named by what a run kept (``ogr_core.naming.LoadName``): an
    unnamed one by the magnitude it had IN THE RUN (the owner's decision,
    2026-11-11); a name the user gave as it is. A plain string the program
    wrote («Dist 20.0 kN/m²») reads by the magnitude it names."""
    from ogr_core.naming import parse_default_load_name
    kind = getattr(value, "kind", "")
    magnitude = getattr(value, "magnitude", None)
    if kind and not getattr(value, "given", True) and magnitude is not None:
        return _load_heading(kind, magnitude,
                             getattr(value, "end_magnitude", None))
    parsed = parse_default_load_name(value)
    if parsed is not None:
        return _load_heading(*parsed)
    return str(value)


def _load_of(project, name, ref):
    """The load ``ref`` of ``project`` when a note's name still names it:
    its name, or its id (an unnamed one, or one named since)."""
    for ld in (list(getattr(project, "distributed_loads", None) or [])
               + list(getattr(project, "line_loads", None) or [])):
        if ref is not None and getattr(ld, "id", None) == ref:
            if name in ((getattr(ld, "name", "") or ref), ref):
                return ld
            return None
    return None


def load_names_label(project, value) -> str:
    """Loads as the core named them in a note (``ogr_core.messages.Joined``,
    their name or their id): each by :func:`load_label` when ``project``
    still has it under that name, so an unnamed one reads by its magnitude
    now and never by its id; the text is never split. Joined by «; » on
    screen: each name holds «—» and may hold «, » (review of 0.1.436)."""
    items = getattr(value, "items", None)
    if items is None:
        return load_name_label(value)
    refs = getattr(value, "refs", ()) or ()
    shown = []
    for k, name in enumerate(items):
        ld = _load_of(project, name, refs[k] if k < len(refs) else None)
        shown.append(load_label(ld) if ld is not None
                     else load_name_label(name))
    return "; ".join(shown)


def line_load_name_label(project, value) -> str:
    """The line load a refusal names, inside a sentence that already says
    «line load»: the name the user gave it, else its magnitude alone
    («Carga lineal «50.0 kN/m»: …»), which «Carga lineal «Carga lineal —
    50.0 kN/m»» said twice (review of 0.1.436)."""
    from ogr_core.naming import (load_has_given_name, load_magnitude,
                                 parse_default_load_name)
    items = getattr(value, "items", None)
    name = items[0] if items else value
    refs = getattr(value, "refs", ()) or ()
    ld = _load_of(project, name, refs[0] if refs else None)
    if ld is not None:
        if load_has_given_name(ld):
            return str(ld.name)
        magnitude = load_magnitude(ld)
    else:
        parsed = parse_default_load_name(name)
        if parsed is None:
            return str(name)
        magnitude = parsed[1]
    return tr("{0:.1f} kN/m").format(magnitude)


def boundary_type_label(btype: BoundaryType) -> str:
    return tr(btype.display_name)


def boundary_has_given_name(boundary) -> bool:
    """Whether the user named ``boundary``. A boundary is born with its
    type's ENGLISH name as its name (``Boundary.__post_init__``): that name
    is data the ``.ogr`` keeps, and on screen it is the type's name in the
    interface's language.

    Any type's English name counts as the default, not only its own: Convert
    Boundary from the canvas's context menu kept the old type's name until
    v0.1.455, and so did the v0.1.69 migration that swapped the water table
    and the drawdown line. Found by the review of v0.1.432: a water table
    converted from a material boundary said «Contorno eliminado: Material
    Boundary». The rule is the core's since v0.1.455 (D410), which the
    conversion asks too."""
    from ogr_core.geometry.boundary import boundary_has_given_name as given
    return given(boundary)


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


#: v0.1.437 (D414) -- what a value of each enumeration of a ``.ogr`` is, as a
#: refusal of the readers names it: «'future_value' is not a valid
#: PorePressureType» printed the class's name. By the class's name, which is
#: what the core's code carries, with its article («…no es un valor válido
#: para el método de presión intersticial», review of 0.1.437); one this table
#: does not have shows as it is.
ENUM_NAMES = {
    "UnitSystem": "the unit system", "TimeUnit": "the time unit",
    "PermeabilityUnit": "the permeability unit",
    "FailureDirection": "the failure direction",
    "PorePressureType": "the pore water pressure method",
    "ForceApplication": "the force application of a support",
    "ForceOrientation": "the force orientation of a support",
    "WaterLevelMode": "the water level of the tension crack",
    "LoadOrientation": "the load orientation",
    "LoadAction": "the load action",
    "LoadDistribution": "the load distribution",
    "VariableKind": "the kind of random variable",
    "DistributionType": "the statistical distribution",
    "FocusKind": "the kind of focus object",
    # the six the review of 0.1.437 found, which no model of the census held
    "SimpleSoilType": "the soil type of the Simple permeability model",
    "BCType": "the type of a seepage boundary condition",
    "GridValueType": "the value type of the pore pressure grid",
    "AnnotationKind": "the kind of annotation",
    "BlockObjectKind": "the kind of block search object",
    "PolylinePointMode": "an end of a block search polyline",
}


def enum_name_label(name) -> str:
    """What a value of the enumeration ``name`` (its class's name) is, in
    the interface's language (:data:`ENUM_NAMES`)."""
    return tr(ENUM_NAMES.get(str(name), str(name)))


def file_value_label(value) -> str:
    """A value a ``.ogr`` holds, as the file writes it: a null as «null»,
    not as Python's «None» (review of 0.1.437)."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def json_shape_label(value) -> str:
    """A JSON shape a section of a ``.ogr`` has or must have (a key of
    ``ogr_core.file_messages.SHAPE_WORDS``), by the words of the sentence in
    the interface's language; ``null`` is said as the file writes it
    (v0.1.438, D422). One this build has no words for shows as it is."""
    from ogr_core.file_messages import SHAPE_WORDS
    words = SHAPE_WORDS.get(str(value))
    if words is None:
        return str(value)
    return words if words == "null" else tr(words)


def _items(value) -> list:
    items = getattr(value, "items", None)
    if items is not None and not callable(items):
        return list(items)
    return list(value) if isinstance(value, (list, tuple)) else [value]


def strength_model_list_label(ids) -> str:
    """Strength models by their identifiers (a ``Joined``, as the registry
    gives them), each by its name in the interface's language, joined by
    «; »: three names hold a comma («Undrained, c(depth below layer top)»).
    An identifier this build does not have shows as it is."""
    from ogr_core.materials import REGISTRY
    out = []
    for mid in _items(ids):
        try:
            out.append(tr(REGISTRY.get(mid).DISPLAY_NAME))
        except KeyError:
            out.append(str(mid))
    return "; ".join(out)


def parameter_list_label(keys) -> str:
    """The parameters a strength model takes (a ``Joined`` of their keys),
    each by its name and, when that is not the key, the key the file has to
    hold between brackets: a file is mended by the key (review of 0.1.437).
    None at all says so."""
    out = []
    for key in _items(keys):
        name = param_label(key)
        out.append(name if name == str(key) else "%s (%s)" % (name, key))
    return ", ".join(out) if out else tr("no parameters")


def random_variable_label(rv, project=None) -> str:
    """The label a random variable is SHOWN with.

    The ``.ogr`` keeps the label ``ogr_core.statistics.available_variables``
    wrote (``"Clay — friction_angle"``, ``"Clay — hydraulic ks"``,
    ``"seismic kh"``), and it is not touched: this builds the shown text from
    it, keeping the name part as stored and translating the parameter. A
    label that does not have the form the core writes (edited in a file or
    by a script) is shown as it is.

    v0.1.436 (D415) -- a load's variable is headed by the LOAD, found by the
    id in its key in ``project``, as :func:`load_label` names it: the label
    froze the name the load had when the variable was made («Dist 20.0
    kN/m² — magnitude_1» of a load of 35). Without ``project``, or with the
    load gone, by the stored head.
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
    if kind in ("line_load", "distributed_load") and tail == param:
        load = _load_of_key(project, rv.key)
        if load is not None:
            head = load_label(load)
        elif head:
            head = load_name_label(head)
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


def _load_of_key(project, key):
    """The load a random variable's key (``kind:load id:param``) names, in
    ``project``; None without it."""
    parts = str(key or "").split(":")
    if project is None or len(parts) < 3:
        return None
    for ld in (list(getattr(project, "distributed_loads", None) or [])
               + list(getattr(project, "line_loads", None) or [])):
        if getattr(ld, "id", None) == parts[1]:
            return ld
    return None


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
            return random_variable_label(rv, project)
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


# ----------------------------------------------------------------------
# v0.1.434 (D412) -- the identifiers the core's messages and the undo step
# names carry, as the user reads them
# ----------------------------------------------------------------------
#: The design standards, by the id the project stores (``PRESETS`` and
#: ``"custom"``), as the notes and the report name them. «custom» and «none»
#: have keys of their own, feminine like «norma» (the owner's decision,
#: 2026-11-09): «Personalizado: 2 material(es)…» did not agree with
#: «Norma de diseño aplicada». The combo of Project Settings shows these
#: names too, except «none», which keeps «No standard» («Ninguna» after
#: «Norma de diseño:», v0.1.325).
DESIGN_STANDARD = {
    "none": "No design standard",
    "eurocode7_da1c1": "Eurocode 7 — DA1 Combination 1",
    "eurocode7_da1c2": "Eurocode 7 — DA1 Combination 2",
    "eurocode7_da2": "Eurocode 7 — DA2",
    "eurocode7_da3": "Eurocode 7 — DA3",
    "custom": "Custom standard",
}


def design_standard_label(value) -> str:
    return _of(DESIGN_STANDARD, getattr(value, "value", value))


#: The operations of ``boundary_edit`` (``ogr_api.ops.model._EDIT_OPS``),
#: as the agent's undo step «Edit boundary ({op})» names them.
BOUNDARY_EDIT_OP = {
    "set_vertices": "set vertices", "translate": "translate",
    "move_vertex": "move vertex", "insert_vertex": "insert vertex",
    "delete_vertex": "delete vertex", "rename": "rename",
    "change_type": "change type", "delete": "delete", "copy": "copy",
    "scale": "scale", "rotate": "rotate", "simplify": "simplify",
    "block_object": "block search object",
}


def boundary_edit_op_label(value) -> str:
    return _of(BOUNDARY_EDIT_OP, value)


def support_names_label(project, value) -> str:
    """Support names as the core joined them (``ogr_core.messages.Joined``):
    each one as :func:`support_name` shows it, a default name by the class
    its set has NOW when ``project`` still has that support. The text is
    never split: a name the user gave may hold «, » (review of 0.1.434), so
    a plain string is one name."""
    from types import SimpleNamespace
    items = getattr(value, "items", None)
    if items is None:
        return support_name(SimpleNamespace(name=str(value)))
    refs = getattr(value, "refs", ()) or ()
    by_id = {getattr(s, "id", None): s
             for s in getattr(project, "supports", None) or []}
    shown = []
    for k, name in enumerate(items):
        s = by_id.get(refs[k]) if k < len(refs) else None
        shown.append(_support_of_note(project, s, name) if s is not None
                     else support_name(SimpleNamespace(name=name)))
    return getattr(value, "sep", ", ").join(shown)


def _support_of_note(project, s, name) -> str:
    """A support of ``project`` that a note named ``name`` (v0.1.436, D415).

    By its name when it has one -- the one it had, or the one it was given
    since the note was written, when the core wrote its id or its class's
    identifier for want of one --, the program's names in the reader's
    language. An unnamed one by its CLASS and its head, «Bulón de suelo en
    (54.00, 8.00)»: by its set, the note of an orphan read «the support
    «Bulón de suelo» … «Bulón de suelo» is used instead», and the supports
    of a pattern, which are born unnamed, all read alike (the owner's
    decision in the review of 0.1.436). Never by its id."""
    own = getattr(s, "name", "") or ""
    written_for_want = name in (getattr(s, "id", None),
                                getattr(s, "type_id", None))
    if own and (own == name or written_for_want):
        from ogr_core.support import resolve_support_type
        return support_name(s, resolve_support_type(project, s))
    if own:
        # it had another name when the note was written: that one
        from types import SimpleNamespace
        return support_name(SimpleNamespace(name=name))
    from ogr_core.support import support_registry
    cls = support_registry().get(getattr(s, "type_id", None))
    kind = (_support_class_label(cls.DISPLAY_NAME) if cls is not None
            else str(getattr(s, "type_id", "") or name))
    head = getattr(s, "head", None)
    if head is None:
        return kind
    return tr("{0} at ({1:.2f}, {2:.2f})").format(kind, head.x, head.y)


def support_failures_label(project, value) -> str:
    """The supports a run could not price, each with its reason, as the
    engine joined them («<id> (reason); …»): each support as
    :func:`support_names_label` names it, the reason as it is (data, D335).
    ``refs`` pairs each support with its reason (v0.1.436, D415)."""
    refs = getattr(value, "refs", ()) or ()
    items = getattr(value, "items", None)
    if not items or len(refs) != len(items):
        return str(value)
    from ogr_core.messages import Joined
    out = []
    for (sid, why) in refs:
        out.append("%s (%s)" % (support_names_label(
            project, Joined([sid or "?"], refs=[sid])), why))
    return getattr(value, "sep", "; ").join(out)


def variable_key_label(project, key) -> str:
    """A random variable named by its key (``kind:target:param``), as Define
    Random Variables names it; the key when ``project`` does not have it."""
    return variable_label(project, key, key)


def variable_keys_label(project, keys) -> str:
    """Keys ", "-joined, each by its label, joined with «; »: a material's
    name may hold a comma (the rule of 0.1.433)."""
    return "; ".join(variable_key_label(project, k)
                     for k in str(keys).split(", ") if k)


def variable_label_by_stored(project, stored) -> str:
    """A random variable named by the label it was stored with («Mat1 —
    friction_angle»), as Define Random Variables names it; the stored label
    when no variable of ``project`` has it."""
    for rv in getattr(project, "random_variables", None) or []:
        if (getattr(rv, "label", None) or getattr(rv, "key", None)) == stored:
            return random_variable_label(rv, project)
    return str(stored)


def material_ref_label(project, ref) -> str:
    """A material the agent named by its id or by its name: its name. The rule
    is the operations layer's (``find_material``), asked and not copied."""
    if project is None:
        return str(ref)
    try:
        from ogr_api.ops.model import find_material
        return find_material(project, ref).name
    except Exception:  # noqa: BLE001 -- gone since: as it was written
        return str(ref)


#: The parts of a project an undo step captures (``commands.LIGHT_ATTRS``
#: and ``HEAVY_ATTRS``), as «(kept, changed since: …)» names them: it listed
#: the attribute names, «materials, settings».
PROJECT_PART = {
    "name": "project name", "settings": "settings",
    "boundaries": "boundaries", "materials": "materials",
    "supports": "supports", "support_types": "support types",
    "distributed_loads": "distributed loads", "line_loads": "line loads",
    "seismic": "seismic load", "seismic_records": "seismic records",
    "region_assignments": "material assignments",
    "tension_crack_properties": "tension crack",
    "water_pressure_grid": "water pressure grid",
    "seepage_bcs": "boundary conditions",
    "random_variables": "random variables", "annotations": "annotations",
    "focus_objects": "focus objects", "user_surfaces": "user surfaces",
    "user_polylines": "user polylines", "fem_mesh": "finite element mesh",
    "seepage_result": "seepage field",
    "transient_results": "transient results",
    "transient_initial_result": "initial state of the transient",
}


def project_part_label(attr) -> str:
    return _of(PROJECT_PART, attr)


class _WithVariables:
    """``project`` with more random variables to name from: those an undo
    step captured. Everything else is the project's."""

    def __init__(self, project, extra) -> None:
        self._project = project
        self.random_variables = (
            list(getattr(project, "random_variables", None) or [])
            + list(extra))

    def __getattr__(self, name):
        return getattr(self._project, name)


def with_variables(project, variables):
    """``project``, and more random variables to name from (those of a
    step, or of the run that wrote a note); ``project`` itself when there
    are none."""
    extra = list(variables or ())
    return _WithVariables(project, extra) if extra else project


def step_scope(project, cmd):
    """What a step's name is said against: ``project``, and the random
    variables the step captured, so a variable the project no longer has is
    still named by its label (the owner's decision, 2026-11-09)."""
    captured = getattr(cmd, "captured", None)
    return with_variables(project, [
        rv for values in (captured("random_variables") if captured else [])
        for rv in (values or [])])

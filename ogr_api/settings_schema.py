# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Reading and writing ``project.settings`` without silent mistakes.

``ProjectSettings`` is a tree of dataclasses, and many of its fields are
declared ``str`` while only accepting a handful of values: an unknown
``search_method`` runs a Grid Search (``analysis_runner._search_for``), an
unknown ``interslice_function`` raises deep inside a run. This module gives
every such field its list of CHOICES, refuses everything else with a
suggestion, and applies a batch of changes ATOMICALLY: the batch is applied
to a copy, validated as a whole (some rules relate two fields), and only
then written onto the live settings, field by field and in place.

Every ``str`` or ``list[str]`` field of the settings is classified here as
one of: a field with choices (:data:`CHOICES`), free text
(:data:`FREE_TEXT`), a structure this layer does not edit yet
(:data:`COMPLEX`), or read-only (:data:`READONLY`).
``tests/test_api_settings_v1194.py`` fails when a new one is not, which is
the whole point: a string setting that nobody classifies is a string
setting that accepts anything.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
import dataclasses
import typing
from typing import Callable, Optional

from .coerce import coerce_value, describe_type, resolve_field, type_hints
from .errors import Conflict, InvalidArgument, did_you_mean


# ----------------------------------------------------------------------
# Choices for the ``str`` fields that are enumerations in disguise
# ----------------------------------------------------------------------
def _enum_values(enum_cls) -> list[str]:
    return [str(m.value) for m in enum_cls]


def _methods() -> list[str]:
    from ogr_slip2d.methods import method_registry
    return sorted(method_registry())


def _search_methods() -> list[str]:
    from ogr_core.project.settings import SearchMethod
    return _enum_values(SearchMethod)


def _surface_types() -> list[str]:
    from ogr_core.project.settings import SurfaceType
    return _enum_values(SurfaceType)


def _weak_layer() -> list[str]:
    from ogr_core.project.settings import WeakLayerHandling
    return _enum_values(WeakLayerHandling)


def _gw_methods() -> list[str]:
    from ogr_core.project.settings import GroundwaterMethod
    return _enum_values(GroundwaterMethod)


def _drawdown_methods() -> list[str]:
    from ogr_slip2d.rapid_drawdown import B_BAR, MULTISTAGE_METHODS
    return [B_BAR, *MULTISTAGE_METHODS]


def _interslice_functions() -> list[str]:
    from ogr_slip2d.methods.gle import INTERSLICE_FUNCTIONS
    return list(INTERSLICE_FUNCTIONS)


def _unit_systems() -> list[str]:
    from ogr_core.units import SYSTEMS
    return list(SYSTEMS)


def _sampling() -> list[str]:
    from ogr_core.statistics.distributions import SamplingMethod
    return _enum_values(SamplingMethod)


def _prob_types() -> list[str]:
    from ogr_core.statistics.probabilistic import ProbabilisticType
    return [ProbabilisticType.GLOBAL_MINIMUM, ProbabilisticType.OVERALL_SLOPE]


def _back_methods() -> list[str]:
    from ogr_slip2d.back_analysis import SUPPORTED_METHODS
    return list(SUPPORTED_METHODS)


def _standards() -> list[str]:
    from ogr_core.project.settings import DesignStandardSettings
    return list(DesignStandardSettings.PRESETS) + ["custom"]


def _polarities() -> list[str]:
    from ogr_slip2d.newmark import Polarity
    return _enum_values(Polarity)


#: Path -> callable giving the accepted values. A callable and not a list,
#: so a method or a unit system registered later is accepted without this
#: file being edited — the registries are the source, not a copy of them.
CHOICES: dict[str, Callable[[], list[str]]] = {
    "units.system_id": _unit_systems,
    "methods.enabled_methods": _methods,
    "methods.interslice_function": _interslice_functions,
    "methods.interslice_forces": lambda: ["total", "effective"],
    "groundwater.method": _gw_methods,
    "groundwater.rapid_drawdown_method": _drawdown_methods,
    "search.surface_type": _surface_types,
    "search.search_method": _search_methods,
    # ``optimize.py`` reads these three (search.py: ``target == "all"``,
    # ``"fos_less_than"``, else the global minimum).
    "search.optimize_target": lambda: ["global_minimum", "all",
                                       "fos_less_than"],
    "search.weak_layer_handling": _weak_layer,
    "statistics.sampling_method": _sampling,
    "statistics.analysis_type": _prob_types,
    "back_analysis.method_id": _back_methods,
    "random_numbers.method": lambda: ["pseudo_random", "random"],
    "design_standard.standard": _standards,
    "seismic.polarity": _polarities,
}

#: Choices that depend on the model rather than on a registry.
DYNAMIC_CHOICES: dict[str, Callable] = {
    "seismic.record_id": lambda project: [""] + [
        r.id for r in getattr(project, "seismic_records", [])],
}

#: Text with no fixed vocabulary.
FREE_TEXT = frozenset({
    "summary.title", "summary.analysis", "summary.author",
    "summary.company", "summary.date_created", "summary.comments",
})

#: Structures this layer does not edit as a plain value yet. Refused with a
#: hint instead of accepted as an unchecked blob.
COMPLEX = frozenset({
    "groundwater.transient_stages", "groundwater.transient_initial_bcs",
})

#: Limits of the program, not choices of the model.
READONLY = frozenset({"max_materials", "max_supports"})

#: Set only through :data:`VIRTUAL` ``groundwater.advanced_option``,
#: because the three are mutually exclusive and ``set_advanced_option`` is
#: what keeps them so.
_ADVANCED_FLAGS = frozenset({"groundwater.transient",
                             "groundwater.excess_pore_pressure",
                             "groundwater.rapid_drawdown"})

_ADVANCED_OPTIONS = [None, "transient", "excess_pore_pressure",
                     "rapid_drawdown"]

#: Keys that are not fields but act on several.
VIRTUAL = {
    "groundwater.advanced_option": (
        "One of null, 'transient', 'excess_pore_pressure', "
        "'rapid_drawdown'. The three groundwater advanced options are "
        "mutually exclusive; this key sets exactly one (or none)."),
}

_DESIGN_FACTORS = ("factor_permanent", "factor_variable", "factor_cohesion",
                   "factor_friction", "factor_unit_weight",
                   "factor_resistance")

#: Numeric bounds that follow from what the quantity IS, not from taste.
#: The design-factor range is the one the interface's spin boxes enforce.
_BOUNDS: dict[str, tuple[Optional[float], Optional[float], str]] = {
    "methods.num_slices": (1, None, "at least 1"),
    "methods.tolerance": (0.0, None, "positive"),
    "methods.max_iterations": (1, None, "at least 1"),
    "search.grid_nx": (1, None, "at least 1"),
    "search.grid_ny": (1, None, "at least 1"),
    **{f"design_standard.{f}": (0.1, 10.0, "between 0.1 and 10")
       for f in _DESIGN_FACTORS},
}
_STRICT_LOWER = {"methods.tolerance"}


def section_names(settings) -> list[str]:
    return [f.name for f in dataclasses.fields(settings)
            if dataclasses.is_dataclass(getattr(settings, f.name))]


def _retired() -> dict:
    """Search-setting names that were removed, with what replaced them."""
    from ogr_core.project.settings import _SHADOW_FIELDS

    out = {}
    for old, (_default, new, version) in _SHADOW_FIELDS.items():
        if new:
            out[old] = f"'{old}' was retired in {version}; use " \
                       f"'search.{new}'."
        else:
            out[old] = f"'{old}' was retired in {version}; nothing read it."
    return out


def choices_for(path: str, project=None) -> Optional[list]:
    if path in CHOICES:
        return CHOICES[path]()
    if path in DYNAMIC_CHOICES and project is not None:
        return DYNAMIC_CHOICES[path](project)
    return None


# ----------------------------------------------------------------------
def describe(project, section: Optional[str] = None) -> dict:
    """Every setting with its value, type and — where it has one — choices.

    ``section`` narrows it to one section (``"search"``, ``"methods"`` ...).
    """
    from .results import json_safe

    settings = project.settings
    sections = section_names(settings)
    if section is not None and section not in sections:
        raise InvalidArgument(
            f"Unknown settings section {section!r}.",
            hint=(did_you_mean(section, sections) + " " if did_you_mean(
                section, sections) else "") + f"Sections: {sections}.")
    out = {}
    for name in ([section] if section else sections):
        sec = getattr(settings, name)
        hints = type_hints(sec)
        fields = {}
        for f in dataclasses.fields(sec):
            path = f"{name}.{f.name}"
            entry = {"value": json_safe(getattr(sec, f.name)),
                     "type": describe_type(hints.get(f.name))}
            ch = choices_for(path, project)
            if ch is not None:
                entry["choices"] = ch
            if path in COMPLEX:
                entry["editable"] = False
            if path in _ADVANCED_FLAGS:
                entry["set_via"] = "groundwater.advanced_option"
            if path in _BOUNDS:
                entry["range"] = _BOUNDS[path][2]
            fields[f.name] = entry
        if name == "groundwater":
            fields["advanced_option"] = {
                "value": sec.advanced_option(), "type": "virtual",
                "choices": _ADVANCED_OPTIONS,
                "description": VIRTUAL["groundwater.advanced_option"]}
        out[name] = fields
    return out


# ----------------------------------------------------------------------
def _check_choice(path: str, value, project) -> None:
    ch = choices_for(path, project)
    if ch is None:
        return
    values = value if isinstance(value, list) else [value]
    for v in values:
        if v not in ch:
            hint = did_you_mean(str(v), [str(c) for c in ch])
            raise InvalidArgument(
                f"{path}: {v!r} is not one of {ch}.", hint=hint or None)


def _check_bounds(path: str, value) -> None:
    if path not in _BOUNDS or value is None:
        return
    lo, hi, text = _BOUNDS[path]
    bad = ((lo is not None and (value <= lo if path in _STRICT_LOWER
                                else value < lo))
           or (hi is not None and value > hi))
    if bad:
        raise InvalidArgument(f"{path} must be {text}, got {value!r}.")


def apply_changes(project, changes: dict) -> dict:
    """Apply ``{path: value}`` atomically; return what changed.

    Nothing is written unless the whole batch is valid. The answer lists
    each changed path with its old and new value, plus the refusals and
    warnings the engine would give for the result (``check_analysis_
    settings`` and ``settings_warnings``), so the caller sees immediately
    whether the model can now run.
    """
    if not isinstance(changes, dict) or not changes:
        raise InvalidArgument(
            "changes must be a non-empty object of {'section.field': value}.",
            hint="e.g. {'methods.num_slices': 30, "
                 "'search.search_method': 'slope'}")
    live = project.settings
    work = copy.deepcopy(live)
    retired = _retired()
    touched: list[str] = []

    # The virtual keys and the design standard go FIRST, so an explicit
    # factor in the same batch is checked against the standard it lands
    # on, and a preset does not overwrite a factor given alongside it.
    ordered = sorted(changes.items(), key=lambda kv: (
        0 if kv[0] in VIRTUAL or kv[0] == "design_standard.standard"
        else 1))
    for path, raw in ordered:
        if not isinstance(path, str):
            raise InvalidArgument(f"Setting paths are strings, got {path!r}.")
        if path in VIRTUAL:
            if raw not in _ADVANCED_OPTIONS:
                raise InvalidArgument(
                    f"{path}: {raw!r} is not one of {_ADVANCED_OPTIONS}.")
            work.groundwater.set_advanced_option(raw)
            touched.extend(sorted(_ADVANCED_FLAGS))
            continue
        if path in _ADVANCED_FLAGS:
            raise InvalidArgument(
                f"{path} is not set directly.",
                hint="The groundwater advanced options are mutually "
                     "exclusive; use 'groundwater.advanced_option' with "
                     "one of " + str(_ADVANCED_OPTIONS) + ".")
        if path in READONLY:
            raise InvalidArgument(f"{path} is a limit of the program, not "
                                  f"a setting of the model.")
        if path in COMPLEX:
            raise InvalidArgument(
                f"{path} is a structure this operation does not edit.",
                hint="Use python_exec for it for now; a dedicated "
                     "operation arrives with the groundwater tools.")
        parent, name, hint = resolve_field(work, path, retired=retired)
        value = coerce_value(raw, hint, path)
        _check_choice(path, value, project)
        _check_bounds(path, value)
        if path == "design_standard.standard":
            parent.apply_preset(value)
            touched.extend(f"design_standard.{f}" for f in _DESIGN_FACTORS)
        else:
            setattr(parent, name, value)
        touched.append(path)

    _check_cross_rules(work, changes, project)

    # Commit: field by field onto the LIVE settings object, so anything
    # holding a reference to it (the interface's dialogs, from phase F4)
    # sees the change.
    diff = {}
    for path in dict.fromkeys(touched):
        sec_name, _, field_name = path.partition(".")
        new_parent = getattr(work, sec_name) if field_name else work
        old_parent = getattr(live, sec_name) if field_name else live
        key = field_name or sec_name
        old, new = getattr(old_parent, key), getattr(new_parent, key)
        if old != new:
            diff[path] = {"old": old, "new": new}
            setattr(old_parent, key, copy.deepcopy(new))
    project.is_dirty = True
    project._notify("settings_changed")
    return {"changed": diff}


def _check_cross_rules(s, changes: dict, project) -> None:
    """Rules that relate two settings; checked on the whole result."""
    from ogr_core.project.settings import (CIRCULAR_METHODS,
                                           NON_CIRCULAR_METHODS,
                                           SearchMethod, SurfaceType)

    sm = SearchMethod(s.search.search_method)
    st = SurfaceType(s.search.surface_type)
    family = CIRCULAR_METHODS if st == SurfaceType.CIRCULAR \
        else NON_CIRCULAR_METHODS
    if sm not in family:
        allowed = sorted(m.value for m in family)
        raise Conflict(
            f"search_method {sm.value!r} does not run on "
            f"{st.value} surfaces.",
            hint=f"With surface_type={st.value!r} use one of {allowed}.")

    def pair(a, b, label):
        va, vb = getattr(s.search, a), getattr(s.search, b)
        if (va is None) != (vb is None):
            raise Conflict(
                f"search.{a} and search.{b} go together: set both, or "
                f"null both for {label}.",
                hint="A lone bound is read by nothing — the engine falls "
                     "back to automatic when either is missing.")
        if va is not None and vb is not None and not va < vb:
            raise Conflict(f"search.{a} ({va}) must be less than "
                           f"search.{b} ({vb}).")

    pair("grid_x_min", "grid_x_max", "an automatic grid")
    pair("grid_y_min", "grid_y_max", "an automatic grid")
    pair("slope_limit_left", "slope_limit_right", "automatic limits")
    pair("slope_limit_left_2", "slope_limit_right_2", "no second window")
    if (s.search.axis_x is None) != (s.search.axis_y is None):
        raise Conflict("search.axis_x and search.axis_y go together.",
                       hint="Set both for a user moment axis, or null both "
                            "for the automatic one.")

    em = list(s.methods.enabled_methods)
    if not em:
        raise Conflict("methods.enabled_methods cannot be empty.",
                       hint="e.g. ['bishop_simplified', 'spencer']")
    if len(set(em)) != len(em):
        raise Conflict("methods.enabled_methods has repeated ids.")

    ds = s.design_standard
    factor_paths = [p for p in changes
                    if p.startswith("design_standard.factor_")]
    if factor_paths and ds.standard != "custom":
        raise Conflict(
            f"{factor_paths[0]} can only be set with "
            f"design_standard.standard='custom' (it is "
            f"{ds.standard!r}); a named standard loads its own factors.",
            hint="Set 'design_standard.standard': 'custom' in the same "
                 "batch, then the factors.")

    if s.seismic.newmark and not s.seismic.record_id:
        raise Conflict("seismic.newmark needs seismic.record_id.",
                       hint="Add a strong-motion record first and set its "
                            "id.")


def settings_diagnostics(project) -> dict:
    """What the engine says about the settings as they are now."""
    from ogr_slip2d.analysis_runner import (check_analysis_settings,
                                            settings_warnings)

    methods = list(project.settings.methods.enabled_methods) or [
        "bishop_simplified"]
    return {"problems": list(check_analysis_settings(project)),
            "warnings": list(settings_warnings(project, methods))}


def all_string_fields(settings) -> list[tuple[str, object]]:
    """Every ``str``-typed or ``list[str]``-typed field, as ``(path, hint)``.

    For the classification test; walks one level of sections plus the root.
    """
    out = []

    def is_stringy(hint) -> bool:
        if hint is str:
            return True
        origin = typing.get_origin(hint)
        args = typing.get_args(hint)
        if origin in (list, tuple) and args and args[0] is str:
            return True
        if origin in (typing.Union,) or type(hint).__name__ == "UnionType":
            return any(is_stringy(a) for a in args)
        return False

    root_hints = type_hints(settings)
    for f in dataclasses.fields(settings):
        value = getattr(settings, f.name)
        if dataclasses.is_dataclass(value):
            hints = type_hints(value)
            for g in dataclasses.fields(value):
                if is_stringy(hints.get(g.name)):
                    out.append((f"{f.name}.{g.name}", hints.get(g.name)))
        elif is_stringy(root_hints.get(f.name)):
            out.append((f.name, root_hints.get(f.name)))
    return out

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What the program offers, read from its registries at call time.

Nothing here is a hand-written list of models or methods: the strength
models come from ``ogr_core.materials.REGISTRY``, the methods from
``ogr_slip2d.method_registry()``, the enumerations from their ``Enum``
classes. A model registered tomorrow appears in the catalogue without this
file changing — the hand-typed list is what went stale in D165.

``PARAMETERS`` does not describe every model completely: the table-based
ones carry ``points`` or ``rules`` and the undrained-with-depth family a
``cutoff_enabled`` switch, outside the numeric dictionary. Those are read
off a default instance's ``to_dict()``, which is what the loader reads back,
so the catalogue cannot promise a field the model does not store.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from .errors import InvalidArgument, unknown
from .results import json_safe

KINDS = ("strength_models", "methods", "search_methods", "surface_types",
         "boundary_types", "pore_pressure_types", "groundwater_methods",
         "interslice_functions", "failure_directions", "unit_systems",
         "design_standards", "settings")


def _strength_models() -> list[dict]:
    from ogr_core.materials import REGISTRY

    out = []
    for mid, cls in REGISTRY.all().items():
        params = [{"name": name, "default": json_safe(default), "unit": unit,
                   "description": desc}
                  for name, (default, unit, desc) in cls.PARAMETERS.items()]
        entry = {"id": mid, "name": cls.DISPLAY_NAME, "parameters": params}
        extras = _extra_fields(cls)
        if extras:
            entry["extra_fields"] = extras
        out.append(entry)
    return out


def _extra_fields(cls) -> dict:
    """Stored state beyond ``params``, with the default instance's value."""
    try:
        d = cls().to_dict()
    except Exception:  # noqa: BLE001 - a model with no default is described bare
        return {}
    return {k: json_safe(v) for k, v in d.items()
            if k not in ("model_id", "params")}


def strength_from_spec(spec) -> object:
    """A ``StrengthModel`` from ``{"model": id, "params": {...}, ...}``.

    ``model`` (or ``model_id``) names the registry entry; ``params`` holds
    the numeric parameters, checked by the model's own constructor; any
    other key must be one of the model's extra fields (``points``,
    ``rules``, ``cutoff_enabled``).
    """
    from ogr_core.materials import REGISTRY
    from ogr_core.materials.strength_model import StrengthModel

    if not isinstance(spec, dict):
        raise InvalidArgument(
            "strength must be an object like {'model': 'mohr_coulomb', "
            "'params': {'cohesion': 10, 'friction_angle': 30}}.")
    spec = dict(spec)
    mid = spec.pop("model", None) or spec.pop("model_id", None)
    if mid not in REGISTRY.ids():
        raise unknown("strength model", mid, REGISTRY.ids())
    cls = REGISTRY.get(mid)
    params = spec.pop("params", {}) or {}
    if not isinstance(params, dict):
        raise InvalidArgument("strength.params must be an object.")
    unknown_params = [k for k in params if k not in cls.PARAMETERS]
    if unknown_params:
        from .errors import did_you_mean
        hint = did_you_mean(unknown_params[0], cls.PARAMETERS)
        raise InvalidArgument(
            f"{mid}: unknown parameter {unknown_params[0]!r}.",
            hint=(hint + " " if hint else "")
            + f"Parameters of {mid}: {list(cls.PARAMETERS)}.")
    clean = {}
    for k, v in params.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise InvalidArgument(f"{mid}.params.{k} must be a number, "
                                  f"got {v!r}.")
        clean[k] = float(v)
    extras = _extra_fields(cls)
    for k in spec:
        if k not in extras:
            raise InvalidArgument(
                f"{mid}: {k!r} is not a field of this model.",
                hint=f"Extra fields of {mid}: {list(extras) or 'none'}.")
    data = {"model_id": mid, "params": clean, **spec}
    try:
        return StrengthModel.from_dict(data)
    except (ValueError, TypeError, KeyError) as exc:
        raise InvalidArgument(f"{mid}: {exc}") from None


def catalog(kind: str, project=None):
    """The entries of one catalogue ``kind`` (see :data:`KINDS`)."""
    if kind not in KINDS:
        raise unknown("catalogue kind", kind, KINDS)
    if kind == "strength_models":
        return _strength_models()
    if kind == "methods":
        from ogr_slip2d.methods import method_registry
        return [{"id": mid, "name": cls.DISPLAY_NAME,
                 "force_equilibrium": bool(getattr(cls, "SATISFIES_FORCE",
                                                   False)),
                 "moment_equilibrium": bool(getattr(cls, "SATISFIES_MOMENT",
                                                    False))}
                for mid, cls in method_registry().items()]
    if kind == "search_methods":
        from ogr_core.project.settings import (CIRCULAR_METHODS,
                                               NON_CIRCULAR_METHODS,
                                               SearchMethod)
        return [{"id": m.value,
                 "circular": m in CIRCULAR_METHODS,
                 "non_circular": m in NON_CIRCULAR_METHODS}
                for m in SearchMethod]
    if kind == "surface_types":
        from ogr_core.project.settings import SurfaceType
        return [m.value for m in SurfaceType]
    if kind == "boundary_types":
        from ogr_core.geometry import BoundaryType
        return [{"id": b.name.lower(), "name": b.display_name,
                 "closed": b == BoundaryType.EXTERNAL}
                for b in BoundaryType]
    if kind == "pore_pressure_types":
        from ogr_core.materials import PorePressureType
        return [m.value for m in PorePressureType]
    if kind == "groundwater_methods":
        from ogr_core.project.settings import GroundwaterMethod
        return [m.value for m in GroundwaterMethod]
    if kind == "interslice_functions":
        from ogr_slip2d.methods.gle import INTERSLICE_FUNCTIONS
        return list(INTERSLICE_FUNCTIONS)
    if kind == "failure_directions":
        from ogr_core.project import FailureDirection
        return [{"id": m.value, "name": m.name.lower()}
                for m in FailureDirection]
    if kind == "unit_systems":
        from ogr_core.units import SYSTEMS
        return list(SYSTEMS)
    if kind == "design_standards":
        from ogr_core.project.settings import DesignStandardSettings
        keys = ("factor_permanent", "factor_variable", "factor_cohesion",
                "factor_friction", "factor_unit_weight", "factor_resistance")
        return ([{"id": name, "factors": dict(zip(keys, vals))}
                 for name, vals in DesignStandardSettings.PRESETS.items()]
                + [{"id": "custom", "factors": None}])
    if kind == "settings":
        from ogr_core.project import Project
        from .settings_schema import describe
        return describe(project if project is not None else Project())
    raise AssertionError(kind)  # pragma: no cover

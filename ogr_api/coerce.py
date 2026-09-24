# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Turn JSON values into what the model's dataclasses declare.

The engine's dataclasses trust their caller. ``settings.search.search_metod
= "grid"`` creates a new attribute nobody reads; ``Boundary(btype="EXTERNAL")``
fails much later, in ``.value``; ``num_slices = 2.5`` is stored as a float.
A caller that is a language model makes every one of those mistakes, so
this module does the checking the constructors do not:

* :func:`resolve_field` walks a dotted path through DATACLASS FIELDS ONLY,
  so a typo is an error with a suggestion instead of a new attribute;
* :func:`coerce_value` converts one JSON value to a type hint, and refuses
  anything that would need a guess (2.5 for an int, "yes" for a bool, NaN
  for a float).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import dataclasses
import enum
import math
import types
import typing
from typing import Any

from .errors import InvalidArgument, did_you_mean

_NONE_TYPE = type(None)


def type_hints(obj_or_cls) -> dict:
    """``typing.get_type_hints`` of a dataclass, cached per class.

    Resolved because the settings module uses ``from __future__ import
    annotations``, so the raw ``__annotations__`` are strings.
    """
    cls = obj_or_cls if isinstance(obj_or_cls, type) else type(obj_or_cls)
    cached = _HINTS.get(cls)
    if cached is None:
        try:
            cached = typing.get_type_hints(cls)
        except NameError:
            # One forward reference the module never imports at runtime
            # (``Material.hydraulic: Optional["HydraulicProperties"]``)
            # makes the whole call fail. Resolve field by field instead and
            # leave the unresolvable ones as Any: they are the structured
            # fields this layer does not edit as plain values anyway.
            import sys
            glb = vars(sys.modules.get(cls.__module__, typing))
            cached = {}
            for klass in reversed(cls.__mro__):
                for name, ann in getattr(klass, "__annotations__",
                                         {}).items():
                    try:
                        cached[name] = (eval(ann, glb) if isinstance(
                            ann, str) else ann)
                    except Exception:  # noqa: BLE001
                        cached[name] = Any
        _HINTS[cls] = cached
    return cached


_HINTS: dict = {}


def field_names(obj) -> list[str]:
    return [f.name for f in dataclasses.fields(obj)]


def resolve_field(root, path: str, *, retired: dict | None = None):
    """``(parent, name, hint)`` for a dotted path of dataclass fields.

    ``retired`` maps a name that USED to be a field to a sentence saying
    what replaced it; hitting one raises with that sentence as the hint,
    which is more useful than "unknown".
    """
    parts = [p for p in str(path).split(".") if p]
    if not parts:
        raise InvalidArgument("An empty setting path.",
                              hint="Use 'section.field', e.g. "
                                   "'methods.num_slices'.")
    obj = root
    walked = []
    for i, part in enumerate(parts):
        if not dataclasses.is_dataclass(obj):
            raise InvalidArgument(
                f"'{'.'.join(walked)}' is a value, not a section; "
                f"'{'.'.join(parts)}' goes too deep.")
        names = field_names(obj)
        if part not in names:
            where = ".".join(walked) or "settings"
            if retired and part in retired:
                raise InvalidArgument(
                    f"'{'.'.join(walked + [part])}' is not a setting any "
                    f"more.", hint=retired[part])
            hint = did_you_mean(part, names)
            raise InvalidArgument(
                f"'{part}' is not a field of {where}.",
                hint=(hint + " " if hint else "")
                + f"Fields of {where}: {', '.join(names)}.")
        walked.append(part)
        if i == len(parts) - 1:
            return obj, part, type_hints(obj).get(part, Any)
        obj = getattr(obj, part)
    raise AssertionError("unreachable")  # pragma: no cover


def describe_type(hint) -> str:
    """A short, JSON-flavoured name for a type hint."""
    origin = typing.get_origin(hint)
    args = typing.get_args(hint)
    if hint is Any:
        return "any"
    if origin in (typing.Union, types.UnionType):
        inner = [describe_type(a) for a in args if a is not _NONE_TYPE]
        suffix = " | null" if _NONE_TYPE in args else ""
        return " | ".join(inner) + suffix
    if origin in (list, tuple, set):
        return f"list[{describe_type(args[0])}]" if args else "list"
    if origin is dict:
        return "object"
    if origin is typing.Literal:
        return " | ".join(repr(a) for a in args)
    if isinstance(hint, type) and issubclass(hint, enum.Enum):
        return "enum(" + " | ".join(str(m.value) for m in hint) + ")"
    return {bool: "boolean", int: "integer", float: "number",
            str: "string", list: "list", dict: "object"}.get(
        hint, getattr(hint, "__name__", str(hint)))


def coerce_enum(raw, enum_cls, where: str = "value"):
    """An enum member from itself, its value, or its name (any case)."""
    if isinstance(raw, enum_cls):
        return raw
    for m in enum_cls:
        if raw == m.value:
            return m
    if isinstance(raw, str):
        key = raw.strip().lower()
        for m in enum_cls:
            if key == str(m.value).lower() or key == m.name.lower():
                return m
    options = [str(m.value) for m in enum_cls]
    hint = did_you_mean(str(raw), options + [m.name for m in enum_cls])
    raise InvalidArgument(
        f"{where}: {raw!r} is not one of {options}.",
        hint=hint or None)


def coerce_value(raw, hint, where: str = "value"):
    """``raw`` converted to ``hint``, or :class:`InvalidArgument`.

    Deliberately strict where a guess would be silent:

    * a bool accepts only JSON booleans (and the strings "true"/"false"),
      never 0/1, which a language model sends for a count as readily as
      for a switch;
    * an int accepts 3.0 but refuses 2.5, instead of truncating it;
    * a float must be finite, because a NaN setting compares false against
      every threshold in the engine and never raises.
    """
    if hint is Any:
        return raw
    origin = typing.get_origin(hint)
    args = typing.get_args(hint)

    if origin in (typing.Union, types.UnionType):
        if raw is None:
            if _NONE_TYPE in args:
                return None
            raise InvalidArgument(f"{where} cannot be null.")
        errors = []
        for a in args:
            if a is _NONE_TYPE:
                continue
            try:
                return coerce_value(raw, a, where)
            except InvalidArgument as exc:
                errors.append(exc.message)
        raise InvalidArgument(f"{where}: {raw!r} is not a "
                              f"{describe_type(hint)}.")

    if origin is typing.Literal:
        if raw in args:
            return raw
        raise InvalidArgument(f"{where}: {raw!r} is not one of "
                              f"{list(args)}.",
                              hint=did_you_mean(str(raw),
                                                [str(a) for a in args])
                              or None)

    if origin in (list, tuple) or hint in (list, tuple):
        if isinstance(raw, (str, bytes)) or not isinstance(raw, (list, tuple)):
            raise InvalidArgument(f"{where} must be a list, got {raw!r}.")
        inner = args[0] if args else Any
        items = [coerce_value(v, inner, f"{where}[{i}]")
                 for i, v in enumerate(raw)]
        return tuple(items) if (origin is tuple or hint is tuple) else items

    if origin is dict or hint is dict:
        if not isinstance(raw, dict):
            raise InvalidArgument(f"{where} must be an object, got {raw!r}.")
        return dict(raw)

    if raw is None:
        raise InvalidArgument(f"{where} cannot be null.")

    if isinstance(hint, type) and issubclass(hint, enum.Enum):
        return coerce_enum(raw, hint, where)

    if hint is bool:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str) and raw.strip().lower() in ("true", "false"):
            return raw.strip().lower() == "true"
        raise InvalidArgument(f"{where} must be true or false, got {raw!r}.")

    if hint is int:
        if isinstance(raw, bool):
            raise InvalidArgument(f"{where} must be an integer, got {raw!r}.")
        if isinstance(raw, int):
            return raw
        if isinstance(raw, float) and math.isfinite(raw) and raw.is_integer():
            return int(raw)
        if isinstance(raw, str):
            try:
                return coerce_value(float(raw), int, where)
            except ValueError:
                pass
        raise InvalidArgument(f"{where} must be an integer, got {raw!r}.")

    if hint is float:
        if isinstance(raw, bool):
            raise InvalidArgument(f"{where} must be a number, got {raw!r}.")
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise InvalidArgument(
                f"{where} must be a number, got {raw!r}.") from None
        if not math.isfinite(value):
            raise InvalidArgument(f"{where} must be finite, got {raw!r}.")
        return value

    if hint is str:
        if isinstance(raw, str):
            return raw
        raise InvalidArgument(f"{where} must be a string, got {raw!r}.")

    if dataclasses.is_dataclass(hint):
        raise InvalidArgument(
            f"{where} is a whole section; set its fields one by one "
            f"(e.g. '{where}.<field>').")

    return raw


def point(raw, where: str = "point") -> tuple[float, float]:
    """``[x, y]`` (or ``{"x":..,"y":..}``) as a pair of finite floats."""
    if isinstance(raw, dict) and "x" in raw and "y" in raw:
        raw = [raw["x"], raw["y"]]
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise InvalidArgument(f"{where} must be [x, y], got {raw!r}.")
    return (coerce_value(raw[0], float, f"{where}.x"),
            coerce_value(raw[1], float, f"{where}.y"))


def points(raw, where: str = "points", minimum: int = 2
           ) -> list[tuple[float, float]]:
    """A list of ``[x, y]`` pairs, at least ``minimum`` long."""
    if not isinstance(raw, (list, tuple)):
        raise InvalidArgument(f"{where} must be a list of [x, y] pairs.")
    out = [point(p, f"{where}[{i}]") for i, p in enumerate(raw)]
    if len(out) < minimum:
        raise InvalidArgument(f"{where} needs at least {minimum} points, "
                              f"got {len(out)}.")
    return out

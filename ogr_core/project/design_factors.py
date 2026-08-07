# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Design standard partial factors — phase M6.

v0.1.52 made the partial factors *configurable*; this module makes them
*apply*. A setting that changes nothing is worse than no setting at all,
because the user believes the analysis honours it.

**The factors are applied by transforming a COPY of the project, not by
altering the solver.** That choice matters:

* every analysis path — deterministic, probabilistic, transient,
  optimisation — gets the factored values automatically, because they all
  read the same project;
* the solver stays a pure limit-equilibrium engine with no notion of any
  design code, so a new standard is a table of numbers rather than a
  change to the mathematics;
* the original project is never modified, so switching the standard off
  restores the unfactored results exactly.

**Convention.** Material factors *divide* (they reduce strength) and
action factors *multiply* (they increase load), following Eurocode 7,
where a partial factor is always applied so as to be unfavourable. The
friction angle is factored on **tan φ**, not on φ itself — that is what
the code specifies, and the difference is not negligible: dividing 30° by
1.25 gives 24.0°, whereas dividing tan 30° by 1.25 gives 24.79°.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

# Strength parameters that are factored, and how. Anything not listed is
# left alone: applying a factor to a parameter the code says nothing
# about would be inventing a standard rather than following one.
_COHESION_PARAMS = ("cohesion", "cohesion_top", "undrained_strength",
                    "constant_c", "c")
_FRICTION_PARAMS = ("friction_angle", "phi", "friction_angle_top")


@dataclass
class FactorReport:
    """What was factored, so the user can check it."""

    standard: str = "none"
    applied: bool = False
    materials: list = field(default_factory=list)
    loads: int = 0
    notes: list = field(default_factory=list)

    def summary(self) -> str:
        if not self.applied:
            return "no partial factors applied"
        return (f"{self.standard}: {len(self.materials)} material(s) and "
                f"{self.loads} load(s) factored")


def factor_friction_angle(phi_deg: float, factor: float) -> float:
    """Reduce a friction angle through **tan φ**.

    Eurocode 7 factors the tangent, not the angle. Dividing 30° by 1.25
    gives 24.00°; dividing tan 30° by 1.25 gives 24.79°, so getting this
    wrong is conservative by roughly 0.8° — small, but wrong in a way
    that would quietly disagree with a hand check.
    """
    if factor <= 0:
        return phi_deg
    phi = max(-89.9, min(89.9, float(phi_deg)))
    return math.degrees(math.atan(math.tan(math.radians(phi)) / factor))


def apply_design_factors(project, settings=None):
    """Return a factored **copy** of ``project``, plus a report.

    When the design standard is disabled the original project is returned
    untouched, so the feature costs nothing when unused and cannot
    perturb a result by being merely present.
    """
    ds = settings if settings is not None else \
        getattr(getattr(project, "settings", None), "design_standard",
                None)
    rep = FactorReport()
    if ds is None or not getattr(ds, "enabled", False):
        return project, rep

    rep.standard = getattr(ds, "standard", "custom")
    from ogr_core.project import Project
    factored = Project.from_dict(project.to_dict())

    f_c = float(getattr(ds, "factor_cohesion", 1.0) or 1.0)
    f_phi = float(getattr(ds, "factor_friction", 1.0) or 1.0)
    f_gamma = float(getattr(ds, "factor_unit_weight", 1.0) or 1.0)
    f_perm = float(getattr(ds, "factor_permanent", 1.0) or 1.0)
    f_var = float(getattr(ds, "factor_variable", 1.0) or 1.0)

    for mat in factored.materials:
        changed = {}
        strength = getattr(mat, "strength", None)
        params = getattr(strength, "params", None)
        if params:
            for key in list(params):
                value = params[key]
                if not isinstance(value, (int, float)) or \
                        isinstance(value, bool):
                    continue
                if key in _COHESION_PARAMS and f_c != 1.0:
                    params[key] = value / f_c
                    changed[key] = (value, params[key])
                elif key in _FRICTION_PARAMS and f_phi != 1.0:
                    params[key] = factor_friction_angle(value, f_phi)
                    changed[key] = (value, params[key])
        if f_gamma != 1.0:
            for attr in ("unit_weight", "sat_unit_weight"):
                value = getattr(mat, attr, None)
                if isinstance(value, (int, float)) and value:
                    # Unit weight MULTIPLIES: a heavier soil is the
                    # unfavourable direction for a driving weight.
                    setattr(mat, attr, value * f_gamma)
                    changed[attr] = (value, value * f_gamma)
        if changed:
            rep.materials.append({"name": mat.name, "changes": changed})

    if f_perm != 1.0 or f_var != 1.0:
        for group, factor in ((getattr(factored, "distributed_loads", []),
                               f_var),
                              (getattr(factored, "line_loads", []),
                               f_var)):
            for load in group:
                for attr in ("magnitude", "magnitude_1", "magnitude_2"):
                    value = getattr(load, attr, None)
                    if isinstance(value, (int, float)) and value:
                        setattr(load, attr, value * factor)
                        rep.loads += 1

    if f_gamma == 1.0 and f_c == 1.0 and f_phi == 1.0 \
            and f_perm == 1.0 and f_var == 1.0:
        rep.notes.append(
            "The standard is enabled but every factor is 1.0, so nothing "
            "changed.")
    rep.applied = True
    return factored, rep

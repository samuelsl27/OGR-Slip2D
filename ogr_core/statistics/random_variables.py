# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Random variables — Phase P1 of the probabilistic plan.

A random variable identifies **which parameter of which object** in the
model is uncertain, and attaches a statistical distribution to it. The
reference allows almost any input parameter to become one; this module
covers the categories it lists explicitly:

    MATERIAL_STRENGTH   a parameter of the material's strength model
                        (cohesion, friction angle, and the parameters of
                        every non-linear model)
    MATERIAL            unit weight, saturated unit weight, phi_b, air
                        entry value, Ru, constant pore pressure
    HYDRAULIC           saturated permeability and the unsaturated
                        parameters
    SUPPORT             a parameter of a support type (tensile capacity,
                        spacing, bond strength...)
    DISTRIBUTED_LOAD    magnitude 1 / magnitude 2
    LINE_LOAD           magnitude
    SEISMIC             horizontal and vertical seismic coefficients
    WATER_TABLE         a vertical offset applied to the water table

The design deliberately keeps a *path*-like description (kind, target id,
parameter name) rather than object references, so a variable definition
survives serialisation and can be applied to a COPY of the project — the
probabilistic engine never mutates the user's model.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .distributions import Distribution, DistributionType


class VariableKind(Enum):
    MATERIAL_STRENGTH = "material_strength"
    MATERIAL = "material"
    HYDRAULIC = "hydraulic"
    SUPPORT = "support"
    DISTRIBUTED_LOAD = "distributed_load"
    LINE_LOAD = "line_load"
    SEISMIC = "seismic"
    WATER_TABLE = "water_table"


# Direct attributes of Material that may be randomised
_MATERIAL_PARAMS = ("unit_weight", "sat_unit_weight", "ru", "constant_u",
                    "phi_b", "air_entry_value")
_HYDRAULIC_PARAMS = ("ks", "k2_k1", "k1_angle_deg", "bc_lambda",
                     "bc_psi_b", "fx_a", "fx_b", "fx_c", "gardner_a",
                     "gardner_n", "vg_alpha", "vg_n", "wc_sat", "wc_res",
                     "specific_storage")
_SEISMIC_PARAMS = ("kh", "kv")
_DIST_LOAD_PARAMS = ("magnitude_1", "magnitude_2")
_LINE_LOAD_PARAMS = ("magnitude",)


@dataclass
class RandomVariable:
    """One uncertain model input."""

    kind: VariableKind = VariableKind.MATERIAL_STRENGTH
    target_id: str = ""          # material / support / load id
    param: str = ""              # parameter name
    distribution: Distribution = field(default_factory=Distribution)
    # Correlation with another variable of the SAME material. Used for
    # the cohesion / friction-angle correlation the reference offers for
    # Mohr-Coulomb materials.
    correlated_with: Optional[str] = None
    correlation: float = 0.0
    label: str = ""

    # ------------------------------------------------------------------
    @property
    def key(self) -> str:
        """Stable identifier used as the sampling dictionary key."""
        return f"{self.kind.value}:{self.target_id}:{self.param}"

    def to_dict(self) -> dict:
        return {"kind": self.kind.value, "target_id": self.target_id,
                "param": self.param, "label": self.label,
                "distribution": self.distribution.to_dict(),
                "correlated_with": self.correlated_with,
                "correlation": self.correlation}

    @classmethod
    def from_dict(cls, d: dict) -> "RandomVariable":
        return cls(
            kind=VariableKind(d.get("kind", "material_strength")),
            target_id=str(d.get("target_id", "")),
            param=str(d.get("param", "")),
            label=str(d.get("label", "")),
            distribution=Distribution.from_dict(d.get("distribution", {})),
            correlated_with=d.get("correlated_with"),
            correlation=float(d.get("correlation", 0.0)),
        )


# ======================================================================
# Reading and writing a parameter on a project
# ======================================================================
def _find_material(project, mat_id):
    for m in getattr(project, "materials", []):
        if m.id == mat_id:
            return m
    return None


def _find_support(project, sup_id):
    for s in getattr(project, "supports", []):
        if getattr(s, "id", None) == sup_id:
            return s
        stype = getattr(s, "support_type", None)
        if stype is not None and getattr(stype, "id", None) == sup_id:
            return stype
    return None


def _find_load(project, load_id, attr):
    for ld in getattr(project, attr, []):
        if getattr(ld, "id", None) == load_id:
            return ld
    return None


def get_value(project, rv: RandomVariable) -> Optional[float]:
    """Current (deterministic) value of the parameter, or None."""
    k = rv.kind
    if k == VariableKind.MATERIAL_STRENGTH:
        m = _find_material(project, rv.target_id)
        if m is None or m.strength is None:
            return None
        return m.strength.params.get(rv.param)
    if k == VariableKind.MATERIAL:
        m = _find_material(project, rv.target_id)
        return None if m is None else getattr(m, rv.param, None)
    if k == VariableKind.HYDRAULIC:
        m = _find_material(project, rv.target_id)
        if m is None or m.hydraulic is None:
            return None
        return getattr(m.hydraulic, rv.param, None)
    if k == VariableKind.SUPPORT:
        s = _find_support(project, rv.target_id)
        return None if s is None else getattr(s, rv.param, None)
    if k == VariableKind.DISTRIBUTED_LOAD:
        ld = _find_load(project, rv.target_id, "distributed_loads")
        return None if ld is None else getattr(ld, rv.param, None)
    if k == VariableKind.LINE_LOAD:
        ld = _find_load(project, rv.target_id, "line_loads")
        return None if ld is None else getattr(ld, rv.param, None)
    if k == VariableKind.SEISMIC:
        return getattr(project.seismic, rv.param, None)
    if k == VariableKind.WATER_TABLE:
        return 0.0        # the variable is an OFFSET, mean zero
    return None


def set_value(project, rv: RandomVariable, value: float) -> bool:
    """Write ``value`` into the project. Returns False if not applicable."""
    k = rv.kind
    if k == VariableKind.MATERIAL_STRENGTH:
        m = _find_material(project, rv.target_id)
        if m is None or m.strength is None:
            return False
        if rv.param not in m.strength.params:
            return False
        m.strength.params[rv.param] = float(value)
        return True
    if k == VariableKind.MATERIAL:
        m = _find_material(project, rv.target_id)
        if m is None or not hasattr(m, rv.param):
            return False
        setattr(m, rv.param, float(value))
        return True
    if k == VariableKind.HYDRAULIC:
        m = _find_material(project, rv.target_id)
        if m is None or m.hydraulic is None:
            return False
        if not hasattr(m.hydraulic, rv.param):
            return False
        setattr(m.hydraulic, rv.param, float(value))
        return True
    if k == VariableKind.SUPPORT:
        s = _find_support(project, rv.target_id)
        if s is None or not hasattr(s, rv.param):
            return False
        setattr(s, rv.param, float(value))
        return True
    if k in (VariableKind.DISTRIBUTED_LOAD, VariableKind.LINE_LOAD):
        attr = ("distributed_loads" if k == VariableKind.DISTRIBUTED_LOAD
                else "line_loads")
        ld = _find_load(project, rv.target_id, attr)
        if ld is None or not hasattr(ld, rv.param):
            return False
        setattr(ld, rv.param, float(value))
        return True
    if k == VariableKind.SEISMIC:
        if not hasattr(project.seismic, rv.param):
            return False
        setattr(project.seismic, rv.param, float(value))
        # A non-zero coefficient implies the seismic load is active
        if abs(float(value)) > 0:
            project.seismic.enabled = True
        return True
    if k == VariableKind.WATER_TABLE:
        return _shift_water_table(project, float(value))
    return False


def _shift_water_table(project, offset: float) -> bool:
    """Shift every water-table vertex vertically by ``offset``.

    The reference lets the water table LOCATION be a random variable;
    a rigid vertical shift is the standard way of expressing that
    uncertainty, and it keeps the surface's shape intact.
    """
    from ogr_core.geometry import BoundaryType, Vertex
    moved = False
    for b in getattr(project, "boundaries", []):
        if b.btype != BoundaryType.WATER_TABLE:
            continue
        verts = b.polyline.vertices
        for i, v in enumerate(verts):
            verts[i] = Vertex(v.x, v.y + offset)
        moved = True
    return moved


# ======================================================================
def available_variables(project) -> list:
    """Every parameter of the project that could become a random
    variable, as ready-to-edit :class:`RandomVariable` objects whose
    distribution mean is already set to the current value.

    This is what feeds the reference's three-step "Add Random Variables"
    wizard: choose objects, choose parameters, set statistics.
    """
    out: list[RandomVariable] = []

    def _add(kind, tid, param, value, label):
        if value is None:
            return
        try:
            v = float(value)
        except (TypeError, ValueError):
            return
        out.append(RandomVariable(
            kind=kind, target_id=tid, param=param, label=label,
            distribution=Distribution(DistributionType.NORMAL, mean=v)))

    for m in getattr(project, "materials", []):
        if m.strength is not None:
            for name, val in m.strength.params.items():
                _add(VariableKind.MATERIAL_STRENGTH, m.id, name, val,
                     f"{m.name} — {name}")
        for name in _MATERIAL_PARAMS:
            _add(VariableKind.MATERIAL, m.id, name,
                 getattr(m, name, None), f"{m.name} — {name}")
        if getattr(m, "hydraulic", None) is not None:
            for name in _HYDRAULIC_PARAMS:
                _add(VariableKind.HYDRAULIC, m.id, name,
                     getattr(m.hydraulic, name, None),
                     f"{m.name} — hydraulic {name}")

    for s in getattr(project, "supports", []):
        stype = getattr(s, "support_type", None) or s
        tid = getattr(s, "id", None) or getattr(stype, "id", "")
        spec = getattr(stype, "PARAMETERS", {}) or {}
        for name in spec:
            _add(VariableKind.SUPPORT, tid, name,
                 getattr(stype, name, None),
                 f"{getattr(stype, 'DISPLAY_NAME', 'support')} — {name}")

    for ld in getattr(project, "distributed_loads", []):
        for name in _DIST_LOAD_PARAMS:
            _add(VariableKind.DISTRIBUTED_LOAD, ld.id, name,
                 getattr(ld, name, None),
                 f"{getattr(ld, 'name', 'load')} — {name}")
    for ld in getattr(project, "line_loads", []):
        for name in _LINE_LOAD_PARAMS:
            _add(VariableKind.LINE_LOAD, ld.id, name,
                 getattr(ld, name, None),
                 f"{getattr(ld, 'name', 'line load')} — {name}")

    seis = getattr(project, "seismic", None)
    if seis is not None:
        for name in _SEISMIC_PARAMS:
            _add(VariableKind.SEISMIC, "", name,
                 getattr(seis, name, 0.0), f"seismic {name}")

    from ogr_core.geometry import BoundaryType
    if any(b.btype == BoundaryType.WATER_TABLE
           for b in getattr(project, "boundaries", [])):
        out.append(RandomVariable(
            kind=VariableKind.WATER_TABLE, target_id="", param="offset",
            label="Water table — vertical offset",
            distribution=Distribution(DistributionType.NORMAL, mean=0.0)))
    return out


# ======================================================================
def clone_project(project):
    """A deep, independent copy of the project.

    The probabilistic engine applies each sample to a clone so the user's
    model is never mutated — a hard requirement, since a run may involve
    thousands of samples.
    """
    return copy.deepcopy(project)


def apply_sample(project, variables: list, sample: dict) -> int:
    """Apply one sample (``key -> value``) to ``project`` in place.

    Returns the number of parameters actually written, so the caller can
    detect a definition that no longer matches the model (for instance a
    material that has since been deleted).
    """
    applied = 0
    for rv in variables:
        if rv.key not in sample:
            continue
        if set_value(project, rv, sample[rv.key]):
            applied += 1
    return applied


def unwritable_variables(project, variables: list, sample: dict) -> list:
    """Keys of ``variables`` that ``set_value`` refuses on this model.

    ``apply_sample`` answers with a COUNT, which is enough to know THAT a
    definition no longer matches the model but not enough to name it. This
    names it, and the callers only ask once a short count has already said
    something is wrong, so a healthy run never enters here. What a healthy
    run DOES pay is the one probe clone its caller makes to get the count:
    one deepcopy against ``num_samples`` of them, and the sentence is
    written out because a docstring that rounds that to "free" is how a
    wrong measurement survives two versions.

    Measured on a throwaway clone, for two reasons and the second is not
    the obvious one: ``set_value`` WRITES, so the caller's project cannot
    be the probe; and the water-table variable is an OFFSET
    (``_shift_water_table``), so asking an already-sampled clone a second
    time would shift the table twice and answer about a model that never
    existed.
    """
    probe = clone_project(project)
    return [rv.key for rv in variables
            if rv.key in sample and not set_value(probe, rv, sample[rv.key])]


def sample_project_variables(variables: list, n: int, method, seed=None,
                             correlate: bool = False):
    """Generate ``n`` samples for a list of random variables, honouring
    the declared correlations.

    Correlated pairs are post-processed with rank reordering, which
    preserves each marginal distribution exactly.

    ``correlate`` is the project-wide Latin Hypercube option and is a
    different thing from a declared correlation between two variables:
    it shares one stratification across ALL of them. The per-pair rank
    reordering below still runs on top of it.
    """
    from .distributions import correlate_pair, sample_variables

    active = [rv for rv in variables if rv.distribution.is_random]
    dists = {rv.key: rv.distribution for rv in active}
    samples = sample_variables(dists, n, method, seed, correlate=correlate)

    by_key = {rv.key: rv for rv in active}
    for rv in active:
        if not rv.correlated_with or abs(rv.correlation) < 1e-12:
            continue
        other = by_key.get(rv.correlated_with)
        if other is None or other.key not in samples:
            continue
        samples[rv.key] = correlate_pair(
            samples[other.key], samples[rv.key], rv.correlation)
    return samples


# ======================================================================
# v0.1.201 (spec 008, F3b) — the dialog's rules, moved here so an agent's
# variables follow the same ones.
# ======================================================================
def default_dispersion(rv: RandomVariable) -> RandomVariable:
    """Give a new variable a starting dispersion: a standard deviation of
    10 % of its mean and a range of 30 % either side (the dialog's comment
    said "10 % either side", which is the deviation, not the range). With
    a mean of zero (kh, kv, a water-table offset) the same numbers are
    absolute: 0.1 and 0.3."""
    m = abs(rv.distribution.mean) or 1.0
    rv.distribution.std_dev = 0.1 * m
    rv.distribution.rel_min = 0.3 * m
    rv.distribution.rel_max = 0.3 * m
    return rv


def forget_variable(variables: list, key: str) -> list:
    """``variables`` without the one keyed ``key``; a correlation that
    pointed at it is cleared, not left dangling."""
    out = [rv for rv in variables if rv.key != key]
    for rv in out:
        if rv.correlated_with == key:
            rv.correlated_with = None
            rv.correlation = 0.0
    return out


def variable_problems(rv: RandomVariable, keys) -> list:
    """What makes ``rv`` unusable next to the variables keyed ``keys``;
    empty when nothing does."""
    from .distributions import DistributionType

    d = rv.distribution
    out = []
    if d.std_dev < 0 or d.rel_min < 0 or d.rel_max < 0:
        out.append("std_dev, rel_min and rel_max cannot be negative.")
    if d.dist_type in (DistributionType.NORMAL, DistributionType.LOGNORMAL,
                       DistributionType.BETA, DistributionType.GAMMA) \
            and d.std_dev <= 0:
        out.append(f"A {d.dist_type.value} distribution needs a positive "
                   f"std_dev; with none the variable is not random.")
    if d.dist_type != DistributionType.NONE and d.high - d.low <= 0:
        out.append("rel_min + rel_max must be positive: a zero range is "
                   "not random.")
    if rv.correlated_with is not None:
        if rv.correlated_with == rv.key:
            out.append("A variable cannot be correlated with itself.")
        elif rv.correlated_with not in set(keys):
            out.append(f"correlated_with {rv.correlated_with!r} is not a "
                       f"defined variable.")
        if not -1.0 <= rv.correlation <= 1.0:
            out.append("correlation must be between -1 and 1.")
    elif rv.correlation:
        out.append("correlation is only read with correlated_with.")
    return out

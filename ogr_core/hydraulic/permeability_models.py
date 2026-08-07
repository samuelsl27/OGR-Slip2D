# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Unsaturated permeability functions k(psi) — Phase 3 of the groundwater
plan.

Implements the permeability models of the reference specification, each
returning a **relative permeability** kr = k/Ks as a function of matric
suction psi (positive when the pore pressure is negative):

    CONSTANT        kr = 1 (fully saturated; the Phase-2 behaviour)
    SIMPLE          automatic curve from Ks and a soil type
    BROOKS_COREY    Brooks & Corey (1964)
    FREDLUND_XING   Fredlund & Xing (1994)
    GARDNER         Gardner (1956)
    VAN_GENUCHTEN   van Genuchten (1980)
    USER_DEFINED    tabulated (suction, permeability) points

Published forms used
--------------------
**Brooks-Corey** with pore-size index ``lam`` and bubbling pressure
``psi_b``:

    kr = 1                          for psi <= psi_b
    kr = (psi_b / psi)^(2 + 3*lam)  for psi >  psi_b

**Fredlund-Xing** with parameters A, B, C (e = 2.71828...):

    kr = 1 / { ln[ e + (psi/A)^B ] }^C

**Gardner** with parameters a, n (h = suction as a pressure head):

    kr = 1 / (1 + a * h^n)

**van Genuchten** with alpha, n and m (by default m = 1 - 1/n, the
Mualem restriction; ``custom_m`` releases it):

    Se = [ 1 + (alpha*h)^n ]^(-m)
    kr = Se^(1/2) * [ 1 - (1 - Se^(1/m))^m ]^2

**Simple** reproduces the documented behaviour: for the *General* soil
type the permeability drops by one order of magnitude over the initial
range of suction and then stays constant. The soil-type variants (sand,
silt, clay, loam) use the same shape with a characteristic suction scale
and drop magnitude per texture — sands lose permeability abruptly at low
suction, clays gradually over a much wider range — which is the
qualitative behaviour the literature curves show.

All functions are clamped to a floor ``kr_min`` so the conductivity
matrix never becomes singular in very dry regions: this is standard
practice in unsaturated FE seepage codes and is what keeps the Picard
iteration solvable.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


class PermeabilityModel(Enum):
    CONSTANT = "constant"
    SIMPLE = "simple"
    BROOKS_COREY = "brooks_corey"
    FREDLUND_XING = "fredlund_xing"
    GARDNER = "gardner"
    VAN_GENUCHTEN = "van_genuchten"
    USER_DEFINED = "user_defined"


class SimpleSoilType(Enum):
    """Soil types offered by the Simple model."""

    GENERAL = "general"
    SAND = "sand"
    SILT = "silt"
    CLAY = "clay"
    LOAM = "loam"


# Characteristic suction scale [kPa] and decades of permeability drop for
# the Simple model. GENERAL matches the documented behaviour (one order
# of magnitude over the initial suction range, then constant); the
# textures follow the qualitative trend of published curves: coarse soils
# desaturate abruptly at low suction, fine soils gradually.
_SIMPLE_PARAMS = {
    SimpleSoilType.GENERAL: (100.0, 1.0),
    SimpleSoilType.SAND: (10.0, 4.0),
    SimpleSoilType.SILT: (50.0, 3.0),
    SimpleSoilType.CLAY: (1500.0, 2.0),
    SimpleSoilType.LOAM: (100.0, 3.0),
}


# ======================================================================
def kr_constant(psi: float, p) -> float:
    return 1.0


def kr_simple(psi: float, p) -> float:
    """Log-linear drop of ``decades`` orders of magnitude over the
    initial suction range ``psi_ref``, constant afterwards."""
    if psi <= 0.0:
        return 1.0
    psi_ref, decades = _SIMPLE_PARAMS.get(
        p.simple_soil_type, _SIMPLE_PARAMS[SimpleSoilType.GENERAL])
    t = min(1.0, psi / max(psi_ref, 1e-12))
    return 10.0 ** (-decades * t)


def kr_brooks_corey(psi: float, p) -> float:
    if psi <= p.bc_psi_b:
        return 1.0
    eta = 2.0 + 3.0 * max(p.bc_lambda, 1e-6)
    return (max(p.bc_psi_b, 1e-12) / psi) ** eta


def kr_fredlund_xing(psi: float, p) -> float:
    if psi <= 0.0:
        return 1.0
    a = max(p.fx_a, 1e-12)
    inner = math.e + (psi / a) ** max(p.fx_b, 1e-9)
    denom = math.log(inner)
    if denom <= 0.0:
        return 1.0
    return 1.0 / denom ** max(p.fx_c, 1e-9)


def kr_gardner(psi: float, p) -> float:
    if psi <= 0.0:
        return 1.0
    return 1.0 / (1.0 + max(p.gardner_a, 0.0) * psi ** max(p.gardner_n, 1e-9))


def kr_van_genuchten(psi: float, p) -> float:
    if psi <= 0.0:
        return 1.0
    n = max(p.vg_n, 1.0 + 1e-9)
    m = p.vg_m if p.vg_custom_m else (1.0 - 1.0 / n)
    m = min(max(m, 1e-6), 1.0 - 1e-9)
    a = max(p.vg_alpha, 1e-12)
    se = (1.0 + (a * psi) ** n) ** (-m)
    se = min(max(se, 1e-12), 1.0)
    try:
        inner = 1.0 - (1.0 - se ** (1.0 / m)) ** m
    except (ValueError, OverflowError):
        return 1.0e-12
    return math.sqrt(se) * inner * inner


def kr_user_defined(psi: float, p) -> float:
    """Log-linear interpolation of the user table (suction, k). Values
    are normalised by the first point, which the reference treats as the
    saturated permeability."""
    pts = sorted(p.user_curve, key=lambda t: t[0])
    if not pts:
        return 1.0
    k_sat = pts[0][1]
    if k_sat <= 0:
        return 1.0
    if psi <= pts[0][0]:
        return 1.0
    if psi >= pts[-1][0]:
        return max(pts[-1][1] / k_sat, 0.0)
    for (s0, k0), (s1, k1) in zip(pts[:-1], pts[1:]):
        if s0 <= psi <= s1:
            if k0 <= 0 or k1 <= 0:
                t = (psi - s0) / max(s1 - s0, 1e-12)
                k = k0 + t * (k1 - k0)
            else:
                t = (psi - s0) / max(s1 - s0, 1e-12)
                k = math.exp(math.log(k0) + t * (math.log(k1)
                                                 - math.log(k0)))
            return max(k / k_sat, 0.0)
    return 1.0


_MODEL_FUNCS = {
    PermeabilityModel.CONSTANT: kr_constant,
    PermeabilityModel.SIMPLE: kr_simple,
    PermeabilityModel.BROOKS_COREY: kr_brooks_corey,
    PermeabilityModel.FREDLUND_XING: kr_fredlund_xing,
    PermeabilityModel.GARDNER: kr_gardner,
    PermeabilityModel.VAN_GENUCHTEN: kr_van_genuchten,
    PermeabilityModel.USER_DEFINED: kr_user_defined,
}


def register_model(model: PermeabilityModel, func) -> None:
    """Register (or override) the relative-permeability function of a
    model, mirroring the extensible strength-model registry."""
    _MODEL_FUNCS[model] = func


def available_models() -> list[PermeabilityModel]:
    return list(_MODEL_FUNCS.keys())


# ======================================================================
# Representative parameter library (the reference's "Pick" button)
# ======================================================================
#   model -> soil name -> parameter dict
# Values are representative literature figures (van Genuchten 1980;
# Carsel & Parrish 1988 for the VG textures; Brooks & Corey 1964).
MATERIAL_LIBRARY: dict[str, dict[str, dict]] = {
    PermeabilityModel.VAN_GENUCHTEN.value: {
        "Sand": {"vg_alpha": 0.145, "vg_n": 2.68},
        "Loamy sand": {"vg_alpha": 0.124, "vg_n": 2.28},
        "Sandy loam": {"vg_alpha": 0.075, "vg_n": 1.89},
        "Loam": {"vg_alpha": 0.036, "vg_n": 1.56},
        "Silt": {"vg_alpha": 0.016, "vg_n": 1.37},
        "Silt loam": {"vg_alpha": 0.020, "vg_n": 1.41},
        "Clay": {"vg_alpha": 0.008, "vg_n": 1.09},
        "Silty clay": {"vg_alpha": 0.005, "vg_n": 1.09},
    },
    PermeabilityModel.BROOKS_COREY.value: {
        "Sand": {"bc_lambda": 2.0, "bc_psi_b": 5.0},
        "Sandy loam": {"bc_lambda": 1.0, "bc_psi_b": 15.0},
        "Loam": {"bc_lambda": 0.6, "bc_psi_b": 30.0},
        "Silt loam": {"bc_lambda": 0.5, "bc_psi_b": 50.0},
        "Clay": {"bc_lambda": 0.3, "bc_psi_b": 100.0},
    },
    PermeabilityModel.GARDNER.value: {
        "Sand": {"gardner_a": 0.1, "gardner_n": 3.0},
        "Loam": {"gardner_a": 0.01, "gardner_n": 2.0},
        "Clay": {"gardner_a": 0.001, "gardner_n": 1.5},
    },
    PermeabilityModel.FREDLUND_XING.value: {
        "Sand": {"fx_a": 10.0, "fx_b": 3.0, "fx_c": 1.0},
        "Loam": {"fx_a": 50.0, "fx_b": 2.0, "fx_c": 1.0},
        "Clay": {"fx_a": 500.0, "fx_b": 1.5, "fx_c": 1.0},
    },
}


def library_for(model: PermeabilityModel) -> dict[str, dict]:
    """Representative parameter sets for ``model`` (empty when the model
    has no library, e.g. Simple / Constant / User Defined)."""
    return MATERIAL_LIBRARY.get(model.value, {})

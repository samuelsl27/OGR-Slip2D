# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Hydraulic (permeability) properties per material — Phase 2 of the
groundwater plan.

Mirrors the reference "Define Hydraulic Properties" specification:

    * **Saturated permeability Ks** — always required. This is the
      *primary* (K1) permeability.
    * **Anisotropic parameters** — a factor ``K2/K1`` giving the relative
      permeability in the direction orthogonal to K1, and a ``K1 angle``
      measured from the positive X (horizontal) axis.
    * **Unsaturated model** — the name of the relative-permeability
      function k(psi). Only ``"saturated"`` is honoured by the Phase-2
      solver (k constant, fully saturated flow); the others are declared
      here so the model file format is already forward compatible with
      Phase 3, which adds the non-linear unsaturated solver.

Conductivity tensor
-------------------
With principal permeabilities K1 (at angle ``theta`` from +x) and
K2 = factor * K1, the global tensor follows from a standard rotation:

    K = R(theta) . diag(K1, K2) . R(theta)^T

        Kxx = K1 cos^2(theta) + K2 sin^2(theta)
        Kyy = K1 sin^2(theta) + K2 cos^2(theta)
        Kxy = (K1 - K2) sin(theta) cos(theta)

which is symmetric positive-definite for K1, K2 > 0 — the condition the
FE stiffness matrix needs to stay solvable.

Units: Ks in length/time (e.g. m/s). The solver is unit-agnostic; heads
come out in the model's length unit.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


from .permeability_models import (  # noqa: E402
    PermeabilityModel,
    SimpleSoilType,
    library_for,
)


class UnsaturatedModel(Enum):
    """Backwards-compatible alias kept for models written by v0.1.26.

    v0.1.27 supersedes this by :class:`PermeabilityModel`, which covers
    the full reference set (Brooks-Corey and Gardner were missing).
    """

    SATURATED = "saturated"
    SIMPLE = "simple"
    VAN_GENUCHTEN = "van_genuchten"
    FREDLUND_XING = "fredlund_xing"
    USER_DEFINED = "user_defined"


@dataclass
class HydraulicProperties:
    """Permeability characteristics of one material."""

    ks: float = 1.0e-6                 # saturated permeability (K1)
    k2_k1: float = 1.0                 # K2/K1 anisotropy factor
    k1_angle_deg: float = 0.0          # K1 direction from +x axis
    # v0.1.27 — permeability model for the unsaturated zone
    model: PermeabilityModel = PermeabilityModel.CONSTANT
    kr_min: float = 1.0e-6             # relative-permeability floor
    # Simple
    simple_soil_type: SimpleSoilType = SimpleSoilType.GENERAL
    # Brooks-Corey (1964)
    bc_lambda: float = 0.6             # pore size index
    bc_psi_b: float = 30.0             # bubbling pressure [kPa]
    # Fredlund-Xing (1994)
    fx_a: float = 50.0
    fx_b: float = 2.0
    fx_c: float = 1.0
    # Gardner (1956)
    gardner_a: float = 0.01
    gardner_n: float = 2.0
    # van Genuchten (1980)
    vg_alpha: float = 0.036            # [1/kPa]
    vg_n: float = 1.56
    vg_m: float = 0.359                # used only when vg_custom_m
    vg_custom_m: bool = False          # release m = 1 - 1/n
    # User Defined: [(suction, permeability), ...]
    user_curve: list = field(default_factory=list)
    # Water content / storage (Phase 6 — transient analysis)
    wc_sat: float = 0.4                # saturated water content theta_s
    wc_res: float = 0.05               # residual water content theta_r
    # Specific storage [1/length]: elastic storage of the SATURATED zone
    # (compressibility of water plus the soil skeleton). Small compared
    # with the unsaturated storage, but it is what keeps the transient
    # system non-singular below the water table, where dtheta/dpsi = 0.
    specific_storage: float = 1.0e-5

    # ------------------------------------------------------------------
    def principal(self) -> tuple[float, float]:
        """(K1, K2) principal permeabilities."""
        k1 = max(float(self.ks), 0.0)
        k2 = k1 * max(float(self.k2_k1), 0.0)
        return k1, k2

    def conductivity_tensor(self) -> tuple[float, float, float]:
        """(Kxx, Kyy, Kxy) of the global conductivity tensor."""
        k1, k2 = self.principal()
        th = math.radians(float(self.k1_angle_deg))
        c, s = math.cos(th), math.sin(th)
        kxx = k1 * c * c + k2 * s * s
        kyy = k1 * s * s + k2 * c * c
        kxy = (k1 - k2) * s * c
        return kxx, kyy, kxy

    # ------------------------------------------------------------------
    def relative_permeability(self, suction: float) -> float:
        """kr = k/Ks at matric suction ``suction`` [kPa].

        Suction is positive where the pore pressure is negative. Below
        zero suction (saturated) kr = 1. The result is clamped to
        ``kr_min`` so the conductivity matrix stays non-singular in very
        dry zones, which is what keeps the Picard iteration solvable.
        """
        from .permeability_models import _MODEL_FUNCS
        func = _MODEL_FUNCS.get(self.model)
        if func is None:
            return 1.0
        kr = func(max(0.0, float(suction)), self)
        if not math.isfinite(kr):
            return self.kr_min
        return min(1.0, max(self.kr_min, kr))

    def k_at_suction(self, suction: float) -> float:
        """Absolute permeability at a given suction."""
        return self.ks * self.relative_permeability(suction)

    def conductivity_tensor_at(self, suction: float
                               ) -> tuple[float, float, float]:
        """Global conductivity tensor scaled by kr(suction). The
        anisotropy ratio and direction are unchanged in the unsaturated
        zone, matching the reference note that K1 is defined by Ks *and*
        the unsaturated model."""
        kr = self.relative_permeability(suction)
        kxx, kyy, kxy = self.conductivity_tensor()
        return kxx * kr, kyy * kr, kxy * kr

    # ------------------------------------------------------------------
    def water_content(self, suction: float) -> float:
        """Volumetric water content theta at matric suction ``suction``.

        Uses the van Genuchten (1980) retention curve for every model,
        parameterised by ``vg_alpha``/``vg_n`` and the saturated and
        residual water contents. The reference likewise keeps the
        retention curve separate from the permeability function: the
        latter governs how fast water MOVES, the former how much water is
        STORED, and only the second matters for the transient storage
        term.
        """
        if suction <= 0.0:
            return self.wc_sat
        n = max(self.vg_n, 1.0 + 1e-9)
        m = self.vg_m if self.vg_custom_m else (1.0 - 1.0 / n)
        m = min(max(m, 1e-6), 1.0 - 1e-9)
        a = max(self.vg_alpha, 1e-12)
        se = (1.0 + (a * suction) ** n) ** (-m)
        se = min(max(se, 0.0), 1.0)
        return self.wc_res + (self.wc_sat - self.wc_res) * se

    def specific_moisture_capacity(self, suction: float) -> float:
        """C = d(theta)/d(pressure head) — the transient storage term.

        Below the water table (suction <= 0) the soil is saturated and
        the moisture capacity vanishes, so the ELASTIC specific storage
        governs instead; that substitution is done by the solver. The
        derivative is evaluated analytically for the van Genuchten curve:

            dSe/dpsi = -m n a (a psi)^(n-1) [1 + (a psi)^n]^(-m-1)

        and dtheta/d(pressure head) = -dtheta/d(suction), since pressure
        head = -suction.
        """
        if suction <= 0.0:
            return 0.0
        n = max(self.vg_n, 1.0 + 1e-9)
        m = self.vg_m if self.vg_custom_m else (1.0 - 1.0 / n)
        m = min(max(m, 1e-6), 1.0 - 1e-9)
        a = max(self.vg_alpha, 1e-12)
        ap = a * suction
        try:
            dse_dpsi = (-m * n * a * ap ** (n - 1.0)
                        * (1.0 + ap ** n) ** (-m - 1.0))
        except (OverflowError, ValueError):
            return 0.0
        dtheta_dpsi = (self.wc_sat - self.wc_res) * dse_dpsi
        # d/d(pressure head) = -d/d(suction); the capacity is positive
        return abs(dtheta_dpsi)

    def storage_content(self, pressure_head: float) -> float:
        """Generalised stored-water content W(P) [-].

        The mixed form of Richards' equation accumulates ``theta``, which
        works in the unsaturated zone but is CONSTANT once saturated —
        so the elastic storage below the water table would vanish and the
        transient problem would collapse onto the steady state. Both
        mechanisms are unified by carrying

            W(P) = theta(-P)             for P < 0   (capillary storage)
            W(P) = theta_s + Ss * P      for P >= 0  (elastic storage)

        whose derivative is exactly :meth:`storage_at`, so the modified
        Picard linearisation stays consistent in both zones.
        """
        if pressure_head < 0.0:
            return self.water_content(-pressure_head)
        return self.wc_sat + max(self.specific_storage, 0.0) * pressure_head

    def storage_at(self, pressure_head: float) -> float:
        """Storage coefficient at a given pressure head.

        Saturated (P >= 0): elastic specific storage Ss.
        Unsaturated (P < 0): specific moisture capacity C(psi), which is
        orders of magnitude larger — this is why a falling water table
        releases far more water than an equal drop in a confined aquifer.
        """
        if pressure_head >= 0.0:
            return max(self.specific_storage, 0.0)
        c = self.specific_moisture_capacity(-pressure_head)
        return max(c, self.specific_storage * 1e-3)

    def library(self) -> dict:
        """Representative parameter sets for the current model (the
        reference's "Pick" button)."""
        return library_for(self.model)

    def curve(self, psi_max: float = 1000.0, n: int = 60) -> list:
        """(suction, kr) samples for plotting the permeability function
        (the reference's "Plot" button). Log-spaced from 0.1 kPa."""
        out = [(0.0, self.relative_permeability(0.0))]
        lo = math.log10(0.1)
        hi = math.log10(max(psi_max, 1.0))
        for i in range(n):
            psi = 10.0 ** (lo + (hi - lo) * i / (n - 1))
            out.append((psi, self.relative_permeability(psi)))
        return out

    def is_isotropic(self) -> bool:
        return abs(self.k2_k1 - 1.0) < 1e-12

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "ks": self.ks,
            "k2_k1": self.k2_k1,
            "k1_angle_deg": self.k1_angle_deg,
            "model": self.model.value,
            "kr_min": self.kr_min,
            "simple_soil_type": self.simple_soil_type.value,
            "bc_lambda": self.bc_lambda,
            "bc_psi_b": self.bc_psi_b,
            "fx_a": self.fx_a, "fx_b": self.fx_b, "fx_c": self.fx_c,
            "gardner_a": self.gardner_a, "gardner_n": self.gardner_n,
            "vg_alpha": self.vg_alpha, "vg_n": self.vg_n,
            "vg_m": self.vg_m, "vg_custom_m": self.vg_custom_m,
            "user_curve": [list(p) for p in self.user_curve],
            "wc_sat": self.wc_sat, "wc_res": self.wc_res,
            "specific_storage": self.specific_storage,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HydraulicProperties":
        return cls(
            ks=float(d.get("ks", 1.0e-6)),
            k2_k1=float(d.get("k2_k1", 1.0)),
            k1_angle_deg=float(d.get("k1_angle_deg", 0.0)),
            model=_model_from_dict(d),
            kr_min=float(d.get("kr_min", 1.0e-6)),
            simple_soil_type=SimpleSoilType(
                d.get("simple_soil_type", "general")),
            bc_lambda=float(d.get("bc_lambda", 0.6)),
            bc_psi_b=float(d.get("bc_psi_b", 30.0)),
            fx_a=float(d.get("fx_a", 50.0)),
            fx_b=float(d.get("fx_b", 2.0)),
            fx_c=float(d.get("fx_c", 1.0)),
            gardner_a=float(d.get("gardner_a", 0.01)),
            gardner_n=float(d.get("gardner_n", 2.0)),
            vg_alpha=float(d.get("vg_alpha", 0.036)),
            vg_n=float(d.get("vg_n", 1.56)),
            vg_m=float(d.get("vg_m", 0.359)),
            vg_custom_m=bool(d.get("vg_custom_m", False)),
            user_curve=[tuple(p) for p in d.get("user_curve", [])],
            wc_sat=float(d.get("wc_sat", 0.4)),
            wc_res=float(d.get("wc_res", 0.05)),
            specific_storage=float(d.get("specific_storage", 1.0e-5)),
        )


def _model_from_dict(d: dict) -> PermeabilityModel:
    """Read the permeability model, accepting the v0.1.26 key
    ``unsaturated_model`` (where "saturated" meant constant k)."""
    if "model" in d:
        try:
            return PermeabilityModel(d["model"])
        except ValueError:
            return PermeabilityModel.CONSTANT
    legacy = d.get("unsaturated_model")
    if legacy in (None, "saturated"):
        return PermeabilityModel.CONSTANT
    try:
        return PermeabilityModel(legacy)
    except ValueError:
        return PermeabilityModel.CONSTANT

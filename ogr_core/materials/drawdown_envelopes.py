# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Undrained strength envelopes for rapid drawdown, and the conversion
between them.

Isotropically-consolidated undrained (IC-U) triaxial tests can be plotted
two ways, and the multi-stage drawdown procedures disagree on which one
they want:

* the **R envelope** — the line tangent to the TOTAL-stress Mohr circles,
  with intercept ``c_R`` and slope ``tan φ_R``. Wanted by the Corps of
  Engineers two-stage procedure;
* the **Kc = 1 envelope** — the same tests plotted as
  ``τ_ff = ½(σ₁ − σ₃)_f · cos φ'`` against ``σ'_fc = σ'₃c``, with
  intercept ``d`` and slope ``tan ψ``. Wanted by Lowe-Karafiath and by
  Duncan, Wright and Wong.

They are two views of the SAME laboratory data, so the conversion is
exact and invertible — which is why a program can accept either and give
the other to whichever procedure needs it.

Derivation (so the formulae below are auditable rather than copied)
-------------------------------------------------------------------
A total-stress Mohr circle of an IC-U test has its left end at the
isotropic consolidation pressure σ'₃c and radius ``r = ½(σ₁ − σ₃)_f``, so
its centre is at ``σ'₃c + r``. The R envelope is tangent to it, so the
distance from the centre to the line equals the radius::

    (c_R + (σ'₃c + r)·tan φ_R) · cos φ_R = r

Solving for r::

    c_R + σ'₃c·tan φ_R = r · (1/cos φ_R − tan φ_R)
                       = r · (1 − sin φ_R) / cos φ_R

    r = (c_R + σ'₃c·tan φ_R) · cos φ_R / (1 − sin φ_R)

and since ``τ_ff = r · cos φ'`` and ``σ'_fc = σ'₃c``::

    τ_ff = c_R·(cos φ_R·cos φ')/(1 − sin φ_R)
         + σ'_fc·(sin φ_R·cos φ')/(1 − sin φ_R)
           └────────── d ──────────┘   └───── tan ψ ─────┘

φ' is the **effective** friction angle, from the drained envelope of the
same tests — not φ_R. A well-known tutorial calls it "the undrained
friction angle", which is a slip: with φ_R in its place neither of the
two published cases in the tests reproduces. Hence ``phi_eff`` is an
explicit argument here and never read from anywhere else: it belongs to
the material, not to the undrained envelope, and a silent default would
be the shortest path to a wrong number that looks right.

References:
    Corps of Engineers (2003). *Slope Stability*, EM 1110-2-1902,
        Appendix G: Procedures and Examples for Rapid Drawdown.
    Duncan, J. M., Wright, S. G. y Wong, K. S. (1990). "Slope Stability
        during Rapid Drawdown". H. Bolton Seed Memorial Symposium, vol. 2,
        pp. 253-272.
    Duncan, J. M. y Wright, S. G. (2005). *Soil Strength and Slope
        Stability*. Wiley.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class REnvelope:
    """Total-stress R envelope: ``τ = c_R + σ·tan φ_R``."""

    c_r: float
    phi_r_deg: float

    def strength_at(self, sigma: float) -> float:
        return self.c_r + max(0.0, sigma) * math.tan(
            math.radians(self.phi_r_deg))

    def to_kc1(self, phi_eff_deg: float) -> "Kc1Envelope":
        """Convert to the Kc = 1 envelope. ``phi_eff_deg`` is φ'."""
        phi_r = math.radians(self.phi_r_deg)
        cos_e = math.cos(math.radians(phi_eff_deg))
        denom = 1.0 - math.sin(phi_r)
        if abs(denom) < 1e-12:
            raise ValueError(
                "phi_R = 90 deg: the R envelope is vertical and has no "
                "Kc = 1 equivalent")
        d = self.c_r * (math.cos(phi_r) * cos_e) / denom
        psi = math.atan((math.sin(phi_r) * cos_e) / denom)
        return Kc1Envelope(d=d, psi_deg=math.degrees(psi))


@dataclass(frozen=True)
class Kc1Envelope:
    """Isotropically consolidated envelope: ``τ_ff = d + σ'_fc·tan ψ``."""

    d: float
    psi_deg: float

    def strength_at(self, sigma_fc: float) -> float:
        return self.d + max(0.0, sigma_fc) * math.tan(
            math.radians(self.psi_deg))

    def to_r(self, phi_eff_deg: float) -> REnvelope:
        """Convert to the R envelope. Inverse of :meth:`REnvelope.to_kc1`.

        From ``tan ψ = sin φ_R·cos φ'/(1 − sin φ_R)``, writing
        ``T = tan ψ / cos φ'`` gives ``T = sin φ_R/(1 − sin φ_R)`` and
        hence ``sin φ_R = T/(1 + T)``.
        """
        cos_e = math.cos(math.radians(phi_eff_deg))
        if abs(cos_e) < 1e-12:
            raise ValueError(
                "phi' = 90 deg: the conversion is undefined")
        t = math.tan(math.radians(self.psi_deg)) / cos_e
        if t <= -1.0:
            raise ValueError("psi out of range for a real R envelope")
        sin_phi_r = t / (1.0 + t)
        if not -1.0 < sin_phi_r < 1.0:
            raise ValueError("psi out of range for a real R envelope")
        phi_r = math.asin(sin_phi_r)
        c_r = self.d * (1.0 - sin_phi_r) / (math.cos(phi_r) * cos_e)
        return REnvelope(c_r=c_r, phi_r_deg=math.degrees(phi_r))


def composite_strength(
    tau_undrained: float,
    sigma_eff: float,
    c_eff: float,
    phi_eff_deg: float,
) -> float:
    """Corps of Engineers (1970) composite envelope: ``min(R, effective)``.

    The undrained strength, capped by the drained strength available at
    ``sigma_eff``. The stated purpose of the cap is to avoid leaning on
    strengths that can only be sustained by negative pore pressures.

    **Which effective stress goes in, and why it is the one AFTER the
    drawdown** (v0.1.69). Until this version both branches were evaluated
    at the effective stress from before it, σ'_fc, and the Corps' own
    worked example in Appendix G came out 9.6 % low — 1.220 against a
    referee value of 1.35 on a fixed circle. The reason is visible slice
    by slice: under a 100 ft reservoir the pre-drawdown effective stress
    near the toe is almost nothing (σ'_fc ≈ 200 psf), so for a soil with
    c' = 0 the drained branch collapses to ≈ 115 psf against 1257 psf
    from the R envelope, and it governed 31 of 50 slices. Pilarcitos
    could not have caught it: there the two lines cross at σ ≈ 104 psf,
    so the cap never bites and the case reproduces either way.

    Taking the drained strength at the POST-drawdown effective stress
    reproduces both published cases — Appendix G 1.334 against 1.35
    (−1.2 %), Pilarcitos 0.838 against 0.824 (+1.7 %) — and it is the
    consistent reading: the negative pore pressures the cap exists to
    distrust would arise after the drawdown, not during consolidation, so
    comparing against the consolidation stress compares two states that
    never coexist. It also leaves the Corps procedure differing from
    Duncan-Wright-Wong in exactly one thing, the undrained envelope (R
    directly against K_c = 1 interpolated by K_c), which is what the
    reference says distinguishes them.

    The cap is still what makes this the most conservative of the three
    procedures: on Pilarcitos it gives ≈ 0.84 where the other two give
    ≈ 1.05.

    v0.1.70 — the caller iterates this to a fixed point. Capping a slice
    lowers the factor of safety, which moves the normal it is read at,
    which moves the cap; one pass leaves the answer depending on where
    the iteration stopped. Converged, both Appendix G cases land within
    0.2 % of their published values instead of 1 % below. See
    ``ogr_slip2d.rapid_drawdown.CAP_RELAXATION`` for the measurement and
    for what the reference says, which is a single substitution.
    """
    drained = c_eff + max(0.0, sigma_eff) * math.tan(
        math.radians(phi_eff_deg))
    return min(tau_undrained, drained)

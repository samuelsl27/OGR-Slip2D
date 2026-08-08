# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Janbu's Simplified & Corrected Methods of Slices.

Janbu Simplified satisfies horizontal force equilibrium; inter-slice
shear forces are ignored:

                    Σ [c'·b + (W − u·b)·tan φ'] / n_α
        F  =  ────────────────────────────────────────────────
                            Σ W · tan α

with:
        n_α = cos²α · (1 + tan α · tan φ' / F)

Janbu Corrected applies an empirical factor fo:
        F_corrected = fo · F
where fo depends on the depth-to-length ratio and soil type.

For pseudo-static seismic analysis:
    - W → W·(1 − kv)
    - kh adds a horizontal driving force:
        Σ W·tan α  →  Σ W·(1−kv)·tan α + Σ kh·W·(1 − tan α · tan α)
                      ≈ Σ W·(1−kv)·tan α + Σ kh·W
      (we use the simpler approximation Σ kh·W · tan α since the
      surface is steep — this is what most practical implementations
      do for Janbu).

References:
    - Janbu, N. (1954, 1973).
    - Abramson et al. (2002), §5.5.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from typing import Optional

from ogr_core.materials import Material
from ogr_core.project import Project

from ..external_forces import slice_forces
from ..slicer import Slice, Slices
from ..surface import SurfaceProtocol
from .base import LEMMethod, LEMResult, register_method
from .bishop import BishopSimplified  # reuse envelope linearisation


@register_method
class JanbuSimplified(LEMMethod):
    METHOD_ID = "janbu_simplified"
    DISPLAY_NAME = "Janbu Simplified"
    SATISFIES_FORCE = True
    SATISFIES_MOMENT = False
    _CORRECTION: bool = False

    def compute_fos(
        self,
        project: Project,
        surface: SurfaceProtocol,
        slices: Slices,
    ) -> LEMResult:
        kh = project.seismic.kh if project.seismic.enabled else 0.0
        kv = project.seismic.kv if project.seismic.enabled else 0.0

        # Sliding direction
        driving_raw = sum(
            slice_forces(s, kh, kv).w_total * math.tan(s.base_angle)
            for s in slices
        )
        slide_sign = 1.0 if driving_raw >= 0 else -1.0

        # Driving force horizontal: Σ W·(1−kv)·tan α + Σ kh·W
        denominator = 0.0
        for s in slices:
            f = slice_forces(s, kh, kv)
            denominator += slide_sign * f.w_total * math.tan(s.base_angle)
            denominator += f.h_seismic  # horizontal seismic adds directly
            # v0.1.61 — external water thrust. The driving force is
            # measured positive along the sliding direction, whose x
            # component is −slide_sign (slide_sign = +1 means the mass
            # moves towards −x); h_water is signed in +x.
            denominator += -slide_sign * f.h_water

        if abs(denominator) < 1e-9:
            return LEMResult(
                fos=math.inf,
                converged=False,
                iterations=0,
                method_id=self.METHOD_ID,
                surface=surface,
                slices=slices,
                error_message="Zero driving force — surface does not slide",
            )

        fos = self.initial_fos
        converged = False
        iterations = 0
        for it in range(1, self.max_iterations + 1):
            iterations = it
            numerator = 0.0

            for s in slices:
                # v0.1.61 — the base normal carries the ponded-water
                # weight; the horizontal thrust belongs on the driving side
                W_eff = slice_forces(s, kh, kv).w_total
                b = s.width

                # Estimate σ'ₙ
                N_est = W_eff * math.cos(s.base_angle)
                N_eff_est = max(0.0, N_est - s.pore_pressure * s.base_length)
                sigma_n_eff = N_eff_est / max(s.base_length, 1e-9)

                c, tan_phi = BishopSimplified._local_c_phi(
                    s, s.material, sigma_n_eff
                )

                # n_α = cos²α · (1 + tan α · tan φ' / F)  (with sliding sign)
                n_alpha = (math.cos(s.base_angle) ** 2) * (
                    1.0 + slide_sign * math.tan(s.base_angle) * tan_phi / fos
                )
                if abs(n_alpha) < 1e-6:
                    return LEMResult(
                        fos=math.nan,
                        converged=False,
                        iterations=iterations,
                        method_id=self.METHOD_ID,
                        surface=surface,
                        slices=slices,
                        error_message=f"nα collapsed at slice {s.index}",
                    )

                # Numerator term: [c'·b + (W − u·b)·tan φ'] / n_α
                numerator += (
                    c * b + (W_eff - s.pore_pressure * b) * tan_phi
                ) / n_alpha

            new_fos = numerator / denominator
            if not math.isfinite(new_fos):
                return LEMResult(
                    fos=math.nan,
                    converged=False,
                    iterations=iterations,
                    method_id=self.METHOD_ID,
                    surface=surface,
                    slices=slices,
                    error_message="Non-finite FoS",
                )
            if abs(new_fos - fos) < self.tolerance:
                fos = new_fos
                converged = True
                break
            fos = new_fos

        if self._CORRECTION:
            fos *= _janbu_correction_factor(project, surface, slices)

        return LEMResult(
            fos=fos,
            converged=converged,
            iterations=iterations,
            method_id=self.METHOD_ID,
            surface=surface,
            slices=slices,
        )


@register_method
class JanbuCorrected(JanbuSimplified):
    METHOD_ID = "janbu_corrected"
    DISPLAY_NAME = "Janbu Corrected"
    _CORRECTION = True


# ----------------------------------------------------------------------
def _janbu_correction_factor(
    project: Project, surface: SurfaceProtocol, slices: Slices
) -> float:
    """Janbu (1973) empirical correction factor fo.

    Approximates the effect of inter-slice shear forces neglected in
    Janbu Simplified:

        fo = 1 + b1 · [(d/L) − 1.4·(d/L)²]

    with b1 depending on the soil type:
        - Purely cohesive (φ=0):  b1 ≈ 0.69
        - Mixed c-φ:              b1 ≈ 0.50  (default)
        - Cohesionless (c=0):     b1 ≈ 0.31
    """
    if not slices.slices:
        return 1.0
    first, last = slices.slices[0], slices.slices[-1]
    # Chord joining the two slip-surface endpoints
    x0, y0 = first.base_x_left, first.base_y_left
    x1, y1 = last.base_x_right, last.base_y_right
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 1e-6:
        return 1.0
    # v0.1.19 — d is the maximum PERPENDICULAR distance from that chord
    # to the slip surface (Janbu's definition), NOT the max soil height
    # above the base. Using the soil height grossly overestimated d/L
    # and the correction factor (gave +2.9 % vs Slide). The base points
    # of every slice are sampled against the chord line.
    dx, dy = x1 - x0, y1 - y0
    d = 0.0
    pts = [(first.base_x_left, first.base_y_left)]
    for s in slices.slices:
        pts.append((s.base_x_right, s.base_y_right))
    for px, py in pts:
        # perpendicular distance from (px,py) to the chord
        dist = abs(dy * (px - x0) - dx * (py - y0)) / L
        if dist > d:
            d = dist
    r = d / L
    # b1 depends on soil type; pick from the dominant base material's
    # strength (cohesive / mixed / frictional).
    b1 = 0.50  # mixed c-φ soil (default)
    return 1.0 + b1 * (r - 1.4 * r * r)

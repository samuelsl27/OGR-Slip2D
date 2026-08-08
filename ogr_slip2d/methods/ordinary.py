# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Ordinary (Fellenius / Swedish) Method of Slices.

Simplest LEM method: ignores inter-slice forces entirely. Satisfies
moment equilibrium about the centre of a circular surface only.

Formulation (circular surface):

    FS = Σ [c'·l + (W cos α − u·l) · tan φ'] / Σ (W sin α)

where
    l   = base length of slice
    α   = base inclination (positive if rising to the right)
    W   = slice weight
    u   = pore pressure at slice base midpoint
    c'  = effective cohesion at the base
    φ'  = effective friction angle at the base

Non-iterative → always returns converged=True.

Reference: Fellenius (1927).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from ogr_core.project import Project

from ..external_forces import slice_forces
from ..slicer import Slices
from ..surface import SlipCircle, SurfaceProtocol
from .base import LEMMethod, LEMResult, register_method


@register_method
class OrdinaryFellenius(LEMMethod):
    METHOD_ID = "ordinary_fellenius"
    DISPLAY_NAME = "Ordinary / Fellenius"
    SATISFIES_FORCE = False
    SATISFIES_MOMENT = True

    def compute_fos(
        self,
        project: Project,
        surface: SurfaceProtocol,
        slices: Slices,
    ) -> LEMResult:
        numerator = 0.0
        denominator = 0.0

        normals: list[float] = []
        shears: list[float] = []
        strengths: list[float] = []

        # Optional seismic load
        kh = project.seismic.kh if project.seismic.enabled else 0.0
        kv = project.seismic.kv if project.seismic.enabled else 0.0

        # Determine sliding direction from the un-seismic driving moment
        driving_raw = sum(
            s.weight * (1.0 - kv) * math.sin(s.base_angle) for s in slices
        )
        slide_sign = 1.0 if driving_raw >= 0 else -1.0

        # v0.1.61 — the horizontal water forces act on the TOP of the
        # slice, not on its base, so they enter the driving side through
        # their MOMENT about the centre of rotation — the same normalised
        # form Bishop uses — and not as a tangential component at the base.
        # Ordinary/Fellenius is a moment method, so R cancels here too.
        circle_R = surface.radius if isinstance(surface, SlipCircle) else None
        circle_yc = (surface.centre_y
                     if isinstance(surface, SlipCircle) else None)

        for s in slices:
            f = slice_forces(s, kh, kv)
            W = f.w_total
            H = s.weight * kh * slide_sign
            # A horizontal force resolved on the base: the inward normal
            # is (−sin α, cos α), so it adds ``+F_h·sin α`` to the base
            # reaction.
            Hw = f.h_water
            # Base-normal effective stress
            N = (W * math.cos(s.base_angle)
                 - H * math.sin(s.base_angle)
                 + Hw * math.sin(s.base_angle))
            N_eff = N - s.pore_pressure * s.base_length
            sigma_n_eff = max(0.0, N_eff) / max(s.base_length, 1e-9)

            tau = self._shear_strength(s.material, sigma_n_eff)
            strength = tau * s.base_length

            driving = (
                slide_sign * W * math.sin(s.base_angle)
                + H * math.cos(s.base_angle)
            )
            if circle_R is not None:
                driving += (
                    -slide_sign * f.water_moment_about(circle_yc) / circle_R
                )

            numerator += strength
            denominator += driving

            normals.append(N)
            shears.append(driving)
            strengths.append(strength)

        if abs(denominator) < 1e-9:
            return LEMResult(
                fos=math.inf,
                converged=False,
                iterations=0,
                method_id=self.METHOD_ID,
                surface=surface,
                slices=slices,
                error_message="Zero driving moment — surface does not slide",
            )

        fos = numerator / denominator
        return LEMResult(
            fos=fos,
            converged=True,
            iterations=1,
            method_id=self.METHOD_ID,
            surface=surface,
            slices=slices,
            base_normal=normals,
            base_shear_force=shears,
            base_shear_strength=strengths,
        )

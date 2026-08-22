# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Lowe-Karafiath Method of Slices.

Reference: Lowe, J. & Karafiath, L. (1960). "Stability of earth dams
upon drawdown." Proc. 1st Pan-American Conf. on Soil Mechanics and
Foundation Engineering, Mexico City, Vol. 2, 537-552.  See also the
review by Abramson, Lee, Sharma & Boyce (2001), "Slope Stability and
Stabilization Methods", 2nd ed., Wiley.

The Lowe-Karafiath procedure is a **force-equilibrium** method (it does
NOT satisfy moment equilibrium). Its single defining assumption is the
inclination of the inter-slice resultant at every internal boundary:

        θ_i = ½ · ( β_i + α_i )

where β_i is the inclination of the *ground surface* over the slice and
α_i is the inclination of the *slip surface* (base) of the slice. The
inter-slice force ratio is therefore prescribed directly,

        X_i / E_i = tan θ_i

with no scalar λ to iterate on. Because only force equilibrium is
enforced, the Factor of Safety follows from a single fixed-point
iteration of the horizontal force-balance equation.

v0.1.98 — everything except that one line now lives in
:class:`ogr_slip2d.methods.modified_swedish.PrescribedInclinationMethod`,
which Corps of Engineers #1 and #2 share. The recursion did not change:
it was already, term by term, the numerical solution published as
EM 1110-2-1902 equation C-19, and this move is what made that checkable
against the manual's own worked example.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from ..slicer import Slices
from .base import register_method
from .modified_swedish import PrescribedInclinationMethod


@register_method
class LoweKarafiath(PrescribedInclinationMethod):
    METHOD_ID = "lowe_karafiath"
    DISPLAY_NAME = "Lowe-Karafiath"
    SATISFIES_FORCE = True
    SATISFIES_MOMENT = False

    # ------------------------------------------------------------------
    def _theta_angles(self, slices: Slices) -> list[float]:
        return [self._interslice_tan_theta_angle(s, 1.0) for s in slices]

    # ------------------------------------------------------------------
    @staticmethod
    def _interslice_tan_theta_angle(s, slide_sign: float) -> float:
        """Lowe-Karafiath inter-slice inclination θ (radians) for slice
        ``s``: the average of the ground-surface and base inclinations,
        both in the normalised (slide-sign flipped) frame."""
        alpha = slide_sign * s.base_angle
        b = max(s.width, 1e-9)
        beta = slide_sign * math.atan2(s.top_y_right - s.top_y_left, b)
        return 0.5 * (alpha + beta)

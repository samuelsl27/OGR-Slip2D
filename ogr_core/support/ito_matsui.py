# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Lateral force on a row of stabilizing piles — Ito and Matsui (1975).

Reference
---------
Ito, T. and Matsui, T. (1975), "Methods to estimate lateral force acting on
stabilizing piles", *Soils and Foundations* **15**(4), 43-59. Theory of
plastic deformation, Eqs. (13), (14) and (23).

The same equation is printed a second time, and independently, as Eq. (10)
of Cai, F. and Ugai, K. (2000), "Numerical analysis of the stability of a
slope reinforced with piles", *Soils and Foundations* **40**(1), 73-84,
grouped around ``A = D1 (D1/D2)^(sqrt(Nphi) tan phi + Nphi - 1)``. Two
independent printings of the same expression is what makes a transcription
check possible at all, and both were read before writing this.

What it computes
----------------
Soil squeezing between two piles of a row goes plastic in the wedge just
around them, and the difference between the lateral thrust on the plane
behind the piles and the one on the plane between them is the force the row
takes off the sliding mass. ``p`` is that force **on one pile, per unit
thickness of soil layer** — so kN/m per metre of depth — and it grows with
depth because the active pressure feeding it does.

Geometry, from Fig. 1 and Fig. 2 of the paper:

* ``d1`` is the CENTRE-TO-CENTRE spacing of the piles in the row;
* ``d2`` is the OPENING between two neighbouring piles;
* hence ``d2 = d1 - diameter``. Piles that touch give ``d2 = 0``, where the
  ``(d1/d2)`` power diverges: the theory has nothing to say about a
  continuous wall and this module refuses rather than returning an infinity.

The three cases
---------------
``lateral_force_c_phi``
    Eq. (13), the general c-phi soil.
``lateral_force_cohesionless``
    Eq. (14), c = 0. It is the third term of Eq. (13) alone, which makes it
    a check on the transcription rather than a separate law.
``lateral_force_cohesive``
    Eq. (23), phi = 0.

Eq. (23) is NOT an independent case: it is the limit of Eq. (13) as phi goes
to zero. Both ``1/(Nphi tan phi)`` and ``1/(sqrt(Nphi) tan phi + Nphi - 1)``
diverge there, and the two ``c*d1/phi`` terms they generate cancel exactly —
which is why the limit is finite. In floating point that cancellation is
catastrophic, so :func:`lateral_force` switches to Eq. (23) below
``PHI_SWITCH_RAD``. The threshold is not a guess: it is where the round-off
of Eq. (13) and the O(phi) truncation of Eq. (23) cross, measured in
``tests/test_ito_matsui_pile_v1123.py``.

Eq. (23) was also re-derived from Eqs. (16), (19), (21) and (22) of the
paper and comes out identical to the printed one, which is the second path
rule 1 asks for and rules out a misread of the scan.

A published criticism, not applied
----------------------------------
Zhang, S. and others (2017), "Error in Ito and Matsui's Limit-Equilibrium
Solution of Lateral Force on a Row of Stabilizing Piles", *J. Geotech.
Geoenviron. Eng.* **143**(9), argue that this solution underestimates the
pile force — increasingly so with the friction angle — and that at close
spacings it exceeds the passive earth pressure, which cannot happen. It is
deliberately NOT applied: the only published factors of safety this
implementation can be validated against were computed with the original
equations, and replacing them would leave the validation with nothing to
check.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

__all__ = [
    "PHI_SWITCH_RAD",
    "clear_spacing",
    "n_phi",
    "lateral_force",
    "lateral_force_c_phi",
    "lateral_force_cohesionless",
    "lateral_force_cohesive",
]


#: Below this friction angle Eq. (13) is evaluated as Eq. (23). It is a
#: NUMERICAL switch, not a modelling one, and the value is measured rather
#: than chosen: sweeping phi in decades, the O(phi) truncation of Eq. (23)
#: falls as 6.3e-4, 6.3e-5, 6.3e-6, 6.3e-7 for phi = 1e-4 .. 1e-7 rad and
#: then STOPS falling -- 6.4e-8 at 1e-8, 9.2e-8 at 1e-9, 7.4e-7 at 1e-10,
#: 1.9e-5 at 1e-11 -- because below that the round-off of Eq. (13) is what
#: is being measured. The two error sources cross at 1e-8, where the
#: branches agree to 6.4e-8 relative. That is as continuous as the switch
#: can be made, and the test asserts that number rather than exactness.
PHI_SWITCH_RAD = 1.0e-8


def clear_spacing(d1: float, diameter: float) -> float:
    """``D2``, the opening between piles, from spacing and diameter.

    One line, but it is the definition that decides everything: ``D2`` is
    the GAP, not the spacing, and reading Fig. 1 of the paper the other way
    round would still produce plausible numbers.
    """
    return d1 - diameter


def n_phi(phi_rad: float) -> float:
    """``N_phi = tan^2(pi/4 + phi/2)``, the flow value of Eq. (2)."""
    return math.tan(0.25 * math.pi + 0.5 * phi_rad) ** 2


def _check(d1: float, d2: float) -> None:
    if d1 <= 0.0:
        raise ValueError("pile spacing D1 must be positive")
    if d2 <= 0.0:
        raise ValueError(
            "the opening D2 between piles must be positive: piles that "
            "touch form a continuous wall, and the (D1/D2) power of Ito "
            "and Matsui (1975) diverges there")
    if d2 > d1:
        raise ValueError("the opening D2 cannot exceed the spacing D1")


def lateral_force_c_phi(
    c: float, phi_rad: float, sigma_v: float, d1: float, d2: float,
) -> float:
    """Eq. (13) — lateral force per unit thickness on ONE pile, kN/m per m.

    ``sigma_v`` stands for the ``gamma z`` of the paper: the vertical stress
    at that depth. Ito and Matsui write it as the weight of the column
    because there is no water anywhere in their paper; which vertical stress
    this program feeds it, and why, is decided in
    ``PileMicropile.interface_tau``.

    Raises ``ValueError`` if the piles touch or overlap — the theory
    diverges there, and an infinity would travel silently into a factor of
    safety.
    """
    _check(d1, d2)
    nq = n_phi(phi_rad)
    t = math.tan(phi_rad)
    sq = math.sqrt(nq)
    # The exponent of the (D1/D2) power and the denominator of the second
    # bracket are THE SAME quantity in the paper. Writing it once is the
    # only way to be sure they stay the same.
    k = sq * t + nq - 1.0
    a = d1 * (d1 / d2) ** k
    ex = math.exp((d1 - d2) / d2 * nq * t
                  * math.tan(0.125 * math.pi + 0.25 * phi_rad))
    g = (2.0 * t + 2.0 * sq + 1.0 / sq) / k

    bracket = (ex - 2.0 * sq * t - 1.0) / (nq * t) + g
    term1 = c * a * bracket
    term2 = -c * (d1 * g - 2.0 * d2 / sq)
    term3 = sigma_v / nq * (a * ex - d2)
    return term1 + term2 + term3


def lateral_force_cohesionless(
    phi_rad: float, sigma_v: float, d1: float, d2: float,
) -> float:
    """Eq. (14) — the c = 0 soil.

    It is the third term of Eq. (13) on its own. Kept as a separate
    function because the paper prints it separately, and because agreeing
    with Eq. (13) at c = 0 checks the transcription of both.
    """
    _check(d1, d2)
    nq = n_phi(phi_rad)
    t = math.tan(phi_rad)
    k = math.sqrt(nq) * t + nq - 1.0
    a = d1 * (d1 / d2) ** k
    ex = math.exp((d1 - d2) / d2 * nq * t
                  * math.tan(0.125 * math.pi + 0.25 * phi_rad))
    return sigma_v / nq * (a * ex - d2)


def lateral_force_cohesive(
    c: float, sigma_v: float, d1: float, d2: float,
) -> float:
    """Eq. (23) — the phi = 0 soil.

    ``log`` in the paper is the natural logarithm: Eq. (15) is
    ``dD/D = d(sigma_x)/(3c)``, whose integral Eq. (16) is
    ``sigma_x = 3c log D + C3``. Reading it as a base-ten logarithm would
    scale the cohesion term by 2.303 and still look reasonable.
    """
    _check(d1, d2)
    return (c * (d1 * (3.0 * math.log(d1 / d2)
                       + (d1 - d2) / d2 * math.tan(0.125 * math.pi))
                 - 2.0 * (d1 - d2))
            + sigma_v * (d1 - d2))


def lateral_force(
    c: float, phi_rad: float, sigma_v: float, d1: float, d2: float,
) -> float:
    """The lateral force per unit thickness, whichever case applies.

    Eq. (13) everywhere except within ``PHI_SWITCH_RAD`` of zero friction,
    where it is numerically singular and Eq. (23) is its exact limit.
    """
    if abs(phi_rad) < PHI_SWITCH_RAD:
        return lateral_force_cohesive(c, sigma_v, d1, d2)
    return lateral_force_c_phi(c, phi_rad, sigma_v, d1, d2)

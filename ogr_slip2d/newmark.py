# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Newmark permanent displacement of a rigid sliding block.

A pseudo-static factor of safety below 1 does not say that a slope falls
down; it says that for some instants of the shaking the available
resistance is exceeded. What decides whether an embankment still works
afterwards is **how far it moved**, and that is the number this module
produces and a pseudo-static analysis cannot.

The model is Newmark's: the sliding mass is a rigid-plastic block that
does not deform, feels nothing below its yield (critical) acceleration
and slides along a basal shear surface above it. The displacement is the
double integral, over the parts of the record that exceed the critical
acceleration, of the excess.

Formulation
-----------
The integration scheme is the one of Wilson and Keefer (1983), as Jibson
(1993) publishes it step by step, with the modification Jibson describes
that **prohibits upslope displacement** (Newmark's fourth assumption:
the upslope resistance is taken to be infinitely large). Three details of
that scheme are not free choices and are reproduced deliberately:

* while the block is sliding the resistance is taken **in the direction
  of sliding**, so the block decelerates once the ground acceleration
  drops below the critical value and keeps moving on its own inertia;
* sliding **stops** when the relative velocity ceases to be positive, and
  both the velocity and the relative acceleration are then set to zero;
* both integrations are **trapezoidal** — acceleration to velocity and
  velocity to displacement. A different quadrature gives a different
  answer at the same time step, so the quadrature is part of the
  definition, not an implementation detail.

The arithmetic is carried out in **cm/s² and cm**, which is what the
published program uses, so that its rest threshold (a relative velocity
below 1e-4 cm/s counts as stopped) means here what it means there. The
value returned is in **metres**, the internal length unit of this
program; the interface converts it for display like any other small
length.

``g = 980.665 cm/s²`` exactly, because the published program converts a
critical acceleration given in g with that factor.

Both directions
---------------
The reference this project follows offers a rigid-block analysis that
allows only downslope movement or allows both. Wilson and Keefer allow
both by using the thrust angle to give the upslope direction its own,
larger, critical acceleration; that asymmetry needs a datum this program
does not have. What :func:`rigid_block_displacement` does with
``allow_upslope=True`` is therefore the **symmetric** two-sided block —
the same critical acceleration in both directions — which is well defined,
is what makes the ``a_c = 0`` identity exact, and is said out loud here
rather than left to be assumed.

References
----------
Newmark, N.M. (1965). Effects of earthquakes on dams and embankments.
    Géotechnique 15(2), 139-160.
Wilson, R.C. and Keefer, D.K. (1983). Dynamic analysis of a slope failure
    from the 6 August 1979 Coyote Lake, California, earthquake. Bulletin
    of the Seismological Society of America 73(3), 863-877.
Jibson, R.W. (1993). Predicting earthquake-induced landslide
    displacements using Newmark sliding block analysis. Transportation
    Research Record 1411, 9-17.
Jibson, R.W., Rathje, E.M., Jibson, M.W. and Lee, Y.W. (2013). SLAMMER —
    Seismic LAndslide Movement Modeled using Earthquake Records. U.S.
    Geological Survey Techniques and Methods, book 12, chapter B1.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from enum import Enum
from typing import Optional, Sequence

from ogr_core.loads.seismic_record import STANDARD_GRAVITY_CM_S2

__all__ = [
    "Polarity",
    "NewmarkResult",
    "rigid_block_displacement",
    "displacement_for_record",
    "ground_displacement",
]

# The published program treats a relative velocity below this, in cm/s,
# as "the block is at rest". It is not a tolerance this module chose: it
# is part of the algorithm being reproduced.
_AT_REST_CM_S = 1e-4


class Polarity(Enum):
    """Which sense of the record drives the slope.

    A record is a signed ground acceleration; which sign pushes the mass
    towards failure depends on how the instrument was oriented, and that
    is not knowable from the numbers. The reference offers five ways of
    resolving it. Four are implemented, and the fifth is not:
    *All Accelerations* is offered without a definition, and it overlaps
    with the choice of allowing upslope movement, so implementing it
    would mean guessing what it does.
    """

    DIRECT = "direct"
    """The record as recorded."""

    INVERSE = "inverse"
    """The record negated."""

    AVERAGE = "average"
    """Mean of the two, which is what the reference calls the average of
    the two polarities."""

    MAXIMUM = "maximum"
    """The larger of the two. The reference default, and this one too."""


class NewmarkResult:
    """What one displacement calculation produced."""

    __slots__ = ("displacement", "direct", "inverse", "polarity", "note")

    def __init__(self, displacement: float, direct: float, inverse: float,
                 polarity: Polarity, note: str = "") -> None:
        #: Permanent displacement in METRES, under the chosen polarity.
        self.displacement = displacement
        #: The two polarities separately, also in metres. Kept because a
        #: slope that moves ten times more one way than the other is
        #: telling the user something the combined number hides.
        self.direct = direct
        self.inverse = inverse
        self.polarity = polarity
        self.note = note

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (f"NewmarkResult({self.displacement:.6g} m, "
                f"direct={self.direct:.6g}, inverse={self.inverse:.6g})")


# ----------------------------------------------------------------------
def _slide_downslope_only(accel_cm_s2: Sequence[float], ac_cm_s2: float,
                          dt: float) -> float:
    """The published scheme, downslope movement only.

    Written to follow the listing of Jibson (1993, Table 2) branch for
    branch rather than in its algebraically simplified form: the three
    cases below collapse to two once the clamp on the velocity is taken
    into account, and writing the short version would make the
    correspondence with the published algorithm impossible to check.
    """
    t = ac_cm_s2
    u_prev = 0.0     # displacement at the previous sample
    v_prev = 0.0     # relative velocity at the previous sample
    y_prev = 0.0     # relative acceleration at the previous sample
    for a in accel_cm_s2:
        if v_prev < _AT_REST_CM_S:
            # At rest. Motion begins only if the ground acceleration
            # exceeds the critical value; below it the block is carried
            # along and its relative acceleration is zero.
            if abs(a) > t:
                y = a - (t if a > 0.0 else -t)
            else:
                # The listing writes this branch as N = A/T, whose only
                # purpose is to make Y = A - N*T vanish. Computing it
                # that way does NOT vanish in floating point — (a/t)*t
                # is not a — and the residue accumulates: a slope whose
                # critical acceleration equals the peak of the record
                # came out with 1.7e-16 m of displacement instead of the
                # exact zero the algorithm means. Written as the zero it
                # is.
                y = 0.0
        else:
            # Sliding: the resistance acts in the direction of sliding,
            # which is what lets the block decelerate and stop.
            y = a - t
        v = v_prev + 0.5 * dt * (y + y_prev)
        if v <= 0.0:
            # The relative velocity has died: the block re-attaches.
            v = 0.0
            y = 0.0
        u = u_prev + 0.5 * dt * (v + v_prev)
        u_prev, v_prev, y_prev = u, v, y
    return u_prev


def _slide_both_ways(accel_cm_s2: Sequence[float], ac_cm_s2: float,
                     dt: float) -> float:
    """The symmetric two-sided block: the same critical acceleration in
    both directions.

    The block starts to slide whenever the ground acceleration exceeds
    the critical value in either sense, the resistance opposes the
    relative velocity, and it re-attaches only when the relative velocity
    dies **and** the ground is no longer driving it. The result is the
    NET relative displacement, which can be negative.

    With ``ac = 0`` the block is never held, so it never re-attaches and
    the relative displacement is exactly the ground displacement. That
    is the identity this branch exists to satisfy, and the reason the
    re-attachment test asks for a positive critical acceleration.
    """
    t = ac_cm_s2
    u_prev = 0.0
    v_prev = 0.0
    y_prev = 0.0
    sliding = False
    sense = 1.0
    for a in accel_cm_s2:
        if not sliding:
            if abs(a) > t:
                sliding = True
                sense = 1.0 if a > 0.0 else -1.0
                y = a - sense * t
            else:
                y = 0.0
        else:
            y = a - sense * t
        v = v_prev + 0.5 * dt * (y + y_prev)
        if sliding and v * sense <= 0.0:
            if abs(a) > t:
                # It stopped going one way and the ground is already
                # driving it the other: it never rests.
                sense = 1.0 if a > 0.0 else -1.0
                y = a - sense * t
                v = v_prev + 0.5 * dt * (y + y_prev)
            elif t > 0.0:
                v = 0.0
                y = 0.0
                sliding = False
        u = u_prev + 0.5 * dt * (v + v_prev)
        u_prev, v_prev, y_prev = u, v, y
    return u_prev


# ----------------------------------------------------------------------
def rigid_block_displacement(accelerations_g: Sequence[float], dt: float,
                             ac_g: float, *,
                             allow_upslope: bool = False) -> float:
    """Permanent displacement of a rigid block, in METRES.

    ``accelerations_g`` is the horizontal ground acceleration in g,
    sampled every ``dt`` seconds; ``ac_g`` is the critical (yield)
    acceleration in g.

    A critical acceleration at or above the peak of the record returns
    **exactly** zero, because no sample ever exceeds it.

    Reference: Wilson and Keefer (1983) as published by Jibson (1993),
    following Newmark (1965).
    """
    if dt <= 0.0 or len(accelerations_g) < 2:
        return 0.0
    if not math.isfinite(ac_g):
        return 0.0
    g = STANDARD_GRAVITY_CM_S2
    accel = [a * g for a in accelerations_g]
    ac = max(0.0, ac_g) * g
    if allow_upslope:
        u_cm = _slide_both_ways(accel, ac, dt)
    else:
        u_cm = _slide_downslope_only(accel, ac, dt)
    return u_cm / 100.0


def ground_displacement(accelerations_g: Sequence[float],
                        dt: float) -> float:
    """Displacement of the GROUND itself, in metres.

    Twice-trapezoidal, the same quadrature the block uses, so that the
    two agree exactly when the block has no resistance to hold it. That
    agreement is an identity and not an approximation, which is what
    makes it worth having as a separate function.
    """
    if dt <= 0.0 or len(accelerations_g) < 2:
        return 0.0
    g = STANDARD_GRAVITY_CM_S2
    u = 0.0
    v = 0.0
    a_prev = 0.0
    v_prev = 0.0
    for a_g in accelerations_g:
        a = a_g * g
        v = v_prev + 0.5 * dt * (a + a_prev)
        u = u + 0.5 * dt * (v + v_prev)
        a_prev, v_prev = a, v
    return u / 100.0


# ----------------------------------------------------------------------
def displacement_for_record(record, ac_g: float, *,
                            polarity: Polarity = Polarity.MAXIMUM,
                            allow_upslope: bool = False,
                            scale: float = 1.0) -> Optional[NewmarkResult]:
    """Displacement of one surface under one :class:`SeismicRecord`.

    Returns ``None`` when the record cannot be integrated — too few
    samples, a non-positive interval, a non-finite value — rather than a
    zero, because zero is a legitimate answer (a strong enough slope) and
    must not be confused with "there was nothing to integrate".

    ``scale`` multiplies the record, which is the reference option that
    lets one record stand in for a stronger or weaker event. It scales
    the accelerations and NOT the critical acceleration, so it is not the
    same as the exact similarity the tests check.
    """
    if record is None or not record.is_usable():
        return None
    if not math.isfinite(ac_g):
        return None
    accel = record.accelerations
    if scale != 1.0:
        accel = [a * scale for a in accel]
    dt = record.dt

    direct = rigid_block_displacement(accel, dt, ac_g,
                                      allow_upslope=allow_upslope)
    inverse = rigid_block_displacement([-a for a in accel], dt, ac_g,
                                       allow_upslope=allow_upslope)
    if polarity is Polarity.DIRECT:
        value = direct
    elif polarity is Polarity.INVERSE:
        value = inverse
    elif polarity is Polarity.AVERAGE:
        value = 0.5 * (direct + inverse)
    else:
        value = max(direct, inverse)
    return NewmarkResult(value, direct, inverse, polarity)

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
From which end a support is read: the one rule the engine and the interface
both ask.

Most support types measure along the support from its HEAD, the end at the
slope face: that is where the plate is, and ``force_at`` is written that way.
A few define their profile from the CREST instead, and say so with
``MEASURED_FROM_TOP``: a retaining wall's earth-pressure diagram grows from
the top of the wall down, and an Ito–Matsui pile integrates the soil pressure
"from the top of the pile to the depth of the slip circle at the pile
position" (Cai and Ugai 2000). For those, which end is the crest is a
question of geometry, not of drawing order — and the answer has to be the
same wherever it is asked.

v0.1.254 (D97). It was asked in three places and answered in three ways:

* the engine (``compute_support_effects``) took the higher end, but with an
  EXACT comparison, so a support 1e-15 off level skipped the refusal and was
  measured from whichever end rounding made higher; and it handed a pile's
  ``force_at`` a distance from the crest while the profile it integrated ran
  from the head — a pile drawn bottom to top integrated from its TIP: on the
  case of Cai and Ugai (2000), 810.45 kN/m against 152.59 kN/m drawn top to
  bottom, and Bishop 3.034 against 1.507, on the unsafe side;
* the canvas tooltip and the support force diagram measured from the head
  whatever the type, so their "force at the midpoint" and "at the slip
  surface" were not the engine's for a support drawn bottom to top, and they
  published a number for a level support the analysis refuses;
* the EFP wall note asked ``head.y == tail.y`` again, exactly.

:func:`crest_reading` is now the only place that decides, and all of them
ask it.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

__all__ = ["CrestReading", "crest_reading"]


@dataclass(frozen=True)
class CrestReading:
    """How a support type reads one support.

    ``from_tail`` — distances along the support run from the TAIL, because
    the type is measured from its crest and the tail is the higher end.
    ``bond`` is the profile oriented the same way (flipped when
    ``from_tail``), ``crest`` and ``other`` the two ends in reading order.
    """

    from_tail: bool
    bond: object
    crest: object
    other: object

    def along(self, distance_from_head: float, length: float) -> float:
        """A distance from the head, as the type reads it."""
        if self.from_tail:
            return length - distance_from_head
        return distance_from_head


def crest_reading(support, stype, bond=None) -> Optional[CrestReading]:
    """From which end ``stype`` reads ``support``, or None if it cannot.

    A type that is not measured from its crest reads from the head, always,
    with ``bond`` as built (head to tail). One that is measured from its
    crest reads from the higher end — the tail when the tail is higher, with
    the profile flipped (:meth:`BondProfile.flipped`) — and from NEITHER when
    the support is level (:meth:`SupportInstance.is_level`): None, which the
    engine reports as a support with no crest instead of guessing.
    """
    if not getattr(stype, "MEASURED_FROM_TOP", False):
        return CrestReading(False, bond, support.head, support.tail)
    if support.is_level():
        return None
    if support.tail.y > support.head.y:
        return CrestReading(True, None if bond is None else bond.flipped(),
                            support.tail, support.head)
    return CrestReading(False, bond, support.head, support.tail)

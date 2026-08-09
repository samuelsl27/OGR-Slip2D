# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The failure direction, and the one place that says what it means.

**Convention** — ``RIGHT_TO_LEFT`` means the sliding mass moves towards
**decreasing x**: the crest is on the right, the toe on the left. It is
the default, and it is the convention the rest of the engine was already
written against:

* :mod:`ogr_slip2d.support_integration` gives a horizontal support force
  an angle of ``0`` (pointing +x) for a right-to-left failure, because a
  support RESISTS the movement;
* the tension crack forms at the crest, so for a right-to-left failure it
  truncates the slice at the **right-hand** end of the crack zone.

**What this setting does NOT do.** It does not orient the calculation.
Every method derives the sense of sliding from the geometry of each
individual surface (``slide_sign``, from the sign of ``Σ W·sin α``), and
that derivation is both more robust and per-surface, which a single
project-wide switch cannot be. Path Search likewise finds the toe as the
lower end of the slope face rather than from this setting — the reference
is explicit that its surfaces always start at the toe *regardless of the
failure direction*.

What is left, and what this module exists for, is the handful of places
where the geometry is genuinely **ambiguous** and something has to break
the tie. Those places are few on purpose: a setting wired into a decision
the geometry already answers correctly would be a setting that makes
results worse.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations


def is_left_to_right(project) -> bool:
    """True if the mass is declared to slide towards increasing x.

    Defensive by design: a project built in a test without full settings
    falls back to the default (right to left), the same fallback
    ``support_integration`` has used since v0.1.64.
    """
    try:
        from ogr_core.project.units import FailureDirection
        fd = project.settings.units.failure_direction
        return fd == FailureDirection.LEFT_TO_RIGHT
    except Exception:  # noqa: BLE001
        return False


def crest_is_on_the_right(project) -> bool:
    """True if the up-slope (crest) side lies at greater x.

    The crest is behind the sliding mass, so it is on the side the mass
    moves AWAY from: a right-to-left failure has its crest on the right.
    """
    return not is_left_to_right(project)

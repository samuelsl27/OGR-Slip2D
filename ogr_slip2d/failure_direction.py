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
* a tension crack forms at the crest, so a right-to-left failure is
  truncated at the **right-hand** end — but see
  :func:`crest_end_is_on_the_right`: since v0.1.109 that end is read off
  the surface's own geometry, and the declaration is only the tiebreak.

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


def crest_end_is_on_the_right(project, ground, x_left: float,
                              x_right: float) -> bool:
    """Which END of one slip surface is its up-slope (crest) end.

    **Geometry decides**: the crest of a surface is the end where the
    GROUND is higher. The declared failure direction only breaks a tie,
    which is the role this module reserves for it.

    Why not the declaration alone, as :func:`crest_is_on_the_right` gives
    it. Three reasons, and the third is the one that changed:

    * the reference's own help says a failure direction does not affect
      modelling options, and states the tension-crack rule in terms of
      "the crest of a slip surface", which is a property of the surface,
      not of the project;
    * :meth:`ogr_slip2d.surface.SlipCircle.apply_reverse_curvature` has
      tested both ends on geometry since v0.1.82, for the same reason:
      whichever end daylights above the centre is the one that reverses;
    * until v0.1.108 this choice only picked which slice received the
      water thrust in a tension crack — worth a percent. It now picks
      which HALF OF THE ARC survives truncation, worth twenty, and always
      on the unsafe side when wrong. D03d found nineteen benchmark models
      whose declared direction contradicted their own terrain.

    A genuine tie (two ends at the same ground elevation, e.g. a
    symmetric trench) falls back to the declaration.
    """
    from .surface import ground_y_at

    y_l = ground_y_at(ground, x_left)
    y_r = ground_y_at(ground, x_right)
    if y_l is None or y_r is None:
        return crest_is_on_the_right(project)
    # Relative to the surface's own horizontal extent, so the same slope
    # answers the same question in millimetres and in metres.
    tol = 1e-9 * max(abs(x_right - x_left), 1.0)
    if abs(y_r - y_l) <= tol:
        return crest_is_on_the_right(project)
    return y_r > y_l

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What an Ito-Matsui pile row is being asked to do outside its theory.

Ito and Matsui (1975) derive the lateral force on a row of RIGID VERTICAL
piles in a DRY soil layer squeezing between them. Every one of those three
words is a place where a real model can step outside the derivation without
anything failing — the equation keeps returning a number. These notes are
where the program says so, once per analysis.

None of them is a refusal. A refusal would be worse: the analysis is still
the best available answer, and hiding it would leave the user with a
plausible number and no idea what it rests on.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from .support_notes import supports_of

#: How far off vertical a pile may lean before it is worth saying. Two
#: degrees is drawing noise; beyond that the integral along the shaft and
#: the integral over depth are measurably different quantities.
_TILT_TOLERANCE_DEG = 2.0

_TYPE_ID = "pile_micropile"


def _piles(project):
    """``(instance, type)`` pairs for the Ito-Matsui piles in the model."""
    from .support_notes import resolved_types

    stype = resolved_types(project).get(_TYPE_ID)
    if stype is None or not getattr(stype, "NEEDS_BOND_PROFILE", False):
        return []
    return [(s, stype) for s in supports_of(project, _TYPE_ID)]


def ito_matsui_notes(project, method_ids=()) -> list[str]:
    """Notes about the Ito-Matsui piles in ``project``."""
    piles = _piles(project)
    if not piles:
        return []

    notes: list[str] = []
    stype = piles[0][1]

    # --- the piles touch -------------------------------------------------
    d1 = float(getattr(stype, "out_of_plane_spacing", 0.0) or 0.0)
    d = float(getattr(stype, "pile_diameter", 0.0) or 0.0)
    if d1 <= 0.0 or d1 - d <= 0.0:
        notes.append(
            "The pile diameter (%.3g) is not smaller than the out-of-plane "
            "spacing (%.3g), so there is no opening between piles. Ito and "
            "Matsui (1975) describe soil squeezing THROUGH that opening and "
            "their equation diverges when it closes, so the row applies no "
            "force at all. A continuous barrier is a wall, not a pile row."
            % (d, d1))
        return notes

    # --- leaning off vertical -------------------------------------------
    leaning = []
    for sup, _ in piles:
        dx = abs(sup.tail.x - sup.head.x)
        dy = abs(sup.tail.y - sup.head.y)
        tilt = math.degrees(math.atan2(dx, dy)) if (dx or dy) else 0.0
        if tilt > _TILT_TOLERANCE_DEG:
            leaning.append(tilt)
    if leaning:
        notes.append(
            "%d pile%s more than %.3g° off vertical (up to %.1f°). Ito and "
            "Matsui (1975) derive the pressure for a vertical row, so the "
            "force is integrated ALONG THE SHAFT rather than over depth. "
            "The theory does not say which is right, and projecting one "
            "onto the other here would be this program deciding."
            % (len(leaning), " is" if len(leaning) == 1 else "s are",
               _TILT_TOLERANCE_DEG, max(leaning)))

    # --- water on the shaft ----------------------------------------------
    if _has_pore_pressure(project, piles):
        notes.append(
            "There is pore pressure along an Ito-Matsui pile. The published "
            "equation is written on the total overburden because there is "
            "no water anywhere in the paper it comes from; with effective "
            "strength parameters this program feeds it the EFFECTIVE "
            "vertical stress, which is the consistent reading and the "
            "conservative one. The theory itself is silent.")

    # --- the pressure goes negative near the surface ---------------------
    if _has_negative_pressure(project, piles):
        notes.append(
            "The Ito-Matsui pressure comes out negative over part of the "
            "pile, near the surface, where the cohesion terms outweigh the "
            "overburden: the theory is saying no plastic pressure develops "
            "there. It is integrated as published, so that stretch reduces "
            "the total instead of being quietly set to zero.")

    return notes


def _has_pore_pressure(project, piles) -> bool:
    """True if any sample along any of the piles sits below water."""
    from ogr_core.support.bond import sigma_v_effective_at

    for sup, _ in piles:
        for f in (0.25, 0.5, 0.75, 1.0):
            x = sup.head.x + f * (sup.tail.x - sup.head.x)
            y = sup.head.y + f * (sup.tail.y - sup.head.y)
            try:
                _sv, u, _depth = sigma_v_effective_at(project, x, y)
            except Exception:  # noqa: BLE001 - a note must not kill a run
                return False
            if u > 1e-9:
                return True
    return False


def _has_negative_pressure(project, piles) -> bool:
    """True if the sampled profile of any pile dips below zero.

    Reads the profile the analysis is going to use, not a second opinion
    about it: the cache is the same one ``compute_support_effects`` asks
    for, so this cannot report on a pressure the run does not see.
    """
    from .support_integration import _bond_profiles

    try:
        profiles = _bond_profiles(project)
    except Exception:  # noqa: BLE001 - a note must not kill a run
        return False
    for sup, _ in piles:
        bp = profiles.get(sup.id)
        if bp is not None and any(t < 0.0 for t in bp.tau):
            return True
    return False

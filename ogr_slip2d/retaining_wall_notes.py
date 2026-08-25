# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Model-level facts about equivalent-fluid-pressure retaining walls.

Asked once per analysis, not once per trial surface: nothing here can
change while the model is being analysed, and a per-surface version of the
same sentence would arrive thousands of times. Same reasoning, and the same
shape, as ``ogr_slip2d.weak_layers.weak_layer_model_warnings`` (v0.1.121).

Two notes. One because a wall drawn flat has no crest, and a profile
defined from the crest down then has no meaning; the other because of rule
7 — the *location of force* control cannot be honoured by five of the nine
methods, and a control that stays quiet about its own reach is as bad as
one that does nothing.

There is deliberately no third note about support patterns; see the tail of
:func:`retaining_wall_notes` for why it would have been dead code.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

#: The methods that write a moment equation, and are therefore the only
#: ones a pure couple can reach. Moving a force leaves a couple; a method
#: that writes force equilibrium alone sees the same force either way, so
#: the *location of force* control is genuinely inert there. Saying which
#: is the honest half of shipping the control at all.
_MOMENT_METHODS = frozenset((
    "ordinary_fellenius", "bishop_simplified", "spencer",
    "gle_morgenstern_price",
))

_FORCE_METHODS = frozenset((
    "janbu_simplified", "janbu_corrected", "corps_engineers_1",
    "corps_engineers_2", "lowe_karafiath",
))


def _walls(project):
    """``(instance, type)`` pairs for every EFP wall placed in the model."""
    by_id = {}
    for stype in getattr(project, "support_types", None) or []:
        by_id[getattr(stype, "TYPE_ID", "")] = stype
    out = []
    for sup in getattr(project, "supports", None) or []:
        if getattr(sup, "type_id", "") != "retaining_wall_efp":
            continue
        stype = by_id.get("retaining_wall_efp")
        if stype is None:
            from ogr_core.support import support_registry
            cls = support_registry().get("retaining_wall_efp")
            if cls is None:
                continue
            stype = cls()
        out.append((sup, stype))
    return out


def retaining_wall_notes(project, method_ids=()) -> list[str]:
    """Notes about the EFP walls in ``project``, for the given methods.

    ``method_ids`` is what the run is about to compute. Empty means "not
    known yet", and then the note about the location of force is phrased
    as a general limitation rather than as a claim about this run.
    """
    walls = _walls(project)
    if not walls:
        return []

    notes: list[str] = []

    flat = [s for s, _ in walls if s.head.y == s.tail.y]
    if flat:
        notes.append(
            "%d retaining wall%s drawn horizontally. Its pressure profile "
            "is defined from the crest downwards and a horizontal wall has "
            "no crest, so it is excluded from the analysis rather than "
            "analysed with a profile that would depend on which end was "
            "drawn first."
            % (len(flat), "" if len(flat) == 1 else "s are"))

    at_centroid = [t for _, t in walls
                   if getattr(t, "force_location", "") == "centroid"]
    if at_centroid:
        blind = sorted(set(method_ids) & _FORCE_METHODS)
        if blind:
            notes.append(
                "The retaining wall force is set to act at the centroid of "
                "its pressure diagram, and %s cannot tell that from acting "
                "at the slip surface: moving a force leaves a couple, and a "
                "couple has nowhere to go in a method that writes force "
                "equilibrium alone. The four methods with a moment equation "
                "— Ordinary, Bishop, Spencer and GLE — do honour it."
                % ", ".join(blind))
        elif not method_ids:
            notes.append(
                "The retaining wall force is set to act at the centroid of "
                "its pressure diagram. Only the four methods with a moment "
                "equation — Ordinary, Bishop, Spencer and GLE — can tell "
                "that apart from acting at the slip surface.")

    # There is deliberately NO note about support patterns here. A wall
    # carries a pressure per metre of slope already, so a row of them would
    # apply the same pressure once per member — but ``SupportPattern``
    # leaves no mark on the instances it generates, so a note at this level
    # could never fire and would be a comforting piece of dead code. The
    # refusal lives where the choice is made instead, in the Add Support
    # Pattern dialog, which filters on ``ALLOWS_PATTERN``.

    return notes

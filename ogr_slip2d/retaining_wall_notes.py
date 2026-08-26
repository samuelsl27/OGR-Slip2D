# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Model-level facts about equivalent-fluid-pressure retaining walls.

Asked once per analysis, not once per trial surface: nothing here can
change while the model is being analysed, and a per-surface version of the
same sentence would arrive thousands of times. Same reasoning, and the same
shape, as ``ogr_slip2d.weak_layers.weak_layer_model_warnings`` (v0.1.121).

Two notes. One is the wall's own: a wall drawn flat has no crest, and a
profile defined from the crest down then has no meaning. The other is rule
7 — the *location of force* control cannot be honoured by five of the nine
methods — and as of v0.1.123 it is no longer written here: a second type
offers the same control, so it moved to
:func:`ogr_slip2d.support_notes.force_location_notes` and this module asks
for it. A rule written in two places goes stale in one of them.

There is deliberately no third note about support patterns; see the tail of
:func:`retaining_wall_notes` for why it would have been dead code.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations


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
    """Notes about the EFP walls in ``project``.

    ``method_ids`` is what the run is about to compute. It is unused since
    v0.1.123 — the only note that depended on it was the one about the
    location of force, which now belongs to
    :func:`ogr_slip2d.support_notes.force_location_notes` — and it stays in
    the signature because every model-level note function in this package
    has it, and one of them differing would be a trap.
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

    # There is deliberately NO note about support patterns here. A wall
    # carries a pressure per metre of slope already, so a row of them would
    # apply the same pressure once per member — but ``SupportPattern``
    # leaves no mark on the instances it generates, so a note at this level
    # could never fire and would be a comforting piece of dead code. The
    # refusal lives where the choice is made instead, in the Add Support
    # Pattern dialog, which filters on ``ALLOWS_PATTERN``.

    return notes

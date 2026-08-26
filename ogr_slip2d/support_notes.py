# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Model-level facts about supports, asked once per analysis.

Not once per trial surface: nothing here can change while the model is
being analysed, and a per-surface version of the same sentence would
arrive thousands of times. Same shape and same reasoning as
``ogr_slip2d.weak_layers.weak_layer_model_warnings`` (v0.1.121).

v0.1.123 — the *location of force* note was born inside
``retaining_wall_notes`` because only one type offered that setting. Two
do now, and a rule written in two places goes stale in one of them, so it
lives here and both modules ask for it. The wording lost the word "wall"
and gained nothing else.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

#: The methods that write a moment equation, and therefore the only ones a
#: pure couple can reach. Moving a force leaves a couple; a method that
#: writes force equilibrium alone sees the same force either way, so the
#: *location of force* control is genuinely inert there. Saying which is
#: the honest half of shipping the control at all.
MOMENT_METHODS = frozenset((
    "ordinary_fellenius", "bishop_simplified", "spencer",
    "gle_morgenstern_price",
))

FORCE_METHODS = frozenset((
    "janbu_simplified", "janbu_corrected", "corps_engineers_1",
    "corps_engineers_2", "lowe_karafiath",
))


def resolved_types(project) -> dict:
    """``{type_id: support type object}`` for the types this project uses.

    The instance carries only a ``type_id`` — the type object itself lives
    in ``project.support_types`` — and a project may legitimately carry
    neither, so a missing type falls back to a default-constructed one from
    the registry rather than to an exception.
    """
    by_id = {}
    for stype in getattr(project, "support_types", None) or []:
        tid = getattr(stype, "TYPE_ID", "")
        if tid:
            by_id[tid] = stype
    out = {}
    for sup in getattr(project, "supports", None) or []:
        tid = getattr(sup, "type_id", "")
        if not tid or tid in out:
            continue
        stype = by_id.get(tid)
        if stype is None:
            from ogr_core.support import support_registry
            cls = support_registry().get(tid)
            if cls is None:
                continue
            stype = cls()
        out[tid] = stype
    return out


def supports_of(project, type_id: str) -> list:
    """The instances of one type placed in the model."""
    return [s for s in (getattr(project, "supports", None) or [])
            if getattr(s, "type_id", "") == type_id]


def force_location_notes(project, method_ids=()) -> list[str]:
    """What the *location of force* setting cannot do, and in which methods.

    ``method_ids`` is what the run is about to compute. Empty means "not
    known yet", and the note is then phrased as a general limitation rather
    than as a claim about this run.
    """
    at_centroid = [t for t in resolved_types(project).values()
                   if getattr(t, "force_location", "") == "centroid"]
    if not at_centroid:
        return []
    blind = sorted(set(method_ids) & FORCE_METHODS)
    if blind:
        return ["The support force is set to act at the centroid of its "
                "pressure diagram, and %s cannot tell that from acting at "
                "the slip surface: moving a force leaves a couple, and a "
                "couple has nowhere to go in a method that writes force "
                "equilibrium alone. The four methods with a moment "
                "equation — Ordinary, Bishop, Spencer and GLE — do honour "
                "it." % ", ".join(blind)]
    if not method_ids:
        return ["The support force is set to act at the centroid of its "
                "pressure diagram. Only the four methods with a moment "
                "equation — Ordinary, Bishop, Spencer and GLE — can tell "
                "that apart from acting at the slip surface."]
    return []

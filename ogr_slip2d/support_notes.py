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

from . import note_messages as N
from .note_messages import note as _note

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


def supports_by_type(project) -> list:
    """``[(type object, [its instances])]``, one entry per resolved set.

    v0.1.149 — grouped by the OBJECT, not by class: two sets of one class
    are two entries, where the ``{type_id: type}`` dictionary this replaces
    kept one and every note below saw only that one. The instance carries
    a reference — the type object itself lives in ``project.support_types``
    — and a project may legitimately carry neither, so a support whose
    class has no set in the project resolves to a registry default and
    forms an entry of its own (see ``ogr_core.support.resolve_support_type``
    for the order, which is the engine's).
    """
    from ogr_core.support import support_type_pairs

    groups: list = []
    for sup, stype in support_type_pairs(project):
        for st, sups in groups:
            if st is stype:
                sups.append(sup)
                break
        else:
            groups.append((stype, [sup]))
    return groups


def resolved_types(project) -> dict:
    """``{set id: support type object}`` for the sets this project uses.

    Keyed by the set's own ``id`` since v0.1.149; it was keyed by class,
    which is the collapse :func:`supports_by_type` describes.
    """
    return {getattr(st, "id", id(st)): st
            for st, _sups in supports_by_type(project)}


def support_identity_notes(project, method_ids=()) -> list[str]:
    """Where the property set of a support was GUESSED, not declared.

    v0.1.149 — ``resolve_support_type`` falls back on the class when an
    instance names no set, or names one the project no longer holds. With
    one set per class the fallback is exact and there is nothing to say;
    with several it is a choice the user never made, and the analysis
    says which one it took rather than computing in silence — silence is
    what kept defect D66 open while every file looked correct.
    """
    from ogr_core.support import unresolved_support_refs

    def _name(st):
        return (getattr(st, "_display_name", "")
                or getattr(st, "DISPLAY_NAME", "")
                or getattr(st, "TYPE_ID", ""))

    refs = unresolved_support_refs(project)
    notes: list[str] = []
    by_class: dict = {}
    for sup, same in refs["ambiguous"]:
        by_class.setdefault(getattr(sup, "type_id", ""),
                            (same, []))[1].append(sup)
    for tid, (same, sups) in by_class.items():
        notes.append(_note(
            N.SUPPORT_AMBIGUOUS_SET, n=len(sups),
            cls=getattr(same[0], "DISPLAY_NAME", tid), n_sets=len(same),
            sets=", ".join("'%s'" % _name(st) for st in same),
            first=_name(same[0])))
    for sup, used in refs["orphan"]:
        name = getattr(sup, "name", "") or sup.id
        notes.append(
            _note(N.SUPPORT_ORPHAN_REPLACED, name=name, used=_name(used))
            if used is not None else
            _note(N.SUPPORT_ORPHAN_DROPPED, name=name))
    return notes


def infinite_strength_notes(project, method_ids=()) -> list[str]:
    """The supports that read the soil and run through a material whose
    strength is not finite, where that soil is read as ZERO.

    v0.1.231 (D227, finding c) -- see
    ``ogr_core.support.bond.infinite_soil_at`` for the decision and why it
    stays. The note samples the axis where the bond profile samples it (the
    mid-points of its segments) and, for a type with plates, each plate.
    """
    from ogr_core.support.bond import DEFAULT_SEGMENTS, infinite_soil_at

    def _name(st):
        return (getattr(st, "_display_name", "")
                or getattr(st, "DISPLAY_NAME", "")
                or getattr(st, "TYPE_ID", ""))

    notes: list[str] = []
    for stype, sups in supports_by_type(project):
        if not getattr(stype, "READS_SOIL_STRENGTH", False):
            continue
        for sup in sups:
            length = sup.length()
            if length <= 0.0:
                continue
            hx, hy = sup.head.x, sup.head.y
            ux = (sup.tail.x - hx) / length
            uy = (sup.tail.y - hy) / length
            axis = sup.axis_angle_rad()

            def _in_it(s, names):
                mat = infinite_soil_at(project, hx + ux * s, hy + uy * s,
                                       axis)
                if mat is not None:
                    names.add(getattr(mat, "name", "") or "?")
                return mat is not None

            names: set = set()
            plates = [min(max(0.0, float(d)), length)
                      for d in stype.station_distances(length)]
            try:
                hits = sum(_in_it((i + 0.5) * length / DEFAULT_SEGMENTS,
                                  names)
                           for i in range(DEFAULT_SEGMENTS))
                plate_hits = sum(_in_it(d, names) for d in plates)
            except Exception:  # noqa: BLE001 - said by the profile channel
                # The same reading fails when the bond profile is built,
                # and the analysis says so for this support: "cannot be
                # priced" with its reason (D227, D95), or the note on a
                # profile that would not build. A note must not kill the
                # run that would have said it.
                continue
            if not hits and not plate_hits:
                continue
            code = (N.SUPPORT_INFINITE_BOTH if hits and plate_hits
                    else N.SUPPORT_INFINITE_LENGTH if hits
                    else N.SUPPORT_INFINITE_PLATES)
            notes.append(_note(
                code, name=getattr(sup, "name", "") or sup.id,
                type_name=_name(stype),
                percent=100.0 * hits / DEFAULT_SEGMENTS,
                hit_plates=plate_hits, n_plates=len(plates),
                materials=", ".join("'%s'" % n for n in sorted(names))))
    return notes


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
        return [_note(N.FORCE_AT_CENTROID_BLIND, methods=", ".join(blind))]
    if not method_ids:
        return [_note(N.FORCE_AT_CENTROID)]
    return []

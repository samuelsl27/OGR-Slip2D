# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What a helical anchor cannot say for itself, said once per analysis.

Three of the reference's own design recommendations are quantitative, and
a model that breaks one produces a number that is arithmetically right and
physically doubtful. The analysis says so rather than adjusting anything:
this project fixes geometry in the model, never inside a calculation.

Same shape and same reasoning as ``ito_matsui_notes`` (v0.1.123): asked
once per analysis, because nothing here can change while a search runs.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from .support_notes import resolved_types, supports_of

#: The spacing-to-diameter band the reference recommends. Outside it the
#: three failure types stop describing what they were derived for: too
#: close and the plates cannot mobilise separate bearing bulbs, too far and
#: no cylinder forms between them.
SPACING_RATIO_MIN = 5.0
SPACING_RATIO_MAX = 12.0


def helical_anchor_notes(project, method_ids=()) -> list[str]:
    """Model-level warnings for every helical anchor in the project."""
    from ogr_core.support.helical_anchor import effective_spacing

    notes: list[str] = []
    for type_id, stype in resolved_types(project).items():
        if type_id != "helical_anchor":
            continue
        diameter = float(getattr(stype, "average_helix_diameter", 0.0))
        width = float(getattr(stype, "shaft_width", 0.0))
        spacing = float(getattr(stype, "helix_spacing", 0.0))
        n = int(getattr(stype, "number_of_helices", 1))

        # A shaft as wide as the helix leaves no plate. Not a
        # recommendation but an error: every bearing term is then zero and
        # the anchor carries nothing in pullout, which reads as a support
        # that does nothing rather than as a model to correct.
        if width >= diameter > 0.0:
            for sup in supports_of(project, type_id):
                notes.append(
                    "The shaft of support '%s' is not narrower than its "
                    "helices, so the plates have no bearing area and the "
                    "anchor carries nothing in pullout."
                    % (getattr(sup, "name", "") or sup.id))
            continue

        if diameter > 0.0 and n >= 2:
            for sup in supports_of(project, type_id):
                length = sup.length()
                used = effective_spacing(n, spacing, length)
                if used <= 0.0:
                    continue
                # The re-spacing the reference documents for input that
                # does not fit. Silent adjustment is how a model comes to
                # mean something the user never typed.
                if abs(used - spacing) > 1e-9:
                    notes.append(
                        "The %d helices of support '%s' do not fit at "
                        "%.2f m: the spacing used is %.2f m, the anchor "
                        "length divided by the number of gaps."
                        % (n, getattr(sup, "name", "") or sup.id,
                           spacing, used))
                ratio = used / diameter
                if not (SPACING_RATIO_MIN <= ratio <= SPACING_RATIO_MAX):
                    notes.append(
                        "The helix spacing of support '%s' is %.2f times "
                        "the average helix diameter. Design guides "
                        "recommend 5 to 12."
                        % (getattr(sup, "name", "") or sup.id, ratio))
    return notes

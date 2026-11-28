# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""What converting or deleting a boundary did to the links of the materials,
said in words (v0.1.507, D443).

The rule is the core's (``ogr_core.project.rules.relink_on_conversion`` and
``unlink_on_removal``, OGR Core 0.2.14, the owner's decision B of
2026-11-27): a water table into a piezometric line, or back, keeps the link
and the pore-pressure model follows the boundary (FOLLOWED); any other
conversion that leaves a link with no reader, and every deletion, clears it
(CLEARED). The core returns the changes and the program writes the notes;
this is the ONE place that writes them, for the window and for the agent,
so the two doors say the same. No Qt: the window hands its ``tr`` and its
label of a boundary type.
"""
from __future__ import annotations

from typing import Callable, Optional

#: The sentences, in English, as the agent has said the cleared ones since
#: v0.1.200; the window translates them (``ogr_gui/i18n``).
NO_WATER_SURFACE = "Materials that used it now have no water surface: {0}"
LOST_ANISOTROPIC = "'{0}' lost its anisotropic surface."
FOLLOW_AS = "Materials that used it now read it as a {0}: {1}"


def link_change_notes(changes, new_type=None, *,
                      translate: Optional[Callable[[str], str]] = None,
                      type_label: Optional[Callable] = None) -> list:
    """The notes of ``changes`` (a list of the core's ``LinkChange``), in
    the order water first, then anisotropic surfaces.

    ``new_type`` is the type a FOLLOWED link now reads (a conversion);
    ``translate`` maps an English template to the reader's language and
    ``type_label`` names a boundary type for that reader (the window's
    ``tr`` and ``boundary_type_label``; the agent passes neither and reads
    English and the type's display name)."""
    from ogr_core.project.rules import (ANISOTROPIC_SURFACE_LINK, CLEARED,
                                        FOLLOWED, WATER_SURFACE_LINK)
    t = translate or (lambda s: s)
    water_cleared = [c.material_name for c in changes
                     if c.link == WATER_SURFACE_LINK and c.change == CLEARED]
    water_followed = [c.material_name for c in changes
                      if c.link == WATER_SURFACE_LINK
                      and c.change == FOLLOWED]
    out = []
    if water_followed and new_type is not None:
        label = (type_label(new_type) if type_label is not None
                 else new_type.display_name)
        out.append(t(FOLLOW_AS).format(label, ", ".join(water_followed)))
    if water_cleared:
        out.append(t(NO_WATER_SURFACE).format(", ".join(water_cleared)))
    for c in changes:
        if c.link == ANISOTROPIC_SURFACE_LINK and c.change == CLEARED:
            out.append(t(LOST_ANISOTROPIC).format(c.material_name))
    return out

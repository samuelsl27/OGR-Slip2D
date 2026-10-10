# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The colour a NEW material gets (v0.1.299, D297).

Every material used to be born ``#d4a373`` — the default of
``Material.color`` — whether the API created it (``model_define``,
``material_set``) or the window did (*Define Materials* → Add): two materials
of a model were indistinguishable on the canvas until someone picked a
colour by hand (the second GUI test). The palette below is muted earth and
pastel tones, distinct from each other and readable under the black
boundaries; its first entry IS the old default, so a one-material model
looks as it always did. A colour chosen by hand, or loaded from a file, is
never touched: only a new material asks.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from typing import Iterable

#: The colours, in the order new materials take them.
MATERIAL_PALETTE = (
    "#d4a373",  # sand (the old default)
    "#8fb3d9",  # blue grey
    "#a8c686",  # sage
    "#e6a1a1",  # pink clay
    "#c3a6d8",  # lilac
    "#f2d07e",  # ochre
    "#9ccfcb",  # teal
    "#c8b39a",  # taupe
    "#b0b0b0",  # grey
    "#e3b5d6",  # rose
    "#7fa8a1",  # slate green
    "#d9c27f",  # straw
)


def next_material_color(used: Iterable[str]) -> str:
    """The first colour of the palette that no material uses yet; when all
    twelve are taken, they repeat in order."""
    taken = {str(c).strip().lower() for c in used if c}
    for colour in MATERIAL_PALETTE:
        if colour not in taken:
            return colour
    return MATERIAL_PALETTE[len(taken) % len(MATERIAL_PALETTE)]

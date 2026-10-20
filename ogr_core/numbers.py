# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Small numerical helpers shared by the core and the interface.

``nice_step`` moved here in v0.1.337 from ``ogr_gui.canvas.snap_engine``
(which re-exports it): the axes of an annotation need it to place their
ticks, and the DXF export, which draws them too, lives in the core and may
not import the interface.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math


def nice_step(target_world: float) -> float:
    """Round to a 1-2-5-10 decade step (for ruler / grid auto-spacing)."""
    if target_world <= 0:
        return 1.0
    mag = 10 ** math.floor(math.log10(target_world))
    normalized = target_world / mag
    if normalized < 1.5:
        step = 1.0
    elif normalized < 3.5:
        step = 2.0
    elif normalized < 7.5:
        step = 5.0
    else:
        step = 10.0
    return step * mag

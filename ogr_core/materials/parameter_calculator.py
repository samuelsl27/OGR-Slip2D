# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Parameter Calculator — phase M6.

Derives the Generalised Hoek-Brown constants ``mb``, ``s`` and ``a`` from
the Geological Strength Index, the intact rock constant ``mi`` and the
disturbance factor ``D``, using the equations of Hoek, Carranza-Torres and
Corkum (2002):

    mb = mi · exp((GSI − 100) / (28 − 14 D))
    s  =      exp((GSI − 100) / (9  − 3 D))
    a  = 0.5 + (1/6) · (exp(−GSI/15) − exp(−20/3))

Kept free of Qt, both so the equations can be tested against published
values and because these constants belong to the rock-mechanics domain,
not to the interface.

Two things the implementation is careful about:

* **D = 2 is a singularity of the s equation** (9 − 3·2 = 3 is fine, but
  28 − 14·2 = 0 makes mb undefined). D is therefore clamped to just below
  2, and the caller is told, rather than the calculation raising or —
  worse — returning infinity.
* **GSI and D are guidance-based quantities**, so the module ships the
  descriptive tables the reference offers through its "Pick" buttons.
  Numbers typed without that context are the usual source of a wrong
  Hoek-Brown envelope.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

# Disturbance factor guidance (Hoek et al., 2002). Excavation method
# matters as much as rock quality, which is why it deserves a table.
DISTURBANCE_GUIDANCE = (
    (0.0, "Excellent quality controlled blasting or TBM: no disturbance"),
    (0.0, "Mechanical or hand excavation, no blasting"),
    (0.5, "Mechanical excavation with squeezing problems and no invert"),
    (0.7, "Good blasting, small-scale slope"),
    (0.7, "Mechanical excavation in a slope"),
    (1.0, "Poor blasting, small-scale slope"),
    (0.7, "Production blasting, large slope, controlled"),
    (1.0, "Production blasting, large slope, uncontrolled"),
)

# Intact rock constant mi, by lithology (indicative ranges).
MI_GUIDANCE = (
    ("Granite", 32), ("Granodiorite", 29), ("Diorite", 25),
    ("Gabbro", 27), ("Dolerite", 16), ("Basalt", 16), ("Rhyolite", 25),
    ("Andesite", 25), ("Gneiss", 28), ("Amphibolite", 26),
    ("Quartzite", 20), ("Marble", 9), ("Migmatite", 29),
    ("Schist", 12), ("Phyllite", 7), ("Slate", 7),
    ("Sandstone", 17), ("Conglomerate", 21), ("Breccia", 19),
    ("Siltstone", 7), ("Claystone", 4), ("Shale", 6),
    ("Greywacke", 18), ("Limestone (crystalline)", 12),
    ("Limestone (micritic)", 9), ("Dolomite", 9), ("Gypsum", 8),
    ("Anhydrite", 12), ("Chalk", 7), ("Marl", 7),
)

# GSI bands, as a coarse but honest guide.
GSI_GUIDANCE = (
    (85, "Intact or massive, very good surfaces"),
    (75, "Blocky, well interlocked, good surfaces"),
    (60, "Very blocky, interlocked, fair surfaces"),
    (45, "Blocky / disturbed / seamy, fair to poor surfaces"),
    (30, "Disintegrated, poor surfaces"),
    (15, "Laminated / sheared, very poor surfaces"),
)

_D_LIMIT = 1.999      # 28 − 14·2 = 0: mb is undefined at exactly D = 2


@dataclass
class HoekBrownParameters:
    """Result of the calculation."""

    mb: float = 0.0
    s: float = 0.0
    a: float = 0.5
    gsi: float = 100.0
    mi: float = 10.0
    d: float = 0.0
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"mb": self.mb, "s": self.s, "a": self.a,
                "gsi": self.gsi, "mi": self.mi, "d": self.d}

    def summary(self) -> str:
        return (f"GSI = {self.gsi:g}, mi = {self.mi:g}, D = {self.d:g}  "
                f"→  mb = {self.mb:.4f}, s = {self.s:.6f}, "
                f"a = {self.a:.4f}")


def calculate_hoek_brown(gsi: float, mi: float,
                         d: float = 0.0) -> HoekBrownParameters:
    """The Generalised Hoek-Brown constants from GSI, mi and D.

    Args:
        gsi: Geological Strength Index, 0 to 100.
        mi: intact rock constant.
        d: disturbance factor, 0 to 2.
    """
    res = HoekBrownParameters()
    res.gsi = max(0.0, min(100.0, float(gsi)))
    res.mi = max(0.0, float(mi))
    d = max(0.0, min(2.0, float(d)))
    if d > _D_LIMIT:
        # Clamped rather than left to divide by zero: mb would become
        # infinite, and an infinite strength constant silently produces a
        # meaningless envelope instead of an error.
        res.notes.append(
            "D = 2 makes mb undefined (28 − 14 D = 0); it has been "
            "clamped to 1.999.")
        d = _D_LIMIT
    res.d = d

    if res.gsi != gsi:
        res.notes.append("GSI was clamped to the range 0 to 100.")

    res.mb = res.mi * math.exp((res.gsi - 100.0) / (28.0 - 14.0 * d))
    res.s = math.exp((res.gsi - 100.0) / (9.0 - 3.0 * d))
    res.a = 0.5 + (1.0 / 6.0) * (math.exp(-res.gsi / 15.0)
                                 - math.exp(-20.0 / 3.0))
    return res


def sigma3_max_slope(sigma_ci: float, unit_weight: float,
                     height: float) -> float:
    """Upper confining stress for fitting a slope, per Hoek et al. (2002).

    Included because a Hoek-Brown envelope has to be fitted over a stress
    range, and using the tunnel expression on a slope is a common and
    quiet error: the slope relation gives a markedly lower bound.
    """
    if sigma_ci <= 0 or unit_weight <= 0 or height <= 0:
        return 0.0
    sigma_cm = sigma_ci        # normalised on the intact strength
    return 0.72 * sigma_cm * ((unit_weight * height) / sigma_cm) ** -0.91

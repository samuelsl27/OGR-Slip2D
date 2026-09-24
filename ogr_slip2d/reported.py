# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Which quantity the headline number of a run IS.

v0.1.194 (spec 008) — the decision moved here from
``ogr_gui/reported_quantity.py``, which keeps the translated captions. It
moved because a second caller appeared that cannot import the interface:
the operations layer an AI agent drives (``ogr_api``). Deciding it twice is
how v0.1.165 (D96) found six captions saying four different things.

The question is asked of the RESULT and of the run's factor report, never
of ``project.settings``: the settings can change after a run, what the run
did cannot (the v0.1.127 rule).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

#: The four things the critical number of a run can be.
FOS = "fos"
OVERDESIGN = "overdesign"
KY = "ky"
NEWMARK = "newmark"


def reported_caption(result, factor_report=None) -> str:
    """One of :data:`FOS`, :data:`OVERDESIGN`, :data:`KY`, :data:`NEWMARK`.

    Precedence: the caption follows the value that is printed. With
    "Compute Ky" on, the number shown is a seismic coefficient, and a
    seismic coefficient does not become an over-design factor because
    partial factors were applied to the soil — so the seismic caption
    wins. The command line resolves this the other way round
    (``ogr_cli/__main__.py``: ``if seismic_objective and not factored``);
    that is reported as a defect of the command line, not copied here.

    With a design standard active the partial factors are applied to the
    INPUTS, so what comes out is not a factor of safety: it is an
    over-design factor, and it must exceed 1.
    """
    if getattr(result, "objective", "fos") == "ky":
        critical = getattr(result, "critical", None)
        details = (getattr(critical, "details", None) or {}) if critical \
            else {}
        if "newmark_displacement" in details:
            return NEWMARK
        return KY
    if bool(getattr(factor_report, "applied", False)):
        return OVERDESIGN
    return FOS

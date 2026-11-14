# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Which quantity the headline number of a run IS.

v0.1.194 (spec 008) — the decision moved here from
``ogr_gui/reported_quantity.py``, which keeps the translated captions,
because the operations layer an AI agent drives (``ogr_api``) cannot import
the interface. v0.1.430 (D405) added what that number is under a design
standard (``standard_note``) and the caption of a run of several methods
(``run_caption``).

v0.1.449 (D408) — the rule lives in the core since this version,
``ogr_core/project/reported.py``, because the PDF report
(``ogr_core.report``) needs it and the core cannot import the engine. This
module re-exports every name, so the engine, the API, the command line and
the window keep asking ``ogr_slip2d.reported`` and get the same rule; read
the docstrings there.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from ogr_core.project.reported import (  # noqa: F401 - re-exported
    FOS, KY, NEWMARK, OVERDESIGN, REPORTED_NOTES, STANDARD_KY,
    STANDARD_KY_FACTOR, STANDARD_NEWMARK, STANDARD_NEWMARK_FACTOR,
    STANDARD_OVERDESIGN, displacement_in_units, factor_kh, reported_caption,
    run_caption, standard_note)

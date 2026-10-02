# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
What to CALL the headline number of a run.

v0.1.165 (D96) — six places print the critical number of a run, and each
one used to decide its own caption. They disagreed: the status bar said
``Critical FoS`` translated, the results dock said the same words in English
three pixels below it, and two read-outs in Interpret said ``FoS`` while the
summary dock of that same window said ``Critical seismic coefficient``. A
design standard adds a fourth thing the number can be called, and captions
decided in six places is how they came to disagree in the first place. One
decision, one place.

The caption is asked of the RESULT and of the run's factor report, never of
``project.settings``. That is the v0.1.127 rule kept intact: a widget that
reads the settings can disagree with the results it is showing, which is how
a stale panel reports a number the analysis never produced. The settings can
change after a run; what the run did cannot.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from .i18n import tr


def reported_quantity(result, factor_report=None):
    """``("fos" | "ky" | "newmark", label)`` for one search result.

    ``kind`` names the QUANTITY, ``label`` names it for the user, and the
    two are deliberately not the same thing. An over-design factor is
    ``critical.fos`` computed on factored inputs: same units, same
    formatting, same field — so its ``kind`` stays ``"fos"`` and only the
    caption changes. Callers that branch on ``kind`` to decide how to
    FORMAT the number therefore need no change, and cannot silently start
    printing a Ky where a factor belongs.

    Precedence: the caption follows the value that is printed. With
    "Compute Ky" on, the number shown is a seismic coefficient, and a
    seismic coefficient does not become an over-design factor because
    partial factors were applied to the soil — so the seismic caption
    wins. The command line resolves this the other way round
    (``ogr_cli/__main__.py``: ``if seismic_objective and not factored``),
    which prints a Ky value under an "Over-design factor" heading; that is
    reported as a defect of the command line, not copied here.

    v0.1.194 (spec 008) — WHICH caption is decided by
    ``ogr_slip2d.reported.reported_caption``, which the operations layer
    an agent drives asks too; only the translated words stay here.
    """
    from ogr_slip2d.reported import KY, NEWMARK, OVERDESIGN, reported_caption

    caption = reported_caption(result, factor_report)
    if caption == NEWMARK:
        return "newmark", tr("Newmark displacement")
    if caption == KY:
        return "ky", tr("Critical seismic coefficient")
    # With a design standard active the partial factors are applied to the
    # INPUTS, so what comes out is not a factor of safety: it is an
    # over-design factor, and it must exceed 1. Saying "FoS" over it is the
    # window contradicting the analysis it just ran.
    if caption == OVERDESIGN:
        return "fos", tr("Over-design factor")
    return "fos", tr("Factor of safety")


def fos_label(factor_report=None) -> str:
    """The caption for a widget that always prints ``critical.fos``.

    Separate from :func:`reported_quantity` on purpose, and the reason is
    worth stating because merging them looks like an obvious simplification
    and would be a defect. The status bar and the results dock print
    ``critical.fos`` and nothing else — including on a Ky run, where
    ``.fos`` is a real and correctly labelled factor of safety (the
    Interpret tooltip shows it as ``FS(0)``), just not the quantity the
    search minimised. Handing those two widgets the seismic caption would
    put "Critical seismic coefficient" over a factor of safety: the exact
    fault this module exists to prevent, with the sign reversed.

    So the seismic question is asked only where the VALUE also changes, and
    here the only question is which of the two things a ``.fos`` can be.
    """
    if bool(getattr(factor_report, "applied", False)):
        return tr("Over-design factor")
    return tr("Critical FoS")


def sample_label(factor_report=None) -> str:
    """The caption of the values a STATISTICAL run collects.

    v0.1.236 (D93) — every sample is a ``result.fos`` computed on the
    prepared copy of the sampled model (under a critical-coefficient mode
    the evaluator chooses the mass by Ky, but the value kept is still the
    factor of safety, v0.1.235), so the only question is the one
    :func:`fos_label` asks: whether a design standard factored the inputs.
    "Factor of safety" otherwise, and not "Critical FoS": a histogram of the
    samples is not one critical value. Asked of the statistics run's own
    report, never of the settings, for the reason the module docstring
    gives.
    """
    if bool(getattr(factor_report, "applied", False)):
        return tr("Over-design factor")
    return tr("Factor of safety")


def statistics_factor_lines(factor_report=None) -> list:
    """What a design standard did to a statistical run, as note lines.

    v0.1.236 (D93) — the statistical counterpart of the line Compute puts
    first since v0.1.165 (D96). Its own sentence, because what it qualifies
    is not one reported value but every sample, and so the probability of
    failure and the reliability index computed from them. The report's own
    notes follow, untranslated, as the deterministic path carries them
    (``ogr_core`` cannot import ``ogr_gui.i18n``). Empty without a standard,
    so the notes of a run without one are exactly what they were.
    """
    if not bool(getattr(factor_report, "applied", False)):
        return []
    lines = [tr("Design standard applied to every sample: %s — the "
                "statistics describe the over-design factor, not the factor "
                "of safety") % factor_report.summary()]
    lines += [str(n) for n in (getattr(factor_report, "notes", None) or [])]
    return lines

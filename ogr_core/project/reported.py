# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Which quantity the headline number of a run IS.

v0.1.194 (spec 008) — the decision moved to ``ogr_slip2d/reported.py`` from
``ogr_gui/reported_quantity.py``, which keeps the translated captions. It
moved because a second caller appeared that cannot import the interface:
the operations layer an AI agent drives (``ogr_api``). Deciding it twice is
how v0.1.165 (D96) found six captions saying four different things.

v0.1.449 (D408) — and it moved here, to the core, for a third caller that
cannot import the engine: the PDF report (``ogr_core.report``), which wrote
``critical.fos`` under «Over-design Factor» on a Ky or a Newmark run, where
the critical surface is the one of the lowest Ky and its factor need not be
the lowest. ``ogr_slip2d.reported`` re-exports every name, so the engine,
the API, the command line and the window ask the same rule as before.

The question is asked of the RESULT and of the run's factor report, never
of ``project.settings``: the settings can change after a run, what the run
did cannot (the v0.1.127 rule).

Author: Samuel Sáez López (UPCT)

v0.1.430 (D405) -- and what that number IS under a design standard, the
sentence every front end prints first (:func:`standard_note`), and the
caption of a run of several methods printed under one heading
(:func:`run_caption`). The command line and the window each wrote their
own, and both wrote the over-design one on every run with an applied
standard, over a seismic coefficient or a Newmark displacement too.
"""
from __future__ import annotations

from ogr_core.messages import MessageSpec, as_nested, coded

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
    wins. The command line resolved this the other way round until
    v0.1.430 (``if seismic_objective and not factored``, reported in
    v0.1.165): with a standard and Newmark it printed a displacement in
    centimetres under "Over-design factor", over a note saying it must
    exceed 1 (D405). It asks :func:`run_caption` since.

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


def run_caption(results, factor_report=None) -> str:
    """The caption of a run of several methods whose critical numbers are
    printed under one heading -- the command line's column, the window's
    first note (v0.1.430, D405).

    :func:`reported_caption` of each result, and :data:`NEWMARK` when ANY
    method's critical surface carries a displacement, not only the first's
    (v0.1.429, D397): a first method left without a critical surface --
    Spencer and GLE find no Ky on a plane with kh, D143 -- put the whole
    column under "Critical Ky" and hid every other method's displacement.
    With no result at all, what one would be called: an over-design factor
    under an applied standard, a factor of safety otherwise.
    """
    captions = [reported_caption(r, factor_report) for r in results]
    if NEWMARK in captions:
        return NEWMARK
    if captions:
        return captions[0]
    if bool(getattr(factor_report, "applied", False)):
        return OVERDESIGN
    return FOS


def factor_kh(item) -> float:
    """The horizontal seismic coefficient ``item.fos`` was computed at:
    the one the method applied, ``details["kh"]``, and 0.0 when the result
    does not keep it (v0.1.449, D408).

    On a "Compute Ky" run the factor of the critical surface is the factor
    at the PROJECT's coefficient, and the Ky beside it is solved over kh
    from zero (``ogr_slip2d.yield_acceleration``, which keeps the project's
    kv): so that factor is the one at kh = 0 only when the project applies
    none, and a door that prints it beside the Ky says which it is. Under a
    Ky mode the design standard does not factor kh
    (``design_factors.SEISMIC_NOT_APPLIED``), so this is the project's own.
    """
    details = getattr(item, "details", None) or {}
    try:
        return float(details.get("kh", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def displacement_in_units(project, metres) -> tuple:
    """``(value, unit)`` of a Newmark displacement for the reader.

    It is stored in metres, as every length in this program is, and is
    given through the project's SMALL_LENGTH quantity -- the one the units
    page reserves for settlements and displacements -- so a metric model
    reads centimetres and an imperial one inches. With no project to ask,
    or a conversion that fails, centimetres, which is what the reference
    prints. Moved here from ``ogr_gui.interpret_window._reported_value``
    (v0.1.449, D408), which asks it, so the report and Interpret print one
    number in one unit.

    v0.1.227 (D225) — ``get_system()``: the window called ``unit_system()``,
    which ``Units`` has never had, and a bare ``except`` swallowed the
    AttributeError, so an imperial project read centimetres too. Only a
    conversion error falls back; a misspelt name raises.
    """
    from ogr_core.units.quantities import Quantity

    value, unit = metres * 100.0, "cm"
    units = getattr(getattr(project, "settings", None), "units", None)
    if units is not None:
        try:
            system = units.get_system()
            value = system.to_user(metres, Quantity.SMALL_LENGTH)
            unit = system.label_for(Quantity.SMALL_LENGTH)
        except (ValueError, KeyError):
            value, unit = metres * 100.0, "cm"
    return value, unit


#: v0.1.430 (D405) -- what the reported value is under a design standard,
#: one sentence for each caption. Codes are ``reported.*``; the interface
#: translates them (``ogr_gui.core_messages``).
STANDARD_OVERDESIGN = "reported.standard_overdesign"
STANDARD_KY = "reported.standard_ky"
STANDARD_NEWMARK = "reported.standard_newmark"
#: The two for a door that prints the factor of the critical surface beside
#: its Ky: the window, whose status bar and results panel print
#: ``critical.fos`` on every run (v0.1.165, D96), an over-design factor under
#: a standard. Saying there that the value is not one contradicted the bar.
#: The PDF report is such a door too since v0.1.449 (D408).
STANDARD_KY_FACTOR = "reported.standard_ky_factor"
STANDARD_NEWMARK_FACTOR = "reported.standard_newmark_factor"

REPORTED_NOTES = {s.code: s for s in (
    MessageSpec(STANDARD_OVERDESIGN,
                "Design standard applied: {summary} — the reported value is "
                "an over-design factor, not a factor of safety, and must "
                "exceed 1."),
    MessageSpec(STANDARD_KY,
                "Design standard applied: {summary} — the reported value is "
                "the critical seismic coefficient with the partial factors "
                "applied, not an over-design factor."),
    MessageSpec(STANDARD_NEWMARK,
                "Design standard applied: {summary} — the reported value is "
                "the Newmark displacement with the partial factors applied, "
                "not an over-design factor."),
    MessageSpec(STANDARD_KY_FACTOR,
                "Design standard applied: {summary} — the critical seismic "
                "coefficient is computed with the partial factors applied, "
                "and the factor shown for the critical surface is an "
                "over-design factor, not a factor of safety, and must exceed "
                "1."),
    MessageSpec(STANDARD_NEWMARK_FACTOR,
                "Design standard applied: {summary} — the critical seismic "
                "coefficient and the Newmark displacement are computed with "
                "the partial factors applied, and the factor shown for the "
                "critical surface is an over-design factor, not a factor of "
                "safety, and must exceed 1."),
)}

_STANDARD_NOTE = {OVERDESIGN: STANDARD_OVERDESIGN, KY: STANDARD_KY,
                  NEWMARK: STANDARD_NEWMARK}
_STANDARD_NOTE_WITH_FACTOR = {OVERDESIGN: STANDARD_OVERDESIGN,
                              KY: STANDARD_KY_FACTOR,
                              NEWMARK: STANDARD_NEWMARK_FACTOR}


def standard_note(caption: str, factor_report, *, shows_factor=False):
    """What the reported value is under the run's design standard -- the
    note the window and the command line print before any other, and the
    PDF report in its «Design Standard» section -- or None when no standard
    was applied.

    ``caption`` is :func:`run_caption` for a run, :func:`reported_caption`
    for one result. A seismic coefficient and a Newmark displacement are
    not over-design factors because partial factors were applied to the
    soil, and neither has to exceed 1: until v0.1.430 both front ends said
    it of them (D405). The coefficient and the displacement are those of the
    factored model, whatever the standard factors: the materials (it divides
    c and tan φ) or the actions (it multiplies the weight and the loads; with
    those alone, the Ky of a dry cohesionless plane is the unfactored one).

    ``shows_factor`` for a door that prints the factor of the critical
    surface beside its Ky or its displacement, as the window and, since
    v0.1.449, the PDF report do: its sentence says what both are. The
    command line prints the Ky or the displacement alone.
    """
    if not bool(getattr(factor_report, "applied", False)):
        return None
    table = _STANDARD_NOTE_WITH_FACTOR if shows_factor else _STANDARD_NOTE
    code = table.get(caption, STANDARD_OVERDESIGN)
    return coded(REPORTED_NOTES, code,
                 summary=as_nested(factor_report.summary()))

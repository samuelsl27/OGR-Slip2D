# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Model invariants that used to live only in the interface.

v0.1.194 (spec 008) — every rule in this module was, until this version,
enforced by the main window and by nothing else: greying a menu action,
or refusing inside a click handler. ``Project.add_boundary`` accepted a
second water table without a word, and ``ogr_slip2d/slicer.py`` says in so
many words that the engine never checks it either. So a script, the
command line, or an AI agent driving the program could build a model the
interface cannot, and get a number for it.

The rules are MOVED here, not copied: the interface now asks this module
the same question and only keeps its tooltips, which are presentation. A
rule written twice is a rule that will disagree with itself, which is how
the six captions of v0.1.165 (D96) came to say different things.

Nothing here imports Qt or the solver packages. Messages are English, like
every message the engine produces; the interface translates its own.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from ..geometry import BoundaryType


@dataclass(frozen=True)
class Refusal:
    """Why an edit or a run is not allowed.

    ``code`` is for a program to branch on and never changes wording;
    ``message`` is for a person or a language model to read.
    """

    code: str
    message: str


#: Boundary types a model may hold at most one of. EXTERNAL is here
#: because the region subdivision reads ``external_boundary()``, which
#: returns the FIRST one and ignores the rest, so a second external would
#: be a boundary that silently does nothing (rule 7).
_SINGLE_INSTANCE = {
    BoundaryType.EXTERNAL: (
        "A model has exactly one External boundary; replace the existing "
        "one instead of adding a second."),
    BoundaryType.WATER_TABLE: (
        "Only one Water Table is allowed; delete or edit the existing one."),
    BoundaryType.TENSION_CRACK: (
        "Only one Tension Crack boundary is allowed; delete the existing one "
        "to add a new one."),
    BoundaryType.DRAWDOWN: (
        "Only one Drawdown Line is allowed; delete or edit the existing one."),
}


def boundary_refusal(project, btype: BoundaryType) -> Optional[Refusal]:
    """Why a new boundary of type ``btype`` cannot be added, or None.

    The same answer the interface gives by greying its drawing actions
    (``MainWindow.refresh_action_availability``). Two kinds of refusal:

    * ``single_instance`` — the model already holds the one it may hold;
    * ``requires_rapid_drawdown`` / ``requires_block_search`` — the
      boundary would be read by nothing under the current settings. A
      drawdown line is only consumed by a rapid-drawdown analysis and a
      Block Search object only by the Block Search, so adding one
      otherwise is a control that moves no number.

    For a drawdown line the settings question is asked FIRST, which is
    the order the interface's tooltip has always reported them in.
    """
    btype = BoundaryType(btype) if not isinstance(btype, BoundaryType) \
        else btype
    settings = project.settings
    if btype == BoundaryType.DRAWDOWN and not getattr(
            settings.groundwater, "rapid_drawdown", False):
        return Refusal(
            "requires_rapid_drawdown",
            "A Drawdown Line is only read by a rapid drawdown analysis; "
            "enable it first (groundwater advanced option "
            "'rapid_drawdown').")
    if btype == BoundaryType.BLOCK_SEARCH_OBJECT and (
            settings.search.search_method != "block"):
        return Refusal(
            "requires_block_search",
            "A Block Search object is only read by the Block Search; set "
            "search.surface_type='non_circular' and "
            "search.search_method='block' first.")
    message = _SINGLE_INSTANCE.get(btype)
    if message is not None and any(b.btype == btype
                                   for b in project.boundaries):
        return Refusal("single_instance", message)
    return None


# ----------------------------------------------------------------------
def assign_water_surface(project, surface_id, picked: Iterable[str],
                         cleared: Iterable[str] = ()) -> None:
    """Point materials at a water surface, and set their pore-pressure model.

    Moved here from ``MainWindow.apply_water_surface_assignment`` in
    v0.1.194; the history below is that method's, kept with the code it
    explains.

    v0.1.97 — IT ALSO SETS ``Material.pore_pressure``, and that is the
    whole reason this function exists. Until then the assignment wrote
    ``water_surface_id`` alone, while ``pore_pressure_at`` returns 0.0
    out of ``if ppt == PorePressureType.NONE`` BEFORE it ever reads that
    field. So ticking a material moved nothing: measured on the Ej_2
    piezometric model, u at (0, 10) stayed at 0.000 kPa with the id
    written, and became 196.200 kPa once the model was set too. A control
    that does not change the number is worse than no control, because the
    user believes the analysis respects it.

    Clearing restores ``NONE``, but only for a material that was actually
    using a water surface: one on Ru, a constant or a finite-element field
    is left alone, since its pore-pressure model was never this
    assignment's to set.
    """
    from ..materials import PorePressureType

    surface = next((b for b in project.boundaries if b.id == surface_id),
                   None)
    model = (PorePressureType.WATER_TABLE
             if surface is not None
             and surface.btype == BoundaryType.WATER_TABLE
             else PorePressureType.PIEZO_LINE)
    picked, cleared = set(picked), set(cleared)
    surface_models = (PorePressureType.WATER_TABLE,
                      PorePressureType.PIEZO_LINE)
    for m in project.materials:
        if m.id in picked:
            m.water_surface_id = surface_id
            m.pore_pressure = model
        elif m.id in cleared:
            m.water_surface_id = None
            if m.pore_pressure in surface_models:
                m.pore_pressure = PorePressureType.NONE
    project._notify("materials_changed")


def water_surface_model(project, surface_id):
    """The pore-pressure model a material pointed at ``surface_id`` gets.

    The same choice :func:`assign_water_surface` makes, exposed so a caller
    that sets the two fields itself cannot pick the other one.
    """
    from ..materials import PorePressureType

    surface = next((b for b in project.boundaries if b.id == surface_id),
                   None)
    if surface is not None and surface.btype == BoundaryType.WATER_TABLE:
        return PorePressureType.WATER_TABLE
    return PorePressureType.PIEZO_LINE


# ----------------------------------------------------------------------
def compute_blockers(project) -> list[Refusal]:
    """The model-level reasons a run cannot start, in the order checked.

    Moved from ``MainWindow.act_compute`` in v0.1.194. These are the two
    checks that are about the MODEL being empty; the checks about the
    SETTINGS live in ``ogr_slip2d.analysis_runner.check_analysis_settings``,
    which this package cannot import. The interface asks the first one
    before the settings and the second one after them, and keeps doing so:
    the codes exist so it can.

    ``no_boundaries`` asks for ANY boundary, exactly as the interface
    always has, not for an External one. A model with boundaries but no
    External reaches the search and finds nothing; whether that should be
    refused up front is a separate decision, reported and not taken here.
    """
    out: list[Refusal] = []
    if not project.boundaries:
        out.append(Refusal(
            "no_boundaries",
            "No model to compute. Add an external boundary first."))
    if not project.materials:
        out.append(Refusal("no_materials", "No materials defined."))
    return out

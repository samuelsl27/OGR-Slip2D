# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The engine's messages in the reader's language (v0.1.333, D314).

The engine writes each per-surface message as an English sentence plus a
stable code with its values (``ogr_core.messages``,
``ogr_slip2d.messages``). This module turns the code back into a sentence
through ``tr()``: the English template is the key of the translation, so
there is one entry per code in ``ogr_gui/i18n``. A message without a code,
or whose code this version does not know, is shown as the engine wrote it.

It also gives the label of a message's GROUP: the same sentence with the
values that vary from surface to surface replaced by "…". The
interpretation window groups the invalid surfaces by that label, so one
condition is one group however many slice counts it was found at.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import functools

from ogr_core.messages import METHOD_NOTE, parts, render

from .i18n import tr


_CATALOGUE: dict = {}


def _catalogue() -> dict:
    """The engine's codes, the DXF import's (v0.1.334), the analysis notes'
    and the project rules' (v0.1.347), the notes about one method's surface
    (v0.1.348), the search's (v0.1.349), the refusals of the settings
    (v0.1.350) and of the strength models (v0.1.351), the seepage solver's,
    the transient's, the back analysis', the sweep's and the Hoek-Brown
    calculator's (v0.1.352), the statistical runs', the design standard's
    and the strength models' factoring (v0.1.353), the DXF export's
    (v0.1.354), and the geometry editions', the strong-motion reader's and
    the undo step names (v0.1.434), in one table: the codes do not collide,
    each family having its own prefix."""
    if not _CATALOGUE:
        from ogr_core.dxf.messages import EXPORT_MESSAGES
        from ogr_core.dxf.messages import MESSAGES as DXF
        from ogr_core.materials.messages import (CALCULATOR_NOTES,
                                                 FACTORING_NOTES)
        from ogr_core.project.design_messages import DESIGN_NOTES
        from ogr_core.messages import CORE_MESSAGES, NOTE_FRAMES
        from ogr_core.project.messages import (REFUSALS, RULES,
                                               STRENGTH_REFUSALS)
        from ogr_core.statistics.messages import SWEEP_NOTES
        from ogr_fem2d.messages import SEEPAGE_NOTES
        from ogr_slip2d.messages import MESSAGES as LEM
        from ogr_slip2d.method_note_messages import METHOD_NOTES
        from ogr_slip2d.note_messages import NOTES
        # v0.1.430 (D405) -- what the reported value is under a standard
        from ogr_slip2d.reported import REPORTED_NOTES
        from ogr_slip2d.run_messages import RUN_NOTES
        from ogr_slip2d.stat_messages import STAT_NOTES
        from ogr_slip2d.search_note_messages import SEARCH_NOTES
        from ogr_slip2d.setting_messages import SETTING_NOTES
        # v0.1.434 (D412)
        from ogr_core.geometry.messages import GEOMETRY_MESSAGES
        from ogr_core.loads.messages import SEISMIC_NOTES
        from ogr_core.project.step_names import STEP_NAMES
        # v0.1.437 (D414) -- the readers of a .ogr and Import Properties
        from ogr_core.file_messages import FILE_MESSAGES
        from ogr_core.project.messages import IMPORT_NOTES
        for table in (CORE_MESSAGES, NOTE_FRAMES, LEM, DXF, NOTES,
                      RULES, METHOD_NOTES, SEARCH_NOTES, REFUSALS,
                      SETTING_NOTES, STRENGTH_REFUSALS, SEEPAGE_NOTES,
                      RUN_NOTES, SWEEP_NOTES, CALCULATOR_NOTES,
                      STAT_NOTES, DESIGN_NOTES, FACTORING_NOTES,
                      EXPORT_MESSAGES, REPORTED_NOTES, GEOMETRY_MESSAGES,
                      SEISMIC_NOTES, STEP_NAMES, FILE_MESSAGES,
                      IMPORT_NOTES):
            _CATALOGUE.update(table)
    return _CATALOGUE


def _show(kind: str, value, project=None):
    """How a value of a declared kind reads: a method by its name, a name the
    program shows through its translation, a strength model by its name.

    v0.1.434 (D412) -- ``project`` names what only the project knows: a
    random variable by its key or its stored label, a material the agent
    named by its id. Without it those values read as they are. It is passed,
    never kept: a module that remembered the window's project would be state
    a test leaks, and with two windows the last one would win."""
    if kind == "method_id":
        from .labels import method_name
        return method_name(value)
    if kind == "method_list":
        # v0.1.347 (D335) -- the ids ", "-joined, as the engine wrote them
        from .labels import method_name
        return ", ".join(method_name(m) for m in str(value).split(", ") if m)
    if kind == "label":
        return tr(str(value))
    if kind == "groundwater_method":
        # v0.1.350 (D335) -- a groundwater method, by its value
        from ogr_core.project.settings import GroundwaterMethod
        from .labels import groundwater_method_label
        try:
            value = GroundwaterMethod(value)
        except ValueError:
            pass
        return groundwater_method_label(value)
    if kind == "force_orientation":
        # v0.1.348 (D335) -- a support's force orientation, by its value:
        # the table is keyed by the member, and a value this build does not
        # know shows as it is
        from ogr_core.support import ForceOrientation
        from .labels import force_orientation_label
        try:
            value = ForceOrientation(value)
        except ValueError:
            pass
        return force_orientation_label(value)
    if kind == "strength_model":
        from ogr_core.materials import REGISTRY
        return tr(REGISTRY.get(value).DISPLAY_NAME)
    # v0.1.433 (D411) -- identifiers the Spanish printed as they are stored
    # («'non_circular'», «'grid'», «'circle'», «b_bar, corps_2»)
    from . import labels as L
    if kind == "search_method":
        return L.search_method_label(value)
    if kind == "surface_type":
        return L.surface_type_label(value)
    if kind == "surface_kind":
        return L.surface_kind_label(value)
    if kind == "surface_noun":
        return L.surface_noun_label(value)
    if kind == "drawdown_method":
        return L.drawdown_procedure_label(value)
    # the names are joined by «; »: one of them («Duncan, Wright, Wong 3
    # Stage (1990)») has commas, and the list of four read as six (review
    # of 0.1.433). The engine joins the identifiers by «, »
    if kind == "drawdown_method_list":
        return "; ".join(L.drawdown_procedure_label(m)
                         for m in str(value).split(", ") if m)
    if kind == "technique_list":
        return "; ".join(L.optimize_technique_label(m)
                         for m in str(value).split(", ") if m)
    # v0.1.434 (D412)
    if kind == "design_standard":
        return L.design_standard_label(value)
    if kind == "boundary_edit_op":
        return L.boundary_edit_op_label(value)
    if kind == "support_names":
        return L.support_names_label(project, value)
    # v0.1.436 (D415) -- the names the program gives: a support class, a
    # property set, a strong-motion record, a load
    if kind == "support_class":
        return L.support_class_label(value)
    if kind == "set_names":
        return L.set_names_label(project, value)
    if kind == "record_name":
        return L.record_name_label(project, value)
    if kind == "load_names":
        return L.load_names_label(project, value)
    if kind == "line_load_name":
        return L.line_load_name_label(project, value)
    if kind == "support_failures":
        return L.support_failures_label(project, value)
    # v0.1.437 (D414) -- what a reader refused: the models this build has,
    # the parameters a model takes, and what an enumeration's value is of
    if kind == "strength_model_list":
        return L.strength_model_list_label(value)
    if kind == "parameter_list":
        return L.parameter_list_label(value)
    if kind == "enum_name":
        return L.enum_name_label(value)
    if kind == "file_value":
        return L.file_value_label(value)
    if kind == "json_shape":
        return L.json_shape_label(value)
    if kind == "variable_key":
        return L.variable_key_label(project, value)
    if kind == "variable_keys":
        return L.variable_keys_label(project, value)
    if kind == "variable_label":
        return L.variable_label_by_stored(project, value)
    if kind == "material_ref":
        return L.material_ref_label(project, value)
    return value


def text(code: str, args, english: str, *, project=None) -> str:
    """The message ``code`` with ``args`` in the reader's language, or
    ``english`` (the sentence the engine wrote) when there is no code.
    ``project`` names what only it knows (``_show``, v0.1.434)."""
    return render(_catalogue(), code, args, english, translate=tr,
                  show=functools.partial(_show, project=project))


def label(code: str, args, english: str) -> str:
    """The label of the group the message belongs to."""
    return render(_catalogue(), code, args, english, translate=tr,
                  show=_show, elide=True)


def _parts(res):
    """``(code, args, sentence)`` of why ``res`` was rejected: its failure,
    else its admissibility note, else None (the order the core's
    ``interpretation.invalid_reason`` reads them in)."""
    sentence = getattr(res, "error_message", None) or ""
    if sentence:
        return (getattr(res, "message_code", "") or "",
                getattr(res, "message_args", None) or {}, sentence)
    sentence = getattr(res, "admissibility_note", None) or ""
    if sentence:
        return (getattr(res, "note_code", "") or "",
                getattr(res, "note_args", None) or {}, sentence)
    return None


def invalid_text(res) -> str:
    """Why ``res`` was rejected, in full and in the reader's language."""
    parts = _parts(res)
    if parts is None:
        return tr("did not converge")
    return text(*parts)


def problem_text(problem: dict) -> str:
    """A DXF import problem (a sanitiser record) in the reader's language
    (v0.1.334, D314)."""
    return text(problem.get("code", "") or "", problem.get("args"),
                problem.get("message", "") or "")


def preview_error_text(pv) -> str:
    """Why a DXF import preview failed, in the reader's language, or the
    empty string when it did not."""
    return text(getattr(pv, "error_code", "") or "",
                getattr(pv, "error_args", None), getattr(pv, "error", "")
                or "")


def invalid_label(res) -> str:
    """The group ``res`` is rejected under: :func:`invalid_text` with the
    values that vary between surfaces left out."""
    parts = _parts(res)
    if parts is None:
        return tr("did not converge")
    return label(*parts)


def surface_note(search_result, res) -> tuple:
    """``(text, tooltip)`` of the Note column of a table of surfaces, for
    the surface ``res`` of ``search_result`` (v0.1.443, D401).

    Whose the surface is when the user drew it, and why it cannot be the
    critical one when a check rejected it, the first in front of the second.
    Empty for a surface of the search that passed, which is every row of a
    run without surfaces of the user: the column reads as it always did.
    The one place the tables ask it (the results panel, Interpret's
    Surfaces and, when it has the column, its Result Table), so they cannot
    say different things of one surface.
    """
    from ogr_slip2d.search import is_user_surface_of

    rejected = not getattr(res, "admissible", True)
    if is_user_surface_of(search_result, res):
        if rejected:
            return (tr("Defined by the user: {0}").format(invalid_label(res)),
                    invalid_text(res))
        return tr("Defined by the user"), ""
    if rejected:
        return invalid_label(res), invalid_text(res)
    return "", ""


# ----------------------------------------------------------------------
# The analysis notes (v0.1.347, D335)
# ----------------------------------------------------------------------
def note_text(note, *, project=None) -> str:
    """A note -- a message the engine or the core wrote, with its code or
    without one -- in the reader's language: through its code when it has
    one, through its translation when it is a fixed sentence with an entry,
    and as it was written otherwise. ``project`` as in :func:`text`."""
    code, args, english = parts(note)
    if code:
        return text(code, args, english, project=project)
    return tr(english)


def error_text(exc, *, project=None) -> str:
    """What an exception says, in the reader's language (v0.1.434, D412).

    The core raises with a :class:`~ogr_core.messages.Coded` as the argument
    (``str(exc)`` is its English, what the agent reads); an exception class
    may carry ``code`` and ``values`` instead (``DxfReadError``); anything
    else -- the operating system's text, Python's -- is shown through its
    translation when it has one, and as it is otherwise. A caller that
    catches more than the core's own refusals puts this inside a translated
    frame (``tr("Could not save project:\n{0}")``)."""
    said = exc.args[0] if getattr(exc, "args", None) else ""
    if getattr(said, "code", ""):
        return note_text(said, project=project)
    code = getattr(exc, "code", "")
    values = getattr(exc, "values", None)
    if isinstance(code, str) and code and isinstance(values, dict):
        return text(code, values, str(exc), project=project)
    return tr(str(exc))


def note_group(note, *, project=None) -> tuple:
    """``(group, sentence)`` of a note for the Analysis Notes panel.

    A note about one method's reported surface is grouped under the method,
    shown by its name; a note about the model has no group (None). A note
    without a code keeps the rule the panel always had: an identifier
    before ``": "`` is the method's. ``project`` as in :func:`text`."""
    code, args, english = parts(note)
    if code == METHOD_NOTE:
        inner = args.get("note") or {}
        sentence = (text(inner.get("code", ""), inner.get("args"),
                         inner.get("text", ""), project=project)
                    if inner.get("code") else tr(inner.get("text", "")))
        return _show("method_id", args.get("method_id", "")), sentence
    if code:
        return None, text(code, args, english, project=project)
    head, sep, tail = english.partition(": ")
    if sep and head and " " not in head:
        return head, tr(tail)
    return None, tr(english)


def note_line(note, *, project=None) -> str:
    """A note on one line, its method first when it has one: what the status
    bar shows and what *Copy all* copies."""
    group, sentence = note_group(note, project=project)
    return sentence if group is None else "%s: %s" % (group, sentence)

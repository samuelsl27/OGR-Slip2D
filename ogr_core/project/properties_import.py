# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Bring materials and support types across from another project.

Moved out of ``MainWindow._import_properties`` in v0.1.196 (spec 008, F2),
so an agent imports exactly what the interface imports, and fixed on the way
— every fix below is something the interface did silently:

* **Fresh ids for materials.** The clone kept the SOURCE material's id, so
  importing from a project that shares an ancestor with this one could leave
  two materials answering to one id, and ``material_by_id`` — which region
  resolution uses — returns the first.
* **Foreign references cleared.** A material pointing at the other project's
  water table (``water_surface_id``) or anisotropic surface arrived pointing
  at a boundary that does not exist here, which the pore-pressure code reads
  as "no water": a material imported "with its water" was silently dry. The
  reference is dropped, its pore-pressure model reset when it depended on
  it, and the caller is told.
* **The material limit is respected** (``settings.max_materials``), which
  the direct append skipped.
* **Unique names compare without case**, as the operations layer does, so
  "Clay" and "clay" are not two materials an agent can confuse.
* **Generalized Anisotropic links** (v0.1.228) point at a material of THIS
  project: the copy imported alongside or, failing that, the material of
  the same name; otherwise the range keeps its strength, unlinked, and the
  caller is told.

Support TYPES are imported, not placed supports; each gets a fresh id
(v0.1.149).

v0.1.439 (D421) -- and a name the model already has, numbered: a support
type as a material always was («Type 1 (2)»), by one rule
(``ogr_core.naming.numbered_name``, the comparison ``find_type`` finds a set
by). Until this version a set kept the name it brought, while the status
bar said duplicated names were numbered, and the agent could no longer find
either of two sets of one name.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

# v0.1.437 (D414) -- the notes with their codes: the window says them
from .messages import (IMPORT_ANISOTROPIC_DROPPED, IMPORT_LINK_DROPPED,
                       IMPORT_LINK_RENAMED, IMPORT_MAX_MATERIALS,
                       IMPORT_WATER_DROPPED, import_child, import_note)
from ..naming import name_key, numbered_name

import copy
from uuid import uuid4


def set_label(st) -> str:
    """The name a support set is known by: the one it was given, else its
    class's (the label ``find_type`` compares)."""
    return getattr(st, "_display_name", None) or st.DISPLAY_NAME


def _relink_generalized(project, source, imported: dict, notes: list):
    """Point the imported Generalized Anisotropic ranges at materials of
    THIS project (v0.1.228, D218b); see ``import_properties``."""
    from ..materials.builtin_models import GeneralizedAnisotropic
    from .design_factors import resolve_generalized_links

    by_src = {m.id: m for m in getattr(source, "materials", [])}
    new_ids = {c.id for c in imported.values()}
    by_name = {m.name.strip().lower(): m for m in project.materials
               if m.id not in new_ids}
    for clone in imported.values():
        if not isinstance(clone.strength, GeneralizedAnisotropic):
            continue
        # New rule dicts, never edited in place: the clone came through
        # ``to_dict``, which hands out the SOURCE's rule dicts, so an edit in
        # place would relink the other project's material as well.
        # v0.1.248 (D231a) -- every child: the ranges, the base and the
        # joints.
        new_children = {}
        for key, rule in clone.strength.children_items():
            # v0.1.437 (D414) -- with its code: «range 2», «the base»
            who = import_child(key)
            link = rule.get("material_id") if isinstance(rule, dict) else None
            if not link:
                continue
            rule = copy.deepcopy(rule)
            new_children[key] = rule
            here = imported.get(link)
            src = by_src.get(link)
            by_name_here = here is None and src is not None
            if by_name_here:
                here = by_name.get(src.name.strip().lower())
            if here is None or here is clone or isinstance(
                    here.strength, GeneralizedAnisotropic):
                rule.pop("material_id", None)
                notes.append(import_note(IMPORT_LINK_DROPPED,
                                         name=clone.name, who=who))
                continue
            rule["material_id"] = here.id
            if by_name_here:
                notes.append(import_note(IMPORT_LINK_RENAMED,
                                         name=clone.name, who=who,
                                         here=here.name))
        clone.strength = clone.strength.with_children(new_children)
    resolve_generalized_links(project.materials)


def import_properties(project, source, *, materials: bool = True,
                      support_types: bool = True, names=None,
                      renamed: list = None) -> dict:
    """Copy materials and/or support types from ``source`` into ``project``.

    ``names`` restricts the copy to those names (case-insensitive). Returns
    ``{"materials": [...], "support_types": [...], "skipped": [...],
    "notes": [...]}`` with the names as they were stored here. A name the
    model already has is numbered, for a material and for a support type
    alike (:func:`ogr_core.naming.numbered_name`); ``renamed``, when given,
    receives a ``(name brought, name stored)`` pair for each one numbered
    (the window counts them; the agent reads the names).
    """
    from ..materials import Material, PorePressureType

    wanted = ({name_key(n) for n in names} if names is not None else None)
    out = {"materials": [], "support_types": [], "skipped": [], "notes": []}
    numbered = renamed if renamed is not None else []

    imported = {}
    if materials:
        taken = [m.name for m in project.materials]
        for m in source.materials:
            if wanted is not None and name_key(m.name) not in wanted:
                continue
            if len(project.materials) >= project.settings.max_materials:
                out["skipped"].append(m.name)
                continue
            clone = Material.from_dict(m.to_dict())
            clone.id = str(uuid4())
            clone.name = numbered_name(clone.name, taken)
            taken.append(clone.name)
            if clone.name != m.name:
                numbered.append((m.name, clone.name))
            if clone.water_surface_id:
                clone.water_surface_id = None
                if clone.pore_pressure in (PorePressureType.WATER_TABLE,
                                           PorePressureType.PIEZO_LINE):
                    clone.pore_pressure = PorePressureType.NONE
                out["notes"].append(import_note(IMPORT_WATER_DROPPED,
                                                name=clone.name))
            if clone.anisotropic_surface_id:
                clone.anisotropic_surface_id = None
                out["notes"].append(import_note(IMPORT_ANISOTROPIC_DROPPED,
                                                name=clone.name))
            project.materials.append(clone)
            out["materials"].append(clone.name)
            imported[m.id] = clone
        # v0.1.228 (D218b) — a Generalized Anisotropic range that linked a
        # material of the other project links, here, the copy imported with
        # it or else the material of the same name; with neither, it keeps
        # the strength it had and loses the link, and a note says so.
        _relink_generalized(project, source, imported, out["notes"])
        if out["skipped"]:
            out["notes"].append(import_note(
                IMPORT_MAX_MATERIALS, n=len(out["skipped"]),
                limit=project.settings.max_materials))
        if out["materials"]:
            project._notify("material_added")

    if support_types:
        taken = [set_label(x) for x in project.support_types]
        for st in getattr(source, "support_types", []) or []:
            label = set_label(st)
            if wanted is not None and name_key(label) not in wanted:
                continue
            clone = copy.deepcopy(st)
            clone.id = str(uuid4())
            # v0.1.439 (D421) -- numbered as a material is; a set with no
            # clash keeps what it had, its class's name included, so a model
            # saved without one reads as it did
            stored = numbered_name(label, taken)
            if stored != label:
                clone._display_name = stored
                numbered.append((label, stored))
            taken.append(stored)
            project.support_types.append(clone)
            out["support_types"].append(stored)
        if out["support_types"]:
            project._notify("support_types_changed")
    project.is_dirty = True
    return out

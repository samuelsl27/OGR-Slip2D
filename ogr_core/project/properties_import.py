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

Support TYPES are imported, not placed supports; each gets a fresh id
(v0.1.149).

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
from uuid import uuid4


def _unique(name: str, taken: set) -> str:
    candidate, i = name, 2
    while candidate.strip().lower() in taken:
        candidate = f"{name} ({i})"
        i += 1
    taken.add(candidate.strip().lower())
    return candidate


def import_properties(project, source, *, materials: bool = True,
                      support_types: bool = True, names=None) -> dict:
    """Copy materials and/or support types from ``source`` into ``project``.

    ``names`` restricts the copy to those names (case-insensitive). Returns
    ``{"materials": [...], "support_types": [...], "skipped": [...],
    "notes": [...]}`` with the names as they were stored here.
    """
    from ..materials import Material, PorePressureType

    wanted = ({str(n).strip().lower() for n in names}
              if names is not None else None)
    out = {"materials": [], "support_types": [], "skipped": [], "notes": []}

    if materials:
        taken = {m.name.strip().lower() for m in project.materials}
        for m in source.materials:
            if wanted is not None and m.name.strip().lower() not in wanted:
                continue
            if len(project.materials) >= project.settings.max_materials:
                out["skipped"].append(m.name)
                continue
            clone = Material.from_dict(m.to_dict())
            clone.id = str(uuid4())
            clone.name = _unique(clone.name, taken)
            if clone.water_surface_id:
                clone.water_surface_id = None
                if clone.pore_pressure in (PorePressureType.WATER_TABLE,
                                           PorePressureType.PIEZO_LINE):
                    clone.pore_pressure = PorePressureType.NONE
                out["notes"].append(
                    f"{clone.name!r} used a water surface of the other "
                    f"project; assign one of this model to it.")
            if clone.anisotropic_surface_id:
                clone.anisotropic_surface_id = None
                out["notes"].append(
                    f"{clone.name!r} lost its anisotropic surface, which "
                    f"belonged to the other project.")
            project.materials.append(clone)
            out["materials"].append(clone.name)
        if out["skipped"]:
            out["notes"].append(
                f"{len(out['skipped'])} material(s) not imported: the model "
                f"already has the maximum of "
                f"{project.settings.max_materials}.")
        if out["materials"]:
            project._notify("material_added")

    if support_types:
        for st in getattr(source, "support_types", []) or []:
            label = getattr(st, "_display_name", None) or st.DISPLAY_NAME
            if wanted is not None and label.strip().lower() not in wanted:
                continue
            clone = copy.deepcopy(st)
            clone.id = str(uuid4())
            project.support_types.append(clone)
            out["support_types"].append(label)
        if out["support_types"]:
            project._notify("support_types_changed")
    project.is_dirty = True
    return out

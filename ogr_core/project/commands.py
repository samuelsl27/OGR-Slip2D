# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Command pattern for Undo/Redo.

Every mutation of a :class:`Project` done from the GUI should go through
a :class:`Command`. The :class:`CommandStack` holds the history and
provides ``undo()`` / ``redo()``.

Benefits:
    - unlimited-depth undo/redo
    - macro commands (grouping several primitive commands)
    - easy debugging: commands have human-readable ``description``
    - the CLI bypasses the stack (it does not need undo)

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Optional

from ogr_core.geometry import Boundary
from ogr_core.loads import DistributedLoad, LineLoad
from ogr_core.materials import Material
from ogr_core.project import Project
from ogr_core.support import SupportInstance


# ----------------------------------------------------------------------
class Command(ABC):
    """A reversible mutation of a Project."""

    description: str = ""

    @abstractmethod
    def execute(self, project: Project) -> None: ...

    @abstractmethod
    def undo(self, project: Project) -> None: ...


# ----------------------------------------------------------------------
@dataclass
class AddBoundaryCommand(Command):
    boundary: Boundary
    description: str = "Add Boundary"

    def execute(self, project: Project) -> None:
        project.add_boundary(self.boundary)

    def undo(self, project: Project) -> None:
        project.remove_boundary(self.boundary.id)


@dataclass
class RemoveBoundaryCommand(Command):
    boundary: Boundary
    description: str = "Remove Boundary"

    def execute(self, project: Project) -> None:
        project.remove_boundary(self.boundary.id)

    def undo(self, project: Project) -> None:
        project.add_boundary(self.boundary)


@dataclass
class AddMaterialCommand(Command):
    material: Material
    description: str = "Add Material"

    def execute(self, project: Project) -> None:
        project.add_material(self.material)

    def undo(self, project: Project) -> None:
        project.materials = [m for m in project.materials if m.id != self.material.id]
        project._notify("material_removed")


@dataclass
class AddSupportCommand(Command):
    support: SupportInstance
    description: str = "Add Support"

    def execute(self, project: Project) -> None:
        project.add_support(self.support)

    def undo(self, project: Project) -> None:
        project.supports = [s for s in project.supports if s.id != self.support.id]
        project._notify("support_removed")


@dataclass
class AddDistributedLoadCommand(Command):
    load: DistributedLoad
    description: str = "Add Distributed Load"

    def execute(self, project: Project) -> None:
        project.add_distributed_load(self.load)

    def undo(self, project: Project) -> None:
        project.distributed_loads = [
            l for l in project.distributed_loads if l.id != self.load.id
        ]
        project._notify("load_removed")


@dataclass
class AddLineLoadCommand(Command):
    load: LineLoad
    description: str = "Add Line Load"

    def execute(self, project: Project) -> None:
        project.add_line_load(self.load)

    def undo(self, project: Project) -> None:
        project.line_loads = [l for l in project.line_loads if l.id != self.load.id]
        project._notify("load_removed")


# ----------------------------------------------------------------------
@dataclass
class ReplaceBoundaryCommand(Command):
    """Replace an existing boundary by index with a new boundary.

    Used for all transformations (translate, rotate, scale, offset,
    convert, vertex edits) — they take the current boundary, compute a
    new one, and swap them.
    """

    index: int
    new_boundary: Boundary
    _prev: Optional[Boundary] = None
    description: str = "Edit Boundary"

    def execute(self, project: Project) -> None:
        if 0 <= self.index < len(project.boundaries):
            self._prev = project.boundaries[self.index]
            project.boundaries[self.index] = self.new_boundary
            project._notify("boundary_replaced")

    def undo(self, project: Project) -> None:
        if self._prev is not None and 0 <= self.index < len(project.boundaries):
            project.boundaries[self.index] = self._prev
            project._notify("boundary_replaced")


@dataclass
class PaintRegionCommand(Command):
    """v0.1.6 — Record a user click painting a material onto a region.

    Stores the click (x, y) and material_id in project.region_assignments.
    Undo removes exactly this assignment entry (by position match);
    if a previous assignment at the same point was overwritten, the
    previous one is restored.
    """
    x: float
    y: float
    material_id: str
    # Filled during execute: (previous_material_id, new_entry_index)
    _prev_state: object = None

    def description(self) -> str:
        return f"Paint material at ({self.x:.2f}, {self.y:.2f})"

    def execute(self, project) -> None:
        # If there is already an entry at this exact point, store its
        # previous material_id so undo can restore it.
        self._prev_state = None
        for i, a in enumerate(project.region_assignments):
            if abs(a["x"] - self.x) < 1e-6 and abs(a["y"] - self.y) < 1e-6:
                self._prev_state = ("replace", i, a["material_id"])
                a["material_id"] = self.material_id
                project._notify("assignments_changed")
                return
        # Check it lands inside some region; if not, no-op
        ok = project.assign_material_at(self.x, self.y, self.material_id)
        if ok:
            self._prev_state = ("append", None, None)

    def undo(self, project) -> None:
        if self._prev_state is None:
            return
        kind = self._prev_state[0]
        if kind == "replace":
            _, idx, prev_mid = self._prev_state
            if 0 <= idx < len(project.region_assignments):
                project.region_assignments[idx]["material_id"] = prev_mid
        elif kind == "append":
            # Remove our added entry (the last one matching this click)
            for i in range(len(project.region_assignments) - 1, -1, -1):
                a = project.region_assignments[i]
                if (abs(a["x"] - self.x) < 1e-6
                        and abs(a["y"] - self.y) < 1e-6
                        and a["material_id"] == self.material_id):
                    del project.region_assignments[i]
                    break
        project._notify("assignments_changed")


@dataclass
class AssignMaterialCommand(Command):
    """Assign a material to an existing material boundary."""

    index: int
    material_id: Optional[str]
    _prev_material_id: Optional[str] = None
    description: str = "Assign Material"

    def execute(self, project: Project) -> None:
        if 0 <= self.index < len(project.boundaries):
            b = project.boundaries[self.index]
            self._prev_material_id = b.material_id
            b.material_id = self.material_id
            project._notify("boundary_material_changed")

    def undo(self, project: Project) -> None:
        if 0 <= self.index < len(project.boundaries):
            project.boundaries[self.index].material_id = self._prev_material_id
            project._notify("boundary_material_changed")


@dataclass
class MacroCommand(Command):
    """Group of commands treated as a single undo unit."""

    children: list[Command] = field(default_factory=list)
    description: str = "Macro"

    def execute(self, project: Project) -> None:
        for c in self.children:
            c.execute(project)

    def undo(self, project: Project) -> None:
        for c in reversed(self.children):
            c.undo(project)


# ----------------------------------------------------------------------
class CommandStack:
    """LIFO stacks for undo/redo with optional depth limit."""

    def __init__(self, max_depth: int = 200) -> None:
        self.max_depth = max_depth
        self._undo: list[Command] = []
        self._redo: list[Command] = []
        self._listeners: list[Callable[[], None]] = []

    # ------------------------------------------------------------------
    def do(self, project: Project, command: Command) -> None:
        command.execute(project)
        self._undo.append(command)
        if len(self._undo) > self.max_depth:
            self._undo.pop(0)
        self._redo.clear()
        self._emit()

    def undo(self, project: Project) -> Optional[Command]:
        if not self._undo:
            return None
        c = self._undo.pop()
        c.undo(project)
        self._redo.append(c)
        self._emit()
        return c

    def redo(self, project: Project) -> Optional[Command]:
        if not self._redo:
            return None
        c = self._redo.pop()
        c.execute(project)
        self._undo.append(c)
        self._emit()
        return c

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
        self._emit()

    # ------------------------------------------------------------------
    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def next_undo_description(self) -> str:
        return self._undo[-1].description if self._undo else ""

    @property
    def next_redo_description(self) -> str:
        return self._redo[-1].description if self._redo else ""

    # ------------------------------------------------------------------
    def on_changed(self, cb: Callable[[], None]) -> None:
        self._listeners.append(cb)

    def _emit(self) -> None:
        for cb in self._listeners:
            try:
                cb()
            except Exception:  # noqa: BLE001
                pass

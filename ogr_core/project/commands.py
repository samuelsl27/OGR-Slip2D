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
    _index: Optional[int] = field(default=None, repr=False, compare=False)

    def execute(self, project: Project) -> None:
        ids = [b.id for b in project.boundaries]
        self._index = (ids.index(self.boundary.id)
                       if self.boundary.id in ids else None)
        project.remove_boundary(self.boundary.id)

    def undo(self, project: Project) -> None:
        # v0.1.203 — back IN ITS PLACE (anomaly A2, reported in v0.1.194).
        # ``add_boundary`` appends, so an undone deletion moved the
        # boundary to the end of the list; the order is not cosmetic (a
        # later edit by index lands elsewhere), and it blocked sharing this
        # stack with an agent's snapshots, which restore the list as it
        # was.
        project.add_boundary(self.boundary)
        last = len(project.boundaries) - 1
        if self._index is not None and self._index < last:
            project.boundaries.insert(self._index,
                                      project.boundaries.pop())
            project._notify("boundary_modified")


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
#: The project attributes a :class:`SnapshotCommand` captures by default.
#: They are the MODEL — what the user edits and what an analysis reads —
#: and every one of them is small next to the three below.
LIGHT_ATTRS: tuple[str, ...] = (
    "name", "settings", "boundaries", "materials", "supports",
    "support_types", "distributed_loads", "line_loads", "seismic",
    "seismic_records", "region_assignments", "tension_crack_properties",
    "water_pressure_grid", "seepage_bcs", "random_variables", "annotations",
    "focus_objects", "user_surfaces",
)

#: Computed or generated state that can weigh megabytes. A snapshot only
#: carries them when the operation says it touches them.
HEAVY_ATTRS: tuple[str, ...] = ("fem_mesh", "seepage_result",
                                "transient_results")


def capture_state(project: Project, attrs=LIGHT_ATTRS) -> dict:
    """Deep copies of ``attrs``, detached from the live project."""
    import copy

    return {a: copy.deepcopy(getattr(project, a)) for a in attrs}


def restore_state(project: Project, state: dict) -> None:
    """Write a :func:`capture_state` result back onto the SAME project.

    Onto the same object, never a replacement: the interface, the canvas
    and an agent's handle all hold a reference to it. Each attribute gets a
    fresh copy so the stored state can be restored again (undo, redo, undo)
    without aliasing what the model now holds. Region and bounding-box
    caches are dropped, because they are keyed by content and a restored
    list is a different list.
    """
    import copy

    for a, value in state.items():
        setattr(project, a, copy.deepcopy(value))
    project.invalidate_regions_cache()
    project._notify("model_restored")


class SnapshotCommand(Command):
    """Undo for any edit, by capturing the state it can touch.

    v0.1.194 (spec 008). The typed commands above cover boundaries and
    painting; loads, supports, materials, settings and everything a script
    can do had no undo at all. This one runs ``mutate(project)`` and keeps
    the listed attributes as they were before and after.

    It is ATOMIC: if ``mutate`` raises, the state is put back before the
    exception propagates, so ``CommandStack.do`` — which only records a
    command whose ``execute`` returned — leaves no trace of a failed edit.

    ``description`` is a plain string, set on the instance; the attribute
    is read as a string by ``CommandStack.next_undo_description`` (see
    :class:`PaintRegionCommand`, where it is a method by mistake).
    """

    def __init__(self, description: str, mutate: Callable[[Project], object],
                 attrs: tuple[str, ...] = LIGHT_ATTRS) -> None:
        self.description = str(description)
        self.attrs = tuple(attrs)
        self._mutate = mutate
        self._before: Optional[dict] = None
        self._after: Optional[dict] = None
        #: What ``mutate`` returned the first time it ran.
        self.result = None
        #: Attributes the last undo or redo left alone because something
        #: else had changed them (v0.1.203, :meth:`_restore_where`).
        self.kept: list = []

    def execute(self, project: Project) -> None:
        if self._after is None:
            self._before = capture_state(project, self.attrs)
            try:
                self.result = self._mutate(project)
            except BaseException:
                restore_state(project, self._before)
                raise
            self._after = capture_state(project, self.attrs)
            self._mutate = None
        else:
            self.kept = self._restore_where(project, self._before,
                                            self._after)

    def undo(self, project: Project) -> None:
        if self._before is not None:
            self.kept = self._restore_where(project, self._after,
                                            self._before)

    def _restore_where(self, project: Project, expect: dict,
                       target: dict) -> list:
        """Restore ``target`` for the attributes still as ``expect``
        left them; return the ones something else changed since.

        v0.1.203 (spec 008, F4). With the window's stack shared with an
        agent, a snapshot is undone after edits that went through no
        command at all — 27 sites of the interface edit the model without
        one (materials, loads, settings...). Restoring every captured
        attribute would silently revert those. An attribute that still
        holds what this command left is put back; one that another hand
        changed since is kept, and named in ``kept``. With nothing in
        between (the usual case) it is exactly the old undo.
        """
        restore, kept = {}, []
        for a in self.attrs:
            now = _state_key({a: getattr(project, a)})
            if now == _state_key({a: expect[a]}):
                restore[a] = target[a]
            else:
                kept.append(a)
        restore_state(project, restore)
        return kept

    @property
    def changed(self) -> bool:
        """Whether the edit changed anything it captured.

        Compared through the serialised form where one exists, because
        deep copies of the same model are equal in content and never equal
        as objects.
        """
        if self._before is None or self._after is None:
            return False
        return _state_key(self._before) != _state_key(self._after)


def _state_key(state: dict):
    """A comparable rendering of a captured state."""
    import json

    def enc(v):
        if hasattr(v, "to_dict"):
            return v.to_dict()
        if hasattr(v, "to_list"):
            return v.to_list()
        if isinstance(v, (list, tuple)):
            return [enc(x) for x in v]
        if hasattr(v, "__dataclass_fields__"):
            from dataclasses import asdict
            return asdict(v)
        return v

    return json.dumps({k: enc(v) for k, v in state.items()},
                      sort_keys=True, default=str)


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
        self.record(command)

    def record(self, command: Command) -> None:
        """Push a command that has ALREADY been executed.

        v0.1.194 — for a caller that has to see what the command did
        before deciding it is worth an undo step: a script that changed
        nothing should not leave an empty entry to undo.
        """
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

    def history(self) -> tuple[list[str], list[str]]:
        """``(undo, redo)`` descriptions, most recent LAST in each list.

        v0.1.194. A description that is not a string — the method
        ``PaintRegionCommand.description``, reported and not changed — is
        called, so the listing reads the same text the user would.
        """
        def text(c):
            d = c.description
            return d() if callable(d) else str(d)

        return [text(c) for c in self._undo], [text(c) for c in self._redo]

    # ------------------------------------------------------------------
    def on_changed(self, cb: Callable[[], None]) -> None:
        self._listeners.append(cb)

    def _emit(self) -> None:
        for cb in self._listeners:
            try:
                cb()
            except Exception:  # noqa: BLE001
                pass

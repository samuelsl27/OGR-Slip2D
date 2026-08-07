# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Tests for project serialization and undo/redo commands."""
from __future__ import annotations

from pathlib import Path

import pytest

from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
from ogr_core.loads import DistributedLoad, LoadOrientation, SeismicLoad
from ogr_core.materials import Material, MohrCoulomb, Undrained
from ogr_core.project import Project
from ogr_core.project.commands import (
    AddBoundaryCommand,
    AddDistributedLoadCommand,
    AddMaterialCommand,
    CommandStack,
    MacroCommand,
)


class TestProjectSerialization:
    def test_empty_project_roundtrip(self, tmp_path):
        p = Project("empty")
        out = tmp_path / "x.ogr"
        p.save(out)
        p2 = Project.load(out)
        assert p2.name == "empty"
        assert p2.file_path == out

    def test_full_project_roundtrip(self, tmp_path):
        p = Project("demo")
        ext = Polyline(
            vertices=[Vertex(0, 0), Vertex(10, 0), Vertex(10, 5), Vertex(0, 5)],
            closed=True,
        )
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.add_material(Material(
            name="clay",
            strength=MohrCoulomb(cohesion=12.0, friction_angle=22.0),
            unit_weight=18.5,
        ))
        p.add_distributed_load(DistributedLoad(
            start=Vertex(2, 5), end=Vertex(8, 5),
            magnitude_1=50.0, orientation=LoadOrientation.VERTICAL,
        ))
        p.seismic = SeismicLoad(kh=0.1, kv=0.0, enabled=True)

        out = tmp_path / "demo.ogr"
        p.save(out)
        p2 = Project.load(out)
        assert len(p2.boundaries) == 1
        assert len(p2.materials) == 1
        assert len(p2.distributed_loads) == 1
        assert p2.seismic.enabled
        assert p2.seismic.kh == 0.1
        assert p2.materials[0].strength.params["cohesion"] == 12.0


class TestCommandStack:
    def test_undo_redo_boundary(self):
        p = Project("t")
        stack = CommandStack()
        b = Boundary(polyline=Polyline(vertices=[Vertex(0, 0), Vertex(1, 1)]),
                     btype=BoundaryType.MATERIAL)
        cmd = AddBoundaryCommand(b)
        stack.do(p, cmd)
        assert len(p.boundaries) == 1
        stack.undo(p)
        assert len(p.boundaries) == 0
        stack.redo(p)
        assert len(p.boundaries) == 1

    def test_can_undo_redo_flags(self):
        p = Project("t")
        stack = CommandStack()
        assert not stack.can_undo
        assert not stack.can_redo
        stack.do(p, AddMaterialCommand(Material(
            name="x", strength=Undrained(cohesion=20))))
        assert stack.can_undo
        assert not stack.can_redo
        stack.undo(p)
        assert not stack.can_undo
        assert stack.can_redo

    def test_do_clears_redo_stack(self):
        p = Project("t")
        stack = CommandStack()
        stack.do(p, AddMaterialCommand(Material(name="a", strength=Undrained(cohesion=20))))
        stack.undo(p)
        assert stack.can_redo
        stack.do(p, AddMaterialCommand(Material(name="b", strength=Undrained(cohesion=30))))
        assert not stack.can_redo

    def test_macro_command(self):
        p = Project("t")
        stack = CommandStack()
        b1 = Boundary(polyline=Polyline(vertices=[Vertex(0, 0), Vertex(1, 1)]),
                      btype=BoundaryType.MATERIAL)
        b2 = Boundary(polyline=Polyline(vertices=[Vertex(0, 0), Vertex(2, 2)]),
                      btype=BoundaryType.MATERIAL)
        macro = MacroCommand(
            children=[AddBoundaryCommand(b1), AddBoundaryCommand(b2)],
            description="Add both",
        )
        stack.do(p, macro)
        assert len(p.boundaries) == 2
        stack.undo(p)
        assert len(p.boundaries) == 0

    def test_max_depth(self):
        stack = CommandStack(max_depth=3)
        p = Project("t")
        for i in range(5):
            stack.do(p, AddMaterialCommand(Material(
                name=f"m{i}", strength=Undrained(cohesion=20))))
        # Only 3 most recent commands retained
        assert len(stack._undo) == 3


class TestProjectObserver:
    def test_listener_notified_on_change(self):
        p = Project("t")
        events: list[str] = []
        p.add_listener(lambda e: events.append(e))
        p.add_material(Material(name="x", strength=Undrained(cohesion=25)))
        assert "material_added" in events
        assert p.is_dirty

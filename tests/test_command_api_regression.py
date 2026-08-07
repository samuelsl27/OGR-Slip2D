# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Regression tests for the command system API.

These catch the v0.1.4 bug where the GUI called `command_stack.execute()`
(which doesn't exist) instead of `command_stack.do()`, causing every
boundary edit to silently fail.
"""
from __future__ import annotations

from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
from ogr_core.project import Project
from ogr_core.project.commands import (
    AddBoundaryCommand,
    CommandStack,
    MacroCommand,
    RemoveBoundaryCommand,
    ReplaceBoundaryCommand,
)


# ----------------------------------------------------------------------
class TestCommandStackAPI:
    """The public CommandStack API must stay stable."""

    def test_do_method_exists(self):
        """CommandStack must expose .do() — NOT .execute()."""
        stack = CommandStack()
        assert hasattr(stack, "do"), "CommandStack must have .do()"
        assert callable(stack.do)

    def test_execute_does_not_exist(self):
        """Guard against typos: .execute() must NOT silently exist."""
        stack = CommandStack()
        assert not hasattr(stack, "execute"), (
            "CommandStack should not have .execute() — use .do() instead. "
            "This test catches the v0.1.4 regression where the GUI was "
            "calling a non-existent method and every edit was lost."
        )

    def test_do_signature_is_project_then_command(self):
        """CommandStack.do(project, command) — order matters."""
        import inspect
        sig = inspect.signature(CommandStack.do)
        params = list(sig.parameters.keys())
        # params[0] is 'self'
        assert params[1] == "project"
        assert params[2] == "command"


# ----------------------------------------------------------------------
class TestEndToEndEditFlow:
    """Verify the exact flow from the GUI: draw External → replace →
    add material → save → reload → everything persists."""

    def _setup_demo(self):
        p = Project("Test")
        ext = Polyline(vertices=[
            Vertex(0, 0), Vertex(50, 0), Vertex(50, 15),
            Vertex(35, 15), Vertex(25, 25), Vertex(0, 25),
        ], closed=True)
        ext.ensure_ccw()
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.add_boundary(Boundary(
            polyline=Polyline(vertices=[Vertex(0, 8), Vertex(50, 8)]),
            btype=BoundaryType.WATER_TABLE,
        ))
        return p

    def test_replace_external_persists(self):
        p = self._setup_demo()
        stack = CommandStack()
        new_pl = Polyline(
            vertices=[Vertex(-5, -5), Vertex(60, -5),
                       Vertex(60, 30), Vertex(-5, 30)],
            closed=True,
        )
        new_pl.ensure_ccw()
        new_ext = Boundary(polyline=new_pl, btype=BoundaryType.EXTERNAL)
        existing_idx = next(
            i for i, b in enumerate(p.boundaries)
            if b.btype == BoundaryType.EXTERNAL
        )
        stack.do(p, ReplaceBoundaryCommand(index=existing_idx, new_boundary=new_ext))
        # External must still be there (replaced, not added)
        externals = [b for b in p.boundaries if b.btype == BoundaryType.EXTERNAL]
        assert len(externals) == 1
        assert len(externals[0].polyline.vertices) == 4

    def test_add_material_boundary_persists_across_save(self):
        import tempfile, os
        p = self._setup_demo()
        stack = CommandStack()
        mat_b = Boundary(
            polyline=Polyline(
                vertices=[Vertex(10, 3), Vertex(40, 7)], closed=False
            ),
            btype=BoundaryType.MATERIAL,
        )
        stack.do(p, AddBoundaryCommand(boundary=mat_b))
        assert len(p.boundaries) == 3

        with tempfile.NamedTemporaryFile(suffix=".ogr", delete=False) as f:
            tmp = f.name
        try:
            p.save(tmp)
            p2 = Project.load(tmp)
        finally:
            os.unlink(tmp)

        assert len(p2.boundaries) == 3
        mats = [b for b in p2.boundaries if b.btype == BoundaryType.MATERIAL]
        assert len(mats) == 1
        assert len(mats[0].polyline.vertices) == 2

    def test_undo_replace_external_restores_original(self):
        p = self._setup_demo()
        original_verts = list(p.external_boundary().polyline.vertices)
        stack = CommandStack()
        new_pl = Polyline(
            vertices=[Vertex(-10, -10), Vertex(60, -10),
                       Vertex(60, 30), Vertex(-10, 30)],
            closed=True,
        )
        new_pl.ensure_ccw()
        new_ext = Boundary(polyline=new_pl, btype=BoundaryType.EXTERNAL)
        stack.do(p, ReplaceBoundaryCommand(index=0, new_boundary=new_ext))
        stack.undo(p)
        # After undo, the original 6-vertex slope is back
        restored = p.external_boundary()
        assert restored is not None
        assert len(restored.polyline.vertices) == len(original_verts)


# ======================================================================
# v0.1.7 — RemoveBoundaryCommand signature regression
# ======================================================================
class TestRemoveBoundaryCommandSignature:
    """v0.1.6 GUI was calling ``RemoveBoundaryCommand(boundary_id=…)``
    but the command takes a ``boundary=`` Boundary object. This was the
    root cause of "Delete Boundary in the Edit menu does nothing"."""

    def test_remove_takes_boundary_keyword(self):
        from ogr_core.project.commands import RemoveBoundaryCommand
        import inspect
        params = list(inspect.signature(RemoveBoundaryCommand).parameters)
        assert "boundary" in params
        assert "boundary_id" not in params, (
            "RemoveBoundaryCommand expects ``boundary``, not "
            "``boundary_id``. Update the GUI caller."
        )

    def test_delete_then_undo_restores(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.project import Project
        from ogr_core.project.commands import (
            CommandStack, RemoveBoundaryCommand,
        )
        p = Project("t")
        ext = Polyline(
            vertices=[Vertex(0,0), Vertex(10,0), Vertex(10,10), Vertex(0,10)],
            closed=True,
        )
        ext.ensure_ccw()
        b = Boundary(polyline=ext, btype=BoundaryType.EXTERNAL)
        p.add_boundary(b)
        stack = CommandStack()
        stack.do(p, RemoveBoundaryCommand(boundary=b))
        assert len(p.boundaries) == 0
        stack.undo(p)
        assert len(p.boundaries) == 1

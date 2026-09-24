# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.203 (spec 008, F4) — the live bridge: an agent drives the window.

Invariants protected
--------------------
**The bridge is only a change of transport.** Every tool reaches its
operation through the bridge with the value given (the forwarding check of
test_mcp_server_v1195, with the bridge client in place of ``call``), and an
error comes back as the same coded error.

**Only the token opens it**, and only on 127.0.0.1.

**The window and the agent share one model and one undo stack.** An
agent's edit changes the window's model, is one step of the window's Undo,
and redraws; ``project_open`` opens in the window, never over unsaved
changes; while the window computes, an edit answers Busy; ``project_save``
after the window opened another file writes THAT file, not the old one.

**What sharing the stack needed** (three defects fixed in this version):

* ``RemoveBoundaryCommand.undo`` put the boundary back at the END (anomaly
  A2 of v0.1.194);
* undoing a snapshot reverted edits made since without a command (27
  sites of the interface) — it now restores only what still holds what it
  left (a three-way merge per attribute);
* ``Project.save`` left the project "unsaved": it cleared the flag and the
  "saved" notification set it again.
"""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

_SOIL = {"model": "mohr_coulomb",
         "params": {"cohesion": 6.0, "friction_angle": 22.0}}


def _qt():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:  # pragma: no cover
        return None
    return QApplication.instance() or QApplication([])


def _drive(fn, timeout=120.0):
    """Run ``fn`` in a thread while this (the Qt) thread pumps events:
    the bridge answers from the event loop, as it does in the window."""
    from PySide6.QtWidgets import QApplication
    box = {}

    def target():
        try:
            box["value"] = fn()
        except BaseException as exc:  # noqa: BLE001 - re-raised below
            box["error"] = exc

    t = threading.Thread(target=target, daemon=True)
    t.start()
    deadline = time.time() + timeout
    while t.is_alive() and time.time() < deadline:
        QApplication.processEvents()
        time.sleep(0.005)
    assert not t.is_alive(), "the bridge did not answer"
    if "error" in box:
        raise box["error"]
    return box.get("value")


class _Window:
    """A real main window with its bridge on, in a private discovery dir."""

    def __enter__(self):
        from ogr_gui.main_window import MainWindow
        self._dir = tempfile.mkdtemp(prefix="ogr_bridges_")
        self._old = os.environ.get("OGR_BRIDGE_DIR")
        os.environ["OGR_BRIDGE_DIR"] = self._dir
        self.w = MainWindow()
        self.w._actions["agent_bridge"].setChecked(True)
        self.w._toggle_agent_bridge(True)
        self.bridge = self.w._agent_bridge
        return self

    def client(self):
        from ogr_api.bridge import BridgeClient
        return _drive(lambda: BridgeClient.attach())

    def __exit__(self, *exc):
        try:
            self.w._stop_agent_bridge()
            self.w.close()
            self.w.deleteLater()
        finally:
            if self._old is None:
                os.environ.pop("OGR_BRIDGE_DIR", None)
            else:
                os.environ["OGR_BRIDGE_DIR"] = self._old
        return False


def _define(c):
    return _drive(lambda: c.call("model_define", spec={
        "external": [[0, 0], [60, 0], [60, 20], [40, 20], [20, 10],
                     [0, 10]],
        "materials": [{"name": "Soil", "unit_weight": 19,
                       "strength": _SOIL}]}))


# ======================================================================
class TestTheWireAndTheDiscovery:
    def test_bytes_nan_and_errors_travel(self):
        from ogr_api.bridge import (decode, encode, error_from_dict,
                                    error_to_dict)
        from ogr_api.errors import Conflict
        msg = decode(encode({"png": b"\x89PNG\x00", "x": float("nan"),
                             "l": [1, 2.5]}))
        assert msg == {"png": b"\x89PNG\x00", "x": None, "l": [1, 2.5]}
        err = error_from_dict(error_to_dict(
            Conflict("no", hint="h", details={"a": 1})))
        assert isinstance(err, Conflict) and str(err) == "[E_CONFLICT] no " \
            "Hint: h" and err.details == {"a": 1}

    def test_a_stale_announcement_is_removed(self):
        import json

        from ogr_api.bridge import live_bridges
        folder = Path(tempfile.mkdtemp(prefix="ogr_bridges_"))
        old = os.environ.get("OGR_BRIDGE_DIR")
        os.environ["OGR_BRIDGE_DIR"] = str(folder)
        try:
            stale = folder / "99999.json"
            stale.write_text(json.dumps({
                "protocol": "ogr-slip2d-bridge/1", "port": 1, "token": "t",
                "pid": 99999, "started": 0}), encoding="utf-8")
            assert live_bridges() == [] and not stale.exists()
        finally:
            if old is None:
                os.environ.pop("OGR_BRIDGE_DIR", None)
            else:
                os.environ["OGR_BRIDGE_DIR"] = old


# ======================================================================
class TestOnlyTheTokenOpensIt:
    def test_a_wrong_token_is_refused(self):
        if _qt() is None:
            return
        from ogr_api.bridge import BridgeClient
        from ogr_api.errors import OgrApiError
        with _Window() as win:
            assert win.bridge.running
            with pytest.raises(OgrApiError):
                _drive(lambda: BridgeClient(win.bridge.port, "wrong"))
            c = win.client()
            try:
                assert c.pid == os.getpid()
            finally:
                c.close()


# ======================================================================
class TestOneModelOneUndoStack:
    def test_an_agent_edit_is_a_window_undo_step(self):
        if _qt() is None:
            return
        with _Window() as win:
            c = win.client()
            try:
                _define(c)
                w = win.w
                assert w.project.materials[0].name == "Soil"
                steps = len(w.command_stack.history()[0])
                _drive(lambda: c.call("material_set", material="Soil",
                                      properties={"unit_weight": 21.5}))
                assert w.project.materials[0].unit_weight == 21.5
                assert len(w.command_stack.history()[0]) == steps + 1
                w.act_undo()                       # the window's Ctrl+Z
                assert w.project.materials[0].unit_weight == 19.0
                w.act_redo()
                assert w.project.materials[0].unit_weight == 21.5
            finally:
                c.close()

    def test_open_goes_to_the_window_and_never_over_unsaved_work(self):
        if _qt() is None:
            return
        from ogr_api.errors import Conflict
        from ogr_core.project import Project
        folder = Path(tempfile.mkdtemp(prefix="ogr_live_"))
        other = folder / "other.ogr"
        Project("Other").save(other)
        with _Window() as win:
            c = win.client()
            try:
                _define(c)                        # unsaved in the window
                with pytest.raises(Conflict):
                    _drive(lambda: c.call("project_open", path=str(other)))
                mine = folder / "mine.ogr"
                _drive(lambda: c.call("project_save", path=str(mine)))
                assert not win.w.project.is_dirty  # saved means saved
                out = _drive(lambda: c.call("project_open",
                                            path=str(other)))
                assert win.w.project.name == "Other" and out["summary"]
                # The window's file is now other.ogr: a save goes there.
                _drive(lambda: c.call("project_save"))
                assert Project.load(mine).name != "Other"
            finally:
                c.close()

    def test_an_edit_waits_for_the_windows_computation(self):
        if _qt() is None:
            return
        from ogr_api.errors import Busy

        class Running:
            def isRunning(self):
                return True

        with _Window() as win:
            c = win.client()
            try:
                _define(c)
                win.w.worker = Running()
                with pytest.raises(Busy):
                    _drive(lambda: c.call("material_set", material="Soil",
                                          properties={"unit_weight": 20.0}))
                win.w.worker = None
            finally:
                c.close()

    def test_the_window_capture(self):
        if _qt() is None:
            return
        from ogr_api.errors import Conflict
        with _Window() as win:
            c = win.client()
            try:
                _define(c)
                out = _drive(lambda: c.call("model_render", source="window",
                                            width=400, height=300))
                assert out["png"][:8] == b"\x89PNG\r\n\x1a\n"
                with pytest.raises(Conflict):
                    _drive(lambda: c.call("model_render", source="window",
                                          field="pore_pressure"))
            finally:
                c.close()

    def test_headless_there_is_no_window_to_capture(self):
        from ogr_api import Conflict, Workspace, call
        ws = Workspace()
        try:
            call(ws, "project_new")
            with pytest.raises(Conflict):
                call(ws, "model_render", source="window")
        finally:
            ws.shutdown()


# ======================================================================
class TestWhatSharingTheStackNeeded:
    def test_an_undone_deletion_goes_back_in_its_place(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        from ogr_core.project import Project
        from ogr_core.project.commands import RemoveBoundaryCommand
        p = Project("A2")
        for y in (1.0, 2.0, 3.0):
            p.add_boundary(Boundary(polyline=Polyline(vertices=[
                Vertex(0, y), Vertex(10, y)]), btype=BoundaryType.MATERIAL))
        ids = [b.id for b in p.boundaries]
        cmd = RemoveBoundaryCommand(p.boundaries[0])
        cmd.execute(p)
        cmd.undo(p)
        assert [b.id for b in p.boundaries] == ids

    def test_undo_keeps_what_changed_since_without_a_command(self):
        from ogr_core.project import Project
        from ogr_core.project.commands import SnapshotCommand
        from ogr_core.materials import Material
        from ogr_core.materials.builtin_models import MohrCoulomb
        p = Project("merge")
        p.materials.append(Material(
            name="A", unit_weight=18.0,
            strength=MohrCoulomb(cohesion=5.0, friction_angle=30.0)))

        def edit(project):
            project.name = "renamed"
            project.materials[0].unit_weight = 20.0

        cmd = SnapshotCommand("agent edit", edit)
        cmd.execute(p)
        # The interface edits the material with no command (it has 27
        # such sites); the name it leaves alone.
        p.materials[0].unit_weight = 25.0
        cmd.undo(p)
        assert p.name == "merge"                 # undone
        assert p.materials[0].unit_weight == 25.0   # kept
        assert cmd.kept == ["materials"]
        cmd.execute(p)                           # redo
        assert p.name == "renamed" and p.materials[0].unit_weight == 25.0

    def test_saving_leaves_the_project_saved(self):
        from ogr_core.project import Project
        folder = Path(tempfile.mkdtemp(prefix="ogr_saved_"))
        p = Project("S")
        p.name = "S2"
        p._notify("renamed")
        assert p.is_dirty
        p.save(folder / "s.ogr")
        assert p.is_dirty is False


# ======================================================================
class TestTheMcpServerForwards:
    def test_every_parameter_reaches_the_window(self):
        """test_mcp_server_v1195's check, with the bridge in place of the
        registry: a tool that dropped a parameter on the way to the window
        would be a control that moves nothing (rule 7)."""
        try:
            import mcp  # noqa: F401
        except ImportError:
            if os.environ.get("GITHUB_ACTIONS") == "true":
                raise AssertionError("the mcp SDK must be installed in CI")
            return
        import asyncio

        from mcp import Client

        from ogr_mcp.server import build_server
        import test_mcp_server_v1195 as base

        seen = {}

        class Backend:
            pid, window = 1, "fake"

            def call(self, op, /, **kwargs):
                seen[op] = kwargs
                if op == "model_render":
                    return {"png": b"\x89PNG\r\n\x1a\n", "saved_to": None}
                if op == "project_list":
                    return {"projects": []}
                return {"ok": True, "state": "done", "job_id": "j_x"}

        srv = build_server(None, backend=Backend())
        value = base._value

        async def scenario():
            async with Client(srv) as c:
                for t in (await c.list_tools()).tools:
                    if t.name == "server_info":
                        info = await c.call_tool(t.name, {})
                        assert not info.is_error
                        continue
                    props = t.input_schema.get("properties", {})
                    args = {n: value(n, s) for n, s in props.items()}
                    r = await c.call_tool(t.name, args)
                    assert not r.is_error, (t.name, r.content)
                    got = seen.pop(t.name)
                    for n, v in args.items():
                        if (t.name, n) in base._CONSUMED_HERE:
                            continue
                        assert got.get(n) == v, (t.name, n, v, got.get(n))
        asyncio.run(scenario())

    def test_attaching_to_no_window_says_so(self):
        from ogr_mcp.cli import main
        folder = tempfile.mkdtemp(prefix="ogr_bridges_")
        old = os.environ.get("OGR_BRIDGE_DIR")
        os.environ["OGR_BRIDGE_DIR"] = folder
        try:
            try:
                import mcp  # noqa: F401
            except ImportError:
                return
            assert main(["--attach"]) == 2
        finally:
            if old is None:
                os.environ.pop("OGR_BRIDGE_DIR", None)
            else:
                os.environ["OGR_BRIDGE_DIR"] = old

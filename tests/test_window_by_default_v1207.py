# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.207 — if the program is open, what an agent does is done THERE.

The owner's rule (2026-09-25): "by default, in any configuration, if you
ask it to do something it shows it, if the program is open". Until this
version the MCP server worked on models of its own unless it was started
with ``--attach``, and ``--attach`` refused to start without a window that
already had its bridge on. So the client's configuration decided, the
order of opening mattered, and the window showed nothing by default.

Invariants protected:

* **The window by default.** Without any option, a call goes to the open
  window when there is one, and to the server's own models when there is
  not (``ogr_api.bridge.WindowRouter``).
* **What is the server's stays the server's.** A ``project_id``, ``job_id``
  or ``result_id`` the server holds keeps going to it after a window
  appears, so a model begun before is not lost.
* **The order is free.** The window is looked for when a call needs it; a
  window that closes is noticed BEFORE the next call is sent (so that call
  goes where it should), and one that opens again is found again.
* **A call the window was answering when it died is not repeated**
  elsewhere: whether it ran cannot be known.
* **The window's side**: the program starts its bridge when it opens
  (``ogr_gui.__main__.start_window``), ``--no-agent-bridge`` keeps it off
  (rule 7: the option moves something), and the server's ``--workdir``
  reaches the window, so a relative path means the same folder there.
* **Tests never find the user's window**: the runner gives the whole run
  an empty discovery folder (``tests/_runner.py``).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

_SOIL = {"model": "mohr_coulomb",
         "params": {"cohesion": 6.0, "friction_angle": 22.0}}


class _FakeClient:
    """A window that records what reaches it."""

    def __init__(self, name="w"):
        self.name = name
        self.calls = []
        self.open = True
        self.pid, self.window = 4242, f"window {name}"

    def alive(self):
        return self.open

    def call(self, op, /, **kwargs):
        if not self.open:
            raise ConnectionError("closed")
        self.calls.append((op, kwargs))
        if op == "project_list":
            return {"projects": [{"project_id": "p_win", "name": "W"}]}
        return {"where": self.name, "op": op}

    def close(self):
        self.open = False


def _router(windows, **kw):
    """A router over a real local workspace and a scripted list of
    windows: each call to the finder pops the next availability."""
    from ogr_api import Workspace
    from ogr_api.bridge import WindowRouter

    ws = Workspace()
    state = {"windows": list(windows)}

    def finder():
        return state["windows"][0] if state["windows"] else None

    def connect(info):
        return info

    r = WindowRouter(ws, finder=finder, connect=connect, **kw)
    return r, ws, state


# ======================================================================
class TestTheWindowByDefault:
    def test_no_window_means_the_servers_own_model(self):
        r, ws, _ = _router([])
        try:
            out = r.call("project_new", name="own")
            assert out["project_id"] in ws.projects
            assert r.status()["next_call_goes_to"] == \
                "the server's own models"
        finally:
            ws.shutdown()

    def test_an_open_window_takes_the_call(self):
        w = _FakeClient()
        r, ws, _ = _router([w])
        try:
            out = r.call("model_define", spec={"x": 1})
            assert out == {"where": "w", "op": "model_define"}
            assert not ws.projects
            st = r.status()
            assert st["window_open"] and st["mode"] == "automatic"
        finally:
            ws.shutdown()

    def test_what_is_the_servers_stays_with_it(self):
        state_w = _FakeClient()
        r, ws, state = _router([])
        try:
            pid = r.call("project_new", name="before")["project_id"]
            state["windows"].append(state_w)        # the program opens
            out = r.call("project_summary", project_id=pid)
            assert out["project_id"] == pid, out    # answered locally
            assert state_w.calls == []
            r.call("project_list")                   # names nothing: window
            assert state_w.calls and state_w.calls[0][0] == "project_list"
        finally:
            ws.shutdown()

    def test_a_closed_window_is_noticed_before_the_next_call(self):
        w = _FakeClient()
        r, ws, state = _router([w])
        try:
            r.call("project_list")
            w.open = False                           # the program closes
            state["windows"].clear()
            out = r.call("project_new", name="after")
            assert out["project_id"] in ws.projects  # not an error
            w2 = _FakeClient("w2")
            state["windows"].append(w2)              # and opens again
            assert r.call("project_list")["projects"][0]["project_id"] == \
                "p_win"
            assert w2.calls
        finally:
            ws.shutdown()

    def test_a_call_cut_in_the_middle_is_not_repeated(self):
        from ogr_api.errors import Conflict

        class Dying(_FakeClient):
            def alive(self):
                return True                          # it looked alive

            def call(self, op, /, **kwargs):
                raise ConnectionError("gone mid-call")

        r, ws, _ = _router([Dying()])
        try:
            with pytest.raises(Conflict):
                r.call("project_new", name="x")
            assert not ws.projects, "the call was repeated locally"
        finally:
            ws.shutdown()

    def test_only_window_says_what_to_open(self):
        from ogr_api.bridge import WindowRouter
        from ogr_api.errors import NotConfigured
        r = WindowRouter(only_window=True, finder=lambda: None)
        with pytest.raises(NotConfigured):
            r.call("project_list")
        assert r.status()["mode"] == "window only"


# ======================================================================
def _qt():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:  # pragma: no cover
        return None
    return QApplication.instance() or QApplication([])


class _Discovery:
    """A private discovery folder, restored after (rule 5)."""

    def __enter__(self):
        self.old = os.environ.get("OGR_BRIDGE_DIR")
        self.dir = tempfile.mkdtemp(prefix="ogr_bridges_")
        os.environ["OGR_BRIDGE_DIR"] = self.dir
        return self

    def __exit__(self, *exc):
        if self.old is None:
            os.environ.pop("OGR_BRIDGE_DIR", None)
        else:
            os.environ["OGR_BRIDGE_DIR"] = self.old
        return False


class TestWithARealWindow:
    def test_the_program_starts_its_bridge_and_the_option_stops_it(self):
        if _qt() is None:
            return
        from ogr_api.bridge import live_bridges
        from ogr_gui.__main__ import start_window
        with _Discovery():
            off = start_window(agent_bridge=False)
            try:
                assert getattr(off, "_agent_bridge", None) is None
                assert live_bridges() == []
            finally:
                off.close()
                off.deleteLater()
            on = start_window()
            try:
                assert on._agent_bridge is not None and on._agent_bridge.running
                assert on._actions["agent_bridge"].isChecked()
                assert [b["pid"] for b in live_bridges()] == [os.getpid()]
            finally:
                on._stop_agent_bridge()
                on.close()
                on.deleteLater()

    def test_the_default_server_edits_the_window_and_uses_the_workdir(self):
        if _qt() is None:
            return
        from test_live_bridge_v1203 import _drive

        from ogr_api import Workspace
        from ogr_api.bridge import WindowRouter
        from ogr_gui.__main__ import start_window
        work = Path(tempfile.mkdtemp(prefix="ogr_work_"))
        with _Discovery():
            win = start_window()
            ws = Workspace(workdir=str(work))
            r = WindowRouter(ws)
            try:
                _drive(lambda: r.call("model_define", spec={
                    "external": [[0, 0], [60, 0], [60, 20], [40, 20],
                                 [20, 10], [0, 10]],
                    "materials": [{"name": "Soil", "unit_weight": 19,
                                   "strength": _SOIL}]}))
                assert win.project.materials[0].name == "Soil"
                assert not ws.projects, "the model was built off-window"
                steps = len(win.command_stack.history()[0])
                assert steps >= 1, "the edit is not an undo step there"
                _drive(lambda: r.call("project_save", path="rel.ogr"))
                assert (work / "rel.ogr").is_file(), (
                    "a relative path did not mean the server's --workdir")
            finally:
                r.close()
                ws.shutdown()
                win._stop_agent_bridge()
                win.close()
                win.deleteLater()


# ======================================================================
class TestTheCommandLine:
    def test_contradictions_are_refused(self):
        try:
            import mcp  # noqa: F401
        except ImportError:
            return
        from ogr_mcp.cli import main
        assert main(["--attach", "--headless"]) == 2
        assert main(["--attach", "not-a-pid"]) == 2

    def test_the_run_cannot_see_the_users_windows(self):
        """The runner's own guard, checked from inside a test: any server a
        test starts looks in an empty folder of this run, never in the
        user's home."""
        folder = Path(os.environ.get("OGR_BRIDGE_DIR", ""))
        home = Path.home() / ".ogr-slip2d" / "bridges"
        assert folder.name and folder.resolve() != home.resolve()

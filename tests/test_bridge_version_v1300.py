# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.300 (D296) — ``server_info`` says when the MCP server and the window
it forwards to run different versions of OGR Slip2D.

The defect (first GUI test, H0): Claude Desktop had started its
``ogr-slip2d`` server before the code was updated. ``server_info`` said
``"version": "0.1.271"`` while the window's title said v0.1.284 and every
call went to that window, and nothing warned. An old server shows the
agent the tools, schemas and guide of another version while the
operations run in the new window, and the agent has no way to know.

What these tests protect:

* the window says its version: in the bridge's greeting and in its
  discovery file, and ``BridgeClient`` keeps it;
* ``WindowRouter.status()`` carries it;
* ``server_info`` compares it with its own: the same version gives no
  warning; a different one gives a warning that says which side is older
  and what to restart; a window that does not report a version (older than
  0.1.300, when the greeting began to carry it) is a mismatch too;
* with no window open, there is nothing to compare and nothing is said.
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_mcp import __version__  # noqa: E402


class _FakeClient:
    """An open window of the version given (``None``: it does not say)."""

    def __init__(self, version):
        self.pid, self.window = 4242, "OGR Slip2D vX — fake"
        self.version = version

    def alive(self):
        return True

    def call(self, op, /, **kwargs):
        if op == "project_list":
            return {"projects": []}
        return {}

    def close(self):
        pass


def _info(window_version=None, *, window=True):
    """``server_info`` of a server routed to a fake window."""
    from mcp import Client

    from ogr_api import Workspace
    from ogr_api.bridge import WindowRouter
    from ogr_mcp.server import build_server

    ws = Workspace()
    fake = _FakeClient(window_version)
    router = WindowRouter(ws, finder=lambda: fake if window else None,
                          connect=lambda info: info)
    srv = build_server(ws, backend=router)

    async def scenario():
        async with Client(srv) as c:
            r = await c.call_tool("server_info", {})
            assert not r.is_error, r.content
            return r.structured_content
    try:
        return asyncio.run(scenario())
    finally:
        ws.shutdown()


def _older(v):
    major, minor, patch = (int(p) for p in v.split("."))
    return f"{major}.{minor}.{patch - 1}" if patch else f"{major}.{minor - 1}.999"


def _newer(v):
    major, minor, patch = (int(p) for p in v.split("."))
    return f"{major}.{minor}.{patch + 1}"


def _have_mcp():
    from test_mcp_server_v1195 import _have_mcp as have
    return have()


# ======================================================================
class TestTheWindowSaysItsVersion:
    def test_the_greeting_and_the_discovery_carry_it(self):
        from PySide6.QtWidgets import QApplication

        from ogr_gui.agent_bridge import AgentBridge
        from ogr_gui.main_window import MainWindow
        QApplication.instance() or QApplication([])
        old = os.environ.get("OGR_BRIDGE_DIR")
        os.environ["OGR_BRIDGE_DIR"] = tempfile.mkdtemp(prefix="ogr_bridges_")
        w = MainWindow()
        bridge = AgentBridge(w)
        try:
            bridge.start()
            hello = bridge._answer({"authed": False},
                                   {"hello": "ogr-slip2d-bridge/1",
                                    "token": bridge.token})
            assert hello["ok"] and hello["version"] == w.VERSION
            data = json.loads(bridge.discovery.read_text(encoding="utf-8"))
            assert data["version"] == w.VERSION
        finally:
            bridge.stop()
            w.project.is_dirty = False
            w.close()
            if old is None:
                os.environ.pop("OGR_BRIDGE_DIR", None)
            else:
                os.environ["OGR_BRIDGE_DIR"] = old

    def test_the_client_keeps_it(self):
        from ogr_api.bridge import PROTOCOL, BridgeClient, decode, encode

        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)

        def answer(version):
            conn, _ = server.accept()
            with conn, conn.makefile("rwb") as f:
                decode(f.readline())
                reply = {"hello": PROTOCOL, "ok": True, "window": "w",
                         "pid": 7}
                if version is not None:
                    reply["version"] = version
                f.write(encode(reply))
                f.flush()
                f.readline()            # until the client hangs up
        try:
            for version in ("9.8.7", None):
                t = threading.Thread(target=answer, args=(version,),
                                     daemon=True)
                t.start()
                c = BridgeClient(server.getsockname()[1], "token")
                try:
                    assert c.version == version
                finally:
                    c.close()
                t.join(5)
        finally:
            server.close()


class TestServerInfoCompares:
    def test_the_same_version_says_nothing(self):
        if not _have_mcp():
            return
        si = _info(__version__)
        assert si["attached_to_window"]["version"] == __version__
        assert si["warnings"] == []

    def test_an_older_server_says_restart_the_client(self):
        if not _have_mcp():
            return
        si = _info(_newer(__version__))
        assert len(si["warnings"]) == 1, si["warnings"]
        text = si["warnings"][0]
        assert __version__ in text and _newer(__version__) in text
        assert "Restart the MCP client" in text

    def test_an_older_window_says_reopen_the_program(self):
        if not _have_mcp():
            return
        si = _info(_older(__version__))
        assert len(si["warnings"]) == 1, si["warnings"]
        assert "reopen OGR Slip2D" in si["warnings"][0]

    def test_a_window_that_does_not_say_is_older(self):
        if not _have_mcp():
            return
        si = _info(None)
        assert len(si["warnings"]) == 1, si["warnings"]
        assert "0.1.300" in si["warnings"][0]
        assert "reopen OGR Slip2D" in si["warnings"][0]

    def test_no_window_nothing_to_compare(self):
        if not _have_mcp():
            return
        si = _info(_newer(__version__), window=False)
        assert si["attached_to_window"]["window_open"] is False
        assert si["warnings"] == []

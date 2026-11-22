# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.481 — ``server_info`` names the folder relative paths are resolved
against in every mode of the MCP server, ``--attach`` included.

The defect, seen on the machine of 2026-11-22: a server started with
``--attach --workdir <folder>`` answered ``"workdir": null``. In that mode
the server has no workspace of its own (``ws is None``), and ``server_info``
only looked there; the ``--workdir`` was in use all the same, kept by the
``WindowRouter`` and sent to the window in the bridge's greeting, so a
relative path meant that folder while the server said there was none.

What these tests protect:

* attached to a window, ``server_info`` gives the router's ``workdir``;
* attached without ``--workdir``, it still says ``null``: nothing invented;
* with a workspace of its own, the workspace's folder, as before.
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _have_mcp():
    from test_mcp_server_v1195 import _have_mcp as have
    return have()


def _workdir(ws, router):
    from mcp import Client

    from ogr_mcp.server import build_server
    from _leaks import root_logging_kept
    # v0.1.374 — building the server configures the root logger (audit D-f)
    with root_logging_kept():
        srv = build_server(ws, backend=router)

    async def scenario():
        async with Client(srv) as c:
            r = await c.call_tool("server_info", {})
            assert not r.is_error, r.content
            return r.structured_content["workdir"]
    return asyncio.run(scenario())


class TestTheWorkdirIsSaid:

    def test_attached_it_is_the_routers(self):
        if not _have_mcp():
            return
        from ogr_api.bridge import WindowRouter
        with tempfile.TemporaryDirectory() as d:
            router = WindowRouter(None, only_window=True, workdir=d,
                                  finder=lambda: None)
            assert _workdir(None, router) == str(d)

    def test_attached_without_one_it_is_null(self):
        if not _have_mcp():
            return
        from ogr_api.bridge import WindowRouter
        router = WindowRouter(None, only_window=True, finder=lambda: None)
        assert _workdir(None, router) is None

    def test_with_a_workspace_it_is_the_workspaces(self):
        if not _have_mcp():
            return
        from ogr_api import Workspace
        from ogr_api.bridge import WindowRouter
        with tempfile.TemporaryDirectory() as d:
            ws = Workspace(workdir=d)
            try:
                router = WindowRouter(ws, finder=lambda: None)
                got = _workdir(ws, router)
                assert got == str(ws.workdir), (got, ws.workdir)
            finally:
                ws.shutdown()

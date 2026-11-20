# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.476 — a tool's description is the same text on every Python.

The invariant: what a model reads about a tool is its docstring without the
indentation of the source, whatever interpreter serves it. The MCP SDK takes
``fn.__doc__`` as it is, and Python strips the common indentation of
docstrings at compile time only from 3.13 on; on 3.11 and 3.12 every
continuation line carried eight spaces into the model's context. Linux's CI
saw it as the compact profile measuring 14 060 against its budget of 14 000
on 3.11 and 3.12 and passing on 3.13 -- exactly the 88 characters of
indentation the raw docstrings of its eight multi-line tools add, measured
against the source.

The first case has its teeth on any Python: the docstring is assigned at run
time, which the compiler never sees, so returning ``fn.__doc__`` unchanged
fails it on 3.14 as on 3.11. Another marks what the function returns and
looks for the mark in every tool the protocol lists, so a registration that
skips it fails on any Python too. The last reads what the protocol sends, which
on 3.13+ would pass without the fix and is there for the CI's 3.11 and 3.12.

Cost: well under a second; one server per profile, no analysis.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _have_mcp() -> bool:
    try:
        import mcp  # noqa: F401
    except ImportError:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise AssertionError("the mcp SDK must be installed in CI")
        return False
    return True


class TestTheDescription:

    def test_the_source_indentation_does_not_reach_the_model(self):
        if not _have_mcp():
            return
        from ogr_mcp.server import _tool_description

        def tool():
            pass
        # what 3.11 leaves in __doc__ for a docstring inside build_server
        tool.__doc__ = ("Create a model (empty or the demo slope); returns its"
                        "\n        project_id.\n        ")
        assert _tool_description(tool) == (
            "Create a model (empty or the demo slope); returns its\n"
            "project_id.")

    def test_no_docstring_is_no_description(self):
        if not _have_mcp():
            return
        from ogr_mcp.server import _tool_description

        def tool():
            pass
        assert _tool_description(tool) is None

    def test_every_tool_is_registered_through_it(self):
        """On 3.13+ the compiler already strips the indentation, so the case
        below cannot see a registration that skips ``_tool_description``;
        this one marks what it returns and looks for the mark."""
        if not _have_mcp():
            return
        from mcp import Client

        import ogr_mcp.server as S
        from _leaks import root_logging_kept
        from ogr_api import Workspace

        async def listed(srv):
            async with Client(srv) as c:
                return (await c.list_tools()).tools

        original = S._tool_description
        S._tool_description = lambda fn: "MARK " + (original(fn) or "")
        ws = Workspace()
        try:
            with root_logging_kept():
                srv = S.build_server(ws, profile="full")
            tools = asyncio.run(listed(srv))
        finally:
            S._tool_description = original
            ws.shutdown()
        unmarked = [t.name for t in tools
                    if not (t.description or "").startswith("MARK ")]
        assert not unmarked, unmarked

    def test_no_line_the_server_sends_starts_indented(self):
        if not _have_mcp():
            return
        from mcp import Client

        from _leaks import root_logging_kept
        from ogr_api import Workspace
        from ogr_mcp.server import build_server

        async def listed(srv):
            async with Client(srv) as c:
                return (await c.list_tools()).tools

        for profile in ("compact", "full"):
            ws = Workspace()
            try:
                with root_logging_kept():
                    srv = build_server(ws, profile=profile)
                tools = asyncio.run(listed(srv))
            finally:
                ws.shutdown()
            bad = {t.name: t.description for t in tools
                   if t.description and any(
                       ln != ln.lstrip() or ln != ln.rstrip()
                       for ln in t.description.splitlines())}
            assert not bad, (profile, json.dumps(bad, indent=1)[:2000])

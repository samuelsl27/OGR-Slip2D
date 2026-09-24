# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.195 (spec 008, F1b) — the MCP tools are the operations, faithfully.

Driven through the SDK's own in-memory client, so everything here crosses
the real protocol layer (schemas, validation, content conversion) without a
process or a port. Invariants protected:

* **No drift between the tools and ``ogr_api``.** Every operation has a
  tool and every tool (but ``server_info``) is an operation; and EVERY TOOL
  PARAMETER REACHES ITS OPERATION with the value given — checked by
  calling each tool with a non-default value for every parameter and
  spying on the call. A parameter the tool accepted and dropped would be a
  control that moves nothing (rule 7) in the one layer that has no other
  test of it. The two exceptions consume their argument in this layer
  (``wait_seconds``), and have their own test below.
* **A model can read the tools**: every tool and every parameter has a
  description, the order is stable (the 2026-07-28 specification asks for
  deterministic lists), and the compact profile stays under a frozen size.
* **Errors carry their code and their suggestion**, and an unexpected
  exception its type — the SDK would otherwise send "Error executing tool".
* **Rule 1 through the protocol**: ACADS 1(a) built and run by tool calls
  gives exactly the number the operations layer gives, inside the
  published band.
* **The documentation names every tool** (``docs/mcp/herramientas.md``).

Every test returns early when the ``mcp`` SDK is not installed — EXCEPT in
CI, where a missing SDK is a failure: otherwise this file could be skipped
in its entirety without anyone noticing.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))

import test_acads_validation_v178 as acads  # noqa: E402

#: The compact profile's tools/list, in JSON characters, may not grow past
#: this. Measured 12 774 when it was written (v0.1.195); the margin is for
#: honest edits of a description, not for new tools.
_COMPACT_BUDGET = 14_000

#: Parameters the MCP layer consumes itself instead of forwarding.
_CONSUMED_HERE = {("analysis_run", "wait_seconds"),
                  ("job_get", "wait_seconds")}


def _have_mcp() -> bool:
    try:
        import mcp  # noqa: F401
    except ImportError:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise AssertionError("the mcp SDK must be installed in CI "
                                 "(pip install -e .[mcp])")
        return False
    return True


def _run(coro):
    return asyncio.run(coro)


def _server(profile="full", ws=None):
    from ogr_api import Workspace
    from ogr_mcp.server import build_server
    ws = ws or Workspace()
    return ws, build_server(ws, profile=profile)


async def _tools(srv):
    from mcp import Client
    async with Client(srv) as c:
        return (await c.list_tools()).tools


class TestTheToolsAreTheOperations:
    def test_every_operation_has_a_tool_and_back(self):
        if not _have_mcp():
            return
        from ogr_api import OPERATIONS
        ws, srv = _server()
        try:
            names = {t.name for t in _run(_tools(srv))}
        finally:
            ws.shutdown()
        assert names - {"server_info"} == set(OPERATIONS), (
            sorted(names ^ (set(OPERATIONS) | {"server_info"})))

    def test_every_parameter_reaches_its_operation(self):
        if not _have_mcp():
            return
        import ogr_mcp.server as S
        from mcp import Client
        ws, srv = _server()
        seen = {}

        def spy(_ws, op, /, **kwargs):
            seen[op] = kwargs
            if op == "model_render":
                return {"png": b"\x89PNG\r\n\x1a\n", "saved_to": None}
            if op in ("analysis_run", "job_get"):
                return {"job_id": "j_x", "state": "done"}
            return {"ok": True}

        def value(name, schema, default=None):
            """A NON-default value of the declared type (nested lists
            included: ``list[float]`` and ``list[list[float]]`` differ)."""
            default = schema.get("default", default)
            options = [s for s in schema.get("anyOf", [schema])
                       if s.get("type") != "null"] or [schema]
            s = options[0]
            if "enum" in s:
                return next((o for o in s["enum"] if o != default),
                            s["enum"][0])
            kind = s.get("type")
            if kind == "boolean":
                return not (default or False)
            if kind == "integer":
                return 7
            if kind == "number":
                return 2.5
            if kind == "array":
                item = s.get("items", {})
                return [value(name, item), value(name, item)]
            if kind == "object":
                return {"k": 1}
            return f"v_{name}"

        saved = S.call
        S.call = spy
        try:
            async def scenario():
                async with Client(srv) as c:
                    tools = (await c.list_tools()).tools
                    for t in tools:
                        if t.name == "server_info":
                            continue
                        props = t.input_schema.get("properties", {})
                        args = {n: value(n, s) for n, s in props.items()}
                        r = await c.call_tool(t.name, args)
                        assert not r.is_error, (t.name, r.content)
                        op_args = seen.pop(t.name)
                        for n, v in args.items():
                            if (t.name, n) in _CONSUMED_HERE:
                                continue
                            assert op_args.get(n) == v, (t.name, n, v,
                                                         op_args.get(n))
            _run(scenario())
        finally:
            S.call = saved
            ws.shutdown()

    def test_the_tool_parameters_are_the_operation_parameters(self):
        """Names too: a tool parameter the operation does not declare
        would be refused at call time, not at registration."""
        if not _have_mcp():
            return
        import inspect
        from ogr_api import OPERATIONS
        ws, srv = _server()
        try:
            for t in _run(_tools(srv)):
                if t.name == "server_info":
                    continue
                op = set(inspect.signature(OPERATIONS[t.name].func)
                         .parameters) - {"ws"}
                tool = set(t.input_schema.get("properties", {}))
                assert tool <= op, (t.name, sorted(tool - op))
        finally:
            ws.shutdown()


class TestAModelCanReadThem:
    def test_every_tool_and_parameter_is_described(self):
        if not _have_mcp():
            return
        ws, srv = _server()
        try:
            for t in _run(_tools(srv)):
                assert t.description and len(t.description) > 20, t.name
                for n, s in t.input_schema.get("properties", {}).items():
                    assert s.get("description"), (t.name, n)
        finally:
            ws.shutdown()

    def test_the_profiles_and_their_order(self):
        if not _have_mcp():
            return
        from ogr_mcp.profiles import PROFILES
        for profile in ("full", "compact"):
            ws, srv = _server(profile)
            try:
                names = [t.name for t in _run(_tools(srv))]
            finally:
                ws.shutdown()
            assert names == list(PROFILES[profile]), profile
        assert set(PROFILES["compact"]) < set(PROFILES["full"])

    def test_the_compact_profile_stays_small(self):
        if not _have_mcp():
            return
        ws, srv = _server("compact")
        try:
            tools = _run(_tools(srv))
        finally:
            ws.shutdown()
        size = len(json.dumps([t.model_dump(mode="json", exclude_none=True)
                               for t in tools]))
        assert size <= _COMPACT_BUDGET, size

    def test_the_documentation_names_every_tool(self):
        from ogr_mcp.profiles import PROFILES
        doc = (_ROOT / "docs" / "mcp" / "herramientas.md").read_text(
            encoding="utf-8")
        missing = [t for t in PROFILES["full"] if f"`{t}`" not in doc]
        assert not missing, missing


class TestErrors:
    def test_a_refusal_keeps_its_code_and_suggestion(self):
        if not _have_mcp():
            return
        from mcp import Client
        ws, srv = _server()

        async def scenario():
            async with Client(srv) as c:
                await c.call_tool("project_new", {"name": "e"})
                r = await c.call_tool("settings_set", {"changes": {
                    "search.search_metod": "slope"}})
                return r
        try:
            r = _run(scenario())
        finally:
            ws.shutdown()
        text = r.content[0].text
        assert r.is_error
        assert "[E_INVALID_ARGUMENT]" in text and "'search_method'" in text

    def test_an_unexpected_exception_keeps_its_type(self):
        if not _have_mcp():
            return
        import ogr_mcp.server as S
        from mcp import Client
        ws, srv = _server()

        def boom(*_a, **_k):
            raise ValueError("boom detail")

        async def scenario():
            async with Client(srv) as c:
                return await c.call_tool("project_list", {})
        saved = S.call
        S.call = boom
        try:
            r = _run(scenario())
        finally:
            S.call = saved
            ws.shutdown()
        assert r.is_error and "ValueError: boom detail" in r.content[0].text


def _acads_by_tools(profile="compact"):
    from mcp import Client
    ws, srv = _server(profile)
    (x0, x1), (y0, y1) = acads._GRID["grid_x"], acads._GRID["grid_y"]

    async def scenario():
        async with Client(srv) as c:
            await c.call_tool("project_new", {"name": "ACADS"})
            r = await c.call_tool("model_define", {"spec": {
                "external": [[20, 20], [70, 20], [70, 35], [50, 35],
                             [30, 25], [20, 25]],
                "materials": [{"name": "Soil", "unit_weight": 20.0,
                               "strength": {"model": "mohr_coulomb",
                                            "params": {"cohesion": 3.0,
                                                       "friction_angle":
                                                           19.6}}}]}})
            assert not r.is_error, r.content
            r = await c.call_tool("analysis_configure", {
                "methods": ["bishop_simplified"],
                "grid": {"x_min": x0, "x_max": x1, "y_min": y0,
                         "y_max": y1, "nx": 20, "ny": 20},
                "radius_increment": 10})
            assert not r.is_error, r.content
            r = await c.call_tool("analysis_run", {"wait_seconds": 50})
            assert not r.is_error, r.content
            return r.structured_content
    try:
        return _run(scenario())
    finally:
        ws.shutdown()


class TestRuleOneThroughTheProtocol:
    def test_acads_by_tool_calls(self):
        if not _have_mcp():
            return
        out = _acads_by_tools()
        assert out["state"] == "done", out
        m = out["summary"]["methods"][0]
        assert m["counts"]["attempted"] == 21 * 21 * 11
        err = abs(m["value"] - acads._MEAN_33) / acads._MEAN_33
        assert err < acads._TOL, m["value"]

    def test_it_is_the_number_the_operations_layer_gives(self):
        if not _have_mcp():
            return
        from ogr_api import Workspace, call
        through_mcp = _acads_by_tools()["summary"]["methods"][0]["value"]
        ws = Workspace()
        try:
            pid = call(ws, "project_new", name="ACADS")["project_id"]
            call(ws, "model_define", project_id=pid, spec={
                "external": [[20, 20], [70, 20], [70, 35], [50, 35],
                             [30, 25], [20, 25]],
                "materials": [{"name": "Soil", "unit_weight": 20.0,
                               "strength": {"model": "mohr_coulomb",
                                            "params": {"cohesion": 3.0,
                                                       "friction_angle":
                                                           19.6}}}]})
            (x0, x1), (y0, y1) = acads._GRID["grid_x"], acads._GRID["grid_y"]
            call(ws, "analysis_configure", project_id=pid,
                 methods=["bishop_simplified"],
                 grid={"x_min": x0, "x_max": x1, "y_min": y0, "y_max": y1,
                       "nx": 20, "ny": 20}, radius_increment=10)
            direct = call(ws, "analysis_run", project_id=pid,
                          wait_seconds=300)
        finally:
            ws.shutdown()
        assert through_mcp == direct["summary"]["methods"][0]["value"]


class TestWhatTheLayerAdds:
    def test_wait_seconds_decides_between_a_result_and_a_job(self):
        """Rule 7 for the one argument this layer consumes itself."""
        if not _have_mcp():
            return
        from mcp import Client
        ws, srv = _server()

        async def scenario():
            async with Client(srv) as c:
                await c.call_tool("project_new", {"name": "wait"})
                await c.call_tool("model_define", {"spec": {
                    "external": [[20, 20], [70, 20], [70, 35], [50, 35],
                                 [30, 25], [20, 25]],
                    "materials": [{"name": "S", "strength": {
                        "model": "mohr_coulomb",
                        "params": {"cohesion": 3, "friction_angle": 20}}}],
                    "settings": {"methods.enabled_methods":
                                 ["gle_morgenstern_price", "spencer"],
                                 "search.grid_nx": 60, "search.grid_ny": 60,
                                 "search.radius_increment": 12}}})
                r = await c.call_tool("analysis_run", {"wait_seconds": 0})
                st = r.structured_content
                assert st["state"] == "running" and st["job_id"], st
                r = await c.call_tool("job_get", {"job_id": st["job_id"],
                                                  "wait_seconds": 1})
                assert r.structured_content["state"] == "running"
                r = await c.call_tool("job_cancel", {"job_id":
                                                     st["job_id"]})
                return r.structured_content
        try:
            out = _run(scenario())
        finally:
            ws.shutdown()
        assert out["state"] == "cancelled", out

    def test_the_render_is_an_image(self):
        if not _have_mcp():
            return
        import base64
        from mcp import Client
        ws, srv = _server()

        async def scenario():
            async with Client(srv) as c:
                await c.call_tool("project_new", {"name": "img"})
                await c.call_tool("model_define", {"spec": {
                    "external": [[0, 0], [40, 0], [40, 10], [20, 10],
                                 [10, 5], [0, 5]],
                    "materials": [{"name": "S", "strength": {
                        "model": "undrained",
                        "params": {"cohesion": 20}}}]}})
                return await c.call_tool("model_render", {"width": 400,
                                                          "height": 300})
        try:
            r = _run(scenario())
        finally:
            ws.shutdown()
        assert not r.is_error
        img = r.content[0]
        assert img.type == "image" and img.mime_type == "image/png"
        png = base64.b64decode(img.data)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"

    def test_resources_and_server_info(self):
        if not _have_mcp():
            return
        from mcp import Client
        from ogr_api.inventory import coverage
        ws, srv = _server()

        async def scenario():
            async with Client(srv) as c:
                g = await c.read_resource("ogr://guide")
                cat = await c.read_resource("ogr://catalog/methods")
                info = await c.call_tool("server_info", {})
                return g, cat, info
        try:
            g, cat, info = _run(scenario())
        finally:
            ws.shutdown()
        assert "first material" in g.contents[0].text.lower()
        ids = {e["id"] for e in json.loads(cat.contents[0].text)["entries"]}
        assert "spencer" in ids
        si = info.structured_content
        assert si["units"].startswith("SI")
        assert si["program_coverage"] == coverage()
        assert si["licence"] == "AGPL-3.0-or-later"

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.195 (spec 008, F1b) — the server as a real process, on both transports.

Invariants protected:

* **stdio survives stray output.** Over stdio the process's standard
  output IS the protocol, and ``python_exec`` runs arbitrary code. A
  ``print``, a raw ``os.write(1, ...)`` and a CHILD PROCESS writing to its
  inherited standard output must none of them reach the wire: the next call
  must still work. (The SDK diverts file descriptor 1 while it serves — the
  spike of F0 read it in its source; this is the test that it holds.)
* **HTTP always needs the token** — 401 without it or with a wrong one —
  and the SDK's DNS-rebinding protection is ON: a foreign ``Origin`` is 403
  and a foreign ``Host`` 421, even WITH the token.
* **No network without a token.** A non-loopback host with no explicit
  token, or with ``--no-auth``, is refused at start (exit code 2) — because
  ``python_exec`` makes the port a way to run code as the user.
* **A missing SDK says what to install** (exit code 3), rather than a
  traceback from an import.

Every test that needs the SDK returns early without it, except in CI.
"""
from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _have_mcp() -> bool:
    try:
        import mcp  # noqa: F401
    except ImportError:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise AssertionError("the mcp SDK must be installed in CI")
        return False
    return True


def _env(**extra) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("OGR_MCP_TOKEN", None)
    env.update(extra)
    return env


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


_STRAY = r'''
import os, subprocess, sys
print("hello from print")
os.write(1, b"raw bytes on fd 1\n")
subprocess.run([sys.executable, "-c", "print('child stdout')"])
sys.stdout.flush()
6 * 7
'''


class TestStdio:
    def test_stray_output_never_reaches_the_protocol(self):
        if not _have_mcp():
            return
        from mcp import Client, StdioServerParameters
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "ogr_mcp", "--profile",
                                          "compact"],
            cwd=str(_ROOT), env=_env())

        async def scenario():
            async with Client(params) as c:
                await c.call_tool("project_new", {"name": "stdio"})
                r = await c.call_tool("python_exec", {"code": _STRAY})
                after = await c.call_tool("project_summary", {})
                return r, after
        r, after = asyncio.run(scenario())
        out = r.structured_content
        assert out["ok"] and out["value"] == "42", out
        assert out["stdout"] == "hello from print\n"
        # The protocol survived: a call after the stray writes works.
        assert not after.is_error
        assert after.structured_content["name"] == "stdio"


class TestHttp:
    def _start(self, *args, env=None):
        port = _free_port()
        proc = subprocess.Popen(
            [sys.executable, "-m", "ogr_mcp", "--transport", "http",
             "--port", str(port), *args],
            cwd=str(_ROOT), env=env or _env(),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        url = f"http://127.0.0.1:{port}/mcp"
        import httpx2
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                httpx2.get(url, timeout=0.5)
                break
            except Exception:  # noqa: BLE001 - not up yet
                time.sleep(0.2)
        return proc, url

    def test_the_token_host_and_origin_are_enforced(self):
        if not _have_mcp():
            return
        import httpx2
        from mcp import Client
        from mcp.client.streamable_http import streamable_http_client

        proc, url = self._start(env=_env(OGR_MCP_TOKEN="s3cret-token"))
        try:
            body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list",
                    "params": {}}
            h = {"content-type": "application/json",
                 "accept": "application/json, text/event-stream"}
            ok = {**h, "authorization": "Bearer s3cret-token"}
            assert httpx2.post(url, json=body, headers=h).status_code == 401
            assert httpx2.post(url, json=body, headers={
                **h, "authorization": "Bearer wrong"}).status_code == 401
            assert httpx2.post(url, json=body, headers={
                **ok, "origin": "http://evil.example"}).status_code == 403
            assert httpx2.post(url, json=body, headers={
                **ok, "host": "evil.example"}).status_code == 421

            async def scenario():
                hc = httpx2.AsyncClient(headers={
                    "authorization": "Bearer s3cret-token"})
                async with Client(streamable_http_client(
                        url, http_client=hc)) as c:
                    return await c.call_tool("project_new", {"name": "h"})
            r = asyncio.run(scenario())
            assert not r.is_error and r.structured_content["name"] == "h"
        finally:
            proc.terminate()
            proc.wait(15)

    def test_no_network_without_a_token(self):
        if not _have_mcp():
            return
        for extra in ([], ["--no-auth"]):
            r = subprocess.run(
                [sys.executable, "-m", "ogr_mcp", "--transport", "http",
                 "--host", "0.0.0.0", "--port", str(_free_port()), *extra],
                cwd=str(_ROOT), env=_env(), capture_output=True, text=True,
                timeout=60)
            assert r.returncode == 2, (extra, r.stderr)


class TestTheCommandLine:
    def test_a_missing_sdk_says_what_to_install(self):
        code = ("import sys; sys.modules['mcp'] = None; "
                "from ogr_mcp.cli import main; sys.exit(main([]))")
        r = subprocess.run([sys.executable, "-c", code], cwd=str(_ROOT),
                           env=_env(), capture_output=True, text=True,
                           timeout=60)
        assert r.returncode == 3, r.stderr
        assert "ogr-slip2d[mcp]" in r.stderr

    def test_the_extra_and_the_command_are_declared(self):
        """What ``docs/mcp/`` tells a user to install must exist: the
        ``[mcp]`` extra with the SDK major that was audited, and the
        ``ogr-slip2d-mcp`` command pointing at this ``main``."""
        import tomllib
        data = tomllib.loads((_ROOT / "pyproject.toml").read_text(
            encoding="utf-8"))
        extra = data["project"]["optional-dependencies"]["mcp"]
        assert extra == ["mcp>=2.1,<3"], extra
        assert data["project"]["scripts"]["ogr-slip2d-mcp"] == \
            "ogr_mcp.cli:main"

    def test_the_package_imports_without_the_sdk(self):
        code = ("import sys; sys.modules['mcp'] = None; "
                "import ogr_mcp, ogr_mcp.cli, ogr_mcp.profiles, "
                "ogr_mcp.guide; print(ogr_mcp.__version__)")
        r = subprocess.run([sys.executable, "-c", code], cwd=str(_ROOT),
                           env=_env(), capture_output=True, text=True,
                           timeout=60)
        assert r.returncode == 0, r.stderr

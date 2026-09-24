# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
``ogr-slip2d-mcp`` — start the MCP server.

    ogr-slip2d-mcp --workdir C:\\proyectos                 # stdio (default)
    ogr-slip2d-mcp --profile compact                     # small local models
    ogr-slip2d-mcp --transport http --port 8765          # HTTP, token made
    ogr-slip2d-mcp --transport http --token-file tok.txt # HTTP, your token

Exit codes: 0 normal end, 2 a configuration the server refuses to run
with (a network host without a token), 3 the ``mcp`` SDK is missing.

Nothing is printed on standard output: over stdio that stream IS the
protocol. Messages go to standard error or to ``--log-file``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path


def _parse(argv):
    p = argparse.ArgumentParser(
        prog="ogr-slip2d-mcp",
        description="MCP server for OGR Slip2D (slope stability). stdio by "
                    "default; --transport http for Open WebUI, mcpo and "
                    "other HTTP clients.")
    p.add_argument("--transport", choices=("stdio", "http"),
                   default="stdio")
    p.add_argument("--host", default="127.0.0.1",
                   help="HTTP: interface to listen on (default 127.0.0.1)")
    p.add_argument("--port", type=int, default=8765, help="HTTP: port")
    p.add_argument("--token", default=None,
                   help="HTTP: bearer token (prefer --token-file or the "
                        "OGR_MCP_TOKEN variable: a token on the command "
                        "line is visible to other users)")
    p.add_argument("--token-file", default=None,
                   help="HTTP: file holding the bearer token")
    p.add_argument("--no-auth", action="store_true",
                   help="HTTP on loopback only: no token. python_exec is "
                        "always available, so this lets any local program "
                        "run code as you.")
    p.add_argument("--allow-origin", action="append", default=[],
                   help="HTTP: an extra allowed Origin (repeatable)")
    p.add_argument("--profile", choices=("full", "compact"), default=None,
                   help="Tool set: full (default) or compact for small "
                        "models; also OGR_MCP_PROFILE")
    p.add_argument("--toolsets", default=None,
                   help="Comma-separated toolsets instead of a profile: "
                        "core,model,settings,analysis,view,history,python")
    p.add_argument("--workdir", default=None,
                   help="Folder relative paths are resolved against")
    p.add_argument("--max-wait", type=float, default=None,
                   help="Longest a tool waits for an analysis before "
                        "returning its job_id (default 50 s)")
    p.add_argument("--max-jobs", type=int, default=1,
                   help="Analyses allowed to run at the same time")
    p.add_argument("--log-file", default=None)
    p.add_argument("--version", action="store_true")
    return p.parse_args(argv)


def _token(args):
    if args.token:
        return args.token.strip(), "command line"
    if args.token_file:
        return Path(args.token_file).read_text(encoding="utf-8").strip(), \
            "file"
    env = os.environ.get("OGR_MCP_TOKEN", "").strip()
    if env:
        return env, "environment"
    return None, None


def main(argv=None) -> int:
    args = _parse(sys.argv[1:] if argv is None else argv)
    from . import __version__
    if args.version:
        print(f"ogr-slip2d-mcp {__version__}", file=sys.stderr)
        return 0

    # ``basicConfig`` refuses ``filename`` and ``stream`` together even when
    # one of them is None, so exactly one is passed.
    target = ({"filename": args.log_file} if args.log_file
              else {"stream": sys.stderr})
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(message)s", **target)
    log = logging.getLogger("ogr_mcp")

    try:
        import mcp  # noqa: F401
    except ImportError:
        print("The MCP SDK is not installed. Install the extra:\n"
              '    pip install "ogr-slip2d[mcp]"', file=sys.stderr)
        return 3

    from .security import http_app, is_loopback, new_token

    token = None
    if args.transport == "http":
        token, source = _token(args)
        loop = is_loopback(args.host)
        if args.no_auth and not loop:
            print(f"--no-auth is only allowed on a loopback host, not "
                  f"{args.host!r}.", file=sys.stderr)
            return 2
        if token is None and not loop:
            print(f"Refusing to listen on {args.host!r} without a token: "
                  f"python_exec lets anyone who reaches this port run code. "
                  f"Give --token-file or OGR_MCP_TOKEN.", file=sys.stderr)
            return 2
        if token is None and not args.no_auth:
            token = new_token()
            print(f"ogr-slip2d-mcp: generated bearer token (give it to "
                  f"your client as 'Authorization: Bearer <token>'):\n"
                  f"{token}", file=sys.stderr, flush=True)
        elif token is not None:
            log.info("bearer token from %s", source)

    profile = args.profile or os.environ.get("OGR_MCP_PROFILE") or "full"
    toolsets = [t.strip() for t in args.toolsets.split(",")] \
        if args.toolsets else None

    from ogr_api import Workspace

    from .server import DEFAULT_MAX_WAIT_S, build_server

    ws = Workspace(workdir=args.workdir, max_concurrent_jobs=args.max_jobs)
    try:
        server = build_server(ws, profile=profile, toolsets=toolsets,
                              max_wait=args.max_wait or DEFAULT_MAX_WAIT_S)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    log.info("ogr-slip2d-mcp %s, profile %s, %d tools, transport %s",
             __version__, profile, len(server._ogr_tools), args.transport)
    try:
        if args.transport == "stdio":
            server.run("stdio")
        else:
            import uvicorn
            app = http_app(server, host=args.host, port=args.port,
                           token=None if args.no_auth else token,
                           extra_origins=args.allow_origin)
            uvicorn.run(app, host=args.host, port=args.port,
                        log_level="warning")
    except KeyboardInterrupt:
        pass
    finally:
        ws.shutdown()
    return 0

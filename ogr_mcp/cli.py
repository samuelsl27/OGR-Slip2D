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
    p.add_argument("--public-url", default=None,
                   help="HTTP: the https:// address the server is reached "
                        "at from outside (a tunnel or reverse proxy). Turns "
                        "on OAuth 2.1, which ChatGPT needs; access is "
                        "approved with the server's token")
    p.add_argument("--oauth-redirect", action="append", default=[],
                   help="With --public-url: an extra allowed OAuth "
                        "redirect URI (repeatable; ChatGPT's and Claude's "
                        "are allowed already)")
    p.add_argument("--tls-cert", default=None,
                   help="HTTP: serve HTTPS directly with this certificate "
                        "(PEM)")
    p.add_argument("--tls-key", default=None,
                   help="HTTP: the key of --tls-cert (PEM)")
    p.add_argument("--profile", choices=("full", "compact"), default=None,
                   help="Tool set: full (default) or compact for small "
                        "models; also OGR_MCP_PROFILE")
    p.add_argument("--toolsets", default=None,
                   help="Comma-separated toolsets instead of a profile: "
                        "core,model,settings,analysis,loads,supports,search,"
                        "annotations,files,groundwater,statistics,view,"
                        "history,python")
    p.add_argument("--attach", nargs="?", const="auto", default=None,
                   metavar="PID",
                   help="Drive a RUNNING window instead of a model of "
                        "your own: the one whose Tools > Agent bridge (MCP) "
                        "is on, or the one with this process id when "
                        "several are")
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
    public = None
    if args.transport != "http" and (args.public_url or args.tls_cert
                                     or args.tls_key or args.oauth_redirect):
        print("--public-url, --tls-cert, --tls-key and --oauth-redirect "
              "are HTTP options.", file=sys.stderr)
        return 2
    if args.transport == "http":
        # v0.1.204 (F4b) — the rules of exposure, before anything listens.
        if bool(args.tls_cert) != bool(args.tls_key):
            print("--tls-cert and --tls-key go together.", file=sys.stderr)
            return 2
        for f in (args.tls_cert, args.tls_key):
            if f and not Path(f).is_file():
                print(f"{f} does not exist.", file=sys.stderr)
                return 2
        if args.oauth_redirect and not args.public_url:
            print("--oauth-redirect is only read with --public-url.",
                  file=sys.stderr)
            return 2
        if args.public_url:
            from urllib.parse import urlparse
            u = urlparse(args.public_url)
            if u.scheme not in ("https", "http") or not u.netloc or \
                    (u.scheme == "http" and not is_loopback(u.hostname or "")):
                print("--public-url must be an https:// address (http:// "
                      "only for a loopback address, to test).",
                      file=sys.stderr)
                return 2
            if args.no_auth:
                print("--no-auth cannot go with --public-url: that would "
                      "put python_exec on the Internet.", file=sys.stderr)
                return 2
            public = args.public_url.rstrip("/")
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
        if public is not None and token is not None and len(token) < 32:
            # v0.1.204 (F4b) — on the Internet the token is the only thing
            # between a stranger and python_exec, and the approval page lets
            # anyone try it: it has to be long. The generated one has 43.
            print("--public-url needs a token of at least 32 characters "
                  "(or none, and one is generated).", file=sys.stderr)
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

    from ogr_api import OgrApiError, Workspace

    from .server import DEFAULT_MAX_WAIT_S, build_server

    backend = None
    if args.attach is not None:
        # F4 (v0.1.203): forward every tool to a running window.
        from ogr_api.bridge import BridgeClient
        try:
            pid = None if args.attach == "auto" else int(args.attach)
            backend = BridgeClient.attach(pid)
        except (OgrApiError, OSError, ValueError) as exc:
            print(f"Cannot attach to a window: {exc}", file=sys.stderr)
            return 2
        log.info("attached to window pid %s (%s)", backend.pid,
                 backend.window)
    ws = None if backend is not None else Workspace(
        workdir=args.workdir, max_concurrent_jobs=args.max_jobs)
    oauth = None
    if public is not None:
        from .oauth import OwnerApprovalProvider
        oauth = OwnerApprovalProvider(token, resource=f"{public}/mcp",
                                      approve_url=f"{public}/approve",
                                      extra_redirects=args.oauth_redirect)
        log.info("OAuth on: approve access at %s/approve with the server "
                 "token", public)
    try:
        server = build_server(ws, profile=profile, toolsets=toolsets,
                              max_wait=args.max_wait or DEFAULT_MAX_WAIT_S,
                              backend=backend, oauth=oauth,
                              public_url=public)
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
                           extra_origins=args.allow_origin,
                           public_url=public, tls=bool(args.tls_cert))
            tls = ({"ssl_certfile": args.tls_cert,
                    "ssl_keyfile": args.tls_key} if args.tls_cert else {})
            uvicorn.run(app, host=args.host, port=args.port,
                        log_level="warning", **tls)
    except KeyboardInterrupt:
        pass
    finally:
        if ws is not None:
            ws.shutdown()
        if backend is not None:
            backend.close()
    return 0

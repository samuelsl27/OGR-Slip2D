# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The live bridge's wire format, discovery and client (spec 008, F4).

The window of OGR Slip2D can serve its own model to an agent: *Tools >
Agent bridge (MCP)* starts a TCP server on 127.0.0.1 inside the window
(``ogr_gui.agent_bridge``), and ``ogr-slip2d-mcp --attach`` forwards every
tool call to it as ``(operation, kwargs)`` — the same registry the headless
server calls, so the bridge is only a change of transport.

Why loopback TCP with a token, and not a named pipe: the client below is
plain ``socket`` on every system; nothing leaves the machine; and a token
is required on every connection, in the spirit of the rule that the HTTP
server never runs without one (AGENTS.md). The token is in the discovery
file, readable by the user alone.

Wire format: one JSON object per line, UTF-8. Bytes (a PNG) travel as
``{"__bytes__": base64}``.

* client → server, first line: ``{"hello": PROTOCOL, "token": ...}``;
  answer ``{"hello": PROTOCOL, "ok": true, "window": title, "pid": n}``.
* then ``{"id": n, "op": name, "kwargs": {...}}``; answer
  ``{"id": n, "ok": true, "result": ...}`` or
  ``{"id": n, "ok": false, "error": {"code", "message", "hint",
  "details"}}``, which the client raises as the same ``OgrApiError``.

Only the standard library: ``ogr_api`` imports neither Qt nor ``mcp``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import base64
import json
import math
import os
import socket
import threading
import time
from pathlib import Path
from typing import Optional

from .errors import (Busy, Conflict, InvalidArgument, JobFailed,
                     NotConfigured, NotFound, OgrApiError)

PROTOCOL = "ogr-slip2d-bridge/1"
#: Longest line either side accepts (a large PNG, base64, fits well).
MAX_LINE = 64 * 1024 * 1024

_ERRORS = {cls.code: cls for cls in (NotFound, InvalidArgument, Conflict,
                                     NotConfigured, Busy, JobFailed)}


# ----------------------------------------------------------------------
# Encoding
# ----------------------------------------------------------------------
def _to_wire(obj):
    if isinstance(obj, (bytes, bytearray)):
        return {"__bytes__": base64.b64encode(bytes(obj)).decode("ascii")}
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {str(k): _to_wire(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_wire(v) for v in obj]
    return obj


def _from_wire(obj):
    if isinstance(obj, dict):
        if set(obj) == {"__bytes__"}:
            return base64.b64decode(obj["__bytes__"])
        return {k: _from_wire(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_wire(v) for v in obj]
    return obj


def encode(message: dict) -> bytes:
    """One message as a UTF-8 JSON line."""
    return (json.dumps(_to_wire(message), ensure_ascii=False,
                       allow_nan=False, default=str) + "\n").encode("utf-8")


def decode(line: bytes) -> dict:
    """One JSON line back into a message."""
    return _from_wire(json.loads(line.decode("utf-8")))


def error_to_dict(exc: BaseException) -> dict:
    """An exception as the wire's error object."""
    if isinstance(exc, OgrApiError):
        return exc.to_dict()
    return {"code": "E_INTERNAL",
            "message": f"{type(exc).__name__}: {exc}"}


def error_from_dict(d: dict) -> OgrApiError:
    """The wire's error object as the ``OgrApiError`` it was."""
    cls = _ERRORS.get(d.get("code"), OgrApiError)
    exc = cls(d.get("message", "error"), hint=d.get("hint"),
              details=d.get("details"))
    if cls is OgrApiError:
        exc.code = d.get("code", "E_INTERNAL")
    return exc


# ----------------------------------------------------------------------
# Discovery
# ----------------------------------------------------------------------
def bridge_dir() -> Path:
    """Where a running window announces its bridge (one file per pid)."""
    override = os.environ.get("OGR_BRIDGE_DIR")
    return Path(override) if override else \
        Path.home() / ".ogr-slip2d" / "bridges"


def write_discovery(port: int, token: str, title: str) -> Path:
    """Announce this process's bridge; the file is the user's alone."""
    folder = bridge_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{os.getpid()}.json"
    data = {"protocol": PROTOCOL, "port": int(port), "token": token,
            "pid": os.getpid(), "title": title, "started": time.time()}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:  # pragma: no cover - Windows keeps the home private
        pass
    os.replace(tmp, path)
    return path


def remove_discovery(path: Optional[Path] = None) -> None:
    target = path or (bridge_dir() / f"{os.getpid()}.json")
    try:
        target.unlink()
    except OSError:
        pass


def _answers(port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout):
            return True
    except OSError:
        return False


def live_bridges() -> list:
    """The windows whose bridge answers, newest first. A file whose port
    no longer answers is a window that closed without saying so; it is
    removed."""
    out = []
    folder = bridge_dir()
    if not folder.is_dir():
        return out
    for f in folder.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if data.get("protocol") != PROTOCOL:
            continue
        if _answers(data.get("port", 0)):
            out.append(data)
        else:
            remove_discovery(f)
    out.sort(key=lambda d: -float(d.get("started", 0)))
    return out


def find_bridge(pid: Optional[int] = None) -> dict:
    """The bridge to attach to: ``pid``'s, or the only one running."""
    bridges = live_bridges()
    if pid is not None:
        for b in bridges:
            if int(b.get("pid", -1)) == int(pid):
                return b
        raise NotFound(f"No OGR Slip2D window with pid {pid} has its "
                       f"agent bridge on.",
                       hint=_listing(bridges))
    if not bridges:
        raise NotFound("No OGR Slip2D window has its agent bridge on.",
                       hint="In the window: Tools > Agent bridge (MCP).")
    if len(bridges) > 1:
        raise Conflict("Several OGR Slip2D windows have their bridge on; "
                       "say which with --attach PID.",
                       hint=_listing(bridges))
    return bridges[0]


def _listing(bridges) -> str:
    if not bridges:
        return "None is running."
    return "Running: " + "; ".join(f"pid {b['pid']} ({b.get('title', '')})"
                                   for b in bridges)


# ----------------------------------------------------------------------
# Client
# ----------------------------------------------------------------------
class BridgeClient:
    """A connection to one window's bridge; ``call`` is thread-safe."""

    def __init__(self, port: int, token: str, *,
                 timeout: float = 600.0) -> None:
        self._sock = socket.create_connection(("127.0.0.1", int(port)),
                                              timeout=10.0)
        self._sock.settimeout(timeout)
        self._file = self._sock.makefile("rwb")
        self._lock = threading.Lock()
        self._next = 0
        hello = self._exchange({"hello": PROTOCOL, "token": token})
        if not hello.get("ok"):
            self.close()
            raise error_from_dict(hello.get("error") or {
                "code": "E_INTERNAL", "message": "handshake refused"})
        self.window = hello.get("window", "")
        self.pid = hello.get("pid")

    @classmethod
    def attach(cls, pid: Optional[int] = None) -> "BridgeClient":
        info = find_bridge(pid)
        return cls(info["port"], info["token"])

    def _exchange(self, message: dict) -> dict:
        self._file.write(encode(message))
        self._file.flush()
        line = self._file.readline(MAX_LINE)
        if not line:
            raise ConnectionError("The OGR Slip2D window closed the "
                                  "bridge.")
        return decode(line)

    def call(self, op: str, /, **kwargs):
        """Run ``op`` in the window; raises the operation's own error."""
        with self._lock:
            self._next += 1
            answer = self._exchange({"id": self._next, "op": op,
                                     "kwargs": kwargs})
        if answer.get("ok"):
            return answer.get("result")
        raise error_from_dict(answer.get("error") or {})

    def close(self) -> None:
        for thing in (self._file, self._sock):
            try:
                thing.close()
            except OSError:
                pass

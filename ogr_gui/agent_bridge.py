# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The live bridge: an agent drives THIS window (spec 008, F4).

*Tools > Agent bridge (MCP)* starts a TCP server on 127.0.0.1 with a random
token and announces it in a discovery file (``ogr_api.bridge``);
``ogr-slip2d-mcp --attach`` finds it and forwards every tool call here as
``(operation, kwargs)``, to the same operations registry the headless
server calls. What makes it "live":

* the model is the window's (``provider=lambda: window.project``), so New
  and Open in the window are seen at once;
* the undo stack is the window's: an agent's edit is one step of *Edit >
  Undo*, and the user's steps are the agent's to undo too;
* everything runs on the Qt thread — the server delivers through the event
  loop — so an agent's edit and the user's never race, and the canvas is
  redrawn after each edit;
* an analysis the agent runs is shown in the results panel and on the
  canvas, as a Compute would be;
* ``project_new`` and ``project_open`` open in the window, and refuse while
  the window has unsaved changes;
* ``model_render(source="window")`` is a capture of the real canvas.

While the window is computing (its own Compute or drawdown sweep, which use
the live model on another thread) an edit answers ``Busy``.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import hmac
import os
import secrets
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject
from PySide6.QtNetwork import QHostAddress, QTcpServer

from ogr_api.bridge import (MAX_LINE, PROTOCOL, decode, encode,
                            error_to_dict, remove_discovery,
                            write_discovery)
from ogr_api.errors import Conflict, InvalidArgument


class WindowHost:
    """What the operations ask of the window in bridge mode
    (``Workspace.host``). Every method runs on the Qt thread."""

    def __init__(self, window) -> None:
        self.window = window
        self.handle_id: Optional[str] = None

    # -- state ----------------------------------------------------------
    def busy(self) -> Optional[str]:
        w = self.window
        for name in ("worker", "sweep_worker"):
            t = getattr(w, name, None)
            try:
                if t is not None and t.isRunning():
                    return ("The window is computing; an edit now would "
                            "change the model under it.")
            except RuntimeError:        # a deleted QThread
                continue
        return None

    def unsaved(self) -> bool:
        return bool(getattr(self.window.project, "is_dirty", False))

    # -- after the operations -------------------------------------------
    def after_edit(self) -> None:
        w = self.window
        w.canvas.refresh_scene()
        w.refresh_action_availability()

    def after_save(self) -> None:
        w = self.window
        path = w.project.file_path
        w.setWindowTitle(f"OGR Slip2D v{w.VERSION} — "
                         f"{path.name if path else w.project.name}")

    def replace_project(self, project) -> None:
        """Open ``project`` in the window, as File > Open would, but never
        over unsaved changes (the window's prompt cannot be answered by an
        agent, and an agent does not get to discard the user's work)."""
        if self.unsaved():
            raise Conflict(
                "The window has unsaved changes.",
                hint="Save them first (project_save), or let the user "
                     "decide in the window.")
        w = self.window
        w._attach_project(project)
        w.terminal_dock.attach_context(w.project, w.canvas, w)
        w.command_stack.clear()
        project.is_dirty = False
        self.after_save()

    def show_analysis(self, results: dict, factor_report=None,
                      warnings=()) -> None:
        """Show an agent's analysis as the window shows a Compute."""
        w = self.window
        first = next((r for r in results.values() if r is not None), None)
        w.last_search_results = dict(results)
        w.last_search_result = first
        w.last_factor_report = factor_report
        w.last_compute_warnings = list(warnings)
        w.results_dock.show_result(first, factor_report)
        if first is not None:
            w.canvas.display_search_result(first)

    def capture(self, width: int, height: int) -> bytes:
        """The canvas as it is on screen, as PNG bytes."""
        from PySide6.QtCore import Qt

        pix = self.window.canvas.grab()
        if width and height:
            pix = pix.scaled(int(width), int(height),
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        data = QByteArray()
        buf = QBuffer(data)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        pix.save(buf, "PNG")
        buf.close()
        return bytes(data)


class AgentBridge(QObject):
    """The TCP server of the live bridge, owned by the main window."""

    def __init__(self, window) -> None:
        super().__init__(window)
        from ogr_api import Workspace

        self.window = window
        self.host = WindowHost(window)
        self.ws = Workspace()
        self.ws.host = self.host
        handle = self.ws.add(provider=lambda: window.project)
        handle.stack = window.command_stack
        self.host.handle_id = handle.id
        self.token = secrets.token_urlsafe(24)
        self._server = QTcpServer(self)
        self._server.newConnection.connect(self._on_connection)
        self._clients: dict = {}
        self.discovery = None

    # ------------------------------------------------------------------
    @property
    def port(self) -> int:
        return int(self._server.serverPort())

    @property
    def running(self) -> bool:
        return self._server.isListening()

    def start(self) -> int:
        if not self._server.listen(QHostAddress(QHostAddress.SpecialAddress
                                                .LocalHost), 0):
            raise RuntimeError(self._server.errorString())
        self.discovery = write_discovery(self.port, self.token,
                                         self.window.windowTitle())
        return self.port

    def stop(self) -> None:
        for sock in list(self._clients):
            try:
                sock.disconnectFromHost()
            except RuntimeError:
                pass
        self._clients.clear()
        self._server.close()
        remove_discovery(self.discovery)
        self.discovery = None
        self.ws.shutdown()

    # ------------------------------------------------------------------
    def _on_connection(self) -> None:
        while self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            self._clients[sock] = {"authed": False, "buf": bytearray()}
            sock.readyRead.connect(lambda s=sock: self._on_ready(s))
            sock.disconnected.connect(lambda s=sock: self._forget(s))

    def _forget(self, sock) -> None:
        self._clients.pop(sock, None)
        sock.deleteLater()

    def _on_ready(self, sock) -> None:
        state = self._clients.get(sock)
        if state is None:
            return
        state["buf"] += bytes(sock.readAll())
        if len(state["buf"]) > MAX_LINE:
            sock.disconnectFromHost()
            return
        while b"\n" in state["buf"]:
            line, _, rest = bytes(state["buf"]).partition(b"\n")
            state["buf"] = bytearray(rest)
            try:
                message = decode(line)
            except ValueError:
                sock.write(encode({"ok": False, "error": {
                    "code": "E_INVALID_ARGUMENT",
                    "message": "Not a JSON line."}}))
                continue
            sock.write(encode(self._answer(state, message)))
            sock.flush()
            if not state["authed"]:
                sock.disconnectFromHost()
                return

    def _answer(self, state: dict, message: dict) -> dict:
        if not state["authed"]:
            token = str(message.get("token", ""))
            if message.get("hello") != PROTOCOL or not hmac.compare_digest(
                    token.encode("utf-8"), self.token.encode("utf-8")):
                return {"hello": PROTOCOL, "ok": False, "error": {
                    "code": "E_UNAUTHORIZED",
                    "message": "Wrong protocol or token."}}
            state["authed"] = True
            # v0.1.207 — the MCP server's --workdir, so that a relative
            # path means the same folder whether the call runs there or
            # here. The last client to connect sets it.
            wd = message.get("workdir")
            if wd and Path(wd).is_dir():
                self.ws.workdir = Path(wd).resolve()
            return {"hello": PROTOCOL, "ok": True,
                    "window": self.window.windowTitle(),
                    "pid": os.getpid()}
        mid = message.get("id")
        try:
            op = message.get("op")
            kwargs = message.get("kwargs") or {}
            if not isinstance(op, str) or not isinstance(kwargs, dict):
                raise InvalidArgument("A request is {'id', 'op', "
                                      "'kwargs'}.")
            from ogr_api import call
            result = call(self.ws, op, **kwargs)
            return {"id": mid, "ok": True, "result": result}
        except Exception as exc:  # noqa: BLE001 - reported, with its type
            return {"id": mid, "ok": False, "error": error_to_dict(exc)}


# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Run Python the caller sends, and give back what it printed.

This is arbitrary code execution BY DESIGN — the owner's decision of
2026-09-24, for the cases no dedicated operation covers yet. What this
module guarantees is narrower and checkable:

* output is captured PER THREAD. ``contextlib.redirect_stdout`` swaps a
  process-wide ``sys.stdout``, so two scripts running at once (the server
  runs each call on its own worker thread) would each capture the other's
  prints. Here ``sys.stdout`` is replaced by a router only while at least
  one script runs, and the router sends each thread's writes to that
  thread's buffer, anything else to the stream that was there before;
* ``sys.stdout`` and ``sys.stderr`` are put back exactly when the last
  script ends (rule 5: a test must not leak global state);
* the last expression's value is returned, as in a REPL;
* an exception comes back as data, with its traceback, instead of
  propagating.

What it does NOT do: stop a script. A thread cannot be killed; a script
that never ends holds its model's lock until the process exits. That is
why analyses are jobs and scripts are not.

Over the stdio transport the stream "that was there before" is file
descriptor 1, which the MCP SDK has already pointed at stderr while it
serves — so a stray write from another thread cannot reach the protocol.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import ast
import io
import sys
import threading
import traceback

_MAX_OUT = 20_000
_MAX_REPR = 5_000

_lock = threading.Lock()
_depth = 0
_saved: tuple = ()
_buffers: dict[int, dict[str, io.StringIO]] = {}


class _Router(io.TextIOBase):
    """A stream that writes to the calling thread's buffer, if it has one."""

    def __init__(self, which: str, fallback) -> None:
        super().__init__()
        self._which = which
        self._fallback = fallback

    def write(self, s: str) -> int:
        bufs = _buffers.get(threading.get_ident())
        if bufs is not None:
            return bufs[self._which].write(s)
        return self._fallback.write(s) if self._fallback else len(s)

    def flush(self) -> None:
        if _buffers.get(threading.get_ident()) is None and self._fallback:
            try:
                self._fallback.flush()
            except (OSError, ValueError):
                pass

    @property
    def encoding(self):  # noqa: D401 - file-like protocol
        return getattr(self._fallback, "encoding", "utf-8")

    def isatty(self) -> bool:
        return False

    def writable(self) -> bool:
        return True


def _enter() -> dict[str, io.StringIO]:
    global _depth, _saved
    with _lock:
        if _depth == 0:
            _saved = (sys.stdout, sys.stderr)
            sys.stdout = _Router("out", _saved[0])
            sys.stderr = _Router("err", _saved[1])
        _depth += 1
    bufs = {"out": io.StringIO(), "err": io.StringIO()}
    _buffers[threading.get_ident()] = bufs
    return bufs


def _leave() -> None:
    global _depth
    _buffers.pop(threading.get_ident(), None)
    with _lock:
        _depth -= 1
        if _depth == 0:
            sys.stdout, sys.stderr = _saved


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [{len(text) - limit} more characters]"


def run_python(code: str, namespace: dict) -> dict:
    """Execute ``code`` in ``namespace``; never raises for the script's own
    errors.

    Returns ``{"ok", "stdout", "stderr", "value", "error"}``: ``value`` is
    the ``repr`` of the last expression (None if the script ends with a
    statement), ``error`` the formatted traceback when it raised.
    """
    if not isinstance(code, str):
        return {"ok": False, "stdout": "", "stderr": "", "value": None,
                "error": "code must be a string"}
    bufs = _enter()
    value = None
    error = None
    try:
        try:
            tree = ast.parse(code, mode="exec")
        except SyntaxError:
            error = traceback.format_exc(limit=0)
        else:
            last = None
            if tree.body and isinstance(tree.body[-1], ast.Expr):
                last = ast.Expression(tree.body.pop().value)
            try:
                exec(compile(tree, "<python_exec>", "exec"), namespace)
                if last is not None:
                    result = eval(compile(last, "<python_exec>", "eval"),
                                  namespace)
                    if result is not None:
                        value = _clip(repr(result), _MAX_REPR)
            except BaseException:  # noqa: BLE001 - returned as data
                error = traceback.format_exc()
    finally:
        _leave()
    return {"ok": error is None,
            "stdout": _clip(bufs["out"].getvalue(), _MAX_OUT),
            "stderr": _clip(bufs["err"].getvalue(), _MAX_OUT),
            "value": value,
            "error": _clip(error, _MAX_OUT) if error else None}

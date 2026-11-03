# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""D370 probe — only on the branch ``dev/d370-shutdown``, never on ``main``.

Since v0.1.276 the Linux CI dies after the totals: «QObject: shared QObject
was deleted directly» and SIGSEGV (139), with ``<no Python frame>``. The
runner of ``main`` ends with ``os._exit`` off Windows, so the crash is not
seen there. This branch ends the way it did up to v0.1.376 and calls
:func:`before_exit` first, which, by ``OGR_D370``:

* ``census`` — installs a Qt message handler that dumps the Python stack of
  every thread when the warning appears, and prints what is still alive:
  top-level widgets by class and Python-wrapped QObjects by class;
* ``byhand`` — the same, then deletes the top-level widgets ONE BY ONE with
  Python alive, printing each before it goes, so the warning lands right
  after the widget whose destruction raises it.
"""
from __future__ import annotations

import faulthandler
import gc
import os
import sys
from collections import Counter


def _say(text: str) -> None:
    sys.__stderr__.write(text + "\n")
    sys.__stderr__.flush()


def _handler(mode, ctx, msg) -> None:
    _say(f"[D370 Qt {mode}] {msg}")
    if "shared QObject" in msg:
        _say("[D370] Python stacks at the warning:")
        faulthandler.dump_traceback(file=sys.__stderr__, all_threads=True)
        try:
            _say(f"[D370] context: file={ctx.file} line={ctx.line} "
                 f"function={ctx.function} category={ctx.category}")
        except Exception as exc:  # the context may be empty in a release
            _say(f"[D370] context unreadable: {exc!r}")


def _census() -> None:
    from PySide6.QtCore import QObject
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        _say("[D370] no QApplication at exit")
        return
    tops = app.topLevelWidgets()
    c = Counter(f"{type(w).__module__}.{type(w).__name__}" for w in tops)
    _say(f"[D370] top-level widgets alive: {len(tops)}")
    for name, n in c.most_common():
        _say(f"[D370]   {n:5d} {name}")
    gc.unfreeze()
    objs = [o for o in gc.get_objects() if isinstance(o, QObject)]
    c = Counter(f"{type(o).__module__}.{type(o).__name__}" for o in objs)
    _say(f"[D370] Python-wrapped QObjects alive: {len(objs)}")
    for name, n in c.most_common(80):
        _say(f"[D370]   {n:5d} {name}")


def _by_hand() -> None:
    import shiboken6
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return
    # Only the windows with no parent: a popup menu is a top-level widget
    # too, but it belongs to its window and goes with it.
    tops = [w for w in app.topLevelWidgets() if w.parent() is None]
    for i, w in enumerate(tops):
        if not shiboken6.isValid(w):
            continue
        try:
            title = w.windowTitle()
        except Exception:
            title = "?"
        _say(f"[D370] deleting {i}/{len(tops)} {type(w).__module__}."
             f"{type(w).__name__} title={title!r} name={w.objectName()!r}")
        shiboken6.delete(w)
    _say("[D370] every top-level widget deleted by hand")


def before_exit() -> None:
    mode = os.environ.get("OGR_D370", "")
    if not mode:
        return
    try:
        from PySide6.QtCore import qInstallMessageHandler
    except Exception as exc:
        _say(f"[D370] no PySide6: {exc!r}")
        return
    qInstallMessageHandler(_handler)
    _say(f"[D370] mode {mode}: Qt message handler installed")
    _census()
    if mode == "byhand":
        _by_hand()
    _say("[D370] leaving through sys.exit")

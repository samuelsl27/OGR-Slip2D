# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""D370 probe of the PROGRAM, not the suite — only on ``dev/d370-shutdown``.

Starts OGR Slip2D through its real entry point (``ogr_gui.__main__.main``),
loads the demo, computes, opens Interpret, closes everything as a user
would, and leaves through the interpreter's normal shutdown. The exit code
says whether a user on Linux meets the crash the suite meets.

    python tests/_d370_app.py [--no-agent-bridge]
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)


def _say(text: str) -> None:
    print(f"[D370 app] {text}", flush=True)


def main() -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox
    import ogr_gui.__main__ as gm

    # A modal box would wait for ever without a screen.
    for name in ("information", "warning", "critical", "question"):
        setattr(QMessageBox, name, staticmethod(
            lambda *a, _n=name, **k: (_say(f"QMessageBox.{_n}: {a[2:3]}"),
                                      QMessageBox.Ok)[1]))

    def drive(win) -> None:
        app = QApplication.instance()
        try:
            win.act_load_demo()
            win.act_compute()
            res = getattr(win, "last_search_results", None)
            _say(f"computed: {sorted(res) if isinstance(res, dict) else res!r}")
            win.act_interpret()
            _say(f"interpret windows: {len(win.interpret_windows)}")
            for iw in list(win.interpret_windows):
                iw.close()
            win.project.is_dirty = False
            win.close()
        except Exception as exc:  # report it and still leave normally
            import traceback
            traceback.print_exc()
            _say(f"drive failed: {exc!r}")
        app.quit()

    start = gm.start_window

    def start_window(**kw):
        win = start(**kw)
        QTimer.singleShot(300, lambda: drive(win))
        return win

    gm.start_window = start_window
    rc = gm.main([sys.argv[0], *sys.argv[1:]])
    _say(f"app.exec returned {rc}")
    import _d370
    _d370.before_exit()
    return rc


if __name__ == "__main__":
    sys.exit(main())

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Entry point for the graphical application.

Run as:

    ogr-slip2d
    # or
    python -m ogr_gui
    python -m ogr_gui --no-agent-bridge     # without the agent bridge

v0.1.207 — the agent bridge (Tools > Agent bridge (MCP)) starts with the
window, by the owner's decision: whatever an AI client asks, if the program
is open the work is done there, where it is seen. It listens on 127.0.0.1
only, with a token, as it does when turned on by hand.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import sys

# v0.1.262 (D247) — nothing from Qt or the window at import time. A Grid
# Search started from *Compute* now splits across processes, and on Windows
# every child starts by re-importing the parent's main module: run as
# ``python -m ogr_gui``, that is this file, and its PySide6 and window
# imports cost each child 1.4 s before it did any work. They are imported
# where they are used.


def start_window(agent_bridge: bool = True):
    """The main window, shown, with its agent bridge on unless asked not
    to. Separate from :func:`main` so that it can be tested without
    entering the event loop; the tests that build a ``MainWindow`` directly
    get no bridge, which is what keeps them off the user's discovery
    folder."""
    from .main_window import MainWindow
    win = MainWindow()
    win.show()
    if agent_bridge:
        win._actions["agent_bridge"].setChecked(True)
        win._toggle_agent_bridge(True)
    return win


def apply_saved_preferences(app) -> None:
    """The language and the theme of the last session (v0.1.289, D290).

    BEFORE the window is built: its menus, toolbar and status bar take
    their texts from ``tr()`` once, so a language set afterwards would not
    reach them. With nothing saved, English and the light theme, as
    always. Tests that build a ``MainWindow`` directly never come here."""
    from .i18n import set_language
    from .themes import apply_theme
    from .user_prefs import saved_language, saved_theme
    lang = saved_language()
    if lang:
        set_language(lang)
    apply_theme(app, saved_theme() or "light")


def main(argv=None) -> int:
    import argparse
    import multiprocessing

    # v0.1.262 (D247) — a no-op unless this runs as a frozen executable,
    # where it is what keeps the grid's worker processes from starting a
    # second copy of the program instead of doing their work.
    multiprocessing.freeze_support()
    from PySide6.QtWidgets import QApplication

    argv = list(sys.argv if argv is None else argv)
    parser = argparse.ArgumentParser(prog="ogr-slip2d", add_help=False)
    parser.add_argument("--no-agent-bridge", action="store_true")
    opts, rest = parser.parse_known_args(argv[1:])
    app = QApplication([argv[0] if argv else "ogr-slip2d", *rest])
    app.setApplicationName("OGR Slip2D")
    app.setOrganizationName("OpenGeoRock Suite")
    app.setApplicationDisplayName("OGR Slip2D")
    apply_saved_preferences(app)

    win = start_window(agent_bridge=not opts.no_agent_bridge)  # noqa: F841
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

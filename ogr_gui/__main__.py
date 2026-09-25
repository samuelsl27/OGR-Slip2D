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

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from .themes import apply_theme


def start_window(agent_bridge: bool = True) -> MainWindow:
    """The main window, shown, with its agent bridge on unless asked not
    to. Separate from :func:`main` so that it can be tested without
    entering the event loop; the tests that build a ``MainWindow`` directly
    get no bridge, which is what keeps them off the user's discovery
    folder."""
    win = MainWindow()
    win.show()
    if agent_bridge:
        win._actions["agent_bridge"].setChecked(True)
        win._toggle_agent_bridge(True)
    return win


def main(argv=None) -> int:
    import argparse

    argv = list(sys.argv if argv is None else argv)
    parser = argparse.ArgumentParser(prog="ogr-slip2d", add_help=False)
    parser.add_argument("--no-agent-bridge", action="store_true")
    opts, rest = parser.parse_known_args(argv[1:])
    app = QApplication([argv[0] if argv else "ogr-slip2d", *rest])
    app.setApplicationName("OGR Slip2D")
    app.setOrganizationName("OpenGeoRock Suite")
    app.setApplicationDisplayName("OGR Slip2D")
    apply_theme(app, "light")

    win = start_window(agent_bridge=not opts.no_agent_bridge)  # noqa: F841
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

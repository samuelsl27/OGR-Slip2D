# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Entry point for the graphical application.

Run as:

    ogr-slip2d
    # or
    python -m ogr_gui

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from .themes import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("OGR Slip2D")
    app.setOrganizationName("OpenGeoRock Suite")
    app.setApplicationDisplayName("OGR Slip2D")
    apply_theme(app, "light")

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

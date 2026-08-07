# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Reusable GUI widgets (status bar, docks, side panels)."""
from .results_dock import ResultsDock
from .status_bar import OgrStatusBar
from .terminal import TerminalDock, TerminalWidget

__all__ = ["ResultsDock", "OgrStatusBar", "TerminalDock", "TerminalWidget"]

# v0.1.4
from .assign_materials_panel import AssignMaterialsPanel

__all__.append("AssignMaterialsPanel")

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Icon factory — single point of contact for all icons in the GUI.

Uses ``qtawesome`` (Font Awesome 6 + Material Design Icons) which is
licensed under OFL and MIT — both permissive and compatible with
GPL-3.0. All icons are vector, so they scale to any DPI and can be
recoloured dynamically.

Usage:

    from ogr_gui.resources.icons import icon
    btn.setIcon(icon("new_project"))

The central ``_CATALOG`` dict maps *semantic* icon keys (e.g.
``"zoom_window"``) to the underlying qtawesome identifier. To swap
icon fonts, only this file needs to change.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

# Semantic key → (qtawesome id, color override | None)
_CATALOG: dict[str, tuple[str, Optional[str]]] = {
    # --- File ---------------------------------------------------------
    "new_project":       ("fa6s.file-circle-plus", None),
    "open_project":      ("fa6s.folder-open", None),
    "save":              ("fa6s.floppy-disk", None),
    "save_as":           ("fa6s.file-arrow-down", None),
    "print":             ("fa6s.print", None),
    "print_report":      ("fa6s.file-pdf", None),
    "import_dxf":        ("fa6s.file-import", None),
    "export_dxf":        ("fa6s.file-export", None),
    "preferences":       ("fa6s.gear", None),
    # --- Edit ---------------------------------------------------------
    "undo":              ("fa6s.rotate-left", None),
    "redo":              ("fa6s.rotate-right", None),
    "copy":              ("fa6s.copy", None),
    "delete":            ("fa6s.trash", "#c0392b"),
    "delete_all":        ("fa6s.trash-can-arrow-up", "#c0392b"),
    # --- View ---------------------------------------------------------
    "zoom_all":          ("fa6s.expand", None),
    "zoom_in":           ("fa6s.magnifying-glass-plus", None),
    "zoom_out":          ("fa6s.magnifying-glass-minus", None),
    "zoom_window":       ("fa6s.vector-square", None),
    "pan":               ("fa6s.hand", None),
    "ruler":             ("fa6s.ruler-combined", None),
    "grid":              ("fa6s.border-all", None),
    "display_options":   ("fa6s.sliders", None),
    # --- Analysis -----------------------------------------------------
    "compute":           ("fa6s.calculator", "#2a7f2a"),
    "interpret":         ("fa6s.chart-line", "#1f6f9f"),
    "project_settings":  ("fa6s.gears", None),
    "info_viewer":       ("fa6s.circle-info", None),
    # --- Boundaries ---------------------------------------------------
    "ext_boundary":      ("fa6s.draw-polygon", "#2c2c2c"),
    "mat_boundary":      ("fa6s.shapes", "#8b4513"),
    "water_table":       ("fa6s.water", "#1e90ff"),
    "piezo_line":        ("fa6s.wave-square", "#4169e1"),
    "tension_crack":     ("fa6s.bolt-lightning", "#dc143c"),
    "boundary_delete":   ("fa6s.eraser", None),
    "move_vertex":       ("fa6s.arrows-up-down-left-right", None),
    "insert_vertex":     ("fa6s.circle-plus", None),
    "delete_vertex":     ("fa6s.circle-minus", None),
    # --- Loading ------------------------------------------------------
    "distributed_load":  ("fa6s.angles-down", "#d35400"),
    "line_load":         ("fa6s.arrow-down-long", "#d35400"),
    "seismic_load":      ("fa6s.tower-broadcast", "#7d3c98"),
    "delete_load":       ("fa6s.eraser", None),
    # --- Support ------------------------------------------------------
    "add_support":       ("fa6s.thumbtack", "#4b0082"),
    "support_pattern":   ("fa6s.table-cells", "#4b0082"),
    "delete_support":    ("fa6s.eraser", None),
    # --- Surfaces -----------------------------------------------------
    "surface_options":   ("fa6s.arrows-split-up-and-left", None),
    "auto_grid":         ("fa6s.border-all", None),
    "surface_3pts":      ("fa6s.circle-dot", None),
    "slope_limits":      ("fa6s.left-right", None),
    # --- Properties ---------------------------------------------------
    "define_materials":  ("fa6s.layer-group", None),
    "define_support":    ("fa6s.screwdriver-wrench", None),
    "define_crack":      ("fa6s.bolt-lightning", None),
    "assign":            ("fa6s.paintbrush", None),
    # --- Tools --------------------------------------------------------
    "add_text":          ("fa6s.font", None),
    "add_line":          ("fa6s.slash", None),
    "add_arrow":         ("fa6s.arrow-right-long", None),
    "measure":           ("fa6s.ruler", None),
    "add_polyline":      ("fa6s.pen-nib", None),
    "add_polygon":       ("fa6s.draw-polygon", None),
    "add_rectangle":     ("fa6s.square", None),
    "add_circle":        ("fa6s.circle", None),
    "add_image":         ("fa6s.image", None),
    "dim_angle":         ("fa6s.compass", None),
    "dim_length":        ("fa6s.arrows-left-right", None),
    "dim_vertical":      ("fa6s.arrows-up-down", None),
    "dim_horizontal":    ("fa6s.arrows-left-right", None),
    "material_table":    ("fa6s.table", None),
    "support_table":     ("fa6s.table", None),
    "hydraulic_table":   ("fa6s.table", None),
    # --- Help ---------------------------------------------------------
    "help":              ("fa6s.circle-question", None),
    "about":             ("fa6s.info", None),
    # --- Status bar ---------------------------------------------------
    "snap":              ("fa6s.crosshairs", None),
    "ortho":             ("fa6s.square", None),
    "osnap":             ("fa6s.arrows-to-dot", None),
    "language":          ("fa6s.language", None),
    "theme":             ("fa6s.palette", None),
}


# ----------------------------------------------------------------------
# Defensive fallback
# ----------------------------------------------------------------------
# qtawesome versions differ slightly in which Font Awesome 6 identifiers
# they ship (some old names were renamed in FA6, some new names require
# qtawesome ≥ 1.3). Rather than crashing the whole GUI when a single
# icon name fails to resolve, we catch the exception and fall back to a
# simple always-present icon. This mirrors what QGIS does internally
# and keeps the UI usable across environments.

_FALLBACK_IDS: tuple[str, ...] = ("fa6s.circle", "fa6s.square", "fa5s.circle")


def _safe_qta_icon(qta, qta_id: str, color: Optional[str]):
    """Try to build an icon; on failure, fall back to a generic one."""
    kwargs = {"color": color} if color else {}
    try:
        return qta.icon(qta_id, **kwargs)
    except Exception:  # noqa: BLE001  — any qtawesome lookup error
        for fb in _FALLBACK_IDS:
            try:
                return qta.icon(fb, color="#888888")
            except Exception:  # noqa: BLE001
                continue
        from PySide6.QtGui import QIcon
        return QIcon()


# ----------------------------------------------------------------------
@lru_cache(maxsize=256)
def icon(key: str, color: Optional[str] = None):
    """Return a ``QIcon`` for the given semantic key.

    Args:
        key: a key from ``_CATALOG``. Unknown keys return a default gear.
        color: override the catalog colour (hex string).

    Robust against qtawesome version drift — if the underlying icon ID
    is missing in the installed qtawesome build, a fallback icon is
    returned so the GUI keeps working.
    """
    try:
        import qtawesome as qta
    except ImportError:
        # Graceful fallback — return an empty icon so the GUI still runs
        from PySide6.QtGui import QIcon
        return QIcon()

    qta_id, default_color = _CATALOG.get(key, ("fa6s.gear", None))
    chosen = color or default_color
    return _safe_qta_icon(qta, qta_id, chosen)


def has(key: str) -> bool:
    return key in _CATALOG

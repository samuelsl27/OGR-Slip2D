# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
How big a dialog opens, and a scroll area that never scrolls sideways.

v0.1.315 (D293). Two dialogs opened at a size written for English and
cut their Spanish buttons and notes: the transient one at 520 px when its
row of buttons needed 1156, the hydraulic one with its parameters squeezed
into a 190 px column that scrolled sideways.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QScrollArea, QWidget


def open_at_content_size(dialog: QWidget, at_least: QSize) -> None:
    """Resize ``dialog`` to what its content asks for, never below
    ``at_least`` and never beyond the screen it opens on.

    The layout still keeps it from shrinking under its minimum, so this
    only decides where it starts.
    """
    size = dialog.sizeHint().expandedTo(at_least)
    screen = dialog.screen()
    if screen is not None:
        size = size.boundedTo(screen.availableGeometry().size())
    dialog.resize(size)


class VerticalScrollArea(QScrollArea):
    """A scroll area as wide as its content: it scrolls up and down only.

    ``QScrollArea`` asks for almost no width, so a layout short of room
    gives it a sliver and its content scrolls sideways. This one asks for
    the width of the widget it holds plus the vertical bar, so its column
    is never narrower than the labels and buttons inside.
    """

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        hint = super().minimumSizeHint()
        inner = self.widget()
        if inner is None:
            return hint
        frame = 2 * self.frameWidth()
        bar = self.verticalScrollBar().sizeHint().width()
        return QSize(inner.minimumSizeHint().width() + bar + frame,
                     hint.height())

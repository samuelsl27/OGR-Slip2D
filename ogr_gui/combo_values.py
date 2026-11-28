# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A combo box that shows a stored value it has no option for, and keeps it.

v0.1.522 (D462). The settings dialog chose a combo's option with
``max(0, combo.findData(value))``: a value the combo did not list gave −1,
``max`` turned it into the first option, and ``apply()`` wrote that option
back on OK, even if the user never touched the combo. A ``.ogr`` saved by a
later version (``slice_angles = "optimized_global"`` was such a value for
0.1.470) lost its value the first time anyone accepted the dialog, to change
something on another page. The interslice forces were worse: their first
option is «Effective» while the setting's default is ``total``.

The reader of the project keeps such a value (``from_dict`` drops unknown
KEYS, not values), and the analysis decides what to do with it: Sarma is
left out with its note, an unknown drawdown procedure is refused. So the
dialog is the only place that must not change it silently. Here the value
gets an entry of its own, «Unknown value: <value>», in italics and with a
tip that says this version does not know it; it is selected, so ``apply()``
writes it back as it was unless the user picks another option.

With a value the combo lists, nothing is added: a project of this version
sees exactly the options it always saw.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox

from ogr_gui.i18n import tr


def select_stored_value(combo: QComboBox, value) -> int:
    """Select the option of ``combo`` whose data is ``value`` and return its
    index. A value the combo has no option for gets an entry of its own at
    the end, marked as unknown, and that entry is selected: what the
    project holds is shown, and kept, rather than replaced by the first
    option. ``None`` (nothing stored) selects the first option, as before."""
    i = combo.findData(value)
    if i < 0 and value is not None:
        combo.addItem(tr("Unknown value: %s") % (value,), value)
        i = combo.count() - 1
        font = combo.font()
        font.setItalic(True)
        combo.setItemData(i, font, Qt.FontRole)
        combo.setItemData(i, tr(
            "This version of the program does not know this value. It is "
            "kept as it is unless you choose another option."),
            Qt.ToolTipRole)
    combo.setCurrentIndex(max(0, i))
    return combo.currentIndex()

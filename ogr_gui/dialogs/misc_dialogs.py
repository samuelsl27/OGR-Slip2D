# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
About dialog & Compute progress dialog.

The About dialog reads the software identity from a central config so
that renaming or re-branding the product is a one-file change, as
requested in the spec.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from ogr_gui.i18n import tr

SOFTWARE_NAME = "OGR Slip2D"
SUITE_NAME = "OpenGeoRock Suite (OGR)"
# v0.1.59 — the version is read from the SOURCE TREE first and from the
# installed metadata only as a fallback.
#
# The order matters. An editable install freezes its metadata at install
# time, so a developer who bumps pyproject.toml and forgets to reinstall
# would see the OLD number in the About dialog — which is exactly the
# place someone checks which build they are running. Reading the tree
# first means the answer always matches the code being edited; for a
# proper wheel there is no adjacent pyproject.toml and the metadata takes
# over.
import re as _re
from pathlib import Path as _Path

VERSION = "unknown"
try:
    _toml = (_Path(__file__).resolve().parents[2]
             / "pyproject.toml").read_text(encoding="utf-8")
    VERSION = _re.search(r'version\s*=\s*"([^"]+)"', _toml).group(1)
except Exception:  # noqa: BLE001
    try:
        from importlib.metadata import version as _pkg_version
        VERSION = _pkg_version("ogr-slip2d")
    except Exception:  # noqa: BLE001
        VERSION = "unknown"
BUILD_DATE = "2026-08"
COPYRIGHT = "© 2026 Samuel Sáez López"
AUTHOR = "Samuel Sáez López"
INSTITUTION = "Universidad Politécnica de Cartagena (UPCT)"
WEBSITE = "https://opengeorock.org"
LICENSE = "AGPL-3.0-or-later"


# ----------------------------------------------------------------------
class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("About OGR Slip2D"))
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)

        title = QLabel(f"<h2>{SOFTWARE_NAME}</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(f"<i>{SUITE_NAME}</i>")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        info = QTextBrowser()
        info.setOpenExternalLinks(True)
        info.setHtml(
            tr("\n            <table>\n            <tr><td><b>Version:</b></td><td>{0}</td></tr>\n            <tr><td><b>Build:</b></td><td>{1}</td></tr>\n            <tr><td><b>License:</b></td><td>{2}</td></tr>\n            <tr><td><b>Developer:</b></td><td>{3}</td></tr>\n            <tr><td><b>Institution:</b></td><td>{4}</td></tr>\n            <tr><td><b>Website:</b></td><td><a href='{5}'>{6}</a></td></tr>\n            </table>\n            <hr>\n            <p><b>{7}</b> is an open-source 2D slope-stability\n            analysis tool based on the Limit Equilibrium Method (LEM).\n            It is part of the <b>{8}</b>, a modular family of\n            geotechnical analysis programs developed as part of a PhD\n            research project at {9}.</p>\n            <p>{10}, released under the <b>GNU Affero General\n            Public License v3.0 or later</b>.</p>\n            <p>You may use this software freely, including for commercial\n            engineering work. If you modify it and let others use your\n            version remotely over a network, you must offer them its\n            source. There is no warranty of any kind: results must be\n            checked against independent calculations before being relied\n            on.</p>\n            ").format(VERSION, BUILD_DATE, LICENSE, AUTHOR, INSTITUTION, WEBSITE, WEBSITE, SOFTWARE_NAME, SUITE_NAME, INSTITUTION, COPYRIGHT)
        )
        layout.addWidget(info)

        btn = QDialogButtonBox(QDialogButtonBox.Close)
        btn.rejected.connect(self.reject)
        btn.accepted.connect(self.accept)
        layout.addWidget(btn)


# ----------------------------------------------------------------------
class ComputeProgressDialog(QDialog):
    """Modal progress dialog for surface-search operations."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Computing..."))
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)

        self.lbl_status = QLabel(tr("Computing..."))
        layout.addWidget(self.lbl_status)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        layout.addWidget(self.bar)

        self.btn_cancel = QPushButton(tr("Cancel"))
        layout.addWidget(self.btn_cancel)
        self.btn_cancel.clicked.connect(self.reject)
        self.cancelled = False
        self.btn_cancel.clicked.connect(lambda: setattr(self, "cancelled", True))

    def update_progress(self, done: int, total: int) -> None:
        if total <= 0:
            return
        pct = int(100 * done / total)
        self.bar.setValue(pct)
        self.lbl_status.setText(f"{tr('Computing...')} {done}/{total}")


class TaskProgressDialog(ComputeProgressDialog):
    """The progress of a calculation that runs off the window's thread
    (v0.1.365, D348, ``ogr_gui.background.run_task``).

    Window-modal, so the model cannot be edited while another thread reads
    it, and it does NOT close until the calculation has returned: Esc and the
    title bar's button would otherwise hand the window back with the thread
    still running, which is how *Compute*'s Cancel let a recompute start on
    top of a running one (D362). There is no Cancel button until a
    calculation can actually be stopped — a button that does nothing is the
    one thing worse than none (rule 7).
    """

    def __init__(self, parent=None, title: str = "") -> None:
        super().__init__(parent)
        from PySide6.QtCore import Qt
        if title:
            self.setWindowTitle(title)
        self.setWindowModality(Qt.ApplicationModal)
        # busy until a calculation that counts its steps says how many
        self.bar.setRange(0, 0)
        self.btn_cancel.hide()
        self._finished = False

    def update_progress(self, done: int, total: int) -> None:
        if total > 0 and self.bar.maximum() == 0:
            self.bar.setRange(0, 100)
        super().update_progress(done, total)

    def finish(self) -> None:
        """Close it: the calculation has returned."""
        self._finished = True
        self.accept()

    def reject(self) -> None:                   # Esc, the title bar's button
        if self._finished:
            super().reject()

    def closeEvent(self, event) -> None:        # noqa: N802 - Qt's name
        if self._finished:
            super().closeEvent(event)
        else:
            event.ignore()

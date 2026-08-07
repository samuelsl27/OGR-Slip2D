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
            f"""
            <table>
            <tr><td><b>Version:</b></td><td>{VERSION}</td></tr>
            <tr><td><b>Build:</b></td><td>{BUILD_DATE}</td></tr>
            <tr><td><b>License:</b></td><td>{LICENSE}</td></tr>
            <tr><td><b>Developer:</b></td><td>{AUTHOR}</td></tr>
            <tr><td><b>Institution:</b></td><td>{INSTITUTION}</td></tr>
            <tr><td><b>Website:</b></td><td><a href='{WEBSITE}'>{WEBSITE}</a></td></tr>
            </table>
            <hr>
            <p><b>{SOFTWARE_NAME}</b> is an open-source 2D slope-stability
            analysis tool based on the Limit Equilibrium Method (LEM).
            It is part of the <b>{SUITE_NAME}</b>, a modular family of
            geotechnical analysis programs developed as part of a PhD
            research project at {INSTITUTION}.</p>
            <p>{COPYRIGHT}, released under the <b>GNU Affero General
            Public License v3.0 or later</b>.</p>
            <p>You may use this software freely, including for commercial
            engineering work. If you modify it and let others use your
            version remotely over a network, you must offer them its
            source. There is no warranty of any kind: results must be
            checked against independent calculations before being relied
            on.</p>
            """
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

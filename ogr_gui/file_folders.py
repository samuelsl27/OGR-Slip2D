# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Where the file dialogs of a window start (v0.1.418, D355).

Every ``QFileDialog`` of the main window and of Interpret was given ``""``
as its folder, so each one opened in the program's working folder, and
*Generate Report* proposed a bare file name, resolved against it too.

Now a dialog starts in the folder last used in that window during this
session; before any, in the folder of the project if it has been saved, and
otherwise in the user's Documents. The folder is remembered in the window
and not in the saved preferences, on purpose: every test that picks a file
would otherwise leave the settings file changed.
"""
from __future__ import annotations

import os

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QFileDialog


def start_folder(window) -> str:
    """The folder a file dialog of ``window`` starts in."""
    last = getattr(window, "_last_folder", None)
    if last and os.path.isdir(last):
        return last
    path = getattr(getattr(window, "project", None), "file_path", None)
    if path:
        folder = os.path.dirname(os.path.abspath(os.fspath(path)))
        if os.path.isdir(folder):
            return folder
    return (QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
            or os.path.expanduser("~"))


def remember_folder(window, path) -> None:
    """The folder of a file the user picked, for the window's next dialog."""
    if path:
        window._last_folder = os.path.dirname(os.path.abspath(os.fspath(path)))


def get_open_file_name(window, title: str, filters: str, parent=None):
    """``QFileDialog.getOpenFileName`` started in :func:`start_folder`;
    ``parent`` is the dialog's owner when it is not the window itself."""
    path, chosen = QFileDialog.getOpenFileName(
        parent or window, title, start_folder(window), filters)
    remember_folder(window, path)
    return path, chosen


def get_save_file_name(window, title: str, filters: str, name: str = "",
                       parent=None):
    """``QFileDialog.getSaveFileName`` started in :func:`start_folder`, with
    ``name`` proposed inside it; ``parent`` as in
    :func:`get_open_file_name`."""
    folder = start_folder(window)
    path, chosen = QFileDialog.getSaveFileName(
        parent or window, title,
        os.path.join(folder, name) if name else folder, filters)
    remember_folder(window, path)
    return path, chosen

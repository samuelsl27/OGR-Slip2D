# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.289 (D290) — the application preferences that outlive a session: the
language and the theme.

Until this version *Preferences* changed the language for the session and
said «Restart the application to fully apply translations»; nothing stored
the choice, so the restart came back in English and the advice was false.
The menus, the toolbar and the status bar are built once, with ``tr()``, so
the language has to be set BEFORE the window is built: ``ogr_gui.__main__``
asks this module first thing (the owner's decision: save and restart, no
live retranslation).

Where it is kept: ``QSettings("OpenGeoRock Suite", "OGR Slip2D")`` — the
user's registry on Windows, a local file elsewhere; nothing leaves the
machine. If ``OGR_SETTINGS_DIR`` is set, an INI file in that folder instead:
the test runner points it at an empty folder of its own, so no test ever
reads or writes the user's preferences (rule 5).

A stored value this version does not know (a language or a theme that no
longer exists) is ignored, not trusted.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import QSettings

ORGANIZATION = "OpenGeoRock Suite"
APPLICATION = "OGR Slip2D"


def _settings() -> QSettings:
    folder = os.environ.get("OGR_SETTINGS_DIR")
    if folder:
        return QSettings(os.path.join(folder, "ogr-slip2d.ini"),
                         QSettings.Format.IniFormat)
    return QSettings(ORGANIZATION, APPLICATION)


def _read(key: str, allowed) -> Optional[str]:
    value = _settings().value(key)
    return value if isinstance(value, str) and value in allowed else None


def saved_language() -> Optional[str]:
    """The language chosen in a previous session, or None."""
    from .i18n import available_languages
    return _read("language", available_languages())


def save_language(code: str) -> None:
    s = _settings()
    s.setValue("language", code)
    s.sync()


def saved_theme() -> Optional[str]:
    """The theme chosen in a previous session, or None."""
    from .themes import THEMES
    return _read("theme", THEMES)


def save_theme(name: str) -> None:
    s = _settings()
    s.setValue("theme", name)
    s.sync()

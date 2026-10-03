# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Help Topics: the online documentation, in the language of the interface.

v0.1.250 — until this version *Help Topics* (F1) opened a modal box with a
repository address and one line about the terminal, and the interpretation
window had a box of its own with a different line: no help at all, and in
two versions. The documentation lives on the project's site, in English and
in Spanish — the two languages of this interface — so F1 opens the page in
the language the user is reading, from both windows, through
:func:`open_documentation`.

**Why this is not the network call AGENTS.md forbids.** The program sends
nothing and fetches nothing: it hands a public address to the system's
browser, and only when the user asks for help. Nothing is opened at
start-up, nothing leaves the machine on its own, and *Check for Updates*
still contacts no server.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from .i18n import current_language, tr

#: The documentation index of the site, per interface language: ONE place
#: for both addresses, so the two windows cannot disagree. A language without
#: a page of its own gets the English one, which is also the page the site
#: declares as its ``x-default``.
DOCS_URLS = {
    "es": "https://opengeorock.org/es/docs/index.html",
    "en": "https://opengeorock.org/docs/index.html",
}
_FALLBACK_LANGUAGE = "en"


def documentation_url(language=None) -> str:
    """The documentation page for ``language``, the active one by default."""
    lang = current_language() if language is None else language
    return DOCS_URLS.get(lang, DOCS_URLS[_FALLBACK_LANGUAGE])


def _open_url(url: str) -> bool:
    """Hand ``url`` to the system browser; whether it was accepted.

    A module-level function on purpose and looked up at call time: the tests
    replace it, so that no test run ever opens a browser.
    """
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    return bool(QDesktopServices.openUrl(QUrl(url)))


def open_documentation(window=None) -> bool:
    """Open the documentation and say so on ``window``'s status bar.

    Returns whether the browser accepted the address. When it did not —
    no browser registered, a locked-down machine — the status bar gives the
    address, so it can still be typed by hand. Never modal: a dialog blocks a
    test run for good (AGENTS.md), and a missing browser is not worth one.
    """
    url = documentation_url()
    try:
        opened = _open_url(url)
    except Exception:  # noqa: BLE001 - a missing browser must not kill a window
        opened = False
    bar = getattr(window, "statusBar", None)
    if callable(bar):
        if opened:
            message = tr("Opening the documentation in your browser: %s") % url
        else:
            message = tr("No browser could be opened; the documentation is "
                         "at %s") % url
        bar().showMessage(message, 15000)
    return opened

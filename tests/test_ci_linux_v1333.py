# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.333 (D338b) — the DXF import dialog keeps its boxes whole with a
larger font.

The CI of 0.1.332 failed on its three Linux runners in the dialog census of
D293 (``test_dialogs_fit_v1315``): at its minimum size *Import DXF* left its
two tolerance boxes at 26 px of the 27 they ask for. On Windows the census
passed, so it went unseen until the push. The cause is D321's: the preview
note wraps, and Qt does not add the height a wrapped label asks for at the
minimum width to the window's minimum. The dialog was not among the
thirteen that ``hold_wrapped_height`` was put on.

What differs on Linux is the font, and that can be reproduced here. With
the application font half a point larger, the same census measured the two
boxes 1 to 3 px short on 0.1.332 (+0.5, +1, +1.5 and +2 points); with the
filter, none. The invariant: at every one of those sizes, no box of the
dialog is shorter than its minimum, opened or shrunk to its minimum. The
font is put back afterwards, so nothing leaks to the next file (rule 5).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import QApplication  # noqa: F401
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


@_requires_qt
class TestTheImportDialogWithALargerFont:

    def test_no_box_is_squeezed(self):
        import test_dialogs_fit_v1315 as fit
        from PySide6.QtWidgets import QApplication
        w = fit._window()
        app = QApplication.instance()
        base = app.font()
        bad = []
        try:
            for extra in (0.5, 1.5):
                font = type(base)(base)
                font.setPointSizeF(base.pointSizeF() + extra)
                app.setFont(font)
                with fit._spanish_with("light") as a, fit._no_modals():
                    got = fit._measure(a, fit._census(w)["DxfImportDialog"])
                assert got is not None, extra
                _size, cut, squeezed = got
                if cut or squeezed:
                    bad.append((extra, cut, squeezed))
        finally:
            app.setFont(base)
            fit._done(w)
        assert bad == [], bad

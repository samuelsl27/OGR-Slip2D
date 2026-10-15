# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.314 (D305) — the Block Search panel of *Surface Options* reads the
crest of the model it was opened on.

``SurfaceOptionsDialog._build_block_panel`` called
``model_crest_is_on_the_right(project)`` with ``project`` a name the method
never had. Every call raised ``NameError`` and an ``except Exception`` turned
it into "crest on the right" whatever the slope. The flag only words the note
under the projection angles (``rules.block_angle_notes``), so a slope whose
crest is on the left was told the limits of the other side: an admissible
angle flagged, an inadmissible one not. What the dialog stores never
depended on it.

The demo slope is that case: its ground is higher on the left (y = 25 at
x = 0, 15 at x = 50), so its crest is on the LEFT by geometry, whatever the
declared failure direction. Its mirror image is the control.

The invariants:

* with the crest on the left, a left projection of 200° to 220° goes outside
  95°–175° and is said; a right one of −60° to −30° is inside −85°–85° and is
  not;
* with the crest on the right (the mirror), the other way round;
* the note is exactly what ``block_angle_notes`` says for the crest of the
  model, so the panel and the rule cannot drift apart;
* a project with no External boundary opens the dialog (the rule falls back
  to the declared direction);
* OK with nothing touched writes the search settings it found, on both
  slopes (QUÉ NO SE PUEDE MOVER).
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

_MISSING = object()

_LEFT_OUTSIDE_IF_CREST_LEFT = (200.0, 220.0)
_RIGHT_OUTSIDE_IF_CREST_RIGHT = (-60.0, -30.0)


@contextlib.contextmanager
def _swap(owner, name, value):
    raw = (owner.__dict__.get(name, _MISSING) if isinstance(owner, type)
           else getattr(owner, name))
    setattr(owner, name, value)
    try:
        yield
    finally:
        if raw is _MISSING:
            delattr(owner, name)
        else:
            setattr(owner, name, raw)


@contextlib.contextmanager
def _no_modals():
    from PySide6.QtWidgets import QDialog, QMessageBox

    def modal(*a, **k):
        raise AssertionError("a modal window")

    with contextlib.ExitStack() as stack:
        stack.enter_context(_swap(QDialog, "exec", modal))
        for name in ("information", "warning", "critical", "question"):
            stack.enter_context(_swap(QMessageBox, name,
                                      staticmethod(modal)))
        yield


def _demo(mirrored=False):
    """The demo slope, or its mirror image about x = 25."""
    from ogr_core.geometry import Vertex
    from ogr_core.geometry import scale as g_scale
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    w.act_load_demo()
    p = w.project
    if mirrored:
        p.boundaries[:] = [g_scale(b, Vertex(25.0, 0.0), -1.0, 1.0)
                           for b in p.boundaries]
        p.invalidate_regions_cache()
    s = p.settings.search
    (s.block_left_start_angle_deg,
     s.block_left_end_angle_deg) = _LEFT_OUTSIDE_IF_CREST_LEFT
    (s.block_right_start_angle_deg,
     s.block_right_end_angle_deg) = _RIGHT_OUTSIDE_IF_CREST_RIGHT
    p.is_dirty = False
    return w, p


def _done(w):
    w.project.is_dirty = False
    w.close()


def _panel(project):
    from ogr_gui.dialogs.grid_dialogs import SurfaceOptionsDialog
    with _no_modals():
        d = SurfaceOptionsDialog(project, None)
    return d


def _sides_said(d):
    """Which projections the note under the angles talks about."""
    from ogr_gui.i18n import tr
    if d._b_angle_note.isHidden():
        return set()
    text = d._b_angle_note.text()
    return {side for side, label in (("left", "Left projection"),
                                     ("right", "Right projection"))
            if tr(label) in text}


class TestTheCrestOfTheModel:
    def test_the_demo_has_its_crest_on_the_left_and_its_mirror_on_the_right(
            self):
        """The premise of the two tests below, measured rather than
        assumed."""
        from ogr_slip2d.failure_direction import model_crest_is_on_the_right
        for mirrored, right in ((False, False), (True, True)):
            w, p = _demo(mirrored)
            try:
                assert model_crest_is_on_the_right(p) is right
            finally:
                _done(w)

    def test_crest_on_the_left(self):
        w, p = _demo()
        try:
            d = _panel(p)
            assert d._b_crest_on_right is False
            assert _sides_said(d) == {"left"}
            d.deleteLater()
        finally:
            _done(w)

    def test_crest_on_the_right(self):
        w, p = _demo(mirrored=True)
        try:
            d = _panel(p)
            assert d._b_crest_on_right is True
            assert _sides_said(d) == {"right"}
            d.deleteLater()
        finally:
            _done(w)

    def test_the_note_is_the_rules_for_the_crest_of_the_model(self):
        from types import SimpleNamespace

        from ogr_core.project.rules import block_angle_notes
        from ogr_slip2d.failure_direction import model_crest_is_on_the_right
        for mirrored in (False, True):
            w, p = _demo(mirrored)
            try:
                d = _panel(p)
                s = p.settings.search
                angles = SimpleNamespace(**{
                    k: getattr(s, k) for k in d._BLOCK_ANGLE_BOXES})
                expected = {n.side for n in block_angle_notes(
                    angles, model_crest_is_on_the_right(p))}
                assert _sides_said(d) == expected, mirrored
                d.deleteLater()
            finally:
                _done(w)


class TestAnyModelOpens:
    def test_a_project_with_no_external_boundary(self):
        from ogr_core.project import Project
        from ogr_core.project.units import FailureDirection
        from ogr_slip2d.failure_direction import crest_is_on_the_right
        QApplication.instance() or QApplication([])
        p = Project("empty")
        # declared left to right, so the crest is on the LEFT: the old
        # "crest on the right" cannot pass this by coincidence
        p.settings.units.failure_direction = FailureDirection.LEFT_TO_RIGHT
        d = _panel(p)
        assert crest_is_on_the_right(p) is False
        assert d._b_crest_on_right is False
        d.deleteLater()

    def test_ok_with_nothing_touched_writes_what_it_found(self):
        for mirrored in (False, True):
            w, p = _demo(mirrored)
            try:
                before = json.dumps(p.to_dict()["settings"], sort_keys=True,
                                    default=str)
                d = _panel(p)
                with _no_modals():
                    d.accept()
                after = json.dumps(p.to_dict()["settings"], sort_keys=True,
                                   default=str)
                assert after == before, mirrored
                d.deleteLater()
            finally:
                _done(w)

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.91 — the slice panel's three buttons, and the one rule about arrows.

WHAT INVARIANT THIS PROTECTS: that the panel never shows an interslice force
for a method that did not compute one.

Copy, Zoom Slice and Hide Geometry move no number; they are conveniences and
they are tested as such — the button exists, it is reachable, and it does what
its label says. The interslice part is different, and is why this file has a
docstring longer than its subject deserves.

Bishop Simplified, Janbu and Ordinary do not form interslice forces at all:
Bishop assumes the interslice shear is zero, Janbu applies a correction in its
place, Ordinary ignores them. Spencer, GLE and Lowe-Karafiath SOLVE for the
interslice inclination and publish it as ``details["boundary_ratios"]``.

So the panel decides by asking for that datum, never by matching a method name.
Two reasons, and the second is the one that matters:

* a method added later that solves λ gets the arrows without anyone editing a
  list, and one that does not can never be handed numbers it never computed;
* drawing an arrow for Bishop would be drawing the solver's ASSUMPTION as if it
  were a result. That is exactly the mistake v0.1.82 removed from the line of
  thrust, and it is worth not making twice.

When the datum is absent the panel says so in words, which is a different thing
from leaving a blank: a blank reads as "no data", and the truth is "this method
does not have this concept".

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _ej1():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_slide_validation_ej1 import _ej1_project
    return _ej1_project()


def _result(method_cls):
    """A converged result on the Ej_1 reference circle."""
    from ogr_slip2d.search import GridSearch
    from ogr_slip2d.surface import SlipCircle
    ev = GridSearch(method=method_cls(), num_slices=25, min_area=0.0)
    return ev.evaluate_circle(
        _ej1(), SlipCircle(centre_x=88.0, centre_y=70.5, radius=47.2124436))


class TestTheArrowRuleIsAboutTheDatum:
    def test_the_three_methods_that_solve_it_publish_the_ratios(self):
        from ogr_gui.interpret_window import _SliceDataDock
        from ogr_slip2d import GLEMorgensternPrice, LoweKarafiath, Spencer
        for cls in (Spencer, GLEMorgensternPrice, LoweKarafiath):
            res = _result(cls)
            assert res is not None and res.is_valid, cls.DISPLAY_NAME
            assert _SliceDataDock.solves_interslice(res), cls.DISPLAY_NAME

    def test_the_methods_that_do_not_are_refused(self):
        from ogr_gui.interpret_window import _SliceDataDock
        from ogr_slip2d import (BishopSimplified, JanbuSimplified,
                                OrdinaryFellenius)
        for cls in (BishopSimplified, JanbuSimplified, OrdinaryFellenius):
            res = _result(cls)
            assert res is not None and res.is_valid, cls.DISPLAY_NAME
            assert not _SliceDataDock.solves_interslice(res), cls.DISPLAY_NAME

    def test_it_asks_the_datum_and_not_a_list_of_names(self):
        """Source-level, because the property above only survives as long
        as nobody 'clarifies' it into a tuple of method ids."""
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "ogr_gui"
               / "interpret_window.py").read_text(encoding="utf-8")
        body = src.split("def solves_interslice")[1].split("\n    @")[0]
        assert "boundary_ratios" in body, body
        for name in ("spencer", "bishop", "METHOD_ID", "method_id"):
            assert name not in body, name

    def test_a_method_without_the_datum_gets_no_numbers(self):
        from ogr_gui.interpret_window import _SliceDataDock
        from ogr_slip2d import BishopSimplified
        res = _result(BishopSimplified)
        s = res.slices[5]
        for name in ("E", "X"):
            for side in (0, 1):
                assert _SliceDataDock._inter(res, s, name, side) == "—"

    def test_a_method_with_the_datum_gets_real_numbers(self):
        from ogr_gui.interpret_window import _SliceDataDock
        from ogr_slip2d import Spencer
        res = _result(Spencer)
        s = res.slices[5]
        got = [_SliceDataDock._inter(res, s, n, k)
               for n in ("E", "X") for k in (0, 1)]
        assert all(v != "—" for v in got), got
        assert any(isinstance(v, float) and v != 0.0 for v in got), got

    def test_the_panel_says_so_in_words(self):
        """A blank reads as "no data"; the truth is "no such concept"."""
        from ogr_gui.interpret_window import _SliceDataDock
        from ogr_slip2d import BishopSimplified, Spencer
        no = _SliceDataDock._inter_status(_result(BishopSimplified))
        yes = _SliceDataDock._inter_status(_result(Spencer))
        assert no not in ("—", ""), no
        assert no != yes, (no, yes)


class TestTheButtons:
    def _dock_with_a_slice(self):
        from ogr_gui.interpret_window import _SliceDataDock
        from ogr_slip2d import Spencer
        _app()
        dock = _SliceDataDock()
        res = _result(Spencer)
        dock.show_slice(res.slices[5], res)
        return dock, res

    def test_copy_and_zoom_need_a_slice(self):
        from ogr_gui.interpret_window import _SliceDataDock
        _app()
        dock = _SliceDataDock()
        assert not dock.btn_copy.isEnabled()
        assert not dock.btn_zoom.isEnabled()
        # Hiding the model is about the model, not about a slice.
        assert dock.btn_geometry.isEnabled()

    def test_showing_a_slice_enables_them(self):
        dock, _res = self._dock_with_a_slice()
        assert dock.btn_copy.isEnabled() and dock.btn_zoom.isEnabled()

    def test_clearing_disables_them_again(self):
        dock, _res = self._dock_with_a_slice()
        dock.clear_slice()
        assert not dock.btn_copy.isEnabled()
        assert dock.current() == (None, None)

    def test_the_clipboard_text_is_tab_separated_pairs(self):
        dock, _res = self._dock_with_a_slice()
        text = dock.as_tsv()
        lines = [l for l in text.split("\n") if "\t" in l]
        assert len(lines) > 15, len(lines)
        for line in lines:
            assert line.count("\t") == 1, line
        # Section headers carry no value and therefore no tab.
        assert any("\t" not in l for l in text.split("\n"))

    def test_the_clipboard_text_carries_the_values_on_screen(self):
        dock, _res = self._dock_with_a_slice()
        text = dock.as_tsv()
        shown = dock.table.item(1, 1).text()      # Slice Number
        assert shown in text, (shown, text[:200])

    def test_copy_actually_reaches_the_clipboard(self):
        from PySide6.QtWidgets import QApplication
        dock, _res = self._dock_with_a_slice()
        dock.copy_to_clipboard()
        cb = QApplication.clipboard()
        if cb is None:
            return                      # no clipboard offscreen; not a failure
        assert cb.text() == dock.as_tsv()

    def test_the_geometry_button_toggles_its_own_label(self):
        from ogr_gui.i18n import tr
        dock, _res = self._dock_with_a_slice()
        assert dock.btn_geometry.text() == tr("Hide Geometry")
        dock.btn_geometry.setChecked(True)
        assert dock.btn_geometry.text() == tr("Show Geometry")
        dock.btn_geometry.setChecked(False)
        assert dock.btn_geometry.text() == tr("Hide Geometry")

    def test_the_geometry_button_reports_its_state(self):
        dock, _res = self._dock_with_a_slice()
        seen = []
        dock.geometry_hidden_changed.connect(seen.append)
        dock.btn_geometry.setChecked(True)
        dock.btn_geometry.setChecked(False)
        assert seen == [True, False], seen

    def test_zoom_asks_the_window_rather_than_doing_it(self):
        """The dock owns the button, the window owns the canvas."""
        dock, _res = self._dock_with_a_slice()
        seen = []
        dock.zoom_requested.connect(lambda: seen.append(1))
        dock.btn_zoom.click()
        assert seen == [1], seen


class TestEveryLabelIsTranslated:
    """Rule 2, on the strings this version added."""

    _NEW = ("Copy", "Zoom Slice", "Hide Geometry", "Show Geometry",
            "Copy the table to the clipboard",
            "Centre the view on the selected slice",
            "Show only the selected slice, for a clean capture",
            "─ Interslice forces ─", "Resolved by this method",
            "E left (kN)", "E right (kN)", "X left (kN)", "X right (kN)",
            "no — this method does not resolve them")

    def test_they_all_have_a_spanish_entry(self):
        from ogr_gui.i18n import _DICTS
        es = _DICTS.get("es", {})
        missing = [s for s in self._NEW if s not in es]
        assert not missing, missing

    def test_the_translations_are_not_the_english(self):
        from ogr_gui.i18n import _DICTS
        es = _DICTS.get("es", {})
        same = [s for s in self._NEW
                if s in es and es[s] == s and not s.startswith("─")]
        assert not same, same

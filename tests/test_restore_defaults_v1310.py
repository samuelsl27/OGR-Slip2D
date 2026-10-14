# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.310 (D309) — *Restore Defaults* in Project Settings restores what its
pages show, and writes it on Apply or OK.

It replaced the whole ``ProjectSettings`` with a fresh one, at once. The
pages show 72 of its 152 fields, and the other 80 went too, with nothing on
screen saying so:

* all 72 search options: the grid and the slope limits drawn on the
  canvas, the axis, the optimisation, Block Search… The ticket counted 9
  and believed a Search page showed 5; the class existed but was never in
  the dialog's list of pages, and it is gone;
* the back analysis (4 fields);
* the stages and the initial state of a transient;
* the seed of the statistics and the date the project was created.

The invariants:

* Restore writes nothing; Apply and OK write the defaults of the fields
  the pages show, and no other field;
* every field ends either where it was or at its default, never a third
  value, and what goes back is exactly what the pages' own ``apply``
  write, each page at least one field (rule 7: a page whose ``apply`` were
  not reached would restore nothing and pass);
* the part of the settings each page edits is the settings or one of their
  sections, which is what Restore relies on to point it at the copy;
* through the window, Restore and OK is one undo step that undo takes back,
  and Restore and Cancel leaves none;
* after Restore the pages show the copy: the Transient page counts the
  stages that are kept.
"""
from __future__ import annotations

import contextlib
import copy
import dataclasses
import enum
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

_MISSING = object()


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
    """A modal dialog or message box fails the test instead of waiting for
    ever without a screen."""
    from PySide6.QtWidgets import QDialog, QMessageBox

    def modal(*a, **k):
        raise AssertionError("a modal window")

    with contextlib.ExitStack() as stack:
        stack.enter_context(_swap(QDialog, "exec", modal))
        for name in ("information", "warning", "critical", "question"):
            stack.enter_context(_swap(QMessageBox, name,
                                      staticmethod(modal)))
        yield


def _window():
    from ogr_gui.i18n import set_language
    from ogr_gui.main_window import MainWindow
    QApplication.instance() or QApplication([])
    set_language("en")
    w = MainWindow()
    w.act_load_demo()
    w.project.is_dirty = False
    return w


def _done(w):
    w.project.is_dirty = False
    w.close()


def _json(p):
    return json.dumps(p.to_dict(), sort_keys=True, default=str)


_DIALOGS: list = []


def _dialog(settings, project=None):
    from ogr_gui.dialogs.project_settings_dialog import ProjectSettingsDialog
    QApplication.instance() or QApplication([])
    d = ProjectSettingsDialog(settings, None, project=project)
    _DIALOGS.append(d)
    return d


def _leaves(obj, prefix=""):
    """``{"section.field": value}`` for every leaf of the settings."""
    if dataclasses.is_dataclass(obj):
        out = {}
        for f in dataclasses.fields(obj):
            out.update(_leaves(getattr(obj, f.name), prefix + f.name + "."))
        return out
    return {prefix[:-1]: obj}


def _set(obj, path, value):
    *parts, last = path.split(".")
    for p in parts:
        obj = getattr(obj, p)
    setattr(obj, last, value)


def _perturb(path, v):
    """A value of the same kind that is not the default."""
    if path == "groundwater.transient_stages":
        # the Transient page reads its entries
        return [{"time": 5.0, "calculate_sf": True, "label": "p"}]
    if isinstance(v, bool):
        return not v
    if isinstance(v, int):
        return v + 7
    if isinstance(v, float):
        return v + 0.123
    if isinstance(v, str):
        return v + "_x"
    if v is None:
        return 1.5
    if isinstance(v, list):
        return list(v) + ["zz"]
    if isinstance(v, dict):
        return dict(v, zz=1)
    if isinstance(v, enum.Enum):
        members = list(type(v))
        return members[(members.index(v) + 1) % len(members)]
    raise AssertionError((path, v))


def _perturbed():
    """A ProjectSettings with every one of its leaves off its default."""
    from ogr_core.project import ProjectSettings
    s = ProjectSettings()
    for path, v in _leaves(ProjectSettings()).items():
        _set(s, path, _perturb(path, v))
    return s


#: Fields no page shows: what the old Restore wiped (D309). Set in the
#: reproduction to values that are not their defaults.
_HIDDEN = {
    "search.grid_x_min": 12.0, "search.grid_x_max": 30.0,
    "search.grid_y_min": 25.0, "search.grid_y_max": 40.0,
    "search.slope_limit_left": 5.0, "search.slope_limit_right": 45.0,
    "search.axis_x": 20.0, "search.axis_y": 30.0,
    "search.optimize_max_iterations": 123,
    "back_analysis.target_fos": 1.7,
    "groundwater.transient_stages": [
        {"time": 10.0, "calculate_sf": True, "label": "first"},
        {"time": 20.0, "calculate_sf": False, "label": "second"}],
    "groundwater.transient_initial_bcs": {"captured": "before the stages"},
    "statistics.seed": 99,
    "summary.date_created": "2026-10-14",
}

#: One field of each page, set off its default.
_SHOWN = {
    "max_materials": 33,                            # General
    "methods.num_slices": 77,                       # Methods
    "groundwater.pore_fluid_unit_weight": 10.0,     # Groundwater
    "groundwater.transient_tolerance": 1.0e-3,      # Transient
    "statistics.num_samples": 77,                   # Statistics
    "random_numbers.seed": 1234,                    # Random Numbers
    "design_standard.enabled": True,                # Design Standard
    "advanced.check_m_alpha": False,                # Advanced
    "seismic.compute_ky": True,                     # Seismic
    "summary.author": "Someone",                    # Project Summary
}


def _reproduction(s):
    for path, v in list(_HIDDEN.items()) + list(_SHOWN.items()):
        _set(s, path, copy.deepcopy(v))
    s.groundwater.set_advanced_option("transient")


# ----------------------------------------------------------------------
class TestRestoreWritesWhatThePagesShow:
    def test_the_reproduction(self):
        """The demo, with a grid, limits and an axis drawn, a transient
        with two stages and its initial state, and one field of each page
        changed: Restore writes nothing, and Apply puts back the ten fields
        of the pages and leaves the hidden ones alone."""
        from ogr_core.project import ProjectSettings
        w = _window()
        try:
            s = w.project.settings
            _reproduction(s)
            before = _json(w.project)
            d = _dialog(s, w.project)
            told = []
            d.settings_applied.connect(lambda: told.append(1))
            with _no_modals():
                d._defaults()
            assert _json(w.project) == before
            assert told == []
            with _no_modals():
                d._apply()
            assert told == [1]
            got = _leaves(s)
            fresh = _leaves(ProjectSettings())
            for path, v in _HIDDEN.items():
                assert got[path] == v, path
            for path in _SHOWN:
                assert got[path] == fresh[path], path
            # the switch is on the Groundwater page, so it goes back; the
            # stages it would run, which no page shows, stay
            assert s.groundwater.transient is False
        finally:
            _done(w)

    def test_every_field_ends_where_it_was_or_at_its_default(self):
        """All 152 leaves off their defaults: after Restore and Apply each
        one is either untouched or at its default, and the ones at their
        default are exactly what the pages' own apply writes."""
        from ogr_core.project import ProjectSettings
        from ogr_gui.dialogs import project_settings_dialog as M
        fresh = ProjectSettings()
        default = _leaves(fresh)
        s = _perturbed()
        start = _leaves(s)
        d = _dialog(s)
        with _no_modals():
            d._defaults()
            d._apply()
        end = _leaves(s)
        assert end.keys() == default.keys()
        third = {p: end[p] for p in end
                 if end[p] != start[p] and end[p] != default[p]}
        assert not third, third
        restored = {p for p in end if end[p] != start[p]}

        # what each page writes, on its own (rule 7: at least one field)
        written = set()
        for label, cls_name in d._PAGES:
            page = d._make_page(cls_name, fresh)
            target = _perturbed()
            page.s = M._part_of(target, fresh, page.s)
            page.apply()
            page.deleteLater()
            mine = {p for p, v in _leaves(target).items() if v != start[p]}
            assert mine, label
            assert all(_leaves(target)[p] == default[p] for p in mine), label
            written |= mine
        assert restored == written
        for path in _HIDDEN:
            assert path not in restored, path
        assert not any(p.startswith("search.") for p in restored)

    def test_each_page_edits_the_settings_or_one_of_their_sections(self):
        """What Restore relies on to point a page at the copy. A page that
        kept a nested section would make ``_part_of`` raise, not write in
        the wrong place."""
        from ogr_core.project import ProjectSettings
        from ogr_gui.dialogs import project_settings_dialog as M
        s = ProjectSettings()
        d = _dialog(s)
        assert len(d.pages) == len(d._PAGES)
        for page in d.pages:
            assert page.s is s or any(page.s is getattr(s, n)
                                      for n in vars(s)), type(page).__name__
        try:
            M._part_of(ProjectSettings(), s, s.groundwater.transient_stages)
        except LookupError:
            pass
        else:  # pragma: no cover
            raise AssertionError("a part that is no section was found")

    def test_apply_keeps_the_sections_the_project_holds(self):
        """Apply after Restore writes field by field: ``settings.search``
        and the other sections stay the objects the rest of the program
        holds."""
        s = _perturbed()
        held = {n: getattr(s, n) for n in vars(s)
                if dataclasses.is_dataclass(getattr(s, n))}
        d = _dialog(s)
        with _no_modals():
            d._defaults()
            d._apply()
        for n, section in held.items():
            assert getattr(s, n) is section, n

    def test_a_second_apply_after_restore_still_reaches_the_settings(self):
        from ogr_core.project import ProjectSettings
        s = ProjectSettings()
        s.methods.num_slices = 77
        d = _dialog(s)
        with _no_modals():
            d._defaults()
            d._apply()
            assert s.methods.num_slices == ProjectSettings().methods.num_slices
            d.pages[1].spn_slices.setValue(41)
            d._apply()
        assert s.methods.num_slices == 41


# ----------------------------------------------------------------------
class TestThroughTheWindow:
    def test_restore_and_ok_is_one_step_that_undo_takes_back(self):
        from ogr_core.project import ProjectSettings
        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog)

        def restore_then_ok(self):
            self._defaults()
            self._apply()
            return 1

        w = _window()
        try:
            _reproduction(w.project.settings)
            w.project.settings.groundwater.set_advanced_option(None)
            w.command_stack.clear()
            w.project.is_dirty = False
            before = _json(w.project)
            with _no_modals(), _swap(ProjectSettingsDialog, "exec",
                                     restore_then_ok):
                w.act_project_settings()
            assert w.command_stack.history() == (["Change settings"], [])
            s = w.project.settings
            assert (s.search.grid_x_min, s.search.grid_x_max,
                    s.search.grid_y_min, s.search.grid_y_max) == (
                12.0, 30.0, 25.0, 40.0)
            assert s.methods.num_slices == ProjectSettings().methods.num_slices
            after = _json(w.project)
            w.act_undo()
            assert _json(w.project) == before
            w.act_redo()
            assert _json(w.project) == after
        finally:
            _done(w)

    def test_restore_and_cancel_leaves_nothing(self):
        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog)

        def restore_then_cancel(self):
            self._defaults()
            return 0

        w = _window()
        try:
            _reproduction(w.project.settings)
            w.command_stack.clear()
            w.project.is_dirty = False
            before = _json(w.project)
            with _no_modals(), _swap(ProjectSettingsDialog, "exec",
                                     restore_then_cancel):
                w.act_project_settings()
            assert _json(w.project) == before
            assert w.command_stack.history() == ([], [])
            assert not w.project.is_dirty
        finally:
            _done(w)


# ----------------------------------------------------------------------
def _enabled(d, row):
    from PySide6.QtCore import Qt
    return bool(d.nav.item(row).flags() & Qt.ItemIsEnabled)


class TestWhatThePagesShow:
    def test_restore_shows_the_defaults(self):
        from ogr_core.project import ProjectSettings
        s = ProjectSettings()
        _reproduction(s)
        d = _dialog(s)
        assert d.pages[1].spn_slices.value() == 77
        with _no_modals():
            d._defaults()
        fresh = ProjectSettings()
        assert d.pages[1].spn_slices.value() == fresh.methods.num_slices
        assert d.pages[-1].ed_author.text() == fresh.summary.author

    def test_the_transient_page_counts_the_stages_that_are_kept(self):
        """After Restore the Transient page reads the copy, which keeps the
        stages; its gate follows the switch the Groundwater page now
        shows, off."""
        from ogr_core.project import ProjectSettings
        from ogr_gui.i18n import tr
        s = ProjectSettings()
        _reproduction(s)
        d = _dialog(s)
        row = [i for i, (label, _c) in enumerate(d._PAGES)
               if label == "Transient"][0]
        assert _enabled(d, row)
        with _no_modals():
            d._defaults()
        assert d.pages[row].lbl_stages.text() == (
            tr("%d stage(s), %d with a factor of safety") % (2, 1))
        assert not _enabled(d, row)
        # and nothing was written
        assert s.groundwater.transient is True

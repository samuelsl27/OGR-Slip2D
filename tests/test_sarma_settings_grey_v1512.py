# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D463 (v0.1.512) — the Sarma settings of the Methods page are greyed out
when they do not apply.

The invariant
-------------
A control that does not affect the result is not offered enabled (the
reason of rule 7, applied to the window). Sarma's seven settings
(``_MethodsPage._sarma_widgets``: number of wedges, tolerance, iterations,
face angles, face strength, boundaries at contacts, sense of the face
shear) reach only Sarma's method, so they are enabled only while its box is
ticked; the face cohesion and friction angle reach it only with a GIVEN
face strength, so they are enabled only then. The table, measured on
0.1.471 and 0.1.485 and fixed here:

=====================  =========  ========
State                  the seven  c and φ
=====================  =========  ========
unticked               grey       grey
ticked                 enabled    grey
ticked, «given»        enabled    enabled
unticked, «given»      grey       grey
=====================  =========  ========

The code is of 0.1.464 (``_refresh_sarma``, connected to the box and to the
strength combo) and no test named it until this one. Each control is read
by itself, not as "all of them", so a control dropped from the tuple or
enabled by some other path is seen. The signal path is checked without
calling ``_refresh_sarma`` by hand, and a no-op ``_refresh_sarma`` (the
mutant) must make the checks fail.

Out of scope, by the owner's decision of 2026-11-28: the box greyed out
because the method is not in the registry. That rule is v0.1.78's, for
every box, and ``tests/test_methods_page_v178.py`` covers it.

Cost: three pages, never shown and never ``exec()``-ed; well under 1 s.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_NAMES = ("spn_sarma_n", "dsp_sarma_tol", "spn_sarma_iter",
          "cbo_sarma_angles", "cbo_sarma_strength", "chk_sarma_contacts",
          "cbo_sarma_sense")


def _page():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ogr_core.project.settings import ProjectSettings
    from ogr_gui.dialogs.project_settings_dialog import _MethodsPage
    return _MethodsPage(ProjectSettings())


def _states(page):
    """``{name: enabled}`` for the seven and for c and φ, one by one."""
    out = {n: getattr(page, n).isEnabled() for n in _NAMES}
    out["dsp_sarma_c"] = page.dsp_sarma_c.isEnabled()
    out["dsp_sarma_phi"] = page.dsp_sarma_phi.isEnabled()
    return out


def _walk(page):
    """The four states of the table, through the signals only."""
    cb = page.checkboxes["sarma"]
    strength = page.cbo_sarma_strength
    not_given = next(i for i in range(strength.count())
                     if strength.itemData(i) != "given")
    strength.setCurrentIndex(not_given)
    cb.setChecked(True)          # a toggle both ways, whatever the default
    cb.setChecked(False)
    rows = [("unticked", _states(page))]
    cb.setChecked(True)
    rows.append(("ticked", _states(page)))
    strength.setCurrentIndex(strength.findData("given"))
    rows.append(("ticked, given", _states(page)))
    cb.setChecked(False)
    rows.append(("unticked, given", _states(page)))
    return rows


_WANT = {"unticked": (False, False), "ticked": (True, False),
         "ticked, given": (True, True), "unticked, given": (False, False)}


def _problems(rows):
    bad = []
    for label, st in rows:
        group, cphi = _WANT[label]
        for n in _NAMES:
            if st[n] is not group:
                bad.append(f"{label}: {n} enabled={st[n]}")
        for n in ("dsp_sarma_c", "dsp_sarma_phi"):
            if st[n] is not cphi:
                bad.append(f"{label}: {n} enabled={st[n]}")
    return bad


class TestSarmaSettingsGrey:
    def test_the_premise_the_tuple_is_the_seven(self):
        page = _page()
        assert tuple(page._sarma_widgets) == tuple(
            getattr(page, n) for n in _NAMES)
        # the box itself is enabled: the method is registered
        assert page.checkboxes["sarma"].isEnabled()

    def test_the_four_states_control_by_control(self):
        assert _problems(_walk(_page())) == []

    def test_the_strength_combo_alone_turns_c_and_phi_on(self):
        page = _page()
        page.checkboxes["sarma"].setChecked(True)
        assert not page.dsp_sarma_c.isEnabled()
        page.cbo_sarma_strength.setCurrentIndex(
            page.cbo_sarma_strength.findData("given"))
        assert page.dsp_sarma_c.isEnabled()
        assert page.dsp_sarma_phi.isEnabled()

    def test_a_refresh_that_does_nothing_is_seen(self):
        from ogr_gui.dialogs.project_settings_dialog import _MethodsPage
        saved = _MethodsPage._refresh_sarma
        _MethodsPage._refresh_sarma = lambda self, *_a: None
        try:
            bad = _problems(_walk(_page()))
        finally:
            _MethodsPage._refresh_sarma = saved
        assert bad, "a no-op _refresh_sarma passed the table"

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The Methods page must ask the registry which methods exist.

**The invariant**: a method checkbox is disabled if and only if its id is
absent from ``method_registry()``. Not "disabled if it is in a list of
names someone wrote down" — that list is the bug.

Why this file exists. Lowe-Karafiath was implemented, registered and
validated in v0.1.20 (error < 1 % against the reference factor of safety,
``test_slide_validation_ej1.py``). It nevertheless sat greyed out in
Project Settings with the tooltip "Not yet implemented in OGR Slip2D"
until v0.1.78, because ``_MethodsPage`` carried its own hand-written tuple
of six ids, frozen at v0.1.7 and never revisited. The user could not
select a method the engine had been computing correctly for fifty-eight
versions.

It is the *same* failure ``build_method`` already documents for
``janbu_corrected`` (``analysis_runner.py``): whenever a second list of
methods exists beside the registry, the only question is which version it
drifts in. So the test does not assert "Lowe-Karafiath is enabled" — that
would be a third list. It asserts the two sets agree, which is the
property that makes the drift impossible.

Consequence worth stating: Corps of Engineers #1 and #2 were genuinely not
in the registry, so they had to stay disabled. The day someone registered
them, this test would keep passing and the checkboxes would light up on
their own.

**That day was v0.1.98**, and it is the proof the invariant is worth
having: the two methods were implemented and registered, and not one line
of ``_MethodsPage`` changed. The test below used to assert the opposite —
that they stay grey — and it has been rewritten rather than deleted,
because the half of the invariant it guards is still needed: the fix must
not turn the greying off wholesale. What changed is only which methods
are on which side of it, and the first test in this file, the one that
compares the two SETS, never had to change at all.
"""
from __future__ import annotations


_WINDOWS: list = []


def _methods_page():
    from PySide6.QtWidgets import QApplication
    from ogr_core.project import ProjectSettings
    from ogr_gui.dialogs.project_settings_dialog import ProjectSettingsDialog
    QApplication.instance() or QApplication([])
    d = ProjectSettingsDialog(ProjectSettings())
    _WINDOWS.append(d)          # keep alive: a collected dialog takes its
    return d.pages[1]           # child widgets with it


class TestTheMethodsPageAsksTheRegistry:
    def test_disabled_set_is_exactly_the_unregistered_set(self):
        from ogr_slip2d.methods import method_registry
        page = _methods_page()
        registry = set(method_registry())

        disabled = {mid for mid, cb in page.checkboxes.items()
                    if not cb.isEnabled()}
        expected = {mid for mid in page.checkboxes if mid not in registry}
        assert disabled == expected, (
            f"greyed out but registered: {sorted(disabled - expected)}; "
            f"registered but offered: {sorted(expected - disabled)}")

    def test_lowe_karafiath_is_selectable(self):
        """The regression itself, named. v0.1.20 registered and validated
        it; v0.1.78 is when the interface finally agreed."""
        from ogr_core.project.settings import LEMMethod as LEM
        page = _methods_page()
        cb = page.checkboxes[LEM.LOWE_KARAFIATH.value]
        assert cb.isEnabled(), "Lowe-Karafiath is registered and validated"
        assert not cb.toolTip(), "no 'not implemented' tooltip on a method"

    def test_corps_of_engineers_is_now_offered(self):
        """Was ``test_corps_of_engineers_stays_disabled`` until v0.1.98.

        Why it changed. Until v0.1.97 these two ids were in the
        ``LEMMethod`` enum and in no registry, which is exactly what this
        assertion pinned. v0.1.98 implemented them — Modified Swedish,
        validated against the slice tables USACE publishes in EM
        1110-2-1902 Appendix G — so the honest assertion is now the
        opposite one. It is rewritten rather than deleted because the
        claim it protects has not changed: the greying must follow the
        registry and nothing else, in both directions.

        If a third method is ever declared in the enum without being
        implemented, this test is where to state it, and the set
        comparison above will already be enforcing it.
        """
        from ogr_core.project.settings import LEMMethod as LEM
        from ogr_slip2d.methods import method_registry
        registry = set(method_registry())
        page = _methods_page()
        for m in (LEM.CORPS_OF_ENGINEERS_1, LEM.CORPS_OF_ENGINEERS_2):
            assert m.value in registry, m.value
            cb = page.checkboxes[m.value]
            assert cb.isEnabled(), m.value
            assert not cb.toolTip(), (
                f"{m.value} is implemented; no 'not implemented' tooltip")

    def test_nothing_in_the_enum_is_unimplemented_any_more(self):
        """The state of the gap itself, named. Nine declared, nine
        registered — so today no checkbox on that page is grey, and the
        day one is, the set comparison above says which and why."""
        from ogr_core.project.settings import LEMMethod as LEM
        from ogr_slip2d.methods import method_registry
        missing = {m.value for m in LEM} - set(method_registry())
        assert not missing, sorted(missing)

    def test_every_enum_member_has_a_checkbox(self):
        """A method the engine knows about but the page never lists is
        unreachable in a different way — rule 3, one level down."""
        from ogr_core.project.settings import LEMMethod as LEM
        page = _methods_page()
        assert {m.value for m in LEM} == set(page.checkboxes)

    def test_every_registered_method_is_offered(self):
        """The registry is allowed to grow; the enum has to keep up."""
        from ogr_slip2d.methods import method_registry
        page = _methods_page()
        missing = set(method_registry()) - set(page.checkboxes)
        assert not missing, f"registered but not on the page: {sorted(missing)}"

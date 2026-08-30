# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.103 — no search setting may exist without a reader outside
the interface.

**The invariant**: a field of ``SearchSettings`` is editable, saved to the
`.ogr` and printed in reports. If nothing outside ``ogr_gui/`` ever reads
it, the user is configuring nothing and believes the analysis respects it.
That is rule 7, and this project has now met it three times in three
disguises:

    A9-1  — the whole Optimize Surfaces panel, thirteen fields stored and
            read by nobody. Closed in v0.1.104, which is why not one of
            them is on the list below any more.
    A37-1 — Minimum Elevation and Minimum Depth, declared, editable,
            saved, and not passed by a single one of the six searches.
    D07b  — six settings that existed TWICE, under the name the interface
            showed and the name the engine read. The dialog wrote both, so
            they agreed from the interface and diverged everywhere else.

One test of this shape would have caught all three. It exists now.

**Why the inventory is frozen rather than allowed**: the fields still
without a reader belong to defects that are open and named. Comparing the
exact SET, and not merely checking membership of a permitted list, means a
NEW unread field fails immediately, and closing one of those defects fails
too — forcing the inventory down instead of letting it drift up. Same
budget shape as the i18n test that counts unwrapped strings.
"""
from __future__ import annotations
import re
from pathlib import Path


#: Packages that are the analysis, as opposed to the interface. A setting
#: read only by ``ogr_gui`` is read only by the dialog that edits it.
_ENGINE_PACKAGES = ("ogr_core", "ogr_slip2d", "ogr_fem2d", "ogr_cli")

#: Search settings that no engine module reads yet, each with the open
#: defect that owns it. Shrinks; never grows.
_KNOWN_UNREAD = {
    # The thirteen ``optimize_*`` fields were here until v0.1.104, the
    # whole of defect D08. They are gone from this list because they now
    # have readers: ``ProjectSettings.optimize_kwargs`` turns them into an
    # ``OptimizeSettings``, ``build_search`` hands it to the three
    # non-circular searches and ``BaseSearch.run`` walks the surfaces with
    # it. The list is a budget that only shrinks, so this is what closing
    # a defect looks like from here.
    # D07c — found by this inventory in v0.1.103, reported and not yet
    # fixed because each one moves a number and needs its own reference.
    #   D07c(a) is closed in v0.1.132: the n_eps of Su (2009) section
    #   2.1.7 reaches ``_vfsa``, which broke on a hand-written 3 while the
    #   field declared the paper's 5. Out of the list because it has a
    #   reader now — ``tests/test_annealing_stopping_v1132.py`` holds it.
    #   D07c(b) is closed in v0.1.118 — ``block_num_groups`` stopped being
    #   derived as ``num_surfaces // 1000`` and got its own control. This
    #   field STAYS on the list, and legitimately: it enables that control
    #   and nothing else, so the engine has nothing to read. Kept here so
    #   the inventory keeps saying so out loud.
    "block_multiple_groups": "UI only",
}


def _engine_source() -> str:
    """Every engine module, with the settings declarations themselves cut.

    Without that cut the dataclass would read itself: ``foo: int = 3`` in
    the class body is not a reader, and counting it would make the test
    pass for every field forever.
    """
    root = Path(__file__).resolve().parent.parent
    out = []
    for pkg in _ENGINE_PACKAGES:
        for f in sorted((root / pkg).rglob("*.py")):
            src = f.read_text(encoding="utf-8", errors="replace")
            if f.as_posix().endswith("ogr_core/project/settings.py"):
                src = "\n".join(
                    ln for ln in src.splitlines()
                    if not re.match(r"^    [a-z_][a-z0-9_]*\s*:\s*\S", ln))
            out.append(src)
    return "\n".join(out)


def _reads(blob: str, name: str) -> bool:
    """An attribute access or a quoted name — the two ways a setting is
    reached, ``s.min_depth`` and ``getattr(s, "min_depth", None)``."""
    return bool(re.search(r"(\.%s\b)|([\"']%s[\"'])" % (name, name), blob))


# ======================================================================
class TestEverySearchSettingHasAReader:

    def test_the_unread_ones_are_exactly_the_ones_on_record(self):
        from dataclasses import fields
        from ogr_core.project.settings import SearchSettings

        blob = _engine_source()
        unread = {f.name for f in fields(SearchSettings)
                  if not _reads(blob, f.name)}
        expected = set(_KNOWN_UNREAD)

        new = sorted(unread - expected)
        assert not new, (
            "these search settings are editable and saved and no analysis "
            "reads them, which is rule 7: " + ", ".join(new))
        fixed = sorted(expected - unread)
        assert not fixed, (
            "these now have a reader — take them out of _KNOWN_UNREAD and "
            "close the defect that owned them: " + ", ".join(fixed))

    def test_the_settings_of_the_six_pairs_are_read(self):
        """The point of v0.1.103, stated as an assertion: the field the
        interface shows is the field the analysis consumes."""
        blob = _engine_source()
        for name in ("path_num_surfaces",
                     "auto_refine_num_iterations",
                     "auto_refine_divisions_along_slope",
                     "path_segment_length_manual",
                     "path_segment_length_value",
                     "path_initial_angle_at_toe_lower_deg",
                     "path_initial_angle_at_toe_upper_deg",
                     "path_initial_angle_at_toe_lower_enabled",
                     "path_initial_angle_at_toe_upper_enabled",
                     "sa_temperature_coefficient",
                     "initial_angle_at_toe_lower_enabled",
                     # v0.1.104 — the seventh pair, and the only one found
                     # the other way round: the engine read the hidden
                     # ``path_optimize`` while the dialog showed
                     # ``optimize_enabled``, which nothing read.
                     "optimize_enabled"):
            assert _reads(blob, name), name

    def test_no_field_is_a_second_name_for_another(self):
        """The shape of the defect, not one instance of it: two fields
        whose names differ only by the words the interface happened to
        use are how the pair drifts apart in the first place."""
        from dataclasses import fields
        from ogr_core.project.settings import SearchSettings

        def _key(name: str) -> str:
            words = [w for w in name.split("_")
                     if w not in ("num", "number", "of", "the", "value")]
            return "_".join(sorted(words))

        seen: dict = {}
        for f in fields(SearchSettings):
            seen.setdefault(_key(f.name), []).append(f.name)
        clashes = {k: v for k, v in seen.items() if len(v) > 1}
        assert not clashes, clashes


# ======================================================================
class TestTheInventoryItselfIsHonest:
    """A frozen list is only worth what its entries are worth."""

    def test_every_entry_is_a_real_field(self):
        from dataclasses import fields
        from ogr_core.project.settings import SearchSettings
        names = {f.name for f in fields(SearchSettings)}
        stale = sorted(set(_KNOWN_UNREAD) - names)
        assert not stale, (
            "the inventory names fields that no longer exist: "
            + ", ".join(stale))

    def test_every_entry_names_the_defect_that_owns_it(self):
        """Or, since v0.1.118, says why there is no defect to name.

        ``UI only`` is the one other answer allowed, and it is a narrow
        one: a field the interface uses to drive its own widgets and that
        the engine therefore has nothing to read. It is not an escape
        hatch for a setting that ought to reach the analysis and does not
        — that is what the defect ids are for.
        """
        for name, owner in _KNOWN_UNREAD.items():
            ok = owner == "UI only" or re.fullmatch(r"D\d+[a-z]?", owner)
            assert ok, (name, owner)

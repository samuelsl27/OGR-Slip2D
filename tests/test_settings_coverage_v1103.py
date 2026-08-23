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

    A9-1  — the whole Optimize Surfaces panel, stored and read by nobody.
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
    # D08 (groups A9-1) — Optimize Surfaces. The capability exists in the
    # searches; what is missing is any wiring from these settings to it.
    "optimize_enabled": "D08",
    "optimize_target": "D08",
    "optimize_fos_threshold": "D08",
    "optimize_tolerance": "D08",
    "optimize_max_iterations": "D08",
    "optimize_step_reduction_factor": "D08",
    "optimize_max_concave_angle_enabled": "D08",
    "optimize_max_concave_angle_deg": "D08",
    "optimize_explore_all_vertices": "D08",
    "optimize_snap_shallow_to_slope": "D08",
    "optimize_snap_specify_distance": "D08",
    "optimize_snap_distance": "D08",
    "optimize_use_depth_elevation_concave_checks": "D08",
    # D32 — the non-circular Auto Refine does not exist: the setting is
    # there and the search it configures is the circular one.
    "auto_refine_num_vertices_along_surface": "D32",
    # D07c — found by this inventory in v0.1.103, reported and not yet
    # fixed because each one moves a number and needs its own reference.
    #   the n_e of Su (2009) section 2.1.7, against a hard-coded 3;
    "sa_num_fos_compared_before_stopping": "D07c",
    #   what the interface derives block_num_groups from is not what the
    #   reference calls Multiple Groups.
    "block_multiple_groups": "D07c",
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
                     "initial_angle_at_toe_lower_enabled"):
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
        for name, owner in _KNOWN_UNREAD.items():
            assert re.fullmatch(r"D\d+[a-z]?", owner), (name, owner)

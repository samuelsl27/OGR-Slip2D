# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.192 — the Tensile Stress Check survives saving and reopening a
project; only a file written before v0.1.74 is still switched off.

THE INVARIANT. A setting that does not survive save-and-open is rule 7:
the user switches it on, saves, reopens, runs, and gets the answer of a
check that is off. ``AdvancedSettings.from_dict`` turned EVERY stored
``check_tensile_stresses: true`` into ``false`` (defect D178). Its comment
said the migration was "conditional on the value being the old default: a
user who deliberately typed something else keeps it" — and for a boolean
the old default and a deliberate choice are the SAME value, so the
condition could not tell them apart and never did. Since v0.1.191 (D165)
the check grants rock its tensile strength, which is what made this matter:
that allowance reached only runs made in the same session.

HOW AN OLD FILE IS TOLD FROM A CHOICE, and why no version field was added.
``tensile_percent`` entered ``AdvancedSettings`` in commit 81c997d (v0.1.74)
— the SAME commit that flipped the default to False — and ``asdict`` writes
it on every save. So its absence is exactly "written before v0.1.74", the
only files whose True was a default and not a choice. It is the rule this
codebase already migrates by: the PRESENCE of a key (``_SHADOW_FIELDS``,
``pre_v1103``, ``Material.use_sat_unit_weight``), never a value. The
``.ogr`` carries no writer version (``format_version`` is "0.1" and read by
nobody), and adding one would not help the files that exist today, which
would still need this marker.

WHAT THIS FILE DOES NOT CLAIM. The lambda migrations in the same function
still decide by VALUE alone and have the same flaw: a deliberate
``max_lambda = 1.5`` reopens as 6.0 (``test_lambda_range_v190.py`` pins
it). The defect report forbade moving that chain; it is reported as D182.

WHAT THIS FILE DISCRIMINATES against the v0.1.191 tree. MEASURED, by
copying this file into a ``git worktree`` at that commit and running it
there. Of the 6 cases, **2 fail and 4 pass**:

  fail  on_stays_on                              (behaviour: the defect)
        the_reopened_setting_reaches_the_search  (behaviour: rule 7)

  pass  off_stays_off                            (guard: the other arm)
        a_block_written_before_v0174_is_...      (guard: the migration
                                                  that must survive)
        every_save_writes_the_marker             (guard: the marker)
        the_validation_models_on_disk_carry_...  (guard: the marker, on
                                                  real files)

The four that pass do so BY DESIGN: they state what must NOT change (old
files still migrate) and the premise the fix rests on (the marker is
there), both of which were already true in v0.1.191. Both failures are on
behaviour, neither on the absence of a symbol.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent

#: The ``advanced`` block as v0.1.73 wrote it: the five fields of the
#: dataclass before 81c997d, at their defaults (``git show
#: 0985074:ogr_core/project/settings.py``). No ``tensile_percent``, because
#: that field did not exist yet.
PRE_V174_BLOCK = {
    "check_tensile_stresses": True,
    "min_initial_fs": 1.0,
    "min_lambda": -1.25,
    "max_lambda": 1.25,
    "iterate_steffensen": True,
}


def _reopened(check_on: bool):
    """A project saved with the check as given, through JSON and back —
    the round trip a file on disk makes."""
    from ogr_core.project import Project
    p = Project("d178")
    p.settings.advanced.check_tensile_stresses = check_on
    text = json.dumps(p.to_dict())
    return Project.from_dict(json.loads(text))


# ======================================================================
class TestAChoiceSurvivesTheRoundTrip:

    def test_on_stays_on(self):
        assert _reopened(True).settings.advanced.check_tensile_stresses \
            is True

    def test_off_stays_off(self):
        assert _reopened(False).settings.advanced.check_tensile_stresses \
            is False

    def test_the_reopened_setting_reaches_the_search(self):
        """Rule 7 asks whether the setting MOVES something, not whether a
        field kept its value: after reopening, the search the analysis
        builds must be the one that rejects tensile surfaces."""
        from ogr_slip2d.analysis_runner import build_search
        back = _reopened(True)
        assert back.settings.admissibility_kwargs()["reject_tensile"] is True
        search = build_search(back, "bishop_simplified")
        assert search is not None
        assert search.reject_tensile is True
        # And the control: the same round trip with the check off builds a
        # search that does not reject, so the assertion above is not
        # something every search says.
        assert build_search(_reopened(False),
                            "bishop_simplified").reject_tensile is False


# ======================================================================
class TestOnlyAnOldFileIsMigrated:

    def test_a_block_written_before_v0174_is_switched_off(self):
        from ogr_core.project.settings import AdvancedSettings
        old = AdvancedSettings.from_dict(dict(PRE_V174_BLOCK))
        assert old.check_tensile_stresses is False

    def test_every_save_writes_the_marker(self):
        """The migration is only as good as the marker: if a save could
        omit ``tensile_percent``, a deliberate True would be migrated again
        on the next open."""
        from ogr_core.project import Project
        from ogr_core.project.settings import AdvancedSettings
        block = Project("x").to_dict()["settings"]["advanced"]
        assert "tensile_percent" in block
        assert "tensile_percent" not in PRE_V174_BLOCK
        # And the marker is not something the reader invents: a block
        # without it stays without it until the dataclass fills the default.
        assert AdvancedSettings.from_dict(dict(PRE_V174_BLOCK)) \
            .tensile_percent == AdvancedSettings().tensile_percent

    def test_the_validation_models_on_disk_carry_the_marker(self):
        """Real files, not a dictionary written here: every model under
        ``validacion/casos`` was saved after v0.1.74 and must say so."""
        models = sorted((_ROOT / "validacion" / "casos").glob("*/modelo.ogr"))
        assert models, "no validation models found"
        for path in models:
            data = json.loads(path.read_text(encoding="utf-8"))
            advanced = data["settings"]["advanced"]
            assert "tensile_percent" in advanced, path.parent.name
            assert "min_initial_fs" not in advanced, path.parent.name

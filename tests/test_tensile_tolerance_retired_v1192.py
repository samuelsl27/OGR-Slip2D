# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.192 — ``tensile_tolerance`` is retired from the searches, and an old
call that still passes it by name keeps working.

THE INVARIANT. A setting that moves nothing is worse than no setting (rule
7). ``tensile_tolerance`` was the tolerance of the interslice-tension
filter of v0.1.24 ("5 % of max|E|", ``CHANGELOG_v0.1.24.md``); v0.1.32
replaced that filter by the Tensile Stress Check on slice BASES, and from
then on every search took the argument, stored it in
``self.tensile_tolerance`` and never read it (defect D179). Since v0.1.191
the name also reads as the tensile strength that version introduced, which
is the material's (``StrengthModel.tensile_strength``) — so the dead
parameter had started to lie as well as to do nothing.

What must NOT move, and is checked here: ``reject_tensile`` and
``tensile_percent``, which the check does read; and old calls that pass
``tensile_tolerance`` by name, which must still build every search. The
shared door (``_base_kwargs``) consumes the name, and only that name.

WHAT THIS FILE DISCRIMINATES against the v0.1.191 tree. MEASURED, by
copying this file into a ``git worktree`` at that commit and running it
there. Of the 5 cases, **4 fail and 1 passes**:

  fail  base_search_no_longer_declares_it          (structural, signature)
        no_search_keeps_the_attribute              (behaviour: it was stored)
        nothing_reads_or_writes_it_as_an_attribute (structural: an ABSENCE)
        the_shared_door_consumes_only_that_name    (behaviour: the door
                                  popped it AND handed it on to BaseSearch)

  pass  every_search_still_builds_with_an_old_call (guard: compatibility)

The one that passes does so BY DESIGN: it is the compatibility the
retirement must not break, and v0.1.191 already had it. The header said
"3 fail, 2 pass" before it was measured; the door test fails on the old
tree too, because consuming the name was never the problem — forwarding it
was.
"""
from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent
_NAME = "tensile_" "tolerance"   # split: this file is scanned below


def _every_search_class():
    from ogr_slip2d.particle_swarm import ParticleSwarmSearch
    from ogr_slip2d.search import (
        AutoRefineNonCircularSearch, AutoRefineSearch, BlockSearch,
        GridSearch, PathSearch, SimulatedAnnealingSearch, SlopeSearch,
    )
    return (GridSearch, SlopeSearch, AutoRefineSearch,
            AutoRefineNonCircularSearch, BlockSearch, PathSearch,
            SimulatedAnnealingSearch, ParticleSwarmSearch)


def _build(cls):
    from ogr_slip2d import BishopSimplified
    return cls(method=BishopSimplified(), reject_tensile=True,
               tensile_percent=90.0, **{_NAME: 0.1})


# ======================================================================
class TestTheParameterIsGone:

    def test_base_search_no_longer_declares_it(self):
        from ogr_slip2d.search import BaseSearch
        sig = inspect.signature(BaseSearch.__init__)
        assert _NAME not in sig.parameters
        # The two it sat between are still there, with their defaults.
        assert sig.parameters["reject_tensile"].default is False
        assert sig.parameters["tensile_percent"].default == 95.0

    def test_no_search_keeps_the_attribute(self):
        for cls in _every_search_class():
            s = _build(cls)
            assert not hasattr(s, _NAME), cls.__name__

    def test_nothing_reads_or_writes_it_as_an_attribute(self):
        """An absence, which no positive grep can see: before v0.1.192
        ``BaseSearch.__init__`` assigned ``self.<name>`` and nothing in the
        whole tree ever read it back."""
        hits = []
        for pkg in ("ogr_core", "ogr_slip2d", "ogr_fem2d", "ogr_gui",
                    "ogr_cli"):
            for path in sorted((_ROOT / pkg).rglob("*.py")):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Attribute) and node.attr == _NAME:
                        hits.append(f"{path.relative_to(_ROOT)}:"
                                    f"{node.lineno}")
        assert not hits, hits


# ======================================================================
class TestOldCallsStillWork:

    def test_every_search_still_builds_with_an_old_call(self):
        for cls in _every_search_class():
            s = _build(cls)
            # What the check DOES read arrives intact.
            assert s.reject_tensile is True, cls.__name__
            assert abs(s.tensile_percent - 90.0) < 1e-12, cls.__name__

    def test_the_shared_door_consumes_only_that_name(self):
        """The name is taken out of ``legacy`` so nothing downstream sees
        it, and a name the door does not know is left where it was: the
        door must not grow into a place that swallows anything."""
        from ogr_slip2d.search import _base_kwargs
        legacy = {_NAME: 0.1, "not_a_shared_argument": 1}
        out = _base_kwargs(legacy)
        assert _NAME not in out
        assert _NAME not in legacy
        assert legacy == {"not_a_shared_argument": 1}

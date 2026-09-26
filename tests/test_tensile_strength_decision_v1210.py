# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.210 — there is no per-material tensile strength, and that is a written
decision (defect D180, closed as a documentary closure).

THE INVARIANT. The allowable tension of the Tensile Stress Check comes from
the strength criterion alone (``StrengthModel.tensile_strength()``, D165),
and the reason no per-material value exists is written where the tolerance
is read, ``checks._material_tensile_strength``. The reference documents
such a value for a SOLVER mechanism it gives no formula for, its pages on
the check never mention it, and its two eligibility lists disagree; the
full argument is in that docstring.

THIS FILE IS WEAK BY NATURE, and says so. A documentary closure changes no
number, so the only case that can fail on v0.1.209 is the decision text.
The rest are GUARDS: they keep a field from arriving later without its
rule-7 test -- in the model, its serialisation, the dialog or the API --
and keep D165's allowances where they are.

DISCRIMINATION against the v0.1.209 tree, MEASURED in a ``git worktree`` at
a6eceda: of the 6 cases, **1 fails** (the_decision_is_written, text) and 5
pass (guards).
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _doc(fn) -> str:
    return re.sub(r"\s+", " ", fn.__doc__ or "")


class TestTheDecisionIsWritten:
    def test_the_decision_is_written(self):
        from ogr_slip2d.checks import _material_tensile_strength
        doc = _doc(_material_tensile_strength)
        for phrase in ("v0.1.210 (D180)",
                       "there is NO per-material tensile strength",
                       "SOLVER mechanism",
                       "creates none by itself",
                       "+22.52 %",
                       "Revisit if a source publishes the rule"):
            assert phrase in doc, phrase


class TestNoFieldArrivedWithoutItsRule:
    """GUARDS. They pass on v0.1.209 as well."""

    def test_the_material_has_no_tensile_field(self):
        import dataclasses

        from ogr_core.materials import Material, MohrCoulomb
        names = [f.name for f in dataclasses.fields(Material)]
        assert not [n for n in names if "tensile" in n.lower()], names
        m = Material(name="x", unit_weight=20.0,
                     strength=MohrCoulomb(cohesion=5.0, friction_angle=30.0))
        keys = list(m.to_dict())
        assert not [k for k in keys if "tensile" in k.lower()], keys

    def test_an_old_or_foreign_file_with_the_key_loads_the_same(self):
        """A file written by something that had the field still loads, and
        the key does nothing -- which is exactly why it must not exist
        silently in the model either."""
        from ogr_core.materials import Material, MohrCoulomb
        m = Material(name="x", unit_weight=20.0,
                     strength=MohrCoulomb(cohesion=5.0, friction_angle=30.0))
        d = m.to_dict()
        d["use_tensile_strength"] = True
        d["tensile_strength"] = 50.0
        back = Material.from_dict(d)
        assert back.to_dict() == m.to_dict()

    def test_the_dialog_offers_no_tensile_row(self):
        src = (REPO / "ogr_gui" / "dialogs"
               / "material_properties_dialog.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        labels = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            name = (f.id if isinstance(f, ast.Name)
                    else f.attr if isinstance(f, ast.Attribute) else "")
            if name not in ("tr", "QCheckBox", "QLabel", "addRow"):
                continue
            for a in node.args:
                if (isinstance(a, ast.Constant) and isinstance(a.value, str)
                        and "tensile" in a.value.lower()):
                    labels.append(a.value)
        assert not labels, labels

    def test_the_api_takes_no_tensile_field(self):
        from ogr_api.ops.model import _MATERIAL_FIELDS
        assert not [f for f in _MATERIAL_FIELDS if "tensile" in f.lower()]

    def test_d165_is_untouched(self):
        """The allowances still come from the criterion alone: exactly the
        two Hoek-Brown models have one, measured over the registry."""
        from ogr_core.materials import Material
        from ogr_core.materials.registry import REGISTRY
        from ogr_slip2d.checks import _material_tensile_strength
        with_one = set()
        for mid, cls in REGISTRY.all().items():
            if _material_tensile_strength(Material(name="r",
                                                   strength=cls())) > 0:
                with_one.add(mid)
        assert with_one == {"hoek_brown", "hoek_brown_classic"}, with_one

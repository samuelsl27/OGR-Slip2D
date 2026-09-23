# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.192 — the GSI calculator writes mb, s and a into the material, and the
material dialog stops rounding the parameters it shows.

TWO DEFECTS, ONE PANEL.

D176 — the calculator's button wrote nothing. ``_open_parameter_calculator``
looked the editors up with ``getattr(panel, "_widgets", {})``, and the panel
keeps them in ``_editors``: the lookup got the empty default, every value
was skipped without a word, and accepting the calculator left mb, s and a
as they were. Rule 7 in its purest form — a control that does nothing. The
write now lives in ``_apply_parameter_result``, apart from the modal
``exec()`` so it can be driven without a screen, and goes through
``_StrengthParamPanel.set_param_values``, which RAISES on a name it has no
editor for instead of skipping it.

D181 — found while planning D176, and worse than it. The editors were
``QDoubleSpinBox`` with four decimals, ``setValue`` rounds to them, and the
dialog rebuilds the strength from its editors whenever a material is
stored. So opening the dialog and pressing OK WITHOUT TOUCHING ANYTHING
rewrote every parameter at four decimals. Measured on v0.1.191 with a GSI-10
rock mass: s = 4.5399929762484854e-05 came back 0.0, mb 0.4018402645107363
came back 0.4018, and the tensile strength s*sigci/mb that v0.1.191 grants
rock went from 5.649 kPa to 0. Every GSI up to 13 lost ``s`` entirely; GSI 20
lost 29 % of it. And D176's fix alone would have written into those same
editors, so a fixed button would have stored s = 0 for exactly the rock
masses whose s is smallest. The function-points table of the same panel had
the same defect at three decimals (``f"{:.3f}"``), fixed with it.

THE ANCHORS. The calculator's own formulas (Hoek, Carranza-Torres & Corkum
2002): s = exp((GSI - 100)/(9 - 3D)) is checked in closed form on the value
that ARRIVES in the material, not on the calculator's output. And the
identity that D181 broke: a dialog opened and accepted without an edit must
hand back exactly the parameters it was given — asserted to the bit, over
every built-in model, with values chosen to have more digits than any fixed
decimal count keeps.

WHAT THIS FILE DOES NOT CLAIM. The other spin boxes of this dialog (unit
weights, ru, constant u, phi_b, the air-entry value) and the ~95
``setDecimals`` elsewhere in the interface are not censused here; D181 is
scoped to the strength-parameter panel and says so.

WHAT THIS FILE DISCRIMINATES against the v0.1.191 tree. MEASURED, by copying
this file into a ``git worktree`` at that commit and running it there. Of
the 9 cases, **all 9 fail**, and not all equally:

  BEHAVIOUR  the_three_editors_change            (the real button handler
             the_accepted_material_carries_...    writes nothing)
             a_low_gsi_arrives_whole             (s stays 0.004)
             every_builtin_model_round_trips_... (anisotropic_linear c1
                                                  6.172839450617284 ->
                                                  6.1728, and on)
             the_function_points_round_trip_...  (5.123456789012345 ->
                                                  5.123)
  ABSENCE    nothing_looks_up_widgets_any_more   (finds line 1037)
  WEAK       a_name_without_an_editor_raises     (no ``set_param_values``)
             the_text_reads_back_as_the_same_... (no ``_PreciseSpinBox``)
             scientific_notation_can_be_typed    (no ``_PreciseSpinBox``)

The two button cases go through ``_open_parameter_calculator`` itself, the
handler both trees have, with only the modal ``exec()`` replaced — which is
why they fail on the old tree by what they WRITE and not by a missing name.
"""
from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_ROOT = Path(__file__).resolve().parent.parent

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except Exception:  # noqa: BLE001
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_WINDOWS = []


def _dialog(material):
    """The real material dialog on one material, kept alive for Qt."""
    from ogr_gui.dialogs.material_properties_dialog import (
        MaterialPropertiesDialog,
    )
    QApplication.instance() or QApplication([])
    d = MaterialPropertiesDialog([material], None)
    _WINDOWS.append(d)
    return d


def _rock(**params):
    from ogr_core.materials import GeneralizedHoekBrown, Material
    return Material(name="rock", strength=GeneralizedHoekBrown(**params))


def _press_the_button(dialog, gsi, mi=10.0, d=0.0):
    """Drive the REAL button handler, with the modal ``exec()`` of the
    calculator replaced by an immediate accept after setting its inputs.
    Rule 5: the class attribute is restored whatever happens. Returns the
    calculator's result, read from the calculator itself."""
    from ogr_gui.dialogs import parameter_calculator_dialog as pcd
    seen = {}

    def _accept_at_once(calc):
        calc.sp_gsi.setValue(gsi)
        calc.sp_mi.setValue(mi)
        calc.sp_d.setValue(d)
        seen["result"] = calc.result_params
        return 1

    original = pcd.ParameterCalculatorDialog.exec
    pcd.ParameterCalculatorDialog.exec = _accept_at_once
    try:
        dialog._open_parameter_calculator()
    finally:
        pcd.ParameterCalculatorDialog.exec = original
    return seen["result"]


# ======================================================================
@_requires_qt
class TestTheButtonWrites:
    """D176, through the button's own handler."""

    def test_the_three_editors_change(self):
        d = _dialog(_rock())                 # mb 2.5, s 0.004, a 0.5
        before = {k: e.value() for k, e in d.param_panel._editors.items()}
        res = _press_the_button(d, gsi=50.0)
        after = {k: e.value() for k, e in d.param_panel._editors.items()}
        assert (after["mb"], after["s"], after["a"]) == (res.mb, res.s,
                                                         res.a)
        for k in ("mb", "s", "a"):
            assert after[k] != before[k], k
        assert after["sigci"] == before["sigci"]

    def test_the_accepted_material_carries_them_and_its_tension_moves(self):
        """Rule 7 asks what the control MOVES: here the tensile strength
        s*sigci/mb the Tensile Stress Check grants the rock."""
        mat = _rock(sigci=50000.0)
        sigma_t_before = mat.strength.tensile_strength()
        d = _dialog(mat)
        res = _press_the_button(d, gsi=50.0)
        d._ok()
        out = d.result_materials()[0].strength
        assert (out.params["mb"], out.params["s"], out.params["a"]) == \
            (res.mb, res.s, res.a)
        expected = res.s * 50000.0 / res.mb
        assert abs(out.tensile_strength() - expected) <= 1e-12 * expected
        assert out.tensile_strength() != sigma_t_before

    def test_a_low_gsi_arrives_whole(self):
        """The case D181 destroyed: s = exp(-10) at GSI 10, D = 0, checked
        in closed form (Hoek, Carranza-Torres & Corkum 2002) on what the
        MATERIAL holds after OK, not on what the calculator printed."""
        d = _dialog(_rock(sigci=50000.0))
        _press_the_button(d, gsi=10.0)
        d._ok()
        s = d.result_materials()[0].strength.params["s"]
        closed = math.exp((10.0 - 100.0) / 9.0)
        assert abs(s - closed) <= 1e-15 * closed, (s, closed)

    def test_a_name_without_an_editor_raises(self):
        """Skipping silently is what hid D176; the writer must refuse."""
        from ogr_core.materials import Material, MohrCoulomb
        d = _dialog(Material(name="soil",
                             strength=MohrCoulomb(cohesion=5.0,
                                                  friction_angle=30.0)))
        try:
            d.param_panel.set_param_values({"mb": 1.0})
        except KeyError:
            return
        raise AssertionError("a value for a missing editor was skipped")

    def test_nothing_looks_up_widgets_any_more(self):
        """An absence: the attribute that never existed is not named in the
        dialog's code, as an attribute or as a string."""
        path = _ROOT / "ogr_gui" / "dialogs" / "material_properties_dialog.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        name = "_" "widgets"
        hits = [n.lineno for n in ast.walk(tree)
                if (isinstance(n, ast.Attribute) and n.attr == name)
                or (isinstance(n, ast.Constant) and n.value == name)]
        assert not hits, hits


# ======================================================================
@_requires_qt
class TestOpeningAndAcceptingIsTheIdentity:
    """D181: a dialog accepted without an edit changes nothing."""

    #: More significant digits than any fixed decimal count keeps, and small
    #: enough that four decimals turn them into zero.
    ODD = (1.2345678901234567, 4.5399929762484854e-05)

    def test_every_builtin_model_round_trips_to_the_bit(self):
        from ogr_core.materials import REGISTRY, Material
        tried, changed, skipped, with_params = 0, [], [], 0
        for mid in sorted(REGISTRY.ids()):
            cls = REGISTRY.get(mid)
            names = list(getattr(cls, "PARAMETERS", {}) or {})
            if not names:
                continue
            with_params += 1
            for i, odd in enumerate(self.ODD):
                params = {}
                for j, name in enumerate(names):
                    default = cls.PARAMETERS[name][0]
                    # Odd but plausible: the default nudged by a factor with
                    # 17 digits, or the small odd value when it is zero.
                    params[name] = (float(default) * (odd if i == 0 else
                                                      1.0 + odd)
                                    if default else odd)
                try:
                    strength = cls(**params)
                except Exception:  # noqa: BLE001 — a model may validate
                    skipped.append(mid)
                    continue
                d = _dialog(Material(name=mid, strength=strength))
                d._ok()
                got = d.result_materials()[0].strength.params
                tried += 1
                diff = {k: (strength.params[k], got.get(k)) for k in names
                        if got.get(k) != strength.params[k]}
                if diff:
                    changed.append((mid, diff))
        # Every model with parameters, at both odd values — measured 15 and
        # 30 on v0.1.192. An equality and not a floor, so a sweep that
        # quietly shrank (a model starting to reject the odd values) would
        # say so instead of passing on what was left.
        assert not skipped and tried == 2 * with_params, (tried, skipped)
        assert with_params >= 15, with_params
        assert not changed, changed[:4]

    def test_the_function_points_round_trip_to_the_bit(self):
        from ogr_core.materials import REGISTRY, Material
        cls = REGISTRY.get("shear_normal_function")
        pts = [(0.0, 5.123456789012345), (100.25, 45.98765432109876),
               (333.3333333333333, 110.00001)]
        strength = cls(points=pts)
        d = _dialog(Material(name="snf", strength=strength))
        d._ok()
        # The table models keep their points on the instance, not in
        # ``params`` (``PARAMETERS`` is empty for them).
        got = d.result_materials()[0].strength.points
        assert [tuple(p) for p in got] == [tuple(p) for p in pts], got

    def test_the_text_reads_back_as_the_same_number(self):
        """What makes the identity robust rather than lucky: a box that
        re-reads its own text (on focus-out, say) gets the same double."""
        from ogr_gui.dialogs.material_properties_dialog import (
            _PreciseSpinBox,
        )
        QApplication.instance() or QApplication([])
        box = _PreciseSpinBox()
        box.setRange(-1e12, 1e12)
        box.setSuffix(" kPa")
        for v in (4.5399929762484854e-05, 0.1, 1.0 / 3.0, 1e-9, -2.5e7,
                  123456.789, math.pi, 0.0):
            box.setValue(v)
            assert box.value() == v, (v, box.value())
            assert box.valueFromText(box.textFromValue(v) + box.suffix()) \
                == v, v

    def test_scientific_notation_can_be_typed(self):
        from PySide6.QtGui import QValidator
        from ogr_gui.dialogs.material_properties_dialog import (
            _PreciseSpinBox,
        )
        QApplication.instance() or QApplication([])
        box = _PreciseSpinBox()
        box.setRange(-1e12, 1e12)
        state = box.validate("4.54e-5", 0)[0]
        assert state == QValidator.State.Acceptable
        assert box.validate("4.54e-", 0)[0] == QValidator.State.Intermediate
        box.lineEdit().setText("4.54e-5")
        box.interpretText()
        assert box.value() == 4.54e-5

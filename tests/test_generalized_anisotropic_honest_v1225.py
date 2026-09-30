# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.225 — Generalized Anisotropic never answers a strength of zero in
silence, and reads its ranges as ABSOLUTE slice base inclinations (defect
D218 of the verification bank, with three findings made while planning it).

THE DEFECTS.

* ``_model_for_angle`` wrapped the building of a rule's model in
  ``except Exception: return None`` and ``shear_strength_ctx`` turned that
  None into τ = 0; an angle no rule held gave the same zero. A model id that
  no longer exists, a parameter it does not know, a gap between two
  ranges: the base had no strength and nothing said so (the class of D56
  and D94).
* The material dialog rebuilt the strength from its editors when it stored
  a material, and this model has none: showing a Generalized Anisotropic
  material and pressing OK left ``rules = []``, and with it τ = 0 at every
  base (finding A).
* The angle was folded into (-90, 90] only when a bedding was subtracted,
  so a support reading the model at the angle of its axis (``atan2``, in
  (-180, 180]) found no rule at 165 degrees and got zero.
* A child that reads the distance to the slope face got no distance,
  because the slicer asks the parent's class, which does not read one
  (finding N).

THE DECISIONS, with their sources:

* The ranges are the reference's "Angle Range" input: absolute slice base
  inclinations measured from the horizontal (its tutorial for the model:
  "Angles in the dialog are measured from horizontal"), ordered counter-
  clockwise from -90 to +90, each starting where the previous one ends.
  v0.1.126 subtracted the bedding of a linked anisotropic surface first,
  which no source supports; in the reference a surface belongs to the other
  input of this model, "Angle or Surface", which OGR does not implement. A
  material that still links one is refused until it is reviewed.
* One rule (``rules.generalized_anisotropic_rules_refusal``) says what a
  valid set of rules is; the dialog, the API and the analysis ask it. The
  model computes with what it is given and RAISES
  ``IncompleteGeneralizedAnisotropic`` where it used to return zero.

THE REFERENCES (rule 1): an identity -- a Generalized Anisotropic model
whose ranges hold Mohr-Coulomb children is, base for base, the Anisotropic
Strength Function with the same rows (the reference describes the two in
the same words; D195 fixed the function's frame) -- and the child alone,
for a single range over every angle.

DISCRIMINATION, measured on the v0.1.224 tree: 24 of the 31 cases fail
there. 12 fail by behaviour: the fold (two cases), the absolute frame, a
limit that arrives in radians, the rules the dialog kept, the child's slope
distance, the surface link refused by the analysis, the API and the dialog,
a new material with no rules, and the API and analysis refusals of a gap.
12 fail by a symbol that did not exist (the rule and the exception). The
two identities, the cache and the controls pass.
"""
from __future__ import annotations

import math

#: The documented example of the Anisotropic Strength Function, written as
#: Generalized Anisotropic ranges of Mohr-Coulomb children.
DOC_ROWS = [(-30.0, 10.0, 35.0), (0.0, 1.0, 20.0), (90.0, 5.0, 10.0)]
#: A dry circle whose bases run from about -18 to +62 degrees.
CIRCLE = (38.0, 22.0, 23.0)
N_SLICES = 30


def _mc_dict(c, phi):
    return {"model_id": "mohr_coulomb",
            "params": {"cohesion": c, "friction_angle": phi}}


def _rules(rows=DOC_ROWS):
    out, lo = [], -90.0
    for hi, c, phi in rows:
        out.append({"angle_min": lo, "angle_max": hi,
                    "model": _mc_dict(c, phi)})
        lo = hi
    return out


def _ga(rules=None):
    from ogr_core.materials.builtin_models import GeneralizedAnisotropic
    return GeneralizedAnisotropic(rules=_rules() if rules is None else rules)


def _ctx(angle_deg, bedding=None):
    from ogr_core.materials.strength_model import SliceContext
    return SliceContext(base_angle_rad=math.radians(angle_deg),
                        bedding_angle_deg=bedding)


def _tau(model, angle_deg, sigma=50.0, bedding=None):
    return model.shear_strength_ctx(sigma, _ctx(angle_deg, bedding))


def _mc(c, phi, sigma=50.0):
    return c + sigma * math.tan(math.radians(phi))


def _project(strength, name="bedded"):
    """The dry slope of ``test_anisotropic_function_ranges_v1218``."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.project import Project
    h, toe = 12.0, 30.0
    crest = toe + h / math.tan(math.radians(30.96))
    ext = Polyline(vertices=[
        Vertex(0, -10), Vertex(60, -10), Vertex(60, h),
        Vertex(crest, h), Vertex(toe, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("generalized")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    mat = Material(name=name, unit_weight=20.0, strength=strength)
    p.materials = [mat]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), mat.id)
    return p


def _fos(strength, method_id="bishop_simplified"):
    from ogr_slip2d.methods import method_registry
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    p = _project(strength)
    circle = SlipCircle(*CIRCLE)
    sl = slice_surface(p, circle, num_slices=N_SLICES)
    return method_registry()[method_id]().compute_fos(p, circle, sl)


def _raises(fn, *exc_types):
    try:
        fn()
    except exc_types as exc:
        return exc
    raise AssertionError(f"{fn} did not raise {exc_types}")


# ======================================================================
class TestTheRule:
    """``rules.generalized_anisotropic_rules_refusal``: one case each."""

    def _code(self, rules):
        from ogr_core.project.rules import generalized_anisotropic_rules_refusal
        why = generalized_anisotropic_rules_refusal(rules)
        return None if why is None else why.code

    def test_the_documented_ranges_are_valid(self):
        assert self._code(_rules()) is None
        assert self._code(_rules([(90.0, 5.0, 25.0)])) is None

    def test_no_rules(self):
        assert self._code([]) == "generalized_rules_empty"
        assert self._code(None) == "generalized_rules_empty"

    def test_a_rule_that_is_not_a_rule(self):
        assert self._code(["-90..90"]) == "generalized_rules_not_rules"
        bad = _rules()
        bad[1]["angle_max"] = "zero"
        assert self._code(bad) == "generalized_rules_not_rules"

    def test_angles_backwards_or_out_of_the_circle(self):
        bad = _rules()
        bad[0]["angle_max"] = -95.0
        assert self._code(bad) == "generalized_rules_angles"
        empty = [{"angle_min": -90.0, "angle_max": -90.0,
                  "model": _mc_dict(1, 20)}] + _rules([(90.0, 5, 10)])
        assert self._code(empty) == "generalized_rules_angles"

    def test_the_first_range_starts_at_minus_ninety(self):
        bad = _rules()
        bad[0]["angle_min"] = -80.0
        assert self._code(bad) == "generalized_rules_start"

    def test_a_gap_and_an_overlap(self):
        gap = _rules()
        gap[1]["angle_min"] = -20.0
        assert self._code(gap) == "generalized_rules_order"
        overlap = _rules()
        overlap[1]["angle_min"] = -40.0
        assert self._code(overlap) == "generalized_rules_order"

    def test_the_last_range_ends_at_ninety(self):
        bad = _rules()
        bad[-1]["angle_max"] = 80.0
        assert self._code(bad) == "generalized_rules_end"

    def test_a_model_missing_or_unbuildable(self):
        missing = _rules()
        missing[2]["model"] = None
        assert self._code(missing) == "generalized_rules_model"
        unknown = _rules()
        unknown[2]["model"] = {"model_id": "a_model_that_does_not_exist",
                               "params": {}}
        assert self._code(unknown) == "generalized_rules_model"
        bad_param = _rules()
        bad_param[0]["model"] = {"model_id": "mohr_coulomb",
                                 "params": {"cohesion": 1.0, "angle": 3.0}}
        assert self._code(bad_param) == "generalized_rules_model"

    def test_the_analysis_refuses_it_by_name(self):
        from ogr_slip2d.analysis_runner import check_analysis_settings
        gap = _rules()
        gap[1]["angle_min"] = -20.0
        problems = check_analysis_settings(_project(_ga(gap)))
        assert any("'bedded'" in s and "Generalized" in s
                   and "-30" in s for s in problems), problems

    def test_the_api_refuses_it(self):
        from ogr_api.catalog import strength_from_spec
        from ogr_api.errors import InvalidArgument
        gap = _rules()
        gap[1]["angle_min"] = -20.0
        _raises(lambda: strength_from_spec(
            {"model": "generalized_anisotropic", "rules": gap}),
            InvalidArgument)
        ok = strength_from_spec({"model": "generalized_anisotropic",
                                 "rules": _rules()})
        assert len(ok.rules) == 3


class TestTheModelNeverAnswersZero:

    def test_an_angle_no_rule_holds_raises(self):
        from ogr_core.materials.builtin_models import (
            IncompleteGeneralizedAnisotropic)
        gap = _rules()
        gap[1]["angle_min"] = -20.0
        m = _ga(gap)
        exc = _raises(lambda: _tau(m, -25.0),
                      IncompleteGeneralizedAnisotropic)
        assert "-25" in str(exc)
        assert math.isclose(_tau(m, -10.0), _mc(1.0, 20.0), rel_tol=1e-12)

    def test_a_model_that_cannot_be_built_raises(self):
        from ogr_core.materials.builtin_models import (
            IncompleteGeneralizedAnisotropic)
        bad = _rules()
        bad[2]["model"] = {"model_id": "a_model_that_does_not_exist",
                           "params": {}}
        m = _ga(bad)
        exc = _raises(lambda: _tau(m, 45.0),
                      IncompleteGeneralizedAnisotropic)
        assert "rule 3" in str(exc)
        assert math.isclose(_tau(m, -45.0), _mc(10.0, 35.0), rel_tol=1e-12)

    def test_no_rules_raises_without_a_context_too(self):
        from ogr_core.materials.builtin_models import (
            IncompleteGeneralizedAnisotropic)
        _raises(lambda: _ga([]).shear_strength(50.0),
                IncompleteGeneralizedAnisotropic)


class TestTheAngleIsAbsoluteAndFolded:

    def test_each_range_holds_its_own_child(self):
        m = _ga()
        for angle, (c, phi) in ((-89.0, (10.0, 35.0)), (-29.5, (1.0, 20.0)),
                                (-5.0, (1.0, 20.0)), (0.5, (5.0, 10.0)),
                                (89.9, (5.0, 10.0))):
            assert math.isclose(_tau(m, angle), _mc(c, phi),
                                rel_tol=1e-12), angle

    def test_a_limit_belongs_to_the_lower_range(self):
        m = _ga()
        assert math.isclose(_tau(m, -30.0), _mc(10.0, 35.0), rel_tol=1e-12)
        assert math.isclose(_tau(m, 0.0), _mc(1.0, 20.0), rel_tol=1e-12)

    def test_a_bedding_in_the_context_does_not_move_the_range(self):
        """v0.1.126 subtracted it: a base at 10 degrees under a bedding at
        25 was read at -15, in the second range."""
        m = _ga()
        assert _tau(m, 10.0, bedding=25.0) == _tau(m, 10.0)
        assert math.isclose(_tau(m, 10.0, bedding=25.0), _mc(5.0, 10.0),
                            rel_tol=1e-12)

    def test_an_axis_pointing_left_is_the_same_plane(self):
        m = _ga()
        for axis, plane in ((165.0, -15.0), (-135.0, 45.0), (120.0, -60.0)):
            assert _tau(m, axis) == _tau(m, plane), (axis, plane)

    def test_a_support_reads_the_folded_angle(self):
        from ogr_core.support.bond import soil_shear_strength_at
        p = _project(_ga())
        down_right = soil_shear_strength_at(
            p, 40.0, -5.0, 60.0, axis_angle_rad=math.radians(-15.0))
        up_left = soil_shear_strength_at(
            p, 40.0, -5.0, 60.0, axis_angle_rad=math.radians(165.0))
        assert up_left == down_right, (up_left, down_right)
        assert math.isclose(down_right, _mc(1.0, 20.0, 60.0),
                            rel_tol=1e-12), down_right


class TestIdentities:
    """Rule 1: the same material written two ways."""

    def test_mohr_coulomb_ranges_are_the_anisotropic_function(self):
        from ogr_core.materials.builtin_models import (
            AnisotropicStrengthFunction)
        from ogr_slip2d.methods import method_registry
        asf = AnisotropicStrengthFunction(rows=DOC_ROWS)
        for mid in sorted(method_registry()):
            a = _fos(_ga(), mid).fos
            b = _fos(asf, mid).fos
            assert a is not None and math.isclose(a, b, rel_tol=1e-12), (
                mid, a, b)

    def test_one_range_over_every_angle_is_the_child(self):
        from ogr_core.materials.builtin_models import MohrCoulomb
        a = _fos(_ga(_rules([(90.0, 4.0, 27.0)]))).fos
        b = _fos(MohrCoulomb(cohesion=4.0, friction_angle=27.0)).fos
        assert math.isclose(a, b, rel_tol=1e-12), (a, b)

    def test_a_child_gets_the_slope_distance_it_reads(self):
        """Finding N: the slicer asks the parent whether any material reads
        the distance to the slope; the parent now answers for its child."""
        from ogr_core.materials.builtin_models import (
            GeneralizedAnisotropic, UndrainedDistanceToSlope)
        child = UndrainedDistanceToSlope(cohesion_top=8.0,
                                         cohesion_change=3.0)
        ga = GeneralizedAnisotropic(rules=[{
            "angle_min": -90.0, "angle_max": 90.0, "model": child.to_dict()}])
        assert ga.NEEDS_SLOPE_DISTANCE is True
        assert ga.NEEDS_LAYER_TOP is False
        a = _fos(ga).fos
        b = _fos(child).fos
        assert math.isclose(a, b, rel_tol=1e-12), (a, b)


class TestTheCache:

    def test_a_warm_model_answers_what_a_fresh_one_does(self):
        warm = _ga()
        for angle in (-80.0, -30.0, -12.5, 0.0, 7.0, 55.0, 90.0, 165.0):
            assert _tau(warm, angle) == _tau(_ga(), angle), angle

    def test_a_rule_edited_in_place_is_rebuilt(self):
        m = _ga()
        before = _tau(m, 45.0)
        m.rules[2]["model"]["params"]["cohesion"] = 50.0
        after = _tau(m, 45.0)
        assert math.isclose(before, _mc(5.0, 10.0), rel_tol=1e-12)
        assert math.isclose(after, _mc(50.0, 10.0), rel_tol=1e-12)


class TestALinkedSurface:
    """A Generalized Anisotropic material that links an anisotropic
    surface is refused until reviewed; the API no longer links one."""

    def _with_surface(self):
        from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
        p = _project(_ga())
        b = Boundary(polyline=Polyline(
            vertices=[Vertex(0.0, 5.0), Vertex(60.0, 20.0)], closed=False),
            btype=BoundaryType.ANISOTROPIC_SURFACE)
        p.add_boundary(b)
        p.materials[0].anisotropic_surface_id = b.id
        return p, b

    def test_the_analysis_refuses_it(self):
        from ogr_slip2d.analysis_runner import check_analysis_settings
        p, _b = self._with_surface()
        problems = check_analysis_settings(p)
        assert any("'bedded'" in s and "0.1.225" in s for s in problems), (
            problems)
        p.materials[0].anisotropic_surface_id = None
        assert not any("0.1.225" in s for s in check_analysis_settings(p))

    def test_the_api_will_not_link_one(self):
        from ogr_api.errors import Conflict
        from ogr_api.ops.model import _apply_material_fields
        p, b = self._with_surface()
        m = p.materials[0]
        m.anisotropic_surface_id = None
        _raises(lambda: _apply_material_fields(
            p, m, {"anisotropic_surface_id": b.id}, creating=False),
            Conflict)

    def test_the_two_bedded_models_still_read_one(self):
        from ogr_core.project.rules import reads_anisotropic_surface
        assert reads_anisotropic_surface("anisotropic_linear")
        assert reads_anisotropic_surface("snowden_anisotropic_linear")
        assert not reads_anisotropic_surface("generalized_anisotropic")
        assert not reads_anisotropic_surface(_ga())


class TestTheDialog:
    """Finding A, the surface link and the refusal texts."""

    def _dialog(self, *strengths, surface=False):
        from PySide6.QtWidgets import QApplication
        from ogr_core.materials import Material
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog)
        QApplication.instance() or QApplication([])
        mats = [Material(name=f"m{i}", unit_weight=20.0, strength=s)
                for i, s in enumerate(strengths)]
        if surface:
            mats[0].anisotropic_surface_id = "a-surface"
        dlg = MaterialPropertiesDialog(mats)
        dlg.list.setCurrentRow(0)
        # v0.1.231 -- the lambda keeps the LIST, not the dialog: capturing
        # the dialog made a cycle the garbage collector broke at any later
        # moment, inside another test; a Qt object destroyed there is the
        # likely cause of the segfault of the 3.12 job of v0.1.230.
        calls = dlg.accepted_calls = []
        dlg.accept = lambda: calls.append(True)
        return dlg

    def test_ok_keeps_the_rules_of_the_material_on_screen(self):
        dlg = self._dialog(_ga())
        dlg._ok()
        assert dlg.accepted_calls == [True]
        kept = dlg.result_materials()[0].strength
        assert kept.rules == _rules(), kept.rules
        assert math.isclose(_tau(kept, 45.0), _mc(5.0, 10.0), rel_tol=1e-12)

    def test_an_untouched_broken_material_does_not_block_ok(self):
        from ogr_core.materials.builtin_models import MohrCoulomb
        gap = _rules()
        gap[1]["angle_min"] = -20.0
        dlg = self._dialog(MohrCoulomb(cohesion=5.0, friction_angle=30.0),
                           _ga(gap))
        dlg.list.setCurrentRow(1)
        dlg.list.setCurrentRow(0)
        dlg._ok()
        assert dlg.accepted_calls == [True]

    def test_a_new_generalized_material_without_rules_is_refused(self):
        from ogr_core.materials.builtin_models import MohrCoulomb
        dlg = self._dialog(MohrCoulomb(cohesion=5.0, friction_angle=30.0))
        dlg.cbo_strength.setCurrentIndex(
            dlg.cbo_strength.findData("generalized_anisotropic"))
        dlg._ok()
        assert dlg.accepted_calls == []
        assert not dlg.lbl_strength_problem.isHidden()

    def test_a_linked_surface_is_shown_and_removed(self):
        dlg = self._dialog(_ga(), surface=True)
        assert "0.1.225" in dlg.lbl_strength_problem.text()
        dlg._ok()
        assert dlg.accepted_calls == [True]
        assert dlg.result_materials()[0].anisotropic_surface_id is None

    def test_every_refusal_text_has_its_spanish(self):
        """The dialog translates these through a variable, which the
        coverage test cannot see; this is its guard."""
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog)
        from ogr_gui.i18n import _DICTS
        es = _DICTS["es"]
        missing = [t for t in MaterialPropertiesDialog._TABLE_REFUSALS.values()
                   if t not in es]
        assert not missing, missing

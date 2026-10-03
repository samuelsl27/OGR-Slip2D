# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D231a — Generalized Anisotropic gains the reference's other input, "Angle or
Surface": a base strength, joints at an angle, each with its strength, and a
mapping between them.

**The invariant.** With the "Angle or Surface" input, a slice base at an
angle δ (acute) from a joint has the strength

    τ_j = (1 − t)·τ_joint(σ'ₙ) + t·τ_base(σ'ₙ),

t = 0 on the joint and 1 on the base: with A and B as Anisotropic Linear
(Mercer 2012, 2013), δ/90 for the linear mapping and sin²δ for the cosine
one (the S-shaped curve of the reference's figure of the three functions).
Several joints: the lowest τ_j ("Worst Case") or the joint with the
smallest δ, the first of the list on a tie ("Closest"); then, with "use the
base where it is weaker", min(τ, τ_base). Without a slice, the weakest of
the base and the joints. The design factors reach the base and each joint by
their own category. The reference's documentation of the model describes the
input; where it is silent (the blend of two arbitrary children, the tie) or
contradicts its own figure (the cosine), the decisions are written in D231.

What each class pins, and against what (rule 1)
-----------------------------------------------
1. Identities: one A and B joint with Mohr-Coulomb children IS Anisotropic
   Linear, in τ and in the nine methods; with non-linear children, without
   the weaker-base switch, it IS Snowden (Mercer 2012, 2013) with A1 = A2,
   B1 = B2; the linear mapping IS A and B with A = 0 and B = 90.
2. Closed forms: the cosine mapping, by hand; worst case and closest, the
   tie; the weaker base; no slice.
3. The reference's Tutorial 20 (Generalized Anisotropic, γ = 20, Soil Mass
   c = 5, φ = 30, Bedding c = 0, φ = 20 within 10° of horizontal):
   "Angle Range" on the critical circle of OGR's Auto Refine search gives
   Bishop within 0.5 % of its published 1.478 (an external anchor; OGR's
   search finds 1.4753), and the equivalent "Angle or Surface" (a joint at
   0°, A = B = 10) gives the same factor in the nine methods.
4. Rule 7: the mapping, the joint selection and the weaker-base switch each
   move the number; the design factors give F/γ with c′ = tan φ′ factors.
5. The rule, the links (resolution, API, delete, import), the water (the
   parent's), the file and the dialog.

DISCRIMINATION, measured on the v0.1.247 tree: see the changelog of
v0.1.248.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import copy
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_REL = 1e-12
#: The dry slope of ``test_generalized_links_v1228``, its circle (bases from
#: about -18 to +62 degrees).
_CIRCLE = dict(centre_x=38.0, centre_y=22.0, radius=23.0)
#: Tutorial 20: OGR's critical circle (Auto Refine, Bishop, 0.1.247).
_T20_CIRCLE = dict(centre_x=39.26562163803558, centre_y=82.29999970154077,
                   radius=52.858162399921724)
_T20_PUBLISHED = 1.478


def _close(a, b, rel=_REL):
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-12)


def _mc(c, phi):
    from ogr_core.materials import MohrCoulomb
    return MohrCoulomb(cohesion=c, friction_angle=phi)


def _ga(base, joints, **kw):
    """An "Angle or Surface" model: ``base`` a model, ``joints`` a list of
    (angle, A, B, model)."""
    from ogr_core.materials.builtin_models import GeneralizedAnisotropic
    kw.setdefault("mapping", "ab")
    return GeneralizedAnisotropic(
        input_type="angle_or_surface", base={"model": base.to_dict()},
        joints=[{"angle": a, "A": A, "B": B, "model": m.to_dict()}
                for a, A, B, m in joints], **kw)


def _ctx(deg):
    from ogr_core.materials.strength_model import SliceContext
    return SliceContext(base_angle_rad=math.radians(deg))


def _tau(model, deg, sigma):
    return model.shear_strength_ctx(sigma, _ctx(deg))


def _angles():
    return [a + 0.37 for a in range(-90, 90, 7)]


def _slope(strength):
    import test_generalized_links_v1228 as L
    from ogr_core.materials import Material
    p = L._slope("aos")
    m = Material(name="bedded", unit_weight=20.0, strength=strength)
    p.materials = [m]
    L._paint(p, m)
    return p


def _fos(p, method="bishop_simplified", circle=_CIRCLE, n=50):
    from ogr_core.project import prepare_analysis_project
    from ogr_slip2d.methods import get_method
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.surface import SlipCircle
    work = prepare_analysis_project(p)[0]
    c = SlipCircle(**circle)
    sl = slice_surface(work, c, num_slices=n)
    r = get_method(method)(tolerance=1e-12).compute_fos(work, c, sl)
    assert r.fos is not None, (method, getattr(r, "reason", None))
    return float(r.fos)


def _nine():
    from ogr_slip2d.methods import method_registry
    names = sorted(method_registry())
    assert len(names) == 9, names
    return names


# ======================================================================
class TestIdentities:

    def _al_pair(self):
        from ogr_core.materials.builtin_models import AnisotropicLinear
        al = AnisotropicLinear(c1=2.0, phi1=18.0, c2=12.0, phi2=34.0,
                               bedding_angle=20.0, A=8.0, B=27.0)
        ga = _ga(_mc(12.0, 34.0), [(20.0, 8.0, 27.0, _mc(2.0, 18.0))])
        return al, ga

    def test_one_ab_joint_is_anisotropic_linear_in_tau(self):
        al, ga = self._al_pair()
        for deg in _angles():
            for s in (0.0, 13.0, 150.0):
                a, b = _tau(al, deg, s), _tau(ga, deg, s)
                assert _close(a, b, 1e-14), (deg, s, a, b)

    def test_and_in_the_nine_methods(self):
        al, ga = self._al_pair()
        for m in _nine():
            a, b = _fos(_slope(al), m), _fos(_slope(ga), m)
            assert _close(a, b), (m, a, b)

    def test_without_the_weaker_base_it_is_snowden(self):
        import test_snowden_reference_v1229 as S
        from ogr_core.materials.strength_model import StrengthModel
        sn = S._snowden(bedding_angle=10.0, A1=12.0, B1=33.0, A2=12.0,
                        B2=33.0)
        ga = _ga(StrengthModel.from_dict(S.ROCK_MASS),
                 [(10.0, 12.0, 33.0, StrengthModel.from_dict(S.BEDDING))],
                 use_base_if_weaker=False)
        for deg in _angles():
            for s in (0.0, 40.0, 180.0, 400.0):
                a = sn.shear_strength_ctx(s, S._ctx(deg))
                b = _tau(ga, deg, s)
                assert _close(a, b, 1e-13), (deg, s, a, b)

    def test_linear_is_a_and_b_with_0_and_90(self):
        lin = _ga(_mc(12.0, 34.0), [(-15.0, 0.0, 0.0, _mc(2.0, 18.0))],
                  mapping="linear")
        ab = _ga(_mc(12.0, 34.0), [(-15.0, 0.0, 90.0, _mc(2.0, 18.0))])
        for deg in _angles():
            assert _tau(lin, deg, 77.0) == _tau(ab, deg, 77.0), deg


# ======================================================================
class TestClosedForms:

    def test_the_cosine_mapping_by_hand(self):
        base, joint = _mc(12.0, 34.0), _mc(2.0, 18.0)
        ga = _ga(base, [(30.0, 0.0, 0.0, joint)], mapping="cosine")
        s = 60.0
        tb, tj = base.shear_strength(s), joint.shear_strength(s)
        for deg in (30.0, 75.0, 120.0, -60.0, 41.0, -5.5):
            d = abs(deg - 30.0) % 180.0
            d = 180.0 - d if d > 90.0 else d
            t = math.sin(math.radians(d)) ** 2
            assert _close(_tau(ga, deg, s), (1 - t) * tj + t * tb, 1e-14), deg
        # The ends and the middle of the S.
        assert _tau(ga, 30.0, s) == tj
        assert _close(_tau(ga, -60.0, s), tb, 1e-14)
        assert _close(_tau(ga, 75.0, s), 0.5 * (tj + tb), 1e-14)

    def test_worst_case_closest_and_the_tie(self):
        weak, strong = _mc(1.0, 15.0), _mc(6.0, 25.0)
        base = _mc(20.0, 40.0)
        joints = [(60.0, 40.0, 40.0, strong), (0.0, 40.0, 40.0, weak)]
        s = 50.0
        worst = _ga(base, joints)
        closest = _ga(base, joints, joint_selection="closest")
        # At 25°: δ = 35 to the first, 25 to the second; both inside A.
        assert _tau(worst, 25.0, s) == weak.shear_strength(s)
        assert _tau(closest, 25.0, s) == weak.shear_strength(s)
        # At 40°: δ = 20 to the first (strong), 40 to the second (weak).
        assert _tau(worst, 40.0, s) == weak.shear_strength(s)
        assert _tau(closest, 40.0, s) == strong.shear_strength(s)
        # A tie: a base at 0° and joints at +40° and −40°, δ = 40 to both;
        # the first of the list answers, whichever it is.
        tie = [(40.0, 50.0, 50.0, strong), (-40.0, 50.0, 50.0, weak)]
        first = _ga(base, tie, joint_selection="closest")
        assert _tau(first, 0.0, s) == strong.shear_strength(s)
        tie.reverse()
        second = _ga(base, tie, joint_selection="closest")
        assert _tau(second, 0.0, s) == weak.shear_strength(s)
        # A tie through radians: 30° comes back as 29.999999999999996, and
        # 30° from joints at 60° and 0° is still a tie (within 1e-9°).
        assert _tau(closest, 30.0, s) == strong.shear_strength(s)

    def test_the_weaker_base_takes_over(self):
        base, joint = _mc(1.0, 15.0), _mc(10.0, 35.0)    # a strong joint
        on = _ga(base, [(0.0, 10.0, 10.0, joint)])
        off = _ga(base, [(0.0, 10.0, 10.0, joint)], use_base_if_weaker=False)
        s = 80.0
        assert _tau(on, 3.0, s) == base.shear_strength(s)
        assert _tau(off, 3.0, s) == joint.shear_strength(s)

    def test_without_a_slice_the_weakest(self):
        base, j1, j2 = _mc(5.0, 30.0), _mc(0.0, 20.0), _mc(3.0, 25.0)
        ga = _ga(base, [(0.0, 5.0, 5.0, j1), (40.0, 5.0, 5.0, j2)])
        for s in (0.0, 10.0, 300.0):
            assert ga.shear_strength(s) == min(
                m.shear_strength(s) for m in (base, j1, j2)), s


# ======================================================================
def _tutorial20(angle_or_surface=False):
    """Tutorial 20 of the reference, as its pages 20-3 to 20-6 give it."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import GeneralizedAnisotropic
    from ogr_core.project import Project
    ext = Polyline(vertices=[Vertex(0, 0), Vertex(130, 0), Vertex(130, 50),
                             Vertex(80, 50), Vertex(33.5, 30), Vertex(0, 30)],
                   closed=True)
    ext.ensure_ccw()
    p = Project("Tutorial 20")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    soil = Material(name="Soil Mass", unit_weight=20.0,
                    strength=_mc(5.0, 30.0))
    bed = Material(name="Bedding", unit_weight=20.0, strength=_mc(0.0, 20.0))

    def link(m, **kw):
        return {"material_id": m.id, "model": m.strength.to_dict(), **kw}
    if angle_or_surface:
        st = GeneralizedAnisotropic(
            input_type="angle_or_surface", base=link(soil),
            joints=[link(bed, angle=0.0, A=10.0, B=10.0)], mapping="ab")
    else:
        st = GeneralizedAnisotropic(rules=[
            link(soil, angle_min=-90.0, angle_max=-10.0),
            link(bed, angle_min=-10.0, angle_max=10.0),
            link(soil, angle_min=10.0, angle_max=90.0)])
    g = Material(name="Material 3", unit_weight=20.0, strength=st)
    p.materials = [soil, bed, g]
    p.assign_material_at(60.0, 20.0, g.id)
    return p


class TestTutorial20:

    def test_angle_range_reproduces_the_published_factor(self):
        f = _fos(_tutorial20(), circle=_T20_CIRCLE, n=25)
        assert abs(f / _T20_PUBLISHED - 1.0) < 0.005, f

    def test_the_equivalent_angle_or_surface_is_the_same(self):
        for m in _nine():
            a = _fos(_tutorial20(), m, circle=_T20_CIRCLE, n=25)
            b = _fos(_tutorial20(True), m, circle=_T20_CIRCLE, n=25)
            assert _close(a, b), (m, a, b)


# ======================================================================
class TestRule7:

    def _f(self, **kw):
        # The closer joint is the stronger one where both are within A, so
        # "Worst Case" and "Closest" answer differently there.
        joints = [(20.0, 25.0, 40.0, _mc(6.0, 28.0)),
                  (50.0, 25.0, 40.0, _mc(1.0, 16.0))]
        return _fos(_slope(_ga(_mc(12.0, 34.0), joints, **kw)))

    def test_every_choice_moves_the_number(self):
        ab = self._f()
        assert abs(self._f(mapping="cosine") / ab - 1.0) > 1e-3
        assert abs(self._f(mapping="linear") / ab - 1.0) > 1e-3
        assert abs(self._f(joint_selection="closest") / ab - 1.0) > 1e-4

    def test_the_weaker_base_moves_the_number(self):
        joints = [(20.0, 8.0, 27.0, _mc(30.0, 40.0))]
        on = _fos(_slope(_ga(_mc(5.0, 25.0), joints)))
        off = _fos(_slope(_ga(_mc(5.0, 25.0), joints,
                              use_base_if_weaker=False)))
        assert off / on - 1.0 > 0.01, (on, off)

    def test_the_design_factors_reach_base_and_joints(self):
        # c′ and tan φ′ both / 1.25 on base and joint, the weight untouched
        # (DA1-C2): every strength / 1.25, so Γ = F / 1.25.
        st = _ga(_mc(12.0, 34.0), [(20.0, 8.0, 27.0, _mc(2.0, 18.0))])
        p = _slope(st)
        f = _fos(p)
        ds = p.settings.design_standard
        ds.enabled = True
        ds.apply_preset("eurocode7_da1c2")
        for m in ("bishop_simplified", "spencer"):
            g = _fos(p, m)
            ref = _fos(_slope(copy.deepcopy(st)), m) / 1.25
            assert _close(g, ref, 1e-9), (m, g, ref)
        assert f > 1.0


# ======================================================================
class TestTheRule:

    def _code(self, **kw):
        from ogr_core.project.rules import strength_model_refusal
        base = kw.pop("base", _mc(12.0, 34.0))
        joints = kw.pop("joints", [(20.0, 8.0, 27.0, _mc(2.0, 18.0))])
        why = strength_model_refusal(_ga(base, joints, **kw), "G")
        return None if why is None else why.code

    def test_its_codes(self):
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        from ogr_core.project.rules import strength_model_refusal
        assert self._code() is None
        # Changed on purpose in v0.1.249 (D231b): joints by surface are
        # computed, and a joint by surface without its surface is refused.
        assert self._code(definition="surface") == \
            "generalized_aos_joint_surface"
        assert self._code(mapping="sigmoid") == "generalized_aos_mapping"
        assert self._code(joint_selection="best") == \
            "generalized_aos_selection"
        assert self._code(joints=[]) == "generalized_aos_joints"
        assert self._code(joints=[(0.0, 30.0, 20.0, _mc(1.0, 1.0))]) == \
            "generalized_aos_ab"
        assert self._code(joints=[(0.0, 30.0, 95.0, _mc(1.0, 1.0))]) == \
            "generalized_aos_ab"
        # A and B are not read by the other mappings.
        assert self._code(joints=[(0.0, 30.0, 20.0, _mc(1.0, 1.0))],
                          mapping="cosine") is None
        no_base = GeneralizedAnisotropic(
            input_type="angle_or_surface", base=None,
            joints=[{"angle": 0.0, "A": 1.0, "B": 2.0,
                     "model": _mc(1.0, 1.0).to_dict()}])
        assert strength_model_refusal(no_base, "G").code == \
            "generalized_aos_base"
        nested = _ga(_mc(1.0, 1.0), [(0.0, 1.0, 2.0, GeneralizedAnisotropic(
            rules=[{"angle_min": -90, "angle_max": 90,
                    "model": _mc(1.0, 1.0).to_dict()}]))])
        assert strength_model_refusal(nested, "G").code == \
            "generalized_aos_nested"
        odd = GeneralizedAnisotropic(input_type="sideways")
        assert strength_model_refusal(odd, "G").code == \
            "generalized_input_type"


# ======================================================================
class TestLinksWaterAndFile:

    def _project(self):
        from ogr_core.materials import Material
        p = _slope(_mc(1.0, 1.0))
        rock = Material(name="Rock", unit_weight=20.0,
                        strength=_mc(12.0, 34.0))
        bed = Material(name="Bed", unit_weight=20.0, strength=_mc(2.0, 18.0))
        g = p.materials[0]
        stale = _mc(99.0, 1.0).to_dict()
        from ogr_core.materials.builtin_models import GeneralizedAnisotropic
        g.strength = GeneralizedAnisotropic(
            input_type="angle_or_surface",
            base={"material_id": rock.id, "model": stale},
            joints=[{"angle": 20.0, "A": 8.0, "B": 27.0,
                     "material_id": bed.id, "model": stale}])
        p.materials = [g, rock, bed]
        return p, g, rock, bed

    def test_the_materials_decide_not_the_stale_copies(self):
        p, _g, _r, _b = self._project()
        al = TestIdentities()._al_pair()[0]
        for m in ("bishop_simplified", "spencer"):
            a, b = _fos(p, m), _fos(_slope(al), m)
            assert _close(a, b), (m, a, b)

    def test_a_link_to_nothing_is_refused(self):
        from ogr_core.project.rules import generalized_links_refusal
        p, g, rock, _b = self._project()
        p.materials = [g, rock]
        why = generalized_links_refusal(g, p.materials)
        assert why is not None and "joint 1" in why.message

    def test_the_water_is_the_parents(self):
        import ogr_slip2d.slicer as S
        p, g, rock, _b = self._project()
        g.strength = g.strength.replaced(use_parent_water=False)
        assert g.strength.linked_material_id(20.0) is None
        assert S.water_material(p, g, math.radians(20.0)) is g

    def test_the_file_round_trip_and_an_old_file(self):
        from ogr_core.materials.strength_model import StrengthModel
        _p, g, _r, _b = self._project()
        d = g.strength.to_dict()
        back = StrengthModel.from_dict(d)
        assert back.to_dict() == d
        for k in ("input_type", "base", "joints", "definition", "mapping",
                  "joint_selection", "use_base_if_weaker"):
            del d[k]
        old = StrengthModel.from_dict(d)
        assert old.input_type == "angle_range" and not old.angle_or_surface

    def test_the_api_links_by_name_and_a_delete_moves_the_link(self):
        from ogr_api import Workspace, call
        ws = Workspace()
        pid = call(ws, "project_new", name="AOS")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[0, -10], [60, -10], [60, 12], [50, 12], [30, 0],
                         [0, 0]],
            "materials": [
                {"name": "Rock", "unit_weight": 20.0,
                 "strength": {"model": "mohr_coulomb",
                              "params": {"cohesion": 12.0,
                                         "friction_angle": 34.0}}},
                {"name": "Bed", "unit_weight": 20.0,
                 "strength": {"model": "mohr_coulomb",
                              "params": {"cohesion": 2.0,
                                         "friction_angle": 18.0}}},
                {"name": "Bed2", "unit_weight": 20.0,
                 "strength": {"model": "mohr_coulomb",
                              "params": {"cohesion": 3.0,
                                         "friction_angle": 19.0}}},
                {"name": "Bedded", "unit_weight": 20.0, "strength": {
                    "model": "generalized_anisotropic",
                    "input_type": "angle_or_surface",
                    "base": {"material": "rock"},
                    "joints": [{"angle": 20, "A": 8, "B": 27,
                                "material": "Bed"}]}}]})
        mats = {m.name: m for m in ws.get(pid).project.materials}
        st = mats["Bedded"].strength
        assert st.base["material_id"] == mats["Rock"].id
        assert st.joints[0]["material_id"] == mats["Bed"].id
        assert st.joints[0]["model"] == mats["Bed"].strength.to_dict()
        call(ws, "material_delete", project_id=pid, material="Bed",
             reassign_to="Bed2")
        mats = {m.name: m for m in ws.get(pid).project.materials}
        st = mats["Bedded"].strength
        assert st.joints[0]["material_id"] == mats["Bed2"].id
        assert st.angle_or_surface and st.joints[0]["angle"] == 20

    def test_the_import_relinks_the_base(self):
        from ogr_core.materials import Material
        from ogr_core.project import Project
        from ogr_core.project.properties_import import import_properties
        _p, g, rock, bed = self._project()
        src = Project("source")
        src.materials = [g, rock, bed]
        dst = Project("destination")
        dst.materials = [Material(name="rock", strength=_mc(7.0, 31.0))]
        import_properties(dst, src, support_types=False, names=["bedded"])
        got = next(m for m in dst.materials if m.name == "bedded").strength
        assert got.angle_or_surface
        assert got.base["material_id"] == dst.materials[0].id
        assert got.base["model"] == dst.materials[0].strength.to_dict()
        assert "material_id" not in got.joints[0]


# ======================================================================
class TestTheDialog:

    def _dialog(self, materials, row):
        from PySide6.QtWidgets import QApplication
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog)
        QApplication.instance() or QApplication([])
        dlg = MaterialPropertiesDialog(materials)
        dlg.list.setCurrentRow(row)
        calls = dlg.accepted_calls = []
        dlg.accept = lambda: calls.append(True)
        return dlg

    def _materials(self):
        _p, g, rock, bed = TestLinksWaterAndFile()._project()
        return [rock, bed, g]

    def test_it_shows_the_joints_and_keeps_both_inputs(self):
        from PySide6.QtCore import Qt
        mats = self._materials()
        mats[2].strength = mats[2].strength.replaced(
            mapping="cosine",
            rules=[{"angle_min": -90.0, "angle_max": 90.0,
                    "model": _mc(3.0, 3.0).to_dict()}])
        dlg = self._dialog(mats, 2)
        panel = dlg.param_panel
        assert len(panel.table_headers()) == 4
        assert panel.is_unchanged()
        # A and B are not editable with the cosine mapping (rule 7).
        assert not panel._table.item(0, 1).flags() & Qt.ItemIsEditable
        # Surface is shown and cannot be taken yet.
        cbo = panel._ga["definition"]
        assert not cbo.model().item(cbo.findData("surface")).isEnabled()
        before = panel.get_params()
        panel._ga["input"].setCurrentIndex(
            panel._ga["input"].findData("angle_range"))
        assert panel.table_headers()[0] == "Angle to (°)"
        mid = panel.get_params()
        assert mid["joints"] == before["joints"]
        assert mid["mapping"] == "cosine"
        panel._ga["input"].setCurrentIndex(
            panel._ga["input"].findData("angle_or_surface"))
        assert panel.get_params()["rules"] == before["rules"]

    def test_ok_stores_what_is_on_screen(self):
        mats = self._materials()
        dlg = self._dialog(mats, 2)
        panel = dlg.param_panel
        sel = panel._ga["selection"]
        sel.setCurrentIndex(sel.findData("closest"))
        panel._ga["weaker"].setChecked(False)
        assert not panel.is_unchanged()
        dlg._ok()
        assert dlg.accepted_calls == [True]
        st = dlg.result_materials()[2].strength
        assert st.angle_or_surface
        assert (st.joint_selection, st.use_base_if_weaker) == ("closest",
                                                               False)
        assert st.base["material_id"] == mats[0].id
        assert st.joints[0]["material_id"] == mats[1].id

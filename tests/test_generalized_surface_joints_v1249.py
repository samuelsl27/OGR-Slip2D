# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
D231b — the joints of a Generalized Anisotropic "Angle or Surface" function
can follow an anisotropic surface of the model instead of a fixed angle.

**The invariant.** A joint defined by a surface takes, at each slice base,
the orientation of its surface at the point CLOSEST to the base and, when
that point is a vertex, the orientation of the segment drawn first; then the
strength is computed as for a joint by angle. The reference's documentation
of the model: "The point on the anisotropic surface that is closest to the
given slice base is found, and the angle of the anisotropic surface at that
point is taken as the angle of anisotropy for the given slice base". It is
the rule OGR has applied to anisotropic surfaces since v0.1.126
(``anisotropy_angle_at``), read at the middle of the base by the slicer and
at the point by the supports (D228).

What each class pins, and against what (rule 1)
-----------------------------------------------
1. Identity: a straight surface at θ is the joint by angle θ, in the nine
   methods.
2. The rule of the surface: at a kink, the segment drawn first, so drawing
   the surface the other way round changes the strength there.
3. A support reads the surface's orientation at its own point.
4. A joint naming a surface the model does not have is refused before the
   analysis; deleting a surface a joint reads is refused by the API and by
   the window; the file keeps the surface; the dialog edits it.

DISCRIMINATION, measured on the v0.1.248 tree: see the changelog of
v0.1.249.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_REL = 1e-12
_THETA = 20.0


def _close(a, b, rel=_REL):
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-12)


def _mc(c, phi):
    from ogr_core.materials import MohrCoulomb
    return MohrCoulomb(cohesion=c, friction_angle=phi)


def _surface(p, points):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    b = Boundary(polyline=Polyline(vertices=[Vertex(x, y) for x, y in points],
                                   closed=False),
                 btype=BoundaryType.ANISOTROPIC_SURFACE)
    p.add_boundary(b)
    return b


def _ga(by_surface=None, angle=_THETA):
    from ogr_core.materials.builtin_models import GeneralizedAnisotropic
    joint = {"A": 8.0, "B": 27.0, "model": _mc(2.0, 18.0).to_dict()}
    if by_surface is not None:
        joint["surface_id"] = by_surface
    else:
        joint["angle"] = angle
    return GeneralizedAnisotropic(
        input_type="angle_or_surface",
        definition="surface" if by_surface is not None else "angle",
        base={"model": _mc(12.0, 34.0).to_dict()}, joints=[joint])


def _slope_with(strength_of, points=((0.0, -10.0), (60.0, 11.84))):
    """The slope of the v1248 test, a straight anisotropic surface, and a
    material whose strength ``strength_of(surface id)`` gives."""
    import test_generalized_angle_or_surface_v1248 as A
    p = A._slope(_mc(1.0, 1.0))
    b = _surface(p, points)
    p.materials[0].strength = strength_of(b.id)
    return p, b


def _straight_points(theta=_THETA):
    x0, y0, length = 0.0, -10.0, 70.0
    t = math.radians(theta)
    return ((x0, y0), (x0 + length * math.cos(t), y0 + length * math.sin(t)))


# ======================================================================
class TestIdentity:

    def test_a_straight_surface_is_its_angle_in_the_nine_methods(self):
        import test_generalized_angle_or_surface_v1248 as A
        pts = _straight_points()
        for m in A._nine():
            p_s, _b = _slope_with(lambda sid: _ga(sid), pts)
            p_a, _b = _slope_with(lambda sid: _ga(None), pts)
            a, b = A._fos(p_a, m), A._fos(p_s, m)
            assert _close(a, b), (m, a, b)

    def test_the_slices_carry_the_orientation(self):
        import test_generalized_angle_or_surface_v1248 as A
        from ogr_core.project import prepare_analysis_project
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.surface import SlipCircle
        p, b = _slope_with(lambda sid: _ga(sid), _straight_points())
        work = prepare_analysis_project(p)[0]
        sl = slice_surface(work, SlipCircle(**A._CIRCLE), num_slices=50)
        for s in sl.slices:
            assert _close(s.surface_angles[b.id], _THETA, 1e-13), s.index


# ======================================================================
class TestTheRuleOfTheSurface:

    def test_at_a_kink_the_segment_drawn_first(self):
        from ogr_core.geometry import Polyline, Vertex
        from ogr_core.geometry.anisotropic_surface import surface_angles_at
        from ogr_core.materials.strength_model import SliceContext
        pts = [(0.0, 0.0), (10.0, 10.0), (20.0, 10.0)]   # 45° then 0°
        fwd = Polyline(vertices=[Vertex(*q) for q in pts], closed=False)
        bwd = Polyline(vertices=[Vertex(*q) for q in reversed(pts)],
                       closed=False)
        # A point whose closest point of the surface is the vertex for both
        # segments: before the start of the second (x < 10) and past the
        # end of the first (x + y > 20).
        x, y = 8.0, 14.0
        a_fwd = surface_angles_at({"s": fwd}, x, y)["s"]
        a_bwd = surface_angles_at({"s": bwd}, x, y)["s"]
        assert _close(a_fwd, 45.0, 1e-12), a_fwd
        assert abs(a_bwd) < 1e-12, a_bwd
        # And the strength follows: a horizontal base reads the joint where
        # the surface is horizontal (inside A = 8), not where it is 45°.
        ga = _ga("s")
        s = 50.0

        def tau(angle):
            ctx = SliceContext(base_angle_rad=0.0,
                               surface_angles={"s": angle})
            return ga.shear_strength_ctx(s, ctx)
        assert tau(a_bwd) == _mc(2.0, 18.0).shear_strength(s)
        assert tau(a_fwd) == _mc(12.0, 34.0).shear_strength(s)

    def test_without_a_base_the_model_says_so(self):
        from ogr_core.materials.builtin_models import (
            IncompleteGeneralizedAnisotropic)
        from ogr_core.materials.strength_model import SliceContext
        ga = _ga("s")
        try:
            ga.shear_strength_ctx(50.0, SliceContext(base_angle_rad=0.0))
        except IncompleteGeneralizedAnisotropic as exc:
            assert "joint 1" in str(exc)
        else:
            raise AssertionError("a joint by surface answered with no "
                                 "orientation")
        # No slice at all: the weakest of the base and the joint.
        assert ga.shear_strength(50.0) == min(
            _mc(12.0, 34.0).shear_strength(50.0),
            _mc(2.0, 18.0).shear_strength(50.0))


# ======================================================================
class TestSupports:

    def test_a_support_reads_the_surface_at_its_point(self):
        from ogr_core.materials.strength_model import SliceContext
        from ogr_core.support.bond import soil_shear_strength_at
        # A folded surface: 0° for x < 30, 40° beyond.
        p, b = _slope_with(lambda sid: _ga(sid),
                           ((0.0, -5.0), (30.0, -5.0), (60.0, 20.17)))
        st = p.materials[0].strength
        axis = math.radians(5.0)
        steep = math.degrees(math.atan2(20.17 + 5.0, 30.0))   # about 40°
        for x, y, local in ((12.0, -3.0, 0.0), (50.0, 4.0, steep)):
            got = soil_shear_strength_at(p, x, y, 80.0, depth=3.0,
                                         axis_angle_rad=axis)
            ctx = SliceContext(base_angle_rad=axis,
                               surface_angles={b.id: local})
            want = st.shear_strength_ctx(80.0, ctx)
            assert _close(got, want), (x, y, got, want)
        # The two points read different joints: the fold matters.
        a = soil_shear_strength_at(p, 12.0, -3.0, 80.0, depth=3.0,
                                   axis_angle_rad=axis)
        c = soil_shear_strength_at(p, 50.0, 4.0, 80.0, depth=3.0,
                                   axis_angle_rad=axis)
        assert abs(a / c - 1.0) > 0.1, (a, c)


# ======================================================================
class TestRulesFileAndDialog:

    def test_a_missing_surface_is_refused_before_the_analysis(self):
        from ogr_core.project.rules import generalized_surfaces_refusal
        from ogr_slip2d.analysis_runner import check_analysis_settings
        p, b = _slope_with(lambda sid: _ga(sid))
        assert generalized_surfaces_refusal(p.materials[0], p) is None
        p.boundaries = [x for x in p.boundaries if x.id != b.id]
        why = generalized_surfaces_refusal(p.materials[0], p)
        assert why is not None and why.code == "generalized_surface_missing"
        assert any("not in the model" in m
                   for m in check_analysis_settings(p))

    def test_deleting_a_surface_a_joint_reads_is_refused(self):
        from types import SimpleNamespace

        from ogr_api import Workspace, call
        from ogr_api.errors import Conflict
        from ogr_core.project.rules import surface_in_use_refusal
        from ogr_gui.main_window import MainWindow
        p, b = _slope_with(lambda sid: _ga(sid))
        assert surface_in_use_refusal(p, b.id).code == "surface_in_use"
        # The window: the status bar says so and the surface stays.
        said = []
        fake = SimpleNamespace(
            project=p,
            ogr_status=SimpleNamespace(
                showMessage=lambda text, ms=0: said.append(text)))
        assert MainWindow._surface_in_use(fake, b) is True and said
        # The API refuses the delete.
        ws = Workspace()
        pid = ws.add(p).id
        try:
            call(ws, "boundary_edit", project_id=pid, boundary=b.id,
                 op="delete")
        except Conflict:
            pass
        else:
            raise AssertionError("the API deleted a surface a joint reads")
        assert any(x.id == b.id for x in ws.get(pid).project.boundaries)

    def test_the_file_keeps_the_surface(self):
        from ogr_core.materials.strength_model import StrengthModel
        st = _ga("sid-1")
        d = st.to_dict()
        back = StrengthModel.from_dict(d)
        assert back.definition == "surface"
        assert back.joints[0]["surface_id"] == "sid-1"
        assert back.to_dict() == d

    def test_the_dialog_edits_joints_by_surface(self):
        from PySide6.QtWidgets import QApplication
        from ogr_core.materials import Material
        from ogr_gui.dialogs.material_properties_dialog import (
            MaterialPropertiesDialog)
        QApplication.instance() or QApplication([])
        bed = Material(name="Bed", strength=_mc(2.0, 18.0))
        g = Material(name="G", strength=_ga(None))
        g.strength = g.strength.replaced(base={
            "material_id": bed.id, "model": bed.strength.to_dict()})
        dlg = MaterialPropertiesDialog(
            [bed, g], anisotropic_surfaces=[("s1", "Surface 1"),
                                            ("s2", "Surface 2")])
        dlg.list.setCurrentRow(1)
        calls = dlg.accepted_calls = []
        dlg.accept = lambda: calls.append(True)
        panel = dlg.param_panel
        cbo = panel._ga["definition"]
        assert cbo.model().item(cbo.findData("surface")).isEnabled()
        cbo.setCurrentIndex(cbo.findData("surface"))
        assert panel.table_headers()[0] == "Anisotropic surface"
        combo = panel._table.cellWidget(0, 0)
        combo.setCurrentIndex(combo.findData("s2"))
        params = panel.get_params()
        assert params["definition"] == "surface"
        assert params["joints"][0]["surface_id"] == "s2"
        # The angle it had is carried, for going back to angles.
        assert params["joints"][0]["angle"] == _THETA
        dlg._ok()
        assert calls == [True]
        st = dlg.result_materials()[1].strength
        assert st.definition == "surface"
        assert st.joints[0]["surface_id"] == "s2"

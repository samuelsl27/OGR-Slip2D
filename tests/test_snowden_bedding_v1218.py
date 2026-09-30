# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.218 — the Snowden Modified Anisotropic Linear model reads the LOCAL
bedding of an anisotropic surface (defect D208 of the verification bank).

THE DEFECT. v0.1.126 taught the three bedded models to read the orientation
an anisotropic surface gives at each slice base (``ctx.bedding_angle_deg``,
through ``_local_bedding_deg``). For Snowden's model it changed the signature
of ``_c_phi`` and not the call: ``shear_strength_ctx`` went on passing the
base angle alone, so the material's global ``bedding_angle`` won everywhere.
The material dialog lists the model in ``_ANISOTROPIC_MODEL_IDS`` and offers
to link a surface to it: a control that moved no number (rule 7). The same
commit put the missing argument in the Anisotropic Strength Function's call,
which does not take it (D195, closed in v0.1.215).

THE ANCHOR is the identity ``test_anisotropic_surface_v1126`` already holds
for Anisotropic Linear: a STRAIGHT anisotropic surface at alpha degrees is a
global bedding of alpha, digit for digit, through a whole analysis. For
Snowden it failed for every alpha other than the global angle.

What does NOT move: a Snowden material with no surface, bit for bit (the
context then carries None and the fallback answers the global angle), and
the verification bank, which has no Snowden material.

DISCRIMINATION, measured on the v0.1.217 tree: the identity and rule-7 cases
fail there by behaviour (the surface is ignored); the controls pass.

v0.1.229 (D215) -- changed on purpose: the model is now the reference's
(A1, B1, A2, B2 and two strength functions, a linear transition), and a
material with the old c1, phi1, c2, phi2 and B is refused until reviewed.
The material here is the old one's nearest form (A = 0, B = 25, one C/Phi
row per function), and the one case that read the old ``_c_phi`` reads the
new ``weight`` and ``_blend``. What the file pins is unchanged: the local
bedding is read, and without a surface the global angle is.
"""
from __future__ import annotations

import math

from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
from ogr_core.materials import Material
from ogr_core.materials.builtin_models import (GeneralizedAnisotropic,
                                               SnowdenModifiedAnisotropicLinear)
from ogr_core.project import Project
from ogr_slip2d.methods import method_registry
from ogr_slip2d.search import GridSearch
from ogr_slip2d.surface import SlipCircle

def _cphi(c: float, phi: float) -> dict:
    return {"model_id": "c_phi_function", "params": {},
            "rows": [[0.0, c, phi]]}


#: A Snowden material whose transition is sharp enough (B = 25 deg) for a
#: change of bedding to show on the factor of safety.
SNOWDEN = dict(A1=0.0, B1=25.0, A2=0.0, B2=25.0, bedding=_cphi(5.0, 12.0),
               rock_mass=_cphi(25.0, 32.0))


def _line(*pts) -> Polyline:
    return Polyline(vertices=[Vertex(x, y) for x, y in pts], closed=False)


def _straight(alpha: float) -> Polyline:
    dx = 100.0
    return _line((0.0, 15.0), (dx, 15.0 + dx * math.tan(math.radians(alpha))))


def _slope(bedding_angle: float = 0.0, surface: Polyline | None = None,
           dangling: bool = False, nested: bool = False) -> Project:
    """The homogeneous slope of ``test_anisotropic_surface_v1126`` with a
    Snowden material. ``nested`` wraps the same Snowden model in a
    Generalized Anisotropic material whose one rule covers every angle."""
    p = Project("snowden")
    ext = Polyline(vertices=[
        Vertex(0.0, 0.0), Vertex(120.0, 0.0), Vertex(120.0, 20.0),
        Vertex(80.0, 20.0), Vertex(50.0, 40.0), Vertex(0.0, 40.0),
    ], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    snowden = SnowdenModifiedAnisotropicLinear(bedding_angle=bedding_angle,
                                               **SNOWDEN)
    strength = snowden
    if nested:
        strength = GeneralizedAnisotropic(rules=[{
            "angle_min": -90.0, "angle_max": 90.0,
            "model": snowden.to_dict()}])
    mat = Material(name="bedded", unit_weight=20.0, strength=strength)
    p.materials = [mat]
    p.resolve_regions()
    p.assign_material_at(60.0, 10.0, mat.id)
    if surface is not None:
        b = Boundary(polyline=surface,
                     btype=BoundaryType.ANISOTROPIC_SURFACE)
        p.add_boundary(b)
        mat.anisotropic_surface_id = b.id
    elif dangling:
        mat.anisotropic_surface_id = "a-boundary-that-was-deleted"
    p.settings.methods.num_slices = 40
    return p


def _fos(project, method_id: str = "bishop_simplified") -> float:
    g = GridSearch(method=method_registry()[method_id](), num_slices=40,
                   grid_nx=3, grid_ny=3, radius_increment=3)
    res = g.evaluate_circle(project, SlipCircle(centre_x=60.0, centre_y=62.0,
                                                radius=48.0))
    assert res is not None and res.is_valid, "the trial circle did not solve"
    return res.fos


# ======================================================================
class TestTheSurfaceIsRead:
    """A straight surface at alpha IS a global bedding of alpha."""

    def test_straight_surface_equals_the_global_angle(self):
        bad = []
        for alpha in (20.0, -35.0, 60.0):
            with_surface = _fos(_slope(bedding_angle=0.0,
                                       surface=_straight(alpha)))
            with_angle = _fos(_slope(bedding_angle=alpha))
            if not math.isclose(with_surface, with_angle, rel_tol=1e-12):
                bad.append((alpha, with_surface, with_angle))
        assert not bad, bad

    def test_every_method_agrees_on_the_identity(self):
        bad = []
        for mid in sorted(method_registry()):
            a = _fos(_slope(bedding_angle=0.0, surface=_straight(25.0)), mid)
            b = _fos(_slope(bedding_angle=25.0), mid)
            if not math.isclose(a, b, rel_tol=1e-9):
                bad.append("%s: %.10f vs %.10f" % (mid, a, b))
        assert not bad, "\n".join(bad)

    def test_the_linked_surface_moves_the_number(self):
        """Rule 7: linking a surface at 25 degrees to a material whose own
        angle is 0 must change the factor. On v0.1.217 it changed
        nothing."""
        linked = _fos(_slope(bedding_angle=0.0, surface=_straight(25.0)))
        plain = _fos(_slope(bedding_angle=0.0))
        assert abs(linked - plain) > 1e-3 * plain, (linked, plain)


class TestWhatMustNotMove:

    def test_no_surface_is_the_global_angle_bit_for_bit(self):
        """With no surface the context carries None and the fallback is
        the global angle: exactly the call v0.1.217 made."""
        from ogr_core.materials.builtin_models import fold_plane_angle_deg
        from ogr_core.materials.strength_model import SliceContext
        m = SnowdenModifiedAnisotropicLinear(bedding_angle=17.0, **SNOWDEN)
        for angle in (-40.0, 5.0, 17.0, 33.0, 71.0):
            ctx = SliceContext(base_angle_rad=math.radians(angle))
            alpha = fold_plane_angle_deg(math.degrees(math.radians(angle))
                                         - 17.0)
            want = m._blend(80.0, m.weight(alpha))
            assert m.shear_strength_ctx(80.0, ctx) == want, angle

    def test_a_dangling_id_falls_back_to_the_global_angle(self):
        a = _fos(_slope(bedding_angle=17.0, dangling=True))
        b = _fos(_slope(bedding_angle=17.0))
        assert math.isclose(a, b, rel_tol=1e-15), (a, b)


class TestNestedInGeneralizedAnisotropic:
    """The Generalized Anisotropic model hands its context to a sub-model
    that needs one, so a Snowden rule reads the bedding the context
    carries: one rule over every angle is the Snowden model itself.

    v0.1.225 (D218) -- changed on purpose. These two cases linked an
    anisotropic surface to the GENERALIZED material and compared factors of
    safety. Since v0.1.225 its ranges are absolute slice base inclinations,
    as the reference defines them, and a Generalized material that links a
    surface is refused before any analysis
    (``rules.material_surface_refusal``); so the pass-through is pinned
    where it lives, on the model and the context it is handed."""

    def _pair(self):
        from ogr_core.materials.strength_model import SliceContext
        snow = SnowdenModifiedAnisotropicLinear(bedding_angle=0.0, **SNOWDEN)
        nested = GeneralizedAnisotropic(rules=[{
            "angle_min": -90.0, "angle_max": 90.0,
            "model": snow.to_dict()}])

        def ctx(angle, bedding):
            return SliceContext(base_angle_rad=math.radians(angle),
                                bedding_angle_deg=bedding)
        return snow, nested, ctx

    def test_one_rule_over_every_angle_is_the_model_itself(self):
        snow, nested, ctx = self._pair()
        for angle in (-60.0, -10.0, 0.0, 12.0, 40.0, 85.0):
            for bedding in (None, 25.0):
                c = ctx(angle, bedding)
                assert nested.shear_strength_ctx(80.0, c) == \
                    snow.shear_strength_ctx(80.0, c), (angle, bedding)

    def test_and_the_bedding_it_carries_moves_it(self):
        snow, nested, ctx = self._pair()
        a = nested.shear_strength_ctx(80.0, ctx(12.0, 25.0))
        b = nested.shear_strength_ctx(80.0, ctx(12.0, None))
        assert abs(a - b) > 1e-3 * b, (a, b)

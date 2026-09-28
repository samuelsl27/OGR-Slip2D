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

#: A Snowden material whose transition is sharp enough (B = 25 deg) for a
#: change of bedding to show on the factor of safety.
SNOWDEN = dict(c1=5.0, phi1=12.0, c2=25.0, phi2=32.0, B=25.0)


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
        from ogr_core.materials.strength_model import SliceContext
        m = SnowdenModifiedAnisotropicLinear(bedding_angle=17.0, **SNOWDEN)
        for angle in (-40.0, 5.0, 17.0, 33.0, 71.0):
            ctx = SliceContext(base_angle_rad=math.radians(angle))
            c, phi = m._c_phi(angle)
            want = c + 80.0 * math.tan(math.radians(phi))
            assert m.shear_strength_ctx(80.0, ctx) == want, angle

    def test_a_dangling_id_falls_back_to_the_global_angle(self):
        a = _fos(_slope(bedding_angle=17.0, dangling=True))
        b = _fos(_slope(bedding_angle=17.0))
        assert math.isclose(a, b, rel_tol=1e-15), (a, b)


class TestNestedInGeneralizedAnisotropic:
    """The Generalized Anisotropic model hands its context to a sub-model
    that needs one, so a Snowden rule reads the local bedding as well: one
    rule over every angle is the Snowden material itself, surface
    included. A behaviour change of v0.1.218 for that combination."""

    def test_one_rule_over_every_angle_is_the_model_itself(self):
        surf = _straight(25.0)
        a = _fos(_slope(bedding_angle=0.0, surface=surf, nested=True))
        b = _fos(_slope(bedding_angle=0.0, surface=surf))
        assert math.isclose(a, b, rel_tol=1e-12), (a, b)

    def test_and_the_surface_moves_it(self):
        a = _fos(_slope(bedding_angle=0.0, surface=_straight(25.0),
                        nested=True))
        b = _fos(_slope(bedding_angle=0.0, nested=True))
        assert abs(a - b) > 1e-3 * b, (a, b)

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.14 Support system (Slide-aligned implementation).

Covers all 7 support types + SupportPattern + LEM integration.
"""
from __future__ import annotations
import math


# ======================================================================
class TestSupportRegistry:
    def test_seven_types_registered(self):
        from ogr_core.support import support_registry
        ids = list(support_registry().keys())
        for sid in (
            "end_anchored", "grouted_tieback", "grouted_tieback_friction",
            "soil_nail", "pile_micropile", "geosynthetic", "user_defined",
        ):
            assert sid in ids, f"Missing support type: {sid}"

    def test_all_types_have_display_name(self):
        from ogr_core.support import support_registry
        for sid, cls in support_registry().items():
            assert cls.DISPLAY_NAME, f"{sid} has no DISPLAY_NAME"

    def test_all_types_have_parameters_declared(self):
        from ogr_core.support import support_registry
        for sid, cls in support_registry().items():
            assert hasattr(cls, "PARAMETERS")
            # User Defined uses a custom table — empty PARAMETERS is OK
            if sid != "user_defined":
                assert len(cls.PARAMETERS) >= 1, (
                    f"{sid} has empty PARAMETERS"
                )


# ======================================================================
class TestEndAnchored:
    def test_constant_force(self):
        from ogr_core.support import EndAnchored
        s = EndAnchored(anchor_capacity=200, out_of_plane_spacing=1.5)
        L = 10.0
        # Constant force at all x ∈ [0, L]
        for x in [0, 2, 5, 7, 10]:
            assert s.force_at(x, L) == 200.0 / 1.5

    def test_default_orientation_parallel(self):
        from ogr_core.support import EndAnchored, ForceOrientation
        assert EndAnchored.DEFAULT_ORIENTATION == ForceOrientation.PARALLEL_TO_SUPPORT


# ======================================================================
class TestGroutedTieback:
    def test_three_failure_modes(self):
        from ogr_core.support import GroutedTieback
        # Bond = 30% at the tail, free length = 70%
        s = GroutedTieback(
            tensile_capacity=600, plate_capacity=200,
            bond_strength=150, bond_length_percent=30,
            out_of_plane_spacing=2.0,
        )
        L = 10.0
        # In the free length (x ∈ [0, 7]):
        #   L_o = full bond = 3 m → pullout = 150·3/2 = 225
        #   L_i = 0 → stripping = (plate + 0) / spacing = 200/2 = 100
        #   tensile = 600/2 = 300
        #   min = 100 (plate-stripping dominates)
        assert s.force_at(3.0, L) == 100.0
        # At x=9 (within bond zone): L_o = 1, pullout = 75, L_i = 2,
        # stripping = (200 + 150*2)/2 = 250, tensile = 300, min = 75
        assert s.force_at(9.0, L) == 75.0
        # At x=10 (tail): L_o=0, pullout=0, stripping=(200+150*3)/2=325,
        # min=0
        assert s.force_at(10.0, L) == 0.0

    def test_zero_spacing_safe(self):
        from ogr_core.support import GroutedTieback
        s = GroutedTieback(out_of_plane_spacing=0)
        assert s.force_at(5, 10) == 0.0


# ======================================================================
class TestSoilNail:
    def test_three_modes_along_length(self):
        from ogr_core.support import SoilNail
        s = SoilNail(tensile_capacity=200, plate_capacity=100,
                     bond_strength=20, out_of_plane_spacing=1.0)
        L = 10.0
        # At x=0: L_o=10, L_i=0
        #   pullout = 20*10/1 = 200
        #   tensile = 200/1 = 200
        #   stripping = (100 + 20*0)/1 = 100
        # min = 100
        assert s.force_at(0, L) == 100.0
        # At x=5: L_o=5, L_i=5
        #   pullout = 100, tensile = 200, stripping = (100+100)/1 = 200
        # min = 100
        assert s.force_at(5, L) == 100.0
        # At x=10: L_o=0, L_i=10
        #   pullout = 0, tensile = 200, stripping = (100+200)/1 = 300
        # min = 0
        assert s.force_at(10, L) == 0.0

    def test_shear_capacity(self):
        from ogr_core.support import SoilNail
        s = SoilNail(shear_capacity=60, out_of_plane_spacing=1.5)
        # shear_at = shear_capacity / spacing
        assert s.shear_at(5, 10) == 40.0


# ======================================================================
class TestPileMicropile:
    def test_constant_force(self):
        from ogr_core.support import PileMicropile
        s = PileMicropile(pile_shear_strength=120, out_of_plane_spacing=2.0)
        for x in [0, 2, 5, 8, 10]:
            assert s.force_at(x, 10) == 60.0


# ======================================================================
class TestGeosynthetic:
    def test_symmetric_pullout(self):
        from ogr_core.support import Geosynthetic
        s = Geosynthetic(tensile_capacity=50, adhesion=10,
                         pullout_mode="mohr_coulomb")
        # At midpoint, L_pull = 5: F_p = 2*10*5 = 100, F_t = 50 → 50
        assert s.force_at(5, 10) == 50.0
        # At x=1 (near edge), L_pull = 1: F_p = 20, F_t=50 → 20
        assert s.force_at(1, 10) == 20.0
        # Symmetric: force at x=1 == force at x=9
        assert s.force_at(1, 10) == s.force_at(9, 10)


# ======================================================================
class TestUserDefined:
    def test_table_interpolation(self):
        from ogr_core.support import UserDefined
        s = UserDefined(out_of_plane_spacing=1.0, points=[
            (0, 50), (5, 200), (10, 50),
        ])
        # Linear interp at midpoints
        assert s.force_at(0, 10) == 50.0
        assert s.force_at(5, 10) == 200.0
        assert s.force_at(2.5, 10) == 125.0  # halfway from 50→200
        assert s.force_at(7.5, 10) == 125.0  # halfway from 200→50
        # Extrapolation = constant
        assert s.force_at(-1, 10) == 50.0
        assert s.force_at(15, 10) == 50.0


# ======================================================================
class TestSupportInstance:
    def test_axis_angle(self):
        from ogr_core.support import SupportInstance
        from ogr_core.geometry import Vertex
        s = SupportInstance(type_id="end_anchored",
            head=Vertex(0, 0), tail=Vertex(10, 0))
        assert abs(s.axis_angle_deg() - 0.0) < 1e-9
        s = SupportInstance(type_id="end_anchored",
            head=Vertex(0, 0), tail=Vertex(0, 10))
        assert abs(s.axis_angle_deg() - 90.0) < 1e-9

    def test_length(self):
        from ogr_core.support import SupportInstance
        from ogr_core.geometry import Vertex
        s = SupportInstance(type_id="end_anchored",
            head=Vertex(0, 0), tail=Vertex(3, 4))
        assert abs(s.length() - 5.0) < 1e-9

    def test_intersection_with_polyline(self):
        from ogr_core.support import SupportInstance
        from ogr_core.geometry import Vertex
        # Support from (0,5) to (10,0); intersect with y=2.5
        s = SupportInstance(type_id="end_anchored",
            head=Vertex(0, 5), tail=Vertex(10, 0))
        slip = [(0, 2.5), (10, 2.5)]
        result = s.intersection_with_polyline(slip)
        assert result is not None
        x, y, d = result
        assert abs(y - 2.5) < 1e-6
        assert abs(x - 5.0) < 1e-6
        # Distance from head = sqrt(5² + 2.5²) = √31.25 ≈ 5.59
        assert abs(d - math.sqrt(5**2 + 2.5**2)) < 1e-6

    def test_to_dict_from_dict_roundtrip(self):
        from ogr_core.support import (SupportInstance, ForceApplication,
                                       ForceOrientation)
        from ogr_core.geometry import Vertex
        s1 = SupportInstance(type_id="soil_nail",
            head=Vertex(1, 2), tail=Vertex(5, -1),
            force_application=ForceApplication.PASSIVE,
            orientation=ForceOrientation.BISECTOR,
            name="N1", color="#ff0000")
        d = s1.to_dict()
        s2 = SupportInstance.from_dict(d)
        assert s2.type_id == s1.type_id
        assert (s2.head.x, s2.head.y) == (s1.head.x, s1.head.y)
        assert (s2.tail.x, s2.tail.y) == (s1.tail.x, s1.tail.y)
        assert s2.force_application == s1.force_application
        assert s2.orientation == s1.orientation
        assert s2.name == s1.name


# ======================================================================
class TestSupportPattern:
    def test_generates_correct_count(self):
        from ogr_core.support import SupportPattern
        from ogr_core.geometry import Vertex
        pat = SupportPattern(type_id="soil_nail", length=6.0,
                             spacing=2.0, orientation_mode="angle",
                             angle_deg=-15)
        # Along a 10 m segment, expect ≈ 6 supports (every 2 m + endpoints)
        supports = pat.generate_along_segment(
            Vertex(0, 0), Vertex(10, 0))
        assert len(supports) == 6

    def test_pattern_with_normal_orientation(self):
        from ogr_core.support import SupportPattern
        from ogr_core.geometry import Vertex
        pat = SupportPattern(type_id="soil_nail", length=5.0,
                             spacing=1.0, orientation_mode="normal")
        # Horizontal segment: normal points down (negative y)
        supports = pat.generate_along_segment(
            Vertex(0, 10), Vertex(5, 10))
        # All tails should be below head (y direction)
        for s in supports:
            assert s.tail.y < s.head.y
            assert abs(s.length() - 5.0) < 1e-3


# ======================================================================
class TestSupportLEMIntegration:
    def test_support_increases_fos(self):
        """A row of supports applied to a marginal slope should increase
        the computed FoS.

        v0.1.84 — the model gained a 10 m foundation. It used to be
        ``(0,0) (60,0) (60,H) (crest,H) (toe,0)``, whose closing edge runs
        back along the bottom one: between x = 0 and the toe at x = 30 the
        ground surface and the base of the model are the same line at
        y = 0, enclosing no soil. Once v0.1.84 stopped analysing surfaces
        that leave the soil region, the only circles left with enough
        driving moment to carry these five nails were exactly the ones
        that had been reaching below the base, and the supported search
        returned no critical surface at all. With real ground underneath,
        the answer is the same as before the rule existed: 1.159 → 2.128.
        """
        from ogr_core.geometry import (Boundary, BoundaryType, Polyline,
                                       Vertex)
        from ogr_core.materials import Material, MohrCoulomb
        from ogr_core.project import Project
        from ogr_core.support import (SupportInstance, SoilNail,
                                       ForceApplication, ForceOrientation)
        from ogr_slip2d import BishopSimplified, GridSearch

        H = 12.0; beta = math.radians(30.96)
        toe = 30.0; crest = toe + H / math.tan(beta)
        ext = Polyline(vertices=[
            Vertex(0, -10), Vertex(60, -10), Vertex(60, H),
            Vertex(crest, H), Vertex(toe, 0), Vertex(0, 0),
        ], closed=True); ext.ensure_ccw()

        p = Project("test")
        p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
        p.materials = [Material(name="S", unit_weight=18,
            strength=MohrCoulomb(cohesion=8, friction_angle=20))]
        search = GridSearch(method=BishopSimplified(),
            grid_x=(20, 60), grid_y=(15, 35), grid_nx=8, grid_ny=8,
            radius_increment=2.0, min_radius=8.0, num_slices=25, min_area=0.5)
        r0 = search.run(p)
        fos0 = r0.critical.fos
        assert 0.5 < fos0 < 3.0, f"unreasonable baseline FoS={fos0}"

        # Add soil nails
        nail = SoilNail(tensile_capacity=200, plate_capacity=100,
                        bond_strength=50, out_of_plane_spacing=1.5)
        p.support_types = [nail]
        for i in range(5):
            frac = (i + 0.5) / 5.0
            hx = toe + frac * (crest - toe)
            hy = frac * H
            ang = math.radians(-15)
            tail_x = hx + 8 * math.cos(ang)
            tail_y = hy + 8 * math.sin(ang)
            p.supports.append(SupportInstance(
                type_id="soil_nail",
                head=Vertex(hx, hy), tail=Vertex(tail_x, tail_y),
                force_application=ForceApplication.ACTIVE,
                orientation=ForceOrientation.TANGENT_TO_SLIP,
            ))
        r1 = search.run(p)
        fos1 = r1.critical.fos
        assert fos1 > fos0, (
            f"Supports should improve FoS: before={fos0:.3f}, "
            f"after={fos1:.3f}"
        )
        # And the improvement should be substantial (>5%)
        assert (fos1 / fos0) > 1.05


# ======================================================================
class TestSupportSerialization:
    def test_pattern_roundtrip(self):
        from ogr_core.support import (SupportPattern, ForceApplication,
                                       ForceOrientation)
        pat = SupportPattern(
            type_id="grouted_tieback",
            length=12.0, spacing=2.5,
            orientation_mode="angle", angle_deg=-10,
            flip_180=True,
            force_application=ForceApplication.PASSIVE,
            orientation=ForceOrientation.BISECTOR,
        )
        d = pat.to_dict()
        pat2 = SupportPattern.from_dict(d)
        assert pat2.type_id == pat.type_id
        assert pat2.length == pat.length
        assert pat2.flip_180 == pat.flip_180
        assert pat2.force_application == pat.force_application

    def test_each_type_roundtrip(self):
        from ogr_core.support import (
            EndAnchored, GroutedTieback, GroutedTiebackFriction,
            SoilNail, PileMicropile, Geosynthetic, UserDefined,
            support_from_dict,
        )
        for orig in [
            EndAnchored(anchor_capacity=250),
            GroutedTieback(tensile_capacity=700),
            GroutedTiebackFriction(adhesion=80),
            SoilNail(tensile_capacity=150),
            PileMicropile(pile_shear_strength=150),
            Geosynthetic(tensile_capacity=60),
            UserDefined(points=[(0, 100), (5, 250), (10, 100)]),
        ]:
            d = orig.to_dict()
            restored = support_from_dict(d)
            assert restored.TYPE_ID == orig.TYPE_ID

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
EFFECTIVE or TOTAL inter-slice forces: the fork, pinned from both sides.

WHAT INVARIANT THIS PROTECTS.

The three methods that PRESCRIBE the inter-slice inclination — Lowe and
Karafiath (1960) and the two Corps of Engineers variants of the Modified
Swedish procedure, USACE (2003) EM 1110-2-1902 §C-4a — force the resultant
on every vertical face to lie at an angle θ fixed by geometry. When there
is water, the resultant on that face is the sum of an effective part
carried by the skeleton and the water pressure integrated over the face,
which is purely HORIZONTAL. Whether θ is imposed on the TOTAL resultant or
only on the EFFECTIVE one is a modelling choice; the manual treats both as
legitimate and says the answer differs. Since v0.1.98 it is
``MethodsSettings.interslice_forces``, defaulted to ``effective``.

**Neither value satisfies both of the external anchors below**, and that is
the point of this file. It is not a defect waiting for a patch: it is a
property of the assumption, and until v0.1.117 it was recorded as "one
datum missing". The datum is no longer missing — see
``docs/PENDIENTES.md`` §7 — and both halves are measured here so neither
can drift unnoticed.

v0.1.144 — the decision was taken and the default is now **TOTAL**. Anchor
1 is what a user gets by default; anchor 2 is what they get one click away,
and the model-level note in ``analysis_runner`` tells them when they need
it. Nothing below changed value: every case here sets the mode by hand,
which is the only reason a default can move without this file moving with
it. What is new at the end is the test that the default IS total and
reaches the method — rule 7 for a setting whose value is now a claim.

THE TWO ANCHORS, both external and both published.

1. **TOTAL reproduces the published factors of safety.** Pockoski and
   Duncan (2000), test slope 1 — the same case the reference program's
   verification bank numbers 55 — publishes Lowe-Karafiath **1.318** from
   the reference program and **1.32** from UTEXAS4, against Bishop 1.293.
   Every published implementation puts Lowe-Karafiath ABOVE Bishop; with
   effective forces this program puts it 3 % below. The same table is
   reproduced for test slope 2 (bank problem 56, 1.304 / 1.31) and for the
   Ej_2 piezometric model (0.7035), and the manual's own worked example in
   EM Appendix G — which ``test_modified_swedish_v198.py`` reproduces slice
   by slice — states in §G-5a that "the interslice forces are total forces
   and thus include the water pressures on the sides of the slices".

2. **EFFECTIVE is the only one that survives ponded water.** Duncan and
   Wright (2005), figure 6.27, page 88 — bank problem 70 — is a submerged
   slope analysed with the water 30 ft and 60 ft above the crest. Raising
   water over an already-submerged slope adds a uniform pressure γ_w·Δh on
   every face of the free body, whose exact effect is ΔN = γ_w·Δh·ℓ,
   ΔE_i = γ_w·Δh·h_i **horizontal**, ΔX_i = 0, leaving σ' and therefore F
   unchanged. An assumption that forces X_i = E_i·tan θ demands
   ΔX_i = ΔE_i·tan θ ≠ 0, so with TOTAL forces this family **cannot** be
   invariant to the depth of the water. Measured, it is worse than
   non-invariant: at 30 ft the closure residual has no sign change at all
   and the root finder falls back to the edge of its bracket grid, and at
   60 ft a SPURIOUS root appears in the mirrored marching orientation and
   converges, quietly, to 0.22.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
from ogr_core.materials import Material, PorePressureType
from ogr_core.materials.builtin_models import MohrCoulomb
from ogr_core.project import Project
from ogr_slip2d.analysis_runner import build_method
from ogr_slip2d.search import GridSearch
from ogr_slip2d.surface import SlipCircle

EFFECTIVE = "effective"
TOTAL = "total"

#: The three that read the setting, and the four that must not.
PRESCRIBED = ("lowe_karafiath", "corps_engineers_1", "corps_engineers_2")
INDIFFERENT = ("ordinary_fellenius", "bishop_simplified", "janbu_simplified",
               "spencer", "gle_morgenstern_price")


# ======================================================================
# Pockoski and Duncan (2000), test slope 1 — bank problem 55.
#
# Geometry read from the published figure; c' = 300 psf, φ' = 30°,
# γ = 120 pcf, γ_w = 62.4 pcf. Imperial units throughout: the factor of
# safety is dimensionless and the inputs are internally consistent.
# ======================================================================
P55_EXTERNAL = [(-75, 75), (170, 75), (170, 150), (100, 150), (0, 100),
                (-75, 100)]
P55_WATER_TABLE = [(-75, 100), (0, 100), (100, 140), (170, 140)]
P55_SLICES = 30

#: This program's critical circle for the case. It is not published, so it
#: is pinned by Bishop: on THIS circle Bishop must reproduce the published
#: 1.293, which is what makes the Lowe-Karafiath comparison below a
#: statement about the METHOD and not about the search.
P55_CIRCLE = dict(centre_x=23.333, centre_y=192.778, radius=98.2325)

#: Table 55.2 of the verification manual, itself Pockoski and Duncan (2000).
P55_PUBLISHED = {"bishop_simplified": 1.293, "spencer": 1.300,
                 "lowe_karafiath": 1.318}
#: UTEXAS4, same table. Wright's own program, and Wright is the co-author
#: of the book the other anchor of this file comes from.
P55_UTEXAS4_LOWE = 1.32


def _p55(wet: bool = True) -> Project:
    p = Project("Pockoski and Duncan 2000, test slope 1")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in P55_EXTERNAL],
                   closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    if wet:
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(x, y) for x, y in P55_WATER_TABLE],
            closed=False), btype=BoundaryType.WATER_TABLE))
    soil = Material(name="sandy clay", unit_weight=120.0,
                    sat_unit_weight=120.0,
                    strength=MohrCoulomb(cohesion=300.0, friction_angle=30.0),
                    pore_pressure=PorePressureType.WATER_TABLE)
    p.materials = [soil]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), soil.id)
    p.settings.groundwater.pore_fluid_unit_weight = 62.4
    return p


# ======================================================================
# Duncan and Wright (2005), figure 6.27 — bank problem 70.
# The same geometry ``test_ponded_water_v161.py`` uses; rebuilt here
# rather than imported, because a test module of this project is not
# importable outside the runner.
# ======================================================================
P70_EXTERNAL = [(0, 0), (140, 0), (140, 45), (105, 45), (30, 15), (0, 15)]
P70_CIRCLE = dict(centre_x=49.42, centre_y=88.56, radius=76.08)
P70_SLICES = 50
P70_GAMMA = 128.0
P70_GAMMA_W = 62.4


def _p70_ponded(water_y: float) -> Project:
    p = Project("Duncan and Wright 2005 fig. 6.27, ponded at %g" % water_y)
    ext = Polyline(vertices=[Vertex(x, y) for x, y in P70_EXTERNAL],
                   closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(-10, water_y), Vertex(150, water_y)], closed=False),
        btype=BoundaryType.WATER_TABLE))
    soil = Material(name="Soil", unit_weight=P70_GAMMA,
                    sat_unit_weight=P70_GAMMA, use_sat_unit_weight=True,
                    strength=MohrCoulomb(cohesion=100.0, friction_angle=20.0),
                    pore_pressure=PorePressureType.WATER_TABLE)
    p.materials = [soil]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), soil.id)
    p.settings.groundwater.pore_fluid_unit_weight = P70_GAMMA_W
    return p


def _p70_buoyant() -> Project:
    """Duncan and Wright's equivalent procedure: γ' = γ − γ_w, no water.

    With no water surface there is no thrust on any vertical face, so the
    two settings describe the SAME analysis — which is why this is the
    common ground the two conventions can be measured against.
    """
    p = Project("Duncan and Wright 2005 fig. 6.27, buoyant")
    ext = Polyline(vertices=[Vertex(x, y) for x, y in P70_EXTERNAL],
                   closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    soil = Material(name="Soil", unit_weight=P70_GAMMA - P70_GAMMA_W,
                    strength=MohrCoulomb(cohesion=100.0, friction_angle=20.0))
    p.materials = [soil]
    p.assign_material_at(*p.resolve_regions()[0].centroid(), soil.id)
    return p


# ----------------------------------------------------------------------
def _fos(project: Project, method_id: str, mode: str, circle: dict,
         num_slices: int):
    """FoS through ``build_method``, which is the ONLY place the setting is
    read; instantiating the class by hand would bypass it silently."""
    project.settings.methods.interslice_forces = mode
    method = build_method(project, method_id, num_slices)
    assert method is not None, method_id
    ev = GridSearch(method=method, num_slices=num_slices, min_area=0.0)
    result = ev.evaluate_circle(project, SlipCircle(**circle))
    assert result is not None, (method_id, mode)
    return result


def _fos55(method_id: str, mode: str, wet: bool = True) -> float:
    return _fos(_p55(wet), method_id, mode, P55_CIRCLE, P55_SLICES).fos


def _fos70(project: Project, mode: str,
           method_id: str = "lowe_karafiath") -> float:
    return _fos(project, method_id, mode, P70_CIRCLE, P70_SLICES).fos


# ======================================================================
class TestTheCircleIsTheOneThePublishedTableDescribes:
    """Before comparing Lowe-Karafiath against 1.318, show that the two
    tables are talking about the same slope and the same surface."""

    def test_bishop_and_spencer_reproduce_their_published_values(self):
        for mid, pub in (("bishop_simplified", P55_PUBLISHED["bishop_simplified"]),
                         ("spencer", P55_PUBLISHED["spencer"])):
            got = _fos55(mid, EFFECTIVE)
            assert abs(got - pub) / pub < 0.005, (mid, got, pub)

    def test_neither_of_them_moves_with_the_setting(self):
        """The control that identifies WHAT the setting touches. A method
        that solves for the inter-slice inclination, or assumes it
        horizontal, is insensitive to the split by construction; if one of
        these ever moves, the setting has reached somewhere it should not."""
        for mid in INDIFFERENT:
            a = _fos55(mid, EFFECTIVE)
            b = _fos55(mid, TOTAL)
            assert a == b, (mid, a, b)


# ======================================================================
class TestPublishedLoweKarafiathNeedsTotalForces:
    """Anchor 1. Three published implementations put Lowe-Karafiath ABOVE
    Bishop wherever there is a water table; only TOTAL forces do that."""

    def test_total_reproduces_the_published_factor_of_safety(self):
        got = _fos55("lowe_karafiath", TOTAL)
        pub = P55_PUBLISHED["lowe_karafiath"]
        assert abs(got - pub) / pub < 0.01, (got, pub)
        assert abs(got - P55_UTEXAS4_LOWE) / P55_UTEXAS4_LOWE < 0.01, got

    def test_effective_is_low_by_several_per_cent(self):
        """Two-sided on purpose. If this ever shrinks to nothing, the
        default has been changed or the split has been altered, and
        ``docs/PENDIENTES.md`` §7 has to be rewritten rather than quietly
        left behind."""
        got = _fos55("lowe_karafiath", EFFECTIVE)
        pub = P55_PUBLISHED["lowe_karafiath"]
        short = (pub - got) / pub
        assert 0.02 < short < 0.10, (got, pub, short)

    def test_the_ratio_to_bishop_changes_side(self):
        """The shape of the anomaly, stated as the published tables state
        it: Lowe-Karafiath / Bishop is 1.318/1.293 = 1.019 published."""
        bishop = _fos55("bishop_simplified", EFFECTIVE)
        assert _fos55("lowe_karafiath", TOTAL) / bishop > 1.0
        assert _fos55("lowe_karafiath", EFFECTIVE) / bishop < 1.0

    def test_without_water_the_two_settings_are_the_same_analysis(self):
        """And the published relation is reproduced by BOTH: dry, this
        family already sits just above Bishop. That is what makes the wet
        case a statement about the water term and not about θ."""
        bishop = _fos55("bishop_simplified", EFFECTIVE, wet=False)
        for mid in PRESCRIBED:
            a = _fos55(mid, EFFECTIVE, wet=False)
            b = _fos55(mid, TOTAL, wet=False)
            assert a == b, (mid, a, b)
            assert a / bishop > 1.0, (mid, a, bishop)


# ======================================================================
class TestSubmergedSlopeNeedsEffectiveForces:
    """Anchor 2. The other half of the fork, on Duncan and Wright's own
    submerged slope."""

    def test_effective_is_invariant_to_the_depth_of_the_water(self):
        """The analytical identity of the file header, at the level of the
        answer: the extra water is a uniform pressure increment on a
        closed contour, so it cannot change the factor of safety."""
        a = _fos70(_p70_ponded(75.0), EFFECTIVE)
        b = _fos70(_p70_ponded(105.0), EFFECTIVE)
        assert math.isclose(a, b, rel_tol=1e-6), (a, b)

    def test_effective_reproduces_the_buoyant_equivalent(self):
        """Duncan and Wright's two procedures for water — total weights
        plus boundary water forces plus u, against buoyant unit weights
        with no water — must agree."""
        ponded = _fos70(_p70_ponded(75.0), EFFECTIVE)
        buoyant = _fos70(_p70_buoyant(), EFFECTIVE)
        assert abs(ponded - buoyant) / buoyant < 0.005, (ponded, buoyant)

    def test_total_loses_both(self):
        """With TOTAL forces the same case is not merely a few per cent
        out: the answer is not a factor of safety at all. At 30 ft the
        closure residual never changes sign over the whole bracket grid,
        so ``_force_balance`` returns its nearest-residual fallback; at
        60 ft a spurious root appears in the mirrored orientation. Both
        are pinned by how FAR they are, not by their digits."""
        buoyant = _fos70(_p70_buoyant(), TOTAL)
        for water_y in (75.0, 105.0):
            got = _fos70(_p70_ponded(water_y), TOTAL)
            assert abs(got - buoyant) / buoyant > 0.5, (water_y, got, buoyant)

    def test_the_thirty_foot_case_does_not_even_converge(self):
        """Named separately because "the method answers 5.0" and "the
        method has no root here" are different findings, and the second is
        the true one. ``converged`` is the flag the fallback path leaves
        false."""
        r = _fos(_p70_ponded(75.0), "lowe_karafiath", TOTAL, P70_CIRCLE,
                 P70_SLICES)
        assert not r.converged, r.fos

    def test_with_no_water_at_all_the_fork_disappears(self):
        """The control: on the buoyant model the two settings describe the
        same analysis, so the comparison above is about the water term."""
        for mid in PRESCRIBED:
            a = _fos70(_p70_buoyant(), EFFECTIVE, mid)
            b = _fos70(_p70_buoyant(), TOTAL, mid)
            assert a == b, (mid, a, b)


# ======================================================================
class TestTheSettingMovesTheNumber:
    """Rule 7, for the two methods ``test_modified_swedish_v198.py`` does
    not cover — it pins the same property for Corps of Engineers #1."""

    def test_each_prescribed_method_moves_and_in_the_same_direction(self):
        for mid in PRESCRIBED:
            a = _fos55(mid, EFFECTIVE)
            b = _fos55(mid, TOTAL)
            assert (b - a) / a > 0.01, (mid, a, b)


# ======================================================================
class TestTheDefaultIsTotalAndReachesTheMethod:
    """v0.1.144. The decision, pinned where it can be read.

    Three separate claims, because they failed separately elsewhere in
    this project: the stored default, the class default, and the value
    that actually arrives at the solver. A default that is right in the
    dataclass and wrong in the class is the shape of the v0.1.78 method
    list and of defect D33 — two lists of the same fact, drifting apart.
    """

    def test_a_new_project_asks_for_total_forces(self):
        assert Project("fresh").settings.methods.interslice_forces == TOTAL

    def test_the_class_default_is_the_same_one(self):
        """Instantiating the method directly must not describe a
        different analysis from going through ``build_method``."""
        from ogr_slip2d.methods.lowe_karafiath import LoweKarafiath
        assert LoweKarafiath().interslice_forces == TOTAL

    def test_the_default_arrives_at_the_solver(self):
        """Rule 7 in its strict form: not that the field holds a value,
        but that the value reaches the object that uses it. Nobody sets
        the mode here — that is the whole test."""
        p = _p55()
        for mid in PRESCRIBED:
            m = build_method(p, mid, P55_SLICES)
            assert m is not None, mid
            assert m.interslice_forces == TOTAL, mid

    def test_and_a_project_that_stored_effective_keeps_it(self):
        """The other half of changing a default: a file saved before the
        change carries the field (``to_dict`` writes the whole dataclass),
        so it must go on being analysed the way it was. 86 of the 88
        models of the verification bank are in exactly this position."""
        p = _p55()
        p.settings.methods.interslice_forces = EFFECTIVE
        stored = Project.from_dict(p.to_dict())
        assert stored.settings.methods.interslice_forces == EFFECTIVE
        assert build_method(
            stored, "lowe_karafiath", P55_SLICES).interslice_forces == EFFECTIVE

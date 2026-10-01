# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Tests for v0.1.234 — the slope face is the run of profile segments COLLINEAR
with the steepest one, so a vertex on the face does not change the search.
Defect D241.

**The invariant**: the same terrain gives the same search. A ground profile
with an extra vertex ON a straight face — which is what a material contact or
a water line that meets the face leaves there — is the same polyline, and
five searches read the slope face from it: the Path Search (initiation
window and the target its turn-up schedule aims at), the Block Search
without objects (its implicit region), the Simulated Annealing (its fixed
endpoints), and through ``slope_frame`` the Slope Search and the Particle
Swarm (their windows). Until v0.1.233 the face was ONE segment — the
steepest, with a tie-break — so a straight face cut into collinear pieces
was read as one piece, and the five searches sized everything on it.

**What it cost, measured against a published number.** Verification problem
52 (Zhu and Lee 2002, a four-layer slope with a tension crack) has a straight
face from (0, 0) to (30, 15) that two material contacts cut at (6, 3) and
(18, 9). The face was read as (0, 0)-(6, 3); the Path Search aimed its paths
6 m from the toe and never generated the deep surface the manual publishes
for its «Surface 4 - Noncircular, deep - Path search». Dry, with the manual's
Bishop at 1.624, this file's 1000-surface Path Search gives 2.1395 with the
face cut (+31.7 %) and 1.6432 with it whole (+1.2 %, without the
optimisation the manual used). That is the external anchor (§ anchor).

**How invariance is asserted.** Bit-for-bit is too strong: interpolating
the ground on a segment split in two rounds differently in the last bits,
so factors differ by ~1e-13 relative. What has to hold is everything else —
the same number of attempts and evaluations, the same valid and invalid
surfaces — and every factor within 1e-11 relative. The switch
``failure_direction.FACE_IS_THE_COLLINEAR_RUN`` turned off shows that the
same comparison fails without the fix, so the test cannot pass by accident.

COST. Ten small searches on a 100 m slope for the invariance, two Bishop Path
Searches of 1000 surfaces for the anchor; about forty seconds.
"""
from __future__ import annotations

import contextlib

#: Manual, table 52.9, «Surface 4 - Noncircular, deep - Path search (Dry
#: Condition)», Bishop.
_ZHU_LEE_S4_DRY_BISHOP = 1.624
_CACHE: dict = {}


@contextlib.contextmanager
def _face_switch(on: bool):
    """The module switch, put back on the way out whatever happens (the
    runner does not call teardown_method: rule 5)."""
    from ogr_slip2d import failure_direction as fd
    before = fd.FACE_IS_THE_COLLINEAR_RUN
    fd.FACE_IS_THE_COLLINEAR_RUN = on
    try:
        yield
    finally:
        fd.FACE_IS_THE_COLLINEAR_RUN = before


def _profile(*pts):
    from ogr_core.geometry import Vertex
    return [Vertex(float(x), float(y)) for x, y in pts]


def _project():
    from ogr_core.project import Project
    return Project("D241")


# ======================================================================
class TestTheFaceIsTheCollinearRun:

    def test_a_split_straight_face_is_read_whole(self):
        from ogr_slip2d.failure_direction import slope_face
        top = _profile((-20, 0), (0, 0), (6, 3), (18, 9), (30, 15), (50, 15))
        assert slope_face(top, _project()) == (1, 4)

    def test_a_real_bend_stays_two_faces(self):
        """(0,0)-(10,5) and (10,5)-(20,12): slopes 0.5 and 0.7 — a turn, not
        a split. The steeper one is the face, alone."""
        from ogr_slip2d.failure_direction import slope_face
        top = _profile((-10, 0), (0, 0), (10, 5), (20, 12), (40, 12))
        assert slope_face(top, _project()) == (2, 3)

    def test_a_vertex_a_hair_off_the_line_does_not_split_it(self):
        """A contact endpoint rounded a nanometre off the face, in a model
        drawn in metres: the tolerance is relative, not a coordinate."""
        from ogr_slip2d.failure_direction import slope_face
        top = _profile((-20, 0), (0, 0), (6, 3 + 1e-9), (30, 15), (50, 15))
        assert slope_face(top, _project()) == (1, 3)

    def test_a_vertical_step_never_joins_an_inclined_face(self):
        from ogr_slip2d.failure_direction import slope_face
        top = _profile((0, 0), (10, 0), (10, 2), (20, 7), (30, 12), (40, 12))
        lo, hi = slope_face(top, _project())
        assert (lo, hi) == (2, 4), (lo, hi)

    def test_the_tie_break_between_two_faces_is_unchanged(self):
        """A symmetric embankment: two faces of equal inclination that are
        NOT collinear. The declared failure direction still picks one
        (the toe on the side the mass moves to), and the other is not
        merged into it."""
        from ogr_slip2d.failure_direction import (slope_face,
                                                  steepest_face_index)
        top = _profile((0, 0), (10, 0), (20, 5), (30, 5), (40, 0), (50, 0))
        p = _project()
        i = steepest_face_index(top, p)
        assert slope_face(top, p) == (i, i + 1)

    def test_the_switch_off_is_one_segment(self):
        from ogr_slip2d.failure_direction import (slope_face,
                                                  steepest_face_index)
        top = _profile((-20, 0), (0, 0), (6, 3), (18, 9), (30, 15), (50, 15))
        p = _project()
        with _face_switch(False):
            i = steepest_face_index(top, p)
            assert slope_face(top, p) == (i, i + 1)
        assert slope_face(top, p) == (1, 4)


# ======================================================================
def _slope(split, method, family, n=40):
    """A 2:3 slope, (30, 20)-(60, 40), with or without two vertices on its
    face. One material: the two models are the same terrain and the same
    soil, and differ only in the vertex list of the external boundary."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    p = Project("D241 invariance")
    pts = [(0, 0), (100, 0), (100, 40), (60, 40)]
    if split:
        pts += [(48, 32), (39, 26)]
    pts += [(30, 20), (0, 20)]
    ext = Polyline(vertices=[Vertex(*v) for v in pts], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="soil", unit_weight=19.0,
                            strength=MohrCoulomb(cohesion=10.0,
                                                 friction_angle=30.0))]
    p.resolve_regions()
    s = p.settings.search
    s.surface_type = family
    s.search_method = method
    s.path_num_surfaces = n
    s.block_num_surfaces = n
    return p


def _search(split, method, family):
    from ogr_slip2d.analysis_runner import build_search
    p = _slope(split, method, family)
    s = build_search(p, "bishop_simplified")
    for attr, value in (("num_surfaces", 40), ("max_iterations", 60),
                        ("num_particles", 8), ("num_iterations", 6)):
        if hasattr(s, attr):
            setattr(s, attr, value)
    return s.run(p)


def _same(a, b, rel=1e-11) -> bool:
    if a.attempts != b.attempts or len(a.evaluations) != len(b.evaluations):
        return False
    for x, y in zip(a.evaluations, b.evaluations):
        if x.is_valid != y.is_valid or (x.fos is None) != (y.fos is None):
            return False
        if x.fos is not None and abs(x.fos - y.fos) > rel * abs(x.fos):
            return False
    return True


_READERS = (("path", "non_circular"), ("block", "non_circular"),
            ("simulated_annealing", "non_circular"),
            ("slope", "circular"), ("particle_swarm", "circular"))


class TestTheSameTerrainGivesTheSameSearch:
    """The five readers of the face, each run on the slope with and without
    two collinear vertices on its face."""

    def _check(self, method, family):
        key = ("inv", method)
        if key not in _CACHE:
            _CACHE[key] = (_search(False, method, family),
                           _search(True, method, family))
        whole, split = _CACHE[key]
        assert _same(whole, split), method

    def test_path_search(self):
        self._check(*_READERS[0])

    def test_block_search_without_objects(self):
        self._check(*_READERS[1])

    def test_simulated_annealing(self):
        self._check(*_READERS[2])

    def test_slope_search(self):
        self._check(*_READERS[3])

    def test_particle_swarm(self):
        self._check(*_READERS[4])

    def test_without_the_fix_the_comparison_fails(self):
        """The same comparison with the switch off: four of the five
        searches change with the vertex, so the assertions above are
        measuring the fix and not passing by construction."""
        changed = 0
        with _face_switch(False):
            for method, family in _READERS:
                if not _same(_search(False, method, family),
                             _search(True, method, family)):
                    changed += 1
        assert changed >= 3, changed


# ======================================================================
def _zhu_lee_dry(n):
    """Verification problem 52: Zhu and Lee (2002), four layers, dry, with
    the tension crack at 13.985 that its figures show; the Path Search of
    the manual's Surface 4. The face (0,0)-(30,15) is cut at (6,3) and
    (18,9) by the contacts 2/3 and 1/2."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.geometry.tension_crack import (TensionCrackProperties,
                                                 WaterLevelMode)
    from ogr_core.materials import Material, PorePressureType
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from shapely.geometry import Polygon

    p = Project("Zhu and Lee 2002")
    ext = Polyline(vertices=[Vertex(*v) for v in (
        (-20, -9), (50, -9), (50, 15), (30, 15), (18, 9), (6, 3), (0, 0),
        (-20, 0))], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    for pts in (((18, 9), (50, 9)), ((6, 3), (50, 3)), ((-20, -6), (50, -6))):
        p.add_boundary(Boundary(polyline=Polyline(
            vertices=[Vertex(*v) for v in pts], closed=False),
            btype=BoundaryType.MATERIAL))
    p.add_boundary(Boundary(polyline=Polyline(
        vertices=[Vertex(27.97, 13.985), Vertex(50.0, 13.985)], closed=False),
        btype=BoundaryType.TENSION_CRACK))
    p.tension_crack_properties = TensionCrackProperties(
        mode=WaterLevelMode.DRY)
    mats = [Material(name=name, unit_weight=g, sat_unit_weight=g,
                     strength=MohrCoulomb(cohesion=c, friction_angle=phi),
                     pore_pressure=PorePressureType.NONE)
            for name, c, phi, g in (("1", 20.0, 18.0, 18.8),
                                    ("2", 40.0, 22.0, 18.5),
                                    ("3", 25.0, 26.0, 18.4),
                                    ("4", 10.0, 12.0, 18.0))]
    p.materials = mats
    for reg in p.resolve_regions():
        pt = Polygon([(v.x, v.y) for v in reg.polygon.vertices])\
            .representative_point()
        i = 0 if pt.y > 9.0 else 1 if pt.y > 3.0 else 2 if pt.y > -6.0 else 3
        p.assign_material_at(pt.x, pt.y, mats[i].id)
    p.settings.methods.num_slices = 50
    p.settings.methods.tolerance = 1e-4
    s = p.settings.search
    s.surface_type = "non_circular"
    s.search_method = "path"
    s.path_num_surfaces = n
    s.min_area = 5.0
    return p


def _zhu_lee_bishop(face_whole: bool) -> float:
    """The engine as it is for ``face_whole`` — the switch is only touched to
    turn it OFF, so in a tree without the fix this measures the old engine's
    BEHAVIOUR instead of failing on a missing name."""
    key = ("zl", face_whole)
    if key not in _CACHE:
        from ogr_slip2d.analysis_runner import build_search
        guard = (contextlib.nullcontext() if face_whole
                 else _face_switch(False))
        with guard:
            p = _zhu_lee_dry(1000)
            _CACHE[key] = build_search(p, "bishop_simplified").run(p)\
                .critical.fos
    return _CACHE[key]


class TestTheAnchorZhuAndLee2002:

    def test_the_face_is_read_whole(self):
        from ogr_slip2d import search as S
        from ogr_slip2d.failure_direction import slope_face
        p = _zhu_lee_dry(10)
        top = S.PathSearch._ground_profile(next(
            b for b in p.boundaries
            if b.btype.name == "EXTERNAL").polyline.vertices)
        lo, hi = slope_face(top, p)
        assert ((top[lo].x, top[lo].y), (top[hi].x, top[hi].y)) == (
            (0.0, 0.0), (30.0, 15.0))

    def test_the_path_search_reaches_the_published_surface_4(self):
        """Within 2 % of the manual's Bishop (1.624) with 1000 surfaces and
        no optimisation; measured 1.6432 (+1.2 %)."""
        f = _zhu_lee_bishop(True)
        assert abs(f / _ZHU_LEE_S4_DRY_BISHOP - 1.0) < 0.02, f

    def test_rule_7_the_face_moves_the_number(self):
        """With the face read as one piece the same search stays more than
        20 % above the manual (measured 2.1395, +31.7 %)."""
        f = _zhu_lee_bishop(False)
        assert f > 1.20 * _ZHU_LEE_S4_DRY_BISHOP, f

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.264, defect D250 — the non-circular Auto Refine reaches the published
mechanism of the reference's Generalized Anisotropic tutorial, through the
ordinary analysis door, when Optimize Surfaces uses Surface Altering.

**The invariant.** The reference's Tutorial 20 (Generalized Anisotropic,
"Angle Range": Soil Mass c = 5, phi = 30, Bedding c = 0, phi = 20 for slice
bases within 10 degrees of horizontal, gamma = 20, no water) run with its
own search panel — non-circular Auto Refine, 10 divisions, 10 circles,
10 iterations, 50 %, 12 vertices, Optimize Surfaces on — and Bishop with 25
slices gives the factor the tutorial publishes, 1.268, to within 1 %, and
the critical surface has the shape the tutorial describes: "a section of
sub-horizontal slip connected to the surface by a steep incline", the
sub-horizontal section on the bedding.

**The external anchor (rule 1)** is that published value and that
sentence (pages 20-11 and 20-12). The tutorial's circular answer, 1.478,
is pinned separately in ``test_generalized_angle_or_surface_v1248``.

**Why Surface Altering and not the default walk.** D250 measured, on
v0.1.263 and without touching the engine, where the 4.9 % came from:

* not the seed: every surface the search analyses is a polygon inscribed
  in a circle (the documented method), so none has a kink; the best of the
  2875 is 1.4379 and none comes below 1.40. The whole way down belongs to
  Optimize Surfaces, in the reference as here;
* the Monte Carlo walk: 1.3069 to 1.3524 over six seeds. It lengthens the
  run along the bedding and leaves the ramp at about 36 degrees, because
  steepening a straight ramp one vertex at a time passes through a concave
  kink that the default ceiling of 5 degrees forbids (with 45 degrees,
  1.2687 to 1.3059). Free ends, Explore All Vertices and twice the vertices
  stay in the same basin. That is reported in defect D264, which owns the
  walk's defaults, and is NOT pinned here: a test that asserted 1.33 would
  consecrate the trap (rule 1);
* Surface Altering reaches the family from every start tried: 1.2691 from
  the search's critical surface, 1.2609 to 1.2784 from four others.

The default technique stays Monte Carlo by the owner's decision of
2026-10-05 (no model moves unless Surface Altering is chosen), so this file
chooses it explicitly, as a user of the panel would.

**Why 1 % and why one run.** Surface Altering does not read the seed and
the Auto Refine is deterministic, so there is no seed scatter to sample;
the scatter that exists is the START's, -0.56 % to +0.82 % over five starts,
and 1 % covers it. The run gives 1.26915 (+0.09 %) on v0.1.264.

DISCRIMINATION, measured against a ``git archive`` of v0.1.255, which has no
Surface Altering, so the same model runs the Monte Carlo walk: the factor
test FAILS there (1.3303, +4.9 %). The shape test PASSES there too, and that
is a finding rather than a gap: the walk already finds the run along the
bedding and an incline steeper than 35 degrees; what it does not find is how
steep the incline is (about 36 degrees against the figure's 45). A threshold
on that angle would be read off a figure digitised to half a metre, so it is
not pinned. Archived in the verification bank, ``_auditoria/P5_0264``.

COST: one analysis, about 100 s, shared by both tests.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math

#: Tutorial 20, page 20-11: the non-circular Auto Refine with Optimize
#: Surfaces, Bishop.
_PUBLISHED = 1.268
_REL_TOL = 0.01
#: The Bedding band of the tutorial's "Angle Range" input, in degrees.
_BEDDING = 10.0

_CACHE: dict = {}


def _cached(name, fn):
    if name not in _CACHE:
        _CACHE[name] = fn()
    return _CACHE[name]


def _tutorial20():
    """Tutorial 20 of the reference, as its pages 20-3 to 20-6 and 20-11
    give it: the model of ``test_generalized_angle_or_surface_v1248`` and
    the search panel of page 20-11."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.materials.builtin_models import GeneralizedAnisotropic
    from ogr_core.project import Project
    ext = Polyline(vertices=[Vertex(0, 0), Vertex(130, 0), Vertex(130, 50),
                             Vertex(80, 50), Vertex(33.5, 30), Vertex(0, 30)],
                   closed=True)
    ext.ensure_ccw()
    p = Project("Tutorial 20")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    soil = Material(name="Soil Mass", unit_weight=20.0,
                    strength=MohrCoulomb(cohesion=5.0, friction_angle=30.0))
    bed = Material(name="Bedding", unit_weight=20.0,
                   strength=MohrCoulomb(cohesion=0.0, friction_angle=20.0))

    def link(m, **kw):
        return {"material_id": m.id, "model": m.strength.to_dict(), **kw}
    st = GeneralizedAnisotropic(rules=[
        link(soil, angle_min=-90.0, angle_max=-_BEDDING),
        link(bed, angle_min=-_BEDDING, angle_max=_BEDDING),
        link(soil, angle_min=_BEDDING, angle_max=90.0)])
    g = Material(name="Material 3", unit_weight=20.0, strength=st)
    p.materials = [soil, bed, g]
    p.assign_material_at(60.0, 20.0, g.id)

    s = p.settings
    s.methods.num_slices = 25
    s.methods.tolerance = 0.005
    q = s.search
    q.surface_type = "non_circular"
    q.search_method = "auto_refine"
    q.auto_refine_divisions_along_slope = 10
    q.auto_refine_circles_per_division = 10
    q.auto_refine_num_iterations = 10
    q.auto_refine_divisions_to_use_pct = 50.0
    q.auto_refine_num_vertices_along_surface = 12
    q.optimize_enabled = True
    q.optimize_technique = "surface_altering"
    return p


def _critical():
    from ogr_slip2d.analysis_runner import run_analysis

    def run():
        out = run_analysis(_tutorial20(), ["bishop_simplified"])
        return out.results["bishop_simplified"].critical
    return _cached("critical", run)


class TestTutorial20NonCircular:

    def test_reaches_the_published_factor(self):
        crit = _critical()
        assert crit is not None and crit.is_valid
        assert abs(crit.fos / _PUBLISHED - 1.0) <= _REL_TOL, crit.fos

    def test_is_the_published_shape(self):
        """A sub-horizontal section on the bedding, joined to the ground by
        a steep incline — the tutorial's own words, measured on the
        segments of the critical polyline."""
        crit = _critical()
        pl = getattr(crit.surface, "polyline", None)
        assert pl is not None, "the critical surface is not a polyline"
        pts = [(v.x, v.y) for v in pl.vertices]
        width = pts[-1][0] - pts[0][0]
        on_bedding = 0.0
        steepest = 0.0
        for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
            a = abs(math.degrees(math.atan2(y1 - y0, x1 - x0)))
            steepest = max(steepest, a)
            if a <= _BEDDING + 1e-6:
                on_bedding += x1 - x0
        assert on_bedding >= 0.30 * width, (on_bedding, width, pts)
        assert steepest >= 35.0, (steepest, pts)

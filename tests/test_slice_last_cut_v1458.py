# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.458 (D407) — the slicer shares out exactly ``[x_l, x_r]``, with the
number of slices asked for, also when nothing forces a cut.

WHAT WAS WRONG

Without a mandatory cut, ``_slice_boundaries`` returned the uniform division
``x_l + step * i`` and did not pin the last boundary on ``x_r``. The branch
with cuts has done that since v0.1.66. In floating point ``x_l + (w / n) * n``
is not ``x_r``. On the plane (2, 2)–(30, 10) of
``test_yield_acceleration_v1127`` the last boundary overshoots 30 by 3.6e-15
with 25, 41, 43, 50 and 51 slices (it falls short with 55 and 71, which is
harmless). ``SlipSurface.base_y_at`` answers None past the last vertex, so the
slicer abandoned the surface without recording a reason. The run then blamed
"more mandatory cuts than slices, a degenerate width or a tension crack",
none of which it was. 25 is the default number of slices.

The joint of ``test_weak_layer_v1121`` fell for the same numbers and the same
reason. Its path (2, 2)–(16, 1)–(30, 10) is clipped onto the layer from
(2, 2) to (30, 10). The layer wins the whole span, so the vertex at x = 16 is
not a kink of the clipped surface (``WeakLayerSurface.kinks``). Without cuts,
the division is uniform between the same two ends.

The suspicion recorded when D407 was opened, a uniform cut landing on a
mandatory one and leaving a sliver, is refuted for both: neither surface has
any mandatory cut, and the 25 slices of the plane all measure 28/25.

A circle was never refused for this, but one leaving through a vertical face
at x_r, with the ground lower in front, was sliced wrong (found by the
adversarial review of v0.1.458). One ulp past the face, the envelope read
one-sided is the bench in front and not the crest of the face, and the last
corner's base was clamped down to it. The factor moved upwards by several
percent: 4.7 % between the model and its mirror image, with 39 slices.

INVARIANTS, against references outside this code (AGENTS.md, rule 1)

* **The partition.** For every number of slices from 5 to 80 the plane is
  sliced into exactly that many slices. The first starts on x = 2 and the
  last ends on x = 30, both exactly. The interior boundaries are the uniform
  division, bit for bit: only the last one was moved.
* **The joint against Fellenius.** On the joint, the Ordinary method is the
  planar closed form of ``test_weak_layer_v1121`` (``_ordinary_closed_form``)
  to 1e-9 for every number of slices from 5 to 80: a plane has one answer
  whatever n is.
* **Ky against Newmark.** On the plane, Janbu simplified gives
  Ky = tan(φ − β) (Newmark 1965) to 1e-6 with 25, 41, 43, 50 and 51 slices,
  as ``test_yield_acceleration_v1127`` asserts with 60.
* **The door the user sees.** The plane as a surface evaluated with the
  project's own 25 slices gives a factor and no note.
* **A face at the right end, against its mirror image.** A cut toe whose
  vertical face is at x_r, and the same model mirrored, failing the other
  way, with its face at x_l (always exact). For every number of slices from 5
  to 80, a circle leaving through the face ends its last slice on its own arc
  under the crest of the face, and Bishop (1955) gives the model and its
  mirror image one factor, to 1e-10. With the rule of v0.1.457 they differ
  by up to 4.7 %. A last cut pinned only for what is not a circle (option C
  of the prompt) passes every other case here, and fails these two.

Measured on v0.1.457 before the fix (D407, step 0), on a population of
circles of the same slope with c = 5 kPa: see the changelog of v0.1.458 for
how many factors moved in their last bits.

Measured cost: about 1 s, nearly all of it in the slicings and the 152 Bishop
factors of the face.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from test_weak_layer_v1121 import (  # noqa: E402
    _GAMMA, _JOINT_C, _JOINT_PHI, _base_below_the_joint, _fos,
    _ordinary_closed_form, _project,
)
from test_yield_acceleration_v1127 import (  # noqa: E402
    _KY_EXACT, _PLANE, _plane_project, _plane_surface,
)

#: The numbers of slices whose uniform division overshoots x_r = 30 on the
#: plane (``2.0 + (28.0 / n) * n > 30.0``). Correctly rounded IEEE arithmetic,
#: no library function, so the same set on every platform; the project's
#: default, 25, is one of them.
_OVERSHOOT = (25, 41, 43, 50, 51)
_COUNTS = tuple(range(5, 81))


def _plane_slices(n):
    from ogr_slip2d.slicer import slice_surface
    p = _plane_project()
    with p.regions_frozen():
        return slice_surface(p, _plane_surface(), num_slices=n)


class TestThePartition:
    """The plane is cut into exactly the slices asked for, end to end."""

    def test_the_premise_the_overshoot_exists_in_floating_point(self):
        x_l, x_r = _PLANE[0][0], _PLANE[1][0]
        over = [n for n in _COUNTS if x_l + ((x_r - x_l) / n) * n > x_r]
        assert tuple(over) == _OVERSHOOT, over

    def test_every_count_slices_the_plane_end_to_end(self):
        bad = []
        for n in _COUNTS:
            sl = _plane_slices(n)
            if sl is None:
                bad.append((n, "refused"))
                continue
            first, last = sl.slices[0], sl.slices[-1]
            if (len(sl.slices) != n or first.base_x_left != 2.0
                    or last.base_x_right != 30.0):
                bad.append((n, len(sl.slices), first.base_x_left,
                            last.base_x_right))
        assert not bad, bad

    def test_only_the_last_boundary_moves(self):
        from ogr_slip2d.slicer import _slice_boundaries
        x_l, x_r = _PLANE[0][0], _PLANE[1][0]
        p = _plane_project()
        bad = []
        with p.regions_frozen():
            for n in _COUNTS:
                got = _slice_boundaries(p, _plane_surface(), x_l, x_r, n)
                step = (x_r - x_l) / n
                want = [x_l + step * i for i in range(n)] + [x_r]
                if got != want:
                    bad.append(n)
        assert not bad, bad


class TestTheJointAgainstFellenius:
    """The weak-layer joint, the second case of D407, is a plane too."""

    def test_the_ordinary_method_is_the_closed_form_for_every_count(self):
        expected = _ordinary_closed_form(_JOINT_C, _JOINT_PHI, _GAMMA)
        bad = []
        for n in _COUNTS:
            p, _ = _project(joint=(_JOINT_C, _JOINT_PHI))
            res, notes = _fos(p, _base_below_the_joint(),
                              method="ordinary_fellenius", num_slices=n)
            if res is None or res.fos is None:
                bad.append((n, None, notes))
            elif abs(res.fos - expected) > 1e-9 * expected:
                bad.append((n, res.fos))
        assert not bad, (expected, bad)


class TestKyAgainstNewmark:
    """The counts the slicer refused are the ones this has to see."""

    def test_janbu_gives_the_closed_form_ky_with_the_refused_counts(self):
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.yield_acceleration import critical_seismic_coefficient
        bad = []
        for n in _OVERSHOOT:
            p = _plane_project()
            surface = _plane_surface()
            with p.regions_frozen():
                sl = slice_surface(p, surface, num_slices=n)
                assert sl is not None, n
                out = critical_seismic_coefficient(
                    get_method("janbu_simplified")(), p, surface, sl)
            err = abs(out.ky - _KY_EXACT) / _KY_EXACT if out.found else None
            if err is None or err > 1e-6:
                bad.append((n, out.found, out.ky, err))
        assert not bad, (_KY_EXACT, bad)


class TestTheDoorTheUserSees:
    """With the project's default 25 slices the plane gets its factor."""

    def test_the_plane_evaluated_with_the_default_count_has_a_factor(self):
        from ogr_slip2d.analysis_runner import evaluate_surfaces
        p = _plane_project()
        p.seismic.enabled = False
        assert p.settings.methods.num_slices == 25, "the premise: the default"
        # The project's convergence tolerance, not the slicer, is what stands
        # between Janbu and the closed form at the default 0.005 (2.6e-6 off).
        p.settings.methods.tolerance = 1e-10
        p.settings.methods.max_iterations = 400
        out = evaluate_surfaces(p, _plane_surface(), ["janbu_simplified"])
        res = out.results["janbu_simplified"]
        assert res is not None and res.fos is not None, out.warnings
        assert not out.warnings, out.warnings
        # A cohesionless plane: F = tan φ / tan β, the infinite-slope wedge
        # (Duncan & Wright 2005, §6) — what any of the force methods owes it.
        beta = math.atan2(_PLANE[1][1] - _PLANE[0][1],
                          _PLANE[1][0] - _PLANE[0][0])
        expected = math.tan(math.radians(30.0)) / math.tan(beta)
        assert abs(res.fos - expected) < 1e-6 * expected, (res.fos, expected)


#: A cut toe: the crest at y = 25, a slope down to a bench at y = 15, the
#: bench to x = 40, a vertical face down to y = 10 and the ground in front.
_FACE = ((0, 0), (60, 0), (60, 10), (40, 10), (40, 15), (30, 15), (10, 25),
         (0, 25))
_FACE_X, _FACE_TOP, _WIDTH = 40.0, 15.0, 60.0
#: A circle of the default grid of that model that leaves through the face
#: (the adversarial review's, where the two rules differ the most).
_FACE_CIRCLE = (36.0, 38.333333333333336, 26.507002985831416)


def _face_project(mirror):
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project
    from ogr_core.project.units import FailureDirection
    p = Project("face")
    pts = [(_WIDTH - x, y) for x, y in _FACE] if mirror else list(_FACE)
    p.settings.units.failure_direction = (
        FailureDirection.RIGHT_TO_LEFT if mirror
        else FailureDirection.LEFT_TO_RIGHT)
    ext = Polyline([Vertex(*v) for v in pts], closed=True)
    ext.ensure_ccw()
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.add_material(Material(
        name="Soil", unit_weight=20.0,
        strength=MohrCoulomb(cohesion=5.0, friction_angle=30.0)))
    # tight enough that the identity below measures the slicing, not the
    # iteration (the project's default is 0.005)
    p.settings.methods.tolerance = 1e-12
    p.settings.methods.max_iterations = 400
    return p


def _face_circle(mirror):
    from ogr_slip2d.surface import SlipCircle
    cx, cy, r = _FACE_CIRCLE
    return SlipCircle(centre_x=_WIDTH - cx if mirror else cx, centre_y=cy,
                      radius=r)


class TestAFaceAtTheRightEnd:
    """A circle leaving through a vertical face at x_r, the ground lower in
    front: the end of D407 that moved factors by percent, not by bits."""

    def test_the_last_corner_is_on_the_arc_under_the_crest_of_the_face(self):
        from ogr_slip2d.slicer import slice_surface
        p = _face_project(mirror=False)
        bad = []
        with p.regions_frozen():
            for n in _COUNTS:
                c = _face_circle(mirror=False)
                sl = slice_surface(p, c, num_slices=n)
                if sl is None:
                    bad.append((n, "refused"))
                    continue
                last = sl.slices[-1]
                on_arc = c.base_y_at(_FACE_X)
                if (last.base_x_right != _FACE_X
                        or abs(last.base_y_right - on_arc) > 1e-12 * _WIDTH
                        or abs(last.top_y_right - _FACE_TOP) > 1e-12 * _WIDTH):
                    bad.append((n, last.base_x_right, last.base_y_right,
                                on_arc, last.top_y_right))
        assert not bad, bad

    def test_the_model_and_its_mirror_image_give_one_factor(self):
        from ogr_slip2d.methods import get_method
        from ogr_slip2d.slicer import slice_surface
        bishop = get_method("bishop_simplified")()
        fos = {}
        for mirror in (False, True):
            p = _face_project(mirror)
            with p.regions_frozen():
                for n in _COUNTS:
                    c = _face_circle(mirror)
                    sl = slice_surface(p, c, num_slices=n)
                    res = None if sl is None else bishop.compute_fos(p, c, sl)
                    fos[mirror, n] = None if res is None else res.fos
        bad = [(n, fos[False, n], fos[True, n]) for n in _COUNTS
               if fos[False, n] is None or fos[True, n] is None
               or abs(fos[False, n] - fos[True, n]) > 1e-10 * fos[True, n]]
        assert not bad, bad

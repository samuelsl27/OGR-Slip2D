# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Sarma's method with non-vertical slices, registered (spec 009, D357,
v0.1.464).

The factor of safety is the largest F at which the critical acceleration
Kc of the mass (Sarma 1973) equals the applied horizontal coefficient, the
strength of the bases AND of the faces divided by F
(:mod:`ogr_slip2d.sarma.solver`, the project's own derivation; Sarma 1979
was not consulted). It satisfies the force equilibrium of every wedge;
the moments would only place the resultants, and the line of thrust is out
of scope, so ``SATISFIES_MOMENT`` is False.

TWO ENTRIES (spec 009, «Decisiones de diseño»)

* **Wedges** (:class:`ogr_slip2d.sarma.wedges.Wedges`), which the searches
  build on every surface they slice for this method (the loop of a
  search reads ``NON_VERTICAL`` and calls ``_wedge_trial``): the full
  method, with inclined faces.
* **Vertical slices**, from any other caller (the tests that walk the
  registry, a script): read as wedges with vertical faces, with the faces'
  own strength and water of the setting (``wedges.vertical_faces``). So
  the identities those callers check on the slices they hand in (the weight
  of the given slices, F/γ) hold for this method too, without exempting it.

What is refused, with a code and never NaN: a surface with supports
(``lem.sarma_supports``; the spec leaves supports out of scope), and what
the wedges or the solver refuse. Rapid drawdown and the excess pore
pressure of loading are not computed, and the run says so once
(``analysis_runner.non_vertical_skip``); the wrapper
``rapid_drawdown.wrap_for_drawdown`` gives this method,
``NonVerticalDrawdownRefusal``, is the net for a door that skips that
check.

Author: Samuel Sáez López (UPCT)

References:
    Sarma, S. K. (1973). Stability analysis of embankments and slopes.
        Géotechnique 23(3), 423–433. Consulted.
    Sarma, S. K. (1979). Stability analysis of embankments and slopes.
        J. Geotech. Eng. Div. ASCE 105(GT12), 1511–1524. NOT consulted.
"""
from __future__ import annotations

import math
from typing import Optional

from ogr_core.project import Project

from .. import messages as msg
from ..sarma import solver as _solver
from ..sarma import wedges as _wedges
from ..sarma.angles import ANGLE_SETTINGS, BISECTOR, OPTIMIZED_MODES
from ..sarma.vertical import from_vertical_slices
from ..slicer import Slices
from ..surface import SurfaceProtocol
from .base import (
    REASON_NON_PHYSICAL_FOS,
    REASON_NOT_CONVERGED,
    REASON_SARMA_REFUSED,
    REASON_ZERO_DRIVING,
    LEMMethod,
    LEMResult,
    register_method,
)

#: The reason of a result the solver refuses, by its code.
_REASONS = {
    msg.SARMA_NO_DRIVING: REASON_ZERO_DRIVING,
    msg.SARMA_NO_ROOT: REASON_NON_PHYSICAL_FOS,
    msg.NOT_CONVERGED: REASON_NOT_CONVERGED,
}

#: v0.1.466 (D451) -- below this least |q| of the faces (``min_abs_q`` of
#: the solution, the analogue of m_alpha: each face thrust is divided by its
#: q) the factor is a root of Kc(F) = kh next to a pole, and the run says so
#: (``method.sarma_near_pole``) without taking the factor away: by the
#: owner's decision of 2026-11-16, after the adversarial review, which root
#: such a surface should report is open (D452). The review measured why
#: the first guard, a refusal above ten times the weight on the
#: ``max_force_ratio``, failed both ways: a vertex drawn 2 m off the scarp
#: of problem 4 left a root above a pole with forces of 7.5 times the
#: weight (least |q| 0.074), and a straight base with a face cohesion of
#: 6000 kPa, far from any pole (least |q| 0.88, the factor equal to
#: Janbu's), reached 10.9 because X carries c̄′d. 0.2 is the limit of the
#: m-alpha check (Whitman & Bailey 1967), taken by analogy and declared as
#: such. A constant, not a setting.
NEAR_POLE_MIN_Q = 0.2

def _near_pair_details(pair) -> dict:
    """``details`` of ``solver.near_pair`` (v0.1.470, D452): the distance of
    the factor to a zero of D and the next root down, or nothing."""
    if pair is None:
        return {}
    distance, next_root = pair
    return {"sarma_kc_pole_distance": distance, "sarma_next_root": next_root}


def frozen_faces_of(result):
    """``(boundaries, {x: θ°})`` of every interior face of a result on
    optimised wedges (``Wedges.angle_policy`` one of ``OPTIMIZED_MODES``),
    for ``SarmaNonVertical.frozen_faces``; None for any other result
    (v0.1.471). The faces given at vertices go too: a surface rebuilt from
    its dictionary may come without them."""
    w = getattr(result, "slices", None)
    if (not isinstance(w, _wedges.Wedges)
            or w.angle_policy not in OPTIMIZED_MODES or not w.boundaries):
        return None
    return (tuple(w.boundaries),
            {f.x_base: math.degrees(f.theta) for f in w.faces[1:-1]})


def freeze_faces(method, result) -> None:
    """``method.frozen_faces`` from the optimised wedges of ``result``
    (:func:`frozen_faces_of`), when the method takes them (v0.1.471): the
    one door of the two runs that evaluate a deterministic critical surface
    again, the probabilistic Global Minimum and the sensitivity (the review
    of 0.1.471: the sensitivity gave the bisector's factor at the mean)."""
    frozen = frozen_faces_of(result)
    if frozen is not None and hasattr(method, "frozen_faces"):
        method.frozen_faces = frozen


#: The strength of the faces, as ``settings.sarma.interslice_strength``.
INTERSLICE_STRENGTHS = ("materials", "given", "none")


def face_strength_of(kind: str, cohesion: float = 0.0, phi: float = 0.0):
    """What :func:`ogr_slip2d.sarma.wedges.build_wedges` takes as
    ``face_strength`` for ``settings.sarma.interslice_strength``."""
    if kind == "materials":
        return _wedges.MATERIALS
    if kind == "none":
        return _wedges.NO_STRENGTH
    if kind == "given":
        return (float(cohesion), float(phi))
    raise ValueError("interslice strength must be one of %s, not %r"
                     % (INTERSLICE_STRENGTHS, kind))


@register_method
class SarmaNonVertical(LEMMethod):
    METHOD_ID = "sarma"
    DISPLAY_NAME = "Sarma (non-vertical)"
    SATISFIES_FORCE = True
    SATISFIES_MOMENT = False
    #: The searches build this method's wedges after slicing (v0.1.464).
    NON_VERTICAL = True
    #: Supports are refused with a code (spec 009, «Fuera de alcance»).
    ACCEPTS_SUPPORTS = False

    def __init__(self, tolerance: float = 1e-4, max_iterations: int = 75,
                 initial_fos: float = 1.0, min_lambda: float = -0.1,
                 max_lambda: float = 6.0, iterate_steffensen: bool = False,
                 *, num_wedges: int = 25, angle_policy: str = BISECTOR,
                 face_strength=_wedges.MATERIALS,
                 boundaries_at_materials: bool = True,
                 shear_sense: str = _solver.FIXED):
        # The global initial F, λ range and Steffensen switch reach no part
        # of this method: it brackets F itself (``solver.solve``).
        super().__init__(tolerance=tolerance, max_iterations=max_iterations,
                         initial_fos=initial_fos, min_lambda=min_lambda,
                         max_lambda=max_lambda,
                         iterate_steffensen=iterate_steffensen)
        if angle_policy not in ANGLE_SETTINGS:
            raise ValueError("angle policy must be one of %s, not %r"
                             % (ANGLE_SETTINGS, angle_policy))
        if shear_sense not in _solver.SHEAR_SENSES:
            raise ValueError("shear sense must be one of %s, not %r"
                             % (_solver.SHEAR_SENSES, shear_sense))
        self.num_wedges = int(num_wedges)
        # v0.1.471 -- an optimised mode is the bisector on every surface
        # the search computes, and the optimiser where the mode says
        # (``optimize_angles``; the search reads ``optimize_angles``)
        self.optimize_angles = (angle_policy if angle_policy in OPTIMIZED_MODES
                                else None)
        self.angle_policy = (BISECTOR if self.optimize_angles
                             else angle_policy)
        #: v0.1.471 -- ``(boundaries, {x: θ°})`` of the optimised faces of a
        #: critical surface, which this method's wedges then take instead
        #: of a policy: the samples of a Global Minimum probabilistic run
        #: compute the deterministic mechanism, faces and all (the owner's
        #: decision of 2026-11-17), and the check of D88 asks the same.
        self.frozen_faces = None
        self.face_strength = face_strength
        self.boundaries_at_materials = bool(boundaries_at_materials)
        self.shear_sense = shear_sense

    # ------------------------------------------------------------------
    def wedges_for(self, project: Project, surface: SurfaceProtocol,
                   vertical: Slices, reasons=None, *, policy=None,
                   boundaries=None, face_angles=None):
        """The wedges this method computes ``surface`` on, built on the
        slicer's ``vertical`` slices with the method's settings; None, with
        the reason in ``reasons``, when the constructor refuses.

        v0.1.471 -- ``policy``, ``boundaries`` and ``face_angles`` are the
        optimiser's (``build_wedges``): a policy other than the method's,
        and the faces it sets by abscissa. Without any of them, the frozen
        faces of ``frozen_faces``, when their ends are this mass's.

        v0.1.465 (D357) -- with the per-vertex data the surface carries
        (fields of ``SlipSurface``, set by ``surface.attach_vertex_data``
        and carried by every copy and by Optimize's walk), or the surface a
        weak layer clipped (``base``): a datum whose vertex is not on the
        computed surface (cut off by a crack, moved by Optimize, clipped),
        or the farther of two on one vertex, is left out and listed in
        ``Wedges.unused_vertex_data``, which the run says
        (``analysis_runner.sarma_notes``, and per stored polyline the
        search's ``search.user_polyline_sarma_unused``)."""
        holder = surface
        if (getattr(surface, "vertex_angles", None) is None
                and getattr(surface, "vertex_strength", None) is None):
            holder = getattr(surface, "base", None) or surface
        strengths = getattr(holder, "vertex_strength", None)
        if strengths and getattr(project, "design_factored_copy", False):
            # the design standard's material factors, on the copy only, in
            # this one place (``design_factors.factored_face_strength``)
            from ogr_core.project.design_factors import factored_face_strength
            ds = project.settings.design_standard
            strengths = {k: factored_face_strength(c, phi, ds)
                         for k, (c, phi) in strengths.items()}
        frozen = None
        if (policy is None and boundaries is None and face_angles is None
                and self.frozen_faces is not None
                and _wedges.boundaries_fit(project, vertical,
                                           self.frozen_faces[0])):
            frozen = self.frozen_faces
            boundaries, face_angles = frozen
        out = _wedges.build_wedges(
            project, surface, vertical, self.num_wedges,
            angles=policy or self.angle_policy,
            vertex_angles=getattr(holder, "vertex_angles", None),
            face_strength=self.face_strength,
            vertex_strength=strengths,
            boundaries_at_materials=self.boundaries_at_materials,
            reasons=reasons, boundaries=boundaries, face_angles=face_angles)
        if frozen is not None and out is not None:
            out.angle_policy = self.optimize_angles or OPTIMIZED_MODES[0]
        return out

    def larger_root_above(self, project: Project, result) -> Optional[float]:
        """v0.1.471 (D457) -- a factor above ``result.fos`` where the H of
        its wedges changes sign (``solver.larger_root_above``), or None: the
        guard the optimiser of the angles asks of each factor it keeps. The
        wedges are read as :meth:`compute_fos` reads them."""
        slices = getattr(result, "slices", None)
        if not isinstance(slices, _wedges.Wedges) or result.fos is None:
            return None
        kh = project.seismic.kh if project.seismic.enabled else 0.0
        kv = project.seismic.kv if project.seismic.enabled else 0.0
        s_in = _wedges.to_solver(slices, kh, kv)
        return _solver.larger_root_above(
            s_in.bases, s_in.faces, result.fos, kh=kh,
            slide_sign=s_in.slide_sign, shear_sense=self.shear_sense,
            head_thrust=s_in.head_thrust)

    def _refused(self, surface, slices, code, **args):
        return LEMResult(fos=None, converged=False, iterations=0,
                         method_id=self.METHOD_ID, surface=surface,
                         slices=slices, reason=REASON_SARMA_REFUSED,
                         **msg.failure(code, **args))

    def _near_pair(self, sol, bases, faces, kh, sign, head) -> dict:
        """v0.1.470 (D452) -- for a factor already next to a pole of the
        recurrence (least |q| under ``NEAR_POLE_MIN_Q``), whether it lies
        next to a zero of D too, and the next root down (``solver.
        near_pair``): only there, so no other surface pays for it. The
        factor is not touched."""
        q = sol.min_abs_q
        if q is not None and q >= NEAR_POLE_MIN_Q:
            return {}
        return _near_pair_details(_solver.near_pair(
            bases, faces, sol.fos, kh=kh, slide_sign=sign,
            shear_sense=self.shear_sense, head_thrust=head,
            tolerance=self.tolerance, max_iterations=self.max_iterations))

    def compute_fos(self, project: Project, surface: SurfaceProtocol,
                    slices: Slices) -> LEMResult:
        strengthless = self._no_shear_strength_result(surface, slices)
        if strengthless is not None:
            return strengthless
        kh = project.seismic.kh if project.seismic.enabled else 0.0
        kv = project.seismic.kv if project.seismic.enabled else 0.0
        is_wedges = isinstance(slices, _wedges.Wedges)
        vertical = slices.vertical if is_wedges else slices

        from ..methods.janbu import slide_sense
        from ..support_integration import resolve_support_terms
        sign = int(slide_sense(list(vertical), kh, kv))
        if resolve_support_terms(project, surface, vertical, sign).present:
            return self._refused(surface, slices, msg.SARMA_SUPPORTS)

        if is_wedges:
            s_in = _wedges.to_solver(slices, kh, kv)
            bases, faces = s_in.bases, s_in.faces
            head, sign = s_in.head_thrust, s_in.slide_sign
        else:
            reasons = []
            faces = _wedges.vertical_faces(project, slices,
                                           self.face_strength, reasons)
            if faces is None:
                code, args = reasons[0]
                return self._refused(surface, slices, code, **args)
            w = from_vertical_slices(slices, kh, kv)
            bases, head, sign = w.bases, 0.0, w.slide_sign
        sol = _solver.solve(bases, faces, kh=kh, slide_sign=sign,
                            shear_sense=self.shear_sense, head_thrust=head,
                            tolerance=self.tolerance,
                            max_iterations=self.max_iterations)
        if sol.fos is None:
            if sol.code == msg.SARMA_FACE_PARALLEL:
                return self._refused(surface, slices, sol.code, **sol.args)
            return LEMResult(fos=None, converged=False,
                             iterations=sol.iterations,
                             method_id=self.METHOD_ID, surface=surface,
                             slices=slices,
                             reason=_REASONS.get(sol.code,
                                                 REASON_SARMA_REFUSED),
                             **msg.failure(sol.code, **sol.args))
        F = sol.fos
        normals = sol.base_normals or []
        strengths = [b.cohesion * b.length + n_eff * b.tan_phi
                     for b, n_eff in zip(bases, normals)]
        # v0.1.467 -- ``base_shear_force`` is the DRIVING force
        # s·W_total·sin α of every method (``LEMResult``, v0.1.107), and
        # Sarma had put the mobilised shear there, which the panel printed
        # under «Driving shear W·sinα»: the defect v0.1.107 closed in five
        # methods, by the owner's decision now closed here. The mobilised
        # shear, strength/F, goes to ``details["sarma_base_shear"]``.
        from .bishop import driving_shear_forces
        return LEMResult(
            fos=F, converged=True, iterations=sol.iterations,
            method_id=self.METHOD_ID, surface=surface, slices=slices,
            base_normal_force=[n_eff + b.pore_force
                               for b, n_eff in zip(bases, normals)],
            base_shear_force=driving_shear_forces(list(slices), kh, kv,
                                                  sign),
            base_shear_strength=strengths,
            details={
                "sarma_base_shear": [t / F for t in strengths],
                "kh": kh, "kv": kv, "slide_sign": sign,
                # the total normal of the method's own solution, which the
                # Tensile Stress Check reads as N/l - U/l
                "solved_base_normal": [n_eff + b.pore_force
                                       for b, n_eff in zip(bases, normals)],
                "sarma_kc": sol.kc_at_1,
                "sarma_min_q": sol.min_q,
                # v0.1.466 (D451): None when a q vanishes at the root itself
                "sarma_min_abs_q": sol.min_abs_q,
                "sarma_max_force_ratio": sol.max_force_ratio,
                "sarma_shear_sense": self.shear_sense,
                "sarma_kinematically_admissible":
                    sol.kinematically_admissible,
                "sarma_verticalized": (slices.verticalized if is_wedges
                                       else 0),
                **self._near_pair(sol, bases, faces, kh, sign, head),
                "sarma_face_thrusts": sol.face_thrusts,
                "sarma_face_effective": sol.face_effective,
                "sarma_face_shears": sol.face_shears,
                # v0.1.468 -- PW per face, the crack's water on the head one
                "sarma_face_water": sol.face_water,
                "sarma_non_vertical": is_wedges,
            })

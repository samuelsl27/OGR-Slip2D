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

from ogr_core.project import Project

from .. import messages as msg
from ..sarma import solver as _solver
from ..sarma import wedges as _wedges
from ..sarma.angles import BISECTOR, POLICIES
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
        if angle_policy not in POLICIES:
            raise ValueError("angle policy must be one of %s, not %r"
                             % (POLICIES, angle_policy))
        if shear_sense not in _solver.SHEAR_SENSES:
            raise ValueError("shear sense must be one of %s, not %r"
                             % (_solver.SHEAR_SENSES, shear_sense))
        self.num_wedges = int(num_wedges)
        self.angle_policy = angle_policy
        self.face_strength = face_strength
        self.boundaries_at_materials = bool(boundaries_at_materials)
        self.shear_sense = shear_sense

    # ------------------------------------------------------------------
    def wedges_for(self, project: Project, surface: SurfaceProtocol,
                   vertical: Slices, reasons=None):
        """The wedges this method computes ``surface`` on, built on the
        slicer's ``vertical`` slices with the method's settings; None, with
        the reason in ``reasons``, when the constructor refuses."""
        return _wedges.build_wedges(
            project, surface, vertical, self.num_wedges,
            angles=self.angle_policy, face_strength=self.face_strength,
            boundaries_at_materials=self.boundaries_at_materials,
            reasons=reasons)

    def _refused(self, surface, slices, code, **args):
        return LEMResult(fos=None, converged=False, iterations=0,
                         method_id=self.METHOD_ID, surface=surface,
                         slices=slices, reason=REASON_SARMA_REFUSED,
                         **msg.failure(code, **args))

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
        return LEMResult(
            fos=F, converged=True, iterations=sol.iterations,
            method_id=self.METHOD_ID, surface=surface, slices=slices,
            base_normal_force=[n_eff + b.pore_force
                               for b, n_eff in zip(bases, normals)],
            base_shear_force=[t / F for t in strengths],
            base_shear_strength=strengths,
            details={
                "kh": kh, "kv": kv, "slide_sign": sign,
                # the total normal of the method's own solution, which the
                # Tensile Stress Check reads as N/l - U/l
                "solved_base_normal": [n_eff + b.pore_force
                                       for b, n_eff in zip(bases, normals)],
                "sarma_kc": sol.kc_at_1,
                "sarma_min_q": sol.min_q,
                "sarma_max_force_ratio": sol.max_force_ratio,
                "sarma_shear_sense": self.shear_sense,
                "sarma_kinematically_admissible":
                    sol.kinematically_admissible,
                "sarma_verticalized": (slices.verticalized if is_wedges
                                       else 0),
                "sarma_face_thrusts": sol.face_thrusts,
                "sarma_face_effective": sol.face_effective,
                "sarma_face_shears": sol.face_shears,
                "sarma_non_vertical": is_wedges,
            })

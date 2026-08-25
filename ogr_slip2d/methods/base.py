# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Abstract base class & plugin registry for Limit Equilibrium Methods.

Each LEM method is a subclass of :class:`LEMMethod` registered with the
``@register_method`` decorator. The GUI dropdown and the CLI ``--method``
flag both enumerate the registry, so adding a new method requires
**only** creating a new file in this package.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar, Optional

from ogr_core.project import Project

from ..slicer import Slices
from ..surface import SurfaceProtocol


# ======================================================================
@dataclass
class LEMResult:
    """Result of a single FoS calculation on a specific slip surface."""

    fos: float
    converged: bool
    iterations: int
    method_id: str
    surface: SurfaceProtocol
    slices: Slices
    error_message: str = ""

    # Per-slice arrays. ALL THREE ARE FORCES, in kN/m per unit
    # out-of-plane width, and none of them is a stress:
    #
    #   base_normal_force    N, the normal force on the slice base
    #   base_shear_force     the DRIVING force, s*W_total*sin(alpha)
    #   base_shear_strength  tau_f * l, the available shear RESISTANCE -
    #                        the name says strength and the number is a
    #                        force, which is why this list exists
    #
    # v0.1.107 - ``base_normal`` was the old name of the first one, and
    # reading it as kPa gives a number about four times too small and
    # plausible enough to go unnoticed: it stayed wrong in two benchmark
    # sheets until one that publishes the STRESS caught it (force 7.69,
    # stress 36.46, published 36.33). The effective stress is
    # ``N/l - u``; the mobilised shear is ``base_shear_strength / fos``.
    base_normal_force: list[float] = field(default_factory=list)
    base_shear_force: list[float] = field(default_factory=list)
    base_shear_strength: list[float] = field(default_factory=list)

    # v0.1.22 — method-specific extras. Recognised keys:
    #   "boundary_ratios": list[float] of X/E at each of the n+1 slice
    #       boundaries (used by the line-of-thrust post-processor).
    #       Methods that assume X = 0 (Bishop, Janbu, Ordinary) may omit
    #       it; zeros are assumed.
    #   "lambda": converged interslice scaling (Spencer: tanθ; GLE: λ).
    details: dict = field(default_factory=dict)

    # v0.1.32 — post-analysis admissibility (anomaly A3). Surfaces that
    # fail the Tensile Stress or m-alpha checks stay in the evaluation
    # list (so search algorithms that need feedback, such as Simulated
    # Annealing, keep working) but are excluded when the CRITICAL
    # surface is selected.
    admissible: bool = True
    # Why the surface was judged inadmissible. Deliberately NOT stored in
    # ``error_message``: that field marks a FAILED calculation and feeds
    # ``is_valid``, whereas an inadmissible surface has a perfectly
    # converged (but physically unreliable) factor of safety.
    admissibility_note: str = ""

    @property
    def base_normal(self) -> list[float]:
        """Deprecated alias of :attr:`base_normal_force`.

        Kept read-only because the name is the trap the rename exists to
        close: it reads like a stress and holds a force. Scripts outside
        this repository still ask for it by that name.
        """
        return self.base_normal_force

    @property
    def is_valid(self) -> bool:
        return (
            self.converged
            and math.isfinite(self.fos)
            and self.fos > 0
            and not self.error_message
        )

    def to_dict(self) -> dict:
        return {
            "fos": self.fos,
            "converged": self.converged,
            "iterations": self.iterations,
            "method": self.method_id,
            "surface": self.surface.to_dict(),
            "slices": self.slices.to_list(),
            "base_normal_force": list(self.base_normal_force),
            "base_shear_force": list(self.base_shear_force),
            "base_shear_strength": list(self.base_shear_strength),
            "error": self.error_message,
        }


# ======================================================================
class LEMMethod(ABC):
    """Abstract Limit Equilibrium Method.

    Concrete subclasses must implement :meth:`compute_fos` for a single
    pre-sliced failure surface.
    """

    METHOD_ID: ClassVar[str] = ""
    DISPLAY_NAME: ClassVar[str] = ""
    SATISFIES_FORCE: ClassVar[bool] = False
    SATISFIES_MOMENT: ClassVar[bool] = False

    def __init__(
        self,
        tolerance: float = 1e-3,
        max_iterations: int = 75,
        initial_fos: float = 1.0,
        min_lambda: float = -0.1,
        # v0.1.90 — was 1.5, now the reference's own upper default. It
        # does NOT widen the first sampling pass (see lambda_grid); it is
        # the room the lazy extension is allowed to use.
        max_lambda: float = 6.0,
        iterate_steffensen: bool = False,
    ) -> None:
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.initial_fos = initial_fos
        # v0.1.74 — the λ search range, for the two methods that have
        # one. Kept on the base class so a caller can hand the same
        # configuration to every method without knowing which of them
        # will use it.
        self.min_lambda = min_lambda
        self.max_lambda = max_lambda
        self.iterate_steffensen = iterate_steffensen

    # ------------------------------------------------------------------
    @staticmethod
    def aitken(x0: float, x1: float, x2: float):
        """Aitken Δ² extrapolation of three fixed-point iterates.

        Applying it to every third iterate of ``x ← g(x)`` is Steffensen's
        method in its practical form, and it is what the reference's
        "Use Steffensen's Method" switch does: the same equation, reached
        in fewer passes.

        Returns None when the extrapolation is not usable — a vanishing
        second difference (the sequence has already converged, so there
        is nothing to accelerate and the formula would divide by nearly
        zero) or a non-physical result. The caller then simply keeps the
        plain iterate, which is why turning the option on cannot make a
        surface fail that would otherwise have converged.
        """
        import math as _math
        second_difference = x2 - 2.0 * x1 + x0
        if abs(second_difference) < 1e-14:
            return None
        accelerated = x0 - (x1 - x0) ** 2 / second_difference
        if not _math.isfinite(accelerated) or accelerated <= 0.0:
            return None
        return accelerated

    # ------------------------------------------------------------------
    # The λ sampling grid, shared by Spencer and GLE.
    #
    # The spacing is NOT uniform, and that is deliberate: it is dense
    # near zero, where most surfaces converge, and reaches ±1.5 because
    # some geometries genuinely need it — the reference-validated circle
    # of the Ej1 case converges under GLE at λ = 1.4919. It is a
    # calibrated list, so a user-supplied range CLIPS it rather than
    # replacing it with a linear spacing: at the default ±1.5 the result
    # is the identical list, so no stored project moves.
    _LAMBDA_SHAPE = (-1.5, -1.0, -0.6, -0.4, -0.2, -0.1, 0.0,
                     0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5)

    # v0.1.90 — λ BEYOND the calibrated shape, sampled ONLY when the shape
    # found no bracket. Two facts made this necessary:
    #
    # * The reference's own models carry ``min_lambda: -0.1`` and
    #   ``max_lambda: 6``, with the enforcement checkboxes OFF — so it does
    #   not restrict λ by default at all, while this program clipped at
    #   ±1.5 always.
    # * Measured on a Simulated Annealing candidate that GLE could not
    #   solve: F_f − F_m is monotone in λ and still −0.32 at λ = 1.5. The
    #   root is at λ = 2.994, where F_f = 1.1257 and F_m = 1.1262, giving
    #   FoS 1.1260 against a circular minimum of 1.1239 on the same model.
    #   Every one of the 61 candidates of that run failed with "no
    #   λ-bracket"; none of them was unsolvable, all of them were
    #   unreachable.
    #
    # Positive only, and that is not an oversight: λ is the interslice
    # force ratio X/E, and the far side of the range that surfaces reach
    # for is the steep-interslice one. The reference's own lower bound is
    # −0.1, well inside what the shape above already covers.
    #
    # This has bitten once before, which is why it is sampled lazily
    # rather than by widening the shape: the range used to be ±1.25 and
    # was raised to ±1.5 in v0.1.74 because the reference-validated Ej_1
    # circle converges at λ = 1.4919 — widened exactly enough for the case
    # that failed at the time. Sampling these only on failure means every
    # surface that converges today is untouched, by construction, and only
    # the ones that currently give up pay for the extra evaluations.
    _LAMBDA_EXTENSION = (2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0)

    def lambda_grid(self) -> list:
        """The λ values sampled FIRST: the calibrated shape, clipped.

        Intersected with the calibrated span as well as with the user's
        range, so that widening ``max_lambda`` does not add samples here.
        Anything beyond the shape belongs to :meth:`lambda_grid_extension`
        and is only reached when this grid brackets nothing.
        """
        lo = max(min(self.min_lambda, self.max_lambda),
                 min(self._LAMBDA_SHAPE))
        hi = min(max(self.min_lambda, self.max_lambda),
                 max(self._LAMBDA_SHAPE))
        if hi < lo:
            lo = hi = min(max(self.min_lambda, self.max_lambda),
                          max(self._LAMBDA_SHAPE))
        grid = [v for v in self._LAMBDA_SHAPE if lo <= v <= hi]
        # The endpoints always belong to the search: without them a
        # narrowed range could lose the sign change that brackets the
        # root and report "all sampled λ diverged" for a surface that has
        # a perfectly good solution just outside the surviving samples.
        for end in (lo, hi):
            if not any(abs(v - end) < 1e-12 for v in grid):
                grid.append(end)
        return sorted(grid)

    def lambda_grid_extension(self) -> list:
        """The λ tried only after :meth:`lambda_grid` brackets nothing.

        Bounded by the user's configured range, so narrowing it still
        narrows the search — a range the user set has to mean something
        (rule 7), and it means the same thing here as it always did.
        """
        lo = min(self.min_lambda, self.max_lambda)
        hi = max(self.min_lambda, self.max_lambda)
        out = [v for v in self._LAMBDA_EXTENSION if lo <= v <= hi]
        if hi > max(self._LAMBDA_SHAPE) and not any(
                abs(v - hi) < 1e-12 for v in out):
            out.append(hi)
        return sorted(out)

    # ------------------------------------------------------------------
    # A SURFACE WITH NO SHEAR STRENGTH AT ALL.
    #
    # Every method answers this with the same value and the same words, and
    # the uniformity is the point. Measured on 0.1.98, a mass lying entirely
    # inside a c = 0, phi = 0 material got six different answers out of the
    # nine methods:
    #
    #   Bishop, Janbu simplified, Janbu corrected  ZeroDivisionError
    #   Spencer, GLE                               nan, "all sampled lambda
    #                                              diverged" — a false reason
    #   Corps 1, Corps 2, Lowe-Karafiath           0.2, which is not a factor
    #                                              of safety but the first
    #                                              sample of their F grid
    #   Ordinary / Fellenius                       0.0, right and unexplained
    #
    # The three that raised did so because the numerator is EXACTLY 0.0, so
    # F becomes 0.0 — which is finite, and therefore passes the isfinite
    # guard — and the next pass evaluates tan(phi)/F as 0.0/0.0. In Python
    # that is ZeroDivisionError, not nan, so the m_alpha guard two lines
    # further down never runs and the exception leaves the search.
    #
    # The answer is not a modelling choice. With tau = 0 on every slice base
    # the resisting term of Bishop (1955), c'*b + (W - u*b)*tan(phi'),
    # vanishes identically, so F = 0 exactly: a mass with no strength
    # anywhere does not stand up.
    #
    # It is reported as a FAILED calculation rather than as a factor of
    # safety of zero, which is what the reference documentation does with
    # this exact condition — it writes an error code in place of the safety
    # factor, and the surface joins the invalid population. Here that means
    # ``error_message`` (so ``is_valid`` is False and the searches count it
    # in ``invalid_count``) and NOT ``admissible=False``, which is reserved
    # for a CONVERGED factor that fails a post-analysis check.

    #: One string, so a caller can group by it. Deliberately not passed
    #: through ``tr()``: every other engine reason is a plain English
    #: string and the interface translates at the point of display.
    NO_SHEAR_STRENGTH_NOTE: ClassVar[str] = (
        "Zero shear strength on the whole slip surface — "
        "factor of safety is zero"
    )

    @staticmethod
    def surface_has_no_shear_strength(slices) -> bool:
        """True when NO slice base offers any shear resistance.

        Both the cohesion and the friction tangent of the linearised
        envelope have to be zero on every slice — the condition under which
        the resisting term of every method here is identically zero.

        The envelope is read through ``BishopSimplified._local_c_phi``, the
        one linearisation the nine methods already share, so the verdict
        covers the non-linear strength models and matric suction as well as
        Mohr-Coulomb. ``InfiniteStrength`` linearises to 1e12, so it can
        never trip this.

        The effective normal stress is the same first-pass estimate the
        methods use for their own first iteration,
        ``sigma'_n = max(0, W*cos(alpha) - u*l) / l``, with the seismic
        coefficients left out so the predicate needs nothing from the
        project. For a linear envelope the verdict does not depend on
        sigma' at all; for a non-linear one this is the same point the
        method itself evaluates first.

        Returns on the FIRST slice that has any strength, so an ordinary
        surface pays one envelope evaluation.

        Measured over the 4860 circles of the problem-27 reference grid:
        true for 147 of the 147 that raised ZeroDivisionError, false for
        all 4713 others.
        """
        from ..external_forces import slice_forces
        from .bishop import BishopSimplified

        any_slice = False
        for s in slices:
            any_slice = True
            length = max(s.base_length, 1e-9)
            w = slice_forces(s).w_total
            sigma_n_eff = max(
                0.0, w * math.cos(s.base_angle) - s.pore_pressure * length
            ) / length
            c, tan_phi = BishopSimplified._local_c_phi(
                s, s.material, sigma_n_eff
            )
            if c != 0.0 or tan_phi != 0.0:
                return False
        # An empty slice list is not a strengthless surface, it is no
        # surface. The methods have their own "no slices" paths for that.
        return any_slice

    def _no_shear_strength_result(
        self, surface: SurfaceProtocol, slices: Slices
    ) -> Optional[LEMResult]:
        """The result for a strengthless surface, or None if it has strength.

        Called first by every ``compute_fos``, which is what makes the nine
        methods agree instead of failing six different ways.
        """
        if not self.surface_has_no_shear_strength(slices):
            return None
        return LEMResult(
            fos=0.0,
            converged=False,
            iterations=0,
            method_id=self.METHOD_ID,
            surface=surface,
            slices=slices,
            error_message=self.NO_SHEAR_STRENGTH_NOTE,
        )

    # ------------------------------------------------------------------
    @abstractmethod
    def compute_fos(
        self,
        project: Project,
        surface: SurfaceProtocol,
        slices: Slices,
    ) -> LEMResult:
        """Compute the Factor of Safety for one failure surface."""

    # v0.1.120 — ``_shear_strength`` used to live here: a one-line helper
    # that asked ``material.strength.shear_strength(sigma)`` with no
    # SliceContext. Its only reader was Ordinary/Fellenius, and through it
    # that method silently ignored the eight strength models that depend on
    # more than sigma'n, plus the matric-suction cohesion. It is deleted
    # rather than fixed: a context-free strength lookup sitting on the base
    # class is an invitation to use it, and there is exactly one right way
    # to read an envelope in this program — ``_local_c_phi``.


# ======================================================================
_METHOD_REGISTRY: dict[str, type[LEMMethod]] = {}


def register_method(cls: type[LEMMethod]) -> type[LEMMethod]:
    if not cls.METHOD_ID:
        raise ValueError(f"{cls.__name__} has no METHOD_ID")
    if cls.METHOD_ID in _METHOD_REGISTRY:
        raise ValueError(f"Duplicate METHOD_ID: {cls.METHOD_ID}")
    _METHOD_REGISTRY[cls.METHOD_ID] = cls
    return cls


def method_registry() -> dict[str, type[LEMMethod]]:
    return dict(_METHOD_REGISTRY)


def get_method(method_id: str) -> type[LEMMethod]:
    if method_id not in _METHOD_REGISTRY:
        raise KeyError(
            f"Unknown method '{method_id}'. Available: {list(_METHOD_REGISTRY)}"
        )
    return _METHOD_REGISTRY[method_id]

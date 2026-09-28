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
# WHY A CALCULATION HAS NO FACTOR OF SAFETY.
#
# v0.1.152 (D56) — the reason codes, one per condition, so a caller can
# GROUP by reason instead of matching free text. ``error_message`` keeps
# the sentence a human reads; these are the handle a program takes.
#
# That split is not an invention: the reference documentation writes an
# error CODE in place of the safety factor and prints its description
# separately, and its own run summaries count surfaces by code — "Error
# Code -108 reported for 256 surfaces". With only a free string here, the
# equivalent line cannot be produced without parsing prose.
#
# Deliberately NOT passed through ``tr()``, for the same reason as
# ``NO_SHEAR_STRENGTH_NOTE`` below: every engine reason is a plain English
# string and the interface translates at the point of display.

#: The surface produced no slices at all.
REASON_NO_SLICES = "no_slices"
#: No slice base offers any shear resistance; see NO_SHEAR_STRENGTH_NOTE.
REASON_NO_SHEAR_STRENGTH = "no_shear_strength"
#: The total driving moment (or force) vanishes: the mass does not slide,
#: so there is no factor of safety to report. The reference gives this
#: condition its own code and says it exists to keep extremely high
#: factors from being calculated when the driving force is very small.
REASON_ZERO_DRIVING = "zero_driving"
#: Active support alone exceeds the driving moment.
REASON_ACTIVE_SUPPORT_EXCEEDS_DRIVING = "active_support_exceeds_driving"
#: m-alpha collapsed towards zero on a slice base.
REASON_M_ALPHA_COLLAPSED = "m_alpha_collapsed"
#: n-alpha collapsed towards zero on a slice base (the Janbu analogue).
REASON_N_ALPHA_COLLAPSED = "n_alpha_collapsed"
#: The arithmetic produced a factor that is not a physical one (<= 0, or
#: not a finite number).
REASON_NON_PHYSICAL_FOS = "non_physical_fos"
#: The iteration ran out of passes before the factor settled. There IS a
#: number — the last iterate — but it is where the solver happened to
#: stop, not where it was going.
#:
#: v0.1.152 (D56) — this one was found by the guard rather than by the
#: report that opened the defect. Every iterative method returned that last
#: iterate with ``converged=False`` and NOTHING else: no message, no note.
#: The reference gives the condition a code of its own and names the
#: setting that causes it, which is the difference between "this surface
#: has no answer" and "raise the iteration limit".
REASON_NOT_CONVERGED = "not_converged"
#: Every sampled interslice ratio diverged; no branch to solve on.
REASON_ALL_LAMBDA_DIVERGED = "all_lambda_diverged"
#: The sampled range never changed sign, so the root is not bracketed.
REASON_NO_LAMBDA_BRACKET = "no_lambda_bracket"
#: The branch diverged at the interslice ratio finally chosen.
REASON_DIVERGENT_AT_LAMBDA = "divergent_at_lambda"
#: The bracket on lambda was found and then refined, and the secant still
#: did not close it: ``|F_f - F_m|`` is above the requested tolerance at the
#: lambda being handed back.
#:
#: v0.1.180 (D146) — it used to be ``REASON_NOT_CONVERGED``, which is the
#: string Bishop and Janbu give for a completely different loop: their
#: factor-of-safety iteration. Two loops that fail for unrelated reasons
#: cannot be told apart by a caller that groups by reason, and grouping is
#: the whole point of these constants (D56). The message that travels with
#: it names the residual, the width the bracket collapsed to and how many
#: iterations were spent, because those three are what separate the four
#: ways this loop can fail to close — see ``docs/audits/lambda_closure_*``.
#:
#: The name says what is OBSERVED and not why. The ficha that asked for it
#: proposed "g is discontinuous", and this version's own measurement refutes
#: that mechanism: what produced the only known jump was the premature
#: acceptance D145 closed, not a second fixed point. Writing a mechanism
#: into a constant is how ``TestAWedgeWithNoRootSaysSo`` spent two versions
#: asserting true things under a false name.
REASON_LAMBDA_NOT_CLOSED = "lambda_not_closed"
#: The prescribed-inclination force balance found no bracket, so what it
#: has is the sampled F of smallest residual — a fallback, not a solution.
REASON_NO_FORCE_BRACKET = "no_force_bracket"
#: The prescribed-inclination force balance produced no usable factor.
REASON_FORCE_BALANCE_DIVERGED = "force_balance_diverged"
#: The rapid-drawdown procedure does not apply to this surface. Not an
#: engine failure: in a search most candidates are like this.
REASON_DRAWDOWN_NOT_APPLICABLE = "drawdown_not_applicable"
#: The surface could not be sliced at the drawn-down level.
REASON_UNSLICEABLE_AT_DRAWDOWN = "unsliceable_at_drawdown"
#: v0.1.213 (D84) -- the strength envelope depends on the normal stress and
#: the stress it was read at never settled on the stress the method resolved
#: (see :func:`self_consistent_envelope`), so the factor of safety is not the
#: one of that envelope.
REASON_ENVELOPE_NOT_CONVERGED = "envelope_not_converged"

#: Every reason a method may give. A membership test against this set is
#: what keeps the next reason from being born as a loose string.
ALL_REASONS = frozenset({
    REASON_NO_SLICES,
    REASON_NO_SHEAR_STRENGTH,
    REASON_ZERO_DRIVING,
    REASON_ACTIVE_SUPPORT_EXCEEDS_DRIVING,
    REASON_M_ALPHA_COLLAPSED,
    REASON_N_ALPHA_COLLAPSED,
    REASON_NON_PHYSICAL_FOS,
    REASON_NOT_CONVERGED,
    REASON_ALL_LAMBDA_DIVERGED,
    REASON_NO_LAMBDA_BRACKET,
    REASON_DIVERGENT_AT_LAMBDA,
    REASON_LAMBDA_NOT_CLOSED,
    REASON_NO_FORCE_BRACKET,
    REASON_FORCE_BALANCE_DIVERGED,
    REASON_DRAWDOWN_NOT_APPLICABLE,
    REASON_UNSLICEABLE_AT_DRAWDOWN,
    REASON_ENVELOPE_NOT_CONVERGED,
})

# v0.1.192 (D177) — the machine-readable half of ``admissibility_note``,
# which is to that note what ``reason`` is to ``error_message``: the handle
# a program takes instead of parsing prose. A separate set and NOT members
# of ``ALL_REASONS``, because those are reasons a calculation FAILED and a
# screened surface did not fail — its factor converged and is kept; the
# post-analysis checks judge it inadmissible afterwards.
#
# Needed because the raw-data export had to GUESS the code from the note:
# "m_alpha" in it gave -112 and everything else not converged gave -101, so
# a surface rejected by the tensile check went out as a generic failure
# although the note itself said -120.

#: The Tensile Stress Check rejected the surface. The reference's code is
#: -120: "tensile effective normal stress on the base of a slice exceeds the
#: tensile strength of the material".
SCREEN_TENSILE_STRESS = "tensile_stress"
#: The m-alpha check rejected the surface (Whitman & Bailey, 1967). The
#: reference's code is -112.
SCREEN_M_ALPHA = "m_alpha"
#: v0.1.211 (D184) -- the checks themselves raised, so the surface could not
#: be judged, and it is rejected rather than let through. Until now
#: ``BaseSearch._is_admissible`` swallowed the exception and ADMITTED the
#: surface with no note, so a failure of the measurement read as a verdict --
#: the shape of D94. Rejecting can raise the reported minimum if that surface
#: was the lowest, and that is accepted on purpose: the note says why, and a
#: critical surface nobody could screen is not one to publish. The reference
#: gives this no code of its own, so the export writes -101 ("any other
#: rejection"), never -112, even when the exception's text names m_alpha.
SCREEN_ERROR = "screen_error"

#: Every screen ``checks.screen_surface`` may name.
ALL_SCREENS = frozenset({SCREEN_TENSILE_STRESS, SCREEN_M_ALPHA, SCREEN_ERROR})


# ======================================================================
@dataclass
class LEMResult:
    """Result of a single FoS calculation on a specific slip surface."""

    # v0.1.152 (D56) — ``None`` means THERE IS NO FACTOR OF SAFETY, and it
    # is the only way to say so: a non-finite value can no longer be
    # stored here (see __post_init__).
    #
    # It used to be ``float``, and fourteen return paths put ``math.nan``
    # or ``math.inf`` in it. Every one of them also set
    # ``converged=False`` and an ``error_message``, so the failure WAS
    # declared — but the field still carried a non-number, and nothing
    # obliged a reader to consult ``is_valid`` before using it. One that
    # did not (a benchmark script evaluating a published circle) copied a
    # ``nan`` into a results file, from there into a comparison table and
    # from there into a report, unremarked, for seventeen versions.
    #
    # ``None`` is what makes that impossible rather than merely unlikely:
    # arithmetic on it raises where the mistake is made, instead of
    # producing a number that propagates and compares false against
    # everything. The reference does the same thing in its own vocabulary
    # — it writes a code, never a number, when there is no factor.
    fos: Optional[float]
    converged: bool
    iterations: int
    method_id: str
    surface: SurfaceProtocol
    slices: Slices
    error_message: str = ""
    # v0.1.152 (D56) — the machine-readable half of ``error_message``: one
    # of the REASON_* constants above, so a run can report "this reason, N
    # surfaces" without parsing prose. Empty on a result that succeeded.
    reason: str = ""

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
    #   "m_alpha_sign": v0.1.189 (D112) — the sign the m_alpha
    #       denominator was formed with. Published by the five methods the
    #       m-alpha check screens, and deliberately by no other.
    #   "kv": v0.1.191 (D167) — the vertical seismic coefficient the method
    #       APPLIED (0 when the earthquake is disabled), positive DOWNWARD
    #       since v0.1.214 (D170). Published by every method and read by the
    #       admissibility checks; a result without it is read as kv = 0.
    #   "kh": v0.1.214 (D173) — the horizontal one, likewise; read by the
    #       interslice march of ``postprocess.compute_interslice_state``, so
    #       the interpretation applies the loads the method did.
    #   "janbu_b1", "janbu_f0": v0.1.214 (D80) — Janbu Corrected only: the
    #       ``b1`` read off the soil type of the bases and the factor f0.
    #   "sigma_support_load": v0.1.210 (D172) — per slice, the support load
    #       the method added to ``w_total`` for the stress it linearised its
    #       envelope at (Bishop and Janbu: ``support_vertical_load`` of the
    #       last pass; Spencer, GLE and the prescribed-inclination family:
    #       ``-nf_v``); None without a support. The Ordinary Method has none.
    #   "solved_base_normal": v0.1.210 (D172) — per slice, the total base
    #       normal of the method's OWN solution, whose N/l - u the Tensile
    #       Stress Check tests. Published by Spencer, GLE, the family and
    #       the Ordinary Method; Bishop and Janbu publish none because the
    #       check's fallback form IS theirs.
    # Not exhaustive: methods publish diagnostics of their own. These are
    # the keys other modules rely on.
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
    # v0.1.192 (D177) — which post-analysis check rejected the surface: one
    # of ``ALL_SCREENS``, or empty. Set only by the search's admissibility
    # screen; a method that marks its own result inadmissible (the relaxed
    # interslice thrust, active support beyond the driving moment) leaves it
    # empty, because neither is a screen the reference gives a code to.
    admissibility_reason: str = ""
    # v0.1.211 (D200) -- the states the post-analysis checks judge INSTEAD
    # of this result, when no single solve produced it. Today that is the
    # cycling drained cap of a rapid drawdown, whose factor is the centre of
    # a cycle and whose two horns are the passes that were actually solved:
    # ``checks.screen_surface`` admits the centre only if both horns pass.
    # Empty -- the result judges itself -- everywhere else. Not in
    # ``to_dict`` on purpose: each state is a whole result of its own, and
    # what the result IS (factor, verdict, note) is already there.
    screen_states: tuple = field(default=(), repr=False, compare=False)

    # ------------------------------------------------------------------
    def __post_init__(self) -> None:
        """The three things a method is not allowed to hand out (D56).

        All three used to be reachable, and each one has a measured case
        behind it, taken on 0.1.151 over a circle whose sliding mass is
        symmetric about the vertical through its centre — so the driving
        moment cancels to 1.5e-13 against terms of 51, and there is
        genuinely no factor of safety to report:

        * **a non-number**: Bishop, both Janbus and Fellenius answered
          ``inf``; Spencer and GLE answered ``nan``. Both survive a
          ``float()`` and a ``round()``, and ``nan`` compares false
          against every bound it is tested with, so a range check reads
          it as "out of range" and a sort puts it wherever the algorithm
          happens to look first;
        * **no factor and no failure**: a result cannot say "there is no
          number" and "I converged" at once;
        * **a failure with no reason**: on the same surface the three
          prescribed-inclination methods answered ``5.0`` — the TOP OF
          THEIR OWN SAMPLING GRID, returned as the nearest-residual
          fallback — with ``converged=False`` and an empty
          ``error_message``. That is the worst of the three, because 5.0
          looks like a factor of safety and a reader has nothing to tell
          them otherwise.

        Raising is deliberate: these are programming errors inside a
        method, not conditions a slope can be in, and the whole lesson of
        this defect is that the quiet ones cost seventeen versions.
        """
        # Two λ-sampling paths passed ``None`` to a field declared ``str``.
        # Normalised rather than rejected: the value they meant is "no
        # message", and that is what the empty string is for.
        if self.error_message is None:
            self.error_message = ""
        if self.admissibility_note is None:
            self.admissibility_note = ""
        if self.admissibility_reason is None:
            self.admissibility_reason = ""
        if self.screen_states is None:
            self.screen_states = ()
        if self.reason is None:
            self.reason = ""

        if self.fos is not None and not math.isfinite(self.fos):
            raise ValueError(
                f"{self.method_id or 'a method'} returned {self.fos!r} as a "
                "factor of safety. A calculation with no answer is reported "
                "with fos=None and a reason, never with a non-number."
            )
        if self.fos is None and self.converged:
            raise ValueError(
                f"{self.method_id or 'a method'} reported no factor of "
                "safety and converged at the same time."
            )
        if not self.converged and not (self.error_message
                                       or self.admissibility_note):
            raise ValueError(
                f"{self.method_id or 'a method'} failed to converge without "
                "saying why. Every failure carries its reason: that is the "
                "whole of D56."
            )

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
        # v0.1.152 — the ``math.isfinite`` that used to stand here is gone
        # because it can no longer fail: __post_init__ refuses to build a
        # result with a non-finite factor at all.
        return (
            self.converged
            and self.fos is not None
            and self.fos > 0
            and not self.error_message
        )

    def to_dict(self) -> dict:
        """The result as plain data, safe to serialise as JSON.

        v0.1.152 (D56) — ``fos`` comes out as ``None`` (JSON ``null``)
        when there is no factor of safety, never as ``NaN`` or
        ``Infinity``: neither is valid JSON, and Python's own encoder
        emits them anyway unless asked not to, so a file written this way
        parses in Python and nowhere else. ``json.dumps(d, allow_nan=False)``
        on this dict is the check, and the suite runs it.

        ``reason``, ``admissible`` and ``admissibility_note`` are included
        because a factor that is missing without them is exactly the
        unreadable row this defect is about. ``admissibility_reason``
        joined them in v0.1.192 (D177), for the same reason.
        """
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
            "reason": self.reason,
            "admissible": self.admissible,
            "admissibility_note": self.admissibility_note,
            "admissibility_reason": self.admissibility_reason,
        }


# ======================================================================
# v0.1.213 (D84) -- the strength envelope is read at the normal stress the
# method RESOLVES on each slice base, not at the Fellenius estimate.
#
# Every method linearises the envelope once per slice, ``tau ~ c + sigma'
# tan phi``, and then applies that straight line to the stress its own
# equilibrium puts on the base. Until v0.1.213 the line was always the
# tangent at the Fellenius estimate ``max(0, W cos a - u l) / l``. For
# Mohr-Coulomb the point does not matter. For a curved envelope it does, and
# in both directions. A tangent taken anywhere but at the resolved stress
# lies ABOVE a concave curve there, and one taken at a clipped estimate of
# zero, on a curve through the origin, is ZERO. Measured as the strength the
# solver used against the envelope at the stress of its own solution:
#
#     Perry (1993), the given five-slice surface   +2.0 to +2.2 % in the sum
#                                                  (+10 to +11 % on a slice)
#     problem 41, the critical Path Search surface -21 % in the sum
#                                                  (-100 % on four slices)
#
# So the method was not solving limit equilibrium with the material's
# envelope. At the fixed point, where the stress the envelope is read at is
# the stress the method resolves, it is: the tangent there gives the curve's
# own value. That is also how the one other program whose documentation is
# public describes it (the envelope's tangent at the base normal stress of
# each slice, the first iteration being the ordinary one).
#
# The Ordinary Method is not wrapped. Its normal does not depend on c or
# tan phi, so reading the envelope at it is already the fixed point.
#
# A module switch, as ``interslice.BRANCH_STALL_PAIR`` is, so an A/B can
# turn it off and a test can demand that it moves the number (rule 7).
ENVELOPE_AT_OWN_STRESS = True
#: The fixed point stops when no slice's stress moves by more than this,
#: relative to max(1 kPa, |sigma'|). Measured on the 23 surfaces of the
#: verification bank with a curved envelope: 3 to 5 passes.
ENVELOPE_STRESS_TOL = 1e-6
#: And gives up after this many solves, reporting the surface unconverged.
ENVELOPE_MAX_PASSES = 50
#: The two stresses [kPa] at which an envelope is asked whether its tangent
#: depends on the stress at all; the verification bench's census of D172
#: used the same two.
_ENVELOPE_PROBES = (5.0, 500.0)

ENVELOPE_NOT_CONVERGED_NOTE = (
    "The strength envelope depends on the normal stress, and the stress it "
    "was read at did not settle on the stress the method resolved within "
    "the maximum number of passes")


def _envelope_depends_on_stress(slice_, cache: dict) -> bool:
    """Whether the envelope of this slice's material has a tangent that
    changes with sigma'n. Cached per material when the model needs no slice
    context; a model that does is asked on its own slice."""
    mat = getattr(slice_, "material", None)
    if mat is None:
        return False
    strength = getattr(mat, "strength", None)
    per_slice = bool(getattr(strength, "needs_context", False))
    key = id(mat)
    if not per_slice and key in cache:
        return cache[key]
    from .bishop import BishopSimplified
    try:
        _c1, t1 = BishopSimplified._local_c_phi(slice_, mat,
                                                _ENVELOPE_PROBES[0])
        _c2, t2 = BishopSimplified._local_c_phi(slice_, mat,
                                                _ENVELOPE_PROBES[1])
        depends = (math.isfinite(t1) and math.isfinite(t2)
                   and abs(t1 - t2) > 1e-6 * max(1.0, abs(t1), abs(t2)))
    except Exception:  # noqa: BLE001
        # An envelope that cannot be probed keeps the old reading rather
        # than getting a new one on a guess.
        depends = False
    if not per_slice:
        cache[key] = depends
    return depends


def self_consistent_envelope(compute):
    """Wrap a method's ``compute_fos`` so a curved envelope is read at the
    stress the method resolves (v0.1.213, D84; see the note above).

    Solves once. With no slice whose envelope depends on the stress, or no
    factor of safety, that is the answer, bit for bit as before. Otherwise
    it iterates: the effective normal stress of the method's own solution
    (``checks.base_effective_stresses``, which since v0.1.210 is each
    method's own, support included) is imposed as the point every
    stress-dependent slice is linearised at, and the surface is solved
    again, until the stress it was read at and the stress it resolved agree
    to ``ENVELOPE_STRESS_TOL``. Slices whose envelope does not depend on the
    stress keep the Fellenius point, so they are treated exactly as before.

    Published in ``details``: ``envelope_stress`` (the signed stresses the
    returned solve was linearised at, None on a slice that kept the
    Fellenius point), ``envelope_passes`` and ``envelope_converged``. The
    checks read the first to judge the surface where the solver read it.
    """
    import functools

    @functools.wraps(compute)
    def wrapper(self, project, surface, slices):
        res = compute(self, project, surface, slices)
        if (not ENVELOPE_AT_OWN_STRESS or res is None or res.fos is None
                or not res.converged or slices is None):
            return res
        s_list = list(slices.slices if hasattr(slices, "slices") else slices)
        cache: dict = {}
        depends = [_envelope_depends_on_stress(s, cache) for s in s_list]
        if not any(depends):
            return res
        from ..checks import base_effective_stresses

        imposed = None
        passes, settled = 1, False
        try:
            while True:
                own = base_effective_stresses(res)
                if len(own) != len(s_list) or not all(
                        math.isfinite(v) for v, d in zip(own, depends) if d):
                    break
                target = [v if d else None for v, d in zip(own, depends)]
                if imposed is not None and max(
                        abs(t - p) / max(1.0, abs(t))
                        for t, p in zip(target, imposed)
                        if t is not None) < ENVELOPE_STRESS_TOL:
                    settled = True
                    break
                if passes >= ENVELOPE_MAX_PASSES:
                    break
                self._envelope_stress = target
                nxt = compute(self, project, surface, slices)
                passes += 1
                if nxt is None or nxt.fos is None:
                    return nxt
                nxt.details["envelope_stress"] = list(target)
                res, imposed = nxt, target
                if not res.converged:
                    # The method's own iteration failed at this point; its
                    # reason says why, and there is no fixed point to chase.
                    break
        finally:
            self._envelope_stress = None
        res.details["envelope_passes"] = passes
        res.details["envelope_converged"] = settled
        if not settled and res.converged:
            res.converged = False
            res.error_message = ENVELOPE_NOT_CONVERGED_NOTE
            res.reason = REASON_ENVELOPE_NOT_CONVERGED
        return res

    return wrapper


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

    #: v0.1.213 (D84) -- the effective normal stress [kPa] each slice's
    #: envelope is linearised at, imposed by :func:`self_consistent_envelope`
    #: for one solve and put back to None after it; None on a slice keeps
    #: the Fellenius estimate. A class default so every instance, a plugin's
    #: included, has it.
    _envelope_stress: Optional[list] = None

    def _imposed_stress(self, i: int) -> Optional[float]:
        """The stress slice ``i`` is to be linearised at, or None for the
        Fellenius estimate (v0.1.213, D84). Signed: the caller clips it at
        zero, and a negative one is a base in tension at the solution."""
        env = self._envelope_stress
        if env is None or i >= len(env):
            return None
        return env[i]

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

    #: What every iterative method says when it runs out of passes.
    #:
    #: v0.1.152 (D56) — shared for the same reason as the note above: the
    #: five iterative solvers used to answer this condition by saying
    #: nothing at all, each in its own place, and the number they returned
    #: was the last iterate. It names the setting on purpose. "Did not
    #: converge" is a fact about the surface; "within the maximum number of
    #: iterations" is the half that tells the user there is something they
    #: can do about it.
    NOT_CONVERGED_NOTE: ClassVar[str] = (
        "The factor of safety iteration did not converge within the "
        "maximum number of iterations"
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
            reason=REASON_NO_SHEAR_STRENGTH,
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

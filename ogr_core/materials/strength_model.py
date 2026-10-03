# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Abstract constitutive-model (strength) interface.

Every failure criterion in OGR Slip2D is implemented as a subclass of
:class:`StrengthModel`. Adding a new criterion = creating a new subclass
in its own file and registering it with the global ``REGISTRY``. The
core solver and GUI discover it automatically.

Design pattern: Strategy + Plugin Registry.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar, Optional


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class MaterialFactors:
    """The divisors a design standard applies to a strength, by category.

    v0.1.225 (D224) — the four categories of material partial factor of
    the reference documentation's design-standard dialog ("Effective
    cohesion c'", "Effective friction tan(phi)", "Undrained strength cu"
    and "Shear strength (other models)"), each already multiplied by the
    resistance factor, which divides the whole resisting side (Frank et al.
    2004, §11.5: the over-design factor is F/(γG·γR;e)). Every model says
    which category its parameters belong to in
    :meth:`StrengthModel.design_factored`; there is no list of names.
    """

    cohesion: float = 1.0     # c′            (γc′·γR;e)
    tan_phi: float = 1.0      # tan φ′        (γφ′·γR;e)
    undrained: float = 1.0    # cu            (γcu·γR;e)
    shear: float = 1.0        # τ, other models (γτ·γR;e)


@dataclass
class FactoredStrength:
    """What :meth:`StrengthModel.design_factored` returns: the factored
    model (a NEW object; the original is never touched), what changed
    (``{name: (before, after)}``), the category or categories applied, and
    a note when something could not be factored."""

    model: "StrengthModel"
    changes: dict = field(default_factory=dict)
    category: str = ""
    note: Optional[str] = None


def tan_factored_angle(phi_deg: float, factor: float) -> float:
    """An angle whose TANGENT is divided by ``factor``, in degrees.

    Eurocode 7 factors tan φ′, not φ′ (EN 1997-1, Annex A): dividing 30° by
    1.25 gives 24.0°, dividing tan 30° by 1.25 gives 24.79°. Clamped to
    ±89.9° so a vertical input stays finite.
    """
    if factor <= 0:
        return phi_deg
    phi = max(-89.9, min(89.9, float(phi_deg)))
    return math.degrees(math.atan(math.tan(math.radians(phi)) / factor))


class StrengthModel(ABC):
    """Base class for all shear-strength constitutive laws.

    Subclasses must declare:
        - ``MODEL_ID``: unique string identifier for serialization
        - ``DISPLAY_NAME``: human-readable name (translatable)
        - ``PARAMETERS``: dict of {name: (default, unit, description)}

    and implement ``shear_strength(sigma_n_eff)``.
    """

    MODEL_ID: ClassVar[str] = ""
    DISPLAY_NAME: ClassVar[str] = ""
    PARAMETERS: ClassVar[dict[str, tuple[float, str, str]]] = {}

    def __init__(self, **params: float) -> None:
        # Populate with defaults, then override with user-supplied values
        self.params: dict[str, float] = {
            name: default for name, (default, _, _) in self.PARAMETERS.items()
        }
        for key, value in params.items():
            if key not in self.PARAMETERS:
                raise ValueError(
                    f"{self.MODEL_ID}: unknown parameter '{key}'. "
                    f"Valid: {list(self.PARAMETERS)}"
                )
            self.params[key] = float(value)

    # ------------------------------------------------------------------
    @abstractmethod
    def shear_strength(self, sigma_n_eff: float) -> float:
        """Return shear strength τ for a given effective normal stress σ'n.

        Args:
            sigma_n_eff: effective normal stress on the slip surface [kPa].

        Returns:
            Shear strength [kPa].
        """

    # ------------------------------------------------------------------
    def shear_strength_ctx(
        self, sigma_n_eff: float, ctx: "SliceContext | None" = None,
    ) -> float:
        """Context-aware shear strength.

        v0.1.15 — most models depend only on σ'ₙ and ignore ``ctx``.
        Anisotropic and stress-history models (SHANSEP, Anisotropic
        Linear, Generalized Anisotropic, Barton-Bandis with depth, …)
        override this to use the slice base angle, vertical effective
        stress, depth, etc., provided in the SliceContext.

        The default implementation simply delegates to
        :meth:`shear_strength`, so existing models work unchanged.
        """
        return self.shear_strength(sigma_n_eff)

    @property
    def needs_context(self) -> bool:
        """True if this model's strength depends on more than σ'ₙ
        (e.g. base angle or vertical stress). The solver uses this to
        decide whether to call shear_strength_ctx with a populated
        SliceContext. Default False."""
        return False

    # ------------------------------------------------------------------
    def tensile_strength(self) -> float:
        """Tensile strength of the material, as a POSITIVE magnitude [kPa].

        v0.1.191 (D165) — zero unless the model's criterion defines a
        finite tensile strength. It is the tension the Tensile Stress Check
        allows on a slice base (``ogr_slip2d.checks``), and zero is also
        that check's answer for every criterion without one, so a model
        written later inherits the conservative answer instead of having to
        be remembered in a list: a hand-typed list of capable models is
        what went stale in D165.

        Override it only with a criterion's own tensile strength, computed
        from this instance's ``params`` — the dictionary ``shear_strength``
        reads, so the names cannot drift apart from the envelope's.
        """
        return 0.0

    # v0.1.120 — two SliceContext fields cost real work to fill in, so the
    # slicer only fills them when some material asks for them. They are
    # CLASS attributes rather than properties because the slicer asks the
    # question once per analysis, of every material in the project, before
    # there is any slice to ask about.
    NEEDS_LAYER_TOP: ClassVar[bool] = False
    """Model reads ``SliceContext.layer_top_y`` — the top of the material
    band the slice base sits in."""

    NEEDS_SLOPE_DISTANCE: ClassVar[bool] = False
    """Model reads ``SliceContext.slope_distance`` — the true distance
    from the slice base to the nearest point of the ground profile. The
    more expensive of the two: a point-to-polyline distance per slice,
    paid on every trial surface of a search."""

    # ------------------------------------------------------------------
    def design_factored(self, factors: MaterialFactors) -> FactoredStrength:
        """This strength with a design standard's partial factors applied.

        v0.1.225 (D224) — every built-in model overrides it and says which
        category of :class:`MaterialFactors` its parameters are. A model
        that does not (a plugin written later) is returned UNCHANGED, with
        a note that says so: until this version the factors were applied to
        parameters picked by NAME, and every model whose names did not match
        was left unfactored without a word.
        """
        return FactoredStrength(
            self, {}, "",
            note=(f"{self.DISPLAY_NAME or self.MODEL_ID}: this strength model "
                  f"declares no partial factor, so it was NOT factored."))

    def _with_params(self, **new) -> "StrengthModel":
        """A copy of this model with some parameters replaced; any state it
        carries beside ``params`` (tables, rules, switches) is copied too."""
        import copy
        out = copy.deepcopy(self)
        out.params.update({k: float(v) for k, v in new.items()})
        return out

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {"model_id": self.MODEL_ID, "params": dict(self.params)}

    @classmethod
    def from_dict(cls, data: dict) -> "StrengthModel":
        from .registry import REGISTRY

        model_cls = REGISTRY.get(data["model_id"])
        # v0.1.60 — Models whose state does not fit in the numeric
        # PARAMETERS dict (the table-based ones, and the per-angle rules of
        # Generalized Anisotropic) store it at the TOP level of the dict and
        # override ``from_dict`` to read it back. Rebuilding them with
        # ``model_cls(**params)`` silently dropped that state, so saving and
        # reopening a project replaced the user's τ–σ'n table with the
        # built-in demo table. Dispatch to the subclass when it defines its
        # own ``from_dict``; ``__dict__`` is used deliberately, since an
        # inherited one would recurse straight back into here.
        #
        # v0.1.120 — the walk goes up the MRO, stopping BEFORE this class.
        # Asking only ``model_cls.__dict__`` answered "no" for a model that
        # inherits its ``from_dict`` from an intermediate base, and the
        # fallback below would then have dropped exactly the state the
        # override exists to carry. Stopping at ``StrengthModel`` keeps the
        # original reason for not using plain attribute lookup: an
        # inherited one from HERE would recurse straight back in.
        own = None
        for klass in model_cls.__mro__:
            if klass is StrengthModel:
                break
            if "from_dict" in klass.__dict__:
                own = klass.__dict__["from_dict"]
                break
        if own is not None:
            return own.__func__(model_cls, data)
        return model_cls(**data.get("params", {}))

    def __repr__(self) -> str:
        kv = ", ".join(f"{k}={v:g}" for k, v in self.params.items())
        return f"{self.__class__.__name__}({kv})"


# ----------------------------------------------------------------------
from dataclasses import dataclass as _dataclass


@_dataclass
class SliceContext:
    """Per-slice context passed to ``shear_strength_ctx`` for models
    whose strength depends on more than the effective normal stress.

    v0.1.15. All fields optional; populated by the LEM solver.

    Attributes:
        base_angle_rad: inclination of the slice base from horizontal
            (α). Used by anisotropic models (the angle between the slip
            direction and the bedding orientation).
        sigma_v_eff: vertical effective stress at the base centre [kPa]:
            overburden, PLUS any water standing on the ground (v0.1.214,
            D166), minus pore pressure; no seismic coefficient; clipped at
            zero by the solver that fills it. Read by SHANSEP and, since
            v0.1.218 (D207), by Vertical Stress Ratio, which until then used
            σ'ₙ in its place.
        depth: vertical depth below the ground surface at the slice
            base [m]. Used by Barton-Bandis (JCS scaling) and others.
        pore_pressure: pore water pressure at the base [kPa].
        y_base: elevation of the slice base [m].
        layer_top_y: elevation of the TOP of the material band the slice
            base sits in [m], v0.1.120. Not the ground surface: with three
            clay layers stacked under an embankment, each slice sees the
            top of its own layer. ``None`` means nobody filled it in — a
            model that needs it must fall back rather than invent a depth.
        slope_distance: true distance from the slice base centre to the
            nearest point of the ground profile [m], v0.1.120. Differs
            from ``depth`` under a slope face, where the nearest point is
            not the one straight above. ``None`` as above.
        x_base: abscissa of the middle of the slice base [m], v0.1.246
            (D229), for the Discrete Function, whose strength is a field
            over (x, y). ``None`` means nobody filled it in, and a model
            that needs it must say what it does instead.
        bedding_angle_deg: LOCAL orientation of the bedding at this
            slice's base [deg from horizontal], v0.1.126. Filled in only
            when the material names an anisotropic surface; ``None``
            means it does not, and the anisotropic models then fall back
            on the single global angle they carry themselves. The
            distinction matters: 0.0 would be a horizontal bedding, which
            is a real answer and not the absence of one.
    """
    base_angle_rad: float = 0.0
    sigma_v_eff: float = 0.0
    depth: float = 0.0
    pore_pressure: float = 0.0
    y_base: float = 0.0
    layer_top_y: "float | None" = None
    slope_distance: "float | None" = None
    bedding_angle_deg: "float | None" = None
    x_base: "float | None" = None

    @classmethod
    def from_slice(cls, slice_, sigma_n_eff: float,
                   sigma_v_probe: "float | None" = None) -> "SliceContext":
        """The context of the base of ``slice_``, as the solvers read it.

        v0.1.230 (D219) -- moved here, bit for bit, from
        ``ogr_slip2d.methods.bishop.BishopSimplified._local_c_phi``, where
        every method built it: Janbu's soil type reads the anisotropic
        models on each base, with the context of that base, and must read
        exactly what the solver reads. ``sigma_n_eff`` is the vertical
        stress's fallback when the slice cannot give one (a stand-in with
        no weight), and ``sigma_v_probe`` replaces it (v0.1.218, D207: the
        question "is there strength at SOME stress" of ``_zero_strength``).
        Every field is read with ``getattr`` because
        ``ogr_core.support.bond`` hands in a stand-in, not a ``Slice``.
        """
        sn = sigma_n_eff
        # vertical effective stress at the base ≈ (W + W_w)/b − u (per
        # unit width). Use slice attributes when available.
        #
        # v0.1.214 (D166) -- ``+ water_weight``, the ponded water
        # standing on the slice, which the slicer keeps out of
        # ``weight`` so the seismic coefficients cannot reach it. The
        # pore pressure at the base carries the head of that water, so
        # without its weight the estimate fell by ``γ_w·d`` under a
        # reservoir and was clipped to zero -- and SHANSEP, the model
        # that reads it, then fell back to ``su(σ'_n)`` in silence. With
        # it, a submerged column gives ``γ'·h`` whatever the depth of the
        # water: Terzaghi's principle, and the sum the reference
        # documentation writes for its own excess-pore-pressure example.
        # NO seismic coefficient here: this is the consolidation stress
        # a strength model reads, not a load the earthquake applies.
        # By ``getattr`` because ``ogr_core.support.bond`` hands in a
        # stand-in with no water field.
        try:
            b = max(slice_.width, 1e-9)
            sigma_v_total = (slice_.weight
                             + getattr(slice_, "water_weight", 0.0)) / b
            u = getattr(slice_, "pore_pressure", 0.0)
            sigma_v_eff = max(sigma_v_total - u, 0.0)
        except Exception:  # noqa: BLE001
            sigma_v_eff = sn
        if sigma_v_probe is not None:
            sigma_v_eff = max(float(sigma_v_probe), 0.0)
        depth = 0.0
        try:
            depth = 0.5 * (slice_.top_y_left + slice_.top_y_right) \
                - 0.5 * (slice_.base_y_left + slice_.base_y_right)
        except Exception:  # noqa: BLE001
            pass
        return cls(
            base_angle_rad=getattr(slice_, "base_angle", 0.0),
            sigma_v_eff=sigma_v_eff,
            depth=max(depth, 0.0),
            pore_pressure=getattr(slice_, "pore_pressure", 0.0),
            y_base=0.5 * (getattr(slice_, "base_y_left", 0.0)
                          + getattr(slice_, "base_y_right", 0.0)),
            # v0.1.120 — measured by the slicer, which is the only
            # thing that knows the layer contacts and the ground
            # profile. Passed through unchanged, None included: a
            # model that needs one and is handed None must fall back,
            # not read a depth off the other field.
            layer_top_y=getattr(slice_, "layer_top_y", None),
            slope_distance=getattr(slice_, "slope_distance", None),
            # v0.1.126 — the local bedding orientation, for the
            # anisotropic models. None when the material names no
            # anisotropic surface, and they then use the single global
            # angle they carry, exactly as before this existed.
            bedding_angle_deg=getattr(slice_, "bedding_angle_deg", None),
            # v0.1.246 (D229) — where the base is, for the models whose
            # strength is a field over the material.
            x_base=getattr(slice_, "x_centre", None),
        )

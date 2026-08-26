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

from abc import ABC, abstractmethod
from typing import ClassVar


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
        sigma_v_eff: vertical effective stress at the base centre [kPa]
            (overburden minus pore pressure). Used by SHANSEP and
            Vertical-Stress-Ratio models.
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

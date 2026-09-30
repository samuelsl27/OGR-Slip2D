# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Design standard partial factors — phase M6.

v0.1.52 made the partial factors *configurable*; this module makes them
*apply*. A setting that changes nothing is worse than no setting at all,
because the user believes the analysis honours it.

**The factors are applied by transforming a COPY of the project, not by
altering the solver.** That choice matters:

* every analysis path — deterministic, probabilistic, transient,
  optimisation — gets the factored values automatically, because they all
  read the same project;
* the solver stays a pure limit-equilibrium engine with no notion of any
  design code, so a new standard is a table of numbers rather than a
  change to the mathematics;
* the original project is never modified, so switching the standard off
  restores the unfactored results exactly.

**Convention.** Material factors *divide* (they reduce strength) and
action factors *multiply* (they increase load), following Eurocode 7,
where a partial factor is always applied so as to be unfavourable. The
friction angle is factored on **tan φ**, not on φ itself — that is what
the code specifies, and the difference is not negligible: dividing 30° by
1.25 gives 24.0°, whereas dividing tan 30° by 1.25 gives 24.79°.

**v0.1.225 (D224) — the material factors by CATEGORY, not by name.** Until
this version a parameter was factored when its NAME was on a list
(``cohesion``, ``friction_angle`` and five more). Everything else was left
as it was without a word: Anisotropic Linear, the anisotropic function's
rows, Generalized Anisotropic's rules, the τ–σ'ₙ tables, SHANSEP, Vertical
Stress Ratio, Hoek-Brown, Barton-Bandis, the unsaturated angle φb and the
rapid-drawdown envelopes; the undrained-with-depth models were factored in
part (``cohesion_top`` and not the rate, so cu(z) = c_top/γ + Δc·z) or not
at all (``cohesion_datum``); the power curve had only its ``c`` divided;
the undrained strength took the COHESION factor; and ``factor_resistance``
was applied nowhere. Now:

* the four categories of material factor of the reference documentation's
  design-standard dialog — effective cohesion c', effective friction
  tan φ', undrained strength cu, and "Shear strength (other models)" —
  and each strength model says in
  :meth:`~ogr_core.materials.strength_model.StrengthModel.design_factored`
  which one its parameters belong to (a model that says nothing is left
  alone WITH a note);
* the resistance factor γR;e divides the four, which is dividing the whole
  resisting side of the factor of safety: Frank et al. (2004, §11.5) write
  the over-design factor as F/(γG·γR;e);
* the suction term goes with tan φ' (it grows with tan φb) and the two
  rapid-drawdown envelopes with c' and tan φ' (intercept and slope).

With the four factors equal to γ and γR;e = 1, every model's strength is
divided by γ at every σ'ₙ, so F_design = F/γ in every method: the strength
reduction the limit-equilibrium factor of safety is defined by. The
reference's own Eurocode 7 tutorial reports F = 1.37 and, with DA1-C2,
1.096 = 1.37/1.25.

References:
    EN 1997-1:2004, Eurocode 7: Geotechnical design — Part 1, Annex A.
    Frank, R., Bauduin, C., Driscoll, R., Kavvadas, M., Krebs Ovesen, N.,
        Orr, T. & Schuppener, B. (2004). Designers' Guide to EN 1997-1.
        Thomas Telford, §11.5.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ogr_core.materials.strength_model import (MaterialFactors,
                                               tan_factored_angle)


@dataclass
class FactorReport:
    """What was factored, so the user can check it."""

    standard: str = "none"
    applied: bool = False
    materials: list = field(default_factory=list)
    loads: int = 0
    notes: list = field(default_factory=list)

    def summary(self) -> str:
        if not self.applied:
            return "no partial factors applied"
        return (f"{self.standard}: {len(self.materials)} material(s) and "
                f"{self.loads} load(s) factored")


def factor_friction_angle(phi_deg: float, factor: float) -> float:
    """Reduce a friction angle through **tan φ**.

    Eurocode 7 factors the tangent, not the angle. Dividing 30° by 1.25
    gives 24.00°; dividing tan 30° by 1.25 gives 24.79°, so getting this
    wrong is conservative by roughly 0.8° — small, but wrong in a way
    that would quietly disagree with a hand check.

    v0.1.225 — the rule lives in ``ogr_core.materials.strength_model``,
    where the strength models that apply it can reach it.
    """
    return tan_factored_angle(phi_deg, factor)


def material_factors(ds) -> MaterialFactors:
    """The four divisors of a design standard's settings, each times the
    resistance factor γR;e (which divides the whole resisting side)."""
    def _f(name):
        return float(getattr(ds, name, 1.0) or 1.0)

    r = _f("factor_resistance")
    return MaterialFactors(cohesion=_f("factor_cohesion") * r,
                           tan_phi=_f("factor_friction") * r,
                           undrained=_f("factor_undrained") * r,
                           shear=_f("factor_shear_strength") * r)


def _factor_envelope(env, mf: MaterialFactors):
    """A rapid-drawdown envelope with its intercept divided by the c'
    factor and the tangent of its slope by the tan φ' one, or None when
    nothing changes."""
    from ogr_core.materials.drawdown_envelopes import Kc1Envelope, REnvelope

    if mf.cohesion == 1.0 and mf.tan_phi == 1.0:
        return None
    if isinstance(env, REnvelope):
        return REnvelope(c_r=env.c_r / mf.cohesion,
                         phi_r_deg=tan_factored_angle(env.phi_r_deg,
                                                      mf.tan_phi))
    if isinstance(env, Kc1Envelope):
        return Kc1Envelope(d=env.d / mf.cohesion,
                           psi_deg=tan_factored_angle(env.psi_deg,
                                                      mf.tan_phi))
    return None


def apply_design_factors(project, settings=None):
    """Return a factored **copy** of ``project``, plus a report.

    When the design standard is disabled the original project is returned
    untouched, so the feature costs nothing when unused and cannot
    perturb a result by being merely present.
    """
    ds = settings if settings is not None else \
        getattr(getattr(project, "settings", None), "design_standard",
                None)
    rep = FactorReport()
    if ds is None or not getattr(ds, "enabled", False):
        return project, rep

    rep.standard = getattr(ds, "standard", "custom")
    from ogr_core.project import Project
    factored = Project.from_dict(project.to_dict())

    mf = material_factors(ds)
    f_gamma = float(getattr(ds, "factor_unit_weight", 1.0) or 1.0)
    f_perm = float(getattr(ds, "factor_permanent", 1.0) or 1.0)
    f_var = float(getattr(ds, "factor_variable", 1.0) or 1.0)

    for mat in factored.materials:
        changed = {}
        category = ""
        strength = getattr(mat, "strength", None)
        if strength is not None:
            done = strength.design_factored(mf)
            mat.strength = done.model
            changed.update(done.changes)
            category = done.category
            if done.note:
                rep.notes.append(f"Material {mat.name!r}: {done.note}.")
        phi_b = float(getattr(mat, "phi_b", 0.0) or 0.0)
        if phi_b and mf.tan_phi != 1.0:
            mat.phi_b = tan_factored_angle(phi_b, mf.tan_phi)
            changed["phi_b"] = (phi_b, mat.phi_b)
        env = getattr(mat, "drawdown_envelope", None)
        if env is not None:
            new_env = _factor_envelope(env, mf)
            if new_env is not None:
                mat.drawdown_envelope = new_env
                changed["drawdown_envelope"] = (env, new_env)
        if f_gamma != 1.0:
            for attr in ("unit_weight", "sat_unit_weight"):
                value = getattr(mat, attr, None)
                if isinstance(value, (int, float)) and value:
                    # Unit weight MULTIPLIES: a heavier soil is the
                    # unfavourable direction for a driving weight.
                    setattr(mat, attr, value * f_gamma)
                    changed[attr] = (value, value * f_gamma)
        if changed:
            rep.materials.append({"name": mat.name, "changes": changed,
                                  "category": category})

    if f_perm != 1.0 or f_var != 1.0:
        for group, factor in ((getattr(factored, "distributed_loads", []),
                               f_var),
                              (getattr(factored, "line_loads", []),
                               f_var)):
            for load in group:
                for attr in ("magnitude", "magnitude_1", "magnitude_2"):
                    value = getattr(load, attr, None)
                    if isinstance(value, (int, float)) and value:
                        setattr(load, attr, value * factor)
                        rep.loads += 1

    # v0.1.225 — what the standard asks for and this version does not do
    # yet is SAID, not left for the user to find (D226).
    if f_perm != 1.0:
        rep.notes.append(
            f"The permanent-action factor ({f_perm:g}) is not applied: the "
            f"weight of the soil and the permanent loads carry no action "
            f"factor in this version, and every load takes the variable one "
            f"({f_var:g}).")

    factors = (mf.cohesion, mf.tan_phi, mf.undrained, mf.shear, f_gamma,
               f_perm, f_var)
    if all(f == 1.0 for f in factors):
        rep.notes.append(
            "The standard is enabled but every factor is 1.0, so nothing "
            "changed.")
    rep.applied = True
    return factored, rep

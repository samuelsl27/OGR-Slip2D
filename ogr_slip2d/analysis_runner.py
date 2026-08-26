# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
The one place an analysis is configured from a project.

v0.1.77. Everything here used to live inside ``_ComputeWorker`` in
``ogr_gui/main_window.py``, which meant it lived inside a ``QThread`` —
so the only way to run a project *as the user configured it* was through
the graphical interface. ``ogr_cli.compute`` therefore read nothing from
``project.settings`` at all: it deserialised the geometry and the
materials and built its own search from command-line defaults.

That failed silently and on the unsafe side in three separate ways:

- **rapid drawdown** was never applied, so a terminal run of a drawdown
  project reported the ordinary factor of safety (noted as pending in the
  changelogs of v0.1.72, v0.1.74 and v0.1.75);
- **design-standard partial factors** were never applied, so the analysis
  used unfactored c', φ' and γ;
- a **finite-element seepage field** is not serialised into the ``.ogr``,
  and the pore-pressure lookup falls back to ``u = 0``, so the run
  reported a dry slope.

Plus everything that merely gave a *different* answer: four of the six
search strategies unreachable, the convergence settings, the seed, the
admissibility checks, and the number of slices.

The design rule this module exists to enforce is the one
``rapid_drawdown.wrap_for_drawdown`` already stated about itself: a
method must be instantiated in exactly ONE place, because a second place
that forgets a wrapper reports a different number without saying so. This
module is that place; the GUI worker and the CLI are both callers.

No Qt anywhere in this file — that is what makes it shareable.
"""
from __future__ import annotations

import math
from typing import Callable, Optional

from ogr_core.geometry import BoundaryType

from .methods import method_registry
from .methods.gle import interslice_function
from .rapid_drawdown import check_drawdown_settings, wrap_for_drawdown

__all__ = [
    "AnalysisOutcome",
    "build_method",
    "build_search",
    "check_analysis_settings",
    "daylight_tangent_note",
    "grid_edge_note",
    "run_analysis",
    "settings_warnings",
]

# Methods that take an interslice force function and a λ bracket. Keyed
# by METHOD_ID rather than by class so the mapping survives a rename, and
# so the registry stays the single list of what exists.
_LAMBDA_METHODS = ("spencer", "gle_morgenstern_price")
_INTERSLICE_METHODS = ("gle_morgenstern_price",)

# v0.1.98 — the methods that PRESCRIBE the inter-slice inclination, and so
# are the only ones for which "is Z the effective or the total inter-slice
# force?" is a question at all. Spencer and GLE solve for the inclination
# and are insensitive to the split; Bishop and Janbu assume it horizontal.
_PRESCRIBED_THETA_METHODS = (
    "lowe_karafiath", "corps_engineers_1", "corps_engineers_2")

# Searches that enumerate rather than draw at random. Seeding them would
# mean handing an argument they can only ignore.
_DETERMINISTIC_SEARCHES = ("grid", "auto_refine")


class AnalysisOutcome:
    """What one call to :func:`run_analysis` produced.

    ``results`` maps method id to :class:`~ogr_slip2d.search.SearchResult`.
    ``factor_report`` is the design-standard report (empty when the
    standard is disabled). ``warnings`` collects anything the run decided
    to carry on through — an unknown method id, mostly. It exists because
    the code this replaced answered an unknown id with a bare
    ``continue``, and the method simply vanished from the results with no
    trace at all.
    """

    __slots__ = ("results", "factor_report", "warnings", "project")

    def __init__(self, results, factor_report, warnings, project) -> None:
        self.results = results
        self.factor_report = factor_report
        self.warnings = warnings
        #: The FACTORED copy actually analysed — never the caller's
        #: project, which must come out of an analysis untouched.
        self.project = project

    def __iter__(self):
        """So ``results, report = run_analysis(...)`` keeps working."""
        return iter((self.results, self.factor_report))


# ======================================================================
def check_analysis_settings(project) -> list[str]:
    """Every reason ``project`` cannot be analysed as configured.

    Empty list when it can. Refusing beats returning a plausible number
    computed from settings that were quietly dropped — that is the whole
    argument of ``check_drawdown_settings``, generalised.
    """
    problems: list[str] = []

    why = check_drawdown_settings(project)
    if why:
        problems.append(why)

    # v0.1.77 — ``pore_pressure`` answers 0.0 when the finite-element
    # field is missing, so computing without one reports a dry slope in
    # silence. The guard turns that into a refusal.
    #
    # v0.1.78 — the field is now written to the .ogr, so the common cause
    # is gone: reopening a solved project no longer loses it. The guard
    # stays because the remaining causes are real — a project saved by an
    # older version, a mesh regenerated since (which clears the field,
    # main_window.py), or a model where the groundwater analysis was
    # simply never run. Only the wording changed: it used to blame the
    # file format, which is no longer true.
    problems.extend(_shadow_setting_problems(project))

    from ogr_core.materials import PorePressureType
    uses_fem = [m.name for m in project.materials
                if getattr(m, "pore_pressure", None) == PorePressureType.FEM_SEEPAGE]
    field = getattr(project, "seepage_result", None)
    if uses_fem and (field is None or not field.pore_pressure):
        problems.append(
            "These materials take their pore pressure from a "
            "finite-element seepage field, and this project has no "
            f"computed field: {', '.join(uses_fem)}. Run the groundwater "
            "analysis first — computing now would report u = 0 "
            "everywhere, which looks like a dry slope.")

    return problems


def _shadow_setting_problems(project) -> list[str]:
    """Refuse to run on a settings object carrying a retired field name.

    Until v0.1.103 six settings existed twice — the name the interface
    showed and the name the engine read — and assigning the second one is
    what a script did when it thought it was configuring the search. The
    names are gone, but a dataclass takes any attribute you hand it
    without a word, so ``s.path_num_paths = 300`` would still look like a
    setting and still reach nothing. Refusing is the only answer that
    cannot be mistaken for having worked.
    """
    from ogr_core.project.settings import _SHADOW_FIELDS

    s_search = project.settings.search
    out = []
    for name in _SHADOW_FIELDS:
        if name not in vars(s_search):
            continue
        _old_default, survivor = _SHADOW_FIELDS[name]
        value = getattr(s_search, name)
        if survivor is None:
            out.append(
                f"This project sets {name} = {value}. That setting was "
                f"removed in v0.1.103: no analysis ever read it, and it "
                f"has no replacement.")
        else:
            out.append(
                f"This project sets {name} = {value}. That name was "
                f"removed in v0.1.103 because the interface never showed "
                f"it; set {survivor} instead. Computing now would ignore "
                f"the value and report a plausible number.")
    return out


def settings_warnings(project, method_ids=()) -> list[str]:
    """Settings this project sets that the chosen analysis cannot honour.

    Not a refusal: the analysis is valid, it just does less than the
    Project Settings pages suggest, or it rests on a declaration the
    geometry disagrees with. Saying so is the minimum rule 7 asks when a
    control cannot be honoured.
    """
    notes: list[str] = []
    # v0.1.121 — facts about the weak layers of the model. Asked once, here,
    # because they cannot change while the model is analysed and a per-surface
    # version of the same sentence would arrive thousands of times.
    from .weak_layers import weak_layer_model_warnings
    notes.extend(weak_layer_model_warnings(project))
    # v0.1.122 — and the same for the equivalent-fluid retaining walls,
    # for the same reason and asked the same way: once per analysis.
    from .retaining_wall_notes import retaining_wall_notes
    notes.extend(retaining_wall_notes(project, method_ids))
    # v0.1.123 — the Ito-Matsui pile row, and the *location of force*
    # setting, which two types now offer and which therefore stopped
    # belonging to either of them.
    from .ito_matsui_notes import ito_matsui_notes
    from .support_notes import force_location_notes
    notes.extend(ito_matsui_notes(project, method_ids))
    notes.extend(force_location_notes(project, method_ids))
    s_search = project.settings.search
    if (s_search.search_method == "slope"
            and s_search.slope_limit_left is not None
            and s_search.slope_limit_right is not None):
        notes.append(
            "Slope Search derives its entry and exit window from the "
            "ground profile, so the Slope Limits you set did not steer "
            "where it looked. They were still applied as a filter, as "
            "they are for every search.")
    # Anything the stored model carried that could not be migrated. It is
    # a note and not a refusal: the analysis is valid, it simply did not
    # honour a value the file still mentions.
    #
    # Not a field of the dataclass, so it does not survive a project that
    # is rebuilt from its own dictionary — which happens only when design
    # factors are enabled, and costs the note, never the result.
    notes.extend(getattr(s_search, "_migration_notes", []) or [])
    notes.extend(_failure_direction_note(project))
    notes.extend(_optimize_notes(s_search))
    notes.extend(_undrained_profile_notes(project))
    return notes


def _undrained_profile_notes(project) -> list[str]:
    """Materials whose undrained profile reaches zero inside the model.

    An undrained strength that varies linearly with depth is a straight
    line, and a straight line crosses zero. Where it does, the material
    has NO shear strength: the solver floors the local cohesion at zero
    (``BishopSimplified._local_c_phi``), so nothing negative ever reaches
    the equilibrium, but a search that looks above that elevation finds
    surfaces with a factor of zero and reports one as the minimum.

    That is what the law says, not a defect. It is worth a note because
    the elevation where it happens is not visible in the three numbers the
    material dialog shows, and because the Cutoff cannot prevent it: with
    a rising profile the Cutoff is a maximum.

    Measured on verification problem 29 (Duncan 2000), whose published
    profile — 100 psf at elevation −20 ft, +9.8 psf/ft — reaches zero at
    −9.8 while the model runs up to +22.
    """
    extents = _material_y_extents(project)
    if not extents:
        return []
    notes: list[str] = []
    for mat in project.materials:
        span = extents.get(mat.id)
        if span is None:
            continue
        y_min, y_max = span
        st = getattr(mat, "strength", None)
        rate = (getattr(st, "params", None) or {}).get("cohesion_change")
        c_ref = getattr(st, "_C_REF", None)
        if rate is None or c_ref is None or rate == 0.0:
            continue
        c0 = st.params.get(c_ref, 0.0)
        # A cutoff only helps on the side the line falls towards, and only
        # when it is enabled and non-negative.
        if (getattr(st, "cutoff_enabled", False) and rate < 0.0
                and st.params.get("cutoff", 0.0) >= 0.0):
            continue
        d0 = -c0 / rate            # depth at which the line reaches zero
        if st.MODEL_ID == "undrained_depth_datum":
            y0 = st.params.get("datum", 0.0) - d0
            # rate > 0: the line falls going UP, so the dead zone is above
            # y0; rate < 0: it falls going DOWN, and the zone is below.
            reaches = y0 < y_max if rate > 0.0 else y0 > y_min
            where = ("above" if rate > 0.0 else "below")
            if reaches:
                notes.append(
                    f"Material '{mat.name}': its undrained profile reaches "
                    f"zero at elevation {y0:.4g}, and the material extends "
                    f"{where} that ({y_min:.4g} to {y_max:.4g}). The soil "
                    f"{where} it has no shear strength at all, so any "
                    f"surface that goes there has a factor of safety of "
                    f"zero. The Cutoff cannot bound this side of the line.")
        elif 0.0 < d0 < (y_max - y_min):
            # Layer-top and distance-to-slope measure a depth that cannot
            # be negative, so only a FALLING profile can reach zero.
            notes.append(
                f"Material '{mat.name}': its undrained profile reaches "
                f"zero {d0:.4g} below its reference, and the material is "
                f"{y_max - y_min:.4g} deep. Below that it has no shear "
                f"strength and any surface reaching it has a factor of "
                f"safety of zero.")
    return notes


def _material_y_extents(project) -> dict:
    """{material id: (y_min, y_max)} from the planar subdivision.

    The MODEL's own range would be the easy answer and it is the wrong
    one: on verification problem 84 the foundation's steepest profile
    reaches zero exactly at the crest of the EMBANKMENT, twenty feet above
    any soil the profile describes. Asking where the material actually is
    keeps the note about soil that exists.

    Falls back to the external boundary for a project whose regions cannot
    be resolved, which is the state a half-built model is in.
    """
    try:
        regions = project.resolve_regions()
    except Exception:                                        # noqa: BLE001
        regions = []
    out: dict = {}
    for region in regions or []:
        mid = getattr(region, "material_id", None)
        ys = [v.y for v in region.polygon.vertices]
        if mid is None or not ys:
            continue
        lo, hi = min(ys), max(ys)
        if mid in out:
            out[mid] = (min(out[mid][0], lo), max(out[mid][1], hi))
        else:
            out[mid] = (lo, hi)
    if out:
        return out
    ys = [v.y for b in project.boundaries
          if b.btype == BoundaryType.EXTERNAL
          for v in b.polyline.vertices]
    if not ys:
        return {}
    return {m.id: (min(ys), max(ys)) for m in project.materials}


#: Search methods Optimize Surfaces can be applied to. The reference makes
#: the option available for Surface Type = Non-Circular, and these are the
#: three non-circular strategies this program implements.
_OPTIMIZABLE_SEARCHES = ("block", "path", "simulated_annealing")


def _optimize_notes(s_search) -> list[str]:
    """What Optimize Surfaces will and will not do on this model.

    Both notes are rule 7's minimum: a control that cannot be honoured has
    to say so, and one whose cost is unbounded has to say that too.
    """
    from ogr_core.project.settings import optimize_enabled_for

    # v0.1.119 — the RESOLVED tri-state, not the raw field. Reading the
    # automatic ``None`` as "off" would silence both notes for every
    # Simulated Annealing run, which is the one search where the option is
    # on by default and therefore the one where the notes matter most.
    if not optimize_enabled_for(s_search):
        return []
    out = []
    if s_search.search_method not in _OPTIMIZABLE_SEARCHES:
        out.append(
            "Optimize Surfaces applies to non-circular surfaces, which are "
            "the ones with vertices to move; this project searches with "
            "'%s'. The setting was ignored." % s_search.search_method)
    elif getattr(s_search, "optimize_target", "") == "all":
        out.append(
            "Optimize Surfaces is set to optimise ALL surfaces, so the "
            "random walk runs once per surface the search generates rather "
            "than once on the critical one. The answer is the same kind of "
            "answer; the run takes far longer.")
    return out


#: How far apart the two ends of the ground surface must be, as a
#: fraction of the model's own relief, before the check will call a side
#: up-slope. Relative and not absolute, so it reads the same in
#: millimetres and in metres.
#:
#: The bank it was measured on gives no evidence for the exact value: the
#: ratio comes out at exactly 0 for 13 of the 138 models and at 0.50 or
#: more for the other 125, with nothing in between. Any threshold in that
#: gap behaves identically there, so this is a judgement — biased towards
#: speaking up, since a spurious note costs a glance and a missed
#: contradiction costs what the nineteen cost.
_FAILURE_DIRECTION_REL_TOL = 0.01


def _failure_direction_note(project) -> list[str]:
    """Warn when the declared Failure Direction contradicts the ground.

    The crest is the end the mass moves AWAY from, so a ground surface
    that is higher on the left describes a mass sliding towards
    increasing x — left to right. A project that declares the opposite
    has its crest on the wrong side, and three decisions read that
    declaration: which slice carries the tension-crack water thrust
    (``slicer._apply_tension_crack``), which way a support resists
    (``support_integration``), and which face Path Search starts from
    when two are equally steep. A fourth place reads it — the "Failure
    Direction" row of the PDF report — but that one only prints it.

    Found by auditing a bank of 138 models: 19 of them declared right to
    left with the crest plainly on the left. None of the nineteen had a
    support, and the only one with a tension crack had it dry, so not a
    single factor of safety was wrong — which is exactly why it survived.
    The one that mattered would have gone on being wrong silently: with
    the crack wet, the contradictory declaration picks the down-slope end
    of the crack zone, where the ground has already fallen to the base of
    the crack, so the thrust is never applied at all and its factor of
    safety comes out 22.6 % too high, on the unsafe side.

    Compares only the two ENDS of the upper envelope. The steepest-face
    rule the searches use answers a different question and gives false
    positives here: an embankment dam with both toes at the same level
    has a steep face on each side and no up-slope side at all.

    Abstains on a tie. A symmetric embankment has no geometric answer,
    and a check that guesses is worse than one that keeps quiet.
    """
    from ogr_core.geometry import ground_surface

    from .failure_direction import crest_is_on_the_right

    external = project.external_boundary()
    if external is None:
        return []
    vertices = list(ground_surface(external).vertices)
    if len(vertices) < 2:
        return []
    y_left, y_right = vertices[0].y, vertices[-1].y
    relief = max(v.y for v in vertices) - min(v.y for v in vertices)
    if abs(y_left - y_right) <= _FAILURE_DIRECTION_REL_TOL * relief:
        return []

    crest_right = y_right > y_left
    if crest_right == crest_is_on_the_right(project):
        return []

    # Only reached when the two disagree, so the declaration is whatever
    # the ground is not.
    declared_crest_right = not crest_right
    declared = "Right to Left" if declared_crest_right else "Left to Right"
    higher, lower = ("right", "left") if crest_right else ("left", "right")
    return [
        f"The Failure Direction is set to {declared}, which puts the "
        f"crest on the {lower}, but the ground surface is higher on the "
        f"{higher} (y = {y_left:g} at the left end against "
        f"y = {y_right:g} at the right end). Tension-crack water thrust, "
        f"support force direction and the Path Search starting face all "
        f"read this setting."
    ]


# ======================================================================
#: How steep the slip surface's own tangent must be where it daylights,
#: in degrees, before the run says that the factor of safety on that
#: surface depends on the number of slices.
#:
#: A surface that leaves the ground VERTICALLY has an endpoint no finite
#: slicing can represent: the last slice's base angle tends to 90 degrees
#: as the count grows, and every method's contribution from that slice
#: depends strongly on it, so refining keeps moving the answer instead of
#: settling. Measured on the two published circles of verification problem
#: 23 (Low 1989), in one and the same model:
#:
#:     exit tangent 90.00 deg   FoS 1.19207 -> 1.14739 over 30..240 slices
#:                              (3.9 %, still falling)
#:     exit tangent 74.43 deg   FoS 1.36835 -> 1.36482 over 30..240 slices
#:                              (0.26 %, settled)
#:
#: 85 degrees sits in the gap between those two, and it is a REPORTING
#: threshold, not a physical constant: nothing changes in the analysis on
#: either side of it. Being told costs a glance; not being told cost this
#: project anomaly A23-1, where a 25 % error read as convergence.
_DAYLIGHT_TANGENT_WARN_DEG = 85.0


def daylight_tangent_note(result, num_slices: int) -> list[str]:
    """Warn when a critical surface leaves the ground near-vertically.

    The factor of safety is correct for the slicing it was computed with;
    what it is not, on such a surface, is independent of that slicing. The
    reference values published for surfaces like this are themselves values
    at a particular slice count.
    """
    surface = getattr(result, "surface", None)
    angle_at = getattr(surface, "base_angle_at", None)
    if angle_at is None:
        return []
    ends = [getattr(surface, "x_left", None),
            getattr(surface, "x_right", None)]
    if any(x is None for x in ends):
        try:
            ends = list(surface.x_range())
        except Exception:  # noqa: BLE001
            return []
    steepest = 0.0
    for x in ends:
        try:
            steepest = max(steepest, abs(math.degrees(angle_at(x))))
        except Exception:  # noqa: BLE001
            return []
    if steepest < _DAYLIGHT_TANGENT_WARN_DEG:
        return []
    return [
        f"The critical surface daylights at {steepest:.1f} deg from the "
        f"horizontal, which is too steep for a fixed number of slices to "
        f"resolve: its factor of safety depends on that number. It was "
        f"computed with {num_slices} slices. Re-run with more and compare "
        f"before quoting it."
    ]


#: How close to a grid edge the critical centre must fall, as a fraction
#: of that axis' own span, before the run says the grid may be too small.
#:
#: Relative and not absolute, by the project's rule that a geometric
#: tolerance has to read the same in millimetres and in metres. The value
#: barely matters: the centre returned by a Grid Search IS one of the grid
#: nodes, so it either sits on the perimeter exactly or a whole node
#: spacing away from it. Anything well below 1/nx behaves identically.
_GRID_EDGE_REL_TOL = 1e-6


def grid_edge_note(search, result) -> list[str]:
    """Warn when the critical centre came off the edge of the grid.

    A minimum on the boundary of the searched region is not a minimum, it
    is the best of what was looked at — the true one may lie outside, and
    the grid is what decided the answer. Reporting only, like the
    daylight-tangent note: nothing in the analysis changes either way.

    Measured on verification problem 77 of the reference bank, one and the
    same model: with the grid ending at x = 900 the minimum came out AT
    x = 900 and gave 1.757, 11 % above the published value; widened to
    1400 the minimum moved inside to x = 1019 and gave 1.587, 0.2 % off.
    Nothing warned. The back-analysis problem 37 does the same thing with
    its left edge.

    Abstains on an axis of zero span. A one-row or one-column grid puts
    every centre on the perimeter by construction, so a note there would
    fire on every run and mean nothing.
    """
    gx = getattr(search, "grid_x_used", None)
    gy = getattr(search, "grid_y_used", None)
    if gx is None or gy is None:
        return []                      # not a grid search, or it never ran
    crit = getattr(result, "critical", None)
    surface = getattr(crit, "surface", None)
    cx = getattr(surface, "centre_x", None)
    cy = getattr(surface, "centre_y", None)
    if cx is None or cy is None:
        return []

    on_edge = []
    for name, value, (lo, hi) in (("x", cx, gx), ("y", cy, gy)):
        span = abs(hi - lo)
        if span <= 0.0:
            continue
        tol = _GRID_EDGE_REL_TOL * span
        if abs(value - min(lo, hi)) <= tol or abs(value - max(lo, hi)) <= tol:
            on_edge.append(f"{name} = {value:g}")
    if not on_edge:
        return []
    return [
        f"The critical centre lies on the edge of the search grid "
        f"({', '.join(on_edge)}; grid x {gx[0]:g} to {gx[1]:g}, "
        f"y {gy[0]:g} to {gy[1]:g}). A minimum on the boundary is the best "
        f"of what was searched, not necessarily the lowest one: widen the "
        f"grid on that side and re-run before quoting it."
    ]


def build_method(project, method_id: str, num_slices: Optional[int] = None):
    """The configured LEM method object for ``method_id``, or None.

    THE single instantiation point. Two things are attached here and
    nowhere else:

    - the convergence settings the user configured (``lem_kwargs``);
      v0.1.74 found that every method had accepted ``tolerance``,
      ``max_iterations`` and ``initial_fos`` since it was written and
      every call site had instantiated them with no arguments at all;
    - the rapid-drawdown wrapper, applied unconditionally because it is a
      no-op when the project does not ask for one.

    The method table is derived from ``method_registry()`` instead of
    being written out by hand. The hand-written version is what let
    ``janbu_corrected`` be tickable in Project Settings while producing
    no result at all, and let the GUI and the CLI support two different
    subsets of the seven registered methods.
    """
    cls = method_registry().get(method_id)
    if cls is None:
        return None

    s = project.settings
    kwargs = dict(s.lem_kwargs())
    if method_id in _LAMBDA_METHODS:
        kwargs["min_lambda"] = s.advanced.min_lambda
        kwargs["max_lambda"] = s.advanced.max_lambda
    if method_id in _INTERSLICE_METHODS:
        kwargs["interslice_func"] = interslice_function(
            s.methods.interslice_function)
    if method_id in _PRESCRIBED_THETA_METHODS:
        kwargs["interslice_forces"] = getattr(
            s.methods, "interslice_forces", "effective")

    method = cls(**kwargs)

    # v0.1.68 — a rapid drawdown replaces what "the factor of safety of
    # this surface" means, so it is applied where methods are made. A
    # second place that forgot would silently report the ordinary factor
    # of safety instead; from v0.1.72 to v0.1.76, ogr_cli was that place.
    if num_slices is None:
        num_slices = s.methods.num_slices
    return wrap_for_drawdown(method, project, num_slices=int(num_slices))


# ======================================================================
def build_search(project, method_id: str, progress_cb: Optional[Callable] = None):
    """The search object for ``method_id``, configured from the project.

    Exposed so the Overall Slope probabilistic analysis and Optimize
    Surfaces can rebuild EXACTLY the same search once per sample rather
    than duplicating this dispatch. Returns None when ``method_id`` is
    not registered.
    """
    method = build_method(project, method_id)
    if method is None:
        return None

    s = project.settings
    s_search = s.search
    num_slices = s.methods.num_slices
    admissibility = s.admissibility_kwargs()
    search_method = s_search.search_method

    def _seed_kw() -> dict:
        """The project's seed, for the searches that draw at random.

        v0.1.74 — the Random Numbers page promised a pseudo-random run
        "will give exactly the same results", and no search had ever been
        told which seed to use.
        """
        if search_method in _DETERMINISTIC_SEARCHES:
            return {}
        return {"seed": s.analysis_seed()}

    def _optimize_kw() -> dict:
        """Optimize Surfaces, for the NON-CIRCULAR searches only.

        v0.1.104 — the whole panel was editable, saved and read by nobody
        (defect D08, anomaly A9-1): ticking the box on a Block Search
        stored the tick and changed nothing. It is not in ``common``
        because the reference offers the option for Surface Type =
        Non-Circular alone; a circular search would only be able to ignore
        it, which is the fault this closes, not one to repeat.

        The optimisation gets the project's seed too. Without one the walk
        would draw from ``random.Random(None)`` and the same model would
        give a different answer on every run — which is exactly what the
        Random Numbers page promises it will not do.
        """
        kw = dict(s.optimize_kwargs())
        if kw.get("optimize") is not None:
            kw["optimize_seed"] = s.analysis_seed()
        return kw

    common = dict(
        method=method,
        num_slices=num_slices,
        progress_cb=progress_cb,
        **admissibility,
        # v0.1.102 — the Surface Filters, and they go in ``common`` rather
        # than into each branch on purpose: they apply to EVERY search, and
        # the six branches below are exactly the place where a filter gets
        # forgotten for one of them. That is anomaly A37-1: Minimum
        # Elevation and Minimum Depth were declared, editable and saved,
        # and not one branch passed them.
        **s.surface_filter_kwargs(),
        # v0.1.118 — and the Slope Limits go with them, for the same reason
        # and one more. The reason: they are a project setting, so the six
        # branches below are exactly where one of them gets forgotten — and
        # one HAD been, five of them. The extra reason: the reference is
        # explicit that the limits "ALWAYS serve as a filter for valid
        # surfaces, regardless of the Surface Type or the Search Method",
        # and only the Grid Search was ever handed them. Block Search even
        # implemented the filter and was never given a value to filter on.
        # Defect D21 / anomaly A19-1.
        slope_limits=_slope_limits(s_search),
        **_seed_kw(),
    )

    if search_method == "slope":
        from .search import SlopeSearch
        # ``slope_limits`` reaches this search through ``common`` since
        # v0.1.118, but only as the FILTER every search now applies in
        # ``_best_of_masses``. Its GENERATION still derives the entry/exit
        # window from the ground profile and reads no user-supplied limit,
        # which is what ``settings_warnings`` still warns about.
        #
        # v0.1.103 — the LOWER checkbox used to decide nothing: its angle
        # was passed whether or not the box was ticked, so a user who
        # changed the number without ticking got it applied anyway. Same
        # fault as the Path Search's, found while inventorying which
        # settings have a reader at all. Every model of the reference bank
        # stores this field at -45, which is also the search's own default,
        # so gating it moves nothing that exists today.
        return SlopeSearch(
            num_surfaces=s_search.num_surfaces,
            min_area=s_search.min_area or 1.0,
            initial_angle_lower_deg=(
                s_search.initial_angle_at_toe_lower_deg
                if s_search.initial_angle_at_toe_lower_enabled else -45.0),
            initial_angle_upper_deg=(
                s_search.initial_angle_at_toe_upper_deg
                if s_search.initial_angle_at_toe_upper_enabled else None),
            **common,
        )

    if search_method == "auto_refine":
        from .search import AutoRefineSearch
        return AutoRefineSearch(
            # v0.1.103 — both of these used to come from a SECOND field of
            # the same name-but-not-quite (``auto_refine_divisions`` and
            # ``auto_refine_iterations``), which the interface wrote from
            # the same widget and a script never touched. The iterations
            # one defaulted to 5 against the 10 the panel displayed, so a
            # model built by code ran half the search it declared.
            divisions=s_search.auto_refine_divisions_along_slope,
            circles_per_division=getattr(
                s_search, "auto_refine_circles_per_division", 10),
            iterations=s_search.auto_refine_num_iterations,
            next_iter_fraction=getattr(
                s_search, "auto_refine_divisions_to_use_pct", 50.0),
            min_area=s_search.min_area or 0.5,
            **common,
        )

    if search_method == "block":
        from .search import BlockSearch
        return BlockSearch(
            num_groups=s_search.block_num_groups,
            left_start_angle_deg=s_search.block_left_start_angle_deg,
            left_end_angle_deg=s_search.block_left_end_angle_deg,
            right_start_angle_deg=s_search.block_right_start_angle_deg,
            right_end_angle_deg=s_search.block_right_end_angle_deg,
            num_surfaces=s_search.block_num_surfaces,
            min_area=s_search.min_area or 2.0,
            convex_only=s_search.block_convex_only,
            **_optimize_kw(),
            **common,
        )

    if search_method == "path":
        from .search import PathSearch
        return PathSearch(
            # v0.1.103 — every argument on this call used to be read from a
            # field the interface did not show, while the one it did show
            # was saved and ignored. Unticked boxes mean AUTOMATIC, which is
            # how the reference describes all three: the segment length is
            # then ~0.3·H and the angular window [45° below horizontal,
            # β − 5°]. The angles travel in the absolute convention and
            # PathSearch converts them; see the note there.
            segment_length=(float(s_search.path_segment_length_value)
                            if s_search.path_segment_length_manual else None),
            initial_angle_lower_deg=(
                s_search.path_initial_angle_at_toe_lower_deg
                if s_search.path_initial_angle_at_toe_lower_enabled else None),
            initial_angle_upper_deg=(
                s_search.path_initial_angle_at_toe_upper_deg
                if s_search.path_initial_angle_at_toe_upper_enabled else None),
            num_surfaces=s_search.path_num_surfaces,
            convex_only=getattr(s_search, "path_convex_only", False),
            # v0.1.104 — this used to read ``path_optimize``, a field the
            # dialog never showed and that defaulted to True, so Path
            # Search optimised on every run while the checkbox the user
            # could see wrote a setting nothing read. One optimisation
            # now, the same one every non-circular search gets.
            **_optimize_kw(),
            **common,
        )

    if search_method == "simulated_annealing":
        from .search import SimulatedAnnealingSearch
        return SimulatedAnnealingSearch(
            initial_vertices=s_search.sa_initial_vertices,
            generation_steps=s_search.sa_generation_steps,
            tolerance=s_search.sa_tolerance,
            temperature_coefficient=s_search.sa_temperature_coefficient,
            convex_only=s_search.sa_convex_only,
            min_area=s_search.min_area or 1.0,
            **_optimize_kw(),
            **common,
        )

    # Default = Grid Search.
    from .search import GridSearch
    return GridSearch(
        focus_objects=[f for f in getattr(project, "focus_objects", [])
                       if f.enabled and f.valid],
        grid_x=_grid_range(s_search.grid_x_min, s_search.grid_x_max),
        grid_y=_grid_range(s_search.grid_y_min, s_search.grid_y_max),
        grid_nx=s_search.grid_nx,
        grid_ny=s_search.grid_ny,
        radius_increment=s_search.radius_increment or 1.5,
        # v0.1.88 — was 3.0, which pushed the sampled minimum radius above
        # the reference's at every centre closer than 3 m to the ground.
        # The radius bracket is now the reference's, and a hard-coded floor
        # here would have been the one thing still departing from it.
        min_radius=0.0,
        min_area=s_search.min_area or 1.0,
        **common,
    )


def _grid_range(lo, hi):
    """A user-defined grid extent, or None for automatic."""
    if lo is None or hi is None:
        return None
    return (lo, hi)


def _slope_limits(s_search):
    """Explicit slope limits, or None.

    v0.1.55 — None means automatic: derived from the ground surface,
    which is what keeps a model portable between geometries.
    """
    if (s_search.slope_limit_left is None
            or s_search.slope_limit_right is None):
        return None
    return (s_search.slope_limit_left, s_search.slope_limit_right)


# ======================================================================
def run_analysis(project, method_ids=None,
                 progress_cb: Optional[Callable] = None) -> AnalysisOutcome:
    """Run one configured search per method and return every result.

    ``progress_cb(done, total)`` is called across the whole run, not per
    method, so a caller driving a progress bar needs no arithmetic.

    v0.1.57 — the design-standard partial factors are applied HERE, once,
    by substituting a factored **copy** of the project. Every analysis
    path downstream then reads the factored values without knowing the
    feature exists, and the caller's project is never modified.
    """
    from ogr_core.project import apply_design_factors
    project, factor_report = apply_design_factors(project)

    if method_ids is None:
        method_ids = list(project.settings.methods.enabled_methods)
    method_ids = list(method_ids) or ["bishop_simplified"]

    known = method_registry()
    warnings: list[str] = settings_warnings(project, method_ids)
    results: dict = {}
    n_methods = len(method_ids)

    for i, mid in enumerate(method_ids):
        if mid not in known:
            # v0.1.77 — this used to be a bare ``continue``, and that is
            # how "Janbu Corrected" could be ticked in Project Settings
            # and produce nothing whatsoever. An unrunnable method now
            # leaves a trace.
            warnings.append(
                f"'{mid}' is not a registered analysis method, so it was "
                f"not computed. Available: {', '.join(sorted(known))}.")
            continue

        def _progress(done, total, _i=i, _n=n_methods):
            if progress_cb is not None:
                progress_cb(_i * total + done, _n * total)

        search = build_search(project, mid, progress_cb=_progress)
        if search is None:  # pragma: no cover - guarded by the check above
            continue
        results[mid] = search.run(project)
        # v0.1.100 — a surface that daylights near-vertically has a factor
        # of safety that moves with the slice count. Said once per method,
        # on the surface the run actually reports.
        crit = getattr(results[mid], "critical", None)
        if crit is not None:
            for note in daylight_tangent_note(crit, search.num_slices):
                line = f"{mid}: {note}"
                if line not in warnings:
                    warnings.append(line)
        # v0.1.102 — and once per method, whether the answer came off the
        # boundary of the region that was searched at all.
        for note in grid_edge_note(search, results[mid]):
            line = f"{mid}: {note}"
            if line not in warnings:
                warnings.append(line)
        # v0.1.121 — anything the search itself decided it had to say, such
        # as a weak-layer case set that had to be truncated. Prefixed with
        # the method because the same surface can be truncated under one
        # method and not another.
        for note in getattr(results[mid], "notes", ()):
            line = f"{mid}: {note}"
            if line not in warnings:
                warnings.append(line)

    return AnalysisOutcome(results, factor_report, warnings, project)

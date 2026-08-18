# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Slip-surface search engines.

Two search strategies are provided:

    - :class:`GridSearch` — grid of circle centres × radius increments.
      Classical "Swedish" search for circular surfaces.
    - :class:`SlopeSearch` — sample circles that emerge at the toe of
      the slope with random angles / radii.

Both return a :class:`SearchResult` containing every evaluated surface
sorted by ascending Factor of Safety.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Optional

from ogr_core.project import Project

from .methods import LEMMethod, LEMResult
from .slicer import slice_surface
from .surface import SlipCircle


@dataclass
class SearchResult:
    """Aggregate result of a surface-search run."""

    method_id: str
    evaluations: list[LEMResult] = field(default_factory=list)
    valid_count: int = 0
    invalid_count: int = 0
    # v0.1.24 — generation attempts made (searches that count VALID
    # surfaces, e.g. Path Search, report the true attempt count here).
    attempts: int = 0

    @property
    def critical(self) -> Optional[LEMResult]:
        """Lowest-FoS surface among the ADMISSIBLE ones.

        v0.1.32 — surfaces rejected by the post-analysis checks are kept
        in ``evaluations`` (search algorithms that steer on the factor of
        safety need them) but never reported as the critical surface. If
        every surface is inadmissible the checks are ignored rather than
        returning nothing, so the user always gets an answer plus the
        warning in ``inadmissible_count``.
        """
        valid = [r for r in self.evaluations if r.is_valid]
        if not valid:
            return None
        ok = [r for r in valid if getattr(r, "admissible", True)]
        return min(ok or valid, key=lambda r: r.fos)

    @property
    def total_count(self) -> int:
        """Every surface the search GENERATED, valid or not.

        v0.1.83 — the honest denominator, and the reason it needs its own
        name: ``len(evaluations)`` is not it. A surface that could not be
        analysed has no ``LEMResult`` to store, so it never reaches that
        list, yet it was generated and the reference counts it. On the
        Ej_1 benchmark grid the two differ by 1697 of 4851.

        The reference documents the population exactly — (X intervals + 1)
        × (Y intervals + 1) × (Radius Increment + 1) — so this is a
        checkable identity, not a bookkeeping preference.
        """
        return self.valid_count + self.invalid_count

    @property
    def inadmissible_count(self) -> int:
        return sum(1 for r in self.evaluations
                   if r.is_valid and not getattr(r, "admissible", True))

    @property
    def analysed_count(self) -> int:
        """Surfaces that both converged AND survived the post-checks.

        v0.1.84 — the number to report to the user, and the reason it is
        not ``valid_count``: a surface screened out by the m-alpha or
        tensile check has a converged factor of safety, so it counts as
        valid, but it can never be the critical surface. With the m-alpha
        check off by default that gap was always zero; with it on, as the
        reference has it, the panel would have claimed 2966 valid
        surfaces while 64 of them were barred from ever being the answer.
        The reference makes the same choice: its report lists surfaces
        screened by error code -112 under "Number of Invalid Surfaces".
        """
        return max(0, self.valid_count - self.inadmissible_count)

    @property
    def min_fos(self) -> float:
        c = self.critical
        return c.fos if c else math.inf

    def valid(self) -> list[LEMResult]:
        return [r for r in self.evaluations if r.is_valid]

    def top_n(self, n: int = 10) -> list[LEMResult]:
        return sorted(self.valid(), key=lambda r: r.fos)[:n]


# ======================================================================
class BaseSearch(ABC):
    """Base class for search strategies."""

    def __init__(
        self,
        method: LEMMethod,
        num_slices: int = 30,
        min_area: float = 0.5,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        reject_tensile: bool = False,
        tensile_tolerance: float = 0.05,
        tensile_percent: float = 95.0,
        check_m_alpha: bool = True,
    ) -> None:
        self.method = method
        self.num_slices = num_slices
        self.min_area = min_area
        self.progress_cb = progress_cb
        # v0.1.24 — optional kinematic-admissibility filter (anomaly A3).
        # A physically acceptable limit-equilibrium mechanism requires
        # COMPRESSIVE interslice forces; a surface whose force field
        # needs substantial interslice TENSION is not a feasible
        # mechanism, and the reference documentation warns that such
        # surfaces yield a safety factor that is "usually too low".
        # Non-circular searches can generate them (e.g. a deep wedge
        # closed by a near-vertical rising segment), so this filter is
        # available for all searches. Default OFF to preserve existing
        # results; recommended ON for non-circular searches.
        # See Krahn (2003), "The limits of limit equilibrium analyses".
        self.reject_tensile = reject_tensile
        self.tensile_tolerance = tensile_tolerance
        # v0.1.32 — reference-style post-analysis checks (anomaly A3).
        # ``reject_tensile`` now maps onto the documented Tensile Stress
        # Check: negative effective normal stress on slice BASES, tested
        # AFTER the factor of safety has converged, over a percentage of
        # slices measured from the toe. Both default to off, as in the
        # reference, where tensile normal stresses are permitted unless
        # the user opts in.
        self.tensile_percent = tensile_percent
        # v0.1.89 — DEFAULT ON, matching ProjectSettings.advanced, which has
        # said True since v0.1.84. Until now the two disagreed, so the same
        # model gave two different answers depending on which door you came
        # in by: through build_search (interface, CLI, validation cases) the
        # check ran, and constructing a search directly — every test, every
        # script, examples/ — it did not.
        #
        # What that hid, found in v0.1.89 when nine test models stopped being
        # degenerate: with 10 m of foundation under the toe, Simulated
        # Annealing returned FoS 0.500 and Block Search 0.651 on this stable
        # slope, against a circular minimum of 1.1239. Both surfaces closed
        # with a near-vertical segment, where m_alpha goes NEGATIVE and
        # Bishop's formulation divides by it. With the check on: 1.187 and
        # 1.120, and the surfaces still reach 9.5 m below the toe — depth was
        # never the problem, the vertical closing segment was.
        #
        # The comment above, written in v0.1.24, names this exact mechanism
        # ("a deep wedge closed by a near-vertical rising segment") and says
        # the filter is "recommended ON for non-circular searches". It was
        # left off "to preserve existing results" — results that were only
        # stable because no test model had soil to dive into.
        #
        # NOTE the asymmetry, and it is deliberate: reject_tensile stays OFF
        # because the reference permits tensile normal stresses unless the
        # user opts in, while its reports DO filter on m_alpha by default and
        # count the rejects as error -112.
        self.check_m_alpha = check_m_alpha

    # ------------------------------------------------------------------
    def _is_admissible(self, result: Optional[LEMResult]) -> bool:
        """Reference-style post-analysis admissibility.

        Applied as a POST-FILTER on a converged result — never during the
        iteration — exactly as the reference specifies. Surfaces failing
        the Tensile Stress Check or the m-alpha check are discarded, and
        the reason is recorded on the result for reporting.
        """
        if result is None:
            return True
        if not (self.reject_tensile or self.check_m_alpha):
            return True
        try:
            from .checks import check_surface
            ok, reason = check_surface(
                result,
                tensile=self.reject_tensile,
                tensile_percent=self.tensile_percent,
                m_alpha=self.check_m_alpha,
            )
        except Exception:  # noqa: BLE001
            return True
        if not ok:
            result.admissible = False
            result.admissibility_note = reason or ""
        return ok

    # ------------------------------------------------------------------
    def evaluate_circle(
        self, project: Project, circle: SlipCircle
    ) -> Optional[LEMResult]:
        # v0.1.11 — Early-skip: bbox-only checks before doing the
        # full slicing pass. We reject circles that obviously cannot
        # produce a valid failure surface.
        try:
            xmin, ymin, xmax, ymax = project.bounding_box()
        except Exception:
            xmin = ymin = xmax = ymax = None
        if xmin is not None:
            cx, cy, R = circle.centre_x, circle.centre_y, circle.radius
            # Skip 1: circle bbox does not overlap model bbox at all
            if (cx + R < xmin or cx - R > xmax
                    or cy + R < ymin or cy - R > ymax):
                return None
            # Skip 2: circle is so high above the model that it
            # cannot intersect the ground (centre well above bbox top
            # AND lower edge above bbox top → no possible intersection)
            if cy - R > ymax:
                return None
            # Skip 3: circle so deep below the bottom that lower edge
            # is more than radius below the model bottom (non-physical)
            if cy + R < ymin:
                return None

        # v0.1.84 — a circle that crosses the ground more than twice
        # defines several DISJOINT sliding masses, and the critical
        # mechanism is the one with the lowest factor of safety. Until now
        # the first mass from the left was taken and the rest discarded
        # unseen; on the Ej_2 reference model that resolved Slide's own
        # critical circle onto a 62 m² lens of level ground beyond the toe
        # (driving moment ≈ 0, so no factor of safety at all) instead of
        # the 184 m² slope failure at FoS = 1.155, and the true critical
        # circle was thrown away as invalid.
        best: Optional[LEMResult] = None
        for trial in self._candidate_surfaces(project, circle):
            slices = slice_surface(project, trial, num_slices=self.num_slices)
            if slices is None or len(slices) < 3:
                continue
            # Filter by minimum "area" (here approximated as Σ w_i · h_i)
            area = sum(s.width * max(s.height, 0.0) for s in slices)
            if area < self.min_area:
                continue
            res = self.method.compute_fos(project, trial, slices)
            self._is_admissible(res)     # marks res.admissible in place
            if res is None:
                continue
            if best is None:
                best = res
            elif res.is_valid and (not best.is_valid or res.fos < best.fos):
                best = res
        if best is not None:
            # The caller's circle must end up carrying the mass that was
            # actually analysed, or the drawing and the number disagree.
            circle.x_left = best.surface.x_left
            circle.x_right = best.surface.x_right
            circle.tension_cracks = list(
                getattr(best.surface, "tension_cracks", []) or [])
        return best

    # ------------------------------------------------------------------
    def _candidate_surfaces(self, project: Project, circle: SlipCircle):
        """Yield every sliding mass of ``circle`` that is worth analysing.

        Each is a fresh :class:`SlipCircle` with its endpoints already
        resolved and its reverse curvature already treated, so the caller
        only has to slice and solve.

        Masses that leave the soil region are dropped, which is the
        reference's documented behaviour for non-composite circular
        surfaces and what its report counts as error −103. With Composite
        Surfaces enabled the rule does not apply: that option exists
        precisely so such a circle follows the boundary instead of being
        rejected by it. Containment is judged on the surface as finally
        analysed — after any reverse-curvature tension crack has moved an
        endpoint — because that is the surface the factor of safety
        belongs to.
        """
        from ogr_core.geometry import ground_surface
        from .slicer import _reverse_curvature_mode
        from .surface import leaves_soil_region

        external = project.external_boundary()
        if external is None:
            return
        if circle.x_left is not None and circle.x_right is not None:
            yield circle           # already resolved by the caller
            return

        ground = ground_surface(external)
        chords = circle.candidate_chords(ground)
        if not chords:
            return
        mode = _reverse_curvature_mode(project)
        try:
            composite = bool(project.settings.search.composite_surfaces)
        except AttributeError:
            composite = False
        ext_verts = list(external.polyline.vertices)

        for x_l, x_r in chords:
            trial = SlipCircle(centre_x=circle.centre_x,
                               centre_y=circle.centre_y,
                               radius=circle.radius)
            trial.x_left, trial.x_right = x_l, x_r
            if not trial.apply_reverse_curvature(ground, mode=mode):
                continue
            if not composite and leaves_soil_region(
                    trial, ext_verts, trial.x_left, trial.x_right):
                continue
            yield trial

    # ------------------------------------------------------------------
    def evaluate_surface(
        self, project: Project, surface
    ) -> Optional[LEMResult]:
        """Evaluate any SurfaceProtocol (circular or non-circular)."""
        slices = slice_surface(project, surface, num_slices=self.num_slices)
        if slices is None or len(slices) < 3:
            return None
        area = sum(s.width * max(s.height, 0.0) for s in slices)
        if area < self.min_area:
            return None
        res = self.method.compute_fos(project, surface, slices)
        self._is_admissible(res)     # marks res.admissible in place
        return res

    # ------------------------------------------------------------------
    def run(self, project: Project) -> SearchResult:
        """Run the search with the project's region caches frozen.

        v0.1.93 — a template method purely so the freeze cannot be
        forgotten by one search or one caller. Resolving the material at a
        point revalidates the regions cache by rebuilding a signature over
        every boundary vertex, about twice per slice; on the Ej_2 reference
        grid that was 41 % of the run, for a model that by contract does
        not change while it is being analysed.

        It is here rather than in ``analysis_runner.build_search`` for the
        reason v0.1.89 records above: when the interface and direct
        construction come in by different doors, the two end up behaving
        differently. Tests, scripts and ``examples/`` all build their
        search by hand.
        """
        with project.regions_frozen():
            return self._run(project)

    @abstractmethod
    def _run(self, project: Project) -> SearchResult: ...


# ======================================================================
class GridSearch(BaseSearch):
    """Grid Search (circular) — Slide2 method.

    v0.1.17 — reimplemented to follow the documented Slide2 algorithm:

    1. A rectangular grid of slip-circle CENTRES is defined (Auto Grid
       or Add Grid). With ``grid_nx`` × ``grid_ny`` intervals there are
       (grid_nx+1)·(grid_ny+1) centres.
    2. For each centre, the **Slope Limits** determine the relevant
       "slope surface" (the segments of the External between the
       limits). Suitable MINIMUM and MAXIMUM radii are computed from the
       distances between the centre and that slope surface, so every
       generated circle actually intersects the slope.
    3. The **Radius Increment** is the NUMBER OF INTERVALS between the
       minimum and maximum radius; the number of circles per centre is
       therefore (Radius Increment + 1).

    The previous implementation used ``radius_increment`` as a metric
    step size and swept from a fixed minimum to the bbox diagonal,
    generating large numbers of useless circles and missing the
    per-centre radius bracketing. This version matches Slide.
    """

    def __init__(
        self,
        method: LEMMethod,
        grid_x: tuple[float, float] | None = None,
        grid_y: tuple[float, float] | None = None,
        grid_nx: int = 10,
        grid_ny: int = 10,
        radius_increment: float = 10.0,
        # v0.1.88 — was 2.0. The reference has no minimum-radius control at
        # all, so any non-zero default made the out-of-the-box sampling
        # differ from it at every centre whose nearest ground point is
        # closer than that. Kept as an option because excluding tiny
        # circles is a legitimate thing to want; zero by default because
        # reproducing the reference is what the default is for.
        min_radius: float = 0.0,
        num_slices: int = 30,
        min_area: float = 0.5,
        slope_limits: tuple[float, float] | None = None,
        focus_objects=None,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        **legacy_kwargs,
    ) -> None:
        super().__init__(
            method, num_slices, min_area, progress_cb,
            reject_tensile=bool(legacy_kwargs.pop('reject_tensile', False)),
            tensile_tolerance=float(
                legacy_kwargs.pop('tensile_tolerance', 0.05)),
            tensile_percent=float(
                legacy_kwargs.pop('tensile_percent', 95.0)),
            check_m_alpha=bool(
                legacy_kwargs.pop('check_m_alpha', True)),
        )
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.grid_nx = max(2, grid_nx)
        self.grid_ny = max(2, grid_ny)
        # radius_increment is the NUMBER OF INTERVALS (Slide convention).
        # Accept floats for back-compat but use as an integer count.
        self.radius_increment = max(1, int(round(radius_increment)))
        self.min_radius = min_radius
        self.slope_limits = slope_limits
        # v0.1.55 (phase M4) — focus objects, applied BEFORE evaluation:
        # rejecting a circle costs two distance calculations, evaluating
        # one costs a full slicing and iteration, so the order is what
        # makes focusing worth using rather than merely tidy.
        self.focus_objects = focus_objects or []

    # ------------------------------------------------------------------
    def _auto_grid(self, project: Project) -> tuple[tuple[float, float], tuple[float, float]]:
        xmin, ymin, xmax, ymax = project.bounding_box()
        dx = xmax - xmin
        dy = ymax - ymin
        gx = (xmin + 0.2 * dx, xmax - 0.2 * dx)
        gy = (ymax, ymax + 0.8 * dy)  # above the ground
        return gx, gy

    # ------------------------------------------------------------------
    def _slope_surface(self, project):
        """The ground profile between the Slope Limits, **ends included**.

        v0.1.88 — the clip now INTERPOLATES the two limit abscissae instead
        of filtering vertices by x. It has to: the radius bracket below is
        measured to the two limit POINTS, and a limit falling between two
        vertices used to yield no point at all — the segment it cut was
        dropped whole, the surface ended at the last vertex strictly inside,
        and both ends of the bracket were then measured to the wrong place.
        """
        from ogr_core.geometry import BoundaryType, Vertex
        ext = None
        for b in project.boundaries:
            if b.btype == BoundaryType.EXTERNAL:
                ext = b
                break
        if ext is None:
            return []
        top = PathSearch._ground_profile(ext.polyline.vertices)
        if self.slope_limits is None or len(top) < 2:
            return top
        x0, x1 = sorted(self.slope_limits)
        x0 = max(x0, top[0].x)
        x1 = min(x1, top[-1].x)
        # Relative to the profile's own width, not absolute: the same model
        # in millimetres and in metres has to clip identically.
        tol = 1e-9 * max(top[-1].x - top[0].x, 1e-300)
        if x1 - x0 <= tol:
            # Limits that cross, or collapse onto one abscissa, describe no
            # surface at all. Falling back to the whole profile keeps the
            # search running on something meaningful instead of returning a
            # result computed from a single point.
            return top
        y0 = PathSearch._interpolate_top_y(top, x0)
        y1 = PathSearch._interpolate_top_y(top, x1)
        if y0 is None or y1 is None:
            return top
        # Strict comparison, so a profile vertex sitting exactly on a limit
        # is not emitted twice: the interpolated end already carries it.
        inner = [v for v in top if x0 + tol < v.x < x1 - tol]
        return [Vertex(x0, y0)] + inner + [Vertex(x1, y1)]

    # ------------------------------------------------------------------
    @staticmethod
    def _distance_to_surface(xc, yc, pts) -> float:
        """Shortest distance from a centre to the slope surface POLYLINE.

        The nearest point is the foot of a perpendicular when that foot
        falls inside a segment and a VERTEX when it does not, and both cases
        occur among the reference centres — at Ej_2's (12.381, 87.632) the
        nearest point is the vertex (40, 55), not any perpendicular foot. So
        clamping the projection parameter to [0, 1] is not a nicety; taking
        distances to vertices only (which is what this class did until
        v0.1.88) is a different and wrong measurement.
        """
        best = float("inf")
        for a, b in zip(pts[:-1], pts[1:]):
            dx = b.x - a.x
            dy = b.y - a.y
            L2 = dx * dx + dy * dy
            if L2 <= 0.0:
                t = 0.0
            else:
                t = ((xc - a.x) * dx + (yc - a.y) * dy) / L2
                t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
            d = math.hypot(xc - (a.x + t * dx), yc - (a.y + t * dy))
            if d < best:
                best = d
        return best

    # The sampled range is inset by this fraction of its own width at each
    # end. MEASURED, not chosen — see _radius_bracket. It is a constant of
    # the rule: the A1/A2 pair (same grid, Radius Increment 1 and 10) gives
    # byte-identical bracket ends, so the inset does not depend on how many
    # circles are asked for.
    RADIUS_INSET = 0.05

    def _radius_bracket(self, xc, yc, slope_pts):
        """The (r_min, r_max) sampled at one grid centre.

        v0.1.88 — DERIVED FROM MEASUREMENT, replacing two versions of
        inference from a drawing. *Grid Search* says only that "suitable
        Minimum and Maximum radii are determined, based on the distances
        from the slip center to the slope surface", and v0.1.84 recorded
        that reading the accompanying figure literally made one reference
        model better and the other twice as bad. The rule below is not a
        reading of the figure: it is read off the reference's own output.

        The rule
        --------
        With ``S`` the slope surface (the ground profile between the Slope
        Limits) and ``P_L``, ``P_R`` the two limit points::

            d_min = distance from the centre to the nearest point of S
            d_max = min(|C - P_L|, |C - P_R|)      # the limit reached FIRST
            delta = RADIUS_INSET * (d_max - d_min)

            r_min = d_min + delta
            r_max = d_max - delta

        and Radius Increment intervals give ``rinc + 1`` equally spaced
        radii across ``[r_min, r_max]``.

        Two consequences worth stating, because both were bugs before:

        * ``d_max >= d_min`` is a THEOREM, not a case to guard: ``P_L`` and
          ``P_R`` are points OF ``S``, so their distances cannot be below
          the minimum distance to ``S``. This function therefore never
          fails, and the population of a grid is exactly
          ``(nx+1)(ny+1)(rinc+1)`` — the denominator v0.1.83 fixed. An
          earlier draft returned None when ``d_max == d_min`` and silently
          dropped Ej_1's whole ``x = 120`` column, 4851 circles down to
          4620.
        * when ``d_min == d_max`` (the centre sits directly above a limit
          point) the rule yields ``rinc + 1`` IDENTICAL radii, and that is
          what the reference does too: at Ej_1's (120, 30) it emits eleven
          circles of R = 5.

        How it was measured
        -------------------
        ``referencias/Ejemplos/00_2026_08_17_Test_Regla_radios`` holds six
        Slide models run for this. Their ``.s01`` output lists, per centre,
        every generated circle as ``(r, yleft, x1, y1, x2, y2, yright,
        fs..., b1)``, so the bracket is READ rather than fitted — which is
        what unblocked this, since four fitted numbers could never have
        settled it (rule 1). The models come in pairs: Radius Increment 1
        (exactly two circles, the two ends) and 10 (eleven), on the same
        grid, for two geometries — one failing left-to-right, one
        right-to-left.

            check                                          worst error
            68 bracket ends, both geometries, rinc 1 & 10   5.7e-14
            441 centres of Ej_1's reference grid            4.0e-08 *
            440 centres of Ej_2's reference grid            7.0e-13
            uniform spacing, rinc+1 circles per centre      8.4e-13

        (*) that outlier is one centre, Ej_1's (52, 48), which lies exactly
        ON the slope face so ``d_min`` is 0: the reference prints
        2.601922406 where the rule gives 2.601922366, 1.5e-8 relative. Its
        own numerics in the degenerate case, not a disagreement.

        Decisively, the rule generates the two critical radii that no
        previous bracket could reach: 47.2124436 at Ej_1's (88, 70.5), the
        4th of its 11, and 60.2564659 at Ej_2's (-3.333, 87.632), the 4th
        of its 11. Both reference global minima are now IN the sampled
        population, and the searches land on the reference's own centre and
        radius rather than on a neighbour:

            case            method        before            after
            Ej_1            Bishop        +0.18 %           +0.02 %
            Ej_1            Janbu simpl.  -0.55 %           +0.13 %
            Ej_2            Bishop        +0.95 %           -0.07 %
            Ej_2            Janbu simpl.  +0.83 %           -0.03 %

        The five PUBLISHED cases of ``validacion/casos/`` — an independent
        check, since none of them is a Slide run — all stay inside their
        declared tolerances, moving by at most 0.24 % and in both
        directions. Both facts are tabulated in
        ``docs/audits/grid_radius_rule_v188.md``.

        What is NOT measured
        --------------------
        In all six models the Slope Limits sit at their automatic position,
        which coincides with the ends of the ground profile. The data
        therefore cannot distinguish "the limit points" from "the ends of
        the profile", nor whether ``d_min`` is measured over the clipped
        surface or the whole one. What is implemented is the documented
        reading — "the slope surface is simply the segments of the External
        Boundary between the Slope Limits" — so narrowing the limits
        narrows the radii. Confirming it needs one more Slide model with
        the limits moved inward to an abscissa that is NOT a profile
        vertex; until that exists, this paragraph is the honest statement of
        what the rule rests on.

        ``min_radius`` is an OGR control with no counterpart in the
        reference (which offers Minimum Elevation and Minimum Depth
        instead). It acts as a floor on ``d_min``, and its default is 0 so
        that the out-of-the-box sampling is the reference's exactly.
        """
        if not slope_pts or len(slope_pts) < 2:
            return None
        d_min = max(self._distance_to_surface(xc, yc, slope_pts),
                    self.min_radius)
        # The FIRST limit reached as the radius grows, not the farthest one:
        # past it the circle no longer daylights inside the Slope Limits.
        d_max = min(math.hypot(xc - slope_pts[0].x, yc - slope_pts[0].y),
                    math.hypot(xc - slope_pts[-1].x, yc - slope_pts[-1].y))
        # max() only matters when min_radius has been raised above d_min,
        # which is the one way the caller can break the theorem above.
        d_max = max(d_max, d_min)
        delta = self.RADIUS_INSET * (d_max - d_min)
        return d_min + delta, d_max - delta

    # ------------------------------------------------------------------
    def _run(self, project: Project) -> SearchResult:
        gx = self.grid_x or self._auto_grid(project)[0]
        gy = self.grid_y or self._auto_grid(project)[1]

        nx_pts = self.grid_nx + 1
        ny_pts = self.grid_ny + 1
        xs = [gx[0] + (gx[1] - gx[0]) * i / (nx_pts - 1) for i in range(nx_pts)]
        ys = [gy[0] + (gy[1] - gy[0]) * j / (ny_pts - 1) for j in range(ny_pts)]

        slope_pts = self._slope_surface(project)

        result = SearchResult(method_id=self.method.METHOD_ID)
        total = nx_pts * ny_pts
        processed = 0
        n_circles = self.radius_increment + 1  # circles per centre

        for xc in xs:
            for yc in ys:
                processed += 1
                if self.progress_cb:
                    self.progress_cb(processed, total)

                bracket = self._radius_bracket(xc, yc, slope_pts)
                if bracket is None:
                    # No slope surface at all: nothing can be generated
                    # here. Counted rather than skipped, for the same
                    # reason as below.
                    result.invalid_count += n_circles
                    continue
                r_min, r_max = bracket
                for k in range(n_circles):
                    if n_circles > 1:
                        r = r_min + (r_max - r_min) * k / (n_circles - 1)
                    else:
                        r = r_min
                    if r <= 0:
                        # Only reachable when the centre IS a limit point,
                        # so d_min = d_max = 0. Counted, not skipped: the
                        # population has to stay (nx+1)(ny+1)(rinc+1)
                        # whatever the geometry does — see total_count.
                        result.invalid_count += 1
                        continue
                    if self.focus_objects:
                        from .focus import accepts as _focus_accepts
                        if not _focus_accepts(self.focus_objects, xc, yc,
                                              r):
                            continue
                    circle = SlipCircle(centre_x=xc, centre_y=yc, radius=r)
                    res = self.evaluate_circle(project, circle)
                    # v0.1.83 — a circle that could not be analysed is
                    # still a circle that was GENERATED, and it has to
                    # appear in the totals. Until now ``res is None`` fell
                    # through counting nothing at all, so 1697 of the 4851
                    # circles of the reference grid simply vanished: the
                    # window reported "2966 / 3154" for a population of
                    # 4851. Worse, the denominator MOVED when a search
                    # option changed (2633 with reverse curvature off),
                    # which is the one thing a number a user compares
                    # between runs must never do.
                    if res is None:
                        result.invalid_count += 1
                        continue
                    if res.is_valid and not (0.2 <= res.fos <= 100.0):
                        result.invalid_count += 1
                        continue
                    result.evaluations.append(res)
                    if res.is_valid:
                        result.valid_count += 1
                    else:
                        result.invalid_count += 1

        return result


# ======================================================================
class SlopeSearch(BaseSearch):
    """Slope Search (circular) — Slide2 method.

    v0.1.17 — reimplemented to follow the documented Slide2 algorithm,
    which is the circular analogue of the Path Search:

    1. The Slope Limits define the segment(s) of ground surface used
       for the slip-surface ENTRY and EXIT points.
    2. For each candidate, TWO points are randomly generated on the
       ground surface within the Slope Limits — one on the toe side
       (the exit, lower) and one on the crest side (the entry, upper).
    3. A circular arc is fitted through those two surface points. The
       THIRD constraint that makes the circle unique is the *Initial
       Angle at Toe* — the inclination of the slip surface where it
       emerges at the toe. By default Slide samples this angle randomly
       within an admissible window; the circle centre is then the
       intersection of (a) the perpendicular bisector of the two
       surface points and (b) the line through the toe point normal to
       the chosen tangent direction.

    This produces circles that actually daylight on the slope surface
    between the Slope Limits, rather than arbitrary circles spanning the
    whole bounding box (the old behaviour).
    """

    def __init__(
        self,
        method: LEMMethod,
        num_surfaces: int = 1000,
        num_slices: int = 30,
        min_area: float = 0.5,
        initial_angle_lower_deg: float = -45.0,
        initial_angle_upper_deg: Optional[float] = None,
        seed: Optional[int] = 42,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        **legacy_kwargs,
    ) -> None:
        # v0.1.77 — the admissibility arguments are forwarded here for
        # the same reason the other five searches forward them: the
        # Tensile Stress and m-alpha checks are project settings, not
        # per-search ones. Until this version SlopeSearch was the only
        # search that did not accept them, and since the GUI passes them
        # to every search, picking Slope Search raised a TypeError that
        # the blanket ``except Exception`` in the compute worker turned
        # into a generic "Error" dialog with no results — for every
        # release since the first public one.
        super().__init__(
            method, num_slices, min_area, progress_cb,
            reject_tensile=bool(legacy_kwargs.pop('reject_tensile', False)),
            tensile_tolerance=float(
                legacy_kwargs.pop('tensile_tolerance', 0.05)),
            tensile_percent=float(
                legacy_kwargs.pop('tensile_percent', 95.0)),
            check_m_alpha=bool(
                legacy_kwargs.pop('check_m_alpha', True)),
        )
        self.num_surfaces = num_surfaces
        self.initial_angle_lower_deg = initial_angle_lower_deg
        self.initial_angle_upper_deg = initial_angle_upper_deg
        self.rng = random.Random(seed)

    def _run(self, project: Project) -> SearchResult:
        from ogr_core.geometry import BoundaryType

        result = SearchResult(method_id=self.method.METHOD_ID)

        ext = None
        for b in project.boundaries:
            if b.btype == BoundaryType.EXTERNAL:
                ext = b
                break
        if ext is None:
            return result
        ext_verts = ext.polyline.vertices
        if len(ext_verts) < 3:
            return result

        # Ground profile (real upper contour). Reuse PathSearch helper.
        top = PathSearch._ground_profile(ext_verts)
        if len(top) < 2:
            return result

        x_left = top[0].x
        x_right = top[-1].x
        y_max = max(v.y for v in ext_verts)
        y_min = min(v.y for v in ext_verts)
        H = y_max - y_min

        # Locate slope face (steepest segment) → toe/crest + β
        steepest_i = 0
        steepest = -1.0
        for i in range(len(top) - 1):
            ddx = top[i + 1].x - top[i].x
            ddy = top[i + 1].y - top[i].y
            if abs(ddx) < 1e-9:
                continue
            s = abs(ddy / ddx)
            if s > steepest:
                steepest = s
                steepest_i = i
        face_a = top[steepest_i]
        face_b = top[steepest_i + 1]
        beta_deg = math.degrees(math.atan2(
            abs(face_b.y - face_a.y), abs(face_b.x - face_a.x)))
        toe_pt = face_a if face_a.y <= face_b.y else face_b
        crest_pt = face_b if face_a.y <= face_b.y else face_a
        to_right = crest_pt.x > toe_pt.x
        face_lo_x = min(face_a.x, face_b.x)
        face_hi_x = max(face_a.x, face_b.x)
        face_w = max(face_hi_x - face_lo_x, 1e-6)

        # Entry (toe-side) and exit (crest-side) sampling ranges along x.
        # Generous ranges (extending onto the flat shelf and plateau) so
        # the search can reach deep-seated circles whose daylight points
        # are well beyond the slope face — these often govern the
        # critical FoS.
        if to_right:
            toe_x0 = max(x_left, toe_pt.x - 0.8 * face_w)
            toe_x1 = toe_pt.x + 0.6 * face_w
            crest_x0 = crest_pt.x - 0.4 * face_w
            crest_x1 = min(x_right, crest_pt.x + 1.5 * face_w)
        else:
            toe_x0 = toe_pt.x - 0.6 * face_w
            toe_x1 = min(x_right, toe_pt.x + 0.8 * face_w)
            crest_x0 = max(x_left, crest_pt.x - 1.5 * face_w)
            crest_x1 = crest_pt.x + 0.4 * face_w
            toe_x0, toe_x1 = min(toe_x0, toe_x1), max(toe_x0, toe_x1)
            crest_x0, crest_x1 = min(crest_x0, crest_x1), max(crest_x0, crest_x1)

        # Initial-angle window (radians, descending into slope). Use a
        # wide window so both shallow and deep-seated circles are
        # generated: from steep (toward −70°) up to nearly horizontal.
        ang_lo = math.radians(self.initial_angle_lower_deg)
        if self.initial_angle_upper_deg is not None:
            ang_hi = math.radians(self.initial_angle_upper_deg)
        else:
            # v0.1.24 FIX (anomaly A2): same root cause as A1 — the
            # documented Upper Angle is +(β − 5)°. The tangent of a
            # toe-exiting circle at the toe RISES towards the crest
            # (e.g. +15.5° for the reference case), so negating this
            # limit excluded the true critical circle from the search
            # and the reported FoS was ~1.05 instead of ~0.89.
            ang_hi = math.radians(max(beta_deg - 5.0, 5.0))
        # Broaden downward so deep circles (steep exit tangents) appear
        ang_lo = min(ang_lo, math.radians(-70.0))
        if ang_lo > ang_hi:
            ang_lo, ang_hi = ang_hi, ang_lo

        best = []  # (fos, cx, cy, r)
        for i in range(self.num_surfaces):
            if self.progress_cb and (i % 50 == 0):
                self.progress_cb(i, self.num_surfaces)

            # Two surface points: toe (exit) and crest (entry)
            xt = self.rng.uniform(toe_x0, toe_x1)
            xc = self.rng.uniform(crest_x0, crest_x1)
            yt = PathSearch._interpolate_top_y(top, xt)
            yc = PathSearch._interpolate_top_y(top, xc)
            if yt is None or yc is None:
                result.invalid_count += 1
                continue
            if abs(xc - xt) < 0.5:
                result.invalid_count += 1
                continue

            theta = self.rng.uniform(ang_lo, ang_hi)
            circle = self._circle_from_point_tangent_point(
                xt, yt, theta, xc, yc, to_right,
            )
            if circle is None:
                result.invalid_count += 1
                continue
            cx, cy, radius = circle
            if radius <= 0 or radius > 50.0 * max(H, 1.0):
                result.invalid_count += 1
                continue

            from .surface import SlipCircle
            sc = SlipCircle(centre_x=cx, centre_y=cy, radius=radius)
            res = self.evaluate_circle(project, sc)
            if res is not None:
                if res.is_valid and not (0.2 <= res.fos <= 100.0):
                    result.invalid_count += 1
                    continue
                result.evaluations.append(res)
                if res.is_valid:
                    result.valid_count += 1
                    best.append((res.fos, cx, cy, radius))
                else:
                    result.invalid_count += 1
            else:
                result.invalid_count += 1

        # v0.1.17 — local refinement (gradient-free hill-descent) on the
        # best few circles, mirroring Slide's surface optimisation. This
        # is what lets the Slope Search converge onto the same critical
        # circle the Grid Search finds, instead of stopping at the best
        # random sample.
        if best:
            from .surface import SlipCircle
            best.sort(key=lambda t: t[0])
            for k in range(min(8, len(best))):
                f0, cx, cy, r = best[k]
                cur_f, cur = f0, (cx, cy, r)
                span = max(0.15 * r, 1.0)
                for _it in range(120):
                    step = span * (1.0 - _it / 120.0)
                    tcx = cur[0] + self.rng.uniform(-step, step)
                    tcy = cur[1] + self.rng.uniform(-step, step)
                    tr = cur[2] + self.rng.uniform(-step, step)
                    if tr <= 0:
                        continue
                    sc = SlipCircle(centre_x=tcx, centre_y=tcy, radius=tr)
                    res = self.evaluate_circle(project, sc)
                    if res is None or not res.is_valid:
                        continue
                    if not (0.2 <= res.fos <= 100.0):
                        continue
                    result.evaluations.append(res)
                    result.valid_count += 1
                    if res.fos < cur_f:
                        cur_f = res.fos
                        cur = (tcx, tcy, tr)

        if self.progress_cb:
            self.progress_cb(self.num_surfaces, self.num_surfaces)
        return result

    @staticmethod
    def _circle_from_point_tangent_point(x1, y1, tangent_angle,
                                         x2, y2, to_right):
        """Determine the circle passing through (x1,y1) and (x2,y2) whose
        tangent at (x1,y1) has the given inclination ``tangent_angle``
        (radians from +x axis).

        Geometry: the centre lies on the line through (x1,y1)
        perpendicular to the tangent direction, AND on the perpendicular
        bisector of the chord (x1,y1)-(x2,y2). Intersect the two.

        Returns (cx, cy, radius) or None if degenerate / centre below
        the surface.
        """
        # Normal to the tangent at point 1 (perpendicular direction)
        # tangent unit vector:
        tx, ty = math.cos(tangent_angle), math.sin(tangent_angle)
        # normal direction (rotate 90°): (-ty, tx)
        nx, ny = -ty, tx
        # Line 1: P1 + s*(nx,ny)  → centre is somewhere on this line.
        # Line 2: perpendicular bisector of P1-P2.
        mx, my = 0.5 * (x1 + x2), 0.5 * (y1 + y2)
        # chord direction
        cdx, cdy = x2 - x1, y2 - y1
        # bisector direction (perp to chord): (-cdy, cdx)
        bx, by = -cdy, cdx
        # Solve P1 + s*(nx,ny) = M + t*(bx,by)
        # → s*nx - t*bx = mx - x1 ; s*ny - t*by = my - y1
        det = nx * (-by) - (-bx) * ny
        if abs(det) < 1e-12:
            return None
        rhs_x = mx - x1
        rhs_y = my - y1
        s = (rhs_x * (-by) - (-bx) * rhs_y) / det
        cx = x1 + s * nx
        cy = y1 + s * ny
        radius = math.hypot(cx - x1, cy - y1)
        # The centre must be ABOVE the surface points for a valid
        # slip circle (concave-up arc daylighting on the slope).
        if cy < max(y1, y2):
            return None
        return (cx, cy, radius)


# ======================================================================
# v0.1.10 — Stub solver classes for the additional Search Methods.
#
# These currently delegate to GridSearch / SlopeSearch (or run a small
# random sweep) so the user can SELECT the method without crashing.
# Full implementations of Block/Path/SA/AutoRefine arrive in v0.2.x.
# ======================================================================
class AutoRefineSearch(BaseSearch):
    """Auto Refine Search (circular) — Slide2 method.

    v0.1.17 — reimplemented to follow the documented Slide2 algorithm,
    which iteratively narrows the search to the part of the slope that
    produces the lowest safety factors:

    1. The slope surface (between the Slope Limits) is divided into
       ``divisions`` divisions, measured ALONG the slope polyline.
    2. For each PAIR of divisions, ``circles_per_division`` circles are
       generated. The straight line joining the division midpoints sets
       a MINIMUM tangent angle; vertical (90°) sets the MAXIMUM. The
       angular range is split equally (with a small offset) and a circle
       is fitted for each tangent angle.
    3. The FoS of each circle is computed and the AVERAGE FoS associated
       with each division is recorded.
    4. The ``next_iter_fraction`` (e.g. 0.5 = 50%) of divisions with the
       LOWEST average FoS are kept; the rest are discarded. The retained
       divisions form a new, narrowed slope polyline.
    5. Steps 1-4 repeat for ``iterations`` iterations (no convergence
       cut-off — the full count always runs).

    This typically finds a lower FoS than Grid or Slope search for an
    equal number of surfaces.
    """

    def __init__(
        self,
        method,
        divisions: int = 10,
        circles_per_division: int = 10,
        iterations: int = 5,
        next_iter_fraction: float = 0.5,
        num_slices: int = 30,
        min_area: float = 0.5,
        slope_limits: Optional[tuple] = None,
        focus_objects=None,
        progress_cb=None,
        # Back-compat (old signature used factor/radius_increment)
        **legacy_kwargs,
    ) -> None:
        super().__init__(
            method=method, num_slices=num_slices,
            reject_tensile=bool(legacy_kwargs.pop('reject_tensile', False)),
            tensile_tolerance=float(
                legacy_kwargs.pop('tensile_tolerance', 0.05)),
            tensile_percent=float(
                legacy_kwargs.pop('tensile_percent', 95.0)),
            check_m_alpha=bool(
                legacy_kwargs.pop('check_m_alpha', True)),
        )
        self.divisions = max(2, divisions)
        self.circles_per_division = max(1, circles_per_division)
        self.iterations = max(1, iterations)
        # next_iter_fraction may arrive as a percentage (50) or fraction
        # (0.5); normalise to a fraction.
        f = next_iter_fraction
        if f > 1.0:
            f = f / 100.0
        self.next_iter_fraction = min(0.95, max(0.1, f))
        self.min_area = min_area
        self.slope_limits = slope_limits
        # v0.1.55 (phase M4) — focus objects, applied BEFORE evaluation:
        # rejecting a circle costs two distance calculations, evaluating
        # one costs a full slicing and iteration, so the order is what
        # makes focusing worth using rather than merely tidy.
        self.focus_objects = focus_objects or []
        self.progress_cb = progress_cb

    def _run(self, project) -> SearchResult:
        from ogr_core.geometry import BoundaryType
        from .surface import SlipCircle

        result = SearchResult(method_id=self.method.METHOD_ID)

        ext = None
        for b in project.boundaries:
            if b.btype == BoundaryType.EXTERNAL:
                ext = b
                break
        if ext is None:
            return result
        top = PathSearch._ground_profile(ext.polyline.vertices)
        if len(top) < 2:
            return result

        # Initial slope polyline = ground profile within Slope Limits.
        #
        # v0.1.92 — the clip INTERPOLATES the limit abscissae, as
        # GridSearch._slope_surface has done since v0.1.88. It used to keep
        # the vertices whose x fell between the limits, which throws away the
        # segment a limit cuts through: a limit that is not itself a vertex
        # produced no point at all, and the polyline this search starts from
        # ended at the last vertex strictly inside instead of at the limit.
        #
        # v0.1.88 reported this and did NOT fix it, because there was no
        # measurement saying where the limits belong. There is now: two
        # models run with the limits moved inward to abscissae that are not
        # vertices show the surface reaching exactly to the limit POINTS, to
        # 5e-14. See tests/test_grid_radius_rule_v188.py.
        poly_pts = list(top)
        if self.slope_limits is not None and len(top) >= 2:
            x0, x1 = sorted(self.slope_limits)
            x0 = max(x0, top[0].x)
            x1 = min(x1, top[-1].x)
            span = max(top[-1].x - top[0].x, 1e-300)
            tol = 1e-9 * span            # relative, never absolute
            if x1 - x0 > tol:
                y0 = PathSearch._interpolate_top_y(top, x0)
                y1 = PathSearch._interpolate_top_y(top, x1)
                if y0 is not None and y1 is not None:
                    from ogr_core.geometry import Vertex as _V
                    poly_pts = ([_V(x0, y0)]
                                + [v for v in top if x0 + tol < v.x < x1 - tol]
                                + [_V(x1, y1)])
        if len(poly_pts) < 2:
            poly_pts = list(top)

        # Resample the slope polyline into a dense set of points we can
        # divide evenly along arc length.
        def _resample(pts, n):
            """Return n+1 points equally spaced along the polyline arc."""
            seg = []
            total = 0.0
            for a, b in zip(pts[:-1], pts[1:]):
                d = math.hypot(b.x - a.x, b.y - a.y)
                seg.append(d)
                total += d
            if total < 1e-9:
                return list(pts)
            out = []
            from ogr_core.geometry import Vertex
            for i in range(n + 1):
                target = total * i / n
                acc = 0.0
                placed = False
                for j, d in enumerate(seg):
                    if acc + d >= target - 1e-12:
                        f = (target - acc) / d if d > 1e-12 else 0.0
                        a, b = pts[j], pts[j + 1]
                        out.append(Vertex(a.x + f * (b.x - a.x),
                                          a.y + f * (b.y - a.y)))
                        placed = True
                        break
                    acc += d
                if not placed:
                    out.append(pts[-1])
            return out

        total_iter = self.iterations
        for it in range(total_iter):
            if self.progress_cb:
                self.progress_cb(it, total_iter)
            # Divide the current slope polyline into `divisions` divisions
            div_pts = _resample(poly_pts, self.divisions)
            # midpoint of each division
            mids = []
            for k in range(len(div_pts) - 1):
                ax, ay = div_pts[k].x, div_pts[k].y
                bx, by = div_pts[k + 1].x, div_pts[k + 1].y
                mids.append(((ax + bx) / 2.0, (ay + by) / 2.0))

            # For each PAIR of divisions (i<j) generate circles and
            # accumulate the FoS into BOTH divisions' running averages.
            div_fos_sum = [0.0] * (len(div_pts) - 1)
            div_fos_cnt = [0] * (len(div_pts) - 1)

            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    p1 = mids[i]
                    p2 = mids[j]
                    # The chord direction between the two midpoints.
                    dxm = p2[0] - p1[0]
                    dym = p2[1] - p1[1]
                    chord_ang = math.atan2(dym, dxm)
                    # For a concave-up slip circle through the two
                    # points with the centre ABOVE them, the valid
                    # tangent angles lie roughly from (chord_ang + 90°)
                    # towards (chord_ang + 180°). We sweep this band,
                    # which corresponds to the documented "minimum angle
                    # = slope of joining line, maximum = vertical"
                    # mapped into the construction's convention. Invalid
                    # constructions (centre below points) are filtered.
                    lo = chord_ang + math.radians(92.0)
                    hi = chord_ang + math.radians(178.0)
                    ncpd = self.circles_per_division
                    for c in range(ncpd):
                        if ncpd > 1:
                            ang = lo + (hi - lo) * c / (ncpd - 1)
                        else:
                            ang = 0.5 * (lo + hi)
                        circle = self._circle_through_two_points_tangent(
                            p1[0], p1[1], p2[0], p2[1], ang)
                        if circle is None:
                            continue
                        cx, cy, r = circle
                        sc = SlipCircle(centre_x=cx, centre_y=cy, radius=r)
                        res = self.evaluate_circle(project, sc)
                        if res is None or not res.is_valid:
                            result.invalid_count += 1
                            continue
                        if not (0.2 <= res.fos <= 100.0):
                            result.invalid_count += 1
                            continue
                        result.evaluations.append(res)
                        result.valid_count += 1
                        for d in (i, j):
                            div_fos_sum[d] += res.fos
                            div_fos_cnt[d] += 1

            # Average FoS per division; keep the lowest fraction
            div_avg = []
            for d in range(len(div_pts) - 1):
                if div_fos_cnt[d] > 0:
                    div_avg.append((div_fos_sum[d] / div_fos_cnt[d], d))
                else:
                    div_avg.append((float("inf"), d))
            div_avg.sort(key=lambda t: t[0])
            n_keep = max(1, int(round(
                (len(div_pts) - 1) * self.next_iter_fraction)))
            keep_idx = sorted(d for _f, d in div_avg[:n_keep])

            # Build the narrowed slope polyline from the retained
            # divisions (contiguous span from first to last kept index).
            if keep_idx:
                lo_i = keep_idx[0]
                hi_i = keep_idx[-1] + 1
                new_pts = div_pts[lo_i:hi_i + 1]
                if len(new_pts) >= 2:
                    poly_pts = new_pts

        if self.progress_cb:
            self.progress_cb(total_iter, total_iter)
        return result

    @staticmethod
    def _circle_through_two_points_tangent(x1, y1, x2, y2, tangent_angle):
        """Circle passing through two division-midpoints, with the given
        initial tangent angle at the first point.

        For Auto Refine, the tangent direction at the lower point plus
        the requirement to pass through the upper point defines the
        circle. The centre lies on the normal to the tangent at point 1,
        at the distance where it is equidistant from point 2. The centre
        must be ABOVE both points (concave-up daylighting arc).
        Returns (cx, cy, r) or None.
        """
        # Normal direction at point 1 (perpendicular to tangent)
        tx, ty = math.cos(tangent_angle), math.sin(tangent_angle)
        nx, ny = -ty, tx  # rotate +90°
        # Centre = P1 + s·(nx,ny). Solve |C - P2| = |C - P1| = r.
        # |C-P1|² = s²;  |C-P2|² = (P1+s·n - P2)² = s²
        # Expand: (P1-P2)² + 2 s n·(P1-P2) = 0  → s = -(P1-P2)²/(2 n·(P1-P2))
        dx1 = x1 - x2
        dy1 = y1 - y2
        denom = 2.0 * (nx * dx1 + ny * dy1)
        if abs(denom) < 1e-12:
            return None
        s = -(dx1 * dx1 + dy1 * dy1) / denom
        cx = x1 + s * nx
        cy = y1 + s * ny
        r = math.hypot(cx - x1, cy - y1)
        if r <= 1e-6:
            return None
        # Centre must be above both points (valid slip arc)
        if cy < max(y1, y2):
            # try the mirrored normal
            nx, ny = ty, -tx
            denom = 2.0 * (nx * dx1 + ny * dy1)
            if abs(denom) < 1e-12:
                return None
            s = -(dx1 * dx1 + dy1 * dy1) / denom
            cx = x1 + s * nx
            cy = y1 + s * ny
            r = math.hypot(cx - x1, cy - y1)
            if cy < max(y1, y2):
                return None
        return (cx, cy, r)


class BlockSearch(BaseSearch):
    """Block Search (non-circular) — Slide2 method.

    v0.1.17 — reimplemented to follow the documented Slide2 algorithm.
    The sliding mass is treated as active / central / passive "blocks".

    Method (per the Slide documentation):
      1. One random point is generated for each Block Search object. In
         the absence of user-drawn search objects, OGR generates the
         points within ``num_groups`` vertical "block windows" spanning
         the central part of the slope — these act as implicit search
         windows.
      2. The points are sorted by X-coordinate so the surface is
         kinematically admissible (single-valued, does not reverse).
      3. The Left and Right Projection Angles project the surface up to
         the ground surface from the leftmost and rightmost block points.
         Angles are measured CCW from the +x axis (Slide convention):
         the default Left = 135°, Right = 45°. A *range* (start..end)
         may be given, in which case a random angle in the range is
         drawn per surface.
      4. The surface must intersect the slope surface within the Slope
         Limits, otherwise it is discarded.
      5. Repeated for ``num_surfaces`` candidates.

    Options: ``convex_only`` rejects surfaces with a reflex (non-convex)
    vertex, matching Slide's "Convex Surfaces Only".
    """

    def __init__(
        self,
        method,
        num_groups: int = 3,
        left_proj_angle_deg: float = 135.0,
        right_proj_angle_deg: float = 45.0,
        left_start_angle_deg: Optional[float] = None,
        left_end_angle_deg: Optional[float] = None,
        right_start_angle_deg: Optional[float] = None,
        right_end_angle_deg: Optional[float] = None,
        num_surfaces: int = 1000,
        num_slices: int = 30,
        min_area: float = 1.0,
        convex_only: bool = False,
        slope_limits: Optional[tuple] = None,
        focus_objects=None,
        seed: Optional[int] = None,
        progress_cb=None,
        **legacy_kwargs,
    ) -> None:
        super().__init__(
            method=method, num_slices=num_slices,
            reject_tensile=bool(legacy_kwargs.pop('reject_tensile', False)),
            tensile_tolerance=float(
                legacy_kwargs.pop('tensile_tolerance', 0.05)),
            tensile_percent=float(
                legacy_kwargs.pop('tensile_percent', 95.0)),
            check_m_alpha=bool(
                legacy_kwargs.pop('check_m_alpha', True)),
        )
        self.num_groups = max(1, num_groups)
        # Single-angle defaults; ranges override if provided.
        self.left_start = (left_start_angle_deg
                           if left_start_angle_deg is not None
                           else left_proj_angle_deg)
        self.left_end = (left_end_angle_deg
                         if left_end_angle_deg is not None
                         else left_proj_angle_deg)
        self.right_start = (right_start_angle_deg
                            if right_start_angle_deg is not None
                            else right_proj_angle_deg)
        self.right_end = (right_end_angle_deg
                          if right_end_angle_deg is not None
                          else right_proj_angle_deg)
        self.num_surfaces = num_surfaces
        self.min_area = min_area
        self.convex_only = convex_only
        self.slope_limits = slope_limits
        # v0.1.55 (phase M4) — focus objects, applied BEFORE evaluation:
        # rejecting a circle costs two distance calculations, evaluating
        # one costs a full slicing and iteration, so the order is what
        # makes focusing worth using rather than merely tidy.
        self.focus_objects = focus_objects or []
        self.seed = seed
        self.progress_cb = progress_cb

    def _run(self, project) -> SearchResult:
        import random
        from ogr_core.geometry import Polyline, Vertex, BoundaryType
        from .surface import SlipSurface

        rng = random.Random(self.seed)
        result = SearchResult(method_id=self.method.METHOD_ID)

        try:
            xmin, ymin, xmax, ymax = project.bounding_box()
        except Exception:  # noqa: BLE001
            return result
        dx = xmax - xmin
        dy = ymax - ymin
        if dx < 1e-3 or dy < 1e-3:
            return result

        ext = None
        for b in project.boundaries:
            if b.btype == BoundaryType.EXTERNAL:
                ext = b
                break
        if ext is None:
            return result
        ext_verts = ext.polyline.vertices
        top = PathSearch._ground_profile(ext_verts)
        if len(top) < 2:
            return result

        # External polygon for inside-tests
        ext_poly = None
        try:
            from shapely.geometry import Polygon as _Poly
            ext_poly = _Poly([(v.x, v.y) for v in ext_verts])
            if not ext_poly.is_valid:
                ext_poly = ext_poly.buffer(0)
        except Exception:  # noqa: BLE001
            ext_poly = None

        # Slope-limits x-range (endpoints must daylight within this)
        if self.slope_limits is not None:
            sl_x0, sl_x1 = sorted(self.slope_limits)
        else:
            sl_x0, sl_x1 = top[0].x, top[-1].x

        # v0.1.17 — collect user-drawn Block Search objects. Each is a
        # Boundary of type BLOCK_SEARCH_OBJECT. Their geometry kind is
        # inferred from the vertex count:
        #   - 1 vertex   → point   (use exactly)
        #   - 2 vertices → line    (sample a random point along it)
        #   - closed 4-vertex → window (sample inside the quad)
        #   - open >2    → polyline (sample a point along it)
        block_objects = [
            b for b in project.boundaries
            if b.btype == BoundaryType.BLOCK_SEARCH_OBJECT
        ]
        use_user_objects = len(block_objects) > 0

        # Block windows: vertical bands over the slope region. Center
        # them on the slope face (the steepest ground segment) so the
        # sampled points fall inside the soil mass, not in the air in
        # front of the toe.
        steepest_i = 0
        steepest = -1.0
        for i in range(len(top) - 1):
            ddx = top[i + 1].x - top[i].x
            ddy = top[i + 1].y - top[i].y
            if abs(ddx) < 1e-9:
                continue
            sl = abs(ddy / ddx)
            if sl > steepest:
                steepest = sl
                steepest_i = i
        face_lo_x = min(top[steepest_i].x, top[steepest_i + 1].x)
        face_hi_x = max(top[steepest_i].x, top[steepest_i + 1].x)
        face_w = max(face_hi_x - face_lo_x, 1e-6)
        # Windows span from a little before the toe to a little past the
        # crest, where realistic slip surfaces pass.
        x_lo = max(xmin, face_lo_x - 0.3 * face_w)
        x_hi = min(xmax, face_hi_x + 0.5 * face_w)
        y_lo = ymin + 0.05 * dy
        y_hi = ymin + 0.75 * dy

        for ip in range(self.num_surfaces):
            if self.progress_cb and ip % 25 == 0:
                self.progress_cb(ip, self.num_surfaces)

            # 1. one random point per block window (or per user-drawn
            #    Block Search object). Each point must lie INSIDE the
            #    soil mass.
            block_pts = []
            ok = True
            if use_user_objects:
                # Sample one point from each user-drawn search object.
                for bobj in block_objects:
                    pt = self._sample_block_object(bobj, rng)
                    if pt is None:
                        ok = False
                        break
                    px, py = pt
                    # Clip to inside the soil; reject points above ground
                    gy = PathSearch._interpolate_top_y(top, px)
                    if gy is not None and py > gy + 1e-6:
                        ok = False
                        break
                    if ext_poly is not None:
                        from shapely.geometry import Point as _Pt0
                        if not ext_poly.buffer(1e-6 * max(dx, 1.0)).contains(
                                _Pt0(px, py)):
                            ok = False
                            break
                    block_pts.append(Vertex(px, py))
            else:
                for k in range(self.num_groups):
                    bx0 = x_lo + (x_hi - x_lo) * k / self.num_groups
                    bx1 = x_lo + (x_hi - x_lo) * (k + 1) / self.num_groups
                    px = rng.uniform(bx0, bx1)
                    gy = PathSearch._interpolate_top_y(top, px)
                    if gy is None:
                        ok = False
                        break
                    min_depth = 0.10 * max(dy, 1.0)
                    hi = min(y_hi, gy - min_depth)
                    lo = y_lo
                    if hi <= lo:
                        hi = lo + 0.1
                    py = rng.uniform(lo, hi)
                    if ext_poly is not None:
                        from shapely.geometry import Point as _Pt0
                        if not ext_poly.contains(_Pt0(px, py)):
                            ok = False
                            break
                    block_pts.append(Vertex(px, py))
            if not ok or len(block_pts) < 1:
                result.invalid_count += 1
                continue

            # 2. sort by x (kinematic admissibility)
            block_pts.sort(key=lambda v: v.x)

            # 3. projection angles (range → random per surface)
            a_left = math.radians(rng.uniform(
                min(self.left_start, self.left_end),
                max(self.left_start, self.left_end)))
            a_right = math.radians(rng.uniform(
                min(self.right_start, self.right_end),
                max(self.right_start, self.right_end)))

            left_pt = self._project_to_top(
                block_pts[0], a_left, top, xmin, ymax)
            right_pt = self._project_to_top(
                block_pts[-1], a_right, top, xmax, ymax)
            if left_pt is None or right_pt is None:
                result.invalid_count += 1
                continue

            verts = sorted([left_pt] + block_pts + [right_pt],
                           key=lambda v: v.x)
            # dedup near-coincident x
            deduped = [verts[0]]
            for v in verts[1:]:
                if abs(v.x - deduped[-1].x) > 1e-3:
                    deduped.append(v)
            if len(deduped) < 3:
                result.invalid_count += 1
                continue

            # 4. endpoints must daylight within the Slope Limits
            if not (sl_x0 - 1e-6 <= deduped[0].x <= sl_x1 + 1e-6):
                result.invalid_count += 1
                continue
            if not (sl_x0 - 1e-6 <= deduped[-1].x <= sl_x1 + 1e-6):
                result.invalid_count += 1
                continue

            # kinematic admissibility: interior vertices below the chord
            x0v, y0v = deduped[0].x, deduped[0].y
            xnv, ynv = deduped[-1].x, deduped[-1].y
            admissible = True
            if xnv - x0v > 1e-9:
                for vv in deduped[1:-1]:
                    tt = (vv.x - x0v) / (xnv - x0v)
                    chord = y0v + tt * (ynv - y0v)
                    if vv.y > chord + 1e-6:
                        admissible = False
                        break
            if not admissible:
                result.invalid_count += 1
                continue

            # v0.1.17 — require the surface to be UNIMODAL (single
            # valley): y descends to a minimum then ascends. This
            # rejects "sawtooth" surfaces (down-up-down-up) that produce
            # spurious low FoS values from non-physical wedge shapes.
            ys = [v.y for v in deduped]
            imin = ys.index(min(ys))
            unimodal = True
            for a in range(1, imin + 1):
                if ys[a] > ys[a - 1] + 1e-6:
                    unimodal = False
                    break
            if unimodal:
                for a in range(imin + 1, len(ys)):
                    if ys[a] < ys[a - 1] - 1e-6:
                        unimodal = False
                        break
            if not unimodal:
                result.invalid_count += 1
                continue

            # Convex Surfaces Only filter
            if self.convex_only and len(deduped) >= 3:
                if not self._is_convex_down(deduped):
                    result.invalid_count += 1
                    continue

            # Inside-External validation
            if ext_poly is not None:
                from shapely.geometry import Point as _Pt
                buf = ext_poly.buffer(1e-6 * max(dx, 1.0))
                if any(not buf.contains(_Pt(v.x, v.y)) for v in deduped):
                    result.invalid_count += 1
                    continue

            poly = Polyline(vertices=deduped, closed=False)
            surface = SlipSurface(polyline=poly)
            res = self.evaluate_surface(project, surface)
            if res is None:
                result.invalid_count += 1
                continue
            if res.is_valid and not (0.2 <= res.fos <= 100.0):
                result.invalid_count += 1
                continue
            result.evaluations.append(res)
            if res.is_valid:
                result.valid_count += 1
            else:
                result.invalid_count += 1

        if self.progress_cb:
            self.progress_cb(self.num_surfaces, self.num_surfaces)
        return result

    @staticmethod
    def _sample_block_object(boundary, rng):
        """Sample one point from a Block Search object, per Slide rules.

        point (1 vertex)   → the exact point
        line (2 vertices)  → random point along the segment
        polyline (>2 open) → random point along the polyline
        window (closed quad)→ random point inside the quadrilateral
        Returns (x, y) or None.
        """
        verts = boundary.polyline.vertices
        closed = getattr(boundary.polyline, "closed", False)
        n = len(verts)
        if n == 0:
            return None
        if n == 1:
            return (verts[0].x, verts[0].y)
        if closed and n >= 3:
            # Window: sample inside the polygon via bounding-box rejection
            xs = [v.x for v in verts]
            ys = [v.y for v in verts]
            x0, x1 = min(xs), max(xs)
            y0, y1 = min(ys), max(ys)
            poly = [(v.x, v.y) for v in verts]
            for _ in range(50):
                px = rng.uniform(x0, x1)
                py = rng.uniform(y0, y1)
                if BlockSearch._point_in_poly(px, py, poly):
                    return (px, py)
            # fallback: centroid
            return (sum(xs) / n, sum(ys) / n)
        # line or open polyline: sample by arc length
        seglens = []
        total = 0.0
        for a, b in zip(verts[:-1], verts[1:]):
            d = math.hypot(b.x - a.x, b.y - a.y)
            seglens.append(d)
            total += d
        if total < 1e-12:
            return (verts[0].x, verts[0].y)
        t = rng.uniform(0.0, total)
        acc = 0.0
        for i, d in enumerate(seglens):
            if acc + d >= t:
                f = (t - acc) / d if d > 1e-12 else 0.0
                a, b = verts[i], verts[i + 1]
                return (a.x + f * (b.x - a.x), a.y + f * (b.y - a.y))
            acc += d
        return (verts[-1].x, verts[-1].y)

    @staticmethod
    def _point_in_poly(x, y, poly) -> bool:
        inside = False
        n = len(poly)
        j = n - 1
        for i in range(n):
            xi, yi = poly[i]
            xj, yj = poly[j]
            if ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / (yj - yi + 1e-300) + xi
            ):
                inside = not inside
            j = i
        return inside

    @staticmethod
    def _is_convex_down(verts) -> bool:
        """True if the polyline is convex when viewed as a slip surface
        (no interior vertex makes a reflex angle pointing downward — the
        cross-products of consecutive edges keep a consistent sign)."""
        sign = 0
        for i in range(1, len(verts) - 1):
            ax = verts[i].x - verts[i - 1].x
            ay = verts[i].y - verts[i - 1].y
            bx = verts[i + 1].x - verts[i].x
            by = verts[i + 1].y - verts[i].y
            cross = ax * by - ay * bx
            if abs(cross) < 1e-12:
                continue
            s = 1 if cross > 0 else -1
            if sign == 0:
                sign = s
            elif s != sign:
                return False
        return True

    @staticmethod
    def _project_to_top(
        start, angle_rad: float, top_verts, x_clip: float, y_clip: float,
    ):
        """March from `start` in the given direction until we cross the
        top profile of the External, return the intersection point."""
        from ogr_core.geometry import Vertex
        x0, y0 = start.x, start.y
        cx, sy = math.cos(angle_rad), math.sin(angle_rad)
        step = 0.5
        max_iters = 10000
        t = 0.0
        prev_above = None
        for _ in range(max_iters):
            t += step
            x = x0 + t * cx
            y = y0 + t * sy
            if x < min(top_verts[0].x, x_clip) - 1.0:
                return None
            if x > max(top_verts[-1].x, x_clip) + 1.0:
                return None
            if y > y_clip + 1.0:
                return None
            top_y = PathSearch._interpolate_top_y(top_verts, x)
            if top_y is None:
                continue
            now_above = y > top_y
            if prev_above is not None and now_above != prev_above:
                return Vertex(x, top_y)
            prev_above = now_above
            if t == step and y > top_y:
                return Vertex(x0, top_y)
        return None


class PathSearch(BaseSearch):
    """Path Search (non-circular) — XSTABL "Irregular Surface Search".

    v0.1.17 — reimplemented to follow the algorithm documented by
    Rocscience for Slide2, which is itself modelled on the "Irregular
    Surface Search" of the slope-stability program XSTABL. The previous
    (v0.1.15/16) implementation used a unimodal depth-profile heuristic
    that produced reasonable shapes but did not match the documented
    method. The XSTABL method is:

    1. **Initiation point** — randomly generated on the slope surface
       within the toe-side half of the Slope Limits. Slide ALWAYS starts
       at the toe and progresses towards the crest, regardless of the
       Failure Direction.

    2. **First segment** — emitted from the initiation point at a random
       *Initial Angle at Toe*. The default angular window is
       [45° below horizontal, (β − 5°)], where β is the inclination of
       the ground-surface segment at the initiation point. Angles follow
       Slide's convention (CCW-positive from +x axis); for a
       right-to-left failure the surface descends into the slope.

    3. **Subsequent segments** — each of fixed ``segment_length`` (Slide
       default ≈ 0.3·H, H = slope height). The direction of each new
       segment is drawn randomly but constrained to keep the surface
       *kinematically admissible* (concave-up: the segment angle rotates
       monotonically upward, never folding back down). This is the XSTABL
       admissibility rule and prevents the "impossible" wavy surfaces.

    4. **Termination** — the surface is grown until it re-emerges on the
       ground surface. The exit point must lie within the Slope Limits,
       otherwise the surface is discarded (the Slope Limits act as a
       filter on the endpoint, per the documentation).

    5. **Minimum Elevation** — no vertex may go below the lower limit of
       the External boundary (or a user Minimum Elevation).

    6. **Optimize Surfaces** — optional Surface Altering Optimization
       (random-walk refinement of the best surfaces) to drive the FoS
       lower, matching Slide's "Optimize Surfaces" post-process.

    All randomness is reproducible when ``seed`` is given (Slide's
    Pseudo-Random mode).
    """

    def __init__(
        self,
        method,
        num_paths: int = 500,
        num_slices: int = 30,
        segment_length: Optional[float] = None,
        initial_angle_upper_deg: Optional[float] = None,
        initial_angle_lower_deg: float = -45.0,
        min_elevation: Optional[float] = None,
        optimize: bool = True,
        optimize_iterations: int = 200,
        convex_only: bool = False,
        seed: Optional[int] = None,
        progress_cb=None,
        max_segments: int = 30,
        max_attempts_factor: int = 20,
        **legacy_kwargs,
    ) -> None:
        super().__init__(
            method=method, num_slices=num_slices,
            reject_tensile=bool(legacy_kwargs.pop('reject_tensile', False)),
            tensile_tolerance=float(
                legacy_kwargs.pop('tensile_tolerance', 0.05)),
            tensile_percent=float(
                legacy_kwargs.pop('tensile_percent', 95.0)),
            check_m_alpha=bool(
                legacy_kwargs.pop('check_m_alpha', True)),
        )
        self.num_paths = num_paths
        # v0.1.24 — cap on generation attempts (num_paths × factor)
        self.max_attempts_factor = max(1, max_attempts_factor)
        # segment_length None → auto (0.3·H) computed in run()
        self.segment_length = segment_length
        self.initial_angle_upper_deg = initial_angle_upper_deg
        self.initial_angle_lower_deg = initial_angle_lower_deg
        self.min_elevation = min_elevation
        self.optimize = optimize
        self.optimize_iterations = optimize_iterations
        self.convex_only = convex_only
        self.seed = seed
        self.progress_cb = progress_cb
        self.max_segments = max(5, max_segments)
        # Back-compat: older callers passed num_vertices / min_area /
        # min_angle_deg / max_angle_deg. Absorb silently.
        self.num_vertices = legacy_kwargs.get("num_vertices", 8)
        self.min_area = legacy_kwargs.get("min_area", 1.0)
        if "min_angle_deg" in legacy_kwargs:
            self.initial_angle_lower_deg = legacy_kwargs["min_angle_deg"]
        # External polygon + ground profile, set in run()
        self._ext_poly = None
        self._top = None
        self._y_floor = None

    # ------------------------------------------------------------------
    def _run(self, project) -> SearchResult:
        import random
        from ogr_core.geometry import BoundaryType, Polyline, Vertex
        from .surface import SlipSurface

        rng = random.Random(self.seed)
        result = SearchResult(method_id=self.method.METHOD_ID)

        ext = None
        for b in project.boundaries:
            if b.btype == BoundaryType.EXTERNAL:
                ext = b
                break
        if ext is None:
            return result
        ext_verts = ext.polyline.vertices
        if len(ext_verts) < 3:
            return result

        # Ground profile (real upper contour, sorted by x)
        top = self._ground_profile(ext_verts)
        if len(top) < 2:
            return result
        self._top = top

        # External polygon for inside-tests
        self._ext_poly = None
        try:
            from shapely.geometry import Polygon as _Poly
            self._ext_poly = _Poly([(v.x, v.y) for v in ext_verts])
            if not self._ext_poly.is_valid:
                self._ext_poly = self._ext_poly.buffer(0)
        except Exception:  # noqa: BLE001
            self._ext_poly = None

        x_left = top[0].x
        x_right = top[-1].x
        y_min = min(v.y for v in ext_verts)
        y_max = max(v.y for v in ext_verts)
        H = y_max - y_min  # slope height
        self._y_floor = (self.min_elevation if self.min_elevation is not None
                         else y_min)

        # Segment length default ≈ 0.3 H (Slide recommendation)
        seg_len = self.segment_length
        if seg_len is None or seg_len <= 0:
            seg_len = max(0.3 * H, (x_right - x_left) * 0.05, 1e-3)

        # Locate the slope face (steepest ground segment) → defines the
        # toe / crest and the Slope-Limits ranges.
        #
        # v0.1.73 — with a strict ``>`` the FIRST steepest segment won,
        # so a symmetric embankment (two faces of equal inclination)
        # always chose the LEFT one, by iteration order and nothing else.
        # That is the one place in this search where the geometry really
        # is ambiguous, and where the Failure Direction is the missing
        # information rather than a second opinion on something already
        # answered: everything below still derives the toe as the lower
        # end of the chosen face, because the reference is explicit that
        # Path Search starts at the toe regardless of the direction.
        slopes = []
        for i in range(len(top) - 1):
            dx = top[i + 1].x - top[i].x
            dy = top[i + 1].y - top[i].y
            if abs(dx) < 1e-9:
                continue
            slopes.append((i, abs(dy / dx)))
        steepest_i = 0
        if slopes:
            steepest = max(s for _, s in slopes)
            # Near-ties only. A face that is genuinely the steepest keeps
            # winning whatever the direction is set to, so an ordinary
            # single-face slope cannot be changed by this setting.
            tied = [i for i, s in slopes if s >= steepest * (1.0 - 1e-6)]
            if len(tied) > 1:
                from .failure_direction import crest_is_on_the_right
                # The mass exits at the toe, so pick the face whose toe
                # lies on the side it is declared to move towards: the
                # left-hand face for a right-to-left failure.
                def _toe_x(i):
                    a, b = top[i], top[i + 1]
                    return a.x if a.y <= b.y else b.x
                steepest_i = (min(tied, key=_toe_x)
                              if crest_is_on_the_right(project)
                              else max(tied, key=_toe_x))
            else:
                steepest_i = tied[0]
        face_a = top[steepest_i]
        face_b = top[steepest_i + 1]
        # Slope angle β (magnitude) of the face
        beta = math.atan2(abs(face_b.y - face_a.y),
                          abs(face_b.x - face_a.x))
        beta_deg = math.degrees(beta)
        # left_low: True if the toe is on the LEFT (ground rises to the
        # right). The toe is the lower end of the slope face.
        left_low = face_a.y <= face_b.y
        toe_pt = face_a if face_a.y <= face_b.y else face_b
        crest_pt = face_b if face_a.y <= face_b.y else face_a
        # Failure progresses from toe to crest. The slip surface moves
        # horizontally from the toe towards the crest.
        to_right = crest_pt.x > toe_pt.x  # crest is to the right of toe

        face_lo_x = min(face_a.x, face_b.x)
        face_hi_x = max(face_a.x, face_b.x)
        face_w = max(face_hi_x - face_lo_x, 1e-6)

        # Initiation range: toe-side portion of the slope face + a small
        # margin onto the adjoining flat (Slope-Limits toe half).
        if to_right:
            init_x0 = max(x_left, toe_pt.x - 0.15 * face_w)
            init_x1 = toe_pt.x + 0.55 * face_w
        else:
            init_x0 = toe_pt.x - 0.55 * face_w
            init_x1 = min(x_right, toe_pt.x + 0.15 * face_w)
            init_x0, init_x1 = min(init_x0, init_x1), max(init_x0, init_x1)

        # Exit range (crest side) — used to filter endpoints.
        if to_right:
            exit_x0 = crest_pt.x - 0.55 * face_w
            exit_x1 = min(x_right, crest_pt.x + 0.6 * face_w)
        else:
            exit_x0 = max(x_left, crest_pt.x - 0.6 * face_w)
            exit_x1 = crest_pt.x + 0.55 * face_w
            exit_x0, exit_x1 = min(exit_x0, exit_x1), max(exit_x0, exit_x1)

        # Initial-angle window (radians), in "descending into slope"
        # terms. Lower = 45° below horizontal; Upper = β − 5°.
        ang_lo = math.radians(self.initial_angle_lower_deg)  # e.g. -45°
        if self.initial_angle_upper_deg is not None:
            ang_hi = math.radians(self.initial_angle_upper_deg)
        else:
            # v0.1.24 FIX (anomaly A1): the documented Upper Angle is
            # +(β − 5)°, NOT −(β − 5)°. In this local frame the +x axis
            # points from the toe towards the crest, so a POSITIVE angle
            # means the first segment RISES as it advances into the
            # slope — which is exactly what a toe-exiting slip surface
            # does (its base is shallow at the toe and steepens towards
            # the crest). Negating the limit collapsed the admissible
            # window to a ~5° sliver of steeply-diving directions
            # ([−45°, −40°] for a 45° face), making the true critical
            # surface geometrically impossible to generate: 97 % of
            # paths were discarded and the reported FoS was ~1.60
            # instead of ~0.88.
            ang_hi = math.radians(max(beta_deg - 5.0, 5.0))
        if ang_lo > ang_hi:
            ang_lo, ang_hi = ang_hi, ang_lo

        # v0.1.24 — per the documented behaviour, "Number of Surfaces" is
        # the number of VALID surfaces generated: invalid ones are
        # discarded and do NOT count towards the total. We therefore keep
        # generating until num_paths valid surfaces exist, capped at
        # max_attempts_factor× attempts so a pathological model cannot
        # spin forever.
        best_surfaces = []
        attempts = 0
        max_attempts = self.num_paths * self.max_attempts_factor
        while result.valid_count < self.num_paths and attempts < max_attempts:
            ip = attempts
            attempts += 1
            if self.progress_cb and ip % 25 == 0:
                self.progress_cb(min(result.valid_count, self.num_paths),
                                 self.num_paths)
            verts = self._generate_path_xstabl(
                rng, top, init_x0, init_x1, exit_x0, exit_x1,
                seg_len, ang_lo, ang_hi, to_right, self._y_floor,
            )
            if verts is None or len(verts) < 3:
                result.invalid_count += 1
                continue
            poly = Polyline(vertices=verts, closed=False)
            surface = SlipSurface(polyline=poly)
            res = self.evaluate_surface(project, surface)
            if res is None:
                result.invalid_count += 1
                continue
            if res.is_valid and not (0.2 <= res.fos <= 100.0):
                result.invalid_count += 1
                continue
            result.evaluations.append(res)
            if res.is_valid:
                result.valid_count += 1
                best_surfaces.append((res.fos, verts))
            else:
                result.invalid_count += 1

        # Surface Altering Optimization on the best few
        if self.optimize and best_surfaces:
            best_surfaces.sort(key=lambda t: t[0])
            for k in range(min(5, len(best_surfaces))):
                _f, verts0 = best_surfaces[k]
                opt = self._optimize_surface(project, list(verts0), rng)
                if opt is not None:
                    result.evaluations.append(opt)
                    if opt.is_valid:
                        result.valid_count += 1

        if self.progress_cb:
            self.progress_cb(self.num_paths, self.num_paths)
        result.attempts = attempts
        return result

    # ------------------------------------------------------------------
    def _generate_path_xstabl(
        self, rng, top, init_x0, init_x1, exit_x0, exit_x1,
        seg_len, ang_lo, ang_hi, to_right, y_floor,
    ):
        """Grow one irregular surface following the XSTABL method.

        Returns a left-to-right-ordered list of Vertex, or None if the
        surface is invalid (doesn't re-emerge in the exit range, goes
        below the floor, or exceeds the segment budget).
        """
        from ogr_core.geometry import Vertex

        # 1. Initiation point on the ground surface
        x_start = rng.uniform(init_x0, init_x1)
        y_start = self._interpolate_top_y(top, x_start)
        if y_start is None:
            return None

        # 2. First segment: random initial angle in the window. The
        #    horizontal march direction is from toe towards crest.
        hdir = 1.0 if to_right else -1.0
        angle = rng.uniform(ang_lo, ang_hi)  # negative = descending
        # Per-surface "depth aggressiveness": controls how long the
        # surface stays deep before turning up. Low → shallow surfaces,
        # high → deep surfaces. Sampling a range gives a good spread of
        # candidate depths so the search finds the true critical one.
        depth_factor = rng.uniform(0.55, 1.6)
        # Build the surface as a list of points marching towards crest.
        pts = [(x_start, y_start)]
        cx, cy = x_start, y_start
        prev_angle = angle
        max_seg = self.max_segments
        emerged = False

        for seg in range(max_seg):
            # March horizontally towards the crest by seg_len projected.
            dx = hdir * seg_len * math.cos(angle)
            dy = seg_len * math.sin(angle)
            nx, ny = cx + dx, cy + dy

            # Floor check
            if ny < y_floor - 1e-9:
                # Clamp the descent: don't go below the floor
                return None

            # Has it re-emerged at/above the ground surface?
            ty = self._interpolate_top_y(top, nx)
            if ty is not None and ny >= ty - 1e-6:
                # Interpolate the exact crossing on the last segment so
                # the surface ends exactly on the ground.
                # Linear solve along the segment for y == ground.
                cross = self._segment_ground_crossing(
                    cx, cy, nx, ny, top)
                if cross is not None:
                    pts.append(cross)
                    emerged = True
                    break
                else:
                    pts.append((nx, ty))
                    emerged = True
                    break

            pts.append((nx, ny))
            cx, cy = nx, ny

            # 3. Next segment angle: rotate upward (towards the crest)
            #    monotonically to stay concave-up / admissible. The turn
            #    rate adapts so the surface aims to re-emerge near the
            #    crest: the closer the horizontal distance to the exit
            #    range, the more strongly it turns up. This keeps the
            #    XSTABL admissibility (monotone upward rotation) while
            #    greatly improving the fraction of surfaces that emerge
            #    inside the Slope Limits.
            crest_target = 0.5 * (exit_x0 + exit_x1)
            remaining = abs(crest_target - cx)
            total = abs(crest_target - x_start) + 1e-9
            progress = max(0.0, min(1.0, 1.0 - remaining / total))
            # depth_factor < 1 → turns up sooner (shallow); > 1 → stays
            # deeper longer (deep-seated). Raising progress to this power
            # shifts the whole turn-up schedule.
            sched = progress ** depth_factor
            target_angle = ang_lo + sched * (math.radians(55.0) - ang_lo)
            jitter = rng.uniform(-0.12, 0.18)
            angle = max(prev_angle, target_angle + jitter)  # monotone up
            angle = min(angle, math.radians(80.0))
            prev_angle = angle

        if not emerged or len(pts) < 3:
            return None

        # 4. Endpoint must be within the exit (crest-side) range
        ex = pts[-1][0]
        if not (min(exit_x0, exit_x1) - 1e-6 <= ex <= max(exit_x0, exit_x1) + 1e-6):
            return None

        # Order left→right
        if pts[0][0] > pts[-1][0]:
            pts = pts[::-1]
        # Enforce strict x-monotonicity (XSTABL surfaces are single-valued
        # in x). Drop any backtracking points.
        mono = [pts[0]]
        for p in pts[1:]:
            if p[0] > mono[-1][0] + 1e-9:
                mono.append(p)
        if len(mono) < 3:
            return None

        # 5. Inside-External validation (definitive guard)
        if self._ext_poly is not None:
            from shapely.geometry import Point as _Pt
            buf = self._ext_poly.buffer(1e-6 * max(
                abs(mono[-1][0] - mono[0][0]), 1.0))
            for (px, py) in mono:
                if not buf.contains(_Pt(px, py)):
                    return None

        # 6. Optional convex-only filter (concave-up admissibility vs the
        #    entry-exit chord)
        if self.convex_only:
            x0, y0 = mono[0]
            xn, yn = mono[-1]
            if xn - x0 > 1e-9:
                for (px, py) in mono[1:-1]:
                    t = (px - x0) / (xn - x0)
                    if py > y0 + t * (yn - y0) + 1e-6:
                        return None

        return [Vertex(px, py) for (px, py) in mono]

    @staticmethod
    def _segment_ground_crossing(x0, y0, x1, y1, top):
        """Find where the segment (x0,y0)->(x1,y1) first crosses the
        ground profile, returning (x, y) or None."""
        # Sample the segment and the ground; find sign change of
        # (seg_y - ground_y).
        N = 12
        prev_t = 0.0
        prev_diff = None
        for i in range(N + 1):
            t = i / N
            sx = x0 + t * (x1 - x0)
            sy = y0 + t * (y1 - y0)
            gy = PathSearch._interpolate_top_y(top, sx)
            if gy is None:
                prev_diff = None
                prev_t = t
                continue
            diff = sy - gy
            if prev_diff is not None and prev_diff < 0 <= diff:
                # Crossing between prev_t and t — bisect a little
                a, b = prev_t, t
                for _ in range(20):
                    m = 0.5 * (a + b)
                    mx = x0 + m * (x1 - x0)
                    my = y0 + m * (y1 - y0)
                    mg = PathSearch._interpolate_top_y(top, mx)
                    if mg is None:
                        break
                    if my - mg < 0:
                        a = m
                    else:
                        b = m
                mx = x0 + b * (x1 - x0)
                mg = PathSearch._interpolate_top_y(top, mx)
                return (mx, mg if mg is not None else y1)
            prev_diff = diff
            prev_t = t
        return None

    # ------------------------------------------------------------------
    def _optimize_surface(self, project, verts, rng):
        """Surface Altering Optimization (random-walk refinement)."""
        from ogr_core.geometry import Polyline, Vertex
        from .surface import SlipSurface

        def _fos_of(vs):
            poly = Polyline(vertices=vs, closed=False)
            surf = SlipSurface(polyline=poly)
            r = self.evaluate_surface(project, surf)
            if r is None or not r.is_valid:
                return None, None
            if not (0.2 <= r.fos <= 100.0):
                return None, None
            return r.fos, r

        cur = list(verts)
        cur_fos, cur_res = _fos_of(cur)
        if cur_fos is None:
            return None
        span = abs(cur[-1].x - cur[0].x)
        step0 = 0.05 * span
        for it in range(self.optimize_iterations):
            step = step0 * (1.0 - it / self.optimize_iterations)
            if len(cur) <= 2:
                break
            idx = rng.randint(1, len(cur) - 2)
            v = cur[idx]
            dy = rng.uniform(-step, step)
            dx = rng.uniform(-0.3 * step, 0.3 * step)
            new_v = Vertex(v.x + dx, v.y + dy)
            trial = list(cur)
            trial[idx] = new_v
            if not (trial[idx - 1].x < trial[idx].x < trial[idx + 1].x):
                continue
            if self._ext_poly is not None:
                from shapely.geometry import Point as _Pt
                if not self._ext_poly.buffer(1e-6 * max(span, 1.0)).contains(
                        _Pt(new_v.x, new_v.y)):
                    continue
            f, r = _fos_of(trial)
            if f is not None and f < cur_fos:
                cur = trial
                cur_fos = f
                cur_res = r
        return cur_res

    # ------------------------------------------------------------------
    @staticmethod
    def _ground_profile(ext_verts):
        """Real upper contour of the External (not the convex hull),
        sorted by x. For each distinct x, the maximum y over all edges.

        v0.1.84 — delegates to :func:`ogr_core.geometry.ground_surface`.
        This was the only one of the project's three ground-surface
        implementations that walked the edges rather than the vertices, so
        it is the one the shared function generalises; keeping a private
        copy here would have re-created the divergence that produced the
        Ej_2 anomaly.
        """
        from ogr_core.geometry import ground_surface
        if len(ext_verts) < 3:
            return list(ext_verts)
        return list(ground_surface(list(ext_verts)).vertices)

    @staticmethod
    def _interpolate_top_y(top_verts, x: float) -> Optional[float]:
        if x < top_verts[0].x - 1e-9 or x > top_verts[-1].x + 1e-9:
            return None
        for v1, v2 in zip(top_verts[:-1], top_verts[1:]):
            if v1.x <= x <= v2.x:
                if abs(v2.x - v1.x) < 1e-12:
                    return max(v1.y, v2.y)
                t = (x - v1.x) / (v2.x - v1.x)
                return v1.y + t * (v2.y - v1.y)
        return None



class SimulatedAnnealingSearch(BaseSearch):
    """Hybrid Simulated Annealing (HSA) Search for non-circular surfaces.

    Implements the algorithm from:
        Su, X. (2009). Global Optimization of General Failure Surfaces
        in Slope Analysis by Hybrid Simulated Annealing.
        University of Waterloo / Rocscience Inc.

    HSA = VFSA (Very Fast Simulated Annealing) + LMC (Local Monte-Carlo).

    Phase 1 — VFSA (global search):
      - Control variables: x_2..x_{N-1} and y_2..y_{N-1} parameterized
        to [0, 1] (endpoints x_1, x_N are fixed on the slope; y_1, y_N
        are computed by interpolating the External top profile at those x)
      - Bounds for x: each x_m lives in division [D_{m-1}, D_m]
      - Bounds for y: dynamic — depend on neighbouring vertices
        (Cheng 2007). y_m_min = ymin of bbox, y_m_max = min(slope,
        line through neighbours) so we don't generate self-intersecting
        surfaces by default.
      - State generation: Cauchy distribution
            r = sgn(u-0.5) · T_gen · [(1 + 1/T_gen)^|2u-1| - 1]
      - Acceptance: 1 / (1 + exp(dE/T_accept))
      - Schedule: T_k = T_0 · exp(-c · k^(1/n)), c=8
      - Ratio control: if accept/reject ratio > 2 → halve T_accept
        (more selective); if < 0.5 → double it (less selective)

    Phase 2 — LMC (local refinement, Greco 1996):
      - For each vertex, try 8 directional moves (N_x, N_y) ∈ {-1,0,1}²
      - On success, repeat the same direction (extrapolation)
      - On failure for all 8 directions of one vertex, shrink that
        vertex's step size by factor (1 - eps), eps=0.75 default
      - Stop when all step sizes < tolerance OR no improvement after
        a full pass over all vertices

    Convex-only mode: rejects candidate surfaces whose curvature
    changes sign (kappa < 0 anywhere), preserving downward-concave
    failure shapes typical of weak-layer slopes.
    """

    def __init__(
        self,
        method,
        initial_vertices: int = 9,
        generation_steps: int = 200,
        tolerance: float = 1e-3,
        temperature_factor: float = 0.97,
        convex_only: bool = False,
        num_slices: int = 30,
        min_area: float = 1.0,
        seed: Optional[int] = 1234,
        progress_cb=None,
        **legacy_kwargs,
    ) -> None:
        super().__init__(
            method=method, num_slices=num_slices,
            reject_tensile=bool(legacy_kwargs.pop('reject_tensile', False)),
            tensile_tolerance=float(
                legacy_kwargs.pop('tensile_tolerance', 0.05)),
            tensile_percent=float(
                legacy_kwargs.pop('tensile_percent', 95.0)),
            check_m_alpha=bool(
                legacy_kwargs.pop('check_m_alpha', True)),
        )
        self.seed = seed
        self.initial_vertices = max(4, initial_vertices)
        self.generation_steps = max(10, generation_steps)
        self.tolerance = tolerance
        # Note: temperature_factor in the UI maps to the c parameter
        # of VFSA (Su 2009). The paper uses c=8.0 but values 1-10 work.
        # We keep the user's parameter as a "speed knob" (closer to 1
        # = more thorough/slower) and translate to c internally.
        self.temperature_factor = max(0.5, min(0.999, temperature_factor))
        self.convex_only = convex_only
        self.min_area = min_area
        self.progress_cb = progress_cb

    # ==================================================================
    # Top-level: HSA = VFSA + LMC
    # ==================================================================
    def _run(self, project) -> SearchResult:
        result = SearchResult(method_id=self.method.METHOD_ID)
        if self.seed is not None:
            import random as _r
            _r.seed(self.seed)
        try:
            xmin, ymin, xmax, ymax = project.bounding_box()
        except Exception:
            return result
        dx = xmax - xmin
        dy = ymax - ymin
        if dx < 1e-3 or dy < 1e-3:
            return result

        # External top profile (slope ground line)
        from ogr_core.geometry import BoundaryType
        ext = None
        for b in project.boundaries:
            if b.btype == BoundaryType.EXTERNAL:
                ext = b
                break
        if ext is None:
            return result
        # Real ground profile (upper contour), reused from PathSearch.
        top = PathSearch._ground_profile(ext.polyline.vertices)
        if len(top) < 2:
            return result

        # External polygon for inside-tests
        self._ext_poly = None
        try:
            from shapely.geometry import Polygon as _Poly
            self._ext_poly = _Poly(
                [(v.x, v.y) for v in ext.polyline.vertices])
            if not self._ext_poly.is_valid:
                self._ext_poly = self._ext_poly.buffer(0)
        except Exception:  # noqa: BLE001
            self._ext_poly = None

        # Locate the slope face (steepest ground segment) → toe / crest.
        steepest_i = 0
        steepest = -1.0
        for i in range(len(top) - 1):
            ddx = top[i + 1].x - top[i].x
            ddy = top[i + 1].y - top[i].y
            if abs(ddx) < 1e-9:
                continue
            s = abs(ddy / ddx)
            if s > steepest:
                steepest = s
                steepest_i = i
        face_a = top[steepest_i]
        face_b = top[steepest_i + 1]
        toe_pt = face_a if face_a.y <= face_b.y else face_b
        crest_pt = face_b if face_a.y <= face_b.y else face_a

        # Fixed slip-surface endpoints near the toe and crest of the
        # slope face (the surface daylights here). These bracket the
        # SA's inner vertices.
        N = self.initial_vertices
        x1 = min(toe_pt.x, crest_pt.x)
        xN = max(toe_pt.x, crest_pt.x)
        # Small inward margin so endpoints sit on the slope, not exactly
        # on a corner
        face_w = max(xN - x1, 1e-6)
        x1 = x1 - 0.0 * face_w
        xN = xN + 0.0 * face_w

        # Phase 1 — VFSA
        best_verts, best_fos = self._vfsa(
            project, result, x1, xN, ymin, ymax, top, N, dx, dy,
        )

        # Phase 2 — LMC (local refinement, only if VFSA produced something)
        if best_verts is not None:
            best_verts, best_fos = self._lmc(
                project, result, best_verts, best_fos, ymin, ymax, top, dx,
            )

        if self.progress_cb:
            self.progress_cb(self.generation_steps, self.generation_steps)
        return result

    # ==================================================================
    # Helpers
    # ==================================================================
    @staticmethod
    def _interp_top_y(top, x):
        if x < top[0].x or x > top[-1].x:
            return None
        for v1, v2 in zip(top[:-1], top[1:]):
            if v1.x <= x <= v2.x:
                if abs(v2.x - v1.x) < 1e-12:
                    return (v1.y + v2.y) / 2.0
                t = (x - v1.x) / (v2.x - v1.x)
                return v1.y + t * (v2.y - v1.y)
        return None

    @staticmethod
    def _is_convex(verts):
        """Check that the polyline is convex (downward-concave) — i.e.
        no sign changes in the cross-product of consecutive segments."""
        if len(verts) < 3:
            return True
        sign = None
        for i in range(1, len(verts) - 1):
            ax = verts[i].x - verts[i - 1].x
            ay = verts[i].y - verts[i - 1].y
            bx = verts[i + 1].x - verts[i].x
            by = verts[i + 1].y - verts[i].y
            cross = ax * by - ay * bx
            if abs(cross) < 1e-9:
                continue
            s = 1 if cross > 0 else -1
            if sign is None:
                sign = s
            elif s != sign:
                return False
        return True

    @staticmethod
    def _cauchy_step(u, T_gen):
        """VFSA Cauchy generator — Eq (8) in Su 2009.

            r = sgn(u-0.5) · T · [(1 + 1/T)^|2u-1| - 1]
        """
        sign = 1.0 if u >= 0.5 else -1.0
        # Numerical guard: T_gen very small → (1 + 1/T_gen) huge → overflow
        T = max(T_gen, 1e-6)
        try:
            base = 1.0 + 1.0 / T
            exponent = abs(2 * u - 1)
            # Clamp exponential argument to avoid overflow
            log_val = exponent * math.log(base)
            if log_val > 50:
                power = math.exp(50)
            else:
                power = math.exp(log_val)
            return sign * T * (power - 1.0)
        except (OverflowError, ValueError):
            # Fall back to a small random step
            return sign * T * 0.1

    def _evaluate_polyline(self, project, verts):
        """Evaluate the candidate non-circular surface. Returns
        (LEMResult, fos) or (None, None) if invalid/unphysical.

        v0.1.17 — added the same physical-admissibility guards used by
        the Path and Block searches, to stop the SA from chasing
        degenerate surfaces (tiny slivers, sawtooth shapes) that yield
        spurious sub-unity FoS values.
        """
        from ogr_core.geometry import Polyline
        from .surface import SlipSurface
        if len(verts) < 3:
            return None, None
        if self.convex_only and not self._is_convex(verts):
            return None, None

        # (a) strictly increasing in x (single-valued surface)
        for a, b in zip(verts[:-1], verts[1:]):
            if b.x <= a.x + 1e-9:
                return None, None

        # (b) interior vertices must lie below the entry-exit chord
        #     (concave-up / kinematically admissible slip mass)
        x0v, y0v = verts[0].x, verts[0].y
        xnv, ynv = verts[-1].x, verts[-1].y
        if xnv - x0v > 1e-9:
            for vv in verts[1:-1]:
                tt = (vv.x - x0v) / (xnv - x0v)
                chord = y0v + tt * (ynv - y0v)
                if vv.y > chord + 1e-6:
                    return None, None

        # (c) unimodal (single valley): y descends to a minimum then
        #     ascends — rejects sawtooth wedge shapes
        ys = [v.y for v in verts]
        imin = ys.index(min(ys))
        for a in range(1, imin + 1):
            if ys[a] > ys[a - 1] + 1e-6:
                return None, None
        for a in range(imin + 1, len(ys)):
            if ys[a] < ys[a - 1] - 1e-6:
                return None, None

        # (d) minimum area of the sliding mass (reject slivers)
        area = 0.0
        for a, b in zip(verts[:-1], verts[1:]):
            # area between chord-top and surface (trapezoids vs entry-exit
            # chord); use simple |∫(chord - surface) dx|
            tt0 = (a.x - x0v) / (xnv - x0v) if xnv > x0v else 0.0
            tt1 = (b.x - x0v) / (xnv - x0v) if xnv > x0v else 0.0
            c0 = y0v + tt0 * (ynv - y0v)
            c1 = y0v + tt1 * (ynv - y0v)
            area += 0.5 * ((c0 - a.y) + (c1 - b.y)) * (b.x - a.x)
        if abs(area) < max(self.min_area, 0.5):
            return None, None

        # (e) every vertex inside the External polygon (definitive guard
        #     against surfaces poking outside the soil mass)
        if getattr(self, "_ext_poly", None) is not None:
            from shapely.geometry import Point as _Pt
            buf = self._ext_poly.buffer(1e-6 * max(xnv - x0v, 1.0))
            for vv in verts:
                if not buf.contains(_Pt(vv.x, vv.y)):
                    return None, None

        poly = Polyline(vertices=verts, closed=False)
        surface = SlipSurface(polyline=poly)
        res = self.evaluate_surface(project, surface)
        if res is None or not res.is_valid:
            return None, None
        if not (0.5 <= res.fos <= 100.0):
            return None, None
        return res, res.fos

    # ==================================================================
    # Phase 1 — Very Fast Simulated Annealing
    # ==================================================================
    @staticmethod
    def _bootstrap_parameters(n_inner, D, top, y_floor, dy, ymax,
                              x1, xN, y1, yN, rng, attempt):
        """Parameters of an admissible starting surface.

        The inner vertices are placed on a bowl hanging below the chord
        that joins the entry and exit points:

            y(t) = chord(t) - depth * sin(pi * t) ** power

        which is single-valued in x, lies below the chord and has ONE
        low point — the three conditions the admissibility filters check.
        ``depth`` and ``power`` are randomised (and the depth is shrunk
        on successive attempts) so the bootstrap still explores, while
        every candidate it produces is valid by construction.

        Returns the ``(P_X, P_Y)`` parameters in [0, 1] expected by the
        annealing, so the search continues from here unchanged.
        """
        import math as _m

        depth_cap = max(1e-6, y1 - y_floor if y1 > y_floor else 1.0)
        depth_cap = max(depth_cap, max(y1, yN) - y_floor)
        # Shrink with the attempt number: a shallower bowl always fits
        depth = depth_cap * (0.65 * (0.85 ** attempt)) * (
            0.6 + 0.4 * rng.random())
        power = 0.8 + 1.4 * rng.random()
        skew = 0.35 + 0.3 * rng.random()      # position of the low point

        P_X = []
        P_Y = []
        for m in range(1, n_inner + 1):
            # Keep x near the middle of its division, with mild jitter
            px = 0.35 + 0.3 * rng.random()
            P_X.append(px)
            xm = D[m - 1] + px * (D[m] - D[m - 1])
            t = (xm - x1) / max(xN - x1, 1e-9)
            chord = y1 + t * (yN - y1)
            # Asymmetric bowl: warp t so the low point sits at ``skew``
            tw = t ** (_m.log(0.5) / _m.log(max(skew, 1e-6))) \
                if 0 < skew < 1 else t
            drop = depth * (_m.sin(_m.pi * min(max(tw, 0.0), 1.0))
                            ** power)
            ym = chord - drop

            top_y_here = SimulatedAnnealingSearch._interp_top_y(top, xm)
            y_top = top_y_here if top_y_here is not None else ymax
            ym_max = y_top - 0.05 * dy
            ym_min = y_floor
            if ym_max <= ym_min:
                ym_max = ym_min + 0.1
            ym = min(max(ym, ym_min + 1e-9), ym_max - 1e-9)
            P_Y.append((ym - ym_min) / max(ym_max - ym_min, 1e-12))
        return P_X, P_Y

    def _vfsa(self, project, result, x1, xN, ymin, ymax, top, N, dx, dy):
        """Run the VFSA loop. Returns (best_verts, best_fos)."""
        import random
        from ogr_core.geometry import Vertex

        # Slope endpoint y-values (snap to top profile)
        y1 = self._interp_top_y(top, x1)
        yN = self._interp_top_y(top, xN)
        if y1 is None or yN is None:
            return None, None

        # Equi-divisions for x-bounds (Eq. 3 in Su 2009)
        # We have N vertices, so N-2 inner ones, with N-1 divisions
        D = [x1 + i * (xN - x1) / (N - 1) for i in range(N)]

        # Bounds for inner y. The lower bound must NOT plunge to the
        # bottom of the bounding box (that produces absurdly deep, narrow
        # surfaces with spurious sub-unity FoS). v0.1.17 — clamp the
        # floor near the toe elevation, allowing the surface to dip a
        # reasonable fraction of the slope height below the toe.
        y_toe = min(self._interp_top_y(top, x1) or ymin,
                    self._interp_top_y(top, xN) or ymin)
        slope_h = ymax - y_toe
        y_floor = y_toe - 0.15 * max(slope_h, 1.0)
        y_floor = max(y_floor, ymin)

        def _denormalize(P_X, P_Y):
            """Convert parameterised values in [0,1] to actual (x, y)
            coords for inner vertices."""
            inner = []
            for m in range(1, N - 1):
                # x_m within division [D_{m-1}, D_m]
                # Wait — paper says D_m = x1 + (m-1)*(xN-x1)/(N-2)
                # so for m=1 first inner vertex, x in [D_0, D_1]
                xm = D[m - 1] + P_X[m - 1] * (D[m] - D[m - 1])
                # Dynamic upper bound for y_m: interpolation between
                # neighbours (or top profile) prevents auto-intersection
                top_y_here = self._interp_top_y(top, xm)
                y_top = top_y_here if top_y_here is not None else ymax
                ym_max = y_top - 0.05 * dy  # below ground surface
                ym_min = y_floor
                if ym_max <= ym_min:
                    ym_max = ym_min + 0.1
                ym = ym_min + P_Y[m - 1] * (ym_max - ym_min)
                inner.append(Vertex(xm, ym))
            return [Vertex(x1, y1)] + inner + [Vertex(xN, yN)]

        # Initialize parameters (all in [0,1])
        n_inner = N - 2
        n = 2 * n_inner  # total control variables
        P_X = [random.random() for _ in range(n_inner)]
        P_Y = [random.random() for _ in range(n_inner)]

        # Bootstrap: build a valid initial surface.
        #
        # v0.1.39 (anomaly A5) — the previous bootstrap drew every inner
        # vertex INDEPENDENTLY at random and relied on the result
        # happening to pass the admissibility filters. The decisive one
        # is unimodality (the surface must descend to a single low point
        # and then rise): for n independently ordered values the chance
        # of that is about 2^(n-1)/n!, i.e. well under 1 % for the
        # default 9 vertices. The search therefore failed COMPLETELY for
        # unlucky seeds — 200 rejections and not a single evaluation —
        # which is exactly the reported anomaly.
        #
        # The fix is to construct the starting surface so that it
        # satisfies the constraints BY CONSTRUCTION: a bowl hanging below
        # the entry-exit chord, whose depth profile is a single smooth
        # arc. Randomness now controls the depth and the asymmetry of the
        # bowl instead of each vertex independently, so every draw is
        # admissible and the annealing always has somewhere to start.
        best_verts = None
        best_fos = None
        for attempt in range(60):
            P_X, P_Y = self._bootstrap_parameters(
                n_inner, D, top, y_floor, dy, ymax, x1, xN, y1, yN,
                random, attempt)
            verts = _denormalize(P_X, P_Y)
            r, f = self._evaluate_polyline(project, verts)
            if r is not None:
                best_verts = verts
                best_fos = f
                result.evaluations.append(r)
                result.valid_count += 1
                break
        if best_verts is None:
            # Last resort: the plain random draw, in case an unusual
            # geometry defeats the constructed bowl.
            for _ in range(200):
                P_X = [random.random() for _ in range(n_inner)]
                P_Y = [random.random() for _ in range(n_inner)]
                verts = _denormalize(P_X, P_Y)
                r, f = self._evaluate_polyline(project, verts)
                if r is not None:
                    best_verts = verts
                    best_fos = f
                    result.evaluations.append(r)
                    result.valid_count += 1
                    break
        if best_verts is None:
            return None, None

        # Initial temperatures (Su 2009 Section 2.1.3)
        T_gen = 1.0
        T_accept = best_fos  # initial acceptance T = current FoS
        c = 8.0  # paper-recommended; user's temperature_factor influences cooling

        # External annealing iterations
        K = max(4, int(self.generation_steps / 50))  # outer loop count
        Ngen0 = max(20, self.generation_steps // K)  # inner loop size

        no_improve_passes = 0
        last_best = best_fos

        for k in range(1, K + 1):
            n_accepted = 0
            n_rejected = 0
            # Inner loop: Ngen Cauchy random walks (paper has Ngen ~ 1000n
            # but we scale to user's generation_steps)
            Ngen = max(10, Ngen0 // (2 ** (k - 1)))

            for _ in range(Ngen):
                # Cauchy random walk for ALL control variables
                cand_X = list(P_X)
                cand_Y = list(P_Y)
                for i in range(n_inner):
                    u = random.random()
                    r_step = self._cauchy_step(u, T_gen)
                    new_p = cand_X[i] + r_step
                    # Bounds check (Section 2.1.9): truncate to [0, 1]
                    cand_X[i] = max(0.001, min(0.999, new_p))
                for i in range(n_inner):
                    u = random.random()
                    r_step = self._cauchy_step(u, T_gen)
                    new_p = cand_Y[i] + r_step
                    cand_Y[i] = max(0.001, min(0.999, new_p))

                verts = _denormalize(cand_X, cand_Y)
                r, f = self._evaluate_polyline(project, verts)
                if r is None:
                    continue
                result.evaluations.append(r)
                result.valid_count += 1

                # Acceptance: Eq (9) in Su 2009
                dE = f - best_fos
                if dE <= 0:
                    P_accept = 1.0
                else:
                    # Guard against overflow when T_accept is very small
                    arg = dE / max(T_accept, 1e-9)
                    if arg > 50:
                        P_accept = 0.0
                    else:
                        P_accept = 1.0 / (1.0 + math.exp(arg))
                if random.random() <= P_accept:
                    P_X = cand_X
                    P_Y = cand_Y
                    if f < best_fos - self.tolerance:
                        best_fos = f
                        best_verts = verts
                    n_accepted += 1
                else:
                    n_rejected += 1

            # ---- Schedule (Eqs 10-11) ----
            try:
                exp_arg = -c * (k ** (1.0 / max(n, 1)))
                exp_arg = max(-50.0, exp_arg)
                cooling = math.exp(exp_arg)
            except (OverflowError, ValueError):
                cooling = 0.5
            T_accept = max(1e-6, T_accept * cooling)
            T_gen = max(1e-6, T_gen * cooling)

            # ---- Ratio control (Section 2.1.8) ----
            if n_rejected > 0:
                ratio = n_accepted / n_rejected
                if ratio > 2.0:
                    T_accept *= 0.5
                elif ratio < 0.5:
                    T_accept *= 2.0

            # ---- Stopping criterion (Section 2.1.7) ----
            if best_fos < last_best - self.tolerance:
                last_best = best_fos
                no_improve_passes = 0
            else:
                no_improve_passes += 1
            if no_improve_passes >= 3:
                break

            if self.progress_cb:
                self.progress_cb(k * Ngen0, K * Ngen0)

        return best_verts, best_fos

    # ==================================================================
    # Phase 2 — Local Monte-Carlo (Greco 1996, Su 2009 Section 2.2)
    # ==================================================================
    def _lmc(
        self, project, result, verts, fos, ymin, ymax, top, dx,
    ):
        """Local Monte-Carlo refinement of the surface from VFSA."""
        import random
        from ogr_core.geometry import Vertex

        if len(verts) < 4:
            return verts, fos

        # Step sizes per vertex (one per (vertex, axis))
        # Initial step ~ 5% of dx
        step_x = [0.05 * dx for _ in verts]
        step_y = [0.05 * dx for _ in verts]
        eps = 0.75   # step reduction factor per Su 2009
        min_step = self.tolerance * dx * 0.1

        # 8 cardinal+diagonal directions
        DIRS = [
            (-1, -1), (-1, 0), (-1, 1),
            ( 0, -1),          ( 0, 1),
            ( 1, -1), ( 1, 0), ( 1, 1),
        ]

        max_passes = 15  # hard cap on outer LMC passes
        max_total_evals = 2 * self.generation_steps  # hard cap on # of evals
        evals_done = 0

        for pass_idx in range(max_passes):
            improved_anywhere = False
            for i in range(1, len(verts) - 1):  # skip slope endpoints
                if evals_done >= max_total_evals:
                    return verts, fos

                # Skip vertex if its step has already shrunk below threshold
                if step_x[i] < min_step and step_y[i] < min_step:
                    continue

                # ---- Exploration phase ----
                best_dir = None
                best_local_fos = fos
                best_cand = None
                Rx = random.uniform(-0.5, 0.5)
                Ry = random.uniform(-0.5, 0.5)
                if abs(Rx) < 0.1: Rx = 0.1 if Rx >= 0 else -0.1
                if abs(Ry) < 0.1: Ry = 0.1 if Ry >= 0 else -0.1

                for (Nx, Ny) in DIRS:
                    if Nx == 0 and Ny == 0:
                        continue
                    cand = [Vertex(v.x, v.y) for v in verts]
                    cand[i] = Vertex(
                        cand[i].x + Nx * Rx * step_x[i],
                        cand[i].y + Ny * Ry * step_y[i],
                    )
                    # Keep monotonically increasing x
                    if cand[i].x <= cand[i - 1].x or cand[i].x >= cand[i + 1].x:
                        continue
                    r, f = self._evaluate_polyline(project, cand)
                    evals_done += 1
                    if r is None:
                        continue
                    result.evaluations.append(r)
                    result.valid_count += 1
                    if f < best_local_fos - self.tolerance:
                        best_local_fos = f
                        best_dir = (Nx, Ny)
                        best_cand = cand
                    if evals_done >= max_total_evals:
                        if best_cand is not None:
                            verts = best_cand
                            fos = best_local_fos
                        return verts, fos

                if best_cand is not None:
                    # ---- Extrapolation phase ----
                    verts = best_cand
                    fos = best_local_fos
                    improved_anywhere = True
                    Nx, Ny = best_dir
                    for _ in range(5):  # cap extrapolation
                        if evals_done >= max_total_evals:
                            return verts, fos
                        cand = [Vertex(v.x, v.y) for v in verts]
                        cand[i] = Vertex(
                            cand[i].x + Nx * Rx * step_x[i],
                            cand[i].y + Ny * Ry * step_y[i],
                        )
                        if cand[i].x <= cand[i - 1].x or cand[i].x >= cand[i + 1].x:
                            break
                        r, f = self._evaluate_polyline(project, cand)
                        evals_done += 1
                        if r is None or f >= fos - self.tolerance:
                            break
                        result.evaluations.append(r)
                        result.valid_count += 1
                        verts = cand
                        fos = f
                else:
                    # No direction improved → shrink steps for this vertex
                    step_x[i] *= (1.0 - eps)
                    step_y[i] *= (1.0 - eps)

            if not improved_anywhere:
                # Check if all step sizes are below threshold
                all_done = all(
                    step_x[i] < min_step and step_y[i] < min_step
                    for i in range(1, len(verts) - 1)
                )
                if all_done:
                    break

        return verts, fos

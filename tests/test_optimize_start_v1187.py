# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""Where the optimisation's ``null`` actually comes from (D161).

THE INVARIANT THIS FILE PROTECTS is that a walk which cannot start says
WHICH of the two ways it failed, and that the surface it hands back is
the one its result describes.

D161 WAS WRITTEN ON A PREMISE THAT IS FALSE, and the first class here
executes the refutation rather than asserting it in prose. The defect
was recorded as "the walk steps onto a surface it cannot evaluate and
returns null instead of keeping the last one that worked". It cannot:
``_score`` returns ``None`` for such a candidate and the loop does
``continue`` without touching ``best_pts`` or ``best_res``, so no
unevaluable step is ever taken. The ``null`` is born at the DOOR — the
starting surface is densified to ``densify_to`` points, evaluated once,
and if that fails the function returns before the first step.

AND THE TWO WAYS IT CAN FAIL SAY OPPOSITE THINGS:

  * no result at all — the slicer refused the polyline whole, which
    since v0.1.100 is what happens when it rises above the ground
    ANYWHERE. The factor is MISSING, and the cause is usually upstream;
  * a result WITHOUT a factor — the surface is fine and the method has
    no answer for it. Nothing is missing: that IS the answer.

Until v0.1.187 both wrote the same sentence, and a consumer reading it
had no way to tell a gap from an answer. Measured on the verification
bank, of the nine rows with no optimised factor, EIGHT are the first
kind and arrive from upstream (three from a surface degraded by rounding,
five from a composite surface's drawing being handed over as if it were a
surface) and exactly ONE is the second.

WHY NOTHING HERE IS A SNAPSHOT. The rejection rule that makes the first
case deterministic is external and measured: ``BaseSearch.
evaluate_surface`` documents it on verification problem 27 (Malkawi &
Sarma 2001), where "a vertex lifted 0.05 ft over the ground is already
enough" to have the polyline discarded. No assertion below records a
factor of safety.
"""
H, TOE, CREST = 12.0, 30.0, 50.0
SEMILLA = 20260819


# ----------------------------------------------------------------------
def _slope():
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material, MohrCoulomb
    from ogr_core.project import Project
    ext = Polyline(vertices=[
        Vertex(0, -10.0), Vertex(60, -10.0), Vertex(60, H),
        Vertex(CREST, H), Vertex(TOE, 0), Vertex(0, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("optimize-start")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="Soil", unit_weight=18,
                            strength=MohrCoulomb(cohesion=8,
                                                 friction_angle=20))]
    return p


def _search(project, method_id="bishop_simplified"):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.search import PathSearch
    return PathSearch(method=method_registry()[method_id](),
                      num_vertices=6, num_surfaces=20, num_slices=20,
                      seed=10116)


def _surface(points):
    from ogr_core.geometry import Polyline, Vertex
    from ogr_slip2d.surface import SlipSurface
    return SlipSurface(polyline=Polyline(
        vertices=[Vertex(x, y) for x, y in points], closed=False))


def _face_y(x):
    """The slope face, ``y = (x - TOE) * H / (CREST - TOE)``.

    Written as a function and not as a number because the first version
    of this file lifted a vertex to a height it had guessed, the guess
    was BELOW the face, and the surface evaluated perfectly. A test that
    means to break something has to compute where the edge is.
    """
    return (x - TOE) * H / (CREST - TOE)


def _good_start():
    """A surface that slices and evaluates: entry and exit on the ground.

    Endpoints ON the profile and the middle well below it, which is what
    the generator produces and what the walk expects to be handed.
    """
    return [(10.0, 0.0), (20.0, -5.0), (32.0, -6.0), (44.0, 4.8),
            (CREST, H)]


def _walk(project, search, points, **kw):
    from ogr_slip2d.optimize import OptimizeSettings, optimize_surface
    opts = OptimizeSettings(seed=SEMILLA, **kw)
    return optimize_surface(project, search, _surface(points), opts)


# ======================================================================
class TestTheWalkNeverAcceptsAnUnevaluableStep:
    """The refutation of D161's premise, executed.

    Every candidate after the first is refused, so if the walk could
    move onto one it cannot evaluate, it would. It does not move at all.
    """

    def test_the_best_never_leaves_the_starting_surface(self):
        p = _slope()
        s = _search(p)
        original = s.evaluate_surface
        primera = {"hecho": False}

        def solo_la_partida(project, surface, _o=original, _f=primera):
            if not _f["hecho"]:
                _f["hecho"] = True
                return _o(project, surface)
            return None

        s.evaluate_surface = solo_la_partida
        try:
            surf, res, rep = _walk(p, s, _good_start(), densify_to=0)
        finally:
            s.evaluate_surface = original
        assert res is not None and res.is_valid, "the start did not evaluate"
        assert rep.accepted == 0, rep.accepted
        assert rep.iterations > 0, "no candidate was ever scored"
        assert rep.final_fos == rep.initial_fos, (rep.final_fos,
                                                  rep.initial_fos)
        entregados = [(round(v.x, 9), round(v.y, 9))
                      for v in surf.polyline.vertices]
        assert entregados == [(round(x, 9), round(y, 9))
                              for x, y in _good_start()]

    def test_and_the_report_arithmetic_still_holds(self):
        """``accepted + rejected == iterations``, which is what says the
        skipped candidates were counted rather than lost."""
        p = _slope()
        s = _search(p)
        original = s.evaluate_surface
        primera = {"hecho": False}

        def solo_la_partida(project, surface, _o=original, _f=primera):
            if not _f["hecho"]:
                _f["hecho"] = True
                return _o(project, surface)
            return None

        s.evaluate_surface = solo_la_partida
        try:
            _surf, _res, rep = _walk(p, s, _good_start(), densify_to=0)
        finally:
            s.evaluate_surface = original
        assert rep.accepted + rep.rejected == rep.iterations


# ======================================================================
class TestTheNullHasTwoCausesAndTheyAreTwoSentences:
    """The repair of v0.1.187, one class per half of the sentence."""

    def test_a_surface_the_slicer_refuses_says_so(self):
        """Lift one interior vertex over the ground and the WHOLE
        polyline is refused — the rule of v0.1.100, measured there on
        verification problem 27."""
        p = _slope()
        s = _search(p)
        pts = _good_start()
        # 1e-3 above the face, which is twenty times smaller than the
        # 0.05 ft the reference measurement used and still enough.
        pts[3] = (44.0, _face_y(44.0) + 1e-3)
        _surf, res, rep = _walk(p, s, pts, densify_to=0)
        assert res is None, "the lifted surface still evaluated"
        assert "error" in rep.notes
        assert "refused it whole" in rep.notes["error"], rep.notes["error"]
        assert "start_invalid" not in rep.notes

    def test_a_surface_with_no_factor_says_the_opposite(self):
        """A start that slices fine and whose METHOD has no answer.

        The evaluator is replaced by one that returns a declared failure
        — ``converged=False`` with a reason, which is the only shape
        ``LEMResult`` permits since D56. That is the 085 row of the bank,
        and the note has to say the number is not missing.
        """
        p = _slope()
        s = _search(p)
        real = s.evaluate_surface

        def sin_factor(project, surface, _r=real):
            base = _r(project, surface)
            if base is None:
                return None
            from dataclasses import replace as _replace
            return _replace(base, converged=False,
                            error_message="Spencer: no lambda-bracket")

        s.evaluate_surface = sin_factor
        try:
            _surf, res, rep = _walk(p, s, _good_start(), densify_to=0)
        finally:
            s.evaluate_surface = real
        assert res is not None and not res.is_valid
        assert "start_invalid" in rep.notes, rep.notes
        assert "lambda-bracket" in rep.notes["start_invalid"]
        # ``error`` keeps its name in both cases: the menu action of the
        # interface short-circuits on it.
        assert "error" in rep.notes
        assert "it is the answer" in rep.notes["error"], rep.notes["error"]

    def test_the_two_notes_are_never_both_the_same(self):
        """Guard on the guard: if the two branches ever wrote the same
        sentence again, this is what would notice."""
        p = _slope()
        s = _search(p)
        pts = _good_start()
        pts[3] = (44.0, _face_y(44.0) + 1e-3)
        _s1, _r1, roto = _walk(p, s, pts, densify_to=0)

        real = s.evaluate_surface

        def sin_factor(project, surface, _r=real):
            base = _r(project, surface)
            if base is None:
                return None
            from dataclasses import replace as _replace
            return _replace(base, converged=False,
                            error_message="Spencer: no lambda-bracket")

        s.evaluate_surface = sin_factor
        try:
            _s2, _r2, sin = _walk(p, s, _good_start(), densify_to=0)
        finally:
            s.evaluate_surface = real
        assert roto.notes["error"] != sin.notes["error"]


# ======================================================================
class TestTheReturnedSurfaceIsTheOneThatWasEvaluated:
    """The return used to describe a different surface from its result."""

    def test_a_failed_start_hands_back_the_densified_points(self):
        p = _slope()
        s = _search(p)
        pts = _good_start()
        pts[3] = (44.0, _face_y(44.0) + 1e-3)
        surf, res, rep = _walk(p, s, pts, densify_to=12)
        assert res is None
        assert len(surf.polyline.vertices) == 12, len(surf.polyline.vertices)
        assert rep.notes.get("start_densified_to") == 12, rep.notes

    def test_and_says_nothing_about_densifying_when_it_did_not(self):
        """Rule 7 in its smallest form: a key that is always there says
        nothing. With ``densify_to=0`` the surface is untouched and the
        note must be absent."""
        p = _slope()
        s = _search(p)
        pts = _good_start()
        pts[3] = (44.0, _face_y(44.0) + 1e-3)
        surf, _res, rep = _walk(p, s, pts, densify_to=0)
        assert len(surf.polyline.vertices) == len(pts)
        assert "start_densified_to" not in rep.notes


# ======================================================================
class TestTheSearchSaysWhatItSkipped:
    """``_optimize_result`` used to swallow both causes in one
    ``continue``, while the menu action of the interface warned."""

    def test_a_search_whose_walks_fail_leaves_a_note(self):
        from ogr_slip2d.optimize import OptimizeSettings
        p = _slope()
        s = _search(p)
        s.optimize = OptimizeSettings(enabled=True, seed=SEMILLA)
        s.optimize_seed = SEMILLA
        # ``_optimize_result`` imports the function inside its own body,
        # so the module attribute is what it resolves at call time.
        import ogr_slip2d.optimize as opt_mod
        original = opt_mod.optimize_surface

        def falla(project, evaluator, surface, settings=None):
            from ogr_slip2d.optimize import OptimizeReport
            rep = OptimizeReport()
            rep.notes["error"] = "forced for the test"
            return surface, None, rep

        opt_mod.optimize_surface = falla
        try:
            r = s.run(p)
        finally:
            opt_mod.optimize_surface = original
        texto = " ".join(r.notes)
        assert "Optimize Surfaces walked" in texto, r.notes
        assert "could not evaluate the starting surface" in texto, r.notes

    def test_and_says_nothing_when_every_walk_worked(self):
        """Rule 7 the other way round: a note on every analysis is noise,
        and the notes of v0.1.143 and v0.1.151 set the precedent."""
        from ogr_slip2d.optimize import OptimizeSettings
        p = _slope()
        s = _search(p)
        s.optimize = OptimizeSettings(enabled=True, seed=SEMILLA)
        s.optimize_seed = SEMILLA
        r = s.run(p)
        texto = " ".join(r.notes)
        assert "Optimize Surfaces walked" not in texto, r.notes


# ======================================================================
class TestACompositeIsNotAPolylineAndIsNotWalked:
    """Five of the nine bank rows, turned into an invariant.

    The engine already refuses to walk a composite surface, and the
    reason is a contract written in ``surface.py``: the vertex list a
    composite reports is a PICTURE of it, not the surface the slicer
    works on. Only the bank reconstructed that picture as a bare
    polyline and handed it over. This is what says the engine's side is
    correct, so the repair belongs there and not here.
    """

    def test_a_composite_has_no_polyline_to_move(self):
        from ogr_slip2d.surface import CompositeSurface
        campos = getattr(CompositeSurface, "__dataclass_fields__", {})
        assert "polyline" not in campos, sorted(campos)

    def test_the_contract_of_the_vertex_list_is_written_down(self):
        """The claim rests on a docstring, so the docstring is the thing
        to protect: if it ever stops saying this, the reasoning above
        stops holding and someone has to look again."""
        import inspect
        from ogr_slip2d.surface import CompositeSurface
        doc = inspect.getdoc(CompositeSurface.drawing_vertices) or ""
        assert "PICTURE" in doc, doc[:200]

    def test_and_the_optimiser_drops_anything_without_one(self):
        p = _slope()
        s = _search(p)

        class _SinPolilinea:
            polyline = None

        class _Resultado:
            is_valid = True
            admissible = True
            fos = 1.0
            surface = _SinPolilinea()

        class _Result:
            evaluations = [_Resultado()]
            minima = []

            @property
            def critical(self):
                return self.evaluations[0]

        assert s._surfaces_to_optimize(_Result()) == []

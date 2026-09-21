# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""v0.1.185 (D155) — THE EVALUATOR DOES NOT STEER the non-circular path
search. It decides which of the surfaces it generates is ELIGIBLE, and where
the generation stops.

WHAT INVARIANT THIS PROTECTS, and it is the opposite of what the ficha says.
Bank defect D155 reports that verification problem 85 moved +37,03 % and
+11,90 % between 0.1.178 and 0.1.181 on its two non-circular halves, and
explains it by saying the path search is *guided*: that the surfaces it
generates depend on the factors of safety it obtains, so any change in the
evaluator sends it down another trajectory. **That premise is false**, and
three measurements say so.

  * ``bishop_simplified`` on those two halves is
    IDENTICAL between the two versions — 36559 generated, 5000 valid, 31559
    invalid, 1,505885, and even 1,429714 after optimisation. Bishop does not
    touch ``interslice.py``, so if the trajectory were steered by the
    evaluator this row would have moved with the rest of the file.
  * Replaying the generator with ``evaluate_surface`` patched to return
    ``None`` — 100 000 attempts, 17 s — finds BOTH critical surfaces, the one
    0.1.178 published and the one 0.1.181 publishes, in the SAME sequence:
    indices 5075 and 6514 on the passive half, 11994 and 17629 on the active
    one, matched to 6e-5, which is the rounding of the archived JSON.
  * The new run is SHORTER, not different: 38461 attempts against 34175 on
    the passive half and 73009 against 65138 on the active one. Both critical
    indices are far inside the shorter run, so the truncation is not what lost
    the surface either.

WHAT ACTUALLY MOVED. The surface 0.1.178 published is generated today,
evaluated today and sitting in ``result.evaluations`` today. It scores
1,513872 with ``is_valid`` TRUE — and ``admissible`` FALSE.
``is_valid`` IS NOT THE PREDICATE:
``SearchResult.critical`` builds ``ok`` from the valid AND admissible ones
and falls back to the whole valid set only when ``ok`` is empty
(``pool = ok or valid``). With 2907 of 5000 surfaces inadmissible in
that run, ``ok`` is not empty and the old minimum is excluded — correctly, by
a preference the engine has applied since v0.1.130. The ficha measured
``is_valid``, which is the predicate of a different question.

THE ATTRIBUTION, and it is not the version the ficha names. Turning the
switches of ``interslice.py`` off one at a time on that surface:
``BRANCH_PAIR_TIGHTEN`` alone brings back ``admissible`` TRUE, λ = 1,0 and
1,512355 against the 1,512356 archived; none of the other seven that post-date
the file returns the flag. That switch is D145, **v0.1.179** — not D148 /
v0.1.181, which is where the ficha puts it. What it moves is small and what
it decides is not: the factor goes
+0,10 % and the interior thrust resultant goes from +2214 kN/m to −22076, a
sign change. The factor is insensitive to λ near the answer and the thrust is
not, and the thrust is what the boolean reads.

WHY THAT MAKES THIS FILE A CHARACTERISATION AND NOT A REPAIR. The remedy the
ficha offers — multiple starts, or seeding the trajectory with the best of the
previous run — cannot move this row, and
``TestMultiStartCannotRecoverADisqualifiedSurface`` is that argument executed:
the surface is ALREADY in the list, and putting it there again through the one
channel that exists for injected surfaces changes nothing while the flag says
what it says. Adding it would be a setting that moves no number, which is
rule 7 read backwards. So this file changes no engine line. **It has no
discrimination against the tree of 0.1.184 and every case here passes on it**,
which is declared rather than hidden: what it buys is that the four statements
above stop being findings in a changelog and become things the suite refuses
to let drift.

WHAT IT ALSO PINS, WITHOUT FIXING IT. ``PathSearch._run`` stops at
``valid_count >= num_surfaces``, so the SIZE of the sample is a function of
the validity rate: an engine that makes more surfaces valid sees FEWER
surfaces. ``TestTheEvaluatorOnlyChoosesWhereToCut`` measures it as A PREFIX OF
the longer run, which is the honest shape of the thing — nothing is
reordered, the tail is simply never reached. It is latent on problem 85 and it
is reported as its own defect rather than repaired here, because "Number of
Surfaces is the count of VALID surfaces" is a documented decision with a
reference behind it and undoing it moves every non-circular row in the bank.

THE DENOMINATOR OF THE CENSUS THAT COULD NOT BE RUN. The ficha asks how many
of the 39 non-circular rows changed critical surface between 0.1.180 and
0.1.181. 35 of 38 files in both snapshots were written by 0.1.173 and one by
0.1.147, and they are byte for byte identical in the two: the question can
only ever answer "the two halves of problem 85", and it would answer it for
an arithmetic reason and not a measured one. That is its own defect too.

WHAT THIS FILE DOES NOT CLAIM. Not that the minimum published today is the
right one — it is the minimum over the admissible subset under today's
criterion, and whether that criterion is too strict on reinforced
non-circular surfaces is a question this file does not open. Not that the
other six non-circular searches behave like this one: ``BlockSearch``
generates a fixed count and cannot even shorten, ``SimulatedAnnealingSearch``
IS steered by the factor through its Metropolis acceptance, and the
optimisation walk of ``optimize.py`` is guided by construction. Not anything
about which surfaces a search would find under a different seed.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

import contextlib

H, TOE, CREST = 12.0, 30.0, 50.0

#: Every switch of ``interslice.py`` that a version has added to the branch
#: and λ machinery. Off together they are the engine as it solved before any
#: of them; the point of the list is that NONE of them may move a generated
#: polyline, because none of them is consulted while one is generated.
INTERRUPTORES = (
    "BRANCH_RESCUE", "BRANCH_PAIR_TIGHTEN", "BRANCH_PAIR_SETTLE",
    "BRANCH_PLANAR_FORCE", "BRANCH_CYCLE_RESCUE", "LAMBDA_GAP_REFINE",
    "LAMBDA_EDGE_RECOVERY", "LAMBDA_BRACKET_FLOOR_CUT",
    "THRUST_FLAG_FROM_STATE",
)

SEMILLA = 10116          # the project default, so this is the bank's stream
N_SUP = 40               # small: this file is about sequences, not minima


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
    p = Project("path-population")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [Material(name="Soil", unit_weight=18,
                            strength=MohrCoulomb(cohesion=8,
                                                 friction_angle=20))]
    return p


def _search(method_id="spencer", num_surfaces=N_SUP, seed=SEMILLA):
    from ogr_slip2d.methods.base import method_registry
    from ogr_slip2d.search import PathSearch
    return PathSearch(method=method_registry()[method_id](),
                      num_vertices=8, num_surfaces=num_surfaces,
                      num_slices=20, seed=seed)


@contextlib.contextmanager
def _switches_off():
    """Every branch and λ switch off at once, restored with try/finally.

    ``getattr(..., None)`` per name so that a tree missing one of them is
    still measured on the rest instead of erroring out, and ``try/finally``
    because the runner does not call ``teardown_method`` (rule 5) — a leak
    here would reach every other file in the suite and only in a full run.
    """
    import ogr_slip2d.interslice as interslice
    previos = {}
    for nombre in INTERRUPTORES:
        v = getattr(interslice, nombre, None)
        if v is not None:
            previos[nombre] = v
            setattr(interslice, nombre, False)
    try:
        yield tuple(sorted(previos))
    finally:
        for nombre, v in previos.items():
            setattr(interslice, nombre, v)


def _generated(search, project, tope=None):
    """The polylines the generator produces, in order, WITHOUT evaluating.

    ``evaluate_surface`` is replaced by a spy that returns ``None``, which
    the loop counts as invalid and skips. ``None`` is what makes this a
    measurement of the generator alone: ``valid_count`` never rises, so the
    loop runs to its ``max_attempts`` ceiling and the whole sequence comes
    out. Nothing in the generator consults the evaluator, and that is the
    claim being measured rather than assumed.
    """
    vistas = []

    def espia(_project, surface, _v=vistas):
        _v.append(tuple((round(v.x, 9), round(v.y, 9))
                        for v in surface.polyline.vertices))
        return None

    original = search.evaluate_surface
    search.evaluate_surface = espia
    try:
        search._run(project)
    finally:
        search.evaluate_surface = original
    return vistas if tope is None else vistas[:tope]


def _generated_with_rate(search, project, cada):
    """The same, but 1 surface in ``cada`` is declared VALID.

    The stub is a plain object and never the engine: this class is about
    the LOOP, and a real evaluator would make the validity rate a property
    of the slope instead of a knob. Returns ``(sequence, attempts,
    valid_count)``.
    """
    vistas = []

    class _Falso:
        def __init__(self, ok):
            self.is_valid = ok
            self.fos = 1.5
            self.admissible = True

    def espia(_project, surface, _v=vistas):
        _v.append(tuple((round(v.x, 9), round(v.y, 9))
                        for v in surface.polyline.vertices))
        return _Falso(len(_v) % cada == 0)

    original = search.evaluate_surface
    search.evaluate_surface = espia
    try:
        res = search._run(project)
    finally:
        search.evaluate_surface = original
    return vistas, res.attempts, res.valid_count


def _resultado(fos, valid=True, admissible=True):
    """A ``LEMResult`` with only the fields ``SearchResult.critical`` reads.

    Hand-made on purpose: the pick is a piece of set arithmetic and asking
    it of two literals says what it does far more sharply than asking it of
    a slope that happens to produce them.
    """
    from ogr_slip2d.methods.base import LEMResult
    r = LEMResult(fos=fos, converged=True, iterations=1,
                  method_id="spencer", surface=None, slices=None)
    r.admissible = admissible
    if not valid:
        r.error_message = "vetoed"
    return r


def _pool(*resultados):
    from ogr_slip2d.search import SearchResult
    res = SearchResult(method_id="spencer")
    res.evaluations = list(resultados)
    res.valid_count = sum(1 for r in resultados if r.is_valid)
    return res


# ======================================================================
class TestTheGeneratorIsAPureFunctionOfTheSeed:
    """Same seed, same polylines — whatever the evaluator is doing.

    ``PathSearch`` draws every surface from ``random.Random(self.seed)`` and
    nothing between one draw and the next consults a result, so the surface
    of attempt k is fixed by the seed, the geometry and the settings. This
    is the leg of the refutation that does not depend on the bank.
    """

    def test_two_runs_of_the_same_seed_are_bit_identical(self):
        p = _slope()
        a = _generated(_search(), p, tope=200)
        b = _generated(_search(), p, tope=200)
        assert a and a == b, "same seed, different polylines"

    def test_and_so_are_the_two_sides_of_every_branch_switch(self):
        p = _slope()
        enviado = _generated(_search(), p, tope=200)
        with _switches_off() as vistos:
            apagado = _generated(_search(), p, tope=200)
        assert len(vistos) >= 8, (
            "only %d switches were found, so this compared almost nothing"
            % len(vistos))
        assert enviado == apagado, (
            "turning the branch and λ machinery off moved a GENERATED "
            "polyline, which would mean the generator does consult the "
            "evaluator after all")

    def test_the_method_does_not_change_what_is_generated(self):
        """Bishop and Spencer get the same surfaces, in the same order."""
        p = _slope()
        assert (_generated(_search("bishop_simplified"), p, tope=200)
                == _generated(_search("spencer"), p, tope=200))


class TestTheEvaluatorOnlyChoosesWhereToCut:
    """What the evaluator decides is WHERE THE SEQUENCE ENDS.

    The loop stops at ``valid_count >= num_surfaces``, so a validity rate of
    one in one and one in three walk the same sequence and stop at different
    places. Nothing is reordered: the short run is A PREFIX OF the long one.
    This states the defect reported alongside D155 and does not repair it.
    """

    def test_a_lower_validity_rate_costs_more_attempts(self):
        p = _slope()
        _s1, att1, v1 = _generated_with_rate(_search(), p, 1)
        _s3, att3, v3 = _generated_with_rate(_search(), p, 3)
        assert v1 == v3 == N_SUP, (
            "the runs did not both reach the target (%d, %d)" % (v1, v3))
        assert att3 > att1, (
            "one valid in three cost %d attempts against %d for one in one, "
            "so the budget does not depend on the evaluator and this "
            "defect does not exist" % (att3, att1))

    def test_and_the_short_run_is_a_prefix_of_the_long_one(self):
        p = _slope()
        corta, _a1, _v1 = _generated_with_rate(_search(), p, 1)
        larga, _a3, _v3 = _generated_with_rate(_search(), p, 3)
        assert len(corta) < len(larga)
        assert larga[:len(corta)] == corta, (
            "the two runs diverge inside the common length, which would "
            "mean the sequence itself depends on the verdicts")

    def test_so_a_more_permissive_engine_sees_less(self):
        """The irony stated as an assertion, because it is the mechanism."""
        p = _slope()
        permisiva, _a, _v = _generated_with_rate(_search(), p, 1)
        estricta, _b, _w = _generated_with_rate(_search(), p, 3)
        assert len(permisiva) < len(estricta)


class TestABishopSearchIsBitIdenticalAcrossTheSwitches:
    """The null control, and without it nothing above is distinguishable.

    Bishop simplified never reaches ``interslice.py``. If its whole search
    moves when those switches move, then something other than the evaluator
    is different between the two sides and every comparison in this file is
    measuring that instead.
    """

    def test_the_whole_search_comes_back_the_same(self):
        p = _slope()
        b = _search("bishop_simplified", num_surfaces=30)
        antes = b.run(p)
        with _switches_off():
            b2 = _search("bishop_simplified", num_surfaces=30)
            despues = b2.run(p)
        assert antes.valid_count == despues.valid_count
        assert antes.invalid_count == despues.invalid_count
        assert antes.attempts == despues.attempts
        assert antes.critical is not None
        assert antes.critical.fos == despues.critical.fos, (
            "Bishop moved with the inter-slice switches: %r against %r"
            % (antes.critical.fos, despues.critical.fos))


class TestTheMinimumIsOverTheAdmissibleSubset:
    """``is_valid`` IS NOT THE PREDICATE, which is what the ficha missed.

    Set arithmetic on two hand-made results. No slope, no solver, no seed:
    the point is what ``critical`` selects, and that is decidable.
    """

    def test_a_lower_but_inadmissible_surface_does_not_win(self):
        bajo = _resultado(1.51, valid=True, admissible=False)
        alto = _resultado(2.07, valid=True, admissible=True)
        res = _pool(bajo, alto)
        assert bajo.is_valid and alto.is_valid, (
            "both have to be VALID or this measures the veto instead")
        assert res.critical is alto, (
            "the published minimum is the minimum over the ADMISSIBLE "
            "subset, and this is the whole of D155")

    def test_and_wins_the_moment_the_flag_turns(self):
        bajo = _resultado(1.51, valid=True, admissible=False)
        alto = _resultado(2.07, valid=True, admissible=True)
        assert _pool(bajo, alto).critical is alto
        bajo.admissible = True
        assert _pool(bajo, alto).critical is bajo, (
            "one boolean, nothing else, and the published minimum moves "
            "37 % — which is the size of the jump on problem 85")

    def test_but_it_does_win_when_nothing_else_is_admissible(self):
        """``pool = ok or valid``, and it is why the answer is not empty."""
        bajo = _resultado(1.51, valid=True, admissible=False)
        alto = _resultado(2.07, valid=True, admissible=False)
        assert _pool(bajo, alto).critical is bajo, (
            "with no admissible surface the preference steps aside; a "
            "search that returned nothing here would be a different defect")

    def test_is_valid_alone_predicts_nothing(self):
        bajo = _resultado(1.51, valid=True, admissible=False)
        alto = _resultado(2.07, valid=True, admissible=True)
        ganador = _pool(bajo, alto).critical
        assert bajo.is_valid is alto.is_valid is True
        assert ganador is not min((bajo, alto), key=lambda r: r.fos), (
            "reading is_valid and taking the smallest reproduces the "
            "ficha's reasoning, and it has to give the wrong answer here")


class TestMultiStartCannotRecoverADisqualifiedSurface:
    """The remedy the ficha proposes, executed, and it moves nothing.

    ``SearchResult.user_evaluations`` is the one channel that already exists
    for a surface handed to a search from outside — drawn by the user, or
    seeded from a previous run — and ``all_evaluations`` makes it compete
    for the minimum on equal terms. That is as much as any multi-start could
    buy on this row, because the surface is not missing: it is disqualified.
    """

    def test_seeding_it_back_in_changes_nothing(self):
        vieja = _resultado(1.51, valid=True, admissible=False)
        hoy = _resultado(2.07, valid=True, admissible=True)
        res = _pool(hoy)
        res.user_evaluations = [vieja]
        assert vieja in res.all_evaluations(), (
            "the seeded surface is not even being considered, so this case "
            "would prove nothing")
        assert res.critical is hoy, (
            "handing the old minimum back to the search does not make it "
            "eligible — which is why multi-start is a setting that would "
            "move no number here (rule 7)")

    def test_and_the_flag_is_the_only_thing_in_the_way(self):
        vieja = _resultado(1.51, valid=True, admissible=True)
        hoy = _resultado(2.07, valid=True, admissible=True)
        res = _pool(hoy)
        res.user_evaluations = [vieja]
        assert res.critical is vieja, (
            "with the flag turned the same seeding does recover it, so the "
            "case above is about eligibility and not about the channel")

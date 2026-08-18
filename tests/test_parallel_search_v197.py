# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Splitting a Grid Search across processes may not change a single number.

WHAT INVARIANT THIS PROTECTS.

The circles of a Grid Search are independent: each one is sliced and solved
from the project alone, nothing is carried from one to the next, and since
v0.1.93 ``regions_frozen`` guarantees by contract that the project does not
change while it is being analysed. So parallelising them is not an
approximation and the test for it is not a tolerance — it is **bit-for-bit
identity** against the sequential run, which is how v0.1.93 validated its
own optimisation.

Identity needs one thing the parallelism itself does not give: ORDER.
``evaluations`` is a list, and a caller may read it positionally. The
batches are therefore contiguous runs of ``_centres`` in visiting order,
and ``ProcessPoolExecutor.map`` returns results in submission order, so
reassembling them concatenates back into the same list — whichever worker
happened to finish first.

The second half covers the two Project Settings controls — ``parallel_search``
and ``parallel_cpu_percent`` — because rule 7 applies to them as much as to
anything else: an option that changes nothing is worse than no option. They
are two and not one deliberately. "Use the machine" and "use HOW MUCH of the
machine" are different questions, and a search that takes every processor
makes the computer unusable for anything else while it lasts.

Finally, that a host which cannot start a pool still gets the right answer,
only slower. That is not hypothetical: on Windows the workers re-import the
parent's ``__main__``, and there are contexts where that cannot succeed.

Author: Samuel Sáez López (UPCT)
"""
from __future__ import annotations

# Big enough to cross the automatic threshold (7 x 7 centres, 11 radii each
# = 605 circles > 400) and small enough that the suite does not notice.
GRID_NX = GRID_NY = 6
RADIUS_INCREMENT = 10
NUM_SLICES = 12


def _project():
    """The Ej_2 geometry, dry. Built in code — the suite runs from a clone."""
    from ogr_core.geometry import Boundary, BoundaryType, Polyline, Vertex
    from ogr_core.materials import Material
    from ogr_core.materials.builtin_models import MohrCoulomb
    from ogr_core.project import Project

    ext = Polyline(vertices=[
        Vertex(0, 0), Vertex(100, 0), Vertex(100, 70), Vertex(70, 70),
        Vertex(55, 55), Vertex(40, 55), Vertex(15, 30), Vertex(-50, 30),
        Vertex(-50, 0),
    ], closed=True)
    ext.ensure_ccw()
    p = Project("par")
    p.add_boundary(Boundary(polyline=ext, btype=BoundaryType.EXTERNAL))
    p.materials = [
        Material(name="Material 1", unit_weight=20,
                 strength=MohrCoulomb(cohesion=20, friction_angle=35)),
    ]
    return p


def _search(project, workers):
    """``workers`` here is a process count, translated into the two
    controls the user actually sees: off when 1, otherwise the share of
    this machine that yields that many."""
    import os
    from ogr_slip2d.methods import get_method
    from ogr_slip2d.search import GridSearch
    adv = project.settings.advanced
    if workers <= 1:
        adv.parallel_search = False
    else:
        adv.parallel_search = True
        total = os.cpu_count() or 1
        adv.parallel_cpu_percent = max(1, min(100,
                                              int(round(100 * workers / total))))
    return GridSearch(
        method=get_method("bishop_simplified")(),
        grid_x=(-40.0, 70.0), grid_y=(35.0, 135.0),
        grid_nx=GRID_NX, grid_ny=GRID_NY,
        radius_increment=RADIUS_INCREMENT, min_radius=0.0,
        num_slices=NUM_SLICES, min_area=1.0,
    )


def _fingerprint(result):
    """Every evaluation, at full floating-point precision, in order.

    ``repr`` and not ``round``: the claim is identity, so the comparison
    has to be able to see the last bit.
    """
    out = []
    for e in result.evaluations:
        sd = e.surface.to_dict()
        out.append((
            repr(e.fos), e.converged, e.iterations, e.is_valid,
            e.admissible, e.error_message,
            repr(sd.get("centre_x")), repr(sd.get("centre_y")),
            repr(sd.get("radius")), repr(sd.get("x_left")),
            repr(sd.get("x_right")), len(e.slices),
        ))
    return out


_CACHE: dict = {}


def _run(workers):
    if workers in _CACHE:
        return _CACHE[workers]
    p = _project()
    _CACHE[workers] = _search(p, workers).run(p)
    return _CACHE[workers]


# ======================================================================
class TestParallelIsBitIdentical:
    """The one claim that matters."""

    def test_same_evaluations_in_the_same_order(self):
        seq = _fingerprint(_run(1))
        par = _fingerprint(_run(2))
        assert len(seq) == len(par), (len(seq), len(par))
        assert seq == par

    def test_same_counts(self):
        seq, par = _run(1), _run(2)
        assert seq.valid_count == par.valid_count
        assert seq.invalid_count == par.invalid_count
        # The documented population identity, which must survive the split:
        # (nx+1)(ny+1)(rinc+1).
        expected = (GRID_NX + 1) * (GRID_NY + 1) * (RADIUS_INCREMENT + 1)
        assert seq.total_count == expected, seq.total_count
        assert par.total_count == expected, par.total_count

    def test_same_critical_surface_to_the_last_bit(self):
        seq, par = _run(1), _run(2)
        assert seq.critical is not None and par.critical is not None
        assert repr(seq.critical.fos) == repr(par.critical.fos)
        a, b = seq.critical.surface.to_dict(), par.critical.surface.to_dict()
        for key in ("centre_x", "centre_y", "radius", "x_left", "x_right"):
            assert repr(a[key]) == repr(b[key]), (key, a[key], b[key])

    def test_the_test_would_notice_a_difference(self):
        """Guard on the guard: the fingerprint has to discriminate.

        A fingerprint that collapsed everything to a constant would make
        every assertion above pass for free.
        """
        seq = _run(1)
        mutated = _fingerprint(seq)
        assert len(mutated) > 50, len(mutated)
        assert len(set(mutated)) > 1


# ======================================================================
class TestTheSettingDecides:
    """Rule 7 — the two Project Settings controls have to change what happens.

    They are two and not one on purpose: "use the machine" and "use HOW
    MUCH of the machine" are different questions, and a run that takes
    every processor makes the computer unusable while it lasts.
    """

    def test_switching_it_off_means_sequential(self):
        from ogr_slip2d.search import _worker_count
        p = _project()
        p.settings.advanced.parallel_search = False
        assert _worker_count(p, 100000) == 1

    def test_the_percentage_scales_the_process_count(self):
        """And it has to be MONOTONE: more share, never fewer processes."""
        import os
        from ogr_slip2d.search import _worker_count
        p = _project()
        p.settings.advanced.parallel_search = True
        counts = []
        for pct in (1, 25, 50, 75, 100):
            p.settings.advanced.parallel_cpu_percent = pct
            counts.append(_worker_count(p, 100000))
        assert counts == sorted(counts), counts
        if (os.cpu_count() or 1) >= 4:
            # A real machine must show the control doing something.
            assert counts[-1] > counts[0], counts

    def test_the_share_never_rounds_down_to_none(self):
        """1 % means "as little as possible", not "off".

        Switching it off is the checkbox's job; a percentage that also
        meant off would be a second way to say the same thing, and the
        one the user did not expect.
        """
        from ogr_slip2d.search import _worker_count
        p = _project()
        p.settings.advanced.parallel_search = True
        p.settings.advanced.parallel_cpu_percent = 1
        assert _worker_count(p, 100000) >= 1

    def test_a_small_search_stays_in_process(self):
        """Starting a pool for 25 circles costs far more than it saves."""
        from ogr_slip2d.search import _PARALLEL_MIN_CIRCLES, _worker_count
        p = _project()
        p.settings.advanced.parallel_search = True
        assert _worker_count(p, _PARALLEL_MIN_CIRCLES - 1) == 1

    def test_both_settings_survive_a_save(self):
        from ogr_core.project.settings import AdvancedSettings
        a = AdvancedSettings.from_dict({"parallel_search": False,
                                        "parallel_cpu_percent": 25})
        assert a.parallel_search is False
        assert a.parallel_cpu_percent == 25
        # A project written before this version keeps working, on the
        # defaults.
        b = AdvancedSettings.from_dict({})
        assert b.parallel_search is True
        assert b.parallel_cpu_percent == 50

    def test_the_dialog_writes_both(self):
        """The page has to reach the fields, or this is unreachable."""
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from ogr_gui.dialogs.project_settings_dialog import (
            ProjectSettingsDialog,
        )
        p = _project()
        dlg = ProjectSettingsDialog(p.settings, None)
        page = next((pg for pg in dlg.pages
                     if hasattr(pg, "chk_parallel")), None)
        assert page is not None, "the Advanced page has no parallel controls"
        page.chk_parallel.setChecked(False)
        page.sp_cpu_pct.setValue(25)
        page.apply()
        assert p.settings.advanced.parallel_search is False
        assert p.settings.advanced.parallel_cpu_percent == 25


# ======================================================================
class TestItFallsBackInsteadOfFailing:
    """A pool that cannot start is not a reason to refuse to analyse."""

    def test_a_broken_pool_still_returns_the_sequential_answer(self):
        import ogr_slip2d.search as SM

        p = _project()
        search = _search(p, 2)

        class _Boom:
            def __init__(self, *a, **kw):
                raise OSError("no process pool on this host")

        original = SM.ProcessPoolExecutor if hasattr(
            SM, "ProcessPoolExecutor") else None
        import concurrent.futures as cf
        real = cf.ProcessPoolExecutor
        cf.ProcessPoolExecutor = _Boom
        try:
            got = search.run(p)
        finally:
            cf.ProcessPoolExecutor = real
            if original is not None:
                SM.ProcessPoolExecutor = original

        seq = _run(1)
        assert got.valid_count == seq.valid_count
        assert got.invalid_count == seq.invalid_count
        assert repr(got.critical.fos) == repr(seq.critical.fos)

    def test_the_progress_callback_survives_the_trip(self):
        """It is stripped for pickling and must be put back, and called.

        A bound Qt signal does not pickle, so the parallel path removes it
        from the search object before handing it to the workers. Losing it
        there would silently freeze the progress bar of every later run
        with the same search object.
        """
        seen = []
        p = _project()
        search = _search(p, 2)
        search.progress_cb = lambda done, total: seen.append((done, total))
        search.run(p)
        assert search.progress_cb is not None
        assert seen, "the parallel run reported no progress at all"
        assert seen[-1][0] == seen[-1][1]

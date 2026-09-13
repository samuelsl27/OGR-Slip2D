# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
A bond profile that will not build costs force, and says which force.

Defect D95, opened out of writing the reasons of D62 and fixed here.
``_bond_profiles`` wrapped ``build_bond_profile`` in a blanket
``except Exception: continue``, and the comment on it argued the silence
was harmless: ``force_at`` would fall back on its zero-stress envelope,
"which is conservative: never MORE reinforcement than the stress state
would give".

That is true of two of the four types that ask for a profile and false of
the other two. Neither ``PileMicropile`` in Ito-Matsui mode nor
``HelicalAnchor`` has an envelope at zero stress to fall back on — their
strength comes from the ground rather than from a parameter of their own —
and both answer exactly 0.0. "Less reinforcement" was in fact NONE, and
the factor of safety became the bare slope's, wearing a valid answer's
clothes: the shape of D94 and D98 one step further down.

The second half is the diagnosis. Such a support surfaced through
``SUPPORT_NO_CAPACITY``, "develops no capacity where it crosses" — which
is a statement about the MODEL, and the truth was a statement about the
TYPE: its profile could not be built. The comment on that constant had
been warning about this confusion since v0.1.155 without being able to
prevent it.

Seven invariants, none of them a captured value:

  * **the profile is worth something.** For each of the four types the
    factor with a sound profile is strictly higher than with a broken one.
    Without this the rest would be measuring a quantity that was zero
    anyway (rule 7);
  * **when the fallback is nothing, it is the bare slope.** Geosynthetic
    in coefficient mode, helical anchor and Ito-Matsui pile with a broken
    profile give BIT FOR BIT the factor of the model with its supports
    deleted — an identity between two runs of the real solver, not a
    number read off this version;
  * **and now it says which.** The reason names the profile and the
    exception class, and it is NOT ``no_capacity``;
  * **the branch that still contributes stays in the equilibrium.** A
    grouted tieback with adhesion keeps its zero-stress envelope, so it
    lands strictly between the bare slope and the sound one, reports the
    other reason, and is kept OUT of the count of supports that put no
    force — a lone one must never produce "0 of the 1 supports placed";
  * **the written contract holds for a profile too.** ``docs/plugins.md``
    names "a profile that will not build" among the reasons to raise
    :class:`~ogr_core.support.SupportEvaluationError`, and until this
    version a type that did exactly that got the same answer as one with a
    ``TypeError`` in it. Now it reaches D94's handler, that one support is
    left out, and the others still count;
  * **a sound profile changes nothing**, which is what "zero digits
    moved" means inside the suite;
  * **the interface says it too.** The canvas tooltip and the Support
    Force Diagram build their own profile and swallowed the same failure,
    so after this fix they would have been the only two mouths left shut.

The plugin types are reached by IDENTITY through ``type_ref`` and are
subclasses of REGISTERED types: the registry is module-level state and a
test that writes to it leaks into every other test of the run (rule 5) —
the pattern ``test_support_silence_v1155.py`` set, which
``test_support_failure_v1161.py`` and ``test_support_shear_failure_v1162``
followed. Nothing here monkeypatches ``build_bond_profile``: the profile
is broken where a real one breaks, in the type's own sampling method, and
the trigger is the PRESENCE OF THE CONTEXT rather than a threshold on the
stress. ``build_bond_profile`` always calls ``interface_tau`` and
``station_value`` with the six context keys, while the fallback inside
``force_at`` calls ``interface_tau(0.0)`` positionally and with none, so
the split is exact instead of depending on no sample landing at zero
effective stress.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_supports_all_methods_v164 import (  # noqa: E402
    _circle, _project,
)

import pytest  # noqa: E402


# ======================================================================
# Fixtures
# ======================================================================
#: The horizontal axis the other support tests use; it crosses the fixture
#: circle at x = 46.71.
_ACROSS = ((43.5, 8.0), (54.0, 8.0))
#: A second axis, parallel and lower, crossing at x = 44.24. Used where a
#: model needs a support that is NOT the broken one.
_SECOND = ((43.5, 7.0), (54.0, 7.0))


def _instance(type_ref, ends=_ACROSS):
    from ogr_core.geometry import Vertex
    from ogr_core.support import (ForceApplication, ForceOrientation,
                                  SupportInstance)
    return SupportInstance(
        type_id="soil_nail", head=Vertex(*ends[0]), tail=Vertex(*ends[1]),
        force_application=ForceApplication.PASSIVE,
        orientation=ForceOrientation.TANGENT_TO_SLIP, type_ref=type_ref)


def _blown(base, method, exc_factory, **kw):
    """``base`` with one sampling method that refuses to answer.

    The override fires only when a context is passed, which is what tells
    the two callers apart: ``build_bond_profile`` samples with
    ``project``, ``x``, ``y``, ``pore_pressure``, ``depth`` and
    ``axis_angle_rad``, and the zero-stress fallback inside ``force_at``
    passes nothing at all. So the profile breaks and the envelope the fix
    is about stays reachable.
    """
    def hook(self, sigma_v_eff, **ctx):
        if ctx:
            raise exc_factory(self.id)
        return getattr(super(cls, self), method)(sigma_v_eff, **ctx)

    cls = type("_Blown" + base.__name__, (base,), {method: hook})
    return cls(**kw)


def _runtime_error(_sid):
    return RuntimeError("the demo type cannot sample that")


def _evaluation_error(sid):
    from ogr_core.support import SupportEvaluationError
    return SupportEvaluationError(sid, "the profile will not build")


# --- the four types that ask for a profile ----------------------------
#: Coefficient mode: its pullout law is a fraction of the SOIL's strength,
#: so without a project there is nothing to take a fraction of and the
#: envelope is genuinely zero. An envelope that exists and is nil.
_GEO = dict(tensile_capacity=50.0, pullout_mode="coefficient",
            coefficient_of_interaction=0.8, connection_strength=25.0)
#: Adhesion at the interface, which IS an envelope at zero stress: this is
#: the type the old comment described correctly.
_TIEBACK = dict(adhesion=60.0, friction_angle_bond=25.0)


def _geo(**kw):
    from ogr_core.support import Geosynthetic
    return Geosynthetic(**dict(_GEO, **kw))


def _tieback(**kw):
    from ogr_core.support import GroutedTiebackFriction
    return GroutedTiebackFriction(**dict(_TIEBACK, **kw))


def _anchor(**kw):
    from ogr_core.support import HelicalAnchor
    return HelicalAnchor(**dict(dict(out_of_plane_spacing=2.0), **kw))


def _nail():
    from ogr_core.support import SoilNail
    return SoilNail(tensile_capacity=30, plate_capacity=20,
                    bond_strength=8, out_of_plane_spacing=3.0)


def _model(*stypes_and_ends):
    """A project carrying one support per ``(type, ends)`` pair."""
    p = _project(None)
    p.support_types = [st for st, _e in stypes_and_ends]
    p.supports = [_instance(st.id, ends) for st, ends in stypes_and_ends]
    return p


def _bare():
    p = _project(None)
    p.support_types, p.supports = [], []
    return p


# --- running it -------------------------------------------------------
def _result(p):
    """A LEMResult on the fixture circle, from the real solver."""
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(p, _circle(), num_slices=25)
    return BishopSimplified().compute_fos(p, _circle(), sl)


def _bishop(p):
    return _result(p).fos


def _reasons(p):
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import compute_support_effects
    sl = slice_surface(p, _circle(), num_slices=25)
    out: list = []
    compute_support_effects(p, _circle(), sl, reasons=out)
    return out


def _effects(p):
    from ogr_slip2d.slicer import slice_surface
    from ogr_slip2d.support_integration import compute_support_effects
    sl = slice_surface(p, _circle(), num_slices=25)
    return compute_support_effects(p, _circle(), sl)


def _notes(project, result):
    from ogr_slip2d.support_integration import uncontributing_support_notes
    return uncontributing_support_notes(project, result)


def _why(p):
    """The reason strings alone, so an assertion does not chase uuids."""
    return [why for _sid, why in _reasons(p)]


# --- the Ito-Matsui pile lives in its own published fixture ------------
def _pile_models():
    """``(sound, blown, bare)`` for the Cai and Ugai pile row.

    Borrowed rather than rebuilt: the pile is VERTICAL there, and on the
    horizontal axis above it would stop at ``no_crest`` before the force
    is ever computed — ``MEASURED_FROM_TOP`` is true in this mode — so a
    model of my own would have measured the wrong guard.
    """
    import test_ito_matsui_pile_v1123 as T
    from ogr_core.support import PileMicropile

    kw = dict(failure_mode="ito_matsui", out_of_plane_spacing=3.0 * T.DIAM,
              pile_diameter=T.DIAM)
    sound = T._project(3.0)
    blown = T._project(3.0)
    st = _blown(PileMicropile, "interface_tau", _runtime_error, **kw)
    blown.support_types = [st]
    blown.supports[0].type_ref = st.id
    bare = T._project(3.0)
    bare.support_types, bare.supports = [], []
    return T, sound, blown, bare


def _pile_fos(project, T):
    from ogr_slip2d.methods.bishop import BishopSimplified
    from ogr_slip2d.slicer import slice_surface
    sl = slice_surface(project, T._circle(), num_slices=40)
    return BishopSimplified().compute_fos(project, T._circle(), sl).fos


# ======================================================================
class TestTheProfileIsWorthSomething:
    """Rule 7, and the anchor every block below stands on.

    "Breaking the profile costs the bare slope" proves nothing if the
    profile was worth nothing to begin with. One case per type that
    declares ``NEEDS_BOND_PROFILE``, because what the fallback IS differs
    between them and that difference is the defect.
    """

    def test_a_geosynthetic_is_worth_more_with_its_profile(self):
        blown = _blown(type(_geo()), "interface_tau", _runtime_error, **_GEO)
        assert _bishop(_model((_geo(), _ACROSS))) > \
            _bishop(_model((blown, _ACROSS)))

    def test_a_grouted_tieback_is_worth_more_with_its_profile(self):
        blown = _blown(type(_tieback()), "interface_tau", _runtime_error,
                       **_TIEBACK)
        assert _bishop(_model((_tieback(), _ACROSS))) > \
            _bishop(_model((blown, _ACROSS)))

    def test_a_helical_anchor_is_worth_more_with_its_profile(self):
        """Broken at ``station_value``, which only the profile calls.

        Its plate bearing capacities exist at the helices and nowhere
        between them, so they arrive through ``bond.stations`` rather than
        through the integral — a second way for the same build to fail.
        """
        blown = _blown(type(_anchor()), "station_value", _runtime_error,
                       out_of_plane_spacing=2.0)
        assert _bishop(_model((_anchor(), _ACROSS))) > \
            _bishop(_model((blown, _ACROSS)))

    def test_an_ito_matsui_pile_is_worth_more_with_its_profile(self):
        T, sound, blown, _bare_p = _pile_models()
        assert _pile_fos(sound, T) > _pile_fos(blown, T)


# ======================================================================
class TestWhenTheFallbackIsNothingItIsTheBareSlope:
    """The numerical claim of the defect, as identities.

    Three of the four types answer exactly zero with no profile — two of
    them because they have no envelope at zero stress at all, the
    geosynthetic because in coefficient mode the envelope it does have is
    nil — so the factor is the one for a slope with no reinforcement,
    which is the answer that looks most like a correct one.
    """

    def test_the_geosynthetic_loses_everything(self):
        blown = _blown(type(_geo()), "interface_tau", _runtime_error, **_GEO)
        assert _bishop(_model((blown, _ACROSS))) == _bishop(_bare())

    def test_the_helical_anchor_loses_everything(self):
        blown = _blown(type(_anchor()), "station_value", _runtime_error,
                       out_of_plane_spacing=2.0)
        assert _bishop(_model((blown, _ACROSS))) == _bishop(_bare())

    def test_the_ito_matsui_pile_loses_everything(self):
        T, _sound, blown, bare = _pile_models()
        assert _pile_fos(blown, T) == _pile_fos(bare, T)

    def test_and_none_of_them_is_in_the_equilibrium_at_all(self):
        blown = _blown(type(_geo()), "interface_tau", _runtime_error, **_GEO)
        assert _effects(_model((blown, _ACROSS))) == []


# ======================================================================
class TestAndNowItSaysWhich:
    """The defect itself: everything above was already true in silence."""

    def test_the_reason_names_the_profile_and_the_exception(self):
        from ogr_slip2d.support_integration import (
            SUPPORT_BOND_PROFILE_NO_FORCE)

        blown = _blown(type(_geo()), "interface_tau", _runtime_error, **_GEO)
        assert _why(_model((blown, _ACROSS))) == [
            SUPPORT_BOND_PROFILE_NO_FORCE + ":RuntimeError"]

    def test_and_it_is_not_the_one_about_the_model(self):
        """``no_capacity`` is a fact about the slope, and this is not one.

        The distinction the whole defect is about: "develops no capacity
        where it crosses" sends the user to look at the soil around a
        support that may be perfectly specified.
        """
        from ogr_slip2d.support_integration import SUPPORT_NO_CAPACITY

        blown = _blown(type(_anchor()), "station_value", _runtime_error,
                       out_of_plane_spacing=2.0)
        assert SUPPORT_NO_CAPACITY not in _why(_model((blown, _ACROSS)))

    def test_the_note_says_the_profile_and_names_the_exception(self):
        blown = _blown(type(_geo()), "interface_tau", _runtime_error, **_GEO)
        p = _model((blown, _ACROSS))
        note = " ".join(_notes(p, _result(p)))
        assert "bond profile" in note, note
        assert "RuntimeError" in note, note
        assert "develops no capacity" not in note, note

    def test_a_support_that_genuinely_develops_nothing_still_says_so(self):
        """The old reason is narrowed, not removed.

        A type with a real zero capacity and a sound profile must keep
        reporting ``no_capacity``: the fix is that the two stop sharing a
        sentence, not that one of them stops existing.
        """
        from ogr_slip2d.support_integration import SUPPORT_NO_CAPACITY

        p = _model((_geo(tensile_capacity=0.0, connection_strength=0.0),
                    _ACROSS))
        assert _why(p) == [SUPPORT_NO_CAPACITY]


# ======================================================================
class TestTheBranchThatStillContributes:
    """The other half of D95, and the one the old comment described.

    A grouted tieback with adhesion has a real envelope at zero effective
    stress, so a failed profile costs it the stress-dependent part of its
    pullout and no more. It stays in the equilibrium with less
    reinforcement than the model carries — the shape of D98 — and until
    this version that cost nothing was said anywhere at all: not even the
    wrong reason, because the support never reached the guard that writes
    one.
    """

    def _blown_tieback(self):
        return _blown(type(_tieback()), "interface_tau", _runtime_error,
                      **_TIEBACK)

    def test_it_lands_strictly_between_the_bare_slope_and_the_sound_one(self):
        blown = _bishop(_model((self._blown_tieback(), _ACROSS)))
        assert _bishop(_bare()) < blown < _bishop(_model((_tieback(),
                                                          _ACROSS)))

    def test_it_is_still_in_the_equilibrium(self):
        e = _effects(_model((self._blown_tieback(), _ACROSS)))
        assert len(e) == 1
        assert e[0].force_magnitude > 0

    def test_the_reason_is_the_other_one(self):
        from ogr_slip2d.support_integration import SUPPORT_BOND_PROFILE_FAILED

        assert _why(_model((self._blown_tieback(), _ACROSS))) == [
            SUPPORT_BOND_PROFILE_FAILED + ":RuntimeError"]

    def test_and_it_is_not_counted_among_the_ones_that_put_no_force(self):
        """The trap that cost D98 its own test.

        The support DOES put force on the surface. Filing its reason with
        the others would say "The only support placed puts no force",
        which is false; filtering it out and letting the tail run would
        say "0 of the 1 supports placed put no force", which is a sentence
        about nothing at all and worse than the false one, because the
        false one at least shows.
        """
        p = _model((self._blown_tieback(), _ACROSS))
        notes = _notes(p, _result(p))
        assert len(notes) == 1, notes
        assert "puts no force" not in notes[0], notes
        assert "put no force" not in notes[0], notes
        assert "zero-stress envelope" in notes[0], notes

    def test_the_two_halves_can_be_told_apart_in_one_model(self):
        """One of each, and the sentence keeps them separate.

        The count of supports that put no force has to be 1 of the 2 —
        not 2, which would swallow a support that contributed, and not 0.
        """
        p = _model((self._blown_tieback(), _ACROSS),
                   (_blown(type(_geo()), "interface_tau", _runtime_error,
                           **_GEO), _SECOND))
        notes = _notes(p, _result(p))
        assert len(notes) == 2, notes
        assert "1 of the 2 supports placed put no force" in notes[0], notes
        assert "zero-stress envelope" in notes[1], notes


# ======================================================================
class TestTheContractForAProfileThatWillNotBuild:
    """``SupportEvaluationError`` from the sampling reaches D94's handler.

    ``docs/plugins.md`` lists "a profile that will not build" among the
    reasons a type may raise it, and the docstring of the exception itself
    repeats the promise. Measured on the tree of 0.1.162, a type that
    honoured it got the same answer as one with a plain bug: swallowed,
    priced off an envelope, and reported as developing no capacity.
    """

    def _refused(self):
        return _blown(type(_geo()), "interface_tau", _evaluation_error,
                      **_GEO)

    def test_that_one_support_is_left_out_and_named(self):
        from ogr_slip2d.support_integration import SUPPORT_NOT_PRICEABLE

        p = _model((self._refused(), _ACROSS))
        assert _why(p) == [SUPPORT_NOT_PRICEABLE]
        assert _effects(p) == []

    def test_the_reason_travels_on_the_result(self):
        p = _model((self._refused(), _ACROSS))
        det = _result(p).details or {}
        assert "will not build" in det.get("support_failure", ""), det

    def test_and_the_note_says_it_could_not_be_priced(self):
        p = _model((self._refused(), _ACROSS))
        assert "could not price" in _notes(p, _result(p))[0]

    def test_the_other_supports_still_count(self):
        """D94's rule, one level down: it costs that support and no other.

        Without this, routing the typed exception into the per-support
        handler could have been done by dropping the whole reinforcement,
        which is the answer D94 exists to prevent.
        """
        p = _model((self._refused(), _ACROSS), (_nail(), _SECOND))
        assert [e.support_id for e in _effects(p)] == [p.supports[1].id]
        assert _bishop(p) > _bishop(_bare())


# ======================================================================
class TestASoundProfileChangesNothing:
    """What "zero digits moved" means where the suite can check it."""

    def test_no_reason_is_recorded_for_any_of_the_four_types(self):
        assert _why(_model((_geo(), _ACROSS))) == []
        assert _why(_model((_tieback(), _ACROSS))) == []
        assert _why(_model((_anchor(), _ACROSS))) == []
        T, sound, _b, _bare_p = _pile_models()
        from ogr_slip2d.slicer import slice_surface
        from ogr_slip2d.support_integration import compute_support_effects
        sl = slice_surface(sound, T._circle(), num_slices=40)
        out: list = []
        compute_support_effects(sound, T._circle(), sl, reasons=out)
        assert out == []

    def test_and_no_note_is_written(self):
        p = _model((_tieback(), _ACROSS))
        assert _notes(p, _result(p)) == []

    def test_the_cache_still_holds_the_profiles_it_built(self):
        """The registers are additions, not a replacement.

        A ``dict`` subclass that stopped behaving like the mapping every
        reader indexes would be a far larger change than the one this
        defect asks for.
        """
        from ogr_slip2d.support_integration import _bond_profiles

        p = _model((_geo(), _ACROSS))
        profiles = _bond_profiles(p)
        assert set(profiles) == {p.supports[0].id}
        assert profiles.failed == {} and profiles.refused == {}


# ======================================================================
class TestTheShapeInTheSource:
    """The shape D95 closes on cannot come back through a refactor.

    Comments are stripped before looking, for the reason
    ``test_support_failure_v1161.py`` gives: the comment explaining each
    of these handlers QUOTES what it replaced and names the defect, and a
    check that cannot tell code from prose would be measuring the prose.
    """

    def _code(self, fn):
        import inspect

        src = inspect.getsource(fn)
        lines = [l.split("#")[0].rstrip() for l in src.splitlines()]
        return [l for l in lines if l.strip()]

    def test_the_wide_handler_records_the_exception_class(self):
        from ogr_slip2d import support_integration as si

        code = self._code(si._bond_profiles)
        wide = [i for i, l in enumerate(code) if "except Exception" in l]
        assert wide, code
        assert any("failed[" in l for l in code[wide[0]:]), code

    def test_the_typed_exception_is_let_through_first(self):
        from ogr_slip2d import support_integration as si

        code = self._code(si._bond_profiles)
        typed = [i for i, l in enumerate(code)
                 if "except SupportEvaluationError" in l]
        wide = [i for i, l in enumerate(code) if "except Exception" in l]
        assert typed and wide, code
        # The order is the whole fix, exactly as in D98: Python takes the
        # first matching clause and ``SupportEvaluationError`` is a
        # ``RuntimeError``, so a wide handler placed first swallows it
        # precisely as the single one did before this version.
        assert typed[0] < wide[0], code

    def test_the_note_reads_the_same_constants_that_write_them(self):
        from ogr_slip2d import support_integration as si

        code = self._code(si.uncontributing_support_notes)
        assert any("SUPPORT_BOND_PROFILE_NO_FORCE" in l for l in code), code
        assert any("SUPPORT_BOND_PROFILE_FAILED" in l for l in code), code

    def test_the_sentences_avoid_the_substrings_the_bank_reserves(self):
        """Three closures of the verification bank grep whole runs.

        ``d40()`` fires on "stable" AND "head" appearing in any warning,
        ``d69()`` on "edge of the search grid" and ``d71()`` on
        "path_optimize". A new sentence carrying one of them would break a
        closure that has nothing to do with this defect. Note that
        "unstable" contains "stable" and "ahead" contains "head".
        """
        blown = _blown(type(_geo()), "interface_tau", _runtime_error, **_GEO)
        p = _model((blown, _ACROSS),
                   (_blown(type(_tieback()), "interface_tau", _runtime_error,
                           **_TIEBACK), _SECOND))
        for note in _notes(p, _result(p)):
            assert not ("stable" in note and "head" in note), note
            assert "edge of the search grid" not in note, note
            assert "path_optimize" not in note, note


# ======================================================================
try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except Exception:  # noqa: BLE001 - pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


_WINDOWS: list = []   # Qt destroys the widgets with the owning window


@_requires_qt
class TestTheInterfaceSaysItToo:
    """The two places that build a profile of their own.

    Neither goes through ``_bond_profiles``: the canvas tooltip and the
    Support Force Diagram call ``build_bond_profile`` directly, each
    inside a blanket handler of its own. With the engine fixed and these
    two left alone they would have been the only mouths still shut, and
    the worse for it — the diagram would plot a flat zero for a
    geosynthetic in coefficient mode while the analysis now says in words
    why that zero happened.
    """

    def test_the_force_diagram_says_the_profile_would_not_build(self):
        from ogr_gui.dialogs.support_force_diagram import (
            SupportForceDiagramWindow)

        QApplication.instance() or QApplication([])
        blown = _blown(type(_geo()), "interface_tau", _runtime_error, **_GEO)
        p = _model((blown, _ACROSS))
        # NOT modal, like every informative chart in this program: a test
        # that reaches ``exec()`` hangs forever without a screen.
        w = SupportForceDiagramWindow(p)
        _WINDOWS.append(w)
        note = w.note.text()
        assert "bond profile" in note, note
        assert "RuntimeError" in note, note

    def test_and_stays_quiet_when_the_profile_builds(self):
        from ogr_gui.dialogs.support_force_diagram import (
            SupportForceDiagramWindow)

        QApplication.instance() or QApplication([])
        w = SupportForceDiagramWindow(_model((_geo(), _ACROSS)))
        _WINDOWS.append(w)
        assert "bond profile" not in w.note.text()

    def test_the_canvas_tooltip_says_it(self):
        from ogr_gui.canvas.graphics_items import SupportItem

        QApplication.instance() or QApplication([])
        blown = _blown(type(_geo()), "interface_tau", _runtime_error, **_GEO)
        p = _model((blown, _ACROSS))
        item = SupportItem(p.supports[0], "Geosynthetic", blown, None, p)
        assert "Bond profile could not be built" in item.toolTip()
        assert "RuntimeError" in item.toolTip()

    def test_the_tooltip_stays_quiet_when_the_profile_builds(self):
        from ogr_gui.canvas.graphics_items import SupportItem

        QApplication.instance() or QApplication([])
        stype = _geo()
        p = _model((stype, _ACROSS))
        item = SupportItem(p.supports[0], "Geosynthetic", stype, None, p)
        assert "Bond profile could not be built" not in item.toolTip()

    def test_both_sentences_are_translated(self):
        """Rule 2: every visible string has its Spanish entry."""
        from ogr_gui.i18n import set_language, tr

        english = [
            "Bond profile could not be built (%s): the forces above are "
            "the envelope at zero effective stress.",
            "The bond profile of this support could not be built (%s): the "
            "capacities below are its envelope at zero effective stress, "
            "not the ones the stress state would give.",
        ]
        try:
            set_language("es")
            for s in english:
                assert tr(s) != s, s
                assert "perfil de adherencia" in tr(s), tr(s)
        finally:
            # Rule 5: the active language is global state, and a test that
            # left it in Spanish once broke unrelated menu tests only when
            # the whole suite ran.
            set_language("en")

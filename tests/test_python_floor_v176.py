# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.76 — the source parses with the OLDEST Python the project claims.

Invariant protected: every ``.py`` in the repository is valid syntax for
the minimum interpreter declared in ``pyproject.toml``
(``requires-python``), not merely for the one the developer happens to
have installed.

Why this file exists. ``main_window.py`` carried, from v0.1.70 to
v0.1.75, an f-string whose replacement field contained an implicitly
concatenated literal split across two lines::

    f"... {tr('first half '
              'second half')} ..."

PEP 701 made that legal in Python 3.12. In 3.11 an f-string is a single
token, so the line break ends the literal and the file does not parse at
all. The development machine runs 3.14 and never saw it; the CI job for
3.11 had been red for five releases, failing on an *import*, which reads
like dozens of unrelated test failures.

Two things this file had to get right, both of which cost a wrong turn:

1. ``ast.parse(src, feature_version=(3, 11))`` does NOT catch it. It
   parses the broken file without complaint, because ``feature_version``
   gates a handful of semantic checks and does not revert the tokenizer
   to the pre-PEP-701 grammar. Verified against the offending revision.
2. So the check has to work on tokens — but ``FSTRING_START`` only
   exists from 3.12 on. Hence the split below: when the interpreter is
   at or below the declared floor, ``compile()`` answers the question
   exactly and there is nothing to approximate; only when running above
   the floor does the token scan stand in for the interpreter we do not
   have.
"""
from __future__ import annotations

import glob
import io
import re
import sys
import tokenize
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKSLASH = chr(92)
_NEWLINE = chr(10)

#: The version that legalised everything ``_fstring_defects`` looks for.
#: Once the declared floor reaches it, the scan has nothing left to say
#: and must stop talking — a check that outlives its constraint turns
#: into a source of false positives, which is how checks get deleted.
_PEP701 = (3, 12)


def _label(path: Path) -> str:
    """A short name for ``path``, which need not live under the repo.

    The scanner is exercised on temporary files by its own regression
    tests, and ``relative_to`` raises for anything outside the root.
    """
    try:
        return str(path.relative_to(_ROOT))
    except ValueError:
        return path.name


def _floor() -> tuple[int, int]:
    """The minimum Python version ``pyproject.toml`` promises to support.

    Read rather than hard-coded: when the floor rises to 3.12 this whole
    check becomes vacuous and must stop firing on its own, instead of
    outliving the constraint it enforces.
    """
    text = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'requires-python\s*=\s*["\'][^0-9]*(\d+)\.(\d+)', text)
    if m is None:  # pragma: no cover - packaging metadata is tested elsewhere
        return (3, 11)
    return (int(m.group(1)), int(m.group(2)))


def _sources():
    for f in glob.glob(str(_ROOT / "**" / "*.py"), recursive=True):
        if "__pycache__" in f or f"{Path(f).parts[0]}" == ".git":
            continue
        yield Path(f)


def _fstring_defects(path: Path) -> list[str]:
    """Constructs in ``path`` that only Python 3.12+ accepts.

    Walks each f-string from ``FSTRING_START`` to its matching
    ``FSTRING_END``, counting nesting so an inner f-string is examined as
    part of the outer expression rather than as a second literal. Three
    things were illegal before PEP 701:

    - a single-quoted (non-triple) f-string spanning more than one line;
    - the delimiting quote reappearing inside a replacement field;
    - a backslash inside a replacement field.

    The backslash rule is deliberately limited to replacement fields. A
    backslash in the *literal* part — ``f"line{n}\\n"`` — has always been
    legal, and there are seventeen such f-strings in this repository;
    flagging them would make the check noise instead of a guard.
    """
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    defects: list[str] = []

    # Below 3.12 there are no FSTRING_* tokens to walk — an f-string is a
    # single STRING token — and none are needed: the running interpreter
    # IS the floor, so it answers the question exactly. Discovered the
    # hard way, on the very CI job this file was written to protect: the
    # scanner's own unit tests called this helper unconditionally and
    # died with AttributeError on 3.11.
    if not hasattr(tokenize, "FSTRING_START"):
        try:
            compile(src, str(path), "exec")
        except SyntaxError as exc:
            return [f"{_label(path)}:{exc.lineno}: {exc.msg}"]
        return []

    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError) as exc:
        return [f"{_label(path)}: cannot tokenise ({exc})"]

    depth = 0
    start = None
    quote = ""
    inner: list[tokenize.TokenInfo] = []
    for tok in toks:
        if tok.type == tokenize.FSTRING_START:
            depth += 1
            if depth == 1:
                start, quote, inner = tok.start, tok.string.lstrip("fFrRbB"), []
                continue
        elif tok.type == tokenize.FSTRING_END:
            depth -= 1
            if depth == 0:
                end = tok.end
                triple = len(quote) == 3
                reasons = []
                if not triple and start[0] != end[0]:
                    reasons.append(
                        "a single-quoted f-string spans lines "
                        f"{start[0]}-{end[0]}")
                for t in inner:
                    if t.type == tokenize.FSTRING_MIDDLE:
                        continue
                    if quote[0] in t.string:
                        reasons.append(
                            f"the delimiting quote {quote[0]} is reused "
                            f"inside the replacement field ({t.string!r})")
                    if _BACKSLASH in t.string:
                        reasons.append(
                            "a backslash appears inside the replacement "
                            f"field ({t.string!r})")
                if reasons:
                    raw = lines[start[0] - 1][start[1]:].rstrip(_NEWLINE)
                    defects.append(
                        f"{_label(path)}:{start[0]}: "
                        + "; ".join(dict.fromkeys(reasons))
                        + f"  --> {raw[:70]}")
                continue
        if depth >= 1:
            inner.append(tok)
    return defects


class TestPythonFloor:
    def test_every_source_parses_on_the_declared_minimum(self):
        """A file the floor interpreter cannot parse breaks on import.

        Not "some tests fail": the module never loads, so every test that
        touches it dies with the same traceback and the real cause is one
        line buried in a wall of noise.
        """
        floor = _floor()
        if floor >= _PEP701 and sys.version_info[:2] > floor:
            # The floor already accepts every construct the scan looks
            # for, and this interpreter is above it, so there is nothing
            # this test can honestly assert. Passing quietly beats
            # inventing offenders out of legal code.
            return
        offenders: list[str] = []
        for p in _sources():
            src = p.read_text(encoding="utf-8")
            if sys.version_info[:2] <= floor:
                # We ARE the floor: the interpreter is the authority.
                try:
                    compile(src, str(p), "exec")
                except SyntaxError as exc:
                    offenders.append(
                        f"{_label(p)}:{exc.lineno}: {exc.msg}")
            else:
                offenders.extend(_fstring_defects(p))
        assert not offenders, (
            f"{len(offenders)} construct(s) newer than Python "
            f"{floor[0]}.{floor[1]}, which pyproject.toml declares as the "
            f"minimum:" + _NEWLINE + _NEWLINE.join(offenders[:10]))

    def test_the_scanner_recognises_the_construct_that_caused_this(self, tmp_path):
        """The guard must fail on the v0.1.70 defect, or it guards nothing.

        A check that has only ever been observed passing is indistinguishable
        from a check that cannot fail. This reproduces the exact shape that
        broke CI — an implicitly concatenated literal split across lines
        inside a replacement field — and asserts it is caught.

        Runs on every interpreter. Below 3.12 the defect is caught by
        ``compile`` and reported as "unterminated string literal"; above,
        by the token walk, as "spans lines". Either wording is the same
        finding, and asserting only one of them is what left this test
        dead on the one version it was written for.
        """
        bad = tmp_path / "regression.py"
        bad.write_text(
            "def f(tr, x):\n"
            "    return f\"a {tr('first half '\n"
            "                    'second half')} b {x}\"\n",
            encoding="utf-8",
        )
        found = _fstring_defects(bad)
        assert found, "the scanner missed the construct it exists to catch"
        assert ("spans lines" in found[0]
                or "unterminated" in found[0].lower()), found

    def test_the_pre_312_fallback_reports_a_syntax_error(self, tmp_path):
        """Exercise the branch CI runs on the floor interpreter.

        On 3.11 there are no FSTRING_* tokens, so ``_fstring_defects``
        delegates to ``compile``. That branch cannot be tested here by
        feeding it the PEP 701 construct — this interpreter's ``compile``
        accepts it, which is precisely why the token walk exists above
        3.12 — so it is fed a syntax error every version rejects, which
        proves the plumbing: compile raises, and the failure comes back
        as a located defect string rather than an exception.
        """
        broken = tmp_path / "broken.py"
        broken.write_text("def f(:\n    pass\n", encoding="utf-8")
        saved = getattr(tokenize, "FSTRING_START", None)
        if saved is not None:
            del tokenize.FSTRING_START
        try:
            found = _fstring_defects(broken)
        finally:
            if saved is not None:
                tokenize.FSTRING_START = saved
        assert found and "broken.py" in found[0], found

    def test_a_backslash_in_the_literal_part_is_not_flagged(self, tmp_path):
        """``f"{n}\\n"`` is legal in 3.11 and must stay unflagged.

        Seventeen f-strings in this repository put an escape in the text
        part. A guard that rejected them would be turned off within a
        week, which is worse than not having it.
        """
        ok = tmp_path / "legal.py"
        ok.write_text(
            'def f(n):\n'
            '    return f"count: {n}\\n" + f"{n}: {chr(92)}"\n',
            encoding="utf-8",
        )
        assert not _fstring_defects(ok)

    def test_the_check_retires_when_the_floor_reaches_312(self, tmp_path):
        """Raising ``requires-python`` to 3.12 must switch this off.

        Not cosmetic. Every rule the scan enforces became legal in 3.12,
        so against a 3.12 floor it would report ordinary, correct code as
        an offence — and a check that cries wolf gets deleted, taking the
        real protection with it. Asserted rather than trusted, because
        the first version of this file documented the behaviour without
        implementing it.
        """
        import test_python_floor_v176 as mod

        # Outside the repository on purpose: while it exists it would be
        # a source file with no SPDX header, and the licence test scans
        # every .py in the tree.
        offender = Path(tmp_path) / "retire_probe.py"
        saved_floor = mod._floor
        saved_sources = mod._sources
        offender.write_text(
            "def f(tr, x):\n"
            "    return f\"a {tr('first half '\n"
            "                    'second half')} b {x}\"\n",
            encoding="utf-8",
        )
        try:
            mod._sources = lambda: iter([offender])

            mod._floor = lambda: (3, 11)
            try:
                self.test_every_source_parses_on_the_declared_minimum()
                on_duty = False
            except AssertionError:
                on_duty = True

            mod._floor = lambda: (3, 12)
            self.test_every_source_parses_on_the_declared_minimum()
        finally:
            mod._floor = saved_floor
            mod._sources = saved_sources
            offender.unlink(missing_ok=True)

        # Same file, same interpreter: an offence against a 3.11 floor,
        # and nothing at all against a 3.12 one.
        assert on_duty, "the scan did not fire against a 3.11 floor"

    def test_the_floor_comes_from_packaging_metadata(self):
        """The declared floor is what CI runs, so it is what we check."""
        floor = _floor()
        assert floor >= (3, 0)
        wf = _ROOT / ".github" / "workflows"
        texts = [p.read_text(encoding="utf-8") for p in wf.glob("*.yml")]
        declared = f"{floor[0]}.{floor[1]}"
        assert any(declared in t for t in texts), (
            f"pyproject.toml promises Python {declared} but no CI job "
            f"runs it, so the promise is untested")

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
        """
        if sys.version_info[:2] <= _floor():
            # Below 3.12 the file cannot even be written and re-read as
            # source without the interpreter rejecting it, which is the
            # point: there is nothing to approximate.
            return
        bad = tmp_path / "regression.py"
        bad.write_text(
            "def f(tr, x):\n"
            "    return f\"a {tr('first half '\n"
            "                    'second half')} b {x}\"\n",
            encoding="utf-8",
        )
        found = _fstring_defects(bad)
        assert found, "the scanner missed the construct it exists to catch"
        assert "spans lines" in found[0], found

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

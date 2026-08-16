# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.81 — the CI cannot silently fall back onto a retired Node runtime.

Invariant protected: every GitHub Action pinned in ``.github/workflows``
sits at or above the major that this project has vetted, and every action
in use has a vetted major at all.

Why this file exists. A JavaScript action declares the Node runtime it
wants in its own ``action.yml``; the workflow cannot override it. So
``actions/checkout@v4`` meant ``node20``, and when Node 20 left the
runners in the autumn of 2026 the only fix was a version bump. GitHub had
been saying so since September 2025 — as a yellow annotation, on a tab
nobody opens while the build is green. Two months of warnings reached
nobody.

Dependabot (``.github/dependabot.yml``) now covers the forward direction:
a new major arrives as an open pull request. This file covers the
backward one, which Dependabot cannot: nothing stops a merge, a revert or
a copied snippet from putting ``@v4`` back, and the CI would go green
while quietly depending on a runtime that no longer exists.

What this is NOT: a snapshot of what the workflow says today. The table
below is a *declared floor* with a stated reason — "the first major that
runs on ``node24``" — so it fails for a reason a reader can check, and it
is edited deliberately rather than refreshed to match whatever is there.
"""
from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_WORKFLOWS = _ROOT / ".github" / "workflows"

#: Minimum major version accepted for each action, and why.
#:
#: ``node24`` is the reason for both numbers, not novelty: ``checkout@v5``
#: and ``setup-python@v6`` were the first majors to declare it, and v7 is
#: what the project pinned so the jump would not be due again within the
#: year. Anything below these floors declares ``node20``, which the
#: runners no longer provide.
MIN_MAJOR = {
    "actions/checkout": 7,
    "actions/setup-python": 7,
}

#: ``uses:`` may appear as a step (``- uses: x``) or on its own line.
_USES = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)", re.MULTILINE)


def _workflow_files() -> list[Path]:
    return sorted(_WORKFLOWS.glob("*.yml")) + sorted(_WORKFLOWS.glob("*.yaml"))


def _pins() -> list[tuple[str, str, str]]:
    """Every ``uses:`` in the workflows as ``(file, action, ref)``."""
    found = []
    for path in _workflow_files():
        text = path.read_text(encoding="utf-8")
        for ref in _USES.findall(text):
            action, _, version = ref.partition("@")
            found.append((path.name, action, version))
    return found


class TestActionPins:
    def test_the_scan_finds_the_pins_it_is_supposed_to_guard(self):
        """A scanner that matches nothing passes every other test here.

        That is precisely the failure this file exists to prevent, so the
        scan has to prove it can see before it is allowed to judge: if a
        rename or a syntax change ever makes ``_USES`` stop matching, the
        silence must be a failure and not a green tick.
        """
        pins = _pins()
        assert _workflow_files(), "no workflow files found under .github/workflows"
        assert pins, "the `uses:` scan matched nothing — the guard is blind"
        actions = {action for _, action, _ in pins}
        for expected in MIN_MAJOR:
            assert expected in actions, (
                f"{expected} is vetted below but no workflow uses it; "
                f"found {sorted(actions)}")

    def test_every_pinned_action_meets_its_vetted_floor(self):
        """Below the floor the action asks for a runtime that is gone."""
        stale = []
        for name, action, version in _pins():
            floor = MIN_MAJOR.get(action)
            if floor is None:
                continue  # reported by the test below, not here
            match = re.fullmatch(r"v?(\d+)(?:\.\d+)*", version)
            # A commit SHA carries no major, so the floor cannot be
            # checked against it. That is a deliberate refusal rather
            # than a gap: pinning by SHA is a reasonable hardening step,
            # but it has to come with a decision about how this guard
            # keeps working, not slip past it unnoticed.
            assert match, (
                f"{name}: {action}@{version} is not a version tag, so its "
                f"major cannot be checked against the vetted floor")
            if int(match.group(1)) < floor:
                stale.append((name, f"{action}@{version}", f"needs v{floor}+"))
        assert not stale, (
            "actions below their vetted major (these declare node20, which "
            f"the runners no longer provide): {stale}")

    def test_every_action_in_use_has_been_vetted(self):
        """An action added without a floor is an unguarded dependency.

        Silence about a new action reads the same as approval, which is
        how the node20 warning survived two months.
        """
        unvetted = sorted({
            f"{action} (in {name})"
            for name, action, _ in _pins()
            if action not in MIN_MAJOR
        })
        assert not unvetted, (
            "actions used in CI with no vetted minimum major in "
            f"MIN_MAJOR: {unvetted}")


class TestDependabotWatchesTheActions:
    def test_dependabot_is_configured_for_github_actions(self):
        """The forward-looking half of the guard has to actually exist."""
        cfg = _ROOT / ".github" / "dependabot.yml"
        assert cfg.exists(), "no .github/dependabot.yml"
        txt = cfg.read_text(encoding="utf-8")
        assert "package-ecosystem: github-actions" in txt

    def test_dependabot_does_not_watch_python_dependencies(self):
        """Deliberate: a NumPy or Shapely bump has to go through the
        published validation cases, and an automatic PR invites merging
        it on a green tick that proves less than it looks."""
        txt = (_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
        assert "package-ecosystem: pip" not in txt

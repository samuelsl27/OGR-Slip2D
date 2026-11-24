# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.490 (D430) -- the command line says why it cannot open a ``.ogr``.

Invariant protected: ``info`` and ``compute``, given a path that exists
but is not a readable ``.ogr``, print ONE line ``Cannot open project:
<reason>`` and exit with 1 -- no Python traceback -- and the reason is the
one ``ogr_api.ops.project.load_ogr`` gives the agent (D422). A valid
``.ogr`` still prints its table with code 0, and a missing path still says
``File not found``.

Why. Both commands read with a bare ``Project.load``: a folder named
``carpeta.ogr``, a root that is a list or a cut JSON ended in the 52-63
line traceback typer paints, with the reason on its last line. The
reference here is ``load_ogr``'s sentence, computed by calling it, not a
capture of what the CLI prints: the CLI must not grow a second list of
what counts as unreadable (AGENTS.md, «Capas»).
"""
from __future__ import annotations

from pathlib import Path

_CASES = ("folder", "list", "cut", "bytes", "null")


def _make(tmp_path, case) -> Path:
    path = Path(tmp_path) / f"{case}.ogr"
    if case == "folder":
        path.mkdir()
    elif case == "list":
        path.write_text("[]\n", encoding="utf-8")
    elif case == "cut":
        path.write_text('{"name": "x", "materials": [\n', encoding="utf-8")
    elif case == "bytes":
        path.write_bytes(b"\xff\xfe{}")
    elif case == "null":
        path.write_text("null\n", encoding="utf-8")
    return path


def _sub(tmp_path, name) -> Path:
    sub = Path(tmp_path) / name
    sub.mkdir(exist_ok=True)
    return sub


def _reason(path) -> str:
    """What the agent is told about ``path`` (the reference)."""
    from ogr_api.errors import InvalidArgument
    from ogr_api.ops.project import load_ogr
    try:
        load_ogr(path.resolve())
    except InvalidArgument as exc:
        return exc.message
    raise AssertionError(f"{path} opened")


def _run(args):
    from typer.testing import CliRunner
    from ogr_cli.__main__ import app
    return CliRunner().invoke(app, [str(a) for a in args])


class TestUnreadable:
    def _check(self, tmp_path, command):
        for case in _CASES:
            path = _make(_sub(tmp_path, command), case)
            out = path.parent / f"{case}.h5"
            args = [command, path] + (["--output", out]
                                      if command == "compute" else [])
            res = _run(args)
            assert res.exit_code == 1, (case, res.output)
            assert "Traceback" not in res.output, case
            lines = [ln for ln in res.output.splitlines() if ln.strip()]
            assert lines == [f"Cannot open project: {_reason(path)}"], lines
            # it reads before it writes: nothing is left at --output
            assert not out.exists(), case

    def test_info_says_it_in_one_line_with_code_one(self, tmp_path):
        self._check(tmp_path, "info")

    def test_compute_says_it_in_one_line_with_code_one(self, tmp_path):
        self._check(tmp_path, "compute")

    def test_a_missing_path_is_still_not_found(self, tmp_path):
        for command in ("info", "compute"):
            path = Path(tmp_path) / "nowhere.ogr"
            res = _run([command, path])
            assert res.exit_code == 1, command
            assert "File not found:" in res.output, command
            assert "Cannot open project" not in res.output, command

    def test_a_valid_project_still_prints_its_table(self, tmp_path):
        from ogr_core.project.demo import build_demo_project
        path = Path(tmp_path) / "demo.ogr"
        project = build_demo_project()
        project.save(path)
        res = _run(["info", path])
        assert res.exit_code == 0, res.output
        assert "Cannot open project" not in res.output
        assert "Materials" in res.output
        assert project.materials[0].name in res.output

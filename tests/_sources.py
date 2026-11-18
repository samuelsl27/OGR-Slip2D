# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.473 (spec 010) — where the sources a census reads are: the core's in
the tree of the ``ogr_core`` that is imported, this repository's here.

Until v0.1.471 every census of this suite found the core under
``_ROOT / "ogr_core"``. The core left this repository for OGR-Core, and a
census that kept looking there either failed (``FileNotFoundError``) or,
worse, walked an empty folder and passed. So nothing here returns nothing:
:func:`source` fails on a file that is not there, and :func:`package_files`
on a package with no sources.

The keys a census writes stay ``"ogr_core/…"`` and ``"ogr_slip2d/…"``:
:func:`relative` gives them from either tree. The tree of the core is the one
the runner names in its banner (``shared: ogr_core …``), the one the tests
import.

Not a test file: the runner collects ``test_*.py`` only.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent

#: For the teeth of the censuses only: the folder that holds ``ogr_core``
#: instead of the imported one (``OGR_TEST_CORE_ROOT``, read once, or set by
#: ``test_sources_v1473``). Pointed at an empty folder, every census that
#: reads the core must fail.
_CORE_ROOT: Optional[Path] = (Path(os.environ["OGR_TEST_CORE_ROOT"])
                              if os.environ.get("OGR_TEST_CORE_ROOT") else None)


def core_root() -> Path:
    """The folder that holds the imported ``ogr_core`` (its parent)."""
    if _CORE_ROOT is not None:
        return Path(_CORE_ROOT)
    import ogr_core
    return Path(ogr_core.__file__).resolve().parent.parent


def root_for(rel) -> Path:
    """The tree a repository-relative path such as ``ogr_core/dxf/x.py`` or
    ``ogr_gui/main_window.py`` lives in."""
    first = str(rel).replace("\\", "/").split("/", 1)[0]
    return core_root() if first == "ogr_core" else ROOT


def source(rel) -> Path:
    """The file ``rel`` (``"ogr_core/…"`` or a path of this repository),
    which must exist."""
    rel = str(rel).replace("\\", "/")
    path = root_for(rel) / rel
    if not path.is_file():
        raise FileNotFoundError(f"{rel}: not in {root_for(rel)}")
    return path


def package_files(package: str) -> list:
    """Every ``.py`` of ``package``, sorted; fails if there is none."""
    files = sorted((root_for(package) / package).rglob("*.py"))
    if not files:
        raise AssertionError(f"no sources of {package} under "
                             f"{root_for(package)}: the census would see "
                             f"nothing and pass")
    return files


def relative(path) -> str:
    """The key of ``path`` in a census: relative to the tree it is in, with
    forward slashes (``ogr_core/project/rules.py``)."""
    path = Path(path).resolve()
    for root in (core_root(), ROOT):
        try:
            return path.relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
    raise ValueError(f"{path} is in neither tree")

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.473 (spec 010) — a census of this suite cannot pass by finding nothing.

The core left this repository for OGR-Core. Two dozen tests read its sources
by path, and the ensayo of the move found both ways of getting it wrong:
thirty failed with ``FileNotFoundError``, and some passed because they
walked an empty folder (``test_core_layering_v1340`` matched an empty
allow-list; ``test_settings_coverage_v1103`` stopped seeing who reads a
setting). They all read through ``tests/_sources.py`` now, and that module
is what this file holds to:

* the core is the tree of the ``ogr_core`` that is imported, and its keys
  are still ``ogr_core/…``;
* a file that is not there is an error, and so is a package with no sources;
* pointed at an empty folder, the censuses that read the core fail (one of
  each kind is run here: the whole-core walk and the single file).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import _sources as S  # noqa: E402


class _EmptyCore:
    """``_sources`` pointed at an empty folder, and put back."""

    def __enter__(self):
        self.saved = S._CORE_ROOT
        S._CORE_ROOT = Path(tempfile.mkdtemp(prefix="ogr_test_nocore_"))
        return self

    def __exit__(self, *exc):
        S._CORE_ROOT = self.saved
        return False


class TestTheTrees:
    def test_the_core_is_the_imported_one(self):
        import ogr_core
        assert S.core_root() == Path(ogr_core.__file__).resolve().parent.parent

    def test_the_keys_stay_as_they_were(self):
        assert S.relative(S.source("ogr_core/project/rules.py")) == \
            "ogr_core/project/rules.py"
        assert S.relative(S.source("ogr_gui/main_window.py")) == \
            "ogr_gui/main_window.py"
        assert S.root_for("ogr_core/x.py") == S.core_root()
        assert S.root_for("ogr_slip2d/x.py") == S.ROOT

    def test_the_whole_core_is_seen(self):
        files = S.package_files("ogr_core")
        assert len(files) > 80
        assert S.source("ogr_core/fem/seepage.py") in files


class TestNothingIsAnError:
    def test_a_missing_file(self):
        with pytest.raises(FileNotFoundError):
            S.source("ogr_core/no_such_module.py")

    def test_a_package_with_no_sources(self):
        with _EmptyCore():
            with pytest.raises(AssertionError):
                S.package_files("ogr_core")

    def test_a_census_of_the_whole_core_fails(self):
        import test_core_layering_v1340 as L
        with _EmptyCore():
            with pytest.raises(AssertionError):
                L.TestTheCensusSeesTheCore().test_it_reads_the_whole_imported_core()

    def test_a_census_of_one_file_fails(self):
        import test_dxf_drawings_v1341 as D
        with _EmptyCore():
            with pytest.raises(FileNotFoundError):
                D.TestTheCensusLosesTheExporter() \
                    .test_the_exporter_imports_nothing_above()

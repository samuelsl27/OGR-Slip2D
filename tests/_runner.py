# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Minimal test runner for environments without pytest.

Discovers classes starting with 'Test' in tests/*.py, instantiates them,
and runs methods starting with 'test_'. Supports the small subset of
pytest features used in the OGR test suite:

    - pytest.approx()
    - pytest.raises(...)
    - tmp_path fixture (emulated with tempfile)

Not a replacement for pytest in production — only a smoke-test tool
that allows verifying the suite in air-gapped CI environments.
"""
from __future__ import annotations

import importlib.util
import inspect
import math
import sys
import tempfile
import traceback
from contextlib import contextmanager
from pathlib import Path


# --- pytest compatibility shim ----------------------------------------
class _Approx:
    def __init__(self, expected, rel=None, abs_=None):
        self.expected = expected
        self.rel = rel
        self.abs = abs_

    def __eq__(self, other):
        if self.abs is not None:
            return math.isclose(other, self.expected, abs_tol=self.abs)
        tol = self.rel if self.rel is not None else 1e-6
        return math.isclose(other, self.expected, rel_tol=tol, abs_tol=1e-9)

    def __repr__(self):
        return f"approx({self.expected})"


def _approx(expected, rel=None, abs=None):  # noqa: A002
    return _Approx(expected, rel=rel, abs_=abs)


@contextmanager
def _raises(exc_type):
    try:
        yield
    except exc_type:
        return
    except Exception as e:
        raise AssertionError(f"Expected {exc_type.__name__}, got {type(e).__name__}")
    raise AssertionError(f"Expected {exc_type.__name__}, no exception raised")


class _FakePytest:
    approx = staticmethod(_approx)
    raises = staticmethod(_raises)


sys.modules["pytest"] = _FakePytest()  # type: ignore


# --- Discovery & runner -----------------------------------------------
def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = mod
    spec.loader.exec_module(mod)
    return mod


def _run_method(instance, method):
    # Bind the unbound function to the instance so `self` is provided
    bound = method.__get__(instance, type(instance))
    sig = inspect.signature(bound)
    kwargs = {}
    if "tmp_path" in sig.parameters:
        tmpdir = tempfile.mkdtemp()
        kwargs["tmp_path"] = Path(tmpdir)
    bound(**kwargs)


def main(tests_dir: Path) -> int:
    # The ✓/✗ marks below are not printable in the console codepage Windows
    # picks when stdout is redirected (cp1252), and the UnicodeEncodeError
    # lands *inside* the except branch that reports a failure — so a single
    # unprintable character turns a full run into a traceback. Widening the
    # encoding here keeps `python tests/_runner.py > log.txt` usable.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # non-reconfigurable stream
        pass

    passed = 0
    failed = 0
    fail_details: list[tuple[str, str]] = []

    test_files = sorted(p for p in tests_dir.glob("test_*.py"))
    for f in test_files:
        print(f"\n=== {f.name} ===")
        try:
            mod = _load_module(f)
        except Exception as e:  # noqa: BLE001
            print(f"  [LOAD ERROR] {e}")
            fail_details.append((f.name, traceback.format_exc()))
            failed += 1
            continue

        for name, cls in inspect.getmembers(mod, inspect.isclass):
            if not name.startswith("Test"):
                continue
            if cls.__module__ != mod.__name__:
                continue
            print(f"  {name}:")
            for m_name, m in inspect.getmembers(cls, inspect.isfunction):
                if not m_name.startswith("test_"):
                    continue
                try:
                    instance = cls()
                    _run_method(instance, m)
                    print(f"    ✓ {m_name}")
                    passed += 1
                except AssertionError as e:
                    print(f"    ✗ {m_name}: {e}")
                    fail_details.append((f"{name}.{m_name}", traceback.format_exc()))
                    failed += 1
                except Exception as e:  # noqa: BLE001
                    print(f"    ✗ {m_name}: {type(e).__name__}: {e}")
                    fail_details.append((f"{name}.{m_name}", traceback.format_exc()))
                    failed += 1

    print("\n" + "=" * 60)
    print(f"Total: {passed + failed}    Passed: {passed}    Failed: {failed}")

    if fail_details:
        print("\n--- FAILURE DETAILS ---")
        for name, tb in fail_details[:10]:
            print(f"\n[{name}]\n{tb}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root.parent))
    sys.exit(main(root))

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.483 (D395) — no PySide6 that takes references from None on Python 3.11.

The defect is not this program's: PySide6 6.12.0 on Linux takes one
reference from None on nearly every ``QGraphicsItem`` setter, and on 3.11,
where None is not immortal yet (PEP 683 made it immortal in 3.12), its
count reaches zero and the interpreter aborts with «none_dealloc». Measured
in run 45127694244 (tag ``archivo/dev-d395-medida``): −1 per call of
``setPen``, ``setBrush``, ``setPos``, ``setZValue``, ``setVisible``,
``setLine``, ``setRect``…; the demo aborted after ~880 redraws, ~47 once
computed. 6.11.3 and 6.10.3 lose nothing, and on Windows none of the three
does. The probe of 739885e had died after two candidates, so the ficha's
«path items give 0» was never measured on 3.11: they lose one too.

What these tests protect:

* ``pyproject.toml`` excludes 6.12.0 below Python 3.12 and only there, and
  the two PySide6 requirements cover every Python between them;
* an identity, not a snapshot: on a Python whose None is mortal, the
  setters the canvas calls leave None's count exactly where it was. That
  is what makes the 3.11 job of the CI catch a future bad release that the
  exclusion does not name. With an immortal None (3.12+) the count cannot
  move and the case says so instead of passing.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_CALLS = 50  # few enough that a bad binding cannot take None to zero here


def _pyside_requirements() -> list[tuple[str, str]]:
    """``(specifier, marker)`` of every PySide6 requirement, spaces out."""
    import tomllib

    meta = tomllib.loads((_ROOT / "pyproject.toml").read_text(
        encoding="utf-8"))["project"]
    out = []
    for req in meta["dependencies"]:
        name = re.split(r"[\s<>=!~;\[]", req, maxsplit=1)[0]
        if name.lower() != "pyside6":
            continue
        spec, _, marker = req[len(name):].partition(";")
        out.append((re.sub(r"\s", "", spec),
                    re.sub(r"\s", "", marker).replace('"', "'")))
    return out


class TestTheExclusion:
    def test_six_twelve_zero_is_excluded_below_three_twelve(self):
        reqs = dict((m, s) for s, m in _pyside_requirements())
        assert "python_version<'3.12'" in reqs, reqs
        assert "!=6.12.0" in reqs["python_version<'3.12'"].split(","), reqs

    def test_the_exclusion_is_only_below_three_twelve(self):
        reqs = dict((m, s) for s, m in _pyside_requirements())
        assert "python_version>='3.12'" in reqs, reqs
        assert "6.12.0" not in reqs["python_version>='3.12'"], reqs

    def test_the_two_markers_cover_every_python(self):
        reqs = _pyside_requirements()
        assert sorted(m for _, m in reqs) == [
            "python_version<'3.12'", "python_version>='3.12'"], reqs
        # the same floor on both sides: the exclusion is the only difference
        floors = {[p for p in s.split(",") if p.startswith(">=")][0]
                  for s, _ in reqs}
        assert floors == {">=6.6"}, reqs


def _setters():
    from PySide6.QtCore import QLineF, QPointF, QRectF
    from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen, QPolygonF
    from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsLineItem,
                                   QGraphicsPathItem, QGraphicsPolygonItem,
                                   QGraphicsRectItem, QGraphicsScene,
                                   QGraphicsSimpleTextItem)

    scene = QGraphicsScene()
    line = QGraphicsLineItem(0, 0, 1, 1)
    rect = QGraphicsRectItem(0, 0, 1, 1)
    path_item = QGraphicsPathItem()
    poly = QGraphicsPolygonItem()
    text = QGraphicsSimpleTextItem("x")
    ell = QGraphicsEllipseItem(0, 0, 1, 1)
    for it in (line, rect, path_item, poly, text, ell):
        scene.addItem(it)
    pen = QPen(QColor("red"))
    brush = QBrush(QColor("blue"))
    path = QPainterPath()
    path.addPolygon(QPolygonF([QPointF(0, 0), QPointF(1, 0), QPointF(1, 1)]))
    calls = {
        "QGraphicsLineItem.setPen": lambda: line.setPen(pen),
        "QGraphicsLineItem.setLine": lambda: line.setLine(QLineF(0, 0, 2, 2)),
        "QGraphicsRectItem.setPen": lambda: rect.setPen(pen),
        "QGraphicsRectItem.setBrush": lambda: rect.setBrush(brush),
        "QGraphicsRectItem.setRect": lambda: rect.setRect(QRectF(0, 0, 2, 2)),
        "QGraphicsPathItem.setPen": lambda: path_item.setPen(pen),
        "QGraphicsPathItem.setPath": lambda: path_item.setPath(path),
        "QGraphicsPolygonItem.setBrush": lambda: poly.setBrush(brush),
        "QGraphicsEllipseItem.setPen": lambda: ell.setPen(pen),
        "QGraphicsSimpleTextItem.setBrush": lambda: text.setBrush(brush),
        "QGraphicsItem.setPos": lambda: line.setPos(1, 1),
        "QGraphicsItem.setZValue": lambda: line.setZValue(2),
        "QGraphicsItem.setVisible": lambda: line.setVisible(True),
        "QPen.setWidthF": lambda: pen.setWidthF(1.0),
    }
    # the objects must outlive the calls that use them
    return calls, (scene, line, rect, path_item, poly, text, ell, pen, brush,
                   path)


def none_lost_per_call() -> dict[str, float]:
    """Change of None's reference count per call, setter by setter."""
    calls, _keep = _setters()
    out = {}
    for name, fn in calls.items():
        fn()  # a first call may cache something; it is not what is measured
        before = sys.getrefcount(None)
        for _ in range(_CALLS):
            fn()
        out[name] = (sys.getrefcount(None) - before) / _CALLS
    return out


class TestTheSettersLeaveNoneAlone:
    def test_no_setter_takes_a_reference_from_none(self):
        if sys.getrefcount(None) > 2 ** 30:
            pytest.skip(f"None is immortal on Python "
                        f"{sys.version.split()[0]}: its count cannot move")
        from PySide6.QtWidgets import QApplication

        QApplication.instance() or QApplication([])
        lost = {k: v for k, v in none_lost_per_call().items() if v < 0}
        assert not lost, lost

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""D370 probe of None's reference count — only on ``dev/d370-shutdown``.

Small slices of the suite died on Python 3.11 with «Fatal Python error:
none_dealloc: deallocating None», in ``line1.setPen(cross_pen)`` of the
canvas: something returns None without a new reference, so every call
takes one from None, and on 3.11 (where None is not immortal yet) the count
reaches zero. This prints how much None's count moves per call, for the
calls the canvas makes and for a whole redraw of the demo.

    python tests/_d370_none.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF  # noqa: E402
from PySide6.QtGui import (QBrush, QColor, QFont, QPainterPath, QPen,  # noqa: E402
                           QPolygonF)
from PySide6.QtWidgets import (QApplication, QGraphicsEllipseItem,  # noqa: E402
                               QGraphicsLineItem, QGraphicsPathItem,
                               QGraphicsRectItem, QGraphicsScene,
                               QGraphicsSimpleTextItem)

import PySide6  # noqa: E402

print("Python", sys.version.split()[0], "PySide6", PySide6.__version__,
      "None immortal" if sys.getrefcount(None) > 2 ** 30 else "None mortal")
app = QApplication([])
scene = QGraphicsScene()
line = QGraphicsLineItem(0, 0, 1, 1)
rect = QGraphicsRectItem(0, 0, 1, 1)
path_item = QGraphicsPathItem()
text = QGraphicsSimpleTextItem("x")
ell = QGraphicsEllipseItem(0, 0, 1, 1)
for it in (line, rect, path_item, text, ell):
    scene.addItem(it)
pen = QPen(QColor("red"))
brush = QBrush(QColor("blue"))
path = QPainterPath()
path.addPolygon(QPolygonF([QPointF(0, 0), QPointF(1, 0), QPointF(1, 1)]))

CANDIDATES = {
    "QGraphicsLineItem.setPen": lambda: line.setPen(pen),
    "QGraphicsRectItem.setPen": lambda: rect.setPen(pen),
    "QGraphicsRectItem.setBrush": lambda: rect.setBrush(brush),
    "QGraphicsPathItem.setPath": lambda: path_item.setPath(path),
    "QGraphicsPathItem.setPen": lambda: path_item.setPen(pen),
    "QGraphicsSimpleTextItem.setBrush": lambda: text.setBrush(brush),
    "QGraphicsSimpleTextItem.setFont": lambda: text.setFont(QFont()),
    "QGraphicsEllipseItem.setPen": lambda: ell.setPen(pen),
    "QGraphicsItem.setZValue": lambda: line.setZValue(2),
    "QGraphicsItem.setPos": lambda: line.setPos(1, 1),
    "QGraphicsItem.setToolTip": lambda: line.setToolTip("t"),
    "QGraphicsItem.setVisible": lambda: line.setVisible(True),
    "QGraphicsItem.setFlag": lambda: line.setFlag(
        QGraphicsLineItem.ItemIgnoresTransformations, True),
    "QGraphicsScene.addItem(new line)": lambda: scene.addItem(
        QGraphicsLineItem(0, 0, 1, 1)),
    "QGraphicsLineItem(…)": lambda: QGraphicsLineItem(0, 0, 1, 1),
    "QPen.setCosmetic": lambda: pen.setCosmetic(True),
    "QPen.setWidthF": lambda: pen.setWidthF(1.0),
    "QColor.setAlphaF": lambda: QColor("red").setAlphaF(0.5),
    "QGraphicsScene.setSceneRect": lambda: scene.setSceneRect(
        QRectF(0, 0, 10, 10)),
}

N = 2000
for name, fn in CANDIDATES.items():
    fn()
    before = sys.getrefcount(None)
    for _ in range(N):
        fn()
    after = sys.getrefcount(None)
    print(f"[D370 none] {name:36s} {(after - before) / N:+.3f} per call")

from ogr_gui.main_window import MainWindow  # noqa: E402

w = MainWindow()
w.act_load_demo()
w.project.is_dirty = False
w.canvas.refresh_scene()
before = sys.getrefcount(None)
for _ in range(20):
    w.canvas.refresh_scene()
after = sys.getrefcount(None)
print(f"[D370 none] {'CanvasView.refresh_scene (demo)':36s} "
      f"{(after - before) / 20:+.1f} per redraw")
w.project.is_dirty = False
w.close()

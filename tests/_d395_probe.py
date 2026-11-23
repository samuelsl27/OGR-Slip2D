# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""D395 probe of None's reference count — only on ``dev/d395-medida``.

The probe of 739885e ran every candidate in one process, and on Linux with
Python 3.11 and PySide6 6.12.0 it aborted after the first two: the rest
were never measured on 3.11. Here every candidate runs in its own child,
few enough calls that None cannot reach zero, so an abort hides nothing.

    python tests/_d395_probe.py calls      # one child per candidate
    python tests/_d395_probe.py program    # the real window, action by action
    python tests/_d395_probe.py redraws    # redraw until abort or 5000
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

N_CALLS = 200
CANDIDATES = [
    "QGraphicsLineItem.setPen", "QGraphicsRectItem.setPen",
    "QGraphicsRectItem.setBrush", "QGraphicsPathItem.setPath",
    "QGraphicsPathItem.setPen", "QGraphicsPolygonItem.setPen",
    "QGraphicsPolygonItem.setBrush", "QGraphicsSimpleTextItem.setBrush",
    "QGraphicsEllipseItem.setPen", "QGraphicsEllipseItem.setBrush",
    "QGraphicsItem.setZValue", "QGraphicsItem.setPos",
    "QGraphicsItem.setToolTip", "QGraphicsItem.setVisible",
    "QGraphicsScene.addItem(new line)", "QGraphicsScene.addLine",
    "QGraphicsScene.addRect", "QGraphicsLineItem.pen",
    "QGraphicsLineItem.setLine", "QGraphicsRectItem.setRect",
    "QPen(QColor)", "QPen.setWidthF",
]


def _say(text):
    print(f"[D395] {text}", flush=True)


def _header():
    import PySide6
    _say(f"Python {sys.version.split()[0]} PySide6 {PySide6.__version__} "
         f"{sys.platform} None "
         + ("immortal" if sys.getrefcount(None) > 2 ** 30 else "mortal")
         + f" refcount={sys.getrefcount(None)}")


def one(name):
    from PySide6.QtCore import QLineF, QPointF, QRectF
    from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen, QPolygonF
    from PySide6.QtWidgets import (QApplication, QGraphicsEllipseItem,
                                   QGraphicsLineItem, QGraphicsPathItem,
                                   QGraphicsPolygonItem, QGraphicsRectItem,
                                   QGraphicsScene, QGraphicsSimpleTextItem)
    app = QApplication([])  # noqa: F841
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
    fns = {
        "QGraphicsLineItem.setPen": lambda: line.setPen(pen),
        "QGraphicsRectItem.setPen": lambda: rect.setPen(pen),
        "QGraphicsRectItem.setBrush": lambda: rect.setBrush(brush),
        "QGraphicsPathItem.setPath": lambda: path_item.setPath(path),
        "QGraphicsPathItem.setPen": lambda: path_item.setPen(pen),
        "QGraphicsPolygonItem.setPen": lambda: poly.setPen(pen),
        "QGraphicsPolygonItem.setBrush": lambda: poly.setBrush(brush),
        "QGraphicsSimpleTextItem.setBrush": lambda: text.setBrush(brush),
        "QGraphicsEllipseItem.setPen": lambda: ell.setPen(pen),
        "QGraphicsEllipseItem.setBrush": lambda: ell.setBrush(brush),
        "QGraphicsItem.setZValue": lambda: line.setZValue(2),
        "QGraphicsItem.setPos": lambda: line.setPos(1, 1),
        "QGraphicsItem.setToolTip": lambda: line.setToolTip("t"),
        "QGraphicsItem.setVisible": lambda: line.setVisible(True),
        "QGraphicsScene.addItem(new line)": lambda: scene.addItem(
            QGraphicsLineItem(0, 0, 1, 1)),
        "QGraphicsScene.addLine": lambda: scene.addLine(0, 0, 1, 1, pen),
        "QGraphicsScene.addRect": lambda: scene.addRect(0, 0, 1, 1, pen),
        "QGraphicsLineItem.pen": lambda: line.pen(),
        "QGraphicsLineItem.setLine": lambda: line.setLine(QLineF(0, 0, 2, 2)),
        "QGraphicsRectItem.setRect": lambda: rect.setRect(QRectF(0, 0, 2, 2)),
        "QPen(QColor)": lambda: QPen(QColor("red")),
        "QPen.setWidthF": lambda: pen.setWidthF(1.0),
    }
    fn = fns[name]
    fn()
    before = sys.getrefcount(None)
    for _ in range(N_CALLS):
        fn()
    after = sys.getrefcount(None)
    _say(f"call {name:34s} {(after - before) / N_CALLS:+.3f} per call")


def calls():
    _header()
    for name in CANDIDATES:
        r = subprocess.run([sys.executable, __file__, "one", name],
                           capture_output=True, text=True)
        out = [ln for ln in r.stdout.splitlines() if ln.startswith("[D395]")]
        print("\n".join(out) if out else f"[D395] call {name:34s} no output",
              flush=True)
        if r.returncode:
            _say(f"call {name:34s} EXIT={r.returncode} "
                 f"{r.stderr.strip().splitlines()[:1]}")


def _window():
    from PySide6.QtWidgets import QApplication, QMessageBox
    # A modal box would wait for ever without a screen.
    for nm in ("information", "warning", "critical", "question"):
        setattr(QMessageBox, nm, staticmethod(
            lambda *a, _n=nm, **k: (_say(f"QMessageBox.{_n}: {a[2:3]}"),
                                    QMessageBox.Ok)[1]))
    app = QApplication.instance() or QApplication([])
    from ogr_gui.main_window import MainWindow
    w = MainWindow()
    w.show()
    w.act_load_demo()
    w.project.is_dirty = False
    app.processEvents()
    return app, w


def program():
    _header()
    app, w = _window()
    _say(f"after demo: None refcount={sys.getrefcount(None)} "
         f"scene items={len(w.canvas.scene().items())}")

    def measure(label, fn, reps=1):
        fn()
        app.processEvents()
        before = sys.getrefcount(None)
        for _ in range(reps):
            fn()
            app.processEvents()
        after = sys.getrefcount(None)
        _say(f"action {label:28s} {(after - before) / reps:+.1f} per action "
             f"(None refcount now {after})")

    measure("refresh_scene", w.canvas.refresh_scene, 5)
    measure("zoom_by in/out", lambda: (w.canvas.zoom_by(1.25),
                                       w.canvas.zoom_by(0.8)), 5)
    measure("zoom_all", w.canvas.zoom_all, 5)
    measure("compute (demo)", w.act_compute, 1)
    measure("refresh_scene, computed", w.canvas.refresh_scene, 5)
    measure("interpret (open+close)", lambda: (
        w.act_interpret(),
        [iw.close() for iw in list(w.interpret_windows)]), 1)
    _say(f"end: None refcount={sys.getrefcount(None)}")
    w.project.is_dirty = False
    w.close()


def redraws():
    _header()
    app, w = _window()
    start = sys.getrefcount(None)
    _say(f"redraw 0 None refcount={start}")
    for i in range(1, 5001):
        w.canvas.refresh_scene()
        app.processEvents()
        if i % 25 == 0:
            _say(f"redraw {i} None refcount={sys.getrefcount(None)}")
    _say("redraw 5000 reached, no abort")
    w.project.is_dirty = False
    w.close()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "calls"
    if mode == "one":
        one(sys.argv[2])
    else:
        {"calls": calls, "program": program, "redraws": redraws}[mode]()

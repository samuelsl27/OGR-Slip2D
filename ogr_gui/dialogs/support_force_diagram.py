# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
Capacity of a support along its own length, mode by mode.

v0.1.124 — until this version ``force_at`` returned only the smallest of a
type's failure modes, so there was no way to see WHICH one governed. For a
grouted tieback that is a curiosity; for a helical anchor it is the whole
point, because seven capacities compete and the winner changes twice along
a five-metre anchor.

The window is NOT modal, like every other informative chart in this
program: a diagram that blocks the application cannot be compared against
the model beside it.

Author: Samuel Sáez López — UPCT
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from ogr_gui.i18n import tr

#: Mode key -> English label. The keys are ASCII tokens that live in
#: ``ogr_core``, which has no i18n; the label is user-visible text and
#: belongs on this side of the line, where ``tr()`` can reach it. Same
#: split as ``_CHOICES`` in the support dialog.
MODE_LABELS: dict[str, str] = {
    "pullout": "Pullout",
    "tensile": "Tensile",
    "stripping": "Stripping",
    "pullout_shallow": "Pullout - shallow failure",
    "pullout_cylindrical": "Pullout - cylindrical shear",
    "pullout_bearing": "Pullout - individual bearing",
    "stripping_shallow": "Stripping - shallow failure",
    "stripping_cylindrical": "Stripping - cylindrical shear",
    "stripping_bearing": "Stripping - individual bearing",
}

#: Points along the support. The diagram STEPS wherever a helix crosses the
#: surface, and a step drawn from samples is only as sharp as the sampling;
#: four hundred over a five-metre anchor puts the riser inside a
#: centimetre, which is finer than the geometry is ever known.
SAMPLES = 401


def _resolve_type(project, support):
    """The support-type properties the analysis itself would use."""
    from ogr_core.support import support_registry

    for st in (getattr(project, "support_types", None) or ()):
        if st.TYPE_ID == support.type_id:
            return st
    cls = support_registry().get(support.type_id)
    return cls() if cls is not None else None


def _cut_distance(project, support, critical) -> Optional[float]:
    """Distance from the head to the critical surface, or None.

    Uses the analysis's own polyline rather than a second opinion about
    what the slip surface is: the two disagreeing about where a support
    crosses would put the marker somewhere the number never came from.
    """
    if critical is None or not getattr(critical, "slices", None):
        return None
    try:
        from ogr_slip2d.support_integration import _slip_polyline

        xy = _slip_polyline(critical.surface, critical.slices)
        hit = support.intersection_with_polyline(xy)
    except Exception:  # noqa: BLE001 - a diagram must not kill Interpret
        return None
    return None if hit is None else hit[2]


def support_bond(project, support, stype):
    """The profile the analysis would build for this support, or None."""
    if not getattr(stype, "NEEDS_BOND_PROFILE", False):
        return None
    try:
        from ogr_core.support import build_bond_profile

        return build_bond_profile(project, support, stype)
    except Exception:  # noqa: BLE001 - a diagram must not kill Interpret
        return None


def support_series(project, support, samples: int = SAMPLES):
    """``(label, xs, ys)`` per failure mode, plus the applied envelope.

    Separate from the widget so a test can read the numbers without a
    screen, which is also how they are checked against the published
    capacity table.
    """
    stype = _resolve_type(project, support)
    length = support.length()
    if stype is None or length <= 0.0:
        return []

    bond = support_bond(project, support, stype)
    n = max(2, int(samples))
    xs = [length * i / (n - 1) for i in range(n)]
    modes: dict[str, list] = {}
    applied_ys = []
    for x in xs:
        applied_ys.append(stype.force_at(x, length, bond))
        for key, value in (stype.capacity_modes(x, length, bond) or {}).items():
            modes.setdefault(key, []).append(value)

    series = [(tr(MODE_LABELS.get(k, k)), xs, ys) for k, ys in modes.items()]
    series.append((tr("Applied"), xs, applied_ys))
    return series


class SupportForceDiagramWindow(QDialog):
    """Capacity against distance from the head, for one support at a time."""

    def __init__(self, project, critical=None, parent=None) -> None:
        super().__init__(parent)
        self.project = project
        self.critical = critical
        self.setWindowTitle(tr("Support Force Diagram"))
        self.resize(760, 500)

        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel(tr("Support:")))
        self.cbo = QComboBox()
        self._supports = list(getattr(project, "supports", None) or ())
        for i, sup in enumerate(self._supports, 1):
            stype = _resolve_type(project, sup)
            name = getattr(sup, "name", "") or f"{i}"
            label = getattr(stype, "DISPLAY_NAME", "") if stype else ""
            self.cbo.addItem(f"{name}  [{label}]" if label else name, i - 1)
        top.addWidget(self.cbo, 1)
        lay.addLayout(top)

        self.note = QLabel("")
        self.note.setWordWrap(True)
        lay.addWidget(self.note)

        self._canvas = None
        self._figure = None
        try:
            import matplotlib

            matplotlib.use("QtAgg", force=False)
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure

            self._figure = Figure(figsize=(7.2, 4.4), tight_layout=True)
            self._canvas = FigureCanvasQTAgg(self._figure)
            lay.addWidget(self._canvas)
        except ImportError:  # pragma: no cover - matplotlib is a dependency
            self.note.setText(tr("matplotlib is not installed."))

        self.cbo.currentIndexChanged.connect(self.refresh)
        self.refresh()

    # ------------------------------------------------------------------
    def current_support(self):
        i = self.cbo.currentIndex()
        if 0 <= i < len(self._supports):
            return self._supports[i]
        return None

    def series(self):
        """What is plotted, as data. The test reads this."""
        sup = self.current_support()
        if sup is None:
            return [], None, None
        series = support_series(self.project, sup)
        cut = _cut_distance(self.project, sup, self.critical)
        applied = None
        if cut is not None:
            stype = _resolve_type(self.project, sup)
            bond = support_bond(self.project, sup, stype)
            applied = stype.force_at(cut, sup.length(), bond)
        return series, applied, cut

    def refresh(self) -> None:
        series, applied, cut = self.series()
        if len(series) <= 1:
            self.note.setText(tr(
                "This support type publishes no failure modes; only the "
                "applied force is shown."))
        elif cut is not None and applied is not None:
            self.note.setText(tr("At the slip surface: %.4f kN/m") % applied)
        else:
            self.note.setText("")
        if self._figure is None or self._canvas is None:
            return
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        for label, xs, ys in series:
            wide = label == tr("Applied")
            ax.plot(xs, ys, label=label,
                    linewidth=2.6 if wide else 1.2,
                    color="black" if wide else None,
                    zorder=3 if wide else 2)
        if cut is not None:
            ax.axvline(cut, color="0.4", linestyle="--", linewidth=1.0)
            if applied is not None:
                ax.plot([cut], [applied], marker="o", color="black",
                        zorder=4)
        ax.set_xlabel(tr("Distance from head (m)"))
        ax.set_ylabel(tr("Force per metre of slope (kN/m)"))
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        self._canvas.draw_idle()

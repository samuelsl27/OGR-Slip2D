# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.279 (D273) — every parameter library of the hydraulic dialog's Pick
button says where its numbers come from, and the Brooks-Corey one IS a
published table.

The defect: one comment cited "representative literature figures (van
Genuchten 1980; Carsel & Parrish 1988; Brooks & Corey 1964)" for the four
libraries, and the Pick list said "Soil (literature values)" for all of
them. Only van Genuchten had a table behind it. Brooks & Corey (1964)
publish no means by texture, and the old Brooks-Corey sand (psi_b 5 kPa,
lambda 2.0) was seven times the bubbling pressure of the textural table.
Gardner (rational form) and Fredlund-Xing are fitted to each soil, and no
table by texture was found for them.

What these tests protect:

* **Brooks-Corey is the table** (rule 1): the eleven USDA textures of Rawls,
  Brakensiek & Saxton (1982), table "Hydrologic soil properties classified
  by soil texture", geometric means of the bubbling pressure (cm of water)
  and of lambda, copied here from the paper. lambda is the printed value
  and psi_b the printed cm times 9.81/100 kPa, so that with the project's
  default gamma_w the bubbling HEAD of the material is the table's;
* **Gardner and Fredlund-Xing are declared illustrative**: no source in
  ``LIBRARY_SOURCES``, and the Pick list and the API say so;
* the Pick list names the table for van Genuchten (Carsel & Parrish 1988,
  whose values are checked in ``test_groundwater_ops_v1200``) and for
  Brooks-Corey;
* the psi_b box keeps the six decimals of the library: Pick then OK keeps
  0.712206 kPa, which three decimals rounded.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ogr_core.hydraulic import (  # noqa: E402
    LIBRARY_SOURCES,
    MATERIAL_LIBRARY,
    HydraulicProperties,
    PermeabilityModel,
    library_for,
    library_source,
)

try:
    from PySide6.QtWidgets import QApplication
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False


def _requires_qt(cls):
    return cls if _QT else type(cls.__name__, (), {})


#: Rawls, Brakensiek & Saxton (1982), Trans. ASAE 25(5): table "Hydrologic
#: soil properties classified by soil texture", the GEOMETRIC means: bubbling
#: pressure psi_b [cm of water] and pore-size distribution index lambda.
RAWLS_1982 = {
    "Sand": (7.26, 0.592),
    "Loamy sand": (8.69, 0.474),
    "Sandy loam": (14.66, 0.322),
    "Loam": (11.15, 0.220),
    "Silt loam": (20.76, 0.211),
    "Sandy clay loam": (28.08, 0.250),
    "Clay loam": (25.89, 0.194),
    "Silty clay loam": (32.56, 0.151),
    "Sandy clay": (29.17, 0.168),
    "Silty clay": (34.19, 0.127),
    "Clay": (37.30, 0.131),
}
GAMMA_W = 9.81


class TestBrooksCoreyIsRawlsTable:
    def test_the_eleven_textures(self):
        assert set(library_for(PermeabilityModel.BROOKS_COREY)) \
            == set(RAWLS_1982)

    def test_each_value_in_the_models_unit(self):
        lib = library_for(PermeabilityModel.BROOKS_COREY)
        for soil, (hb_cm, lam) in RAWLS_1982.items():
            assert lib[soil]["bc_lambda"] == lam, soil
            assert abs(lib[soil]["bc_psi_b"] - hb_cm * GAMMA_W / 100.0) \
                < 1e-12, soil

    def test_the_bubbling_head_is_the_tables(self):
        """kr = 1 up to the bubbling pressure and below 1 past it, at a
        pressure head of the table's cm / 100 with gamma_w 9.81."""
        lib = library_for(PermeabilityModel.BROOKS_COREY)
        for soil, (hb_cm, _lam) in RAWLS_1982.items():
            p = HydraulicProperties(model=PermeabilityModel.BROOKS_COREY,
                                    kr_min=1e-12, **lib[soil])
            h = hb_cm / 100.0
            assert p.kr_at_pressure_head(-h * (1 - 1e-9), GAMMA_W) == 1.0
            assert p.kr_at_pressure_head(-h * (1 + 1e-3), GAMMA_W) < 1.0


class TestEachLibrarySaysItsSource:
    def test_the_sources(self):
        assert library_source(PermeabilityModel.VAN_GENUCHTEN) \
            == "Carsel & Parrish (1988)"
        assert library_source(PermeabilityModel.BROOKS_COREY) \
            == "Rawls, Brakensiek & Saxton (1982)"
        assert library_source(PermeabilityModel.GARDNER) is None
        assert library_source(PermeabilityModel.FREDLUND_XING) is None

    def test_every_library_is_declared(self):
        assert set(LIBRARY_SOURCES) == set(MATERIAL_LIBRARY)

    def test_the_api_note_says_it(self):
        import atexit
        from ogr_api import Workspace, call
        ws = Workspace()
        atexit.register(ws.shutdown)
        pid = call(ws, "project_new", name="D273")["project_id"]
        call(ws, "model_define", project_id=pid, spec={
            "external": [[0, 0], [10, 0], [10, 5], [0, 5]],
            "materials": [{"name": "Soil", "unit_weight": 20, "strength": {
                "model": "mohr_coulomb",
                "params": {"cohesion": 5.0, "friction_angle": 30.0}}}]})
        for model, soil, word in (("brooks_corey", "loam", "Rawls"),
                                  ("gardner", "sand", "illustrative"),
                                  ("fredlund_xing", "clay", "illustrative")):
            out = call(ws, "hydraulic_set", project_id=pid, material="Soil",
                       model=model, library=soil)
            assert any(word in n for n in out["notes"]), (model, out["notes"])


@_requires_qt
class TestThePickList:
    def _dialog(self):
        QApplication.instance() or QApplication([])
        from test_retention_dialog_v1268 import _dialog, _project
        p = _project(transient=False)
        return p, _dialog(p)

    def _pick(self, d, model, answer=None):
        """Run Pick for ``model`` with the list replaced; returns the label
        the list was shown with."""
        from PySide6.QtWidgets import QInputDialog
        seen = []

        def fake(_parent, _title, label, items, *_a, **_k):
            seen.append(label)
            return (answer or items[0]), True

        d.cbo_model.setCurrentIndex(d.cbo_model.findData(model))
        raw = QInputDialog.__dict__.get("getItem")
        QInputDialog.getItem = staticmethod(fake)
        try:
            d._pick()
        finally:
            if raw is None:
                del QInputDialog.getItem
            else:
                QInputDialog.getItem = raw
        return seen[0]

    def test_the_label_names_the_table_or_says_illustrative(self):
        from ogr_gui.i18n import tr
        _p, d = self._dialog()
        want = {PermeabilityModel.VAN_GENUCHTEN: "Carsel & Parrish (1988)",
                PermeabilityModel.BROOKS_COREY: "Rawls",
                PermeabilityModel.GARDNER: tr("Soil (illustrative values, no "
                                              "published source):"),
                PermeabilityModel.FREDLUND_XING: tr("Soil (illustrative "
                                                    "values, no published "
                                                    "source):")}
        for model, word in want.items():
            assert word in self._pick(d, model), model

    def test_pick_then_ok_keeps_the_librarys_psi_b(self):
        p, d = self._dialog()
        self._pick(d, PermeabilityModel.BROOKS_COREY, answer="Sand")
        d._accept()
        got = p.materials[0].hydraulic.bc_psi_b
        assert abs(got - 7.26 * GAMMA_W / 100.0) < 1e-12, got

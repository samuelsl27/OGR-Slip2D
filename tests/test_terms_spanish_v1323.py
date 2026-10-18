# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.323 — one Spanish term for each thing, in the whole dictionary.

The defect: three things had two names in the Spanish interface, found while
translating D300:

* the Water Pressure Grid was «Malla de presiones de agua», although the
  project keeps «malla» for the finite-element mesh and «rejilla» for a
  grid (D240, «Añadir rejilla»; 0.1.320, «Búsqueda por rejilla»);
* total head and pressure head were «cabeza total» and «cabeza de
  presión», a calque of «head», while the Hu tooltip of 0.1.320 said
  «altura de presión»;
* the stripping failure of a support was «Descabezamiento» for the helical
  anchor and «desprendimiento» in what 0.1.322 wrote for the others.

By decision of the owner: «rejilla de presiones de agua», «altura total» y
«altura de presión», and «descabezamiento» — the term the program already
had. By the same rule, four more that 0.1.319–0.1.322 wrote against the
program's own terms go back to them: «carga distribuida» (the menus' «Añadir
carga distribuida»), «magnitud» (the load dialog's «Magnitud:»), «Expandir /
contraer» (the menu's) and «OSnap» in the drawing menu (the legend's OSNAP).
This file fails if an old name comes back anywhere in the dictionary.

Controls: «malla» still names the finite-element mesh, and «cabeza» the head
of a support, which are the meanings these words keep.
"""
from __future__ import annotations

import re


def _spanish():
    from ogr_gui.i18n import _DICTS
    return _DICTS["es"]


#: The old name, and the new one that replaces it everywhere.
_RETIRED = {
    r"malla de presiones": "rejilla de presiones",
    r"cabeza total": "altura total",
    r"cabeza de presión": "altura de presión",
    r"desprendimiento": "descabezamiento",
    r"carga repartida": "carga distribuida",
    r"ampliar / reducir": "expandir / contraer",
    r"forzado a objeto": "OSnap",
    # the factor of safety is «FS» in Spanish, as 31 entries already said
    r"\bFoS\b": "FS",
}


class TestOneTermForEachThing:
    def test_no_old_name_is_left(self):
        es = _spanish()
        for old in _RETIRED:
            left = sorted(k for k, v in es.items()
                          if re.search(old, v, re.I))
            assert not left, (old, left)

    def test_the_new_names_are_where_the_old_ones_were(self):
        es = _spanish()
        assert es["Water Pressure Grid"] == "Rejilla de presiones de agua"
        assert es["Total Head"] == "Altura total"
        assert es["Pressure Head"] == "Altura de presión"
        assert es["Stripping"] == "Descabezamiento"
        assert es["Pullout & Stripping"] == \
            "Arrancamiento y descabezamiento"
        assert es["Distributed Load"] == "Carga distribuida"
        assert es["Expand / Shrink…"] == "Expandir / contraer…"
        assert "OSnap" not in es

    def test_a_magnitude_is_a_magnitude(self):
        """«Módulo» keeps what it means elsewhere (the OGR FEM2D module); a
        quantity's magnitude is «magnitud», as in the load dialog."""
        es = _spanish()
        assert es["Magnitude:"] == "Magnitud:"
        left = sorted(k for k, v in es.items()
                      if re.search(r"agnitude", k) and re.search(r"ódulo", v))
        assert not left, left

    def test_control_the_words_keep_their_other_meaning(self):
        es = _spanish()
        assert es["Finite element mesh"] == "Malla de elementos finitos"
        assert es["Head (x, y):"] == "Cabeza (x, y):"

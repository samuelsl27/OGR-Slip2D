# OGR Slip2D v0.1.519

**D468: el agua libre contra un acantilado que queda dentro del tope de una masa empuja a la masa, entera
en la dovela del lado alto de la cara.** La propietaria aprobó la regla el 2026-11-28, con la medida
delante: la cara mojada es un corte obligado y su empuje va entero a la dovela de cuyo costado es la cara.

## 0. Lo que se encontró

- **Más de lo que decía la ficha** (medido con 0.1.517; ficha D468 de `ERRORES_Y_DISCREPANCIAS.md`):
  - el corte en x = 50 del guion lo ponía el **vértice de la superficie**, no el terreno, porque el
    rebanador no corta en los vértices del terreno;
  - con la superficie (40, 10)→(55, 5)→(80, 13)→(90, 20), sin vértice en el escalón, el empuje dependía
    del número de dovelas: 0 con 30 y 31 (un corte uniforme cae por casualidad en x = 50) y **196,2**
    con 97. En ese caso la cara queda dentro de una dovela, y el agua se leía sobre la cuerda de su tope:
    γw·(17 − 15)·10. La forma cerrada es ½·γw·7² = **240,345 kN/m** a la cota 12,333.
- **El reparto mueve el factor**, con el empuje cerrado puesto a mano en un corte (30 dovelas):

  | | Spencer | GLE |
  |---|---|---|
  | Sin empuje | 2,16582 | 2,13794 |
  | Todo en el lado alto | **2,61580** | **2,59172** |
  | Todo en el lado bajo | 2,65413 | 2,61992 |
  | Mitad y mitad | 2,63486 | 2,60576 |

  Ordinario, Bishop, Janbu y Corps 2 no los distinguen, porque suman la masa entera. En el lado bajo, o
  a medias, la fuerza actúa a 12,33, por encima del tope de esa dovela (10): en el aire.
- **Sarma ya lo contaba bien, y ayer lo describí mal.** El escalón cae dentro del tope de una cuña, que
  integra el agua sobre él (240,345). Con la bisectriz, la cara de (50, 6) sube hasta (51,06; 20), y el
  escalón es un lado del polígono de esa misma cuña. El único caso en que el escalón caería en el
  límite entre dos cuñas es con una cara vertical en x = 50, y ese caso **Sarma lo rechaza**
  (`lem.sarma_wedge_invalid`), porque el polígono de la cuña degenera. Escribí el traspaso a la cuña
  vecina y lo quité: nada lo recorre. El rechazo queda apuntado como hallazgo, sin ficha.
- **Un artefacto del mismo origen.** Con el freático por encima del pie solo **detrás** de la cara (a 5
  delante y a 17 detrás), la dovela que contenía el escalón también leía 196,2 kN/m de la cuerda, sin
  ninguna agua contra la cara. Por eso el corte se pone con el agua por encima del pie en cualquiera de
  los dos lados, y el empuje solo con agua delante.
- **Censo en seco** (`_auditoria/P10_D468/censo_d468_0.1.518.log`): de los 230 modelos vivos, solo el
  **092** tiene una cara que cuenta (x = 6, de 6 a 9, con el agua a 9 delante y detrás). La otra que sale
  es el borde izquierdo del 059 (x = 0), que no puede quedar dentro de una masa.
- **A/B del 092 en disco**, 0.1.518 contra 0.1.519 (`_auditoria/P10_D468/ab_d468_092.py` y sus cuatro
  logs): **ningún número publicado se mueve**. Los dos modelos dan las mismas críticas y el mismo círculo
  publicado, bit a bit:
  - Bishop 0,967107 y 0,964846;
  - Spencer 1,026664 y 1,023243;
  - GLE 1,024975 y 1,022576;
  - el círculo publicado, 1,042182 y 1,0077.

  Sus superficies salen **por** la cara (eso es D450), no la cruzan.

## 1. Qué cambia

- `ogr_slip2d/slicer.py`:
  - `INTERIOR_FACE_PONDED_WATER = True`, el interruptor de módulo, que se lee en cada llamada;
  - `_wet_faces`: las caras verticales del terreno dentro de la masa con el agua por encima del pie en
    algún lado, con su lado bajo. Lo dice el orden de los vértices de la envolvente;
  - `_slice_boundaries`: cada una de esas caras es un **corte obligado**. Sin ellas, se corta como antes,
    bit a bit;
  - `_apply_interior_face_water`: el empuje de `end_face_water`, con el nivel leído delante de la cara,
    va entero a la dovela del lado alto, empujando del agua hacia ella, por `add_water_force` y
    `pond_force_h` (D199). Una cara dentro de una dovela (las columnas de Sarma, con sus cortes dados) se
    queda como estaba.
- Sarma no cambia.

## 2. Tests

- `tests/test_interior_face_ponded_d468_v1519.py` (nuevo, 6 tests, menos de 1 s), contra la forma
  cerrada:
  - 240,345 kN/m a 12,333 en la dovela que empieza en la cara, con 30, 31 y 97 dovelas;
  - el espejo: −240,345 en la dovela que acaba en la cara;
  - Sarma suma lo mismo;
  - sin agua delante, la cara es un corte y nada empuja. Sin la regla salía el 196,2 de la cuerda;
  - el control: con la cara seca, las dovelas son las de la regla apagada, bit a bit;
  - el interruptor mueve el factor de Spencer (regla 7).

- Áreas `ponded`, `sarma`, `tension_crack`, `end_face`, `interior_face`, `slicer`, `slice`,
  `interslice`, `drawdown`, `slide_validation`, `wall` y `step`, con `--jobs 4`: 938 casos en verde.

## 3. Suite

La suite entera, con `--jobs 4`, tras el commit.

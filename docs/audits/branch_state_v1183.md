# Criterio de aceptacion de una rama — censo D145 — OGR 0.1.183

Medido por `_tools/criterio_rama_d145.py`, que solo mide. `d_x` se reconstruye de `BranchState.boundary_x` de dos llamadas topadas, no de una copia de `solve_branch`.

## Denominador

| que | cuantas |
|---|---|
| casos | 344 |
| ramas | 6188 |
| medidas | 5699 |
| saltados | 18 |
| aceptadas | 5337 |
| aceptadas con d x | 5337 |
| aceptadas empuje vivo | 8 |
| aceptadas empuje creciendo | 1 |
| esperan mas de 20 | 0 |
| hueco en paciencia | 46 |
| aceptadas por rescate | 70 |
| aceptadas en la MISMA pasada | 5259 |
| aceptadas que la puerta rechaza | 8 |
| adelanto mediano | 0 |
| adelanto maximo | 0 |
| no aceptadas que el nuevo acepta | 0 |
| fallos de control rescate | 0 |
| ramas planas | 31 |
| ramas planas de fuerza | 22 |
| quitadas por la puerta | 18 |
| D152 quitadas planas de fuerza | 0 |
| D152 de esas con el mismo factor | 0 |
| descuadradas | 6 |
| lado | enviado |

## Ramas aceptadas con el empuje por encima de la tolerancia

| problema | archivo | metodo | lambda | rama | k* | d_x/tol | crece | paso/tol |
|---|---|---|---|---|---|---|---|---|
| 047 | resultados.json | spencer | +0.6000 | force | 11 | 79.6 | False | 0.875 |
| 047 | resultados.json | spencer | +0.8000 | force | 11 | 1.87e+03 | True | 0.875 |
| 047 | resultados.json | spencer | +0.7000 | force | 11 | 433 | False | 0.875 |
| 047 | resultados.json | spencer | +0.6500 | force | 11 | 192 | False | 0.875 |
| 047 | resultados.json | spencer | +0.6750 | force | 11 | 290 | False | 0.875 |
| 047 | resultados.json | spencer | +0.6875 | force | 11 | 355 | False | 0.875 |
| 047 | resultados.json | spencer | +0.6937 | force | 11 | 392 | False | 0.875 |
| 047 | resultados.json | spencer | +0.6906 | force | 11 | 373 | False | 0.875 |

## Ramas que siguen iterando con el par ya asentado

| problema | metodo | lambda | rama | asentada en | k* | espera |
|---|---|---|---|---|---|---|
| 011 | spencer | -0.1000 | force | 4 | 161 | 157 |
| 011 | gle_morgenstern_price | -0.1000 | force | 3 | 161 | 158 |
| 079 | spencer | -0.1000 | force | 4 | 161 | 157 |
| 081 | spencer | -0.1000 | force | 4 | 161 | 157 |

## D152 — ramas que la puerta del empuje quita

Una fila por rama que el motor enviado NO acepta y que con `BRANCH_PAIR_TIGHTEN` y `BRANCH_PAIR_SETTLE` apagados SI aceptaria. `plano` es la dispersion de `SliceRow.alpha` bajo `DISPERSION_PLANA`, que es donde el factor de la rama de fuerzas no depende del empuje.

| problema | archivo | metodo | lambda | rama | plano | disp alpha | k* | k sin puerta | fos | fos sin puerta |
|---|---|---|---|---|---|---|---|---|---|---|
| 060 | referencia.json | spencer | +0.7000 | moment | False | 0.368 | 161 | 14 | 1.44751074 | 1.44751074 |
| 060 | referencia.json | spencer | +0.6750 | moment | False | 0.368 | 161 | 14 | 1.44751074 | 1.44751074 |
| 060 | referencia.json | spencer | +0.6625 | moment | False | 0.368 | 161 | 14 | 1.44751074 | 1.44751074 |
| 060 | referencia.json | spencer | +0.6562 | moment | False | 0.368 | 161 | 14 | 1.44751074 | 1.44751074 |
| 060 | referencia.json | spencer | +0.6531 | moment | False | 0.368 | 161 | 14 | 1.44751074 | 1.44751074 |
| 078 | resultados_modelo_1a.json | spencer | +0.6000 | moment | False | 1.28 | 161 | 12 | 1.18124404 | 1.18124404 |
| 078 | resultados_modelo_2a.json | spencer | +0.6000 | moment | False | 1.28 | 161 | 12 | 1.18124404 | 1.18124404 |
| 078 | resultados_modelo_3a.json | gle_morgenstern_price | +2.0000 | force | False | 1.47 | 164 | 16 | 1.59734612 | 1.59686137 |
| 078 | resultados_modelo_3a.json | gle_morgenstern_price | +2.0000 | moment | False | 1.47 | 161 | 12 | 1.17886439 | 1.17886439 |
| 085 | resultados_modelo_pasivo.json | gle_morgenstern_price | +2.0000 | moment | False | 1.02 | 161 | 15 | 1.84554278 | 1.84554278 |
| 087 | resultados.json | gle_morgenstern_price | +3.0000 | moment | False | 0.769 | 171 | 45 | 1.0631469 | 1.06324996 |
| 087 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +3.0000 | moment | False | 0.769 | 171 | 45 | 1.0631469 | 1.06324996 |
| 090 | resultados.json | gle_morgenstern_price | +3.0000 | moment | False | 0.803 | 175 | 49 | 0.899508766 | 0.899532122 |
| 090 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +3.0000 | moment | False | 0.803 | 175 | 49 | 0.899508766 | 0.899532122 |
| 090 | referencia.json | spencer | +1.6250 | moment | False | 0.473 | 168 | 46 | 0.918232523 | 0.918194054 |
| 090 | referencia.json | spencer | +1.5938 | moment | False | 0.473 | 168 | 48 | 0.918204864 | 0.918190826 |
| 092 | resultados_modelo_sin_conexion.json | spencer | +3.5000 | moment | False | 0.391 | 131 | 4 | 0.998349282 | 0.998612365 |
| 093 | referencia.json | spencer | +1.5000 | moment | False | 0.478 | 155 | 37 | 1.02113645 | 1.02115531 |

## Saltadas

| problema | archivo | metodo | motivo |
|---|---|---|---|
| 045 | resultados.json | spencer | la superficie no define ninguna masa evaluable en este modelo |
| 045 | resultados_modelo_mc.json | spencer | la superficie no define ninguna masa evaluable en este modelo |
| 045 | resultados_modelo_mc_iter.json | spencer | la superficie no define ninguna masa evaluable en este modelo |
| 052 | referencia.json | gle_morgenstern_price | falta modelo.ogr |
| 052 | referencia.json | spencer | falta modelo.ogr |
| 057 | resultados_modelo_compuesto.json | spencer | la superficie no define ninguna masa evaluable en este modelo |
| 058 | referencia.json | spencer | falta modelo.ogr |
| 062 | referencia.json | spencer | falta modelo.ogr |
| 070 | referencia.json | spencer | falta modelo.ogr |
| 073 | referencia.json | spencer | falta modelo.ogr |
| 077 | referencia.json | spencer | la superficie no define ninguna masa evaluable en este modelo |
| 079 | resultados_no_circular_2.json | spencer | la superficie no define ninguna masa evaluable en este modelo |
| 079 | resultados_no_circular_2.json | gle_morgenstern_price | la superficie no define ninguna masa evaluable en este modelo |
| 079 | referencia.json | spencer | falta modelo.ogr |
| 081 | referencia.json | spencer | falta modelo.ogr |
| 085 | resultados_no_circular_pasivo.json | gle_morgenstern_price | la superficie no define ninguna masa evaluable en este modelo |
| 085 | referencia.json | gle_morgenstern_price | falta modelo.ogr |
| 103 | resultados_modelo_1.6.json | spencer | la superficie no define ninguna masa evaluable en este modelo |

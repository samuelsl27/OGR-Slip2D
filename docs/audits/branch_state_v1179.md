# Criterio de aceptacion de una rama — censo D145 — OGR 0.1.179

Medido por `_tools/criterio_rama_d145.py`, que solo mide. `d_x` se reconstruye de `BranchState.boundary_x` de dos llamadas topadas, no de una copia de `solve_branch`.

## Denominador

| que | cuantas |
|---|---|
| casos | 344 |
| ramas | 6110 |
| medidas | 5642 |
| saltados | 18 |
| aceptadas | 5348 |
| aceptadas con d x | 5348 |
| aceptadas empuje vivo | 223 |
| aceptadas empuje creciendo | 53 |
| esperan mas de 20 | 12 |
| hueco en paciencia | 0 |
| aceptadas por rescate | 35 |
| aceptadas en la MISMA pasada | 5060 |
| aceptadas que la puerta rechaza | 223 |
| adelanto mediano | 0 |
| adelanto maximo | 114 |
| no aceptadas que el nuevo acepta | 0 |
| fallos de control rescate | 0 |
| descuadradas | 10 |
| lado | antes (interruptores apagados) |

## Ramas aceptadas con el empuje por encima de la tolerancia

| problema | archivo | metodo | lambda | rama | k* | d_x/tol | crece | paso/tol |
|---|---|---|---|---|---|---|---|---|
| 001 | resultados.json | spencer | +0.6000 | force | 5 | 1.14 | False | 0.857 |
| 001 | referencia.json | spencer | +0.6000 | force | 5 | 1.17 | False | 0.658 |
| 015 | resultados_no_circular.json | spencer | +1.0000 | moment | 19 | 3.61 | False | 0.51 |
| 025 | referencia.json | spencer | +0.6000 | force | 9 | 9.51 | False | 0.5 |
| 025 | referencia.json | spencer | +0.6000 | moment | 15 | 1.24 | False | 0.708 |
| 025 | referencia.json | spencer | +0.5244 | force | 9 | 2.93 | False | 0.535 |
| 025 | referencia.json | spencer | +0.5237 | force | 9 | 2.89 | False | 0.535 |
| 027 | resultados.json | spencer | +0.4000 | moment | 7 | 26.5 | False | 0.152 |
| 027 | resultados.json | spencer | +0.3343 | moment | 8 | 9 | False | 0.864 |
| 027 | resultados.json | spencer | +0.3302 | force | 7 | 19.9 | False | 0.341 |
| 027 | resultados.json | spencer | +0.3302 | moment | 8 | 9.21 | False | 0.25 |
| 027 | resultados.json | spencer | +0.3334 | moment | 8 | 9.05 | False | 0.616 |
| 027 | resultados.json | spencer | +0.3327 | moment | 8 | 9.08 | False | 0.437 |
| 027 | resultados.json | spencer | +0.3322 | moment | 8 | 9.1 | False | 0.303 |
| 027 | resultados.json | spencer | +0.3319 | moment | 8 | 9.12 | False | 0.2 |
| 027 | resultados.json | spencer | +0.3316 | moment | 8 | 9.14 | False | 0.12 |
| 027 | resultados.json | spencer | +0.3313 | force | 7 | 19.8 | False | 0.917 |
| 027 | resultados.json | spencer | +0.3313 | moment | 8 | 9.15 | False | 0.0561 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.108 |
| 027 | resultados.json | spencer | +0.3315 | force | 7 | 19.8 | False | 0.998 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0991 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.107 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.105 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.104 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.103 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.103 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.102 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.101 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.101 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.101 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.1 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.1 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.1 |
| 027 | resultados.json | spencer | +0.3315 | force | 7 | 19.8 | False | 1 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0998 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.1 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | force | 7 | 19.8 | False | 1 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | force | 7 | 19.8 | False | 1 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | force | 7 | 19.8 | False | 1 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | force | 7 | 19.8 | False | 1 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | force | 7 | 19.8 | False | 1 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 027 | resultados.json | spencer | +0.3315 | force | 7 | 19.8 | False | 1 |
| 027 | resultados.json | spencer | +0.3315 | moment | 8 | 9.14 | False | 0.0999 |
| 039 | resultados_modelo_arcilla.json | spencer | +0.1574 | force | 4 | 1 | False | 0.37 |
| 047 | resultados.json | spencer | +0.6000 | force | 11 | 79.6 | False | 0.875 |
| 047 | resultados.json | spencer | +0.8000 | force | 11 | 1.87e+03 | True | 0.875 |
| 047 | resultados.json | spencer | +1.0000 | force | 11 | 2.17e+04 | True | 0.875 |
| 047 | resultados_modelo_sin_bulones.json | spencer | +0.4000 | moment | 13 | 3.35 | False | 0.597 |
| 047 | resultados_modelo_sin_bulones.json | spencer | +0.6000 | moment | 13 | 639 | True | 0.597 |
| 047 | resultados_modelo_sin_bulones.json | spencer | +0.8000 | moment | 13 | 2.64e+04 | True | 0.597 |
| 060 | referencia.json | spencer | +0.6000 | force | 34 | 4.47 | False | 0.984 |
| 060 | referencia.json | spencer | +0.6000 | moment | 14 | 62 | False | 0.546 |
| 060 | referencia.json | spencer | +0.8000 | moment | 14 | 3.3e+03 | True | 0.546 |
| 060 | referencia.json | spencer | +1.0000 | moment | 14 | 7.23e+04 | True | 0.546 |
| 062 | resultados_modelo_seco.json | spencer | +0.4000 | force | 4 | 5.25 | False | 0.219 |
| 062 | resultados_no_circular_seco.json | spencer | +0.6000 | moment | 8 | 1.06 | False | 0.423 |
| 062 | resultados_no_circular_seco.json | spencer | +0.8000 | force | 7 | 2.48 | False | 0.0493 |
| 062 | resultados_no_circular_seco.json | spencer | +0.6108 | moment | 8 | 1.1 | False | 0.301 |
| 068 | resultados.json | spencer | +0.6000 | force | 24 | 1.59 | False | 0.854 |
| 068 | resultados.json | spencer | +0.6000 | moment | 12 | 15.4 | False | 0.687 |
| 068 | resultados.json | spencer | +0.8000 | moment | 12 | 476 | True | 0.687 |
| 068 | resultados.json | spencer | +1.0000 | moment | 12 | 6.87e+03 | True | 0.687 |
| 068 | resultados.json | gle_morgenstern_price | +1.5000 | force | 16 | 3.99 | False | 0.507 |
| 068 | resultados.json | gle_morgenstern_price | +1.5000 | moment | 12 | 13.4 | False | 0.62 |
| 068 | resultados.json | gle_morgenstern_price | +2.0000 | moment | 12 | 420 | False | 0.62 |
| 068 | resultados.json | gle_morgenstern_price | +2.5000 | moment | 12 | 6.12e+03 | True | 0.62 |
| 068 | resultados.json | gle_morgenstern_price | +3.0000 | moment | 12 | 5.46e+04 | True | 0.62 |
| 078 | resultados_modelo_1a.json | spencer | +0.6000 | moment | 12 | 92.8 | False | 0.885 |
| 078 | resultados_modelo_1a.json | spencer | +0.8000 | moment | 12 | 2.88e+03 | True | 0.885 |
| 078 | resultados_modelo_1a.json | spencer | +1.0000 | moment | 12 | 4.14e+04 | True | 0.885 |
| 078 | resultados_modelo_1a.json | gle_morgenstern_price | +1.0000 | force | 8 | 1.68 | False | 0.099 |
| 078 | resultados_modelo_1a.json | gle_morgenstern_price | +1.5000 | force | 17 | 4.92 | False | 0.602 |
| 078 | resultados_modelo_1a.json | gle_morgenstern_price | +1.5000 | moment | 12 | 17.4 | False | 0.798 |
| 078 | resultados_modelo_1a.json | gle_morgenstern_price | +2.0000 | moment | 12 | 548 | True | 0.798 |
| 078 | resultados_modelo_1a.json | gle_morgenstern_price | +2.5000 | moment | 12 | 8e+03 | True | 0.798 |
| 078 | resultados_modelo_1a.json | gle_morgenstern_price | +3.0000 | moment | 12 | 7.15e+04 | True | 0.798 |
| 078 | resultados_modelo_2a.json | spencer | +0.6000 | moment | 12 | 92.8 | False | 0.885 |
| 078 | resultados_modelo_2a.json | spencer | +0.8000 | moment | 12 | 2.88e+03 | True | 0.885 |
| 078 | resultados_modelo_2a.json | spencer | +1.0000 | moment | 12 | 4.14e+04 | True | 0.885 |
| 078 | resultados_modelo_2a.json | gle_morgenstern_price | +1.0000 | force | 8 | 1.68 | False | 0.099 |
| 078 | resultados_modelo_2a.json | gle_morgenstern_price | +1.5000 | force | 17 | 4.92 | False | 0.602 |
| 078 | resultados_modelo_2a.json | gle_morgenstern_price | +1.5000 | moment | 12 | 17.4 | False | 0.798 |
| 078 | resultados_modelo_2a.json | gle_morgenstern_price | +2.0000 | moment | 12 | 548 | True | 0.798 |
| 078 | resultados_modelo_2a.json | gle_morgenstern_price | +2.5000 | moment | 12 | 8e+03 | True | 0.798 |
| 078 | resultados_modelo_2a.json | gle_morgenstern_price | +3.0000 | moment | 12 | 7.15e+04 | True | 0.798 |
| 078 | resultados_modelo_3a.json | spencer | +0.4000 | moment | 12 | 3.26 | False | 0.873 |
| 078 | resultados_modelo_3a.json | spencer | +0.6000 | moment | 12 | 404 | True | 0.873 |
| 078 | resultados_modelo_3a.json | spencer | +0.8000 | moment | 12 | 1.26e+04 | True | 0.873 |
| 078 | resultados_modelo_3a.json | gle_morgenstern_price | +1.5000 | force | 15 | 3.91 | False | 0.327 |
| 078 | resultados_modelo_3a.json | gle_morgenstern_price | +1.5000 | moment | 12 | 10.3 | False | 0.873 |
| 078 | resultados_modelo_3a.json | gle_morgenstern_price | +2.0000 | force | 16 | 274 | False | 0.247 |
| 078 | resultados_modelo_3a.json | gle_morgenstern_price | +2.0000 | moment | 12 | 322 | False | 0.873 |
| 078 | resultados_modelo_3a.json | gle_morgenstern_price | +2.5000 | moment | 12 | 4.71e+03 | True | 0.873 |
| 078 | resultados_modelo_3a.json | gle_morgenstern_price | +3.0000 | moment | 12 | 4.21e+04 | True | 0.873 |
| 078 | resultados_modelo_3a.json | gle_morgenstern_price | +3.5000 | moment | 12 | 2.68e+05 | True | 0.873 |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +0.4000 | moment | 7 | 3.34 | True | 0.659 |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +0.6000 | force | 11 | 1.04 | False | 0.629 |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +0.8000 | force | 12 | 17.4 | False | 0.566 |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +1.0000 | force | 21 | 94.3 | False | 0.937 |
| 078 | resultados_no_circular_1b.json | spencer | +0.6000 | force | 15 | 15.3 | False | 0.515 |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +0.4000 | force | 8 | 2.98 | False | 0.0735 |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +0.6000 | force | 10 | 47 | False | 0.103 |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +0.8000 | force | 13 | 935 | True | 0.061 |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +1.0000 | force | 12 | 1.25e+04 | True | 0.299 |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +0.4000 | moment | 7 | 3.34 | True | 0.659 |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +0.6000 | force | 11 | 1.04 | False | 0.629 |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +0.8000 | force | 12 | 17.4 | False | 0.566 |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +1.0000 | force | 21 | 94.3 | False | 0.937 |
| 078 | resultados_no_circular_3a.json | spencer | +0.8000 | force | 14 | 4.22 | False | 0.485 |
| 078 | resultados_no_circular_3a.json | spencer | +1.0000 | force | 32 | 2.99 | False | 0.874 |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +0.6000 | force | 9 | 4.45 | False | 0.522 |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +0.8000 | force | 10 | 41.6 | False | 0.978 |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +1.0000 | force | 18 | 212 | False | 0.685 |
| 078 | referencia.json | spencer | +0.4000 | force | 8 | 2.69 | False | 0.0742 |
| 078 | referencia.json | spencer | +0.6000 | force | 33 | 1.58 | False | 0.923 |
| 078 | referencia.json | spencer | +0.6000 | moment | 12 | 25.1 | False | 0.955 |
| 078 | referencia.json | spencer | +0.8000 | moment | 12 | 776 | True | 0.955 |
| 078 | referencia.json | spencer | +1.0000 | moment | 12 | 1.11e+04 | True | 0.955 |
| 078 | referencia.json | spencer | +0.4000 | force | 8 | 2.69 | False | 0.0742 |
| 078 | referencia.json | spencer | +0.6000 | force | 33 | 1.58 | False | 0.923 |
| 078 | referencia.json | spencer | +0.6000 | moment | 12 | 25.1 | False | 0.955 |
| 078 | referencia.json | spencer | +0.8000 | moment | 12 | 776 | True | 0.955 |
| 078 | referencia.json | spencer | +1.0000 | moment | 12 | 1.11e+04 | True | 0.955 |
| 078 | referencia.json | spencer | +0.4000 | force | 6 | 13.4 | False | 0.343 |
| 078 | referencia.json | spencer | +0.6000 | moment | 12 | 63.1 | False | 0.972 |
| 078 | referencia.json | spencer | +0.8000 | moment | 12 | 1.95e+03 | True | 0.972 |
| 078 | referencia.json | spencer | +1.0000 | moment | 12 | 2.81e+04 | True | 0.972 |
| 085 | resultados_modelo_activo.json | spencer | +0.8000 | force | 21 | 1.92 | False | 0.981 |
| 085 | resultados_modelo_activo.json | spencer | +0.8000 | moment | 15 | 7.24 | False | 0.73 |
| 085 | resultados_modelo_activo.json | spencer | +1.0000 | moment | 15 | 196 | False | 0.73 |
| 085 | resultados_modelo_activo.json | spencer | +1.5000 | moment | 15 | 7.89e+04 | True | 0.73 |
| 085 | resultados_modelo_activo.json | gle_morgenstern_price | +1.5000 | force | 15 | 2.64 | False | 0.987 |
| 085 | resultados_modelo_activo.json | gle_morgenstern_price | +1.5000 | moment | 15 | 1.37 | False | 0.732 |
| 085 | resultados_modelo_activo.json | gle_morgenstern_price | +2.0000 | force | 41 | 6.85 | False | 0.995 |
| 085 | resultados_modelo_activo.json | gle_morgenstern_price | +2.0000 | moment | 15 | 89.5 | False | 0.732 |
| 085 | resultados_modelo_activo.json | gle_morgenstern_price | +2.5000 | moment | 15 | 2.35e+03 | True | 0.732 |
| 085 | resultados_modelo_activo.json | gle_morgenstern_price | +3.0000 | moment | 15 | 3.4e+04 | True | 0.732 |
| 085 | resultados_modelo_activo.json | gle_morgenstern_price | +3.5000 | moment | 15 | 3.27e+05 | True | 0.732 |
| 085 | resultados_modelo_pasivo.json | spencer | +0.6000 | moment | 15 | 30.7 | False | 0.629 |
| 085 | resultados_modelo_pasivo.json | spencer | +0.8000 | moment | 15 | 2.16e+03 | True | 0.629 |
| 085 | resultados_modelo_pasivo.json | spencer | +1.0000 | moment | 15 | 5.86e+04 | True | 0.629 |
| 085 | resultados_modelo_pasivo.json | gle_morgenstern_price | +1.0000 | force | 10 | 3.9 | False | 0.631 |
| 085 | resultados_modelo_pasivo.json | gle_morgenstern_price | +1.5000 | force | 10 | 213 | False | 0.04 |
| 085 | resultados_modelo_pasivo.json | gle_morgenstern_price | +1.5000 | moment | 15 | 40.2 | False | 0.516 |
| 085 | resultados_modelo_pasivo.json | gle_morgenstern_price | +2.0000 | moment | 15 | 2.89e+03 | True | 0.516 |
| 085 | resultados_modelo_pasivo.json | gle_morgenstern_price | +2.5000 | moment | 15 | 8e+04 | True | 0.516 |
| 085 | resultados_no_circular_activo.json | spencer | +0.8000 | force | 14 | 22.3 | False | 0.461 |
| 085 | resultados_no_circular_activo.json | spencer | +1.0000 | force | 13 | 563 | False | 0.972 |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +1.0000 | force | 14 | 3.84 | False | 0.563 |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +1.5000 | force | 13 | 997 | False | 0.799 |
| 085 | resultados_no_circular_pasivo.json | spencer | +0.8000 | force | 13 | 39.6 | False | 0.624 |
| 085 | resultados_no_circular_pasivo.json | spencer | +1.0000 | force | 13 | 686 | False | 0.495 |
| 087 | resultados.json | spencer | +1.0000 | moment | 24 | 2.42 | True | 0.842 |
| 087 | resultados.json | gle_morgenstern_price | +2.5000 | force | 26 | 7.88 | False | 0.866 |
| 087 | resultados.json | gle_morgenstern_price | +2.5000 | moment | 25 | 4.76 | False | 0.805 |
| 087 | resultados.json | gle_morgenstern_price | +3.0000 | moment | 45 | 885 | True | 0.945 |
| 087 | resultados_modelo_sin_conexion.json | spencer | +1.0000 | moment | 24 | 2.18 | False | 0.787 |
| 087 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +2.5000 | force | 26 | 7.88 | False | 0.866 |
| 087 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +2.5000 | moment | 25 | 4.76 | False | 0.805 |
| 087 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +3.0000 | moment | 45 | 885 | True | 0.945 |
| 089 | referencia.json | spencer | +0.4000 | force | 3 | 1.45 | False | 0.224 |
| 090 | resultados.json | gle_morgenstern_price | +2.5000 | force | 36 | 2.73 | False | 0.641 |
| 090 | resultados.json | gle_morgenstern_price | +2.5000 | moment | 32 | 1.29 | False | 0.925 |
| 090 | resultados.json | gle_morgenstern_price | +3.0000 | moment | 49 | 415 | False | 0.000431 |
| 090 | resultados_modelo_sin_conexion.json | spencer | +1.0000 | moment | 33 | 1.95 | True | 0.694 |
| 090 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +2.5000 | force | 36 | 2.73 | False | 0.641 |
| 090 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +2.5000 | moment | 32 | 1.29 | False | 0.925 |
| 090 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +3.0000 | moment | 49 | 415 | False | 0.000431 |
| 090 | referencia.json | spencer | +1.5000 | force | 80 | 1.3 | False | 0.969 |
| 092 | resultados_modelo_sin_conexion.json | spencer | +2.0000 | moment | 8 | 2.55 | False | 0.789 |
| 092 | resultados_modelo_sin_conexion.json | spencer | +2.5000 | force | 13 | 2.29 | False | 0.587 |
| 092 | resultados_modelo_sin_conexion.json | spencer | +2.5000 | moment | 9 | 8.04 | False | 0.645 |
| 092 | resultados_modelo_sin_conexion.json | spencer | +3.0000 | force | 4 | 124 | True | 0.708 |
| 092 | resultados_modelo_sin_conexion.json | spencer | +3.5000 | moment | 4 | 250 | False | 0.67 |
| 093 | resultados.json | gle_morgenstern_price | +2.0000 | force | 21 | 1.1 | False | 0.0821 |
| 093 | resultados.json | gle_morgenstern_price | +2.0000 | moment | 16 | 3.02 | False | 0.799 |
| 093 | resultados.json | gle_morgenstern_price | +2.5000 | force | 33 | 62.1 | False | 0.391 |
| 093 | resultados.json | gle_morgenstern_price | +2.5000 | moment | 27 | 55 | False | 0.0352 |
| 093 | resultados.json | gle_morgenstern_price | +3.0000 | moment | 7 | 895 | True | 0.228 |
| 093 | resultados_modelo_sin_conexion.json | spencer | +1.0000 | moment | 18 | 2.39 | False | 0.941 |
| 093 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +2.0000 | force | 7 | 87.8 | False | 0.643 |
| 093 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +2.0000 | moment | 17 | 2.08 | False | 0.858 |
| 093 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +2.5000 | force | 32 | 33.2 | False | 0.28 |
| 093 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +2.5000 | moment | 26 | 41.9 | False | 0.133 |
| 093 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +3.0000 | moment | 25 | 4.31e+03 | True | 0.619 |
| 093 | referencia.json | spencer | +1.5000 | moment | 37 | 99.7 | False | 0.816 |
| 094 | resultados.json | spencer | +1.0000 | moment | 24 | 2.36 | False | 0.827 |
| 094 | resultados.json | gle_morgenstern_price | +2.5000 | force | 26 | 7.41 | False | 0.712 |
| 094 | resultados.json | gle_morgenstern_price | +2.5000 | moment | 25 | 4.53 | False | 0.791 |
| 094 | resultados.json | gle_morgenstern_price | +3.0000 | moment | 43 | 760 | True | 0.962 |
| 094 | resultados_modelo_sin_conexion.json | spencer | +1.0000 | moment | 24 | 2.04 | False | 0.734 |
| 094 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +3.0000 | force | 26 | 26.6 | False | 0.216 |
| 094 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +3.0000 | moment | 23 | 17.3 | False | 0.983 |
| 094 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +3.5000 | moment | 74 | 2.65e+04 | True | 0.866 |
| 094 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +4.0000 | moment | 29 | 4.72e+04 | True | 0.944 |
| 104 | resultados_modelo_ky.json | spencer | +0.6000 | moment | 4 | 9.35 | False | 0.11 |
| 104 | resultados_modelo_ky.json | spencer | +0.5417 | moment | 4 | 6.32 | False | 0.457 |
| 104 | resultados_modelo_ky.json | spencer | +0.5458 | moment | 4 | 6.5 | False | 0.412 |
| 104 | resultados_modelo_ky.json | spencer | +0.4000 | moment | 3 | 7.35 | False | 0.537 |
| 104 | resultados_modelo_ky.json | spencer | +0.4000 | moment | 3 | 7.34 | False | 0.767 |
| 104 | resultados_modelo_ky.json | spencer | +0.4000 | moment | 3 | 7.34 | False | 0.785 |
| 104 | resultados_modelo_ky.json | spencer | +0.4000 | moment | 3 | 7.34 | False | 0.791 |

## Ramas que siguen iterando con el par ya asentado

| problema | metodo | lambda | rama | asentada en | k* | espera |
|---|---|---|---|---|---|---|
| 011 | spencer | -0.1000 | force | 4 | 161 | 157 |
| 011 | gle_morgenstern_price | -0.1000 | force | 3 | 161 | 158 |
| 016 | spencer | +0.4000 | force | 10 | 47 | 37 |
| 025 | spencer | +0.5244 | moment | 12 | 40 | 28 |
| 025 | spencer | +0.5237 | moment | 12 | 38 | 26 |
| 047 | spencer | +0.4000 | moment | 23 | 100 | 77 |
| 061 | spencer | +0.8000 | force | 15 | 65 | 50 |
| 079 | spencer | -0.1000 | force | 4 | 161 | 157 |
| 081 | spencer | -0.1000 | force | 4 | 161 | 157 |
| 085 | gle_morgenstern_price | +1.0000 | moment | 23 | 59 | 36 |
| 085 | spencer | +0.6000 | moment | 21 | 45 | 24 |
| 086 | spencer | +0.8000 | force | 15 | 63 | 48 |
| 090 | spencer | +0.8000 | force | 27 | 119 | 92 |
| 090 | spencer | +0.6000 | force | 31 | 85 | 54 |
| 093 | spencer | +0.8000 | force | 18 | 136 | 118 |
| 093 | spencer | +0.8000 | force | 18 | 40 | 22 |

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

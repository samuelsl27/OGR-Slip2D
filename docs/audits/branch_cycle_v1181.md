# La salida `None` de una rama y la firma del ciclo - censo D148 - OGR 0.1.181 (SIN GUARDA)

Medido por `_tools/ciclo_rama_d148.py`, que solo mide. La pasada de muerte se busca por biseccion sobre `max_passes`, licita porque la muerte es monotona en el presupuesto; la racha se reconstruye con `criterio_rama_d145._paso`, importado y no copiado; y el `GLESystem` se captura parcheando `_inner_solve` en vez de construir uno parecido.

## Denominador - escalera de cunas

| que | cuantas |
|---|---|
| casos | 16 |
| ramas | 960 |
| medidas | 960 |
| saltados | 0 |
| problemas | 1 |
| criticas | 0 |
| publicadas | 0 |
| cunas | 16 |
| salidas nulas | 77 |
| nulas antes de STALL PATIENCE | 71 |
| nulas por sitio | {"m_alpha": 0, "momento_nulo": 0, "f_new_no_positivo": 77, "fuerzas_sin_discriminar": 0, "sin_dovelas": 0} |
| pasada de muerte minima | 2 |
| pasada de muerte mediana | 9 |
| pasada de muerte maxima | 191 |
| ramas vivas | 883 |
| aceptadas | 797 |
| racha maxima de una ACEPTADA | 43 |
| racha maxima de una NULA | 49 |
| histograma racha aceptadas | {"0": 574, "1": 184, "2": 36, "19": 1, "5": 1, "43": 1} |
| nulas alcanzadas por umbral | {"2": 58, "3": 44, "4": 40, "5": 35, "6": 35, "7": 30, "8": 30, "9": 26, "10": 25, "11": 24, "12": 24} |
| aceptadas tocadas por umbral | {"2": 39, "3": 3, "4": 3, "5": 3, "6": 2, "7": 2, "8": 2, "9": 2, "10": 2, "11": 2, "12": 2} |
| descuadradas | 0 |

## Denominador - banco

| que | cuantas |
|---|---|
| casos | 344 |
| ramas | 6020 |
| medidas | 6020 |
| saltados | 18 |
| problemas | 79 |
| criticas | 236 |
| publicadas | 108 |
| cunas | 0 |
| salidas nulas | 485 |
| nulas antes de STALL PATIENCE | 484 |
| nulas por sitio | {"m_alpha": 0, "momento_nulo": 36, "f_new_no_positivo": 96, "fuerzas_sin_discriminar": 353, "sin_dovelas": 0} |
| pasada de muerte minima | 1 |
| pasada de muerte mediana | 2 |
| pasada de muerte maxima | 90 |
| ramas vivas | 5535 |
| aceptadas | 5193 |
| racha maxima de una ACEPTADA | 61 |
| racha maxima de una NULA | 55 |
| histograma racha aceptadas | {"0": 4796, "1": 339, "2": 37, "4": 6, "61": 1, "3": 4, "5": 1, "6": 2, "57": 1, "29": 2, "18": 2, "10": 1, "8": 1} |
| nulas alcanzadas por umbral | {"2": 105, "3": 76, "4": 62, "5": 45, "6": 41, "7": 40, "8": 32, "9": 26, "10": 24, "11": 24, "12": 22} |
| aceptadas tocadas por umbral | {"2": 58, "3": 21, "4": 17, "5": 11, "6": 10, "7": 8, "8": 8, "9": 7, "10": 7, "11": 6, "12": 6} |
| descuadradas | 15 |

## El umbral, umbral por umbral

La columna que decide es `aceptadas tocadas`, y lo que la hace legible es partirla en dos. Una rama ya `rescued` es una que la puerta de v0.1.176 iba a tomar en la pasada 81 de todas formas, alcanzada antes; una ORDINARIA es una que la iteracion amortiguada estaba asentando sola, y de esas tiene que haber CERO o el predicado mueve un digito que hoy se publica.

| fuente | racha K | nulas que la alcanzan | aceptadas tocadas | de ellas rescatadas | ORDINARIAS |
|---|---|---|---|---|---|
| escalera de cunas | 2 | 58 | 39 | 13 | 26 |
| escalera de cunas | 3 | 44 | 3 | 3 | 0 |
| escalera de cunas | 4 | 40 | 3 | 3 | 0 |
| escalera de cunas | 5 | 35 | 3 | 3 | 0 |
| escalera de cunas | 6 | 35 | 2 | 2 | 0 |
| escalera de cunas | 7 | 30 | 2 | 2 | 0 |
| escalera de cunas | 8 | 30 | 2 | 2 | 0 |
| escalera de cunas | 9 | 26 | 2 | 2 | 0 |
| escalera de cunas | 10 | 25 | 2 | 2 | 0 |
| escalera de cunas | 11 | 24 | 2 | 2 | 0 |
| escalera de cunas | 12 | 24 | 2 | 2 | 0 |
| banco | 2 | 105 | 58 | 13 | 45 |
| banco | 3 | 76 | 21 | 10 | 11 |
| banco | 4 | 62 | 17 | 10 | 7 |
| banco | 5 | 45 | 11 | 10 | 1 |
| banco | 6 | 41 | 10 | 9 | 1 |
| banco | 7 | 40 | 8 | 7 | 1 |
| banco | 8 | 32 | 8 | 7 | 1 |
| banco | 9 | 26 | 7 | 7 | 0 |
| banco | 10 | 24 | 7 | 7 | 0 |
| banco | 11 | 24 | 6 | 6 | 0 |
| banco | 12 | 22 | 6 | 6 | 0 |

## Las ramas que mueren - escalera de cunas

| problema | archivo | metodo | lambda | rama | pasada | sitio | racha | f_new |
|---|---|---|---|---|---|---|---|---|
| cuna | spencer 35 activa | spencer | +2.5000 | moment | 49 | f_new_no_positivo | 22 | -6.50153 |
| cuna | spencer 35 activa | spencer | +2.7500 | moment | 31 | f_new_no_positivo | 12 | -2.6286 |
| cuna | spencer 35 activa | spencer | +3.0000 | moment | 23 | f_new_no_positivo | 8 | -4.76634 |
| cuna | spencer 35 pasiva | spencer | +2.7500 | moment | 61 | f_new_no_positivo | 30 | -1.49722 |
| cuna | spencer 35 pasiva | spencer | +3.0000 | moment | 37 | f_new_no_positivo | 14 | -5.97941 |
| cuna | spencer 40 activa | spencer | +2.2500 | moment | 65 | f_new_no_positivo | 39 | -42.1257 |
| cuna | spencer 40 activa | spencer | +2.5000 | moment | 31 | f_new_no_positivo | 21 | -21.0392 |
| cuna | spencer 40 activa | spencer | +2.7500 | moment | 21 | f_new_no_positivo | 14 | -6.74397 |
| cuna | spencer 40 activa | spencer | +3.0000 | moment | 17 | f_new_no_positivo | 14 | -0.79977 |
| cuna | spencer 40 pasiva | spencer | -2.0000 | moment | 191 | f_new_no_positivo | 2 | -2.62076 |
| cuna | spencer 40 pasiva | spencer | +2.5000 | moment | 67 | f_new_no_positivo | 41 | -1.75635 |
| cuna | spencer 40 pasiva | spencer | +2.7500 | moment | 35 | f_new_no_positivo | 24 | -1.83375 |
| cuna | spencer 40 pasiva | spencer | +3.0000 | moment | 23 | f_new_no_positivo | 16 | -31.0189 |
| cuna | spencer 45 activa | spencer | -2.0000 | moment | 49 | f_new_no_positivo | 3 | -10.2738 |
| cuna | spencer 45 activa | spencer | -1.7500 | moment | 134 | f_new_no_positivo | 3 | -4.79611 |
| cuna | spencer 45 activa | spencer | +2.0000 | moment | 23 | f_new_no_positivo | 17 | -35.9317 |
| cuna | spencer 45 activa | spencer | +2.2500 | moment | 13 | f_new_no_positivo | 10 | -22.4485 |
| cuna | spencer 45 activa | spencer | +2.5000 | moment | 11 | f_new_no_positivo | 8 | -0.512433 |
| cuna | spencer 45 activa | spencer | +2.7500 | moment | 9 | f_new_no_positivo | 6 | -0.501714 |
| cuna | spencer 45 activa | spencer | +3.0000 | moment | 7 | f_new_no_positivo | 4 | -1.62033 |
| cuna | spencer 45 pasiva | spencer | -2.0000 | moment | 110 | f_new_no_positivo | 3 | -0.454784 |
| cuna | spencer 45 pasiva | spencer | -1.7500 | moment | 154 | f_new_no_positivo | 2 | -6.12661 |
| cuna | spencer 45 pasiva | spencer | +2.2500 | moment | 25 | f_new_no_positivo | 19 | -3.7395 |
| cuna | spencer 45 pasiva | spencer | +2.5000 | moment | 15 | f_new_no_positivo | 12 | -2.68673 |
| cuna | spencer 45 pasiva | spencer | +2.7500 | moment | 11 | f_new_no_positivo | 8 | -2.68191 |
| cuna | spencer 45 pasiva | spencer | +3.0000 | moment | 9 | f_new_no_positivo | 6 | -2.09639 |
| cuna | spencer 50 sin ancla | spencer | -1.7500 | moment | 169 | f_new_no_positivo | 2 | -12.6909 |
| cuna | spencer 50 sin ancla | spencer | +2.7500 | moment | 23 | f_new_no_positivo | 20 | -0.482519 |
| cuna | spencer 50 sin ancla | spencer | +3.0000 | moment | 15 | f_new_no_positivo | 12 | -4.13646 |
| cuna | spencer 50 activa | spencer | -2.0000 | moment | 2 | f_new_no_positivo | 0 | -2.89888 |
| cuna | spencer 50 activa | spencer | -1.7500 | moment | 2 | f_new_no_positivo | 0 | -3.95478 |
| cuna | spencer 50 activa | spencer | -1.5000 | moment | 2 | f_new_no_positivo | 0 | -6.22056 |
| cuna | spencer 50 activa | spencer | -1.2500 | moment | 2 | f_new_no_positivo | 0 | -14.5654 |
| cuna | spencer 50 activa | spencer | -1.0000 | moment | 3 | f_new_no_positivo | 0 | -5.32709 |
| cuna | spencer 50 activa | spencer | -0.7500 | moment | 3 | f_new_no_positivo | 0 | -272.169 |
| cuna | spencer 50 activa | spencer | +1.0000 | moment | 39 | f_new_no_positivo | 27 | -6.48777 |
| cuna | spencer 50 activa | spencer | +1.2500 | moment | 9 | f_new_no_positivo | 6 | -2.68095 |
| cuna | spencer 50 activa | spencer | +1.5000 | moment | 5 | f_new_no_positivo | 2 | -18.287 |
| cuna | spencer 50 activa | spencer | +1.7500 | moment | 5 | f_new_no_positivo | 2 | -1.45454 |
| cuna | spencer 50 activa | spencer | +2.0000 | moment | 5 | f_new_no_positivo | 2 | -0.481108 |
| cuna | spencer 50 activa | spencer | +2.2500 | moment | 3 | f_new_no_positivo | 0 | -8.80357 |
| cuna | spencer 50 activa | spencer | +2.5000 | moment | 3 | f_new_no_positivo | 0 | -3.33029 |
| cuna | spencer 50 activa | spencer | +2.7500 | moment | 3 | f_new_no_positivo | 0 | -1.94749 |
| cuna | spencer 50 activa | spencer | +3.0000 | moment | 3 | f_new_no_positivo | 0 | -1.32776 |
| cuna | spencer 50 pasiva | spencer | -2.0000 | moment | 3 | f_new_no_positivo | 0 | -3.99314 |
| cuna | spencer 50 pasiva | spencer | -1.7500 | moment | 3 | f_new_no_positivo | 0 | -10.6185 |
| cuna | spencer 50 pasiva | spencer | -1.5000 | moment | 4 | f_new_no_positivo | 1 | -26.9254 |
| cuna | spencer 50 pasiva | spencer | -1.2500 | moment | 115 | f_new_no_positivo | 3 | -5.50429 |
| cuna | spencer 50 pasiva | spencer | +1.5000 | moment | 17 | f_new_no_positivo | 13 | -2.80992 |
| cuna | spencer 50 pasiva | spencer | +1.7500 | moment | 9 | f_new_no_positivo | 6 | -9.29912 |
| cuna | spencer 50 pasiva | spencer | +2.0000 | moment | 7 | f_new_no_positivo | 4 | -2.60211 |
| cuna | spencer 50 pasiva | spencer | +2.2500 | moment | 5 | f_new_no_positivo | 2 | -201.769 |
| cuna | spencer 50 pasiva | spencer | +2.5000 | moment | 5 | f_new_no_positivo | 2 | -1.99252 |
| cuna | spencer 50 pasiva | spencer | +2.7500 | moment | 5 | f_new_no_positivo | 2 | -0.769092 |
| cuna | spencer 50 pasiva | spencer | +3.0000 | moment | 5 | f_new_no_positivo | 2 | -0.38286 |
| cuna | gle 50 sin ancla | gle | +3.0000 | moment | 49 | f_new_no_positivo | 46 | -1.66037 |
| cuna | gle 50 activa | gle | -2.0000 | moment | 2 | f_new_no_positivo | 0 | -12.7267 |
| cuna | gle 50 activa | gle | -1.7500 | moment | 2 | f_new_no_positivo | 0 | -50.5772 |
| cuna | gle 50 activa | gle | -1.5000 | moment | 3 | f_new_no_positivo | 0 | -5.07195 |
| cuna | gle 50 activa | gle | -1.2500 | moment | 3 | f_new_no_positivo | 0 | -14.944 |
| cuna | gle 50 activa | gle | +1.2500 | moment | 29 | f_new_no_positivo | 19 | -8.11374 |
| cuna | gle 50 activa | gle | +1.5000 | moment | 11 | f_new_no_positivo | 8 | -4.3332 |
| cuna | gle 50 activa | gle | +1.7500 | moment | 7 | f_new_no_positivo | 4 | -6.47396 |
| cuna | gle 50 activa | gle | +2.0000 | moment | 5 | f_new_no_positivo | 2 | -26.5302 |
| cuna | gle 50 activa | gle | +2.2500 | moment | 5 | f_new_no_positivo | 2 | -2.40185 |
| cuna | gle 50 activa | gle | +2.5000 | moment | 5 | f_new_no_positivo | 2 | -0.944035 |
| cuna | gle 50 activa | gle | +2.7500 | moment | 5 | f_new_no_positivo | 2 | -0.45641 |
| cuna | gle 50 activa | gle | +3.0000 | moment | 3 | f_new_no_positivo | 0 | -19.9241 |
| cuna | gle 50 pasiva | gle | -2.0000 | moment | 5 | f_new_no_positivo | 1 | -13.9317 |
| cuna | gle 50 pasiva | gle | +1.7500 | moment | 23 | f_new_no_positivo | 15 | -7.78961 |
| cuna | gle 50 pasiva | gle | +2.0000 | moment | 13 | f_new_no_positivo | 9 | -5.53812 |
| cuna | gle 50 pasiva | gle | +2.2500 | moment | 9 | f_new_no_positivo | 6 | -13.1183 |
| cuna | gle 50 pasiva | gle | +2.5000 | moment | 7 | f_new_no_positivo | 4 | -27.1132 |
| cuna | gle 50 pasiva | gle | +2.7500 | moment | 7 | f_new_no_positivo | 4 | -1.12594 |
| cuna | gle 45 pasiva | gle | +2.5000 | moment | 69 | f_new_no_positivo | 49 | -0.922973 |
| cuna | gle 45 pasiva | gle | +2.7500 | moment | 29 | f_new_no_positivo | 19 | -10.5964 |
| cuna | gle 45 pasiva | gle | +3.0000 | moment | 19 | f_new_no_positivo | 13 | -65.4912 |

## Las ramas que mueren - banco

| problema | archivo | metodo | lambda | rama | pasada | sitio | racha | f_new |
|---|---|---|---|---|---|---|---|---|
| 011 | resultados.json | spencer | -0.1000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | spencer | +0.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | spencer | +0.0000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | spencer | +0.1000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | spencer | +0.1000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | spencer | +0.2000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | spencer | +0.2000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | spencer | +0.4000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | spencer | +0.4000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | spencer | +0.6000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | spencer | +0.6000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | spencer | +0.8000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | spencer | +0.8000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | spencer | +1.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | spencer | +1.0000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | spencer | +1.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | spencer | +1.5000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | -0.1000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +0.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +0.0000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +0.1000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +0.1000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +0.2000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +0.2000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +0.4000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +0.4000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +0.6000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +0.6000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +0.8000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +0.8000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +1.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +1.0000 | moment | 1 | momento_nulo | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +1.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 011 | resultados.json | gle_morgenstern_price | +1.5000 | moment | 1 | momento_nulo | 0 | - |
| 012 | referencia.json | spencer | -0.1000 | force | 90 | fuerzas_sin_discriminar | 12 | - |
| 015 | resultados_no_circular.json | spencer | +2.0000 | force | 5 | fuerzas_sin_discriminar | 1 | - |
| 015 | resultados_no_circular.json | spencer | +2.0000 | moment | 8 | f_new_no_positivo | 5 | -2.03362 |
| 015 | resultados_no_circular.json | spencer | +2.5000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 015 | resultados_no_circular.json | spencer | +2.5000 | moment | 4 | f_new_no_positivo | 1 | -1.80936 |
| 015 | resultados_no_circular.json | spencer | +3.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 015 | resultados_no_circular.json | spencer | +3.0000 | moment | 4 | f_new_no_positivo | 1 | -0.680263 |
| 015 | resultados_no_circular.json | spencer | +3.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 015 | resultados_no_circular.json | spencer | +3.5000 | moment | 2 | f_new_no_positivo | 0 | -4.29905 |
| 015 | resultados_no_circular.json | spencer | +4.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 015 | resultados_no_circular.json | spencer | +4.0000 | moment | 2 | f_new_no_positivo | 0 | -2.25737 |
| 015 | resultados_no_circular.json | spencer | +5.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 015 | resultados_no_circular.json | spencer | +5.0000 | moment | 2 | f_new_no_positivo | 0 | -1.23664 |
| 015 | resultados_no_circular.json | spencer | +6.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 015 | resultados_no_circular.json | spencer | +6.0000 | moment | 2 | f_new_no_positivo | 0 | -0.896421 |
| 047 | resultados.json | spencer | +0.8000 | moment | 8 | f_new_no_positivo | 5 | -2.70987 |
| 047 | resultados.json | spencer | +1.0000 | moment | 6 | f_new_no_positivo | 3 | -0.582821 |
| 047 | resultados.json | spencer | +1.5000 | moment | 4 | f_new_no_positivo | 1 | -0.391009 |
| 047 | resultados.json | spencer | +2.0000 | moment | 4 | f_new_no_positivo | 1 | -0.124995 |
| 047 | resultados.json | spencer | +2.5000 | moment | 2 | f_new_no_positivo | 0 | -3.90068 |
| 047 | resultados.json | spencer | +3.0000 | moment | 2 | f_new_no_positivo | 0 | -1.72975 |
| 047 | resultados.json | spencer | +3.5000 | moment | 2 | f_new_no_positivo | 0 | -1.11127 |
| 047 | resultados.json | spencer | +4.0000 | moment | 2 | f_new_no_positivo | 0 | -0.81858 |
| 047 | resultados.json | spencer | +5.0000 | moment | 2 | f_new_no_positivo | 0 | -0.536154 |
| 047 | resultados.json | spencer | +6.0000 | moment | 2 | f_new_no_positivo | 0 | -0.398622 |
| 047 | resultados_modelo_sin_bulones.json | spencer | +0.6000 | force | 37 | fuerzas_sin_discriminar | 31 | - |
| 047 | resultados_modelo_sin_bulones.json | spencer | +0.8000 | force | 11 | fuerzas_sin_discriminar | 7 | - |
| 047 | resultados_modelo_sin_bulones.json | spencer | +1.0000 | force | 7 | fuerzas_sin_discriminar | 3 | - |
| 047 | resultados_modelo_sin_bulones.json | spencer | +1.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 047 | resultados_modelo_sin_bulones.json | spencer | +2.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 047 | resultados_modelo_sin_bulones.json | spencer | +2.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 047 | resultados_modelo_sin_bulones.json | spencer | +3.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 047 | resultados_modelo_sin_bulones.json | spencer | +3.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 047 | resultados_modelo_sin_bulones.json | spencer | +4.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 047 | resultados_modelo_sin_bulones.json | spencer | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 047 | resultados_modelo_sin_bulones.json | spencer | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 059 | resultados.json | spencer | +2.0000 | force | 8 | fuerzas_sin_discriminar | 4 | - |
| 059 | resultados.json | spencer | +2.5000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 059 | resultados.json | spencer | +3.0000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 059 | resultados.json | spencer | +3.0000 | moment | 9 | f_new_no_positivo | 5 | -0.137132 |
| 059 | resultados.json | spencer | +3.5000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 059 | resultados.json | spencer | +3.5000 | moment | 7 | f_new_no_positivo | 3 | -0.61713 |
| 059 | resultados.json | spencer | +4.0000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 059 | resultados.json | spencer | +5.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 059 | resultados.json | spencer | +5.0000 | moment | 5 | f_new_no_positivo | 2 | -0.979458 |
| 059 | resultados.json | spencer | +6.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 060 | referencia.json | spencer | +0.8000 | force | 37 | fuerzas_sin_discriminar | 29 | - |
| 060 | referencia.json | spencer | +1.0000 | force | 11 | fuerzas_sin_discriminar | 7 | - |
| 060 | referencia.json | spencer | +1.5000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 060 | referencia.json | spencer | +2.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 060 | referencia.json | spencer | +2.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 060 | referencia.json | spencer | +3.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 060 | referencia.json | spencer | +3.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 060 | referencia.json | spencer | +4.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 060 | referencia.json | spencer | +5.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 068 | resultados.json | spencer | +0.8000 | force | 61 | fuerzas_sin_discriminar | 55 | - |
| 068 | resultados.json | spencer | +1.0000 | force | 17 | fuerzas_sin_discriminar | 12 | - |
| 068 | resultados.json | spencer | +1.5000 | force | 7 | fuerzas_sin_discriminar | 2 | - |
| 068 | resultados.json | spencer | +2.0000 | force | 5 | fuerzas_sin_discriminar | 0 | - |
| 068 | resultados.json | spencer | +2.5000 | force | 5 | fuerzas_sin_discriminar | 0 | - |
| 068 | resultados.json | spencer | +3.0000 | force | 5 | fuerzas_sin_discriminar | 1 | - |
| 068 | resultados.json | spencer | +5.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 068 | resultados.json | spencer | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 068 | resultados.json | gle_morgenstern_price | +2.5000 | force | 26 | fuerzas_sin_discriminar | 7 | - |
| 068 | resultados.json | gle_morgenstern_price | +3.0000 | force | 13 | fuerzas_sin_discriminar | 4 | - |
| 068 | resultados.json | gle_morgenstern_price | +3.5000 | force | 7 | fuerzas_sin_discriminar | 1 | - |
| 068 | resultados.json | gle_morgenstern_price | +4.0000 | force | 7 | fuerzas_sin_discriminar | 1 | - |
| 068 | resultados.json | gle_morgenstern_price | +5.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 068 | resultados.json | gle_morgenstern_price | +6.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_1a.json | spencer | +0.8000 | force | 21 | fuerzas_sin_discriminar | 17 | - |
| 078 | resultados_modelo_1a.json | spencer | +1.0000 | force | 11 | fuerzas_sin_discriminar | 7 | - |
| 078 | resultados_modelo_1a.json | spencer | +1.5000 | force | 5 | fuerzas_sin_discriminar | 1 | - |
| 078 | resultados_modelo_1a.json | spencer | +2.0000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 078 | resultados_modelo_1a.json | spencer | +2.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_1a.json | spencer | +3.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_1a.json | spencer | +3.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_1a.json | spencer | +4.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_1a.json | spencer | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_1a.json | spencer | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_1a.json | gle_morgenstern_price | +2.5000 | force | 24 | fuerzas_sin_discriminar | 7 | - |
| 078 | resultados_modelo_1a.json | gle_morgenstern_price | +3.0000 | force | 13 | fuerzas_sin_discriminar | 3 | - |
| 078 | resultados_modelo_1a.json | gle_morgenstern_price | +3.5000 | force | 9 | fuerzas_sin_discriminar | 2 | - |
| 078 | resultados_modelo_1a.json | gle_morgenstern_price | +4.0000 | force | 4 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_1a.json | gle_morgenstern_price | +5.0000 | force | 4 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_1a.json | gle_morgenstern_price | +6.0000 | force | 4 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_2a.json | spencer | +0.8000 | force | 21 | fuerzas_sin_discriminar | 17 | - |
| 078 | resultados_modelo_2a.json | spencer | +1.0000 | force | 11 | fuerzas_sin_discriminar | 7 | - |
| 078 | resultados_modelo_2a.json | spencer | +1.5000 | force | 5 | fuerzas_sin_discriminar | 1 | - |
| 078 | resultados_modelo_2a.json | spencer | +2.0000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 078 | resultados_modelo_2a.json | spencer | +2.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_2a.json | spencer | +3.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_2a.json | spencer | +3.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_2a.json | spencer | +4.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_2a.json | spencer | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_2a.json | spencer | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_2a.json | gle_morgenstern_price | +2.5000 | force | 24 | fuerzas_sin_discriminar | 7 | - |
| 078 | resultados_modelo_2a.json | gle_morgenstern_price | +3.0000 | force | 13 | fuerzas_sin_discriminar | 3 | - |
| 078 | resultados_modelo_2a.json | gle_morgenstern_price | +3.5000 | force | 9 | fuerzas_sin_discriminar | 2 | - |
| 078 | resultados_modelo_2a.json | gle_morgenstern_price | +4.0000 | force | 4 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_2a.json | gle_morgenstern_price | +5.0000 | force | 4 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_2a.json | gle_morgenstern_price | +6.0000 | force | 4 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_3a.json | spencer | +0.6000 | force | 47 | fuerzas_sin_discriminar | 41 | - |
| 078 | resultados_modelo_3a.json | spencer | +0.8000 | force | 13 | fuerzas_sin_discriminar | 9 | - |
| 078 | resultados_modelo_3a.json | spencer | +1.0000 | force | 7 | fuerzas_sin_discriminar | 3 | - |
| 078 | resultados_modelo_3a.json | spencer | +1.5000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 078 | resultados_modelo_3a.json | spencer | +2.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_3a.json | spencer | +2.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_3a.json | spencer | +3.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_3a.json | spencer | +3.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_3a.json | spencer | +4.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_3a.json | spencer | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_3a.json | spencer | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_3a.json | gle_morgenstern_price | +3.5000 | force | 7 | fuerzas_sin_discriminar | 2 | - |
| 078 | resultados_modelo_3a.json | gle_morgenstern_price | +4.0000 | force | 4 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_3a.json | gle_morgenstern_price | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_modelo_3a.json | gle_morgenstern_price | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +1.5000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +1.5000 | moment | 2 | f_new_no_positivo | 0 | -17.1876 |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +2.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +2.0000 | moment | 2 | f_new_no_positivo | 0 | -2.36266 |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +2.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +2.5000 | moment | 2 | f_new_no_positivo | 0 | -1.26852 |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +3.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +3.0000 | moment | 2 | f_new_no_positivo | 0 | -0.867008 |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +3.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +3.5000 | moment | 2 | f_new_no_positivo | 0 | -0.658561 |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +4.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +4.0000 | moment | 2 | f_new_no_positivo | 0 | -0.530918 |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +5.0000 | moment | 2 | f_new_no_positivo | 0 | -0.382604 |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1a.json | gle_morgenstern_price | +6.0000 | moment | 2 | f_new_no_positivo | 0 | -0.29906 |
| 078 | resultados_no_circular_1b.json | spencer | +0.8000 | moment | 4 | f_new_no_positivo | 1 | -7.84097 |
| 078 | resultados_no_circular_1b.json | spencer | +1.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | spencer | +1.0000 | moment | 2 | f_new_no_positivo | 0 | -9.92543 |
| 078 | resultados_no_circular_1b.json | spencer | +1.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | spencer | +1.5000 | moment | 2 | f_new_no_positivo | 0 | -1.43891 |
| 078 | resultados_no_circular_1b.json | spencer | +2.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | spencer | +2.0000 | moment | 2 | f_new_no_positivo | 0 | -0.775679 |
| 078 | resultados_no_circular_1b.json | spencer | +2.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | spencer | +2.5000 | moment | 2 | f_new_no_positivo | 0 | -0.53095 |
| 078 | resultados_no_circular_1b.json | spencer | +3.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | spencer | +3.0000 | moment | 2 | f_new_no_positivo | 0 | -0.403611 |
| 078 | resultados_no_circular_1b.json | spencer | +3.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | spencer | +3.5000 | moment | 2 | f_new_no_positivo | 0 | -0.325536 |
| 078 | resultados_no_circular_1b.json | spencer | +4.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | spencer | +4.0000 | moment | 2 | f_new_no_positivo | 0 | -0.272771 |
| 078 | resultados_no_circular_1b.json | spencer | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | spencer | +5.0000 | moment | 2 | f_new_no_positivo | 0 | -0.205994 |
| 078 | resultados_no_circular_1b.json | spencer | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | spencer | +6.0000 | moment | 2 | f_new_no_positivo | 0 | -0.165482 |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +0.8000 | moment | 58 | f_new_no_positivo | 44 | -296.088 |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +1.0000 | moment | 2 | f_new_no_positivo | 0 | -13.0543 |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +1.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +1.5000 | moment | 2 | f_new_no_positivo | 0 | -1.55829 |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +2.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +2.0000 | moment | 2 | f_new_no_positivo | 0 | -0.828601 |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +2.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +2.5000 | moment | 2 | f_new_no_positivo | 0 | -0.564341 |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +3.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +3.0000 | moment | 2 | f_new_no_positivo | 0 | -0.42788 |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +3.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +3.5000 | moment | 2 | f_new_no_positivo | 0 | -0.344563 |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +4.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +4.0000 | moment | 2 | f_new_no_positivo | 0 | -0.288404 |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +5.0000 | moment | 2 | f_new_no_positivo | 0 | -0.217504 |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_1b.json | gle_morgenstern_price | +6.0000 | moment | 2 | f_new_no_positivo | 0 | -0.174585 |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +1.5000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +1.5000 | moment | 2 | f_new_no_positivo | 0 | -17.1876 |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +2.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +2.0000 | moment | 2 | f_new_no_positivo | 0 | -2.36266 |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +2.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +2.5000 | moment | 2 | f_new_no_positivo | 0 | -1.26852 |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +3.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +3.0000 | moment | 2 | f_new_no_positivo | 0 | -0.867008 |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +3.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +3.5000 | moment | 2 | f_new_no_positivo | 0 | -0.658561 |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +4.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +4.0000 | moment | 2 | f_new_no_positivo | 0 | -0.530918 |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +5.0000 | moment | 2 | f_new_no_positivo | 0 | -0.382604 |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_2a.json | gle_morgenstern_price | +6.0000 | moment | 2 | f_new_no_positivo | 0 | -0.29906 |
| 078 | resultados_no_circular_3a.json | spencer | +1.5000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_3a.json | spencer | +1.5000 | moment | 4 | f_new_no_positivo | 1 | -1.18955 |
| 078 | resultados_no_circular_3a.json | spencer | +2.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_3a.json | spencer | +2.0000 | moment | 2 | f_new_no_positivo | 0 | -5.4205 |
| 078 | resultados_no_circular_3a.json | spencer | +2.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_3a.json | spencer | +2.5000 | moment | 2 | f_new_no_positivo | 0 | -2.05511 |
| 078 | resultados_no_circular_3a.json | spencer | +3.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_3a.json | spencer | +3.0000 | moment | 2 | f_new_no_positivo | 0 | -1.26791 |
| 078 | resultados_no_circular_3a.json | spencer | +3.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_3a.json | spencer | +3.5000 | moment | 2 | f_new_no_positivo | 0 | -0.916751 |
| 078 | resultados_no_circular_3a.json | spencer | +4.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_3a.json | spencer | +4.0000 | moment | 2 | f_new_no_positivo | 0 | -0.717918 |
| 078 | resultados_no_circular_3a.json | spencer | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_3a.json | spencer | +5.0000 | moment | 2 | f_new_no_positivo | 0 | -0.500718 |
| 078 | resultados_no_circular_3a.json | spencer | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_3a.json | spencer | +6.0000 | moment | 2 | f_new_no_positivo | 0 | -0.384416 |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +1.5000 | moment | 4 | f_new_no_positivo | 1 | -5.30392 |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +2.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +2.0000 | moment | 2 | f_new_no_positivo | 0 | -3.65589 |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +2.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +2.5000 | moment | 2 | f_new_no_positivo | 0 | -1.66392 |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +3.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +3.0000 | moment | 2 | f_new_no_positivo | 0 | -1.07707 |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +3.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +3.5000 | moment | 2 | f_new_no_positivo | 0 | -0.796238 |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +4.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +4.0000 | moment | 2 | f_new_no_positivo | 0 | -0.631567 |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +5.0000 | moment | 2 | f_new_no_positivo | 0 | -0.446772 |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | resultados_no_circular_3a.json | gle_morgenstern_price | +6.0000 | moment | 2 | f_new_no_positivo | 0 | -0.345638 |
| 078 | referencia.json | spencer | +0.8000 | force | 39 | fuerzas_sin_discriminar | 33 | - |
| 078 | referencia.json | spencer | +1.0000 | force | 15 | fuerzas_sin_discriminar | 11 | - |
| 078 | referencia.json | spencer | +1.5000 | force | 7 | fuerzas_sin_discriminar | 3 | - |
| 078 | referencia.json | spencer | +2.0000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 078 | referencia.json | spencer | +2.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +3.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +3.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +4.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +0.8000 | force | 39 | fuerzas_sin_discriminar | 33 | - |
| 078 | referencia.json | spencer | +1.0000 | force | 15 | fuerzas_sin_discriminar | 11 | - |
| 078 | referencia.json | spencer | +1.5000 | force | 7 | fuerzas_sin_discriminar | 3 | - |
| 078 | referencia.json | spencer | +2.0000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 078 | referencia.json | spencer | +2.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +3.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +3.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +4.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +0.8000 | force | 23 | fuerzas_sin_discriminar | 18 | - |
| 078 | referencia.json | spencer | +1.0000 | force | 11 | fuerzas_sin_discriminar | 7 | - |
| 078 | referencia.json | spencer | +1.5000 | force | 5 | fuerzas_sin_discriminar | 1 | - |
| 078 | referencia.json | spencer | +2.0000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 078 | referencia.json | spencer | +2.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +3.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +3.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +4.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 078 | referencia.json | spencer | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 079 | referencia.json | spencer | -0.1000 | moment | 1 | momento_nulo | 0 | - |
| 079 | referencia.json | spencer | +0.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 079 | referencia.json | spencer | +0.0000 | moment | 1 | momento_nulo | 0 | - |
| 079 | referencia.json | spencer | +0.1000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 079 | referencia.json | spencer | +0.1000 | moment | 1 | momento_nulo | 0 | - |
| 079 | referencia.json | spencer | +0.2000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 079 | referencia.json | spencer | +0.2000 | moment | 1 | momento_nulo | 0 | - |
| 079 | referencia.json | spencer | +0.4000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 079 | referencia.json | spencer | +0.4000 | moment | 1 | momento_nulo | 0 | - |
| 079 | referencia.json | spencer | +0.6000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 079 | referencia.json | spencer | +0.6000 | moment | 1 | momento_nulo | 0 | - |
| 079 | referencia.json | spencer | +0.8000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 079 | referencia.json | spencer | +0.8000 | moment | 1 | momento_nulo | 0 | - |
| 079 | referencia.json | spencer | +1.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 079 | referencia.json | spencer | +1.0000 | moment | 1 | momento_nulo | 0 | - |
| 079 | referencia.json | spencer | +1.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 079 | referencia.json | spencer | +1.5000 | moment | 1 | momento_nulo | 0 | - |
| 081 | referencia.json | spencer | -0.1000 | moment | 1 | momento_nulo | 0 | - |
| 081 | referencia.json | spencer | +0.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 081 | referencia.json | spencer | +0.0000 | moment | 1 | momento_nulo | 0 | - |
| 081 | referencia.json | spencer | +0.1000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 081 | referencia.json | spencer | +0.1000 | moment | 1 | momento_nulo | 0 | - |
| 081 | referencia.json | spencer | +0.2000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 081 | referencia.json | spencer | +0.2000 | moment | 1 | momento_nulo | 0 | - |
| 081 | referencia.json | spencer | +0.4000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 081 | referencia.json | spencer | +0.4000 | moment | 1 | momento_nulo | 0 | - |
| 081 | referencia.json | spencer | +0.6000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 081 | referencia.json | spencer | +0.6000 | moment | 1 | momento_nulo | 0 | - |
| 081 | referencia.json | spencer | +0.8000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 081 | referencia.json | spencer | +0.8000 | moment | 1 | momento_nulo | 0 | - |
| 081 | referencia.json | spencer | +1.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 081 | referencia.json | spencer | +1.0000 | moment | 1 | momento_nulo | 0 | - |
| 081 | referencia.json | spencer | +1.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 081 | referencia.json | spencer | +1.5000 | moment | 1 | momento_nulo | 0 | - |
| 085 | resultados_modelo_activo.json | spencer | +1.5000 | force | 11 | fuerzas_sin_discriminar | 4 | - |
| 085 | resultados_modelo_activo.json | spencer | +2.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_activo.json | spencer | +2.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_activo.json | spencer | +3.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_activo.json | spencer | +3.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_activo.json | spencer | +4.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_activo.json | spencer | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_activo.json | spencer | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_activo.json | gle_morgenstern_price | +3.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_activo.json | gle_morgenstern_price | +3.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_activo.json | gle_morgenstern_price | +4.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_activo.json | gle_morgenstern_price | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_activo.json | gle_morgenstern_price | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_pasivo.json | spencer | +0.8000 | force | 25 | fuerzas_sin_discriminar | 16 | - |
| 085 | resultados_modelo_pasivo.json | spencer | +1.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_pasivo.json | spencer | +1.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_pasivo.json | spencer | +2.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_pasivo.json | spencer | +2.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_pasivo.json | spencer | +3.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_pasivo.json | spencer | +3.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_pasivo.json | spencer | +4.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_pasivo.json | spencer | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_pasivo.json | spencer | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_pasivo.json | gle_morgenstern_price | +4.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_pasivo.json | gle_morgenstern_price | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_modelo_pasivo.json | gle_morgenstern_price | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | spencer | +1.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | spencer | +1.5000 | moment | 5 | f_new_no_positivo | 2 | -6.3755 |
| 085 | resultados_no_circular_activo.json | spencer | +2.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | spencer | +2.0000 | moment | 3 | f_new_no_positivo | 0 | -39.3339 |
| 085 | resultados_no_circular_activo.json | spencer | +2.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | spencer | +2.5000 | moment | 3 | f_new_no_positivo | 0 | -5.15267 |
| 085 | resultados_no_circular_activo.json | spencer | +3.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | spencer | +3.0000 | moment | 3 | f_new_no_positivo | 0 | -2.59979 |
| 085 | resultados_no_circular_activo.json | spencer | +3.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | spencer | +3.5000 | moment | 3 | f_new_no_positivo | 0 | -1.67464 |
| 085 | resultados_no_circular_activo.json | spencer | +4.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | spencer | +4.0000 | moment | 3 | f_new_no_positivo | 0 | -1.20255 |
| 085 | resultados_no_circular_activo.json | spencer | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | spencer | +5.0000 | moment | 3 | f_new_no_positivo | 0 | -0.731962 |
| 085 | resultados_no_circular_activo.json | spencer | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | spencer | +6.0000 | moment | 3 | f_new_no_positivo | 0 | -0.502882 |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +1.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +1.5000 | moment | 9 | f_new_no_positivo | 3 | -17.7246 |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +2.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +2.0000 | moment | 3 | f_new_no_positivo | 0 | -26.3778 |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +2.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +2.5000 | moment | 3 | f_new_no_positivo | 0 | -6.19517 |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +3.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +3.0000 | moment | 2 | f_new_no_positivo | 0 | -20.8723 |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +3.5000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +3.5000 | moment | 2 | f_new_no_positivo | 0 | -7.95774 |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +4.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +4.0000 | moment | 2 | f_new_no_positivo | 0 | -4.916 |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +5.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +5.0000 | moment | 2 | f_new_no_positivo | 0 | -2.7861 |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | +6.0000 | moment | 2 | f_new_no_positivo | 0 | -1.94389 |
| 085 | resultados_no_circular_pasivo.json | spencer | +1.5000 | moment | 5 | f_new_no_positivo | 2 | -2.82539 |
| 085 | resultados_no_circular_pasivo.json | spencer | +2.0000 | moment | 3 | f_new_no_positivo | 0 | -14.1239 |
| 085 | resultados_no_circular_pasivo.json | spencer | +2.5000 | moment | 3 | f_new_no_positivo | 0 | -2.54367 |
| 085 | resultados_no_circular_pasivo.json | spencer | +3.0000 | moment | 3 | f_new_no_positivo | 0 | -1.27429 |
| 085 | resultados_no_circular_pasivo.json | spencer | +3.5000 | moment | 3 | f_new_no_positivo | 0 | -0.802763 |
| 085 | resultados_no_circular_pasivo.json | spencer | +4.0000 | moment | 3 | f_new_no_positivo | 0 | -0.563058 |
| 085 | resultados_no_circular_pasivo.json | spencer | +5.0000 | moment | 3 | f_new_no_positivo | 0 | -0.328423 |
| 085 | resultados_no_circular_pasivo.json | spencer | +6.0000 | force | 1 | fuerzas_sin_discriminar | 0 | - |
| 085 | resultados_no_circular_pasivo.json | spencer | +6.0000 | moment | 3 | f_new_no_positivo | 0 | -0.217796 |
| 087 | resultados.json | spencer | +1.5000 | force | 11 | fuerzas_sin_discriminar | 8 | - |
| 087 | resultados.json | spencer | +2.0000 | force | 7 | fuerzas_sin_discriminar | 4 | - |
| 087 | resultados.json | spencer | +2.5000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 087 | resultados.json | spencer | +3.0000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 087 | resultados.json | spencer | +3.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 087 | resultados.json | spencer | +4.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 087 | resultados.json | spencer | +5.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 087 | resultados.json | spencer | +6.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 087 | resultados.json | gle_morgenstern_price | +5.0000 | force | 10 | fuerzas_sin_discriminar | 4 | - |
| 087 | resultados.json | gle_morgenstern_price | +6.0000 | force | 9 | fuerzas_sin_discriminar | 4 | - |
| 087 | resultados_modelo_sin_conexion.json | spencer | +1.5000 | force | 11 | fuerzas_sin_discriminar | 8 | - |
| 087 | resultados_modelo_sin_conexion.json | spencer | +2.0000 | force | 7 | fuerzas_sin_discriminar | 4 | - |
| 087 | resultados_modelo_sin_conexion.json | spencer | +2.5000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 087 | resultados_modelo_sin_conexion.json | spencer | +3.0000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 087 | resultados_modelo_sin_conexion.json | spencer | +3.5000 | force | 4 | fuerzas_sin_discriminar | 0 | - |
| 087 | resultados_modelo_sin_conexion.json | spencer | +4.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 087 | resultados_modelo_sin_conexion.json | spencer | +5.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 087 | resultados_modelo_sin_conexion.json | spencer | +6.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 087 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +5.0000 | force | 10 | fuerzas_sin_discriminar | 4 | - |
| 087 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +6.0000 | force | 9 | fuerzas_sin_discriminar | 4 | - |
| 090 | resultados.json | spencer | +0.8000 | force | 39 | fuerzas_sin_discriminar | 36 | - |
| 090 | resultados.json | spencer | +1.0000 | force | 11 | fuerzas_sin_discriminar | 8 | - |
| 090 | resultados.json | spencer | +1.5000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 090 | resultados.json | spencer | +2.0000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 090 | resultados.json | spencer | +2.5000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 090 | resultados.json | spencer | +3.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 090 | resultados.json | spencer | +3.5000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 090 | resultados.json | spencer | +4.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 090 | resultados.json | spencer | +5.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 090 | resultados.json | spencer | +6.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 090 | resultados.json | gle_morgenstern_price | +4.0000 | force | 9 | fuerzas_sin_discriminar | 2 | - |
| 090 | resultados.json | gle_morgenstern_price | +5.0000 | force | 7 | fuerzas_sin_discriminar | 1 | - |
| 090 | resultados.json | gle_morgenstern_price | +6.0000 | force | 5 | fuerzas_sin_discriminar | 1 | - |
| 090 | resultados_modelo_sin_conexion.json | spencer | +1.0000 | force | 15 | fuerzas_sin_discriminar | 12 | - |
| 090 | resultados_modelo_sin_conexion.json | spencer | +1.5000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 090 | resultados_modelo_sin_conexion.json | spencer | +2.0000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 090 | resultados_modelo_sin_conexion.json | spencer | +2.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 090 | resultados_modelo_sin_conexion.json | spencer | +3.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 090 | resultados_modelo_sin_conexion.json | spencer | +3.5000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 090 | resultados_modelo_sin_conexion.json | spencer | +4.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 090 | resultados_modelo_sin_conexion.json | spencer | +5.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 090 | resultados_modelo_sin_conexion.json | spencer | +6.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 090 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +4.0000 | force | 9 | fuerzas_sin_discriminar | 2 | - |
| 090 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +5.0000 | force | 7 | fuerzas_sin_discriminar | 1 | - |
| 090 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +6.0000 | force | 5 | fuerzas_sin_discriminar | 1 | - |
| 090 | referencia.json | spencer | +2.0000 | force | 17 | fuerzas_sin_discriminar | 13 | - |
| 090 | referencia.json | spencer | +2.5000 | force | 8 | fuerzas_sin_discriminar | 5 | - |
| 090 | referencia.json | spencer | +3.0000 | force | 6 | fuerzas_sin_discriminar | 3 | - |
| 090 | referencia.json | spencer | +3.5000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 090 | referencia.json | spencer | +4.0000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 090 | referencia.json | spencer | +5.0000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 090 | referencia.json | spencer | +6.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 092 | resultados_modelo_sin_conexion.json | spencer | +4.0000 | force | 50 | fuerzas_sin_discriminar | 45 | - |
| 092 | resultados_modelo_sin_conexion.json | spencer | +5.0000 | force | 20 | fuerzas_sin_discriminar | 15 | - |
| 093 | resultados.json | spencer | +0.8000 | force | 54 | fuerzas_sin_discriminar | 49 | - |
| 093 | resultados.json | spencer | +1.0000 | force | 16 | fuerzas_sin_discriminar | 13 | - |
| 093 | resultados.json | spencer | +1.5000 | force | 7 | fuerzas_sin_discriminar | 4 | - |
| 093 | resultados.json | spencer | +2.0000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 093 | resultados.json | spencer | +2.5000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 093 | resultados.json | spencer | +3.0000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 093 | resultados.json | spencer | +3.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 093 | resultados.json | spencer | +4.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 093 | resultados.json | spencer | +5.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 093 | resultados.json | spencer | +6.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 093 | resultados.json | gle_morgenstern_price | +3.5000 | force | 17 | fuerzas_sin_discriminar | 8 | - |
| 093 | resultados.json | gle_morgenstern_price | +4.0000 | force | 11 | fuerzas_sin_discriminar | 4 | - |
| 093 | resultados.json | gle_morgenstern_price | +5.0000 | force | 9 | fuerzas_sin_discriminar | 4 | - |
| 093 | resultados.json | gle_morgenstern_price | +6.0000 | force | 6 | fuerzas_sin_discriminar | 3 | - |
| 093 | resultados_modelo_sin_conexion.json | spencer | +0.8000 | force | 53 | fuerzas_sin_discriminar | 48 | - |
| 093 | resultados_modelo_sin_conexion.json | spencer | +1.0000 | force | 16 | fuerzas_sin_discriminar | 13 | - |
| 093 | resultados_modelo_sin_conexion.json | spencer | +1.5000 | force | 7 | fuerzas_sin_discriminar | 4 | - |
| 093 | resultados_modelo_sin_conexion.json | spencer | +2.0000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 093 | resultados_modelo_sin_conexion.json | spencer | +2.5000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 093 | resultados_modelo_sin_conexion.json | spencer | +3.0000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 093 | resultados_modelo_sin_conexion.json | spencer | +3.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 093 | resultados_modelo_sin_conexion.json | spencer | +4.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 093 | resultados_modelo_sin_conexion.json | spencer | +5.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 093 | resultados_modelo_sin_conexion.json | spencer | +6.0000 | force | 2 | fuerzas_sin_discriminar | 0 | - |
| 093 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +4.0000 | force | 11 | fuerzas_sin_discriminar | 3 | - |
| 093 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +5.0000 | force | 9 | fuerzas_sin_discriminar | 3 | - |
| 093 | referencia.json | spencer | +2.0000 | force | 23 | fuerzas_sin_discriminar | 9 | - |
| 093 | referencia.json | spencer | +4.0000 | force | 6 | fuerzas_sin_discriminar | 3 | - |
| 093 | referencia.json | spencer | +5.0000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 093 | referencia.json | spencer | +6.0000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 094 | resultados.json | spencer | +1.5000 | force | 11 | fuerzas_sin_discriminar | 8 | - |
| 094 | resultados.json | spencer | +2.0000 | force | 7 | fuerzas_sin_discriminar | 4 | - |
| 094 | resultados.json | spencer | +2.5000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 094 | resultados.json | spencer | +3.0000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 094 | resultados.json | spencer | +3.5000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 094 | resultados.json | spencer | +4.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 094 | resultados.json | spencer | +5.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 094 | resultados.json | spencer | +6.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 094 | resultados.json | gle_morgenstern_price | +5.0000 | force | 10 | fuerzas_sin_discriminar | 4 | - |
| 094 | resultados.json | gle_morgenstern_price | +6.0000 | force | 9 | fuerzas_sin_discriminar | 4 | - |
| 094 | resultados_modelo_sin_conexion.json | spencer | +1.5000 | force | 11 | fuerzas_sin_discriminar | 8 | - |
| 094 | resultados_modelo_sin_conexion.json | spencer | +2.0000 | force | 7 | fuerzas_sin_discriminar | 4 | - |
| 094 | resultados_modelo_sin_conexion.json | spencer | +2.5000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 094 | resultados_modelo_sin_conexion.json | spencer | +3.0000 | force | 5 | fuerzas_sin_discriminar | 2 | - |
| 094 | resultados_modelo_sin_conexion.json | spencer | +3.5000 | force | 4 | fuerzas_sin_discriminar | 1 | - |
| 094 | resultados_modelo_sin_conexion.json | spencer | +4.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 094 | resultados_modelo_sin_conexion.json | spencer | +5.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 094 | resultados_modelo_sin_conexion.json | spencer | +6.0000 | force | 3 | fuerzas_sin_discriminar | 0 | - |
| 094 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +5.0000 | force | 15 | fuerzas_sin_discriminar | 6 | - |
| 094 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | +6.0000 | force | 8 | fuerzas_sin_discriminar | 2 | - |

### Saltadas - banco

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

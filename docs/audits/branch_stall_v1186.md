# El detector de estancamiento mira media pareja — censo D158 — OGR 0.1.186

Generado por `_tools/estancamiento_d158.py`, que SOLO MIDE. Busquedas ENTERAS, no criticas archivadas: el cero que la ficha publica sobre `censo_0.1.183.json` es cota inferior por construccion.

## Denominador

| | |
|---|---|
| filas medidas | 35 |
| problemas | 22 |
| ramas resueltas | 2992152 |
| aceptadas | 2383186 |
| perdidas por presupuesto | 10913 |
| perdidas por desbordamiento de empuje | 179541 |
| sin estado (`None`) | 357976 |
| **cortadas por ESTANCAMIENTO** | **60536** |
| de esas, clasificadas | 7648 |
| descartadas por el control (A) | 0 |
| saltadas | 24 |
| **sin medir** (tope de tiempo) | 26 |

**El denominador de ramas NO es comparable con el de 0.1.185 ni con las 5699 de `censo_0.1.183.json`**: desde v0.1.186 (D159) un lambda repetido no vuelve a llamar a `solve_branch`, asi que se ven menos ramas sin que el solver haya cambiado.

Sin medir, NOMBRADOS para poder reanudar: 088 089 090 091 092 093 094 045 101 086 001 002 003 004 006 012 013 024 030 036 038 074 082 083 084 010.

## Los cuatro cubos

**OJO AL DENOMINADOR DE ESTA TABLA, que no es el de la anterior.** Los cubos reparten las **7648 ramas CLASIFICADAS**, no las 60536 cortadas por estancamiento. La diferencia es el tope de 400 reconstrucciones por fila, alcanzado en 15 de las 35 filas. Y ese tope **no toma una muestra al azar**: se queda con las PRIMERAS 400 de cada fila, asi que los porcentajes de abajo no se pueden extrapolar a las 60536. Lo que si se puede afirmar es lo medido: existen al menos 627 ramas en (ii)+(iv), y eso basta para que la poblacion no sea cero.

| | |
|---|---|
| (i) empuje vivo y NO contrayendo — el detector acierta | 1479 |
| (ii) empuje vivo y CONTRAYENDO | **616** |
| (iii) F clavada en el recorte | 5542 |
| (iv) F y X asentadas, cortada igual | **11** |
| **poblacion del defecto = (ii) + (iv)** | **627** |

## Lo que costaria, como COTA SUPERIOR

Medido volviendo a lanzar cada rama de (ii) y (iv) con `patience` enorme y el mismo `max_passes`. Es una cota superior y no el coste del detector por pares, que seguiria cortando cuando NINGUNO de los dos residuos bate su record.

| pasadas de mas | 65027 |
| respuestas compradas a cambio | 434 |

## Por fila

| problema | metodo | ramas | estancadas | (i) | (ii) | (iii) | (iv) | control |
|---|---|---|---|---|---|---|---|---|
| 027 | spencer | 10558 | 363 | 0 | **2** | 361 | **0** | +0.0001 % |
| 027 | gle_morgenstern_price | 11146 | 406 | 0 | **5** | 395 | **0** | +0.0001 % |
| 007 | spencer | 67190 | 88 | 80 | **5** | 1 | **2** | +0.0000 % |
| 007 | gle_morgenstern_price | 68914 | 30 | 30 | **0** | 0 | **0** | +0.0000 % |
| 009 | spencer | 68776 | 119 | 112 | **7** | 0 | **0** | +0.0000 % |
| 009 | gle_morgenstern_price | 67560 | 98 | 96 | **2** | 0 | **0** | +0.0000 % |
| 014 | spencer | 45608 | 1063 | 21 | **0** | 379 | **0** | +0.0000 % |
| 014 | gle_morgenstern_price | 43454 | 1287 | 4 | **10** | 386 | **0** | +0.0000 % |
| 015 | spencer | 87344 | 2173 | 43 | **0** | 357 | **0** | +0.0000 % |
| 015 | gle_morgenstern_price | 86518 | 3141 | 42 | **55** | 303 | **0** | +0.0001 % |
| 016 | spencer | 46712 | 1012 | 33 | **2** | 365 | **0** | +0.0000 % |
| 017 | spencer | 75884 | 10 | 10 | **0** | 0 | **0** | +0.0000 % |
| 018 | spencer | 78296 | 0 | 0 | **0** | 0 | **0** | +0.0000 % |
| 019 | spencer | 85976 | 0 | 0 | **0** | 0 | **0** | +0.0000 % |
| 047 | spencer | 46244 | 2149 | 164 | **230** | 3 | **3** | no aplica (superficie dada) |
| 051 | spencer | 29422 | 173 | 20 | **4** | 148 | **1** | +0.0000 % |
| 051 | gle_morgenstern_price | 27186 | 158 | 1 | **0** | 157 | **0** | +0.0003 % |
| 068 | spencer | 42216 | 2249 | 6 | **5** | 389 | **0** | +0.0000 % |
| 068 | gle_morgenstern_price | 36884 | 2373 | 9 | **2** | 389 | **0** | +0.0000 % |
| 080 | spencer | 36958 | 852 | 55 | **4** | 340 | **1** | +0.0000 % |
| 080 | gle_morgenstern_price | 32852 | 967 | 2 | **4** | 394 | **0** | +0.0000 % |
| 103 | spencer | 203520 | 31 | 2 | **8** | 21 | **0** | +0.0000 % |
| 104 | spencer | 239944 | 1 | 1 | **0** | 0 | **0** | +0.0455 % |
| 109 | spencer | 4394 | 13 | 8 | **0** | 5 | **0** | +0.0000 % |
| 109 | gle_morgenstern_price | 4456 | 39 | 17 | **10** | 11 | **1** | +0.0000 % |
| 075 | spencer | 64192 | 1585 | 4 | **0** | 396 | **0** | +0.0000 % |
| 075 | gle_morgenstern_price | 61706 | 1601 | 0 | **2** | 398 | **0** | +0.0000 % |
| 076 | spencer | 64274 | 37 | 29 | **4** | 3 | **1** | +0.0000 % |
| 076 | gle_morgenstern_price | 59114 | 6 | 0 | **1** | 5 | **0** | +0.0000 % |
| 059 | spencer | 11654 | 80 | 43 | **12** | 25 | **0** | +0.0001 % |
| 071 | spencer | 68562 | 222 | 72 | **11** | 138 | **1** | +0.0000 % |
| 071 | gle_morgenstern_price | 60898 | 180 | 3 | **4** | 173 | **0** | +0.0000 % |
| 057 | spencer | 84340 | 0 | 0 | **0** | 0 | **0** | +0.0000 % |
| 087 | spencer | 476016 | 11462 | 400 | **0** | 0 | **0** | +0.1208 % |
| 087 | gle_morgenstern_price | 493384 | 26568 | 172 | **227** | 0 | **1** | +0.0000 % |

## El punto ciego que este censo NO hereda

El contador `esperan_mas_de_20` de `criterio_rama_d145.py` filtra sobre ramas ACEPTADAS, asi que por construccion no puede ver una rama cortada por estancamiento. No se reutiliza: las cortadas se cuentan aqui a mano.

## Controles y limite

- **(A)** la llamada topada tiene que reproducir `fos` bit a bit y `passes`; 0 ramas descartadas por no hacerlo.
- **(B)** reproduccion de la fila: 2 descuadradas: 104 spencer (+0.0455 %), 087 spencer (+0.1208 %).
- **Limite**: cota inferior. Muestra de hasta 400 centros mas el 010, tope de tiempo por coste creciente, y tope de 400 ramas reconstruidas por fila (alcanzado en 15 filas).

## Saltadas

- 049 - — ninguna fila con metodo de lambda
- 050 - — ninguna fila con metodo de lambda
- 008 - — ninguna fila con metodo de lambda
- 021 - — ninguna fila con metodo de lambda
- 022 - — ninguna fila con metodo de lambda
- 025 - — ninguna fila con metodo de lambda
- 026 - — ninguna fila con metodo de lambda
- 028 - — ninguna fila con metodo de lambda
- 029 - — ninguna fila con metodo de lambda
- 040 - — ninguna fila con metodo de lambda
- 041 - — ninguna fila con metodo de lambda
- 048 - — ninguna fila con metodo de lambda
- 053 - — ninguna fila con metodo de lambda
- 064 - — ninguna fila con metodo de lambda
- 065 - — ninguna fila con metodo de lambda
- 066 - — ninguna fila con metodo de lambda
- 067 - — ninguna fila con metodo de lambda
- 069 - — ninguna fila con metodo de lambda
- 095 - — ninguna fila con metodo de lambda
- 096 - — ninguna fila con metodo de lambda
- 098 - — ninguna fila con metodo de lambda
- 102 - — ninguna fila con metodo de lambda
- 111 - — ninguna fila con metodo de lambda
- 097 - — ninguna fila con metodo de lambda

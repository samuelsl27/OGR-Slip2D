# El suelo de la horquilla de lambda — censo D153 — OGR 0.1.184

Generado por `_tools/suelo_horquilla_d153.py`, que SOLO MIDE. Una busqueda ENTERA por fila, no la critica archivada: las superficies que no cierran lambda no se archivan.

## Denominador

| | |
|---|---|
| filas medidas | 32 |
| problemas | 20 |
| superficies evaluadas | 123710 |
| llamadas a `_inner_solve` | 1095840 |
| superficies que no cierran lambda | 25 |
| **horquillas que llegan al suelo** (cota superior de los disparos) | 15 |
| saltadas | 23 |
| **sin medir** (tope de tiempo, orden por coste) | 29 |

## Cuantas llegan al suelo, y por que no son «disparos»

**15** de las 123710 superficies evaluadas llegan al suelo del doble. Esa cuenta es una **cota superior** del numero de veces que la guarda corta: la guarda pide ademas que los DOS extremos de la horquilla superen la tolerancia, y de los dos `details` solo publica uno. El numero exacto sale de la tabla de A/B de abajo, donde un disparo es una superficie cuyo `iterations` cambia.

## Por fila

| problema | metodo | superficies | llamadas | no cierran | en el suelo | control |
|---|---|---|---|---|---|---|
| 027 | spencer | 771 | 5987 | 0 | **0** | +0.0001 % |
| 027 | gle_morgenstern_price | 771 | 6284 | 0 | **0** | +0.0001 % |
| 007 | spencer | 4925 | 38220 | 5 | **2** | +0.0000 % |
| 007 | gle_morgenstern_price | 4925 | 39139 | 0 | **0** | +0.0000 % |
| 009 | spencer | 4712 | 38611 | 7 | **4** | +0.0000 % |
| 009 | gle_morgenstern_price | 4712 | 38058 | 2 | **1** | +0.0000 % |
| 014 | spencer | 2753 | 24688 | 0 | **0** | +0.0000 % |
| 014 | gle_morgenstern_price | 2753 | 23652 | 0 | **0** | +0.0000 % |
| 015 | spencer | 3405 | 50587 | 0 | **0** | +0.0000 % |
| 015 | gle_morgenstern_price | 3405 | 50710 | 0 | **0** | +0.0001 % |
| 016 | spencer | 2819 | 25334 | 0 | **0** | +0.0000 % |
| 017 | spencer | 5051 | 42926 | 1 | **0** | +0.0000 % |
| 018 | spencer | 5023 | 44141 | 3 | **3** | +0.0000 % |
| 019 | spencer | 5008 | 47991 | 4 | **3** | +0.0000 % |
| 047 | spencer | 1604 | 26825 | 0 | **0** | no aplica (superficie dada) |
| 051 | spencer | 1716 | 16318 | 1 | **1** | +0.0000 % |
| 051 | gle_morgenstern_price | 1716 | 15239 | 0 | **0** | +0.0003 % |
| 068 | spencer | 1574 | 22441 | 0 | **0** | +0.0000 % |
| 068 | gle_morgenstern_price | 1574 | 20031 | 0 | **0** | +0.0000 % |
| 080 | spencer | 1782 | 19728 | 0 | **0** | +0.0000 % |
| 080 | gle_morgenstern_price | 1782 | 17805 | 0 | **0** | +0.0000 % |
| 103 | spencer | 16740 | 118461 | 0 | **0** | +0.5297 % |
| 104 | spencer | 15859 | 135819 | 0 | **0** | +0.0455 % |
| 109 | spencer | 187 | 2295 | 0 | **0** | +0.0000 % |
| 109 | gle_morgenstern_price | 187 | 2315 | 0 | **0** | +0.0000 % |
| 075 | spencer | 5801 | 37648 | 0 | **0** | +0.0000 % |
| 075 | gle_morgenstern_price | 5801 | 36405 | 0 | **0** | +0.0000 % |
| 076 | spencer | 4213 | 36242 | 0 | **0** | +0.0000 % |
| 076 | gle_morgenstern_price | 4213 | 33740 | 0 | **0** | +0.0000 % |
| 059 | spencer | 536 | 6699 | 1 | **0** | +0.0001 % |
| 071 | spencer | 3696 | 37536 | 1 | **1** | +0.0000 % |
| 071 | gle_morgenstern_price | 3696 | 33965 | 0 | **0** | +0.0000 % |

## Control: filas cuyo factor critico no cuadra con lo archivado

Sin esta tabla, un cero se leeria como una afirmacion sobre filas que nadie comprobo que fueran las mismas.

Antes de leerlas como defecto, mirar QUE BUSQUEDA declara el modelo: una busqueda ESTOCASTICA no reproduce su propio minimo entre dos corridas, asi que un desvio pequeno ahi es lo esperado y no un descuadre. Ninguna fila descuadrada aporta superficies al recuento del suelo, de modo que el numero de disparos no depende de ellas.

* 103 spencer (+0.5297 %)
* 104 spencer (+0.0455 %)

## Saltadas

| problema | metodo | motivo |
|---|---|---|
| 049 | - | ninguna fila con metodo de lambda |
| 050 | - | ninguna fila con metodo de lambda |
| 008 | - | ninguna fila con metodo de lambda |
| 021 | - | ninguna fila con metodo de lambda |
| 022 | - | ninguna fila con metodo de lambda |
| 025 | - | ninguna fila con metodo de lambda |
| 026 | - | ninguna fila con metodo de lambda |
| 028 | - | ninguna fila con metodo de lambda |
| 029 | - | ninguna fila con metodo de lambda |
| 040 | - | ninguna fila con metodo de lambda |
| 041 | - | ninguna fila con metodo de lambda |
| 048 | - | ninguna fila con metodo de lambda |
| 053 | - | ninguna fila con metodo de lambda |
| 064 | - | ninguna fila con metodo de lambda |
| 065 | - | ninguna fila con metodo de lambda |
| 066 | - | ninguna fila con metodo de lambda |
| 067 | - | ninguna fila con metodo de lambda |
| 069 | - | ninguna fila con metodo de lambda |
| 095 | - | ninguna fila con metodo de lambda |
| 096 | - | ninguna fila con metodo de lambda |
| 098 | - | ninguna fila con metodo de lambda |
| 102 | - | ninguna fila con metodo de lambda |
| 111 | - | ninguna fila con metodo de lambda |

## A/B donde la guarda dispara

| problema | metodo | llamadas sin | con | ahorro | fos movidos | iterations | mensajes | claves de `details` |
|---|---|---|---|---|---|---|---|---|
| 007 | spencer | 38227 | 38220 | 7 | **0** | 2 | 2 | NINGUNA |
| 009 | spencer | 38620 | 38611 | 9 | **0** | 3 | 3 | NINGUNA |
| 009 | gle_morgenstern_price | 38059 | 38058 | 1 | **0** | 0 | 0 | NINGUNA |
| 018 | spencer | 44151 | 44141 | 10 | **0** | 3 | 3 | NINGUNA |
| 019 | spencer | 48000 | 47991 | 9 | **0** | 3 | 3 | NINGUNA |
| 051 | spencer | 16319 | 16318 | 1 | **0** | 0 | 0 | NINGUNA |
| 071 | spencer | 37541 | 37536 | 5 | **0** | 1 | 1 | NINGUNA |


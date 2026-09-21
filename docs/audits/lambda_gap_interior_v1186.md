# Nodos de lambda perdidos en el interior — censo D157 — OGR 0.1.186

Generado por `_tools/hueco_interior_d157.py`, que SOLO MIDE. Una busqueda ENTERA por fila, no la critica archivada: las superficies que no horquillan no se archivan, y son justo las que llegan a `refine_lambda_gap`.

## El embudo, que es el denominador

| | |
|---|---|
| filas medidas | 35 |
| problemas | 22 |
| superficies evaluadas | 164936 |
| superficies que no cierran lambda | 25 |
| **superficies que LLEGAN a `refine_lambda_gap`** | **23945** |
| de esas, con al menos un hueco INTERIOR | **1** |
| huecos interiores | 1 |
| de ellos, con `g` del mismo signo a los dos lados | 1 |
| nodos perdidos interiores | 1 |
| nodos perdidos de borde (lo que la funcion SI mira) | 214788 |
| **superficies donde la sonda encuentra un cambio de signo dentro** | **0** |
| sondeos gastados | 0 |
| saltadas | 24 |
| **sin medir** (tope de tiempo, orden por coste) | 26 |

Sin medir, NOMBRADOS para que la corrida se pueda reanudar: 088 089 090 091 092 093 094 045 101 086 001 002 003 004 006 012 013 024 030 036 038 074 082 083 084 010.

## Lo que la ficha preguntaba, y lo que se puede contestar

La ficha pide «en cuantas de esas el `g` de las muestras a los dos lados del hueco comparte signo». La respuesta es **1 de 1**, y es una identidad y no un hallazgo: `refine_lambda_gap` solo se llama cuando `_first_bracket` devolvio None, o sea cuando NINGUN par consecutivo de muestras cambia de signo. Se mide igualmente porque un numero deducido y no comprobado es el que se queda mal cuando el codigo cambia.

## Las filas con hueco interior, una por una

- **109 spencer**: 187 superficies, 48 llegan al refinado, 1 hueco(s) interior(es), 1 nodo(s), 0 sondeos.

**Y CERO SONDEOS NO ES UN FALLO DE LA SONDA, es la prueba de tendencia que la ficha prohibe tocar.** `refine_lambda_gap` solo sondea cuando `abs(borde[1]) < abs(dentro[1])`, o sea cuando `|g|` decrece HACIA el hueco, y `dentro` es la muestra viva que sigue al borde por el lado contrario. Con menos de TRES muestras vivas no existe ese `dentro` por ningun lado y la prueba no tiene entrada, asi que la extension que D157 pide seria inerte ahi aunque se escribiera. El control (E) de abajo ensena que el detector si ve un hueco cuando lo hay.

El «329 filas de 340» de la ficha esta contado sobre criticas archivadas, que por definicion horquillaron: ninguna de ellas ejecuta una instruccion de la funcion que el arreglo tocaria.

## Por fila

| problema | metodo | superficies | no cierran | llegan | con hueco interior | cruces | control |
|---|---|---|---|---|---|---|---|
| 027 | spencer | 771 | 0 | 12 | **0** | 0 | +0.0001 % |
| 027 | gle_morgenstern_price | 771 | 0 | 10 | **0** | 0 | +0.0001 % |
| 007 | spencer | 4925 | 5 | 271 | **0** | 0 | +0.0000 % |
| 007 | gle_morgenstern_price | 4925 | 0 | 204 | **0** | 0 | +0.0000 % |
| 009 | spencer | 4712 | 7 | 484 | **0** | 0 | +0.0000 % |
| 009 | gle_morgenstern_price | 4712 | 2 | 431 | **0** | 0 | +0.0000 % |
| 014 | spencer | 2753 | 0 | 149 | **0** | 0 | +0.0000 % |
| 014 | gle_morgenstern_price | 2753 | 0 | 103 | **0** | 0 | +0.0000 % |
| 015 | spencer | 3405 | 0 | 1323 | **0** | 0 | +0.0000 % |
| 015 | gle_morgenstern_price | 3405 | 0 | 1295 | **0** | 0 | +0.0001 % |
| 016 | spencer | 2819 | 0 | 222 | **0** | 0 | +0.0000 % |
| 017 | spencer | 5051 | 1 | 129 | **0** | 0 | +0.0000 % |
| 018 | spencer | 5023 | 3 | 83 | **0** | 0 | +0.0000 % |
| 019 | spencer | 5008 | 4 | 321 | **0** | 0 | +0.0000 % |
| 047 | spencer | 1604 | 0 | 797 | **0** | 0 | no aplica (superficie dada) |
| 051 | spencer | 1716 | 1 | 199 | **0** | 0 | +0.0000 % |
| 051 | gle_morgenstern_price | 1716 | 0 | 92 | **0** | 0 | +0.0003 % |
| 068 | spencer | 1574 | 0 | 765 | **0** | 0 | +0.0000 % |
| 068 | gle_morgenstern_price | 1574 | 0 | 609 | **0** | 0 | +0.0000 % |
| 080 | spencer | 1782 | 0 | 420 | **0** | 0 | +0.0000 % |
| 080 | gle_morgenstern_price | 1782 | 0 | 225 | **0** | 0 | +0.0000 % |
| 103 | spencer | 16740 | 0 | 52 | **0** | 0 | +0.0000 % |
| 104 | spencer | 15859 | 0 | 31 | **0** | 0 | +0.0455 % |
| 109 | spencer | 187 | 0 | 48 | **1** | 0 | +0.0000 % |
| 109 | gle_morgenstern_price | 187 | 0 | 49 | **0** | 0 | +0.0000 % |
| 075 | spencer | 5801 | 0 | 24 | **0** | 0 | +0.0000 % |
| 075 | gle_morgenstern_price | 5801 | 0 | 4 | **0** | 0 | +0.0000 % |
| 076 | spencer | 4213 | 0 | 257 | **0** | 0 | +0.0000 % |
| 076 | gle_morgenstern_price | 4213 | 0 | 99 | **0** | 0 | +0.0000 % |
| 059 | spencer | 536 | 1 | 116 | **0** | 0 | +0.0001 % |
| 071 | spencer | 3696 | 1 | 590 | **0** | 0 | +0.0000 % |
| 071 | gle_morgenstern_price | 3696 | 0 | 194 | **0** | 0 | +0.0000 % |
| 057 | spencer | 5840 | 0 | 14 | **0** | 0 | +0.0000 % |
| 087 | spencer | 17693 | 0 | 7524 | **0** | 0 | +0.1208 % |
| 087 | gle_morgenstern_price | 17693 | 0 | 6799 | **0** | 0 | +0.0000 % |

## Controles

- **(A) Reproduccion**: 2 filas descuadradas: 104 spencer (+0.0455 %), 087 spencer (+0.1208 %).
- **(B) La re-enunciacion**: 0 desacuerdos entre `_par()` y `branches()`. Si no es cero, la sonda esta midiendo su propia copia.
- **(D) El denominador** es la tabla de arriba, con las sin medir nombradas.
- **(E) El detector detecta**: sobre un muestreo escrito a mano con dos nodos perdidos DENTRO del rango vivo y uno mas alla del ultimo, `_huecos` VE el hueco interior y separa el de borde. Sin este control, un cero de la tabla de arriba no distinguiria «no hay huecos interiores» de «el medidor no los ve», que es exactamente el defecto que D158 resulto tener.

## El limite, declarado

Es una COTA INFERIOR: muestra de rejillas de hasta 400 centros mas el 010, y tope de tiempo por coste creciente. Un cero aqui significa «cero en lo medido».

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

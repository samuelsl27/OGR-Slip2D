# Censo del borde de admisibilidad de lambda (D149) - OGR 0.1.182

Generado por `_tools/borde_admisible_d149.py`. SOLO MIDE.

Contesta el paso 1 de P-D149: cuantas filas del banco tienen lambdas rechazados por admisibilidad conviviendo con supervivientes de un SOLO signo, y en cuantas de ellas devolver los rechazados hace aparecer una horquilla que hoy nadie alcanza.

## Denominador - banco

| que | cuantas |
|---|---|
| problemas | 77 |
| filas | 340 |
| criticas | 232 |
| publicadas | 108 |
| descuadradas | 6 |
| medidas | 334 |
| saltados | 22 |
| sin rechazos | 310 |
| A | 3 |
| B ok | 1 |
| B sin horquilla | 20 |
| B sin cruce medible | 0 |
| B1 | 0 |
| B2 | 0 |
| filas con algun rechazo | 24 |
| filas en reserva | 48 |
| d156 discrepancias | 0 |

## Las dos familias

Escribiendo `lam_E` para donde cruza cero la suma de empujes interiores y `lam_g` para donde cruza cero `F_f - F_m`: con **lam_E < lam_g** la raiz es ADMISIBLE y `refine_lambda_gap` (v0.1.181, D148) sondea justo en ese intervalo y la alcanza; con **lam_g < lam_E** la raiz cae del lado inadmisible, el refinado sondea hacia `lam_E` -que esta PASADA la raiz- y no llega nadie.

**CERO filas de caso B1 o B2 en el banco.** Las 20 filas de `B_sin_horquilla` tienen la forma -lambdas rechazados, supervivientes de un solo signo- pero al devolver los rechazados no aparece ningun cambio de signo en rejilla ni en extension, de modo que el rescate REVIERTE en todas ellas y no puede mover un digito.

Solo **24** de las 334 filas medidas rechazan algun lambda, y todas ellas estan en estos problemas: 047, 060, 085, 087, 090, 092, 093, 094.

## D156 - la bandera de la salida de reserva

La salida de reserva deriva `admissible` de QUE PASADA produjo la muestra; la salida con horquilla lo deriva del ESTADO DEVUELTO. De las **48** filas que salen por reserva, **0** discrepan entre las dos reglas. Con cero, unificarlas seria un ajuste que no hace nada (regla 7), y por eso se reporta en vez de corregirse.

## Denominador - escalera de cunas (el control B)

Sin esta tabla, el cero de arriba se lee igual que el silencio de un medidor que solo conoce el arbol sano. Plano de 45 grados, ancla Pasiva, GLE, 50 dovelas, 1e-10; lo unico que cambia es la capacidad.

| cap kN/m | esperado | medido | lam_g | lam_E | vivos | admisibles |
|---|---|---|---|---|---|---|
| 120 | B1 | B1 | 0.189970 | 0.107787 | 10 | 7 |
| 122 | - | B2 | 0.226281 | 0.259352 | 10 | 6 |
| 125 | - | B2 | 0.275136 | 0.499066 | 10 | 5 |
| 128 | - | B2 | 0.318188 | 0.755157 | 10 | 4 |
| 131 | - | B2 | 0.356325 | 1.029585 | 10 | 2 |
| 134 | B2 | B2 | 0.390285 | 1.324606 | 10 | 2 |
| 137 | A | A | - | - | 10 | 1 |

**El clasificador DISCRIMINA: ve B2 donde esta y no lo ve donde no.**

## Control: filas cuyo re-calculo no cuadra con lo archivado

El censo re-evalua la superficie ARCHIVADA de cada fila, asi que el factor tiene que salir el mismo. Cuando no sale, la fila NO se cuenta como medida de nada y se publica aqui: la instantanea del banco no es homogenea y una fila escrita por otra version no mide este cambio.

| problema | archivo | metodo | archivado | re-calculado | dif % |
|---|---|---|---|---|---|
| 039 | resultados_no_circular_arcilla.json | spencer | 0.993957 | 1.0202148896002807 | 2.641753073853371 |
| 039 | resultados_no_circular_arcilla.json | gle_morgenstern_price | 1.01262 | 1.0334108413112726 | 2.053173086772186 |
| 081 | resultados_modelo_1_tol1e-06.json | spencer | 1.235635 | 1.2194975793793197 | 1.3060022272499852 |
| 081 | resultados_modelo_1_tol1e-06.json | gle_morgenstern_price | 1.235635 | 1.2265215227693902 | 0.7375541507491974 |
| 086 | resultados_no_circular.json | spencer | 1.586399 | 1.5866562987496613 | 0.016219043863580692 |
| 086 | resultados_no_circular.json | gle_morgenstern_price | 1.591289 | 1.5915671090829675 | 0.017476968857796923 |

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
| 100 | resultados.json | spencer | AttributeError: 'BBarDrawdownMethod' object has no attribute 'lambda_grid' |
| 100 | resultados.json | gle_morgenstern_price | AttributeError: 'BBarDrawdownMethod' object has no attribute 'lambda_grid' |
| 101 | resultados.json | spencer | AttributeError: 'BBarDrawdownMethod' object has no attribute 'lambda_grid' |
| 101 | resultados.json | gle_morgenstern_price | AttributeError: 'BBarDrawdownMethod' object has no attribute 'lambda_grid' |
| 103 | resultados_modelo_1.6.json | spencer | la superficie no define ninguna masa evaluable en este modelo |

## Alcance, dicho porque un cero sin su limite se lee como si no lo tuviera

Esto cubre las superficies ARCHIVADAS: la critica de cada fila y las publicadas. Una busqueda evalua miles, asi que **cero es cota inferior** sobre esa poblacion, igual que el «21 es COTA INFERIOR» de v0.1.179.


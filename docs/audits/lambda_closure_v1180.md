# Como sale el bucle de lambda — censo D146 — OGR 0.1.180

Medido por `_tools/cierre_lambda_d146.py`, que solo mide. La causa de cada salida que no cierra se lee de la TRAZA de lambdas que el motor resolvio, capturada en `_inner_solve`, no de una copia del bucle secante.

## Denominador

| que | cuantas |
|---|---|
| filas medidas | 344 |
| no cierran | 0 |
| problemas | 79 |
| criticas | 236 |
| publicadas | 108 |
| saltadas | 18 |
| descuadradas control | 8 |

### Reparto de razones

| razon | filas |
|---|---|
| `(cierra)` | 341 |
| `all_lambda_diverged` | 2 |
| `no_lambda_bracket` | 1 |

### NOT_CONVERGED, por causa

| causa | filas |
|---|---|
| horquilla colapsada | 0 |
| par invalido | 0 |
| g plana | 0 |
| presupuesto | 0 |

## El caso que la ficha nombra

No es una fila del banco: el banco corre el 059 con su soporte y a 1e-4, y la ficha lo mide sin soporte y a 5e-5. Ademas lo contamina D147, porque el radio publicado esta redondeado y la masa sale fusionada.

| que | valor |
|---|---|
| `fos` | 0.5592600533686025 |
| `converged` | True |
| `iterations` | 8 |
| `reason` | `` |
| causa | - |
| lambda | 0.5508698587009847 |

## Filas en que el bucle de lambda NO cierra

Ninguna. El censo recorrio 344 filas de 79 problemas y **ni una sola** tomo esa salida.

## Las otras corridas de este censo

Un censo que solo sabe contestar «cero» no distingue un motor arreglado de un medidor roto, asi que las tres corridas van juntas. `sin cambio` apaga los dos interruptores de D145, que reproduce el motor de 0.1.178 instruccion por instruccion; la tolerancia forzada contesta si esta salida es alcanzable del todo, porque una aceptacion prematura se DESHACE al apretar la tolerancia y una discontinuidad de verdad no.

| corrida | filas | no cierran | cuales | por causa |
|---|---|---|---|---|
| motor enviado | 344 | 0 | - | - |
| sin cambio (motor 0.1.178) | 344 | 1 | 027 spencer | horquilla colapsada 1 |
| motor enviado, tolerancia forzada 1e-08 | 344 | 0 | - | - |

## Control: filas cuyo re-calculo no cuadra con lo archivado

El censo re-evalua la superficie ARCHIVADA de cada fila, asi que el factor tiene que salir el mismo. Cuando no sale, la fila NO se cuenta como medida de nada y se publica aqui: la instantanea del banco no es homogenea -sus archivos se reparten entre siete versiones de OGR- y una fila escrita por otra version no mide este cambio. Sin esta tabla, «cero filas no cierran» se leeria como una afirmacion sobre 344 filas que nadie comprobo que fueran las mismas.

| problema | archivo | metodo | archivado | aqui | desvio |
|---|---|---|---|---|---|
| 039 | resultados_no_circular_arcilla.json | spencer | 0.993957 | 1.020215 | +2.6418 % |
| 039 | resultados_no_circular_arcilla.json | gle_morgenstern_price | 1.012620 | 1.033411 | +2.0532 % |
| 047 | resultados.json | spencer | 0.849792 | 0.860685 | +1.2819 % |
| 081 | resultados_modelo_1_tol1e-06.json | spencer | 1.235635 | 1.219498 | +1.3060 % |
| 081 | resultados_modelo_1_tol1e-06.json | gle_morgenstern_price | 1.235635 | 1.226522 | +0.7376 % |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | 2.250695 | 2.238695 | +0.5331 % |
| 086 | resultados_no_circular.json | spencer | 1.586399 | 1.586656 | +0.0162 % |
| 086 | resultados_no_circular.json | gle_morgenstern_price | 1.591289 | 1.591567 | +0.0175 % |

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

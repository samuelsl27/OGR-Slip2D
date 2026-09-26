# Censo de elegibilidad de la critica archivada (D155) - OGR 0.1.208

Generado por `_tools/elegibilidad_critica_d155.py`. SOLO MIDE.

Contesta lo que P-D155 queria preguntar: no cuantas filas cambiaron de critica entre dos instantaneas —eso es imposible de medir y sale abajo con numero propio— sino **cuantas criticas archivadas dejaria de admitir el motor de hoy**, que es lo que mueve el minimo que la comparativa publica. Fuente: el banco vivo.

`SearchResult.critical` (`search.py:293-323`) elige el minimo de las ADMISIBLES y solo cae al conjunto entero cuando no queda ninguna (`pool = ok or valid`). Una fila se mueve, por tanto, en cuanto su incumbente pierde la bandera, **sin que ningun factor se haya movido de forma apreciable**.

## Denominador

| que | cuantas |
|---|---|
| problemas | 64 |
| filas | 237 |
| medidas | 230 |
| descuadradas | 7 |
| saltados | 7 |
| circular medidas | 182 |
| circular vuelcan | 0 |
| circular al borde | 14 |
| circular en reserva | 33 |
| circular inadmisibles hoy | 1 |
| no circular medidas | 48 |
| no circular vuelcan | 0 |
| no circular al borde | 0 |
| no circular en reserva | 9 |
| no circular inadmisibles hoy | 0 |
| vuelcan | 0 |
| al borde | 14 |
| sin margen | 0 |

## Por que el censo que pedia la ficha no se puede correr

Version que escribio cada archivo de resultados del banco:

| familia | version_ogr | archivos |
|---|---|---|
| circular | (sin anotar) | 2 |
| circular | 0.1.160 | 24 |
| circular | 0.1.163 | 2 |
| circular | 0.1.173 | 61 |
| circular | 0.1.178 | 17 |
| circular | 0.1.179 | 27 |
| circular | 0.1.181 | 10 |
| circular | 0.1.187 | 13 |
| circular | 0.1.188 | 21 |
| circular | 0.1.193 | 5 |
| circular | 0.1.202 | 11 |
| circular | 0.1.97 | 1 |
| no_circular | 0.1.147 | 1 |
| no_circular | 0.1.185 | 32 |
| no_circular | 0.1.187 | 4 |
| no_circular | 0.1.190 | 1 |

De los 38 archivos no circulares, **38 no los escribio la version instalada** (32 de 0.1.185, 4 de 0.1.187, 1 de 0.1.190, 1 de 0.1.147). Un archivo que no se ha vuelto a escribir no puede haber cambiado de critica entre dos instantaneas, asi que «cuantas filas cambiaron» leido por diff solo cuenta los archivos re-corridos entre ellas, y lo cuenta por aritmetica: por eso este censo re-evalua la critica archivada con el motor instalado en vez de comparar instantaneas.

## Las filas cuya critica archivada ya no seria elegible

| problema | archivo | metodo | familia | version | fos arch. | fos hoy | deriva % | adm hoy | margen | salida |
|---|---|---|---|---|---|---|---|---|---|---|
| - | - | - | - | - | - | - | - | - | - | - |

### Atribucion, un interruptor cada vez

Cual de los interruptores de `interslice.py`, EL SOLO apagado, devuelve la bandera a la fila que la perdio. Medido, no razonado. Cada fila se compara SOLO contra los estrenados DESPUES de la version que escribio su archivo: apagarlos todos reconstruiria un motor mas viejo que ese y descuadraria la fila por culpa del medidor.

| interruptor | version | filas que recupera |
|---|---|---|
| `BRANCH_RESCUE` | 0.1.176 | 0 |
| `BRANCH_PAIR_TIGHTEN` | 0.1.179 | 0 |
| `BRANCH_PAIR_SETTLE` | 0.1.179 | 0 |
| `BRANCH_CYCLE_RESCUE` | 0.1.181 | 0 |
| `LAMBDA_GAP_REFINE` | 0.1.181 | 0 |
| `LAMBDA_EDGE_RECOVERY` | 0.1.182 | 0 |
| `BRANCH_PLANAR_FORCE` | 0.1.183 | 0 |
| `LAMBDA_BRACKET_FLOOR_CUT` | 0.1.184 | 0 |
| `THRUST_FLAG_FROM_STATE` | 0.1.185 | 0 |
| `LAMBDA_STATE_CACHE` | 0.1.186 | 0 |
| `BRANCH_PARTNER_RETRY` | 0.1.193 | 0 |
| `slicer.CRACK_WALL_ON_LINE` | 0.1.208 | 0 |

## Las que volcaran despues: el margen del criterio de empuje

`thrust_is_admissible` compara `sum(E_interior)` con cero, y el margen es esa suma dividida por `sum(|E_interior|)`: +1 con todas las caras en compresion, -1 con todas en traccion, y cerca de cero cuando el veredicto esta a punto de volcar. **14 filas medidas tienen |margen| < 0.05.** En el 085 ese numero paso de +0,044 a -0,627 con un cambio del 0,10 % en el factor.

| problema | archivo | metodo | margen | adm hoy | salida | inadm. archivadas |
|---|---|---|---|---|---|---|
| 093 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | 0.000112 | True | reserva | 5289 |
| 094 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | 0.000525 | True | reserva | 6766 |
| 087 | resultados.json | gle_morgenstern_price | 0.000613 | True | reserva | 6361 |
| 087 | resultados_modelo_sin_conexion.json | gle_morgenstern_price | 0.000613 | True | reserva | 6852 |
| 094 | resultados.json | gle_morgenstern_price | 0.000721 | True | reserva | 6269 |
| 090 | resultados.json | spencer | 0.010487 | True | reserva | 5657 |
| 090 | resultados_modelo_sin_conexion.json | spencer | 0.010487 | True | reserva | 6647 |
| 092 | resultados.json | spencer | 0.012323 | True | reserva | 7826 |
| 094 | resultados_modelo_sin_conexion.json | spencer | 0.028053 | True | reserva | 6809 |
| 085 | resultados_modelo_pasivo.json | gle_morgenstern_price | 0.028236 | True | reserva | 782 |
| 093 | resultados.json | spencer | 0.029586 | True | reserva | 2003 |
| 093 | resultados_modelo_sin_conexion.json | spencer | 0.029586 | True | reserva | 4592 |
| 087 | resultados_modelo_sin_conexion.json | spencer | 0.038416 | True | reserva | 7050 |
| 085 | resultados_modelo_activo.json | spencer | 0.046270 | True | reserva | 569 |

### Descuadradas - no cuentan como medida de nada

El control A'' es que el factor con los interruptores POSTERIORES a la version del archivo apagados reproduzca el archivado dentro de 0.01 %. El control heredado de D148 —reproducirlo tal como se envia— habria tirado justo las filas que este censo busca, cuya deriva real es del orden del 0,10 %.

| problema | archivo | metodo | version | fos arch. | fos sin interruptores | control % | misma masa |
|---|---|---|---|---|---|---|---|
| 039 | resultados_no_circular_arcilla.json | spencer | 0.1.185 | 0.993957 | 1.020215 | 2.6418 | True |
| 039 | resultados_no_circular_arcilla.json | gle_morgenstern_price | 0.1.185 | 1.012620 | 1.033411 | 2.0532 | True |
| 081 | resultados_modelo_1_tol1e-06.json | spencer | 0.1.97 | 1.235635 | 1.219498 | 1.3060 | True |
| 081 | resultados_modelo_1_tol1e-06.json | gle_morgenstern_price | 0.1.97 | 1.235635 | 1.226522 | 0.7376 | True |
| 085 | resultados_no_circular_pasivo.json | spencer | 0.1.187 | 2.071732 | 2.047170 | 1.1856 | True |
| 086 | resultados_no_circular.json | spencer | 0.1.185 | 1.586399 | 1.586656 | 0.0162 | True |
| 086 | resultados_no_circular.json | gle_morgenstern_price | 0.1.185 | 1.591289 | 1.591567 | 0.0175 | True |

### Saltadas

| problema | archivo | metodo | motivo |
|---|---|---|---|
| 045 | resultados.json | spencer | la superficie no define ninguna masa evaluable en este modelo |
| 045 | resultados_modelo_mc.json | spencer | la superficie no define ninguna masa evaluable en este modelo |
| 045 | resultados_modelo_mc_iter.json | spencer | la superficie no define ninguna masa evaluable en este modelo |
| 057 | resultados_modelo_compuesto.json | spencer | la superficie no define ninguna masa evaluable en este modelo |
| 079 | resultados_no_circular_2.json | spencer | la superficie no define ninguna masa evaluable en este modelo |
| 079 | resultados_no_circular_2.json | gle_morgenstern_price | la superficie no define ninguna masa evaluable en este modelo |
| 085 | resultados_no_circular_pasivo.json | gle_morgenstern_price | la superficie no define ninguna masa evaluable en este modelo |

## Contra la instantanea `0.1.180`

El censo de arriba mide el banco VIVO, cuyas criticas ya escribio un motor reciente, y ahi un vuelco reciente no se puede ver. El vuelco solo aparece sobre la critica que archivo la instantanea ANTERIOR, y eso es esta tabla (`censo_0.1.208_desde0.1.180.json`).  **3 de 229 filas medidas.**

| problema | archivo | metodo | familia | version | fos arch. | fos hoy | deriva % | margen hoy | quien la recupera |
|---|---|---|---|---|---|---|---|---|---|
| 085 | resultados_no_circular_activo.json | spencer | no_circular | 0.1.178 | 2.066678 | 2.071581 | 0.237 | -0.29296 | `BRANCH_PAIR_TIGHTEN` |
| 085 | resultados_no_circular_activo.json | gle_morgenstern_price | no_circular | 0.1.178 | 2.250695 | 2.238695 | 0.533 | -0.29157 | nadie |
| 085 | resultados_no_circular_pasivo.json | spencer | no_circular | 0.1.178 | 1.512356 | 1.513872 | 0.100 | -0.62694 | `BRANCH_PAIR_TIGHTEN` |

## Contra la instantanea `0.1.207`

El censo de arriba mide el banco VIVO, cuyas criticas ya escribio un motor reciente, y ahi un vuelco reciente no se puede ver. El vuelco solo aparece sobre la critica que archivo la instantanea ANTERIOR, y eso es esta tabla (`censo_0.1.208_desde0.1.207.json`).  **0 de 230 filas medidas.**

| problema | archivo | metodo | familia | version | fos arch. | fos hoy | deriva % | margen hoy | quien la recupera |
|---|---|---|---|---|---|---|---|---|---|
| - | - | - | - | - | - | - | - | - | - |

## El limite de este censo, dicho antes de que nadie lo lea mal

Mide LA CRITICA ARCHIVADA, que es 1 de las 5000 superficies que la busqueda evaluo. Que la critica de una fila no vuelque no garantiza que la fila no se mueva: basta con que dos casi-empates se reordenen. **Es una cota inferior**, igual que el «21 es COTA INFERIOR» de v0.1.179.


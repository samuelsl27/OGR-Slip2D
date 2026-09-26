# El detector de estancamiento mira el PAR — A/B de D158 — OGR 0.1.209

Generado por `_tools/estancamiento_d158.py --ab`, que SOLO MIDE. Por fila, dos busquedas ENTERAS en el mismo proceso: `BRANCH_STALL_PAIR` encendido y apagado. Motor medido: `C:\Samuel\OpenGeoRock_Slip2d\OGR-Slip2D`.

## Denominador

| | |
|---|---|
| filas medidas | 73 |
| problemas | 30 |
| ramas, encendido / apagado | 18734900 / 18745444 |
| estancadas, encendido / apagado | 461314 / 666344 |
| aceptadas, encendido / apagado | 13327575 / 13329626 |
| saltadas | 0 |
| sin medir | 0 |

## Neutralidad, ejecutada rama a rama

Dentro de la corrida encendida, toda rama de mas de `STALL_PATIENCE` pasadas o sin estado se resolvio otra vez con el interruptor apagado. Las que ahi NO se estancaban tienen que salir identicas bit a bit (`fos`, `passes`, `converged`, `boundary_x`).

| comprobadas | rotas | estancadas en la ultima pasada | sin verificar |
|---|---|---|---|
| 3657568 | **0** | 48 | 0 |

**El estancamiento en la ultima pasada no es una rotura.** El detector de 0.1.208 puede cortar justo en la pasada del presupuesto; entonces `GLESystem.branches` la cuenta como PRESUPUESTO (`passes == max`), pero el corte ocurre ANTES de actualizar F y el detector nuevo completa esa pasada: mismas pasadas, F distinto en una actualizacion, ninguno converge y el lambda se pierde en los dos lados. Es una rama convertida. Los trabajos lanzados antes de reconocerlo lo contaban como rotura, y se reclasifica aqui ejemplo a ejemplo.

Control de determinismo (una segunda corrida encendida en la primera fila de cada problema, critica y pasadas identicas): **30 de 30**.

## Lo que cuesta y lo que compra

Pasadas de rama sumadas sobre la busqueda entera. Las de una rama que vuelve `None` no las publica el motor: las de una rama CONVERTIDA se buscan por biseccion y se suman al lado encendido; las de una que no lo es son las mismas en los dos lados y se cancelan.

| | |
|---|---|
| pasadas, apagado | 663045415 |
| pasadas, encendido | 741550931 |
| **pasadas de mas** | **+78505516 (+11.84 %)** |
| ramas convertidas (se estancaban con el detector de 0.1.208) | 897366 |
| pasadas de mas de las convertidas | 62568550 |
| desenlace: converge | **259203** |
| desenlace: presupuesto | 176699 |
| desenlace: desborda | 20 |
| desenlace: estanca_mas_tarde | 461314 |
| desenlace: sin_estado | 130 |

**Respuestas compradas**: 259203 ramas que hoy convergen donde el detector de 0.1.208 las cortaba, a cambio de 62568550 pasadas de mas en las convertidas. La cota superior de 0.1.186 (`patience` enorme, solo cubos ii y iv) era 65 027 pasadas por 434 respuestas.

## Filas cuyo minimo publicado se mueve

| fila | fos apagado | fos encendido | delta % | adm apagado -> encendido | margen apagado -> encendido | lambda apagado -> encendido |
|---|---|---|---|---|---|---|
| - | - | - | - | - | - | - |

Filas cuya critica cambia de bandera de admisibilidad: **0**.

## D155: que moveria una banda muerta (primer orden)

De las MISMAS evaluaciones de la corrida encendida: cuantas filas cambiarian de critica si una superficie que la criba dejo pasar y el metodo rechazo SOLO por el signo del empuje contara como admisible con `margen > -eps`. **Es de primer orden**: la banda actua aqui solo en la eleccion de la critica, no dentro de la busqueda de lambda, donde tambien cambiaria que lambdas sobreviven.

| eps | filas que se mueven | superficies en la banda | mayor bajada % |
|---|---|---|---|
| 0.001 | 0 | 86 | - |
| 0.01 | 3 | 977 | -1.217 |
| 0.05 | 12 | 6317 | -7.627 |

## Por fila

| fila | pasadas de mas | convertidas | converge | neutralidad rota | fos apagado | fos encendido |
|---|---|---|---|---|---|---|
| 007 resultados.json gle_morgenstern_price | +0 | 30 | 0 | 0 | 1.281475 | 1.281475 |
| 007 resultados.json spencer | +1412 | 88 | 2 | 0 | 1.290767 | 1.290767 |
| 009 resultados.json gle_morgenstern_price | +487 | 98 | 0 | 0 | 0.681053 | 0.681053 |
| 009 resultados.json spencer | +2281 | 119 | 0 | 0 | 0.707136 | 0.707136 |
| 014 resultados.json gle_morgenstern_price | +9746 | 1291 | 11 | 0 | 1.403030 | 1.403030 |
| 014 resultados.json spencer | +7387 | 1065 | 6 | 0 | 1.403971 | 1.403971 |
| 015 resultados.json gle_morgenstern_price | +73372 | 3199 | 272 | 0 | 0.420484 | 0.420484 |
| 015 resultados.json spencer | +33910 | 2509 | 3 | 0 | 0.422900 | 0.422900 |
| 016 resultados.json spencer | +10039 | 1028 | 9 | 0 | 1.117677 | 1.117677 |
| 017 resultados_no_circular.json spencer | +0 | 0 | 0 | 0 | 1.360425 | 1.360425 |
| 018 resultados_no_circular.json spencer | +0 | 0 | 0 | 0 | 1.064266 | 1.064266 |
| 019 resultados_no_circular.json spencer | +0 | 0 | 0 | 0 | 1.415285 | 1.415285 |
| 027 resultados.json gle_morgenstern_price | +0 | 401 | 0 | 0 | 0.242953 | 0.242953 |
| 027 resultados.json spencer | +0 | 361 | 0 | 0 | 0.314136 | 0.314136 |
| 047 resultados.json spencer | +314147 | 2886 | 725 | 0 | 1.251258 | 1.251258 |
| 051 resultados.json gle_morgenstern_price | +87 | 157 | 0 | 0 | 0.995552 | 0.995552 |
| 051 resultados.json spencer | +4 | 150 | 0 | 0 | 0.994107 | 0.994107 |
| 057 resultados.json spencer | +0 | 0 | 0 | 0 | 1.429380 | 1.429380 |
| 059 resultados.json spencer | +4504 | 112 | 14 | 0 | 0.565634 | 0.565634 |
| 068 resultados.json gle_morgenstern_price | +113457 | 2827 | 328 | 0 | 1.134726 | 1.134726 |
| 068 resultados.json spencer | +183829 | 2743 | 423 | 0 | 1.148638 | 1.148638 |
| 071 resultados.json gle_morgenstern_price | +1384 | 185 | 0 | 0 | 1.144118 | 1.144118 |
| 071 resultados.json spencer | +2849 | 173 | 0 | 0 | 1.144116 | 1.144116 |
| 075 resultados.json gle_morgenstern_price | +1890 | 1599 | 0 | 0 | 1.432856 | 1.432856 |
| 075 resultados.json spencer | +5228 | 1577 | 0 | 0 | 1.431095 | 1.431095 |
| 076 resultados.json gle_morgenstern_price | +103 | 15 | 0 | 0 | 1.082657 | 1.082657 |
| 076 resultados.json spencer | +432 | 17 | 0 | 0 | 1.083653 | 1.083653 |
| 080 resultados.json gle_morgenstern_price | +7279 | 1003 | 1 | 0 | 1.241536 | 1.241536 |
| 080 resultados.json spencer | +15665 | 834 | 0 | 0 | 1.253888 | 1.253888 |
| 085 resultados_modelo_activo.json gle_morgenstern_price | +461189 | 10250 | 1463 | 0 | 2.209183 | 2.209183 |
| 085 resultados_modelo_activo.json spencer | +771101 | 10323 | 1783 | 0 | 2.205786 | 2.205786 |
| 085 resultados_modelo_pasivo.json gle_morgenstern_price | +708715 | 11785 | 2163 | 0 | 1.854884 | 1.854884 |
| 085 resultados_modelo_pasivo.json spencer | +985720 | 11616 | 2201 | 0 | 2.040037 | 2.040037 |
| 085 resultados_no_circular_activo.json gle_morgenstern_price | +1211716 | 9528 | 2849 | 0 | 2.321325 | 2.321325 |
| 085 resultados_no_circular_activo.json spencer | +168014 | 3346 | 504 | 0 | 2.312511 | 2.312511 |
| 085 resultados_no_circular_pasivo.json gle_morgenstern_price | +1318746 | 8875 | 3780 | 0 | 1.725838 | 1.725838 |
| 085 resultados_no_circular_pasivo.json spencer | +92412 | 1564 | 286 | 0 | 2.071732 | 2.071732 |
| 087 resultados.json gle_morgenstern_price | +4523128 | 40675 | 15393 | 3 | 1.075576 | 1.075576 |
| 087 resultados.json spencer | +557312 | 15625 | 1863 | 0 | 1.073709 | 1.073709 |
| 087 resultados_modelo_sin_conexion.json gle_morgenstern_price | +4148664 | 37860 | 14084 | 2 | 1.075576 | 1.075576 |
| 087 resultados_modelo_sin_conexion.json spencer | +519110 | 14141 | 1695 | 0 | 1.068760 | 1.068760 |
| 088 resultados.json gle_morgenstern_price | +5565439 | 49234 | 19019 | 3 | 1.051042 | 1.051042 |
| 088 resultados.json spencer | +359256 | 18614 | 1055 | 0 | 1.051694 | 1.051694 |
| 088 resultados_modelo_sin_conexion.json gle_morgenstern_price | +4455598 | 41233 | 15344 | 0 | 1.044713 | 1.044713 |
| 088 resultados_modelo_sin_conexion.json spencer | +342185 | 17004 | 1041 | 0 | 1.045316 | 1.045316 |
| 089 resultados.json gle_morgenstern_price | +4027445 | 34519 | 13040 | 0 | 0.978331 | 0.978331 |
| 089 resultados.json spencer | +500507 | 13704 | 1673 | 0 | 0.978322 | 0.978322 |
| 089 resultados_modelo_sin_conexion.json gle_morgenstern_price | +3893697 | 34088 | 12681 | 3 | 0.977875 | 0.977875 |
| 089 resultados_modelo_sin_conexion.json spencer | +500230 | 13349 | 1617 | 0 | 0.977866 | 0.977866 |
| 090 resultados.json gle_morgenstern_price | +4052578 | 36835 | 14035 | 1 | 0.917879 | 0.917879 |
| 090 resultados.json spencer | +606644 | 14640 | 1873 | 0 | 0.896155 | 0.896155 |
| 090 resultados_modelo_sin_conexion.json gle_morgenstern_price | +4204060 | 37880 | 14626 | 0 | 0.917879 | 0.917879 |
| 090 resultados_modelo_sin_conexion.json spencer | +681801 | 14879 | 2107 | 0 | 0.896155 | 0.896155 |
| 091 resultados.json gle_morgenstern_price | +4522677 | 40671 | 15389 | 0 | 0.972551 | 0.972551 |
| 091 resultados.json spencer | +551961 | 15554 | 1843 | 0 | 0.972205 | 0.972205 |
| 091 resultados_modelo_sin_conexion.json gle_morgenstern_price | +4147096 | 37848 | 14082 | 0 | 0.972551 | 0.972551 |
| 091 resultados_modelo_sin_conexion.json spencer | +514148 | 14088 | 1677 | 0 | 0.972205 | 0.972205 |
| 092 resultados.json gle_morgenstern_price | +2979091 | 28468 | 10190 | 0 | 1.006545 | 1.006545 |
| 092 resultados.json spencer | +495360 | 11081 | 1430 | 0 | 0.998046 | 0.998046 |
| 092 resultados_modelo_sin_conexion.json gle_morgenstern_price | +2774543 | 24640 | 8935 | 0 | 0.998726 | 0.998726 |
| 092 resultados_modelo_sin_conexion.json spencer | +522935 | 9931 | 1480 | 0 | 0.998342 | 0.998342 |
| 093 resultados.json gle_morgenstern_price | +1953151 | 19104 | 6763 | 0 | 1.014632 | 1.014632 |
| 093 resultados.json spencer | +565692 | 10646 | 1830 | 0 | 0.989734 | 0.989734 |
| 093 resultados_modelo_sin_conexion.json gle_morgenstern_price | +3888388 | 36575 | 13545 | 0 | 0.998564 | 0.998564 |
| 093 resultados_modelo_sin_conexion.json spencer | +673142 | 14438 | 2010 | 0 | 0.989734 | 0.989734 |
| 094 resultados.json gle_morgenstern_price | +4420816 | 39884 | 14930 | 0 | 1.073757 | 1.073757 |
| 094 resultados.json spencer | +713066 | 17423 | 2338 | 0 | 1.072901 | 1.072901 |
| 094 resultados_modelo_sin_conexion.json gle_morgenstern_price | +3761254 | 35738 | 12940 | 0 | 1.104274 | 1.104274 |
| 094 resultados_modelo_sin_conexion.json spencer | +573616 | 15158 | 1841 | 0 | 1.062337 | 1.062337 |
| 103 resultados.json spencer | +2676 | 32 | 6 | 0 | 1.220941 | 1.220941 |
| 104 resultados.json spencer | +0 | 0 | 0 | 0 | 1.360608 | 1.360608 |
| 109 resultados.json gle_morgenstern_price | +1103 | 39 | 5 | 0 | 6.744289 | 6.744289 |
| 109 resultados.json spencer | +42 | 14 | 0 | 0 | 6.731184 | 6.731184 |

## Una correccion al censo de 0.1.186

En aquel censo el `paso` de F de una rama estancada valia **0.0 bit a bit siempre**: el estancamiento hace `break` antes de actualizar F, y la llamada topada en `passes - 1` termina con la actualizacion que produce ese mismo F. El cubo (iv) «F y X asentadas» solo pedia `d_x < tol`. La poblacion de 627 sigue siendo «empuje contrayendo o ya dentro de tolerancia»; lo que era falso es la etiqueta. Corregido en `_clasificar`: el paso es ahora F_{k+1} - F_k con el detector fuera.


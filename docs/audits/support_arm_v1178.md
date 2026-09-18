# D144 - el brazo del soporte en la rama de momentos (OGR 0.1.178)

Medido por `_tools/brazo_soporte_d144.py` del banco. SOLO MIDE.

## El problema 85, por forma cerrada y por el motor

Con `phi' = 0` la ecuacion de momentos es un cociente de dos sumas, asi que estas cuatro filas se PREDICEN sin ejecutar el solver y se contrastan despues contra el.

| escenario | circulo | cuerda | exacto | Bishop | Fellenius | publicado | err |
|---|---|---|---|---|---|---|---|
| 085 activo | 85.2 | 1.556171 | 1.569188 | 1.569188 | 1.569188 | 1.575 | -0.369 % |
| 085 pasivo | 85.3 | 1.325508 | 1.321350 | 1.321350 | 1.321350 | 1.324 | -0.200 % |
| 085 activo | 85.3 | 1.539349 | 1.528816 | 1.528816 | 1.528816 | - | - |
| 085 pasivo | 85.2 | 1.327025 | 1.331903 | 1.331903 | 1.331903 | - | - |

## El efecto, dovela a dovela

| circulo | dovela | cruce | cuerda | tangente | t cuerda | t exacto | corto | ley -da*tan(a-th) |
|---|---|---|---|---|---|---|---|---|
| 85.2 | 40 | (36.676, 20.000) | 50.8600 | 50.3024 | 5680.9516 | 5748.2061 | -1.1700 % | -1.1724 % |
| 85.3 | 41 | (36.885, 20.000) | 53.2633 | 53.7050 | 5383.2518 | 5326.7934 | +1.0599 % | +1.0497 % |

El signo del error CAMBIA entre los dos circulos publicados del mismo problema: en el 85.2 la cuerda va 0,558 grados por encima de la tangente y el termino sale corto, y en el 85.3 va 0,442 por debajo y sale largo. No es un sesgo que una malla mas fina pague en una direccion.

## A/B contra `Evaluaciones/0.1.177`, fila a fila

**1986 numeros comparados en 46 archivos, 319 movidos.** La columna `A` es la version con que se midio el lado izquierdo: la instantanea NO es una corrida homogenea, y sin esa columna los digitos que movieron 0.1.175 y 0.1.176 se imputarian a D144. Archivos con A/B limpio: **21**.

| problema | archivo | A | B | numeros | movidos | A/B |
|---|---|---|---|---|---|---|
| 030 | resultados.json | 0.1.173 | 0.1.178 | 17 | 5 | arrastra 0.1.173..0.1.176 |
| 031 | resultados.json | 0.1.173 | 0.1.178 | 11 | 0 | arrastra 0.1.173..0.1.176 |
| 047 | resultados.json | 0.1.162 | 0.1.162 | 65 | 0 | NO RE-CORRIDO |
| 047 | resultados_modelo_sin_bulones.json | 0.1.175 | 0.1.178 | 39 | 0 | arrastra 0.1.175..0.1.176 |
| 048 | resultados.json | 0.1.173 | 0.1.178 | 9 | 0 | arrastra 0.1.173..0.1.176 |
| 048 | resultados_modelo_sin_bulones.json | 0.1.173 | 0.1.178 | 9 | 0 | arrastra 0.1.173..0.1.176 |
| 048 | resultados_no_reproduce.json | 0.1.97 | 0.1.97 | 34 | 0 | NO RE-CORRIDO |
| 049 | resultados.json | 0.1.173 | 0.1.178 | 34 | 0 | arrastra 0.1.173..0.1.176 |
| 050 | resultados.json | 0.1.173 | 0.1.178 | 22 | 0 | arrastra 0.1.173..0.1.176 |
| 054 | resultados.json | 0.1.173 | 0.1.178 | 50 | 4 | arrastra 0.1.173..0.1.176 |
| 054 | resultados_modelo_sin_pilote.json | 0.1.173 | 0.1.178 | 50 | 2 | arrastra 0.1.173..0.1.176 |
| 059 | resultados.json | 0.1.176 | 0.1.178 | 60 | 14 | limpio |
| 059 | resultados_todos.json | 0.1.160 | 0.1.160 | 48 | 0 | NO RE-CORRIDO |
| 060 | resultados.json | 0.1.173 | 0.1.178 | 53 | 6 | arrastra 0.1.173..0.1.176 |
| 060 | resultados_todos.json | 0.1.160 | 0.1.160 | 24 | 0 | NO RE-CORRIDO |
| 085 | resultados_modelo_activo.json | 0.1.176 | 0.1.178 | 43 | 12 | limpio |
| 085 | resultados_modelo_pasivo.json | 0.1.176 | 0.1.178 | 43 | 22 | limpio |
| 085 | resultados_no_circular_activo.json | 0.1.176 | 0.1.178 | 150 | 3 | limpio |
| 085 | resultados_no_circular_pasivo.json | 0.1.176 | 0.1.178 | 137 | 3 | limpio |
| 085 | resultados_todos.json | 0.1.160 | 0.1.160 | 18 | 0 | NO RE-CORRIDO |
| 086 | resultados.json | 0.1.173 | 0.1.178 | 35 | 13 | arrastra 0.1.173..0.1.176 |
| 086 | resultados_no_circular.json | 0.1.173 | 0.1.173 | 158 | 0 | NO RE-CORRIDO |
| 086 | resultados_todos.json | 0.1.160 | 0.1.160 | 12 | 0 | NO RE-CORRIDO |
| 087 | resultados.json | 0.1.176 | 0.1.178 | 37 | 14 | limpio |
| 087 | resultados_modelo_sin_conexion.json | 0.1.176 | 0.1.178 | 37 | 14 | limpio |
| 088 | resultados.json | 0.1.176 | 0.1.178 | 35 | 14 | limpio |
| 088 | resultados_modelo_sin_conexion.json | 0.1.176 | 0.1.178 | 35 | 14 | limpio |
| 089 | resultados.json | 0.1.176 | 0.1.178 | 35 | 14 | limpio |
| 089 | resultados_modelo_sin_conexion.json | 0.1.176 | 0.1.178 | 35 | 14 | limpio |
| 090 | resultados.json | 0.1.176 | 0.1.178 | 38 | 15 | limpio |
| 090 | resultados_modelo_sin_conexion.json | 0.1.176 | 0.1.178 | 38 | 14 | limpio |
| 091 | resultados.json | 0.1.176 | 0.1.178 | 35 | 14 | limpio |
| 091 | resultados_modelo_sin_conexion.json | 0.1.176 | 0.1.178 | 35 | 14 | limpio |
| 092 | resultados.json | 0.1.176 | 0.1.178 | 35 | 14 | limpio |
| 092 | resultados_modelo_sin_conexion.json | 0.1.176 | 0.1.178 | 36 | 14 | limpio |
| 093 | resultados.json | 0.1.176 | 0.1.178 | 38 | 14 | limpio |
| 093 | resultados_modelo_sin_conexion.json | 0.1.176 | 0.1.178 | 38 | 21 | limpio |
| 094 | resultados.json | 0.1.176 | 0.1.178 | 37 | 14 | limpio |
| 094 | resultados_modelo_sin_conexion.json | 0.1.176 | 0.1.178 | 37 | 14 | limpio |
| 106 | resultados.json | 0.1.173 | 0.1.178 | 11 | 0 | arrastra 0.1.173..0.1.176 |
| 106 | resultados_modelo_D1D2.json | 0.1.173 | 0.1.178 | 11 | 0 | arrastra 0.1.173..0.1.176 |
| 106 | resultados_modelo_D1D3.json | 0.1.173 | 0.1.178 | 11 | 1 | arrastra 0.1.173..0.1.176 |
| 106 | resultados_modelo_D1D4.json | 0.1.173 | 0.1.178 | 11 | 1 | arrastra 0.1.173..0.1.176 |
| 106 | resultados_modelo_D1D6.json | 0.1.173 | 0.1.178 | 11 | 1 | arrastra 0.1.173..0.1.176 |
| 106 | resultados_todos.json | 0.1.163 | 0.1.163 | 36 | 0 | NO RE-CORRIDO |
| 111 | resultados.json | 0.1.163 | 0.1.163 | 193 | 0 | NO RE-CORRIDO |


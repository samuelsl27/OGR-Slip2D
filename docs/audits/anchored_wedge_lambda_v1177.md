# Las dos ramas de Spencer y GLE sobre la cuna anclada — OGR 0.1.177

Generado por `_tools/curva_cuna_d119.py` del banco de verificacion, que es
**solo de medida**: no escribe ningun `.ogr` ni ningun resultado, y este
archivo se regenera entero. Medido el 2026-09-18T08:21:48 con 50 dovelas,
tolerancia 1e-10 y `max_iterations` 400.

## Que se mide y por que

Ficha **D119**: con un ancla de 120 kN/m a 15 grados, Spencer y GLE no
encuentran raiz de lambda sobre el plano de 50 grados, y si sobre los de 35,
40 y 45. Que no haya horquilla esta medido desde 0.1.159; **por que** ese
plano y no los otros, no estaba escrito. Lo que la ficha pide para cerrarse es
tabular `F_f(lambda)` y `F_m(lambda)` en un rango ancho y con los dos signos,
para cada beta y con el ancla Activa, Pasiva y ausente, marcando donde cada
rama deja de converger.

La superficie es un PLANO y el modelo no es del banco: es la fixture de
`tests/test_interslice_budget_v1159.py` y `tests/test_janbu_wedge_v1142.py`,
cuatro vertices y un material. Sobre un plano la masa es una cuna rigida y su
factor de seguridad esta en **forma cerrada** (Coulomb 1776; el enunciado
moderno, con el soporte resuelto sobre la base, es Duncan y Wright 2005,
seccion 6), que es el anclaje externo contra el que se mide todo lo de abajo.

Cada lambda se resuelve con `system.states(lambda)` y **no** con
`branches(lambda)`: asi no se tocan los contadores del motor ni su filtro de
admisibilidad. `g` se escribe solo cuando las **dos** ramas convergieron, que
es la regla del propio motor; si no, la fila dice por que, con los mismos tres
motivos que `GLESystem.branches` distingue (empuje desbordado, presupuesto
agotado, estancamiento) mas `nula` cuando `solve_branch` no devuelve estado.

El sistema se construye como lo construye el **metodo**, con `sup` y `axis`.
El ayudante `_system()` del test v1159 lo construye con `sup=None`, de modo que
el refuerzo llega a la rama de fuerzas y no al cierre de momentos: medir por
ahi habria medido otro sistema.

## La respuesta, en una linea

**El ancla no destruye la raiz: la desplaza hasta un lambda donde la rama de
momentos ya no se puede resolver.** Alcanzada y medida en la celda Pasiva de
Spencer -raiz en lambda 1,31988, F = la forma cerrada a 8e-6-; en las otras
tres celdas de 50 grados con ancla el escape llega antes del cruce incluso con
la puerta mas temprana, y lo medido alli es que `g` sube hacia cero y que la
rama se pierde, no donde cruza. El detalle, celda a celda, en la seccion
«La raiz que se pierde».

## Resumen de las 16 celdas

`F_f` es exactamente constante en lambda sobre un plano -Sigma(X_{i+1} - X_i)
se telescopa y alfa no varia-, con ancla y sin ella, y coincide con la forma
cerrada; la columna `disp(F_f)` es la dispersion medida de esa constante y la
columna `err F_f` su error contra la cuna. `raiz` es el lambda donde `g`
cambia de signo **entre lambdas usables de serie**; `usable` es el tramo donde
las dos ramas convergen.


| metodo | beta | ancla | F_f | err F_f | disp(F_f) | raiz λ | usable | motor publica | err motor | reserva |
|---|---|---|---|---|---|---|---|---|---|---|
| spencer | 35 | sin ancla | 1.009342663 | -3.6e-11 | 1.4e-14 | 0.7002 | [-2.00, 2.00] | 1.009343 | -4.53e-11 | no |
| spencer | 35 | activa | 1.312709408 | -1.5e-11 | 2.5e-13 | 0.7122 | [-1.90, 2.30] | 1.312709 | -1.91e-11 | no |
| spencer | 35 | pasiva | 1.250414516 | -1.8e-11 | 1.6e-13 | 0.7146 | [-2.00, 2.60] | 1.250415 | -4.32e-11 | no |
| spencer | 40 | sin ancla | 0.901452199 | +4.7e-11 | 1.0e-14 | 0.8388 | [-2.00, 2.00] | 0.901452 | +5.93e-11 | no |
| spencer | 40 | activa | 1.288830844 | -2.7e-11 | 6.0e-13 | 0.8073 | [-1.70, 2.15] | 1.288831 | -3.70e-11 | no |
| spencer | 40 | pasiva | 1.217018877 | -2.1e-11 | 3.5e-13 | 0.8018 | [-1.95, 2.40] | 1.217019 | -3.54e-11 | no |
| spencer | 45 | sin ancla | 0.855128047 | +7.3e-11 | 1.9e-14 | 1.0000 | [-2.00, 2.05] | 0.855128 | +7.95e-11 | no |
| spencer | 45 | activa | 1.467930420 | -2.0e-11 | 5.9e-12 | 1.2861 | [-1.45, 1.75] | 1.467930 | -3.61e-11 | no |
| spencer | 45 | pasiva | 1.308737259 | -2.9e-11 | 2.4e-11 | - | [-1.45, 1.95] | 1.308152 | -4.47e-04 | si, residuo 0.001171 |
| spencer | 50 | sin ancla | 0.941982760 | +6.5e-11 | 7.4e-14 | 1.1916 | [-1.45, 2.00] | 0.941983 | +1.09e-10 | no |
| spencer | 50 | activa | 2.757457925 | -9.4e-13 | 1.6e-11 | - | [-0.70, 0.95] | 2.853339 | +3.48e-02 | si, residuo 0.1918 |
| spencer | 50 | pasiva | 1.748317883 | -1.9e-11 | 6.2e-12 | - | [-0.90, 1.25] | 1.765482 | +9.82e-03 | si, residuo 0.03433 |
| gle | 45 | pasiva | 1.308737259 | -2.9e-11 | 1.4e-12 | 0.1901 | [-2.00, 2.35] | 1.308768 | +2.35e-05 | si, residuo 6.144e-05 |
| gle | 50 | sin ancla | 0.941982760 | +6.5e-11 | 2.5e-14 | 1.4303 | [-2.00, 2.95] | 0.941983 | +6.65e-11 | no |
| gle | 50 | activa | 2.757457925 | +4.3e-13 | 2.2e-11 | - | [-1.10, 1.15] | 2.855670 | +3.56e-02 | si, residuo 0.1964 |
| gle | 50 | pasiva | 1.748317883 | -1.9e-11 | 9.3e-12 | - | [-1.40, 1.50] | 1.756993 | +4.96e-03 | si, residuo 0.01735 |

La lectura del resumen es la respuesta de la ficha, y son **tres** cosas
distintas y no una. Seis celdas salen por la reserva:

* las **cuatro del plano de 50 grados con ancla** (Spencer y GLE, Activa y
  Pasiva): hay cruce, pero cae FUERA del tramo usable, porque la rama de
  momentos deja de ser resoluble antes de llegar a el. Es el hallazgo de
  esta medida y la seccion siguiente lo mide;
* **45 pasiva con Spencer**: `g` conserva UN solo signo en todo el tramo
  usable y se acerca a cero tan despacio que nada cruza en el rango
  buscado. Aqui la lectura de 0.1.159 -no hay raiz a la que converger- es
  la correcta, y por eso esta celda esta en la tabla;
* **45 pasiva con GLE**: el cruce esta y las dos ramas convergen a los dos
  lados de el (lambda 0,1 con g +5,64e-4 y lambda 0,2 con g -6,14e-5), pero
  los lambda de un lado son INADMISIBLES -el empuje entre dovelas sale en
  traccion neta- y el muestreo estricto los borra; el re-muestreo relajado
  solo se dispara cuando no sobrevive NINGUNA muestra, y aqui sobreviven
  las del otro lado. Es un tercer mecanismo, reportado como **D149**.

En las diez celdas restantes la raiz cae dentro del tramo usable y el motor
la refina. El ancla no cambia que haya cruce: cambia **donde** cae respecto
del tramo donde la rama de momentos se deja resolver.

## La raiz que se pierde

La rama de momentos de esta cuna es una contraccion cuya razon
tiende a 1 al crecer lambda (medido en 0.1.159 §1 sin refuerzo: 0,73 en
lambda 0 y 0,96 en lambda 2). **Con el ancla deja de ser una contraccion
monotona y pasa a oscilar**: la iteracion amortiguada `F <- 0,5·(F + f_new)`
entra en un ciclo de periodo 2 cuya amplitud CRECE, y la orbita se sale de la
region admisible -`solve_branch` devuelve `None`- antes de que ninguno de los
dos mecanismos que 0.1.159 y 0.1.176 pusieron para esto llegue a verla: el
rescate de Wegstein entra en la pasada siguiente a `STALL_PATIENCE` = 80 y la
rama muere antes.

Lo que sigue busca ese punto fijo adelantando la puerta -`patience` gobierna
a la vez cuando entra el rescate y cuando corta el estancamiento-, con varios
arranques. **No es un cambio del motor**: es el mismo `solve_branch` con otro
argumento. El control de que lo alcanzado es un punto fijo y no el sitio donde
una iteracion se paro es que puertas distintas dan el MISMO numero: la columna
`caminos` cuenta cuantas combinaciones convergen y `dispersion` es la
diferencia entre la mayor y la menor.

### spencer · 45 grados · ancla pasiva

| λ | F_m (punto fijo) | g = F_f − F_m | puerta | arranque | pasadas | caminos | dispersion |
|---|---|---|---|---|---|---|---|
| -1.500 | 1.308058837 | +0.000678422 | 50 | 1.309 | 112 | 5 | 7.8e-11 |
| -1.450 | 1.308045602 | +0.000691656 | 50 | 1.309 | 104 | 5 | 1.3e-09 |
| -1.400 | 1.308032123 | +0.000705136 | 30 | 1.000 | 133 | 10 | 4.7e-10 |
| -1.350 | 1.308018391 | +0.000718868 | 30 | 1.000 | 133 | 10 | 3.5e-10 |
| -1.300 | 1.308004400 | +0.000732859 | 25 | 1.309 | 81 | 13 | 2.7e-10 |
| -1.250 | 1.307990142 | +0.000747116 | 25 | 1.309 | 78 | 12 | 2.2e-09 |
| -1.200 | 1.307975611 | +0.000761648 | 25 | 1.000 | 186 | 18 | 6.4e-10 |
| -1.150 | 1.307960797 | +0.000776462 | 25 | 1.309 | 63 | 17 | 6.5e-09 |
| -1.100 | 1.307945692 | +0.000791566 | 25 | 1.000 | 89 | 18 | 3.9e-10 |
| -1.050 | 1.307930288 | +0.000806970 | 25 | 1.000 | 90 | 18 | 3.8e-10 |
| -1.000 | 1.307914576 | +0.000822682 | 25 | 1.000 | 78 | 18 | 4.3e-10 |

**No se alcanza ninguna raiz en este tramo**: `g` no cambia de signo en ninguna de las lambdas donde alguna puerta llega al punto fijo.

### spencer · 50 grados · ancla activa

| λ | F_m (punto fijo) | g = F_f − F_m | puerta | arranque | pasadas | caminos | dispersion |
|---|---|---|---|---|---|---|---|
| 0.980 | 2.883283776 | -0.125825851 | 30 | 1.000 | 234 | 15 | 1.5e-10 |
| 0.990 | 2.879613985 | -0.122156060 | 30 | 1.000 | 252 | 11 | 5.2e-11 |
| 1.000 | 2.875943168 | -0.118485243 | 30 | 2.757 | 248 | 6 | 3.7e-11 |
| 1.010 | 2.872271275 | -0.114813350 | 30 | 2.757 | 266 | 3 | 2.5e-11 |
| 1.020 | 2.868598255 | -0.111140330 | 30 | 2.757 | 288 | 2 | 8.6e-12 |
| 1.030 | 2.864924058 | -0.107466133 | 30 | 2.757 | 334 | 1 | 0.0e+00 |
| 1.040 | - | - | - | - | - | 0 | - |
| 1.050 | - | - | - | - | - | 0 | - |
| 1.060 | - | - | - | - | - | 0 | - |
| 1.070 | - | - | - | - | - | 0 | - |

**No se alcanza ninguna raiz en este tramo**: `g` no cambia de signo en ninguna de las lambdas donde alguna puerta llega al punto fijo.

### spencer · 50 grados · ancla pasiva

| λ | F_m (punto fijo) | g = F_f − F_m | puerta | arranque | pasadas | caminos | dispersion |
|---|---|---|---|---|---|---|---|
| 1.280 | 1.752847607 | -0.004529725 | 30 | 1.000 | 257 | 15 | 2.1e-10 |
| 1.285 | 1.752283880 | -0.003965997 | 30 | 1.000 | 261 | 14 | 2.1e-10 |
| 1.290 | 1.751718944 | -0.003401061 | 30 | 1.000 | 261 | 12 | 2.1e-10 |
| 1.295 | 1.751152795 | -0.002834912 | 30 | 1.748 | 235 | 13 | 2.1e-10 |
| 1.300 | 1.750585426 | -0.002267543 | 30 | 1.000 | 266 | 12 | 2.2e-11 |
| 1.305 | 1.750016832 | -0.001698949 | 30 | 1.000 | 280 | 7 | 1.8e-11 |
| 1.310 | 1.749447007 | -0.001129125 | 35 | 1.748 | 314 | 4 | 1.1e-11 |
| 1.315 | 1.748875946 | -0.000558063 | 45 | 1.748 | 348 | 2 | 4.7e-12 |
| 1.320 | 1.748303642 | +0.000014241 | 30 | 1.748 | 304 | 4 | 1.3e-11 |
| 1.325 | 1.747730089 | +0.000587793 | 30 | 1.748 | 314 | 2 | 1.8e-12 |
| 1.330 | 1.747155282 | +0.001162600 | 30 | 1.748 | 324 | 2 | 1.1e-12 |
| 1.335 | 1.746579215 | +0.001738668 | 30 | 1.000 | 348 | 3 | 9.7e-12 |
| 1.340 | 1.746001881 | +0.002316002 | 30 | 1.000 | 364 | 3 | 1.3e-11 |
| 1.345 | 1.745423274 | +0.002894609 | 30 | 1.748 | 358 | 1 | 0.0e+00 |
| 1.350 | 1.744843389 | +0.003474494 | 30 | 1.748 | 372 | 1 | 0.0e+00 |
| 1.355 | - | - | - | - | - | 0 | - |
| 1.360 | 1.743679757 | +0.004638126 | 30 | 1.748 | 454 | 1 | 0.0e+00 |
| 1.365 | - | - | - | - | - | 0 | - |
| 1.370 | - | - | - | - | - | 0 | - |
| 1.375 | - | - | - | - | - | 0 | - |
| 1.380 | - | - | - | - | - | 0 | - |

**Hay raiz en lambda 1.31988**, donde `F_m = F_f = 1.748317883`, que es la forma cerrada de la cuna a -1.9e-11. Lo que el motor publica hoy sobre esta celda es 1.765482, a +9.82e-03 de esa forma cerrada.

### gle · 50 grados · ancla activa

| λ | F_m (punto fijo) | g = F_f − F_m | puerta | arranque | pasadas | caminos | dispersion |
|---|---|---|---|---|---|---|---|
| 1.150 | 2.916449927 | -0.158992002 | 25 | 2.757 | 296 | 13 | 3.1e-11 |
| 1.170 | 2.911542982 | -0.154085057 | 25 | 1.000 | 402 | 11 | 3.1e-11 |
| 1.190 | 2.906654655 | -0.149196730 | 25 | 1.000 | 534 | 15 | 1.8e-10 |
| 1.210 | 2.901784608 | -0.144326683 | 25 | 1.000 | 902 | 9 | 1.8e-10 |
| 1.230 | 2.896932504 | -0.139474579 | 25 | 2.757 | 1784 | 4 | 1.7e-10 |
| 1.250 | - | - | - | - | - | 0 | - |
| 1.270 | - | - | - | - | - | 0 | - |
| 1.290 | - | - | - | - | - | 0 | - |
| 1.310 | - | - | - | - | - | 0 | - |

**No se alcanza ninguna raiz en este tramo**: `g` no cambia de signo en ninguna de las lambdas donde alguna puerta llega al punto fijo.

### gle · 50 grados · ancla pasiva

| λ | F_m (punto fijo) | g = F_f − F_m | puerta | arranque | pasadas | caminos | dispersion |
|---|---|---|---|---|---|---|---|
| 1.500 | 1.765668164 | -0.017350281 | 45 | 1.000 | 354 | 9 | 1.4e-10 |
| 1.510 | 1.764990780 | -0.016672897 | 30 | 1.000 | 371 | 11 | 1.9e-10 |
| 1.520 | 1.764313079 | -0.015995196 | 45 | 1.748 | 418 | 8 | 1.1e-10 |
| 1.530 | 1.763635055 | -0.015317172 | 25 | 1.000 | 458 | 10 | 1.5e-10 |
| 1.540 | 1.762956699 | -0.014638816 | 35 | 1.000 | 538 | 13 | 1.3e-10 |
| 1.550 | 1.762278005 | -0.013960122 | 25 | 1.000 | 610 | 17 | 6.0e-11 |
| 1.560 | 1.761598966 | -0.013281083 | 25 | 1.000 | 739 | 16 | 3.7e-11 |
| 1.570 | 1.760919573 | -0.012601691 | 25 | 1.000 | 935 | 13 | 3.6e-11 |
| 1.580 | 1.760239821 | -0.011921938 | 25 | 1.000 | 1267 | 10 | 3.4e-11 |
| 1.590 | 1.759559701 | -0.011241818 | 25 | 1.000 | 1956 | 6 | 3.4e-11 |
| 1.600 | 1.758879207 | -0.010561324 | 25 | 1.748 | 3809 | 2 | 4.6e-14 |
| 1.610 | - | - | - | - | - | 0 | - |
| 1.620 | - | - | - | - | - | 0 | - |
| 1.630 | - | - | - | - | - | 0 | - |
| 1.640 | - | - | - | - | - | 0 | - |

**No se alcanza ninguna raiz en este tramo**: `g` no cambia de signo en ninguna de las lambdas donde alguna puerta llega al punto fijo.


## Las curvas

Tabla completa para el plano de 50 grados y para el 45
pasiva, que son las celdas donde vive el hallazgo. Para las demas se conservan
los nodos de la rejilla del motor, los multiplos de 0,25 y **toda** fila en
que alguna rama cambia de estado; la regla se dice aqui porque una tabla que
esconde su propio submuestreo no es evidencia.

### spencer · 35 grados · ancla sin ancla (submuestreada)

- **Forma cerrada** 1.009342663 · **F_f** 1.009342663 (-3.6e-11) · 101 filas, 81 usables · min |g| 6.071e-07 en lambda 0.70
- **Motor**: fos 1.009342663 · converged si · lambda 0.7002 · reserva no · residuo - · reason `-`
- **Muertes de la rama de momentos**: nula 0 · empuje 0 · presupuesto 18 · estancamiento 2

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | 1.009343 | 1.006423 | +0.002919 | 42 | 50 | - | - | no |
| -1.75 | 1.009343 | 1.006529 | +0.002813 | 42 | 38 | - | - | no |
| -1.50 | 1.009343 | 1.006649 | +0.002693 | 42 | 36 | - | - | no |
| -1.25 | 1.009343 | 1.006786 | +0.002557 | 42 | 27 | - | - | no |
| -1.00 | 1.009343 | 1.006944 | +0.002399 | 42 | 26 | - | - | no |
| -0.75 | 1.009343 | 1.007128 | +0.002215 | 42 | 21 | - | - | no |
| -0.60 | 1.009343 | 1.007254 | +0.002089 | 42 | 21 | - | - | no |
| -0.50 | 1.009343 | 1.007345 | +0.001998 | 42 | 20 | - | - | no |
| -0.40 | 1.009343 | 1.007443 | +0.001900 | 42 | 26 | - | - | no |
| -0.25 | 1.009343 | 1.007605 | +0.001738 | 42 | 32 | - | - | no |
| -0.20 | 1.009343 | 1.007663 | +0.001679 | 42 | 34 | - | - | no |
| -0.10 | 1.009343 | 1.007787 | +0.001556 | 42 | 38 | - | - | no |
| 0.00 | 1.009343 | 1.007922 | +0.001421 | 42 | 42 | - | - | no |
| 0.10 | 1.009343 | 1.008069 | +0.001274 | 42 | 46 | - | - | no |
| 0.20 | 1.009343 | 1.008230 | +0.001112 | 42 | 50 | - | - | no |
| 0.25 | 1.009343 | 1.008317 | +0.001026 | 42 | 52 | - | - | no |
| 0.40 | 1.009343 | 1.008604 | +0.000738 | 42 | 59 | - | - | no |
| 0.50 | 1.009343 | 1.008823 | +0.000520 | 42 | 65 | - | - | no |
| 0.60 | 1.009343 | 1.009067 | +0.000276 | 42 | 71 | - | - | no |
| 0.75 | 1.009343 | 1.009493 | -0.000150 | 42 | 82 r | - | - | no |
| 0.80 | 1.009343 | 1.009654 | -0.000311 | 42 | 86 r | - | - | no |
| 1.00 | 1.009343 | 1.010424 | -0.001081 | 42 | 93 r | - | - | no |
| 1.25 | 1.009343 | 1.011800 | -0.002458 | 42 | 112 r | - | - | no |
| 1.50 | 1.009343 | 1.014038 | -0.004695 | 42 | 142 r | - | - | no |
| 1.75 | 1.009343 | 1.018268 | -0.008925 | 42 | 194 r | - | - | no |
| 2.00 | 1.009343 | 1.028781 | -0.019438 | 42 | 314 r | - | - | no |
| 2.05 | 1.009343 | - | - | 42 | 342 | - | estancamiento | no |
| 2.15 | 1.009343 | - | - | 42 | 400 | - | presupuesto | no |
| 2.25 | 1.009343 | - | - | 42 | 400 | - | presupuesto | no |
| 2.50 | 1.009343 | - | - | 42 | 400 | - | presupuesto | no |
| 2.75 | 1.009343 | - | - | 42 | 400 | - | presupuesto | no |
| 3.00 | 1.009343 | - | - | 42 | 400 | - | presupuesto | no |

### spencer · 35 grados · ancla activa (submuestreada)

- **Forma cerrada** 1.312709408 · **F_f** 1.312709408 (-1.5e-11) · 101 filas, 85 usables · min |g| 0.001812 en lambda 0.70
- **Motor**: fos 1.312709408 · converged si · lambda 0.7125 · reserva no · residuo - · reason `-`
- **Muertes de la rama de momentos**: nula 13 · empuje 0 · presupuesto 1 · estancamiento 2

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | 1.312709 | - | - | 47 | 204 | - | estancamiento | no |
| -1.90 | 1.312709 | 1.167015 | +0.145694 | 47 | 77 | - | - | no |
| -1.75 | 1.312709 | 1.170134 | +0.142575 | 47 | 68 | - | - | no |
| -1.50 | 1.312709 | 1.175920 | +0.136789 | 47 | 49 | - | - | no |
| -1.25 | 1.312709 | 1.182582 | +0.130127 | 47 | 44 | - | - | no |
| -1.00 | 1.312709 | 1.190327 | +0.122382 | 47 | 39 | - | - | no |
| -0.75 | 1.312709 | 1.199431 | +0.113278 | 47 | 31 | - | - | no |
| -0.60 | 1.312709 | 1.205696 | +0.107013 | 47 | 26 | - | - | no |
| -0.50 | 1.312709 | 1.210267 | +0.102442 | 47 | 25 | - | - | no |
| -0.40 | 1.312709 | 1.215196 | +0.097513 | 47 | 22 | - | - | no |
| -0.25 | 1.312709 | 1.223350 | +0.089360 | 47 | 33 | - | - | no |
| -0.20 | 1.312709 | 1.226295 | +0.086415 | 47 | 36 | - | - | no |
| -0.10 | 1.312709 | 1.232567 | +0.080143 | 47 | 41 | - | - | no |
| 0.00 | 1.312709 | 1.239401 | +0.073309 | 47 | 46 | - | - | no |
| 0.10 | 1.312709 | 1.246870 | +0.065839 | 47 | 51 | - | - | no |
| 0.20 | 1.312709 | 1.255060 | +0.057650 | 47 | 56 | - | - | no |
| 0.25 | 1.312709 | 1.259454 | +0.053255 | 47 | 59 | - | - | no |
| 0.40 | 1.312709 | 1.274009 | +0.038701 | 47 | 67 | - | - | no |
| 0.50 | 1.312709 | 1.285018 | +0.027691 | 47 | 74 | - | - | no |
| 0.60 | 1.312709 | 1.297253 | +0.015456 | 47 | 80 | - | - | no |
| 0.75 | 1.312709 | 1.318314 | -0.005604 | 47 | 88 r | - | - | no |
| 0.80 | 1.312709 | 1.326165 | -0.013456 | 47 | 89 r | - | - | no |
| 1.00 | 1.312709 | 1.362604 | -0.049894 | 47 | 93 r | - | - | no |
| 1.25 | 1.312709 | 1.422539 | -0.109830 | 47 | 111 r | - | - | no |
| 1.50 | 1.312709 | 1.504238 | -0.191529 | 47 | 131 r | - | - | no |
| 1.75 | 1.312709 | 1.614534 | -0.301825 | 47 | 153 r | - | - | no |
| 2.00 | 1.312709 | 1.759125 | -0.446415 | 47 | 185 r | - | - | no |
| 2.25 | 1.312709 | 1.940727 | -0.628018 | 47 | 279 r | - | - | no |
| 2.35 | 1.312709 | - | - | 47 | 400 | - | presupuesto | no |
| 2.40 | 1.312709 | - | - | 47 | - | - | nula | no |
| 2.50 | 1.312709 | - | - | 47 | - | - | nula | no |
| 2.75 | 1.312709 | - | - | 47 | - | - | nula | no |
| 3.00 | 1.312709 | - | - | 47 | - | - | nula | no |

### spencer · 35 grados · ancla pasiva (submuestreada)

- **Forma cerrada** 1.250414516 · **F_f** 1.250414516 (-1.8e-11) · 101 filas, 93 usables · min |g| 0.001395 en lambda 0.70
- **Motor**: fos 1.250414516 · converged si · lambda 0.7148 · reserva no · residuo - · reason `-`
- **Muertes de la rama de momentos**: nula 8 · empuje 0 · presupuesto 0 · estancamiento 0

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | 1.250415 | 1.146462 | +0.103952 | 47 | 69 | - | - | no |
| -1.75 | 1.250415 | 1.150374 | +0.100040 | 47 | 60 | - | - | no |
| -1.50 | 1.250415 | 1.154803 | +0.095612 | 47 | 44 | - | - | no |
| -1.25 | 1.250415 | 1.159853 | +0.090561 | 47 | 42 | - | - | no |
| -1.00 | 1.250415 | 1.165662 | +0.084752 | 47 | 37 | - | - | no |
| -0.75 | 1.250415 | 1.172408 | +0.078007 | 47 | 29 | - | - | no |
| -0.60 | 1.250415 | 1.176999 | +0.073416 | 47 | 25 | - | - | no |
| -0.50 | 1.250415 | 1.180324 | +0.070091 | 47 | 24 | - | - | no |
| -0.40 | 1.250415 | 1.183885 | +0.066529 | 47 | 27 | - | - | no |
| -0.25 | 1.250415 | 1.189726 | +0.060689 | 47 | 36 | - | - | no |
| -0.20 | 1.250415 | 1.191820 | +0.058595 | 47 | 39 | - | - | no |
| -0.10 | 1.250415 | 1.196253 | +0.054161 | 47 | 43 | - | - | no |
| 0.00 | 1.250415 | 1.201044 | +0.049370 | 47 | 48 | - | - | no |
| 0.10 | 1.250415 | 1.206235 | +0.044180 | 47 | 53 | - | - | no |
| 0.20 | 1.250415 | 1.211872 | +0.038542 | 47 | 58 | - | - | no |
| 0.25 | 1.250415 | 1.214876 | +0.035539 | 47 | 60 | - | - | no |
| 0.40 | 1.250415 | 1.224718 | +0.025696 | 47 | 68 | - | - | no |
| 0.50 | 1.250415 | 1.232063 | +0.018351 | 47 | 74 | - | - | no |
| 0.60 | 1.250415 | 1.240131 | +0.010283 | 47 | 79 | - | - | no |
| 0.75 | 1.250415 | 1.253806 | -0.003392 | 47 | 87 r | - | - | no |
| 0.80 | 1.250415 | 1.258841 | -0.008427 | 47 | 88 r | - | - | no |
| 1.00 | 1.250415 | 1.281819 | -0.031404 | 47 | 91 r | - | - | no |
| 1.25 | 1.250415 | 1.318510 | -0.068095 | 47 | 107 r | - | - | no |
| 1.50 | 1.250415 | 1.367099 | -0.116684 | 47 | 125 r | - | - | no |
| 1.75 | 1.250415 | 1.431439 | -0.181025 | 47 | 145 r | - | - | no |
| 2.00 | 1.250415 | 1.515239 | -0.264824 | 47 | 169 r | - | - | no |
| 2.25 | 1.250415 | 1.620749 | -0.370334 | 47 | 203 r | - | - | no |
| 2.50 | 1.250415 | 1.747832 | -0.497418 | 47 | 279 r | - | - | no |
| 2.65 | 1.250415 | - | - | 47 | - | - | nula | no |
| 2.75 | 1.250415 | - | - | 47 | - | - | nula | no |
| 3.00 | 1.250415 | - | - | 47 | - | - | nula | no |

### spencer · 40 grados · ancla sin ancla (submuestreada)

- **Forma cerrada** 0.901452199 · **F_f** 0.901452199 (+4.7e-11) · 101 filas, 81 usables · min |g| 7.103e-05 en lambda 0.85
- **Motor**: fos 0.901452199 · converged si · lambda 0.8391 · reserva no · residuo - · reason `-`
- **Muertes de la rama de momentos**: nula 0 · empuje 13 · presupuesto 2 · estancamiento 5

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | 0.901452 | 0.908239 | -0.006787 | 53 | 59 | - | - | si |
| -1.75 | 0.901452 | 0.908004 | -0.006552 | 53 | 53 | - | - | si |
| -1.50 | 0.901452 | 0.907740 | -0.006288 | 53 | 44 | - | - | si |
| -1.25 | 0.901452 | 0.907441 | -0.005989 | 53 | 38 | - | - | si |
| -1.00 | 0.901452 | 0.907100 | -0.005648 | 53 | 33 | - | - | si |
| -0.75 | 0.901452 | 0.906707 | -0.005254 | 53 | 26 | - | - | si |
| -0.60 | 0.901452 | 0.906440 | -0.004988 | 53 | 22 | - | - | si |
| -0.50 | 0.901452 | 0.906248 | -0.004796 | 53 | 29 | - | - | si |
| -0.40 | 0.901452 | 0.906043 | -0.004590 | 53 | 35 | - | - | si |
| -0.25 | 0.901452 | 0.905707 | -0.004254 | 53 | 42 | - | - | si |
| -0.20 | 0.901452 | 0.905586 | -0.004134 | 53 | 44 | - | - | si |
| -0.10 | 0.901452 | 0.905332 | -0.003880 | 53 | 49 | - | - | si |
| 0.00 | 0.901452 | 0.905057 | -0.003605 | 53 | 54 | - | - | si |
| 0.10 | 0.901452 | 0.904760 | -0.003308 | 53 | 58 | - | - | si |
| 0.20 | 0.901452 | 0.904437 | -0.002985 | 53 | 63 | - | - | si |
| 0.25 | 0.901452 | 0.904264 | -0.002812 | 53 | 66 | - | - | si |
| 0.40 | 0.901452 | 0.903698 | -0.002246 | 53 | 75 | - | - | si |
| 0.50 | 0.901452 | 0.903274 | -0.001821 | 53 | 82 r | - | - | si |
| 0.60 | 0.901452 | 0.902804 | -0.001352 | 53 | 86 r | - | - | si |
| 0.75 | 0.901452 | 0.901999 | -0.000547 | 53 | 89 r | - | - | si |
| 0.80 | 0.901452 | 0.901699 | -0.000247 | 53 | 90 r | - | - | si |
| 1.00 | 0.901452 | 0.900298 | +0.001154 | 53 | 102 r | - | - | si |
| 1.25 | 0.901452 | 0.897905 | +0.003547 | 53 | 120 r | - | - | si |
| 1.50 | 0.901452 | 0.894273 | +0.007180 | 53 | 150 r | - | - | si |
| 1.75 | 0.901452 | 0.888019 | +0.013433 | 53 | 198 r | - | - | si |
| 2.00 | 0.901452 | 0.873927 | +0.027525 | 53 | 328 r | - | - | si |
| 2.05 | 0.901452 | - | - | 53 | 374 | - | estancamiento | si |
| 2.10 | 0.901452 | - | - | 53 | 400 | - | presupuesto | si |
| 2.20 | 0.901452 | - | - | 53 | 190 | - | estancamiento | si |
| 2.25 | 0.901452 | - | - | 53 | 188 | - | estancamiento | si |
| 2.30 | 0.901452 | - | - | 53 | 164 | - | empuje | si |
| 2.50 | 0.901452 | - | - | 53 | 123 | - | empuje | si |
| 2.75 | 0.901452 | - | - | 53 | 122 | - | empuje | si |
| 2.95 | 0.901452 | - | - | 53 | 209 | - | estancamiento | si |
| 3.00 | 0.901452 | - | - | 53 | 215 | - | estancamiento | si |

### spencer · 40 grados · ancla activa (submuestreada)

- **Forma cerrada** 1.288830844 · **F_f** 1.288830844 (-2.7e-11) · 101 filas, 77 usables · min |g| 0.000729 en lambda 0.80
- **Motor**: fos 1.288830844 · converged si · lambda 0.8075 · reserva no · residuo - · reason `-`
- **Muertes de la rama de momentos**: nula 18 · empuje 0 · presupuesto 1 · estancamiento 5

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | 1.288831 | - | - | 49 | 182 | - | estancamiento | no |
| -1.90 | 1.288831 | - | - | 49 | - | - | nula | no |
| -1.85 | 1.288831 | - | - | 49 | 195 | - | estancamiento | no |
| -1.80 | 1.288831 | - | - | 49 | - | - | nula | no |
| -1.75 | 1.288831 | - | - | 49 | 207 | - | estancamiento | no |
| -1.70 | 1.288831 | 1.179642 | +0.109189 | 49 | 95 r | - | - | no |
| -1.65 | 1.288831 | - | - | 49 | 232 | - | estancamiento | no |
| -1.60 | 1.288831 | 1.181534 | +0.107296 | 49 | 76 | - | - | no |
| -1.50 | 1.288831 | 1.183522 | +0.105309 | 49 | 69 | - | - | no |
| -1.25 | 1.288831 | 1.188951 | +0.099880 | 49 | 56 | - | - | no |
| -1.00 | 1.288831 | 1.195146 | +0.093685 | 49 | 42 | - | - | no |
| -0.75 | 1.288831 | 1.202275 | +0.086556 | 49 | 33 | - | - | no |
| -0.60 | 1.288831 | 1.207087 | +0.081744 | 49 | 31 | - | - | no |
| -0.50 | 1.288831 | 1.210553 | +0.078278 | 49 | 27 | - | - | no |
| -0.40 | 1.288831 | 1.214247 | +0.074584 | 49 | 23 | - | - | no |
| -0.25 | 1.288831 | 1.220265 | +0.068565 | 49 | 36 | - | - | no |
| -0.20 | 1.288831 | 1.222411 | +0.066420 | 49 | 39 | - | - | no |
| -0.10 | 1.288831 | 1.226934 | +0.061897 | 49 | 45 | - | - | no |
| 0.00 | 1.288831 | 1.231791 | +0.057040 | 49 | 50 | - | - | no |
| 0.10 | 1.288831 | 1.237017 | +0.051814 | 49 | 55 | - | - | no |
| 0.20 | 1.288831 | 1.242653 | +0.046178 | 49 | 61 | - | - | no |
| 0.25 | 1.288831 | 1.245639 | +0.043192 | 49 | 64 | - | - | no |
| 0.40 | 1.288831 | 1.255342 | +0.033489 | 49 | 72 | - | - | no |
| 0.50 | 1.288831 | 1.262505 | +0.026325 | 49 | 78 | - | - | no |
| 0.60 | 1.288831 | 1.270301 | +0.018530 | 49 | 85 r | - | - | no |
| 0.75 | 1.288831 | 1.283348 | +0.005483 | 49 | 89 r | - | - | no |
| 0.80 | 1.288831 | 1.288102 | +0.000729 | 49 | 90 r | - | - | no |
| 1.00 | 1.288831 | 1.309482 | -0.020651 | 49 | 100 r | - | - | no |
| 1.25 | 1.288831 | 1.342691 | -0.053860 | 49 | 106 r | - | - | no |
| 1.50 | 1.288831 | 1.385309 | -0.096478 | 49 | 135 r | - | - | no |
| 1.75 | 1.288831 | 1.440151 | -0.151320 | 49 | 171 r | - | - | no |
| 2.00 | 1.288831 | 1.510149 | -0.221318 | 49 | 233 r | - | - | no |
| 2.20 | 1.288831 | - | - | 49 | 400 | - | presupuesto | no |
| 2.25 | 1.288831 | - | - | 49 | - | - | nula | no |
| 2.50 | 1.288831 | - | - | 49 | - | - | nula | no |
| 2.75 | 1.288831 | - | - | 49 | - | - | nula | no |
| 3.00 | 1.288831 | - | - | 49 | - | - | nula | no |

### spencer · 40 grados · ancla pasiva (submuestreada)

- **Forma cerrada** 1.217018877 · **F_f** 1.217018877 (-2.1e-11) · 101 filas, 85 usables · min |g| 0.0001073 en lambda 0.80
- **Motor**: fos 1.217018877 · converged si · lambda 0.8018 · reserva no · residuo - · reason `-`
- **Muertes de la rama de momentos**: nula 13 · empuje 0 · presupuesto 0 · estancamiento 3

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | 1.217019 | - | - | 50 | - | - | nula | no |
| -1.95 | 1.217019 | 1.143600 | +0.073419 | 50 | 114 r | - | - | no |
| -1.90 | 1.217019 | - | - | 50 | 193 | - | estancamiento | no |
| -1.80 | 1.217019 | 1.145380 | +0.071639 | 50 | 92 r | - | - | no |
| -1.75 | 1.217019 | - | - | 50 | 234 | - | estancamiento | no |
| -1.70 | 1.217019 | 1.146634 | +0.070385 | 50 | 74 | - | - | no |
| -1.50 | 1.217019 | 1.149317 | +0.067702 | 50 | 64 | - | - | no |
| -1.25 | 1.217019 | 1.153044 | +0.063974 | 50 | 50 | - | - | no |
| -1.00 | 1.217019 | 1.157263 | +0.059756 | 50 | 40 | - | - | no |
| -0.75 | 1.217019 | 1.162071 | +0.054948 | 50 | 31 | - | - | no |
| -0.60 | 1.217019 | 1.165290 | +0.051729 | 50 | 29 | - | - | no |
| -0.50 | 1.217019 | 1.167596 | +0.049423 | 50 | 25 | - | - | no |
| -0.40 | 1.217019 | 1.170042 | +0.046977 | 50 | 28 | - | - | no |
| -0.25 | 1.217019 | 1.174003 | +0.043016 | 50 | 39 | - | - | no |
| -0.20 | 1.217019 | 1.175408 | +0.041611 | 50 | 42 | - | - | no |
| -0.10 | 1.217019 | 1.178357 | +0.038662 | 50 | 47 | - | - | no |
| 0.00 | 1.217019 | 1.181506 | +0.035512 | 50 | 52 | - | - | no |
| 0.10 | 1.217019 | 1.184876 | +0.032143 | 50 | 57 | - | - | no |
| 0.20 | 1.217019 | 1.188489 | +0.028530 | 50 | 62 | - | - | no |
| 0.25 | 1.217019 | 1.190393 | +0.026625 | 50 | 65 | - | - | no |
| 0.40 | 1.217019 | 1.196544 | +0.020475 | 50 | 73 | - | - | no |
| 0.50 | 1.217019 | 1.201047 | +0.015971 | 50 | 79 | - | - | no |
| 0.60 | 1.217019 | 1.205915 | +0.011104 | 50 | 85 r | - | - | no |
| 0.75 | 1.217019 | 1.213990 | +0.003029 | 50 | 88 r | - | - | no |
| 0.80 | 1.217019 | 1.216912 | +0.000107 | 50 | 90 r | - | - | no |
| 1.00 | 1.217019 | 1.229933 | -0.012915 | 50 | 98 r | - | - | no |
| 1.25 | 1.217019 | 1.249852 | -0.032833 | 50 | 106 r | - | - | no |
| 1.50 | 1.217019 | 1.275055 | -0.058036 | 50 | 129 r | - | - | no |
| 1.75 | 1.217019 | 1.307235 | -0.090216 | 50 | 159 r | - | - | no |
| 2.00 | 1.217019 | 1.348398 | -0.131379 | 50 | 201 r | - | - | no |
| 2.25 | 1.217019 | 1.400564 | -0.183545 | 50 | 275 r | - | - | no |
| 2.45 | 1.217019 | - | - | 50 | - | - | nula | no |
| 2.50 | 1.217019 | - | - | 50 | - | - | nula | no |
| 2.75 | 1.217019 | - | - | 50 | - | - | nula | no |
| 3.00 | 1.217019 | - | - | 50 | - | - | nula | no |

### spencer · 45 grados · ancla sin ancla (submuestreada)

- **Forma cerrada** 0.855128047 · **F_f** 0.855128047 (+7.3e-11) · 101 filas, 82 usables · min |g| 3.611e-11 en lambda 1.00
- **Motor**: fos 0.855128047 · converged si · lambda 1.0000 · reserva no · residuo - · reason `-`
- **Muertes de la rama de momentos**: nula 0 · empuje 16 · presupuesto 2 · estancamiento 1

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | 0.855128 | 0.884077 | -0.028949 | 59 | 78 | - | - | si |
| -1.75 | 0.855128 | 0.883087 | -0.027959 | 59 | 68 | - | - | si |
| -1.50 | 0.855128 | 0.881987 | -0.026859 | 59 | 53 | - | - | si |
| -1.25 | 0.855128 | 0.880756 | -0.025628 | 59 | 46 | - | - | si |
| -1.00 | 0.855128 | 0.879371 | -0.024243 | 59 | 32 | - | - | si |
| -0.75 | 0.855128 | 0.877798 | -0.022670 | 59 | 28 | - | - | si |
| -0.60 | 0.855128 | 0.876747 | -0.021619 | 59 | 26 | - | - | si |
| -0.50 | 0.855128 | 0.875996 | -0.020868 | 59 | 34 | - | - | si |
| -0.40 | 0.855128 | 0.875200 | -0.020072 | 59 | 41 | - | - | si |
| -0.25 | 0.855128 | 0.873911 | -0.018783 | 59 | 49 | - | - | si |
| -0.20 | 0.855128 | 0.873454 | -0.018326 | 59 | 51 | - | - | si |
| -0.10 | 0.855128 | 0.872494 | -0.017366 | 59 | 56 | - | - | si |
| 0.00 | 0.855128 | 0.871468 | -0.016340 | 59 | 62 | - | - | si |
| 0.10 | 0.855128 | 0.870369 | -0.015240 | 59 | 67 | - | - | si |
| 0.20 | 0.855128 | 0.869187 | -0.014059 | 59 | 73 | - | - | si |
| 0.25 | 0.855128 | 0.868563 | -0.013435 | 59 | 76 | - | - | si |
| 0.40 | 0.855128 | 0.866538 | -0.011410 | 59 | 84 r | - | - | si |
| 0.50 | 0.855128 | 0.865045 | -0.009917 | 59 | 86 r | - | - | si |
| 0.60 | 0.855128 | 0.863419 | -0.008291 | 59 | 88 r | - | - | si |
| 0.75 | 0.855128 | 0.860687 | -0.005559 | 59 | 91 r | - | - | si |
| 0.80 | 0.855128 | 0.859687 | -0.004559 | 59 | 92 r | - | - | si |
| 1.00 | 0.855128 | 0.855128 | -0.000000 | 59 | 105 r | - | - | si |
| 1.25 | 0.855128 | 0.847742 | +0.007386 | 59 | 124 r | - | - | si |
| 1.50 | 0.855128 | 0.837323 | +0.017805 | 59 | 152 r | - | - | si |
| 1.75 | 0.855128 | 0.821057 | +0.034071 | 59 | 200 r | - | - | si |
| 2.00 | 0.855128 | 0.789064 | +0.066064 | 59 | 326 r | - | - | si |
| 2.10 | 0.855128 | - | - | 59 | 400 | - | presupuesto | si |
| 2.20 | 0.855128 | - | - | 59 | 190 | - | estancamiento | si |
| 2.25 | 0.855128 | - | - | 59 | 152 | - | empuje | si |
| 2.50 | 0.855128 | - | - | 59 | 100 | - | empuje | si |
| 2.75 | 0.855128 | - | - | 59 | 100 | - | empuje | si |
| 3.00 | 0.855128 | - | - | 59 | 95 | - | empuje | si |

### spencer · 45 grados · ancla activa (submuestreada)

- **Forma cerrada** 1.467930420 · **F_f** 1.467930420 (-2.0e-11) · 101 filas, 64 usables · min |g| 0.0001629 en lambda 1.30
- **Motor**: fos 1.467930420 · converged si · lambda 1.2863 · reserva no · residuo - · reason `-`
- **Muertes de la rama de momentos**: nula 31 · empuje 0 · presupuesto 0 · estancamiento 6

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | 1.467930 | - | - | 51 | - | - | nula | no |
| -1.75 | 1.467930 | - | - | 51 | - | - | nula | no |
| -1.70 | 1.467930 | - | - | 51 | 162 | - | estancamiento | no |
| -1.50 | 1.467930 | - | - | 51 | 184 | - | estancamiento | no |
| -1.45 | 1.467930 | 1.451259 | +0.016671 | 51 | 282 r | - | - | no |
| -1.40 | 1.467930 | - | - | 51 | 210 | - | estancamiento | no |
| -1.35 | 1.467930 | 1.451576 | +0.016354 | 51 | 180 r | - | - | no |
| -1.25 | 1.467930 | 1.451905 | +0.016026 | 51 | 136 r | - | - | no |
| -1.00 | 1.467930 | 1.452782 | +0.015148 | 51 | 67 | - | - | no |
| -0.75 | 1.467930 | 1.453751 | +0.014180 | 51 | 43 | - | - | no |
| -0.60 | 1.467930 | 1.454381 | +0.013550 | 51 | 40 | - | - | no |
| -0.50 | 1.467930 | 1.454823 | +0.013107 | 51 | 35 | - | - | no |
| -0.40 | 1.467930 | 1.455286 | +0.012645 | 51 | 30 | - | - | no |
| -0.25 | 1.467930 | 1.456019 | +0.011911 | 51 | 36 | - | - | no |
| -0.20 | 1.467930 | 1.456275 | +0.011656 | 51 | 40 | - | - | no |
| -0.10 | 1.467930 | 1.456804 | +0.011126 | 51 | 47 | - | - | no |
| 0.00 | 1.467930 | 1.457359 | +0.010571 | 51 | 54 | - | - | no |
| 0.10 | 1.467930 | 1.457942 | +0.009989 | 51 | 60 | - | - | no |
| 0.20 | 1.467930 | 1.458553 | +0.009377 | 51 | 66 | - | - | no |
| 0.25 | 1.467930 | 1.458871 | +0.009059 | 51 | 69 | - | - | no |
| 0.40 | 1.467930 | 1.459875 | +0.008055 | 51 | 79 | - | - | no |
| 0.50 | 1.467930 | 1.460590 | +0.007340 | 51 | 85 r | - | - | no |
| 0.60 | 1.467930 | 1.461345 | +0.006585 | 51 | 88 r | - | - | no |
| 0.75 | 1.467930 | 1.462560 | +0.005370 | 51 | 96 r | - | - | no |
| 0.80 | 1.467930 | 1.462989 | +0.004941 | 51 | 98 r | - | - | no |
| 1.00 | 1.467930 | 1.464840 | +0.003091 | 51 | 108 r | - | - | no |
| 1.25 | 1.467930 | 1.467505 | +0.000425 | 51 | 130 r | - | - | no |
| 1.50 | 1.467930 | 1.470660 | -0.002730 | 51 | 165 r | - | - | no |
| 1.75 | 1.467930 | 1.474446 | -0.006516 | 51 | 315 r | - | - | no |
| 1.80 | 1.467930 | - | - | 51 | - | - | nula | no |
| 2.00 | 1.467930 | - | - | 51 | - | - | nula | no |
| 2.25 | 1.467930 | - | - | 51 | - | - | nula | si |
| 2.50 | 1.467930 | - | - | 52 | - | - | nula | no |
| 2.55 | - | - | - | 55 | - | empuje | nula | si |
| 2.75 | - | - | - | 32 | - | empuje | nula | no |
| 3.00 | - | - | - | 22 | - | empuje | nula | no |

### spencer · 45 grados · ancla pasiva

- **Forma cerrada** 1.308737259 · **F_f** 1.308737259 (-2.9e-11) · 101 filas, 68 usables · min |g| 0.0006917 en lambda -1.45
- **Motor**: fos 1.308151718 · converged si · lambda -0.1000 · reserva si · residuo 0.001171 · reason `-`
- **Muertes de la rama de momentos**: nula 26 · empuje 0 · presupuesto 1 · estancamiento 6

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | 1.308737 | - | - | 52 | - | - | nula | no |
| -1.95 | 1.308737 | - | - | 52 | 223 | - | estancamiento | no |
| -1.90 | 1.308737 | - | - | 52 | - | - | nula | no |
| -1.85 | 1.308737 | - | - | 52 | - | - | nula | no |
| -1.80 | 1.308737 | - | - | 52 | - | - | nula | no |
| -1.75 | 1.308737 | - | - | 52 | - | - | nula | no |
| -1.70 | 1.308737 | - | - | 52 | - | - | nula | no |
| -1.65 | 1.308737 | - | - | 52 | 218 | - | estancamiento | no |
| -1.60 | 1.308737 | - | - | 52 | 264 | - | estancamiento | no |
| -1.55 | 1.308737 | - | - | 52 | 311 | - | estancamiento | no |
| -1.50 | 1.308737 | - | - | 52 | 276 | - | estancamiento | no |
| -1.45 | 1.308737 | 1.308046 | +0.000692 | 52 | 144 r | - | - | no |
| -1.40 | 1.308737 | 1.308032 | +0.000705 | 52 | 121 r | - | - | no |
| -1.35 | 1.308737 | - | - | 52 | 295 | - | estancamiento | no |
| -1.30 | 1.308737 | 1.308004 | +0.000733 | 52 | 97 r | - | - | no |
| -1.25 | 1.308737 | 1.307990 | +0.000747 | 52 | 79 | - | - | no |
| -1.20 | 1.308737 | 1.307976 | +0.000762 | 52 | 71 | - | - | no |
| -1.15 | 1.308737 | 1.307961 | +0.000776 | 52 | 58 | - | - | no |
| -1.10 | 1.308737 | 1.307946 | +0.000792 | 52 | 63 | - | - | no |
| -1.05 | 1.308737 | 1.307930 | +0.000807 | 52 | 59 | - | - | no |
| -1.00 | 1.308737 | 1.307915 | +0.000823 | 52 | 55 | - | - | no |
| -0.95 | 1.308737 | 1.307899 | +0.000839 | 52 | 51 | - | - | no |
| -0.90 | 1.308737 | 1.307882 | +0.000855 | 52 | 52 | - | - | no |
| -0.85 | 1.308737 | 1.307865 | +0.000872 | 52 | 48 | - | - | no |
| -0.80 | 1.308737 | 1.307848 | +0.000889 | 52 | 44 | - | - | no |
| -0.75 | 1.308737 | 1.307831 | +0.000906 | 52 | 44 | - | - | no |
| -0.70 | 1.308737 | 1.307813 | +0.000924 | 52 | 41 | - | - | no |
| -0.65 | 1.308737 | 1.307795 | +0.000942 | 52 | 38 | - | - | no |
| -0.60 | 1.308737 | 1.307777 | +0.000961 | 52 | 34 | - | - | no |
| -0.55 | 1.308737 | 1.307758 | +0.000980 | 52 | 35 | - | - | no |
| -0.50 | 1.308737 | 1.307738 | +0.000999 | 52 | 32 | - | - | no |
| -0.45 | 1.308737 | 1.307718 | +0.001019 | 52 | 30 | - | - | no |
| -0.40 | 1.308737 | 1.307698 | +0.001039 | 52 | 29 | - | - | no |
| -0.35 | 1.308737 | 1.307677 | +0.001060 | 52 | 28 | - | - | no |
| -0.30 | 1.308737 | 1.307656 | +0.001081 | 52 | 35 | - | - | no |
| -0.25 | 1.308737 | 1.307635 | +0.001103 | 52 | 40 | - | - | no |
| -0.20 | 1.308737 | 1.307612 | +0.001125 | 52 | 43 | - | - | no |
| -0.15 | 1.308737 | 1.307590 | +0.001148 | 52 | 47 | - | - | no |
| -0.10 | 1.308737 | 1.307566 | +0.001171 | 52 | 50 | - | - | no |
| -0.05 | 1.308737 | 1.307542 | +0.001195 | 52 | 53 | - | - | no |
| 0.00 | 1.308737 | 1.307518 | +0.001219 | 52 | 56 | - | - | no |
| 0.05 | 1.308737 | 1.307493 | +0.001245 | 52 | 59 | - | - | no |
| 0.10 | 1.308737 | 1.307467 | +0.001270 | 52 | 62 | - | - | no |
| 0.15 | 1.308737 | 1.307440 | +0.001297 | 52 | 65 | - | - | no |
| 0.20 | 1.308737 | 1.307413 | +0.001324 | 52 | 68 | - | - | no |
| 0.25 | 1.308737 | 1.307385 | +0.001352 | 52 | 71 | - | - | no |
| 0.30 | 1.308737 | 1.307357 | +0.001380 | 52 | 74 | - | - | no |
| 0.35 | 1.308737 | 1.307327 | +0.001410 | 52 | 77 | - | - | no |
| 0.40 | 1.308737 | 1.307297 | +0.001440 | 52 | 80 | - | - | no |
| 0.45 | 1.308737 | 1.307266 | +0.001471 | 52 | 83 r | - | - | no |
| 0.50 | 1.308737 | 1.307234 | +0.001503 | 52 | 86 r | - | - | no |
| 0.55 | 1.308737 | 1.307201 | +0.001536 | 52 | 87 r | - | - | no |
| 0.60 | 1.308737 | 1.307167 | +0.001570 | 52 | 88 r | - | - | no |
| 0.65 | 1.308737 | 1.307133 | +0.001605 | 52 | 90 r | - | - | no |
| 0.70 | 1.308737 | 1.307097 | +0.001641 | 52 | 90 r | - | - | no |
| 0.75 | 1.308737 | 1.307060 | +0.001678 | 52 | 94 r | - | - | no |
| 0.80 | 1.308737 | 1.307021 | +0.001716 | 52 | 98 r | - | - | no |
| 0.85 | 1.308737 | 1.306982 | +0.001755 | 52 | 100 r | - | - | no |
| 0.90 | 1.308737 | 1.306941 | +0.001796 | 52 | 102 r | - | - | no |
| 0.95 | 1.308737 | 1.306899 | +0.001838 | 52 | 104 r | - | - | no |
| 1.00 | 1.308737 | 1.306856 | +0.001881 | 52 | 106 r | - | - | no |
| 1.05 | 1.308737 | 1.306811 | +0.001926 | 52 | 108 r | - | - | no |
| 1.10 | 1.308737 | 1.306765 | +0.001973 | 52 | 112 r | - | - | no |
| 1.15 | 1.308737 | 1.306716 | +0.002021 | 52 | 116 r | - | - | no |
| 1.20 | 1.308737 | 1.306667 | +0.002071 | 52 | 120 r | - | - | no |
| 1.25 | 1.308737 | 1.306615 | +0.002122 | 52 | 124 r | - | - | no |
| 1.30 | 1.308737 | 1.306561 | +0.002176 | 52 | 128 r | - | - | no |
| 1.35 | 1.308737 | 1.306506 | +0.002232 | 52 | 132 r | - | - | no |
| 1.40 | 1.308737 | 1.306448 | +0.002289 | 52 | 134 r | - | - | no |
| 1.45 | 1.308737 | 1.306388 | +0.002349 | 52 | 136 r | - | - | no |
| 1.50 | 1.308737 | 1.306326 | +0.002412 | 52 | 145 r | - | - | no |
| 1.55 | 1.308737 | 1.306260 | +0.002477 | 52 | 157 r | - | - | no |
| 1.60 | 1.308737 | 1.306193 | +0.002545 | 52 | 171 r | - | - | no |
| 1.65 | 1.308737 | 1.306122 | +0.002615 | 52 | 166 r | - | - | no |
| 1.70 | 1.308737 | 1.306048 | +0.002689 | 52 | 160 r | - | - | no |
| 1.75 | 1.308737 | 1.305971 | +0.002766 | 52 | 209 r | - | - | no |
| 1.80 | 1.308737 | 1.305891 | +0.002847 | 52 | 231 r | - | - | no |
| 1.85 | 1.308737 | 1.305806 | +0.002931 | 52 | 257 r | - | - | no |
| 1.90 | 1.308737 | 1.305718 | +0.003019 | 52 | 291 r | - | - | no |
| 1.95 | 1.308737 | 1.305625 | +0.003112 | 52 | 335 r | - | - | no |
| 2.00 | 1.308737 | - | - | 52 | 400 | - | presupuesto | no |
| 2.05 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.10 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.15 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.20 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.25 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.30 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.35 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.40 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.45 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.50 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.55 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.60 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.65 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.70 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.75 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.80 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.85 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.90 | - | - | - | 48 | - | empuje | nula | no |
| 2.95 | - | - | - | 42 | - | empuje | nula | no |
| 3.00 | - | - | - | 37 | - | empuje | nula | si |

### spencer · 50 grados · ancla sin ancla

- **Forma cerrada** 0.941982760 · **F_f** 0.941982760 (+6.5e-11) · 101 filas, 70 usables · min |g| 0.000639 en lambda 1.20
- **Motor**: fos 0.941982760 · converged si · lambda 1.1918 · reserva no · residuo - · reason `-`
- **Muertes de la rama de momentos**: nula 12 · empuje 7 · presupuesto 2 · estancamiento 10

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | 0.941983 | - | - | 59 | 179 | - | estancamiento | si |
| -1.95 | 0.941983 | - | - | 59 | 137 | - | empuje | si |
| -1.90 | 0.941983 | - | - | 59 | - | - | nula | si |
| -1.85 | 0.941983 | - | - | 59 | 176 | - | estancamiento | si |
| -1.80 | 0.941983 | - | - | 59 | - | - | nula | si |
| -1.75 | 0.941983 | - | - | 59 | - | - | nula | si |
| -1.70 | 0.941983 | - | - | 59 | 211 | - | estancamiento | si |
| -1.65 | 0.941983 | - | - | 59 | 229 | - | estancamiento | si |
| -1.60 | 0.941983 | - | - | 59 | 246 | - | estancamiento | si |
| -1.55 | 0.941983 | - | - | 59 | 222 | - | estancamiento | si |
| -1.50 | 0.941983 | - | - | 59 | 226 | - | estancamiento | si |
| -1.45 | 0.941983 | 1.039218 | -0.097235 | 59 | 121 r | - | - | si |
| -1.40 | 0.941983 | 1.038275 | -0.096292 | 59 | 77 | - | - | si |
| -1.35 | 0.941983 | 1.037315 | -0.095332 | 59 | 97 r | - | - | si |
| -1.30 | 0.941983 | 1.036338 | -0.094355 | 59 | 73 | - | - | si |
| -1.25 | 0.941983 | 1.035343 | -0.093360 | 59 | 64 | - | - | si |
| -1.20 | 0.941983 | 1.034330 | -0.092347 | 59 | 65 | - | - | si |
| -1.15 | 0.941983 | 1.033297 | -0.091315 | 59 | 60 | - | - | si |
| -1.10 | 0.941983 | 1.032246 | -0.090263 | 59 | 51 | - | - | si |
| -1.05 | 0.941983 | 1.031174 | -0.089191 | 59 | 52 | - | - | si |
| -1.00 | 0.941983 | 1.030082 | -0.088099 | 59 | 52 | - | - | si |
| -0.95 | 0.941983 | 1.028968 | -0.086985 | 59 | 48 | - | - | si |
| -0.90 | 0.941983 | 1.027832 | -0.085849 | 59 | 44 | - | - | si |
| -0.85 | 0.941983 | 1.026674 | -0.084691 | 59 | 40 | - | - | si |
| -0.80 | 0.941983 | 1.025492 | -0.083509 | 59 | 40 | - | - | si |
| -0.75 | 0.941983 | 1.024285 | -0.082303 | 59 | 37 | - | - | si |
| -0.70 | 0.941983 | 1.023054 | -0.081071 | 59 | 33 | - | - | si |
| -0.65 | 0.941983 | 1.021797 | -0.079814 | 59 | 34 | - | - | si |
| -0.60 | 0.941983 | 1.020512 | -0.078530 | 59 | 31 | - | - | si |
| -0.55 | 0.941983 | 1.019200 | -0.077217 | 59 | 28 | - | - | si |
| -0.50 | 0.941983 | 1.017859 | -0.075877 | 59 | 29 | - | - | si |
| -0.45 | 0.941983 | 1.016488 | -0.074506 | 59 | 28 | - | - | si |
| -0.40 | 0.941983 | 1.015087 | -0.073104 | 59 | 35 | - | - | si |
| -0.35 | 0.941983 | 1.013653 | -0.071670 | 59 | 38 | - | - | si |
| -0.30 | 0.941983 | 1.012185 | -0.070203 | 59 | 42 | - | - | si |
| -0.25 | 0.941983 | 1.010683 | -0.068701 | 59 | 44 | - | - | si |
| -0.20 | 0.941983 | 1.009145 | -0.067162 | 59 | 47 | - | - | si |
| -0.15 | 0.941983 | 1.007569 | -0.065587 | 59 | 49 | - | - | si |
| -0.10 | 0.941983 | 1.005955 | -0.063972 | 59 | 51 | - | - | si |
| -0.05 | 0.941983 | 1.004299 | -0.062316 | 59 | 53 | - | - | si |
| 0.00 | 0.941983 | 1.002601 | -0.060618 | 59 | 53 | - | - | si |
| 0.05 | 0.941983 | 1.000859 | -0.058876 | 59 | 48 | - | - | si |
| 0.10 | 0.941983 | 0.999070 | -0.057087 | 59 | 58 | - | - | si |
| 0.15 | 0.941983 | 0.997233 | -0.055250 | 59 | 63 | - | - | si |
| 0.20 | 0.941983 | 0.995345 | -0.053362 | 59 | 68 | - | - | si |
| 0.25 | 0.941983 | 0.993404 | -0.051422 | 59 | 72 | - | - | si |
| 0.30 | 0.941983 | 0.991408 | -0.049425 | 59 | 76 | - | - | si |
| 0.35 | 0.941983 | 0.989353 | -0.047371 | 59 | 80 | - | - | si |
| 0.40 | 0.941983 | 0.987237 | -0.045255 | 59 | 83 r | - | - | si |
| 0.45 | 0.941983 | 0.985057 | -0.043074 | 59 | 86 r | - | - | si |
| 0.50 | 0.941983 | 0.982808 | -0.040825 | 59 | 87 r | - | - | si |
| 0.55 | 0.941983 | 0.980488 | -0.038505 | 59 | 88 r | - | - | si |
| 0.60 | 0.941983 | 0.978092 | -0.036109 | 59 | 89 r | - | - | si |
| 0.65 | 0.941983 | 0.975616 | -0.033633 | 59 | 90 r | - | - | si |
| 0.70 | 0.941983 | 0.973055 | -0.031072 | 59 | 94 r | - | - | si |
| 0.75 | 0.941983 | 0.970404 | -0.028422 | 59 | 96 r | - | - | si |
| 0.80 | 0.941983 | 0.967658 | -0.025675 | 59 | 99 r | - | - | si |
| 0.85 | 0.941983 | 0.964810 | -0.022827 | 59 | 101 r | - | - | si |
| 0.90 | 0.941983 | 0.961853 | -0.019870 | 59 | 103 r | - | - | si |
| 0.95 | 0.941983 | 0.958780 | -0.016797 | 59 | 105 r | - | - | si |
| 1.00 | 0.941983 | 0.955582 | -0.013599 | 59 | 107 r | - | - | si |
| 1.05 | 0.941983 | 0.952251 | -0.010268 | 59 | 109 r | - | - | si |
| 1.10 | 0.941983 | 0.948775 | -0.006792 | 59 | 110 r | - | - | si |
| 1.15 | 0.941983 | 0.945144 | -0.003161 | 59 | 118 r | - | - | si |
| 1.20 | 0.941983 | 0.941344 | +0.000639 | 59 | 124 r | - | - | si |
| 1.25 | 0.941983 | 0.937360 | +0.004623 | 59 | 130 r | - | - | si |
| 1.30 | 0.941983 | 0.933176 | +0.008807 | 59 | 136 r | - | - | si |
| 1.35 | 0.941983 | 0.928771 | +0.013211 | 59 | 142 r | - | - | si |
| 1.40 | 0.941983 | 0.924125 | +0.017858 | 59 | 148 r | - | - | si |
| 1.45 | 0.941983 | 0.919209 | +0.022773 | 59 | 156 r | - | - | si |
| 1.50 | 0.941983 | 0.913995 | +0.027988 | 59 | 162 r | - | - | si |
| 1.55 | 0.941983 | 0.908445 | +0.033538 | 59 | 172 r | - | - | si |
| 1.60 | 0.941983 | 0.902515 | +0.039467 | 59 | 182 r | - | - | si |
| 1.65 | 0.941983 | 0.896153 | +0.045830 | 59 | 192 r | - | - | si |
| 1.70 | 0.941983 | 0.889291 | +0.052692 | 59 | 206 r | - | - | si |
| 1.75 | 0.941983 | 0.881847 | +0.060136 | 59 | 220 r | - | - | si |
| 1.80 | 0.941983 | 0.873711 | +0.068271 | 59 | 236 r | - | - | si |
| 1.85 | 0.941983 | 0.864742 | +0.077240 | 59 | 256 r | - | - | si |
| 1.90 | 0.941983 | 0.854743 | +0.087240 | 59 | 280 r | - | - | si |
| 1.95 | 0.941983 | 0.843430 | +0.098553 | 59 | 308 r | - | - | si |
| 2.00 | 0.941983 | 0.830371 | +0.111612 | 59 | 344 r | - | - | si |
| 2.05 | 0.941983 | - | - | 59 | 374 | - | estancamiento | si |
| 2.10 | 0.941983 | - | - | 59 | 400 | - | presupuesto | si |
| 2.15 | 0.941983 | - | - | 59 | 400 | - | presupuesto | si |
| 2.20 | 0.941983 | - | - | 59 | 214 | - | estancamiento | si |
| 2.25 | 0.941983 | - | - | 59 | 186 | - | estancamiento | si |
| 2.30 | 0.941983 | - | - | 59 | 152 | - | empuje | si |
| 2.35 | 0.941983 | - | - | 59 | 130 | - | empuje | si |
| 2.40 | 0.941983 | - | - | 59 | 116 | - | empuje | si |
| 2.45 | 0.941983 | - | - | 59 | 107 | - | empuje | si |
| 2.50 | 0.941983 | - | - | 59 | 101 | - | empuje | si |
| 2.55 | 0.941983 | - | - | 59 | 100 | - | empuje | si |
| 2.60 | 0.941983 | - | - | 59 | - | - | nula | si |
| 2.65 | 0.941983 | - | - | 59 | - | - | nula | si |
| 2.70 | 0.941983 | - | - | 59 | - | - | nula | si |
| 2.75 | 0.941983 | - | - | 59 | - | - | nula | si |
| 2.80 | 0.941983 | - | - | 59 | - | - | nula | si |
| 2.85 | 0.941983 | - | - | 59 | - | - | nula | si |
| 2.90 | 0.941983 | - | - | 59 | - | - | nula | si |
| 2.95 | 0.941983 | - | - | 59 | - | - | nula | si |
| 3.00 | 0.941983 | - | - | 59 | - | - | nula | si |

### spencer · 50 grados · ancla activa

- **Forma cerrada** 2.757457925 · **F_f** 2.757457925 (-9.4e-13) · 101 filas, 34 usables · min |g| 0.1368 en lambda 0.95
- **Motor**: fos 2.853338845 · converged no · lambda 0.8000 · reserva si · residuo 0.1918 · reason `no_lambda_bracket`
- **Muertes de la rama de momentos**: nula 67 · empuje 0 · presupuesto 0 · estancamiento 0

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | - | - | - | 9 | - | empuje | nula | si |
| -1.95 | - | - | - | 9 | - | empuje | nula | si |
| -1.90 | - | - | - | 9 | - | empuje | nula | si |
| -1.85 | - | - | - | 10 | - | empuje | nula | si |
| -1.80 | - | - | - | 10 | - | empuje | nula | si |
| -1.75 | - | - | - | 11 | - | empuje | nula | si |
| -1.70 | - | - | - | 11 | - | empuje | nula | si |
| -1.65 | - | - | - | 12 | - | empuje | nula | si |
| -1.60 | - | - | - | 13 | - | empuje | nula | si |
| -1.55 | - | - | - | 14 | - | empuje | nula | si |
| -1.50 | - | - | - | 15 | - | empuje | nula | si |
| -1.45 | - | - | - | 18 | - | empuje | nula | si |
| -1.40 | - | - | - | 21 | - | empuje | nula | si |
| -1.35 | - | - | - | 26 | - | empuje | nula | si |
| -1.30 | - | - | - | 37 | - | empuje | nula | si |
| -1.25 | 2.757458 | - | - | 48 | - | - | nula | si |
| -1.20 | 2.757458 | - | - | 48 | - | - | nula | si |
| -1.15 | 2.757458 | - | - | 48 | - | - | nula | si |
| -1.10 | 2.757458 | - | - | 48 | - | - | nula | si |
| -1.05 | 2.757458 | - | - | 48 | - | - | nula | si |
| -1.00 | 2.757458 | - | - | 48 | - | - | nula | si |
| -0.95 | 2.757458 | - | - | 48 | - | - | nula | si |
| -0.90 | 2.757458 | - | - | 48 | - | - | nula | si |
| -0.85 | 2.757458 | - | - | 48 | - | - | nula | si |
| -0.80 | 2.757458 | - | - | 48 | - | - | nula | si |
| -0.75 | 2.757458 | - | - | 48 | - | - | nula | si |
| -0.70 | 2.757458 | 3.519649 | -0.762191 | 48 | 219 r | - | - | si |
| -0.65 | 2.757458 | 3.499236 | -0.741778 | 48 | 98 r | - | - | si |
| -0.60 | 2.757458 | 3.478969 | -0.721511 | 48 | 70 | - | - | si |
| -0.55 | 2.757458 | 3.458842 | -0.701384 | 48 | 66 | - | - | si |
| -0.50 | 2.757458 | 3.438849 | -0.681392 | 48 | 57 | - | - | si |
| -0.45 | 2.757458 | 3.418985 | -0.661528 | 48 | 53 | - | - | si |
| -0.40 | 2.757458 | 3.399245 | -0.641787 | 48 | 40 | - | - | si |
| -0.35 | 2.757458 | 3.379622 | -0.622164 | 48 | 42 | - | - | si |
| -0.30 | 2.757458 | 3.360111 | -0.602653 | 48 | 34 | - | - | si |
| -0.25 | 2.757458 | 3.340708 | -0.583250 | 48 | 33 | - | - | si |
| -0.20 | 2.757458 | 3.321407 | -0.563949 | 48 | 27 | - | - | si |
| -0.15 | 2.757458 | 3.302203 | -0.544745 | 48 | 35 | - | - | si |
| -0.10 | 2.757458 | 3.283091 | -0.525633 | 48 | 42 | - | - | si |
| -0.05 | 2.757458 | 3.264066 | -0.506608 | 48 | 48 | - | - | si |
| 0.00 | 2.757458 | 3.245123 | -0.487665 | 48 | 52 | - | - | si |
| 0.05 | 2.757458 | 3.226258 | -0.468800 | 48 | 57 | - | - | si |
| 0.10 | 2.757458 | 3.207464 | -0.450006 | 48 | 61 | - | - | si |
| 0.15 | 2.757458 | 3.188738 | -0.431281 | 48 | 65 | - | - | si |
| 0.20 | 2.757458 | 3.170075 | -0.412617 | 48 | 69 | - | - | si |
| 0.25 | 2.757458 | 3.151470 | -0.394012 | 48 | 73 | - | - | si |
| 0.30 | 2.757458 | 3.132918 | -0.375460 | 48 | 76 | - | - | si |
| 0.35 | 2.757458 | 3.114413 | -0.356955 | 48 | 80 | - | - | si |
| 0.40 | 2.757458 | 3.095952 | -0.338494 | 48 | 85 r | - | - | si |
| 0.45 | 2.757458 | 3.077529 | -0.320072 | 48 | 88 r | - | - | si |
| 0.50 | 2.757458 | 3.059140 | -0.301682 | 48 | 90 r | - | - | si |
| 0.55 | 2.757458 | 3.040779 | -0.283321 | 48 | 94 r | - | - | si |
| 0.60 | 2.757458 | 3.022441 | -0.264983 | 48 | 100 r | - | - | si |
| 0.65 | 2.757458 | 3.004122 | -0.246664 | 48 | 104 r | - | - | si |
| 0.70 | 2.757458 | 2.985815 | -0.228357 | 48 | 107 r | - | - | si |
| 0.75 | 2.757458 | 2.967516 | -0.210058 | 48 | 109 r | - | - | si |
| 0.80 | 2.757458 | 2.949220 | -0.191762 | 48 | 123 r | - | - | si |
| 0.85 | 2.757458 | 2.930920 | -0.173462 | 48 | 143 r | - | - | si |
| 0.90 | 2.757458 | 2.912611 | -0.155153 | 48 | 185 r | - | - | si |
| 0.95 | 2.757458 | 2.894287 | -0.136830 | 48 | 235 r | - | - | si |
| 1.00 | 2.757458 | - | - | 48 | - | - | nula | si |
| 1.05 | 2.757458 | - | - | 48 | - | - | nula | si |
| 1.10 | 2.757458 | - | - | 48 | - | - | nula | si |
| 1.15 | 2.757458 | - | - | 48 | - | - | nula | si |
| 1.20 | 2.757458 | - | - | 48 | - | - | nula | si |
| 1.25 | 2.757458 | - | - | 48 | - | - | nula | no |
| 1.30 | 2.757458 | - | - | 48 | - | - | nula | no |
| 1.35 | 2.757458 | - | - | 48 | - | - | nula | no |
| 1.40 | 2.757458 | - | - | 48 | - | - | nula | no |
| 1.45 | - | - | - | 40 | - | empuje | nula | no |
| 1.50 | - | - | - | 32 | - | empuje | nula | no |
| 1.55 | - | - | - | 27 | - | empuje | nula | si |
| 1.60 | - | - | - | 23 | - | empuje | nula | si |
| 1.65 | - | - | - | 21 | - | empuje | nula | si |
| 1.70 | - | - | - | 19 | - | empuje | nula | si |
| 1.75 | - | - | - | 17 | - | empuje | nula | si |
| 1.80 | - | - | - | 16 | - | empuje | nula | no |
| 1.85 | - | - | - | 15 | - | empuje | nula | si |
| 1.90 | - | - | - | 14 | - | empuje | nula | no |
| 1.95 | - | - | - | 13 | - | empuje | nula | si |
| 2.00 | - | - | - | 12 | - | empuje | nula | no |
| 2.05 | - | - | - | 12 | - | empuje | nula | no |
| 2.10 | - | - | - | 11 | - | empuje | nula | si |
| 2.15 | - | - | - | 11 | - | empuje | nula | si |
| 2.20 | - | - | - | 10 | - | empuje | nula | no |
| 2.25 | - | - | - | 10 | - | empuje | nula | no |
| 2.30 | - | - | - | 10 | - | empuje | nula | no |
| 2.35 | - | - | - | 9 | - | empuje | nula | si |
| 2.40 | - | - | - | 9 | - | empuje | nula | si |
| 2.45 | - | - | - | 9 | - | empuje | nula | si |
| 2.50 | - | - | - | 9 | - | empuje | nula | si |
| 2.55 | - | - | - | 8 | - | empuje | nula | no |
| 2.60 | - | - | - | 8 | - | empuje | nula | no |
| 2.65 | - | - | - | 8 | - | empuje | nula | no |
| 2.70 | - | - | - | 8 | - | empuje | nula | no |
| 2.75 | - | - | - | 8 | - | empuje | nula | no |
| 2.80 | - | - | - | 8 | - | empuje | nula | no |
| 2.85 | - | - | - | 7 | - | empuje | nula | si |
| 2.90 | - | - | - | 7 | - | empuje | nula | si |
| 2.95 | - | - | - | 7 | - | empuje | nula | si |
| 3.00 | - | - | - | 7 | - | empuje | nula | si |

### spencer · 50 grados · ancla pasiva

- **Forma cerrada** 1.748317883 · **F_f** 1.748317883 (-1.9e-11) · 101 filas, 44 usables · min |g| 0.007887 en lambda 1.25
- **Motor**: fos 1.765481995 · converged no · lambda 1.0000 · reserva si · residuo 0.03433 · reason `no_lambda_bracket`
- **Muertes de la rama de momentos**: nula 52 · empuje 0 · presupuesto 0 · estancamiento 5

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | - | - | - | 14 | - | empuje | nula | si |
| -1.95 | - | - | - | 16 | - | empuje | nula | si |
| -1.90 | - | - | - | 17 | - | empuje | nula | si |
| -1.85 | - | - | - | 19 | - | empuje | nula | si |
| -1.80 | - | - | - | 22 | - | empuje | nula | si |
| -1.75 | - | - | - | 26 | - | empuje | nula | si |
| -1.70 | - | - | - | 33 | - | empuje | nula | si |
| -1.65 | - | - | - | 49 | - | empuje | nula | si |
| -1.60 | 1.748318 | - | - | 52 | - | - | nula | si |
| -1.55 | 1.748318 | - | - | 52 | - | - | nula | si |
| -1.50 | 1.748318 | - | - | 52 | - | - | nula | si |
| -1.45 | 1.748318 | - | - | 52 | - | - | nula | si |
| -1.40 | 1.748318 | - | - | 52 | - | - | nula | si |
| -1.35 | 1.748318 | - | - | 52 | - | - | nula | si |
| -1.30 | 1.748318 | - | - | 52 | - | - | nula | si |
| -1.25 | 1.748318 | - | - | 52 | - | - | nula | si |
| -1.20 | 1.748318 | - | - | 52 | - | - | nula | si |
| -1.15 | 1.748318 | - | - | 52 | 167 | - | estancamiento | si |
| -1.10 | 1.748318 | - | - | 52 | 204 | - | estancamiento | si |
| -1.05 | 1.748318 | - | - | 52 | 264 | - | estancamiento | si |
| -1.00 | 1.748318 | - | - | 52 | 348 | - | estancamiento | si |
| -0.95 | 1.748318 | - | - | 52 | 292 | - | estancamiento | si |
| -0.90 | 1.748318 | 1.927997 | -0.179679 | 52 | 169 r | - | - | si |
| -0.85 | 1.748318 | 1.924993 | -0.176675 | 52 | 119 r | - | - | si |
| -0.80 | 1.748318 | 1.921956 | -0.173638 | 52 | 80 | - | - | si |
| -0.75 | 1.748318 | 1.918887 | -0.170570 | 52 | 75 | - | - | si |
| -0.70 | 1.748318 | 1.915785 | -0.167467 | 52 | 67 | - | - | si |
| -0.65 | 1.748318 | 1.912649 | -0.164331 | 52 | 59 | - | - | si |
| -0.60 | 1.748318 | 1.909478 | -0.161160 | 52 | 55 | - | - | si |
| -0.55 | 1.748318 | 1.906271 | -0.157954 | 52 | 46 | - | - | si |
| -0.50 | 1.748318 | 1.903028 | -0.154710 | 52 | 47 | - | - | si |
| -0.45 | 1.748318 | 1.899748 | -0.151430 | 52 | 39 | - | - | si |
| -0.40 | 1.748318 | 1.896429 | -0.148111 | 52 | 36 | - | - | si |
| -0.35 | 1.748318 | 1.893071 | -0.144753 | 52 | 34 | - | - | si |
| -0.30 | 1.748318 | 1.889672 | -0.141354 | 52 | 32 | - | - | si |
| -0.25 | 1.748318 | 1.886233 | -0.137915 | 52 | 29 | - | - | si |
| -0.20 | 1.748318 | 1.882751 | -0.134433 | 52 | 38 | - | - | si |
| -0.15 | 1.748318 | 1.879225 | -0.130907 | 52 | 44 | - | - | si |
| -0.10 | 1.748318 | 1.875655 | -0.127337 | 52 | 48 | - | - | si |
| -0.05 | 1.748318 | 1.872039 | -0.123721 | 52 | 53 | - | - | si |
| 0.00 | 1.748318 | 1.868376 | -0.120058 | 52 | 57 | - | - | si |
| 0.05 | 1.748318 | 1.864665 | -0.116347 | 52 | 61 | - | - | si |
| 0.10 | 1.748318 | 1.860903 | -0.112586 | 52 | 65 | - | - | si |
| 0.15 | 1.748318 | 1.857091 | -0.108773 | 52 | 68 | - | - | si |
| 0.20 | 1.748318 | 1.853226 | -0.104908 | 52 | 72 | - | - | si |
| 0.25 | 1.748318 | 1.849306 | -0.100988 | 52 | 76 | - | - | si |
| 0.30 | 1.748318 | 1.845331 | -0.097013 | 52 | 79 | - | - | si |
| 0.35 | 1.748318 | 1.841298 | -0.092980 | 52 | 83 r | - | - | si |
| 0.40 | 1.748318 | 1.837205 | -0.088887 | 52 | 86 r | - | - | si |
| 0.45 | 1.748318 | 1.833051 | -0.084733 | 52 | 88 r | - | - | si |
| 0.50 | 1.748318 | 1.828833 | -0.080515 | 52 | 90 r | - | - | si |
| 0.55 | 1.748318 | 1.824550 | -0.076232 | 52 | 92 r | - | - | si |
| 0.60 | 1.748318 | 1.820200 | -0.071882 | 52 | 96 r | - | - | si |
| 0.65 | 1.748318 | 1.815779 | -0.067461 | 52 | 100 r | - | - | si |
| 0.70 | 1.748318 | 1.811285 | -0.062968 | 52 | 102 r | - | - | si |
| 0.75 | 1.748318 | 1.806717 | -0.058399 | 52 | 106 r | - | - | si |
| 0.80 | 1.748318 | 1.802071 | -0.053753 | 52 | 108 r | - | - | si |
| 0.85 | 1.748318 | 1.797344 | -0.049026 | 52 | 112 r | - | - | si |
| 0.90 | 1.748318 | 1.792533 | -0.044215 | 52 | 116 r | - | - | si |
| 0.95 | 1.748318 | 1.787635 | -0.039317 | 52 | 126 r | - | - | si |
| 1.00 | 1.748318 | 1.782646 | -0.034328 | 52 | 132 r | - | - | si |
| 1.05 | 1.748318 | 1.777563 | -0.029245 | 52 | 132 r | - | - | si |
| 1.10 | 1.748318 | 1.772382 | -0.024064 | 52 | 155 r | - | - | si |
| 1.15 | 1.748318 | 1.767098 | -0.018780 | 52 | 181 r | - | - | si |
| 1.20 | 1.748318 | 1.761707 | -0.013390 | 52 | 221 r | - | - | si |
| 1.25 | 1.748318 | 1.756205 | -0.007887 | 52 | 273 r | - | - | si |
| 1.30 | 1.748318 | - | - | 52 | - | - | nula | si |
| 1.35 | 1.748318 | - | - | 52 | - | - | nula | si |
| 1.40 | 1.748318 | - | - | 52 | - | - | nula | si |
| 1.45 | 1.748318 | - | - | 52 | - | - | nula | si |
| 1.50 | 1.748318 | - | - | 52 | - | - | nula | si |
| 1.55 | 1.748318 | - | - | 52 | - | - | nula | si |
| 1.60 | 1.748318 | - | - | 52 | - | - | nula | no |
| 1.65 | 1.748318 | - | - | 52 | - | - | nula | no |
| 1.70 | 1.748318 | - | - | 52 | - | - | nula | no |
| 1.75 | 1.748318 | - | - | 52 | - | - | nula | no |
| 1.80 | - | - | - | 49 | - | empuje | nula | si |
| 1.85 | - | - | - | 39 | - | empuje | nula | si |
| 1.90 | - | - | - | 33 | - | empuje | nula | si |
| 1.95 | - | - | - | 28 | - | empuje | nula | no |
| 2.00 | - | - | - | 25 | - | empuje | nula | si |
| 2.05 | - | - | - | 23 | - | empuje | nula | si |
| 2.10 | - | - | - | 21 | - | empuje | nula | si |
| 2.15 | - | - | - | 19 | - | empuje | nula | si |
| 2.20 | - | - | - | 18 | - | empuje | nula | no |
| 2.25 | - | - | - | 16 | - | empuje | nula | no |
| 2.30 | - | - | - | 15 | - | empuje | nula | si |
| 2.35 | - | - | - | 15 | - | empuje | nula | si |
| 2.40 | - | - | - | 14 | - | empuje | nula | no |
| 2.45 | - | - | - | 13 | - | empuje | nula | si |
| 2.50 | - | - | - | 13 | - | empuje | nula | si |
| 2.55 | - | - | - | 12 | - | empuje | nula | no |
| 2.60 | - | - | - | 12 | - | empuje | nula | no |
| 2.65 | - | - | - | 11 | - | empuje | nula | si |
| 2.70 | - | - | - | 11 | - | empuje | nula | si |
| 2.75 | - | - | - | 11 | - | empuje | nula | si |
| 2.80 | - | - | - | 10 | - | empuje | nula | no |
| 2.85 | - | - | - | 10 | - | empuje | nula | no |
| 2.90 | - | - | - | 10 | - | empuje | nula | no |
| 2.95 | - | - | - | 9 | - | empuje | nula | si |
| 3.00 | - | - | - | 9 | - | empuje | nula | si |

### gle · 45 grados · ancla pasiva

- **Forma cerrada** 1.308737259 · **F_f** 1.308737259 (-2.9e-11) · 101 filas, 88 usables · min |g| 6.144e-05 en lambda 0.20
- **Motor**: fos 1.308767979 · converged si · lambda 0.2000 · reserva si · residuo 6.144e-05 · reason `-`
- **Muertes de la rama de momentos**: nula 11 · empuje 0 · presupuesto 2 · estancamiento 0

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | 1.308737 | 1.271017 | +0.037720 | 52 | 158 r | - | - | no |
| -1.95 | 1.308737 | 1.273547 | +0.035190 | 52 | 109 r | - | - | no |
| -1.90 | 1.308737 | 1.275861 | +0.032876 | 52 | 111 r | - | - | no |
| -1.85 | 1.308737 | 1.277985 | +0.030753 | 52 | 111 r | - | - | no |
| -1.80 | 1.308737 | 1.279938 | +0.028799 | 52 | 112 r | - | - | no |
| -1.75 | 1.308737 | 1.281740 | +0.026998 | 52 | 73 | - | - | no |
| -1.70 | 1.308737 | 1.283406 | +0.025331 | 52 | 73 | - | - | no |
| -1.65 | 1.308737 | 1.284951 | +0.023786 | 52 | 73 | - | - | no |
| -1.60 | 1.308737 | 1.286387 | +0.022351 | 52 | 59 | - | - | no |
| -1.55 | 1.308737 | 1.287724 | +0.021013 | 52 | 64 | - | - | no |
| -1.50 | 1.308737 | 1.288974 | +0.019764 | 52 | 60 | - | - | no |
| -1.45 | 1.308737 | 1.290143 | +0.018594 | 52 | 55 | - | - | no |
| -1.40 | 1.308737 | 1.291239 | +0.017498 | 52 | 56 | - | - | no |
| -1.35 | 1.308737 | 1.292270 | +0.016467 | 52 | 51 | - | - | no |
| -1.30 | 1.308737 | 1.293241 | +0.015496 | 52 | 51 | - | - | no |
| -1.25 | 1.308737 | 1.294157 | +0.014580 | 52 | 51 | - | - | no |
| -1.20 | 1.308737 | 1.295023 | +0.013715 | 52 | 47 | - | - | no |
| -1.15 | 1.308737 | 1.295843 | +0.012895 | 52 | 47 | - | - | no |
| -1.10 | 1.308737 | 1.296621 | +0.012117 | 52 | 43 | - | - | no |
| -1.05 | 1.308737 | 1.297360 | +0.011378 | 52 | 39 | - | - | no |
| -1.00 | 1.308737 | 1.298063 | +0.010674 | 52 | 40 | - | - | no |
| -0.95 | 1.308737 | 1.298733 | +0.010004 | 52 | 35 | - | - | no |
| -0.90 | 1.308737 | 1.299373 | +0.009364 | 52 | 36 | - | - | no |
| -0.85 | 1.308737 | 1.299985 | +0.008752 | 52 | 37 | - | - | no |
| -0.80 | 1.308737 | 1.300570 | +0.008167 | 52 | 33 | - | - | no |
| -0.75 | 1.308737 | 1.301131 | +0.007606 | 52 | 34 | - | - | no |
| -0.70 | 1.308737 | 1.301670 | +0.007067 | 52 | 31 | - | - | no |
| -0.65 | 1.308737 | 1.302187 | +0.006550 | 52 | 31 | - | - | no |
| -0.60 | 1.308737 | 1.302685 | +0.006052 | 52 | 30 | - | - | no |
| -0.55 | 1.308737 | 1.303165 | +0.005572 | 52 | 29 | - | - | no |
| -0.50 | 1.308737 | 1.303627 | +0.005110 | 52 | 32 | - | - | no |
| -0.45 | 1.308737 | 1.304074 | +0.004663 | 52 | 36 | - | - | no |
| -0.40 | 1.308737 | 1.304505 | +0.004232 | 52 | 39 | - | - | no |
| -0.35 | 1.308737 | 1.304923 | +0.003814 | 52 | 42 | - | - | no |
| -0.30 | 1.308737 | 1.305327 | +0.003410 | 52 | 44 | - | - | no |
| -0.25 | 1.308737 | 1.305719 | +0.003018 | 52 | 46 | - | - | no |
| -0.20 | 1.308737 | 1.306099 | +0.002638 | 52 | 48 | - | - | no |
| -0.15 | 1.308737 | 1.306469 | +0.002269 | 52 | 50 | - | - | no |
| -0.10 | 1.308737 | 1.306828 | +0.001909 | 52 | 52 | - | - | no |
| -0.05 | 1.308737 | 1.307177 | +0.001560 | 52 | 54 | - | - | no |
| 0.00 | 1.308737 | 1.307518 | +0.001219 | 52 | 56 | - | - | no |
| 0.05 | 1.308737 | 1.307850 | +0.000888 | 52 | 58 | - | - | no |
| 0.10 | 1.308737 | 1.308173 | +0.000564 | 52 | 59 | - | - | no |
| 0.15 | 1.308737 | 1.308490 | +0.000248 | 52 | 61 | - | - | si |
| 0.20 | 1.308737 | 1.308799 | -0.000061 | 52 | 63 | - | - | si |
| 0.25 | 1.308737 | 1.309101 | -0.000364 | 52 | 65 | - | - | si |
| 0.30 | 1.308737 | 1.309397 | -0.000660 | 52 | 67 | - | - | si |
| 0.35 | 1.308737 | 1.309687 | -0.000950 | 52 | 68 | - | - | si |
| 0.40 | 1.308737 | 1.309971 | -0.001234 | 52 | 70 | - | - | si |
| 0.45 | 1.308737 | 1.310250 | -0.001513 | 52 | 72 | - | - | si |
| 0.50 | 1.308737 | 1.310524 | -0.001787 | 52 | 74 | - | - | si |
| 0.55 | 1.308737 | 1.310793 | -0.002056 | 52 | 75 | - | - | si |
| 0.60 | 1.308737 | 1.311058 | -0.002320 | 52 | 77 | - | - | si |
| 0.65 | 1.308737 | 1.311318 | -0.002581 | 52 | 79 | - | - | si |
| 0.70 | 1.308737 | 1.311575 | -0.002837 | 52 | 82 r | - | - | si |
| 0.75 | 1.308737 | 1.311827 | -0.003090 | 52 | 83 r | - | - | si |
| 0.80 | 1.308737 | 1.312077 | -0.003339 | 52 | 85 r | - | - | si |
| 0.85 | 1.308737 | 1.312323 | -0.003585 | 52 | 86 r | - | - | si |
| 0.90 | 1.308737 | 1.312566 | -0.003828 | 52 | 86 r | - | - | si |
| 0.95 | 1.308737 | 1.312806 | -0.004068 | 52 | 88 r | - | - | si |
| 1.00 | 1.308737 | 1.313043 | -0.004306 | 52 | 88 r | - | - | si |
| 1.05 | 1.308737 | 1.313278 | -0.004541 | 52 | 89 r | - | - | si |
| 1.10 | 1.308737 | 1.313510 | -0.004773 | 52 | 90 r | - | - | si |
| 1.15 | 1.308737 | 1.313741 | -0.005003 | 52 | 92 r | - | - | si |
| 1.20 | 1.308737 | 1.313969 | -0.005232 | 52 | 94 r | - | - | si |
| 1.25 | 1.308737 | 1.314195 | -0.005458 | 52 | 96 r | - | - | si |
| 1.30 | 1.308737 | 1.314420 | -0.005683 | 52 | 98 r | - | - | si |
| 1.35 | 1.308737 | 1.314643 | -0.005906 | 52 | 100 r | - | - | si |
| 1.40 | 1.308737 | 1.314865 | -0.006128 | 52 | 102 r | - | - | si |
| 1.45 | 1.308737 | 1.315086 | -0.006348 | 52 | 103 r | - | - | si |
| 1.50 | 1.308737 | 1.315305 | -0.006568 | 52 | 105 r | - | - | si |
| 1.55 | 1.308737 | 1.315523 | -0.006786 | 52 | 107 r | - | - | si |
| 1.60 | 1.308737 | 1.315741 | -0.007003 | 52 | 109 r | - | - | si |
| 1.65 | 1.308737 | 1.315957 | -0.007220 | 52 | 111 r | - | - | si |
| 1.70 | 1.308737 | 1.316173 | -0.007436 | 52 | 114 r | - | - | si |
| 1.75 | 1.308737 | 1.316389 | -0.007651 | 52 | 116 r | - | - | si |
| 1.80 | 1.308737 | 1.316604 | -0.007866 | 52 | 119 r | - | - | si |
| 1.85 | 1.308737 | 1.316818 | -0.008081 | 52 | 122 r | - | - | si |
| 1.90 | 1.308737 | 1.317033 | -0.008296 | 52 | 128 r | - | - | si |
| 1.95 | 1.308737 | 1.317247 | -0.008510 | 52 | 132 r | - | - | si |
| 2.00 | 1.308737 | 1.317462 | -0.008725 | 52 | 132 r | - | - | si |
| 2.05 | 1.308737 | 1.317676 | -0.008939 | 52 | 142 r | - | - | si |
| 2.10 | 1.308737 | 1.317891 | -0.009154 | 52 | 156 r | - | - | si |
| 2.15 | 1.308737 | 1.318106 | -0.009369 | 52 | 175 r | - | - | si |
| 2.20 | 1.308737 | 1.318322 | -0.009585 | 52 | 200 r | - | - | si |
| 2.25 | 1.308737 | 1.318538 | -0.009801 | 52 | 232 r | - | - | si |
| 2.30 | 1.308737 | 1.318755 | -0.010018 | 52 | 276 r | - | - | si |
| 2.35 | 1.308737 | 1.318973 | -0.010235 | 52 | 342 r | - | - | si |
| 2.40 | 1.308737 | - | - | 52 | 400 | - | presupuesto | si |
| 2.45 | 1.308737 | - | - | 52 | 400 | - | presupuesto | si |
| 2.50 | 1.308737 | - | - | 52 | - | - | nula | si |
| 2.55 | 1.308737 | - | - | 52 | - | - | nula | si |
| 2.60 | 1.308737 | - | - | 52 | - | - | nula | si |
| 2.65 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.70 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.75 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.80 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.85 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.90 | 1.308737 | - | - | 52 | - | - | nula | no |
| 2.95 | 1.308737 | - | - | 52 | - | - | nula | no |
| 3.00 | 1.308737 | - | - | 52 | - | - | nula | no |

### gle · 50 grados · ancla sin ancla

- **Forma cerrada** 0.941982760 · **F_f** 0.941982760 (+6.5e-11) · 101 filas, 100 usables · min |g| 0.0009742 en lambda 1.45
- **Motor**: fos 0.941982760 · converged si · lambda 1.4304 · reserva no · residuo - · reason `-`
- **Muertes de la rama de momentos**: nula 1 · empuje 0 · presupuesto 0 · estancamiento 0

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | 0.941983 | 1.102795 | -0.160812 | 59 | 109 r | - | - | si |
| -1.95 | 0.941983 | 1.097621 | -0.155639 | 59 | 75 | - | - | si |
| -1.90 | 0.941983 | 1.092997 | -0.151014 | 59 | 75 | - | - | si |
| -1.85 | 0.941983 | 1.088790 | -0.146807 | 59 | 75 | - | - | si |
| -1.80 | 0.941983 | 1.084913 | -0.142931 | 59 | 75 | - | - | si |
| -1.75 | 0.941983 | 1.081304 | -0.139321 | 59 | 70 | - | - | si |
| -1.70 | 0.941983 | 1.077914 | -0.135931 | 59 | 64 | - | - | si |
| -1.65 | 0.941983 | 1.074710 | -0.132727 | 59 | 47 | - | - | si |
| -1.60 | 0.941983 | 1.071663 | -0.129680 | 59 | 53 | - | - | si |
| -1.55 | 0.941983 | 1.068751 | -0.126768 | 59 | 59 | - | - | si |
| -1.50 | 0.941983 | 1.065956 | -0.123974 | 59 | 59 | - | - | si |
| -1.45 | 0.941983 | 1.063264 | -0.121282 | 59 | 54 | - | - | si |
| -1.40 | 0.941983 | 1.060662 | -0.118680 | 59 | 54 | - | - | si |
| -1.35 | 0.941983 | 1.058140 | -0.116157 | 59 | 49 | - | - | si |
| -1.30 | 0.941983 | 1.055689 | -0.113706 | 59 | 49 | - | - | si |
| -1.25 | 0.941983 | 1.053300 | -0.111317 | 59 | 45 | - | - | si |
| -1.20 | 0.941983 | 1.050968 | -0.108985 | 59 | 45 | - | - | si |
| -1.15 | 0.941983 | 1.048686 | -0.106703 | 59 | 40 | - | - | si |
| -1.10 | 0.941983 | 1.046449 | -0.104466 | 59 | 41 | - | - | si |
| -1.05 | 0.941983 | 1.044253 | -0.102270 | 59 | 41 | - | - | si |
| -1.00 | 0.941983 | 1.042094 | -0.100111 | 59 | 37 | - | - | si |
| -0.95 | 0.941983 | 1.039967 | -0.097984 | 59 | 37 | - | - | si |
| -0.90 | 0.941983 | 1.037870 | -0.095887 | 59 | 33 | - | - | si |
| -0.85 | 0.941983 | 1.035799 | -0.093816 | 59 | 34 | - | - | si |
| -0.80 | 0.941983 | 1.033752 | -0.091769 | 59 | 30 | - | - | si |
| -0.75 | 0.941983 | 1.031726 | -0.089743 | 59 | 32 | - | - | si |
| -0.70 | 0.941983 | 1.029719 | -0.087736 | 59 | 30 | - | - | si |
| -0.65 | 0.941983 | 1.027729 | -0.085746 | 59 | 32 | - | - | si |
| -0.60 | 0.941983 | 1.025753 | -0.083770 | 59 | 36 | - | - | si |
| -0.55 | 0.941983 | 1.023790 | -0.081807 | 59 | 39 | - | - | si |
| -0.50 | 0.941983 | 1.021838 | -0.079855 | 59 | 41 | - | - | si |
| -0.45 | 0.941983 | 1.019896 | -0.077913 | 59 | 44 | - | - | si |
| -0.40 | 0.941983 | 1.017961 | -0.075978 | 59 | 45 | - | - | si |
| -0.35 | 0.941983 | 1.016033 | -0.074050 | 59 | 47 | - | - | si |
| -0.30 | 0.941983 | 1.014109 | -0.072126 | 59 | 49 | - | - | si |
| -0.25 | 0.941983 | 1.012189 | -0.070207 | 59 | 50 | - | - | si |
| -0.20 | 0.941983 | 1.010272 | -0.068289 | 59 | 52 | - | - | si |
| -0.15 | 0.941983 | 1.008355 | -0.066373 | 59 | 53 | - | - | si |
| -0.10 | 0.941983 | 1.006439 | -0.064456 | 59 | 54 | - | - | si |
| -0.05 | 0.941983 | 1.004521 | -0.062538 | 59 | 54 | - | - | si |
| 0.00 | 0.941983 | 1.002601 | -0.060618 | 59 | 53 | - | - | si |
| 0.05 | 0.941983 | 1.000677 | -0.058695 | 59 | 38 | - | - | si |
| 0.10 | 0.941983 | 0.998749 | -0.056766 | 59 | 57 | - | - | si |
| 0.15 | 0.941983 | 0.996815 | -0.054832 | 59 | 61 | - | - | si |
| 0.20 | 0.941983 | 0.994875 | -0.052892 | 59 | 64 | - | - | si |
| 0.25 | 0.941983 | 0.992926 | -0.050944 | 59 | 66 | - | - | si |
| 0.30 | 0.941983 | 0.990969 | -0.048986 | 59 | 69 | - | - | si |
| 0.35 | 0.941983 | 0.989002 | -0.047020 | 59 | 71 | - | - | si |
| 0.40 | 0.941983 | 0.987025 | -0.045042 | 59 | 74 | - | - | si |
| 0.45 | 0.941983 | 0.985035 | -0.043052 | 59 | 76 | - | - | si |
| 0.50 | 0.941983 | 0.983033 | -0.041050 | 59 | 78 | - | - | si |
| 0.55 | 0.941983 | 0.981017 | -0.039034 | 59 | 82 r | - | - | si |
| 0.60 | 0.941983 | 0.978985 | -0.037003 | 59 | 83 r | - | - | si |
| 0.65 | 0.941983 | 0.976938 | -0.034955 | 59 | 85 r | - | - | si |
| 0.70 | 0.941983 | 0.974874 | -0.032891 | 59 | 85 r | - | - | si |
| 0.75 | 0.941983 | 0.972791 | -0.030808 | 59 | 86 r | - | - | si |
| 0.80 | 0.941983 | 0.970689 | -0.028706 | 59 | 87 r | - | - | si |
| 0.85 | 0.941983 | 0.968566 | -0.026583 | 59 | 88 r | - | - | si |
| 0.90 | 0.941983 | 0.966422 | -0.024439 | 59 | 89 r | - | - | si |
| 0.95 | 0.941983 | 0.964254 | -0.022272 | 59 | 90 r | - | - | si |
| 1.00 | 0.941983 | 0.962063 | -0.020080 | 59 | 91 r | - | - | si |
| 1.05 | 0.941983 | 0.959846 | -0.017863 | 59 | 92 r | - | - | si |
| 1.10 | 0.941983 | 0.957601 | -0.015619 | 59 | 94 r | - | - | si |
| 1.15 | 0.941983 | 0.955329 | -0.013346 | 59 | 96 r | - | - | si |
| 1.20 | 0.941983 | 0.953026 | -0.011044 | 59 | 99 r | - | - | si |
| 1.25 | 0.941983 | 0.950692 | -0.008710 | 59 | 101 r | - | - | si |
| 1.30 | 0.941983 | 0.948325 | -0.006343 | 59 | 102 r | - | - | si |
| 1.35 | 0.941983 | 0.945924 | -0.003941 | 59 | 103 r | - | - | si |
| 1.40 | 0.941983 | 0.943485 | -0.001503 | 59 | 105 r | - | - | si |
| 1.45 | 0.941983 | 0.941009 | +0.000974 | 59 | 107 r | - | - | si |
| 1.50 | 0.941983 | 0.938491 | +0.003491 | 59 | 108 r | - | - | si |
| 1.55 | 0.941983 | 0.935931 | +0.006051 | 59 | 109 r | - | - | si |
| 1.60 | 0.941983 | 0.933327 | +0.008656 | 59 | 112 r | - | - | si |
| 1.65 | 0.941983 | 0.930675 | +0.011308 | 59 | 114 r | - | - | si |
| 1.70 | 0.941983 | 0.927973 | +0.014009 | 59 | 116 r | - | - | si |
| 1.75 | 0.941983 | 0.925219 | +0.016764 | 59 | 120 r | - | - | si |
| 1.80 | 0.941983 | 0.922410 | +0.019573 | 59 | 123 r | - | - | si |
| 1.85 | 0.941983 | 0.919542 | +0.022441 | 59 | 127 r | - | - | si |
| 1.90 | 0.941983 | 0.916612 | +0.025371 | 59 | 129 r | - | - | si |
| 1.95 | 0.941983 | 0.913617 | +0.028366 | 59 | 133 r | - | - | si |
| 2.00 | 0.941983 | 0.910552 | +0.031431 | 59 | 135 r | - | - | si |
| 2.05 | 0.941983 | 0.907414 | +0.034569 | 59 | 137 r | - | - | si |
| 2.10 | 0.941983 | 0.904197 | +0.037785 | 59 | 138 r | - | - | si |
| 2.15 | 0.941983 | 0.900898 | +0.041085 | 59 | 146 r | - | - | si |
| 2.20 | 0.941983 | 0.897509 | +0.044474 | 59 | 152 r | - | - | si |
| 2.25 | 0.941983 | 0.894026 | +0.047957 | 59 | 156 r | - | - | si |
| 2.30 | 0.941983 | 0.890441 | +0.051542 | 59 | 162 r | - | - | si |
| 2.35 | 0.941983 | 0.886747 | +0.055236 | 59 | 168 r | - | - | si |
| 2.40 | 0.941983 | 0.882935 | +0.059047 | 59 | 174 r | - | - | si |
| 2.45 | 0.941983 | 0.878998 | +0.062985 | 59 | 182 r | - | - | si |
| 2.50 | 0.941983 | 0.874923 | +0.067060 | 59 | 188 r | - | - | si |
| 2.55 | 0.941983 | 0.870699 | +0.071284 | 59 | 199 r | - | - | si |
| 2.60 | 0.941983 | 0.866313 | +0.075670 | 59 | 214 r | - | - | si |
| 2.65 | 0.941983 | 0.861750 | +0.080233 | 59 | 219 r | - | - | si |
| 2.70 | 0.941983 | 0.856991 | +0.084992 | 59 | 239 r | - | - | si |
| 2.75 | 0.941983 | 0.852016 | +0.089967 | 59 | 255 r | - | - | si |
| 2.80 | 0.941983 | 0.846801 | +0.095182 | 59 | 273 r | - | - | si |
| 2.85 | 0.941983 | 0.841316 | +0.100667 | 59 | 291 r | - | - | si |
| 2.90 | 0.941983 | 0.835526 | +0.106457 | 59 | 311 r | - | - | si |
| 2.95 | 0.941983 | 0.829388 | +0.112595 | 59 | 341 r | - | - | si |
| 3.00 | 0.941983 | - | - | 59 | - | - | nula | si |

### gle · 50 grados · ancla activa

- **Forma cerrada** 2.757457925 · **F_f** 2.757457925 (+4.3e-13) · 101 filas, 46 usables · min |g| 0.159 en lambda 1.15
- **Motor**: fos 2.855669731 · converged no · lambda 1.0000 · reserva si · residuo 0.1964 · reason `no_lambda_bracket`
- **Muertes de la rama de momentos**: nula 55 · empuje 0 · presupuesto 0 · estancamiento 0

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | - | - | - | 9 | - | empuje | nula | si |
| -1.95 | - | - | - | 9 | - | empuje | nula | si |
| -1.90 | - | - | - | 9 | - | empuje | nula | si |
| -1.85 | - | - | - | 10 | - | empuje | nula | si |
| -1.80 | - | - | - | 10 | - | empuje | nula | si |
| -1.75 | - | - | - | 11 | - | empuje | nula | si |
| -1.70 | - | - | - | 12 | - | empuje | nula | si |
| -1.65 | - | - | - | 12 | - | empuje | nula | si |
| -1.60 | - | - | - | 13 | - | empuje | nula | si |
| -1.55 | - | - | - | 15 | - | empuje | nula | si |
| -1.50 | - | - | - | 16 | - | empuje | nula | si |
| -1.45 | - | - | - | 19 | - | empuje | nula | si |
| -1.40 | - | - | - | 23 | - | empuje | nula | si |
| -1.35 | - | - | - | 30 | - | empuje | nula | si |
| -1.30 | 2.757458 | - | - | 48 | - | - | nula | no |
| -1.25 | 2.757458 | - | - | 48 | - | - | nula | si |
| -1.20 | 2.757458 | - | - | 48 | - | - | nula | si |
| -1.15 | 2.757458 | - | - | 48 | - | - | nula | si |
| -1.10 | 2.757458 | 3.259395 | -0.501937 | 48 | 242 r | - | - | si |
| -1.05 | 2.757458 | 3.388487 | -0.631029 | 48 | 199 r | - | - | si |
| -1.00 | 2.757458 | 3.470434 | -0.712976 | 48 | 134 r | - | - | si |
| -0.95 | 2.757458 | 3.515292 | -0.757834 | 48 | 108 r | - | - | si |
| -0.90 | 2.757458 | 3.535179 | -0.777721 | 48 | 95 r | - | - | si |
| -0.85 | 2.757458 | 3.539325 | -0.781867 | 48 | 76 | - | - | si |
| -0.80 | 2.757458 | 3.533757 | -0.776299 | 48 | 70 | - | - | si |
| -0.75 | 2.757458 | 3.522225 | -0.764767 | 48 | 65 | - | - | si |
| -0.70 | 2.757458 | 3.507045 | -0.749587 | 48 | 60 | - | - | si |
| -0.65 | 2.757458 | 3.489662 | -0.732204 | 48 | 55 | - | - | si |
| -0.60 | 2.757458 | 3.470989 | -0.713532 | 48 | 50 | - | - | si |
| -0.55 | 2.757458 | 3.451614 | -0.694156 | 48 | 45 | - | - | si |
| -0.50 | 2.757458 | 3.431915 | -0.674457 | 48 | 45 | - | - | si |
| -0.45 | 2.757458 | 3.412140 | -0.654683 | 48 | 41 | - | - | si |
| -0.40 | 2.757458 | 3.392453 | -0.634995 | 48 | 38 | - | - | si |
| -0.35 | 2.757458 | 3.372959 | -0.615501 | 48 | 35 | - | - | si |
| -0.30 | 2.757458 | 3.353723 | -0.596266 | 48 | 32 | - | - | si |
| -0.25 | 2.757458 | 3.334789 | -0.577331 | 48 | 28 | - | - | si |
| -0.20 | 2.757458 | 3.316180 | -0.558722 | 48 | 38 | - | - | si |
| -0.15 | 2.757458 | 3.297908 | -0.540450 | 48 | 43 | - | - | si |
| -0.10 | 2.757458 | 3.279976 | -0.522519 | 48 | 46 | - | - | si |
| -0.05 | 2.757458 | 3.262383 | -0.504925 | 48 | 49 | - | - | si |
| 0.00 | 2.757458 | 3.245123 | -0.487665 | 48 | 52 | - | - | si |
| 0.05 | 2.757458 | 3.228188 | -0.470730 | 48 | 55 | - | - | si |
| 0.10 | 2.757458 | 3.211567 | -0.454109 | 48 | 58 | - | - | si |
| 0.15 | 2.757458 | 3.195250 | -0.437792 | 48 | 60 | - | - | si |
| 0.20 | 2.757458 | 3.179225 | -0.421767 | 48 | 63 | - | - | si |
| 0.25 | 2.757458 | 3.163482 | -0.406024 | 48 | 65 | - | - | si |
| 0.30 | 2.757458 | 3.148007 | -0.390549 | 48 | 67 | - | - | si |
| 0.35 | 2.757458 | 3.132791 | -0.375333 | 48 | 69 | - | - | si |
| 0.40 | 2.757458 | 3.117821 | -0.360363 | 48 | 71 | - | - | si |
| 0.45 | 2.757458 | 3.103087 | -0.345629 | 48 | 73 | - | - | si |
| 0.50 | 2.757458 | 3.088579 | -0.331121 | 48 | 76 | - | - | si |
| 0.55 | 2.757458 | 3.074286 | -0.316828 | 48 | 78 | - | - | si |
| 0.60 | 2.757458 | 3.060199 | -0.302741 | 48 | 80 | - | - | si |
| 0.65 | 2.757458 | 3.046308 | -0.288850 | 48 | 83 r | - | - | si |
| 0.70 | 2.757458 | 3.032605 | -0.275147 | 48 | 85 r | - | - | si |
| 0.75 | 2.757458 | 3.019081 | -0.261623 | 48 | 87 r | - | - | si |
| 0.80 | 2.757458 | 3.005729 | -0.248271 | 48 | 88 r | - | - | si |
| 0.85 | 2.757458 | 2.992540 | -0.235082 | 48 | 90 r | - | - | si |
| 0.90 | 2.757458 | 2.979507 | -0.222049 | 48 | 97 r | - | - | si |
| 0.95 | 2.757458 | 2.966623 | -0.209165 | 48 | 113 r | - | - | si |
| 1.00 | 2.757458 | 2.953882 | -0.196424 | 48 | 141 r | - | - | si |
| 1.05 | 2.757458 | 2.941276 | -0.183818 | 48 | 181 r | - | - | si |
| 1.10 | 2.757458 | 2.928801 | -0.171343 | 48 | 241 r | - | - | si |
| 1.15 | 2.757458 | 2.916450 | -0.158992 | 48 | 363 r | - | - | si |
| 1.20 | 2.757458 | - | - | 48 | - | - | nula | si |
| 1.25 | 2.757458 | - | - | 48 | - | - | nula | si |
| 1.30 | 2.757458 | - | - | 48 | - | - | nula | si |
| 1.35 | 2.757458 | - | - | 48 | - | - | nula | no |
| 1.40 | 2.757458 | - | - | 48 | - | - | nula | no |
| 1.45 | - | - | - | 47 | - | empuje | nula | si |
| 1.50 | - | - | - | 36 | - | empuje | nula | no |
| 1.55 | - | - | - | 30 | - | empuje | nula | no |
| 1.60 | - | - | - | 25 | - | empuje | nula | si |
| 1.65 | - | - | - | 22 | - | empuje | nula | no |
| 1.70 | - | - | - | 20 | - | empuje | nula | no |
| 1.75 | - | - | - | 18 | - | empuje | nula | no |
| 1.80 | - | - | - | 17 | - | empuje | nula | si |
| 1.85 | - | - | - | 15 | - | empuje | nula | si |
| 1.90 | - | - | - | 14 | - | empuje | nula | no |
| 1.95 | - | - | - | 14 | - | empuje | nula | no |
| 2.00 | - | - | - | 13 | - | empuje | nula | si |
| 2.05 | - | - | - | 12 | - | empuje | nula | no |
| 2.10 | - | - | - | 12 | - | empuje | nula | no |
| 2.15 | - | - | - | 11 | - | empuje | nula | si |
| 2.20 | - | - | - | 11 | - | empuje | nula | si |
| 2.25 | - | - | - | 10 | - | empuje | nula | no |
| 2.30 | - | - | - | 10 | - | empuje | nula | no |
| 2.35 | - | - | - | 10 | - | empuje | nula | no |
| 2.40 | - | - | - | 9 | - | empuje | nula | si |
| 2.45 | - | - | - | 9 | - | empuje | nula | si |
| 2.50 | - | - | - | 9 | - | empuje | nula | si |
| 2.55 | - | - | - | 9 | - | empuje | nula | si |
| 2.60 | - | - | - | 8 | - | empuje | nula | no |
| 2.65 | - | - | - | 8 | - | empuje | nula | no |
| 2.70 | - | - | - | 8 | - | empuje | nula | no |
| 2.75 | - | - | - | 8 | - | empuje | nula | no |
| 2.80 | - | - | - | 8 | - | empuje | nula | no |
| 2.85 | - | - | - | 8 | - | empuje | nula | no |
| 2.90 | - | - | - | 7 | - | empuje | nula | si |
| 2.95 | - | - | - | 7 | - | empuje | nula | si |
| 3.00 | - | - | - | 7 | - | empuje | nula | si |

### gle · 50 grados · ancla pasiva

- **Forma cerrada** 1.748317883 · **F_f** 1.748317883 (-1.9e-11) · 101 filas, 59 usables · min |g| 0.01735 en lambda 1.50
- **Motor**: fos 1.756993023 · converged si · lambda 1.5000 · reserva si · residuo 0.01735 · reason `-`
- **Muertes de la rama de momentos**: nula 33 · empuje 4 · presupuesto 1 · estancamiento 4

| λ | F_f | F_m | g = F_f − F_m | pasadas_f | pasadas_m | motivo_f | motivo_m | admisible |
|---|---|---|---|---|---|---|---|---|
| -2.00 | - | - | - | 15 | - | empuje | nula | si |
| -1.95 | - | - | - | 17 | - | empuje | nula | si |
| -1.90 | - | - | - | 18 | - | empuje | nula | si |
| -1.85 | - | - | - | 21 | 8 | empuje | empuje | si |
| -1.80 | - | - | - | 24 | 9 | empuje | empuje | si |
| -1.75 | - | - | - | 30 | 11 | empuje | empuje | si |
| -1.70 | - | - | - | 40 | 161 | empuje | estancamiento | si |
| -1.65 | 1.748318 | - | - | 52 | - | - | nula | si |
| -1.60 | 1.748318 | - | - | 52 | 198 | - | estancamiento | si |
| -1.55 | 1.748318 | - | - | 52 | 400 | - | presupuesto | si |
| -1.50 | 1.748318 | - | - | 52 | 163 | - | estancamiento | si |
| -1.45 | 1.748318 | - | - | 52 | 398 | - | estancamiento | si |
| -1.40 | 1.748318 | 1.941225 | -0.192908 | 52 | 268 r | - | - | si |
| -1.35 | 1.748318 | 1.955788 | -0.207470 | 52 | 243 r | - | - | si |
| -1.30 | 1.748318 | 1.962085 | -0.213767 | 52 | 130 r | - | - | si |
| -1.25 | 1.748318 | 1.963735 | -0.215417 | 52 | 120 r | - | - | si |
| -1.20 | 1.748318 | 1.962786 | -0.214468 | 52 | 106 r | - | - | si |
| -1.15 | 1.748318 | 1.960358 | -0.212041 | 52 | 89 r | - | - | si |
| -1.10 | 1.748318 | 1.957073 | -0.208755 | 52 | 71 | - | - | si |
| -1.05 | 1.748318 | 1.953287 | -0.204969 | 52 | 71 | - | - | si |
| -1.00 | 1.748318 | 1.949212 | -0.200894 | 52 | 66 | - | - | si |
| -0.95 | 1.748318 | 1.944977 | -0.196660 | 52 | 61 | - | - | si |
| -0.90 | 1.748318 | 1.940663 | -0.192345 | 52 | 60 | - | - | si |
| -0.85 | 1.748318 | 1.936320 | -0.188002 | 52 | 56 | - | - | si |
| -0.80 | 1.748318 | 1.931980 | -0.183662 | 52 | 51 | - | - | si |
| -0.75 | 1.748318 | 1.927664 | -0.179346 | 52 | 50 | - | - | si |
| -0.70 | 1.748318 | 1.923385 | -0.175067 | 52 | 47 | - | - | si |
| -0.65 | 1.748318 | 1.919149 | -0.170831 | 52 | 37 | - | - | si |
| -0.60 | 1.748318 | 1.914962 | -0.166644 | 52 | 39 | - | - | si |
| -0.55 | 1.748318 | 1.910825 | -0.162508 | 52 | 39 | - | - | si |
| -0.50 | 1.748318 | 1.906740 | -0.158422 | 52 | 30 | - | - | si |
| -0.45 | 1.748318 | 1.902705 | -0.154387 | 52 | 33 | - | - | si |
| -0.40 | 1.748318 | 1.898719 | -0.150401 | 52 | 32 | - | - | si |
| -0.35 | 1.748318 | 1.894781 | -0.146463 | 52 | 30 | - | - | si |
| -0.30 | 1.748318 | 1.890889 | -0.142571 | 52 | 38 | - | - | si |
| -0.25 | 1.748318 | 1.887040 | -0.138723 | 52 | 42 | - | - | si |
| -0.20 | 1.748318 | 1.883233 | -0.134916 | 52 | 46 | - | - | si |
| -0.15 | 1.748318 | 1.879466 | -0.131148 | 52 | 49 | - | - | si |
| -0.10 | 1.748318 | 1.875735 | -0.127417 | 52 | 52 | - | - | si |
| -0.05 | 1.748318 | 1.872039 | -0.123721 | 52 | 54 | - | - | si |
| 0.00 | 1.748318 | 1.868376 | -0.120058 | 52 | 57 | - | - | si |
| 0.05 | 1.748318 | 1.864744 | -0.116426 | 52 | 59 | - | - | si |
| 0.10 | 1.748318 | 1.861140 | -0.112822 | 52 | 62 | - | - | si |
| 0.15 | 1.748318 | 1.857564 | -0.109246 | 52 | 64 | - | - | si |
| 0.20 | 1.748318 | 1.854012 | -0.105694 | 52 | 66 | - | - | si |
| 0.25 | 1.748318 | 1.850483 | -0.102165 | 52 | 68 | - | - | si |
| 0.30 | 1.748318 | 1.846976 | -0.098658 | 52 | 70 | - | - | si |
| 0.35 | 1.748318 | 1.843488 | -0.095170 | 52 | 73 | - | - | si |
| 0.40 | 1.748318 | 1.840019 | -0.091701 | 52 | 75 | - | - | si |
| 0.45 | 1.748318 | 1.836566 | -0.088248 | 52 | 77 | - | - | si |
| 0.50 | 1.748318 | 1.833129 | -0.084811 | 52 | 79 | - | - | si |
| 0.55 | 1.748318 | 1.829705 | -0.081387 | 52 | 82 r | - | - | si |
| 0.60 | 1.748318 | 1.826293 | -0.077975 | 52 | 83 r | - | - | si |
| 0.65 | 1.748318 | 1.822893 | -0.074575 | 52 | 85 r | - | - | si |
| 0.70 | 1.748318 | 1.819502 | -0.071184 | 52 | 86 r | - | - | si |
| 0.75 | 1.748318 | 1.816120 | -0.067802 | 52 | 88 r | - | - | si |
| 0.80 | 1.748318 | 1.812746 | -0.064428 | 52 | 88 r | - | - | si |
| 0.85 | 1.748318 | 1.809377 | -0.061059 | 52 | 90 r | - | - | si |
| 0.90 | 1.748318 | 1.806014 | -0.057696 | 52 | 92 r | - | - | si |
| 0.95 | 1.748318 | 1.802654 | -0.054336 | 52 | 96 r | - | - | si |
| 1.00 | 1.748318 | 1.799297 | -0.050979 | 52 | 100 r | - | - | si |
| 1.05 | 1.748318 | 1.795942 | -0.047625 | 52 | 102 r | - | - | si |
| 1.10 | 1.748318 | 1.792588 | -0.044271 | 52 | 106 r | - | - | si |
| 1.15 | 1.748318 | 1.789234 | -0.040916 | 52 | 108 r | - | - | si |
| 1.20 | 1.748318 | 1.785879 | -0.037561 | 52 | 108 r | - | - | si |
| 1.25 | 1.748318 | 1.782521 | -0.034203 | 52 | 117 r | - | - | si |
| 1.30 | 1.748318 | 1.779161 | -0.030843 | 52 | 137 r | - | - | si |
| 1.35 | 1.748318 | 1.775796 | -0.027478 | 52 | 165 r | - | - | si |
| 1.40 | 1.748318 | 1.772426 | -0.024108 | 52 | 205 r | - | - | si |
| 1.45 | 1.748318 | 1.769051 | -0.020733 | 52 | 267 r | - | - | si |
| 1.50 | 1.748318 | 1.765668 | -0.017350 | 52 | 380 r | - | - | si |
| 1.55 | 1.748318 | - | - | 52 | - | - | nula | si |
| 1.60 | 1.748318 | - | - | 52 | - | - | nula | si |
| 1.65 | 1.748318 | - | - | 52 | - | - | nula | si |
| 1.70 | 1.748318 | - | - | 52 | - | - | nula | no |
| 1.75 | 1.748318 | - | - | 52 | - | - | nula | no |
| 1.80 | 1.748318 | - | - | 52 | - | - | nula | no |
| 1.85 | - | - | - | 45 | - | empuje | nula | si |
| 1.90 | - | - | - | 37 | - | empuje | nula | si |
| 1.95 | - | - | - | 31 | - | empuje | nula | si |
| 2.00 | - | - | - | 27 | - | empuje | nula | si |
| 2.05 | - | - | - | 24 | - | empuje | nula | no |
| 2.10 | - | - | - | 22 | - | empuje | nula | no |
| 2.15 | - | - | - | 20 | - | empuje | nula | no |
| 2.20 | - | - | - | 19 | - | empuje | nula | si |
| 2.25 | - | - | - | 17 | - | empuje | nula | si |
| 2.30 | - | - | - | 16 | - | empuje | nula | no |
| 2.35 | - | - | - | 15 | - | empuje | nula | si |
| 2.40 | - | - | - | 15 | - | empuje | nula | si |
| 2.45 | - | - | - | 14 | - | empuje | nula | no |
| 2.50 | - | - | - | 13 | - | empuje | nula | si |
| 2.55 | - | - | - | 13 | - | empuje | nula | si |
| 2.60 | - | - | - | 12 | - | empuje | nula | no |
| 2.65 | - | - | - | 12 | - | empuje | nula | no |
| 2.70 | - | - | - | 11 | - | empuje | nula | si |
| 2.75 | - | - | - | 11 | - | empuje | nula | si |
| 2.80 | - | - | - | 11 | - | empuje | nula | si |
| 2.85 | - | - | - | 10 | - | empuje | nula | no |
| 2.90 | - | - | - | 10 | - | empuje | nula | no |
| 2.95 | - | - | - | 10 | - | empuje | nula | no |
| 3.00 | - | - | - | 10 | 7 | empuje | empuje | no |


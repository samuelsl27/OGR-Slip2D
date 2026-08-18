# OGR Slip2D v0.1.97 — la búsqueda se reparte entre procesos, y el techo no es el que parecía

| Ej_2, rejilla de referencia (4840 círculos) | secuencial | en paralelo |
|---|---|---|
| Bishop | 8,2 s | **3,8 s** |
| Lowe-Karafiath | 35,3 s | **19,2 s** |

**Idéntico bit a bit.** Mismo `repr` de coma flotante en los 3717 (Bishop) y
4482 (Lowe) resultados, mismo orden, mismos recuentos, mismo círculo crítico.
No es una tolerancia: es identidad.

Y la parte que no salió como se esperaba: **añadir procesos por encima de dos
no mejora nada**, y eso cambia lo que hay que hacer después — §3.

---

## 1 · Por qué esto no puede cambiar ningún número

Los círculos de una Grid Search son **independientes**: cada uno se rebana y se
resuelve a partir del proyecto y de nada más, no se arrastra nada de uno al
siguiente, y desde v0.1.93 `regions_frozen()` garantiza **por contrato** que el
proyecto no se mueve mientras se analiza.

Falta una cosa que el paralelismo no da solo: el **orden**. `evaluations` es una
lista y alguien puede leerla por posición. Así que los lotes son tramos
**contiguos** de `_centres()` en el orden de visita, y `ProcessPoolExecutor.map`
devuelve en orden de envío: al concatenar sale la misma lista, gane quien gane
la carrera.

Por eso el test no comprueba una tolerancia sino **identidad bit a bit**, que es
como v0.1.93 validó su propia optimización.

Procesos y no hilos: todos los bucles internos son Python puro, así que el GIL
los volvería a serializar.

## 2 · Los dos controles, en Project Settings

No uno, dos, y la distinción importa: «usar la máquina» y «usar **cuánta**
máquina» son preguntas distintas. Un cálculo que se lleva todos los
procesadores deja el ordenador inservible mientras dura.

- **Buscar superficies en paralelo** — activado o desactivado, y punto.
- **Procesadores a usar: N %** — la parte del equipo que la búsqueda puede
  ocupar. Redondea **hacia abajo** y nunca por debajo de uno: 1 % significa «lo
  menos posible», no «nada». Apagarlo es trabajo de la casilla, y un porcentaje
  que además significara apagado sería una segunda forma de decir lo mismo.

Debajo, la página dice **cuántos procesos compra ese porcentaje en este
equipo**, porque una fracción no es un número sobre el que decidir.

**El predeterminado es 50 %, y la razón está medida, no es cortesía**: ver §3.
Con 8 procesadores lógicos son 4 procesos, que dan la misma velocidad que 7 y
dejan el equipo utilizable.

Independientemente de las dos, una búsqueda **pequeña se queda en el proceso**:
por debajo de 400 círculos arrancar el pool cuesta más de lo que ahorra, y eso
es lo que impide que un test de 25 círculos levante ocho intérpretes.

## 3 · El techo, y el error de expectativa

La expectativa escrita en el plan era **~6× en 8 núcleos**. No es lo que pasa,
y conviene dejar por qué.

Barrido sobre la rejilla completa, Bishop, con corrida de control repetida:

| procesos | tiempo | aceleración |
|---|---|---|
| 1 (secuencial) | 8,21 s | — |
| 2 | 5,41 s | 1,52× |
| 3 | 5,71 s | 1,44× |
| 4 | 6,23 s | 1,32× |
| 6 | 5,42 s | 1,52× |
| 7 | 5,44 s | 1,51× |
| control secuencial repetido | 9,47 s | **deriva 15,3 %** |

**Plano de dos procesos en adelante.** Con una deriva de control del 15 %, las
diferencias entre 2 y 7 no significan nada.

### Dónde se va, medido aparte

Instrumentando los workers sobre Lowe-Karafiath, 7 procesos, 56 lotes:

| | wall | suma de cómputo en los workers | paralelismo efectivo |
|---|---|---|---|
| **sin** devolver las evaluaciones | **11,79 s** | 74,25 s | **6,30×** |
| devolviendo todo | 18,05 s | 115,32 s | 6,39× |

Dos lecturas, y las dos importan:

1. **El reparto funciona**: el paralelismo efectivo es 6,3×. No hay
   desequilibrio de carga que arreglar.
2. **Devolver los resultados cuesta el 35 % del reloj** (11,79 → 18,05 s), y ese
   trabajo es **serie en el proceso padre**: deserializar ~30 MB de
   `LEMResult`, cada uno con sus 25 dovelas y sus referencias a materiales.

Es decir: el cuello no son los núcleos, es la **carga de vuelta**. Con
transferencia cero el techo sería 35,3 / 11,79 ≈ **3,0×**, no 6×.

### Un camino que se probó y NO era el problema

Primero se sospechó desequilibrio de carga —el coste de un centro varía más de
un orden de magnitud— y se pasó de un lote por worker a ocho. Medido:
1,85× → 1,84×. **Nada.** Se deja el reparto fino porque es correcto y gratis, y
porque protege de geometrías donde sí importaría, pero **no es una mejora de
esta versión** y venderla como tal sería el tipo de número que este proyecto no
se cree. Es la misma lección que v0.1.93 §3.

### Lo que haría falta, y por qué no entra aquí

Que los workers devuelvan **un resumen compacto por círculo** en vez del
`LEMResult` entero, y que el padre reconstruya sólo las superficies que la
ventana de interpretación va a enseñar. Eso llevaría de 1,5-2× a ~3×.

No entra en esta versión porque cambia **qué recibe la ventana de
interpretación** de una búsqueda, y eso necesita su propio triaje: hay que
saber primero quién recorre `evaluations` esperando encontrar dovelas.
Anotado en `docs/PENDIENTES.md`.

## 4 · Lo que NO se paraleliza, y se dice

Sólo Grid Search. Las búsquedas aleatorias —Simulated Annealing, Path, Block—
necesitarían la semilla derivada por lote para no romper la promesa de
reproducibilidad de v0.1.74, y Auto Refine alimenta cada iteración con la
anterior. Decirlo sale más barato que dejar al usuario preguntándose por qué
una búsqueda se aceleró y otra no.

## 5 · Un pool que no arranca no es motivo para no calcular

`_parallel_grid_run` devuelve `None` en vez de propagar, y el llamador cae al
camino secuencial. No es hipotético: en Windows los workers reimportan el
`__main__` del padre, y hay contextos donde eso no puede salir bien — se
reprodujo durante el desarrollo con un script alimentado por *stdin*. El
resultado tiene que seguir siendo el correcto; sólo el reloj puede empeorar.
Hay test.

---

## Archivos

| archivo | qué |
|---|---|
| `ogr_slip2d/search.py` | `_worker_count`, `_grid_batch`, `_parallel_grid_run`; `_run` partido en `_centres` + `_run_centres` |
| `ogr_core/project/settings.py` | `parallel_search`, `parallel_cpu_percent`, y la migración de la clave intermedia |
| `ogr_gui/dialogs/project_settings_dialog.py` | los dos controles y cuántos procesos compran aquí |
| `ogr_gui/i18n/__init__.py` | seis cadenas nuevas en español |
| `tests/test_parallel_search_v197.py` | 12 tests; identidad bit a bit, los controles, el repliegue |

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later

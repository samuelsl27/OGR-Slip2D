# OGR Slip2D v0.1.119 — el recocido minimizaba una función cuyo mínimo el programa se niega a publicar

`docs/PENDIENTES.md` §0 llevaba abierto desde v0.1.89 y traía su causa ya
diagnosticada: «eso convierte esta entrada de *investigar* en *cambiar
exactamente esto*», `ngen` 1000 en vez de 50 y `nepsilon` 5 en vez de 3.

**Ese diagnóstico era falso**, y las tres cosas que proponía se midieron una
a una antes de tocar nada. La causa estaba en una línea que ninguna de las
dos versiones anteriores miró.

| talud del defecto (H = 12 m, c′ = 8, φ′ = 20), Bishop, 7 semillas | peor semilla |
|---|---|
| mínimo **circular** de la rejilla | 1,1135 |
| SA antes | **1,7365** |
| SA ahora | **1,1232** |

Seis de las siete semillas caen por debajo del círculo, que es lo que una
búsqueda no circular tiene que poder hacer.

---

## 1 · La causa: la búsqueda se guiaba por lo que no iba a publicar

`_evaluate_polyline` preguntaba `res.is_valid` y **nunca preguntaba
`res.admissible`**. `SearchResult.critical` pregunta las dos. De modo que el
recocido descendía hacia superficies que el programa después rechaza.

Instrumentado sobre el talud del defecto, `generation_steps` = 300:

| semilla | bootstrap | fin de VFSA | fin de LMC | **publicado** |
|---|---|---|---|---|
| 1234 | 1,4668 | 1,4341 | **0,6972** | 1,3631 |
| 7 | 1,4016 | 1,1534 | **0,5003** | 1,3660 |
| 42 | 1,2296 | 1,2296 | **0,5005** | 1,2067 |

El algoritmo **converge a 0,50** —el suelo del guardarraíl `0.5 <= fos` que
la propia `_evaluate_polyline` lleva desde v0.1.17— y el número que se
enseña es la mejor superficie *admisible* que la marcha se cruzó por el
camino. Un subproducto, no un resultado.

De la población evaluada, el **83–98 % era inadmisible** (`m_alpha < 0,2`,
Whitman y Bailey 1967). Y **de las últimas cincuenta evaluadas, cero eran
admisibles** en las tres semillas: la fase local terminaba entera dentro de
la zona prohibida. Ahora esa fracción es del **1 %**.

Eso explica de una vez los tres síntomas que la ficha listaba por separado:
el número alto, que fuera errático entre semillas, y que **subir el esfuerzo
lo empeorase** (1,3631 con 300 pasos, 1,4341 con 1000) — más presupuesto es
descender mejor a la cuenca equivocada.

### Lo que más incomoda de este hallazgo

`ogr_slip2d/optimize.py`, escrito en v0.1.104, lleva quince versiones con la
frase exacta que describe el defecto puesta encima de la línea que lo evita:

> *«Admissibility matters most here: optimisation chases a LOWER factor,
> which is exactly where kinematically impossible surfaces live.»*

Y v0.1.89, al activar por defecto la comprobación de m-alpha, dejó de
**publicar** el 0,500 que SA devolvía, y dejó a la búsqueda **guiándose**
por él. Medio arreglo, treinta versiones invisible: el síntoma visible
desapareció y el mecanismo siguió intacto.

Ahora todo pasa por `SimulatedAnnealingSearch._steer`, un solo sitio. La
superficie inadmisible **se sigue contando** —entra en `evaluations` y en
`valid_count`, para que `inadmissible_count` y `total_count` signifiquen
aquí lo mismo que en las otras cinco búsquedas— y no guía nada.

## 2 · Los caminos equivocados, que son la mitad que merece recordarse

A/B espalda con espalda parcheando el fuente de `_vfsa`, una cosa cada vez,
con dos controles que coinciden dígito a dígito:

| variante | s1234 | s7 | s42 |
|---|---|---|---|
| control | 1,3631 | 1,3660 | 1,2067 |
| `Ngen0` = `generation_steps` — el «ngen 1000» de la ficha | 1,4668 | 1,3662 | 1,2296 |
| `nepsilon` = 5 | 1,3631 | 1,3660 | 1,1396 |
| `dE` contra el estado actual (Ec. 9) en vez de contra el mejor | 1,3631 | 1,3660 | 1,2067 |
| enfriamiento absoluto (Ecs. 10-11) | 1,3243 | 1,1803 | 1,2186 |

Ninguna arregla nada; la del presupuesto **empeora**. Y con la causa raíz ya
corregida, añadir el enfriamiento absoluto y `nepsilon` = 5 sube la peor
semilla de 1,1237 a 1,1394 —los dos del mismo A/B, tomados antes del
cambio de semilla propia, así que se comparan entre sí y no con el 1,1232
de producción—, así que **no se han tocado**: el paper dice una
cosa, la medición dice otra, y aquí manda la medición con la discrepancia
escrita en `docs/PENDIENTES.md` en vez de resuelta a favor del que suena
mejor.

`dE` es el caso más instructivo: es una desviación **real** de la Ec. (9) de
Su (2009) y su corrección da un resultado **idéntico bit a bit**. Un defecto
que no mueve ningún número sigue siendo un defecto, y decirlo cuesta menos
que dejar que el siguiente lo vuelva a encontrar.

## 3 · La segunda causa, ésta sí del paper: las dos puntas estaban clavadas

Su (2009) §2.1 cuenta `n = 2N − 2` grados de libertad precisamente porque
*«the two extremity points of the failure surface can only move along the
slope line»*: los extremos **son** variables de control. OGR los fijaba en
el pie y la coronación del tramo de terreno más inclinado y no los volvía a
tocar, ni en VFSA ni en LMC.

Sobre el talud del defecto eso significaba que toda superficie expresable
entraba y salía dentro de x = [30,00, 50,00], mientras que el círculo
crítico aflora en 30,03 y 51,45. La crítica que devuelve ahora va de 28,231
a 55,273.

Un extremo se mueve **sólo en x**; su `y` se lee del perfil del terreno, de
modo que sigue aflorando. Liberarlos, con la raíz ya arreglada, bajó la peor
de siete semillas de 1,3781 a 1,1862.

## 4 · Y por el camino: los Slope Limits podían dejar la búsqueda sin nada

Escribiendo el test de la regla 7 apareció que con `slope_limits` estrechos
SA **no devolvía ninguna superficie**. Los límites le llegaban sólo como
filtro de masas en `_best_of_masses`; la generación no los conocía, así que
la fase 1 arrancaba de un par de extremos fuera de los límites y todo lo que
construía se tiraba *después* de analizarlo.

Un filtro que el generador no conoce es un filtro que puede rechazar una
búsqueda entera — la misma forma que tenía el hallazgo del Block Search en
D21. Ahora `_run` recorta el vano a los límites y el LMC no deja salir de
ellos a los extremos.

## 5 · Optimize Surfaces, por defecto activado para Simulated Annealing

La ayuda de la referencia dice literalmente que para esta búsqueda la opción
viene activada de fábrica y que se recomienda no apagarla nunca. En OGR
estaba en `False` para las tres búsquedas no circulares.

Medido sobre siete semillas con los dos arreglos anteriores puestos: sin
ella la peor semilla queda en 1,2054, con ella en **1,1232**.

`optimize_enabled` pasa a ser **tri-estado**: `None` significa automático
—activado para el recocido, apagado para las demás—, y `True`/`False`
explícitos siempre mandan, de modo que desmarcar la casilla en un recocido
de verdad la desmarca. Se resuelve en un solo sitio,
`settings.optimize_enabled_for`.

**Consecuencia que conviene saber**: todo `.ogr` escrito hasta hoy guardó
`false`, que era el valor por defecto, así que **conserva el comportamiento
viejo** hasta que se vuelva a guardar desde el diálogo. Los modelos de
`validacion/casos/` y los del banco no cambian solos. Se eligió eso antes
que voltear en silencio proyectos guardados: un `false` que nadie escogió
sigue siendo un `false` guardado, y distinguir «no contestado» de «contestado
que no» es justo para lo que existe el tercer estado.

## 6 · La referencia externa que faltaba, y estaba publicada

`docs/PENDIENTES.md` decía que **no hay referencia externa para el resultado
de una búsqueda no circular** y proponía buscar la de Yamagami y Ueta (1988)
o el reanálisis de Greco (1996). Existe, y es del talud que ya estaba en el
repositorio, `validacion/casos/002-yamagami-ueta-1988`:

- Yamagami, T. y Ueta, Y. (1988). *Search for noncircular slip surfaces by
  the Morgenstern-Price method.* Proc. 6th Int. Conf. on Numerical Methods
  in Geomechanics, Innsbruck, 1219-1223 → **1,338 – 1,348**.
- Greco, V. R. (1996). *Efficient Monte Carlo technique for locating
  critical slip surface.* J. Geotech. Engrg. 122(7), 517-525 → **1,327 –
  1,333**.

| caso 002, Spencer | valor |
|---|---|
| circular OGR | 1,3446 |
| SA antes | 1,5026 – 1,5401 (**+13 % sobre todo lo publicado**) |
| SA ahora | **1,3294 – 1,3550**, mínimo 1,3294 |

Es la primera vez que una búsqueda no circular de este programa se contrasta
con un valor publicado y no con una identidad interna. El test lo asserta
como **banda** y no como valor, por dos razones dichas en su cabecera: lo
publicado es Morgenstern-Price con f(x) = 1 y aquí se corre Spencer, y
`caso.md` deja a Spencer fuera de su `esperado.json` a propósito. Va
acompañado de la desigualdad, que no depende del método.

## 7 · Lo que sigue mal, medido y sin corregir

Cuatro cosas, todas en `docs/PENDIENTES.md` con sus tablas. La primera es la
que más sorprende:

**`generation_steps` sigue sin ser monótono.** Con la causa raíz corregida,
la peor de siete semillas: 1,1232 con 300 pasos, 1,1611 con 600 y **1,1772
con 1000**. En el caso 002 mejora un poco (1,3550 → 1,3500) y tampoco es
monótono. Así que la puerta de admisibilidad explicaba el nivel del error,
no su falta de monotonía, y el hallazgo de v0.1.90 sigue abierto por otra
razón. Detalle: `generation_steps` mueve **dos** cosas a la vez —las pasadas
externas de VFSA y el tope de evaluaciones del LMC— y eso solo ya impide
leer el efecto de una.

Las otras son desviaciones del paper con efecto medido: el enfriamiento
acumulado, el `dE` contra el mejor histórico, y las divisiones en x, que
vedan el 12,5 % derecho del vano a todo vértice interior.

---

## Números que se movieron, y por qué

| | antes | ahora |
|---|---|---|
| SA, talud del defecto, peor de 7 semillas | 1,7365 | 1,1232 |
| SA, caso 002 con Spencer | 1,5026 – 1,5401 | 1,3294 – 1,3550 |
| población inadmisible que SA recorre | 83 – 98 % | 1 % |
| extremos alcanzables | x ∈ [30,00 , 50,00] | todo el perfil, o los Slope Limits |
| `optimize_enabled` por defecto | `False` | `None` (automático) |

La semilla, además, deja de ser estado global: `_run` sembraba el módulo
`random` entero. Reproducía —volvía a sembrar en cada corrida, así que dos
corridas coincidían— y aun así dejaba el flujo aleatorio del proceso donde
el recocido lo hubiera dejado. Reproducibilidad y no-interferencia son dos
propiedades y sólo se comprobaba la primera; el test que existía pasaba por
la razón equivocada. Ahora es un `random.Random` propio, y hay tres
aserciones separadas.

Ese cambio mueve el flujo aleatorio, así que **todos los números de arriba
están medidos después de él**, no antes.

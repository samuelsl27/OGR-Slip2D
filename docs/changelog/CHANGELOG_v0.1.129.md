# OGR Slip2D v0.1.129

**Los objetos de foco llegan a las siete búsquedas**, y no a una. Hasta
aquí, un foco dibujado sobre un modelo que no usara Grid Search no hacía
absolutamente nada.

Cierra **D33** y **D51**. Lo que merece recordarse no es el cableado: es
que el enunciado del defecto daba por aplicado un foco que dos clases sólo
guardaban, que la guía **no** extiende el foco a lo no circular —así que
la mitad de la solución hubo que definirla y decirlo—, y que dos de las
siete búsquedas resultaron no poder enfocarse por filtrado, cosa que se
midió y se dejó anotada en vez de arreglada.

---

## Qué estaba mal

`build_search` construye siete búsquedas y pasaba `focus_objects` a
**una**, como argumento exclusivo de la rama Grid.

El coste no es un porcentaje. En el banco de verificación, los problemas
78, 79 y 81 plantean **dos casos por modelo** y lo único que los separa en
el `.ogr` es el foco: *(a)* la superficie pasa por el pie · *(b)* es
tangente al fondo del cimiento. Con Grid Search funciona; con Path Search
el foco se caía y **los dos modelos del par eran el mismo cálculo dos
veces**. Medido antes de tocar nada, con Bishop y 500 superficies:

```
modelo_1a_path.ogr   min_fos = 0.9315
modelo_1b_path.ogr   min_fos = 0.9315
```

Y la comparativa publicaba de ahí un `OK` (78/1b, −0,14 %) y un `REVISAR`
(78/1a, −3,52 %) **producidos por el mismo número**. Regla 7, y aquí el
ajuste no es un número de vértices: es la restricción que dice de qué caso
se está hablando.

## Tres cosas del enunciado que resultaron falsas

Comprobarlas antes de escribir cambió el arreglo entero.

**1. `AutoRefineSearch` y `BlockSearch` NO aplicaban el foco.** El
enunciado afirmaba que las tres clases que aceptan el parámetro «lo
aplican antes de evaluar». Lo guardaban en `self.focus_objects` y no
volvían a leerlo jamás: la única lectura del motor entero estaba en
`GridSearch`. El comentario que decía *"applied BEFORE evaluation"* llevaba
mintiendo en los dos sitios desde v0.1.55.

Esto no es un matiz. **Pasar el foco por `common` y parar ahí habría dejado
esas dos ramas sin hacer nada, con el test en verde y el defecto cerrado**:
exactamente el falso arreglo que la regla 7 existe para impedir. Por eso la
lectura bajó a `BaseSearch`, donde hay una sola y la comparten las siete.

**2. `_base_kwargs()` no listaba `focus_objects`.** Su propio docstring
explica que existe porque «un argumento compartido nuevo cae en
`**legacy_kwargs` y se absorbe sin decir una palabra». Cierto — pero sólo
para los siete argumentos que sí listaba. Pasar el foco por `common` sin
añadirlo ahí no habría dado error y no habría hecho nada en `slope`, `path`
y `simulated_annealing`.

**3. Son siete ramas, no seis.** `particle_swarm` tiene rama propia desde
v0.1.126, y los **dos** tests cuyo trabajo es no perder una rama seguían
recorriendo seis. Añadido a los dos.

## Lo que la guía dice, y lo que no

Consultada antes de decidir, y es tajante en una dirección: **el foco es
una función de las búsquedas circulares**. Lo dice tres veces —«focus the
**Grid Search**», «can also be defined for the **Slope Search** method for
circular slip surfaces», y en la página de Slope Limits «If a Focus Search
object is defined for a Grid Search or Slope Search…»—, las cinco páginas
de foco viven bajo *Circular Surfaces*, la sección no circular no lo
menciona, y de la Path Search dice que *no requiere ningún objeto de
búsqueda*.

Y define los cuatro focos como reglas de **generación de radios**: con un
foco de punto o de tangente se genera **un solo círculo por centro** y el
Radius Increment deja de aplicarse.

De modo que «qué significa un foco sobre una poligonal» **no está en la
guía**, y hubo que preguntarlo antes de inventarlo.

Lo que decidió el diseño fue un detalle del propio OGR: **este motor nunca
implementó el foco como generador, sino como filtro** —genera los radios de
los Slope Limits y descarta los que no cumplen, que es por lo que existe
aquí el campo `tolerance` y allí no hace falta—. Y un filtro **sí** se
traduce a una poligonal, mientras que una regla de radios no. Punto, línea
y ventana se trasladan sin decidir nada; **la tangencia es lectura
nuestra**, y está escrita como tal:

> una poligonal es tangente cuando **toca** la recta infinita dentro de la
> tolerancia y **no la cruza**.

Es la condición circular sin cambiarle el sentido, y para las tres
tangentes del banco —todas horizontales, en la base de un estrato— se
reduce a *«el punto más bajo de la superficie está en esa cota»*, que es
literalmente el enunciado del caso 78(b).

**No es `min_elevation` dicho de otra forma**, y ese es el discriminante
del test: el filtro dice hasta dónde **puede** bajar una superficie; el
foco tangente exige que **llegue**. Una superficie somera pasa el filtro y
falla el foco, y esa diferencia es la que separa los dos casos del 78.

## El coste, medido y no supuesto

A/B en el mismo proceso sobre el 78, que es la única forma que funciona en
esta máquina:

| | µs |
|---|---|
| generar una superficie (`_generate_path_xstabl`) | **440** |
| evaluarla (`evaluate_surface`) | **2176** |

Sólo 4,9× — no los 40× que el razonamiento suponía, y esa diferencia
cambia la decisión. Con el foco tangente del 78 sobrevive el **2,2 %** de
lo generado, así que pidiendo 5000 superficies válidas:

| | segundos | factor |
|---|---|---|
| hoy, sin foco | 13 | — |
| rechazo **después** de evaluar | 594 | ×45 |
| rechazo **antes** de evaluar, presupuesto ×46 | 111 | ×8,5 |
| rechazo **antes**, presupuesto ×20 (el actual) | ~47 | **×3,3** |

Adoptada la última: el rechazo va **antes** de `evaluate_surface` —que es
lo que convierte un ×45 en un ×3— y el tope `num_surfaces × 20` se queda
donde está. La búsqueda devuelve menos válidas de las pedidas, lo cual es
correcto: un foco estrecha el espacio a propósito, y `valid_count` ya lo
enseña.

## El hallazgo: dos búsquedas no se dejan enfocar por filtrado

Salió al escribir el test de regla 7 para las siete ramas, y es la parte
que merece recordarse.

Las cinco búsquedas que sacan candidatas **independientes** —Grid, Slope,
Auto Refine, Block, Path— pierden **rendimiento** ante un foco y nada más.
Las dos **guiadas** no se comportan así: el recocido camina de candidata en
candidata y el enjambre dirige partículas hacia la mejor encontrada, de
modo que el foco filtra **el camino** además del destino.

Recocido simulado, tangente a `y = −5`, seis vértices y 25 pasos:

| tolerancia | 2 | 5 | 10 | 12 | 14 | 20 |
|---|---|---|---|---|---|---|
| válidas | 0 | 0 | 0 | 71 | 71 | 71 |
| mínimo | — | — | — | 1,3427 | 1,3427 | 1,3427 |

**No hay término medio.** Por debajo de 12 no devuelve nada; a partir de 12
el foco acepta todo lo que el paseo produce y deja de decidir — 1,3427 es
el valor **sin foco**.

Y la medición que lo convierte en hallazgo y no en «tolerancia demasiado
apretada»: **la superficie que devuelve la búsqueda SIN foco satisface ese
mismo foco** a tolerancia 10, y con él puesto la búsqueda no encuentra
nada. Existe una superficie que lo cumple y el paseo no llega a ella.

La causa está en el arranque: `_bootstrap_parameters` construye el cuenco
inicial a partir de una **profundidad** y la **encoge** en cada reintento,
así que un rechazo lo aleja de una tangente profunda en vez de acercarlo.

El enjambre tiene la versión suave de lo mismo: sus partículas son círculos
construidos de un punto en el pie, un ángulo de tangencia y un punto en la
coronación, y esa parametrización no coloca un círculo tangente a `y = −5`
a menos de 2 m en ese modelo. Con tolerancia 5 funciona y estrecha bien
(1,9619 contra 1,4269).

**Se reporta, no se arregla** (regla 6). Enseñar al arranque a apuntar al
foco sería dirigir la generación, que es un diseño distinto del filtro que
esta versión implementa, y cambiaría la distribución de muestreo de una
búsqueda estocástica: eso se decide con mediciones delante, no de pasada.
Queda fijado en `TestGuidedSearchesCanBeCutOffByTheirFocus`, con la nota de
que si algún día encuentra algo, lo que hay que actualizar es el docstring
y no borrar el test.

Mientras tanto `settings_warnings` lo dice en voz alta, porque «no he
encontrado ninguna» y «no existe ninguna» se leen igual en una ventana de
resultados.

## La última puerta, que habría deshecho todo lo demás

`optimize_surface` evalúa cada paso de su paseo llamando a
`evaluate_surface` **directamente** sobre el objeto de búsqueda, así que
era la única puerta del motor que un foco no podía ver.

Aquí importa más que en ningún otro sitio, y por una razón que está en el
banco y no en el código: **la comparativa publica el número OPTIMIZADO** en
la familia no circular, porque «el manual optimiza SIEMPRE en sus tablas no
circulares». Un paseo libre de salirse del foco habría devuelto una
superficie de **un caso distinto del que declara el modelo** — que es D33
volviendo por detrás después de cerrarlo por delante.

Un paso que abandona el foco no se toma: el callback devuelve `None`, que
es lo que ya devolvía para una superficie inevaluable, y el paseo trata
ambos igual. Con dos tests, porque una guarda que rechaza todo es una
optimización apagada: que la superficie optimizada **siga cumpliendo** el
foco, y que la optimización **siga moviendo el número**.

## D51, de paso, porque es el mismo patrón

`min_area` se pasaba **a mano** en seis de las siete ramas y la de `path`
lo olvidaba, así que `PathSearch` lo fijaba en 1.0 dijera lo que dijera el
proyecto. Lo que costó, en el problema 86: Spencer **1,1728 (−26,4 %)**
sobre una lonja de 2,41 ft² contra **1,5841 (−0,62 %)** sobre el mecanismo
de 201,95 ft² que publica el manual.

Movido a `common`, **conservando el default de cada rama** (0,5 en Auto
Refine, 2,0 en Block, 1,0 en las demás). Eso no es pulcritud: **76 modelos
del banco dejan el campo vacío** y cabalgan sobre el default de su rama, y
colapsar los siete a un número habría movido filas publicadas por una razón
que no tiene nada que ver con el defecto que se cierra. El test comprueba
las dos mitades: que un valor declarado llega a las siete, y que sin
declarar cada una conserva el suyo.

## Anomalía nueva, medida y NO corregida

En `GridSearch`, un círculo rechazado por foco hace `continue` **sin sumar
`invalid_count`**, a diferencia de todos los demás rechazos de ese bucle.
Rompe la invariante que las líneas de al lado defienden por escrito —la
población tiene que seguir siendo `(nx+1)(ny+1)(rinc+1)`—, así que con
focos activos `total_count` deja de cuadrar.

Puede ser deliberado (un círculo filtrado no se «generó» conceptualmente),
pero entonces el comentario de al lado es el que está mal. Los rechazos
nuevos de esta versión se han escrito **iguales al de Grid** para que no se
mueva ninguna fila publicada por este motivo; decidir cuál de los dos
criterios es el bueno es trabajo aparte, y hay que medir si el arreglo
mueve alguna fila circular antes de aplicarlo.

## Lo que NO se ha tocado

- **El foco sigue siendo un filtro, no un generador de radios.** Que la
  guía lo defina generando —un solo círculo tangente por centro, sin Radius
  Increment— mientras OGR filtra los radios de los Slope Limits con una
  tolerancia es una divergencia **real y anterior a D33**, que hace que el
  efecto del foco dependa del Radius Increment. Anotada; tocarla movería
  todas las filas circulares del banco.
- **El banco no se re-modela.** Los trece `.ogr` con foco se quedan como
  están; lo que cambia es que el foco por fin se aplica.
- **Optimize Surfaces sobre una superficie enfocada** puede sacarla de su
  foco. Pregunta abierta, sin respuesta inventada.

## Qué se movió y qué no

**Ninguna fila circular se mueve.** Comprobado dígito a dígito contra los
resultados guardados en once modelos circulares, ocho de ellos con foco:

| # | modelo | guardado | 0.1.129 |
|---|---|---|---|
| 37 | modelo | 0,766024 | 0,766024 |
| 61 | modelo | 1,422973 | 1,422973 |
| 62 | modelo_seco | 0,991813 | 0,991813 |
| 77 | modelo (bishop) | 1,589954 | 1,589954 |
| 77 | modelo (spencer) | 1,642807 | 1,642807 |
| 78 | modelo_1a | 1,127886 | 1,127886 |
| 78 | modelo_1b | 1,138991 | 1,138991 |
| 79 | modelo_1 | 1,419106 | 1,419106 |
| 79 | modelo_2 | 1,466685 | 1,466685 |
| 81 | modelo_1 | 1,235695 | 1,235695 |
| 81 | modelo_2 | 1,158036 | 1,158036 |

Es lo esperado y no una casualidad: `GridSearch` no cambia de lógica, y
`min_area` conserva el default por rama precisamente para esto.

**Suite completa y sin argumentos: 2879 pasan, 0 fallan.**

Regenerada la comparativa entera: de sus **533 filas**, **0 circulares se
mueven** y **35 no circulares sí**, todas en los doce modelos que llevan
foco o un `min_area` que su rama perdía. Ninguna fila nueva, ninguna
desaparecida.

### Las que mejoran

| # | esc. | método | manual | antes | ahora | estado |
|---|---|---|---|---|---|---|
| 78 | 2a | Bishop | 0,947 | −5,69 % | **−0,72 %** | DISCREPANCIA → **OK** |
| 78 | 2a | GLE | 0,910 | −5,06 % | **−0,63 %** | DISCREPANCIA → **OK** |
| 78 | 3a | GLE | 0,910 | −5,66 % | **+0,01 %** | DISCREPANCIA → **OK** |
| 78 | 3a | Bishop | 0,947 | −3,70 % | **−0,72 %** | REVISAR → **OK** |
| 78 | 1a | Bishop | 0,947 | −3,52 % | **−0,72 %** | REVISAR → **OK** |
| 78 | 1a | GLE | 0,914 | −5,47 % | −1,06 % | DISCREPANCIA → REVISAR |
| 79 | caso 1 | Bishop | 1,225 | +1,23 % | **+0,68 %** | REVISAR → **OK** |
| 81 | caso 1 | Spencer | 1,183 | −2,42 % | **+0,51 %** | REVISAR → **OK** |
| 81 | caso 2 | Bishop | 1,155 | −6,41 % | −3,47 % | DISCREPANCIA → REVISAR |
| 86 | — | Spencer | 1,594 | −30,99 % | **−6,09 %** | (D51) |
| 86 | — | GLE | 1,588 | −30,90 % | **−6,33 %** | (D51) |
| 77 | caso 2 | Spencer | 1,570 | −35,75 % | −10,99 % | (foco) |

El 86 es la comprobación de D51 y sale **clavada**: el registro predecía
Spencer 1,584134 con `min_area = 50`, y eso es exactamente lo que da.

### Y los pares por fin se separan, que era el criterio de cierre

| par | antes | ahora |
|---|---|---|
| 78 1a / 1b (Bishop) | 0,9137 / **0,9137** | 0,9402 / **0,9055** |
| 78 2a / 2b (Bishop) | 0,8931 / 0,9093 | 0,9402 / 0,9479 |
| 79 caso 1 / 2 (Bishop) | 1,2401 / **1,2401** | 1,2333 / **1,3292** |
| 81 caso 1 / 2 (Bishop) | 1,0810 / **1,0810** | 1,0802 / **1,1150** |

## El hallazgo nuevo: la Path Search no llega al fondo del modelo

Varias filas **empeoran**, y hay que decir por qué, porque no es ruido: es
un defecto que el cierre de D33 ha destapado y que antes era invisible.

Los seis escenarios del 78 se reparten en dos familias por su tipo de foco,
y el rendimiento cae con la profundidad de la tangente:

| esc. | foco | válidas de las 5000 pedidas | Δ Bishop |
|---|---|---|---|
| 1a | punto en el pie | **5000** | −0,72 % |
| 2a | punto en el pie | **5000** | −0,72 % |
| 3a | punto en el pie | **5000** | −0,72 % |
| 1b | tangente a y = 0 | 1363 | −1,04 % |
| 2b | tangente a y = −16,5 (**suelo del modelo**) | **170** | +6,51 % |
| 3b | tangente a y = −30 (**suelo del modelo**) | **0** | sin dato |

Medido aparte, y es la causa: sobre el 3b, de 424 superficies generadas
**sin** foco la más profunda llega a `y = −18,83`, y el foco pide `y ≤ −27`.
Sobre el 2b, exactamente **1 de 415** cae en la banda. El `_y_floor` de la
búsqueda es el suelo del modelo en ambos casos, así que **no es que esté
prohibido bajar**: es que el generador XSTABL no genera superficies tan
profundas.

De modo que el 2b responde desde una muestra de 170 —no representativa, y
por eso su número se aleja— y el 3b **no responde**. Eso último parece una
pérdida y no lo es: **antes el 3b publicaba el número del 3a**, porque su
foco se caía y los dos modelos eran el mismo cálculo. Una fila que dice «no
he encontrado ninguna» es mejor evidencia que una que copia el caso de al
lado.

Queda como defecto nuevo del generador de trayectorias, no de los focos.

### Otras dos cosas vistas al comparar, ninguna del cambio

- **`janbu_simplified` aparece donde antes no estaba.** Los `.ogr` del 78
  declaran cuatro métodos y las corridas guardadas de 0.1.127 sólo tenían
  tres. Comprobado que **no es de este cambio**: con los ajustes de 0.1.127
  reproducidos a mano (sin foco, `min_area = 1`) Janbu da 0,934362, así que
  siempre pudo darlo. Es procedencia de los archivos guardados.
- **El Bishop del 86 no optimiza**: `la optimizacion no devolvio superficie`.
  Tampoco es de aquí — `_focus_rejects` devuelve False, porque el 86 no
  tiene focos. Con `min_area = 50` su mínimo se muda a un mecanismo cuyo
  extremo izquierdo roza la esquina del modelo, `(0.15, 0.12)`, y esa
  superficie **no se puede rebanar** al reconstruirla desde los vértices
  guardados. Es el viaje de ida y vuelta de la herramienta del banco, y se
  anota.

---

## Archivos

- `ogr_slip2d/focus.py` — `FocusObject.accepts_surface` y el
  `accepts_surface` de módulo, más los auxiliares de geometría
  (`_segments_cross`, `_polyline_point_distance`,
  `_signed_distance_point_line`).
- `ogr_slip2d/search.py` — `focus_objects` en `_base_kwargs` y en
  `BaseSearch`; `_focus_rejects` / `_focus_rejects_circle`; aplicación en
  las siete búsquedas; `min_area` con nombre en `PathSearch`.
- `ogr_slip2d/particle_swarm.py` — aplicación en el enjambre.
- `ogr_slip2d/optimize.py` — el paseo de optimización no puede salirse del
  foco.
- `ogr_slip2d/analysis_runner.py` — `focus_objects` y `min_area` en
  `common`, `_MIN_AREA_FALLBACK`, `_focus_notes`.
- `tests/test_focus_all_searches_v1129.py` — nuevo.
- `tests/test_search_inequality_v1118.py`,
  `tests/test_surface_filters_v1102.py` — la séptima rama.

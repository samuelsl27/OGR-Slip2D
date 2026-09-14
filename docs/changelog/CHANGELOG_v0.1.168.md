# OGR Slip2D v0.1.168 — «Add Surface (three points)»: el modo estaba, la acción no

Cierra **D101** (P-D101, paquete P1). Cero dígitos movidos, y medido.

---

## 1 · Qué estaba mal

`ToolMode.ADD_SURFACE_3PT` existía desde v0.1.3 con miembro de enumeración, cursor
(`CrossCursor`) y texto de estado («Click three points to define a circular surface»), y
**ningún `_set_tool` del repositorio lo activaba**. Con él vivían una traducción huérfana
—`"Add Surface (three points)"`— y `SlipCircle.from_three_points`, ejercitada sólo por
`tests/test_slip2d.py`. Es la **segunda** manera de añadir una superficie circular
concreta que documenta la referencia, con el andamiaje puesto y sin acción: **regla 3** en
su forma pura, durante **98 versiones**.

Se implementa en vez de retirar porque el modo, la traducción, la fórmula y el modelo de
datos de 0.1.157 —`user_surfaces`, su gestor, su serialización, su dibujo en
`_draw_user_surfaces`, su grupo en el `.h5` y su competencia por el mínimo global en
`_evaluate_user_surfaces`— ya existían: retirar era borrar seis piezas para no escribir la
séptima.

---

## 2 · Lo que la ficha daba por sentado y la medición desmiente

De las siete cosas que P-D101 afirma, **siete** no se sostienen.

1. **«Falla con 0.1.159 por (a)» es falso, y (a) es justo el caso que no puede
   discriminar.** El caso (a) de la ficha —(0,0), (4,0), (0,4) → centro (2,2), radio
   2√2— **pasa hoy, bit a bit**: `from_three_points` ya devuelve `centre=(2.0, 2.0)` y
   `radius == 2*math.sqrt(2)` exactamente. La fórmula llevaba correcta desde siempre y ya
   tenía test propio. Lo que faltaba era la acción.
2. **Su caso (e) también pasaba hoy**: la traducción ya existía — es precisamente la
   huérfana que motiva la ficha. Dos de los cinco casos que propone estaban **verdes**
   contra el árbol sin arreglar, y uno de ellos era el que nombraba como discriminador.
3. **El rótulo no lleva puntos suspensivos**, y la ficha manda ponerlos («la traducción de
   1269 se actualiza con los puntos suspensivos»). v0.1.166 midió la convención una
   versión antes: «...» aparece **sólo** cuando se abre un diálogo, y **todas** las
   acciones de modo de dibujo van sin ellos. Ésta entra en modo de dibujo y no abre
   ninguno, así que los puntos habrían prometido un diálogo inexistente —una mentira
   nueva, pequeña, dentro del arreglo de una mentira—; y, peor, habrían dejado la clave
   sin casar, con `tr()` cayendo al inglés y el censo `_LABELS_WITHOUT_SPANISH` subiendo
   de 27 a 28, que es **literalmente** el defecto `"Add Grid"`/`"Add Grid..."` que
   v0.1.166 encontró. Sin puntos, **la huérfana se reutiliza tal cual** y el diccionario
   no gana ninguna entrada por el rótulo.
4. **La acción no lleva icono**, y eso es una trampa de la versión anterior y no un
   descuido: el changelog de v0.1.166 dice que `surface_3pts` «queda libre para D101»,
   pero su test **fija la ausencia** de esa clave en el catálogo
   (`assert not has("surface_3pts")`). Re-añadirla lo pondría rojo. El hermano
   `surf_centre_radius` va con `icon_key=None`: ésa es la convención del menú.
5. **`d101()` no existía** en `_tools/verificar_cierres.py` aunque el criterio de cierre la
   cite como si estuviera escrita. Mismo caso que D91, D95, D96, D98, D102 y D103.
6. **El test es `_v1168` y no `_v1160`**: `_vNNNN` es la versión en que ATERRIZA. Mismo
   re-anclaje que las seis anteriores.
7. **Dos de sus cinco citas de línea estaban caducadas**: `i18n:1269` es hoy 1303, y el
   gating «3675-3681» es hoy 3769-3789, porque v0.1.166 y v0.1.167 reescribieron esa zona.
   Por eso **nada** en este cambio ni en su test se localiza por número de línea: todo por
   nombre de símbolo. Un rango es una cita que caduca.

---

## 3 · El hallazgo que cambió el trabajo: la guarda de colinealidad no protege de un ratón

`from_three_points` rechaza los tres puntos alineados con

```python
d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
if abs(d) < 1e-14:
    raise ValueError("Three points are collinear; no unique circle")
```

`d` es cuatro veces el área con signo del triángulo: una **magnitud de área** comparada
contra una **tolerancia absoluta**, que es exactamente lo que AGENTS.md prohíbe («las
tolerancias geométricas van relativas al tamaño del modelo»). Y aquí no es teórico.
Medido, con a=(0,0), b=(10,0), c=(20,ε):

| ε (desviación de la recta) | radio |
|---|---|
| 1e-3 m | **1,0·10⁵ m** |
| 1e-6 m | **1,0·10⁸ m** |
| 1e-9 m | **1,0·10¹¹ m** |
| 1e-15 m | **1,0·10¹⁷ m** |
| 0 exacto | `ValueError` |

La guarda **sólo salta con colinealidad exacta en coma flotante**, que es lo único que un
ratón nunca produce. Un usuario que pinche tres puntos visualmente alineados obtenía, en
silencio, un círculo de radio kilométrico que se añade a `user_surfaces`, se dibuja
entero, se escribe al `.ogr`, se exporta al grupo `user_surfaces/` del `.h5` y **compite
por el mínimo global**. Capturar el `ValueError` como pide la ficha era necesario y **no
suficiente**: casi nunca se lanza.

La guarda de verdad va en el lienzo, no en el motor —la ficha prohíbe mover ningún número
y `test_slip2d.py` fija ese comportamiento—, y es una tolerancia de **pantalla**, la
convención del proyecto, con el idioma que `canvas_view.py` ya usa en `_pick_boundary`:
`px_per_unit = abs(self.transform().m11()) or 1.0`.

Tres medidas más fijaron la forma exacta:

- **`_point_segment_distance`, que ya existe en el archivo, es la medida equivocada**: con
  a=(0,0), b=(10,0), c=(20,0) —colineales— contesta **10**, porque recorta la proyección
  al segmento, mientras la perpendicular a la **recta** es 0. Habría dejado pasar el trío.
  Va con test, porque «reutiliza el ayudante que ya está» es exactamente lo que alguien
  propondrá.
- **No hace falta guarda de separación entre clics**, aunque lo parezca — se escribió
  primero dándolo por necesario y la medición lo refutó: con a y b a 1e-8 y c=(10,10) el
  círculo converge a radio 10 centrado en (0,10), perfectamente condicionado. La
  degeneración la gobierna la **alineación**, no la proximidad. Su **ausencia** va con
  test.
- **El umbral no juzga si el radio es sensato**, y eso se dice en el docstring y aquí: 3 px
  a un zoom típico (~20 px/u) son 0,15 m y dan radio 667 m, que es una rotura casi plana
  **legítima** y se acepta. Lo que no es legítimo es que dentro del ancho del propio cursor
  el radio recorra de 667 m a 20 km. `mousePressEvent` hace
  `mapToScene(event.position().toPoint())`, o sea **redondea a píxel entero**, así que por
  debajo de la resolución del puntero el usuario no controla el número. `_MIN_PERP_PX` se
  fija en **2** porque a 1 px el único valor expresable por debajo es 0, y porque 2 queda
  **estrictamente por debajo de todas** las tolerancias de acierto del archivo (8, 10 y
  12 px): una guarda igual a una tolerancia de acierto habría rechazado clics que el mismo
  lienzo trata como acierto deliberado de otra cosa.

**Y el `except ValueError` no es código muerto**, que era la duda razonable y la razón de
mirarlo: `tol = 2 px / px_per_unit` es **relativa** al zoom, así que con la vista muy
ampliada se encoge por debajo del 1e-14 **absoluto** del motor y la guarda del motor salta
primero. Es la asimetría absoluto/relativo del propio AGENTS.md, y va comentada con esa
razón donde se captura.

### El snapping juega en contra (medido)

`_snap_point` mete `self._draw_points` como pseudo-frontera **sin condicionar al modo**
(`if self._draw_points:`), a diferencia de la referencia ORTHO de veinte líneas antes, que
sí exige `is_drawing_boundary`. Con snapping activo —el valor por defecto— eso significa
que un **segundo clic a menos de 12 px del primero se convierte en duplicado exacto**
(a == b, el caso 0/0) y que un **tercer clic a menos de 10 px de la cuerda se proyecta
sobre ella**, perpendicular exactamente 0. Los dos los absorbe el diseño: el repetido se
ignora —como cualquier clic que no acierta nada, y rechazarlo sería un callejón sin salida,
porque con a == b guardado todo clic posterior se rechazaría también— y el proyectado lo
ve la guarda de perpendicular. El comportamiento de fondo queda **reportado y no
corregido** (§7).

---

## 4 · Qué se ha hecho

**`ogr_gui/canvas/canvas_view.py`**

- Señal `three_points_picked = Signal(float × 6)`, tercer miembro de la familia
  `point_picked` (1 clic) → `segment_picked` (2) → ésta (3). **No** se extiende
  `segment_picked`: seis slots están atados a su aridad y todos usan el idioma
  `disconnect`/`except (TypeError, RuntimeError)`, que resuelve por identidad. **No** una
  `Signal(object)` con lista: todas las `Signal(object)` del archivo llevan **un** objeto
  de dominio y nunca un contenedor mutable, que además aliasaría el acumulador del que
  sale. **No** que el lienzo construya el `SlipCircle`: medido, `ogr_gui/canvas/` **nunca
  ha importado `ogr_slip2d`**, y habría sido el primer import del motor en la capa de
  vista justo en la versión que arregla un descuido de capas.
- `_MIN_PERP_PX` y `_is_degenerate_triangle`, con la perpendicular a la recta infinita.
- **Rama propia** en `mousePressEvent`, detrás del bloque de 2 clics y **sin tocar una coma
  de su tupla**: esos cinco modos alimentan la rejilla de búsqueda y la población de
  soportes, y generalizarlos a N clics los habría hecho pasar por código nuevo a cambio de
  nada; además este flujo tiene un paso que ninguno tiene, un **rechazo** que conserva los
  puntos pendientes. Precedente en el mismo método: `ADD_LINE_LOAD` tiene rama propia
  siendo de un clic.
- Rechazar **conserva los dos primeros puntos** en vez de reiniciar. Dos clics buenos ya
  están invertidos y sus puntos rojos siguen en pantalla, que es lo que hace la corrección
  directa; es la misma respuesta que `_finish_drawing` da a un polígono demasiado corto; y
  deja estado **positivo** que un test puede mirar, mientras que un reinicio deja
  exactamente el estado de «no haber pinchado nunca», indistinguible de que el cableado no
  exista.
- `tool_mode.py` **no se toca**, y `ADD_SURFACE_3PT` **no** entra en `is_drawing_boundary`:
  le habría dado el menú contextual de dibujo, habría hecho que Enter llamara a
  `_finish_drawing` —cuyo `boundary_type_drawn` es `None`, o sea cancelar en silencio— y
  habría enganchado ORTHO. Los puntos rojos de `_update_draw_preview` son la vista previa
  correcta y ya funcionaban.

**`ogr_gui/main_window.py`** — `_mk("surf_three_points", …)`, la entrada de menú entre
`surf_centre_radius` y `surf_manage`, la clave sumada a la tupla del gating (hereda las
dos ramas de tooltip, ya traducidas: una segunda frase para la misma precondición es cómo
un tooltip acaba contradiciendo al de al lado), `_add_surface_three_points` y
`_on_surface_3pt_picked`. La señal se conecta **una vez** en `__init__` y no se arma y
desarma en cada uso como `segment_picked`, porque pertenece a un solo modo y no tiene con
qué colisionar. `_add_surface_three_points` **no** imprime nada: `set_tool_mode` ya emite
el texto del modo, y repetirlo habría dado al usuario la misma instrucción dos veces
—`act_add_block_search_object` tiene que imprimir la suya sólo porque `DRAW_BLOCK_SEARCH`
no lleva texto de estado—. El slot sale a SELECT **antes** de `refresh_scene()`.

**`ogr_gui/i18n/__init__.py`** — dos entradas nuevas; la del rótulo ya estaba.

---

## 5 · Dos cosas que la ficha no pedía, por decisión del propietario

**(A) Los textos de estado no pasaban por `tr()`.** `set_tool_mode` emitía
`mode.status_message` en crudo, y los **34** textos de estado de `ToolMode` tenían **cero**
entradas en español. Activar este modo habría publicado una cadena inglesa nueva visible
con el idioma en español: la versión habría **creado** la violación de regla 2 en vez de
evitarla. Se envuelve en `tr()` y se traduce **sólo** el del modo nuevo; los otros 33
siguen cayendo al inglés exactamente como hoy, sin regresión. `tr()` recibe una
**variable**, así que el escáner AST de `test_i18n_coverage_v141` no ve ni uno —el mismo
agujero que v0.1.166 documentó para las etiquetas de acción—, y por eso el censo va con
techo `==` y no `<=`, fijando **los dos** números (34 totales, 33 sin español): fijar sólo
el techo permitiría satisfacerlo borrando hints, y un techo holgado deja de medir mucho
antes de que nadie lo note, que es la lección del 210.

**(B) Un clic pendiente sobrevivía a un cambio de herramienta.** `set_tool_mode` no
vaciaba `_draw_points`, que es **compartido** por todos los modos de picking: un clic
suelto de Add Support o Pick Grid Rectangle se convertía en el **primero de los tres** de
un círculo que el usuario nunca colocó. Era pre-existente y alcanzaba ya a los cinco modos
de dos clics. Se descarta el estado pendiente al **cambiar** de modo, con guarda
`mode is not previous`: Pick Grid Rectangle se re-arma desde un diálogo que sigue abierto,
y re-entrar en el mismo modo no puede ser una cancelación encubierta. Consecuencia
deliberada que conviene decir en voz alta: **cambiar de herramienta a media frontera ahora
descarta el dibujo**. Panear a media frontera va por el botón central o Shift+arrastre,
que no pasan por `set_tool_mode`, así que no se pierde nada del flujo documentado.

---

## 6 · El censo que la ficha hizo a ojo: no era un modo huérfano, eran seis

Medido **por AST** sobre toda llamada a `set_tool_mode`/`_set_tool` de `ogr_gui` —y la
única forma de llamada que no nombra un `ToolMode` literal es el propio reenviador
`_set_tool(mode)`, así que el censo es completo—, los modos que **nadie activa** son
**seis**, no uno:

- **`MEASURE`** y **`ADD_SURFACE_CR`** — andamiaje puro: cursor y texto de estado, y nadie
  los lee siquiera. Exactamente la forma de D101. `ADD_SURFACE_CR` es además **el modo del
  hermano que la ficha cita como el precedente que sí funciona**:
  `_add_surface_centre_radius` va por diálogos (`_read_points` + `QInputDialog`) y **nunca
  entra en él**.
- **`SCALE_BOUNDARY`**, **`ROTATE_BOUNDARY`**, **`EXPAND_SHRINK`** y
  **`CHANGE_SLOPE_ANGLE`** — a éstos sí los lee `_on_boundary_clicked`, pero como nadie
  entra en ellos esas ramas `elif` son **inalcanzables**. Las funciones en sí no se pierden:
  sus acciones están en el menú y se llegan por otro camino.

Un tropiezo propio que merece quedar escrito, porque es la diferencia entre dos censos que
parecían el mismo: el primer recuento buscó **cualquier referencia** a `ToolMode.X` fuera
de `tool_mode.py` y dio **tres** huérfanos; el bueno busca **activaciones**, y da seis. Un
modo puede estar referenciado en abundancia y no ser alcanzable jamás — que es el defecto
entero de esta ficha. Y al comprobar el cuarto se cayó otro error propio antes de
escribirlo: `change_slope_angle` parecía no estar registrado como acción, y sí lo está,
bajo la clave `change_slope`. Se miró antes de levantar acta.

Los seis quedan **reportados y no corregidos** (regla 6), con ficha propia en el banco
(**D142**) y con el conjunto exacto fijado en un test que se pondrá rojo el día que alguien
cablee uno, que es cuando la ficha tiene que cambiar.

---

## 7 · Reportado y no corregido (regla 6)

- Los **seis modos que nadie activa** (§6), y las ramas `elif` inalcanzables de
  `_on_boundary_clicked` que cuatro de ellos alimentan.
- **`_snap_point` mete `_draw_points` como pseudo-frontera para cualquier modo**, no sólo
  los de dibujo de fronteras, y eso trabaja activamente contra un círculo de tres puntos
  (§3). Estrecharlo cambiaría el snapping de los cinco modos de dos clics en la misma
  versión que ya toca `set_tool_mode`.
- **La guarda absoluta `abs(d) < 1e-14` sigue en `from_three_points`**, y sigue siendo una
  tolerancia absoluta sobre una magnitud de área. No se toca: la ficha prohíbe mover
  números y `test_slip2d.py` la fija. Lo que esta versión añade es una guarda **encima**,
  en la capa donde la tolerancia puede ser de pantalla.
- **`_cancel_drawing` emite `"Drawing cancelled."` sin `tr()`** — cadena visible, invisible
  a los siete patrones `_VISIBLE` porque no es ninguno de sus constructores.
- **33 textos de estado siguen sin español** (§5A), medidos y con techo, sin traducir:
  traducirlos mueve texto visible en 33 sitios y es un encargo propio.
- **Los envoltorios C++ muertos**: `_clear_draw_preview` llama a `it.scene()` sobre cada
  item guardado, y si un `refresh_scene()` corrió mientras había items pendientes esos
  envoltorios están muertos. El riesgo **pre-existe** y esta versión no lo ensancha —la
  rama nueva limpia la vista previa **antes** de emitir, y el slot sale a SELECT antes de
  refrescar—, pero sigue ahí.
- **El presupuesto 210 contra una cuenta real de 20** sigue siendo un control que no puede
  fallar, y el criterio de cierre de D101 prohíbe moverlo.

---

## 8 · Qué se probó

- **Suite entera y sin argumentos**: **3596/3596**. 0.1.167 traía 3552, y los 44 nuevos son
  este archivo.
- **El test discrimina, y se midió**: contra el árbol de 0.1.167 con sólo el archivo de
  test presente, **33 de 44 fallan y 11 pasan**, y los 11 son justo los que deben —las
  identidades que el cambio tiene que **conservar** (terminar una frontera, los modos de
  dos clics de punta a punta, re-armar el mismo modo, ningún rótulo prefijo de otro, el
  presupuesto de mensajes), las **medidas** del motor que no se mueve (los radios
  kilométricos, el rechazo sólo de la colinealidad exacta, el par casi duplicado sano, el
  ayudante equivocado), la **evidencia** de D142, y el **control** declarado—. Un archivo
  que pasara entero contra el árbol sin arreglar no mediría nada.
- **Ninguna aserción fija un factor de seguridad**: lo que se comprueba son identidades y
  nombres. El círculo que aparece en el proyecto es, bit a bit, el que
  `from_three_points` devuelve con los mismos puntos de escena — identidad entre dos
  caminos, no una captura. El caso (a) de la ficha se sustituye por la identidad analítica
  que lo generaliza (los tres puntos de entrada caen sobre el círculo devuelto), declarada
  como **control** en su propio docstring porque es verde antes y después.
- **Cero dígitos movidos, y es consecuencia y no comodidad**: el cambio no sale de
  `ogr_gui/`, no toca una línea ejecutable de cálculo ni una constante ni una tolerancia ni
  un valor por defecto, y ningún `.ogr` del banco llega a una barra de menús ni a un clic
  de ratón. `d101()` lo comprueba contando apariciones de los símbolos de esta versión en
  `ogr_core`, `ogr_slip2d`, `ogr_fem2d` y `ogr_cli`, que son cero. **El banco no se
  re-corre.**
- Los dos presupuestos de `test_i18n_coverage_v141` intactos: 210 (cuenta real 20) y 68
  **exacto**.

### Qué falta por probar

- **En la aplicación en marcha**, porque headless no ve un cursor ni una vista previa: que
  el cursor cambia a cruz, que los puntos rojos aparecen donde se pincha, y que el círculo
  se dibuja entero con su marca de centro.
- El comportamiento **con snapping encendido** está razonado y acotado por las dos guardas,
  pero los tests lo apagan a propósito para medir la guarda y no el motor de snapping.

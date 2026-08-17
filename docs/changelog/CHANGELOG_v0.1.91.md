# OGR Slip2D v0.1.91 — el panel de dovelas se puede usar, y dice cuándo no sabe

Ningún número se mueve. El pendiente 3 llevaba abierto desde v0.1.87, cuando
el panel *Query Slice Data* pasó de enseñar guiones a enseñar números pero se
quedó sin los tres botones que la referencia describe.

---

## 1 · Los tres botones

- **Copy** — la tabla al portapapeles como TSV. Separado por tabuladores y no
  por comas porque el destino es una hoja de cálculo o una tabla de informe, y
  varias de estas etiquetas llevan comas dentro.
- **Zoom Slice** — centra la vista en la dovela. Reutiliza
  `CanvasView.zoom_to_point()`, que ya conserva el eje y hacia arriba del
  modelo; un zoom escrito aquí habría tenido que redescubrir eso por las
  malas. El semiancho es el tamaño de la propia dovela, así que llena la vista
  con algo de su entorno en vez de convertirse en un punto.
- **Hide / Show Geometry** — deja en pantalla sólo la dovela, para capturas.

Copy y Zoom se desactivan sin dovela; ocultar el modelo no la necesita, porque
va del modelo y no de la dovela.

Dos detalles que no son adorno:

**Los ajustes se restauran de una copia guardada, no poniéndolo todo en
visible.** El usuario puede haber apagado capas en *Display Options* antes de
pulsar; volver con todo encendido sería que el panel le cambia la vista por su
cuenta.

**El resaltado se vuelve a dibujar desde
`_refresh_canvas_with_highlights`**, que v0.1.82 dejó escrito como «el ÚNICO
sitio que dibuja el resultado». Ocultar la geometría reconstruye la escena, y
la dovela que el usuario había pulsado el botón para fotografiar habría sido
justo lo que la reconstrucción se llevaba por delante.

## 2 · Las fuerzas entre dovelas, y la única decisión de criterio

Sección nueva en el panel con `E` y `X` en las dos caras verticales, y flechas
en el lienzo. **Se dibujan si y sólo si el método publicó
`result.details["boundary_ratios"]`** — la inclinación interdovela que de
verdad resolvió.

Hoy la publican Spencer, GLE y Lowe-Karafiath. Bishop, Janbu y Ordinary no,
porque **no la forman**: Bishop asume que el cortante entre dovelas es cero,
Janbu aplica una corrección en su lugar, Ordinary las ignora.

Preguntar por el **dato** y no por una lista de nombres de método tiene dos
motivos, y el segundo es el que importa:

- un método que se añada después y resuelva λ hereda las flechas sin que nadie
  edite una lista, y uno que no lo haga no puede recibir números que nunca
  calculó;
- dibujar una flecha para Bishop sería dibujar la **suposición** del solver
  como si fuera un resultado. Es exactamente el error que v0.1.82 quitó de la
  línea de empuje, y merece no cometerse dos veces.

Hay un test a nivel de fuente que falla si alguien «aclara» ese criterio
convirtiéndolo en una tupla de identificadores de método.

Cuando el dato no está, el panel **lo dice con palabras**: «no — este método no
las resuelve». Un guión se lee como «no hay dato», y la verdad es «este método
no tiene ese concepto».

Las fuerzas interdovela entran además en la escala de las flechas. Son del
mismo orden que el peso, así que dejarlas fuera encogía todas las demás en
cuanto aparecían.

## 3 · Un test que hubo que reescribir, no relajar

`test_interpret_slice_data_v187.py::test_no_field_is_left_as_a_dash` exigía que
**ningún** campo quedara en guión — era la queja entera de v0.1.87. Ahora los
cuatro de interdovela lo quedan, porque ese panel se conduce con Bishop.

No se ha bajado la exigencia: el caso pasa a llamarse
`test_no_field_the_method_can_compute_is_left_as_a_dash` y afirma **dos** cosas
donde antes afirmaba una — que ningún campo calculable queda vacío, y que los
cuatro de interdovela están **todos** en guión, no algunos. Así la excepción no
puede convertirse en un agujero.

---

## Fuera del repositorio: `referencias/Ejemplos/`

No lleva versión —esa carpeta no está bajo control de versiones— pero se hizo
en esta tanda.

**`README.md`**: qué es cada ejemplo, de qué raíz sale, qué cambia y qué
despejó. Incluye **el formato del `.s01`**, que es la llave de todo el trabajo
de las últimas cuatro versiones y no estaba escrito en ningún sitio: el orden
de los siete factores de seguridad, los códigos de error negativos, y que los
`.sli` son CRLF — detalle que hace que cualquier lectura con expresiones
regulares ancladas en `\n` devuelva vacío y parezca que el archivo no tiene
nada.

**Diez `.ogr` generados** desde su `.sli`, campo a campo, uno por escenario y
junto a su `.slim`. Los diez cargan, resuelven sus tres regiones, y los dos no
circulares llevan la superficie dibujada visible en el lienzo.

### Dos cosas que aparecieron al hacerlo

**`PGR_Slip2D_Ej_1_General.ogr` no tiene la rejilla de su propio `.sli`**:
lleva (24,40)-(120,140) 12×12 donde el modelo de referencia dice
(40,30)-(120,120) 20×20. No ha afectado a ninguna validación —los tests
construyen la rejilla en código— pero ese archivo no es una copia fiel y ahora
está dicho.

**OGR no tiene «analizar exactamente esta superficie»**, que la referencia
llama *Add Surface*. Las superficies no circulares dibujadas a mano se guardan
como objeto de Block Search para que se vean en el lienzo; evaluarlas hay que
hacerlo por programa. Es un hueco de funcionalidad real, anotado.

---

## Archivos

- `ogr_gui/interpret_window.py` — botones, sección interdovela, flechas,
  `solves_interslice()`, `_zoom_to_current_slice()`, `_set_geometry_hidden()`.
- `ogr_gui/i18n/__init__.py` — 14 cadenas nuevas con su español.
- `tests/test_slice_panel_buttons_v191.py` — nuevo, 17 casos.
- `tests/test_interpret_slice_data_v187.py` — el caso de los guiones,
  reescrito más exigente.
- `referencias/Ejemplos/README.md` y diez `.ogr` (fuera del repositorio).

## Probado

- Suite entera sin argumentos.
- `tests/_runner.py slice_panel_buttons i18n_coverage menu_reachability
  interpret` — 150/150.
- Los diez `.ogr` cargan con `Project.load` y resuelven sus regiones.

## Sin probar

- El aspecto de las flechas y del panel en pantalla real. Los tests comprueban
  que los elementos existen y que el criterio decide bien, no que se vean
  bonitos.

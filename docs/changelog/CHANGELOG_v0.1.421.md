# OGR Slip2D v0.1.421

**Cinco detalles de la sexta prueba de la interfaz (D363):**
- un rechazo de resistencia del API nombra su material;
- Interpretar se abre en la pantalla de la ventana principal y dentro de ella;
- Interpretar no corta ningún texto a 1536 ni a 1280 px, en ninguno de los dos idiomas;
- los diálogos se titulan por su nombre, sin los «...» del menú, y el nombre del programa ya no se repite en el
  título;
- la guía del servidor MCP dice que un *Calcular* de la ventana no tiene `result_id`.

Es la quinta de la tanda P8o. La ficha sale de H4, H5, H7, H8 y B2b de `INFORME_prueba_GUI_0.1.357.md`, medidos por
`repro_d363.py`. **Decisiones de la propietaria (2026-11-03):**
- el punto 5 se documenta, en vez de dar identificador a un *Calcular* de la ventana;
- fuera `setApplicationDisplayName`.

Ningún número cambia. El inglés del API tampoco, salvo el nombre del material.

## 0. Lo que se encontró, punto por punto

1. **«Material '?'».** `strength_from_spec` (`ogr_api/catalog.py`) preguntaba la regla de resistencia sin nombre
   (`strength_model_refusal(model, None)`), y el marco del mensaje escribe «?» cuando no lo hay. Sus dos llamadas, la
   de un material nuevo y la de uno que se edita, tenían el nombre a mano. La ventana ya lo pasaba. Pasaba con todo
   rechazo de resistencia por el API desde 0.1.218 (D209).
2. **Interpretar se abría donde caía.** El constructor solo hace `resize(1200, 800)` y `act_interpret` la enseñaba
   sin colocarla. La prueba la vio en la otra pantalla y con la barra de título por encima del borde.
   - Sin pantalla, la de offscreen mide 800 × 800, y el marco de Interpretar salía de 1204 × 804.
3. **Textos cortados en Interpretar.** El censo nuevo (títulos de los paneles, cabeceras de las tablas y el título de
   la leyenda, con lo que cada uno necesita frente a lo que tiene) encontró, en castellano y a 1536 × 823:
   - el título del panel «Leyenda»: necesita 59 px y tiene 54. El panel mide lo que la leyenda, 96 px;
   - las cabeceras de *Superficies*, que se estiraban a partes iguales: «Método», «Centro X», «Centro Y» y «Radio».
     Desde 0.1.419 son siete columnas en 331 px, así que cada una tenía 48–49 px;
   - **uno que la ficha no decía:** el título dentro de la leyenda, «Factor de seguridad», pintado en una sola línea
     de 96 px cuando necesita 153.
   - En inglés y a 1280 px, lo mismo salvo el panel.
4. **Los títulos.**
   - Cuatro diálogos llevaban de título la clave del menú, con sus «...»: *Opciones de visualización*, *Definir
     materiales*, *Preferencias* y *Ajustes de proyecto*. «Calculando...» es un proceso en marcha y se queda.
   - `setApplicationDisplayName("OGR Slip2D")` hace que Qt añada « - OGR Slip2D» a todo título que no acabe así, y el
     de la ventana principal ya empieza por el nombre.
5. **Los resultados de *Calcular* desde el API.** Los identificadores solo los crea `analysis_run`, y nada de
   `ogr_gui` escribe en `handle.results`.

## 1. Qué cambia

- **`ogr_api/catalog.py`:** `strength_from_spec(spec, name=None)`, y el nombre llega a la regla.
  - `_new_material` le pasa el del material nuevo.
  - `material_set` le pasa el que tendrá el material, el nuevo si se renombra en la misma llamada.
  - `model_define` pasa por `_new_material`.
- **`ogr_gui/dialog_size.py`:** `place_on_screen_of(window, anchor, wanted)`.
  - Abre la ventana en la pantalla del ancla, con el tamaño pedido acotado por el área disponible de esa pantalla.
  - La centra sobre el ancla y la mueve para que su marco entero, con la barra de título, quede dentro.
  - El marco se toma del ancla, porque el gestor de ventanas lo pone al enseñarla.
  - `act_interpret` la llama antes de `show()`.
- **`ogr_gui/widgets/legend.py`:** el título se parte por palabras (`title_rect`), con la altura que pida.
- **`ogr_gui/interpret_window.py`:**
  - `_fit_dock_titles` da a cada panel, como mínimo, el ancho de su título;
  - la tabla *Superficies* pone cada columna al ancho de su contenido, cabecera incluida (`ResizeToContents`), y se
    desplaza de lado cuando no caben.
- **`ogr_gui/widgets/results_dock.py`:** lo mismo en el panel de resultados de la ventana principal. No lo pedía la
  ficha, pero tiene la misma tabla, y desde 0.1.419 también siete columnas.
- **Los títulos:** claves nuevas sin «...» para los cuatro diálogos, con su castellano. `ogr_gui/__main__.py` ya no
  pone el nombre a mostrar.
- **`docs/mcp/clientes.md`:** «al revés no». Un *Calcular* de la ventana no tiene `result_id`, y el agente lanza su
  propio `analysis_run`.
- **`tests/test_sixth_test_details_v1421.py`,** nuevo, con 6 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Una decisión que no tomé, para la propietaria

- El plan decía que «Untitled» y «Demo slope» del título de la ventana principal pasarían por `tr()`. **No lo hice.**
- `test_gui_spanish_v1318` los declara a propósito como el **nombre del proyecto**, un dato que también sale, por
  ejemplo, en el título del informe.
- Traducirlos solo en el título haría que la ventana dijera «Talud de ejemplo» y el PDF «Demo slope».
- La opción del plan la redacté yo sin tener presente esa decisión de D318. Si se quiere, hay que decidir qué hacer
  con el nombre del proyecto en los dos sitios.

## 3. Qué se probó

- **`tests/test_sixth_test_details_v1421.py`,** con 6 tests:
  - el Hoek-Brown con a = 1,2 por el API dice «Material 'roca'». Lo comprueba al editar, al renombrar en la misma
    llamada («granito»), al crear («roca2») y en `model_define`, sin «'?'», con el resto del mensaje en su inglés;
  - **la colocación, por la acción real:** la ventana principal abre Interpretar con `act_interpret` en la pantalla
    offscreen (800 × 800), y el marco cabe en el área disponible de la misma pantalla;
  - **el censo de Interpretar,** con el modelo de `repro_d363.py`, en castellano y en inglés, a 1536 × 823 y a
    1280 × 720: ningún título de panel, cabecera de tabla ni título de la leyenda se queda sin sitio;
  - los cuatro diálogos, en los dos idiomas, sin «...» («Preferencias», «Ajustes de proyecto»);
  - `__main__` ya no llama a `setApplicationDisplayName`, leído con el AST, y sí a `setApplicationName`;
  - la guía dice «al revés no», con `result_id` y `analysis_run`.
- **La discriminación,** con el árbol de 0.1.420 y el test copiado: **fallan los 6**, por comportamiento.
  - El primer borrador probaba la colocación llamando a la función nueva, y la leyenda con su método nuevo, así que
    en el árbol viejo fallaba por su ausencia.
  - Ahora la colocación se mide en la ventana que abre la acción (marco de 1204 × 804 en una pantalla de 800 × 800),
    y la leyenda se mide en una sola línea si el árbol no sabe partirla.
- **Los vecinos:** los censos de diálogos, los cuatro diálogos, la leyenda, Interpretar, los dos paneles de
  resultados, el API de materiales, de modelo y de resistencias, el catálogo, el servidor MCP, los títulos, el
  castellano y el idioma: 390 de 390.
- **La suite entera con `--jobs 4`:** **7100 de 7100**, `Failed: 0`, sin `Leaks` ni `Chunks died`. La serie no toca.
- **El banco:**
  - `d363()`, nueva en el `verificar_cierres.py` de la raíz, mide los cinco puntos.
    - Con 0.1.420 da SIGUE ABIERTO en los puntos 1 a 4: «'?'», el marco fuera, 6 textos cortados y títulos con
      «...».
    - El 5 sale bien también allí, porque la guía se lee del repositorio vivo: es documentación, no código del
      árbol.
    - Con 0.1.421 da CUBIERTO POR TEST.
  - El VC de la raíz entero da 131 comprobaciones con 0 bajadas.
  - El del 02 en seco da 242 de 242 iguales a los archivados.
  - D363 se cierra:
    - instantánea y retirada;
    - `PAQUETES` podado y la cadena tachada;
    - 35 prompts, con las 17 FALTA anteriores;
    - auditorías con 0 ERROR;
    - instantánea `--forzar`.
  - El prompt de la prueba a mano de la tanda está en `_auditoria/P8_interfaz/PROMPT_prueba_GUI_0.1.421.md`, y el
    informe irá en `INFORME_prueba_GUI_0.1.421.md`.

## 4. Qué falta

- **A mano:** Interpretar en dos pantallas de escala distinta (100 % y 125 %), con la ventana principal en la segunda,
  y maximizada a 1536 px. Va en el prompt de la prueba a mano del final de la tanda.

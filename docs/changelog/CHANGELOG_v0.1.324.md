# OGR Slip2D v0.1.324

**El castellano que la tercera prueba de la interfaz aún vio en inglés:**

- los métodos con su nombre y no con su identificador;
- los títulos de cinco paneles;
- las ayudas de todos los modos de herramienta;
- «rejilla» donde se decía «malla» (D315, D316, D317).

Primera versión de la tanda P8i.

## 0. Lo que se encontró

La tercera prueba de la interfaz (`_auditoria/P8_interfaz/INFORME_prueba_GUI_0.1.323.md`, H1, H6 y H7)
y su medida en el código:

- **D315, el identificador del método en pantalla.** «bishop_simplified» salía en el panel de
  resultados (resumen y columna Método), en la barra de estado tras calcular y en *Interpretar*
  (resumen, tabla, título del diagrama de sólido libre y la etiqueta junto a la barra de método).
  - Iba como argumento de un `tr(...).format(...)` o directo a una celda, sitios que no mira ningún
    censo de AST.
  - La revisión de los 158 sitios de 0.1.321 solo siguió las variables pasadas directamente a una
    llamada visible.
  - **La etiqueta de *Interpretar* no estaba en la lista de la ficha:** la encontró el test de
    pantalla ampliado de esta versión.
  - **Tampoco la barra de *Interpretar agua subterránea*,** que decía «FoS bishop_simplified=…» y
    «NOT CONVERGED» sin `tr()`. Las dos cosas se metían con `bits.append(...)` en una lista que
    después se une en el texto, otro sitio que el censo no ve. Lo destapó un test que fijaba ese
    identificador.
- **D315, los títulos de panel.** Cinco paneles se titulaban con `super().__init__("Results",
  parent)`: Results, Summary, Surfaces, Assign Materials y Terminal. El censo de AST de
  `test_gui_spanish_v1318` no leía esa llamada.
- **Por qué no lo vio el test de pantalla de 0.1.321:**
  - no recorría títulos de panel, celdas de tabla ni la barra de estado;
  - «bishop_simplified» no tiene ninguna palabra de su lista de palabras inglesas;
  - el resultado iba rodeado de castellano («Método: … Válidas: …»), y el heurístico lo daba por
    castellano.
- **D316, las ayudas de modo.** No eran dos: **32 de las 39** ayudas de `canvas/tool_mode.py` no
  tenían castellano.
  - La ventana principal escribe enseguida su propio mensaje traducido encima de la mayoría, y por eso
    la prueba solo vio las de *Mover contorno* y *Añadir soporte*.
  - **No era un hueco desconocido.** `test_add_surface_three_points_v1168` contaba desde v0.1.168
    las ayudas sin castellano y las fijaba como techo (`_HINTS_WITHOUT_SPANISH = 32`). El techo
    medía, pero nadie lo bajó. Baja a 0.
- **D317, «malla» por «rejilla».** Seis entradas más que 0.1.323 no buscó: «Tipo de malla:», «Mostrar
  malla», «(el método no es de malla)», «…la malla de búsqueda de círculos», «…cada centro de la
  malla» y «…la malla de centros».
- **Otro par que sale de aquí, para D318 (0.1.325):** el diccionario dice «contorno exterior» (17
  entradas) y «contorno externo» (12). Las ayudas nuevas ya usan «exterior».

## 1. Qué cambia

- **El nombre del método** (`ogr_gui/labels.method_name`) en esos nueve sitios. La exportación a
  CSV conserva el identificador, porque es dato.
- **«FS {0}» y «NO CONVERGIDO»** en la barra de *Interpretar agua subterránea*.
- **`tr()` en los cinco títulos de panel**: «Resultados», «Resumen», «Superficies», «Asignar
  materiales» y «Terminal de Python».
- **El castellano de las 32 ayudas de modo**, en tuteo como los mensajes de la ventana («Pulsa un
  contorno y arrástralo para moverlo, Esc para salir»).
- **«rejilla» en las seis entradas** de D317.
- **El censo de AST** (`test_gui_spanish_v1318`) lee también `super().__init__("…")` en una subclase de
  un widget que enseña su primer argumento. Con el código de 0.1.323 encuentra justo los cinco
  títulos.
- **El test de pantalla** (`test_labels_spanish_v1321`):
  - calcula el ejemplo;
  - recoge también los títulos de panel, las celdas de tabla (20 filas) y la barra de estado;
  - cuenta como inglés cualquier texto que contenga un identificador guardado de `ogr_gui.labels`
    (`bishop_simplified`, `grid_total_head`…), aunque lleve castellano alrededor.
- **36 claves nuevas** (dos títulos, 32 ayudas y los dos textos de *Interpretar agua
  subterránea*) **y 6 valores cambiados**, sin claves repetidas.
- **Tres tests fijaban lo que esta versión corrige**, y pasan a medir el comportamiento nuevo:
  - `test_interpret_i1_v149`: la etiqueta de *Interpretar* nombra el método («Bishop
    Simplified», «Spencer»);
  - `test_initial_factor_v1309`: «FoS Bishop Simplified=» en la barra de *Interpretar agua
    subterránea*;
  - `test_add_surface_three_points_v1168`: el techo de ayudas sin castellano, de 32 a 0.

## 2. Tests

`tests/test_spanish_leftovers_v1324.py` (nuevo), 6 casos:

- toda ayuda de `ToolMode` tiene castellano, y las dos que vio la prueba dicen lo esperado;
- ninguna clave con *grid* (y sin *mesh*) se traduce con «malla»; **control:** la malla de elementos
  finitos sigue siendo «Malla de elementos finitos»;
- con el ejemplo calculado en castellano:
  - el panel se titula «Resultados»;
  - su columna Método dice «Bishop simplificado»;
  - la barra de estado nombra el método.

  **Control:** en inglés, «Results» y «Bishop Simplified»;
- *Interpretar* titula «Resumen» y «Superficies», y su tabla nombra los métodos.

**Con el código de 0.1.323 fallan 5 de los 6 casos;** el control pasa. También fallan:

- los dos casos de presupuesto del censo de AST, que encuentra los cinco títulos de panel;
- el test de pantalla ampliado, con «Results», «Método: bishop_simplified…» y
  «bishop_simplified» en *Interpretar*.

Se corrió sobre un `git archive` de 0.1.323, sin el buscador editable.

## 3. Verificación

- **Los tests de esta versión**, 54/54. Los vecinos, 581/584 a la primera: los tres que fallaron
  fijaban lo que se corrige (§1) y pasan a medir lo nuevo. Después, 68/68 y 28/28.
  - Son resultados, *Interpretar*, terminal, asignar materiales, lienzo, barra de estado, leyenda,
    menús, la ventana en los dos idiomas, retroanálisis, estadística, modos de herramienta, rejilla,
    presiones de agua y opciones de visualización.
- **Suite entera:** 6157/6157, `EXIT=0`, 82 min.
  - Es más larga que las anteriores (54–62 min), y lo atribuyo a que el test de pantalla ahora
    calcula el ejemplo. No está medido aparte.
- **Banco:**
  - `verificar_cierres.py` entero: 64 comprobaciones, D315, D316 y D317 **CUBIERTO POR TEST** y 0
    bajadas;
  - instantánea `Evaluaciones/0.1.324`, las tres retiradas y podadas de P8;
  - prompts (46);
  - auditorías con 0 ERROR.
- **Ningún número del motor cambia:** es texto de pantalla.

## 4. Pendiente

- **El resto de P8i:**
  - D318: términos, con «contorno exterior»;
  - D319–D330.
- **A mano, en la cuarta prueba de la interfaz:** el panel de resultados, *Interpretar* y las ayudas de
  los modos.

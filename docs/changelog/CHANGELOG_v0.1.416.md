# OGR Slip2D v0.1.416

**Las herramientas de anotación se dibujan con clics en el lienzo (Herramientas → Dibujar, Cotas y Añadir ejes), con
el forzado, la vista previa, Intro/Hecho y Esc de los contornos. Ninguna pide ya coordenadas en un cuadro (D354).**

Es la quinta y última de la tanda P8n. La propietaria decidió el 2026-11-02: solo clics. Un punto exacto se escribe
como en todo dibujo, en la casilla X,Y de la barra de estado o en la Tabla de coordenadas del menú del botón derecho;
el texto de *Añadir texto* se pide en un cuadro después del clic.

Lo que se guarda no cambia: el tipo, los puntos, el texto y el estilo, y por tanto tampoco el DXF ni el PNG.

## 0. Lo que se encontró: el inventario

Las doce herramientas pasaban por una sola función, `_start_annotation`, que pedía los puntos con
`QInputDialog.getText` («Introduce N punto(s) como x,y  x,y …»). Su docstring decía que se tecleaban «por ahora»,
para colocar una figura exacta.

| Menú | Herramienta | Puntos | Antes | Ahora |
|---|---|---|---|---|
| Dibujar | Línea, Flecha | 2 | teclado | clics |
| Dibujar | Polilínea | 2 o más | teclado | clics, termina con Intro o Hecho |
| Dibujar | Polígono | 3 o más | teclado | clics, termina con Intro o Hecho |
| Dibujar | Rectángulo | 2 esquinas | teclado | clics, se ve el rectángulo |
| Dibujar | Círculo | centro y un punto | teclado | clics, se ve el círculo |
| Dibujar | Añadir texto | 1 y el texto | teclado ×2 | un clic y el texto en un cuadro |
| Cotas | Acotar longitud, Cota X, Cota Y | 2 | teclado | clics |
| Cotas | Acotar ángulo | 3, el vértice el del medio | teclado | clics |
| Herramientas | Añadir ejes | 2 esquinas (D332) | teclado | clics |

- **Ya iban por clics:** *Medir* (D329a), y *Acotar longitud* en Interpretar, que no guarda nada.
- ***Añadir imagen*** no pide puntos: abre el archivo y la pone sobre la extensión del modelo.
- **Fuera de la ficha:** `_read_points`, que usan el foco de búsqueda y la superficie tecleada, también teclea, pero
  no son anotaciones.
- **El polígono** aceptaba dos puntos por teclado. Ahora pide tres, la regla de `Annotation.outline`.

## 1. Qué cambia

- **`ogr_gui/canvas/tool_mode.py`:**
  - un modo por herramienta, como los cuatro de Block Search: `DRAW_ANN_LINE` … `DRAW_ANN_AXES`;
  - `annotation_kind_drawn`, `is_drawing_annotation`, `annotation_min_points` y `collects_points`, que es un
    contorno o una anotación;
  - `points_to_finish`:
    - texto 1;
    - línea, flecha, rectángulo, círculo, las tres cotas de dos puntos y los ejes 2;
    - ángulo 3;
    - polilínea y polígono 0, porque terminan cuando lo dice el usuario;
  - el cursor de cruz;
  - una ayuda por modo, con su castellano.
- **`ogr_gui/canvas/canvas_view.py`:**
  - los siete sitios que leían `is_drawing_boundary` leen `collects_points`. Son el clic, el movimiento con el
    forzado y la vista previa, Intro, el menú del botón derecho, la casilla X,Y (`add_manual_point`), el punto de
    referencia del orto e `is_drawing`;
  - `_finish_drawing` entrega una anotación por su señal, `annotation_drawn(kind, points)`, y vuelve a Seleccionar,
    lo que borra el marcador del forzado. Con menos puntos de los que hacen falta lo dice y sigue dibujando;
  - la vista previa del rectángulo, el círculo y el polígono es su forma, sacada del mismo `outline` que dibuja y
    exporta.
- **`ogr_gui/main_window.py`:**
  - cada entrada del menú llama a `_start_annotation(mode=ToolMode.…)`, que solo entra en el modo. El censo de
    modos lee el `mode=`;
  - `_on_annotation_drawn`, con `@undo_step("Set annotation")`, guarda la anotación: un paso por anotación, como
    antes. Para un texto pregunta las palabras, y Cancelar es `STEP_CANCELLED`;
  - el mensaje «Anotación añadida: …» es el de antes.
- **`ogr_gui/i18n/__init__.py`:** el castellano de las doce ayudas.
- **Cambiados a propósito,** porque el cuadro de coordenadas ya no existe:
  - `test_annotations_drawn_v1330`: «la ventana pide dos» pasa a «toma dos». Con una esquina espera; con la segunda
    deja los ejes;
  - `test_undo_settings_annotations_v1305` y `test_texts_spanish_v1370`: el paso y el mensaje son los de la
    anotación dibujada;
  - `test_add_surface_three_points_v1168`: el total de ayudas pasa de 34 a 46, y todas tienen su castellano.
- **`tests/test_annotation_clicks_v1416.py`**, nuevo, con 6 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_annotation_clicks_v1416.py`,** con el lienzo real (mostrado, a 15 px por metro, sin forzado ni orto,
  clics de verdad con `QTest`) y `QInputDialog.getText` sustituido. Contesta solo la pregunta del texto, cancela
  cualquier otra y las apunta todas:
  - las doce entradas del menú:
    - entran en su modo;
    - sus clics dejan la anotación de su clase en los puntos pulsados, a menos de un píxel;
    - es un solo paso «Set annotation», que deshacer y rehacer devuelven exactamente;
    - el lienzo vuelve a Seleccionar sin marcador;
    - la única pregunta en todo el recorrido es la del texto;
  - el texto es el contestado;
  - el polígono con dos puntos e Intro dice «This shape needs 3 point(s).» y sigue; con el tercero se cierra;
  - la casilla X,Y de la barra pone un punto exacto, al bit;
  - Esc y un texto cancelado no dejan nada, ni paso, ni cambios sin guardar.
- **La discriminación,** con el árbol de 0.1.412 y el test copiado: fallan 5 de 6, el de Esc es la guarda.
  - El primer borrador del falso contestaba también la pregunta de coordenadas. En el árbol viejo eso abría el aviso
    modal «No se ha podido leer…» y la corrida se colgó.
  - Ahora cancela todo lo que no sea el texto, y el árbol viejo falla sin colgarse.
- **`d354()`** da SIGUE ABIERTO con 0.1.412: 0 de 12, y 12 preguntas de coordenadas. Con 0.1.416 da CUBIERTO POR
  TEST: 12 de 12, una sola pregunta, la del texto.
- **Los vecinos:** anotaciones (dibujadas, a DXF, a PNG, oscuras), expandir dibujando, Medir y Acotar, los menús, los
  modos y su censo, añadir superficie, el lienzo, el forzado, el castellano, las traducciones, Interpretar, la
  casilla X,Y y la polilínea de Block Search: 554 de 554.
- **La suite entera con `--jobs 4`:** **7050 de 7050, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 25,4 min. La
  serie no toca: 17 commits desde la última.
- **El banco**, al cerrar la tanda:
  - `verificar_cierres.py` entero en la raíz da 126 comprobaciones con 0 bajadas;
  - el del 02, entero y no en seco, salió con **una bajada apartada: D102**. Ver la sección 3;
  - D354 se cierra: instantánea, retirada, `PAQUETES` podado, cadena tachada, prompts y auditorías con 0 ERROR en la
    raíz y en el 02.

## 3. Una bajada del banco que traía 0.1.414, y una medida mía que la tapó

- **Lo que pasó.** `d102()` del 02 (el rótulo de la acción de búsqueda por bloques, 0.1.166) cuenta el texto de los
  símbolos que aquel cambio renombró. Uno es «Add Block Search Object», la etiqueta vieja de la acción. Lo busca en
  `ogr_core`, `ogr_slip2d`, `ogr_fem2d` y `ogr_cli`, para asegurar que el renombrado no podía mover un número.
  - El docstring de `add_boundary_step_name` (D349, 0.1.414) usaba justo ese texto como ejemplo de nombre de paso.
  - Es una coincidencia de texto, no un uso del símbolo viejo: en ejecución, el nombre se arma con
    `f"Add {display_name}"` y no hay ningún literal.
  - Pero la comprobación no se puede cumplir con ese docstring, y bajó de CUBIERTO POR TEST a NO SE SOSTIENE.
- **El arreglo,** en esta versión y sin tocar la comprobación del banco: el ejemplo del docstring pasa a «Add Tension
  Crack». `d102()` vuelve a CUBIERTO POR TEST, y el 02 queda con 0 bajadas.
- **La medida equivocada, mía.** En 0.1.414 y 0.1.415 comparé los veredictos del 02 en seco con un script que se
  quedaba con la ÚLTIMA línea de cada ficha. El 02 imprime, debajo de una que cambia, una segunda línea
  «CUBIERTO POR TEST -> NO SE SOSTIENE», y el script leyó en ella el veredicto de antes.
  - Los changelogs de esas dos versiones dicen «234 de 234 iguales», y es falso: D102 ya había bajado en 0.1.414.
  - Corregido en los dos changelogs, con una nota.
  - Vuelto a medir con la primera línea de cada ficha: el único cambio de la tanda en el 02 es D102, y con 0.1.413
    no había ninguno.

## 4. Qué falta

- **La prueba a mano de la tanda P8n entera** (D369, D350, D349, D353 y D354), con el prompt
  `_auditoria/P8_interfaz/PROMPT_prueba_GUI_0.1.416.md` del banco.
  - Allí se ve lo que un test sin pantalla no ve: el ratón real, el tema oscuro en el escritorio, los 6 s del mensaje
    a la anchura real.
  - El informe irá en `INFORME_prueba_GUI_0.1.416.md`.

# OGR Slip2D v0.1.413

**En el tema oscuro, una anotación con el color por defecto se dibuja con la tinta del tema y se lee; lo que se
guarda y lo que se exporta no cambia (D350).**

Es la segunda de la tanda P8n. La salida la eligió la propietaria el 2026-11-02 entre las tres de la ficha: invertir
al dibujar, y solo el color por defecto. Las otras eran «por defecto» sin color guardado, o un halo. Ningún número
se mueve.

## 0. Lo que se encontró

- **El color por defecto de una anotación es `#202020`** (`AnnotationStyle.colour`), y se guarda con ella en el
  `.ogr`. El lienzo lo dibujaba tal cual en los dos temas: en el oscuro, sobre `#1f1f1f`, son **1,01:1** de
  contraste.
  - Por eso la prueba de 0.1.355 (H12) solo leyó «eba», donde el texto cruzaba las celdas grises de la rejilla. En
    una captura del lienzo, el píxel más contrastado bajo el texto da 3,4:1, y sale de esa rejilla.
- **`#202020` es exactamente la tinta del tema claro** (`theme_color("ink")`). Dibujar el color por defecto con la
  tinta del tema deja el lienzo claro igual que antes, píxel a píxel. En el oscuro le da `#e0e0e0`, unos 12,5:1.
- **Exportar imagen e Imprimir pintan la escena sobre papel blanco.** `scene.render` no pinta el fondo de la vista.
  Si el lienzo oscuro hubiera aclarado las anotaciones sin más, la figura exportada desde el oscuro habría salido
  gris claro sobre blanco. Las dos pintan ahora con el color guardado, como el DXF y el PNG del API, que no pasan
  por el lienzo.
- **Cambiar de tema con la ventana abierta no tocaba lo dibujado:** `CanvasView.retheme` (D301) cambiaba solo el
  fondo, «lo dibujado conserva sus colores». Ahora las anotaciones se vuelven a dibujar solas, sin redibujar el
  modelo.
- **Lo que no se sabe distinguir:** un `#202020` puesto a mano (solo se puede por el API o en el archivo) se trata
  como el color por defecto. Va dicho, no corregido: distinguirlo pedía guardar «sin color», que es la salida que la
  propietaria no eligió.
- **Reportado y sin tocar:** el contorno exterior (`#2c2c2c`) sobre el lienzo oscuro tiene unos 1,2:1, la misma
  clase de falta. Lo deja así a propósito la decisión de D301: los objetos del modelo no siguen al tema, y un test
  lo fija. Se lee porque lo rellenan los colores de los materiales, pero queda fuera de esta ficha.
- **Un camino equivocado al escribir el test:** el primer cálculo del rectángulo de la captura usaba
  `sceneTransform()` de un texto que ignora la transformación de la vista. Leía sus tamaños en píxeles como metros, y
  el rectángulo medía 2556 px, todo rejilla y fondo, y dio 3,58:1 con el arreglo puesto. Con
  `deviceTransform(viewportTransform())` cae sobre el texto.

## 1. Qué cambia

- **`ogr_core/annotations/annotation.py`:** `DEFAULT_COLOUR = "#202020"`, que usan el dataclass y `from_dict`, sin
  el literal en dos sitios. Lo exporta `ogr_core.annotations`.
- **`ogr_gui/canvas/annotation_items.py`:**
  - una sola función, `_ink(colour, on_paper)`, para el trazo, la punta de flecha y el texto;
  - el color por defecto es la tinta del tema, salvo sobre papel; cualquier otro va tal cual. El relleno no se toca;
  - `annotation_items(annotation, on_paper=False)`.
- **`ogr_gui/canvas/canvas_view.py`:**
  - `_draw_annotations()` dibuja las anotaciones y las superposiciones del lienzo, y nada más;
  - `retheme()` lo llama;
  - el contexto `on_paper()` las dibuja con el color guardado durante el bloque y luego las devuelve.
- **`ogr_gui/main_window.py`:** `_export_image` y `_render_to_printer` pintan dentro de `canvas.on_paper()`.
- **`tests/test_annotation_dark_v1413.py`**, nuevo, con 7 tests y una sola ventana compartida.
- **`tests/test_min_area_zero_v1412.py`**, de la versión anterior, más barato: la rejilla de sus tres corridas baja a
  3 × 3 × 3, porque el círculo del usuario se evalúa sea cual sea la rejilla.
  - Pasa de 21,5 a 3,7 s.
  - El caso del FS crítico compara 0 con null en esa rejilla. Ya no lleva el número del ejemplo, que fijan otros
    tests de la suite y que se midió para el changelog de 0.1.412.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_annotation_dark_v1413.py`:**
  - el contraste WCAG contra el fondo del lienzo del texto, la flecha y la línea con el color por defecto es de 4,0
    o más en los dos temas (el suelo de D301). Se lee de los elementos y de una captura del lienzo, y el tema se
    cambia por `_apply_theme`, el camino de Preferencias;
  - en el claro el texto sigue siendo `#202020`;
  - un cambio de tema con la ventana abierta recolorea sin redibujar a mano;
  - un `#12ab34` elegido sale igual en los dos temas;
  - lo guardado sigue siendo `#202020`, y el DXF también;
  - Exportar imagen da la misma imagen en el oscuro que en el claro, y después el lienzo vuelve a la tinta del tema.
- **La discriminación,** con el árbol de 0.1.412 (`git worktree` de 4fd6824, el test copiado y sin el buscador
  editable): fallan 4 de 7, con 1,01:1 en los elementos y 3,4:1 en la captura. Los 3 que pasan son guardas: el color
  elegido, el `.ogr` y el DXF.
- **`d350()`** da SIGUE ABIERTO con 0.1.412 (claro 15,6, oscuro 1,0) y CUBIERTO POR TEST con 0.1.413 (oscuro 12,5).
- **Los vecinos:** anotaciones, el tema oscuro, el DXF, exportar e imprimir, el redibujado del lienzo, Interpretar y
  el PNG: 433 de 433.
- **La suite entera con `--jobs 4`:** **7025 de 7025, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 26,2 min. La
  serie no toca: 14 commits desde la última.
- **El banco:**
  - `verificar_cierres.py` entero en la raíz da 123 comprobaciones con 0 bajadas;
  - el del 02 en seco da los mismos veredictos que con 0.1.412 (234 de 234);
  - D350 se cierra: instantánea, retirada, `PAQUETES` podado, cadena tachada, prompts y auditorías con 0 ERROR en la
    raíz y en el 02.

## 3. Qué falta

- Verlo a mano en el escritorio real:
  - el tema oscuro con una anotación de cada tipo;
  - Exportar imagen e Imprimir desde el oscuro;
  - y que un cambio de tema con Interpretar abierto también recolorea (su lienzo es el mismo `CanvasView`).

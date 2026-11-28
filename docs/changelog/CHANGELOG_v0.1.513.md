# OGR Slip2D v0.1.513

**D456: en Interpretar, los menús contextuales del modelo ya no ofrecen acciones que no hacen nada.**
Interpretar es una vista de solo lectura, así que sus menús de vértice, contorno, soporte y carga se
quedan con su línea informativa y con lo que solo lee. Las acciones de edición siguen en la ventana
principal, igual que antes.

## 0. Lo que se encontró

- **El mecanismo** (medido en 0.1.485 y leído de nuevo en 0.1.512). El lienzo de Interpretar es un
  `CanvasView`, y un clic derecho en modo de selección abría los mismos menús que en la ventana
  principal. Cada acción solo emite una señal (`vertex_action_requested`, `boundary_action_requested`,
  `support_action_requested`, `load_action_requested`), y esas señales solo las conecta la ventana
  principal. En el talud de ejemplo había 4 + 6 acciones activas, y dispararlas no cambiaba el proyecto.
- **Censo de los menús que puede abrir el lienzo de Interpretar**, con la decisión de la propietaria
  del 2026-11-28 («analiza cuáles mantener y desarrollar y cuáles no tienen sentido»):

  | Menú | Acciones hasta 0.1.512 | En Interpretar desde 0.1.513 |
  |---|---|---|
  | Vértice | Move Vertex, Insert Vertex (after), Edit Coordinates…, Delete Vertex | La línea informativa y **Copy Coordinates** (nueva) |
  | Contorno | Move Boundary, Edit Coordinates…, Convert Boundary…, Delete Boundary; según el tipo, Define Tension Crack…, Block Search Object..., Expand / Shrink…, Change Slope Angle… | Solo la línea informativa (tipo y nombre) |
  | Soporte | Properties…, Stretch, Modify Pattern…, Delete | La línea informativa y **Support Force Diagram...** sobre ese soporte (nueva) |
  | Carga | Modify…, Delete | Solo la línea informativa (magnitud) |
  | Vértice de una superficie del usuario | (sin menú en Interpretar desde 0.1.469) | Sin cambios |
  | Dibujo (Done/Close/Undo…) | No se abre: Measure y Dimension Length no recogen puntos de dibujo (`collects_points` es falso), y un clic derecho fuera de Select no abre menú | Sin cambios |
  | Región o fondo | `canvas_right_click_xy`, sin receptor en Interpretar | Sin cambios: no abre nada |

  Ninguna de las acciones de edición tiene sentido aquí. Editan el modelo, y los resultados que enseña
  Interpretar pueden ser de un modelo anterior (D419). Las dos nuevas solo leen. Copiar las
  coordenadas sirve para llevarlas a otra herramienta. El diagrama de fuerza ya estaba en el menú de
  Interpretar, pero obligaba a buscar el soporte en el combo.
- **Lo que no se encontró:** un camino de edición por arrastre en Interpretar. Mover un vértice solo
  funciona en `ToolMode.MOVE_VERTEX`, y a ese modo solo entra la ventana principal.

## 1. Qué cambia

- `CanvasView.model_edit_menus` (`ogr_gui/canvas/canvas_view.py`) sigue el molde de
  `user_surface_menu` (0.1.469). Está **apagado por defecto** y solo lo enciende la ventana principal
  (`ogr_gui/main_window.py`), que es la que conecta las cuatro señales. Apagado, cada menú enseña su
  línea informativa y solo las acciones de lectura.
- **Copy Coordinates** pone `x<TAB>y` en el portapapeles con `repr`, que es el texto más corto que
  vuelve a leer el mismo double. La línea informativa redondea a tres decimales, así que no vale para
  copiar. La barra de estado de Interpretar dice «Coordinates copied: (x, y).»: Interpretar escucha
  ahora `status_message` del lienzo, que antes no oía nadie.
- **Support Force Diagram...** sale del menú del soporte y emite la señal nueva
  `support_diagram_requested(int)`. Interpretar la conecta a `_support_force_diagram`, que acepta un
  `support_index` solo con nombre: el `triggered` de la acción del menú le pasa su `checked` por
  posición. `SupportForceDiagramWindow` admite `support_index` y lo elige antes de conectar `refresh`,
  así que dibuja una vez y el soporte correcto. Se abre no modal (`keep_chart`), como antes.
- Castellano: «Copiar coordenadas», «Coordenadas copiadas: ({0}, {1}).». «Diagrama de fuerza del
  soporte...» ya existía.

## 2. Tests

- `tests/test_interpret_context_menus_v1513.py` (nuevo, 6 tests). El modelo es el talud de ejemplo con
  dos soportes y una carga lineal. Los menús reales se leen desde un `QTimer` con
  `activePopupWidget()`, la trampa medida en la ficha:
  - el interruptor está apagado en Interpretar y encendido en la ventana principal;
  - el vértice: solo «Copy Coordinates», y el portapapeles recibe `repr(x)\trepr(y)`, restaurado al
    acabar;
  - el contorno y la carga: solo su línea informativa, sin ninguna acción activa;
  - el soporte: solo «Support Force Diagram...», que abre el diagrama no modal sobre el soporte 2, el
    pulsado;
  - ninguna acción de edición en los cuatro menús de Interpretar, y el proyecto sin cambios;
  - el control: en la ventana principal, los cuatro menús con sus acciones de siempre y las cuatro
    señales conectadas. No se disparan porque varias abren diálogos modales.

  Contra 0.1.512 fallan 5 de los 6. Solo pasa el control.
- Áreas `interpret`, `menu_reachability`, `canvas`, `i18n`, `context` y los seis archivos del diagrama de
  fuerza, con `--jobs 4`: 464 casos en verde.

## 3. Lista de comprobación de la guía de interfaz

- Identidad: ningún rasgo de la tabla cambia. No hay ningún nombre comercial.
- Acción: ninguna acción de barra nueva. El diagrama ya estaba en el menú de Interpretar (regla 3) y
  los textos nuevos llevan `tr()` y su castellano. No hay atajos nuevos. Las acciones de edición no se
  deshabilitan: se quitan, porque en Interpretar no aplicarán nunca, y quitarlas es lo que pide la regla 7.
- Diálogo: no aplica, no hay diálogo nuevo. El diagrama sigue no modal y no hay `exec()` en lo que
  corre un test.
- Probado sin pantalla y sin dejar estado: el portapapeles se restaura con `try/finally`.
- Resultado y lienzo: no aplica, no cambian ni colores ni tolerancias.
- Mensaje: «Coordinates copied: (x, y).» dice qué se copió, una vez y en la barra de estado.
- Gemela en `ogr_ui`: no aplica. OGR-GUI no tiene lienzo ni menús contextuales.

## 4. Suite

La suite entera se corre al final de la tanda. Falta la prueba a mano en la ventana real: clic
derecho en Interpretar sobre un vértice, un contorno, un soporte y una carga.

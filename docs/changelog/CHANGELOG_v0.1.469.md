# OGR Slip2D v0.1.469

**La herramienta de ángulos de Sarma y el menú contextual del vértice (D357).** El ángulo de cara de un vértice
interior de una superficie no circular ya no se da solo en la tabla:
- **Superficies → «Definir ángulos de cara de Sarma»:** se pulsa el vértice y después la dirección de su cara. Un rayo
  en vivo llega hasta donde el método cortará la cara, y la barra de estado da el ángulo. Intro permite teclearlo de 0
  a 360°.
- **Superficies → «Quitar ángulos de cara de Sarma».**
- **El menú contextual del vértice:** definir, teclear o quitar el ángulo, y la tabla de esa superficie.
- Cada edición es un paso de deshacer, y la c y la φ del vértice se quedan.
- Los rayos guardados llegan también hasta el terreno.

Ningún factor de seguridad cambia, de ningún método.

Decisiones de la propietaria (2026-11-17):
- **La herramienta guarda θ en (0°, 180°),** la mitad de la recta que sube. Un tecleo de 300° se guarda como 120°, un
  clic por debajo del vértice da la cara que sube, y la barra dice lo guardado. El diálogo de 0.1.465 no cambia.
- **Un punto que es vértice de un contorno y de una superficie** abre un menú con las dos partes. El quiebro del 4,
  (108; 6,4), es también vértice del contacto de materiales.
- **Los rayos, el vivo y los guardados, llegan hasta donde la cara sale del terreno,** con la regla del método.
- **Optimize con datos por vértice se queda como está** (pendiente desde 0.1.465). Se revisa con los ángulos
  optimizados de 0.1.471.
- **En la revisión:**
  - un vértice que comparten dos superficies tiene una parte del menú para cada una; la herramienta toma la primera y
    la barra la nombra;
  - el filtro de selección «Slip surfaces» se consulta;
  - los menús contextuales muertos de Interpretar, de antes, van a una ficha nueva del banco.

## 0. Lo que se encontró

### Las exploraciones del plan (solo lectura)

- **El lienzo no elegía vértices de una superficie del usuario** (`_pick_vertex` solo mira contornos) y no tenía menú
  para ellos.
- **Los rayos guardados tenían un largo fijo,** 0,2 del ancho de la superficie. Podían quedarse cortos o salir por
  encima del terreno, y no eran la cara que corta el método.
- **El método guarda el ángulo tal cual y lee θ mod 180** (`angles.upward`), así que 300° y 120° son la misma cara.

### Al escribir

- **Una sola regla de la cara:** `wedges.vertex_face` da el θ y el tope (donde el rayo sale del suelo) con las piezas
  de `build_wedges`, que ahora la comparte (`_vertex_top`). Sin mover un bit del método: la revisión comparó 33 casos
  con el árbol de HEAD.
- **El rayo en vivo y el punto del vértice son path items,** no line items. D395 midió que `setPen` de un line item
  pierde una referencia a None en Python 3.11 con PySide6 6.12.0, y el lienzo usa path items desde entonces. El plan
  decía `QGraphicsLineItem`.
- **El rayo en vivo va discontinuo y no punteado,** para no contarse entre los rayos guardados (los tests de 0.1.465
  cuentan los path items punteados).
- **Dos trampas de los mutantes** en el arnés ya corregido en 0.1.468:
  - anclas con la sangría de la clase y no la del fuente desindentado;
  - la barra doble de un heredoc, que llegó simple.

  Las dos se arreglaron con anclas de una línea y la herramienta Edit.

### La revisión adversaria (un agente)

No encontró ningún alto. Ningún bit del método se mueve: `build_wedges`, `solve_wedges` y `evaluate_surfaces` dan lo
mismo que HEAD en 33 casos, y el tope de `vertex_face` es el de `build_wedges` en 15 caras dadas.

Encontró cuatro medios, arreglados:
- **Dos superficies que comparten un vértice:** la herramienta y el menú solo llegaban a la primera, sin decir cuál.
  Ahora el menú tiene una parte por superficie, y la herramienta toma la primera y la nombra («superficie 1»).
- **El vértice elegido sobrevivía a Archivo → Abrir** de un proyecto con los mismos id (el mismo archivo, o una copia
  guardada), y el clic siguiente escribía en él. Ahora `_forget_interaction` lo suelta.
- **El menú del vértice de superficie salía también en Interpretar, y no hacía nada:** su lienzo es un `CanvasView` y
  nadie conecta la señal. Ahora solo lo ofrece el lienzo de la ventana principal (`user_surface_menu`).
  - Los menús del modelo que ya estaban (vértice de contorno, contorno, soporte, carga) están muertos igual en
    Interpretar. Van a una ficha nueva, por decisión de la propietaria.
- **«Teclear ángulo de cara…» empezaba en un ángulo guardado fuera de [0, 360] recortado.** −60, la cara de 120°,
  salía como 0, y Aceptar sin tocar nada se rechazaba como cara horizontal. Ahora empieza en la cara guardada,
  θ mod 180.

Y los bajos, también arreglados:
- **Ruido de coma flotante:** 300,1 se guardaba como 120,10000000000002. Ahora se redondea a los cuatro decimales del
  diálogo.
- **La puerta cerrada no paraba la herramienta:** activa antes de pasar a una corrida circular, seguía escribiendo.
  Ahora la escritura pregunta la puerta de las acciones y dice su motivo.
- **El vértice de superficie tapaba las cargas y los soportes** del clic derecho. Ahora va detrás de ellos. El filtro
  «Slip surfaces», que no leía nadie, se consulta al elegir el vértice.
- **Un id que no es cadena** (un archivo editado a mano, un guion) no pasaba por una `Signal(str)`. Las señales llevan
  ahora el id como objeto. Los id repetidos se suman a la familia de D445, en el banco.
- **Un dato con una resistencia mala:** «Quitar» decía que no había ángulo. Ahora dice el rechazo de la regla y dónde
  corregirlo.
- **El punto del vértice se rehacía con su `setPen` en cada movimiento del ratón.** Ahora se hace una vez, y el rayo
  solo recibe su trazado nuevo.
- **`vertex_face` leía el terreno para cada rayo de cada redibujado:** 16 ms por rayo con 5000 vértices de terreno.
  Ahora se lee una vez por dibujo (`face_context`).
- **Un tecleo cuya cara no sale del terreno se guardaba sin decirlo.** Ahora la barra lo dice, como el rayo en vivo.
- **El test dejaba siete mutantes vivos,** y dos de sus aserciones no comprobaban lo que decían: el extremo de la
  superficie, y el vértice movido que en realidad cambiaba el id. Ahora mueren, con un caso cada uno.

## 1. El cambio

- **`ogr_slip2d/sarma/angles.py`:** `upward_degrees(dx, dy)`, el θ en (0°, 180°) de la cara hacia el puntero, a 0,1°.
- **`ogr_slip2d/sarma/wedges.py`:** `vertex_face`, `face_context` y `_vertex_top`, que `build_wedges` usa.
- **`ogr_core/geometry/user_polyline.py`:** `with_vertex_angle`, el ángulo de un vértice con la c y la φ intactas.
- **`ogr_gui/canvas/tool_mode.py`:** `SET_SARMA_ANGLE` y `REMOVE_SARMA_ANGLE`, con su cursor y su pista.
- **`ogr_gui/canvas/canvas_view.py`:**
  - la elección del vértice, en píxeles, y la vista previa;
  - Esc, el botón derecho e Intro;
  - el menú del vértice de superficie, con una parte por superficie y junto al del contorno;
  - los rayos hasta el terreno;
  - las señales `sarma_angle_picked`, `sarma_angle_typed`, `sarma_angle_removed` y `user_vertex_action_requested`.
- **`ogr_gui/main_window.py`:**
  - las dos acciones en Superficies, con su puerta;
  - `_write_sarma_angle`, un paso de deshacer;
  - el tecleo mod 180 y los mensajes;
  - `_edit_sarma_data_of`, la tabla de una superficie dada.
- **`ogr_api/inventory.py`:** las dos acciones, con `user_surface_edit`.
- **Español** de cada texto nuevo.
- **La spec 009:** la tarea 29 y las dos casillas de la ventana hechas.

## 2. El test

`tests/test_sarma_angle_tool_v1469.py`, 33 casos, con la ventana mostrada, el snap apagado y la escala fijada.
Comprueba:
- **el problema 4 publicado** (Hoek 1987):
  - teclear su ángulo da el factor de la herramienta del banco y el publicado 0,434 a ±1 %;
  - un clic sobre el tope publicado de la interfaz guarda el ángulo del punto pulsado, a 0,1° del publicado, y el
    factor a ±1 %;
  - quitarlo devuelve el factor de la política;
- **la regla de la cara:**
  - el tope en forma cerrada y el de `build_wedges`, al bit;
  - la misma recta dada al revés;
  - una cara que sale por un lado del modelo;
- **la regla de la edición:** la c y la φ se quedan, los rechazos con su motivo, las otras filas intactas y el primero
  de dos datos de un vértice;
- **la herramienta:**
  - la elección en píxeles, a dos escalas;
  - la mitad que sube y 300° → 120°;
  - los rechazos en inglés y en español;
  - un paso por edición y deshacer;
  - el rayo en vivo y los guardados hasta el terreno;
  - Esc y el botón derecho;
  - el vértice que cambia (por un redibujado, un Intro, otro proyecto o un cambio de herramienta);
  - la puerta cerrada, el filtro de selección, el dato rechazado, el tecleo y el id que no es cadena;
- **el menú:**
  - las dos partes en el quiebro, y una parte por superficie;
  - el soporte que conserva su menú;
  - el lienzo de Interpretar sin él;
  - cada acción, y en gris con tipo circular;
- **el español.**

Mutantes: `_auditoria/P9_D357/mutants_v1469.py` del banco, con su log. Son 39, contando los de la revisión, y no vive
ninguno.

## 3. La suite

- `test_add_surface_three_points_v1168`: `_HINTS_TOTAL` 47 → 49, las pistas de los dos modos.
- `test_f3b_ops_v1201`: acciones mapeadas 119 → 121.
- **La primera suite entera dio un fallo, de un nombre:** `test_edit_messages_v1434` exige que el nombre de un paso de
  deshacer sea un literal o una elección de literales, para traducirlo, y `_write_sarma_angle` lo recibía en una
  variable. Ahora elige entre los dos literales dentro. Se repitió la suite.

## 4. Verificación

- **La suite entera, `--jobs 4`, tras la revisión:** la primera dio el fallo del apartado 3. La segunda: 8004 casos,
  pasan 8003 y uno queda saltado, sin fugas ni tramos muertos. La última serie en verde es de hace 47 commits.
- **El test nuevo:** 33 de 33. **Mutantes:** 39, ninguno vivo.
- **Los README:** 7970 → 8003 tests.

## 5. Lo que queda

- El banco, tras el commit:
  - la ficha nueva de los menús contextuales de Interpretar, que se abren y no hacen nada;
  - los id repetidos de las superficies del usuario, en la familia de D445;
  - el progreso de D357 y su prompt largo.
- **Prueba a mano para la propietaria:** en el 4 saturado, definir el ángulo del quiebro con el ratón y tecleando,
  quitarlo, deshacer, y el menú contextual en el quiebro.
- 0.1.470: D452, la regla de la raíz junto a un polo.

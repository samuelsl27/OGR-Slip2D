# OGR Slip2D v0.1.431

**Un redibujado del lienzo a mitad de un dibujo ya no rompe las herramientas de dibujo. Lo elegido sobre el modelo no
se da por bueno si el modelo cambió entre medias, y la regla de cada contorno se pregunta al terminar el dibujo
(D398).**
- **El lienzo borra y vuelve a dibujar su escena** en cada evento del proyecto (la edición de un agente, deshacer) y
  con Opciones de visualización. Si pasaba mientras el usuario dibujaba, los elementos de la vista previa morían con la
  escena, pero la lista que los guarda seguía apuntando a ellos.
  - El siguiente movimiento, clic, final del dibujo o cambio de herramienta tocaba uno muerto y lanzaba
    `RuntimeError` («Internal C++ object already deleted»).
  - La lista no se vaciaba nunca, porque vaciarla lanzaba antes: todas las herramientas de dibujo de la sesión
    lanzaban desde entonces, y el dibujo se perdía.
- **Ahora el dibujo sobrevive:** sus puntos siguen, su vista previa se vuelve a dibujar, el siguiente vértice y el final
  entregan todo lo clicado, y cambiar de herramienta no lanza. Un arrastre de Zoom Window en curso se cancela, como lo
  cancela un cambio de herramienta.
- **Pero no a todo.** La revisión vio que lo que ahora sobrevive a un redibujado sobrevivía también a un cambio del
  modelo sobre el que se eligió:
  - **Cambiar ángulo del talud** guarda el pie como índice del contorno exterior. Una edición entre los dos clics lo
    renumeraba, y el clic de la coronación editaba otra cara o lanzaba `IndexError`. Ahora el pie se comprueba al
    clicar la coronación: si en su índice ya no está el vértice clicado, se pide otra vez;
  - **un proyecto nuevo** (Archivo > Nuevo, Abrir, el project_new de un agente) se llevaba el dibujo en curso. Ahora
    se olvida lo que hubiera a medias. Con el mismo proyecto (importar un DXF, Convertir a contorno) el dibujo sigue;
  - **Interpretar** volvía a pintar la línea de empuje de un resultado que, tras una edición del modelo, ya no se
    dibuja (D323). Ahora vuelve con el resultado y solo con él.
- **Y, por decisión de la propietaria, tres cosas anteriores a esta versión que la revisión encontró al lado:**
  - **la regla de cada contorno se pregunta al terminar su dibujo** (`boundary_refusal`), no solo al habilitar su
    entrada de menú. Un nivel freático empezado sin haber ninguno y terminado tras un deshacer o la edición de un
    agente dejaba dos, que `rules.py` prohíbe; el motor lee el más alto, y el número podía moverse sin aviso. Ahora no
    se añade, y la barra dice el mismo motivo que la entrada en gris. Ya pasaba antes con la edición antes del primer
    clic; esta versión lo agrandaba;
  - **Escalar y Rotar** comprueban, como el pie, que el contorno elegido siga en su índice antes del pivote, y su
    sombra se vuelve a pintar tras un redibujado. Antes se escalaba o rotaba otro contorno sin aviso;
  - **las líneas de Show Slices** vuelven con el resultado tras Contour Options, las capas de agua, Cota u Ocultar
    geometría. Antes desaparecían con el menú marcado. Mientras la geometría está oculta no se pintan, porque esa vista
    enseña la dovela sola, y al mostrarla vuelven.
- **En Interpretar,** la etiqueta de consulta se olvida con la escena sin lanzar.
- **AGENTS.md** dice ahora «de los 134 min, 46 eran la máquina», y no «la mitad», por decisión de la propietaria
  (0.1.430, §0).
- **Ningún número cambia.**

Es la cuarta versión de la tanda P10.

## 0. Lo que se encontró

- **Reproducido antes de tocar nada,** con un lienzo suelto en el árbol de 0.1.430:
  - dos vértices de un contorno, `refresh_scene()`, y el movimiento, el tercer clic, el final y la salida del modo
    lanzan los cuatro;
  - no se entrega nada, y el modo no se suelta;
  - **el fallo arrastra:** en el siguiente dibujo, con otra herramienta, lanzan ya sus primeros clics. Es la sesión
    rota que describe la ficha;
  - Zoom Window lanza en el segundo movimiento, al soltar y al salir.
- **Lo que ya estaba bien:** la sombra del arrastre de contornos la anula `_draw_model` desde v0.1.312 (D307), y la
  de Escalar y Rotar se quita dentro de `try/except RuntimeError` desde v0.1.336. La vista previa y la goma no tenían
  ni lo uno ni lo otro.
- **La revisión** (tres lentes, 27 agentes) repasó las 26 herramientas que recogen puntos, las de selección, Escalar,
  Rotar, los arrastres y Zoom Window con un redibujado a mitad: ninguna lanza en esta versión, y en 0.1.430 lanzaban
  todas. Encontró lo de arriba: tres cosas de este diff y tres anteriores.
- **Caminos equivocados:**
  - **La primera versión del arreglo dejaba sobrevivir todo,** y con ello lo elegido sobre un modelo que ya no es el
    mismo. Antes la herramienta se rompía; con el arreglo seguía con un estado caducado. Lo vieron dos lentes de la
    revisión en el pie del ángulo de talud: de un error visible se pasaba a editar otra cara sin aviso.
  - **La comprobación del pie iba detrás de «la coronación es el propio pie»,** y un deshacer que dejaba la coronación
    en el índice viejo del pie hacía que el clic se ignorase sin decir nada. Ahora va delante.
  - **Se descartó olvidar el pie desde el escuchador de eventos del proyecto.** Un cambio que no avisa (un script que
    edita el contorno, como el propio test) lo habría dejado pasar. El pie, y el contorno de Escalar y Rotar, se
    comprueban al usarlos, llegue el cambio por donde llegue.
  - **La primera versión de olvidar al cambiar de proyecto** olvidaba también con el mismo proyecto, que es lo que
    hacen importar un DXF y Convertir a contorno. Ahora solo con otro proyecto.
  - **La primera sonda se colgó** al terminar el contorno externo. La ventana abre un diálogo modal para preguntar si
    sustituye el que ya tiene el modelo de ejemplo. Antes no llegaba ahí, porque lanzaba. El test dibuja los
    contornos en un lienzo suelto, sin ventana ni diálogos.
  - **La sonda moría sin traza:** al salir del modo lanzaba, y mi `sys.excepthook` se tragaba el error. El código de
    salida 1 era la única pista.
  - **La discriminación se colgó una vez en el árbol de 0.1.430.** Allí el segundo nivel freático se añadía, y tras
    añadirlo la ventana abre su aviso de asignar la superficie de agua, que sin pantalla espera para siempre. El test
    sustituye esos avisos en su propia ventana.
  - **El test de la ventana creía tener un lienzo de 900×600,** pero la ventana no se mostraba, y un lienzo dentro de
    una ventana oculta se queda en 98×28 px. Pasaba igual, porque compara con la misma conversión de píxeles. Ahora la
    ventana se muestra y el test comprueba el tamaño.
  - **Los tests del lienzo compartían uno,** y en el árbol viejo un test roto rompía a los siguientes. Ahora cada uno
    tiene el suyo, y cada uno falla por sí mismo.
  - **Mi primer mutante del pie no desactivaba nada:** `False and A or B` vale `B` por la precedencia, y la
    comprobación seguía activa. Con una tolerancia infinita sí, y el test la caza.
- **Un test de otra versión y una comprobación del banco se apoyaban en lo que se arregla:**
  - **`test_add_boundary_step_v1414`** dibujaba cada tipo sobre el modelo de ejemplo saltándose los menús, y tres de
    esos dibujos los prohíbe la regla en ese modelo: un segundo nivel freático, una línea de desembalse sin desembalse
    rápido y un objeto de búsqueda por bloques sin la búsqueda por bloques. Ahora el modelo se prepara para admitir
    cada uno, como haría el usuario, y el test sigue probando lo suyo (el nombre del paso de deshacer);
  - **`d349()` del banco** (cerrada) dibujaba un objeto de búsqueda por bloques sobre el ejemplo y bajaba a SIGUE
    ABIERTO. Se le pone la búsqueda por bloques al cerrar esta ficha. En seco, con eso, vuelve a CUBIERTO POR TEST.

## 1. Qué cambia

- **`ogr_gui/canvas/canvas_view.py`:**
  - `_draw_model`, tras `scene.clear()`, vacía `_draw_preview_items`, anula la goma de Zoom Window (`_zw_rubber`,
    `_zw_start_scene`) y la sombra de Escalar y Rotar, como ya hacía con la del arrastre;
  - `refresh_scene` vuelve a dibujar la vista previa si hay un dibujo en curso, y la sombra de Escalar y Rotar si su
    contorno sigue siendo el elegido (si no, lo dice y lo olvida). Después emite `scene_rebuilt`, una señal nueva para
    quien guarde elementos fuera de las listas de la escena;
  - `_clear_draw_preview` quita sus elementos dentro de `try/except RuntimeError`, el patrón de
    `_clear_transform_target`;
  - el clic de la coronación de Cambiar ángulo del talud comprueba, antes que nada, que en el índice del pie siga el
    vértice clicado, con una tolerancia relativa al modelo. Si no sigue, lo dice y pide otra vez el pie;
  - Escalar y Rotar guardan el `id` del contorno elegido (`_transform_target_id`) y lo comprueban antes del pivote
    (`_transform_target_holds`);
  - `set_project` con otro proyecto olvida lo que hubiera a medias (`_forget_interaction`): el dibujo y su vista
    previa, el pie, el contorno de Escalar o Rotar, un arrastre de contorno y uno de Zoom Window.
- **`ogr_gui/main_window.py`:** `_on_boundary_drawn` pregunta `boundary_refusal` para todo tipo salvo el exterior, que
  tiene su sustitución. Si la regla lo rechaza, no lo añade, y la barra dice el motivo de su entrada en gris
  (`_boundary_refusal_text`) y «The boundary was not added.».
- **`ogr_gui/interpret_window.py`:**
  - escucha `scene_rebuilt`: olvida la línea de empuje y la etiqueta de consulta;
  - `_refresh_canvas_with_highlights`, el sitio donde se dibuja el resultado, vuelve a dibujar una vez, tras un
    redibujado, la línea de empuje y las líneas de Show Slices, si están encendidas y la geometría no está oculta;
  - `_redraw_thrust_line` y `_clear_query_label` quitan sus elementos dentro de `try/except RuntimeError`.
- **`ogr_gui/i18n`:** los tres mensajes nuevos, en castellano.
- **`AGENTS.md`:** la cifra en lugar de la fracción.
- **`tests/test_add_boundary_step_v1414.py`:** el modelo de ejemplo se prepara para admitir cada tipo (§0).
- **`tests/test_canvas_rebuild_drawing_v1431.py`,** nuevo.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_canvas_rebuild_drawing_v1431.py`,** 16 tests. Casi todo su coste es la ventana de Interpretar y su
  corrida, y la ventana principal.
  - **La referencia** son los propios clics, pasados por la conversión de píxeles del lienzo (`mapFromScene` y
    `mapToScene`): lo que se entrega se compara con lo que se clicó, con una tolerancia relativa al tamaño del modelo.
  - **Un lienzo suelto por test,** mostrado, de 900×600 y sin ajuste:
    - contorno externo, de material y superficie del usuario, con la escena reconstruida tras el segundo vértice:
      cada uno entrega sus cuatro puntos, y no hay ninguna excepción;
    - la vista previa vuelve a estar en la escena nueva, y salir del modo la quita;
    - Zoom Window: la goma existía, y tras el redibujado no lanza, se va y la vista no cambia.
  - **Lo elegido sobre el modelo:**
    - el pie y la coronación con un redibujado entre medias dan sus índices (control);
    - con el contorno renumerado entre los dos clics, o con la coronación en el índice viejo del pie, no se entrega
      nada y se pide el pie;
    - un proyecto nuevo a mitad de un dibujo lo olvida, y el siguiente dibujo entrega solo lo suyo; el mismo proyecto
      lo conserva;
    - Escalar: la sombra vuelve tras un redibujado y el pivote se toma; con los contornos renumerados, con redibujado
      o sin él, no se entrega nada y se pide el contorno.
  - **La regla al terminar:** un segundo nivel freático no se añade, y la barra dice por qué; un contorno de material
    sí (control).
  - **La ventana mostrada, con la edición de un agente** (`WindowHost.after_edit`, que es el camino real) a mitad de
    una superficie del usuario: se guarda una con cuatro vértices, los dos centrales son los clics, y el modo se
    suelta.
  - **Interpretar:**
    - la línea de empuje vuelve con el resultado tras un redibujado, y una edición del modelo no la dibuja sola;
    - las líneas de Show Slices vuelven, se van con la geometría oculta y vuelven al mostrarla;
    - la etiqueta de consulta se olvida sin lanzar.
- **Discriminación en el árbol de 0.1.430** (`git archive` de 72da058, sin el buscador editable, `__file__`
  comprobados): fallan los 16, cada uno por sí mismo y por comportamiento.
  - Lanzan `RuntimeError` sobre un elemento muerto.
  - Se escala el contorno equivocado.
  - Se añade el segundo nivel freático.
  - Se ignora el clic en el índice viejo.
  - El proyecto nuevo conserva el dibujo.
- **Mutantes de los arreglos de la segunda ronda,** cada uno en un proceso limpio sobre el árbol vivo:
  - sin la comprobación del pie, falla el del contorno renumerado;
  - con la comprobación detrás de «es el propio pie», falla el de la coronación en el índice viejo;
  - sin olvidar al cambiar de proyecto, falla el del proyecto nuevo;
  - con la línea de empuje redibujada desde la señal, falla el de la edición del modelo.
- **Vecinos:** lienzo, arrastre de contornos, superficies a tres puntos, polilíneas y superficies del usuario,
  Interpretar, Escalar y Rotar, zoom, dibujo, línea de empuje, consultas, ángulo de talud, transformaciones, contornos,
  nivel freático, reglas, motivos de lo deshabilitado, i18n, español, versión y cachés de los tests: 680 de 680. Antes
  de adaptar `test_add_boundary_step_v1414`, 678 (§0).
- **Suite entera con `--jobs 4`: 7240 en verde, 1 saltado y 0 fallos,** sin fugas ni tramos muertos, sobre el árbol
  final. La primera corrida, antes de la revisión, dio 7230 en verde. La última serie en verde fue hace 9 commits, y
  toca a los 100.
- **Banco, en seco:**
  - D307, D323, D353, D360, D334 y D349 corregida en la raíz, y D103, D101, D102, D58, D96 y D225 del manual 02:
    todas CUBIERTO POR TEST;
  - sin corregir, D349 baja a SIGUE ABIERTO (§0);
  - `d398()`, aún sin aplicar al verificador, probada dentro de él sin escribir nada: con el árbol vivo, CUBIERTO POR
    TEST (los dos dibujos entregan sus cuatro puntos, sin excepciones); con el de 0.1.430, SIGUE ABIERTO por lo que
    hace (no entregan nada y lanzan).
- **Revisión adversaria:** tres lentes (el lienzo, Interpretar y la ventana, y tests, changelog y banco) y dos
  escépticos por hallazgo, 27 agentes. Salieron 12 hallazgos, 10 distintos.
  - **De este diff, confirmados y corregidos:**
    - el pie del ángulo de talud con un índice caducado (alta, dos lentes y 4 de 4 votos), y su residuo del orden;
    - el dibujo que pasaba a un proyecto nuevo;
    - la línea de empuje sola sobre un modelo editado (un votante lo refuta como lo decidido en el plan; se corrige
      igual, porque el resultado no se dibuja);
    - los tests: el lienzo de 98×28 en el de la ventana, la precondición de Zoom Window, el lienzo compartido y las
      versiones citadas.
  - **Anteriores, que la propietaria metió en D398:** la regla al terminar el dibujo, Show Slices y Escalar y Rotar.
  - **Anterior, que va a una ficha nueva:** Copiar contorno y Convertir contorno tampoco preguntan la regla.

## 3. Qué queda

- El resto de la tanda P10: D399 (textos) en 0.1.432, D400–D404 en 0.1.433–0.1.437, D408 (el informe PDF) en 0.1.438,
  D406 (`surface_evaluate`) en 0.1.439 y D409 (el FS(0) con kh) en 0.1.440. D407 (el rebanador) sigue sin versión.
  Sarma va en 0.1.441–0.1.447.
- **Ficha nueva, por decisión de la propietaria:** Copiar contorno y Convertir contorno añaden su contorno sin
  preguntar la regla de su tipo (`_do_copy_boundary` y `_do_convert_boundary`). Se abre al cerrar D398.
- **Prueba a mano, para la propietaria:**
  - dibujar un contorno o una superficie mientras un agente edita el modelo por el servidor MCP, y terminarlo;
  - en Cambiar ángulo del talud, elegir el pie, deshacer una edición del contorno y clicar la coronación: debe pedir
    otra vez el pie;
  - en Escalar, elegir un contorno, deshacer el que se añadió antes y clicar el pivote: debe pedir otra vez el
    contorno;
  - empezar un nivel freático en un modelo sin ninguno, añadir otro por un agente y terminar el primero: debe decir
    que solo se permite uno;
  - en Interpretar, con la línea de empuje y Show Slices encendidas, cambiar Contour Options y Ocultar geometría.

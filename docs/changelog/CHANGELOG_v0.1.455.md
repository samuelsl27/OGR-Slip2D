# OGR Slip2D v0.1.455

**Copiar contorno y Convertir contorno preguntan la regla de su tipo, y el Convertir del menú contextual hace lo del
menú (D410).** La regla es `boundary_refusal` (`ogr_core/project/rules.py`): un solo exterior, nivel freático, grieta
y línea de desembalse; esta, solo con desembalse rápido; y los objetos de bloques, solo con esa búsqueda. La
preguntaban el menú en gris, el final de un dibujo (desde 0.1.431, D398) y el agente al copiar y al cambiar de tipo. No
la preguntaban Copiar contorno ni los dos caminos de Convertir contorno de la ventana.

Medido con 0.1.452 sobre el talud de ejemplo, con el diálogo sustituido, igual que con 0.1.435. 0.1.453 y 0.1.454 no
tocan este código, y `d410()` mide lo mismo con 0.1.454:

| acción | 0.1.452–0.1.454 | ahora |
|---|---|---|
| Copiar el nivel freático | dos niveles freáticos (el motor lee el más alto) | no se copia: «Solo se permite un nivel freático. El contorno no se ha añadido.» |
| Copiar el exterior | dos exteriores (las regiones leen el primero; el segundo no hace nada) | no se copia: «Solo se permite un contorno exterior. …» |
| Convertir el nivel freático en desembalse, sin desembalse rápido | se queda en el modelo | no se convierte, con el motivo |
| Convertir el nivel freático, abierto, en exterior | dos exteriores, por los dos caminos | no se convierte: «Solo se permite un contorno exterior. El contorno no se ha convertido.» |
| Convertir una lente en nivel freático, con uno puesto | dos, por los dos caminos | no se convierte: «Solo se permite un nivel freático. …» |
| Convertir una lente en nivel freático, sin otro, por el menú contextual | «Material Boundary», cerrada, con su material y el color del material (#8b4513) | el contorno de `convert_boundary`: «Water Table», abierta, sin material, #1e90ff |

Por decisión de la propietaria, convertir en exterior se rechaza, como lo rechaza el agente, y el diálogo no cambia: la
regla se pregunta al aceptar y la barra dice el motivo, como al terminar un dibujo. **Ningún número cambia.** Es la
vigesimoctava versión de la tanda P10 y la tercera del plan aprobado el 2026-11-14.

## 0. Lo que se encontró

- **Paso 0:** el REPRODÚCELO da con 0.1.452 lo de 0.1.435. D416 y D417 no tocan este código.
- **El agente escribía la regla de la conversión a mano.** `boundary_edit` con `change_type` sacaba el contorno del
  modelo para preguntar la regla y lo volvía a meter: una regla que muta el modelo. Además comprobaba aparte que un
  exterior sea una polilínea cerrada. Las dos cosas bajan al núcleo, `rules.conversion_refusal`, con los mismos
  mensajes, el mismo orden y el mismo `Conflict`. Las preguntan el agente y la ventana.
- **El objeto de búsqueda por bloques (R4 del plan), medido con 0.1.454:**
  - una polilínea que vuelve atrás en x, convertida en objeto de bloques con la búsqueda por bloques puesta, quedaba
    guardada por los dos caminos de la ventana, aunque `block_object_refusal` la rechaza;
  - el agente la rechaza (`InvalidArgument`, tras toda edición).

  Entra: la ventana pregunta también `block_object_refusal` del contorno convertido.
- **Los dos Convertir buscan el diálogo en módulos distintos.** El del menú usa el `ConvertBoundaryDialog` de
  `main_window`, y el contextual el de `ogr_gui.dialogs`, y cada test sustituye el que lee su camino. Se conservan las
  dos búsquedas, y lo común es el paso posterior al diálogo, `_apply_conversion`.
- **El paso común vuelve a buscar el contorno al cerrarse el diálogo,** que es modal: un agente puede editar el modelo
  mientras está abierto (lo aprendió D419). Lo busca por identidad y, si ese objeto ya no está, por su `id` (§0, las
  dos revisiones).
- **El Convertir contextual no decía nada en la barra.** Ahora dice «Convertido en …», como el menú.
- **Una rama de más.** Para el exterior abierto se escribió primero una rama propia en `_boundary_refusal_text`. Un
  mutante que la quitaba sobrevivió: el respaldo (`tr(message)` entonces, `note_text` ahora, que para un texto sin
  código es `tr`) ya la traduce, porque la frase del núcleo tiene su castellano. Se quitó.
- **La revisión adversaria (un agente)** no encontró fallos en la regla. Comparó 468 conversiones (cada tipo en
  cada tipo, con y sin desembalse rápido y búsqueda por bloques) y 26 copias entre la ventana y el agente, y no vio
  ninguna diferencia. Encontró, y se arregló:
  - **(baja–media, del cambio) dos motivos del objeto de bloques en inglés con la interfaz en castellano.** Las frases
    de los vértices de un Punto o una Línea llevan un valor (`{n}`), y `tr` de la frase rellena no encuentra entrada.
    Se llega dibujando una Línea de bloques, insertándole un vértice y convirtiéndola. Ahora el motivo se dice por
    `note_text`, como lo dice ya `apply_block_object_spec`: «Una línea de búsqueda por bloques es un segmento dado por
    dos puntos; esta tiene 3 vértices…»;
  - **(media–baja) el test no veía el mensaje del camino contextual.** Sin pantalla, el plazo de un mensaje de la
    barra no vence nunca, y el camino contextual leía el que había dejado el del menú. Ahora la barra se limpia
    antes de cada camino;
  - **(baja) una frase falsa de este changelog.** Decía que `project_validate` bloquea un modelo sin exterior. No lo
    bloquea: da solo una nota («There is no External boundary…»);
  - **(baja, del cambio) un Aceptar que no hacía nada ni decía nada.** El primer borrador buscaba el contorno por
    identidad tras el diálogo modal. Una edición del agente mientras el diálogo estaba abierto (un movimiento)
    sustituye el objeto con el mismo `id`, y entonces Aceptar no convertía ni decía nada. Ahora lo busca por su `id` y
    convierte lo que hay en el modelo al aceptar. Si ya no está, la barra lo dice: «El contorno ya no está en el
    modelo: no se ha convertido nada.»;
  - **(baja, anterior) un paso de deshacer vacío.** Convertir un contorno en su propio tipo, sin que cambie nada,
    guardaba un paso «Edit Boundary». El agente no guarda ninguno, y D292 quitó los pasos vacíos de arrastrar un
    vértice. Ahora no se guarda;
  - **(baja, anterior) `convert_boundary` pisaba el nombre que puso el usuario,** en el menú y en el agente (y, con el
    paso común, también en el contextual): un nivel freático llamado «Phreatic 2024», convertido en nivel freático,
    salía «Water Table». **Por decisión de la propietaria entra:** solo un nombre por defecto pasa a ser el del tipo
    nuevo, y cualquier otro se conserva: el del usuario y los pocos que pone el programa. La regla de qué nombre es por defecto (el inglés de cualquier tipo, D399)
    baja de `ogr_gui/labels.py` al núcleo (`ogr_core/geometry/boundary.py`, `boundary_has_given_name`), y la
    preguntan la conversión y la etiqueta de la ventana. Cambia lo que devuelve el agente con un contorno con nombre;
  - dos frases: la tabla decía «0.1.454» sobre una medida de 0.1.452, y el docstring de `_boundary_refusal_text`
    hablaba solo de añadir.
- **La segunda revisión (un agente), acotada a lo que entró por la primera,** no encontró nada grave. Comparó los 14
  motivos que llegan a `_boundary_refusal_text`, antes y después y en los dos idiomas: el camino del dibujo dice lo
  mismo que antes. Encontró, y se arregló:
  - **(baja–media) la regla de D399 se había quedado sin test.** «el inglés de cualquier tipo es nombre por defecto»
    lo fijaba un test de v1432 que guardaba «Material Boundary» en un nivel freático, y ya no lo guarda. Un mutante
    (solo el nombre del propio tipo) pasaba. Ahora un caso convierte un nivel freático con ese nombre viejo;
  - **(baja) de dos contornos con el mismo `id` se convertía el primero,** no el elegido. Solo los trae un `.ogr` a
    mano: 0 de 32 356 archivos en el banco, el histórico y el repositorio. Ahora busca primero por identidad y
    después por `id`;
  - **(baja) un nombre que no es texto,** en un `.ogr` a mano, hacía que el `change_type` del agente lanzara un
    `TypeError` sin envolver, al compararlo con los nombres por defecto. Ahora se conserva;
  - **(baja) los nombres que pone el programa se conservan también,** no solo los del usuario: el terreno original de
    Expandir / contraer, y los «Block Search Object 1» de los guiones del banco. Es la regla decidida (solo cambia un
    nombre por defecto); lo que estaba mal eran los docstrings y este changelog, que decían «el del usuario». Ahora
    lo dicen;
  - y cinco frases: el paso común busca por `id` y no por identidad, el respaldo es `note_text`, los tests del agente
    que «no se mueven» no cambian de tipo ningún contorno, el test decía que probaba el agente y no lo hacía, y un
    import repetido.

  Se reporta sin tocar: convertir un contorno en su propio tipo sin que cambie nada dice «Convertido en …» aunque no
  guarde paso.
- **Se reporta sin tocar, a fichas nuevas por decisión de la propietaria:**
  - **(media, anterior, en las dos puertas) un material conserva su enlace a un contorno que se convierte, y deja de
    valer sin aviso.** Convertir el nivel freático del ejemplo en línea piezométrica, que la regla deja, baja u en
    (25; 0,5) de 73,6 kPa a 0,0, del lado inseguro: el material sigue con poros «nivel freático» y su
    `water_surface_id`, y `project_validate` deja calcular. Pasa también con las superficies anisótropas. Borrar sí
    limpia los enlaces y lo dice;
  - **(media, anterior) otros caminos de la ventana añaden contornos sin la regla:**
    - Convertir herramienta en contorno añade un segundo nivel freático, un segundo exterior abierto y una segunda
      grieta, y el agente rechaza los tres;
    - importar un DXF sin «sustituir el modelo» puede dejar dos exteriores;
    - y Convertir no comprueba que la polilínea se cruce a sí misma, y el agente sí.
- **Se reporta sin tocar:** convertir el único exterior en otro tipo deja el modelo sin exterior. El agente lo permite
  también, y `project_validate` solo da una nota.

## 1. Qué cambia

- **`ogr_core/geometry/boundary.py`:** `DEFAULT_BOUNDARY_NAMES` y `boundary_has_given_name`, la regla de D399 que
  vivía en `ogr_gui/labels.py` (que ahora la pregunta).
- **`ogr_core/geometry/transforms.py`, `convert_boundary`:** solo un nombre por defecto pasa a ser el del tipo nuevo;
  cualquier otro (el del usuario, uno que puso el programa) se conserva.
- **`ogr_core/project/rules.py`:**
  - `boundary_refusal(project, btype, *, ignoring=None)`: no cuenta el contorno `ignoring`, por identidad;
  - `conversion_refusal(project, boundary, new_type)`: la regla del tipo sin contar el contorno que se convierte, y un
    exterior solo desde una polilínea cerrada (`EXTERNAL_NOT_CLOSED`, la frase del agente).
- **`ogr_api/ops/model.py`, `boundary_edit` con `change_type`:** pregunta `conversion_refusal`, con los mismos
  mensajes, y ya no saca ni mete el contorno del modelo.
- **`ogr_gui/main_window.py`:**
  - `_do_copy_boundary` pregunta `boundary_refusal` con el tipo del original, también el exterior. Si rechaza, la
    barra dice el motivo y «El contorno no se ha añadido.», y la pila no cambia;
  - `_apply_conversion`, el paso común a los dos Convertir:
    - busca el contorno al cerrarse el diálogo, por identidad y si no por su `id`;
    - pregunta `conversion_refusal` y, con un objeto de bloques, `block_object_refusal`;
    - si rechaza, el motivo y «El contorno no se ha convertido.»;
    - si no, `convert_boundary` (tipo, nombre, cierre, material, color y objeto de bloques), el `id` conservado, un
      paso de deshacer solo si algo cambia, y «Convertido en …»;
  - `_boundary_refusal_text` dice el exterior («Solo se permite un contorno exterior.») y el resto por `note_text`.
- **`ogr_gui/i18n/__init__.py`:** cuatro frases nuevas con su castellano: «The boundary was not converted.», «Only one
  External boundary is allowed.», la del exterior abierto y «The boundary is no longer in the model: nothing was
  converted.».

## 2. Qué se probó

- **`tests/test_copy_convert_boundary_rule_v1455.py`** (17 casos, unos 2 s en el runner). Lleva una ventana real para el
  archivo, el diálogo sustituido en sus dos módulos y nunca ejecutado (es modal), y el idioma restaurado.
  - **La referencia es una identidad:** la ventana añade exactamente lo que deja la regla del núcleo, la que pregunta
    el agente. El control son las respuestas del agente, con su inglés de siempre.
  - **Copiar:** el nivel freático y el exterior del ejemplo no se copian, la barra dice el motivo en castellano y la
    pila no cambia. Una lente sí se copia.
  - **Convertir, por los dos caminos,** se rechaza con el mismo motivo:
    - el desembalse sin desembalse rápido;
    - un segundo nivel freático;
    - un segundo exterior;
    - una polilínea abierta en exterior, sin otro exterior;
    - un objeto de bloques que su geometría no puede ser.
  - Una Línea de bloques de tres vértices se rechaza con su motivo en castellano.
  - El nivel freático en sí mismo sí se convierte, por los dos caminos, sin paso de deshacer.
  - Una lente en nivel freático da por los dos caminos el contorno de `convert_boundary`, campo a campo, con #1e90ff.
  - Un nombre que puso el usuario se conserva por los dos caminos y por el agente, y uno por defecto pasa a ser el del
    tipo nuevo; también el de otro tipo que dejó una versión vieja («Material Boundary» en un nivel freático).
  - De dos contornos con el mismo `id` se convierte el elegido, y un nombre que no es texto se conserva sin error.
  - Una edición del agente con el diálogo abierto: un movimiento se convierte con sus vértices nuevos, y un contorno
    borrado se dice.
  - Un espía en `conversion_refusal` ve las dos puertas, la ventana y `boundary_edit`.
- **Cambian a propósito:**
  - `test_a_copy_names_its_type` (`tests/test_add_boundary_step_v1414.py`) copiaba el nivel freático del ejemplo. Ahora
    copia una línea piezométrica añadida: «Add Piezometric Line»;
  - `test_converted_from_the_context_menu_keeps_no_english` (`tests/test_spanish_texts_v1432.py`) fijaba
    `b.name == "Material Boundary"`. Ahora fija «Water Table».
- **No se mueven:** `test_converted_to_a_type_through_tr` y la copia de `_life` (v1432), cuya ventana abre un proyecto
  vacío, y `test_f2_ops_v1196` y `test_f2_rules_v1196`, que no cambian de tipo ningún contorno. El `change_type` del
  agente con un contorno con nombre lo fija ahora el test nuevo.
- **Discriminación:** en el árbol de 0.1.454, sin el buscador editable, fallan 14 de los 17 casos: 12 por lo que hacen
  y 2 por nombres nuevos. Pasan los tres controles: la copia de una lente, los dos contornos con el mismo `id`
  (0.1.454 convertía por índice) y el nombre que dejó una versión vieja (0.1.454 pisaba todos).
- **Mutantes** (`mutants_d410.py`, en el banco): 20, todos muertos. Seis son de la primera revisión: el motivo por
  `tr`, el contorno buscado solo por identidad o el de antes del diálogo, el contorno que falta sin decirlo, el paso
  vacío y el nombre pisado. Tres, de la segunda: solo el nombre del propio tipo como nombre por defecto, el contorno
  buscado solo por `id`, y el nombre que no es texto comparado. Los once primeros:
  - Copiar sin la regla;
  - Convertir sin `conversion_refusal`, o sin la geometría del objeto de bloques;
  - el paso propio del contextual (0.1.454);
  - el exterior dicho en inglés, o la frase del exterior abierto sin castellano;
  - un rechazo que convierte igual;
  - el contorno que se cuenta contra sí mismo;
  - una polilínea abierta que se hace exterior;
  - las dos negativas en el otro orden;
  - el agente con su propia copia (0.1.454).
- **Vecinos**, con los patrones `copy_convert_boundary_rule add_boundary_step spanish_texts f2_ops f2_rules rules
  transforms i18n disabled gui_spanish labels_spanish voice_and_terms redraw block_polyline lens_regions` (cada uno
  comprobado con `--list`): 277 casos en verde, con los censos de castellano y el presupuesto de cadenas sin envolver.
- **La suite entera** con `--jobs 4`, una sola vez y tras las dos revisiones: **7728 casos, 7727 en verde, 0
  fallos y 1 omitido**, sin fugas ni tramos muertos. La serie no toca (33 commits desde la última).

## 3. Qué queda

- Las dos fichas nuevas de §0: los enlaces de los materiales a un contorno que se convierte, y los otros caminos de la
  ventana que añaden contornos sin la regla.
- En el plan del 2026-11-14 siguen D425 (0.1.456), que reescribe `_do_copy_boundary` con `copy_boundary` en el
  núcleo, y D426.

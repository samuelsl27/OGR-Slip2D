# OGR Slip2D v0.1.434

**Con la interfaz en español, los mensajes del núcleo y los nombres de deshacer que se construyen con valores ya salen
en español. El inglés que lee el agente no cambia ni un byte (D412, la mitad del núcleo).** Lo resuelve el mismo
patrón de mensajes con código que ya usan el motor y las reglas: el texto en inglés de cada mensaje lleva su código y
sus valores. Así `str(exc)`, las notas y `project_history` dicen lo de siempre, y la ventana los dice a partir del
código.

- **Los rechazos y las notas de la geometría:**
  - Cambiar ángulo del talud, Simplificar contorno, Expandir / contraer y el desplazamiento del exterior. Llegaban a la
    barra de estado y a los avisos tal cual, sin `tr()` («The toe must be lower than the crest.»).
  - Las dos notas de Cambiar ángulo (soportes y cargas que no se movieron).
  - Las notas del lector de registros sísmicos, pegadas detrás de un marco traducido («No se importó nada: no numeric
    data»).
- **Siete nombres de deshacer construidos con f-strings,** que el menú Edición enseñaba en inglés:
  - tres de la ventana: «Paint material at (12.34, 5.67)», «Offset External (+1.50 m)» y «Expand/Shrink (shrink)»;
  - cuatro de las operaciones del agente: «Edit boundary (translate)», «Hydraulic properties of …», «Random variable
    material:<uuid>:cohesion» y «Delete random variable …».
  - «(kept, changed since: materials, settings)» nombra ya las partes del proyecto, no los atributos.
- **Tres sitios anteriores, por decisión de la propietaria en la revisión de 0.1.433:**
  - la norma de diseño por su nombre, no por su identificador («eurocode7_da1c2»), en Notas del análisis, en la
    estadística y en el PDF de la ventana;
  - una variable aleatoria por su etiqueta, no por su clave con UUID, en las notas de estadística;
  - las unidades del PDF que su tabla no conocía («Minutes», «M Day», «Mm Hour»).
- **Los textos del sistema.** Todo texto de una excepción en pantalla pasa por un lector (`error_text`). Los siete que
  salían solos van ya en una frase traducida: Guardar, Guardar como, tres exportaciones de Interpretar y los errores
  inesperados de Calcular y del barrido.
- **Tres anteriores más, por decisión de la propietaria en la revisión de esta versión:**
  - la ventana de estadística dice en castellano las notas de la norma;
  - una variable aleatoria que se borró después de la corrida sigue nombrándose por su etiqueta en las notas de
    estadística, porque la ventana guarda las variables de la corrida, como un paso de deshacer guarda lo que capturó;
  - el respaldo de «Mostrar valores a lo largo de la superficie» rotula sus columnas como la gráfica («τ disp. (kPa)»,
    no «τavail»).
- **Ningún número cambia.** El agente, la línea de órdenes y el `.ogr` siguen con su inglés y sus datos. El PDF del
  agente cambia solo en las seis unidades que su tabla no conocía («M Day» pasa a «meters/day»), por decisión de la
  propietaria en la revisión.

Es la séptima versión de la tanda P10. En su revisión la propietaria abrió **D414** en 0.1.436 (Importar propiedades
calla las notas del núcleo, y Abrir enseña en inglés los rechazos de los lectores del `.ogr`). Por eso D400–D409 pasan
una versión más tarde (0.1.437–0.1.444) y la spec de Sarma se renumera +1, a 0.1.445–0.1.451, en este commit. D413
sigue en 0.1.435.

## 0. Lo que se encontró

- **Al planificar,** tres exploradores en solo lectura midieron sobre 73c6d33:
  - los mensajes del núcleo sin código;
  - los nombres de deshacer y su camino por la pila;
  - y los tres sitios que añadió la propietaria.
  - Un agente de diseño propuso el plan, y la propietaria decidió cuatro puntos (abajo).
- **Ningún mensaje de estos cinco módulos llevaba código.** Son 30 textos; doce llegaban a la ventana. El único con
  entrada en el diccionario («The new overall angle must be between 0° and 90°.») era la del diálogo, y la copia del
  núcleo nunca pasaba por `tr()`.
- **La pila tiraba el código en cuatro sitios:** `SnapshotCommand.__init__`, `CommandStack.history()`,
  `MainWindow._step_name` y `ogr_api/ops/history.py` hacían `str()` del nombre. `str()` de un `Coded` devuelve un `str`
  sin el código. Ahora hay una regla, `commands.step_description`, que las tres copias leen.
- **`PaintRegionCommand.description` era un método desde v0.1.6.** Se reportó en v0.1.194 y no se cambió; cada lector
  lo llamaba aparte. Pasa a ser una propiedad.
- **La exención de `test_window_english_left_v1293` para los nombres de paso** (desde v0.1.301) es la que dejó vivos
  «Offset External ({d:+.2f} m)» y «Expand/Shrink ({mode})» 133 versiones. Se quita.
- **El censo F1 de 0.1.433 no vio la norma ni las claves.** Los identificadores de la norma son claves de `PRESETS`, no
  valores de un enum, y las muestras de las variables hidráulicas estaban en `_LATER` de `test_stat_notes_v1353`, que
  no leía.
- **Lo que se reporta y no se cambia:**
  - la misma edición tiene dos nombres: la ventana dice «Offset External» y «Expand/Shrink», y el agente, «Reshape
    External boundary». El inglés del agente se queda;
  - en la nota de Cambiar ángulo, un soporte sin nombre sale por su id;
  - la entrada «ft/s» del informe no correspondía a ninguna unidad (se quita);
  - los rechazos de `offset_polygon` y de `mode` no se alcanzan desde la ventana, y el de `mode` tampoco desde el
    agente. Se codifican igual, para que el censo no necesite excepciones.
- **Paso 0, medido antes de arreglar (regla 6):**
  - el inglés de 0.1.433 se capturó llamando a las funciones de un `git archive` de 73c6d33: cada rechazo, las dos
    notas, las notas sísmicas (la vacía sigue siendo `""`) y lo que `project_history` da tras las cuatro ediciones del
    agente. Con el árbol nuevo, los mismos textos y el mismo JSON, salvo que las notas son ya `Coded`;
  - sobre 73c6d33, el censo de la excepción encuentra exactamente los 27 sitios del plan, y el de los nombres de paso,
    seis. El séptimo, el de pintar, es un método de la clase y no un sitio de llamada, y lo ve el censo «sin código».
    Ese da 56 hallazgos en las funciones tocadas: 55 en la primera versión del censo, 54 de los cinco módulos y la
    f-string de `PaintRegionCommand` (este changelog decía 54, y lo corrigió la revisión), más la frase asignada que
    vio la regla que añadió la revisión (`note = "time step is not constant"`).
- **Decisiones de la propietaria (2026-11-09):**
  - la norma «custom» y la «none» llevan claves propias en femenino: «Custom standard» / «Norma personalizada», también
    en el combo de Ajustes del proyecto, y «No design standard» / «Ninguna norma» en las notas y el informe (el combo
    sigue con «Ninguna», que fija v0.1.325);
  - un paso de deshacer de una variable aleatoria ya borrada se nombra por lo que guardó el paso;
  - el censo de la excepción cubre los 27 sitios, y los siete que salían solos se enmarcan;
  - como en D411, la ventana en inglés también deja de enseñar identificadores.
- **El inglés de la ventana también cambia**, donde enseñaba un identificador (el agente no):
  - «Edit boundary (set vertices)»;
  - la norma por su nombre («Eurocode 7 — DA1 Combination 2: 2 material(s) …»);
  - las variables por su etiqueta;
  - «(kept, changed since: …)» con palabras donde había un atributo («material assignments», no
    «region_assignments»; «materials» y «settings» ya se leían igual);
  - la pista de la página Norma de diseño, que nombra la entrada del combo como el combo («choose Custom standard»);
  - y los marcos de Guardar, de las tres exportaciones y de los dos errores inesperados.
- **La revisión adversaria** tuvo siete agentes: cuatro lentes (el agente y la pila, la ventana en castellano, los tests
  y los censos, y un barrido del resto), un crítico de completitud y dos escépticos. Dio 21 hallazgos; uno refutado y
  dos el mismo, contado dos veces. **Del diff, arreglados:**
  - **El PDF del agente cambiaba seis unidades** («Minutes» → «minutes», «M Day» → «meters/day», «Mm Hour» →
    «mm/hour»…), contra lo que decía este changelog. La propietaria decidió que el agente lea también las palabras
    nuevas, y un test las fija por el camino del agente.
  - **La nota de Cambiar ángulo partía por «, » los nombres** que el núcleo había unido. Así traducía el trozo inicial
    de un nombre dado por el usuario («End Anchored, top row» salía «Anclado en el extremo, top row»), y nombraba un
    soporte por la clase que dice su nombre, no por la que tiene ahora su conjunto, que es la regla de D411. El núcleo
    pasa los nombres como un `Joined` (`ogr_core/messages.py`): es el mismo texto unido, así que el inglés y el JSON no
    cambian, pero guarda cada nombre y su soporte, y la ventana nombra cada uno como el resto de la ventana.
  - **La pista de la página Norma de diseño** seguía diciendo «elige Personalizado» cuando el combo dice ya «Norma
    personalizada». Ahora toma el nombre de la misma tabla.
  - **Huecos de los tests:**
    - tres de los nueve tipos de estadística se podían quitar sin que fallara nada;
    - el F1 ampliado no veía la norma: ninguna muestra que lee llevaba una, y sus claves de variable eran de dos
      partes;
    - el camino del éxito del diálogo sísmico;
    - la última regla de `error_text`;
    - la ventana de estadística y Copiar todo, con el proyecto.
    Cada uno tiene ya su test, y un mutante en memoria lo comprueba.
  - **Los censos tenían reglas sin autocomprobación** (siete, aunque la cabecera decía que todas la tenían) y tres
    huecos:
    - un nombre de paso pasado por palabra clave (`mutate(pid, description=f"…")`);
    - `exc.args[0]` enseñado tal cual;
    - una frase corta asignada a una variable, que era justo la forma de «time step is not constant» en 0.1.433;
    - y el censo de pasos aceptaba como parámetro el de cualquier envoltorio del archivo.

    Los tres censos leen ya esas formas, y cada regla tiene un caso propio en su autocomprobación: 21 mutantes de
    regla, cada uno cazado.
  - **La cabecera de `test_window_english_left_v1293`** seguía declarando la exención quitada.
  - **Este changelog** daba 54 hallazgos del censo «sin código» (eran 55) y un ejemplo de «(kept …)» que no cambia en
    inglés.
- **Anteriores a la versión, con decisión de la propietaria:**
  - **Entran aquí** tres pequeños de la misma familia:
    - la ventana de estadística enseñaba en inglés las notas de la norma: la primera línea de su etiqueta salía
      traducida y las demás no;
    - una variable borrada después de la corrida volvía a salir por su clave con UUID en las notas de estadística;
    - las cabeceras «σnef» y «τavail» del respaldo de Mostrar valores.
  - **Ficha nueva, D414, en 0.1.436:**
    - Importar propiedades tira las notas del núcleo: un material que usaba el nivel freático del otro proyecto queda
      seco, lo que cambia el FS, y la ventana no lo dice;
    - Abrir un `.ogr` con un tipo de soporte o un modelo de resistencia desconocidos enseña el inglés del núcleo con
      las comillas del repr de `KeyError`.
  - **A la primera cuestión de D413:** «Record», el nombre por defecto de un registro sísmico, en inglés en su diálogo.
  - **Refutado:** ese mismo «Record» como parte de D412, porque es un nombre por defecto, no un mensaje.
- **Caminos equivocados:**
  - **La tabla de unidades del informe estaba dentro de `generate_report`,** y no se podía comparar con sus enums. Sale
    a dos constantes de módulo.
  - **El primer censo de los nombres de paso leía las asignaciones de una variable en todo el archivo,** y `name` tiene
    decenas. Ahora las lee en la función de la llamada, y en el módulo si no hay función.
  - **En el test del PDF, las celdas de la tabla son `Paragraph`, no texto.** Se leen como pares de párrafos.
  - **El runner no tiene `pytest.mark`.** El test nuevo marca lo que necesita Qt como el resto.
  - **Llamé «malla de presiones intersticiales» a la rejilla de presiones de agua** en la tabla de «(kept …)». Lo cazó
    la suite: `test_spanish_leftovers_v1324` y `test_terms_spanish_v1323` reservan «malla» para los elementos
    finitos.
  - **Al editar,** el guion de `history.py` no casaba por la sangría, `seismic_record.py` tiene CRLF y los heredocs de
    Bash se comen las barras. Cada uno falló antes de escribir nada y se repitió con el archivo correcto.
  - **El tipo `support_names` era una regla de texto sobre un texto ya unido,** y no podía acertar: un nombre con coma
    no se distingue de dos nombres. El arreglo no fue partir mejor, sino no partir: el valor guarda sus piezas.
  - **Dos autocomprobaciones nuevas recorrían el mismo conjunto que comprobaban** (`_VISIBLE` y `_CORE_REFUSALS`), así
    que su mutante quitaba a la vez la regla y su caso. Escriben ya la lista aparte. El mutante del parámetro de
    envoltorio tampoco reproducía la regla vieja hasta que leyó todas las funciones del archivo.

## 1. Qué cambia

- **`ogr_core/geometry/messages.py`, nuevo** (`GEOMETRY_MESSAGES`, 25 códigos `geometry.*`).
  - `slope_angle.py`, `cleanup.py`, `expand_shrink.py` y `transforms.py` lanzan la excepción de siempre con el `Coded`
    de argumento, y las dos notas de Cambiar ángulo son `Coded`.
  - La nota de soportes lleva sus nombres como un `Joined` (`ogr_core/messages.py`, nuevo): el texto unido de siempre,
    con cada nombre y su soporte. La ventana nombra cada uno por la clase de su conjunto (tipo `support_names`).
- **`ogr_core/loads/messages.py`, nuevo** (`SEISMIC_NOTES`, cinco `seismic.*`), en `parse_record_text`.
- **`ogr_core/project/step_names.py`, nuevo** (`STEP_NAMES`, nueve `step.*`), con `expand_shrink_step_name` y
  `delete_random_variable_step_name`.
- **`ogr_core/project/commands.py`:**
  - `step_description`, la única regla para leer el nombre de un paso;
  - `SnapshotCommand` conserva el `Coded`, y su `captured(attr)` da lo que el paso guardó;
  - `CommandStack.peek_undo` / `peek_redo`;
  - `PaintRegionCommand.description`, propiedad.
- **`ogr_api/ops`:** `boundary_edit`, `hydraulic_set` y `random_variable_set` / `_delete` nombran su paso con código, y
  `project_history` lo lee por `step_description`. El inglés no cambia.
- **El núcleo y el motor, sin cambiar ningún número:**
  - `design.summary` declara el tipo de la norma;
  - nueve notas de estadística declaran el de la clave o la etiqueta de su variable;
  - el informe: `standard_name=` (solo lo pasa la ventana, así que el PDF del API sigue con el identificador),
    `TIME_UNIT_WORDS` y `PERMEABILITY_UNIT_WORDS`, y el valor guardado como respaldo. Las tablas valen para los dos
    PDF: el del agente nombra ya las seis unidades que su tabla no tenía (decisión de la propietaria en la revisión).
- **`ogr_gui/core_messages.py`:**
  - los tres catálogos;
  - `error_text(exc)`;
  - `project=` por palabra clave en `text`, `note_text`, `note_group`, `note_line` y `_show` (se pasa, nunca se
    guarda);
  - siete tipos nuevos: `design_standard`, `boundary_edit_op`, `support_names`, `variable_key`, `variable_keys`,
    `variable_label` y `material_ref`.
- **`ogr_gui/labels.py`:**
  - `DESIGN_STANDARD`, `BOUNDARY_EDIT_OP` y `PROJECT_PART`, con sus funciones;
  - `variable_key_label`, `variable_keys_label` y `variable_label_by_stored`;
  - `material_ref_label`, que pregunta a `find_material` de las operaciones y no copia la regla;
  - `with_variables` y `step_scope`.
- **La ventana:**
  - los rechazos y las notas de Cambiar ángulo, Simplificar y Expandir / contraer, por `error_text` y `note_text`;
  - el menú Edición y su barra, por `_step_label` (con lo que el paso guardó);
  - «(kept …)» por `project_part_label`;
  - las notas de estadística, con el proyecto;
  - el combo de la norma, desde `DESIGN_STANDARD`.
- **Los 27 sitios de un texto de excepción** (`main_window.py`, `interpret_window.py`, `background.py` y los diálogos de
  DXF, etapas transitorias y registros sísmicos), por `error_text`. Siete van ya en una frase traducida.
- **El panel de notas y la ventana de estadística** nombran por `MainWindow.notes_scope()`: el proyecto, más las
  variables aleatorias de la última corrida estadística (`last_statistics_variables`, que se guardan al lanzarla y se
  vacían con el proyecto). El panel lo pide en cada llenado, así que es el de después de Abrir. La ventana de
  estadística dice también por su código las notas de la norma. El diálogo de registros sísmicos dice su nota por
  `note_text`.
- **Interpretar:** el respaldo de Mostrar valores rotula sus columnas con la misma lista que la gráfica.
- **Ajustes del proyecto:** la pista de la página Norma de diseño nombra la entrada «custom» por `DESIGN_STANDARD`
  (la clave cambia: `choose {0}`).
- **`ogr_gui/i18n`:** 75 entradas nuevas y ningún valor cambiado; las que ya existían se reutilizan («materials»,
  «seepage field», «days», «Unexpected failure: {0}»…). La pista de la norma cambia de clave, con el mismo
  castellano salvo el nombre de la entrada.
- **Tests:**
  - `tests/test_edit_messages_v1434.py`, nuevo;
  - `test_spanish_paths_v1433` amplía el censo F1 y fija las cabeceras del respaldo de Mostrar valores;
  - `test_window_english_left_v1293` quita la exención de los nombres de paso, también de su cabecera;
  - y cambian a propósito las aserciones que fijaban el identificador de la norma en castellano
    (`test_stat_notes_v1353` ×2, `test_report_spanish_v1355` ×2, una de ellas la de la llamada de la ventana, y
    `test_cli_reported_caption_v1430`).
- **La spec de Sarma** (`spec/features/009-sarma-dovelas-no-verticales/`) se renumera +1: 0.1.445–0.1.451.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_edit_messages_v1434.py`,** 30 tests (26 antes de la revisión):
  - **`_V1433`:** el inglés de cada código igual al de 0.1.433, con una muestra por código de los tres catálogos. El
    núcleo lanza cada rechazo con ese texto, su código y su tipo, y las notas y la nota sísmica vacía salen igual.
  - **El agente lee lo mismo** por `ogr_api.call`: los rechazos de Cambiar ángulo, `external_reshape` y
    `seismic_record_set`, y los ocho nombres de `project_history` tras sus cuatro ediciones, también en JSON. La pila
    guarda los códigos.
  - **Cada código tiene su castellano,** con los mismos campos y sin llaves sin rellenar. Cada tipo nuevo, con
    proyecto y sin él, y el inglés del agente intacto. La última regla de `error_text` (una frase sin código). Un
    soporte por la clase de su conjunto y un nombre con coma entero, por el `change_slope_angle` real.
  - **Las tablas coinciden con lo que nombran:** `BOUNDARY_EDIT_OP` con `_EDIT_OPS`, `DESIGN_STANDARD` con `PRESETS` +
    custom (y es el combo, en su orden, con la pista de la página), `PROJECT_PART` con los atributos de la pila, y las
    unidades con sus enums. El PDF del agente, con «minutes» y «meters/day», y la regla de las once unidades.
  - **`_V1434_KINDS`:** las muestras con identificadores reales (una norma, claves de tres partes) que lee el F1.
  - **Por la ventana real, en castellano,** con sus diálogos sustituidos y restaurados:
    - Cambiar ángulo, con el rechazo y las dos notas;
    - Simplificar y el aviso de Expandir / contraer;
    - el menú Edición y su barra tras pintar, y tras desplazar el exterior;
    - una variable borrada, nombrada por su etiqueta;
    - «(se conserva …: materiales, ajustes)»;
    - el panel de notas;
    - una variable borrada tras la corrida estadística, por `_compute_statistics` con su resultado sustituido: la
      barra, el panel, Copiar todo y la ventana de estadística, con las notas de la norma;
    - el PDF de la ventana (Norma, Coeficientes aplicados, unidades);
    - Guardar sobre una carpeta;
    - y la importación sísmica, la vacía y la de paso irregular.
  - **Los tres censos,** cada uno con su autocomprobación sobre fuentes propias.
- **Discriminación en el árbol de 0.1.433** (`git archive` de 73c6d33, sin el buscador editable): fallan 26 de 30.
  - Los cuatro que pasan en los dos árboles son el control del inglés del agente (`test_the_refusals`) y las tres
    autocomprobaciones de los censos, que leen fuentes propias.
  - En `test_spanish_paths_v1433` fallan allí lo que esta versión le añade: el F1 ampliado (VARS_NONE, VAR_ORPHAN, las
    hidráulicas) y las cabeceras de Mostrar valores.
- **Mutantes, uno a uno y en memoria,** cada uno cazado por los tests de su regla. Ocho antes de la revisión:
  - `error_text` como `str()`;
  - `step_description` que tira el código;
  - sin el ámbito del paso;
  - «(kept …)» con los atributos;
  - los siete tipos nuevos apagados;
  - la norma por su identificador;
  - las unidades viejas;
  - el panel sin proyecto.
- **Y diez después:**
  - los soportes partidos por «, »;
  - los soportes por la clase de su nombre;
  - sin `notes_scope`;
  - las notas de la norma sin código;
  - `error_text` sin `tr()`;
  - los tres tipos de estadística sin test;
  - el F1 sin el tipo de la norma;
  - el F1 sin los de las variables;
  - las unidades con el nombre del miembro;
  - las cabeceras viejas de Mostrar valores.
- **Y 21 de regla de los censos,** uno por regla, cada uno cazado por su autocomprobación
  (`scratchpad/census_rule_mutants_434.py`).
- **Vecinos** (708 casos):
  - mensajes, notas, estadística, informe, línea de órdenes, deshacer, Cambiar ángulo, Expandir / contraer, sismo,
    variables aleatorias, Ajustes del proyecto, castellano e i18n;
  - la primera pasada dio cinco fallos, los cinco que el plan preveía (la norma por su nombre), cambiados con su
    motivo.
- **Suite entera con `--jobs 4`:** la primera corrida, antes de la revisión, dio 7323 de 7326, 1 saltado y 2 fallos,
  sin fugas ni tramos muertos. Los dos eran el mismo de §0: la parte «pore pressure grid» decía «malla de presiones
  intersticiales», y en este programa una malla es la de elementos finitos (v0.1.324). Pasa a «water pressure grid» /
  «rejilla de presiones de agua», el término de la rejilla. **La corrida final**, con lo de la revisión: 7329 de
  7330, 1 saltado, 0 fallos, sin fugas ni tramos muertos y sin archivos lentos fuera de `tests/_slow.txt`. La última
  serie en verde sigue a 12 commits.
- **Vecinos tras la revisión** (575 casos: estadística, notas, Cambiar ángulo, Ajustes, informe, sismo, castellano,
  deshacer y el puente del agente): en verde.
- **Revisión adversaria:** la de §0. Lo arreglado tiene sus tests y sus mutantes, arriba.
- **Banco, en seco antes del commit:**
  - D300, D315, D335, D344, D399 y D411: CUBIERTO POR TEST. D335 sigue contando sus quince catálogos;
  - `d412()`: CUBIERTO POR TEST en vivo, y SIGUE ABIERTO con 0.1.433 por lo que hace el programa: el rechazo en
    inglés, «Paint material at», «eurocode7_da1c2» y la clave con UUID. El inglés del agente pasa en los dos árboles,
    porque es su control.
  - El cierre (D412 retirada, D414 abierta en P10 y D400–D409 una versión más tarde) va tras el commit.

## 3. Qué queda

- **D413,** en 0.1.435: las cinco cuestiones de diseño que abrió la propietaria en la revisión de 0.1.433. La primera
  incluye ya «Record», el nombre por defecto de un registro sísmico.
- **D414,** en 0.1.436, abierta en la revisión de esta versión:
  - las notas que Importar propiedades tira, entre ellas la del material que queda seco;
  - los rechazos de los lectores del `.ogr` en inglés: tipo de soporte, modelo de resistencia y parámetro
    desconocidos.
  - Primero se mide con un censo qué más llega a Abrir y a Importar propiedades.
- El resto de la tanda P10: D400–D404 en 0.1.437–0.1.441, D408 en 0.1.442, D406 en 0.1.443 y D409 en 0.1.444; D407 y
  D410 siguen sin versión. Sarma va en 0.1.445–0.1.451.
- **Prueba a mano, para la propietaria,** con la interfaz en español:
  - Cambiar ángulo del talud con el pie y la coronación al revés, y con un soporte en la cara;
  - Simplificar con una tolerancia enorme;
  - Expandir / contraer con un extremo fuera del contorno, y el desplazamiento numérico;
  - el menú Edición tras pintar un material, desplazar el exterior y una edición del agente;
  - una norma de diseño en Notas del análisis, en la ventana de estadística y en el PDF;
  - una variable aleatoria borrada después de Calcular estadística, en Notas del análisis;
  - Importar un registro sísmico vacío y uno de paso irregular;
  - y Guardar en una carpeta sin permiso.

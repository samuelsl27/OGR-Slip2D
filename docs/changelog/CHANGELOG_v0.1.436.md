# OGR Slip2D v0.1.436

**Los nombres que pone el programa salen en el idioma de la interfaz y no se repiten, y una carga se nombra por la
magnitud que tiene (D415).** Es la mitad de D413 que lee el agente, separada al planificarla. Su referencia es el
inglés y el JSON del agente, que no cambian ni un byte.

- **Definir soporte nombraba un conjunto nuevo «Type N» contando las filas.** Al borrar el segundo de tres y añadir
  otro, salía un segundo «Type 3». Duplicar dos veces daba dos «X (copy)». Ahora «Type N» toma el primer número libre y
  la copia se numera: «X (copy)», «X (copy) (2)». Las reglas viven en el núcleo (`ogr_core/naming.py`) y Definir
  soporte las importa, con la comparación de `find_type`. El agente encuentra por su nombre cada conjunto que la
  ventana nombró.
- **Con la interfaz en castellano, esos nombres se traducen al enseñarlos:** «Tipo 3», «Anclado en el extremo (copia)»
  (por la clase que el conjunto tiene ahora; las copias se encadenan), «Norte (copia)» y «Registro». El `.ogr`, el
  agente y los campos de edición siguen con lo guardado, también al aceptar el diálogo en castellano.
- **Una carga sin nombre dado se nombra por su tipo y su magnitud actual:** «Carga distribuida — 35.0 kN/m²». Antes
  salía «Dist 20.0 kN/m²», el nombre con la magnitud que tenía al crearla. Una carga que varía a lo largo se nombra por
  sus dos extremos, «10.0–30.0 kN/m²», también en el menú contextual (decisión de la propietaria en la revisión). Vale
  en los dos idiomas, así que el inglés de la ventana también cambia. Un nombre dado es un dato y sale tal cual. Lo
  hacen el dato emergente (una carga lineal en kN/m, no en kPa), las variables aleatorias, la nota de Cambiar ángulo
  (unidas por «; » en pantalla) y las dos de carga lineal, que la nombran por su magnitud sola dentro de una frase que
  ya dice «carga lineal».
- **El panel de Resultados con norma y el PDF de la ventana nombran la carga por la magnitud de la corrida,** por
  decisión de la propietaria (2026-11-11): el rótulo se pregunta a la corrida, como en D413. La corrida guarda un
  `LoadName` por carga, que es el mismo texto de siempre (el JSON del agente y su PDF no cambian) y lleva además el tipo
  y las magnitudes.
- **Las notas que nombran un conjunto, un soporte, un registro o una carga declaran su tipo** con un `Joined`, y el
  inglés es el mismo texto: el conjunto ambiguo, el huérfano, las tres del anclaje helicoidal, las tres de resistencia
  infinita, el soporte invertido, el soporte que no se pudo calcular (una y varias, por decisión de la propietaria en
  la revisión) y la de Newmark. «User Defined» va en masculino («Definido por el usuario»: tomaba la clave femenina del
  modelo de permeabilidad).
- **Un soporte sin nombre se nombra por su clase y su cabeza,** «Bulón de suelo en (54.00, 8.00)», nunca por su id ni
  por «soil_nail». Los de un patrón nacen sin nombre. Lo decidió la propietaria en la revisión: por su conjunto, la
  nota del huérfano quedaba circular y los soportes de un patrón se leían iguales.
- **Ningún número cambia.**

Es la novena versión de la tanda P10, y la primera del orden que la propietaria aprobó el 2026-11-11: una ficha por
versión de 0.1.436 a 0.1.460. En este commit la spec 009 de Sarma se renumera +14, a 0.1.461–0.1.467.

## 0. Lo que se encontró

- **Al planificar** (2026-11-11, sobre c080aa0), tres exploradores en solo lectura midieron los sitios de D415, D414,
  D421 y D422. La propietaria decidió las cuatro cuestiones que dejaban los prompts. La de esta versión es el panel y el
  PDF con la magnitud de la corrida. El plan está en el de la tanda P10.
- **Lo que vio la planificación, fuera de esta ficha** (se reporta y no se cambia):
  - **la identidad de D422 es falsa en general.** El prompt da por referencia que `from_dict(to_dict(p))` conserva el
    `document_hash`, pero `ogr_api/snapshot.py:6-13` dice que el lector migra (D182: un `max_lambda` de 1,5 se lee
    como 6,0). D422 la sustituye por un A/B de lectores sobre el banco y por la idempotencia de leer lo que el programa
    escribe;
  - **el banco ya tiene conjuntos de nombre repetido:** el 049 (dos «Grouted Tieback») y el 050 (siete «Soil Nail»),
    con el `DISPLAY_NAME` de la clase. `find_type` no los encuentra por su nombre. Es materia de D421;
  - **los nombres de test de la spec 009 se habían quedado atrás:** `test_sarma_solver_v1437` y los tres siguientes,
    en secciones de 0.1.447–0.1.450. Se renumeraron +9 en 0.1.428 y nunca más. Con el +14 pasan a la versión de su
    sección (v1461–v1464).
- **Paso 0, medido antes de escribir (regla 6):**
  - **la lista del diseño**, hecho sobre 9830ba5, se rehízo con grep sobre c080aa0. Salen fuera, y no se tocan:
    - «Material N» por cuenta de filas (`material_properties_dialog.py:2539`), la misma repetición que «Type N». Ya está
      entre los hallazgos pendientes de la propietaria, con `find_material` frente a `find_type`;
    - «X (stage 2)» (`rapid_drawdown.py:645`), un material interno de la segunda etapa del desembalse;
    - los demás hallazgos del plan: el nombre tecleado que repite otro en Definir soporte, el soporte que no sigue al
      renombrar su conjunto, la etiqueta de una variable congelada al crearla, `degenerate_supports` sin código y
      `_find_record` con el primero de un nombre repetido;
  - **la referencia, `_V1435`:** 39 entradas, medidas llamando a las funciones de un `git archive` de c080aa0 con
    `capture_d415.py` (copiado al banco, en `_auditoria/P10_herramientas/`). La captura da 42; las otras tres son
    diagnósticos que el test no fija. Las 39 son:
    - las notas con un nombre, incluidos uno con apóstrofo, uno con coma y uno sin nombre;
    - las del soporte que no se pudo calcular y la de Cambiar ángulo con un soporte sin nombre, añadidas en la revisión;
    - los dos rechazos de carga lineal;
    - y el JSON del agente: `support_type_set` dos veces, `support_set`, `seismic_record_set`, `load_set` sin nombre y
      con otra magnitud, `project_get` de cinco secciones, y los avisos y los `load_factors` de una corrida con norma.
    Los ids se enmascaran. Dos capturas seguidas dieron lo mismo, y el árbol nuevo da las 42 iguales byte a byte.
- **Lo que apareció al escribir:**
  - **en inglés la ventana ya llamaba «User-defined» a la clase** (la clave propia de D411), así que «User Defined (2)»
    sale «User-defined (2)». El agente sigue leyendo «User Defined»;
  - **el censo de pantalla de `test_labels_spanish_v1321` no ve ningún nombre de carga,** porque ninguna de sus
    pantallas lo enseña. Los cubre el test nuevo: el menú contextual, el dato emergente, la variable, el panel y el PDF;
  - **un camino equivocado, y medido:** el mutante «`_program_base` sin "Type N"» dejaba pasar el censo. Rompía también
    la regla que usa el propio censo (`is_program_set_name`), que pasaba a tomar «Type 3» como un dato. Es la lección
    de D412. Con el mutante solo sobre la etiqueta (`support_set_name`), el censo falla en «Type 3»;
  - **los scripts de sustitución dejaron en CRLF doce archivos LF** al escribir en modo texto. Lo delató el aviso de
    Git, y se devolvieron a LF antes de probar nada. `seismic_record.py` y `seismic_records_dialog.py` ya estaban en
    CRLF en la copia de trabajo; quedan en LF, como fija `.gitattributes`.

### La revisión adversaria

Ocho agentes: cuatro dimensiones (el inglés del agente, las reglas de `labels.py`, los sitios que faltan, y los tests y
la mecánica) y un verificador por dimensión que intentó refutar cada hallazgo. **Los 26 se confirmaron**, con varios
repetidos entre dimensiones.

- **En el diff, y arreglados:**
  - **un nombre que no es texto en el `.ogr`** («"name": 5», editado a mano) pasaba a "5" en el JSON del agente: el
    `Joined` y el `LoadName` lo convertían en cadena. Ahora solo se envuelve un nombre que es texto
    (`ogr_core.messages.joined_name`; `LoadName.of` devuelve el valor como vino). El A/B del revisor con nombres de
    texto sobre 89 respuestas del agente, `ogr_cli compute` en 7 modelos, el MCP y los `.ogr` guardados salió igual
    byte a byte;
  - **una nota sobre un soporte sin nombre de una clase desconocida** salía con el nombre vacío («El soporte «»…»);
  - **en inglés, la lista de conjuntos de la nota ambigua** salía con «», mezcladas con las comillas rectas de la misma
    frase. Las comillas pasan por la traducción (`'{0}'` → «{0}»);
  - **«Type 01» o «Type 007», tecleados,** se enseñaban «Tipo 1» y «Tipo 7»: dos conjuntos distintos para `find_type`
    se leían igual. La regla casa solo lo que escribe `NEW_SET_NAME`;
  - **`parse_default_load_name` aceptaba «Dist 20 kN/m²», «Dist 1e3 kN/m²» o «Dist nan kN/m²»,** que el programa
    nunca escribe, y tapaba el nombre que dio el usuario. Casa solo lo que escribe `{0:.1f}`;
  - **el diagrama de fuerzas decidía el corchete por el nombre del soporte,** no por el que enseña: un soporte de
    patrón repetía la clase tras «… (copia)». Ya no, y tampoco tras un conjunto sin nombre, que ya la repetía en
    c080aa0;
  - **un `LoadName` nuevo por superficie evaluada** costaba unos 160 B por carga y por evaluación guardada (unos 20 MB
    por carga en la prueba de interfaz de 0.1.397). Ahora es uno por carga y corrida, guardado en la copia de análisis
    por lo que dice (`design_actions._load_names`);
  - **los rechazos de cada tarea y la primera nota de Calcular se decían sin el proyecto** (`main_window.py`: el
    trabajador del barrido, el retroanálisis, el barrido, la estadística, optimizar, el transitorio, la comprobación de
    Calcular y las dos barras). Sin él, las reglas vuelven al id o a la magnitud con que nació la carga;
  - **un soporte que se nombró después de escribirse la nota** volvía a salir por su id;
  - **«Carga 'Carga distribuida — 25.0 kN/m²'»** en el PDF y **«Line load Line Load — 50.0 kN/m»** en la ventana en
    inglés: el tipo de carga, dos veces. El PDF de la ventana pone solo el rótulo de una carga sin nombre, y los
    rechazos de carga lineal, su magnitud sola;
  - **los documentos:** el changelog decía 39 entradas de `_V1435` cuando el test tenía 35 (ahora son 39 de verdad,
    con los avisos de la corrida y las tres notas nuevas). `numbered_name` decía ser ya la regla del agente y del
    importador, que conservan su copia hasta D421. `default_support_name` quedaba sin uso y se borra
    (`test_spanish_paths_v1433` pasa a `is_program_set_name`);
  - **el test:**
    - dos aserciones de «el dato no cambia» no podían fallar porque los diálogos nunca se aceptaban: ahora se aceptan en
      castellano;
    - la «referencia independiente» del combo de clases leía la misma función que la regla: se contrasta con la palabra
      del diccionario;
    - la caché del agente compartía la de las notas;
    - una clave mal nombrada (`infinite_user_defined_class` → `infinite_unnamed_support`);
    - `_requires_qt` a medias;
    - y faltaban la nota de Cambiar ángulo con un soporte sin nombre y el combo del diagrama.
- **Decisiones de la propietaria (2026-11-11):**
  - un soporte sin nombre, por su clase y su cabeza;
  - una carga trapecial, por sus dos extremos, también en el menú contextual;
  - las notas «support <id> could not be priced», que ya estaban en c080aa0, entran: el id sigue en el inglés y la
    ventana nombra el soporte;
  - **el inglés de la ventana cambia también fuera de las cargas, y se declara:**
    - un soporte sin nombre deja de salir por su id o su «soil_nail»;
    - la clase «User Defined» de la nota ambigua sale «User-defined», como la llama la ventana en inglés;
    - un conjunto «End Anchored (copy)» cuya clase es ahora otra sale por la clase actual («Grouted Tieback (copy)»);
    - y el combo del diagrama ya no repite la clase.
    Es la regla de D411 y D412: la ventana en inglés también deja de enseñar identificadores.
- **Se reporta y no se cambia:**
  - las variables aleatorias de una carga, en las ventanas de resultados, llevan la magnitud de ahora, y el panel y el
    PDF la de la corrida. Es la decisión 1 de la propietaria, que nombra solo esos dos;
  - una carga sin nombre que el proyecto ya no tiene solo se puede nombrar por su id, que es lo que escribió el núcleo;
  - otras llamadas de la ventana dicen notas sin el proyecto (DXF, optimizar, transitorio): ninguna nombra un soporte
    ni una carga.

## 1. Qué cambia

- **`ogr_core/naming.py`, nuevo y sin dependencias** (lo importan las cargas y los soportes sin ciclos):
  - `NEW_SET_NAME`, `COPY_SUFFIX` y `DEFAULT_RECORD_NAME`;
  - `name_key`, `numbered_name`, `first_free_set_name` y `copy_name`;
  - `default_load_name` y `parse_default_load_name`, con «Dist 20.0 kN/m²» y «Line 50.0 kN/m» byte a byte;
  - `load_kind`, `load_magnitude`, `load_end_magnitude` y `load_has_given_name`;
  - `LoadName(str)`, con `__reduce__`.
- **Los que escriben esos nombres los toman de ahí:** `seismic_record.py` (el valor por defecto y `from_dict`),
  `ogr_api/ops/loads.py` (cargas y registros), `main_window.py` (las dos cargas) y Definir soporte (añadir, el primer
  conjunto y duplicar).
- **`ogr_core.messages`:** `Joined` gana `quote` (las comillas de cada nombre van en el texto y no en `items`), y
  `joined_name` envuelve solo un nombre que es texto.
- **Las notas llevan sus refs** (`support_notes.py`, `helical_anchor_notes.py`, `support_integration.py`, también las
  del soporte que no se pudo calcular, `analysis_runner.py`, `slope_angle.py`, `LineLoad._named`), y sus catálogos
  declaran los tipos `support_names`, `set_names`, `support_class`, `record_name`, `load_names`, `line_load_name` y
  `support_failures`.
- **`design_actions`:** `load_factors` guarda un `LoadName` por carga y corrida (`_load_names`).
- **`ogr_gui/labels.py`:**
  - `support_set_name`, `set_name_names_its_class` e `is_program_set_name`. `support_type_label` y `support_name` pasan
    por la primera. Cubren la lista y los combos de Definir soporte, Patrón, Modificar soporte y patrón, la Tabla de
    propiedades, el dato emergente, el lienzo y el diagrama de fuerzas;
  - `support_class_label`, `set_names_label`, `record_label` y `record_name_label`;
  - `load_label`, `load_name_label`, `load_names_label` y `line_load_name_label`;
  - `support_names_label` con `_support_of_note`: un soporte por su nombre (también el que recibió después de la nota),
    y uno sin nombre por su clase y su cabeza; `support_failures_label`;
  - `random_variable_label(rv, project=None)`, que encabeza la variable de una carga por la carga (el id de la clave);
  - sale `default_support_name`.
- **La ventana:**
  - el dato emergente de una carga;
  - el menú contextual de una carga trapecial;
  - el panel y el PDF (`generate_report(..., load_name=)`, como `standard_name=`);
  - la lista de Registros sísmicos y el combo de Ajustes de proyecto;
  - el diagrama de fuerzas;
  - y las notas dichas contra el proyecto.
- **i18n:** «Tipo {0}», «(copia)», «Registro», «'{0}'» → «{0}», «{0} en (…)», la carga distribuida con dos extremos, la
  magnitud de una lineal, y las comillas «» en las dos notas de carga lineal.
- **Tests que cambian a propósito:**
  - `test_gui_spanish_v1318`: salen las excepciones «Type {}» y «{}: {} kPa». La segunda, porque la unidad es ahora un
    valor (kN/m en una lineal);
  - `test_labels_spanish_v1321`:
    - el dato emergente de una carga sin nombre empieza por «Carga distribuida — 10.0 kN/m²»;
    - `_data_names` ya no da por datos los nombres del programa;
    - el proyecto del censo lleva dos conjuntos con nombres del programa, un registro «Record» y una carga con su
      nombre de nacimiento;
  - `test_report_spanish_v1355`: la ventana pasa `load_name=`;
  - `test_model_notes_v1347`: sale la exención `"'%s'" % _name(st)`, que el `Joined` hace muerta;
  - `test_spanish_paths_v1433`: `is_program_set_name` en lugar de `default_support_name`;
  - `test_i18n_coverage_v141`: «{0:.1f} kN/m» entra entre las entradas idénticas en los dos idiomas (notación);
  - `test_setting_refusals_v1350` y `test_seepage_run_notes_v1352`, que leen el código de la ventana: sus llamadas a
    `note_text` llevan ahora el proyecto. La segunda corrida de la suite entera los encontró.
- **Spec 009:** +14 (0.1.461–0.1.467), y los cuatro tests a la versión de su sección.

## 2. Qué se probó

- **`tests/test_default_names_v1436.py`** (26 casos, unos 6 s en un proceso, casi todo importaciones):
  - `_V1435`, las 39 entradas;
  - un nombre que no es texto llega al agente como vino;
  - la regla del núcleo y el caso de la ficha en Definir soporte, aceptado en castellano, con la identidad
    `find_type(p, nombre) is conjunto`;
  - las muestras de `support_set_name` (escritas aparte de la regla, con «Type 01»), la copia de un conjunto nacido de
    otra clase, la lista, el combo de Patrón y el campo de edición, y el combo del diagrama de fuerzas;
  - «Registro» en las dos listas, aplicado en castellano, y en la nota de Newmark;
  - una carga por su magnitud ahora: el menú contextual como referencia (también una trapecial), el dato emergente y
    la variable aleatoria de las dos magnitudes;
  - el panel y el PDF con la magnitud de la corrida (la carga nace en 15, corre en 25 y queda en 40): la ventana dice
    25 y el PDF del agente «Dist 15.0 kN/m²»; un solo `LoadName` por carga en toda la corrida;
  - el castellano de cada nota y su inglés de la ventana: un soporte sin nombre por su clase y su cabeza (también de
    una clase desconocida), uno nombrado después, el que no se pudo calcular, las cargas y el rechazo de Calcular por
    la magnitud de ahora;
  - las llamadas de la ventana con el proyecto, y el censo de `_data_names`.
- **Discriminación** en el `git archive` de c080aa0, con `correr_sin_editable.py`: 24 de 26 fallan. Pasan el control
  del agente (`_V1435`) y «un `LoadName` por carga», que guarda una regresión de este diff y en c080aa0 se cumplía
  (compartía la cadena del nombre). Definir soporte falla allí por comportamiento: `['Type 1', 'Type 3', 'Type 3',
  'Type 1 (copy)', 'Type 1 (copy)']`. El panel, también: «Dist 15.0 kN/m²».
- **Mutantes:** 31 de las reglas, y los 31 mueren (`mutants_d415.py`, en el banco). Además, dos del censo de pantalla
  de `test_labels_spanish_v1321`: «Type N» en inglés (por la etiqueta) y «Record» en inglés hacen fallar el censo, y el
  control pasa (`census_mutants_d415.py`).
- **Vecinos:**
  - `default_names`, `model_notes`, `method_notes`, `edit_messages`, `labels_spanish`, `gui_spanish`, `spanish_paths`;
  - `support_identity`, `data_tip`, `report_spanish`, `seismic`, `random_var`, `stat_notes`, `voice_and_terms`,
    `window_english`;
  - `support_reversed`, `newmark`, `design_factor_report`, `load`, `i18n`, `support_force`, `task_notes`,
    `support_soil`, `support_silence` y `slope_angle`: 583 casos.
- **La suite entera,** `--jobs 4`, cuatro veces:
  - antes de la revisión: 7374 casos, 7373 en verde y 1 omitido;
  - tras los arreglos de la revisión, dos fallos de tests que leen el código de la ventana (§1, los dos últimos de
    «cambian a propósito»);
  - la tercera, uno: `test_api_jobs_v1194::test_progress_is_written_and_ends_complete`, que es **D371**, abierta (un
    trabajo del API pierde a veces la última escritura de su `progress.json` con la máquina cargada). Pasa solo, tres
    veces seguidas, y no es de esta versión;
  - la cuarta: **7382 casos, 7381 en verde y 1 omitido**, `Failed: 0`, sin `Leaks` ni `Chunks died`, sin aviso de
    lentos ni de serie (14 commits desde la última).
- **Banco:**
  - `d415()` en el verificador de la raíz: SIGUE ABIERTO con c080aa0, por lo que hace el programa, y CUBIERTO POR TEST
    con el árbol nuevo;
  - en seco, D300, D335, D399, D411, D412 y D413 de la raíz siguen CUBIERTO POR TEST, también tras los arreglos de la
    revisión, y D66 del 02 SE SOSTIENE (el 049 y el 050, justo los de conjuntos repetidos, con sus números);
  - la auditoría de invariantes de la raíz: 0 ERROR y 71 AVISO, como antes.

## 3. Qué queda

- **D414,** en 0.1.437: Importar propiedades dice sus notas en Notas del análisis, y Abrir enseña en castellano los
  rechazos de los lectores del `.ogr`. El resto de P10 va de 0.1.438 (D422) a 0.1.460, y Sarma en 0.1.461–0.1.467.
- **Prueba a mano, para la propietaria,** con la interfaz en español:
  - en Definir soporte, añadir, borrar, añadir y duplicar dos veces;
  - el dato emergente de una carga lineal y de una repartida tras cambiar su magnitud;
  - el panel de Resultados con norma, tras cambiar una carga después de calcular;
  - las notas de un patrón de soportes sin nombre (Análisis > Notas del análisis).
- **Hallazgos fuera de la ficha** (§0): «Material N», «(stage 2)» y los cinco del plan.

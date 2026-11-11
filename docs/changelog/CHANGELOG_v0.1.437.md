# OGR Slip2D v0.1.437

**Importar propiedades dice lo que cambió en lo que copió, y Abrir dice en el idioma de la interfaz lo que un `.ogr`
trae y esta versión no conoce (D414).** Es de la familia de D412, la de los mensajes del núcleo sin código, y su
referencia es la misma: el inglés y el JSON del agente, que no cambian ni un byte.

- **Importar propiedades tiraba las notas del núcleo.** Un material que usaba el nivel freático del otro proyecto
  llegaba seco, y eso cambia el factor de seguridad. La barra decía solo cuántos materiales se habían importado. Al
  máximo de materiales decía «Importados 0 material(es)…» sin el porqué.
  - Ahora las notas van a Análisis > Notas del análisis, como las de los demás cálculos (decisión de la propietaria),
    y la barra las cuenta: «[2 nota(s) — Análisis > Notas del análisis]».
  - **Por decisión de la propietaria en la revisión,** las notas de las importaciones de un proyecto **se suman**, y
    deshacer una importación quita las suyas.
  - Las cinco notas llevan código: el nivel freático, la superficie anisótropa, el rango que toma la resistencia de un
    material de este modelo, el que se queda sin enlace y el máximo de materiales.
- **Abrir e Importar enseñaban el inglés del lector, con las comillas del repr de un `KeyError`:** «'Unknown support
  type: future_nail'». Ahora dicen «Tipo de soporte desconocido: «future_nail»». Pasa lo mismo con un modelo de
  resistencia desconocido (con los que hay, por su nombre) y con un parámetro desconocido (con los que admite, por su
  nombre y su clave).
- **Por decisión de la propietaria, sobre el censo, también se dicen dos de Python:**
  - un tipo de contorno desconocido, que enseñaba solo «'future_value'» o «7»;
  - y el valor desconocido de cualquiera de las **veinte** enumeraciones que lee un `.ogr`: ««future_value» no es un
    valor válido para el método de presión intersticial». Eran catorce, y la revisión encontró seis más.
  - Lo demás que levanta un archivo estropeado sigue como lo escribe Python, dentro del marco traducido: una clave que
    falta, un valor de otro tipo, un JSON roto. Es la regla de D412.
- **El inglés de la ventana cambia en esos rechazos, y se declara (§1).** El del agente no.
- **Ningún número cambia, ni lo que se importa.**

Es la décima versión de la tanda P10.

## 0. Lo que se encontró

- **Paso 0, el censo (regla 6), sobre 5d36030.** Se estropearon 5210 copias de seis modelos:
  - el ejemplo ampliado, con dos conjuntos de soportes (uno llamado «O'Neil»), un soporte, dos cargas, un registro, una
    variable aleatoria y un material generalizado;
  - y del banco, el 049, el 050, el 059 (el único con objeto de foco), el 013 (con rejilla de presiones) y el 010
    (con malla).

  En cada copia se hizo una de estas cosas, y se leyó con `Project.from_dict`:
  - se quitó una clave;
  - se puso a null;
  - se cambió de tipo;
  - se le dio un valor desconocido;
  - o se le añadió una clave nueva.

  **4324 abren sin error**, y el resto cae en 115 grupos:

  | clase | grupos | lo que decía la ventana |
  |---|---|---|
  | rechazo propio del núcleo | 5 | `'Unknown support type: x'` (con un texto, un número o null), el modelo y el parámetro |
  | valor de enumeración desconocido | 48 (17 enumeraciones) | `'x' is not a valid PorePressureType` |
  | falta una clave | 17 | `'type_id'`, solo el nombre de la clave |
  | tipo de contorno desconocido | 3 | `'x'` o `7`, solo el valor |
  | forma de una sección (D422) | 16 | `'NoneType' object is not iterable` |
  | otro tipo dentro de una sección | 26 | `float() argument must be … not 'NoneType'` |

  - **Las 11 de una clave que esta versión no conoce** («… got an unexpected keyword argument 'future_key'», en ocho
    subsecciones de los ajustes y en tres tipos de soporte) caen en las dos últimas filas. También siguen como las
    escribe Python, y la propietaria las vio una a una en el censo.
  - **De las 48, 40 son de las catorce que esta versión trató primero.** Son tres por enumeración, salvo la aplicación
    y la orientación de la fuerza de un soporte, que con null no levantan. Las otras 8 son de `GridValueType`,
    `SimpleSoilType` y `BCType`, y la primera versión de esta entrada las dejó fuera sin decirlo (ver la revisión).
  - El `raise` de los ajustes del transitorio («Stage times must be positive») no se alcanza al leer, y «unknown
    interpolation method» de la rejilla de presiones tampoco salió.
  - **El censo no miró lo que levanta `Project.load` antes de `from_dict`:** un JSON roto, un archivo vacío o unos bytes
    que no son UTF-8. Se dicen como los escribe Python dentro del marco traducido, por la misma regla de D412. La forma
    del archivo es D422.
  - **Decisión de la propietaria:** entran con código la primera, la del tipo de contorno y las enumeraciones. Las
    claves que faltan y los tipos cambiados siguen tal cual dentro del marco, y la forma es D422.
- **La referencia, `_V1436`:** 95 entradas de 5d36030.
  - **Cómo se mide:** se llama a las funciones de un `git archive` del árbol. `capture_d414.py` (en el banco) ejecuta
    sobre ese árbol el `_capture()` del propio test, así que las entradas son las del test y no una copia que pueda
    divergir.
  - **Qué recoge:**
    - el tipo y el texto de cada rechazo de los lectores;
    - un parámetro desconocido, de un modelo con parámetros y de uno sin ninguno;
    - las veinte enumeraciones, con un valor desconocido, un número y null;
    - las seis notas de una importación, con un nombre con apóstrofo («"O'Neil"»);
    - la del máximo;
    - y lo que leen `project_open` y `properties_import`, también su JSON.
  - **La carpeta temporal se escribe «`<tmp>/`»** con cualquier separador.
  - Las 76 entradas de la primera captura salen iguales, salvo el separador, y el árbol nuevo da las 95 iguales byte a
    byte.
- **Lo que apareció al escribir:**
  - **las dos de Python no se pueden envolver en un `Coded` sin cambiar el inglés del agente:** `str(KeyError(7))` es
    `7`, y `str(KeyError("7"))` es `'7'`. Por eso llevan el código como atributos de la excepción de siempre
    (`code` y `values`, como `DxfReadError`), y su texto sigue siendo el de Python;
  - **el `who` de la importación** («range 2») era inglés del núcleo. Ahora es un mensaje anidado: «el rango 2», y
    «la base» y «la junta 1» con las palabras que ya tenían los rechazos de resistencia;
  - **`test_focus_circle_in_core_v1343`** exige que `ogr_slip2d.focus` reexporte cada nombre del módulo de foco del
    núcleo, y un `read_enum` importado arriba era un nombre nuevo. En `focus.py` se importa dentro de `from_dict`, y
    en los seis lectores que añadió la revisión se hizo igual;
  - **un camino equivocado, medido:** el mutante de `import_child` sobrevivía, porque `properties_import` lo importa al
    cargarse y yo parcheaba el módulo de mensajes. Además, ningún test miraba el castellano de esas notas. El test lo
    mira ahora, y el mutante, apuntado al nombre que usa `properties_import`, muere;
  - **el guion de mutantes colgaba la máquina:** un método recompilado con una copia de los globales de su módulo no
    veía el diálogo de archivo sustituido después, y abría el real, que es modal. Ahora se compila con los globales
    del módulo.
- **La revisión adversaria** (ocho agentes, 28 hallazgos, uno refutado) encontró en el diff:
  - **lo más grave, el inglés del agente cambiaba:** con un modelo sin parámetros (`infinite_strength`,
    `no_strength`…), «Valid: []» pasaba a «Valid: », y el castellano acababa en «Los que admite: » sin nada. La causa
    es que el rechazo se construía desde su plantilla, y `english` toma una lista vacía por una lista de mensajes
    anidados, que une en nada. `_V1436` solo tenía Mohr-Coulomb. Ahora:
    - `file_refusal` guarda el texto f-string que el lector escribió siempre;
    - una lista va como `Joined`;
    - la ventana dice «ninguno»;
    - y `_V1436` lleva el caso;
  - **seis enumeraciones más sin `read_enum`:** `SimpleSoilType`, `BCType`, `GridValueType`, `AnnotationKind`,
    `BlockObjectKind` y `PolylinePointMode`. El censo de la primera versión leía una lista fija de lectores y de clases,
    y no podía verlas. Por decisión de la propietaria entran, y el censo encuentra él mismo las enumeraciones (las
    clases que derivan de `Enum` en `ogr_core`, `ogr_fem2d` y `ogr_slip2d`) y lee cada lector (cada función cuyo nombre
    lleva `from_`);
  - **cada importación borraba las notas de la anterior,** también una de solo soportes, aunque el material siguiera
    seco. Y al deshacerla, las notas seguían ahí nombrando materiales que ya no estaban. Por decisión de la propietaria:
    - las notas se suman;
    - deshacer oculta las de la importación deshecha, y rehacer las devuelve;
    - y un paso nuevo tras deshacer las olvida;
  - **la cabecera del panel** decía «del último análisis… ninguna cambia un factor de seguridad» aunque hubiera notas
    de la importación, que sí lo cambian. Con ellas dice ahora que las de Importar propiedades pueden cambiarlo;
  - **la lista de modelos se unía con «, »,** y tres nombres llevan coma («Undrained, c(depth below layer top)»). Ahora
    con «; »;
  - **los parámetros salían por su etiqueta y el desconocido por su clave,** así que no se podían comparar. Ahora salen
    por su nombre con la clave entre paréntesis cuando no coinciden: «cohesión (cohesion), ángulo de rozamiento
    (friction_angle)»;
  - **tres maneras de citar el valor, y «None» donde el archivo dice null.** En castellano va ahora siempre entre «»,
    con `null`, `true` y `false` como los escribe el JSON;
  - **«sentido de la rotura»** no es como la interfaz llama al ajuste. Ahora es «la dirección de rotura», y cada nombre
    lleva su artículo («… no es un valor válido para el método de presión intersticial»);
  - **el mismo hijo de un generalizado es «la regla N» en los rechazos de resistencia y «el rango N» en las notas.** Se
    queda «el rango», que es lo que dice el resto del material. El changelog lo llamaba «tramo», y ya no;
  - **`_V1436` fijaba la barra invertida de Windows,** y el test habría fallado en la CI de Linux;
  - **este changelog contaba mal el censo:** «48 (14 enumeraciones)», 3 grupos en la primera fila y un ejemplo con un
    objeto de foco que no tenía;
  - **el inglés de la ventana cambiaba sin declararse;**
  - **y los huecos del test:**
    - un rechazo que dejara de levantarse pasaba;
    - el censo de las notas veía tres formas en dos funciones;
    - el error de Importar al leer no tenía caso;
    - y la prueba del panel no miraba el panel.

    Todo arreglado, con 31 mutantes. El hallazgo refutado decía que una clave desconocida en los ajustes o en un tipo
    de soporte salía en inglés fuera de la decisión. Es Python, está en el censo y la propietaria lo vio, así que va
    por la regla de D412. Quedaba solo la etiqueta de la tabla, que ahora la nombra.
- **Ficha nueva, D429, al final de P10 y sin versión** (decisión de la propietaria). Son valores desconocidos que un
  `.ogr` trae y que se sustituyen en silencio, así que ni el censo ni esta entrada los ven, porque el archivo abre:
  - un modelo de permeabilidad pasa a constante;
  - una envolvente de desembalse de tipo desconocido se descarta;
  - una búsqueda desconocida se calcula como Búsqueda en rejilla;
  - un muestreo desconocido, como Monte Carlo;
  - una interpolación de la rejilla, como IDW;
  - y una unidad de aceleración, como g.

  El censo de esta versión fija los dos lectores de esa clase que encuentra (el modelo de permeabilidad y la unidad de
  aceleración), para que uno nuevo no pase sin verse.
- **Se reporta y no se cambia** (decisión de la propietaria): cinco notas incrustan el inglés de un rechazo con
  `"%s: %s" % (tipo, exc)`:
  - la del material generalizado con un modelo que no se construye, en `rules.py:649` y `:733`;
  - `builtin_models.py:1815`;
  - la del Snowden que no se construye, en `builtin_models.py:2315`, que la primera versión no contaba;
  - y `bond.py:440`.

  Con esta versión, un parámetro desconocido dentro de ellas lleva código, y esas notas lo pierden.

## 1. Qué cambia

- **`ogr_core/file_messages.py`, nuevo y sin dependencias:**
  - el catálogo de los lectores, `FILE_MESSAGES`;
  - `file_refusal`, el texto de siempre con su código;
  - `said_as`, que pone el código a una excepción de Python;
  - y `read_enum`, el lector común de una enumeración: el mismo `ValueError`, con su texto.
- **Los tres rechazos del núcleo** (`support.py`, `materials/registry.py`, `materials/strength_model.py`) levantan la
  excepción de siempre con un `Coded` de argumento. El tipo de contorno (`boundary.py`) usa `said_as`.
- **Las veinte enumeraciones** se leen con `read_enum`:
  - las de las unidades, el material, los soportes, la grieta de tracción, las cargas, las variables aleatorias, las
    distribuciones y el foco;
  - y, desde la revisión, el tipo de suelo del modelo de permeabilidad Simple, las condiciones de contorno de la
    filtración, el tipo de valor de la rejilla de presiones, las anotaciones y los objetos de búsqueda por bloques.
- **`ogr_core/project/messages.py`:** el catálogo `IMPORT_NOTES`, `import_note` e `import_child`. `properties_import.py`
  escribe con ellos.
- **`ogr_core/project/commands.py`:** `CommandStack.holds(cmd)` dice si un paso está en deshacer, en rehacer o en
  ninguno, por identidad.
- **La ventana:**
  - `_import_properties` guarda las notas de cada importación con el paso que dejó. `_refresh_import_notes`, que la
    pila llama en cada cambio, las enseña como la sección «Importar propiedades» de Notas del análisis. La barra las
    cuenta. El paso en sí es `_import_properties_step`;
  - la cabecera del panel con notas de la importación;
  - los dos catálogos entran en `core_messages._catalogue`;
  - los tipos de campo `strength_model_list`, `parameter_list`, `enum_name` y `file_value`, con `ENUM_NAMES`,
    `strength_model_list_label`, `parameter_list_label`, `enum_name_label` y `file_value_label` en `labels.py`.
- **i18n:** los cinco rechazos, los veinte nombres de enumeración, las cinco notas, «el rango {n}», «ninguno» y la
  cabecera del panel.
- **El inglés de la ventana cambia en lo que enseñan Abrir e Importar** (el del agente no se mueve):

  | rechazo | 0.1.436 | 0.1.437 |
  |---|---|---|
  | tipo de soporte | `'Unknown support type: future_nail'` | `Unknown support type: future_nail` |
  | modelo | `"Unknown strength model: 'x'. Available: ['mohr_coulomb', …]"` | `Unknown strength model: 'x'. Available: Mohr-Coulomb; Undrained (φ=0); …` |
  | parámetro | `mohr_coulomb: unknown parameter 'x'. Valid: ['cohesion', 'friction_angle']` | `Mohr-Coulomb: unknown parameter 'x'. Valid: cohesion, friction angle (friction_angle)` |
  | tipo de contorno | `'FUTURE'` | `Unknown boundary type: 'FUTURE'` |
  | enumeración | `'x' is not a valid PorePressureType` | `'x' is not a valid value for the pore water pressure method` |

  Y la cabecera de Notas del análisis, con notas de la importación.

## 2. Qué se probó

- **`tests/test_import_messages_v1437.py`** (15 casos):
  - `_V1436`, las 95 entradas;
  - las excepciones llevan sus códigos, cada enumeración por el nombre de su clase, y `Coded` no tiene repr propio.
    Un rechazo que no se levante falla;
  - cada código con su castellano y sus campos;
  - las seis notas de una importación en castellano;
  - un valor como lo trae el archivo: entre «», null y un modelo sin parámetros;
  - y cada enumeración con su nombre;
  - la ventana real, con los diálogos sustituidos y restaurados, y un proyecto nuevo en cada prueba:
    - las notas leídas del propio panel, con su cabecera, y la barra;
    - el material seco;
    - las notas que se suman, deshacer, rehacer y un paso nuevo tras deshacer;
    - el máximo;
    - Abrir con los cinco rechazos, en castellano y en inglés, sin las comillas del repr;
    - Importar con los mismos cinco, sin dejar paso que deshacer;
    - y una clave que falta, tal cual;
  - los dos censos, con su autocomprobación:
    - en las notas, ninguna frase construida en su sitio en ninguna función de `properties_import.py`, salvo `_unique`;
    - las enumeraciones, encontradas por el propio censo: ninguna llamada sin código, los dos lectores tolerantes de
      D429, y cada `read_enum` con su nombre en `ENUM_NAMES`.
  - **Coste:** el censo de las enumeraciones analizaba todos los archivos de los tres paquetes y tardaba 4,6 s en la
    suite. Ahora solo analiza los que definen un lector (`def …from_…(`) o una clase `Enum`, filtrados por su texto, y
    recorre solo los lectores: 0,67 s. Los dos filtros se comprueban sobre la fuente propia del censo.
- **Discriminación** en el `git archive` de 5d36030, con `correr_sin_editable.py`: fallan 12 de 15. Pasan el control
  del agente (`_V1436`), la autocomprobación de los censos y «una clave que falta sigue como la escribe Python», que
  vale en los dos árboles.
- **Mutantes:** 31, y los 31 mueren (`mutants_d414.py` y su registro, en el banco):
  - **los lectores y el inglés del agente:**
    - el `ValueError` sin código;
    - uno de los seis lectores sin `read_enum`;
    - el rechazo construido desde su plantilla («Valid: »);
    - un `Coded` con repr propio;
    - las notas sin código;
  - **lo que dice la ventana:**
    - `error_text` como `str()`;
    - la enumeración por su clase;
    - los modelos por su identificador y unidos por coma;
    - los parámetros por su clave, sin su clave y sin «ninguno»;
    - el valor con las comillas de Python;
    - null como None;
    - «el sentido de la rotura»;
    - y el rango como «rule»;
  - **las notas de la ventana:**
    - sin las notas;
    - cada importación sustituye las anteriores;
    - deshacer no las quita;
    - una importación deshecha y olvidada vuelve;
    - el panel sin la sección;
    - la cabecera de antes;
    - y el error de Importar sin `error_text`;
  - **los censos:**
    - el de las notas ciego a «+»;
    - el de las enumeraciones con todo `try` como código;
    - ciego a `enum.Enum`;
    - un lector nuevo sin código;
    - un lector tolerante nuevo;
    - un `read_enum` sin nombre;
    - y cada uno de los dos filtros de texto, más estrecho.
- **Vecinos:**
  - antes de la revisión, 772 casos: `import_messages`, `strength_refusals`, `strength_reader`, `f2_rules`,
    `f2_ops`, `generalized`, `open_asks`, `materials`, `support_identity`, `focus`, `random_var`, `distribution`,
    `units`, `load`, `seismic`, `edit_messages`, `gui_spanish`, `labels_spanish`, `i18n`, `model_notes`,
    `project_io`, `undo_materials`, `task_notes` y `default_names`;
  - y después de ella, 398 casos: `dxf_problems`, `edit_messages`, `method_notes`, `model_notes`,
    `partial_method_loss`, `search_notes`, `support_silence`, `task_notes`, `api_undo`, `f2_ops`, `f2_rules`,
    `generalized_*`, `undo_materials_water`, `window_undo`, `strength_refusals`, `strength_reader`, `labels_spanish`,
    `gui_spanish` y `core_messages`.
- **La suite entera,** `--jobs 4`:
  - con el arreglo de la revisión: 7397 casos, 7396 en verde y 1 omitido, `Failed: 0`, sin `Leaks` ni `Chunks died`. La
    serie no toca: hace 15 commits de la última;
  - después se abarató el censo, que es lo único que cambió del programa y de los tests, y se volvió a correr: lo
    mismo, 7397 casos, 7396 en verde y 1 omitido, `Failed: 0`, sin `Leaks` ni `Chunks died`. El archivo nuevo tarda
    2,5 s en la suite, y antes 5,7. La mayor parte es abrir su ventana (1,6 s medido solo).
- **Banco:** `d414()` en el VC de la raíz mide, con la interfaz en castellano:
  - la nota del material seco y la barra;
  - que deshacer quita las notas;
  - el máximo en un proyecto nuevo;
  - Abrir;
  - y el agente, también con un modelo sin parámetros.

  Da CUBIERTO POR TEST con el árbol nuevo y SIGUE ABIERTO con el de 0.1.436, con los dos controles del agente iguales
  en los dos.
  - En seco, con el árbol nuevo: D335 (449 códigos en 15 catálogos, todos en castellano), D411, D412 y D415, CUBIERTO
    POR TEST.
  - `auditoria_invariantes.py`, en la raíz y en el 02: 0 ERROR. `generar_prompts.py`: 56 prompts, 18 FALTA (las 17 de
    antes y D429, sin prompt largo todavía).
  - El cierre de la ficha, tras el commit.

## 3. Qué queda

- **D422,** en 0.1.438: lo que recibe el agente de un `.ogr` mal formado, con el arreglo en el núcleo y en el API
  (decisión de la propietaria). La forma de las secciones (la clase 5 del censo) se dirá en castellano con él.
- **D421,** en 0.1.439: Importar numera los tipos de soporte. Usa las notas de esta versión.
- **D429,** al final de P10 y sin versión: los valores desconocidos que se sustituyen en silencio.
- **Prueba a mano, para la propietaria,** con la interfaz en español:
  - importar dos veces las propiedades de otro proyecto que use su nivel freático, mirar Análisis > Notas del
    análisis, deshacer una y volver a mirar;
  - abrir un `.ogr` con un tipo de soporte inventado.

# OGR Slip2D v0.1.438

**Un `.ogr` mal formado llega al agente como un rechazo con su código, y no como una excepción de Python suelta; y los
archivos de otra forma que abrían sin decir nada se rechazan (D422).** Es la mitad de D414 que lee el agente. Medido
con 0.1.435 y con 0.1.437 (`medir_d422.py` del banco): de 20 archivos estropeados, 8 daban un `AttributeError` suelto,
1 un `PermissionError` suelto, 3 abrían y 8 llegaban envueltos.

- **El núcleo comprueba la forma del archivo antes de leerlo** (`ogr_core/project/file_shape.py`, nuevo). La forma es la
  que escribe `to_dict`: la raíz es un objeto, cada sección es una lista de objetos o un objeto, y cada subsección de
  los ajustes es un objeto. Lo que no la tiene se rechaza con un `ValueError` y un código que nombra la sección:
  - «The file does not hold a project: it is a list, not an object.»;
  - «The section 'settings' of the file must be an object, not a list.»;
  - «Item 1 of the section 'focus_objects' of the file must be an object, not a list.»;
  - y un `{}`, o un objeto sin ninguna clave de proyecto, que abría un «Untitled» vacío: «The file does not hold a
    project: it has none of the keys of one.»

  La ventana lo dice en castellano: «La sección «settings» del archivo tiene que ser un objeto, no una lista.»
- **Todo archivo válido abre igual.** Lo que el lector siempre tomó como null lo sigue tomando, y solo eso: `""`, `0` y
  `false` donde va una sección se rechazan (decisión de la propietaria). Los 248 `.ogr` fuente del banco abren con el
  lector nuevo con el mismo `document_hash` que con el de 0.1.437. La revisión no encontró ninguno rechazado entre los
  2486 `.ogr` del repositorio y del histórico.
- **El API tiene un solo lector para `project_open` y `properties_import`** (`ogr_api/ops/project.py`, `load_ogr`), que
  dicen lo mismo.
  - Una carpeta que se llama `x.ogr` dice «is not a file.».
  - Un archivo que el sistema no entrega dice «cannot be read», con el tipo y el texto del error.
  - Lo que está roto **dentro** de un elemento, donde no se comprueba la forma, llega también envuelto, con el tipo y el
    texto de Python: un `AttributeError`, un `IndexError`, un `OverflowError` (un `1e999` donde va un entero) o un
    `RecursionError` (un JSON demasiado anidado). Lo decidió la propietaria en la revisión.
  - De las 5210 copias estropeadas del censo de D414, ninguna llega ya suelta al agente.
- **El servidor MCP dice lo mismo con ventana y sin ella:** una excepción inesperada sale como `[E_INTERNAL]` con su tipo
  y su texto por los dos caminos (`ogr_api.errors.internal_error`).
- **Un archivo con BOM se lee** (`utf-8-sig`): es JSON válido, y un archivo sin BOM se lee igual.
- **El inglés del agente y el de la ventana cambian en esos archivos, y se declara (§1).**
- **Ningún número cambia.** Son archivos que no abrían, o abrían mal.

Es la undécima versión de la tanda P10.

## 0. Lo que se encontró

- **Paso 0, sobre 0.1.437 (2b56e28):**
  - el guion del prompt da lo mismo que con 0.1.435: 8 `AttributeError` y 1 `PermissionError` sueltos, 3 que abren
    (`"materials": {}`, `{}` y el peso `"x"`) y 8 envueltos;
  - **la identidad del prompt es falsa en general**, como decía el plan: `from_dict(to_dict(p))` migra (D182). Se
    sustituyó por dos que sí lo son, medidas con `medir0_d422.py` (en el banco) sobre los 248 `.ogr` fuente:
    - **A/B de lectores:** el de 0.1.437 y el de 0.1.438 dan el mismo `document_hash` en los 248. Los ids se hacen
      deterministas antes de importar `ogr_core`, que fija `uuid4` al cargarse, para que dos procesos lean igual;
    - **idempotencia:** `load(save(load(f)))` da el mismo hash que `load(f)` en los 248, con los dos lectores;
  - **ninguno de los 248 tiene BOM, y todos llevan `format_version`;**
  - **el censo de formas de los 248 coincide con lo que escribe `to_dict`.** Hay `null` solo en cuatro secciones
    opcionales: `water_pressure_grid`, `fem_mesh`, `seepage_bcs` y `seepage_result`. La quinta,
    `transient_initial_result`, no está en ninguno.
- **Qué toma hoy el lector como null sin fallar, medido una por una sobre el ejemplo:**
  - seis listas (`transient_results`, `random_variables`, `annotations`, `focus_objects`, `user_surfaces` y
    `user_polylines`) y los cinco objetos opcionales;
  - y, en los ajustes, `search`, `advanced` y `design_standard`.

  La tabla los deja como «lista o null» y «objeto o null». El resto de las secciones con null ya fallaba (un
  `TypeError` o un `AttributeError`), y ahora se rechaza con código.
- **Lo que la comprobación cambia de lo que ya llegaba envuelto** (regla 6, se preguntó antes de escribir):
  - **`"boundaries": "x"` y `"materials": [null]`** salían con el texto de Python («string indices must be integers»,
    «'NoneType' object is not subscriptable»). **Decisión de la propietaria:** también dicen la frase nueva, porque son
    la misma clase de defecto. `"settings": {"methods": []}`, que daba «MethodsSettings() argument after ** must be a
    mapping», es de la misma clase y también la dice;
  - **`"settings": {"search": []}` abría** con los valores por defecto de la búsqueda, como `"materials": {}` abría sin
    materiales. Ahora se rechaza.
  - Los otros cinco envueltos no se mueven: un vértice como texto, un JSON roto, unos bytes que no son UTF-8, un
    material sin nombre y un contorno de tipo desconocido. Siguen como los escribe Python, dentro del marco traducido en
    la ventana (la regla de D412).
- **La revisión** (`/revisar`) encontró en el diff dos cosas, y la propietaria las decidió:
  - **lo roto dentro de un elemento seguía llegando suelto.** El docstring de `load_ogr` decía que, comprobada la
    forma, un `AttributeError` solo podía ser un fallo de un lector, y no era verdad. El censo de D414 sobre esta
    versión sacaba 9 copias sueltas, porque la forma se comprueba hasta los elementos de cada sección y no dentro de
    ellos:
    - 2 `AttributeError`, como un null en la distribución de una variable aleatoria;
    - y 7 `IndexError`, como una huella de región con un vértice de una sola coordenada.

    En 0.1.437 eran 66 `AttributeError`. **Decisión de la propietaria:** `load_ogr` los envuelve también, con su tipo y
    su texto, como ya listaba el prompt. Un fallo de verdad de un lector saldrá como archivo ilegible y sin traza. El
    test fija los dos casos, y el censo da ahora 109 grupos de 109 envueltos;
  - **la frase nueva se aplicó a toda la clase,** no solo a los dos envueltos que nombró la propietaria. Medido copia a
    copia con el censo, **100 copias que abrían con 0.1.437 se rechazan ahora**, y ninguna hace el camino contrario.
    Todas tienen una sección de otra forma:
    - un objeto donde va una lista, en las 13 secciones de listas que tienen los modelos del censo (6 copias cada una;
      en la pregunta a la propietaria dije 16, mal contado);
    - una lista donde va un objeto opcional, en las 4 que tienen (1 cada una);
    - y una lista en `settings.search`, `settings.advanced` o `settings.design_standard` (6 cada una).

    La clase es más ancha que el censo: son 14 secciones de listas (falta `user_polylines`) y 5 objetos opcionales
    (falta `transient_initial_result`), porque los modelos del censo no tienen ninguna de las dos. Abren 4224 copias de
    5210, y antes 4324. **La propietaria confirmó la clase entera.**
- **La revisión adversaria** (diecinueve agentes, 15 hallazgos, uno refutado) encontró en el diff:
  - **lo que el lector se tragaba como vacío.** Los modismos que tomaban un null (`if section:`, `or {}`, iterar)
    tomaban también `""`, `0` y `false`: 50 pares de sección y valor que abrían con 0.1.437. Pasaba lo mismo con un
    objeto sin ninguna clave de proyecto (un GeoJSON renombrado a `.ogr` abría un «Untitled» vacío). El censo no los
    veía, porque sus mutaciones no ponen `""`, `0` ni `false` donde va una sección. **Decisión de la propietaria:** se
    rechazan, como cualquier sección de otra forma y como `{}`, y se declaran. El docstring de `file_shape.py` decía
    que se seguía tolerando «lo que el lector tomó como null», y ahora dice que solo el null;
  - **dos excepciones más llegaban sueltas:** un `1e999` donde va un entero (`int(inf)`, `OverflowError`) y un JSON
    anidado 100 000 niveles (`RecursionError`). **Decisión de la propietaria:** también se envuelven, con la lista
    explícita (`ArithmeticError` y `RecursionError`), sin un `except Exception`;
  - **el castellano de un mensaje:** «no tiene ninguna de sus claves» se leía como las claves del archivo. Ahora dice
    «no tiene ninguna de las claves de un proyecto»;
  - **la clave y null en la ventana en castellano.** La ventana nombra una sección por su clave JSON («La sección
    «settings.methods»…») y dice null como null, como D414 dice un valor tal como lo trae el archivo. **La propietaria
    lo confirmó:** quien arregla el archivo busca la clave;
  - **el inglés de la ventana cambiaba sin declararse** (§1);
  - **y los huecos del test:**
    - el modelo «con todas las secciones» no tenía malla, campo de filtración ni resultados transitorios, y una tabla
      que rechazara todo modelo de filtración guardado pasaba. Ahora tiene una malla de un triángulo y sus campos;
    - el test de los null leía de la misma tabla las secciones que debía comprobar. Ahora las lleva escritas, medidas
      con 0.1.437;
    - solo se probaba el primer elemento de una lista, y ahora también el segundo;
    - y la discriminación tenía la cuenta mal explicada (§2).

    Todo arreglado, con 22 mutantes. Además:
    - las cuentas de este changelog (cinco secciones con null en el banco, que son cuatro) y el `LEEME.md` del banco,
      que se habían quedado viejos;
    - el registro de la A/B con 0.1.438, que decía «0.1.437» porque se midió antes de subir la versión y se ha vuelto a
      medir.

    El refutado decía que el primer caso del MCP pasaba de 5 s sin decirlo en la cabecera. Medido solo tarda 2,5 s, y
    AGENTS.md pide la razón a partir de 5 s medidos solo.
- **Fuera de la ficha, se dice** (la revisión): la línea de órdenes (`ogr_cli`, `info` y `compute`) lee con
  `Project.load` sin `except`, así que una carpeta o un `.ogr` mal formado acaban en una traza. Era así antes; ahora la
  traza lleva la frase nueva. No es el agente, y queda para que la propietaria decida si pide ficha.
- **El peso `"x"`** (un valor de otro tipo dentro de una sección) abre, `project_validate` da `can_run` sin avisos, y el
  cálculo falla con `TypeError: can't multiply sequence…`. El plan proponía abrirle ficha como D429, pero ese número lo
  tomó la revisión de 0.1.437. **Decisión de la propietaria:** amplía D429, que ya era «un `.ogr` que abre sin decir
  nada». Esta versión comprueba la forma de las secciones, no los valores que llevan dentro.
- **La referencia de D414 cambia en lo que se decidió unificar.** `test_import_messages_v1437` fijaba el inglés de
  `properties_import` de 0.1.436, que no llevaba el tipo de la excepción. Con un solo lector, cada rechazo suyo es el de
  `project_open`. El test lo dice así, como identidad con el `project_open` de 0.1.436, y no con un texto nuevo.
- **Lo que apareció al escribir:**
  - **la captura de 0.1.437 acumulaba los materiales importados en un mismo destino,** así que la numeración de un
    caso («Silty clay (2)» o «(3)») dependía de cuántos casos abrían antes, y eso cambia entre los dos árboles. Cada
    importación tiene ahora su destino;
  - **un `OSError` que no es una carpeta** (un archivo bloqueado o sin permiso) no lo produce ninguno de los 20
    archivos, y su mutante sobrevivía. El test lo provoca sustituyendo `Project.load`;
  - **el texto de un `RecursionError` del decodificador cambia con la versión de Python** («Stack overflow (used
    2912 kB)…» en 3.14): el test fija su tipo, no su texto;
  - **el heredoc de la herramienta Bash volvió a convertir `\\n` en un salto de línea** dentro de un guion de edición. Se
    deshizo con Edit.
- **No cambia y se dice:** una carpeta abierta desde la ventana sigue diciendo el texto de Python («[Errno 13]
  Permission denied»), porque Abrir no pasa por el lector del API. El diálogo de archivo no deja elegir una carpeta.

## 1. Qué cambia

- **`ogr_core/project/file_shape.py`, nuevo:** `SECTIONS` y `SETTINGS_SECTIONS` (literales, la forma de `to_dict`) y
  `check_shape(data)`. Una clave que esta versión no conoce se deja como siempre.
- **`ogr_core/file_messages.py`:** cuatro códigos (`not_a_project`, `no_project_key`, `section_shape`, `item_shape`),
  `SHAPE_WORDS` (las palabras con que se dice cada forma) y `json_shape`.
- **`Project.load`** lee con `utf-8-sig`, y **`Project.from_dict`** llama a `check_shape` antes de nada.
- **`ogr_api`:**
  - `ops/project.py:load_ogr`, el lector de las dos operaciones: `is_file()`, el `OSError` como «cannot be read», y el
    `ValueError`, `KeyError`, `TypeError`, `AttributeError`, `IndexError`, `ArithmeticError` o `RecursionError` de
    `Project.load` con su tipo;
  - `errors.internal_error`, que usan el puente (`bridge.error_to_dict`) y el servidor MCP (`ogr_mcp/server.py`,
    `_errors`).
- **La ventana:** el tipo de campo `json_shape` (`core_messages._show`, `labels.json_shape_label`) y el castellano de
  los cuatro mensajes y de las siete palabras.
- **El inglés del agente cambia, por decisión de la propietaria** (en el agente, todo lo demás no se mueve):

  | archivo | 0.1.437 | 0.1.438 |
  |---|---|---|
  | raíz lista, número, texto, null o `true` | `AttributeError` suelto | `[E_INVALID_ARGUMENT] … ValueError: The file does not hold a project: it is a list, not an object.` |
  | `"settings": []`, `"seismic": []` | `AttributeError` suelto | `… The section 'settings' of the file must be an object, not a list.` |
  | `"focus_objects": [[1]]`, `"random_variables": ["x"]` | `AttributeError` suelto | `… Item 1 of the section 'focus_objects' of the file must be an object, not a list.` |
  | una carpeta `x.ogr` | `PermissionError` suelto | `[E_INVALID_ARGUMENT] <ruta> is not a file.` |
  | un archivo bloqueado o sin permiso | `PermissionError` suelto | `[E_INVALID_ARGUMENT] <ruta> cannot be read: PermissionError: …` |
  | un objeto donde va una lista (`"materials": {}`), una lista donde va un objeto opcional, o `settings.search`, `advanced` o `design_standard` como lista | abre | `… The section 'materials' of the file must be a list, not an object.` |
  | `""`, `0` o `false` donde va una sección | abre | `… The section 'focus_objects' of the file must be a list or null, not a boolean.` |
  | `{}`, o un objeto sin ninguna clave de proyecto | abre un «Untitled» vacío | `… it has none of the keys of one.` |
  | `"boundaries": "x"`, `"materials": [null]`, `"settings": {"methods": []}` | envuelto, texto de Python | la frase de su forma |
  | algo roto dentro de un elemento (`random_variables/0/distribution` null, un vértice de una coordenada en una huella, un `1e999` donde va un entero) | `AttributeError`, `IndexError` u `OverflowError` suelto | `[E_INVALID_ARGUMENT] … AttributeError: …`, con el texto de Python |
  | un JSON demasiado anidado | `RecursionError` suelto | `[E_INVALID_ARGUMENT] … RecursionError: …` |
  | con BOM | envuelto (`Unexpected UTF-8 BOM`) | abre |
  | cualquier rechazo de `properties_import` | sin el tipo de la excepción | el de `project_open`, con el tipo |
  | una excepción inesperada por el MCP sin ventana | `ValueError: …` | `[E_INTERNAL] ValueError: …`, como con ventana |

- **El inglés de la ventana cambia también, en lo que enseñan Abrir e Importar propiedades.** Dentro del marco de
  siempre («Could not open project:» y «Could not read the project:»):

  | archivo | 0.1.437 | 0.1.438 |
  |---|---|---|
  | raíz, sección o elemento de otra forma | el texto de Python (`'list' object has no attribute 'get'`, `string indices must be integers…`) | la frase de su forma, la del agente |
  | lo que abría con otra forma, o `{}` y un objeto sin claves de proyecto | abría | se rechaza con la frase de su forma |
  | con BOM | `Unexpected UTF-8 BOM (decode using utf-8-sig)…` | abre |

  En castellano, la ventana dice la frase en castellano. Lo demás de Python (una clave que falta, un JSON roto, unos
  bytes que no son UTF-8) sigue tal cual dentro del marco.

## 2. Qué se probó

- **`tests/test_ogr_open_refusals_v1438.py`** (17 casos):
  - **todo archivo válido abre igual:**
    - la tabla tiene la forma de cada clave que escribe `to_dict()` de un modelo que tiene todas las secciones, malla
      y campos de filtración incluidos, ninguna en null;
    - sus claves son las que leen `Project.from_dict` y `ProjectSettings.from_dict`, por AST, con `format_version`
      como la única que se escribe y no se lee;
    - un archivo guardado y vuelto a leer da el mismo `document_hash`;
    - cada null que el lector siempre tomó sigue abriendo. Las secciones van escritas en el test, medidas con 0.1.437;
    - solo el null: `""`, `0` y `false` en esas secciones, y un null en las demás, se rechazan (61 casos);
    - y un archivo con BOM se lee como el mismo sin él;
  - **ninguno de los 32 casos sale de `ogr_api.call` sin ser `OgrApiError`.** Son los 20 del guion y doce más: una raíz
    `true`, dos subsecciones de los ajustes, dos cosas rotas dentro de un elemento, tres valores «vacíos», un objeto
    sin claves de proyecto, un segundo elemento malo, un `1e999` y un JSON anidado. Abren el BOM y el peso `"x"`
    (D429);
  - las dos operaciones dicen lo mismo;
  - lo que no se mueve es `_V1437`: 64 entradas medidas ejecutando `_capture()` del test sobre un `git archive` de
    2b56e28 (`capture_d422.py`, en el banco). Lo que se mueve dice la frase de su forma, escrita en el test;
  - un archivo que el sistema no entrega;
  - las excepciones llevan sus códigos;
  - el MCP, con un *backend* que hace lo del puente y sin él, da el mismo texto en los 32, y una excepción inesperada
    sale como `[E_INTERNAL]` por los dos;
  - el castellano de los cuatro mensajes y de las palabras;
  - y Abrir en la ventana real, con el diálogo de archivo y el aviso sustituidos y restaurados.
- **Discriminación** en el `git archive` de 2b56e28, con `correr_sin_editable.py`: fallan 14 de 17.
  - 9 fallan por lo que hace 0.1.437, y 5 porque los nombres nuevos no existen.
  - Pasan los tres controles: la idempotencia, los null que el lector siempre tomó y la referencia de 0.1.437.
- **Mutantes:** 22, y los 22 mueren (`mutants_d422.py` y su registro, en el banco):
  - **el lector del agente:**
    - el `except` de 0.1.437;
    - la carpeta dicha por Python;
    - un `OSError` suelto;
    - lo roto dentro de un elemento suelto;
    - y un `OverflowError` o un `RecursionError` sueltos;
  - **la forma:**
    - sin comprobación;
    - sin la de las claves de un proyecto;
    - sin la de los elementos;
    - solo el primer elemento;
    - sin la de los ajustes;
    - una lista y dos ajustes que dejan de tomar null;
    - un valor «vacío» tomado por null;
    - la malla dicha como lista;
    - un valor lógico dicho como número;
    - sin BOM;
    - y una sección nueva de `to_dict` sin su forma;
  - **el MCP:** `_errors` sin código;
  - **la ventana:** las formas por su clave y en inglés;
  - **el censo de las claves que leen los lectores,** ciego.
- **Vecinos** (`--jobs 4`), con los arreglos de las dos revisiones, 480 casos en verde:
  `ogr_open_refusals`, `mcp_server`, `live_bridge`, `open_asks`, `strength`, `f2_ops`, `groundwater_ops`,
  `import_messages`, `project_io`, `open_`, `bridge`, `snapshot`, `migration`, `roundtrip`, `default_names`, `agent_`,
  `api_undo`, `f2_rules`, `task_notes`, `model_notes`, `edit_messages`, `labels_spanish`, `gui_spanish`,
  `core_messages` y `version_consistency`.
- **La suite entera,** `--jobs 4`:
  - antes de las revisiones y con los arreglos de `/revisar`: dos corridas de 7413 casos, 7412 en verde y 1 omitido,
    `Failed: 0`, sin `Leaks` ni `Chunks died`. La serie no toca (16 commits de la última);
    - el archivo nuevo tardó 12 s en la primera, 9,2 de ellos en su primer caso del MCP. Importar el SDK cuesta 1,3 s
      solo y construir el servidor 0,23; el resto es la máquina cargada con cuatro tramos;
    - en la segunda tardó 6,2 s;
  - con los arreglos de la revisión adversaria: 7414 casos, 7413 en verde y 1 omitido, `Failed: 0`, sin `Leaks` ni
    `Chunks died`. El archivo nuevo tardó 6,6 s. Los README pasan a 7413.
- **Banco:**
  - `medir_d422.py` con el árbol nuevo: 18 de 20 llegan como `InvalidArgument`, abren 2 (el BOM y el peso `"x"`), y
    el MCP no deja ningún registro «tool failed»;
  - el censo de D414 con el árbol nuevo: de 5210 copias abren 4224, y los 109 grupos de fallo llegan al agente como
    `InvalidArgument`;
  - `medir0_d422.py` con 0.1.438 (ya con la versión subida): los 248 abren con el mismo hash que con 0.1.437;
  - `d422()` en el VC de la raíz mide la raíz como lista, `"settings": []` y la carpeta. Da CUBIERTO POR TEST con el
    árbol nuevo y SIGUE ABIERTO con el de 0.1.437;
  - D429 ampliada con el peso `"x"`;
  - en seco, con el árbol nuevo: D412, D414, D415 y D335, CUBIERTO POR TEST (la lista de catálogos de D335 es la
    de su versión, y no cuenta los de D414 ni los de esta);
  - `auditoria_invariantes.py`, en la raíz y en el 02: 0 ERROR. `generar_prompts.py`: 55 prompts, las 18 FALTA de
    antes;
  - el cierre de la ficha, tras el commit.

## 3. Qué queda

- **D421,** en 0.1.439: Importar numera los tipos de soporte.
- **D429,** al final de P10 y sin versión: los valores desconocidos que se sustituyen en silencio, y el valor de otro
  tipo que abre y solo falla al calcular.
- **Para la propietaria:** si la línea de órdenes, que sigue dando una traza con un `.ogr` mal formado, pide ficha.
- **Prueba a mano, para la propietaria,** con la interfaz en español: abrir un `.ogr` cuyo `"settings"` sea `[]` y
  leer el aviso.

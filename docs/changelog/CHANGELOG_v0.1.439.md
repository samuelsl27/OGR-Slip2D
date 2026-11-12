# OGR Slip2D v0.1.439

**Importar propiedades numera un tipo de soporte cuyo nombre ya tiene el modelo, como siempre numeró un material, y el
agente vuelve a encontrar cada conjunto por su nombre (D421).** Medido con 0.1.435 y con 0.1.438 (`medir_d421.py` del
banco):

- un «Type 1» importado sobre un «type 1 » seguía llamándose «Type 1»;
- la barra decía «Los nombres duplicados se han numerado en lugar de sobrescribirse.»;
- y el agente ya no encontraba ninguno de los dos por su nombre: `[E_NOT_FOUND] Unknown support type 'Type 1'`, con el
  nombre dos veces entre los conocidos.

Ahora:

- **Una sola regla para los dos** (`ogr_core.naming.numbered_name`, la de D415, con la comparación de `find_type`): el
  tipo importado se llama «Type 1 (2)», como el material «Silty clay (2)».
  - Por decisión de la propietaria, también se numera el segundo de dos conjuntos de un nombre que vienen en un mismo
    archivo: no puede haber dos conjuntos con el mismo nombre.
  - `_unique` desaparece, y `support_type_set` importa la regla en vez de copiarla.
  - Un conjunto sin choque conserva lo que traía, también el nombre de su clase.
- **La barra dice cuántos nombres se numeraron, y solo si se numeró alguno:** «Importados 1 material(es) y 1 tipo(s) de
  soporte. 2 nombre(s) se han numerado para que no se repitan.» En castellano el conjunto se lee «Tipo 1 (2)», por la
  etiqueta de D415.
- **El agente**, por decisión de la propietaria:
  - dos conjuntos de un nombre son **ambiguos**, no desconocidos: `[E_CONFLICT] 2 support types are named 'Grouted
    Tieback'. Hint: Pass one of their ids: '<id>' (Grouted Tieback), '<id>' (Grouted Tieback).`;
  - y renombrar un conjunto a un nombre que ya tiene otro se niega, como crearlo, con cualquier combinación de mayúsculas:
    `[E_CONFLICT] A support type named 'Type 1' exists.` Su propio nombre, repetido o con otras mayúsculas, sigue siendo
    un renombrado, también en un modelo con dos conjuntos de ese nombre.
- **Dos defectos anteriores de `support_type_set`, por decisión de la propietaria:**
  - modificaba **el conjunto equivocado** cuando había dos de una clase con los mismos parámetros. Salió al medir, y se
    preguntó antes de tocarlo. Ahora sustituye por identidad;
  - al modificar un conjunto con una clase desconocida daba un `KeyError` suelto, y ahora da el rechazo con código de
    crear. Lo encontró la revisión.
- **Ningún número cambia:** el motor resuelve un soporte por `type_ref`, nunca por el nombre, y cada conjunto importado
  conserva su id nuevo y sus parámetros.

Es la duodécima versión de la tanda P10.

## 0. Lo que se encontró

- **Paso 0, sobre 0.1.438 (773b246):**
  - `medir_d421.py` da lo mismo que con 0.1.435:
    - un nombre distinto de tres con la comparación de `find_type`;
    - la barra que dice que se numeraron;
    - `support_set` por el nombre, que no lo encuentra;
    - y renombrar «Malla» a «Type 1», aceptado;
  - **cuántos `.ogr` del banco tienen dos conjuntos de un nombre:** uno de los 248, el 049, con dos «Grouted Tieback»
    nombrados por su clase. El plan contaba también el 050, con siete «Soil Nail», pero hoy sus nombres ya no chocan.
    En el 049, el agente dice ahora «ambiguo» si se le pide un conjunto por ese nombre. Ningún guion del banco lo
    hace;
  - **la regla:** la A del prompt, la de los materiales y de `support_type_set` («Type 1 (2)»), que es ya
    `ogr_core.naming.numbered_name` (D415). Decidida en el plan.
- **Un defecto anterior, medido y preguntado antes de tocarlo** (regla 6):
  - `support_type_set` sustituía el conjunto modificado con `project.support_types.index(old)`, que compara los
    conjuntos como dataclasses, y su campo `id` está fuera de la comparación (`compare=False`);
  - con un «Soil Nail» y un «Malla» de la misma clase y los mismos parámetros, renombrar «Malla» a «MALLA» convertía
    «Soil Nail» en «MALLA», dejaba «Malla» como estaba y dejaba dos conjuntos con el mismo id;
  - lo traza `indice_por_igualdad_d421.py` (en el banco) con 0.1.438. Es el único sitio así: los contornos se comparan
    por su id;
  - **decisión de la propietaria:** se arregla aquí, con un test. La sustitución va por identidad.
- **La revisión adversaria** (dieciocho agentes, 14 hallazgos, uno refutado) encontró en el diff:
  - **el propio nombre se negaba** en un modelo con dos conjuntos de ese nombre (la forma del 049): repetirlo, o
    cambiarle las mayúsculas, pidiendo el conjunto por su id. La pista mandaba además al nombre ambiguo. La negativa
    solo vale ahora cuando el nombre cambia;
  - **un mismo archivo con dos conjuntos de un nombre** sale numerado, aunque el modelo no tuviera ninguno, y la barra
    decía «que el modelo ya tenía». **Decisión de la propietaria:** se numera, porque es la regla, y la barra dice «N
    nombre(s) se han numerado para que no se repitan.»;
  - **un nombre que no es texto** (un 5 o un null escritos a mano en un conjunto o en un material) ya no hace fallar
    las búsquedas ni la importación, porque `name_key` compara `str(nombre)`. Antes era un `AttributeError` suelto. Por
    la API de Python, `support_type_set(name=7)` guarda un 7; el MCP no lo deja pasar. **Decisión de la propietaria:**
    se declara (§1) y amplía D429, la familia de los valores de otro tipo;
  - **un defecto anterior junto a lo tocado:** al modificar un conjunto con una clase desconocida, `support_type_set`
    buscaba la clase en el registro antes de comprobar que existía, y daba un `KeyError`. **Decisión de la
    propietaria:** se arregla aquí. Solo se llega por la API de Python o `python_exec`, porque el MCP limita la clase;
  - **otro anterior, fuera de la ficha:** el runner de tests descarta sin avisar un patrón que no casa con nada si va
    junto a otros. Así se colaron en la lista de vecinos de este changelog tres patrones que no corrieron nada.
    **Decisión de la propietaria:** ficha nueva, **D431**, al final de P10 y sin versión;
  - **y los huecos del test:**
    - nada fijaba los repetidos dentro de una misma importación;
    - el renombrado negado solo se probaba con las mismas mayúsculas;
    - el mutante «los nombres comparados con sus mayúsculas» parcheaba `ogr_core.naming`, pero `supports.py` y
      `properties_import.py` importan `name_key` al cargarse, así que solo alcanzaba `numbered_name`;
    - dos de las respuestas que se mueven no se comparaban con nada, y otras dos solo en parte.

    Todo arreglado, con 15 mutantes. Además se corrigieron el docstring de `capture_d421.py` (decía «0.1.437») y la
    lista de vecinos de este changelog. El hallazgo refutado decía que `set_label` copiaba `_label` del API en vez de ser
    la regla de `find_type`: son el mismo texto, y la comparación es `name_key`.
- **Lo que apareció al escribir:**
  - **la captura de 0.1.438 tenía que ordenar sus pasos:**
    - en 0.1.438 un renombrado a un nombre que ya existe se acepta, y eso cambia lo que ven los pasos siguientes;
    - y el renombrado equivocado del defecto de arriba deja «MALLA» como nombre de dos conjuntos;
    - además, la lista de conocidos de un nombre desconocido incluye los nombres importados, así que ese paso va en un
      modelo vacío;
  - **el censo de notas de D414** daba por hecho que existía `_unique`, «la función que construye un nombre en su
    sitio». Con la regla en `ogr_core.naming` ya no hay ninguna, y el censo lee ahora todas las funciones de
    `properties_import.py` sin excepción;
  - **la sección 5 de `medir_d421.py`** llama a `_unique`, que ya no existe. Es un guion de medida de los árboles
    viejos, y sus secciones 1 a 4 dan con 0.1.439 lo que pide el criterio de cierre.

## 1. Qué cambia

- **`ogr_core/project/properties_import.py`:**
  - los materiales y los tipos de soporte se numeran con `numbered_name`, también entre los de un mismo archivo, y
    `_unique` desaparece;
  - un tipo numerado guarda su nombre en `_display_name` y lo devuelve en `support_types`;
  - `set_label`, el nombre por el que se conoce un conjunto;
  - y el argumento `renamed`, que recibe las parejas (nombre traído, nombre guardado) de lo numerado. Lo usa la
    ventana; el agente lee los nombres.
- **`ogr_api/ops/supports.py`:**
  - `find_type` dice `E_CONFLICT` con los ids ante dos o más conjuntos de un nombre;
  - `support_type_set`:
    - importa `numbered_name`;
    - niega un renombrado a un nombre que tiene otro conjunto, salvo el suyo;
    - comprueba la clase antes de buscarla;
    - y sustituye el conjunto modificado por identidad.
- **La ventana** (`main_window._import_properties`): la barra cuenta los nombres numerados, solo cuando los hay. Dos
  textos nuevos y su castellano sustituyen al de antes.
- **El inglés del agente cambia, por decisión de la propietaria** (en el agente, todo lo demás no se mueve):

  | llamada | 0.1.438 | 0.1.439 |
  |---|---|---|
  | `properties_import` con un tipo de un nombre que ya existe | `"support_types": ["Type 1"]` | `"support_types": ["Type 1 (2)"]` |
  | `properties_import` de un archivo con dos conjuntos de un nombre | `["Grouted Tieback", "Grouted Tieback"]` | `["Grouted Tieback", "Grouted Tieback (2)"]` |
  | un conjunto pedido por un nombre que tienen dos | `[E_NOT_FOUND] Unknown support type 'X'. Hint: Known: …` | `[E_CONFLICT] 2 support types are named 'X'. Hint: Pass one of their ids: …` |
  | `support_type_set` que renombra a un nombre de otro conjunto | aceptado (dos conjuntos de un nombre) | `[E_CONFLICT] A support type named 'X' exists. Hint: Pass support_type='X' to change it.` |
  | `support_type_set` que modifica uno de dos conjuntos iguales | modificaba el primero | modifica el pedido |
  | `support_type_set` que modifica un conjunto con una clase desconocida | `KeyError` suelto | `[E_NOT_FOUND] Unknown support class 'x'.`, como al crear |
  | un nombre que no es texto (un 5 o un null) en un conjunto o en un material | `AttributeError` suelto al buscarlo o importarlo | se compara como texto: el 5 se encuentra por «5», e importar numera «5 (2)» (D429) |

- **El inglés de la ventana cambia en la barra de Importar propiedades:** «Imported 1 material(s) and 1 support
  type(s).», y «N name(s) were numbered so that no two are the same.» solo cuando se numeró alguno. Antes decía siempre
  «Duplicated names were numbered rather than overwritten.»

## 2. Qué se probó

- **`tests/test_import_support_names_v1439.py`** (11 casos):
  - **la identidad:** tras tres importaciones, `find_type(proyecto, nombre)` es ese mismo conjunto para cada uno, y los
    cuatro nombres son distintos con `name_key`;
  - **una regla para los dos:** el material y el tipo de un nombre salen «Silty clay (2)» y «Type 1 (2)» por
    `numbered_name`, y `renamed` lo cuenta;
  - dos conjuntos y dos materiales de un nombre en un mismo archivo: se numera el segundo, y cada conjunto se encuentra
    por su nombre;
  - un conjunto sin choque conserva su archivo salvo el id, y uno nombrado por su clase no gana un nombre;
  - ids nuevos, los mismos parámetros, y un soporte enganchado por id resuelve a su conjunto;
  - **el agente:**
    - lo que no se mueve es `_V1438`: 16 entradas medidas ejecutando `_capture()` del test sobre un `git archive` de
      773b246 (`capture_d421.py`, en el banco);
    - lo que se mueve, entero: cada respuesta de 0.1.438 con solo el cambio decidido;
    - un renombrado cambia el conjunto que nombra;
    - un nombre de otro se niega con otras mayúsculas;
    - el propio nombre, repetido o con otras mayúsculas, se acepta en la forma del 049;
    - una clase desconocida dice su código al modificar;
    - y dos conjuntos de un nombre dan los dos ids, y cada uno se encuentra por su id;
  - **la ventana**, con el diálogo de archivo y el de elección sustituidos y restaurados:
    - la barra cuenta los dos nombres numerados, y sin choque no dice que se numerara nada;
    - y el conjunto se lee «Tipo 1 (2)».
- **Discriminación** en el `git archive` de 773b246, con `correr_sin_editable.py`: fallan 9 de 11.
  - Pasan los dos controles: el soporte que resuelve por id y la referencia de 0.1.438.
  - Tres de los 9 fallan por el argumento nuevo `renamed`, y los otros 6 por lo que hace 0.1.438.
- **Mutantes:** 15, y los 15 mueren (`mutants_d421.py` y su registro, en el banco):
  - **el núcleo:**
    - el tipo con el nombre que traía;
    - el nombre numerado sin guardar;
    - los nombres comparados con sus mayúsculas, en los tres módulos que importan la comparación;
    - un conjunto sin choque con nombre propio;
    - `renamed` sin rellenar;
    - y los conjuntos y los materiales de un mismo archivo sin separar;
  - **el agente:**
    - dos de un nombre dichos como desconocidos;
    - un renombrado a un nombre de otro aceptado, y comparado con sus mayúsculas;
    - el propio nombre negado;
    - la clase buscada antes de comprobarla;
    - y la sustitución por igualdad;
  - **la ventana:** la barra que lo dice siempre y que no lo dice nunca.
- **Vecinos** (`--jobs 4`), 341 casos de 19 archivos, cada patrón comprobado con `--list` (el runner descarta sin avisar
  uno que no casa: D431): `import_support_names`, `f2_rules`, `f2_ops`, `generalized_links`, `mcp_server`,
  `default_names`, `import_messages`, `ogr_open_refusals`, `support_identity`, `supports_spanish`, `spanish_paths`,
  `undo_loads_supports`, `window_undo`, `zero_length_support`, `labels_spanish`, `gui_spanish`, `api_undo`, `task_notes`
  y `version_consistency`.
- **La suite entera,** `--jobs 4`:
  - antes de la revisión adversaria: 7423 casos, 7422 en verde y 1 omitido, `Failed: 0`, sin `Leaks` ni `Chunks died`.
    La serie no toca (17 commits de la última);
  - con sus arreglos: 7425 casos, 7424 en verde y 1 omitido, `Failed: 0`, sin `Leaks` ni `Chunks died`. Los README
    pasan a 7424.
- **Banco:**
  - `medir_d421.py` con el árbol nuevo:
    - tres nombres distintos de tres;
    - la barra que cuenta el nombre numerado;
    - `support_set` por el nombre, que lo encuentra;
    - y renombrar «Malla» a «Type 1», negado;
  - `d421()` en el VC de la raíz mide un «Type 1» importado sobre otro en el núcleo, en la ventana y en el agente. Da
    CUBIERTO POR TEST con el árbol nuevo y SIGUE ABIERTO con el de 0.1.438;
  - D429 ampliada con los nombres que no son texto, y D431 abierta;
  - en seco, con el árbol nuevo: D414, D415 y D422 de la raíz, CUBIERTO POR TEST, y D66 del 02 (`--seco`), SE
    SOSTIENE: los factores del 049 y del 050, que tienen conjuntos de soporte, siguen dentro de su referencia;
  - `auditoria_invariantes.py` en la raíz: 0 ERROR. `generar_prompts.py`: 56 prompts, 20 FALTA (las 18 de antes, D430
    y D431, sin prompt largo);
  - el cierre de la ficha, tras el commit.

## 3. Qué queda

- **Sin ficha, del plan de esta tanda:** un soporte colocado copia el nombre de su conjunto y no lo sigue al
  renombrarlo (el `name` de `support_set`), y Definir soporte acepta un nombre tecleado que repite otro. Esta versión no
  los toca.
- **D429, D430 y D431,** al final de P10 y sin versión.
- **D419,** en 0.1.440: el retroanálisis de Interpretar con los datos de la corrida.
- **Prueba a mano, para la propietaria,** con la interfaz en español: importar dos veces un mismo tipo de soporte desde
  otro proyecto, y mirar la barra y la lista de Definir soporte.

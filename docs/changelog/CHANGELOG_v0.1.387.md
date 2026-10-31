# OGR Slip2D v0.1.387

**Un resultado guarda los materiales con los que se calculó, no los objetos del proyecto vivo (D381).**

Lo encontró la revisión de 0.1.386, y la propietaria decidió arreglarlo en su propia versión antes de seguir con V9.
Es anterior a V8: V8 solo amplió a qué rejillas les pasaba.

Ningún número del cálculo se mueve. Lo que cambia es lo que enseña un resultado guardado cuando, después de calcular,
alguien edita un material en el sitio.

## 0. Lo que se encontró y lo que se decidió

- **Qué pasaba.** El rebanador pone en cada dovela el objeto `Material` del proyecto que analiza. Sin norma de diseño
  ni enlaces de Generalized Anisotropic, ese proyecto es el del usuario. Un resultado calculado en el proceso guardaba
  esos objetos; uno que vuelve del pool trae copias deserializadas.
- **Qué lo disparaba:** una edición del material en el sitio después de calcular. El `material_set` del agente por el
  puente de la ventana lo hace, y también un script de `python_exec` o de la terminal. El diálogo de materiales no,
  porque edita copias.
- **Reproducido** en un talud con nivel freático y un anclaje, calculado en el proceso:
  - la dovela apuntaba al material vivo;
  - tras cambiar la cohesión de 8 a 2 y el nombre, las filas pasaban de ('clay', 8.0) a ('edited after the run',
    2.0), y el estado entre dovelas cambiaba;
  - tras una restauración como la de Deshacer, que devuelve copias profundas a `project.materials`, seguía enseñando
    lo editado. La huella del modelo vuelve entonces a la del resultado, así que nada lo marca como caduco.
- **El censo** de lo que un resultado comparte con el proyecto vivo, sobre ese modelo y nueve del banco (soportes,
  pilotes, desembalse, varios materiales, de uno a siete métodos): solo el `Material` de las dovelas.
  - El `EnumType` que aparece en el 097 es una clase de enumeración, un singleton.
  - Los lectores (la tabla de Interpretar, `slice_rows`, el estado entre dovelas de `postprocess` y el informe PDF)
    leen `s.material`; ninguno lo busca por `id`.
- **Las decisiones de la propietaria:**
  - el arreglo va en el motor, no solo en la ventana, para que cubra también los scripts;
  - se acepta el coste de recorrer todas las dovelas de cada resultado.

## 1. Qué cambia

- **`ogr_slip2d/search.py`:**
  - **`detach_materials(project, results)`:** cada dovela cuyo material es uno de los objetos del proyecto analizado
    recibe una copia profunda, una por material y por llamada, compartida por todas las dovelas que lo cortaron. Los
    valores y el `id` son los del material, así que una búsqueda por `id` sigue encontrándolo. Una dovela con otro
    material (un resultado del pool, los materiales de la etapa 2 del desembalse) se deja como está.
  - **`_results_of(result)`:** las evaluaciones de la búsqueda y las del usuario, más los mínimos y la optimizada, que
    una búsqueda puede guardar fuera de ellas.
  - **`SlipSearch.run`** la llama al final, después de las superficies del usuario y de la optimización. Así cubre
    Calcular, la corrida determinista de la estadística, el retroanálisis, el barrido, el transitorio y la
    optimización dentro de la búsqueda.
- **`ogr_slip2d/analysis_runner.py`:**
  - `run_configured_optimization` (el Optimize Surfaces del menú, cuyo resultado la ventana guarda en lugar del
    crítico) la llama sobre su resultado;
  - `evaluate_surfaces` la llama sobre los suyos, para los scripts. El API ya calculaba sobre una copia.
- **`tests/test_result_materials_v1387.py`**, nuevo: 10 tests.
- El número, en los nueve sitios, y el contador de los dos README.

**El coste, medido** sobre el caso 001 con su rejilla de 5292 círculos y Bishop, en el proceso: 58,6 ms para 120 350
dovelas, un +0,75 % sobre una corrida de 7,8 s. Si no hay nada que cambiar (un resultado del pool), recorrerlas cuesta
33 ms.

## 2. Qué se probó

- **`tests/test_result_materials_v1387.py`:**
  - ninguna dovela apunta a un material del proyecto, en cada puerta: la corrida de una búsqueda (sus evaluaciones,
    las del usuario y la optimizada), `run_analysis`, `run_configured_optimization` y `evaluate_surfaces`;
  - lo que enseña el resultado no se mueve, bit a bit (filas y fuerzas entre dovelas), tras una edición en el sitio
    ni tras una restauración como la de Deshacer;
  - la copia es igual al material de la corrida, con su `id`, y es una sola por material;
  - un material ajeno se deja como está;
  - ningún número se mueve: las evaluaciones son las mismas con las copias y con la función sustituida por una que no
    hace nada.

  Ninguno pasa de 0,35 s.
- **Siete mutantes** del arreglo, cada uno cazado:
  - las tres llamadas, quitadas una a una;
  - las superficies del usuario fuera;
  - una copia superficial en vez de profunda;
  - una copia por dovela;
  - los materiales ajenos sustituidos también.
- **Los dos tests que comparan por identidad el material de una dovela** (`test_generalized_child_water_v1247`,
  `test_material_domain_v1143`) llaman a `slice_surface` directamente, sin pasar por `run`, y no les afecta.
- **El banco:** la huella de los 23 casos frente a 0.1.377: 23 de 23 idénticos (`all identical`, código 0).
- **La suite entera con `--jobs 4`:** **6830 de 6830, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 28 min. La serie
  no se repite: la versión no toca lo paralelo, y la última en verde es la de 0.1.386, de anoche.

## 3. Lo que queda

- **D381 en el banco:** en `ERRORES_Y_DISCREPANCIAS.md` pasa a resuelta en esta versión. Falta su cierre formal (la
  instantánea, el índice de cerrados, `CIERRE`, la comprobación y los prompts), como en D380.
- **V9–V18,** cada una con su OK. La siguiente es V9: la anisotropía, con la caché de `_child_model` sin importaciones
  ni etiqueta.

## Archivos

- `ogr_slip2d/search.py`
- `ogr_slip2d/analysis_runner.py`
- `tests/test_result_materials_v1387.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.387.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)

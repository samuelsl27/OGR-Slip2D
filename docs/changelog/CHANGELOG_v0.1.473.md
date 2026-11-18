# OGR Slip2D v0.1.473

**Un solo núcleo: OGR Slip2D adopta `ogr-core` 0.2.0.** Este repositorio deja de llevar su copia de `ogr_core`
y su paquete `ogr_fem2d`. El programa depende de `ogr-core` en la versión que fija `pyproject.toml`:
`ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.2.0`. Ese núcleo es el de este repositorio en `d48e2b3`
(v0.1.471), con la malla y la filtración en `ogr_core.fem`. **Desde esta versión, su código solo se cambia en
OGR-Core.** El runner de tests también pasa a ser el de OGR-Core: `tests/_runner.py` es ahora un envoltorio que le
dice lo de este repositorio.

**Ningún número cambia**: el código del núcleo es el mismo, solo cambia de sitio. Es la fase 2 de la spec 010
(`spec/features/010-adoptar-ogr-core/`), rama `dev/adoptar-ogr-core`; la fase 1 fue la v0.1.472.

Decisiones de la propietaria (2026-11-18):
- **F1 no se fusiona.** F1 es el commit `2d68c29` de la rama `dev/extraer-ogr-core`, que no se toca. Sus cambios en
  tests se reprodujeron aquí y se compararon con el ensayo.
- **Fuera `pyclipper` y el extra `[fem]`**, que nadie importa. `ezdxf`, `h5py` y `reportlab` se quedan porque los
  importan los tests.
- **El `.venv` se crea primero** y la versión se prueba con él. Antes de borrar `ogr_core/`, la propietaria cerró
  Claude Desktop.
- **Las dos presas que usan seis tests**, copiadas a `tests/_dam_models.py`.
- **El censo de capas del núcleo entero** lo lleva OGR-Core: una sola lista.

## 0. Lo que se encontró

### Al hacer el censo (fase 0, `censo.md` de la spec)

- **Los 39 tests que ya viven en OGR-Core** se compararon uno a uno. 17 eran iguales byte a byte, 6 solo diferían en
  el fin de línea y 15 solo en las importaciones. El último, `test_child_model_v1388`, lleva en OGR-Core el arreglo de
  su intermitencia y nada más.
- **Seis tests que se quedan cargaban por ruta dos de los que salían**: `test_unsaturated_v127` (la presa
  rectangular) y `test_rescue_face_v1356` (la presa con dren de pie). La spec 009 solo miró la dirección contraria,
  y el ensayo no lo vio porque no quitó los tests.
- **Un invariante del runner compartido no tiene test en OGR-Core**: «un test `async` falla en vez de pasar vacío».
  Se queda aquí, contra el runner compartido, y se pedirá para la v0.2.1 del núcleo.
- **`pyclipper` estaba declarado y no lo importaba nadie**; el extra `[fem]` (`scikit-fem`, `meshpy`), tampoco.
- **El ensayo no veía todo el banco**: tres `construir_modelo.py` vivos del banco 02 y
  `elegibilidad_critica_d155.py` también nombran `ogr_fem2d`. Van en la fase del banco.

### Al hacerlo

- **`pip install -e ".[mcp]"` habría reinstalado `ogr-core` desde GitHub encima del editable.** El `--dry-run` decía
  `Would install ogr-core-0.2.0`. Slip2D se instaló con `--no-deps`, con todo lo demás ya fijado, y `pip check` dio
  limpio. `AGENTS.md` lo dice: el núcleo en editable va después, y `.[mcp]` no se repite sin `--no-deps`.
- **El censo de capas de este repositorio, leyendo el núcleo instalado, encontró algo que la copia no tenía**:
  `ogr_core/testing/runner.py` hace `import importlib` a nivel de módulo. OGR-Core ya lo tiene en la lista permitida
  de su propio censo (`test_core_layering_v10`, con su porqué: el runner carga los tests por ruta).
  - Había dos censos del núcleo entero, y ya decían cosas distintas.
  - Por decisión de la propietaria, el de aquí sale, y la lista vive en un solo sitio.
  - En `test_core_layering_v1340` se quedan `census_of` (lo usan otros cinco tests), su autocomprobación, «ve el
    núcleo entero» y lo que movió cada versión.
- **Con el núcleo apuntando a una carpeta vacía fallan 30 tests en 22 archivos** (`OGR_TEST_CORE_ROOT`, el diente de
  `tests/_sources.py`). Son los mismos 30 que el ensayo vio fallar al quitar la carpeta. Ningún censo pasa ya
  buscando en vacío; antes `test_core_layering_v1340` y `test_settings_coverage_v1103` lo habrían hecho.
- **La herramienta y F1 importan los datos de la filtración desde sitios distintos.** La herramienta usa
  `ogr_core.fem.seepage`; F1, `ogr_core.fem`. Son los mismos objetos (comprobado con `is`). Es la única diferencia del
  programa con la rama `trial` del ensayo, aparte de lo que esta versión añade a propósito.
- **Una anomalía anterior, anotada y no corregida:** `test_no_vendor_names_v1160` nunca ha recorrido `ogr_api` ni
  `ogr_mcp`; su lista de árboles es de antes de que existieran. Esta versión solo le quita `ogr_core` y `ogr_fem2d`.
- **Errores propios, por si se repiten:**
  - Escribí en `/tmp` desde Git Bash y lo leí con el Python de Windows, que no ve ese `/tmp`; no se escribió nada.
  - Las barras invertidas de un patrón llegaron recortadas a través de la herramienta Bash, la trampa ya conocida;
    se buscó por anclas sin barras.
  - Un `grep` de cargadores dio falsos positivos con mi propia nota de cabecera, que empieza una línea por «from».
  - Un `git rm` se negó a borrar archivos modificados por la reescritura, sin borrar nada.
  - **Un diente de mi test de la v0.1.472 dependía del entorno.** El caso «el `pythonw.exe` base sin lanzador»
    esperaba «un trabajador está fuera del venv». En el `.venv` el pool muere: fuera de él, el hijo ni siquiera
    puede cargar el núcleo, que solo existe dentro. Lo cazaba igual, pero el test aceptaba solo una de las dos
    formas.
    - Por decisión de la propietaria acepta las dos, y el script hijo apunta qué ejecutable y qué variable usó
      el contexto para cada trabajador, así que cada diente comprueba que hizo lo que dice.
    - Un caso nuevo comprueba lo mismo del programa: el base y el lanzador.
    - Los ocho mutantes de la v0.1.472, otra vez en el `.venv`: mueren los ocho. El M4 lo caza además el
      detector de fugas (`env:__PYVENV_LAUNCHER__`).
- **Los tests de las presas, más baratos.** Antes cargaban `test_unsaturated_v127` o `test_rescue_face_v1356`
  ejecutando el archivo cada vez, y cada carga construía su malla y su caso. Ahora importan `_dam_models` una vez
  y comparten su caché. En la misma corrida `--jobs 4`, `test_rescue_fold_v1362` pasa de 586 s a 234 y
  `test_picard_loop_face_v1358` de 115 a 65. Los valores y las tolerancias no cambian.

## 1. El cambio

- **`pyproject.toml`:** `ogr-core @ git+…@v0.2.0`, sin `pyclipper` y sin el extra `[fem]`.
- **Fuera `ogr_core/` y `ogr_fem2d/`.**
- **Importaciones:** con `reescribir_imports.py`, 225 sentencias en 57 archivos. `test_fem_data_in_core_v1342` es la
  versión de F1 («una clase en una ruta», «no hay `ogr_fem2d` en este árbol»). Ninguna línea importa `ogr_fem2d`.
- **Docstrings del programa** que nombraban `ogr_fem2d`, con el texto de F1: `ogr_api/__init__.py`,
  `ogr_slip2d/run_messages.py`, `ogr_slip2d/transient_stability.py` y `ogr_gui/dialogs/boundary_conditions_dialog.py`.
- **`tests/_runner.py`**, el envoltorio del ensayo:
  - los cinco paquetes propios, y `ogr_core` compartido y fijado;
  - los dos ganchos de Qt y las dos carpetas de la corrida;
  - las diez entradas de la lista blanca que son de este programa;
  - `label="ogr-slip2d"` y `serial_every=100`.
- **`tests/_leaks.py`** es un puente a `ogr_core.testing.leaks`.
- ***Acerca de*** da la versión del núcleo (fila «Core» / «Núcleo», con su `tr()` y su español).
- **Versión en siete sitios**, más la comprobación de que el `ogr_core` importado es el fijado.
- **Documentos:**
  - `AGENTS.md`: dónde vive el núcleo, capas, la regla nueva, los siete sitios, los comandos con el `.venv` y la
    instalación;
  - `CONTRIBUTING.md`, `README.md`, `README.es.md`, `docs/architecture.md`, `docs/quickstart.md`, `docs/plugins.md`,
    `spec/constitution/tech-stack.md` y `.claude/commands/release.md`;
  - el comentario de la CI.

## 2. Los tests

### Los que salen, y dónde siguen

| Salen | Siguen en |
|---|---|
| Los 39 de `censo.md` §1 | OGR-Core, con el mismo nombre |
| `test_runner_exit_v1203`, `_selection_v180`, `_provenance_v189`, `_state_v1373`, `_jobs_v1375`, `_fast_v1376`, `_shutdown_v1377`, `test_leaks_v1374` | OGR-Core (`test_runner_*_v10`, `*_v020`, `test_leaks_v020`) lo genérico; `test_runner_wrapper_v1473` lo de este repositorio |
| Un caso de `test_gc_guard_v1302` y uno de `test_rules_moved_v1194` | `test_runner_wrapper_v1473` |
| El censo del núcleo entero de `test_core_layering_v1340` | OGR-Core, `test_core_layering_v10` |

### Nuevos

- **`test_runner_wrapper_v1473`** (26 casos). Lo que este repositorio dice al runner compartido:
  - los cinco paquetes propios, el núcleo compartido, sin las dos copias, y el fijado es el importado;
  - sin fijar, el envoltorio sale con 2;
  - la suite real, los tres archivos de reloj, `_slow.txt`;
  - el 100 y `release.md`, y los archivos de máquina;
  - las dos carpetas de la corrida;
  - las diez entradas y sus reglas;
  - la fuga del idioma;
  - los dos ganchos de Qt;
  - un test `async` falla.
- **`test_sources_v1473`** (7 casos): un censo no puede pasar sin encontrar nada.
- **`tests/_sources.py`** y **`tests/_dam_models.py`** son módulos auxiliares; el runner no los recoge.
  `_dam_models` es copia exacta de su origen: 16 definiciones comparadas una a una por su árbol sintáctico.

### Cambiados, con su nota de cabecera

- **Leen el núcleo instalado vía `_sources`:**
  - `test_api_layering_pyexec_v1194`, `test_core_layering_v1340`, `test_dxf_drawings_v1341`;
  - `test_dxf_export_census_v1354`, `test_dxf_messages_v1334`, `test_edit_messages_v1434`;
  - `test_fem_data_in_core_v1342`, `test_focus_circle_in_core_v1343`, `test_import_messages_v1437`;
  - `test_local_c_phi_in_core_v1345`, `test_model_notes_v1347`, `test_ogr_open_refusals_v1438`;
  - `test_overburden_in_core_v1344`, `test_png_annotations_v1338`, `test_seepage_run_notes_v1352`;
  - `test_setting_refusals_v1350`, `test_settings_coverage_v1103`, `test_stat_notes_v1353`;
  - `test_strength_refusals_v1351`, `test_window_undo_v1301`, `test_tensile_tolerance_retired_v1192`;
  - `test_results_query_user_surfaces_v1442`.
- **Las presas de `_dam_models`:**
  - `test_picard_history_v1269`, `test_transient_initial_state_v1270`;
  - `test_user_curve_dialog_v1275`, `test_retention_alpha_v1278`;
  - `test_picard_loop_face_v1358`, `test_rescue_fold_v1362`.
- **Otros:**
  - `test_project_settings_wiring_v174` carga otros tests con el cargador del runner compartido;
  - `test_version_consistency_v176`: siete sitios y el núcleo fijado;
  - `test_minor_menus_m5_v156`: *Acerca de* da la versión del núcleo, en inglés y en castellano;
  - `test_no_vendor_names_v1160`, `test_agent_scaffolding_v158`: sin las dos carpetas.

## 3. Verificación

**El entorno:** `.venv` con Python 3.14.7.
- Los 95 paquetes de las medidas de partida (`requisitos_fijados.txt`), comprobados con `pip freeze`.
- `ogr-core` 0.2.0 en editable desde OGR-Core (`3f4051c`, que es la etiqueta) y Slip2D en editable con
  `--no-deps`. `pip check` limpio.
- El banner del runner dice: `shared: ogr_core 0.2.0 C:\Samuel\OGR_Suite\Core\OGR-Core\ogr_core @ 3f4051c`.

**La suite entera, `--jobs 4`, en el `.venv`**, comparada test a test con la de partida (`d48e2b3`, Python del
sistema) mediante `comparar_suites.py`:

| | Casos | Pasan | Fallan | Saltados |
|---|---|---|---|---|
| Partida, `d48e2b3` | 8046 | 8044 | 0 | 2 |
| Primera corrida | 7530 | 7526 | 2 | 2 |
| Segunda, tras los dos arreglos | **7531** | **7529** | **0** | 2 |

En la segunda:
- **7474 tests dan el mismo resultado y ninguno cambia.**
- **Faltan 572, todos explicados:**
  - 442 de los 39 archivos que pasaron a OGR-Core;
  - 125 de los 8 archivos del runner y las fugas;
  - el censo del núcleo entero de `test_core_layering_v1340`;
  - los dos de «una clase en las dos rutas» de `test_fem_data_in_core_v1342`, sustituidos por los tres de F1;
  - un caso de `test_gc_guard_v1302`, rehecho;
  - uno de `test_rules_moved_v1194`, que pasó a `test_runner_wrapper_v1473`.
- **Sobran 57, todos nuevos y en verde.**
- Ninguna fuga, ningún tramo muerto.
- 8046 − 572 + 57 = 7531.

Los dos fallos de la primera corrida:
- `_slow.txt` aún nombraba tres archivos que pasaron a OGR-Core;
- el diente del test de los pools (§0).

**`tests/_slow.txt`**, reescrito con `--write-slow-list` (45 s) tras la primera corrida: 23 archivos, antes 37.
- **Salen:**
  - los tres que pasaron a OGR-Core (`test_picard_steep_curve_v1266`, `test_rescue_face_v1356`,
    `test_transient_face_rule_v1274`);
  - y además `test_dialogs_fit_v1315`, `test_face_tie_search_v1136`, `test_fos_chart_v1308`,
    `test_janbu_wedge_v1142`, `test_names_and_headings_v1369`, `test_noncircular_v115`,
    `test_probabilistic_v135`, `test_remote_oauth_v1204`, `test_retention_alpha_v1278`,
    `test_search_inequality_v1118`, `test_statistics_gui_v138`, `test_transient_coupling_v1125`,
    `test_transient_initial_result_v1307` y `test_transient_v130`.
- **Entran:** `test_discrete_function_v1246`, `test_interpret_v112` y `test_points_table_v1371`.
- **Fueron 419 de los 7531 tests**, 37,5 de los 89,1 min medidos.
- **Por qué cambia tanto:** las duraciones son de una corrida en cuatro tramos, con la máquina compartida. Las
  presas se comparten ahora (§0). La lista anterior era de la v0.1.397.

**Con el núcleo apuntando a una carpeta vacía** (`OGR_TEST_CORE_ROOT`) fallan los 22 archivos que leen el núcleo
(30 tests).

**Mutantes:** los ocho de la v0.1.472, en el `.venv`; mueren los ocho.

**El programa**, comparado con la rama `trial` del ensayo:
- solo difiere en lo que esta versión añade a propósito (*Acerca de*, docstrings, la v0.1.472);
- y en de dónde importan tres archivos los datos de la filtración, que son los mismos objetos.

`git diff d48e2b3 -- tests/test_slide_validation_* tests/test_acads_* validacion/`: vacío.

### La huella del banco de cómputo (fase 5 de la spec)

El banco se puso al día en la fase 4 (fuera de git, con el diff aprobado):
- **las rutas de `OGR_Suite`** en `comun.py`, `_tools/banco.py`, `LEEME.md` y el manifiesto;
- **las importaciones a `ogr_core.fem`** en `casos.py` y en los cinco `construir_modelo.py` que importaban
  `ogr_fem2d` (004 y 015 del 05; 010, 038 y 102 del 02);
- **el `pytest` simulado:** `casos.py` lo obtenía cargando `tests/_runner.py`, y el runner compartido ya no lo
  instala al importarse; ahora `casos.py` llama a `install_pytest_shim()`;
- **la procedencia** dice qué núcleo se midió (`ogr_core_version`, `ogr_core_fem_file`, `ogr_fem2d_importable`);
- **los nueve interruptores de `elegibilidad_critica_d155.py`** quedan en «ruta nueva,ruta vieja», el convenio de
  0.1.344.

Cada archivo conserva su fin de línea. El manifiesto conserva los 23 hashes de referencia: 19 iguales y 4 cambios
aceptados con su motivo (los tres de esta versión y el de D388).

**El lote `version`**, con el intérprete del `.venv` y ningún otro proceso del banco a la vez:
- **Los trabajos:** los 23 salen con código 0 y ningún fallo; ninguna entrada cambia durante el lote.
- **La comparación:** frente a `antes/huella_d48e2b3` (`comparar_huellas.py`, con el `comparar.py` del banco), **23
  de 23 casos idénticos bit a bit** y ninguna clave sin pareja.
- **La procedencia, en las 23:**
  - Slip2D 0.1.473 de este árbol y `ogr_core` 0.2.0 de OGR-Core (`…\OGR-Core\ogr_core`), con la filtración en
    `ogr_core\fem\seepage.py` y `ogr_fem2d` no importable;
  - el intérprete del `.venv`, con Python 3.14.7, numpy 2.5.1, scipy 1.18.0 y shapely 2.1.2, los mismos que la de
    partida (que midió 0.1.471 con la copia del núcleo dentro de Slip2D);
  - los hijos de los pools con el `pythonw.exe` del Python base: la v0.1.472 en uso.
- **Los ocho casos que abren pool**, que en el ensayo dentro de un venv llevaban la nota del pool caído, salen
  idénticos.

### La suite en serie

Sin argumentos, en el `.venv`: **7531 casos, 7529 pasan, 0 fallan, 2 saltados, ninguna fuga**. Queda registrada como
serie en verde en `07524e8`. Comparada test a test con la corrida `--jobs 4`, todos dan lo mismo. Cinco nombres
salen «distintos» solo porque en el registro en serie un aviso de `stderr` se cuela a media línea: pega texto al
nombre de un test o se come el encabezado de una clase. Los cinco son ✓ en las líneas crudas.

### El arranque

Con el `.venv`:
- `python -m ogr_cli --help` y `python -m ogr_mcp --help` salen con código 0, y también sus ejecutables
  `ogr-slip2d-cli` y `ogr-slip2d-mcp`;
- `python -m ogr_gui`, fuera de pantalla y con carpetas de ajustes y de puente propias, seguía abierta y sin
  errores a los 15 s.

## 4. Lo que queda

- **La CI**, en el primer push que autorice la propietaria. Instalará `ogr-core` desde la etiqueta, algo que aquí no
  se ha probado: aquí el núcleo va en editable.
- **Slip2D en el Python del sistema, el servidor MCP y los accesos directos:** a decidir por la propietaria. Hasta
  entonces no arrancan desde el Python del sistema.
- **OGR-Core, para su v0.2.1:** pedir el test de «un test `async` falla».
- **`test_no_vendor_names_v1160`:** nunca ha recorrido `ogr_api` ni `ogr_mcp`. Es una anomalía anterior, anotada.

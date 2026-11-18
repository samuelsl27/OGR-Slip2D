# Censo de la adopción (fase 0)

> Hecho el 2026-11-18 sobre `d48e2b3` (v0.1.471) y `ogr-core` v0.2.0 (`3f4051c`, que es la
> etiqueta y el HEAD de OGR-Core, árbol limpio). Solo lectura: `cmp`, `ast`,
> `reescribir_imports.py --dry` y `grep` acotado. Si `main` avanza antes de la v0.1.473, se repite.

## 1. Los 39 tests que ya viven en OGR-Core

Los 34 de la v0.1.0 (censo 009 §3) más `test_child_model_v1388`, `test_strength_reader_v1391`,
`test_published_fluxes_v1392`, `test_seepage_element_cache_v1393` y
`test_transient_system_reuse_v1394`. Comparados con `OGR-Core/tests/` uno a uno: bytes, bytes sin
`\r`, y árbol sintáctico (docstrings incluidos) quitando las sentencias que importan de `ogr_fem2d`
u `ogr_core.fem`, y comprobando que importan los mismos nombres.

| Resultado | Cuántos | Archivos (`test_…`) |
|---|---|---|
| Idénticos byte a byte | 17 | `assignment_independence_v116`, `command_api_regression`, `degenerate_boundary_v189`, `drawdown_envelopes_v167`, `dxf_reader_v144`, `dxf_sanitiser_v145`, `geometry`, `loads`, `p1_dangling_v112`, `p1_tjunction_v113`, `project`, `region_subdivision_v115`, `regions`, `statistics_v133`, `strength_reader_v1391`, `transforms`, `units_v113` |
| Solo el fin de línea | 6 | `expand_shrink`, `material_inheritance_v114`, `materials`, `region_welding_v117`, `strength_v112`, `surface_options_v112` (aquí el árbol de trabajo está en CRLF; el índice, en LF) |
| Solo las importaciones, mismos nombres | 15 | `face_bands_v1284`, `mesh_flat_triangles_v1271`, `no_convergence_advice_v1273`, `picard_steep_curve_v1266`, `picard_tolerance_v1272`, `published_fluxes_v1392`, `rescue_face_v1356`, `seepage_element_cache_v1393`, `simple_convention_v1267`, `switch_budget_v1283`, `transient_carried_state_v1282`, `transient_celia_v1268`, `transient_face_rule_v1274`, `transient_system_reuse_v1394`, `unsaturated_v127` |
| El arreglo anunciado de su intermitencia, y nada más | 1 | `child_model_v1388`: OGR-Core guarda vivos los modelos devueltos durante la secuencia (`_answer(call, alive)`); ningún valor esperado cambia (CHANGELOG 0.2.0 de OGR-Core, §0) |

**38 son el mismo test, y el 39.º lleva solo el arreglo.** Salen de aquí en la v0.1.473.

**Pero dos de ellos los cargan por ruta seis tests que se quedan** (hallazgo de este censo; el de la
spec 009 solo miró la dirección contraria, qué cargaban los que se iban):

| Test que se queda | Carga | Toma |
|---|---|---|
| `test_picard_history_v1269` | `test_unsaturated_v127` | `_dam_mesh`, `_dam_bcs`, `K_DAM` |
| `test_transient_initial_state_v1270` | `test_unsaturated_v127` | `_dam_mesh`, `_dam_bcs`, `K_DAM` |
| `test_user_curve_dialog_v1275` | `test_unsaturated_v127` | `_dam_mesh`, `_dam_bcs` |
| `test_retention_alpha_v1278` | `test_unsaturated_v127` | `_dam_mesh`, `_dam_bcs`, `K_DAM` |
| `test_picard_loop_face_v1358` | `test_rescue_face_v1356` (3 veces), `test_unsaturated_v127` | `_case`, `_dam_project`, `RESERVOIR`, `W`, `TOL`; la presa |
| `test_rescue_fold_v1362` | `test_unsaturated_v127` | la presa |

Las demás menciones de los 39 en tests que se quedan son comentarios o docstrings
(`transform_tools_v1415`, `picard_loop_face_v1358` l. 78, `statistics_v145`,
`retention_dialog_v1268`, `groundwater_ops_v1200`, `initial_steady_v1281`).

Opciones, a decidir en el plan de la v0.1.473:

- **(a, recomendada)** Las fábricas que se usan (`_dam_mesh`, `_dam_bcs`, `K_DAM`, y lo que toman de
  `test_rescue_face_v1356`) pasan, copiadas sin cambiar, a un módulo auxiliar de esta suite
  (`tests/_dam_models.py`, que el runner no recoge), y los seis lo importan; los dos tests salen.
  Se duplica código de construcción de modelos, no tests.
- **(b)** `test_unsaturated_v127` y `test_rescue_face_v1356` se quedan también aquí: el mismo test
  corre en las dos suites.

## 2. Importaciones de `ogr_fem2d`

`grep` da 229 líneas en 59 archivos; uno es `ogr_fem2d/solvers/seepage.py`, que se borra. Quedan
**58 archivos**: seis del programa (`ogr_gui/core_messages.py`,
`ogr_gui/dialogs/boundary_conditions_dialog.py`, `ogr_gui/interpret_window.py`,
`ogr_gui/main_window.py`, `ogr_api/ops/groundwater.py`, `ogr_slip2d/transient_stability.py`) y el
resto tests (de ellos, algunos de los 39 que salen).

`reescribir_imports.py --dry .` reescribe **226 sentencias** y deja dos «PROBLEMA»:
`import ogr_fem2d.mesh` e `import ogr_fem2d.solvers` en `test_fem_data_in_core_v1342` (l. 63 y 65),
que son los de «una clase en las dos rutas», la invariante que F1 retiró. Hay que lanzarla con
`-X utf8`: con `-I`, Python ignora `PYTHONIOENCODING` y la salida revienta al imprimir `→`.

**62 menciones** que no son `import`, a mano. Regla: `ogr_fem2d` como **nombre prohibido** al
núcleo se queda (es el programa 03); como **carpeta de este repositorio**, sale.

| Dónde | Menciones |
|---|---|
| Programa (docstrings) | `ogr_api/__init__.py` (1), `ogr_slip2d/run_messages.py` (1), `ogr_slip2d/transient_stability.py` (2), `ogr_gui/dialogs/boundary_conditions_dialog.py` (2) |
| En las carpetas que se borran | `ogr_core/fem/{__init__,mesh,seepage_data}.py`, `hydraulic/ponded_water.py`, `project/project.py`, `ogr_fem2d/…` (10): nada que hacer |
| Tests | `_runner.py`, `agent_scaffolding_v158`, `api_layering_pyexec_v1194` (3), `core_layering_closed_v1346` (2), `core_layering_v1340` (5), `dxf_drawings_v1341` (2), `fea_ponding_v165` (2), `fem_data_in_core_v1342` (12), `focus_circle_in_core_v1343`, `import_messages_v1437` (2), `interpret_water_layers_v1332`, `local_c_phi_in_core_v1345`, `no_vendor_names_v1160`, `overburden_in_core_v1344` (2), `results_query_user_surfaces_v1442`, `runner_provenance_v189` (2), `seepage_note_codes_v1364`, `seepage_run_notes_v1352` (2), `settings_coverage_v1103`, `streamlines_v1332`, `tensile_tolerance_retired_v1192`, `version_consistency_v176` |

Ningún `.ogr`, `examples/` ni `validacion/` nombra `ogr_fem2d`, y el único pickle (`ogr_api/jobs`)
vive dentro de una ejecución (censo 009 §6).

## 3. Tests que leen fuentes del núcleo por ruta

**30 tests en 22 archivos fallan** sin la carpeta (los mismos que el ensayo), y **seis archivos más
no fallan pero pasarían en vacío** o dejarían de mirar el núcleo. FNF = `FileNotFoundError`;
«vacío» = el recorrido no encuentra nada y no lo comprueba.

Arreglo común: `tests/_sources.py` (nuevo; el runner no recoge archivos con `_`):
`core_root()` = `Path(ogr_core.__file__).parent.parent`; `source(rel)` resuelve `"ogr_core/…"`
contra el núcleo instalado y lo demás contra el repositorio; `package_files(pkg)` falla si no
encuentra nada. Las claves de los censos siguen siendo `"ogr_core/…"`: ninguna tabla esperada
cambia salvo `ogr_fem2d/…` → `ogr_core/fem/…`. `census_of(path, root)` de
`test_core_layering_v1340` (lo importan 1341, 1342, 1343, 1344 y 1345) recibe `core_root()` para los
archivos del núcleo (con `_ROOT` daría `ValueError`).

| Archivo (`test_…`) | Lee del núcleo | Sin la carpeta | Qué cambia |
|---|---|---|---|
| `api_layering_pyexec_v1194` | todo `ogr_core` y `ogr_fem2d` (l. 60); `project/rules.py` (l. 66) | vacío / FNF | `package_files`; fuera `ogr_fem2d` de la lista de carpetas; el conjunto prohibido (l. 67-68) se queda |
| `core_layering_v1340` | todo `ogr_core` (l. 88); `project/results_io.py` (l. 138) | **vacío**: `ALLOWED` es un `Counter` vacío y un censo vacío lo iguala / FNF | censo del núcleo instalado, y que vea más de 80 módulos |
| `core_layering_closed_v1346` | por importación (`walk_packages`) | ya afirma más de 80 módulos | solo docstring |
| `dxf_drawings_v1341` | `dxf/exporter.py` (l. 189) | FNF | `source()` |
| `dxf_export_census_v1354` | `dxf/exporter.py`, `dxf/annotation_export.py` (l. 191-219) | FNF | `source()` |
| `dxf_messages_v1334` | todo `ogr_core` (l. 237); `dxf/importer.py` (l. 260) | afirma ≥ 7 / FNF | `package_files`, `source()` |
| `edit_messages_v1434` | `project/commands.py` (l. 1279); `geometry/{slope_angle,cleanup,expand_shrink,transforms}.py`, `loads/seismic_record.py` (l. 1335-1351) | FNF | `source()` |
| `fem_data_in_core_v1342` | `project/project.py` (l. 164); importa `ogr_fem2d` (l. 63, 65, 150) | FNF / `ImportError` | como F1: «una clase en una ruta» y «no hay `ogr_fem2d` en este árbol»; `source()` |
| `focus_circle_in_core_v1343` | `project/project.py` (l. 143) | FNF | `source()` |
| `import_messages_v1437` | todo `ogr_core` y `ogr_fem2d` (`_PACKAGES`, l. 1077); `project/properties_import.py` (l. 1216) | afirma (núcleo), vacío (`ogr_fem2d`) / FNF | fuera `ogr_fem2d`; `package_files`, `source()` |
| `local_c_phi_in_core_v1345` | `materials/strength_model.py` (l. 178), `support/bond.py` (l. 247) | FNF | `source()` |
| `model_notes_v1347` | `project/rules.py` (l. 720) | FNF | `source()` |
| `ogr_open_refusals_v1438` | `project/project.py`, `project/settings.py` (l. 809-814) | FNF | `source()` |
| `overburden_in_core_v1344` | todo `ogr_core` y `ogr_fem2d` (l. 112); `hydraulic/excess_pore_pressure.py`, `support/bond.py` (l. 174-176) | afirma (núcleo), vacío (`ogr_fem2d`: sus interruptores desaparecerían sin decirlo) / FNF | `package_files`; los interruptores de la filtración se cuentan en `ogr_core/fem/` |
| `png_annotations_v1338` | `dxf/annotation_export.py` (l. 190-195) | FNF | `source()` |
| `seepage_run_notes_v1352` | `ogr_fem2d/solvers/seepage.py` (l. 462), `statistics/drawdown_sweep.py`, `materials/parameter_calculator.py` | FNF | `ogr_core/fem/seepage.py`; `source()` |
| `setting_refusals_v1350` | `project/rules.py`, `loads/loads.py` (l. 390-402) | FNF | `source()` |
| `settings_coverage_v1103` | todo `ogr_core` y `ogr_fem2d` (l. 38, 82) | **vacío**: deja de ver quién lee `optimize_enabled` y falla por la razón equivocada | fuera `ogr_fem2d`; el núcleo por `package_files` |
| `stat_notes_v1353` | `project/design_factors.py`, `materials/{strength_model,builtin_models}.py` (l. 851-882) | FNF | `source()` |
| `strength_refusals_v1351` | `project/rules.py`, `materials/builtin_models.py` (l. 725-744) | FNF | `source()` |
| `window_undo_v1301` | `project/commands.py` (l. 695) | FNF | `source()` |
| `version_consistency_v176` | `ogr_core/__init__.py`, `ogr_fem2d/__init__.py` (l. 30-32) | FNF | siete sitios; y el `ogr_core` que se importa es el fijado en `pyproject.toml` |
| `test_imports_v1372` | nombres de carpeta (l. 89) | marca cada `import ogr_core` como no declarado | pasa al declarar `ogr-core` (comprobar que su lector entiende `nombre @ git+…`) |
| **No fallan:** `no_vendor_names_v1160` (l. 55), `tensile_tolerance_retired_v1192` (l. 91) | todo `ogr_core` y `ogr_fem2d` | vacío | fuera las dos carpetas de la lista (OGR-Core tiene `test_no_vendor_names_v10`) |
| `results_query_user_surfaces_v1442` (l. 847) | los siete paquetes con `os.walk` | vacío | fuera `ogr_fem2d`; el núcleo por `package_files` |
| `license_v143`, `python_floor_v176` | todo `**/*.py` | dejan de ver el núcleo | nada: OGR-Core tiene `test_license_v10` y `test_python_floor_v10` |
| `agent_scaffolding_v158` (l. 66) | `AGENTS.md` | falla cuando `AGENTS.md` deje de nombrar `ogr_fem2d` | la lista pasa a los paquetes de verdad |

Diente de cada uno: con el árbol del núcleo apuntando a una carpeta vacía, o sin el archivo que
lee, tiene que fallar.

## 4. El runner y las fugas

`tests/_runner.py` pasa a ser el envoltorio (borrador en `ensayo/tests__runner.py.borrador`):
`OWN` (`ogr_slip2d`, `ogr_gui`, `ogr_cli`, `ogr_api`, `ogr_mcp`), `SHARED` (`ogr_core`) con la
versión de `pyproject.toml`, `Hooks` (`gc_guard.install`, `gc_guard.release`,
`_release_windows`), `run_folders` (`OGR_BRIDGE_DIR`, `OGR_SETTINGS_DIR`), `label="ogr-slip2d"`,
`serial_every=100` y las diez entradas de abajo. Sin `ogr-core` fijado en `pyproject.toml` sale
con 2. `tests/_leaks.py`, un puente (`sys.modules[__name__] = ogr_core.testing.leaks`): los cinco
archivos que importan `root_logging_kept` siguen igual.

**Lista blanca.** De las 24 entradas de `tests/_leaks.py`, 14 están en `leaks.ALLOWED` de OGR-Core
con la misma regla (más una suya, `mod:ogr_core.testing.leaks._DEFAULTS`). Las **diez del
programa**, que se quedan aquí: `mod:*.icon`, `mod:ogr_api.coerce._HINTS`,
`cls:ogr_gui.main_window.MainWindow._sessions`, `mod:ogr_gui.gc_guard._kept`,
`mod:ogr_gui.core_messages._CATALOGUE`, `mod:ogr_gui.wheel_guard._guard`,
`mod:ogr_gui.button_floor._floor`, `mod:ogr_gui.themes._ORIGINAL_PALETTE`, `mpl.rcParams`
(solo `backend_fallback`), `mp.executable` (regla `to_windowless`).

**Dónde queda cada invariante** de los tests que usaban lo de dentro de `tests/_runner.py`. El
envoltorio no reexporta nada del runner viejo: casi todos rompen (la firma de `main` cambia, las
constantes son ahora parámetros, un parche al envoltorio no llega al módulo compartido).

| Archivo de hoy (`test_…`) | Lo genérico, en OGR-Core | Lo que es de este repositorio y se queda |
|---|---|---|
| `runner_exit_v1203` | `test_runner_exit_v10` (los 8) | nada: sale |
| `runner_selection_v180` | `test_runner_selection_v10` | la suite real tiene más de 1000 tests |
| `runner_provenance_v189` | `test_runner_provenance_v10`, `test_runner_shared_v10` | los cinco propios resuelven dentro del repositorio; `ogr_core` fuera y fijado; no hay carpetas `ogr_core/` ni `ogr_fem2d/` |
| `runner_state_v1373` | `test_runner_state_v020` | las dos carpetas de la corrida son las de este repositorio |
| `runner_jobs_v1375` | `test_runner_jobs_v020` | los tres archivos de reloj llevan `SERIAL_LANE` (`jobs_file_race_v1198`, `optimizations_v111`, `remote_oauth_v1204`) |
| `runner_fast_v1376` | `test_runner_fast_v020` | `tests/_slow.txt` solo nombra archivos que existen; 100 aquí y en `AGENTS.md`; `.claude/commands/release.md` lee el aviso; los archivos de máquina se siguen llamando `ogr-slip2d-*` |
| `runner_shutdown_v1377` | `test_runner_shutdown_v020` | nada: sale |
| `leaks_v1374` | `test_leaks_v020` (las nueve reglas, la carpeta, el INI, la lista) | las diez entradas dicen su porqué y son de una clase válida; sus reglas (`wheel_guard` instalado, `_CATALOGUE` lleno una vez, `mpl.rcParams` solo `backend_fallback`, `to_windowless`); la fuga del idioma de `ogr_gui` hace fallar su archivo |
| `gc_guard_v1302` (1 de 6) | `test_runner_shared_v10` (ganchos), `test_runner_state_v020` | `HOOKS.before_run` instala el guardia y `before_file` lo vacía |
| `rules_moved_v1194` (1 de 9) | **ninguno** | «un test `async` falla en vez de pasar vacío», contra `ogr_core.testing.runner._run_method`; se pide a OGR-Core para la v0.2.1 |
| `project_settings_wiring_v174` (5) | — | solo cambia cómo carga otro test (`ogr_core.testing.runner._load_module`, mismo significado); valores intactos |
| `shutdown_release_v1422`, `api_layering_pyexec_v1194`, `bridge_version_v1300`, `live_bridge_v1203`, `mcp_server_v1195`, `ogr_open_refusals_v1438`, `window_by_default_v1207` | — | funcionan con el envoltorio y el puente sin cambios |

Lo que se queda va a `tests/test_runner_wrapper_v1473.py`, con esta tabla en su cabecera; los
archivos cuyo contenido está entero en OGR-Core salen. Cuidado al probar las entradas del programa:
`leaks.diff(antes, después)` usa por defecto solo la lista del núcleo; hay que pasarle
`leaks.ALLOWED + _runner.ALLOWED`.

## 5. Pools en un entorno virtual

Once tests en siete archivos comprueban que un pool corrió y fallan en un venv sin consola:
`console_language_demo_v1329` (1), `grid_cancel_v1372` (1), `left_soil_refusal_v1445` (1),
`pool_threshold_v1386` (1), `slice_store_parallel_v1409` (1), `slope_limit_refusals_v1261` (3),
`window_grid_parallel_v1262` (3). Ninguno cambia: los arregla la v0.1.472.

`ogr_slip2d/processes.child_executable` da hoy `dirname(sys.executable)/pythonw.exe`; en un venv
ese es el lanzador. `multiprocessing` (`popen_spawn_win32`) solo sabe tratar el lanzador que
coincide con `sys.executable`. El Python base de esta máquina
(`…\Python\pythoncore-3.14-64`) tiene `pythonw.exe`.

`test_report_pdf_v1417` falló en el ensayo por una carpeta temporal larga; `%TEMP%` de esta sesión
es el normal. `test_child_model_v1388` sale (§1).

## 6. El banco (fuera de git)

En `referencias/Ejemplos/RS2_Verification Manuals/`:

| Archivo | Qué tiene |
|---|---|
| `_auditoria/COMPUTO/bench/comun.py` | `REPO`, `BANK` con rutas de antes de `OGR_Suite`; la procedencia importa `ogr_fem2d` |
| `_auditoria/COMPUTO/bench/casos.py` | nueve sentencias que importan `ogr_fem2d` |
| `_auditoria/COMPUTO/bench/LEEME.md`, `datos/manifiesto.json` | rutas viejas |
| `_tools/banco.py` | `REPO_OGR` viejo |
| `05_…/05_Groundwater_Problema004/construir_modelo.py`, `…Problema015/…` | importan `ogr_fem2d` (K15 y K16 de la huella) |
| `02_…/02_Slide2_Problema010/construir_modelo.py` (l. 128, 129, 159), `…038/…` (l. 183, 184), `…102/…` (l. 135, 173, 183) | importan `ogr_fem2d` (Q3: entran) |
| `02_…/_tools/elegibilidad_critica_d155.py` | siete interruptores por su ruta `ogr_fem2d.solvers.seepage.*` y `ogr_fem2d.mesh.generator.*` (Q3: entra) |

Menciones que no se tocan: las copias de `Evaluaciones/<versión>/` (instantáneas de su versión) y
texto o listas en herramientas viejas del 02 (`_auditoria/D202_etapa1/verificar_cierres_0.1.211.py`,
`_tools/auditoria_omitidos.py`, `_tools/biseccion_arco_059.py`). El orquestador reescribe
`PYTHONPATH` en cada trabajo y cuenta como intruso cualquier proceso con `_runner.py`.

## 7. Anomalías del censo (regla 6)

1. `pyclipper` está declarado y nadie lo importa (programa, núcleo ni tests); el extra `[fem]`
   (`scikit-fem`, `meshpy`), tampoco. Decidido (Q2): fuera.
2. El ensayo no veía todo el banco: los tres scripts del 02 y `elegibilidad_critica_d155.py`.
   Decidido (Q3): entran.
3. «Un test `async` falla» no tiene test en OGR-Core (§4).
4. Seis tests que se quedan cargan por ruta dos de los que salen (§1).
5. Error propio al hacer este censo: un `grep` recursivo sobre `RS2_Verification Manuals` pasó de
   dos minutos y se paró. No corría ninguna suite.

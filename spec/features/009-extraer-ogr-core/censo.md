# Censo de la extracción (tareas 0.3 y 0.4)

> Hecho el 2026-10-27 sobre el árbol de v0.1.370 (`680837b` más los cambios de v0.1.370 aún sin
> confirmar). Leído del código con búsquedas y `ast`, sin ejecutar nada. Si v0.1.370 cambia algún
> test antes de confirmarse, se repite el recuento al empezar F1.

## 1. Nombres nuevos en `ogr_core/fem/` (propuesta para la tarea 1.1)

`ogr_core/fem/` ya tiene `mesh.py` (malla) y `seepage_data.py` (datos de filtración). Lo que llega:

| Hoy | Después de F1 |
|---|---|
| `ogr_fem2d/mesh/generator.py` (`generate_mesh`, `generate_mesh_for_project`, `discretize_edges`) | `ogr_core/fem/generator.py` |
| `ogr_fem2d/solvers/seepage.py` (solvers, `solve_project_seepage`, `TransientStage`, `free_surface_points`…) | `ogr_core/fem/seepage.py` |
| `ogr_fem2d/solvers/bc_targets.py` (`SIDE_LEFT`, `apply_reservoir`, `boundary_cycle`, `wetted_nodes`, `fits_mesh`…) | `ogr_core/fem/bc_targets.py` |
| `ogr_fem2d/solvers/streamlines.py` | `ogr_core/fem/streamlines.py` |
| `ogr_fem2d/messages.py` (códigos `seepage.*`) | `ogr_core/fem/messages.py` |
| `ogr_fem2d/mesh/mesh.py`, y los nombres de datos que reexportan `ogr_fem2d.mesh` y `ogr_fem2d.solvers` | ya están en `ogr_core.fem`: las importaciones apuntan ahí |
| `ogr_fem2d/elements/` (vacío: «planned v0.5.0») | se borra |

Dentro de los módulos que se mueven solo cambian dos importaciones: `seepage.py` pasa de
`from .. import messages as M` a `from . import messages as M`, y su importación diferida de
`ogr_fem2d.mesh.generate_mesh_for_project` (línea 434) pasa a `ogr_core.fem.generator`. Las demás
ya apuntan a `ogr_core`.

`ogr_core/fem/__init__.py` sigue exportando solo los datos. Los solvers se importan por su
submódulo (`from ogr_core.fem import seepage`, `from ogr_core.fem.generator import …`), para que
cargar un modelo no cargue el solver.

## 2. Importadores de `ogr_fem2d` que F1 reescribe

- **Programa (6)**: `ogr_gui/core_messages.py`, `ogr_gui/dialogs/boundary_conditions_dialog.py`,
  `ogr_gui/interpret_window.py`, `ogr_gui/main_window.py`, `ogr_api/ops/groundwater.py`,
  `ogr_slip2d/transient_stability.py`.
- **Tests (46)**: los que da `grep -lE "(from|import) ogr_fem2d" tests/*.py`. Ninguno de
  validación (`test_slide_validation_*`, `test_acads_*`) importa `ogr_fem2d`.
- Los datos guardados no nombran módulos: `.ogr` es JSON sin rutas de clase, y `examples/` y
  `validacion/` no contienen `ogr_fem2d`.

## 3. Tests que se mueven a OGR-Core en F2 (34)

Importan solo `ogr_core` (tras F1), y lo que toman de otros tests o leen por ruta también se
mueve:

`test_assignment_independence_v116`, `test_command_api_regression`,
`test_degenerate_boundary_v189`, `test_drawdown_envelopes_v167`, `test_dxf_reader_v144`,
`test_dxf_sanitiser_v145`, `test_expand_shrink`, `test_face_bands_v1284`, `test_geometry`,
`test_loads`, `test_material_inheritance_v114`, `test_materials`,
`test_mesh_flat_triangles_v1271`, `test_no_convergence_advice_v1273`, `test_p1_dangling_v112`,
`test_p1_tjunction_v113`, `test_picard_steep_curve_v1266`, `test_picard_tolerance_v1272`,
`test_project`, `test_region_subdivision_v115`, `test_region_welding_v117`, `test_regions`,
`test_rescue_face_v1356`, `test_simple_convention_v1267`, `test_statistics_v133`,
`test_strength_v112`, `test_surface_options_v112`, `test_switch_budget_v1283`, `test_transforms`,
`test_transient_carried_state_v1282`, `test_transient_celia_v1268`,
`test_transient_face_rule_v1274`, `test_units_v113`, `test_unsaturated_v127`.

**Corrección del censo** (2026-10-27, al preparar F2; regla 6): el primer recuento daba 36 porque
solo miraba sentencias `import`. Siete de estos tests cargan otro test **por ruta**
(`importlib.util.spec_from_file_location`). Cinco cargan tests que también se mueven
(`test_unsaturated_v127`, `test_picard_steep_curve_v1266`, `test_picard_tolerance_v1272`), y dos no
pueden irse:

- `test_face_flux_scale_v1359` carga `test_transient_coupling_v1125`, que importa `ogr_slip2d` y
  `ogr_gui`;
- `test_region_assignments` lee la fuente de `ogr_gui/canvas/tool_mode.py`.

Pasan a la tabla de abajo.

## 4. Tests del núcleo que se quedan en Slip2D (8)

| Test | Por qué se queda |
|---|---|
| `test_fem_data_in_core_v1342` | toma el modelo de `test_coupling_v128` (que importa `ogr_slip2d`) |
| `test_interpret_water_layers_v1332` | toma `_ej1_project` de `test_slide_validation_ej1` |
| `test_picard_history_v1269` | toma `_interpret` de `test_interpret_i3_v153` (que importa `ogr_gui`) |
| `test_seepage_v126` | toma `_ej1_project` de `test_slide_validation_ej1` |
| `test_streamlines_v1332` | importa `test_interpret_i3_v153` |
| `test_settings_coverage_v1103` | recorre también `ogr_slip2d` y `ogr_cli` |
| `test_face_flux_scale_v1359` | carga por ruta `test_transient_coupling_v1125` (que importa `ogr_slip2d` y `ogr_gui`) |
| `test_region_assignments` | lee la fuente de `ogr_gui/canvas/tool_mode.py` |

## 5. Los 24 tests que nombran rutas del núcleo

**Regla para F3**: un test que se queda en Slip2D y necesita leer las fuentes del núcleo las busca
en `Path(ogr_core.__file__).parent` (el árbol compartido que nombra el runner), **nunca** en
`_ROOT / "ogr_core"`, que tras F3 no existe. Y todo censo afirma que encontró algo, para que una
carpeta vacía no dé un verde falso.

| Test | Qué hace con la ruta | F1 | F3 |
|---|---|---|---|
| `test_agent_scaffolding_v158` | `AGENTS.md` nombra los paquetes | quitar `ogr_fem2d` | `ogr_core` sigue nombrado (como dependencia) |
| `test_api_layering_pyexec_v1194` | los motores no importan `ogr_api` | quitar `ogr_fem2d` | la parte del núcleo la cubre el test de capas de OGR-Core; queda `ogr_slip2d` |
| `test_core_layering_v1340` | censo de importaciones del núcleo | el solver movido no importa nada prohibido | **pasa a OGR-Core** (ya hay copias de licencia, nombres, suelo y CI); en Slip2D queda lo que comprueba que lo movido vive en `ogr_slip2d` |
| `test_core_layering_closed_v1346` | el núcleo no carga capas superiores en tiempo de ejecución | ídem | **pasa a OGR-Core**; necesita un modelo con malla y filtración construido sin Slip2D |
| `test_dxf_drawings_v1341` | lee `ogr_core/dxf/exporter.py`; usa `ogr_slip2d` | — | se queda; ruta vía `ogr_core.__file__` |
| `test_dxf_export_census_v1354` | lee `dxf/annotation_export.py`, `dxf/exporter.py`; usa `ogr_gui` | — | ídem |
| `test_dxf_messages_v1334` | lee `dxf/importer.py`; usa `ogr_gui` | — | ídem |
| `test_fem_data_in_core_v1342` | lee `project/project.py` | se reescribe (sin ruta antigua) | ruta vía `ogr_core.__file__` |
| `test_focus_circle_in_core_v1343` | lee `project/project.py`; usa `ogr_slip2d` | — | ídem |
| `test_license_v143` | todo `**/*.py` del repositorio | — | deja de ver el núcleo (OGR-Core tiene su copia) |
| `test_local_c_phi_in_core_v1345` | lee el árbol del núcleo; usa `ogr_slip2d` | — | ruta vía `ogr_core.__file__` |
| `test_model_notes_v1347` | lee `project/rules.py`; usa `ogr_gui` | — | ídem |
| `test_no_vendor_names_v1160` | recorre `_TREES` | quitar `ogr_fem2d` | quitar `ogr_core` (OGR-Core tiene su copia) |
| `test_overburden_in_core_v1344` | lee `loads/overburden.py` y otros; recorre motores | quitar `ogr_fem2d` | ruta vía `ogr_core.__file__` |
| `test_png_annotations_v1338` | lee `dxf/annotation_export.py`; usa `ogr_api` | — | ídem |
| `test_python_floor_v176` | todo `**/*.py` | — | deja de ver el núcleo (OGR-Core tiene su copia) |
| `test_runner_provenance_v189` | `PACKAGES` del runner | quitar `ogr_fem2d` | prueba la configuración del envoltorio (propios y compartidos); lo genérico ya está en OGR-Core |
| `test_seepage_run_notes_v1352` | lee `fem2d/solvers/seepage.py` y dos del núcleo; usa `ogr_gui` | ruta nueva `ogr_core/fem/seepage.py` | ruta vía `ogr_core.__file__` |
| `test_setting_refusals_v1350` | lee `loads/loads.py`, `project/rules.py`; usa `ogr_gui` | — | ídem |
| `test_settings_coverage_v1103` | recorre `ogr_core`, `ogr_slip2d`, `ogr_fem2d`, `ogr_cli` | quitar `ogr_fem2d` | el núcleo vía `ogr_core.__file__` |
| `test_stat_notes_v1353` | lee `materials/…`, `project/design_factors.py`; usa `ogr_gui` | — | ruta vía `ogr_core.__file__` |
| `test_strength_refusals_v1351` | lee `materials/builtin_models.py`, `project/rules.py`; usa `ogr_gui` | — | ídem |
| `test_tensile_tolerance_retired_v1192` | recorre paquetes | quitar `ogr_fem2d` | el núcleo vía `ogr_core.__file__` |
| `test_version_consistency_v176` | nueve sitios de versión | ocho | siete más la versión fijada del núcleo |
| `test_window_undo_v1301` | lee el árbol del núcleo; usa `ogr_gui` | — | ruta vía `ogr_core.__file__` |

## 6. Pickles (tarea 0.4)

- Solo `ogr_api/jobs` usa `pickle`: escribe `input.pkl` y `result.pkl` en una carpeta temporal
  `ogr_jobs_*` de cada sesión, y los lee el subproceso y el padre **de la misma instalación**.
  Ningún pickle sobrevive a una versión, así que el cambio de ruta de módulo de las clases movidas no
  rompe nada guardado.
- El `.ogr` es JSON y no guarda rutas de módulo ni nombres de clase de `ogr_fem2d`.

## 7. F1 preparada: script y ediciones a mano

**Script** (`f1_rewrite.py`, fuera del repositorio; probado en una copia del árbol): después de
mover los cinco módulos, reescribe **181 sentencias `from ogr_fem2d… import …` en 52 archivos**
(más la importación relativa del hallazgo de abajo)
partiendo cada una por el destino real de cada nombre (datos → `ogr_core.fem`, generador →
`ogr_core.fem.generator`, condiciones de contorno → `ogr_core.fem.bc_targets`, resto →
`ogr_core.fem.seepage`), y conserva los comentarios `# noqa`. El árbol resultante compila.

**Hallazgo al probarlo**: `ogr_fem2d/solvers/seepage.py` importa `from .. import messages as M`
(los códigos `seepage.*`). Movido a `ogr_core/fem/seepage.py`, esa misma línea apuntaría **en
silencio** a `ogr_core/messages.py`, que también existe: compilaría y fallaría al primer aviso del
solver. El script la cambia a `from . import messages as M`.

**Ediciones a mano** (las 64 líneas que el script lista, agrupadas):

| Dónde | Qué |
|---|---|
| `tests/_runner.py` | `PACKAGES` sin `ogr_fem2d` |
| `tests/test_version_consistency_v176.py` | sin `ogr_fem2d/__init__.py` (ocho sitios) |
| `test_agent_scaffolding_v158`, `test_api_layering_pyexec_v1194` (lista de motores), `test_no_vendor_names_v1160`, `test_overburden_in_core_v1344` (bucle de paquetes), `test_settings_coverage_v1103`, `test_tensile_tolerance_retired_v1192` | quitar `ogr_fem2d` de las listas de **carpetas de este repositorio** |
| `test_core_layering_v1340`, `_closed_v1346`, y las comprobaciones en subproceso de `test_dxf_drawings_v1341`, `test_focus_circle_in_core_v1343`, `test_local_c_phi_in_core_v1345`, `test_overburden_in_core_v1344`, `test_api_layering_pyexec_v1194` (importaciones de `rules.py`) | **se dejan**: `ogr_fem2d` sigue prohibido para el núcleo, ahora como nombre del programa 03 |
| `test_fem_data_in_core_v1342` | retirar «una clase en las dos rutas» (las cuatro `import ogr_fem2d… as`); la comprobación en subproceso pasa a exigir que cargar el modelo no traiga `ogr_core.fem.seepage` ni `ogr_core.fem.generator` |
| `test_seepage_run_notes_v1352` (línea 404) | la ruta `ogr_fem2d/solvers/seepage.py` pasa a `ogr_core/fem/seepage.py` |
| Docstrings y comentarios: `ogr_api/__init__.py`, `ogr_core/fem/{__init__,mesh,seepage_data,seepage}.py`, `ogr_core/hydraulic/ponded_water.py`, `ogr_core/project/project.py`, `ogr_gui/dialogs/boundary_conditions_dialog.py`, `ogr_slip2d/run_messages.py`, `ogr_slip2d/transient_stability.py`, y en tests `test_fea_ponding_v165`, `test_interpret_water_layers_v1332`, `test_seepage_note_codes_v1364`, `test_seepage_run_notes_v1352`, `test_streamlines_v1332` | la ruta nueva donde la vieja dejaría de ser verdad |
| `AGENTS.md`, `CONTRIBUTING.md`, `README.md`, `README.es.md`, `docs/architecture.md` | estructura sin `ogr_fem2d`; capas; ocho sitios de versión; el núcleo contiene el solver de filtración |

## 8. Lo que ya está adelantado en OGR-Core (2026-10-27)

`C:\Samuel\OpenGeoRock_Core\OGR-Core`, con el remoto `samuelsl27/OGR-Core` (público, vacío). Aún
**no tiene ningún commit**: el primero será la copia del código de F1 (decisión P5).

- Andamiaje: `pyproject.toml` (0.1.0, dependencias del censo), `LICENSE`, `CLA.md`,
  `CONTRIBUTORS.md`, README en inglés y castellano, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`,
  `.gitignore`, `.gitattributes`, CI (`tests.yml`) y `dependabot.yml`.
- Runner compartido `ogr_core/testing/runner.py` (P4), con paquetes propios y compartidos, versión
  fijada (`pinned_from_pyproject`) y ganchos para la interfaz (`Hooks`). Diferencia con el de
  Slip2D: el `pytest` simulado se instala al empezar `main()` y no al importar el módulo, para que
  importar un módulo del núcleo no toque `sys.modules`.
- Tests: los tres del runner de Slip2D portados (`selection`, `exit`, `provenance`), uno nuevo para
  los compartidos (`test_runner_shared_v10`) y copias de los de licencia, nombres de productos (que
  añade los dos productos de elementos finitos), suelo de Python y acciones de CI. **97 tests en
  verde.**
- `ogr_core/__init__.py` es provisional; lo sustituye el del commit de F1, conservando
  `__version__ = "0.1.0"`.

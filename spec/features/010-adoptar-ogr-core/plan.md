# Plan de implementación

## Enfoque

**Repetir lo ensayado, no reinventarlo**, en versiones que se puedan comprobar por separado, cada
una con su plan y el OK de la propietaria:

1. **v0.1.472** — los pools en un entorno virtual. Va primero porque condiciona todo lo que se mida
   en el `.venv`.
2. **v0.1.473** — la adopción: dependencia, fuera las dos copias, importaciones, tests, runner,
   versión, documentación, CI.
3. **Entorno** — `.venv` con las versiones de las medidas de partida.
4. **Banco** — ponerlo al día para que vuelva a correr (fuera de git).
5. **Verificación** — suite en `--jobs 4` y en serie, huella 23/23, arranque, CI.

Todo en la rama corta `dev/adoptar-ogr-core`. Commit, push, PR y fusión, solo cuando lo diga la
propietaria.

```
hoy:     [Slip2D] ogr_core ─► ogr_slip2d / ogr_fem2d ─► ogr_api ─► {ogr_gui, ogr_cli, ogr_mcp}
después: [OGR-Core 0.2.0] ogr_core (con fem) ─► [Slip2D] ogr_slip2d ─► ogr_api ─► {…}
```

## Archivos que se tocan

### v0.1.472

| Archivo | Qué cambia |
|---|---|
| `ogr_slip2d/processes.py` | `child_executable` / `windowless_children` en un venv (ver «Decisiones») |
| `tests/test_<area>_v1472.py` | el pool real dentro de un venv, con los dos dientes |
| `tests/_leaks.py` | si el diseño se confirma, una entrada para `__PYVENV_LAUNCHER__` |
| los nueve sitios de versión, `docs/changelog/CHANGELOG_v0.1.472.md` | versión |

### v0.1.473

| Archivo | Qué cambia |
|---|---|
| `pyproject.toml` | `ogr-core @ git+…@v0.2.0`; fuera `pyclipper` y `[fem]` |
| `ogr_core/`, `ogr_fem2d/` | se borran |
| 58 archivos (6 del programa, el resto tests) | importaciones de `ogr_fem2d` → `ogr_core.fem…` con `reescribir_imports.py`; las 62 menciones, a mano (`censo.md` §2) |
| 39 tests | salen (viven en OGR-Core; `censo.md` §1) |
| `tests/_runner.py`, `tests/_leaks.py` | envoltorio y puente (`censo.md` §4) |
| `tests/_sources.py` (nuevo) | dónde están las fuentes: el núcleo instalado o este repositorio; falla si no encuentra nada |
| 22 + 6 tests de `censo.md` §3 | leen el núcleo instalado vía `_sources.py` |
| tests del runner y las fugas (`censo.md` §4) | lo genérico sale; lo de este repositorio pasa a `tests/test_runner_wrapper_v1473.py` |
| `tests/test_version_consistency_v176.py` | siete sitios y la versión fijada del núcleo |
| `ogr_gui/dialogs/misc_dialogs.py` (`AboutDialog`), `ogr_gui/i18n/__init__.py` | la versión del núcleo, con su traducción |
| `ogr_api/__init__.py`, `ogr_slip2d/run_messages.py`, `ogr_slip2d/transient_stability.py`, `ogr_gui/dialogs/boundary_conditions_dialog.py` | docstrings que nombraban `ogr_fem2d` |
| `AGENTS.md`, `CONTRIBUTING.md`, `README.md`, `README.es.md`, `docs/architecture.md`, `docs/quickstart.md`, `docs/plugins.md`, `spec/constitution/tech-stack.md`, `.claude/commands/release.md` | dónde vive el núcleo; regla nueva; siete sitios; comandos con `.venv` |
| `.github/workflows/tests.yml` | comentario: el núcleo llega por la dependencia git |
| siete sitios de versión, `docs/changelog/CHANGELOG_v0.1.473.md` | versión y lo que se encontró |

### Fuera de git

| Archivo | Qué cambia |
|---|---|
| `Ejemplos/RS2_Verification Manuals/_auditoria/COMPUTO/bench/{comun.py,casos.py,LEEME.md,datos/manifiesto.json}` | rutas de `OGR_Suite`; importaciones a `ogr_core.fem` |
| `…/_tools/banco.py` | `REPO_OGR` |
| `05_…/05_Groundwater_Problema004/construir_modelo.py`, `…Problema015/…` | importaciones |
| `02_…/02_Slide2_Problema{010,038,102}/construir_modelo.py` | importaciones |
| `02_…/_tools/elegibilidad_critica_d155.py` | rutas de los siete interruptores |

Diff a la propietaria antes de escribir ninguno.

## Decisiones de diseño

- **F1 no se fusiona** (Q1). `ogr_core/` y `ogr_fem2d/` desaparecen enteros, así que de F1 solo
  quedan sus cambios en tests; se reproducen y se comparan con `trial`. El diff del programa contra
  `trial` (`git diff ensayo/trial -- ogr_slip2d ogr_gui ogr_cli ogr_api ogr_mcp`) solo puede
  diferir en lo que esta versión añade a propósito, y se explica.
- **Los pools en un venv** (propuesta; se reconfirma en el plan de v0.1.472). En un venv
  (`sys.prefix != sys.base_prefix`), sin consola, los hijos van con el `pythonw.exe` **del Python
  base** y `__PYVENV_LAUNCHER__` apuntando al `pythonw.exe` del venv, que es lo que el ensayo vio
  funcionar. La variable va en `os.environ` y no alrededor de cada pool: el pool lanza sus
  trabajadores bajo demanda (también desde su hilo gestor, al reponer uno), y `popen_spawn_win32`
  solo pasa un entorno propio cuando el ejecutable es `sys.executable`; con otro, hereda el del
  proceso. Es un cambio de entorno del proceso igual cada vez, como `mp.executable`: entrada en la
  lista blanca con su porqué. El `pythonw.exe` base solo, sin lanzador, queda descartado: el hijo
  sale del venv y calcula con otro árbol.
- **Un solo sitio para encontrar fuentes** (`tests/_sources.py`). Hoy cada test se fabrica su
  `_ROOT / "ogr_core" / …`; tras borrar la carpeta, unos fallan con `FileNotFoundError` y otros
  **pasan en vacío** (`test_core_layering_v1340`, `test_settings_coverage_v1103`,
  `test_no_vendor_names_v1160`…). Un ayudante que resuelve `ogr_core/…` contra
  `Path(ogr_core.__file__).parent` y falla si un recorrido no encuentra nada cierra las dos cosas a
  la vez, y las claves de los censos (`"ogr_core/…"`) no cambian.
- **El runner: lo genérico en OGR-Core, lo de este repositorio aquí.** Los tests que cargaban
  `tests/_runner.py` y usaban lo de dentro (`DURATIONS`, `partition`, `run_test`…) ya tienen su
  equivalente en `ogr-core` (`tests/*_v10.py`, `*_v020.py`). Aquí quedan, en un archivo, las
  invariantes que son de Slip2D (`censo.md` §4). La que OGR-Core no prueba («un test `async`
  falla») se queda aquí contra el runner compartido y se pide para la v0.2.1.
- **Instalación de desarrollo.** El núcleo en editable desde su árbol (`pip install -e
  …\OGR-Core`) y Slip2D en editable. Si `pip install -e ".[mcp]"` reinstalara `ogr-core` desde la
  etiqueta encima del editable, Slip2D se instala con `--no-deps` (lo demás ya está fijado) y se
  comprueba con `pip check`; la instalación desde la etiqueta la prueba la CI.

## Riesgos

| Riesgo | Cómo se detecta o se evita |
|---|---|
| Un censo que leía `ogr_core/` pasa en verde porque la carpeta ya no está | `_sources.package_files` falla si no encuentra nada; cada test tocado lleva su diente (carpeta vacía o archivo quitado) |
| El `ogr_core` editable no es la versión fijada | el runner compartido se niega y lo dice; `test_version_consistency_v176` también |
| Medir el árbol equivocado (la lección de la fase 1: el orquestador del banco reescribe `PYTHONPATH`) | leer la procedencia de cada huella; el banner del runner nombra los dos árboles |
| `__PYVENV_LAUNCHER__` en el entorno llega a otros subprocesos | el lanzador del venv la sobrescribe con la suya; se comprueba en v0.1.472 con los trabajos de `ogr_api` y los trozos del runner |
| Dos corridas a la vez, o un runner mientras corre un lote del banco | una suite a la vez; el banco cuenta como intruso cualquier `_runner.py` |
| La suite entera tarda (20 min `--jobs 4`, 40 en serie) | en segundo plano, guardando el código de salida |
| Búsquedas recursivas sobre el banco (minutos) | solo sobre archivos concretos |

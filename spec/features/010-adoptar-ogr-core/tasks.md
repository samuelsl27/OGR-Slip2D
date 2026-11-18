# Tareas

Pequeñas y verificables. Si una tarea no se puede comprobar, no es una tarea: es un deseo. Plan y
OK de la propietaria antes de cada fase; una a la vez.

## Fase 0 · La spec

- [x] 0.1 `main` sigue en `d48e2b3`, limpio (2026-11-18).
- [x] 0.2 Leídos `AGENTS.md`, el `LEEME.md` del traspaso, `CHANGELOG_v0.2.0.md` de OGR-Core y la
      spec 009 de la rama `dev/extraer-ogr-core`.
- [x] 0.3 Censo (`censo.md`): los 39 tests comparados con los de OGR-Core, las importaciones, los
      tests que leen fuentes del núcleo, el runner y las fugas, los pools, el banco.
- [x] 0.4 Decisiones Q1–Q3 de la propietaria (`spec.md`).
- [x] 0.5 Rama `dev/adoptar-ogr-core` y esta spec.

## Fase 1 · v0.1.472, los pools en un entorno virtual

- [ ] 1.1 Plan de la fase y OK (incluido el coste del test que necesita un venv).
- [ ] 1.2 `ogr_slip2d/processes.py`: el `pythonw.exe` base con `__PYVENV_LAUNCHER__` dentro de un
      venv; igual que antes fuera.
- [ ] 1.3 Test: pool real en un venv, el hijo con el mismo `sys.prefix` y los mismos archivos de
      `ogr_slip2d` y `ogr_core`; mueren los dos dientes (`pythonw.exe` del venv; base sin
      lanzador).
- [ ] 1.4 Los once tests de pools de `censo.md` §5, en un venv: pasan.
- [ ] 1.5 Versión en nueve sitios y changelog; suite entera `--jobs 4` en verde.

## Fase 2 · v0.1.473, la adopción

- [ ] 2.1 Plan de la fase y OK.
- [ ] 2.2 Bundle a refs locales `ensayo/trial` y `ensayo/envoltorio`.
- [ ] 2.3 `pyproject.toml`: `ogr-core` fijado; fuera `pyclipper` y `[fem]`.
- [ ] 2.4 Fuera `ogr_core/` y `ogr_fem2d/`.
- [ ] 2.5 `reescribir_imports.py` (226 sentencias, 58 archivos) y las 62 menciones; al terminar,
      ninguna línea importa `ogr_fem2d`.
- [ ] 2.6 Fuera los 39 tests de `censo.md` §1. Antes, los seis que cargan por ruta
      `test_unsaturated_v127` o `test_rescue_face_v1356` dejan de hacerlo (opción de `censo.md` §1
      que elija la propietaria), y un `grep` confirma que ningún otro carga ninguno de los 39.
- [ ] 2.7 `tests/_runner.py` (envoltorio) y `tests/_leaks.py` (puente); `test_runner_wrapper_v1473`
      con lo de `censo.md` §4; fuera lo que ya está en OGR-Core.
- [ ] 2.8 `tests/_sources.py` y los tests de `censo.md` §3, cada uno con su diente.
- [ ] 2.9 Versión en siete sitios; `test_version_consistency_v176` comprueba también la versión
      fijada del núcleo.
- [ ] 2.10 *Acerca de* con la versión del núcleo, `tr()` y español.
- [ ] 2.11 Documentos (`spec.md`, criterios de la v0.1.473) y CI.
- [ ] 2.12 Diff del programa contra `ensayo/trial`, explicado.
- [ ] 2.13 Changelog registrando **qué se encontró**.

## Fase 3 · Entorno

- [ ] 3.1 Plan y OK.
- [ ] 3.2 `.venv` con `requisitos_fijados.txt`; `pip install -e …\OGR-Core`; Slip2D en editable con
      `[mcp]`; `pip check`. El Python del sistema, sin tocar.

## Fase 4 · El banco (fuera de git)

- [ ] 4.1 Diff a la propietaria de los archivos de `censo.md` §6, y OK.
- [ ] 4.2 Aplicado; el lote `version` arranca.

## Fase 5 · Verificación

- [ ] 5.1 Suite entera `--jobs 4` en el `.venv` y `comparar_suites.py` contra
      `antes/suite_d48e2b3_jobs4.txt`: cada diferencia explicada.
- [ ] 5.2 Suite entera en serie, sin argumentos.
- [ ] 5.3 Huella del banco, lote `version`: 23 de 23 idénticos (`comparar_huellas.py`), leyendo la
      procedencia.
- [ ] 5.4 Diff vacío de `tests/test_slide_validation_*`, `tests/test_acads_*` y `validacion/`.
- [ ] 5.5 `python -m ogr_gui` (fuera de pantalla), `python -m ogr_cli --help`,
      `python -m ogr_mcp --help`.
- [ ] 5.6 CI en verde (tras el push que autorice la propietaria).
- [ ] 5.7 Pendiente para la propietaria: Slip2D en el Python del sistema, el servidor MCP y los
      accesos directos.

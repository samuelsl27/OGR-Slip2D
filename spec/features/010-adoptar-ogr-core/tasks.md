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

- [x] 1.1 Plan de la fase y OK (2026-11-18): contexto de `multiprocessing` acotado al pool (B), no la
      variable en todo el proceso.
- [x] 1.2 `ogr_slip2d/processes.py`: el `pythonw.exe` base con `__PYVENV_LAUNCHER__`, solo mientras se crea
      cada trabajador (`pool_context`, `_start_in_venv`); igual que antes fuera.
- [x] 1.3 `test_venv_pools_v1472` (14 casos): pool real en un venv con los árboles del padre y sin consola; los
      dos dientes; ocho mutantes, todos muertos.
- [x] 1.4 Los once tests de pools, en un venv: 96 de 96 (control 0.1.471: fallan los once). Y la suite entera
      en el venv desechable: 8058 de 8060, sin fallos.
- [x] 1.5 Versión en nueve sitios y changelog; suite entera `--jobs 4` en verde (8058 de 8060, la segunda; la
      primera dio 12 fallos por un error propio, `CHANGELOG_v0.1.472.md` §0).

## Fase 2 · v0.1.473, la adopción

- [x] 2.1 Plan de la fase y OK (2026-11-18): el `.venv` primero; parar antes de borrar el núcleo; las presas a
      `tests/_dam_models.py`.
- [x] 2.2 Bundle a refs locales `ensayo/trial` y `ensayo/envoltorio`.
- [x] 2.3 `pyproject.toml`: `ogr-core` fijado; fuera `pyclipper` y `[fem]`.
- [x] 2.4 Fuera `ogr_core/` y `ogr_fem2d/` (tras cerrar la propietaria Claude Desktop).
- [x] 2.5 `reescribir_imports.py` (225 sentencias en 57 archivos) y las menciones; ninguna línea importa
      `ogr_fem2d`.
- [x] 2.6 Fuera los 39; `_dam_models.py` para los seis que cargaban dos de ellos.
- [x] 2.7 Envoltorio y puente; `test_runner_wrapper_v1473`; fuera los ocho del runner; el censo del núcleo
      entero queda solo en OGR-Core (decisión de la propietaria).
- [x] 2.8 `tests/_sources.py`, `test_sources_v1473` y los 22 + 6 archivos; con el núcleo vacío fallan 30.
- [x] 2.9 Versión en siete sitios; el núcleo importado es el fijado.
- [x] 2.10 *Acerca de* con la versión del núcleo, `tr()` y español.
- [x] 2.11 Documentos y CI.
- [x] 2.12 Diff del programa contra `ensayo/trial`, explicado en el changelog.
- [x] 2.13 Changelog; suite entera `--jobs 4` en el `.venv`: 7529 de 7531, 0 fallos, sin fugas.

## Fase 3 · Entorno

- [x] 3.1 Adelantada a la fase 2, por decisión de la propietaria.
- [x] 3.2 `.venv` con `requisitos_fijados.txt` (95, comprobados con `pip freeze`), `ogr-core` en editable,
      Slip2D en editable con `--no-deps` (con dependencias reinstalaba `ogr-core` desde GitHub); `pip check`
      limpio. El Python del sistema, sin tocar.

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

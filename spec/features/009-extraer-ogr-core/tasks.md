# Tareas

Pequeñas y verificables. Si una tarea no se puede comprobar, no es una
tarea: es un deseo.

## F0 · Antes de tocar código

- [x] 0.1a El propietario responde P1–P7 de `spec.md` (2026-10-27).
- [x] 0.1b El propietario aprueba este plan (2026-10-27).
- [x] 0.2 v0.1.370 confirmada (`32cb051`); rama `dev/extraer-ogr-core` en
      un *worktree* aparte, `C:\Samuel\OpenGeoRock_Slip2d\OGR-Slip2D-f1`,
      porque en el árbol principal se está haciendo la v0.1.371 en paralelo.
- [x] 0.3 Censo exacto, archivo por archivo: los tests que se mueven, los
      que se quedan y los 24 que nombran rutas del núcleo, con qué hace cada
      uno con esas rutas. Está en `censo.md` (2026-10-27); se anota en el
      changelog de F1.
- [x] 0.4 Confirmar que ningún pickle, caché ni `.ogr` guarda rutas de
      módulo de `ogr_fem2d` (`ogr_api/jobs`, `Project.to_dict`): ninguno
      (`censo.md` §6).
- [ ] 0.5 Medida de referencia: suite completa sin argumentos (total de
      casos y código de salida), los FS de los casos de validación y un
      campo de filtración transitoria guardados para el A/B.
      **Hecho el A/B** (2026-10-27, sobre v0.1.370): FS de los seis métodos
      en Ej_1, la búsqueda de Bishop, el campo no saturado de
      `test_coupling_v128` y la infiltración de Celia (1990), con `repr` de
      float y huellas SHA-256. Dos corridas idénticas byte a byte: el
      cálculo es determinista, y repetido sobre `32cb051` limpio da lo
      mismo. Suite completa de v0.1.370: la de su changelog (6617 de 6618,
      un fallo de tiempo en `test_optimizations_v111`, máquina cargada).
- [ ] 0.6 Anotar las anomalías que aparezcan antes de corregir nada
      (regla 6).

## F1 · Malla y filtración dentro de `ogr_core` (Slip2D)

- [x] 1.1 Fijar los nombres de módulo en `ogr_core/fem/` (p. ej.
      `generator.py`, `seepage.py`, `bc_targets.py`, `streamlines.py`,
      `messages.py`) sin chocar con `mesh.py` ni `seepage_data.py`.
- [x] 1.2 Mover los cinco módulos sin cambiar nada salvo las importaciones.
      Un `git diff -M` debe verlos como renombrados. (Lo hace; `seepage.py`
      cambia 6 líneas.)
- [x] 1.3 Reescribir las importaciones: 6 archivos de programa y 46 de
      tests. Al terminar, la búsqueda de `ogr_fem2d` en el código da cero.
      (181 sentencias en 52 archivos; cero importaciones restantes.)
- [x] 1.4 Borrar `ogr_fem2d/`.
- [x] 1.5 Adaptar los tests que nombran `ogr_fem2d` como paquete (lista en
      `censo.md` §7), cada uno con su cabecera explicando la invariante
      nueva.
- [x] 1.6 `test_fem_data_in_core_v1342`: retirar «una clase en las dos
      rutas» y conservar «un modelo con malla y filtración carga sin el
      solver».
- [ ] 1.7 Versión en ocho sitios; `test_version_consistency_v176` en verde.
      **Ocho sitios hechos; la subida del número se hace al integrar** (la
      v0.1.371 va en paralelo y decide cuál toca).
- [x] 1.8 A/B contra 0.5: FS y campo de filtración idénticos al bit, y
      ningún `ogr_fem2d` en `sys.modules`.
- [ ] 1.9 Suite completa sin argumentos en verde; el total de casos coincide
      con 0.5 salvo los tests de reexportación retirados (contados).
- [x] 1.10 `AGENTS.md`, `CONTRIBUTING.md` y `docs/architecture.md`: capas
      nuevas; changelog registrando qué se encontró (borrador en
      `changelog_F1.md`, que pasa a `docs/changelog/` al integrar).

## F2 · Repositorio OGR-Core

- [x] 2.1 Carpeta `C:\Samuel\OpenGeoRock_Core\OGR-Core` y repositorio
      público `samuelsl27/OGR-Core`, vacío (2026-10-27; creado con permiso
      del propietario).
- [x] 2.2 Copiar `ogr_core/` del commit de F1 y citar ese commit en el
      primer commit (P5). Copiado de `2d68c29`; primer commit de OGR-Core
      `ae1c83e` (local, sin subir).
- [x] 2.3 `pyproject.toml` con las dependencias del censo; versión 0.1.0
      (P2), y el changelog 0.1.0 dice de qué commit de Slip2D sale.
- [x] 2.4 Runner compartido (P4) con gancho opcional para `gc_guard`; tests
      del runner (selección, salida 2 con patrón vacío, procedencia), y uno
      nuevo para los paquetes compartidos y la versión fijada.
- [x] 2.5 Mover los 34 tests de `censo.md` §3 sin tocar valores ni
      tolerancias (copiados byte a byte de `2d68c29`). En F3 se borran de
      Slip2D.
- [x] 2.6 Tests propios del núcleo: licencia, nombres de productos, suelo de
      Python, acciones de CI, capas (censo estático y en tiempo de
      ejecución, con un modelo construido solo con el núcleo) y versión.
      Cada censo afirma que encontró algo.
- [ ] 2.7 En un venv limpio: `pip install -e .` sin PySide6, y suite
      completa en verde. **Suite completa en verde: 499 de 499.** El venv
      limpio lo hará la CI al subir (instalar dependencias aquí exige el
      OK del propietario).
- [x] 2.8 `LICENSE`, `CLA.md`, `CONTRIBUTORS.md`, README, `AGENTS.md`,
      `CLAUDE.md`, `CONTRIBUTING.md`, CI (acciones en versiones mayores
      comprobadas, como en `test_ci_actions_v181`), changelog.
- [ ] 2.9 Etiqueta `v0.1.0` (P2, P3): al subir, con el OK del propietario.

## F3 · Slip2D depende de `ogr-core`

- [ ] 3.1 Borrar `ogr_core/` y los tests movidos en 2.5.
- [ ] 3.2 `pyproject.toml`: `ogr-core` fijada (P3); revisar qué dependencias
      quedan.
- [ ] 3.3 Runner: propios frente a compartidos; el banner nombra los dos
      árboles; se niega con versión distinta. Test nuevo en
      `test_runner_provenance_v189`.
- [ ] 3.4 `test_version_consistency_v176`: siete sitios más la versión fijada
      del núcleo.
- [ ] 3.4b *Acerca de* da también la versión de `ogr_core`, con su
      traducción española (regla 2) y su test.
- [ ] 3.5 Los tests de 0.3 que leían `ogr_core/`: cada invariante queda
      cubierta en uno de los dos repositorios, y ninguno busca en una
      carpeta vacía.
- [ ] 3.6 CI instala `ogr-core` desde la etiqueta; en verde.
- [ ] 3.7 Entorno limpio: `pip install -e ".[mcp]"` trae el núcleo y el
      programa arranca (`python -m ogr_gui`, `python -m ogr_cli --help`).
- [ ] 3.8 A/B contra 0.5 otra vez: idéntico al bit.
- [ ] 3.9 Suite completa sin argumentos en verde; el total de casos más los
      de OGR-Core coincide con 0.5, y las cifras van al changelog.
- [ ] 3.10 El diff de `tests/test_slide_validation_*`, `tests/test_acads_*`
      y `validacion/` está vacío.

## F4 · Documentación

- [ ] 4.1 Slip2D: `AGENTS.md` (primer párrafo, estructura, capas, stack,
      siete sitios de versión, comandos con los dos árboles en editable),
      `CONTRIBUTING.md`, `README.md`, `README.es.md`, `docs/quickstart.md`,
      `docs/architecture.md`, `spec/constitution/*`.
- [ ] 4.2 Versión mínima de Slip2D que convive con OGR FEM2D, en los README
      de los dos.
- [ ] 4.3 OGR-FEM2D: `AGENTS.md` y `tech-stack.md` apuntan a la versión
      etiquetada de `ogr-core`.
- [ ] 4.4 Changelogs registrando **qué se encontró**.

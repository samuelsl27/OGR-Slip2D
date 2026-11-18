# Plan de implementación

> Aprobado por el propietario (2026-10-27), con las decisiones P1–P7 de
> `spec.md`. Se empieza cuando v0.1.370 esté confirmada y exista
> `samuelsl27/OGR-Core`.

## Enfoque

**Mover, no reescribir**, y en dos pasos que se puedan comprobar por
separado:

1. **F1, dentro de Slip2D**: el generador de malla y la filtración pasan de
   `ogr_fem2d/` a `ogr_core/fem/` (P1), todas las importaciones cambian a la
   ruta nueva y `ogr_fem2d/` desaparece. Es una versión normal de Slip2D,
   con la suite completa en verde y los mismos números al bit.
2. **F2, OGR-Core**: el repositorio nuevo nace con `ogr_core/` tal como
   quedó en el commit de F1, sus tests y sus herramientas.
3. **F3, Slip2D otra vez**: borra `ogr_core/`, depende de `ogr-core` con
   versión fijada (P3) y el runner y el test de versión pasan a reconocer un
   árbol compartido.
4. **F4**: documentación de los dos repositorios.

Tras F1, la extracción de F2–F3 es solo empaquetado: si algo cambia un
número, se sabe en qué paso fue.

```
hoy:   ogr_core ─► ogr_slip2d / ogr_fem2d ─► ogr_api ─► {ogr_gui, ogr_cli, ogr_mcp}
F1:    ogr_core (con fem: datos + malla + filtración) ─► ogr_slip2d ─► ogr_api ─► {…}
F3:    [OGR-Core] ogr_core ─► [OGR-Slip2D] ogr_slip2d ─► ogr_api ─► {…}
       [OGR-FEM2D] ogr_fem2d ─┘ (más adelante)
```

## Archivos que se tocan

### F1 — Slip2D (nada sale todavía del repositorio)

| Archivo | Qué cambia |
|---|---|
| `ogr_fem2d/mesh/generator.py`, `solvers/seepage.py`, `solvers/bc_targets.py`, `solvers/streamlines.py`, `messages.py` | movidos, sin cambiar su contenido salvo las importaciones, a `ogr_core/fem/` (P1; nombres de módulo a fijar en la tarea 1.1) |
| `ogr_fem2d/` (`__init__`, `mesh/`, `solvers/`, `elements/`) | se borra |
| `ogr_core/fem/__init__.py` | sigue exportando **solo los datos**; los solvers se importan por su submódulo, para que cargar un modelo no cargue el solver |
| `ogr_gui/core_messages.py`, `ogr_gui/dialogs/boundary_conditions_dialog.py`, `ogr_gui/interpret_window.py`, `ogr_gui/main_window.py`, `ogr_api/ops/groundwater.py`, `ogr_slip2d/transient_stability.py` | importaciones a la ruta nueva |
| 46 archivos de `tests/` | importaciones a la ruta nueva |
| `tests/_runner.py` | `PACKAGES` sin `ogr_fem2d` |
| `tests/test_version_consistency_v176.py` | ocho sitios en vez de nueve |
| `tests/test_api_layering_pyexec_v1194.py`, `test_no_vendor_names_v1160.py`, `test_settings_coverage_v1103.py`, `test_tensile_tolerance_retired_v1192.py`, `test_agent_scaffolding_v158.py`, `test_overburden_in_core_v1344.py` | quitan `ogr_fem2d` de sus listas de carpetas de este repositorio. Los censos de capas (`test_core_layering_v1340`, `_closed_v1346` y las comprobaciones en subproceso) lo **mantienen prohibido**: es el nombre del programa 03 (`censo.md` §7) |
| `tests/test_fem_data_in_core_v1342.py` | su invariante «una clase en las dos rutas» se retira (ya no hay ruta antigua); se conserva «un modelo con malla y filtración carga sin el solver» |
| `AGENTS.md`, `CONTRIBUTING.md`, `docs/architecture.md` | capas y estructura sin `ogr_fem2d`; la regla de capas dice que el núcleo contiene el solver de filtración compartido (P1) |

### F2 — OGR-Core (repositorio nuevo, P6)

| Archivo | Qué es |
|---|---|
| `ogr_core/` | copia exacta del árbol del commit de F1 |
| `pyproject.toml` | distribución `ogr-core`, Python ≥ 3.11, AGPL-3.0-or-later, dependencias del censo (numpy, scipy, shapely, ezdxf, reportlab, h5py), versión **0.1.0** (P2) |
| `ogr_core/testing/runner.py` (P4) | el runner de Slip2D, sin el `import` de `ogr_gui`: el `gc_guard` entra por un gancho que solo instala quien lo tiene |
| `tests/` | los 34 archivos movidos (`censo.md` §3) y las versiones para el núcleo de los tests de licencia, nombres de productos, suelo de Python, capas y versión |
| `LICENSE`, `CLA.md`, `CONTRIBUTORS.md`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md` | los de la suite, con su alcance |
| `.github/workflows/tests.yml` | instalar y pasar la suite, con cada acción en una versión mayor ya comprobada, como exige `test_ci_actions_v181` |
| `docs/changelog/` | primera entrada: de qué commit de Slip2D sale y qué se encontró |

### F3 — Slip2D

| Archivo | Qué cambia |
|---|---|
| `ogr_core/` | se borra |
| `pyproject.toml` | dependencia `ogr-core @ git+https://github.com/samuelsl27/OGR-Core@v0.1.0` (P3); se revisa qué dependencias usa Slip2D directamente y cuáles solo usaba el núcleo |
| `ogr_gui/dialogs/misc_dialogs.py` (`AboutDialog`) | da también la versión de `ogr_core`, con su traducción (P2) |
| `tests/_runner.py` | delega en el runner del núcleo (P4); distingue paquetes **propios**, que deben resolver dentro del repositorio, de **compartidos** (`ogr_core`), de los que nombra la ruta, el commit y la versión, y se niega si la versión no es la fijada |
| `tests/test_version_consistency_v176.py` | siete sitios más la comprobación de la versión fijada de `ogr_core` |
| `tests/test_runner_provenance_v189.py` | el caso nuevo: un paquete compartido fuera del árbol no es un extraño; uno propio sí |
| tests que leen fuentes del núcleo (los 24 de `spec.md`) | o se mueven a OGR-Core, o dejan de leer `ogr_core/`. Ninguno se borra sin que su invariante quede cubierta en uno de los dos repositorios |
| `.github/workflows/tests.yml` | instala `ogr-core` desde la etiqueta fijada |
| `AGENTS.md`, `CONTRIBUTING.md`, `README.md`, `README.es.md`, `docs/architecture.md`, `docs/quickstart.md`, `spec/constitution/*` | el núcleo es una dependencia; instalación para desarrollo con los dos árboles en editable |

## Decisiones de diseño

- **Primero mover dentro de Slip2D y después extraer.** Hacerlo todo de una
  vez mezclaría un cambio de importaciones (52 archivos) con un cambio de
  empaquetado, y si un número cambiara no se sabría cuál de los dos fue.
- **Sin módulo de compatibilidad llamado `ogr_fem2d`.** Es el patrón de
  v0.1.346 (la ruta antigua falla diciendo cuál es la nueva), pero aquí ese
  módulo **ocuparía el nombre**, que es justo lo que la extracción viene a
  liberar. La ruta antigua dará `ModuleNotFoundError`, y el changelog dirá
  adónde fue cada nombre.
- **`ogr_core/fem/__init__.py` no importa el solver.** Hoy cargar un modelo
  con malla y filtración no trae el solver (`test_fem_data_in_core_v1342`).
  Con el solver dentro del núcleo, esa propiedad se conserva importándolo
  solo por su submódulo.
- **El runner distingue propios y compartidos.** La razón de
  `foreign_packages` (v0.1.89) sigue en pie: que una ejecución nunca mida
  en silencio un árbol distinto del que se está editando. Con un núcleo
  aparte, la respuesta correcta no es dejar de mirar, sino **nombrar el
  árbol del núcleo** (ruta, commit, versión) y negarse cuando su versión no
  es la fijada.
- **Los 5 tests que toman modelos de tests de Slip2D se quedan aquí.**
  Prueban la integración del núcleo con este programa, y moverlos obligaría
  a llevarse modelos de validación del equilibrio límite.
- **Las dependencias de `ogr-core` salen del censo**, no de la lista de
  Slip2D: hoy pyclipper, matplotlib, PySide6, pydantic, typer y rich no los
  importa el núcleo.

## Riesgos

| Riesgo | Cómo se detecta o se evita |
|---|---|
| En desarrollo, el `ogr_core` editable no es la versión fijada | el runner de F3 se niega y lo dice |
| Con la serie nueva desde 0.1.0 (P2), «ogr_core 0.1.5» puede ser el núcleo nuevo o el de una versión vieja de Slip2D | el changelog 0.1.0 de OGR-Core dice de qué commit sale; el banner del runner y *Acerca de* dan siempre las dos versiones |
| Una instalación con pip de un Slip2D anterior a F1 (que trae `ogr_fem2d`) junto al futuro OGR FEM2D se sobrescribe | documentar la versión mínima de Slip2D compatible; los instaladores congelados no comparten entorno |
| Un test que lee `ogr_core/` por ruta pasa en verde porque la carpeta ya no está (busca en el vacío) | cada test de censo debe afirmar que encontró algo, como ya hace `test_core_layering_v1340` con su módulo de prueba |
| Los trabajos en subproceso viajan por pickle, y la ruta de módulo de las clases movidas cambia | el pickle vive dentro de una ejecución (`ogr_api/jobs`); confirmar que ningún pickle se guarda entre versiones (tarea 0.4) |
| Hay trabajo de v0.1.370 sin confirmar que toca `ogr_core/` y `ogr_fem2d/` | empezar con el árbol limpio y en su propia rama (P7); nadie toca `ogr_core/` mientras F1–F3 estén abiertas |
| La suite tarda 50–72 min | lanzarla en segundo plano y guardar el código de salida (`AGENTS.md`); F1 y F3 necesitan cada una una corrida completa sin argumentos |

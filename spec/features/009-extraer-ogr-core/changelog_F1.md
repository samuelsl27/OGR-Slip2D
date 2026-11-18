# OGR Slip2D — F1 de la spec 009 (borrador de changelog)

> Borrador hasta que la rama `dev/extraer-ogr-core` se integre en `main`: entonces pasa a
> `docs/changelog/CHANGELOG_v0.1.<n>.md`, con el número que toque (la v0.1.371 se está haciendo en
> paralelo), y la versión sube en los **ocho** sitios.

**La malla y la filtración por elementos finitos pasan de `ogr_fem2d` a `ogr_core/fem/`, y
`ogr_fem2d` sale del repositorio.** Primer paso de la extracción del núcleo a su propio paquete,
`ogr-core` (spec 009): dentro de Slip2D todavía, para que el cambio de importaciones se compruebe
solo, antes de cambiar el empaquetado. Ningún número cambia.

## 0. Lo que se encontró

- **Una importación relativa que cambiaba de sentido en silencio.** `ogr_fem2d/solvers/seepage.py`
  importaba `from .. import messages as M` (los códigos `seepage.*`). Movida tal cual a
  `ogr_core/fem/seepage.py`, la misma línea habría apuntado a `ogr_core/messages.py`, que también
  existe: el módulo cargaba y el fallo habría llegado con el primer aviso del solver. Ahora es
  `from . import messages as M`. Se vio al probar el script de reescritura sobre una copia del árbol,
  no al compilar.
- **La mitad del trabajo ya estaba hecha** desde v0.1.342 (D337): la malla y los datos de filtración
  vivían en `ogr_core/fem/` y `ogr_fem2d` solo los reexportaba. Lo que faltaba era el generador, los
  solvers, los destinos de contorno, las líneas de corriente y los códigos.
- **Sin módulo de compatibilidad con el nombre `ogr_fem2d`.** Es el patrón de v0.1.346 (la ruta vieja
  falla diciendo cuál es la nueva), pero aquí ese módulo ocuparía justo el nombre que se libera para
  el programa de elementos finitos de la suite. La ruta vieja da `ModuleNotFoundError`; esta tabla
  dice adónde fue cada cosa:

  | Antes | Ahora |
  |---|---|
  | `ogr_fem2d.mesh` (`generate_mesh`, `generate_mesh_for_project`, `discretize_edges`) | `ogr_core.fem.generator` |
  | `ogr_fem2d.mesh` (`Mesh`, `Node`, `Element`), `ogr_fem2d.mesh.mesh` | `ogr_core.fem` |
  | `ogr_fem2d.solvers.seepage` y los solvers de `ogr_fem2d.solvers` | `ogr_core.fem.seepage` |
  | los datos de `ogr_fem2d.solvers` (`BCType`, `SeepageResult`…) | `ogr_core.fem` |
  | `ogr_fem2d.solvers.bc_targets` y sus nombres | `ogr_core.fem.bc_targets` |
  | `ogr_fem2d.solvers.streamlines` | `ogr_core.fem.streamlines` |
  | `ogr_fem2d.messages` | `ogr_core.fem.messages` |
  | `ogr_fem2d.elements` (vacío) | — |

- **`ogr_fem2d` sigue prohibido para el núcleo**, ahora como nombre del programa 03: los censos de
  capas y las comprobaciones en subproceso que lo nombran se han dejado como estaban. Lo que se ha
  quitado es `ogr_fem2d` de las listas de **carpetas de este repositorio**, donde un `rglob` sobre una
  carpeta inexistente habría devuelto nada y dado un verde falso.
- **Un test que miraba el sistema de importación en vez del árbol.** Comprobar que `ogr_fem2d` ya no
  existe con `find_spec` daría un resultado falso en una máquina con otra copia instalada en editable
  (aquí, el árbol principal): resolvería a ESA copia, la trampa de v0.1.84. `test_fem_data_in_core`
  mira la carpeta.
- `test_fem_data_in_core_v1342`: «una clase en las dos rutas» pasa a «una clase en una ruta», y
  «un modelo carga sin el motor» pasa a exigir que cargar un modelo con malla y filtración no traiga
  `ogr_core.fem.seepage` ni `ogr_core.fem.generator`: el `__init__` de `ogr_core.fem` sigue
  exportando solo los datos.

## 1. Qué cambia

- Cinco módulos movidos con `git mv` (git los ve como renombrados): el generador, `bc_targets`,
  `streamlines` y `messages` sin cambios; `seepage.py` con la importación relativa, la importación
  diferida del generador y un docstring.
- 181 importaciones reescritas en 52 archivos (6 del programa, 46 de tests) por un script que parte
  cada sentencia por el destino real de cada nombre y conserva los `# noqa`.
- `tests/_runner.py`: `PACKAGES` sin `ogr_fem2d`. `test_version_consistency_v176`: ocho sitios.
- `AGENTS.md`, `CONTRIBUTING.md`, `README.md`, `README.es.md`, `docs/architecture.md`: estructura,
  capas (el núcleo contiene el solver de filtración) y ocho sitios de versión.
- La spec 009 entra en el repositorio (`spec/features/009-extraer-ogr-core/`).

## 2. Pruebas

- **A/B al bit** (`ab_numbers.py`, en el mismo árbol antes y después): FS de los seis métodos en los
  círculos de referencia de Ej_1, la búsqueda en rejilla de Bishop (FS, centro, radio, 4851
  círculos), el campo no saturado de `test_coupling_v128` (huellas SHA-256 de alturas y presiones) con
  su FS de Bishop, y la infiltración de Celia et al. (1990) (perfil y balance de masa). **Idénticos**.
  La medida es determinista: dos corridas antes del cambio dieron lo mismo byte a byte. Y tras el
  cambio no hay ningún módulo `ogr_fem2d` en `sys.modules`.
- **Los tests que toca F1**, más los de capas, runner, licencia, suelo de Python y
  `test_coupling_v128`: 59 archivos, **807 de 807**, en el worktree (`tree:
  …\OGR-Slip2D-f1`). Ejecución filtrada: no es la suite.
- **Suite entera**: pendiente (no a la vez que otra suite completa: la v0.1.370 tardó 3 h 50 min con
  la máquina cargada).
- **Un detalle del runner**: en un *worktree* el banner dice `@ ?` en vez del commit, porque allí
  `.git` es un archivo que apunta al repositorio y no una carpeta. El runner compartido de OGR-Core lo
  resuelve (F2); el de aquí se queda como está hasta F3.

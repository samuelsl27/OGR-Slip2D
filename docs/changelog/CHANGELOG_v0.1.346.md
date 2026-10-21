# OGR Slip2D v0.1.346

**La estadística (análisis probabilístico y de sensibilidad) sube, entera, del núcleo al motor, y el núcleo
deja de importar cualquier capa de encima, medido en el código y en ejecución (D337, última parte; D337
cerrada).** Séptima versión de la tanda P8k.

## 0. Lo que se encontró

- **Las últimas siete entradas del censo eran los ejecutores estadísticos.**
  - `probabilistic.py` y `sensitivity.py` estaban en `ogr_core/statistics`, pero ejecutan el motor: una
    búsqueda por muestra, la reevaluación del método y las superficies del motor.
  - Lo que el paquete tiene de puro (distribuciones, variables aleatorias y el barrido de desembalse, que ya
    recibía la búsqueda como argumento) se queda.
- **Suben enteros, sin partirlos.** Los tests parchean sus globales (`P._evaluate_on`, `_rebuild_surface`,
  `_surface_key`…), y un parche en una mitad no llegaría a la otra: es la trampa del interruptor de 0.1.344
  otra vez.
- **La ruta vieja no puede reexportar.** Una reexportación desde el núcleo sería justo la importación que
  D337 quita. Así que falla en voz alta y dice adónde fue.
- **Dos comprobaciones habrían pasado sin mirar nada.**
  - `TestOneDoor` de v1235 buscaba llamadas a `GridSearch(` en `ogr_core/statistics/*.py`, y la del manual 02
    hacía lo mismo.
  - Tras la mudanza habrían barrido un paquete sin ejecutores y dado «ninguna».
  - Las dos siguen ahora a los módulos que suben.
- **El manual 02 lee los dos módulos por su ruta** en tres comprobaciones. Leer el módulo de reserva habría
  dado un árbol sin funciones. Ahora leen el de `ogr_slip2d`, y el viejo si es un árbol anterior.
- **Dos docstrings que mentían dicen ahora la verdad:**
  - `drawdown_sweep.py:40`: «`ogr_core` still never imports `ogr_slip2d`»;
  - `ponded_water.py:71`.

## 1. Qué cambia

- **`ogr_slip2d/probabilistic.py` y `ogr_slip2d/sensitivity.py`:** los dos módulos, palabra por palabra. Sus
  importaciones relativas del paquete del núcleo pasan a absolutas.
- **`ogr_core/statistics/probabilistic.py` y `sensitivity.py`** son módulos de reserva que lanzan
  `ImportError` con la ruta nueva.
- **`ogr_core.statistics`** pide un nombre de los que se fueron con `__getattr__` (PEP 562), y lanza
  `ImportError` con su ruta nueva en vez de un `AttributeError` mudo.
- **Las importaciones:** 130 sentencias en 27 archivos del programa y de los tests, más 31 en 7 herramientas
  del banco, reescritas con una herramienta que solo toca sentencias `import` por su rango de líneas.
- **`test_core_layering_v1340`:** la lista permitida queda **vacía**.

## 2. Tests

- **`tests/test_core_layering_closed_v1346.py`** (nuevo, 4 casos):
  - **las rutas viejas fallan en voz alta con la nueva:** los dos módulos, y tres nombres pedidos a
    `ogr_core.statistics`;
  - las rutas nuevas funcionan, y lo puro sigue donde estaba;
  - **en ejecución, en un intérprete nuevo:**
    - se importan todos los módulos del núcleo (salvo las dos reservas);
    - se carga un modelo con malla, campo de filtración, objetos de foco y círculos del usuario;
    - se calcula lo que el núcleo calcula para el motor: la tensión efectiva y el c y φ equivalentes junto a
      un soporte, la tensión de las cargas, un DXF con su superficie crítica;
    - **en `sys.modules` no queda ningún módulo** de `ogr_slip2d`, `ogr_fem2d`, `ogr_api`, `ogr_gui`,
      `ogr_cli`, `ogr_mcp`, `PySide6` ni `mcp`.

**Con el código de 0.1.345 fallan 4 de los 8 de los dos archivos de capas.** Los tres de las rutas y el del
censo fallan; los otros tres que pasan son de v1340 y no cambian con esta versión.

El de ejecución **también pasa en 0.1.345**: las importaciones del motor de la estadística vieja estaban
dentro de funciones, y el script no lanza ningún cálculo estadístico, así que tampoco cargaba el motor. Ese
test guarda el estado final que dejan 0.1.340–0.1.346 juntas; lo que esta versión añade lo miden el censo, las
reservas y las rutas nuevas.

## 3. Verificación

- **El test de esta versión**, 4/4, y los 4 del censo de v1340.
- **Los vecinos:** 551/551: los dos censos de capas, el probabilístico, la sensibilidad y la estadística, la
  pendiente global, la reevaluación, las claves de superficie, los conmutadores de masa, la pérdida parcial de
  métodos, las variables aleatorias, los bloques, las operaciones del API, el desembalse, la interpretación,
  la pureza de superficie, las grietas, las capas del API, el esquema de ajustes y el servidor MCP.
- **Comparación A/B, árbol contra árbol, con semillas fijas:** el probabilístico configurado de 40 muestras,
  el de mínimo global de 25 y la sensibilidad de 16 puntos salen idénticos, muestra a muestra y por `repr`.
  La sensibilidad se compara por nombre de parámetro: su clave lleva el UUID del material, nuevo en cada
  corrida.
- **Suite entera:** 6391/6391, `EXIT=0`, 98 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 87 comprobaciones, 0 bajadas;
  - **`d337()`**, nueva: el censo AST de `ogr_core` (0), la carga de 02-010 `modelo_fem.ogr` (791 nodos) en un
    intérprete nuevo sin ningún módulo de encima, y las rutas viejas de la estadística. Su primera versión
    contaba `importlib` también en `sys.modules`, donde está siempre porque es la maquinaria de importación
    del propio intérprete; `importlib` se prohíbe en el código del núcleo, no al ejecutar;
  - manual 02: `verificar_cierres.py` **entero**, 238 fichas, porque esta versión mueve lo que leen muchas.
    Dio **una bajada, D103, que no viene de esta versión**: su comprobación exigía que el presupuesto de
    cadenas sin `tr()` siguiera en 210, y vale 9 desde 0.1.321, cuando P8 envolvió esas cadenas. El
    manual 02 no se había pasado entero desde entonces. Reanclada: el presupuesto no puede pasar de 210, y
    el segundo presupuesto sigue midiéndose con su barrido. D103 vuelve a «cubierto», y quedan 0 bajadas;
  - **D337 cerrada:** retirada, podada de `PAQUETES` y tachada en la fila de P8;
  - instantánea `Evaluaciones/0.1.346`, prompts (33) y auditorías con 0 ERROR.

## 4. Pendiente

- **D337 cerrada.** Siguiente: D335, los mensajes del núcleo en castellano (0.1.347–0.1.355).

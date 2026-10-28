# OGR Slip2D v0.1.374

**El runner de tests nombra el archivo que deja estado global cambiado, y eso hace fallar la corrida.**
Antes de cada archivo toma una foto del estado del proceso y, al terminarlo, otra. Lo que cambia sin una
razón escrita sale como `✗ [LEAK] clave: antes → después` bajo ese archivo, los totales añaden `Leaks: N`
y el código de salida es 1 aunque pasen todos los tests. Es la etapa 2 del plan de la auditoría de la
suite (`docs/audits/AUDITORIA_SUITE_v0.1.372.md`, §8–9). **Ningún módulo del programa cambia**, salvo el
número de versión.

## 0. Lo que se encontró

Hasta ahora la regla 5 («los tests no filtran estado») se comprobaba por suerte. Una fuga solo se veía si un
test posterior dependía de ella, y solo en la suite entera, que es el peor sitio para diagnosticarla. La
auditoría hizo esta misma comparación desde fuera y encontró tres fugas reales (D-c, D-e, D-f). Al meterla
en el runner aparecieron otras cosas, y casi ninguna era lo que parecía:

- **D-f tenía dos causas y la auditoría vio una.** El `logging` raíz quedaba configurado para el resto de la
  corrida tras `test_bridge_version_v1300`.
  - La causa vista: el constructor de `MCPServer`, de la librería `mcp`, llama a
    `logging.basicConfig(level=INFO, handlers=[RichHandler])`.
  - La otra: `ogr_mcp.cli.main` también llama a `basicConfig`, con razón, porque en su propio proceso es
    quien configura el registro.
  - `basicConfig` no hace nada una vez que la raíz tiene un manejador, así que el primero en llamar tapaba
    al segundo. Con el primero arreglado, el detector marcó el segundo.
  - Los tests llaman a los dos dentro del proceso de la suite: siete llamadas en cuatro archivos. Ahora van
    dentro de `root_logging_kept()`, que devuelve nivel y manejadores y cierra los que se añadieron.
- **`qtpy` cambia `QFileDialog` al importarse.** Lo trae QtAwesome, y sustituye los cuatro diálogos
  estáticos de `QFileDialog` por funciones Python que envuelven los de Qt (`qtpy/QtWidgets.py`).
  - Desde ese momento, guardar `QFileDialog.getOpenFileName` leyéndolo de la clase y devolverlo deja una
    función suelta donde había un `staticmethod`. Llamada desde la clase da lo mismo; desde una instancia,
    la función recibe la instancia como primer argumento.
  - `test_block4_v1202` lo hacía. Ahora guarda lo que hay en `QFileDialog.__dict__`.
  - Con un diálogo de Qt sin envolver (un builtin), las dos formas sí son equivalentes, y el detector no
    marca los ~40 archivos que restauran así.
- **El detector marcó cuatro cosas que no eran fugas de un test**, y cada una tiene su entrada razonada en
  la lista blanca:
  - **`random.state`.** `rich` saca 24 bits del generador global de `random` al importarse
    (`rich/style.py`). El programa no lo usa: cada búsqueda tiene su `random.Random` desde 0.1.119.
  - **`gc_guard._kept`.** Es basura que el colector encontró en otro hilo y espera a liberarse en el
    principal, cosa que el runner hace antes de cada archivo.
  - **`mpl.rcParams`.** El programa llama a `matplotlib.use("QtAgg", force=False)` antes de su primera
    gráfica, en siete sitios. `use()` pone **siempre** `rcParams['backend_fallback'] = False`
    (`matplotlib/__init__.py`). La entrada admite solo ese cambio y solo desde unos `rcParams` limpios:
    cualquier otra clave cambiada sigue siendo fuga, y hay un test que lo comprueba.
  - **Los diálogos de `QFileDialog`**, en el archivo donde se importa `qtpy` por primera vez.
- **Dos falsos positivos del propio detector**, corregidos en él y no en la lista blanca:
  - **`staticmethod(builtin)` frente al builtin suelto.** Muchos tests devuelven `QMessageBox.warning`
    leyéndolo de la clase. Para un builtin no hay diferencia, así que la foto los trata igual. Para una
    función Python sí la hay, como se ve en el punto de `qtpy`.
  - **El valor al importar de `misc_dialogs.VERSION`.** Un atributo de un módulo `ogr_*` importado por
    primera vez se compara con el literal que le da su fuente. `VERSION` se asigna dos veces, en un `try` y
    en su `except`, y la primera versión del detector solo miraba el nivel superior. Ahora cuenta las
    asignaciones también dentro de `if`, `try`, `with`, `for`, `while` y `match`: con más de una, el valor al
    importar es desconocido y no se compara.
- **Un camino equivocado mío, en el test del detector.** El archivo de control `test_e`, que cambia y
  devuelve todo, restauraba `QFileDialog` leyéndolo de la clase. Con `qtpy` ya importado se marcaba, y con
  razón: lo que fallaba era el control. Ahora lo devuelve desde `__dict__`, como cualquier test debe hacer.

## 1. Qué cambia

**`tests/_leaks.py` (nuevo):**

- **`snapshot()` mira:**
  - el entorno, la carpeta de trabajo, `sys.meta_path`, `warnings`, el `logging` raíz, el locale y los
    ganchos y ajustes del intérprete, `builtins`, `time`, `multiprocessing`, numpy y `random`;
  - de matplotlib, las claves de `rcParams` cambiadas, el backend y las figuras abiertas;
  - de la `QApplication`, el estilo, la hoja, la paleta, la fuente, el locale y los diálogos estáticos que
    los tests sustituyen para que no se abra nada modal;
  - el contenido de los INI de preferencias y de los archivos de puente de la corrida;
  - todos los atributos de cada módulo `ogr_*` y de cada clase que definen.
- **`diff()` cuenta como fuga:**
  - un valor cambiado o una clave desaparecida;
  - una clave nueva solo si su valor viene de un archivo de test (una función escrita en él, un `mock`) o
    si es una variable de entorno;
  - una constante de un módulo recién importado que ya no vale lo que dice su fuente.
- **`ALLOWED`** son 20 entradas, cada una con su porqué y un test que exige que lo tenga.

**`tests/_runner.py`:** foto antes de cargar cada archivo y otra en su `finally`, después de devolver
`sys.path` y las carpetas de 0.1.373. `Leaks: N` cuenta archivos, no tests, y el veredicto es 0 solo con
`Failed: 0` y `Leaks: 0`. Las fugas aparecen también en `FAILURE DETAILS`.

**Tests que pasan a devolver su estado.** Solo devolver; lo que validan no cambia.

| Archivo | Lo que dejaba | Arreglo |
|---|---|---|
| `test_dark_theme_v1316` (D-c) | el tema oscuro guardado: desde él, toda ventana de la corrida abría oscura | preferencias en una carpeta propia del bloque |
| `test_qt_translations_v1292` (D-e) | `qt_catalog._CURRENT` apuntando a un traductor ya retirado | `reset_qt_translator(app)` en vez de `removeTranslator(t)` |
| `test_mcp_server_v1195`, `test_bridge_version_v1300`, `test_live_bridge_v1203`, `test_window_by_default_v1207` (D-f) | el `logging` raíz configurado | `root_logging_kept()` |
| `test_block4_v1202` | `QFileDialog.getOpenFileName` sin su `staticmethod` | guardarlo desde `__dict__` |

**`tests/test_leaks_v1374.py` (21 casos):**

- Corre el runner sobre cinco archivos desechables. Las cuatro fugas de la verificación V1 de la auditoría
  (el idioma, una variable de entorno, `_PARALLEL_MIN_CIRCLES`, `GridSearch._centres`) hacen fallar su
  archivo y solo el suyo.
- Un quinto archivo cambia todo eso y además dos diálogos, y lo devuelve: no se marca.
- La corrida da `Passed: 5`, `Leaks: 4` y código 1.
- Las reglas de la lista blanca y el valor al importar se prueban sobre fotos sintéticas.

**Documentación:** los dos README, la regla 5 de AGENTS.md y `.claude/commands/test.md` dicen que una fuga
hace fallar la corrida aunque `Failed` sea 0.

## 2. Medida

**Primera suite entera con el detector** (2026-10-28, sin los dos arreglos de la tabla de arriba que salieron
de ella): **6653/6653 y `Leaks: 2`**, código 1, 70,9 min. Las dos fugas eran las de `test_block4_v1202` y
`mpl.rcParams` en `test_background_tasks_v1365`, el primer archivo que abre una gráfica. No apareció
ninguna más.

**Coste del detector, contado y no cronometrado.** El reloj de una suite de 70 min no distingue unos
segundos, y AGENTS.md pide contar el trabajo añadido:

- con los 258 módulos `ogr_*` importados y 9776 claves, una foto tarda unos 40 ms y la comparación 4 ms;
- son dos fotos por archivo, unos 85 ms; por 445 archivos, **unos 38 s**;
- a eso se suma ~1 s por leer una vez el código fuente de cada módulo para su valor al importar.

Una foto no guarda referencias a ningún objeto, solo cadenas, así que no retiene memoria entre archivos.

**Suite final**, la de esta versión, sin argumentos (2026-10-28): **6654/6654, `Leaks` ausente, código 0**,
74,6 min.

- **El reloj no resuelve el coste.** Las dos corridas con detector difieren entre sí 3,7 min (70,9 y 74,6)
  con el mismo código, más que la diferencia de la primera con 0.1.373 (67,5).
- Así que, como pide AGENTS.md, manda el trabajo contado: unos 40 s.
- Al terminar, `explorer.exe` gastaba un 26 % de un núcleo y el Administrador de tareas, abierto, un 13 %.
  No se sabe cuánto coincidió con cada corrida.

## 3. Qué no cambia

- **Ningún número del programa.** Solo cambian el runner, su módulo nuevo, ocho archivos de test, la versión
  y la documentación.
- **`python tests/_runner.py` sin argumentos** corre los mismos archivos, en el mismo orden. Su veredicto es
  más estricto: ahora una fuga también es un fallo.
- **Las anomalías que quedan del informe:**
  - D-b, las ventanas que siguen vivas a propósito, entra en la lista blanca como `MainWindow._sessions`;
  - D-g, `PYTHONFAULTHANDLER` con `pythonw`, es del programa y no de la suite;
  - D-h, el segfault al salir de la CI, y D-i, el registro con búfer en Linux, van en la etapa 5.

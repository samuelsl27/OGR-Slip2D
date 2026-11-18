# OGR Slip2D v0.1.472

**Los pools de cálculo, dentro de un entorno virtual.** En Windows, sin consola, dentro de un venv, el pool de
procesos de la búsqueda moría al arrancar (`BrokenProcessPool`). Toda búsqueda que se partía en varios procesos
caía a uno y lo decía. Ahora corre, y sus trabajadores calculan con los mismos árboles que el proceso que lo abre.
Fuera de un venv no cambia nada. **Ningún número cambia**: una búsqueda partida reproduce la secuencial al bit
(`test_parallel_search_v197`), y aquí solo cambia con qué intérprete arrancan los trabajadores.

Es la fase 1 de la spec 010 (`spec/features/010-adoptar-ogr-core/`), y va antes de pasar Slip2D a su propio
`.venv`, que es parte de adoptar `ogr-core` 0.2.0. Rama `dev/adoptar-ogr-core`.

Decisión de la propietaria (2026-11-18): **un contexto de `multiprocessing` propio, acotado al pool**, y no la
variable en el entorno de todo el proceso (la opción del ensayo de OGR-Core).

## 0. Lo que se encontró

### De dónde venía

Sin consola (una ventana lanzada desde un acceso directo, un trabajo de `ogr_api` con `CREATE_NO_WINDOW`, un
cliente MCP, el runner en una sesión sin terminal), `ogr_slip2d.processes` manda los trabajadores a
`pythonw.exe`, para que no abran una consola cada uno (D326, v0.1.329). Lo toma junto a `sys.executable`.

En un venv, ese `pythonw.exe` **no es el intérprete, sino un lanzador**: arranca el `pythonw.exe` del Python
base con `__PYVENV_LAUNCHER__` apuntando a sí mismo, para que el base sepa que está en el venv.
`multiprocessing` solo sabe tratar el lanzador que coincide con `sys.executable` (bpo-35797: entonces arranca él
mismo el base y pone la variable). Con el `pythonw.exe` del venv, no. Lo encontró la sesión de OGR-Core al
ensayar la fase 1 (`CHANGELOG_v0.2.0.md` de OGR-Core, §0): once tests de siete archivos fallaban en un venv, y la
huella del banco salía con una nota de más en los ocho casos que abren pool.

### Lo medido (un venv desechable, `--without-pip`, 0,4 s en crearse)

Con `diag_pool_venv.py` (`referencias/_traspaso_ogr_core_0.2.0/herramientas/`), dos trabajadores:

| Hijos con | Resultado |
|---|---|
| el `python.exe` del venv (lo que hace `multiprocessing` por defecto) | corre, dentro del venv, **con una consola por trabajador** (D326) |
| el `pythonw.exe` del venv (v0.1.471) | **el pool muere** (`BrokenProcessPool`) |
| el `pythonw.exe` del Python base | corre, pero **los hijos quedan fuera del venv** (`sys.prefix` del base): pueden importar otro árbol |
| el `pythonw.exe` base con `__PYVENV_LAUNCHER__` = el del venv | corre, dentro del venv, sin consola |

Y dos medidas que decidieron dónde poner la variable:

- **Un `python.exe` base lanzado por su ruta completa con la variable en el entorno se mete en el venv** (su
  `sys.prefix` pasa a ser el del venv). Dejarla en `os.environ` para todo el proceso, como hacía el ensayo, se lo
  haría a cualquier subproceso posterior que arranque el base.
- Los lanzadores de un venv la pisan con la suya, y el alias `python` de WindowsApps no la obedece.

Además, si el ejecutable global de `multiprocessing` apuntara al `pythonw.exe` base, **cualquier otro pool del
proceso** (algunos tests abren el suyo) arrancaría sus hijos con el base y sin la variable: fuera del venv, sin
avisar.

### El prototipo

Un `SpawnContext` cuya `Process._Popen` pone el ejecutable y la variable solo mientras crea el trabajador, y los
repone después. Probado en el scratchpad antes de tocar el programa: cuatro tareas en dos trabajadores, los hijos
con el `sys.prefix` del venv y la variable ausente en el padre al terminar.

Hay que cubrir a todos los trabajadores, no solo a los primeros. Un `ProcessPoolExecutor` con `spawn` los crea
bajo demanda, en cada `submit` (`concurrent/futures/process.py`, l. 913), y su hilo gestor puede reponer uno.
Por eso el gancho va en la creación de cada proceso, y no alrededor del pool.

### Al escribir el test

- **El juez del primer borrador no veía la consola.** Con el pool sin su contexto (mutante M6), `multiprocessing`
  arranca los hijos con el `python.exe` del venv: dentro del venv y con los árboles del padre, así que el caso
  principal pasaba. Solo lo cazaban los dos dientes, y de lado. El juez exige ahora además que cada trabajador
  sea un `pythonw.exe`, y M6 muere en el caso principal.
- **`test_console_language_demo_v1329` habría fallado en un venv por la razón equivocada.** Sus casos de
  decisión suponen que no hay venv, y uno de ellos apuntaba `multiprocessing` a mano a `child_executable()`.
  Dentro de un venv eso es el base sin lanzador, la única forma de hacerlo que deja los hijos fuera.
- **Error propio: la primera suite entera salió con 12 fallos.** `stoppable_pool` pasaba `mp_context=None`
  también fuera de un venv, y dos dobles del pool escritos con la firma de antes no aceptaban el argumento
  (`Inline` en `test_shared_pool_v1396`, `_Recorder` en `test_cancel_stops_workers_v1399`). Ningún número se
  movió: los 12 eran `TypeError` en el constructor del doble o consecuencias suyas, y los otros 8034 casos daban
  lo de la partida.
  - Por decisión de la propietaria, el arreglo va en el código: fuera de un venv la llamada vuelve a ser la de
    0.1.471, sin la palabra clave, y un caso nuevo lo comprueba.
  - **Y además en los dos dobles**, también por decisión suya: en un venv sin consola el contexto sí se pasa, y
    con el intérprete del venv desechable fallaban los mismos 12. Eso habría salido en el `.venv` de la fase 3.
    Ahora aceptan `mp_context` y lo guardan; sus invariantes no cambian.
  - Por eso se corrió también la suite entera en el venv desechable, para cazar cualquier otro doble así.
    No salió ninguno.
  - Lección: la verificación del plan corría en el venv solo los siete archivos que el ensayo vio fallar. Esos
    dos no estaban en la lista porque, en el ensayo, el pool se creaba todavía sin argumento nuevo.
- **Error propio:** el primer script de mutantes no reponía el archivo en un `finally`. Se rompió al imprimir
  (consola cp1252) y dejó `processes.py` con el mutante M1. Se repuso desde la copia buena, comprobada con `cmp`,
  y el script se rehízo con `try/finally`.

## 1. El cambio

`ogr_slip2d/processes.py`:

- `child_executable(..., base_executable=None, in_venv=None)`: los dos argumentos nuevos son para los tests. En
  un venv (`sys.prefix != sys.base_prefix`) da el `pythonw.exe` junto a `sys._base_executable`; fuera, lo de
  siempre.
- `venv_launcher()`: el `pythonw.exe` del venv, el valor de `__PYVENV_LAUNCHER__`.
- `pool_context()`: `None` salvo en un venv sin consola en Windows, donde da un `_VenvContext`. Sus trabajadores
  (`_VenvProcess`) arrancan por `_start_in_venv`, que pone el ejecutable de `multiprocessing.spawn` y la
  variable bajo un candado, crea el proceso y repone los dos en un `finally`.
- `windowless_children()`: fuera de un venv, igual que antes. **Dentro, no toca nada global.**
- `stoppable_pool()`: el pool y su `Event` se crean con `pool_context()`. Solo se pasa `mp_context` cuando hay
  contexto; fuera de un venv, la llamada es la de 0.1.471. Es el único sitio del programa que abre
  un pool, así que la búsqueda en serie, la del ámbito compartido (`pool_scope`) y la de la ventana pasan por él.

Nada de `ogr_core`, de OGR-Core ni del runner.

## 2. Los tests

**`tests/test_venv_pools_v1472.py`** (nuevo, 14 casos):
- **Las decisiones**, con carpetas falsas y sin procesos:
  - en un venv, el `pythonw.exe` base; fuera, el de antes;
  - con consola, en otro sistema o en una compilación congelada, nada;
  - sin `pythonw.exe` base, nada;
  - el contexto, solo en un venv;
  - en un venv, el ejecutable global no se toca.
- **El pool se hace como antes:** fuera de un venv, sin `mp_context`; dentro, con su contexto.
- **Un trabajador arranca con las dos cosas y después no queda ninguna**, también cuando falla el arranque, con un
  sustituto del `Popen` de `multiprocessing`.
- **Un pool real en un venv real** (solo Windows; la CI es Linux y lo salta):
  - un venv desechable cuyo `.pth` añade los `site-packages` del intérprete que corre el test, así que vale igual
    con el Python del sistema y con un `.venv`;
  - un hijo lanzado con `CREATE_NO_WINDOW` abre el pool del programa;
  - cada trabajador da el `sys.prefix` del venv, los `ogr_slip2d` y `ogr_core` del padre, y es un `pythonw.exe`;
  - **los dos dientes, como casos fijos:** con el `pythonw.exe` del venv, el juez dice «el pool murió»; con el
    base sin lanzador, dice «un trabajador está fuera del venv».

Unos 4 s el archivo: tres hijos con un pool de dos cada uno. Un pool no se prueba sin arrancar uno, y el venv se
hace una sola vez.

**Ocho mutantes, y no vive ninguno:**

| Mutante | Lo cazan |
|---|---|
| M1 en el venv, el `pythonw.exe` del venv | el caso principal (`BrokenProcessPool`) y las decisiones |
| M2 el contexto no pone la variable | el caso principal (trabajadores con el `sys.prefix` del base) y el arranque |
| M3 no repone el ejecutable | el arranque (después, y cuando falla) |
| M4 no repone la variable | el arranque (después, y cuando falla) |
| M5 en un venv, el ejecutable global apuntado | «nada global» |
| M6 el pool sin su contexto | el caso principal (una consola por trabajador) y los dos dientes |
| M7 fuera del venv, el base | las decisiones de este archivo y de `test_console_language_demo_v1329` |
| M8 `mp_context=None` siempre | «el pool se hace como antes» |

**`tests/test_console_language_demo_v1329.py`**:
- sus tres casos de decisión dicen `in_venv=False`, para que digan lo mismo con cualquier intérprete;
- la búsqueda partida «sin consola» va por el camino del programa, forzando solo la falta de consola, y no
  apuntando `multiprocessing` a mano;
- su invariante (la partida reproduce la secuencial al bit) no cambia.

**`tests/test_shared_pool_v1396.py`** y **`tests/test_cancel_stops_workers_v1399.py`**: sus dobles del pool
(`Inline`, `_Recorder`) aceptan y guardan `mp_context`, como el `ProcessPoolExecutor` de verdad. Sin eso fallaban
en un venv sin consola (§0).

## 3. Verificación

- **Los once tests de pools** (siete archivos), con el intérprete de un venv desechable
  (`--system-site-packages`, que con el Python del sistema ve este árbol) y sin consola: **96 de 96**.
  - Control con el `processes.py` de 0.1.471: fallan los mismos once que en el ensayo.
  - Además fallan, como se esperaba, los tres casos de `v1329` que ahora pasan `in_venv`, un argumento que el
    código viejo no conoce.
- Con el arreglo de §0, `test_shared_pool_v1396` y `test_cancel_stops_workers_v1399`: 17 de 17 con los dos
  intérpretes.

## 4. La suite

Las tres corridas, con `--jobs 4`, comparadas test a test con la de partida (`d48e2b3`, 8046 casos, 8044 pasan, 2
saltados) mediante `comparar_suites.py`:

| Corrida | Resultado | Frente a la partida |
|---|---|---|
| Python del sistema, primera | 8058 casos: 8044 pasan, **12 fallan**, 2 saltados | los 12 de §0; los otros 8034, igual |
| Venv desechable (`--system-site-packages`), sin consola | 8060: **8058 pasan**, 0 fallan, 2 saltados; ninguna fuga | 8046 con el mismo resultado; 14 nuevos, en verde |
| Python del sistema, tras el arreglo | 8060: **8058 pasan**, 0 fallan, 2 saltados; ninguna fuga, ningún tramo muerto | 8046 con el mismo resultado; 14 nuevos, en verde |

La última serie entera en verde es `bea135c`, de hace 53 commits: no toca aún (la siguiente, a los 100). El runner no
da la duración total, y no se midió.

## 5. Lo que queda

- **No se ha probado** la ventana real lanzada desde un acceso directo con un `.venv`: no hay `.venv` todavía. Es
  la fase 3 de la spec 010.
- **La CI no corre el pool real** (Linux, sin `pythonw.exe`): solo las decisiones y el arranque.

# OGR Slip2D v0.1.372

**Cancelar una rejilla repartida en procesos suelta su cola siempre, y no solo cuando gana una carrera con
el hilo gestor del pool (D368, abierta y cerrada en esta versión). Además, un test de 0.1.366 dejaba roja la
CI porque importaba `psutil`, que el proyecto no declara; ahora usa la biblioteca estándar, y un censo
nuevo impide que un test importe lo que la CI no instala.** Decisión de la propietaria: las dos cosas en
una sola versión, porque el test de `psutil` es el que destapó la carrera.

## 0. Lo que se encontró

- **La CI de la tanda P8l falló por un test mío.** Al subir 0.1.363–0.1.371, las tres versiones de Python
  dieron 6620 de 6623. El fallo fue
  `test_cancel_v1366.py::test_the_queue_is_cancelled_and_no_worker_is_left`, con
  `ModuleNotFoundError: No module named 'psutil'`. Los otros dos casos que faltan son los saltados de
  siempre: los tests que necesitan `pythonw.exe`, que en Linux no existe.
  - El test usaba `psutil` para ver que no quedaban trabajadores vivos tras cancelar.
  - `psutil` no es dependencia del proyecto. En la máquina de desarrollo está instalado en la carpeta de
    usuario de Python, y por eso la suite entera pasó aquí seis versiones seguidas.
- **Al quitar `psutil` salió un defecto de 0.1.366.** El cambio fue a `multiprocessing.active_children()`,
  de la biblioteca estándar, comprobado antes con un pool de 3 trabajadores. Con él el test pasó dos veces
  y luego falló tres de tres: 8 trabajadores vivos a los 30 s, y un proceso que no salía hasta que lo
  cortaba el `timeout`. Entre medias solo cambió una cosa: la otra sesión había lanzado la suite de
  OGR-FEM2D y la máquina estaba cargada.
  - **Un camino equivocado antes de eso.** Para reproducir la CI escondí `psutil` con un módulo falso en
    `PYTHONPATH`, y el test se colgó. Pareció culpa del módulo falso, pero nadie lo importaba: un registro
    dentro de él quedó vacío. Lo que cambiaba era la carga de la máquina.
- **La causa, leída en CPython** (`concurrent/futures/process.py` de 3.14):
  - al cancelar, D362 llama a `pool.shutdown(wait=False, cancel_futures=True)` dentro del bloque
    `with ProcessPoolExecutor(...)`. Esa llamada solo deja una marca para el hilo gestor del pool y olvida
    el hilo, sin esperarlo;
  - el `raise` sale del `with`, cuyo `__exit__` llama a `shutdown(wait=True)`. Esa segunda llamada vuelve a
    poner la marca en False y, sin hilo al que esperar, no espera nada;
  - el hilo gestor solo lee la marca cuando despierta. Si la salida del `with` llega antes, no cancela
    nada, y los trabajadores calculan el resto de la rejilla en segundo plano.

  El comentario de D362 decía que se esperaba a los lotes en curso. No se esperaba a ninguno.
- **Lo que veía el usuario:** tras Cancelar no se publicaba nada, y eso D362 lo cumple. Pero la CPU podía
  seguir ocupada hasta acabar la rejilla, y cerrar el programa podía esperar a que acabara.
- **Forzar la carrera hace el fallo determinista.** En el test, el hilo gestor espera 0,3 s antes de
  atender el cierre, que es lo que la carga hacía por azar. Con el modelo Ej_2 y 8 trabajadores:

  | Código | Lotes que corren tras cancelar | Trabajadores vivos al volver `run` |
  |---|---|---|
  | 0.1.371 | 49 de 49 | 8 |
  | 0.1.372, carrera forzada | 18 de 49 | 0 |
  | 0.1.372, sin forzar | 18 de 49 | 0 |

  Los 18 son los 8 lotes en marcha, los 9 que el pool tiene en cola para sus trabajadores (uno por
  trabajador y uno más) y el que acabó primero.

## 1. Qué cambia

- **`ogr_slip2d/search.py`, `_parallel_grid_run`:** al cancelar se llama a `cancel()` sobre cada futuro, en
  el propio hilo y sin depender del gestor. `cancel()` solo rechaza los lotes ya entregados a un trabajador.
  Después, `pool.shutdown(wait=True, cancel_futures=True)` espera a esos lotes y a nada más.
  - Ningún número cambia: es solo el camino de cancelar. La identidad bit a bit entre la rejilla en
    paralelo y la secuencial (`test_parallel_search_v197`, `test_window_grid_parallel_v1262`) sigue en
    verde.
- **`tests/test_cancel_v1366.py`:**
  - `psutil` cambiado por `multiprocessing.active_children()`;
  - la llamada esperada pasa a ser `shutdown(wait=True, cancel_futures=True)`. Es un cambio deliberado:
    exigía la llamada vieja.

## 2. Tests

- **`tests/test_grid_cancel_v1372.py`** (nuevo, 2 casos), con la carrera forzada:
  - solo corren los lotes ya entregados: como mucho 3 por trabajador más 2;
  - al volver `run` no queda ningún trabajador.

  **Con el código de 0.1.371 fallan los dos:** 49 de 49 lotes y 8 trabajadores vivos.
- **`tests/test_test_imports_v1372.py`** (nuevo, 3 casos):
  - **qué permite:** que cada módulo que importa un test sea de la biblioteca estándar, del repositorio,
    de una dependencia de `pyproject.toml` (la lista base y el extra `[mcp]`, que es lo que instala la
    CI), o de una lista corta que dice por qué está. En esa lista van `pytest`, que lo aporta el runner;
    `examples`; el módulo que registra `test_snap_engine`; `httpx2` y `starlette`, que trae `mcp`; y
    `cryptography`, protegido con `except ImportError`;
  - **cómo lee:** los imports, no los prueba. Un módulo que «simplemente está» en una máquina es
    invisible para cualquier corrida local;
  - **qué comprueba de sí mismo:** que ve un import dentro de un método, como el que falló, y que ninguna
    entrada de la lista se ha quedado sin uso.

  **Con el árbol de 0.1.371 falla:** `{'test_cancel_v1366.py': ['psutil']}`.

## 3. Verificación

- **Los tests de esta versión:** 5/5. Contra 0.1.371 fallan los 2 de la carrera y el censo.
- **El test de D362 sin `psutil`:** con `psutil` escondido por un módulo que lanza `ImportError`, en
  0.1.371 falla en el import, como en la CI. En 0.1.372 pasan los 22 casos de los tres archivos.
- **Los vecinos:** 88/88 en 10 archivos: la rejilla en paralelo, Cancelar, las notas de la búsqueda, los
  rechazos por límites del talud, la demo del idioma de la consola, la consistencia de versión y el test
  de tiempo de la rejilla.
- **Suite entera:** 6628/6628, `EXIT=0`, en 134 min (19:36 → 21:50). Tuvo la máquina compartida con la
  suite de OGR-FEM2D durante la primera parte. Esta vez no falló el test de tiempo de la rejilla.
- **Banco:**
  - D368, ficha abierta y cerrada en esta versión;
  - `d368()` en el `verificar_cierres.py` de la raíz fuerza la misma carrera con el modelo Ej_2. Resultado:
    corren 18 de 49 lotes con 8 trabajadores y no queda ninguno vivo, así que sale **CUBIERTO POR TEST**;
  - el verificador de la raíz, entero: 107 comprobaciones, 0 bajadas, en 36 min;
  - el del 02, en seco: los mismos veredictos que en 0.1.371. Solo cambian dos recuentos que crecen con el
    árbol: D174 cuenta 607 archivos en vez de 605 (los dos tests nuevos) y D188 cuenta 293 citas en vez de
    292;
  - después: instantánea → retirada de D368 → comentario en `PAQUETES` (no llegó a entrar en la lista) y
    D368 tachada en la cadena de P8 → prompts regenerados → auditorías de la raíz y del 02 con 0 ERROR →
    instantánea `--forzar`. Las instantáneas coinciden byte a byte: 983 de 983 en la raíz y 3284 de 3284
    en el 02.
  - Un tropiezo mío por el camino: la primera corrida del 02 la corté yo con un `timeout` de 20 min,
    cuando tarda 26. La relancé sin límite, y lo que alcanzó a escribir coincidía con 0.1.371.

## 4. Pendiente

- Mirar la CI después de subir: debería quedar sin fallos de tests, roja solo por el segfault al salir
  en Linux, ya conocido.

# OGR Slip2D v0.1.398

**Una tarea cancelada (o fallida) de la ventana suelta lo que había calculado (D382).**

Es la primera versión del plan que salió de la prueba de la interfaz de 0.1.397, hecha por Claude Desktop
(`_auditoria/P8_interfaz/INFORME_prueba_GUI_0.1.397.md`, parcial). El plan tiene seis fichas, D382–D387, abiertas el
2026-11-01 con la medida de cada una.

Ningún número del cálculo se mueve: el cambio está en la puerta de la ventana que corre las tareas en un hilo.

## 0. Lo que se encontró

- **Lo que vio la prueba (FALLO 1):**
  - ACADS 1(a) a 51×51×12 con 4 métodos en paralelo, Cancelar al 25 %;
  - la ventana pasó de 437 MB en reposo a 3298 MB y se quedó ahí, con el panel en «Todavía no hay resultados.»;
  - tras cinco cálculos, ~9 GB y la RAM de 16 GB llena.
- **Lo que había detrás, separado en tres:**
  - **El caso estaba mal dimensionado,** y el error es del prompt.
    - Cada superficie evaluada guarda sus 25 dovelas: 57,2 kB por evaluación, el 90 % dovelas
      (`_auditoria/P8_interfaz/d383_mem_eval.py`, con `tracemalloc`).
    - Un resultado completo del caso son 7,1 GB, y la ventana guarda el anterior mientras calcula el siguiente.
    - Los «9 GB» son un solo resultado, no cinco acumulados. Es D383, con revisión de diseño propia.
  - **No viene de la fase 3 de la auditoría del cómputo:** el pico de K03 en serie fue 3752 MB en 0.1.377 y 3591 en
    0.1.397.
  - **Lo que esta versión arregla:** los 3,3 GB que se quedaban tras Cancelar sin enseñar nada.
- **El mecanismo:**
  - `_TaskWorker.run` guarda la excepción en `self.error`;
  - su traceback lleva el marco de `run()`, cuyo `self` es el worker, y `run_task` la relanzaba con
    `raise worker.error`, sumando su propio marco, que también sujeta al worker;
  - los marcos del motor que lleva ese traceback guardan sus variables: los resultados ya calculados.
  - Es un ciclo, y un ciclo solo lo libera el recolector cíclico.
- **Por qué no pasaba el recolector:**
  - Python solo hace una recolección completa cuando lo nuevo supera un 25 % de lo viejo, y en una ventana ociosa no
    ocurre;
  - `gc_guard.release` solo recolecta si un hilo secundario le dejó algo guardado.
  - El resultado parcial vivía hasta el siguiente Calcular.
- **Medido** con el `run_task` real en un hilo (ACADS 1(a) a 5×5×12 en serie, cancelado en la llamada de progreso 100,
  con el recolector apagado entre el Cancelar y la cuenta):
  - 0.1.397 deja **1002 LEMResult vivos** tras el `except`, que solo suelta `gc.collect()`;
  - esta versión, **0**.
- **Desde 0.1.366 (D362),** que creó `run_task`. La misma puerta sirve a Calcular, el barrido, la estadística, el agua
  subterránea, el retroanálisis y la optimización, así que el arreglo cubre las seis.

## 1. Qué cambia

- **`ogr_gui/background.py`, `run_task`:**
  - tras esperar al hilo, saca `error` y `result` del worker y deja los dos a None;
  - relanza desde una variable local que se borra en el `finally`, como hace `concurrent.futures.Future.result`.
  - El tipo, el mensaje y el traceback de la excepción no cambian mientras la excepción viva.
- **`tests/test_task_frees_v1398.py`**, nuevo: 4 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_task_frees_v1398.py`:** `run_task` en un hilo con un `QWidget` corriente, sin `MainWindow`. Entre el
  cálculo y la comprobación el recolector va apagado, y se restaura después.
  - Una tarea cancelada: lo que calculó (un marcador con referencia débil) ha muerto al salir del `except`.
  - Un Calcular real cancelado en su segundo método, con el modelo de demostración a 3×3×3 y Bishop y Janbu
    simplificados: ningún LEMResult más que antes.
  - Una tarea que falla: lo mismo, y su mensaje llega intacto.
  - Una que acaba bien sigue devolviendo su resultado, y nada más lo retiene.
- **La discriminación:**
  - con el `run_task` de 0.1.397 fallan tres de los cuatro: «25 surface results of the cancelled Compute are alive»,
    y los dos marcadores siguen vivos;
  - el cuarto, el de la tarea que acaba bien, es una guarda y pasa en los dos.
- **Dos mutantes de medio arreglo,** cada uno cazado con 3 fallos de 4:
  - vaciar el worker pero relanzar sin el `finally`, porque el marco de `run_task` sujeta entonces la excepción en su
    variable;
  - el `finally` sin vaciar el worker, que deja el ciclo del marco de `run`.
- **La sonda** `_auditoria/P8_interfaz/d382_cancel_retiene.py`, con el `run_task` instalado: 0 LEMResult vivos tras el
  `except`.
- **La suite entera con `--jobs 4`:** **6930 de 6930, `Failed: 0`**, sin `Leaks` ni `Chunks died`. La serie no se
  repite: la versión no toca lo paralelo, y la última en verde es la de 0.1.396 (aebc2b6), un commit atrás.

## 3. El banco

- **D382–D387 abiertas** en `ERRORES_Y_DISCREPANCIAS.md` (paquete P8), cada una con su prompt largo. El siguiente
  libre pasa a D388.
- **D382 cerrada en esta versión,** CUBIERTO POR TEST.
  - `d382()` en el `verificar_cierres.py` de la raíz: el Calcular de demostración a 3×3×3, cancelado en su segundo
    método, por la puerta real en un hilo; y una tarea que falla.
  - Discriminada: con el árbol de 0.1.397 da SIGUE ABIERTO («25 LEMResult vivos tras el except; la tarea fallida
    retiene lo que calculo»), y con este da 0 y «suelta».
  - Instantáneas `Evaluaciones/0.1.398` en la raíz y en el 02, el índice de cerrados, `PAQUETES` podado, la cadena de
    P8 tachada y los prompts regenerados.
  - `auditoria_invariantes.py` sin ERROR en los dos bancos.

## 4. Lo que queda

- **El plan, en orden:** D384 (Cancelar en paralelo para a los trabajadores), D385 (el `.h5` fuera del hilo de la
  ventana), D386 (el ajuste de paralelo no caduca el resultado, si la propietaria está de acuerdo) y D387 (un análisis
  del agente se deserializa una vez).
- **Después:** la prueba a mano redimensionada a 31×31×12, y D383 con su revisión de diseño.

## Archivos

- `ogr_gui/background.py`
- `tests/test_task_frees_v1398.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.398.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`, `ogr_gui`,
  `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)

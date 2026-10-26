# OGR Slip2D v0.1.366

**Cancelar para el cálculo: no publica nada, el diálogo dice «Cancelando…» y no se cierra hasta que el
hilo ha terminado, y Calcular justo después ya no hace abortar el programa. El resultado se sella con el
modelo con que empezó la corrida, y la barra avanza durante la optimización y dice qué está haciendo
(D362, cerrada).** Cuarta versión de la tanda P8l.

## 0. Lo que se encontró

- **El plan de la tanda iba a abrir esta ficha como D368 nueva, y ya existía: era D362**, de la sexta
  prueba de la interfaz (0.1.357). Se vio al cerrar 0.1.363. No se abrió ninguna ficha, y D362 traía más
  alcance que lo planeado: no poder recalcular con el hilo vivo, la huella del modelo y la barra de la
  optimización.
- **Lo que D362 midió con `repro_d362.py`, repetido ahora como test:**
  - Cancelar cerraba el diálogo y ponía `cancelled = True`, que nadie leía. El hilo seguía y publicaba su
    resultado sellado como vigente sobre un modelo editado mientras corría;
  - Calcular otra vez sustituía `self.worker` con el primer hilo vivo, y cuando ese `QThread` perdía su
    última referencia el proceso abortaba (0xC0000409). **El test nuevo lo reprodujo sobre el árbol de
    0.1.365:** el runner murió en «Calcular otra vez tras cancelar»;
  - con una sola superficie que optimizar (Mínimo global, lo normal) la caminata no informaba de nada, y
    la barra se quedaba en el 100 %.
- **Decisión de la propietaria en la parada de diseño (2026-10-26):**
  - la parada es `TaskCancelled`, una `BaseException` lanzada desde la retrollamada de progreso que el
    cálculo ya llama, y desde puntos de parada en los bucles que no llaman ninguna;
  - ninguna firma obligatoria del motor cambia;
  - descartadas: una señal `threading.Event` pasada a una decena de funciones, y un subproceso que se
    mata;
  - y el diálogo nombra la fase de la optimización.
- **Por qué `BaseException`:** el motor rodea con `except Exception` una superficie que no se puede
  evaluar, una búsqueda que falla o un pool que no arranca, y una parada no puede contarse como una
  superficie fallida más. Se buscó en el motor: no hay `except:` desnudos, y el único
  `except BaseException` (`commands.py`) relanza.
- **Un pool que se para esperaba igual a toda la rejilla.** `_parallel_grid_run` aplazaba hasta el final
  el error de la retrollamada, y una `BaseException` salía por el `with` del pool, que espera todos los
  lotes en cola. Ahora suelta la cola (`cancel_futures`) y solo espera a los lotes que ya corren: hay ocho
  lotes por proceso, así que es una fracción pequeña de la rejilla.
- **Tres cálculos no se podían parar en su parte larga**, porque esa parte corría sin progreso:
  - la corrida determinista de la estadística;
  - la búsqueda del retroanálisis;
  - las búsquedas de las etapas del transitorio.

  Ahora reciben el progreso del que las llama. Las búsquedas de cada nivel del barrido reciben una
  retrollamada que solo comprueba la parada: la barra sigue contando niveles.

## 1. Qué cambia

- **`ogr_core/progress.py`** (nuevo), por hilo y sin Qt:
  - `progress_phase(...)` y `phase()`: la fase en que está el cálculo (`OPTIMIZE`);
  - `watching(check)` y `checkpoint()`: puntos de parada en los bucles que no informan de progreso. Sin
    vigilante instalado (la línea de órdenes, el API, los tests) no hacen nada.
- **Motor, ningún número cambia:**
  - `_parallel_grid_run` (`ogr_slip2d/search.py`): ante una `BaseException`,
    `pool.shutdown(wait=False, cancel_futures=True)` y relanzar;
  - `optimize_surface(..., progress_cb=None)`: informa por evaluación, en las dos técnicas, y sin
    retrollamada comprueba la parada. La búsqueda se la pasa cuando hay una sola superficie y anuncia la
    fase `OPTIMIZE`. `run_configured_optimization(..., progress_cb=None)` también la acepta;
  - `checkpoint()` en los bucles de Picard (permanente y transitorio) y en los del rescate (Anderson y el
    Newton de la continuación);
  - el progreso llega a la corrida determinista de la estadística, a la búsqueda del retroanálisis y a las
    búsquedas de las etapas del transitorio; el barrido comprueba la parada en sus búsquedas.
- **Ventana:**
  - `TaskCancelled` y un vigilante por cálculo en `ogr_gui/background.py`;
  - Cancelar, Esc y el botón de la barra de título piden la parada; el diálogo dice «Cancelando…», se
    queda abierto y se cierra cuando el hilo vuelve;
  - **Calcular y el barrido pasan por `run_task`**, como los cálculos de 0.1.365. `_ComputeWorker` y
    `_DrawdownSweepWorker` tienen ahora `compute(progress_cb)`, y `run()` sigue para quien los maneja;
  - un cálculo cancelado no deja nada: ni resultado, ni campo, ni paso de deshacer, ni notas. La barra
    dice «Se ha cancelado «…»: no se ha cambiado nada.»;
  - **la huella se toma al empezar** en Calcular y en Optimizar superficies
    (`_remember_results_model(fingerprint)`);
  - el diálogo dice «Optimizando la superficie crítica… n/N» en la fase de optimizar.
- **Castellano:** «Cancelando...», «Optimizando la superficie crítica...» y «Se ha cancelado «{0}»: no se
  ha cambiado nada.».

## 2. Tests

- **`tests/test_cancel_v1366.py`** (nuevo, 17 casos). Las cancelaciones las hace un apretón de manos: el
  cálculo envía un evento a la ventana y espera; la ventana, al despacharlo, pulsa Cancelar en el diálogo
  de verdad.
  - **las dos escenas de `repro_d362`:**
    - Cancelar a mitad de búsqueda para el hilo, no publica nada, el diálogo dice «Cancelling...», sigue
      abierto con el botón gris, y el modelo y el historial no cambian;
    - Calcular justo después llega al final con el FS de una corrida nueva;
  - la huella al empezar: una edición al primer progreso deja el resultado desfasado;
  - **los otros seis cálculos se paran igual y no dejan nada:** estadística, agua permanente y
    transitoria, retroanálisis, optimización y barrido;
  - la rejilla en paralelo cancela su cola (un espía de `shutdown` ve `cancel_futures=True`) y no deja
    ningún proceso;
  - la optimización con una superficie informa en la fase `OPTIMIZE`, con el total de iteraciones; el
    diálogo lo dice en castellano, y Optimizar superficies por la ventana solo emite progreso de esa fase;
  - **ningún número se mueve** con una retrollamada que nunca para:
    - la búsqueda con su caminata;
    - la filtración permanente y la transitoria, con los puntos de parada contados;
    - la estadística y el retroanálisis;
    - el barrido.

**Con el código de 0.1.365 fallan 14** y el runner aborta en el decimoséptimo, como describía la ficha.
Pasan los tres de «ningún número se mueve» que no importan nada nuevo, como deben.

## 3. Verificación

- **El test de esta versión:** 17/17.
- **Los vecinos:** 994 casos en 60 archivos (búsquedas en paralelo, optimización, progreso, Picard y
  rescate, filtración, transitorio, desembalse, retroanálisis, estadística, operaciones de agua del API,
  norma, resultados desfasados, redibujado, notas y negativas, y los tests de 0.1.363–0.1.365): 992 a la
  primera. **Dos cambios deliberados:**
  - `test_setting_refusals_v1350` cuenta los sitios donde la ventana dice una negativa por su código: de
    cinco a seis. El barrido la dice ahora en la ventana, que lo lanza por `run_task`, y el `run()` de su
    trabajador conserva la suya;
  - `test_optimize_start_v1187` sustituye `optimize_surface` por una falsa con la firma de antes. La
    búsqueda le pasa ahora `progress_cb`, así que la falsa acepta `**_kw`.

  Con los dos, 21/21.
- **Suite entera:** 6594/6594, `EXIT=0`, 99 min.
- **Banco, primera corrida de la raíz: dos bajadas, las dos de las propias comprobaciones:**
  - **`d348`** (0.1.365) buscaba como texto literal la llamada a `solve_project_groundwater`. Esta versión
    la mete en un `try`, la sangría cambia y el literal desaparece. Ahora compara el código sin espacios;
  - **`d362`** (nueva) reventaba al construir su ventana: «Internal C++ object (MainWindow) already
    deleted», en `_rebuild_window_menu` → `session_label` → `isActiveWindow()`. Medido comprobación a
    comprobación:
    - dos comprobaciones antiguas, `d334` y `d339`, destruían sus ventanas con `deleteLater()` **sin
      cerrarlas**, así que seguían en el registro del menú Ventana (`MainWindow._sessions`);
    - la destrucción diferida no ocurre hasta que corre un bucle de eventos, y el primero en correr fue
      el de `run_task` en `d348`;
    - desde ahí, cualquier `MainWindow()` nueva revienta al listar las ventanas abiertas;
    - `d334` y `d339` las cierran ahora antes de destruirlas, como los tests;
  - **hallazgo del programa, reportado y sin corregir (regla 6):** el registro de ventanas no aguanta una
    ventana destruida sin cerrar. El programa nunca lo hace (`closeEvent` la saca del registro), así que
    el usuario no lo ve, pero un script que destruya una ventana sí lo provoca;
  - segunda corrida de la raíz: 100 comprobaciones (una más, `d362`) y 0 bajadas. D362 queda **CUBIERTO
    POR TEST**. Medido allí, por la ventana real:
    - Cancelar a mitad de búsqueda: «Cancelling...», diálogo abierto, nada publicado y el modelo igual;
    - Calcular otra vez: FS 1,091433149, el de una corrida nueva y el del ejemplo de siempre;
    - una edición al primer progreso deja el resultado desfasado;
    - 301 avisos de progreso en la fase OPTIMIZE;
  - manual 02: `verificar_cierres.py` **entero** (esta versión toca el motor), 242 defectos acumulados y 0
    bajadas;
  - **D362 retirada**, podada de `PAQUETES` y tachada en la cadena de P8;
  - instantáneas `Evaluaciones/0.1.366` (raíz 983 archivos, 02 3284), prompts (40) y auditorías con
    0 ERROR.

## 4. Pendiente

- La tanda sigue con D346 (0.1.367): la nota de una superficie del usuario que no corta el terreno.
- **Prueba a mano:** la C.4 de `_auditoria/P8_interfaz/PROMPT_prueba_GUI_0.1.357.md`. Cancelar tiene que
  parar en segundos, y Calcular otra vez no puede romper nada.

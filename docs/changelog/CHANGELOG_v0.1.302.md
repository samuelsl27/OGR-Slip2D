# OGR Slip2D v0.1.302

**La suite ya no aborta al abrir un pool de procesos (D310): un guardián del
recolector de basura impide que un hilo secundario destruya objetos de Qt.**
Esta versión interrumpe la tanda P8e por decisión de la propietaria
(«diagnosticar antes de seguir»). P8e sigue en 0.1.303–0.1.305.

## 0. Lo que se encontró

- **El síntoma.** La suite entera moría sin totales ni traza, con código 127
  en Git Bash, siempre en el test 3679,
  `TestGlobalMinimumEngine.test_a_shared_seed_is_denounced`. Pasó en 2 de 5
  corridas de 0.1.300 y en 4 de 6 el 2026-10-12. El changelog de 0.1.300 lo
  leyó como «algo externo a los ~40 min», y el de 0.1.301 ya lo refutó: una
  corrida murió a los 28 min en el mismo test.
- **Qué es el 127.** En Git Bash, un proceso que termina con 0xC0000409
  (`__fastfail`, lo que hace `abort()` del CRT) da 127, y con 0xC0000005 da
  139. Lo comprobé terminando un proceso con cada código.
- **Dónde.** Con `PYTHONFAULTHANDLER=1`: «Fatal Python error: Aborted», con
  el hilo principal esperando en `as_completed` de `_parallel_grid_run`. La
  rejilla `grid=(6, 6, 8)` del test son 7 × 7 × 9 = 441 círculos, por encima
  del umbral de 400, así que abre un pool de 4 procesos. No salió ningún
  mensaje de Qt, aunque se pidió con `QT_FORCE_STDERR_LOGGING=1`.
- **La pila nativa.** `faulthandler` no la da en Windows. Para obtenerla
  escribí un manejador de SIGABRT del UCRT por ctypes, con
  `RtlCaptureStackBackTrace` y los símbolos de `dbghelp`:

  ```
  ucrtbase       abort
  VCRUNTIME140   purecall              ← llamada a un virtual puro
  Qt6Core        QObject::~QObject
  QtWidgets.pyd  (destructor de un envoltorio)
  shiboken6      BindingManager::runDeletionInMainThread
  python314      Py_HandlePending      ← una llamada pendiente
  ```
- **El mecanismo.** El recolector cíclico de Python salta en el hilo que está
  asignando memoria cuando se cruza un umbral. Aquí, en los hilos del pool:
  el que alimenta la cola y el gestor. La basura que encuentra contiene
  objetos de Qt que tests anteriores dejaron en ciclos. Una auditoría en cada
  frontera de archivo los nombró:
  - lienzos de matplotlib (`FigureCanvasQTAgg`), su `NavigationToolbar2QT`,
    sus `QAction` y un `QLabel`, de `test_chart_dialogs_v170`,
    `test_close_asks_v1296` y `test_gw_gui_v129`;
  - piezas de *Ajustes de proyecto* (`_FailureDirectionSelector`,
    `_SlopeSketch`, `QRadioButton`), de `test_parallel_search_v197` y
    `test_partial_method_loss_v1170`.

  Shiboken no puede destruir un objeto de Qt fuera del hilo principal. A
  veces lo destruye en el propio hilo secundario: medido aparte, un
  `QDialog` recogido en un hilo se destruye allí, y Qt lo prohíbe para un
  widget. Otras veces aplaza la destrucción al hilo principal, y ahí
  `~QObject` llamó a un virtual puro.
- **Por qué es aleatorio.** Depende de si una recolección de generación 2
  cae en un hilo del pool mientras hay basura de Qt. Una corrida que cazaba
  esas recolecciones (sin liberar nada) vio cinco en hilos secundarios, sin
  Qt, y pasó.
- **Lo que no lo reproduce por separado** (seis intentos sintéticos):
  - 6 GB de lastre en memoria;
  - 300 `MainWindow` sueltas: no son basura, porque las retienen las
    conexiones de C++, y `gc.collect()` da 0;
  - los archivos que dejan basura de Qt, recogida en un hilo y procesada
    después en el principal.

  Hacen falta el estado y el orden de toda la suite.
- **El programa tiene el mismo riesgo.** El hilo de cálculo
  (`_ComputeWorker`) y los hilos del pool ejecutan Python, y una ventana de
  gráficas cerrada puede ser basura cíclica.
- **Aparte, la memoria.** La suite acaba ocupando 7,7 GB privados con 10157
  widgets de primer nivel vivos:
  - 2,85 GB los dejan 101 archivos con ventanas que se cierran pero nunca se
    destruyen, a unos 2,7 MB por ventana;
  - 4,8 GB los retienen archivos sin ventanas: `test_acads_validation` 1 GB,
    `test_published_cases` 686 MB, `test_validation_cases` 682 MB…

  No se toca en esta versión.
- **Otro test frágil,** visto con la máquina muy cargada:
  `test_api_jobs_v1194::test_progress_is_written_and_ends_complete` leyó el
  progreso de un trabajo antes de que terminara. No se toca.
- **Un proceso abortado** se quedó a medio desmontar reteniendo 4 GB, y ni
  `taskkill` lo cerró. Al abortar quedan siempre 4 trabajadores
  `spawn_main` huérfanos.

## 1. Qué cambia

- **`ogr_gui/gc_guard.py`** (decisión de la propietaria, 2026-10-13):
  - un callback de `gc` hace que una recolección que empieza fuera del hilo
    principal guarde lo que encuentra (`DEBUG_SAVEALL`, solo para esa
    recolección) en lugar de liberarlo;
  - `release()`, llamado en el hilo principal, deja que una recolección allí
    lo libere, y llamado fuera no hace nada;
  - no importa Qt.
- **La ventana** instala el guardián al crearse y llama a `release()` cada
  2 s con un `QTimer`.
- **El runner** (`tests/_runner.py`) instala el guardián tras comprobar el
  árbol, y antes de cada archivo hace `release()` y `gc.collect()` en el hilo
  principal.
- **Sin `WA_DeleteOnClose`** en las ventanas de gráficas: borra con
  `deleteLater`, y los borrados aplazados son lo que se sospecha del segfault
  de la CI de Linux al cerrar el intérprete.

## 2. Tests

`tests/test_gc_guard_v1302.py`, 6 casos:
- **con el guardián,** un `QDialog` en un ciclo, recogido en un hilo
  secundario, NO se destruye aunque el hilo principal ejecute Python (que es
  cuando corren las llamadas pendientes de shiboken). Se destruye al llamar a
  `release()`, en el hilo principal: el `QSignalSpy` cuenta 1 y el slot de
  un receptor vivo se ejecuta en directo;
- **el control, sin el guardián:** la recolección del hilo destruye el
  diálogo allí mismo. El espía cuenta 1 antes de que el hilo principal haga
  nada, y el receptor solo se entera por una llamada en cola;
- **el temporizador de la ventana,** movido por el bucle de eventos, libera
  en el hilo principal lo que encontró un hilo secundario;
- `release()` fuera del hilo principal no hace nada;
- la ventana instala el guardián y su temporizador;
- el runner lo instala y libera antes de cada archivo.

**Lo que enseñó la primera suite entera.** La primera versión de estos
tests procesaba los eventos antes de comprobar que el diálogo seguía vivo, y
falló en la suite completa, aunque pasaba sola. Una ventana que un test
anterior dejó viva tenía su temporizador de liberación, y `processEvents()`
lo disparó: liberó el diálogo en el hilo principal. Es justo lo que debe
hacer el guardián. El test ya no procesa eventos en ese punto, y el caso del
temporizador fija ese comportamiento.

Con el código de 0.1.301 fallan los 5 casos de entonces, al importar
`ogr_gui.gc_guard`. Se corrió sobre un `git archive` de HEAD sin el buscador
editable. El control fallaría solo por esa importación: el comportamiento
que vigila es el antiguo.

## 3. Verificación

- **Las 4 corridas parciales** (los 223 archivos hasta el test, unos 30 min
  cada una), con el guardián: 4 de 4 limpias, 3690/3690 y código 0.
  - Sin el guardián abortaron 4 de 6 ese día.
  - Si el arreglo no hiciera nada, la probabilidad de 4 limpias por azar
    sería de un 6 %. Fue el criterio que fijó la propietaria.
  - Llegaron al archivo del aborto en 1788 s, frente a 1604 y 1900 s sin el
    guardián: el `gc.collect()` antes de cada archivo no se nota en el reloj.
- **Suite entera:** 5980/5980, código de salida 0, a la primera, pasando por
  el test del aborto. Una corrida anterior se descartó por el test mal
  planteado que se cuenta en §2.
- **Lo que no se ve en estas corridas:** un aborto que siguiera ocurriendo con
  menos frecuencia. Se vigilará en las suites de P8e.

## 4. Pendiente

- P8e, 0.1.303–0.1.305 (deshacer: materiales y agua, cargas y soportes, el
  resto y D306).
- La memoria de la suite (7,7 GB) y el test frágil de `test_api_jobs`: se
  anotan, no se abren como fichas.
- D307–D309, después de P8e.

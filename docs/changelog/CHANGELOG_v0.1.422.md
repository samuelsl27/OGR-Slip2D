# OGR Slip2D v0.1.422

**La suite vuelve a terminar por la finalización normal del intérprete en todas las plataformas, y la CI de Linux
sale con 0. El runner borra antes las ventanas sin padre que dejaron los tests, que en Linux hacían reventar el
desmontaje de PySide (D370). Y un test que mataba la suite entera en Linux arranca su proceso en su propia sesión
(D394).**

Es la sexta y última de la tanda P8o. **Decisiones de la propietaria en la PARADA de D370 (2026-11-04):**
- el arreglo va en el runner;
- el runner vuelve a `sys.exit` también en Linux, si la CI sale con 0 en las tres Pythons;
- D394 se abre y se cierra en esta misma versión;
- D395 se abre y se mide antes de decidir.

Ningún número del programa cambia. El final de Windows es el de siempre.

## 0. Lo que se encontró

El diagnóstico se hizo en la rama `dev/d370-shutdown`, con permiso de la propietaria para subirla, en cuatro vueltas
de la CI. Ninguna tocó `main`.

- **Vuelta 1 (run 41691202835):**
  - **el programa real sale con 0 en Linux**, con el puente y sin él (`tests/_d370_app.py`: el demo, Calcular,
    Interpretar, cerrar). A un usuario que cierra OGR en Linux no le pasa;
  - de ocho tramos alfabéticos, tres mueren con 139 tras el aviso «QObject: shared QObject was deleted directly»;
    uno muere con 134; los demás salen con 1 por la fuga de `locale` de Linux (D378);
  - un manejador de mensajes de Qt captura el aviso, pero la pila de Python en ese instante está vacía: es
    desmontaje de C++;
  - **la suite entera no termina**, ni bajo gdb ni sin él: el paso de la CI se queda sin conclusión y sin registro.
    Así nació D394.
- **Vuelta 2 (run 41703110167):**
  - con el test de D394 arreglado, la suite entera llega al final;
  - **gdb da la pila del 139:** `Py_FinalizeEx` → `atexit` → `PySide::destroyQCoreApplication` →
    `Shiboken::BindingManager::visitAllPyObjects` → `QObject::~QObject`. Al salir, PySide borra uno por uno los
    objetos envueltos que siguen vivos, y uno lo sujeta además un `QSharedPointer` de Qt;
  - la bisección cierra el 139 en dos octavos;
  - **el 134 era otra cosa:** «Fatal Python error: none_dealloc», en Python 3.11. Así nació D395;
  - borrar a mano, con Python vivo, las ventanas sin padre de un tramo que moría quita el aviso.
- **Vuelta 3 (run 41707080912):**
  - archivo por archivo, mueren solos `test_assign_water_surface_v195.py` y `test_transient_no_stages_v1306.py`;
  - y el contador de `None` en 3.11: ver D395.
- **Vuelta 4 (run 41711115938):** test por test, en Python 3.12 (para que no se mezcle el 134), mueren solos cinco:
  tres de `test_assign_water_surface_v195` y dos de `test_transient_no_stages_v1306`.
  - Todos dejan vivo un diálogo SIN PADRE (`AssignWaterSurfaceDialog`, `TransientStagesDialog`) con `lambda`
    conectadas a sí mismo: un ciclo que lo mantiene hasta el `atexit` de PySide.
  - Tests vecinos que hacen lo mismo no mueren: depende de si el recolector lo libera antes.

## 1. Qué cambia

- **`tests/_runner.py`:**
  - `_release_windows()` borra con `shiboken6.delete`, antes del final y con Python vivo, cada ventana sin padre
    que siga viva, y cada una se lleva a sus hijos en el orden de Qt.
    - Solo las que no tienen padre: un menú desplegable también es una ventana de primer nivel, pero es de su
      ventana. Medido al escribir la sonda: borrar los menús antes que su ventana reventaba en Windows.
    - En una corrida que nunca importó Qt no hace nada.
  - **El final:** `sys.exit(código)` en todas las plataformas, como hasta 0.1.376. El `os._exit` de Linux de
    0.1.377 se va, por decisión de la propietaria: un fallo futuro al cerrar vuelve a verse en la CI.
- **`tests/test_runner_shutdown_v1377.py`:** con el final nuevo, un fallo inyectado al cerrar se ve en todas las
  plataformas (`_ENDS_ITSELF = False`), y los totales se siguen escribiendo antes. Es un **cambio deliberado**.
- **`tests/test_slice_store_parallel_v1409.py` (D394):** el proceso del test arranca en su propia sesión
  (`start_new_session` en POSIX), como un trabajador de `JobManager`.
- **`tests/test_test_imports_v1372.py`:** `shiboken6` entra en `_ALLOWED`. Es el tiempo de ejecución de las
  ligaduras de PySide6, que lo instala con él.
- **`tests/test_shutdown_release_v1422.py`,** nuevo, con 4 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. La corrida de la CI que cierra D370

- **Run 41798317380,** en la rama `dev/d370-shutdown` (7d88eb1). Es el código de 0.1.416 ya subido (`origin/main`)
  con solo los arreglos de esta versión, y el flujo de la CI de siempre: la suite entera en serie en Python 3.11,
  3.12 y 3.13. La base es 0.1.416 para no publicar en la rama los commits de la tanda que aún no están subidos.
- **Las tres salen con código 1, no con 139.** En ninguna aparece «QObject: shared QObject was deleted directly»
  ni un segfault: el desmontaje es limpio, y el código es el veredicto de los tests.
  - **3.11:** 7054 tests, 7051 pasan, 2 saltados, 1 fallo. El fallo es mi test del subproceso: en Linux, ese
    proceso también tropieza con la fuga de `locale` y sale con 1. Está corregido en esta versión.
  - **3.12:** 7050 pasan, 2 fallos: el mismo test y `test_child_model_v1388::test_the_same_sequence`.
  - **3.13:** 7051 pasan, 1 fallo, el mismo test.
  - **En las tres,** la fuga de `locale` de la primera `QApplication` en Linux (**D378**, abierta) hace salir con 1
    de todas formas.
- **Decisión de la propietaria (2026-11-04),** ante esto:
  - D370 se cierra con esta evidencia, y su criterio se re-ancla: «salida 0 en las tres» no se puede cumplir
    mientras D378 siga abierta;
  - el runner vuelve a `sys.exit` también en Linux, así que lo que la CI dé desde ahora es el veredicto de los
    tests, y un fallo al cerrar volvería a verse.
- **Hallazgo sin ficha, para la propietaria:** `test_child_model_v1388::test_the_same_sequence` falla a veces en
  Linux. Identifica los modelos por `id(m)`, y un modelo que se reconstruye libera el viejo, cuya dirección puede
  reutilizar el nuevo: 3 distintos en vez de 4. Es la trampa conocida de `id()` reutilizado (memoria «trampas al
  censar por superficie»). No se toca aquí.

## 3. Qué se probó

- **`tests/test_shutdown_release_v1422.py`,** con 4 tests:
  - `_release_windows`, en un proceso aparte (llamarla dentro de la suite borraría ventanas que otros archivos
    guardan), borra un diálogo sin padre que un ciclo mantiene vivo y una ventana principal, y el menú
    desplegable de esa ventana se va con ella;
  - **el runner de verdad,** sobre uno de los tests que en Linux morían solos con 135
    (`test_assign_water_surface_v195 -k test_select_all_and_clear_all`), sale con 0 y sin «shared QObject». En
    Linux acepta 1 solo si lo causa la fuga de `locale` de D378;
  - cada `Popen` de `test_slice_store_parallel_v1409.py` arranca en su propia sesión, leído con el AST;
  - **en POSIX,** cancelar un trabajo cuyo proceso tiene sesión propia deja vivo al que llama. En Windows se salta.
- **Cambiado a propósito:** `test_runner_shutdown_v1377`. Con el final nuevo, el fallo inyectado al cerrar se ve
  en todas las plataformas.
- **La suite entera con `--jobs 4`, en Windows:** **7103 pasan y 1 se salta** (el de POSIX), `Failed: 0`, sin
  `Leaks` ni `Chunks died`, `EXIT=0`. Borrar las ventanas antes de salir no rompe los tramos en Windows: el
  0xC0000005 de 0.1.377 era de `os._exit`, que aquí no se usa.
- **La serie,** porque el arreglo toca cómo se liberan los objetos de Qt al salir: **7103 pasan, 1 saltado**,
  `Failed: 0`, `EXIT=0`, y queda apuntada como la última serie en verde.
  - El runner avisa de que `test_points_table_v1371.py` tardó 173 s en serie y no está en `tests/_slow.txt`. No es
    de esta tanda; queda dicho para quien reescriba la lista.
- **El banco:**
  - D394 y D395 se abren en el `ERRORES` de la raíz, con su paquete (P8) y su lugar en la cadena. D395 lleva prompt
    largo.
  - `d370()` y `d394()`, nuevas en el `verificar_cierres.py` de la raíz. Leen el código del runner y del test, el
    changelog (la corrida 41798317380, sin 139 en las tres Pythons, y la decisión) y que los tests existan. Las dos
    dan CUBIERTO POR TEST.
    - Las dos leen el código del repositorio vivo, así que discriminarlas contra el árbol anterior no tiene sentido.
      Lo que separa los dos árboles es la corrida de la CI de arriba y los tests.
  - El VC de la raíz entero da 133 comprobaciones con 0 bajadas.
  - El del 02 en seco da 242 de 242 iguales a los archivados.
  - D370 y D394 se cierran:
    - instantánea y retirada de las dos;
    - `PAQUETES` podado y la cadena tachada;
    - 35 prompts, con las 17 FALTA anteriores; P8 queda con D371, D378 y D395;
    - auditorías con 0 ERROR;
    - instantánea `--forzar`.

## 4. Qué queda abierto

- **D378:** la fuga de `locale` de Linux, que hace salir con 1 a toda corrida de la CI.
- **D395 (nueva):** en Python 3.11 con PySide6 6.12.0, `setPen` de `QGraphicsLineItem` y `QGraphicsRectItem` resta
  una referencia a `None` en cada llamada. Un redibujado del ejemplo se come unas 1500, y la sonda abortó
  (`none_dealloc`). En 3.12 o más no pasa. Por decisión de la propietaria se mide antes de decidir: qué versiones
  lo tienen, y si el programa aborta de verdad en una sesión. Tiene su prompt largo.
- **La rama `dev/d370-shutdown`** queda subida y sin integrar. Lleva las sondas (`_d370*.py`) en su historia, para
  medir D395. Qué se hace con ella lo decide la propietaria.

# OGR Slip2D v0.1.365

**Calcular estadística, Calcular agua subterránea (permanente y transitorio), el retroanálisis y
Optimizar superficies corren fuera del hilo de la ventana, con un diálogo de progreso, y la ventana
responde mientras calculan (D348, cerrada).** Tercera versión de la tanda P8l.

## 0. Lo que se encontró

- **La «ventana oscura» de la quinta prueba de la interfaz es el fantasma de «No responde» de Windows, no
  consolas.** Medido antes de tocar nada (regla 6), en el escritorio real y sin consola (`pythonw`), con el
  código de 0.1.364 (`_auditoria/P8_interfaz/D348_ventana_colgada_0.1.364.json` y su script):
  - Calcular estadística del talud de ejemplo, 50 muestras: 13,1 s en el hilo de la ventana;
    `IsHungAppWindow` dice que la ventana está colgada en 35 de 45 muestras, desde los 2,7 s;
  - aparece una ventana de clase `Ghost`, propiedad de `dwm.exe`, titulada «OGR Slip2D v0.1.364 — Demo
    slope (No responde)»: la que Windows pinta encima de una ventana que no atiende sus mensajes;
  - los 8 procesos hijo del pool de la rejilla son `pythonw.exe` (D326) y no abren ninguna ventana.
- **Los cuatro cálculos son largos.** En el ejemplo y en esta máquina: la estadística 13,1 s, el
  retroanálisis 6,2 s y Optimizar superficies 9,1 s (sus 4000 iteraciones por defecto, sobre la superficie
  no circular del modelo de los tests). Los tres pasan de los 5 s a partir de los cuales Windows pone el
  fantasma, así que los cuatro van al hilo, como pedía la ficha si se confirmaban.
- **Dos errores míos al medir, que cuento porque el primero dio una medida falsa:**
  - el vigilante leía los títulos con `GetWindowTextW`. Sobre una ventana del propio proceso, eso **envía**
    `WM_GETTEXT` al hilo de la ventana, que estaba calculando, y el vigilante esperó: una muestra en 110 s.
    Ahora usa `InternalGetWindowText`;
  - el script no tenía la guarda `if __name__ == "__main__":`. Los hijos del pool arrancan con *spawn* y
    vuelven a ejecutar el módulo principal, así que cada uno abrió su propia ventana y calculó su propia
    estadística. De ahí salieron unos 108 s y ventanas «OGR Slip2D» de `pythonw.exe` que no eran de OGR.
- **Con el código nuevo, en el escritorio real** (`D348_dos_corridas_0.1.365.json`): dos estadísticas
  seguidas, con la ventana de estadística abierta entre una y otra, como haría un usuario. Ninguna muestra
  colgada (0 de 46 y 0 de 45), ningún fantasma, y la ventana despacha durante cada cálculo 2314 y 2301 tics
  de un temporizador de 5 ms y 21 387 y 21 333 eventos encolados.
- **Una rareza de la plataforma sin pantalla, que decidió cómo mide el test.** En «offscreen», una vez
  mostrada en el proceso una ventana de estadística, el hilo de la ventana no consigue turno del GIL
  mientras otro hilo ejecuta Python puro. Es la segunda corrida en adelante: 0 tics en 1,5 s, ni con un
  bucle vacío en lugar del cálculo. Se acotó así:
  - no es el intervalo de cambio del GIL, ni el recolector, ni `gc_guard`, ni un hilo de Python de más, ni
    las señales de progreso, ni la modalidad del diálogo;
  - sin la ventana de estadística, o con un lienzo de matplotlib suelto, sí hay tics.

  En el escritorio real no pasa (la medida de arriba), y por eso no se persiguió más. El test no cuenta tics
  de un temporizador: hace un **apretón de manos**. Al empezar, el cálculo envía un evento a la ventana y
  espera a que esta lo despache. Esperando suelta el GIL, y eso solo se cumple si el bucle de la ventana
  corre durante el cálculo.
- **El transitorio cambia el agua del proyecto vivo en cada etapa** (`with_stage_water`): un lector a mitad
  de cálculo (el agente, la comprobación de resultados desfasados) vería otro modelo. Por eso el agua se
  calcula sobre una copia desacoplada y el campo se escribe de vuelta en el hilo de la ventana, como ya
  hacía `groundwater_run` del API. La estadística, el retroanálisis y la optimización solo leen el
  proyecto: muestrean sobre copias o trabajan sobre la copia factorizada, así que usan el vivo, como hace
  *Calcular*.

## 1. Qué cambia

- **`ogr_gui/background.py`** (nuevo):
  - `run_task(window, fn, title)` ejecuta `fn(progress_cb)` en un `QThread` y espera en un `QEventLoop`
    local, con el diálogo de progreso delante;
  - **devuelve el resultado** o relanza la excepción en el hilo de la ventana, así que cada manejador
    conserva su forma (el paso de deshacer del agua incluido) y una negativa `AnalysisNotConfigured` llega
    a su cuadro de siempre;
  - sin pantalla (plataforma «offscreen», el precedente de `_ask_unsaved`), `fn(None)` corre en línea, como
    antes: los 51 sitios de los tests que llaman a estos manejadores y leen el resultado en la línea
    siguiente, y `d341` del banco, no cambian. `window._tasks_threaded = True` fuerza el hilo.
- **`TaskProgressDialog`** (`ogr_gui/dialogs/misc_dialogs.py`):
  - modal de aplicación, para que el modelo no se pueda editar mientras otro hilo lo lee;
  - **no se cierra** (Esc, el botón de la barra de título) hasta que el cálculo ha vuelto;
  - sin botón Cancelar hasta que un cálculo se pueda parar de verdad (D362, la siguiente versión): un botón
    que no hace nada es peor que no tenerlo (regla 7);
  - barra indeterminada hasta que llega un total.
- **`ogr_gui/main_window.py`:**
  - las cinco puertas (`run_configured_statistics`, `run_configured_back_analysis`,
    `run_configured_optimization`, `run_transient_stability`, `solve_project_groundwater`) van por
    `run_task`;
  - el agua se calcula con `_field_copy`/`_take_field`: los cinco atributos que escribe el solver
    (`seepage_result`, `transient_results`, `transient_initial_result`, `_fea_ponding_cache`, `_gw_solver`)
    vuelven todos o ninguno. Un estado refusado a mitad, en la búsqueda de una etapa, conserva el campo, como
    siempre;
  - el comentario de `_DrawdownSweepWorker` dejaba la estadística como ejemplo de lo síncrono; ahora dice
    que ya no lo es.
- **`ogr_gui/agent_bridge.py`:** `busy()` cuenta también `task_worker`, así que el agente recibe Busy ante
  una edición mientras calcula cualquiera de los cuatro.
- **Ningún número cambia:** por el hilo y en línea, el mismo resultado al bit, en los cinco cálculos.

## 2. Tests

- **`tests/test_background_tasks_v1365.py`** (nuevo, 9 casos):
  - **por el hilo y en línea, el mismo resultado al bit**, cada uno sobre su propio modelo, con el
    apretón de manos (el cálculo corre en otro hilo, la ventana despacha durante el cálculo, el diálogo es
    el widget modal y el puente dice Busy):
    - la estadística: cada valor de cada muestra, la probabilidad de rotura, el índice de fiabilidad y las
      notas;
    - el agua permanente;
    - el transitorio: las alturas y los FS de cada etapa y del estado inicial;
    - el retroanálisis: la fuerza necesaria, la activa, la pasiva y el FS sin soporte;
    - la optimización: el FS y los vértices de la superficie;
  - el agua sigue siendo **un** paso de deshacer que marca el proyecto como modificado, y el campo del
    proyecto es el que se calculó sobre la copia (con un espía, no es el proyecto vivo);
  - una negativa lanzada en el hilo llega al cuadro de la ventana;
  - el diálogo no se cierra antes de tiempo y no tiene un Cancelar que no cancela;
  - sin pantalla, el cálculo corre en línea con `progress_cb=None`, que es la llamada de antes.
  - **Comparar sin identificadores:** el primer intento comparaba el diccionario de la superficie y las
    claves de las muestras, que llevan UUID nuevos en cada modelo construido. Ningún número difería.

**Con el código de 0.1.364 fallan los 9.**

## 3. Verificación

- **El test de esta versión:** 9/9.
- **Los vecinos:** 562/562 en 34 archivos: la estadística, el agua y el transitorio, deshacer, el
  retroanálisis y la optimización, las notas de 0.1.363, el puente del agente, el castellano, el tamaño de
  los diálogos, las capas y las licencias.
- **Suite entera:** 6577/6577, `EXIT=0`, 105 min.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 99 comprobaciones (una más, `d348`), 0 bajadas. D348 queda
    **CUBIERTO POR TEST**:
    - leído en el código: las cinco puertas van por `run_task`, el agua sobre una copia y el puente cuenta
      el hilo;
    - medido allí, por la ventana real con el hilo forzado: un retroanálisis de verdad del ejemplo corre en
      otro hilo, la ventana despacha un evento mientras calcula, el diálogo es el modal, el puente dice Busy
      y la fuerza es la del cálculo en línea (40,4349);
    - y la medida archivada del escritorio real: con 0.1.364, colgada 35 de 45 muestras y 2 fantasmas de
      `dwm.exe`; con 0.1.365, dos corridas sin colgarse;
  - manual 02: `verificar_cierres.py --seco`, 238 veredictos iguales;
  - **D348 retirada**, podada de `PAQUETES` y tachada en la cadena de P8;
  - instantáneas `Evaluaciones/0.1.365` (raíz 983 archivos, 02 3284), prompts (41) y auditorías con
    0 ERROR.

## 4. Pendiente

- La siguiente versión es **D362** (0.1.366): que Cancelar pare de verdad. Su prompt pide presentar antes
  el diseño de la parada con sus alternativas.
- **Prueba a mano:** el transitorio de la quinta prueba (talud de ejemplo con filtración por elementos
  finitos, alturas 22 y 12, dos etapas a 60 y 3600 s con FS), con la ventana respondiendo y su diálogo.

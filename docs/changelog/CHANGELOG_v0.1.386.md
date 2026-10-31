# OGR Slip2D v0.1.386

**Dos cambios en una versión, por decisión de la propietaria.**
- **V8:** una rejilla con foco abre el pool de procesos para los círculos que va a resolver, no para los que nombra.
  Es la octava versión de la fase 3 de la auditoría del cómputo (`docs/audits/AUDITORIA_COMPUTO_v0.1.377.md`).
- **El progreso de la ventana:** el diálogo recibe una señal por porcentaje, no una por llamada.

**Lo medido en K04** (banco 078, caso 3b; una tangente deja 43 de 13 671 círculos por método; cuatro métodos), en
procesos nuevos y en orden ABBA:
- con un pool por método, 2,45 s;
- en serie, 0,99 s más 0,16 s del recuento: **−53 %**;
- en el banco de pruebas, de 2,37 s (el código de 0.1.385, puerta de hoy) a **1,12 s**;
- los resultados, idénticos en todas las corridas.

Clase A: no toca la aritmética. Lo demuestran la huella de los 23 casos, 23 de 23 idénticos a 0.1.377, y serie igual a
paralelo en los 12 casos con pool. De los 23, solo K04 cambia de camino. En el manual 02 del banco cambian seis
rejillas de 145: 060, 078 1b, 2b y 3b, 079-1 y 081-1.

## 0. Lo que se encontró y lo que se decidió

- **La puerta de medida.** K04 se reprodujo: abre un pool por método para 43 círculos, y el pool lo hace 2,4 veces
  más lento que la serie. K05 (062 Ru 0,5, foco de punto) deja 720 círculos y conserva su pool.
- **Antes de escribir nada, la medida cambió el diseño del plan en dos puntos:**
  - **La ventana.** Su prueba toma 72 puntos de cada círculo: 67 µs por círculo, frente a 3 µs de un punto, una línea
    o una tangente. Recorrerla es, por tanto, trabajo que el pool reparte. Con una ventana que deja 150 círculos en la
    rejilla de K04, hoy se tarda 7,5–8,7 s y con el recuento serían 13,8 s (+60 a +80 %). **Decisión:** la ventana se
    queda con la regla de antes.
  - **El precio cerca del suelo, más alto que en el plan.** En la rejilla de K04, el pool de hoy frente a la serie de
    V8:
    - Bishop: −44 % con 146 círculos y ≈ 0 con 348;
    - Spencer: +33 % con 146 y +48 % con 348 (el plan decía «hasta +35 %»);
    - Bishop con Ky: +27 % con 348.

    Es lo que ya cuesta hoy una rejilla sin foco de menos de 400 círculos. **Decisión:** el suelo se queda en 400.
- **La primera revisión** (seis lentes y dos verificadores por hallazgo; ningún hallazgo refutado):
  - **V8 sin cotas hacía más lentas rejillas que hoy van bien.** El recuento y la corrida en serie recorren la rejilla
    dos veces, y el pool repartía ese recorrido. Con los resultados idénticos:
    - 316 000 círculos con foco: 4,5–5,1 s frente a 2,2;
    - 1,25 millones: 13,5 s frente a 4,0;
    - dos ventanas de límites sobre un perfil de 206 puntos: de 5,5 a 8,8 veces más lento, porque la horquilla de
      radios con dos ventanas crece con el cuadrado de los segmentos.

    **Decisión:** contar solo donde recorrer es barato (abajo, «Qué cambia»).
  - **El recuento no tenía punto de cancelación.** En una rejilla de 200 × 200, Cancelar esperaba sus 6–10 s. Ahora
    cada centro es un `checkpoint`, como pide la regla de D362 para los bucles que no informan de progreso.
  - **La ventana se inundaba de señales** con una rejilla en serie: una por centro, sin límite, frente a una por lote
    (32 por método) con el pool.
    - **Medido:** en K04, tirones de hasta 0,18 s, frente a 0,03 con pool. En una rejilla de 200 × 200 con foco, la
      ventana se congeló hasta 7 s, y un Cancelar pulsado a los 20 s se leyó a los 26, con el cálculo terminado, así
      que el resultado se publicó.
    - **Ya pasaba antes de V8**, con la búsqueda en paralelo apagada, en máquinas de 1 a 3 procesadores o cuando el
      pool falla. V8 lo extendía a las rejillas con foco.
    - **Decisión:** arreglarlo en esta versión.
  - **D381, anterior a V8** (regla 6). Un resultado calculado en el proceso guarda en sus dovelas los mismos objetos
    `Material` del proyecto vivo; con pool eran copias.
    - Una edición en el sitio (el `material_set` del agente, un script) cambia lo que enseña Interpretar junto al
      factor viejo.
    - Tras Deshacer, la marca de caduco desaparece y siguen saliendo los valores editados.
    - **Decisión:** ficha D381 y una versión propia, justo después de esta.
  - **Menores:** ningún test comparaba una rejilla con foco por un pool real frente a la serie; un objeto de foco que no
    fuera `FocusObject` reventaba; la frase de AGENTS.md y varios comentarios decían más o menos que el código.
- **La segunda revisión**, sobre el diseño acotado: tres lentes. El revisor de contratos y los verificadores de
  rendimiento no terminaron por el límite de uso de la sesión, así que sus hallazgos de rendimiento son medidas del
  revisor sin una segunda verificación.
  - **Un perfil denso dentro de las cotas.** Con 100 puntos de perfil, 1000 centros y Bishop simple, V8 iba entre un
    13 y un 30 % más lento con 185–390 círculos. Parte es el segundo recorrido; parte, que un perfil denso encarece
    cada evaluación (4,1 ms frente a 2,1–2,5 con 7 puntos). Con 7 puntos, la misma rejilla iba más rápida que el pool.
    **Arreglo:** la cota del perfil baja de 100 000 a **20 000** y se mide con los vértices del contorno exterior.
  - **La envolvente del terreno.** La cota del perfil se medía con `_slope_surface`, y con la caché fría eso construía
    la envolvente en el padre aunque luego se abriera el pool. Las puertas del programa ya la calientan antes; los
    vértices del contorno no la necesitan.
  - **Un recuento que llega a 400 tarde** recorre casi toda la rejilla antes de abrir el mismo pool. Dentro de las
    cotas son menos de 0,1 s. Queda escrito.
  - **Tests:** faltaban una sola ventana de límites, la identidad de la corrida que deja el recuento (notas y
    contadores) y una cota de objetos que no contara los desactivados. **Textos:** un docstring falso, la frase de
    AGENTS.md y tres cifras distintas para el arranque del pool.
  - **Lo que miré a mano en lugar del revisor de contratos:** los siete `run_task` de la ventana. Ninguno se rompe con
    el límite de progreso:
    - Calcular acumula a lo largo de los métodos;
    - la estadística cambia de total entre la corrida determinista y las muestras;
    - el transitorio vuelve a 0 en cada etapa con el mismo total, y esa vuelta se envía porque difiere del último
      envío;
    - la optimización cambia de fase.

    Solo la ventana instala un vigilante de `checkpoint`, y lo único que hace es leer un `threading.Event`.
- **Lo que no se arregla aquí:**
  - D381;
  - que `_focus_rejects_circle` importe `accepts` en cada llamada (es de antes y cuesta poco);
  - que `_grid_radius` sea una llamada por círculo, unos 50–75 ns, que se paga para que el recuento y la corrida no
    puedan separarse;
  - que un parche hecho en el padre llegue ahora a las seis rejillas que pasan a serie. Eso afecta a las herramientas
    A/B del banco: las seis ven sus interruptores, lo que es más correcto que antes (D375).

## 1. Qué cambia

- `ogr_slip2d/search.py`, en `GridSearch._run`: solo cuando el recuento nominal abriría un pool,
  `_too_few_reach_the_solver` cuenta los círculos que llegan a `evaluate_circle`.
  - **La regla:** si son menos de 400, la corrida se queda en el proceso.
  - **Solo se cuenta si se cumple todo esto:**
    - **foco barato:** algún punto, línea o tangente activo y bien formado, y ninguna ventana activa
      (`_focus_is_cheap`). Un objeto que no es `FocusObject` deja la regla de antes;
    - **como mucho una ventana de límites;**
    - **la rejilla cabe en las tres cotas:** `_COUNT_MAX_CENTRES` = 1000 centros, `_COUNT_MAX_FOCUS_TESTS` = 20 000
      círculos × objetos de foco activos y `_COUNT_MAX_PROFILE_WORK` = 20 000 centros × vértices del contorno
      exterior.

    Dentro de ellas, un recorrido cuesta menos de 0,1 s.
  - **El recuento** (`_circles_reaching_the_solver`): los tres rechazos de `_run_centres`, en su orden; un
    `checkpoint` por centro; para en 400.
  - **La fórmula del radio** pasa a `_grid_radius` y la usan el recuento y la corrida.
  - **Comentarios:** el docstring de `_worker_count` y el comentario de `_PARALLEL_MIN_CIRCLES` dicen que hay una
    segunda puerta.
- `ogr_gui/background.py`: `_TaskWorker._progress` sigue leyendo Cancelar en cada llamada, pero solo emite cuando
  cambia (porcentaje, total, fase). Son como mucho 101 señales por barrido.
- `tests/test_pool_threshold_v1386.py`, nuevo: 31 tests.
- `tests/test_task_progress_v1386.py`, nuevo: 5 tests.
- `AGENTS.md`: la frase del umbral del pool, con las cotas.
- El número, en los nueve sitios, y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_pool_threshold_v1386.py`:**
  - **el suelo:** el mismo foco a los dos lados del suelo (380 círculos, sin pool; 434, con pool), y el suelo
    estricto, con la constante puesta en 380 y en 381;
  - **el recuento es la población resuelta**, comparado con las llamadas a `evaluate_circle` en cada rama: sin foco,
    los cuatro tipos, un centro en un punto límite, un radio mínimo, dos ventanas de límites y sin superficie;
  - **los radios son los de 0.1.385**, con su expresión copiada en el test;
  - **cuándo se cuenta y cuándo no:** cada condición de la regla y cada cota en su borde;
  - **el recuento:** para en el suelo, cada centro es un `checkpoint` y una parada lo corta;
  - **la nota de caída** al pool;
  - **identidad:** una rejilla con foco por un pool real frente a la serie, bit a bit, y la corrida que deja el recuento
    frente a la decisión de 0.1.385, con notas y contadores.

  El más lento tarda 1,7 s, y es el que abre un pool real; el siguiente, 0,6 s.
- **`tests/test_task_progress_v1386.py`:**
  - una señal por porcentaje (101 de 442 llamadas);
  - Cancelar se lee en cada llamada;
  - un total o una fase nuevos se envían;
  - por la puerta real de `run_task`, en su hilo: 1764 llamadas llegan al diálogo 101 veces.
- **27 mutantes** del motor y de la ventana, cada uno cazado por al menos un test.
- **Los tests que protegen estas puertas**, juntos: 306 de 306 (pool, foco, Cancelar, horquilla de radios, censo de
  frases, tareas de la ventana, transitorio y retroanálisis).
- **El banco:**
  - la huella de los 23 casos frente a 0.1.377: 23 de 23 idénticos (`all identical`, código 0);
  - los 12 gemelos en serie: idénticos a los de 0.1.377 y a su corrida en paralelo (código 0);
  - los seis modelos del banco siguen en serie con la cota final.
- **La suite entera con `--jobs 4`:** **6820 de 6820, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en unos 26 min.
- **La serie entera,** porque la versión toca lo paralelo: **6820 de 6820, `Failed: 0`**, sin fugas, en 54 min. Queda
  apuntada como la última serie en verde. El runner avisa de un archivo que no toca esta versión:
  `test_points_table_v1371.py` tardó 95,4 s en serie y no está en `tests/_slow.txt`. En la corrida con `--jobs 4` no
  pasó de 90 s. La lista no se reescribe aquí.

## 3. Lo que queda

- **D381, en la versión siguiente**, por decisión de la propietaria. La ficha está en `ERRORES_Y_DISCREPANCIAS.md`
  (siguiente libre, D382), sin prompt largo porque se arregla a continuación.
- **V9–V18,** cada una con su OK.
- **El dato de 0.1.385 sobre el modelo 010** (539 círculos sin foco, más lento con pool que en serie tras el índice de
  V5) no lo toca V8: no tiene foco, y su recuento nominal decide como antes.

## Archivos

- `ogr_slip2d/search.py`
- `ogr_gui/background.py`
- `tests/test_pool_threshold_v1386.py` (nuevo)
- `tests/test_task_progress_v1386.py` (nuevo)
- `AGENTS.md`
- `docs/changelog/CHANGELOG_v0.1.386.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`,
  `ogr_gui`, `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)

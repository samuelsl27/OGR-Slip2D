# OGR Slip2D v0.1.428

**El retroanálisis cubre toda superficie que analiza la corrida, también las que dibuja el usuario (D396).**
- **Hasta hoy solo leía la población de la búsqueda.** Con una superficie del usuario como crítica publicaba la fuerza
  de OTRA superficie, del lado inseguro:
  - una polilínea en el talud de ejemplo (Janbu, objetivo 1,5, cota 20): 190,99 kN/m, cuando la del usuario necesita
    259,02;
  - un círculo: 145,99 frente a 166,33.
- **Una regla para todas** (decisión de la propietaria): ninguna superficie inadmisible gobierna, sea de la búsqueda o
  del usuario, mientras haya alguna admisible. Una nota lo dice solo cuando habría gobernado.
  - Si las comprobaciones rechazan TODAS, gobierna la que más fuerza necesita de entre ellas, y se dice. Es la misma
    reserva de la superficie crítica de la corrida (§0).
- **Con Bishop, una superficie que no es un círculo se deja fuera y se dice.** Antes contaba como analizada, y el
  resultado decía «ninguna» sin el motivo.
- **Se dice si la que gobierna es del usuario,** y el API trae por fin la geometría de la que gobierna; salía
  `{"type": "dict"}`.
- **Ningún número de hoy se mueve.** Se midió antes de escribir el arreglo (§0): ningún modelo del banco ni de los
  tests fijados tiene superficies del usuario, ni una superficie inadmisible entre las que retroanaliza.

Es la primera versión de la tanda P10: los once defectos que ya estaban y que encontró la revisión de 0.1.427
(D396–D404, en 0.1.428–0.1.436). Va antes de Sarma, así que las siete versiones del método pasan a 0.1.437–0.1.443, y
la spec 009 se renumera aquí.

**Decisiones de la propietaria (2026-11-05):**
- antes de Sarma;
- una ficha por versión;
- una regla de admisibilidad para todas las superficies, medida antes. Si hubiera movido el 037 o un test fijado, se
  le habría enseñado antes de seguir.

## 0. Lo que se encontró

- **El defecto.** `run_back_analysis` recorría `run.evaluations`, y no las `user_evaluations` que la misma corrida
  analiza y que pueden ser su crítica.
  - Desde 0.1.157 pasaba con los círculos del usuario.
  - 0.1.427 lo extendió a las polilíneas, que ahora pueden ser la crítica de una corrida no circular.
  - La ventana de Interpretar tasaba en cambio `res.critical`, que sí las incluye, así que las dos puertas se
    contradecían.
- **El paso 0: lo que mueve la regla de admisibilidad.** Se midió re-derivando fuerza a fuerza, sin tocar el motor
  (`scratchpad/paso0_d396.py`):

  | modelo | superficies | inadmisibles | se mueve |
  |---|---|---|---|
  | 037 del banco (Bishop, 1,5, cota 9) | 3097 | 0 | no: 334,77 kN/m antes y después |
  | Ej1 de `test_back_analysis_v140` | 190 | 0 | no |
  | `_slope` de `test_f3b_ops_v1201` | 59 | 0 | no (fuerza 0) |
  | talud de ejemplo de la ventana | 1366 | 0 | no |

  - Con la polilínea del usuario se reproducen 259,02 frente a 190,99 kN/m.
- **Tres cosas más, preexistentes, en el mismo sitio:**
  - el retroanálisis no miraba la admisibilidad de ninguna superficie;
  - con Bishop, una polilínea o una superficie recortada por una capa débil daba `None` y contaba como analizada;
  - `back_analysis_summary` pasaba a `surface_summary` el `dict` que guarda el retroanálisis, que solo lee objetos, y
    el API recibía `{"type": "dict"}` en vez de la geometría.
- **Un error mío de 0.1.427, corregido aquí.** El comentario sobre D395 de `canvas_view.py` decía que no se había
  medido si un `QGraphicsPathItem` pierde referencias a `None`. La ficha de D395 dice que sí se midió, y que da 0. El
  comentario original iba bien encaminado; fui yo quien lo estropeó en la revisión.
- **Caminos equivocados, para quien repita algo de esto:**
  - **Un `_rederived` del test que usaba el acceso nuevo** habría fallado en el árbol anterior por un nombre que
    falta, no por lo que calcula. Se reescribió desde la definición: la búsqueda más las del usuario, por identidad.
  - **La primera redacción de la nota del cribado** decía «más fuerza que la publicada», y no se sostiene cuando todas
    son inadmisibles y no se publica ninguna. Ahora dice «más que cualquier admisible».
  - **En el talud de ejemplo no hay ninguna superficie inadmisible de factor bajo que Janbu calcule.**
    - La polilínea de m-alpha de 0.1.427 no converge con Janbu.
    - Los círculos inadmisibles tienen F ≥ 3 y nunca necesitarían la fuerza mayor.
    - La regla se prueba con la evaluación REAL de la polilínea del usuario marcada inadmisible, a través de una
      búsqueda que devuelve la corrida, el patrón de `test_back_analysis_loads_v1220`.
- **La revisión adversaria de esta versión** (tres lentes y dos escépticos por hallazgo, 31 agentes, en solo lectura)
  encontró, antes de publicar:
  - **(media, mío) con todas las superficies inadmisibles, el retroanálisis dejaba de dar resultado.**
    - Publicaba NaN, con una nota que no era verdad: llamaba «más fuerza que cualquier admisible» a superficies de
      fuerza 0, cuando no había ninguna admisible.
    - 0.1.427 daba 0,0 kN/m o 162,70 kN/m en el mismo modelo: talud de ejemplo, Path de 5 superficies, c = 80 kPa,
      φ = 5° y la comprobación de tracción encendida.
    - `SearchResult.critical` vuelve en ese caso a todas las válidas («the checks are ignored rather than returning
      nothing»), y mi regla no.
    - **Ahora el retroanálisis hace lo mismo y lo dice** (`run.back_all_inadmissible`). Es la lectura de «la misma
      regla que la superficie crítica»: la letra de la decisión, «ninguna inadmisible gobierna», no contemplaba el caso
      en que no hay otra. **Lo decide la propietaria antes del commit.**
  - **(media, mío) con Bishop en una corrida no circular, el cuadro de la ventana solo decía «no se pudo retroanalizar
    ninguna superficie; revisa el objetivo y los ajustes de la búsqueda».**
    - El motivo de verdad estaba en el panel de notas.
    - Ahora el error del retroanálisis es ese motivo, y el cuadro lista además las notas que explican por qué.
  - **(baja, mío) el español de la nota del cribado:**
    - «m-alpha», cuando el diccionario dice «m-alfa»;
    - «el sostenimiento», cuando la ventana dice «fuerza de soporte»;
    - un «cualquier» sin sustantivo.
    - Además, la suite entera encontró «corrida» en la nota nueva, otra forma retirada: es «cálculo».
  - **(baja, mío) textos que no decían lo que hace el código:**
    - el docstring de la operación `back_analysis_run` del API;
    - el de `all_evaluations_of`, que daba por hecho que ya leían por él Newmark, los listados y las ventanas;
    - el comentario de D395, que citaba una sonda que ya no está en la punta de la rama. Ahora cita el commit 739885e.
  - **(baja, mío) dos tests que no podían fallar:**
    - las formas cerradas comparaban fuerzas ya recortadas a 0 (la polilínea tiene F = 1,12 y no necesita fuerza a
      1,0). Ahora se miden sin recortar, con las sumas del método y el factor resuelto a 1e-12;
    - la cuenta de Bishop pedía «al menos 2», y ahora pide exactamente las de la búsqueda más la del usuario (6).
  - **(baja, preexistente) Interpretar,** con Bishop y una crítica que no es un círculo, decía que el retroanálisis
    «solo está disponible para Bishop, Janbu y Janbu corregido». Ahora da la frase del motor. Se arregla aquí porque es
    la misma regla de D-B del plan.
  - **Refutado por los dos escépticos:** que `surfaces_analysed` cuente las inadmisibles. Se analizan, así que cuentan.
- **El banco: las nueve fichas de la tanda, abiertas.** D396–D404 se abrieron al planificar, en el paquete nuevo P10,
  como se hizo con P8j:
  - la cabecera del ERRORES dice ahora D404 y el siguiente libre D405;
  - la tabla de paquetes y `PAQUETES` de `generar_prompts.py` llevan P10;
  - van sin prompt largo, porque cada una se abre y se cierra en su versión con el plan de la tanda;
  - la auditoría da 0 ERROR y 80 AVISO, que son los 71 de antes y nueve «ficha abierta sin prompt largo».

## 1. Qué cambia

- **`ogr_slip2d/search.py`:** `all_evaluations_of(result)` y `is_user_surface_of(result, r)`, el acceso tolerante de
  la tanda.
  - Sin superficies del usuario es la misma lista, bit a bit.
  - Funciona con los dobles `SimpleNamespace` que solo tienen `evaluations`: tres en `tests/`, y d345 y d177 del banco.
- **`ogr_slip2d/back_analysis.py`:**
  - recorre `all_evaluations_of(run)`;
  - con Bishop, una superficie que no es círculo se cuenta aparte, no entra en `surfaces_analysed` y se dice; si eso deja
    el retroanálisis sin nada, ese es su error, y no «revisa el objetivo»;
  - una inadmisible no puede gobernar, y se dice si habría gobernado;
  - si todas son inadmisibles, gobierna la que más fuerza necesita de entre ellas, y se dice;
  - `BackAnalysisSurfaceResult.user_defined`;
  - el docstring del módulo y el de `run_back_analysis`.
- **`ogr_slip2d/run_messages.py`:** cuatro códigos nuevos, `run.back_not_circular_left_out`,
  `run.back_inadmissible_governed`, `run.back_user_governs` y `run.back_all_inadmissible`, con su español en
  `ogr_gui/i18n/__init__.py`.
- **`ogr_api/results.py` `back_analysis_summary`:** `critical_surface` con la geometría, más `user_defined` cuando lo
  es.
- **`ogr_gui/main_window.py`:**
  - la ventana enseña las notas nuevas en el panel de notas, sin tocar el texto de la llamada que fija la comprobación
    d348 del banco;
  - sin resultado, el cuadro dice el motivo y las notas que lo explican. Se conserva el texto literal que fija
    `test_seepage_run_notes_v1352`.
- **`ogr_gui/interpret_window.py`:** con Bishop y una crítica que no es un círculo, la frase del motor.
- **`ogr_api/ops/statistics.py`:** el docstring de `back_analysis_run`.
- **`ogr_gui/canvas/canvas_view.py`:** el comentario de D395, corregido (§0).
- **Documentación:**
  - `ogr_mcp/server.py` y `ogr_mcp/guide.py`;
  - `docs/mcp/herramientas.md`: toda superficie admisible que analiza la corrida, y qué dicen sus `notes`.
- **La spec 009 se renumera +9:** versiones, títulos y nombres de test de `plan.md`, `spec.md` y `tasks.md`, con su
  línea en el plan.
- **Tests:**
  - `tests/test_back_analysis_user_surfaces_v1428.py`, nuevo;
  - `tests/test_seepage_run_notes_v1352.py`, con las muestras de los tres códigos (cambio a propósito).
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_back_analysis_user_surfaces_v1428.py`,** 16 tests, en un segundo aproximadamente:
  - **la definición, como identidad:** la fuerza publicada es el máximo re-derivado superficie a superficie sobre la
    búsqueda más las del usuario, con la misma regla. Vale con la polilínea (Janbu) y con un círculo del usuario;
  - **las formas cerradas sobre la polilínea que gobierna,** sin recortar, desde las sumas del método:
    - fuerza 0 en su propio factor, resuelto a 1e-12 (≤ 1e-9 del peso, la identidad y la tolerancia de D210);
    - activa igual a pasiva con objetivo 1,0;
  - **lo que no cambia:** sin la superficie del usuario se publica la fuerza de la búsqueda, como antes;
  - **la regla de admisibilidad:**
    - una inadmisible que habría gobernado no gobierna, y la nota sale con n = 1;
    - una que necesitaba menos no deja nota;
    - si todas son inadmisibles, gobierna la de más fuerza, y se dice;
  - **Bishop con polilíneas:** 0 analizadas, y el motivo como error, con n exacto (5 de la búsqueda y 1 del usuario).
    Interpretar da la misma frase;
  - **el API:** la geometría y `user_defined`, solo cuando lo es;
  - **el acceso tolerante,** con un doble;
  - **la ventana:** enseña las notas nuevas y, sin resultado, el motivo en el cuadro, con el retroanálisis simulado.
- **Discriminación en el árbol de 0.1.427** (`git archive` de 2410e56, sin el buscador editable y comprobando los
  `__file__`): fallan 11 de 13.
  - Por comportamiento:
    - la fuerza publicada es 190,99 frente a los 259,02 del máximo, con la polilínea y con el círculo;
    - Bishop cuenta las polilíneas como analizadas;
    - el API da `{'type': 'dict'}`.
  - Los demás fallan por los nombres nuevos.
  - Pasan los dos controles, que deben valer en los dos árboles: las formas cerradas y la nota que no debe salir.
- **Vecinos:** retroanálisis, notas, español, MCP, resultados, versión, licencia, F2/F3b, notas de tarea, cancelar,
  hilos, almacén de dovelas, Janbu, sismo, superficies del usuario, términos y lienzo: 681 tests, en verde salvo el
  del changelog, que faltaba.
- **Suite entera con `--jobs 4`: 7198 en verde, 1 saltado y 0 fallos,** sin fugas ni tramos muertos.
  - Tardó 22,4 min.
  - La última corrida en serie fue hace 6 commits.
- **Banco, en seco:**
  - en la raíz, con las comprobaciones llamadas sin escribir el JSON, cierran:
    - D348: el retroanálisis da la misma fuerza en línea que por el hilo, 40,4349;
    - D346, D381 y D369;
  - en el 02, con `--seco`, cierran D210, D58, D204 y D211 (fuerza sin recortar en el factor propio con el solver a
    1e-12, y la envolvente curva);
  - la auditoría de la raíz da 0 ERROR.
- **Revisión adversaria:** ver §0. Todo lo que se confirmó está corregido aquí. La reserva con todas inadmisibles queda
  para que la propietaria la confirme.

## 3. Qué queda

- El resto de la tanda P10: D397 (Newmark) en 0.1.429, y después D398–D404.
- **La prueba a mano de la propietaria:** el retroanálisis desde la ventana con una polilínea del usuario como
  crítica. Comprobar que el panel de notas dice que gobierna la del usuario.
- Lo que el plan deja fuera de la tanda:
  - la estadística no acumula superficies del usuario (D405 propuesta);
  - el diálogo de retroanálisis de Interpretar tasa la crítica, y no la que más fuerza necesita.

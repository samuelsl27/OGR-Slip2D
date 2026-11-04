# OGR Slip2D v0.1.426

**Simulated Annealing y el enjambre evalúan cada candidato una sola vez por corrida, y cuentan su esfuerzo como las
demás búsquedas (D377).**
- **Reutilización (A).** Un candidato que la corrida ya evaluó no se vuelve a calcular. Su resultado se guarda otra vez
  y se repite lo que su evaluación hizo al estado de la corrida, así que la población, los contadores, las notas y la
  crítica son los de evaluarlo dos veces. **Ningún factor ni ninguna superficie cambia.**
- **Contadores (C), en el enjambre y en SA.** Se cumple `attempts − total_count == focus_rejected`, la identidad de las
  demás búsquedas:
  - el informe final del enjambre ya no cuenta como evaluación;
  - SA cuenta cada candidato como intento (el arranque, el paseo VFSA y el paseo local), cada rechazo como inválida, y
    los del foco en `focus_rejected`;
  - cada superficie que Optimize añade cuenta como intento, en toda búsqueda.
- **Cambian los contadores que enseñan la ventana, el API y el informe**, nada más.

Es la cuarta y última de la tanda P5c. La ficha sale de la sonda S8 de la auditoría del cómputo
(`AUDITORIA_COMPUTO_v0.1.377.md` §10, A8). **Decisiones de la propietaria (2026-11-04):**
- A (reutilizar) y C en el enjambre;
- C también en SA, confirmada cuando le dije que SA incumplía la identidad a propósito desde v0.1.187 (véase §0);
- las superficies de Optimize cuentan como intento, decidido cuando apareció el resto de −4 en el 104;
- B (dejar de gastar presupuesto en las repeticiones de SA) **no** se hace: movería los resultados.

## 0. Lo que se encontró

- **Las repeticiones de SA.**
  - En los extremos de la superficie, `_lmc` mueve solo la x (`_moved` no usa Ny). De sus ocho direcciones, tres dan
    el mismo candidato y dos la superficie actual.
  - Cada una se evaluaba, se guardaba y contaba contra `max_total_evals`.
  - Medido en la auditoría (S8): 540 evaluaciones guardadas en el caso 002, 102 de ellas repetidas.
  - Aquí, contando las llamadas a `_evaluate_polyline`: en el caso 002 del test (80 pasos, Bishop), 211 llamadas con 187
    candidatos distintos.
- **Las repeticiones del enjambre.**
  - En el modo de un mínimo, la partícula que está sobre el mejor global tiene velocidad exactamente cero y se evalúa
    donde ya estaba.
  - El informe final pedía otra vez el mejor de cada partícula.
- **La identidad del enjambre** (S8, 104): `attempts − total_count` = 2500 − 2535 = −35, con nada fuera del foco.
  - El informe final contaba como evaluación (−31).
  - **Los −4 restantes eran Optimize.** `_optimize_result` y `_optimize_each_minimum` suman 1 a `valid_count` por cada
    superficie que mejoran, sin contar un intento. Eso pasa en toda búsqueda con Optimize, encendido por defecto en SA
    y en el enjambre: el caso 002 da −1 y Tutorial 20 (K13), −1.
- **SA no cumplía la identidad a propósito.** v0.1.187 (D160) escribió que su población «es K×Ngen, fijada antes de la
  primera evaluación», y que un rechazo del foco es una propuesta del paseo, no un miembro.
  - Medido en K12 (caso 002, Spencer, semilla 1234, 300 pasos): esos K×Ngen son 117 pasos VFSA (50+25+12+10+10+10).
    `evaluations` guardaba 540 superficies, y 661 candidatos llegaban a `_evaluate_polyline`, 122 de ellos rechazados.
  - `attempts − total_count` daba −423.
  - Se lo presenté a la propietaria antes de tocarlo (regla 6), y confirmó cuadrarla.
- **Lo que la ficha leyó y no midió, medido:** en la rejilla de referencia de Ej_1 (4851 círculos), en Auto Refine
  circular sobre Ej_1 y en Auto Refine no circular de Tutorial 20 (K13) **no hay ninguna repetición exacta** entre las
  evaluaciones guardadas. No se toca nada ahí.
- **Una trampa de la medida, para quien la repita.** La huella de `test_slice_share_v1397` compara `vars(surface)`, y una
  superficie no circular lleva un `Polyline` que se compara con `==` y tiene un id propio. Con ella, dos corridas
  idénticas de SA no coincidían ni en la evaluación 0. La huella del test nuevo baja a los vértices.

## 1. Qué cambia

- **`ogr_slip2d/search.py`:**
  - `BaseSearch._REUSE_DUPLICATES` (el interruptor del A/B de los tests), `_new_memo`, y `_recorded`/`_replayed`.
    - `_recorded` apunta lo que una evaluación hace al estado de la corrida: el incremento de cada contador de
      `_RUN_COUNTERS` y el `_last_refusal` que escribe.
    - `_replayed` lo repite.
    - Las notas de `_note` no necesitan nada, porque se deduplican por línea.
  - `_bits_key`: la clave de un candidato, con los bits exactos de sus coordenadas y sus tipos. Con `==`, 0.0 y −0.0
    serían el mismo candidato.
  - **SA:**
    - `_candidate` es la única puerta del arranque, del paseo VFSA y del paseo local: cuenta, consulta el memo, evalúa
      y guarda;
    - `_run` envuelve a `_run_annealing` para que el memo dure exactamente una corrida;
    - el `attempts += 1` del bucle VFSA desaparece, porque cuenta la puerta;
    - la rama del foco de `_evaluate_polyline` deja una marca y su comentario de v0.1.187 se reescribe.
  - **Optimize:** `attempts += 1` donde `_optimize_result` y `_optimize_each_minimum` añaden una superficie.
- **`ogr_slip2d/particle_swarm.py`:**
  - `_evaluate` pasa por el memo y cuenta según `count`. El cuerpo de antes, sin contar, es `_outcome`.
  - `_run` envuelve a `_run_swarm`.
  - `_report_minima` pide `count=False`. El resultado se sigue listando en `evaluations`, como antes, así que la lista
    no cambia.
- **`tests/test_duplicate_evaluations_v1426.py`,** nuevo, con 9 tests.
- **`tests/test_search_effort_focus_v1187.py`, cambiado a propósito:**
  - la tabla de identidades gana SA y el enjambre;
  - `test_the_optimisation_walk_does_not_touch_the_search_counter` pasa de `con.attempts == sin.attempts` a
    `con.attempts == sin.attempts + len(con.steered)`, y añade la identidad. Los candidatos y rechazos del propio paseo
    siguen sin contar; lo que cuenta es cada superficie que Optimize **añade** a la población, que ya contaba como
    válida.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_duplicate_evaluations_v1426.py`,** 9 tests:
  - **A/B en el mismo proceso,** con la reutilización apagada y encendida, en SA (caso 002, 80 pasos) y en el
    enjambre (10 × 8):
    - las mismas evaluaciones en el mismo orden, bit a bit hasta los vértices, y los mismos contadores, notas,
      crítica y mínimos;
    - las evaluaciones reales con la reutilización son exactamente las distintas que contó, desde fuera, la corrida
      sin ella;
  - el generador global no se toca (regla 5);
  - **la identidad,** con un recuento hecho desde fuera:
    - en SA, `attempts` es el número de llamadas a `_evaluate_polyline` con la reutilización apagada, sin foco y con
      foco;
    - en el enjambre, `attempts` es partículas × iteraciones, sin foco y con foco;
    - con Optimize en los dos, `attempts` suma además las superficies que añade (`steered`).
  - El test cuenta con una clave propia, no con `_bits_key`, para que en el árbol anterior falle por comportamiento.
- **Discriminación.** En el árbol anterior (worktree de 1577e93, 0.1.425) fallan 7 de 9, todos por comportamiento:
  - SA: 50 intentos frente a 212 candidatos, el foco sin contar, y las llamadas repetidas;
  - el enjambre: 80 frente a 85 intentos, y 80 frente a 81 con Optimize.
  - Pasan el del generador global y el del enjambre con foco, en el que el informe final no tuvo que volver a pedir
    nada.
- **Vecinos** (en el árbol de desarrollo): los de SA, el enjambre, Optimize, Path, Block, Auto Refine, el esfuerzo de
  búsqueda, el almacén de dovelas y las notas de búsqueda: 415 de 415 tras el cambio deliberado de v1187.
- **Suite entera** con `--jobs 4`: 7136 en verde, 1 saltado, 0 fallos, sin fugas ni tramos muertos.
- **Banco de pruebas del cómputo**, lote `version`: 20 de 23 casos idénticos a 0.1.377. Los otros tres solo difieren
  en contadores, ruta a ruta:
  - **K12** (SA en el caso 002): `attempts` 117 → 662, `invalid_count` 0 → 122 y `total_count` 540 → 662. `valid_count`
    sigue en 540, que son 539 candidatos analizados más la superficie de Optimize.
  - **K11** (el enjambre del 104): `attempts` 2500 → 2504 y `total_count` 2535 → 2504. `valid_count` y
    `analysed_count` pasan de 2118 a 2087, porque los 31 del informe final ya no cuentan.
  - **K13** (Auto Refine no circular de Tutorial 20, con Optimize): `attempts` 4500 → 4501.
  - Las evaluaciones, la crítica, los mínimos y los factores son idénticos en los tres.
- **El 103 y el 104 del banco,** sus seis modelos de enjambre, con un A/B en disco (0.1.425 frente a 0.1.426, la
  misma configuración del modelo, en serie):
  - las evaluaciones, la crítica, los mínimos y las notas son idénticos bit a bit en los seis;
  - `attempts − total_count` pasa de −33…−45 a 0 en todos.
  - **Los resultados del banco no se vuelven a correr.** Guardan contadores (`generadas`, `validas`, `intentos`), pero
    se midieron con 0.1.179 (104) y 0.1.260 (103). Correrlos ahora mezclaría esta versión con todo lo que cambió
    entre medias, y ningún contador se compara con la referencia. Queda dicho para quien los vuelva a correr: `validas`
    y `generadas` bajarán y `intentos` subirá.
- **El tiempo de K12,** con un A/B en el mismo proceso, alternando: con reutilización, 7,22, 8,82 y 7,93 s; sin ella,
  9,46, 8,65 y 8,86 s.
  - La media baja un 11 %, pero los controles se separan tanto como el efecto, así que la medida no es concluyente.
  - **Manda contar el trabajo:** la reutilización ahorra 100 de las 661 evaluaciones de la búsqueda (15 %). El paseo de
    Optimize, que no cambia, se lleva el resto del tiempo.
- **`d377()`**, nueva en el `verificar_cierres.py` de la raíz: **CUBIERTO POR TEST**.
  - K12 con la reutilización apagada y encendida: 661 candidatos, 100 repetidos y 561 cálculos, con todo idéntico.
  - La identidad cuadra en K12 (662/662) y en el 104 (2504/2504, 4 superficies de Optimize).
  - Discriminada con el motor de 0.1.425: **SIGUE ABIERTO**, con 661 cálculos y las identidades en −423 (K12) y −35
    (104). Es la medida de S8.
  - Igual que el test, mide sin nombres nuevos, para que en el árbol anterior falle por comportamiento.
- **El VC de la raíz entero:** 137 comprobaciones, todas cierran, y 0 bajadas. **El del 02 entero**, por ser la última
  versión de la tanda: 242 fichas y 0 bajadas.
- **El cierre del banco:** `Evaluaciones/0.1.426` de la raíz, D377 retirada al índice, podada de `PAQUETES` y tachada en
  la cadena de P5, que queda con D258, D260, D261 y D264. `auditoria_invariantes.py` da 0 ERROR en la raíz y en el 02.

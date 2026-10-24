# OGR Slip2D v0.1.358

**Un bucle de Picard que para con la cara de rezume sin asentar pasa al rescate, y el rescate
arranca sin los nodos que el bucle congeló (D356).**

El bucle del permanente no saturado para cuando el cambio relajado baja de la tolerancia y el
conjunto de la cara deja de cambiar. Un nodo congelado por el presupuesto de conmutaciones ya no
lo cambia. El bucle podía parar, así, con un nodo retenido a P = 0 mientras entraba agua; la
comprobación final daba el resultado por no convergido, y el rescate (D124, D285) no corría,
porque solo corría si el bucle fallaba.

La puerta de la aplicación lo encontraba en el banco: la presa 2 del problema 9 del manual de agua
(Bowles 1984; Chapuis et al. 2001).
- Hoy sale «no convergido», sin caudal y con la superficie libre de 3 a 4 m más alta.
- Ahora converge con el caudal a −0,46 % del publicado.

## 0. Lo que se encontró

- **La ficha decía que, con el presupuesto por defecto, el defecto no aparece en el banco.**
  - Era cierto con el banco de 0.1.355: en el barrido de D285, 265 corridas, ninguna lo tenía.
  - Dejó de serlo el 2026-10-23, cuando D358 rehízo la presa 2 del problema 9 con la geometría y
    las curvas medidas sobre la figura.
  - El barrido de esta puerta (`_auditoria/P6_0358/` del banco) lo encuentra en esa presa, malla
    x1 (955 T3), con ω 0,4 (la de la puerta), 0,6 y 0,8 y el presupuesto por defecto.
  - El banco publica ese modelo con ω 0,3, donde el bucle falla y la continuación lo rescata: por
    eso no se veía.
- **Con los ajustes de la puerta** (ω 0,4, 200 pasadas, tol 1e-5):
  - el bucle para con un nodo de la cara del dren retenido mientras le entra agua a 35 veces el
    caudal de la presa (2,46e-6 m³/s por metro, frente a 7,0e-8);
  - el resultado sale no convergido y sin caudal, porque `flux_through_segment` da NaN para un
    campo no convergido;
  - la superficie libre sale en 5,47 / 5,30 / 5,11 m (x = 114 / 142,5 / 171), y las cargas a
    4,66 m del punto fijo.
  - Rescatado: caudal **4,2105e-6 m³/(min m), −0,46 %** frente al 4,23e-6 de Chapuis et al.
    (2001), y superficie libre en 2,184 / 1,719 / 1,154 m. Es lo que publica el banco.
  - En esa presa la continuación es la única vía que converge: el bucle solo cicla aun con
    presupuestos de 100 y 400 y 3000 pasadas, como midió D124. El ancla es el caudal publicado.
- **Los casos de la ficha se asientan en el punto fijo de otras vías,** con la misma cara:
  - (a), la presa del 102 de v1125, presupuesto 1: a 2,2e-6 m del campo con el presupuesto por
    defecto (tol/ω = 2,5e-5); hoy, a 5,73 m;
  - (b), la presa de Gardner de v127, ω 0,1, presupuesto 25: a 5,8e-7 m del punto fijo a
    1e-12; hoy, a 0,129 m.
- **El mecanismo es el presupuesto, siempre.** En todas las firmas medidas, los nodos sin asentar
  están congelados y retenidos con agua entrando. El bucle veía la violación al parar (el cociente
  es el final hasta la quinta cifra) y no podía actuar. La ficha temía también un desfase entre el
  iterado relajado del bucle y la solución final; no apareció en ninguna fila.
- **El diseño del plan era otro, y la medida lo cambió.** El plan arrancaba Anderson con la cara
  del bucle tal como quedó (A1).
  - En el 004 con presupuesto 1 y 200 pasadas, A1 converge, pero a **otra cara admisible dentro
    de las bandas**: un nodo retenido en zona seca (kr ~1e-5) con una entrada de 0,001 veces la
    banda de flujo, a 4,2 cm (80 p_tol) de la referencia. Hoy ese caso sale no convergido.
  - Arrancando sin los congelados del bucle (A2), llega a la referencia (1,7e-6, misma cara).
  - Censo de 36 configuraciones con presupuestos ahogados, 14 firmas:
    - A1: 12 en la referencia, **1 con otra cara publicada como convergida** y 1 respaldo;
    - A2: 10 en la referencia, **0 con otra cara** y 4 respaldos, todos con presupuesto 1 y todos
      al bit lo de hoy.
  - Con presupuesto 1, A2 tiene que volver a retener sin margen los nodos que suelta, congela
    alguno mal y se aparta. Es el precio de no heredar un estado que el bucle no pudo revisar.
- **La ficha nombraba dos tests que fijaban «no convergido», y son tres.** Con D279 apagado,
  `test_switch_budget_v1283::test_switched_off_it_freezes_again` vuelve al presupuesto 25 con
  ω 0,1, que es el caso (b). Con A2, el de v1125 sigue pasando tal cual: (a) acaba en el
  respaldo.
- **Dos anomalías que no son D356** (regla 6). Se abren como fichas; aquí no se toca nada.
  - **D364.** La banda de flujo de la cara es 1e-4 del mayor caudal nodal de la PRIMERA
    solución, la saturada. Si el modelo solo sale por la cara de rezume, esa solución no tiene
    caudal (con una sola carga impuesta es esa carga constante) y la banda queda en el redondeo.
    - En la presa del 102 sin cola, q_tol = 5e-24, con un caudal real de 3,3e-6.
    - En el banco pasa en 60 de las 255 corridas: el 05-006, el 05-009 y el 05-011.
    - No se ha visto que mueva un resultado convergido.
  - **D365.** La presa 2 del 05-009 en la malla x4 no converge con ω 0,2, 0,4 (también con los
    ajustes de la puerta) ni 0,8: falla el rescate entero. Con ω 0,3, la del banco, y 0,6,
    converge por Anderson 5. Antes de D358 convergía con las cinco ω.
- **Errores míos en la puerta,** corregidos antes de cerrar:
  - el plan decía que ninguna puerta llegaba al defecto, con datos anteriores a D358;
  - el primer informe daba las reacciones de la presa 2 en m³/min cuando son m³/s (sus curvas van
    en m/min y el modelo las divide por 60, D130). Decía «más de la mitad del caudal» donde son
    35 veces.
- **Decisiones de la propietaria en la puerta:**
  - A2;
  - el test principal es la presa 2 reproducida en el repositorio, frente al caudal publicado,
    más los casos forzados;
  - abrir D364 y D365, fuera de esta versión.

## 1. Qué cambia

- **Interruptor `seepage.LOOP_SETTLED_FACE`,** con alta en `INTERRUPTORES` del banco como
  (0, 1, 358). Apagado reconstruye 0.1.357.
- **`solve_unsaturated`.** Si el bucle convergió, su estado final (la misma solución lineal que
  publica el final) se calcula una vez, antes de decidir el rescate, y se le pregunta la cara.
  - Si la cara asienta, se publica ese estado: los mismos bits que antes.
  - Si no asienta, el resultado va al rescate como un bucle que falló, con Anderson arrancando de
    la cara del bucle sin sus nodos congelados.
  - Si un camino asienta, se publica ese camino.
  - Si ninguno asienta, se publica el estado del bucle, al bit el de 0.1.357, con
    `rescue = "failed"`. Crecen `iterations`, `history`, `history_segments` y las notas del
    rescate.
- **`_rescue(..., fallback=True)`.** Con `fallback=False` no devuelve un camino apartado por
  D285: el bucle tiene su propio estado al que volver.
- **Docstrings:**
  - `solve_unsaturated`: una sección nueva; el párrafo de la ω muy pequeña (ω 0,1 con
    presupuesto 25 ya no sale no convergido: lo rescata); y `rescue` «failed» cuando se publica
    el bucle;
  - `_rescue`: el párrafo de `fallback`;
  - el comentario de `PICARD_RESCUE`, el de `RESCUE_SETTLED_FACE` y el de `max_node_switches`.
- **No cambian:**
  - los mensajes (FACE_UNSETTLED sigue diciendo la verdad cuando nada asienta);
  - las claves de las notas;
  - el paso transitorio, que tiene el mismo patrón pero no tiene rescate por diseño, y ya lo da
    por no convergido;
  - el resultado publicado del banco.

## 2. Tests

- **`tests/test_picard_loop_face_v1358.py`,** 8 casos, unos 60 s.
  - **La presa 2,** reproducida con la API del repositorio: polígono, línea del dren, las dos
    curvas de la figura divididas por 60 y la malla del generador a 1000 elementos (se comprueba
    antes que son 955 T3). Se resuelve con los ajustes de la puerta, importados de
    `transient_stability`.
    - Apagado, el defecto: el bucle paró (su último cambio relajado está por debajo de la
      tolerancia), no hubo rescate, la cara no asentó, no convergido y sin caudal.
    - Encendido: convergido por la continuación, con cada nodo de la cara cumpliendo la condición
      (juzgado con las bandas del solver, sin su `_unsettled_nodes`), y el caudal a menos del 1 %
      del publicado (medido −0,46 %). Regla 1, valor externo.
  - **El 004 con presupuesto 1** (la malla de `test_rescue_face_v1356`): el rescate llega al
    punto fijo al que llega el bucle solo con el presupuesto por defecto, con la misma cara y a
    menos de tol/ω (medido 1,7e-6 m). Es el caso que separa A2 de A1.
  - **Ningún camino asienta** (la presa de v1125, presupuesto 1):
    - se publica el estado del bucle al bit (cargas, cara, recuentos, `picard_delta` y aviso con
      código y argumentos), no convergido, con `rescue` «failed»;
    - solo crecen las iteraciones (lo mismo que `rescue_iterations`) y la serie, cuyo principio
      es la del bucle, con los cuatro segmentos.
  - **Un bucle que converge con la cara asentada** (Gardner, ω 0,4): mismas cargas, iteraciones,
    cara y notas enteras con el interruptor encendido y apagado.
- **`test_picard_tolerance_v1272::TestAVerySlowRelaxation`.**
  - El caso de siempre (ω 0,1, presupuesto 25) se pide con `LOOP_SETTLED_FACE` apagado y conserva
    sus aserciones, más la de que no hubo rescate.
  - Un test nuevo: encendido, el bucle paró, el rescate de Anderson lo asienta a menos de la
    tolerancia del punto fijo a 1e-12 (medido 5,8e-7 m) y con la misma cara.
  - `_solve` lleva el interruptor en la clave de su caché y lo restaura.
- **`test_switch_budget_v1283::test_switched_off_it_freezes_again`.** Apaga también
  `LOOP_SETTLED_FACE`: reconstruir 0.1.282 son los dos interruptores.
- **En 0.1.357** (con el atributo puesto a mano, para que falle por comportamiento y no por el
  nombre):
  - el test nuevo falla en 4 de sus 8 casos: el caudal sale NaN, la puerta no rescata, el 004 no
    se rescata y no se informa el rescate. Pasan los 4 que fijan lo que no debe cambiar;
  - el test nuevo de v1272 falla;
  - los «apagados» de v1272 y v1283 pasan, como deben.

## 3. Verificación

- **Selección dirigida** (los 9 archivos de filtración y rescate vecinos, con el censo de v1352):
  131/131.
- **Suite entera:** 6528/6528, `EXIT=0`, 92 min. Parte del tiempo corrió a la vez que los A/B,
  `repro_d365.py` y los dos verificadores de cierres. Después se tocaron solo los README, y sus
  cuatro tests (licencia, andamiaje, versiones y nombres de producto) pasan, 60/60.
- **A/B árbol contra árbol** (`_auditoria/P6_0356/ab_arbol.py`, el `git archive` de 0.1.357
  frente al árbol de trabajo): **73 filas, 0 distintas**, sin claves de notas nuevas.
  - Son el 05 entero con las dos mallas, el 02-010, el 02-038 con tres alturas por cuatro curvas,
    y el permanente y el transitorio de la presa del 102.
  - Son dos menos que en 0.1.356: D130 retiró la variante `nucleo` del 05-009.
  - El 05-009 presa 2 entra con su ω 0,3, y no cambia.
- **A/B de los casos con la firma** (`_auditoria/P6_0358/ab_d356.py`): la presa 2 en la puerta,
  (a), (b) y el 004 con presupuesto 1.
  - **0.1.357 frente a 0.1.358 apagado: 4 de 4 iguales al bit** (cargas, `converged`,
    `iterations`, cara y notas enteras).
  - Encendido: los cuatro cambian.
    - Tres se rescatan: la presa 2 (4,67 m), (b) (0,129 m) y el 004 (7,5 cm).
    - En (a), el respaldo deja las cargas iguales. Solo cambian `iterations` (de 29 a 64),
      `history`, `history_segments` y las notas del rescate.
- **El barrido del banco con el prototipo** (255 corridas): las 3 firmas son las 3 que cambian;
  las otras 252 salen iguales al bit. El motor de esta versión da lo mismo al bit que el prototipo
  en (a), en (b) y en la presa 2 en la puerta.
- **`d356()` del verificador de la raíz.**
  - CUBIERTO POR TEST en 0.1.358, en vivo: la presa 2 apagada reproduce el defecto y encendida da
    −0,46 %; (b) queda a 5,8e-7 m del punto fijo; (a) cae al respaldo al bit con «failed»;
    y los tres tests.
  - SIGUE ABIERTO en el `git archive` de 0.1.357, y también con el atributo puesto a mano, por
    comportamiento.
- **Banco:**
  - **raíz:** `verificar_cierres.py` entero, 92 comprobaciones (una más, `d356`), 0 bajadas y 0
    veredictos cambiados. Cambian tres detalles, ninguno por esta versión:
    - D124 y D130 pasan a las cifras de la presa 2 que D358 rehízo el día antes (−0,98 % en ×4
      y −0,46 %), y D124 lista además el test nuevo;
    - D335 pasa de 423 a 425 códigos: los de Hoek-Brown de 0.1.357;
  - **manual 02:** `verificar_cierres.py --seco` entero, 242 fichas, 0 bajadas, todas con el
    veredicto de su línea base;
  - `INTERRUPTORES` (`elegibilidad_critica_d155.py` del 02) gana `seepage.LOOP_SETTLED_FACE` con
    (0, 1, 358). La tabla cubre los 54 interruptores del motor;
  - D356 retirada (CUBIERTO POR TEST), con la historia en `Evaluaciones/0.1.358/`;
  - `PAQUETES["P6"]` = D364, D365, y D356 tachada en la cadena;
  - D364 y D365 abiertas con ficha, prompt largo y `repro_d364.py` y `repro_d365.py`. La cabecera
    dice D366 libre;
  - prompts: 46 (29 largos y las 17 FALTA de antes); citas, las 19 rotas de antes;
  - auditorías: 0 ERROR en los dos bancos;
  - instantáneas de 0.1.358 forzadas tras retirar: raíz 810 archivos y 02 3284.
- **README:** el contador de tests (estaba en 4836 desde v0.1.217) y la duración de la suite (decía
  35 min). Las líneas de código («84 600 y 90 700») no se tocan: no salen con `wc` ni en v0.1.217
  (95 939 y 104 724), así que no se sabe cómo se contaron.

## 4. Lo que sigue abierto

- **D364** y **D365** (P6), con su prompt largo.
- **Los dos casos de los tests dependen de la malla:** la presa 2 con 955 T3 y el 004 con 2307.
  Si la CI de Linux triangula de otra forma, lo dirán sus primeros casos.

## 5. Lo que no se ha probado

- La gráfica de convergencia de *Interpret Groundwater* con un tramo del bucle que acaba por
  debajo de su umbral y los caminos del rescate detrás. Dibuja cualquier combinación desde
  0.1.269, pero no se ha mirado en la aplicación.
- Abrir la presa 2 del 05-009 en la ventana y calcular el agua: el test usa los ajustes de la
  puerta, no la ventana.
- La CI de Linux (no se ha subido).

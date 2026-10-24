# OGR Slip2D v0.1.360

**Por qué el rescate no converge en la presa 2 del problema 9 en mallas finas: el camino de la
continuación se pliega en el quiebro donde la curva del dren cae a su suelo. Se cierra documentado
(D366) y se abre una ficha para un camino que siga el camino de soluciones a través de esos pliegues
(D367). Ningún número cambia.**

El 05-009 presa 2 (`nucleo_k_min`), con los ajustes de la puerta de la aplicación (ω 0,4, 200
pasadas, tol 1e-5), sale «no convergido» en las mallas de 3691 y 3886 T3. D365 lo midió en 0.1.359 y
abrió D366 para buscar un camino del rescate robusto ante curvas casi escalón. Esta versión es la
medida de esos candidatos y el porqué de que fallen.

## 0. Lo que se encontró

La puerta de medida está en `_auditoria/P6_0360/D366_medida.md` del banco. El motor no se tocó para
medir: los candidatos se instalaron por parche de clase, con copias literales de `_rescue`,
`_anderson`, `_continuation_newton` y `_NewtonSystem.newton` de 0.1.359. Esas copias salen al bit con
el motor (control C0) en las dos mallas que fallan y, con los cinco modos, en la ×1.

- **Dónde se para Newton.** En las dos mallas, un solo elemento del dren (el 3349 en 3886 T3, el 3014
  en 3691) queda clavado en el quiebro de 9,8 kPa, donde la curva del dren baja seis décadas y cae a
  su suelo `kr_min` (pendiente de −4,76 /kPa en ln kr a un lado, plana al otro).
  - Desde el lado húmedo, el paso de Newton lo manda al seco; desde el seco, al húmedo.
  - El λ que acepta la búsqueda lineal baja con la distancia al quiebro (9,7821 → 9,8810 → 9,8016 →
    … → 9,8000, a 3e-6 kPa): un Zeno.
- **No es el jacobiano.**
  - La derivada direccional de |R| a lo largo del paso vale −1,000 por debajo del λ de cruce: el
    jacobiano es exacto en el lado en que está el elemento.
  - Ningún elemento está a menos del paso de la diferencia central de un quiebro.
  - El Newton semiliso (Qi & Sun 1993), que estaba en la lista como candidato condicional, se
    descartó por esta medida.
- **Es un pliegue situado en el quiebro.** El jacobiano tiene determinante +1 con la pendiente seca
  del elemento y −1 con la húmeda.
  - **El caso 3886.** Forzando el elemento a cada tramo, para t < t* hay dos soluciones (seca y
    húmeda), y se juntan en el quiebro entre t = 0,6172 y 0,6177. Pasado ese t, ninguna es solución:
    el camino da la vuelta.
  - **En 3691,** entre 0,6489 y 0,6504.
  - **Por qué no se veía.** El determinante cambia de signo saltando el quiebro, no pasando por cero,
    así que ningún valor singular de un lado lo ve. La continuación en el parámetro natural no puede
    cruzarlo, se busque como se busque el paso.
- **Un camino equivocado de D365.** D365 leyó el σ_min suave como «un quiebro más que un pliegue».
  Era las dos cosas, y el plan de esta tanda partía de esa lectura: «Zeno en un quiebro, globalización».
  El Zeno es real, pero no hay raíz al otro lado que una búsqueda mejor pudiera alcanzar.
- **Los candidatos de la ficha, medidos.** Cada uno en las dos mallas que fallan y escrito de dos
  formas algebraicamente iguales, como control de redondeo:
  - **una búsqueda lineal no monótona** (Grippo, Lampariello & Lucidi 1986; la memoria N = 10 es la
    de Ahookhosh & Ghaderi, porque el original no se pudo leer): falla en las dos mallas y en las
    dos formas. Acepta 110 pasos no monótonos y no sale de t*;
  - **la continuación por pseudo-longitud de arco** (Keller 1977; Allgower & Georg 1990): falla en
    las dos. Llega a t = 0,61752 con la componente en t de la tangente bajando a 0,0077 (la tangente
    se pone vertical en el pliegue);
  - **Anderson con reinicios sistemáticos** (Henderson & Varadhan 2019, con un ciclo igual a la
    profundidad), arrancado desde el último estado de la continuación: converge en 3886 en las dos
    formas (profundidad 20, 82 evaluaciones, a 3,2e-6 m de la respuesta del banco) y falla en 3691 en
    las dos. Los reinicios dentro de los Anderson de hoy rompen la malla de 4095, que hoy converge.
- **Un candidato que no estaba en la ficha,** que salió del pliegue: la continuación pseudo-transitoria
  (Kelley & Keyes 1998; Fowler & Kelley 2005 la extienden a ecuaciones no lisas). No sigue ningún
  camino en t.
  - En 3886 converge solo con un paso inicial δ₀ = 1, en las dos formas. Con 0,1 y con 10 agota el
    presupuesto.
  - En 3691 no converge con nada.
  - La fuente no fija ni δ₀ ni la escala D: funcionar en una sola década es un parámetro ajustado al
    caso.
- **La solución existe en las dos mallas, pero llegar a ella es una lotería de arranques.**
  - Se lanzó Anderson desde cuatro arranques: el del motor, el último iterado del bucle, la saturada
    y el estado de la continuación. En cada uno, con tres variantes y dos profundidades: 24
    combinaciones por malla.
  - Convergen 2 en 3886 y 4 en 3691, y **ninguna en las dos**. El caudal sale en −1,44 % y −1,39 %
    del publicado (4,23e-6 m³/(min m), Chapuis et al. 2001).
  - Los ajustes del banco no convergen en 3691 con ninguna de cuatro ω, ni en la malla de 4095 con
    ω 0,3 y 0,6, aunque esta converge con la puerta.
- **Otro camino equivocado, mío.** Arrancando desde la solución de 3886 interpolada a la malla de
  3691, ni Anderson ni el pseudo-transitorio convergían, y estuve a punto de escribir «en 3691 la
  solución no está demostrada». La tabla de arranques la encontró desde la saturada.
- **Dónde no corre, no mueve nada.** Los caminos nuevos se midieron en la posición «reanudar»: solo
  corren cuando la continuación se rinde por el paso mínimo. Así salen al bit en las tres mallas que
  convergen (1921, 2901 y 4095 T3) y, con los cinco modos, en la ×1.
- **Decisión de la propietaria en la puerta:**
  - D366, CIERRE DOCUMENTAL en el docstring de `_rescue`;
  - una ficha nueva (D367) para un camino que siga el camino de soluciones a través de pliegues no
    lisos;
  - con versión propia.
  - No se adopta Anderson con reinicios como arreglo parcial, ni un abanico de caminos elegido
    porque cubre las dos mallas: los dos serían ajustar al caso.

## 1. Qué cambia

- **El docstring de `UnsaturatedSeepageSolver._rescue`.**
  - Una sección nueva: por qué se para la continuación (el pliegue en el quiebro), los caminos
    medidos y su resultado, que la solución existe en las dos mallas, y la decisión.
  - La lectura de D365 («un quiebro más que un pliegue») queda corregida en su sitio.
  - Se conservan las piezas que comprueba `d365()` del banco.
- **El docstring de `_continuation_newton`:** la continuación en el parámetro natural no cruza un
  punto de retorno, y con curvas a trozos ese punto puede estar en un quiebro, donde ningún
  jacobiano de un lado se vuelve singular.
- Ni código, ni interruptores, ni mensajes, ni notas. Ningún número del programa ni del banco se
  mueve.

## 2. Tests

Ninguno nuevo. La versión no cambia ningún comportamiento, y el cierre lo comprueba `d366()` en el
verificador de cierres de la raíz del banco: la medida archivada y las piezas del docstring.

## 3. Verificación

- **Suite entera:** 6536/6536, `EXIT=0`, unos 111 min.
  - Corrió a la vez que los dos verificadores de cierres, las instantáneas y las auditorías del banco:
    el reloj no es una medida.
  - Después solo se tocó este changelog. Se repitieron sus tests (versiones, andamiaje, licencia y
    nombres comerciales).
- **El diff:** solo docstrings de `seepage.py`, los nueve sitios de versión y este changelog.
  - No hace falta A/B árbol contra árbol: no cambia ni una línea que se ejecute.
  - Los README siguen en 6536 tests, porque no hay ninguno nuevo.
- **`d366()` del verificador de la raíz.**
  - En 0.1.360, CIERRE DOCUMENTAL. Lee la medida archivada: el elemento del dren clavado en 9,8 kPa
    en las dos mallas, con determinante +1 del lado seco y −1 del húmedo, y sin rama pasado t =
    0,6177 y 0,6504; los arranques, 2 de 24 en 3886, 4 en 3691 y 0 en las dos. Y lee la decisión en
    el docstring de `_rescue`.
  - En el `git archive` de 0.1.359, SIGUE ABIERTO: al docstring le faltan las piezas.
- **Banco:**
  - **raíz:** `verificar_cierres.py` entero, 95 comprobaciones (una más, `d366`), 0 bajadas.
    Ningún veredicto ni detalle cambia frente a la línea base, tampoco el de `d365`, cuyas piezas
    del docstring se conservan;
  - **manual 02:** `verificar_cierres.py --seco` entero, 242 fichas, todas con el veredicto de su
    línea base;
  - D366 retirada, con la historia en `Evaluaciones/0.1.360/`;
  - D367 abierta, con ficha y prompt largo; la cabecera dice D368 libre;
  - `PAQUETES["P6"]` = D367, y D366 tachada en la cadena;
  - prompts: 45 (28 largos y las 17 FALTA de antes), 0 sin paquete; citas, las 19 rotas de antes,
    ninguna de D366 ni de D367;
  - auditorías: 0 ERROR en los dos bancos;
  - instantáneas de 0.1.360 forzadas al final: la raíz con 910 archivos y el 02 con 3284;
  - `INTERRUPTORES` no cambia: esta versión no tiene interruptor.

## 4. Lo que sigue abierto

- **D367 (P6, nueva):** un camino del rescate que siga el camino de soluciones a través de un pliegue
  no liso. Candidatos con fuente:
  - una continuación a trozos que cruce el quiebro por la otra rama, guiada por el signo del
    determinante (los métodos lineales a trozos de Allgower & Georg 1990);
  - la continuación pseudo-transitoria con la capacidad física del transitorio como escala, en lugar
    de diag|J|, que quitaría el δ₀ libre.
- La presa 2 del 05-009 en las mallas de 3691 y 3886 T3 sigue saliendo no convergida con los ajustes
  de la puerta. El banco la publica en la ×4 con ω 0,3, con la que converge.

## 5. Lo que no se ha probado

- El barrido completo del banco y los tests con un candidato instalado: ninguno pasó la primera
  etapa del embudo. Solo la fila ×4 del barrido con Anderson con reinicios.
- La CI de Linux (no se ha subido).

# OGR Slip2D v0.1.356

**Cada camino del rescate del permanente no saturado se acepta solo si su respuesta asienta la
cara de rezume; si no, se prueba el siguiente (D285).**

Hasta 0.1.355, el rescate de D124 tomaba el primer camino que bajaba de la tolerancia, aunque su
propio presupuesto de conmutaciones hubiera congelado un nodo de la cara en el estado equivocado.
Pasaba entonces esto:
- el resultado salía «no convergido, la cara no asentó»;
- la continuación con Newton no se llegaba a probar.

En los cuatro casos medidos donde pasaba, la continuación asienta la cara. En tres de ellos otra
vía independiente llega al mismo punto fijo. Si ningún camino asienta, se publica lo mismo que
antes, al bit.

## 0. Lo que se encontró

- **El mecanismo, y por qué el arreglo solo mueve lo que salía mal.**
  - En el punto en que un camino acepta, su regla de conmutación acaba de correr sobre la misma
    solución lineal G(x), con las mismas bandas que `_unsettled_nodes`.
  - La solución final de `solve_unsaturated` repite esa solución.
  - Por tanto, en un camino aceptado solo pueden quedar sin asentar nodos **congelados** por el
    presupuesto del camino.
  - Mirar la cara al aceptar solo cambia las corridas que antes acababan en `converged=False`
    tras un camino «convergido». No añade ninguna solución lineal. En la medida, el número de
    nodos sin asentar del camino coincidió con el publicado en las 8 filas en que algún camino
    llegó al residuo.
- **La reproducción de la ficha sigue valiendo, con otras cifras.** Con 0.1.355:
  91 evaluaciones de Anderson, 2 nodos sin asentar y 5 congelados. La ficha (0.1.283) decía
  87, 1 y 4. Lo más probable es que las bandas ×0,1 de D280 (0.1.284) movieran esas cifras. La
  medida de D274 también es anterior a D279 y D280: tenía la firma en 3 de sus 8 filas
  empinadas, y hoy la tiene en 2.
- **La puerta de medida** (`_auditoria/P6_0356/` del banco, `D285_medida.md`).
  - Un prototipo por parche de clase, sin tocar el motor, comparado con el motor en el
    problema 4 del manual de agua (la presa con dren de pie de Harr 1990).
  - Curvas de seis décadas en 0,5 kPa («empinada»), 0,05 kPa («escalón») y 0,005 kPa.

  | Caso (ω 0,4) | 0.1.355 | Con la cara en la aceptación | max\|ΔH\| |
  |---|---|---|---|
  | Malla graduada 2 cm, 500 pasadas (la de la ficha) | Anderson 5 aceptado con 2 sin asentar (entra agua: 48,5 y 4,7 veces la banda) y 5 congelados; la cara de rezume llega a 0,486 m del pie | Anderson 5 y 20 apartados; la continuación asienta; la cara llega a 0,194 | 4,75 cm |
  | La misma, con los ajustes de la puerta de la aplicación (200 pasadas, tol 1e-5) | igual: 2 sin asentar | la continuación asienta | 4,75 cm |
  | Malla graduada 5 mm, 500 pasadas | Anderson 20 aceptado con 4 sin asentar y 9 congelados | la continuación asienta | 4,1 cm |
  | Malla del generador a 2400 (2307 T3), 1 pasada (el caso del test) | Anderson 5 aceptado con 1 nodo libre a presión (67 veces la banda) | la continuación asienta | 3,7 cm |
  | El mismo con presupuesto 1 | Anderson 5 con 1 sin asentar | ningún camino asienta: se publica lo de antes, al bit | 0 |

  - Las seis filas con las curvas «escalón» y casi escalón no tienen la firma: los tres caminos
    fallan por el residuo. Las filas sin firma dan lo mismo al bit.
- **Es el punto fijo del problema.**
  - En tres de los cuatro casos, otra vía independiente llega al mismo punto fijo, con la misma
    cara:
    - el bucle solo con 200 pasadas, en el caso del test: 2,1e-6 m, por debajo de tol/ω;
    - Anderson 20 con ω 0,25, en la malla de 2 cm: 6,2e-7 m. La fila de 2 cm con los ajustes de
      la puerta acaba en la misma continuación, que arranca de la solución saturada y no depende
      del bucle.
  - En la malla de 5 mm ninguna otra vía asienta. Con ω 0,25 y con los ajustes de la puerta
    también asienta la continuación, y da lo mismo a 2,0e-14 m porque es el mismo camino. Ahí
    queda solo el ancla de la teoría (abajo).
  - La revisión a la contra del diff pilló que una primera redacción contaba esos 2,0e-14 m
    como confirmación independiente.
  - El extremo de la cara de rezume coincide con donde la superficie libre corta la cara: 0,194
    frente a 0,192, 0,181 frente a 0,184 y 0,188 frente a 0,188.
  - La salida que da la teoría para esta cara a 135° es la de Casagrande (1937) corregida (Harr
    1990, fig. 3-5c): 0,172 m. Los estados asentados dan 0,18–0,19, con el sesgo de malla que
    midió D274. Los estados de 0.1.355 ponían la cara hasta en 0,49.
  - Los caudales casi no cambian: la entrada se mueve menos de un 0,04 %.
- **El banco no se mueve.**
  - 53 filas permanentes no saturadas × 5 valores de ω = 265 corridas, con 16 rescates (05-009
    núcleo x4 y núcleo_k_min x4; 02-038 Gardner seca con ω 0,6 y 0,8).
  - 0 caminos apartados. El prototipo da lo mismo al bit, con las notas enteras.
- **El defecto también lo encontraba la aplicación,** con los ajustes de su puerta (la fila de
  2 cm).
- **Lo que no es D285, y se abre como D356.** El bucle de Picard tiene un patrón parecido. Con un
  presupuesto explícito de 1, la presa de `test_a_starved_budget…` «converge» a las 29 pasadas
  congelando 33 nodos (7 sin asentar), y el rescate no corre. Es otro mecanismo: el bucle decide
  la cara con el iterado relajado. `test_picard_tolerance_v1272` y `test_transient_coupling_v1125`
  lo fijan a propósito. No se toca aquí; la propietaria decidió abrir D356.
- **Caminos que no llevaron a nada, o casi engañan:**
  - **La presa rectangular de Gardner** de `test_unsaturated_v127` no da la firma con ninguna
    curva, malla, ω, número de pasadas o presupuesto (2, 3 o 5). Hace falta la geometría del 004:
    el foco y la cara a 45°.
  - **Una continuación que falla** (residuo NaN) no deja su segmento en `history_segments`. Un
    rescate `failed` enseña solo «anderson 5» y «anderson 20». El test cuenta las llamadas a la
    continuación en vez de fiarse de los segmentos.
  - **El comparador de la medida.** Un aviso `picard_rescue_failed` lleva en sus `args` el
    residuo del rescate, NaN si la continuación falló, y un NaN no es igual a sí mismo. Dos
    avisos idénticos salían «distintos». Lo encontró la revisión a la contra de los scripts y se
    repitió con una igualdad que trata NaN == NaN.
  - **Anderson 20 no ayudó en ninguno de los tres casos en que se probó tras un rechazo por la
    cara**: congela los mismos nodos que Anderson 5. Se sigue probando por decisión de la
    propietaria: es el orden escrito, y es el camino que resuelve otros casos tras un fallo por
    el residuo (2 cm, ω 0,25).
- **Decisiones de la propietaria:**
  - exigir la cara en cada camino; si ninguno asienta, publicar lo de antes;
  - Anderson 20 en el orden escrito;
  - abrir D356.

## 1. Qué cambia

- **`UnsaturatedSeepageSolver._anderson`.** Cuando un estado baja de la tolerancia con la cara
  quieta, se pregunta además `_unsettled_nodes` sobre esa misma solución. Si queda algún nodo
  sin asentar, el camino termina sin aceptar, marcado `unsettled`: seguir iterando no
  descongela nada.
- **`_continuation_newton`.** Lo mismo en su aceptación final.
- **`_rescue`.**
  - Aparta el primer camino que llegó a la tolerancia con la cara sin asentar y prueba el
    siguiente.
  - Si ninguno asienta, devuelve el apartado como convergido, y la comprobación final de
    `solve_unsaturated` dice que la cara no asentó. Es el estado que publicaba 0.1.355:
    mismas cargas, cara, `rescue`, `rescue_residual`, congelados, sin asentar y aviso.
  - Cambian `iterations`, `rescue_iterations`, `history` e `history_segments`, que recogen
    todos los caminos probados.
- **Interruptor `seepage.RESCUE_SETTLED_FACE`,** con alta en `INTERRUPTORES` del banco como
  (0, 1, 356). Apagado reconstruye 0.1.355.
- **Docstrings.**
  - `_rescue` gana la sección «What a road must settle», con la medida y la decisión sobre
    Anderson 20.
  - `_anderson` y `_continuation_newton`, una frase cada uno.
  - El párrafo `history` de `solve_unsaturated` dice que la serie lleva todos los caminos
    probados y que una continuación que falla antes de t = 1 no deja entrada.
- **No cambian:**
  - el código de `solve_unsaturated` (respeta el censo de frases de v1352);
  - los mensajes;
  - las claves de las notas;
  - el bucle de Picard y el transitorio.

## 2. Tests

`tests/test_rescue_face_v1356.py`, 10 casos, unos 30 s. El caso es el 004 en la malla del
generador a 2400 con la curva «empinada» como USER_DEFINED y una pasada, construido solo con la
API del repositorio.
- **Interruptor apagado, el defecto.** Rescate de Anderson, sin asentar ≥ 1, congelados ≥ 1,
  aviso `seepage.face_unsettled`, 0 llamadas a la continuación. El campo publicado incumple la
  condición de cara. Antes se comprueba que la malla es la medida (2307 T3).
- **Encendido, la continuación lo asienta.**
  - Convergido, los cuatro segmentos, 0 sin asentar y 0 congelados, sin aviso.
  - Cada nodo de la cara cumple la condición. Se juzga con las bandas del solver, pero sin su
    `_unsettled_nodes`.
  - **Ancla (regla 1):** la respuesta es el punto fijo al que llega el bucle solo con 200
    pasadas, con la misma cara y a menos de tol/ω (medido 2,1e-6 m). El campo del defecto queda
    a más de 1 mm (medido 3,7 cm).
- **Ningún camino asienta (presupuesto 1).** Cargas iguales al bit con el interruptor encendido
  y apagado, y también cara, `rescue`, `rescue_residual`, congelados, sin asentar y aviso
  (código y argumentos). Solo crecen las iteraciones (lo mismo que `rescue_iterations`) y la
  serie, cuyo principio es la de antes.
- **Lo que no aparta ningún camino no se mueve:** el rescate de la presa de Gardner de v1269
  (Anderson asienta en su primer camino) y un bucle que converge. Mismas cargas, iteraciones,
  cara y notas enteras con el interruptor encendido y apagado.

## 3. Verificación

- **El test de esta versión**, 10/10, 36 s (con el arranque).
- **Suite entera:** 6504/6504, `EXIT=0`, 74 min. Parte del tiempo corrió a la vez que los A/B.
  - Después se corrigió el comentario del interruptor (abajo) y se repasaron los 8 archivos que
    leen el fuente o tocan el rescate (98/98).
- **A/B árbol contra árbol** (`_auditoria/P6_0356/ab_arbol.py`, el `git archive` de 0.1.355
  frente al árbol de trabajo): **75 filas, 0 distintas**, sin claves de notas nuevas. Son el 05
  entero con las dos mallas, el 02-010, el 02-038 con tres alturas por cuatro curvas, y el
  permanente y el transitorio de la presa del 102.
- **A/B de los casos con la firma** (`ab_d285.py`, que el banco no tiene):
  - **0.1.355 frente a 0.1.356 apagado: 5 de 5 iguales al bit** (cargas, `converged`,
    `iterations`, cara y todas las notas).
  - Encendido: los cuatro naturales convergen, con max\|ΔH\| de 3,7 a 4,75 cm.
  - El de presupuesto 1 solo cambia `iterations` (26 → 126), `rescue_iterations`, `history` e
    `history_segments`.
- **El barrido del banco con el prototipo** (265 corridas): 0 caminos apartados, y las 16
  rescatadas iguales al bit.
- **Banco:**
  - raíz: `verificar_cierres.py` entero, 90 comprobaciones (una más, `d285`), 0 bajadas. D285
    queda **CUBIERTO POR TEST**. Las vecinas de filtración (D124, D265–D269, D274, D279, D280)
    siguen cerrando;
  - manual 02: `verificar_cierres.py` entero, 238 fichas, 0 bajadas;
  - `INTERRUPTORES` (`elegibilidad_critica_d155.py` del 02) gana
    `seepage.RESCUE_SETTLED_FACE` con (0, 1, 356).
- **`d285()` del verificador de la raíz:**
  - CUBIERTO POR TEST en 0.1.356;
  - SIGUE ABIERTO en el `git archive` de 0.1.355;
  - y también si al motor viejo se le pone el atributo a mano: la parte en vivo falla («la
    continuación no asienta», «el respaldo no publica lo de antes»). Discrimina por
    comportamiento, no solo por estructura.
- **Revisión a la contra,** dos rondas con un escéptico por hallazgo:
  - la de los scripts de la puerta encontró el comparador que tropezaba con el NaN (§0);
  - la del diff encontró que el comentario del interruptor y una primera redacción de este
    changelog contaban como confirmación independiente la continuación comparada consigo misma
    (5 mm, 2e-14 m), y decían «de dos a cuatro nodos» donde el caso del test tiene uno.
    Corregido.

## 4. Lo que sigue abierto

- **D356** (P6): el bucle «converge» congelando nodos y no llama al rescate.
- **El caso del test depende de la malla.** Con 2000 o 3000 elementos no aparece. Si la CI de
  Linux, con otro SciPy, triangula de otra forma, el test lo dirá en su primer caso (2307 T3).
  Hay que mirar la CI cuando se suba.

## 5. Lo que no se ha probado

- La gráfica de convergencia de *Interpret Groundwater* con los segmentos de los caminos
  apartados. Dibuja cualquier combinación de segmentos desde 0.1.269, pero no se ha mirado en la
  aplicación con este caso.
- La CI de Linux (no se ha subido).

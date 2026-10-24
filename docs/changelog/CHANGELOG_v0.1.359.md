# OGR Slip2D v0.1.359

**La banda de flujo de la cara de rezume sale de un caudal que existe (D364). Y la presa 2 del
problema 9 en la malla fina, que el rescate no converge con la puerta, se cierra documentada: no
es la banda, la solución existe, y lo que falla son los caminos (D365).**

Un nodo de la cara retenido a P = 0 se suelta cuando le entra agua por encima de la banda de
flujo: 1e-4 del mayor caudal nodal de la primera solución, la saturada. Una presa que solo sale
por su cara tiene un único nivel impuesto y ningún caudal impuesto. Su saturada es ese nivel, sin
caudal, y la banda era redondeo: 5e-24 en la presa del 102 sin cola, cuya cara lleva 1,3e-6.

Desde esta versión, en ese caso la banda se toma de la primera pasada resuelta con la cara
retenida, que es la primera cuya conmutación la lee. Es la regla de cada paso transitorio desde
D269.

## 0. Lo que se encontró

La puerta de medida está en `_auditoria/P6_0359/D364_D365_medida.md` del banco. El motor no se
tocó para medir: se usó un prototipo por parche de clase, con una copia literal de
`solve_unsaturated`, al bit con el motor en 7 de 7 casos (control C0).

- **El hueco de D364 existe, pero en el banco casi nada cae en él.**
  - Se censaron, en el bucle, en Anderson, en la continuación y en la comprobación final, todas
    las decisiones que leen la banda en las 60 corridas degeneradas del barrido (12 filas × 5 ω):
    son 6854.
  - Ninguna tuvo un caudal por debajo de 1e-4 del caudal nodal de la respuesta.
  - Con la banda nueva salen al bit 254 de las 255 corridas.
  - La otra es el 05-011 ×1 con ω 0,3. Hoy se suelta un nodo al que entra 1,9e-4 del caudal
    final; la banda nueva (2,1e-4) lo deja retenido, y la corrida acaba en la misma cara, con las
    mismas 56 pasadas y a 2,3e-8 m (0,007 tol/ω). Cumple el criterio de la propietaria: misma cara
    y dentro de tol/ω.
- **El disparador del plan, un umbral sobre el campo, no servía.**
  - El plan detectaba el caso con «la carga saturada es uniforme hasta 1e-12 relativo». Se saltaba
    la presa 2 del 05-009: su redondeo da 4,3e-12, porque el dren es 500 veces más permeable que
    el núcleo.
  - Se decide por los contornos: un solo nivel impuesto y ningún caudal impuesto. Por unicidad, la
    saturada es entonces ese nivel (las filas de una matriz de conductividad suman cero).
  - Separa exactamente 60 corridas de 195. El rango relativo del campo va de 3e-14 a 7e-12 en las
    degeneradas y de 0,19 en adelante en las sanas.
- **La escala nueva no siempre es del orden del caudal final.** Va de 0,9 a 65 veces el caudal
  nodal de la respuesta, y el 65 es la presa 2 del 05-009: en la pasada 2 toda su cara aguas abajo
  está retenida y el dren la bombea. Aun así es una banda de 6,5e-3 del caudal por nodo, por debajo
  de toda reacción que haya decidido algo.
- **Las 284 decisiones «por debajo de 1e-4 del caudal final» que dio el censo no son de D364.**
  Están en el 02-038 con la curva Gardner seca, una fila sana. Allí la escala saturada es 0,09
  veces el caudal final, el extremo bajo que D356 ya había medido (0,09–2,6). La banda nueva no
  las toca: las 195 sanas, al bit.
- **D365 no es D364.**
  - Con la banda de hoy, con 1e-5, 1e-4 y 1e-3 del caudal real, con la perezosa y con la de un
    «oráculo» (1e-4 del caudal de la convergida), los tres caminos del rescate salen idénticos en
    la ×4.
  - Ninguno cambia la cara: un nodo retenido de principio a fin. La banda solo se lee para soltar
    un nodo retenido.
- **La solución de la ×4 existe con los ajustes de la puerta.** Arrancando de la convergida del
  banco (ω 0,3), Anderson la acepta en 5 evaluaciones (residuo 1,6e-7 m).
- **Anderson depende de su arranque, y del redondeo.**
  - Desde cuatro arranques más (el último iterado del bucle, la saturada, el estado de la
    continuación…) ninguna profundidad llega a la tolerancia.
  - La forma de mezcla de Walker & Ni (2011) con parámetro 1 es algebraicamente el Anderson del
    motor. Desde el mismo arranque acaba a 3,1 m, y el motor a 2,0; con profundidad 20, a 0,049 y a
    3,9.
  - Con mezcla 0,4 y profundidad 5 converge, pero con profundidad 20, y con mezcla 0,2, no. Con ese
    control, un acierto suelto no prueba un arreglo: elegirlo sería ajustar un parámetro a un caso.
- **La continuación se para en t ≈ 0,62, y no es un pliegue.**
  - El paso se parte hasta el mínimo porque la búsqueda lineal de Newton no reduce |R|, que queda
    fijo hasta la octava cifra (con λ hasta 1e-10, también).
  - No es el presupuesto (266 de 1000), ni el presupuesto por paso, ni la cara.
  - El valor singular mínimo del jacobiano baja suave a lo largo de t (8,8e-12, 1,8e-12, 7,7e-13),
    sin desplomarse en el punto en que se para.
  - Apunta a un quiebro de las curvas a trozos, sin medida directa del quiebro. La curva del dren
    baja seis décadas en 2,9 kPa.
- **Es la malla, pero no una sola.** Con los ajustes de la puerta, de 5 mallas (1921 a 4095 T3)
  fallan 2: la ×4, de 3886, y su vecina, de 3691.
  - Las otras 3 convergen, cada una por un camino distinto, con el caudal entre −2,45 % y +0,84 %
    del publicado (4,23e-6 m³/(min m), Chapuis et al. 2001).
  - El 2 % del criterio de cierre de la ficha es más estrecho que la dispersión de la propia malla.
  - Antes de D358, la ×4 convergía siempre por Anderson y nunca llegaba a la continuación.
- **Lo que las fichas temían, y no es.** La banda en el redondeo coincide, en la presa 2, con la
  firma natural de D356 en la ×1 y con el fallo de la ×4, y las dos fichas sospechaban que una
  banda nula invitaba a conmutar por redondeo. No se sostiene. En la ×1, con la banda nueva, el
  bucle hace las mismas 97 sueltas y llega al mismo estado al bit; en la ×4, la cara ni se mueve.
- **Decisiones de la propietaria en la puerta:**
  - D364, la escala perezosa con interruptor;
  - D365, CIERRE DOCUMENTAL, con la medida en el docstring de `_rescue`, y una ficha nueva (D366)
    para un rescate robusto ante curvas casi escalón;
  - las dos en esta versión.

## 1. Qué cambia

- **Interruptor `seepage.FACE_FLUX_SCALE_FROM_FLOW`,** con alta en `INTERRUPTORES` del banco como
  (0, 1, 359). Apagado reconstruye 0.1.358.
- **`UnsaturatedSeepageSolver._saturated_carries_no_flow(bcs)`:** un solo nivel impuesto (los
  `TOTAL_HEAD`, `PRESSURE_HEAD` y `ZERO_PRESSURE` resueltos en carga total), ningún `NODAL_FLOW`
  distinto de cero y ningún segmento con caudal. Dos niveles que difieren en un ulp cuentan como
  dos: en la duda, la banda de antes.
- **`solve_unsaturated`.** Si la saturada no tiene caudal, la banda se toma de la primera pasada
  resuelta con la cara retenida, antes de su conmutación. La usan después el rescate y la
  comprobación final. Si el bucle no llega a retener la cara, queda la de antes.
- **`_face_q_tol` no cambia.** Su firma y sus valores los fija v1284; su docstring dice ahora de
  dónde sale la escala.
- **Docstrings:**
  - `solve_unsaturated`: una sección sobre el modelo que solo sale por su cara;
  - `_rescue`: el cierre documental de D365, con la medida;
  - el comentario de las bandas.
- **No cambian:** el transitorio (cada paso ya tomaba su escala de su primera solución), los
  mensajes, las claves de las notas y el resultado publicado del banco.

## 2. Tests

- **`tests/test_face_flux_scale_v1359.py`,** 8 casos, unos 15 s, con la presa del 102 de
  `test_transient_coupling_v1125` a 1200 elementos.
  - **El detector.** Con un nivel y sin caudal impuesto, la saturada ES el nivel (a menos de 1e-9
    relativo) y su mayor caudal nodal es menos de 1e-12 del de la cara: la identidad, y lo que era
    la banda vieja. Dos niveles, o un nivel con un caudal nodal o con infiltración, no disparan.
  - **Sin cola, encendido:** toda banda que la conmutación lee con la cara retenida es 1e-4 de una
    escala entre 0,5 y 5 veces el mayor caudal nodal de la respuesta (medido 1,5). **Apagado:**
    redondeo, por debajo de 1e-20 (medido 5e-24). Regla 7: el interruptor mueve el número para el
    que existe.
  - **En esta presa la banda nueva no decide nada:** cargas, cara, iteraciones y notas, iguales
    con el interruptor encendido y apagado.
  - **Con cola,** la saturada tiene caudal: la banda es la suya, encendido y apagado, y la
    respuesta no se mueve.

## 3. Verificación

- **Selección dirigida:** los 10 archivos de filtración y rescate vecinos, el censo de v1352, las
  versiones y la licencia. 172 de 173; la que faltaba era este changelog.
- **Suite entera:** 6536/6536, `EXIT=0`, unos 110 min.
  - Corrió a la vez que los dos volcados del A/B, el barrido final y los dos verificadores de
    cierres: el reloj no es una medida.
  - Después solo se tocaron los README (el contador, 6528 → 6536). Sus tests y el de nombres
    comerciales pasan.
- **A/B árbol contra árbol** (`_auditoria/P6_0356/ab_arbol.py`, el `git archive` de 0.1.358 frente
  al árbol de trabajo): **73 filas, 1 distinta, sin claves de notas nuevas.**
  - La distinta es el 05-011 ×1, a 2,256e-8 m: la misma que predijo el barrido del prototipo.
  - El resto, al bit: el 05 entero, el 02-010, el 02-038 y el permanente y el transitorio del 102.
- **Barrido del banco con el motor de esta versión frente al prototipo** (255 corridas): **255 de
  255 iguales al bit.** El motor reproduce la medida de la puerta, así que frente a 0.1.358 se
  mueve solo la corrida del 05-011.
- **`d364()` y `d365()` del verificador de la raíz.**
  - En 0.1.359:
    - D364, CUBIERTO POR TEST, en vivo: el 102 sin cola con la banda en 2,00e-10 (1,53 veces 1e-4
      del caudal), apagado 5,1e-24, la misma respuesta; con cola, la banda de la saturada;
    - D365, CIERRE DOCUMENTAL: la medida archivada y la decisión en el docstring de `_rescue`.
  - En el `git archive` de 0.1.358, las dos SIGUE ABIERTO.
- **Banco:**
  - **raíz:** `verificar_cierres.py` entero, 94 comprobaciones (dos más, `d364` y `d365`), 0
    bajadas. Ningún detalle cambia frente a la línea base, tampoco los de D124, D280 y D356, que
    resuelven la presa 2 y el Charnyi en vivo;
  - **manual 02:** `verificar_cierres.py --seco` entero, 242 fichas, todas con el veredicto de su
    línea base;
  - `INTERRUPTORES` (`elegibilidad_critica_d155.py` del 02) gana
    `seepage.FACE_FLUX_SCALE_FROM_FLOW` con (0, 1, 359). La tabla cubre los 55 interruptores del
    motor;
  - D364 y D365 retiradas, con la historia en `Evaluaciones/0.1.359/`;
  - `PAQUETES["P6"]` = D366, y D364 y D365 tachadas en la cadena;
  - D366 abierta con ficha y prompt largo. La cabecera dice D367 libre;
  - prompts: 45 (28 largos y las 17 FALTA de antes), 0 sin paquete; citas, las 19 rotas de antes,
    ninguna de D366;
  - auditorías: 0 ERROR en los dos bancos;
  - instantáneas de 0.1.359 forzadas tras retirar: raíz 849 archivos y 02 3284.

## 4. Lo que sigue abierto

- **D366 (P6, nueva):** un rescate robusto ante curvas casi escalón. Los candidatos con fuente
  son: una búsqueda lineal no monótona en la continuación (Grippo, Lampariello & Lucidi 1986), la
  continuación por longitud de arco (Allgower & Georg 1990), por si hubiera un pliegue que esta
  medida no ve, y Anderson con reinicio por estancamiento.
- La presa 2 del 05-009 en la malla ×4 sigue saliendo no convergida con los ajustes de la puerta.
  El banco la publica con ω 0,3, con la que converge.

## 5. Lo que no se ha probado

- La CI de Linux (no se ha subido).
- La gráfica de convergencia de *Interpret Groundwater* con un caso de la banda nueva: nada en ella
  cambia, porque la banda no se publica.

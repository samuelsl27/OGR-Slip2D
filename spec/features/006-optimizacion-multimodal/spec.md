# Optimización multimodal

## Qué hace

Devuelve **varios mínimos locales significativos** en vez de uno solo, con una
búsqueda por enjambre de partículas, y añade la **superficie anisótropa** que
orienta el buzamiento allí donde cambia con la posición.

Tres piezas. La primera se midió antes que nada porque podía sesgar a las
otras, y acabó no cambiando producción — pero saberlo era condición para que
las otras dos signifiquen algo:

1. **El eje de momentos, medido y NO cambiado.** Se midió que una poligonal
   inscrita en un arco no reproduce el arco (Ordinary −4,7 %, Bishop −4,2 %,
   convergido) porque el eje se construye desde la cuerda y cae a 65 m del
   centro. Se probó el centro del círculo de mejor ajuste, **y la medición lo
   rechazó**: contra la tabla de siete métodos que la referencia publica para
   dos superficies no circulares, el eje actual clava Ordinary a seis cifras y
   el ajuste se va a +0,93 % y +3,13 %. Queda como **anomalía D47 medida**, con
   un test que sujeta las dos mitades.
2. **La optimización multimodal.** Búsqueda por enjambre, con modo de un mínimo
   y modo de varios, y un radio de agrupación que decide qué mínimos son
   distintos.
3. **La superficie anisótropa.** Una polilínea que orienta el buzamiento allí
   donde la anisotropía cambia de dirección con la posición, en vez del único
   ángulo global desde la horizontal que hay hoy.

## Por qué

Un talud rara vez tiene una sola región crítica. Una búsqueda unimodal
converge a la más desfavorable y **no dice que existan otras**, que es
justamente lo que el ingeniero necesita saber para decidir dónde refuerza. El
problema 103 del banco existe para enseñar eso: al variar la relación de
resistencia entre dos capas no drenadas el mecanismo crítico salta de profundo
a somero, y en el salto **coexisten los dos**.

El eje se midió primero porque un mínimo sesgado no vale nada. Resultó que el
sesgo existe pero **no es corregible sin perder el acuerdo con lo publicado**:
es una propiedad de aplicar un método de sólo momentos a una superficie sin
centro de rotación, y el convenio que OGR usa es el de la referencia,
verificado ahora a seis cifras. El número queda escrito porque acota lo que
significa un factor de seguridad no circular — y es la magnitud de la anomalía
del problema 41.

## Criterios de aceptación

### El eje de momentos — criterio cumplido, con el resultado contrario

- [x] Con el eje forzado al centro verdadero, una poligonal inscrita reproduce
      el arco dentro del 0,5 % en los **nueve** métodos. Es el control positivo:
      dice que rebanado, marco de base y sumas de momentos son correctos y que
      lo único en juego es la elección del punto.
- [x] Con el eje automático **no** lo reproduce, y la deriva no encoge al
      refinar: Ordinary −4,7 %, Bishop −4,2 %; Spencer y GLE, inmunes.
- [x] Medido contra la tabla publicada de siete métodos: el eje actual da
      Ordinary a seis cifras en las dos superficies; el de mejor ajuste se va a
      +0,93 % y +3,13 %. **El cambio se retira**: cambiarlo empeoraría el
      acuerdo con lo publicado para satisfacer una identidad que la propia
      fuente no satisface.
- [x] Ningún modelo se mueve un dígito, porque producción no cambia.

### La optimización multimodal

- [ ] Sobre el problema 103 con la geometría publicada, el modo de varios
      mínimos devuelve **dos** mínimos significativos en los ratios 1,5 y 1,6,
      y los identifica como profundo (tangente al firme) y somero (tangente a
      la cota del pie).
- [ ] El ratio de cruce cae en **[1,5 · 1,6]**, que es donde el manual dice que
      lo pone el equilibrio límite, y contiene el **P_crit = 1,5** que publica
      la Tabla 2 de Guo y Griffiths (2020) para cot β = 2,0 y D = 2,0.
- [ ] La **proporcionalidad de la rama profunda**: F(1,5)/F(1,4) reproduce el
      1,0617 publicado dentro del 1 %. Cancela el sesgo común de búsqueda.
- [ ] La **rama somera no depende de c_u2**: es una identidad exacta, porque
      ese mecanismo no toca el cimiento.
- [ ] El modo de un mínimo devuelve exactamente uno, y no mayor que el menor
      de los que devuelve el modo de varios.
- [ ] Dos corridas con la misma semilla dan el mismo resultado.

### La superficie anisótropa

- [ ] Una superficie **recta** a α grados da exactamente el mismo factor que
      `bedding_angle = α` global: identidad, dígito a dígito.
- [ ] Un material **sin** superficie asignada no se mueve un dígito.
- [ ] Una superficie **plegada** mueve el número.
- [ ] El ángulo se toma del **punto más cercano** de la polilínea, no de la
      vertical; y si el punto más cercano es un vértice, del segmento
      **dibujado primero**, así que invertir el orden de los vértices puede
      cambiar el resultado — y hay un test que lo demuestra.

### Reglas del proyecto

- [ ] Cada ajuste nuevo mueve el número (regla 7): uno/varios mínimos, radio de
      agrupación, número de partículas, número de iteraciones, enjambre
      mejorado.
- [ ] *Add Anisotropic Surface* está en el menú **Boundaries**; el enjambre se
      elige en *Surface Options*; el modo de varios mínimos está en el menú
      **Data** de la ventana de interpretación (regla 3).
- [ ] Todo texto nuevo pasa por `tr()` y tiene entrada en español (regla 2).
- [ ] `Show GM Surfaces` **dibuja** y `Pick GM Surfaces` **selecciona**: hoy la
      primera sólo escribe un mensaje en la barra de estado y la segunda abre
      un diálogo modal y tira lo que el usuario elige.

## Validación numérica

- **El eje de momentos**: dos anclas, y se contradicen, que es el resultado.
  Una **identidad cerrada** —una poligonal inscrita en un arco es el arco en el
  límite, así que su factor tiene que converger al del arco— y la **tabla de
  siete métodos** que la referencia publica para dos superficies no circulares
  dibujadas a mano. La identidad falla con el eje actual y se cumple con el
  centro verdadero; la tabla dice lo contrario, y a seis cifras. Manda la tabla,
  porque es externa y porque la identidad tampoco la cumple quien publica los
  números. Queda como anomalía **D47** medida.
- **El problema 103**: la geometría entera la publican **Guo, S. y Griffiths,
  D.V. (2020)**, «Failure mechanisms in two-layer undrained slopes»,
  *Canadian Geotechnical Journal* **57**(10) 1617-1621,
  doi 10.1139/cgj-2019-0642 — `c_u1 = 60 kPa`, `γ = 20 kN/m³`, `H = 18 m`,
  `cot β = 2,0`, `D = 2,0` —, y su **Tabla 2** publica `P_crit` para treinta
  combinaciones de `cot β` y `D`. El manual del banco publica ocho factores de
  seguridad **dentro de la figura 103.3** y la tabla de materiales
  (60 / 84 / 90 / 96 kPa).
- **El enjambre**: Kennedy, J. y Eberhart, R. (1995), «Particle swarm
  optimization», *Proc. IEEE Int. Conf. on Neural Networks*, 1942-1948.
- **La forma multimodal** (dos vecinos más próximos como atractores): Qu, B.Y.,
  Suganthan, P.N. y Das, S. (2013), «A distance-based locally informed particle
  swarm model for multimodal optimization», *IEEE Trans. Evol. Comput.*
  **17**(3) 387-402.
- **El radio que separa un mínimo de otro**: Li, X. (2004), «Adaptively
  choosing neighbourhood bests using species in a particle swarm optimizer for
  multimodal function optimization», *GECCO 2004*, LNCS **3102** 105-116.
- **El contexto en taludes**: Cheng, Y.M., Li, L., Chi, S.-C. y Wei, W.B.
  (2007), «Performance studies on six heuristic global optimization methods in
  the location of critical slip surface», *Computers and Geotechnics* **34**(6)
  462-484.
- **La superficie anisótropa**: por identidad contra el ángulo global, que ya
  está validado con los modelos anisótropos existentes.

## Fuera de alcance, y por qué

- **La Tabla 105.1 del problema 105.** Se implementa la superficie anisótropa
  que le falta, pero su geometría es la de un tutorial que **no está
  publicado** —ni en el manual ni en la documentación de referencia local— y su
  figura no lleva ejes ni cotas. Reconstruirla midiendo píxeles daría un número
  que parece que funciona, que es el peor resultado posible aquí. Lo que sí se
  comprueba es el **invariante del algoritmo** que ese problema afirma: el
  mínimo más crítico de la búsqueda multimodal concuerda con el de la unimodal.
- **Partículas elípticas.** La referencia las ofrece junto a las circulares; el
  103 no las necesita y la parametrización de una elipse en este espacio no
  está publicada.
- **La política heurística de capas débiles**, que en la referencia sólo existe
  sobre el enjambre. Ahora tendría dónde engancharse, pero su regla no está
  documentada y aproximarla sería inventarla. Se anota que quedó desbloqueada.
- **La deriva de la optimización sobre la rama profunda** (1,0393 con doce
  vértices, contra 1,215 publicado). Se mide y se reporta con número propio;
  arreglarla es otro trabajo, y puede que el del eje ya la mueva.

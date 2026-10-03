# OGR Slip2D v0.1.246

**D229: la Discrete Function es la de la referencia, y la de OGR pasa a
llamarse «Step Function (σ′ₙ)».** Hasta 0.1.245, el modelo llamado Discrete
Function era un escalón de τ en σ′ₙ. La Discrete Function de la referencia es
otra cosa: la resistencia se da en puntos x, y de un material y se interpola
en la base de cada dovela, cu sin drenaje o c y φ drenado. Ahora OGR tiene las
dos: la de la referencia con su nombre, y el escalón con uno propio,
declarado como extensión.

Quinta versión de la tanda D226–D232, tras las cuatro de D226.

## 0. Lo que se encontró, y dónde

- **Banco:** 0 de 230 modelos usan `discrete_function`. El cambio no puede
  mover un número del banco.
- **La ayuda de la referencia** (*Discrete Function* e *Interpolation
  Method*) dice:
  - que la resistencia se da «at discrete x,y locations throughout a
    material» y se interpola;
  - que es sin drenaje (cu, φ = 0) o drenada (c y φ, interpolados por
    separado);
  - que el método de interpolación es el del proyecto. Lo describe para
    Inverse Distance (Shepard 1968), TIN, Thin Plate Spline (Franke 1985),
    Local TPS, Chugh, Chugh modificado, Kriging y Linear by Elevation;
  - que donde el método no puede responder responde un secundario: el TPS
    local con los 10 puntos más próximos y, si falla, Inverse Distance.
- **La rejilla de presiones de OGR** ya tenía el TPS clásico y el IDW. Se
  mueven tal cual a un módulo compartido, para que la rejilla dé los mismos
  dobles.
- **Una prueba fallida que se cuenta.** El test del cambio de tipo en el
  diálogo falló al principio con «objeto C++ ya borrado»: no guardaba la
  referencia al diálogo y el recolector se lo llevaba con sus combos. Era el
  test, no el diálogo.

## 1. El motor

- **`ogr_core/interpolation.py`** (nuevo):
  - `tps_fit`, `tps_value` e `idw_value`, movidos sin cambios desde la
    rejilla, que ahora los llama;
  - `ScatteredField`, con Inverse Distance (Shepard 1968, potencia 2 sobre
    todos los puntos, como lo escribe la referencia), TIN (Delaunay de
    `scipy.spatial` y el plano del triángulo), Thin Plate Spline (el clásico,
    Harder y Desmarais 1972; Duchon 1976) y Linear by Elevation (solo y; fuera
    del rango, el valor del extremo; varios puntos a una misma cota cuentan
    por su media);
  - el secundario, TPS local con 10 puntos y luego Inverse Distance.
  - Chugh, Chugh modificado, el TPS local como método propio y el Kriging no
    se implementan: se dice, no se aproxima.
- **`StepFunction`** (`step_function`, «Step Function (σ′ₙ)»): el modelo que
  hasta ahora se llamaba Discrete Function, sin cambiar una línea de su
  cálculo.
- **`DiscreteFunction`** (`discrete_function`): la de la referencia.
  - Sin drenaje, τ = cu(x, y); drenada, τ = c(x, y) + σ′ₙ·tan φ(x, y).
  - (x, y) es el centro de la base de la dovela: `SliceContext` gana `x_base`,
    que `from_slice` lee de la dovela y los soportes de su punto.
  - Después de interpolar, cu y c se recortan a 0 y φ a [0, 90), porque un
    spline puede pasarse.
  - Sin punto donde leer (una gráfica de la envolvente, una llamada sin
    dovela), se lee en el centroide de sus puntos.
  - Coeficientes de diseño: sin drenaje, la categoría cu; drenada, c′ y tan φ′.
    Dividen lo INTERPOLADO, con divisores que lleva la copia, como la C/Phi
    Function.
- **Migración.**
  - Un `discrete_function` de un archivo con puntos (σ′ₙ, τ) se lee como
    `StepFunction`, con el mismo τ bit a bit: no se rechaza nada, porque
    ningún número cambia.
  - Sin `function_type`, filas de tres o cuatro valores dicen si es sin
    drenaje o drenada.
- **Regla** `discrete_function_refusal`, preguntada por
  `strength_model_refusal` (el diálogo, la API y el análisis): tipo y método
  conocidos, al menos un punto, filas de (x, y, cu) o (x, y, c, φ) finitas,
  cu y c ≥ 0, 0 ≤ φ < 90, y dos puntos nunca en el mismo sitio.

## 2. La interfaz y la API

- **Diálogo de materiales.** La Discrete Function tiene:
  - su tipo de función;
  - su método de interpolación, con una pista sobre el secundario;
  - una tabla de puntos con columnas x, y, cu o x, y, c, φ en las unidades
    del proyecto.

  Cambiar el tipo conserva los puntos: un cu pasa a c con φ = 0, y al volver
  se queda la c. La Step Function conserva la tabla de σ′ₙ de siempre.
- **API.** `model_define` acepta `function_type`, `method` y `points` por los
  campos extra del modelo, sin código propio.

## 3. Tests

**`tests/test_discrete_function_v1246.py`** (17 casos):

- **Un campo constante** es el material Undrained o Mohr-Coulomb de esa
  constante, en los nueve métodos y con los cuatro interpoladores. Medido:
  1,6e-14 en el peor caso.
- **Un campo plano** sale exacto con TIN dentro del casco y con el spline;
  fuera del casco del TIN responde el secundario.
- **A mano:** Inverse Distance con tres puntos, Linear by Elevation dentro y
  fuera del rango, c y φ interpolados por separado y recortados.
- **El punto de lectura.** En el círculo φ = 0, Bishop es
  Σ cu(xᵢ, yᵢ)·lᵢ / Σ W·sen α, con el empuje sacado de una corrida uniforme.
  Además, un campo que cambia de lado mueve el número, y un soporte lee el
  campo en su punto.
- **Coeficientes:** Γ = F/1,4 con γcu y Γ = F/1,25 con γc′ y γφ′.
- **Migración, ida y vuelta, regla, API y diálogo en psf**, incluido el cambio
  de tipo.

**Discriminación** contra `git archive` f9a767c (0.1.245), con el runner de ese
árbol: **17 de 17 fallan**, casi todos por símbolo, porque el modelo de la
referencia no existía.

**Cambian a propósito** los tests que fijaban el escalón con el nombre viejo:

- `test_strength_models_v115::TestDiscreteFunction`, ahora
  `TestStepFunction`;
- `test_material_tables_units_v1227::test_the_discrete_function_shows_its_own_default`,
  ahora `..._step_function_...`, y la lista de tablas vacías gana
  `step_function`;
- `test_material_sat_uw_v160::test_discrete_function_keeps_its_points`, ahora
  `..._step_function_...`.

## 4. El banco

- **Censo:** 0 de 230 modelos con `discrete_function`.
- **A/B árbol contra árbol de todo el 02** (`_auditoria/P4_0246/ab_d229.py`):
  194 modelos, **0 de 1821 números distintos**. La rejilla de presiones y el
  contexto de las dovelas no se han movido.
- **`d229()`, CUBIERTO POR TEST.** Comprueba en vivo que un campo constante es
  el Undrained con los cuatro interpoladores, el IDW a mano, que un campo que
  cambia de lado mueve el factor y la migración. Comprueba además el censo, el
  A/B y la discriminación. Contra el motor de 0.1.245 dice NO SE SOSTIENE.
- **Ciclo de cierre:**
  - `verificar_cierres.py` entero: 216 cierres y 0 bajadas, tras el ajuste de
    D228 (§0);
  - instantánea `Evaluaciones/0.1.246`;
  - D229 retirada al índice, podada de `PAQUETES` y tachada en la cadena P4,
    que queda con D230 → D231;
  - prompts regenerados (42);
  - auditorías con 0 ERROR en el 02 y en la raíz;
  - instantánea rehecha con `--forzar`;
  - `--seco` completo después de retirar.

- **Una bajada que no lo era: D228.** La primera verificación de cierres dio
  NO SE SOSTIENE en D228, el buzamiento local que leen los soportes. Su parte
  en vivo se sostenía bit a bit; lo que fallaba era una comprobación de texto
  que buscaba `"bedding_angle_deg")` como final de los `__slots__` de
  `_PointAsSlice`, que desde esta versión acaban en `"x_centre"`. La
  comprobación busca ahora el slot y no su posición, y D228 vuelve a CUBIERTO
  POR TEST.

## 5. Lo que se reporta y NO se corrige

- **El TPS de la referencia es el de Franke (1985) con tensión**, y el de OGR
  el clásico. Ya estaba documentado en la rejilla.
- **Los métodos que no se implementan** (Chugh, Chugh modificado, el TPS local
  como método propio y el Kriging) se rechazan con la regla. No se aproximan.

## 6. Verificación

- **Suite entera:** 5460 de 5460, en 79,5 min, con dos verificaciones
  enteras de cierres en paralelo.
- **Selección** de rejillas, materiales, resistencia, soportes, adherencia,
  arrancamiento, helicoidales, Ito-Matsui, C/Phi, la discreta, validación de la
  API, operaciones, `model_define`, i18n e interpolación: 817 de 817.
- **Test nuevo:** 17 de 17. Discriminación: 17 de 17 contra 0.1.245.
- **Banco:** censo, A/B (0 de 1821), `d229()` y el ciclo de cierre (216
  cierres, 0 bajadas).

**Qué falta por probar:**
- **Un caso publicado con Discrete Function:** ningún problema de los manuales
  la usa.
- **Que el campo se vea en el modelo**, los símbolos de los puntos que dibuja
  la referencia: no se ha implementado.

# OGR Slip2D v0.1.244

**D226c: las presiones intersticiales que leen el peso siguen al peso que la
norma factorizó.** Afecta a Ru, al exceso de presión del método B̄ y al agua
que integran en las caras entre dovelas Lowe-Karafiath y los dos Corps of
Engineers.

Hasta 0.1.243 esas presiones se calculaban con el peso SIN factorizar,
mientras el peso sí se factorizaba. Una norma de diseño hacía parecer un
talud MÁS seguro que su modelo característico.

Ahora se calculan con el mismo peso que la dovela, como hace la referencia: un
solo peso por dovela para todos los términos, la presión intersticial
incluida.

Cuarta versión de la tanda D226–D232, y la tercera de las cuatro de D226. La
ficha sigue abierta hasta D226d.

## 0. Lo que se encontró, y dónde

### La premisa, medida con 0.1.243

Talud de `test_tension_crack_truncation_v1109` con c′ = 0 y φ′ = 40°, seco salvo
la presión que se mide, círculo (55; 58) R 34, 160 dovelas y los nueve métodos
a 1e-12. Con EC7 DA1-C1 (γG 1,35 con la fuente única, M1 = 1), si la presión
sigue al peso todo escala por 1,35 y la homogeneidad da Γ = F:

| Presión | Γ/F con 0.1.243 | Γ/F con 0.1.244 |
|---|---|---|
| ninguna (seco) | 1,000000 | 1,000000 |
| Ru = 0,25 | **1,085–1,094** | 1,000000 |
| B̄ = 0,5, el peso del material carga | **1,233–1,291** | 1,000000 |
| terraplén que carga una arcilla de B̄ = 0,6 | **1,128** (Bishop) | 1,000000 |

Del lado inseguro: con la norma el peso subía y la presión no, así que la
tensión efectiva y la resistencia crecían más que el empuje.

### Tres lectores del peso, no dos

El plan nombraba Ru, el B̄ de las cargas y «el empuje entre dovelas de
Lowe-Karafiath». Leído el código, son estos:

- **Ru** (`pore_pressure_at`): u = ru·(γ·z + γw·d). El término del suelo lleva
  ahora el factor de la dovela; el agua embalsada no, porque no es suelo.
- **El exceso de B̄** (`excess_at`): Δσv sale de las bandas cuyo peso carga
  (con el factor del suelo de la dovela), de las cargas que crean exceso (cada
  una con su factor de D226b) y del término sísmico, que es una fracción del
  del suelo y lo sigue. Esto cierra el hueco que 0.1.243 dejó declarado: desde
  esa versión el exceso leía las cargas sin factorizar.
- **El agua en las caras entre dovelas** (`external_forces.interslice_water_thrust`):
  la integran los tres métodos de inclinación prescrita, Lowe-Karafiath y los
  dos Corps. Con Ru, cada muestra de la cara lee el peso; la cara toma el
  factor de la dovela de su izquierda, la misma que ya le da el material.

### Por qué una segunda pasada

La presión se calcula al rebanar, dovela a dovela, y el factor de una dovela
sale del sentido de deslizamiento de toda la masa, que solo existe con todas
las dovelas hechas. Por eso el bloque de presiones del rebanador pasa a una
función, `_base_pore_pressure`, sin cambiar una línea. `design_actions` la
vuelve a llamar, con los factores, solo donde el material lee el peso y algún
factor no es 1. El punto donde se pregunta son los mismos dobles que guardó la
dovela.

### Lo que no se toca

- **Un material cuya presión no lee peso** (nivel freático, piezométrica,
  rejilla, filtración, constante) no cambia: comprobado bit a bit.
- **La u de los anclajes** (`bond.py`) sigue sin el factor, y es D226d.
- **El desembalse** (`rapid_drawdown.py`, su u inicial con Ru) queda fuera: es
  otro camino de análisis y se declara.

### El banco no tiene ninguna norma, pero todos pasan por la función nueva

Toda dovela de todo modelo pasa ahora por `_base_pore_pressure`, y ningún
interruptor deshace eso. Se compara **árbol contra árbol** (04dfb17, 0.1.243,
frente a este) sobre TODOS los modelos del 02: los círculos publicados y las
críticas archivadas.

Son 194 modelos, sin error en ninguno, entre ellos los de los problemas 018,
021, 022, 036, 041 y 062, que tienen los 8 materiales con Ru del banco. Dan
1821 números en 4306 hojas, **0 distintos**.

## 1. El motor

- **`pore_pressure_at(..., weight_factor=1.0)`.** Ru multiplica por él su
  término del suelo; con 1 no toca nada.
- **El exceso.**
  - `load_delta_sigma_v(..., load_factors=None)`, `delta_sigma_v_at` y
    `excess_at(..., weight_factor, load_factors)`;
  - sin argumentos, las mismas sumas en el mismo orden.
- **`slicer._base_pore_pressure`:** el bloque de siempre (presión, política
  de no saturados y exceso).
- **`slicer.reads_the_weight(project, material)`:** Ru, o B̄ > 0 con el exceso
  activado.
- **`design_actions.refresh_pore_pressures`**, al final de
  `apply_action_factors`: vuelve a preguntar la presión de cada base que lee
  el peso, con el factor de su dovela y los de las cargas.
- **`interslice_water_thrust`** pasa el factor de la dovela a cada muestra de
  la cara.
- **Interruptor `ogr_slip2d.slicer.DESIGN_PORE_PRESSURE_FOLLOWS_WEIGHT`.**
  - Apagado, el comportamiento de 0.1.243.
  - Entra como el 36.º en `INTERRUPTORES`.

## 2. Tests

**`tests/test_design_pore_pressure_v1244.py`** (11 casos):

- **Homogeneidad en los nueve métodos.** Con c′ = 0 y todas las acciones
  permanentes escaladas igual (DA1-C1 con la fuente única, y γG = γG,fav =
  1,35 dovela a dovela), Γ = F:
  - con Ru;
  - con un B̄ cuyo peso se carga a sí mismo;
  - con un terraplén que carga una cimentación de B̄ > 0, comprobando antes
    que la carga llega.
- **A mano:**
  - Ru bajo agua embalsada, u = ru·(ξ·γ·z + γw·d), con ξ = 1 y ξ = 1,35;
  - dovela a dovela, cada base con el ξ de su dovela (1,35 o 0,9);
  - una carga que crea exceso añade B̄ por su tensión factorizada: 13,5 bajo
    una permanente que empuja, y 0 bajo una variable que resiste, que queda
    fuera y su exceso con ella.
- **El agua en las caras** escala con el factor del suelo, a 1e-12.
- **Nada más se mueve:**
  - sin norma, u es la fórmula de siempre;
  - un material que no lee peso, bit a bit;
  - con el interruptor apagado, 3,089071, el número de 0.1.243;
  - el proyecto del usuario, intacto.

**Discriminación** contra `git archive` 04dfb17 (0.1.243), con el runner de ese
árbol: **8 de 11 fallan**, 7 por comportamiento y 1 por símbolo (el
interruptor). Pasan los tres controles: el material que no lee peso, la
fórmula sin norma y el proyecto intacto.

## 3. El banco

- **Censo:** 0 de 230 modelos con la norma activada.
- **A/B árbol contra árbol de todo el 02** (`_auditoria/P4_0244/ab_d226c.py`):
  194 modelos, 0 de 1821 números distintos.
- **`INTERRUPTORES`** gana `slicer.DESIGN_PORE_PRESSURE_FOLLOWS_WEIGHT`.
- **D226 no se cierra:** el cierre llega con D226d.

## 4. Lo que se reporta y NO se corrige

- **El desembalse** con Ru y norma de diseño lee su u inicial sin el factor.
  Es otro camino de análisis.
- **La u en el punto de un anclaje** sigue sin el factor. Es D226d, con la
  casilla de la referencia.

## 5. Verificación

- **Suite entera:** 5429 de 5429, en 42,5 min, con el A/B y la verificación de
  los cierres en paralelo.
- **Test nuevo:** 11 de 11. Discriminación: 8 de 11 contra 0.1.243.
- **Banco:**
  - censo (0 de 230 con norma) y A/B árbol contra árbol de todo el 02 (0 de
    1821);
  - `verificar_cierres.py` entero: 214 cierres y 0 bajadas;
  - instantánea `Evaluaciones/0.1.244`;
  - prompts regenerados (44);
  - auditorías de invariantes con 0 ERROR en el 02 y en la raíz;
  - instantánea rehecha con `--forzar`.

**Qué falta por probar:**
- **Un caso publicado con Ru o B̄ y norma:** no hay ninguno.
- **El desembalse con norma** (§4).

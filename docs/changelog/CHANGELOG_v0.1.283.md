# OGR Slip2D v0.1.283

**El presupuesto de conmutaciones de la cara de rezume escala con la
relajación (D279).** Con una relajación lenta, un nodo de la cara agotaba sus
25 conmutaciones antes de que el iterado se asentara. Se congelaba retenido a
P = 0 con agua entrando, y el resultado salía no convergido. El rescate de D124
no podía entrar: un conjunto congelado ya no cambia, así que el bucle «acaba».

## 0. Lo que se encontró

- **El caso de la ficha** (medido en D267, `_auditoria/P6_0272/`): la presa
  rectangular de Gardner de `test_unsaturated_v127` con ω = 0,1.
  - El nodo 34, al pie de la cara, agota las 25 conmutaciones.
  - El resultado queda a 0,129 m del punto fijo, con `converged = False`, un
    nodo congelado y el aviso de que la cara no asentó.
  - Con 50 conmutaciones o más converge a 1,3 tolerancias.
- **Decisión de la propietaria:** escalar el presupuesto con 1/ω, frente a
  dejar que el rescate entre con la cara sin asentar (que revisa D124 y toca
  `test_a_starved_budget`) o declararlo.

## 1. Qué cambia

- **`UnsaturatedSeepageSolver.max_node_switches`** pasa a ser una propiedad.
  - Toma el valor dado al constructor o, si no se da, max(25, ceil(10/ω)).
  - 10/ω vale 25 en ω = 0,4, la de la puerta, así que la puerta y todo
    ω ≥ 0,4 conservan exactamente el presupuesto que tenían.
  - Con ω = 0,3 sale 34; con 0,2, 50; con 0,1, 100.
  - Se lee al usarse, así que el permanente inicial de un transitorio,
    resuelto con la ω de la puerta (D277), recibe el presupuesto de esa ω.
- **Interruptor `SWITCH_BUDGET_SCALES_WITH_OMEGA`,** con alta en
  `INTERRUPTORES` como (0, 1, 283).
- **Un presupuesto dado explícitamente no se escala.**
  `test_a_starved_budget…` (presupuesto 1) sigue igual.

## 2. Tests

`tests/test_switch_budget_v1283.py`, 5 casos:
- la fórmula para ω de 1 a 0,1;
- un presupuesto dado no se escala;
- apagado, vuelve a 25;
- con el presupuesto por defecto, ω = 0,1 converge en la presa, sin nodos
  congelados, a menos de 2 tolerancias del punto fijo resuelto a 1e-12;
- apagado, se vuelve a congelar.

`test_picard_tolerance_v1272::test_is_reported_and_not_passed_off_as_converged`
pide ahora el presupuesto de 25 explícitamente. Su intención (un presupuesto
agotado se notifica y no se presenta como convergido) no cambia.

## 3. Verificación

- **A/B en el mismo proceso** (`_auditoria/P6_0283/ab_d279.py`): las 53 filas
  permanentes no saturadas de D266 (el 05 en sus dos mallas, el 02-010 y el
  02-038) con ω = 0,2 y 0,3, que es donde el presupuesto cambia. Resultado:
  **106 corridas, 0 distintas**, porque ninguna fila del banco agotaba 25
  conmutaciones.
- **A/B árbol contra árbol** (0.1.282 frente a 0.1.283): 75 filas, 0 distintas.
  Incluye los transitorios con ω = 0,3, donde el presupuesto por paso pasa a 34.
- **Suite entera:** 5866 / 5866, con código de salida del proceso 0.

## 4. Lo que se abrió

**D285.** El rescate de D124 da por convergido el estado de Anderson sin mirar
la cara, y la comprobación final lo devuelve a «no convergido» sin probar la
continuación.
- **Reproducción** (`_auditoria/P6_0283/repro_d285.py`): el 004 de D274 en la
  malla graduada con la curva empinada y ω = 0,4.
- **Resultado:** rescate de Anderson en 87 pasadas, 1 nodo sin asentar y 4
  congelados.
- Va en P6, con prompt largo.

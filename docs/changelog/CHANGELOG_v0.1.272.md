# OGR Slip2D v0.1.272

**Qué mide la tolerancia del Picard no saturado (D267), dicho y fijado con un
test, sin cambiar el motor.** La ficha afirmaba que, con una relajación ω
pequeña, el bucle se daba por convergido lejos del punto fijo: 0,129 m con
ω = 0,1, unas 12 900 veces la tolerancia. **La medida lo refuta.** Ese
resultado sale con `converged = False` y el aviso de que la cara de rezume no
asentó. El 0,129 m no viene del criterio relajado, sino del presupuesto de
conmutaciones de la cara (ficha nueva D279). Ningún número cambia.

## 0. Lo que se encontró (puerta de medida A, `_auditoria/P6_0272/` del banco)

Caso: la presa rectangular de Gardner de `test_unsaturated_v127`, frente a su
punto fijo resuelto con tolerancia 1e-12.

- **El script del prompt no miraba `converged`.** Imprimía las pasadas y el
  error. La corrida con ω = 0,1 termina con un nodo congelado y otro sin
  asentar, y el solver la marca como no convergida.
- **El mecanismo es el presupuesto de conmutaciones.** Con ω = 0,1 la
  relajación es tan lenta que el conjunto de nodos activos de la cara cambia
  en cada pasada, de la 2 a la 29. El nodo del pie de la cara agota sus 25
  conmutaciones (`DEFAULT_MAX_NODE_SWITCHES`) y se congela retenido a P = 0,
  con agua ENTRANDO (reacción 73 veces q_tol).
  - **Con un presupuesto de 50 o más converge** a 1,3 tolerancias del punto
    fijo.
  - **El rescate de D124 no entra**, porque el bucle no «falla»: el conjunto
    congelado ya no cambia.
- **Mi hipótesis del plan también era falsa.** Pensaba que la causa era la
  banda de histéresis del caudal, con varios puntos fijos posibles. Encoger
  q_tol, p_tol o las dos a la décima parte no cambia nada: ω = 0,1 sigue a
  0,129 m.
- **El punto fijo es único.** Con ω = 0,4 y 0,5, y desde tres arranques
  distintos (saturado, perturbado ±0,5 m y hidrostático), coincide a 3e-13.
- **El criterio relajado cuesta poco.** En las corridas que convergen, el
  error frente al punto fijo queda en estas tolerancias, por debajo de la cota
  tol/ω:

  | ω | 0,8 | 0,4 | 0,3 | 0,2 | 0,1 (presupuesto ≥ 50) |
  |---|---|---|---|---|---|
  | Error, en tolerancias | 0,06 | 0,25 | 0,56 | 0,76 | 1,3 |

  Juzgar el cambio sin relajar (lo que proponía el prompt) apretaría el
  criterio 1/ω veces y movería los dígitos de todos los modelos que hoy
  convergen. No arreglaría el 0,129 m.

**Decisión de la propietaria:** cierre documental con test, y ficha nueva
**D279** para el presupuesto que se agota con una relajación lenta.

## 1. Qué cambia

- **El docstring de `solve_unsaturated`** gana una sección, «What the
  tolerance measures»: qué mide `tol`, la cota tol/ω, las cifras medidas, la
  unicidad del punto fijo, por qué no se cambió el criterio y qué hace una ω
  muy pequeña.
- **`picard_delta`** queda documentado como el último cambio relajado, que es
  lo que lee la parada.

## 2. Tests

`tests/test_picard_tolerance_v1272.py`, 5 casos. Fija lo medido, que ya era
así antes de esta versión: no discrimina contra 0.1.271 porque el cierre es
documental.

- Con ω = 0,4 (la de la puerta del permanente) y con ω = 0,2, las corridas
  convergidas quedan a menos de una tolerancia del punto fijo.
- El punto fijo no depende de ω (0,4 y 0,5 coinciden a 1e-10).
- ω = 0,1 con el presupuesto por defecto sale NO convergido, con nodos
  congelados y sin asentar y el aviso de la cara. No se hace pasar por
  convergido.
- ω = 0,1 con un presupuesto de 100 converge a menos de 2 tolerancias.

Suite entera: **5775 de 5775**.

## 3. Cierre en el banco

`d267()` en el `verificar_cierres.py` de la raíz exige:
- en vivo, que ω = 0,1 no salga convergido si queda a más de 10 tolerancias
  (la premisa del prompt);
- en vivo, que ω = 0,2 y 0,4 queden a menos de una tolerancia;
- el docstring;
- la medida archivada;
- el test.

Veredicto: **CIERRE DOCUMENTAL**.

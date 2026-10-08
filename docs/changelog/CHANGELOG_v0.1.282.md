# OGR Slip2D v0.1.282

**Un paso transitorio que converge arrastra lo que publica, y lo que mide la
tolerancia del transitorio queda escrito (D276).**
- **Hasta esta versión,** cada etapa publicaba la última solución lineal SIN
  relajar, mientras que el estado que pasaba al paso siguiente y al balance de
  agua almacenada era el iterado RELAJADO.
- **Lo que cambia:** las cargas publicadas son ya las del estado que usan el
  agua almacenada y el paso siguiente.

## 0. Lo que se encontró (puerta de medida, `_auditoria/P6_0282/medida_d276.py`)

**B, el estado publicado.** Donde el paso converge, max|publicado − arrastrado|
es exactamente la cota que sale del criterio, tol·(1 − ω)/ω:

| Caso | ω | Tolerancia | Diferencia | Tolerancias |
|---|---|---|---|---|
| 05-017, 018 y 019 | 0,3 | 1e-4 | 1,6–2,2e-4 m | 2,3 |
| 05-020 | 0,3 | 1e-6 | 1,7–2,1e-6 m | ≈ 2 |
| Desembalse del 102 (puerta) | 0,5 | — | 5,5e-6 m | — |

En la etapa que no converge del 102 (2 pasos de 5·10⁷ s, que ya no convergía)
la diferencia era de 4,66 m: lo publicado era una sola solución lineal.

**A, el criterio.** Juzgar el cambio sin relajar equivale a correr con
tolerancia·ω.
- **Cuánto mueve:**
  - el 05-017–019, de 2 a 10 mm, es decir, de 20 a 100 tolerancias;
  - el 05-020, de 1e-5 a 4e-5 m;
  - en pasadas, alrededor de un 20 % más.
- **Lectura:** el criterio relajado se para así de lejos de la respuesta más
  estricta. Nada en las cifras publicadas del banco es tan preciso, y el
  permanente juzga igual (D267).

**Decisiones de la propietaria:**
- B se arregla, con la variante «arrastrar lo publicado».
  - **Por qué esa variante:** la última solución lineal resuelve un sistema,
    y el iterado relajado no.
  - **La alternativa, publicar el relajado,** habría dejado reacciones
    residuales en los nodos libres y un balance de masa que no cierra.
- A se declara, con esta medida.

## 1. Qué cambia

- **`TransientSeepageSolver.step`** devuelve como estado, en un paso que
  converge, la última solución lineal: la que publica.
  - Interruptor `TRANSIENT_CARRY_LAST_SOLVE`, con alta en `INTERRUPTORES`
    como (0, 1, 282).
  - Un paso que no converge sigue arrastrando el iterado relajado, porque su
    solución sin relajar puede estar muy lejos, y lo dice.
- **Con ω = 1** relajado y sin relajar son lo mismo al bit. Por eso erfc,
  Terzaghi (05-015), capas (05-016), Ferris (05-021) y Celia no se mueven.
- **Docstring de `step`:** qué se arrastra, qué se publica y qué mide la
  tolerancia, con la medida (A declarada).

## 2. Tests

`tests/test_transient_carried_state_v1282.py`, 6 casos, en una columna 1-D con
curva de usuario y ω = 0,5:
- un paso que converge arrastra al bit lo que publica;
- con el interruptor apagado la diferencia es > 0 y < tol·(1 − ω)/ω, la
  identidad que sale del criterio (regla 1);
- el agua almacenada de la etapa es la de sus cargas publicadas;
- con ω = 1 nada cambia;
- un paso sin converger arrastra el relajado;
- el último cambio sin relajar de un paso que converge queda por debajo de
  tol/ω (A declarada).

## 3. Verificación

**El movimiento en el banco fue unas 20 veces mayor de lo que se estimó al
decidir.**
- **La estimación** fue «~2,3 tolerancias, ≤ 2e-4 m», que es la cota por paso.
- **Lo medido en el A/B árbol contra árbol** (`_auditoria/P6_0282/ab_arbol.py`,
  0.1.281 frente a 0.1.282): 75 filas, 5 distintas.

  | Fila | Movimiento |
  |---|---|
  | 05-017 | 4,3 mm |
  | 05-018 | 3,9 mm |
  | 05-019 | 3,8 mm |
  | 05-020 | 3,3e-5 m |
  | 02-102 transitorio | 2,5e-7 m |

- **Por qué es mayor:** arrastrar otro estado cambia la trayectoria del Picard,
  y cada paso se para en otro punto dentro de la precisión del criterio
  relajado, que es lo que midió A (20–100 tolerancias).
- **En la comparativa** (`ejecutar_filtracion.py --banco 05 15–21 --forzar`)
  se mueven hasta 8 mm (05-019, P_superficie a 792 min), y ninguna fila cambia
  de estado: el 17–20 no tiene cifra publicada.
- **El 015, el 016 y el 021 (ω = 1)** quedan iguales al bit.
- Se le preguntó a la propietaria con esta medida delante y confirmó la
  adopción.

- **Suite entera:** 5861 / 5861, con código de salida del proceso 0.

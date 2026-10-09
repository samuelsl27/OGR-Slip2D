# OGR Slip2D v0.1.284

**Las bandas de histéresis de la cara de rezume pasan a la décima parte
(D280).** Con las bandas de antes, la cara admitía varios estados convergidos,
y ω o el camino (bucle o rescate) elegían uno distinto. En 4 de las 53 filas
permanentes no saturadas del banco, el resultado cambiaba entre 1 y 24 mm según
la ω. Con las bandas nuevas, tres de esas filas dan una sola cara para toda ω.

## 0. Lo que se encontró

- **El mecanismo** (medido en D266, `_auditoria/P6_0273/`).
  - Un nodo libre de la cara se retiene a P = 0 solo si su presión pasa de
    p_tol = 0,02·h.
  - Un nodo retenido se libera solo si el agua que entra pasa de
    q_tol = 1e-3 × el mayor caudal nodal de la primera solución.
  - Con esas bandas cabía más de un conjunto de cara: la diferencia estaba
    siempre en un nodo de la cara y por debajo de p_tol.
- **El caso más limpio, el 05-001** (lluvia entre dos ríos, Harr 1990, en la
  malla del manual).
  - Con ω = 0,2, el nodo de la orilla derecha justo encima del río queda en la
    cara.
  - Con ω ≥ 0,4 queda libre, con una presión positiva por debajo de 0,02·h, y
    las cargas difieren 1 cm.
- **La puerta de medida** (`_auditoria/P6_0284/medida_d280.py`, sin tocar el
  motor). Las 4 filas de D266 con ω = 0,2, 0,4, 0,6 y 0,8, con las bandas tal
  cual y a la décima parte:

  | Fila | Conjuntos de cara entre las ω (bandas ×1 → ×0,1) | max\|ΔH\| frente a ω = 0,4 con ×0,1 |
  |---|---|---|
  | 05-001 x1 | 2 → **1** | 6e-8 m |
  | 02-038 h61 Gardner seco | 3 → 2 | 2,1 mm |
  | 02-038 h62 Gardner seco | 3 → **1** | 2,5e-5 m |
  | 02-038 h63 Gardner seco | 4 → **1** | 3,4e-5 m |

  Todas convergen con todas. Los rescates de Anderson con ω = 0,6 y 0,8 en el
  02-038 siguen ahí.
- **El ancla externa de la cara no se mueve.** El caudal de Charnyi por la presa
  rectangular de `test_unsaturated_v127` da un error del 1,772 % antes y
  después, con el mismo nodo de cara y las mismas 30 pasadas. El punto de salida
  es el mismo porque la cara es la misma.
- **Lo que no se probó.** La ficha proponía una pasada de pulido tras converger.
  El motor no admite arrancar de un estado dado, así que el prototipo resolvió
  desde el principio con las bandas encogidas, que es lo que esa pasada pediría
  al final. Así ha quedado: no hay pasada aparte.
- **Decisión de la propietaria:** adoptar ×0,1 en las dos bandas, en el
  permanente y en el transitorio.

## 1. Qué cambia

- **`UnsaturatedSeepageSolver._face_p_tol()` y `_face_q_tol(q_scale)`.** Son las
  dos bandas, usadas en el permanente y en cada paso transitorio (una regla
  desde D269).
  - p_tol = 0,002·h, o el `switch_pressure_tol` dado.
  - q_tol = 1e-4 × el mayor caudal nodal de la primera solución, o 1e-14 si es
    nulo.
- **Interruptor `FACE_BANDS_TIGHT`,** con alta en `INTERRUPTORES` como
  (0, 1, 284). Apagado, vuelven 0,02·h y 1e-3.
- **Los docstrings** de `solve_unsaturated` y de `solve_project_groundwater`
  dicen ya lo que queda: en el 02-038 h61 seco, dos conjuntos a 2,1 mm.

## 2. Tests

`tests/test_face_bands_v1284.py`, 8 casos, sobre el bloque de Harr (1990) del
05-001 en su malla de 230 elementos:
- las bandas valen la décima parte, y un `switch_pressure_tol` explícito se
  respeta;
- apagado, son las viejas;
- con ω = 0,2, 0,4 y 0,8 sale la misma cara y las cargas quedan a menos de dos
  tolerancias. El punto fijo no depende de la relajación que lo alcanza, así que
  la referencia es esa identidad;
- apagado, la cara vuelve a depender de ω, con más de 5 mm de diferencia;
- con las bandas viejas y ω = 0,4 queda libre el nodo que las nuevas retienen,
  con una presión entre 0,002·h y 0,02·h;
- el paso transitorio usa las mismas bandas (encendido y apagado).

## 3. Verificación

- **A/B en el mismo proceso** (`_auditoria/P6_0284/ab_d280.py`). Las 53 filas
  de D266 con la ω de la puerta (0,4), los transitorios 05-017 a 020 y el
  desembalse del 102: **58 filas, 14 distintas.** Ninguna cambia de
  convergencia ni de rescate. Las pasadas cambian como mucho en una, salvo el
  05-020 (de 703 a 699).
  - **Con otra cara:**
    - 05-001 x1: 1,0 cm;
    - 02-038 seco h61, h62 y h63: 2,1, 0,33 y 1,9 mm;
    - 05-018 transitorio: 1,9 cm;
    - 05-020 transitorio: 0,26 mm.
  - **Con la misma cara,** 8 filas del 05 se mueven ≤ 4,5e-8 m (de 1e-6 a 1e-5
    de tolerancia).
- **A/B árbol contra árbol** (0.1.283 frente a 0.1.284,
  `_auditoria/P6_0284/ab_arbol.py`, todas las diferencias en
  `diferencias_0283_0284.txt`): **75 filas, 19 distintas.**
  - **Con otra cara:**
    - 05-001 x1: 1,0 cm;
    - 05-018: 1,1 y 1,9 cm, en sus dos resultados;
    - 02-038 seco: 2,1, 0,33 y 1,9 mm;
    - 05-020: 1,3e-5 y 2,6e-4 m.
  - **El 05-007 (x1 y x4)** da las mismas cargas al bit con dos pasadas más.
  - **El resto** se mueve ≤ 1e-6 m, con como mucho una pasada más: el 05-006,
    009, 010 y 011, y el permanente del 102.
  - **El 02-102 transitorio a 700 elementos:** su primera etapa se mueve
    1,8e-7 m. La segunda (5·10⁷ s por paso) ya terminaba sin converger en
    0.1.283, con 60 pasadas, y sigue igual. Sus cargas difieren hasta 10,4 m,
    pero son un iterado no convergido en los dos lados y no miden nada
    (`converged = False` se publica en los dos).
- **En el banco** (`ejecutar_filtracion.py --banco 05 1 6 7 9 10 11 18 20
  --forzar`, 16 corridas, 0 fallos; comparativa regenerada):
  - **05-001, malla del manual:** x_a pasa de 4,2269 a 4,1022 m y se acerca a
    la solución cerrada (de +6,00 % a +2,88 %), a la referencia (de +4,11 % a
    +1,04 %) y a la malla fina (4,0274, que no se mueve). La fila pasa de
    DISCREPANCIA a REVISAR.
    - h_max pasa de 4,5433 a 4,5413 m y sigue en DISCREPANCIA (+6,93 %).
    - x_a es la abscisa del máximo de una curva casi plana: por eso 1 cm de
      carga lo mueve 12 cm.
  - **El 018** se mueve hasta 3,2 mm y **el 020** 0,1 mm, en cifras sin valor
    publicado.
  - **El 02-038 publicado** usa la curva «gardner», que sale igual al bit: no
    se re-corre.
- **`verificar_cierres.py` de la raíz:** 28 comprobaciones, 25 cierran y 0
  bajadas. `d280()` da CUBIERTO POR TEST.
- **Suite entera:** 5874 / 5874, con código de salida del proceso 0.

## 4. Lo que sigue abierto

- **D285** (el rescate de D124 da por convergido el estado de Anderson sin
  mirar la cara) no cambia. Sigue en P6.
- **El 02-038 h61 con Gardner seco** conserva dos conjuntos a 2,1 mm entre las
  ω. Es la precisión del algoritmo (un nodo y p_tol), declarada en el docstring.

## 5. Lo que no se ha probado

- La serie de factores del 02-102, re-corrida con su script del banco. Sus
  etapas convergidas se mueven ≤ 1e-6 m, igual que en 0.1.281 y 0.1.282.
- La interfaz no cambia: no hay prueba manual pendiente por esta versión.

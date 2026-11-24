# OGR Slip2D v0.1.487

**D457: el factor de Sarma con dovelas no verticales vuelve a ser la raíz mayor de Kc(F) = kh cuando hay
raíces juntas.** El solver buscaba el primer cambio de signo de H bajando desde F = ∞ con un barrido de
razón 1,05. Dos raíces dentro de un mismo paso no cambian el signo, así que el barrido seguía bajando y
daba una raíz menor que la de la regla del método. Ahora las raíces se separan sobre un polinomio exacto,
y no dependen de ningún paso.

| caso | 0.1.486 | 0.1.487 = raíz mayor |
|---|---|---|
| círculo de D452, 75 cuñas | 0,763189 | **0,817510** |
| círculo de D452, 100 cuñas | 0,596451 | **0,819129** |
| problema 5, γw 9,81, bisectriz, sin la tabla, 2 / 10 / 25 cuñas | 0,595702 | **0,609567** |

El círculo de D452 es el de (30; 35) R 26, con caras verticales, φ 30°, c 1 y Ru 0,7.

**Sube factores**, del lado de la regla del método. En ese círculo Spencer da 0,4827: la raíz mayor se
aleja de los métodos de dovelas verticales. Qué raíz es la física es D452, que sigue sin fuente (§4).

## 0. Lo que se encontró

### Por qué ninguna razón fija basta

`_auditoria/P9_D457/medir_barridos_d457.py` (banco) mide 27 casos contra la raíz mayor de un barrido de
razón 1,0005 con Brent. Los 27 son el círculo con 25–200 cuñas, el 5 sin tabla y los publicados del 03
con los dos sentidos.

- **En el círculo, las raíces forman un peine.** Cada raíz queda justo encima de un cero de un q de la
  recurrencia, con un cero de D (un polo de Kc) justo debajo. El paso entre raíces es 1 + 1,3/n: 1,0177
  con 75 cuñas, 1,0132 con 100, 1,0088 con 150 y 1,0066 con 200.
- **Con 60 cuñas, la de 1,05 acertó por suerte.** Solo falla cuando el paso que contiene la raíz mayor
  contiene un número par de raíces.
- **Razón 1,02:** acierta con 75 y 100 cuñas y falla con 150 y 200. Razón 1,005: acierta en los 27
  casos, pero el argumento del peine dice que falla desde unas 260 cuñas.
- **Muestrear más donde |H| tiene un mínimo local sin cambiar de signo** no ve una caída estrecha sobre
  una tendencia monótona. Falla igual que la de hoy.
- **Añadir los ceros de q como nodos del barrido** (forma cerrada, cuesta +2–10 %) arregla todos los
  círculos, pero no el 5. Allí las dos raíces (0,60957 y 0,60192) quedan entre dos ceros de q, separadas
  por un cero de D. Es otro mecanismo.

### Lo que sí lo resuelve: H es un polinomio en 1/F

**H·∏√(1 + tan²φᵢ g²) es un polinomio en g = 1/F de grado ≤ 2(n − pares).** El producto lleva un factor
por cuña y deja fuera uno de cada par cancelado.

- Cada término de la recurrencia lleva exactamente un factor de cada cuña: Aᵢ o Pᵢ de la suya, qₖ de las
  anteriores y Ẽⱼ de las posteriores.
- Multiplicados por la raíz de su cuña, q, Ẽ y A son cuadráticos en g y P es lineal, porque
  cos(atan(tan φ g)) = 1/√(1 + tan²φ g²).
- Las dos cuñas de un par cancelado tienen el mismo tan φ. Por eso el factor que falta es el mismo sea
  cual sea la que lo pierde.
- Comprobado: interpolado con unos puntos de Chebyshev de más, los coeficientes por encima de ese grado
  son redondeo (≤ 1e-14 relativo). Es `TestThePolynomial` del test nuevo.

### El enumerador (`solver._nodes`)

1. Por encima de F = 100, los mismos pasos gruesos de antes.
2. Por debajo, el polinomio se interpola de forma exacta en tramos de g de razón 2, en sus puntos de
   Chebyshev-Lobatto (Trefethen 2013, cap. 2).
3. Un tramo cuyos coeficientes cumplen |c₀| > Σ|cₖ| no tiene raíz. Uno cuya derivada lo cumple es
   monótono y tiene a lo sumo una raíz. En los dos basta con su extremo.
4. En los demás, los autovalores reales de la matriz colega dan dónde están las raíces (Good 1961;
   Trefethen 2013, cap. 18). H se muestrea a los dos lados de cada una y entre cada dos.
5. **El signo se lee siempre de H, nunca del interpolante.** Una estimación algo desviada añade una
   muestra, no una raíz.
6. Donde H se desborda (muchas cuñas a F pequeño), el tramo se barre con razón 1,005. Es la decisión de
   la propietaria.

Lo usan `solve` (a través de `_bracket`) y la raíz siguiente de la nota de D452 (`_lower_root` y
`near_pair`). Con eso, la nota da la raíz siguiente de verdad: en el círculo de 40 cuñas, **0,7857**. Hasta
ahora daba 0,7372 y se saltaba 0,7857 y 0,7609.

`solver.ROOT_ENUMERATOR = "sweep"` devuelve el barrido de 0.1.486. Queda para el A/B y para el test de la
regla 7.

### Abaratarlo: lo que se midió

La propietaria pidió abaratarlo y evaluar el impacto. Se probó partir en dos los tramos que no son ni sin
raíz ni monótonos, con H evaluado de nuevo en cada mitad, antes de los autovalores. Con 25 cuñas:

| mitades | 25 cuñas | 100 cuñas |
|---|---|---|
| 0 | 2,5 ms | 56 ms |
| 1 | 3,1 ms | 55 ms |
| 3 | 5,0 ms | 190 ms |

Sale más caro que ir directo a los autovalores, así que se quitó. Lo que sí abarató: H de todos los tramos
en una sola llamada vectorizada, y el signo de los extremos leído de esa misma evaluación (antes eran 14
llamadas por superficie).

**Coste de `solve` por superficie** (tolerancia 1e-12, 20 repeticiones):

| caso | 0.1.486 | 0.1.487 |
|---|---|---|
| 4 saturado, 25 cuñas | 1,26 ms | 1,02 ms |
| 5 con la tabla | 0,65 ms | 0,84 ms |
| círculo, 25 cuñas | 1,57 ms | 2,49 ms |
| círculo, 100 cuñas | 5,8 ms | 56 ms |

El coste de los autovalores crece como n³. Con 100 cuñas es diez veces más lento.

### El impacto en el banco del 03

`_auditoria/P9_D457/ab_busquedas_d457.py` es un A/B en memoria, en serie: las 13 búsquedas de Sarma del 03
con el interruptor en los dos sentidos.

- **Ninguna raíz cambia** en las 49 739 superficies.
- **35 700 cambian ≤ 0,004 %.** Es ruido de la tolerancia de Brent (1e-4 por defecto): el corchete
  empieza en otro nodo.
- **Las críticas se mueven ≤ 9e-6:** 1,152554 → 1,152563 en el 002, 1,119137 → 1,119133 en el 002
  circular, 1,083117 → 1,083120 en el 003 circular. Las demás, iguales.
- **El tiempo de las búsquedas sube 0–15 %.**
- Por eso no se ha re-corrido el banco: sus cifras de 4 decimales no cambian.

### La guarda del optimizador sobraba

**Se ha quitado la guarda de D457** (decisión de la propietaria, regla 7). Era `larger_root_above` (un
barrido de 1,002 sobre cada factor que aceptaba el optimizador de 0.1.471), y con ella se van su contador
`sarma_sweep_misses` y el caso «sin arranque».

- Con `solve` sin pares escondidos, la guarda ya no podía rechazar nada.
- Se van también las notas `method.sarma_sweep_miss` y `method.sarma_angles_no_start` y sus traducciones,
  el campo de `ogr_api`, `SarmaNonVertical.larger_root_above`, `solver.larger_root_above` y
  `FINE_SWEEP_RATIO`.
- Un `.ogr` con resultados guardados que traen esos campos se abre igual: los campos se ignoran.

### El pliegue del 4 saturado optimizado: de 0,2037 a 0,19955

**El 0,2037 de 0.1.471 era el sitio donde el barrido de 1,05 perdía el par de raíces**, antes de que se
juntaran. Esa condición es suave, y 0,001° la resolvía.

Con raíces exactas el borde es un pliegue de verdad, donde F(θ) va como la raíz cuadrada de la distancia
al borde. Partido a 0,001°, daba 0,20001 con 10 cuñas y 0,20004 con 2: el test pedía 1e-4 y salían 1,95e-4.
Con un paso más fino el borde seguía bajando:

| paso | 10 cuñas | 2 cuñas |
|---|---|---|
| 1e-4° | 0,19969 | 0,19971 |
| 1e-5° | 0,19956 | 0,19959 |
| 1e-7° | 0,199553 | 0,199553 (a 2e-6) |

La propietaria eligió afinar el borde ya.

- **`FOLD_STEP` = 1e-7°** es la precisión del borde del pliegue, separada de `JUMP_STEP` (0,001°), que
  sigue decidiendo un salto de rama.
- El pliegue del 4 saturado queda en **0,19955**, con 2 cuñas, con 10 y con el último paso ocho veces
  más fino.
- La nota del pliegue dice el paso nuevo.
- El círculo con Ru 0,7 y 8 cuñas, optimizado, termina ahora en un pliegue (0,51808, dos caras en el
  borde): sus dos raíces quedan dentro de la tolerancia del factor. El test de la raíz mayor se ha
  adaptado a eso: busca el cambio de signo dentro de ±1e-5 con muestreo logarítmico, y no a ±1e-5 en
  bruto.

### Una anomalía que queda (regla 6)

Con 200 cuñas, `_polynomial` en aritmética de arrays se desborda al bajar hacia F ≈ 0,2 (`overflow` e
`invalid value`): los productos de q crecen sin límite. Un `nan` en H se lee como «sin cambio de signo». El
enumerador evita esos tramos (los barre con razón 1,005 donde el polinomio no es finito). Pero el desborde
de H en sí existía ya en 0.1.486, y no está medido si movió algún factor. Queda por abrir ficha.

## 1. Qué cambia

- **`ogr_slip2d/sarma/solver.py`**:
  - `ROOT_ENUMERATOR`, `_root_weights`, `_cheb`, `_no_root`, `_pieces`, `_nodes` y `_first_change`;
  - `_bracket` y `_lower_root` pasan por `_first_change`;
  - `near_pair` empieza justo debajo del factor, no en el siguiente nodo de 1,05;
  - el docstring del módulo («THE ROOT») y las referencias (Good 1961, Trefethen 2013);
  - fuera `larger_root_above` y `FINE_SWEEP_RATIO`.
- **`ogr_slip2d/sarma/optimize_angles.py`**: sin guarda (el argumento `larger_root`, `sweep_misses` y
  `no_start`); `FOLD_STEP` y el docstring del pliegue.
- **`ogr_slip2d/search.py`**: sin `_no_start`; `_all_angles_optimised` devuelve solo el resultado.
- **`ogr_slip2d/analysis_runner.py`**, **`ogr_slip2d/method_note_messages.py`**, **`ogr_gui/i18n`**,
  **`ogr_api/results.py`** y **`ogr_slip2d/methods/sarma.py`**: lo de la guarda, fuera; la nota del
  pliegue con `FOLD_STEP`.
- **Versión** en los siete sitios.

## 2. Tests

- **Nuevo, `tests/test_sarma_sweep_v1487.py`.** Lo juzga `_kc_direct` de `test_sarma_solver_v1461` (el
  equilibrio como sistema lineal, regla 1):
  - el factor es la raíz mayor en el círculo de 75 y 100 cuñas y en el 5 sin tabla;
  - 40, 50 y 60 cuñas no se mueven;
  - con `ROOT_ENUMERATOR = "sweep"` el juez encuentra una raíz por encima del factor (regla 7);
  - la nota de D452 da 0,7857 en el círculo de 40 cuñas;
  - la identidad del polinomio.
- **`tests/test_sarma_optimize_angles_v1471.py`**:
  - fuera los cinco tests de la guarda: tres con una guarda inyectada, el del arranque del 5 y el de la
    nota en español;
  - el del círculo sigue, sin el contador: el factor guardado es la raíz mayor según el juez y está en
    un pliegue;
  - el del pliegue, sin cambiar su tolerancia: ahora pasa con `FOLD_STEP`;
  - docstrings con los valores nuevos.
- **`tests/test_method_notes_v1348.py`**: fuera las dos notas que ya no existen.

## 3. El banco

- **`_auditoria/P9_D457/`**: `medir_barridos_d457.py` y su log (las candidatas (a)–(e) y su coste), y
  `ab_busquedas_d457.py` y su log (el A/B de las 13 búsquedas).
- **`d457()`** en el `verificar_cierres.py` de la raíz, en vivo:
  - los cinco casos de la ficha a 1e-6 de la raíz mayor de un barrido de 1,0005;
  - 40, 50 y 60 cuñas y los dos publicados del 4 sin moverse;
  - y el test con sus cuatro clases.
  - Con el motor de 0.1.487 sale **CUBIERTO POR TEST**, y con `ROOT_ENUMERATOR = "sweep"`, **SIGUE
    ABIERTO**.

## 4. La fuente de D452

**Sarma (1979) sigue sin estar.** Se buscó en la web el 2026-11-24: solo está tras el pago de ASCE
(doi 10.1061/AJGEB6.0000903).

- Ni la tesis de Albataineh (2006, Akron) ni Mukherjee et al. (IGC), que sí se leyeron, dicen qué raíz
  se elige.
- Unas diapositivas del propio Sarma, posteriores a 2008, dan su «criterio de aceptabilidad» (diap. 28):
  normales y empujes de compresión, cortante cinemáticamente admisible y factor ≥ 1 en todo plano
  interior. Se guardan en `referencias/Documentacion_Guia/` como fuente secundaria, con su fila en
  `INDICE.md`.

## 5. Qué se probó y qué falta

- Probado:
  - `python tests/_runner.py sarma method_notes i18n spanish results --jobs 4` en verde;
  - `d457()` en los dos sentidos;
  - el A/B en memoria del 03.
- Falta:
  - la suite entera con `--jobs 4`, al final de la tanda;
  - `verificar_cierres.py` de la raíz con `d122`, `d123`, `d357`, `d451` y `d459`;
  - `auditoria_invariantes.py`;
  - abrir la ficha del desborde de H con muchas cuñas.

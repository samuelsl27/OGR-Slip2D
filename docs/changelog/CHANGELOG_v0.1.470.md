# OGR Slip2D v0.1.470

**D452: el factor de Sarma junto a un par casi cancelado, dicho y no cambiado.** El factor del método de Sarma sigue
siendo la raíz mayor de Kc(F) = kh, como desde 0.1.461. Ningún factor cambia, de ningún método.

Lo nuevo es una nota. La raíz mayor puede estar ya junto a un polo de la recurrencia (menor |q| por debajo de 0,2,
la nota de 0.1.466) y quedar además a menos del 1,2 % de un cero de D, el denominador de Kc. Esa es la huella de una
raíz y un polo que casi se cancelan. En ese caso, la nota `method.sarma_near_pair` dice la distancia y da la raíz
siguiente hacia abajo, la que tiene la superficie sin doblar, y los details y el API la llevan.

**D452 sigue abierta,** a la espera de Sarma (1979).

Decisiones de la propietaria (2026-11-17):
- **Primero la medida, sin tocar el programa.** Mientras, ella intenta conseguir Sarma (1979).
- **El PDF mal nombrado se anota** en `referencias/Documentacion_Guia/INDICE.md`, sin renombrarlo.
- **La regla R5** (saltar una raíz a menos del 1,2 % de un cero de D): la eligió con las medidas, y la refutó la
  revisión adversaria.
- **La raíz mayor y una nota informativa,** después de la refutación.
- **Dos fichas nuevas:** el barrido que pierde la raíz mayor con muchas cuñas, y F(kh) casi plano en la rama
  publicada.

## 0. Lo que se encontró

### Al planificar

- **El PDF «…_Sarma_1979.pdf» de `Documentacion_Guia` es Sarma (1973),** *Géotechnique* 23(3), el de dovelas
  verticales. Está desde el 2026-11-04 y nadie lo había abierto; la ficha decía que no estaba.
  - El de 1973 exige una solución «físicamente aceptable»: que no viole el criterio de rotura y que no implique
    tracción en la masa (págs. 425 y 427, con Whitman y Bailey 1967).
  - No dice cómo elegir entre varias raíces.
  - El de 1979, el de dovelas no verticales, sigue sin estar.
- **La documentación de la referencia** solo dice que se reduce la resistencia hasta que Kc llega a cero.

### La medida (fase A, solo el banco)

`_auditoria/P9_D452/medir_reglas_d452.py` busca todas las raíces de H en [0,01; 100] con un barrido fino (razón
1,002) y Brent. Para cada raíz mide:
- el menor |q|;
- el cociente de fuerzas;
- la tracción en caras y bases;
- la distancia al cero de Q (polo de la recurrencia) y al cero de D (polo de Kc) más cercanos.

Se aplicaron seis reglas a los publicados, al 4 doblado (de 0 a 12 m), al círculo de D452, al pie y la base
escalonada del test del solver, y a un censo de 42 753 superficies de 8 búsquedas del 03:
- **Corrección a la ficha.** El polo 0,4288 que citaba el solver junto al publicado saturado es un cero de D, no de
  Q. La regla de ejemplo de la ficha («si un polo separa la mayor de la siguiente, la siguiente») la refuta el 4 seco:
  daría 0,362 en vez de 1,198.
- **R1 (menor |q| ≥ 0,2)** rechaza la raíz verdadera del pie recto (|q| 0,185) y de la base escalonada.
- **R2 y R2b (sin tracción)** dejan sin factor al 4 saturado con 25 cuñas y al 5: sus raíces publicadas tienen caras
  en tracción.
- **R4 (polo de Q a más del 1 %)** salta en el 4 doblado a partir de 1 m.
- **R5 (cero de D a más del 1,2 %)** era la única que dejaba los publicados, el pie y la escalonada.
  - Seguía el 4 doblado sin salto (0,4346 → 0,4114).
  - En el censo movía 28 superficies y ninguna crítica.
  - Su 1,2 % estaba ajustado entre el 1,05 % de un caso espurio y el 1,4 % del publicado saturado.

  La eligió la propietaria.
- **El censo comparó la raíz mayor del barrido fino con la del motor:** 441 superficies diferían, y ninguna por un
  fallo del motor. 402 tienen la raíz del motor por encima de 100, donde el barrido fino no llega; las otras 39 dan
  un motor mayor que 100.

### La revisión adversaria (un agente): R5 refutada

- **ALTO — R5 se salta la rama publicada del 4 saturado con cambios pequeños de los datos.** Esa rama queda un 1,4 %
  por encima de un cero VERDADERO de D, y estos cambios lo meten dentro de la ventana; comprobado aparte:

  | Cambio | Sin la regla | Con R5 |
  |---|---|---|
  | kh 0,03 | 0,4339 | 0,1280 |
  | kh 0,05 | 0,4334 | 0,1172 |
  | γw = 10 | 0,4326 | 0,1397 |
  | φ 5° en el suelo | 0,4224 | 0,1376 |
  | γc 1,25 | 0,4280 | 0,1258 |

  Una corrida Ky con objetivo 0,3 aterrizaba en el salto. La distancia al cero de D no separa los dos grupos: las
  espurias quedan del 0,0005 % al 1,04 %, y la rama publicada variada del 0,001 % al 1,08 %. La distancia al cero de Q
  casi los separa (del 0,02 % al 5,2 % frente al 33–36 %), pero entonces el salto del 4 doblado vuelve hacia 3–5 m.
  **Por decisión de la propietaria se quitó la regla,** y queda la información.
- **MEDIO — lo implementado no era lo medido.**
  - El barrido de razón 1,05 no separa raíces muy juntas (el círculo con 45 y 50 cuñas).
  - El coste por solución subía de un 38 a un 44 %.

  Las dos cosas quedan fuera con la nota: `near_pair` solo se pide junto a un polo, y el docstring dice que una raíz
  que el paso del barrido esconde no se encuentra.
- **BAJOS que siguen valiendo, arreglados:**
  - con D ≡ 0 (ninguna base con peso de suelo) cada muestra era un cero; ahora no hay nota;
  - los tests no tenían kh > 0: el test nuevo tiene el 4 doblado con kh 0,05, y la raíz siguiente se juzga como raíz
    de Kc = kh.
- **Dos anomalías anteriores, a fichas nuevas:**
  - el barrido de razón 1,05 pierde la raíz mayor en HEAD: el círculo de D452 con 60, 75 y 100 cuñas da 0,8388,
    0,9282 y 0,9707 frente a 0,9989, 0,9998 y 1,0006;
  - en la rama publicada del 4 saturado F(kh) es casi plano (de 0,4347 a 0,4310 con kh 0,3), mientras Spencer va de
    0,21 a 0,11.
- **Sin hallazgos:** 70 casos idénticos a HEAD con R5 (los publicados, 48 círculos y el solver directo); el espejo y
  el sentido cinemático; la grieta llena; varios dobleces.

### Lo que no hubo

No hubo una segunda revisión adversaria de la nota. Su código reutiliza las dos funciones que la revisión ya leyó
(`_near_kc_pole` y `_lower_root`). La nota no mueve ningún número. Las pruebas son el juez independiente del test y
los mutantes.

## 1. El cambio

- **`ogr_slip2d/sarma/solver.py`:**
  - `near_pair(bases, faces, F, …)`: la distancia de F al cero de D más cercano, si está a menos de `NEAR_KC_POLE`
    (1,2 %), y la raíz siguiente hacia abajo;
  - `_near_kc_pole` y `_lower_root`;
  - el docstring del módulo cuenta lo medido y lo refutado.
- **`ogr_slip2d/methods/sarma.py`:** `_near_pair` solo se pide cuando el menor |q| baja de 0,2. Así ninguna otra
  superficie paga el coste. Llena `details["sarma_kc_pole_distance"]` y `["sarma_next_root"]`.
- **`ogr_slip2d/analysis_runner.py`:** la nota `method.sarma_near_pair`, junto a `method.sarma_near_pole`.
- **`ogr_slip2d/method_note_messages.py`**, con su español.
- **`ogr_api/results.py`:** los dos campos nuevos en `details` de `results_get`.
- **La spec 009:** la tarea de 0.1.470.

## 2. El test

`tests/test_sarma_near_pair_v1470.py`, 10 casos. El juez independiente es `_kc_direct` del test del solver: el
equilibrio de las cuñas como un solo sistema lineal, sin recurrencia ni polinomio. Comprueba:
- **el factor es la raíz mayor, como era:**
  - el 4 saturado publicado con 2 y 25 cuñas, a 1e-6 de la herramienta del banco;
  - las cuatro variantes de la revisión (kh 0,03 y 0,05, γw = 10, φ 5°) en la rama publicada, a ±3 % de 0,4347, y sin
    nota;
  - el 4 doblado 1 cm y 2 m con su raíz mayor, sin otra por encima;
- **el par, por el juez** (en el 4 doblado 1 cm y 2 m, con kh 0 y 0,05, en el pie doblado 0,06° y en el círculo de
  D452 con raíces a un 5 %):
  - el factor tiene un polo de Kc a menos del 1,2 %;
  - la raíz siguiente es raíz de Kc = kh, y no hay otra entre ella y el factor;
  - con poco doblez, continúa la de la superficie recta, a menos del 1 %;
- **sin par no hay nota ni coste:** `near_pair` no se pide con un menor |q| de 0,2 o más;
- **la regla 7:** con `NEAR_KC_POLE` = 0 la nota se va y el factor se queda;
- **la nota** en inglés y en español, los details y el API;
- **`_lower_root`** encuentra una raíz justo debajo del punto de partida.

Mutantes: `_auditoria/P9_D357/mutants_v1470.py` del banco, con su log: 11, ninguno vivo. Uno vivía (empezar la
búsqueda un 10 % más abajo); lo mata el círculo con raíces a un 5 %.

## 3. La suite

- `test_method_notes_v1348`: una muestra de la nota nueva.

## 4. Verificación

- **La suite entera, `--jobs 4`, tras la revisión:** 8014 casos; pasan 8013 y uno queda saltado, sin fugas ni tramos
  muertos. La última serie en verde es de hace 48 commits.
- **El test nuevo:** 10 de 10. **Mutantes:** 11, ninguno vivo.
- **Los README:** 8003 → 8013 tests.

## 5. Lo que queda

- **D452 sigue abierta,** con sus medidas, la regla refutada y la nota, a la espera de Sarma (1979).
- **0.1.471 (los ángulos optimizados) minimiza la raíz mayor.** Una raíz espuria junto a un par es mayor que la que
  continúa, así que un minimizador se aparta de ella. Pero el factor de una geometría concreta casi doblada puede
  quedar del lado inseguro, y la nota lo dice.
- **El banco, tras el commit:**
  - las fichas del barrido y de F(kh) plano;
  - la ficha D452 con las medidas;
  - el progreso de D357.

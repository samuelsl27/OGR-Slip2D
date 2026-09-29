# OGR Slip2D v0.1.223

**D222 — Corps #2 y Lowe-Karafiath inclinan la fuerza de cada contacto con
el promedio de las inclinaciones de sus dos dovelas.** Hasta 0.1.222 cada
contacto tomaba la de la dovela de su IZQUIERDA en el orden de índices, que
siempre va de izquierda a derecha en x. Por eso el mismo talud reflejado daba
otro factor: −0,88 % en Corps #2 y −0,10 % en Lowe-Karafiath, con 50 dovelas.

La propietaria pidió evaluarlo «de forma exhaustiva, con rigor científico y
matemático». La evaluación tiene cinco partes (secciones 0 a 3):

1. fuentes;
2. análisis de la discretización;
3. un estudio numérico de simetría, orden y consistencia;
4. anclas externas: el 027, publicado por la referencia y por XSTABL, y el 055
   y el 056, publicados por UTEXAS4;
5. el censo del banco.

Este cambio **mueve factores**: los de Corps #2 y Lowe-Karafiath. En el banco
se mueven las filas de Lowe-Karafiath (sección 4); Corps #2 no lo corre ningún
modelo. Corps #1 no se mueve ni un bit.

Hay un hallazgo nuevo, que se reporta y NO se corrige (regla 6):

- **D223**: Corps #1 con grieta de tracción traza su cuerda hasta el fondo de
  la grieta, y la referencia y XSTABL la trazan hasta el terreno (sección 5).

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. Las fuentes

- **USACE (2003), EM 1110-2-1902, §C-4a (p. C-21)**. Lowe y Karafiath (1960)
  suponen las fuerzas entre dovelas inclinadas «at an angle that is the
  average of the inclinations of the slope (ground surface) and shear surface
  **at each vertical interslice boundary**».
- **Duncan, Wright y Brandon (2014)**:
  - la Tabla 6.1 dice de Lowe-Karafiath que la inclinación «varies from slice
    to slice, depending on where the slice boundaries are located»;
  - la Fig. 6.14c dibuja la variante de los Corps que sigue la pendiente del
    terreno: «interslice force here is parallel to average slope here».
  - Esa figura es la que la documentación de la referencia usa para su Corps
    #2.
- **El libro de SLOPE/W (2022, Tabla 2-2)** lo enuncia por dovela («ground
  surface at top of slice», «average of ground surface and slice base
  inclination»). No dice cómo lo lleva al contacto.
- **El procedimiento gráfico del propio EM** (§C-4b, pasos 4 y 5) traza una
  sola fuerza por contacto: la del lado aguas abajo de una dovela es la del
  lado aguas arriba de la siguiente.

Conclusión: la inclinación pertenece a la sección vertical sobre la que actúa
la fuerza, es decir, al contacto. Tomar la dovela de un lado la evalúa media
dovela más allá.

## 1. El análisis

Llamemos θ(x) a la inclinación que prescribe el método en la sección x. Es
continua a trozos: salta donde el terreno tiene un vértice.

**Qué tomaba cada contacto x_k hasta ahora.** La recursión le daba el valor de
la dovela k−1, es decir, θ evaluada en x_k − b/2 (b, el ancho de la dovela).

**Primer orden.** Ese desplazamiento es de primer orden en b, y el error del
factor también lo es: O(1/n).

**Signo fijo, y por eso asimetría.** El error tiene el signo del lado elegido.
Tomar la dovela de la derecha comete el error opuesto. El modelo reflejado
toma la otra, así que la diferencia entre un talud y su reflejo es también de
primer orden.

**El promedio de las dos dovelas.** Da θ(x_k) + O(b²) y es simétrico por
construcción. Una θ negada, que es lo que hace la marcha reflejada, da la θ
negada exacta.

**Cuando θ salta dentro de la masa.** Es la coronación de un talud en Corps #2,
de 59,7° a 0°. Ningún esquema es de segundo orden allí, porque la fuerza tiene
que girar en una dovela. Pero el promedio no tiene sesgo de dirección.

**Por qué el promedio y no la geometría exacta en el contacto** (la tangente
del círculo y la pendiente del terreno en esa x):

- las dovelas son la geometría que el método resuelve: sus cuerdas llevan sus
  ángulos de base y sus techos, sus pesos;
- en ese polígono, la inclinación EN un contacto no existe donde se juntan dos
  cuerdas, y la elección simétrica es su bisectriz, que es el promedio de los
  dos ángulos;
- las dos convergen en segundo orden al mismo límite (sección 2);
- con un terreno dibujado como poligonal, la exacta coge la pendiente del lado
  en que caiga el contacto (orden observado entre 1,7 y 2,4).

El promedio es además lo que `_boundary_ratios` publicaba hasta 0.1.221. D220
hizo que la publicación siguiera a la recursión; D222 mueve la recursión.

Se promedian ángulos y no tangentes. Es la bisectriz, invariante por rotación,
y es el promedio de «inclinaciones» que dice el EM.

## 2. El estudio numérico

Cuatro esquemas:

- **izq**: la dovela de la izquierda, el viejo;
- **der**: la de la derecha;
- **promedio**: la media de las dos dovelas;
- **geom**: la geometría exacta en el contacto.

**Simetría.** Talud de `test_support_normal_v1137`, factor del talud reflejado
menos el del original, en fracción:

| Método | izq, 25 → 800 dovelas | promedio y geom |
|---|---|---|
| Corps #2 | −1,77·10⁻² → −5,5·10⁻⁴ | ~10⁻¹⁰, la tolerancia de la raíz |
| Lowe-Karafiath | −2,11·10⁻³ → −6,4·10⁻⁵ | ~10⁻¹⁰ |

Con izq, la diferencia se reduce a la mitad con cada duplicación: primer
orden. der es exactamente el reflejo de izq.

**Orden de convergencia** con θ(x) suave, de 25 a 1600 dovelas. Se estima como
p = log₂((F(n) − F(2n)) / (F(2n) − F(4n))) y se da el valor asintótico:

| Caso | izq | der | promedio | geom |
|---|---|---|---|---|
| Cara recta, círculo que entra y sale por ella (L-K) | 0,96 | 1,03 | 2,00 | 2,00 |
| Terreno C¹, y = 10(1 − cos(πx/40)), Corps #2 | 1,00 | 1,00 | 2,00 | 1,7–2,4 |
| Terreno C¹, Lowe-Karafiath | 0,97 | 1,03 | 2,00 | 1,8–2,2 |

**Consistencia.** La extrapolación de Richardson de izq, de primer orden, cae
sobre la del promedio, de segundo, las dos con 800 y 1600 dovelas:

- terreno C¹, Corps #2: 1,8982172 frente a 1,8982175;
- Lowe-Karafiath: 1,8415097 frente a 1,8415101.

Los cuatro esquemas convergen al mismo factor; el viejo, más despacio y desde
un lado.

**Con un salto de θ dentro de la masa** (el talud del clavo, coronación en x =
37), la convergencia es irregular en los cuatro esquemas. Con 800 dovelas,
Corps #2 da:

| izq | der | promedio | geom |
|---|---|---|---|
| 1,91617 | 1,91512 | 1,91550 | 1,91590 |

## 3. Las anclas externas

**El 027** (Malkawi, Hassan y Sarma 2001, del manual de XSTABL) tiene un
círculo dado y dos programas publicados.

- Sin grieta, la referencia y XSTABL coinciden en que Lowe-Karafiath es igual
  a Corps #1 y Corps #2 queda 0,003 por encima.
- Corps #1 no depende de la regla, así que las diferencias cancelan lo que el
  modelo tiene en común con el publicado.
- La tolerancia es el redondeo de dos números de tres decimales: ±0,001.

| Regla | Corps #2 − Corps #1 | L-K − Corps #1 |
|---|---|---|
| publicado (los dos programas) | +0,003 | 0,000 |
| **promedio** | **+0,0023** | **−0,0005** |
| izq (viejo) | +0,0033 | −0,0020 ✗ |
| der | +0,0012 ✗ | +0,0011 |

Es estable con la tolerancia de la raíz (igual a 10⁻⁴ y a 10⁻⁸).

**Las tres variantes del 027 con Spencer como vara.** El modelo del banco
tiene un desfase común de +0,8 % en todos los métodos. Desviación de
Lowe-Karafiath respecto de ese desfase, en %:

| Escenario | izq | der | promedio | geom |
|---|---|---|---|---|
| sin grieta | −0,13 | +0,09 | −0,02 | −0,01 |
| grieta seca | −0,06 | +0,09 | +0,01 | +0,03 |
| grieta con agua | −0,08 | +0,07 | −0,01 | +0,01 |

**El 055 y el 056** (Pockoski y Duncan 2000) publican además Lowe-Karafiath de
UTEXAS4, el programa de S. G. Wright, coautor de DW&B y del apéndice C del EM:

| Problema | UTEXAS4 | intervalo de redondeo | OGR izq | OGR promedio |
|---|---|---|---|---|
| 055 | 1,32 | [1,315, 1,325) | 1,3135 ✗ | 1,3179 ✓ |
| 056 | 1,31 | [1,305, 1,315) | 1,3018 ✗ | 1,3056 ✓ |

La referencia publica 1,318 y 1,304: el promedio la clava en el 055, y en el
056 la referencia queda entre las dos reglas.

El 055 tiene además el círculo con el que `test_interslice_split_v1117` fija
Bishop, que reproduce su 1,293 a +0,025 %. Sobre ese círculo, Lowe-Karafiath
con fuerzas totales pasa de 1,31520 a **1,32040**:

- frente al 1,32 de UTEXAS4, de −0,36 % a **+0,03 %**;
- frente al 1,318 de la referencia, de −0,21 % a +0,18 %.

**El 057**: la referencia (1,414) queda más cerca de la regla vieja (−0,19 %)
que de la nueva (+0,23 %). Su UTEXAS4 publicado (1,12) no es coherente con
nada del problema, así que no puede desempatar.

En resumen: dos programas independientes de la referencia (XSTABL en el 027,
UTEXAS4 en el 055 y el 056) excluyen la regla vieja y admiten el promedio. La
propia referencia coincide con el promedio en el 027 y el 055, y queda cerca
en el 056.

## 4. El banco

Censo en `_auditoria/P4_0223` (`_tools/censo_p4_0223.py`), con el interruptor
apagado y encendido, en serie.

**Superficies archivadas o publicadas de Lowe-Karafiath: 18.**

- La mayoría se mueve entre +0,08 y +0,58 %.
- Hay tres casos grandes:
  - el 057 compuesto: +1,71 %, de −1,76 % a −0,09 % del publicado;
  - el 026 publicado: −2,75 %, sobre el mecanismo de Prandtl, cuyo factor
    exacto es 1,0 y cuyo Lowe-Karafiath no publica nadie;
  - el 040 publicado: −3,89 %. Tiene 5 dovelas, donde el error de primer
    orden es grande, y el manual no publica Lowe-Karafiath.
- El 059 y el 060 no se mueven (+0,004 y +0,02 %).

**Búsquedas.** Las 11 filas del banco con Lowe-Karafiath y búsqueda, con
`run_analysis` en serie (`parallel_search = False`: el interruptor no llega a
los hijos del pool). En los desembalses 096–098, «Lowe-Karafiath» es el nombre
de un procedimiento, no del método, y no entran.

| Fila | antes | después | Δ | crítica | publicado | Δ frente al publicado |
|---|---|---|---|---|---|---|
| 027 círculo dado (la lámina de A27-1) | 0,31019 | 0,31111 | +0,30 % | la misma | — | — |
| 027 búsqueda | 1,41387 | 1,41636 | +0,18 % | la misma | 1,392 | +1,57 → +1,75 % |
| 027 grieta seca | 1,54961 | 1,55087 | +0,08 % | la misma | 1,545 | +0,30 → +0,38 % |
| 027 grieta con agua | 1,52767 | 1,52892 | +0,08 % | la misma | 1,522 | +0,37 → +0,45 % |
| 051 | 0,96502 | 0,96678 | +0,18 % | la misma | 1,288 | −25,1 → −24,9 % |
| 055 | 1,31345 | 1,31758 | +0,31 % | otra | 1,318 | **−0,34 → −0,03 %** |
| 056 | 1,30182 | 1,30537 | +0,27 % | otra | 1,304 | −0,17 → +0,10 % |
| 057 circular | 1,41527 | 1,42350 | +0,58 % | la misma | 1,414 | +0,09 → +0,67 % |
| 057 compuesto | 1,33262 | 1,38326 | +3,80 % | otra | 1,385 | **−3,78 → −0,13 %** |
| 059 | 0,56108 | 0,56110 | +0,004 % | la misma | 0,588 | −4,58 → −4,58 % |
| 060 | 1,56509 | 1,56546 | +0,02 % | la misma | 1,021 | +53,3 → +53,3 % |

**Bandas de la comparativa** (OK < 1 %, REVISAR < 5 %): el 057 compuesto pasa
de REVISAR a OK y ninguna fila empeora de banda.

- Entre las filas con publicado reproducible se acercan el 055, el 056 y el
  057 compuesto.
- Se alejan algo:
  - el 027 (+0,08 a +0,18 %), que arrastra el desfase común de su modelo;
  - el 057 circular, que tiene la misma crítica y es el único caso en que la
    referencia favorece la regla vieja (sección 3).

## 5. Hallazgo que se reporta y NO se corrige: D223

- **Corps #1 con grieta de tracción traza su cuerda hasta el fondo de la
  grieta.**
  - En el 027 el fondo está en y = 94,05, y el terreno en la grieta en y =
    104,97.
  - Sobre el círculo dado, frente a lo publicado: sin grieta, +0,84 % (Spencer
    +0,82 %); con la grieta seca, −0,49 % (Spencer +0,78 %); con agua, −0,47 %
    (Spencer +0,86 %).
  - Con la cuerda hasta el terreno vuelve al desfase común: +0,79 % y +0,84 %.
  - Corps #2 y Lowe-Karafiath no dependen de los extremos y quedan en el
    desfase común en las tres variantes.
  - El EM define la cuerda por «the crest and toe of the slope».
  - El banco no calcula Corps #1 en ningún modelo, así que no mueve ninguna
    fila.

## 6. Los cambios

- **`methods/modified_swedish.py`**:
  - `boundary_theta(theta)`, la regla en un solo sitio;
  - la recursión `_march` y `_base_forces` toman la inclinación de cada cara
    del contacto que la lleva;
  - `_boundary_ratios` publica sus tangentes;
  - interruptor `THETA_AT_BOUNDARY`. Apagado reproduce 0.1.222 bit a bit:
    factor, normales, razones, `thrust_reversal` y resistencias, en nueve
    casos contra un `git archive` de c6e5b5b.
- Los contratos no cambian: θ sigue definida por dovela en cada método, y los
  tests que llaman a la recursión con θ constante siguen igual.
- Docstrings al día: el módulo, la recursión, `_base_forces`, Corps #2 y
  `lowe_karafiath.py`.
- La tabla `INTERRUPTORES` del banco pasa a 29.

## 7. Tests

**`test_prescribed_theta_boundary_v1223.py`, 9 casos**:

- simetría por espejo, y su regla 7;
- orden 2 con el promedio y 1 con la regla vieja, sobre el terreno C¹;
- consistencia por Richardson;
- las diferencias publicadas del 027 sobre su modelo, reconstruido en el
  test, y que la regla vieja fallaba en Lowe-Karafiath;
- Corps #1 bit a bit;
- las razones publicadas son las tangentes del promedio.

**Contra 0.1.222 fallan 5 de 9**: 4 por comportamiento y 1 por símbolo
(`boundary_theta`). Pasan los tres casos de regla 7 cuyo estado apagado es el
viejo, y el de Corps #1.

**Cambia a propósito
`test_interslice_thrust_v1222.test_the_old_ratios_part_from_the_method`.** Las
razones promediadas de antes de D220 son ahora las del solver. La regla 7 de
`BOUNDARY_RATIOS_AS_SOLVED` se mide contra la recursión de 0.1.222 (con
`THETA_AT_BOUNDARY` apagado), y con los dos interruptores encendidos las dos
publicaciones son la misma lista.

## 8. Caminos equivocados

- **El primer estudio de orden**, sobre el talud del clavo, dio convergencia
  irregular en los cuatro esquemas. No era ningún esquema: θ salta de 59,7° a
  0° en la coronación, dentro de la masa. Hizo falta un terreno C¹ para medir
  el orden.
- **La escalera de la regla vieja con 50, 100 y 200 dovelas** leía 0,73 en
  Lowe-Karafiath. Su término de primer orden es pequeño frente al de segundo
  en ese terreno, y el orden solo se asienta pasadas las 100 dovelas (0,29,
  0,73, 0,88, 0,94 y 0,97 de 25 a 1600). El test usa 100, 200 y 400.
- **La comparación absoluta con el banco parecía mixta**: el 027 se alejaba un
  0,1 % del publicado. Es el desfase común de ese modelo (+0,8 % en todos los
  métodos). Con Spencer como vara, y con las diferencias frente a Corps #1,
  queda claro.
- **Un script de medida calculaba la «geometría exacta» de Corps #1 con la
  fórmula de Lowe-Karafiath.** Esas filas se descartaron: Corps #1 es
  constante y no depende del esquema.

## 9. Verificación

- Selección dirigida: familia prescrita, validación, EM, James Bay,
  desembalse, marcha y `test_interslice_split_v1117`.
  - 371 de 372 antes de cambiar a propósito el test de D220;
  - 33 de 33 en `interslice_split` y `disjoint_masses`.
- Suite entera: **4970 de 4970**, con el censo del banco corriendo a la vez.
- Interruptor apagado: la familia reproduce 0.1.222 bit a bit.
- Banco:
  - `d222()` cierra, y da NO SE SOSTIENE contra 0.1.222, por comportamiento y
    por código;
  - **`d220()` se actualiza**: la regla 7 de su interruptor se mide contra la
    recursión de 0.1.222, por la misma razón que su test. Sigue cerrando en
    0.1.222 y en 0.1.223 y no en 0.1.221;
  - el primer recorrido en seco de los 160 cierres dio esa bajada, D220, y
    nada más; tras actualizarla, 0 bajadas;
  - D222 queda retirada y D223 abierta en P4, sin prompt largo;
  - auditorías a 0 ERROR (en el 02, los mismos 753 hallazgos que en
    0.1.222);
  - la tabla `INTERRUPTORES` pasa a 29.
- Falta por hacer tras el commit: re-correr las 11 filas del banco que mueve
  (sección 4) para que sus `resultados*.json` digan 0.1.223.

# OGR Slip2D v0.1.224

**D223 — Corps of Engineers #1 traza su línea hasta el TECHO de una grieta de
tracción.** Hasta 0.1.223 la trazaba hasta el fondo de la grieta, que es un
punto de la superficie de deslizamiento por debajo del terreno.

- Sobre el círculo dado del problema 027 con su grieta de 11 ft, Corps #1
  caía un 1,3 % respecto del desfase que comparten todos los métodos de ese
  modelo.
- Hasta el techo de la grieta reproduce lo que publican la referencia y
  XSTABL.

Este cambio mueve Corps #1 **solo cuando una grieta trunca la masa**. En el
banco, cero filas: el único modelo que corre Corps #1, el 095, no tiene
grieta, y no se mueve ni un bit.

Lo que cambia en el banco de verificación (`_tools/`, `_auditoria/`, fichas)
está fuera de git.

---

## 0. Lo que se decidió, y por qué

**Las fuentes.** Duncan, Wright y Brandon (2014, Fig. 6.14) dibujan tres
interpretaciones de la «average inclination of the embankment slope» de USACE
(1970):

1. **(a)** una línea que une los puntos donde la superficie de deslizamiento
   llega al terreno;
2. **(b)** la línea del pie a la coronación del talud, independiente de la
   superficie;
3. **(c)** la pendiente del terreno en cada contacto, que es Corps #2.

La figura de Corps #1 de la documentación de la referencia es la (a), y la
docstring de `CorpsOfEngineers1` dice desde su origen que implementa la (a).
El EM 1110-2-1902 (2003, §C-4a) describe la (b) como lo «usual». OGR no la
implementa, y no se cambia aquí.

**Con una grieta.** La grieta trunca la masa en su extremo de coronación, y la
superficie de rotura (la de deslizamiento más la grieta) llega al terreno en
el TECHO de la grieta. Ese es el punto de la interpretación (a). El fondo de la
grieta no está en el terreno.

**Por qué la pared y no el techo de la dovela extrema.** Una superficie que
sale por una cara vertical del terreno (un muro, un escarpe) deja una dovela
extrema con altura en su borde. Ahí el punto donde la superficie llega al
terreno es su salida por la cara, no la coronación de encima. Por eso:

- la grieta se lee de su pared, `(x, y_fondo, y_techo)`, que el rebanador ya
  calculaba y ahora viaja con las dovelas (`Slices.tension_crack_wall`);
- se toma solo en el extremo que la pared cierra, con tolerancia relativa al
  tamaño de la masa. Una masa que la grieta no truncó, como la lámina que el
  círculo del 027 también corta junto al pie, no termina ahí.

Además, sin grieta el techo y la base de la dovela extrema no son iguales bit
a bit (1,4·10⁻¹⁴ en el 027), así que usar siempre el techo tampoco habría
dejado igual lo que no tiene grieta.

## 1. Los cambios

- **`slicer.py`**:
  - `Slices.tension_crack_wall`: la pared que la grieta dejó, seca o con agua,
    o `None`;
  - `slice_surface` la asigna.
- **`methods/modified_swedish.py`**:
  - `CorpsOfEngineers1._theta_angles` usa el techo de la pared en el extremo
    que cierra;
  - interruptor `CHORD_TO_CRACK_TOP`.
  - Sin pared, las mismas operaciones que antes: bit a bit.
- La tabla `INTERRUPTORES` del banco pasa a 30.

## 2. Lo medido

Círculo dado del 027, 30 dovelas, sobre los modelos del banco. Diferencias
frente a Corps #1, que cancelan lo que el modelo comparte con el publicado:

| Variante | Corps #2 − Corps #1 | L-K − Corps #1 | publicado (los dos programas) | fondo (0.1.223) |
|---|---|---|---|---|
| grieta seca | **+0,0066** | **−0,0101** | +0,007 / −0,010 | +0,0264 / +0,0098 |
| grieta con 6 ft de agua | **+0,0060** | **−0,0098** | +0,006 / −0,010 | +0,0261 / +0,0102 |
| sin grieta | +0,0023 | −0,0005 | +0,003 / 0,000 | igual, bit a bit |

**Con Spencer como vara** (el desfase común del modelo):

| Variante | Spencer | Corps #1 en 0.1.223 | Corps #1 en 0.1.224 |
|---|---|---|---|
| grieta seca | +0,78 % | −0,49 % | +0,79 % |
| grieta con agua | +0,86 % | −0,47 % | +0,84 % |

- La pared, en el 027, es (155,42; 94,05; 104,97): 10,9 ft de grieta. Su x es
  exactamente la del borde de la última dovela.
- **Espejo**: el mismo modelo reflejado, con la grieta en el extremo
  izquierdo, da el mismo factor (1,567286862 seco, 1,544879427 con agua).

## 3. Tests

**`test_corps_one_crack_v1224.py`, 7 casos**:

- las diferencias publicadas del 027 con grieta, seco y con agua, sobre el
  modelo reconstruido en el test;
- que la línea al fondo las fallaba (regla 7);
- que las dovelas llevan la pared en el extremo que cierra, y ninguna sin
  grieta;
- el espejo;
- sin grieta, bit a bit, en el 027 y en el talud de
  `test_support_normal_v1137`.

**Contra 0.1.223 fallan 3 de 7**: 2 por comportamiento y 1 por el campo nuevo.

## 4. El banco

Cero filas. Corps #1 solo lo calcula el 095, sobre su círculo publicado y sin
grieta: el factor es el mismo bit a bit (lo comprueba `d223()`).

## 5. Caminos equivocados

- **«Usar siempre el techo de la dovela extrema».** Era lo más corto, y falla
  dos veces:
  - no es bit a bit igual sin grieta (1,4·10⁻¹⁴);
  - con una superficie que sale por una cara vertical, movería el extremo a la
    coronación.
- **La primera medida sobre el 027 leyó otra masa.** Tomó las dovelas de
  `slice_surface`, que es la lámina de 0,9 ft junto al pie (la primera masa
  por la izquierda, A27-1). Hay que tomar las del resultado de
  `evaluate_circle`, que se queda con el mecanismo real.
- **El test del espejo fallaba contra 0.1.223 por símbolo, no por
  comportamiento.** Leía la pared antes de comparar factores. Se reordenó: la
  guarda de que la línea se movió va primero.

## 6. Verificación

- Selección dirigida (el test nuevo, grietas de tracción, la familia
  prescrita, D222): 91 de 91.
- Suite entera: **4977 de 4977**.
- Banco:
  - `d223()` cierra, y da NO SE SOSTIENE contra 0.1.223;
  - el recorrido en seco de los 161 cierres no da ninguna bajada;
  - D223 queda retirada y P4 queda en D215, D216 y D219;
  - auditorías a 0 ERROR (en el 02, los mismos 753 hallazgos);
  - la tabla `INTERRUPTORES` pasa a 30.

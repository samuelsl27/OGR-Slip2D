# La regla de radios del Grid Search, despejada por medición

**Estado: resuelto en v0.1.88.** Este documento es la derivación, para que el
`0.05` del código no vuelva a ser un número sin padre. Sustituye al pendiente
1 de `docs/PENDIENTES.md`, que queda cerrado.

Historia corta: v0.1.18 puso un intervalo de radios inventado y razonable.
v0.1.84 midió que no era el de la referencia, probó a leer literalmente la
figura de la documentación, comprobó que mejoraba un modelo y empeoraba el
otro al doble, y **lo revirtió** dejando escrito por qué (regla 6). Lo que
faltaba no era ingenio, era un dato. Ya está.

---

## 1 · Por qué no se podía deducir antes

La documentación de *Grid Search* dice sólo esto:

> «For each slip center in a grid, suitable Minimum and Maximum radii are
> determined, based on the distances from the slip center to the slope
> surface.»

«Based on the distances» admite infinitas lecturas. Y las restricciones
disponibles eran cuatro números —los dos centros críticos de cada ejemplo—
frente a un intervalo con dos extremos y una constante. Ajustar parámetros
hasta que cuadren cuatro números es exactamente lo que la regla 1 prohíbe,
porque el resultado pasa el test que se construyó para que lo pase.

## 2 · El experimento

En `referencias/Ejemplos/00_2026_08_17_Test_Regla_radios`, seis modelos
ejecutados en el programa de referencia. Los `.slim` son ZIP; dentro, el
`.sli` es texto (rejilla, Slope Limits, `rinc`) y el `.s01` lleva, por cada
centro, **todos los círculos generados**:

```
* surface center xc,yc
*   all circles (r,yleft,x1,y1,x2,y2,yright,fs...,b1)
84 66 2
  36.3156666795018 46.8663296181119 ... 2.17326 2.17389 ...
  53.6015638426406 50 ...             1.6249  1.95679 ...
```

Los radios **se leen**. No hay ajuste, así que no hay nada que la regla 1
pueda reprochar.

El diseño es lo que lo hace concluyente: pares del mismo modelo con **Radius
Increment 1 y 10** sobre la misma rejilla. Con incremento 1 salen exactamente
dos círculos, que son el intervalo desnudo; con 10 salen once. Y los dos
primeros coinciden con los extremos de los once — de donde el retranqueo **no
depende de cuántos círculos se pidan**, que es justo lo que una sola corrida
no puede decir.

| modelo | geometría | rejilla | `rinc` | sentido |
|---|---|---|---|---|
| Ej_1 A1 | Ej_1 | 2×2 en (84,66)–(88,70.5) | 1 | izq → der |
| Ej_1 A2 | Ej_1 | la misma | 10 | izq → der |
| Ej_2 B1 | Ej_2 | 4×4 en (−3.333,61.316)–(12.381,87.632) | 1 | der → izq |
| Ej_2 B2 | Ej_2 | la misma | 10 | der → izq |
| Ej_1/Ej_2 General | ambas | la de referencia completa | 10 | — |

Las rejillas B se eligieron con criterio: su esquina es exactamente el centro
crítico de Ej_2, `(−3.333333, 87.631579)`.

## 3 · La regla

Con `S` el perfil del terreno entre los Slope Limits y `P_L`, `P_R` los dos
puntos límite:

```
d_min = distancia mínima del centro al punto más cercano de S
d_max = min( |C − P_L| , |C − P_R| )
δ     = 0,05 · (d_max − d_min)

r_min = d_min + δ
r_max = d_max − δ
r_k   = r_min + k·(r_max − r_min)/rinc      k = 0 … rinc
```

Tres cosas que no son evidentes y sí importan:

**`d_min` es a la POLILÍNEA, no a los vértices.** El punto más cercano es el
pie de una perpendicular cuando cae dentro de un tramo y un **vértice**
cuando no, y los dos casos aparecen entre los centros de referencia: en
`(12,381 , 87,632)` de Ej_2 el más cercano es el vértice `(40, 55)`. La
implementación anterior medía sólo a vértices, que es una medición distinta.

**`d_max` es al límite que se alcanza ANTES, no al más lejano.** Al crecer el
radio, un extremo del círculo avanza hacia un límite y el otro hacia el otro;
el primero que se toca es el que manda. Por eso es un `min`, y por eso leer la
figura como «al límite más lejano» daba +1,99 % en Ej_1.

**`d_max ≥ d_min` es un teorema, no un caso a proteger.** `P_L` y `P_R` son
puntos *de* `S`, así que sus distancias no pueden bajar del mínimo a `S`. De
ahí que la función no pueda fallar y la población sea exactamente
`(nx+1)(ny+1)(rinc+1)`.

Lectura equivalente del retranqueo, por si ayuda a recordarlo: el intervalo
muestreado es el **90 % central** de `[d_min, d_max]`; o los puntos medios del
primero y del último de diez subintervalos iguales.

## 4 · La comprobación

Implementación ya integrada contra **todos** los círculos de los seis
modelos, no sólo los extremos:

| modelo | centros | `rinc` | peor \|r_generado − r_referencia\| |
|---|---|---|---|
| Ej_1 rejilla de referencia | 441 | 10 | 4,00 · 10⁻⁸ (*) |
| Ej_2 rejilla de referencia | 440 | 10 | 7,53 · 10⁻¹³ |
| Ej_1 A1 | 9 | 1 | 4,26 · 10⁻¹⁴ |
| Ej_1 A2 | 9 | 10 | 4,97 · 10⁻¹⁴ |
| Ej_2 B1 | 25 | 1 | 5,68 · 10⁻¹⁴ |
| Ej_2 B2 | 25 | 10 | 6,40 · 10⁻¹⁴ |

Son 949 centros y del orden de 10 000 radios. El error mediano en la rejilla
de Ej_1 es 3,2 · 10⁻¹⁴.

(*) El único residuo por encima de 10⁻¹² es **un** centro: `(52, 48)` de Ej_1,
que está exactamente **sobre** la cara del talud (52 + 48 = 100), así que
`d_min = 0`. Ahí la referencia imprime 2,601922406 donde la regla da
2,601922366: 1,5 · 10⁻⁸ relativo. Es la numérica de su propia búsqueda de
punto más cercano en el caso degenerado. Queda como test, con tolerancia
1e-7 y explicado, para que si algún día la implementación se desvía más que
eso no se confunda con esto.

### Los dos radios que no se generaban

Es el hallazgo, y es binario: no se trataba de precisión sino de **ausencia**.

| ejemplo | centro crítico | radio de referencia | ¿generado antes? | ahora |
|---|---|---|---|---|
| Ej_1 | (88 , 70,5) | 47,2124436389792 | **no** | sí, el 5.º de 11 |
| Ej_2 | (−3,3333 , 87,6316) | 60,2564659389906 | **no** | sí, el 4.º de 11 |

Los once radios que este programa generaba en el centro crítico de Ej_2 eran
`53,72 · 58,83 · 63,94 · 69,05 · 74,16 · 79,27 · 84,38 · 89,49 · 94,60 ·
99,72 · 104,83`. Ninguna búsqueda encuentra una superficie que nunca generó, y
ningún test de método podía verlo: sobre el círculo correcto los factores de
seguridad siempre habían coincidido.

### Caso degenerado, y el denominador

Cuando el centro cae justo encima de un punto límite, `d_min = d_max` y la
regla da `rinc + 1` radios **idénticos**. La referencia hace lo mismo: en
`(120, 30)` de Ej_1 emite once círculos de R = 5.

Esto no es una curiosidad. Un primer borrador devolvía «sin intervalo» en ese
caso y descartaba en silencio los 21 centros de la columna `x = 120`: la
población de Ej_1 bajaba de 4851 a 4620. Mover ese denominador es exactamente
lo que v0.1.83 arregló, así que la regla se aplica sin excepciones y hay un
test de la identidad `(nx+1)(ny+1)(rinc+1)` sobre una rejilla colocada a
propósito encima del límite.

## 5 · Efecto en los dos modelos de referencia

Rejilla de referencia completa, 25 dovelas, `rinc` 10, comprobación m-alpha
activada. «REF» quiere decir que el mínimo cae en el centro **y** el radio de
la referencia, no en un vecino.

### Ej_1 — población 4851 en los siete métodos

| método | antes | ahora | error | círculo |
|---|---|---|---|---|
| ordinary/fellenius | | 0,850046 | +0,060 % | REF |
| bishop simplified | 0,884517 (+0,18 %) | 0,883065 | **+0,020 %** | REF |
| janbu simplified | 0,837923 (−0,55 %) | 0,843627 | +0,128 % | REF |
| janbu corrected | | 0,883917 | +0,100 % | REF |
| spencer | | 0,882489 | +0,635 % | REF |
| lowe-karafiath | | 0,885966 | +0,084 % | REF |
| gle/morgenstern-price | | 0,875161 | −0,362 % | **otro** (84 , 66) r 41,5014 |

### Ej_2 — población 4840 en los siete métodos

| método | antes | ahora | error | círculo |
|---|---|---|---|---|
| ordinary/fellenius | | 1,114129 | −0,026 % | REF |
| bishop simplified | 1,166658 (+0,95 %) | 1,154851 | **−0,068 %** | REF |
| janbu simplified | 1,093974 (+0,83 %) | 1,084608 | −0,030 % | REF |
| janbu corrected | | 1,149223 | −0,002 % | REF |
| spencer | | 1,154548 | −0,181 % | REF |
| lowe-karafiath | | 1,161674 | −0,123 % | REF |
| gle/morgenstern-price | | 1,154840 | −0,260 % | REF |

**13 de 14 caen en el círculo de la referencia.** El error máximo de Bishop
pasa de +0,95 % a −0,07 %.

La excepción, GLE en Ej_1, **no es un problema de muestreo**: encuentra un
mínimo *más bajo* (0,875161) en el centro (84, 66) que el que la referencia
declara en (88 , 70,5). Es decir, sobre la población correcta OGR ordena los
círculos distinto para GLE. Eso pertenece a
`docs/audits/spencer_gle_interslice_v179.md`, que sigue abierto: allí está
medido que Spencer y GLE de OGR se separan de Bishop mucho menos que en las
referencias publicadas. Spencer en Ej_1, con +0,635 %, es el mismo asunto.
Ninguno de los dos empeoró con este cambio; lo que hizo el cambio fue dejar
de esconderlos detrás de un muestreo equivocado.

## 6 · Contraste independiente: los cinco casos publicados

La regla se dedujo de un programa. Que reproduzca ese programa mejor no
demuestra que sea mejor física. Los cinco casos de `validacion/casos/` son la
comprobación que sí es independiente: ninguno es una corrida de la referencia,
todos vienen de literatura.

| caso | referencia | antes | ahora | tolerancia |
|---|---|---|---|---|
| 001 ACADS 1(a) — Bishop | 0,991 | +0,00 % | −0,24 % | 2,0 % |
| 001 ACADS 1(a) — Janbu corr. | 0,991 | +0,03 % | −0,06 % | 2,0 % |
| 002 Yamagami-Ueta — Bishop | 1,348 | +0,44 % | **+0,17 %** | 1,5 % |
| 002 Yamagami-Ueta — Fellenius | 1,282 | +0,31 % | +0,25 % | 1,5 % |
| 003 ACADS 1(c) — Bishop | 1,406 | +0,03 % | +0,27 % | 1,5 % |
| 004 Arai-Tagyo 1 — Bishop | 1,451 | −2,58 % | −2,65 % | 3,5 % |
| 005 Arai-Tagyo 3 — Bishop | 1,138 | −1,59 % | **−1,51 %** | 2,5 % |

Los siete siguen dentro de su tolerancia. Se mueven poco (0,24 % el que más)
y **en las dos direcciones**, que a primera vista sorprende: si el muestreo es
más ancho, ¿cómo puede subir un mínimo? Porque los dos conjuntos de círculos
no son anidados — el intervalo viejo llegaba a `r_toe · 1,08`, que en algunos
centros pasa de `r_max`. No hay degradación, y tampoco una mejora que se pueda
presentar como validación: la conclusión honesta es que en estos cinco casos
el muestreo no era lo que limitaba.

## 7 · Lo que NO está medido

En los seis modelos los Slope Limits están en su **posición automática**, que
coincide con los extremos del perfil del terreno. Los datos, por tanto, no
distinguen:

- si `d_max` se mide a los **puntos límite** o a los **extremos del perfil**;
- si `d_min` se mide sobre el perfil **recortado** o sobre el **completo**.

Se ha implementado la lectura documentada —«the slope surface is simply the
segments of the External Boundary between the Slope Limits»—, de modo que
estrechar los límites estrecha los radios. Está dicho en el docstring de
`GridSearch._radius_bracket` con estas palabras, y hay un test de que mover
los límites mueve el intervalo (regla 7).

El experimento que lo cerraría, **pendiente**:

> Los modelos A1 y B1 tal cual (pocos centros, `rinc = 1`) pero con los Slope
> Limits **metidos hacia dentro**, a una `x` que **no** sea vértice del
> perfil — en Ej_1, por ejemplo, x = 20 y x = 100, cuyos vértices están en 0,
> 50, 75 y 120. Con `rinc = 1` siguen saliendo dos círculos por centro, y sus
> radios responden las dos preguntas de arriba a la vez, más si el 5 % sigue
> siendo 5 %.

## 8 · `min_radius`

La referencia **no tiene** control de radio mínimo; ofrece *Minimum Elevation*
y *Minimum Depth*. `min_radius` es un añadido de OGR y actúa como suelo de
`d_min`.

Su predeterminado pasa de 2,0 a **0,0** en `GridSearch`, y de 3,0 a 0,0 en
`analysis_runner.build_search`. Motivo: cualquier suelo distinto de cero hace
que la configuración de fábrica muestree una población distinta de la de la
referencia en todo centro cuyo punto de terreno más cercano esté por debajo de
ese valor. Medido: con 3,0 y con 0,0 el factor de seguridad de los cinco casos
publicados es **idéntico**; sólo cambian los recuentos de válidas en unas
unidades. Se conserva la opción porque excluir círculos diminutos es una cosa
legítima de querer, con su test de que mueve el número (regla 7).

---

## Reproducir esto

Los `.s01` son texto dentro de los ZIP `.slim`. El formato de cada centro es
`xc yc n` seguido de `n` líneas cuyo primer campo es el radio. Comparar contra
la implementación no necesita nada más que `GridSearch._radius_bracket` y el
perfil que devuelve `GridSearch._slope_surface`.

Los tests permanentes viven en `tests/test_grid_radius_rule_v188.py`, con los
valores de referencia escritos a mano y su procedencia en comentarios, porque
`referencias/` no forma parte del repositorio y la suite tiene que correr
desde un clon limpio.

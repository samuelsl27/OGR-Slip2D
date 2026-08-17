# OGR Slip2D v0.1.88 — el círculo crítico de la referencia no estaba entre los que el programa dibujaba

El pendiente más antiguo abierto, y no era un problema de precisión: era de
**ausencia**. En el centro crítico del Ejemplo 2, `(−3,333 , 87,632)`, los
once radios que este programa generaba eran

```
53,72 · 58,83 · 63,94 · 69,05 · 74,16 · 79,27 · 84,38 · 89,49 · 94,60 · 99,72 · 104,83
```

y el radio crítico de la referencia, **60,257**, no está ahí. Una búsqueda no
encuentra una superficie que nunca generó. Y ningún test de método podía
verlo, porque **sobre el círculo correcto los siete métodos ya coincidían**
con la referencia entre −0,00 % y −0,26 % desde v0.1.84. El error se veía
sólo en el mínimo global: +0,95 % en Ej_2, y en Ej_1 el mínimo de Janbu caía
en un centro que no era el de la referencia.

Ahora los dos radios se generan, y **13 de los 14 mínimos globales (siete
métodos × dos ejemplos) caen en el centro Y el radio de la referencia**, no en
un vecino.

| | antes | ahora | círculo |
|---|---|---|---|
| Ej_1 Bishop | 0,884517 (+0,18 %) | **0,883065 (+0,020 %)** | el de la referencia |
| Ej_1 Janbu simpl. | 0,837923 (−0,55 %, otro centro) | **0,843627 (+0,128 %)** | el de la referencia |
| Ej_2 Bishop | 1,166658 (+0,95 %) | **1,154851 (−0,068 %)** | el de la referencia |
| Ej_2 Janbu simpl. | 1,093974 (+0,83 %) | **1,084608 (−0,030 %)** | el de la referencia |

La derivación completa, con todas las tablas, en
`docs/audits/grid_radius_rule_v188.md`.

---

## 1 · Lo que faltaba era un dato, no una idea

v0.1.18 puso un intervalo de radios inventado y razonable: mínimo a la
distancia al vértice más cercano del perfil, máximo a la distancia al pie más
un 8 %. v0.1.84 midió que no era el de la referencia, probó a leer
literalmente la figura de la documentación (`fig_gridsearch2.gif`), obtuvo
**mejor en un modelo y el doble de malo en el otro** —Ej_1 pasaba de +0,18 % a
+1,99 %— y **lo revirtió** dejando escrito por qué. Aquella decisión fue la
correcta: las restricciones disponibles eran cuatro números frente a un
intervalo con dos extremos y una constante, y ajustar parámetros hasta que
cuadren cuatro números es exactamente lo que la regla 1 prohíbe.

Lo que desbloqueó esto fue el experimento pedido en `docs/PENDIENTES.md` y
ejecutado en `referencias/Ejemplos/00_2026_08_17_Test_Regla_radios`. La clave
está en el diseño: pares del mismo modelo con **Radius Increment 1 y 10** sobre
la misma rejilla. Con incremento 1 salen exactamente dos círculos, que son el
intervalo desnudo, y **se leen** del `.s01` en vez de deducirse.

El detalle que hizo el experimento concluyente en lugar de sólo útil: los dos
radios del `rinc = 1` coinciden con los extremos de los once del `rinc = 10`.
De ahí que el retranqueo sea una constante de la regla y no una función de
cuántos círculos se piden — algo que **una sola corrida no puede decir**.

## 2 · La regla

Con `S` el perfil del terreno entre los Slope Limits y `P_L`, `P_R` los dos
puntos límite:

```
d_min = distancia mínima del centro al punto más cercano de S
d_max = min( |C − P_L| , |C − P_R| )
δ     = 0,05 · (d_max − d_min)

r_min = d_min + δ        r_max = d_max − δ
rinc + 1 radios equiespaciados entre los dos
```

Tres cosas que no se ven a simple vista y las tres eran fallos antes:

**`d_min` es a la POLILÍNEA, no a los vértices.** El punto más cercano es el
pie de una perpendicular cuando cae dentro de un tramo y un **vértice** cuando
no. Los dos casos aparecen en la referencia: en `(12,381 , 87,632)` de Ej_2 el
más cercano es el vértice `(40, 55)`.

**`d_max` es al límite que se alcanza ANTES, no al más lejano.** Al crecer el
radio un extremo del círculo va hacia un límite y el otro hacia el otro; manda
el primero que se toca. Por eso es un `min` — y por eso leer la figura como «al
límite más lejano» daba +1,99 % en Ej_1.

**`d_max ≥ d_min` es un teorema.** `P_L` y `P_R` son puntos *de* `S`, así que
sus distancias no pueden bajar del mínimo a `S`. La función no puede fallar, y
por tanto la población es exactamente `(nx+1)(ny+1)(rinc+1)`.

## 3 · Un borrador que se llevó por delante el denominador de v0.1.83

Merece contarse porque es el camino equivocado más instructivo de esta
versión, y porque el aviso venía de dos versiones antes.

Cuando el centro cae justo encima de un punto límite, `d_min = d_max` y el
intervalo tiene **anchura cero**. Parece un caso degenerado que hay que
descartar, y el primer borrador lo descartaba. Consecuencia: los 21 centros de
la columna `x = 120` de Ej_1 no generaban nada y la población bajaba de **4851
a 4620**.

Mover ese denominador es precisamente lo que v0.1.83 arregló («1697
superficies se esfumaban del recuento, y el denominador se movía solo»). Y la
referencia no descarta nada: en `(120, 30)` emite **once círculos de R = 5**,
idénticos. Así que la regla se aplica sin excepciones, y hay un test de la
identidad `(nx+1)(ny+1)(rinc+1)` sobre una rejilla colocada a propósito encima
del límite —con su propio test de que la rejilla sigue estando encima, porque
si dejara de estarlo el primero pasaría sin comprobar nada.

Dos huecos más por los que se escapaban círculos del recuento, tapados de
paso: `bracket is None` y `r <= 0` hacían `continue` sin contar.

## 4 · Comprobación

Contra **todos** los círculos de los seis modelos, no sólo los extremos del
intervalo: 949 centros, del orden de 10 000 radios.

| modelo | centros | `rinc` | peor \|r_generado − r_referencia\| |
|---|---|---|---|
| Ej_1 rejilla de referencia | 441 | 10 | 4,00 · 10⁻⁸ (*) |
| Ej_2 rejilla de referencia | 440 | 10 | 7,53 · 10⁻¹³ |
| Ej_1 A1 / A2 | 9 | 1 / 10 | 4,97 · 10⁻¹⁴ |
| Ej_2 B1 / B2 | 25 | 1 / 10 | 6,40 · 10⁻¹⁴ |

(*) **Un** centro: `(52, 48)` de Ej_1, que está exactamente sobre la cara del
talud, luego `d_min = 0`. La referencia imprime 2,601922406 donde la regla da
2,601922366 — 1,5 · 10⁻⁸ relativo, la numérica de su propia búsqueda en el
caso degenerado. Queda como test explícito con tolerancia 1e-7, para que si la
implementación se desvía algún día más que eso no se confunda con esto.

### El contraste que sí es independiente

La regla se dedujo de un programa; reproducir mejor ese programa no demuestra
mejor física. Los cinco casos **publicados** de `validacion/casos/` sí lo
comprueban, y los siete valores siguen dentro de su tolerancia:

| caso | referencia | antes | ahora | tol. |
|---|---|---|---|---|
| 001 ACADS 1(a) Bishop | 0,991 | +0,00 % | −0,24 % | 2,0 % |
| 001 ACADS 1(a) Janbu corr. | 0,991 | +0,03 % | −0,06 % | 2,0 % |
| 002 Yamagami-Ueta Bishop | 1,348 | +0,44 % | **+0,17 %** | 1,5 % |
| 002 Yamagami-Ueta Fellenius | 1,282 | +0,31 % | +0,25 % | 1,5 % |
| 003 ACADS 1(c) Bishop | 1,406 | +0,03 % | +0,27 % | 1,5 % |
| 004 Arai-Tagyo 1 Bishop | 1,451 | −2,58 % | −2,65 % | 3,5 % |
| 005 Arai-Tagyo 3 Bishop | 1,138 | −1,59 % | **−1,51 %** | 2,5 % |

Se mueven poco y **en las dos direcciones**, lo que a primera vista no cuadra:
si el muestreo es más ancho, ¿cómo sube un mínimo? Porque los dos conjuntos de
círculos **no son anidados** — el intervalo viejo llegaba a `r_toe · 1,08`, que
en algunos centros pasa del `r_max` nuevo. La conclusión honesta no es «mejora
los casos publicados», es que **en estos cinco el muestreo no era lo que
limitaba**.

## 5 · Lo que este cambio dejó a la vista

GLE en Ej_1 es el único de los catorce que **no** cae en el círculo de la
referencia: encuentra un mínimo *más bajo* (0,875161) en el centro (84, 66)
que el que la referencia declara en (88 , 70,5). Y Spencer en Ej_1 se queda en
+0,635 %, el peor de los catorce.

No es una regresión de esta versión: es
`docs/audits/spencer_gle_interslice_v179.md`, que sigue abierto, donde está
medido que Spencer y GLE de OGR se separan de Bishop mucho menos que en las
referencias publicadas. Lo que hizo este cambio fue **dejar de esconderlo**
detrás de un muestreo equivocado.

## 6 · `min_radius` pasa a valer 0 por defecto

La referencia no tiene control de radio mínimo; ofrece *Minimum Elevation* y
*Minimum Depth*. `min_radius` es un añadido de OGR, y cualquier valor distinto
de cero hacía que la configuración de fábrica muestreara una población
distinta de la de la referencia en todo centro cuyo terreno más cercano
estuviera por debajo de ese valor.

Predeterminado 2,0 → **0,0** en `GridSearch`, y 3,0 → **0,0** en
`analysis_runner.build_search` (que es por donde pasan la interfaz, la CLI y
los casos de validación). Medido: con 3,0 y con 0,0 el factor de seguridad de
los cinco casos publicados es **idéntico**; sólo cambian los recuentos de
válidas en unas unidades. Se conserva la opción porque excluir círculos
diminutos es legítimo, con su test de que mueve el número (regla 7).

## 7 · Los Slope Limits ya no se recortan filtrando vértices

`_slope_surface` se quedaba con los vértices cuya `x` cae entre los límites.
Eso **tira el tramo que un límite corta por el medio**: un límite que no
coincide con un vértice no producía punto alguno, la superficie terminaba en el
último vértice estrictamente interior, y los dos extremos del intervalo se
medían al sitio equivocado. Con la regla nueva eso importa el doble, porque
`d_max` se mide **a los puntos límite**.

Ahora el recorte interpola las dos abscisas límite. Test analítico, no captura:
en el perfil de Ej_1 la cara baja 1 en 1 de (50,50) a (75,25), así que a x = 60
el terreno está exactamente en y = 40.

## 8 · Lo que queda sin medir, y se dice

En los seis modelos los Slope Limits están en su **posición automática**, que
coincide con los extremos del perfil. Los datos no distinguen si `d_max` se
mide a los *puntos límite* o a los *extremos del perfil*, ni si `d_min` se mide
sobre el perfil recortado o el completo.

Se implementa la lectura documentada —«the slope surface is simply the segments
of the External Boundary between the Slope Limits»— y queda dicho con esas
palabras en el docstring. El experimento que lo cerraría está escrito en el
§7 de la auditoría: los modelos A1 y B1 tal cual, pero con los límites metidos
hacia dentro a una `x` que **no** sea vértice del perfil.

---

## Archivos

- `ogr_slip2d/search.py` — `_radius_bracket` reescrito con la derivación en el
  docstring, `_distance_to_surface` nuevo, `_slope_surface` recorta
  interpolando, `min_radius` 2,0 → 0,0, dos huecos del recuento tapados.
- `ogr_slip2d/analysis_runner.py` — `min_radius` 3,0 → 0,0.
- `tests/test_grid_radius_rule_v188.py` — nuevo, 19 casos.
- `tests/test_slide_validation_ej1.py` — tolerancias 1 % → 0,5 %, asertos
  nuevos de centro y radio críticos y de población, y las seis corridas de
  rejilla del archivo compartidas en una caché por método (dos en lugar de
  cuatro; el test de informe PDF ya no lanza las suyas).
- `tests/test_slide_validation_ej2_v184.py` — tolerancia 2 % → 0,5 %, aserto
  nuevo de centro y radio críticos, `min_radius` 2,0 → 0,0.
- `docs/audits/grid_radius_rule_v188.md` — nuevo, la derivación completa.
- `docs/PENDIENTES.md` — se borra la entrada 1, cerrada.

## Probado

- **Suite entera sin argumentos: 1861 / 1861, cero fallos.**
- `tests/test_grid_radius_rule_v188.py` — 19/19.
- `tests/_runner.py slide_validation` — 34/34 con las tolerancias apretadas.
- `tests/_runner.py validation_cases published_cases acads` — 35/35; los cinco
  casos publicados dentro de tolerancia.
- Los siete métodos sobre las dos rejillas de referencia completas, población
  4851 y 4840 exactas.
- Los seis modelos de medición, círculo a círculo: 949 centros, ~10 000 radios.

El triaje que este cambio hacía prever —tests cuyo valor esperado era una
captura de la salida de OGR y habría que re-derivar— **no hizo falta**. Cambiar
el muestreo en 441 centros y que 1861 aserciones aguanten no estaba
garantizado; dice que las tolerancias del proyecto están puestas con criterio.

### Y un camino equivocado que me hice a mí mismo

La primera corrida de la suite dio 1860/1861, con un fallo en
`test_about_version_is_not_a_stale_literal`: `('0.1.87', '0.1.88')`. La lectura
inmediata —«hay un octavo sitio con la versión que AGENTS.md no lista»— era
falsa. `ogr_gui/dialogs/misc_dialogs.py` **deriva** `VERSION` leyendo
`pyproject.toml` al importarse, y la lista de siete está completa.

Lo que pasó fue que **edité el árbol con la suite en marcha**: ese módulo se
importó antes del cambio de versión y leyó 0.1.87, mientras el test releía
`pyproject.toml` ya en 0.1.88. La corrida entera quedó inservible, porque
también se tocó `search.py` mientras corría.

Es exactamente la clase de error del pendiente 4 —confundir *qué código se está
midiendo* con *qué código está en el disco*— y salió a los diez minutos de
haberlo diagnosticado. Se repitió la suite con el árbol quieto. Regla para la
casa: **mientras la suite corre, no se toca nada**; y un fallo de versión con
dos números distintos es sospechoso de esto antes que de un sitio olvidado.

## Sin probar

- La regla con los Slope Limits movidos hacia dentro (§8). Es la única pieza
  no medida, y necesita una corrida más en el programa de referencia.

# OGR Slip2D v0.1.82 — el círculo se quedaba a medias, y la leyenda explicaba un color que nadie pintaba

Esta versión sale del **Ejemplo 1** rehecho en el programa de referencia
(`referencias/Ejemplos/Ej_1/`). El motor LEM no ha cambiado: los siete
métodos siguen coincidiendo con el informe de referencia como venían
haciéndolo desde v0.1.19. Lo que ha cambiado es todo lo que rodeaba a ese
motor y no se sostenía al mirarlo de cerca.

Cuatro de los cinco hallazgos son la misma falta, la **regla 7**: un ajuste
que no hace nada. Y el quinto explica una anomalía que llevaba anotada en
`AGENTS.md` desde v0.1.32 sin diagnóstico.

---

## 1 · La curvatura inversa: 522 círculos analizados con la geometría mal

`create_tension_crack_reverse_curvature` existía en `SearchSettings`, se
guardaba en el `.ogr`, se editaba en el diálogo de Surface Options… y
**ningún módulo de `ogr_slip2d` la leía**. Un `grep` sobre el paquete
entero devolvía cero resultados fuera de los ajustes y la interfaz.

### Qué es una superficie de curvatura inversa

Un círculo cuyo **centro está por debajo de la cota máxima del terreno**
puede cortar la superficie del terreno en un punto que queda *por encima
de su propio centro*. Recorriendo el arco desde ahí hacia abajo, la x
primero **decrece** hasta `x_c − R` y luego vuelve a crecer: la superficie
se vuelve hacia atrás y forma un voladizo. No puede existir.

La documentación de referencia (Grid Search, *Reverse Curvature Surfaces*)
da exactamente dos tratamientos, y ahora están los dos implementados:

- **Casilla marcada** — se genera una **grieta de tracción vertical en el
  punto donde la superficie empieza a invertirse, o sea donde su cota
  iguala la del centro**. En un círculo ese punto es el de tangente
  vertical, `x = x_c ∓ R`. Eso es literalmente el «alarga el círculo hasta
  la frontera en 90 grados» del documento del ejemplo.
- **Casilla sin marcar** — la superficie **se descarta**.

La grieta así creada es **siempre seca**: es una consecuencia geométrica de
la búsqueda, no un elemento del modelo, así que no lleva empuje
hidrostático. La grieta que el usuario dibuja como *boundary* sí lo lleva,
y sigue por su camino de siempre (`_apply_tension_crack`). Son dos cosas
distintas y ahora el docstring lo dice.

### Lo que estaba pasando en su lugar

Se cortaba en la intersección real con el terreno —que cae en el cuadrante
superior del círculo— y la base se dibujaba sobre el **arco inferior**.
Para el círculo `c=(68 , 34,5) R=13,519`: el corte quedaba en
`(57,27 , 42,73)` y la base arrancaba en `y = 26,28`, **16 m por debajo del
terreno**. Nadie lo veía porque la primera dovela salía alta y el número,
sin más, parecía razonable.

| | nuestro FS | referencia | error |
|---|---|---|---|
| `c=(68 , 34,5) R=13,519` **antes** | 2,0757 | 1,588 | **+30,7 %** |
| `c=(68 , 34,5) R=13,519` **ahora** | 1,5646 | 1,588 | +1,5 % |
| `c=(72 , 34,5) R=10,803` antes | 1,3449 | 1,330 | +1,1 % |
| `c=(72 , 34,5) R=10,803` ahora | 1,3142 | 1,330 | +1,2 % |

Los dos valores de referencia se leen de las capturas de *Add Query* del
mismo modelo, que es de donde salió la pregunta.

**En la malla de referencia (40–120 × 30–120, 20×20, incremento 10) hay
4851 círculos —el mismo número exacto que informa la referencia— y 522 de
ellos (16,4 %) tienen curvatura inversa.** Sobre esa malla, con la opción
activada se evalúan 2966 superficies válidas; desactivada, 2448.

**El mínimo global no se mueve**: el crítico entra en el terreno por
`(45,470 , 50,0)`, *por debajo* de su centro `y_c = 70,5`, así que no es
una superficie de curvatura inversa. Sigue en `(88 , 70,5)` con
FS = 0,884517 frente a los 0,882889 de la referencia (+0,18 %).

### El 1,5 % que queda

No es discretización: refinando a 50, 100, 200 y 400 dovelas el resultado
converge a 1,5637, no hacia 1,588. Es una diferencia de formulación y
queda anotada aquí sin inventarle una explicación.

---

## 2 · La anomalía m-alpha: el criterio no estaba mal, se leía en el espejo

`AGENTS.md` recoge desde v0.1.32 que la comprobación m-alpha «habría
rechazado el círculo crítico validado contra la referencia (por eso sigue
desactivada por defecto)». Ahora hay diagnóstico.

`m_alpha = cos α + s·sin α·tan φ / F` **no es simétrica en α**, así que
solo significa algo evaluada con el mismo sentido de deslizamiento `s` que
usó el método. Todos los solvers lo deducen de `sign(Σ W·sin α)` y lo
arrastran a su iteración; `checks.py` **omitía el factor**.

Sobre el círculo crítico validado (88 , 70,5), R = 47,212, FS = 0,883074,
con `slide_sign = −1`:

| | min m_alpha | dovelas < 0,2 |
|---|---|---|
| como se comprobaba | **−0,0100** | 5 |
| con el signo del solver | **+0,9282** | 0 |

Y la comprobación se equivocaba en las dos direcciones. Sobre la cuña
degenerada de Block Search, la dovela 14 —el tramo casi vertical
ascendente, +73,8°, en la zona pasiva— tiene ahora `m_alpha = −0,42` y una
tensión normal efectiva en base de unos −300 kPa. Antes el signo espejado
la daba por sana. Es exactamente el caso que la referencia describe para su
error −112: *«deep seated slip surfaces with many high negative base angle
slices in the passive zone»*.

**El defecto sigue siendo OFF**, así que ningún resultado publicado cambia.
Queda pendiente la comparación de recuentos: la referencia trae la
comprobación activada e informa de −112 en **97 de 4851** superficies con
Bishop.

---

## 3 · La leyenda: el color por defecto, medido y no inventado

Los 24 colores de la leyenda por defecto de la referencia se han
**muestreado píxel a píxel** de la captura del Interpret del Ejemplo 1:
rango **fijo 0–6**, 24 bandas de 0,25, de `#ff0000` a `#0000ff`. Trazan una
rampa de tono HSV de 0° a 230° en pasos de 10°, con la última banda forzada
a azul puro — pero lo que se escribe en `PALETTES` es la medición, no la
rampa, porque la medición es el dato.

Se indexan, no se interpolan: muestrear una rampa de 24 paradas en los
centros de banda cae a mitad de camino entre cada par de colores medidos,
y entonces **ninguno de los colores de la referencia llegaría a dibujarse
nunca**.

### Por qué fijo y no automático

Nuestro rango automático usa un percentil, y en la captura del usuario dio
**0,90 → 31,34**: todo lo que importa —de 0,8 a 1,5— aplastado en la
primera banda. Pero el problema de fondo no es la resolución: es que con
rango automático **la escala se reconstruye con lo que traiga el resultado
de turno**, así que 0,883 sale de un color con Bishop y de otro con Janbu
sobre el mismo modelo. Nada de lo que hay en pantalla se puede comparar con
nada. Hay un test que lo fija.

Los campos hidráulicos conservan el rango automático: una carga en metros
no vive en 0–6, y ningún rango fijo serviría para dos modelos.

En el diálogo de Contour Options aparecen los dos botones de la referencia,
**«0 a 6»** y **«Ajustar a los resultados»**, y cambiar de campo escalar
recarga el rango propio de ese campo.

---

## 4 · Las superficies ya se pintan con su factor de seguridad

`SlipSurfaceItem` pintaba **verde fijo**. Una pantalla llena de *Minimum
Surfaces* decía solo «aquí hay superficies»; ahora dice de qué parte del
talud vienen los factores bajos, que es la razón de que el modo exista.
La crítica, la seleccionada y las consultadas conservan su color propio:
son la respuesta a «¿cuál es?», que es otra pregunta.

Y los tres modos del menú Data significaban otra cosa de la que dicen:

| Modo | Hacía | Hace |
|---|---|---|
| Global Minimum | la superficie crítica | igual, **más las dos líneas radiales** centro→extremos |
| Minimum Surfaces | `top_n(30)` global | la superficie de FS mínimo **de cada centro de la malla** |
| All Surfaces | 600, dibujadas de menor a mayor FS | **todas**, dibujadas **de mayor a menor** |

El orden de *All Surfaces* estaba invertido respecto a lo que documenta la
referencia, y no es un detalle estético: dibujando primero los factores más
bajos, **cada superficie posterior los tapaba**. Lo único que el lector
busca acababa debajo.

*Minimum Surfaces* no es un recuento sino una identidad, y así se comprueba:
ninguna de las superficies dibujadas comparte centro con otra, y cada una
es el mínimo del suyo.

---

## 5 · Add Query: una consulta es una superficie, no un par de números

`Add Query` pedía «x,y» en un cuadro modal y guardaba la tupla. Un par de
números no se puede dibujar, ni dovelar, ni graficar: **todas las demás
entradas del menú Query —Show Slices, Query Slice Data, Graph Query, Line
of Thrust— se quedaban sin nada sobre lo que trabajar**. Lo que una
consulta tiene que identificar es la superficie.

Ahora:

- Al activarlo, el cursor entra en modo selección y la barra de estado lo
  dice. **Esc sale** (un modo de selección sin salida es una trampa en un
  modelo donde no haya nada lo bastante cerca).
- Al pasar por encima —sobre la malla de centros decide el centro más
  próximo; en cualquier otro sitio, la superficie más próxima— se resalta
  la superficie y aparece una etiqueta flotante con el formato de la
  referencia, espaciado incluido: `FS =1.588 r =13.519 c=(68.000,34.500)`.
  Es lo que el usuario compara contra la otra pantalla.
- Al pulsar, la consulta queda fijada, **en negro y con sus líneas
  radiales**.
- **«Text during Query»** era una casilla conectada a nada; ahora gobierna
  esa etiqueta. **«Query Invalid Surfaces»** abría un resumen (que sigue
  disponible, en el menú Data, que es donde encaja); ahora es el
  interruptor que muestra el código de error de los centros sin superficie
  válida, que es para lo que sirve.
- Cualquier opción que necesite una consulta y no encuentre ninguna crea la
  del mínimo global, como documenta la referencia, en vez de negarse.

La etiqueta es un item de la escena, no un diálogo: un cuadro modal no
puede seguir al cursor, y este proyecto los prohíbe en cualquier camino que
un test vaya a ejecutar. Por lo mismo, `Graph Query` está partido en dos —
elegir qué graficar es una pregunta modal, graficarlo no.

### Nota sobre los centros

La resolución de un clic a una superficie se deduce del **resultado**, no
de los ajustes de búsqueda del proyecto. Los ajustes pueden haber cambiado
desde que se calculó —el usuario edita la malla y no recalcula— y entonces
el clic se resolvería contra una malla de la que no salió ni uno de los
números que hay en pantalla.

---

## 6 · Filter Surfaces, que guardaba el filtro y nadie lo leía

Se abría el diálogo, se calculaba `self._fos_filter`, se anunciaba «filtro
activo» en la barra de estado… y **ningún código leía el atributo**. Se
seguían dibujando todas las superficies.

Ahora filtra de las tres formas que documenta la referencia —rango de factor
de seguridad, las N más bajas, y **«Surfaces with error code»**—, se aplica a
*Minimum* y a *All*, tiene *Apply* que refresca sin cerrar, y *Cancel*
deshace lo que *Apply* hizo. **El mínimo global nunca se filtra**: un filtro
es una forma de mirar el resultado, no de esconder su respuesta.

«Surfaces with error code» no es un filtro más sino una vista aparte: enseña
**solo** las superficies no válidas del código elegido, en morado, con las
válidas ocultas, porque la pregunta que se hace ahí es «qué ha fallado
aquí», no «cómo se compara esto». Con un límite que conviene decir en voz
alta: un círculo rechazado **antes** de dovelarse —sin dos cortes con el
terreno, o curvatura inversa con la casilla quitada— no llega a
`evaluations`, así que ni se cuenta ni se puede dibujar. El resumen lo
advierte en lugar de dar un total que parece completo y no lo es.

---

## 6 bis · Graph SF Along Slope: era una línea horizontal

Merece su apartado porque no era una opción incompleta, era una opción que
respondía a otra pregunta. Usaba **solo la superficie crítica** y le daba a
cada dovela el factor de seguridad global — con el comentario escrito en el
código: *«very coarse: treat every slice with the global FoS»*. Lo que eso
dibuja es una recta horizontal: un número, repetido.

Para lo que sirve la opción, según la referencia, es para ver **en qué parte
del talud afloran los factores bajos** y poder dirigir allí la búsqueda. Así
que usa **todas** las superficies válidas y toma los **dos puntos de corte
con el terreno** de cada una, representando su factor de seguridad en cada
uno. Con las opciones documentadas: corte izquierdo y/o derecho, y «mínimo
por intervalo» con número de intervalos frente a «todos los datos».

El mínimo global sobrevive al agrupado por intervalos —hay un test que lo
exige—, porque es justo el valor que se busca en esa gráfica.

---

## 7 bis · Había dos leyendas, y no decían lo mismo

Se vio al renderizar la ventana para compararla con las capturas. El panel
*Summary* llevaba desde v0.1.8 una tabla de colores escrita a mano —rojo
≤ 1,00, naranja 1,00–1,25 … gris > 3,00— copiada de una función de color que
el lienzo ya no usa. Dos leyendas para un mismo gráfico, contradiciéndose:
la de verdad en el panel izquierdo, y ésta afirmando que el mapa de calor
significaba otra cosa. Eliminada. Una leyenda que no se genera a partir del
mapeo que explica acaba siempre diciendo eso.

---

## 7 · Auditoría de los menús Data y Query

- **Ninguna** de las cadenas de `Data` y `Query` pasaba por `tr()`
  (regla 2). Envueltas las 68, con terminología geotécnica castellana:
  *dovela*, *superficie de rotura*, *grieta de tracción*, *línea de
  empujes*, *consulta*.
- **Export Raw Data** apuntaba al CSV de dovelas, que es otro export. Ahora
  es lo que define la referencia: una fila por **superficie** —centro,
  radio, los dos puntos de corte con el talud y el factor de seguridad, **o
  un código de error negativo en su lugar**—, con *Copiar* y *Guardar*. Las
  filas con código de error son justo las que explican un hueco en blanco
  en la malla contorneada; quitarlas sería tirar la mitad del export.
  El CSV de dovelas sigue estando, con su nombre.
- **Show Line of Thrust** estaba siempre habilitada. La línea de empujes es
  el lugar geométrico de las resultantes entre dovelas, así que solo existe
  para los métodos que **resuelven** esas fuerzas: Spencer,
  GLE/Morgenstern-Price, Lowe-Karafiath y Corps of Engineers. Bishop, Janbu
  y Fellenius las suponen. Dibujarla ahí es enseñar una curva calculada a
  partir de una hipótesis. Deshabilitada, con el motivo en el tooltip, y se
  desmarca sola al cambiar a un método que no la produce.

---

## Sobre el ejemplo del usuario

El `PGR_Slip2D_Ej_1_General.ogr` usa una malla distinta de la del modelo de
referencia: **24–120 × 40–140 con 12×12**, frente a **40–120 × 30–120 con
20×20**. Por eso su Interpret decía 0,896 y la referencia 0,883. **No es un
fallo del motor**: con la malla de la referencia salen 0,884517 en el mismo
centro. Queda escrito para no volver a confundirlo.

---

## Lo que NO se ha tocado

- La comprobación m-alpha **sigue desactivada por defecto**.
- `Composite Surfaces`, `Minimum Elevation` y `Minimum Depth` no se han
  auditado. Están en los ajustes y no entraban en el encargo, pero **merecen
  exactamente la misma revisión que la curvatura inversa**: si tampoco los
  lee nadie, es la misma violación de la regla 7.

---

## Tests

Tres archivos nuevos y dos reescritos:

- `test_reverse_curvature_v182.py` (11) — geometría de la grieta, los dos
  FS de referencia, las dos ramas de la casilla, y la regresión de que el
  mínimo global no se mueve.
- `test_slide_legend_v182.py` (14) — los 24 colores medidos, el indexado
  por banda, la etiqueta «6.000+», la política de rango por campo y que la
  pluma de cada superficie es el color de su factor de seguridad.
- `test_interpret_query_v182.py` (13) — que el filtro filtra, que el mínimo
  global sobrevive a cualquier filtro, los códigos de error del export
  bruto y la disponibilidad de la línea de empujes por método.
- `test_checks_v132.py` — dos tests fijaban el comportamiento espejado.
  Reescritos con el diagnóstico correcto, más uno nuevo que comprueba,
  dovela a dovela, que `base_m_alphas` reproduce el `m_alpha` que usó el
  solver.
- `test_project_settings_wiring_v174.py` — el mismo espejismo, escrito por
  segunda vez y en otro archivo: `test_it_rejects_the_reference_validated_
  circle`. Que la creencia estuviera fijada en dos sitios es justo lo que
  la hacía parecer comprobada.
- `test_interpret_v112.py` / `test_interpret_i3_v153.py` — fijaban
  `top_n(30)` y las consultas como tuplas `(x, y)`. Reescritos sobre el
  significado documentado.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later

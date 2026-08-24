# OGR Slip2D v0.1.111

**Superficies compuestas: la opción existía, se guardaba y se imprimía en el
informe, y hacía lo contrario de lo que promete. No es que no recortara el
arco — es que, al dejar de rechazarlo, lo analizaba entero, con treinta
dovelas apoyadas cinco pies por debajo del modelo. Y lo que decidió el
diseño no fue la geometría: fue el eje de momentos.**

El encargo describía la anomalía **A22-1** (defecto **D15** del banco). Sus
medidas eran de **0.1.97**, así que lo primero fue volver a tomarlas en
0.1.110. Se reproducían enteras, dígito a dígito.

---

## 1 · Qué estaba mal

`ogr_slip2d/search.py`, en `_candidate_surfaces`:

```python
if not composite and leaves_soil_region(trial, ext_verts, ...):
    continue
```

La opción sólo servía para **saltarse el rechazo**. El *docstring* del propio
método decía lo contrario —*«that option exists precisely so such a circle
follows the boundary instead of being rejected by it»*— y esa frase es
probablemente la razón de que el defecto sobreviviera a dos lecturas: el
comentario describía la intención con tanta claridad que se leía como una
descripción del código.

Medido en **0.1.110** sobre el círculo que publica el problema 22 —Fredlund
y Krahn (1977), (120 · 90) R 80, 30 dovelas, la casilla ACTIVADA—:

| | 0.1.110 | publicado |
|---|---|---|
| cota mínima del arco | **10,0000** (= `centre_y − radius`) | fondo del modelo **15** |
| dovelas apoyadas en la capa débil | **2 de 30** | debería recorrerla casi entera |
| Ordinary / Fellenius | 1,841189 | 1,300 (Slide) · 1,288 (F&K) |
| **Bishop simplificado** | **1,980572** | 1,382 · 1,377 → **+43,3 %** |
| Spencer | 1,978251 | 1,382 · 1,373 |
| GLE / M-P | 1,979216 | 1,372 · 1,370 |

La capa débil de este problema —1 pie de espesor, c′ = 0, φ′ = 10°, apoyada
en el fondo del modelo— es todo el problema. El arco sin recortar pasaba por
debajo de ella.

---

## 2 · El camino equivocado, y es el que más enseña

La primera forma de escribir esto es obvia: `CompositeSurface` hereda de
`SlipCircle`, hereda con ella el centro, el radio y todos los `isinstance`
del proyecto, y sólo se sobrescribe `base_y_at`.

**Habría sido un error, y bastante caro.** Los cuatro métodos de momentos
—Bishop, Ordinary, Spencer y GLE— despachan por
`isinstance(surface, SlipCircle)` a la **fórmula circular pura**, la que
divide el radio de todos los términos porque *todas* las normales de base
apuntan al centro. En los tramos rectos de una compuesta no apuntan: la
normal tiene un brazo propio, y su momento es el término **Σ N·f** de la
formulación general de **Fredlund y Krahn (1977)** — precisamente el término
que ese artículo introduce para poder resolver superficies compuestas.

De modo que una compuesta **no** es un `SlipCircle`: es una superficie con
centro que se resuelve por el **balance general de momentos alrededor de ese
centro**. `moment_balance.moment_terms` ya lo calculaba como producto
vectorial desde v0.1.92; lo único que faltaba era que `moment_axis` le
entregara el centro.

Cuánto vale la diferencia, medido sobre la compuesta del problema 22
construida a mano, 40 dovelas, caso seco:

| Método | eje construido de polilínea | **eje = centro del círculo** | Slide |
|---|---|---|---|
| Ordinary | 1,295993 (−0,31 %) | **1,302984 (+0,23 %)** | 1,300 |
| **Bishop** | 1,356573 (**−1,84 %**) | **1,383143 (+0,08 %)** | 1,382 |
| Spencer | 1,383787 (+0,13 %) | **1,383329 (+0,10 %)** | 1,382 |
| GLE | 1,373804 (+0,13 %) | **1,373527 (+0,11 %)** | 1,372 |

El eje que el programa construye para una superficie sin centro cae en
(142,28 · 152,89), a 68 pies del centro real. Con él, Bishop se queda a
−1,84 %: dentro de una tolerancia del 2 %, es decir, lo bastante bien como
para no levantar sospechas.

---

## 3 · Qué se ha hecho

### 3.1 · `max(arco, fondo)`, y por qué esa forma

La referencia describe **un** hundimiento: la superficie se adapta al
contorno *«between the two circle intersection points along the lower edge»*.
Un techo de roca no está obligado a cortarse dos veces, así que la regla
implementada es, en cada abscisa,

```
base_y(x) = max(arco(x), fondo(x))
```

Coincide exactamente con lo documentado cuando hay un solo hundimiento y
generaliza sin casos particulares. Y no es una comodidad de escritura: dice
la mecánica. El fondo restringe la superficie **por abajo y en ningún otro
sentido**, así que donde el arco vuelve a estar dentro del terreno el arco
es la superficie.

El caso que separa las dos lecturas es una **zanja** en el sustrato. Leído
al pie de la letra —seguir el contorno del primer corte al último—, la
superficie bajaría por una pared de la zanja, recorrería su fondo y subiría
por la otra, añadiendo profundidad y longitud que nada exige. Con `max` pasa
por encima, que es lo que hace una superficie de rotura: un agujero en el
sustrato no es un sitio por el que la masa tenga que ir.

### 3.2 · Piezas

| Archivo | Qué |
|---|---|
| `ogr_core/geometry/ground.py` | `bedrock_surface()`, la envolvente **inferior** del contorno externo, gemela de `ground_surface()` y memoizada igual |
| `ogr_slip2d/surface.py` | `CompositeSurface` y `compose_with_bedrock()`; `moment_axis()` y `lowest_elevation()` aprenden la compuesta |
| `ogr_slip2d/search.py` | `_candidate_surfaces` recorta en vez de rechazar cuando la opción está activa |
| `ogr_slip2d/slicer.py` | la compuesta va por la rama de círculo; `kinks()`/`y_span()` en vez de `isinstance`; guarda de tramo coincidente |
| `ogr_gui`, `ogr_core/dxf`, `ogr_core/project` | dibujo, DXF, interpretación y HDF5 |

`compose_with_bedrock` devuelve **el círculo tal cual** cuando el arco no
baja del fondo. No es una optimización: es lo que garantiza que ningún
modelo sin superficies que se salgan pueda moverse un dígito.

### 3.3 · El troceador deja de preguntar de qué clase es la superficie

`_slice_boundaries` resolvía dos preguntas por su cuenta —dónde se quiebra la
superficie y hasta dónde llega en y— con un `isinstance` y una ojeada a
`.polyline`. Eso es una regla sobre dos geometrías escrita donde no se podía
ver una tercera. Ahora las dos preguntas se le hacen a la superficie
(`kinks()`, `y_span()`), y las tres clases las contestan.

**No es cosmético, y el problema 22 lo enseña.** Una compuesta no tiene
`.polyline`, así que por el camino viejo habría contestado el rango en y con
la envolvente de sus **dos extremos**: (20 · 60), para una superficie que
recorre y = 15. El contorno de material de la capa débil está en y = 16 —
fuera de ese rango—, se habría descartado por caja envolvente y habría dejado
de ser un corte obligatorio. **En silencio**, que es la peor forma de perder
una capa.

### 3.4 · Correr *a lo largo* de un contorno no es cruzarlo

`_surface_crossings` decide un corte por cambio de signo de
`g(x) = base_y(x) − línea_y(x)`, y una superficie que corre **sobre** el
contorno da `g = 0` en todas partes. La distinción es si el cero está
aislado: un cruce toca la línea en un punto, un tramo coincidente da ceros en
muestras consecutivas.

Las superficies compuestas hacen esto alcanzable en un modelo corriente —el
tutorial de la referencia lleva justo a esa geometría antes de pedir que se
borre el contorno—, y sin la distinción un tramo así emite ~8 cortes espurios
por segmento y la superficie se descarta entera por tener más cortes
obligatorios que dovelas, sin decir por qué.

### 3.5 · El brazo del peso se pide a un centro, no a una clase

`slice_surface` calculaba `weight_arm_ratio = (xc − centre_x)/R` sólo para un
`SlipCircle` y `sin(α)` para todo lo demás. El brazo de una fuerza vertical
respecto de un punto depende sólo de su abscisa, así que la primera forma es
la verdadera en **cualquier** superficie con centro, tramos rectos incluidos.
La compuesta no usa ese campo —va por el balance general— pero dejarle
escrito un número que no es el brazo de nada es sembrar la próxima confusión.

---

## 4 · Hallazgos colaterales

### 4.1 · Dos de las tres casillas «Composite Surfaces» no se leían nunca

`grid_dialogs.py` construye la casilla en **tres** paneles —Grid, Slope
Search y Auto Refine— y `apply()` escribía el ajuste **siempre desde la de
Grid**. Marcarla en Slope Search o en Auto Refine no hacía nada, y además
quedaba pisada por lo que mostrase la página de Grid, que el usuario no
estaba viendo. Lo mismo con *Create tension crack for reverse curvature*, que
aparece en dos.

Constaba como pendiente abierto desde **v0.1.78** (punto 3 de aquel
changelog). Mientras la opción no hacía nada, daba igual; ahora no.

Arreglado como se arregló el mismo problema en v0.1.104 para las casillas de
*Optimize Surfaces*: las vistas de un mismo ajuste se mantienen en paso **en
el momento del clic**, de modo que `apply()` tiene un solo valor que escribir
y ninguna regla que equivocar. (v0.1.104 probó antes la otra vía —un OR sobre
las tres— y como las tres arrancan del mismo valor guardado, el OR devolvía
la marca que el usuario acababa de quitar.)

### 4.2 · El rótulo decía «Material Boundary»

La casilla de Grid se rotulaba *«Composite Surfaces (slip surface follows a
Material Boundary)»*, y no es lo que hace: la superficie sigue el **borde
inferior del contorno externo**, que es donde se dibuja un techo de roca.
Inofensivo mientras la opción no hacía nada.

### 4.3 · El retroanálisis no puede con una compuesta, y ahora lo dice

`required_force` escribe Bishop en su forma circular —todas las normales al
centro, todos los brazos R—, que en el tramo recto de una compuesta no vale, y
por eso devolvía `None` en vez de un número plausible. Eso está bien; que lo
hiciera **en silencio** no. Con la opción activada, el retroanálisis habría
informado de una fuerza gobernante sacada de una población que él mismo había
encogido sin decirlo.

Ahora las cuenta y las declara en `notes`. **No se ha inventado la fórmula
para el caso recto**: la regla del proyecto es que una ecuación plausible pero
incorrecta es el peor resultado posible, así que queda como carencia dicha en
voz alta y no como número.

---

## 5 · Validación

`tests/test_composite_surfaces_v1111.py`, **23 comprobaciones**, contra
**Fredlund y Krahn (1977)** —la fuente original del problema— y no contra el
número de ningún programa.

Sobre el círculo que publica el artículo, generando la compuesta el programa
solo, 30 dovelas y la tolerancia de convergencia **de la clase** (0,001), que
es la que usa el test:

| Método | **OGR 0.1.111** | F&K (1977) | Δ | Slide | Δ |
|---|---|---|---|---|---|
| Ordinary / Fellenius | 1,298914 | 1,288 | +0,85 % | 1,300 | −0,08 % |
| Bishop simplificado | 1,381389 | 1,377 | +0,32 % | 1,382 | −0,04 % |
| Spencer | 1,380828 | 1,373 | +0,57 % | 1,382 | −0,08 % |
| GLE / M-P | 1,371297 | 1,370 | +0,09 % | 1,372 | −0,05 % |

Caso 2, Ru = 0,25:

| Método | **OGR 0.1.111** | F&K (1977) | Δ | Slide | Δ |
|---|---|---|---|---|---|
| Ordinary / Fellenius | 1,120843 | 1,029 | +8,93 %\* | 1,121 | −0,01 % |
| Bishop simplificado | 1,122862 | 1,124 | −0,10 % | 1,124 | −0,10 % |
| Spencer | 1,123333 | 1,118 | +0,48 % | 1,124 | −0,06 % |
| GLE / M-P | 1,113747 | 1,118 | −0,38 % | 1,114 | −0,02 % |

Con la tolerancia **del proyecto** (0,005 — la discrepancia que salió al
cerrar D12) los mismos cuatro dan 1,298914 / 1,380905 / 1,380080 / 1,370754 en
seco: ≤ 0,05 % de diferencia, sin cambiar ningún veredicto.

\* **la única exclusión del test, y está documentada**: hay dos
formulaciones clásicas de cómo entra `u` en el equilibrio de momentos de
Fellenius, F&K usaron una y los programas modernos la otra. Se midió por
separado en el problema 21 —el mismo talud sin capa débil—, donde el caso
seco coincide al 0,1 % y sólo el de Ru se separa. Afirmar la discrepancia
congelaría una diferencia de formulación en un test; afirmar la coincidencia
fallaría por algo que no tiene que ver con superficies compuestas. El caso
seco lleva los cuatro métodos; el de Ru, los tres que comparten formulación.

Lo demás que sujeta el test, y nada de ello es una captura de lo que el
código imprime:

- **la geometría es aritmética cerrada**: el arco corta la cota `y_f` en
  `xc ± √(R² − (yc − y_f)²)`, y ahí es donde la compuesta tiene que cambiar
  de rama, al último bit;
- **la contención** es una afirmación sobre el modelo: ninguna parte de la
  superficie analizada puede quedar por debajo del fondo;
- **regla 7 en los dos sentidos**: con la opción apagada ese mismo círculo se
  **descarta** (que es la rama OFF de la referencia, la que su diálogo dibuja
  junto al rótulo *Invalid Surface*), y un círculo que no sale del terreno da
  el **mismo número dígito a dígito** con la opción encendida y apagada;
- **el corte de la capa débil**: las dos abscisas donde el arco corta y = 16
  tienen que ser **límites de dovela**, y ninguna base de dovela puede
  atravesar la capa por su interior;
- **el eje de momentos** es el centro, y un eje puesto por el usuario **no**
  lo sobrescribe — la misma regla por la que un círculo ya ignora *Add Axis*;
- **la respuesta no cuelga del número de dovelas**: 30 y 60 coinciden al
  0,5 %;
- **la zanja**: cuatro cruces del fondo, la superficie lo sigue a los dos
  lados y pasa por encima del hueco sobre su propio arco, y sus **seis**
  quiebres son cortes obligatorios — los dos labios de la zanja sí, las dos
  esquinas del fondo no, porque ahí la superficie es el arco.

---

## 6 · Lo que la búsqueda del problema 22 dice ahora, y lo que no dice

Con la corrección, la rejilla del problema 22 pasa de un mínimo de **1,6691**
(Bishop) a **1,3412**. El publicado es 1,382, así que el mínimo de la
búsqueda queda un **−2,9 %** por debajo.

**No es un error, y conviene decir por qué.** El manual **no publica
rejilla** para este problema: sus tres tablas son *«Composite Circular»* sobre
el círculo que da el enunciado. Comparar el mínimo de una rejilla contra un
círculo dado a mano mide el paso de la rejilla tanto como el motor. La
superficie que OGR encuentra —centro (117 · 78), R 71,54— es una compuesta
perfectamente sana que recorre **67,8 pies** de capa débil frente a los 55,7
del círculo publicado, con 20 de 30 dovelas apoyadas en ella y `min m_alpha`
= 0,584: un mecanismo genuinamente más crítico que la rejilla del enunciado
no contenía. Es la misma lección que la ficha del problema 57 ya tenía
escrita —*un mínimo de rejilla no es un mínimo*—, aquí en el sentido
conservador.

La comparación limpia de este problema es, y era, **sobre el círculo
publicado**.

---

## 7 · Los otros dos problemas que usan la opción

El encargo pedía comprobar que **no se mueven**. Uno no se mueve; el otro sí,
y tenía que hacerlo.

### El 61 no se mueve — los ocho números idénticos

Sus dos modelos llevan `composite_surfaces = False`, así que sus **507
círculos** que bajan del fondo (de 16 250) los sigue rechazando
`leaves_soil_region` igual que antes. Curva de potencia y Mohr-Coulomb, cuatro
métodos cada uno: **idénticos al último dígito** frente a la corrida de
0.1.107. Que el subtítulo del manual diga *composite surfaces* es cosa de los
modelos del banco, no del código.

### El 57 sí se mueve, y reproduce una tabla que estaba PENDIENTE

Su `modelo_compuesto.ogr` lleva la opción activada y **1181 de sus 3366
círculos** bajan del fondo (y = 85). Ese caso era, además, la *segunda*
evidencia del defecto y la más limpia, porque era aritmética: hasta 0.1.110 la
corrida con la opción daba en los cinco métodos **los mismos seis decimales**
que la búsqueda circular sin ella.

| Método | 0.1.97 | **0.1.111** | Slide 57.2 | Δ antes | **Δ ahora** |
|---|---|---|---|---|---|
| Spencer | 1,434281 | **1,402793** | 1,400 | +2,4 % | **+0,20 %** |
| Bishop simplificado | 1,435256 | **1,396624** | 1,392 | +3,1 % | **+0,33 %** |
| Janbu simplificado | 1,292247 | **1,226413** | 1,222 | +5,7 % | **+0,36 %** |
| Lowe-Karafiath | 1,362138 | **1,275431** | 1,385 | −1,7 % | **−7,9 %** |
| Fellenius | 1,351607 | **1,264083** | 1,257 | +7,5 % | **+0,56 %** |

Cuatro de cinco pasan a **dentro del ±0,6 %**. El quinto empeora, y no es
casualidad: es **A55-1 / D20** —Lowe-Karafiath se desvía por el lado
conservador en cuanto hay nivel freático, y este problema lo tiene—. La
compuesta es más profunda y recorre más estrato duro, así que expone más el
mismo defecto. **No se ha tocado nada de Lowe-Karafiath**: queda como
evidencia adicional, con el signo que ya tenía.

El círculo publicado del 57 **no se ve afectado**: (36,451 · 201,910) R
116,891 toca el fondo en y = 85,019, diecinueve milésimas por encima de él.

## 8 · Qué se probó

- `tests/test_composite_surfaces_v1111.py` — 23 en verde.
- **Suite completa sin filtrar**: 136 archivos.
- Problema 22 del banco: círculo publicado (seco y Ru = 0,25) y búsqueda
  completa, más el contraste independiente de `superficie_compuesta.py` —la
  compuesta a mano coincide con la generada dentro del **+0,16 a +0,31 %**, y
  la de mano sale siempre más alta, que es lo que hace una poligonal de ocho
  cuerdas por arco—.
- Problema 57 con `modelo_compuesto.ogr` y problema 61 con sus dos modelos.
- `auditoria_invariantes.py` del banco: los siete ERROR que salen son los
  mismos de antes (modelos sin refuerzo o sin grieta declarada) y ninguno es
  del 22.

## 9 · Qué queda por probar

- **El `0,01` absoluto de `slicer.py`** con que se resuelve el material
  «inmediatamente por encima de la base». Es la regla que la referencia
  enuncia para los tramos rectos y funciona aquí (capa de 1 pie), pero la
  norma del proyecto pide tolerancias **relativas** al tamaño del modelo. Con
  una capa de 5 cm en un modelo métrico, ese desplazamiento se sale de la
  capa. No se ha tocado en esta versión porque moverlo mueve todos los casos
  validados; queda anotado como deuda con su medida pendiente.
- **La guarda de tramo coincidente** distingue el cero exacto. Un contorno
  *casi* coincidente —a 1e-9 del fondo— seguiría dando signos alternos y
  cortes espurios. No se ha visto en ningún modelo del banco.
- **Superficies compuestas en las búsquedas no circulares.** La referencia
  ofrece la casilla sólo para las circulares (Grid, Slope, Auto Refine) y así
  queda; una polilínea que se salga del modelo la sigue rechazando el
  troceador.

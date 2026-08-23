# OGR Slip2D v0.1.109

**La grieta de tracción por fin trunca la superficie: diez problemas del
banco que no salía ninguno, tres premisas del encargo que la medición
tumbó, y un residuo del problema 12 que no era la grieta sino un spline
mal citado desde v0.1.7.**

El encargo describía dos defectos medidos en **0.1.97**. Lo primero fue
volver a medirlos en 0.1.108: los dos seguían enteros, y la línea acusada
—`slicer.py:1019`— no había cambiado un carácter.

```python
if tc_boundaries and not project.tension_crack_properties.is_dry():
    result = _apply_tension_crack(project, result, tc_boundaries[0])
```

---

## 1 · Qué hacía mal, y por qué se notaba tan poco

Dos defectos en una guarda:

1. **Con la grieta seca no se hacía nada.** Ni empuje —correcto, no hay
   agua— ni truncado, que es la otra mitad del modelo y la mitad que
   funciona sin agua. Seis de los diez problemas del banco con grieta la
   tienen seca.
2. **Con la grieta llena tampoco se truncaba.** El *docstring* de
   `_apply_tension_crack` afirmaba desde v0.1.7 que la dovela superior se
   trunca en la pared vertical de la grieta. No se truncaba: `x_right`
   seguía siendo la intersección con el terreno.

El arco corría más allá de la grieta hasta cortar el terreno, y cada metro
de ese arco de más aportaba resistencia al corte sobre un plano que no
puede aportar ninguna. **Siempre del lado inseguro.**

Lo que lo mantenía escondido es que la grieta se leía como «una fuerza de
agua» y no como «dónde acaba la superficie». Mientras la única salida fuera
un empuje, una grieta seca no tenía nada que decir.

---

## 2 · Qué dice la referencia, leído antes de escribir nada

| Pregunta | Respuesta | Dónde |
|---|---|---|
| ¿Dónde acaba la superficie? | En la intersección con la **línea** de la grieta; de ahí una **pared vertical** sube al terreno | *«When a potential failure surface hits this line, it will ascend vertically to the ground surface»* |
| ¿Pesa la masa por encima? | **Sí**, y su cara vertical no resiste: *«…if the tension crack zone were dry, then the normal force on the side of the last slice would be zero»* | Tutorial de grietas, pág. 8 |
| ¿Y si no llega a la profundidad? | Superficie **inválida** — la referencia tiene código de error propio para «superficie enteramente dentro de la zona de grieta», uno circular y otro no circular | Resumen de códigos de error |
| ¿Y si la corta dos veces? | *«…it is only truncated to the first region from the crest»*, y sólo si *«the crest of a slip surface … is contained within the tension crack zone»* | Página de *Add Tension Crack*, con figura de los casos (a) y (b) |

La fórmula del empuje se cita por su fuente científica: Terzaghi (1943) para
½·γ_w·h_w² y su brazo en h_w/3, y Duncan y Wright (2005), capítulo 14, para
el modelo de arco corto con la cuña entera en el peso.

---

## 3 · Tres premisas del encargo que la medición corrigió

Esta es la parte que merece recordarse.

### 3.1 · No es «una zona sin resistencia al corte»

El encargo lo decía así, y es la lectura natural. Es falsa, y comprobarla
costó una medida:

En el problema 2, con el arco ya truncado, **5 de las 25 dovelas tienen su
base dentro de la zona de grieta** — por el lado del **pie**, donde el
terreno queda 3,87 m por encima de la línea. Con esas cinco resistiendo,
Bishop da **1,5956** contra un publicado **1,596**. Si se les quitara la
resistencia el número dejaría de cuadrar.

La grieta no es una zona blanda: es un **truncado en el extremo de
coronación**. El pie está en compresión y su suelo resiste. Haber
implementado la lectura natural habría cambiado un error inseguro por otro
excesivamente conservador, igual de equivocado y más difícil de detectar
porque va «del lado bueno».

### 3.2 · El aviso sobre el problema 12 estaba caducado

El encargo avisaba —con razón, en 0.1.97— de que el modelo del problema 12
declara `R2L` mientras su geometría dice lo contrario, y de que el arreglo
truncaría por el extremo equivocado. **D03d se cerró en 0.1.98** y ese
`modelo.ogr` dice `L2R`. La trampa ya no existía.

Pero el aviso llevaba dentro algo que sí importaba, y ver §4.

### 3.3 · Spencer del problema 12 ya no valía 1,288

El encargo daba Bishop 1,288 y Spencer 1,288 para el problema 12. Que los
dos coincidieran hasta la milésima **era el defecto D10**, cerrado en
0.1.106: Spencer y GLE devolvían Bishop dígito a dígito. Hoy Spencer da
1,4242. Cualquier criterio de cierre escrito sobre aquel 1,288 habría
medido otra cosa.

---

## 4 · Quién decide qué extremo es la coronación: la geometría

`crest_is_on_the_right()` leía la dirección de rotura declarada, como
decidió v0.1.73. Ahora decide **la geometría** —el extremo cuya cota de
terreno es mayor— y la declaración queda para **romper el empate**.

No es un cambio de opinión, es un cambio de escala. En v0.1.73 el sentido
sólo elegía qué dovela recibía el empuje; ahora elige **qué mitad del arco
sobrevive**, hasta un 20 % en el problema 12, y siempre del lado inseguro
cuando se equivoca. Tres razones más:

- la ayuda de la referencia dice que la dirección de rotura **no afecta a
  las opciones de modelado**, y enuncia la regla de la grieta en términos
  del *crest of a slip surface*, que es una propiedad de la superficie y no
  del proyecto;
- `surface.py` ya hacía esto desde v0.1.82 para la curvatura inversa, y su
  propio docstring explica por qué: *«both ends are tested independently,
  so the treatment does not depend on the declared failure direction»*;
- D03d encontró **diecinueve** modelos del banco cuya declaración
  contradecía su terreno.

El empate no es hipotético —una grieta abierta en terreno horizontal deja
los dos extremos a la misma cota— y tiene su test.

---

## 5 · El empuje, sobre la pared que existe (A2-2)

El empuje horizontal del problema 2 salía **−73,46 kN en los tres casos
probados**: el círculo de Bishop, el de Janbu, y un círculo de R = 1,58 m
que ni siquiera llega a la base de la grieta. 73,46 = ½·9,81·3,87², la
profundidad **completa** de la grieta: la geometría del contorno, no la de
la superficie.

Ahora el empuje se calcula sobre la **pared que dejó el truncado**, y esto
se arregla solo: la pared nace *sobre* la línea de grieta, así que la
profundidad mojada es la real por construcción. Y una superficie sin pared
no recibe nada.

El círculo de 1,58 m —2,5 m² de suelo, 50 kN de peso, al que se le aplicaban
73,5 kN, más que su propio peso, y que la búsqueda de Bishop, Spencer y GLE
elegía como crítico con FoS 0,96 donde sin grieta da 9,67— **queda
descartado**: está entero dentro de la zona de grieta, no tiene plano de
corte sobre el que escribir un equilibrio, y contestarle un número sería
aritmética sobre un mecanismo que no existe. La búsqueda no estaba rota;
encontraba fielmente el mínimo de un campo mal calculado.

---

## 6 · Un rodeo que costó una corrida: dónde se aplica el truncado

La primera versión copió el patrón de `apply_reverse_curvature` y truncó
**sólo en la rama de resolución fresca** de `slice_surface`, con el
argumento de que unos extremos ya cacheados son unos extremos ya tratados.

El problema 2 funcionó a la primera. El **27 no truncaba nada**, y su
`pared` salía `None` con el corte perfectamente localizable en x = 155,42.

La razón: un par `(x_left, x_right)` cacheado **no es prueba de que nadie
lo haya truncado**. La búsqueda resuelve sus propias cuerdas y las entrega
resueltas; y cualquiera que elija una masa a mano —como hay que hacer en el
problema 27, cuyo círculo corta el terreno cuatro veces— entrega lo mismo.
El truncado se aplica ahora **siempre**, y la idempotencia sale gratis de
la condición documentada: la coronación tiene que estar *estrictamente por
encima* de la línea de grieta, y después de truncar está *sobre* ella.

Sigue habiendo un enganche en `BaseSearch._candidate_surfaces`, y no
sobra: ahí es donde se juzga la contención en el terreno, y hay que
juzgarla sobre la superficie tal como se va a analizar.

---

## 7 · Resultados

Círculos publicados del banco, con los métodos y el número de dovelas de
cada problema:

| | antes | ahora | publicado | error |
|---|---|---|---|---|
| **P2** bishop | 1,6192 | **1,5956** | 1,596 | **−0,02 %** |
| **P2** janbu corr. | 1,6459 | **1,4886** | 1,489 | **−0,03 %** |
| **P2** spencer | 1,6158 | **1,5916** | 1,592 | **−0,03 %** |
| **P2** gle | 1,6159 | **1,5923** | 1,592 | **+0,02 %** |
| **P2** bishop *en la búsqueda* | −39,9 % | **1,5958** | 1,596 | **−0,01 %** |
| **P27** grieta seca, bishop | 1,5693 | **1,5446** | 1,532 | +0,82 % |
| **P27** grieta seca, janbu c. | 1,6025 | **1,5569** | 1,544 | +0,84 % |
| **P27** grieta seca, spencer | 1,5686 | **1,5436** | 1,532 | +0,76 % |
| **P27** grieta seca, gle | 1,5685 | **1,5437** | 1,532 | +0,76 % |
| **P27** grieta + 6 ft de agua, bishop | 1,5693 | **1,5238** | 1,511 | +0,85 % |
| **P12** bishop | 1,2912 | **1,0173** | 1,069 | −4,84 % |

Y la geometría, que es la prueba fuerte:

- **P2**: el arco sale en **53,7772** (publicado 53,776) con Bishop y en
  **50,9831** (publicado 50,982) con Janbu corregido;
- **P12**: el extremo izquierdo cae en **19,5706** (publicado 19,570), con
  una pared de 4,00 m exactos, que es la profundidad que rotula el manual;
- **P27**: la masa deja de llegar a x = 169,89 y termina en **155,4219**.

El **27 es la comprobación limpia**: su modelo *sin* grieta ya salía a
**+0,80 %** del publicado, y con grieta sale a **+0,82 %**. El truncado no
añade sesgo; reproduce el escalón entero de 1,396 a 1,532 que el manual
publica. Y deja de dar el mismo número con el contorno y sin él, que era el
otro criterio de cierre.

### El problema 12 no cierra, y la causa no es la grieta

Cumple su criterio **geométrico** exacto y se queda a −4,84 % en el factor.
El residuo es el **campo de presiones intersticiales**:

- su factor es extremadamente sensible a *u*: 1,0173 con `u`, 2,5765 con
  `u/2`, 4,1364 con `u = 0`. Un **1,7 %** de error en *u* explica el 4,8 %
  entero;
- se resuelve con una rejilla de 22 puntos interpolada por *thin-plate
  spline*, y **6 de las 30 dovelas** tienen la base fuera de la envolvente
  convexa de esos 22 puntos: son extrapolación pura.

Y ahí apareció el hallazgo del día. La implementación de OGR es correcta en
lo que dice ser —reproduce los 22 puntos con error 1e-12 y un campo plano
con 7e-15— pero **decía ser otra cosa**: su docstring atribuía
φ(r) = r²·ln r a *Franke (1985)*, y Franke (1985) se titula **«Thin plate
splines with tension»** y describe una superficie distinta, de base
ln(φr/2) + K₀(φr) + γₑ, que degenera en la clásica sólo cuando φ → 0. La
ayuda de la referencia habla literalmente de *una placa elástica infinita
bajo tensión*. Las dos bases coinciden dentro de la nube y divergen
**extrapolando**, que es exactamente donde caen esas seis dovelas.

La cita queda corregida a Harder y Desmarais (1972) / Duchon (1976), que es
de quien es. **El algoritmo no se ha tocado**: el parámetro de tensión φ no
está publicado, y elegirlo para que el problema 12 dé 1,069 sería ajustar al
resultado. Queda escrito en `docs/PENDIENTES.md` con las tres identidades
—exactitud en los datos, límite φ → 0, límite φ → ∞— contra las que habría
que validarlo si algún día se aborda.

---

## 8 · Qué se ha tocado

| Archivo | Qué |
|---|---|
| `ogr_slip2d/slicer.py` | `tension_crack_boundary`, `apply_tension_crack_truncation`, `_truncate_polyline_surface`; `slice_surface` trunca en todos los caminos; `_apply_tension_crack` reescrito sobre la pared |
| `ogr_slip2d/failure_direction.py` | `crest_end_is_on_the_right`: geometría primero, declaración para el empate |
| `ogr_slip2d/surface.py` | `tension_crack_wall` en `SlipCircle` y `SlipSurface`; `tension_cracks` y su serialización en la no circular |
| `ogr_slip2d/search.py` | truncado en `_candidate_surfaces`, antes de juzgar la contención |
| `ogr_core/hydraulic/water_pressure_grid.py` | la cita del spline |
| `docs/PENDIENTES.md` | el hallazgo del spline con tensión |

Superficies **no circulares** incluidas: cuatro de los modelos del banco con
grieta se resuelven con Path Search, y la referencia tiene código de error
propio para el caso no circular. La polilínea se recorta ella misma, así que
`x_range()` sigue siendo la única fuente de verdad y el dibujo y el número
describen la misma masa.

---

## 9 · Tests

Nuevo: **`tests/test_tension_crack_truncation_v1109.py`**, 20 tests. Los
dos más fuertes no necesitan ningún número publicado:

1. **Forma cerrada φ = 0.** En un talud homogéneo sin rozamiento el
   equilibrio de momentos da `F = c·L_arco·R / M` exactamente. Con grieta,
   `L_arco` es el arco **truncado** y `M` el momento motor de la masa
   **entera, cuña incluida**, así que una sola identidad sujeta el truncado
   y el peso a la vez: quitar la cuña sube el factor, no truncar lo baja, y
   sólo el par correcto pasa. Los dos lados se calculan en el test por
   cuadratura de Simpson sobre la geometría, nunca con las dovelas bajo
   prueba. Converge como O(1/n²): +0,042 % con 40 dovelas, +0,0026 % con
   160, +0,0002 % con 640.
2. **Identidad geométrica.** El extremo cae sobre la línea de grieta y no
   sobre el terreno, comprobado contra el contorno del propio modelo.

Y además: regla 7 con grieta **seca** (poner y quitar el contorno da números
distintos); que el suelo de la zona de grieta del lado del **pie** conserva
su resistencia; que se trunca por el corte más próximo a la coronación
cuando hay dos; que una superficie entera dentro de la zona se descarta **y
no aparece como crítica de una búsqueda**; que dos paredes de altura
distinta dan empujes en razón de sus cuadrados; que una polilínea trunca
igual y que volver a rebanarla no la corta otra vez.

Ancla publicada: **ACADS 1(b)** (Giam y Donald, 1989, árbitro 1,65), con la
profundidad de grieta de Rankine `2c/(γ√Ka)` [Craig 1997] calculada y no
escrita a mano. Tolerancia del 5 % y razonada en el docstring: es una
propiedad de la fuente, no de este código.

### Tests existentes revisados, no domados

- **`test_failure_direction_v173.py`** — la clase
  `TestTheCrackTruncatesTheUpSlopeEnd` fijaba la decisión de v0.1.73 que §4
  revierte. Reescrita entera con el invariante nuevo, y con la lección
  invertida: donde antes se comprobaba que las dos declaraciones eligen
  extremos opuestos, ahora se comprueba que **una declaración que
  contradice el terreno ya no mueve el arco**, y que la declaración sigue
  rompiendo el empate cuando lo hay.
- Su fixture tenía la zona de grieta empezando en x = 3 con la superficie
  saliendo a x = 2,12: **la coronación quedaba fuera de la zona por nueve
  décimas de metro**. Es la misma trampa que su propio docstring advierte y
  que v0.1.61 ya había encontrado una vez. Corregida a x = 0.
- **`test_tension_crack.py`** — idéntico: la zona llegaba a x = 84 y el arco
  sale en 84,64. Corregida a 90.

Ninguna de las dos correcciones afloja un test: las dos hacen que vuelvan a
medir lo que sus nombres dicen.

---

## 10 · Qué se ha probado

- La suite entera, sin filtrar.
- Banco: problemas **2** (círculo publicado y **búsqueda**), **12** y **27**
  en sus tres escenarios; los tres criterios de cierre de D13 salvo el
  factor del 12, con causa nombrada y medida.
- **No se ha movido nada de lo que ya estaba bien**: problemas 1, 18 y 23
  dan el mismo número **hasta el último dígito**. El 78 sí difiere de su
  `resultados.json`, pero ese archivo es de 0.1.100 y la diferencia está en
  Spencer y GLE, que es exactamente la firma de D10 (cerrado en 0.1.106);
  su Bishop coincide dígito a dígito.

## 10 bis · Los otros siete modelos con grieta, de pasada

No entraban en el encargo, pero se corrieron los diez para ver que ninguno
revienta. Ninguno lo hace, y salieron dos cosas que conviene anotar:

**El 52 sale idéntico bit a bit con y sin el contorno en Path Search**, y
eso **no** es un fallo. Su zona de grieta tiene **1,015 m** de profundidad y
cubre sólo x ∈ [27,97 · 50], la coronación llana; las superficies que Path
Search encuentra salen todas en **x ≈ 9,5**, a media cara del talud, con la
coronación fuera de la zona. Es el caso (b) de la figura de la referencia:
no se trunca, y no se debe truncar. En su modelo de **rejilla** la misma
grieta sí trunca —pared en x = 41,149, de 1,015 m— y mueve el número un
0,2 %, que es lo que un metro de grieta puede mover.

Comprobado con un A/B en el mismo proceso, misma semilla y misma población,
poniendo y quitando el contorno; el problema **39**, con la misma búsqueda,
sí se mueve: 1,0146 sin grieta y **0,9732** con ella.

**Y de paso, el riesgo que había que descartar**: el truncado de una
superficie no circular la modifica **en el sitio**. Path Search construye un
`SlipSurface` nuevo por cada candidata, con su `Polyline` nueva —igual que
Block Search, Simulated Annealing y `optimize.py`—, así que no hay ningún
objeto que se reutilice entre candidatas y no hay estado que corromper. El
A/B lo confirma por el otro lado: sin grieta, los mismos 409 válidos de
60 000.

## 11 · Qué falta por probar

- La **revalidación completa del banco**: los catorce modelos con grieta,
  la comparativa global, las fichas y el cierre formal de D13 y D14 en
  `ERRORES_Y_DISCREPANCIAS.md`. Queda como tarea siguiente.
- Si los problemas **60 y 73** se pueden reabrir. El 60 está omitido
  literalmente por este defecto; el 73 no tiene modelo construido. El 30
  **no** depende de esto (lo omite el arrancamiento del geosintético).
- Los problemas **56, 57 y 64** necesitan que se les construya el contorno
  de grieta que hoy no tienen: se les omitió porque no habría hecho nada.
- El spline con tensión, si se decide abordarlo.
- Sin mirar, a propósito (regla 6): `checks.py` exime del chequeo de
  tracción al 5 % superior de dovelas *«porque son, en realidad, la zona de
  grieta de tracción»*. Con un truncado de verdad esa excusa se debilita,
  pero medirlo es otra tarea.

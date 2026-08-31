# OGR Slip2D v0.1.138

**Defecto D40.** El convenio sobre el que descansa toda la formulación del
refuerzo —`head` es el extremo del **paramento** y `tail` el del **anclaje**—
no se comprobaba en ningún sitio. Ahora el análisis avisa cuando la cabeza de
un refuerzo cae del lado **estable** de la superficie que reporta.

Es un **aviso, no un rechazo**, y **no mueve ningún número**. La geometría no
es ilegal: un bulón anclado dentro de la masa deslizante es un diseño real,
sólo que malo. Lo que no podía seguir pasando es que pasara en silencio.

---

## 1. Por qué el error no se delata solo

Tres cosas distintas leen el convenio, y ninguna lo verificaba:

| lo que lee el convenio | dónde |
|---|---|
| la longitud de arrancamiento `L_i`, medida **desde la cabeza** | `GroutedTieback.capacity_modes`, `SoilNail.capacity_modes` |
| la longitud de adherencia `L_o`, medida **desde la cola** | las mismas |
| la fuerza apuntada **cabeza → cola** (`parallel_to_support`, `bisector`) | `_support_force_angle`, desde v0.1.112 |

*Add Support* es «primer clic, segundo clic». Dibujar el bulón del otro lado
invierte **las tres a la vez**, y por eso el resultado no parece equivocado:
parece otro número, igual de plausible.

Medido sobre el problema 59 del banco, en el círculo que publica su figura
59.2 — el mismo anclaje, la misma superficie, sólo los dos extremos
intercambiados:

| | Bishop | Spencer |
|---|---|---|
| como está dibujado | 0,756987 | 0,764945 |
| extremos intercambiados | 0,407783 | 0,495522 |

**El signo del error depende de en qué sentido se equivoque el usuario, y el
aviso no lo presupone.** Si dibuja al revés un bulón que ancla al fondo, el
programa devuelve el número BAJO y el usuario lo nota. Si el bulón real ancla
del lado de la masa y el programa lo lee como si anclara al fondo, devuelve el
número ALTO — y esa es la mitad insegura, la que nadie vuelve a cuestionar.

## 2. Los números del encargo estaban obsoletos, y el motivo importa

El encargo daba Bishop **1,14973 → 0,190454**, «un factor de 6,0», medido
sobre 0.1.127. Hoy son **0,756987 → 0,407783**, un factor de 1,86; Spencer, en
cambio, coincide dígito a dígito. Lo explica **v0.1.137**, que metió
`T_N·tanφ'` dentro de `m_α` en Bishop — justo el término que alimenta el
refuerzo. El defecto seguía intacto (el intercambio seguía siendo silencioso),
pero su titular llevaba una versión desactualizado. La ficha del banco además
se contradecía consigo misma: su titular decía 1,14973 → 0,190454 y su cuerpo
seguía diciendo 1,235779 → 0,314789.

Lección repetida, y ya van varias: **un defecto que se queda abierto arrastra
mediciones que caducan sin avisar.** El número que justifica una ficha hay que
volver a tomarlo antes de cerrarla, no leerlo de la ficha.

## 3. La comprobación depende de la SUPERFICIE, no del modelo

Un mismo bulón puede estar bien puesto para un círculo y al revés para otro,
así que esto no se puede validar al cargar el proyecto. La regla se evalúa
localmente, **en el punto de corte** y con la pendiente de la superficie allí:

```
side(P) = (P.y − iy) − pendiente·(P.x − ix)     # > 0 ⇒ encima ⇒ masa deslizante
```

Y no comparando `P.y` contra la cota de la superficie en `P.x`: **el extremo
anclado cae rutinariamente en una x que la superficie no alcanza** —la cola del
59 termina en x = 36,3 sobre una superficie que se acaba en x = 12,6— y ahí una
comparación de cotas no tiene nada que decir. En el 59:

| | side(cabeza) | side(cola) |
|---|---|---|
| como está dibujado | **+15,82** | −58,18 |
| intercambiados | **−58,18** | +15,82 |

Se avisa sólo con `side(cabeza) < 0` **y** `side(cola) > 0`.

Se pregunta **una vez por método, sobre la superficie crítica**, junto a
`daylight_tangent_note`, `m_alpha_margin_note` y `grid_edge_note`, y no dentro
de la búsqueda: `compute_support_effects` se llama miles de veces por corrida
y repetiría la misma frase. Reutiliza los tres primitivos que ya deciden dónde
corta el soporte —`_slip_polyline`, `_slip_tangent_at_x` e
`intersection_with_polyline`— por lo mismo que el diagrama de fuerzas de la
interfaz los reutiliza: para no dar una segunda opinión sobre dónde está la
superficie.

**Cuatro abstenciones**, cada una porque el aviso no tendría qué nombrar: un
soporte que no cruza (no aporta fuerza ninguna — eso es otro defecto, y este
aviso no puede empezar a reclamarlo), uno que cruza **más de una vez** (la del
apartado 3b), un corte fuera del rango rebanado, y un extremo que cae **sobre**
la superficie dentro de tolerancia. La tolerancia es
`1e-6 · longitud del soporte`, relativa por la regla del proyecto: una
tolerancia absoluta no se comporta igual en milímetros que en metros.

## 3b. Y esa regla, tal cual, estuvo mal una tarde: el problema 85

La primera versión leía **el primer corte** y comparaba los dos extremos contra
la tangente de ahí. Pasó la suite entera y los 34 modelos del banco menos uno:
el **85**, donde marcó como invertido un tirante que está **bien dibujado** —su
cabeza, (20 · 20), cae exactamente sobre la línea del paramento, de (15 · 10) a
(25 · 30)—.

La causa: la superficie crítica que Bishop reporta en el 85 es una lente somera
en la coronación, centro (42,556 · 32,722) y R 12,806, que baja sólo hasta
y = 19,92. El tirante es **horizontal a y = 20**, así que la **cruza dos veces**,
en x = 41,10 y x = 44,02. Con dos cortes **los dos extremos están fuera de la
masa deslizante**: el bulón es una cuerda que atraviesa la masa, no un anclaje
que llega más allá de ella. `intersection_with_polyline` devuelve sólo el
primero, así que la regla prolongaba una tangente **más allá de un segundo
corte** y contestaba con seguridad sobre un lado que no había mirado.

**La premisa sobre la que descansaba toda la regla —un corte, un extremo a cada
lado— no se estaba comprobando.** Es exactamente la lección de D16/D41 otra
vez: un razonamiento local que parece obvio, y un caso publicado que lo tumba.
Con el corte único garantizado la aritmética pasa a ser exacta —el tramo del
corte a cada extremo es recto y no puede volver a cruzar esa tangente—, así que
la corrección **no fue cambiar la fórmula sino añadir la guarda que faltaba**.

Hizo falta contar cortes, y contar es otra pregunta que localizar: se añadió
`SupportInstance.intersections_with_polyline` —**todos** los cortes— y
`intersection_with_polyline` pasa a delegar en ella, para que la aritmética del
segmento siga viviendo en un solo sitio.

Con dos cortes el aviso **se abstiene**, que no es lo mismo que dar el bulón por
bueno: no puede distinguirlo, y no debe fingir que sí. El test
`TestTheFirstCrossingIsNotEnoughOnItsOwn` vuelve a ejecutar la aritmética vieja
y comprueba que sigue dando la respuesta equivocada, para que volver a ella no
pueda pasar en silencio.

## 4. Dispara para todos los tipos, también donde no cambia nada

Un pilote `MEASURED_FROM_TOP` con `tangent_to_slip` (problemas 54 y 106) o un
`user_defined` con `horizontal` (85 y 86) dan el mismo factor dibujados al
derecho o al revés: ni la capacidad ni la dirección leen el eje. Aun así el
aviso sale. El convenio está documentado para **todos** los tipos, el `.ogr`
está mal dibujado igual, y la orientación es un ajuste que el usuario puede
cambiar después — una excepción por tipo habría que mantenerla en paralelo con
la tabla de tipos, y se quedaría obsoleta en cuanto alguien añadiera uno.
Por eso la frase enuncia el **hecho geométrico** y no promete un efecto.

## 5. El aviso nace sin un solo positivo, y eso es lo que se quería

**35 modelos re-corridos** (los 19 problemas con refuerzo: 30, 31, 47, 48, 54,
59, 60, 85, 86, 87–94, 106 y 111) y comparados contra la instantánea previa al
cambio: el aviso dispara **cero veces**, ningún factor de seguridad se mueve, y
`COMPARATIVA_Slide2_vs_OGR.md` sale **idéntica**. Es la comprobación que
importaba: un aviso que salta en modelos correctos enseña al lector a saltarse
los avisos.

Un apunte sobre cómo se comprobó, porque la primera manera **no valía**. Antes
de escribir nada se midió que en las **254 instancias** de esos 34 modelos toda
cabeza está al menos tan cerca del contorno externo como su cola, y se dio por
hecho que eso predecía el aviso. No lo predice: aquello es una propiedad del
**modelo** y el aviso lo es de la **superficie**, y fue justo el 85 —limpio en
ese barrido— el que destapó el falso positivo del apartado 3b. Lo único que
contesta esta pregunta es correr el banco y diferenciar los resultados.

## 6. Lo que se ha dejado fuera a propósito

`compute_support_effects` tiene **cinco `continue` silenciosos**: un soporte
que no cruza la superficie, que cruza fuera de toda dovela, de tipo
desconocido, plano bajo `MEASURED_FROM_TOP`, o de capacidad nula, desaparece
sin dejar rastro. Es un defecto real y vecino, y es la razón por la que la
primera abstención de arriba está redactada como está — pero **no es D40**, y
se anota aparte en el banco en vez de colarlo en este cambio.

Tampoco se impide la geometría en *Add Support* ni se autocorrige: eso sería
exactamente suponer una de las dos direcciones, que es lo que el encargo
prohíbe.

---

## Archivos

| Archivo | Cambio |
|---|---|
| `ogr_core/support/support.py` | `intersections_with_polyline()` — todos los cortes; la de un corte delega |
| `ogr_slip2d/support_integration.py` | `reversed_support_notes()` y `_side_of_slip()` |
| `ogr_slip2d/analysis_runner.py` | importado, en `__all__`, y pedido sobre `crit` en `run_analysis` |
| `tests/test_support_reversed_v1138.py` | 15 tests, cinco clases: dispara / calla / no mueve nada / la cuerda del 85 / la trampa del corte único |

**Ninguna fórmula tocada**: lo añadido a `support.py` es una consulta geométrica, y la que ya existía delega en ella sin cambiar de respuesta.

## Verificación

- Suite entera: 168 archivos, sin fallos.
- `tests/test_support_reversed_v1138.py`: 15/15. Retirando el aviso —un
  `return []` al principio de la función— **fallan 5**, así que no es
  decorativo (regla 7).
- Banco: los 19 problemas con refuerzo re-corridos y comparados contra el
  snapshot previo. Ni un factor de seguridad se mueve, y la lista `avisos` de
  cada `resultados.json` sale idéntica.
- El barrido del problema 59 devuelve los mismos dos pares de números y el
  aviso **sólo** en el caso invertido.

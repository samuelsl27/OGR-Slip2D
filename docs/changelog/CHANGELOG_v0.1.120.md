# OGR Slip2D v0.1.120 — la resistencia sin drenar ya varía con la profundidad, y el método que no la leía llevaba once versiones sin leer nada

El registro tenía dieciocho modelos de resistencia y **ninguno** hacía
`cu = c_ref + Δc·z`. `Undrained` es una constante; `VerticalStressRatio` y
`SHANSEP` varían con σ′v, que no es lo mismo que la profundidad dentro de
una capa. Ese hueco —**F23-1** en el banco de verificación— dejaba fuera
seis problemas del manual y obligaba al único que sí estaba publicado a
aproximar su perfil con cuatro franjas horizontales.

Se cierra con tres modelos nuevos. Pero **lo que se encontró por el camino
vale más que lo que se escribió**: al quitar las franjas del problema 23,
Fellenius se desplomó de 1,3674 a 1,1710 contra un publicado de 1,370
mientras Bishop se movía un 0,3 %.

---

## 1 · Lo que había que implementar, leído y no supuesto

La página *Undrained* de la ayuda de la referencia describe **cuatro**
subtipos de cohesión sin drenar, todos con φ = 0. Las dos ecuaciones están
en `eq_undrained_depth.gif` y `eq_undrained_datum.gif`:

| Subtipo | Ley | Profundidad medida desde |
|---|---|---|
| Constant | `c = c` | — |
| F(Depth from Top of Layer) | `c = c_top + Δc·(y_top − y)` | techo de la capa **local a la dovela** |
| F(Depth from Horizontal Datum) | `c = c_datum + Δc·(y_datum − y)` | cota que fija el usuario |
| F(Distance to Slope) | `c = c_top + Δc·d` | distancia **real** al punto más cercano del talud |

Con el `Cutoff` marcado el valor es un **máximo**; y si la tasa es
**negativa**, ese mismo valor actúa de **mínimo**. La asimetría es del
enunciado y está implementada tal cual.

La ley lineal no se cita por el programa que la implementa: en una arcilla
normalmente consolidada `su/σ'v` es constante —**Skempton (1957)**, **Ladd
y Foott (1974)**— y σ′v crece linealmente con la profundidad bajo un
depósito llano. Los perfiles concretos que este trabajo reproduce son de
**Low (1989)**, **Duncan (2000)** y **Duncan y Wright (2005)**.

### Tres entradas del registro, no un selector

`undrained_depth_layer`, `undrained_depth_datum` y
`undrained_slope_distance`, con una base privada que guarda la fórmula y
la lógica del cutoff **en un solo sitio**. La referencia los anida bajo un
desplegable *Cohesion Type*; el registro de OGR es plano por construcción
—la lista del diálogo sale de `REGISTRY.all()` y el `.ogr` guarda un
`MODEL_ID`—, así que un modo que no fuera ninguna de las dos cosas habría
tenido que colarse por los dos sitios. **`undrained`, el modelo que usa
todo el banco, no se ha tocado.**

`cutoff_enabled` es un booleano y `PARAMETERS` sólo admite flotantes, así
que viaja al lado, por el mismo camino que `points` y `rules`.

## 2 · Dos campos nuevos en el rebanador, y uno de los dos sale gratis

`SliceContext` y `Slice` reciben `layer_top_y` y `slope_distance`.

**El techo de la capa ya estaba medido.** `_column_weight` corta la columna
en cada contorno de material y resuelve qué material ocupa cada banda —lo
hace desde v0.1.63 para pesar la dovela banda a banda—, así que devolver
dónde acaba la banda de abajo cuesta unas cuatro comparaciones de
identidad sobre trabajo ya pagado. Un corte de nivel freático parte una
banda sin cambiar el material, y por eso la comparación es por `id` y no
por límites.

**La distancia al talud no.** Es una pasada punto-polilínea por todo el
perfil del terreno, por dovela, en cada superficie de ensayo de una
búsqueda. Se pregunta **una vez por análisis** si algún material declara
`NEEDS_SLOPE_DISTANCE`, y sólo entonces se mide.

Los dos se leen en un único sitio, `BishopSimplified._local_c_phi`, por
donde pasan los nueve métodos, el postproceso, las comprobaciones, las
fuerzas interdovela y el retroanálisis. `soil_shear_strength_at` —el
arrancamiento por coeficiente de interacción— los mide por su cuenta, y
también sólo cuando el modelo del material los declara.

---

## 3 · EL HALLAZGO: Ordinary/Fellenius leía la resistencia sin contexto

`LEMMethod._shear_strength` llamaba a
`material.strength.shear_strength(σ)` **a secas**, sin `SliceContext`. Era
el único camino por el que Ordinary obtenía τ, y el único método que lo
usaba. Los otros ocho pasan por `_local_c_phi`.

Consecuencia: **Ordinary ignoraba los ocho modelos que dependen del
contexto** —SHANSEP, los cuatro anisótropos y los tres de profundidad de
esta versión— y contestaba con el respaldo sin contexto de cada uno:
SHANSEP toma σ′v = σ′ₙ, los anisótropos toman su dirección más débil, y un
perfil de profundidad toma el valor en su propia cota de referencia.

Medido sobre un círculo de un talud homogéneo, 50 dovelas, contra Bishop:

| modelo de resistencia | Ordinary | Bishop | Δ |
|---|---|---|---|
| `mohr_coulomb` c=20 φ=20 **(control)** | 1,3640 | 1,5343 | **−11,1 %** |
| `shansep` S=0,25 m=0,8 OCR=2 | 1,3726 | 1,7662 | **−22,3 %** |
| `anisotropic_linear` c1=5 c2=40 | 0,6101 | 1,3730 | **−55,6 %** |
| `undrained_depth_datum` 20 + 3·(30−y) | 0,2163 | 0,6724 | **−67,8 %** |

Fellenius es el conservador de la familia y el control dice cuánto: 11 %.
Lo que pasaba de ahí era la ley de resistencia sin leer.

**Y una segunda consecuencia que estaba escrita al revés en un changelog.**
La cohesión por succión se suma en `_local_c_phi`, y el changelog de
v0.1.28 afirma que así *«los siete métodos LEM la recogen sin tocar
ninguno»*. De Ordinary no era verdad: no pasaba por ahí.

**Es un defecto anterior a esta versión** —desde v0.1.15, cuando se añadió
el mecanismo de contexto— y ha sido invisible once versiones porque
ningún caso del banco combinaba Ordinary con un modelo con contexto. El
problema 23 lo hacía… con cuatro franjas de `undrained` constante, que no
necesitan contexto. Al quitar las franjas apareció.

Arreglado: los dos caminos de `ordinary.py` leen la envolvente por
`_local_c_phi`, como todos. `_shear_strength` se **borra** en vez de
arreglarse: una consulta de resistencia sin contexto colgando de la clase
base es una invitación a usarla, y en este programa hay exactamente una
forma correcta de leer una envolvente.

Después del arreglo, y con φ = 0 —donde Fellenius y Bishop son
literalmente la misma suma, porque m_α colapsa a cos α—:

| modelo | Ordinary | Bishop | Δ |
|---|---|---|---|
| `mohr_coulomb` (control, **sin cambio**) | 1,3640 | 1,5343 | −11,1 % |
| `shansep` | 1,7662 | 1,7662 | **+0,0 %** |
| `undrained_depth_datum` | 0,6724 | 0,6724 | **+0,0 %** |
| `anisotropic_linear` | 1,2415 | 1,3730 | −9,6 % |

Esa identidad —φ = 0 ⇒ Fellenius ≡ Bishop— es lo que fija el test, y no
un número guardado.

**Mohr-Coulomb no se mueve un dígito**, que es lo que protege a los cien y
pico casos del banco: para una envolvente recta la linealización es
exacta.

---

## 4 · La cohesión negativa: se midió antes de decidir, y la pregunta era otra

La recta del datum cruza el cero. En el problema 29 del manual —el único
de los seis cuyo material llega muy por encima de su propio datum— la ley
que declara su enunciado, `100 + 9,8·(−20 − y)`, vale **cero en
y = −9,796** y en la coronación, y = +22, daría **−311 psf**. La
documentación de la referencia no dice qué pasa ahí, y su `Cutoff`, con
tasa positiva, es un máximo: no protege ese lado.

Se implementó la ley **literal** —no se inventó un suelo— y se midió:

1. sobre la superficie publicada de Duncan (2000), **ninguna dovela**
   alcanza la zona negativa, y por poco: la última tiene su centro de base
   en y = −10,595, con cu = +7,8 psf;
2. en una rejilla de 3825 círculos, **cero** superficies con factor
   negativo, y el mínimo idéntico con y sin suelo;
3. un círculo puesto a propósito en el banco alto, con toda su base entre
   −177 y −307 psf de cohesión, da **0,0000 con las dos reglas**.

La causa de (3) es que **el suelo ya estaba, una capa más arriba y desde
mucho antes**: `_local_c_phi` hace `c = max(0.0, c)`. La resistencia
negativa nunca llega al equilibrio, y no había nada que añadir.

Lo que sí se añade es **un aviso**, porque callarlo sería peor: por encima
de esa cota el material tiene resistencia **cero**, y una búsqueda
encontraría allí superficies de factor cero y publicaría una como el
mínimo. El aviso nombra la cota y se mide contra la extensión **del
material**, no la del modelo: con el rango del modelo entero, el problema
84 quedaba a un pelo de avisar de un suelo que no existe, porque su perfil
más empinado se anula justo en la coronación del *terraplén* y el
*cimiento*, que es quien lleva ese perfil, acaba veinte pies más abajo.

---

## 5 · Un tercer defecto latente, de una línea

`StrengthModel.from_dict` buscaba un `from_dict` propio en
`model_cls.__dict__` **solo**. Un modelo que lo herede de una base
intermedia —que es exactamente lo que son los tres nuevos— contestaba
«no», y el respaldo habría descartado justo el estado que ese override
existe para llevar. La búsqueda ahora sube por el MRO y se detiene
**antes** de `StrengthModel`, que conserva la razón original de no usar
una consulta de atributo normal.

---

## 6 · Interfaz

- El gradiente se declara en **kPa/m**, que es la cantidad que el sistema
  imperial escribe psf/ft. Sin esa entrada en el mapa de unidades habría
  llegado sin convertir a un proyecto en pies —y los tres problemas de
  Duncan y Wright lo están.
- Una casilla **Cutoff** que habilita su propio valor: el número solo no
  puede codificar «apagado», porque cero es un mínimo legítimo cuando la
  tasa es negativa.
- Los tres modelos se suman a los que deshabilitan los *Water Parameters*,
  como manda la referencia: con φ = 0 y τ = c(z) no entra ninguna presión
  intersticial en la resistencia.
- Fórmula al lado del desplegable, y traducción al español de lo nuevo.
- El desembalse rápido los **rechaza con mensaje**, que es lo que ya hacía
  con cualquier envolvente que no sea lineal, y lo que dice la propia
  referencia de un material sin drenar por construcción. No hacía falta
  añadir nada; sí un test que lo fije.

---

## 7 · Tests

`tests/test_undrained_depth_v1120.py`, 43 casos. Lo que sujetan:

- **Identidad Δc = 0**: los tres modelos dan *exactamente* lo que
  `Undrained`, a nivel de modelo y a través de un factor de seguridad
  completo. Es la comprobación más barata que hay.
- **Identidad entre subtipos**: los dos que no tienen caso publicado se
  fijan con identidades analíticas. Sobre un techo de capa horizontal, la
  forma de capa es dígito a dígito la del datum; bajo terreno llano, la
  distancia al talud es dígito a dígito la profundidad. Y un tercer test
  comprueba que **bajo un paramento inclinado sí difieren**, para que las
  dos identidades no puedan cumplirse porque nadie mide nada.
- **Regla 7**: la tasa, el datum, el valor del cutoff y la casilla del
  cutoff mueven el número, cada uno por separado.
- **Asimetría del cutoff**, techo y suelo.
- **Serialización** con ida y vuelta por `.ogr`.
- **Validación externa (regla 1)**: los cuatro perfiles del problema 84 de
  Duncan y Wright (2005), cada uno sobre su círculo publicado. El perfil I
  es cz = 0 y por tanto **no ejercita el modelo nuevo**: es el control que
  dice si una discrepancia es la geometría o la resistencia.
- **Ordinary lee la envolvente como todos**, anclado en la identidad
  φ = 0 ⇒ Fellenius ≡ Bishop, más un guardián que comprueba que el número
  no es el respaldo sin contexto, más que Mohr-Coulomb no se mueve.
- **El aviso del perfil que se anula**, con su caso que avisa, su caso que
  calla y su caso que el cutoff silencia.

Suite completa en verde antes y después.

---

## 8 · Los seis problemas del manual de verificación

El banco vive fuera del repositorio, así que ningún commit lo recoge. Los
seis que F23-1 bloqueaba están construidos y corridos.

| # | qué comprueba | resultado |
|---|---|---|
| **84** | cuatro perfiles del mismo modelo, `cu = 300 + cz·z`, cada uno sobre **su** círculo publicado | **12 filas OK**, peor **0,53 %** |
| **83** | dos perfiles que cambian el **mecanismo**: somero con cu creciente, profundo con cu constante | **6 filas OK**, peor **0,73 %** |
| **23** | el mismo problema **sin** las cuatro franjas | Bishop **−0,03 %**, Fellenius **−0,02 %** — mejor que la escalera |
| **29** | el enunciado que nombra los tres parámetros del subtipo *datum* uno por uno | 3 OK, Janbu corregido **−1,49 %** |
| **30**, **31** | Cu top/bottom por capa, con geosintético | **modelables, no OK**: −27 % y −24 % |

**El criterio de cierre pedía el 2 % en el problema 84**, y sale a 0,53 %.

**El 23 sin franjas sale MEJOR que con ellas** sobre los círculos
publicados: Bishop pasa de +0,29 % a −0,03 %. La escalera se conserva en
`modelo_franjas.ogr`, que es la evidencia del hallazgo P084-COHERENCIA2 de
la auditoría —el banco resolvía el mismo hueco con dos criterios
opuestos— y el único modo de medir lo que costaba.

**El 83 perfil II nunca estuvo bloqueado** (P083-COHERENCIA1): `cu = 300`
constante es el modelo `undrained` de siempre, y se había omitido por
arrastre del perfil I.

**La superficie del 29 no está publicada como números**, sólo dibujada. Se
digitalizó extrayéndola por color y calibrando contra la caja del relleno
de la figura; los seis vértices rotulados que **no** entran en la
calibración caen sobre el contorno con un residuo máximo de **0,77 ft**.

### Y dos cosas que el 30 y el 31 dejan abiertas

**A30-2** — el terraplén tiene **dos caras** y una **sola** lámina. Sin
limitar la búsqueda, el mínimo se va a un deslizamiento somero de la cara
opuesta a la cabeza del refuerzo, y ahí la lámina **empeora** el factor:
sobre (22,0 · 14,2) R 9,23, **3,0796 sin refuerzo y 0,7104 con él**. No es
un fallo del cálculo —`_support_force_angle` documenta que
`PARALLEL_TO_SUPPORT` es el eje del refuerzo, cabeza → cola, y que «no
está orientado para resistir nada»—, pero **un geosintético es un elemento
de tracción y no puede empujar**. Los modelos del banco limitan la
búsqueda al mecanismo del enunciado (*Slope Limits*) para no mezclarlo con
lo que sí se venía a medir.

**A30-3** — el mínimo queda un 25 % por debajo, y **no es F23-1**: sobre un
círculo profundo como el que dibuja la figura, OGR da 1,8947 con refuerzo
y 1,3195 sin él, y el intervalo publicado —1,66 a 1,77— cae **entre los
dos**. La búsqueda encuentra otra superficie, más somera. Con las
coordenadas de los círculos A y B **ausentes del manual**, la discrepancia
no se puede repartir entre «calcula distinto sobre la misma superficie» y
«encuentra otra superficie».

### Una errata del propio manual

Tabla 29.2: para γ da media 100 pcf, desviación 3,3 y máximo absoluto
**109,9** —que es exactamente media + 3σ— y mínimo **99,1**, a 0,9 de la
media, cuando media − 3σ = **90,1**. Con la otra variable los límites sí
son simétricos. Queda transcrito tal cual y declarado en la ficha.

### La comparativa acepta escenarios circulares

Un problema tenía **una** tabla circular y tantas no circulares como
quisiera. El 84 publica **cuatro** y el 83 **dos**, una por perfil, cada
una con su propio modelo. Con una sola casilla, tres cuartas partes de lo
que el 84 publica se quedaban fuera sin que nada lo dijera —que es justo
lo que la auditoría le reprochó a su ficha—. `generar_comparativa.py`
acepta ahora un bloque `circular.escenarios` espejo del que ya existía; sin
él, los otros 109 problemas se comportan exactamente igual, y se comprobó
regenerando la tabla antes de tocar ninguna ficha.

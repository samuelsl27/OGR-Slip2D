# OGR Slip2D v0.1.126

**Optimización multimodal** — un talud rara vez tiene una sola región crítica,
y hasta esta versión el programa sólo sabía decir una.

Pero lo que más vale de esta versión son dos cosas que salieron por el camino y
que nadie buscaba. Una: **una superficie optimizada podía salirse del modelo**,
y fuera del modelo el suelo resulta ser el material más débil de la lista — un
16 % de error, hacia el lado inseguro. Otra: se midió un sesgo del 4 % en el eje de
momentos, se escribió el arreglo, y **la medición obligó a retirarlo**.

---

## Lo que se añade

1. **Búsqueda por enjambre de partículas**, con modo de un mínimo y modo de
   **varios**. La séptima búsqueda, y la primera de población: las seis
   anteriores devuelven un único mínimo y no dicen si existe otro mecanismo
   unos metros más allá, que es justo lo que hace falta para decidir dónde se
   refuerza.
2. **La superficie anisótropa**: una polilínea que orienta el buzamiento punto
   a punto, para anisotropía plegada. Hasta ahora los tres modelos anisótropos
   tenían un único ángulo global desde la horizontal.
3. **Dos acciones que llevaban existiendo sin hacer nada** pasan a hacer lo que
   dicen (abajo).

Es el hueco **D24** del banco de verificación (problemas 103 y 105).

## El eje de momentos: escrito, medido y retirado

Esto es un camino equivocado, y se registra entero porque es la mitad del valor
de la versión.

**El síntoma.** Una poligonal de N cuerdas inscrita en un arco **es** el arco
cuando N crece, así que su factor de seguridad tiene que converger al del arco.
No converge. Círculo profundo del problema 103, 200 dovelas:

| | Ordinary | Bishop | Spencer |
|---|---|---|---|
| **arco** | **1,3043** | **1,3043** | **1,3043** |
| 24 cuerdas | 1,2470 | 1,2490 | 1,3051 |
| 48 cuerdas | 1,2438 | 1,2497 | 1,3031 |
| **192 cuerdas** | **1,2427** | **1,2500** | 1,3032 |

Ordinary se queda en **−4,7 %** y Bishop en **−4,2 %**, y no mejoran entre 48 y
192 cuerdas: es un sesgo, no discretización.

**La causa, localizada.** `moment_axis` construye el eje de una poligonal desde
su cuerda, `midpoint + rot90`, que para esa superficie cae en
(137,672 · 120,486) frente al centro real (125,400 · 56,700): **65 m, más que
el propio radio**, y no se mueve al refinar porque sólo mira los dos extremos.
Con el eje puesto a mano en el centro, los tres métodos vuelven a 1,3043
exactamente. Sólo los métodos de **sólo momentos** pueden derivar: Spencer y
GLE cumplen también fuerzas, así que su respuesta no puede depender del punto.

**El arreglo, y por qué no se publica.** Se implementó el centro del círculo de
mejor ajuste (Kåsa 1976) y la identidad pasó a cumplirse en los nueve métodos.
Después vino la suite, y con ella la tabla de siete métodos que la referencia
publica para **dos superficies no circulares dibujadas a mano** — un análisis
determinista, sin búsqueda:

| | publicado | eje actual | mejor ajuste |
|---|---|---|---|
| Ej_1 Ordinary | 0,897423 | **0,89742** | 0,89407 (−0,37 %) |
| Ej_1 Bishop | 0,922931 | **0,92308** | 0,91866 (−0,46 %) |
| Ej_2 Ordinary | 1,36921 | **1,36921** | 1,38200 (+0,93 %) |
| Ej_2 Bishop | 1,42443 | **1,42318** | 1,46904 (+3,13 %) |

**Ordinary reproduce el valor publicado a seis cifras en las dos superficies**
con el eje actual, y es el método sin fuerzas interdovela tras las que
esconderse. La sospecha que motivó el cambio —que el `xc, yc` que la referencia
**imprime** para una superficie no circular fuese un valor de presentación y no
el eje que su motor usa— queda **refutada por medición**: es el eje.

Así que producción no cambia, el ajuste de Kåsa se **borra** en vez de quedarse
comentado, y lo que queda es el número: un método de sólo momentos sobre una
superficie sin centro de rotación arrastra **del orden de un 4 %** de holgura
según dónde se tomen los momentos. Es la magnitud de la anomalía del problema
41, donde un Path Search daba un mínimo por debajo de **todas** las referencias
publicadas. Anomalía **D47**, medida y cerrada sin cambio de código.

`tests/test_moment_axis_v1126.py` sujeta las dos mitades: el control positivo
—con el centro verdadero la identidad se cumple, luego rebanado, marco de base
y sumas de momentos son correctos— y la deriva del convenio en bandas, de modo
que mover el eje obliga a rehacer el contraste en vez de retocar un número.

## Un defecto que sale al correr el problema por el banco, y es el mayor

La superficie crítica que devolvió la corrida del 103 baja a **y = −4,83**, y
**la base del modelo está en y = 0**. El análisis la juzgaba **válida y
admisible**:

| | factor |
|---|---|
| tal cual, saliéndose del modelo | **1,0902** |
| la misma recortada a y ≥ 0 | **1,2676** |

Un **16 %**, hacia el lado inseguro. Y lo que lo hacía rentable: fuera de toda
región de material `Project.material_at` devuelve `None` y el respaldo del
dovelador entrega **el primer material del proyecto**, que aquí es el terraplén
a `c_u = 60 kPa`, **el más débil de los dos**. Al optimizador no sólo se le
permitía salirse del modelo: se le pagaba por hacerlo, con suelo inventado y
además flojo.

**La regla ya estaba escrita.** La referencia la documenta —«if a surface
extends past the lower limits of the External Boundary, the surface is
discarded», su código de error −103— y OGR la implementa desde v0.1.84 en
`leaves_soil_region`. La llamaba **un solo sitio**: el generador de círculos.
Una poligonal nunca pasaba por ahí, y **toda** superficie que produce una
optimización es una poligonal. Una regla puesta en una puerta y olvidada en la
otra, que es la forma de defecto que este proyecto lleva encontrando desde
v0.1.42.

Arreglado con `polyline_leaves_soil`, que compara contra la **envolvente
inferior** del contorno —no contra una cota— y en los vértices de la superficie
**y** en los de la propia envolvente, porque un tramo recto puede pasar por
debajo de una base que sube entre ellos. Tolerancia **relativa**. Una
superficie **tangente** al firme se conserva: la regla es «por debajo», no «al
nivel».

**Y NO explica el problema 41**, que era la primera sospecha y está medida y
descartada: sus dos superficies llegan a `y = 4,31` y `y = 3,95` sobre una base
en `y = 0`, así que no se salen de nada. Aquel mínimo por debajo de todas las
referencias publicadas sigue sin causa. Tampoco es D47, que afecta a Ordinary y
Bishop mientras que aquí el método es Spencer, inmune al punto de momentos: son
tres cosas distintas. Anomalía **D48**.

**Lo que no se toca**: `_material_at` sigue entregando el primer material del
proyecto fuera del modelo. Con el guardia delante ya no lo alcanza ninguna
superficie, pero el respaldo sigue ahi. Reportado, no arreglado.

## El enjambre

**La partícula es un círculo**, en la parametrización de Slope Search que ya
estaba validada: dónde aflora del lado del pie, dónde entra del lado de la
coronación, y la inclinación en el pie. Tres consecuencias, y las tres son la
razón de elegirla: el espacio es una caja con límites reales, así que «un radio
del 10 % de la extensión del espacio de búsqueda» significa algo sin inventar
ninguna dimensión; el círculo siempre aflora; y reutiliza una construcción
probada desde v0.1.17. La superficie no circular la produce después la
optimización, que es la misma división del trabajo que la referencia documenta.

Las dos formas de actualización son las que la referencia publica:

    S_{i+1} = S_i + V_i
    un mínimo:      V_i = rand1 (SG − S_i) + rand2 (SB − S_i)
    varios mínimos: V_i = rand1 (N1 − S_i) + rand2 (N2 − S_i)

con N1 y N2 las dos partículas vecinas más próximas. **Dónde se aparta de la
forma canónica se dice en el código**: no lleva término de inercia ni factor de
constricción, a diferencia de Kennedy y Eberhart (1995); lo que se reproduce es
el comportamiento documentado, no el mejor enjambre posible.

**Qué hace significativo a un mínimo.** El encargo pedía elegir entre distancia
entre superficies, diferencia de factor, o las dos. **La fuente lo decide**: un
radio en el espacio de búsqueda, 10 % por defecto, y la diferencia de factor no
interviene. El algoritmo es la identificación de semillas de especie de Li
(2004). Dos mecanismos con el mismo factor en zonas distintas del talud son dos
respuestas; el mismo mecanismo encontrado dos veces es una.

### Un hallazgo del enjambre: la ventana de ángulo escondía el mecanismo profundo

El enjambre estrena **ventana de ángulo propia y más ancha**, y no por gusto.
La de Slope Search llega hasta (β − 5)°, que presupone un círculo que sale
**por el pie**; el mecanismo profundo del problema 103 sale 19 m más allá,
sobre la explanada, y pide **+49,5°** donde β − 5 da **+21,6°**. Con la ventana
estrecha el enjambre devolvía **1,4167** contra los 1,3036 de la rejilla y **no
informaba de un solo mínimo profundo**: el mecanismo que el problema existe
para enseñar quedaba fuera del espacio de búsqueda.

Slope Search **sí** lo alcanza (1,3017, mejor que la rejilla), pero por su
etapa de refinamiento local, que perturba centro y radio directamente y se sale
de esa parametrización. Así que la ventana no es un defecto de Slope Search: es
una restricción escrita para otra búsqueda, que el enjambre no hereda. Y la
referencia no da a su enjambre ningún control de ángulo.

## La superficie anisótropa

La regla está documentada y **no es la de una superficie de agua**: el ángulo
se lee en el **punto más cercano** de la polilínea, no en el que queda encima.
Y cuando el punto más cercano es un **vértice** se usa el segmento **dibujado
primero**, no el promedio de los dos — la fuente dice explícitamente que no
promedia, a propósito. La consecuencia visible es que invertir el orden de los
vértices de una polilínea con un quiebro brusco puede cambiar el resultado, y
hay un test que lo demuestra en el factor de seguridad, no sólo en el ángulo:
promediar quedaría más limpio y sería otro modelo.

Lo sujeta una identidad: una superficie **recta** a α grados da exactamente lo
mismo que `bedding_angle = α` global, dígito a dígito, en los nueve métodos. Y
un material sin superficie asignada no se mueve un dígito.

Es entidad independiente —no se interseca, no define regiones, no llega al
mallador—, el mismo estatuto que la capa débil de v0.1.121.

## Dos acciones que no hacían nada

Encontradas construyendo lo anterior, porque son exactamente la maquinaria que
el modo multimodal necesitaba:

- **`Show GM Surfaces`** era una acción marcable cuyo slot **sólo escribía un
  mensaje en la barra de estado**. No dibujaba ninguna superficie y no ponía
  ninguna bandera que alguien leyera. Ahora dibuja.
- **`Pick GM Surfaces…`** abría un `QInputDialog` **modal** y **descartaba lo
  que el usuario elegía**. Dos defectos en cuatro líneas, y el modal es el más
  grave: este proyecto lo prohíbe en código que un test pueda ejecutar. Ahora
  la lista es **no modal** y elegir una fila selecciona la superficie.
- Las dos cadenas del menú **no pasaban por `tr()`**, aunque el título del
  diálogo sí tenía traducción.

Sirven a las dos fuentes de varios mínimos que hay: los del enjambre
multimodal y los de una corrida probabilística Overall Slope.

## Lo que se toca

| Archivo | Qué cambia |
|---|---|
| `ogr_slip2d/particle_swarm.py` | **nuevo** — enjambre uni/multimodal, especies por radio |
| `ogr_slip2d/search.py` | `SlopeFrame` y `slope_frame` extraídos de Slope Search; `SearchResult.minima`; optimización por mínimo, con el círculo discretizado sobre su propio arco |
| `ogr_slip2d/analysis_runner.py` | rama del enjambre; entra en las búsquedas optimizables |
| `ogr_slip2d/surface.py` | sólo docstring: la medición del eje y lo que el convenio cuesta |
| `ogr_core/geometry/anisotropic_surface.py` | **nuevo** — punto más cercano y regla del vértice |
| `ogr_core/geometry/boundary_type.py`, `transforms.py`, `dxf/*` | el contorno nuevo y sus enganches |
| `ogr_core/materials/*` | `anisotropic_surface_id`; el ángulo local en `SliceContext`; los tres modelos lo leen |
| `ogr_core/project/settings.py` | `PARTICLE_SWARM` y sus ajustes; `pso_enhanced` en Advanced, donde la referencia lo pone |
| `ogr_slip2d/slicer.py` | el ángulo de buzamiento local, resuelto una vez por análisis |
| `ogr_gui/**` | panel del enjambre, casilla avanzada, acción de menú, asignación en materiales, las dos acciones GM, dibujo de varios mínimos, traducciones |

## Lo que queda abierto, con su número

- **D47** — el 4 % del convenio del eje. Medido, sin cambio de código.
- **El problema 41 sigue sin causa.** Era la primera sospecha de D48 y está
  medido que no: sus superficies llegan a y = 4,31 y y = 3,95 sobre una base en
  y = 0, así que no se salen de nada.
- **La segunda mitad de D48**: `_material_at` sigue entregando el primer
  material del proyecto fuera del modelo.
- **El problema 103 SÍ cierra**, entero, y lo cerró D48:

  | ratio | OGR | publicado | Δ | mecanismo |
  |---|---|---|---|---|
  | 1,4 | 1,220131 | 1,215 profundo | **+0,42 %** | tangente al firme |
  | 1,5 | 1,301856 | 1,290 profundo | **+0,92 %** | tangente al firme |
  | 1,6 | 1,316528 | **1,315 somero** | **+0,12 %** | tangente a la cota del pie |

  Sin el guardia, el ratio 1,4 daba 1,0849: un **−10,7 %**. Y al ratio 1,6 el
  mínimo global es el **somero**, que la búsqueda unimodal del propio manual
  **no encuentra** —informa 1,366, un 3,9 % por encima—: es el argumento de la
  funcionalidad, medido sobre los números publicados.
- **El problema 105 sigue sin cerrar**, y ya no por falta de la superficie
  anisótropa: su geometría es la del Tutorial 32, que no está publicada ni en
  el manual ni en la documentación de referencia, y su figura no lleva ejes ni
  cotas. Reconstruirla midiendo píxeles daría un número que parece que
  funciona.
- **D22 sigue vivo** y esto no lo toca: sobre el mismo modelo, Simulated
  Annealing con optimización devuelve **1,3741** donde la rejilla circular da
  **1,3057**. Va en sentido contrario al eje, así que es generación de
  superficies y no evaluación.

## Fuentes

- Kennedy, J. y Eberhart, R. (1995). «Particle swarm optimization».
  *Proc. IEEE Int. Conf. on Neural Networks*, 1942-1948.
- Qu, B.Y., Suganthan, P.N. y Das, S. (2013). «A distance-based locally
  informed particle swarm model for multimodal optimization». *IEEE Trans.
  Evol. Comput.* **17**(3) 387-402.
- Li, X. (2004). «Adaptively choosing neighbourhood bests using species in a
  particle swarm optimizer for multimodal function optimization».
  *GECCO 2004*, LNCS **3102** 105-116.
- Cheng, Y.M., Li, L., Chi, S.-C. y Wei, W.B. (2007). «Performance studies on
  six heuristic global optimization methods in the location of critical slip
  surface». *Computers and Geotechnics* **34**(6) 462-484.
- Guo, S. y Griffiths, D.V. (2020). «Failure mechanisms in two-layer undrained
  slopes». *Canadian Geotechnical Journal* **57**(10) 1617-1621,
  doi 10.1139/cgj-2019-0642.
- Greco, V.R. (1996). «Efficient Monte Carlo technique for locating critical
  slip surface». *J. Geotech. Eng.* **122**(7) 517-525 — la optimización que ya
  estaba y que el enjambre reutiliza.
- Kåsa, I. (1976). «A circle fitting procedure and its error analysis».
  *IEEE Trans. Instrum. Meas.* **25**(1) 8-14 — usado en el camino que se
  retiró, citado aquí porque el camino se registra.

---

Suite entera: **2748 / 2748**, cero fallos, sin marca `FILTERED RUN`.
Comparativa del banco: **95 de 111** analizados (era 94), con el problema 103
en tres escenarios y los tres **OK**.

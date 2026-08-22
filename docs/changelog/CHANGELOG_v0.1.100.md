# OGR Slip2D v0.1.100 — una dovela perdida por un ulp, y el troceado que el manual llevaba usando desde siempre

Un círculo cuyo centro está a la cota de la coronación sale del terreno por su
propio extremo, `|x − x_c| = R`, con **tangente vertical**. No es una rareza: el
círculo crítico de Bishop del problema 23 del banco de verificación (Low 1989)
es exactamente eso. Ahí OGR descartaba **siempre una dovela, la última, en
silencio**, y el factor de seguridad salía un 25 % bajo con las 30 dovelas del
enunciado — subiendo al afinar, que es lo que hace que parezca convergencia.

Se cierra la anomalía **A23-1**.

Lo que se buscaba era un `m_alpha` degenerado. Lo que había era un **ulp**, y
detrás de él un segundo defecto que el primero llevaba tapando desde el
principio: **el troceado medía mal el arco**.

---

## 1 · La hipótesis que se desmintió

La ficha suponía que `m_alpha = cos α + sen α·tanφ/F` tendía a cero al acercarse
α a 90° con φ = 0, y que descartar esa dovela era una protección contra una
resistencia divergente. No es eso, y merece quedar escrito porque justificaba
mirar en el sitio equivocado:

- la cola de ese círculo está en el **Upper Soil**, que tiene **φ = 15°**, así
  que `m_alpha` tiende a `tanφ/F = 0,234`, no a cero;
- `checks.m_alpha_check` daba **min m_alpha = 0,258 > 0,20**, y el mínimo caía
  en la **dovela 0, en el pie**, sin relación ninguna con la tangente.

La comprobación de m-alpha no estaba fallando ni mintiendo: **no tiene
jurisdicción** sobre una dovela que no existe. Hacerla rechazar esta superficie
habría exigido subir el límite por encima de 0,26, y con él se habrían caído
superficies perfectamente legítimas. La lección es la de v0.1.82 otra vez, del
otro lado: no basta con que un diagnóstico esté bien calculado, tiene que estar
mirando la magnitud que falla.

## 2 · El mecanismo, que es aritmético

La salida del círculo es `x_c + R`. En coma flotante:

```
>>> 33.557 - 18.001
15.556000000000001          # R vale 15.556
```

Un ulp por encima del radio. `SlipCircle.base_y_at` calculaba
`disc = R² − dx² = −5.68e−14 < 0`, devolvía `None`, y `slice_surface` hacía
`continue`. Sin aviso, sin marca en el resultado, sin nada.

El error decae como **1/√n** porque el arco que falta escala como √w:

| n | dovelas | arco hasta | Bishop | error vs 1,192 |
|---|---|---|---|---|
| 30 | 29 | 32,614 | 0,89657 | −24,8 % |
| 80 | 79 | 33,180 | 1,05055 | −11,9 % |
| 320 | 319 | 33,467 | 1,11738 | −6,3 % |
| 640 | 639 | 33,512 | 1,12641 | −5,5 % |

√(2Rw) vale 5,42 m con n = 30 y 1,17 m con n = 640 —razón 4,6— y los déficits
van de 24,8 % a 5,5 % —razón 4,5—. La aritmética del fallo y la del arco que
falta son la misma.

**Hay un segundo disparador de la misma familia y no exige tangencia exacta.**
`candidate_chords` redondeaba las raíces a 6 decimales para que `set()` juntara
la que un vértice compartido produce dos veces. Seis decimales sobran en x y no
llegan en y: junto a una tangente casi vertical `dy/dx` ronda 1600, así que
5e−7 de x son 3,4e−4 de y — de sobra para saltarse la guarda **absoluta**
`tol = 1e-4` del troceador. Con el centro en (18,001; **16,010**) se pierde la
dovela igual: 0,9345 con 30 dovelas y 1,0703 con 120.

## 3 · Lo que el primer defecto tapaba: el arco medido con una secante

Con la dovela recuperada, `base_length = b/cos(α del punto medio)` sigue
**subestimando un arco casi vertical en 1/√2**, por fino que se trocee. Se ve
contra una **solución cerrada**: en un talud homogéneo φ = 0, el equilibrio de
momentos sobre un círculo da exactamente `F = c·L_arco·R / M`.

| n | tangente del punto medio | cuerda |
|---|---|---|
| 30 | −2,63 % | +1,41 % |
| 120 | −1,90 % | +0,20 % |
| 3840 | −0,37 % | +0,00 % |

`O(1/√n)` contra `O(1/n)`. Y la **cuerda** —ángulo y longitud del segmento recto
entre los dos extremos del arco— es además lo único que conserva exacta la
identidad `b = l·cos α` sobre la que Bishop (1955) y los otros ocho métodos
escriben su numerador. La formulación general no circular ya tomaba la cuerda
desde v0.1.92; ahora las dos describen la misma base.

## 4 · El 1,192, que sí era alcanzable

La cuerda no sólo acierta contra la solución cerrada. Sobre los **círculos
publicados del propio problema 23**, con las dovelas del propio enunciado:

| | publicado | OGR 0.1.99 | OGR 0.1.100 |
|---|---|---|---|
| Bishop, 25 dovelas | 1,192 | — | **1,19596** (+0,33 %) |
| Bishop, 30 dovelas | 1,192 | 0,89657 (−24,8 %) | **1,19543** (+0,29 %) |
| Ordinary, 25 dovelas | 1,370 | — | **1,36988** (−0,01 %) |
| Ordinary, 30 dovelas | 1,370 | 1,35977 (−0,75 %) | **1,36974** (−0,02 %) |

Dos métodos, dos círculos distintos, dentro del 0,35 % **a la vez**, y Ordinary
—que nunca perdió una dovela— también mejora, hasta quedarse en el −0,01 %. Eso
no es casualidad: el troceado de la referencia es de cuerda.

**Y su número no está convergido.** Con la cuerda, Bishop sobre ese círculo va

```
n =  30   1,19543
n =  60   1,16113
n = 120   1,15227
n = 240   1,14743
n = 960   1,14362
```

Ninguna discretización uniforme en x converge a 1,192; el límite ronda 1,15,
entre el **1,14 de Low (1989)** y el **1,17 de Kim (2002)**, los dos impresos en
el mismo manual al lado del 1,192. Sobre una superficie que sale con tangente
vertical el factor de seguridad **depende del número de dovelas**, y los valores
publicados para superficies así son ellos mismos valores a un número de dovelas.
Reproducir el publicado y ser independiente de n son incompatibles aquí; se ha
elegido reproducir el publicado, y **decirlo**.

## 5 · Descartado por el camino, con medida

Cuatro hipótesis que parecían razonables y no lo eran:

- **la escalera de Cu variable** (hueco F23-1, la capa inferior aproximada con
  4 franjas): de 4 a 32 franjas Bishop va 1,1430 → 1,1400, **hacia abajo**. No
  explica un +4 %;
- **un Upper Soil sin rozamiento** (Cu = 95, φ = 0, por si la tabla del manual
  estuviera mal leída): daría Bishop 1,36–1,40 y **rompería Ordinary**, que
  bajaría a 1,3197 (−3,7 %). La lectura φ = 15° es la buena;
- **el círculo en filo de navaja**: perturbando cy entre 15,9 y 16,5 y R entre
  15,4 y 15,7 el factor sólo se mueve entre 1,134 y 1,153. No hay redondeo del
  centro publicado que explique el 1,192;
- **la formulación**: Spencer sobre el mismo círculo daba 1,14028, es decir lo
  mismo que Bishop. Dos métodos independientes de acuerdo señalaban al troceado
  y no a las ecuaciones.

## 5 bis · Lo que la cuerda rompió, y por qué el arreglo era el correcto

La suite lo dijo enseguida, y con la voz de dos archivos distintos:
`test_ponded_water_v161.py` y `test_drawdown_bbar_v169.py` protegen la misma
propiedad —**sobre un talud ya sumergido, subir el agua no cambia nada**, porque
el peso añadido y el empuje añadido se cancelan— y los dos la exigían a seis
cifras. Con la cuerda pasó a cumplirse sólo en el límite:

| n | tangente del punto medio | cuerda |
|---|---|---|
| 50 | 9,7e−13 | 2,4e−04 |
| 200 | 9,9e−13 | 1,5e−05 |
| 800 | 1,0e−12 | 9,5e−07 |

La cancelación es telescópica y sólo cierra si el brazo del peso es el
verdadero. Con la tangente del punto medio lo era **por accidente**, porque en
un círculo `sen α_medio = (x_medio − x_c)/R` exactamente; con la cuerda deja de
serlo.

El arreglo no es aflojar el test: es dejar de escribir un **brazo** como el seno
de un **ángulo de base**. El momento motor de una carga vertical aplicada en `x`
sobre un círculo vale `W·(x − x_c)`, y punto; `W·R·sen α` era un atajo válido
sólo mientras α fuese la tangente en esa misma `x`. `Slice` lleva ahora
`weight_arm_ratio`, el brazo dividido por R —`(x_centro − x_c)/R` en un círculo,
`sen(base_angle)` en cualquier otra cosa, que es lo único que había antes—, y lo
usan los cuatro sitios donde el término es un momento: `bishop.py`,
`ordinary.py`, `spencer.py` y `gle.py`. En el lado de **fuerzas** de Spencer y
GLE sigue `sen α`, que allí es una dirección y no un brazo.

Con eso la cancelación vuelve a **1e−15**, y de paso el Ordinary del problema 23
mejora de −0,12 % a **−0,01 %** contra su valor publicado.

## 5 ter · Y lo que la invariante nueva encontró sola

`test_focus_optimize_m4_v155.py` empezó a fallar por una razón que merece
quedar escrita: la superficie de la que partía —el mínimo de una Path Search
sobre Ej_1, FoS 0,88281 en los vértices (44,24; 50) … (76,94; 25)— **estaba
troceada en DOCE dovelas de las catorce pedidas**. Dos perdidas en silencio, en
una superficie no circular, por el mismo mecanismo que esta versión cierra. Con
la invariante nueva esa superficie se rechaza y la búsqueda entrega otra, FoS
0,91075, con las catorce.

O sea que el defecto no era sólo de círculos con tangente vertical: se había
colado en el mínimo de una búsqueda no circular, donde nadie lo estaba mirando.
El test se ha reescrito para afirmar el contraste que documenta —densificar
compra más de un orden de magnitud— en vez de un «no mejora nada» que era una
propiedad de la superficie inválida, y se le ha añadido un caso que exige que la
superficie de partida esté entera.

## 5 quater · Y lo tercero que salió al levantar la piedra: una convergencia falsa

La suite tumbó también el caso de validación **ACADS 1(c)** (Giam y Donald,
1989), y por un tercio de razón distinto. Esperado 1,406; obtenido **0,9952**,
un −29 %.

El mínimo lo ganaba un círculo de la propia malla con el centro en el vértice
de coronación (50; 35) y R = 9,1818 — otra **salida a 90°** — cuyo factor de
seguridad es **5,5147**. Y lo publicaba como 0,9952, **convergido en UNA
iteración**:

```
F0 = 1,000  ->  0,995207        paso = 0,0048
tolerancia del modelo            = 0,0050      -> "convergido"
punto fijo real                  = 5,5147
```

El criterio de parada es un **paso entre dos iterados sucesivos**, y el valor
inicial **no es un iterado**: compararse con él mide la distancia al número que
eligió el programa, no la distancia a un punto fijo. Donde el mapa es lento
cerca de ese valor las dos cosas se confunden — y aquí se confundían por un
factor de cinco y medio. El argumento de contracción que justifica el criterio
(está escrito en `tests/test_convergence_tolerance_v198.py`) habla de
**iterados**; no dice nada del primer paso.

El primer paso ya no puede terminar la iteración, en los cinco sitios que paran
sobre un paso: `bishop.py` (las dos ramas), `janbu.py`, y los bucles interiores
en F de `spencer.py` y `gle.py`. Con eso ACADS 1(c) vuelve a **1,40832**, un
0,16 % de su valor publicado.

Este defecto no lo trajo esta versión: estaba desde siempre, y lo tapaba el
mismo troceador. Con la dovela perdida ese círculo daba `new_fos = −0,0169` en
el primer paso —no físico— y la superficie se descartaba entera. Un fallo
escondía al otro.

## 5 quinquies · La confirmación que vino de otro problema

El problema 78 del banco llevaba archivado un `dovelas_perdidas.json`: alguien
ya había medido allí que **el mínimo de la búsqueda lo ganaban superficies con
49 dovelas de las 50 pedidas**, y había apuntado a mano qué salía al excluirlas.
Es la misma anomalía, en otro modelo, sin tangente vertical publicada de por
medio.

La predicción era comprobable, y se cumple exacta:

| modelo 1a | registrado con degeneradas | registrado SIN ellas | 0.1.100 |
|---|---|---|---|
| Bishop | 1,061742 (49 dovelas) | 1,127038 | **1,127886, 50 dovelas** |
| Spencer | 1,061742 (49 dovelas) | 1,127038 | **1,127886, 50 dovelas** |
| Janbu simplificado | 1,044052 (49 dovelas) | 1,176515 | **1,176812, 50 dovelas** |

y en el mismo centro y radio —(104; 98) R 69,55849 y (104; 116) R 86,96319— que
la ficha había anotado. El arreglo llega solo a donde antes había que llegar
quitando superficies a mano.

Barrido de regresión sobre el resto del banco, todo sobre los mismos círculos y
sin volver a buscar: problema 27 **+0,03 %**, problema 39 **+0,12 %**,
problema 95 **≤ 0,022 %** en sus ocho métodos. Y el 23, que era el objetivo, con
la **búsqueda** —no sólo el círculo publicado— cayendo en 1,193782 para Bishop
(+0,15 %) y 1,367380 para Ordinary (−0,19 %), desde los 0,871040 y 0,928208 de
0.1.99.

## 6 · Qué se ha cambiado

**`ogr_slip2d/surface.py`**

- `SlipCircle.base_y_at` — `disc` negativo dentro del redondeo de `R²`
  (tolerancia **relativa**) se lee como cero en vez de como «fuera del círculo».
- `SlipCircle.base_angle_at` — devolvía **`0.0`, horizontal**, justo donde la
  tangente es **vertical**, y con un umbral **absoluto** `1e-12` contra la
  convención del proyecto. Ahora devuelve ±90° con la misma tolerancia relativa.
  Era código muerto mientras `base_y_at` cortaba antes; ya no lo es.
- `SlipCircle.candidate_chords` — fuera el `round(raíz, 6)`; los duplicados se
  funden con una tolerancia **relativa al radio**, que junta lo mismo sin gastar
  seis cifras de precisión donde más falta hacen.

**`ogr_slip2d/slicer.py`**

- **La base de una dovela es la CUERDA** entre sus dos extremos, no la tangente
  en su punto medio.
- En las dos fronteras **extremas** la base *es* el corte con el terreno por
  construcción, así que se recorta sin condición en vez de compararse con una
  tolerancia — que es justo lo que una tangente vertical derrota, porque
  allí un error en x llega multiplicado por `dy/dx`. Las fronteras interiores
  se juzgan con tolerancia **relativa**.
- **La invariante**: el troceador entrega **una dovela por intervalo, o `None`**.
  Los `continue` silenciosos son ahora abandono de la superficie. Un arco corto
  en silencio no es una respuesta más basta: es la respuesta a otra superficie.

**`ogr_slip2d/methods/` — bishop, ordinary, spencer, gle**

- El término motor de momentos toma su brazo de `Slice.weight_arm_ratio` y no
  de `sen(base_angle)`. Ver el apartado 5 bis.

**`ogr_slip2d/methods/` — bishop, janbu, spencer, gle**

- La comparación de parada no se hace en la primera pasada. Ver 5 quater.

**`ogr_slip2d/analysis_runner.py`**

- `daylight_tangent_note` — cuando la superficie crítica sale del terreno a más
  de 85° de la horizontal, la corrida **avisa** de que su factor depende del
  número de dovelas y dice con cuántas se calculó. Los 85° son un umbral de
  **aviso**, no una constante física, y salen del hueco entre las dos medidas
  del mismo modelo: 90,00° deriva un 3,9 % entre 30 y 240 dovelas, y 74,43°
  deriva un 0,26 %.

## 7 · Qué no se ha movido

Los casos validados, con sus 25 dovelas y sus círculos de referencia:

| caso | referencia | 0.1.100 | error |
|---|---|---|---|
| Ej_1 Bishop | 0,882889 | 0,882640 | −0,028 % |
| Ej_1 Janbu | 0,842548 | 0,842944 | +0,047 % |
| Ej_1 Spencer | 0,883036 | 0,882054 | −0,111 % |

contra tolerancias del 0,5 %. Lejos de una tangente vertical la cuerda y la
tangente del punto medio coinciden a unas pocas 1e−4.

Y el radio de daño de la invariante nueva, medido antes de escribirla: barriendo
4851 círculos sobre la malla de Ej_1 y otros 4851 sobre la del problema 23,
**ninguna** superficie perdía dovelas. El cambio convierte un número mal
calculado en silencio en un descarte, sin quitar ni una superficie de las que ya
sobrevivían.

## 8 · Tests

`tests/test_tangent_surface_v1100.py`, cuatro clases:

1. **La aritmética**, con los números de la anomalía: `base_y_at` del extremo del
   arco, la tangente de 90° y la precisión de la raíz. Sin modelo, sin
   tolerancias discutibles.
2. **Cobertura**: `len(slices) == n` exacto y el arco llegando a los dos cortes
   con el terreno, sobre una salida tangente y sobre una casi tangente.
3. **Anclaje externo** contra la forma cerrada φ = 0, dentro del 1 % con 120
   dovelas y con el error encogiendo al afinar. Es el que el código viejo no
   pasaba a ningún n razonable, y el que un test de convergencia n contra n
   **no** habría detectado — porque el código viejo era plano y un 2,6 % falso.
4. **Que la corrida lo diga**: el aviso sale sobre la superficie tangente y no
   sale sobre la que no lo es.

En `tests/test_convergence_tolerance_v198.py`, que es donde ya vivía la
invariante «dónde pares no puede decidir a qué convergiste», dos casos más:
que un mapa lento no se confunda con un punto fijo, y —dicho como invariante y
no como el número de un círculo— que **ningún método declare convergencia en su
primera pasada**.

En `tests/test_focus_optimize_m4_v155.py`, un caso nuevo que exige que la
superficie de partida esté troceada entera.

## 9 · Lo que queda abierto

- Sobre una superficie con salida tangente el factor sigue dependiendo de n con
  cualquier reparto uniforme en x. La cura sería un reparto **graduado** cerca de
  la tangente; se ha descartado a propósito porque llevaría el problema 23 a
  ~1,15 y perdería el acuerdo con el valor publicado. Queda anotado, no resuelto.
- Los métodos de **equilibrio de fuerzas** se portan mucho peor que Bishop sobre
  ese círculo: entre n = 30 y n = 480, Janbu simplificado va de 1,46 a 1,92 y
  Corps of Engineers #2 de 2,36 a 3,07. No se ha tocado aquí.

# OGR Slip2D v0.1.125

**Filtración transitoria acoplada** — el embalse se puede por fin decir dónde
está, y por el camino aparecen dos defectos que multiplicaban el factor de
seguridad por 3,7 y por 1,1, los dos en silencio y los dos hacia el lado
inseguro.

---

## Lo que se añade

Tres piezas, y sólo una de ellas es la que el encargo pedía.

1. **El embalse como condición de contorno geométrica.** Hasta esta versión una
   condición de filtración sólo se podía asignar a uno de **cuatro lados
   enteros**: izquierdo, derecho, inferior y *la superficie del terreno
   completa*. Con eso el enunciado del problema 102 —una presa con agua a un
   lado— **no era expresable**: poner «carga total = 24,41» en la superficie del
   terreno la habría puesto también sobre el coronamiento y sobre el talud de
   aguas abajo. Un embalse pasa a ser **un número y un lado**, y el perímetro
   mojado sale de la geometría; un desembalse es la misma orden con una cota
   menor.
2. **Un camino programático.** Mallar, resolver, escalonar y calcular el factor
   de cada etapa vivía entero dentro de `MainWindow`, así que ni un guion, ni la
   línea de órdenes, ni el banco de verificación podían analizar un desembalse.
   Se extrae a `ogr_slip2d.transient_stability`, que no contiene Qt, y la
   interfaz pasa a llamarla.
3. **El tope de presión intersticial negativa** que la referencia documenta y
   este programa no tenía.

Es el hueco **D30** del banco de verificación (problema 102).

## Lo que NO había que añadir

El encargo describía mal el hueco, y conviene dejarlo escrito porque casi todo
lo que enumeraba existía y estaba validado desde v0.1.30:

| Premisa del encargo | Qué mide el código |
|---|---|
| «un campo de filtración FEM **no se guarda** en el .ogr» | Falso desde v0.1.78: se escribe y se restaura recomponiendo los derivados por identidad cerrada |
| «lo que falta es el **acople**» | El acople existía: `FEM_SEEPAGE` interpola el campo T3 en la base de cada dovela, y la política de Fredlund llega a los nueve métodos por `_local_c_phi` |
| «el desembalse como **contorno móvil**» | La referencia tampoco lo hace continuo: su ayuda dice que las condiciones se definen **en cada etapa**. Es una escalera, igual que `TransientStage.bcs` |

Lo que faltaba no era la física. Era poder **enunciar** el problema y poder
**correrlo** desde fuera de la ventana.

---

## La geometría del 102 está publicada, y sus rótulos están redondeados

La ficha decía `confianza_geometria: "nula - sin vertices rotulados"` y el
encargo repetía que la geometría «no está rotulada». Las dos son falsas: la
figura 102.1 rotula los nueve vértices —la etiqueta del coronamiento se lee
«(100, 29), 29)» porque son **dos rótulos superpuestos**, (100, 29) y (107, 29),
cada uno con su línea guía— y seis figuras de resultados publican el círculo
crítico entero: centro, radio y los dos extremos.

**Y los rótulos están redondeados a enteros, que es la trampa.** Los seis
círculos tienen todos el extremo izquierdo en **y = 28,600** y el derecho en
**y = 7,300**, con x distinta cada uno. Sobre una cara inclinada una cota fija
obliga a una x fija; que varíe la x y no la y sólo cabe si esos extremos están
sobre **tramos horizontales**. El coronamiento está a 28,6 y la explanada de
aguas abajo a 7,3, donde los rótulos dicen 29 y 7.

No es una lectura: son dieciséis ecuaciones cerradas, y el peor residuo es
**1,4 mm**, que es exactamente el redondeo de los tres decimales publicados. Con
esa geometría el caso seco —que no lleva agua, así que mide la geometría y nada
más— sale a **+0,13 %**; con el coronamiento a 29, a −2,7 %.

Hay además un rótulo que la propia tabla desmiente: el pie dice 158, y un
extremo publicado en x = 157,908 con y = 7,300 ya tiene que estar sobre la
explanada, así que el pie está en 157,908 o antes. Leer el 158 al pie de la
letra pone ese extremo 4 cm por encima de donde el manual lo publica.

Es la misma lección del problema 108 con otro disfraz: allí un contacto que
parecía una recta no lo era; aquí un rótulo que parece un entero no lo es.

---

## Primer defecto: el embalse se extrapolaba a TODO el modelo

Con un análisis por elementos finitos el embalse no se dibuja, se **prescribe**:
hay agua embalsada allí donde la carga total aplicada al contorno supera la cota
del propio contorno. `_fea_level_at` interpolaba entre los nodos mojados y, fuera
de ellos, **devolvía el valor del extremo**.

En esta presa los nodos con carga prescrita acaban en x = 87, donde el paramento
alcanza la lámina. A partir de ahí la función respondía **24,41 hasta x = 191**:
diecisiete metros de agua embalsada sobre el talud de aguas abajo, y sobre la
explanada del pie, y sobre todo lo demás.

Medido sobre el círculo publicado del permanente inicial, Spencer:

| | φ_b = 0 | φ_b = 37 |
|---|---|---|
| con la regla anterior | **5,8262** | 6,0023 |
| con el arreglo | 1,7173 | 1,8008 |
| publicado | 1,745 | 1,815 |

**Un factor 3,4, en la dirección insegura y sin decir nada.**

El comentario que lo justificaba —«entre dos embalses a distinta cota esto es una
rampa, y da igual porque el terreno intermedio está por encima de los dos»— es
cierto para una presa con agua **a los dos lados** y falso en cuanto uno de ellos
es una cara de filtración, que es el caso corriente. Y lo que lo hace un defecto
y no una diferencia de criterio es que **la otra ruta ya contestaba bien**:
`interp_y_on_polyline` devuelve `None` fuera de su rango en x desde siempre. Las
superficies dibujadas y las prescritas contestaban distinto a la misma pregunta,
y la del FEM era la equivocada. Ahora los nodos mojados se agrupan en **tramos
contiguos del contorno** y el nivel no se extrapola fuera de un cuerpo de agua
ni se interpola entre dos.

### Y había un test defendiendo el defecto

`test_outside_the_wet_nodes_the_level_is_held`, escrito en v0.1.65, exigía
exactamente lo que había que quitar: que el nivel se **mantuviera** en su valor
de extremo para toda abscisa más allá del último nodo sumergido. Pasaba, y
pasaba con razón, porque la regla es **inofensiva mientras el terreno siga por
encima del agua más allá de la charca**, y en un talud simple siempre lo está.
Deja de serlo en cuanto el terreno vuelve a bajar en otro sitio, que es
exactamente lo que es una presa.

Se reescribe con la afirmación contraria y con **el caso que discrimina**, que
es el que faltaba: terreno que vuelve a bajar por debajo del agua prescrita.
Con la regla vieja aparecen trece metros de agua donde no se prescribió nada;
con el arreglo, cero. Un test que sólo mira el caso plano no podía distinguir
las dos reglas.

### La auditoría de los otros tres consumidores

Se miraron los cuatro sitios que leen el nivel embalsado. El peso sobre cada
dovela y la σ_v del modelo Ru heredan el arreglo. El Δσ_v del método B-bar
también, y ahí importaba el doble, porque es una **diferencia** de dos columnas
embalsadas y las dos estaban mal. **Y uno de los cuatro estaba bien y el apunte
de auditoría era mío y equivocado**: el lienzo *sí* dibuja el embalse prescrito
desde v0.1.65, y además hereda el arreglo, porque toma el nivel de la misma
función. Queda escrito como camino equivocado.

---

## Segundo defecto: la cara de filtración fabricaba su propia convergencia

La condición unilateral de una cara de filtración —«P = 0 **o** Q = 0, y nunca
agua entrando»— se resuelve conmutando nodos, y la conmutación oscila. Contra eso
había dos curas: dos bandas de histéresis y un **presupuesto por nodo**, tras el
cual el nodo se congela «para que el conjunto activo se asiente con seguridad».

El presupuesto valía **3**, y tres no es un salvavidas: es un tope que salta
durante la convergencia normal. Peor: un nodo congelado ya no puede mover el
conjunto activo, y *«el conjunto activo dejó de cambiar»* era el criterio de
convergencia. **Congelar fabricaba la convergencia que se estaba comprobando.**

Medido en esta presa: **47 de los 77 nodos** de la cara de salida congelados,
freática 4,5 m demasiado alta, factor **1,5818 (−9,35 %)** y `converged = True`.

Se arregla por los dos lados:

- el presupuesto sube a **25**, y eso no cuesta nada: con 10, con 40 y con 200 el
  resultado es **idéntico** (1,7174). El tope no compraba estabilidad, sólo daño;
- y sobre todo, la condición unilateral se comprueba ahora **sobre el estado
  final**, nodo a nodo, en vez de deducirse de cómo terminó el bucle. Si algo
  queda sin asentar se dice, se cuenta cuántos nodos se congelaron y
  `converged` pasa a `False`. Preguntarle a la respuesta y no al bucle es lo que
  impide que un tope vuelva a esconderse.

**Y no cuesta nada, medido como este proyecto exige que se mida.** A/B en el
mismo proceso, espalda con espalda, con la versión nueva de control a los dos
lados. Sobre el permanente los controles se separaron un 30 % entre sí, más que
el efecto, así que esa medida **no resuelve** y manda contar el trabajo añadido:
**29 → 33 iteraciones de Picard**, cuatro más, y las 29 anteriores daban la
respuesta equivocada. Sobre el transitorio —donde el conmutador actúa *dentro de
cada paso de tiempo* y por tanto podía multiplicar— la medida **sí** resuelve, y
dice que no hay efecto:

| Presupuesto | `test_transient_v130.py` |
|---|---|
| 25 (nuevo) | 108 s |
| 3 (anterior) | 109 s |
| 25 (control) | 108 s |

Los dos controles coinciden al segundo. Una primera corrida dio 151 s y estaba
contaminada: había otros procesos peleándose por los mismos núcleos, que es
exactamente el ruido autoinfligido contra el que avisa el contrato del proyecto.

**Y el hallazgo más útil salió de aquí.** Con el conmutador asentado, prescribir
una cola de aguas abajo a la cota 7,3 y dejar simplemente cara de filtración dan
**1,7173 y 1,7174**. Son la misma condición física y ahora se comportan como tal;
antes se separaban un 8 %. La cola de aguas abajo, que durante media tarde
pareció ser la causa del desajuste, era el síntoma.

---

## Tercer defecto: cada etapa llevaba el agua de otra

El factor de seguridad de una etapa transitoria se calculaba sustituyendo el
campo de presiones de esa etapa… y **sólo** el campo. El peso del agua embalsada
no sale del campo: sale de las **condiciones de contorno**, que son donde un
modelo de elementos finitos dice dónde está su embalse. Así que un desembalse
quitaba las presiones intersticiales del instante y **conservaba el peso del
embalse que acababa de vaciarse**.

Es el mismo defecto que v0.1.69 corrigió para la línea de desembalse dibujada,
reaparecido por el otro camino. Ahora una etapa instala las dos cosas y las
restaura al salir, aunque el análisis levante por el medio.

---

## Un quinto, que sólo aparece PORQUE se arregló el segundo

Decir la verdad sobre la convergencia tiene una consecuencia: el camino que
informa de un campo que no se asentó pasa de ser casi inalcanzable —la cara de
filtración congelaba sus nodos y llamaba a eso converger— a ser fácil de
alcanzar. Y ese camino terminaba en `QMessageBox.information`, **modal**.

Un mensaje modal en código que una corrida automática puede alcanzar no es un
aviso: es un bloqueo indefinido, que es justo lo que las reglas de este proyecto
prohíben. Se midió: una corrida se quedó **una hora y cincuenta y un minutos**
parada, con el proceso a 125 s de CPU y sin avanzar, esperando a que alguien
pulsara un botón que no existía en una pantalla que tampoco.

Pasa a la barra de estado. Un mensaje sobre el **resultado** que se acaba de
calcular no es una pregunta ni una condición previa, y no tiene por qué detener
a nadie. Va con test, y el test comprueba que la llamada **vuelve**.

## Y una regresión que cazó la suite, no yo

Sacar el conductor fuera de la interfaz se llevó por delante media función de un
aviso. El que dice «ningún material toma su presión intersticial del campo, así
que estos factores ignorarían el agua» vivía en las **notas de la etapa**, y de
ahí lo lee la ventana de Interpret y de ahí sobrevive a un guardado. El conductor
nuevo lo devolvía sólo al que llama — correcto para un guion, y **fuera de la
pantalla para la que se escribió**.

`test_warning_when_materials_ignore_seepage` lo cazó en la suite entera. Vuelve a
las notas, y además se le añade el test que faltaba: que llegue a los dos sitios.

## Un cuarto defecto, pequeño y del mismo sitio

Una etapa de **duración cero** no anotaba `calculate_sf`. La rama que la atiende
construye sus notas a mano y esa clave no estaba, mientras que el consumidor la
busca ahí. Como la única etapa que **siempre** tiene duración cero es el
instante inicial, el efecto era que se podía marcar *Calculate SF* en t = 0 y no
salir factor ninguno, sin un aviso. Se arregla y va con test.

## Seis más, encontrados por una revisión adversarial antes de publicar

Antes del commit se pasó al cambio una revisión con cinco lentes independientes
—corrección numérica, regresión, las siete reglas, calidad de los tests y
honestidad de lo escrito—, con cada hallazgo sometido a un segundo lector cuyo
trabajo era **refutarlo** leyendo el código. De veintiséis hallazgos
sobrevivieron dieciocho, que son seis defectos distintos. **Todos son de esta
versión, y cuatro habrían salido a la calle.**

1. **`wetted_nodes` sí recorría la base del modelo**, y el docstring prometía lo
   contrario. Lo único que apartaba el paseo del cimiento era encontrar antes un
   nodo por encima del agua, y eso falla en dos casos corrientes: un nivel que
   alcance el punto más alto del terreno —el paseo cruza la coronación, baja por
   el paramento opuesto, recorre la base entera y vuelve: **174 de 174 nodos, 83
   sobre el cimiento**— y un modelo cuyo extremo es un vértice único en vez de un
   corte vertical, con las dos direcciones abiertas y una de ellas la base: **66
   de 130 nodos, 63 sobre el cimiento**. En los dos, `apply_reservoir` prescribía
   carga total sobre una frontera impermeable. Ahora la parada se **dice**: la
   base y el extremo opuesto son infranqueables, no se deja a que el agua se
   acabe antes.
2. **La caché del agua embalsada no veía bajar el embalse.** Su clave eran
   identidades y longitudes, sobre el argumento de que «la malla y las
   condiciones se rehacen enteras cuando cambia cualquiera de las dos». No se
   rehacen: `add_node` sustituye una entrada **dentro de la misma lista del mismo
   objeto**. Medido: prescribir 24,41 y luego 12,0 sobre los mismos nodos seguía
   contestando 24,41 — doce metros de columna de agua de más, del lado inseguro.
   Y no es un caso raro: un desembalse **es** «lo mismo con un nivel más bajo».
   La señal estaba a la vista y no la leí: mis propios tests anulaban la caché a
   mano.
3. **La excepción nueva se escapaba de un slot de Qt.** `run_analysis` levanta
   desde esta versión, y la cadena *Compute Groundwater* → transitorio →
   `run_analysis` no tenía un solo `try`. Antes la capturaba `_ComputeWorker`; al
   sacar el conductor de la interfaz, dejó de haber quien la capturase. La
   ventana quedaba a medias, con la filtración ya resuelta y guardada.
4. **Los avisos del conductor se mostraban sin `tr()`.** Las traducciones al
   español se añadieron y quedaron **inalcanzables**: la regla 2 al revés, la
   clave existe y la llamada no.
5. **El tope de succión SÍ mueve el número con φ_b = 0**, y el tooltip, el
   comentario del ajuste y un test afirmaban que no. Sólo es invisible con φ_b y
   valor de entrada de aire **los dos** a cero: por debajo del valor de entrada
   de aire la presión negativa real se **conserva** y se le acredita el ángulo de
   rozamiento saturado, así que acotarla cambia la tensión efectiva sin ningún
   φ_b. Medido: una succión de 90 kPa con AEV = 50 llega a la resistencia como
   −50 sin tope y como −20 con tope de 20.
6. **Y un test mío que pasaba por la razón equivocada.** El que comprueba que se
   avisa cuando ningún material acopla montaba un modelo sin ninguna condición
   Dirichlet, así que el campo fallaba por ser **singular** y no por el
   acoplamiento; y el conductor se tragaba esa razón. Ahora el modelo lleva su
   embalse, el conductor dice que el campo falló y **por qué**, y hay un test
   separado para cada cosa.

## Los números del problema 102

El manual publica **26 factores de seguridad** y **ningún parámetro
hidráulico** —ni k_s, ni curva de retención, ni almacenamiento—, y el artículo
del que los toma, Huang y Jia (2009), *Comput. Geotech.* 36(1-2) 93-101, no tiene
copia abierta. Pero un **régimen permanente no depende de k_s**: sólo de la forma
de k(ψ), y la zona no saturada en equilibrio es prácticamente hidrostática. Así
que hay cuatro valores completamente determinados por lo publicado, y son el
criterio de cierre:

| | Publicado | OGR 0.1.125 | |
|---|---|---|---|
| Seco, Spencer | 2,455 | **2,4582** | +0,13 % |
| Permanente inicial, φ_b = 0 | 1,745 | **1,7173** | −1,59 % |
| Permanente inicial, φ_b = 37 | 1,815 | **1,8008** | −0,78 % |
| Permanente final drenado, φ_b = 0 | 2,376 | **2,4024** | +1,11 % |
| Cociente de φ_b, efecto solo | 1,0401 | **1,0486** | +0,82 % |

El cociente es el que mide lo que el 102 existe para verificar: divide fuera el
sesgo común a los dos y deja el término de succión desnudo.

### El quinto no es un quinto, y lo dice el manual

A 1500 h con φ_b = 37 el manual da 2,612, y es tentador tratarlo como el
permanente drenado igual que su gemelo de φ_b = 0. **No lo es.** La leyenda de su
propia figura 102.11 declara una succión máxima de 9,1 m donde el permanente
exige 21,3, y la columna de Huang y Jia sigue subiendo entre 1000 y 1500 h
(2,804 → 2,813) mientras que la de φ_b = 0 ya no se mueve (2,374 → 2,374). A 1500
horas las presiones positivas han convergido y **las succiones no**.

Así que sólo se afirma la desigualdad que de ahí se sigue: el permanente de OGR
(2,95) tiene que estar **por encima** del 2,612 de una corrida que aún está
drenando. Lo está.

### Y lo que no se valida, dicho antes de medirlo

Los **22 valores intermedios** de las Tablas 102.2 y 102.3 necesitan k_s, θ(ψ) y
S_s. Se corren y se publican como **medición**, no como validación. El
almacenamiento **no se ajusta**: sale del propio manual de verificación de
filtración de la referencia, que declara m_v = 0,003 /kPa para una presa de
tierra, de donde S_s = γ_w·m_v = 0,0294 1/m. Se ajusta **un solo escalar**, k_s,
sobre el eje de tiempos.

Y el ajuste **acota su mínimo**, que es lo que lo distingue de un tope del
barrido:

| k_s (m/s) | 1e-6 | 1e-5 | **3e-5** | 1e-4 | 3e-4 |
|---|---|---|---|---|---|
| error cuadrático medio relativo | 0,143 | 0,098 | **0,045** | 0,048 | 0,165 |

El primer intento barrió de 1e-7 a 1e-5 y puso el mejor valor **en el extremo**,
que no es un ajuste sino el borde del rango; hubo que extenderlo hasta que el
mínimo cayera dentro. Con k_s = 3e-5 los doce instantes salen a un 4,5 % de media
y el último, 1500 h, a **2,370 contra 2,376** — pero eso no valida nada: es un
parámetro ajustado dando el número al que se le ajustó. Queda anotado como
**A102-1**, abierto.

---

## Aparte

- **El tope de presión intersticial negativa.** La referencia le da página propia
  y OGR no lo tenía. Acota la succión que llega al cálculo de resistencia, se
  aplica **antes** de la envolvente bilineal —porque lo que acota es la presión,
  no la cohesión que de ella se deriva— e ignora el signo con que se escriba,
  como la referencia declara. `None` por defecto, que es su valor por defecto y
  lo que este programa hacía. Con φ_b = 0 **no puede** mover el número, y hay un
  test que lo exige: un mando que se notara ahí lo estaría notando por la razón
  equivocada.
- **`run_analysis` deja de poder mentir.** La guarda `check_analysis_settings`
  se escribió en v0.1.77 y se conectó sólo al CLI y a la interfaz, así que el
  único llamante que de verdad la necesitaba —un guion— seguía obteniendo un
  factor plausible calculado con u = 0. Ahora levanta, con un escape explícito
  para quien ya haya leído los problemas y decidido.
- **Una asimetría vista y NO medida, dicha porque toca lo que se ha
  cambiado.** El paso transitorio libera un nodo de la cara de filtración con
  `q_node > 1e-12` en crudo, mientras que el permanente usa una banda escalada
  con el caudal total de las condiciones prescritas. Son la misma decisión con
  dos criterios, y con el presupuesto de conmutación subido el transitorio tiene
  ahora más margen para notarlo. No se ha medido y no se ha tocado: queda
  escrito para que el que lo mida no empiece de cero.
- **Dos funciones escritas y retiradas.** `nodes_below` y `nodes_between`, los
  dos destinos genéricos que el perímetro mojado no cubre, se escribieron y se
  quitaron antes de publicar: **no las llamaba nadie**. Es la regla 7 aplicada a
  una API en vez de a un ajuste — código exportado, sin consumidor y sin test es
  la misma promesa vacía que un control que no mueve el número.
- **El paseo del perímetro mojado nunca entra en la base del modelo.** Sin esa
  regla, partir de la esquina inferior recorre la solera, sube por el extremo
  opuesto y baja por el talud de aguas abajo: **208 de 226 nodos**, medido, para
  un embalse que toca 55.

## Fuera de alcance, a propósito

- **Carga total variando linealmente** a lo largo de un contorno: la referencia
  le da página y ecuaciones propias, y el 102 no la necesita.
- **Picar segmentos en el lienzo**, que es el mecanismo general de la
  referencia. El destino geométrico cubre el caso; el picado es trabajo de
  interfaz con su propia validación.
- **Un mando de tiempo continuo para el desembalse.** La referencia tampoco lo
  tiene.

---

## Compatibilidad

- Los proyectos existentes se abren sin cambios: el tope nace en `None`, que es
  el comportamiento anterior.
- `solve_project_seepage` **no cambia de significado**: sigue siendo la puerta
  saturada lineal, contra la que hay casos confinados validados. Lo que cambia
  es que ya no es la única.
- Ningún modelo sin filtración por elementos finitos se mueve un dígito. Los
  seis modelos del banco con carga embalsada la definen con una superficie
  **dibujada**, que nunca pasó por la función corregida.

Suite entera: **2701 / 2701**.

# OGR Slip2D v0.1.121 — la junta que la superficie recorre en vez de atravesar, y el corte obligatorio que no separaba nada

Hay resistencias que deciden la rotura y no tienen espesor: las hiladas de
un muro de gaviones, una geomembrana, un plano de estratificación. Hasta
esta versión sólo se podían emular con **bandas finas de material**, y eso
es otro problema: una banda tiene espesor y la superficie puede cortarla en
diagonal, mientras que una junta obliga a la superficie a **seguir la
línea**. Con juntas de 1 m entre gaviones de 1×1 m, esa diferencia es el
problema entero.

Se añade el contorno de **capa débil** (defecto **D27** del banco de
verificación, problema 109). Y como suele pasar, lo que se encontró por el
camino vale tanto como lo que se escribió: **una identidad que parecía
obvia era falsa**, y el test que la sustituyó destapó un defecto real en el
propio recorte.

---

## 1 · Qué es una capa débil, leído y no supuesto

La ayuda de la referencia la describe en una frase que decide todo el
diseño: una superficie *«continúa bajando dentro del suelo, y si encuentra
una capa débil la recorre hasta que (a) alcanza el terreno, (b) reencuentra
su propia intersección de vuelta hacia el terreno, o (c) subduce otra capa
débil de cota superior»*.

Las tres salidas son el mismo enunciado visto tres veces, y se implementa
como lo que es — un **máximo**:

    base_y(x) = max( superficie(x), la capa débil más alta en x )

La misma forma que `CompositeSurface`, y por la misma razón mecánica: una
capa débil restringe la superficie **por abajo** y en ningún otro sentido.
Escrito como máximo y no como «baja, sigue, sube» a propósito: esa segunda
redacción necesita que la superficie se hunda **exactamente una vez**, y un
muro escalonado con cuatro juntas se puede cruzar el número de veces que
haga falta.

Tres cosas más de la propia ayuda, y las tres implementadas:

- **No es geometría del modelo.** No se interseca con otros contornos y no
  define regiones de material. En `regions.py` no entra, y en el mallador
  de filtración tampoco.
- **Existe entera o no existe.** Una superficie afectada por una capa la
  corta toda o no la corta.
- **Se puede suprimir** sin borrarla, porque una capa activa fuera del
  contorno externo revienta la discretización y borrarla para averiguarlo
  no es un flujo de trabajo.

### La resistencia sale de un MATERIAL, no de dos campos en el contorno

`Boundary.material_id` ya existía y sólo significaba algo en los contornos
de material. Ahora significa lo mismo en una capa débil: **de qué está
hecha la junta**. Es lo que hace la referencia —su propia figura 109.1
lista *Weak Layer* en la tabla de materiales, con su γ, su tipo de
resistencia, su superficie de agua y su Ru— y tiene tres ventajas
concretas sobre poner `c` y `phi` en el contorno: hereda los **veinte
modelos constitutivos** del proyecto en vez de sólo Mohr-Coulomb, no añade
campos nuevos al formato, y convertir un contorno de material en junta le
deja un material sensato en vez de dejarla muda.

### El peso NO cambia

Una junta de espesor nulo no pesa. Sólo se sustituye `Slice.material`, y
`_column_weight` sigue integrando la columna banda a banda con los
materiales de las regiones que el modelo tiene de verdad. Hay un test que
mete **cincuenta veces** el peso específico del suelo en el material de la
junta y exige que el factor de seguridad no se mueva **un bit**.

La presión intersticial sí sigue al material de la junta, y eso es una
decisión y no un descuido: la tabla de la referencia le da columnas *Water
Surface* y *Ru* propias, así que una junta drenada de otra manera que el
suelo es expresable. Con la misma superficie de agua en las dos —todos los
modelos del banco— no cambia nada.

---

## 2 · Dónde se engancha, y por qué ahí

En **`BaseSearch._best_of_masses`**, envolviendo el bucle que ya elegía la
peor entre varias masas disjuntas. Es el punto único por el que las **seis**
búsquedas llegan al motor —el mismo argumento con el que v0.1.102 puso ahí
los filtros de superficie y v0.1.118 los Slope Limits—, así que una masa
pasa a ser *una superficie por caso de capa débil* y la peor es la
respuesta.

Un modelo sin capas débiles devuelve **el mismo objeto**, no envuelto en
nada. No es una optimización: es el invariante que sujeta los 137 tests de
validación, y se comprueba que ninguno se mueve un dígito.

### Dos políticas, y la tercera se deja fuera con su razón

| Política | Qué hace | Cuánto cuesta |
|---|---|---|
| `highest` (predeterminada) | toda capa que la superficie toca la recorta, y donde dos se solapan gana la más alta | 1 análisis por superficie |
| `auto_cases` | prueba **todas** las combinaciones de las capas tocadas —el caso «ninguna activa» incluido, porque cortar a través de los bloques es un mecanismo— y se queda con la peor | 2ⁿ análisis de esa superficie |

La referencia tiene una tercera, heurística. **No se implementa, y no por
falta de ganas**: es una extensión de *Particle Swarm Optimization* y sólo
existe encima de ella. Sin PSO en este programa no tendría dónde
engancharse, y aproximarla sería inventar.

### «Tocada» se decide capa a capa, y ahí había una trampa

Una capa está tocada cuando, **ella sola**, recortaría la superficie.
Decidirlo con todas activas a la vez sería n veces más barato y estaría
mal: dos juntas paralelas a un metro cruzan la misma superficie, pero con
las dos activas sólo gana la de arriba, así que la de abajo no aparecería
en el conjunto — y bajo `auto_cases` **el caso que más importa**, la
superficie corriendo por la junta INFERIOR con la superior apagada, no se
generaría nunca. La política rigurosa habría sido silenciosamente menos
rigurosa que la barata.

---

## 3 · Lo que se encontró por el camino

### 3.1 · La «identidad de reducción» que escribí en la especificación era FALSA

La especificación pedía esto: *una capa débil a la que se asigna el mismo
material que el entorno debe devolver el factor de siempre dígito a
dígito*. Suena evidente y **no lo es**: la capa sigue **recortando**. Con
la junta hecha del mismo suelo, el factor pasó de **2,651020 a 2,796720**,
un +5,5 %, y con toda la razón: la superficie ya no se hunde por debajo de
la junta, así que es **otra superficie**.

Lo que sí es una identidad, y la que quedó en el test, son dos:

- **La misma trayectoria escrita a mano.** Donde el camino recortado es
  poligonal, entrarlo como superficie no circular ordinaria tiene que dar
  el mismo número. Da **2,589088270572** contra **2,589088270572**.
- **Los dos modelos.** Una junta que aporta una resistencia tiene que dar
  el mismo factor que un modelo hecho **entero** de ese material sobre el
  mismo camino. Medido, para Ordinary, Bishop y Janbu:

| método | sin capa, material único | con capa débil |
|---|---|---|
| Ordinary/Fellenius | 1,605145820 | 1,605145820 |
| Bishop simplificado | 1,598477282 | 1,598477282 |
| Janbu simplificado | 1,605132508 | 1,605132508 |

Dígito a dígito, las tres. Es la afirmación más fuerte que se puede hacer
sobre la sustitución: si se le hubiera escapado un peso, una presión
intersticial o un corte de dovela, las dos columnas se separarían.

### 3.2 · El recorte declaraba cortes obligatorios que no separaban nada

Lo destapó la primera identidad, que fallaba por **1,6e-6**. La causa: los
**extremos** de una capa entraban en `kinks()` sin preguntar si allí
cambiaba algo. Una junta que va de x = 12 a x = 22 sobre una superficie que
sólo gana entre 12,6 y 19,4 declaraba **cuatro** cortes obligatorios donde
hay **dos**.

1,6e-6 es despreciable. Lo que no lo es: **el dovelador rechaza una
superficie con más cortes obligatorios que dovelas**, así que una junta
cuyos extremos caigan sobre tramos que no gana podía dejar sin analizar una
superficie perfectamente ordinaria, sin decir por qué. Un breakpoint sólo
es un quiebro si la rama ganadora cambia al cruzarlo, y ahora se comprueba
—sin epsilon: comparando la rama que gana a cada lado, en los puntos medios
de los intervalos, que es exactamente lo que ya hacía `spans()`—.

### 3.3 · El techo de ángulo de base: se implementa MÁS ESTRECHO que la referencia, a propósito

Donde una junta simplemente termina, la superficie cae de vuelta al arco por
un escalón **vertical**, y un base casi vertical hace que
`m_alpha = cos a (1 + tan a tan phi / F)` se desplome hacia cero mientras
crece sin límite la normal que divide. La referencia lo resuelve con un
techo, θ_max = 80° por defecto, en sus ajustes avanzados.

`AdvancedSettings.max_base_angle_deg` existe ahora con ese valor — pero se
aplica **sólo a las superficies que una capa débil ha recortado**. La
referencia lo aplica a toda columna; aplicarlo aquí a todo movería
resultados en modelos que no tienen ninguna capa débil, **los casos
publicados incluidos**, y una funcionalidad nueva no tiene derecho a
moverlos. Queda medido y anotado: el día que alguien quiera el techo global,
lo primero es contar cuántas superficies de los bancos validados pasan de
80°.

Que el techo hace falta se ve en la propia medición del problema 109: sobre
un muro con tres juntas, el buscador por bloques anota escalones de **85,4°,
85,9° y 88,2°** y los descarta con su aviso.

### 3.4 · Bishop sobre una superficie no circular plana: −0,42 %, y no es de aquí

Sobre un plano, Bishop circular y Ordinary son **la misma expresión**:

    F = (c B + W cos²a tan phi) / (W sin a cos a)

Ordinary de OGR la reproduce a **4e-16**. Bishop da **−0,42 %**. Es una
observación, no un defecto de esta versión: está ahí **sin ninguna capa
débil en el modelo**, y es la misma sensibilidad al eje de momentos
construido que D15/A22-1 midió en −1,84 % contra +0,08 % — una superficie
no circular no tiene centro, así que toma momentos respecto de un eje
construido, y sobre un plano ese eje no es el que la fórmula circular
supone. Por eso el test ancla **Ordinary** contra la forma cerrada y no
Bishop: afirmar una fórmula circular sobre una superficie no circular
mediría eso, no esto.

---

## 4 · Interfaz

- **Boundaries → Add Weak Layer** (`Ctrl+7`), con su modo de lienzo, su
  color propio y su z-order **por encima de los contornos de material y
  por debajo de las superficies de agua**: lo que hace falta ver es dónde
  corre la junta respecto de las capas.
- Al cerrar la polilínea se abre el diálogo de **asignación de material**,
  igual que v0.1.97 abre el de asignación cuando se dibuja una superficie
  de agua. Una junta sin material no tendría resistencia propia y sólo
  cambiaría la geometría, que es el único resultado que nadie quiere.
- *Assign Material* acepta ahora los dos tipos de contorno cuyo
  `material_id` significa algo.
- **Surface Options → Weak Layer Handling**: la política y el tope de
  capas a combinar.
- **Project Settings → Advanced**: `max_base_angle_deg`.
- Visibilidad y color en las opciones de visualización; conversión de
  contorno; capa `OGR_WEAK_LAYER` / `JUNTA` en DXF, de ida y de vuelta.

  **Y ahí saltó un test que existe justo para esto.** Añadida la capa al
  importador y no al exportador,
  `test_dxf_export_v148::test_mapping_is_derived_from_the_importer` falló
  con `BoundaryType.WEAK_LAYER`: su contrato es que las dos mitades no
  puedan separarse. Fue el único fallo de la suite entera, y lo encontró él
  y no una revisión.
- Traducciones: *capa débil*, *Añadir capa débil*, *Tratamiento de capas
  débiles*, *Pegar siempre a la capa más alta*, *Generación automática de
  casos*.

### Avisos, una vez por análisis y no una por superficie

`settings_warnings` señala una capa **sin material asignado** y una capa
**entera por encima del terreno**. Y cuando un conjunto de casos se trunca
por el tope, se dice: un conjunto truncado en silencio se lee exactamente
igual que una cobertura completa.

---

## 5 · Lo que NO hace

- **No se optimiza** una superficie recortada. `_surfaces_to_optimize` deja
  fuera lo que no tiene `.polyline`, igual que deja fuera un círculo y un
  compuesto. No es una regresión —sin capas débiles nada cambia— pero es un
  comportamiento que conviene tener escrito.
- **No hay política heurística** (véase §2).
- **No hay estrategia de rescate** para cortes verticales en zona de
  compresión: se descartan.
- Una capa débil **no entra en la malla** de elementos finitos.

---

## 6 · Verificación

- `tests/test_weak_layer_v1121.py` — 22 tests: la forma cerrada plana, las
  dos identidades, el peso que no llega, los cortes que sí separan, las
  cuatro separaciones de la regla 7, los avisos de modelo y la ida y vuelta
  del `.ogr` (incluido un archivo anterior a esta versión, sin la clave
  `suppressed`).
- Suite completa en verde.
- Los 137 tests de validación externa —`slide_validation`,
  `published_cases`, `validation_cases`, `noncircular`, `composite`— sin
  moverse un dígito.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later

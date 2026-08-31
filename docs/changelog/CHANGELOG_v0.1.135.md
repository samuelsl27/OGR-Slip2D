# OGR Slip2D v0.1.135

**Defecto D21b, puntos (1), (3) y (4).** El criterio de cierre que traía el
encargo era insatisfacible y el repositorio ya lo decía desde 0.1.118; el punto
(3) no era un aviso que faltara sino uno que llegaba a una búsqueda de siete; y
el (4) no era lo que su ficha decía. Debajo de los tres había una anomalía que
los números del propio encargo llevaban dentro sin nombrar.

---

## 1. El punto (1): el criterio pedía algo que no se puede pedir

El encargo pedía un test de que **«a igualdad de superficies generadas, el
mínimo no empeora al subir `num_groups`»**. Tres lecturas del código lo tumban,
y ninguna necesitó ejecutar nada:

1. **La población generada ya estaba fija.** El bucle es
   `for ip in range(self.num_surfaces)` (`search.py:2927`). `num_groups` no
   multiplica candidatas: cambia cuántos **vértices libres** tiene cada una. Las
   cuatro filas que publica el encargo corrieron las cuatro con 5000 generadas,
   así que «a igualdad de superficies generadas» no era una normalización que
   añadir — era la condición bajo la que ya se había medido. Y bajo ella el
   mínimo se mueve en los dos sentidos: 1,633327 → 0,619769 → **0,640339** →
   0,535380 de 1 a 4 grupos.

2. **Las familias son disjuntas, así que no hay contención.** Con k grupos la
   región se parte en k franjas iguales y se sortea **un punto por franja**
   (`search.py:2980-2982`): una candidata de k grupos tiene exactamente k
   vértices de bloque, y al cambiar k las franjas se **reparticionan**. Una
   superficie de k−1 no es un miembro degenerado de la familia de k: no está en
   ella. Este proyecto sólo asserta monotonía donde la contención es
   demostrable, y aquí es demostrablemente inexistente.

3. **Ya estaba escrito, con números.** El docstring de módulo de
   `tests/test_search_inequality_v1118.py:37-43` y el de
   `test_the_number_of_groups_moves_the_number` dicen desde 0.1.118 que *no* se
   asserta que más grupos den un mínimo menor «porque se midió y es falso», con
   1,298 a dos grupos contra 1,367 a cuatro, y lo llaman «una limitación real
   que enunciar, no un bug que asegurar de un plumazo».

**Cerrado por re-enunciado y medición**, con el precedente de D20/A55-1 en
0.1.117. Escribir el test que se pedía habría exigido fabricar la contención
cambiando el muestreo, o sea inventar un algoritmo que la referencia no tiene —
lo que la propia ficha de D21b prohíbe.

### Lo que sí se puede afirmar, y nadie había escrito

Con la misma semilla, **las N primeras candidatas de una corrida de 2N son
idénticas bit a bit** a las N de una corrida de N: el bucle lee `num_surfaces`
sólo como cota y nada más consume del generador. Eso es contención por prefijo,
comprobada y no supuesta, y de ella **sí** se sigue que más candidatas no pueden
dar peor respuesta. Es la forma honesta de la afirmación que D21b buscaba, y es
el eje sobre el que la población importa de verdad.

---

## 2. La anomalía que el encargo traía dentro, medida

Los números del propio encargo pedían explicación y no la tenían: Bishop
**0,5354** sobre el dique de James Bay, que publica **1,105** en no circular
(Duncan y Wright 2005: 1,170) y cuyo mínimo circular es **1,434**. La
explicación de 0.1.118 —dimensionalidad— predice que el mínimo **suba** con los
grupos; no puede explicar un 0,54 en un terraplén que está en pie.

**No era el escalón invisible de `slicer.py:526-542`.** Se comprobó: las dovelas
ven la cara perfectamente (`base_ang_min = −77,97°` con dovelas de 0,42–1,01 m
sobre un tramo de 2,90 m). No hay nada oculto.

**Tampoco era D39**, que es sobre el término normal `T_N·tanφ` de un **soporte**:
el modelo no tiene refuerzo, así que `T_N` es cero. Comparten el síntoma
—métodos de cociente sobre base muy inclinada— y no el mecanismo.

**Lo que es.** En un material **puramente cohesivo** el término de rozamiento de
`m_alpha = cos α + s·sin α·tanφ/F` desaparece y `m_alpha` degenera en **`cos α`
exacto**. Eso convierte el chequeo m-alpha en un techo desnudo de ángulo de
base: **78,46°** al límite de 0,2 de la referencia. Las cuatro arcillas del
dique tienen `tan_phi = 0,0000`, la región implícita de Block genera caras a
**77,8–78,0°**, y ahí Bishop divide la normal por 0,21.

| grupos | FoS | min m_alpha | α de esa dovela | admisible |
|---|---|---|---|---|
| 2 | 0,619769 | 0,2084 | −77,97° | **sí** |
| 4 | 0,535380 | 0,2115 | −77,79° | **sí** |

Aceptada por **once milésimas**, y por **0,67° de ángulo de base**.

Y explica todo lo medido: con **un** grupo no hay ni una superficie bajo lo
publicado (tres vértices no pueden formar una cara vertical: máximo 40,9°); con
más grupos las franjas se estrechan y las caras alcanzables se empinan; y Bishop
se separa de Spencer sólo cuando la cara aparece (0,5354 contra 0,9645 a cuatro
grupos; 1,633 contra 1,721 —un 5 %— a uno).

### Lo que lo convierte en defecto y no en curiosidad

**Una búsqueda minimiza el factor, y el factor se minimiza empujando `m_alpha`
hacia el límite.** La superficie que una búsqueda reporta es por tanto,
sistemáticamente, aquella donde su método es menos válido. A cuatro grupos el
chequeo rechazó el **82,6 %** de la peor banda y la ganadora salió del resto.

### El aviso

`m_alpha_margin_note` (`analysis_runner.py`), junto a `daylight_tangent_note` y
`grid_edge_note` y con la misma naturaleza: **sólo informa**, nada del análisis
cambia. El umbral se eligió como el suyo — midiendo y quedándose en el hueco.
Sobre el dique, 3000 candidatas, 1807 válidas, contra el 1,105 publicado:

| min m_alpha | n | FoS mínimo | % bajo 1,105 |
|---|---|---|---|
| [0,20, 0,25) | 65 | 0,5870 | **35,4 %** |
| [0,30, 0,40) | 142 | 0,6337 | 8,5 % |
| [0,40, 0,50) | 207 | 1,0200 | 1,0 % |
| [0,50, 0,60) | 459 | **1,5775** | **0,0 %** |
| [0,60, 0,80) | 695 | 1,6314 | 0,0 % |

Nada por debajo de 1,105 sobrevive por encima de 0,5, y el factor más bajo salta
de 1,02 a 1,58 al cruzarlo. **0,5** es además `1/m_alpha = 2`: la normal
amplificada al doble. Es umbral de aviso, no constante física.

---

## 3. El punto (3): el aviso existía y llegaba a una búsqueda de siete

Desde 0.1.128 el Auto Refine no circular contaba las superficies que el
rebanador rechazaba enteras y lo decía. **Nada más lo hacía** — y son Block y
Path las que lo necesitan, porque sus superficies llevan un vértice por punto
generado más cada cruce de capa, mientras que un círculo no tiene quiebres y la
regla queda inerte para toda búsqueda circular.

El recuento se muda a **`_best_of_masses`**, la única puerta por la que cada
búsqueda alcanza el rebanador — el mismo argumento que 0.1.102 usó para los
filtros de superficie: *«un filtro puesto en otro sitio sería un filtro por el
que alguna puerta podría rodear»*. El texto pasa a ser `_unsliceable_note()`,
que el Auto Refine sobreescribe porque es la única que puede nombrar la causa
exacta (eligió ella el número de vértices).

De paso se corrigió lo que contaba: el contador viejo medía «el ensayo entero no
dio nada», un escalón más grueso que el rechazo del rebanador que decía medir.

### Cuánto muerde, medido

Problema 19 del banco (260 × 100 m, 30 dovelas), con longitud de segmento
**manual** en Path:

| longitud | generadas | rechazadas por el rebanador | válidas |
|---|---|---|---|
| automática (~0,3H) | 309 | 0 | 300 |
| 5,0 m | 572 | 258 | 300 |
| 2,0 m | 5098 | 5077 | **20** de 300 |
| 1,0 m | 5082 | **5082** | **0** |
| 0,5 m | 5050 | **5050** | **0** |

Un usuario que pide segmentos de un metro se lleva **cero superficies y ni una
palabra**. La ficha describía esto como perder una superficie; se pierde la
búsqueda entera.

---

## 4. El punto (4): `max_segments` no era lo que decía su ficha, y las DOS correcciones se midieron y se descartaron

**No es constante de clase**: es el valor por defecto de un argumento de
`PathSearch.__init__` que `build_search` **nunca pasaba**, así que valía 30
siempre. Hasta ahí, la ficha se corrige sola.

Lo instructivo es lo otro: **se intentaron dos acoplamientos al `num_slices` del
proyecto y los dos se cayeron al medirlos.** El segundo llegó a estar escrito,
con sus tests en verde, y lo tumbó la suite entera.

**Primero, `= num_slices`, que es lo que hace la referencia.** Habría movido
**25 modelos del banco** por puro **arrastre del generador aleatorio**: un
recorrido que agota su presupuesto devuelve `None` tras consumir un número
distinto de sorteos, y eso desplaza el flujo de todo lo que viene detrás. Cero
mejora de búsqueda, 25 filas movidas. Descartado antes de escribirlo.

**Después, `min(max_segments, num_slices)`**, que parecía la versión prudente:
nunca generar lo que el rebanador tendrá que rechazar, y sin mover el banco
porque todos los modelos de Path declaran 30, 40 o 50 dovelas. Se escribió, sus
cinco tests pasaron, y **la suite completa lo tumbó** — un test de otra área
cuya premisa es una superficie concreta dejó de obtenerla.

Al medir por qué, resultó **peor que el primero**: es **inerte donde está el
problema y activo donde no lo hay**.

- Donde el problema existe —problema 19 con longitud de segmento manual de 1 m,
  donde el rebanador rechaza las 5082 superficies que la búsqueda genera— el
  modelo declara 30 dovelas, así que `min(30, 30) = 30` y **la guarda no hace
  nada**.
- Donde no hay problema —el modelo de Ej_1 a 14 dovelas— **ninguna** superficie
  pasa de 7 segmentos y el rebanador **no rechaza ninguna**, y aun así la guarda
  movió Spencer de **1,147928 a 1,161636** y cambió la superficie reportada.

| tope | segmentos máx. | rechazadas por el rebanador | FoS |
|---|---|---|---|
| 30 (hoy) | 7 | **0** | 1,147928 |
| 14 (la guarda) | 7 | **0** | 1,161636 |
| 500 | 8 | **0** | 1,076900 |

**Queda en 30 y justificado**, que es la otra mitad de lo que el propio defecto
admitía («debería ser ajuste **o estar justificada**»). Es una guarda contra un
recorrido que no vuelve a aflorar, **no** un control de resolución, y por eso es
deliberadamente independiente del número de dovelas. Con el tope abierto a 500,
la superficie más larga que produjeron cuatro modelos del banco fue de **15
segmentos**, mediana 8–9, contra este tope de 30: no ata nunca con longitud
automática.

Lo que el rebanador rechaza **se dice** ahora, en vez de intentar evitarlo por
ingeniería: es el punto (3).

**La lección, y es la de siempre en este proyecto**: el arreglo evidente se
midió y no valía, y el que parecía prudente sólo se destapó al correr la suite
entera en vez de los tests dirigidos. El test que lo cazó no se tocó — se quitó
el cambio.

---

## 5. Lo que se encontró y NO se ha tocado (regla 6)

- **`max_base_angle_deg` no llega a Block Search.** El ajuste existe, vale 80°
  por defecto y tiene control en Ajustes del Proyecto → Avanzado, pero
  `_base_angle_ok` (`search.py:618-619`) devuelve `True` para todo lo que no sea
  `WeakLayerSurface`. Su comentario dice por qué —ensancharlo movería modelos sin
  capa débil, incluidos los casos publicados de validación— y esa razón sigue en
  pie. Pero deja el techo de ángulo de base sin alcance justo donde esta versión
  ha medido que hace falta. Reportado, no tocado.
- **Las notas del motor no pasan por `tr()`.** Las cinco, la nueva incluida. No
  es descuido de esta versión: el escáner de presupuesto de
  `test_i18n_coverage_v141.py` sólo recorre fuentes de la GUI, así que ninguna
  se cuenta. Pero llegan al usuario como avisos, y la regla 2 dice que todo texto
  visible pasa por `tr()`. Es su propia tarea.
- **D39 sigue abierto y esta versión no lo toca.** Lo que sí aporta es que su
  síntoma —métodos de cociente sobre base muy inclinada— tiene al menos **dos**
  mecanismos distintos: el término normal del soporte, que necesita un refuerzo,
  y la degeneración de `m_alpha` a `cos α` bajo φ = 0, que no necesita ninguno.

---

## 6. Qué se probó

- `tests/test_block_population_v1135.py` (9 tests): la identidad de población
  para 1..4 grupos, la disjunción de las familias, la contención por prefijo
  comprobada a precisión completa, la monotonía en `num_surfaces`, y la
  identidad analítica `m_alpha == cos α` bajo φ = 0 con el aviso disparando y
  callando.
- `tests/test_slicer_budget_v1135.py` (9 tests): el aviso alcanzando Block, el
  recuento, el caso silencioso, que las superficies se pierden de verdad, y las
  cinco propiedades de la guarda del tope.
- Suite entera, sin filtro.
- **El ancla del banco**: el 75 con su objeto de bloque declarado sigue en
  Bishop **1,611895** y Spencer **1,823021**, con **3160 / 2631** válidas.

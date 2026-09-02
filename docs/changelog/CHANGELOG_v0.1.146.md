# OGR Slip2D v0.1.146

**El encargo decía que los dos intervalos de límites son «el de arranque y
el de salida». La documentación de la referencia dice, con todas las
letras, que no obliga a nada de eso. Y el único caso publicado que podría
desempatar da EXACTAMENTE el mismo círculo crítico con las dos lecturas,
así que no desempata: elegir la que ajusta habría sido inventarse una
prueba que el caso no da.**

Cierra **D50** del banco de verificación. El problema 27 pasa de −73,8 % a
**+1,48 %** contra su tabla 27.3, con la restricción declarada **en el
modelo** y no aplicada por fuera.

---

## Qué estaba mal

`SearchSettings` guardaba **un** intervalo, `slope_limit_left` /
`slope_limit_right`. El enunciado del problema 27 declara **dos**:

> *«a search with the restriction that the circular surface must exit the
> slope between 38 ≤ x ≤ 70 at the toe and 120 ≤ x ≤ 180 at the crest»*

Con un solo par, el modelo sólo podía decir la **unión**, 38..180 — y esa
unión no filtra nada. La superficie que ganaba la búsqueda aflora en
x = 102,7 y x = 162,9: las dos dentro de la unión, las dos fuera de las dos
ventanas. Es una lonja del Soil 2, que tiene c = 0 y φ = 0, y el motor
hacía lo correcto con la pregunta que se le hacía.

Emparenta con **D21** (0.1.118), donde los límites llegaban a **una** de
las seis búsquedas. Aquél era de alcance; éste, de expresividad.

## Qué se ha hecho

`slope_limit_left_2` / `slope_limit_right_2`, opcionales y `None` por
defecto. El motor guarda los intervalos en `BaseSearch.slope_limit_sets` y
`slope_limits` **pasa a ser una propiedad de solo lectura que devuelve la
envolvente**. Eso es lo que hace pequeño el cambio, y no es un truco: la
referencia le da a los límites dos oficios distintos, y sólo uno de los dos
cambia con dos ventanas.

| oficio | qué lee | qué hacen los dos intervalos |
|---|---|---|
| **generación** — «the slope surface is simply the segments of the External Boundary between the Slope Limits» | la **envolvente** | nada: se busca «between the two» además de dentro de cada uno |
| **filtrado** — «all slip surfaces must intersect the slope within the defined slope limits» | los **intervalos** | membresía: cada extremo, en alguno |

Así, los **cinco** recortes de generación (Grid, Auto Refine, Block, Path,
Recocido) no se han tocado y siguen siendo correctos, y con un solo
intervalo la envolvente **es** ese intervalo: byte a byte lo de antes.
Comprobado sobre el propio 27 con la unión 38..180: 0,361112 y 2864
válidas, los mismos dígitos que en 0.1.145.

El filtro pasa a ser membresía en los **tres** sitios donde se pregunta
—`_best_of_masses`, el prefiltro del Block y el punto de salida del Path—,
a través de un helper compartido que hasta ahora no existía: había **cinco
reimplementaciones a mano**, con tres tolerancias distintas.

### El único sitio donde cambia el comportamiento

El rango de arranque del **Path Search**. La referencia enuncia la regla en
dos mitades y sólo la primera era alcanzable:

- un juego → se parte el rango por la mitad y se usa la mitad del lado del
  pie (lo que dejó D21);
- dos juegos → se usa **el juego del lado del pie**, sin partir nada.

Y recomienda el doble juego para esa búsqueda precisamente por eso: deja
enunciar el rango de iniciación en vez de deducirlo de un punto medio.

## Los tres hallazgos, que es lo que merece recordarse

### 1 · La semántica del encargo no es la de la referencia

El encargo describía emparejamiento: un extremo en el intervalo del pie y
el otro en el de coronación. La base de conocimiento de la referencia dice
lo contrario:

> *«When you define two sets of slope limits, there is **no explicit logic
> to force slip surfaces to enter and exit in the two limits**, although
> that is the general purpose of the option. The program **still searches
> each set of limits independently, as well as between the two**.»*

Es **pertenencia**. Se implementa la documentada.

### 2 · Y el problema 27 NO distingue las dos lecturas

Medido antes de decidir, sobre la misma población generada (5042 masas
candidatas), variando **sólo** el filtro:

| regla | válidas | círculo crítico |
|---|---|---|
| pertenencia (A ∪ B) | **1546** | (62,941 · 182,353) R 120,92 |
| emparejamiento estricto (A y B) | **1546** | (62,941 · 182,353) R 120,92 |

Idénticas, en los cinco métodos. Las 237 masas con los dos extremos en la
misma ventana —13 en el pie, 224 en la coronación— no sobreviven a
`min_area = 200` ni a la admisibilidad, así que nunca llegan a competir.

**El caso publicado no autoriza la lectura estricta.** Queda escrito en el
test y en la ficha para que nadie la deduzca del acuerdo de un caso que no
puede decidirlo — que es la forma exacta del error de v0.1.112, donde se
eligió una orientación *porque ajustaba*.

### 3 · La tabla de medidas del encargo había caducado

El encargo tabulaba, con 0.1.127, Bishop +2,58 % y Lowe-Karafiath +0,87 %.
Hoy salen **+1,48 %** y **+1,42 %**. No es una discrepancia: entre 0.1.127
y 0.1.146 aterrizaron D05, D45, D39/D44 y el cambio de convenio interdovela
de 0.1.144. **Una tabla de medidas caduca con el motor que la produjo**, y
ésta llevaba dieciocho versiones sin remedir.

## El resultado

Problema 27, tabla 27.3, con las dos ventanas **en el modelo**:

| método | unión 38..180 | **dos ventanas** | publicado | Δ |
|---|---|---|---|---|
| Bishop | 0,361112 (−73,8 %) | **1,396346** | 1,376 | **+1,48 %** |
| Janbu corregido | 0,351200 (−73,9 %) | **1,372500** | 1,345 | **+2,04 %** |
| Lowe-Karafiath | 0,426391 (−69,4 %) | **1,411793** | 1,392 | **+1,42 %** |
| Spencer | 0,419165 (−69,7 %) | **1,403396** | 1,382 | **+1,55 %** |
| GLE / M-P | 0,408216 (−70,4 %) | **1,398235** | 1,378 | **+1,47 %** |

Válidas 2864 → **1546** de 4860. El mínimo aflora en x = 39,7 y x = 155,9:
una ventana en cada extremo. `mecanismo_reproducido` del 27 pasa de `false`
a `true`, y no es un ajuste de contabilidad — su evidencia escrita era,
literalmente, la frase de las dos ventanas.

## Interfaz

Los límites se editaban con **dos `QInputDialog` encadenados**. Con dos
juegos habrían sido cuatro, sin manera de decir que el segundo está
apagado. Ahora hay un diálogo propio con casilla *Segundo juego de
límites*, que valida que cada juego tenga la derecha mayor que la izquierda
y que **no se crucen** — la referencia tampoco deja arrastrar un marcador
más allá de otro.

De paso arregla dos cosas que estaban:

- el editor mostraba `None` como **`0.0`**, así que «automático» era
  indistinguible de «limitado en x = 0», y abrir el diálogo y aceptar
  convertía lo primero en lo segundo sin que nadie lo pidiera. Ahora parte
  de la extensión del terreno, que es lo que *automático* significa;
- *Reset* dejaba vivo el segundo juego. Ahora borra los cuatro.

Y **se dibujan**: hasta ahora `grep slope_limit` sobre `ogr_gui/canvas/`
daba **cero**. Un modelo estrechado a una ventana junto al pie se veía
igual que uno sin restringir. Se dibujan sólo los límites **explícitos**;
los automáticos caen en los extremos del perfil y un marcador allí no diría
nada que el perfil no diga ya, además de sugerir una restricción que el
modelo no ha hecho.

## Tests

`tests/test_slope_limits_two_sets_v1146.py`, 14 casos. El de regla 7 es el
que cierra el criterio 4: mismo modelo, envolvente contra dos ventanas,
**0,425782 → 0,557293, +30,9 %**, y con dos afirmaciones más que dicen *por
qué* — que el mínimo de la envolvente aflora en el hueco, y que el de las
dos ventanas aflora dentro de ellas. Sin esas dos, el test mediría que algo
cambió sin saber si era lo que se cree.

La cabecera del archivo dice explícitamente que **no valida un factor de
seguridad**: el valor externo es la tabla publicada y esa comparación vive
en el banco.

## Lo que se anotó y NO se corrigió

- `optimize.py` **no lee los límites en ninguna línea**. Con
  `move_endpoints=True` el paseo puede salirse de ellos y sólo lo salva el
  rechazo posterior de `_best_of_masses`: acotación contra rechazo.
- `slope_frame` —Slope Search y Particle Swarm— no los lee al generar.
  Slope Search avisa; **PSO no avisa de nada**.
- Las tolerancias de los tres filtros son incoherentes: `1e-9` **relativa**
  en `_best_of_masses`, `1e-6` **absoluta** en Block y en Path, contra la
  convención del proyecto. El helper recibe la tolerancia como argumento
  para no cambiar ninguna: cambiarlas mueve números y no es este defecto.

## En el banco

El problema 27 pasa a declarar sus **cuatro** tablas como escenarios
(27.2 círculo dado, 27.3 búsqueda, 27.4a y 27.4b grieta). Hasta ahora la
comparativa sólo leía `referencia.fos` y **la tabla 27.3 no generaba
ninguna fila**: el número que mide este defecto era invisible, y las dos de
grieta llevaban versiones con sus resultados en disco sin entrar. El 27
pasa de 5 filas a 20: **+15, de las que 10 salen `OK` y 5 `REVISAR`**, y
ninguna `DISCREPANCIA`. Ninguna fila de ningún otro problema se mueve.

Al declararlos apareció un defecto de la propia herramienta, que es D52 por
el otro lado: el escenario de **búsqueda** resolvía por NOMBRE el círculo
de la tabla 27.2 y comparaba ese factor contra los valores de la 27.3 —dos
tablas distintas en la misma celda—. Ahora un bloque que declara
`superficies` vacío está diciendo que no tiene ninguna, y una declaración
explícita gana a la coincidencia de nombre.

### Y una cosa que se encontró de camino, que no es de este defecto

`auditoria_reproducible.py` **no está en 0 DIFERENTE, y no lo estaba antes
de empezar**. Desde **v0.1.144**, que cambió el predeterminado de
`interslice_forces` de `effective` a `total`, **145 modelos** del banco
discrepan de lo que hoy producen sus constructores. Relanzar los 93
`construir_modelo.py` —el paso habitual cuando crece el esquema— habría
arrastrado ese cambio de convenio a 145 modelos de una vez, moviendo
números por toda la comparativa por una razón que nada tiene que ver con
D50. **No se ha hecho.** En su lugar los dos campos nuevos se han escrito
como `null` en los 180 modelos que están en el esquema vigente, de modo que
la huella de este defecto sobre esa auditoría es **cero**: lo que queda son
145 `interslice_forces` y 4 de rejilla, todos anteriores. Los cuatro
modelos del 27 sí se regeneraron, y ahí el convenio sí cambia: mueve
**sólo** a Lowe-Karafiath, de +0,10 % a +1,42 %.

Los **3 ERROR** de `auditoria_invariantes.py` son los mismos de antes
—D07c, D39 y D21b sin estado en su cabecera; D13 cerrado conservando
sección y prompt— y ninguno es de aquí.

El guardarraíl que traía el encargo (**486 filas, 176 OK, 101 REVISAR, 95
DISCREPANCIA, 0 DIFERENTE, 0 ERROR**) estaba **caducado en los cinco
números**: se escribió el 2026-08-27 con 0.1.127 y el banco lleva dieciocho
versiones de trabajo encima.

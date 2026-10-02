# OGR Slip2D v0.1.237

**D87: Overall Slope acumula la estadística de UNA superficie.** La clave con
que se juntan los factores de cada muestra es ahora el tipo y la geometría
exactos de la superficie, extremos incluidos, y la superficie probabilística
crítica solo se elige entre las que tienen factor en TODAS las muestras
contadas de la corrida. Hasta 0.1.236 la clave era el centro y el radio
redondeados a 0,5 unidades del modelo: juntaba las dos masas de un círculo,
una compuesta con su círculo sin recortar y dos círculos de una rejilla a menos
de medio metro, y la superficie que se publicaba como crítica podía salir de
una mezcla que no es ninguna superficie. En el problema 36 del banco, la única
corrida Overall Slope, la superficie crítica pasa del círculo (3,0; 21,25;
R 16,34), β 1,8858, al (4,0; 18,75; R 13,775), β 1,8693, que la mezcla
escondía; la PF, β y los cuatro mínimos distintos de la corrida no se mueven.

## 0. Lo que se encontró, y dónde

### La premisa del prompt se sostiene

`_surface_key` (`ogr_core/statistics/probabilistic.py`) indexaba un círculo por
`"c:%d:%d:%d"` de centro y radio divididos por `tol = 0.5`. Sobre la muesca
de `test_statistical_rebuild_v1154` (Fredlund y Krahn 1977, problema 22, con
una muesca en la coronación), las dos masas del círculo publicado —x de 45,84
a 49,70 y de 56,05 a 158,73— tienen la misma clave, `c:240:180:160`, y la
compuesta y su círculo sin recortar también.

### Y es más ancha: la tolerancia junta círculos distintos

Medido sobre la búsqueda determinista del 36 (rejilla de 20 × 20 centros a
1,0 × 1,25 m, diez incrementos de radio, 2578 evaluaciones), contando las
claves que reúnen círculos con centro o radio distintos:

| Clave | Claves | Juntan círculos distintos | Círculos en ellas |
|---|---|---|---|
| centro y radio a 0,5 (hasta 0.1.236) | 1570 | **746** | 1754 |
| tipo, centro, radio y extremos a 0,5 (el paso 1 del prompt) | 2444 | **126** | 260 |

Los radios de un mismo centro van a menos de 0,5 m, así que dos de ellos caen
en la misma cuantización. El par que decidía la superficie crítica publicada
es el centro (4,0; 18,75) con R = 13,775 (masa x 5,01–17,26, F = 1,3404 en la
media) y R = 14,126 (x 0,77–17,62, F = 1,5541), los dos bajo `c:8:38:28`.
Ninguno de los dos cambia de masa en las 200 muestras
(`_auditoria/P5_0237/masas_036.json`): lo que movía la crítica no eran dos
masas de un círculo, sino dos círculos de una clave. La propuesta del prompt
(tipo y extremos redondeados por `tol`) habría dejado esos 126.

### Qué es la superficie probabilística crítica

La ayuda de la referencia la define como la superficie, de todas las
analizadas, de mayor probabilidad de rotura (y menor índice de fiabilidad), y
dice cuándo la hay: la superficie tiene que estar en todas las muestras
calculadas; solo las búsquedas Grid, Slope, Path y Block garantizan las mismas
superficies de una muestra a otra, y para las metaheurísticas la opción no se
ofrece; las superficies optimizadas no entran (se calcula con las originales de
la búsqueda); no se ofrece con el análisis sísmico Ky; y su PF nunca supera la
de la corrida entera. La literatura dice lo mismo desde el otro lado: el índice
de fiabilidad es de UNA superficie potencial fija y la superficie crítica
probabilística es la de menor β entre las candidatas (Li y Lumb 1987; Hassan y
Wolff 1999, *J. Geotech. Geoenviron. Eng.* 125(4):301-308, que muestran que la
de menor factor y la de menor β no tienen por qué coincidir; Bhattacharya et
al. 2003; Xue y Gavin 2007; Cheng, Li y Liu 2015, *NHESS*).

En términos matemáticos, PF(S) = P[F(S, X) < 1] para una superficie S fija.
Juntar dos superficies da la PF de una mezcla; contar una superficie solo en
las muestras en que la búsqueda la devuelve la sesga, porque qué masa devuelve
depende de X (la más débil de las dos), y deja su PF sin comparar con las
demás, contadas sobre otras muestras. Si cada candidata se cuenta sobre todas
las muestras contadas, en cada muestra el factor de la corrida es el mínimo y
no supera el de la candidata, así que PF(crítica probabilística) ≤ PF(corrida)
se cumple por construcción: la propiedad que la referencia afirma.

### Por qué sin tolerancia, y no con una relativa

Se consideró hacer la tolerancia relativa al tamaño del modelo (AGENTS.md lo
pide para las tolerancias geométricas). Se descartó: donde la clave decide algo
—las búsquedas que regeneran sus superficies— no hace falta ninguna, porque las
regeneran hasta el último dígito (la misma aritmética sobre la misma geometría:
medido, los 176 círculos de la rejilla de v137 con la cohesión en los dos
extremos de su variable, 3 y 27 kPa, y la población de la Slope Search igual);
y cualquier tolerancia junta, y lo que junta es una mezcla.

### Lo que la regla de la referencia pedía y en OGR no tenía nombre

La Slope Search de OGR añade desde 0.1.17, tras su población, un paseo de
refinamiento por las ocho mejores circunferencias, guiado por sus factores: una
optimización con otro nombre, metida en `evaluations`. La referencia deja fuera
las superficies optimizadas; aquí no había cómo distinguirlas.
`SearchResult.steered` lo dice ahora (el paseo, y lo que guarda Optimize
Surfaces).

### Los mínimos distintos de una búsqueda guiada

Con la identidad exacta, `distinct_minima` cuenta superficies distintas en
cualquier dígito. Para Grid, Slope, Path y Block es lo que era (en el 36 y en
las tres configuraciones de v137, el mismo número). Para Auto Refine, Simulated
Annealing y Particle Swarm, cuyas mínimas difieren de una muestra a otra en
algún dígito, pasa a contar cada una, que es lo que son; con la tolerancia de
0,5 se juntaban las que quedaban a menos de medio metro, una agrupación que no
se explicaba en ningún sitio. Ningún modelo del banco ni ningún test usa
Overall Slope con una búsqueda guiada.

## 1. El motor

- **`_surface_key(sd)`** (`probabilistic.py`): `"<tipo>:<cx>:<cy>:<R>"` más
  `":<x_left>:<x_right>"` cuando el diccionario trae los extremos, con cada
  número escrito por `_exact` (`repr(float(x) + 0.0)`: el entero 4 y el real
  4.0 son una coordenada, y −0,0 se pliega en 0,0); `"p:<tipo>:"` y los
  vértices exactos para las de vértices (v1154 fija el prefijo `p:`). Sin el
  parámetro `tol`: un parámetro que ya no hace nada no se queda (regla 7).
- **`BaseSearch.SAME_SURFACES_EVERY_SAMPLE`** (`ogr_slip2d/search.py`): False
  en la base; True en `GridSearch`, `SlopeSearch`, `PathSearch` y
  `BlockSearch`, cada una con la razón (la Path Search genera hasta tener
  Number of Surfaces válidas, así que una muestra con más inválidas recorre un
  poco más de la MISMA secuencia; las primeras Number of Surfaces se generan
  siempre).
- **`SearchResult.steered`**: lo que la corrida añadió guiada por sus
  factores, también en `evaluations`: el paseo de la Slope Search,
  `optimized` y las mínimas mejoradas de `_optimize_each_minimum`. La acción
  manual Optimize Surfaces de la ventana principal lo continúa en una lista
  nueva (`copy.copy` compartía la vieja).
- **`run_overall_slope`**: por muestra contada, `_critical_probabilistic_excluded`
  decide si la búsqueda puede tenerla (no la tiene si no regenera sus
  superficies o si el objetivo no es el factor de seguridad) y, si puede,
  `_accumulate_surfaces` añade UN factor por superficie y muestra, sin lo
  guiado. Tras el bucle, son candidatas las que tienen un factor por cada
  muestra contada (`n == len(values)`), con al menos `min_evaluations`
  muestras. Criterio de elección sin cambiar: máxima PF, desempate por menor β.
  Cuando no hay, `notes["critical_probabilistic"]` dice por qué con una de
  cuatro frases (`_CPS_STEERED`, `_CPS_KY`, `_CPS_TOO_FEW`,
  `_CPS_NOT_IN_EVERY_SAMPLE`), y `summary()` la lleva en
  `critical_probabilistic_note` (la API y el MCP la ven). Un método sin
  muestras no la lleva: está perdido y ya se dice.
- Las estadísticas de la corrida (PF, β, valores) no dependen de nada de esto:
  la identidad solo decide la superficie crítica y los mínimos distintos.

## 2. La interfaz

- *Pick GM Surfaces*: cada fila dice qué superficie es, con su tipo y sus
  extremos (`minimum_row_text`, despachado por `type` y no por la presencia de
  `radius`, que también tiene una compuesta). Dos masas de un círculo eran dos
  filas iguales.
- *Critical Probabilistic Surface*: cuando una corrida Overall Slope no tiene,
  el aviso es la razón del motor, traducida por su valor; el de Global Minimum
  no cambia.
- Siete entradas nuevas en el diccionario español: tres filas y las cuatro
  frases del motor, con un test que comprueba que siguen al motor.

## 3. Tests

**`tests/test_surface_key_endpoints_v1237.py`**, 24 casos: la clave (dos
masas, compuesta y círculo con los mismos extremos, el par del 36, cualquier
dígito separa y el ida y vuelta por JSON no, polilíneas con su prefijo, el
diccionario sin tipo ni extremos, la firma sin `tol`); qué búsquedas regeneran
sus superficies, con las dos premisas medidas (la rejilla de v137 y la
población de la Slope Search, iguales hasta el último dígito con la cohesión en
3 y en 27, y el paseo en `steered`); Overall Slope sobre la muesca con
búsquedas de prueba (una masa que solo contesta en unas muestras no es
candidata y la nota lo dice; las dos masas nombradas, en todas las muestras,
son dos candidatas y la elegida no pasa la PF de la corrida; lo optimizado y lo
guiado no entran; una búsqueda guiada o con Ky no la tiene y lo dice; pocas
muestras, también); el talud de v137 con su rejilla (la crítica tiene todas las
muestras y los mínimos distintos son los de la clave vieja en las tres
configuraciones); y la interfaz (las filas, las traducciones y el aviso).

Cambia a propósito `test_statistical_rebuild_v1154.py::test_a_circle_keeps_the_key_it_always_had`,
renombrado `test_a_circle_is_keyed_by_its_type_and_its_exact_geometry`: fijaba
el propio defecto (la clave de la compuesta igual a la de su círculo). El
prompt lo contaba entre lo que no se podía mover; al planificar se vio que es
la aserción del defecto.

**Discriminación** contra el árbol de 0.1.236 —sin commit: una copia del
árbol de trabajo con los cambios de D87 quitados—, con su runner: **20 de 24
fallan**, diez por comportamiento (la clave junta las dos masas, la compuesta
con su círculo, el par del 36, dos superficies que difieren en un dígito y dos
polilíneas; lo optimizado y lo guiado entran en la estadística, con 60 factores
en 30 muestras) y diez por símbolo (las cuatro frases, el atributo de las
búsquedas, `steered` y `minimum_row_text`). Pasan las dos premisas y los dos
controles del talud de v137, a propósito. Un caso pasaba en 0.1.236 por
casualidad —lo guiado sí entraba, pero bajo la clave vieja de la masa profunda,
y la superficie que se conservaba era el diccionario de esta— y se reforzó con
el recuento de factores antes de archivar la discriminación.

**Controles** (A/B en el mismo proceso, `ab_v137.py` contra los dos árboles):
en las tres configuraciones de `test_overall_slope_v137`, los mismos mínimos
distintos (4 / 1 / 4), las mismas 168 superficies seguidas y elegibles, la
misma superficie crítica y la misma PF. Allí las 168 tienen factor en todas las
muestras y la elegida es también la de menor β.

## 4. El banco

**Medido antes de tocar el motor**, en una pasada del 36 que acumula con tres
reglas a la vez (`_auditoria/P5_0237/ab_d87_036_exacta.py`, 200 muestras, la
regla vieja reproduce lo archivado en 0.1.236):

| Regla | Mínimos distintos | Superficies seguidas | Superficie probabilística crítica |
|---|---|---|---|
| centro y radio a 0,5 (0.1.236) | 4 | 1563 | (3,0; 21,25; R 16,34), PF 0,03, β 1,8858 |
| tipo, centro, radio y extremos a 0,5 | 4 | 2441 | (4,0; 18,75; R 13,775; x 5,01–17,26), PF 0,03, β 1,8693 |
| exacta, en todas las muestras, sin lo optimizado | 4 | 2573 | la misma, n = 200 |

**El 36 no archivaba la superficie crítica**: `ejecutar_probabilistico.py`
guardaba PF, β y los mínimos distintos de Overall Slope, y nada de la
superficie. Ahora guarda `superficie_probabilistica_critica` (tipo, centro y
radio o vértices, extremos, n, PF, β y veces que fue mínimo global) y la razón
del motor cuando no la hay.

**Re-corrida del 36 con 0.1.237** (2292 s, en paralelo con la suite), a través
de `reejecutar_036_con_espia.py`, que lanza lo mismo que
`correr_probabilistico.py` con un espía en el `max` del módulo (devuelve lo
mismo; guarda las candidatas): las 12 cifras de Global Minimum y las 5 de
Overall Slope, iguales a las de 0.1.236; la superficie archivada es la medida,
(4,0; 18,75; R 13,775; x 5,01–17,26), con un factor en las 200 muestras, PF
0,03, β 1,8693, mínimo global en 147 de ellas.

**El criterio de elección, comprobado y sin tocar.** La ayuda de la
referencia define la superficie como la de mayor PF en una página y como la de
menor índice de fiabilidad en otra, y con la PF contada por muestras las dos
cosas no tienen por qué coincidir. En el 36 coinciden: 2510 candidatas (las
2515 que aparecen en todas las muestras, menos cinco sin factor en alguna),
solo dos con la PF máxima, y la de menor β es la elegida; en las tres
configuraciones de v137, también. No hay con qué abrir una ficha.

**Cierre**: `d87()` en `verificar_cierres.py` (en vivo sin tests, sobre
diccionarios y sobre el talud de d93 con su rejilla y con Auto Refine; el A/B
archivado; el 36 archivado con la superficie medida; la discriminación):
**CUBIERTO POR TEST**, con las seis partes en verde (en la rejilla del talud
de d93, la superficie crítica tiene 8 de 8 muestras y su PF, 0,125, no pasa la
de la corrida; con Auto Refine no hay ninguna y la nota lo dice). D87 se retira
al índice.

## 5. Lo que se reporta y NO se corrige

- **Las superficies del usuario siguen fuera de las candidatas** (lo reportado
  en 0.1.236): se analizan en cada muestra con la misma geometría, y la
  superficie crítica de la corrida puede ser una de ellas, pero la referencia
  calcula la superficie probabilística crítica con las superficies originales
  de la búsqueda. Se queda así a propósito.

## 6. Verificación

- **Suite entera:** 5321 de 5321, en 62 min con la re-corrida del 36 en
  paralelo los primeros 38.
- **Selecciones:** el test nuevo con v1154 y v137, 68 de 68; los 29 archivos
  de estadística, Interpret, i18n, optimización y búsquedas, 572 de 572.
- **Discriminación:** 20 de 24 contra 0.1.236.
- **A/B:** v137 en los dos árboles (sin cambios); el 36 en una pasada con tres
  reglas, y re-corrido con 0.1.237 (sin cambios en sus 17 cifras; la
  superficie crítica, la medida).
- **Ciclo de cierre del banco:** `verificar_cierres.py` entero, 210 cierres y
  0 bajadas; instantánea `Evaluaciones/0.1.237`; D87 retirada, podada de
  `PAQUETES` y tachada en la cadena P5; prompts regenerados (46); auditorías
  de invariantes con 0 ERROR en el 02 y en la raíz; instantánea rehecha con
  `--forzar`; y el `--seco` completo después de retirar, sin ningún NO SE
  SOSTIENE ni PENDIENTE DE CORRIDA.

**Qué falta por probar:**
- **Overall Slope con una búsqueda guiada en la aplicación**, a mano: el aviso
  de *Critical Probabilistic Surface* y el número de mínimos distintos, que
  ahora cuenta cada superficie distinta (ningún modelo del banco lo usa).
- **Una Slope Search o una Path Search en Overall Slope sobre un modelo del
  banco**: el 36 es una rejilla; el paseo de la Slope Search y la cola de la
  Path Search están cubiertos por el test y el razonamiento, no por un caso
  publicado.

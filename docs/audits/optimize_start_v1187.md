# De dónde sale el `null` de la optimización — censo de OGR 0.1.187 (D161)

Medido el 2026-09-22 evaluando, una por una, las superficies que el banco
archiva para las filas sin `fos_optimizado`. La mitad no circular del banco la
escribió 0.1.185, así que **el testigo sobrevivió a una re-corrida**, que no es
obvio: D146 y D149 se escribieron sobre testigos que ya estaban curados.

## La premisa de la ficha es falsa

D161 está escrita así: *«el paseo de `optimize.py` camina hasta una superficie
que no se puede evaluar, y devuelve `null` en vez de quedarse con la última que
sí lo era»*. **El paseo no hace eso y no puede hacerlo.**

- `optimize.py::_score` devuelve `None` cuando el candidato no evalúa, no es
  válido o no es admisible;
- el bucle hace `continue` **sin tocar `best_pts` ni `best_res`**;
- no hay ninguna rama que acepte un `None`, ni en la pasada ordinaria ni en la de
  `explore_all_vertices`;
- el optimizador es *greedy* puro —no hay recocido, no hay movimiento a peor— así
  que «la última» y «la mejor» son la misma superficie por construcción.

El `null` nace en la **puerta de entrada**: se densifica la partida a
`densify_to` puntos, se evalúa **esa**, y si falla se sale **antes del primer
paso**, devolviendo la superficie **original** junto al resultado de *otra*
superficie. El primer elemento del retorno **nunca** es `None`, de modo que el
aviso del banco «la optimizacion no devolvio superficie» es engañoso: lo que no
devolvió fue **resultado**. Los dos avisos, por cierto, **no son del motor**: los
escribe `_tools/ejecutar_no_circular.py`.

## Las nueve filas tienen TRES causas

De 97 filas de método con `fos` de búsqueda en la familia no circular, **9**
archivan `fos_optimizado` nulo o ausente. Ninguna de las tres causas es la que la
ficha describe, salvo la última.

| filas | caso | `leaves_soil` | foco | `_best_of_masses` | causa |
|---|---|---|---|---|---|
| **5** | 057 `modelo_compuesto` (`grid`, `tipo: composite`, 63 vértices) | False | False | **None** | El vector de vértices es `drawing_vertices()`, **un dibujo por contrato explícito** (`ogr_slip2d/surface.py`: *«This is a PICTURE of the surface, never the surface the slicer works on»*). `CompositeSurface` no tiene campo `polyline`, así que `_surfaces_to_optimize` **ya la descarta**; quien la reconstruye como `SlipSurface` desnuda es el banco. → **D164** |
| **3** | 079·gle, 079·spencer, 085·gle | False | False | **None** | **Redondeo a 4 decimales** de `_tools/ejecutar_caso.py`: el vértice del extremo queda **+1,0e-4 sobre el terreno** y `evaluate_surface` rehúsa la polilínea **entera**. → **D163** |
| **1** | 085·spencer | False | False | fos 2,0471695, `is_valid` **False** | «Spencer: no λ-bracket». La superficie rebana y el método **no tiene respuesta**. Aquí el `null` **es correcto**. |

### Las cifras exactas del redondeo

| fila | desfase del extremo sobre el terreno | encajándolo |
|---|---|---|
| 079 · gle_morgenstern_price | dy_ini **+0,000040** | **1,486395** — el `fos` archivado de la búsqueda **al último dígito** |
| 079 · spencer | dy_fin **+0,000040** | 1,489061 |
| 085 · gle_morgenstern_price | dy_ini **+0,000100** | evalúa |

Control: 079·bishop y 085·bishop cayeron en múltiplo exacto de 1e-4, **no se
levantan**, y sus dos filas publican su optimizado.

**Y ojo con leer esa columna de más.** «Encajando el extremo» es lo que da
**evaluar** la superficie con su vértice puesto sobre el terreno, no lo que da
optimizarla: es la prueba de que el vértice levantado era toda la causa. El
paseo, cuando por fin arranca, **sigue bajando** — re-corrido el 079·2 con el
reintento de D163, gle publica **1,44447** y spencer **1,444129**, partiendo de
1,486395 y 1,489058. Confundir las dos cosas convertiría una prueba de
diagnóstico en una prediccion de resultado.

La regla que los rehúsa es correcta y está medida en su sitio
(`BaseSearch.evaluate_surface`, problema 27 de Malkawi & Sarma 2001): *«a vertex
lifted 0.05 ft over the ground is already enough»*. **El motor hace lo que tiene
que hacer; lo que está mal es lo que se le entrega.**

## Un error propio del medidor, que estuvo a punto de publicar una cuarta causa

La primera medida del desfase del 085 dio **+2,6537 m** y **+4,5790 m**, que
parecía un mecanismo distinto y habría quedado escrito como tal. Era el medidor:
`optimize._ground_y` recorre los vértices del External por x, y el External del
085 es el cuadrilátero `[(15,10),(57,10),(57,30),(25,30)]`, así que leyó el
**borde inferior** (`y = 10`) en vez de la **cara** `y = 2x − 20`. Contra el
perfil superior del propio motor los desfases son **+1,0e-4** (gle) y **0,0**
(spencer), y 085·gle resulta ser redondeo como el 079.

Es la lección de v0.1.185 otra vez: una medida equivocada sosteniendo un reparto
equivocado. Aquí se cazó porque el resultado no encajaba con el control —
085·bishop, en el mismo archivo y con el mismo redondeo, **sí** publica su
optimizado.

## Dos cifras más de la ficha, corregidas

- **El residuo**: **0,0272** en la superficie original (6 vértices) y **0,0417**
  en la densificada a 12, que es la que el banco archiva y la que su aviso cita.
  El **0,0335** de la ficha es de 0.1.181.
- **Hay TRES formas de no-dato**, no una: `{}` (057), **clave ausente** (079 y
  085·gle) y `null` explícito (085·spencer). La cascada `f_opt → f_busq → f_sin`
  de `generar_comparativa.py` las absorbe las tres igual, y significan cosas
  distintas.

## El segundo síntoma, el −12,6 % del 077, es otra cosa

En 077 · caso2_piezometrica, entre 0.1.173 y 0.1.185, la crítica de Spencer es
idéntica, el `fos` de búsqueda es idéntico (1,761832), las generadas son
idénticas (28 870), la semilla de optimización es la misma y `fos_optimizado`
pasa de **1,578525 a 1,379141**. Bishop, en el mismo archivo, no mueve un dígito.

Eso **no** es este defecto. Es que **el paseo está guiado por el evaluador**, por
construcción. Dentro de una pasada los dos `rng.uniform` salen **antes** de
`_admissible`, así que un rechazo barato no consume RNG; pero el **número de
pasadas** y el **estado al que se aplican** sí dependen del factor
(`_admissible` rechaza sin incrementar `rep.iterations`; `improved_this_pass`
gobierna cuándo se encoge el paso y cuándo se para). El paseo **no es
reproducible entre evaluadores distintos**, ni entre puntos de partida
distintos — que es lo que hace caro el arreglo de D163.

Nótese además que 1,379 **<** 1,578: la optimización encontró un mínimo **más
bajo**, no uno peor.

## Lo que v0.1.187 corrige, y lo que NO alcanza

Corrige el silencio, que es lo que dejó la ficha escribirse al revés:

1. `optimize.py` separa las dos causas en **dos frases**. `error` conserva su
   nombre —la acción de menú de la interfaz cortocircuita sobre ella— y el matiz
   va en `start_invalid`. La frase del segundo caso dice que **no es un dato que
   falta: es la respuesta**.
2. `optimize.py` devuelve **la superficie que evaluó** (la densificada) en vez de
   la original, y anota `start_densified_to` cuando densificó.
3. `BaseSearch._optimize_result` y su gemelo multimodal dejan de fundir
   `res is None` y `not res.is_valid` en un `continue` mudo: cuentan las tres
   causas aparte y emiten **una** nota, **solo si ocurrió**.

**Lo que NO alcanza, y es fácil de leer al revés**: `ejecutar_no_circular.py`
**no enciende `optimize_enabled`** a propósito —si lo encendiera, `metodos`
archivaría ya el optimizado y la columna «búsqueda» de la comparativa dejaría de
ser la búsqueda— y llama a `optimize_surface` directamente. **Por tanto la nota
del motor no llega a ninguna fila no circular del banco.** El arreglo de motor y
el de banco son disjuntos y ninguno sustituye al otro.

**Cero filas del banco movidas por esta versión.**

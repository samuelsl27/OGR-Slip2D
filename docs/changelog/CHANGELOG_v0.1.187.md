# OGR Slip2D v0.1.187

**Tres fichas en una tanda, y de las tres hubo que corregir primero la premisa
con la que estaban escritas.** D160 pedía un censo que, hecho, **contesta otra
cosa que la que la ficha esperaba**: las filas que mueren en el techo de
intentos son exactamente las que tienen objeto de enfoque, así que hoy el
presupuesto lo cierra el foco y no la tasa de validez del evaluador. D161 decía
que «el paseo de `optimize.py` camina hasta una superficie que no se puede
evaluar», y **el paseo no hace eso y no puede hacerlo**: el `null` nace en la
puerta de entrada, antes del primer paso, y las nueve filas del banco que lo
publican tienen **tres causas distintas** de las que solo una es la que la ficha
describe. Y D162 pedía re-correr la mitad no circular del banco, que **ya se
había re-corrido** el 2026-09-21: su propia tabla era el estado *pre*-corrida y
se contradecía con su cuerpo treinta líneas más abajo.

El cambio de motor **no mueve un solo factor de seguridad**, y eso está medido
de dos maneras y en este orden. Con el motor cambiado y **sin re-correr nada**,
la comparativa balanceada contra `Evaluaciones/0.1.186` da **559 → 559 filas,
las 559 IGUAL, cero sin pareja**. Y re-corriendo de verdad el 079 y el 085 —doce
filas de método— salen **bit a bit idénticas** en `fos`, `generadas`, `validas`,
`invalidas`, `inadmisibles` y la polilínea crítica: **cero movidas**. Lo único
que cambia es lo que el motor **dice**.

Las tres filas que sí se mueven después las mueve el **banco** y no el motor
—son el reintento dirigido de D163— y las tres **mejoran**: dos pasan de
`REVISAR` a `OK` con la desviación cayendo de 3,0 % a **0,10 %** y de 3,2 % a
**0,08 %**. Estaban comparando un mínimo *sin optimizar* contra la columna
optimizada del manual, que es el sesgo al alza que `ejecutar_no_circular` existe
para no cometer.

---

## D160 — EL CENSO CONTESTA OTRA COSA, Y ESO ES LO QUE DECIDE LA RAMA

La ficha describe un mecanismo real y medido: `PathSearch._run` para en
`valid_count >= num_surfaces`, de modo que **un motor que hace válidas más
superficies ve menos superficies**. En el 085, entre 0.1.178 y 0.1.181, las
generadas pasaron de 38 461 a 34 175 con Bishop inmóvil como control nulo.

Lo que no estaba medido era **si eso asfixia alguna fila del banco**, y el censo
—`_tools/censo_presupuesto_d160.py`, SOLO MIDE— dice que no, y dice por qué:

| | filas `path` | por techo | por cuota | con foco | por techo **con foco** |
|---|---|---|---|---|---|
| todas | 88 | 17 | 71 | 36 | **17 de 17** |
| solo reproducibles | 85 | 14 | 71 | 33 | **14 de 14** |

**Ninguna fila sin objeto de enfoque llega al techo**, y las que llegan lo
tienen todas. Pero el foco es **necesario y no suficiente**: 33 lo tienen y solo
14 mueren por techo. Entre las que alcanzan la cuota, `generadas` va del
**5,81 % al 65,03 %** del techo — ninguna está cerca. O sea que el mecanismo que
la ficha describe es **latente** sobre este banco.

**LOS DOS DENOMINADORES NO SON EL MISMO, Y LA DIFERENCIA SON TRES FILAS
CONCRETAS.** El escenario `3b` del 078 está declarado no reproducible, lo midió
0.1.147, y sus tres filas paran por techo con **cero** válidas: contarlas mueve
el titular de 85/14 a 88/17. No es una curiosidad de contabilidad — **dos
recuentos independientes de este mismo censo discreparon justo en eso** antes de
que la herramienta existiera, y los 71 por cuota coincidían al dígito en los
dos. El censo publica los dos cubos por nombre y `verificar_cierres` los exige.

**LA DECISIÓN ES LA RAMA 2**, con cuatro argumentos y no uno: la semántica está
documentada desde v0.1.24 con su referencia detrás y la fijan tres asserts de
`test_search_effort_v1103.py` más la clase de migración; el factor 20× **no es
un ajuste** —vive en el constructor de `PathSearch` y no en `SearchSettings`—,
así que un «modo de presupuesto de generación fijo» tendría que ser además un
ajuste visible o sería un modo que nadie puede elegir; el censo dice que hoy el
techo lo cierra el foco; y la reconciliación honesta no es cambiar
`PathSearch`, porque la cabecera de `test_acads_validation_v178.py` ya documenta
que «Number of Surfaces» significa **dos cosas** —generadas en Slope Search,
aceptadas en Path Search— y *nada en la interfaz las distingue*. Cambiar Path
Search re-apuntaría 85 filas del banco **y dejaría la interfaz igual de
ambigua**.

**LO QUE SÍ FALTABA ES EL NÚMERO QUE NADIE PODÍA RECUPERAR**: la holgura de las
**19** filas que llegaron a cuota teniendo foco. `generadas` es
`validas + invalidas`, y un rechazo por foco no es ninguna de las dos —sale del
bucle sin tocar contador—, así que `attempts = generadas + rechazos_foco` y el
segundo sumando no se archivaba. Con `focus = 0` la resta es cero y `generadas`
**es** el esfuerzo; con foco es solo una cota inferior.

## D161 — LA PREMISA ES FALSA, Y LAS NUEVE FILAS TIENEN TRES CAUSAS

**El paseo de Greco no camina hasta una superficie inevaluable.** `_score`
devuelve `None` y el bucle hace `continue` **sin tocar `best_pts` ni
`best_res`**; no hay ninguna rama que acepte un `None`, ni en la pasada
ordinaria ni en la de `explore_all_vertices`; y el optimizador es *greedy* puro,
así que «la última que evaluaba» y «la mejor» son la misma superficie por
construcción.

El `null` nace en la **puerta**: se densifica la partida a 12 puntos, se evalúa
**esa**, y si falla se sale **antes del primer paso** devolviendo la superficie
**original** junto al resultado de *otra* superficie. El primer elemento del
retorno **nunca** es `None`, de modo que el aviso «la optimizacion no devolvio
superficie» era engañoso: lo que no devolvió fue **resultado**. Y los dos avisos
que la ficha cita **no son del motor**: los escribe la herramienta del banco.

**LAS NUEVE FILAS, REPARTIDAS**, midiendo cada superficie archivada:

| filas | caso | causa |
|---|---|---|
| **5** | 057 `modelo_compuesto` | Sus 63 vértices son `drawing_vertices()`, **un dibujo por contrato explícito**. `CompositeSurface` no tiene campo `polyline`, así que `_surfaces_to_optimize` **ya la descarta**: quien la reconstruye como `SlipSurface` desnuda es el banco. → **D164** |
| **3** | 079·gle, 079·spencer, 085·gle | **Redondeo a 4 decimales**: el vértice del extremo queda **+1,0e-4 sobre el terreno** y `evaluate_surface` rehúsa la polilínea **entera** (regla de v0.1.100, medida allí sobre el problema 27 de Malkawi & Sarma 2001). → **D163** |
| **1** | 085·spencer | La superficie **sí rebana** y **no tiene factor**: «Spencer: no λ-bracket». Aquí el `null` **es correcto**, y es la única fila que la ficha describía. |

Control: 079·bishop y 085·bishop cayeron en múltiplo exacto de 1e-4, **no se
levantan**, y sus dos filas publican su optimizado.

**Y HAY TRES FORMAS DE NO-DATO, NO UNA**: `{}` (057), **clave ausente** (079 y
085·gle) y `null` explícito (085·spencer). La cascada `f_opt → f_busq → f_sin`
de la comparativa las absorbía las tres igual, y significan cosas distintas —
«falta el factor» frente a «esta es la respuesta».

**EL SEGUNDO SÍNTOMA DE LA FICHA, EL −12,6 % DEL 077, ES OTRA COSA.** El paseo
**sí** está guiado por el evaluador, por construcción: dentro de una pasada los
dos `rng.uniform` salen **antes** de `_admissible`, así que un rechazo barato no
consume RNG, pero el **número de pasadas** y el **estado al que se aplican** sí
dependen del factor. El paseo no es reproducible entre evaluadores distintos ni
entre puntos de partida distintos — que es lo que hace caro el arreglo de D163.
Nótese además que 1,379 **<** 1,578: la optimización encontró un mínimo **más
bajo**, no uno peor.

## D162 — LA MITAD NO CIRCULAR YA ESTABA CERRADA, Y LA FICHA SE CONTRADECÍA

Medido: **37 archivos a 0.1.185 + 1 a 0.1.147**, cero a 0.1.173. El lote se
re-corrió el 2026-09-21 entre las 12:39 y las 16:40, y `Evaluaciones/0.1.185`
—congelada a las 16:59— **ya es el lado B**, no el lado A. El coste real fueron
**4 h 15 min** (15 348,6 s), no las «5,2 h» extrapoladas: un **+22 %** de
sobrestimación. La tabla de la ficha era el estado *pre*-corrida y su cuerpo el
*post*, dentro del mismo documento.

**DOS AFIRMACIONES DEL PROMPT SOBRE EL LANZADOR SON FALSAS**, y las dos importan
porque describen la herramienta con la que se trabajaría: `correr_no_circular.py`
**sin `--forzar` SÍ corre** lo que falta y lo caduco —lo que engaña es su
resumen, que se lee como un éxito cuando corrió cero—; y `esta_caduco` mira
primero `modelo_huella`, y solo si falta cae al criterio de fechas.

**Y EL REMEDIO BARATO QUE LA FICHA DABA POR PUESTO ESTABA CADUCO EN EL CÓDIGO.**
El renglón generado «Medido con (D162)» de la comparativa llevaba su frase final
**cableada a mano**: afirmaba que «sus archivos son identicos byte a byte en las
dos porque nadie los volvio a correr», cierto cuando se escribió y **falso desde
el 2026-09-21**. Es exactamente la trampa que su renglón hermano
`_renglon_pool` tiene documentada —una cifra escrita a mano caduca en cuanto el
banco se re-corre— y la pisamos igual. Ahora la frase se **deriva** del mismo
recuento que la describe, y con el banco de hoy dice: la mitad no circular la
midió 0.1.185 salvo uno, la circular sale de **nueve versiones distintas**.

**LO QUE SEGUÍA VIVO ERA LA MITAD CIRCULAR**: 194 archivos, 91 a 0.1.173, y
**nadie había medido lo que cuesta ese lote con el motor de hoy** — los 12,45 h
que suman los `segundos` archivados son de siete versiones y 28 archivos ni
traen el campo. Correr el lote entero a ciegas para averiguarlo es justo lo que
la ficha reprocha, así que se pagó un **sondeo**: ocho problemas, trece
archivos, elegidos por coste y no al azar, de 27 s a 1444 s.

**EL COSTE, MEDIDO**: 3 697 s → 4 526 s, factor **×1,224** — pero con los
extremos en **0,804 y 1,373** y la mediana en 1,144, y el factor **crece con el
coste del caso** (el 13, de 27 s, salió más rápido; el 107, de 843 s, ×1,373).
Extrapolado al lote entero: **15,24 h**, contra las 12,45 archivadas. La
dispersión va publicada al lado del factor a propósito: un ×1,22 con extremos en
0,80 y 1,37 no es la misma afirmación que un ×1,22 limpio, y el reloj de este
proyecto ya ha engañado dos veces.

**Y EL SEGUNDO RESULTADO ES MÁS GRANDE QUE EL PRIMERO: CERO DE 41 FILAS DE
MÉTODO SE MOVIERON.** Once versiones de motor entre 0.1.173 y 0.1.187 —D145,
D148, D149, D152, D153, D156, D159 entre ellas, todas sobre el solver de λ— no
movieron **un solo dígito** en los 41 métodos de esos ocho problemas
circulares, y el balance de la comparativa lo confirma por su lado: las 3 filas
que se mueven son las de D163 y ninguna es circular. Es una muestra —8 de los 61
problemas a 0.1.173, el 8,3 % del coste del lote— y se declara como muestra, no
como el lote. Pero es la primera vez que alguien lo mide, y lo que mide es que
**la obsolescencia era real y su consecuencia numérica, en esta muestra, nula**.

Con eso delante, D162 cierra por su **segunda rama**: la corrida completa no se
paga, se dice por qué con el número delante, y la comparativa lo publica en su
cabecera **y fila a fila**. Lo que queda abierto de verdad es el trabajo
recurrente: hay que repetir esto en cada versión que toque el solver, o la deuda
vuelve.

**Una tensión honesta que salió al final.** La re-corrida del 079 y el 085 dejó
la mitad no circular **menos** homogénea que antes —33 archivos a 0.1.185, 4 a
0.1.187 y 1 a 0.1.147— y la primera versión de `verificar_cierres.d162` exigía
homogeneidad, que es **más estricto que el criterio de la ficha**. Se relajó a lo
que el criterio pide de verdad, y se dejó escrito en su docstring por qué:
endurecer una comprobación por cuenta propia convierte un cierre legítimo en un
`NO SE SOSTIENE` y empuja a relajarla después para que pase, que es como se
vacían. Lo que **sí** sigue exigiendo es que la mitad no circular no esté
dominada por 0.1.173 y que la mezcla esté publicada por fila.

---

## EL CAMBIO DE MOTOR

Dos campos, siete incrementos y dos frases, y ninguno mueve un número.

**`SearchResult.focus_rejected`**, campo nuevo. Cuenta **generación y solo
generación**. No entra en `valid_count`/`invalid_count` porque eso rompería la
identidad `total_count == válidas + inválidas` sobre la que descansa la
población documentada del grid, que diecisiete tests fijan y dos de ellos son
`test_slide_validation_*`. Se incrementa en **cinco sitios de llamada** —Grid,
Slope (muestreo), Auto Refine, Block, Path— y en el de Particle Swarm, y **no**
en el refinamiento local de Slope ni en la propuesta del recocido, que son
paseos y no población; cada uno de esos dos sitios lo dice donde se salta.

**LA TRAMPA, QUE UN TEST EJECUTA**: el sitio evidente para el incremento es
dentro de `BaseSearch._focus_rejects`, y es **incorrecto**, porque `optimize.py`
llega a ese método por `getattr` — los rechazos del **paseo de optimización** se
sumarían a la población de la **búsqueda**.
`TestAWalkIsNotPopulation` corre la misma búsqueda con la optimización encendida
y apagada y exige que el contador no se mueva, con un guard-on-the-guard que
comprueba que el paseo de verdad consulta el foco.

**`attempts` lo rellenan ahora las siete búsquedas.** No cambia de significado
—sigue siendo «candidatos formados, contados antes de que nada pueda fallar»,
que es la definición canónica de Auto Refine desde v0.1.133— y se ancla en
identidades y no en instantáneas: Grid `(nx+1)(ny+1)(rinc+1)`, Block
`num_surfaces`, Slope `num_surfaces` (el muestreo; el refinamiento no cuenta),
Annealing `K × Ngen`, Particle Swarm `num_iterations × num_particles`, y en Path
`attempts − total_count == focus_rejected`. Dejarlo a 0 en cinco de las siete
repetía la forma exacta del defecto de v0.1.83: un denominador que desaparece.
**La fusión paralela suma el campo nuevo**, o una rejilla en `ProcessPoolExecutor`
lo perdería en silencio — el mismo fallo de clase que los 1697 círculos.

**`optimize.py` usa dos frases para dos hechos distintos.** `error` conserva su
nombre porque la acción de menú de la interfaz cortocircuita sobre ella; el
matiz va en `start_invalid`, y la frase del segundo caso dice que **no es un
dato que falta: es la respuesta**. Además anota `start_densified_to` cuando
densificó, y **devuelve la superficie que evaluó** —la densificada— en vez de la
original: hasta ahora el retorno describía una superficie distinta de la de su
propio resultado, y quien archivara las dos guardaba dos respuestas a dos
preguntas.

**`BaseSearch._optimize_result` y su gemelo multimodal dejan de callar.** Fundían
`res is None` y `not res.is_valid` en un `continue` mudo mientras la acción de
menú **sí** avisaba. Ahora cuentan las tres causas aparte y emiten **una** nota
por método, **solo si ocurrió** —regla 7 al revés: una nota en todos los
análisis es ruido, que es el criterio de las notas de v0.1.143 y v0.1.151—.
Inglés llano en `result.notes`, sin `tr()`: el motor no importa `ogr_gui`.

**EL ESFUERZO SE PUBLICA EN CINCO CANALES**: `n_attempts` siempre y
`n_focus_rejected` solo si hubo alguno en el HDF5 (precedente de
`n_user_surfaces`), una columna *Attempted* en el CLI y otra en el informe PDF,
dos frases traducidas en la interfaz —el panel de interpretación y *Summary of
Invalid Surfaces…*, que es una acción que **ya existía y ya estaba en la barra**,
así que la regla 3 no pide ninguna acción nueva— y dos claves nuevas en los
resultados del banco.

## LO QUE SE HA HECHO EN EL BANCO (fuera de git)

- **`_tools/censo_presupuesto_d160.py`**, nuevo y SOLO MIDE. Enumera desde el
  bloque `no_circular` de cada `referencia.json` y **no por un glob de nombres**:
  la primera versión de la comprobación de cierre sí globeaba, y veía **34 de
  38** — se dejaba fuera el 057, el 020, el 075 y el 103, cuyos archivos se
  llaman de otra manera. Un censo por nombre se equivoca en silencio.
- **`ejecutar_caso.py`** archiva `intentos` y `rechazos_foco`, siempre, incluso
  a cero. Y ofrece la superficie crítica **sin redondear** por un parámetro
  opcional, **no** por una clave de `datos`: `datos` se serializa a JSON en
  varios sitios y con `--sin-optimizar` nadie la retiraría.
- **`ejecutar_no_circular.py`**: `_polilinea` rechaza lo que no es una polilínea
  por **lista blanca** —una lista negra se queda corta en cuanto nazca un tipo
  nuevo, y el modo de fallar volvería a ser entregar en silencio algo que no se
  puede optimizar—; los avisos distinguen las dos causas leyendo las claves
  nuevas de `rep.notes`; y el **reintento dirigido** de D163.
- **`generar_comparativa.py`**: `marca_opt` con sus tres marcas, la frase del
  renglón «Medido con» **generada** en vez de cableada, y una columna
  **`Version` AL FINAL**. Al final y no en cualquier otro sitio:
  `balance_evaluaciones.filas()` parsea por **índices posicionales** (`c[12]` es
  el Estado) y el archivo vivo ya tiene filas de 14, 13 y 4 celdas, así que una
  columna intercalada habría corrompido **en silencio** toda comparación contra
  las veinte instantáneas anteriores. Comprobado después: el recuento de estados
  de las dos tablas es idéntico (258 OK, 104 NO REPRODUCIBLE, 101 REVISAR).
- **`balance_evaluaciones.py`** lee esa columna y publica cuántos pares tienen
  los dos lados medidos por la **misma** versión — el cero falso de D101, D103,
  D118, D127, D129 y v0.1.175 convertido en aviso automático. **Sin bandera que
  lo apague**: una medida que se puede apagar no es una medida.
- **`verificar_cierres.py`**: `d160`, `d161` y `d162`, que antes devolvían
  `SIN CRITERIO`.

## LAS DOS FICHAS QUE NACIERON Y SE CERRARON EN LA MISMA TANDA

Salieron las dos de refutar la premisa de D161 —las nueve filas sin
`fos_optimizado` tenían TRES causas y solo una era de motor—, y las dos son de
**BANCO**: el motor hace lo correcto en ambas. Se abrieron con su evidencia
antes de tocar nada (regla 6) y sus remedios entraron en esta misma tanda, así
que cierran aquí. Viven en **P0** («Higiene del banco, no toca el motor») y no
en P2 con su madre: lo que comparten con P0 es el código que se toca, no de
dónde nacieron.

- **D163 — CUBIERTO POR CÓDIGO.** El reintento dirigido. `ejecutar_caso` ofrece
  la superficie viva **por parámetro** y no por una clave de `datos`, que se
  serializa en cinco sitios y que con `--sin-optimizar` nadie retiraría; el
  reintento solo dispara cuando la partida redondeada no da resultado; y
  `partida_sin_redondear` declara en el archivo qué filas lo usaron, porque un
  reintento que no se declara es un número que nadie puede reproducir.
- **D164 — CUBIERTO POR CÓDIGO.** La guarda de `_polilinea`, por **lista
  blanca** y no negra: una lista negra se queda corta en cuanto nazca un tipo
  nuevo, y el modo de fallar volvería a ser entregar en silencio algo que no se
  puede optimizar. Su comprobación de cierre **mide donde se lee** —llama a
  `_polilinea` con la compuesta del 057 y exige que la rechace con motivo— y
  lleva su **control**: una polilínea de verdad tiene que pasar, o la guarda
  aprobaría rechazándolo todo.

## REPORTADO Y NO CORREGIDO (regla 6)

- **D163** — la optimización del banco no arranca de la superficie que la
  búsqueda encontró, sino de una **copia redondeada a 4 decimales**, y eso mata
  tres filas. **No es defecto de motor**: la regla que rehúsa una polilínea
  levantada sobre el terreno es correcta y está medida. Quitar el redondeo del
  todo re-rodaría **~79 de las 85 filas `path`** reproducibles, así que se ha
  puesto un **reintento dirigido** —primero la redondeada, bit a bit como
  siempre, y solo si no evalúa la viva—, que mueve exactamente las tres.

  **Pagado y medido**: re-corridos el 079 y el 085 con 0.1.187, **12 filas de
  método y CERO movidas** —`fos`, `generadas`, `validas`, `invalidas`,
  `inadmisibles` y la polilínea crítica idénticas a 0.1.185 en las doce—, y las
  tres filas rotas publican por fin su optimizado: **1,44447** (079·gle),
  **1,444129** (079·spencer) y **1,638576** (085·gle). El `null` de
  085·spencer **sigue ahí**, que es lo correcto: esa es la respuesta del método.
  `partida_sin_redondear` declara en el archivo cuáles usaron el reintento.

  **Y el efecto en la comparativa es mayor que el conteo**: el 079·caso2 pasa de
  **REVISAR a OK** en los dos métodos, con la desviación cayendo de **3,01 % a
  0,10 %** y de **3,19 % a 0,08 %**, y el 085·pasivo·gle de **15,75 % a 9,90 %**.
  Esas filas estaban comparando un mínimo **sin optimizar** contra la columna
  optimizada del manual, que es exactamente el sesgo al alza que
  `ejecutar_no_circular` existe para no cometer. Tres filas no-dato valían tres
  puntos porcentuales de desviación falsa.
- **D164** — el banco entrega a `optimize_surface` el **dibujo** de una
  superficie compuesta. Tampoco es de motor: `_surfaces_to_optimize` ya la
  descarta, y el docstring de `drawing_vertices` lo dice sin ambigüedad.
- **Las dos semánticas de «Number of Surfaces»** siguen sin reconciliar.
  Publicar los dos números hace la diferencia legible; no la elimina.
- **`max_attempts_factor` sigue sin ser un ajuste**: vive en el constructor de
  `PathSearch` y ni la interfaz ni el `.ogr` lo alcanzan. Subirlo a
  `SearchSettings` exigiría lector y test de regla 7, y el censo dice que hoy
  nadie lo necesita.

## ERRORES PROPIOS DETECTADOS ANTES DE PUBLICAR

1. **El desfase del 085 era un artefacto del medidor, y estuvo a punto de
   publicar una cuarta causa.** La primera medida dio **+2,6537 m** y
   **+4,5790 m**, que parecía otro mecanismo: `optimize._ground_y` recorre los
   vértices del External por x, y el del 085 es el cuadrilátero
   `[(15,10),(57,10),(57,30),(25,30)]`, así que leyó el **borde inferior**
   (`y = 10`) en vez de la cara `y = 2x − 20`. Contra el perfil superior del
   propio motor son **+1,0e-4** y **0,0**, y 085·gle resulta ser redondeo como
   el 079. Lo cazó el control: 085·bishop, en el mismo archivo y con el mismo
   redondeo, **sí** publica su optimizado.
2. **El vértice que el test levanta estaba hundido.** La primera versión de
   `test_optimize_start_v1187` puso el vértice a 6,3 creyendo que lo levantaba
   sobre la cara, y la cara está a 8,4 en esa x. La superficie evaluaba
   perfectamente y el assert lo cazó; ahora el terreno se **calcula**
   (`_face_y`) y el fichero lleva escrito por qué.
3. **El `d162` globeaba por nombre** y contaba **34 de 38** archivos no
   circulares: exactamente el defecto que la ficha denuncia, cometido en su
   propia comprobación de cierre. Ahora enumera desde `referencia.json`.
4. **La comprobación de la frase cableada denunciaba el arreglo.** Buscaba
   «nadie los volvio a correr» en todo el archivo, y el arreglo **cita esa frase
   en un comentario a propósito** —es la lección, y borrarla la perdería—. Ahora
   mira solo líneas de código.
5. **El foco no llegaba a la búsqueda.** El primer `test_search_effort_focus`
   añadía el objeto al **proyecto**, y `_focus_rejects` lee
   `self.focus_objects` de la **búsqueda**. No pasó en vacío porque los asserts
   `focus_rejected > 0` se negaron a pasar sin muestra: un censo cuyo
   denominador puede ser cero tiene que decirlo en el assert.
6. **La barra doble del heredoc, otra vez.** `"\\n"` no sobrevive a la
   herramienta —está escrito en AGENTS.md y en las notas— y el reemplazo falló
   silenciosamente hasta que se usó `chr(92)`. Y su hermana: una cadena de ancla
   que **cruzaba un salto de línea** (`el\núltimo número usado es…`) tampoco
   casaba, que es la trampa que el changelog de v0.1.180 ya tiene escrita.

## LOS TESTS

`tests/test_search_effort_focus_v1187.py`, **10 casos en cuatro clases**, todos
identidades entre números de la misma corrida: la población documentada del
grid, la resta de Path, el presupuesto de generación fijo de Block, y
`TestAWalkIsNotPopulation` con su guard-on-the-guard.

`tests/test_optimize_start_v1187.py`, **12 casos en cinco clases**. El primero
**ejecuta la refutación** de la premisa de D161 —todo candidato después del
primero se rechaza, y el paseo no se mueve— y `TestACompositeIsNotAPolylineAndIsNotWalked`
convierte la evidencia del 057 en invariante, incluido el docstring del que
depende el razonamiento. El anclaje del caso que rehúsa el rebanador es
**externo y medido**: la regla del problema 27 (Malkawi & Sarma 2001), no una
captura.

`tests/test_acads_validation_v178.py` — el alambre-trampa `attempts == 0` se ha
**cortado a propósito**, que es lo que su propia cabecera invitaba a hacer, y
sustituido por su contrario más un test del contador de foco. **Ni un solo
assert de factor de seguridad tocado.**

**Ninguno de los 22 casos nuevos fija un factor de seguridad contra una
instantánea.**

## VERIFICACIÓN

- Suite entera y sin argumentos: **4041/4041**, sin banner `FILTERED RUN`
  (0.1.186 traía 4018; los +23 son los 22 casos nuevos más el alambre-trampa
  desdoblado en dos).
- `generar_comparativa.py` + `balance_evaluaciones.py` contra
  `Evaluaciones/0.1.186`: **559 → 559 filas, 559 IGUAL, 0 sin pareja**, y el
  recuento de estados idéntico en las dos tablas, que es lo que prueba que la
  columna nueva no desplazó nada.
- A/B del 079 y el 085 re-corridos de verdad: **12 filas de método, 0 movidas**.
  Las dos claves nuevas cumplen `intentos − generadas == rechazos_foco` en las
  **doce**, incluidas las seis con `focus = 0` donde los dos valen cero, así que
  **la identidad se cumple sobre datos reales del banco** y no solo sobre el
  modelo del test. Y el 079·1 la confirma donde más importa: archiva
  `intentos = 100 000`, `generadas = 17 271` y **`rechazos_foco = 82 729`**, que
  es exactamente el 82 729 que el informe de D160 había deducido **restando**
  antes de que el campo existiera.
- **El reloj no midió nada, otra vez.** El 079·2 dio **471 s** contra 324 s
  archivados —un +45 % que parecía del motor y era contención mía—, el 079·1 dio
  **301 s contra 304**, y los dos del 085 salieron **más rápidos** (2462 → 1632
  y 1996 → 1514). Misma versión, cuatro archivos, factores de 0,66 a 1,45.
- Comparativa re-generada tras esa corrida: **559 → 559 filas, 556 IGUAL, 2
  MEJORA y 1 mejora**, 0 sin pareja — y las tres son **exactamente** las filas
  de D163.
- `verificar_cierres.py`: **D160 CUBIERTO POR TEST**, **D161 CUBIERTO POR TEST**,
  **D162 CIERRE DOCUMENTAL**, **D163 y D164 CUBIERTO POR CÓDIGO**. Las cinco
  retiradas al índice de cerrados,
  `PAQUETES` podado a mano y la cadena tachada — la arista
  `REQUIERE["D163"] = ["D161"]` se deja donde está, que es la convención.
- `auditoria_invariantes.py` a **0 ERROR** (748 hallazgos: 491 AVISO, 257 INFO,
  el mismo perfil que en 0.1.186). En la primera pasada dio **3**: dos eran la
  señal de retirar las fichas cerradas y el tercero era **la tercera vez que el
  lector de la comparativa se queda viejo por el mismo motivo** — reconstruía la
  celda con `fmt()` a secas en vez de por la función que la emite, y la marca
  nueva salió como «9 filas nuevas, 9 viejas». Los dos párrafos de al lado ya
  dejan esa lección escrita para `marca_pool` y `marca_adm`, y volví a pisarla.
- Instantánea `Evaluaciones/0.1.187`: **1674 archivos comprobados byte a byte**,
  17 de ellos escritos por esta versión.
- Y el contrato «solo mide» de las herramientas nuevas se respetó: el único
  `resultados*.json` tocado fuera de las dos corridas autorizadas es ninguno.

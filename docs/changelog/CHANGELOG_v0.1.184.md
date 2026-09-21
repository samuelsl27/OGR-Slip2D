# OGR Slip2D v0.1.184

**El bucle secante sobre λ deja de refinar una horquilla que ya no tiene
ningún λ dentro (D153).** El cambio son seis líneas de lógica duplicadas en
`spencer.py` y `gle.py`, una constante nueva en `interslice.py`, y un censo que
dice **cero** y que se publica **antes** que el arreglo, porque ése es
literalmente el orden que v0.1.180 dejó escrito al reportar este defecto y no
corregirlo.

---

## Lo primero, porque cambia el tamaño del encargo: el 30 % de la ficha no es el suelo del doble

La ficha D153 dice: *«57 llamadas a `_inner_solve`, y desde la 40 todos los λ
siguientes están a menos de 1e-12 del último. O sea 17 llamadas, el 30 %,
resuelven dos ramas para un λ que no se puede mover»*.

Los 57 reproducen exactos. El 17 **está medido con una ventana relativa de
1e-12**, que está cuatro órdenes por encima del suelo del doble (2⁻⁵² ≈
2,2e-16). Trece de esas diecisiete llamadas son **dobles distintos**: λ sí se
mueve ahí, sólo que muy poco. La frase «un λ que no se puede mover» es falsa
para trece de las diecisiete.

Reconstruido el estado de la horquilla vuelta a vuelta —y **validado bit a bit
contra el `lambda_bracket_width` que publica el propio motor**, que es lo que
hace creíble una reconstrucción— el suelo se alcanza en la **llamada 54**. El
ahorro real con el `max_iterations` de fábrica es de **3 llamadas de 57, el
5 %**.

Y la diferencia no es de contabilidad: las otras catorce **no se pueden
cortar**. Ahí todavía quedan dobles dentro de la horquilla, así que pararse
sería terminar el secante con muestreo pendiente, y **eso sí movería el
factor**. La guarda es exacta o no es nada.

## La segunda: lo que amplifica el defecto es `max_iterations`, y eso sí es un argumento

El suelo se alcanza en la pasada 48 **por geometría** —una horquilla de 0,2
partida por dos hasta el ulp de 0,54— y no por presupuesto. Así que el
desperdicio es `max_iterations − 47`. Medido sobre el testigo, con el corte
apagado y encendido:

| `max_iterations` | llamadas sin corte | llamadas con corte | `fos` |
|---|---|---|---|
| 50 (de fábrica) | 57 | **54** | 0.5559372612135651 |
| 75 (default de `base.py`) | 82 | **54** | idéntico |
| 100 | 107 | **54** | idéntico |
| 200 | 207 | **54** | idéntico |
| 400 | 407 | **54** | idéntico |

Con el corte, **el número de llamadas deja de depender del presupuesto**.
`max_iterations` es un ajuste que el usuario puede subir —y es justo lo que uno
sube cuando una superficie contesta «la horquilla de λ no cerró»— y pasada la
pasada 48 **no compra absolutamente nada**: sólo paga. Ése, y no el ahorro de
hoy, es el argumento de esta versión.

Y el A/B es limpio por una razón que conviene decir: `branch_budget(200) =
max(200, 400)` sigue siendo 400, así que mover el presupuesto **alarga el
secante y deja intacta la aritmética de todas las ramas**. Se mueve una cosa.

## EL CENSO, Y EL NÚMERO ES CERO

La ficha exigía, con estas palabras, que *«ese cero hay que publicarlo antes
que el arreglo»*, y que se midiera donde puede haberlo: **una búsqueda entera**,
no las críticas archivadas, porque las superficies que no cierran λ **no se
archivan**.

`_tools/suelo_horquilla_d153.py` (banco, SÓLO DE MEDIDA, molde de
`cierre_lambda_d146.py`) corre `build_search(proy, mid).run(proy)` **entero**
con el espía puesto. Dos decisiones de medida son portantes y van escritas en
su cabecera:

1. **`parallel_search = False`.** La rejilla se reparte con
   `ProcessPoolExecutor`, en Windows el arranque es `spawn`, y el trabajo de
   verdad ocurre en procesos hijos que no comparten la memoria del padre: un
   espía puesto en el padre vería una fracción y publicaría un número pequeño
   con la misma cara con que publicaría uno de verdad. Es la trampa que el
   censo de excepciones de v0.1.161 documenta.
2. **El disparo se cuenta por la anchura PUBLICADA**, con `math.nextafter`, y
   no por un contador cableado en el motor: un censo que mide el motor con un
   contador del motor no puede desmentirlo. Y **no** con el
   `eps · max(1, |λ|)` que la ficha proponía, que es **más laxo** —a `|λ| < 1`
   son dos ulps— y contaría superficies donde todavía queda un λ dentro. Medido
   sobre el modelo 059: por el criterio laxo salen 8 superficies y por el de la
   guarda 4.

Sobre el modelo 059 en código, búsqueda completa, 1795 superficies, con el
corte encendido y apagado y las dos corridas comparadas superficie a
superficie:

| | superficies | llamadas sin → con | ahorro |
|---|---|---|---|
| Spencer, motor enviado | 1795 | 16 077 → 16 077 | **0** |
| GLE, motor enviado | 1795 | 16 355 → 16 355 | **0** |
| Spencer, D145 apagado | 1795 | 17 854 → 17 841 | 13 |
| GLE, D145 apagado | 1795 | 17 540 → 17 522 | 18 |

**Sobre ESE modelo y con el motor que se envía la guarda no ahorra nada, en
ninguno de los dos métodos.** Las 4 superficies de Spencer que no cierran λ
tienen horquillas de 2,1e-2 a 1,3e-1, lejísimos del suelo; a `max_iterations`
200, las mismas 4 y el mismo cero. Con D145 apagado sí hay población: **4
superficies de 39** en Spencer y **5 de 23** en GLE.

**Pero un modelo no es el banco, y el banco contesta otra cosa** — que es
justamente para lo que se escribió la herramienta, y es la razón por la que no
se publicó el cero del 059 y se dio por hecho. `_tools/suelo_horquilla_d153.py`
sobre 20 problemas del banco, **32 filas, 123 710 superficies y 1 095 840
llamadas a `_inner_solve`**, cada fila corrida dos veces y comparada superficie
a superficie:

| | |
|---|---|
| superficies que no cierran λ | 25 |
| horquillas que **llegan al suelo** | **15** |
| superficies donde la guarda **corta de verdad** | **12** |
| llamadas ahorradas | **42** |
| **factores movidos** | **0** |
| **claves de `details` movidas** | **NINGUNA** |

Así que sobre el banco **la guarda sí dispara con el motor que se envía** —en
007, 009, 018, 019, 051 y 071, con Spencer y una vez con GLE—, al contrario que
la salida de D146, que estaba dormida. Y sobre una población real, no sobre un
testigo, **no se mueve ni un dígito publicado**: ni un factor de los 123 710,
ni una clave de `details` en ninguna de las siete filas donde el corte actúa.
Eso es lo que convierte «cero dígitos movidos» en una medida en vez de en un
argumento.

Las 15 y las 12 no son el mismo número **a propósito**: llegar al suelo es
condición necesaria y no suficiente, porque la guarda pide además que **los
dos** extremos superen la tolerancia y `details` sólo publica uno. La cuenta
por anchura es una **cota superior** y va etiquetada como tal; el número exacto
sale del A/B, donde un disparo es una superficie cuyo `iterations` cambia.

El censo lleva **su límite declarado**: un tope de 75 min que dejó **29
problemas sin medir**, del 097 en adelante, y el recorrido va de más barato a
más caro precisamente para que un corte deje el denominador grande y no una
esquina. Se dice porque un censo que no declara su límite se lee como si no lo
tuviera.

Y el dato que cierra la pregunta de «cero dígitos movidos»: en las cuatro
corridas —**7180 evaluaciones de superficie**— el factor no se movió en
**ninguna**, y **ninguna clave de `details` se movió en ninguna**.

## POR QUÉ ESE SEGUNDO CERO NO ERA OBVIO, Y CASI PUBLICO QUE SÍ LO ERA

La revisión del diseño encontró un camino por el que cortar **sí** podría mover
un número archivado, y tenía razón en el mecanismo: `GLESystem.branches`
incrementa `n_rescued` **una vez por LLAMADA** y no una vez por λ
(`interslice.py`), así que un λ colapsado cuya rama necesite el rescate sumaría
uno por cada vuelta inútil, y `lambdas_rescued` se publica en `details` y lo
archiva el banco. Mi afirmación de «cero dígitos movidos» descansaba sobre el
testigo, donde vale 1 con corte y sin él.

La respuesta es empírica y está arriba: sobre 7180 evaluaciones, ninguna clave
se movió, `lambdas_rescued` incluida. O sea que el riesgo era real y la
población no lo realiza. Las dos mitades van dichas, porque publicar sólo la
segunda dejaría el argumento apoyado en un testigo.

Los cuatro contadores `lambdas_lost_to_*` no pueden moverse **por
construcción**, y eso sí es argumento y no medida: para ser extremo de una
horquilla un λ tuvo que pasar `branch_pair_ok`, o sea que sus dos ramas vienen
con estado y convergidas, y las guardas de `branches` salen antes de tocar esos
cuatro contadores.

## EL CAMBIO

**`ogr_slip2d/interslice.py`** — constante nueva `LAMBDA_BRACKET_FLOOR_CUT`,
puesta detrás de `LAMBDA_EDGE_RECOVERY` para que la familia de λ quede en orden
cronológico D148 → D149 → D153, con su bloque `#:` de partida de nacimiento:
por qué una prueba de punto medio y no una constante, por qué los dos extremos
tienen que superar la tolerancia, el censo que dio cero, la tabla del
presupuesto, y qué no toca. Se lee **en tiempo de llamada** con el molde de
`BRANCH_RESCUE`.

**`spencer.py` y `gle.py`** — la misma guarda, duplicada, junto a la salida por
`g` degenerada:

```python
            if interslice.LAMBDA_BRACKET_FLOOR_CUT:
                mid = 0.5 * (lam_lo + lam_hi)
                if ((mid == lam_lo or mid == lam_hi)
                        and abs(g_lo) >= self.tolerance
                        and abs(g_hi) >= self.tolerance):
                    break
```

**No lleva ninguna constante**, y eso es deliberado. La rejilla de los dobles
ya es relativa a la magnitud, que es lo que AGENTS.md pide de una tolerancia, y
la partida de nacimiento de la prueba es una línea: bajo redondeo al par más
próximo, el punto medio colapsa sobre un extremo exactamente cuando no queda
ningún doble estrictamente entre los dos. El `eps · max(1.0, abs(lam_lo))` que
pedía la ficha dispara una pasada antes y deja de ser una identidad para
comprarla.

Va **después** de `iterations += 1` y **después** del test de `1e-12`, para que
las dos salidas por colapso cuenten su pasada igual y `iterations` siga
significando una sola cosa —«muestras más vueltas entradas»—, que es la
confusión que D146 gastó una versión en deshacer.

## LA PRUEBA DE IDENTIDAD, QUE ES LO QUE AUTORIZA EL CORTE

Cuando no queda ningún doble dentro, el estado del bucle es un **punto fijo**:

1. `lam_new` cae en `[lam_lo, lam_hi]` y por tanto redondea a uno de los dos
   extremos. Para el paso secante, con `g_lo·g_hi < 0` se tiene
   `|g_hi − g_lo| = |g_hi| + |g_lo|`, así que la corrección tiene el signo de
   la anchura y módulo **estrictamente menor** que ella: el valor exacto cae en
   el intervalo abierto. La bisección también, porque la suma exacta está en
   `[2·lam_lo, 2·lam_hi]` y el `×0.5` final es exacto.
2. `solve` es determinista. El único atributo de `GLESystem` que realimenta el
   cálculo —y no cuenta, sino que gobierna un `return None, None`— es `strict`,
   y **sus cuatro asignaciones están todas antes del bucle** (`spencer.py:158`
   y `:236`, `gle.py:246` y `:324`). Luego `g_new` es exactamente `g_lo` o
   `g_hi`.
3. Si `lam_new == lam_lo`: mismo signo, rama `else`, `lam_lo = lam_lo`.
4. Si `lam_new == lam_hi`: signo opuesto, `lam_hi = lam_hi`.
5. La única salida que aún podría dispararse es `abs(g_new) < tolerance`. **Por
   eso la guarda exige que los dos extremos superen la tolerancia**: los dos
   `g` con que **nace** una horquilla nunca se contrastan contra ella
   —`_first_bracket` sólo pide un cambio de signo, y el filtro de muestreo es
   `0.05 < F < 50`—, así que por debajo de la tolerancia la guarda **se aparta**
   y el bucle hace lo de siempre. Ese caso se deja intacto en vez de razonarse.

Y hay una quinta razón para ese conjunto de tolerancia que sólo se ve mirando
el caso degenerado: con `g_lo` exactamente 0, `g_lo * g_new` es `0.0`, que **no
es `< 0`**, se tomaría la rama `else` y se escribiría `lam_lo = lam_hi`, o sea
la horquilla colapsada **sobre el otro extremo** — otro λ y otro factor. Hoy no
puede pasar (el test de signo es estricto y la tolerancia es positiva), y la
guarda no se apoya en que siga siendo así.

## QUÉ SE MUEVE, CON LA MEDIDA DELANTE (regla 7)

Sobre el testigo, corte encendido contra apagado:

- `fos` **idéntico bit a bit**, 0.5559372612135651;
- `converged`, `reason`, `admissible`, `admissibility_note`, `is_valid`:
  idénticos;
- **las dieciocho claves de `details`: idénticas**, `lambdas_rescued` incluida;
- `iterations`: **56 → 54**;
- `error_message`: cambia, y **sólo** en el número que cita dentro de su frase
  («…after 54 iterations» en vez de «…after 56»), porque lleva un `%d` de
  `iterations`. `LEMResult.to_dict` lo archiva como `error`, así que se dice.

Son exactamente dos cosas. Que `iterations` se mueva es lo que salva la regla 7:
si no se moviera nada, el ajuste no haría nada.

## EL TESTIGO DE GLE, QUE HUBO QUE IR A BUSCAR

Sobre el círculo de la figura 59.2, **GLE cierra λ en diez llamadas y no llega
nunca al suelo**. Poner la guarda en `gle.py` con el testigo de Spencer por
todo aval habría sido meter en el gemelo un ajuste que ningún caso de ese
método alcanza — la regla 7 al revés.

Así que se fue a buscar, recorriendo una búsqueda entera del mismo modelo con
D145 y D153 apagados: de las 23 superficies de GLE que no cierran λ, **6 están
en el suelo**, y el test toma la primera,
`(-32.0, 69.66666666666666, 78.86964881062671)`. Allí el corte se comporta
igual: 58 → 55 llamadas, `fos` 0.4263805139365542 idéntico, ninguna clave de
`details` movida, y a presupuesto 200, 208 → 55.

## REPORTADO Y NO CORREGIDO (regla 6)

**D159 — Spencer y GLE re-resuelven dos veces el λ que acaban de resolver.**
Encontrado midiendo D153, y es **veinte veces mayor**. Sobre una búsqueda
entera de Spencer: **17 872 pares de rama para 1795 superficies**, y exactamente
**1795** de ellos (10,0 %) **no pasan por `_inner_solve`** — son el
`system.states(lam_lo)` de `spencer.py:402`, porque `GLESystem.states` no
cachea nada. Y otros **1795** (10,0 %) son el `solve(lam_lo)` de
`spencer.py:385`, que recalcula `ff_lo, fm_lo`, valores que el bucle mantiene
en paridad con `lam_lo` en las líneas 349, 375 y 382 y que **nunca lee**. Total:
**~20 % de un Spencer completo** re-resolviendo lo que el método ya tiene.

El comentario de `spencer.py:393-399` justifica el primero diciendo que `g_lo`
«puede ir un refinamiento atrasado», y **esa cadena nunca está atrasada**: las
tres asignaciones son en bloque. No se corrige aquí porque quitarlo mueve los
contadores que `details` publica y el banco archiva, así que pide su propio A/B
y su propia corrida. Y hay una señal bonita de que el diagnóstico es correcto:
tras el corte de D153, **la única llamada que todavía repite un λ exactamente
es ésa**, y el test lo fija.

**El `1e-12` de `abs(g_hi - g_lo)`** sigue siendo el único número de este bucle
sin nombre, sin constante y sin ficha `#:`, en un proyecto donde el resto tiene
partida de nacimiento medida. Es exactamente lo que D120 dejó dicho del 0,02.
No se toca, y hay un caso que deja constancia de que se vio.

**La asimetría del camino de rescate del par.** `spencer.py` exige
`branch_pair_ok(ff, fm) and ff > 0 and fm > 0` al entrar, y el re-test interior
tras la bisección exige **sólo** `branch_pair_ok(ff, fm)`: un valor no positivo
entraría como extremo de horquilla por el camino de bisección. Hoy no puede
pasar porque `interslice.py` rechaza `f_new <= 0.0` aguas arriba. Idéntico en
`gle.py`.

**Los documentos de auditoría del banco caducan con la versión.** `d144`,
`d146`, `d148` y `d149` construyen el nombre del `.md` desde la versión
**instalada**, así que a 0.1.183 buscaban `*_v1183.md` y sólo existía
`branch_state_v1183.md`: las otras tres estaban en rojo por un archivo que
falta, no por una medida. Esta versión regenera el censo de D146
—`lambda_closure_v1184.md`, **344 filas, 0 que no cierran**, o sea **sin filas
nuevas**, que es lo que la verificación de D153 pedía— y con eso `d146` vuelve
a **CUBIERTO POR TEST**. `d144`, `d148` y `d149` siguen en rojo por la misma
causa y se dice, en vez de dejarlo sin decir.

Un dato de paso de ese censo, porque cambió y no lo cambia esta versión: sus
**descuadradas de control pasan de 8 a 6**. No es un arreglo de aquí; es que la
instantánea del banco no es homogénea y v0.1.181 re-corrió filas que antes
arrastraban una versión vieja. Se nombra para que nadie lea ese 6 como un
efecto del corte.

## ERRORES PROPIOS DETECTADOS ANTES DE PUBLICAR

1. **El paréntesis de la guarda.** La primera forma era
   `A and (B or C) and D and E` escrita sin los paréntesis de `B or C`, y `and`
   liga más que `or`: la rama `mid == lam_lo` se habría saltado el conjunto de
   tolerancia **entero**, que es justo donde hace falta. Con `|g_lo| < tol`
   habría cortado una superficie que iba a converger, convirtiendo un
   `converged=True` sin mensaje en un veto con `error_message` — y
   `error_message` **excluye la superficie de `SearchResult.critical`**. Un
   paréntesis mal puesto podía hacer desaparecer una superficie de una
   búsqueda.
2. **Leí «1 de 39» donde eran 8 de 39**, porque imprimí las ocho primeras filas
   del censo y conté sobre ellas. Por eso el censo publica el denominador y las
   filas con nombre y no una cabecera. (Y el número de la guarda de verdad no
   es ninguno de los dos: son 4, porque el criterio con que conté era el laxo.)
3. **Seis casos del test pasaban en vacío.** Llevaban una puerta
   `if not _cut_exists(): return` que yo había puesto por prudencia, y contra el
   árbol de 0.1.183 pasaban sin medir nada: el reparto decía 3 fallos de 38.
   Quitadas las puertas, esos casos fallan **sobre un número** (0 llamadas
   ahorradas en vez de 3) y el reparto pasa a 9 de 38. Una puerta defensiva que
   convierte una discriminación fuerte en un verde silencioso es peor que no
   tener el caso.
4. **Dije «las quince claves de `details`» y son dieciocho.** Contadas de
   memoria sobre el código en vez de medidas sobre el resultado.
5. **`_trace` quedó con un parámetro `method_id` que su cuerpo no honraba**, en
   un paso intermedio: la firma prometía dos métodos y dentro seguía cableado
   `Spencer`. Retirado — el testigo de GLE es otro círculo y merece su propio
   ayudante en el fichero nuevo.
6. **Lancé una medición de fondo y a la vez corrí la suite filtrada**, que es
   literalmente el ruido autoinfligido que AGENTS.md describe: dos procesos
   peleándose por los mismos núcleos.
7. **Abrí la ficha nueva como D158, y D158 ya existía.** El número libre que yo
   tenía anotado era de antes de v0.1.183, que gastó uno. Lo cazó ir a leer la
   cabecera del índice —«último número usado es D158 y el siguiente libre
   D159»— antes de escribir, y no la serie de memoria. El índice avisa además
   de que un número libre no prueba que el defecto no esté ya abierto: hay que
   grepear el SÍNTOMA. Hecho —`states(lam_lo)`, `solve(lam_lo)`, `ff_lo`— y no
   lo estaba; la única mención cercana es la de D156, que habla de
   `system.states(lam_star)` en la OTRA salida y por otro motivo.
8. **Publiqué «el censo dice cero» antes de que el censo del banco existiera.**
   El cero era del modelo 059 en código, y lo escribí como si fuera del banco.
   Lo desmintió el propio censo en su tercera fila: el 007 tiene **2**
   superficies en el suelo. La frase estaba en el changelog y en la cabecera
   del test, y las dos se acotaron a lo que de verdad habían medido **antes**
   de que llegaran los números, no después.
9. **El control del censo comparó dos familias de búsqueda y me dio un susto
   de +44 %, y mi arreglo fue peor que el fallo.** El 047 salía con el crítico
   a +44,39 % del archivado, y el número coincidía **exacto** con el del
   modelo SIN bulones, lo que apuntaba a soportes perdidos en el camino de
   `run()`. No lo eran: los bulones cargan (2 soportes) y la superficie
   archivada, evaluada por su propia puerta, da 0,8665459 contra el 0,866564
   archivado. Lo que pasa es que la crítica archivada del 047 son **dos
   vértices con `angulo_deg`** —una superficie DADA, de las 18 que el banco
   publica así— y el modelo declara búsqueda de rejilla circular.
   **Y entonces me equivoqué en la corrección**: deduje «la crítica archivada
   es no circular ⇒ el control no aplica» y eso dejó en blanco **DIEZ
   controles válidos**, porque `build_search` no monta siempre una rejilla:
   monta la que el `.ogr` declara, y el 007 y el 009 corren `BlockSearch` con
   crítica poligonal y control +0,0000 %. La regla correcta compara la familia
   **declarada** con la **archivada**, y deja fuera una sola fila. Un arreglo
   que apaga diez medidas buenas para tapar una mala es peor que la mala.
10. **Y las dos filas que siguen descuadradas no son un defecto**: el 103 y el
   104 declaran `ParticleSwarmSearch`, que es **estocástica** y no reproduce
   su propio mínimo entre dos corridas. Va escrito en el informe, porque un
   +0,53 % sin esa frase al lado se lee como un hallazgo.

## EL TEST

`tests/test_lambda_floor_v1184.py`, **19 casos en seis clases**, y ninguna
aserción fija un factor de seguridad contra un valor de referencia: todo es un
A/B en un proceso, una identidad, una adyacencia de dobles (`math.nextafter`) o
un recuento de llamadas que el motor hizo de verdad.

El ancla absoluta **no se copia aquí a propósito**: ya existe y es mejor que una
instantánea nueva, porque `test_lambda_closure_v1180.test_the_factor_does_not_move`
fija 0.5559372612135651 sobre este mismo testigo y **se escribió antes de que el
corte existiera**. Si el corte mueve el factor, ese caso se pone rojo.

La fixture **se reusa** de `test_lambda_closure_v1180.py` en vez de duplicarse:
`_runner._load_module` deja cada módulo en `sys.modules` bajo su `stem` y el
cruce entre ficheros de test ya es patrón asentado en la suite. Duplicar el
talud sería duplicar además la trampa de D154 que su docstring documenta.
`_slope` gana un parámetro `max_it` que, **omitido, no toca el ajuste**, de modo
que toda llamada escrita antes construye el mismo proyecto byte a byte.

Contra el árbol de 0.1.183 con los tres ficheros de motor guardados, **fallan 9
de 38 y pasan 29**, con el reparto NOMBRADO en la cabecera: **ocho** fallan
sobre una diferencia medida y **uno** por la ausencia de un símbolo, que es
discriminación débil y va etiquetada como tal. Las cuatro de
`TestTheCutChangesNoDigit` pasan en los dos árboles **a propósito** —son la
identidad, y sin constante que apagar comparan una corrida consigo misma—, y
`test_without_the_cut_a_bigger_budget_buys_only_calls` es CONTROL verde en los
dos: mide el punto fijo **sin necesitar el interruptor**, que es lo que lo hace
control de todo lo demás.

### Re-anclaje

`test_lambda_closure_v1180.py` estaba **escrito para este día**: su cabecera
decía *«so the day someone adds the cut this file tells them what they
changed»*. Su caso `test_the_loop_keeps_solving_after_the_bracket_stops_moving`
asertaba `wasted > 10` con la ventana de 1e-12 mientras su docstring hablaba del
«suelo del doble» — y con la guarda puesta **seguía pasando, por el motivo
equivocado** (13 > 10). Se parte en dos y se re-ancla sobre el criterio
correcto:

- `test_the_bracket_floor_no_longer_re_solves_the_same_lambda` cuenta las
  llamadas que repiten un λ **exactamente**: eran 4 y ahora es 1;
- `test_the_fichas_thirty_per_cent_was_never_the_floor` deja en el registro que
  la mayor parte de la cola de la ventana son dobles distintos.

El fichero pasa de 18 a 19 casos, y la cabecera lo dice **sin retocar el
reparto histórico medido contra 0.1.179**, que es un hecho de su día.

## VERIFICACIÓN

- **Suite entera y sin argumentos: 3963/3963**, en verde y sin banner
  `FILTERED RUN`, con la máquina sola. 0.1.183 cerró en 3943; los +20 son
  exactamente los 19 casos del fichero nuevo más el caso de v1180 que se partió
  en dos al re-anclarlo.
- A/B en un proceso con el interruptor, sobre los dos testigos: **las dieciocho
  claves de `details` idénticas**, el factor bit a bit, `iterations` y las
  llamadas menores.
- Censo de búsquedas enteras sobre el banco con su denominador, su control y su
  **límite declarado**: `docs/audits/lambda_floor_v1184.md`.
- `auditoria_invariantes.py` a **0 ERROR** (748 hallazgos: 491 AVISO, 257 INFO),
  los mismos que en 0.1.183.
- `verificar_cierres.py D153` → **CUBIERTO POR TEST**, y **comprobado que
  DISCRIMINA**: con los tres ficheros de motor guardados contesta
  `NO SE SOSTIENE`. Sin esa mitad, un verde no distingue un motor arreglado de
  una medida que dejó de medir.
- Instantánea `Evaluaciones/0.1.184` congelada, **1640 archivos comprobados
  byte a byte**, y su reparto de versiones deja el ancla de 0.1.173 en 126,
  que es la comprobación de que no se movió nada.
- **El banco no se re-corre, y es una medida y no una omisión**: sobre 123 710
  superficies el corte no movió un solo factor ni una sola clave de `details`,
  y las 12 superficies donde dispara sólo mueven `iterations` y el número que
  el mensaje cita.

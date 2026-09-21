# OGR Slip2D v0.1.186

**Una ficha cerrada, dos medidas, y de las tres hubo que corregir primero la
premisa con la que estaban escritas.** D159 decía que quitar la doble
resolución de λ «mueve los contadores que `details` publica y que el banco
archiva», y por eso exigía una corrida de banco: es cierto del arreglo que la
ficha describe al pie de la letra y **falso del que se ha hecho**. D158 se
publicaba a sí misma como **dormida** —«0 ramas con el par asentado de 36»—, y
ese cero estaba medido sobre críticas archivadas, que es la cota inferior que
la propia ficha advierte: sobre búsquedas enteras el cubo que la ficha titula
sale **11 y no 0**. Y D157 pedía un censo cuya tercera pregunta **no puede dar
otra cosa** que el 100 %, por construcción.

El cambio de motor vive entero en `interslice.py` y son **doce líneas en el
cuerpo de `GLESystem.states`** —la consulta, el vaciado por firma y el
guardado— más el interruptor, la tupla de diez nombres, un ayudante de tres
líneas, dos slots y dos asignaciones en `__init__`. Las otras siete líneas de
`_solve_states` no son nuevas: son la aritmética que ya estaba, movida para que
el A/B pueda apagar el recuerdo sin que exista una segunda copia de esas seis
llamadas en ningún sitio. El fichero crece 150 líneas porque el bloque `#:` que
lo explica ocupa 120.

**Ni un factor, ni una clave de `details`, ni un contador, ni una fila del banco
se mueven**, y eso está medido y no supuesto.

---

## D159 — LA CACHÉ NO PUEDE MOVER UN CONTADOR, Y ESO ES LO QUE EVITA LA CORRIDA DE BANCO

La ficha ofrece dos arreglos y los trata como intercambiables. No lo son, y la
diferencia es exactamente la que decide si hace falta pagar una corrida del
banco:

* **`ff_final, fm_final = ff_lo, fm_lo`** —el que la ficha escribe— **quita una
  llamada a `GLESystem.branches`**, y con ella un incremento de contador. Eso
  sí mueve `lambdas_rescued` y los `lambdas_lost_to_*`, y por eso la ficha
  concluye que «esto sí pide un A/B del banco de verdad y su propia corrida».
* **Una caché por λ dentro de `states`** no quita ninguna llamada: el
  `solve(lam_lo)` del cierre pasa a ser un **acierto**, no una supresión.

El razonamiento completo son tres pasos, y el primero ha dejado de ser una
frase:

1. **todo incremento de contador vive dentro de `GLESystem.branches`** —
   `n_inadmissible`, `n_thrust_overflow`, `n_passes_exhausted`, `n_stalled`,
   `n_rescued`, `n_thrust_rejected` y la escritura de `thrust_rejected_pairs`—,
   y eso lo comprueba **por AST**
   `test_lambda_state_cache_v1186::test_every_counter_moves_inside_branches`;
2. lo que `branches` incrementa es función pura de los dos `BranchState` que
   `states` le devuelve: lee `state is None`, `converged`, `abandoned`,
   `passes`, `rescued`, los dos `fos` y `thrust_is_admissible(force)`. **Ninguna
   de esas lecturas pregunta cómo se produjo el objeto**;
3. luego `branches` se entra el mismo número de veces con los mismos objetos.

### La advertencia de la ficha sobre `strict` no aplica a esta caché

La ficha avisa: «ojo con la caché, tiene que invalidarse si `strict` cambia,
porque `strict` gobierna un `return None, None`». Medido: **`self.strict` se lee
en un solo sitio de todo el paquete**, y está **dentro de `branches`**, aguas
abajo de `states`. `states` no lo lee. El aviso sólo valdría para una caché del
valor de retorno de `branches`, que es otra cosa.

### Dos pruebas que ya corrían y que demuestran el punto sin haber sido escritas para eso

`tests/test_branch_rescue_v1176.py::test_a_loss_is_counted_even_when_the_partner_is_none`
pide `states(1.0)` y después `branches(1.0)` **sin tocar nada en medio**, y
exige que el contador suba. Y `tests/test_max_iterations_scope_v1173.py` hace lo
mismo con `n_passes_exhausted`, calculando el esperado **de los estados que
`states` devolvió**. Las dos son literalmente el patrón «acierto de caché y el
contador sube igual», y las dos siguen verdes.

### La otra premisa falsa: no hay arranque en caliente

La ficha teme que contar pares «sobreestime el tiempo por un factor grande»
porque el par final «arranca de un `initial_fos` pegado al punto fijo». **No lo
hace**: `states` pasa siempre `self.initial_fos`, escrito una sola vez en
`__init__` y nunca más, así que toda rama de todo λ arranca de la misma F y una
repetición cuesta **exactamente** lo que costó la primera, a la pasada.

Medido sobre una búsqueda de rejilla completa del modelo del 059 con Spencer, un
proceso, 1795 superficies:

| | |
|---|---|
| llamadas a `states` | 17 872 |
| de ellas, un λ ya resuelto por ese sistema | **3578 (20,0 %)** |
| pasadas de rama totales | 757 378 |
| gastadas en repeticiones | **144 114 (19,0 %)** |

20,0 % de las llamadas son 19,0 % de las pasadas. El recuento **no**
sobreestima, y la diferencia entre los dos números no es un arranque caliente:
es qué λ resultan ser las repeticiones.

### Que es una identidad: medido, no argumentado

Comparando cada repetición con el primer cálculo de ese λ **campo a campo y
lista a lista** —`fos`, `converged`, `passes`, `abandoned`, `rescued`,
`normals`, `resisting`, `boundary_e`, `boundary_x`—: **3578 de 3578 idénticas
bit a bit, 0 distintas**.

Esa determinación era, hasta esta versión, una afirmación del docstring de
`thrust_rejected_pairs` (v0.1.182) **de la que el paquete ya dependía** —
`recover_thrust_edge` se fía de un par registrado en una pasada anterior
precisamente por ella— y que nadie había ejecutado nunca. Ahora la ejecuta un
caso.

### El cambio

`GLESystem` gana dos slots, `states` se parte en `_solve_states` (la aritmética)
y `states` (el recuerdo), y aparecen dos símbolos nuevos:

* **`LAMBDA_STATE_CACHE`**, leído en tiempo de llamada con el molde de
  `BRANCH_RESCUE`. Lleva interruptor porque el A/B tiene que poder apagarlo en
  el mismo proceso, que es la única medida que este proyecto se cree; y no es un
  ajuste que no hace nada (regla 7) porque mueve el **coste**, que está medido.
* **`_BRANCH_SWITCH_NAMES`** y `_branch_switches()`: los diez globales que el
  **cuerpo** de `solve_branch` lee en tiempo de llamada. Si la firma cambia, la
  caché se vacía.

La clave es **el doble crudo de λ, sin redondear**. `thrust_rejected_pairs`
redondea a 12 porque su trabajo es contar **inclinaciones** y dos dobles
adyacentes son una inclinación; el de la caché es el contrario, devolver
exactamente lo que `solve_branch` devolvería, y dos λ a un ulp dan
`lambda_boundary` distintos. Redondear aquí los fundiría, y desde el corte de
D153 la secante camina a propósito sobre dobles adyacentes —
`test_lambda_floor_v1184` **afirma** que dentro de la ventana de 1e-12 hay más
de diez dobles distintos.

### El riesgo que la caché sí tiene, y por qué la guarda es la firma

Un `GLESystem` **capturado** que sobrevive a un cambio de interruptor devolvería
el par viejo en silencio. No es hipotético:
`tests/test_branch_rescue_v1176.py::test_a_stall_is_counted` construye el
sistema con `_system_091()`, que resuelve la rejilla **fuera** de cualquier
context manager, y después pregunta por `branches(0.40)` **dentro** de
`_unrescued()`. Medido: λ = 0,40 es nodo de `_LAMBDA_SHAPE` y queda cacheado, y

| | `converged` | `rescued` | `passes` | `fos` |
|---|---|---|---|---|
| rescate ON | True | True | 45 | 0,970571490929 |
| rescate OFF | False | False | 81 | 1,11632765164 |

No es una diferencia de redondeo: es otra respuesta. Se eligió la firma y no un
interruptor que haya que acordarse de apagar —**olvidable**, y el que escriba el
próximo test que capture un sistema no se acordará— ni un `with` alrededor del
cuerpo de los dos métodos —que re-indenta unas 300 líneas por un problema que
sólo tiene el código de medida—. Su único punto débil, que la lista se quede
vieja cuando nazca el interruptor siguiente —el fallo de los siete sitios de
versión, tres congelados diecisiete versiones—, lo cierra un caso que la compara
**por AST** con lo que el cuerpo de `solve_branch` realmente lee.

Y `test_the_guard_is_load_bearing` lo **demuestra** en vez de argumentarlo:
anulando la firma, el lado «sin rescate» devuelve la rama **rescatada**.

### Un hallazgo lateral: `STALL_PATIENCE` no es un interruptor de tiempo de llamada

Al escribir la firma por AST salió que `MAX_PASSES`, `F_MIN`, `F_MAX` y
`STALL_PATIENCE` aparecen **sólo** en las expresiones por defecto de
`solve_branch`, que Python evalúa en tiempo de `def`. Parchear el atributo del
módulo después del import **no cambia nada**. Ningún test lo hace hoy —sólo los
afirman— pero un lector podría creer lo contrario, y por eso quedan fuera de la
firma con su razón escrita y un caso que vigila que sigan siendo esos cuatro.

### El A/B de tiempo, publicado aunque el reloj diga menos

`ON → OFF → ON`, mismo proceso, espalda con espalda, sobre la búsqueda entera:

| corrida | segundos | pares de rama | crítico |
|---|---|---|---|
| ON (control 1) | 38,0 | 28 588 | 0,202605263147 |
| OFF | 49,5 | 35 744 | 0,202605263147 |
| ON (control 2) | 41,3 | 28 588 | 0,202605263147 |

El número sin ruido es el de pares: **−7156 de 35 744, el 20,02 %**, idéntico en
los dos controles. Los dos controles de tiempo difieren entre sí un **8,7 %** y
el efecto contra su media es del 19,9 %, o sea unas 2,3 veces esa dispersión: el
reloj distingue un efecto de este tamaño pero no fija su valor, y AGENTS.md dice
que ahí manda el razonamiento sobre el trabajo suprimido. Aquí ese razonamiento
es exacto y no una estimación.

### El ahorro por superficie NO es una constante, y eso costó un aserto

`d159()` empezó exigiendo cuatro llamadas menos —dos pares— y sobre la crítica
archivada del 059 la caché ahorra **seis**. La causa, medida: **una llamada a
`evaluate_surface` levanta DOS `GLESystem`** para una misma superficie, y los
repetidos caen donde caen —λ 0,273195 pedido tres veces en el primero, λ 0,05625
dos veces en el segundo: tres aciertos, seis llamadas—. El aserto se cambió por
la **identidad** —*un acierto vale exactamente un par*—, que es lo que de verdad
es cierto y no se pudre cuando cambie la forma de la búsqueda.

### Un caso re-anclado porque el refactor lo rompió sin romper su invariante

`test_max_iterations_scope_v1173::test_and_the_system_carries_it_down_to_every_branch`
contaba `max_passes=self.max_passes` **dentro de `states` por su nombre**. Al
partir el método en dos, ese recuento bajó a cero con el invariante de D117
intacto. Un caso que se pone rojo porque un método se ha partido está anclado a
lo que no es, así que ahora pregunta por las **llamadas**: los dos `solve_branch`
de la clase, vivan donde vivan, pasan el presupuesto del usuario. Es
estrictamente más fuerte que el recuento que sustituye.

### La mitad documental

El comentario de D146 de `spencer.py` y su gemelo de `gle.py` llevaban cuatro
versiones justificando un gasto con una obsolescencia que no existe: «medido
sobre el par que produce el factor devuelto **y no sobre `g_lo`, que puede ir un
refinamiento atrasado**». `ff_lo` y `fm_lo` se escriben **en la misma sentencia**
que `lam_lo` en los tres sitios, así que la terna no puede desparejarse. Lo que
sí puede ir atrasado es `g_lo` frente a **`g_hi`**, que es otra afirmación. Es el
mismo patrón que D153 tuvo con su «30 %».

---

## D158 — LA SALIDA NO ESTABA DORMIDA: LO ESTABA EL MEDIDOR

La ficha publica «0 ramas con F y X asentados» sobre las 36 estancadas de
`censo_0.1.183.json`, y **ella misma dice por qué eso es una cota inferior**: ese
censo mide sobre **críticas archivadas**, y una crítica archivada es la
superficie que el banco guardó, no una de las miles que una búsqueda evalúa y
tira.

Instrumentando **búsquedas enteras** —`_tools/estancamiento_d158.py`, que SOLO
MIDE— sobre 35 filas de 22 problemas:

| | |
|---|---|
| ramas resueltas | 2 992 152 |
| aceptadas | 2 383 186 |
| perdidas por presupuesto | 10 913 |
| perdidas por desbordamiento de empuje | 179 541 |
| sin estado (`None`) | 357 976 |
| **cortadas por ESTANCAMIENTO** | **60 536** |
| de ellas, clasificadas | 7648 |
| descartadas por el control (A) | **0** |

y el reparto de las clasificadas:

| cubo | |
|---|---|
| (i) empuje vivo y NO contrayendo — el detector acierta | 1479 |
| (ii) empuje vivo y **CONTRAYENDO** | **616** |
| (iii) F clavada en el recorte | 5542 |
| (iv) F y X **asentadas**, cortada igual | **11** |
| **población del defecto = (ii) + (iv)** | **627** |

**El cubo (iv) es el titular de la ficha —la rama cortada por haber acertado— y
sale 11, no 0.**

### El denominador de los cubos NO es el de las estancadas, y decirlo es la mitad del valor

Hay 60 536 cortadas y sólo **7648 clasificadas**, porque reconstruir `d_x` cuesta
dos llamadas topadas y hay un tope de 400 por fila, alcanzado en **15 de las
35**. Ese tope se queda con las **primeras** 400 de cada fila, así que **no es
una muestra al azar y sus porcentajes no se extrapolan**. Lo que sí se afirma es
lo medido: existen **al menos** 627 ramas en (ii)+(iv), y eso basta para que la
población no sea cero. Publicar «el 8,2 % de 60 536» habría sido exactamente el
cero-falso al revés.

### El coste, medido sin tocar el motor

`solve_branch` **ya expone `patience` en su firma**, así que la cota superior de
lo que costaría no esperar no necesita ningún interruptor nuevo ni ninguna
edición: se vuelve a lanzar cada rama de (ii) y (iv) con `patience` enorme y el
mismo `max_passes`. **65 027 pasadas de más a cambio de 434 respuestas** que hoy
se pierden — o sea, de las 627 re-lanzadas, el **69 %** habría convergido dentro
del mismo presupuesto.

Y hay que leerlo como lo que es: `patience` enorme es una **cota superior** de lo
que costaría mirar el par, no el coste del detector por pares, que seguiría
cortando cuando **ninguno** de los dos residuos bate su récord.

### El punto ciego que este censo no hereda

El contador `esperan_mas_de_20` de `criterio_rama_d145.py` filtra sobre ramas
**ACEPTADAS**, así que por construcción no puede ver una cortada por
estancamiento. No se reutiliza, y las cortadas se cuentan aquí a mano.

### La ficha queda ABIERTA, y a propósito

El criterio de cierre tiene dos ramas excluyentes: o el recuento sale cero y se
declara, o sale población y el contador pasa a mirar el par con su interruptor,
su A/B y su coste. **Sale población y el contador no se ha tocado**, así que
`verificar_cierres.py D158` contesta `PARCIAL` con los números delante. Tocar el
detector es un cambio de motor que mueve ramas en todo el banco y es decisión del
propietario, no de esta tanda.

---

## D157 — EL DEFECTO ES REAL, LA POBLACIÓN ES **1 DE 23 945**, Y EN ESE UNO EL ARREGLO SERÍA INERTE

El defecto está donde la ficha dice: `refine_lambda_gap` trabaja sobre
`rows[-1]`/`rows[-2]` y `rows[0]`/`rows[1]` y sondea en los nodos que quedan
**más allá** de ese borde, así que un nodo perdido **entre** dos muestras vivas
no entra en `fuera` por ninguna de las dos ramas y no lo mira nadie. Lo que esta
versión añade es el tamaño de eso, que es lo que el paso 1 del encargo pedía.

### El denominador de la ficha era el equivocado, y por dos razones a la vez

La ficha publica «329 filas de 340 con al menos un nodo perdido».

1. Está contado sobre **críticas archivadas**, y una crítica archivada es por
   definición una superficie que **sí** horquilló — que es exactamente la que no
   ejecuta una sola instrucción de la función.
2. La función sólo se llama cuando `bracket is None`, así que el denominador es
   **las superficies que LLEGAN a ella**.

Instrumentando búsquedas enteras —`_tools/hueco_interior_d157.py`, que SOLO
MIDE— sobre 35 filas de 22 problemas:

| | |
|---|---|
| superficies evaluadas | 164 936 |
| superficies que no cierran λ | 25 |
| **superficies que LLEGAN a `refine_lambda_gap`** | **23 945** |
| de ésas, con al menos un hueco **interior** | **1** |
| nodos perdidos **interiores** | **1** |
| nodos perdidos **de borde** — lo que la función ya mira | **214 788** |
| desacuerdos del control (B) | **0** |

Uno contra doscientos catorce mil.

### Y en ese uno la extensión no habría hecho nada, que es lo que lo convierte en decisión

El único hueco interior del censo es del **problema 109 con Spencer**: el nodo
perdido es **λ = 0**, entre −0,1 y +0,1, **y esas dos son las únicas muestras
vivas de esa superficie**. La prueba de tendencia que la ficha prohíbe tocar
—`abs(borde[1]) < abs(dentro[1])`— necesita una **tercera** muestra al otro lado
del borde para tener `dentro`, y no la hay por ninguno de los dos lados.

Además `|g|` **crece** hacia la derecha (0,247439 en −0,1 contra 0,393571 en
+0,1), de modo que si hay un cruce está **a la izquierda de −0,1** — que es un
hueco de **borde**, y la función ya lo sondea. Escribir la extensión no habría
movido esa superficie ni un dígito.

Por eso el censo publica **0 sondeos**: no es un fallo de la sonda, es la prueba
de tendencia no teniendo entrada.

### La tercera pregunta de la ficha no podía dar otra cosa

Pide «en cuántas de ésas el `g` de las muestras a los dos lados del hueco
comparte signo». **En todas, siempre, por construcción**: la función sólo corre
cuando `_first_bracket` ha devuelto `None`, y eso significa exactamente que
ningún par consecutivo de muestras ordenadas cambia de signo. Se mide igual —1
de 1— y se publica **diciendo que es una identidad y no un hallazgo**. Es el
patrón del «0 de 48» de D156, que eran 0 de 3.

### Y el cero no es el de un medidor dormido

Que es el reproche que esta misma tanda le hace a D158, así que había que
ganárselo: el **control (E)** del censo enseña, sobre un muestreo escrito a mano
con dos nodos perdidos dentro del rango vivo y uno más allá del último, que
`_huecos` **ve** el interior y **separa** el de borde. Sin ese control, un cero
no distingue «no hay huecos interiores» de «el medidor no los ve».

### La decisión

**No se toca el motor**, y la razón es el número: uno de 23 945, y en ese uno el
arreglo es inerte por la propia guarda que la ficha manda conservar.
`verificar_cierres.py D157` contesta `SE SOSTIENE` con el denominador delante.

**El límite, declarado**: la muestra son rejillas de hasta 400 centros más el
010, y el tope de tiempo dejó **26 problemas sin medir**, nombrados en el
informe. Es una cota inferior, y «cero» aquí significa «cero en lo medido».

---

## REPORTADO Y NO CORREGIDO (regla 6)

Dos anomalías nuevas, encontradas al leer el cierre de los dos métodos. Ninguna
se toca aquí.

* **La salida de reserva no publica `lambda_bracket_width`** y la horquillada sí.
  Es la única clave asimétrica entre las dos salidas después de las reparaciones
  de D155 y D156, y significa que la única salida que no cerró λ es la que no
  dice cuánto le faltaba.
* **En GLE, `boundary_ratios` va en orden de marcha** (`lam * system.shape`)
  mientras `interslice_e` e `interslice_x` van en orden de dovela, porque pasan
  por `boundaries_in_slice_order`. Observable sólo cuando `slide_sign < 0`; en
  Spencer la lista es constante y la incoherencia no se puede ver. Un panel de
  dovelas que lea las dos a la vez está mezclando dos convenios.

Y una tercera, que no es del motor sino de la forma de medirlo: **`evaluate_surface`
construye dos `GLESystem` por superficie**. No es incorrecto, pero hace que «el
ahorro por superficie» no sea una constante y que cualquier recuento por
superficie tenga que decir a qué sistema se refiere.

---

## ERRORES PROPIOS DETECTADOS ANTES DE PUBLICAR

Cuatro, y dos habrían publicado un número falso.

1. **El «80 %» del primer medidor era del medidor.** Agrupaba las repeticiones
   de λ por `id(system)`, y CPython reutiliza un `id` en cuanto el objeto se
   libera, así que 1795 superficies distintas se leían como una sola. Con un
   contador de generación que `compute_fos` incrementa, el número es 20,0 % —
   cuatro veces menor, y en la dirección que **favorecía** al cambio, que es el
   peor de los dos errores posibles.
2. **El aserto de `d159()` llevaba un 4 mágico y era falso.** Sobre la crítica
   archivada del 059 el ahorro son seis llamadas y no cuatro, por los dos
   sistemas por superficie. Sustituido por la identidad.
3. **`test_the_guard_is_load_bearing` pasaba midiendo lo contrario.** Poblaba la
   caché con la firma real y anulaba la firma **después**, con lo que el propio
   cambio de firma vaciaba la caché — es decir, medía la guarda funcionando y lo
   leía como «no hay guarda». Hay que anular la firma **también mientras se
   llena**, que es la forma del riesgo real.
4. **Una subcadena de la cabecera cruzaba un salto de línea** y `d159()` no podía
   casarla nunca: «WEAK discrimination» partido en dos líneas. Es la trampa que
   el changelog de v0.1.180 tiene escrita y que v0.1.185 volvió a pisar; van
   tres.

---

## LOS TESTS

`tests/test_lambda_state_cache_v1186.py`, **19 casos en cuatro clases**. Contra
el árbol de 0.1.185, con los tres ficheros del motor devueltos desde HEAD:
**9 FALLAN y 10 PASAN**, y el reparto está corrido, no recordado.

**Cinco fallan por una diferencia medida**: el λ devuelto se resuelve 3 veces y
no 1; el ahorro es 0 y no 4 en Spencer y en GLE; la caché no acierta nunca, así
que la identidad no tiene de qué serlo; y la firma anulada no puede producir un
par viciado donde no hay caché.

**Cuatro fallan por la AUSENCIA de un símbolo**, que es discriminación débil y va
etiquetada como tal.

**Los diez que pasan en los dos árboles lo hacen a propósito**: son la identidad
—los contadores, las claves de `details`, la traza de `_inner_solve`, la
determinación, `-0.0`, el NaN— y los dos casos de AST. Con la caché apagada
comparan una corrida consigo misma, y ése es su trabajo: el día que la caché deje
de ser una identidad se ponen rojos en el árbol que la tiene.

**Ninguno de los 19 fija un factor de seguridad contra una instantánea.** Son
identidades, recuentos de llamadas que el motor hizo de verdad, hechos de AST y
una adyacencia de dobles. El ancla absoluta ya existe y es mejor que una captura
nueva: los casos de `test_lambda_closure_v1180` y
`test_lambda_floor_v1184.TestTheCutChangesNoDigit`, escritos **antes** de que
esta caché existiera, se ponen rojos si mueve un dígito.

---

## VERIFICACIÓN

* Suite **entera y sin argumentos**: **4018/4018** (0.1.185 traía 3999; los +19 son exactamente el fichero nuevo), sin banner `FILTERED RUN`.
* A/B de tiempo con control repetido, publicado en
  `docs/audits/lambda_state_cache_v1186.md`.
* `verificar_cierres.py`: **D159 CUBIERTO POR TEST**, **D158 PARCIAL** con su
  población, **D157 SE SOSTIENE**.
* `auditoria_invariantes.py` a **0 ERROR** (748 hallazgos: 491 AVISO, 257 INFO,
  el mismo reparto que 0.1.185).
* `generar_comparativa.py` + `balance_evaluaciones.py` contra
  `Evaluaciones/0.1.185`: **559 → 559 filas, las 559 IGUAL, 0 sin pareja**. El
  único carácter que cambia en todo el documento es la versión instalada del
  renglón «Medido con» de D162. La instantánea **no es homogénea** y por eso se
  publica la versión del lado A: 91 archivos de 0.1.173 en la mitad circular.
* Los dos descuadres del control de los censos —**087 spencer +0,1208 %** y
  **104 spencer +0,0455 %**— **no son de esta versión**, y está medido: evaluando
  la **superficie archivada** de las dos, el factor sale a **−0,0000 %** del
  archivado y es **idéntico bit a bit** con la caché puesta y quitada. Son deriva
  de la BÚSQUEDA entre versiones, no del motor sobre una superficie dada; y el
  del 104 es exactamente el mismo +0,0455 % que el censo de D153 publicó sobre
  0.1.184.
* Contrato **SOLO MIDE** de los dos censos, comprobado: ni un `.ogr`, ni un
  `resultados*.json`, ni un `referencia.json` tocado.
* Instantánea `Evaluaciones/0.1.186`, con su comprobación byte a byte.

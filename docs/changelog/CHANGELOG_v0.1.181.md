# OGR Slip2D v0.1.181

**D148 — la rama de momentos se sale antes de que el rescate pueda verla, y la
raíz que se pierde estaba además entre dos nodos de la rejilla.**

## Lo primero, porque cambia el encargo: son DOS causas y no una

El encargo P-D148 pide una de dos cosas: «una entrada al rescate que no dependa
solo del número de pasada» o «una guarda que mantenga el iterado dentro de
`[F_MIN, F_MAX]`». La segunda **no puede hacer nada** y hay que decirlo antes
que ninguna otra cosa: el iterado NUNCA sale de esa ventana. `F` se recorta a
`[f_min, f_max]` en cada actualización y en la pasada en que la rama muere vale
**2,8613769780957528** (Pasiva) y **10,514828873694** (Activa), muy dentro de
[0,05, 50]. Lo que se sale de la región admisible es la **salida del mapa**, y
hacia abajo: `moment_fos` devuelve **−8,554361524365895**, de modo que la salida
que se toma es `f_new <= 0.0` y no el colapso de `m_alpha` ni el término motor
nulo. Una guarda sobre el iterado sería un ajuste que no mueve el resultado, que
es exactamente la regla 7 al revés.

Y hecha la primera —la entrada por firma del ciclo—, **el testigo no se movía ni
un dígito**. La raíz está en λ = 1,31988 y la rejilla calibrada pisa 0,8, 1,0 y
1,5: el arreglo de rama hace resolubles λ = 1,30, 1,32 y 1,35, el cambio de
signo aparece entre 1,30 (g = −2,268e-3) y 1,32 (g = +1,424e-5), **y la búsqueda
no mira ahí**. El último nodo usable es 1,00 con g = −0,034328 y el siguiente,
1,50, se pierde antes y después del arreglo. Son dos causas independientes de una
sola respuesta equivocada, y por eso esta versión cambia dos cosas y lleva **dos
interruptores**.

La tabla de atribución, ejecutada en `TestTheRootIsFoundAndBothChangesAreNeeded`:

| entrada por ciclo | refinamiento del hueco | publicado | error | λ | reserva |
|---|---|---|---|---|---|
| off | off | 1,765482 | +0,9818 % | 1,0000 | sí |
| off | **ON** | 1,750071 | +0,1003 % | 1,2891 | sí |
| **ON** | off | 1,765482 | +0,9818 % | 1,0000 | sí |
| **ON** | **ON** | **1,748318** | **+0,0000 %** | **1,3199** | **no** |

**Ninguno de los dos cambios, por separado, mueve el testigo.** El de rama no
mueve nada porque los λ que vuelve resolubles no son nodos; el del hueco llega a
+0,10 % y sigue cayendo en reserva, porque la muestra que necesita al otro lado
del hueco es justo la que el solver de ramas no sabe producir. Un A/B que moviera
los dos a la vez no habría atribuido nada — la lección de la columna `A` de
`support_arm_v1178.md`.

## El ciclo es de DOS FASES, así que el predicado obvio no puede disparar jamás

La ficha dice que «la amplitud creciente es detectable dos pasadas antes del
escape». Son **cincuenta** pasadas, y no por donde parece. Los pasos de un ciclo
de período 2 alternan pequeño/grande, de modo que `step > prev_step` es cierto en
pasadas alternas y **nunca dos seguidas**: la negación literal del test de
contracción de D116, `step > prev_step > prev_step_2`, no puede dispararse aquí
igual que `step < prev_step < prev_step_2` no podía dispararse sobre la rama
alternante que midió D145. Lo que crece es la **envolvente de la misma fase**,
`step > prev_step_2`, de forma continua desde la pasada 19 hasta el escape en la
69. Medido: 1,8136e-01 · 1,2204e-01 · 1,7602e-01 · 1,3031e-01 · 1,7364e-01 ·
1,3857e-01 sobre las pasadas 15 a 20.

## EL CENSO ES LO QUE AUTORIZÓ TOCAR EL MOTOR, y lo que fijó el umbral

`_tools/ciclo_rama_d148.py` (banco, **SÓLO de medida**, molde de
`criterio_rama_d145.py`): reusa `_evaluar`, `_superficie` y `LAMBDA_METHODS` de
`auditoria_reserva_lambda.py` en vez de reconstruir la búsqueda, captura el
`GLESystem` parcheando `_inner_solve` en vez de construir uno «parecido»,
reconstruye el paso con `criterio_rama_d145._paso` **importado y no copiado**, y
busca la pasada de muerte por bisección sobre `max_passes`. Dos corridas:

* **la escalera de cuñas** (16 celdas, 960 ramas, 0 saltadas, 0 descuadradas):
  77 salidas `None`, **las 77 por `f_new` no positivo**, 71 de ellas antes de
  `STALL_PATIENCE`;
* **el banco** (344 filas, 79 problemas, 236 críticas, 108 publicadas — el mismo
  denominador que `lambda_closure_v1180.md`, 6014 ramas, 18 saltadas con su
  motivo, 8 descuadradas de control que son las mismas de v0.1.180): **460**
  salidas `None`, 459 antes de `STALL_PATIENCE`.

El número que decide el umbral no es cuántas ramas muertas alcanza, sino cuántas
**aceptadas** le quita a la iteración amortiguada, y separando si esa rama
converge sola o sólo porque el rescate ya la toma en la pasada 81:

| K | muertas alcanzadas | aceptadas movidas | de ellas rescatadas | **ordinarias** |
|---|---|---|---|---|
| 3 | 75 | 22 | 11 | **11** |
| 4 | 59 | 18 | 11 | **7** |
| 5 | 44 | 12 | 11 | **1** |
| 6 | 38 | 11 | 10 | **1** |
| **10** | **21** | **8** | **8** | **0** |
| 12 | 18 | 7 | 7 | 0 |

`CYCLE_RUN = 10` es el primer valor en que ninguna rama que converge por
contracción ordinaria se toca, en el banco y en la escalera a la vez. **6 era
seguro en la escalera y se lleva una ordinaria en el banco** (el 093 bajo GLE en
λ = 2,5, racha de 8, aceptada en la pasada 75), que es exactamente por qué un
umbral leído de una sola fixture habría estado mal. Las ocho que K = 10 sí mueve
son todas `rescued=True`: ramas que la puerta de v0.1.176 iba a tomar de todas
formas en la 81, alcanzadas antes.

Y el censo se midió DOS VECES, con la tabla moviéndose entre las dos, cosa que
hay que decir en vez de publicar sólo la que salió mejor: la de arriba es de
ANTES de re-correr el banco, y repetida DESPUÉS —sobre las críticas archivadas
nuevas, que ya no son las mismas superficies— el cero de ordinarias aparece en
**K = 9** en vez de en K = 10. En las dos, 10 tiene margen y ninguna ordinaria;
lo que cambia es cuánto margen, y por eso el documento publica las dos fuentes
y no un número. El documento de auditoría lleva la segunda, que es la que el
árbol que se envía reproduce.

En esa segunda corrida las **descuadradas de control suben de 8 a 15**, y no es
un deterioro: el censo del lado ANTES evalúa con el motor de 0.1.180 contra
resultados que 0.1.181 acaba de archivar, así que las filas re-corridas TIENEN
que descuadrar. Nueve de las quince son exactamente esas —047, 059, 085, 087
×2, 090, 093 ×2, 094— y las otras seis (039 ×2, 081 ×2, 086 ×2) son la
heterogeneidad de la instantánea, que ya estaba.

## EL CAMBIO

**`interslice.py`.** (1) `solve_branch` gana `rescue_gate`, que separa dos
decisiones que un solo número gobernaba —cuándo entra el rescate y cuándo corta
el estancamiento—; `None` significa `patience`, así que es identidad por
construcción. **No es un refactor: es la mitad del arreglo.** Con el
estancamiento en 80 y sólo la puerta adelantada, en el testigo convergen **57 de
65 puertas** y todas al mismo valor, contra **33** cuando `patience` arrastraba
las dos cosas; en λ = 1,32, **37 contra 7**. La fragilidad que hacía que la
puerta 27 convergiera y la 28 no era el corte de estancamiento moviéndose con
ella, no la puerta. (2) `cycle_run`, un entero en el bucle caliente que reusa el
`prev_step_2` que el test de contracción ya guarda, y la entrada al rescate
cuando llega a `CYCLE_RUN`, **leída con una pasada de retraso** como `prev_step`
y `prev_d_x`: armar dentro de la pasada que evalúa la aceptación cambiaría qué
cláusula corre, y la del rescate puede RECHAZAR lo que la contracción admitía.
(3) `refine_lambda_gap` y `GAP_REFINE_STEPS`, junto a `branch_pair_ok` porque los
dos archivos gemelos lo comparten. (4) El quinto contador.

**El contador de la cuarta salida.** `branches()` abría su bucle con
`if state is None or state.converged: continue`, de modo que una λ perdida por
una rama sin estado dejaba los tres contadores **a cero** — medido en el plano
anclado Activo: 11 de 21 nodos perdidos mientras el resultado publicaba
`lambdas_lost_to_stall = 0` y `lambdas_lost_to_budget = 0`. Ahora es
`n_inadmissible`, publicado como `lambdas_lost_to_inadmissible` en los **cuatro**
dicts de `details` de `spencer.py` y `gle.py`, con su nota en
`analysis_runner.lambda_fallback_notes`. El nombre dice **lo observable y no el
mecanismo**, que es la lección de `REASON_LAMBDA_NOT_CLOSED`: de las 460 del
banco, 335 son ramas de FUERZAS —un término motor que se anula, no un ciclo—, así
que bautizar el contador por el escape del ciclo habría cableado una de tres
causas en un contador que ve las tres.

Y la nota del refinamiento **abre su propia puerta**, que estaba cerrada tras
`if not (fell_back or not_closed)`: esa nota se emite precisamente cuando la
superficie **NO** cayó en reserva, así que dejarla dentro habría hecho que la
única búsqueda con algo nuevo que contar fuera la única que no contaba nada. Es
la misma puerta que v0.1.180 tuvo que abrir, por la misma razón.

## POR QUÉ EL REFINAMIENTO NO PUEDE TOCAR LO QUE YA FUNCIONA

Sólo corre cuando la rejilla entera **y** la extensión perezosa no horquillaron
nada, que es exactamente la superficie que estaba a punto de publicar un valor de
reserva. Y sólo mira el hueco si `|g|` es **menor** en la muestra del borde que
en la de dentro: donde `g` es plano o se aleja no hay razón para creer que haya
un cruce escondido, y vuelve en el acto. La bisección trata «perdida» como
«demasiado lejos» y «mismo signo» como «sigue», así que parte el hueco por la
mitad en cada paso: en el testigo, 1,25 (mismo signo), 1,375 (perdida), 1,3125
(mismo signo), 1,34375 (**cambio de signo**) — cuatro pasos de los seis.

## EL A/B, y por qué la atribución NO sale del diff contra la instantánea

A/B **en un solo proceso** conmutando los dos interruptores, sobre las 244
críticas archivadas del banco: **17 movidas, 0 saltadas**. La mayor es el 047
Spencer con **+0,6810 %**; después +0,2377 % y +0,1003 % (las dos mitades no
circulares del 085) y +0,0230 % (059); las once restantes por debajo de
**0,02 %**, seis de ellas por debajo de 1e-9. **Ni una sola fila cambia de estado
de reserva.**

Y la columna sin la cual la tabla sería falsa: **ninguno de los 19 archivos de
resultados de esos ocho problemas es de 0.1.180**. El del 047 es de **0.1.162**,
dieciocho versiones atrás; cuatro son de 0.1.178 y catorce de 0.1.179. Así que el
diff contra `Evaluaciones/0.1.180` **no puede atribuirme nada limpiamente** — le
cargaría a D148 lo que movieron D125, D144, D145 y D146 — y la atribución de esta
versión sale del **A/B en proceso, sobre un único árbol**, que es la medida
limpia.

LA CORRIDA DEL BANCO, aun así, porque refresca esas filas: 8 problemas, 14
modelos circulares en **4,3 h** sin un solo error, más las dos mitades no
circulares del 085 (4569 s) y el 047 por su propio lanzador. Contra la
instantánea, **41 valores iguales y 14 movidos**, cada uno con su versión de
lado A:

| problema | fila | antes | ahora | delta | lado A |
|---|---|---|---|---|---|
| 085 | no circular pasivo · Spencer | 1,512356 | 2,072412 | **+37,03 %** | 0.1.178 |
| 085 | no circular activo · Spencer | 2,066678 | 2,312511 | **+11,90 %** | 0.1.178 |
| 085 | no circular activo · GLE | 2,250695 | 2,321325 | +3,14 % | 0.1.178 |
| 047 | Spencer | 0,849792 | 0,866564 | +1,97 % | **0.1.162** |
| 090 | Spencer | 0,904962 | 0,897195 | +0,86 % | 0.1.179 |
| 093 | sin conexión · Spencer | 0,994166 | 0,993611 | +0,056 % | 0.1.179 |
| 059 | Spencer | 0,565503 | 0,565634 | +0,023 % | 0.1.178 |

y siete más por debajo de 0,02 %. Comparativa **559 → 559** filas, 552 IGUAL,
sin pareja 0/0, y **UN** cambio de estado.

EL 090 ES LA REGLA 7 EN AFIRMATIVO y conviene leerlo antes que los dos de
arriba: su superficie crítica CAMBIA —centro (−5,111, 18,647) R 16,798 pasa a
(−3,222, 16,824) R 14,205— y `validas` sube de **16146 a 16360**. Recuperar λ
vuelve evaluables 214 superficies más, y entre ellas gana una más baja: el
mínimo sólo puede bajar, y baja.

## EL CAMBIO DE ESTADO, Y SU CAUSA NO ES LA QUE PARECE (regla 6)

El único cambio de estado del banco entero es **085 · no circular · activo ·
Spencer, REVISAR → DISCREPANCIA**, de −3,44 % a +13,89 % del 2,016 publicado. Y
la causa **no es la evaluación**: medido superficie a superficie, la crítica que
0.1.178 archivó SIGUE EXISTIENDO, SIGUE SIENDO VÁLIDA y con el motor de hoy vale
**2,071581** (activo) y **1,513872** (pasivo) — a +0,24 % y +0,10 % de lo
archivado, exactamente lo que el A/B en proceso predijo. Lo que cambió es que la
búsqueda guiada de camino **ya no visita esa superficie**: el mismo recuento de
5000 superficies, todas válidas en los dos lados, y un mínimo peor.

Es decir: una búsqueda guiada cuya trayectoria depende del evaluador se re-baraja
con CUALQUIER cambio de motor, y esta fila ya saltó de +19,6 % a −4,0 % en
v0.1.176 por la misma razón. Sale como ficha **D155**, con prompt largo. No se
oculta ni se revierte: el número publicado es el que el motor produce, y lo que
va al lado es la medida de por qué.

## REPORTADO Y NO CORREGIDO (regla 6)

* **La mayor parte de lo que el banco pierde por esta salida no es este
  defecto, y ningún predicado lo alcanzará.** De las 460 salidas `None`, la
  mediana muere en la pasada **DOS** y 335 son ramas de FUERZAS, donde el
  denominador se anula: no hay ciclo que detectar y no hay historia que leer. En
  la escalera, 30 de 77 mueren en la pasada 5 o antes. Lo que cambia para ellas
  es que **se cuentan**;
* **la celda Activa del plano de 50° sigue sin raíz alcanzable**: su escape llega
  antes del cruce con cualquier puerta. Fijado en `TestWhatIsStillOutOfReach`, no
  escondido;
* la concordancia de las notas de `lambda_fallback_notes` está mal en las tres
  que ya existían — «and 7 inclinations **was** discarded» — y no se toca aquí
  porque es texto publicado y su arreglo no pertenece a esta ficha. La nota nueva
  sí concuerda;
* `refine_lambda_gap` mira los dos extremos del rango muestreado, y en el
  extremo inferior no hay ninguna celda medida que lo ejercite: la mitad de abajo
  está escrita por simetría de la formulación y **no por medición**, cosa que hay
  que decir antes de que alguien la lea como cubierta.

## ERRORES PROPIOS DETECTADOS ANTES DE PUBLICAR

1. **El primer umbral se eligió sobre una muestra sesgada.** Medí 60 celdas
   topando el barrido en la pasada de convergencia, de modo que una rama que
   converge sólo porque el rescate la toma en la 81 nunca llegaba a enseñar su
   racha. Con ese sesgo la tabla decía «ninguna rama que converge pasa de 1» y el
   plan se escribió sobre esa frase. La primera celda que midió el censo de
   verdad —λ = 1,275, que converge en la pasada 290 con racha **45**— la refutó.
   El censo del banco la corrigió del todo y movió el umbral de 6 a 10;
2. **el centinela `-inf` hacía la comparación cierta en las dos primeras
   pasadas**, así que toda rama se llevaba dos crecimientos gratis y `CYCLE_RUN`
   habría significado K−2 mientras el censo contaba desde la tercera: el medidor
   y el motor midiendo cosas distintas, que es el error nº 2 de v0.1.180 otra
   vez. Corregido con `prev_step_2 > -math.inf`, que es el mismo argumento por el
   que el centinela es `-inf` y no `+inf`, leído del otro lado;
3. la cabecera del fichero de test **afirmaba** que ningún caso falla por un
   símbolo ausente, y dos importaban `CYCLE_RUN` arriba: la afirmación era falsa
   en su propia cabecera. Pasados a `getattr`, y el reparto de discriminación
   (7 por diferencia medida, 4 por símbolo ausente) se cuenta **ejecutándolo**
   contra el árbol de 0.1.180 con `git stash`, no de memoria;
4. `2>&1 > archivo` manda el error estándar al terminal y no al archivo, así que
   el primer recuento de discriminación perdió un fallo y dijo 10 donde eran 11;
5. copié `sup.total_normal()` en la forma cerrada de la cuña y ese método no
   existe — es `math.fsum(sup.n_press)`, como en el fichero hermano;
6. el barrido de λ con paso 0,25 **no muestrea 1,30**, que es el testigo de la
   ficha, así que la primera medida del rendimiento del arreglo («2 de 35
   convergen») lo excluía justo a él;
7. el primer diseño ponía la entrada del rescate donde se calcula `contracting`,
   dentro de la misma pasada que evalúa la aceptación, donde puede rechazar lo
   que la contracción iba a admitir.

## LOS RE-ANCLAJES, con la razón escrita y sin ensanchar ninguna banda

`test_anchored_wedge_root_v1177.py` mide el defecto y **falla cuando se arregla**
— es su función. Seis casos re-anclados con `_uncycled()` / `_unrefined()`
conmutados en proceso y restaurados con `try/finally` (el runner no ejecuta
`teardown_method`), de modo que **lo que v0.1.177 midió sigue medido**: la pasada
69, el residuo que no sigue a la tolerancia, la dispersión de 1e-11 entre
puertas. Dos clases cambian de nombre porque el suyo pasó a ser falso:
`TestWhatTheProgramPublishesMeanwhile` → `…Until0_1_180`, y
`test_the_recovered_root_is_the_wedge` cambia su última aserción, que era
`published > 100 * near` y ahora es **falsa por éxito y del revés**: lo publicado
está a 1,6e-13 de la cuña y lo experimental a 8,1e-6.

Y en `test_janbu_wedge_v1142.py`, `TestAWedgeWhoseRootTheSolverCannotReachSaysSo`
pasa a `TestAWedgeWhoseRootTookThreeVersionsToReach`. **Es el segundo renombrado
de esa clase y la razón es la misma de la primera vez**, que es justo por qué hay
que escribirla dos veces: todas sus aserciones siguen siendo ciertas bajo
`_as_0_1_180`, así que una clase llamada «no puede alcanzar» se quedaría verde
afirmando como hecho algo que esta versión refuta — que es como
`TestAWedgeWithNoRootSaysSo` pasó dos versiones diciendo cosas ciertas bajo un
nombre falso. Gana un caso que fija el resultado nuevo, para que el nombre no
pueda volver a caducar en silencio.

## EL RE-ANCLAJE QUE LA CORRIDA DIRIGIDA NO VIO

`test_max_iterations_scope_v1173.py` (D117) no estaba en el filtro dirigido y
salió en la suite entera, con dos casos en rojo. **Ése es el argumento entero de
por qué sólo cuenta la suite sin argumentos**, y no es un descuido menor: los dos
fallos son del mismo defecto de método que esta versión corrige en otro sitio.

Su ayudante `_unrescued()` apagaba UN mecanismo de recuperación de λ, y esta
versión añade dos más, así que el caso comparaba un patrón calculado con un motor
contra dos valores calculados con otro. Mientras ninguno de los mecanismos movía
esa celda era inofensivo; ahora los dos la mueven. Pasa a llamarse
**`_without_lambda_recovery()`** y apaga los tres, porque un ayudante que se
llama «sin rescate» y además apaga el refinamiento del hueco dice menos de lo que
hace — que es exactamente el `off(tighten=True)` que v0.1.179 pagó en voz alta.

Y la celda que mide **se acerca a la referencia externa**: el plano de 55° bajo
Spencer pasa de 2,593302 a 2,572160, y la forma cerrada de esa cuña vale
2,461306, así que el error va de **+5,36 % a +4,50 %**. El refinamiento solo la
lleva a 2,584021 y los dos juntos a 2,572160. El segundo caso fallaba por otra
vía y también se arregla sola: con el refinamiento encendido,
`lambdas_lost_to_budget` lee **3** donde la clase exige 0, y los tres son ramas
de λ que el propio refinamiento introdujo — una consecuencia real de muestrear
más, no un defecto.

## EL TEST

`tests/test_branch_cycle_v1181.py`, 23 casos en siete clases. **Ninguna aserción
fija un factor de seguridad contra un valor de reserva**: todo es un A/B en un
proceso, una identidad, un recuento de pasadas o una comparación contra la forma
cerrada de la cuña que el propio archivo calcula (Coulomb 1776; Duncan y Wright
2005 §6). La fixture se escribe EN CÓDIGO porque `tests/` no puede alcanzar el
banco y un test que necesita un directorio fuera del repositorio falla en una
máquina limpia; el `GLESystem` se comparte entre casos para que el fichero no sea
caro.

Contra el árbol de 0.1.180 con sólo este fichero añadido, **FALLAN 11 y PASAN
12**, y el reparto va NOMBRADO: **siete por diferencia medida** —la rama que
vuelve `None`, dos de cuatro arranques en vez de cuatro, las dos λ de la horquilla
en `(None, None)`, el contador ausente, la nota ausente, la tabla de atribución
con 0,98 % en las cuatro esquinas y la respuesta publicada como refusal— y
**cuatro por símbolo ausente**, que es discriminación débil y va etiquetada como
tal. De los doce que pasan, **seis están hechos para pasar en los dos árboles**
porque describen el DEFECTO y no el arreglo, y una diferencia en cualquiera de
ellos significaría que el diagnóstico dejó de sostenerse.

## VERIFICACIÓN

Suite entera y sin argumentos **3905/3905** sobre el árbol final y sin banner
`FILTERED RUN` (0.1.180 traía 3881; los +24 son los 23 del fichero nuevo y el
caso que gana `test_janbu_wedge_v1142`). Corrida DOS veces y las dos SOLA: la
primera dio 3903/3905 y es la que destapó los dos re-anclajes de D117 —que el
filtro dirigido no cubría, y por eso sólo cuenta la suite sin argumentos—; la
que vale es la segunda, ya con el changelog escrito que
`test_version_consistency_v176` exige. Lo único tocado después de esa corrida
es prosa de este archivo y los finales de línea del documento de auditoría, y
el único test que mira el changelog comprueba que exista.

`_tools/ciclo_rama_d148.py` y `curva_cuna_d119.py` regenerados;
`generar_comparativa.py` y `balance_evaluaciones.py` contra
`Evaluaciones/0.1.180`; `auditoria_invariantes.py` a **0 ERROR** (748 hallazgos:
491 AVISO, 257 INFO, el mismo reparto que 0.1.180); `verificar_cierres.py D148`
**CUBIERTO POR TEST** con las cuatro medidas, y comprobado que DISCRIMINA por
los dos lados —sin los símbolos contesta NO SE SOSTIENE nombrando cada uno; con
ellos pero con los interruptores apagados, la rama vuelve a morir en la pasada
69 y el método vuelve a publicar 1,765482 en reserva—. Instantánea
`Evaluaciones/0.1.181` congelada, **1632 archivos comprobados byte a byte**, con
17 archivos ya a 0.1.181 y el resto en el reparto que la instantánea publica.

Ficha retirada al índice **con su renglón corregido**, porque el título heredado
contaba una sola causa y eran dos; podada de P2 en el markdown Y en la constante
`PAQUETES` de `generar_prompts.py`, con el renglón de P2 corregido ENTERO
(descripción y cadena tachada, que el generador no escribe); prompts regenerados
con salida 0 — 44 prompts, 0 fichas cerradas sin prompt, 0 sin paquete. Ficha
nueva **D155** con su prompt largo, en el bloque del 02: la puse primero en el
Bloque 14 y lo cazó el contador de prompts, que la clasificó como 03–07.

## UN ERROR MÁS, EL OCTAVO, Y ES EL DE SIEMPRE

Al arreglar el `Path.write_text` del medidor —que escribía el documento de
auditoría en CRLF contra el `.gitattributes` del repo, que fija LF también en el
árbol de trabajo— escribí el parche por heredoc con una barra DOBLE, **llegó
como una sola**, y `newline="
"` se convirtió en un salto de línea real que
dejó el archivo sin compilar. Es la trampa que `AGENTS.md` tiene escrita, que
v0.1.179 volvió a pisar y que he vuelto a pisar yo. Reparado con `chr(92)`, que
es la forma que la nota de esa trampa recomienda.

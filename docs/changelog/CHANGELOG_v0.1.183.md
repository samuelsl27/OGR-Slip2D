# OGR Slip2D v0.1.183

**D152 — en un plano el factor de fuerzas no debe nada al empuje, así que no
se le puede exigir nada al empuje antes de tomarlo. Y la ficha se equivocaba
en las CUATRO cosas que afirmaba sobre el mecanismo.**

## Lo primero, porque cambia el encargo: la ficha describe mal su propio defecto

D152 dice que en la celda que se pierde «el empuje viaja a **0,0679 de la
escala de fuerzas por pasada**», y el docstring del test que lo fijaba lo
repite añadiendo **«climbing»**. Medido sobre 0.1.182, las dos mitades son
falsas:

- `d_x` **hace pico en 0,341 en la pasada 2** y baja monótonamente desde la 8
  (2 subidas en 57 pasadas, las dos antes de la octava). **No crece.**
- El 0,0679 **no es una tasa**: es el valor **en la pasada 48**. La razón de
  contracción es **0,98275 por pasada**, de modo que `d_x` habría bajado de
  1e-10 hacia la **pasada ~1217**, contra un techo de 400.

O sea que el par **sí estaba convergiendo**, sólo que más despacio que el
presupuesto. Y la segunda afirmación tampoco se sostiene: la rama **no muere
por la puerta ni por el techo**. Sale con `abandoned=''` y `passes=271 < 400`,
lo que deja una sola salida posible, el `break` de estancamiento. El detector
de estancamiento **mira sólo F** (`if step < best_step`), y cuando F alcanza su
punto fijo su paso vale **0,0 exacto** y ya no puede batir su propio récord
nunca más: **una rama que acierta leída como una rama que divaga.**

## La tercera, que es la que habría convertido el arreglo en un defecto

La ficha ofrece como salida «juzgar la rama de fuerzas sobre una **poligonal**
con otro criterio». Eso eximiría a una familia que no tiene la propiedad.
Medido sobre la misma ladera, dispersión relativa de `F_f` a lo largo de λ:

| superficie | ángulos de base distintos | dispersión de `F_f` |
|---|---|---|
| plano 50° | 1 | **2,4e-14** (con ancla 2,2e-12) |
| poligonal 2 tramos | 2 | **10,1 %** (con ancla 7,7 %) |
| poligonal 3 tramos | 3 | **11,7 %** (con ancla 24,3 %) |

**La familia es UN ÁNGULO DE BASE, no una clase de superficie.** Y no es
hallazgo propio: Krahn (2003), *The 2001 R.M. Hardy Lecture: The limits of
limit equilibrium analyses*, Can. Geotech. J. **40**(3): 643-660, p. 646 y
fig. 5, lo dice literalmente — «Now force equilibrium is **completely
independent of interslice shear** … The soil wedge on the planar slip surface
can move **without any slippage between the slices**» — y en la misma página
pone la compuesta en la otra caja: «**both** moment and force equilibrium are
influenced by the interslice shear forces». USACE EM 1110-2-1902 §C-7a llega
al mismo sitio por determinación estática: una dovela, dos ecuaciones, dos
incógnitas.

## Y la cuarta: «no hay prueba barata dentro del bucle» es falso

La ficha dice que exentar la rama «depende de la geometría de la **superficie**
y no de las filas». `SliceRow.alpha` **es** ese ángulo y `solve_branch` ya
recibe las filas. El dato lleva dentro del bucle desde que existe el tipo.

## EL CENSO, y el número NO es cero

`_tools/criterio_rama_d145.py` gana cuatro columnas —`tipo`, `n_vertices`,
`dispersion_alpha` y `perdida_por_la_puerta`— siguiendo el precedente exacto de
`auditoria_reserva_lambda.py:204-206`, que ya publicaba `tipo`. La columna que
contesta el encargo es la última: rama que el motor enviado **no** acepta y que
con `BRANCH_PAIR_TIGHTEN` y `BRANCH_PAIR_SETTLE` apagados **sí** aceptaría.

El banco tiene **exactamente un plano estricto** que llega a Spencer/GLE — las
publicadas de 2 vértices (043, 048, 049, 053) son todas Janbu, que no entra en
`interslice.py`— y ese plano **pierde una rama**:

| problema 047 · Spencer · λ = 0,8 · rama de fuerzas | motor enviado | puerta apagada |
|---|---|---|
| pasadas | **162** | **11** |
| `converged` | **False** (`estancamiento`) | True |
| factor | 0,9103983480295631 | 0,910398348029563 |

`fos_gap` = **1,11e-16, un ULP**: lo que la puerta quita es la **etiqueta** y
las 151 pasadas, no el número. `dispersion_alpha` de ese caso vale 7,105e-15,
el mismo ruido de coma flotante que la cuña sintética.

## EL CAMBIO

Tres piezas en un solo archivo, `ogr_slip2d/interslice.py`:

1. `PLANAR_ALPHA_SPREAD = 1e-9` (rad), con Krahn y el EM citados y **los dos
   márgenes medidos**: un plano de verdad da 4,1e-15 a 7,3e-15 rad —los ángulos
   **no** son bit a bit iguales, son 16 valores distintos sobre 50 dovelas, que
   es lo que descarta una comparación exacta—, la poligonal más suave 3,3e-1 y
   un círculo 1,4. **Catorce órdenes**: cualquier umbral en [1e-12, 1e-3]
   clasifica igual, así que el valor no decide nada.
2. `planar_force`, resuelto **una vez** antes del bucle junto a la cota de
   empuje y por la misma razón: no puede cambiar con F, λ ni la pasada.
3. `BRANCH_PLANAR_FORCE = True`, leído en tiempo de llamada con el molde de
   `BRANCH_RESCUE`, añadiendo un disyunto a la cláusula de contracción. **Sólo
   puede ADMITIR**, como `BRANCH_PAIR_SETTLE` y al revés que su hermano.

**Por qué es inerte fuera de un plano, y es demostración y no censo**: las 5348
ramas que D145 midió son círculos y poligonales de ángulo variable, y el
disyunto es inalcanzable para todas ellas por construcción.

## LA MITAD QUE DISEÑÉ MAL PRIMERO, y lo que la refutó

El primer diseño exigía además que el empuje **contrajera** (`d_x < d_x_was`).
Parecía prudente y encajaba con la cuña anclada, donde contrae a 0,98275. **No
encaja con el banco**: en el 047 a λ = 0,8 el empuje **CRECE** en la pasada que
acepta —0,1875 de la escala y subiendo— mientras F divide su paso por dos cada
pasada exacta. Esa condición habría recuperado la fixture sintética y **no la
fila real**. Si el factor no depende del empuje, exigirle algo al empuje es
importar una condición que la mecánica dice que es irrelevante; las dos
medidas discrepando es lo que lo dijo.

## PERO EL EMPUJE SÍ TIENE QUE ENTRAR, POR OTRA PUERTA, Y ME LO ENSEÑÓ UN TEST

Con el primer diseño sin guarda, `test_a_converged_branch_is_no_longer_built_on_a_runaway`
se puso **rojo**, y tenía razón. Yo había medido que la rama desbocada muere en
la pasada 4 por `thrust overflow` y concluí que la cota protegía la exención —
pero **ese caso corre bajo `_lifted()`, que levanta la cota**, justamente para
probar que la puerta es una segunda línea y no una coincidencia. Con la cota
levantada la exención **aceptaba** el plano de 55° en λ = −5,55 en la pasada 16,
con el empuje a **6,09e9 veces la escala** y un factor de **2,4586394312** contra
una forma cerrada de **2,4613056257**: **0,108 % equivocado**. El telescopado es
exacto en el álgebra y **se rompe en la aritmética** cuando la cancelación es
así de grande, o sea que «el factor no depende del empuje» deja de ser cierto
*antes* de que la cota hubiera dicho nada.

De ahí la guarda, y **no puede ser la cota, porque la cota es lo que un test
levanta**: el empuje no puede moverse en **una** pasada más fuerza de la que
toda la masa deslizante tiene, `d_x < 1.0` en las unidades a las que
`_force_scale` ya normaliza — por eso el número es 1 y no una calibración.
**Sus dos márgenes, porque sólo uno es cómodo**: toda rama de fuerzas plana y
sana medida se queda en 0,444 o por debajo (la cuña pica en 0,341; el 047 llega
a 0,444 tras 162 pasadas y está en 0,1875 en la que acepta), así que el lado
que **admite** despeja por **2,25×** y no más; el que **rechaza** despeja por
**2,7e10**. El lado fino se dice en vez de esconderse, y descansa sobre un caso
de banco y una fixture, que es toda la población que existe.

## QUÉ SE MUEVE, CON LA MEDIDA DELANTE (regla 7)

**Las doce celdas de la cuña anclada dan ahora el mismo factor**, igual a la
forma cerrada a nueve cifras (0,941982760 / 2,757457925 / 1,748317883). La
celda perdida vuelve: 271 pasadas y no convergida → **48 y convergida**. Y las
dos que pagaban la puerta sin perder su respuesta dejan de pagarla: la activa
en λ = −1,0 de **92 a 48** pasadas y la pasiva en 1,25 de **84 a 52**.

**Y se mueve una cifra**: el plano de 52,5° bajo GLE a 1e-4 pasa de
**1,1737414866** a **1,1736808974** (5,2e-5 relativo, **la mitad de su propia
tolerancia**), porque con los nodos recuperados la rejilla de λ **horquilla
sola** y ya no hace falta el refinado de hueco; λ pasa de 1,6216634 a 1,6224203.
Contra la forma cerrada 1,1737425558 el error va de 9e-7 a 5,3e-5 relativo: se
aleja, dentro de su tolerancia, y se dice.

## EL A/B DEL BANCO, CON EL DENOMINADOR DELANTE

Censo completo por los dos lados con `--sin-d152`, que es un interruptor
**propio** y no `--sin-cambio`: apagar la exención plana no es lo mismo que
apagar la puerta de D145, y un A/B que mueva las dos cosas no atribuye
ninguna. Los dos lados recorren **los mismos 344 casos, las mismas 6188 ramas
y las mismas 5699 medidas**, con las mismas 18 saltadas y las mismas 6
descuadradas —idénticas en los dos árboles, así que no las causa este
cambio—, que es lo que hace que la comparación signifique algo.

| | lado A (sin D152) | lado B (enviado) |
|---|---|---|
| ramas aceptadas | 5336 | **5337** |
| `D152_quitadas_planas_de_fuerza` | **1** | **0** |
| `quitadas_por_la_puerta` | 19 | 18 |
| `aceptadas_empuje_vivo` | 0 | **8** |
| `ramas_planas` / de fuerza | 31 / 22 | 31 / 22 |

**Las ocho aceptadas con el empuje vivo son la MISMA superficie**: el 047,
Spencer, poligonal de dos vértices, rama de fuerzas, `plano = True` las ocho,
ocho nodos de λ de la misma búsqueda (0,6000, 0,6500, 0,6750, 0,6875, 0,6906,
0,6937, 0,7000 y 0,8000), aceptadas todas en la pasada 11 con `d_x` entre 80 y
1870 veces la tolerancia. **Ni un círculo y ni una poligonal de más de dos
vértices**, que es la demostración ejecutada de lo que la sección anterior
argumenta: el disyunto no alcanza a nada que no sea un plano. Y por eso ninguna
de las ocho es «una rama con el empuje vivo de verdad» en el sentido del
criterio de cierre: son justo la familia donde el empuje no entra en el factor.

**Y el banco entero se mueve por redondeo y nada más**: de los **344 casos**
comparados sin colapsar ninguno, se mueve **UNO**, el 047 Spencer, de
0,866545932303737 a 0,866545932303737 — **1,28e-16 relativo, un ULP**. De las
**6188 ramas**, difieren **8**: una cambia `converged` y siete mueven su factor
**como mucho 3,66e-16**. No hace falta re-correr el banco, y es una identidad y
no una omisión.

## LO QUE ESTA VERSIÓN NO HACE, Y SALE CON NÚMERO

- **El detector de estancamiento sigue mirando media pareja**, y sale como
  ficha **D158** con su prompt largo, en P2. Arreglarlo solo **no habría
  recuperado nada**: el empuje de esa celda necesita ~1217 pasadas contra un
  techo de 400, así que la rama sólo habría cambiado el **nombre de su
  salida**. Su premisa escrita —«*the step of a fixed point that contracts
  beats its own record on every pass*»— es **falsa justo en el punto fijo**,
  donde `step == 0.0` y `0.0 < 0.0` es `False`, así que una rama que acierta se
  corta por haber acertado. **Se envía DORMIDO y eso se publica**: de las 5699
  ramas medidas mueren por estancamiento **36**, y son **4** clavadas en el
  recorte `[F_MIN, F_MAX]`, **32** con el empuje realmente vivo y **0** con el
  par asentado — en las 36 el detector acierta, y ninguna es plana porque esta
  versión cerró esa mitad. Ojo al punto ciego que se nombra en la ficha: el
  contador `esperan_mas_de_20` del censo filtra sobre ramas ACEPTADAS, así que
  por construcción no puede ver una cortada por estancamiento, y publicar su
  cero como si cubriera el caso sería falso.
- **La rama recuperada publica un empuje sin asentar.** La exención devuelve el
  **factor**, no un empuje convergido: `thrust_is_admissible` pasa de `True`
  sobre el estado no convergido a `False` sobre el aceptado, de modo que ese
  nodo de λ **sigue fuera** de la búsqueda — antes por no converger, ahora por
  empuje inadmisible. Ninguna respuesta se mueve por eso, y decir **cuál de las
  dos cosas está pasando** es el punto. Hay un caso dedicado a afirmarlo.

## REPORTADO Y NO CORREGIDO (regla 6)

- **D158**, el detector de estancamiento, arriba: ficha nueva con prompt largo
  en P2, serie D movida a D158 y siguiente libre D159.
- El registro de D152 afirma un mecanismo que la medida desmiente, en las
  cuatro afirmaciones de arriba. Se corrige **al retirar la ficha**, no en
  silencio, y el docstring del test que lo fijaba se reescribe entero.
- `criterio_rama_d145.py:614` anuncia por consola un nombre de archivo que no
  existe cuando se corre con `--sin-cambio`: omite el sufijo `_antes`.

## ERRORES PROPIOS DETECTADOS ANTES DE PUBLICAR

1. **La guarda que faltaba**, arriba: afirmé que la cota protegía la exención
   habiéndola medido con **mi** fixture y no con la del caso, que corre con la
   cota levantada. Un test cazó una afirmación de seguridad que yo había dado
   por demostrada.
2. **La contracción del empuje**, arriba: un diseño que encajaba con la fixture
   sintética y no con la única fila real. Lo cazó medir el banco **antes** de
   dar por buena la fixture.
3. El control del test nuevo pedía la forma cerrada a **1e-6** sobre una rama
   resuelta a **1e-3**, donde el residuo legítimo `tol·r/(1−r)` vale 1,2e-4. No
   era un fallo del motor: era pedirle a una rama más precisión de la que se le
   compró. Reescrito a la tolerancia apretada, que además **ensancha** el
   contraste con la desbocada de seis órdenes en vez de uno.
4. `LAMBDAS` escrito como global cuando es atributo de clase: `NameError` en el
   primer caso re-anclado.
5. Medí la dispersión de ángulos esperando que un plano diera **un** valor bit a
   bit, y da **16**. Si hubiera escrito la comparación exacta que parecía
   evidente, la exención no habría disparado nunca sobre ningún plano — un
   arreglo que no hace nada, que es la regla 7 al revés.
6. La primera poligonal de control cortaba **por encima** del terreno y el
   slicer devolvía `None`; una fixture que no produce dovelas hace **vacua**
   cada aserción que cuelgue de ella en vez de falsa.

## EL TEST

`tests/test_planar_force_branch_v1183.py`, **13 casos en cinco clases**, y
ninguna aserción fija un factor contra una instantánea: todo es un A/B en un
proceso, una identidad, o la forma cerrada de la cuña. La fixture se escribe en
código porque `tests/` no alcanza el banco.

Contra el árbol de 0.1.182 con sólo este fichero añadido **fallan 3 y pasan
10**, con el reparto **nombrado** en la cabecera: **dos** fallan por diferencia
medida, **uno** por ausencia de símbolo —discriminación débil, etiquetada como
tal—, **tres** de los que pasan son vacuos sobre el árbol viejo por el idioma
`if keep is None` de `_off()`, y los **siete** restantes pasan en los dos
árboles a propósito. Entre esos siete, el de la rama desbocada es **el que hay
que vigilar**: se pone verde en los dos lados **por razones distintas** —0.1.182
la rechaza con la puerta de D145, ésta con la guarda—, así que es hermano del
caso de v1171 y no un duplicado.

### Re-anclajes, ninguna banda se ensancha

- `test_anchored_wedge_root_v1177.py` — el caso que **fijaba el defecto como
  esperado** (`assert lost is None or not lost.converged`) pasa a exigir que las
  doce celdas den la forma cerrada, más un caso hermano que clava los recuentos
  de pasadas con su A/B al lado. Su docstring se reescribe entero porque
  afirmaba el «climbing» y la muerte por la puerta.
- `test_interslice_thrust_bound_v1171.py` — `OVERFLOW_BETA` pasa de **52,5 a
  53,0**. La celda dejó de serlo: en 52,5 la exención devuelve los nodos, la
  búsqueda horquilla sola y las notas callan, que **no es una regresión** sino
  lo que `test_it_stays_quiet_when_the_search_found_its_bracket` ya fija como
  correcto dos casos más abajo. 53,0 se eligió contra **los mismos criterios**
  del bloque `#:`, re-medidos por los dos lados: pierde λ por la cota y las
  narra a 1e-4 (7 antes, 6 después) **y** a 1e-6 (7 y 7), no pierde ninguna por
  presupuesto en ninguno de los dos, su `admissible` y su `fos` siguen
  coincidiendo con la misma corrida con la cota levantada, y Spencer en ese
  plano sigue resolviendo su horquilla sin alcanzar la cota, que es lo que hacía
  de ésta una celda de GLE.

## VERIFICACIÓN

- **Suite entera y sin argumentos: 3943/3943**, cero fallos, **sin banner
  `FILTERED RUN`**, corrida DOS VECES en verde y las dos SOLA, sin nada más en
  la máquina: la primera al cerrar los re-anclajes y **la que cuenta es la
  segunda, 25 min 20 s**, sobre el árbol final y con el changelog ya escrito,
  que es lo que `test_version_consistency_v176` exige. 0.1.182 traía **3929**,
  y los **+14** cuadran exactamente: 13 del fichero nuevo y 1 del re-anclaje
  de v1177, que desdobla un caso en dos.
- Censo del banco por los dos lados con `--sin-d152`, que es un interruptor
  **propio** y no `--sin-cambio`: apagar la exención plana no es lo mismo que
  apagar la puerta de D145, y un A/B que confunda los dos no atribuye ninguno.
  Informe en `docs/audits/branch_state_v1183.md`; censos en
  `_auditoria/D145_criterio/censo_0.1.183.json` y `…_sin_d152.json`.
- `auditoria_invariantes.py` a **0 ERROR** (748 hallazgos: 491 AVISO, 257
  INFO), que es **el mismo perfil exacto** que 0.1.182. Los dos ERROR que
  aparecieron a mitad de camino eran la ficha sin retirar y su prompt sin
  podar, y desaparecieron al hacerlo.
- `verificar_cierres.py D152` → **CUBIERTO POR TEST**. La comprobación se
  escribió en esta versión porque **no existía** —antes contestaba «SIN
  CRITERIO»— y mide sobre la fila REAL del banco y **por los dos lados**: con
  la exención apagada el 047 en λ = 0,8 tiene que volver a no aceptarse, o la
  medida no discrimina.
- Ficha retirada al índice **corrigiendo el registro**, podada de P2 en el
  markdown **y** en `generar_prompts.py`, que es donde de verdad viven los
  paquetes; prompts regenerados con **salida 0**, 44 prompts, 0 fichas
  cerradas sin prompt y 0 sin paquete. El renglón de P2 se corrigió ENTERO —
  descripción y cadena—, no sólo tachando.
- Instantánea `Evaluaciones/0.1.183` congelada: **1637 archivos comprobados
  byte a byte**, salida 0.

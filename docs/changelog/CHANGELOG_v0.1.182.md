# OGR Slip2D v0.1.182

**D149 — el criterio del empuje decide qué λ PREFIERE la búsqueda, no cuál
puede VER. Y el testigo de la ficha llevaba una versión curado sin que nadie
lo supiera.**

## Lo primero, porque cambia el encargo: el testigo de la ficha está muerto

P-D149 nombra una celda —plano de 45°, ancla Pasiva de 120 kN/m, GLE, 50
dovelas, 1e-10— y dice que sale por la reserva en λ = 0,2 con residuo 6,144e-5
y factor 1,308767979. **Sobre el árbol de 0.1.181 esa celda no cae en reserva**:
publica **1,308737259**, que es la forma cerrada de la cuña, con
`lambda_search_fell_back = False`, `lambda_gap_refined = 1` y λ = 0,189970.

Los números de la ficha reproducen **dígito a dígito** apagando
`LAMBDA_GAP_REFINE`: 1,308767979, λ = 0,200000, +0,00235 %, reserva `True`. O
sea que la ficha se midió contra el buscador de λ de **0.1.180** —se abrió el
2026-09-18 con OGR 0.1.177— y **el refinado de hueco que estrenó v0.1.181 (D148)
curó esta celda de rebote**, cuatro versiones después, sin que el changelog de
aquella versión pudiera saberlo. Mismo patrón que D146, que resultó ser D145
visto desde el bucle de λ.

Escribir el test evidente sobre esa celda habría dado un caso **verde en los dos
árboles**, que es la trampa que este proyecto lleva pisada diez veces (D101,
D103, D118, D127, D129).

## Por qué la curó, y es lo que parte el defecto en dos

El criterio de admisibilidad se evalúa en los **NODOS** de la rejilla y la
respuesta **no está en un nodo**. Lo que decide, entonces, es dónde cruza cero
la suma de empujes interiores (λ_E) frente a dónde cruza cero `g = F_f − F_m`
(λ_g):

- **B1 · λ_E < λ_g** — la raíz es **admisible** y el filtro sólo borró el nodo
  que llevaba el otro signo. `refine_lambda_gap` bisecta desde el superviviente
  más bajo hacia el nodo perdido, su sonda cae **entre** λ_E y λ_g, es admisible
  y horquilla en un paso. En la celda de la ficha: λ_E = **0,107787** contra
  λ_g = **0,189970**. Curado por v0.1.181.
- **B2 · λ_g < λ_E** — la raíz cae del lado inadmisible. El refinado sondea
  hacia λ_E, que está **pasada la raíz**, y gasta su presupuesto sin cruzar
  nada. No llega nadie. Es lo que queda.

## El testigo vivo sale moviendo UN solo dato

Mismo plano, misma ancla, misma geometría: sólo la capacidad.

| cap | publicado en 0.1.181 | forma cerrada | err | reserva | adm |
|---|---|---|---|---|---|
| 120 | 1,308737259 | 1,308737259 | −0,00000 % | False | True |
| 122 | 1,316402046 | 1,316297412 | **+0,00795 %** | True | True |
| 125 | 1,328363302 | 1,327637642 | **+0,05466 %** | True | True |
| 128 | 1,340428108 | 1,338977873 | **+0,10831 %** | True | True |
| 131 | 1,352621165 | 1,350318103 | **+0,17056 %** | True | True |
| 134 | 1,364972658 | 1,361658333 | **+0,24340 %** | True | True |
| 137 | 1,372998564 | 1,372998564 | −0,00000 % | False | **False** |

**Un 2 % más de ancla —de 134 a 137 kN/m— lleva la respuesta de +0,243 % con
`admissible` verdadero a la forma cerrada EXACTA con `admissible` falso**, y no
porque el problema cambie sino porque en 137 **todos** los nodos son
inadmisibles y el barrido todo-o-nada de v0.1.106 dispara y encuentra la raíz,
mientras en 134 sobrevive **uno** (λ = 1,5), comparte signo consigo mismo y la
relajación no dispara. Esa discontinuidad es el enunciado de D149 con algo a lo
que agarrarse, y se mide **contra una referencia externa y no contra una
instantánea**: en un plano la masa es una cuña rígida, `F_f` es exactamente
constante en λ y vale la forma cerrada (Coulomb 1776; Duncan y Wright 2005 §6),
así que **cualquier** raíz de `F_f − F_m` es la cuña por identidad. Medido:
−2,4e-11 relativo.

Con el cambio, las seis filas de 122 a 137 publican su propia forma cerrada a
menos de 1e-6, y **la de 120 no se mueve un dígito** —sigue con
`lambda_gap_refined = 1` y `admissible` verdadero—, que es la comprobación de
que esto no toca lo que D148 arregló.

## EL CENSO, y el número es CERO

`_tools/borde_admisible_d149.py` (banco, **sólo de medida**) sobre **el banco
entero** y no sobre los 21 con soporte, porque «cuántas filas del banco» es lo
que pide el criterio de cierre y «los 21 son los candidatos» era una suposición
de la ficha. Re-evalúa la superficie **archivada** de cada fila por
`build_search(...).evaluate_surface(...)` y barre los nodos con
`system.states(lam)` —no con `branches`— para no tocar los contadores del motor
ni su filtro.

**Denominador:** 340 filas (232 críticas archivadas + 108 publicadas), **334
medidas**, 6 descuadradas y 22 saltadas con su motivo escrito.

| caso | filas |
|---|---|
| `sin_rechazos` | 310 |
| `A` (ningún nodo sobrevive; v0.1.106 ya dispara) | 3 |
| `B_ok` (los supervivientes ya horquillan) | 1 |
| `B_sin_horquilla` (la forma, sin cambio de signo) | 20 |
| **B1** | **0** |
| **B2** | **0** |

**Ninguna fila del banco toma este camino**, y en las 20 que tienen la forma el
rescate **revierte**. La suposición de la ficha, en cambio, resultó cierta y
ahora está medida: de 340 filas sólo **24** rechazan algún λ, y **las 24 son
modelos con soporte** (047, 060, 085, 087, 090, 092, 093 y 094).

**El cero está controlado por los dos lados**, que es lo que lo separa del
silencio de un medidor que sólo conoce el árbol sano —la lección de v0.1.180,
donde el censo dejó de medir justo cuando cambió lo que medía—: el MISMO
clasificador, sobre la cuña sintética, contesta **B1** a cap 120, **B2** a cap
134 y **A** a cap 137.

## EL CAMBIO

**`interslice.py`** — `GLESystem` gana `thrust_rejected_pairs`, un diccionario
`λ → (F_f, F_m)` con lo que `branches` estaba a punto de tirar. **Guardar no es
devolver**: la preferencia sigue en pie, `branches` contesta `(None, None)`
igual que antes, y el único lector es el rescate. Cero *solves* extra, cero
contadores movidos. Se guarda **dentro** del `if self.strict`, así que el
diccionario sólo se llena mientras la preferencia se está aplicando.

`recover_thrust_edge(samples, rejected)` devuelve `(filas, horquilla)` o
`(None, None)`. Devolver `None` en vez de las filas fundidas **es toda la
seguridad de la función**: quien llama conserva su lista intacta, de modo que
una superficie que no gana horquilla sale bit a bit lo que era —mismas
muestras, misma reserva `min |g|`, mismos contadores, misma bandera—. **El
rescate sólo puede convertir una reserva en una raíz resuelta; nunca puede
mover una reserva.**

Cuando aparece más de un cambio de signo se toma **el más cercano al tramo
admisible**, medido en nodos, y el λ menor desempata. No el de λ menor a secas,
que es lo que haría un barrido: `F_f − F_m` tiene más de una raíz y las lejanas
no son solución de nada —el círculo de Talbingo del problema 6 encontró un
cruce en λ = −0,979 antes del real en +0,419 y devolvió 1,6826 contra 2,292
publicado—. Ese círculo **hoy no puede llegar** a esta función (sus λ
resolubles son todos admisibles y la rejilla por defecto empieza en −0,1), y
decirlo es el punto: lo que protege es el orden, no el accidente de un rango.

**`spencer.py` y `gle.py`**, escrito dos veces e idéntico: un bloque **después**
de `refine_lambda_gap` y antes de la salida de reserva, más dos claves de
`details` en las dos salidas.

## POR QUÉ DESPUÉS DEL REFINADO Y NO ANTES, con mis dos razones refutadas

Argumenté ANTES por dos motivos y los dos eran malos. **(a) «que el refinado vea
el conjunto más lleno» es VACUA**: si el rescate acierta, `bracket` deja de ser
`None` y el refinado no corre; si falla, se revierte y el refinado ve el
conjunto de siempre. **No hay ningún camino** en el que vea nada más lleno. **(b)
«el refinado quema sus pasos para nada» es cierta sólo en la familia B2** y
apunta al revés: esas sondas desperdiciadas **quedan grabadas** como pares
rechazados, así que ponerlo después hereda un conjunto recuperado más denso al
mismo coste. Y lo que decide: puesto ANTES, la celda de cap 120 pasa de
`gap_refined = 1, edge_recovered = 0` a `gap_refined = 0, edge_recovered = 3`
—mismo λ y mismo factor a nueve cifras, pero **la fila cambia su relato de cómo
llegó**— y `lambda_gap_refined` perdería en silencio una de sus dos filas de
disparo. Puesto DESPUÉS, la escalera se lee **rejilla → extensión → hueco →
borde de empuje**, cada peldaño una afirmación más débil que el anterior.

## POR QUÉ NINGÚN NÚMERO DEL BANCO PUEDE MOVERSE, y es una identidad

El censo mide que **cero de 334 filas** ganan horquilla, y una fila que no gana
horquilla revierte y sale bit a bit igual. No hay ruta por la que un dígito
archivado pueda cambiar, así que **el banco no se re-corre y eso es una
identidad y no una omisión** —mismo argumento de v0.1.180—. Las dos claves
nuevas de `details` sí aparecen en el 100 % de las filas de Spencer y GLE, y
`ejecutar_caso.py` las lee con `.get()`, así que no mueven nada archivado; se
dice aquí en vez de venderlo como «nada se mueve».

**Alcance, dicho porque un cero sin su límite se lee como si no lo tuviera:**
esto cubre las superficies **ARCHIVADAS**. Una búsqueda evalúa miles, así que
**0 es cota inferior** sobre esa población, igual que el «21 es COTA INFERIOR»
de v0.1.179.

## LO QUE SE IBA A HACER Y NO SE HACE, con la medida delante (regla 7)

La salida de **reserva** pone `admissible` según **qué pasada** produjo la
muestra (`spencer.py:308`), mientras la salida con horquilla lo deriva del
**estado devuelto** y explica por qué doce líneas más abajo: «a bisection can
land on a lambda its bracketing samples did not share». Son dos reglas
distintas para la misma bandera, y la decisión tomada era corregirlo aquí con su
propio interruptor y una tabla de atribución de cuatro celdas.

**Medirlo lo tumbó.** De las **48** filas del banco que salen por reserva,
**CERO** discrepan entre la bandera publicada y `thrust_is_admissible` evaluado
en el λ devuelto; las tres únicas con `admissible = False` lo tienen bien
puesto. Un interruptor que no mueve nada es el ajuste que no hace nada, que es
la regla 7 al revés, así que **se retira de esta versión y sale como ficha
D156** con su evidencia. La inconsistencia es real y está latente: bastaría una
relajación más ancha —la que la propia ficha de D149 proponía— para que mordiera
al día siguiente.

## REPORTADO Y NO CORREGIDO (regla 6)

- **D156** — las dos salidas de Spencer/GLE derivan `admissible` con reglas
  distintas; hoy coinciden en las 48 filas medidas y por eso no se toca.
- **D157** — `refine_lambda_gap` **sólo mira los dos EXTREMOS** del conjunto
  muestreado (`rows[0]` y `rows[-1]`) y los nodos más allá de ellos, de modo que
  **un nodo perdido ENTRE dos muestras supervivientes le es invisible**. El
  rescate de esta versión cubre el caso cuando la causa de la pérdida es el
  empuje, y **no** cuando es que la rama no resuelve. En el banco hay 329 filas
  con algún nodo perdido.

## ERRORES PROPIOS DETECTADOS ANTES DE PUBLICAR

Nueve, y el primero habría hecho falso el censo entero:

1. **El clasificador del censo decidía «caso A» mirando rejilla + extensión**, y
   el motor lo decide **sólo con la rejilla estricta**, antes de muestrear la
   extensión siquiera. Lo cazó el control: esperaba `A` en cap 137 y contestó
   `B2`. Mi primer impulso fue corregir la expectativa, que era exactamente lo
   contrario de lo que había que hacer. (Comprobado después que no mueve el
   resultado del banco: las 3 filas `A` son las mismas en las dos corridas.)
2. **Las dos razones para poner el rescate antes del refinado**, arriba.
3. **`lambdas_lost_to_thrust_tension = n_thrust_rejected`** habría publicado un
   número **doblado**: ese contador incrementa **fuera** del `if self.strict`, de
   modo que el barrido todo-o-nada lo cuenta dos veces. Se publica
   `len(thrust_rejected_pairs)`, que está indexado por λ y de-duplica solo.
4. **Decidir el interruptor B antes de medirlo**, y medirlo después lo retiró.
5. El bloque nuevo de `interslice.py` quedó insertado **entre `GAP_REFINE_STEPS`
   y su propio interruptor**, separando una constante de su switch; movido
   detrás de `refine_lambda_gap`.
6. El ancla de 16 espacios del parche de `details` casaba **dentro** de la de 20,
   así que el reemplazo contó dos. No se escribió nada porque la aserción saltó
   antes del `write` — la lección es que el parche asere el número de casos.
7. La cabecera del test traía un reparto **inventado** (7/8) y afirmaba que un
   caso lo comprobaba mecánicamente, que era falso. El reparto real, **ejecutado
   contra el árbol viejo con `git stash`**, es 7/16.
8. **Un parche por heredoc de más de 8 KB**, que Bash corta con «unexpected EOF
   while looking for matching quote»: la trampa que AGENTS.md tiene escrita y
   que este proyecto lleva pisada versión tras versión. No se escribió nada
   —el corte es antes del `write`— y el fichero se comprobó intacto (8624
   líneas) antes de rehacerlo por archivo.
9. Un parche sobre `ERRORES_Y_DISCREPANCIAS.md` que buscaba `ultimo` donde el
   texto dice `último`. Saltó la aserción y no se escribió nada, que es la
   razón de que cada parche de esta versión asere **cuántas veces** casa su
   ancla antes de tocar el archivo: los dos errores de arriba se cazaron solos
   por eso, y el de las 16 columnas también.

## EL TEST

`tests/test_lambda_edge_v1182.py`, **23 casos en siete clases**, y **ninguna
aserción fija un factor de seguridad contra un valor de referencia**: todo es la
forma cerrada calculada en el propio archivo, una identidad, un A/B en proceso o
un recuento. La fixture se escribe **en código** porque `tests/` no puede
alcanzar el banco, y el sistema se construye **como lo construye el método**
(molde de `test_anchored_wedge_root_v1177.py`) y no con el `_system()` de v1159
que pasa `sup=None` y mide otro sistema.

Contra el árbol de 0.1.181 con sólo este fichero añadido **fallan 7 y pasan 16**,
y el reparto va **nombrado**: cinco fallan por diferencia medida en la respuesta
publicada y **dos por la ausencia del símbolo**, que es discriminación débil y va
etiquetada como tal en vez de contada como fuerza. De los 16 que pasan, tres
están **hechos** para pasar —describen el comportamiento viejo a través del A/B—
y el resto son las dos clases de CONTROL más `TestWhatItDoesNotTouch`, cuya
única función es seguir verde.

`TestWhatItDoesNotTouch` es la **reversión ejecutada** y no afirmada en prosa:
compara nueve claves de `details` y el factor, con el interruptor puesto y
quitado, en la capacidad curada, en la de familia A y en **Spencer sobre la
misma fixture**, que es el control más afilado del fichero —misma cuña, misma
capacidad, el método que no se puede mover—.

`test_fallback_origin_v1175.TestTheKeysTheBankCounts` gana un caso para las dos
claves nuevas, porque esa clase existe justamente para que un renombrado no deje
una columna del banco vacía en silencio.

## VERIFICACIÓN

- Suite entera y sin argumentos **3929/3929** sobre el árbol final y sin banner
  `FILTERED RUN`. 0.1.181 traía **3905**, y los **+24** son exactamente los 23
  casos del fichero nuevo más el que gana `TestTheKeysTheBankCounts`. El
  recuento se cuadró contra `grep` de los métodos en `tests/`, que da 3929
  clavados, porque un total que no se explica no es evidencia de nada.
  Corrida **dos veces y las dos en verde**, y las dos **solas** en la máquina:
  la segunda es la que cuenta, sobre el árbol final y con el changelog ya
  escrito, que es lo que `test_version_consistency_v176` exige. El censo del
  banco y la primera corrida NO se solaparon a propósito —dos procesos
  peleándose por los mismos núcleos es el ruido que AGENTS.md ya tiene
  documentado—.
- `generar_comparativa.py` regenerado: `COMPARATIVA_Slide2_vs_OGR.md` y
  `PROGRESO.md` salen **byte a byte idénticos** a los de antes del cambio, que
  es la forma más fuerte de la identidad de arriba: no es que no se haya
  mirado, es que no hay nada que mirar.
- `auditoria_invariantes.py` a **0 ERROR** (748 hallazgos: 491 AVISO, 257
  INFO), el mismo reparto exacto que 0.1.181.
- `verificar_cierres.py D149` → **CUBIERTO POR TEST**, y comprobado que
  **DISCRIMINA por los dos lados** con un parche en proceso: con
  `LAMBDA_EDGE_RECOVERY` apagado contesta NO SE SOSTIENE, y sin el símbolo
  contesta NO SE SOSTIENE nombrando la causa («el motor no tiene
  `LAMBDA_EDGE_RECOVERY`: el lambda que el criterio aparta sigue sin poder
  volver»).
- Ficha retirada al índice; D149 podado de P2 **en el markdown Y en
  `generar_prompts.py`**, que es donde de verdad viven los paquetes; el
  renglón de P2 corregido **entero** —descripción y cadena tachada, no sólo el
  propio eslabón—; prompts regenerados con **salida 0**, 45 prompts, 0 fichas
  cerradas sin prompt y **0 sin paquete**. Fichas nuevas **D156** y **D157**
  con su prompt largo y su paquete; serie movida a D157, siguiente libre D158.
- Instantánea `Evaluaciones/0.1.182` congelada: 1634 archivos comprobados byte
  a byte, y su reparto de versiones es **idéntico** al de 0.1.181 —0.1.97=9,
  0.1.147=1, 0.1.160=24, 0.1.163=2, 0.1.170=11, 0.1.173=126, 0.1.178=17,
  0.1.179=31, 0.1.181=17 y 2 sin anotar—, o sea que **ni un archivo se
  re-selló**.
- El banco **no** se re-corre, y es una **identidad y no una omisión**: el
  censo mide que cero de 334 filas ganan horquilla, y una fila que no la gana
  revierte y sale bit a bit igual.

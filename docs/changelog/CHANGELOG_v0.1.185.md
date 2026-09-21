# OGR Slip2D v0.1.185

**Dos fichas del banco en una tanda, y de las dos hubo que corregir primero la
medida con la que estaban escritas.** D155 decía que la búsqueda de camino no
circular es *guiada*: es falso, y la prueba que la ficha daba usaba el
predicado equivocado. D156 decía «0 discrepancias de 48 filas»: el denominador
real es **3**, y en esas 3 la discrepancia es imposible por construcción — lo
que a su vez es el argumento para construir el testigo a mano, que es lo que
convierte su arreglo en un cambio que mueve un número en vez de en un ajuste
que no hace nada.

El cambio de motor son **dos claves nuevas en `details`, un interruptor y una
bandera que pasa a leerse de otro sitio**. Cero filas del banco se mueven, y
eso está medido y no supuesto.

---

## D155 — LA PREMISA ERA FALSA, Y LA FICHA MEDÍA SU PROPIO DEFECTO CON `is_valid`

La ficha dice que las superficies que la búsqueda de camino genera dependen de
los factores que va obteniendo, y que por eso el 085 saltó +37,03 % y +11,90 %
al re-correrse en 0.1.181. Como prueba ofrece que la crítica que 0.1.178
archivó «sigue existiendo y sigue siendo **válida**»: 1,513872 con
`is_valid=True`.

**`is_valid` no es el predicado.** `SearchResult.critical`
([search.py:293-323](../../ogr_slip2d/search.py#L293-L323)) construye `ok` con
las válidas **y admisibles** y sólo cae al conjunto entero cuando `ok` está
vacío (`pool = ok or valid`). Esa superficie sale hoy `is_valid=True` y
**`admissible=False`**, y con 2907 de 5000 inadmisibles el bote no está vacío:
queda fuera **correctamente**, por una preferencia que el motor aplica desde
v0.1.130.

### La trayectoria sí es reproducible, y hacen falta tres medidas para decirlo

| medida | resultado |
|---|---|
| `bishop_simplified` del 085 entre las dos versiones | **idéntico bit a bit** en las dos mitades: `generadas=36559`, `validas=5000`, `invalidas=31559`, `fos=1,505885`, y hasta `fos_optimizado=1,429714`. Bishop no pisa `interslice.py`: si la trayectoria la dirigiera el evaluador, esta fila se habría movido con el resto del archivo |
| el generador reproducido, con `evaluate_surface` parcheado a `None` (100 000 intentos, 17 s) | las DOS críticas —la de 0.1.178 y la de 0.1.181— salen de **la misma secuencia**: índices 5075 y 6514 en la mitad pasiva, 11994 y 17629 en la activa, casadas a 6e-5, que es el redondeo del JSON archivado |
| ¿se perdió en la cola que la corrida nueva ya no genera? | **no.** La corrida nueva es más CORTA (34 175 y 65 138 contra 38 461 y 73 009) y los cuatro índices están muy dentro |

Es decir: la superficie que la ficha da por perdida **se genera hoy, se evalúa
hoy y está hoy en `result.evaluations`**. No se perdió: quedó descalificada.

### La atribución no es la versión que la ficha nombra

Apagando los interruptores de `interslice.py` uno a uno sobre esa superficie:

```
enviado 0.1.184               fos=1.513872  ADM=False  lam=1.046875
solo BRANCH_PAIR_TIGHTEN OFF  fos=1.512355  ADM=True   lam=1.0     <- 1,512356 archivado
solo BRANCH_PAIR_SETTLE  OFF  fos=1.513872  ADM=False
solo LAMBDA_GAP_REFINE   OFF  fos=1.512356  ADM=False
(los otros cuatro, idénticos al enviado)
```

`BRANCH_PAIR_TIGHTEN` es **D145 / v0.1.179**, no D148 / v0.1.181, que es a lo
que la ficha lo atribuye. Y el **control nulo** es lo que separa «se movió la
elegibilidad» de «se movió todo»: Bishop sobre el mismo modelo da 1,439695251
con el interruptor puesto y apagado.

### El mecanismo, que es lo que le da nombre nuevo a la ficha

Las cuatro superficies del 085 salen por la **salida de reserva**: no hay
horquilla en λ, y el factor publicado es la inclinación muestreada más cercana
(`F_f − F_m` = 0,017 contra una tolerancia de 1e-4). Midiendo `Σ E_interior` en
el λ devuelto, con el contexto sostenido:

| | fos | adm | λ | Σ E | margen |
|---|---|---|---|---|---|
| pasivo, crítica de 0.1.178, motor de hoy | 1,513872 | False | 1,046875 | −22 075,83 | −0,627 |
| la misma, con `BRANCH_PAIR_TIGHTEN` apagado | 1,512355 | True | 1,0 | **+2 214,43** | +0,044 |
| pasivo, el mínimo que se publica hoy | 2,072412 | True | 0,625 | **+224,79** | **+0,0076** |
| activo, el mínimo que se publica hoy | 2,312503 | True | 0,0 | +11 494,85 | +0,451 |

**Un cambio del 0,10 % en el factor mueve la resultante del empuje de +2214 a
−22 076 y le cambia el signo.** El factor es insensible a λ cerca de la
respuesta; el empuje no. Y el mínimo pasivo que se publica hoy está a **+0,76 %
del borde**: es el siguiente en volcar.

### Las dos ramas del criterio de cierre eran inejecutables

- «Que la búsqueda devuelva el mismo mínimo cuando la superficie anterior sigue
  siendo **válida y menor**» pide que `critical` deje de aplicar la preferencia
  de empuje, que es la decisión D37/C1 escrita en `spencer.py`.
- «Etiquetarlo como **valor de trayectoria**» sería una etiqueta falsa.
- Y la opción (a) de la ficha —arranques múltiples, o sembrar con el mejor de
  la corrida anterior— **es provablemente inerte sobre la fila que la motiva**,
  porque la superficie ya está en la lista. Sería un ajuste que no mueve el
  número, que es la regla 7 al revés. `TestMultiStartCannotRecoverA
  DisqualifiedSurface` lo ejecuta en vez de razonarlo: se inyecta por
  `user_evaluations`, que es el canal que ya existe para una superficie venida
  de fuera, y `critical` la sigue sin elegir.

Por eso la ficha queda **RE-ENUNCIADA** y no cerrada ni arreglada, y por eso
esta versión **no toca la búsqueda**.

### El censo que la ficha pedía es aritméticamente imposible

Pedía cuántas de las filas no circulares cambian de crítica entre 0.1.180 y
0.1.181. **35 de los 38 archivos no circulares los escribió 0.1.173** y uno
0.1.147, y son idénticos byte a byte en las dos instantáneas: la pregunta sólo
puede contestar «las dos mitades del 085», y lo contestaría por aritmética.
Publicar ese «2 de 39» sería el cero falso de D101, D103, D118, D127, D129 y
v0.1.175 otra vez, y esta vez escrito en el cierre de una ficha. Sale como
**D162**.

### Lo que se mide en su lugar, y es PREDICTIVO

`_tools/elegibilidad_critica_d155.py` (banco, **SOLO MIDE**) recorre la crítica
archivada de cada fila de Spencer/GLE, la re-evalúa con el motor de hoy y
publica, separados, `is_valid`, `admissible`, `adm_por_empuje` y el **margen**
`Σ E / Σ|E|` en el λ devuelto — o sea a qué distancia del cambio de signo está
el veredicto. Informe en `docs/audits/path_eligibility_v1185.md`.

| | banco vivo | contra `Evaluaciones/0.1.180` |
|---|---|---|
| filas / medidas / descuadradas / saltadas | 236 / 230 / 6 / 8 | 236 / 229 / 7 / 8 |
| vuelcan | **0** | **3**, las tres no circulares del 085 |
| con \|margen\| < 0,05 | **14** | 12 |

Las 14 al borde son siete por debajo de **0,003** y todas de los problemas
reforzados 085, 087, 090, 093 y 094. Esa lista es una predicción: son las filas
que volcarán en la próxima versión que toque el solver de ramas, y ahora se
saben antes.

### Tres correcciones al molde de censo heredado, y una de ellas la enseñó la propia herramienta

- **(A′) ida y vuelta geométrica**: la poligonal archivada tiene que definir la
  misma masa (mismo número de dovelas, mismo tramo en x).
- **(A″) reconstrucción del motor viejo**, y aquí está el error propio. El
  control de D148 —que el factor recalculado reproduzca el archivado dentro de
  `CONTROL_PC = 0,01 %`— **habría tirado justo la fila que importa**, cuya
  deriva real es +0,10 %. Lo que sí debe reproducirlo es el factor con los
  interruptores apagados… y la primera versión de la herramienta los apagaba
  **todos**, lo cual reconstruye un motor **más viejo que el del archivo**:
  sobre el 085 pasivo apagaba también `BRANCH_RESCUE`, que es de v0.1.176 y ya
  estaba encendido cuando 0.1.178 escribió el archivo. El factor se iba un
  0,415 % en vez de un 0,0001 % y **la fila que motiva la ficha salía
  DESCUADRADA por culpa del medidor**. Corregido: cada interruptor lleva la
  versión que lo estrenó y se apagan sólo los posteriores al archivo. Con eso,
  0 descuadradas en el 085 y las 3 filas que vuelcan aparecen.
- **(D) contexto sostenido**: cada fila se mide entera dentro de su contexto y
  dos veces dentro de él. Existe porque **la primera medida del margen de esta
  misma tanda recalculó `Σ E` con los interruptores ya restaurados y publicó
  una discrepancia falsa** (ver más abajo).

### Lo que cambia fuera del motor

`generar_comparativa.py` gana la marca **⚠ N descartadas** pegada al número de
*FoS OGR (búsqueda)* — molde `marca_adm` de D79, **no** un `Estado` nuevo,
porque `balance_evaluaciones.RANGO` es un enumerado cerrado y un estado nuevo
rompe el balance entre instantáneas; y **no** una columna propia, porque el
criterio de `marca_reserva` es que una columna se justifica cuando hay DOS
números en la fila que pueden venir por caminos distintos, y aquí el que hace
la afirmación es uno solo. La clave `inadmisibles` se añade en **las dos ramas**
de `filas_familia()`, que es la trampa que D52/D70 ya pagaron con
`estado_forzado`.

Más dos renglones **generados** en la cabecera de la tabla, molde
`_renglon_convergencia`, porque una cifra que sólo vive en el informe que la
midió no la lee quien usa la tabla: **Mínimo admisible (D155)** y **Medido con
(D162)**, este último contando `version_ogr` archivo a archivo. Ése es el
etiquetado honesto que la ficha pedía, diciendo lo que es verdad en vez de
«valor de trayectoria».

---

## D156 — EL DENOMINADOR NO ERA 48, ERA 3, Y ESO ES LO QUE ABRE EL ARREGLO

La ficha dice que de las 48 filas del banco que salen por reserva, cero
discrepan entre la bandera publicada y `thrust_is_admissible` evaluado en el λ
devuelto, y que por eso v0.1.182 retiró el arreglo: un interruptor que no mueve
nada es la regla 7 al revés.

**De esas 48, 45 no disparan el bloque de v0.1.106**: tienen nodos
supervivientes, así que `inadmissible` vale `False` y las dos reglas coinciden
trivialmente. Y **las 3 que sí lo disparan** —047 `resultados.json` spencer,
060 y 090 `referencia.json` spencer, todas familia A— **no tienen ningún
superviviente**, de modo que no existe ninguna muestra admisible sobre la que
`min |g|` pueda caer: la discrepancia es **imposible por construcción y no por
suerte**. La cifra honesta es **0 de 3**.

Eso no debilita la decisión de v0.1.182: la refuerza, y a la vez dice
exactamente por qué el banco archivado **nunca** podrá dar población. Que es el
argumento para ir a buscar el testigo a otro sitio en vez de repetir el censo.

### El censo medía un compuesto, y por eso publicaba una discrepancia sin explicar

`borde_admisible_d149.py` llega a la superficie por
`build_search(...).evaluate_surface(...)` —con razón documentada: un
`SlipCircle` reconstruido a pelo hace que el rebanador tome la primera masa por
la izquierda— y ese camino pasa por `BaseSearch._check_surface`, que en
[search.py:583-584](../../ogr_slip2d/search.py#L583-L584) escribe
`result.admissible = False` **encima** de lo que el método decidió, por tracción
en la base o por m-alpha, y nunca lo devuelve a `True`. El censo llamaba
`admisible` a esa mezcla.

Se separan los dos escritores (`adm_por_empuje`, leído de `details`, frente a
lo que pisa la búsqueda), el contador **deja de filtrar por `reserva is True`**
—que es lo que escondía la única discrepancia del censo, la fila 012 gle, que
es de la salida CON horquilla— y `resumen()` gana los tres denominadores. Sobre
0.1.185: **48 en reserva, 3 disparan el bloque, 0 pueden discrepar, 1
discrepancia en todo el censo y 0 del método**.

### El testigo, y por qué es de GLE

`lambda_grid()` y `lambda_grid_extension()` son métodos normales de
`LEMMethod`, o sea el **andamiaje** de la búsqueda y no la física. Subclasificar
el método deja colocar los nodos a mano **sobre un modelo y una superficie que
no tienen nada de sintéticos**: el plano de 45° con ancla pasiva de 120 kN/m de
`test_lambda_edge_v1182`, familia B1 de D149, el único caso medido con la
frontera de admisibilidad **por debajo** de la raíz (λ_E = 0,108, λ_g = 0,190).

Rejilla en −0,05 / 0,00 / 0,05 —los tres inadmisibles, los tres del mismo signo
de `g`, así que el barrido de v0.1.106 dispara y nada horquilla— y extensión en
0,15, dentro de la ventana. El motor de 0.1.184 publica entonces `admissible`
**FALSE** sobre un estado cuyo empuje interior suma **+0,78 kN/m**, con una nota
que afirma que «ningún λ deja el empuje interdovela en compresión neta» sobre
un λ que hace exactamente eso.

Y es de GLE por una razón que se puede nombrar. Barrida la misma familia
anclada para Spencer —3 ángulos de talud × 2 aplicaciones × 4 orientaciones × 8
capacidades, **192 celdas**— λ_E no cruza en ninguna. La razón está en una
línea: con la forma constante de Spencer la suma del empuje interior va de
−2,29 a −1,39 a lo largo de toda la rejilla sin llegar a cero, mientras que con
la media senoide de GLE va de −4,52 a +13,13. **La función de forma es lo que
mete las caras en compresión aquí**, así que el testigo es del método que tiene
una.

### El cambio

En `spencer.py` y su gemelo `gle.py`, la salida de reserva:

- `force, _moment = system.states(lam_star)` ya estaba calculado veinte líneas
  antes. Debajo, `estado_inadmisible = force is None or not
  thrust_is_admissible(force)`.
- `admissible` pasa a salir de ahí, gobernado por
  `interslice.THRUST_FLAG_FROM_STATE` (leído en tiempo de llamada, molde de
  `BRANCH_RESCUE`).
- `details` gana **`thrust_admissible`** —que esa salida no escribía, y por eso
  la única invariante que ata la bandera al estado
  (`res.admissible == res.details["thrust_admissible"]`, en
  `test_relaxed_thrust_v1130.py:190`) era **inexpresable justo en la salida que
  se equivocaba**— y **`thrust_margin`**, también en la salida con horquilla
  para que la clave exista en las dos y nadie tenga que saber por cuál salió.
  **Esas dos claves NO llevan interruptor**: una medida que se puede apagar no
  es una medida, y no mueven ningún número.

**La nota se ata a la bandera y su texto no se toca.** La sentencia conflaba
dos hechos —«ningún λ de la rejilla era admisible» y «el λ devuelto está en
tracción»— y en el testigo afirmaba el falso. Atarla a la bandera basta para
que deje de escribirse ahí, que es toda la reparación; re-escribirla habría
roto `test_relaxed_thrust_v1130.py` por un motivo que no tiene nada que ver con
este defecto. El hecho que la frase también llevaba —que la rejilla hubo que
re-muestrearla— sobrevive en `lambdas_lost_to_thrust_tension`, que cuenta
exactamente los λ que la pasada estricta apartó.

### La tabla de atribución, ejecutada en el test y no escrita a mano

| `THRUST_FLAG_FROM_STATE` | `admissible` publicado | `details["thrust_admissible"]` | λ | factor |
|---|---|---|---|---|
| off | **False** | True | 0,15 | 1,308613457 |
| **on** | **True** | True | 0,15 | 1,308613457 |

Un solo interruptor, una fila que se mueve, y el factor **idéntico al último
bit**: esto decide cómo se llama la respuesta, nunca cuánto vale. El control es
la misma cuña con la rejilla de fábrica, que horquilla y da 1,308737259 con
`admissible=True` en los dos lados.

### Por qué ningún número del banco puede moverse

`LEMResult.to_dict()` **no serializa `details`**, así que las dos claves nuevas
no tocan un byte de ningún `resultados*.json`; y `ejecutar_caso.py` escribe un
juego curado de claves por método. La bandera sí se archiva, pero el censo dice
que ninguna fila la cambia: 0 de las 3 en las que sería posible, y las 3 no
pueden. El censo de D149 re-corrido sobre 0.1.185 devuelve **exactamente** el
mismo reparto que sobre 0.1.182 —340 filas, 334 medidas, 310 sin rechazos, 3
en A, 1 B_ok, 20 B_sin_horquilla, 48 en reserva— y la escalera de cuñas de
control sigue dando 120→B1, 134→B2, 137→A.

---

## LA RE-CORRIDA DEL LOTE NO CIRCULAR, QUE ES EL REMEDIO CARO DE D162

Se pagó el mismo día, por decisión del propietario: **37 de los 38 archivos no
circulares re-corridos con 0.1.185**, en ocho lotes ordenados de barato a caro,
**4 h 02 min** más 13 min de un repaso, **cero fallos**. El 38.º es el `3b` del
078, declarado `reproducible: false` con motivo escrito.

**El lado A no es homogéneo y por eso se publica por fila**: de los 37,
**35 los había escrito 0.1.173** y 2 el 0.1.181.

### El resultado, y es lo que deja D162 abierta en vez de cerrada

De **97 filas de método, sólo 6 se movieron**, y el máximo es **1,545 %**:

| problema · archivo | método | ver. A | fos A | fos B | Δ % |
|---|---|---|---|---|---|
| 103 `modelo_1.6` | spencer | 0.1.173 | 1,317420 | 1,337774 | **1,545** |
| 103 `resultados` | spencer | 0.1.173 | 1,227443 | 1,220941 | 0,530 |
| 103 `modelo_1.5` | spencer | 0.1.173 | 1,303875 | 1,298146 | 0,439 |
| 070 `no_circular_2` | spencer | 0.1.173 | 1,641359 | 1,642873 | 0,092 |
| 085 `no_circular_pasivo` | spencer | 0.1.181 | 2,072412 | 2,071732 | 0,033 |
| 062 `no_circular_seco` | spencer | 0.1.173 | 1,039198 | 1,039099 | 0,010 |

Las seis son Spencer. Once versiones de motor —de 0.1.173 a 0.1.185, con D145,
D148, D149, D152, D153 y ésta dentro— mueven la familia no circular **como
mucho un 1,5 %**. La obsolescencia era real y su consecuencia numérica,
pequeña; **pero eso sólo se sabe después de pagar la corrida**, y es
exactamente lo que no se podía afirmar antes de pagarla.

Y **el +37 % del 085 no se revierte**: pasivo · Spencer da 2,071732 contra los
2,072412 archivados. La crítica de 0.1.178 sigue siendo inadmisible y sigue
fuera, que es lo que esta versión afirma.

`balance_evaluaciones.py` contra `Evaluaciones/0.1.184`: **559 → 559 filas,
549 IGUAL, 0 sin pareja**, y tres cambios de estado — 103 `1,5` de REVISAR a OK,
103 `1,6` de OK a REVISAR, y uno que hay que contar aparte.

### El que hay que contar aparte: el 077, y no es la búsqueda

**77 · no circular · caso2_piezometrica · Spencer pasa de `OK` (+0,54 %) a
`DISCREPANCIA` (−12,16 %)**, y la búsqueda no tiene nada que ver:

| | crítica | fos de búsqueda | generadas | válidas | `fos_optimizado` |
|---|---|---|---|---|---|
| spencer, 0.1.173 | — | 1,761832 | 28 870 | 1098 | 1,578525 |
| spencer, 0.1.185 | **idéntica** | **1,761832** | **28 870** | 1101 | **1,379141** |
| bishop, los dos lados | **idéntica** | 1,759541 | 28 870 | 1101 | **1,656771** idéntico |

Misma superficie de partida, misma semilla de optimización (20260819), mismos
ajustes — y la superficie optimizada sale distinta, **−12,6 %**. Bishop, en el
mismo archivo y con el mismo paseo, no mueve un dígito: es el control nulo
metido en la propia fixture.

O sea que **la palabra «guiada» de la ficha D155 es cierta — del paseo de
`optimize.py`, no de `PathSearch`**. Ahí sí, por construcción: un `trial` que
no puntúa se salta y `best_pts` cambia o no según el factor. Está medido, con
su control al lado, y engorda **D161**, que además sale de la corrida con
denominador propio: **9 filas en 3 problemas** (057, 079, 085) archivan
`fos_optimizado` nulo teniendo mínimo de búsqueda, y **el testigo sobrevivió a
la re-corrida**, que no es obvio — D146 y D149 se escribieron sobre testigos
que ya estaban curados.

### Un error propio de esta parte, y la corrida no lo habría cantado

Armé los ocho lotes a partir del **nombre** de los archivos
(`resultados_no_circular*.json`) en vez de a partir de `tareas()`, que es quien
decide qué corre el lanzador. El 057 y el 103 declaran su mitad no circular en
archivos que no se llaman así, de modo que **cuatro escenarios se quedaron
fuera y el resumen decía «0 fallos»**. Lo cazó contar `version_ogr` después, no
el lanzador: `correr_no_circular.py` no tiene por qué avisar de lo que no se le
pidió. La regla es la de siempre — la selección se toma de la herramienta, no
al lado de ella.

### Y el censo, repetido, NO mide la misma población

El censo de elegibilidad se tomó dos veces, antes y después de la corrida, y
**no son comparables**: 236 filas y 14 al borde antes, 237 y 13 después, porque
re-correr cambia la crítica archivada que el censo re-evalúa. Ninguno de los
dos está mal; hay que decir cuál es cuál. El que se publica en
`docs/audits/path_eligibility_v1185.md` y el que congela la instantánea son los
**de después**.

`instantanea.py 0.1.185`: **1646 archivos comprobados byte a byte**, con el
reparto de versiones declarado (0.1.185 = 37, y la mitad circular todavía con
91 archivos a 0.1.173, que es la otra mitad de D162).

---

## REPORTADO Y NO CORREGIDO (regla 6)

- **D160** — `PathSearch._run` para en `valid_count >= num_surfaces`, así que
  el TAMAÑO de la muestra es función de la tasa de validez: un motor que hace
  válidas más superficies **ve menos superficies**. Medido en el 085: generadas
  38 461→34 175 (pasivo) y 73 009→65 138 (activo), con bishop idéntico como
  control. Nada se reordena —la corrida corta es un **prefijo** de la larga— y
  no es la causa del 085, porque los cuatro índices críticos están muy dentro.
  Latente, y es el mecanismo por el que un cambio futuro del evaluador sí
  perderá una superficie que existe.
- **D161** — en el 085 pasivo vivo, `fos_optimizado.spencer` es **null** («la
  superficie optimizada no da factor de seguridad → no λ-bracket») y GLE dice
  «la optimizacion no devolvio superficie»; en 0.1.178 valía 1,488157. La
  cascada `f_opt → f_busq → f_sin` de la comparativa lo absorbe **en silencio**,
  de modo que esa fila publica el mínimo de la búsqueda donde el manual publica
  un optimizado.
- **D162** — la mitad no circular del banco la midió 0.1.173 (35 de 38
  archivos; uno, 0.1.147), y por eso el censo que D155 pedía era imposible. Con
  el coste medido delante: 3,9 h el lote en 0.1.160, +47 % en el único caso
  medido en las dos épocas, del orden de 5,2 h por lado hoy.

Y una pregunta que esta versión deja encima de la mesa sin abrirla: si
`thrust_is_admissible` —`math.fsum(E_interior) > 0.0`, estricto— debería llevar
una **banda muerta relativa a la escala de `E`**. En las filas reforzadas
descarta el 58 % de las válidas y el veredicto de siete de ellas vive a menos
del 0,3 % de la escala. Es un cambio de criterio: mueve el banco entero, pide
su propia ficha y **una referencia externa que hoy no está escrita** — Spencer
(1967) y Ching & Fredlund (1983) justifican el signo, no una banda.

---

## ERRORES PROPIOS DETECTADOS ANTES DE PUBLICAR

Cinco, y dos de ellos habrían publicado un número falso.

1. **La primera medida del margen recalculó `Σ E` con los interruptores YA
   RESTAURADOS**, porque el `finally` que los devolvía corría antes de llamar a
   `states(λ)`. Publicó `admissible=True` sobre un estado con `Σ E = −22 636`,
   o sea **una discrepancia de D156 que no existe**, y estuve a punto de
   escribirla como hallazgo. Con el contexto sostenido, el mismo λ da
   **+2 214** y las dos reglas coinciden. De ahí sale el control (D) de la
   herramienta, que mide cada fila dos veces dentro de su contexto.
2. **El control A″ apagaba todos los interruptores**, incluido
   `BRANCH_RESCUE` (v0.1.176), que ya estaba encendido cuando 0.1.178 escribió
   el archivo. Reconstruía un motor más viejo que el del archivo, el factor se
   iba 0,415 % y **la fila que motiva la ficha salía descuadrada por culpa del
   medidor**. Lo cazó ejecutar la herramienta sobre el 085 y no leerla.
3. **Copié la cresta de la cuña (38) en la fixture prestada del círculo
   reforzado, que la tiene en 50.** El modelo dejó de horquillar y las dos
   puertas del método salieron como una; lo cazó
   `test_the_flag_and_the_detail_agree_in_both_exits`, que se niega a pasar si
   no ha visto las dos salidas — la aserción que existe justo para esto.
4. **`test_the_sign_of_the_margin_is_the_verdict` pasaba EN VACÍO** contra el
   árbol viejo: se saltaba las filas sin margen con un `continue` y no
   afirmaba nada, así que un árbol que no escribe ninguna de las dos claves lo
   veía verde. Un caso que mide cero cosas y reporta éxito es la forma de fallo
   que este proyecto ya conoce. Lleva contador y exige las cuatro.
5. **El lector de la comparativa de `auditoria_invariantes.py` se quedó
   viejo**, y lo dijo él: `la COMPARATIVA del disco no es la que sale de los
   datos: 198 filas nuevas, 198 filas viejas`, que son exactamente las filas
   que llevan la marca. Construía la celda con `fmt(f["f_busq"])` a secas en
   vez de por la función que la emite — y el párrafo que hay tres líneas más
   abajo **ya deja escrita esa misma lección para `marca_adm`**, donde costó
   «cuatro filas nuevas y cuatro viejas». No es que el invariante fallara: es
   que hizo su trabajo y yo no había leído su propio comentario.
6. **Tres subcadenas que `d155()`/`d156()` buscan por AST cruzaban un salto de
   línea** —`IS NOT THE PREDICATE`, `IDENTICAL between the two versions`,
   `WEAK discrimination`— y una subcadena que cruza un salto no puede casar
   nunca. Es exactamente la trampa que el changelog de v0.1.180 tiene escrita,
   y volví a pisarla. Y antes de eso, **un parche por heredoc con una barra
   doble**, que llega como una sola: la trampa que AGENTS.md tiene escrita.

---

## LOS TESTS

**`tests/test_thrust_flag_v1185.py`** — 23 casos en seis clases. Contra el
árbol de 0.1.184 con sólo este fichero añadido **fallan 11 y pasan 12**, y el
reparto va nombrado: **seis** por una diferencia medida en lo que el motor
publica (las dos claves ausentes, la invariante inexpresable, y el
`admissible=False` del testigo) y **cinco** por la ausencia de un símbolo, que
es discriminación débil y va etiquetada como tal. De los doce que pasan, los
cuatro de `TestTheSyntheticWitnessSeparatesTheTwoRules` pasan **a propósito**:
dicen lo que el defecto ES, leyendo el estado por `thrust_is_admissible` y no
por `details`, así que una diferencia ahí significaría que el defecto dejó de
existir y no que el arreglo funciona.

**`tests/test_path_population_v1185.py`** — 13 casos en cinco clases, y es un
fichero de **caracterización**: no cambia ninguna línea de motor, **no
discrimina contra 0.1.184 y todos sus casos pasan ahí**, lo cual se declara en
su cabecera en vez de esconderse. Lo que compra es que las cuatro afirmaciones
de arriba dejen de ser hallazgos de un changelog y pasen a ser cosas que la
suite se niega a dejar derivar. Ninguno de los 36 casos de los dos ficheros
fija un factor de seguridad contra una instantánea: son identidades, un
prefijo, aritmética de conjuntos y un contraste contra la forma cerrada.

---

## VERIFICACIÓN

- Suite entera y sin argumentos, **3999/3999**, sin banner `FILTERED RUN`,
  sola en la máquina y con el changelog ya escrito, que es lo que
  `test_version_consistency_v176` exige. 0.1.184 traía 3963; los +36 son
  exactamente los dos ficheros nuevos (23 + 13).
- `python tests/_runner.py relaxed_thrust lambda interslice` antes de tocar el
  motor: **189/189**, la línea base.
- `verificar_cierres.py D155 D156` → **D155 RE-ENUNCIADO**, **D156 CUBIERTO POR
  TEST**. Las dos funciones son nuevas: hasta ahora contestaban `SIN CRITERIO`.
- `borde_admisible_d149.py --ambos --informe` sobre 0.1.185 →
  `docs/audits/lambda_edge_v1185.md` y `censo_0.1.185.json`.
- `elegibilidad_critica_d155.py --informe` y `--desde 0.1.180` →
  `docs/audits/path_eligibility_v1185.md` y los dos censos.
- `auditoria_invariantes.py` a **0 ERROR** (748 hallazgos: 491 AVISO, 257
  INFO), el mismo reparto que en 0.1.184.
- `generar_comparativa.py` regenerada y `balance_evaluaciones.py` contra
  `Evaluaciones/0.1.184`: **559 → 559 filas, todas IGUAL, 0 sin pareja**. La
  marca vive en la celda 5, que `balance_evaluaciones.filas()` no lee — que es
  por lo que se eligió marca y no `Estado`.
- Y la comprobación de que el contrato «SOLO MIDE» se respetó: ni un
  `resultados*.json`, ni un `.ogr`, ni un `referencia.json` del banco tiene
  fecha de esta sesión.

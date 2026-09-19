# OGR Slip2D v0.1.179

**Defecto D145.** El estado que itera `interslice.solve_branch` es el **par
(F, X)** —factor de seguridad y empuje entre dovelas—, y su criterio de
aceptación preguntaba por la mitad: un paso bajo tolerancia más dos pasos
decrecientes, todo sobre F, nada sobre X. Ya no.

Lo que más enseña esta versión no es el arreglo, que son dos condiciones, sino
que **el diagnóstico llevaba dos versiones escrito dentro del propio motor** y
que la medición desmintió casi todo lo que la ficha daba por sentado —
incluida la mitad que yo mismo había dado por buena.

---

## 1. La frase que ya estaba escrita

El bloque `#:` de `RESCUE_OMEGA_MIN` dice desde v0.1.176, al explicar por qué el
rescate de rama acepta mirando el residuo del empuje:

> *«The thrust residual is what closes the door D116 measured — F sitting at the
> fixed point OF THE CURRENT X while X is still far from its own.»*

Esa frase era cierta y describía **medio solver**. El rescate ya calculaba
`d_x`, ya lo exigía y ya rechazaba con él; lo que nunca se hizo fue llevarlo al
camino ordinario, que es por donde pasa la inmensa mayoría de las ramas. Mismo
patrón que D144, donde el defecto llevaba cuarenta versiones escrito en el
docstring de un test.

---

## 2. De lo que la ficha daba por sentado, la medición desmiente casi todo

La ficha D145 daba dos síntomas, medidos con 0.1.175 y 0.1.176. **Ninguno de los
dos se reproduce tal como está escrito sobre 0.1.178**, y las dos razones
importan:

**(b) El nodo de batido del 087.** Sobre el círculo que la ficha nombra
(0,555556 · 16,823529 R 11,737803) la rama de momentos en λ = 3,0 sí se acepta
en la pasada 95 con el rescate apagado, tal como dice. Pero con el motor que se
envía **ya estaba rechazada**: el nodo cae en la pasada 95, o sea **pasada la
puerta del rescate**, y el rescate —que tiene esta comprobación desde el día
que se escribió— la echa y la rama se desboca en la 140. La mitad de (b) que
seguía viva es justamente la que el rescate no puede alcanzar, y el censo la
encontró en la **crítica archivada del mismo problema**, donde el nodo cae en la
**pasada 45** con el residuo del empuje a **885 veces la tolerancia** y
creciendo (610 → 674 → 752 → 848 → **884** → 924 entre las pasadas 35 y 46).

**(a) La espera del 091.** «λ = 0,36703» **no es un λ que la búsqueda
muestree**. Al λ que sí muestrea, 0,365133, la rama se acepta en la pasada 107
exactamente como dice la ficha. Fuera de la rejilla la misma rama **no se acepta
nunca** y la muestra se pierde por estancamiento, que es un síntoma peor que el
reportado, no más suave.

Y el mecanismo de (a) tampoco es el que la ficha describe. No es ruido de coma
flotante: los pasos **alternan** —6,10e-4, 6,22e-4, 3,18e-4, 3,26e-4, 1,65e-4,
1,71e-4— con la envolvente cayendo a la mitad cada dos pasadas, de modo que
`step < prev_step < prev_step_2` **no puede dispararse jamás** sobre una
secuencia alternante. Que la rama acabe aceptándose o no depende de en qué
pasada el redondeo rompe la alternancia, y eso es una moneda al aire: a
λ = 0,365133 sale cara en la 107; a λ = 0,36703 y a λ = 0,3677 no sale nunca y
la rama estanca en la 188 y en la 184.

---

## 3. El censo, que es lo que autorizó tocar el motor

`_tools/criterio_rama_d145.py` (banco, **sólo de medida**), sobre los 111
problemas: **344 casos, 6002 ramas, 5532 medidas, 18 saltadas con su motivo**.

Cómo mide `d_x` **sin copiar `solve_branch`**, que es lo que hace creíble el
censo: por definición `d_x(k) = max|X_k[i] − X_{k−1}[i]| / force_scale`, y los
dos vectores los devuelve el propio motor en `BranchState.boundary_x` de dos
llamadas con `max_passes = k` y `k−1`. No existe ninguna copia de la función,
luego no puede derivar de ella; es la misma resta sobre los mismos dos floats
que hace hoy el rescate; y `_force_scale` se importa en vez de reimplementarse.
Es el molde de `brazo_soporte_d144.py` —calcular el término desde su definición
y no leerlo del motor— aplicado aquí, y el de
`test_branch_contraction_v1172._iterate_at`, que ya usaba `max_passes` como
máquina del tiempo porque nadie más lee ese argumento.

**Los tres controles**, sin los cuales un censo no vale nada: la **reproducción**
(la llamada topada en `k*` devuelve el mismo `fos` bit a bit), el control
**contra el motor** (en toda rama rescatada el motor ya garantiza
`d_x < tolerance`, y el `d_x` reconstruido tiene que cumplirlo: **35 de 35, cero
fallos**) y el **denominador**, siempre publicado, porque un verificador que
compara cero cosas dice «0 movidos» y se lee como un éxito (v0.1.175).

Lo que contesta:

| medida | resultado |
|---|---|
| ramas aceptadas | 5240 |
| aceptadas con el empuje **por encima** de la tolerancia | **163** (3,1 %) |
| …de ellas, con el empuje **creciendo** | 53 |
| aceptadas que el criterio nuevo admite en la **misma pasada** | **5011** (95,6 %) |
| ramas que esperan más de 20 pasadas con el par ya asentado | 12 |
| fallos del control contra el motor | **0** de 35 |
| filas descuadradas (control > 0,01 %) | 7 |

Reparto de las 163 por `d_x`/tolerancia: **22** entre 1 y 2×, **47** entre 2 y
10×, **33** entre 10 y 100×, **25** entre 100 y 1000× y **36 por encima de
1000×**. Se aceptan entre las pasadas **3 y 80, mediana 13**, y **162 de las 163
antes de la pasada 80**, o sea fuera del alcance del rescate. Y las 12 que
esperan llegan hasta el `093 Spencer λ = 0,80`, asentado en la pasada 18 y
aceptado en la **136**.

**Son dos censos y no uno, y la diferencia hay que decirla.** El de arriba se
midió sobre el banco tal como estaba ANTES de re-correr nada. Repetido después
de la corrida, sobre el árbol de 0.1.179 y con los dos interruptores apagados
—que reproduce el motor anterior instrucción por instrucción, y por eso el
documento de auditoría es regenerable desde la versión que se envía—, da **6110
ramas, 5642 medidas, 223 aceptadas con el empuje vivo y 5060 en la misma
pasada**. No es una contradicción: el censo re-evalúa la superficie ARCHIVADA de
cada fila, y las de los 21 problemas re-corridos ya no son las mismas. Las
críticas nuevas, halladas con la puerta puesta, resultan tener MAS ramas que la
puerta rechazaría si se apagase. El documento publica la segunda, que es la
reproducible; la primera es la que autorizó el cambio.

El 96,9 % de las ramas aceptadas ya tenía el empuje bajo tolerancia, que era la
condición acordada para elegir el criterio de umbral (`d_x < tolerance`) frente
al de crecimiento (`no acepto si el empuje ha crecido`). El de crecimiento
queda descartado con la medida delante: dejaría dentro **36 ramas aceptadas por
encima de 1000 veces la tolerancia** por el accidente de que en esa pasada
concreta el residuo no estuviera subiendo.

---

## 4. El cambio

Un solo archivo, `ogr_slip2d/interslice.py`:

1. **Un solo bucle de X**, con `d_x` medido en **todas** las pasadas y con la
   misma aritmética que ya usaba el rescate, de modo que el rescate queda bit a
   bit. Desaparece la bifurcación `if rescuing:` de la actualización del empuje.
2. **Aceptación con dos limbos**, cada uno con su interruptor de módulo leído
   en tiempo de llamada, con el molde exacto de `BRANCH_RESCUE`:

   ```python
   ok_now = step < tolerance and d_x < tolerance
   if rescuing:                                   # sin cambios
       if ok_now and ok_before: ...
   elif _pass > 0 and step < tolerance and contracting and (
           d_x < tolerance or not BRANCH_PAIR_TIGHTEN):
       ...                                        # T — sólo puede RECHAZAR
   elif BRANCH_PAIR_SETTLE and _pass > 1 and ok_now and ok_before:
       ...                                        # L — sólo puede ADMITIR
   ok_before = ok_now
   ```

   Dos interruptores y no uno porque **un A/B que mueve dos cosas a la vez no
   atribuye ninguna** — la lección de la columna `A` de `support_arm_v1178.md`.

3. **`_pass > 1` en el limbo L no es un número, es una regla**: un camino de
   entrada nuevo no puede costar **menos historia** que aquel al que se suma, y
   la contracción paga tres pasadas por sus dos razones.
4. **La quinta salida, cerrada.** Una rama con F asentada y X viva no podría
   aceptarse (la puerta la rechaza), no podría entrar al rescate (su entrada
   preguntaba sólo por F) y no tiene por qué estancar: moriría por presupuesto y
   se contaría como una que «was still making progress when it was cut», que es
   falso. La entrada al rescate pasa a mirar el par, y las dos mitades
   responden al mismo interruptor porque el estrechamiento es quien crea ese
   estado.

**El orden de los dos limbos es lo que conserva los recuentos de pasadas**: donde
los dos podrían disparar, la contracción dispara una pasada antes, porque L
necesita que la pasada anterior ya estuviera dentro de tolerancia.

### La celda que demuestra que la guarda es portante

De dieciséis celdas medidas (cuatro ángulos × dos ramas × dos tolerancias),
**exactamente una** tiene sus dos primeros pasos ya dentro de tolerancia: la
cuña de 50° en **λ = 0, rama de momentos, tolerancia 5e-3**, con 1,411e-3 y
1,029e-3. Sin `_pass > 1` esa celda se acepta en la **pasada 2**, que es la
aceptación accidental de dos pasadas que el centinela `-inf` de D116 existe para
rechazar — y `test_branch_contraction_v1172` la barre. Y no es laboratorio:
`_LAMBDA_SHAPE` **contiene `0.0`**.

Por qué λ = 0 es justo donde muerde: allí `lambda_boundary` devuelve un vector
de ceros, luego `X ≡ 0`, luego `d_x ≡ 0` **exacto**, luego `ok_now` colapsa a
`step < tolerance` y la mitad nueva del criterio se queda sin información. Yo
había argumentado lo contrario —que λ = 0 era el sitio **seguro**, porque
`d_x ≡ 0` protege los pines contra la puerta— y era cierto para el
estrechamiento y **exactamente al revés** para el ensanchamiento.

---

## 5. Coste

`d_x` en todas las pasadas añade una resta, un `abs` y una comparación por
frontera interior, contra las ~170 operaciones que una dovela ya cuesta en esa
misma pasada: **≈ +9 % del solver de ramas**, ≈ +6 % por superficie Spencer/GLE
y **0 %** en los siete métodos que no entran en este archivo. Se declara con el
razonamiento y no con el cronómetro, que es lo que AGENTS.md exige cuando el
reloj no resuelve.

A nivel de suite es invisible, y conviene decir el número entero: **24 min 13 s**
para 3863 casos, contra los **24,9 min** que v0.1.175 registró para 3782. (La
horquilla de «5 a 7½ minutos» que AGENTS.md publica está caducada desde hace
bastante y esta versión no la actualiza, que es una tarea de otra ficha.)

**Lo que se rechazó y por qué.** Calcular `d_x` sólo cuando `prev_step < K·tol`
ahorraría casi todo ese 9 %, y es mala idea por cuatro razones en orden de peso:
`K` sería una constante mágica sin partida de nacimiento —el ensayo de lo que
eso cuesta lo tiene escrito `FALLBACK_RESIDUAL_LIMIT`—; una rama cuyo paso
oscile alrededor de `K·tol` mediría sí/no/sí/no y **nunca** tendría dos pasadas
medidas consecutivas, que es construir un segundo defecto (a); ahorra en las
ramas baratas y no en las caras, que pasan casi toda su vida con pasos
diminutos; y el techo del ahorro es ese mismo 9 %, porque el bucle de X hay que
recorrerlo igual. Tampoco se funde el bucle de X con la marcha, aunque la
aritmética lo permitiría: la cota de empuje rompe **entre** los dos a propósito
y `spencer.py` publica `force.boundary_x` de estados abandonados.

---

## 6. Los seis re-anclajes, y ninguna banda se ensancha sin que su causa se mueva

**`test_interslice_thrust_bound_v1171`** — el encargo que ese fichero se dejó
escrito. Su clase `TestWhatThisDoesNotFix` estaba clavada «pinned here with the
number in front **so that the version which fixes P-D116 can see exactly what it
moved**», y ésta es esa versión. La rama del plano de 55° en λ = −5,55 con la
cota levantada, que se declaraba convergida con el empuje a más de 1e9 veces la
escala, **ya no devuelve ni siquiera un estado**: devuelve `None`, que es una
respuesta más fuerte que la que la clase esperaba. Las tres medidas del empuje
se conservan intactas y se asertan **primero**, midiendo el estado viejo, para
que el caso no pueda ponerse verde el día que la fixture deje de producir una
rama desbocada.

**`test_support_failure_v1161`** — el pin bit a bit del 091 a 30 dovelas se
mueve **por construcción**, que es el síntoma (a): 0,9636163385716956 →
0,9636226555792213, un +0,00066 % (6,6e-6 relativo contra una tolerancia de
1e-4), porque la rama pasa de aceptarse en la 107 a aceptarse en la 25. Bishop
no entra en `interslice.py` y se queda quieto, que es lo que lo hace control.
Dicho en voz alta: **ese dígito es una instantánea y no una referencia externa**
(regla 1); se conserva como guarda de regresión bit a bit sobre el modelo del
banco, y convertirlo en un A/B en proceso es decisión aparte.

**`test_branch_contraction_v1172`** — la cota `0,25·was` pasa a `0,30·was` con
la medida escrita al lado, y la causa es real: el limbo L acepta doce pasadas
antes en esa rama (28 en vez de 40) y **parar antes en una contracción lenta
—razón 0,96— es parar más lejos**. Medido: 0,279 del error del paso afortunado a
5e-3, donde era 0,168, y 0,083 a 1e-3, donde nada se movió. Es un coste real del
asentamiento y se dice en vez de disimularlo; lo que el caso afirmaba sigue en
pie, porque 0,279 sigue siendo más de tres veces mejor que 1.

**`test_interslice_budget_v1159`** — aquí la puerta **mejora** la celda y por eso
se sale de la banda por abajo: en el plano de 45° con ancla pasiva el residuo de
reserva cae de 0,00104 a 0,00069, que ya está **por debajo de la tolerancia** y
por tanto deja de ser un ejemplo de la frontera que esa clase describe. Mismo
plano, misma ancla, mismo mecanismo, una tolerancia más apretada (1e-4, residuo
0,00117). La banda no se ensanchó para salvar un caso: se movió porque su causa
se movió, y en la dirección de la reserva acercándose.

**`test_anchored_wedge_root_v1177`** — de las doce celdas (tres anclas × cuatro
λ) se pierde **exactamente una**: el ancla activa en λ = 1,25. Las otras once dan
el mismo factor bit a bit, y dos de ellas lo dan gastando más pasadas (la activa
en λ = −1,0 pasa de 48 a 92; la pasiva en 1,25, de 52 a 84). El barrido pasa a
recorrer los λ donde la rama **se admite**, con suelo de tres por celda, y la
celda perdida tiene caso propio con su medida. Ver §7.

**`test_support_active_passive_v1115`** — el más instructivo de los seis, y el
que estuvo a punto de leerse como una regresión contra un valor publicado.

---

## 7. El 085, o cómo un acuerdo publicado se apoyaba en una rama desbocada

Con el cambio puesto, GLE sobre el círculo publicado del problema 085 pasa de
**+0,21 %** del 1,575 del manual a **+2,12 %**, fuera de la banda del 2 % que ese
fichero declara. Antes de tocar nada, la medida:

| λ = 1,5, las dos ramas | antes | ahora |
|---|---|---|
| veredicto | «convergen» en las pasadas 12 y 8 | **rechazadas** |
| `d_x` en la pasada de aceptación | **35,5 veces la tolerancia** | — |
| continuadas | — | se desbocan en las pasadas **127 y 123** |

O sea que **la horquilla que producía el acuerdo con el valor publicado se
apoyaba en dos ramas que se desbocan**. Es literalmente el defecto (b), y es
literalmente lo que la clase hermana de `test_interslice_thrust_bound_v1171`
tenía clavado como evidencia.

Y encaja con lo que **v0.1.176 ya había medido y escrito** de este mismo
problema: con φ′ = 0 la rama de momentos es exactamente constante, y la de
fuerzas **pierde su punto fijo por desbordamiento desde λ = 1,51**, antes de
poder cruzarla. **Aquí no hay raíz que encontrar.** El λ = 1,5 que la producía
está justo por debajo de ese 1,51.

El propio docstring de la clase ya lo avisaba, y conviene citarlo porque es lo
que hace legítimo el re-ancla: *«las dos aserciones de abajo están ancladas en un
**VALOR DE RESERVA**… están aquí por lo que sí cazan… **no como medida de la
formulación**»*. Lo que sustituye a esas dos bandas es lo que no se mueve:

- **Bishop** —que no entra en la búsqueda de λ— reproduce el valor publicado a
  **−0,42 %**;
- la **rama de momentos** de GLE vale lo mismo que Bishop a **2,2e-16 en activo
  y exactamente 0 en pasivo**, en todos los λ. Ésa es la forma cerrada de
  φ′ = 0, afirmada como la identidad que es en vez de como una banda del 1,5 %
  dibujada alrededor de una reserva. Es un **apriete**, y está permitido porque
  su causa cambió: lo que la forma vieja comparaba era el punto medio de una
  reserva entre dos ramas que nunca se encuentran;
- y GLE **dice** que no tiene raíz (`converged=False`, «no λ-bracket»), que es
  la regla 7 en afirmativo: perder la horquilla no puede ser silencioso.

---

## 7bis. El banco

Corrida de los **21 problemas que el censo señala** —42 modelos, 3 h 30 min,
42 de 42 sin un solo error—, contra la instantánea `Evaluaciones/0.1.178`, cuyos
63 archivos se comprobaron **byte a byte** contra el estado vivo antes de
arrancar, para que la línea base no fuese una suposición.

**Y la columna sin la cual la tabla sería falsa, la versión del LADO A**: la
instantánea NO es homogénea. De los 63 archivos comparados sólo **18 dan un A/B
limpio de D145**; ocho arrastran 0.1.175 y dieciséis arrastran 0.1.173, cuyo
brazo de soporte (D144) y rescate de rama (D125) mueven números que no son de
esta versión. Imputárselos a D145 sería exactamente la trampa que v0.1.173 dejó
documentada y que v0.1.178 volvió a pisar.

Sobre esos 63 archivos se compararon **4782 números y se movieron 236**. Lo que
importa son los 18 limpios, y ahí el resultado es el que el diseño predecía:

* en **los 18** se mueve el censo `validas`/`invalidas`/`inadmisibles`, y **tiene
  que moverse**: el criterio cambia qué muestras de λ son válidas, así que un
  recuento quieto significaría que el ajuste no hace nada (regla 7);
* se mueven **15 factores de seguridad**, y el mayor es **+0,1111 %** (el 093 sin
  conexión bajo GLE). Los otros catorce están por debajo de **0,03 %**, y nueve de
  ellos por debajo de 0,006 %.

La comparativa entera: **559 -> 559 filas, 555 IGUAL, 2 que mejoran y 2 que
empeoran, sin pareja 0/0 y NINGÚN cambio de estado**. Cuatro filas de 559.

`auditoria_invariantes.py` a **0 ERROR** (748 hallazgos: 491 AVISO, 257 INFO).

**Lo que esta corrida NO cubre, dicho porque un alcance que no declara su límite
se lee como si no lo tuviera**: son los 21 problemas que el censo pudo señalar, y
el censo sólo ve superficies ARCHIVADAS. Una búsqueda visita miles, así que 21 es
**cota inferior** y no el conjunto de lo que se mueve. Las mitades no circulares
no se re-corrieron. La corrida entera queda como evaluación posterior.

## 8. Reportado y NO corregido (regla 6)

**D152 (nueva).** La puerta rechaza una rama de fuerzas **cuyo factor no depende
de X**. En la cuña anclada activa a λ = 1,25 el factor valía 2,757457925 —las
mismas nueve cifras que los otros tres λ de la misma celda y que la forma
cerrada—, y valía eso porque en un plano `F_f` sale del balance **global** de
fuerzas, donde los esfuerzos entre dovelas se cancelan por pares: v0.1.177 lo
demostró. Lo que la puerta rechaza es el **estado**, no el factor: allí el
empuje viaja a 0,0679 de la escala por pasada y el par (F, X) no está ni cerca
de un punto fijo. Eximirlo exigiría que el solver supiera que `F_f` telescopa,
que es una propiedad de la **superficie** y no de la rama, y no hay prueba
barata dentro del bucle.

**El docstring de `_force_scale` afirma algo falso.** Dice que una superficie de
escala cero «produces `E = 0` at every boundary, so the guard never fires». Con
presión intersticial y rozamiento pero sin peso ni cohesión, `n_i ≠ 0`,
`s_i ≠ 0` y `e ≠ 0`, así que `peak > 0 = thrust_limit` y la rama muere por
desbordamiento **en su primera pasada**. No cambia nada de D145 —la cadena que
esta versión necesita (`force_scale == 0 ⇒ d_x == 0`) se sostiene por la otra
vía, porque la cota corta **antes** del bucle de X, y así queda derivada de
nuevo en el comentario en vez de tomada prestada— pero la frase es portante.

**`pytest.skip` no existe en el runner y hay dieciséis llamadas.** `_FakePytest`
sólo expone `approx` y `raises`; `test_support_failure_v1161` hace una y
`test_seismic_interface_v1127` quince. En una máquina sin el banco esas líneas
lanzan `AttributeError` y el runner las cuenta como **FALLO**, no como omisión,
que es justo lo contrario de lo que su comentario dice buscar. Ya estaba
reportado en v0.1.176 para una sola; son dieciséis.

**`_tools/ejecutar_caso.py` afirma algo caducado**: que `evaluate_surface`
analiza la primera masa por la izquierda. Desde v0.1.101 `search.py` despacha
todo `SlipCircle` a `evaluate_circle`. No hace daño hoy, pero es el comentario
que un medidor nuevo copiaría.

**`auditoria_reserva_lambda._evaluar` recibe un `n` y no lo usa.** La firma es
`_evaluar(proy, surf, mid, n)` y el cuerpo llama a `build_search(proy, mid)`, que
lee las dovelas del PROYECTO. El censo de v0.1.175 le pasa el `n_dovelas` que el
archivo tiene guardado y ese argumento no hace nada, de modo que una fila
archivada con un número de dovelas distinto del que el `.ogr` declara se
re-evalúa con el del `.ogr` y en silencio. En el banco los dos suelen coincidir,
así que rara vez muerde; me mordió a mí al escribir `d145()`, donde el caso del
criterio de cierre es a **30** dovelas y el modelo del 091 declara **50** (§9).
Es exactamente la forma de la regla 7 —un ajuste que no hace nada— en una
herramienta de medida.

**La mitad «círculo publicado» de los censos del banco pierde filas en
silencio.** `auditoria_reserva_lambda.py` (desde v0.1.175) y el medidor de esta
versión leen el modelo con `s.get("modelo") or "modelo.ogr"`, y seis problemas
—052, 062, 070, 079, 081 y 085— tienen sus modelos con otros nombres y
superficies de `referencia.json` sin clave `modelo`. Se saltan con su motivo
escrito, así que el denominador es honesto, pero `RESERVA_LAMBDA_0.1.175.md` y
`_0.1.176.md` arrastran el mismo hueco sin decirlo.

---

## 9. Errores propios detectados antes de publicar

Quince, y el más caro es el octavo porque llegó a decirse en voz alta:

1. **`step(k) = 2·|Δfos|` es falso en la pasada que ACEPTA**, donde el motor
   guarda `f_new` y no la media amortiguada, así que ahí el factor es 1. Sin
   corregirlo el censo publicaba el doble del paso justo en la pasada que
   decide. Lo cazó que el número saliera exactamente al doble del de la pasada
   de al lado.
2. **El agujero de λ = 0.** El diseño que traía no tenía la guarda `_pass > 1`,
   y con `d_x ≡ 0` el limbo nuevo reproducía la aceptación en dos pasadas de
   D116. Lo destapó atacar el diseño antes de escribirlo y lo confirmó la
   medición: una celda de dieciséis, y precisamente una que un test barre.
3. Medí «el empuje crece» con el **pico de |E|**, que en esa superficie es plano
   a nueve cifras. La magnitud que crece es la que lee la puerta.
4. Medí la secuencia de pasos con el motor **nuevo**, que acepta en la 25, así
   que la cola salía como una fila de ceros exactos y el caso habría pasado sin
   medir nada.
5. Usé la rama de **fuerzas** donde `test_branch_contraction_v1172` usa la de
   **momentos**, y concluí que el hueco al punto fijo había desaparecido.
6. Afirmé que la escalera de cuñas quedaba intacta y **la escalera me refutó**:
   β = 35°, λ = −1,0 se movió con `d_x` a 1,088× la tolerancia. Se movió con
   razón, pero mi afirmación era más fuerte que el hecho.
7. Mi regla «todo lo que se mueve estaba sucio» cubría **un limbo de dos**: el
   091 se mueve **limpio**, porque a ése lo adelanta el asentamiento.
8. **Etiquetas invertidas en un diagnóstico**, y publicadas: un ayudante
   `off(tighten=True)` que significaba «apaga TIGHTEN» rotulado como «sólo
   TIGHTEN». Me llevó a decir que el 085 lo rompía el asentamiento cuando lo
   rompe la puerta —lo contrario— y sólo lo cazó volver a medir desde otra
   puerta. Un ayudante cuyo nombre dice lo contrario que su argumento es la
   forma más barata de publicar una conclusión falsa.
9. Un bloque `#:` pegado a una **función** en vez de a una constante, que es
   exactamente el defecto que v0.1.175 arregló en `STALL_PATIENCE`.
10. Código muerto en `_d_x`, una condición que no hacía nada y se explicaba a sí
    misma.
11. Un parche de más de 8 KB por Bash, que corta con «unexpected EOF» — la
    trampa que AGENTS.md tiene escrita y que yo volví a pisar.
12. Un caso de regla 6 que pedía admisibles e inadmisibles sobre **una** cuña,
    donde la respuesta es unánime; hacen falta dos, y esa unanimidad es en sí
    misma lo que el caso quería decir.
13. `d145()` daba **NO SE SOSTIENE** la primera vez porque medía el 091 a 50
    dovelas creyendo pedirlo a 30 — el `n` que `_evaluar` ignora (§8). El
    veredicto era correcto y la causa que nombraba, «la búsqueda ya no muestrea
    ese lambda», también: simplemente hablaba de otra búsqueda.
14. La cabecera del test afirmaba **107 pasadas** como si fuera un número único,
    y son **107 por una puerta de evaluación y 105 por la otra**. Ninguno de los
    dos es el invariante, que es «más de 60 antes y menos de 60 ahora», y así
    queda escrito.
15. El desglose de discriminación de la cabecera decía **cinco por diferencia
    medida y dos por `AttributeError`**, y son **seis y una**. Lo cacé al
    ejecutarlo contra el árbol de 0.1.178 con `git stash`, que es la única forma
    de saberlo; escribirlo de memoria es como un fichero acaba prometiendo una
    cobertura que no tiene.

---

## 10. El test

`tests/test_branch_state_v1179.py`, **18 casos en seis clases**, y **ninguna
aserción fija un factor de seguridad**: todo es un A/B en un proceso, una
identidad o un recuento de pasadas. Las fixturas se escriben en código para que
la suite corra sin el banco, y **087 y 091 son el mismo muro** (Leshchinsky y
Han 2004) — un diff estructural de los dos `.ogr` da tres diferencias
sustantivas y nada más: el borde izquierdo del modelo y los dos parámetros de
resistencia del cimiento—, así que el constructor toma una bandera en vez de
escribirse dos veces.

---

## 11. Verificación

- Suite entera y sin argumentos: **3863/3863**, sin banner `FILTERED RUN`
  (0.1.178 traía 3843; +18 del fichero nuevo, +1 en v1177 y +1 en v1115).
  Corrida **dos veces en verde y las dos sola, sin nada más en la máquina**:
  una al cerrar los re-anclajes (24 min 13 s) y otra sobre el árbol final
  (24 min 45 s). La primera no se descarta —mide el mismo motor— pero la que
  cuenta es la segunda, que ya lleva el changelog que
  `test_version_consistency_v176` exige y las cabeceras corregidas.
- El guion de la ficha con el criterio nuevo: la rama de λ = 3,0 del 087 sobre
  su crítica archivada **no puede aceptarse** (pasa de la pasada 45 a estancar
  en la 171), y el resultado publicado de esa superficie **no se mueve** —
  1,075754608123 antes y después—; lo único que cambia es
  `lambdas_lost_to_stall`, de 0 a 1.
- El 091 a 30 dovelas: **de 107 pasadas a 25**, y el criterio de cierre pedía
  menos de 60. Los otros seis λ de esa búsqueda quedan bit a bit.
- `verificar_cierres.py D145` da **CUBIERTO POR TEST** con las cuatro medidas
  del molde de `d144()` —el test por `_cubierto`, las cabeceras por AST (las del
  fichero nuevo y las de las dos clases re-ancladas de otros ficheros), la
  identidad **ejecutada** por el medidor, y el censo de la versión instalada— y
  se comprobó que **discrimina por los dos lados**: con los interruptores
  apagados contesta NO SE SOSTIENE nombrando la causa, «la rama de lambda 3,0
  del 087 SIGUE aceptandose en la pasada 45: la puerta del empuje no esta
  puesta».
- Ficha retirada al índice, podada de P2 en el markdown **y** en
  `generar_prompts.py`, prompts regenerados con salida 0 y sin fichas sin
  paquete, y el renglón de P2 corregido **entero**: además de D145 le faltaba
  tachar **D144**, cerrado una versión antes, porque arreglar sólo el propio
  renglón lo dejaría igual de falso (la lección de v0.1.175).
- Ficha nueva **D152** con su prompt largo, y la serie D movida a D152/D153.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later

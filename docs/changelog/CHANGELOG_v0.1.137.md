# OGR Slip2D v0.1.137

**Defecto D39/D44.** El término normal del soporte, `T_N·tanφ'`, estaba sumado
**fuera de `m_α`** en Bishop. Ya no. El encargo pedía parar si no aparecía un
caso publicado con superficie crítica **de Bishop**, refuerzo y base inclinada
—y el banco afirmaba por escrito que no existía—; **existen cuatro**, y con
ellos delante el cambio deja de ser retroanálisis y pasa a ser una derivación
con dos identidades detrás.

Lo que **no** se ha corregido es la mitad de Janbu, y esa es la parte que más
enseña: el arreglo consistente le sale exacto en la identidad y le cuesta los
seis planos publicados de Clouterre.

---

## 1. Lo que el encargo daba por imposible

`PROMPTS_RESOLUCION.md` decía, sobre el gemelo D42: «*necesita un caso publicado
con superficie crítica de Bishop, refuerzo y base inclinada, **y no existe en el
banco***», y P-D39 repetía la cláusula. Es falso, y el dato llevaba registrado
desde 0.1.116 en los propios `referencia.json`:

| # | fuente | publica | círculo de Bishop | base |
|---|---|---|---|---|
| **87** | Leshchinsky y Han (2004) | Bishop **1,040**, fig. 87.2 | (−5,713 · 20,432) R 18,547 | 39°→73° |
| **92** | ídem, con filtración | Bishop **1,037**, fig. 92.2 | (−4,903 · 20,532) R 18,112 | 37°→72° |
| **94** | ídem, cinco bancadas | Bishop **1,040**, fig. 94.2 | (−5,537 · 20,452) R 18,450 | 40°→72° |
| **54** | **Yamagami (2000)** | Bishop **1,193** con pilote y **1,102** sin él | (2,674 · 7,376) R 8,102 | — |

Los tres primeros publican centro, radio **y los dos afloramientos**, así que la
geometría está sobredeterminada, y traen una segunda cifra que no sale del
programa de referencia: la de los propios autores (1,00 por Bishop circular,
0,99–1,01 por diferencias finitas). El 54 es mejor todavía como medida del
término, porque publica **el par con y sin pilote** sobre dos círculos
distintos: el término del suelo queda sujeto por el gemelo sin refuerzo.

## 2. La señal estaba en la línea de al lado, y nadie la había leído

Sobre esos mismos círculos publicados, **antes de tocar nada**:

| | Bishop | Fellenius | Spencer | publicado |
|---|---|---|---|---|
| 87 | 1,4117 (**+35,7 %**) | 1,0542 (**+1,4 %**) | 1,0376 (−0,2 %) | 1,040 |
| 94 | 1,4084 (**+35,4 %**) | 1,0548 (**+1,4 %**) | 1,0384 (−0,2 %) | 1,040 |

**La misma fuerza de refuerzo, el mismo círculo, el mismo suelo**, y Fellenius
—que también suma `T_N·tanφ'` en crudo— ya estaba dentro del 1,4 % mientras
Bishop se iba al 35 %. Eso descarta de golpe la magnitud de la fuerza, su
orientación, el reparto Activo/Pasivo y la geometría: lo único que separa a los
dos métodos es **cómo llega esa fuerza a la base**.

## 3. Por qué Fellenius acierta con el término crudo y Bishop no

`m_α` no es una normalización con un afuera. Es lo que queda de resolver el
equilibrio **vertical** de la dovela para N (Bishop 1955):

```
N·cos α + S·sin α = W + P      →      N = (W + P − …) / m_α
```

luego **cualquier** fuerza externa sobre esa dovela llega a la base dividida por
`m_α`, igual que el peso. Fellenius no resuelve la vertical: resuelve
**perpendicular a la base**, donde `N = W·cos α + T_N` es exacto y no hay `m_α`
que dividir. Son dos aritméticas distintas para el mismo enunciado físico, y por
eso Ordinary **no se toca** y su forma cerrada
(`test_ordinary_gains_exactly_t_n_times_tan_phi`) sigue en verde: es el control.

El factor que separaba las dos lecturas es `cos α / m_α`:

| α | 0° | 51° | 56° | 61° |
|---|---|---|---|---|
| `cos α / m_α` | ≈ 1 | 0,71 | 0,51 | 0,36 |

que es exactamente el «*second-order for the usual near-horizontal bases*» que
`bishop.py` llevaba **setenta y dos versiones** escrito como aviso. El aviso era
correcto; lo que faltaba era comprobar dónde dejaba de serlo.

### Lo que la formulación publicada dice de verdad

Las dos ecuaciones que OGR cita —`F = (resisting + T_N·tanφ)/(driving − T_S)` y
su pareja pasiva— **no deciden esto**. Están escritas con las palabras
*resisting force* y *driving force*: son globales, y no dicen dónde va `m_α`.
Lo que sí lo dice es la página de la referencia sobre **dónde** se aplica la
fuerza: en el punto de corte, a la base de una sola dovela, y allí *«the applied
force is simply a line load»*. Una *line load* entra por el equilibrio de la
dovela. No hacía falta contradecir la formulación documentada: hacía falta
leerla entera.

## 4. Las dos identidades que sujetan el cambio

**La primera ya estaba medida y era D46.** La misma fuerza, en el mismo punto,
tiene que dar el mismo factor de seguridad tanto si entra como soporte como si
entra como carga —eso es la definición de un sólido libre, no un convenio—. El
hueco de Bishop era **−0,276 % a cualquier número de dovelas**, que es la firma
de un error de formulación y no de discretización:

| | 25 dovelas | 100 | 400 |
|---|---|---|---|
| Bishop **antes** | −0,276 % | −0,276 % | −0,276 % |
| Bishop **ahora** | −0,0100 % | +0,0016 % | +0,0006 % |
| Ordinary (control) | −0,0090 % | +0,0014 % | +0,0006 % |
| Spencer (control) | −0,0096 % | +0,0015 % | +0,0006 % |

Bishop cae sobre la misma curva de discretización que los que siempre la
tuvieron. El test que congelaba el desacuerdo decía en su propio docstring que
«*si algún día se cierra, falla y obliga a reescribir lo que se afirma aquí*».
Se ha cerrado y se ha reescrito.

**La segunda es la ecuación de Bishop reconstruida término a término** al factor
de seguridad al que converge el solver. Sobre una dovela de base a 51° y un
soporte puramente normal (`T_S = 0,000000000` por construcción), sólo una de las
dos formas cierra la ecuación:

```
forma con m_α    residuo 3,2e-05      <- la que el solver cumple
forma cruda      residuo 1,5e-02      <- 460 veces mayor
```

No es un número capturado: se escriben los dos numeradores candidatos y se mira
cuál cierra. Seguiría discriminando aunque cambiara toda la geometría del
fixture.

## 5. Lo medido, sobre las superficies publicadas

| # | publicado | Bishop antes | Bishop ahora | Spencer (sin tocar) |
|---|---|---|---|---|
| **87** | 1,040 | 1,4117 **+35,74 %** | **1,0330 −0,67 %** | 1,0376 −0,23 % |
| **94** | 1,040 | 1,4084 **+35,42 %** | **1,0340 −0,58 %** | 1,0384 −0,15 % |
| **54** | 1,193 | 1,2118 +1,57 % | **1,1953 +0,19 %** | 1,1939 +0,08 % |
| 54 sin pilote | 1,102 | 1,1011 −0,08 % | 1,1011 −0,08 % | 1,0984 −0,33 % |
| 88 | 1,045 | 1,1965 +14,50 % | 1,0991 +5,18 % | 1,0977 +5,04 % |
| 89 | 0,976 | 1,1487 +17,70 % | 1,0106 +3,54 % | 1,0080 +3,28 % |
| 90 | 1,004 | 1,2288 +22,39 % | 0,9141 −8,96 % | 0,9242 −7,95 % |
| 92 | 1,037 | 1,2207 +17,71 % | 0,8579 −17,27 % | 0,8785 −15,29 % |
| 93 | 0,958 | 1,3798 +44,03 % | 1,0143 +5,88 % | 1,0156 +6,01 % |
| 91 | 0,985 | 0,9983 +1,35 % | 0,9806 −0,45 % | 0,9515 −3,40 % |

**Lo que hay que leer aquí no es la columna del error, es la distancia entre
Bishop y Spencer.** Sin refuerzo esos ocho coincidían al 0,4 %; con refuerzo se
separaban del 14 % al 40 %. Ahora se separan **entre 0,1 % y 2,0 %**, que es lo
que pedía el criterio de cierre de D44. Los desvíos que quedan —el −8 % del 90,
el −15 % del 92, el +5 % del 88 y el 89— los comparten Spencer, GLE,
Lowe-Karafiath y Fellenius **por igual**, así que son de esos modelos del banco
y no del término.

El **91 confirma por el otro lado**: es el único cuyo círculo cruza las láminas
con la base tendida, ya estaba a +1,35 % y se mueve a −0,45 %. El desvío
escalaba con `|sen α|`, que es justo lo que multiplica a `T_N`.

### Y un quinto caso publicado que no estaba en el encargo: el pilote del 106

Cai y Ugai (2000) publican Bishop para cuatro separaciones de pilote. No traen
coordenadas de superficie, así que sólo se puede comparar la búsqueda, pero son
cuatro valores independientes del programa de referencia:

| D1/D | publicado | antes (0.1.127) | ahora | Δ antes | Δ ahora |
|---|---|---|---|---|---|
| 2 | 1,540 | 1,5626 | 1,5626 | +1,47 % | +1,47 % |
| **3** | 1,370 | 1,4735 | **1,4466** | +7,56 % | **+5,59 %** |
| **4** | 1,310 | 1,3604 | **1,3416** | +3,85 % | **+2,41 %** |
| **6** | 1,250 | 1,2724 | **1,2614** | +1,79 % | **+0,91 %** |

Tres de los cuatro mejoran y ninguno empeora. El caso base del 106 **no se
mueve, y no puede**: su `modelo.ogr` no lleva pilote — es la referencia sin
refuerzo — cosa que conviene decir en vez de contarlo como un acierto.

### Y una honestidad sobre las anclas

**Los problemas 85 y 60 no validan nada de esto.** Los dos son arcilla con
**φ = 0**, luego `T_N·tanφ' ≡ 0` y este cambio no puede moverlos ni en el sexto
decimal. Salen idénticos, y decir «el 85 no se ha roto» sería cierto y
engañoso: no se ha roto porque no puede. El ancla que sí mide con fricción es el
54, y el par con y sin pilote de Yamagami es lo que la convierte en medida.

## 6. La mitad que NO se ha corregido: los dos Janbu

Janbu equilibra `Σ S·sec α = Σ W·tan α`, así que le tocaba lo mismo que a Bishop
**y además** un `sec α` en el lado motor, donde resta `T_S` en crudo. Se probaron
las cuatro combinaciones:

| Janbu | Clouterre (6 planos) | identidad carga≡soporte | vs Spencer en geotextiles |
|---|---|---|---|
| **crudo + `T_S` raso** *(lo que queda)* | **1,76 %** | −0,096 %, y no se encoge | 5 % a 13 % |
| crudo + `T_S·sec α` | 6,90 % *(medido en 0.1.113)* | — | — |
| dentro de `n_α` + `T_S` raso | — | — | **−20 % a −39 %** |
| dentro de `n_α` + `T_S·sec α` | **7,95 %** | **0,000000** a 25, 100 y 400 | 0,3 % a 3 % |

Léase la tabla despacio: **la única combinación que reproduce los seis planos
publicados es la que no puede pasar su propia identidad, y la que la pasa exacta
—cero, no «pequeño»— pierde los planos.** Corregir sólo el numerador, que era lo
que parecía el arreglo, es la peor de las cuatro.

Nada externo decide entre las dos, así que Janbu **se queda como estaba**, con
las cuatro medidas escritas en el propio término
(`ogr_slip2d/methods/janbu.py`) y un test que afirma su desacuerdo como hecho,
igual que se afirmaba el de Bishop hasta esta versión. Elegir por lo que ajusta
es exactamente lo que la regla 1 prohíbe, y en este proyecto ya costó ocho
versiones de atribución equivocada en A48-1.

## 7. El defecto del banco: la rejilla del 59

Del banco y no del programa. El recuadro de la figura 59.2 sitúa la rejilla en
`x ∈ [−46, −3]`, `y ∈ [9, 53]`; `construir_modelo.py` declaraba
`x ∈ [−15, 40]`, `y ∈ [15, 80]`, y **el centro publicado (−30,872 · 31,315) cae
fuera**. Comparar ese mínimo con lo publicado es lo que produjo el +95 % con el
que se abrió D39. Cambiada sólo la rejilla:

| método | rejilla vieja | **rejilla de la figura** | publicado |
|---|---|---|---|
| **spencer** | 0,670857 (+12,6 %) | **0,576995 (−3,2 %)** | 0,596 |
| janbu simp. | 0,643114 | 0,637654 (+9,4 %) | 0,583 |
| ordinary | 0,809573 | 0,814166 (−5,2 %) | 0,859 |
| **válidas** | **113** | **463** | |

Spencer, que es el método de esa figura, entra en el ±3,2 % y las superficies
válidas se cuadruplican.

### Y con las dos cosas juntas, el 59 cumple el criterio que se había retirado

El criterio viejo de D39 era «el 59 da 0,582 ± 3 % con Bishop», y el encargo lo
retiró por indecidible. Con la rejilla arreglada **y** el término en su sitio,
la búsqueda da:

| | Bishop | publicado | Δ |
|---|---|---|---|
| rejilla vieja, término viejo | 0,830735 | 0,582 | +42,7 % |
| rejilla de la figura, término viejo | 0,810268 | 0,582 | +39,2 % |
| **rejilla de la figura, término nuevo** | **0,566527** | 0,582 | **−2,66 %** |

Con una salvedad que el propio programa levanta y que conviene medir en vez de
repetir: ese mínimo aflora a **86,6°** y su aviso dice que el número depende del
número de dovelas. Depende, y poco —0,5666 con 50, 0,5712 con 100, 0,5720 con
200, 0,5732 con 400, 0,5718 con 800—, o sea que converge a **−1,7 %**. Dentro
del 3 % por los dos caminos.

Spencer, en la misma corrida, sale **0,576995 bit a bit igual** que antes de
tocar Bishop. Era el ancla y no se ha movido.

## 8. Qué se tocó

| archivo | cambio |
|---|---|
| `ogr_slip2d/support_integration.py` | `support_vertical_load()`: la carga descendente que el soporte pone sobre la dovela — normal entera más tangencial movilizada a `t_active + t_passive/F`, el mismo reparto que `interslice.prepare_rows` |
| `ogr_slip2d/methods/bishop.py` | circular y no circular: la carga entra en `W_eff` **antes** de dividir por `m_α`; fuera el término crudo. En la no circular `sup` **sí** se pasa ya a `moment_terms`, porque el momento de la parte normal lo necesita el eje y `resisting` ya no lleva una segunda copia |
| `ogr_slip2d/methods/janbu.py` | **sin cambio numérico**; las cuatro medidas anotadas en el término |
| `ogr_slip2d/methods/ordinary.py` | **sin cambio numérico**; por qué conserva la forma cruda |
| `tests/test_support_normal_v1137.py` | nuevo: la ecuación reconstruida, el control de Fellenius, y la separación Bishop/Spencer que no crece con la capacidad |
| `tests/test_efp_wall_v1122.py` | el test que congelaba el desacuerdo de Bishop ahora afirma el acuerdo; el de Janbu congela el suyo |
| banco · `02_Slide2_Problema059/construir_modelo.py` | la rejilla de la figura |

## 8.bis El problema 86 pasa de OK a DISCREPANCIA, y eso es lo correcto

Una fila que empeora merece explicación, y esta la tiene. El 86 —talud reforzado
de cinco capas, Duncan y Wright (2005)— publica sus tres métodos **dentro del
0,6 % entre sí**: Bishop 1,629, Spencer 1,620, GLE 1,622. OGR daba:

| | antes | ahora | publicado |
|---|---|---|---|
| Bishop | 1,6447 (**+0,97 %, OK**) | 1,5100 (−7,30 %) | 1,629 |
| Spencer | 1,5036 (−7,19 %) | 1,5036 (sin mover) | 1,620 |
| GLE | 1,5043 (−7,25 %) | 1,5043 (sin mover) | 1,622 |
| Fellenius | 1,4602 | 1,4602 (sin mover) | — |

El «OK» de Bishop era **accidental**: coincidía con el valor publicado mientras
estaba un **8,5 % por encima del Spencer de OGR**, en un problema donde el manual
los publica al 0,6 %. Ahora los cuatro métodos de OGR coinciden entre sí dentro
del 0,4 % y los tres comparables caen juntos a −7,2 % de lo publicado: eso ya no
es un defecto del método, es un desfase del modelo, y está donde se puede
investigar. Es el mismo patrón que v0.1.115 anotó para este problema —«su acuerdo
anterior eran DOS ERRORES CANCELÁNDOSE»—, sólo que ahora se ve entero.

## 9. Qué se probó

- Suite completa, `QT_QPA_PLATFORM=offscreen python tests/_runner.py`.
- El test nuevo **contra el código viejo**: 5 de 10 fallan, y los dos de forma
  cerrada están entre ellos mientras el control de Fellenius pasa en las dos
  direcciones. Un test que no falla contra el defecto que dice proteger no
  protege nada.
- Banco: los **veinte** problemas con refuerzo, sus escenarios con nombre
  propio (`sin_conexion`, `modelo_D1D*`, activo/pasivo) y las mitades no
  circulares que llevan Bishop, más `generar_comparativa.py`.
- Y un A/B directo sobre las superficies publicadas —la misma versión, con y sin
  el cambio— porque es la única medida que atribuye. **La comparativa frente a la
  instantánea de 0.1.127 (OK 176 → 213) NO es de este cambio**: entre medias van
  nueve versiones (D33/D51, D13, D36, D34, D07c…). Del 86 no circular, por
  ejemplo, la mejora de −30,7 % a −5,8 % es de 0.1.129, no de aquí; se comprueba
  en que su Spencer sale 1,584134, el mismo dígito que aquella versión dejó
  escrito.

## 10. Qué queda

- **Janbu**, con sus cuatro combinaciones medidas y ninguna evidencia externa
  que elija. Es lo que queda abierto de D46 y de D39.
- El **−15 % del 92** y el **−8 % del 90**, que son de esos modelos y los
  comparten los nueve métodos.
- El **59** sobre el **círculo publicado** sigue a +30 % en Bishop — pero ese
  círculo es el de Spencer, no el de Bishop, así que la cifra que cuenta es la de
  su búsqueda, y esa está a −2,66 %. Lo que queda por mirar ahí es el
  afloramiento a 86,6°.

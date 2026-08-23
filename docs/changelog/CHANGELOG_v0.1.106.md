# OGR Slip2D v0.1.106

**Spencer y GLE dejan de devolver el valor de Bishop. Eran tres defectos, no
uno, y el que más versiones llevaba escrito tenía la causa mal atribuida.**

Sobre superficie circular, `Spencer` y `GLE/Morgenstern-Price` devolvían el
factor de seguridad de Bishop simplificado **dígito a dígito**. No por poco:
tal como estaban escritos eran *incapaces* de dar otra cosa. Afecta a 64 de
los problemas con número del banco de verificación y a los dos métodos más
usados del programa.

Abierto desde v0.1.79 en `docs/audits/spencer_gle_interslice_v179.md`, y desde
v0.1.94 en `docs/PENDIENTES.md` §6 y §9.

| | publicado | v0.1.105 | **v0.1.106** |
|---|---|---|---|
| ACADS 1(a), Spencer | 0,986 | 0,986936 (= Bishop) | **0,986078** (+0,01 %) |
| ACADS 1(c), Spencer | 1,375 | 1,405251 (= Bishop) | **1,374693** (−0,02 %) |
| Talbingo 2(b), Spencer | 2,292 | 2,208783 (= Bishop) | **2,292801** (+0,03 %) |
| Talbingo 2(b), GLE | 2,301 | 2,208783 (= Bishop) | **2,301930** (+0,04 %) |
| ACADS 3(b) no circular, Spencer | 1,277 | 1,229727 (= Bishop) | **1,288392** (+0,89 %) |
| Prandtl (problema 26), Spencer | 0,94 | 0,761275 (−19,0 %) | **0,939941** (−0,01 %) |
| Problema 57 compuesto, Spencer | 1,4220 | 1,419276 (−0,19 %) | **1,422042** (+0,00 %) |
| Problema 78, Spencer | 1,2000 | 1,195675 (−0,36 %) | **1,198379** (−0,14 %) |
| Problema 85 con refuerzo, GLE | 1,5750 | 1,568407 (−0,42 %) | **1,570863** (−0,26 %) |
| Ej_2 piezométrica, Spencer | 0,687672 | 0,673203 (= Bishop) | **0,688335** (+0,10 %) |
| Ej_1 no circular, Spencer | 0,942419 | 0,922940 (= Bishop) | **0,942663** (+0,03 %) |
| Ej_2 no circular, Spencer | 1,479930 | 1,423177 (= Bishop) | **1,475703** (−0,29 %) |

Y la separación respecto de su propio Bishop, que es lo que este defecto
borraba:

| separación Spencer − Bishop | referencia | v0.1.105 | **v0.1.106** |
|---|---|---|---|
| Ej_2 con piezométrica | +1,888 % | **−0,000 %** | **+2,142 %** |
| Ej_1 no circular | +2,07 % | +0,02 % | **+2,08 %** |
| Ej_2 no circular | +3,75 % | +0,00 % | **+3,56 %** |

---

## 1 · Los tres defectos, y por qué hacían falta los tres

Medidos **antes** de tocar nada, sobre 0.1.105, con los dos anclajes exactos
de Fredlund y Krahn (1977): en λ = 0 no hay cortante entre dovelas, así que la
rama de fuerzas **es** Janbu simplificado y la de momentos **es** Bishop.

| Problema | F_f(0)/Janbu | F_m(0)/Bishop |
|---|---|---|
| 1 | 0,774 | 0,977 |
| 3 | 0,700 | 0,961 |
| 6 | 0,794 | 0,979 |
| 8 (no circular) | 0,497 | 1,017 |

Reproduce la medida del defecto D10 del banco (0,774 / 0,701 / 0,794 / 0,500).
El cierre de D09 en v0.1.105 no tocó nada de esto: el problema 8, ya sin la
guarda `circle_R`, seguía dando Spencer = Bishop exacto.

### (A) La rama de fuerzas llevaba `cos α` donde va `sec α`

Ya estaba escrito en `PENDIENTES.md` §9 desde v0.1.98. El equilibrio
horizontal del conjunto lo cierra sin margen:

```
N = (W − S·senα)/cos α          equilibrio vertical de la dovela
Σ N·senα = Σ S·cos α            equilibrio horizontal del conjunto
  ⇒  F·Σ W·tanα = Σ S_term·sec α
```

y `Σ S_term·secα / Σ W·tanα` **es** Janbu simplificado término a término,
porque `n_α = cos α · m_α`. El factor perdido era `cos²α` por dovela: en un
talud de 45-64° eso es un factor dos.

### (B) Las dos ramas compartían UNA sola F — y esto no estaba nombrado

`_inner_solve` iteraba `new_F = 0.5·(new_fm + new_ff)` y evaluaba `m_α` con
esa media, así que ninguna rama era su propio punto fijo: `F_m` se calculaba
con la `m_α` de un factor que no era `F_m`.

**Ésa, y no `m_α` sin λ, es la causa entera del `F_m(0)/Bishop = 0,961–0,979`.**
El defecto D10 lo venía atribuyendo desde el 2026-08-20 a que «λ no llega a la
normal en la base», y para la mitad de momentos eso es falso: en λ = 0 **no
hay cortante interdovela**, luego `m_α` sin λ y `W_eff` sin `X` son las
expresiones correctas ahí. Es el mismo error de razonamiento que la regla 6
registra para `m_alpha` en v0.1.82 — una medición correcta sosteniendo una
explicación equivocada, durante dos versiones.

Con (A) y (B) corregidos **y nada más**, las dos identidades salen exactas a
ocho cifras. Y el factor de seguridad **no se mueve**: `F_m` sigue sin
contener λ, la raíz `F_f = F_m` vuelve a aterrizar sobre Bishop. Ése es el
motivo de que los tres tuvieran que entrar juntos.

### (C) La normal en la base omitía (X_R − X_L)

El de fondo. La forma completa de Fredlund y Krahn (1977) —recursión
horizontal de `E`, `X_i = λ·f(x_i)·E_i`, y

```
N = [W + (X_R − X_L) − (c'·l − u·l·tanφ')·senα/F] / m_α
```

— vive ahora en `ogr_slip2d/interslice.py`, que **Spencer y GLE comparten
línea a línea**. Los dos métodos se diferencian en una sola cosa, la función
de forma `f(x)`, de modo que «GLE con f constante *es* Spencer» pasa a ser una
identidad del código en vez de una promesa del docstring.

---

## 2 · Lo que sujeta esto: cuatro identidades analíticas

`tests/test_gle_interslice_v1106.py`. Ninguna es una instantánea.

| | identidad | fuente |
|---|---|---|
| I1 | `F_f(λ=0)` ≡ Janbu simplificado | Fredlund y Krahn (1977) |
| I2 | `F_m(λ=0)` ≡ Bishop simplificado (circular) | íd. |
| I3 | `F_f(λ)` ≡ el motor de inclinación prescrita con θ = arctan λ, **para todo λ** | Spencer (1967) es Modified Swedish con θ resuelto en vez de prescrito |
| I4 | GLE con `f(x)` constante ≡ Spencer | Fredlund y Krahn (1977) |

**I3 es la más fuerte, y es la que ancla esto a un caso resuelto a mano.** Ese
motor —`PrescribedInclinationMethod._march`, que comparten Lowe-Karafiath y
los dos Corps of Engineers— está validado término a término contra el ejemplo
del apéndice G de **USACE EM 1110-2-1902**, cuyas columnas de fuerza
interdovela y normal en la base reproduce. Medida a < 1,5·10⁻⁹ en λ = 0 / 0,2 /
0,45 / 0,8, **con sismo y con presión intersticial**, que es lo que fija el
signo de las fuerzas externas dentro de la recursión.

I1 e I2 se comprueban también con agua y con terremoto, por lo mismo.

---

## 3 · Siete cosas que sólo aparecen cuando el método empieza a funcionar

Ninguna podía existir antes, y juntas costaron bastante más que escribir la
ecuación. Las tres primeras porque `F_m` no dependía de λ y la diferencia
`F_f − F_m` tenía una sola raíz por construcción; las demás porque un solver
que nunca formaba las fuerzas interdovela no tenía cómo delatarlas.

### 3a · `F_f − F_m` deja de ser monótona: hay más de una raíz

Hasta v0.1.106 `F_m` no dependía de λ, así que la diferencia tenía **una** sola
raíz por construcción. Ahora puede tener varias, y sólo una es una solución.
Es lo que trata Ching y Fredlund (1983), *Some difficulties associated with the
limit equilibrium method of slices*.

Sobre el círculo de Talbingo la búsqueda encontró una raíz en **λ = −0,979**
antes que la buena en +0,419, y devolvió 1,6826 contra el 2,292 publicado. En
esa λ, **16 de las 24 caras interdovela estaban en tracción**, una de ellas a
−63 000 kN/m; en la buena, las 24 en compresión. En el problema 8, no circular,
la raíz espuria tenía las 24 en tracción.

El suelo no transmite tracción entre dovelas. `thrust_is_admissible` rechaza un
estado cuya resultante interdovela sea de tracción — sobre la **resultante** y
no cara a cara, porque una solución legítima puede llevar tracción pequeña en
una o dos dovelas junto a un extremo libre, donde `E` va a cero de todos modos.

### 3b · Un punto fijo sin converger se estaba publicando como valor

`solve_branch` devolvía su último iterado tras 80 pasadas. Sobre la polilínea
sumergida de Duncan y Wright #70, las dos ramas en λ = −1,5 seguían vagando y
el par en el que pararon (1,0572 y 1,0526) **se cruzaba**. La búsqueda lo tomó
por raíz y devolvió 1,051 donde la respuesta es 1,60. Ahora una rama sin
converger devuelve NaN, que es lo que es.

### 3c · La cola negativa de λ nunca había estado justificada

`min_lambda` pasa de **−1,5 a −0,1**, que es lo que traen los modelos de la
referencia y lo que `base.py` ya tenía escrito desde v0.1.90.

La ampliación de v0.1.74 (±1,25 → ±1,5) fue por el círculo de Ej_1 «que
necesitaba λ = 1,4919», es decir por el lado **positivo**; la cola negativa
vino de acompañante, por simetría, y nunca la pidió nada. λ es la inclinación
de la fuerza interdovela, `X/E = tan θ`, así que λ = −1,5 es una resultante
inclinada 56° hacia **abajo y hacia atrás** sobre una masa que desliza hacia
delante. Era inofensiva mientras sólo hubiera una raíz. Con la ecuación
corregida dejó de serlo, y ahí es donde caía la raíz espuria del §3b.

La migración encadena, como las otras: −1,25 → −1,5 → −0,1. El usuario que
quiera el alcance viejo lo tiene; sigue siendo un ajuste.

### 3d · El punto fijo se acotaba a 10 y la búsqueda aceptaba hasta 50

Dos números que tenían que ser el mismo y no lo eran. `solve_branch` acotaba su
iterado a `[0,2 · 10]` mientras el muestreo de λ acepta una rama en
`(0,05 · 50)`. Una superficie cuyo factor de seguridad está por encima de 10 no
se podía resolver: el punto fijo se clavaba en el techo **y lo devolvía como
respuesta**.

Lo destapó la lámina delgada del caso de masas disjuntas —0,9 pies de suelo,
F = 34,3 por Bishop—, que antes de v0.1.106 daba un 10,0 silencioso y después
del control de convergencia daba NaN. Las dos cotas son ahora `F_MIN` y `F_MAX`
en `interslice.py`, y son la banda que el propio método declara.

### 3e · El camino «sin λ-bracket» devolvía un resultado convergido y vacío

Cuando ningún λ produce cambio de signo, Spencer y GLE devuelven la muestra con
`|F_f − F_m|` menor y la marcan convergida si esa diferencia baja de 0,02. Ese
camino **descartaba la λ que acababa de encontrar** y devolvía un `details`
vacío.

No es cosmético. `compute_interslice_state` —el panel de dovelas, la línea de
empuje— se apoya en `details["boundary_ratios"]`, y sin ellos marchaba la
superficie con razones interdovela **cero**: un dibujo de Janbu sobre un número
de Spencer. Sobre la cuña degenerada de `test_postprocess_v122.py`, que es
justo una superficie que toma ese camino, la marcha cerraba con un residuo del
**49 %** en vez de 1,3·10⁻⁶, y ningún test lo miraba. Ahora ese camino publica
su λ, sus fuerzas interdovela y las tres columnas por dovela como el otro.

De paso queda medido lo que la corrección le hace a ese par de superficies:

| min(E)/E_max | v0.1.105 | **v0.1.106** |
|---|---|---|
| cuña degenerada | −1,50 a −1,60 % | **−1,59 a −1,60 %** |
| superficie sana | −0,52 a −0,58 % | **+0,52 a −0,07 %** |

La degenerada se queda donde estaba; la sana pasa a no necesitar tracción
prácticamente en ninguna cara. El par afirma ahora algo más limpio que «una
necesita varias veces más tracción»: **una la necesita y la otra no**.

### 3f · El criterio de tracción tenía que ser una preferencia, no un veto

Rechazar una raíz espuria (§3a) y rechazar una superficie son cosas distintas,
y la primera versión del criterio no las separaba. En el problema 85 —un talud
con **9000 kN/m** de anclaje— **ningún** λ deja las caras interdovela en
compresión neta, así que el veto devolvía NaN donde v0.1.105 devolvía 1,568
contra un publicado 1,575.

Si esa tracción es real o es un artefacto de concentrar el refuerzo en un punto
es una pregunta que esta versión **no responde**. Lo que no procede es convertir
un número en un NaN sin responderla. Así que el muestreo se repite con el
criterio relajado **sólo cuando fue el criterio, y no la divergencia, lo que
dejó la lista vacía** —el sistema cuenta cuántos λ ha tirado por ese motivo— y
el resultado sale etiquetado: `details["thrust_admissible"] = False` y un
`error_message` que lo dice. El 85 pasa de −0,42 % a **−0,26 %**.

### 3g · La identidad I3 no cubría el soporte, y eso costó un diagnóstico

Al ver el NaN del 85, la primera hipótesis fue que `h_drive` llevaba el soporte
al revés. Comprobarlo era una línea —conducir la recursión Corps a
θ = arctan λ **con el mismo soporte**— y no estaba escrita: I3 cubría sismo y
presión intersticial, no refuerzo. Con el soporte pasado, las dos coinciden a
**5·10⁻¹¹**, o sea que el signo estaba bien y el NaN era el criterio.

El caso está ahora en el archivo de tests, y con él una comprobación de regla 7
sobre el propio refuerzo: tiene que **subir** el factor de seguridad en este
solver.

Nota de paso, medida y **sin corregir**: con refuerzo, `F_m(0)` **no** vale
Bishop —1,5726 contra 1,5380 en el 85—. No es un defecto nuevo: Bishop parte un
soporte en una componente tangencial y otra normal, y Spencer y GLE lo meten
como fuerza cartesiana en el equilibrio; `moment_balance.moment_terms` ya dice
que son «dos maneras de decir lo mismo» y que el llamador pasa **una**. Son
convenios distintos desde v0.1.64, así que la identidad I2 se afirma sin
refuerzo, a propósito.

### Y una medida que retira la justificación de las dos ampliaciones

El mismo círculo de Ej_1 que «necesitaba λ = 1,4919» converge ahora en
**λ = 0,862**. Las 61 candidatas de recocido simulado que en v0.1.90 fallaban
todas con «no λ-bracket» y motivaron ampliar hasta +6: sobre tres corridas de
recocido en ese mismo modelo, **341 superficies resueltas entre Spencer y GLE,
ninguna con |λ| > 1,5 y ninguna sin bracket**. Las dos ampliaciones perseguían
el `F_f` deprimido de (A), exactamente como `PENDIENTES.md` §9 predijo antes de
medirlo.

El alcance hasta 6 **se conserva**: es el límite superior de la propia
referencia, y estrechar un rango porque «hoy no lo necesita nadie» es cómo
apareció el ±1,25 de v0.1.74. Lo que sí cambia es que los tests dicen la
verdad sobre él.

---

## 4 · Lo que se ha revalidado, y lo que se movió

### Ej_1, círculo de referencia

| método | referencia | v0.1.105 | v0.1.106 |
|---|---|---|---|
| Spencer | 0,876917 | 0,64 % | **0,343 %** |
| GLE | 0,878343 | 0,53 % | **0,158 %** |

`test_slide_validation_ej1.py` llevaba desde v0.1.19 concediendo a estos dos
**el doble de tolerancia** que a todo lo demás — 1,0 % contra 0,5 %— sin que
nadie hubiera documentado la decisión. La auditoría de v0.1.79 identificó esa
asimetría como el hallazgo: los dos únicos métodos que necesitaban el doble de
margen eran exactamente los dos que comparten la maquinaria de λ. **Las dos
bajan ahora a 0,5 %**, que es la única manera legítima de quitar una tolerancia
doble: quitando la causa.

### Casos no circulares (`test_noncircular_validation_v192.py`)

La deuda que v0.1.105 registró explícitamente —tolerancias subidas a 5 % con la
salida escrita en la cabecera— queda pagada, y las tolerancias vuelven a 0,5 %
y 1,0 %. `TestSpencerHasCollapsedOntoBishop` vuelve a ser
`TestSpencerSeparatesFromBishop`, que es lo que afirmaba en v0.1.92, y esta vez
comprueba que la separación **coincide con la publicada** y no sólo que existe.

### Un caso de validación nuevo: `007-acads-2b`

Los seis casos de `validacion/casos/` validaban una **búsqueda**, y el `001`
dice con todas las letras por qué ninguno podía separar un método de otro: «en
este problema la referencia apenas los separa de Bishop, así que acertarlos no
demostraba nada».

ACADS 2(b) es el complementario. El círculo está **tabulado en el enunciado**,
así que no hay búsqueda y el número mide el método; y las dos referencias
publicadas se separan un 3,9 % — media Bishop de 11 programas 2,204, factor
arbitrado 2,29. El Spencer de v0.1.105 daba 2,2088 y **este caso lo habría
suspendido**. La carpeta no tenía ninguno capaz de detectarlo, y por eso el
defecto sobrevivió ochenta versiones.

El runner de casos aprende de paso a evaluar una superficie declarada
(`"superficie": {"centro": [...], "radio": ...}`) en vez de buscarla.

### El banco entero, re-corrido

60 problemas del banco declaran Spencer o GLE. **Se han vuelto a correr los 60**
—54 con `ejecutar_caso.py` y los 6 que guardan varios modelos con nombre propio
con una herramienta que los identifica por su Bishop—, y el desplazamiento de
cada número está en `_auditoria/DESPLAZAMIENTO_v1106.md`.

| | antes | **ahora** |
|---|---|---|
| problemas con un método de λ enteramente `OK` | 12 | **15** |
| de ellos corroborados sobre el círculo publicado | 8 | **11** |
| problemas del banco enteramente `OK` (de 77) | 16 | **20** |

Sobre la superficie publicada, que aísla el método de la búsqueda: de 40 valores
comparables con su publicado, **28 mejoran** y 12 empeoran. Los mayores
movimientos, todos hacia el valor publicado:

| problema | método | antes | ahora |
|---|---|---|---|
| 59 (con refuerzo) | Spencer | −35,55 % | **−20,01 %** |
| 8 (no circular) | GLE | +11,74 % | **+0,98 %** |
| 8 (no circular) | Spencer | +10,44 % | **+1,05 %** |
| 6 (Talbingo) | GLE | −4,02 % | **−0,04 %** |
| 6 (Talbingo) | Spencer | −3,65 % | **−0,11 %** |
| 42 | Spencer | −2,62 % | **−0,44 %** |
| 3 (ACADS 1c) | GLE | +2,25 % | **−0,11 %** |
| 3 (ACADS 1c) | Spencer | +2,16 % | **−0,11 %** |

Once de los doce que empeoran lo hacen por **menos de 0,75 puntos**. El
duodécimo hay que mirarlo, y no es de esta versión:

**Problema 12, Spencer +19,22 % → +31,99 %.** El modelo ya estaba mal antes de
llegar aquí: su Bishop da 1,2927 contra un publicado 1,069, un **+21 %**, porque
la grieta de tracción SECA no trunca el arco — defecto **D13** del banco,
abierto. Sobre una masa que incluye cuatro metros de terraplén que no deberían
estar, las fuerzas interdovela también son las de otra masa, así que el +10 %
que Spencer se separa ahora de Bishop no es comparable con el +0,94 % que
separan los valores publicados. Queda anotado para volver a medirlo cuando D13
cierre; corregirlo desde aquí sería perseguir un número sobre una geometría
equivocada.

### Y una trampa de medición que este trabajo se comió entera

La primera versión del informe de desplazamiento restaba «lo de ahora» menos «lo
archivado» y llamaba a eso el efecto de v0.1.106. Salieron **109 números movidos
en métodos que esta versión no toca**, lo que parecía desmontar todo el alcance
del cambio.

No lo desmontaba: el **base no era 0.1.105**. Cada caso del banco estaba
archivado con la versión en que se corrió por última vez, y **52 de 60 eran de
0.1.97** — nueve versiones atrás, con el rebanador de cuerda de v0.1.100 y el
eje de momentos de v0.1.105 por medio. Restar contra eso mide nueve versiones,
no una.

El informe da ahora **dos** medidas y no las confunde: el desplazamiento crudo
con la versión base en cada fila, y la **separación respecto de Bishop** antes y
después. Bishop se recorre en la misma corrida, así que la deriva común se
cancela en la resta y lo que queda es esta versión — que es además la magnitud
de la que trata el defecto. Que Bishop se mueva **mide** lo rancio que estaba el
base, y por eso su tabla se conserva en vez de esconderse.

Medido así, sobre la superficie publicada: de 29 filas con Bishop al lado,
**22 abren la separación** respecto de él.

### Y una decisión que NO se ha tomado: Spencer y GLE siguen fuera de 001-004

El plan decía escribirlos por fin en esos cuatro `esperado.json`. **No se ha
hecho, y el motivo cambió.** Estaban fuera porque los métodos estaban mal;
siguen fuera porque **no hay consenso publicado por método** para esos
problemas. Las tablas de Giam y Donald dan «Mean Bishop FOS (n samples)» y
«Mean FOS (n samples)» y nada por método riguroso, así que un valor de Spencer
tomado de la tabla de resultados del manual de verificación sería la salida de
**un** programa con una cita encima — exactamente lo que esos casos dicen
evitar. `TestTheCasesStayHonestAboutSpencer` afirma ahora las dos cosas que sí
son ciertas: que esos cuatro no citan lo que no pueden citar, y que **algún**
caso tiene que distinguir un método riguroso de Bishop contra un número
publicado.

---

## 5 · Anomalías reportadas y NO corregidas (regla 6)

### 5a · Spencer y GLE no son exactamente invariantes a la profundidad de la lámina

Duncan y Wright #70: sobre un talud ya sumergido, subir el agua no puede
cambiar nada. Bishop lo cumple a 9·10⁻¹³ y Janbu simplificado también. Spencer
y GLE se quedan en **3·10⁻⁴**, y el residuo **no baja al apretar la
tolerancia**: es real.

La causa está aislada. En λ = 0 las dos ramas son exactamente invariantes —son
Janbu y Bishop—; en λ ≠ 0 no:

| | F_f | F_m |
|---|---|---|
| λ = 0,0 | 9·10⁻¹³ | 9·10⁻¹³ |
| λ = 0,1 | **16 %** | 0,6 % |
| λ = 0,2 | **45 %** | 1,3 % |

`X = λ·E` se aplica a la fuerza interdovela **total**, y la presión del agua
sobre la cara vertical entre dovelas es parte de ella: sube la lámina y sube
`E`, luego sube el cortante interdovela a igualdad de λ. Lo que rescata el
resultado es que la **raíz se mueve con ellas**, y el cruce acaba casi donde
estaba. «Casi» es la palabra honesta, y está escrita en
`test_ponded_water_v161.py` con las dos medidas y un tripwire de dos caras.

La salida sería extender a estos dos métodos la bifurcación
efectiva/total que `MethodsSettings.interslice_forces` ya ofrece a la familia
Corps desde v0.1.98. **No se hace aquí**: `PENDIENTES.md` §7 registra que falta
el dato externo para resolver efectiva-contra-total, y la evidencia disponible
apunta a **totales** — la referencia separa su Spencer de su Bishop un
+1,888 % con piezométrica y OGR con totales da +2,14 %.

### 5b · GLE se queda sistemáticamente por encima de Spencer

Con la corrección, Spencer cae en +0,10 % sobre la referencia con piezométrica
y GLE en **+0,77 %**. El sesgo es sistemático y del mismo signo en todos los
modelos medidos: problemas 1, 3, 6 y 8 dan +0,01, +0,00, +0,04 y +0,83 %.

**Lo que NO es**: la función de forma. El informe de la referencia dice
`interslice force function : Half Sine`, que es el predeterminado de OGR, así
que nominalmente es la misma `f(x)`. Lo que queda por comprobar es cómo se
normaliza su **argumento** — OGR mapea x linealmente sobre la luz horizontal
entre el primer y el último borde de dovela, y una referencia que midiera x a
lo largo de la superficie, o sobre una luz que una grieta de tracción trunca,
obtendría una `f` algo distinta en cada borde. Un error aleatorio no sería
sistemático; un argumento desplazado sí.

Anotado con su medida en `TestKnownDivergences`, junto al −10,9 % de
Lowe-Karafiath que sigue abierto por su cuenta.

---

## 6 · Coste

La recursión interdovela es trabajo nuevo por pasada, pero entra con una
compensación que no es un consuelo retórico: la linealización de la
resistencia (`_local_c_phi`, que corre por dovela) y el denominador entero de
momentos del caso circular son **invariantes** respecto de `F` y de λ, y ahora
se resuelven **una vez por superficie** en `GLESystem` en vez de una vez por
iteración y por λ. Antes se recalculaban del orden de cientos de veces por
superficie para dar siempre lo mismo.

La actualización de `X` va **acoplada** al mismo bucle de `F`, no anidada
dentro: medido espalda con espalda a tolerancia 10⁻¹⁰, las dos formas dan la
misma λ y el mismo F a seis cifras, y la acoplada llega en 15 a 52 pasadas.

---

## 7 · Archivos

- `ogr_slip2d/interslice.py` — **nuevo**. La recursión, las dos ramas, la
  admisibilidad y el sistema por superficie. Spencer y GLE lo comparten entero.
- `ogr_slip2d/methods/spencer.py`, `gle.py` — el solver interno se va al módulo
  compartido; los dos publican ahora `base_normal`, `base_shear_force`,
  `base_shear_strength` e `interslice_e` / `interslice_x`, que antes estaban
  vacíos. No es cosmético: `rapid_drawdown._stage1_state` lee `base_normal`.
- `gle.py` evalúa además `f(x)` en los **bordes** de dovela y no en el centro,
  que es donde vive `X_i` y donde `_boundary_ratios` siempre lo reportó. Hasta
  ahora el solver y el informe discrepaban sobre la magnitud que define el
  método.
- `ogr_core/project/settings.py`, `methods/base.py` — `min_lambda` y su
  migración.
- `validacion/casos/007-acads-2b/` — **nuevo**.
- `tests/test_gle_interslice_v1106.py` — **nuevo**, las cuatro identidades.
- `tests/test_validation_cases.py` — modo «superficie declarada».
- Revalidados y actualizados: `test_slide_validation_ej1.py`,
  `test_slide_validation_ej2_piezo_v194.py`, `test_noncircular_validation_v192.py`,
  `test_ponded_water_v161.py`, `test_lambda_range_v190.py`,
  `test_project_settings_wiring_v174.py`, `test_published_cases_v179.py`.
- `docs/audits/spencer_gle_interslice_v179.md` — **cerrado**.
- `docs/PENDIENTES.md` — §9 cerrado; §6 cerrado en su mitad medible.

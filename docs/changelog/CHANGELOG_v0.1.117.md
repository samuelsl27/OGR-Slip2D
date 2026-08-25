# OGR Slip2D v0.1.117

**El dato externo que faltaba estaba escrito y no medido — y con él delante
resulta que el criterio de cierre pedía dos cosas que ningún ajuste puede
cumplir a la vez**

---

## De dónde salió

El encargo era la anomalía **A55-1** (defecto **D20** del banco, pendiente §7
de `docs/PENDIENTES.md`), y venía con una advertencia poco habitual: *este
defecto NO SE PUEDE CERRAR CON LO QUE HAY; falta UN dato externo, y si te
lanzas a arreglarlo romperás un caso publicado*.

Lowe y Karafiath (1960) prescriben la inclinación de la resultante entre
dovelas, θ = ½(α + β). Cuando hay agua, esa resultante es la suma de una parte
efectiva y del empuje del agua sobre la cara vertical, que es **horizontal**.
Desde v0.1.61 OGR separa ese empuje —`interslice_water_thrust`— con lo que θ
se impone sobre la fuerza **efectiva**; desde v0.1.98 la alternativa es un
ajuste del proyecto, `MethodsSettings.interslice_forces`, predeterminado en
`effective`. Con esa elección Lowe-Karafiath cae **por debajo** de Bishop en
cuanto hay freática, y todo lo publicado lo pone **por encima**.

El pendiente pedía un número: qué da la referencia con Lowe-Karafiath sobre un
modelo con agua embalsada. **No hace falta un número. La respuesta está
escrita** — y esta versión no cambia una línea de producción, porque lo que
falta ahora no es un dato sino una decisión.

---

## 1 · Lo primero, remedir: las cifras eran de 0.1.97

Entre medias han entrado D05 (base de cuerda), D10 (Spencer y GLE), D13/D14
(grieta de tracción), D15 (superficies compuestas), D41/D42 (T_S sobre la
base), D43 (cara vertical del terreno) y D18 (soporte pasivo dividido por F).
Cualquiera podía haber movido esto. Medido en 0.1.116 con
`_tools/medir_d20_interdovela.py` (banco, fuera de git), sobre el **mismo
círculo** y cambiando **sólo** el ajuste, en memoria:

### Problema 55 — Pockoski y Duncan (2000), talud 1

Círculo (23,333 · 192,778) R 98,2325, 30 dovelas.

| método | `effective` | `total` | publicado |
|---|---|---|---|
| ordinary_fellenius | 1,26554 | 1,26554 | — |
| bishop_simplified | 1,29337 | 1,29337 | **1,293** |
| janbu_simplified | 1,17566 | 1,17566 | 1,151 |
| spencer | 1,29854 | 1,29854 | **1,300** |
| gle_morgenstern_price | 1,29926 | 1,29926 | — |
| **lowe_karafiath** | **1,25346** | **1,31520** | **1,318** (UTEXAS4 1,32) |
| corps_engineers_1 | 1,27437 | 1,33909 | — |
| corps_engineers_2 | 1,29452 | 1,37478 | — |

Relación con Bishop: **0,9691** con efectivas, **1,0169** con totales, contra
**1,019** publicado. Los cinco métodos que no leen el ajuste dan el mismo
número dígito a dígito en las dos columnas, que es el control de que el ajuste
sólo toca lo que le corresponde.

(Janbu simplificado sale un 2,1 % alto porque **este** círculo no es el suyo:
su mínimo crítico es otro, y sobre el que la búsqueda le encuentra queda a
+0,04 % del publicado. Lo que interesa aquí es que Bishop y Spencer, que sí
comparten círculo con Lowe-Karafiath en la tabla publicada, caen a +0,03 % y
−0,11 %: es eso lo que fija el círculo.)

**Sin freática, las dos columnas son idénticas** y Lowe-Karafiath queda un
0,57 % por encima de Bishop — la relación habitual. La anomalía es del término
de agua, no de θ.

### Los otros tres, con la misma forma

| caso | publicado | `effective` | error | `total` | error |
|---|---|---|---|---|---|
| #55 lowe-k | 1,318 | 1,25346 | **−4,90 %** | 1,31520 | **−0,21 %** |
| #56 lowe-k | 1,304 | 1,24936 | **−4,19 %** | 1,30097 | **−0,23 %** |
| Ej_2 piezométrica lowe-k | 0,703504 | 0,62685 | **−10,90 %** | 0,70411 | **+0,09 %** |

El **#51** (Zhu 2003) mejora en la misma dirección pero no llega: la relación
con Bishop pasa de 0,9333 a 0,9738 contra 1,008 publicado. Ese problema tiene
una **capa 4 que el manual no publica** y que gobierna más de media superficie
—su Bishop sale 1,0196 contra 1,278—, así que ni el valor ni la relación son
comparables ahí. Lo que sí dice es el signo. Y su Corps of Engineers #2, que
Zhu publica aparte, pasa de 0,9939 a **1,0673** contra 1,0775 de Zhu.

---

## 2 · El dato que faltaba, y estaba escrito

Cinco líneas independientes, y las cinco dicen **totales**:

1. **La referencia lo declara en su propia base de conocimiento.** Preguntada
   por cómo entran las fuerzas de filtración: *«In the case of total stress,
   you formulate in terms of total force and seepage forces are conveniently
   hidden within the interslice normal forces … This is why [este programa] and
   most LEM programs formulate in terms of total forces»*, citando a **Duncan,
   Wright y Brandon**, *Soil Strength and Slope Stability*, §6.8.1, p. 105.
   Eso es exactamente la rama «≈ 5» que el pendiente daba por concluyente: la
   referencia no desdobla.
   De paso, la misma página afirma *«both give identical solutions»*, y este
   proyecto sabe medido que eso es **falso** para un método de inclinación
   prescrita: es cierto para Bishop, Janbu, Spencer y GLE, y para esta familia
   la diferencia es del 5 al 12 %.

2. **USACE (2003), EM 1110-2-1902 §C-4a**, sobre esta hipótesis en concreto:
   *«This assumption appears to be better than any of the assumptions described
   earlier, especially when the side forces represent **total**, rather than
   effective, forces.»*

3. **El ejemplo resuelto del apéndice G de esa misma norma**, §G-5a: *«The
   interslice forces are total forces and thus include the water pressures on
   the sides of the slices … also consistent with most computer software.»* Y
   ese ejemplo **ya lo reproduce OGR dovela a dovela** desde v0.1.98
   (`tests/test_modified_swedish_v198.py`), alimentando la recursión con las
   columnas publicadas y **sin restar ningún empuje de cara**. Es decir: la
   única validación dovela a dovela que tiene este motor es una validación en
   convenio **total**.

4. **Lo publicado no es sólo de la referencia.** El #55 y el #56 traen columna
   de **UTEXAS4** (1,32 y 1,31), que es el programa de S. G. Wright, coautor
   del libro que cita el punto 1; el #51 viene de **Zhu (2003)**, un artículo.
   Tres implementaciones independientes ponen Lowe-Karafiath por encima de
   Bishop con freática.

5. **La medida de arriba**: con totales, tres valores publicados de
   Lowe-Karafiath se reproducen dentro del **0,25 %**.

**No encontrado**: el artículo original de Lowe y Karafiath (1960) es un acta
del 1er Congreso Panamericano (Ciudad de México, vol. 2, 537-552) y no está en
línea; el informe de Pockoski y Duncan (2000) sólo aparece en copias sin
certificado válido. Se dice, en vez de citar de oídas.

---

## 3 · Y en contra, una identidad analítica que no admite discusión

Sobre un talud **ya sumergido**, subir la lámina Δh añade una presión uniforme
γ_w·Δh sobre todas las caras del sólido libre. La solución exacta de ese
incremento es

    ΔN  = γ_w·Δh·ℓ      ΔE_i = γ_w·Δh·h_i  (HORIZONTAL)      ΔX_i = 0

con lo que σ' no cambia y el factor de seguridad tampoco. Una hipótesis que
obliga a X_i = E_i·tan θ exige ΔX_i = ΔE_i·tan θ ≠ 0. Por tanto:

> **con fuerzas totales, la familia de inclinación prescrita NO PUEDE ser
> invariante con la profundidad del agua.** Es demostrable, no opinable.

Y se ve en la medida, sobre el problema **70** (Duncan y Wright 2005, fig. 6.27,
árbitro 1,60), círculo publicado, 50 dovelas:

| | embalsada 75 | embalsada 105 | boyante | invarianza |
|---|---|---|---|---|
| bishop_simplified | 1,60031 | 1,60031 | 1,60017 | 0,00 % |
| spencer | 1,59536 | 1,59491 | 1,59685 | 0,03 % |
| **lowe-k `effective`** | **1,60758** | **1,60758** | 1,60777 | **0,000 %** |
| **lowe-k `total`** | **5,00000** | **0,22043** | 1,60777 | **destruida** |

Con efectivas la invarianza no es aproximada: **las dieciséis muestras del
residuo Z_n(F) son idénticas dígito a dígito** entre las dos profundidades, no
sólo su raíz. Y la equivalencia de Duncan y Wright —pesos totales + fuerzas de
agua + u contra peso boyante y nada de agua— se cumple al **0,012 %**.

### Corrección a lo que decía el pendiente: el 5,0 no es un factor de seguridad

La tabla vieja apuntaba «Lowe SIN empuje: 5,0000 y 0,2203», y se leía como si
el método diera esos números. **Son dos fallos distintos, y ninguno es un
resultado.** Muestreado el residuo de cierre sobre la rejilla de arranque de
`_force_balance` (16 valores de F entre 0,2 y 5,0), en las dos orientaciones de
marcha:

- **embalsada 75, totales**: el residuo **no cambia de signo en ninguna de las
  dos orientaciones** (de −963 a −11 791 en una, de −337 300 a −483 en la otra).
  No hay raíz. Lo que devuelve `_force_balance` es su `best_fallback`, el menor
  |Z_n| de todos los muestreados, que cae en F = 5,0 — el **techo** de la
  rejilla. Sale con `converged = False`;
- **embalsada 105, totales**: aparece un cambio de signo **espurio** en la
  orientación reflejada, entre F = 0,2 (+89 642) y F = 0,3 (−45 380), y el
  buscador de raíces converge a **0,22043**. Éste es el peor de los dos: es un
  número convergido, plausible de aspecto y sin aviso.

### Consecuencia: el criterio de cierre del encargo es insatisfacible

Pedía a la vez que 51/55/56 dieran relación Lowe-K/Bishop **por encima de 1,0**
(lo que exige totales) y que el 70 mantuviera la invarianza **dentro del 1 %**
(lo que exige efectivas). Ningún valor único del ajuste cumple las dos, y no
por falta de un arreglo: por lo que dice el apartado 3. El criterio queda
**rectificado** en la ficha D20 y en el pendiente. Es la tercera vez que un
encargo de este banco llega con una premisa falsa (D11 traía tres, D18 un
criterio no medible), y merece quedar escrito.

---

## 4 · Lo que NO se ha cambiado, y por qué

El predeterminado sigue en `effective`. Cambiarlo alinearía OGR con lo
publicado y con su propio Spencer/GLE —que aplican λ·E a la fuerza **total**
desde siempre, con su falta de invarianza documentada como *tripwire* en
v0.1.106—, pero deja el problema 70 sin solución, y eso es una decisión de
producto que no toca tomar dentro de una medición. Ningún número validado se
mueve en esta versión.

Lo que sí queda dicho, con fuente, es la salida práctica: sobre un talud
sumergido, el procedimiento **equivalente de Duncan y Wright** —peso boyante
γ' = γ − γ_w y nada de agua— hace desaparecer la bifurcación entera, porque sin
superficie de agua no hay empuje de cara que separar. Los dos ajustes dan
entonces el mismo número, y ese número está a 0,012 % del que da el
tratamiento con agua embalsada y efectivas.

---

## 5 · Un hallazgo lateral, medido y sin corregir (regla 6)

En la misma tabla del problema 70, **Ordinary/Fellenius no es invariante con la
profundidad del agua**, y por mucho:

| | embalsada 75 | embalsada 105 | boyante |
|---|---|---|---|
| ordinary_fellenius | 1,82636 | 2,10024 | 1,51260 |

+21 % y +39 % sobre el equivalente boyante, y un 15 % entre las dos láminas.
**No tiene nada que ver con este defecto**: el método Ordinario no tiene fuerzas
entre dovelas, así que no hay reparto que elegir. La explicación previsible es
la que la literatura le atribuye desde siempre —su normal en la base no sale de
un equilibrio, y con presiones intersticiales altas el método es inexacto;
Duncan y Wright (2005) cuantifican errores de hasta el 60 % en análisis en
tensiones efectivas—, pero **eso no se ha comprobado aquí**, así que queda
anotado como medida y no como diagnóstico. `test_ponded_water_v161.py` ya lo
excluía de su lista `RIGOROUS`, sin decir por qué.

---

## 6 · Lo que se ha escrito

- **`tests/test_interslice_split_v1117.py`** (12 casos, ninguno una
  instantánea): las dos anclas externas enfrentadas. El modelo del problema 55
  y el del 70 se construyen **en código**, con su geometría y su procedencia,
  porque el banco no está en el repositorio y la suite tiene que correr desde
  un *checkout* limpio. Sujeta:
  1. que el círculo es el que describe la tabla publicada — Bishop y Spencer
     reproducen sus valores dentro del 0,5 % **sobre ese mismo círculo**, que
     es lo que convierte la comparación de Lowe-Karafiath en una afirmación
     sobre el **método** y no sobre la búsqueda;
  2. que con totales Lowe-Karafiath reproduce el 1,318 publicado y el 1,32 de
     UTEXAS4 dentro del 1 %;
  3. que con efectivas se queda corto entre el 2 % y el 10 % — **tripwire de
     dos caras**: falla si crece y falla si desaparece, porque desaparecer
     significaría que alguien cambió el predeterminado sin actualizar §7;
  4. la identidad de invarianza con efectivas (1e-6) y la equivalencia boyante
     de Duncan y Wright (0,5 %);
  5. que con totales el 70 se aleja más de un 50 % del equivalente boyante en
     las dos láminas, y que la de 75 ft **no converge** — nombrado aparte,
     porque «el método da 5,0» y «el método no tiene raíz aquí» son hallazgos
     distintos;
  6. regla 7: el ajuste mueve el número en los tres métodos que lo leen, y en
     **ninguno** de los cinco que no.
- `docs/PENDIENTES.md` §7, reescrito entero.
- Ficha **D20** del banco (`ERRORES_Y_DISCREPANCIAS.md`) y la anomalía A55-1 de
  `02_Slide2_Problema055/referencia.json`, remedidas y con el criterio de cierre
  rectificado.
- `_tools/medir_d20_interdovela.py` en el banco, que es de donde salen todas las
  tablas de aquí y no toca ningún `.ogr`.

---

## Qué falta

Una decisión, no un dato: si el predeterminado debe seguir en `effective`
—físicamente coherente, y solo— o pasar a `total` —lo que hace todo el mundo, y
lo que la propia recursión de OGR ya tiene validado dovela a dovela contra la
norma—, aceptando entonces que la familia de inclinación prescrita se queda sin
respuesta sobre un talud sumergido y avisando de ello. Sea cual sea, la
alternativa tiene que seguir siendo alcanzable, porque las dos son legítimas y
la norma que define los métodos lo dice.

Y una tarea propia: extender la misma bifurcación a Spencer y GLE, que hoy
usan totales sin poder elegir (§7, nota de v0.1.106).

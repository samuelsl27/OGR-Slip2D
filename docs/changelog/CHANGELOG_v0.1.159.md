# OGR Slip2D v0.1.159

**El encargo de P-D63 daba por hipótesis una raíz espuria, y la medida la
refuta. No hay ninguna raíz espuria: hay un techo de iteraciones
hardcodeado que borraba en silencio los λ donde vive la raíz buena, y lo
borraba cada vez a más λ conforme se apretaba la tolerancia.**

Cierra **D63** con su criterio literal: el error contra la forma cerrada de
la cuña plana **decrece** al apretar la tolerancia, como siempre hicieron
Corps #1 y Janbu. Y calla la segunda boca del mismo defecto, que era la que
lo hacía silencioso — aunque **no** por donde parecía: el arreglo evidente de
esa mitad se implementó, se midió y resultó peor que el defecto, y §3 lo
cuenta porque es la mitad de la versión que merece recordarse.

Cero dígitos movidos a la tolerancia de serie, y **por demostración, no por
muestreo**.

---

## 1. La premisa del encargo era falsa, y el diagnóstico está medido

La ficha atribuía a una **raíz espuria** que Spencer y GLE se alejen de la
forma cerrada al apretar la tolerancia (+6,7e-4 a 1e-3 → +2,8e-2 a 1e-10 en
el plano de 50°), y mandaba mirar D10 y D20, «las dos de esta familia». La
familia era la correcta —un valor de reserva disfrazado de resultado— pero
el mecanismo no.

**La rama de FUERZAS ya era exacta.** Sobre un plano es *exactamente
constante en λ* —porque Σ(X_{i+1} − X_i) se telescopa y α no varía— y vale
0,9419827599380499 contra una forma cerrada de 0,9419827599379752:
**+7,9e-14**. Todo el error vivía en la búsqueda de λ.

**Y la búsqueda de λ perdía muestras.** `solve_branch` llevaba
`max_passes: int = 80` **hardcodeado**, y `GLESystem.states` lo llamaba con
cinco posicionales, así que el `max_iterations` del usuario nunca llegaba
ahí. La rama de MOMENTOS es una contracción lineal cuya razón tiende a 1 al
crecer λ, medido sobre esa cuña con 50 dovelas:

| λ | razón r | pasadas a 1e-3 | a 1e-10 |
|---|---|---|---|
| 0,2 | 0,770 | 6 | 68 |
| 0,6 | 0,831 | 13 | 100 |
| 1,0 | 0,875 | 20 | 140 |
| **1,2269** (la raíz) | **0,8955** | 25 | **171** |
| 1,5 | 0,919 | 32 | 222 |
| 2,0 | 0,961 | 234 (a 1e-6) | 468 |

De modo que **el conjunto de λ que cabían en 80 pasadas SE ENCOGÍA al
apretar la tolerancia**. Una rama que tocaba el techo salía con
`converged=False`, `GLESystem.branches` devolvía `(None, None)`, y ese λ
desaparecía sin que nada lo contase ni lo dijese. A 1e-10 sobre el plano de
50° sólo sobrevivían λ ∈ {−0,1 · 0,0 · 0,1 · 0,2}, **todas con g < 0**: no
hay bracket, y el camino de reserva devuelve `min(samples, key=|g|)`, que es
λ = 0,2 exactamente — **un nodo crudo de la rejilla**. De ahí salía 0,96866
contra 0,94198.

Eso explica además lo que la ficha llamaba «tampoco es monótono»: no hay
nada no monótono en el solve. Lo que salta es **cuántos λ sobreviven al
techo**, que es una cantidad discreta.

---

## 2. El arreglo: estancamiento, no cuenta de pasadas

El 80 tenía una razón sólida y escrita, en `GLESystem.branches`: en la
polilínea sumergida de Duncan y Wright las ramas «seguían vagando después de
80 pasadas» y el par en que pararon **se cruzaba**, así que la búsqueda lo
tomó por raíz y devolvió 1,051 donde la respuesta es 1,60. **La razón era
correcta; el instrumento confunde dos cosas.** Una rama lenta y una rama
que vaga no son lo mismo, y una cuenta de pasadas no las distingue.

`solve_branch` para ahora por **estancamiento**: mientras el paso
`|f_new − F|` siga batiendo su propio mínimo, la rama sigue; cuando lleva
`STALL_PATIENCE = 80` pasadas sin batirlo, se abandona. Con un tope duro de
`MAX_PASSES = 400` como segundo cerrojo.

**La neutralidad es una DEMOSTRACIÓN y no una muestra.** `stall` se
incrementa como mucho una vez por pasada y arranca en cero, así que **no
puede alcanzar 80 antes de la pasada 81**: las primeras 80 pasadas del bucle
son las de v0.1.158 instrucción por instrucción, y toda rama que convergía
entonces converge ahora al mismo F en el mismo número de pasadas. Elegir
80 como paciencia —el valor del techo que sustituye— es exactamente lo que
convierte el requisito en identidad estructural.

### Dos diseños que parecían mejores y la medida descartó

- **Presupuesto derivado de la tolerancia**
  (`max(80, ceil(ln(tol/paso₀)/ln(r)))`): cierra la escalera, pero sus dos
  constantes son adivinanzas de dos cantidades que varían **×4,4 sobre la
  misma superficie** (r va de 0,702 en fuerzas a 0,961 en momentos a λ=2,0).
  Con r = 0,92 el presupuesto a 1e-10 sale 268 y la rama de λ=2,0 necesita
  **468**: la mata igual que hoy.
- **Autodimensionado midiendo la razón** (`r = |Δ_k|/|Δ_{k−1}|`, y proyectar
  lo que falta): acierta donde el anterior falla —λ=2,0 converge en 468 con
  dos concesiones— pero **revienta**. `E` y `X` no están acotadas como `F`,
  así que en una rama divergente crecen geométricamente hasta que
  `math.fsum` recibe −inf e +inf juntos: `ValueError: -inf + inf in fsum`
  desde dentro de `compute_fos`, **a la tolerancia de serie**, medido en
  `006-xstabl-1999-min-depth` con techo 2000 y en `003-acads-1c` con 5000,
  y cero fallos con 500 o menos. El 80 hacía también ese trabajo y no lo
  decía en ninguna parte. Por eso el tope duro se queda **por debajo de
  500**, y el comentario de `MAX_PASSES` lo explica.

### Y el detector de estancamiento tampoco es perfecto, dicho aquí

Un récord accidental temprano puede matar una rama que converge: el paso de
λ=2,0 baja mucho en la pasada 5 por casualidad, y la contracción real tarda
más de 80 pasadas en batir ese mínimo, así que se abandona en la 85 en vez
de converger en la 468. **No es una regresión** —hoy esa rama también se
descarta, en la 80— pero es el límite honesto del criterio, y sale de la
misma causa que D116 más abajo.

---

## 3. La segunda boca: el umbral 0,02 que mentía — y el arreglo evidente era PEOR

El camino sin bracket se declaraba **convergido** siempre que el residuo
`|F_f − F_m|` estuviera por debajo de un **0,02 hardcodeado**, sin relación
con lo que el usuario pidió: **veinte mil veces** la tolerancia a 1e-6. Con
`error_message` vacío y `reason` vacía. A 1e-6 sobre el plano de 50° Spencer
publicaba un factor **+0,72 % fuera** de la forma cerrada diciendo que había
convergido.

El arreglo evidente es atarlo a la tolerancia pedida. **Se implementó, se
midió, y es peor que el defecto.** `converged` alimenta `LEMResult.is_valid`,
que `search.surface_score` puntúa a infinito, así que apretar ese umbral no
convierte una mentira en una verdad: convierte una **mentira silenciosa en
un VETO silencioso**. Y eso es exactamente D37/C1, el defecto que v0.1.130
se escribió para arreglar — los problemas 60, 90 y 93 del banco publicaban un
mínimo de búsqueda **por encima** del factor que el mismo motor calcula sobre
el círculo del manual, porque ese círculo se resolvía y luego se borraba.

Medido sobre la búsqueda de bloque de Ej_1, 120 superficies, semilla 0:

| | umbral 0,02 | umbral = tolerancia |
|---|---|---|
| superficies válidas | 48 | **43** |
| crítico con `check_m_alpha=False` | **0,654746** | **1,841807** |
| inadmisibles con `check_m_alpha=True` | **3** | **0** |

Un **+181 % del lado inseguro** en el mínimo reportado. Y de regalo, una
violación de la regla 7 creada por el propio arreglo: el chequeo de m-alpha
**deja de hacer nada**, porque las superficies que marcaba quedan vetadas
antes de que llegue a correr, y eso no se ve en ningún número salvo en su
contador de inadmisibles.

**Así que la frontera se queda donde estaba y gana un nombre y una razón**:
`FALLBACK_RESIDUAL_LIMIT = 0.02`, con esta medición escrita al lado para que
nadie —incluido quien escribe esto— vuelva a «arreglarla».

Lo que SÍ estaba mal, y es lo que se arregla, es que **el residuo no se
reportaba nunca**: el resultado decía «convergido» y nada más, y el usuario
no tenía forma de distinguir una raíz resuelta de la muestra más próxima.
Eso se rompe donde romperlo no veta a nadie:

- `details` publica siempre `lambda_residual`, `lambda_tolerance` y
  `lambda_search_fell_back`;
- `lambda_fallback_notes` lo dice en una nota cuando el residuo supera la
  tolerancia pedida — y una nota no es un veto;
- el `error_message`, que sí lo es y que ya existía por encima de 0,02, pasa
  a **nombrar el residuo** en vez de decir «using nearest F_f≈F_m».

Y entra el tripwire que habría cazado el error a la primera y que no existía:
`TestTheFallbackStillCompetesForTheMinimum` mira **a la vez** el mínimo sin
filtrar y el contador de inadmisibles del filtro de m-alpha. Ninguno de los
dos por separado delata el problema; juntos, sí.

---

## 4. Que perder un λ deje de ser mudo

`branches()` confundía bajo el mismo `(None, None)` una rama que **diverge**
—una afirmación sobre el talud— y una que **se quedó sin pasadas** —una
afirmación sobre el solver—. Sólo la segunda puede mover la respuesta sin
que nada esté mal en el modelo. Se separan con `n_passes_exhausted`,
hermano del `n_thrust_rejected` que ya existía diez líneas más abajo, y
`BranchState.passes` es lo que las distingue sin campo nuevo: la que agotó
el tope usó todas sus pasadas, la que se estancó paró antes.

Entra `lambda_fallback_notes` en `analysis_runner`, calcada de las cuatro notas
por método que ya viven ahí (`daylight_tangent_note`, `m_alpha_margin_note`,
`reversed_support_notes` y la de D62) y leída del mismo `crit`, de modo que
llega sola al `AnalysisNotesPanel` de v0.1.155 y a la CLI.

**Dice dos cosas y las dos sólo cuando la reserva ha disparado**: que los
dos factores promediados difieren más de lo que se pidió —ésa es la que
aparece en la práctica— y que un λ se perdió por presupuesto, que es el
límite del solver decidiendo la respuesta. Con bracket encontrado calla,
porque entonces la respuesta es una raíz y no hay nada que avisar.

**Y es alcanzable, que es lo que impide que sea código muerto**: el plano de
**55° sin refuerzo**, Spencer a 1e-10, pierde exactamente un λ así y cae a
la reserva. Sobre los siete modelos de validación a 0,005 · 1e-3 · 1e-6 ·
1e-10 no dispara ni una vez, y eso también está medido y dicho.

La redacción no era libre: el banco decide si D40 sigue cerrado leyendo el
texto de los avisos, y tres subcadenas están vetadas — «stable» junto a
«head», «edge of the search grid» y «path_optimize» —, con la prohibición
más ancha de lo que parece porque «unstable» contiene «stable» y «ahead»
contiene «head». Hay test que lo comprueba en crudo y en minúsculas.

---

## 5. `max_iterations`: investigado, y la respuesta es NO

La pregunta era razonable, porque en **siete de los nueve métodos**
`max_iterations` **es** la cuenta de pasadas del punto fijo de F
(`bishop.py:205` y `:510`, `janbu.py:205`, `modified_swedish.py:599`), y en
Spencer y GLE ese punto fijo es `solve_branch`, el único bucle al que el
ajuste no llega. El patrón `max(self.max_iterations, 60)` incluso existe ya
en `modified_swedish.py:599`.

**Y aun así no se cablea, por una razón medida**: con el criterio de esta
versión el tope interior ya no es un presupuesto de convergencia sino un
**cerrojo contra el desbordamiento de `E` y `X`**, y dejar que el usuario lo
suba es exactamente cómo se alcanza el `ValueError: -inf + inf in fsum` de
§2. Cablearlo cambiaría un ajuste que no llega por un ajuste que revienta.
Queda reportado como D117.

---

## 6. Alcance y verificación

**La barrera estructural, que es la primera**: `solve_branch` tiene **un
solo llamador en todo el árbol** (`GLESystem.states`, `interslice.py:567` y
`:569`); cero en `tests/`, `ogr_cli/`, `ogr_gui/`, `ogr_core/`. Y
`max_passes` sólo acota `for _pass in range(max_passes)`, con un cuerpo
determinista cuyas salidas tempranas no dependen de él.

- **Suite entera, sin argumentos**: ver §7.
- **Identidades D10 (I1-I4) e I5 de 0.1.141**: 38 residuos comparados antes
  y después, **todos con `dF = +0,000e+00` exacto**. Peor residuo 1,27e-9
  contra `IDENTITY_TOL = 1e-6`, tres décadas de margen. Ninguna se apoyaba
  en una rama sin converger: el máximo medido en esas fixtures a 1e-10 es
  **56 pasadas**, margen 80/56 = 1,43×.
- **`test_convergence_tolerance_v198`**: los cuatro factores **idénticos bit
  a bit**, `|F(1e-3) − F(1e-7)|` sin moverse (Spencer 3,627e-4 contra su
  límite 5e-4). Lo único que se mueve es `Spencer.iterations` **12 → 13**,
  que el test no compara.
- **Casos de validación**: los tres `test_slide_validation_*`, las dos
  poligonales y los dos ACADS, **todos +0,000e+00**. Con el matiz que
  corrige la premisa: la neutralidad **no** se debe a que el techo no se
  toque —se toca en cuatro círculos validados— sino a que los λ perdidos
  caen fuera del primer bracket.
- **Rejillas de círculos**: 1040 comparaciones de `fos`, `converged`,
  `error_message` y λ a 0,005 y 1e-3 sobre los siete modelos, **0 movidas,
  0 crashes**. En una rejilla mayor, 1874 evaluaciones con el techo forzado
  a 80 → 268 → 2000, **0 movidas** y el mismo reparto por tipo de salida en
  las 14 filas.
- **Problema 70 del banco**, Spencer sobre su superficie optimizada:
  **1,617724108883411 antes y después**, bit a bit. Y su λ = −1,0, la rama
  que motivó el 80, se sigue rechazando: en **84 pasadas** en vez de 80.
- **Coste, contado y no cronometrado**: pasadas totales de `solve_branch`
  sobre rejillas reales a la tolerancia de serie, **88.985 → 90.339, un
  +1,52 %** (0,00 % en dos de los siete modelos, +4,33 % en el peor). El
  reloj de la suite no distingue nada por debajo del 10 %, así que la
  medida es la cuenta.

**Un dato que mide lo cerca que estaba el precipicio**: la rama de fuerzas
de la cuña de 50° —la única que reproduce la forma cerrada exactamente—
convergía en la **pasada 79 de 80** a 1e-13. Y `ej2 SMALL` con Spencer, un
círculo validado, converge en la **pasada 80 exacta**: estaba a una pasada
de desaparecer.

### La escalera de la cuña, que es el criterio de cierre

Error relativo contra la forma cerrada, sin refuerzo, 50 dovelas:

| β | método | 1e-3 | 1e-6 | 1e-10 |
|---|---|---|---|---|
| 35 | Spencer | −5,840e-4 | −4,265e-7 | −1,366e-4 → **−4,534e-11** |
| 35 | GLE | −2,334e-4 | −7,770e-7 | −3,795e-11 |
| 40 | Spencer | +4,749e-4 | +5,382e-7 | +1,246e-3 → **+5,928e-11** |
| 40 | GLE | +5,545e-4 | +4,859e-7 | +8,581e-4 → **+6,165e-11** |
| 45 | Spencer | +9,556e-4 | +1,802e-6 → +1,046e-6 | +8,220e-3 → **+1,073e-10** |
| 45 | GLE | +7,024e-4 | +8,095e-7 | +6,693e-3 → **+1,269e-10** |
| 50 | Spencer | +6,664e-4 | +7,220e-3 → **+7,268e-7** | +2,832e-2 → **+1,087e-10** |
| 50 | GLE | +5,782e-4 | +6,590e-7 | +2,391e-2 → **+6,646e-11** |

**Las ocho decrecen**, y la columna de 1e-3 no se mueve en ninguna.

### Un hallazgo que el arreglo destapa

**Con refuerzo, el plano de 50° no tiene raíz.** Con el ancla Activa o
Pasiva, el residuo en el λ más próximo es 0,03 a 0,20 y **no encoge** al
apretar la tolerancia, así que el camino de reserva ahí no es un fallo de
convergencia: es el informe correcto de que no hay raíz a la que converger.
El 1 % a 3,5 % de error contra la forma cerrada viene de eso y **no** del
techo que esta versión quita. Se dice en su propia clase de test
(`TestAWedgeWithNoRootSaysSo`) precisamente para que nadie lea esas dos
filas como el mismo defecto y las «corrija».

---

## 7. Resultados de la verificación

**Suite entera, sin argumentos.** Línea base con 0.1.158: **3360/3360** (188
archivos). Con 0.1.159: **3390/3390** (189). La diferencia son 3360 + 30, y
30 es exactamente 23 del archivo nuevo `test_interslice_budget_v1159.py` más
los 7 que gana `test_janbu_wedge_v1142.py` (20 → 27): **ni uno de los
existentes cambia de veredicto**.

**Los 50 tests de esos dos archivos contra el código de 0.1.158: 24
fallan.** De ellos **5 por COMPORTAMIENTO**, y son exactamente los cinco que
enuncian D63:

| test | lo que devolvía 0.1.158 |
|---|---|
| `test_tightening_the_tolerance_moves_them_towards_it` | 6,66e-4 · 7,22e-3 · 2,83e-2 — **sube** |
| `test_each_rung_is_inside_the_bound_its_tolerance_earns` | 7,22e-3 a tolerancia 1e-6 |
| `test_every_plane_reaches_the_wedge_at_a_tight_tolerance` | 1,37e-4 en el plano de 35° |
| `test_the_branch_at_the_root_needs_more_than_the_old_ceiling` | `converged=False`, `passes=80` |
| `test_a_slower_lambda_still_beyond_the_ceiling_also_converges` | `converged=False`, `passes=80` |

Los otros 19 son **estructurales** —`STALL_PATIENCE`, `MAX_PASSES`,
`FALLBACK_RESIDUAL_LIMIT`, `lambda_fallback_notes`, el argumento `patience`,
el contador `n_passes_exhausted` y las claves nuevas de `details` no existen
en 0.1.158— y se dice porque el proyecto pide distinguir las dos cosas y
porque un `ImportError` no demuestra nada sobre el motor.

**Y una lección que la versión no buscaba.** El arreglo equivocado de §3 no
lo cazó ninguno de los tests nuevos: lo cazó la **suite entera**, con cuatro
rojos en `test_postprocess_v122.py` y `test_checks_v132.py`, archivos de
v0.1.22 y v0.1.32 que no tienen nada que ver con Spencer ni con λ. Un cambio
que parecía local a dos archivos del motor movió el mínimo de una búsqueda
un +181 %, y lo único que estaba mirando eran dos tests de hace ciento
treinta versiones. Por eso entra
`TestTheFallbackStillCompetesForTheMinimum`: para que la próxima vez lo cace
el archivo que introduce el riesgo y no la casualidad de que alguien, hace
años, escribiera el test correcto.

---

## 8. Lo que se reporta y NO se corrige (regla 6)

Último defecto del banco: **D114** (v0.1.158). Éstos van del D115.

- **D115 — `iterate_steffensen` se acepta en Spencer y GLE y no se usa
  nunca**, mientras Bishop (`bishop.py:602`) y Janbu (`janbu.py:314`) sí lo
  usan; `test_project_settings_wiring_v174` comprueba que el atributo
  **llega**, no que se use, y su clase de Steffensen sólo ejercita Bishop.
  Regla 7 viva. **Y cablearlo no es el arreglo, está medido**: el patrón de
  Bishop copiado literal *empeora* la rama (λ=1,2269 a 1e-10: 171 pasadas →
  430) y a λ=2,0 **la mata** (`None`), porque el estado de `solve_branch` no
  es `F` sino `(F, X)` y extrapolar F deja X atrás; extrapolando el par
  junto se gana sólo 1,4-1,6×. Y mueve **8 de 8** números a la tolerancia de
  serie (1(c) Spencer a 5e-3: **+0,200 %**), con `iterate_steffensen: true`
  en 7 de los 8 `.ogr` del banco. Es su propia versión.
- **D116 — una rama puede declararse convergida en 2 a 5 pasadas con
  tolerancia floja siendo divergente al apretar.** Medido: ACADS 1(c) λ=1,5
  converge en 2 pasadas a 0,005 y diverge a 1e-3; ACADS 1(a) λ=2,0 en 3 a
  0,005 y diverge a 1e-6; la cuña de 50° λ=2,0 en 5 a 1e-3. Es el reverso
  exacto de D63 —en vez de tirar λ buenos, admite λ malos— y es además la
  causa de que el detector de estancamiento corte λ=2,0 en la pasada 85
  (§2): el récord accidental de la pasada 5 es el que no se bate.
- **D117 — `max_iterations` alcanza uno de los tres bucles y su nombre
  promete los tres.** Gobierna la búsqueda exterior de λ (`spencer.py:245`,
  `gle.py:334`) y nada más; el bucle interior de `solve_branch` y el
  `max_passes = 15` de `search.py:5447` no lo ven. Investigado y
  deliberadamente no cableado por la razón de §5.
- **D118 — `E` y `X` no están acotadas como `F`.** El desbordamiento a ±inf
  y el `ValueError` de `math.fsum` son alcanzables desde `compute_fos` en
  cuanto el tope de pasadas sube, y hoy la única defensa es que el tope es
  bajo. La guarda que faltaría es sobre el empuje, no sobre la cuenta.
- **D120 — el 0,02 de `FALLBACK_RESIDUAL_LIMIT` sigue sin origen escrito.**
  Esta versión le pone nombre y deja medido por qué **no** puede ser la
  tolerancia, que es lo urgente; de dónde salió el número, no. Y la pregunta
  de fondo queda abierta y es más ancha: si una superficie cuyo λ no tiene
  raíz debe competir por el mínimo global —hoy compite, y v0.1.130 lo
  decidió así con razón escrita— o si debería salir por `admissible`, que es
  una preferencia y no un veto. Contestarlo exige medir el banco entero, no
  un modelo.
- **D119 — el residuo del plano de 50° con refuerzo no tiene explicación
  escrita.** Que no haya raíz está medido; *por qué* un ancla de 120 kN/m a
  15° destruye la raíz en ese plano y no en los de 35°, 40° y 45°, no. Es la
  pregunta que este trabajo deja abierta y no la que le encargaron.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later

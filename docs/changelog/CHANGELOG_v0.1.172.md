# OGR Slip2D v0.1.172

**Una rama se declara convergida cuando la iteración CONTRAE, no cuando un
paso cae bajo la tolerancia por casualidad.** Ficha D116 del banco, prompt
P-D116, paquete P2.

---

## 1. El defecto, reproducido antes de tocar nada

`solve_branch` aceptaba la convergencia con **un solo** paso por debajo de la
tolerancia. La iteración está **amortiguada** —`F ← 0,5·(F + f_new)`— y eso le
da un transitorio **oscilante**: los pasos alternan grande y pequeño. Uno de
los pequeños puede colarse bajo una tolerancia floja **por casualidad**, en un
punto fijo que no contrae. Reproducido contra 0.1.171, cuña de 50°, rama de
momentos, λ = 2,0:

| tolerancia | pasadas | F publicado | punto fijo real |
|---|---|---|---|
| 0,005 | 3 | 0,9834072 | 0,8303711 |
| 1e-3 | 5 | 0,9673276 | 0,8303711 |
| 1e-4 | 85 (abandonada) | — | 0,8303711 |

**A 0,005 el error es del 18 %**, y apretar la tolerancia no lo mejora
gradualmente: hace desaparecer el λ. El punto fijo cuesta **585 pasadas** a
1e-12 con la paciencia levantada.

Y no es un caso de laboratorio. La misma forma en ACADS 1(a), círculo centrado
en (36, 45) con R = 20, rama de FUERZAS, λ = −1,0:

| tolerancia | 0.1.171 | 0.1.172 | punto fijo |
|---|---|---|---|
| 0,005 | **0,910304440 en 2 pasadas** | 0,808336373 en 13 | 0,801353205 (114) |
| 1e-3 | 0,802861536 en 20 | idéntico bit a bit | |
| 1e-4 | 0,801485485 en 31 | idéntico bit a bit | |

Dos pasadas y **13,6 % de error**, que es la fila de «2 pasadas» de la tabla
de la ficha reproducida sobre un modelo publicado. Las dos tolerancias
apretadas del mismo caso salen **idénticas en los dos motores**, lo cual dice
la otra mitad: donde no había nada mal, no se mueve nada.

---

## 2. El arreglo

Un solo punto, `solve_branch`, localizado **por nombre de símbolo** y nunca
por número de línea:

```python
    prev_step = prev_step_2 = -math.inf
    ...
        contracting = step == 0.0 or step < prev_step < prev_step_2
        prev_step_2, prev_step = prev_step, step
        if _pass > 0 and step < tolerance and contracting:
```

`step < prev_step < prev_step_2` **es** «las dos últimas razones
`r_k = step_k/step_{k−1}` son < 1», escrito sin la división: ni denominador
cero, ni `inf`, y un `nan` la vuelve falsa, que es el veredicto correcto. Es el
criterio clásico del punto fijo contractivo, **Isaacson y Keller (1966),
*Analysis of Numerical Methods*, §3.1**, citado en el docstring. Ninguna
fórmula geotécnica nueva.

Tres decisiones de diseño, ninguna por defecto:

- **`-inf` y no `+inf`** en el centinela. Con `+inf` la comparación encadenada
  ya es cierta en la SEGUNDA pasada, habiendo visto una sola razón, y el caso
  de dos pasadas que esta versión viene a rechazar vuelve entero. Va fijado en
  un test que lo mide por comportamiento.
- **`step == 0.0`** es el punto fijo EXACTO, y es obligatorio, no adorno: sin
  él una rama que aterriza clavada no vuelve a batir su propio paso cero, muere
  por estancamiento y el λ desaparece. Es la identidad `I5` que nombra la
  ficha (`dF = 0`).
- **La actualización va ANTES del `if`**, para que ocurra también en las
  pasadas que salen por uno de los `break`.

Consecuencia declarada y con su precio dicho en voz alta: **ninguna rama puede
convergir antes de su TERCERA pasada.** Ver una razón cuesta dos pasos y ver
dos cuesta tres.

**No se añade un cuarto contador a `GLESystem`**, y es una decisión, no un
olvido: el criterio no crea una salida nueva del bucle, sólo retrasa la
primera, así que un λ perdido por él sale por el estancamiento o por el
presupuesto de pasadas y ya está contado ahí. Los tres contadores siguen
nombrando las tres salidas. Va dicho en el comentario.

**No se toca nada más**: ni `STALL_PATIENCE`, ni `MAX_PASSES`, ni
`FALLBACK_RESIDUAL_LIMIT` (P-D118 / P-D120), ni `THRUST_SCALE_LIMIT`, ni el
amortiguamiento, ni `GLESystem.branches`.

### Dónde PARA la garantía, dicho en el propio docstring

El criterio descarta el paso afortunado. **NO** pone el valor aceptado dentro
de la tolerancia del punto fijo: una contracción de razón r parada en un paso
de `tol` sigue a `tol·r/(1−r)` de la raíz, y r llega a **0,9614** en esa cuña,
o sea veinticinco veces la tolerancia. El estimador residual que lo cerraría
—`paso·r/(1−r) < tol`, §3.1 de la misma referencia— se midió y **no se
adopta**: convierte λ que hoy dan un número malo en λ **perdidos** (λ = 2,0 a
0,005: converge → no converge), y con `MAX_PASSES` congelado por otra ficha eso
es el mecanismo de D63 corriendo al revés. Es su propia versión. Hay un caso de
test que afirma el hueco, para que nadie lea el criterio como la promesa ancha
que no hace.

---

## 3. Dos hallazgos que el arreglo destapa, y son mayores que el encargo

Ninguno de los dos lo pedía la ficha. Los dos aparecieron como tests en rojo, y
los dos tests estaban escritos **fijando un defecto con una banda**, con su
propio mensaje pidiendo exactamente la medición que los volvió del revés — que
es la forma que v0.1.159 usó con `TestSpencerAndGleSettleOnTheWedge`.

### 3.1 La raíz negativa espuria de Duncan y Wright ha desaparecido

`test_lambda_range_v190` fija que, con el rango de λ abierto hacia atrás hasta
−1,5, la poligonal flotante de Duncan y Wright se pierde. Medido espalda con
espalda sobre esa misma superficie:

| | FS | λ |
|---|---|---|
| 0.1.171, `min_lambda = −1,5` | 1,0657073000399622 | **−1,481520482204042** |
| 0.1.172, `min_lambda = −1,5` | **1,5983406804896207** | +0,3072517086963592 |
| con el recorte de serie | 1,5983406804896207 | +0,3072517086963592 |

La segunda fila es el MISMO número que el recorte, **hasta el último dígito**.
La causa es D116 y no el rango: las dos ramas cerca de λ = −1,5 no convergen,
vagan, y hasta ahora una rama vagando podía dar un paso bajo la tolerancia por
suerte y entregarle a la búsqueda exterior un par que cruzaba. Es la otra
mitad de D63.

**El recorte de v0.1.106 NO se quita**, y nada aquí dice que deba quitarse:
esto es una superficie, y el rango decide qué se muestrea en TODAS. Si el
recorte sigue ganándose su sitio es una medida sobre el banco entero, no sobre
esta fixture. Queda reportado como ficha nueva.

### 3.2 La «discontinuidad de λ» del círculo de Loukidis tampoco existía

`test_yield_acceleration_v1127` documentaba que el factor de Spencer no era
función continua del coeficiente sísmico: entre k = 0,4325 y k = 0,4330 daba un
salto de 1,001017 a 0,996266 mientras λ brincaba de 0,5804 a 0,5516. Medido:

| k | λ en 0.1.171 | λ en 0.1.172 |
|---|---|---|
| 0,4320 | 0,5802387 | 0,5815652 |
| 0,4325 | 0,5804252 | 0,5817041 |
| 0,4330 | **0,5516213** | 0,5814913 |
| 0,4335 | 0,5520515 | 0,5816454 |

El salto era la segunda raíz hecha de ramas que no convergían. Contra la
comprobación que **la propia referencia publica sobre sí misma** —el factor en
Ky tiene que ser 1,000—, círculo seco:

| método | 0.1.171 | 0.1.172 |
|---|---|---|
| **spencer** | 3,737e-3 | **1,189e-7** (×31 000) |
| **gle_morgenstern_price** | 1,933e-4 | **1,730e-9** (×112 000) |
| corps_engineers_1 | 1,952e-10 | 1,952e-10 |
| lowe_karafiath | 1,310e-10 | 1,310e-10 |
| janbu_simplified | 8,866e-8 | 8,866e-8 |
| bishop_simplified | 2,027e-9 | 2,027e-9 |
| ordinary_fellenius | 7,997e-7 | 7,997e-7 |

**Los cinco métodos que no buscan λ no mueven un dígito**, y eso es lo que dice
que la causa es la búsqueda de λ y no la fixture. Los dos que sí la buscan
pasan a reproducir la comprobación de la referencia, y por eso entran en ella
en vez de llevarle una excepción.

En el círculo `ru05`, dicho porque no todo mejora: Spencer no se mueve
(4,117e-5 los dos lados) y **GLE empeora**, de 5,49e-11 a 3,72e-8, con su Ky
moviéndose en la octava cifra. Los dos están tres órdenes dentro de la banda de
1e-5 que el archivo exige, pero el número sube y se publica.

---

## 4. Alcance medido, y una celda que se mueve y la ficha congelaba

- **Escalera de la cuña (§6 de 0.1.159), 32 celdas** (β 35/40/45/50 × Spencer/
  GLE × 1e-3/1e-4/1e-6/1e-10): **se mueve UNA**, β = 35 con Spencer a 1e-3,
  `F` 1,0087532014438025 → 1,0089850311411437, o sea error contra la forma
  cerrada **−5,840e-4 → −3,544e-4**. **MEJORA**, y las otras 31 salen
  `+0,000e+00`. La ficha declara esa columna intocable; se publica la celda con
  su razón y la decisión fue del propietario. La causa es el mínimo de tres
  pasadas, y ese mínimo es imprescindible: las tres filas de la tabla de la
  ficha convergen en 2, 3 y 5 pasadas.
- **Censo de ramas**, siete modelos de `validacion/casos/`, 88 círculos, 15 λ,
  las dos ramas: cambian **3,83 %** a 0,005, **3,60 %** a 1e-3 y **2,58 %** a
  1e-4, de 2640 evaluaciones cada vez.
- **Desglose a la tolerancia del banco (1e-4)**: 1484 idénticas, **56 valores
  movidos** (mediana 5,0e-5 relativo, p90 7,9e-4, máximo 1,0e-1), **12 λ
  perdidos**, **0 ganados**, **0 `None` nuevos**.
- **`compute_fos` completo** sobre esas rejillas: **10 de 176** resultados se
  mueven, **todos Spencer**, el mayor +0,20 % (003-acads-1c, 1,554512544652 →
  1,557693193171).

### La primera fila del banco que se mueve, declarada una a una

La suite la cazó sola, que es para lo que v0.1.161 la puso:
`test_support_failure_v1161.TestNothingMoved` fija bit a bit el círculo
publicado del **problema 091** —quince láminas de geosintético— y Spencer se
mueve:

| | valor | distancia a la respuesta convergida |
|---|---|---|
| 0.1.171 | 0,9641449174231770 | 6,455e-5 |
| **0.1.172** | **0,9641378773625315** | **5,751e-5** |
| convergida (1e-10) | 0,9640803604041095 | — |

Siete partes por millón, **hacia** la respuesta, y una décima parte de la
tolerancia que el modelo pide (1e-4). **Bishop no mueve un dígito** y no
puede: no entra en `interslice.py`, que sólo pisan Spencer y GLE. Y a 1e-6 y
por debajo los dos motores coinciden a nueve cifras y más, que es la frase que
dice que nunca hubo nada mal donde la tolerancia era lo bastante apretada para
verlo. La instantánea se **actualiza con esa medición escrita en su propio
docstring**, no se afloja la comparación: ese caso es el instrumento, y un
instrumento que se relaja la primera vez que marca algo deja de serlo.

### El coste, contado y no cronometrado — y el recuento sorprende

El reloj de la suite varía ±40 s entre corridas idénticas y no distingue nada
por debajo del 10 %, así que la medida es la cuenta de pasadas de
`solve_branch` sobre las mismas 88 superficies × 2 métodos:

| tolerancia | pasadas | llamadas |
|---|---|---|
| 0,005 | 39 674 → 39 887 (**+0,54 %**) | 3296 → 3302 (+0,18 %) |
| 1e-3 | 58 293 → 47 950 (**−17,7 %**) | 4202 → 3408 (−18,9 %) |
| 1e-4 | 62 927 → 60 380 (**−4,0 %**) | 3742 → 3586 (−4,2 %) |

O sea que el criterio **sale más barato** en las dos tolerancias apretadas, y
la causa es la misma que el hallazgo 3.1: rechazar un λ basura cambia dónde
horquilla la búsqueda exterior, y a menudo la horquilla aparece antes y con
menos resoluciones de rama. El archivo de test nuevo cuesta **2 s**.

**Sobre el reloj de la suite entera, y es una corrección a AGENTS.md**: el
documento dice 5 a 7½ minutos y esa cifra está caducada. Sólo
`test_transient_*` tarda ya **162 s**. La corrida completa de esta versión
tardó bastante más que esa horquilla, y **no se ha re-medido la línea base de
0.1.171**, de modo que aquí no se afirma ni que suba ni que baje: lo que sí
tiene una cuenta —el trabajo del solver— baja.

---

## 4 bis. El banco entero, re-corrido, y lo que mueve

154 modelos circulares en **38 738 s (10,8 h)** y 37 tareas no circulares. Las
nueve últimas se re-corrieron aparte tras apagar el equipo, con el filtro por
problema y **`--forzar`**, que ahí no es redundante: sin él el lanzador consulta
`esta_caduco`, que compara la fecha del `.ogr` con la del resultado, y como los
`.ogr` no han cambiado habría dicho «ya corrido» y las habría dejado en
0.1.171. **«Ya corrido» no es «a esta versión».**

### La comparativa: 559 filas, y catorce se mueven

| | antes (0.1.160) | ahora |
|---|---|---|
| OK | 258 | 258 |
| REVISAR | 101 | **102** |
| DISCREPANCIA | 64 | **63** |
| el resto | sin cambio | sin cambio |
| **filas** | **559** | **559** |

`IGUAL` 545, **`MEJORA` 1**, `mejora (mismo estado)` 12, `empeora (mismo
estado)` 1, **sin pareja 0/0**. Y la atribución es limpia: v0.1.171 midió
«559 → 559 IGUAL» contra esta misma línea base, así que **las catorce son de
esta versión**.

**El único cambio de veredicto cierra una discrepancia**: problema 94, circular,
Spencer, contra los 1,129 que publica la referencia — **DISCREPANCIA →
REVISAR**, error **−7,57 % → −4,98 %**.

### Los 262 números, y por qué no se declaran 262

De los 262 movidos, **188 son geometría** de la superficie reportada
(coordenadas de vértices, centro, radio) y **74 son respuestas escalares**. Una
superficie que cambia mueve todos sus vértices por UNA decisión, así que
declarar 188 coordenadas «una a una con su razón» sería una lista larga
fingiendo ser un análisis. `d116()` declara **las 74 escalares una a una** y
admite una cifra de geometría **sólo si ese mismo método, en ese mismo archivo,
tiene una respuesta escalar declarada** — una superficie que se moviera sin que
se moviera ningún número suyo es justo lo que habría que mirar, y así el cierre
se pone rojo en vez de tragárselo. Medido: **cero geometría huérfana**.

**Ningún método ajeno a `interslice.py` se mueve.** Los 15 números cuya ruta no
lleva un método reconocible son escenarios de Spencer y GLE (`spencer_mc`,
`perfil_III_gle`, `circulo_publicado_figura_59_2`).

### Lo que parecía un contraejemplo y no lo era

Tres movimientos son grandes y el mayor **sube** el mínimo reportado, que es el
sentido que este proyecto vigila (D37/C1). Medido, es lo contrario de una
pérdida: **las superficies válidas SUBEN** —094 Spencer 14 810 → 14 985, 092
GLE 15 479 → 15 647— con `generadas` intacto y `válidas + inválidas`
conservado, y los tres se acercan al valor publicado:

| | 0.1.160 → 0.1.172 | publicado |
|---|---|---|
| 094 Spencer | 1,043504 → **1,072753** | 1,129 |
| 094 s/conexión GLE | 1,075457 → **1,104359** | 1,194 |
| 092 GLE | 1,002076 → 1,006584 | 1,111 |

Son los muros de bancadas del 087–094 de D74/D77, donde el mínimo de OGR queda
por debajo por la horquilla de radios. Esto **no** cierra aquello; lo reduce,
porque parte de aquel mínimo estaba hecho de λ aceptados por suerte.

Y uno gana un número donde no lo había: el **círculo publicado del problema
59** no daba factor con Spencer (`null`) y ahora da **0,772453**.

### Dos cosas del balance que NO son de esta versión

- **Los avisos `⚠ inadmisible` nuevos son deriva de esquema.** `admisible`,
  `nota_admisibilidad`, `traccion_bases` y `traccion_chequeo` **no existían en
  0.1.160**, así que aparecen como cambio contra esa línea base. Lo que lo
  prueba sin discusión es a quién le tocan: al **Bishop** del problema 12 y al
  **Janbu** del mismo, que no pasan por `interslice.py`.
- **Las tres filas del 075** que `d116()` cuenta como declaradas las **hereda**
  de `D118_YA_DIFERIAN`: ya diferían antes de que esta versión existiera, y
  re-declararlas como propias sería atribuirse un movimiento ajeno.

### El censo, y la ley que de verdad lo gobierna

344 cifras de censo en 140 método-archivo, todas coherentes, **sólo en
`spencer` y `gle_morgenstern_price`**. Que se muevan es la PRUEBA de que el
criterio rechaza algo: un criterio que no cambiase ningún censo sería la regla
7.

La regla que lo comprueba se corrigió midiendo, y la corrección importa: la
copiada de `d118()` exigía `generadas` intacto, y eso es falso fuera de la
rejilla. Censo del banco entero: **`grid` (124 archivos) mueve `generadas` CERO
veces**, igual que `block`, `auto_refine` y el resto; **`path` lo mueve en 27 de
33 y `particle_swarm` en 2 de 6**. En esas dos el conjunto de superficies es
ADAPTATIVO —lo que se genera depende de lo que se va aceptando—, así que
rechazar un λ cambia cuántas se llegan a formar. Lo que se exige entonces es la
**identidad contable** (`Δválidas + Δinválidas = Δgeneradas`) siempre, y
`Δgeneradas = 0` sólo donde el conjunto está fijado de antemano.

### El coste de la corrida

**×1,162** sobre 0.1.160 en la circular y **×1,042** en la no circular. Es la
misma deriva que v0.1.171 midió (×1,157 y ×1,165) **antes** de este cambio, de
modo que esta versión no añade coste medible a la corrida — coherente con el
recuento de pasadas, que baja.

---

## 5. Lo que se reporta y NO se corrige (regla 6)

- **El récord accidental del detector de estancamiento sigue siendo suyo.** Es
  el paso 3 del encargo, contestado con número: con el criterio nuevo λ = 2,0
  de la cuña **converge en la pasada 60 a 1e-3** —ni en la 468 ni en la 5— y a
  **1e-4 sigue muriendo en la 85**. Se anota, no se arregla aquí, exactamente
  como la ficha manda; y va fijado en un caso de test para que el día que se
  repare se ponga rojo y diga cuál era.
- **El estimador residual**, medido y no adoptado (§2).
- **`STALL_PATIENCE`, `MAX_PASSES` y `FALLBACK_RESIDUAL_LIMIT`** intactos.
- **El recorte del rango de λ de v0.1.106** (§3.1), que puede haber dejado de
  ser portante y que esta versión deliberadamente no toca. Nace como **ficha
  D143** del banco, en el paquete P2, con su criterio de cierre escrito: los
  111 re-corridos con el rango abierto, las filas que se muevan declaradas una
  a una, el coste contado en pasadas, y una decisión. Quitarlo es una medida
  sobre el banco entero y no sobre una fixture, que es exactamente por lo que
  no se quita aquí.
- **GLE empeora en el círculo `ru05`** de Loukidis (§3.2), dentro de la banda.

### Premisas de la ficha que la medición desmiente

1. **«El banco corre a la tolerancia de serie»** (0,005). **Falso desde
   0.1.160**: 193 de los 194 `.ogr` del banco traen
   `settings.methods.tolerance = 1e-4`, y ahí el defecto muerde menos —2,58 %
   de las ramas en vez de 3,83 %—. La tolerancia de serie sigue siendo 0,005 en
   `ogr_core/project/settings.py`, que es lo que ve un usuario nuevo, y por eso
   la segunda puerta del test se fabrica ahí.
2. **«Para ACADS 1(a) y 1(c), los modelos están en
   `test_acads_validation_v178.py`»**. Para 1(c) es falso, y lo dice el propio
   docstring de ese archivo: «ACADS variants 1(c) and 1(d) are not in this
   file: their material boundaries exist only as a drawing». El modelo de 1(c)
   vive en `validacion/casos/003-acads-1c/`. La segunda puerta se construye
   sobre 1(a), que son seis vértices y un material.
3. **El nombre del archivo de test.** La ficha lo llama
   `test_branch_contraction_v1160.py`; `_vNNNN` es la versión en la que el test
   **ATERRIZA**, y esto sale en 0.1.172. Mismo re-anclaje que d91, d95, d96,
   d98, d101, d102, d103, d127, d129 y d118.
4. **`d116()` NO EXISTÍA**, aunque el criterio de cierre la cite como escrita.
   La undécima vez seguida.
5. **Las citas de línea** (`interslice.py:318`, `452-458`) ya no apuntaban a lo
   que la ficha describe, porque v0.1.171 reescribió esa zona. Nada de este
   cambio ni de su test se localiza por número de línea; todo por nombre de
   símbolo.

---

## 6. Los tests

### `tests/test_branch_contraction_v1172.py` — 14 casos, nuevo

**La prueba de que mide algo**: contra el árbol de 0.1.171, con sólo este
archivo presente, **fallan 5 y pasan 9**. Los cinco que fallan son los dos
puertas y el mínimo de tres pasadas; de los nueve que pasan, **tres se declaran
CONTROL en su propio docstring** —las dos tendencias y el caso `dF = 0`, verdes
por los dos lados— porque un caso que no dice cuál de las dos cosas es se leerá
como la que no es.

Ninguna puerta es una instantánea del motor viejo: las dos **reconstruyen**
dónde paraba la iteración desde el motor ACTUAL, topando `max_passes` en la
pasada en que saltaba el paso afortunado, de modo que nada hay que re-medir si
la aritmética se mueve.

### Tres archivos existentes, y en ninguno se afloja una constante

- **`test_lambda_range_v190.py`** — el caso de la raíz espuria se **invierte**
  con la medida (§3.1) y gana una identidad más fuerte que la banda que tenía:
  que el número con el rango abierto es EL MISMO que con el recorte, no sólo
  parecido.
- **`test_yield_acceleration_v1127.py`** — el caso de la discontinuidad se
  invierte (§3.2) y se parte en dos: el factor en Ky para los dos métodos de λ,
  y la continuidad de λ misma, que es la causa y no el síntoma.
- **`test_janbu_wedge_v1142.py`** — la aserción del 3 % se **parte por
  mecanismo**, y no se sube ninguna constante. Medido a 1e-3 sobre sus
  dieciséis filas: **once resuelven bracket y están a 4,6e-4 o mejor**, tres
  décadas dentro de la banda vieja, y **las cinco que pasan de 1e-3 son
  exactamente las que no encuentran raíz** y publican la muestra más cercana.
  Su distancia a la forma cerrada no es error de convergencia —no encoge con la
  tolerancia, que es lo que `TestAWedgeWithNoRootSaysSo` afirma dos clases más
  abajo—, así que una banda compartida acotaba dos cantidades distintas con un
  número, y acotaba las once resueltas **treinta veces más flojo** de lo que
  necesitan. Cada mitad recibe la cota que su propio mecanismo gana: la
  tolerancia pedida para las resueltas, y **su propio residuo publicado** para
  las de reserva (la peor de las cinco está a 0,69 de él). El archivo partido
  **pasa con los dos motores**, que es lo que dice que es conservación y no un
  apaño.
- **`test_support_failure_v1161.py`** — la instantánea del problema 091 se
  actualiza con su medición (§4), y la clase gana en su docstring la tabla de
  tolerancias que autoriza el cambio. Bishop, que es el control, no se toca.
- **`test_interslice_thrust_bound_v1171.py`** — **cero aserciones movidas**; se
  mueve la CELDA en que está fabricada la puerta de D118, y el porqué importa:
  el plano de 35° a 1e-3 ahora **ENCUENTRA horquilla** donde antes no la tenía
  (`lambda_search_fell_back` True → False), así que la búsqueda deja de
  muestrear antes de llegar al λ en fuga. La cota no dejó de disparar; la
  búsqueda dejó de llegar. Barridos todos los planos desnudos de 25 a 70 grados
  a cuatro tolerancias **contra los dos motores**, la celda elegida —52,5° con
  GLE a 1e-4— pierde dos λ por la cota **en los dos**, que es el requisito que
  evita convertir un test de D118 en un test de la versión equivocada. 1e-4 de
  las dos que califican porque es la tolerancia a la que corre el banco.

---

## 7. Verificación

- **Suite entera y sin argumentos**: **3697/3697**, con el árbol quieto y nada
  en paralelo. 0.1.171 traía 3682, y los 15 nuevos son los 14 de
  `test_branch_contraction_v1172.py` más el que gana
  `test_yield_acceleration_v1127.py` al partirse en dos (§3.2). Ni uno de los
  otros archivos cambia de recuento.
- **`verificar_cierres.py D116` da `CUBIERTO POR TEST`**, que es el criterio de
  cierre de la ficha, y **DISCRIMINA**: contra el árbol sin el arreglo contesta
  `NO SE SOSTIENE` nombrando la causa —«`solve_branch` recuerda 1 pasos y hacen
  falta 3»—. Mide por AST y EJECUTANDO, nunca por `grep`, y comprueba los tres
  cerrojos que la ficha congela con su valor delante.
- **Ficha retirada** al índice; `D116` podado a mano de `PAQUETES` y de la
  cadena del paquete P2, y `PROMPTS_RESOLUCION.md` regenerado (41 prompts, 0
  fichas cerradas sin prompt, 0 sin paquete). Sus dos aristas en REQUIERE se
  quedan: D115 y D125 siguen necesitando que el criterio exista, y esa
  dependencia no desaparece porque el prerrequisito se haya cumplido — el
  mismo trato que v0.1.171 dio a D118.
- **Selección dirigida** `interslice lambda acads convergence gle spencer janbu
  slide_validation`: **250/250**.
- **Regla 2**: cero texto visible nuevo, cero entradas de i18n, ningún
  presupuesto movido. **Regla 3**: ninguna acción nueva.
- **Las once probabilísticas NO se re-corren, y es una medición y no una
  omisión**: sus once archivos traen `spencer` **cero** veces y
  `gle_morgenstern_price` **cero** veces —son Bishop— y `interslice.py` no lo
  pisa ningún otro método.

---

## 8. Cuatro errores propios, detectados antes de publicar

1. **La suite se lanzó con `| tail -25`**, que retiene toda la salida hasta el
   final: la corrida terminó y la línea de totales se había quedado fuera de
   las 25 últimas líneas, así que hubo que repetirla redirigiendo a un archivo.
   Es **exactamente** el error que v0.1.171 documentó, repetido una versión
   después.
2. **La primera celda de la puerta de D118** (35° a 0,005) disparaba sólo con
   el motor nuevo, lo que habría convertido dos casos de D118 en un test de
   D116. Lo delató correrlos contra el árbol con el motor guardado, que es la
   razón de hacerlo siempre en los dos sentidos.
3. **Los primeros candidatos a segunda puerta** en ACADS —ramas que convergían
   en 2 pasadas con `F ≈ 0,999`— no eran el defecto sino convergencia rápida de
   verdad: el arranque vale 1,0 y el primer paso es minúsculo. Se descartaron
   midiendo la DISTANCIA al punto fijo en vez de contar pasadas, que es lo que
   separa un paso afortunado de uno merecido.
4. **El heredoc del archivo de test nuevo superó el límite del shell** (~8 KB) y
   murió con `unexpected EOF`; se escribió con la herramienta de escritura, que
   es lo que este proyecto ya tiene apuntado para archivos grandes.
5. **Redirigir a un archivo tampoco basta para ver el progreso**: Python
   bufferea su salida cuando no escribe a una terminal, así que la segunda
   corrida de la suite también estuvo veintiocho minutos con el archivo a cero
   bytes. Hace falta `python -u`, y con él las dos corridas del banco sí se
   pueden seguir. Es el mismo error del punto 1 con otra cara, y los dos juntos
   son la razón de escribirlo aquí: el problema no era la tubería, era el
   búfer.
6. **La detección de «esta fila es de Spencer o de GLE» en `d116()` miraba
   `"/spencer/"`**, y en `.../circulo_publicado/spencer` el método es el
   ÚLTIMO segmento, así que la ruta no casaba y el verificador acusaba a tres
   filas del 075 de venir de un método que no pasa por `interslice.py`. Se
   corrigió comparando por segmentos, y lo delató que las tres filas acusadas
   eran justo las que `d118()` ya declaraba.
7. **La ley de conservación del censo se copió de `d118()` sin comprobar que
   valía aquí**, y no valía: exige `generadas` intacto, lo cual es cierto en
   una rejilla y falso en una búsqueda adaptativa, donde lo que se genera
   depende de lo que se acepta. Acusó en falso al 014 y al 015. El **primer
   arreglo también estuvo mal**: discriminé por `familia_superficie`, que sólo
   escribe uno de los dos lanzadores, y entonces el 042 —un `modelo_path.ogr`
   que produce el lanzador circular— seguía acusado. El discriminador bueno es
   el campo `busqueda` del propio resultado, y la regla salió de censar el
   banco entero en vez de clasificar a ojo.
8. **La guarda de aparición única paró un parche de `verificar_cierres.py`**
   porque la línea del resumen del censo existe **dos veces**, en `d118()` y en
   `d116()`. Se rehizo acotando la sustitución a la región de `d116()`. Es la
   misma familia de error que v0.1.171 documentó con `spencer.py`, y la razón
   de poner la guarda.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later

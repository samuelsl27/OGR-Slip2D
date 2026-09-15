# OGR Slip2D v0.1.171

**P-D118 — el empuje entre dovelas deja de ser la única magnitud del solver
sin cota.**

El encargo pedía una guarda «sobre el empuje, no sobre la cuenta»: `F` está
acotada a `[F_MIN, F_MAX]` y `f_new` se comprueba finito, pero `E` —y con él
`X = λ·f(x)·E`, la normal en la base que carga su diferencia y todo lo que
sale de ahí— no tenía ninguna. Está hecho. Pero **de las siete cosas que la
ficha da por sentadas la medición desmiente las siete**, y la que se cae del
lado caro deja el defecto **corto**, no largo: lo que es alcanzable hoy no es
un choque, es un número.

---

## Lo medido antes de tocar nada (regla 6)

`max|E|` dividido por la escala de fuerzas del modelo (ver `_force_scale`),
sobre la cuña de 50° de `test_interslice_budget_v1159`, con el test de
estancamiento desactivado para aislar el crecimiento:

| pasadas | 10 | 50 | 100 | 200 | 400 | 1000 |
|---|---|---|---|---|---|---|
| **λ = 2,5** (fuga) | 0,021 | 0,12 | 0,45 | **4,1e21** | **2,6e70** | **6,3e216** |
| **λ = 2,0** (converge) | 0,028 | 0,054 | 0,063 | 0,065 | 0,065 | 0,065 |

Con el `patience = 80` de serie la rama de λ = 2,5 se corta en la pasada 123
**habiendo llegado ya a 673 veces la escala**. Y sobre un censo de 64
sistemas × 16 λ × dos ramas × tres tolerancias, la peor rama que dice
`converged=True` lleva **1,7e88**.

### Las dos familias, y cuál es la etiqueta que no sirve

Toda rama que es una **solución** llega como mucho a **0,16 ×** la escala, y
eso incluye las lentas que v0.1.159 peleó: λ = 1,2269 necesita 254 pasadas a
1e-14 y se queda en 0,035; λ = 2,0 necesita 702 y se queda en 0,065. Una fuga
cruza 1 y no vuelve. **Doscientas décadas de separación, no una** — así que
el paso 1 de la ficha se cumple con holgura y el trabajo sigue adelante.

Lo que **no** sirve como etiqueta de «sana» es `converged`, y eso salió de la
misma medición: hay ramas convergidas con el empuje en fuga, y **no** porque
`F` se quede pinchada en el clamp (medido: `F` = 0,2100, 0,9944, 1,3437 —
ninguno es `F_MIN` ni `F_MAX`), sino porque `F_f` es un **cociente** cuyo
numerador y denominador están dominados por los mismos términos en fuga, de
modo que su razón se asienta mientras los dos explotan. Eso es **P-D116** y
no se toca aquí; queda fijado como evidencia en el test.

---

## Las siete cosas que la ficha da por sentadas y la medición desmiente

1. **El `ValueError: -inf + inf in fsum` NO es reproducible hoy subiendo el
   tope.** 2960 llamadas directas a `solve_branch` —los dos modelos que la
   ficha nombra × 75 círculos × 10 λ × las dos ramas × topes 2000 y 5000 ×
   `patience` 80 y desactivado— y 904 corridas completas de `compute_fos` con
   el tope forzado a 400, 2000 y 5000: **cero excepciones**. El changelog de
   0.1.159 §2 explica por qué, si se lee entero: aquella medida se tomó con
   el **autodimensionado** (`r = |Δ_k|/|Δ_{k−1}|`) que estaba evaluando, y no
   con el solver que se publica. La fuga es real; en qué excepción termina es
   suerte.
2. **Su caso discriminante (a) ya estaba VERDE contra 0.1.170.** Pide que «la
   rama divergente con `max_passes=5000` devuelva `None` con la razón, no
   `ValueError`»: hoy ya devuelve `None`. Escrito como está redactado, el test
   no habría medido nada — la trampa de D101, D103, D127 y D129.
3. **Nombra el λ equivocado.** Dice «un λ divergente (2,0 con la rama de
   momentos)». Medido sobre su propia cuña: λ = 2,0 **converge**, en 234
   pasadas a 1e-6 y 702 a 1e-14. El divergente es 2,5, al que
   `test_interslice_budget_v1159` ya llama `WANDERING_LAMBDA`.
4. **Lo alcanzable es peor que un choque: es un número.** El
   `003-acads-1c` produce un par `(F_f, F_m) = (0,983, 5,228)` **convergido y
   declarado admisible por `thrust_is_admissible`**, con `|E|` a **8,1e10**
   veces el peso de la masa — una muestra que la búsqueda exterior de λ
   consume como si fuera una medición. `thrust_is_admissible` pregunta por el
   **signo** del empuje y nunca por su **magnitud**.
5. **Tres de sus ocho citas de línea estaban caducadas el día que se leyó**:
   `E[i+1] = e` está en 414 (acumulado en 412) y no en 421; `X[i] =
   lam_boundary[i]·E[i]` está en 418 y no en 425-426 —425 cae dentro del
   bucle `num`/`den` de la rama de fuerzas, una cita que *parece* buena—; y el
   `isfinite(f_new)` está en 451 y no en 446, por lo cual su propio comando de
   reproducción, `sed -n '380,430p' … | grep -n "…isfinite"`, no puede
   imprimir esa línea. Por eso nada de este cambio ni de su test se localiza
   por número de línea y todo por nombre de símbolo.
6. **El test no es `_v1160` sino `_v1171`**: `_vNNNN` es la versión en que
   **aterriza**.
7. **`d118()` NO EXISTÍA** aunque el criterio de cierre la cite como escrita —
   la novena vez seguida (D91, D95, D96, D98, D101, D102, D103, D127, D129). Y
   su línea base es `Evaluaciones/0.1.159`, re-anclada aquí a **0.1.160** por
   lo mismo que d79, d94, d95, d96, d98, d127 y d129: 0.1.160 metió la
   tolerancia en cada `.ogr` y movió 83 problemas.

---

## El arreglo

### `THRUST_SCALE_LIMIT = 10`, y por qué ése

Es el valor **más apretado que conserva margen**, y no el más flojo que es
seguro: está 60 veces (1,8 décadas) por encima de la peor rama que es una
respuesta, y la fuga lo cruza y no vuelve. 10, 100, 1000 y 1e6 mueven los
mismos cero factores de seguridad, así que **nada salvo el margen decide el
número** — cuanto más flojo, más fuga deja pasar.

### `_force_scale(rows)`, y por qué no `ΣW`

`Σ(|w_eff| + c'·l + |h_drive| + |t_active| + |t_passive|)`: todo lo que
alimenta la recursión de `E`. Es una **escala** y no una cota, y existe para
que el límite sea un número puro en vez de una fuerza — que es lo que
`AGENTS.md` pide cuando dice que las tolerancias van relativas al tamaño del
modelo. **No `ΣW` a secas**, que es la elección obvia y está mal para un caso
que este paquete ya tiene escrito: la lámina delgada de la masa disjunta
lleva 0,9 ft de suelo y sale a F = 34,3, o sea peso pequeño y cohesión no. Se
resuelve **una vez** por llamada, fuera del bucle de pasadas.

Cero es una respuesta legítima y no lleva suelo: una superficie sin carga ni
resistencia da `E = 0` en cada frontera, así que `0 <= 0` y la guarda no
dispara. Poner un suelo sería volver a meter una fuerza absoluta.

### Dónde va la guarda, y es un argumento de orden y no una medición

Entre la marcha de dovelas y la actualización de `X`. `resisting` de la
pasada *k* se construye con la `X` de la pasada *k−1*, así que una rama
cortada en la **primera** pasada cuyo `E` cruza la cota nunca llega a la
pasada que podría entregar un `±inf` al `math.fsum` de la expresión de
momentos. No depende, por tanto, de cuánto se habría pasado la fuga.

Se escribe **`if not (peak <= limit)`** y no `peak > limit`: el segundo es
falso para un `nan`, y un empuje `nan` es exactamente el estado que esto
existe para rechazar. Por lo mismo el máximo se acumula a mano y no con
`max()`, que ante un `nan` contesta según la posición.

### La razón viaja, porque `None` no puede llevarla

`BranchState` gana `abandoned: str = ""` y la rama sale por `break` con
`"thrust overflow"`, igual que sale hoy por estancamiento. La ficha pide
`return None` **con la razón**, y las dos cosas no caben juntas: un `None` no
lleva nada, y `branch_abandoned` —el nombre que propone— no existe en el
repositorio. El campo es además lo que hace la razón medible **al nivel de la
rama**, que es donde la ficha quiere el test.

`GLESystem` gana `n_thrust_overflow`, un **tercer** contador y no uno más
gordo, por la misma razón por la que v0.1.159 mantuvo separados los dos que
ya había: son tres afirmaciones distintas, y el día que compartan una, la
respuesta a «por qué desapareció este λ» vuelve a ser «algo salió mal».
`branches()` atribuye por `abandoned` **antes** que por la cuenta de pasadas,
porque una rama puede cruzar la cota en su última pasada.

`spencer.py` y `gle.py` publican `lambdas_lost_to_thrust_overflow` en sus dos
salidas cada uno, y `analysis_runner.lambda_fallback_notes` gana su tercera
frase. **No veta**: `error_message` alimenta `is_valid`, que
`search.surface_score` puntúa a infinito, y eso es D37/C1. La frase tampoco
ofrece «afloja la tolerancia», que es lo que sí ofrece la del presupuesto:
aquí la rama no estaba mejorando.

### El comentario de `MAX_PASSES`, reescrito

Decía dos cosas. Una la vuelve falsa esta versión: «`E` y `X` no están
acotadas como `F`». La otra **ya era falsa**: «el test de estancamiento es lo
que de verdad lo impide … y éste es el segundo cerrojo, no el primero», cuando
su propia frase anterior mide el desbordamiento **con el test de
estancamiento puesto**. El primer cerrojo era este techo, y no lo decía en
ninguna parte. Ahora el cerrojo es la cota, que vigila lo que se escapa en
vez de cuántas pasadas tarda en hacerlo.

### Regla 2 y regla 3

Cero texto visible nuevo: las notas nacen en `ogr_slip2d`, que no importa
`ogr_gui.i18n`, y llegan en inglés como las dos que ya había. Cero entradas de
i18n, ningún presupuesto movido, ninguna acción nueva.

---

## El test

`tests/test_interslice_thrust_bound_v1171.py`, 20 casos. **Contra el árbol de
0.1.170, con sólo el archivo presente, fallan 16 y pasan 4** — y los 4 son
justo los que deben:

- **el paso 3 de la ficha** (nada sale del rango numérico con el tope a 5000),
  verde por los dos lados, y **eso es el hallazgo**: el `ValueError` no es
  alcanzable. Su docstring lo dice, porque un test que no declara cuál de las
  dos cosas es se leerá como la que no es;
- **los dos constantes que la ficha congela** (`MAX_PASSES = 400`,
  `STALL_PATIENCE = 80`), declarado CONTROL: guarda contra un error que **este**
  diseño podría cometer —comprar la cota aflojando los dos cerrojos que viene
  a relevar— y no contra el defecto que quita;
- **las dos vallas del canal** que v0.1.159 ya tenía: la nota calla cuando la
  búsqueda encontró su horquilla, y calla cuando no se perdió nada.

Lo discriminante, con su razón: la rama en fuga se abandona **con la razón**;
se abandona en la **primera** pasada que cruza la cota, comprobado como
identidad (la pasada anterior está por debajo) y no como número capturado;
todo lo que devuelve sigue siendo finito; y **sin** la cota la misma rama pasa
de 1e100 veces la escala. La escala es relativa al modelo, comprobado con el
**mismo talud a diez veces el tamaño y con la cohesión escalada igual** —peso
va con el cuadrado de una longitud y una fuerza cohesiva con su producto por
una, así que escalar las dos deja la razón intacta—: mismo veredicto, mismas
pasadas y `|E|`/escala igual a nueve cifras (12,8524892533 contra
12,8524892548).

La conservación se escribe como un **A/B en el mismo proceso** —la cota puesta
contra la cota levantada— y no contra una instantánea: 5 planos × 2 métodos ×
3 tolerancias dan `fos`, `converged`, `error_message` y λ **idénticos**, y más
de 40 ramas convergidas dan el **mismo `fos` y las mismas `passes`**. El ancla
externa no está en este archivo a propósito: la forma cerrada de la cuña vive
en `test_janbu_wedge_v1142`, y un test del mecanismo que también fuese dueño
del valor de referencia podría hacerse pasar moviendo la referencia.

La puerta se fabrica además **sin parchear nada**: el plano de 35° con Spencer
a la tolerancia de serie pierde de verdad un λ por la cota, así que
`details` y la nota se comprueban por el camino real. En ese mismo caso
`admissible` es `False` —los paramentos salen en tracción neta, que es el
camino del problema 85 y no tiene nada que ver con D118—, y se afirma **contra
la misma corrida con la cota levantada** en vez de contra la palabra `False`,
para que siga siendo una afirmación sobre lo que este cambio **no** mueve.

Ninguna aserción fija un factor de seguridad: lo que se comprueba son
identidades, recuentos, nombres y cotas recalculadas allí.

### El docstring que esta versión vuelve falso

`test_interslice_budget_v1159.py` está entre lo intocable de la ficha, y su
clase `TestTheBackstopIsBoundedOnPurpose` afirmaba que `E` y `X` no están
acotadas. **Se corrige el docstring y no se mueve una sola aserción**, y eso
está medido y no dicho: 75 líneas `assert`/`def test` idénticas antes y
después. Precedente v0.1.167, que corrigió por lo mismo el de
`test_surfaces_menu_labels_v1166.py`.

---

## Verificación

Suite entera y sin argumentos: **3682/3682**, cero fallos, con el árbol
quieto y nada en paralelo. 0.1.170 traía 3662, y los 20 nuevos son este
archivo.

Selección dirigida `interslice lambda gle spencer acads convergence thrust`:
**175/175**, 13 archivos, con `test_interslice_budget_v1159`,
`test_gle_interslice_v1106`, `test_lambda_range_v190`,
`test_lambda_sampling_v193`, `test_janbu_wedge_v1142`,
`test_acads_validation_v178` y `test_convergence_tolerance_v198` entre ellos —
los que la ficha congela.

Los siete sitios del número de versión se cambiaron **uno a uno con guarda de
aparición única y no con un `sed`**: hay **16** menciones históricas de
`0.1.170` en comentarios, dos de ellas en `main_window.py`, y una sustitución
global habría falsificado en qué versión se hizo aquello. Es el error que
v0.1.168 documentó; las 16 se contaron antes y después y siguen siendo 16.

### El banco

Corrida homogénea completa: **`correr_todo.py --forzar`, 154 de 154 modelos
circulares en 40 393 s (11,2 h), cero fallos**, y **`correr_no_circular.py
--forzar`, 37 de 37 en 15 711 s (4,4 h), cero fallos** — estos últimos porque
ahí vive el OTRO `math.fsum` que la cota protege, el de `moment_balance`.

`balance_evaluaciones.py` contra `Evaluaciones/0.1.160`: **559 filas → 559
filas, las 559 IGUAL, cero sin pareja.**

Y el A/B fino, número a número, separa dos cosas que el criterio de la ficha
mete en una:

| | |
|---|---|
| números que son una **RESPUESTA** (factor, superficie, σ′max) | **0 movidos** de 15 826 |
| de ellos, Spencer o GLE | 5823 |
| **censo** de la búsqueda (`validas`/`invalidas`/`inadmisibles`) | 54 cifras, 20 método-archivo, 11 problemas |
| métodos en los que se mueve el censo | **sólo** `spencer` y `gle_morgenstern_price` |
| conservación `Δvalidas + Δinvalidas` | **0 en las 20**, y `generadas` intacto |
| resultados cuyos avisos nombran la guarda | 16, en 8 problemas |

**Que el censo se mueva es la PRUEBA de que la cota rechaza algo**, no un daño
colateral: un cero ahí sería la regla 7, el ajuste que no mueve el número. Se
mueve en los DOS sentidos —**29 superficies salen** del conjunto válido y **7
entran**—, porque quitar una muestra de λ que era basura cambia dónde horquilla
la búsqueda exterior y a veces la arregla. Ninguna de las 36 era la crítica de
su problema: por eso las 559 filas siguen idénticas.

**Las once probabilísticas NO se re-corren, y es una medición y no una
omisión**: sus once archivos traen `spencer` cero veces y `gle_morgenstern_price`
cero veces —son Bishop— y `interslice.py` no lo pisa ningún otro método. Ahorra
34 min que no habrían medido nada.

`d118()` da **CUBIERTO POR TEST**, y se comprobó que **discrimina**: contra el
árbol sin el arreglo contesta NO SE SOSTIENE nombrando la causa («no existe
`THRUST_SCALE_LIMIT`: el empuje sigue sin cota»).

Se escribe con la forma de `d127()` y `d129()` y **no toma por
evidencia el `grep` que pide el criterio de cierre**: un `grep` de `thrust
overflow` no distingue una guarda de un comentario que la menciona, y este
archivo tiene ahora varios comentarios que la nombran — el fantasma del
presupuesto 210 otra vez. Se comprueba, porque retirar la cadena sí sería una
regresión, pero la medida de verdad es por **AST** y **EJECUTANDO**
`solve_branch` sobre la rama en fuga real con el tope a 5000. Mide además lo
que **no** puede moverse —la rama lenta sigue convergiendo por encima del
techo 80 que D63 quitó— porque un verificador que sólo mirase la fuga daría
por bueno el día que alguien apretase la cota hasta matar las respuestas; y el
254 se **informa** y no se exige, porque exigirlo pondría esta ficha en rojo
cada vez que otra versión tocase el solver legítimamente.

---

## El coste: 9 %, y medido SIN cronómetro

La guarda entra en el bucle más caliente del paquete, así que el coste hay que
decirlo con un número. Tres intentos, y **los dos primeros no resolvieron
nada**, que es la parte que merece recordarse.

**1. A/B de variantes, espalda con espalda.** Tres versiones cargadas del mismo
fuente —la publicada, la misma con el pico en un segundo bucle sobre `E`, y la
de 0.1.170 sin guarda— más la publicada otra vez como **control**, en
round-robin de 15 rondas. El control difirió de sí mismo un **6,5 %** en
mediana, más que la diferencia entre las variantes comparadas, y **por mínimos
el orden se invertía** hasta poner la versión *con* guarda por debajo de la
versión *sin* ella, que es imposible.

**2. Tres versiones del programa entero, en worktrees, alternadas.** 0.1.160,
0.1.170 y 0.1.171 sobre los mismos 113 círculos, cinco rondas intercaladas para
cancelar la deriva. Peor todavía: **0.1.160 pasó de 1,41 s en la primera ronda a
1,73 s en la quinta sin tocar una línea**, un 23 % de deriva DENTRO de un mismo
brazo, que es más que todos los efectos buscados juntos. Es literalmente el caso
que `AGENTS.md` documenta con `_column_weight`.

**3. Contar el trabajo, que no tiene reloj.** Instrumentando `solve_branch` sobre
los mismos 113 círculos y los dos métodos, con la guarda y sin ella:

| | con guarda | sin guarda | |
|---|---|---|---|
| llamadas a `solve_branch` | 5174 | 5206 | **−0,6 %** |
| pasadas totales | 51 119 | 48 814 | **+4,7 %** |

Determinista, sin cronómetro y reproducible. Y contesta de paso la pregunta que
de verdad importaba, que no era el coste: **la cota NO obliga a la búsqueda de λ
a trabajar más.** Era el riesgo real de diseño —quitar una muestra podía dejar
al buscador sin horquilla y mandarlo a barrer la rejilla entera más la
extensión—, y las llamadas BAJAN un 0,6 %. Lo que sube son las pasadas, un
4,7 %, porque abandonar un λ cambia por dónde biseca el buscador.

Sumado a la aritmética añadida —`abs` y una comparación por dovela y pasada, ~3
bytecodes contra los ~73 que ya cuesta una dovela-pasada, ~4 %— sale **~9 %
sobre el trabajo de Spencer y GLE**. Y ese 9 % coincide con lo único que el
cronómetro sí dejó ver (+7 % en mediana con un control de 4,7 %), que es la
razón para creérselo: dos estimadores independientes, uno sin reloj.

**Por qué se publica la variante fundida y no la del segundo bucle**: el pico se
acumula en la marcha que ya visita cada `E` uno a uno, y los dos números son
idénticos por construcción —`E[0]` no se escribe nunca y vale 0, y `E[1..n]` son
los valores sucesivos de `e`—, así que el segundo bucle es un paseo entero por
n+1 flotantes a cambio de nada.

---

## La corrida del banco salió un 16 % más lenta, y eso NO se explica aquí

`correr_todo.py --forzar` costó **11,2 h** contra las 7,2 h que la ficha
presupuesta, y modelo a modelo contra `Evaluaciones/0.1.160` el cociente es
**×1,16** con poca dispersión sobre 163 archivos comparables. Queda **reportado
y no explicado**, porque atribuirlo sería inventar:

- **No es el soporte.** Partido por si el modelo lleva refuerzo: **×1,157 con
  soporte (31 archivos) y ×1,165 sin él (132)**. Las 807 líneas que v0.1.161 a
  v0.1.163 metieron en `support_integration.py` —el único cambio gordo del
  camino entre las dos versiones— no pueden ser la causa de algo que sube igual
  en modelos que no tienen un solo anclaje.
- **No es `interslice.py` antes de esta versión**: el archivo **no cambió ni una
  línea** entre 0.1.160 y 0.1.170.
- **Mi parte son los 9 % de arriba**, y el modelo completo corre además Bishop y
  Janbu, que no toco, así que sobre el modelo entero mi parte es MENOS de 9 %.
  El resto no lo cubre esta versión.
- **Y el presupuesto de la ficha estaba caducado de todos modos**: sus 7,2 h son
  de 0.1.159, antes de que 0.1.160 metiera la tolerancia en cada `.ogr` y moviera
  83 problemas. Una tolerancia más apretada son más pasadas.

La causa honesta de que esto aparezca ahora es que **el banco no se re-corría
entero desde 0.1.160**: diez versiones de coste acumulado sin que nadie las
midiera. Lo que este changelog puede afirmar es el 9 % propio; lo demás es un
hallazgo de esta corrida y no una conclusión.

---

## Errores propios, detectados antes de publicar

- **El parche de `spencer.py` casó dos veces donde debía casar una.** El
  patrón con 16 espacios de sangría es **subcadena** del de 20, así que la
  segunda sustitución encontró la línea que la primera acababa de escribir.
  Lo delató la guarda `count(old) == 1` del propio parche —que es para lo que
  está— y se rehízo anclando los patrones al salto de línea. Nada llegó al
  disco: el script escribe después del bucle.
- **La primera redacción del test afirmaba `r.admissible is True`** sobre el
  plano de 35°, y ahí es `False` desde antes de que la cota existiera. La
  aserción medía el fixture y no el cambio; se sustituyó por la comparación
  contra la misma corrida con la cota levantada, que es lo que de verdad se
  quería decir.
- **`d118()` se escribió primero con `lenta.passes != 254`**, un número
  medido convertido en condición de cierre. Un pin así reabre la ficha por la
  razón equivocada en cuanto otra versión toque el solver; se cambió por la
  invariante (converge y pasa del techo 80) con el número informado al lado.
- **Las dos corridas del banco se lanzaron con `| tail -N`**, que retiene toda
  la salida hasta que el proceso termina, así que durante 15 h no hubo progreso
  visible y hubo que inferirlo por el `mtime` de los resultados. Y ahí se
  cometió el segundo: el glob era `resultados_no_circular.json` exacto, cuando
  varios problemas escriben nombres con sufijo, de modo que se leyeron **11 de
  34 hechos donde había 32** y se proyectaron 7 h de espera que eran 12 min. La
  tubería debió ir a un archivo.
- **Dos parches no casaron donde debían y la guarda `count(old) == 1` los paró
  los dos**: el de `spencer.py`, porque el patrón de 16 espacios de sangría es
  **subcadena** del de 20 y la segunda sustitución encontraba la línea que la
  primera acababa de escribir —se rehízo anclando al salto de línea—; y uno de
  `verificar_cierres.py`, porque el idioma que buscaba lo comparte con `d94()`.
  Ninguno llegó al disco: el script escribe después del bucle.
- **La primera redacción de la guarda recorría `E` en un bucle aparte**, un
  paseo entero por n+1 flotantes en cada pasada del bucle más caliente del
  paquete. Se fundió en la marcha que ya los visita uno a uno, y la razón
  para hacerlo NO fue el cronómetro —que no resuelve nada aquí, ver arriba—
  sino el recuento del trabajo añadido.
- **`d118()` contaba como «dígito movido» dos `nan` en la misma ruta.**
  `nan != nan` es cierto siempre, así que el `resultados_procedimientos.json`
  del 096, que guarda un `nan` en `b_bar/spencer/0` desde antes, se leía como
  una regresión inventada. Es un fallo de la forma de comparar que `d127()` y
  `d129()` tienen igual y nunca notaron, porque sólo miran las once corridas
  probabilísticas y ninguna trae un `nan`.
- **La primera suite completa se lanzó antes de escribir el changelog** y
  `test_version_consistency_v176` exige que exista
  `docs/changelog/CHANGELOG_v0.1.171.md`, de modo que habría salido roja por
  una razón que no es el cambio. Se paró y se relanzó con el árbol completo,
  en vez de leer un rojo falso y corregirlo después.

---

## Reportado y no corregido (regla 6)

- **`thrust_is_admissible` mira el signo y nunca la magnitud.** La cota la
  complementa dentro del solver, pero el criterio publicado sigue aceptando
  cualquier magnitud mientras la resultante sea compresiva.
- **`converged` no significa «sana»**, y esta versión no lo arregla: 132 ramas
  de la propia cuña convergen con el empuje por encima de la cota. Es **P-D116**,
  y queda fijado como evidencia en `TestWhatThisDoesNotFix` con el número
  delante, para que la versión que lo arregle vea qué movió.
- **`STALL_PATIENCE = 80`, `MAX_PASSES = 400` y `FALLBACK_RESIDUAL_LIMIT =
  0,02` no se mueven**, como manda la ficha: cambiarlos aquí mezclaría dos
  causas, y el último es P-D120 con el arreglo evidente ya medido como peor
  (+181 % del lado inseguro).
- **El `ValueError` de la ficha queda sin reproducción en el árbol
  publicado**, dicho con el número de llamadas delante en vez de repetido de
  oídas. Sigue siendo alcanzable para cualquier variante de la iteración
  —el autodimensionado de 0.1.159 lo produjo— y por eso esta cota es lo que
  desbloquea P-D117.
- **La nota sólo se narra por el camino de reserva.** `lambda_fallback_notes`
  devuelve `[]` salvo que `lambda_search_fell_back` sea cierto, así que un λ
  perdido por la cota en una corrida que **sí** encontró horquilla viaja en
  `details` y no en la frase. Es la misma cobertura que tiene
  `lambdas_lost_to_budget` desde v0.1.159, y ensancharla es un encargo propio.

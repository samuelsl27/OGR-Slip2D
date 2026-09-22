# OGR Slip2D v0.1.189

**El chequeo m-alpha deja de cribar métodos que no forman su denominador, y
deja de adivinar el signo con el que se formó.** Dos fichas del paquete P3,
D111 y D112, abiertas desde v0.1.158 sobre la misma función. Y de las dos hubo
que corregir primero la premisa con la que estaban escritas — lo cual, en esta
serie, ya no sorprende, pero conviene decirlo antes que el arreglo.

---

## 1. D111 — la referencia SÍ distingue por método, y se puede demostrar

El paso 1 del prompt pedía leer la documentación de la referencia y *«confirmar
por escrito que aplica la forma de Bishop a todos los métodos»*, con la
advertencia de que **si distingue por método la ficha cambia de naturaleza**.
Distingue.

Su **prosa** no: una sola fórmula, la de Bishop, sin cláusula por método, en la
página de parámetros de iteración y en la tabla de códigos de error. Pero su
**comportamiento** sí, y está publicado en los informes de sus dos ejemplos
trabajados. Recuento del error −112 por bloque de método:

| método | Ej_1 | Ej_2 |
|---|---|---|
| ordinary/fellenius | **ausente** | **ausente** |
| bishop simplified | 97 | 225 |
| janbu simplified | 91 | 146 |
| janbu corrected | 91 | 146 |
| spencer | 110 | 250 |
| **lowe-karafiath** | **ausente** | **ausente** |
| gle/morgenstern-price | 111 | 248 |

**Y la ausencia no es «no impreso»: es cero, por aritmética.** En los catorce
bloques de los dos informes los códigos de error impresos **suman exactamente**
el número de inválidas impreso — 1472 y 2401 en el primero, 1411 y 2722 en el
segundo. No queda ni una superficie sin explicar donde pudiera esconderse un
−112 omitido. Y la población es **la misma para los siete métodos** (4851 en el
primero, 4840 en el segundo), de modo que Lowe-Karafiath vio exactamente las
superficies empinadas de las que Bishop descartó 97 y no descartó ninguna por
esa razón. Que corrió está comprobado por otro lado: acumula 37 y 129
superficies bajo el código −111.

Eso es **el caso publicado que el paso 3 pedía** — no uno donde la *forma*
decida la admisibilidad, sino uno donde la decida la **aplicabilidad**.

### El «4,8 %» de la ficha no era de Janbu

La ficha medía `cos α = 0,7230` contra `n_α = 0,6896` en la base φ = 0 más
inclinada de la superficie publicada del 75, y lo atribuía a Janbu. No lo es:
`cos(43,7° + 2,7°) = 0,6896` es la **familia de inclinación prescrita**, con el
θ = 2,7° de la hoja publicada. La frase «la hoja de James Bay publica `n_α` por
Janbu» es inexacta — esa hoja es equilibrio de fuerzas con θ prescrito, y Janbu
simplificado sería θ = 0, que devuelve exactamente la forma de Bishop.

Para **Janbu** el hueco en ese mismo caso es del **39,5 %**, no del 4,8 %. Y
**gobierna otra dovela**: la 11 con la forma de Bishop y la familia θ, la 1 con
la de Janbu. Las tres formas sobre las once dovelas publicadas:

| forma | mínimo | dovela que gobierna |
|---|---|---|
| Bishop (la del chequeo) | 0,7230 | 11 |
| Janbu `n_α` | **0,5181** | **1** |
| familia θ | 0,6896 | 11 |

**Y las tres pasan 0,2 con holgura**, así que el único caso publicado en mano
**mide** el hueco y **no discrimina** la forma. Eso va afirmado en el test, no
insinuado: un caso que no puede decidir no se disfraza de uno que sí.

### `n_α ≡ cos α · m_α`, y los dos techos

El denominador de Janbu **es** el de Bishop multiplicado por `cos α` —
identidad exacta, comprobada sobre una rejilla de (α, tan φ, F, s), y ya
escrita en `interslice.py` desde v0.1.106. De ahí dos cosas: las dos formas
nunca difieren en **signo** (`cos α > 0`), sólo en tamaño; y aplicar 0,2 a
`n_α` **es** aplicar `0,2/cos α` a `m_α`, o sea un criterio distinto con el
mismo número. Bajo φ = 0, donde el límite degenera en un techo de ángulo de
base, la diferencia se ve entera: **78,463°** con la forma de Bishop,
**63,435°** con la de Janbu, **15,03° de distancia**, sin una sola fuente que
lo diga. Por eso la rama (b) —denominador por método— no es elegir un
denominador: es **inventar un criterio**. Lo que haría falta para ella es un
caso publicado con una base en la banda 63,4°–78,5°, que es D61 y sigue
abierta.

### Lo que cambia, y dónde

`M_ALPHA_SCREENED` en `checks.py`, **lista BLANCA y no negra** por la lección de
D164: una lista de excepciones adopta en silencio todo método que nazca
después, y el precio de ese error aquí es una superficie tirada por un
denominador que su método nunca formó. Los cinco que la referencia criba;
fuera, `ordinary_fellenius` y la familia de inclinación prescrita.

`NO_M_ALPHA_DENOMINATOR` se **muda** de `analysis_runner` a `checks` y el único
lector lo **importa**. Son dos conjuntos y no uno porque contestan dos
preguntas: la familia prescrita **no se criba** pero **sí divide por algo**, así
que la nota debe seguir hablándole — y con el cribado fuera, la nota es lo
único que queda mirando. Que la nota y el chequeo tuvieran cada uno su copia es
exactamente cómo llegaron a discrepar: la exclusión de D104 vivía sólo en la
nota mientras `m_alpha_check` cribaba igual.

La puerta va en **`m_alpha_check`**, la función más pequeña cuyo asunto entero
es el criterio. Consecuencia que conviene señalar: **`search.py` no cambia ni
una línea**, y ésa es la mejor prueba de que está en el sitio bueno. Y
**`base_m_alphas` tampoco**: es una MEDIDA, no un veredicto — la leen la nota y
el diagnóstico de descenso rápido, y silenciarla habría quitado el número a los
dos lectores para cambiar a uno.

**Los dos Corps entran por INFERENCIA DE FAMILIA**, y va escrito con esa
palabra: ninguno de los dos informes los ejercita. La inferencia es débil sobre
la referencia y **fuerte sobre este programa**, y esa mitad se mide en el test:
las tres clases comparten `PrescribedInclinationMethod._march` por identidad de
objeto función y sólo sobreescriben `_theta_angles`.

---

## 2. D112 — el signo lo dice el método, y la clave NO es `slide_sign`

`checks._slide_sign` derivaba el sentido de `sign(Σ W·sin α)`, que es la suma de
Bishop. Janbu deriva el suyo de `sign(Σ w_total·tan α)`: el agua embalsada va
dentro de `w_total` y `tan` pondera una base empinada mucho más que `sin`. Con
el signo al revés `m_α` cambia de rama — es la anomalía de v0.1.82, que este
proyecto tiene escrita como «el criterio nunca estuvo mal, se leía en el
espejo», viva en el método de al lado ciento siete versiones.

El alcance va dicho exacto, porque **una ficha que exagera se descuenta
entera**: Bishop, Spencer, GLE, el Ordinario y la familia prescrita derivan el
suyo de `sign(Σ W(1−kv)·sin α)`, y `(1−kv) ≥ 0` es un factor constante no
negativo, que no invierte una suma. Sólo en `kv = 1,0` exacto la suma se anula.
Luego D112 alcanza a `janbu_simplified` y `janbu_corrected`, y a nada más.

**La clave es `m_alpha_sign` y no `slide_sign`, y no es cosmética.** Para la
familia de inclinación prescrita `slide_sign` **no** es el signo con el que
marchó su denominador, y la trampa va al revés de lo intuitivo: con
`alpha_n = orient·α` y `theta_n = orient·θ`, lo que `_march` forma es, de vuelta
al marco verdadero,

    D = cos(α − θ) − orient·(tan φ/F)·sin(α − θ)

porque esa familia escribe un **menos** donde Bishop escribe un **más**. Así que
`cos α + s·sin α·tan φ/F` no es una cantidad que esa familia forme **para
ningún** `s`: escribir `slide_sign` habría sido falso y escribir `orient` lo
habría sido del otro lado. Leer `slide_sign` como «el signo del denominador»
habría **recreado D112 dentro del propio diccionario `details`**. Un test lo
ejecuta contra la forma cerrada en vez de dejarlo en una frase.

La publican los cinco métodos cribados; **no** la publican el Ordinario (no
forma ninguno) ni la familia prescrita. Las dos claves se escriben en la **misma
sentencia desde el mismo local**, que es el idioma que D113 dejó: mientras
fueran dos expresiones podían volver a separarse.

`_slide_sign` se renombra a **`_denominator_sign`**. El nombre viejo mentía:
nunca fue el sentido de deslizamiento de nadie, era una re-derivación del de un
método. El respaldo a la suma heredada se queda, y **no por cortesía**: dos
ficheros de test construyen `LEMResult` a mano sin `details`,
`MultiStageDrawdownMethod` construye el suyo como literal y **tira** el del
método interior, y un resultado leído de un `.h5` nunca llevó `details` porque
`to_dict` no lo serializa.

---

## 3. El censo de la regla 6, y lo que dice su MARGEN

`_tools/censo_m_alpha_d111_d112.py`, **SOLO MIDE**, corrido contra los dos
árboles. El medidor no llama a `base_m_alphas`, ni a `_denominator_sign`, ni a
`m_alpha_check` —hoy devolverían una cosa y mañana otra—, y la pertenencia a la
familia prescrita **se interroga al registro**, no se teclea.

**D111 — 37 filas, 15 INMÓVILES POR IDENTIDAD, 22 corridas, CERO se mueven.**
El cambio sólo **afloja**, así que una fila con `inadmisibles == 0` no tiene
nada que devolver: eso es identidad y no muestreo. Y el atajo que permite medir
las 22 con **una sola pasada** —el cribado marca `admissible` in situ y
`_analyse` descarta el valor de retorno, luego la generación de una rejilla no
cambia— **no se supuso**: se verificó corriendo además la pasada con el cribado
apagado, y `min(válidas)` del lado ON es el `fos` del lado OFF en las 22.

**Pero el cero tiene margen, y es lo que lo hace decir algo.** La cribada más
floja del problema **023 · modelo_franjas** está a **+0,806 %** de la ganadora
(1,256202 contra 1,246153), con **1860 superficies** que el cribado quitaba.
Esa fila no se mueve, pero no se mueve **por ocho milésimas**, no por un
kilómetro. Las siguientes: 023 a +1,02 %, 098 a +4,72 %, 057 a +10,2 %, 097 a
+10,8 %. Un cero sin esta columna no dice nada — es la lección de D101, D103,
D118, D127 y D129, y el remedio que D155 dejó escrito.

Cuatro filas **no reproducen su archivo**, y las cuatro son `_no_reproduce.json`
escritos por **0.1.97**, que el banco declara no reproducibles: la discrepancia
es anterior a esta tanda y su delta es 0,0 de todos modos. Se declara en vez de
esconderse.

**D112 — 80 filas de Janbu, CERO discrepancias de signo.** El margen
`|Σ| / Σ|·|` de las dos sumas se publica fila a fila, y dos filas caen por
debajo de 0,05. La más baja es **exactamente cero**, y no es un fallo del
medidor: el `modelo_sin_bulones` del **047** es un círculo **simétrico** cuyas
bases van de −11,082° a +11,082°, de modo que las dos sumas valen 1,04e−17.
Es la única fila del banco donde el sentido lo decide el **desempate `>= 0`** y
no una suma — y las dos derivaciones coinciden ahí precisamente porque
comparten ese convenio. Si una usara `> 0`, discreparían.

Seis filas de Janbu **no rebanan** su superficie archivada contra su modelo
(tres del 045, dos del 048, una del 057) y quedan sin medir. Se acota lo que
pueden tapar: **ninguna** está en un problema con lámina embalsada, luego la
única vía de divergencia que les queda es el peso `tan` frente a `sin`, y las
otras 74 filas la ejercen con margen mínimo 0,42 salvo el caso simétrico.

### El A/B, y lo que de verdad demuestra

El censo se corrió contra los **dos árboles** — el lado A contra un `git
worktree` prístino en HEAD, no contra el árbol vivo — y los dos resúmenes
difieren en **tres claves**: `version`, `arbol_medido` y `B_margen_minimo_pct`,
que pasa de **0,806 a None**. La tercera no es inestabilidad de la medida: **es
el cambio mostrándose**, porque sin nada cribado no existe «la cribada más
floja» contra la que medir un margen.

Y el A/B se hace **fila a fila y por predicción**, no por coincidencia: el
`fos_con_D111c` que el censo de 0.1.188 calculó —el mínimo sobre las válidas,
que es lo que `critical` devolvería sin cribado— es **exactamente** el `fos` que
el motor de 0.1.189 publica, en las **22 de 22** filas corridas.

**Y el cambio no es inerte, que es lo otro que hay que demostrar.**
`inadmisibles` cae a cero en 21 filas, desde **1860** en el 023: en total
**4475 evaluaciones de superficie vuelven al conjunto elegible**, y ninguna de
ellas era la ganadora. Un cambio que no moviera nada porque no hiciera nada no
sería una buena noticia, sería un ajuste que no hace nada — la regla 7.

### Por qué NO se paga la re-corrida dirigida

Estaba aprobada cuando la población de candidatas era desconocida. Medida,
ninguna fila mueve su factor, así que lo único que refrescaría la re-corrida es
el contador `inadmisibles` sobre 22 filas, sin tocar un solo número publicado.

Y el coste no es el reloj: `correr_todo.py` re-corre **problemas enteros**, no
métodos sueltos, de modo que también re-correría Bishop, Spencer y GLE de esos
trece problemas —cuyos archivos son de 0.1.173— y metería **once versiones de
deriva de motor ajena** dentro de un changelog que habla de m-alpha. Es el cero
falso de D101, D103, D118, D127 y D129 leído del revés: no un cero que no
significa nada, sino una diferencia que se atribuiría a quien no la causó. El
precedente exacto es D162, que cerró por su segunda rama.

La consecuencia se declara en vez de esconderse: **el `inadmisibles` archivado
de esas 22 filas es anterior a 0.1.189**, y quien lo lea tiene el
`version_ogr` de cada archivo al lado para saberlo.

---

## 4. Lo que se reporta y NO se corrige (regla 6)

- **D167 — los dos chequeos estiman σ sin el sismo vertical que el solver sí
  aplica.** `checks._base_load_and_sigma` llama `slice_forces(s)` con los
  valores por defecto `kh = kv = 0`, mientras el solver la llama
  `slice_forces(s, kh, kv)` y `w_soil = s.weight·(1 − kv)`. Con `kv ≠ 0` los dos
  linearizan la envolvente en tensiones distintas, que es palabra por palabra lo
  que D113 acaba de cerrar un parámetro más arriba. **`kh` no interviene**:
  `w_total` depende de `kv` y del agua, no de `kh`, y decirlo con esa precisión
  es lo que impide que la ficha se lea como más grande de lo que es. **Efecto
  hoy: ninguno, y es identidad** — medidos los 194 `.ogr` vivos, los 194 llevan
  el sismo desactivado. No se corrige aquí porque `checks` recibe un `LEMResult`,
  que no lleva el proyecto: pide el mismo portador que D112 acaba de introducir,
  y hacerlo en la misma tanda fundiría dos atribuciones.

Y dos cosas menores, que van aquí y no a ficha porque no mueven ningún número:
`search._is_admissible` no propaga `m_alpha_limit`, así que el límite es siempre
0,2 venga de donde venga la búsqueda — es un **parámetro** muerto y no un
**ajuste** muerto, porque no existe campo en `AdvancedSettings`, de modo que la
regla 7 no muerde hoy; y la advertencia de que cerrarlo tocaría interfaz y
activaría las reglas 2 y 3.

---

## 5. Dos frases refutadas que seguían vivas

`tests/test_checks_v132.py` conservaba *«Both are OFF by default, matching the
reference»* — la misma frase que `test_m_alpha_notes_v1158.py` prohíbe en
`checks.py` y en `search.py` desde v0.1.158. Sobrevivió treinta y una versiones
**porque aquella guarda nombraba dos archivos del motor y no alcanzaba a los
ficheros de test**, o sea justo al fichero cuyo trabajo entero es proteger este
comportamiento. Se corrige la frase **y se cierra la clase**: la guarda recorre
ahora `tests/*.py`. Ese segundo cambio **sí** discrimina; el primero es prosa y
no discrimina, y se dice.

Y `.claude/skills/geotecnia/SKILL.md` conservaba *«el círculo crítico validado
contra la referencia también lo incumple; es diagnóstico, no criterio de
validez»*, refutada por v0.1.82 —el círculo lo cumple, min m_alpha +0,93— y viva
en una skill que se carga sola.

---

## 6. Los tests

**`tests/test_m_alpha_screening_v1189.py`**, 21 casos en cuatro clases, y
**`tests/test_slide_sign_by_method_v1189.py`**, 18 en seis. Ninguno de los 39
fija un factor de seguridad contra una instantánea. Los anclajes son los
recuentos publicados de los dos informes y su identidad contable, la identidad
`n_α ≡ cos α·m_α`, la tabla publicada de James Bay **importada** de
`test_james_bay_v1158` y no re-tecleada, las dos formas cerradas de los techos,
el álgebra de `(1−kv)`, la forma cerrada `m(+1) − m(−1) = 2·sin α·tan φ/F` y un
testigo aritmético de tres dovelas cuyos números se **calculan** en el test.

**La regla 7 se comprueba por las DOS puertas y con su control**: sobre la misma
superficie degenerada, el Ordinario pasa de rechazado a admisible —min m_alpha
−0,6209, o sea que **la medida no cambia y el veredicto sí**— tanto por
`check_surface` como por `BaseSearch._is_admissible`, mientras Spencer sobre esa
misma superficie **sigue** rechazado. Sin ese control los dos primeros casos
pasarían también en un árbol donde el chequeo estuviera simplemente apagado.

**El reparto contra el árbol de 0.1.188 está medido y declarado en cada
cabecera**, y no todas las fallas valen lo mismo — decirlo es el punto. Del
fichero de D111 fallan 7 de 21: cuatro por comportamiento o contenido medido
(las dos puertas de la regla 7, la decisión ausente del docstring, y
`analysis_runner` declarando su propia copia del conjunto) y **tres por ausencia
de un símbolo, que es discriminación débil y va etiquetada**. Del de D112 fallan
5 de 18: dos por comportamiento medido —el chequeo devuelve la misma lista con
los dos signos declarados, y la forma cerrada pide −0,193 donde sale 0,0— y tres
por ausencia.

El testigo de D112 merece su número porque es el defecto entero en tres
dovelas: con (α = −70°, W_suelo = 100, W_agua = 400) y dos dovelas a +20°, la
suma de `checks` da **+248** y la de Janbu **−1010**; con φ = 30° y F = 1,3 la
dovela empinada sale **m_α = −0,0753** con el signo adivinado —rechazada, y
además negativa— y **+0,7594** con el del método. El chequeo informaba de una
dovela perfectamente normal como de resistencia negativa.

---

## 7. Errores propios detectados antes de publicar

1. **Lancé el censo del lado A contra el árbol de 0.1.188 y acto seguido empecé
   a editar ese mismo árbol.** `checks.py` se importa de forma **perezosa**, así
   que la corrida podía haber cargado el `checks.py` nuevo a mitad de camino y
   haber medido un motor mezclado sin que nada lo dijera. Se mató antes de que
   escribiera el JSON. El remedio no es acordarse: el censo acepta `OGR_REPO`, el
   lado A corre contra un **`git worktree` prístino en HEAD** y el resumen declara
   `arbol_medido`. Eso además hace **ejecutable** la promesa que el propio
   docstring del censo hace.
2. **Una predicción mía era falsa, y estaba escrita antes de medir.** Predije que
   el mínimo de Lowe-Karafiath **bajaría** al dejar de cribarse. No baja: no se
   mueve en ninguna de las dos rejillas. Y la razón que di para Fellenius también
   era mala — usé los recuentos de inválidas de la referencia, que son de **su**
   motor, para predecir los del nuestro; Fellenius criba 95 y LK sólo 8, al revés
   de lo que deduje.
3. **Iba a escribir `slide_sign` en la familia de inclinación prescrita**, que
   habría sido falso por la trampa de signo de §2. Lo cazó derivar el
   denominador de `_march` de vuelta al marco verdadero antes de escribir la
   clave, no después.
4. Un nombre de test partido por un salto de línea (sintaxis inválida) y una
   llamada a `_eval_poly` con un argumento que esa función no acepta: el ayudante
   de `test_checks_v132` fija Spencer, y el punto entero era poner **dos**
   métodos sobre **una** superficie.
5. Un `walrus` sin ningún sentido en el censo, escrito de paso y sin efecto.
6. **Un comentario que se destruyó a sí mismo, y lo cazó la suite entera.**
   Escribí en `ordinary.py` que ese método no forma el denominador, «y la
   prueba es que la cadena no aparece en este archivo» — escribiendo la cadena
   en el archivo. `test_the_ordinary_method_gets_no_note_at_all` afirma
   exactamente esa ausencia desde v0.1.158 y se puso roja. El arreglo no es
   debilitar la guarda: el token se deletrea **rodeándolo**, y el comentario
   dice por qué está escrito así, porque si no el siguiente que lo «arregle»
   lo romperá otra vez.
7. **Y la guarda nueva se encontró a sí misma, dos veces.** Recorre
   `tests/*.py` buscando la frase refutada, y su propio código fuente contiene
   la frase; y cuando eso se arregló, seguía encontrando el literal de la
   aserción original, en el mismo fichero. Los dos literales van ahora
   **partidos** (`"Both are OFF by " + "default"`), con la razón escrita al
   lado y un «no los vuelvas a juntar». Una guarda que se delata a sí misma
   denuncia para siempre el archivo en el que vive, y eso la vuelve ruido.

---

## 8. Verificación

- **Suite entera y sin argumentos, sola en la máquina y con el changelog ya
  escrito: 4093/4093, cero fallos, sin banner `FILTERED RUN`.** 0.1.188 traía
  4053; los **+40** son exactamente los 21 de un fichero nuevo, los 18 del otro
  y la guarda ampliada del §5. La cuenta se escribe porque un total que nadie
  cuadra no verifica nada.
- **La primera corrida dio 4091/4093**, y los dos fallos son los errores 6 y 7
  del §7. Se dice en vez de contar sólo la segunda.
- Los dos ficheros nuevos corridos **contra el árbol de 0.1.188** para comprobar
  que discriminan, con el reparto medido escrito en cada cabecera: 7 de 21 y 5
  de 18 fallan allí, y va etiquetado cuáles fallan por comportamiento medido y
  cuáles sólo por la ausencia de un símbolo.
- `verificar_cierres.py D111 D112` → **CUBIERTO POR TEST** las dos. Las dos
  comprobaciones son nuevas, y las dos **endurecen** el criterio escrito en su
  prompt, porque el escrito no discriminaba: el de D111 pedía un `grep` de
  «−112» en `checks.py` que **ya pasaba** desde v0.1.84 por el docstring de
  módulo, y el de D112 pedía la clave «en al menos dos solvers», que **ya
  pasaba** porque Spencer y GLE la escriben desde v0.1.185. Las dos leen ahora
  por **AST**.
- `retirar_cerrados.py --escribir`: 2 secciones retiradas, 2 renglones al
  índice. A mano lo que la herramienta avisa y no hace: **PAQUETES**, la cadena
  tachada de P3 y el paquete de la ficha nueva.
- `auditoria_invariantes.py` a **0 ERROR** (748 hallazgos: 491 AVISO, 257 INFO),
  el mismo perfil que en 0.1.186, 0.1.187 y 0.1.188.
- `generar_comparativa.py` + `balance_evaluaciones.py` contra
  `Evaluaciones/0.1.188`: **559 → 559 filas, las 559 IGUAL, 0 sin pareja.**
- Instantánea `Evaluaciones/0.1.189`, **1682 archivos comprobados byte a byte**.
- Y el contrato «SOLO MIDE» del censo respetado: ni un `resultados*.json`, ni un
  `.ogr`, ni un `referencia.json` tocado. Por eso el reparto de versiones de la
  instantánea es el mismo que el de 0.1.188 — esta tanda **no re-corrió nada**,
  y el §3 dice por qué con el número delante.

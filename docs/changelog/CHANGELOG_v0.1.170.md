# OGR Slip2D v0.1.170

**P-D129 — un rechazo PARCIAL de método deja de ser mudo.**

El encargo pedía que, cuando un análisis estadístico pide varios métodos y
**algunos** no pueden correrse, el usuario deje de ver un método menos y
ninguna señal. Está hecho. Pero la ficha se escribió midiendo **0.1.159**, y
entre medias dos versiones trabajaron sobre este mismo canal: v0.1.164 (D91)
creó `last_statistics_notes` y v0.1.169 (D127) construyó
`_publish_method_losses`. El changelog de aquélla ya lo decía —«D129 queda
cerrada sólo en su mitad probabilística, la que esta versión crea»—, de modo
que **el encargo leído literalmente mandaba reescribir código que ya estaba y
dejaba sin tocar lo que de verdad seguía mudo**.

---

## Lo medido antes de tocar nada (regla 6)

Contra el árbol de 0.1.169, conduciendo `_publish_method_losses` y el `_split`
real de `AnalysisNotesPanel`:

| caso | qué publicaba | grupo del panel |
|---|---|---|
| **A** · método sin ninguna muestra | `bishop_simplified: all 10 samples failed…` | `bishop_simplified` ✓ |
| **B** · método **rechazado** por `_cannot_reevaluate` | `The deterministic critical surface is a composite one… this method was skipped.` | **`Model`** ✗ |
| **C** · dos métodos perdidos | los dos concatenados en **un** string | todo bajo `bishop_simplified` ✗ |

**B es exactamente el caso de la ficha**: el usuario leía «this method was
skipped» sin que nada le dijera **cuál**. La causa no era el canal sino una
incoherencia del motor consigo mismo — `_no_sample_note` prefijaba `"<mid>: "`
y los tres textos de `_cannot_reevaluate` no, o sea una invariante respetada
por dos escritores de cinco. La de **C** era que el roll-up producía un solo
string y `_split` toma sólo el **primer** prefijo de una línea. v0.1.169 cerró
el camino A y dejó B y C intactos porque D127 sólo pasaba por A.

Después del cambio, las mismas tres entradas dan `bishop_simplified`,
`bishop_simplified` y dos líneas con dos grupos distintos.

Otras dos medidas, tomadas ejecutando y no leyendo, porque de ellas depende el
alcance:

- la corrida sana de Ej_1 (n=6, `bishop_simplified` y `janbu_simplified`)
  pierde **cero** muestras y su `mres.notes` está **vacío**;
- una corrida sana de **Overall Slope** trae `mres.notes =
  {'surfaces_tracked': 115}` y **ningún** `warning` (115 y 116 en los dos
  métodos). Eso decide que el aviso por método salga por **lista blanca de la
  clave `warning`** y no en bloque: sacar `mres.notes` entero habría convertido
  un diagnóstico en una nota de **toda** corrida sana, que es la regla 7 con el
  signo cambiado.

---

## Las siete cosas que la ficha da por sentadas y la medición desmiente

1. **Su criterio de cierre ya se cumplía sin tocar nada.** Pide un `grep` de
   `last_statistics_notes` en `main_window.py` «al menos dos líneas: donde se
   escribe y donde el panel lo lee»; había **ocho** antes de empezar, puestas
   por v0.1.164 y v0.1.169. Ese `grep` no puede fallar: es el fantasma del
   presupuesto 210 otra vez, y por eso `d129()` mide por AST y ejecutando, no
   con la comprobación que la ficha escribe.
2. **Su paso 1 estaba hecho** para `run_global_minimum`. Implementado como está
   redactado habría dicho la frase **dos veces**, porque `notes["warning"]` ya
   contiene las líneas por método.
3. **Su paso 1 manda despachar por la forma del diccionario** —«por cada clave
   de `res.notes` que sea un método pedido y no esté en `by_method`»—, que el
   docstring de `_publish_method_losses` llama «literalmente D59». Y aquí es
   además **medible como erróneo**: `run_sensitivity` guarda una clave
   `"variables"` que no es un método, y el panel la habría archivado bajo un
   método fantasma con ese nombre.
4. **Todas sus citas de línea estaban caducadas** el día que se leyó:
   `probabilistic.py:103-104` es un comentario sobre `samples` y no sobre `ok`;
   `:347-354` cae dentro de `_sample_failure`; `main_window.py:1657-1665` ya
   traía el arreglo de D127; `:3041-3061` es hoy `_analysis_notes` /
   `act_analysis_notes`; y `:2967` ya no es donde se rellena
   `last_compute_warnings`. Por eso **nada de este cambio ni de su test se
   localiza por número de línea y todo por nombre de símbolo**.
5. **La salida esperada de su reproducción ya era falsa**: hoy `res.notes`
   trae además la clave `warning`.
6. **El test no es `_v1160` sino `_v1170`** — `_vNNNN` es la versión en que
   ATERRIZA; mismo re-anclaje que d91, d95, d96, d98, d101, d102, d103 y d127.
7. **`d129()` no existía**, aunque el criterio de cierre la cite como escrita,
   igual que D91, D95, D96, D98, D101, D102, D103 y D127. Hoy
   `verificar_cierres.py D129` contestaba `SIN CRITERIO`, que no cierra nada.

Y una que no cambia el trabajo pero sí su forma: **D88 y D89 siguen abiertas y
van detrás de ésta** (paquete P5 frente a P1). D89 dice literalmente «la
interfaz enseña la nota por el canal de P-D129» y D88 va a introducir un
**segundo texto** para la misma clave `notes[mid]`. El canal se ha escrito
**agnóstico al texto** por eso: no lee ninguna frase, sólo la coloca.

---

## El arreglo

### El canal

`ProbabilisticResult` y `SensitivityResult` ganan **`note_lines`**: el mismo
contenido que `notes`, **sin aplastar**, una frase por elemento. Una frase
sobre un método llega prefijada `"<mid>: "` —que es lo que `_split` agrupa— y
una frase de nivel-corrida llega desnuda y cae en «Model». Es una **lista** y
no un dict por método a propósito: una segunda frase sobre el mismo método
(D88) es un elemento más, no un `notes[mid]` pisado. Nadie hace `asdict()` ni
`to_dict()` sobre estas dataclasses —`summary()` enumera campos a mano—, así
que el campo no viaja a ningún `.ogr` ni a ningún JSON.

**`_publish_note(result, key, sentence)`** es el escritor único: concatena en
`notes[key]` —nunca asigna— y añade la frase a `note_lines`. Lo usan los
**diez** sitios que escriben una nota de nivel-corrida. Que la concatenación
sea propiedad del **escritor** y no de cada sitio es el punto: diez sitios
copiando las mismas dos líneas es exactamente cómo el string y la lista dejan
de ser el mismo contenido.

**El prefijo se pone en un solo sitio.** `_no_sample_note` lo pierde y nace
`_method_lines(result, lost)`. Tres razones, y la tercera no es estética:
`notes[mid]` debe seguir siendo el **hecho desnudo** porque `StatisticsWindow`
lo enseña bajo un combo que ya dice el método — si el prefijo viviera en el
almacén, la ventana tendría que quitarlo **parseando**.

**`_publish_method_losses` se reutiliza con la misma firma** y el cuerpo
reordenado: `note_lines.extend(lines)` primero y sin guarda (para que una línea
llegue al panel aunque el roll-up no la publique porque `error` está ocupado);
luego el `warning` si la corrida sobrevivió; si no, `"; ".join(lines + rest)`,
donde **`rest` no clasifica, conserva** — nunca pregunta qué significa una
clave, arrastra lo que otro escribió, y eso es lo que salva `notes["variables"]`
de sensibilidad **sin que esta función sepa que esa clave existe**. El día que
D88 añada otra, `rest` la arrastra sola.

**El `if not lost: return` de la cabecera se ha quitado**, y era obligatorio:
`test_random_variable_target_v1164` tiene un caso de sensibilidad con **todas**
las variables huérfanas y **ningún** método rechazado, que llega con `lost`
vacío y aun así debe producir `error`. Lo que impide que eso se vuelva ruidoso
es la guarda `if joined`, no el `if not lost`: con nada perdido y nada más que
decir no se escribe ninguna clave, que es lo que
`test_nothing_is_said_when_nothing_was_lost` exige.

### La mitad que faltaba: sensibilidad

`run_sensitivity` guardaba el rechazo en `res.notes[mid]` y su único roll-up
era `if not res.by_method …`, o sea **sólo la caída total**. Ahora tiene su
lista `lost` explícita y llama a `_publish_method_losses` **después** del bloque
de variables huérfanas, de modo que la concatenación se lee «frase de D91;
método perdido» — el mismo orden que produce la ruta probabilística, donde
`_stale_variables_stop` corre antes del bucle de métodos.

**Límite declarado en el docstring**, y va en voz alta porque prometer más
cobertura de la que la guarda da es lo que costó dos versiones en v0.1.82-84:
un método que entró en el barrido y salió con **cero puntos válidos** sigue
saliendo de `by_method` sin nota propia. No se arregla aquí porque no hay
reproducción medida, e inventar una frase para un estado que nadie ha visto es
el ajuste-que-no-hace-nada de la regla 7.

### La interfaz

`_compute_statistics` consume el canal por **un solo `extend` por análisis**, y
`notes["warning"]`/`notes["error"]` van **sólo** a la barra de estado, que toma
una línea. Los dos son el mismo contenido, así que volcar ambos habría dicho la
frase dos veces en el caso mixto —una variable huérfana **y** un método
perdido—, que es justo el escenario de D129. De paso cierra la asimetría que
quedaba: la rama de error de sensibilidad no alimentaba el panel y la
probabilística sí, y con un `extend` por análisis y ningún `append` por rama
eso no puede volver. **No se añade ningún sitio de limpieza**, así que el
recuento textual de `test_design_factor_report_gui_v1165` queda intacto por
construcción (3 y 3).

`StatisticsWindow` gana dos piezas, porque son dos defectos. Una **etiqueta
permanente propia** (`lbl_run_notes`), entre la barra de combos y el lienzo, es
decir **fuera de todo lo que `_redraw` reescribe** — no puede compartir
`self.status`, que se reinicia en cada redibujo, y `_redraw` no la menciona en
ninguna línea, que es la única garantía que no se erosiona. Con nada que decir
se oculta, y la ventana de una corrida sana queda píxel a píxel como estaba:
la regla 7 en forma de interfaz. Y `_with_reason(text, mid)`, que pregunta
`notes.get(mid)` **por nombre** —nunca «qué claves no son error ni warning»— y
completa las tres frases genéricas que decían «No probabilistic result for this
method» sin decir por qué. Ése es el caso de Overall Slope, donde el método
perdido **conserva** su entrada y por tanto es seleccionable.

**No se mete el método perdido de Global Minimum en el combo**: `_method_ids`
contesta «qué métodos tienen algo que dibujar», y meter en un selector de
gráficos un método sin gráfico es la ausencia de un resultado vestida de
resultado, que es D20/D127. Lo nombra la etiqueta, que es su sitio.

### Tres cosas más, por decisión del propietario y fuera del encargo

- **El cuarto sitio de v0.1.169.** `interpret_window.reported_minima` seguía en
  `next(iter(prob.by_method))` cuando los otros tres migraron a `reported`. En
  Overall Slope el primer método puede ser el que perdió todas las búsquedas
  —conserva su entrada— y su `global_minima` está vacío: *Show GM Surfaces* no
  dibujaba nada y no lo decía. El de sensibilidad **no se toca**:
  `sens.by_method` sólo contiene métodos con al menos un barrido válido, así que
  es correcto por construcción.
- **La tercera ruta muda.** `if method is None or det is None: continue` era un
  `continue` pelado en `run_global_minimum` y en `run_sensitivity` — el mismo
  defecto por otra puerta, y alcanzable: `build_method` contesta `None` para un
  `method_id` que no está en el registro. **Se reutilizan las palabras que
  v0.1.77 ya publicó** para esta misma precondición en la ruta determinista
  (`analysis_runner`), porque escribir una segunda frase para la misma
  precondición es cómo dos textos acaban contradiciéndose — la lección de
  v0.1.167. `det is None` es otra causa y lleva su propia frase, por el mismo
  motivo que `_sample_failure` distingue una excepción de un fallo declarado.
  `run_overall_slope` **no** necesita esto: no tiene esa guarda, construye la
  búsqueda dentro del bucle y su fallo ya cae en `_search_failure`.
- **El aviso del 20 %, que no leía nadie.** `_publish_method_warnings` saca
  `mres.notes["warning"]` a `note_lines` **y a ningún otro sitio**: `notes` es
  el titular de una línea de la barra de estado y un detalle por método no es un
  titular — y así cada aserción que ya existía sobre `notes` sigue contestando
  lo mismo. Sólo la clave `warning` y sólo para un método **con muestras**
  (`n > 0`); los dos límites son medidos, no aseo: `surfaces_tracked` está en
  toda corrida sana, y un método que lo perdió todo conserva su entrada en
  Overall Slope y ya tiene su línea de pérdida, así que sin el filtro se
  nombraría dos veces por un solo fallo. **La frase y el umbral no se tocan**:
  esta versión abre el canal, no reescribe la nota.

### Regla 2 y regla 3

Una sola clave nueva, `'What this run could not do:'`, con su entrada en
español. Las otras dos que la ventana usa ya estaban en el diccionario. Las
notas nacen en `ogr_core`, que no puede importar `ogr_gui.i18n`: llegan en
inglés y se quedan en inglés, y sólo el marco pasa por `tr()` — el mismo trato
que `_design_factor_notes`. Ninguna cadena nueva llega a `showMessage` sin
`tr()`, así que el presupuesto `_UNWRAPPED_BUDGET_MESSAGES`, que se afirma con
`==` **exacto**, no se mueve. **No hay acción de menú nueva** (regla 3).

---

## El test

`tests/test_partial_method_loss_v1170.py`, **34 casos**. La prueba de que mide
algo es que **contra el árbol de 0.1.169, con sólo este archivo presente,
fallan 26 y pasan 8** — y los 8 son los que deben. Seis son CONSERVACIÓN: el
roll-up de v0.1.154, la valla del canal vacío de v1164, la barra de estado
informando del superviviente, el motor rechazando el composite, una corrida
parcial publicando igualmente su número, y la frase del 20 % palabra por
palabra. Los otros **dos se declaran CONTROL en su propio docstring**, verdes
por los dos lados a propósito, porque guardan contra un error que **este**
diseño puede cometer y no contra el defecto que quita — y un test cuyo
docstring no dice cuál de las dos cosas es se leerá como la que no es.

**La puerta se fabrica por los dos caminos, separados**, porque el banco no
tiene ningún modelo que la dispare —la propia ficha lo dice: el 109 da
`SlipSurface` en los tres métodos, y por eso el aviso nunca se añadió—:
`_cannot_reevaluate` parcheado (la receta de la ficha, que aísla el canal) y la
muesca de v1154 con dos métodos (camino real, sin parchear nada, que demuestra
que el primero no es un artefacto).

**Ninguna aserción fija un factor de seguridad**: lo que se comprueba son
identidades, nombres, recuentos y agrupaciones recalculados aquí.

---

## Verificación

**Suite entera y sin argumentos: 3662/3662.** 0.1.169 traía 3628, y los 34
nuevos son exactamente este archivo de test. Se corrió con el árbol quieto y
sin nada en paralelo, que es la lección que v0.1.169 escribió para sus propias
mediciones.

**Cero dígitos movidos, y DEMOSTRADO y no razonado**, porque este cambio sí
entra en `ogr_core` y ahí el argumento «no hay nada que re-correr» no vale —el
precedente que dejó escrito `d127()`—: las once corridas probabilísticas del
banco re-corridas y comparadas contra `Evaluaciones/0.1.160`.
**189 números comparados, 24 de ellos PF o β, y CERO movidos.** El lote entero
en 2030 s.

Que ese cero sea consecuencia y no suerte lo dice el propio verificador con el
número delante: **0 de 11 corridas pierden una sola muestra**, así que ni el
canal nuevo ni el aviso por método tienen dónde dispararse. Un cero de movidos
sobre un banco que nunca ejercita el camino nuevo dice menos de lo que parece,
y conviene que lo diga la herramienta y no la prosa.

`d129()` se escribió con la forma de `d127()` y `d101()`, y **se comprobó que
DISCRIMINA y no pasa en vacío**: contra el árbol de 0.1.169 contesta
`NO SE SOSTIENE` nombrando la causa (`ProbabilisticResult.note_lines` no
existe). Mide por AST que el canal exista y que la interfaz lo consuma, y mide
la agrupación **ejecutándola** —conduciendo `_publish_method_losses` con una
razón de rechazo real y pasándola por el `_split` de verdad del panel—, porque
eso es lo único que separa la política aplicada de la declarada. Y dice en su
propio docstring que **la comprobación que escribe el criterio de cierre no
mide nada**, para que el próximo que la lea no la tome por evidencia.

---

## Errores propios, detectados antes de publicar

- **La muesca con Spencer de superviviente no era una pérdida parcial.** La
  primera redacción de la puerta real usaba Spencer como el método que
  sobrevive, y medido Spencer pierde **todas** sus muestras en ese modelo por
  su cuenta (`no_lambda_bracket`), de modo que el caso era una caída **total**
  disfrazada de parcial y el test habría pasado por la razón equivocada. Lo
  delataron los cuatro casos que exigen `res.ok`. Se eligieron por medición
  `janbu_simplified` como perdido y `bishop_simplified` como superviviente, y la
  razón queda escrita junto a las constantes.
- **La trampa de las capas de `\`.** El heredoc que insertaba el texto de la
  etiqueta escribió un salto de línea real donde debía ir la secuencia de dos
  caracteres, y el archivo quedó con un literal sin cerrar. Es la misma trampa
  que el proyecto ya tiene documentada; se rehízo construyendo la barra con
  `chr(92)`, sin ningún escape que pueda perderse por el camino.
- **Un comentario histórico que casi se pierde.** Al reescribir
  `_compute_statistics` se retiró el comentario de v0.1.169 que explicaba por
  qué la razón llega al panel — y esa razón **sigue siendo cierta**; lo que
  cambió es la ruta, no la intención. Se devolvió la atribución. No fue un
  `sed`: los siete sitios del número de versión se cambiaron uno a uno con
  guarda de aparición única, precisamente porque `main_window.py` lleva dos
  comentarios `v0.1.169 (D127)` y `probabilistic.py` **doce** apariciones de
  `0.1.169`, todas históricas y ninguna de versión, que una sustitución global
  habría falsificado — el error que v0.1.168 documentó.

---

## Reportado y no corregido (regla 6)

- **En `run_sensitivity`, un método con cero puntos válidos** sigue saliendo de
  `by_method` sin nota propia. Sin reproducción medida; declarado en el
  docstring de la función y en la cabecera del test.
- **`StatisticsWindow` nunca ve una corrida caída del todo**, porque
  `_compute_statistics` sólo guarda el resultado cuando es `ok`. La etiqueta es
  para el caso **parcial**, que es D129; la caída total la llevan la barra de
  estado y el panel de notas. Arreglarlo exigiría pasarle el resultado no-`ok`,
  y `test_an_all_failed_run_prints_the_reason_instead_of_nan` exige
  `w._prob_result is None`.
- **El aviso del 20 % conserva su umbral y su frase**, y los dos umbrales
  siguen siendo distintos a propósito: `> 0.2 * num_samples` en Global Minimum y
  `if ores.failed_samples:` en Overall Slope.
- **`ores.notes["surfaces_tracked"]` sigue sin lector.** Es un recuento de
  diagnóstico, no un aviso, y publicarlo pondría una nota en toda corrida sana.
- **Los dos esquemas incompatibles bajo `ProbabilisticResult.summary()`**
  siguen conviviendo (Global Minimum trae `reliability_index_lognormal` y
  Overall Slope no, y a cambio `distinct_global_minima`), inertes porque nadie
  consume `summary()` en producción.
- **D88 y D89 siguen abiertas**, y esta versión es el canal que la segunda dice
  esperar. Cuando D88 haga simétrico el rechazo cambiará el **texto** de la
  razón; el canal no lo lee, así que no habrá que tocarlo.

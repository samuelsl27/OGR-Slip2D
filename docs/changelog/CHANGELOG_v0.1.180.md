# OGR Slip2D v0.1.180

**Defecto D146.** La ficha decía que la rama de momentos del problema 059 es
**biestable** —dos puntos fijos a 0,9 %—, que g(λ) salta de signo sin cruzar
cero dentro de una horquilla, y que el bucle secante quema `max_iterations` y
devuelve NOT_CONVERGED sin decir que lo que no cierra es λ.

**Los números reproducen bit a bit. El mecanismo no existe.** No hay dos
puntos fijos: hay uno, y lo que la ficha llama el segundo es una **aceptación
prematura** —el defecto D145— vista desde el bucle de λ. Y por tanto **el
síntoma murió en v0.1.179**, que lo cerró sin que nadie se diera cuenta.

Lo que esta versión corrige es la mitad que **no** depende del mecanismo
refutado: esa salida ya no contesta con la razón del lazo de Bishop y Janbu.

---

## 1. Lo primero, porque decide todo lo demás: el guion de la ficha no reproduce

El propio guion de `REPRODÚCELO TÚ MISMO`, sobre el árbol de 0.1.179:

```
fos = 0.5592600533686025   converged = True   iterations = 8   reason = ''
```

No 50 iteraciones, no NOT_CONVERGED. **Converge.**

Con `BRANCH_PAIR_TIGHTEN` y `BRANCH_PAIR_SETTLE` apagados —que reproduce el
motor de 0.1.178 instrucción por instrucción— reproduce **exactamente** lo que
la ficha publicó:

| lo que dice la ficha | lo que se mide con D145 apagado |
|---|---|
| F_m = 0,557124544 / 0,552329138 | idénticos |
| F_f = 0,554749979 en las dos | idéntico |
| g de −2,37e-3 a +2,42e-3 | −2,374565e-3 / +2,420841e-3 |
| λ ≈ 0,5424726690330398 | el salto cae entre `0.54247266903303981` y `0.54247266903303992` |
| 50 iteraciones, \|g\| = 47× la tolerancia | 56 iteraciones (`iterations` cuenta también las muestras), 47,5× |

Apagando **además** `BRANCH_RESCUE` no cambia nada, así que el rescate de
0.1.176 no tiene parte en esto: es D145 y sólo D145.

## 2. La premisa es falsa, y hacen falta tres medidas para decirlo

**(a) Un atractor, no dos.** En ese λ la rama de momentos, arrancada desde
nueve valores de F entre 0,3 y 3,0, cae siempre en 0,557096–0,557239, todas
`converged=True` y **ninguna rescatada**. Los nueve se agrupan a 2,6e-4 unos de
otros, **treinta veces más cerca** de lo que cualquiera está de 0,552329138.
Un mapa con dos atractores manda arranques distintos a límites distintos; éste
no. Lo que esos 2,6e-4 sí son es el residuo de una contracción lenta, que
`test_branch_contraction_v1172` ya mide: una rama parada en un paso de `tol`
se queda a `tol·r/(1−r)` de su raíz.

**(b) El barrido de dobles.** Sobre **trece dobles adyacentes** de λ el motor
que se envía devuelve **un** valor de F_m, en la **pasada 27** los trece. Con
los dos interruptores apagados devuelve **dos**, y el segundo se acepta en la
**pasada 11**. Dieciséis pasadas antes. 0,552329138 no es un punto fijo: es un
iterado que la cadena `step < prev_step < prev_step_2` admitió por accidente
sobre una secuencia alternante, que es literalmente el enunciado de D145.

**(c) El desempate, que es el que cierra el argumento.** Con D145 apagado, el
fallo existe a 5e-5 **y en ninguna otra tolerancia medida**:

| tolerancia | D145 apagado | motor enviado |
|---|---|---|
| 1e-3 | cierra, 0,551719 | cierra, 0,558292 |
| 5e-4 | cierra, 0,552475 | cierra, 0,558965 |
| 1e-4 | cierra, 0,552077 | cierra, 0,559196 |
| **5e-5** | **NO CIERRA** | cierra, 0,559260 |
| 1e-5 | cierra, 0,559351 | cierra, 0,559362 |
| 1e-6 | cierra, 0,559394 | cierra, 0,559396 |
| 1e-7 | cierra, 0,559399 | cierra, 0,559400 |

Dos cosas se leen de esa tabla. La primera: **una discontinuidad de g no se
arregla pidiendo más precisión**, y ésta sí. La segunda, que es la que enseña:
con D145 apagado las tolerancias **flojas** cierran cerca de **0,5523** —el
valor prematuro— y las apretadas cerca de **0,5594**; el 5e-5 es el filo donde
los dos conviven entre dobles adyacentes. La columna de la derecha, en cambio,
camina monótona hacia 0,55940.

## 3. Y el testigo, además, es sintético por partida triple

No es una fila del banco y conviene decirlo antes de que alguien lo lea como
si lo fuera: el banco corre el 059 **con su soporte** y a **1e-4**; la ficha lo
mide sin soporte en memoria y a 5e-5. Y encima lo contamina **D147**: el radio
publicado está redondeado, el arco pasa 0,00145 ft bajo el pie y
`candidate_chords` funde dos masas en 53,4 ft, así que la superficie medida no
es el arco de 12,58 ft de la figura 59.2.

**El criterio de cierre de la ficha es, por tanto, insatisfacible tal como está
escrito**: pide que «el 059 sin soporte a 5e-5 salga con la razón nueva», y ese
caso ya no falla, de modo que la única forma de hacerle decir la razón nueva
sería romperlo. Lo que se comprueba en su lugar es lo que el criterio quería
decir: que cuando esa salida se toma, dice que lo que no cierra es λ.

## 4. El censo, que es lo que autorizó tocar el motor

`_tools/cierre_lambda_d146.py` en el banco, **sólo de medida**, con el molde de
`criterio_rama_d145.py`. Recorre la crítica **archivada** de cada fila y cada
superficie **publicada**, evalúa por `build_search(...).evaluate_surface(...)`
—no por un `SlipCircle` a pelo, que es la lección de v0.1.175— y clasifica la
salida leyendo la **traza de λ que el motor resolvió**, capturada en
`_inner_solve`, no una copia del bucle secante.

**344 filas, 79 problemas, 236 críticas y 108 publicadas, 18 saltadas con su
motivo y 8 descuadradas de control.** Y:

| corrida | filas | no cierran | cuáles |
|---|---|---|---|
| motor enviado | 344 | **0** | — |
| D145 apagado (motor de 0.1.178) | 344 | **1** | **027 spencer**, horquilla colapsada |
| motor enviado, tolerancia forzada a **1e-8** | 344 | **0** | — |

Tres cosas de ahí:

- **el cero es un cero medido**, no un cero de no haber mirado, y el censo lo
  demuestra por el otro lado: con D145 apagado encuentra el colapso. Un censo
  que sólo sabe contestar «cero» no distingue un motor arreglado de un medidor
  roto;
- **el 027 no es el testigo de la ficha**: es una fila de verdad del banco, con
  su superficie archivada y a su propia tolerancia (1e-4), y su
  `resultados.json` **lo escribió 0.1.179**, o sea que el número archivado es
  el que el motor de hoy reproduce. Con D145 apagado da 0,310470 contra los
  0,314136 archivados —un −1,17 %— con la horquilla a 8,0e-14 y el residuo a
  11,6 veces la tolerancia. **D145 también cerró eso**, y no se sabía;
- ni a 1e-8, diez mil veces más apretada que la del banco, aparece una sola
  fila. **La salida está dormida.**

Las 8 descuadradas de control van **con nombre** en el informe y son las mismas
en los dos árboles: no las causa este cambio, las causa que la instantánea del
banco no es homogénea —sus archivos se reparten entre siete versiones de OGR—.
Sin esa tabla, «cero filas no cierran» se leería como una afirmación sobre 344
filas que nadie comprobó que fueran las mismas.

## 5. El cambio

Nueve líneas de lógica, duplicadas en los dos archivos porque el bucle de λ son
~285 líneas gemelas con **dos** diferencias semánticas (`boundary_ratios` y un
`import`). Se escribe dos veces, como D63, D118 y D125; extraer el bucle
compartido es su propia versión con su propio A/B.

- **`base.py`**: `REASON_LAMBDA_NOT_CLOSED = "lambda_not_closed"`, dado de alta
  en `ALL_REASONS`. El nombre dice **lo observable y no el mecanismo**: la
  ficha proponía «g discontinua», y cablear en el motor una premisa que esta
  misma versión refuta es cómo `TestAWedgeWithNoRootSaysSo` pasó dos versiones
  afirmando cosas ciertas bajo un nombre falso;
- **`spencer.py` y `gle.py`**: la salida horquillada no convergida pasa de
  `NOT_CONVERGED_NOTE` —una frase sobre «the factor of safety iteration» que no
  menciona λ— a un mensaje que nombra **el residuo, la anchura a la que quedó
  la horquilla y las iteraciones gastadas**, que son los tres números que
  separan sus cuatro modos de fallo. El residuo se mide sobre el par que
  produce el factor que se devuelve y no sobre `g_lo`, que puede ir un refino
  retrasado;
- **`details`** gana `lambda_bracket_width` y `lambda_tolerance` siempre, y
  `lambda_residual` **sólo cuando no cierra** — `None` cuando sí. Eso no es
  coquetería: por debajo de la tolerancia el residuo no dice nada que
  `lambda_tolerance` no diga ya, y escribir un número ahí convertiría **229
  nulos archivados** del banco en valores sin que haya defecto. Así la clave
  significa lo mismo en las dos salidas del método: presente quiere decir que
  la búsqueda de λ **no cerró una raíz por refinamiento**;
- **`analysis_runner.lambda_fallback_notes`** abre su puerta a esta salida.
  Estaba cerrada tras `if not details.get("lambda_search_fell_back")`, de modo
  que la salida con más que explicar era la única que no narraba nada. Lleva su
  propia frase de apertura, porque la de la reserva sería falsa aquí —**sí** hay
  un λ donde las dos ramas se cruzan; lo que no llegó fue el refinamiento—
  mientras que los tres contadores de debajo significan lo mismo en las dos.

## 6. Por qué ningún número del banco puede moverse, dicho con el argumento y no con un encogimiento de hombros

`is_valid` es `converged and fos is not None and fos > 0 and not error_message`,
y en esta salida `converged` ya era `False`: la superficie **ya estaba vetada**.
Cambia **qué dice**, no **qué vale**. Por eso:

- el factor devuelto es bit a bit el mismo (0,5559372612135651 en el testigo), y
  el test lo fija;
- `validas` / `invalidas` / `inadmisibles` no se mueven, porque `admissible` e
  `is_valid` no se mueven;
- `ejecutar_caso.py` lee `lambda_residual` con `.get()`, así que **ausente** y
  **presente valiendo `None`** son el mismo `null` archivado;
- `lambda_tolerance` sólo lo consume `barrido_tolerancia.py`, no
  `resultados.json`;
- y el comentario de `ejecutar_caso.py` que dice «en la rama CON bracket
  `lambda_residual` no existe» **sigue siendo cierto en su contexto**, que es la
  crítica de una búsqueda: una superficie no convergida lleva `error_message`,
  y `error_message` la excluye de `SearchResult.critical` sin fallback.

Se comprobó además con la medida delante: el banco no archiva recuentos de
razones en ningún `resultados*.json` (`grep` de `reason`: cero), así que el
cambio de etiqueta de `probabilistic._counted_reasons` —que era el único riesgo
real— no toca nada archivado. **El banco NO se re-corre, y es una identidad y
no una omisión.**

## 7. Lo que esta versión NO hace, y sale con número

**El corte temprano no se implementa.** Cuando la horquilla llega al suelo del
doble, cada vuelta restante resuelve dos ramas —hasta 400 pasadas cada una—
para un λ que no se puede mover. Medido en el testigo: de **57 llamadas a
`_inner_solve`, desde la 40 todos los λ están a menos de 1e-12 del último**, o
sea **17 llamadas, el 30 %**, que son trabajo cuyo resultado está demostrado de
antemano. Sale como **D153**, con su prompt largo, en P2. La razón para no
hacerlo aquí es la regla 7 al derecho: sobre el banco el ahorro medido es
**cero**, y eso hay que publicarlo antes que el arreglo; donde puede pesar es en
una búsqueda entera, y eso pide instrumentar una búsqueda, no re-evaluar
críticas archivadas.

## 8. Reportado y NO corregido (regla 6)

- **D153**, el corte temprano de arriba.
- **D154**, encontrado al escribir el test y **me mordió a mí**:
  `Material(pore_pressure="water_table")` guarda la **cadena** sin convertirla,
  toda comparación con `PorePressureType.WATER_TABLE` sale `False` y el talud se
  evalúa **seco**, sin excepción y sin aviso. Sobre este mismo círculo:
  **1,0886090318268722** contra **0,5592600533686025**, un **+94,6 %** con un
  número perfectamente plausible. El cargador de `.ogr` **sí** convierte
  (`PorePressureType(data.get(...))`), así que el banco entero está a salvo y lo
  que falla es el camino en código. Y tiene una segunda mitad peor:
  `Material.to_dict()` hace `self.pore_pressure.value` y **revienta** con
  `AttributeError`, de modo que un proyecto construido así se analiza en
  silencio con el número equivocado y sólo se rompe **al guardarlo**.
- El bucle secante sigue teniendo **cuatro** modos de fallo bajo una sola
  razón; esta versión les da un nombre común y los tres números para
  distinguirlos, pero no los separa en cuatro razones. Que haga falta o no se
  sabrá cuando alguno aparezca vivo: hoy ninguno lo está.
- `iterations` sigue significando dos cosas en las dos salidas de Spencer/GLE
  (`len(samples)` en la reserva; `len(samples)` más las vueltas del secante en
  la horquillada), ya anotado en v0.1.176 §6.5 y que esta versión **publica en
  el mensaje**, con lo que el equívoco pasa de `details` a una frase que lee un
  usuario.

## 9. Errores propios detectados antes de publicar

Ocho, y el segundo habría publicado un cero falso:

1. el censo reventó con `TypeError: unsupported operand type(s) for -:
   'NoneType' and 'NoneType'` porque una rama puede devolver `None` y yo restaba
   sin mirar. Lo cazó ejecutarlo, no leerlo;
2. **el censo dejó de medir justo cuando cambió lo que mide.** Clasificaba
   preguntando `if r.reason == "not_converged"`, así que en cuanto mi propio
   cambio de motor aterrizó contestó `causa=None` y `horquilla_colapsada 0`
   **para la misma fila que minutos antes había clasificado bien**. Un medidor
   que sólo conoce el árbol viejo publica «cero» con la misma cara con que
   publicaría un cero de verdad. Ahora reconoce las dos razones, y la constante
   `RAZONES_NO_CIERRA` dice por qué;
3. escribí `pore_pressure="water_table"` al reconstruir el modelo, obtuve
   1,0886 en vez de 0,5593, y **mi primera hipótesis fue la dirección de
   rotura** — que es falsa y no mueve un dígito. Dos pasos equivocados
   seguidos; el segundo lo cazó ponerla y ver que no cambiaba nada. De ahí sale
   D154;
4. `test_tightening_the_tolerance_undoes_it` leía
   `details["lambda_tolerance"]`, una clave que **esta versión añade**, así que
   un caso que habla del defecto de D145 fallaba contra el árbol viejo por un
   motivo que no tiene nada que ver con lo que mide: discriminación débil
   disfrazada de fuerte. Lo cazó el reparto nombrado, no leer el archivo;
5. un parche por heredoc con `\\n` dentro: la barra doble llega como una sola y
   la sustitución no casó. Es la trampa que AGENTS.md tiene escrita y que volví
   a pisar;
6. el nombre del informe se deriva de la versión **instalada**, así que la
   primera generación salió como `lambda_closure_v1179.md`, antes de subir los
   siete números;
7. tres de las nueve subcadenas que `d146()` busca por AST no casaban: dos por
   **mayúsculas** (`NO other tolerance measured`, `NOT implemented`) y una
   porque la frase **cruzaba un salto de línea**, y una subcadena que cruza un
   salto no puede casar nunca. Vale la pena saberlo antes de escribir la
   siguiente de estas comprobaciones;
8. el informe publicaba «8 descuadradas de control» sin decir cuáles, que en una
   tabla cuya única función es dejar comprobar el denominador es justo lo que no
   se puede hacer. Ahora van con nombre, con el archivado y con el desvío.

## 10. El test

`tests/test_lambda_closure_v1180.py`, **18 casos en siete clases**, y ninguna
aserción fija un factor de seguridad contra un valor de referencia: todo es un
A/B en un proceso, una identidad, un recuento de iteraciones o una comparación
contra un número que el propio archivo calcula.

La fixture se escribe **en código** —siete vértices de perfil, un nivel freático
de 24 y una arena sin cohesión— porque `tests/` no puede alcanzar el banco, y
**reproduce el banco dígito a dígito**: 0,559260053369 contra el modelo del
banco sobre el mismo círculo, las mismas 50 dovelas, la misma masa (x de
−40,75818 a 12,60680) y el mismo Σu·l. Esa comprobación se hizo **antes** de
escribir ninguna aserción.

Contra el árbol de 0.1.179 con sólo este fichero añadido, **fallan 6 y pasan
12**, y el reparto va **nombrado**: cuatro fallan por diferencia medida (la
razón, el mensaje sin λ, la lista de notas vacía y la clave que falta) y **dos
por la ausencia de un símbolo** —la constante y la clave—, que es discriminación
débil y va etiquetada como tal. De los doce que pasan, tres están **hechos para
pasar** (los dos que fijan que el factor no se mueve y el que describe lo que NO
se hizo) y los tres de `TestTheJumpWasAPrematureAcceptance` pasan en los dos
árboles **a propósito**: hablan de quién era el defecto —D145— y no de esta
versión, así que una diferencia ahí significaría que la refutación dejó de
sostenerse.

`REASON_LAMBDA_NOT_CLOSED` se lee con `getattr` y no se importa arriba, también
a propósito: un `ImportError` convertiría los 18 casos en errores de
recolección contra el árbol anterior, y «18 errores» no dice cuáles miden el
cambio.

## 11. El banco y la ficha

`d146()` da **CUBIERTO POR TEST** con las cuatro medidas del molde de
`d144()`/`d145()` —el test por `_cubierto`; las cabeceras **por AST y no por
grep**; EJECUTADO por el medidor nuevo y **por los dos lados**, porque con D145
apagado el caso tiene que volver a fallar con la razón nueva y la causa
`horquilla_colapsada`; y el documento de auditoría de la versión instalada, al
que se le exige que publique el **denominador** y la corrida `sin cambio`—. Se
comprobó que **discrimina**: sin el cambio de motor contesta NO SE SOSTIENE
nombrando la causa, «el motor no tiene `REASON_LAMBDA_NOT_CLOSED`… contesta
`'not_converged'`».

Ficha retirada al índice; podada de P2 **en el markdown y en
`generar_prompts.py`**, que es donde de verdad viven los paquetes; fichas nuevas
D153 (P2) y D154 (P1) con sus prompts largos; el renglón de P2 corregido
**entero**, porque además de tachar D146 había que poner al día su descripción,
que contaba tres defectos abiertos donde ahora son cuatro; serie D movida a
D154, siguiente libre D155; prompts regenerados con salida 0, 44 prompts, 0
fichas cerradas sin prompt y 0 sin paquete; `auditoria_invariantes.py` a **0
ERROR** (748 hallazgos: 491 AVISO, 257 INFO).

## 12. Verificación

- Suite **entera y sin argumentos, 3881/3881 y sin banner `FILTERED RUN`**, en
  24 min 10 s. 0.1.179 traía 3863: los **+18** son exactamente este fichero
  nuevo. Corrida **dos veces en verde y las dos sola**, sin nada más en la
  máquina: la primera (25 min 28 s) cerró el árbol antes de afinar un caso del
  test, y **la que cuenta es la segunda**, sobre el árbol final y con el
  changelog ya escrito, que es lo que `test_version_consistency_v176` exige.
  Este párrafo se escribió después de esa segunda corrida y no la invalida: ese
  test comprueba que el archivo **existe**, no su contenido.
- El fichero nuevo cuesta **3,3 s**: comparte el `GLESystem` entre casos, que es
  lo que AGENTS.md recomienda para no meter un test caro sin darse cuenta.
- Censo del banco por las tres corridas, con su denominador publicado, y con la
  tabla de descuadradas de control **con nombre**.
- `auditoria_invariantes.py` a **0 ERROR** (748 hallazgos: 491 AVISO, 257 INFO);
  prompts regenerados con salida 0, 44 prompts, 0 fichas cerradas sin prompt y 0
  sin paquete.
- Instantánea `Evaluaciones/0.1.180` congelada: **1628 archivos comprobados byte
  a byte**. Y la instantánea **no es homogénea**, que es lo que obliga a publicar
  la versión del lado A en cualquier A/B futuro contra ella: de sus 240 archivos
  de resultados, 12 están congelados por escrito y los otros se reparten entre
  0.1.97 (9), 0.1.147 (1), 0.1.160 (24), 0.1.162 (1), 0.1.163 (2), 0.1.170 (11),
  **0.1.173 (126)**, 0.1.178 (22) y 0.1.179 (42), más 2 sin anotar.
- El banco **no** se re-corre, por la identidad de la sección 6. El reparto de
  arriba es idéntico al de `Evaluaciones/0.1.179`, que es la comprobación de que
  efectivamente no se movió nada.

# OGR Slip2D v0.1.173

**`max_iterations` alcanza los tres bucles que su nombre prometía, y donde no
puede alcanzarlos lo dice.** Ficha D117 del banco, prompt P-D117, paquete P2.

---

## 1. El defecto

Un número, una página de ajustes, y **cinco bucles que no son el mismo bucle**.
`MethodsSettings.max_iterations` (por defecto 50) viaja por `lem_kwargs()` →
`build_method` → `LEMMethod.__init__` y de ahí a:

| método | qué gobernaba el ajuste |
|---|---|
| `bishop_simplified`, `janbu_simplified`, `janbu_corrected` | la iteración sobre F, tal cual |
| `corps_engineers_1`, `corps_engineers_2`, `lowe_karafiath` | la misma, pero con `max(self.max_iterations, 60)` |
| `ordinary_fellenius` | nada: no tiene iteración |
| `spencer`, `gle_morgenstern_price` | **sólo** la secante exterior sobre λ |

En Spencer y GLE el punto fijo que esos dos métodos de verdad resuelven —una
llamada a `interslice.solve_branch` por rama y por λ muestreado— corría con
`MAX_PASSES = 400` y `STALL_PATIENCE = 80`, dos constantes de módulo sin puerta
desde los ajustes. `grep max_iterations ogr_slip2d/interslice.py` daba **cero
líneas**.

Es la regla 7 en su forma más callada: no un control que no hace nada, sino un
control que hace **otra cosa** que la que su nombre dice. Es peor, porque el
usuario no tiene cómo enterarse. El hecho estaba escrito desde v0.1.159 en un
comentario de 27 líneas de `tests/test_convergence_tolerance_v198.py`, es decir
**documentado donde sólo lo lee quien ya lo sabe**.

## 2. Por qué ahora y no antes

La ficha prohibía cablearlo sin P-D118, y con razón: hasta v0.1.171 el tope
interior no era un presupuesto sino el **cerrojo contra el desbordamiento de
`E` y `X`**, y dejar que el usuario lo subiera era exactamente cómo se alcanza
el `ValueError` de `math.fsum`. v0.1.171 (D118) acotó el empuje con
`THRUST_SCALE_LIMIT` y el propio comentario de `MAX_PASSES` registró el relevo:
«`THRUST_SCALE_LIMIT` is the lock now… This constant goes back to being what
its first paragraph says it is: a backstop». El cerrojo que hacía peligroso el
cableado dejó de ser este número.

## 3. El arreglo

**`interslice.branch_budget(max_iterations)`**, dueño único del suelo:

```python
return max(int(max_iterations), MAX_PASSES)
```

`GLESystem` gana un campo `max_passes` —en `__slots__` y **al final** de la
firma, porque los nueve sitios que construyen la clase pasan nueve posicionales
y nombran `tolerance`/`initial_fos`, de modo que añadir al final es el único
sitio donde un argumento nuevo no puede aterrizar en la ranura de otro—;
`states()` se lo pasa a las dos llamadas a `solve_branch`, y `spencer.py` y
`gle.py` le entregan `branch_budget(self.max_iterations)`. El suelo se aplica
**dentro del ayudante y no en los dos sitios**, porque duplicarlo es cómo
divergen.

### El suelo es `MAX_PASSES` y NO una constante nueva

Bajar no es el espejo de subir. Desde v0.1.172 ninguna rama converge antes de
su **tercera** pasada y `STALL_PATIENCE` es 80, así que un presupuesto por
debajo de eso no recortaría una iteración derrochadora: **borraría λ que hoy
son respuesta**. `TestPatienceCannotChangeWhatAlreadyConverged` es la forma
ejecutable de esa promesa y sigue verde. Y un `MAX_PASSES_MIN` al lado de
`MAX_PASSES` serían dos nombres para un número mantenidos iguales por nada más
que la costumbre, de modo que el día que uno se moviera el otro conservaría la
razón que justificaba a los dos.

### Un defecto que el cableado INTRODUCE, y va corregido con él

`GLESystem.branches()` atribuía con `state.passes >= MAX_PASSES`. Eso era
correcto **mientras la constante FUESE el presupuesto**. En cuanto el
presupuesto es configurable, la comparación contesta sobre un número que la
rama nunca tuvo: con 500 pasadas, una rama que se estanca en la 420 se contaría
como «agotó el presupuesto». `n_passes_exhausted` es justamente el contador que
v0.1.159 creó para separar esas dos cosas. Pasa a `>= self.max_passes`.

Medido, la mitad BAJA es la alcanzable y es la que discrimina: con presupuesto
50 las dos ramas del root del plano de 50° gastan sus 50 pasadas y **hoy no se
cuentan**, porque `50 >= 400` es falso.

### El nombre honesto, que hace falta IGUAL

Cablearlo no volvió cierto el nombre por sí solo: el presupuesto está
**acotado por abajo**, así que todo valor en el suelo o por debajo sigue
dejando el bucle interior donde estaba. El rótulo pasa a
`Maximum iterations (scope differs by method):` y el control gana el tooltip
que no tenía, con el censo entero y con el número **interpolado del motor**
(`%d` ← `MAX_PASSES`) para que los dos no puedan separarse.

La clave vieja `'Maximum iterations:'` **se queda viva a propósito**: la
comparten la página Groundwater de ese mismo diálogo y
`transient_stages_dialog.py`, que iteran el solver de filtración y no tienen
nada que ver con Spencer. Renombrar la clave en vez de añadir una les habría
puesto encima una frase sobre Spencer y GLE.

Y una nota en `settings_warnings`, reutilizando el `_LAMBDA_METHODS` que ya
existía, con dos redacciones —por debajo del suelo dice que el bucle interior
conserva sus 400 pasadas; por encima dice a cuántas lo sube—, que es la regla 7
hecha visible.

### `search.py`: el paso 3 de la ficha

`max_passes = 15` pasa a `LMC_MAX_PASSES`. Era un presupuesto de la **búsqueda**
que compartía deletreo con el del solver de ramas, de modo que un `grep` por uno
aterrizaba en el otro. El comentario que lo explica **no escribe el nombre
viejo**, porque un comentario que lo nombra vuelve a ser un acierto de `grep`.

## 4. Las seis cosas que la ficha da por sentadas y la medición desmiente

**4.1. «Siete de los nueve métodos».** Son **seis**, y tres de esos seis llevan
un suelo oculto de 60, así que el valor de serie (50) **tampoco les llega**;
`ordinary_fellenius` no itera en absoluto. El rótulo honesto tenía más que
decir del que la ficha pensaba, y por decisión del propietario lo cubre entero.

**4.2. El caso de regla 7 que propone mediría CERO.** Pide la rama lenta del
plano de 50° en λ = 2,0, «85 → 468 pasadas». Medido sobre el motor que se
publica, esa rama **no pierde su λ por el techo**: se **estanca** en la pasada
85, con techo 400 y con techo 5000 igual, porque quien la ata es
`STALL_PATIENCE` —que la ficha congela— y el 468 es lo que necesitaría con el
estancamiento levantado. Escrito como está redactado, el test habría medido
exactamente nada: la trampa de D101, D103, D118, D127 y D129.

**4.3. El caso que SÍ discrimina, encontrado barriendo.** 24 combinaciones —dos
ángulos de cuña × dos métodos × seis tolerancias de 1e-5 a 1e-10— y **se mueve
una**:

| beta | método | tol | F @ 400 | perdidos | F @ 500 | perdidos |
|---|---|---|---|---|---|---|
| 55 | spencer | 1e-08 | 2,5933015270 | 0 | 2,5933015270 | 0 |
| 55 | spencer | 1e-09 | 2,5933015322 | 0 | 2,5933015322 | 0 |
| **55** | **spencer** | **1e-10** | **2,6321547344** | **1** | **2,5933015319** | **0** |
| 55 | gle | 1e-10 | 2,6085274132 | 0 | 2,6085274132 | 0 |

Las otras 23 son idénticas bit a bit. Y el caso que se mueve es **la firma de
D63 al revés**: a 1e-10 el λ perdido por el techo alejaba la respuesta del
límite al que el mismo solver se asienta a 1e-8 y 1e-9; recuperado, vuelve a
él. Por eso el test lo fija como **identidad** —la distancia a ese límite,
calculado en la misma corrida— y no como una instantánea de 2,59.

**4.4. El banco no puede moverse, y es una IDENTIDAD.** Los **204** `.ogr` vivos
del banco traen `"max_iterations": 50` sin una excepción, así que la expresión
cableada evalúa a `max(50, 400) = 400`: el mismo entero que el defecto de hoy.
No es «medido cero»; es que no hay nada que pueda moverse. Su tolerancia más
apretada es 1e-4, seis décadas por encima de donde el techo empieza a morder.

**4.5. La redacción que propone rompe el panel de notas.**
`analysis_notes_panel._split` toma como grupo el primer token antes de `": "`
cuando no lleva espacios. Medido, `"Spencer/GLE: max_iterations bounds…"` se
archiva bajo un **grupo fantasma** llamado `Spencer/GLE`. Es D129, cerrado tres
versiones atrás. La nota va con sujeto de nivel-modelo y el test la pasa por el
`_split` **de verdad** del panel, no por una copia de su regla.

**4.6. Citas caducadas, y una que no existe.** `gle.py:347`→354,
`spencer.py:269`→276, `solve_branch` en `interslice.py:318`→398, `MAX_PASSES`
186→196, **`GLESystem.states` 697→900**, `methods/base.py:319-330`→312 y 322 (y
el defecto de la base es **75**, no 50). `test_max_iterations_scope_v1160.py`
no existía y el test no es `_v1160` sino **`_v1173`**, porque `_vNNNN` es la
versión en que **ATERRIZA**. Y `d117()` **no existía** pese a que el criterio
de cierre la cita como escrita: la décima vez seguida tras D91, D95, D96, D98,
D101, D102, D103, D127, D129 y D118. Lo único que la ficha acierta al pie de la
letra es `search.py:5447`.

## 5. Lo que se reporta y NO se corrige (regla 6)

- **El efecto del cableado es inalcanzable desde el diálogo.** El spin box de
  tolerancia es `setRange(1e-6, 1.0)` y el techo no muerde hasta ~1e-10; el de
  iteraciones llega a 500. Se alcanza editando el `.ogr` (`MethodsSettings(**data)`
  no acota) o por API, no tecleando en Project Settings. **No se toca ninguno de
  los dos rangos**: mover un control que la ficha no nombra, en la versión que
  arregla otro, es cómo se encadenan los defectos.
- **La mitad ALTA de la atribución queda sin puerta.** El `>= self.max_passes`
  es correcto en los dos sentidos, pero sólo el bajo es alcanzable: **no existe**
  rama de esta cuña que se estanque en [400, 600) —cero en 984 resoluciones
  sobre cinco ángulos, cuatro tolerancias, 41 λ y las dos ramas—. Va dicho en
  el docstring del test, porque prometer más cobertura de la que un cambio da
  es lo que costó dos versiones en v0.1.82-84.
- **`STALL_PATIENCE = 80` sigue siendo el cerrojo que de verdad ata la familia
  lenta**, y el ajuste no lo alcanza. Con λ = 2,0 a 1e-6 la rama muere en la
  pasada 85 con cualquier techo.
- **El suelo de 60 de `modified_swedish.py`** no se mueve: sólo se nombra en el
  tooltip. Cambiarlo movería el número de tres métodos.
- **`report_generator.py`** sigue imprimiendo «Maximum Iterations» en el PDF. Es
  un volcado del ajuste, no una promesa sobre bucles.
- El bloque `#:` de `STALL_PATIENCE` (líneas 97-161 de `interslice.py`) está
  **pegado a la constante equivocada** por una línea en blanco que falta, de
  modo que Sphinx lo adosa a `FALLBACK_RESIDUAL_LIMIT`. Pre-existente y ajeno a
  esta ficha.
- **`settings_warnings` no tiene ni una cadena en español**, y las suyas son
  `f-string`s con valores interpolados, así que el `tr(note)` del punto de uso
  no podría casar ninguna clave aunque existiera. Deuda ya anotada en
  `docs/PENDIENTES.md`; la nota nueva nace en `ogr_slip2d`, que no puede
  importar `ogr_gui.i18n`, y llega en inglés como las otras once.

## 6. Los tests

`tests/test_max_iterations_scope_v1173.py`, **36 casos**, y la prueba de que
miden algo es que contra el árbol de 0.1.172, **con sólo el archivo presente,
FALLAN 19 y PASAN 17** — y los 17 son justo los que deben:

- los **cuatro CONTROL**, declarados como tales en su propio docstring
  (`STALL_PATIENCE`, `MAX_PASSES`, `THRUST_SCALE_LIMIT` y el valor de serie sin
  mover), verdes por los dos lados a propósito porque guardan contra el error
  que *este* diseño podría cometer —comprar el presupuesto configurable
  aflojando los dos cerrojos que viene a relevar— y no contra el defecto que
  quita;
- las **conservaciones**: bajar el ajuste no cuesta un λ, GLE contesta igual, el
  control de filtración no hereda la frase;
- el **censo de código que ya existía**: Ordinary sin iteración, Bishop y Janbu
  con el valor tal cual, los tres con suelo de 60, la partición de los nueve
  contra el registro, y que el ajuste **sigue** acotando la secante de λ (ganó
  un bucle, no cambió uno por otro).

Ninguna aserción fija un factor de seguridad: lo que se comprueba son
identidades, nombres, recuentos y agrupaciones recalculadas allí.

## 7. Errores propios, detectados antes de publicar

**El más instructivo, y lo cazó el propio test.** La primera redacción de la
clase de conservación exigía que el factor fuese **idéntico bit a bit** al bajar
`max_iterations`, y es **falso**: en el plano de 50° a 1e-10, con
`max_iterations = 1` Spencer devuelve 0,9430587540 sin converger y con 10 o más
devuelve 0,9419827600. Lo que se mueve no es el presupuesto interior —que sigue
en 400 y no pierde ningún λ, medido— sino **la secante exterior sobre λ**, el
bucle que el ajuste siempre gobernó. O sea que mi propia aserción cometía
exactamente la confusión entre los dos bucles que esta ficha existe para
deshacer. El test quedó partido en dos: uno que fija que el presupuesto interior
no pierde nada, y otro que **mide** que lo que se mueve es el exterior, con la
historia escrita en su docstring porque equivocarse así es el defecto.

**El parcheador paró dos.** El repositorio **mezcla finales de línea** —los
módulos del motor son LF y los diálogos de la GUI CRLF— y el primer parche del
diálogo no casó ni una vez: convertir el archivo entero habría metido un diff de
mil líneas dentro de uno de tres. El parcheador pasó a traducir el patrón al
final de línea que el archivo ya usa. (Y al comprobarlo después de un
`git stash`, los dos vuelven a LF: `core.autocrlf = true` y en HEAD **ya eran
LF**, así que el CRLF era de la copia de trabajo y no del repositorio.)

**Las capas de escapado, otra vez.** Reescribir el parcheador con un literal de
Python sin `r` convirtió `\r\n` en un salto real y dejó una cadena sin cerrar.
Rehecho con `chr(13)`/`chr(10)` y un heredoc entrecomillado, que es lo que este
proyecto ya tiene documentado como fiable.

**Un número que contaba otra cosa.** «Los 1563 `.ogr` del banco» era falso y
estuvo escrito en el docstring de `branch_budget` y dos veces en este mismo
changelog: `RAIZ.glob("**/*.ogr")` recorre también `Evaluaciones/`, que guarda
una copia de cada modelo por instantánea, de modo que el recuento sumaba siete
archivos históricos por cada uno vivo. **Son 204**, y los 204 traen
`max_iterations = 50`. Lo destapó el propio `d117()` al imprimir «0 de 1767»
después de congelar una instantánea más: un número que sube cuando archivas
algo no está midiendo lo que dice medir. (El mismo error está en el changelog
de v0.1.165, que no se toca.)

**El verificador se equivocaba en el sentido seguro.** `d117()` comprobaba el
tooltip con `dialogo.split("spn_iter")[1][:1200]`, que es el trozo entre la
PRIMERA y la SEGUNDA aparición —doce caracteres— y daba un falso negativo. Un
verificador que falla hacia el lado prudente sigue siendo un verificador que no
mide lo que dice.

**Dos suposiciones sin medir.** El test del control de filtración miraba
`pages[2]` (Groundwater) cuando el spin box vive en `pages[3]`
(`_TransientPage`); y el primer comentario del renombrado de `search.py`
escribía el nombre viejo, reintroduciendo el acierto de `grep` que ese paso
venía justamente a quitar.

## 8. El banco, re-corrido entero

**154 circulares y 37 no circulares, 190 archivos de resultados a 0.1.173.**
Contra la línea base: **15 304 números, 5908 de ellos Spencer o GLE, CERO
movidos**. La comparativa: **559 filas → 559, todas IGUAL, cero sin pareja**.
`verificar_cierres.py D117` da **CUBIERTO POR TEST**, y se comprobó que
**discrimina**: contra el árbol sin el arreglo contesta `NO SE SOSTIENE`
nombrando la causa.

Y el cero es una **identidad**, que es lo que lo separa de un cero afortunado:
`d117()` lo dice con el número delante — **0 de 204** modelos del banco traen un
`max_iterations` capaz de mover el presupuesto, porque todos traen 50 y
`max(50, 400)` es el 400 que el motor ya usaba.

### La línea base hubo que fabricarla, y eso arregla algo más

El criterio de cierre nombra `Evaluaciones/0.1.159`; las ocho fichas anteriores
lo re-anclaron a `0.1.160`. Medido, contra 0.1.160 este cierre veía **609
dígitos movidos y ninguno era suyo**: son el censo de búsqueda que movieron
v0.1.171 (la cota de empuje) y v0.1.172 (el criterio de contracción), cada una
con su A/B publicado. `d118()` resolvió lo suyo declarando a mano el conjunto
que ya difería; enumerar 609 números sería esa misma medicina en dosis de
caballo, y una lista escrita a mano es lo que se queda vieja.

Así que se congeló **`Evaluaciones/0.1.172` con `instantanea.py` ANTES de
re-correr**. De paso tapa el agujero que el propio changelog de v0.1.171 dejó
escrito: el banco no tenía instantánea desde 0.1.160, diez versiones de coste y
de deriva que nadie podía aislar. La instantánea **dice de sí misma** que no es
una corrida homogénea —190 de 240 archivos a 0.1.172— y eso no la invalida como
base: lo que se compara es el estado justo anterior a este cambio, archivo por
archivo, sea cual sea la versión con que se midió cada uno.

### El coste, y lo que no dice

87 circulares en 21 519 s (6,0 h) y 37 no circulares en 12 342 s (3,4 h). Son
~247 s por modelo circular contra los ~262 s que se deducen de v0.1.171, o sea
el mismo orden: con el ruido que AGENTS.md documenta para estas corridas, eso no
dice nada más que eso. Lo que sí cuenta el trabajo añadido es la aritmética: una
llamada a `max()` por sistema y una comparación de atributo en `branches()`,
cero pasadas nuevas mientras el valor esté en el suelo — que es donde está en
los 204 modelos.

### Dos errores propios de esta corrida

**El PC se reinició a mitad.** No costó trabajo porque la instantánea se había
tomado ANTES: era lo único que la corrida podía destruir y no se podía
reconstruir. Sobrevivieron 67 problemas ya re-corridos, verificados contra la
base (4687 números, 0 movidos) antes de reanudar.

**Y al reanudar quité `--forzar` de los DOS lanzadores.** En `correr_todo.py`
eso es correcto y ahorró 67 problemas, porque salta por **versión**
(`if not forzar and previo.get("version_ogr") == hoy: continue`). En
`correr_no_circular.py` salta por **existencia del archivo**
(`if hecho.exists() and not forzar`), de modo que sin la bandera **no hace nada
nunca** — y su resumen, «0 corridos, 37 ya estaban, 0 fallos [0 s]», se lee
exactamente igual que un éxito. Lo destapó el censo de `version_ogr`, no la
salida: los 33 `resultados_no_circular.json` seguían marcando 0.1.172. Es el
tramo que menos se podía saltar, porque ahí vive el otro `math.fsum` que el
presupuesto de ramas alimenta, el de `moment_balance`. Generalizar el
comportamiento de un lanzador al otro sin medirlo es la forma de error que este
proyecto lleva documentando desde D101.

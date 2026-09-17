# OGR Slip2D v0.1.174

**`iterate_steffensen` declara su alcance: el archivo dejaba escrito que se
aplicaba y en seis de los nueve métodos no se aplicaba.** Ficha D115 del banco,
prompt P-D115, paquete P2.

---

## 1. El defecto

Una casilla, encendida de serie, guardada en todos los `.ogr`, y **tres métodos
de nueve que la leen**. `AdvancedSettings.iterate_steffensen` viaja por
`lem_kwargs()` → `build_method` → `LEMMethod.__init__`, que lo guarda en
`self.iterate_steffensen` para los nueve. Seis no vuelven a consultar el
atributo jamás.

No es la regla 7 en su forma habitual —un control que no hace nada—, porque el
control funciona perfectamente donde está cableado. Es la forma callada: **el
archivo afirma algo que el análisis no hizo**, y el usuario no tiene cómo
notarlo. En el banco son **204 de 204** `.ogr` vivos con `iterate_steffensen:
true` y **ninguno** a `false`.

Reportado en el changelog de 0.1.159 §8 y no corregido desde entonces.

## 2. El censo, medido y no leído

A/B con el ajuste a verdadero y a falso, mismo talud, misma superficie, los
nueve métodos, tolerancia 1e-8:

| método | circular | no circular |
|---|---|---|
| `bishop_simplified` | **honra**, 11 → 7 pasadas | **IGNORA**, 24 = 24 bit a bit |
| `janbu_simplified` | **honra**, 11 → 7 | **honra**, 13 → 7 |
| `janbu_corrected` | **honra**, 11 → 7 | honra, por herencia |
| `spencer` | ignora, 9 = 9 | ignora |
| `gle_morgenstern_price` | ignora, 11 = 11 | ignora |
| `lowe_karafiath` | ignora, 21 = 21 | ignora |
| `corps_engineers_1` | ignora, 20 = 20 | ignora |
| `corps_engineers_2` | ignora, 21 = 21 | ignora |
| `ordinary_fellenius` | ignora, 1 pasada | ignora |

Tres razones distintas detrás de los seis, y hacen falta las tres porque «no se
aplica» no es una razón:

- **Spencer y GLE** resuelven el par `(F, X)`, no `F`. Es estructural.
- **Lowe-Karafiath y los dos Corps** *sí* iteran sobre el factor de seguridad
  —20 y 21 pasadas en la medida de arriba— y simplemente **nunca se cablearon**.
  Es el caso más incómodo de los tres, porque ahí Steffensen podría funcionar.
- **Ordinary/Fellenius** no tiene iteración: una pasada y fuera.

## 3. Por qué NO se cablea

Está medido, en 0.1.159, y va escrito aquí para que nadie lo «arregle» después:
el patrón de Bishop copiado literal **empeora** la rama —λ = 1,2269 a 1e-10 pasa
de 171 pasadas a **430**— y a λ = 2,0 **la mata** (`None`), porque el estado de
`solve_branch` no es `F` sino el par `(F, X)` y extrapolar `F` deja `X` atrás.
Extrapolando el par junto se gana **1,4–1,6×** y mueve **8 de 8** números a la
tolerancia de serie (ACADS 1(c) Spencer a 5e-3: +0,200 %).

O sea que el cierre no es cablearlo, es decir el alcance. Cablearlo es su propia
versión, y esta no es.

## 4. El arreglo

Dos mitades, y hacen falta las dos porque contestan preguntas distintas.

**La nota**, `_steffensen_scope_notes` en `analysis_runner.py`, escrita con la
forma de `_max_iterations_scope_notes` de la versión anterior y enganchada al
final de la misma cadena de `extend`. Habla **sólo cuando ningún método de la
corrida honró el ajuste**, que es la condición de regla 7 exacta: «esto no hizo
nada». La regla de alcance vive en `_steffensen_honouring`, un solo dueño, para
que la nota y el test no puedan llevar cada uno su copia.

**El rótulo**, porque la pregunta «¿este ajuste hace algo para los métodos que
he marcado?» se hace *mientras* se marcan, y una nota exige haber corrido un
análisis. La casilla pasa a `Accelerate convergence (Steffensen, scope differs
by method)` y el tooltip lleva el censo entero por familias.

### Por qué la nota calla en la mezcla

La ficha pide la nota «cuando Spencer o GLE están activos con el ajuste
verdadero». Medido contra el banco, esa condición es cierta en **82 de los 91**
modelos que nombran sus métodos, porque el ajuste viene encendido de serie y los
204 lo traen. Una nota que salta en nueve corridas de cada diez es una nota que
nadie lee —es lo que `test_efp_wall_v1122` afirma con `quiet == []`— y es la
doctrina que el docstring de `_max_iterations_scope_notes` había dejado escrita
una versión antes. Con el disparo afilado son **8 de 91**.

### La clave vieja SÍ se renombra, al revés que en v0.1.173

La versión anterior mantuvo viva `'Maximum iterations:'` porque la comparten la
página Groundwater y `transient_stages_dialog.py`, y renombrarla les habría
puesto encima una frase sobre Spencer y GLE. Aquí **no aplica**: `'Accelerate
convergence (Steffensen)'` tenía **un solo** sitio de uso en todo el
repositorio, comprobado, así que se retira con su entrada española en vez de
convivir con la nueva.

El tooltip viejo se **sustituye**, no se amplía. Decía «it needs 7 passes
instead of 19» sin decir de qué método: es una medición sobre Bishop escrita
como propiedad del ajuste, que es exactamente la promesa que el archivo estaba
haciendo. Dejarlo al lado del nuevo serían dos textos que acaban
contradiciéndose, la lección de v0.1.167.

## 5. Las cuatro cosas que la ficha da por sentadas y la medición desmiente

1. **«Spencer y GLE lo ignoran» se queda corta: son SEIS.** Escribir el rótulo
   como pide la ficha —«(Bishop, Janbu)»— habría dejado a Lowe-Karafiath, los
   dos Corps y Ordinary/Fellenius cargando la misma promesa falsa. Es la trampa
   de D117, cuya ficha decía «siete de los nueve» y eran seis.
2. **Bishop sólo lo honra en superficie CIRCULAR.** `_general_moment_fos`, la
   rama que toma una polilínea, relaja al 50 % y no menciona Steffensen: medido,
   24 pasadas con el ajuste encendido y 24 con él apagado, bit a bit. El rótulo
   que propone la ficha afirma de Bishop algo que sólo vale en círculos, y por
   eso la nota pregunta **qué devuelve la búsqueda**.
3. **El censo del banco no es «7 de los 8 medidos»**, que era una muestra de
   2026-09-10. Son **204 de 204** a `true` y **cero** a `false`. Los `modelo.ogr`
   de primer nivel, que es lo que ve el `grep` del prompt, son 91 de 91.
4. **Dos de sus citas estaban caducadas** el día que se leyeron: `bishop.py:602`
   es hoy **604** y `janbu.py:314` es **315**. Por eso nada de este cambio ni de
   su test se localiza por número de línea y todo por nombre de símbolo.

Y una decisión que la ficha no plantea: el **enjambre de partículas** está en
`CIRCULAR_METHODS` y en `NON_CIRCULAR_METHODS`, igual que Auto Refine, pero por
una razón distinta —sus partículas **son** círculos y la polilínea es lo que la
optimización hace de las ganadoras—. Así que en una corrida `particle_swarm` +
no circular Bishop **sí** tiene círculos que acelerar, y la nota calla a
propósito. Una nota ausente cuesta menos que una falsa.

## 6. Los tests

`tests/test_steffensen_scope_v1174.py`, **34 casos**. No `_v1160` como pide el
criterio de cierre: `_vNNNN` es la versión en que el test **aterriza**, el mismo
re-anclaje que documentan `d116()`, `d117()` y `d118()`.

Ninguna aserción fija un factor de seguridad: lo que se comprueba son
identidades, recuentos, agrupaciones y nombres.

**La prueba de que miden algo**: contra el árbol de 0.1.173, con sólo el fichero
presente, **FALLAN 16 y PASAN 18**, y los 18 son justo los que deben —los cinco
de `TestTheSixThatIgnoreItReturnBitForBitTheSame` y los cuatro de
`TestTheThreeThatHonourItStillDo`, que fijan la medición sobre la que **descansa**
la frase nueva y son verdes por los dos lados por construcción; los dos del censo
que preguntan al registro y no a la tupla nueva; los seis que afirman SILENCIO,
que no pueden discriminar en un árbol donde nada habla nunca; y el que comprueba
que la casilla sigue escribiendo el ajuste. Eso va dicho en el docstring del
propio fichero, porque un test que no declara cuál de las dos cosas es se leerá
como la que no es.

## 7. Errores propios, detectados antes de publicar

Seis. Los dos primeros los cazó ejecutar el fichero contra el árbol viejo en vez
de leerlo, y los dos últimos la suite ENTERA — ninguna corrida dirigida los
habría visto, que es para lo que existe la regla de no publicar con una corrida
filtrada:

1. **`test_it_does_not_invent_a_method_in_the_notes_panel` pasaba en vacío.**
   Recorría las notas y afirmaba el grupo de cada una, lo cual en un árbol sin
   nota es un bucle vacío y un tick verde: el test del grupo fantasma no podía
   ver el grupo fantasma. Ahora cuenta las notas que archivó y exige tres.
2. **`test_both_new_strings_are_translated` pasaba por la razón equivocada.**
   Afirmaba que había dos claves de Steffensen y que las dos estaban traducidas
   —y el par **retirado** también eran dos y también estaba traducido—, así que
   era verde en los dos árboles y contestaba una pregunta que nadie hizo. Ahora
   identifica las dos por las palabras que esta versión introduce.
3. **El tooltip nació con un `% (7, 19)`** y un comentario al lado diciendo que
   el censo se interpolaba del motor para que no pudieran separarse. Era falso:
   interpolaba dos literales. El tooltip de `max_iterations` de al lado **sí**
   interpola, porque cita `MAX_PASSES`, que es una constante del motor y puede
   moverse; 7 y 19 son una **medición** sobre un círculo, fijada por
   `test_project_settings_wiring_v174` donde se tomó. Retirado, con la diferencia
   escrita en el código.
4. **El primer caso del diálogo tumbaba el intérprete** con
   `STATUS_STACK_BUFFER_OVERRUN`: construía `ProjectSettingsDialog` sin
   `QApplication` y llamaba a `deleteLater()`, que sin bucle de eventos no se
   ejecuta nunca mientras Qt sigue sujetando el objeto. Rehecho con la forma que
   `test_max_iterations_scope_v1173` ya había fijado —`QApplication.instance() or
   QApplication([])` y el diálogo aparcado en una lista de módulo—, y buscando la
   página **por su rótulo** en `_PAGES` en vez de por el índice 7, que es un
   número que un día empieza a apuntar a Seismic.

5. **El rótulo nuevo rompió el test de v0.1.173**, y lo destapó la suite
   entera y no la dirigida. `test_max_iterations_scope_v1173` recoge sus dos
   claves con `"scope differs" in k`, y la casilla de Steffensen adopta esa
   misma frase **a propósito**, porque es el control hermano de la misma
   página y decir dos cosas distintas para el mismo hecho es cómo dos textos
   acaban contradiciéndose. Así que el filtro pasó a nombrar su propia clave
   —`"Maximum iterations (scope differs"`— en vez de cambiar el rótulo nuevo.
   **No se mueve ninguna aserción**: lo que ese caso comprueba sigue siendo
   exactamente lo mismo, y el filtro estaba infra-especificado desde el día
   que se escribió.
6. **Mi propio fichero dejaba el idioma en español** y hacía fallar
   `test_support_silence_v1155`, que busca `"no notes"` en inglés — la
   regla 5 en el ejemplo con el que está escrita. La causa es que
   `tests/_runner.py` **no implementa `teardown_method`**: medido, cero
   apariciones del nombre. La restauración pasó a un `finally` dentro del
   propio caso, que es lo único que se ejecuta de verdad.

### Y el mismo agujero, en la versión anterior (regla 6: reportado, no corregido)

`test_max_iterations_scope_v1173` tiene el mismo `teardown_method` decorativo
y **también deja el idioma en español**. En su suite pasaba por suerte: algún
fichero entre él y `test_support_silence_v1155` lo devolvía a inglés. Medido,
con su test ya en verde:

```bash
QT_QPA_PLATFORM=offscreen python tests/_runner.py \
    test_max_iterations_scope_v1173.py test_support_silence_v1155.py
# 63/64, falla test_an_empty_run_says_so_rather_than_showing_an_empty_box
```

No se corrige aquí: no lo creó este cambio, y la regla 6 dice que una anomalía
se reporta antes de tocarla. Lo que esta versión sí arregla es que su propio
fichero no dependa de esa suerte.

Además, la entrada española del tooltip retirado quedaba **huérfana** en el
diccionario después del primer parche: no la vio el `grep`, que aterrizaba en el
comentario nuevo que deletrea la clave vieja, sino preguntárselo al diccionario
ejecutándolo. Es la misma distinción que `d117()` y `d118()` hacen al negarse a
tomar un `grep` por evidencia.

Los siete sitios del número de versión se cambiaron **uno a uno con guarda de
aparición única** y no con un `sed`, aunque aquí los siete ficheros traían una
sola aparición de `0.1.173`: es el error que v0.1.168 documentó y que v0.1.169 y
v0.1.170 volvieron a evitar.

## 8. El banco: por qué NO se re-corre, y qué se mide en su lugar

Las tres versiones anteriores re-corrieron el banco entero para **demostrar** el
cero de dígitos movidos, y el precedente de `d127()` dice que «el cambio entra en
`ogr_core`, así que el censo de símbolos no sirve de coartada». Aquí la decisión
es la contraria, por decisión del propietario y con el argumento delante:
**ninguna ruta de cálculo cambia**. El ayudante nuevo construye texto; el `.ogr`
no cambia de esquema; `lem_kwargs()`, `build_method` y los nueve métodos quedan
byte a byte como estaban. Un dígito movido no tiene de dónde salir, y eso es una
identidad y no una medición afortunada —la misma forma del `max(50, 400)` de
v0.1.173, pero más fuerte, porque allí al menos había una expresión nueva en el
camino del solver.

Lo que sí se mide, y cuesta segundos en vez de las ≈15,6 h que cuesta la corrida
completa, va dentro de `d115()`: `settings_warnings` **ejecutado** contra los 204
`.ogr` vivos del banco. Resultado: **cero excepciones** y la nota habla en **32
de 204**. (Sobre los 91 `modelo.ogr` de primer nivel, que es el subconjunto que
ve el `grep` del prompt, son 8; los dos números miden lo mismo con denominadores
distintos y conviene no confundirlos.) Con el aviso que hace falta al lado, y que es el mismo que
`d118()` imprime cuando su censo no se mueve: los 204 traen el ajuste a `true` y
**ninguno** a `false`, así que el banco **nunca ejercita la rama contraria**, y
un cero medido sobre un banco que no pisa el caso dice menos de lo que parece.

Los `.ogr` se cuentan excluyendo `Evaluaciones/`, que guarda una copia por
instantánea: sin ese filtro el recuento sube cada vez que alguien congela una
versión, y un número que cambia cuando archivas algo no mide lo que dice. Es
literalmente el error que `d117()` destapó al imprimir «0 de 1767».

## 9. Lo que se reporta y NO se corrige (regla 6)

1. **`test_project_settings_wiring_v174` construye seis de los nueve métodos.**
   Faltan `LoweKarafiath`, `CorpsOfEngineers1` y `CorpsOfEngineers2`, de modo que
   su guarda contra «una subclase que sobrescribe `__init__` y olvida un
   argumento» —la que existe porque GLE hizo exactamente eso y colgó la suite—
   tiene un agujero de tres clases. Medido: hoy las tres aceptan el argumento. No
   se toca porque la ficha declara ese fichero intocable.
2. Su docstring dice «ALL **five** methods». Caducado: son nueve registrados.
3. **Bishop no acelera nada en superficie no circular** y no lo había escrito
   nadie. Cablear Steffensen a `_general_moment_fos` es trabajo propio, con su
   propia medición, y no se hace aquí.
4. **`iterate_steffensen` no llega al informe PDF ni a `ogr_cli`**, comprobado,
   a diferencia de `max_iterations`, que v0.1.173 dejó reportado volcándose al
   PDF. La promesa falsa vivía sólo en el diálogo y en el `.ogr`, y las dos están
   contestadas.
5. **El campo sigue siendo global en el `.ogr`.** Partirlo por método sería
   cambiar el esquema, y la ficha lo prohíbe: el valor sigue valiendo para los
   tres que lo usan.
6. **`settings_warnings` sigue sin una sola cadena en español.** La nota nace en
   `ogr_slip2d`, que no puede importar `ogr_gui.i18n`, así que llega en inglés
   como las otras doce. Deuda ya anotada en `docs/PENDIENTES.md` y que esta
   versión no agranda ni reduce.

## 10. La suite

Entera y sin argumentos, con el árbol quieto y nada en paralelo:
**3767 / 3767**, en 24,8 min. 0.1.173 traía **3733**, y los **34** nuevos son
este fichero: la resta cuadra exactamente, y se comprueba en vez de suponerse.

Corrida **dos veces en verde**, y la segunda no es ceremonia: entre la primera y
el final hubo un `git stash push`/`pop` para comprobar que `d115()` DISCRIMINA,
y aunque un `stash` devuelve el contenido por construcción, el número que esta
sección publica es la evidencia de publicación. Repetida sobre el árbol
definitivo: 3767/3767 en 24,9 min.

La primera corrida completa dio 3765/3767, y los dos fallos eran míos —la
colisión del rótulo con el filtro de v0.1.173 y la fuga de idioma—. Los dos
están en §7, y ninguna corrida dirigida los habría visto: la selección de la
ficha (`steffensen settings_wiring settings_coverage i18n_coverage`) daba
95/95 con los dos defectos dentro.

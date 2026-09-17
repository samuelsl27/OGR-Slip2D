# OGR Slip2D v0.1.175

**El 0,02 de `FALLBACK_RESIDUAL_LIMIT` dice por fin de dónde viene, y el banco
dice por fin cuánto decide: 41 de 229 filas Spencer/GLE publican un mínimo
encontrado por el camino de reserva.** Ficha D120 del banco, prompt P-D120,
paquete P2.

---

## 1. El defecto

Cuando la búsqueda de λ de Spencer o GLE no encuentra bracket, el método
devuelve la muestra de menor `|F_f − F_m|` y la declara convergida si el
residuo baja de `interslice.FALLBACK_RESIDUAL_LIMIT = 0.02`. Y `converged`
alimenta `LEMResult.is_valid`, que `search.surface_score` puntúa a infinito:
o sea que ese número decide si una superficie **compite por el mínimo global**.

v0.1.159 le puso nombre y dejó medido por qué **no** puede ser la tolerancia.
Lo que no hizo, y es lo que esta versión cierra, son dos cosas: **de dónde sale
el 0,02**, y **cuántos mínimos del banco salen por ahí** — el número que la
ficha pide para decidir si esas superficies deben seguir compitiendo.

## 2. El origen: hay partida de nacimiento y no hay derivación

El `git log -S` que la ficha manda seguir **muere en el primer commit del
repositorio** (v0.1.59, «initial public release»), que es más tarde que el
cambio que busca. La historia continúa fuera de git, en las instantáneas
pre-públicas de `historico/Versiones_Claude_Desktop/`:

| versión | umbral | dónde |
|---|---|---|
| v0.1.1 … v0.1.12 | `converged = abs(best[1]) < 0.01` | `spencer.py` **y** `gle.py` |
| **v0.1.13** (5 may 2026) | **`< 0.02`** | se DUPLICA, en los dos a la vez |
| v0.1.13 … v0.1.174 | `0.02` | sin cambio |

v0.1.13 reescribió Spencer **desde cero** contra Fredlund y Krahn (1977), y GLE
con el mismo backbone. Su `CHANGELOG_v0.1.13.md` documenta esa reescritura bug
a bug —los cuatro defectos de v0.1.12, la rejilla de bracket ampliada a
`[-1.5, +1.5]`, la tabla de validación— y **no menciona el umbral ni una sola
vez**: sus únicas apariciones de `0.01`/`0.02` son una tabla de conversión de
unidades, ajena.

Así que el número **tiene partida de nacimiento y no tiene derivación**. Es un
arrastre de una reescritura, duplicado una vez sin razón registrada. Eso es una
respuesta y no un encogimiento de hombros, porque la alternativa era dejar un
número sin explicar justo donde un número sin explicar cambia qué superficies
existen.

## 3. Tampoco hay ninguna que tomar prestada

La documentación de referencia publica, como parámetros de iteración, el
chequeo de m-alpha (**Whitman y Bailey 1967**), las cotas de λ, el factor de
tanteo inicial, el cambio máximo de F por iteración, un F mínimo y Steffensen.
**Ningún residuo aceptable, de ninguna clase.**

Y su lista publicada de códigos de error **no tiene ninguno para «no hay raíz
de λ»**: el de no convergencia es de la iteración del factor de seguridad, y
una superficie que no se puede resolver simplemente se rechaza. El camino de
reserva es un **tercer estado que esa formulación no tiene**, que es la razón
de fondo de que nada fuera de este archivo pueda decir cuánto debe valer el
número.

*(De paso: la propia referencia etiqueta uno de sus umbrales como arbitrario
—«0.1 is an arbitrary number»—, así que documentar un umbral en vez de
derivarlo tiene precedente publicado.)*

## 4. El censo del banco: 41 de 229

`lambda_search_fell_back` aparecía **cero veces** en el banco, porque
`ejecutar_caso.py` no guardaba esa clave. Ahora la guarda, y el censo existe:
`_tools/auditoria_reserva_lambda.py` → `_auditoria/RESERVA_LAMBDA_<ver>.md`.

**41 de 229** filas Spencer/GLE del banco tienen su superficie crítica resuelta
por el camino de reserva, en **11 problemas** (015, 047, 059, 068, 078, 085,
087, 090, 092, 093, 094). Y las **41 están por debajo de 0,02**, de modo que
las 41 se declaran convergidas y válidas: compiten y ganan **en silencio**. Sus
residuos llegan al propio 0,02 — **200 veces** la tolerancia con que corre el
banco.

Del círculo publicado son **7 de 108**, y sólo el 091 pasa de 0,02 (0,0608), que
es el caso conocido de D125: ése sí sale como rechazo.

### Por qué el censo cuesta minutos y no 13 h

La pregunta es «cuántos MÍNIMOS salen por ahí», y el mínimo ya está guardado:
`metodos.<mid>.superficie` trae la superficie crítica que la búsqueda reportó.
Así que se re-evalúa **una superficie por fila** en vez de repetir la búsqueda.

Con una trampa que costó el primer intento y que va escrita en el propio
script: `resumen_superficie` **no archiva `x_left`/`x_right`**, así que un
`SlipCircle` reconstruido llega sin resolver, y `slice_surface` resuelve un
círculo sin resolver sobre la **primera** masa por la izquierda, que en un
círculo que corta el terreno más de dos veces no es la crítica. Medido sobre el
problema 001: por la puerta desnuda Spencer contesta «all sampled λ diverged» y
por `build_search(...).evaluate_surface(...)` contesta 0,9859018, que es el
número archivado. Es el mismo defecto que `BaseSearch.evaluate_surface`
documenta sobre el problema 27, donde la masa equivocada valía un factor 24.

El control va en la sección 0 del propio informe: **236 filas re-evaluadas, 7
descuadradas por encima del 0,01 % y excluidas del recuento**, y el resto
reproduce el factor archivado. Sin ese control el censo estaría midiendo otra
superficie y no diría nada.

## 5. El contrafactual: qué publicaría el banco si no compitieran

La ficha pide además «en cuántas el mínimo **sin** reserva sería otro», y
propone para ello «una segunda pasada con las superficies de reserva marcadas
inadmisibles». **No hace falta una segunda pasada**, y ahí está el segundo
ahorro: `SearchResult.evaluations` es una lista de `LEMResult` completos que
nadie poda y `search.py` nunca borra `details`, así que el contrafactual se
recalcula post-hoc de la MISMA corrida, con la regla de `SearchResult.critical`
y una condición más (`_tools/contrafactual_reserva_lambda.py`).

Medido sobre **32 filas de ocho problemas** (015, 047, 059, 068, 078, 085
circular, **090 y 093**). Los que faltan —085 no circular, 087, 092 y 094— son
`path` y rejillas con soporte de entre 500 y 1500 s, y se dice cuáles son en vez
de publicar un porcentaje. **090 y 093 sí se midieron a propósito**, porque son
dos de los tres problemas que v0.1.130 nombra y su ausencia habría sido el hueco
que más pesaba:

- **el mínimo se mueve en 24 y no se mueve en 8**, y las 8 quietas son
  exactamente aquellas cuya crítica **no** venía de la reserva: cero dígitos.
  Ése es el control de que lo que cambia es **quién gana**, no cómo se calcula;
- cuando se mueve, se mueve **siempre hacia arriba**, entre **+1,60 %** y
  **+15,02 %**. Es decir: excluirlas publica un factor **menos conservador**;
- y respecto del valor publicado por el manual es un **empate: 8 filas se
  acercan y 9 se alejan** (contando sólo aquellas cuyo publicado es comparable
  con un mínimo global, porque en 085 el manual publica otra cosa y la
  distancia ahí no mide esto).

**Y el par 090 / 093 lo dice mejor que el recuento**: misma familia, mismo
mecanismo, direcciones OPUESTAS. Excluirlas lleva el 090 de **−10,1 % a +1,5 %**
de su factor publicado —y de 0,901 a 1,017, o sea cruzando F = 1— y el 093 de
**+4,3 % a +12,2 %**. Si estos mínimos fuesen un artefacto del camino de
reserva, los dos tendrían que moverse hacia el mismo lado. No lo hacen.

De paso, la escala: en el 090 son **5681 de 16045** superficies válidas las que
salen por la reserva, un 35 %. No es un caso raro de un problema raro.

**Dónde para esta medida**, dicho porque un contrafactual que no declara su
límite se lee como si no lo tuviera: es exacto para `critical`, que es una
elección sobre una lista ya calculada. NO lo es para lo que pasaría si la
reserva pasara a `admissible`, porque `admissible` **no es sólo una
preferencia** — es filtro DURO en `SimulatedAnnealingSearch._steer`, en
`_optimize_each_minimum` y en los contadores. En esas búsquedas el pilotaje
cambiaría la propia lista de evaluaciones, así que lo medido es una **cota**.

## 5 bis. La decisión

**Se quedan compitiendo**, que es la decisión de v0.1.130 — y ahora está
confirmada **con un número delante** en vez de con un argumento.

Lo que el recuento descarta es la lectura contraria, que era plausible: si
esos 41 mínimos fuesen artefactos, excluirlos debería acercar el banco a lo
publicado. **No lo hace** (8 y 9, y el 090 y el 093 en direcciones opuestas).
Lo único que hace con seguridad es subir el mínimo reportado. Un número que no
es raíz resuelta sigue sin serlo, y por eso la nota de
`lambda_fallback_notes` existe desde v0.1.159 y sigue siendo
el sitio donde eso se dice; pero convertirla en veto o en preferencia no está
respaldado por la medición, y sí lo está el riesgo contrario, que es D37/C1.

Ningún cambio de política, por tanto: **ninguna ruta de cálculo se toca en esta
versión**, y el cero de dígitos movidos que publica la sección 4 es una
identidad.

## 6. El bloque `#:` mal pegado, corregido de paso

`STALL_PATIENCE` tenía su bloque `#:` pegado a `FALLBACK_RESIDUAL_LIMIT` por
una línea en blanco que faltaba, de modo que Sphinx adosaba **los dos** bloques
a la constante del 0,02 y `STALL_PATIENCE = 80` se quedaba **sin comentario
ninguno**. Reportado en v0.1.173 y no corregido.

Se corrige aquí y no es aseo: escribir el origen del 0,02 dentro de un bloque
que aterriza en la constante de al lado **es no escribirlo**. El arreglo es
mover cada constante junto a su bloque, y el diff lo dice — **2 inserciones y 2
supresiones**, con cada línea apareciendo el mismo número de veces como `+` y
como `−`: no se movió una palabra de texto.

## 7. Lo que la ficha da por sentado y la medición desmiente

1. **El `git log -S` no llega al origen.** La ficha manda «seguir el `git log
   -S` hasta la versión que lo introdujo y leer su changelog». Ese log muere en
   el primer commit público; la versión que lo introdujo es **anterior** y vive
   fuera de git.
2. **«veinte mil veces la tolerancia de serie» está caducado.** La tolerancia
   de serie es hoy **0,005**, así que el límite es **4 veces** ella, no veinte
   mil; el 20 000 correspondía a 1e-6. Contra la tolerancia con que corre el
   banco (1e-4) son **200 veces**, que es la cifra que el censo publica.
3. **Los residuos que cita están caducados.** Los seis archivos con «leaves
   F_f» dan hoy 0,023 / 0,0561 / 0,0608, no los 0,0204–0,0355 de la ficha ni
   los 0,0515 / 0,0257 que cita D125.
4. **«`ejecutar_caso.py` no guarda `details`» es cierto sólo para las claves de
   λ**: `det` ya se extraía y se usaba para `ky`, `ky_fos` y `newmark_cm`. Eran
   dos líneas, no plumbing nuevo.
5. **`_diagnostico()` ya leía las dos claves** desde D134, con deletreo
   castellano (`lambda_reserva`, `lambda_residuo`), pero sólo lo llama
   `barrido_tolerancia.py` y no está en el camino de la corrida. Por eso el
   banco marcaba cero.
6. **Seis de sus ocho citas de línea estaban caducadas** —`spencer.py:188` cae
   en `samples.append`, `gle.py:277` en `samples.sort`, `spencer.py:204` y
   `gle.py:288` en comentarios, `spencer.py:233-235` en `base_shear_strength` y
   `analysis_runner.py:846` en un mensaje sobre el tipo de superficie—, razón
   por la cual nada de este cambio se localiza por número de línea y todo por
   nombre de símbolo. **`interslice.py:162` SÍ era correcta** el día que se
   leyó, y conviene decirlo en vez de apuntarse un acierto barato: hoy está en
   la 164 porque esta versión movió el bloque.
7. **Su criterio de cierre ya se cumplía en un tercio.** Pide un `grep` de
   «Ej_1» en el comentario, y «Ej_1» vive ahí **desde v0.1.159** — que es
   justamente la versión que dejó el origen sin escribir. Escrito así no puede
   fallar y no mide nada: el fantasma del presupuesto 210 otra vez. Por eso
   `d120()` lo comprueba y **no lo toma por evidencia**, y exige el ORIGEN, que
   es otra cosa.

## 8. Los tests

`tests/test_fallback_origin_v1175.py`, **15 casos**. No `_v1160` como pide el
criterio: `_vNNNN` es la versión en que el test **aterriza**, el mismo
re-anclaje de `d115()`, `d116()`, `d117()` y `d118()`.

**La prueba de que miden algo**: contra el árbol de 0.1.174, con sólo el fichero
presente, **FALLAN 7 y PASAN 8**, y los 8 son justo los que deben — los cuatro
declarados CONTROL (la constante no se mueve, Spencer y GLE siguen comparando
contra ella y no contra la tolerancia, y las dos claves que el censo lee siguen
llamándose igual), más tres conservaciones: la razón de Ej_1 que sujeta el
número desde v0.1.159, el bloque de `MAX_PASSES` que la reordenación podía
haberse llevado por delante, y el par de claves de la rama con bracket.

Ninguna aserción fija un factor de seguridad.

## 9. Errores propios, detectados antes de publicar

1. **El censo medía otra superficie.** La primera versión re-evaluaba la
   superficie archivada con `compute_fos` a pelo, y el problema 001 contestaba
   «all sampled λ diverged» donde el archivo dice 0,985902. No era el
   redondeo —perturbar el radio 1e-6 no lo arregla— sino que `x_left`/`x_right`
   no se archivan y la primera masa no es la crítica. Lo destapó la **columna
   de control**, que existía precisamente para eso; sin ella el censo habría
   publicado un recuento de superficies que nadie evaluó nunca.
2. **`d120()` se apuntaba un acierto falso.** Su docstring afirmaba que la cita
   `interslice.py:162` estaba caducada. Era correcta: está en la 164 porque
   **yo** moví el bloque. Corregido, y de paso se comprobaron las otras siete.
3. **Un caso del test pasaba por la razón equivocada.**
   `test_it_names_the_version_that_doubled_it` comprobaba `"v0.1.13" in bloque`,
   y `v0.1.13` es **subcadena de `v0.1.130`**, que el bloque viejo ya traía al
   citar D37/C1. Pasaba contra 0.1.174 por una colisión de subcadenas. Pasa a
   exigir la frase `v0.1.13 rewrote` y la palabra `DOUBLED`.
4. **El parcheador de `verificar_cierres.py` no casó a la primera**: el archivo
   **mezcla finales de línea** (735 CRLF y 6194 LF), y el guardia `__main__`
   los lleva CRLF con un LF suelto al final. Es la trampa que v0.1.173 dejó
   documentada. Resuelto empalmando contra los bytes reales y comprobando
   después que el recuento de CRLF **no se movió**.
5. **Un contador mal escrito en `d120()`**: `if not [f for f in faltan]` es
   `if not faltan`, que habría callado la línea de la medida (3) siempre que
   algo hubiera fallado antes. Pasa a comparar contra la longitud previa.
6. **La columna nueva reventaba la comparativa entera.** `res_busq` y
   `res_pub` se asignaban dentro de `if r:` y el diccionario de la fila se
   construye **fuera**, así que un problema sin `resultados.json` daba
   `UnboundLocalError` y la generación moría. Las otras cinco variables de esa
   función ya estaban pre-inicializadas justo por eso; la mía no. Lo cazó
   ejecutar `generar_comparativa.py`, no leerlo.
7. **El verificador de «cero dígitos movidos» comparó cero archivos** y dijo
   que todo estaba bien. La instantánea se copió con Bash a `/tmp`, que en Git
   Bash es `C:/Users/.../AppData/Local/Temp`, y el Python de Windows lee `/tmp`
   como otra cosa: `rglob` devolvía una lista vacía y el recuento salía
   `0 movidos` **de 0 comparados**. Un cero que sale de no mirar nada se lee
   exactamente igual que un cero que sale de mirarlo todo, y es la razón de que
   este informe publique siempre el denominador: 2163.
8. **La columna nueva dejó ciego al auditor de invariantes**, y su queja se
   leía como lo contrario de lo que pasaba: `auditoria_invariantes.py` parsea
   la comparativa con `if len(cel) != 13`, así que con catorce columnas **no
   parseaba ni una fila del disco** y publicaba «548 filas nuevas, 0 filas
   viejas» —que se lee como que la comparativa está mal, cuando lo que estaba
   viejo era el lector—. Pasa a `>= 13`: las ocho celdas que lee se indexan
   por la izquierda, así que una columna al final no mueve ninguna, y la
   próxima no volverá a romperlo.
9. **Dos defectos en el informe publicado, los dos de leerlo ya escrito**: un
   `%%` literal —esa línea no pasa por `%`, así que el escape sobraba— y,
   peor, **catorce filas listadas con el motivo `None`**. La tabla existe
   porque «un camino que no hace nada tiene que dejar rastro» (D03i), y una
   fila cuyo motivo es `None` es exactamente un camino sin rastro: el
   ayudante devolvía `(None, None)` cuando `evaluate_surface` no contestaba.
   Ahora dice cuál es la razón.
10. **Bash truncó el primer intento de escribir el censo** (>8 KB, «unexpected
   EOF»), que es un límite ya documentado del entorno; el archivo se escribió
   con la herramienta de escritura y no a trozos.

## 10. Lo que se reporta y NO se corrige (regla 6)

1. **`resumen_superficie` no archiva `x_left`/`x_right`**, y por eso una
   superficie crítica del banco no se puede re-evaluar sin pasar por
   `build_search`. No se toca aquí: cambiar lo que archiva el banco es cambiar
   el esquema de `resultados.json`, y esta ficha sólo añade columnas.
2. **`_diagnostico()` sigue con su deletreo castellano** (`lambda_reserva`,
   `lambda_residuo`) junto a las claves nuevas en inglés. Unificarlo movería lo
   que ya está escrito en `_auditoria/D134_tolerancia/`, que es una medición
   archivada.
3. **Siete filas del censo quedan descuadradas** por encima del 0,01 % al
   re-evaluar su superficie archivada (039, 047, 081, 086). No se cuentan y se
   listan; por qué se descuadran es trabajo propio. Dos de ellas son
   `081/resultados_modelo_1_tol1e-06.json`, que el filtro de archivos no
   descarta porque su marca `tol` **no va al principio del nombre** y el salto
   copiado de `d117()` es `startswith("resultados_tol")`. Se deja así: el
   control ya las aparta, y cambiar el filtro es tocar lo que otras seis
   herramientas entienden por «archivo del banco».
4. **El párrafo de fichas abiertas de `ERRORES_Y_DISCREPANCIAS.md` está
   caducado, y no sólo por D120.** Sigue listando «D115–D118» entre las de
   regla 7 y D120 entre las decisiones, y los cinco están cerrados. Las cuatro
   retiradas anteriores tampoco lo tocaron, así que arreglarlo sólo para el mío
   dejaría el párrafo igual de falso y encima inconsistente con cómo se
   cerraron D115, D116, D117 y D118. Lo que sí se hizo a mano, porque el
   generador lo pide con un aviso, es podar D120 de `PAQUETES` y tachar su
   eslabón en la cadena P2.
5. **La tolerancia de serie (0,005) y la del banco (1e-4) siguen siendo
   distintas**, de modo que «cuántas veces la tolerancia» vale una cosa u otra
   según dónde se mire. Se dice, no se unifica.

## 11. El banco: cero dígitos movidos, demostrado y no razonado

El cambio del motor es **un comentario**, así que la identidad es trivial; pero
el cambio del banco **sí toca el productor de `resultados.json`**, y ahí el
argumento «no hay nada que re-correr» no vale. Se re-corrieron los cinco
problemas baratos donde el camino de reserva decide el mínimo —015, 047, 059,
068 y 078, diez archivos en 451 s— contra una instantánea tomada **antes**:

| medida | resultado |
|---|---|
| archivos comparados | 20 |
| números comparados | **2163** |
| **números movidos** | **0** |
| claves numéricas nuevas | 28, todas `lambda_residual` |
| claves sin pareja | 0 |

Y la comparativa entera, con la columna nueva puesta:
`balance_evaluaciones.py` da **559 → 559, `{'IGUAL': 559}`, sin pareja 0/0**.
La columna se añade **al final** y `marca_reserva` no toca `Estado`, que es lo
que ordena el balance con un `RANGO` cerrado.

Los 173 archivos restantes con Spencer o GLE **no se re-corren**, y es una
decisión y no un descuido: la instrumentación vive en `ejecutar_caso.py`, que
es productor único, así que cada archivo adquiere las dos claves cuando le
toque correrse, y exigir los 183 sería exigir 13 h de corrida para un número
que el censo ya midió por otra vía en minutos. `d120()` lo dice **con el
número delante** —cuántos la llevan y cuántos no— en vez de prometer una
cobertura que no hay.

## 12. La suite

Entera y sin argumentos, con el árbol quieto y **nada en paralelo**:
**3782 / 3782**, en 24,9 min. 0.1.174 traía **3767**, y los **15** nuevos son
este fichero: la resta cuadra exactamente, y se comprueba en vez de suponerse.

Corrida **dos veces en verde**, y la segunda no es ceremonia: entre una y otra
llegaron las cuatro filas de 090 y las cuatro de 093, que cambiaron el
comentario del motor —de «cinco y cinco» a «8 y 9», y con el par de
direcciones opuestas dentro—. Un comentario no puede mover un test, pero dos
ficheros LEEN ese texto (`test_fallback_origin_v1175` y
`test_no_vendor_names_v1160`), así que el árbol que se publica es el que se ha
corrido entero, no el de antes de la última frase.

Y las cuatro puertas del banco, en este orden:

| comprobación | resultado |
|---|---|
| `balance_evaluaciones.py` sobre la comparativa nueva | **559 → 559, `{'IGUAL': 559}`, sin pareja 0/0** |
| instantánea antes/después de los 10 archivos re-corridos | **2163 números, 0 movidos** |
| `auditoria_invariantes.py` | **0 ERROR** (485 AVISO, 256 INFO) |
| `verificar_cierres.py D120` | **CIERRE DOCUMENTAL** |

`d120()` se comprobó además **contra el árbol sin el arreglo**, que es lo único
que separa un verificador de un adorno: contesta **NO SE SOSTIENE** y nombra la
causa —«el bloque `#:` que cae sobre `FALLBACK_RESIDUAL_LIMIT` no habla del
residuo sino de otra constante»—, que es exactamente el defecto que esta
versión quita.

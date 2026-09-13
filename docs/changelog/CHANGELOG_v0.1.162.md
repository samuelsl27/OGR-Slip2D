# OGR Slip2D v0.1.162

**El encargo de P-D98 pedía que un `shear_at` que revienta dejara de
hacerlo en silencio, y está hecho; pero al ir a tocar ese `except` aparece
que no sólo callaba, sino que estaba interceptando la excepción que D94
acababa de inventar una versión antes. El contrato que `docs/plugins.md`
publica desde 0.1.161 —«`force_at` *and* `shear_at` [...] that exception is
the ONLY one the engine catches»— era falso para la mitad que le da
nombre, y un plugin que lo cumplía al pie de la letra recibía justo la
respuesta que el contrato descarta.**

Cierra **D98**. **Cero dígitos movidos**: ni una línea ejecutable de
cálculo, ni una constante, ni un valor por defecto, ni una tolerancia. Las
dos superficies publicadas del problema 50 —el único modelo del banco que
declara cortante— siguen en 1,608451 y 1,407941.

---

## 1. El defecto

`ogr_slip2d/support_integration.py`, dentro del bucle por soporte de
`compute_support_effects`:

```python
            V = 0.0
            if getattr(stype, "SUPPORTS_SHEAR", False):
                try:
                    V = max(0.0, float(stype.shear_at(d_along, L_total)))
                # noqa: BLE001 - a plugin must not kill a run. What
                # this one still swallows whole is P-D98.
                except Exception:
                    V = 0.0
```

El comentario justifica **no morir**, y eso está bien. No justifica **no
decirlo**. Un tipo que declara `SUPPORTS_SHEAR` y cuyo `shear_at` lanza
pierde la mitad de su capacidad declarada y **sigue contribuyendo** con el
axil, de modo que ni siquiera la nota de D62 podía hablar de él: esa nota
cuenta soportes que **no** ponen fuerza en la superficie, y éste pone.

Lo que sale es un factor de seguridad calculado con menos refuerzo del que
el modelo lleva, indistinguible de una respuesta correcta. Es la misma
forma de defecto que D94 un escalón más abajo, y es la razón de que pida
una **séptima razón con frase propia** y no una séptima entrada en la
tabla de seis: todas las de esa tabla completan «el soporte no pone fuerza
en la superficie», y ésta dice lo contrario.

---

## 2. Lo que la ficha da por sentado y la medición desmiente

Cinco cosas, y la tercera es la que cambia el alcance del arreglo.

### 2.1 Ninguna de las dos citas de código apunta ya a código

La ficha sitúa el `except` en `support_integration.py:884-888` y su prompt
largo en `978-983`. Con 0.1.161 el archivo tiene 1338 líneas y el bloque
vive en **1118-1125**. D94 le dejó además un comentario que nombra la
ficha, lo cual es útil y es una trampa a la vez: cualquier comprobación de
cierre que grepee sobre el archivo entero estará midiendo la prosa. Por
eso `d98()` mira el código **despojado de comentarios**, que es la lección
que `d94()` ya escribió en su docstring.

### 2.2 Son CUATRO tipos con cortante, no tres

La ficha nombra `GroutedTieback`, `GroutedTiebackFriction` y `SoilNail`.
Falta **`HelicalAnchor`** (`ogr_core/support/helical_anchor.py:287`), que
declara `SUPPORTS_SHEAR` desde 0.1.124 y tiene el mismo `shear_at` que los
otros tres. El censo correcto ya estaba congelado en
`tests/test_helical_anchor_v1124.py:708-715`, que fija los cuatro por
nombre; la ficha se escribió sin mirarlo. (Sus números de línea para los
otros tres también están ~10 por encima de los reales: 582, 724, 885.)

### 2.3 El `except` no sólo callaba: interceptaba la excepción de D94

Ésta es la que importa. El `except Exception` de `shear_at` está **dentro**
del `try` que D94 abrió en 1060 para envolver el cuerpo entero del bucle.
Como `SupportEvaluationError` hereda de `RuntimeError`, el manejador ancho
la casaba **primero** y la contestaba con `V = 0.0`: nunca llegaba al
manejador por soporte de 1185.

Es decir, la simetría que 0.1.161 dice haber restaurado no era completa.
`force_at` propagaba al manejador nuevo; `shear_at` no. Y `docs/plugins.md`
lleva desde entonces publicando como contrato lo contrario:

> `force_at` **and** `shear_at` answer with a number or raise
> `SupportEvaluationError(support_id, reason)`. Nothing else. That
> exception is the ONLY one the engine catches.

Medido: un tipo cuyo `shear_at` lanza `SupportEvaluationError` daba con
0.1.161 un resultado cuyos `details` eran `{'active_support_ratio': 0.0}`
—sin clave `support_failure` ninguna—, con el soporte dentro del
equilibrio y el aviso inexistente. Un autor de plugin que hiciera
exactamente lo que el documento le dice recibía la única respuesta que el
documento descarta. Por eso el arreglo no es sólo registrar: es **dejar
pasar** la excepción tipada, que es lo que el contrato ya prometía.

### 2.4 Los dígitos del 050 con los que la ficha ancla están caducados

Publica `por_0_0 = 1,608529` y `por_0_-5 = 1,407976`, medidos con 0.1.159.
0.1.160 metió la tolerancia en cada `.ogr` y movió 83 problemas. Los vivos
son **1,608451** y **1,407941**, y coinciden con los de
`Evaluaciones/0.1.160`. Es el mismo re-anclaje que ya hicieron `d94()` y
`d79()` (precedente `d54`), y por lo mismo la línea base de este cierre es
0.1.160 y no la que la ficha nombra.

### 2.5 `d98()` no existe; hay que escribirla

El prompt largo la cita como si estuviera puesta
(`_cubierto("cortante que revienta se declara", ...)`). En
`verificar_cierres.py` —3589 líneas— no hay ni `def d98` ni la cadena
`D98`. Y el nombre de test que fija, `test_support_shear_failure_v1160.py`,
no puede ser: `_vNNNN` es la versión en que el test **aterriza**, 0.1.160
ya tiene el suyo (`test_no_vendor_names_v1160.py`) y esto sale en 0.1.162.
El archivo es `tests/test_support_shear_failure_v1162.py` y `d98()` se
escribe con ese nombre literal, porque `_cubierto` comprueba que el archivo
**existe** y nada más.

Dos correcciones menores más. El prompt dice «los 19 modelos con soporte»
y D94 midió **21 problemas y 36 archivos `.ogr`**. Y su paso 3 manda
registrar un tipo de plugin «dándolo de baja al terminar» por la regla 5,
cuando el patrón del proyecto es **no registrarlo nunca**: se subclasea un
tipo ya registrado y se alcanza por `type_ref`, porque
`tests/test_support_orientation_v1112.py:349` congela el censo del registro
y no existe función de baja. Dar de baja a mano lo que `register_support`
metió es precisamente la fuga que la regla 5 prohíbe.

---

## 3. Lo que se ha hecho

### 3.1 El manejador se parte en dos

```python
            V = 0.0
            if getattr(stype, "SUPPORTS_SHEAR", False):
                try:
                    V = max(0.0, float(stype.shear_at(d_along, L_total)))
                except SupportEvaluationError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    if reasons is not None:
                        reasons.append(
                            (support.id,
                             SUPPORT_SHEAR_FAILED + ":" + type(exc).__name__))
                    V = 0.0
```

El orden **es** el arreglo: Python toma la primera cláusula que case, y
`SupportEvaluationError` es un `RuntimeError`, así que un manejador ancho
puesto delante se la traga exactamente igual que antes. El `re-raise` la
manda al manejador por soporte de D94, que la contesta con
`SUPPORT_NOT_PRICEABLE`, la escribe en `failures` y de ahí en
`details["support_failure"]`.

`V = 0.0` no se mueve para todo lo demás: la política «un plugin no mata
una corrida» se queda tal cual para el cortante. Lo que cambia es el
silencio. Y el `# noqa: BLE001` pasa a la línea que lo necesita; estaba en
un comentario suelto encima, donde no suprimía nada.

La asimetría que queda con `force_at` —donde un bug cualquiera propaga y
revienta la corrida— es deliberada y está escrita en `docs/plugins.md`:
perder un vector perpendicular se recupera y nombrarlo cuesta cero; perder
la capacidad axial no, y un factor calculado sin ella es el del talud
desnudo con ropa de respuesta válida.

### 3.2 La séptima razón, y por qué NO va en la tabla de seis

`SUPPORT_SHEAR_FAILED = "shear_failed"`, con el nombre de la clase de
excepción pegado detrás de dos puntos —`"shear_failed:TypeError"`— porque
«el cortante no se contó» y «el cortante no se contó **porque
`TypeError`**» no son la misma ayuda para quien tiene que arreglar el
plugin.

Es la única de las siete que describe a un soporte que **sí** aporta, así
que `uncontributing_support_notes` la saca de la lista **antes** de contar
nada, la agrupa aparte y le da frase propia:

> 1 support contributed only its axial capacity: shear_at raised
> TypeError, so the shear it declares was not counted. That is a defect in
> the support type rather than a property of the model, and the factor of
> safety is the one for less reinforcement than the model carries.

La nota parcial va la **segunda** cuando hay las dos, porque la primera es
la consecuente —acaba en «this factor of safety is the one for the slope
with no reinforcement at all»— y quien lea una sola línea tiene que haber
leído ésa. El llamador único (`analysis_runner.py:1660`) ya itera la lista
y deduplica, así que devolver dos notas no pidió cablear nada, y el CLI y
el panel de la interfaz las enseñan por el mismo canal de siempre.

**La trampa que esto tenía dentro** y que costó su propio test: el final
de esa función redacta «%d of the %d supports placed put no force». Si se
filtra la razón nueva pero se deja correr la cola, un modelo con un único
soporte que perdió sólo el cortante publica **«0 of the 1 supports placed
put no force»** — una frase sobre nada en absoluto, y peor que la falsa,
porque la falsa al menos se nota. Con `reasons` vacío tras el filtro hay
que devolver la nota parcial y salir.

### 3.3 El docstring del canal, que decía lo contrario

El de `compute_support_effects` prometía «`reasons` [...] for every PLACED
support that ends up contributing nothing» y «nothing at all for a support
that contributes». Las dos frases dejaban de ser ciertas con este cambio,
así que se dice: la séptima razón viaja por el mismo canal describiendo a
un soporte que aporta, el camino caliente sigue sin pagar nada —la rama no
existe para un `shear_at` que contesta— y el lector único sabe sacarla
antes de contar. Un canal con dos contratos y un docstring que sólo cuenta
uno es exactamente cómo se queda obsoleto.

### 3.4 `docs/plugins.md`

Dos párrafos nuevos donde estaba la afirmación falsa: que el contrato
cubre `shear_at` y **no lo cubría** hasta esta versión, con el defecto
nombrado; y que la única asimetría que queda es la de un bug —no de la
excepción tipada— entre las dos mitades, con la frase que el análisis
escribe y el aviso de que sobrevivir no es permiso: un `shear_at` que
lanza es un defecto del tipo, y la frase existe para que se arregle.

---

## 4. Lo que se probó

`tests/test_support_shear_failure_v1162.py`, 18 tests en cinco bloques.
Los tipos de plugin se alcanzan por identidad vía `type_ref` y no tocan el
registro (regla 5).

- **El cortante vale algo** (regla 7). Con `shear_at` sano el factor es
  estrictamente mayor que con `SUPPORTS_SHEAR` cerrado, y el vector
  diferencia entre las dos corridas tiene módulo exactamente
  `shear_capacity / out_of_plane_spacing`. Sin este bloque los otros
  cuatro medirían una cantidad que podía ser cero — que es justo el estado
  del único modelo del banco que declara cortante.

  De paso desmiente una identidad que parecía obvia y es falsa: el
  resultante **no** es `hypot(axil, cortante)`. Con `TANGENT_TO_SLIP` el
  axil sigue la tangente del deslizamiento y el cortante es perpendicular
  al **eje del soporte**, así que no son perpendiculares entre sí y no hay
  Pitágoras que valga entre ellos. Lo que sí es exacto es el vector
  diferencia, y eso es lo que el test ancla.

- **Reventar el cortante cuesta el cortante y nada más.** Con `shear_at`
  lanzando `TypeError` el factor es **bit a bit** el de `SUPPORTS_SHEAR`
  cerrado, y estrictamente mayor que el del talud sin refuerzo — sin esto
  el test anterior también pasaría para un arreglo que tirase el soporte
  entero, que es la respuesta de D94 y la equivocada aquí.

- **Y ahora lo dice.** La razón nombra la clase de excepción, la nota la
  repite, un soporte sano no registra nada, y con un único soporte que
  perdió el cortante la nota **no** puede contener «put no force». Más un
  test que comprueba que la frase nueva no lleva ninguna de las tres
  subcadenas que el banco reserva.

- **El contrato vale para las dos mitades.** `SupportEvaluationError`
  desde `shear_at` pierde el soporte entero, marca `not_priceable` y viaja
  en `details["support_failure"]`.

- **La forma en el código**, gemelo del de D94: comentarios despojados y
  anclado en la **llamada** a `shear_at`, no en «el único `except
  Exception`» —hay un segundo en esa función, el que lee el sentido de
  rotura, y es una anomalía reportada aparte que este test no puede dar
  por inexistente—. Fija que el manejador ancho registra la razón y que el
  tipado va **delante**.

Contra el árbol de 0.1.161 este archivo da **8 pasados y 10 fallados**, y
fallan los correctos: los ocho que pasan son los que describen lo que ya
era cierto —que el cortante mueve el número, que perderlo cuesta el
cortante, que el soporte sigue en el equilibrio y que la corrida no
muere—. Los diez que fallan son los del silencio y los del contrato.

Los quince archivos de soporte y anclaje helicoidal: **309/309**. Suite
entera **3431/3431**, sin argumentos y sobre el árbol que se publica —los
3413 de 0.1.161 más los 18 de este archivo.

### Qué queda sin probar, y se dice

- **El banco no ejercita esto**, y por eso la prueba tiene que ser
  sintética. El 050 lleva catorce `SoilNail` y es el único modelo con
  cortante declarado, pero sus siete tipos de nail traen
  `shear_capacity = 0.0`: su `shear_at` devuelve cero donde cruzan, así
  que parchearlo para que lance no mueve un dígito. Medido en su día con
  0.1.159 y confirmado ahora contra 0.1.160.
- **Los 90 problemas SIN soporte no se re-corren.** Este cambio no puede
  tocarlos —no se entra en el bucle de soportes sin `supports`— pero sus
  `resultados.json` se quedan en 0.1.160 y otras fichas los verán como
  PENDIENTE DE CORRIDA. Los 21 CON soporte sí se han re-corrido, y están
  en el apartado 5.
- **Nada del árbol lanza `SupportEvaluationError` todavía**, ni desde
  `force_at` ni desde `shear_at`. Sigue siendo un contrato para los
  plugins, y lo que demuestra que el camino funciona es el cuarto bloque
  del test.

---

## 5. El banco: cero dígitos movidos, medido

Se re-corrieron los **21 problemas con soporte**: 34 modelos circulares por
`correr_todo.py` (4,1 h), los tres no circulares del 85 y el 86 por
`correr_no_circular.py` (1,0 h) y el 47 por `correr_47.py`, que tiene
herramienta propia porque su superficie es un plano por el pie y
`correr_todo.py` no lo toca a propósito.

- **39 archivos de resultados contra `Evaluaciones/0.1.160`: 1540 números
  presentes en ambos y NINGUNO distinto.** Cero claves perdidas y ningún
  cambio de forma.
- **`balance_evaluaciones.py`: 559 filas → 559, las 559 IGUAL, sin pareja
  0/0.** El banco entero, fila a fila.
- El 91 —quince láminas— clavado en 0,970072 (Bishop), 0,993290 (Spencer)
  y 0,972325 (GLE/M-P), que son los tres que `d94()` tiene escritos.
- Las dos superficies dadas del 50, en 1,608451 y 1,407941.
- `_auditoria/TRACCION_BANCO_0.1.162.md`, regenerado: **idéntico** al de
  0.1.160 salvo el número de versión.

Las únicas 42 claves que 0.1.162 tiene y 0.1.160 no son todas
`traccion_bases` dentro de `circulo_reevaluado`, un campo que
`_tools/ejecutar_caso.py` empezó a escribir después de aquella instantánea:
deriva de esquema del banco, no de este cambio. Se dice porque un recuento
que no distingue «igual» de «no había con qué comparar» es la trampa que
D79 denuncia.

Cierres: **`d98()` CUBIERTO POR TEST**, `d94()` SE SOSTIENE, y D62, D40,
D69 y D71 intactos — los tres últimos son los dueños de las subcadenas que
el banco reserva, y D40 sigue diciendo «dispara en: ninguno».

### La trampa de la propia receta de verificación, y un error que cometió

El bloque «CÓMO VERIFICAR TODO» de la ficha manda
`python _tools/ejecutar_caso.py 02_Slide2_Problema050`, y así se hizo. Esa
herramienta **no hereda `solo_superficie_publicada`**; `correr_todo.py` sí,
y de ahí sale el `--solo-publicado` que su `--listar` anota. El 50 es de los
18 problemas que sólo publican superficies dadas, de modo que la corrida
literal de la ficha le metió una búsqueda completa de cinco métodos en el
expediente y le puso `solo_superficie_publicada: False`.

Ningún dígito publicado se movió por eso —las dos superficies dadas
siguieron en 1,608451 y 1,407941—, pero la FORMA del registro sí cambió, y
`generar_comparativa.py` habría publicado un mínimo para un problema que no
lo pide, que es justo lo que «no todo problema pide el mínimo» advierte.
Detectado comparando contra 0.1.160 por CLAVES y no sólo por valores (45
claves nuevas bajo `/metodos`, todas del 50) y restaurado con
`--solo-publicado`. Queda escrito porque la receta seguirá diciendo lo
mismo la próxima vez.

### D79 deja de sostenerse, y no por este cambio

`verificar_cierres.py D79` sale **NO SE SOSTIENE** con un solo motivo:
«filas marcadas que no tocaba: 085 GLE/M-P». Es exactamente lo que 0.1.161
dejó reportado y no corregido.

La evidencia de que no es de aquí es la fila entera. En `Evaluaciones/0.1.160`:

```
| 85 | ... | circular · activo | GLE/M-P | 1,575 | 2,2092 | — | — | +40,27 % | — | — | alta | DISCREPANCIA |
```

y hoy:

```
| 85 | ... | circular · activo | GLE/M-P | 1,575 | 2,2092 | — | — | +40,27 % | — ⚠ inadmisible | — | alta | DISCREPANCIA |
```

Los mismos cuatro números. Lo único que aparece es la marca, en la columna
del círculo publicado donde 0.1.160 tenía un `—` que significaba **no hay
dato**: el censo con el que D79 estableció «y en ninguna otra» buscaba
`modelo.ogr` y el 85 no tiene `modelo.ogr` sino `modelo_activo.ogr` y
compañía, así que lo dio por limpio por ausencia de medida. Corrido de
verdad, contesta. No se toca: es ficha ajena, y el arreglo es de D79.

---

## 6. Reportado y no corregido (regla 6)

Tres cosas que salen de mirar este bloque y que **no** se tocan aquí.

- **`max(0.0, float(...))` se come dos no-números en silencio.** Un
  `shear_at` que devuelva `NaN` acaba en `V = 0.0`, porque `nan > 0.0` es
  falso y `max` devuelve el primero; y un cortante **negativo** acaba
  igual. Es el patrón que D56 cerró para los factores de seguridad, un
  escalón más abajo y con la misma forma: un no-número que sale de una
  función como si fuera un número. No es el defecto de D98 y pide su
  propia medida.
- **El `try` del sentido de rotura sigue cayendo a `is_l2r = False`** ante
  cualquier excepción, en silencio y **con consecuencia numérica**.
  0.1.161 ya lo dejó escrito; se repite porque vive en la misma función
  que se ha tocado y porque un segundo `except Exception` ahí obligó a
  anclar el test de forma en la llamada y no en el manejador.
- **El prompt de P-D95 queda con una referencia caduca**, y se dice para que
  no engañe a quien lo coja: su lista de «los otros dos `except` del
  archivo» cita «287-290: P-D94; 982-983: P-D98». Las dos posiciones eran ya
  falsas antes de esta versión —el archivo creció con D94— y ahora además
  P-D98 está cerrado. No se edita aquí: es el texto de una ficha ABIERTA y
  ajena, y corregirlo de paso es exactamente cómo se pierde el rastro de
  quién decidió qué. El `except` que P-D95 persigue sigue donde estaba, en
  `_bond_profiles`.
- **`_bond_profiles` sigue ancho y mudo**, y además se llama **fuera** del
  bucle por soporte, así que un `SupportEvaluationError` lanzado desde
  `build_bond_profile` tampoco llega a ningún manejador — el mismo agujero
  que esta versión cierra para `shear_at`, en el tercer `except` del
  archivo. Es P-D95 y no se toca.

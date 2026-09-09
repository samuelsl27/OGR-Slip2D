# OGR Slip2D v0.1.156

Cierra **D07c(b)**, el último de los cuatro apartados que el inventario de
ajustes de v0.1.103 dejó abiertos, y con él **el inventario entero**:
`_KNOWN_UNREAD` de `tests/test_settings_coverage_v1103.py` queda **vacío** por
primera vez desde que existe.

El encargo daba por sabidas dos cosas y las dos resultaron no serlo. Leer la
documentación de la referencia antes de escribir —que es lo que la propia ficha
mandaba hacer, y nadie había hecho en cincuenta versiones— cambió qué arreglo
era el correcto.

---

## 1 · Lo que estaba mal, medido

`SearchSettings.block_multiple_groups` lo escribía y lo leía **sólo el
diálogo**. `build_search` construye la búsqueda con
`num_groups=s_search.block_num_groups` y no consultaba el booleano; en
`ogr_slip2d/` no aparecía ni una vez. Un `.ogr` con

```json
"block_multiple_groups": false,
"block_num_groups": 7
```

corría con **siete** grupos. Medido a través de `build_search` sobre el dique
de cuatro capas de `test_search_inequality_v1118`, 200 candidatas, semilla
20260825:

| `multiple_groups` | `num_groups` | grupos en el motor | mínimo | válidas | vértices |
|---|---|---|---|---|---|
| False | 7 | 7 | 2,070178713 | 14 | 9 |
| True | 7 | 7 | 2,070178713 | 14 | 9 |
| False | 3 | 3 | 1,318449610 | 109 | 5 |
| True | 3 | 3 | 1,318449610 | 109 | 5 |

La casilla **no movía un dígito**. Y el número que decía gobernar se mueve un
**+57 %**, del lado inseguro.

## 2 · Por qué NO se ha elegido el arreglo que el encargo pedía

El encargo ofrecía dos salidas y recomendaba implícitamente la primera: que el
motor pasara `num_groups = 3` cuando el booleano fuera falso, copiando lo que
el diálogo hace. Se descarta, por dos razones, y la primera sale de la
documentación de la referencia.

**El nombre está tomado prestado y el significado no.** Lo que la referencia
llama *Multiple Groups* es una casilla que habilita asignar un **Group ID a
cada objeto de búsqueda que el usuario dibuja**; entonces la búsqueda se corre
**una vez por grupo** y el *Number of Surfaces* **se reparte por igual** entre
ellos (5000 con dos grupos → ~2500 cada uno). El número de grupos **no se
teclea nunca**: emerge de cuántos Group ID distintos haya. En esa documentación
**no existe ningún campo «Number of Groups»**, no se publica valor por defecto,
y **el número tres no aparece en ninguna parte**.

OGR no implementa nada de eso: `BLOCK_SEARCH_OBJECT` no lleva group id, y
`BlockSearch._run` toma un punto de **todos** los objetos dibujados para **una
sola** superficie — que es exactamente el comportamiento *sin* grupos de la
referencia. OGR está permanentemente en «Multiple Groups apagado». Así que
«apagada» no tiene un comportamiento documentado que honrar, y el 3 habría sido
un invento.

Y `block_num_groups` es **otra magnitud**: las bandas verticales con que OGR
tesela una región implícita, leídas **sólo** cuando no hay ningún objeto
dibujado — un apaño que el docstring de `BlockSearch` ya declaraba *«ours, not
the reference's»* desde v0.1.118.

**La segunda razón es peor que la primera**: el arreglo habría sustituido el
defecto por uno mayor. Poner `block_num_groups = 7` desde un script es la única
manera de alcanzar ese control sin diálogo —y es **exactamente** como el banco
escribe los ajustes de bloque en `derivar_no_circular.py`—, de modo que
condicionarlo habría convertido esa asignación en un no-op silencioso salvo que
el script pusiera además un booleano no documentado. Eso invierte el defecto,
no lo cierra.

## 3 · Lo que se hace

**El campo desaparece.** Se registra en `_SHADOW_FIELDS` en el bloque *«Read by
nobody, ever»*, donde ya vivían `block_left_proj_angle_deg` y
`block_right_proj_angle_deg`, que murieron exactamente igual. `from_dict` lo
descarta sin decir palabra —un valor que nunca llegó a un cálculo no tiene nada
que decir— y `_shadow_setting_problems` **rechaza** el análisis si un script lo
asigna como atributo.

**Alcance honesto: cero dígitos movidos.** Un `.ogr` con `false` y `7` corría
siete grupos antes y corre siete después. El cambio quita la contradicción
quitando la mitad que no decía nada, no moviendo un número. Lo que gana es que
el archivo deja de afirmar algo que el análisis no respeta.

### `_SHADOW_FIELDS` pasa a 3-tupla

`(old_default, survivor, version)`. No es adorno: `_shadow_setting_problems`
escribía *«removed in v0.1.103»* para **todas** las entradas, y ya era falso
para `path_optimize`, retirado en **v0.1.104** — su propio comentario, dos
líneas más arriba en el mismo diccionario, dice *«See v0.1.104»*. Un dato que
varía por entrada no puede vivir en la frase que las imprime todas. Con
`block_multiple_groups` habría sido falso por segunda vez, así que la
inexactitud vieja se corrige de camino: el rechazo ya no manda al lector al
changelog equivocado.

### La casilla se va del panel

Con ella se va **una pérdida de datos** que nadie había mirado:
`grid_dialogs.apply()` escribía

```python
s.block_num_groups = (max(1, int(self._b_groups.value()))
                      if self._b_multi.isChecked() else 3)
```

Desmarcar la casilla no dejaba de usar el número: lo **destruía**. Teclear 7,
desmarcar y volver a marcar devolvía 3. El panel de bloque era el único de los
siete que pisaba el valor que su propia casilla protegía; el de Path, dos
bloques más arriba, escribe los suyos planos y deja que `build_search` resuelva
la pareja. Ahora el contador se guarda plano y lleva un tooltip que dice qué
divide de verdad.

### El aviso que faltaba

`block_num_groups` se lee en **una** rama —la que tesela la región implícita— y
esa rama corre **sólo si el modelo no dibuja ningún objeto de búsqueda**. Que
no es un rincón raro: es la **única** disposición que la referencia admite,
porque exige al menos un objeto, y es lo que hacen **los cinco** modelos de
bloque de su banco. El panel enseñaba un número vivo que describe la corrida en
el único caso que la referencia no documenta, y no describe nada en el que sí.

`settings_warnings` gana `_block_group_notes`, que lo dice. Dispara **sea cual
sea el valor**, incluido su 3 por defecto: un tres es tanto una afirmación del
panel como un siete, y el control es igual de inerte bajo los dos. La nota **no
lleva `tr()`**, como ninguna de las del motor, y su redacción esquiva las tres
subcadenas que el banco reserva para decidir si D40 sigue cerrado —«stable»
junto a «head», «edge of the search grid» y «path_optimize»—, con la
prohibición más ancha de lo que parece porque «unstable» contiene «stable» y
«ahead» contiene «head». Hay test que lo comprueba, calcado del de v0.1.155.

### El inventario congelado llega a cero, y se cierra una puerta

`_KNOWN_UNREAD` queda vacío. Y se retira la salida `"UI only"` que v0.1.118
había añadido para permitir exactamente este campo. El argumento entonces fue
que un campo que sólo enciende un widget no le da nada que leer al motor; era
correcto salvo en un punto, y ese punto era el defecto entero: **el campo se
escribía al `.ogr`**. Un campo que llega al archivo tiene que llegar al
análisis o no existir. La propia entrada avisaba de que no era *«an escape
hatch»*; con cero usuarios, una puerta abierta para nadie es la que el
siguiente cruza por error.

## 4 · Lo que se reporta y NO se corrige

- **D99** — OGR no implementa los *Multiple Groups* de la referencia:
  `BLOCK_SEARCH_OBJECT` no lleva Group ID, no hay corrida por grupo y el
  *Number of Surfaces* no se reparte entre ellos. Es una función que falta, no
  un defecto de este encargo. El banco no la ejercita: sus cinco modelos de
  bloque quedarían todos en un grupo.
- **D100** — sin ningún objeto de bloque dibujado, OGR sustituye la decisión
  del usuario por una región implícita propia, con fracciones (0,3 / 0,5 /
  0,05 / 0,75 del *bounding box*) que v0.1.118 dejó declaradas como **no
  calibrables** porque la referencia no ofrece ningún respaldo que las fije. La
  corrida **no es la Block Search de la referencia**, que exige al menos un
  objeto. El docstring lo dice desde v0.1.118; el usuario no lo ve en ninguna
  parte, y ahora que existe `_block_group_notes` el sitio para decírselo está
  escrito.

## 5 · Qué se ha comprobado

- **Suite entera y sin filtrar.**
- **11 de los 17 tests nuevos fallan con 0.1.155**, y los once **por
  comportamiento**: ni un solo `ImportError`. Los seis que pasan son
  precisamente los que anclan que el control vivo —`block_num_groups`— sigue
  llegando al motor desde los ajustes; si el retiro se hubiera llevado por
  delante el control, esos seis serían los únicos que lo notarían.
- **A/B de los cinco modelos de bloque del banco (7, 9, 20, 75, 109)** contra
  el código de 0.1.155, en la misma sesión: **50 valores comparados, 0
  movidos**. El 75 sigue en Bishop **1,6118946113151422** con 3160 válidas y
  Spencer **1,823020669904262** con 2631, que es lo que su
  `resultados_no_circular.json` publica.
  El A/B se hace **contra el código y no regenerando los `resultados*.json`**
  del banco, y es una decisión: están congelados en 0.1.148/0.1.153, así que
  regenerarlos habría mezclado tres versiones de cambios ajenos con éste. Misma
  razón y misma elección que v0.1.155.
- Los cinco modelos ganan **una** nota cada uno, la de `_block_group_notes`, y
  ninguna otra se pierde.
- `tests/test_block_population_v1135.py` y `tests/test_slicer_budget_v1135.py`
  en verde: usan `num_groups` como palanca construyendo `BlockSearch`
  directamente, así que son el control de que el retiro no tocó el motor.

# OGR Slip2D v0.1.167

**El encargo de P-D103 pedía que `act_add_surface` dejara de abrir un
`QMessageBox` modal con seis cadenas sin `tr()`, y está hecho. Pero la
premisa central de la ficha —«un test headless que llame a la acción se
queda bloqueado para siempre», o sea que el daño es de higiene de
tests— está medida y es falsa en la dirección peor: el modal era
alcanzable en la aplicación en marcha. `View → Terminal` (Ctrl+`) entrega
`mainwindow` al intérprete embebido, y `mainwindow.act_add_block_search_object()`
entraba directo en la caja. No era un cuelgue de la suite: era un cuelgue
del usuario.**

Cierra **D103**. **Cero dígitos movidos**, y es consecuencia y no
coincidencia: el cambio vive entero en `ogr_gui/`, no toca una línea
ejecutable de cálculo, ni una constante, ni una tolerancia, ni un valor
por defecto, y ningún `.ogr` del banco llega a una barra de estado. El
banco no se re-corre.

---

## 1. El defecto

`main_window.py:1194-1214` (en 0.1.166):

```python
        s = self.project.settings.search
        if s.search_method != "block":
            # v0.1.166 (D102) - the WORDS follow the action's new name. The
            # box stays MODAL and stays outside tr(): both of those are
            # P-D103 whole, and half-doing them here would leave that
            # ficha's criterion unmeasurable.
            QMessageBox.information(
                self, "Add Block Search Object",
                "This adds a Block Search object (a search window), "
                ...
            )
            return
```

Seis literales sin `tr()` en la caja y dos más en el `showMessage` de la
otra rama. El comentario es de la versión anterior y dice la verdad: el
modal se dejó a propósito, porque medio arreglo habría dejado esta ficha
sin criterio medible. Esta versión lo hace entero.

## 2. Lo que la ficha da por sentado y la medición desmiente

Ocho cosas, y las ocho están medidas en contra.

**(1) `act_add_surface` no existe.** v0.1.166 (D102) la renombró a
`act_add_block_search_object`. El nombre que usa la ficha —y el que
propone para el archivo de test— es la mentira que aquella versión vino a
quitar del rótulo; se re-ancla, y el test se llama
`test_block_search_action_not_modal_v1167.py`.

**(2) El código que cita no es el código.** El prompt transcribe el
bloque de 0.1.159 («Add Surface adds a Block Search object (search
window).»). v0.1.166 reescribió las seis cadenas y el título. Las líneas
tampoco: 1194-1214, no 1174-1183.

**(3) La premisa central, refutada en la dirección peor.** La ficha dice
que sólo un test headless alcanza la caja. El `QAction` está
efectivamente deshabilitado fuera de Block Search
(`refresh_action_availability`, llamado desde `__init__`), así que ningún
ratón la abría — pero `main_window.py:286` hace
`self.terminal_dock.attach_context(self.project, self.canvas, self)` y
`widgets/terminal.py:256` mete `"mainwindow": mainwindow` en el espacio
de nombres del intérprete, que tiene acción propia y atajo `Ctrl+\``.
El defecto no era higiene de tests. Queda fijado en
`test_the_terminal_hands_the_user_the_window`.

**(4) Y de ahí sale lo que cambia el test.** Como la acción está
deshabilitada, `trigger()` **no la ejecuta**: un test escrito con
`trigger()` —que es la forma natural, y la que usa el archivo de
v0.1.166— habría dado **verde contra el defecto**. Por eso este archivo
llama al método directamente, y eso también se mide, en
`test_triggering_a_disabled_action_is_not_a_probe`, en vez de quedarse en
un comentario que nadie puede falsificar.

**(5) Los dos patrones que la ficha propone revientan el escáner.** El de
`QMessageBox` lleva **dos** grupos de captura, y `re.findall` con dos
grupos devuelve **tuplas**: `_unwrapped_count()` llama entonces
`.startswith("%")` sobre una tupla. Medido:
`AttributeError: 'tuple' object has no attribute 'startswith'`. Van con
grupo no capturador, y eso no es estilo; la trampa queda reproducida en
un test para que nadie «simplifique» `(?:` a `(`.

**(6) El criterio de cierre de la ficha es inalcanzable tal como está
escrito.** Pide «el presupuesto de cadenas sin envolver bajado en seis»,
y envolver estas cadenas no mueve el 210 ni un punto, porque ninguno de
los siete patrones `_VISIBLE` las casa — que es literalmente lo que la
propia ficha explica dos párrafos antes. Ya lo dejó apuntado el changelog
de v0.1.166. Manda el criterio del prompt (segundo presupuesto), y la
premisa refutada queda fijada en
`test_the_seven_old_patterns_never_saw_these_two_strings`.

**(7) El presupuesto de 210 es un fantasma.** Medido,
`_unwrapped_count()` devuelve **20**: holgura de 190 contra un
`assert n <= 210` de un solo lado. Es un control que no puede fallar. La
ficha manda copiarle «la misma regla»; se copia la regla de no subir,
**no la holgura** — el presupuesto nuevo se fija en el recuento real.

**(8) Citas menores caducadas.** El aviso no modal de v0.1.125 no está en
2853-2863 sino en 2896-2908, y usa `self.statusBar()` con 15000 ms;
`_info` no está en 2695-2697 sino en 2739-2741;
`test_add_surface_v1166.py` no existe (es
`test_surfaces_menu_labels_v1166.py`); y `d103()` **no existía** aunque el
criterio de cierre la cite como si estuviera escrita, igual que pasó con
D91, D95, D96, D98 y D102.

## 3. El arreglo

El `QMessageBox.information` entero se sustituye por un aviso en la barra
de estado, conservando el `return`. **La cadena no es nueva: es la misma
del tooltip de la rama deshabilitada**, que v0.1.166 ya escribió y
tradujo. Una precondición, un texto.

No es ahorro de traducción, es la decisión de diseño de esta versión.
Escribir una segunda frase para la misma regla es exactamente cómo un
tooltip acaba contradiciendo el rótulo que describe, que es el defecto
que D102 reparó un escalón más arriba; y compartir la clave convierte la
coherencia en algo **comprobable**: la barra de estado y el tooltip salen
de dos rutas de código distintas —`act_add_block_search_object` y
`refresh_action_availability`— y el test exige que digan lo mismo, que es
más fuerte que comparar contra una instantánea de texto.

`self.ogr_status` y `self.statusBar()` son el mismo objeto
(`OgrStatusBar(QStatusBar)`, 294-296); se usa `ogr_status` por coherencia
con la rama de al lado, y el patrón nuevo ancla en el método, no en el
receptor, así que cuenta las dos formas. 8000 ms: más que los 3000-5000
de una confirmación rutinaria, porque es una precondición sobre la que
hay que actuar, y menos que los 15000 de v0.1.125, porque no es el
resultado de un cálculo que se acaba de tirar.

La única entrada española nueva es la del mensaje de dibujo de la rama
habilitada, que hasta ahora tampoco pasaba por `tr()`. El diccionario
pasa de 1283 a 1284 claves.

## 4. Los dos presupuestos, y por qué son dos

`_UNWRAPPED_BUDGET = 210` **no se toca**. Los patrones nuevos van en su
propia lista `_VISIBLE_MESSAGES` con su propio
`_UNWRAPPED_BUDGET_MESSAGES`: metidos en `_VISIBLE` sumarían 68 cadenas
de avisos al recuento de 20 de diálogos bajo el mismo techo de 210, y
dejarían el histórico del primero sin sentido — que es lo que la ficha
misma prohíbe en la frase siguiente a la que pide ampliarlo.

`_unwrapped_count()` gana un parámetro con centinela `None`, y no un
`patterns=_VISIBLE` por defecto: así la lista se lee en la llamada y no
se congela en la importación. Sin argumentos el comportamiento es
idéntico, y hay un test que lo comprueba comparando las dos formas.

El presupuesto nuevo se fija en **68**, el recuento real, y no en un
techo cómodo. Va con **dos** tests separados a propósito, para que un
fallo diga cuál de las dos cosas se rompió: uno dice que la cobertura no
decae (`n <= 68`) y el otro que el control no se afloja (`n == 68`). El
segundo es la lección del 210: un presupuesto con 190 de holgura dejó de
medir nada mucho antes de que nadie lo notara.

## 5. El test

`tests/test_block_search_action_not_modal_v1167.py`, 17 casos.
`_vNNNN` es la versión en la que el test **aterriza**, no la que nombra la
ficha (`_v1160`): mismo re-anclaje que d91, d95, d96, d98 y d102.

Los cuatro constructores estáticos de `QMessageBox` se re-enlazan para que
**lancen**, no sólo `information`: cambiar la caja por un `warning` no es
arreglarla. Y se reasigna el **nombre en el módulo**
(`main_window.QMessageBox`), no el atributo de la clase Qt: medido, las
dos cosas funcionan, pero `main_window.QMessageBox is QMessageBox`, así
que parchear la clase alcanza a PySide6 entero y un escape antes del
`finally` la dejaría parcheada para todos los archivos posteriores — la
regla 5 en su forma más cara de diagnosticar. Ningún otro test del
proyecto parchea `QMessageBox`; la convención es **evitar** la rama
modal, que es justo lo que dejó este defecto sin medir tanto tiempo.

**Contra el árbol de 0.1.166 fallan 9 de los 17 y pasan 8**, que es la
prueba de que el archivo mide algo — y los 8 que pasan son justo los que
deben pasar: la identidad que el arreglo **conserva** (con Block Search
puesto, la acción sigue entrando en `ToolMode.DRAW_BLOCK_SEARCH`) y las
cinco premisas medidas o refutadas (la acción está deshabilitada, un
`trigger()` no la alcanza, el terminal entrega la ventana, las dos barras
de estado son un objeto, y los siete patrones viejos nunca vieron estas
cadenas).

Dos de los casos leen el árbol sintáctico y no el resultado de una
corrida: uno exige cero `QMessageBox` dentro de la función —coge una caja
escondida tras una rama que la ejecución no recorre— y otro exige que
ninguna cadena llegue a `showMessage` o a un cuadro de mensaje sin pasar
por `tr()`. La función se localiza **por nombre**, nunca por rango de
líneas: todas las citas de línea de esta ficha estaban caducadas el día
que se leyó, y un rango es una cita que expira.

Ninguna aserción fija un factor de seguridad: lo que se comprueba son
identidades y nombres.

## 6. Lo que se ha medido

- **Suite entera y sin argumentos**: 3552/3552 (0.1.166 traía 3531; los 21
  nuevos son los 17 del archivo nuevo y 4 del de i18n).
- **`_unwrapped_count()` por defecto sigue en 20**, y el 210 intacto.
- **`_unwrapped_count(_VISIBLE_MESSAGES)`**: 70 → **68**.
- **Cero `QMessageBox` en el cuerpo de la acción** (medido por AST).
- **Diccionario español**: 1283 → 1284 claves.
- **Cero dígitos movidos, y es consecuencia**: el cambio no sale de
  `ogr_gui/`, y `d103()` lo comprueba contando apariciones de los símbolos
  de esta versión en `ogr_core`, `ogr_slip2d`, `ogr_fem2d` y `ogr_cli`,
  que son cero.

### Inventario de modales, que es el paso 5 del encargo

Se apunta y **no** se aborda aquí. Medido por AST, no por `grep`:

| | modales | con título literal sin `tr()` |
|---|---|---|
| `main_window.py` antes | 40 | 21 |
| `main_window.py` ahora | **39** | **20** |
| `ogr_gui/` entero ahora | **58** | **38** |

Los bloques más repetidos entre los que quedan: cinco `critical` con
título `'Error'` y cuatro de `'Expand / Shrink'`. Y `showMessage` en
`main_window.py`: **117** llamadas, **75** con el primer argumento sin
`tr()` (28 literales planos + 47 f-strings). `_info` (2739-2741) sigue
modal, traduce el título y no el mensaje, y lo llaman **42** veces; el
`_info` homónimo y distinto de `interpret_window.py:3595` tiene otros 55.

## 7. Se reporta y NO se corrige (regla 6)

- **`_UNWRAPPED_BUDGET = 210` contra una cuenta real de 20** sigue siendo
  un control que no puede fallar. Bajarlo lo prohíbe expresamente el
  criterio de cierre de esta ficha; queda medido y dicho.
- **Los 38 modales con título literal y los 75 `showMessage` sin `tr()`**
  siguen ahí: es el inventario de arriba, para un prompt futuro.
- **Los cuerpos de los modales son invisibles incluso a los patrones
  nuevos**, que sólo miran el título.
- **Las f-strings no las puede ver ningún patrón de este tipo** — 47 de
  las 117 llamadas a `showMessage`.
- **`_info` sigue modal**, con 42 + 55 llamadores; es el trabajo que la
  ficha excluye por alcance.
- **`"Non-Circular"` y `"Block Search"`** siguen sin `tr()` en
  `grid_dialogs.py:282` y `:304`, y el aviso reutilizado se apoya en que
  están en inglés en pantalla: quien los traduzca tiene que traducirlo con
  ellos.
- **Las 19 claves duplicadas** del diccionario siguen (medidas en
  v0.1.166), con las dos que discrepan sin tocar.
- **La clave compartida es larga** (~150 caracteres) y en una ventana
  estrecha Qt la corta con puntos suspensivos. Se prefiere a dos textos
  que divergen; si algún día molesta, lo que hay que acortar es el
  tooltip **también**, porque son la misma clave.
- **`main_window.py:327-329`** sigue envolviendo media frase:
  `tr("Ready") + " — File → Load Demo Slope…"`.

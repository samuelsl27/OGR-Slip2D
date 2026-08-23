# OGR Slip2D v0.1.102 — dos filtros que no filtraban, y por qué no bastaba con acordarse

`SearchSettings.min_elevation` y `SearchSettings.min_depth` llevaban desde
siempre declarados, editables en el diálogo bajo «Filtros», guardados en el
`.ogr` — y **ningún módulo del motor los leía**. `build_search` pasaba a sus
seis ramas únicamente `min_area`.

Es la **regla 7** en su forma más incómoda: el usuario marca la casilla, obtiene
exactamente el mismo número —recuento de superficies incluido— y concluye que
el filtro no tenía nada que quitar.

Se cierra la anomalía **A37-1** del banco de verificación.

---

## 1 · La medida, en una tabla

Problema 37 del banco: retroanálisis de refuerzo del manual de referencia de
**XSTABL (1999)**. Su enunciado exige *«only failure surfaces with a minimum
depth of 2 m»* para quitar de en medio los deslizamientos superficiales de la
cara. El `.ogr` del banco ya traía `min_depth = 2.0`; simplemente no llegaba.

Mismo modelo, mismo grid, lo único que cambia es si el filtro llega al motor:

Rejilla del banco, 24×24 centros × 60 incrementos de radio, 50 dovelas:

| | FoS | centro | espesor máximo | generadas | válidas |
|---|---|---|---|---|---|
| sin filtro (lo de ayer) | 0,726327 | **(−20,000 · 45,625)** | **0,642 m** | 16801 | 7932 |
| con `min_depth` = 2 m | 0,766024 | (−9,333 · 33,958) | 2,030 m | 16801 | 3097 |
| publicado (XSTABL 1999) | **0,764** | (−11,41 · 35,26) | | | |

De **−4,9 %** a **+0,26 %**. Y el mínimo de ayer era una **lámina de 64 cm** en
la cara del talud, con el centro **en el borde izquierdo de la rejilla** — que
es el otro síntoma, y tiene su propio apartado más abajo.

Nótese que `generadas` no se mueve: 16801 con filtro y sin él. Lo que se mueve
es el reparto entre válidas e inválidas, que es como tiene que ser.

(La ficha del banco describía esa lámina como de **0,44 m**, medida en 0.1.97.
Vuelta a medir hoy sale **0,642 m**, con el mismo FoS 0,726327 hasta el último
dígito. La diferencia está en el espesor, no en el resultado, y la explicación
más probable es v0.1.100, que cambió la base de la dovela de secante a cuerda.
Se anota como corrección de la ficha, no como cambio de conclusión: la lámina
sigue siendo una lámina.)

---

## 2 · Las cuatro preguntas que había que contestar antes de escribir nada

«Profundidad mínima» y «cota mínima» suenan obvias y no lo son. Cuatro
decisiones cambian qué superficies se descartan, y una interpretación
equivocada tira mecanismos reales:

| Pregunta | Respuesta |
|---|---|
| ¿Profundidad de qué? | La altura **máxima** de dovela de toda la superficie. No es por dovela, ni la media. |
| ¿Vertical o normal al terreno? | **Vertical**, de la superficie de rotura al terreno. |
| ¿Cota mínima de qué? | Del punto más bajo de la **superficie**, no de la masa. |
| ¿Descarta o recorta? | **Descarta**. La superficie no se analiza. |

Las cuatro están documentadas en la ayuda de la interfaz de referencia, bajo
*Surface Filter*, que además aclara dos cosas más: los dos controles son
**globales** —aparecen igual en el diálogo de las seis búsquedas— y el límite
inferior del contorno externo ya actúa como frontera infranqueable, así que
`min_elevation` sólo sirve para imponer una cota **por encima** de ese fondo.
Esa segunda parte sí estaba implementada, desde v0.1.84 (`leaves_soil_region`).

### La corroboración que no se buscaba

El círculo **que publica el manual** tiene un espesor máximo de dovela de
**2,011 m**, contra los 2 m que pide su propio enunciado. Once milímetros de
margen.

Eso no es una curiosidad: es una comprobación independiente del criterio. Si
«profundidad» hubiera querido decir profundidad *media*, o distancia *normal*
al terreno, **el círculo publicado habría caído por su propio filtro**. Las dos
lecturas alternativas quedan descartadas por la referencia misma, sin necesidad
de creerse la documentación.

---

## 3 · Dónde va el filtro, y por qué en un solo sitio

En `BaseSearch._best_of_masses`, y es el único sitio posible que no deja
puertas traseras: las dos entradas públicas al motor (`evaluate_circle` y
`evaluate_surface`) pasan por ahí desde v0.1.101, las seis búsquedas entran por
esas dos, y por ellas entran también *Optimize Surfaces* y el muestreador
probabilístico.

Orden dentro del bucle, por coste creciente:

```
min_elevation   geometría pura, ANTES de dovelar
slice_surface
< 3 dovelas
min_area
min_depth       max(altura de dovela) > valor, DESPUÉS de dovelar
_analyse
```

Una superficie filtrada se salta igual que hoy hace `min_area`, así que la
búsqueda la cuenta como **inválida** y no como inexistente: `generadas` no se
mueve. Es la invariante de v0.1.83, y un filtro nuevo es justo el tipo de
cambio que la rompería. Medido: 5234 generadas con filtro y sin él; lo que se
mueve es 2450/2784 → 954/4280.

### `lowest_elevation`, y la trampa que tiene dentro

Hace falta el punto más bajo del arco **analizado**, y la tentación es leerlo
de `SlipCircle.x_range()`. No se puede: `x_range()` devuelve la extensión del
**círculo entero**, `xc ± R`, no la cuerda. Hay que usar `x_left`/`x_right`,
que además ya vienen con la grieta de curvatura inversa aplicada.

Geometría exacta y **no** un mínimo muestreado sobre las dovelas. Sobre un arco
de 46 m troceado en 50 la diferencia es de 4 mm, o sea nada — pero un filtro
cuya respuesta se mueve al cambiar el número de dovelas no vale nada, y este
proyecto ya pagó esa lección entera en v0.1.100 y en el defecto D05.

---

## 4 · El hallazgo de verdad: no era olvidar un argumento

Lo interesante de A37-1 no es que alguien olvidara pasar dos parámetros. Es
**por qué el olvido no hizo ruido**.

Las seis búsquedas absorben lo que no reconocen a través de `**legacy_kwargs`.
Añadir `min_depth` al diccionario `common` de `build_search` y creer el trabajo
terminado habría sido exactamente el mismo error: cinco de las seis lo habrían
tragado **en silencio**, y la sexta —`PathSearch`, que sí tiene un parámetro
llamado `min_elevation`— habría funcionado, dando la impresión de que estaba
todo bien.

Por eso el arreglo no es la línea que faltaba sino un helper, `_base_kwargs`,
que reúne los argumentos que **toda** búsqueda acepta. Los seis constructores
repetían el mismo bloque de cuatro `pop` copiado literalmente; ahora lo piden
una vez. Un parámetro compartido nuevo se puede olvidar una vez, no seis.

Y hay un test que recorre las seis ramas de `build_search` y exige que los dos
filtros lleguen a cada una. La auditoría de v0.1.82 pedía un vigilante así para
`SearchSettings` entero, como `test_menu_reachability_v142.py` hace con la
barra de menús; esto lo es **sólo** para el grupo de filtros. El resto sigue sin
vigilante, y sigue anotado.

---

## 5 · Un mínimo en el borde de la rejilla ahora se dice

El centro que devolvía el problema 37, x = −20,00, **es** `grid_x_min`. Un
mínimo pegado al borde no es un mínimo: es el mejor de lo que se miró.

El coste de no decirlo está medido, en el problema 77 del banco y sobre el
mismo modelo:

| | mínimo en | FoS | error |
|---|---|---|---|
| rejilla hasta x = 900 | **x = 900** (el borde) | 1,757 | +11 % |
| rejilla hasta x = 1400 | x = 1019 | 1,587 | +0,2 % |

Once por ciento, y la corrida parecía convergida.

Conviene decir dónde NO salta, porque es la parte que se malinterpreta sola:
en el problema 37 **ya no salta**, y eso es la señal de que el arreglo funciona.
El centro se iba al borde *porque* faltaba el filtro; con `min_depth` aplicado
cae en (−9,33 · 33,96), dentro de la rejilla. Los dos síntomas eran el mismo
defecto visto por dos lados.

`grid_edge_note` avisa cuando el centro crítico cae en el perímetro de la
rejilla **realmente barrida** —que hay que recordar, porque sin rejilla de
usuario sale del contorno del modelo y `build_search` no la conoce—. Se
abstiene si un eje tiene vano nulo: en una rejilla de una sola fila todos los
centros están en el borde por construcción, y un aviso que salta siempre enseña
a no leer los avisos.

No cambia nada del análisis. Es un aviso, como el de tangente vertical de
v0.1.100.

---

## 6 · Tres etiquetas que llevaban años sin traducir

`Min elevation`, `Min depth` y `Min area`, en el grupo de filtros del diálogo
de búsqueda, no pasaban por `tr()` y no tenían entrada en español.

Lo llamativo es **cómo se libraron de los dos tests de i18n a la vez**, porque
no fue casualidad:

- el test de presupuesto cuenta texto sin envolver buscando un literal dentro
  de `addRow("...")`, y estas llegaban a `addRow` como **variable**, desde una
  función auxiliar. No había literal que ver;
- el test de completitud recoge las claves de `tr()` del árbol sintáctico, y
  ahí no había ninguna llamada a `tr()`.

Envolver dentro de la auxiliar —`addRow(tr(label_text))`— habría dejado el
segundo agujero abierto: `tr(variable)` tampoco aporta clave. Van envueltas en
el sitio de llamada, que es donde está el literal.

Traducidas con el término geotécnico castellano y no con el literal inglés:
**Cota mínima**, **Profundidad mínima**, **Área mínima**.

---

## 7 · Qué se probó

- `tests/test_surface_filters_v1102.py` — 21 tests. **No afirma ningún factor
  de seguridad**: sólo diferencias (dos corridas del mismo modelo tienen que
  discrepar), identidades (toda superficie superviviente cumple el filtro, que
  es lo que el filtro *es*) y relaciones de recuento. Incluye la dirección del
  efecto —el mínimo filtrado tiene que ser **más profundo**, no sólo distinto,
  o el filtro estaría cableado al revés— y el caso de que la corrida sin filtro
  contenga de verdad lo que el filtro quita, sin lo cual todo lo demás pasaría
  sobre una promesa vacía.
- `tests/test_grid_edge_note_v1102.py` — 8 tests: el aviso salta con la rejilla
  recortada, calla con la rejilla ancha, calla con vano nulo, y calla en una
  búsqueda sin rejilla.
- `validacion/casos/006-xstabl-1999-min-depth/` — **el anclaje externo**, y el
  primer caso de la carpeta que ejercita un filtro de superficie. Bishop
  simplificado contra el 0,764 publicado, tolerancia 1 %. Si el filtro deja de
  llegar al motor, el caso da −4,7 % y se pone rojo.
- Suite completa.
- Banco: problema 37 reproduce **0,766024**, y los 16 problemas que salían
  enteramente `OK` se vuelven a correr para comprobar que no se mueve ninguno.
  De los **142 modelos** `.ogr` del banco, **sólo los dos del problema 37**
  declaran un filtro de superficie, así que para los otros 140 el código nuevo
  está detrás de un `is not None` y no se ejecuta.

### Sobre la rejilla del caso de validación

El problema original usa 24×24 con 60 incrementos de radio. El caso usa
**16×16 con 40**, porque se midió que da el **mismo** error (+0,26 %) en la
mitad de tiempo, y con el centro crítico *más* cerca del publicado (1,5 m
contra 2,5 m). Bajar más degrada: 12×12 con 30 se va a +1,44 %.

El 8×8 vuelve a caer en +0,33 %, y **no** es la razón de nada. Entre él y la
rejilla fina los valores intermedios son peores, así que ese acierto es suerte
del muestreo y no convergencia. Elegirlo por el número habría sido dejar que
una medición justificara una decisión que no sostiene, que es la lección de
v0.1.82 y no apetece repetirla.

---

## 8 · Reportado, no corregido

- **`SearchSettings.optimize_use_depth_elevation_concave_checks`** no aparece
  en ningún otro sitio del repositorio. Misma familia, misma regla 7, otra
  pestaña. No se ha tocado.
- El **informe PDF** no imprime los dos filtros, aunque sí imprime *Composite
  Surfaces*. Ahora que muerden el resultado, deberían salir en él.
- La documentación de referencia lista un cuarto filtro, por **peso mínimo de
  la masa**, que el programa no ofrece. No infringe la regla 7 —no existe, no
  es un control muerto— pero queda anotado.

---

## 9 · Números de versión

`pyproject.toml`, `MainWindow.VERSION` y el `__version__` de `ogr_core`,
`ogr_slip2d`, `ogr_fem2d`, `ogr_gui` y `ogr_cli` — los siete.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later

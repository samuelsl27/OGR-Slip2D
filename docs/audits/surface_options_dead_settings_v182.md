# Auditoría — los tres ajustes de Surface Options que no hace nadie

**Versión auditada:** v0.1.82 · **Autor:** Samuel Sáez López — UPCT

> **Regla 6.** Esto es un informe, no una corrección. Los tres hallazgos
> están medidos y ninguno se ha tocado.

---

## Por qué esta auditoría

Al arreglar la **curvatura inversa** en v0.1.82 salió un patrón que valía
la pena perseguir: un ajuste presente en `SearchSettings`, guardado en el
`.ogr`, editable en el diálogo, *citado en el informe PDF* — y que ningún
módulo de `ogr_slip2d` leía. Es la **regla 7** exactamente: un control que
no afecta al resultado es peor que no tenerlo, porque el usuario cree que
el análisis lo respeta.

Los otros tres ajustes de la misma pestaña son `composite_surfaces`,
`min_elevation` y `min_depth`. **Los tres están muertos.**

---

## La prueba

Misma malla de referencia del Ejemplo 1 (40–120 × 30–120, 20×20,
incremento de radio 10, 25 dovelas, Bishop simplificado). Se ejecuta la
búsqueda completa cambiando un solo ajuste cada vez:

| Ajuste | FS crítico | evaluadas | válidas | centro | R |
|---|---|---|---|---|---|
| por defecto (los tres apagados) | 0,884517 | 3083 | 2966 | (88 , 70,5) | 47,142 |
| `composite_surfaces = True` | 0,884517 | 3083 | 2966 | (88 , 70,5) | 47,142 |
| `min_elevation = 20.0` | 0,884517 | 3083 | 2966 | (88 , 70,5) | 47,142 |
| `min_depth = 15.0` | 0,884517 | 3083 | 2966 | (88 , 70,5) | 47,142 |
| los tres a la vez | 0,884517 | 3083 | 2966 | (88 , 70,5) | 47,142 |

**Idénticas hasta el último dígito, incluido el recuento de superficies.**
No es que el efecto sea pequeño: es que no hay efecto.

### Dónde se corta el cable

```
ogr_core/project/settings.py:190   composite_surfaces: bool = False
ogr_core/project/settings.py:285   min_elevation: Optional[float] = None
ogr_core/project/settings.py:286   min_depth:     Optional[float] = None
```

Se editan en `ogr_gui/dialogs/grid_dialogs.py` (líneas 346-349, 794,
867-871) y en `project_settings_dialog.py` (544, 557). `composite_surfaces`
llega incluso al informe PDF: `ogr_core/report/report_generator.py:230`
imprime «Composite Surfaces: Enabled/Disabled».

**`ogr_slip2d/analysis_runner.py` no los menciona ni una vez.** `GridSearch`
no tiene parámetro para ninguno de los tres. `PathSearch` sí acepta
`min_elevation` (`search.py:1422`) y lo usa como suelo del muestreo
(`search.py:1508`) — pero el runner nunca se lo pasa, así que siempre vale
`None`. La única aparición de «Composite» en `ogr_slip2d` es un **comentario**
en `surface.py:141` que explica que el corte se elige *como si* estuviera
desactivado.

---

## A1 · Composite Surfaces

**Qué debe hacer** (documentación de referencia, *Grid Search → Composite
Surfaces*):

> Normalmente, si una superficie circular se prolonga más allá del límite
> inferior del contorno externo, la superficie **se descarta** y no se
> analiza. Con la casilla marcada, esas superficies **se adaptan a la forma
> del contorno externo** entre los dos puntos de intersección del círculo
> con su borde inferior. […] La resistencia usada en cada dovela de los
> tramos rectos es la del material **inmediatamente por encima** de la base
> de esa dovela.

Es la forma de modelar un techo de roca: se dibuja el fondo del contorno
externo con la forma del sustrato y la búsqueda circular se adapta a él.

**Lo grave no es la rama ON, es la rama OFF.** Igual que en la curvatura
inversa, ninguna de las dos ramas está implementada:

| | superficies |
|---|---|
| con dos cortes en el terreno | 3192 |
| que salen del contorno externo por un tramo **no-talud** | **94** |
| de esas, las que **analizamos y damos por válidas** | **15** |

Los tramos no-talud de este modelo son el borde izquierdo (x = 0), el
derecho (x = 120) y el fondo (y = 0). La referencia descarta esas
superficies con el **error −103**, e informa de 183 en esta malla (el orden
de magnitud coincide; el recuento exacto no, porque el muestreo de radios
difiere ligeramente).

Las 15 que damos por buenas tienen FS de 6,22 en adelante —la más baja en
centro (44 , 34,5) R = 35,017—, así que **en este modelo** ninguna llega a
ser la crítica. Eso es suerte, no diseño: la masa deslizante se sale del
suelo modelado, su peso se cuenta de menos y su factor de seguridad no
significa nada. En un modelo con el sustrato en el fondo del contorno —que
es justo para lo que existe la opción— serían las superficies interesantes.

**Para validar la rama ON hace falta una referencia que hoy no tenemos.**
El informe del Ejemplo 1 se calculó con *Composite Surfaces: Disabled*, así
que sirve para validar el descarte (−103) pero no la adaptación. Haría
falta **una corrida del mismo modelo con la casilla marcada**.

---

## A2 · Minimum Elevation

**Qué debe hacer:** cota Y mínima admisible; toda superficie que baje de
ella se descarta. La referencia añade una nota que importa: *por defecto ya
usa el límite inferior del contorno externo como frontera infranqueable*,
así que el ajuste solo hace falta para imponer una cota **por encima** de
ese fondo.

Esa nota conecta con A1: **la frontera por defecto tampoco está
implementada** — es el mismo agujero de las 94 superficies.

**Cuánto afectaría:** con `min_elevation = 20`, **596 de 3192** superficies
bajan de la cota 20 y deberían descartarse. Hoy se analizan las 596.

---

## A3 · Minimum Depth

**Qué debe hacer:** se generan las dovelas, se mide la **altura máxima** de
dovela (vertical, de la superficie de rotura al terreno) y si no supera el
valor pedido, el círculo **no se analiza**. Es el filtro para quitar de en
medio las roturas superficiales.

**Cuánto afectaría:** con `min_depth = 15`, **2052 de 3192** superficies
tienen altura máxima de dovela menor de 15 m. Hoy se analizan las 2052.

**Es el más peligroso de los tres**, y no por el recuento. Los otros dos
descartan superficies que casi siempre salen con FS alto; éste lo usa el
usuario precisamente **cuando la crítica le sale superficial y quiere ver
el mecanismo profundo**. Pone el filtro, obtiene exactamente el mismo
número, y concluye que no hay mecanismo profundo — cuando lo que ha pasado
es que el filtro no existe.

---

## Recomendación

Por orden de riesgo para quien usa el programa:

1. **`min_depth`** — filtro post-dovelado, ~10 líneas en `BaseSearch.evaluate_*`.
   Se valida con la regla 7: la misma malla con y sin filtro tiene que dar
   recuentos distintos, y con un valor grande la crítica debe cambiar.
2. **`min_elevation`** — el mismo sitio, más la frontera por defecto del
   contorno externo, que es lo que de verdad falta.
3. **La rama OFF de Composite Surfaces** — descartar lo que sale del
   contorno externo por un tramo no-talud. Se valida contra el −103 de la
   referencia.
4. **La rama ON de Composite Surfaces** — es una funcionalidad, no un
   arreglo: hay que construir la superficie compuesta (arco + tramos del
   contorno) y resolver la resistencia por «material inmediatamente
   superior». **Necesita una corrida de referencia con la casilla marcada
   antes de escribir una línea.**

Y hace falta un test que impida que esto vuelva a pasar: uno que recorra
`SearchSettings` campo por campo y exija que cada uno llegue a alguna
búsqueda, del mismo modo que `test_menu_reachability_v142.py` recorre la
barra de menús. La regla 3 tiene su vigilante desde v0.1.42; la regla 7 no
tiene ninguno, y por eso lleva cuatro ajustes.

---

© 2026 Samuel Sáez López — UPCT — AGPL-3.0-or-later

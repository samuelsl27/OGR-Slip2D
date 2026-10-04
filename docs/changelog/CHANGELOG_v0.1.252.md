# OGR Slip2D v0.1.252

**D251: la superficie que corre por una capa débil se dibuja, se exporta, se
elige, se nombra y se resume como cualquier otra. D252: «Add Query» vuelve a
elegir lejos de un centro de la rejilla.** Cero dígitos: son la interfaz, el
DXF y la API.

Tercera versión de la tanda Help + D85, D251/D252, D253, D97, D128 y D131.
Las dos fichas se abrieron en el ciclo de 0.1.251 y se corrigen juntas por
decisión de la propietaria (2026-10-03).

## 0. Lo que se encontró

### D251: cada consumidor que despacha por el tipo perdía la capa débil

Salió al preparar D85 y de la revisión de diseño de la tanda. Cada uno
pregunta por el `type` serializado de la superficie, y nadie conocía
`weak_layer`:

- **El lienzo** (`SlipSurfaceItem`) tenía ramas para `circle` y para
  `polyline`/`composite`. Una superficie de capa débil caía fuera y se dibujaba
  vacía. Medido con la crítica del talud plano de `test_weak_layer_v1121`: 0
  elementos de trazo, con 3 vértices en su diccionario. Desde 0.1.121, la
  crítica de un modelo con capa débil no estaba en pantalla.
- **El DXF** iba a `surf.polyline.vertices`, que la superficie de capa débil
  no tiene. La exportación lanzaba `AttributeError` antes de `saveas` y no
  escribía ni el archivo.
- **La interpretación.** `_at_grid_centre` la dejaba fuera aunque su base
  fuera un círculo de ese centro. `minimum_per_centre` la trataba como
  superficie sin centro, y `_centre_tolerance` no contaba su centro.
  `minimum_row_text` la llamaba «superficie no circular».
- **La API.** `surface_summary` devolvía solo `{"type": ...}` para la
  compuesta y para la capa débil: el MCP no veía su geometría.
- **La optimización.** La interfaz y la API preguntaban cada una por su
  cuenta `hasattr(surface, "polyline")` y contestaban «la superficie crítica
  de este método es un círculo», falso para una de capa débil.

### D252: Add Query revienta lejos de la rejilla desde 0.1.201

`InterpretWindow._surface_at` llamaba a `self._distance_point_to_surface`, que
0.1.201 (commit 13af5e2) se llevó a `ogr_slip2d/interpretation.py`
(`distance_to_path`) sin cambiar esta llamada. Medido en memoria con la
crítica de Ej_1: `AttributeError` en cuanto se pincha sobre ella lejos de la
rejilla. Lo llaman el paso del ratón con «Add Query» activo y el clic que la
fija. Una poligonal o una superficie de capa débil solo se pueden elegir así.

## 1. Los cambios

- **Lienzo** (`ogr_gui/canvas/graphics_items.py`):
  - `weak_layer` entra en la rama de la poligonal y la compuesta, que ya lee
    los `vertices` de la raíz (los de dibujo, con quiebros) y las grietas;
  - `SlipRadiiItem` dibuja los radios desde el centro de la base cuando la
    base es un círculo o una compuesta, como para la compuesta:
    `WeakLayerSurface.moment_axis` delega en la base.
- **DXF** (`ogr_core/dxf/exporter.py`):
  - la compuesta y la capa débil exportan sus `drawing_vertices()`;
  - una clase de superficie que el exportador no conozca se deja fuera con
    una línea en el informe, en vez de reventar y perder el dibujo entero.
- **`interpretation.slip_centre`** responde de dónde salió una superficie: el
  centro de un círculo o de una compuesta, o el de la base de una capa débil.
  Lo preguntan `minimum_per_centre` y la ventana (`_at_grid_centre`,
  `_centre_tolerance`), en vez de una prueba de tipo en cada sitio.
- **`minimum_row_text`** la nombra «superficie de capa débil, x de … a …»,
  con `tr()`.
- **API** (`ogr_api/results.py`): `surface_summary` da la geometría de la
  compuesta (su círculo y los vértices sobre los que se analizó) y de la capa
  débil (su base resumida igual, los tramos de cada capa activa con material y
  contorno, y sus vértices). El círculo y la poligonal salen como antes.
- **Optimización.** `ogr_slip2d.optimize.optimisation_refusal(surface)` es la
  única pregunta, y la hacen la interfaz y la API. Una superficie de capa
  débil recibe su propia frase: va por una capa débil y se recorta desde su
  base en cada evaluación, así que no tiene vértices propios que mover. Hay
  traducción al español.
- **D252:** `_surface_at` mide con `interpretation.surface_path` y
  `distance_to_path`, sobre la superficie que el motor CALCULÓ, la base de sus
  dovelas.

## 2. Tests

**`tests/test_weak_layer_drawing_v1252.py`**, 16 casos.
- **El lienzo:** el trazo de la crítica de capa débil es exactamente su lista
  de vértices de dibujo, y cada punto está sobre la recta de la junta
  `y = 2 + (8/28)(x − 2)`. Los radios salen del centro de la base y miden R.
  El círculo y la poligonal se dibujan como antes.
- **El DXF:** la LWPOLYLINE de la crítica es su lista de vértices de dibujo,
  leída de vuelta con ezdxf. Una superficie desconocida se deja fuera,
  dicho, y el archivo se escribe.
- **La interpretación:** el centro es el de la base; `minimum_per_centre`
  guarda solo la de menor factor de dos superficies de capa débil del mismo
  centro; la fila la nombra.
- **La API:** la capa débil y la compuesta llevan su geometría; el círculo y
  la poligonal, lo de antes.
- **La optimización** distingue la capa débil del círculo, y las dos puertas
  hacen la misma pregunta.
- **D252:** un pinchazo sobre la crítica lejos de la rejilla devuelve una
  superficie que pasa por ese punto, y el paso del ratón no lanza.

**Discriminación** contra `git archive` b3e2257 (0.1.251), con el envoltorio
sin buscador editable: **13 de 16 fallan**. Pasan, a propósito, los dos
controles de «como antes» y la premisa. La primera versión del caso de
`minimum_per_centre` pasaba también en 0.1.251, porque con una sola superficie
«suelta» y «con centro» dan lo mismo. Se rehízo con dos superficies del mismo
centro antes de archivar la discriminación.

## 3. El banco

Sin re-corrida: ningún cambio toca un cálculo, y el banco no tiene números de
interfaz, de DXF ni de la API.

- **`d251()`**, en vivo sobre la crítica de capa débil del talud plano de
  v1121:
  - el trazo del lienzo son sus 3 puntos de dibujo;
  - el DXF, escrito en un temporal y leído de vuelta, es su poligonal de
    dibujo;
  - la API la resume con base, capas y vértices;
  - la optimización la nombra capa débil;
  - con base circular, su centro de rejilla es el de la base, (18; 28).

  Veredicto CUBIERTO POR TEST. Con el árbol de 0.1.251 da NO SE SOSTIENE: el
  lienzo tiene 0 elementos frente a 3 vértices y el resto revienta.
- **`d252()`**, en vivo, con una ventana de interpretación real sin pantalla
  sobre una búsqueda de rejilla del talud de las dos juntas. Un pinchazo
  sobre la crítica lejos de todo centro devuelve una superficie que pasa por
  ese punto, y el paso del ratón con «Add Query» no lanza. La fuente ya no
  llama a `_distance_point_to_surface`. Veredicto CUBIERTO POR TEST; con
  0.1.251, `AttributeError`.

  La primera versión de esta comprobación buscaba el nombre como subcadena y
  daba NO SE SOSTIENE: lo encontraba en el comentario de `_surface_at` que
  cuenta la historia a propósito. Se corrigió la comprobación, no el código:
  ahora busca la llamada en el AST.
- **Verificación entera:** 222 cierres y 0 bajadas.
- **Cierre del ciclo:**
  - instantánea 0.1.252;
  - D251 y D252 retiradas (216 cerradas en el índice);
  - `PAQUETES` de P1 podado y la cadena tachada;
  - prompts regenerados;
  - auditorías del 02 y de la raíz con 0 ERROR;
  - instantánea con `--forzar`;
  - `--seco` completo tras retirar: 222 claves, iguales al JSON clave a clave.

## 4. Verificación

- **Suite entera:** 5558 de 5558.
- **Selección** de DXF, interpretación, lienzo, i18n, optimización, capas
  débiles, API, consultas, mínimos, claves y menús: 584 de 584 (30 archivos).
- **Discriminación:** 13 de 16 contra 0.1.251.

**Qué falta por probar:**
- **En pantalla:** la crítica de un modelo con capa débil dibujada en el
  lienzo, «Add Query» sobre una poligonal, y un DXF de una crítica de capa
  débil abierto en un programa de CAD.

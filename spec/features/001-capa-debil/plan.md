# Plan de implementación

## Enfoque

La capa débil es un `BoundaryType` nuevo cuya resistencia sale del **material
que referencia**, reutilizando el campo `Boundary.material_id` que ya existe.
Un módulo nuevo, `ogr_slip2d/weak_layers.py`, decide qué tramos de una
superficie discurren sobre qué capas y devuelve la superficie recortada; esos
tramos viajan sobre la superficie igual que ya viaja `tension_crack_wall`, y el
dovelador los usa para dos cosas: cortar dovela en sus extremos y darle a la
dovela el material de la junta. La generación de casos —qué capas están activas
en cada evaluación— se engancha en `BaseSearch._best_of_masses`, que es el punto
único por el que todas las búsquedas llegan al motor.

## Archivos que se tocan

| Archivo | Qué cambia |
|---|---|
| `ogr_core/geometry/boundary_type.py` | nuevo — miembro `WEAK_LAYER`, `display_name`, `default_color` |
| `ogr_core/geometry/boundary.py` | nuevo campo `suppressed`, serializado |
| `ogr_slip2d/weak_layers.py` | **nuevo** — recorte, tramos y generación de casos |
| `ogr_slip2d/slicer.py` | modificado — cortes obligatorios y material de la junta |
| `ogr_slip2d/search.py` | modificado — bucle de casos y límite de ángulo de base |
| `ogr_core/project/settings.py` | nuevos — `weak_layer_handling`, `max_base_angle_deg` |
| `ogr_gui/canvas/tool_mode.py` | nuevo modo `DRAW_WEAK_LAYER` |
| `ogr_gui/canvas/canvas_view.py`, `graphics_items.py` | visibilidad, color, z-order |
| `ogr_gui/main_window.py` | acción, menú Boundaries, asignación de material |
| `ogr_gui/dialogs/display_options_dialog.py`, `grid_dialogs.py` | opción de visualización y modo de tratamiento |
| `ogr_gui/i18n/__init__.py` | traducciones |
| `ogr_core/geometry/transforms.py`, `ogr_core/dxf/importer.py` | conversión y DXF |
| `tests/test_weak_layer_v1121.py` | **nuevo** |

## Decisiones de diseño

**La resistencia sale de un material, no de campos c/φ en el contorno.** Es lo
que hace la referencia —su figura 109.1 lista el *Weak Layer* en la tabla de
materiales, con su γ, su tipo de resistencia, su superficie de agua y su Ru— y
tiene tres ventajas concretas: hereda los veinte modelos constitutivos del
proyecto en vez de sólo Mohr-Coulomb, no añade campos nuevos al formato, y
reutiliza `Boundary.material_id`, que ya está serializado.

**El peso NO cambia.** Una junta de espesor nulo no pesa: `_column_weight` sigue
integrando la columna banda a banda con los materiales de las regiones. Sólo se
sustituye `Slice.material`, y con él la resistencia y la presión intersticial.
Lo segundo es una decisión, no un descuido: la tabla de la referencia le da a la
capa columnas *Water Surface* y *Ru* propias.

**El bucle de casos va en `_best_of_masses` y no en cada búsqueda.** Ese método
ya elige la peor entre varias alternativas —las masas disjuntas de un círculo—
y es donde v0.1.102 y v0.1.118 pusieron los filtros de superficie y los Slope
Limits por la misma razón: un filtro colocado en otro sitio es un filtro que
alguna de las seis búsquedas puede rodear.

**Alternativa descartada: recortar en `slice_surface`,** como hace la grieta de
tracción. Es donde estaría si el recorte fuese único, pero la *generación
automática de casos* necesita evaluar N variantes de la misma superficie y
quedarse con la peor; eso es una decisión de nivel superior al dovelado.

**Alternativa descartada: `CompositeSurface`.** Comparte la forma —un arco que
sigue una polilínea en parte de su longitud— pero no la regla: el composite es
`max(arco, suelo)`, un techo por abajo, mientras que la capa débil es «engancha
y sigue hasta salir». Un `max` no sabe soltarse.

## Riesgos

- **2ⁿ evaluaciones por superficie** con generación automática de casos. Tope
  configurable, y cuando se recorta se **dice**: un truncado silencioso se lee
  como cobertura completa.
- **Recortar un círculo lo convierte en polilínea**, así que el eje de momentos
  deja de ser el centro. En D15/A22-1 el eje decidió el resultado (−1,84 % con
  eje de polilínea contra +0,08 % con el centro). Hay que medir las dos antes de
  fijar una.
- **`BoundaryType` tiene dos `mapping[self]` sin `.get()`**: un miembro nuevo sin
  entrada revienta con `KeyError` lejos del sitio donde se olvidó. Y hay ~10
  puntos de enganche dispersos por la GUI y el motor.
- Que el 109 no cierre por el sesgo de la cohesión equivalente en vez de por la
  capa débil. Por eso el criterio lleva la razón Janbu/Bishop, que lo cancela.

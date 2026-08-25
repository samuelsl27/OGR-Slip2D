# Tareas

## Núcleo

- [x] `BoundaryType.WEAK_LAYER` + entrada en `display_name` y en `default_color`.
- [x] `Boundary.suppressed: bool = False`, en `to_dict` / `from_dict`.
- [x] `ProjectSettings`: `weak_layer_handling` (`"highest"` / `"auto_cases"`) y
      `max_base_angle_deg` (80.0), con su serialización.

## Motor

- [x] `ogr_slip2d/weak_layers.py`:
  - [x] `weak_layer_boundaries(project)` — activas, sin suprimir.
  - [x] `clip_surface_to_weak_layers(...)` — superficie recortada + tramos.
  - [x] `weak_layer_cases(project, surface, ground)` — variantes por modo.
  - [x] rechazo de corte vertical en compresión y de ángulo de base > θ_max.
- [x] `slicer.py`: extremos de tramo como cortes obligatorios.
- [x] `slicer.py`: `Slice.material` = material de la junta dentro del tramo.
- [x] `search.py`: bucle de casos en `_best_of_masses`.

## Interfaz

- [x] `ToolMode.DRAW_WEAK_LAYER` + `boundary_type_drawn` + cursor + mensaje.
- [x] Acción `add_weak_layer` con `_mk`, colgada del menú **Boundaries**.
- [x] Al cerrar la polilínea, diálogo de asignación de material.
- [x] Visibilidad, color y z-order en el lienzo y en opciones de visualización.
- [x] Modo de tratamiento en *Surface Options*.
- [x] `convert_boundary` y mapa DXF.
- [x] Traducciones en `ogr_gui/i18n/__init__.py`.

## Tests — `tests/test_weak_layer_v1121.py`

- [x] Forma cerrada plana en Ordinary, 1e-9, e independiente de n.
- [x] Identidad de trayectoria: el camino recortado, escrito a mano.
- [x] Identidad de los dos modelos: junta contra material único.
- [x] El tramo sobre la junta usa su resistencia y NO su peso.
- [x] Los extremos del tramo son cortes de dovela.
- [x] Regla 7: los dos modos separan el número; `suppressed` lo separa; θ_max
      descarta superficies.
- [x] Serialización de ida y vuelta con material y `suppressed`.
- [x] Alcanzabilidad de menú y cobertura i18n (los tests existentes bastan).

## Banco y cierre

- [x] `construir_modelo.py` del problema 109 sobre la geometría del 108.
- [ ] Correr el 109 y comparar contra los cuatro valores publicados.
- [ ] Rehacer la ficha del 109 (deja de estar omitido) y la comparativa.
- [x] Changelog `docs/changelog/CHANGELOG_v0.1.121.md` con lo que se encontró.
- [x] Subir la versión en los **siete** sitios.
- [ ] Suite entera, sin argumentos.

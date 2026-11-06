# Tareas

Pequeñas y verificables. Cada versión se cierra con `/release`:
- los nueve números;
- el contador de tests en los README;
- el changelog que cuenta qué se encontró;
- la suite entera `--jobs 4`;
- el resumen a la propietaria antes del commit.

## 0.1.427 — Superficies no circulares del usuario

- [x] 1. `UserPolylineSurface` en `ogr_core/geometry/user_polyline.py`.
  - id y puntos, con x estrictamente creciente tras normalizar el sentido del dibujo.
  - Se rechaza un retroceso en x o un tramo vertical.
- [x] 2. `Project.user_polylines`:
  - clave `.ogr` solo si no está vacía;
  - en `LIGHT_ATTRS` y en `tests/test_window_undo_v1301.py`;
  - viaja con la copia de diseño.
- [x] 3. El ajuste de extremos al contorno baja de `ogr_api/ops/analysis.py` al motor, y `surface_evaluate` lo
      llama desde allí.
- [x] 4. `_evaluate_user_surfaces` evalúa las polilíneas en corridas no circulares y las salta en circulares,
      con notas `USER_*` propias (código, español y muestra).
- [x] 5. API y MCP:
  - `user_surface_add` con `{"type": "polyline", "points": …}`;
  - `user_surface_delete` de las dos clases;
  - descripciones y `herramientas.md`;
  - `tests/test_f2_ops_v1196.py` cambia con su razón.
- [x] 6. Ventana:
  - acciones «Añadir superficie no circular» y su gestor en Superficies, en gris con tipo circular;
  - modo de lienzo con `ToolMode`, cursor, estado y `_set_tool`;
  - dibujo en `_draw_user_surfaces`;
  - deshacer.
- [x] 7. Test `tests/test_user_polylines_v1427.py`:
  - ida y vuelta, `.ogr` viejo y huella;
  - el mismo F que `surface_evaluate` en cada método vertical;
  - salto en circular;
  - menú y gris.
- [x] 8. Español de todo texto nuevo, y menú alcanzable.

## 0.1.441 — Solver

- [ ] 9. `ogr_slip2d/sarma/solver.py`: recurrencia, H(F), raíz mayor (barrido y Brent), sentido fijo y
      cinemático, Kc(1), normales y fuerzas de cara, y motivos con código.
- [ ] 10. La tabla de fuentes de `.claude/skills/geotecnia/SKILL.md`:
  - Sarma (1973), consultado;
  - Sarma (1979), no consultado;
  - la derivación propia.
- [ ] 11. Test `tests/test_sarma_solver_v1437.py`:
  - la cuña cerrada;
  - Janbu a 1e-10;
  - el reflejo;
  - los dos sentidos;
  - la raíz junto a un polo;
  - tolerancia e iteraciones mueven el número.

## 0.1.442 — Cuñas

- [ ] 12. `ogr_slip2d/sarma/wedges.py` y `angles.py`, con:
  - fronteras y políticas de ángulo;
  - topes que se cruzan;
  - peso por material con Shapely;
  - U y PW por tramos;
  - agua libre y cargas;
  - grieta;
  - factores de acción;
  - columna en la base;
  - resistencia de cara;
  - rechazos con código.
- [ ] 13. B0 en el banco: `cunas_sarma.py --sentido fijo|cinematico`, con el cinemático por defecto.
- [ ] 14. Test `tests/test_sarma_wedges_v1438.py`:
  - área y peso en forma cerrada;
  - δ = 0 frente al rebanador vertical donde este es exacto;
  - c/φ de base igual a la de Bishop con SHANSEP y VSR;
  - el ancla de diseño de Frank et al. (2004);
  - el 4 y el 5 a ±1 %, con los dos modos a 1e-6 de la herramienta;
  - «solo bases» se aparta;
  - cada rechazo.

## 0.1.443 — Método registrado

- [ ] 15. `SarmaNonVertical`. Funciona con `cls()` a pelo.
- [ ] 16. Puertas del motor:
  - `build_method` y `_slice_trial` (vertical primero, luego las `Wedges`);
  - número de cuñas propio;
  - `SliceShare`;
  - salto de corrida con desembalse y B-bar, y el envoltorio de red;
  - el cuarto cubo de m-alpha;
  - `compute_interslice_state`;
  - `SliceStore` y HDF5;
  - Ky genérico.
- [ ] 17. `settings.sarma` con escritura condicional, esquema del API, avisos y factores de diseño sobre la c/φ
      global.
- [ ] 18. CLI: alias `sarma` y `--sarma-slices`, con su test.
- [ ] 19. Ventana:
  - casilla y grupo de ajustes;
  - tooltips y censos con Sarma, y sus tests;
  - guardas en el PNG, en Interpret y en el informe.
- [ ] 20. La suite archivo a archivo, con las exenciones justificadas (soportes), y el A/B de coste.
- [ ] 21. Documentación: `architecture.md`, `plugins.md`, `guide.py`, README y AGENTS.md.
- [ ] 22. Test `tests/test_sarma_method_v1439.py`. Cubre los criterios de «Integración» de `spec.md`.

## 0.1.444 — Datos por vértice

- [ ] 23. Ángulo, c y φ por vértice en `UserPolylineSurface` y en la superficie del motor, por coordenadas.
- [ ] 24. API (`sarma` en `user_surface_add` y `surface_evaluate`, y `user_surface_edit`), MCP y
      `herramientas.md`.
- [ ] 25. Factores de diseño y avisos de combinaciones inactivas.
- [ ] 26. Tabla de ángulo, c y φ en la ventana, desde el menú y desde el menú contextual; rayos punteados.
- [ ] 27. Test `tests/test_sarma_vertices_v1440.py`:
  - el 4 y el 5 guardados y por `surface_evaluate`;
  - cada dato mueve el número;
  - las precedencias;
  - F/γ.

## 0.1.445 — Interpret

- [ ] 28. Cuñas como polígonos, selección, diagrama de cuerpo libre, filas de cara y tabla del informe.

## 0.1.446 — Herramienta de ángulos

- [ ] 29. Definir y quitar ángulos con el ratón o tecleando, atajos en el vértice y deshacer, con sus tests en
      el lienzo mostrado.

## 0.1.447 — Ángulos optimizados

- [ ] 30. Digitalizar las figuras 1.2 y 1.3 del problema 1, con la lectura declarada.
- [ ] 31. Optimizador determinista; `optimized_global` y `optimized_all`; Block y Path con la crítica
      optimizada.
- [ ] 32. Test:
  - el problema 1 frente a 1,382 / 1,324;
  - F optimizado ≤ el de las políticas;
  - determinismo y coste.

## Banco (fuera de git)

- [ ] 33. B1:
  - `superficie_publicada` con el bloque `sarma`;
  - `settings.sarma` en los modelos del 4 y del 5;
  - entradas `<esc>__sarma`;
  - re-corrida.
- [ ] 34. B2 y B3: `comparar_con: sarma` con su razón, y la columna «OGR Sarma» al final de la comparativa.
- [ ] 35. B4 y B5: `d357()` y el re-anclaje de `d122()` y `d123()`; después el procedimiento de cierre.
- [ ] 36. B6: el resto del 03 (1, 6, 7, 8 y 9) comparado o declarado.

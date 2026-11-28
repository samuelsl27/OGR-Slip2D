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

## 0.1.461 — Solver

- [x] 9. `ogr_slip2d/sarma/solver.py`: recurrencia, H(F), raíz mayor (barrido y Brent), sentido fijo y
      cinemático, Kc(1), normales y fuerzas de cara, y motivos con código.
- [x] 10. La tabla de fuentes de `.claude/skills/geotecnia/SKILL.md`:
  - Sarma (1973), consultado;
  - Sarma (1979), no consultado;
  - la derivación propia.
- [x] 11. Test `tests/test_sarma_solver_v1461.py`:
  - la cuña cerrada;
  - Janbu a 1e-10;
  - el reflejo;
  - los dos sentidos;
  - la raíz junto a un polo;
  - tolerancia e iteraciones mueven el número.

## 0.1.463 — Cuñas

- [x] 12. `ogr_slip2d/sarma/wedges.py` y `angles.py`, con:
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
- [x] 13. B0 en el banco: `cunas_sarma.py --sentido fijo|cinematico`, con el cinemático por defecto.
- [x] 14. Test `tests/test_sarma_wedges_v1463.py`:
  - área y peso en forma cerrada;
  - δ = 0 frente al rebanador vertical donde este es exacto;
  - c/φ de base igual a la de Bishop con SHANSEP y VSR;
  - el ancla de diseño de Frank et al. (2004);
  - el 4 y el 5 a ±1 %, con los dos modos a 1e-6 de la herramienta;
  - «solo bases» se aparta;
  - cada rechazo.

## 0.1.464 — Método registrado

- [x] 15. `SarmaNonVertical`. Funciona con `cls()` a pelo.
- [x] 16. Puertas del motor:
  - `build_method` y `_slice_trial` (vertical primero, luego las `Wedges`);
  - número de cuñas propio;
  - `SliceShare`;
  - salto de corrida con desembalse y B-bar, y el envoltorio de red;
  - el cuarto cubo de m-alpha;
  - `compute_interslice_state`;
  - `SliceStore` y HDF5;
  - Ky genérico.
- [x] 17. `settings.sarma` con escritura condicional, esquema del API, avisos y factores de diseño sobre la c/φ
      global.
- [x] 18. CLI: alias `sarma` y `--sarma-slices`, con su test.
- [ ] 19. Ventana:
  - casilla y grupo de ajustes;
  - tooltips y censos con Sarma, y sus tests;
  - guardas en el PNG, en Interpret y en el informe.

  Sin marcar a 2026-11-17: todo está programado, pero el gris del grupo no tiene test (D463). El changelog de
  0.1.464 declara sin test el dibujo de las caras en el PNG. El gris del grupo tiene test desde 0.1.512
  (`tests/test_sarma_settings_grey_v1512.py`); sigue sin marcar por el dibujo de las caras en el PNG.
- [ ] 20. La suite archivo a archivo, con las exenciones justificadas (soportes), y el A/B de coste.
  Sin marcar a 2026-11-17: la suite y las exenciones están en el §3 del changelog de 0.1.464; el A/B de coste no
  consta en él.
- [x] 21. Documentación: `architecture.md`, `plugins.md`, `guide.py`, README y AGENTS.md.
  - **0.1.464:** puso «10 métodos» en AGENTS.md, `ogr_mcp/guide.py` y los README.
  - **Lo que faltaba:** `docs/architecture.md` seguía diciendo que todo método consume el mismo `Slices`, y
    `docs/plugins.md` no contaba lo que un método nuevo tiene que declarar.
  - **Los dos, el 2026-11-17, al cerrar D357,** por decisión de la propietaria: la entrada con cuñas, y la lista de
    lo que se pregunta al método (menú, `NON_VERTICAL`, `ACCEPTS_SUPPORTS`, el cubo de m-alpha, los ajustes propios
    y los tests que recorren el registro).
- [x] 22. Test `tests/test_sarma_method_v1464.py`. Cubre los criterios de «Integración» de `spec.md`.

## 0.1.465 — Datos por vértice

- [x] 23. Ángulo, c y φ por vértice en `UserPolylineSurface` y en la superficie del motor, por coordenadas.
- [x] 24. API (`sarma` en `user_surface_add` y `surface_evaluate`, y `user_surface_edit`), MCP y
      `herramientas.md`.
- [x] 25. Factores de diseño y avisos de combinaciones inactivas.
- [x] 26. Tabla de ángulo, c y φ en la ventana, desde el menú y desde el menú contextual; rayos punteados.
- [x] 27. Test `tests/test_sarma_vertices_v1465.py`:
  - el 4 y el 5 guardados y por `surface_evaluate`;
  - cada dato mueve el número;
  - las precedencias;
  - F/γ.

## 0.1.466 — D451, la raíz junto a un polo

- [x] Un tramo recto sigue recto: las cuñas se cortan sobre los extremos que resolvió el rebanado vertical.
- [x] Una raíz junto a un polo se dice (`method.sarma_near_pole`, menor |q| de las caras bajo 0,2), con su factor.
- [x] Test `tests/test_sarma_pole_v1466.py`.

## 0.1.467 — Interpret

- [x] 28. Cuñas como polígonos, selección, diagrama de cuerpo libre y filas de cara en la ventana; Sarma cumple
      el contrato de `base_shear_force`. Test `tests/test_sarma_interpret_v1467.py`.

## 0.1.468 — Informe y exportaciones

- [x] 28b. La tabla de cuñas y la de caras del informe, los ajustes de Sarma en él, las caras en el CSV, el API y
      el HDF5; y D453, las unidades de la tabla de dovelas del informe. Una sola fuente de las filas,
      `ogr_core/result_rows.py`. Test `tests/test_sarma_report_v1468.py`.

## 0.1.469 — Herramienta de ángulos y menú contextual del vértice

- [x] 29. Definir y quitar ángulos con el ratón o tecleando, atajos en el vértice y deshacer, con sus tests en
      el lienzo mostrado. Una sola regla de la cara (`wedges.vertex_face`) para el rayo vivo, los guardados y el
      método. Test `tests/test_sarma_angle_tool_v1469.py`.

## 0.1.470 — D452, la regla de la raíz junto a un polo

- [x] Con su plan y su censo (`_auditoria/P9_D452/medir_reglas_d452.py`). La regla elegida (saltar una raíz a menos
      del 1,2 % de un cero de D) la refutó la revisión adversaria: el factor sigue siendo la raíz mayor, y una nota
      (`method.sarma_near_pair`) da la raíz siguiente cuando la mayor lleva la huella del par casi cancelado
      (decisión de la propietaria). D452 sigue abierta hasta Sarma (1979). Test
      `tests/test_sarma_near_pair_v1470.py`.

## 0.1.471 — Ángulos optimizados

- [x] 30. Digitalizar las figuras 1.2 y 1.3 del problema 1, con la lectura declarada
      (`_auditoria/P9_D357/digitalizar_p1_v1471.py` del banco; la medida en `medir_angulos_v1471.py`).
- [x] 31. Optimizador determinista (`sarma/optimize_angles.py`: búsqueda por patrón de 10° a 0,3125° desde la
      mejor política comprobada, con empuje, continuidad, el borde de un pliegue afinado y la guarda de D457);
      `optimized_global` (la crítica, en su sitio, en toda búsqueda y en la puerta de una superficie; con un
      objetivo que no es F, solo si no la empeora) y `optimized_all`; el probabilístico de mínimo global y la
      sensibilidad congelan las caras.
- [x] 32. Test `tests/test_sarma_optimize_angles_v1471.py`:
  - el problema 1 frente a 1,382 / 1,324;
  - F optimizado ≤ el de las políticas;
  - el problema 4 seco frente a un barrido bruto;
  - las reglas, exactas y sobre cuñas reales;
  - determinismo y coste.

## Banco (fuera de git)

- [x] 33. B1:
  - `superficie_publicada` con el bloque `sarma`;
  - `settings.sarma` en los modelos del 4 y del 5;
  - entradas `<esc>__sarma`;
  - re-corrida.
- [x] 34. B2 y B3: `comparar_con: sarma` con su razón, y la columna «OGR Sarma» al final de la comparativa.
- [x] 35. B4 y B5: `d357()` y el re-anclaje de `d122()` y `d123()`; después el procedimiento de cierre.
  - `d357()` da CUBIERTO POR TEST (2026-11-17, con 0.1.471) y, con el árbol de 0.1.460, SIGUE ABIERTO.
  - D357 se cierra con D452 abierta (decisión de la propietaria): D452 sigue hasta Sarma (1979).
- [x] 36. B6: el resto del 03 (1, 6, 7, 8 y 9) comparado o declarado (2026-11-17, con 0.1.471).
  - **El 1:** D459 delante, con la capa débil en y = 0–0,75; cerrada con `d459()`.
  - **El 1, el 6, el 7 y el 8:** se comparan con el Sarma del motor.
  - **El 2, el 3 y el 9:** se declaran. En el 9, ninguna resistencia de cara da su 1,438, y los métodos verticales
    quedan un 10 % abajo en el mismo círculo.

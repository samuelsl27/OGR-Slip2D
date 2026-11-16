# OGR Slip2D v0.1.465

**Los datos de Sarma por vértice (D357, cuarta de las siete versiones).** Una superficie no circular del usuario
(`UserPolylineSurface`) lleva ahora, en sus vértices interiores, el ángulo de la cara de Sarma y su c y φ. El dato va
de punta a punta: el archivo, el motor, el API, el MCP y una tabla en la ventana. Así el 4 y el 5 publicados,
guardados como superficies del usuario, dan lo publicado por cualquier puerta. Ningún factor de los diez métodos sin
datos por vértice cambia, y la huella de una polilínea sin datos no se mueve.

Por las decisiones de la propietaria (2026-11-16):
- **el menú contextual del vértice va en 0.1.467,** con la herramienta de ángulos. En esta versión la tabla se abre
  desde Superficies → «Datos de Sarma por vértice…»;
- **un dato que no llega a la superficie calculada se dice con una nota,** y se calcula sin él: un vértice que corta la
  grieta, uno que Optimize mueve, o una superficie que recorta una capa débil;
- **la c y la φ de una cara van siempre juntas.** El ángulo va aparte.

## 0. Lo que se encontró

### El censo, antes de escribir

Dos exploraciones (solo lectura), sobre 0.1.464:
- **la copia de diseño se rehace con `Project.from_dict(project.to_dict())`:** un dato que no pase por `to_dict` se
  pierde en cada cálculo con norma;
- **los vértices cambian de tres formas,** y por coordenadas el dato sobrevive a las tres:
  - `checked_points` invierte una polilínea dibujada de derecha a izquierda, sin tocar las coordenadas;
  - `snap_polyline_ends` mueve solo los extremos;
  - la grieta quita vértices y añade extremos nuevos;
- **`Wedges.unused_vertex_data` existía desde 0.1.463, pero nadie lo leía;**
- `test_f3b_ops_v1201` fija las acciones mapeadas, y el MCP pide una fila en `herramientas.md` para cada herramienta.

### Al escribir

- **La copia de diseño dividía dos veces o ninguna.** Al principio `apply_design_factors` dividía la c/φ de cada vértice
  sobre la copia. Pero una superficie que llega a una puerta (`evaluate_surfaces`, el `surface_evaluate` del API) trae
  sus datos colgados, y esa copia no los ve: salían sin dividir. Además, el primer test dividía dos veces una polilínea
  guardada. Ahora se divide en un solo sitio, donde el método los lee (`SarmaNonVertical.wedges_for`, sobre una copia
  que dice serlo, con `factored_face_strength`), y el informe solo los nombra.
- **Una polilínea guardada no da los bits de la puerta:** 7e-8 de diferencia en el 4, porque la corrida lleva antes sus
  extremos al terreno (la cabeza, (128, 67,6737), queda 1e-4 por encima). El test la compara con la herramienta del
  banco a 1e-6, no al bit.
- **El API redondea F a seis decimales:** su test va a 1e-6.
- **Un literal «kPa» en la tabla rompía el presupuesto de cadenas sin envolver.** La unidad sale ahora del sistema de
  unidades del proyecto (`Quantity.SHEAR_STRENGTH`).
- **Un error propio al editar `main_window.py`:** el decorador `@undo_step("Delete user surfaces")` pasó del gestor de
  polilíneas al manejador nuevo. Se devolvió a su sitio.

### La corrida rápida (`--fast --jobs 4`)

7256 casos; fallaron 6, todos de esta versión:
- faltaban el ejemplo de deshacer de `user_surface_edit` (`test_api_undo_v1194`) y el 118 → 119 de `test_f3b_ops_v1201`;
- los nombres de los dos pasos de deshacer nuevos no tenían español (los ven dos censos);
- la tabla enseñaba el texto de la excepción tal cual, y el censo de `test_edit_messages_v1434` lo prohíbe;
- el informe de diseño nombraba la fila de un vértice con `"Sarma (%g, %g)" % …`, una frase sin código que el censo de
  `test_stat_notes_v1353` no admite. La fila se llama «Sarma» y lleva el vértice en `vertex`, como dato.

### La revisión adversaria (un agente)

Encontró dos fallos altos y seis medios, todos de esta versión, y todos arreglados:
- **H1, el dato se perdía en tres puertas.** Colgaba de la `SlipSurface` como atributo suelto, y lo perdían las tres
  puertas que rehacen la superficie:
  - la copia de los casos de una capa débil (`weak_layers._own_copy`, con `dataclasses.replace`);
  - la semilla de la estadística y la sensibilidad (`probabilistic._rebuild_surface`, por `to_dict`);
  - el paseo de Optimize (`optimize._walk._make`, que construye superficies nuevas).

  En el 5, F pasaba de 1,08827 a 1,13722 sin decir nada. Ahora `vertex_angles` y `vertex_strength` son **campos** de
  `SlipSurface`, en `to_dict` y `from_dict` solo si los hay, y Optimize los lleva a cada superficie del paseo.
- **H2, dos tests existentes:** son los dos primeros fallos de la corrida rápida.
- **M1, una c/φ de cara mala abortaba todos los métodos.** La copia de diseño divide siempre la c/φ de cara global (una
  puerta puede correr Sarma sin tenerlo en la lista), y un `None` o un texto reventaba en `float()` el cálculo entero
  con norma, con Sarma o sin él. Ahora solo se dividen números. Un valor que el método no admite es su propio rechazo
  (`sarma_setting_problem`, con nota), y los demás métodos calculan. Además, el comentario de
  `test_sarma_method_v1464.py` («solo entonces se divide») era falso, y un test fija ahora que se divide siempre.
- **M2, una fila mala de un archivo costaba la polilínea entera.** Un archivo editado a mano con una fila mala:
  - `slip_surface_of` lo rechazaba para todos los métodos, con la nota de una superficie que no avanza en x;
  - el informe de diseño reventaba en `float("abc")`;
  - el dibujo de los rayos reventaba con un ángulo `"abc"`;
  - `"sarma": 5` daba un `TypeError` que impedía abrir el archivo.

  Ahora la regla se aplica dato a dato (`split_vertex_data`). La corrida toma los buenos y nombra los demás con una nota
  por polilínea (`search.user_polyline_sarma_refused`). El informe y el lienzo leen solo los buenos, y el lector ignora
  lo que no es una lista de filas.
- **M3, dos tolerancias de casado distintas.** La regla casa a una milmillonésima del ancho, y el constructor de cuñas a
  la rejilla del modelo. Dos vértices a menos de una celda, cada uno con su dato válido, caían en el mismo punto, y el
  `ValueError` «two data for the vertex» abortaba la corrida. Ahora gana el más cercano y el otro va con los no usados,
  que se dicen. `test_sarma_wedges_v1463` fijaba el error, y pasa a fijar la regla nueva en los dos órdenes. El umbral
  de una cara horizontal es ahora uno solo (`HORIZONTAL_FACE_RAD`, en el núcleo, que lee `angles.upward`): la regla
  rechazaba solo 0 y 180 exactos, y el método 1e-12 rad alrededor.
- **M4, Aceptar sin editar reescribía los datos.** La tabla enseña con `%g` y en las unidades del usuario, y releía lo
  que enseñaba: un 80,123456789 volvía como 80,1235. Una celda cuyo texto no cambió devuelve ahora el valor guardado.
- **M5, la tabla enseñaba la frase inglesa del núcleo** tras un prefijo en español. `NotASurface` lleva ahora `reason` y
  `where`, y la ventana dice cada motivo en su idioma (`user_surface_refusal_text`). Una celda que no es un número se
  dice aparte, con su fila.
- **M6, la nota de datos sin aplicar leía solo la superficie crítica.** Un dato que la grieta cortaba en otra polilínea
  no se decía. Ahora hay también una nota por polilínea (`search.user_polyline_sarma_unused`).
- **Los bajos:**
  - en el API, un `sarma` que no es una lista de filas da `InvalidArgument`, en `user_surface_edit` y en
    `surface_evaluate`;
  - un `True` ya no se acepta como ángulo de 1°;
  - `user_surface_edit` comprueba antes la geometría guardada (`checked_points`);
  - la descripción MCP de `surface_evaluate` menciona el bloque `sarma`;
  - en `wedges.py`, la cuenta de puntos de un anillo va ahora antes de `Polygon(ring)`, porque Shapely revienta con
    menos de tres. **No lo reproduje:** con una sola cuña el talud del test da cuñas válidas. El orden se corrige
    igual, y no lleva test.
- **La estadística no lo decía.** El plan prometía avisar de que la c/φ dada a mano no se muestrea, y no estaba hecho.
  Ahora lo dicen Global Minimum, Overall Slope y la sensibilidad (`stat.sarma_given_fixed`), con Sarma en la corrida y
  una c/φ dada en los ajustes o en un vértice.

## 1. El cambio

- **El núcleo** (`ogr_core/geometry/user_polyline.py`):
  - `UserPolylineSurface.vertex_data`: `{(x, y): {"angle", "c", "phi"}}`, por las coordenadas exactas de un vértice
    interior;
  - en el archivo, `"sarma": [{x, y, angle, c, phi}]`, solo si hay alguno;
  - **una sola regla:** `checked_vertex_data` (estricta) y `split_vertex_data` (los buenos y los rechazados). La
    preguntan el API, la ventana, la corrida, el informe y el lienzo;
  - `NotASurface` lleva `reason` (de `VERTEX_DATA_REASONS`) y `where`; también `HORIZONTAL_FACE_RAD` e
    `is_face_angle`.
- **El motor:**
  - `SlipSurface.vertex_angles` y `vertex_strength`, campos;
  - `slip_surface_of(user, refused=)`;
  - `SarmaNonVertical.wedges_for` los lee, de la superficie o de la base de un recorte de capa débil, y divide la c/φ por
    los coeficientes en la copia de diseño;
  - Optimize los lleva;
  - `_by_vertex` da el más cercano.
- **Las notas:**
  - `method.sarma_vertex_data_unused`, sobre la superficie del resultado;
  - `search.user_polyline_sarma_refused` y `search.user_polyline_sarma_unused`, por polilínea y solo con Sarma;
  - `stat.sarma_given_fixed`.

  Todas llevan su español y su muestra.
- **El diseño:** la c/φ de cara global se divide siempre en la copia, solo si son números. La de un vértice se divide
  en `wedges_for`. El informe nombra las dos como «Sarma» (la de un vértice, con `vertex`) solo con Sarma en la lista.
- **El API y el MCP:**
  - `user_surface_add` y `surface_evaluate` aceptan el bloque `sarma`;
  - `user_surface_edit` es nuevo: cambia los datos de una polilínea guardada en un paso de deshacer. Va en el grupo
    «search» del MCP, con su fila en `docs/mcp/herramientas.md`;
  - el inventario pasa de 118 a 119 acciones mapeadas.
- **La ventana:**
  - Superficies → «Datos de Sarma por vértice…» (`surf_polyline_sarma`), en gris con su motivo sin tipo no circular o
    sin polilínea;
  - con varias polilíneas, se elige una;
  - la tabla (`ogr_gui/dialogs/sarma_vertex_dialog.py`) tiene x e y de solo lectura, ángulo, c en las unidades del
    proyecto y φ. Se acepta en un paso de deshacer, y rechaza con su motivo sin cerrarse;
  - en el lienzo, rayos punteados, un solo `QPainterPath` por superficie (D395).

## 2. El test

`tests/test_sarma_vertices_v1465.py`, 19 casos; el archivo tarda 4,8 s con el arranque. Comprueba:
- **el 4 y el 5 publicados** como superficies del usuario, por la puerta, la polilínea guardada y el API: el constructor
  al bit (puerta), lo publicado a ±1 % y la herramienta del banco a 1e-6;
- **la regla 7:** el ángulo, la c y la φ de un vértice mueven F cada uno, y se cumplen las precedencias;
- **el archivo:** sin datos no aparece la clave, la ida y vuelta conserva los datos, también dibujada al revés, y cada
  dato malo se rechaza con su motivo y su vértice;
- **la copia de diseño:** F_d = F/γ por la puerta y por la polilínea guardada (Frank et al. 2004), y el informe;
- **la grieta:** la nota del resultado y la de la polilínea;
- **lo de la revisión:**
  - las tres puertas, al bit;
  - Optimize: lleva los datos y dice los que movió;
  - una fila mala: F de las otras filas, su nota, el informe y el lector;
  - la c/φ global dividida siempre y nunca un fallo;
  - la nota de la estadística;
  - Aceptar sin editar;
  - el motivo en español;
  - el lienzo con datos malos;
  - el API con basura.

Mutantes: `_auditoria/P9_D357/mutants_v1465.py` del banco, con su log (`mutants_v1465_0.1.465.log`). Son 28 y no vive
ninguno. Incluye el de dos datos en un vértice, que muere en `test_sarma_wedges_v1463`.

## 3. La suite

- `test_sarma_wedges_v1463`: dos datos en un vértice ya no son un error; gana el más cercano, en los dos órdenes.
- `test_api_undo_v1194`: el ejemplo de `user_surface_edit`.
- `test_f3b_ops_v1201`: 118 → 119.
- `test_search_notes_v1349` y `test_stat_notes_v1353`: las muestras de las tres notas nuevas.
- `test_sarma_method_v1464`: un comentario falso, corregido.

## 4. Verificación

- **La suite entera, `--jobs 4`, una vez tras la revisión:** 7928 casos; pasan 7927 y uno queda saltado, sin fugas ni
  tramos muertos. La última serie en verde es de hace 43 commits.
- **El test nuevo:** 19 de 19. **Mutantes:** 28, ninguno vivo.
- **Los README:** 7908 → 7927 tests.
- **Pruebas a mano para la propietaria:**
  - la tabla desde Superficies, con una y con varias polilíneas;
  - los rayos punteados;
  - un cálculo del 4 con su ángulo en el quiebro;
  - el motivo de un dato malo en español.

## 5. Lo que queda

- **Optimize con datos por vértice.** Por decisión de la propietaria, un vértice que el paseo mueve pierde su
  dato, y la nota lo dice. Pero entonces el paseo compara superficies con datos y sin ellos. En el 5, 40 pasos llevan F
  de 1,0883 a 1,0575, y no está separado qué parte es geometría y qué parte es perder datos. La alternativa es que el
  dato siga al vértice (por su orden) durante el paseo. La propietaria decidió dejarlo así (2026-11-16); queda anotado
  en la ficha D357 para revisarlo con la herramienta de ángulos de 0.1.467.
- **Dos notas para lo mismo.** Con la superficie del resultado siendo una polilínea del usuario, su dato no aplicado
  sale dos veces: la nota del método y la de la polilínea. Se dejó así a propósito, porque la de la polilínea es la
  única que llega a las que no son el resultado.
- **El banco, tras el commit:**
  - B1: el 4 y el 5 con sus datos en `superficie_publicada`, `settings.sarma` en sus modelos, las entradas
    `<esc>__sarma` y la re-corrida del 03;
  - B2 y B3: `comparar_con: sarma` y la columna «OGR Sarma»;
  - el progreso de la ficha D357.
- Interpretar con cuñas: 0.1.466. La herramienta de ángulos y el menú contextual del vértice: 0.1.467.

# OGR Slip2D v0.1.412

**Un Área mínima 0 declarada apaga el filtro de área; la casilla sin marcar sigue siendo el valor por defecto de
la búsqueda, y el diálogo dice cuál es (D369).**

Es la primera de la tanda P8n (D369, D350, D349, D353, D354), y la propietaria eligió la opción A de la ficha el
2026-11-02. Ningún modelo con `min_area` null o positivo cambia: el FS del talud de ejemplo sigue en
1,0914331494631124 con Bishop, y ningún `.ogr` del banco declara 0 (barridos 28 256: 16 879 null y 11 377
positivos).

## 0. Lo que se encontró

- **La puerta.** `_search_common` (`ogr_slip2d/analysis_runner.py`) entregaba a todas las búsquedas
  `s_search.min_area or _MIN_AREA_FALLBACK.get(search_method, 1.0)`. El `or` lee el 0 como «sin declarar».
  - Un 0 declarado llegaba como 1 a la rejilla, como 2 a Block y como 0,5 a Auto Refine, igual que un null.
  - 1e-9 pasaba tal cual, y un −1 apagaba el filtro porque ningún área es menor.
  - Es la única puerta: `build_evaluator`, el de la estadística, pasa por el mismo `_search_common`.
- **El 0 entraba por cuatro sitios:** el diálogo (rango de 0 a 1e6), el API (que no acotaba `search.min_area` y
  aceptaba negativos), un `.ogr` y un script. Era la regla 7: un ajuste que se podía escribir y no hacía lo que
  decía.
- **El resultado que mueve:** el círculo rozante de D346 (radio 5, que entra 0,1 m en la cara del talud de ejemplo;
  unos 0,13 m² de masa):
  - con null no da resultado, y la nota dice «Área mínima 1 (valor por defecto de la búsqueda)»;
  - con 0 daba lo mismo. Ahora da FS 11,84305595821084, el mismo que con 1e-9, un valor que la puerta siempre
    respetó.
- **La nota de D346** (`_user_surface_filters`) decidía «por defecto» con `declared or project is None`, así que
  compartía la misma lectura del 0. Y con un negativo habría dicho «Área mínima −1», que no filtra nada.
- **La fila del diálogo sin marcar** enseñaba un 0,5 fijo, cuando la rejilla filtra a 1 y Block a 2.
- **Cuatro tests de la suite ya escribían `min_area = 0.0` creyendo que apagaba el filtro**, y filtraban a 2 o a 1:
  - `test_ground_refusals_v1259.py:271`;
  - `test_slope_limit_refusals_v1261.py:281`, `:327` y `:431`;
  - y, en el banco, `d257()` del 02.
  - Medido antes de tocar nada (regla 6), con un A/B en el mismo proceso de la puerta vieja y la nueva sobre esos
    dos archivos. De las 17 búsquedas, las 8 de Block y de Path dan lo mismo.
  - Las tres rejillas de `TestAParallelGridSaysWhatASequentialOneSays` pasan de 461 válidas y 78 inválidas a 471 y
    68: son diez superficies diminutas que quitaba el filtro de 1 m². El FS crítico es el mismo.
  - Los 26 tests pasan con las dos puertas, porque comparan la serie con el paralelo, que se mueven igual. No se
    toca ninguno: ahora miden lo que siempre dijeron medir.
- **Camino equivocado del A/B, dos veces.**
  - El script sin la guarda de `__main__` se colgó: los trabajadores `spawn` del pool lo vuelven a ejecutar, la
    trampa de siempre.
  - Con la guarda, se volvió a colgar. Esa vez, la causa era envolver `run` como atributo de la instancia con un
    cierre local: la búsqueda en paralelo ya no se podía serializar para el pool. Envuelto en la clase, terminó.

## 1. Qué cambia

- **`ogr_slip2d/analysis_runner.py`:**
  - dos funciones públicas nuevas:
    - `effective_min_area(search_settings, search_method=None)` devuelve lo declarado si no es None, y si lo es, el
      valor por defecto de la búsqueda;
    - `min_area_fallback(search_method)` acepta el id o el miembro de `SearchMethod`;
  - `_search_common` usa `effective_min_area`, con el porqué escrito.
- **`ogr_slip2d/search.py`, `_user_surface_filters`:**
  - el fragmento de área solo sale con un filtro mayor que 0;
  - «por defecto» se dice solo cuando el modelo no declara nada (`declared is None`).
- **`ogr_api/settings_schema.py`:** `search.min_area` en `_BOUNDS` con mínimo 0. El API rechaza −1 con «search.min_area
  must be at least 0, got -1.0.».
- **`ogr_gui/dialogs/grid_dialogs.py`:**
  - la fila sin marcar enseña `min_area_fallback` de la búsqueda elegida: 1 con la rejilla, 2 con Block, 0,5 con
    Auto Refine;
  - se actualiza al cambiar de búsqueda y al desmarcar la casilla;
  - un valor marcado no lo pisa el cambio de búsqueda;
  - la casilla y la caja llevan una ayuda: «Sin marcar, se aplica el valor por defecto del método de búsqueda
    elegido. Con 0 no se descarta ninguna superficie.».
  - La regla se pregunta al motor, no se copia.
- **`ogr_gui/i18n/__init__.py`:** el castellano de esa ayuda.
- **`tests/test_min_area_zero_v1412.py`**, nuevo, con 16 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_min_area_zero_v1412.py`:**
  - **regla 7:** el círculo rozante con 0 da su factor (el mismo que con 1e-9, ≈ 11,8431) y con null no;
  - el FS crítico del ejemplo es el mismo con 0 y con null;
  - un 0 llega como 0 a la rejilla, a Block y a Auto Refine, y a la estadística (`build_evaluator`); un null llega
    como 1, 2 y 0,5;
  - la nota: null dice «por defecto», un valor declarado se dice sin la etiqueta, y 0 o un negativo no dan
    fragmento. En una corrida real con 0 no hay nota;
  - el API rechaza −1 con el rango y acepta 0;
  - el diálogo, en los términos del primer punto de la sección 1.
- **La discriminación,** con el árbol de 0.1.411 (`git worktree` de a9a59ec, el test copiado dentro y sin el buscador
  editable): fallan 9 de 16. Los 7 que pasan son guardas: el null, un valor declarado y el guardado del diálogo.
- **`d369()`** da SIGUE ABIERTO con 0.1.411, por comportamiento y con el test presente, y CUBIERTO POR TEST con
  0.1.412.
- **Los vecinos:** las notas de las búsquedas y de las superficies del usuario, los ajustes, los diálogos, el foco
  en todas las búsquedas, la estadística, los rechazos del terreno y de los límites, las traducciones, el castellano
  de la interfaz, el esquema del API y el servidor MCP: 384 de 384.
- **La suite entera con `--jobs 4`:** **7018 de 7018, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 32,8 min.
  - La sesión de OGR-FEM2D estaba calculando a la vez, así que el reloj no es una medida.
  - La serie no toca: 13 commits desde la última.
  - El runner avisa de `test_discrete_function_v1246.py` (91,3 s), que no es de esta versión: la lista de lentos no
    se toca.
- **El banco:**
  - `verificar_cierres.py` entero en la raíz da 122 comprobaciones con 0 bajadas;
  - el del 02 entero da 242 con 0 bajadas, `d257` incluida (40 candidatas en metros y en milímetros);
  - D369 se cierra: instantánea, retirada, `PAQUETES` podado, cadena tachada, prompts y auditorías con 0 ERROR en la
    raíz y en el 02.

## 3. Qué falta

- Probar el diálogo a mano: la fila sin marcar al cambiar de búsqueda y la ayuda. Va en la próxima prueba de la
  interfaz.

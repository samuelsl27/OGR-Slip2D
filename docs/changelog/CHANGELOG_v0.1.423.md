# OGR Slip2D v0.1.423

**Una variable aleatoria hidráulica ya no pasa por una que mueve el factor de seguridad (D372).**
- Si **todas** las variables activas son hidráulicas, Global Minimum, Overall Slope y la sensibilidad se niegan antes
  de sortear nada, con su código (`stat.vars_hydraulic_only`). No sale ningún resultado, en vez de una dispersión nula
  publicada como si fuera una medida.
- Si van **mezcladas** con otras, la corrida avisa y las nombra (`stat.vars_hydraulic`), y sigue como antes. La
  sensibilidad no las barre y marca cada una (`stat.var_hydraulic`). La ventana de estadística las llama hidráulicas, y
  no «ya no está en el modelo».

Es la primera de la tanda P5c. La ficha sale de la sonda S1 de la auditoría del cómputo (`AUDITORIA_COMPUTO_v0.1.377.md`
§10, A1). **Decisión de la propietaria (2026-11-04): opción A, decirlo y negarse.** Resolver la filtración en cada muestra
(la opción B) es una funcionalidad aparte, con su propia ficha.

Ningún número cambia.

## 0. Lo que se encontró

- **El mecanismo, comprobado otra vez en este árbol.**
  - Una variable HYDRAULIC escribe `material.hydraulic.<param>` (`random_variables.set_value`).
  - Fuera de la filtración, nada lo lee. Un `grep "\.hydraulic\b"` sobre `ogr_slip2d` y `ogr_core` solo encuentra:
    - el propio muestreador;
    - la serialización del material;
    - los datos del MEF (`ogr_core/fem/seepage_data.py`).
  - El equilibrio límite toma la presión del campo **guardado**, y ningún bucle de muestras (GM, OS, sensibilidad) vuelve
    a resolver la filtración. `clone_project` copia el campo tal cual.
- **Medido en la auditoría** (S1, 0.1.377): Ej_1 con Gardner y el permanente del MEF, GM con N = 20 sobre el círculo de
  referencia.
  - Con `ks` aleatoria: **un único factor en las 20 muestras** (0,836185679621466), sin fallos ni notas.
  - Con la cohesión como control: 20 valores distintos.
- **La ventana lo hacía peor.** La sensibilidad dibujaba la curva plana de `ks` y la ponía la **última** de la
  clasificación, «ΔFoS 0.0000». Es decir, decía que el agua es lo que menos importa. Lo enseña el test nuevo en el árbol
  anterior: «Mat1 — cohesion: ΔFoS 0.3456 | Mat1 — hydraulic ks: ΔFoS 0.0000».
- **Por qué las hidráulicas mezcladas se siguen sorteando.** `sample_variables` reparte un solo generador entre todas
  las columnas, una vez por clave y en orden. Si se quitara la columna hidráulica, las demás se volverían a sortear y se
  moverían números que esta versión no debía mover. Siguen en `result.variables` y en `result.samples`, y el aviso dice
  que no llegan al factor.

## 1. Qué cambia

- **`ogr_slip2d/stat_messages.py`:** tres códigos nuevos: `stat.vars_hydraulic_only`, `stat.vars_hydraulic` y
  `stat.var_hydraulic`.
- **`ogr_slip2d/probabilistic.py`:**
  - `_hydraulic_keys(variables)`, con el porqué en su docstring. Cuando exista un análisis que resuelva la filtración
    por muestra, la excepción va ahí.
  - `_hydraulic_variables_stop(result, variables)`, en el estilo de `_stale_variables_stop`: error y parada si todas son
    hidráulicas, y aviso si solo lo son algunas.
  - `run_global_minimum` y `run_overall_slope` lo llaman justo después de comprobar que hay variables, antes de sortear.
    Overall Slope se para antes de la primera búsqueda.
- **`ogr_slip2d/sensitivity.py`:**
  - el mismo control antes del bucle de métodos;
  - una variable hidráulica no se barre y lleva `vs.note = stat.var_hydraulic`, el patrón de `VAR_ORPHAN` (D91). Así no
    se dibuja ni entra en la clasificación.
- **`ogr_gui/statistics_window.py`:** las variables sin barrer se nombran por su motivo: «sin barrer, ya no está en el
  modelo» o «sin barrer, hidráulica (la filtración no se vuelve a resolver)».
- **`ogr_gui/i18n/__init__.py`:** el castellano de los tres códigos y de la etiqueta de la ventana.
- **`ogr_mcp/guide.py` y `docs/mcp/herramientas.md`:** una línea sobre las variables hidráulicas.
- **`tests/test_hydraulic_variables_v1423.py`,** nuevo, con 10 tests.
- **`tests/test_stat_notes_v1353.py`, cambiado a propósito:**
  - una lista `_LATER` con los tres códigos nuevos y su inglés, el patrón de `test_search_notes_v1349` y
    `test_seepage_run_notes_v1352`. `_V1352` sigue siendo el inglés de 0.1.352 byte a byte;
  - `_hydraulic_variables_stop` entra en el censo `_CODED`.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_hydraulic_variables_v1423.py`,** 10 tests, 6 s con el arranque de Qt:
  - **todas hidráulicas:**
    - GM, OS y sensibilidad acaban con `stat.vars_hydraulic_only` bajo `error`, sin `by_method`;
    - OS con una fábrica que revienta si se la llama, así que se para antes de buscar;
    - el castellano por `note_text`;
  - **mezcladas:**
    - el aviso nombra `ks` y no la cohesión, y está también en `note_lines`;
    - la cohesión sigue moviendo el número;
  - **dos identidades, recalculadas y no congeladas:**
    - la corrida con cohesión y `ks` da, valor a valor, la misma que con la cohesión sola a la misma semilla;
    - la misma corrida mezclada con el control parcheado a nada da los mismos factores (A/B en el mismo proceso);
  - **la sensibilidad:**
    - no barre `ks`, la marca y no la clasifica;
    - la curva de la cohesión es la de la corrida sin `ks`;
  - **la ventana**, en castellano, dice «hidráulica» y no «ya no está en el modelo».
- **Discriminación.** En el árbol anterior (worktree de 4dfcd0b, sin el buscador editable, con la ruta del árbol
  comprobada) fallan 9 de los 10:
  - 8 por comportamiento: sin error ni aviso, `ok` verdadero, y la curva plana clasificada;
  - 1 por importar el código nuevo.
  - Pasa la premisa (las dos corridas coinciden), que vale en los dos árboles.
- **Vecinos:** `test_stat_notes_v1353`, `test_random_variable_target_v1164`, `test_partial_method_loss_v1170` y
  `test_sensitivity_v136`.
- **Suite entera** con `--jobs 4`: 7113 en verde, 1 saltado, 0 fallos, sin fugas ni tramos muertos.
  - Antes de lanzarla, `TextInputHost.exe` volvía a girar un núcleo entero (4,7 s de CPU en 5 s; 280 000 s acumulados
    desde el 28-10). Se cerró a mitad de la suite con permiso de la propietaria, junto con cuatro trabajadores `pythonw`
    huérfanos del 2-11.
- **Banco de pruebas del cómputo**, lote `version`: los 23 casos idénticos a 0.1.377, K19 y K20 incluidos (las dos
  estadísticas del banco, Global Minimum, Overall Slope y la sensibilidad).
- **Las once probabilísticas del banco** (028 y 036), corridas otra vez con `correr_probabilistico.py`:
  - comparadas por ruta contra `Evaluaciones/0.1.411` (donde están las de 0.1.251), con el comparador de
    `_auditoria/P5c_0423/` (copia del de `P5_0236`, que además cuenta la igualdad bit a bit);
  - salen **idénticas**: 19 números en cada una del 028 y 31 en la del 036, ninguno distinto, tampoco bit a bit, y
    ninguna clave sin pareja;
  - 1725 s el lote, 1313 s la del 036, que en 0.1.251 tardaba 2265.
- **`d372()`**, nueva en el `verificar_cierres.py` de la raíz, con el modelo de S1 en vivo (Ej_1, Gardner, el
  permanente del MEF con 400 elementos y GM con N = 20): **CUBIERTO POR TEST**.
  - `ks` sola se niega con `stat.vars_hydraulic_only` y no da factores.
  - Con la cohesión y `ks`, avisa con `stat.vars_hydraulic` y da 20 factores distintos, iguales a los de la cohesión
    sola.
  - Discriminada con el motor de 0.1.422 (el VC se carga antes y se comprueba la ruta del motor): **SIGUE ABIERTO**.
    `ks` sola da `ok=True` y 20 factores con un único valor distinto, sin error ni aviso. Es la medida de S1.
- **El VC de la raíz entero:** 134 comprobaciones, todas cierran, y 0 bajadas.
- **El del 02 en seco:** 242 de 242 veredictos iguales a los archivados, comparados por la primera línea de cada ficha,
  sin bajadas.
- **El cierre del banco:** `Evaluaciones/0.1.423` de la raíz, D372 retirada al índice, podada de `PAQUETES` y tachada
  en la cadena de P5. `auditoria_invariantes.py` da 0 ERROR en la raíz y en el 02.

## 3. Lo que queda

- **La opción B** (resolver la filtración en cada muestra cuando una variable hidráulica está activa) es una
  funcionalidad nueva. Pide una solución del MEF por muestra y validarla contra una referencia externa (regla 1) antes
  de publicar un número.

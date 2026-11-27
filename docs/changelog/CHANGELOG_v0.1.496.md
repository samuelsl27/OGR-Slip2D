# OGR Slip2D v0.1.496

**D435: una superficie que aflora fuera de los Límites del talud es el −113 de la referencia.**
Hasta esta versión, el censo la contaba como −101. Dos comentarios decían que la referencia no
tiene código para ese rechazo, y su ayuda sí lo tiene. No cambia ningún factor ni el recuento de
válidas.

## 0. Lo que se encontró

- **La ayuda de la referencia** («Summary of Error Codes», leída el 2026-11-27) define el −113
  así: la superficie corta el contorno exterior fuera de los Límites que definió el usuario, pero
  dentro de los límites por defecto. Si queda fuera también de estos, se aplica el −101. Los
  límites por defecto son los extremos del perfil del terreno.
- **La opción B se sostiene por construcción.** Una superficie que rechazan los Límites siempre
  corta el terreno dentro del perfil. Un círculo que no lo corta en ningún punto se rechaza antes:
  como `misses_ground` o, si es de un centro sin radio válido, como −1000 (D434).
  - Medido en Ej_1 con Límites de 30 a 90: ninguno de los 611 rechazos por los Límites de 0.1.494
    corta el terreno fuera de [0, 120]. El test nuevo lo comprueba círculo a círculo.
- **Por qué los Límites cambiaban `misses_ground` (de 231 a 770) y `leaves_external` (de 183 a
  1).** Con los Límites de 30 a 90, en los centros con x ≥ 92 el punto más cercano de la
  superficie del talud es el límite (90, y). Ahí `d_min == d_max`, y la rejilla emite once veces
  el mismo radio, que solo toca el talud en ese punto. Es la regla de la horquilla de v0.1.88, la
  misma que en la columna x = 120 sin Límites.
  - De esos 114 centros salen 770 círculos que no cortan el terreno y 484 que lo cortan fuera de
    los Límites. Desde D434, los 1254 son −1000.
  - Que la referencia haga lo mismo con unos Límites movidos hacia dentro no está medido. El
    docstring de `_radius_bracket` ya lo dice: todos sus modelos de prueba tienen los Límites en
    su posición automática.
- **Visto de paso, sin tocar.** Un círculo con el centro por debajo del terreno, como el (40, 30)
  de R 20,12, corta el terreno en 37,8 y 42,2. La base de sus dovelas va de 19,9 a 60,1 por el
  arco inferior, y los Límites lo rechazan por los extremos de esa base, no por sus cortes. Es la
  regla de pertenencia de D50, que la ficha pide no mover.
- **El banco.** Ningún informe del 02 publica un −113. El 109 de D263 cuenta 3804 rechazos por los
  Límites en su Path Search (sin re-medir en esta versión).

## 1. Qué cambia

Opción **B**, decisión de la propietaria del 2026-11-27: todo rechazo por los Límites del talud es
−113.

- `ogr_slip2d/interpretation.py`:
  - `ERROR_SLOPE_LIMITS = -113` en `ERROR_CODES`, que lista la vista `error_codes` del agente;
  - la fila `outside_slope_limits` de `COUNTED_REJECTIONS` pasa de `ERROR_OTHER` a
    `ERROR_SLOPE_LIMITS`;
  - el párrafo de D263 ya no dice que la referencia no tiene código.
- `ogr_slip2d/search.py`: sale «has no code of its own there» del comentario de
  `REFUSED_OUTSIDE_SLOPE_LIMITS`, que ahora cita el −113 y explica por qué todos sus rechazos
  caen dentro de los límites por defecto.
- Las búsquedas Path y Block cuentan en el mismo contador, así que también salen como −113.

## 2. Tests

- `tests/test_slope_limits_code_v1496.py` (nuevo, 3 tests), sobre Ej_1 con Límites de 30 a 90:
  - −113 = los 127 rechazos por los Límites que quedan tras D434, y ningún −101;
  - la premisa de B, círculo a círculo: todos cortan el terreno dentro del perfil;
  - la vista del agente y el comentario.

  Contra 0.1.495 fallan los tres. El de la premisa fallaba por la afirmación de más que se quitó
  (ver «visto de paso»), y ahora pasa en los dos árboles: es una premisa, no el arreglo.
- Cambiados a propósito:
  - `tests/test_slope_limit_refusals_v1261.py`: la Block Search rechazada entera por los Límites
    da `{-113: 40}`;
  - `tests/test_results_query_user_surfaces_v1442.py`: los once rechazos de la rejilla baja salen
    como −113. `_no_evaluation` reparte los contadores por código (−101, −103, −113, −1000). La
    referencia medida en 0.1.441 se compara con el único cambio declarado, `_as_of_0_1_496`, que
    renombra −101 a −113 en el censo.
- Las áreas del censo, de la rejilla, de Interpretar y de la API: 696 de 696 en verde.
- Banco: `d435()` en el `verificar_cierres.py` de la raíz da **CUBIERTO POR TEST** (`{-1000: 1254,
  -113: 127, -111: 261, -103: 1}`). `d403()` sigue cubierto.

## 3. Lo que no se ha probado aquí

- Las huellas de `_auditoria/COMPUTO/bench/` de D434 y D435, y la suite entera: van al cierre de
  la tanda, después de este commit.

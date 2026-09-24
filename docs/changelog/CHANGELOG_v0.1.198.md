# OGR Slip2D v0.1.198

**Segundo bloque de correcciones antes de F3: *Change Slope Angle*
rehecha.** Ahora hace lo que su nombre dice:

- eliges con el ratón el **pie** y la **coronación** del talud;
- cambia el ángulo global de la cara entre ambos, **y solo el de la cara**;
- la hay en la interfaz y la tiene el agente (`slope_angle_change`).

Antes giraba el contorno exterior entero, y además su modo en el lienzo no
se activaba nunca.

De paso apareció que ***Insert Vertex* no ha funcionado nunca** en la
historia pública del programa: a `_pick_edge` le faltaba la línea `def`
(§3).

---

## 1. Qué hacía y qué hace

**Antes** (`transforms.change_slope_angle`), medido en la demo al pedir 30°:

- la cara quedaba a **60°**;
- la base, la coronación y todo lo demás del exterior quedaban inclinados
  15°: giraba el contorno ENTERO alrededor de un pivote tecleado, y el
  sentido del giro dependía de hacia dónde miraba el talud;
- la cara la adivinaba: «la arista más empinada»;
- el modo `ToolMode.CHANGE_SLOPE_ANGLE` existía, pero nada entraba en él, y
  la rama que lo atendía era inalcanzable.

**Ahora** (`ogr_core/geometry/slope_angle.py`), como describe la
documentación de referencia:

- **La cara** es el tramo del exterior entre dos vértices, el pie y la
  coronación, por la superficie del terreno (`ground_surface`), nunca por la
  base.
- **El ángulo global** es el de la cuerda pie → coronación. Cambia en la
  cantidad pedida (o hasta el ángulo pedido), más empinado o más tendido,
  **igual mire el talud hacia donde mire**.
- **Tres formas de mover los vértices**, con H la altura, β′ el ángulo
  nuevo y s el sentido:
  - proyectar en horizontal (por defecto): la coronación va a
    x_t + s·H/tan β′ a su misma cota;
  - proyectar en vertical: y_c′ = y_t + |Δx|·tan β′;
  - girar: la cara gira rígida alrededor del pie.
- **Conservar las bermas** (por defecto, en las dos proyecciones): cada
  vértice se mueve en proporción a su altura (o a su abscisa), así que dos
  vértices a la misma cota se mueven juntos y la berma conserva su ancho.
  Sin la opción, cada vértice va por su propio rayo desde el pie y los
  anchos cambian.
  - **Esta lectura de la opción es nuestra.** La referencia da el nombre y
    el propósito de la opción, no sus fórmulas.
- **Lo que está sobre la cara:**
  - un vértice de otro contorno que está sobre un tramo de la cara (una capa
    que llega al talud, un nivel freático) se mueve con ella, en la misma
    fracción del tramo. Es más limpio que lo que describe la referencia
    («puede que haya que editarlos a mano»);
  - los soportes y las cargas no se mueven, como en la referencia, pero el
    resultado nombra los que estaban en la cara.
- **Se rechaza con el motivo, sin tocar el modelo:**
  - un ángulo fuera de (0°, 90°);
  - un pie más alto que la coronación;
  - un punto que no es vértice;
  - una coronación que choca con la meseta (la demo a 5°);
  - `keep_benches` en el modo girar, que no lo lee (regla 7).

### Interfaz

- La acción y el menú contextual del exterior entran en el modo.
- **La selección:**
  - cada clic se resuelve al vértice del exterior más cercano, dentro de una
    tolerancia en píxeles;
  - un clic lejos de todos se rechaza y lo dice;
  - el primer clic marca el pie con un punto rojo;
  - Esc cancela.
- La selección llega a la ventana por una señal propia,
  `slope_vertices_picked(int, int)`, conectada una sola vez.
- **El diálogo** muestra el ángulo global actual y el nuevo, pide el cambio
  y su sentido, y el tipo de giro. La casilla de bermas se deshabilita al
  girar.
- **Un solo paso de deshacer** (`SnapshotCommand`).
- **Textos:** todo pasa por `tr()` con su castellano: *pie*, *coronación*,
  *berma*, *ángulo global*. También la etiqueta de la acción, que no lo
  tenía.

### Agente

- **Nueva operación y herramienta `slope_angle_change`.**
  - El pie y la coronación se dan como índice o como `[x, y]`, que se
    reconoce a 1e-5 × la diagonal porque los resúmenes redondean.
  - Se da `change_deg` o `target_deg`, junto con `mode` y `keep_benches`.
- **Perfiles:** `full` pasa de 55 a 56 herramientas; `compact` no cambia.
- **Inventario:** `change_slope` deja de estar pendiente. Son **99 de 136**
  acciones cubiertas y 14 pendientes, todas de F3. `PENDING_CEILING` baja
  de 15 a 14.

## 2. Lo que se borró

- `transforms.change_slope_angle` y su exportación. No se deja al lado de la
  nueva.
- Su único test, `TestChangeSlopeAngle` de `test_transforms.py`, que solo
  comprobaba que el número de vértices sobrevivía al giro del contorno
  entero.
- Tres traducciones del diálogo antiguo que ya nada usa.

## 3. *Insert Vertex* nunca funcionó

`canvas_view._pick_edge` no tenía su línea `def`. Su docstring y su cuerpo
estaban tras el `return` de `_pick_support_endpoint`, como código muerto, y
la rama de *Insert Vertex* lo llamaba: **cada clic en ese modo lanzaba
`AttributeError`**.

`git log -S "def _pick_edge"` no encuentra ni un commit que la contenga: ya
estaba así en la primera versión pública (v0.1.59). Se restaura con su
tolerancia en píxeles, y un clic real sobre una arista inserta el vértice
(test).

## 4. Un análisis en segundo plano podía morir por un sondeo de su progreso

**Encontrado por la primera suite entera de esta versión** (4425/4426). No
tiene que ver con *Change Slope Angle*: el defecto está en la capa de
trabajos desde v0.1.194.

- **Qué pasó.** Un trabajo de análisis murió con `PermissionError:
  [WinError 5] Acceso denegado` al renombrar `progress.json.tmp` sobre
  `progress.json`.
- **La causa.** En Windows no se puede renombrar un archivo encima de otro
  que un proceso tiene abierto, y el proceso padre lee `progress.json`
  mientras el trabajo corre. La excepción salía del callback de progreso y
  **terminaba el análisis entero**.
- **Reproducido de forma determinista:** `os.replace` sobre un archivo
  abierto para lectura da `PermissionError 5`, y al cerrarlo funciona.
- **Es una carrera:** el mismo test pasó tres veces seguidas después.

Reportado antes de tocarlo (regla 6). El propietario decidió arreglarlo en
esta versión:

- **El progreso es informativo.** Una actualización que no se puede escribir
  se salta, sin reintentar ni lanzar excepción (`_write_progress`).
- **Las escrituras finales** (`result.pkl`, `summary.json`, `status.json`)
  reintentan el renombrado hasta 40 veces cada 25 ms: una lectura del padre
  dura milisegundos.

`test_jobs_file_race_v1198.py` (3 casos) mantiene el archivo abierto a
propósito:

- una actualización de progreso con el archivo retenido no lanza;
- una escritura final espera a que el lector suelte el archivo;
- **un trabajo cuyo `progress.json` un lector mantiene abierto todo el
  tiempo termina con su resultado.** Contra el `worker.py` anterior, este
  último falla con el mismo `PermissionError` de la suite.

## 5. Contadores de tests que se mueven a propósito

- `_NEVER_ENTERED` (`test_add_surface_three_points_v1168`) pierde
  `CHANGE_SLOPE_ANGLE`: el modo ya se usa.
- `_HINTS_WITHOUT_SPANISH`: 33 → 32. La pista del modo, reescrita, tiene su
  castellano.
- `_UNWRAPPED_BUDGET_MESSAGES` (`test_i18n_coverage_v141`): 68 → 67. El
  `QMessageBox` sin `tr()` de la acción antigua desapareció.

## 6. Tests

`test_slope_angle_v1198.py`, 15 casos, cada uno contra una forma cerrada:

- **Demo en horizontal a 30°:**
  - solo cambia la coronación, a 35 − 10/tan 30°;
  - el ángulo es exacto;
  - el área cambia exactamente ½·H·Δx.
- **El talud en espejo** da el resultado en espejo.
- **Un cambio** se suma al ángulo global.
- **Bermas:**
  - con la opción, el ancho no cambia;
  - sin ella, cada vértice cae en x = x_t + (y − y_t)·cot(φ + δ) y el ancho
    cambia (regla 7).
- **Vertical y girar** con sus fórmulas.
- **Regla 1 por el motor.** La cuña de Coulomb de
  `test_anchored_wedge_root_v1177`, con la cara llevada de 56,3° a 50° por la
  operación, da la forma cerrada de la geometría NUEVA (Coulomb 1776;
  Duncan & Wright 2005 §6) con Spencer y Janbu dentro de 2e-6.
- **Lo que está sobre la cara:**
  - una capa que acaba en la cara la sigue a su cota;
  - un soporte no se mueve y sale en la nota.
- **Siete rechazos** sin cambiar el modelo, y el agente dice por qué.
- **Interfaz con clics reales:**
  - pie y coronación dan lo mismo que el núcleo;
  - un clic lejos no elige nada;
  - Esc olvida el pie;
  - el menú contextual entra en el modo;
  - un solo paso de deshacer;
  - el diálogo: signo, ángulo fuera de rango y la casilla deshabilitada al
    girar.
- ***Insert Vertex*** inserta el vértice con un clic real.

La tabla de `test_api_undo_v1194` añade la operación: hacer, deshacer y
rehacer exactos.

## 7. Verificación

- Selección dirigida (i18n, modos del lienzo, inventario, MCP, API, F2,
  menús, lienzo, vértices, contornos, diálogos, transformaciones, lentes,
  cierre, ayudas): 435/435 en 28 archivos.
- **Primera suite entera: 4425/4426.** El único fallo fue la carrera de los
  trabajos del §4.
- **Tras arreglarla, suite entera y sin argumentos: 4429/4429**, sin aviso
  FILTERED RUN, con los siete paquetes medidos de este árbol. Tardó 33 min
  (14:22 → 14:56). Cuadra con v0.1.197: 4412 + 15 (pendiente) − 1 (el test
  borrado) + 3 (la carrera) = 4429.
- **No probado a mano:** la interfaz en pantalla. Los clics de los tests
  son eventos Qt reales, en un lienzo que no llega a pantalla.

## 8. Qué falta

- Bloque 3: las cargas puntuales `normal_to_boundary` y `angle_to_boundary`,
  con validación externa, con su plan corto antes.
- Después, F3.
- *Slope Angle Wizard*, que genera escenarios en pasos de ángulo: hace falta
  el concepto de grupos/escenarios.

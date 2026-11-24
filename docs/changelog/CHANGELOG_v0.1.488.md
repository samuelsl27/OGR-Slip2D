# OGR Slip2D v0.1.488

**D454: el número de cuñas del método de Sarma es un número pedido, no un mínimo, y una división ya solo se
quita donde quitarla no puede mover el factor.** El nombre del ajuste («Número mínimo de cuñas») nunca fue
cierto. La medida previa mostró además que quitar divisiones fuera de un tramo recto cambiaba la superficie:
un círculo que pedía 25 cuñas acababa con dos cuerdas.

## 0. Lo que se encontró

### El alcance, medido antes de decidir

`_auditoria/P9_D454/censo_cunas_d454.py` (banco) envuelve `build_wedges` en las 13 búsquedas de Sarma del 03.
Con 0.1.487:

- **8195 de 51 452 superficies tienen menos cuñas que las pedidas**, y 1497 tienen más (por las fronteras
  obligatorias).
- **En las poligonales (6597), F no se mueve.** Una división uniforme no es un vértice ni un cruce con un
  contacto o con el freático, así que las dos bases que separa están en un tramo recto. Las dos cuñas suman la
  que partían (`TestFacesOnAStraightStretch`).
- **En los círculos (554) y en las superficies compuestas (1044), sí.** Sus bases son cuerdas entre las
  divisiones, y la cascada de 0.1.464 quitaba casi todas.

En el 002 circular, 20 círculos pidieron 25 y se quedaron en 2 (23 cuñas perdidas). Uno de ellos:

| caras | cuñas | F |
|---|---|---|
| bisectriz | 2 | 2,2126 |
| normal media | 2 | 3,0154 |
| verticales | 25 | 4,1942 |
| Spencer | — | 4,3691 |

**Es otra superficie, de dos cuerdas, y del lado inseguro.** En el 007, un círculo de 3 cuñas daba 14,05,
12,60, 10,63, 12,00 o 13,13 según se pidieran 23, 24, 25, 26 o 27. Las críticas de esas búsquedas conservaban
sus 25 cuñas.

### La decisión (de la propietaria, 2026-11-24): la opción C

**Una división uniforme se quita solo si las dos bases que separa son un tramo recto de un solo material de
Mohr-Coulomb** (`wedges.build_wedges`, `droppable`). Es exactamente lo que necesita la identidad del tramo recto.

- Colineal quiere decir que los ángulos difieren menos de `_COLLINEAR` = 1e-9 rad. El redondeo de una
  poligonal partida es ~1e-12; las cuerdas de un círculo de 1000 cuñas difieren ~1e-3.
- **En otro sitio (las cuerdas de un círculo o de un arco, un cambio de material sin contacto), la cara se pone
  vertical**, como ya se hacía en un vértice, un contacto o un corte del freático. Dos caras verticales nunca se
  cruzan.
- `wedges.DROP_ONLY_ON_STRAIGHT = False` devuelve la regla de 0.1.464–0.1.487. Queda para el A/B y para el
  test de la regla 7.

Se descartó la opción B (volver a dividir hasta llegar al número): podía no terminar y cambiaba la geometría de
todas las superficies con pérdidas. La opción A sola (renombrar) dejaba el círculo de dos cuerdas tal cual.

### El impacto en el banco del 03

`_auditoria/P9_D454/ab_cunas_d454.py` es un A/B en memoria, en serie, con el interruptor en los dos sentidos.

| búsqueda | superficies con otro número de cuñas | F que cambia (mayor) | crítica |
|---|---|---|---|
| 002 circular | 20 | 17 (+338 %) | 1,119133, igual |
| 003 circular | 463 | 1743 (+849 %) | 1,083120, igual |
| 003 poligonal | 22 | 35 (+43 %) | 1,369861, igual |
| 007 | 61 | 60 (+63 %) | 1,195673, igual |
| **009** | **895** | **895 (+20 %)** | **1,402861 → 1,439940** |
| las otras 8 | 0 | 0 | iguales |

- En el 002 circular, 32 superficies ganan un factor y 34 lo pierden; en el 003 circular, 24 lo ganan.
- **El 009 cambia de crítica.** Su superficie es compuesta: un círculo recortado por la capa débil. El 009 se
  compara con Spencer (no con Sarma: es «la discrepancia del modelo», D357), y su Sarma de Slide, con caras
  verticales, es 1,438. La referencia de Fredlund y Krahn es 1,432.
- En el 003 poligonal, las 22 superficies que cambian de número tienen bases que no son un tramo recto de un
  material aunque la división sea uniforme. La crítica no se mueve.
- Después, con 0.1.488 (`censo_cunas_d454_0.1.488-dev.log`), **ningún círculo pierde cuñas.** Siguen perdiéndolas
  6597 poligonales, donde F no se mueve, y 974 compuestas en sus tramos rectos: 1044 antes, 501 de ellas pierden
  una.

### El nombre

- Página de métodos: **«Number of wedges asked for:» / «Número de cuñas pedido:»**, con un tooltip que dice que
  una superficie puede tener más cuñas (fronteras obligatorias) o menos (divisiones quitadas en un tramo recto de
  un material de Mohr-Coulomb, donde F no cambia), y que en otro sitio la cara se pone vertical y el número se
  conserva.
- El tooltip del ángulo de las caras dice la regla nueva.
- La línea de órdenes (`--sarma-slices`): «Number of wedges asked for in Sarma's method…».
- El español de la fila del informe, «Least Number of Wedges», pasa a «Número de cuñas pedido».
- **El inglés de esa fila es de OGR-Core** (`_sarma_settings_rows` de `ogr_core/report/report_generator.py`) y
  sigue diciendo «Least Number of Wedges». También el docstring de `SarmaSettings`, «the LEAST number of wedges».
  **Pendiente del núcleo**: se pide en la ventana de OGR-Core y sale como versión nueva. `d454()` lo dice como
  pendiente.
- Docstrings de `ogr_slip2d/sarma/wedges.py`, sin «minimum» ni «least number».

## 1. Qué cambia

- **`ogr_slip2d/sarma/wedges.py`**: `_COLLINEAR`, `DROP_ONLY_ON_STRAIGHT`, `droppable` en `build_wedges` (en vez
  de `plain`, en los dos sitios donde se quitaba una división), y el comentario de la decisión de 0.1.464 con la
  de 0.1.488.
- **`ogr_gui/dialogs/project_settings_dialog.py`**, **`ogr_gui/i18n/__init__.py`** y **`ogr_cli/__main__.py`**: los
  textos.
- **Versión** en los siete sitios.
- El número que guarda el `.ogr` (`settings.sarma.num_slices`) y su valor por defecto, 25, no cambian.

## 2. Tests

- **Nuevo, `tests/test_sarma_wedge_count_v1488.py`**:
  - un círculo con el centro dentro del talud (sus bisectrices se cruzan bajo el terreno) conserva sus 25 cuñas,
    y sus bases son las 25 cuerdas entre sus divisiones, por la longitud total calculada aquí a partir del
    círculo solo (geometría, regla 1);
  - con la regla de antes tiene 2 cuñas y otro factor (regla 7);
  - el 4 saturado publicado pedido con 25 tiene 19 cuñas y el factor de 2 (0,434662, Hoek 1987);
  - ningún texto visible del ajuste dice «least» ni «mínimo», en inglés ni en español.
- **`tests/test_sarma_report_v1468.py`**: la lista en español empieza ahora por «Número de cuñas pedido», a
  propósito. La fila inglesa sigue en «Least Number of Wedges» (OGR-Core).

## 3. El banco

- **`_auditoria/P9_D454/`**: `censo_cunas_d454.py` y sus dos logs (0.1.487 y 0.1.488-dev), y `ab_cunas_d454.py` y
  su log.
- **`d454()`** en el `verificar_cierres.py` de la raíz: sale **CUBIERTO POR TEST**, con la fila del informe del
  núcleo como pendiente.

## 4. Qué se probó y qué falta

- Probado:
  - `tests/test_sarma_wedge_count_v1488.py`;
  - `python tests/_runner.py sarma i18n spanish report version unwrapped budget --jobs 4`: 583 casos en verde;
  - el A/B en memoria del 03.
- Falta:
  - la suite entera con `--jobs 4`, al final de la tanda;
  - re-correr el 9 del banco (su crítica de Sarma cambia) y regenerar la comparativa;
  - pedir a OGR-Core el texto de la fila del informe y del docstring de `SarmaSettings`.

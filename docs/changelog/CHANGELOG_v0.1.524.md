# OGR Slip2D v0.1.524

**D461 cerrada documental.** Con la norma de diseño y la fuente única apagada, F de Sarma salta cuando una
cara entre una cuña que empuja y otra que resiste cruza la vertical. Es consecuencia del modelo y ahora
queda escrito, con las cifras y lo que hace el optimizador. La propietaria eligió el 2026-11-28 la
opción A con la nota de C. Ningún número cambia.

## 0. Lo que se encontró

- **La tabla de la ficha se reproduce exacta en 0.1.524.** Círculo de
  `tests/test_sarma_optimize_angles_v1471.py`, DA1-C1, `single_source_weight=False`, salto de F entre
  89,999° y 90,001°:

  | Caso | Salto |
  |---|---|
  | Ru 0,3, 6 cuñas, cara 2 (x = 31,162) | −0,578 % |
  | Ru 0,3, 10 cuñas | −0,316 % |
  | Ru 0,3, 25 cuñas | −0,118 % |
  | Ru 0,6, 6 cuñas | −2,074 % |
  | Ru 0 | 0 |

  Con la media de los dos factores en `_face_factor` (solo en la sonda), ninguna fila pasa de 0,001 %.
- **Frank et al. (2004), §11.5**, la sección empieza en la p. 199 del libro:
  - dice que tratar el peso y el agua es «often difficult» en DA-2 y en DA-1 C1, porque son
    desfavorables en una parte de la masa y favorables en otra, y el límite entre las dos depende del
    punto de los momentos;
  - recomienda factor 1 en todas las acciones permanentes, agua incluida, y aplicar γG al final;
  - su principio de fuente única (mismo factor en todas las presiones de agua de una fuente) lo aplican
    en sus ejemplos de zapatas drenadas (cap. 6) y de levantamiento de pilotes (cap. 7);
  - **ninguna fuente da una regla** para el agua de Ru cuando el peso que la genera es favorable en unas
    cuñas y desfavorable en otras. La media ponderada (opción B) no tendría fuente, y la media simple ya
    la descartó la revisión de 0.1.463 (PW 485 frente a 557).
- **El optimizador en estos casos** (`optimized_global`, 6 cuñas, instrumentado con `sys.settrace`
  sobre `attempt`):
  - **Ru 0,3:** sale de la bisectriz (F 1,228537). La cara de la frontera cruza la vertical en su primer
    movimiento (92,59° → 82,59°, un salto menor que el `JUMP` del 1 %) y acaba en 67,59°, con F
    1,215381, 111 pruebas y 0 saltos rechazados.
  - **Ru 0,6:** sale de la normal media (F 0,685534). El primer cruce de esa cara (92,61° → 82,61°) se
    rechaza como cambio de rama. En la pasada siguiente, con la cara de abajo ya movida, el mismo
    movimiento se acepta. La cara acaba en 77,60°, con F 0,552147, 809 pruebas y 41 saltos rechazados:
    19 en esa cara y los demás en las caras 3 a 5, que no cruzan la vertical.
  - **La continuidad frena la cara de la frontera, pero solo durante una pasada.**
- **Censo del banco:** 248 `.ogr` vivos, fuera de `Evaluaciones/` y `_auditoria/`. Ninguno tiene la
  norma con la fuente única apagada, y ninguno tiene Sarma con la norma. No hay ningún
  `construir_modelo.py` vivo con `single_source_weight = False`.

## 1. Qué cambia

- **Docstring de `_face_factor`** (`ogr_slip2d/sarma/wedges.py`): por qué salta F, las cifras, por qué la
  regla es la correcta para la columna, lo que dice Frank et al. (2004), que con la fuente única (el
  valor por defecto) no hay salto, y lo que hace el optimizador.
- **Tooltip de «Single source»** (Ajustes → Norma de diseño), una frase más con su español: desactivada,
  con Sarma y Ru, F salta cuando esa cara cruza la vertical (−0.6 % con Ru 0.3, −2 % con Ru 0.6, en un
  círculo de prueba); activada, no hay salto.

## 2. Tests

No hay test nuevo: es un cierre documental y ningún número cambia. Tests dirigidos
(`sarma design i18n texts_details settings budget dialogs_fit`, 33 archivos): 585 en verde. El veredicto en
vivo lo da `d461()` del `verificar_cierres.py` de la raíz del banco.

## 3. Suite y cierre en el banco

- **La suite entera con `--jobs 4`** (núcleo `ogr_core 0.2.15`), sobre 55de1a5, sale en verde: **7760 casos, 0
  fallos**, 2 saltados, sin fugas y sin tramos muertos. Cubre las tres versiones de la tanda, de 0.1.522 a
  0.1.524. La última serie en verde fue hace 71 commits.
- **Banco, raíz**, el 2026-11-28:
  - `d460()`, `d461()` y `d462()` del `verificar_cierres.py`: CIERRE DOCUMENTAL, CIERRE DOCUMENTAL y CUBIERTO
    POR TEST. Con el árbol de 0.1.521, las tres dan SIGUE ABIERTO.
  - Instantánea `Evaluaciones/0.1.524`; las tres fichas retiradas y podadas de P9.
  - Nace **D470** (P8): los 16 combos de otros diálogos.
  - Auditoría de invariantes: 0 ERROR.

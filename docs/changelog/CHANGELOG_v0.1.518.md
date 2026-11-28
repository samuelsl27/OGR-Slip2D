# OGR Slip2D v0.1.518

**D455, preparación: la suite de Slip2D acepta el informe de OGR Core 0.2.15, que titula el peso de la
tabla de dovelas en kN/m.** Solo tests, sin código del programa.

## 0. Lo que se encontró

El arreglo de D455 en el informe es de OGR Core (`_slice_table`: `Weight\n[kN]` pasa a `[kN/m]`). Antes
de etiquetar un núcleo, la suite de Slip2D tiene que correr contra él con `--dev-core` y salir en verde
(AGENTS.md, «Un núcleo y varios programas»). Pero `tests/test_report_spanish_v1355.py` fija el texto
`'Weight\n[kN]'`: contra 0.2.15.devN habría caído, aunque el núcleo hiciera justo lo pedido.

## 1. Qué cambia

- `tests/test_report_spanish_v1355.py`: la cabecera esperada sale de la versión del núcleo importado.
  Con 0.2.15 o posterior (su `.devN` incluida) es `[kN/m]`, y con la fijada (0.2.14) sigue siendo
  `[kN]`. Cuando la fijación llegue a 0.2.15, el texto queda solo en `[kN/m]` y la condición sobra.

## 2. Tests

- `report_spanish`: 6 en verde contra el núcleo fijado.

## 3. Suite

Solo cambia un test, que se ha corrido solo. La suite entera va con la fijación de 0.2.15.

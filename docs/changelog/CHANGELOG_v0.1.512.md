# OGR Slip2D v0.1.512

**D463: el gris del grupo de ajustes de Sarma en la página Métodos tiene test.** Es un hueco de tests,
no un defecto: el comportamiento es el pedido desde 0.1.464, y esta versión solo lo fija. Sin código
del programa.

## 0. Lo que se encontró

- **Ningún test nombraba el grupo.** Comprobado en 0.1.485 y otra vez en 0.1.511: nada en `tests/`
  citaba `_refresh_sarma`, `_sarma_widgets` ni ninguno de los nueve controles. Los tests de Sarma que
  miran `isEnabled()` son de acciones de menú.
- **Lo que hace el código, medido de nuevo** (`_MethodsPage(ProjectSettings())` sin mostrar): los siete
  controles del grupo en gris sin la casilla; con ella, activos; la c y la φ de cara solo con la
  resistencia «dada». Igual que en 0.1.471 y 0.1.485.
- **El mutante cae.** Con un `_refresh_sarma` que no hace nada los controles se quedan como los crea
  Qt, todos activos, y el estado «sin marcar» falla control a control.

## 1. Qué cambia

- `spec/features/009-sarma-dovelas-no-verticales/spec.md`: marcado el criterio «La casilla de Sarma y
  su grupo de ajustes en Métodos, en gris cuando no aplican», citando el test.
- `tasks.md` de la misma spec: nota en la tarea 19, que sigue **sin marcar**. Le falta el test del
  dibujo de las caras en el PNG, que el changelog de 0.1.464 declara sin test y que no es de esta ficha.

## 2. Tests

- `tests/test_sarma_settings_grey_v1512.py` (nuevo, 4 tests, menos de 1 s, sin `MainWindow`):
  - la premisa: `_sarma_widgets` son exactamente los siete, y la casilla está activa porque el método
    está registrado;
  - los cuatro estados de la tabla, **control a control** y solo por las señales;
  - el combo de resistencia, sin llamar a `_refresh_sarma` a mano, enciende la c y la φ;
  - el mutante: un `_refresh_sarma` que no hace nada, restaurado con `try/finally`, hace fallar la
    tabla.
- Fuera, por decisión de la propietaria del 2026-11-28: la casilla en gris con el método fuera del
  registro. Esa regla es de v0.1.78 para todas las casillas, y la cubre `tests/test_methods_page_v178.py`.

## 3. Suite

La suite entera se corre al final de la tanda.

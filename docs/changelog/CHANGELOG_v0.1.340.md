# OGR Slip2D v0.1.340

**Un test prohíbe que el núcleo importe las capas de encima, con la lista exacta de lo que todavía lo hace, y
salen las dos primeras entradas: `results_io` y los ajustes de optimización (D337, primera parte).** Primera
versión de la tanda P8k.

## 0. Lo que se encontró

- **D337 es más grande que su ficha.**
  - La ficha nombraba un sitio, el exportador DXF.
  - El censo de esta versión encuentra **22 sentencias en 7 archivos** que importan el motor desde
    `ogr_core`: el exportador, `Project.from_dict`, la estadística, los anclajes (`bond.py`), el exceso de
    presión intersticial, `ProjectSettings.optimize_settings` y `results_io`.
  - Todas están dentro de una función, salvo la de `results_io`, que va en un bloque `TYPE_CHECKING`. Por eso
    nunca falló nada al importar.
  - Por decisión de la propietaria, se arreglan todas en esta tanda (0.1.340–0.1.346).
- **Nada lo impedía.** `test_api_layering_pyexec_v1194` solo prohibía `ogr_api` al núcleo.
- **Dos docstrings dicen lo contrario:**
  - `ogr_core/statistics/drawdown_sweep.py:40` («`ogr_core` still never imports `ogr_slip2d`»);
  - `ogr_core/hydraulic/ponded_water.py:71`.

  Pasarán a ser verdad al cerrar D337.

## 1. Qué cambia

- **`tests/test_core_layering_v1340.py`** (nuevo): un censo AST de todo `ogr_core`, también dentro de
  funciones, de clases y de `TYPE_CHECKING`.
  - Cuenta cada importación de `ogr_slip2d`, `ogr_fem2d`, `ogr_api`, `ogr_gui`, `ogr_cli`, `ogr_mcp`,
    `PySide6`, `mcp` o `importlib`, y cada llamada a `__import__`.
  - El resultado tiene que ser **exactamente** la lista `ALLOWED`, que solo encoge. Una importación nueva
    falla, y una entrada que ya no casa también. Cada versión de la tanda borra las suyas, y la lista quedará
    vacía en 0.1.346.
- **`results_io`** nombra `SearchResult` solo como anotación en cadena, que `from __future__ import annotations`
  nunca evalúa. Ya no lo importa.
- **Los ajustes de optimización:**
  - `ProjectSettings.optimize_settings()` y `optimize_kwargs()` construían un objeto del motor
    (`OptimizeSettings`);
  - suben, palabra por palabra, a `ogr_slip2d/optimize.py` como `settings_from_project(settings)` y
    `optimize_kwargs(settings)`;
  - en el núcleo queda `optimize_enabled_for`, que es pura.
  - `analysis_runner` los llama allí.

**Cambios deliberados en tests:**

- `test_optimize_wiring_v1104` y `test_surface_altering_v1260` llaman a las funciones nuevas: cambia la
  llamada, no lo que comprueban.
- Un comentario de `test_settings_coverage_v1103`.

## 2. Tests

- **`tests/test_core_layering_v1340.py`** (nuevo, 4 casos):
  - el censo es la lista exacta;
  - **el censo ve lo que debe**: un módulo escrito en el test, con una importación de cada tipo, se encuentra
    entero, para que un censo vacío no sea un escáner ciego;
  - `results_io` no importa nada de arriba;
  - los ajustes de optimización los construye el motor, con los valores de los ajustes. Sin la casilla
    marcada, el ángulo cóncavo vale 0 («no se permiten»), y desmarcada la optimización da `None`.

**Con el código de 0.1.339 fallan 3 de los 4.** El que pasa es el control del escáner, que no depende del
árbol. Se corrió sobre un `git archive` de 0.1.339, sin el buscador editable.

## 3. Verificación

- **El test de esta versión**, 4/4.
- **Los vecinos:** 131/131 en 7 archivos (la optimización y su cableado, Surface Altering, la cobertura de
  ajustes, las capas del API y el test nuevo).
- **Suite entera:** 6357/6357, `EXIT=0`, 79 min.
- **La CI de 0.1.333–0.1.339, subida al empezar esta tanda:** 6351 pasan, 0 fallan y 2 se saltan, en Python
  3.11, 3.12 y 3.13. Sale en rojo solo por el segfault al salir que se arrastra desde 0.1.276. Los tres
  fallos de Linux de 0.1.332 (D338) ya no están.
- **Banco:**
  - `verificar_cierres.py` entero: 86 comprobaciones, 0 bajadas;
  - D337, con su alcance medido y su primera parte apuntada;
  - abierta **D340**: avisos que el motor calcula y la ventana no enseña (retroanálisis, optimización,
    barrido de desembalse y etapas del transitorio). No se arregla en esta tanda;
  - instantánea `Evaluaciones/0.1.340`, prompts (34) y auditorías con 0 ERROR.
- **Ningún número del motor cambia:** las dos funciones se mueven palabra por palabra, y
  `test_optimize_wiring_v1104` comprueba lo mismo que antes.

## 4. Pendiente

- **0.1.341:** el exportador DXF recibe puntos (D337).

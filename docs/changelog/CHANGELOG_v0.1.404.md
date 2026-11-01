# OGR Slip2D v0.1.404

**Una ventana Interpretar cerrada suelta su resultado, y un lienzo deja de escuchar al proyecto que ya no enseña
(D389).**

Es la segunda versión del plan que salió de la prueba de la interfaz de 0.1.402. Arregla la causa principal de que la
ventana llegara a 8 GB en una sesión (hallazgos 2 y 8).

Ningún número se mueve: el cambio está en lo que la ventana retiene.

## 0. Lo que se encontró

- **Lo que vio la prueba:**
  - la memoria de la ventana subió a lo largo de la sesión: 3012 MB tras B.5, 5202 tras F.1 y G.3, 8074 tras J.3;
  - abrir otro proyecto no la bajó (5205 MB con el panel en «Todavía no hay resultados.»), y hubo que reiniciar;
  - `QApplication.topLevelWidgets()` seguía listando ventanas Interpretar ya cerradas.
- **La primera causa, la que se sospechaba:** `act_interpret` crea la `InterpretWindow` como hija de Qt de la ventana
  principal, y al cerrarla solo la quitaba de `interpret_windows`. Qt la conservaba oculta, con el diccionario de
  resultados que recibió.
- **La segunda causa, que salió en el censo previo y es la que manda:**
  - cada `CanvasView` se suscribía a su proyecto con `project.add_listener(lambda evt: self.refresh_scene())` y no se
    daba de baja nunca; `Project` ni siquiera tenía `remove_listener`;
  - el proyecto sujetaba así el lienzo de cada Interpretar abierta, y con él el resultado que dibujaba
    (`_shown_result`), aunque la ventana se borrase;
  - cada edición del modelo redibujaba además los lienzos ocultos de todas las Interpretar cerradas, así que la
    ventana se volvía más lenta durante la sesión;
  - el lienzo principal también se suscribía a cada proyecto que recibía, y dos veces al mismo si se lo daban dos
    veces.
- **Medido con la ventana real** (`_auditoria/P8_interfaz/d389_recalcular.py`, offscreen; Calcular de la demostración,
  abrir y cerrar Interpretar dos veces, Calcular otra vez; un cálculo deja 56 resultados de superficie):

  | Variante | Resultados vivos | Oyentes del proyecto | Interpretar ocultas |
  |---|---:|---:|---:|
  | Como estaba (0.1.403) | 168 | 4 | 2 |
  | Borrada al cerrar | 168 | 4 | 0 |
  | Borrada al cerrar y fuera de los oyentes | **56** | **2** | **0** |

  Igual sin recolector completo que tras uno.
- **Un camino equivocado, mío:** una primera medida de la tercera variante dio 112, y la tomé por una tercera causa
  (el `_shown_result` del lienzo borrado a la espera del recolector). Era la sonda: una variable suya seguía sujetando
  el último oyente. El test de abajo, sin esa variable, lo deshizo: el mutante que no suelta los datos pasaba.

## 1. Qué cambia

- **`ogr_core/project/project.py`:** `Project.remove_listener(cb)`, que no hace nada si `cb` no está.
- **`ogr_gui/canvas/canvas_view.py`:**
  - el lienzo guarda su oyente (`_project_listener`);
  - `set_project` se da de baja del proyecto anterior antes de suscribirse al nuevo;
  - `detach_project()` se da de baja y olvida el resultado dibujado.
- **`ogr_gui/interpret_window.py`, `closeEvent`:** llama a `canvas.detach_project()` y suelta `results_by_method` y
  `search_result`. Lo segundo es para una ventana cerrada sin borrar, como la que crea un script: el objeto sobrevive
  a su cierre y no sujeta nada.
- **`ogr_gui/main_window.py`, `act_interpret`:** `WA_DeleteOnClose`. La ventana se borra al cerrarla, y sus gráficos
  (sus hijas de Qt, como el diagrama de fuerzas del soporte) se cierran con ella.
- **`tests/test_interpret_releases_v1404.py`**, nuevo: 5 tests.
- El número en los nueve sitios y el contador de los dos README.

## 2. Qué se probó

- **`tests/test_interpret_releases_v1404.py`:**
  - `remove_listener` quita y calla si el oyente no está;
  - un lienzo escucha una sola vez al proyecto que enseña, y deja de escuchar al anterior;
  - con la ventana real: tras abrir y cerrar Interpretar dos veces y calcular otra vez, con el recolector apagado,
    solo quedan los resultados del cálculo actual, ninguna de esas ventanas sigue entre las ventanas de primer nivel
    (referencia débil y comparación por `id`) y el proyecto tiene los oyentes que tenía;
  - una Interpretar cerrada ya no se redibuja al editar el modelo, y abrir otra funciona;
  - una ventana cerrada sin borrar no sujeta ningún resultado.
- **La discriminación:** con el código de 0.1.403 fallan los cinco («224 surface results alive, 112 of them of
  earlier Computes», «a closed Interpret canvas was redrawn», «the same project, listened twice», y la falta de
  `remove_listener`).
- **Tres mutantes, cada uno cazado:**
  - sin `WA_DeleteOnClose`: 1 fallo;
  - sin darse de baja: 2;
  - sin soltar los datos: 1, el test de la ventana cerrada sin borrar.
- **Un fallo del test en la primera corrida combinada:** la comprobación de que no queda ninguna Interpretar miraba
  `topLevelWidgets()` entero, y otros archivos del mismo proceso dejan las suyas. Ahora mira solo las de este test, con
  referencias débiles que no las mantienen vivas.
- **Los vecinos:** Interpretar, el lienzo, contornos, leyendas, anclajes, ayuda, castellano, exportación, capas débiles,
  resultados caducos, cerrar con cambios, el puente y los menús: 395 de 395.
- **Las sondas:** `h8_interpretar_retiene.py` pasa de «LEMResult alive 56 | hidden Interpret windows 2» a 0 y 0, y
  `d389_recalcular.py` a 56 resultados y 2 oyentes.
- **La suite entera con `--jobs 4`:**
  - la primera dio un fallo, mío: `test_test_imports_v1372` (el censo de imports de los tests) cazó el `shiboken6` que
    importaba el test nuevo para `isValid`, que no es una dependencia declarada (viene con PySide6). Ahora el test
    compara por `id` con `topLevelWidgets()`, y sigue cazando el mutante sin `WA_DeleteOnClose`;
  - la segunda: **6956 de 6956, `Failed: 0`**, sin `Leaks` ni `Chunks died`, en 24,5 min. La serie no se repite: la
    versión no toca el pool.

## 3. El banco

- **D389 cerrada,** CUBIERTO POR TEST.
  - `d389()` en el `verificar_cierres.py` de la raíz, con la ventana real: tras abrir y cerrar Interpretar dos veces y
    calcular otra vez, 56 resultados (los del cálculo actual), los mismos oyentes y ninguna Interpretar oculta.
  - Discriminada: con el árbol de 0.1.397 da SIGUE ABIERTO («168; oyentes 2 -> 4; Interpretar ocultas 2»); con este,
    CUBIERTO POR TEST.
  - Instantáneas `Evaluaciones/0.1.404` en la raíz y en el 02, el índice de cerrados, `PAQUETES` podado, la cadena de
    P8 tachada y los prompts regenerados.
  - `auditoria_invariantes.py` sin ERROR en los dos bancos.
- Las sondas quedan en `_auditoria/P8_interfaz/` (`d389_recalcular.py`, `d389_variantes.py`, `d389_quien_retiene.py`
  y `h8_interpretar_retiene.py`).

## 4. Lo que queda

- **El plan:** D390 (Calcular y Abrir esperan al `.h5` pendiente) y D391 (Abrir pregunta si guardar). Después, D383.

## Archivos

- `ogr_core/project/project.py`, `ogr_gui/canvas/canvas_view.py`, `ogr_gui/interpret_window.py`,
  `ogr_gui/main_window.py`
- `tests/test_interpret_releases_v1404.py` (nuevo)
- `docs/changelog/CHANGELOG_v0.1.404.md` (nuevo)
- `README.md`, `README.es.md`
- `pyproject.toml`, `ogr_gui/main_window.py` y los `__init__.py` de `ogr_core`, `ogr_slip2d`, `ogr_fem2d`, `ogr_gui`,
  `ogr_cli`, `ogr_api` y `ogr_mcp` (el número)

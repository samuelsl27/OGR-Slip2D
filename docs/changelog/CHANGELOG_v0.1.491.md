# OGR Slip2D v0.1.491

**Una búsqueda o un muestreo que esta versión no conoce se rechazan con su código, en vez de
calcularse como Búsqueda en rejilla o como Monte Carlo (D429, la parte del motor).** Es la parte de
D429 que vive en este repositorio. Los cuatro lectores del núcleo (permeabilidad, envolvente de
desembalse, interpolación de la rejilla de presiones y unidad de aceleración), el peso que no es
número y el nombre que no es texto se arreglan en OGR-Core y llegan con la subida de la fijación.
La propietaria eligió la opción (a): rechazar con código.

## 0. Lo que se encontró

- **Medido otra vez antes de tocar nada** (regla 6), con 0.1.489 (ogr-core 0.2.10). Los ocho
  casos de la ficha abren como dice: `busqueda: future_search [] GridSearch` y `muestreo:
  future_sampling []`, entre ellos.
- **Censo del banco el 2026-11-24**, sobre el JSON en crudo de los 30 800 `.ogr` de la raíz (38
  más que en la ficha): **0 afectados** en los seis valores, el peso, γsat y el nombre.
  - Lo que hay: búsquedas `grid` 22 962, `path` 4 220, `block` 1 905, `particle_swarm` 1 245 y
    `auto_refine` 468; muestreos `monte_carlo` 30 257 y `latin_hypercube` 543; 698 envolventes,
    todas `r`, y ninguna sin `kind`; 234 rejillas, todas `tps`; cinco modelos de permeabilidad
    conocidos; ningún registro sísmico.
  - Arreglarlo no mueve ninguna fila.
- **Había dos sitios más que tomaban el desconocido por la Rejilla**, y la ficha no los nombraba:
  `_run_returns_circles` y `_surface_type_notes` de `analysis_runner.py`. Los dos decían en un
  comentario «an unknown id is the default Grid Search's». Ya no es verdad: ahora dicen que lo
  rechaza `check_analysis_settings`. El valor que devuelven no cambia, porque a ese punto ya no
  llega ningún desconocido por un camino que calcule.
- **El muestreo solo se pregunta con el análisis probabilístico activo.** Es la única corrida
  que lo lee; un cálculo determinista no muestrea, y rechazarlo por un campo que no usa sería
  otro silencio, al revés.

## 1. Qué cambia

- `ogr_slip2d/setting_messages.py`: `setting.search_unknown` y `setting.sampling_unknown`, como
  `DRAWDOWN_UNKNOWN`, con «Available: …». Las listas son las enumeraciones del núcleo
  (`SearchMethod` y `SamplingMethod`), no una copia.
- `check_analysis_settings` rechaza:
  - un `search_method` fuera de `SearchMethod`;
  - con `probabilistic_analysis`, un `sampling_method` fuera de `SamplingMethod`.

  Lo leen la ventana, la CLI (también `--search` con un valor que no existe), `project_validate`
  y `analysis_run` del agente, y `run_configured_statistics`.
- `build_search` pierde la rama «Default = Grid Search». La Rejilla es la rama de `"grid"`, y
  cualquier otro valor lanza `ValueError` con el mismo código, para quien llame sin preguntar
  antes.
- `run_configured_statistics` ya no cambia un muestreo desconocido por Monte Carlo
  (`except ValueError`).
- La ventana:
  - `ogr_gui/labels.py`: `SAMPLING_METHOD` y `sampling_method_label`;
  - `ogr_gui/core_messages.py`: los tipos `search_method_list`, `sampling_method` y
    `sampling_method_list`;
  - `ogr_gui/i18n`: las dos frases en español. Nombran cada valor por su rótulo («Disponibles:
    Monte Carlo; Hipercubo latino.»), y el desconocido sale tal cual.
- `tests/test_setting_refusals_v1491.py` (nuevo, 9 tests):
  - el desconocido se rechaza con su código, también en `build_search` y en la corrida
    estadística;
  - ningún valor de las dos enumeraciones se rechaza;
  - el muestreo no se pregunta sin el probabilístico;
  - `grid` sigue dando una `GridSearch`;
  - las dos frases en español.
  - Contra el motor de 0.1.490 fallan 4 de los 9.
- `tests/test_setting_refusals_v1350.py`: los dos códigos nuevos van en `_SINCE`, con su inglés, en
  vez de en `_V1349`, que sigue siendo lo que escribía la 0.1.349. Así los cubre
  `test_the_samples_cover_every_code`.
- La versión, en siete sitios.

## 2. Qué se probó

- El fragmento de REPRODÚCELO para la búsqueda y el muestreo: `['setting.search_unknown']` (y
  `build_search` lo rechaza) y `['setting.sampling_unknown']`.
- Por áreas: `setting_refusals`, `spanish_paths`, `core_messages`, `i18n`, `cli` y
  `probabilistic`, en verde.
- La suite entera con `--jobs 4`: 7597 casos, 7595 pasan, 0 fallan, 2 saltados, sin fugas ni tramos muertos.

## 3. Pendiente

- **OGR-Core** (versión nueva): los cuatro lectores, el peso y el nombre. Después, la subida de la
  fijación, con `_TOLERANT` vacío, y `d429()` en el banco. D429 sigue abierta hasta entonces.
- **Fuera de la ficha:** la ayuda de `compute --search` no menciona `particle_swarm`.

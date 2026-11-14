# OGR Slip2D v0.1.446

**Una nota sobre una superficie rechazada habla de esa superficie, y la puerta de una sola superficie dice por qué no
la tasó (D403).** Medido con 0.1.445 (dc27320):

| caso | 0.1.445 | ahora |
|---|---|---|
| el muro de D77 (27 círculos, ninguno corta el terreno), su región en un material borrado, más un círculo del usuario (10, 10) de radio 9,5 | la nota «ninguna superficie válida» gana «; 1 that crossed a region with no material» (con 2 dovelas, «; 1 that the slicer refused») | la misma nota que sin el círculo; el círculo conserva la suya |
| el círculo rozante de D346 (radio 5, entra 0,1 m en la cara), talud de ejemplo, Bishop, por `evaluate_surfaces` y `surface_evaluate` | «the surface does not cut the model, so there is nothing to price.» (la corrida, con el círculo guardado, nombraba el «Minimum Area 1») | «the surface was not analysed, and no reason was recorded; filters active that can remove it: Minimum Area 1 (the search's default, not a setting of this model).» |
| el mismo círculo con unos Límites del talud [0, 60], que contienen todo el modelo | la corrida, sobre el círculo del usuario: «Filters active… Slope Limits [0, 60], Minimum Area 1…» | solo el Área mínima, en las dos |
| la junta de `test_weak_layer_v1121` (polilínea (2, 2)–(16, 1)–(30, 10), 40 dovelas) con el techo del ángulo de base de una capa débil a 10° | `evaluate_surfaces`: «does not cut the model»; la corrida, sobre la polilínea del usuario: «Filters active… Minimum Area 1». La razón, una base de 15,9°, solo en la nota general de la corrida | las dos: «…a weak layer clips it, and the base of one of its slices is steeper than the "Maximum base angle on weak-layer clips" of Project Settings > Advanced.»; la puerta lleva además la nota con los grados |
| la misma junta con «casos automáticos» y el techo a 10° | la puerta da F = 4,0053 (el caso sin recortar) sin decir que el recortado (1,5984) cayó por el techo | el mismo factor, con la nota del techo |

**Ningún número ni ningún filtro cambia.** Se sigue filtrando a las superficies del usuario, por decisión de la
propietaria. Es la decimonovena versión de la tanda P10 y la segunda del plan aprobado el 2026-11-13.

## 0. Lo que se encontró

- **Paso 0, sobre 0.1.445 (dc27320):** el REPRODÚCELO del prompt da lo que dice la ficha (`paso0_d403.py`, en el
  banco): las dos notas del muro, que solo difieren en el fragmento del círculo del usuario, y el círculo rozante con
  «does not cut the model» y 11,84305595821084 con el área 0. El círculo (25, 20) de radio 21 ya dice su motivo de
  D420 (sale del contorno exterior), así que la frase de los filtros no puede culpar de él al Área mínima.
- **El techo de la capa débil no registraba motivo** (`paso0_d403_r5.py`). Con el techo a 10° en la junta de
  `test_weak_layer_v1121`, `evaluate_surfaces` decía «does not cut the model» y la nota de la corrida sobre la
  polilínea del usuario culpaba al Área mínima: las dos, falsas. Con solo el R5 del plan (recoger las notas
  pendientes), la corrida lo habría seguido diciendo. **Por decisión de la propietaria, el techo registra su motivo**,
  como hicieron D420 y los Límites del talud.
- **La revisión adversaria (dos agentes) encontró:**
  - **los dos, por separado:** la lista de filtros que «pueden haberla quitado» nombraba los Límites del talud, que
    nunca pueden ser la causa cuando no hay motivo, porque cuando quitan una superficie registran el suyo. La corrida
    lo hacía con los círculos del usuario desde 0.1.367 y con las polilíneas desde 0.1.427. **Se quitan de la lista en
    las tres notas**, por decisión de la propietaria;
  - **que mi paso 0 se equivocaba:** escribí en este changelog que el techo era la única nota que nace dentro de una
    evaluación, y `weak_layer_variants` emite otra (el tope de casos de capa débil, por `note_cb=self._note`). Además,
    con «casos automáticos» el techo descarta el caso recortado y deja el otro: la puerta daba 4,0053 sin decirlo. El
    paso 0 solo midió con «la capa más alta», que tiene un caso. **Por decisión de la propietaria, la puerta recoge
    también las notas de la búsqueda** (era el R5 del plan);
  - que la frase nueva decía «on this run» y «the search recorded no reason» en una puerta que no es una corrida.
    Pasa a neutral, por decisión de la propietaria;
  - una regresión del propio cambio: en un modelo sin contorno exterior la búsqueda sale sin motivo y la puerta
    culpaba al Área mínima. Ahora da la frase por defecto, que es la verdadera;
  - que este changelog y un comentario decían que el techo registra su motivo si «todas» las piezas caen por él: lo
    registra si alguna cae por él y ninguna da resultado. Corregido;
  - que el comentario de `run()` prometía «28 refused of 27 generated» sin la instantánea, cuando los contadores del
    rebanador cuentan piezas y pueden pasar del total sin ninguna superficie del usuario. Corregido.
- **La ayuda de la referencia** («Surface Filter», en `Documentacion_Guia/`): sus filtros son Cota, Profundidad, Área
  y Peso mínimos, y no se aplican a las superficies definidas por el usuario. Para los Límites del talud tiene un
  código propio, el −113. El docstring de `_evaluate_user_surfaces` decía que los tres filtros de OGR sobre lo
  dibujado a mano eran lo que hace la referencia, y no nombraba la Cota mínima.
- **El −113 contradice un comentario de D263.** `ogr_slip2d/search.py` dice que una superficie fuera de los Límites
  del talud «has no code of its own there», y el censo la cuenta bajo −101 desde 0.1.261. La tabla de códigos de la
  ayuda le da el −113 (y el −101 solo si queda también fuera de los límites por defecto). Se abre **D435**.
- **Otro defecto, anterior y aparte:** el rebanador rechaza esa misma polilínea de la junta con 25 dovelas, el valor
  por defecto, y con 50; con 20, 24, 26, 30 y 40 da F = 1,5985. Es la familia de D407 (un plano de dos vértices con
  25, 41, 43, 50 y 51) y, por decisión de la propietaria, se añade a esa ficha como segundo caso. Por eso el test
  usa 40 dovelas y lo dice.
- **Camino equivocado.** Medí R5 primero con `settings.search.num_slices`, que no es un campo: Python dejó crear el
  atributo y `build_search` siguió con las 25 de `settings.methods.num_slices`. El rechazo con 25 parecía del techo, y
  era D407.
- **La lista de vecinos del prompt** se comprobó patrón a patrón con `--list` antes de correrla (D431).

## 1. Qué cambia

- **La nota «ninguna superficie válida»** (`ogr_slip2d/search.py`): `run` toma los contadores del rebanador
  (`_outside_model`, `_orphan_material`, `_unsliceable`, en `_SLICER_COUNTS`) antes de las superficies del usuario y
  se los pasa a `_no_valid_surface_note(result, slicer_counts)`. Como antes, con lo que contó el paseo de Optimizar.
  Sin el argumento, los lee vivos.
- **El techo de una capa débil** (`_best_of_masses`): si una pieza de la superficie cae por él y ninguna da
  resultado, registra `weak_layer_steep` (`REFUSED_WEAK_LAYER_STEEP`). Los Límites del talud, si también descartaron
  una pieza, tienen la última palabra, porque son lo que cuenta el censo. La nota general de la corrida no cambia.
- **Los filtros que se nombran** (`_user_surface_filters`): Área, Profundidad y Cota mínimas, sin los Límites del
  talud. El fragmento sigue en el catálogo, para las notas ya escritas.
- **La puerta de una superficie** (`ogr_slip2d/analysis_runner.py`, `evaluate_surfaces`):
  - las notas que la búsqueda dejó al evaluarla, con el método delante, como en una corrida (el techo con sus grados,
    el tope de casos), haya o no resultado;
  - sin resultado, `_given_refusal`: el motivo registrado; si no hay ninguno, hay contorno exterior y hay filtros
    activos, el código nuevo `search.given_no_result_filtered` con los mismos fragmentos que la corrida; si no, la
    frase por defecto. Se corrige el docstring de `evaluate_surfaces`.
- **El docstring de `_evaluate_user_surfaces`**, parafraseado: el −113 de la referencia para los Límites del talud,
  los otros tres filtros como decisión de OGR, y la Cota mínima, que faltaba.
- **Frases con código** (`ogr_slip2d/search_note_messages.py`), con su español:
  - `search.refused_surface.weak_layer_steep`: «the surface was not analysed: a weak layer clips it, and the base of
    one of its slices is steeper than the "Maximum base angle on weak-layer clips" of Project Settings > Advanced.» /
    «la superficie no se analizó: una capa débil la recorta, y la base de una de sus dovelas es más empinada que el
    «Ángulo máximo de base en recortes de capa débil» de Ajustes de proyecto > Avanzado.»;
  - `search.given_no_result_filtered`: «the surface was not analysed, and no reason was recorded; filters active that
    can remove it: {filters}.» / «la superficie no se analizó y no se registró ningún motivo; filtros activos que
    pueden quitarla: {filters}.».
- **Agente:** `docs/mcp/herramientas.md` dice qué da `notes` en esos casos. Las claves del JSON de `surface_evaluate`
  no cambian.

## 2. Qué se probó

- **`tests/test_refused_surface_notes_v1446.py`** (16 casos, unos 3 s):
  - la nota del muro, idéntica con y sin el círculo del usuario, con el material borrado y con 2 dovelas (una
    identidad: la superficie del usuario no es de la búsqueda); la premisa de los 27; y la nota propia del círculo;
  - el círculo rozante por `evaluate_surfaces` y por `surface_evaluate` del agente, en inglés y en castellano, con
    los mismos fragmentos que la nota de la corrida; sin los Límites del talud en la puerta ni en la corrida; con el
    área 0, su factor (`_V1445`, medido con 0.1.445); el motivo registrado antes que los filtros (el círculo de
    D420); sin motivo ni filtro, la frase por defecto; y sin contorno exterior, también;
  - el techo: la junta con su factor sin techo (premisa, `_V1445`); con el techo a 10°, la nota con sus grados y el
    motivo en `evaluate_surfaces`, y el motivo en la nota de la polilínea del usuario de la corrida; con «casos
    automáticos», el factor del caso sin recortar (4,005282776854345, el de 0.1.445) con la nota; y el tope de casos,
    dicho en la puerta.
- **Discriminación:** en el árbol de 0.1.445, sin el buscador editable, fallan 10 de 16, todos por lo que miden salvo
  «sin motivo ni filtro», que falla allí porque no existe `_given_refusal` (0.1.445 ya daba la frase por defecto).
  Pasan las dos premisas, el factor con el área 0, el motivo de D420, la nota propia del círculo y el modelo sin
  contorno exterior, que ya eran ciertos (el último es la regresión que encontró la revisión).
- **Mutantes** (`mutants_d403.py`, en el banco): 10, todos muertos. Dos quedan fuera por equivalentes y lo dice su
  cabecera: registrar el motivo del techo con una masa entregada (con resultado, nadie lo lee) y volver a contar las
  notas de antes de la evaluación (`build_search` hace una búsqueda nueva por método, sin notas).
- **Cambia a propósito** `tests/test_search_notes_v1349.py`: las muestras de los dos códigos nuevos, el motivo nuevo
  en el conjunto de los que registra una búsqueda, y `_DATA` pierde el formato de las ventanas de los Límites en
  `_user_surface_filters`, que ya no las nombra.
- **Vecinos**, con los patrones `slope_limit_refusals user_surface_note min_area_zero search_notes method_notes
  user_polylines user_surfaces f2_ops ground_refusals weak_layer base_angle_ceiling two_ceilings phi_zero_ceiling
  refused_surface_notes left_soil_refusal mcp_server spanish_texts i18n voice_and_terms shared_test_caches
  slope_limits_two_sets` (cada uno comprobado por separado con `--list`): 494 casos en verde en 28 archivos.
- **La suite entera** con `--jobs 4`, tras los arreglos de la revisión: **7580 casos, 7579 en verde, 0 fallos y 1
  omitido**, sin fugas ni tramos muertos. La serie no toca (24 commits desde la última).

## 3. Qué queda

- **Sigue en P10:** D424 (0.1.447), la última del plan.
- **D407** gana el segundo caso (la junta con 25 y 50 dovelas).
- **Se abren, sin versión, por decisión de la propietaria:**
  - **D435:** el −113 de la referencia para los Límites del talud, que el censo cuenta como −101 desde 0.1.261, y el
    comentario de D263 que dice que no tiene código;
  - **D436:** Optimizar, ante una superficie de partida sin resultado, dice siempre que el rebanador la rechazó entera
    (`optimize.py`, `OPT_START_REFUSED`). Lo midió la revisión con el Área mínima a 1e6 sobre la crítica de un Path, y
    el agente puede llegar con `optimize_run` sobre un resultado viejo.
- **Reportado y sin tocar:**
  - la nota del tope de casos de capa débil (`weak_layers.py`) es una cadena en inglés sin código: sale en inglés
    también con la interfaz en castellano;
  - qué motivo gana si una pieza de una superficie cae por los Límites del talud y otra por el techo: los Límites,
    por el orden de los dos bloques. Ningún test lo protege, porque ninguna superficie medida tiene las dos;
  - el techo pisa el motivo del rebanador de otra pieza de la misma superficie (un material borrado, por ejemplo). La
    revisión lo da por aceptable: la pieza del techo ya estaba rebanada, y subir el techo la tasa;
  - lo que la tolerancia del borde del modelo decide en una superficie del usuario no se dice en ninguna parte.

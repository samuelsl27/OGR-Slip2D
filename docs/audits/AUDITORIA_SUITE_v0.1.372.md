# Auditoría de la suite de tests — OGR Slip2D 0.1.372

Fecha: 2026-10-28. Árbol: `3b7010e` (0.1.372), sin cambios. Python 3.14.7, Windows 11, i7-8550U
(4 núcleos, 8 lógicos), 15,9 GB de RAM, plan «Equilibrado», enchufado.

Pregunta: ¿por qué la suite entera tardaba 2–2½ h y cómo bajarla sin perder lo que caza? Este
documento es la **fase 2** (diagnóstico). No se ha cambiado nada del programa ni de los tests; la
propuesta (fase 3) va aparte y espera el OK de la propietaria.

Cada cifra lleva su naturaleza: **[M]** medida en esta auditoría, **[H]** hipótesis o
extrapolación, **[L]** leída en el código.

---

## 1. Resumen

1. **La mitad del «2–2½ h» era la máquina, no la suite.** `TextInputHost.exe` llevaba girando un
   núcleo desde el 22-10 (92 h de CPU) y hacía todo un 40–50 % más lento, también el código de un
   solo hilo [M]. Cerrado, la suite entera instrumentada tarda **87,6 min** con los 6628 casos en
   verde [M]. La corrida de ayer, con él vivo, tardó 134 min.
2. **De esos 87,6 min, ~22 son estado acumulado** [M+H]: el proceso único llega a 10,2 GB, 10,3 M
   objetos vivos, 441 ventanas principales vivas y un `sys.path` de 369 entradas, y eso encarece
   el `gc.collect()` del runner, los pools y los cambios globales de Qt.
3. **El `gc.collect()` que el runner hace antes de cada archivo cuesta 13,6 min** [M]: ~320 ns
   por objeto vivo, de 0,4 s por archivo al principio a 3,4 s al final.
4. **`sys.path` crece una entrada por archivo** (242 archivos hacen `sys.path.insert` y nadie la
   quita) y cada trabajador `spawn` hereda la lista: con 369 entradas, abrir un pool cuesta
   2,4–3,6 s en vez de 0,5–0,7 s [M, A/B en el mismo proceso]. La suite abre 149 pools.
5. **Ninguna `MainWindow` se libera**: 93 archivos dejan 441 vivas [M]. Un cambio de tema cuesta
   0,1 s sin ventanas y 19 s con 200 vivas, en línea recta [M]. Ahí está el ×11 de
   `test_points_table_v1371`.
6. **Lo demás son tests caros de verdad**: 99 tests de más de 10 s suman 37,9 min; los 40
   archivos más caros, 48,7 de los 86,4 min de archivos [M]. Los 5075 tests de ≤ 0,1 s apenas
   cuentan.
7. **Windows tarda ×1,5 lo que Linux** (52,6 / 57,3 / 64,8 min los tres jobs de la CI de este
   mismo commit), de forma bastante uniforme por bloques [M]. La CI está roja por el segfault
   al salir aunque pase 6626/6626 [M]: **hoy no hay un verde que distinga**.
8. **Siete anomalías** reportadas en §9 sin corregir (regla 6), entre ellas una fuga real de
   estado entre archivos (el tema oscuro guardado) y un cuelgue del programa con
   `PYTHONFAULTHANDLER` y sin consola.

## 2. Qué se midió y cómo

Todo con herramientas en el scratchpad de la sesión, fuera del árbol:
`C:\Users\samue\AppData\Local\Temp\claude\c--Samuel-OpenGeoRock-Slip2d-OGR-Slip2D\a9f96fd5-c1be-4ca9-9a78-f594b83b58b4\scratchpad\suite\`

| Herramienta | Qué hace |
|---|---|
| `perfil_suite.py` | Ejecuta `tests/_runner.py` tal cual como `__main__` (los hijos `spawn` lo reimportan igual) y envuelve `run_test`, `_load_module` y el `gc.collect` del runner. Registra por test y por archivo: pared, GC por generación y por hilo (`gc.callbacks`), memoria (`GetProcessMemoryInfo`), objetos vivos, ventanas de Qt por clase, hilos, procesos hijo (Toolhelp), pools, `Popen`, `bind`, y un **censo de estado** antes/después de cada archivo (entorno, `sys.path`, filtros de `warnings`, `logging`, numpy, matplotlib, Qt, carpetas de preferencias y puentes, y todos los atributos de módulo y de clase de `ogr_*`). Al final calibra en el mismo proceso. |
| `conducir.py` | Encadena los pasos uno a uno, espera si hay otra suite viva, corta un paso que no escribe en 40 min. |
| `muestreo.py` | Contadores de Windows (PDH) cada 5 s: memoria libre, paginación, CPU, frecuencia, disco. |
| `estatico.py` | Mapa con `ast` de los 443 archivos de test. |
| `analizar.py`, `ab_estado.py`, `ab_ventanas.py` | Tablas y los dos A/B de atribución. |

**Verificación del instrumento** [M]: el censo caza cuatro fugas inyectadas (idioma, variable de
entorno, constante del motor, método de clase) en su archivo y no marca el archivo que restaura;
el envoltorio no añade coste medible (47,1–47,3 s frente a 46,9 s del runner pelado, mismo
veredicto 346/346). En E1 el instrumento sumó 52 s de 87,6 min.

**Experimentos**, en serie, máquina sin otra suite (el conductor no vio intrusos):

| | Qué | Resultado |
|---|---|---|
| E0 | Calibración en proceso fresco (antes, entre y después) | 3 corridas |
| E1 | Suite entera, orden normal | 87,6 min, 6628/6628, código 0 |
| E2 | 16 archivos, cada uno solo en un proceso | todos en verde |
| E3 | Segunda mitad sola (archivos 222–443) | 39,0 min, 3173/3173 |
| A/B | `sys.path` normal/inflado; 0–200 ventanas vivas | §4 |

**Estado de la máquina**: TextInputHost cerrado (con permiso) antes de medir; VS Code y Claude
Code abiertos ocupan ~12 GB, así que E1 corrió con **menos de 1 GB libre en 279 de 1050
muestras** (mínimo 265 MB) y una paginación media de 239 páginas/s [M]. El Administrador de
tareas estaba abierto (≈15 % de un núcleo).

**Una noche perdida, y por qué** [M]: la primera cadena se colgó 6 h en el archivo 65. Causa mía:
la lancé con `PYTHONFAULTHANDLER=1` (§9, D-g). Arreglado en el conductor y comprobado.

## 3. Dónde se van los 87,6 min de E1

| Parte | Min | |
|---|---:|---|
| Tests (suma de su pared) | 72,7 | [M] |
| …de ellos, GC automático dentro de los tests | 1,3 | [M] |
| `gc.collect()` del runner antes de cada archivo | 13,6 | [M] |
| Instrumento | 0,9 | [M] |
| Carga de módulos, `release` del guardián, resto | 0,4 | [M] |

Por cuartos de la suite (mismos archivos, en orden) [M]:

| | Archivos | Tests (min) | Casos | `collect` (min) | Pools | Vida de pools (min) |
|---|---|---:|---:|---:|---:|---:|
| Q1 | 1–110 | 17,8 | 1643 | 1,4 | 44 | 2,4 |
| Q2 | 111–221 | 11,6 | 1812 | 2,9 | 29 | 1,5 |
| Q3 | 222–332 | 24,8 | 1515 | 3,7 | 33 | 3,6 |
| Q4 | 333–443 | 18,6 | 1658 | 5,7 | 43 | 5,1 |

El `collect` del runner crece con el estado; los tests dependen más de qué archivos caen en cada
cuarto que del estado.

## 4. El estado acumulado, pieza a pieza

### 4.1 El proceso crece sin parar [M]

| Archivo | Min | Privada (MB) | Objetos vivos | `collect` (s) | ns/objeto | `sys.path` | Ventanas 1.er nivel |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 6,9 | 1656 | 1,29 M | 0,42 | 321 | 24 | 446 |
| 100 | 18,9 | 3880 | 3,39 M | 1,11 | 326 | 84 | 3094 |
| 200 | 32,0 | 5906 | 5,57 M | 1,74 | 313 | 165 | 7688 |
| 300 | 59,3 | 7162 | 6,56 M | 2,01 | 306 | 268 | 11 100 |
| 400 | 74,1 | 8925 | 9,76 M | 3,15 | 323 | 337 | 12 876 |
| 443 | 87,6 | 10 227 | 10,31 M | 3,43 | 333 | 369 | 15 626 |

Las que más memoria dejan: `test_acads_validation_v178` (+1029 MB, es el primero e importa todo),
`test_validation_cases` (+678), `test_cancel_v1366` (+647), `test_points_table_v1371` (+494),
`test_tension_crack_truncation_v1109` (+486). Ya en 0.1.301 se medían 7,7 GB al final: no es
nuevo.

### 4.2 Calibración: fresco frente al final [M]

| Componente | Fresco | Final de E3 (222 arch.) | Final de E1 (443) |
|---|---|---|---|
| Bucle de CPU (control) | 0,21–0,26 s | 0,23 s | 0,24–0,27 s |
| 20 importaciones fallidas | 0,009–0,011 s | 0,19–0,20 s | 0,37–0,49 s |
| `gc.collect()` completo | 0,005 s | 1,64 s | 3,46 s |
| Carga que asigna mucho, con GC / sin GC | 0,41 / 0,30 s | 1,9–3,6 / 0,25 s | 3,7 / 0,23 s |
| Pool de 4 en vacío | 0,52–0,77 s | 1,8–2,3 s | 3,4–4,2 s |
| Rejilla de 539 círculos con pool / secuencial | 0,86–1,0 / 0,56–0,80 s | 2,4 / 0,67–0,82 s | 3,9 / 0,88–1,06 s |
| 50×20 widgets creados y cerrados | 0,14 s | 0,63 s | 1,13 s |

El control de CPU no se mueve: **la máquina no se frena; se encarece el estado del proceso**.

### 4.3 `sys.path` y los pools — A/B en el mismo proceso [M]

Mismo proceso, `sys.path` alternado entre 12 entradas y 369 (la carpeta `tests` repetida, como
al final de E1):

| `sys.path` | Pool de 4 en vacío | Rejilla con pool | 20 import. fallidas | Rejilla secuencial |
|---|---|---|---|---|
| 12 | 0,50 / 0,52 s | 0,74 / 0,68 s | 0,014 s | 0,55 s |
| 369 | 2,43 / 2,42 s | 3,64 / 3,98 s | 0,355 s | 0,73 s |
| 12 | 0,70 / 0,66 s | 0,96 / 1,05 s | 0,015 s | 0,75 s |
| 369 | 3,46 / 3,59 s | 4,45 / 3,90 s | 0,392 s | 0,76 s |
| 12 | 0,57 / 0,64 s | 1,19 / 0,99 s | 0,017 s | 0,78 s |

**El `sys.path` inflado explica por sí solo todo el encarecimiento de los pools.** Mecanismo [L]:
cada trabajador `spawn` recibe el `sys.path` del padre, y cada importación de primer nivel que
hace al arrancar (numpy, scipy, shapely, `ogr_*`…) recorre las entradas una a una con un `stat`
por entrada (~60 µs en Windows) hasta encontrar el módulo. Con 369 entradas, ~22 ms por
importación.

Consecuencias medidas:
- vida media de un pool: 3,2 s en la primera mitad de E1 y 6,9 s en la segunda;
- `test_window_grid_parallel_v1262`: 9,9 s solo, 33,8 s en la suite (×3,4), toda la diferencia
  en sus 3 pools; `test_validation_cases`: 68 → 102 s (×1,5) por sus 8 pools;
- **el test de tiempo frágil** `test_optimizations_v111::test_grid_completes_quickly` (< 5 s) abre
  un pool en el archivo 233: hoy 3,1 s y pasa; en 0.1.370, con TextInputHost, 11,1 s y falla. Su
  margen depende de cuántos archivos han corrido antes [M+H].

### 4.4 Las ventanas vivas y Qt — A/B con ventanas reales [M]

Coste de un cambio global en función de las `MainWindow` vivas (GC desactivado al cronometrar):

| `MainWindow` vivas | Widgets de 1.er nivel | Objetos bajo ellos | Tema oscuro ida y vuelta | Cambio de fuente | `processEvents` |
|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 0,1 s | 0 s | 0 ms |
| 25 | 625 | 13 600 | 2,2 s | 0,05 s | 4,6 ms |
| 100 | 2525 | 61 960 | 8,7–9,1 s | 0,21 s | 14,6 ms |
| 200 | 5100 | 144 051 | 18,9–19,5 s | 0,45–0,49 s | 20 ms |

Cada `MainWindow` trae ~25 widgets de primer nivel (sus `QMenu`) y ~600 objetos. Un cambio de
hoja de estilo, paleta o fuente de la aplicación recorre todos los widgets vivos. Al final de E1
hay 441 `MainWindow`, 147 `InterpretWindow` y 12 679 `QMenu` de primer nivel: un cambio de tema
costaría ~40 s [H, extrapolado].

En cambio, 14 500 widgets vacíos (`QMenu`/`QFrame` sin hijos) apenas pesan: crear 1000 widgets
pasa de 0,15 a 0,20 s y cambiar el catálogo de Qt de 0 a 0,03–0,06 s [M]. **Lo caro son las
ventanas completas, no el número de objetos de Qt.**

Retención [M]: 93 archivos dejan ventanas vivas (441 en total); los que más,
`test_design_factor_report_gui_v1165` (17), `test_undo_settings_annotations_v1305`,
`test_statistics_gui_v138`, `test_m1_datatips_snap_v151` (16). 127 archivos tienen
contenedores de módulo que retienen objetos (`_WINDOWS`, `_KEEP`…); 32 de ellos construyen
`MainWindow` [M, estático]. Cada ventana viva tiene además un `QTimer` de 2 s que llama a
`gc_guard.release` [L].

Es a propósito que sigan vivas [L]: borrar ventanas desde otro hilo abortaba la suite (0.1.302,
D310) y borrarlas a destiempo dejaba temporizadores apuntando a una ventana muerta. Cualquier
corte de este estado tiene que hacerse en el hilo principal y entre archivos.

### 4.5 La segunda mitad sola (E3) frente a dentro de la suite [M]

Los 222 archivos de la segunda mitad tardan **39,0 min solos y 53,6 dentro de E1 (+14,6 min)**:

| Parte del exceso | Min |
|---|---:|
| `collect` del runner (9,4 frente a 2,9) | 6,5 |
| Pools más lentos (`sys.path`) | 2,7 |
| Cambios globales de Qt con ventanas vivas (`points_table` +105 s, `qt_translations` +18 s) | 2,0 |
| Resto, sin atribuir | 3,0 |

El resto son tests numéricos puros un 10–25 % más lentos dentro de la suite
(`test_rescue_fold_v1362` +44 s, `test_transient_v130` +42 s, `test_slope_face_collinear_v1234`
+20 s, `test_overall_slope_v137` +18 s), sin pools ni GC apreciable. **Hipótesis sin medir**:
presión de memoria (10 GB del proceso con < 1 GB libre) y caché de la CPU. La CPU de control no
se movió.

La mediana por archivo (los de > 2 s) es ×1,13; el máximo, ×11,4 (`test_points_table_v1371`).

### 4.6 Cada archivo solo (E2) frente a dentro de la suite [M]

| Archivo | Posición | Solo (s) | En la suite (s) | × |
|---|---:|---:|---:|---:|
| `test_window_grid_parallel_v1262` | 439 | 9,9 | 33,8 | 3,41 |
| `test_dialogs_fit_more_v1326` | 82 | 10,6 | 28,0 | 2,65 |
| `test_validation_cases` | 427 | 68,1 | 101,8 | 1,50 |
| `test_relaxed_thrust_v1130` | 283 | 20,3 | 25,1 | 1,24 |
| `test_published_cases_v179` | 270 | 45,9 | 55,5 | 1,21 |
| `test_transient_coupling_v1125` | 408 | 36,4 | 39,7 | 1,09 |
| `test_cancel_v1366` | 52 | 51,2 | 53,9 | 1,05 |
| `test_acads_validation_v178` | 1 | 26,9 | 27,7 | 1,03 |
| `test_focus_all_searches_v1129` | 121 | 68,5 | 69,8 | 1,02 |
| `test_method_notes_v1348` | 217 | 16,9 | 17,0 | 1,01 |
| `test_names_and_headings_v1369` | 225 | 34,2 | 34,3 | 1,00 |
| `test_annealing_inequality_v1119` | 12 | 344,4 | 312,6 | 0,91 |
| `test_phi_zero_general_branch_v1190` | 250 | 0,4 | 0,2 | 0,56 |
| `test_api_undo_v1194` | 20 | 5,0 | 2,0 | 0,40 |
| `test_i18n_coverage_v141` | 150 | 4,3 | 1,1 | 0,25 |
| `test_steffensen_scope_v1174` | 355 | 3,6 | 0,6 | 0,16 |

Los archivos baratos son **más lentos solos**: pagan las importaciones que en la suite ya están
hechas (1–4 s cada uno). Es el coste fijo que un reparto en procesos paga una vez por proceso, no
una vez por archivo, si los procesos son de larga vida.

## 5. Los tests caros [M]

Tests de más de 10 s: 99, que suman **37,9 min**. Tests de más de 1 s: 587 (65,6 min). Tests
de ≤ 0,1 s: 5075.

Los 15 archivos más caros de E1 (tests + carga + `collect`; los 40 primeros suman 48,7 min):

| # | Archivo | Casos | Total (s) | Pools |
|---:|---|---:|---:|---:|
| 288 | `test_rescue_fold_v1362` | 12 | 330,9 | 0 |
| 12 | `test_annealing_inequality_v1119` | 13 | 313,0 | 3 |
| 413 | `test_transient_v130` | 35 | 213,7 | 0 |
| 335 | `test_slope_face_collinear_v1234` | 15 | 125,7 | 0 |
| 25 | `test_auto_refine_noncircular_family_v1264` | 2 | 120,0 | 0 |
| 259 | `test_points_table_v1371` | 5 | 116,7 | 0 |
| 239 | `test_overall_slope_v137` | 22 | 115,9 | 0 |
| 427 | `test_validation_cases` | 9 | 105,6 | 8 |
| 287 | `test_rescue_face_v1356` | 10 | 87,9 | 0 |
| 252 | `test_picard_loop_face_v1358` | 9 | 79,9 | 0 |
| 142 | `test_groundwater_ops_v1200` | 48 | 77,6 | 0 |
| 121 | `test_focus_all_searches_v1129` | 46 | 70,9 | 4 |
| 235 | `test_optimize_wiring_v1104` | 36 | 60,6 | 0 |
| 224 | `test_multimodal_v1126` | 23 | 59,1 | 1 |
| 95 | `test_drawdown_sweep_v170` | 18 | 58,5 | 17 |

Los cinco tests más lentos: `TestTheFoldIsCrossed.test_the_continuation_stops_on_its_smallest_step`
(147 s) y `TestTheCellIsTheProblem.test_residual_and_orientation` (133 s), los dos de
`test_rescue_fold_v1362`; `TestTutorial20NonCircular.test_is_the_published_shape` (120 s);
`test_all_runnable_cases` de `test_validation_cases` (102 s); y
`test_a_long_time_is_the_steady_state` de `test_groundwater_ops_v1200` (55 s). Muchos de los caros
son casos de validación contra referencia externa (regla 1): **no se pueden quitar ni
debilitar**, sí cambiar de nivel o de carril.

Pools [M]: 149 (136 de 4 trabajadores, 9 de 8, 4 de 2), en 45 archivos; 12,6 min de vida en
total. Los que más abren: `test_drawdown_sweep_v170` (17), `test_interpret_v112` (12),
`test_cancel_v1366` (11), `test_validation_cases` (8). Además 624 procesos de `multiprocessing`,
71 `Popen` y 44 `bind`.

## 6. Windows frente a Linux [M]

CI del mismo commit `3b7010e` (corrida 40594255853), por bloques de 20 archivos (el registro de la
CI va con búfer: no vale archivo a archivo):

| Bloque | Windows E1 | 3.11 | 3.12 | 3.13 | Win/3.12 | Archivo pesado del bloque |
|---|---:|---:|---:|---:|---:|---|
| 1–20 | 6,9 | 4,2 | 5,7 | 6,3 | 1,22 | `annealing_inequality` |
| 21–40 | 3,6 | 0,6 | 0,8 | 0,8 | 4,63 | `auto_refine_noncircular_family` |
| 221–240 | 6,0 | 2,9 | 3,2 | 3,6 | 1,84 | `overall_slope` |
| 241–260 | 5,6 | 2,5 | 2,8 | 3,4 | 1,96 | `points_table` |
| 281–300 | 10,6 | 4,8 | 5,9 | 6,9 | 1,80 | `rescue_fold` |
| 401–420 | 7,7 | 4,1 | 4,9 | 5,4 | 1,58 | `transient_v130` |
| **Total** | **87,6** | **52,6** | **57,3** | **64,8** | **1,53** | |

Primera mitad ×1,46; segunda ×1,57. El exceso de Windows es casi uniforme: lo explica sobre todo
el hardware (un portátil de 1,8 GHz base contra los servidores de GitHub) [H], y algo más en la
segunda mitad, donde pesa el estado. En Linux los pools arrancan con `fork`, que no reimporta
nada [L]. El bloque 21–40 (×4,6) es una anomalía (§9, D-i).

## 7. Mapa de dependencias (estático) [M]

- **170 de 443 archivos importan otro archivo de test** (89 módulos distintos):
  `test_slide_validation_ej1` lo importan 53; `test_supports_all_methods_v164`, 11;
  `test_tension_crack_truncation_v1109`, 10. Un reparto por archivos tiene que conservar estas
  importaciones (son de funciones auxiliares; se importan, no se ejecutan sus tests).
- **242 archivos** hacen `sys.path.insert`; **80** construyen `MainWindow`; **127** tienen
  contenedores de módulo que retienen objetos.
- **Tests que comparan con el reloj: solo 3** —
  `test_optimizations_v111::test_grid_completes_quickly` (< 5 s),
  `test_jobs_file_race_v1198::test_a_final_write_waits_for_the_reader` (< 5 s, 0,25 s en E1),
  `test_remote_oauth_v1204::test_register_approve_token_call_refresh_revoke` (≥ 0,9 s, un
  mínimo). Solo el primero depende del estado acumulado.
- **Puertos**: los 3 archivos que abren servidores usan `bind(("127.0.0.1", 0))` y el sistema
  asigna uno libre; no se reutiliza un puerto cerrado, así que no hay carrera entre procesos
  paralelos [M, estático + los 44 `bind` de E1].
- **Procesos**: 10 archivos lanzan `subprocess` directamente (trabajadores de trabajos, CLI,
  servidores MCP, comprobaciones de capas).

## 8. El censo de estado entre archivos [M]

277 archivos cambian algún estado observable al pasar; 62 claves distintas. La gran mayoría es
esperable: `sys.path` (241 archivos), primeras importaciones (numpy, matplotlib, Qt, `qApp`),
cachés acotadas (`ogr_core.geometry.ground._envelope`, `lru_cache(maxsize=64)`; `_HINTS` de
`ogr_api.coerce`), la caché de iconos que el cambio de tema vacía a propósito, y el registro
`MainWindow._sessions` (crece en 43 archivos y algún test lo vacía).

Un falso positivo: `test_auto_refine_refinement_v1150` restaura
`AutoRefineSearch._circle_through_two_points_half_angle` con un `staticmethod` nuevo sobre la
función original. Es otro objeto con el mismo comportamiento; no es una fuga.

Lo que sí es fuga está en §9.

## 9. Anomalías encontradas (regla 6: reportadas, no corregidas)

**D-a. `sys.path` crece una entrada por archivo** [M]. 242 archivos hacen
`sys.path.insert(0, tests)` a nivel de módulo y ninguno la quita; el runner tampoco. Coste
medido: +2–3 s por pool al final de la suite (§4.3) y la fragilidad de
`test_grid_completes_quickly`. No cambia ningún resultado: las entradas son la misma carpeta.

**D-b. Las ventanas principales no se liberan nunca** [M]. 441 `MainWindow` vivas al final, de
93 archivos; cada cambio global de Qt cuesta en proporción (§4.4). Es deliberado [L] (el aborto de
0.1.302), pero su coste no estaba medido.

**D-c. `test_dark_theme_v1316` deja guardado el tema oscuro para el resto de la corrida**
[M]. `MainWindow._apply_theme` guarda el tema en las preferencias (`main_window.py:5530`); el
`_themed()` del test restaura hoja, paleta, idioma e iconos, pero no el archivo de preferencias.
Comprobado aparte: tras `_apply_theme("dark")`, una `MainWindow` nueva arranca con
`active_theme == "dark"` (antes, `"light"`), y aparece `ogr-slip2d.ini` en la carpeta de
preferencias de la corrida. Afecta a toda ventana construida entre el archivo 74 y el que cambia
de carpeta (D-d). Ningún test falla por ello hoy; es exactamente la clase de fuga de la regla 5.

**D-d. Dos tests cambian las carpetas de preferencias y de puentes de toda la corrida** [M].
`test_runner_provenance_v189` y `test_runner_selection_v180` llaman a `main()` de otra copia del
runner, que apunta `OGR_BRIDGE_DIR` y `OGR_SETTINGS_DIR` a carpetas nuevas
(`tests/_runner.py:437`, `:440`) y no las devuelve. Inocuo hoy (carpetas vacías), pero tapa D-c
a partir de ahí y hace que el estado de la corrida dependa del orden.

**D-e. `qt_catalog._CURRENT` queda apuntando a un traductor ya retirado** [M]. En
`test_qt_translations_v1292::test_the_saved_spanish_installs_it`, `apply_saved_preferences`
instala el catálogo con `switch_qt_translator` y el test lo retira con `app.removeTranslator(t)`
en vez de `reset_qt_translator(app)`. Sin efecto visible (el siguiente cambio retira uno que ya no
está), pero el estado del módulo miente.

**D-f. El `logging` raíz queda configurado** [M] tras `test_bridge_version_v1300`: nivel INFO y un
`RichHandler`. Los registros de los tests posteriores salen por él. Menor.

**D-g. Con `PYTHONFAULTHANDLER` o `-X faulthandler`, un pool de `pythonw.exe` no arranca, y
puede colgar al padre** [M]. Afecta al programa, no solo a los tests:
`windowless_children` (`ogr_slip2d/processes.py:56`) elige `pythonw.exe` cuando no hay consola.
Con cualquiera de las dos opciones, el trabajador intenta activar `faulthandler` sin `stderr` y
muere al arrancar (`multiprocessing` pasa `-X faulthandler` a los hijos; comprobado las dos).
Con un `sys.path` corto da `BrokenProcessPool` en 0,08 s. Con uno largo (80 entradas), **el
padre se queda bloqueado para siempre** escribiendo los datos de arranque en una tubería que nadie
lee. Le pasó a la primera cadena de esta auditoría (6 h colgada en
`test_console_language_demo_v1329`, que fuerza `pythonw` a propósito). Impacto real bajo: pocos
usuarios fijan esa variable. La memoria de sesiones anteriores recomendaba
`PYTHONFAULTHANDLER=1` para diagnosticar abortos de la suite; ya está corregida.

**D-h. La CI no tiene verde** [M]. Los tres jobs de `3b7010e` pasan 6626 de 6628 (2 omitidos
por no haber `pythonw` en Linux) y acaban con código 139 por el segfault al salir, como desde
0.1.276. Un fallo real produce el mismo estado «failure»: para saberlo hay que leer los totales a
mano. Es el primer obstáculo para cualquier reparto en la CI (un fragmento muerto no se
distinguiría de uno sano).

**D-i. `test_auto_refine_noncircular_family_v1264` tarda 120 s en Windows** y el bloque entero
de Linux que lo contiene, 0,6–0,8 min [M]. Por el búfer del registro de la CI no se puede aislar
su tiempo en Linux; la diferencia (×2,5 o más) es mayor que la del resto de tests numéricos
(×1,5–2). Sin explicar [H].

**Además, de la máquina**: `TextInputHost.exe` colgado del 22 al 28-10 (§1). Hay 10 servidores
`ogr-slip2d-mcp` huérfanos del 22–27 de octubre, dormidos (1–3 MB cada uno); no se han tocado.

## 10. Qué no se midió

- El exceso por estado de la **primera** mitad: solo se midió el de la segunda (E3). Por cuántas
  entradas de `sys.path` y cuántas ventanas tiene la primera mitad, se estima en 2–3 min [H].
- Los **3 min sin atribuir** de §4.5.
- Una corrida entera **con** TextInputHost el mismo día: la comparación 134 → 87,6 min mezcla
  días. Lo que sí está medido es la calibración con y sin él, a 5 min de distancia.
- Linux archivo a archivo: haría falta `PYTHONUNBUFFERED=1` en la CI.
- Cualquier reparto en paralelo: es fase 3.

## 11. Lo que esto deja para la propuesta

Cifras de partida para la fase 3, todas a confirmar con su propia medida:

- **Sin estado acumulado**, la suite en serie bajaría de 87,6 a unos **65 min** [H]: −12 min de
  `collect` y −8 a −10 min de pools y Qt.
- **El piso en serie son los tests mismos**, ~65 min en esta máquina; de ellos, 38 min en 99
  tests de más de 10 s.
- **Con 4 procesos** (4 núcleos físicos), el límite teórico es ~17 min. En la práctica lo acotan
  el archivo más largo (`test_rescue_fold_v1362`, 5,5 min), el reparto y los pools de 4
  trabajadores de los propios tests, que compiten por los mismos núcleos [H].
- **Un nivel rápido sin los tests de más de 10 s** sería ~27 min en serie y ~7–8 min en 4
  procesos [H].
- **Memoria**: hoy un único proceso llega a 10 GB con ~12 GB ocupados por el editor. Cuatro
  procesos con el estado partido en cuatro rondarían 2,5–3 GB cada uno [H]; hay que medirlo antes
  de fijar N.

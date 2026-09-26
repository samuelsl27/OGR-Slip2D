# Censo del cribado posterior que revienta (D184), OGR 0.1.211

Generado por `_tools/censo_cribado_suite_d184.py` del banco de verificacion (fuera de git) con los censos de la suite (`suite_<v>.json`) y del 095-098 (`censo_<v>.json`, de `_tools/censo_p3_desembalse.py`). Alcance decidido por la propietaria el 2026-09-26: la suite y el 095-098, NO el banco entero.

Receta de D94: se envuelve `tensile_stress_check`, `m_alpha_check` y `screen_surface`, se registra a un archivo y se vuelve a lanzar, con el parche en un `sitecustomize` que cargan tambien los hijos de la busqueda paralela. Cada censo lleva un control positivo que tiene que ver una excepcion forzada.

| version | suite: casos / fallan | suite: llamadas al cribado | suite: excepciones (fuera del control) | suite: screen_error | 095-098: llamadas | 095-098: excepciones | 095-098: screen_error | controles |
|---|---|---|---|---|---|---|---|---|
| 0.1.210 | 4629 / 0 | 474488 | 0 | 0 | 22492 | 0 | 0 | True / True |
| 0.1.211 | 4664 / 0 | 473499 | 10 | 10 | 22492 | 0 | 0 | True / True |

Las excepciones y los `screen_error` de la suite van agrupados por test en el detalle (`EXCEPCIONES_POR_TEST`, `SCREEN_ERROR_POR_TEST`): los de `test_screen_error_v1211.py` son los que ese archivo provoca a proposito para probar la declaracion, no fallos del cribado.

## Detalle

### 0.1.210

- suite `version`: 0.1.210
- suite `arbol_medido`: worktree temporal de 0.1.210
- suite `completo`: True
- suite `suite`: {'codigo': 0, 'segundos': 2462.3, 'total': 4629, 'pasan': 4629, 'fallan': 0, 'filtrada': False, 'arbol_equivocado': False}
- suite `LINEAS_ILEGIBLES`: 0
- suite `archivos_de_registro`: 384
- suite `procesos_con_sonda`: 349
- suite `SONDAS_FUERA_DEL_ARBOL`: []
- suite `LLAMADAS`: {'screen_surface': 474488, 'screen_surface[m]': 473444, 'm_alpha_check': 411055, 'screen_surface[t]': 791, 'tensile_stress_check': 805, 'screen_surface[]': 2, 'screen_surface[tm]': 251}
- suite `EXCEPCIONES_DEL_CRIBADO`: 0
- suite `EXCEPCIONES_QUE_ESCAPAN_DE_SCREEN_SURFACE`: 0
- suite `EXCEPCIONES_POR_TEST`: {}
- suite `SCREEN_ERROR`: 0
- suite `SCREEN_ERROR_POR_TEST`: {}
- suite `tipos`: []
- suite `CONTROL_VE_EL_CASO`: True
- suite `control_pids`: [27908]
- 095-098 `version`: 0.1.210
- 095-098 `arbol_medido`: worktree temporal de 0.1.210
- 095-098 `completo`: True
- 095-098 `D184_LLAMADAS`: {'screen_surface': 22492, 'screen_surface[m]': 22492, 'm_alpha_check': 21619}
- 095-098 `D184_EXCEPCIONES_DEL_CRIBADO`: 0
- 095-098 `D184_excepciones`: []
- 095-098 `D184_SCREEN_ERROR`: 0
- 095-098 `D184_CONTROL_VE_EL_CASO`: True
- 095-098 `comparado_con`: None

### 0.1.211

- suite `version`: 0.1.211
- suite `arbol_medido`: C:\Samuel\OpenGeoRock_Slip2d\OGR-Slip2D
- suite `completo`: True
- suite `suite`: {'codigo': 0, 'segundos': 3015.7, 'total': 4664, 'pasan': 4664, 'fallan': 0, 'filtrada': False, 'arbol_equivocado': False}
- suite `LINEAS_ILEGIBLES`: 0
- suite `archivos_de_registro`: 426
- suite `procesos_con_sonda`: 385
- suite `SONDAS_FUERA_DEL_ARBOL`: []
- suite `LLAMADAS`: {'screen_surface': 473499, 'screen_surface[m]': 472448, 'm_alpha_check': 410070, 'screen_surface[t]': 794, 'tensile_stress_check': 814, 'screen_surface[]': 2, 'screen_surface[tm]': 255, 'screen_error': 11}
- suite `EXCEPCIONES_DEL_CRIBADO`: 10
- suite `EXCEPCIONES_QUE_ESCAPAN_DE_SCREEN_SURFACE`: 0
- suite `EXCEPCIONES_POR_TEST`: {'test_screen_error_v1211.py::test_check_surface_keeps_its_two_value_contract': 2, 'test_screen_error_v1211.py::test_it_cannot_be_the_critical_surface_while_another_is_admissible': 1, 'test_screen_error_v1211.py::test_it_exports_as_minus_101_even_if_the_text_says_m_alpha': 1, 'test_screen_error_v1211.py::test_no_combination_of_checks_admits_it_silently': 3, 'test_screen_error_v1211.py::test_screen_surface_declares_the_exception': 1, 'test_screen_error_v1211.py::test_the_search_door_rejects_it_with_note_and_reason': 1, 'test_screen_error_v1211.py::test_the_result_keeps_its_factor_and_validity': 1}
- suite `SCREEN_ERROR`: 10
- suite `SCREEN_ERROR_POR_TEST`: {'test_screen_error_v1211.py::test_check_surface_keeps_its_two_value_contract': 2, 'test_screen_error_v1211.py::test_it_cannot_be_the_critical_surface_while_another_is_admissible': 1, 'test_screen_error_v1211.py::test_it_exports_as_minus_101_even_if_the_text_says_m_alpha': 1, 'test_screen_error_v1211.py::test_no_combination_of_checks_admits_it_silently': 3, 'test_screen_error_v1211.py::test_screen_surface_declares_the_exception': 1, 'test_screen_error_v1211.py::test_the_search_door_rejects_it_with_note_and_reason': 1, 'test_screen_error_v1211.py::test_the_result_keeps_its_factor_and_validity': 1}
- suite `tipos`: ['m_alpha_check:KeyError', 'm_alpha_check:RuntimeError', 'm_alpha_check:ValueError', 'tensile_stress_check:ValueError']
- suite `CONTROL_VE_EL_CASO`: True
- suite `control_pids`: [26044]
- 095-098 `version`: 0.1.211
- 095-098 `arbol_medido`: C:\Samuel\OpenGeoRock_Slip2d\OGR-Slip2D
- 095-098 `completo`: True
- 095-098 `D184_LLAMADAS`: {'screen_surface': 22492, 'screen_surface[m]': 22492, 'm_alpha_check': 21732}
- 095-098 `D184_EXCEPCIONES_DEL_CRIBADO`: 0
- 095-098 `D184_excepciones`: []
- 095-098 `D184_SCREEN_ERROR`: 0
- 095-098 `D184_CONTROL_VE_EL_CASO`: True
- 095-098 `comparado_con`: 0.1.210

